#!/usr/bin/env python3
"""Data-hygiene audit: one row per problem found in the account records,
with a proposed fix. No model, no network. Proposes fixes; never applies
them to the CRM.

Checks
  CRM       missing city or state, low-confidence location
  Apollo    no record, name mismatch (Apollo data ignored), shared host or
            social page instead of a company domain, headquarters in a
            different state than the CRM site, industry tag contradicted by
            the website (from the grader's tag_disagrees flag)
  Website   could not be read, by failure type

The output holds no raw Apollo values (no headcount, headquarters or tag),
only what is wrong and what to do, so it can be shared.

Inputs   data/crm_export.csv, data/accounts.csv, data/evidence.jsonl,
         data/graded.csv (optional, for tag conflicts and grades)
Output   data/data_hygiene.csv

Run from the project folder:  python3 <skill>/scripts/hygiene_report.py
"""
import collections
import csv
import json

from common import DATA
from territories import state_code

TRUSTED_LOCATION = {"zip", "city"}

SCRAPE_FIX = {
    "http_403": "Site blocks automated reads. Retry later or review by hand. Do not bypass the block.",
    "dns_failure": "Domain does not resolve. Confirm the website in the CRM; the business may have closed.",
    "connect_failed": "Site did not answer. Retry later; if it fails again, confirm the website.",
    "thin_content": "Site has almost no readable text (often built in JavaScript). Review by hand.",
    "parked": "Domain is parked or for sale. Confirm the business is still active.",
}


def main():
    crm = list(csv.DictReader(open(DATA / "crm_export.csv")))
    acc = {r["account_id"]: r for r in csv.DictReader(open(DATA / "accounts.csv"))}
    ev = {json.loads(l)["account_id"]: json.loads(l) for l in open(DATA / "evidence.jsonl")}
    graded = {}
    if (DATA / "graded.csv").exists():
        graded = {r["account_id"]: r for r in csv.DictReader(open(DATA / "graded.csv"))}

    rows = []

    def add(c, source, issue_type, issue, fix):
        rows.append({"account_id": c["account_id"], "name": c["name"],
                     "grade": graded.get(c["account_id"], {}).get("grade", ""),
                     "source": source, "issue_type": issue_type, "issue": issue, "proposed_fix": fix})

    for c in crm:
        aid = c["account_id"]
        a = acc.get(aid, {})
        e = ev.get(aid, {})

        # CRM record
        if not c["city"] or not c["state"]:
            add(c, "CRM", "missing_location_fields", "CRM record has no city or state.",
                "Fill city and state from the site address. Needed for state-based territories.")
        if c["location_match"] not in TRUSTED_LOCATION:
            add(c, "CRM", "low_confidence_location",
                f"Site coordinates matched by {c['location_match'] or 'nothing'}, not ZIP or city.",
                "Confirm the street address before relying on territory distance.")

        # Apollo
        st = a.get("apollo_status", "")
        if st == "no_match":
            add(c, "Apollo", "no_apollo_record", "Apollo has no record for this domain.",
                "Segment defaults to Mid-Market. Confirm size by hand if the account matters.")
        elif st == "apollo_mismatch":
            add(c, "Apollo", "name_mismatch", "Apollo returned a company whose name does not match the CRM.",
                "Apollo data ignored. Confirm the website domain; if it is right, accept the match by hand.")
        elif st == "skipped_shared_host":
            add(c, "CRM", "shared_host_website",
                "Website is a site-builder or social page, not the company's own domain.",
                "Add the company's own domain to the CRM so it can be enriched.")
        elif st == "matched":
            hq, site = state_code(a.get("apollo_hq_state")), state_code(c["state"])
            if hq and site and hq != site:
                add(c, "Apollo", "hq_vs_site_state",
                    "Apollo headquarters is in a different state than the CRM site.",
                    "Keep the CRM site for territories. Treat it as a branch or chain location.")
        if graded.get(aid, {}).get("tag_disagrees", "").lower() == "true":
            add(c, "Apollo", "industry_tag_conflict", "The website contradicts Apollo's industry tag.",
                "Do not route or segment by this tag. The website-based grade stands.")

        # Website
        ss = e.get("scrape_status", "")
        if ss and ss != "ok":
            fix = SCRAPE_FIX.get(ss) or (
                "Page not found. Confirm the website URL in the CRM." if ss == "http_404" else
                "Site returned an error. Retry later; if it persists, confirm the website.")
            add(c, "Website", "website_unreadable", f"Website could not be read ({ss}).", fix)

    rows.sort(key=lambda r: (r["source"], r["issue_type"], r["name"]))
    fields = ["account_id", "name", "grade", "source", "issue_type", "issue", "proposed_fix"]
    with open(DATA / "data_hygiene.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    by_type = collections.Counter(r["issue_type"] for r in rows)
    accounts = len({r["account_id"] for r in rows})
    print(f"Data hygiene: {len(rows)} issues on {accounts} of {len(crm)} accounts.")
    for t, n in by_type.most_common():
        print(f"  {t:<26} {n}")
    print("Wrote data/data_hygiene.csv (proposed fixes; nothing applied to the CRM).")


if __name__ == "__main__":
    main()
