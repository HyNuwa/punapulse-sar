# PunaPulse SAR

**Open NISAR L-band radar watch over the Salar de Olaroz-Cauchari (Jujuy, Argentina).**
NASA Space Apps Challenge 2026 · Challenge: *Dancing with the SARs*

PunaPulse SAR is an open-source web app plus a small Python pipeline. It turns NASA-ISRO **NISAR** radar products into maps that anyone can read. The target is a high-Andean salt flat in the "Lithium Triangle", where lithium brine is pumped into large evaporation ponds. Local communities, researchers and regulators ask what is changing on the surface: how far the ponds spread, what happens to the surrounding *vegas* (high-Andean wetlands), and whether the ground moves. That information is often closed or hard to interpret. NISAR images the site every 12 days, day or night and through cloud and dust, with free and open data.

> **Live app:** `https://hynuwa.github.io/punapulse-sar/` (GitHub Pages, folder `docs/`)

![Evidence labels](https://img.shields.io/badge/evidence-observed%20%7C%20derived%20%7C%20context%20%7C%20hypothesis-555)

---

## What the app shows

| Layer | Evidence type | What it means |
|---|---|---|
| Dual-pol composite (R=HH, G=HV, B=HH/HV) | **Observed** | NISAR GCOV backscatter. Bright = rough or built surfaces; dark = smooth, specular surfaces (calm brine, water, very smooth crust). |
| HH backscatter (dB) | **Observed** | The single channel that is most sensitive to surface roughness and moisture. |
| Low-backscatter surface | **Derived** | Pixels with HH below a threshold (default −20 dB). These are candidate brine ponds or water. Hectares are given per date and per zone. |
| Change map | **Derived** | 10·log10(after/before) of HH. Blue = backscatter dropped; red = it rose. Changes smaller than ±2 dB are hidden. |
| Interferogram (phase, coherence) | **Exploratory** | One NISAR GUNW pair. Coherence shows which surfaces stayed stable over about 12 days. |
| Optical basemaps, places, rain | **Context** | Esri imagery, NASA GIBS MODIS, OpenStreetMap places, NASA POWER monthly rain. |

Other features:
- A before/after **swipe** between any two dates.
- **Zones**: draw a polygon in the app, paste it into `docs/data/zones.geojson`, and re-run. You get hectares and mean dB for that zone over time.
- A **time series** chart of low-backscatter area per date, plotted against monthly rain.

## Scientific framing

**Hypotheses we test:**
1. Inside the pond fields, growth of the low-backscatter area between dates reflects expansion of the evaporation ponds.
2. In the vegas, backscatter changes during the dry season (outside Dec–Mar) would point to non-climatic drivers. These are worth field checks; the tool cannot prove a cause.

**Why L-band radar:**
- Radar responds to **roughness** and to the **dielectric constant** (moisture).
- Calm brine reflects the pulse away from the sensor, so it looks very dark. Berms, plant structures and rough crust look bright.
- Wetter soil raises backscatter.
- L-band (about 24 cm wavelength) penetrates further into vegetation and loose material than C-band, and keeps coherence longer.

**Limits (we state them in the app too):**
- Smooth salt crust can be as dark as brine. Interpret the mask together with optical imagery and the change between dates.
- Only compare dates from the **same track, pass direction and data maturity**. The pipeline picks such a stack automatically and warns if the inputs are mixed.
- **A single 12-day interferogram is not a subsidence rate.** Tropospheric delay over the Andes can exceed mm-level signals. Measuring subsidence would need a long time series, which is future work.
- Rain comes from NASA POWER, about 0.5° resolution, at the AOI centre. Use it as context only.
- Data that is not yet VALIDATED (BETA or PROVISIONAL) is labelled as such in the app.

## Quick start

### Option A: Google Colab (easiest)
Open `notebooks/PunaPulse_Colab.ipynb` in Colab and run the cells. At the end it gives you a zip of `docs/data/`; upload its contents to the repo.

### Option B: local
```bash
pip install -r requirements.txt
export EARTHDATA_TOKEN=...          # urs.earthdata.nasa.gov -> Generate Token (free account)

python -m pipeline.search_nisar --product GCOV --max-scenes 4   # lists every NISAR GCOV frame over the AOI
python -m pipeline.download_nisar --product GCOV                # several GB per file
python -m pipeline.process_gcov                                 # -> docs/data/*.webp + manifest.json
python -m pipeline.fetch_precip --start 2025-01-01              # NASA POWER rain
# optional, exploratory:
python -m pipeline.search_nisar --product GUNW && python -m pipeline.download_nisar --product GUNW --limit 1 && python -m pipeline.process_gunw

# or everything at once:
python -m pipeline.run_all --max-scenes 4 --start 2026-06-01

# view locally
python -m http.server -d docs 8000   # open http://localhost:8000
```

Useful flags:
- `process_gcov --dark-db -18`: tune the brine/water threshold.
- `--change-db 3`: stricter change threshold.
- `search_nisar --start/--end`: limit the date window.

### Publish
Commit `docs/` (including `docs/data/`). Then go to GitHub **Settings → Pages → Deploy from branch → main / docs**.

## Repository layout
```
pipeline/            Python: search (asf_search), download (Earthdata), GCOV + GUNW processing, NASA POWER
  config.py          AOI, thresholds, display ranges
docs/                static web app (Leaflet), served by GitHub Pages
  data/              manifest.json + processed layers (written by the pipeline)
  data/zones.geojson your zones (pond fields, vegas, ...)
notebooks/           Colab notebook
submission/          texts for the Space Apps project page, 30 s video script, slides outline
tests/               synthetic HDF5 fixtures to test the code (NOT data; never published)
```

## Data (all free and open)
- **NISAR L2 GCOV**: geocoded, terrain-corrected γ⁰ backscatter (HH, HV), NASA-ISRO, distributed by the ASF DAAC. Collections `NISAR_L2_GCOV_V1`, `_PROVISIONAL_V1` and `_BETA_V1`.
- **NISAR L2 GUNW**: geocoded unwrapped interferogram, with coherence.
- **NASA POWER**: daily precipitation (PRECTOTCORR).
- **NASA GIBS**: MODIS Terra corrected reflectance (optical context).
- **Context:** Esri World Imagery and © OpenStreetMap contributors (places, via Overpass).

## Use of super-intelligence (SI) tools: disclosure
Parts of this repository were drafted with the help of an SI tool, Claude by Anthropic: pipeline code, web app code and documentation. The team reviewed, ran and edited them. No SI-generated images, video or audio are included. All map layers are computed from NISAR data by the code in this repo. Files drafted with SI assistance carry a header note.
*Team: before submitting, add here how you chose the project idea and what you changed yourselves.*

## License
MIT. See `LICENSE`.
