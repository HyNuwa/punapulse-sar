# SI disclosure: drafted with assistance from Claude (Anthropic); reviewed by the PunaPulse SAR team.
"""Grid, HDF5 and image helpers shared by the processing scripts (numpy + h5py + pyproj + Pillow only)."""
import json
import re
from datetime import datetime

import h5py
import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer

from . import config


# --------------------------------------------------------------------------- output grid (EPSG:3857)
class WebGrid:
    """Regular Web-Mercator grid covering the AOI; every output layer uses it, so layers align."""

    def __init__(self, bbox=config.AOI_BBOX, pixel=config.OUTPUT_PIXEL_M):
        w, s, e, n = bbox
        to3857 = Transformer.from_crs(4326, 3857, always_xy=True)
        (x0, x1), (y0, y1) = to3857.transform([w, e], [s, n])
        self.bbox, self.pixel = bbox, pixel
        self.nx = int(np.ceil((x1 - x0) / pixel))
        self.ny = int(np.ceil((y1 - y0) / pixel))
        self.x = x0 + (np.arange(self.nx) + 0.5) * pixel           # west -> east
        self.y = y1 - (np.arange(self.ny) + 0.5) * pixel           # north -> south
        to4326 = Transformer.from_crs(3857, 4326, always_xy=True)
        _, self.lat = to4326.transform(np.full(self.ny, self.x[0]), self.y)
        # true ground area of each pixel (m^2), per row (Mercator scale = 1/cos(lat))
        self.row_area_m2 = (pixel * np.cos(np.radians(self.lat))) ** 2
        self._cache = {}

    def leaflet_bounds(self):
        w, s, e, n = self.bbox
        return [[s, w], [n, e]]

    def area_ha(self, mask):
        mask = np.asarray(mask, bool)
        return float((mask.sum(axis=1) * self.row_area_m2).sum() / 1e4)

    def sample_from(self, epsg, xc, yc):
        """Nearest-neighbour index arrays mapping this grid onto a source grid (cached per source grid)."""
        key = (int(epsg), float(xc[0]), float(xc[-1]), len(xc), float(yc[0]), float(yc[-1]), len(yc))
        if key not in self._cache:
            tr = Transformer.from_crs(3857, int(epsg), always_xy=True)
            X, Y = np.meshgrid(self.x, self.y)
            sx, sy = tr.transform(X, Y)
            dx, dy = xc[1] - xc[0], yc[1] - yc[0]
            col = np.rint((sx - xc[0]) / dx).astype(np.int64)
            row = np.rint((sy - yc[0]) / dy).astype(np.int64)
            ok = (col >= 0) & (col < len(xc)) & (row >= 0) & (row < len(yc))
            self._cache[key] = (np.where(ok, row, 0), np.where(ok, col, 0), ok)
        return self._cache[key]

    def regrid(self, data, epsg, xc, yc):
        row, col, ok = self.sample_from(epsg, xc, yc)
        out = data[row, col].astype(np.float32)
        out[~ok] = np.nan
        return out

    def rasterize_geojson(self, geometry):
        """Boolean mask of a GeoJSON Polygon/MultiPolygon (lon/lat) on this grid."""
        to3857 = Transformer.from_crs(4326, 3857, always_xy=True)
        img = Image.new("1", (self.nx, self.ny), 0)
        draw = ImageDraw.Draw(img)
        polys = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
        for poly in polys:
            for i, ring in enumerate(poly):
                lon, lat = zip(*[(p[0], p[1]) for p in ring])
                mx, my = to3857.transform(lon, lat)
                px = (np.asarray(mx) - (self.x[0] - self.pixel / 2)) / self.pixel
                py = ((self.y[0] + self.pixel / 2) - np.asarray(my)) / self.pixel
                draw.polygon(list(zip(px, py)), fill=1 if i == 0 else 0)
        return np.array(img, dtype=bool)


# --------------------------------------------------------------------------- HDF5 helpers
def find_group(h5, suffix):
    """Return the first group path ending with `suffix` (e.g. 'GCOV/grids/frequencyA')."""
    hits = []
    h5.visititems(lambda name, obj: hits.append(name) if isinstance(obj, h5py.Group) and name.endswith(suffix) else None)
    return hits[0] if hits else None


def find_datasets(h5, pattern):
    rx = re.compile(pattern)
    hits = []
    h5.visititems(lambda name, obj: hits.append(name) if isinstance(obj, h5py.Dataset) and rx.search(name) else None)
    return hits


