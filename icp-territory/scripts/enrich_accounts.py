#!/usr/bin/env python3
"""Step 1: enrich the CRM's prospect accounts with Apollo.

Reads the account list (today a CSV export; tomorrow a Salesforce query,
by changing load_crm_accounts only), calls Apollo's organization enrichment
once per website domain, and writes data/accounts.csv: the CRM fields plus
Apollo's industry tag, keywords, size and headquarters location.

Apollo's location is the company's headquarters, not this account's site.
Territories never use it; it is kept only to report data-hygiene gaps.

Every Apollo answer is cached in data/cache/apollo/<domain>.json, so a crash
or a re-run never pays for the same lookup twice. New lookups run in batches
of 25, and the run stops at the first credit, plan or rate-limit error.

Run from the project folder:  python3 <skill>/scripts/enrich_accounts.py
"""
import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from common import DATA, load_config, load_env, names_agree, need

API = "https://api.apollo.io/api/v1/organizations/enrich"
CACHE = DATA / "cache" / "apollo"
BATCH = 25
MIN_SECONDS_BETWEEN_CALLS = 1.5   # stays under the free plan's 50 a minute
STOP_CODES = {401, 402, 403, 429}  # auth, credits, plan, rate limit


class StopRun(Exception):
    pass


def load_crm_accounts():
    """The one place that knows where accounts come from."""
    with open(DATA / "crm_export.csv", newline="") as f:
        return list(csv.DictReader(f))


def cached(domain):
    p = CACHE / f"{domain}.json"
    return json.loads(p.read_text()) if p.exists() else None


def fetch(key, domain):
    req = urllib.request.Request(
        API + "?" + urllib.parse.urlencode({"domain": domain}),
        headers={"X-Api-Key": key, "Accept": "application/json",
                 "Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        if e.code in STOP_CODES or "credit" in body.lower():
            raise StopRun(f"HTTP {e.code} on {domain}: {body}")
        return None   # other errors: leave uncached, report as error
    except Exception:
        return None
    (CACHE / f"{domain}.json").write_text(json.dumps(payload))
    time.sleep(MIN_SECONDS_BETWEEN_CALLS)
    return payload


def skip_apollo(domain, cfg):
    """Shared hosts and social pages: the domain belongs to the platform,
    so Apollo would describe Wix or Facebook, not this business."""
    return any(domain == h or domain.endswith("." + h) for h in cfg["apollo_skip_hosts"])


def segment(status, org, cfg):
    """Deterministic segment rule from config.json. Only a trusted Apollo
    match can make an account Enterprise."""
    s = cfg["segment"]
    if status != "matched":
        return "Mid-Market"
    emp = org.get("estimated_num_employees") or 0
    out_of_region = (org.get("state") not in cfg["region_states"]
                     or (org.get("country") or "United States") != "United States")
    if (out_of_region and emp >= s["out_of_region_min_employees"]) \
            or emp >= s["any_region_min_employees"]:
        return "Enterprise"
    return "Mid-Market"


def to_row(account, payload, cfg):
    apollo_name = ""
    if skip_apollo(account["domain"], cfg):
        status, org = "skipped_shared_host", {}
    elif payload is None:
        status, org = "error", {}
    else:
        org = payload.get("organization") or {}
        status = "matched" if org.get("name") else "no_match"
        apollo_name = org.get("name", "")
        if status == "matched" and not names_agree(account["name"], apollo_name):
            # Apollo answered for a different company. Keep its name for
            # the hygiene report, ignore everything else it said.
            status, org = "apollo_mismatch", {}
    return {
        **account,
        "apollo_status": status,
        "segment": segment(status, org, cfg),
        "apollo_name": apollo_name,
        "apollo_industry": org.get("industry", ""),
        "apollo_keywords": "; ".join((org.get("keywords") or [])[:10]),
        "employees": org.get("estimated_num_employees", ""),
        "annual_revenue": org.get("annual_revenue", ""),
        "apollo_hq_city": org.get("city", ""),
        "apollo_hq_state": org.get("state", ""),
        "apollo_hq_postal_code": (org.get("postal_code") or "")[:5],
        "apollo_description": (org.get("short_description") or "")[:300],
    }


def write(rows):
    with open(DATA / "accounts.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    need('crm_export.csv')
    key = load_env("APOLLO_API_KEY")
    if not key:
        sys.exit("APOLLO_API_KEY is empty in .env")
    CACHE.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    accounts = load_crm_accounts()
    todo = [a["domain"] for a in accounts
            if cached(a["domain"]) is None and not skip_apollo(a["domain"], cfg)]
    print(f"{len(accounts)} accounts, {len(accounts) - len(todo)} already cached, "
          f"{len(todo)} to look up", flush=True)

    stopped = None
    for start in range(0, len(todo), BATCH):
        batch = todo[start:start + BATCH]
        try:
            for d in batch:
                fetch(key, d)
        except StopRun as e:
            stopped = str(e)
            break
        print(f"  batch {start // BATCH + 1}: {len(batch)} looked up", flush=True)

    rows = [to_row(a, cached(a["domain"]), cfg) for a in accounts]
    write(rows)
    counts = {}
    for r in rows:
        counts[r["apollo_status"]] = counts.get(r["apollo_status"], 0) + 1
    print("Result counts:", counts)
    if stopped:
        sys.exit(f"STOPPED at first credit/plan error. Cached lookups kept.\n{stopped}")


if __name__ == "__main__":
    main()
