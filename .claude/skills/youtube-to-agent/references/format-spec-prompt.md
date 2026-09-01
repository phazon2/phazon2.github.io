Reverse-engineer this video into a **production specification** precise enough
to rebuild the format with different content. You are reading it as a
production designer, not a viewer.

Guess nothing. Where you cannot read a value off the screen, write `UNKNOWN`
with a timestamp. An invented number is worse than a missing one, because a
build will silently adopt it.

## SHOT LIST
Every visual change, as
`start -> end | duration_sec | what is on screen | how it entered`.
"How it entered" means hard cut, fade, slide, zoom, or none. Include shots
that only change the text while the image holds.

## TIMING
- total runtime
- number of distinct shots
- mean and range of shot duration
- cuts per minute
- how long the FIRST shot holds before the first cut

## TEXT ON SCREEN
For each text element, as
`text | position | approx size relative to frame height | colour | when it appears | how long it holds | animation`.
Note whether text appears **before, with, or after** the matching narration.
Note whether text is full sentences or fragments, and its capitalisation.

## LAYOUT
- aspect ratio
- where the subject sits in frame (thirds, centred, offset)
- how much of frame height the subject occupies
- safe margins — how close text gets to edges
- any persistent element: progress bar, logo, counter, caption strip

## PALETTE
Background, subject, text, and accent colours as approximate hex. Note how
many distinct colours the whole video uses.

## AUDIO
- is there narration, and is it human or synthetic (say which cues you used)
- speaking pace in words per minute
- music: present or not, and roughly what kind
- sound effects and where they land

## STRUCTURE
The segment order with timestamps: hook, promise, body items, recap, CTA.
Quote the hook verbatim. State how many seconds pass before the first piece
of real content.

## REPEATABLE TEMPLATE
The rules an editor would follow to make episode two — durations, ordering,
text conventions, and what changes per episode versus what stays fixed.
