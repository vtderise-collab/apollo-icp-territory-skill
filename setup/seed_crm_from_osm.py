#!/usr/bin/env python3
"""Demo-data setup: build a stand-in "CRM export" of prospect accounts.

Rackwell is fictional, so it has no real CRM. This script plays that role:
it pulls real businesses from OpenStreetMap (a free public map database)
across several categories in the region, keeps one row per website domain,
and writes data/crm_export.csv with only what a CRM export would hold:
an account ID, a name, a website and an address. Fit is unknown.

The OSM category is written to a separate file (data/seed_source.csv) so it
never reaches the grader. It is used only to pick a balanced validation set.

Run once from the repo root:  python3 setup/seed_crm_from_osm.py
"""
import csv
import json
import pathlib
import random
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "icp-territory" / "scripts"))
from common import registered_domain, normalize_url  # noqa: E402

SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
USER_AGENT = "icp-territory-skill/0.1"


def build_query(states, osm_filters):
    areas = "".join(f'area["ISO3166-2"="{s}"];' for s in states)
    parts = []
    for f in osm_filters:
        tag = "][".join(
            '"{}"="{}"'.format(*kv.split("=", 1)) for kv in f.split("][")
        )
        for web in ("website", "contact:website"):
            parts.append(f'nwr(area.r)[{tag}]["{web}"];')
    return (f"[out:json][timeout:180];({areas})->.r;("
            + "".join(parts) + ");out center tags;")


def overpass(query):
    # Fetch through curl, not Python's urllib: macOS's built-in Python ships
    # an old TLS library that the main Overpass server refuses.
    last = None
    for attempt in range(2):
        for url in SERVERS:
            r = subprocess.run(
                ["curl", "-s", "-m", "240", "-A", USER_AGENT,
                 "--data-urlencode", "data=" + query, "-w", "\n%{http_code}", url],
                capture_output=True, text=True)
            body, _, status = r.stdout.rpartition("\n")
            if r.returncode == 0 and status == "200":
                try:
                    return json.loads(body)["elements"]
                except ValueError:
                    pass
            last = f"{url}: curl exit {r.returncode}, HTTP {status}"
            print("  server failed, trying next:", last, flush=True)
        time.sleep(15)
    sys.exit(f"All OpenStreetMap servers failed. Last error: {last}")


def main():
    cfg = json.loads((ROOT / "setup" / "seed_config.json").read_text())
    seed = cfg["seed"]
    rng = random.Random(seed["random_seed"])
    seen_domains = set()
    rows, source = [], []

    for category, spec in seed["categories"].items():
        print(f"Pulling {category} ...")
        elements = overpass(build_query(cfg["region_states"], spec["osm"]))
        candidates = []
        for el in elements:
            t = el.get("tags", {})
            site = t.get("website") or t.get("contact:website")
            name = t.get("name")
            if not site or not name:
                continue
            candidates.append({
                "name": name,
                "website": normalize_url(site),
                "domain": registered_domain(site),
                "city": t.get("addr:city", ""),
                "state": t.get("addr:state", ""),
                "postal_code": t.get("addr:postcode", "")[:5],
                "lat": el.get("lat") or el.get("center", {}).get("lat", ""),
                "lon": el.get("lon") or el.get("center", {}).get("lon", ""),
            })
        # Sort before shuffling so the same seed gives the same list
        # even if the server returns results in a different order.
        candidates.sort(key=lambda c: (c["domain"], c["name"]))
        rng.shuffle(candidates)
        taken = 0
        for c in candidates:
            if taken >= spec["take"]:
                break
            if not c["domain"] or c["domain"] in seen_domains:
                continue  # one account per company website
            seen_domains.add(c["domain"])
            c["account_id"] = f"ACC-{len(rows) + 1:04d}"
            rows.append(c)
            source.append({"account_id": c["account_id"], "osm_category": category})
            taken += 1
        print(f"  {len(elements)} found, {len(candidates)} with name and website, kept {taken}")

    # Shuffle so the CRM file is not grouped by category.
    rng.shuffle(rows)
    out = ROOT / "data"
    out.mkdir(exist_ok=True)
    fields = ["account_id", "name", "website", "domain", "city", "state",
              "postal_code", "lat", "lon"]
    with open(out / "crm_export.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["account_id"]))
    with open(out / "seed_source.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["account_id", "osm_category"])
        w.writeheader()
        w.writerows(source)
    print(f"\nWrote {len(rows)} accounts to data/crm_export.csv")


if __name__ == "__main__":
    main()
