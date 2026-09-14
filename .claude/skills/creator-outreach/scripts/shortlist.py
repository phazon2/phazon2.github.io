#!/usr/bin/env python3
"""Rank candidate creators by whether their audience actually asks for help.

The four filters from the method — 10k-100k subscribers, teaches a job, no
product in bio, public email — are all about the creator. None of them measures
the audience, and the audience is who buys. A 60k-subscriber channel whose
comments are applause is worth less than an 12k channel whose comments are
"how do I handle this when my client already has a CRM".

So this adds a fifth filter and sorts on it: STRONG-SIGNAL DENSITY, the share of
comments that are someone asking for help with their own situation. Measured by
the same grader demand_harvest.py uses, on a cheap 3-video sample.

Cost: ~100 quota units per search query, ~6 per channel screened. A 4-query,
20-channel run is ~520 units of a 10,000/day free allowance.

Usage:
    export YOUTUBE_API_KEY=...
    ./shortlist.py "bookkeeping tutorial" "quickbooks for bookkeepers" -o shortlist.md
    ./shortlist.py "etsy shop tips" --min-subs 5000 --max-subs 150000
"""

import argparse
import json
import os
import pathlib
import statistics as stt
import sys

import demand_harvest as dh


def search_channels(query, key, limit=25):
    data = dh.yt("search", key, part="snippet", q=query, type="channel",
                 maxResults=min(50, limit), relevanceLanguage="en")
    return [(it["snippet"]["channelId"], it["snippet"]["title"])
            for it in data.get("items", [])]


