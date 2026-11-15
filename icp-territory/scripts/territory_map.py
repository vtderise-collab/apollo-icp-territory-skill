#!/usr/bin/env python3
"""Territory planner page: one HTML file a sales leader opens in a browser.

It shows the territory plan on a map with controls to try changes live:
radius, stretch radius, balancing on or off, a book-size goal, each marquee
account on or off, and manual assignment of any fit (click it). A summary
table and plain-sentence findings update as you go. Two downloads:
  - territory_plan_draft.csv: the plan as shown on screen
  - territory_overrides.csv: your manual assignments. Put it in data/ and
    rerun territories.py to make them part of the official plan.

The page's rules live in assets/planner.js, a copy of territories.py. After
writing the page this script runs planner.js with Node (if installed) on the
config's settings and checks it reproduces data/territory_plan.csv exactly.

No model and no network while running. The page loads Leaflet and Esri's
light gray basemap when opened (no API key; works from a local file).

Reads   data/territory_plan.csv, enterprise_handoff.csv, needs_review.csv,
        territory_overrides.csv (optional), crm_export.csv, graded.csv,
        config.json
Writes  data/territory_map.html

Run from the project folder:  python3 <skill>/scripts/territory_map.py
"""
import csv
import json
import shutil
import subprocess

from common import DATA, SKILL_DIR, need
from territories import load_overrides, resolve_anchors

COLORS = ["#1f6feb", "#d1495b", "#2a9d8f", "#e9a23b", "#8e44ad"]
PLANNER_JS = SKILL_DIR / "assets" / "planner.js"


def rows(name):
    return list(csv.DictReader(open(DATA / name)))


def node_check(data, params):
    """Run planner.js on the config's settings and compare with the plan
    territories.py wrote. Returns a one-line result."""
    node = shutil.which("node")
    if not node:
        return "Planner check skipped: Node is not installed."
    script = (f"const {{computePlan}} = require({json.dumps(str(PLANNER_JS))});"
              "let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{"
              "const d=JSON.parse(s);const r=computePlan(d.fits,d.anchors,d.params);"
              "console.log(JSON.stringify(Object.fromEntries(r.rows.map(x=>[x.id,[x.status,x.territory]]))));});")
    payload = json.dumps({"fits": data["fits"], "anchors": data["anchors"], "params": params})
    run = subprocess.run([node, "-e", script], input=payload, capture_output=True, text=True)
    if run.returncode:
        return f"PLANNER CHECK FAILED: planner.js error: {run.stderr.strip()[:300]}"
    js = json.loads(run.stdout)
    py = {r["account_id"]: [r["status"], r["territory"]] for r in rows("territory_plan.csv")}
    diff = [f"{k}: page {js.get(k)} vs plan {v}" for k, v in py.items() if js.get(k) != v]
    if diff:
        return "PLANNER CHECK FAILED: the page disagrees with territories.py: " + "; ".join(diff[:5])
    return f"Planner check passed: the page reproduces territory_plan.csv for all {len(py)} Mid-Market Fits."


