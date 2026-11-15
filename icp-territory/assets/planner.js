/* Territory planner: the browser copy of the assignment and balancing rules
 * in scripts/territories.py, so a sales leader can try changes live.
 *
 * computePlan() must give the same result as territories.py for the same
 * settings. territory_map.py checks this with Node every time it builds the
 * page. If you change a rule in one place, change it in the other.
 *
 * The rest of the file is the page UI. It runs only in a browser.
 */

function milesBetween(lat1, lon1, lat2, lon2) {
  const r = 3958.8;
  const rad = (d) => d * Math.PI / 180;
  const p1 = rad(lat1), p2 = rad(lat2);
  const dp = p2 - p1, dl = rad(lon2 - lon1);
  const a = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(a));
}

/* fits: Mid-Market Fits in graded order: {id, name, lat, lon, ...}
 * anchors: marquee accounts in config order: {territory, anchor, lat, lon}
 * p: {radius, stretch, balance, goal (0 = auto), active: [territory...],
 *     overrides: {id: territory or "Unassigned"}} */
function computePlan(fits, anchors, p) {
  const act = anchors.filter((a) => p.active.includes(a.territory));
  const names = act.map((a) => a.territory);
  const byName = Object.fromEntries(act.map((a) => [a.territory, a]));
  const rows = fits.map((f) => ({ ...f, territory: "", status: "", assigned_by: "", miles: null, dist: null }));

  for (const r of rows) {
    const hasLoc = r.lat != null && r.lon != null;
    if (hasLoc) r.dist = Object.fromEntries(act.map((a) => [a.territory, milesBetween(r.lat, r.lon, a.lat, a.lon)]));
    const ov = p.overrides[r.id];
    if (ov) { // the manager's choice wins, with or without a location
      r.assigned_by = "manager override";
      if (ov !== "Unassigned" && byName[ov]) {
        r.territory = ov; r.status = "assigned"; r.miles = hasLoc ? r.dist[ov] : null;
      } else {
        r.status = "unassigned by manager";
      }
      continue;
    }
    if (!hasLoc) { r.status = "no location in CRM"; continue; }
    if (!act.length) { r.status = "out of range"; continue; }
    // nearest; ties keep config order, like Python's stable sort
    let best = null;
    for (const a of act) if (best === null || r.dist[a.territory] < r.dist[best]) best = a.territory;
    if (r.dist[best] <= p.radius) {
      r.territory = best; r.status = "assigned"; r.assigned_by = "nearest marquee account"; r.miles = r.dist[best];
    } else {
      r.status = "out of range"; r.nearest = best; r.miles = r.dist[best];
    }
  }

  const counts = Object.fromEntries(names.map((t) => [t, 0]));
  for (const r of rows) if (r.status === "assigned") counts[r.territory] += 1;
  const before = { ...counts };
  const assignedTotal = Object.values(counts).reduce((x, y) => x + y, 0);
  const autoGoal = names.length ? Math.ceil(assignedTotal / names.length) : 0;
  const goal = p.goal > 0 ? p.goal : autoGoal;
  const moved = [], claimed = [];
  let stillShort = [];

  const place = (r, t, how) => {
    if (r.territory) counts[r.territory] -= 1;
    r.territory = t; r.status = "assigned"; r.assigned_by = how; r.miles = r.dist[t];
    counts[t] += 1;
  };

  if (p.balance && names.length) {
    for (;;) { // contested fits go to the shorter book
      let pick = null;
      for (const r of rows) {
        if (r.status !== "assigned" || !r.dist || r.assigned_by === "manager override") continue;
        for (const u of names) {
          if (u === r.territory || r.dist[u] > p.radius) continue;
          const diff = counts[r.territory] - counts[u];
          if (diff < 2) continue;
          const key = [diff, -r.dist[u]];
          if (!pick || key[0] > pick.key[0] || (key[0] === pick.key[0] && key[1] > pick.key[1])) pick = { key, r, u };
        }
      }
      if (!pick) break;
      moved.push({ name: pick.r.name, from: pick.r.territory, to: pick.u });
      place(pick.r, pick.u, "balanced: contested fit moved to the shorter book");
    }
    const stretch = Math.max(p.stretch, p.radius);
    const blocked = new Set();
    for (;;) { // short books stretch for unclaimed fits
      const short = names.filter((t) => counts[t] < goal && !blocked.has(t))
        .sort((a, b) => counts[a] - counts[b]);
      if (!short.length) break;
      const t = short[0];
      let pickR = null;
      for (const r of rows) {
        if (r.status !== "out of range" || !r.dist || r.dist[t] > stretch) continue;
        if (!pickR || r.dist[t] < pickR.dist[t]) pickR = r;
      }
      if (!pickR) { blocked.add(t); continue; }
      claimed.push({ name: pickR.name, to: t, miles: pickR.dist[t] });
      place(pickR, t, `balanced: claimed within the ${stretch}-mile stretch radius`);
    }
    stillShort = names.filter((t) => counts[t] < goal);
  }
  return { rows, names, before, after: counts, goal, autoGoal, moved, claimed, stillShort };
}

