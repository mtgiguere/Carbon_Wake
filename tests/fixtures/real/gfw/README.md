# Real GFW fixtures — provenance and license

Both files below are cut from `fleet-daily-csvs-100-v3-2012.zip`, downloaded
2026-08-23 from Zenodo
(DOI [10.5281/zenodo.14982712](https://doi.org/10.5281/zenodo.14982712)).
No row was edited — a hand-tweaked "real" fixture would defeat the entire
point of Blind spot A (see docs/ARCHITECTURE.md §5): these files exist so the
code is tested against what Global Fishing Watch actually publishes.

## fleet-daily-100-v3-2012-02-04.head500.csv

The **verbatim** first 501 lines (header + 500 rows) of the member
`fleet-daily-csvs-100-v3-2012-02-04.csv`. Selection: file position only.

## fleet-daily-100-v3-2012.german-bight-box.csv

Every row of the **entire 2012 product** (all 366 daily members) whose
`cell_ll_lat`/`cell_ll_lon` falls in the German Bight box
lat [53.66, 53.92], lon [7.48, 7.72] — the area covered by the committed
Diesing 2021 raster crop (../diesing2021/) — under the source header. 1153
rows, verbatim; the spatial filter is the only selection applied. This is a
miniature of the real annual ETL: a year of real effort overlapping real
carbon pixels.

**Ground truth pinned at creation time** (plain-dict aggregation + raw
rasterio against the carbon crop, independent of `carbon_atlas`): summing
`fishing_hours` of the `trawlers` + `dredge_fishing` rows per 0.01° cell and
sampling the crop at each cell center gives **220 cells on mapped carbon
(139.7554 h)** and **97 cells unmapped (168.4296 h** — centers on land or
outside the 30 km crop). Busiest mapped cell: lower-left (53.90, 7.64),
15.0057 h on OC density 1.5652642 ± 2.4579988 kg/m3.

**Source & attribution:** Global Fishing Watch, *AIS-based Apparent Fishing
Effort by Flag State and Gear Type, version 3.0* (2012–2024). Data licensed
**CC BY-NC 4.0** — redistribution of this sample is non-commercial and carries
this attribution, per ADR-0008/ADR-0009.

If GFW publishes a v4 with a different schema, refresh this fixture from the
new product in the same PR that adapts the parser — never edit it in place.
