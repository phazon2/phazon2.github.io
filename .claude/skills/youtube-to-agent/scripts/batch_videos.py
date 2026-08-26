#!/usr/bin/env python3
"""Run one extraction prompt across a whole playlist, resumably.

Built for corpus work: dozens of videos where the value is the synthesized
whole, not any single summary. Three properties matter at that scale.

Resumable — one output file per video, existing files skipped. A run that
dies at video 80 is re-run for free, and cost is never paid twice.

Bounded concurrency — free-tier keys allow ~15 requests/minute. Default 3
workers stays well inside that; raise only on a paid key.

Failures isolated — one bad video (private, region-locked, too long) records
its error and the run continues. A 106-video job must not die on video 12.

Usage:
    yt-dlp --flat-playlist --print "%(id)s|%(title)s" <playlist> > list.txt
    ./batch_videos.py list.txt --prompt-file p.md --out-dir corpus/ --workers 3
    ./batch_videos.py list.txt --prompt-file p.md --out-dir corpus/ --limit 6
"""

import argparse
import concurrent.futures as cf
import os
import pathlib
import re
import subprocess
import sys
import threading

HERE = pathlib.Path(__file__).parent
PRINT_LOCK = threading.Lock()


def log(msg):
    with PRINT_LOCK:
        print(msg, file=sys.stderr, flush=True)


def slug(text, maxlen=60):
    s = re.sub(r"[^\w\s-]", "", text).strip()
    return re.sub(r"[\s_]+", "-", s)[:maxlen].strip("-").lower() or "untitled"


def parse(path, limit=None):
    """Accept '<id>|<title>' or the richer '<idx>|<dur>|<id>|<title>' form."""
    items = []
    for line in pathlib.Path(path).read_text().splitlines():
        if "|" not in line:
            continue
        f = line.split("|")
        if len(f) >= 4:
            vid, title = f[2].strip(), f[3].strip()
        else:
            vid, title = f[0].strip(), f[1].strip()
        if vid and vid != "NA":
            items.append((vid, title))
    return items[:limit] if limit else items


def run_one(idx, total, vid, title, args):
    out = pathlib.Path(args.out_dir) / f"{idx:03d}-{slug(title)}.md"
    if out.exists() and out.stat().st_size > 0:
        log(f"[{idx:3d}/{total}] skip (done)  {title[:55]}")
        return ("skipped", 0)

    cmd = [
        sys.executable, str(HERE / "gemini_video.py"),
        f"https://www.youtube.com/watch?v={vid}",
        "--prompt-file", args.prompt_file,
        "--model", args.model,
        "-o", str(out),
    ]
    log(f"[{idx:3d}/{total}] start        {title[:55]}")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)

    usage = ""
    for line in proc.stderr.splitlines():
        if line.startswith("[usage]"):
            usage = line
    tokens = 0
    m = re.search(r"total=([\d,]+)", usage)
    if m:
        tokens = int(m.group(1).replace(",", ""))

    if proc.returncode != 0 or not out.exists():
        # Record the failure instead of losing it, but leave no partial file
        # behind — an empty .md would be skipped as "done" on the next run.
        out.unlink(missing_ok=True)
        err = (proc.stderr or proc.stdout).strip().splitlines()
        tail = err[-1][:160] if err else "unknown error"
        (pathlib.Path(args.out_dir) / "_failures.log").open("a").write(
            f"{idx:03d}\t{vid}\t{title}\t{tail}\n"
        )
        log(f"[{idx:3d}/{total}] FAIL         {title[:45]} :: {tail[:70]}")
        return ("failed", 0)

    # Prepend provenance so a synthesis pass can always cite the source.
    body = out.read_text()
    out.write_text(
        f"---\nvideo_id: {vid}\ntitle: {title!r}\n"
        f"url: https://www.youtube.com/watch?v={vid}\nindex: {idx}\n---\n\n{body}"
    )
    log(f"[{idx:3d}/{total}] ok {tokens:>8,} tok  {title[:45]}")
    return ("ok", tokens)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("list_file")
    ap.add_argument("--prompt-file", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--model", default="gemini-3.5-flash-lite")
    ap.add_argument("--workers", type=int, default=3, help="keep <=3 on free tier")
    ap.add_argument("--limit", type=int, help="only the first N (pilot runs)")
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args()

    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        raise SystemExit("no GEMINI_API_KEY set")

    pathlib.Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    items = parse(args.list_file, args.limit)
    total = len(items)
    log(f"{total} videos -> {args.out_dir}  (model={args.model}, workers={args.workers})\n")

    tally, tokens = {"ok": 0, "failed": 0, "skipped": 0}, 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(run_one, i, total, v, t, args)
                   for i, (v, t) in enumerate(items, 1)]
        for f in cf.as_completed(futures):
            try:
                status, tok = f.result()
            except Exception as exc:
                status, tok = "failed", 0
                log(f"worker crashed: {type(exc).__name__}: {exc}")
            tally[status] += 1
            tokens += tok

    log(f"\n{'='*58}")
    log(f"ok={tally['ok']}  failed={tally['failed']}  skipped={tally['skipped']}")
    log(f"tokens={tokens:,}  approx cost=${tokens * 0.30 / 1e6:.3f} (flash-lite input rate)")
    if tally["failed"]:
        log(f"failures logged to {args.out_dir}/_failures.log — re-run to retry them")


if __name__ == "__main__":
    main()
