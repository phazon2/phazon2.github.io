#!/usr/bin/env python3
"""Second, independent read of a video through Gemini's native video understanding.

Gemini ingests a YouTube URL directly — its own decode, sampling, and audio
path — so its reading fails differently from the local frames+transcript pass.
Feed it the video and the extraction prompt only; never the other pipeline's
output, or it stops being independent.

Usage:
    export GEMINI_API_KEY=...
    ./gemini_video.py <youtube-url> --prompt-file ../references/extraction-prompt.md
    ./gemini_video.py <youtube-url> --prompt "what commands are typed?" -o gemini.md

Stdlib only — no pip install.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")


def build_request(url, prompt, model, key, start=None, end=None):
    file_data = {"file_uri": url}
    part = {"file_data": file_data}
    if start or end:
        meta = {}
        if start:
            meta["start_offset"] = {"seconds": start}
        if end:
            meta["end_offset"] = {"seconds": end}
        part["video_metadata"] = meta

    body = {"contents": [{"parts": [part, {"text": prompt}]}]}
    req = urllib.request.Request(
        API.format(model=model),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    return req


def extract_text(payload):
    candidates = payload.get("candidates") or []
    if not candidates:
        # A prompt-level block has no candidates at all; surface why.
        feedback = payload.get("promptFeedback", payload)
        raise SystemExit(f"gemini returned no candidates: {json.dumps(feedback)[:800]}")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        reason = candidates[0].get("finishReason", "unknown")
        raise SystemExit(f"gemini returned an empty response (finishReason={reason})")
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url", help="Video URL (YouTube URLs are ingested natively)")
    ap.add_argument("--prompt", help="Inline extraction prompt")
    ap.add_argument("--prompt-file", help="Read the extraction prompt from a file")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"default: {DEFAULT_MODEL}")
    ap.add_argument("--start", type=int, help="Start offset in seconds")
    ap.add_argument("--end", type=int, help="End offset in seconds")
    ap.add_argument("-o", "--out", help="Write to a file instead of stdout")
    args = ap.parse_args()

    if bool(args.prompt) == bool(args.prompt_file):
        ap.error("pass exactly one of --prompt or --prompt-file")

    prompt = args.prompt
    if args.prompt_file:
        with open(args.prompt_file) as fh:
            prompt = fh.read()

    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise SystemExit(
            "no GEMINI_API_KEY (or GOOGLE_API_KEY) set.\n"
            "Continue single-sourced and label every claim SINGLE-SOURCE (watch)."
        )

    req = build_request(args.url, prompt, args.model, key, args.start, args.end)
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:800]
        raise SystemExit(f"gemini HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        raise SystemExit(f"gemini unreachable: {exc.reason}")

    text = extract_text(payload)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
