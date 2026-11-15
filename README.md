# ICP territory skill

A Claude Code skill for revenue teams. It takes your CRM account list and
grades every account against your ideal customer profile (ICP), using the
company's own website as evidence. It enriches each account with Apollo,
builds balanced rep territories from the real fits, and audits your records
for data problems.

**Try the territory planner:** https://vtderise-collab.github.io/apollo-icp-territory-skill/example/territory_map.html

**What you provide**

| Input | How |
|---|---|
| CRM account list | `data/crm_export.csv`: name, website, city, state, coordinates |
| Your ICP | Plain English in `icp-territory/references/icp.md` |
| Apollo API key | `.env`. The free plan works for enrichment. |
| How to build territories | The skill asks you: by state, or around marquee accounts you name (by CRM account ID or coordinates) with a radius |

**What you get back**
- **A book for each rep:** the fits in their territory, each with the
  sentence from the company's website that the grade rests on.
- **Balanced territories:** each rep gets about the same number of fits.
  Books that can't be balanced, and fits no territory covers, are called
  out.
- **An interactive planner:** a sales leader drags the radius, turns marquee
  accounts on or off, and reassigns accounts by hand, watching the books
  update live. Their choices feed back into the official plan.
- **An Enterprise handoff list:** chain and large-company fits, routed away
  from regional reps.
- **A Needs Review queue:** accounts it could not see clearly, each with a
  reason. Nothing is guessed.
- **A data-hygiene audit:** every record problem (CRM gaps, Apollo
  conflicts, unreadable websites), each with a proposed fix.

## Why it matters

Most CRMs hold thousands of prospect accounts that nobody has qualified.
Industry tags can't tell a real fit from a look-alike. In the example,
gyms, yoga studios and massage spas share one tag. So reps call accounts that
will never buy, and territories get drawn around the wrong accounts.

Grading by hand takes about 50 seconds an account. At 50,000 accounts (an
example size), that is about 700 hours. This skill runs unattended, puts a
checkable quote on every grade, and tests itself against hand labels before
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

Systems touched:
- Apollo, through its live API.
- Company websites, read directly. This is not a web search.
- A CRM export, as CSV.
- CSV and HTML outputs.

Scripts do all the data work. The model makes one judgment per account. It
never supplies a fact, picks a marquee account, or edits the ICP.

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

The repo ships `data/` with only the example inputs, so a new run starts
clean. The example run's finished outputs are in `example/`. The skill
checks what is already done first, so it never reruns finished, validated
work. `setup/` only rebuilds the example data, and it needs
`curl`.

## Example run

Rackwell is a made-up company that sells gym equipment in Illinois,
Wisconsin and Indiana. Its CRM holds 136 prospect accounts. Territories are
built around 3 made-up marquee accounts at real ZIP codes, with a 60-mile
radius.

| Result | |
|---|---|
| Fits found | 24 (and 70 Unlikely) |
| Rep books after balancing (equal share 4) | Chicagoland 6, Milwaukee 4, Michiana 2 |
| Fits no territory covers | 5, mostly downstate Illinois |
| Enterprise handoff / Needs Review | 7 / 42 |
| Data-hygiene audit | 164 issues on 105 accounts, each with a proposed fix |
| Validation (30 hand labels, 90% bar) | 77%, then 87% after an evidence fix. 26 of 27 on readable sites. |

Michiana can't reach the equal share with its current marquee account, so
the plan says so and lists the options. In the planner, turn Michiana off,
or widen its stretch radius, and watch the books move.

## Design in brief

- **Why a skill:** grading is a judgment, so it needs a model. Everything
  else is deterministic, so it lives in scripts. The policy is a file the
  business owns. A direct Apollo MCP call returns data, not a decision.
- **Model input and output:** one record per account goes in. One JSON line
  comes out, with a fixed grade and a quote. Anything malformed or unquoted
  becomes Needs Review.
- **Left out of v1:** ranked contacts (Apollo's free plan blocks people
  search), applying hygiene fixes, and CRM write-back.

## More

- [Full write-up](docs/WRITEUP.md): the problem, assumptions, design, where
  AI helped and where I overrode it, territory methods, rollout plan,
  production hardening, and what was pre-existing.
- [One-pager](ONE-PAGER.md)
- More of my work: https://revops-hub-demo-vtderise-collabs-projects.vercel.app/architecture
