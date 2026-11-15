# SI disclosure: drafted with assistance from Claude (Anthropic); reviewed by the PunaPulse SAR team.
"""TEST FIXTURE ONLY - writes small synthetic HDF5 files shaped like NISAR GCOV/GUNW products.

They exist only to check that the pipeline code runs end to end. They are NOT NISAR data and
their outputs must never be committed to docs/data/ or shown as results.

    python tests/make_fake_products.py tests/_out/raw
"""
import sys
from pathlib import Path

import h5py
import numpy as np
from pyproj import Transformer

EPSG = 32719  # UTM 19S, the zone NISAR would use over Olaroz-Cauchari


def grid():
    tr = Transformer.from_crs(4326, EPSG, always_xy=True)
    (x0, x1), (y0, y1) = tr.transform([-66.95, -66.45], [-23.85, -23.10])
    xc = np.arange(x0, x1, 20.0)
    yc = np.arange(y1, y0, -20.0)
    return xc, yc


def ponds(xc, yc, grow):
    X, Y = np.meshgrid(xc, yc)
    tr = Transformer.from_crs(4326, EPSG, always_xy=True)
    cx, cy = tr.transform(-66.72, -23.42)
    m = (np.abs(X - cx) < 1500 + grow) & (np.abs(Y - cy) < 800)
    return m


def gcov(path, date, grow, seed):
    rng = np.random.default_rng(seed)
    xc, yc = grid()
    shape = (len(yc), len(xc))
    hh = 10 ** (rng.normal(-12, 2.5, shape) / 10)
    hv = 10 ** (rng.normal(-20, 2.5, shape) / 10)
    p = ponds(xc, yc, grow)
    hh[p] = 10 ** (-26 / 10)
    hv[p] = 10 ** (-33 / 10)
    with h5py.File(path, "w") as h:
        g = h.create_group("science/LSAR/GCOV/grids/frequencyA")
        g["HHHH"], g["HVHV"] = hh.astype("f4"), hv.astype("f4")
        g["xCoordinates"], g["yCoordinates"] = xc, yc
        g["projection"] = np.uint32(EPSG)
        g["projection"].attrs["epsg_code"] = EPSG
        h["science/LSAR/identification/zeroDopplerStartTime"] = np.bytes_(f"{date}T10:15:30.000000")


def gunw(path):
    rng = np.random.default_rng(7)
    xc, yc = grid()
    xc, yc = xc[::4], yc[::4]
    X, Y = np.meshgrid(xc, yc)
    ph = 0.8 * np.sin(X / 3000) + rng.normal(0, 0.2, X.shape)
    co = np.clip(rng.normal(0.7, 0.1, X.shape), 0, 1)
    with h5py.File(path, "w") as h:
        base = h.create_group("science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram")
        base["xCoordinates"], base["yCoordinates"] = xc, yc
        base["projection"] = np.uint32(EPSG)
        hh = base.create_group("HH")
        hh["unwrappedPhase"], hh["coherenceMagnitude"] = ph.astype("f4"), co.astype("f4")


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "tests/_out/raw")
    (out / "gcov").mkdir(parents=True, exist_ok=True)
    (out / "gunw").mkdir(parents=True, exist_ok=True)
    for i, (d, g) in enumerate([("2026-10-21", 0), ("2026-11-02", 600), ("2026-11-14", 1200)]):
        gcov(out / "gcov" / f"FAKE_TEST_GCOV_{d.replace('-', '')}.h5", d, g, i)
    gunw(out / "gunw" / "FAKE_TEST_GUNW_20261102T101530_20261114T101530.h5")
    print("fake products written to", out)
