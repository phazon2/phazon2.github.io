#!/usr/bin/env python3
"""Volume prospecting: find every contactable creator in a niche, cheaply.

This exists because filtering was never the bottleneck on outreach volume —
addresses were. The API does not return a creator's email and YouTube's
About-page reveal is behind a captcha, so every address used to be found by
hand, which is most of the cost of a cycle. But creators who want to be
contacted print the address in the bio or under the videos, and those
descriptions ride along free on a call we already make.

So this pass is deliberately almost unfiltered. It drops only what would waste
a send outright:

  * dead channels      — a creator who stopped uploading cannot post a link
  * already contacted  — the one unforgivable outreach error
  * no address         — cannot be emailed at all, so cannot be a send

It does NOT drop creators for having a storefront. That filter was inherited
from a premise worth stating plainly, because two niches' worth of evidence
went against it: "find a creator whose audience wants what they don't sell"
selects, at reach, for creators who are bad at business. A creator already
selling has payment rails, a buying audience and a reason to care about
margin — that is a better affiliate, not a worse one. The storefront is
reported, and ranked *up*, not filtered out.

Spends no Gemini tokens. Clustering happens afterwards, on the contactable
shortlist only, so no tokens are burned on someone who cannot be reached.

    ./prospect.py "pressure washing business" "lawn care business" \
        --min-subs 3000 --max-subs 500000 -o queue.md
"""
import argparse
import json
import os
import pathlib
import sys

import re

import demand_harvest as dh
import shortlist as sl


# Words that identify nobody. A description carries other people's addresses —
# sponsors, collaborators, the creator's own second business — and an address
# extracted from one is not necessarily the creator's. A 157,000-subscriber
# roofing channel yielded `vito@amazingunderdeck.com`, a sponsor. Emailing that
# with "your audience keeps asking..." burns the lead and looks like a scrape.
GENERIC = {"lawn", "care", "business", "cleaning", "pressure", "washing",
           "window", "junk", "removal", "detailing", "handyman", "painting",
           "roofing", "service", "services", "channel", "company", "official",
           "professional", "academy", "exterior", "interior", "grass",
           "cutting", "mobile", "clean", "wash", "paint", "the", "and", "with",
           "media", "info", "contact", "hello", "team", "youtube"}


def address_confidence(title, email):
    """'named' | 'generic' | 'mismatch' — does the address belong to this channel?

    Substring, not token equality: "biglinlawncare@gmail.com" is a single token,
    so comparing whole words finds nothing and calls every real address a
    mismatch. A distinctive word from the channel name appearing anywhere in the
    address is the signal.
    """
    flat = re.sub(r"[^a-z]", "", (email or "").lower())
    words = re.findall(r"[a-z]{3,}", (title or "").lower())
    if any(w not in GENERIC and w in flat for w in words):
        return "named"
    if any(w in GENERIC and w in flat for w in words):
        return "generic"
    return "mismatch"


