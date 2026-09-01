#!/usr/bin/env python3
"""Score a channel as a scriptwriting PROSPECT, from public data only.

Replaces "pick creators you understand" — an unmeasured judgment — with signals
that can actually be read off a channel page. Nothing here is a model opinion;
every number comes from yt-dlp metadata.

What matters for selling scripts is not niche quality. It is:

  CAN PAY      median views. Revenue roughly tracks views, and a channel with
               no revenue cannot hire regardless of how good the fit is.
  NEEDS SCRIPTS  upload cadence. Someone shipping weekly has a recurring
               scripting load; someone posting twice a year does not.
  IS GROWING   recent views vs older views. Rising channels add freelancers,
               declining ones cut them first.
  REACHABLE    subscriber band. Too small cannot pay, too large already has a
               team and never reads a cold DM.

It also surfaces OVERPERFORMERS — videos far above that channel's own median.
Those are the formats their audience actually rewards, and they are what a
sample script should be modeled on instead of generic structure advice.

Usage:
    ./score_channel.py @handle1 @handle2 --recent 30
    ./score_channel.py --from-file candidates.txt --json out.json
"""

import argparse
import json
import pathlib
import re
import statistics
import subprocess
import sys
from datetime import datetime


def log(m):
    print(m, file=sys.stderr, flush=True)


def norm(t):
    """Accept @handle, channel URL, or a video URL (resolved to its channel).

    A video URL is the natural thing to paste when you have found a creator
    through one of their videos, and silently appending /videos to it scores
    whatever channel YouTube happens to redirect to — a wrong number that
    looks like a right one.
    """
    t = t.strip()
    if not t.startswith("http"):
        return "https://www.youtube.com/@" + t.lstrip("@")
    t = t.rstrip("/")
    if "watch?v=" in t or "youtu.be/" in t:
        p = subprocess.run(
            ["yt-dlp", "--skip-download", "--no-warnings", "--print",
             "%(channel_url)s", t],
            capture_output=True, text=True, timeout=180)
        ch = p.stdout.strip().splitlines()
        if ch and ch[-1].startswith("http"):
            return ch[-1].rstrip("/")
        raise SystemExit(
            f"could not resolve channel for {t}\n"
            f"  {(p.stderr or '').strip().splitlines()[-1][:160] if p.stderr else ''}\n"
            "  pass the @handle directly instead")
    return t


def fetch(url, n):
    v = url if "/videos" in url else url + "/videos"
    p = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--no-warnings", "--playlist-end", str(n),
         "--print", "%(id)s|%(view_count)s|%(duration)s|%(timestamp)s|%(title)s", v],
        capture_output=True, text=True, timeout=600)
    rows = []
    for line in p.stdout.splitlines():
        f = line.split("|", 4)
        if len(f) >= 5 and f[0].strip():
            rows.append({
                "id": f[0],
                "views": int(f[1]) if f[1].isdigit() else 0,
                "dur": int(f[2]) if f[2].isdigit() else 0,
                "ts": int(f[3]) if f[3].isdigit() else 0,
                "title": f[4],
            })
    return rows, p.stderr


def score(url, n):
    rows, err = fetch(url, n)
    if not rows:
        return {"url": url, "error": (err or "no videos").strip().splitlines()[-1][:120]}

    views = [r["views"] for r in rows if r["views"] > 0]
    if not views:
        return {"url": url, "error": "no view data (channel may hide counts)"}
    med = statistics.median(views)

    # Cadence from timestamps, when available.
    ts = sorted(r["ts"] for r in rows if r["ts"])
    per_month = None
    if len(ts) >= 4:
        span_days = (ts[-1] - ts[0]) / 86400
        if span_days > 0:
            per_month = round(len(ts) / (span_days / 30.4), 1)

    # Trend: newest third vs oldest third, by upload time.
    trend = None
    dated = sorted([r for r in rows if r["ts"]], key=lambda r: r["ts"])
    if len(dated) >= 6:
        k = len(dated) // 3
        old = statistics.median([r["views"] for r in dated[:k]] or [0])
        new = statistics.median([r["views"] for r in dated[-k:]] or [0])
        if old > 0:
            trend = round(new / old, 2)

    over = sorted([r for r in rows if r["views"] >= med * 2],
                  key=lambda r: -r["views"])[:5]

    # Prospect score. Deliberately crude and fully inspectable — every term is
    # a public number, so a surprising rank can always be traced to its cause.
    s = 0.0
    if 5_000 <= med <= 500_000:          # can pay, not yet a media company
        s += 40
    elif med > 500_000:
        s += 10                           # likely has staff writers
    elif med >= 1_000:
        s += 15
    if per_month and per_month >= 4:
        s += 25
    elif per_month and per_month >= 2:
        s += 15
    elif per_month and per_month >= 1:
        s += 8
    if trend and trend >= 1.3:
        s += 25
    elif trend and trend >= 0.9:
        s += 12
    elif trend:
        s -= 10                           # shrinking: cuts freelancers first
    if over:
        s += 10                           # has a repeatable winning format

    return {
        "url": url,
        "videos_sampled": len(rows),
        "median_views": int(med),
        "max_views": max(views),
        "uploads_per_month": per_month,
        "trend_new_vs_old": trend,
        "prospect_score": round(s),
        "overperformers": [{"views": o["views"], "mult": round(o["views"] / med, 1),
                            "id": o["id"], "title": o["title"][:70]} for o in over],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="*")
    ap.add_argument("--from-file")
    ap.add_argument("--recent", type=int, default=30)
    ap.add_argument("--json")
    args = ap.parse_args()

    targets = list(args.targets)
    if args.from_file:
        targets += [l.strip() for l in pathlib.Path(args.from_file).read_text().splitlines()
                    if l.strip() and not l.startswith("#")]
    if not targets:
        ap.error("give handles or --from-file")

    out = []
    for t in targets:
        u = norm(t)
        log(f"scoring {u} ...")
        out.append(score(u, args.recent))

    ranked = sorted([r for r in out if "error" not in r],
                    key=lambda r: -r["prospect_score"])
    print(f"\n{'score':>5} {'med views':>10} {'up/mo':>6} {'trend':>6}  channel")
    print("-" * 74)
    for r in ranked:
        print(f"{r['prospect_score']:>5} {r['median_views']:>10,} "
              f"{str(r['uploads_per_month'] or '?'):>6} {str(r['trend_new_vs_old'] or '?'):>6}  "
              f"{r['url'].split('/')[-1][:34]}")
    for r in out:
        if "error" in r:
            print(f"    ? {'':>10} {'':>6} {'':>6}  {r['url'].split('/')[-1][:34]}  ({r['error']})")

    if ranked:
        best = ranked[0]
        print(f"\ntop prospect: {best['url']}")
        for o in best["overperformers"][:3]:
            print(f"  {o['mult']}x median ({o['views']:,}) — {o['title']}")
        print("  ^ model the sample script on these, not on generic structure")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(out, indent=2))
        log(f"wrote {args.json}")


if __name__ == "__main__":
    main()
