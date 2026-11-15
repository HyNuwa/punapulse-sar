/* SI disclosure: drafted with assistance from Claude (Anthropic); reviewed by the PunaPulse SAR team. */
/* PunaPulse SAR - static viewer. Reads data/manifest.json produced by the Python pipeline. */
(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const fmtHa = (v) => (v == null ? "–" : `${Math.round(v).toLocaleString("en-US")} ha`);
  const fmtDb = (v) => (v == null ? "–" : `${v.toFixed(1)} dB`);
  const DEFAULT_BBOX = [-66.85, -23.75, -66.55, -23.2];

  const state = { m: null, layer: "rgb", before: null, after: null, opacity: 0.9, swipe: true, pct: 0.5,
                  overlays: { before: null, after: null, change: null, ifg: null }, zones: null, precip: null };

  // ------------------------------------------------------------------ map + basemaps
  const map = L.map("map", { zoomControl: true, preferCanvas: false });
  map.createPane("sarBefore").style.zIndex = 410;
  map.createPane("sarAfter").style.zIndex = 420;
  map.createPane("sarChange").style.zIndex = 430;
  map.createPane("sarIfg").style.zIndex = 440;
  map.createPane("labels").style.zIndex = 460;
  map.getPane("labels").style.pointerEvents = "none";

  const gibsDate = new Date(Date.now() - 3 * 864e5).toISOString().slice(0, 10);
  const base = {
    "Optical · Esri World Imagery": L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 18, attribution: "Imagery © Esri, Maxar, Earthstar Geographics" }),
    [`Optical · NASA GIBS MODIS (${gibsDate})`]: L.tileLayer(
      `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_CorrectedReflectance_TrueColor/default/${gibsDate}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`,
      { maxNativeZoom: 9, maxZoom: 18, attribution: "NASA GIBS / MODIS Terra" }),
    "Map · OpenStreetMap": L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      { maxZoom: 18, attribution: "© OpenStreetMap contributors" }),
  };
  base["Optical · Esri World Imagery"].addTo(map);
  const labels = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    { pane: "labels", maxZoom: 18, attribution: "Labels © Esri" });
  const places = L.layerGroup().addTo(map);
  const zoneLayer = L.geoJSON(null, { style: { color: "#e2b35b", weight: 2, fill: false, dashArray: "4 3" },
    onEachFeature: (f, l) => l.bindTooltip(f.properties?.name || "zone") }).addTo(map);
  const drawn = new L.FeatureGroup().addTo(map);
  L.control.layers(base, { "Places (OpenStreetMap)": places, "Labels": labels, "Zones": zoneLayer }, { collapsed: true }).addTo(map);
  L.control.scale({ imperial: false }).addTo(map);

  // ------------------------------------------------------------------ load data
  async function getJSON(url) {
    const r = await fetch(`${url}?v=${Date.now()}`);
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    return r.json();
  }

  async function init() {
    let m;
    try { m = await getJSON("data/manifest.json"); } catch (e) { m = { scenes: [] }; }
    m.scenes = m.scenes || []; m.changes = m.changes || []; m.interferograms = m.interferograms || [];
    state.m = m;
    const bb = m.aoi?.bbox || DEFAULT_BBOX;
    const bounds = m.bounds ? L.latLngBounds(m.bounds) : L.latLngBounds([[bb[1], bb[0]], [bb[3], bb[2]]]);
    state.bounds = bounds;
    L.rectangle(bounds, { color: "#f3efe6", weight: 1.5, fill: false, interactive: false }).addTo(map);
    map.fitBounds(bounds, { padding: [20, 20] });

    try { state.zones = await getJSON("data/zones.geojson"); zoneLayer.addData(state.zones); } catch (e) { state.zones = null; }
    if (m.precip) { try { state.precip = await getJSON(m.precip); } catch (e) { state.precip = null; } }

    renderStatus();
    fillControls();
    loadPlaces(bb);
    update();
  }

  // ------------------------------------------------------------------ status card
  function renderStatus() {
    const m = state.m, el = $("status");
    if (!m.scenes.length) {
      el.classList.add("empty");
      el.innerHTML = `<h2>No NISAR scenes processed yet</h2>
        <p class="hint">This viewer only shows real NISAR data. Run the pipeline (see README):</p>
        <pre class="hint"><code>export EARTHDATA_TOKEN=...\npython -m pipeline.run_all --max-scenes 4</code></pre>
        <p class="hint">Context layers (optical imagery, places, AOI) are already available.</p>`;
      showBanner("Waiting for NISAR data: run the pipeline to add radar layers. Context layers shown.");
      ["layerSel", "beforeSel", "afterSel", "swipeChk", "opacity", "changeSel"].forEach((id) => ($(id).disabled = true));
      return;
    }
    const mats = [...new Set(m.scenes.map((s) => s.maturity))];
    const s0 = m.scenes[0], s1 = m.scenes[m.scenes.length - 1];
    el.innerHTML = `<h2>NISAR L-band · ${m.scenes.length} date${m.scenes.length > 1 ? "s" : ""} <span class="tag observed">Observed</span></h2>
      <div>${s0.date} → ${s1.date}</div>
      <div>${mats.map((x) => `<span class="badge ${x}">${x}</span>`).join("")}
        ${s0.track != null ? `<span class="badge">track ${s0.track}</span>` : ""}
        ${s0.direction ? `<span class="badge">${String(s0.direction).toLowerCase()}</span>` : ""}
        <span class="badge">${(s0.polarizations || []).join(" · ")}</span></div>
      ${(m.warnings || []).map((w) => `<p class="warn">⚠ ${w}</p>`).join("")}
      ${mats.some((x) => x !== "VALIDATED") ? `<p class="warn">Not fully validated data: treat values as preliminary.</p>` : ""}`;
  }

  function showBanner(t) { const b = $("banner"); b.textContent = t; b.hidden = !t; }

  // ------------------------------------------------------------------ controls
  function fillControls() {
    const m = state.m;
    const opts = m.scenes.map((s) => `<option value="${s.id}">${s.date}${s.maturity && s.maturity !== "VALIDATED" ? " · " + s.maturity : ""}</option>`).join("");
    $("beforeSel").innerHTML = opts; $("afterSel").innerHTML = opts;
    if (m.scenes.length) {
      state.before = m.scenes[0].id; state.after = m.scenes[m.scenes.length - 1].id;
      $("beforeSel").value = state.before; $("afterSel").value = state.after;
      if (!m.scenes[0].layers.rgb) { state.layer = "hh"; $("layerSel").value = "hh"; $("layerSel").querySelector('[value="rgb"]').disabled = true; }
    }
    if (m.scenes.length < 2) { state.swipe = false; $("swipeChk").checked = false; $("swipeChk").disabled = true; }

    $("changeSel").innerHTML = `<option value="">Off</option>` +
      m.changes.map((c, i) => `<option value="${i}">${c.from} → ${c.to}</option>`).join("");

    if (m.interferograms.length) {
      $("ifgCard").hidden = false;
      $("ifgSel").innerHTML = `<option value="">Off</option>` + m.interferograms.map((g, i) =>
        `<option value="p${i}">Phase ${g.ref} → ${g.sec}</option>` + (g.coherence ? `<option value="c${i}">Coherence ${g.ref} → ${g.sec}</option>` : "")).join("");
    }

    const zoneNames = ["Whole AOI", ...((state.zones?.features || []).map((f, i) => f.properties?.name || `zone ${i + 1}`))];
    const statZones = Object.keys(m.scenes[0]?.stats?.zones || {});
    const names = [...new Set([...statZones, ...zoneNames])];
    $("zoneSel").innerHTML = names.map((n) => `<option>${n}</option>`).join("");

    $("layerSel").onchange = (e) => { state.layer = e.target.value; update(); };
    $("beforeSel").onchange = (e) => { state.before = e.target.value; update(); };
    $("afterSel").onchange = (e) => { state.after = e.target.value; update(); };
    $("swipeChk").onchange = (e) => { state.swipe = e.target.checked; update(); };
    $("opacity").oninput = (e) => { state.opacity = +e.target.value; Object.values(state.overlays).forEach((o) => o && o.setOpacity(state.opacity)); };
    $("changeSel").onchange = () => updateChange();
    $("ifgSel").onchange = () => updateIfg();
    $("zoneSel").onchange = () => { renderZoneStats(); renderChart(); };
    $("togglePanel").onclick = () => {
      const p = $("panel"); p.classList.toggle("collapsed");
      $("togglePanel").setAttribute("aria-expanded", !p.classList.contains("collapsed"));
      setTimeout(() => { map.invalidateSize(); clip(); }, 50);
    };
  }

  const scene = (id) => state.m.scenes.find((s) => s.id === id);

  function setOverlay(key, url, pane) {
    const cur = state.overlays[key];
    if (cur && cur._url === url) return cur;
    if (cur) map.removeLayer(cur);
    state.overlays[key] = url ? L.imageOverlay(url, state.bounds, { pane, opacity: state.opacity, interactive: false }).addTo(map) : null;
    if (state.overlays[key]) state.overlays[key].on("load", clip);
    return state.overlays[key];
  }

  // ------------------------------------------------------------------ main update
  function update() {
    const m = state.m;
    renderLegend();
    if (!m.scenes.length) { renderChart(); return; }
    const a = scene(state.after), b = scene(state.before);
    const lay = (s) => s?.layers?.[state.layer] || s?.layers?.hh;
    const swipe = state.swipe && b && a && b.id !== a.id;
    setOverlay("after", lay(a), "sarAfter");
    setOverlay("before", swipe ? lay(b) : null, "sarBefore");
    $("swipe").hidden = !swipe; $("swipeLabels").hidden = !swipe;
    $("lblBefore").textContent = b ? `◀ Before · ${b.date}` : ""; $("lblAfter").textContent = a ? `After · ${a.date} ▶` : "";
    clip();
    // keep the change selector in sync with the chosen pair when one exists
    const idx = m.changes.findIndex((c) => c.from === state.before && c.to === state.after);
    if (idx >= 0 && $("changeSel").value !== "" ) { $("changeSel").value = String(idx); }
    updateChange(); renderZoneStats(); renderChart();
  }

  function renderLegend() {
    const el = $("layerLegend");
    if (state.layer === "rgb") el.innerHTML = `<span class="tag observed">Observed</span>
      <p class="hint"><span class="swatch" style="background:#d33"></span>HH (rough / double-bounce: structures, berms)
      <br><span class="swatch" style="background:#3c3"></span>HV (volume: vegetation, loose crust)
      <br><span class="swatch" style="background:#36f"></span>HH/HV ratio. Very dark = smooth, specular (calm brine, water, smooth crust).</p>`;
    else if (state.layer === "hh") el.innerHTML = `<span class="tag observed">Observed</span><div class="bar greys"></div>
      <div class="scale"><span>${state.m.display?.hh_db?.[0] ?? -25} dB<br>smooth</span><span>${state.m.display?.hh_db?.[1] ?? 0} dB<br>rough</span></div>`;
    else el.innerHTML = `<span class="tag derived">Derived</span><p class="hint"><span class="swatch" style="background:#1e90ff"></span>
      HH below ${state.m.scenes[0]?.stats?.dark_threshold_db ?? -20} dB: candidate brine / water. Smooth salt crust can also fall here; compare with the optical basemap.</p>`;
  }

  // ------------------------------------------------------------------ swipe
  function clip() {
    const after = state.overlays.after;
    if (!after || !after.getElement()) return;
    const el = after.getElement();
    if ($("swipe").hidden) { el.style.clipPath = ""; return; }
    const size = map.getSize();
    const divX = size.x * state.pct;
    $("swipe").style.left = `${divX}px`;
    const nw = map.latLngToContainerPoint(state.bounds.getNorthWest());
    const se = map.latLngToContainerPoint(state.bounds.getSouthEast());
    const w = Math.max(se.x - nw.x, 1);
    const local = Math.min(Math.max(divX - nw.x, 0), w) * (el.offsetWidth / w || 1);
    el.style.clipPath = `inset(0 0 0 ${local}px)`;
  }
  map.on("move zoom zoomend moveend resize viewreset", clip);
  (() => {
    const h = document.querySelector("#swipe .handle");
    let drag = false;
    const setX = (clientX) => {
      const r = $("map").getBoundingClientRect();
      state.pct = Math.min(Math.max((clientX - r.left) / r.width, 0.02), 0.98);
      h.setAttribute("aria-valuenow", Math.round(state.pct * 100)); clip();
    };
    h.addEventListener("pointerdown", (e) => { drag = true; h.setPointerCapture(e.pointerId); map.dragging.disable(); });
    h.addEventListener("pointermove", (e) => drag && setX(e.clientX));
    h.addEventListener("pointerup", () => { drag = false; map.dragging.enable(); });
    h.addEventListener("keydown", (e) => {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
        state.pct = Math.min(Math.max(state.pct + (e.key === "ArrowLeft" ? -0.03 : 0.03), 0.02), 0.98); clip(); e.preventDefault();
      }
    });
  })();

  // ------------------------------------------------------------------ change + interferogram
  function updateChange() {
    const v = $("changeSel").value, el = $("changeStats");
    if (v === "") { setOverlay("change", null); el.innerHTML = ""; return; }
    const c = state.m.changes[+v];
    setOverlay("change", c.layer, "sarChange");
    const s = c.stats;
    el.innerHTML = `<table>
      <tr><td>Compared area</td><td>${fmtHa(s.compared_ha)}</td></tr>
      <tr><td>Backscatter dropped ≥ ${s.threshold_db} dB</td><td class="down">${fmtHa(s.decrease_ha)}</td></tr>
      <tr><td>Backscatter rose ≥ ${s.threshold_db} dB</td><td class="up">${fmtHa(s.increase_ha)}</td></tr>
      <tr><td>New low-backscatter surface</td><td>${fmtHa(s.new_dark_ha)}</td></tr>
      <tr><td>Low-backscatter surface lost</td><td>${fmtHa(s.lost_dark_ha)}</td></tr></table>`;
  }

  function updateIfg() {
    const v = $("ifgSel").value;
    if (!v) { setOverlay("ifg", null); $("ifgHint").textContent = ""; return; }
    const g = state.m.interferograms[+v.slice(1)];
    if (v[0] === "p") {
      setOverlay("ifg", g.phase, "sarIfg");
      $("ifgHint").innerHTML = `<div class="bar diverging"></div><div class="scale"><span>−${g.phase_range_rad[1].toFixed(1)} rad</span><span>+${g.phase_range_rad[1].toFixed(1)} rad</span></div>
        Unwrapped phase relative to the AOI median, one ~12-day pair. 2π rad ≈ ${g.los_cm_per_cycle} cm of line-of-sight change.
        <b>Not a subsidence rate</b>: atmospheric delay is not removed.`;
    } else {
      setOverlay("ifg", g.coherence, "sarIfg");
      $("ifgHint").innerHTML = `<div class="bar coh"></div><div class="scale"><span>0 · unreliable</span><span>1 · stable</span></div>
        Mean coherence ${g.mean_coherence ?? "–"}. Low coherence marks surfaces that changed between passes (brine, wet vegas, moving crust).`;
    }
  }

  // ------------------------------------------------------------------ zones + chart
  function zoneRow(s, zone) { return s?.stats?.zones?.[zone]; }

  function renderZoneStats() {
    const el = $("zoneStats"), zone = $("zoneSel").value || "Whole AOI";
    const a = scene(state.after), b = scene(state.before);
    const za = zoneRow(a, zone), zb = zoneRow(b, zone);
    if (!za) { el.innerHTML = state.m.scenes.length ? `<p class="hint">No statistics for “${zone}” yet: re-run process_gcov after adding it to zones.geojson.</p>` : ""; return; }
    const d = (x, y, f) => (x == null || y == null || a.id === b.id ? "" : `<span class="${x - y >= 0 ? "up" : "down"}">${x - y >= 0 ? "+" : ""}${f(x - y)}</span>`);
    el.innerHTML = `<div class="big">${fmtHa(za.dark_ha)}</div>
      <div class="hint">low-backscatter surface on ${a.date} <span class="tag derived">Derived</span></div>
      <table><tr><th></th><th>${b.date}</th><th>${a.date}</th><th>Δ</th></tr>
      <tr><td>Low-backscatter</td><td>${fmtHa(zb?.dark_ha)}</td><td>${fmtHa(za.dark_ha)}</td><td>${d(za.dark_ha, zb?.dark_ha, (v) => Math.round(v) + " ha")}</td></tr>
      <tr><td>Mean HH</td><td>${fmtDb(zb?.mean_hh_db)}</td><td>${fmtDb(za.mean_hh_db)}</td><td>${d(za.mean_hh_db, zb?.mean_hh_db, (v) => v.toFixed(1) + " dB")}</td></tr>
      <tr><td>Mean HV</td><td>${fmtDb(zb?.mean_hv_db)}</td><td>${fmtDb(za.mean_hv_db)}</td><td>${d(za.mean_hv_db, zb?.mean_hv_db, (v) => v.toFixed(1) + " dB")}</td></tr></table>`;
  }

  function renderChart() {
    const el = $("chart"), zone = $("zoneSel").value || "Whole AOI";
    const pts = state.m.scenes.map((s) => ({ t: Date.parse(s.date), v: zoneRow(s, zone)?.dark_ha, s })).filter((p) => p.v != null);
    const months = (state.precip?.monthly || []).map((r) => ({ t: Date.parse(r.month + "-01"), v: r.precip_mm }));
    if (!pts.length && !months.length) { el.innerHTML = `<p class="hint">Time series appears once data is processed.</p>`; return; }
    const W = 340, H = 190, L0 = 38, R0 = 38, T0 = 14, B0 = 26, iw = W - L0 - R0, ih = H - T0 - B0;
    const ts = [...pts.map((p) => p.t), ...months.map((p) => p.t), ...months.map((p) => p.t + 30 * 864e5)];
    let t0 = Math.min(...ts), t1 = Math.max(...ts);
    if (pts.length && !months.length) { t0 -= 6 * 864e5; t1 += 6 * 864e5; }
    if (t1 === t0) t1 = t0 + 864e5;
    const x = (t) => L0 + ((t - t0) / (t1 - t0)) * iw;
    const pMax = Math.max(10, ...months.map((p) => p.v)), aMax = Math.max(1, ...pts.map((p) => p.v)) * 1.15;
    const yP = (v) => T0 + ih - (v / pMax) * ih, yA = (v) => T0 + ih - (v / aMax) * ih;
    let svg = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">`;
    svg += `<line x1="${L0}" y1="${T0 + ih}" x2="${L0 + iw}" y2="${T0 + ih}" stroke="#2a313b"/>`;
    months.forEach((p) => {
      const x0 = x(p.t), x1 = x(p.t + 28 * 864e5);
      svg += `<rect x="${x0}" y="${yP(p.v)}" width="${Math.max(x1 - x0 - 1, 1)}" height="${T0 + ih - yP(p.v)}" fill="#4a7fb0" opacity=".55"><title>${new Date(p.t).toISOString().slice(0, 7)}: ${p.v} mm (NASA POWER)</title></rect>`;
    });
    if (pts.length) {
      svg += `<polyline fill="none" stroke="#e2b35b" stroke-width="2" points="${pts.map((p) => `${x(p.t)},${yA(p.v)}`).join(" ")}"/>`;
      pts.forEach((p) => {
        const sel = p.s.id === state.after || p.s.id === state.before;
        svg += `<circle cx="${x(p.t)}" cy="${yA(p.v)}" r="${sel ? 4.5 : 3}" fill="${sel ? "#f3efe6" : "#e2b35b"}"><title>${p.s.date}: ${Math.round(p.v)} ha low-backscatter</title></circle>`;
      });
    }
    // axes labels
    const tick = (t) => new Date(t).toISOString().slice(0, 7);
    svg += `<text x="${L0}" y="${H - 8}">${tick(t0)}</text><text x="${L0 + iw}" y="${H - 8}" text-anchor="end">${tick(t1)}</text>`;
    if (months.length) svg += `<text x="4" y="${T0 + 4}">${Math.round(pMax)} mm</text><text x="4" y="${T0 + ih}">0</text>`;
    if (pts.length) svg += `<text x="${W - 4}" y="${T0 + 4}" text-anchor="end">${Math.round(aMax)} ha</text><text x="${W - 4}" y="${T0 + ih}" text-anchor="end">0</text>`;
    svg += `</svg>`;
    el.innerHTML = svg + `<p class="hint"><span class="swatch" style="background:#e2b35b"></span>Low-backscatter area in “${zone}” <span class="tag derived">Derived</span>
      ${months.length ? `<br><span class="swatch" style="background:#4a7fb0"></span>Monthly rain, NASA POWER <span class="tag context">Context</span>` : ""}</p>`;
  }

  // ------------------------------------------------------------------ places (OpenStreetMap via Overpass, context only)
  async function loadPlaces(bb) {
    const pad = 0.35, [w, s, e, n] = bb;
    const q = `[out:json][timeout:25];node["place"~"town|village|hamlet"](${s - pad},${w - pad},${n + pad},${e + pad});out;`;
    try {
      const r = await fetch("https://overpass-api.de/api/interpreter", { method: "POST", body: "data=" + encodeURIComponent(q) });
      const j = await r.json();
      j.elements.forEach((el) => {
        if (!el.tags?.name) return;
        L.circleMarker([el.lat, el.lon], { radius: 4, color: "#fff", weight: 1, fillColor: "#e2b35b", fillOpacity: 1 })
          .bindTooltip(el.tags.name, { permanent: true, direction: "right", className: "place-label", offset: [6, 0] })
          .addTo(places);
      });
    } catch (e) { /* offline or rate-limited: places are optional context */ }
  }

  // ------------------------------------------------------------------ draw a zone
  const drawCtl = new L.Draw.Polygon(map, { shapeOptions: { color: "#e2b35b" } });
  $("drawBtn").onclick = () => drawCtl.enable();
  map.on(L.Draw.Event.CREATED, (e) => {
    drawn.clearLayers(); drawn.addLayer(e.layer);
    const f = e.layer.toGeoJSON(); f.properties = { name: "My zone (rename me)" };
    f.geometry.coordinates = f.geometry.coordinates.map((ring) => ring.map(([x, y]) => [+x.toFixed(5), +y.toFixed(5)]));
    $("drawText").value = JSON.stringify(f);
    $("drawOut").hidden = false;
  });
  $("copyBtn").onclick = async () => {
    try { await navigator.clipboard.writeText($("drawText").value); $("copyBtn").textContent = "Copied"; }
    catch (e) { $("drawText").select(); }
    setTimeout(() => ($("copyBtn").textContent = "Copy"), 1500);
  };

  init();
})();
