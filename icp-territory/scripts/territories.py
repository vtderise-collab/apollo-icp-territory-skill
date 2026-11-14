#!/usr/bin/env python3
"""Stage 4: turn graded accounts into a territory plan. No model, no network.

Inputs
  data/graded.csv       grades from Stage 2 (Fit / Needs Review / Unlikely)
  data/crm_export.csv   CRM location (lat/lon). The only location used:
                        Apollo returns headquarters, not the local site.
  data/accounts.csv     segment (Enterprise / Mid-Market) from Stage 0
  config.json           anchors, one radius, target per territory

Rules
  - Mid-Market Fits only go into territories. Each one goes to its nearest
    anchor if that anchor is within the radius (great-circle miles). Other
    anchors also in range are listed as secondary.
  - Mid-Market Fits outside every radius are listed as out of range.
  - Enterprise Fits go on a separate handoff list, never into a territory.
  - Fits with no CRM location are listed, never guessed.
  - location_match other than zip/city is flagged "check location"; the
    account is still assigned.
  - Needs Review goes on its own list, Enterprise first.

Outputs (data/)
  territory_plan.csv     every Mid-Market Fit: territory or why not
  territory_summary.csv  one row per territory
  enterprise_handoff.csv Enterprise Fits
  needs_review.csv       Needs Review accounts, Enterprise first

Run from the repo root:  python3 icp-territory/scripts/territories.py
"""
import csv
import json
import math

from common import DATA, SKILL_DIR

TRUSTED_LOCATION = {"zip", "city"}


