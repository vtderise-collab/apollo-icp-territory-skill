# ICP territory skill

A Claude Code skill that grades a CRM's prospect accounts against a written
ideal customer profile, then builds rep territories from the real fits.

## The problem

Rackwell (a made-up company that sells and services commercial gym
equipment in Illinois, Wisconsin and Indiana) has 136 prospect accounts in
its CRM, and nobody knows which ones run a gym floor that buys treadmills and
racks. The industry tag puts gyms, yoga studios, boxing clubs and massage
spas in the same bucket, so reps call accounts that will never buy and
territories get drawn around the wrong accounts.

## What the skill does

```
CRM export (136 accounts, with site coordinates)
   |
1  Enrich      Apollo company enrichment: size, HQ, industry tag.
   |           Sets the segment (Enterprise or Mid-Market) by a fixed rule.
2  Evidence    Reads each account's own website. Unreadable sites are
   |           marked with the reason, never guessed.
3  Grade       Claude applies one written rule (references/icp.md):
   |           Fit, Needs Review or Unlikely, with an exact quote from the
   |           site. Code rejects any quote not found in the site text.
4  Validate    Grades are scored against 30 hand labels and a pass bar
   |           set before the first run.
5  Territories Mid-Market Fits go to the nearest anchor customer within one
               radius, using CRM coordinates. Enterprise Fits go to a
               handoff list. Needs Review gets its own list.
```

Scripts do all the data work. The model makes one judgment per account and
never invents a fact or changes the policy.

## Install and run

Needs Python 3 (standard library only) and Claude Code.

1. Copy the `icp-territory` folder into your project's `.claude/skills/`.
2. Put your CRM export at `data/crm_export.csv` in the project folder. This
   repo includes a stand-in list built from OpenStreetMap.
3. Enrichment needs your own Apollo API key. Put `APOLLO_API_KEY=...` in a
   `.env` file in the project folder. A free plan works: company enrichment
   is allowed, company and people search are not.
4. In Claude Code, from the project folder, ask: "Grade my accounts against
   the ICP and build territories." The skill runs the five steps and stops
   to show you the validation result.

To run the scripts by hand, from the project folder:

```
python3 .claude/skills/icp-territory/scripts/enrich_accounts.py
python3 .claude/skills/icp-territory/scripts/fetch_evidence.py
python3 .claude/skills/icp-territory/scripts/grading.py batch --size 10   # Claude grades these
python3 .claude/skills/icp-territory/scripts/grading.py check
python3 .claude/skills/icp-territory/scripts/validate.py
python3 .claude/skills/icp-territory/scripts/territories.py
```

Anchors, radius, region and segment thresholds are in
`icp-territory/config.json`. The policy is `icp-territory/references/icp.md`.

The `setup/` folder only rebuilds the demo data and is not part of the skill.
`setup/seed_crm_from_osm.py` needs `curl` on your path.
`data/crm_export.csv` is committed, so you do not need to run it.

Apollo's data (`data/accounts.csv`, `data/evidence.jsonl`) is not in this
repo. Run enrichment with your own key to create it.

## Results

**Apollo enrichment (136 accounts)**
- 88 trusted matches. 34 had no Apollo record. 9 were flagged as name
  mismatches and ignored. Most are a different company, but at least two
  are true matches the guard is too strict on. 5 shared hosts and social
  pages were skipped.
- 32 accounts were segmented Enterprise and 104 Mid-Market.
- 52 accounts share the tag "health, wellness & fitness", across gyms, yoga
  studios, boxing clubs and chains. The tag cannot separate fits from
  non-fits.

**Scrape coverage:** 96 of 136 websites readable (71%). The other 40 go to
Needs Review with the reason (blocked, dead, or nearly empty).

**Grades (all 96 readable accounts):** 24 Fit, 70 Unlikely. Including the 40
unreadable sites, 42 accounts are Needs Review.

**Validation (30 hand-labeled accounts, bar: 90% overall, 85% on Fit and on
Unlikely)**

| Run | Overall | Fit | Unlikely | Result |
|-----|---------|-----|----------|--------|
| 1 | 23/30 = 77% | 10/13 = 77% | 13/17 = 76% | Fail |
| 2 (final) | 26/30 = 87% | 13/16 = 81% | 13/14 = 93% | Fail |

What changed between runs:
- The evidence step, not the policy. Run 1 cut each site to 3,500
  characters, which dropped real evidence. Run 2 also keeps the meta
  description, image alt text and short snippets around equipment words.
  The cap is now 7,000 characters.
- Run 1's quotes showed that 3 of my hand labels were wrong. I rechecked
  those sites myself and corrected the labels, which is why the Fit and
  Unlikely counts differ between runs.
- Run 2 was graded in a fresh session that had never seen the labels.
- The ICP and the pass bar did not change.

Of run 2's 4 misses, 3 are sites that blocked the rescrape (HTTP 403). The
script sent them to Needs Review before the model saw them. On the 27 sites
it could read, the grader got **26 of 27** right. The real miss was a
training gym whose evidence is in photos, which the grader cannot see.
Run 2 is reported as final. Nothing was tuned after it.

**Territories (radius 60 miles, target 5 per territory; anchors are made up
but sit at real ZIP codes)**

| Territory | Anchor | Assigned | Short | Farthest | Also in range of another anchor |
|-----------|--------|----------|-------|----------|---------------------------|
| Chicagoland | Schaumburg, IL 60173 | 6 | 0 | 38 mi | 0 |
| Milwaukee | Milwaukee, WI 53202 | 3 | 2 | 47 mi | 2 |
| Michiana | South Bend, IN 46601 | 2 | 3 | 51 mi | 1 |

