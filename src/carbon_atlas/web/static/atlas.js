/* Trawl Carbon Atlas map page (ADR-0015).
 *
 * Visual-honesty rules this file implements (docs/SHOWCASE_SPIKE.md §3):
 * color encodes measured fishing hours only; unmapped cells get their own
 * distinct treatment (never the ocean background — unknown is not zero); the
 * effort layer label and full attribution stack render on the page.
 *
 * Test hooks (Blind spot B pixel tests drive these):
 *   window.__atlasIdle          — true once the map has fully rendered
 *   window.__atlas.setOverlayVisible(bool) — toggle our data layers
 * ?basemap=none renders without the external basemap so pixel tests exercise
 * OUR layers with zero third-party network dependence.
 */

(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  var statusBox = document.getElementById("status");

  function blankStyle() {
    return {
      version: 8,
      sources: {},
      layers: [{ id: "bg", type: "background", paint: { "background-color": "#dfe8ee" } }],
    };
  }

  var style =
    params.get("basemap") === "none"
      ? blankStyle()
      : "https://tiles.openfreemap.org/styles/positron";

  var map = new maplibregl.Map({
    container: "map",
    style: style,
    center: [4.0, 55.5],
    zoom: 5.2,
    attributionControl: { compact: false },
  });

  function addOverlay(runId) {
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
  }

  window.__atlas = {
    map: map,
    hasOverlay: false,
    setOverlayVisible: function (visible) {
      var value = visible ? "visible" : "none";
      ["cells-mapped", "cells-unmapped"].forEach(function (id) {
        if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", value);
      });
    },
  };

  map.on("idle", function () {
    window.__atlasIdle = true;
  });
  map.on("render", function () {
    window.__atlasIdle = false;
  });

  map.on("load", function () {
    fetch("/api/runs/")
      .then(function (response) { return response.json(); })
      .then(function (body) {
        if (!body.runs.length) {
          statusBox.textContent = "no ETL runs in the database yet";
          return;
        }
        var run = body.runs[0]; // newest first, per the API contract
        addOverlay(run.id);
        window.__atlas.hasOverlay = true;
        statusBox.textContent =
          "run " + run.id + ": " + run.cells_mapped.toLocaleString() +
          " cells on mapped carbon, " + run.cells_unmapped.toLocaleString() +
          " on unmapped seafloor (shown grey — unknown, not zero)";
      })
      .catch(function (error) {
        statusBox.textContent = "failed to load runs: " + error;
      });
  });
})();

/* ---- The estimate panel: the range is the default view ------------------- */

(function () {
  "use strict";

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
    return t.toLocaleString(undefined, { maximumSignificantDigits: 3 }) + " t";
  }

  function co2Text(quantity) {
    return tonnes(quantity.mean_kg) + " ± " + tonnes(quantity.uncertainty_kg);
  }

  function endText(entry) {
    var flag = entry.preset.derivation ? " (inferred)" : "";
    return co2Text(entry.aqueous) + " — " + entry.preset.label + flag;
  }

  function renderRange(estimate) {
    var box = document.getElementById("estimate-range");
    box.replaceChildren();
    var byKey = {};
    estimate.estimates.forEach(function (e) { byKey[e.preset.key] = e; });
    var low = byKey[estimate.range.low.preset_key];
    var high = byKey[estimate.range.high.preset_key];
    box.appendChild(el("strong", "First-year aqueous CO₂, 2012 (mapped effort only)"));
    box.appendChild(el("div", "low: " + endText(low)));
    box.appendChild(el("div", "high: " + endText(high)));
    box.appendChild(
      el("div", "disturbed organic carbon: " +
        tonnes(estimate.disturbed_carbon.mean_kg) + " ± " +
        tonnes(estimate.disturbed_carbon.uncertainty_kg), { style: "color:#555" })
    );
    document.getElementById("estimate-range").hidden = false;
    document.getElementById("preset-detail").hidden = true;
  }

  function renderPreset(entry) {
    var box = document.getElementById("preset-detail");
    box.replaceChildren();
    box.appendChild(el("strong", entry.preset.label));
    box.appendChild(el("div", "aqueous CO₂: " + co2Text(entry.aqueous)));
    box.appendChild(
      el("div", "atmospheric CO₂: " +
        (entry.atmospheric_co2 ? co2Text(entry.atmospheric_co2)
                               : "unknown — not quantified by the source"))
    );
    if (entry.preset.derivation) {
      box.appendChild(el("div", "inferred: " + entry.preset.derivation, { style: "color:#8a5a00" }));
    }
    box.appendChild(
      el("div", (entry.preset.accounts_for_additionality
        ? "credits natural background remineralization (additionality)"
        : "does not credit additionality"), { style: "color:#555" })
    );
    box.appendChild(el("div", entry.preset.citation, { style: "color:#555;font-size:11px" }));
    document.getElementById("estimate-range").hidden = true;
    box.hidden = false;
  }

  function wire(estimate) {
    // Slider stops ordered from strongest correction to highest estimate;
    // ties broken by key so the order is deterministic.
    var stops = estimate.estimates.slice().sort(function (a, b) {
      return (a.preset.remineralization_fraction - b.preset.remineralization_fraction) ||
             (a.preset.key < b.preset.key ? -1 : 1);
    });
    // The API serves aqueous and atmospheric as *_co2; normalize the field
    // names the panel reads so render code stays uniform.
    stops.forEach(function (s) { s.aqueous = s.aqueous_co2; });

    var slider = document.getElementById("preset-slider");
    slider.min = 0;
    slider.max = stops.length - 1;
    slider.value = Math.floor(stops.length / 2);
    slider.addEventListener("input", function () {
      renderPreset(stops[Number(slider.value)]);
    });
    document.getElementById("show-range").addEventListener("click", function () {
      renderRange(estimate);
    });

    var list = document.getElementById("caveat-list");
    estimate.caveats.forEach(function (caveat) {
      list.appendChild(el("li", caveat, { style: "margin-bottom:4px" }));
    });
    list.appendChild(
      el("li", "coverage: " +
        Math.round(estimate.effort_coverage.fishing_hours_mapped).toLocaleString() +
        " fishing hours on mapped carbon; " +
        Math.round(estimate.effort_coverage.fishing_hours_unmapped).toLocaleString() +
        " hours on unmapped seafloor are excluded from this estimate.")
    );

    // Range view normalization for its own lookups:
    estimate.estimates.forEach(function (s) { s.aqueous = s.aqueous_co2; });
    renderRange(estimate);
    document.getElementById("estimate").hidden = false;
  }

  function loadEstimate() {
    fetch("/api/runs/")
      .then(function (r) { return r.json(); })
      .then(function (body) {
        if (!body.runs.length) return;
        return fetch("/api/runs/" + body.runs[0].id + "/estimate/")
          .then(function (r) { return r.json(); })
          .then(function (estimate) {
            window.__atlas.estimate = estimate;
            wire(estimate);
          });
      })
      .catch(function () { /* the map's own status line already reports failures */ });
  }

  if (window.__atlas) loadEstimate();
})();
