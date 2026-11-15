#!/usr/bin/env python3
"""Stage 3: check the grader against hand labels before trusting it.

Compares data/graded.csv with data/validation_labels.csv (labeled by the
policy owner before any grading). Reports two separate numbers:

  1. Scrape coverage: how many accounts the pipeline could read at all.
     Unreadable accounts are graded Needs Review by a script, never by the
     model, so they say nothing about grading quality.
  2. Grading accuracy on the labeled, readable accounts: overall, per grade,
     a confusion matrix and every miss with its evidence line.

The pass bar is fixed in PASS_BAR and was set before the first run.

Run from the repo root:  python3 icp-territory/scripts/validate.py
"""
import csv
import json
import sys

from common import DATA

PASS_BAR = {"overall": 0.90, "Fit": 0.85, "Unlikely": 0.85}   # set 11/14, do not move
GRADES = ["Fit", "Needs Review", "Unlikely"]


def main():
    evidence = [json.loads(l) for l in open(DATA / "evidence.jsonl")]
    readable = sum(1 for e in evidence if e["scrape_status"] == "ok")
    print(f"Scrape coverage: {readable} of {len(evidence)} accounts readable "
          f"({readable / len(evidence):.0%}). Not part of grading accuracy.\n")

    labels_path = DATA / "validation_labels.csv"
    if not labels_path.exists():
        print("No hand labels found, so these grades are NOT validated.\n"
              "To validate: pick about 30 accounts, write the grade you expect for each in\n"
              "data/validation_labels.csv (columns: account_id,name,website,expected_grade,why),\n"
              "then run this again. Treat the grades as a draft until then.")
        return
    labels = {r["account_id"]: r for r in csv.DictReader(open(labels_path))}
    graded = {r["account_id"]: r for r in csv.DictReader(open(DATA / "graded.csv"))}
    missing = [a for a in labels if a not in graded or not labels[a]["expected_grade"]]
    if missing:
        sys.exit(f"Not ready: unlabeled or ungraded accounts: {', '.join(missing)}")

    pairs = [(labels[a]["expected_grade"], graded[a]["grade"], a) for a in labels]
    correct = sum(e == g for e, g, _ in pairs)
    overall = correct / len(pairs)
    print(f"Grading accuracy: {correct} of {len(pairs)} = {overall:.0%} "
          f"(bar {PASS_BAR['overall']:.0%})")

    passed = overall >= PASS_BAR["overall"]
    for grade in GRADES:
        rows = [(e, g) for e, g, _ in pairs if e == grade]
        if not rows:
            continue
        acc = sum(e == g for e, g in rows) / len(rows)
        bar = PASS_BAR.get(grade)
        flag = "" if bar is None else f" (bar {bar:.0%})"
        print(f"  {grade:<13} {sum(e == g for e, g in rows)}/{len(rows)} = {acc:.0%}{flag}")
        if bar is not None and acc < bar:
            passed = False

    print("\nConfusion matrix (rows = your label, columns = grader):")
    print(" " * 15 + "".join(f"{g:>14}" for g in GRADES))
    for e in GRADES:
        print(f"{e:<15}" + "".join(
            f"{sum(1 for x, y, _ in pairs if x == e and y == g):>14}" for g in GRADES))

    misses = [(e, g, a) for e, g, a in pairs if e != g]
    print(f"\nMisses ({len(misses)}):")
    for e, g, a in misses:
        print(f"  {a} {labels[a]['name']}: expected {e}, got {g}")
        print(f"     your why: {labels[a]['why']}")
        print(f"     grader evidence: {graded[a]['evidence'] or graded[a]['reason_code']}")

    print("\nRESULT:", "PASS" if passed else "FAIL")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
