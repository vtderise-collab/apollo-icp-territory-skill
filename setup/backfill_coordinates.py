#!/usr/bin/env python3
"""Demo-data setup: add latitude and longitude to the existing CRM export.

Keeps the current account list exactly as it is. Runs one OpenStreetMap
query for every listed website domain in the region, then matches each
account back to its own location: same domain, preferring the same ZIP,
then the same city, then the same name. Chains (one domain, many locations)
need that tie-break.

Gives up after MAX_SECONDS. Any account left without coordinates is later
reported as "no location in CRM" and left unassigned.

Run from the repo root:  python3 setup/backfill_coordinates.py
"""
import csv
import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "setup"))
sys.path.insert(0, str(ROOT / "icp-territory" / "scripts"))
from common import registered_domain  # noqa: E402
import seed_crm_from_osm as seed      # noqa: E402

MAX_SECONDS = 600
CRM = ROOT / "data" / "crm_export.csv"


def main():
    started = time.time()
    with open(CRM, newline="") as f:
        rows = list(csv.DictReader(f))
    domains = sorted({r["domain"] for r in rows})
    pattern = "|".join(re.escape(d).replace("\\", "\\\\") for d in domains)
    cfg = json.loads((ROOT / "setup" / "seed_config.json").read_text())
    areas = "".join(f'area["ISO3166-2"="{s}"];' for s in cfg["region_states"])
    query = (f"[out:json][timeout:300];({areas})->.r;("
             f'nwr(area.r)["website"~"{pattern}",i];'
             f'nwr(area.r)["contact:website"~"{pattern}",i];'
             ");out center tags;")

    elements = None
    while time.time() - started < MAX_SECONDS:
        try:
            elements = seed.overpass(query)
            break
        except SystemExit as e:   # overpass() exits when every server failed
            print("  all servers failed this round:", e, flush=True)
    if elements is None:
        sys.exit("Gave up after 10 minutes. Accounts keep blank coordinates.")

    by_domain = {}
    for el in elements:
        t = el.get("tags", {})
        site = t.get("website") or t.get("contact:website")
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if site and lat:
            by_domain.setdefault(registered_domain(site), []).append({
                "lat": lat, "lon": lon, "name": t.get("name", ""),
                "zip": t.get("addr:postcode", "")[:5],
                "city": t.get("addr:city", "").lower()})

    filled = 0
    for r in rows:
        cands = by_domain.get(r["domain"], [])
        # How the location was matched. "name" with several candidates means
        # a chain row with no address in the CRM: one of its locations,
        # not necessarily this account's. Shown as low confidence.
        tests = [
            ("zip", lambda c: r["postal_code"] and c["zip"] == r["postal_code"]),
            ("city", lambda c: r["city"] and c["city"] == r["city"].lower()),
            ("only_candidate", lambda c: len(cands) == 1),
            ("name_low_confidence" if len(cands) > 1 else "name",
             lambda c: c["name"] == r["name"]),
        ]
        best, method = None, "none"
        for label, test in tests:
            best = next((c for c in cands if test(c)), None)
            if best:
                method = label
                break
        r["lat"] = best["lat"] if best else ""
        r["lon"] = best["lon"] if best else ""
        r["location_match"] = method
        filled += bool(best)

    fields = list(rows[0].keys())
    with open(CRM, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"Coordinates filled for {filled} of {len(rows)} accounts "
          f"in {int(time.time() - started)}s. {len(rows) - filled} have no location.")


if __name__ == "__main__":
    main()
