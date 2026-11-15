# ICP territory skill

**A Claude Code skill that turns an unqualified CRM account list into
balanced rep territories.** It grades every account against a plain-English
ICP using the company's own website, enriches it with Apollo, and assigns
the real fits to reps. Every grade comes with its evidence.
Live planner: https://vtderise-collab.github.io/apollo-icp-territory-skill/data/territory_map.html

## What it does for a GTM team

- **Sales leader:** an interactive planner. Drag the radius, turn marquee
  accounts on or off, reassign accounts by hand, and watch the books
  rebalance live. Their choices feed back into the official plan.
- **Rep:** a book of real fits, each with the sentence the grade rests on.
- **Enterprise team:** a handoff list of chain and large-company fits.
- **RevOps:** a hygiene audit with a proposed fix for every record problem,
  and a Needs Review queue with a reason on every account.

## The problem: what it saves and unlocks

- **Time.** Grading by hand takes about 50 seconds an account. At 50,000
  accounts (an example size), that's 700 hours. The skill runs unattended,
  at least five times faster, with a checkable quote on every grade.
- **Rep focus.** In the example, 70 of 136 accounts were confirmed not
  worth a call.
- **Fairer territories.** Carves are built on evidence, not an industry tag,
  and books are balanced. It flags fits no territory covers, and books that
  can't be balanced.

## How it works: architecture and data flow

```
 CRM export (CSV) ──► 1 Enrich ◄── Apollo API (size, HQ, industry tag)
                      2 Evidence ◄── company websites (read directly)
                      3 Grade      Claude + references/icp.md, quote verified by code
                      4 Validate   hand labels, fixed pass bar
                      5 Set up     asks the user: by state, or around marquee accounts
                      6 Territories CRM locations only, balanced, manager overrides kept
                      7 Hygiene    record problems, each with a proposed fix
                         ▼
     rep books · planner · Enterprise list · Needs Review · hygiene audit (CSV, HTML)
```

**Systems touched:** Apollo's live API, company websites, the CRM export,
and CSV and HTML outputs. Claude Code runs the skill.

## Design decisions

- **Why a skill, not a script or an MCP call:** the grade is a judgment, so
  it needs a model. Everything else is deterministic, so it lives in
  scripts. The policy is one sentence the business owns: "A Fit runs a
  member-facing floor of cardio or strength machines." An Apollo MCP call
  returns data, not a decision.
- **Data shaped for the model:** one record per account goes in (name, tag,
  website text). One JSON line comes out, with a fixed grade and an exact
  quote. Code checks the quote. Anything malformed becomes Needs Review.
- **Left out:** ranked contacts (Apollo's free plan blocks people search),
  applying fixes, and CRM write-back.

## Assumptions

- The CRM location is the real site. Apollo returns headquarters.
- Chains buy centrally, so they go to enterprise.
- The company's website is the most current truth.
- Every fit counts the same in balancing.

## Proof: example run

Rackwell (made up) sells gym equipment in Illinois, Wisconsin and Indiana.
- **Fits:** 24 found. 12 placed in three balanced books (6, 4, 2), with one
  flagged as unable to balance. 7 went to enterprise, and 42 to review.
- **Hygiene:** 164 problems on 105 of 136 accounts, each with a fix.
- **Validation:** 87% against a 90% bar. On readable sites, 26 of 27.

## Why I built it

I solved this in my current role: leadership wanted territories rebuilt
around marquee accounts, with no way to grade or map accounts. Here I rebuilt
it from scratch on Apollo. No code or data from the original build is in
this repo.

## Trust, rollout, production

- **Where I overrode the AI:**
  - Required CRM locations over Apollo headquarters.
  - Kept Needs Review for "could not see" only.
  - Added a guard against wrong Apollo matches.
  - Moved grading to a blind session.
  - Made territory setup a question, not an assumption.
- **Rollout:**
  - Pilot with half the mid-market reps, using the other half as the
    comparison.
  - Managers approve the plan and any overrides.
  - Target: Fit conversion above the rest of the book.
- **Before reps depend on it:**
  - A larger validation set.
  - A headless browser for JavaScript sites.
  - Image evidence.
  - One shared rules engine behind the planner.
  - A scoped key.
  - CRM write-back after approval.