def miles(lat1, lon1, lat2, lon2):
    """Great-circle distance in miles (haversine)."""
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def write(name, rows, fields):
    with open(DATA / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    cfg = json.load(open(SKILL_DIR / "config.json"))["territories"]
    radius, target, anchors = cfg["radius_miles"], cfg["target_per_territory"], cfg["anchors"]

    crm = {r["account_id"]: r for r in csv.DictReader(open(DATA / "crm_export.csv"))}
    segment = {r["account_id"]: r["segment"] for r in csv.DictReader(open(DATA / "accounts.csv"))}
    graded = list(csv.DictReader(open(DATA / "graded.csv")))

    plan, enterprise, review = [], [], []
    for g in graded:
        aid = g["account_id"]
        c = crm[aid]
        seg = segment.get(aid, "Mid-Market")
        base = {"account_id": aid, "name": g["name"], "city": c["city"], "state": c["state"],
                "segment": seg, "evidence": g["evidence"]}

        if g["grade"] == "Needs Review":
            review.append({**base, "reason_code": g["reason_code"], "website": c["website"]})
            continue
        if g["grade"] != "Fit":
            continue
        if seg == "Enterprise":
            enterprise.append({**base, "website": c["website"]})
            continue

        row = {**base, "territory": "", "anchor": "", "miles": "", "also_in_range_of": "",
               "status": "", "location_check": ""}
        if c["location_match"] not in TRUSTED_LOCATION:
            row["location_check"] = f"check location ({c['location_match'] or 'none'})"
        if not c["lat"] or not c["lon"]:
            row["status"] = "no location in CRM"
            plan.append(row)
            continue

        dist = sorted((miles(float(c["lat"]), float(c["lon"]), a["lat"], a["lon"]), a) for a in anchors)
        d, nearest = dist[0]
        if d <= radius:
            row.update(territory=nearest["territory"], anchor=nearest["anchor"], miles=round(d),
                       status="assigned",
                       also_in_range_of="; ".join(f"{a['territory']} ({round(x)} mi)"
                                                  for x, a in dist[1:] if x <= radius))
        else:
            row.update(territory="", anchor=f"nearest: {nearest['territory']}", miles=round(d),
                       status="out of range")
        plan.append(row)

    plan.sort(key=lambda r: (r["status"] != "assigned", r["territory"], r["miles"] if r["miles"] != "" else 9999))
    review.sort(key=lambda r: (r["segment"] != "Enterprise", r["reason_code"], r["name"]))

    summary = []
    for a in anchors:
        mine = [r for r in plan if r["territory"] == a["territory"]]
        summary.append({
            "territory": a["territory"], "anchor": a["anchor"],
            "anchor_location": f"{a['city']}, {a['state']} {a['postal_code']}",
            "assigned": len(mine), "target": target, "shortfall": max(0, target - len(mine)),
            "secondary_overlaps": sum(1 for r in mine if r["also_in_range_of"]),
            "farthest_miles": max((r["miles"] for r in mine), default=""),
            "location_checks": sum(1 for r in mine if r["location_check"]),
        })

    write("territory_plan.csv", plan,
          ["account_id", "name", "city", "state", "segment", "status", "territory", "anchor",
           "miles", "also_in_range_of", "location_check", "evidence"])
    write("territory_summary.csv", summary, list(summary[0].keys()))
    write("enterprise_handoff.csv", enterprise,
          ["account_id", "name", "city", "state", "segment", "website", "evidence"])
    write("needs_review.csv", review,
          ["account_id", "name", "city", "state", "segment", "reason_code", "website", "evidence"])

    # ---- report ----
    print(f"Radius {radius} miles, target {target} per territory. CRM coordinates only.\n")
    print(f"{'Territory':<12} {'Anchor':<38} {'Assigned':>8} {'Short':>5} {'Farthest':>8} {'Overlap':>7} {'Loc check':>9}")
    for s in summary:
        print(f"{s['territory']:<12} {s['anchor']:<38} {s['assigned']:>8} {s['shortfall']:>5} "
              f"{str(s['farthest_miles']) + ' mi' if s['farthest_miles'] != '' else '-':>8} "
              f"{s['secondary_overlaps']:>7} {s['location_checks']:>9}")

    out = [r for r in plan if r["status"] == "out of range"]
    noloc = [r for r in plan if r["status"] == "no location in CRM"]
    assigned = [r for r in plan if r["status"] == "assigned"]
    mm_fits = len(plan)

    print("\nFindings")
    print(f"- {len(assigned)} of {mm_fits} Mid-Market Fits fall inside a territory; "
          f"{len(out)} are out of range and {len(noloc)} have no CRM location.")
    for s in summary:
        if s["shortfall"]:
            print(f"- {s['territory']} is {s['shortfall']} short of its target of {target} "
                  f"({s['assigned']} assigned).")
    deepest = max(summary, key=lambda s: s["assigned"])
    if deepest["assigned"] > target:
        print(f"- {deepest['territory']} has the deepest pool: {deepest['assigned']} Fits, "
              f"{deepest['assigned'] - target} over target.")
    if out:
        far = ", ".join(f"{r['name']} ({(r['city'] + ' ' + r['state']).strip() or 'no city in CRM'}, "
                        f"{r['miles']} mi from {r['anchor'][9:]})"
                        for r in sorted(out, key=lambda r: r["miles"]))
        print(f"- Out of range: {far}.")
    overlaps = [r for r in assigned if r["also_in_range_of"]]
    if overlaps:
        print(f"- {len(overlaps)} assigned account(s) are also in range of a second anchor: "
              + "; ".join(f"{r['name']} in {r['territory']}, also {r['also_in_range_of']}" for r in overlaps) + ".")
    checks = [r for r in plan if r["location_check"]]
    if checks:
        print(f"- {len(checks)} Fit(s) rely on a low-confidence CRM location: "
              + ", ".join(r["name"] for r in checks) + ".")
    ent_review = sum(1 for r in review if r["segment"] == "Enterprise")
    print(f"- Enterprise handoff: {len(enterprise)} Fits for the enterprise team, not in any territory.")
    print(f"- Needs Review: {len(review)} accounts ({ent_review} Enterprise, listed first).")
    print("\nWrote data/territory_plan.csv, territory_summary.csv, enterprise_handoff.csv, needs_review.csv")


if __name__ == "__main__":
    main()