def main():
    need('territory_plan.csv', 'territory_summary.csv', 'graded.csv')
    full = json.load(open(SKILL_DIR / "config.json"))
    cfg = full["territories"]
    marquee = cfg.get("method", "marquee") == "marquee"
    crm = {r["account_id"]: r for r in rows("crm_export.csv")}
    graded = rows("graded.csv")
    plan = rows("territory_plan.csv")
    ent, review = rows("enterprise_handoff.csv"), rows("needs_review.csv")
    summary_names = [r["territory"] for r in rows("territory_summary.csv")]

    def loc(aid):
        c = crm.get(aid, {})
        try:
            return float(c["lat"]), float(c["lon"])
        except (KeyError, ValueError):
            return None, None

    anchors = []
    if marquee:
        for i, a in enumerate(resolve_anchors(cfg["anchors"], crm)):
            anchors.append({"territory": a["territory"], "anchor": a["anchor"], "lat": a["lat"], "lon": a["lon"],
                            "city": a.get("city", ""), "state": a.get("state", ""),
                            "postal_code": a.get("postal_code", ""), "color": COLORS[i % len(COLORS)]})
    else:  # by state: colors per state, planner controls hidden
        anchors = [{"territory": t, "color": COLORS[i % len(COLORS)]} for i, t in enumerate(summary_names)]

    # Mid-Market Fits in graded order, the order territories.py works in
    in_plan = {r["account_id"]: r for r in plan}
    fits = []
    for g in graded:
        r = in_plan.get(g["account_id"])
        if not r:
            continue
        lat, lon = loc(g["account_id"])
        fits.append({"id": r["account_id"], "name": r["name"], "city": r["city"], "state": r["state"],
                     "lat": lat, "lon": lon, "evidence": r["evidence"],
                     "territory": r["territory"], "status": r["status"]})

    others = []
    for r in ent:
        lat, lon = loc(r["account_id"])
        if lat is not None:
            others.append({"kind": "enterprise", "name": r["name"], "lat": lat, "lon": lon,
                           "label": "Fit · Enterprise handoff", "evidence": r["evidence"]})
    for r in review:
        lat, lon = loc(r["account_id"])
        if lat is not None:
            others.append({"kind": "review", "name": r["name"], "lat": lat, "lon": lon,
                           "label": f"Needs Review · {r['segment']} · {r['reason_code']}", "evidence": r["evidence"]})

    overrides = load_overrides([a["territory"] for a in anchors] if marquee else summary_names)
    data = {
        "static": not marquee,
        "anchors": anchors,
        "fits": fits,
        "others": others,
        "defaults": {"radius": cfg.get("radius_miles") or 60,
                     "stretch": cfg.get("stretch_radius_miles") or cfg.get("radius_miles") or 60,
                     "balance": bool(cfg.get("balance")), "overrides": overrides},
        "totals": {"accounts": len(graded), "fits": sum(1 for g in graded if g["grade"] == "Fit"),
                   "enterprise": len(ent), "review": len(review)},
    }

    def js(obj):
        return json.dumps(obj).replace("</", "<\\/")

    method_note = ("Territories are built around marquee accounts, then balanced so each rep gets about the same "
                   "number of fits. Drag the sliders or click a fit to try changes."
                   if marquee else "Territories are built by state (CRM state). The planner controls work "
                   "with marquee-account territories.")
    page = PAGE.replace("__DATA__", js(data)).replace("__PLANNER__", PLANNER_JS.read_text()) \
               .replace("__NOTE__", method_note).replace("__STATIC__", "static" if not marquee else "")
    (DATA / "territory_map.html").write_text(page)
    print(f"Wrote data/territory_map.html (territory planner: {len(fits)} Mid-Market Fits, "
          f"{len(others)} other accounts, {len(anchors) if marquee else 0} marquee accounts).")

    if marquee:
        params = {"radius": data["defaults"]["radius"], "stretch": data["defaults"]["stretch"],
                  "balance": data["defaults"]["balance"], "goal": 0,
                  "active": [a["territory"] for a in anchors], "overrides": overrides}
        print(node_check(data, params))


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Territory planner</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
 :root { --ink:#1b1f24; --muted:#57606a; --line:#d8dee4; --panel:#f6f8fa; --short:#b42318; --over:#9a6700; --even:#1a7f37; }
 * { box-sizing:border-box; }
 body { margin:0; font:14px/1.45 system-ui, -apple-system, sans-serif; background:#fff; color:var(--ink); }
 header { padding:12px 16px; border-bottom:1px solid var(--line); }
 h1 { font-size:18px; margin:0 0 2px; }
 #counts { font-weight:600; }
 .note, .muted { color:var(--muted); font-size:12px; }
 .wrap { display:grid; grid-template-columns:340px 1fr; height:calc(100vh - 86px); min-height:520px; }
 aside { overflow:auto; padding:12px 16px; background:var(--panel); border-right:1px solid var(--line); }
 #map { height:100%; }
 h2 { font-size:13px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted); margin:16px 0 6px; }
 .ctl { margin:8px 0 12px; }
 .ctl label { display:flex; justify-content:space-between; font-weight:600; }
 .ctl input[type=range] { width:100%; }
 .off { opacity:.4; pointer-events:none; }
 .chk { display:flex; align-items:center; gap:6px; margin:4px 0; }
 .dot { width:11px; height:11px; border-radius:50%; display:inline-block; margin-right:4px; vertical-align:middle; }
 table { width:100%; border-collapse:collapse; background:#fff; }
 th, td { text-align:left; padding:5px 6px; border-bottom:1px solid var(--line); font-size:13px; }
 td.short { color:var(--short); font-weight:600; } td.over { color:var(--over); font-weight:600; } td.even { color:var(--even); }
 #findings { padding-left:18px; margin:6px 0; }
 #findings li { margin:4px 0; }
 .btns { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
 button { font:inherit; padding:6px 10px; border:1px solid var(--line); border-radius:6px; background:#fff; cursor:pointer; }
 button:hover { border-color:var(--muted); }
 .key { font-size:12px; color:var(--muted); line-height:1.7; }
 .key i { display:inline-block; width:11px; height:11px; border-radius:50%; vertical-align:middle; margin-right:4px; }
 .ent { width:12px; height:12px; background:#111; border:2px solid #fff; box-shadow:0 0 0 1px #111; }
 .anc { font-size:22px; line-height:22px; text-shadow:0 0 3px #fff; }
 .leaflet-tooltip { max-width:320px; white-space:normal; }
 .pop { min-width:220px; } .pop .ev { margin:6px 0; font-style:italic; } .pop select { width:100%; margin-top:4px; }
 body.static .planner { display:none; }
 @media (max-width: 800px) {
   .wrap { grid-template-columns:1fr; height:auto; }
   aside { border-right:0; border-bottom:1px solid var(--line); }
   #map { height:65vh; }
 }
</style></head><body class="__STATIC__">
<header>
 <h1>Territory planner</h1>
 <div id="counts"></div>
 <div class="note">__NOTE__ Locations are CRM coordinates, never Apollo headquarters.</div>
</header>
<div class="wrap">
 <aside>
  <div class="planner">
   <h2>Try changes</h2>
   <div class="ctl"><label>Radius <span id="radius_v"></span></label><input id="radius" type="range" min="20" max="150" step="5"></div>
   <div class="ctl"><label class="chk" style="justify-content:flex-start"><input id="balance" type="checkbox"> Balance the books</label></div>
   <div class="ctl" id="stretchrow"><label>Stretch radius <span id="stretch_v"></span></label><input id="stretch" type="range" min="20" max="250" step="5">
     <div class="muted">How far a short book may reach for unclaimed fits.</div></div>
   <div class="ctl"><label>Book-size goal <span id="goal_v"></span></label><input id="goal" type="range" min="0" max="10" step="1">
     <div class="muted">0 = equal share of the fits in range.</div></div>
   <h2>Marquee accounts</h2>
   <div id="anchors"></div>
  </div>
  <h2>Books</h2>
  <table id="summary"></table>
  <h2>What the plan says</h2>
  <ul id="findings"></ul>
  <div class="planner">
   <div class="btns"><button id="reset">Reset</button><button id="dl_plan">Download plan</button><button id="dl_over">Download overrides</button></div>
   <p class="muted">Click any fit on the map to assign it by hand. To make your changes official, put
   <code>territory_overrides.csv</code> in <code>data/</code> and rerun the skill's territory step.</p>
  </div>
  <h2>Key</h2>
  <div class="key">Colored dot: fit in that book · grey: no territory covers it<br>
  Dashed ring: moved by balancing · thick black ring: your manual assignment<br>
  &#9733; marquee account · black square: Enterprise handoff · small ring: Needs Review</div>
 </aside>
 <div id="map"></div>
</div>
<script>window.PLANNER_DATA = __DATA__;</script>
<script>
__PLANNER__
</script>
</body></html>
"""

if __name__ == "__main__":
    main()
