---
name: creator-outreach
description: Find a YouTube creator whose audience is asking for something they do not sell, then build that thing. Screens candidate channels on whether their viewers ask for help (not on subscriber count), harvests and clusters their comments into demand clusters with verbatim evidence, and builds the product. Use when prospecting creators for a digital-product partnership, researching what an audience actually wants, or picking which creator to approach. Read "What this pipeline does not prove" before treating a demand report as a reason to launch.
---

# Creator outreach — demand-driven prospecting

Built 2026-09-14 while testing the "growth operator" method from the Side Hustle Summit
videos (see the Notion page *📹 Watched Video Findings*). The method's own version of this
work is manual: watch videos, read comments, guess. That is a week per creator, or a guess
from three videos. Comments are a JSON endpoint, so neither is necessary.

## What this pipeline does not prove

**It proves the audience wants *something*. It does not prove they want yours, and it says
nothing about whether they will pay.** Everything below measures demand for a *topic*, from
people typing free comments. Willingness to pay is a separate question this tooling cannot
answer, and conflating the two is the failure this section exists to prevent.

Three consequences, learned by building the whole sequence the wrong way round first:

**Conversion is the bottleneck, not acceptance.** A creator posting a link converts perhaps
1–2% of viewers to a click and 1–3% of those to a sale. On a typical post that is 0–2 sales,
not a business. A "yes" from a creator does not fix a product nobody has bought — it just
splits nothing, and spends a relationship doing it. Measure **sales**, never reply rate.

**Pure revenue-share selects for the wrong yes.** A creator hears "let's split the revenue"
and reads "unpaid work on an unproven product". The ones who accept are disproportionately
those with no better offers, which usually means an audience that does not convert. Offer a
choice — a tracked affiliate link, or a flat licence fee — so the yes is informative.

**No tracking kills deals on its own.** Without an affiliate link the creator has to trust a
stranger's spreadsheet for the numbers. Use a platform with native affiliate dashboards
(Gumroad, Lemon Squeezy) so they see their own figures.

**The cheap way to close the gap:** list the product yourself somewhere with its own search
traffic — Etsy for templates, Gumroad for the file — and get one sale from a stranger before
approaching anyone. Then the pitch carries a conversion rate instead of an assumption. This
costs roughly nothing and needs no audience, but it does need an account and a payout method,
so it is the operator's job, not the agent's.

**Lifetime views are not current reach.** A video with 744,894 views accumulated over two years
may reach very few people this month. The API gives no time series, so treat a big number as
an unverified maximum, and never repeat it to the creator as evidence — they can check their
own analytics in seconds.

## Outreach legality, briefly

Commercial email needs real sender identification and a working opt-out — US CAN-SPAM and
Chile's Ley 19.496 both want this. Low volume plus genuine personalisation behaves completely
differently from two hundred identical sends: the latter is what gets a domain flagged and a
personal mailbox throttled. Cap the sequence at two touches, send by hand, honour every "no"
immediately. Never automate the send: scripted outreach at volume violates platform terms, and
a ban costs more than the outreach earns.

## The pipeline

```
shortlist.py        search + screen candidates    -> shortlist.md
demand_harvest.py   harvest + cluster one channel -> <channel>.demand.md
build_workbook.py   build the product             -> product .xlsx
verify_workbook.py  check the product's formulas  -> pass/fail
```

```bash
export YOUTUBE_API_KEY=...   # Google Cloud, YouTube Data API v3 enabled
export GEMINI_API_KEY=...    # aistudio.google.com/apikey

# 1. who is worth approaching
./scripts/shortlist.py "bookkeeping business" "quickbooks online tutorial" \
    --videos 12 --pages 2 -o shortlist.md

# 2. what to build for the winner
./scripts/demand_harvest.py <channel-id-or-@handle> --videos 30 --pages 5 --out-dir demand/

# 3. cluster again without re-paying for the fetch
./scripts/demand_harvest.py --from-cache demand/<channel>.raw.json -o report.md
```

## The metric that matters: demand reach

`demand reach = median views per video × share of comments that ask for help`

**Subscriber count is not used for ranking, because it misleads.** Measured on real channels
in one niche:

| Creator | Subscribers | Median views | Demand reach |
|---|---:|---:|---:|
| Zach Pasquariello | 53,400 | 1,029 | 104 |
| Realistic Bookkeeping | 38,200 | 9,401 | **619** |
| The Quickbooks University | 75,500 | 15,682 | **4,308** |

