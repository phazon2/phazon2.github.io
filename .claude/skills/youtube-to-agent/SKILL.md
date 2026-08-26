---
name: youtube-to-agent
description: Turn a video into a Claude Code agent, skill, or slash command — or just extract what a video actually says and shows. Reads it through Gemini (server-side fetch, works from cloud containers) and, where the network allows, a second local frames+transcript pass via /watch, reconciling both into a cross-checked spec before writing anything. Use when the user shares a YouTube/Instagram/TikTok URL or local video and wants it analyzed, or the workflow in it built or automated.
---

# Video tutorial → Claude Code agent

A tutorial video is a lossy source. Transcripts drop what was only shown on
screen; frame sampling drops what was only said between frames; and a single
model summarizing either one will confidently invent the parts it missed. The
failure mode is not "the agent is wrong," it is "the agent looks right and
silently encodes a step the video never contained."

So watch the video twice, through pipelines that fail differently, and let
disagreement surface as a finding rather than get averaged away.

## The pipeline

### 0. Check which legs are available here

Run this first. It decides whether you get one pipeline or two:

```bash
command -v yt-dlp ffmpeg                       # local leg needs both
yt-dlp --skip-download --print "%(title)s" "<url>"   # and an unblocked IP
```

**YouTube blocks datacenter IPs.** From a cloud container (Claude Code on the
web, CI, a VPS) the local leg returns `HTTP 429` / `IpBlocked` no matter which
player client or impersonation target you try — it is IP reputation, not
configuration. On a laptop with a residential connection it works fine.

So the leg availability is environmental, and you must state which you got:

| Environment | Gemini leg | `/watch` leg | Result |
|---|---|---|---|
| Local machine, residential IP | ✅ | ✅ | true dual-pipeline |
| Cloud container | ✅ | ❌ blocked | single-sourced, label it |

Never present a single-leg run as cross-checked.

### 1. Ingest with Gemini (primary — survives IP blocks)

Gemini fetches the video on Google's servers, so nothing depends on this
machine's IP. This is the leg that works everywhere.

```bash
export GEMINI_API_KEY=...                      # aistudio.google.com/apikey
scripts/gemini_video.py --list-models          # naming drifts; check, don't guess
scripts/gemini_video.py <URL> --prompt-file references/extraction-prompt.md -o gemini.md
```

The script routes by source automatically:

- **YouTube** → passed natively as `file_uri`; no download. `--start/--end`
  narrow to a segment.
- **Instagram, TikTok, local files** → downloaded, uploaded via the Files API,
  polled until `ACTIVE`. Native URL ingestion is **YouTube-only**; everything
  else must go through Files.

Free-tier keys are Flash-class and rate-limited (~15 RPM), which is ample for
analyzing videos one at a time.

### 2. Ingest with `/watch` (second leg, when the network allows)

Only meaningful when step 0 showed the local leg works. Requires the plugin:

```
/plugin marketplace add bradautomates/claude-video
/plugin install watch@claude-video
```

```
/watch <URL> --detail balanced --resolution 1024 <question>
```

Use a resolution that can read on-screen text — tutorials are full of terminal
output, paths, and config that is never spoken. Ask for the mechanism, not a
summary. Note the working directory it prints; frames and the timestamped
transcript stay there for follow-ups (`--timestamps` to revisit a moment).

Do **not** show it the Gemini output. A second opinion that has read the first
is not a second opinion.

**Independence has degrees, and it collapses for non-YouTube sources.** On
YouTube the two legs fetch separately — genuinely independent. For Instagram or
TikTok, both legs end up reading the *same downloaded file*, so a truncated or
corrupted download poisons both identically. Agreement there is weaker
evidence; say so in the spec rather than claiming a clean cross-check.

### 3. Reconcile into a spec

Put the two readings side by side and label **every** claim. Use
`references/spec-template.md`.

| Label | Meaning | What to do |
|---|---|---|
| `CONFIRMED` | Both pipelines report it, compatibly | Build on it |
| `SINGLE-SOURCE (watch \| gemini)` | Only one reports it, or only one leg ran | Keep, flag; a sampling gap or a blocked leg, not a fabrication |
| `CONFLICT` | They disagree on substance | Resolve before building |

Two claims that differ only in wording are one `CONFIRMED` claim — reconcile
at the level of meaning, not of string equality.

Resolve conflicts by evidence, in this order:

1. **Go back to the video.** `--timestamps` on the disputed moment, at
   `--resolution 1024`. A frame showing the actual command settles it.
2. **Check the primary source.** A repo, doc page, or CLI `--help` outranks
   both pipelines — the video may simply be out of date.
3. **If neither settles it,** leave it `CONFLICT` in the spec, pick the safer
   reading, and say in the handoff which one you took and why.

Never resolve a conflict by picking the more plausible-sounding option. That
is the exact failure this whole pipeline exists to prevent.

### 4. Build from the spec, not from the video

Write the artifact — subagent, skill, or slash command — using the spec as the
only input. Choose the form by what the video actually teaches: a repeatable
judgment call wants a skill, a delegated end-to-end task wants a subagent, a
fixed sequence wants a command.

`CONFIRMED` claims become behavior. `SINGLE-SOURCE` and `CONFLICT` claims
become behavior too — but each carries a comment naming its status, so the
next person editing the file knows which lines rest on one pipeline's word.

Anything the video assumes but never shows (credentials, prerequisites,
project layout) is a gap, not a detail to invent. Name it in the handoff.

### 5. Hand off

Report: what was built and where, the confirmed/single-source/conflict counts,
every unresolved conflict with the reading you took, and every gap the video
left open. Then verify — run the thing on a real input. A tutorial-derived
agent that has never executed is a transcript with frontmatter.
