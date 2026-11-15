# ICP territory skill

A Claude Code skill for revenue teams. It takes your CRM account list and
grades every account against your ideal customer profile (ICP), using the
company's own website as evidence. It enriches each account with Apollo,
builds rep territories from the real fits, and audits your records for data
problems.

**What you provide**

| Input | How |
|---|---|
| CRM account list | `data/crm_export.csv`: name, website, city, state, coordinates |
| Your ICP | Plain English in `icp-territory/references/icp.md` |
| Apollo API key | `.env`. The free plan works for enrichment. |
| How to build territories | The skill asks you. Choose by state, or around marquee accounts you name (by CRM account ID or coordinates) with a radius. Marquee books are balanced. |
| Target book size per territory | The skill asks you |

**What you get back**
- **A book for each rep:** the fits in their territory, each with the
  sentence from the company's website that the grade rests on.
- **Balanced territories:** each rep gets about the same number of fits.
  The summary shows coverage, any book that can't be balanced, and fits
  that no territory covers.
- **An interactive territory planner:** a map where a sales leader drags
  sliders (radius, stretch radius, book-size goal), turns marquee accounts
  on or off, and assigns any account by hand. The books and findings update
  live. Manual choices download as a file that the skill makes official on
  its next run.
- **An Enterprise handoff list:** chain and large-company fits, routed away
  from regional reps.
- **A Needs Review queue:** accounts it could not see clearly, each with a
  reason. Nothing is guessed.
- **A data-hygiene audit:** one row per problem in your records (CRM gaps,
  Apollo conflicts, unreadable websites), each with a proposed fix.

## Why it matters

Most CRMs hold thousands of prospect accounts that nobody has qualified.
Industry tags are too coarse to tell a real fit from a look-alike. In the
example data, gyms, yoga studios and massage spas all share one tag. So reps
call accounts that will never buy, and territories get drawn around the
wrong accounts.

Grading by hand takes about 50 seconds an account. At 50,000 accounts (an
example size) that is about 700 hours. This skill runs unattended. It puts a
checkable quote on every grade and tests itself against hand labels before
anyone trusts it.

## How it works

```
 CRM export (CSV) ──► 1 Enrich ◄── Apollo API: size, HQ, industry tag
                      2 Evidence ◄── each company's own website
                      3 Grade      Claude applies references/icp.md: Fit / Needs Review / Unlikely,
                                   with an exact quote that code verifies
                      4 Validate   scored against hand labels and a fixed pass bar
                      5 Set up     asks you: by state, or around marquee accounts + radius
                      6 Territories CRM locations only, balanced; manager overrides kept
                      7 Hygiene    every record problem, with a proposed fix
                         │
                         ▼
 territory_plan.csv · territory_summary.csv · enterprise_handoff.csv · needs_review.csv
 data_hygiene.csv · territory_map.html (interactive planner)
```

It touches four systems:
- **Apollo:** company enrichment over the live API.
- **Company websites:** read directly as evidence. This is not a web search.
- **A CRM export:** a CSV file.
- **CSV and HTML outputs:** written for the team.

Scripts do all the data work. The model makes one judgment per account. It
never supplies a fact, picks a marquee account, or edits the ICP.

**Two ways to build territories.** You choose; the skill never assumes.
- **Around marquee accounts.** Name your marquee customers, one per
  territory. Each real fit goes to the nearest one within your radius. Then
  the books are balanced so each rep gets about the same number of fits:
  - Contested fits go to the shorter book.
  - Short books may claim nearby unclaimed fits within a stretch radius.
  - A book that still can't be balanced is reported, with options.
  - Fits outside every radius are reported as coverage gaps.
- **By state.** One territory per state in your region. This is the simplest
  setup, but it cannot show coverage gaps, and it cannot place accounts whose
  CRM record has no state.

## Install and run

You need Python 3 (standard library only) and Claude Code.

1. Copy `icp-territory/` into your project's `.claude/skills/`.
2. Put your account list at `data/crm_export.csv`. This repo includes an
   example list.
3. Add `APOLLO_API_KEY=...` to `.env`, and write your ICP in
   `references/icp.md`.
4. In Claude Code, ask: "Which of my CRM accounts are real fits? Build
   territories for my reps." The skill asks how to build territories before
   it builds them.

The skill checks what is already done first, so it never reruns finished,
validated work. The `setup/` folder only rebuilds the example data, and
`setup/seed_crm_from_osm.py` needs `curl` on your path.

## Example run

The example uses Rackwell, a made-up company that sells gym equipment in
Illinois, Wisconsin and Indiana. Its CRM holds 136 prospect accounts. The
territories are built around 3 marquee accounts, which are made up but sit
at real ZIP codes, with a 60-mile radius.

| Result | |
|---|---|
| Fits found | 24 (and 70 Unlikely) |
| Rep books after balancing (equal share 4) | Chicagoland 6, Milwaukee 4, Michiana 2 |
| Fits no territory covers | 5, mostly downstate Illinois |
| Enterprise handoff / Needs Review | 7 / 42 |
| Data-hygiene audit | 164 issues on 105 accounts, each with a proposed fix |
| Validation (30 hand labels, 90% bar) | 77%, then 87% after an evidence fix. 26 of 27 on readable sites. |

Balancing pulled Madison into Milwaukee's book. Michiana can't reach the
equal share with its current marquee account, so the plan says so and lists
the options. Built by state instead, the same fits come out as Illinois 9,
Wisconsin 4, Indiana 1.
Three fits can't be placed because their CRM records have no state, and the
6-fit coverage gap disappears from view.

**Try the planner:** https://vtderise-collab.github.io/apollo-icp-territory-skill/data/territory_map.html
Drag the radius, or turn off Michiana and watch its fits move. Every time it
is built, a check confirms the page gives the same answer as the skill's own
script.

## Design in brief

- **Why a skill:** grading is a judgment, so it needs a model. Everything
  else is deterministic, so it lives in scripts. The policy is a file the
  business owns. A direct Apollo MCP call returns data, not a decision.
- **Model input and output:** one record per account goes in. Out comes one
  JSON line with a fixed grade and a quote. Anything malformed or unquoted
  becomes Needs Review.
- **Left out of v1:** ranked contacts (Apollo's free plan blocks people
  search), several radii, applying fixes, and CRM write-back.

## More

- [Full write-up](docs/WRITEUP.md): the problem, assumptions, design, where
  AI helped and where I overrode it, rollout plan, production hardening, and
  what was pre-existing.
- [One-pager](ONE-PAGER.md)
- More of my work: https://revops-hub-demo-vtderise-collabs-projects.vercel.app/architecture
