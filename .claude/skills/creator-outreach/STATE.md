# State — where the creator-outreach operation actually is

Living file. A session picking this up cold reads this first, then `SKILL.md`.
Update it at the end of each cycle. Last updated **2026-09-23** (cycle 04).

## Who is doing this

Diego Radrigán · Lampa, Chile · `mcjuanopepito@gmail.com`
Gumroad seller name shows as **Diego RV**.

## The product (live)

| | |
|---|---|
| Name | 12-Month Bookkeeping Workbook — Year-to-Date P&L for Excel & Google Sheets |
| URL | https://juanopepito.gumroad.com/l/12-month-bookkeeping-workbook |
| Price | **$39** |
| Creator code | `RACHAEL` — $10 off, 1,000 uses, capped deliberately |
| Discover | **on** (30% flat fee, but it is traffic that needs no creator) |
| Refunds | Gumroad's 30-day default, left on deliberately — see below |
| Built by | `scripts/build_workbook.py`, verified by `scripts/verify_workbook.py` |

**Fees, from Gumroad's own settings page:** direct sales 10% + 50¢ Gumroad plus
2.9% + 30¢ card ≈ **$24.46 kept on a $39 sale**; Discover sales **30% flat**.

**Payout:** Chile is supported, paid in CLP. BancoEstado CuentaRUT works — bank
code `012`, account type **Checking** (a *cuenta vista* is neither of the two
options offered, and it is definitely not savings), account number is the RUT
without its check digit. **Minimum payout threshold for Chile is $100**, so
roughly 5 sales before money moves. A $0 bank balance after two sales is the
threshold, not a failure — check the Gumroad balance instead.

## Cycle log

### Cycle 01 — Rachael Brown, Realistic Bookkeeping · SENT 2026-09-21

- `UCGTlfnD16-eogZJp5u34i0w` · 38,200 subs · median 9,401 views · demand reach 619
- Top video `EFAig6aSBYg` "FREE TEMPLATE … BOOKKEEPING" — 744,894 **lifetime** views
- Chosen because: no product in bio, bio literally says "please reach out", and her
  audience already downloads a spreadsheet from her
- Product built from her own comment cluster: the twelve-month / year-to-date version
  five separate commenters asked for
- Offer: affiliate (40%, code RACHAEL) **or** licence ($150–300 one-off)
- Status: **sent, awaiting reply.** Day-6 follow-up due ~2026-09-27, once, then stop.
- Sales to date: **0**

### Cycle 02 — 2026-09-23 · NOTHING SENT, and the niche looks exhausted

Six queries, 71 channels found, 22 screened, **2 eligible, 1 real** — and the one
real candidate was Rachael, already emailed.

| Creator | Subs | Median views | Demand reach | Verdict |
|---|---:|---:|---:|---|
| Bookkeeping with Jake Demi | — | — | 585 | sells coaching |
| Realistic Bookkeeping | 38,200 | 9,401 | 486 | already emailed |
| QuickBooks From The Top | 6,130 | 747 | 224 | **no real cluster** |
| The Bookkeeping Shop® | 15,700 | 1,602 | 169 | sells a bundle |
| Veronica Wasek | 53,800 | 841 | 147 | below reach floor |
| everyone else | | | 0–114 | too thin |

**Read: bookkeeping is done.** Rachael was not the best candidate I happened to
find, she was close to the only one. Every remaining channel either already sells
something, has ~1,000-view reach, or has a comment section too thin to cluster.
More bookkeeping queries will not fix that — the next real move is a second
product for a different niche.

