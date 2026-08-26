---
name: youtube-to-agent
description: Turn a video tutorial (YouTube, or any yt-dlp-supported URL) into a Claude Code agent, skill, or slash command. Watches the video twice through independent pipelines — local frames+transcript via /watch, and Gemini's native video understanding — then reconciles both readings into a cross-checked spec before writing anything. Use when the user shares a video URL and wants the workflow in it built, replicated, or automated.
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

### 1. Ingest locally with `/watch`

Requires the `claude-video` plugin:

```
/plugin marketplace add bradautomates/claude-video
/plugin install watch@claude-video
```

Then run it at a fidelity that can actually read on-screen text — tutorials
are full of terminal output, file paths, and config that never gets spoken:

```
/watch <URL> --detail balanced --resolution 1024 <question>
```

Ask for the mechanism, not a summary: exact commands typed, file paths and
their contents, tool and plugin names, the order of operations, and anything
shown on screen but never said aloud. Note the working directory `/watch`
prints — the frames and timestamped transcript stay there for follow-ups.

Reach for `--start/--end` when only one segment matters, and `--timestamps`
to go back for a specific frame once you know what you are looking for.

### 2. Ingest independently with Gemini

Gemini ingests a YouTube URL natively — its own decode, its own sampling, its
own audio path. That independence is the entire point, so do **not** feed it
the `/watch` output or your notes from step 1; a second opinion that has read
the first is not a second opinion.

```bash
export GEMINI_API_KEY=...   # or GOOGLE_API_KEY
scripts/gemini_video.py <URL> --prompt-file references/extraction-prompt.md
```

Ask it the same questions from step 1, worded the same way. If the key is
missing or the call fails, say so and continue single-sourced — every claim in
the spec is then `SINGLE-SOURCE (watch)`, which is a weaker artifact, not an
invisible one.

### 3. Reconcile into a spec

Put the two readings side by side and label **every** claim. Use
`references/spec-template.md`.

| Label | Meaning | What to do |
|---|---|---|
| `CONFIRMED` | Both pipelines report it, compatibly | Build on it |
| `SINGLE-SOURCE (watch \| gemini)` | Only one reports it | Keep, flag; likely a real sampling gap, not a fabrication |
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
