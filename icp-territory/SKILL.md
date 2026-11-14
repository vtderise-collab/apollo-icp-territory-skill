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
5. **Build territories**: `python3 <skill>/scripts/territories.py`
   Anchors, radius and target live in `config.json` under `territories`.
   Writes `data/territory_plan.csv`, `territory_summary.csv`,
   `enterprise_handoff.csv` and `needs_review.csv`. Show the user the
   summary table and the findings as printed; do not add numbers of your own.
   Last, draw the map: `python3 <skill>/scripts/territory_map.py`
   (writes `data/territory_map.html`; open it in a browser).

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
