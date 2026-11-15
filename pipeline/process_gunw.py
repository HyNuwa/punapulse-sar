# SI disclosure: drafted with assistance from Claude (Anthropic); reviewed by the PunaPulse SAR team.
"""EXPLORATORY: turn a NISAR L2 GUNW (geocoded unwrapped interferogram) into web layers.

Writes (docs/data/):
  ifg_phase_<ref>_<sec>.webp  unwrapped phase relative to the AOI median, blue/red   (Observed, relative)
  ifg_coh_<ref>_<sec>.webp    coherence magnitude 0..1                               (Observed)

Scientific boundary (shown in the app, keep it in your pitch):
  * One pair = one ~12-day snapshot of line-of-sight (LOS) change. It is NOT a subsidence rate.
  * Tropospheric delay over the Andes can easily exceed mm-level deformation signals in a single pair.
  * One full colour cycle of 2*pi rad corresponds to ~wavelength/2 = ~11.9 cm of LOS change at L-band.
  * Low coherence (dark) = phase is unreliable there (e.g. pond water, wet vegas, moving surfaces).

Usage:
    python -m pipeline.process_gunw                    # files in data/raw/gunw/
    python -m pipeline.process_gunw --files x.h5 --pol HH
"""
import argparse
import re
from pathlib import Path

import h5py
import numpy as np

from . import config, geo, manifest


def pick(h5, pattern, pol):
    hits = geo.find_datasets(h5, pattern)
    pref = [h for h in hits if "frequencyA" in h and f"/{pol}/" in h]
    return (pref or hits or [None])[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", nargs="*", type=Path)
    ap.add_argument("--pol", default="HH")
    ap.add_argument("--epsg", type=int, default=None)
    args = ap.parse_args()

    files = args.files or sorted((config.RAW_DIR / "gunw").glob("*.h5"))
    if not files:
        raise SystemExit("No GUNW .h5 files. Run: search_nisar --product GUNW, then download_nisar --product GUNW --limit 1")
    grid = geo.WebGrid()
    out = config.WEB_DATA_DIR
    ifgs = []
    for f in files:
        with h5py.File(f, "r") as h5:
            ph_path = pick(h5, r"unwrappedInterferogram/.*/unwrappedPhase$", args.pol)
            co_path = pick(h5, r"unwrappedInterferogram/.*/coherenceMagnitude$", args.pol)
            if not ph_path:
                print(f"  SKIP {f.name}: no unwrappedPhase dataset")
                continue
            g = h5[ph_path.rsplit("/", 2)[0]]  # .../unwrappedInterferogram
            while "xCoordinates" not in g and g.name != "/":
                g = g.parent
            epsg = args.epsg or geo.read_epsg(g)
            xc, yc = g["xCoordinates"][()], g["yCoordinates"][()]
            win = geo.aoi_window(xc, yc, epsg)
            if win is None:
                print(f"  SKIP {f.name}: does not overlap AOI")
                continue
            rs, cs = win
            ph = h5[ph_path][rs, cs].astype(np.float32)
            co = h5[co_path][rs, cs].astype(np.float32) if co_path else None
            dates = re.findall(r"(20\d{6})T\d{6}", f.name)
        ph[~np.isfinite(ph) | (ph == 0)] = np.nan
        phw = grid.regrid(ph, epsg, xc[cs], yc[rs])
        ref, sec = (dates + ["ref", "sec"])[:2] if len(dates) >= 2 else ("ref", "sec")
        tag = f"{ref}_{sec}"
        valid = np.isfinite(phw)
        rel = phw - np.nanmedian(phw)
        lim = float(np.nanpercentile(np.abs(rel), 98)) or np.pi
        geo.save_rgba(out / f"ifg_phase_{tag}.webp", geo.ramp(geo.stretch(rel, -lim, lim), geo.DIVERGING), valid * 0.9)
        entry = {"ref": ref, "sec": sec, "file": f.name, "phase": f"data/ifg_phase_{tag}.webp",
                 "phase_range_rad": [-lim, lim],
                 "los_cm_per_cycle": round(config.NISAR_L_WAVELENGTH_M / 2 * 100, 1)}
        if co is not None:
            cow = grid.regrid(co, epsg, xc[cs], yc[rs])
            geo.save_rgba(out / f"ifg_coh_{tag}.webp", geo.ramp(np.clip(cow, 0, 1), geo.COHERENCE), np.isfinite(cow) * 0.9)
            entry["coherence"] = f"data/ifg_coh_{tag}.webp"
            entry["mean_coherence"] = round(float(np.nanmean(cow)), 3)
        ifgs.append(entry)
        print(f"  {tag}: phase range +/-{lim:.2f} rad, mean coherence {entry.get('mean_coherence')}")

    m = manifest.load()
    m.setdefault("bounds", grid.leaflet_bounds())
    m["interferograms"] = ifgs
    manifest.save(m)
    print(f"{len(ifgs)} interferogram(s) -> manifest.json")


if __name__ == "__main__":
    main()
