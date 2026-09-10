# Real EMODnet fixture — provenance and license

`windfarms_polygons.german-bight.geojson`: five **verbatim** features from the
EMODnet Human Activities WFS layer `emodnet:windfarmspoly` ("Wind Farms
(Polygons)", CETMAR for EMODnet), fetched 2026-09-08 from
`https://ows.emodnet-humanactivities.eu/wfs` (GetFeature, EPSG:4326,
application/json). License: **Creative Commons CC-BY 4.0** (stated in the
dataset's metadata record 8201070b-4b0b-4d54-8910-abcea5dce57f). No property
or coordinate was edited; the only selection is by name — the four
producing German farms just north of the committed German Bight effort box
(Gode Wind 01/02/3, Nordergründe) plus one *Planned* site (NC 1), so the
parser is exercised on real statuses, a real missing commissioning year
(Gode Wind 01 and 02 carry `year: null`), and real MultiPolygon geometry.

Status vocabulary as published: Production, Construction, Approved, Planned,
Dismantled, Test site. The atlas keeps Production and Construction as
reference zones (docs/DECISIONS.md, ADR-0018).
