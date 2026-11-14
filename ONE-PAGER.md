# ICP territory skill: one page

**136** CRM accounts in. **24** real fits found from their own websites.
**11** placed in three rep territories, **7** handed to enterprise, **42**
flagged for review. Validation: **87%** against a 90% bar, **26 of 27** on
sites it could read.

## The problem

Rackwell (made up) sells commercial gym equipment in Illinois, Wisconsin and
Indiana. Its CRM holds prospect accounts with unknown fit. The industry tag
lumps gyms with yoga studios and spas: 52 accounts share one tag. Reps waste
calls, and territories are drawn around accounts that will never buy. This
skill answers the territory question: which fits does each rep own?

## How it works

```
CRM export -> 1 Enrich (Apollo) -> 2 Read websites -> 3 Grade (Claude, one written rule)
           -> 4 Validate (30 hand labels, fixed bar) -> 5 Territories (CRM coordinates)
```

- **Systems touched:**
  - Apollo company enrichment (free plan, live API).
  - Company websites.
  - A CRM export as CSV.
  - Claude Code running the skill.
- **The model's job:** one judgment per account, with an exact quote from
  the site. Code checks the quote. Scripts do everything else.
- **The policy:** one sentence the business owns. "A Fit runs a
  member-facing floor of cardio or strength machines."

## Numbers

| What | Result |
|------|--------|
| Apollo enrichment | 88 trusted, 34 no record, 9 flagged as name mismatches and ignored, 5 skipped |
| Websites readable | 96 of 136 (71%) |
| Grades | 24 Fit, 70 Unlikely, 42 Needs Review |
| Validation run 1 | 77%. The text cap cut real evidence. |
| Validation run 2 (final) | 87%, below the 90% bar. 3 of 4 misses were blocked sites. 26 of 27 readable sites correct. |

| Territory (60 mi) | Assigned | Short of 5 |
|-------------------|----------|------------|
| Chicagoland | 6 | 0 |
| Milwaukee | 3 | 2 |
| Michiana | 2 | 3 |

6 fits sit outside every radius, mostly in downstate Illinois. That is the
case for a fourth territory.

## Design decisions

- **A skill, not a script or an MCP call.** The judgment needs a model, the
  rest needs code, and the policy needs to be a file a sales leader can
  read. An Apollo call alone returns data, not a decision.
- **Three grades, not two.** What cannot be seen goes to Needs Review with a
  reason. It is never guessed.
- **Fit and segment are separate.** Chain locations are fits, but they go to
  the enterprise team.
- **Left out of v1:**
  - Several radii.
  - Ranked contacts.
  - Letting Apollo data nudge a grade.
  - Writing back to the CRM.

## Where I did not trust the AI

- I reframed the problem from finding accounts to qualifying the CRM.
- I barred Needs Review as a place for undecided policy.
- I required CRM locations, since Apollo returns headquarters.
- I separated segment from fit.
- I added a guard for Apollo's wrong-company matches.
- I blocked a padded validation set.
- I moved grading to a blind session.
- After a failed run, I fixed the evidence, not the policy or the bar.

## Production next

- A larger fixture, rerun on every policy change.
- A headless browser for JavaScript sites, with no bot-block workarounds.
- Image evidence.
- A scoped key in a secrets manager.
- CRM write-back after a manager approves.

*Pre-existing:* the approach comes from an ICP classifier and territory
assigner I built in my last role. Nothing from it is in this repo. All of it
was rewritten for this exercise.
