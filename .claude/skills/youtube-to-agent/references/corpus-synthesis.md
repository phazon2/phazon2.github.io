# Merging a single-creator corpus

Input: one extraction file per video (see `learning-corpus-prompt.md`).
Output: one technique base. Not 106 summaries — those are the raw material,
and shipping them unmerged is shipping the problem.

## The failure mode this exists to prevent

A single creator repeats themselves. Across 100+ videos the same technique
appears 30 times with slightly different wording. Two things go wrong if you
merge naively:

1. **Repetition reads as corroboration.** It is not. Thirty mentions by one
   person is *one* source stated thirty times. Never let a frequency count
   stand in for evidence — an unsupported claim repeated often is still
   unsupported, and volume makes it feel more true, not more true.
2. **The framework becomes invisible.** Deduplicating to a flat technique list
   loses the thing worth having: how the pieces depend on each other, and
   where this creator diverges from mainstream advice.

## Merge procedure

**Dedupe on `canonical`, not `name`.** One creator renames standard
techniques constantly; the canonical field is what collapses them.

For each merged technique record:
- the fullest `do` steps found across all videos (later videos usually refine
  earlier ones — prefer the most recent, note if it *contradicts* the earlier)
- `mention_count` and the source video list — as reach, explicitly **not** as
  evidence weight
- the strongest evidence grade any video offered for it, and which video

**Then find the self-contradictions.** Where video 12 and video 80 give
incompatible instructions for the same canonical technique, that is a real
finding — either a framework that evolved, or advice that is not stable.
Record both, with dates. Do not silently prefer the newer one.

**Keep `CONTRADICTS-COMMON-ADVICE` intact.** Merged and deduped, this becomes
the actual thesis of the corpus — the part that differs from generic study
advice, and the part most worth testing against outside sources.

## Evidence discipline

Report the grade distribution over the whole corpus: how many techniques rest
on `STUDY`, how many on `RESEARCH-VAGUE`, `EXPERIENCE`, or `ASSERTED`. That
ratio is the corpus's own credibility statement, and it should be visible in
the output rather than inferred by a reader.

**One creator is one source.** A corpus like this documents a *framework*, not
a consensus, no matter how internally consistent it is — internal consistency
is what a single point of view produces by construction. Anything you plan to
act on that rests on `RESEARCH-VAGUE` or `ASSERTED` should be checked against
primary literature before it becomes a habit. Where the creator names a real
study, verifying that the study says what they claim is cheap and occasionally
surprising.

Label the output as one framework, cross-checked or not. A technique base that
presents itself as settled science is wrong even when every technique in it
happens to work.
