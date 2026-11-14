# ICP territory skill: one page

**136** CRM accounts in. **24** real fits found from their own websites.
**11** placed in three rep territories, **7** handed to enterprise, **42**
flagged for review. Validation: **87%** against a 90% bar, **26 of 27** on
sites it could read.

It replaces weeks of manual account qualification with an unattended run, so
reps only call real fits and territories are built on evidence instead of a
tag.

## The problem

Rackwell (made up) sells commercial gym equipment in Illinois, Wisconsin and
Indiana. Its CRM holds prospect accounts with unknown fit. The industry tag
lumps gyms with yoga studios and spas: 52 accounts share one tag. Reps waste
calls, and territories are drawn around accounts that will never buy.

**What it saves**
- **Time.** I hand-labeled 30 accounts at about 50 seconds each. The skill
  graded 96 within one 15-minute session, at least five times faster. It runs
  unattended, with a checkable quote on every grade. For an example CRM of
  50,000 accounts, manual labeling would take about 700 hours.
- **Rep focus.** 70 of 136 accounts are confirmed not worth a call.
- **Better territories.** It found 6 fits that no territory covers and moved
  7 chains to enterprise. A carve based on the tag misses both.

## Why this problem

I solved it for real in my current role. Sales leadership wanted territories
rebuilt around marquee accounts, with no way to grade or map accounts.
Leadership validated the scores, and reps got a prioritized book. Here I
rebuilt it from scratch on **Apollo**. Apollo's size and headquarters data
splits regional from enterprise, and the skill audits that data instead of
trusting it. That is ideas #1 and #4 from the brief. No code or data from
the original build is in this repo.

## Who uses it

- **Sales leader:** the map and summary, to approve the plan and see gaps.
- **Rep:** a book of fits, with the sentence each grade rests on.
- **RevOps:** data-hygiene findings on Apollo mismatches, headquarters
  versus site location, and unreadable sites.

## Rollout and success

- **Pilot:** half the mid-market reps use it for a quarter, with the other
  half as the comparison.
- **Managers approve:** the territory plan, ownership changes and holdover
  requests.
- **Then:** write grade and territory to the CRM, and expand to the team.
- **Targets:**
  - Fit conversion above the rest of the book.
  - Pipeline per territory.
  - Referrals near marquee anchors.
  - Live grades at 90% or better.

## How it works

```
CRM export -> 1 Enrich (Apollo) -> 2 Read websites -> 3 Grade (Claude, one written rule)
           -> 4 Validate (30 hand labels, fixed bar) -> 5 Territories (CRM coordinates)
```

The model makes one judgment per account, with an exact quote that code
checks. Scripts do the rest. The policy is one sentence the business owns:
"A Fit runs a member-facing floor of cardio or strength machines."

| What | Result |
|------|--------|
| Apollo audit | 88 trusted, 34 no record, 9 name mismatches flagged and ignored, 5 skipped |
| Websites readable | 96 of 136 (71%) |
| Validation | Run 1: 77%, text cap cut evidence. Run 2: 87%, 3 of 4 misses were blocked sites. |
| Territories (60 mi) | Chicagoland 6, Milwaukee 3, Michiana 2. 6 fits out of range. |

## Design and trust

- **Why a skill:** the judgment needs a model, the rest needs code, and the
  policy must be a file a sales leader can read. An Apollo call alone
  returns data, not a decision.
- **Where I overrode the AI:**
  - Qualify the existing CRM rather than source new accounts.
  - Needs Review only for "could not see".
  - CRM locations, not Apollo headquarters.
  - Segment kept separate from fit.
  - A guard against wrong Apollo matches.
  - Blind grading.
- **Production next:**
  - A larger fixture.
  - A headless browser.
  - Image evidence.
  - A scoped key.
  - CRM write-back after approval.
