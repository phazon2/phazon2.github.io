#!/usr/bin/env python3
"""One command: a niche in, ready-to-send outreach packages out.

The first run of this method took four separate scripts and a hand-written
email per creator. That is fine once and wrong twelve times, so this chains
the whole thing:

    search -> screen on demand reach -> drop the already-monetised
          -> harvest + cluster each survivor -> draft its outreach email

Each creator gets one file: subject line, email body quoting that creator's own
commenters verbatim, the evidence behind it, and the two checks only a human can
do (the bio eyeball, the CAPTCHA'd business email).

Usage:
    export YOUTUBE_API_KEY=... GEMINI_API_KEY=...
    ./campaign.py "bookkeeping business" "start a bookkeeping business" \
        --product-url https://you.gumroad.com/l/thing \
        --product-name "12-Month Bookkeeping Workbook" \
        --price 39 --code RACHAEL --discount 10 \
        --sender "Diego Radrigán" --location "Lampa, Chile" --email you@example.com \
        --top 5 --out-dir campaign-02/

Resumable: a creator whose package file already exists is skipped, so a run that
dies on candidate four costs nothing to repeat.

WHAT THIS DOES NOT DO: send anything. The send is manual, always — scripted
outreach at volume breaks platform terms, and the two-touch cap plus a real
signature is what keeps this the right side of CAN-SPAM and Ley 19.496.
"""

import argparse
import json
import os
import pathlib
import re
import sys

import demand_harvest as dh
import shortlist as sl

EMAIL_PROMPT = """You are drafting one cold email from a person who builds spreadsheet
products to a YouTube creator, offering to let the creator sell it to their audience.

You are given: the creator's name and channel, the demand clusters found in their own
comment section, and the verbatim comments behind each cluster.

Write the email following this proven structure exactly:

1. "Hi <first name>," then name the pattern in their comments — no compliments, no preamble.
2. Quote THREE of their commenters verbatim, each on its own line, as block quotes.
   Copy them character for character from the comments given. Never paraphrase into a
   quote. Never invent one. Never tidy the spelling or grammar.
3. One sentence: how many separate people asked for the same thing.
4. "So I built it. It's attached, nothing to click, yours to keep either way."
5. ONE short paragraph on what the product does. Use ONLY the PRODUCT FACTS given
   below. Do not add a feature, tab, or capability that is not in that list, however
   well it would answer the comments. An invented feature is a lie the buyer discovers
   on download.
6. The product link on its own line.
7. Two options, labelled A and B:
   A. Affiliate link — {price}, code {code} takes {discount} off so their audience pays
      {net}, tracked link plus their own dashboard, costs them nothing, commits them to nothing.
   B. Licence it — pay once, their name on it, they keep 100% of every sale.
8. A paragraph admitting plainly that the product has no sales yet and that they can watch
   the real conversion rate before committing. Do not hide this or soften it into marketing.
9. "If it's not for you, reply \\"no\\" and I'll stop — I won't email you again."
10. Signature: name, location, email address.

Rules:
- Address the creator using GREETING NAME exactly as given. The discount code is a
  coupon, never a person's name — do not greet anyone by it.
- Under 300 words in the body.
- No words: collaboration, partnership, opportunity, synergy, exciting, revolutionary.
- No em-dash-heavy hype. Plain sentences.
- Do not claim view counts, audience size, or growth figures back at them. They can check
  their own analytics and a wrong number ends the conversation.
- Lifetime view totals are not current reach. Never cite one as evidence.

Then, after the email, output a line `SUBJECT: <subject line>` with a lowercase subject
that names the specific thing you built for them. No pitch words. Under 60 characters.
"""


def draft_email(raw, report, args, key, model):
    """Ask Gemini for the email, grounded only in this creator's real comments."""
    name = raw["channel"]["title"]
    comments = []
    for v in raw["videos"]:
        for c in v.get("comments") or []:
            if c.get("signal") == "strong":
                comments.append(f"- \"{c['text'][:400]}\"")
    net = args.price - args.discount

    body = {"contents": [{"parts": [{"text":
        EMAIL_PROMPT.format(price=f"${args.price}", code=args.code,
                            discount=f"${args.discount}", net=f"${net}")
        + f"\n\n---\nCREATOR: {name}\nGREETING NAME: {args.greeting or name}\n"
        + f"CHANNEL: {raw['channel']['channel_id']}\n"
        + f"PRODUCT: {args.product_name}\nPRODUCT LINK: {args.product_url}\n"
        + f"PRODUCT FACTS (the only claims you may make about it):\n{args.product_facts}\n"
        + f"SENDER: {args.sender}\nLOCATION: {args.location}\nEMAIL: {args.email}\n\n"
        + f"DEMAND CLUSTERS FOUND:\n{report[:6000]}\n\n"
        + "VERBATIM COMMENTS (quote only from these):\n" + "\n".join(comments[:120])
    }]}]}

    import urllib.request, urllib.error
    req = urllib.request.Request(
        f"{dh.GEMINI}/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        return None, f"gemini HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}"

    cand = (payload.get("candidates") or [{}])[0]
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
    m = re.search(r"SUBJECT:\s*(.+)", text)
    subject = m.group(1).strip() if m else f"the thing your commenters keep asking for"
    email = re.sub(r"SUBJECT:.*", "", text).strip()
    return (subject, email), None


