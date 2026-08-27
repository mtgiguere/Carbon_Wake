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
        "fill-color": [
          "interpolate",
          ["linear"],
          ["get", "fishing_hours"],
          0, "#fee08b",
          25, "#f46d43",
          100, "#a50026",
        ],
        "fill-opacity": 0.75,
      },
    });
  }

  window.__atlas = {
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
