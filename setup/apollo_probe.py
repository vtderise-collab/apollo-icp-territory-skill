#!/usr/bin/env python3
"""Free-tier check: what does Apollo's API return for this account?

Makes one small call to each of three endpoints and reports, in plain terms,
whether the call was allowed and which fields came back filled in.

  1. Company search      POST /mixed_companies/search
  2. Company enrichment  GET  /organizations/enrich
  3. People search       POST /mixed_people/api_search

Uses only the Python standard library. Reads APOLLO_API_KEY from .env.
The key is sent in a header and is never printed or written to disk.
Raw responses are saved under notes/apollo-probe/ (git-ignored).

Run from the repo root:  python3 setup/apollo_probe.py
"""
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = "https://api.apollo.io/api/v1"
OUT = ROOT / "notes" / "apollo-probe"

# Fields the pipeline needs per account (design spec, stage 0).
ACCOUNT_FIELDS = [
    "name", "primary_domain", "website_url", "industry", "keywords",
    "estimated_num_employees", "annual_revenue", "city", "state",
    "postal_code", "country", "short_description",
]
PERSON_FIELDS = ["first_name", "last_name", "last_name_obfuscated", "title",
                 "email", "linkedin_url", "organization"]


def load_key():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.strip().startswith("APOLLO_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def call(key, method, path, body=None, query=None):
    url = BASE + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "X-Api-Key": key,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status, raw, headers = resp.status, resp.read(), resp.headers
    except urllib.error.HTTPError as e:
        status, raw, headers = e.code, e.read(), e.headers
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = {"_unparsed": raw[:500].decode("utf-8", "replace")}
    limits = {k: v for k, v in headers.items() if "rate" in k.lower()}
    return status, payload, limits


def filled(record, fields):
    """Split the wanted fields into those with a value and those without."""
    have = [f for f in fields if record.get(f) not in (None, "", [], {})]
    return have, [f for f in fields if f not in have]


def report(label, status, payload, limits, list_keys, fields, show):
    print(f"\n=== {label} ===")
    print(f"HTTP status: {status}")
    if status != 200:
        print("Blocked or failed. Apollo said:",
              json.dumps(payload)[:400])
        return []
    records = []
    for k in list_keys:
        v = payload.get(k)
        if isinstance(v, list):
            records += v
        elif isinstance(v, dict):
            records.append(v)
    total = (payload.get("pagination") or {}).get("total_entries",
                                                  payload.get("total_entries"))
    print(f"Records in this response: {len(records)}"
          + (f"   Total matches Apollo reports: {total}" if total is not None else ""))
    if records:
        have, missing = filled(records[0], fields)
        print("Filled on first record :", ", ".join(have) or "none")
        print("Empty on first record  :", ", ".join(missing) or "none")
        for r in records[:5]:
            print("  -", " | ".join(str(r.get(f, ""))[:40] for f in show))
    if limits:
        print("Rate-limit headers:", limits)
    return records


def main():
    key = load_key()
    if not key:
        sys.exit("APOLLO_API_KEY is empty. Paste your key into .env after the "
                 "equals sign, save, and run this again.")
    OUT.mkdir(parents=True, exist_ok=True)

    # 1. Company search: keyword plus state, the way stage 0 would source accounts.
    status, payload, limits = call(key, "POST", "/mixed_companies/search", body={
        "q_organization_keyword_tags": ["gym", "fitness center", "health club"],
        "organization_locations": ["Illinois, US", "Wisconsin, US"],
        "per_page": 5, "page": 1,
    })
    (OUT / "1_company_search.json").write_text(json.dumps(payload, indent=2))
    orgs = report("1. Company search", status, payload, limits,
                  ["organizations", "accounts"], ACCOUNT_FIELDS,
                  ["name", "primary_domain", "industry", "city", "state"])

    # 2. Company enrichment: one domain in, full company record out.
    domain = next((o.get("primary_domain") for o in orgs if o.get("primary_domain")),
                  "planetfitness.com")
    status, payload, limits = call(key, "GET", "/organizations/enrich",
                                   query={"domain": domain})
    (OUT / "2_company_enrichment.json").write_text(json.dumps(payload, indent=2))
    print(f"\n(enriching domain: {domain})")
    report("2. Company enrichment", status, payload, limits,
           ["organization"], ACCOUNT_FIELDS,
           ["name", "industry", "estimated_num_employees", "city", "state",
            "postal_code"])

    # 3. People search: who works there, by title.
    status, payload, limits = call(key, "POST", "/mixed_people/api_search", body={
        "q_organization_domains_list": [domain],
        "person_titles": ["owner", "general manager", "operations"],
        "per_page": 3, "page": 1,
    })
    (OUT / "3_people_search.json").write_text(json.dumps(payload, indent=2))
    report("3. People search", status, payload, limits,
           ["people", "contacts"], PERSON_FIELDS, ["first_name", "title"])

    print(f"\nRaw responses saved in {OUT.relative_to(ROOT)}/ (git-ignored).")


if __name__ == "__main__":
    main()
