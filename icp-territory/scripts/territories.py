#!/usr/bin/env python3
"""Stage 4: turn graded accounts into a territory plan. No model, no network.

Two ways to build territories, chosen in config.json -> territories.method:

  "marquee"  One territory per marquee customer the user names. Each
             Mid-Market Fit goes to the nearest marquee account within the
             radius (great-circle miles). Fits outside every radius are
             listed as out of range: coverage gaps. A marquee account is
             given either as a CRM account_id (location taken from the CRM)
             or with lat/lon.
             With "balance": true, books are then evened out (fits count
             equally): see balance() below.
  "state"    One territory per state in the region. Each Mid-Market Fit goes
             to its CRM state. Fits outside the region are out of range.

Both methods
  - Use CRM locations only. Apollo returns headquarters, not the site.
  - Send Enterprise Fits to a separate handoff list, never a territory.
  - List Fits with no CRM location (or no state) instead of guessing.
  - Flag location_match other than zip/city as "check location".
  - Put Needs Review on its own list, Enterprise first.

Inputs   data/graded.csv, data/crm_export.csv, data/accounts.csv (segment),
         config.json
Outputs  data/territory_plan.csv, territory_summary.csv,
         enterprise_handoff.csv, needs_review.csv

Run from the project folder:  python3 <skill>/scripts/territories.py
"""
import collections
import csv
import json
import math
import sys

from common import DATA, SKILL_DIR

TRUSTED_LOCATION = {"zip", "city"}

STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "florida": "FL", "georgia": "GA",
    "hawaii": "HI", "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA",
    "kansas": "KS", "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD", "tennessee": "TN",
    "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
}


def state_code(value):
    """'Illinois' or 'IL' -> 'IL'. Blank or unknown -> ''."""
    v = (value or "").strip()
    if len(v) == 2 and v.upper() in STATES.values():
        return v.upper()
    return STATES.get(v.lower(), "")


