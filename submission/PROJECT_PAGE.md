# Space Apps project page: text ready to paste (English)

> Fill in every `[ ]` after running the pipeline. Do not paste numbers you have not computed.
> Check the field names against the live project-submission form.

---

## Project name
PunaPulse SAR

## High-level project summary
PunaPulse SAR is an open-source web app that turns NASA-ISRO NISAR L-band radar data into an easy-to-read record of surface change in the Salar de Olaroz-Cauchari, a high-Andean salt flat in Jujuy, Argentina, where lithium brine is evaporated in large ponds.

Every 12 days, day or night and through cloud and dust, NISAR shows us three things:
- how far the smooth, dark brine surfaces extend;
- where backscatter changed between dates;
- how stable the ground stayed (coherence).

A before/after swipe, hectares per user-drawn zone, and rainfall context from NASA POWER let communities, researchers and regulators see these changes for themselves. Every layer is labelled as observed, derived, context or hypothesis, so nobody over-reads the radar.

## Link to demo
`[30-second video URL, public, no login]` (or up to 7 slides; keep within the official limit)

## Link to final project
`https://YOUR-USER.github.io/punapulse-sar/` · code: `https://github.com/YOUR-USER/punapulse-sar`

## Project details

**What it does.** PunaPulse SAR tracks surface change at a lithium brine operation in the Puna, at almost 4,000 m in one of the driest places on Earth. A Python pipeline does five things:
1. Searches the ASF archive for every NISAR GCOV frame over the salar.
2. Picks a stack from one track, one pass direction and one data-maturity level, so that dates are truly comparable.
3. Downloads it with a free Earthdata login.
4. Reads only the area of interest from the HDF5 files.
5. Produces web layers, using a common Web-Mercator grid, so every layer lines up:
   - a dual-pol colour composite (HH, HV, HH/HV);
   - HH backscatter in dB;
   - a "low-backscatter surface" mask (candidate brine or water);
   - change maps between dates;
   - hectares for the whole salar and for any zone drawn by the user.

As an exploratory layer, it also shows one NISAR GUNW interferogram (coherence and relative phase).

**How it works.** Radar responds to surface roughness and moisture:
- Calm brine reflects the radar pulse away from the sensor and looks very dark.
- Berms, rough salt crust and built structures look bright.
- Wetter soil in the *vegas* (high-Andean wetlands) raises backscatter.

The low-backscatter area per date gives a simple indicator of the pond footprint. The change map shows where the surface became smoother or wetter (blue) or rougher or drier (red). The viewer is a static Leaflet app on GitHub Pages: no server, free to host, and easy for anyone to fork for another salar.

**Results so far.** `[Fill after running: e.g. "Between [date] and [date], the low-backscatter surface inside the [zone] grew from [x] ha to [y] ha (+[z] ha), during a month with [r] mm of rain (NASA POWER)."]`

**Benefits.** The data is open, repeatable every 12 days, and independent of company reporting or cloud-free optical images. A community member can use the swipe. A researcher can download the numbers. A regulator gets a consistent footprint series.

**What we were careful about (validity).**
- Smooth salt crust can look as dark as brine, so the mask is labelled "candidate" and always shown next to optical imagery.
- The app refuses to imply that one 12-day interferogram is a subsidence rate, because atmospheric delay over the Andes can be larger than mm-level motion.
- Data that is not VALIDATED is flagged.
- Rain from NASA POWER is coarse and is used as context only.
- We state hypotheses as hypotheses: for example, that pond growth, not rain, explains new dark surfaces during the dry season.

**Tools.** Python (asf_search, h5py, numpy, pyproj, Pillow), JavaScript (Leaflet, Leaflet.draw), GitHub Pages, Google Colab. No paid services.

**Next steps.**
- Build a long NISAR interferometric time series to measure real deformation rates around the wellfields.
- Add SAOCOM L-band (CONAE) data for denser revisits.
- Calibrate the brine mask with field or optical labels.
- Co-design alerts with local communities.

## Use of super-intelligence (SI)
We used an SI tool, Claude by Anthropic, to help draft the pipeline code, the web app code and the documentation. The team reviewed, ran, tested and edited the output. `[Team: describe how you chose the idea and what you built or changed yourselves.]`

No SI-generated images, video or audio are used. All map layers are computed from NISAR data by our code. Source files drafted with SI assistance carry a header note.

## NASA data
- NISAR L2 GCOV (Geocoded Polarimetric Covariance), L-band HH/HV, NASA-ISRO, from the ASF DAAC: `[list granule IDs / dates used]`
- NISAR L2 GUNW (Geocoded Unwrapped Interferogram), exploratory: `[granule ID]`
- NASA POWER daily precipitation (PRECTOTCORR)
- NASA GIBS: MODIS Terra Corrected Reflectance (optical context basemap)

## Space agency partner data
None used in this version. CONAE SAOCOM L-band is planned as future work.

## References
- NISAR Data User Guide (ASF): https://nisar-docs.asf.alaska.edu/
- ASF Data Search Vertex: https://search.asf.alaska.edu/
- asf_search Python package: https://github.com/asfadmin/Discovery-asf_search
- NASA Earthdata, Intro to SAR: https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar
- NASA POWER API: https://power.larc.nasa.gov/
- NASA GIBS: https://nasa-gibs.github.io/gibs-api-docs/
- Leaflet: https://leafletjs.com/ · Leaflet.draw: https://github.com/Leaflet/Leaflet.draw
- Esri World Imagery; © OpenStreetMap contributors (Overpass API)
