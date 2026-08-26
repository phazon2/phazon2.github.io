#!/usr/bin/env python3
"""Analyze a video with Gemini — the one video path that works from a cloud container.

Local download (yt-dlp) is blocked from datacenter IPs: YouTube returns 429 /
IpBlocked. This script sidesteps that by making *Google's* servers fetch the
video, so nothing depends on this machine's IP reputation.

Two ingestion modes, picked automatically:

  YouTube URL  -> passed natively as file_uri; Google fetches it. No download.
  Anything else -> downloaded locally (yt-dlp), uploaded via the Files API,
                   polled until ACTIVE, then analyzed. Needed for Instagram,
                   TikTok, and local files, which the native path rejects.

Usage:
    export GEMINI_API_KEY=...              # aistudio.google.com/apikey
    ./gemini_video.py --list-models        # what this key can actually use
    ./gemini_video.py <youtube-url> --prompt-file ../references/extraction-prompt.md
    ./gemini_video.py <reel-url> --prompt "what happens on screen?" -o out.md
    ./gemini_video.py ./clip.mp4 --prompt "transcribe with timestamps"

Stdlib only — no pip install needed beyond yt-dlp for non-YouTube sources.
"""

import argparse
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://generativelanguage.googleapis.com"

# Model naming drifts fast. Override with --model or GEMINI_MODEL; if the name
# is wrong the script lists what the key can actually reach instead of guessing.
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

YOUTUBE_RE = re.compile(r"^https?://(www\.|m\.)?(youtube\.com/(watch|shorts|live)|youtu\.be/)")


def api(path, key, method="GET", body=None, headers=None, timeout=120):
    url = path if path.startswith("http") else f"{BASE}{path}"
    hdrs = {"x-goog-api-key": key}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            payload = json.loads(raw) if raw else {}
            return payload, dict(resp.headers)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:900]
        raise SystemExit(f"gemini HTTP {exc.code} on {method} {url}\n{detail}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"gemini unreachable: {exc.reason}")


def list_models(key):
    payload, _ = api("/v1beta/models?pageSize=200", key)
    rows = []
    for m in payload.get("models", []):
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        rows.append((m["name"].removeprefix("models/"), m.get("inputTokenLimit", "?")))
    return sorted(rows)


def is_youtube(src):
    return bool(YOUTUBE_RE.match(src))


def download(src, workdir):
    """Fetch a non-YouTube source locally so it can go through the Files API."""
    if not shutil.which("yt-dlp"):
        raise SystemExit("yt-dlp not found — needed for non-YouTube sources (pip install yt-dlp)")
    out = os.path.join(workdir, "video.%(ext)s")
    print(f"downloading {src} ...", file=sys.stderr)
    proc = subprocess.run(
        ["yt-dlp", "-f", "mp4/best", "-o", out, "--no-playlist", src],
        capture_output=True, text=True,
    )
    files = [f for f in os.listdir(workdir) if f.startswith("video.")]
    if proc.returncode != 0 or not files:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-3:]
        raise SystemExit(
            "download failed:\n  " + "\n  ".join(tail) +
            "\n\nInstagram/TikTok often need login cookies, and datacenter IPs are\n"
            "frequently blocked outright. Retry from a residential connection, or\n"
            "pass an already-downloaded local file instead."
        )
    return os.path.join(workdir, files[0])


