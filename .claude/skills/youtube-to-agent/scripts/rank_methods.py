#!/usr/bin/env python3
"""Rank money-making methods by what it costs to TRY them, not by claimed upside.

Claimed income is the wrong sort key. It is unverifiable, it is the number the
video is optimized to make memorable, and every method in a playlist like this
claims a good one. What actually differs between methods — and what actually
decides whether someone with no capital and three days can start — is the cost
of finding out it does not work.

So this ranks on barrier: money required, plus assets you must already have.

Barrier score (lower = startable sooner):
    recurring cost   $/month
    one-off cost     amortized over 3 months
    prerequisite     +$50 equivalent each, +$150 if it is an audience
                     or portfolio (those take months, not dollars)

The audience/portfolio weighting is the point. A method needing a $30 tool is
a smaller obstacle than one needing 5,000 followers, and a pure dollar sort
would rank them the other way round.

Usage:  ./rank_methods.py corpus/ai-business --top 15
"""

import argparse
import collections
import json
import pathlib
import re

MONEY = re.compile(r"\$\s?([\d,]+(?:\.\d{1,2})?)\s*(k|K)?")
RECURRING = re.compile(r"\b(month|mo\b|recurring|/mo|per month|subscription|annual|year)\b", re.I)
FREE = re.compile(r"\bstated free\b|\bfree\b", re.I)
HEAVY_PREREQ = re.compile(r"\b(audience|following|followers|subscriber|email list|portfolio|"
                          r"testimonial|past results|case stud|track record|existing client)\b", re.I)
GRADES = ["SHOWN", "NAMED-CASE", "STATED", "HYPOTHETICAL"]

TABLE_SEP = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
TABLE_HDR = re.compile(r"^\|\s*(parameter|figure|claim|item|technique|symptom|requirement|"
                       r"whose|evidence|timestamp|value|context|condition|action|cost)\s*\|", re.I)


def is_scaffolding(line):
    """Markdown table separators and header rows are formatting, not content."""
    s = line.strip()
    return bool(TABLE_SEP.match(s) or TABLE_HDR.match(s))



def parse_front(text):
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta = {}
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip("'\"")
    return meta, text[end + 4:]


def sections(body):
    out, cur = collections.defaultdict(list), None
    for line in body.splitlines():
        m = re.match(r"^#{1,4}\s+([A-Z][A-Z\- ]+)\s*$", line.strip())
        if m:
            cur = m.group(1).strip()
            continue
        if cur and line.strip() and not is_scaffolding(line):
            out[cur].append(line.strip())
    return out


def dollars(line):
    """Largest dollar figure on a line, k-suffix expanded."""
    best = 0.0
    for amt, k in MONEY.findall(line):
        v = float(amt.replace(",", ""))
        if k:
            v *= 1000
        best = max(best, v)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("-o", "--out", default="methods.json")
    args = ap.parse_args()

    rows = []
    for path in sorted(pathlib.Path(args.corpus_dir).glob("*.md")):
        meta, body = parse_front(path.read_text())
        s = sections(body)

        one_off = recur = 0.0
        costs = []
        for line in s.get("CAPITAL-REQUIRED", []):
            if not line.startswith(("-", "*", "|")):
                continue
            amt = dollars(line)
            if amt == 0 and FREE.search(line):
                costs.append(("free", line[:90]))
                continue
            if amt:
                if RECURRING.search(line):
                    recur += amt
                else:
                    one_off += amt
                costs.append((f"${amt:,.0f}", line[:90]))

        prereqs = [l for l in s.get("PREREQUISITES", []) if l.startswith(("-", "*", "|"))]
        heavy = [p for p in prereqs if HEAVY_PREREQ.search(p)]

        barrier = recur + one_off / 3 + len(prereqs) * 50 + len(heavy) * 100

        claims = collections.Counter()
        for line in s.get("INCOME-CLAIMS", []):
            for g in GRADES:
                if re.search(rf"\|\s*{re.escape(g)}\b", line):
                    claims[g] += 1
                    break

        rows.append({
            "title": meta.get("title", path.stem)[:70],
            "url": meta.get("url", ""),
            "barrier": round(barrier, 1),
            "recurring_month": round(recur, 2),
            "one_off": round(one_off, 2),
            "prereqs": len(prereqs),
            "heavy_prereqs": [h[:70] for h in heavy],
            "income_claims": dict(claims),
            "has_shown_evidence": claims.get("SHOWN", 0) > 0,
            "sells": len([l for l in s.get("SELLING", []) if l.startswith(("-", "*"))]),
            "prompts": len([l for l in s.get("PROMPTS-AND-TEMPLATES", []) if l.strip()]),
            "costs_sample": costs[:4],
        })

    rows.sort(key=lambda r: r["barrier"])
    pathlib.Path(args.out).write_text(json.dumps(rows, indent=2))

    print(f"{len(rows)} videos analyzed. Ranked by BARRIER TO TRY (low = start soonest)\n")
    print(f"{'barrier':>8} {'$/mo':>7} {'once':>7} {'pre':>4} {'shown?':>7}  title")
    print("-" * 100)
    for r in rows[:args.top]:
        print(f"{r['barrier']:>8.0f} {r['recurring_month']:>7.0f} {r['one_off']:>7.0f} "
              f"{r['prereqs']:>4} {'YES' if r['has_shown_evidence'] else '-':>7}  {r['title'][:58]}")

    tot = collections.Counter()
    for r in rows:
        tot.update(r["income_claims"])
    n = sum(tot.values())
    print(f"\nIncome claims across corpus ({n} total):")
    for g in GRADES:
        c = tot.get(g, 0)
        print(f"  {g:<14} {c:>4}  {c/n*100 if n else 0:5.1f}%")
    print(f"\nvideos showing any documented evidence: "
          f"{sum(1 for r in rows if r['has_shown_evidence'])}/{len(rows)}")
    print(f"videos with verbatim prompts captured : "
          f"{sum(1 for r in rows if r['prompts'])}/{len(rows)}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