- 11 of 17 Mid-Market Fits fall inside a territory. 6 are out of range:
  Madison (73 mi) and Oshkosh (76 mi) just miss. Peoria, Mahomet,
  Springfield and Eau Claire are 120 to 217 miles from an anchor. That
  points to a missing downstate Illinois territory.
- 2 assigned Fits rely on a low-confidence CRM location and are flagged.
- **Enterprise handoff:** 7 Fits (chain locations such as LA Fitness,
  Equinox, Life Time). They go to the enterprise team, not a regional rep.
- **Needs Review:** 42 accounts, 9 of them Enterprise and listed first.

Outputs are in `data/`: `territory_plan.csv`, `territory_summary.csv`,
`enterprise_handoff.csv`, `needs_review.csv`, `graded.csv`.

## Why a skill, not a script or an MCP call

- **The core step is a judgment.** Reading a website and deciding whether
  members use a machine floor needs a model. Everything around it (calls,
  caching, distance math, scoring) is deterministic, so it lives in scripts.
  A skill packages both, with instructions for when to use each.
- **The policy is a file the business owns.** `icp.md` is plain English that
  a sales leader can read and change. The model applies it and the skill
  forbids it from editing it.
- **A direct Apollo MCP call returns data, not a decision.** It has no
  policy, no evidence trail and no validation. On the free plan, Apollo's
  search is blocked anyway. Only enrichment works.
- **A plain script would hard-code the prompt** and hide the judgment step.
  The skill keeps that step visible and checked: every grade has a verified
  quote, and nothing is trusted until it passes the fixture.

How the data is shaped for the model: one record per account with the name,
the Apollo tag and the website text, ten at a time. The output is one JSON
line with a fixed set of grades and reason codes. Anything that does not
parse, or quotes text that is not on the site, becomes Needs Review.

Deliberately left out of v1: comparing several radii, ranked contacts,
letting Apollo data nudge a grade, and writing results back to the CRM.

## Assumptions

- The CRM export is the starting point. Apollo enriches it; it does not
  source accounts.
- The CRM location is the real site. Apollo's location is headquarters, so
  it is never used for territories.
- Chains buy equipment centrally (head office or an approved-vendor list).
  So chain locations route to Enterprise. I would confirm this with sales
  leadership.
- An account Apollo cannot find is small, so it defaults to Mid-Market.
- A company's own website is the most current public statement of what it
  does.
- Each rep is anchored on an existing customer, and 60 miles is about an
  hour's drive.

## Where AI helped and where I overrode it

I ran a second Claude session as a reviewer of the first, and a third to
grade blind. Several catches below came out of that review. I decided what
to act on.

AI wrote the code, drafted the ICP for my approval and graded all 96
readable accounts. Its exact quotes caught 3 errors in my own hand labels.

Where I did not trust it (full list in my correction log):
- **Framing.** It framed Apollo as the place to find accounts. I reframed it:
  a revenue team's real problem is the thousands of accounts already in the
  CRM that nobody has qualified.
- **Needs Review.** It parked undecided policy questions in Needs Review. I
  ruled that Needs Review means "could not see clearly", never "policy not
  decided", and made each borderline call myself.
- **Location.** It planned to use Apollo's location. Apollo returns
  headquarters (a Wisconsin gym came back as New Hampshire), so I required
  CRM coordinates.
- **Chains.** It graded chain locations Unlikely. Fit and segment are
  separate questions. Chains are a different segment, and one franchisor win
  can open every location.
- **Wrong-company matches.** Apollo matched by domain alone and returned the
  wrong company, for example a site builder or a different organization. I
  had a name check added: mismatches are flagged and their Apollo data is
  ignored.
- **Segment rule.** It made a company Enterprise from headquarters alone. I
  required a trusted match plus a size floor.
- **Inflated scoring.** It prefilled 3 unreadable sites in the validation
  set, which were guaranteed hits. It also planned to grade in the session
  that had seen the answer key. I replaced the sites and moved grading to a
  fresh, blind session.
- **After run 1 failed,** I fixed what the grader could see, not the policy
  or the bar. Labels were changed only by me, after rechecking the sites.

## What I would harden for production

- **Accuracy:**
  - Grow the fixture well past 30 accounts and rerun it on every ICP change.
  - Audit a sample of live grades each month.
  - Read image evidence, since the one real miss was in photos.
- **Coverage:**
  - Use a headless browser for sites that render with JavaScript.
  - Retry blocked sites later. Never work around a bot block.
  - Track scrape coverage as its own metric.
- **Reliability:**
  - Run grading through the API with structured output and retries.
  - Rerun from cache so a crash loses nothing.
- **Security:**
  - Use an Apollo key scoped to enrichment only, stored in a secrets
    manager.
  - Keep Apollo's data out of shared storage.
- **Data quality:**
  - Use fuzzy name matching for Apollo. The current guard also discards a
    few true matches.
  - Use an offline geocoder for addresses.
- **Scale and workflow:**
  - Batch and parallelize the scrape.
  - Write grades back to the CRM only after a manager approves the
    territory plan.

## What was pre-existing

> The approach comes from an ICP classifier and territory assigner I designed and ran in my last role. Nothing from that build is in this repo. I rewrote it from scratch for this exercise on public data: a different company, a different ICP, Apollo as the account source, and a skill in place of a standalone script.

Everything here was written new for this exercise with Claude Code.
