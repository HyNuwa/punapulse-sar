# SI disclosure: drafted with assistance from Claude (Anthropic); reviewed by the PunaPulse SAR team.
"""Search the ASF archive for NISAR products over the AOI and pick a consistent stack.

Usage:
    python -m pipeline.search_nisar                      # GCOV, all dates
    python -m pipeline.search_nisar --product GUNW       # interferograms
    python -m pipeline.search_nisar --start 2026-06-01 --max-scenes 6

Searching does NOT need an Earthdata login. Results are written to data/raw/.
"""
import argparse
import json
from collections import Counter

import asf_search as asf

from . import config

COLLECTIONS = {
    "GCOV": {"VALIDATED": "NISAR_L2_GCOV_V1", "PROVISIONAL": "NISAR_L2_GCOV_PROVISIONAL_V1", "BETA": "NISAR_L2_GCOV_BETA_V1"},
    "GUNW": {"VALIDATED": "NISAR_L2_GUNW_V1", "PROVISIONAL": "NISAR_L2_GUNW_PROVISIONAL_V1", "BETA": "NISAR_L2_GUNW_BETA_V1"},
}


def maturity_of(collection_name: str) -> str:
    if not collection_name:
        return "UNKNOWN"
    if "BETA" in collection_name:
        return "BETA"
    if "PROVISIONAL" in collection_name:
        return "PROVISIONAL"
    return "VALIDATED"


def bbox_wkt(b):
    w, s, e, n = b
    return f"POLYGON(({w} {s},{e} {s},{e} {n},{w} {n},{w} {s}))"


def search(product, start=None, end=None, bbox=config.AOI_BBOX):
    short_names = list(COLLECTIONS[product].values())
    opts = dict(shortName=short_names, intersectsWith=bbox_wkt(bbox))
    if start:
        opts["start"] = start
    if end:
        opts["end"] = end
    results = asf.search(**opts)
    rows = []
    for r in results:
        p = r.properties
        url = p.get("url") or ""
        if not url.endswith(".h5"):
            h5 = [u for u in (p.get("additionalUrls") or []) if u.endswith(".h5")]
            url = h5[0] if h5 else url
        size = 0
        for v in (p.get("bytes") or {}).values():
            if isinstance(v, dict):
                size += v.get("bytes") or 0
        rows.append({
            "scene": p.get("sceneName") or p.get("fileID"),
            "start": p.get("startTime"),
            "stop": p.get("stopTime"),
            "track": p.get("pathNumber"),
            "frame": p.get("frameNumber"),
            "direction": p.get("flightDirection"),
            "collection": p.get("collectionName"),
            "maturity": maturity_of(p.get("collectionName")),
            "polarization": p.get("mainBandPolarization"),
            "full_frame": p.get("frameCoverage"),
            "size_mb": round(size / 1e6, 1) if size else None,
            "url": url,
            "browse": (p.get("browse") or [None])[0],
        })
    rows.sort(key=lambda r: r["start"] or "")
    return rows


def pick_stack(rows, max_scenes):
    """Pick one maturity level and one track/direction so dates are comparable."""
    if not rows:
        return [], None

    def best_stack(level_rows):
        groups = Counter((r["track"], r["direction"]) for r in level_rows)
        (track, direction), _ = groups.most_common(1)[0]
        stack = [r for r in level_rows if r["track"] == track and r["direction"] == direction]
        seen, uniq = set(), []          # one product per acquisition date
        for r in stack:
            d = (r["start"] or "")[:10]
            if d not in seen:
                seen.add(d)
                uniq.append(r)
        return uniq, track, direction

    candidates = []
    for level in [*config.MATURITY_PREFERENCE, "UNKNOWN"]:
        level_rows = [r for r in rows if r["maturity"] == level]
        if level_rows:
            stack, track, direction = best_stack(level_rows)
            candidates.append((level, stack, track, direction))
    # first maturity level (in preference order) that has >= 2 comparable dates, else the longest stack
    chosen = next((c for c in candidates if len(c[1]) >= 2), max(candidates, key=lambda c: len(c[1])))
    level, stack, track, direction = chosen
    return stack[-max_scenes:], {"maturity": level, "track": track, "direction": direction,
                                 "comparable_dates_available": len(stack)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--product", choices=list(COLLECTIONS), default="GCOV")
    ap.add_argument("--start", help="YYYY-MM-DD")
    ap.add_argument("--end", help="YYYY-MM-DD")
    ap.add_argument("--max-scenes", type=int, default=6, help="max dates to keep in the selected stack")
    args = ap.parse_args()

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows = search(args.product, args.start, args.end)
    all_path = config.RAW_DIR / f"search_{args.product.lower()}.json"
    all_path.write_text(json.dumps(rows, indent=2))

    print(f"\n{len(rows)} NISAR {args.product} products intersect {config.AOI_NAME} {config.AOI_BBOX}\n")
    print(f"{'date':<11} {'maturity':<12} {'track':>5} {'frame':>5} {'dir':<11} {'pol':<10} {'MB':>8}  scene")
    for r in rows:
        print(f"{(r['start'] or '')[:10]:<11} {r['maturity']:<12} {str(r['track']):>5} {str(r['frame']):>5} "
              f"{str(r['direction']):<11} {str(r['polarization']):<10} {str(r['size_mb']):>8}  {r['scene']}")

    if args.product == "GUNW":
        sel = rows[-args.max_scenes:]
        info = {"note": "GUNW pairs are listed as found; choose pairs from the same track."}
    else:
        sel, info = pick_stack(rows, args.max_scenes)
    sel_path = config.RAW_DIR / f"selected_{args.product.lower()}.json"
    sel_path.write_text(json.dumps({"info": info, "scenes": sel}, indent=2))
    print(f"\nSelected {len(sel)} products -> {sel_path}")
    if info:
        print(f"Selection: {info}")
    if args.product == "GCOV" and len(sel) < 2:
        print("\nWARNING: fewer than 2 comparable dates. Change detection needs >= 2. "
              "Try a wider date range, another maturity level, or a nearby AOI.")
    total = sum(r["size_mb"] or 0 for r in sel)
    if total:
        print(f"Total download size: ~{total/1000:.1f} GB")


if __name__ == "__main__":
    main()
