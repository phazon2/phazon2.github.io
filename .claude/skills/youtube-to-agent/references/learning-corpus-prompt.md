Extract the **actionable content** of this video on learning and studying.
Another pass will merge your output with ~100 sibling videos from the same
creator, so write for machine merging, not for a human reader. Be terse.

Output these sections, in this order, omitting any that are genuinely empty.

## TECHNIQUES
For each concrete, executable technique:
- **name:** the creator's own term, verbatim if they name one
- **canonical:** the standard/common name if it differs (e.g. "spaced
  repetition", "elaborative interrogation", "Feynman technique"), else `same`
- **do:** the actual steps, numbered. Executable, not motivational.
- **why:** the stated mechanism — *why* it is claimed to work
- **when:** the conditions or subjects it is claimed to suit
- **timestamp:** where it starts

## CLAIMS
Each falsifiable assertion, one line each, as `claim | evidence | timestamp`.

For `evidence`, use exactly one of:
- `STUDY` — a specific named study, author, or paper is cited
- `RESEARCH-VAGUE` — "studies show" / "research says" with nothing named
- `EXPERIENCE` — the creator's own practice, students, or coaching
- `ASSERTED` — stated with no support offered

This split is the whole point. Do not upgrade `RESEARCH-VAGUE` to `STUDY`
because a claim sounds scientific.

## CONTRADICTS-COMMON-ADVICE
Anything presented as correcting a widespread belief, as
`common belief -> creator's position -> stated reason`. These are the highest
value lines in the corpus: they are where this creator's framework actually
differs from generic study advice, and where the merge pass will find real
conflicts to resolve.

## PREREQUISITES
Techniques presented as depending on another technique, skill, or prior video.
Format: `technique -> depends on`.

## SELLING
Any point where the video pitches a course, coaching, community, or product.
Note the timestamp and what claim it is attached to. Record it plainly; a
technique is not disqualified by being adjacent to a pitch, but a synthesis
should be able to see where the incentive sits.

## UNCLEAR
Anything you could not make out, with a timestamp. Never fill a gap with what
advice of this kind usually says — a plausible invention is worse than a
labeled hole, because the merge pass cannot detect it.
