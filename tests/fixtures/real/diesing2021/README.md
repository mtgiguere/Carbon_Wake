# Real Diesing 2021 fixture — provenance and license

`OCdensity_quantrf_mean.win60.tif` and `OCdensity_quantrf_tot.unc.win60.tif`
are 60x60-pixel windowed copies (window offset col=1847, row=1877; German
Bight coast, ~53.8° N 7.7° E — deliberately containing both mapped seafloor and
land/nodata) of the same-named rasters in `Diesing_2021.zip`, downloaded
2026-08-23 from PANGAEA (DOI
[10.1594/PANGAEA.928272](https://doi.org/10.1594/PANGAEA.928272)).

Produced with rasterio: the windowed pixel values, dtype (float32), CRS
(500 m Lambert Azimuthal Equal-Area), nodata (-3.4e38), and the window's
georeferencing are carried over unchanged — only the extent is reduced. Pixel
values are bit-identical to the source window.

**Ground truth pinned at creation time** (read straight off the crop files
with rasterio, independent of `carbon_atlas.ingest.diesing`):

- pixel (row=7, col=17), center lat 53.901543 lon 7.599223 (sea):
  mean = 1.5459666 kg/m3, uncertainty = 2.3630075 kg/m3
- pixel (row=59, col=0), center lat 53.665470 lon 7.483920 (land): nodata
- per-raster pixel counts: 1868 mapped, 1732 nodata — identical masks in both.

**Source & attribution:** Diesing, M. (2021): Spatially predicted sedimentation
rates, organic carbon densities and organic carbon accumulation rates in
surface sediments of the North Sea and Skagerrak. PANGAEA,
doi:10.1594/PANGAEA.928272. Supplement to Diesing, Thorsnes & Bjarnadóttir
(2021), Biogeosciences 18(6), 2139–2160, doi:10.5194/bg-18-2139-2021.
License **CC-BY-4.0** — redistribution of this sample with this attribution.
