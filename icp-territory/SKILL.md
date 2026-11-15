---
name: icp-territory
description: Grade a CRM's prospect accounts against a written ideal customer profile using each company's own website as evidence, then build a territory plan of the fits nearest each rep's anchor customers. Use when asked to qualify, score or clean up an account list against an ICP, find which prospects are real fits, or build or rebalance territories or books of business.
---

# ICP territory skill

Turns an unqualified account list into a territory plan. Scripts do all data
work. You make exactly one judgment per account: its grade under the written
ICP in `references/icp.md`. You never supply a fact, and you never change
the ICP.

Run every command from the project folder, which holds `data/` and `.env`.
`<skill>` below is this skill's folder: `icp-territory` in the repo, or
`.claude/skills/icp-territory` once installed.

## Check what is already done (always first)

Earlier steps are cached and may already be finished. Check before running
anything, and start at the first step that is not done:

- `data/accounts.csv` exists: enrichment is done.
- `data/evidence.jsonl` exists: evidence is done.
- `python3 <skill>/scripts/grading.py batch --size 1` prints "0 readable
  accounts left to grade": grading is done. Run the check, then go to
  validate or territories.

Rules for reading state and reporting:
- Every number you report to the user must come from a script's printed
  output or a CSV reader. Never estimate or round ("~56"). If you have not
  counted it, do not state it.
- Never count CSV lines to count accounts. Fields contain line breaks. Use
  the scripts' own counts, or a CSV reader.
- Unreadable websites are graded Needs Review by a script, not by you. Fewer
  lines in `grades.jsonl` than accounts is normal, not a partial run.
- Do not regrade or re-enrich anything already done unless the user asks.
  Regrading throws away grades that were validated. Re-enrichment spends
  Apollo credits.

## Steps

1. **Enrich** with Apollo (needs `APOLLO_API_KEY` in `.env`):
   `python3 <skill>/scripts/enrich_accounts.py`
   Cached, batched by 25, stops at the first credit or plan error. Report the
   stop to the user; do not retry around it.
2. **Gather evidence** from each website:
   `python3 <skill>/scripts/fetch_evidence.py`
3. **Grade** (your step). Read `references/icp.md` in full first. Then loop:
   - `python3 <skill>/scripts/grading.py batch --size 10`
     (add `--ids data/validation_labels.csv` to grade the validation set only)
   - For each record printed, append one line to `data/grades.jsonl` (format
     below).
   - Repeat until the batch command says 0 left.
   - `python3 <skill>/scripts/grading.py check`
   Report every FAILED CHECK line to the user as is.
4. **Validate** before trusting any grades:
   `python3 <skill>/scripts/validate.py`
   If it fails the pass bar, show the misses. Do not edit the ICP yourself;
   propose changes and wait for the policy owner.
5. **Set up territories with the user** (always ask; never assume).
   Show what `config.json` -> `territories` holds now, then ask:
   - **Method:** by state (one territory per state in `region_states`), or
     around marquee accounts (one territory per marquee customer, fits go to
     the nearest one within a radius)?
   - **If marquee:** which accounts? Each needs a CRM `account_id` (location
     comes from the CRM) or a latitude and longitude from the user. Also ask
     for the radius in miles, and whether to balance the books (each rep
     gets about the same number of fits). If balancing, ask for a stretch
     radius: how far a short book may reach for unclaimed fits.
   - **Target book size** per territory (used only to report shortfall).
   Never look up, estimate or invent a location or an account. If the user
   gives a marquee account with neither an account_id nor coordinates, ask
   again. Write the answers to `config.json`, read them back to the user,
   and build only after they confirm. If they say "keep the current setup",
   use it as is.
6. **Build territories**: `python3 <skill>/scripts/territories.py`
   Writes `data/territory_plan.csv`, `territory_summary.csv`,
   `enterprise_handoff.csv` and `needs_review.csv`. Show the user the
   summary table and the findings as printed; do not add numbers of your own.
   Then draw the map: `python3 <skill>/scripts/territory_map.py`
   (writes `data/territory_map.html`; open it in a browser).
7. **Data-hygiene audit**: `python3 <skill>/scripts/hygiene_report.py`
   Writes `data/data_hygiene.csv`: one row per problem in the records
   (CRM gaps, Apollo conflicts, unreadable sites) with a proposed fix. It
   proposes fixes only. Do not change the CRM export or apply fixes unless
   the user asks.

## Grading rules

- Grade only from the record's `text`. No outside knowledge of the business,
  even if you recognize the name.
- Apply the one rule in `references/icp.md`. The examples there illustrate
  it; they are not extra rules.
- `apollo_industry_tag` decides nothing. Set `tag_disagrees` to true when the
  website clearly contradicts it.
- Needs Review only for the reason codes listed in the ICP. Never use it for
  "the policy is unclear".
- Size, headquarters and chain status play no part in the grade.

## Output format: one JSON object per line in data/grades.jsonl

```json
{"account_id": "ACC-0014", "grade": "Fit", "evidence_quote": "<exact words copied from text>", "reason_code": "", "confidence": "high", "tag_disagrees": false}
```

- `grade`: exactly `Fit`, `Needs Review` or `Unlikely`.
- `evidence_quote`: 8 to 25 words copied exactly from `text`, the words the
  grade rests on. The checker rejects any quote not found in the text, and
  that account becomes Needs Review.
- `reason_code`: required for Needs Review (`parked_or_empty`,
  `wrong_business`, `cannot_tell`), empty otherwise.
- `confidence`: `high`, `medium` or `low`.

Write nothing else to the file: no commentary, no blank grades.
