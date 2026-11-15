# SI disclosure: drafted with assistance from Claude (Anthropic); reviewed by the PunaPulse SAR team.
"""Turn downloaded NISAR L2 GCOV files into web layers + statistics for the AOI.

For every date it writes (into docs/data/):
  rgb_<date>.webp   dual-pol colour composite  R=HH  G=HV  B=HH/HV           (Observed)
  hh_<date>.webp    HH backscatter in dB, greyscale                          (Observed)
  dark_<date>.webp  low-backscatter surface: candidate brine ponds / water   (Derived)
For consecutive date pairs and first->last:
  change_<d1>_<d2>.webp 10*log10(after/before) of HH, |change| < CHANGE_DB hidden  (Derived)
and statistics (hectares, mean dB) for the whole AOI and every zone in docs/data/zones.geojson.

Usage:
    python -m pipeline.process_gcov                       # files in data/raw/gcov/
    python -m pipeline.process_gcov --files a.h5 b.h5 --dark-db -19
"""
import argparse
import json
from pathlib import Path

import h5py
import numpy as np

from . import config, geo, manifest


def load_meta():
    p = config.RAW_DIR / "selected_gcov.json"
    if not p.exists():
        return {}
    return {Path(s["url"]).name: s for s in json.loads(p.read_text())["scenes"] if s.get("url")}


def read_gcov(path, grid, epsg_override=None):
    with h5py.File(path, "r") as h5:
        gpath = geo.find_group(h5, "GCOV/grids/frequencyA")
        if gpath is None:
            raise ValueError(f"{path.name}: no GCOV/grids/frequencyA group (is this a GCOV file?)")
        g = h5[gpath]
        epsg = epsg_override or geo.read_epsg(g)
        xc, yc = g["xCoordinates"][()], g["yCoordinates"][()]
        win = geo.aoi_window(xc, yc, epsg)
        if win is None:
            raise ValueError(f"{path.name}: frame does not overlap the AOI")
        rs, cs = win
        bands = {}
        for pol in ("HHHH", "HVHV", "VVVV", "VHVH"):
            if pol in g:
                sub = g[pol][rs, cs].astype(np.float32)
                sub[~np.isfinite(sub) | (sub <= 0)] = np.nan
                bands[pol] = geo.boxcar(grid.regrid(sub, epsg, xc[cs], yc[rs]))
        when = geo.read_time(h5, path.name)
    return when, bands, epsg


def zone_stats(grid, zones, hh_db, hv_db, dark):
    out = {}
    for name, mask in zones.items():
        m = mask & np.isfinite(hh_db)
        out[name] = {
            "valid_ha": round(grid.area_ha(m), 1),
            "mean_hh_db": round(float(np.nanmean(hh_db[m])), 2) if m.any() else None,
            "mean_hv_db": round(float(np.nanmean(hv_db[m])), 2) if (hv_db is not None and m.any()) else None,
            "dark_ha": round(grid.area_ha(dark & m), 1),
        }
    return out