def screen(channel_id, key, videos, pages):
    """Cheap density sample. Returns a row, or None if the channel is unusable."""
    ch = dh.resolve_channel(channel_id, key)
    vids = dh.recent_videos(ch["uploads"], key, videos)
    if not vids:
        return None
    stats = dh.video_stats([v["video_id"] for v in vids], key)
    views = [stats.get(v["video_id"], {}).get("views", 0) for v in vids]
    views = [v for v in views if v > 0]

    fetched = strong = weak = 0
    examples = []
    for v in vids:
        cs, note = dh.comments(v["video_id"], key, pages)
        fetched += len(cs)
        for c in cs:
            if c["signal"] == "strong":
                strong += 1
                if len(examples) < 3:
                    examples.append(c["text"].replace("\n", " ")[:150])
            elif c["signal"] == "weak":
                weak += 1

    return {
        "channel_id": ch["channel_id"],
        "title": ch["title"],
        "subscribers": ch["subscribers"],
        "videos_sampled": len(vids),
        "fetched": fetched,
        "strong": strong,
        "weak": weak,
        "density": (strong / fetched * 100) if fetched else 0.0,
        # Reach is what decides sales. Subscriber count does not: a 53k channel
        # in this niche had a 2,338-view median. Demand reach = how many
        # help-seeking viewers a typical post actually puts the product in front of.
        "median_views": int(stt.median(views)) if views else 0,
        "max_views": max(views) if views else 0,
        "demand_reach": int((stt.median(views) if views else 0)
                            * ((strong / fetched) if fetched else 0)),
        "email_in_bio": "@" in ch["description"],
        "link_in_bio": any(s in ch["description"].lower()
                           for s in ("http", "gumroad", "whop", "course", "shop", "store")),
        "examples": examples,
        "latest_titles": [v["title"] for v in vids[:3]],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("queries", nargs="+", help="search phrases a creator in this niche would rank for")
    ap.add_argument("--min-subs", type=int, default=10_000)
    ap.add_argument("--max-subs", type=int, default=100_000)
    ap.add_argument("--videos", type=int, default=10, help="videos sampled per channel")
    ap.add_argument("--pages", type=int, default=2, help="comment pages per video")
    ap.add_argument("--min-comments", type=int, default=30,
                    help="below this many comments a density is not reportable (default 30)")
    ap.add_argument("--per-query", type=int, default=15)
    ap.add_argument("-o", "--out", default="shortlist.md")
    args = ap.parse_args()

    key = os.environ.get("YOUTUBE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("set YOUTUBE_API_KEY")

    seen, candidates = set(), []
    for q in args.queries:
        found = search_channels(q, key, args.per_query)
        print(f'search "{q}" -> {len(found)} channels', file=sys.stderr)
        for cid, title in found:
            if cid not in seen:
                seen.add(cid)
                candidates.append((cid, title, q))

    rows, skipped = [], []
    for cid, title, q in candidates:
        try:
            ch = dh.resolve_channel(cid, key)
        except SystemExit as exc:
            skipped.append((title, str(exc)[:60]))
            continue
        if not (args.min_subs <= ch["subscribers"] <= args.max_subs):
            skipped.append((ch["title"], f"{ch['subscribers']:,} subs — outside band"))
            continue
        print(f"  screening {ch['title']} ({ch['subscribers']:,})...", file=sys.stderr)
        try:
            row = screen(cid, key, args.videos, args.pages)
        except SystemExit as exc:
            skipped.append((ch["title"], str(exc)[:60]))
            continue
        if row:
            row["found_via"] = q
            rows.append(row)
            print(f"    {row['strong']:>3}/{row['fetched']:>3} strong = {row['density']:>4.1f}%"
                  f"  · median {row['median_views']:>7,} views"
                  f"  · demand reach {row['demand_reach']:>6,}", file=sys.stderr)

    thin = [r for r in rows if r["fetched"] < args.min_comments]
    rows = [r for r in rows if r["fetched"] >= args.min_comments]
    rows.sort(key=lambda r: (-r["demand_reach"], -r["density"]))

    out = [f"# Creator shortlist — {', '.join(args.queries)}", "",
           f"{len(candidates)} channels found · {len(rows)} in the "
           f"{args.min_subs:,}–{args.max_subs:,} subscriber band · "
           f"sampled {args.videos} videos × {args.pages} comment page(s) each", "",
           "Sorted by **strong-signal density**: the share of comments that are someone "
           "asking for help with their own situation, not praise or commentary. "
           "Ranked by **demand reach** = median views x density: roughly how many "
           "help-seeking viewers a typical post reaches. Subscriber count is not "
           "used for ranking, because it misleads — a 53,400-subscriber channel in "
           "this niche had a 2,338-view median. "
           "Under 3% density means the audience reacts rather than asks. "
           "Channels whose sample returned fewer than "
           f"{args.min_comments} comments are listed separately: their density is not "
           "measurable, which is not the same as being zero.", "",
           "| Creator | Subs | Median views | Density | **Demand reach** | Best video | Email? |",
           "|---|---:|---:|---:|---:|---:|:--:|"]
    for r in rows:
        out.append(f"| {r['title']} | {r['subscribers']:,} | {r['median_views']:,} | "
                   f"{r['density']:.1f}% | **{r['demand_reach']:,}** | {r['max_views']:,} | "
                   f"{'yes' if r['email_in_bio'] else '—'} |")

    out += ["", "## Evidence per candidate", ""]
    for r in rows:
        out += [f"### {r['title']} — demand reach {r['demand_reach']:,}",
                f"`{r['channel_id']}` · {r['subscribers']:,} subs · "
                f"median {r['median_views']:,} views (best {r['max_views']:,}) · "
                f"{r['density']:.1f}% strong · found via \"{r['found_via']}\"",
                "", "Recent videos: " + "; ".join(r["latest_titles"]), ""]
        if r["examples"]:
            out.append("Real strong-signal comments:")
            out += [f"> {e}" for e in r["examples"]]
        else:
            out.append("_No strong-signal comments in the sample._")
        out.append("")

    if thin:
        out += ["", "## Sample too thin to score", "",
                f"Fewer than {args.min_comments} comments in the sample. Not scored — "
                "re-run these with more `--videos` or `--pages` before ruling them out.", "",
                "| Creator | Subs | Comments found |", "|---|---:|---:|"]
        for r in sorted(thin, key=lambda r: -r["fetched"]):
            out.append(f"| {r['title']} | {r['subscribers']:,} | {r['fetched']} |")

    if skipped:
        out += ["## Skipped", ""] + [f"- **{t}** — {why}" for t, why in skipped]

    pathlib.Path(args.out).write_text("\n".join(out))
    print(f"\n{len(rows)} screened -> {args.out}", file=sys.stderr)
    if rows:
        best = rows[0]
        print(f"top: {best['title']}  demand reach {best['demand_reach']:,} "
              f"({best['median_views']:,} median views x {best['density']:.1f}%)", file=sys.stderr)


if __name__ == "__main__":
    main()
