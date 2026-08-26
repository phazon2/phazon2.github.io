Extract **everything in this video that could change what someone does in a
study session.** Another pass merges your output with ~105 sibling videos from
the same creator, so write for machine merging.

**Completeness beats brevity.** Length is not a cost here; a missed operational
detail is. If a video contains forty actionable specifics, return forty. Never
compress by dropping items, and never stop early because the list feels long.

## What counts as operational

Include anything that changes **what you do, when you do it, in what order, or
for how long**: techniques, sequences, timings, thresholds, quantities,
decision rules, diagnostic tests, error corrections, worked examples.

Capture **numbers exactly as stated** — durations, intervals, repetitions,
percentages, ratios, session lengths. A number is the most operational thing a
video can contain and the easiest to lose in paraphrase.

**Deprioritize** motivation, mindset talk, life lessons, and personal anecdote
*unless* they carry a concrete instruction. "Believe in yourself" is out.
"When you feel resistance, switch to a lower-order task for ten minutes" is in
— it names a trigger and an action.

## Output sections

### TECHNIQUES
For each technique, however minor, and including variants of ones the creator
has covered elsewhere:
- **name:** his term, verbatim
- **canonical:** the standard name if different (e.g. "spaced repetition",
  "elaborative interrogation", "interleaving"), else `same`
- **do:** numbered, executable steps. Enough that someone could follow them
  without the video. Include his exact numbers.
- **why:** the stated mechanism
- **when:** conditions, subjects, or stages it suits
- **when-not:** any stated conditions where it fails or should be avoided
- **timestamp:**

### PARAMETERS
Every specific quantity, as `parameter | value | context | timestamp`.
Examples: session length, break ratio, review interval, number of passes,
time-per-question, how many concepts per map. These merge into a settings
sheet, so extract them even when they also appear inside a technique above.

### DECISION-RULES
Every conditional instruction, as `if <condition> -> then <action> | timestamp`.
This is the highest-value section for building an actual study system: it is
what turns a list of techniques into something that runs.

### CLAIMS
Each falsifiable assertion, as `claim | evidence | timestamp`.

`evidence` is exactly one of:
- `STUDY` — a specific study, author, paper, or researcher is named
- `RESEARCH-VAGUE` — "studies show" / "the research says", nothing named
- `EXPERIENCE` — his own practice, students, or coaching
- `ASSERTED` — stated with no support offered

Never upgrade `RESEARCH-VAGUE` to `STUDY` because a claim sounds scientific.
This grading is metadata for later cross-checking, not a verdict on the claim.

### CONTRADICTS-COMMON-ADVICE
`common belief -> his position -> his stated reason`. Where he corrects
mainstream study advice.

### CORRECTS-HIS-OWN-PRIOR
Where he revises, softens, or reverses something he has said before —
"I used to say", "I was wrong about", "this is more nuanced than". Note the old
and new position. The merge pass needs these to resolve conflicts between
early and late videos by date rather than by guesswork.

### DIAGNOSTICS
Any test, self-check, or symptom he gives for telling whether you are doing
something correctly, as `symptom/test -> what it indicates -> what to change`.

### PREREQUISITES
`technique -> depends on`.

### SELLING
Timestamps where a course, coaching, or community is pitched, and the claim it
is attached to. Record plainly — a technique is not disqualified by sitting
near a pitch, but the merge should be able to see where the incentive is.

### UNCLEAR
Anything you could not make out, with a timestamp. Never fill a gap with what
advice of this kind usually says: a plausible invention is undetectable
downstream, whereas a labeled hole can be re-checked.
