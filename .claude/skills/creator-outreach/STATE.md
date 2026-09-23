# State — where the creator-outreach operation actually is

Living file. A session picking this up cold reads this first, then `SKILL.md`.
Update it at the end of each cycle. Last updated **2026-09-23**.

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
7. **The offer must not be revenue-share only.** It reads as unpaid work on an
   unproven product and selects for creators whose audience does not convert.
   Always affiliate-or-licence, their choice.

## Open items

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