def miles(lat1, lon1, lat2, lon2):
    """Great-circle distance in miles (haversine)."""
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def write(name, rows, fields):
    with open(DATA / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def resolve_anchors(anchors, crm):
    """Give every marquee account a location. A CRM account_id takes its
    lat/lon, city and state from the CRM. Stops if a location is missing:
    the model must never guess one."""
    out = []
    for a in anchors:
        a = dict(a)
        if a.get("account_id"):
            c = crm.get(a["account_id"])
            if not c or not c["lat"] or not c["lon"]:
                sys.exit(f"Marquee account {a['account_id']} has no location in the CRM. "
                         "Give lat/lon for it in config.json instead.")
            a.setdefault("anchor", c["name"])
            a.update(lat=float(c["lat"]), lon=float(c["lon"]),
                     city=a.get("city") or c["city"], state=a.get("state") or c["state"],
                     postal_code=a.get("postal_code") or c["postal_code"])
        elif a.get("lat") is None or a.get("lon") is None:
            sys.exit(f"Marquee account {a.get('anchor', '?')} needs an account_id or lat/lon.")
        out.append(a)
    return out


def balance(plan, anchors, radius, stretch):
    """Even out the books so each rep gets about the same number of fits.
    Every fit counts the same. Three moves, all reported:

    1. Fair share = in-range fits / number of territories, rounded up.
    2. Contested fits (in range of two marquee accounts) move from the
       fuller book to the shorter one, while that narrows the gap.
    3. A book still below fair share may claim unclaimed out-of-range fits
       within the stretch radius, nearest first, shortest book first.

    A book that is still short after both moves cannot be balanced with
    the current marquee accounts; that is reported, not hidden."""
    names = {a["territory"]: a["anchor"] for a in anchors}
    assigned = [r for r in plan if r["status"] == "assigned"]
    counts = collections.Counter(r["territory"] for r in assigned)
    for t in names:
        counts.setdefault(t, 0)
    before = dict(counts)
    fair = math.ceil(len(assigned) / len(names)) if names else 0

    def place(r, t, how):
        counts[r["territory"]] -= 1 if r["territory"] else 0
        r.update(territory=t, anchor=names[t], miles=round(r["_dist"][t]),
                 status="assigned", assigned_by=how)
        counts[t] += 1

    while True:  # 2. contested fits go to the shorter book
        moves = [(counts[r["territory"]] - counts[u], -r["_dist"][u], r, u)
                 for r in plan if r["status"] == "assigned" and r.get("_dist")
                 for u in names if u != r["territory"] and r["_dist"][u] <= radius
                 and counts[r["territory"]] - counts[u] >= 2]
        if not moves:
            break
        _, _, r, u = max(moves, key=lambda m: (m[0], m[1]))
        r["moved_from"] = r["territory"]
        place(r, u, "balanced: contested fit moved to the shorter book")

    blocked = set()
    while True:  # 3. short books stretch for unclaimed fits
        short = sorted((t for t in names if counts[t] < fair and t not in blocked), key=lambda t: counts[t])
        if not short:
            break
        t = short[0]
        options = [r for r in plan if r["status"] == "out of range" and r.get("_dist")
                   and r["_dist"][t] <= stretch]
        if not options:
            blocked.add(t)
            continue
        r = min(options, key=lambda r: r["_dist"][t])
        place(r, t, f"balanced: claimed within the {stretch}-mile stretch radius")
    return before, fair, sorted(t for t in names if counts[t] < fair)


def main():
    full = json.load(open(SKILL_DIR / "config.json"))
    cfg = full["territories"]
    method = cfg.get("method", "marquee")
    target = cfg["target_per_territory"]
    radius = cfg.get("radius_miles")

    crm = {r["account_id"]: r for r in csv.DictReader(open(DATA / "crm_export.csv"))}
    segment = {r["account_id"]: r["segment"] for r in csv.DictReader(open(DATA / "accounts.csv"))}
    graded = list(csv.DictReader(open(DATA / "graded.csv")))

    if method == "marquee":
        anchors = resolve_anchors(cfg["anchors"], crm)
        territories = [a["territory"] for a in anchors]
    elif method == "state":
        anchors = []
        territories = [state_code(s) for s in full["region_states"]]
    else:
        sys.exit(f"Unknown territory method {method!r}. Use 'marquee' or 'state'.")

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
               "status": "", "assigned_by": "", "location_check": ""}
        if c["location_match"] not in TRUSTED_LOCATION:
            row["location_check"] = f"check location ({c['location_match'] or 'none'})"

        if method == "state":
            st = state_code(c["state"])
            if not st:
                row["status"] = "no state in CRM"
            elif st in territories:
                row.update(territory=st, status="assigned", assigned_by="CRM state")
            else:
                row.update(status="out of range", anchor=f"outside region ({st})")
            plan.append(row)
            continue

        if not c["lat"] or not c["lon"]:
            row["status"] = "no location in CRM"
            plan.append(row)
            continue
        dist = sorted(((miles(float(c["lat"]), float(c["lon"]), a["lat"], a["lon"]), a) for a in anchors),
                      key=lambda x: x[0])
        d, nearest = dist[0]
        row["_dist"] = {a["territory"]: x for x, a in dist}
        if d <= radius:
            row.update(territory=nearest["territory"], anchor=nearest["anchor"], miles=round(d),
                       status="assigned", assigned_by="nearest marquee account",
                       also_in_range_of="; ".join(f"{a['territory']} ({round(x)} mi)"
                                                  for x, a in dist[1:] if x <= radius))
        else:
            row.update(anchor=f"nearest: {nearest['territory']}", miles=round(d), status="out of range")
        plan.append(row)

    balanced = None
    if method == "marquee" and cfg.get("balance"):
        stretch = cfg.get("stretch_radius_miles", radius)
        balanced = balance(plan, anchors, radius, stretch)
        for r in plan:  # contested lists now read from the final territory
            if r.get("_dist") and r["status"] == "assigned":
                r["also_in_range_of"] = "; ".join(f"{t} ({round(x)} mi)" for t, x in r["_dist"].items()
                                                  if t != r["territory"] and x <= radius)

    order = {t: i for i, t in enumerate(territories)}
    plan.sort(key=lambda r: (r["status"] != "assigned", order.get(r["territory"], 99),
                             r["miles"] if r["miles"] != "" else 9999, r["name"]))
    review.sort(key=lambda r: (r["segment"] != "Enterprise", r["reason_code"], r["name"]))

    summary = []
    for t in territories:
        mine = [r for r in plan if r["territory"] == t]
        a = next((x for x in anchors if x["territory"] == t), None)
        summary.append({
            "territory": t,
            "anchor": a["anchor"] if a else "",
            "anchor_location": f"{a['city']}, {a['state']} {a['postal_code']}".strip() if a else "",
            "before_balance": balanced[0][t] if balanced else len(mine),
            "fair_share": balanced[1] if balanced else "",
            "assigned": len(mine), "target": balanced[1] if balanced else target,
            "shortfall": max(0, (balanced[1] if balanced else target) - len(mine)),
            "secondary_overlaps": sum(1 for r in mine if r["also_in_range_of"]),
            "farthest_miles": max((r["miles"] for r in mine if r["miles"] != ""), default=""),
            "location_checks": sum(1 for r in mine if r["location_check"]),
        })

    write("territory_plan.csv", plan,
          ["account_id", "name", "city", "state", "segment", "status", "territory", "anchor",
           "miles", "assigned_by", "also_in_range_of", "location_check", "evidence"])
    write("territory_summary.csv", summary, list(summary[0].keys()))
    write("enterprise_handoff.csv", enterprise,
          ["account_id", "name", "city", "state", "segment", "website", "evidence"])
    write("needs_review.csv", review,
          ["account_id", "name", "city", "state", "segment", "reason_code", "website", "evidence"])

    # ---- report ----
    if method == "marquee":
        bal = (f" Balanced: fair share {balanced[1]}, stretch radius {cfg.get('stretch_radius_miles', radius)} miles."
               if balanced else " Not balanced.")
        goal = "" if balanced else f" Target {target} per territory."
        print(f"Method: marquee accounts. Radius {radius} miles.{goal}{bal} "
              "CRM coordinates only.\n")
    else:
        print(f"Method: one territory per state ({', '.join(territories)}). Target {target} per "
              "territory. CRM state only.\n")
    print(f"{'Territory':<12} {'Anchor':<38} {'Before':>6} {'After':>5} {'Short':>5} {'Farthest':>8} {'Overlap':>7} {'Loc check':>9}")
    for s in summary:
        far = f"{s['farthest_miles']} mi" if s["farthest_miles"] != "" else "-"
        print(f"{s['territory']:<12} {s['anchor'] or '-':<38} {s['before_balance']:>6} {s['assigned']:>5} "
              f"{s['shortfall']:>5} {far:>8} {s['secondary_overlaps']:>7} {s['location_checks']:>9}")

    assigned = [r for r in plan if r["status"] == "assigned"]
    out = [r for r in plan if r["status"] == "out of range"]
    noloc = [r for r in plan if r["status"] in ("no location in CRM", "no state in CRM")]

    print("\nFindings")
    if balanced:
        before, fair, still_short = balanced
        moved = [r for r in plan if r["assigned_by"].startswith("balanced: contested")]
        claimed = [r for r in plan if r["assigned_by"].startswith("balanced: claimed")]
        print(f"- Balancing aimed for {fair} fits per book. "
              + ("; ".join(f"{r['name']} moved from {r['moved_from']} to {r['territory']}" for r in moved) + ". " if moved else "")
              + ("Claimed with the stretch radius: " + "; ".join(f"{r['name']} by {r['territory']} ({r['miles']} mi)" for r in claimed) + "." if claimed else "No fits were claimed with the stretch radius."))
        for t in still_short:
            print(f"- {t} cannot reach {fair} with its current marquee account: no unclaimed fits within the "
                  f"stretch radius. Options: a different or second marquee account, a wider radius, or a shared rep.")
    print(f"- {len(assigned)} of {len(plan)} Mid-Market Fits fall inside a territory; "
          f"{len(out)} are out of range and {len(noloc)} have no usable CRM location.")
    goal_word = "the equal share" if balanced else "its target"
    for s in summary:
        if s["shortfall"] and not (balanced and s["territory"] in balanced[2]):
            print(f"- {s['territory']} is {s['shortfall']} short of {goal_word} of {s['target']} "
                  f"({s['assigned']} assigned).")
    for s in summary:
        if s["assigned"] > s["target"]:
            extra = " None of its fits are in range of another marquee account, so balancing cannot move them." \
                if balanced else ""
            print(f"- {s['territory']} has the deepest pool: {s['assigned']} fits, "
                  f"{s['assigned'] - s['target']} over {goal_word}.{extra}")
    if out:
        def where(r):
            place = (r["city"] + " " + r["state"]).strip() or "no city in CRM"
            return f"{r['name']} ({place}, {r['miles']} mi from {r['anchor'][9:]})" if r["miles"] != "" \
                else f"{r['name']} ({place})"
        print("- Out of range: " + ", ".join(where(r) for r in sorted(out, key=lambda r: r["miles"] or 0)) + ".")
    if noloc:
        print(f"- No usable CRM location: " + ", ".join(r["name"] for r in noloc)
              + ". Fix the CRM record (see data_hygiene.csv).")
    overlaps = [r for r in assigned if r["also_in_range_of"]]
    if overlaps:
        print(f"- {len(overlaps)} assigned account(s) are also in range of a second marquee account: "
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
