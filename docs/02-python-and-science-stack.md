# 02 — Python and the science stack

## Isolated environments

Create one virtual environment per project or purpose rather than installing
packages globally:

```bash
python3 -m venv ~/Work/science_venv
source ~/Work/science_venv/bin/activate

python -m pip install --upgrade pip
```

Why isolate?

- **Reproducibility** — the packages a result depends on are a known, listable
  set.
- **No cross-contamination** — a package upgrade for one project cannot break
  another.
- **Safe experiments** — delete the directory and start again.
- **No system-wide changes** — you never need `sudo pip`.

Record the environment alongside your work:

```bash
python -m pip freeze > requirements.txt     # exact versions in use
python --version
```

Use separate environments for separate jobs. For example the ecLand build in
[03](03-ecland-on-apple-silicon.md) uses its own clean environment
(`~/Work/ecland_venv`) rather than this one.

Avoid mixing environment managers in one shell. If conda is active, run
`conda deactivate` before activating a venv.

## Useful packages

You do **not** need all of these. Install what your task requires.

| Package | Typical use |
|---------|-------------|
| `numpy` | Arrays and numerics |
| `scipy` | Scientific algorithms, interpolation, statistics |
| `pandas` | Tabular and time-series data |
| `xarray` | Labelled N-dimensional arrays; the natural interface to NetCDF |
| `netCDF4` | Direct NetCDF I/O |
| `matplotlib` | Plotting |
| `dask` | Chunked / parallel computation on larger-than-memory arrays |
| `zarr` | Chunked, cloud-friendly array storage |
| `rasterio` | Raster geospatial data (GeoTIFF etc.) |
| `geopandas` | Vector geospatial data |
| `cartopy` | Maps and projections |

A modest starting point for gridded Earth-system data:

```bash
python -m pip install numpy scipy pandas xarray netCDF4 matplotlib
```

Add heavier packages when needed:

```bash
python -m pip install dask zarr
python -m pip install cartopy rasterio geopandas   # geospatial; may need system libraries (GEOS, GDAL, PROJ)
```

## Notes

- **Native libraries.** `netCDF4`, `rasterio`, `cartopy` and friends depend on
  C libraries. Wheels usually bundle them on arm64; if a build from source is
  triggered, install the corresponding Homebrew formulae from
  [01](01-mac-scientific-setup.md) first.
- **`PYTHONNOUSERSITE=1`** stops Python importing packages from
  `~/Library/Python/...`, which otherwise can silently shadow a venv. It is
  used in the ecLand build for exactly that reason.
- **Pin what matters.** For results you intend to publish or compare, keep
  `requirements.txt` (or a lock file) in version control with the analysis.
- **ECMWF data.** ecCodes and `cfgrib` bridge GRIB into xarray; they need the
  `eccodes` Homebrew library from [01](01-mac-scientific-setup.md).

Next: [03 — ecLand on Apple silicon](03-ecland-on-apple-silicon.md).
