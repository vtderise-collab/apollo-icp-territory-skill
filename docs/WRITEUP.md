# ICP territory skill: full write-up

The detail behind the [README](../README.md): every discussion question from
the brief, the results in full, and the reasoning.

A Claude Code skill that grades a CRM's prospect accounts against a written
ideal customer profile, using each company's own website as evidence, and
builds rep territories from the real fits, with Apollo enrichment for size
and headquarters.

On a stand-in CRM of 136 gym-equipment prospects, it found **24 real fits**
and placed **12** in three balanced rep territories. It also handed **7 chains** to
the enterprise team and flagged **42** accounts for review. Validation scored
**87%** against a 90% bar, and **26 of 27** on the sites it could read.

- One-page summary: [ONE-PAGER.md](../ONE-PAGER.md)
- Territory planner (live): https://vtderise-collab.github.io/apollo-icp-territory-skill/example/territory_map.html

## The problem

Rackwell (a made-up company that sells and services commercial gym
equipment in Illinois, Wisconsin and Indiana) has 136 prospect accounts in
its CRM, and nobody knows which ones run a gym floor that buys treadmills and
racks. The industry tag puts gyms, yoga studios, boxing clubs and massage
spas in the same bucket, so reps call accounts that will never buy and
territories get drawn around the wrong accounts.

**What it saves**
- **Time.** I hand-labeled 30 accounts in 25 minutes, about 50 seconds each.
  The skill graded all 96 readable accounts unattended, in one session,
  with a checkable quote on every grade.
  At 50 seconds each, a CRM with 50,000 unqualified accounts (an example
  size, not a real company) is about 700 hours of one person's work.
- **Rep focus.** 70 of the 136 accounts are confirmed not worth a call, and
  only 24 are real fits. Reps stop working the other half.
- **Better territory decisions.** The plan evens out the books between
  reps. It found 6 real fits outside every territory, pulled one into the
  shortest book, and flagged the rest as a coverage gap. It also moved 7
  chains to the enterprise team. A carve based on the industry tag would
  have missed all of it.

## Why this problem

I have solved this for real in my current role. Sales leadership wanted to
rebalance territories and build new ones around marquee accounts. We had no
reliable way to grade accounts against our ideal customer profile, and no way
to turn grades into territories. I started from a CRM export and a written set
of fit rules. Claude built the scorer, and I tested and iterated on it. Sales
leadership validated the grades. Then I mapped the results to geographic
territories. The output was a book of business for each rep, showing which
accounts to work first.

For this exercise I rebuilt it around Apollo, because that is where it gets
stronger:
- **Apollo supplies what the CRM lacks.** Company size and headquarters
  decide whether an account belongs to a regional rep or to the enterprise
  team. The CRM alone cannot answer that.
- **It maps to the brief.** It is idea #4 (data hygiene and enrichment): it
  audits the records, fills firmographics from Apollo and flags conflicts.
  It also covers the first half of idea #1: a plain-English ICP turned into
  a prioritized list. The ranked contacts in idea #1 are not built. Apollo's
  free plan blocks people search, so that is a next step.
- **It shows how to use Apollo data with care.** Trust it where it matches.
  Flag it where it conflicts, as with the 9 name mismatches and the
  headquarters-versus-site locations. Never let it overrule what the
  company's own website says.
- **It is the kind of tool this team builds:** account planning and territory
  design for a revenue team, on Apollo data.

## Who uses it and what they get

- **Sales leader:** the interactive planner. Drag the radius, turn marquee
  accounts on or off, reassign accounts by hand, and watch the books
  rebalance live. Their choices feed back into the official plan.
- **Rep:** their book. That is a list of fits in their territory, with the
  sentence each grade rests on.
- **Enterprise team:** a handoff list of chain and large-company fits.
- **RevOps:** the data-hygiene audit, with a proposed fix for every record
  problem, and a Needs Review queue with a reason on every account.

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
5  Set up      Asks the user how to build territories: by state, or around
   |           marquee accounts (CRM account ID or coordinates) + radius.
6  Territories Mid-Market Fits go to a territory using CRM locations only,
   |           then the books are balanced. Manager overrides are kept.
   |           Enterprise Fits go to a handoff list; Needs Review to its own.
   |           Builds the interactive planner page.