def load_zones(grid):
    zones = {"Whole AOI": np.ones((grid.ny, grid.nx), bool)}
    p = config.WEB_DATA_DIR / "zones.geojson"
    if p.exists():
        for i, f in enumerate(json.loads(p.read_text()).get("features", [])):
            name = (f.get("properties") or {}).get("name") or f"zone {i+1}"
            if f.get("geometry") and f["geometry"]["type"] in ("Polygon", "MultiPolygon"):
                zones[name] = grid.rasterize_geojson(f["geometry"])
    return zones


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", nargs="*", type=Path)
    ap.add_argument("--dark-db", type=float, default=config.DARK_HH_DB)
    ap.add_argument("--change-db", type=float, default=config.CHANGE_DB)
    ap.add_argument("--epsg", type=int, default=None, help="override EPSG if it cannot be read from the file")
    args = ap.parse_args()

    files = args.files or sorted((config.RAW_DIR / "gcov").glob("*.h5"))
    if not files:
        raise SystemExit("No GCOV .h5 files found. Run search_nisar + download_nisar first.")
    out = config.WEB_DATA_DIR
    out.mkdir(parents=True, exist_ok=True)
    grid = geo.WebGrid()
    zones = load_zones(grid)
    meta = load_meta()
    print(f"Output grid {grid.nx} x {grid.ny} px at {grid.pixel} m (EPSG:3857); zones: {list(zones)}")

    scenes, arrays = [], {}
    for f in files:
        try:
            when, bands, epsg = read_gcov(f, grid, args.epsg)
        except Exception as e:  # keep going with the other dates
            print(f"  SKIP {f.name}: {e}")
            continue
        if "HHHH" not in bands:
            print(f"  SKIP {f.name}: no HHHH band (polarizations: {list(bands)})")
            continue
        date = when[:10]
        tag = date if date not in arrays else f"{date}_{len(arrays)}"
        hh_db = geo.to_db(bands["HHHH"])
        hv_db = geo.to_db(bands["HVHV"]) if "HVHV" in bands else None
        valid = np.isfinite(hh_db)
        dark = valid & (hh_db < args.dark_db)

        # layers
        if hv_db is not None:
            rgb = np.dstack([
                geo.stretch(hh_db, *config.HH_DB_RANGE),
                geo.stretch(hv_db, *config.HV_DB_RANGE),
                geo.stretch(hh_db - hv_db, *config.RATIO_DB_RANGE),
            ])
            geo.save_rgba(out / f"rgb_{tag}.webp", (np.nan_to_num(rgb) * 255).astype(np.uint8), valid)
        g = geo.ramp(geo.stretch(hh_db, *config.HH_DB_RANGE), geo.GREYS)
        geo.save_rgba(out / f"hh_{tag}.webp", g, valid)
        blue = np.zeros((grid.ny, grid.nx, 3), np.uint8)
        blue[..., 0], blue[..., 1], blue[..., 2] = 30, 144, 255
        geo.save_rgba(out / f"dark_{tag}.webp", blue, dark * 0.75)

        m = meta.get(f.name, {})
        scenes.append({
            "id": tag, "date": date, "datetime": when, "file": f.name,
            "maturity": m.get("maturity", "UNKNOWN"), "track": m.get("track"), "frame": m.get("frame"),
            "direction": m.get("direction"), "epsg_source": epsg, "polarizations": sorted(bands),
            "layers": {k: f"data/{k}_{tag}.webp" for k in (["rgb"] if hv_db is not None else []) + ["hh", "dark"]},
            "stats": {
                "aoi_valid_ha": round(grid.area_ha(valid), 1),
                "dark_ha": round(grid.area_ha(dark), 1),
                "dark_threshold_db": args.dark_db,
                "zones": zone_stats(grid, zones, hh_db, hv_db, dark),
            },
        })
        arrays[tag] = (hh_db, dark)
        print(f"  {tag}: valid {scenes[-1]['stats']['aoi_valid_ha']:.0f} ha, dark {scenes[-1]['stats']['dark_ha']:.0f} ha")

    scenes.sort(key=lambda s: s["datetime"])
    maturities = {s["maturity"] for s in scenes}
    tracks = {(s["track"], s["direction"]) for s in scenes}
    warnings = []
    if len(maturities) > 1:
        warnings.append(f"Mixed data maturity levels {sorted(maturities)}: ASF advises against comparing them.")
    if len(tracks) > 1:
        warnings.append(f"Mixed tracks/directions {sorted(map(str, tracks))}: viewing geometry differs, change maps may show false change.")

    # change maps
    ids = [s["id"] for s in scenes]
    pairs = list(zip(ids[:-1], ids[1:]))
    if len(ids) > 2:
        pairs.append((ids[0], ids[-1]))
    changes = []
    for a, b in pairs:
        (ha, da), (hb, db) = arrays[a], arrays[b]
        d = hb - ha  # dB difference == 10 log10(after/before)
        both = np.isfinite(d)
        sig = both & (np.abs(d) >= args.change_db)
        rgb = geo.ramp(geo.stretch(d, -8, 8), geo.DIVERGING)
        geo.save_rgba(out / f"change_{a}_{b}.webp", rgb, sig * 0.85)
        changes.append({
            "from": a, "to": b, "layer": f"data/change_{a}_{b}.webp",
            "stats": {
                "compared_ha": round(grid.area_ha(both), 1),
                "increase_ha": round(grid.area_ha(both & (d >= args.change_db)), 1),
                "decrease_ha": round(grid.area_ha(both & (d <= -args.change_db)), 1),
                "new_dark_ha": round(grid.area_ha(both & db & ~da), 1),
                "lost_dark_ha": round(grid.area_ha(both & da & ~db), 1),
                "threshold_db": args.change_db,
            },
        })
        print(f"  change {a} -> {b}: +{changes[-1]['stats']['increase_ha']:.0f} ha / -{changes[-1]['stats']['decrease_ha']:.0f} ha; "
              f"new dark {changes[-1]['stats']['new_dark_ha']:.0f} ha")

    m = manifest.load()
    m.update({
        "bounds": grid.leaflet_bounds(),
        "grid": {"epsg": 3857, "pixel_m": grid.pixel, "nx": grid.nx, "ny": grid.ny, "boxcar": config.BOXCAR},
        "display": {"hh_db": config.HH_DB_RANGE, "hv_db": config.HV_DB_RANGE, "ratio_db": config.RATIO_DB_RANGE,
                    "change_db": [-8, 8]},
        "scenes": scenes, "changes": changes, "warnings": warnings,
    })
    manifest.save(m)
    print(f"\n{len(scenes)} dates, {len(changes)} change maps -> {out/'manifest.json'}")
    for w in warnings:
        print("WARNING:", w)


if __name__ == "__main__":
    main()