def upload(path, key):
    """Resumable upload to the Files API, then wait for server-side processing."""
    size = os.path.getsize(path)
    mime = mimetypes.guess_type(path)[0] or "video/mp4"
    print(f"uploading {os.path.basename(path)} ({size/1e6:.1f} MB, {mime}) ...", file=sys.stderr)

    _, headers = api(
        "/upload/v1beta/files", key, method="POST",
        body={"file": {"display_name": os.path.basename(path)}},
        headers={
            "X-Goog-Upload-Protocol": "resumable",
            "X-Goog-Upload-Command": "start",
            "X-Goog-Upload-Header-Content-Length": str(size),
            "X-Goog-Upload-Header-Content-Type": mime,
        },
    )
    session = headers.get("X-Goog-Upload-URL") or headers.get("x-goog-upload-url")
    if not session:
        raise SystemExit("Files API did not return an upload URL")

    with open(path, "rb") as fh:
        req = urllib.request.Request(
            session, data=fh.read(), method="POST",
            headers={
                "Content-Length": str(size),
                "X-Goog-Upload-Offset": "0",
                "X-Goog-Upload-Command": "upload, finalize",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=1800) as resp:
                info = json.load(resp)["file"]
        except urllib.error.HTTPError as exc:
            raise SystemExit(f"upload failed HTTP {exc.code}: {exc.read().decode(errors='replace')[:500]}")

    # Video is transcoded server-side; generateContent rejects it until ACTIVE.
    name, deadline = info["name"], time.time() + 900
    while info.get("state") == "PROCESSING":
        if time.time() > deadline:
            raise SystemExit(f"{name} stuck in PROCESSING after 15 min")
        time.sleep(5)
        info, _ = api(f"/v1beta/{name}", key)
        print(f"  state={info.get('state')}", file=sys.stderr)
    if info.get("state") != "ACTIVE":
        raise SystemExit(f"upload ended in state {info.get('state')}: {info.get('error')}")
    return info["uri"], mime


def analyze(part, prompt, model, key):
    body = {"contents": [{"parts": [part, {"text": prompt}]}]}
    payload, _ = api(f"/v1beta/models/{model}:generateContent", key,
                     method="POST", body=body, timeout=900)

    candidates = payload.get("candidates") or []
    if not candidates:
        feedback = payload.get("promptFeedback", payload)
        raise SystemExit(f"no candidates returned: {json.dumps(feedback)[:600]}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise SystemExit(f"empty response (finishReason={candidates[0].get('finishReason')})")
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", nargs="?", help="YouTube URL, other video URL, or local file")
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"default: {DEFAULT_MODEL}")
    ap.add_argument("--list-models", action="store_true",
                    help="list models this key can use, then exit")
    ap.add_argument("--start", type=int, help="start offset, seconds (YouTube only)")
    ap.add_argument("--end", type=int, help="end offset, seconds (YouTube only)")
    ap.add_argument("--keep", action="store_true", help="keep the downloaded file")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit(
            "No GEMINI_API_KEY set. Get a free key at https://aistudio.google.com/apikey\n"
            "then:  export GEMINI_API_KEY=..."
        )

    if args.list_models:
        for name, limit in list_models(key):
            print(f"{name:<45} {limit:>10} input tokens")
        return

    if not args.source:
        ap.error("source is required (unless --list-models)")
    if bool(args.prompt) == bool(args.prompt_file):
        ap.error("pass exactly one of --prompt or --prompt-file")

    prompt = args.prompt
    if args.prompt_file:
        with open(args.prompt_file) as fh:
            prompt = fh.read()

    workdir = None
    try:
        if is_youtube(args.source):
            part = {"file_data": {"file_uri": args.source}}
            if args.start or args.end:
                meta = {}
                if args.start:
                    meta["start_offset"] = {"seconds": args.start}
                if args.end:
                    meta["end_offset"] = {"seconds": args.end}
                part["video_metadata"] = meta
            print("mode: native YouTube ingestion (Google fetches it)", file=sys.stderr)
        else:
            if args.start or args.end:
                print("warning: --start/--end apply to YouTube sources only; ignored",
                      file=sys.stderr)
            path = args.source
            if "://" in args.source:
                workdir = tempfile.mkdtemp(prefix="gemvid-")
                path = download(args.source, workdir)
            elif not os.path.exists(path):
                raise SystemExit(f"no such file: {path}")
            uri, mime = upload(path, key)
            part = {"file_data": {"file_uri": uri, "mime_type": mime}}
            print("mode: Files API upload", file=sys.stderr)

        try:
            text = analyze(part, prompt, args.model, key)
        except SystemExit as exc:
            if "404" in str(exc) or "not found" in str(exc).lower():
                names = "\n  ".join(n for n, _ in list_models(key))
                raise SystemExit(f"{exc}\n\nModels available to this key:\n  {names}")
            raise
    finally:
        if workdir and not args.keep:
            shutil.rmtree(workdir, ignore_errors=True)

    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
