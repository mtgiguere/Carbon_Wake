/* Trawl Carbon Atlas map page (ADR-0015, ADR-0016).
 *
 * Visual-honesty rules this file implements (docs/SHOWCASE_SPIKE.md §3):
 * color encodes measured hours per km2 only; unmapped cells get their own
 * distinct treatment (never the ocean background — unknown is not zero); the
 * effort layer label and full attribution stack render on the page; the
 * estimate's RANGE is the default view; every run is titled and priced with
 * its own year (ADR-0016).
 *
 * Test hooks (the Blind-spot-B pixel and behavior tests drive these):
 *   window.__atlasIdle              — true once the map has fully rendered
 *   window.__atlas.map              — the MapLibre map
 *   window.__atlas.hasOverlay       — overlay layers exist
 *   window.__atlas.currentRun       — the run being displayed
 *   window.__atlas.estimate         — the current run's estimate payload
 *   window.__atlas.footprint        — the cumulative-footprint payload (null: none computed)
 *   window.__atlas.setOverlayVisible(bool)
 * ?basemap=none renders without the external basemap so tests exercise OUR
 * layers with zero third-party network dependence.
 */

(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  var statusBox = document.getElementById("status");

  /* ---------- helpers ---------- */

  function el(tag, text, attrs) {
    var node = document.createElement(tag);
    if (text) node.textContent = text;
    if (attrs) Object.keys(attrs).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    return node;
  }

  function tonnes(kg) {
    var t = kg / 1000.0;
    if (t >= 1e6) return (t / 1e6).toPrecision(3) + " Mt";
    if (t >= 1e3) return (t / 1e3).toPrecision(3) + " kt";
    return t.toLocaleString("en-US", { maximumSignificantDigits: 3 }) + " t";
  }

  // Compact units alone once hid a 1000x disagreement behind one letter
  // (3.98 kt vs 3.98 Mt — same digits). The exact tonne count with thousands
  // separators makes the order of magnitude impossible to miss.
  function exactTonnes(kg) {
    return Math.round(kg / 1000.0).toLocaleString("en-US") + " t";
  }

  function co2Text(quantity) {
    var text = tonnes(quantity.mean_kg) + " ± " + tonnes(quantity.uncertainty_kg);
    if (quantity.mean_kg >= 1e6) text += " (" + exactTonnes(quantity.mean_kg) + ")";
    return text;
  }

  // Everyday-unit anchors (backlog #6): two significant figures — a familiar
  // scale, never a precise-looking count — with the uncertainty alongside in
  // the same unit. The server computes the counts and ships each with its
  // citation and its "for scale only" basis; this only formats them.
  function unitsText(n) {
    var rounded = Number(n.toPrecision(2));
    return rounded >= 1000 ? Math.round(rounded).toLocaleString("en-US") : String(rounded);
  }

  function anchorCountText(anchor) {
    return unitsText(anchor.mean_units) + " ± " + unitsText(anchor.uncertainty_units);
  }

  /* ---------- the map ---------- */

  function blankStyle() {
    return {
      version: 8,
      sources: {},
      layers: [{ id: "bg", type: "background", paint: { "background-color": "#dfe8ee" } }],
    };
  }

  var map = new maplibregl.Map({
    container: "map",
    style: params.get("basemap") === "none"
      ? blankStyle()
      : "https://tiles.openfreemap.org/styles/positron",
    center: [4.0, 55.5],
    zoom: 5.2,
    attributionControl: { compact: false },
  });

  function removeOverlay() {
    ["cells-mapped", "cells-unmapped"].forEach(function (id) {
      if (map.getLayer(id)) map.removeLayer(id);
    });
    if (map.getSource("cells")) map.removeSource("cells");
  }

  function addOverlay(runId) {
    removeOverlay();
    map.addSource("cells", {
      type: "vector",
      tiles: [window.location.origin + "/api/runs/" + runId + "/tiles/{z}/{x}/{y}.mvt"],
      minzoom: 0,
      maxzoom: 14,
    });
    map.addLayer({
      id: "cells-unmapped",
      type: "fill",
      source: "cells",
      "source-layer": "cells",
      filter: ["!", ["to-boolean", ["get", "mapped"]]],
      paint: { "fill-color": "#9aa5ad", "fill-opacity": 0.55 },
    });
    map.addLayer({
      id: "cells-mapped",
      type: "fill",
      source: "cells",
      "source-layer": "cells",
      filter: ["to-boolean", ["get", "mapped"]],
      paint: {
        // Hours per km2 of seabed, so one ramp is honest at every zoom —
        // low-zoom tiles are 0.1-degree aggregates, high-zoom tiles are the
        // 0.01-degree cells, and both carry their true area.
        "fill-color": [
          "interpolate",
          ["linear"],
          ["/", ["get", "fishing_hours"], ["get", "area_km2"]],
          0, "#fee08b",
          20, "#f46d43",
          80, "#a50026",
        ],
        "fill-opacity": 0.75,
      },
    });
    window.__atlas.hasOverlay = true;
  }

  window.__atlas = {
    map: map,
    hasOverlay: false,
    currentRun: null,
    estimate: null,
    setOverlayVisible: function (visible) {
      var value = visible ? "visible" : "none";
      ["cells-mapped", "cells-unmapped"].forEach(function (id) {
        if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", value);
      });
    },
  };

  map.on("idle", function () { window.__atlasIdle = true; });
  map.on("render", function () { window.__atlasIdle = false; });

  /* ---------- the estimate panel ---------- */

  var presetStops = [];

  function renderRange() {
    var estimate = window.__atlas.estimate;
    var box = document.getElementById("estimate-range");
    box.replaceChildren();
    var byKey = {};
    estimate.estimates.forEach(function (e) { byKey[e.preset.key] = e; });
    var low = byKey[estimate.range.low.preset_key];
    var high = byKey[estimate.range.high.preset_key];
    function endText(entry) {
      var flag = entry.preset.derivation ? " (inferred)" : "";
      return co2Text(entry.aqueous_co2) + " — " + entry.preset.label + flag;
    }
    box.appendChild(
      el("strong", "First-year aqueous CO₂, " + estimate.effort_year + " (mapped effort only)")
    );
    box.appendChild(el("div", "low: " + endText(low)));
    box.appendChild(el("div", "high: " + endText(high)));
    // Anchor BOTH ends in the same everyday unit: the range is the message.
    low.anchors.forEach(function (anchor, i) {
      var node = el("div", null, { class: "anchor", style: "color:#555;margin-top:4px" });
      node.appendChild(
        el("div", "As " + anchor.unit_label + ": low ≈ " + anchorCountText(anchor) +
          ", high ≈ " + anchorCountText(high.anchors[i]) + " — the disagreement is the story.")
      );
      node.appendChild(el("div", anchor.basis, { style: "font-size:11px;color:#777" }));
      box.appendChild(node);
    });
    box.appendChild(
      el("div", "disturbed organic carbon: " +
        tonnes(estimate.disturbed_carbon.mean_kg) + " ± " +
        tonnes(estimate.disturbed_carbon.uncertainty_kg), { style: "color:#555" })
    );
    box.hidden = false;
    document.getElementById("preset-detail").hidden = true;
  }

  function renderPreset(entry) {
    var box = document.getElementById("preset-detail");
    box.replaceChildren();
    box.appendChild(el("strong", entry.preset.label));
    box.appendChild(el("div", "aqueous CO₂: " + co2Text(entry.aqueous_co2)));
    box.appendChild(
      el("div", "atmospheric CO₂: " +
        (entry.atmospheric_co2 ? co2Text(entry.atmospheric_co2)
                               : "unknown — not quantified by the source"))
    );
    if (entry.preset.derivation) {
      box.appendChild(el("div", "inferred: " + entry.preset.derivation, { style: "color:#8a5a00" }));
    }
    entry.anchors.forEach(function (anchor) {
      var node = el("div", null, { class: "anchor", style: "color:#555;margin-top:4px" });
      node.appendChild(el("div", "≈ " + anchorCountText(anchor) + " " + anchor.unit_label));
      node.appendChild(el("div", anchor.basis, { style: "font-size:11px;color:#777" }));
      node.appendChild(el("div", anchor.citation, { style: "font-size:11px;color:#777" }));
      box.appendChild(node);
    });
    box.appendChild(
      el("div", (entry.preset.accounts_for_additionality
        ? "credits natural background remineralization (additionality)"
        : "does not credit additionality"), { style: "color:#555" })
    );
    box.appendChild(el("div", entry.preset.citation, { style: "color:#555;font-size:11px" }));
    box.appendChild(
      el("div", "Note: the map's spatial pattern does not change with the preset — " +
        "every cell scales by the same factor; only the magnitude moves.",
        { style: "color:#777;font-size:11px;margin-top:4px" })
    );
    document.getElementById("estimate-range").hidden = true;
    box.hidden = false;
  }

  function renderEstimate(estimate) {
    window.__atlas.estimate = estimate;
    presetStops = estimate.estimates.slice().sort(function (a, b) {
      return (a.preset.remineralization_fraction - b.preset.remineralization_fraction) ||
             (a.preset.key < b.preset.key ? -1 : 1);
    });
    var slider = document.getElementById("preset-slider");
    slider.min = 0;
    slider.max = presetStops.length - 1;
    slider.value = Math.floor(presetStops.length / 2);

    var list = document.getElementById("caveat-list");
    list.replaceChildren();
    estimate.caveats.forEach(function (caveat) {
      list.appendChild(el("li", caveat, { style: "margin-bottom:4px" }));
    });
    list.appendChild(
      el("li", "coverage: " +
        Math.round(estimate.effort_coverage.fishing_hours_mapped).toLocaleString("en-US") +
        " fishing hours on mapped carbon; " +
        Math.round(estimate.effort_coverage.fishing_hours_unmapped).toLocaleString("en-US") +
        " hours on unmapped seafloor are excluded from this estimate.")
    );

    renderRange();
    document.getElementById("estimate").hidden = false;
  }

  // Wired ONCE — year switches re-render, they must not stack listeners.
  document.getElementById("preset-slider").addEventListener("input", function (event) {
    renderPreset(presetStops[Number(event.target.value)]);
  });
  document.getElementById("show-range").addEventListener("click", renderRange);

  /* ---------- the cumulative footprint (ADR-0017) ---------- */

  function pct(fraction) {
    var value = fraction * 100;
    return (value < 10 ? value.toFixed(1) : value.toFixed(0)) + " %";
  }

  function km2(m2) {
    return Math.round(m2 / 1e6).toLocaleString("en-US") + " km²";
  }

  // A coverage claim, never a single number: floor, Poisson union, ceiling,
  // the years and the denominator on the headline; method, comparator, and
  // caveats one gesture away. The server did every division.
  function renderFootprint(fp) {
    var box = document.getElementById("footprint");
    var years = fp.years;
    var span = years.length > 1 ? years[0] + "–" + years[years.length - 1] : String(years[0]);
    var f = fp.mapped_seabed.fraction;
    box.replaceChildren();
    box.appendChild(
      el("strong", "Trawled at least once, " + span + ": ≈ " + pct(f.poisson) +
        " of the mapped seabed")
    );
    box.appendChild(
      el("div", "bracket — floor " + pct(f.lower) + " (largest single year) · ceiling " +
        pct(f.upper) + " (years never overlapping); headline = random-placement union across " +
        years.length + (years.length === 1 ? " year" : " years"), { style: "color:#555" })
    );
    box.appendChild(
      el("div", "denominator: " + km2(fp.mapped_seabed_area_m2) +
        " of carbon-mapped seabed (Diesing 2021). A coverage claim, independent of any CO₂ preset.",
        { style: "font-size:11px;color:#777" })
    );
    var details = el("details", null, { style: "margin-top:4px" });
    details.appendChild(el("summary", "method, comparator & caveats", { style: "cursor:pointer" }));
    details.appendChild(
      el("div", "per year: " + years.map(function (y) {
        return y + " " + pct(fp.per_year_mapped_fraction[String(y)]);
      }).join(", "), { style: "font-size:11px;color:#555;margin-top:4px" })
    );
    details.appendChild(el("div", fp.method.description, { style: "font-size:11px;color:#555;margin-top:4px" }));
    details.appendChild(el("div", fp.method.citation, { style: "font-size:11px;color:#555;margin-top:4px" }));
    details.appendChild(
      el("div", "Published comparator: " + fp.method.published_comparator,
        { style: "font-size:11px;color:#555;margin-top:4px" })
    );
    var list = el("ul", null, { style: "margin:6px 0 0 16px;padding:0;font-size:11px;color:#555" });
    fp.caveats.forEach(function (caveat) { list.appendChild(el("li", caveat, { style: "margin-bottom:3px" })); });
    details.appendChild(list);
    box.appendChild(details);
    box.hidden = false;
  }

  fetch("/api/footprint/")
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (fp) {
      window.__atlas.footprint = fp;
      if (fp) renderFootprint(fp);
    })
    .catch(function () { window.__atlas.footprint = null; });

  /* ---------- runs and the year axis ---------- */

  function selectRun(run) {
    window.__atlas.currentRun = run;
    addOverlay(run.id);
    statusBox.textContent =
      run.effort_year + ", run " + run.id + ": " +
      run.cells_mapped.toLocaleString("en-US") + " cells on mapped carbon, " +
      run.cells_unmapped.toLocaleString("en-US") +
      " on unmapped seafloor (shown grey — unknown, not zero)";
    fetch("/api/runs/" + run.id + "/estimate/")
      .then(function (r) { return r.json(); })
      .then(renderEstimate)
      .catch(function (error) { statusBox.textContent = "failed to load estimate: " + error; });
  }

  function wireYears(runs) {
    // One run per year on the axis (the newest run wins a duplicate year).
    var byYear = {};
    runs.forEach(function (run) {
      if (!(run.effort_year in byYear) || run.id > byYear[run.effort_year].id) {
        byYear[run.effort_year] = run;
      }
    });
    var years = Object.keys(byYear).map(Number).sort(function (a, b) { return a - b; });
    var newest = byYear[years[years.length - 1]];

    if (years.length > 1) {
      var slider = document.getElementById("year-slider");
      var label = document.getElementById("year-label");
      slider.min = 0;
      slider.max = years.length - 1;
      slider.value = years.length - 1;
      label.textContent = String(newest.effort_year);
      slider.addEventListener("input", function () {
        var run = byYear[years[Number(slider.value)]];
        label.textContent = String(run.effort_year);
        selectRun(run);
      });
      document.getElementById("year-control").hidden = false;
    }
    selectRun(newest);
  }

  map.on("load", function () {
    fetch("/api/runs/")
      .then(function (r) { return r.json(); })
      .then(function (body) {
        if (!body.runs.length) {
          statusBox.textContent = "no ETL runs in the database yet";
          return;
        }
        wireYears(body.runs);
      })
      .catch(function (error) { statusBox.textContent = "failed to load runs: " + error; });
  });
})();
