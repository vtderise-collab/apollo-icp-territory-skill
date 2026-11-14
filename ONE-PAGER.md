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
- **Time.** I hand-labeled 30 accounts in 25 minutes, about 50 seconds each.
  The skill graded 96 within one 15-minute session, at least five times
  faster per account. It runs unattended, with a checkable quote on every
  grade. For an example CRM of 50,000 accounts (not a real company), manual
  labeling would be about 700 hours.
- **Rep focus.** 70 of 136 accounts are confirmed not worth a call. Only 24
  are real fits.
- **Better territory decisions.** The plan found 6 fits that no territory
  covers and moved 7 chains to enterprise. A carve based on the tag would
  miss both.

## Why this problem

I solved it for real in my current role. Sales leadership wanted territories
rebuilt around marquee accounts, with no way to grade accounts or map them.
I built a scorer from a CRM export and written fit rules, and leadership
validated it. Reps got a prioritized book. Here I rebuilt it on **Apollo**.
Apollo's size and headquarters data splits regional from enterprise, and the
skill audits that data instead of trusting it blindly. That is ideas #1 and
#4 from the brief.

## Who uses it and what they get

- **Sales leader:** the map and territory summary, to approve the plan and
  see gaps.
- **Rep:** their book of fits, with the sentence each grade rests on.
- **RevOps:** data-hygiene findings. These are Apollo name mismatches,
  headquarters versus site location, and unreadable sites.
- **Next, not built:** write grade, evidence, segment and territory back to
  the CRM.

## How it works

```
CRM export -> 1 Enrich (Apollo) -> 2 Read websites -> 3 Grade (Claude, one written rule)
           -> 4 Validate (30 hand labels, fixed bar) -> 5 Territories (CRM coordinates)
```

The model makes one judgment per account, with an exact quote that code
checks. Scripts do everything else. The policy is one sentence the business
owns: "A Fit runs a member-facing floor of cardio or strength machines."

## Numbers

| What | Result |
|------|--------|
| Apollo enrichment (the data-hygiene audit) | 88 trusted, 34 no record, 9 flagged as name mismatches and ignored, 5 skipped |
| Websites readable | 96 of 136 (71%) |
| Validation | Run 1: 77% (text cap cut evidence). Run 2: 87%, 3 of 4 misses were blocked sites. |
| Territories (60 mi, target 5) | Chicagoland 6, Milwaukee 3, Michiana 2. 6 fits out of range, mostly downstate Illinois. |

## Design and trust

- **Why a skill:** the judgment needs a model, the rest needs code, and the
  policy must be a file a sales leader can read. An Apollo call alone
  returns data, not a decision.
- **Where I overrode the AI:** I reframed the problem to qualifying the
  existing CRM. I kept Needs Review for "could not see" only. I required CRM
  locations over Apollo's headquarters. I separated segment from fit. I
  guarded against wrong Apollo matches. I moved grading to a blind session.
- **Production next:** a larger fixture, a headless browser for JavaScript
  sites, image evidence, a scoped key, and CRM write-back after approval.

*Pre-existing:* the approach comes from an ICP classifier and territory
assigner I built in my current role. Nothing from it is in this repo. All of it
was rewritten for this exercise.