def verify_quotes(email, raw):
    """Every block quote in the email must appear in the real harvest.

    This exists because a drafted quote that nobody actually wrote turns the
    strongest part of the pitch into the thing that ends the conversation.
    """
    haystack = " ".join(
        c["text"] for v in raw["videos"] for c in (v.get("comments") or []))
    haystack = re.sub(r"\s+", " ", haystack).lower()
    bad = []
    for line in email.splitlines():
        line = line.strip()
        if not line.startswith(">"):
            continue
        q = re.sub(r"\s+", " ", line.lstrip("> ").strip(' "“”')).lower()
        if len(q) < 25:
            continue
        probe = q[:60]
        if probe not in haystack:
            bad.append(line[:110])
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="+")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--product-url", required=True)
    ap.add_argument("--product-name", required=True)
    ap.add_argument("--sender", required=True)
    ap.add_argument("--location", required=True)
    ap.add_argument("--email", required=True)
    ap.add_argument("--price", type=int, default=39)
    ap.add_argument("--code", default="")
    ap.add_argument("--discount", type=int, default=10)
    ap.add_argument("--product-facts", required=True,
                    help="the ONLY claims the email may make about the product; "
                         "pass a file path or the text itself")
    ap.add_argument("--greeting", default="",
                    help="first name to open with; defaults to the channel title")
    ap.add_argument("--contacted",
                    default=str(pathlib.Path(__file__).resolve().parent.parent / "contacted.txt"),
                    help="ledger of channels already drafted/emailed, across campaigns")
    ap.add_argument("--top", type=int, default=5, help="creators to draft for")
    ap.add_argument("--min-subs", type=int, default=5_000)
    ap.add_argument("--max-subs", type=int, default=250_000)
    ap.add_argument("--min-reach", type=int, default=150,
                    help="skip candidates below this demand reach (default 150)")
    ap.add_argument("--videos", type=int, default=25)
    ap.add_argument("--pages", type=int, default=4)
    ap.add_argument("--model", default=dh.DEFAULT_MODEL)
    args = ap.parse_args()

    yt_key = os.environ.get("YOUTUBE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    g_key = os.environ.get("GEMINI_API_KEY")
    if not yt_key or not g_key:
        raise SystemExit("set YOUTUBE_API_KEY and GEMINI_API_KEY")

    facts = pathlib.Path(args.product_facts)
    if facts.exists():
        args.product_facts = facts.read_text()

    out = pathlib.Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    (out / "raw").mkdir(exist_ok=True)

    # One ledger across every campaign, so nobody is drafted — or emailed — twice.
    ledger = pathlib.Path(args.contacted)
    already = {l.split()[0] for l in ledger.read_text().splitlines()
               if l.strip() and not l.startswith("#")} if ledger.exists() else set()
    if already:
        print(f"{len(already)} channel(s) already handled, from {ledger}", file=sys.stderr)

    # ---- 1. find and screen -------------------------------------------------
    seen, cands = set(), []
    for q in args.queries:
        for cid, title in sl.search_channels(q, yt_key, 15):
            if cid not in seen:
                seen.add(cid); cands.append((cid, q))
    print(f"{len(cands)} channels found across {len(args.queries)} queries", file=sys.stderr)

    rows = []
    for cid, q in cands:
        try:
            ch = dh.resolve_channel(cid, yt_key)
        except SystemExit:
            continue
        if not (args.min_subs <= ch["subscribers"] <= args.max_subs):
            continue
        try:
            row = sl.screen(cid, yt_key, 10, 2)
        except SystemExit:
            continue
        if not row:
            continue
        row["found_via"] = q
        rows.append(row)
        flag = ",".join(row["sells_something"][:2]) or "-"
        print(f"  {row['title'][:38]:<38} reach {row['demand_reach']:>6,}  sells: {flag}",
              file=sys.stderr)

    # the bio heuristic is a filter, not a verdict — it is still eyeballed later
    fresh = [r for r in rows if not r["sells_something"]
             and r["demand_reach"] >= args.min_reach]
    fresh.sort(key=lambda r: -r["demand_reach"])
    print(f"\n{len(rows)} screened, {len(fresh)} with no product tell and reach "
          f">= {args.min_reach}", file=sys.stderr)

    # ---- 2. harvest, cluster, draft ----------------------------------------
    made, skipped = [], []
    for r in fresh[:args.top]:
        slug = re.sub(r"\W+", "-", r["title"].lower()).strip("-")
        pkg = out / f"{slug}.OUTREACH.md"
        if pkg.exists() or r["channel_id"] in already:
            print(f"skip (already handled)  {r['title']}", file=sys.stderr); continue

        print(f"\n== {r['title']}  (reach {r['demand_reach']:,})", file=sys.stderr)
        raw = dh.harvest(r["channel_id"], yt_key, args.videos, args.pages)
        (out / "raw" / f"{slug}.raw.json").write_text(
            json.dumps(raw, indent=2, ensure_ascii=False))
        if raw["counts"]["strong"] < 8:
            skipped.append((r["title"], f"only {raw['counts']['strong']} strong signals"))
            print("   too few strong signals to draft from", file=sys.stderr); continue

        report, _ = dh.cluster(raw, g_key, args.model)

        # The clustering pass is allowed to say "there is nothing here". When it
        # does, drafting anyway produces an email built on unrelated one-off
        # questions — which is how the first run of this invented product
        # features to make three stray comments look like a cluster.
        refusals = ("no demand cluster", "do not manufacture", "clears the minimum",
                    "isolated queries", "evaluate a different creator")
        low = report.lower()
        if any(r in low for r in refusals):
            skipped.append((r["title"], "clustering found no real demand cluster"))
            (out / f"{slug}.NO-CLUSTER.md").write_text(
                f"# No cluster — {r['title']}\n\n"
                f"`{r['channel_id']}` · demand reach {r['demand_reach']:,}\n\n"
                "The clustering pass refused this dataset, so no email was drafted. "
                "Its reasoning:\n\n" + report)
            print("   clustering refused — no email drafted", file=sys.stderr)
            continue

        drafted, err = draft_email(raw, report, args, g_key, args.model)
        if err:
            skipped.append((r["title"], err)); print("   " + err, file=sys.stderr); continue
        subject, email = drafted

        fake = verify_quotes(email, raw)
        status = ("**QUOTES VERIFIED** — every block quote was found in the harvest."
                  if not fake else
                  "**QUOTE CHECK FAILED** — these do not appear in the harvest, fix or cut "
                  "them before sending:\n\n" + "\n".join(f"  - {q}" for q in fake))

        pkg.write_text(f"""# Outreach — {r['title']}

**Channel:** `{r['channel_id']}` · {r['subscribers']:,} subs
**Median views:** {r['median_views']:,} · **demand reach:** {r['demand_reach']:,} ·
**{r['density']:.1f}%** of comments ask for help
**Found via:** "{r['found_via']}"

## Before you send — two things only you can do

1. **Eyeball the bio.** The automated check found no product tell, but it is a heuristic.
   Open the channel's About page: if they already sell a course or template, skip them —
   they do not need a partner.
2. **Get the business email.** About page → Business email → View email address. It is
   behind a CAPTCHA on purpose, so no script can fetch it.

## Subject

{subject}

## Body

{email}

## Quote check

{status}

---

## Demand report

{report}
""")
        made.append((r["title"], r["demand_reach"], subject))
        with ledger.open("a") as fh:
            fh.write(f"{r['channel_id']}  {r['title']}  drafted\n")
        print(f"   -> {pkg.name}", file=sys.stderr)

    # ---- 3. index -----------------------------------------------------------
    idx = [f"# Campaign — {', '.join(args.queries)}", "",
           f"Product: {args.product_name} · {args.product_url} · ${args.price}"
           + (f" · code {args.code} (−${args.discount})" if args.code else ""), "",
           f"{len(cands)} channels found · {len(rows)} screened · {len(fresh)} eligible · "
           f"{len(made)} packages drafted", "",
           "| Creator | Demand reach | Subject | Sent? | Replied? |",
           "|---|---:|---|:--:|:--:|"]
    for t, reach, subj in made:
        idx.append(f"| {t} | {reach:,} | {subj} | ☐ | ☐ |")
    if skipped:
        idx += ["", "## Skipped", ""] + [f"- **{t}** — {why}" for t, why in skipped]
    idx += ["", "## Rules that do not change", "",
            "- You press send. Never automate it.",
            "- One follow-up, day 6, then stop. No third email.",
            "- Honour every \"no\" immediately and permanently.",
            "- Track **sales**, not replies. A yes that never gets posted is not progress."]
    (out / "INDEX.md").write_text("\n".join(idx))

    print(f"\n{len(made)} package(s) -> {out}/  · index at {out}/INDEX.md", file=sys.stderr)


if __name__ == "__main__":
    main()