**This run also exposed four bugs in `campaign.py`, all now fixed** — see the
commit. Two would have sent a bad email: it greeted a stranger as "Hi Rachael"
(having read the discount code as a first name), and it invented product features
that do not exist ("twelve monthly input tabs", "printable customer statement
view") to make three unrelated comments look like a cluster. The clustering pass
had explicitly refused that dataset and the drafter ignored it.

### Cycle 03 — 2026-09-23 · Etsy / print-on-demand · NOTHING SENT

Screened correctly this time — **screen first, build second**, the cycle-01 correction.
90 channels found, 16 screened, 3 clean candidates harvested (~3,600 comments).

| Creator | Subs | Median views | Demand reach | Verdict |
|---|---:|---:|---:|---|
| Brandon Timothy | 164,000 | 13,239 | **929** | **channel is dead** — see below |
| Tatyana Savage | 149,000 | 6,647 | **837** | full `stan.store` catalog |
| Cassie Council | 11,700 | 3,382 | 336 | physical craft, wrong product shape |

**Brandon Timothy is the most useful failure so far.** He ranked first on every
metric the pipeline had. His newest upload in a 30-video sample is 2024-08-31,
titled *"I'm taking a break from Etsy (here's why…)"* — dormant two years. A
median view count is **lifetime accumulation and does not decay when a channel
dies**, so demand reach cannot see this, and neither could the bio filter.
Fixed: `shortlist.py` now records `last_upload` and drops anything past
`--max-dormant-days` (default 180).

**Tatyana Savage** posted yesterday and has real demand, but her video
descriptions carry a whole storefront — `stan.store/tatyanasavage` selling shop
starter kits, banner templates, customer-retention templates and an Etsy shop
Notion planner. Her top cluster (Notion templates, 9 asks, 76 likes) is a
product she already sells. Note the bio filter missed this too: **the tell was
in the video descriptions, not the channel About page.** Worth folding into
`_sells()`.

**Cassie Council** clusters cleanly (10 asks on "how do you seal painted acrylic
so it doesn't chip") but the demand is for *technique*, not a template. Reach 336.

**The cross-creator signal worth keeping:** "Etsy doesn't support my country"
appeared independently in **both** 150k channels — 4 strong asks each, including
sellers in India, Nigeria, Jordan, Kenya and Nicaragua who finished a product and
then found they could not sell it. That is the largest unserved cluster this
pipeline has found. It is deliberately **not** being built: it turns on payment
rails, entity setup and tax residency, where wrong information does real damage
to the buyer. Revisit only with a source that can be cited.

**The structural read after two niches and 161 channels:** essentially every
creator with real reach already sells something. The premise "find a creator
whose audience wants what they don't sell" is, at reach, selecting for creators
who are *bad at business* — a small population, and not the one whose audience
converts. Three of three leads across two niches died on this. The gate the skill
already names and we keep skipping (**sell one copy to a stranger first**) is now
the higher-value move than a fourth niche.

### Cycle 04 — 2026-09-23 · service businesses · 3 DRAFTED, not yet sent

The first cycle run for **volume**, on the operator's instruction to stop
filtering so hard. The filters were not the bottleneck — **addresses were**, and
fixing that is what changed the numbers.

| Stage | Count |
|---|---:|
| Channels found (12 queries) | 291 |
| Live and in band (3k–500k) | 89 |
| **With an address, automatically** | **25** |
| Clustered | 25 |
| Produced a usable pricing cluster | **3** |

25 addresses from one sweep, against 2 found by hand in the three cycles
before it. `prospect.py` extracts them from bios and video descriptions, which
were already being fetched — so it costs nothing and spends no Gemini tokens.

**The three drafted, all quotes verified against the raw harvests:**

| Creator | Subs | Median views | Address | Currency |
|---|---:|---:|---|---|
| Partridge Exterior Cleaning (Sid) | 206,000 | 22,927 | `sid@partridgeexteriorcleaning.co.uk` | GBP |
| The Lawn Care Life in Mowssouri | 29,400 | 15,645 | `youtube@thelawncarelife.com` | USD |
| Maxwells Grass Cutting Services (Rob) | 13,800 | 5,457 | `maxwellsgrasscutting@gmail.com` | GBP |

Maxwells is the strongest of the three despite being the smallest: his
commenters do not merely ask the price question, they describe drowning in
contradictory answers to it — *"people saying don't charge less that £80 an hr,
don't go by hourly rate, go by hourly rate… it's a bit overwhelming"*. That is
a calculator-shaped complaint. Partridge last uploaded 2026-04-07, five and a
half months back, so check he is still active before sending.

**22 of 25 were dropped by the clustering, and that is the system working.**
Biglin (63,525 median views) is charity lawn transformations — 16 strong
comments out of 3,375, an audience that watches rather than asks. Drake and
Spencer are vlogs. `my-pressure-washing-business` clustered strongly (8 asks)
but on unloader-valve calibration, which is not a spreadsheet. Every refusal is
now recorded in `contacted.txt` so the next cycle does not re-spend tokens
clustering them.

**Ranking by reach alone put the entertainment channel first.** `prospect.py`
stays token-free and therefore cannot see demand density, so its ordering
favours eyeballs over intent. A 5-video × 1-page comment sample would cost ~5
quota units and no tokens — the obvious next improvement, not yet built.

**Product #2 shipped this cycle:** the Job Pricing & Quoting Calculator, built
because "how do I price a job" turned out to be a cluster in *four* channels
across *two* unrelated niches (add Cassie Council's acrylic-pricing cluster from
cycle 03). One product serves the whole queue. Built in USD and GBP.

## What has been learned the hard way

1. **Rank on demand reach, never subscribers.** A 53,400-sub channel in this niche
   had a 1,029-view median. Subscribers put it first; reach put it last.
2. **Lifetime views are not current reach.** Never quote a big lifetime number back
   to a creator — they can check their own analytics in seconds.
3. **Check the bio by eye.** The automated product filter is a heuristic. Doing this
   manually disqualified the two highest-reach candidates (both sell courses).
4. **Track sales, not replies.** A creator who says "interesting, send the link" and
   never posts looks like progress for weeks. If replies climb and sales stay at
   zero, the product or the price is wrong and more emails will not find it.
5. **Never fabricate a quote.** The verbatim comments are why the email works.
   `campaign.py` verifies every block quote against the harvest for this reason.
6. **Refunds: leave the 30-day guarantee on for now.** Yes, a buyer can download and
   refund and keep the file — unavoidable with digital goods. But with zero reviews
   the guarantee is what makes a stranger buy at all, and switching it off pushes
   people to chargebacks, which cost more and can flag the account. Revisit only if
   a buy-download-refund pattern actually appears.
7. **A dead channel keeps its numbers.** Median views never decay, so a
   two-years-dormant channel can top the ranking. Always check the newest
   upload date — the filter now does, but check it by eye too.
8. **The storefront is often in the video descriptions, not the bio.** A
   channel About page with no product tell is not evidence of no product.
9. **Addresses are the bottleneck on volume, not filtering.** Three cycles were
   spent tightening filters while the real constraint was that every email
   address had to be found by hand. Extracting them from bios and video
   descriptions yielded 25 in one sweep, free. Cluster *last*, on the
   contactable list only.
10. **A description holds other people's addresses.** A 157,000-subscriber
   channel yielded a sponsor's address. `address_confidence()` flags it.
11. **Test a product past its shipped defaults.** A typo in the calculator's
   work-type name priced a job at the minimum call-out with zero hours and
   reported "Worth doing" at 70% margin. The defaults all looked perfect.
12. **A verifier that fails a valid file is worse than none.** Mine reported 61
   problems in a sound workbook because Excel's IF short-circuits and Python's
   eval does not. Had that shipped, the next real failure would have been
   waved through as noise.
13. **The offer must not be revenue-share only.** It reads as unpaid work on an
   unproven product and selects for creators whose audience does not convert.
   Always affiliate-or-licence, their choice.

## Open items

- [ ] **Send the three cycle-04 drafts** — Partridge, Lawn Care Life, Maxwells.
      Drafts hold no product URL by design, so they can go out before a Gumroad
      listing for product #2 exists; a listing is only needed if someone says yes.
- [ ] **Open a calculator workbook once in Excel.** The Python verifier proves
      the formulas are right, not that an engine renders them, and LibreOffice
      cannot open any xlsx in this container.
- [ ] Add a cheap density sample to `prospect.py` so the queue sorts on intent
      rather than views
- [ ] Day-6 follow-up to Rachael (~2026-09-27), one email, then stop
- [ ] **Rotate both API keys** — the YouTube and Gemini keys were pasted into a chat
      transcript and live there permanently
- [ ] First sale from a stranger via Discover — the evidence the pitch still lacks
- [ ] **A second product — now the blocking item, not a later one.** Cycle 02 showed
      bookkeeping is exhausted. Pick a niche with commercial-intent buyers, run
      `campaign.py` to find where the demand is, then build for the winner.

## Keys

**Not stored here and never committed.** Two are needed, both pasted into the shell
at run time:

- `YOUTUBE_API_KEY` — Google Cloud, YouTube Data API v3 enabled. Confirmed working.
- `GEMINI_API_KEY` — AI Studio. Confirmed working.

Quota used per cycle is roughly 1,500–2,000 units of a 10,000/day allowance.

## Container reality

Scratch space, reclaimed after inactivity. Only pushed git state survives, so
campaign output and `corpus/` do not — hand files to the operator before the session
goes idle. LibreOffice cannot open any xlsx here, which is why
`verify_workbook.py` checks formulas in Python instead of recalculating.
