#!/usr/bin/env python3
"""Stage 4 visual: one HTML map of the territory plan. No model, no network
while running. The page loads Leaflet and OpenStreetMap tiles when opened
(no API key).

Reads the outputs of territories.py plus CRM coordinates:
  data/territory_plan.csv, enterprise_handoff.csv, needs_review.csv,
  data/crm_export.csv, data/graded.csv, config.json (anchors, radius)

Writes data/territory_map.html

Run from the project folder:  python3 <skill>/scripts/territory_map.py
"""
import csv
import html
import json

from common import DATA, SKILL_DIR

COLORS = ["#1f6feb", "#d1495b", "#2a9d8f", "#e9a23b", "#8e44ad"]
GREY = "#8a8f98"
REVIEW = "#6b4f2a"


def rows(name):
    return list(csv.DictReader(open(DATA / name)))


def tip(name, grade, segment, evidence, extra=""):
    parts = [f"<b>{html.escape(name)}</b>", f"{html.escape(grade)} · {html.escape(segment)}"]
    if extra:
        parts.append(html.escape(extra))
    parts.append(f"<i>{html.escape(evidence)}</i>")
    return "<br>".join(parts)


def main():
    cfg = json.load(open(SKILL_DIR / "config.json"))["territories"]
    radius_m = cfg["radius_miles"] * 1609.34
    anchors = cfg["anchors"]
    color = {a["territory"]: COLORS[i % len(COLORS)] for i, a in enumerate(anchors)}

    crm = {r["account_id"]: r for r in rows("crm_export.csv")}
    graded = rows("graded.csv")
    plan, ent, review = rows("territory_plan.csv"), rows("enterprise_handoff.csv"), rows("needs_review.csv")

    def loc(aid):
        c = crm.get(aid, {})
        try:
            return float(c["lat"]), float(c["lon"])
        except (KeyError, ValueError):
            return None

    points, unmapped = [], 0
    for r in plan:
        p = loc(r["account_id"])
        if not p:
            unmapped += 1
            continue
        if r["status"] == "assigned":
            col, extra = color[r["territory"]], f"{r['territory']}, {r['miles']} mi from anchor"
        else:
            col, extra = GREY, f"{r['status']} ({r['miles']} mi, {r['anchor']})" if r["miles"] else r["status"]
        points.append({"lat": p[0], "lon": p[1], "kind": "fit", "color": col,
                       "tip": tip(r["name"], "Fit", r["segment"], r["evidence"], extra)})
    for r in ent:
        p = loc(r["account_id"])
        if not p:
            unmapped += 1
            continue
        points.append({"lat": p[0], "lon": p[1], "kind": "enterprise", "color": "#111111",
                       "tip": tip(r["name"], "Fit", r["segment"], r["evidence"], "Enterprise handoff")})
    for r in review:
        p = loc(r["account_id"])
        if not p:
            unmapped += 1
            continue
        points.append({"lat": p[0], "lon": p[1], "kind": "review", "color": REVIEW,
                       "tip": tip(r["name"], "Needs Review", r["segment"], r["evidence"], r["reason_code"])})

    assigned = sum(1 for r in plan if r["status"] == "assigned")
    out = sum(1 for r in plan if r["status"] != "assigned")
    fits = sum(1 for g in graded if g["grade"] == "Fit")
    headline = (f"{len(graded)} accounts · {fits} Fit · {assigned} in territories · "
                f"{out} out of range · {len(ent)} Enterprise handoff · {len(review)} Needs Review")
    if unmapped:
        headline += f" · {unmapped} without CRM coordinates (not shown)"

    anchor_data = [{"lat": a["lat"], "lon": a["lon"], "color": color[a["territory"]],
                    "tip": f"<b>{html.escape(a['territory'])}</b><br>{html.escape(a['anchor'])}<br>"
                           f"{html.escape(a['city'])}, {html.escape(a['state'])} {html.escape(a['postal_code'])}"}
                   for a in anchors]
    legend = "".join(
        f'<span class="item"><span class="dot" style="background:{color[a["territory"]]}"></span>'
        f'{html.escape(a["territory"])}</span>' for a in anchors)
    legend += (f'<span class="item"><span class="dot" style="background:{GREY}"></span>Out of range Fit</span>'
               '<span class="item"><span class="sq"></span>Enterprise Fit</span>'
               f'<span class="item"><span class="ring" style="border-color:{REVIEW}"></span>Needs Review</span>'
               '<span class="item"><span class="star">&#9733;</span>Anchor customer</span>')

    def js(obj):
        return json.dumps(obj).replace("</", "<\\/")

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rackwell territory map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
 body {{ margin:0; font:14px/1.4 system-ui, sans-serif; background:#fff; color:#1b1f24; }}
 header {{ padding:12px 16px; }}
 h1 {{ font-size:18px; margin:0 0 4px; }}
 .counts {{ font-weight:600; margin-bottom:6px; }}
 .note {{ color:#57606a; font-size:12px; }}
 .legend {{ display:flex; flex-wrap:wrap; gap:6px 16px; margin-top:8px; }}
 .item {{ display:inline-flex; align-items:center; gap:6px; }}
 .dot {{ width:12px; height:12px; border-radius:50%; display:inline-block; }}
 .sq {{ width:11px; height:11px; background:#111; display:inline-block; }}
 .ring {{ width:8px; height:8px; border:2px solid; border-radius:50%; display:inline-block; }}
 .star {{ font-size:16px; }}
 #map {{ height: calc(100vh - 130px); min-height:420px; }}
 .ent {{ width:12px; height:12px; background:#111; border:2px solid #fff; box-shadow:0 0 0 1px #111; }}
 .anc {{ font-size:22px; line-height:22px; text-shadow:0 0 3px #fff; }}
 .leaflet-tooltip {{ max-width:320px; white-space:normal; }}
</style></head><body>
<header>
 <h1>Rackwell territory plan</h1>
 <div class="counts">{html.escape(headline)}</div>
 <div class="note">Anchors are made up, at real ZIP codes. Circles are the {cfg['radius_miles']}-mile radius.
 Locations are CRM coordinates, never Apollo headquarters. Hover a dot for the evidence.</div>
 <div class="legend">{legend}</div>
</header>
<div id="map"></div>
<script>
const anchors = {js(anchor_data)};
const points = {js(points)};
const radius = {radius_m};
const map = L.map('map');
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 18, attribution: '&copy; OpenStreetMap contributors'
}}).addTo(map);
const bounds = [];
for (const a of anchors) {{
  L.circle([a.lat, a.lon], {{radius, color:a.color, weight:1.5, fillOpacity:0.06}}).addTo(map);
  L.marker([a.lat, a.lon], {{icon: L.divIcon({{className:'', html:'<div class="anc" style="color:'+a.color+'">&#9733;</div>', iconSize:[22,22], iconAnchor:[11,11]}})}})
    .bindTooltip(a.tip).addTo(map);
  bounds.push([a.lat, a.lon]);
}}
const order = {{review:0, fit:1, enterprise:2}};
points.sort((p, q) => order[p.kind] - order[q.kind]);
for (const p of points) {{
  let m;
  if (p.kind === 'enterprise') {{
    m = L.marker([p.lat, p.lon], {{icon: L.divIcon({{className:'', html:'<div class="ent"></div>', iconSize:[12,12], iconAnchor:[6,6]}})}});
  }} else if (p.kind === 'review') {{
    m = L.circleMarker([p.lat, p.lon], {{radius:4, color:p.color, weight:1.5, fill:false}});
  }} else {{
    m = L.circleMarker([p.lat, p.lon], {{radius:7, color:'#fff', weight:1.5, fillColor:p.color, fillOpacity:0.95}});
  }}
  m.bindTooltip(p.tip).addTo(map);
  bounds.push([p.lat, p.lon]);
}}
map.fitBounds(bounds, {{padding:[20,20]}});
</script>
</body></html>
"""
    (DATA / "territory_map.html").write_text(page)
    print(f"Wrote data/territory_map.html ({len(points)} accounts, {len(anchors)} anchors). {headline}")


if __name__ == "__main__":
    main()