The 53,400-subscriber channel reaches ~1,000 people per video. Ranking on subscribers picked
it first; ranking on demand reach put it last, and the correct answer sixth.

One caveat that applies to this metric too: median views is a *recent* figure, but a single
huge lifetime number is not. The chosen creator's top video shows 744,894 views accumulated
over roughly two years, which says nothing about this month — see "Lifetime views are not
current reach" above.

## Comments are graded, not filtered

`demand_harvest.grade()` returns `strong`, `weak` or `None`.

- **strong** — someone asking for help with their own situation, or asking the creator to make
  something. Only these may found a demand cluster.
- **weak** — question-shaped but possibly rhetoric. Corroborates, never founds.
- **None** — praise, reactions, noise. Dropped before it costs a token.

This grading exists because two earlier versions looked like they worked and did not. A bare
`?` or `why` matched *"Who wants a stylus?"* and *"So we go back to horizontal videos? lol"*.
A looser `I can't …` clause matched *"I cannot unsee it"*, *"phones I can't afford"* and
*"I can't wait"* — feeling, not task. On a consumer channel the fixed grader returns **0
strong out of 300**, which is the right answer: that audience reacts, it does not ask.

**Test any change to the grader against real comments, never invented ones.** Both false-positive
classes above were invisible until real data went through.

## Known limits

- **The "no product in bio" filter does not work.** `link_in_bio` matches `http`, which nearly
  every description contains, so it flags everything. This is the highest-value filter in the
  method — **check it by eye.** Doing so demoted the two highest-demand-reach candidates
  (both already sell courses) and promoted the one with no product.
- **Shorts poison a sample.** They return 0–2 comments each and drag the median down. Sample
  more videos rather than trusting a thin denominator; `--min-comments` (default 30) separates
  unscored channels from genuine zeroes.
- **Search surfaces brand channels.** Of 46 channels found for one niche, only 3 fell inside a
  10k–100k subscriber band; the rest were Intuit's own regional accounts. Use several query
  phrasings.
- **Clustering ranks the symptom over the need.** One run's top cluster was "fix the invalid
  phone number error at signup" when the real signal underneath was "international beginners
  locked out of US-only tooling". Read the verbatim quotes, not just the headline.
- **A cluster asking for a *video* is not automatically a product.** "Please make a video on X"
  converts only as templates, scripts or a procedure. A cluster asking for an SOP or a
  calculator is a paid deliverable as-is, and is worth more even with fewer requests.

## Sequence, corrected

1. **Screen** candidates on demand reach (`shortlist.py`), check the no-product filter by eye.
2. **Cluster** the winner's comments (`demand_harvest.py`), read the verbatim quotes.
3. **Build** the product (`build_workbook.py`), verify it (`verify_workbook.py`), open it once
   in a real spreadsheet app.
4. **Sell one copy yourself** on a platform with its own traffic. This is the gate the first
   version of this skill was missing.
5. **Set up tracking** — affiliate links with a dashboard the creator can see.
6. **Then** approach creators, offering affiliate or licence, with a real conversion rate.

Steps 4 and 5 are cheap and are what make step 6 an offer rather than a favour request. An
operator may choose to skip them and email first; that is a legitimate call about speed versus
strength of offer, and it should be a decision, not an oversight.

## Quota and cost

`search.list` is 100 units per query; everything else is ~1 per call. A 6-query, 20-channel
screen plus two full harvests ran ~1,500 units of the 10,000/day free allowance. Clustering a
1,282-comment channel cost ~27k Gemini input tokens.

## Verifying a product built here

`verify_workbook.py` parses every formula and re-computes the arithmetic in Python: that each
`SUMIFS` references the intended columns and criteria cells, that only pre-2007 functions are
used (so nothing can degrade to `#NAME?`), and that the example rows total correctly.

It exists because **LibreOffice cannot load any xlsx in this container** — a three-cell test
workbook fails with `source file could not be loaded`, so the normal `recalc.py` check from the
`xlsx` skill is unavailable here. The Python verifier is not a substitute: it proves the
formulas are *right*, not that a spreadsheet engine *renders* them. Open the file in Excel once
before shipping it to anyone. (The workbook built this way did open correctly in Excel, with all
252 SUMIFS computing.)

Generate expected-value tables from the file, never by hand. A hand-typed January net of
`$907.64` shipped in a draft when the correct figure was `$906.64`.
