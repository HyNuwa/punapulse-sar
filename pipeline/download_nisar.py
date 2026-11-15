# SI disclosure: drafted with assistance from Claude (Anthropic); reviewed by the PunaPulse SAR team.
"""Download the selected NISAR products (needs a free NASA Earthdata account).

Auth (first one found is used):
    EARTHDATA_TOKEN=...                       (recommended: urs.earthdata.nasa.gov -> Generate Token)
    EARTHDATA_USERNAME=... EARTHDATA_PASSWORD=...

Usage:
    python -m pipeline.download_nisar                 # GCOV selection
    python -m pipeline.download_nisar --product GUNW --limit 1
"""
import argparse
import json
import os

import asf_search as asf

from . import config


def session_from_env():
    s = asf.ASFSession()
    token = os.environ.get("EARTHDATA_TOKEN")
    user, pwd = os.environ.get("EARTHDATA_USERNAME"), os.environ.get("EARTHDATA_PASSWORD")
    if token:
        return s.auth_with_token(token)
    if user and pwd:
        return s.auth_with_creds(user, pwd)
    raise SystemExit("Set EARTHDATA_TOKEN (or EARTHDATA_USERNAME and EARTHDATA_PASSWORD) first.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--product", choices=["GCOV", "GUNW"], default="GCOV")
    ap.add_argument("--limit", type=int, default=None, help="download only the N most recent selected files")
    ap.add_argument("--processes", type=int, default=2)
    args = ap.parse_args()

    sel_path = config.RAW_DIR / f"selected_{args.product.lower()}.json"
    if not sel_path.exists():
        raise SystemExit(f"{sel_path} not found. Run: python -m pipeline.search_nisar --product {args.product}")
    scenes = json.loads(sel_path.read_text())["scenes"]
    if args.limit:
        scenes = scenes[-args.limit:]

    out = config.RAW_DIR / args.product.lower()
    out.mkdir(parents=True, exist_ok=True)
    todo = [s["url"] for s in scenes if s.get("url") and not (out / os.path.basename(s["url"])).exists()]
    print(f"{len(scenes)} selected, {len(todo)} to download into {out}")
    if todo:
        asf.download_urls(urls=todo, path=str(out), session=session_from_env(), processes=args.processes)
    print("Done. Files:")
    for f in sorted(out.glob("*.h5")):
        print(f"  {f.name}  {f.stat().st_size/1e9:.2f} GB")


if __name__ == "__main__":
    main()
