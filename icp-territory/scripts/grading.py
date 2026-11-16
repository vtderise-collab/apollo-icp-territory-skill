#!/usr/bin/env python3
"""Step 3 helpers: hand records to the grader, then check what comes back.

The model makes one judgment per account. Everything around it is code:

  batch   Print the next ungraded, readable evidence records for the agent
          to grade. Records whose scrape failed are never sent to the model;
          `check` grades them Needs Review with the failure as the reason.
  check   Validate data/grades.jsonl against the rules and the evidence, and
          write data/graded.csv. A grade that fails a check becomes Needs
          Review (invalid_output). It is never repaired by guessing.

Checks: grade is one of three values; Needs Review carries an allowed
reason_code; Fit and Unlikely carry a quote that really appears in that
account's scraped text (so the evidence line cannot be invented).

Usage (from the project folder):
  python3 <skill>/scripts/grading.py batch --size 10 [--ids FILE]
  python3 <skill>/scripts/grading.py check
"""
import argparse
import csv
import json
import re
import sys

from common import DATA, need

GRADES = {"Fit", "Needs Review", "Unlikely"}
REASONS = {"scrape_failed", "parked_or_empty", "wrong_business", "cannot_tell"}
FAILED_TO_REASON = lambda s: "parked_or_empty" if s in ("parked", "thin_content") else "scrape_failed"


def load_evidence():
    with open(DATA / "evidence.jsonl") as f:
        return {r["account_id"]: r for r in map(json.loads, f)}


def load_grades():
    p = DATA / "grades.jsonl"
    out = {}
    if p.exists():
        for n, line in enumerate(p.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                g = json.loads(line)
                out[g["account_id"]] = g
            except (ValueError, KeyError, TypeError):
                print(f"line {n} of grades.jsonl does not parse; ignored", file=sys.stderr)
    return out


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def cmd_batch(args):
    ev, done = load_evidence(), load_grades()
    ids = None
    if args.ids:
        ids = {l.strip().split(",")[0] for l in open(args.ids) if l.strip()}
    todo = [r for aid, r in ev.items()
            if r["scrape_status"] == "ok" and aid not in done
            and (ids is None or aid in ids)]
    for r in todo[: args.size]:
        print(json.dumps({k: r[k] for k in ("account_id", "name", "apollo_industry_tag", "text")}))
    print(f"# {len(todo)} readable accounts left to grade; showed {min(len(todo), args.size)}",
          file=sys.stderr)


def check_one(g, ev):
    """Return (grade, reason_code, evidence, problem)."""
    grade, quote = g.get("grade"), (g.get("evidence_quote") or "").strip()
    if grade not in GRADES:
        return "Needs Review", "invalid_output", "", f"grade not allowed: {grade!r}"
    if grade == "Needs Review":
        rc = g.get("reason_code")
        if rc not in REASONS:
            return "Needs Review", "invalid_output", quote, f"bad reason_code {rc!r}"
        return grade, rc, quote, ""
    if len(norm(quote)) < 8 or norm(quote) not in norm(ev["text"]):
        return "Needs Review", "invalid_output", quote, "quote not found in website text"
    return grade, "", quote, ""


def cmd_check(_):
    ev, grades = load_evidence(), load_grades()
    rows, problems, ungraded = [], [], 0
    for aid, r in ev.items():
        if r["scrape_status"] != "ok":
            grade, rc, quote, src = ("Needs Review", FAILED_TO_REASON(r["scrape_status"]),
                                     f"Website could not be read: {r['scrape_status']}", "script")
        elif aid in grades:
            grade, rc, quote, problem = check_one(grades[aid], r)
            src = "model"
            if problem:
                problems.append(f"{aid} {r['name']}: {problem}")
        else:
            ungraded += 1
            continue
        g = grades.get(aid, {})
        rows.append({"account_id": aid, "name": r["name"], "grade": grade,
                     "reason_code": rc, "evidence": quote,
                     "confidence": g.get("confidence", "") if src == "model" else "",
                     "tag_disagrees": g.get("tag_disagrees", "") if src == "model" else "",
                     "graded_by": src})
    with open(DATA / "graded.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    counts = {}
    for r in rows:
        counts[r["grade"]] = counts.get(r["grade"], 0) + 1
    print(f"Graded {len(rows)} ({ungraded} readable accounts not graded yet): {counts}")
    for p in problems:
        print("  FAILED CHECK ->", p)


def main():
    need('evidence.jsonl')
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("batch")
    b.add_argument("--size", type=int, default=10)
    b.add_argument("--ids", help="CSV whose first column is account_id")
    sub.add_parser("check")
    args = ap.parse_args()
    {"batch": cmd_batch, "check": cmd_check}[args.cmd](args)


if __name__ == "__main__":
    main()
