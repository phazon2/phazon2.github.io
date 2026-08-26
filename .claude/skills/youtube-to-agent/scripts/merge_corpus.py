#!/usr/bin/env python3
"""Aggregate per-video extractions into one structured corpus index.

Deterministic pass only. Parsing, grouping and counting are done here in
plain code so the model never has to hold 106 files in context and never
gets the chance to hallucinate a total. Judgement calls — reconciling
genuine contradictions, merging near-duplicate technique names — are left
to a synthesis pass reading this output.

The load-bearing rule (see references/corpus-synthesis.md): mention_count
is REACH, not evidence. One creator saying something thirty times is one
source stated thirty times, and this script never lets frequency stand in
for support.

Usage:
    ./merge_corpus.py corpus/ -o merged.json --report
"""

import argparse
import collections
import json
import pathlib
import re

SECTIONS = ["TECHNIQUES", "PARAMETERS", "DECISION-RULES", "CLAIMS",
            "CONTRADICTS-COMMON-ADVICE", "CORRECTS-HIS-OWN-PRIOR",
            "DIAGNOSTICS", "PREREQUISITES", "SELLING", "UNCLEAR"]
GRADES = ["STUDY", "RESEARCH-VAGUE", "EXPERIENCE", "ASSERTED"]
EMPTY = re.compile(r"^\*?\(?\s*(none|n/?a|nothing)\s*\)?\*?$", re.I)


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


def split_sections(body):
    """Bucket lines under their nearest preceding known section heading."""
    out, current = collections.defaultdict(list), None
    for line in body.splitlines():
        m = re.match(r"^#{1,4}\s+([A-Z][A-Z\- ]+)\s*$", line.strip())
        if m:
            name = m.group(1).strip()
            current = name if name in SECTIONS else None
            continue
        if current and line.strip() and not EMPTY.match(line.strip()):
            out[current].append(line.rstrip())
    return out


def canon_key(text):
    """Normalize a technique name so trivial variants collapse together."""
    t = text.lower().strip().strip("*_`")
    t = re.sub(r"\(.*?\)", "", t)
    t = re.sub(r"\b(technique|method|approach|strategy|the|a|an)\b", "", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus_dir")
    ap.add_argument("-o", "--out", default="merged.json")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    files = sorted(p for p in pathlib.Path(args.corpus_dir).glob("*.md"))
    videos, techniques = [], collections.defaultdict(list)
    grades = collections.Counter()
    buckets = collections.defaultdict(list)

    for path in files:
        meta, body = parse_front(path.read_text())
        secs = split_sections(body)
        vid = meta.get("video_id", path.stem)
        title = meta.get("title", path.stem)
        videos.append({"file": path.name, "video_id": vid, "title": title,
                       "sections": {k: len(v) for k, v in secs.items()}})

        for line in secs.get("TECHNIQUES", []):
            m = re.search(r"\*\*canonical:\*\*\s*(.+)", line)
            if m:
                val = m.group(1).strip().strip("`*")
                if val.lower() != "same":
                    techniques[canon_key(val)].append({"video": vid, "title": title, "raw": val})
        for line in secs.get("TECHNIQUES", []):
            m = re.search(r"\*\*name:\*\*\s*(.+)", line)
            if m:
                techniques[canon_key(m.group(1))].append(
                    {"video": vid, "title": title, "raw": m.group(1).strip().strip("`*")})

        for line in secs.get("CLAIMS", []):
            for g in GRADES:
                if re.search(rf"\|\s*{re.escape(g)}\s*\|", line):
                    grades[g] += 1
                    break

        for name in ("PARAMETERS", "DECISION-RULES", "CONTRADICTS-COMMON-ADVICE",
                     "CORRECTS-HIS-OWN-PRIOR", "DIAGNOSTICS", "UNCLEAR"):
            for line in secs.get(name, []):
                if line.strip().startswith(("-", "*", "|")):
                    buckets[name].append({"video": vid, "line": line.strip()})

    merged = {
        "videos_parsed": len(videos),
        "evidence_grades": dict(grades),
        "technique_groups": [
            # mention_count is REACH. It is deliberately not called evidence,
            # weight, or confidence anywhere downstream.
            {"key": k, "mention_count": len(v),
             "variants": sorted({x["raw"] for x in v}),
             "videos": sorted({x["video"] for x in v})}
            for k, v in sorted(techniques.items(), key=lambda kv: -len(kv[1])) if k
        ],
        "buckets": {k: v for k, v in buckets.items()},
        "videos": videos,
    }
    pathlib.Path(args.out).write_text(json.dumps(merged, indent=2))

    if args.report:
        print(f"videos parsed        : {len(videos)}")
        print(f"distinct techniques  : {len(merged['technique_groups'])}")
        for name in ("PARAMETERS", "DECISION-RULES", "DIAGNOSTICS",
                     "CONTRADICTS-COMMON-ADVICE", "CORRECTS-HIS-OWN-PRIOR", "UNCLEAR"):
            print(f"{name:<22} : {len(buckets.get(name, []))}")
        total = sum(grades.values())
        print(f"\nclaims graded        : {total}")
        for g in GRADES:
            n = grades.get(g, 0)
            print(f"  {g:<16} {n:>5}  {n/total*100 if total else 0:5.1f}%")
        print("\ntop techniques by REACH (mentions, NOT evidence):")
        for t in merged["technique_groups"][:12]:
            print(f"  {t['mention_count']:>3}x  {t['key'][:52]}")
        thin = [v for v in videos if sum(v["sections"].values()) < 8]
        if thin:
            print(f"\n{len(thin)} thin extractions (<8 lines) — candidates for re-run:")
            for v in thin[:10]:
                print(f"  {v['file']}")

    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
