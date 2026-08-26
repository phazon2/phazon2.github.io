# Spec: <artifact name>

**Source:** <video URL> · <title> · <channel> · <duration>
**Pipelines:** `/watch` <detail level> · Gemini <model> (or: Gemini SKIPPED — reason)
**Target artifact:** subagent | skill | slash command

## Claims

Every claim carries a label. No unlabeled lines.

| # | Claim | Label | Evidence |
|---|-------|-------|----------|
| 1 | `/plugin install watch@claude-video` | CONFIRMED | watch 0:42 frame · gemini 0:40 |
| 2 | Frames extracted at 512px by default | SINGLE-SOURCE (gemini) | gemini 1:15; not visible in sampled frames |
| 3 | Reconciliation happens before spec, not after | CONFLICT | watch: before · gemini: after — see below |

## Conflicts

### C1 — <one-line description>
- **watch says:** … (timestamp)
- **gemini says:** … (timestamp)
- **Re-check:** what was pulled at higher resolution / which primary source was consulted
- **Resolution:** which reading was taken, and why. If unresolved, say so and
  name the safer option chosen.

## Gaps

Things the tutorial depends on but never demonstrates — credentials, prior
setup, project layout, versions. These are handoff items, not details to fill in.

## Build plan

What gets written, where, and which claim numbers drive each behavior.
Carry the label into the artifact as a comment wherever a behavior rests on a
SINGLE-SOURCE or CONFLICT claim.

## Verification

The real input this was run against, and what happened.