if (typeof module !== "undefined") module.exports = { computePlan, milesBetween };

/* ------------------------------------------------------------------ */
/* Page UI (browser only). Expects window.PLANNER_DATA and Leaflet.     */
/* ------------------------------------------------------------------ */
if (typeof window !== "undefined") window.addEventListener("DOMContentLoaded", () => {
  const D = window.PLANNER_DATA;
  const GREY = "#8a8f98", REVIEW = "#6b4f2a";
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const color = Object.fromEntries(D.anchors.map((a) => [a.territory, a.color]));
  const defaults = () => ({ radius: D.defaults.radius, stretch: D.defaults.stretch, balance: D.defaults.balance,
    goal: 0, active: D.anchors.map((a) => a.territory), overrides: { ...D.defaults.overrides } });
  let p = defaults();

  const map = L.map("map");
  const esri = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/";
  L.tileLayer(esri + "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 16, attribution: "Tiles &copy; Esri, HERE, Garmin, &copy; OpenStreetMap contributors" }).addTo(map);
  L.tileLayer(esri + "World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}", { maxZoom: 16 }).addTo(map);

  const staticLayer = L.layerGroup().addTo(map);
  if (D.static) { // by-state plan: show it as built, no planner controls
    const bnds = [];
    const counts = Object.fromEntries(D.anchors.map((a) => [a.territory, 0]));
    for (const f of D.fits) {
      if (f.status === "assigned") counts[f.territory] += 1;
      if (f.lat == null) continue;
      L.circleMarker([f.lat, f.lon], { radius: 7, color: "#fff", weight: 1.5, fillOpacity: 0.95,
        fillColor: f.status === "assigned" ? color[f.territory] : GREY })
        .bindTooltip(`<b>${esc(f.name)}</b><br>${esc(f.territory || f.status)}<br><i>${esc(f.evidence)}</i>`).addTo(staticLayer);
      bnds.push([f.lat, f.lon]);
    }
    for (const s of D.others) {
      L.circleMarker([s.lat, s.lon], { radius: 4, color: s.kind === "enterprise" ? "#111" : REVIEW, weight: 1.5, fill: false })
        .bindTooltip(`<b>${esc(s.name)}</b><br>${esc(s.label)}`).addTo(staticLayer);
      bnds.push([s.lat, s.lon]);
    }
    document.getElementById("summary").innerHTML = "<tr><th>Book</th><th>Fits</th></tr>" + D.anchors.map((a) =>
      `<tr><td><span class="dot" style="background:${a.color}"></span>${esc(a.territory)}</td><td>${counts[a.territory]}</td></tr>`).join("");
    document.getElementById("counts").textContent = `${D.totals.accounts} accounts · ${D.totals.fits} Fit · ${D.totals.enterprise} Enterprise handoff · ${D.totals.review} Needs Review`;
    map.fitBounds(bnds, { padding: [20, 20] });
    return;
  }
  const circleLayer = L.layerGroup().addTo(map);
  const fitLayer = L.layerGroup().addTo(map);
  const anchorLayer = L.layerGroup().addTo(map);
  const bounds = [];
  for (const s of D.others) {
    const m = s.kind === "enterprise"
      ? L.marker([s.lat, s.lon], { icon: L.divIcon({ className: "", html: '<div class="ent"></div>', iconSize: [12, 12], iconAnchor: [6, 6] }) })
      : L.circleMarker([s.lat, s.lon], { radius: 4, color: REVIEW, weight: 1.5, fill: false });
    m.bindTooltip(`<b>${esc(s.name)}</b><br>${esc(s.label)}<br><i>${esc(s.evidence)}</i>`).addTo(staticLayer);
  }
  // open on the territories: fits and marquee accounts, not far-off review dots
  for (const a of D.anchors) bounds.push([a.lat, a.lon]);
  for (const f of D.fits) if (f.lat != null) bounds.push([f.lat, f.lon]);

  const $ = (id) => document.getElementById(id);
  const fmtMi = (x) => (x == null ? "" : `${Math.round(x)} mi`);

  function popupFor(r) {
    const div = document.createElement("div");
    div.className = "pop";
    const where = r.status === "assigned" ? `${r.territory}, ${fmtMi(r.miles)}` : r.status;
    div.innerHTML = `<b>${esc(r.name)}</b><div class="muted">${esc(r.city)} ${esc(r.state)} · ${esc(where)}</div>`
      + `<div class="ev">"${esc(r.evidence)}"</div><label>Assign to</label>`;
    const sel = document.createElement("select");
    const opts = [["", "Automatic (rules decide)"], ...D.anchors.filter((a) => p.active.includes(a.territory)).map((a) => [a.territory, a.territory]), ["Unassigned", "Unassigned"]];
    for (const [v, label] of opts) {
      const o = document.createElement("option"); o.value = v; o.textContent = label;
      if ((p.overrides[r.id] || "") === v) o.selected = true;
      sel.appendChild(o);
    }
    sel.addEventListener("change", () => {
      if (sel.value) p.overrides[r.id] = sel.value; else delete p.overrides[r.id];
      map.closePopup(); render();
    });
    div.appendChild(sel);
    return div;
  }

  function render() {
    const res = computePlan(D.fits, D.anchors, p);
    circleLayer.clearLayers(); fitLayer.clearLayers(); anchorLayer.clearLayers();
    for (const a of D.anchors) {
      const on = p.active.includes(a.territory);
      if (on) L.circle([a.lat, a.lon], { radius: p.radius * 1609.34, color: a.color, weight: 1.5, fillOpacity: 0.06 }).addTo(circleLayer);
      if (on && p.balance && p.stretch > p.radius)
        L.circle([a.lat, a.lon], { radius: p.stretch * 1609.34, color: a.color, weight: 1, dashArray: "4 6", fill: false }).addTo(circleLayer);
      L.marker([a.lat, a.lon], { icon: L.divIcon({ className: "", html: `<div class="anc" style="color:${on ? a.color : GREY}">&#9733;</div>`, iconSize: [22, 22], iconAnchor: [11, 11] }), zIndexOffset: 1000 })
        .bindTooltip(`<b>${esc(a.territory)}</b>${on ? "" : " (turned off)"}<br>${esc(a.anchor)}<br>${esc(a.city)}, ${esc(a.state)} ${esc(a.postal_code)}`)
        .addTo(anchorLayer);
    }
    for (const r of res.rows) {
      if (r.lat == null) continue;
      const assigned = r.status === "assigned";
      const style = { radius: 7, weight: 1.5, color: "#fff", fillOpacity: 0.95, fillColor: assigned ? color[r.territory] : GREY };
      if (r.assigned_by === "manager override") Object.assign(style, { color: "#111", weight: 3 });
      else if (r.assigned_by.startsWith("balanced")) Object.assign(style, { color: "#111", weight: 2, dashArray: "2 2" });
      if (r.status === "unassigned by manager") Object.assign(style, { fillColor: "#fff", color: GREY, weight: 2 });
      const how = assigned ? `${r.territory}, ${fmtMi(r.miles)}. ${r.assigned_by}` : `${r.status}${r.nearest ? `, ${fmtMi(r.miles)} from ${r.nearest}` : ""}`;
      L.circleMarker([r.lat, r.lon], style)
        .bindTooltip(`<b>${esc(r.name)}</b><br>Fit · Mid-Market<br>${esc(how)}<br><i>${esc(r.evidence)}</i><br><span class="muted">Click to assign by hand</span>`)
        .bindPopup(() => popupFor(r))
        .addTo(fitLayer);
    }

    // summary table
    const tb = res.names.map((t) => {
      const gap = res.after[t] - res.goal;
      const cls = gap < 0 ? "short" : gap > 0 ? "over" : "even";
      return `<tr><td><span class="dot" style="background:${color[t]}"></span>${esc(t)}</td><td>${p.balance ? res.before[t] : ""}</td>`
        + `<td><b>${res.after[t]}</b></td><td class="${cls}">${gap > 0 ? "+" : ""}${gap}</td></tr>`;
    }).join("");
    $("summary").innerHTML = `<tr><th>Book</th><th>${p.balance ? "Before" : ""}</th><th>Fits</th><th>vs goal</th></tr>${tb}`;

    const assigned = res.rows.filter((r) => r.status === "assigned").length;
    const out = res.rows.filter((r) => r.status === "out of range");
    const manual = res.rows.filter((r) => r.assigned_by === "manager override");
    $("counts").textContent = `${D.totals.accounts} accounts · ${D.totals.fits} Fit · ${assigned} in territories · `
      + `${out.length} out of range · ${D.totals.enterprise} Enterprise handoff · ${D.totals.review} Needs Review`;

    const f = [];
    f.push(`Goal: ${res.goal} fits per book${p.goal > 0 ? " (set by you)" : " (equal share)"}.`);
    for (const m of res.moved) f.push(`${m.name} moved from ${m.from} to ${m.to} (contested fit to the shorter book).`);
    for (const c of res.claimed) f.push(`${c.to} claimed ${c.name} (${fmtMi(c.miles)}) with the stretch radius.`);
    for (const t of res.stillShort) f.push(`${t} is below the goal with no unclaimed fits in its stretch radius. Options: another marquee account, a wider radius, or a shared rep.`);
    for (const t of res.names) {
      if (res.after[t] <= res.goal) continue;
      const movable = res.rows.some((r) => r.territory === t && r.assigned_by !== "manager override" && r.dist
        && res.names.some((u) => u !== t && r.dist[u] <= p.radius));
      f.push(`${t} is ${res.after[t] - res.goal} over the goal.${movable ? "" : " None of its fits are in range of another marquee account."}`);
    }
    if (out.length) f.push(`Not covered (${out.length}): ${out.map((r) => r.name).join(", ")}.`);
    for (const a of D.anchors) if (!p.active.includes(a.territory)) f.push(`${a.territory} is turned off. Its fits go to other books or out of range.`);
    if (manual.length) f.push(`Your manual assignments (${manual.length}): ${manual.map((r) => `${r.name} to ${r.territory || "Unassigned"}`).join("; ")}.`);
    $("findings").innerHTML = f.map((x) => `<li>${esc(x)}</li>`).join("");
    window.__lastPlan = res;
  }

  // controls
  const bind = (id, key, fmt) => {
    const el = $(id), out = $(id + "_v");
    el.value = p[key]; out.textContent = fmt(p[key]);
    el.addEventListener("input", () => { p[key] = Number(el.value); out.textContent = fmt(p[key]); render(); });
  };
  bind("radius", "radius", (v) => `${v} mi`);
  bind("stretch", "stretch", (v) => `${v} mi`);
  bind("goal", "goal", (v) => (v > 0 ? `${v} fits` : "Auto: equal share"));
  const bal = $("balance");
  bal.checked = p.balance;
  bal.addEventListener("change", () => { p.balance = bal.checked; $("stretchrow").classList.toggle("off", !p.balance); render(); });
  $("anchors").innerHTML = D.anchors.map((a) => `<label class="chk"><input type="checkbox" data-t="${esc(a.territory)}" checked>`
    + `<span class="dot" style="background:${a.color}"></span>${esc(a.territory)} <span class="muted">${esc(a.city)}</span></label>`).join("");
  for (const cb of document.querySelectorAll("#anchors input")) cb.addEventListener("change", () => {
    p.active = [...document.querySelectorAll("#anchors input")].filter((x) => x.checked).map((x) => x.dataset.t);
    render();
  });
  $("reset").addEventListener("click", () => {
    p = defaults();
    for (const [id, k] of [["radius", "radius"], ["stretch", "stretch"], ["goal", "goal"]]) { $(id).value = p[k]; $(id).dispatchEvent(new Event("input")); }
    bal.checked = p.balance; $("stretchrow").classList.toggle("off", !p.balance);
    for (const cb of document.querySelectorAll("#anchors input")) cb.checked = true;
    render();
  });

  const csvCell = (v) => { const s = String(v ?? ""); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  const download = (name, rows) => {
    const text = rows.map((r) => r.map(csvCell).join(",")).join("\n") + "\n";
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
    a.download = name; document.body.appendChild(a); a.click(); a.remove();
  };
  $("dl_plan").addEventListener("click", () => {
    const res = window.__lastPlan;
    download("territory_plan_draft.csv", [["account_id", "name", "city", "state", "territory", "status", "assigned_by", "miles", "evidence"],
      ...res.rows.map((r) => [r.id, r.name, r.city, r.state, r.territory, r.status, r.assigned_by, r.miles == null ? "" : Math.round(r.miles), r.evidence])]);
  });
  $("dl_over").addEventListener("click", () => {
    download("territory_overrides.csv", [["account_id", "territory"], ...Object.entries(p.overrides)]);
  });

  render();
  map.fitBounds(bounds, { padding: [20, 20] });
});
