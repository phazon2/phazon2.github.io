#!/usr/bin/env python3
"""Produce a ready-to-send outreach package for one YouTube creator.

Implements the scriptwriting method from video 058 of the ai-business corpus:
pick creators in a niche you understand, send a free sample script, convert to
paid in 2-3 weeks. Everything up to the send is automated here.

The send is deliberately NOT automated. It needs your own social accounts, and
scripted DMs violate platform terms — a ban costs more than the outreach earns.
This produces text you paste yourself, which takes a couple of minutes and no
real concentration.

Per creator it emits one markdown file containing:
  1. catalogue analysis  — niche, recurring formats, what their titles promise
  2. hook + pacing profile — how their best videos open and hold attention
  3. a full sample script — on a topic they have not covered but should
  4. a DM draft           — short, specific, no pitch beyond the free sample

Usage:
    export GEMINI_API_KEY=...
    ./prospect.py "https://www.youtube.com/@channelhandle" --out-dir outreach/
    ./prospect.py @handle1 @handle2 --out-dir outreach/ --recent 12
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).parent


def log(m):
    print(m, file=sys.stderr, flush=True)


def normalize(target):
    if target.startswith("http"):
        return target.rstrip("/")
    return f"https://www.youtube.com/{target.lstrip('@') and '@' + target.lstrip('@')}"


def recent_videos(channel_url, n):
    """Metadata only — this path is not IP-blocked the way caption fetch is."""
    url = channel_url if "/videos" in channel_url else channel_url + "/videos"
    proc = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--no-warnings", "--playlist-end", str(n),
         "--print", "%(id)s|%(duration)s|%(view_count)s|%(title)s", url],
        capture_output=True, text=True, timeout=600,
    )
    out = []
    for line in proc.stdout.splitlines():
        f = line.split("|", 3)
        if len(f) >= 4 and f[0].strip():
            out.append({"id": f[0], "dur": f[1], "views": f[2], "title": f[3]})
    if not out:
        raise SystemExit(f"could not enumerate {url}\n{proc.stderr[-400:]}")
    return out


def gemini(prompt_text, video_url, model, out_path):
    cmd = [sys.executable, str(HERE / "gemini_video.py"), video_url,
           "--prompt", prompt_text, "--model", model, "-o", str(out_path)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        return None, (err[-1][:200] if err else "unknown")
    return out_path.read_text(), None


ANALYSIS = """Analyze this video as a scriptwriter studying a potential client.

Report:
1. NICHE — what specific audience and problem, in one line.
2. HOOK — transcribe the first 30 seconds verbatim, then name the technique used.
3. STRUCTURE — the segment order with approximate timestamps.
4. VOICE — sentence length, vocabulary level, humour, use of "you", pacing.
   Quote three sentences that are most characteristic of how they talk.
5. RETENTION DEVICES — open loops, pattern interrupts, callbacks; where each sits.
6. WEAKNESS — the single clearest scriptwriting weakness. Be specific and
   concrete; a vague criticism is useless in outreach and reads as flattery
   in reverse.
7. GAP — one topic their audience clearly wants that this video shows they
   have not covered well.

Be precise and quote directly. This feeds a sample script written in their voice."""


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("targets", nargs="+", help="channel URLs or @handles")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--recent", type=int, default=8, help="videos to list")
    ap.add_argument("--analyze", type=int, default=2, help="videos to deep-analyze")
    ap.add_argument("--model", default="gemini-3.6-flash")
    args = ap.parse_args()

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise SystemExit("no GEMINI_API_KEY set")

    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    for target in args.targets:
        url = normalize(target)
        slug = re.sub(r"[^\w-]", "-", url.split("/")[-1]).strip("-").lower()
        log(f"\n=== {url} ===")
        try:
            vids = recent_videos(url, args.recent)
        except SystemExit as e:
            log(str(e))
            continue
        log(f"  {len(vids)} recent videos")

        # Analyze the most-viewed recent videos: those are the ones whose
        # formula is working, and the ones the creator is most attached to.
        ranked = sorted(vids, key=lambda v: int(v["views"]) if v["views"].isdigit() else 0,
                        reverse=True)[:args.analyze]
        analyses = []
        for v in ranked:
            log(f"  analyzing: {v['title'][:60]}")
            tmp = out / f".{slug}-{v['id']}.analysis.md"
            text, err = gemini(ANALYSIS, f"https://www.youtube.com/watch?v={v['id']}",
                               args.model, tmp)
            if err:
                log(f"    failed: {err}")
                continue
            analyses.append({"title": v["title"], "views": v["views"], "text": text})
            tmp.unlink(missing_ok=True)

        if not analyses:
            log("  no analyses succeeded; skipping")
            continue

        pkg = out / f"{slug}.md"
        with pkg.open("w") as fh:
            fh.write(f"# Outreach package — {url}\n\n")
            fh.write("## Recent catalogue\n\n| views | duration | title |\n|---|---|---|\n")
            for v in vids:
                mins = f"{int(v['dur'])//60}m" if v["dur"].isdigit() else "?"
                fh.write(f"| {v['views']} | {mins} | {v['title'][:70]} |\n")
            for a in analyses:
                fh.write(f"\n---\n\n## Analysis: {a['title']}\n_{a['views']} views_\n\n{a['text']}\n")
            fh.write("\n---\n\n## NEXT\n"
                     "Sample script and DM are generated in the follow-up step,\n"
                     "which reads the WEAKNESS and GAP fields above.\n")
        log(f"  wrote {pkg}")


if __name__ == "__main__":
    main()