7  Hygiene     Every record problem, each with a proposed fix.
```

Scripts do all the data work. The model makes one judgment per account and
never invents a fact or changes the policy.

## Install and run

Setup and the normal way to run it are in the [README](../README.md). To run
the scripts by hand, from the project folder:

```
python3 .claude/skills/icp-territory/scripts/enrich_accounts.py
python3 .claude/skills/icp-territory/scripts/fetch_evidence.py
python3 .claude/skills/icp-territory/scripts/grading.py batch --size 10   # Claude grades these
python3 .claude/skills/icp-territory/scripts/grading.py check
python3 .claude/skills/icp-territory/scripts/validate.py
python3 .claude/skills/icp-territory/scripts/territories.py
python3 .claude/skills/icp-territory/scripts/territory_map.py
python3 .claude/skills/icp-territory/scripts/hygiene_report.py
```

The example CRM list is a stand-in built from OpenStreetMap. `setup/`
rebuilds it and needs `curl`; you do not need to run it. Apollo's data is
not in this repo. Run enrichment with your own key to create it.

## Results

**Apollo enrichment (136 accounts)**
This is the audit that the data-hygiene idea in the brief asks for. Gaps and
conflicts are found and flagged, not guessed over.

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

**Territories (3 marquee accounts, made up but at real ZIP codes; 60-mile
radius, balanced with a 90-mile stretch radius)**

| Territory | Marquee account | Before balancing | After | Below equal share (4) |
|-----------|-----------------|------------------|-------|------------------------|
| Chicagoland | Schaumburg, IL 60173 | 6 | 6 | 0 |
| Milwaukee | Milwaukee, WI 53202 | 3 | 4 | 0 |
| Michiana | South Bend, IN 46601 | 2 | 2 | 2 |

- **Balancing evens out the books, the way I did it in my current role.**
  Every fit counts the same, and the equal share is 4.
  - Milwaukee claimed Twisted Fitness in Madison (73 mi) with the stretch
    radius.
  - Chicagoland stays at 6. None of its fits are in range of another rep.
  - Michiana cannot reach 4: there are no unclaimed fits within 90 miles of
    South Bend.

  That is a decision for the sales leader: a second marquee account, a
  wider radius, or a shared rep.
- 12 of 17 Mid-Market Fits fall inside a territory. 5 are still out of
  range: Oshkosh (76 mi), plus Peoria, Mahomet, Springfield and Eau Claire
  at 120 to 217 miles. That points to a missing downstate Illinois
  territory.
- 2 assigned Fits rely on a low-confidence CRM location and are flagged.
- **Enterprise handoff:** 7 Fits (chain locations such as LA Fitness,
  Equinox, Life Time). They go to the enterprise team, not a regional rep.
- **Needs Review:** 42 accounts, 9 of them Enterprise and listed first.

**Territory planner (`example/territory_map.html`, live at
https://vtderise-collab.github.io/apollo-icp-territory-skill/example/territory_map.html).**
A sales leader can try changes on the map: radius, stretch radius,
balancing, book-size goal, marquee accounts on or off, and manual assignment
of any fit. The books table and findings update live.
- "Download overrides" saves the manual choices as
  `territory_overrides.csv`. The skill applies them on the next run, and
  balancing never moves them.
- The page carries its own copy of the rules (`assets/planner.js`). That
  copy could drift from the Python, so every build runs it with Node and
  checks it reproduces `territory_plan.csv` exactly. I tested that check
  across seven settings, including manual overrides.

**Two ways to build territories.** The skill asks the user which one; it
never assumes.
- **Around marquee accounts** (the example): name one marquee customer per
  territory, by CRM account ID or by coordinates, plus a radius. Each fit
  goes to the nearest marquee account in range. The books are then
  balanced, with every fit counted the same. Contested fits go to the
  shorter book, and short books may claim unclaimed fits within a stretch
  radius. This mirrors how I built territories in my current role.
- **By state:** one territory per state. The same fits come out as Illinois
  9, Wisconsin 4, Indiana 1. Three fits can't be placed because their CRM
  record has no state. Illinois's 9 fits span 180 miles, and there is no
  coverage-gap signal.

**Data-hygiene audit (`data/data_hygiene.csv`):** 164 issues on 105 of 136
accounts, each with a proposed fix. Nothing is applied to the CRM.

| Issue | Count |
|---|---|
| Website could not be read | 40 |
| No Apollo record | 34 |
| CRM record missing city or state | 28 |
| Apollo headquarters in a different state than the CRM site | 27 |
| Low-confidence CRM location | 20 |
| Apollo name mismatch (Apollo data ignored) | 9 |
| Site-builder or social page instead of a company domain | 5 |
| Industry tag contradicted by the website | 1 |

A run writes its outputs to `data/`. This example run's outputs are
committed in `example/`: `territory_plan.csv`, `territory_summary.csv`,
`enterprise_handoff.csv`, `needs_review.csv`, `data_hygiene.csv`,
`graded.csv` and `territory_map.html`. The repo ships `data/` with only the
inputs, so every new run starts clean.

## Why a skill, not a script or an MCP call

- **The core step is a judgment.** Reading a website and deciding whether
  members use a machine floor needs a model. Everything around it (calls,
  caching, distance math, scoring) is deterministic, so it lives in scripts.
  A skill packages both, with instructions for when to use each.
- **The policy is a file the business owns.** `icp.md` is plain English that
  a sales leader can read and change. The model applies it and the skill
  forbids it from editing it.
- **Apollo is called by API from a script, not through MCP.** A direct
  Apollo MCP call would return data, not a decision. It has no
  policy, no evidence trail and no validation. On the free plan, Apollo's
  search is blocked anyway. Only enrichment works.
- **A plain script would hard-code the prompt** and hide the judgment step.
  The skill keeps that step visible and checked: every grade has a verified
  quote, and nothing is trusted until it passes the fixture.

How the data is shaped for the model: one record per account with the name,
the Apollo tag and the website text, ten at a time. The output is one JSON
line with a fixed set of grades and reason codes. Anything that does not
parse, or quotes text that is not on the site, becomes Needs Review.

Deliberately left out of v1:
- Ranked contacts. Apollo's free plan blocks people search.
- Letting Apollo data nudge a grade.
- Applying hygiene fixes. The skill only proposes them.
- Writing results back to the CRM.

## Assumptions

- The business keeps its prospects in its CRM (Salesforce, for example).
  For this proof of concept the skill reads a CSV export of that CRM.
  Apollo enriches the accounts; it does not source them.
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
- In balancing, every fit counts the same. A rep's book is fair when it has
  the same number of fits, not the same revenue potential. That is
  deliberately simple for v1.
- The CRM export has no last-activity or last-updated dates. So the hygiene
  audit checks gaps and conflicts, but not staleness. Staleness checks are a
  next step once the export carries those dates.

## Where AI helped and where I overrode it

I ran the grading in a separate Claude session that never saw my hand
labels. I decided what to act on below.

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
- **Territories.** It built territories one fixed way and never asked. I
  made the skill ask: by state, or around marquee accounts the user names.
  It is never allowed to pick or locate a marquee account itself.

How I checked the finished skill: I ran it in fresh Claude sessions with no
history, asking only "Which of my CRM accounts are real fits? Build
territories for my reps."
- The first run counted CSV lines instead of rows. Company descriptions
  contain line breaks, so it read 136 accounts as 153. It then planned to
  regrade everything, which would have thrown away validated grades. I
  added a "check what is already done" step, and the retest went straight
  to the existing results.
- A later run reported "~56 Needs Review" when the scripts said 42. I added
  a rule: every number must come from script output, never an estimate.
- The planner page carries its own copy of the territory rules. Every build
  runs that copy and checks it matches the Python plan exactly. I tested
  this across seven settings, including manual overrides.

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
  - Connect to Salesforce directly through its CLI or an MCP server, so one
    skill run pulls the accounts, grades them and builds territories, with
    no manual export.
  - Batch and parallelize the scrape.
  - Write grades back to the CRM only after a manager approves the
    territory plan.
- **Planner:**
  - The page keeps a second copy of the territory rules. Today a test
    catches drift. In production, both should run from one shared rules
    service.
  - Manager overrides should carry who made them, when, and why, as an
    audit trail.
  - Approval should happen in the planner rather than by passing a CSV.

## Rollout and success plan

In my current role this went to the whole mid-market team at once, because
leadership was testing how territories built around marquee accounts
performed. For Rackwell I would roll it out in three steps.

1. **Pilot with a comparison.** Half the mid-market reps work from the
   skill's books for one quarter. The other half keep their current lists.
   A whole-team launch cannot show whether the skill made the difference. A
   split can.
2. **Keep managers in the loop.** The sales leader signs off on the
   territory plan before anyone's book changes. Managers still approve
   account ownership changes and holdover requests, where a rep asks to keep
   an account from an old territory. Only the policy owner changes the ICP,
   and only after the fixture passes again.
3. **Label the CRM, then expand.** Write the grade, segment and territory
   onto each CRM account, so every report can split by fit and by territory.
   Then roll out to the full team.

What I would track. These are targets, not results, since a prototype has
none. Baselines come from the first month.
- **Fit conversion:** the opportunity and close rate of Fit accounts,
  compared with the rest of the book. The target is that Fits clearly
  outperform.
- **Territory performance:** pipeline and close rate per territory, to see
  which carves work and where coverage is thin.
- **Marquee pull-through:** referrals and new opportunities near each
  marquee anchor account.
- **Guardrail:** a monthly sample of live grades stays at or above the 90%
  bar.

## What was pre-existing

> The approach comes from an ICP classifier and territory assigner I designed and ran in my current role. Nothing from that build is in this repo. I rewrote it from scratch for this exercise on public data: a different company, a different ICP, Apollo enrichment, and a skill in place of a standalone script.

Everything here was written new for this exercise with Claude Code.

## More of my work

A RevOps hub demo with its architecture: https://revops-hub-demo-vtderise-collabs-projects.vercel.app/architecture
