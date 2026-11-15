# SI disclosure: drafted with assistance from Claude (Anthropic); reviewed by the PunaPulse SAR team.
"""Fetch daily precipitation for the AOI centre from NASA POWER and aggregate it to months.

NASA POWER (power.larc.nasa.gov) needs no login. Parameter PRECTOTCORR = bias-corrected total
precipitation (mm/day). It is a coarse (~0.5 deg) product: use it as climate context only.

Usage:
    python -m pipeline.fetch_precip --start 2025-01-01
"""
import argparse
from collections import defaultdict
from datetime import date, timedelta

import requests

from . import config, geo, manifest

API = "https://power.larc.nasa.gov/api/temporal/daily/point"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="2025-01-01")
    ap.add_argument("--end", default=(date.today() - timedelta(days=3)).isoformat())
    args = ap.parse_args()

    lat, lon = config.AOI_CENTER
    params = {"parameters": "PRECTOTCORR", "community": "AG", "latitude": lat, "longitude": lon,
              "start": args.start.replace("-", ""), "end": args.end.replace("-", ""), "format": "JSON"}
    r = requests.get(API, params=params, timeout=120)
    r.raise_for_status()
    daily = r.json()["properties"]["parameter"]["PRECTOTCORR"]
    monthly, days = defaultdict(float), defaultdict(int)
    for k, v in daily.items():
        if v is None or v < 0:  # -999 = missing
            continue
        monthly[f"{k[:4]}-{k[4:6]}"] += v
        days[f"{k[:4]}-{k[4:6]}"] += 1
    months = [{"month": k, "precip_mm": round(monthly[k], 1), "days": days[k]} for k in sorted(monthly)]
    out = {"source": "NASA POWER daily PRECTOTCORR (MERRA-2 based, ~0.5 deg)", "lat": lat, "lon": lon,
           "start": args.start, "end": args.end, "monthly": months}
    config.WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    geo.write_json(config.WEB_DATA_DIR / "precip.json", out)
    m = manifest.load()
    m["precip"] = "data/precip.json"
    manifest.save(m)
    total = sum(x["precip_mm"] for x in months)
    print(f"{len(months)} months, {total:.0f} mm total -> docs/data/precip.json")


if __name__ == "__main__":
    main()
