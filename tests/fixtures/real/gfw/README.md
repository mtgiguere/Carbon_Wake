# Real GFW fixture — provenance and license

`fleet-daily-100-v3-2012-02-04.head500.csv` is the **verbatim** first 501 lines
(header + 500 rows) of the member `fleet-daily-csvs-100-v3-2012-02-04.csv` from
`fleet-daily-csvs-100-v3-2012.zip`, downloaded 2026-08-23 from Zenodo
(DOI [10.5281/zenodo.14982712](https://doi.org/10.5281/zenodo.14982712)).
Nothing was edited — a hand-tweaked "real" fixture would defeat the entire
point of Blind spot A (see docs/ARCHITECTURE.md §5): this file exists so the
parser is tested against what Global Fishing Watch actually publishes.

**Source & attribution:** Global Fishing Watch, *AIS-based Apparent Fishing
Effort by Flag State and Gear Type, version 3.0* (2012–2024). Data licensed
**CC BY-NC 4.0** — redistribution of this sample is non-commercial and carries
this attribution, per ADR-0008/ADR-0009.

If GFW publishes a v4 with a different schema, refresh this fixture from the
new product in the same PR that adapts the parser — never edit it in place.