def read_epsg(group):
    """NISAR L2 grids store the EPSG code in a 'projection' dataset (value and/or attributes)."""
    if "projection" in group:
        ds = group["projection"]
        for k in ("epsg_code", "epsg"):
            if k in ds.attrs:
                return int(np.array(ds.attrs[k]).ravel()[0])
        try:
            v = int(np.array(ds[()]).ravel()[0])
            if v > 1000:
                return v
        except (TypeError, ValueError):
            pass
        for k, v in ds.attrs.items():
            m = re.search(r"EPSG\D*(\d{4,5})", str(v))
            if m:
                return int(m.group(1))
    raise ValueError(f"Could not find EPSG code in {group.name}/projection; pass --epsg")


def aoi_window(xc, yc, epsg, bbox=config.AOI_BBOX, pad_px=5):
    """Row/col slices of a source grid that cover the AOI (so we only read a subset from disk)."""
    w, s, e, n = bbox
    lon = np.r_[np.linspace(w, e, 20), np.full(20, e), np.linspace(e, w, 20), np.full(20, w)]
    lat = np.r_[np.full(20, s), np.linspace(s, n, 20), np.full(20, n), np.linspace(n, s, 20)]
    X, Y = Transformer.from_crs(4326, epsg, always_xy=True).transform(lon, lat)
    cols = np.where((xc >= X.min()) & (xc <= X.max()))[0]
    rows = np.where((yc >= Y.min()) & (yc <= Y.max()))[0]
    if len(cols) == 0 or len(rows) == 0:
        return None
    c0, c1 = max(cols[0] - pad_px, 0), min(cols[-1] + pad_px + 1, len(xc))
    r0, r1 = max(rows[0] - pad_px, 0), min(rows[-1] + pad_px + 1, len(yc))
    return slice(r0, r1), slice(c0, c1)


def read_time(h5, fallback_name=""):
    for p in find_datasets(h5, r"identification/zeroDopplerStartTime$"):
        v = h5[p][()]
        if isinstance(v, np.ndarray):
            v = v.ravel()[0]
        if isinstance(v, bytes):
            v = v.decode()
        return str(v).strip().replace(" ", "T")[:19]
    m = re.search(r"(20\d{6})T?(\d{6})?", fallback_name)
    if m:
        return datetime.strptime(m.group(1), "%Y%m%d").strftime("%Y-%m-%dT00:00:00")
    return "unknown"


# --------------------------------------------------------------------------- image helpers
def boxcar(a, k=config.BOXCAR):
    """NaN-aware mean filter (k x k)."""
    if k <= 1:
        return a
    v = np.where(np.isfinite(a), a, 0.0).astype(np.float64)
    c = np.isfinite(a).astype(np.float64)
    pad = k // 2

    def csum(x):
        x = np.pad(x, pad + 1, mode="constant")[1:, 1:]
        s = x.cumsum(0).cumsum(1)
        return s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]

    with np.errstate(invalid="ignore", divide="ignore"):
        out = csum(v) / csum(c)
    out[~np.isfinite(a)] = np.nan
    return out.astype(np.float32)


def to_db(p):
    with np.errstate(divide="ignore", invalid="ignore"):
        d = 10 * np.log10(np.where(p > 0, p, np.nan))
    return d.astype(np.float32)


def stretch(a, lo, hi):
    return np.clip((a - lo) / (hi - lo), 0, 1)


def ramp(t, stops):
    """Map t in [0,1] through colour stops [(pos, (r,g,b)), ...] -> uint8 RGB."""
    pos = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], dtype=np.float32)
    t = np.nan_to_num(t, nan=0.0)
    rgb = np.stack([np.interp(t, pos, cols[:, i]) for i in range(3)], axis=-1)
    return rgb.astype(np.uint8)


DIVERGING = [(0.0, (33, 102, 172)), (0.5, (247, 247, 247)), (1.0, (178, 24, 43))]   # blue - white - red
GREYS = [(0.0, (0, 0, 0)), (1.0, (255, 255, 255))]
COHERENCE = [(0.0, (20, 20, 40)), (0.5, (120, 90, 160)), (1.0, (250, 240, 200))]


def save_rgba(path, rgb, alpha):
    """Save RGBA; .webp (default in the pipeline) is ~10x smaller than PNG for these layers."""
    a = (np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    img = Image.fromarray(np.dstack([rgb, a]), "RGBA")
    if str(path).endswith(".webp"):
        img.save(path, quality=82, method=4)
    else:
        img.save(path, optimize=True)


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, default=lambda o: float(o) if isinstance(o, np.floating) else str(o)))
