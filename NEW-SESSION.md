# Starting a session that can watch videos

## 1. Set the API key BEFORE opening the session

claude.ai/code → environment selector (cloud icon above the message box)
→ **Custom** → Environment variables:

```
GEMINI_API_KEY=<key from aistudio.google.com/apikey>
```

**This must be done first.** Environment variables are copied once, at session
start — a running session never sees a value added afterwards, and no amount of
re-asking helps. Add it, then open a *new* session.

## 2. Point the session at this branch

Repository: `phazon2/phazon2.github.io`
Branch: `claude/instagram-reel-reference-g0ybei`

The tooling lives on that branch only; `main` does not have it.

## 3. Paste this as the first message

```
Check out branch claude/instagram-reel-reference-g0ybei, then read
.claude/skills/youtube-to-agent/SKILL.md.

You can watch YouTube videos. Do NOT try yt-dlp — YouTube blocks this
container's datacenter IP (429 / IpBlocked, not fixable by allowlist).
Use scripts/gemini_video.py, which passes the URL to Gemini so Google's
servers fetch it.

Verify it works first:
  python3 .claude/skills/youtube-to-agent/scripts/gemini_video.py --list-models

Then analyse: <paste video URLs>
```

## What each script does

| Script | Purpose |
| --- | --- |
| `gemini_video.py` | one video → analysis. `--start/--end` for segments |
| `batch_videos.py` | whole playlist, resumable, failure-isolated |
| `merge_corpus.py` | aggregate extractions, dedupe, count evidence grades |
| `rank_methods.py` | rank business methods by barrier-to-try |
| `score_channel.py` | score a channel as a prospect from public data |
| `prospect.py` | creator → outreach package |
| `compare_specs.py` | separate format from one channel's quirks |
| `make_episode.py` | episode JSON → finished MP4 |

## Things that will otherwise waste an hour

- **Gemini's ceiling is 1,048,576 tokens ≈ 3.1 hours of video** at ~92.8
  tokens/second. Longer videos fail — and the first failure may report
  `PERMISSION_DENIED`, which looks exactly like a private video. Retry before
  concluding it is inaccessible. The fix is chunking with `--start/--end`;
  stop when a chunk returns empty.
- **Native URL ingestion is YouTube-only.** Instagram, TikTok and local files
  are downloaded and pushed through the Files API instead — the script routes
  automatically, but the download half can still be blocked.
- **Metadata succeeding is not content succeeding.** YouTube will serve titles
  and playlist listings while refusing the payload.
- **Long videos are under-extracted.** Measured across 105 videos: 1.19
  lines/min on a 122-minute video versus 24 lines/min on a 2.5-minute one.
  Chunk long-form rather than trusting one pass.
- **`corpus/` and `build/` are gitignored** — this repo is public and the
  extractions are third-party derivative content. Output does not travel
  between sessions; hand it back as files.

## Costs, measured

| | |
| --- | --- |
| ~92.8 tokens per second of video | |
| 10-min video | ~$0.02 (flash-lite) |
| 4-hour livestream, chunked | ~$1.20–1.50 |
| 105-video playlist | ~$6.50 |
