# SI disclosure: drafted with assistance from Claude (Anthropic); reviewed by the PunaPulse SAR team.
"""Shared configuration for the PunaPulse SAR pipeline.

Edit the values here (or pass CLI flags) rather than hard-coding them in scripts.
"""
import os
from pathlib import Path

# Salar de Olaroz-Cauchari, Jujuy, Argentina  (west, south, east, north) in degrees
AOI_BBOX = (-66.85, -23.75, -66.55, -23.20)
AOI_NAME = "Salar de Olaroz-Cauchari (Jujuy, Argentina)"
AOI_CENTER = (-23.45, -66.70)  # (lat, lon) used for the NASA POWER precipitation point

REPO_ROOT = Path(__file__).resolve().parents[1]
# downloaded HDF5 files + search results (git-ignored)
RAW_DIR = Path(os.environ.get("PUNAPULSE_RAW_DIR", REPO_ROOT / "data" / "raw"))
# processed, web-ready layers (committed, served by GitHub Pages)
WEB_DATA_DIR = Path(os.environ.get("PUNAPULSE_WEB_DATA_DIR", REPO_ROOT / "docs" / "data"))

# Output grid: Web Mercator (EPSG:3857) so PNG overlays line up exactly in Leaflet.
OUTPUT_PIXEL_M = 25.0     # pixel size in EPSG:3857 units (~23 m on the ground at this latitude)

# Speckle smoothing: boxcar window (pixels, odd number; 1 = off), applied in linear power.
BOXCAR = 3

# Fixed display stretches (dB) so colours are comparable between dates.
HH_DB_RANGE = (-25.0, 0.0)
HV_DB_RANGE = (-32.0, -8.0)
RATIO_DB_RANGE = (0.0, 15.0)

# "Low-backscatter surface" class: candidate open brine / water (smooth, specular surfaces).
# NOTE: smooth salt crust can also be dark at L-band -> always interpret with the optical basemap
# and with the change between dates. Tune per scene if needed (see docs/SCIENCE in README).
DARK_HH_DB = -20.0

# Change map: |10*log10(after/before)| below this (dB) is treated as "no significant change".
CHANGE_DB = 2.0

# NASA L-band wavelength used by NISAR (m) - for interferogram legends only.
NISAR_L_WAVELENGTH_M = 0.2384

# Prefer one data-maturity level; ASF advises not to mix BETA / PROVISIONAL / VALIDATED in one analysis.
MATURITY_PREFERENCE = ("VALIDATED", "PROVISIONAL", "BETA")