def prospect(cid, key, videos):
    ch = dh.resolve_channel(cid, key)
    vids = dh.recent_videos(ch["uploads"], key, videos)
    if not vids:
        return None
    stats = dh.video_stats([v["video_id"] for v in vids], key)
    desc = "\n".join(stats.get(v["video_id"], {}).get("description", "")
                     for v in vids)
    views = [stats.get(v["video_id"], {}).get("views", 0) for v in vids]
    views = [v for v in views if v > 0]
    pubs = sorted(v["published"] for v in vids if v.get("published"))
    last = pubs[-1][:10] if pubs else ""
    import datetime as dt
    dormant = ((dt.date.today() - dt.date(*map(int, last.split("-")))).days
               if last else -1)
    import statistics as stt
    return {
        "channel_id": ch["channel_id"],
        "title": ch["title"],
        "subscribers": ch["subscribers"],
        "median_views": int(stt.median(views)) if views else 0,
        "last_upload": last,
        "dormant_days": dormant,
        "emails": sl._emails(ch["description"], desc),
        "obfuscated": bool(sl._emails(ch["description"], desc))
                      and not sl.EMAIL_RE.search(ch["description"] + desc),
        "storefront": sl._storefront(desc) + sl._sells(ch["description"]),
        "address_confidence": (address_confidence(
            ch["title"], sl._emails(ch["description"], desc)[0])
            if sl._emails(ch["description"], desc) else "none"),
        "latest_titles": [v["title"] for v in vids[:3]],
    }


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="+")
    ap.add_argument("--min-subs", type=int, default=3_000)
    ap.add_argument("--max-subs", type=int, default=500_000)
    ap.add_argument("--videos", type=int, default=8,
                    help="videos sampled per channel, for dates and descriptions")
    ap.add_argument("--per-query", type=int, default=25)
    ap.add_argument("--max-dormant-days", type=int, default=180)
    ap.add_argument("--contacted", default=str(
        pathlib.Path(__file__).resolve().parent.parent / "contacted.txt"))
    ap.add_argument("-o", "--out", default="queue.md")
    args = ap.parse_args()

    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise SystemExit("set YOUTUBE_API_KEY")

    already = set()
    cpath = pathlib.Path(args.contacted)
    if cpath.exists():
        for line in cpath.read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                already.add(line.split()[0])

    seen, cands = set(), []
    for q in args.queries:
        found = sl.search_channels(q, key, args.per_query)
        print(f'search "{q}" -> {len(found)}', file=sys.stderr)
        for cid, title in found:
            if cid not in seen:
                seen.add(cid)
                cands.append((cid, q))

    rows, dropped = [], []
    for cid, q in cands:
        if cid in already:
            dropped.append((cid, "already contacted"))
            continue
        try:
            r = prospect(cid, key, args.videos)
        except SystemExit as exc:
            dropped.append((cid, str(exc)[:50]))
            continue
        if not r:
            continue
        if not (args.min_subs <= r["subscribers"] <= args.max_subs):
            dropped.append((r["title"], f"{r['subscribers']:,} subs"))
            continue
        if 0 <= args.max_dormant_days < r["dormant_days"]:
            dropped.append((r["title"],
                            f"dormant since {r['last_upload']}"))
            continue
        r["found_via"] = q
        rows.append(r)
        print(f"  {r['title'][:32]:34} {r['subscribers']:>8,}  "
              f"{', '.join(r['emails'][:1]) or '-'}", file=sys.stderr)

    sendable = [r for r in rows if r["emails"]]
    noaddr = [r for r in rows if not r["emails"]]
    # Reach, because a link's value is the audience it reaches.
    sendable.sort(key=lambda r: -r["median_views"])
    noaddr.sort(key=lambda r: -r["median_views"])

    out = [f"# Outreach queue — {', '.join(args.queries)}", "",
           f"{len(cands)} channels found · {len(rows)} live and in band · "
           f"**{len(sendable)} with an address, ready to send** · "
           f"{len(noaddr)} need an address found by hand", "",
           "Storefronts are reported, not filtered: a creator who already "
           "sells has payment rails and a buying audience, which makes a "
           "better affiliate than one who has never sold anything.", "",
           "| # | Creator | Subs | Median views | Email | Storefront | Last upload |",
           "|--:|---|---:|---:|---|---|---|"]
    for i, r in enumerate(sendable, 1):
        flag = " ⚠obfuscated" if r["obfuscated"] else ""
        if r["address_confidence"] == "mismatch":
            flag += " ⚠**not the creator?**"
        elif r["address_confidence"] == "generic":
            flag += " ⚠generic"
        out.append(f"| {i} | {r['title']} | {r['subscribers']:,} | "
                   f"{r['median_views']:,} | `{r['emails'][0]}`{flag} | "
                   f"{', '.join(r['storefront'][:2]) or '—'} | "
                   f"{r['last_upload']} |")
    if noaddr:
        out += ["", "## No address in bio or descriptions", "",
                "Each needs the About tab's Email button (captcha, so it is a "
                "human step) or a site whois. Worth doing only for the top of "
                "this list.", "",
                "| Creator | Subs | Median views | Last upload |",
                "|---|---:|---:|---|"]
        for r in noaddr:
            out.append(f"| {r['title']} | {r['subscribers']:,} | "
                       f"{r['median_views']:,} | {r['last_upload']} |")
    if dropped:
        out += ["", "## Dropped", ""]
        out += [f"- {t} — {why}" for t, why in dropped]

    pathlib.Path(args.out).write_text("\n".join(out))
    pathlib.Path(args.out).with_suffix(".json").write_text(
        json.dumps({"sendable": sendable, "no_address": noaddr}, indent=1))
    print(f"\n{len(sendable)} sendable / {len(rows)} live -> {args.out}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
