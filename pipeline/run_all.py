# SI disclosure: drafted with assistance from Claude (Anthropic); reviewed by the PunaPulse SAR team.
"""One command for the whole pipeline (search -> download -> process -> precipitation).

    export EARTHDATA_TOKEN=...            # urs.earthdata.nasa.gov -> Generate Token
    python -m pipeline.run_all --max-scenes 4 --start 2026-06-01
    python -m pipeline.run_all --max-scenes 4 --with-gunw        # also one exploratory interferogram

Afterwards commit docs/data/ and open docs/index.html (or GitHub Pages).
"""
import argparse
import subprocess
import sys


def run(*a):
    print("\n$ python -m", " ".join(a), flush=True)
    subprocess.run([sys.executable, "-m", *a], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--max-scenes", default="4")
    ap.add_argument("--with-gunw", action="store_true")
    ap.add_argument("--skip-precip", action="store_true")
    a = ap.parse_args()
    window = (["--start", a.start] if a.start else []) + (["--end", a.end] if a.end else [])

    run("pipeline.search_nisar", "--product", "GCOV", "--max-scenes", a.max_scenes, *window)
    run("pipeline.download_nisar", "--product", "GCOV")
    run("pipeline.process_gcov")
    if a.with_gunw:
        run("pipeline.search_nisar", "--product", "GUNW", "--max-scenes", "1", *window)
        run("pipeline.download_nisar", "--product", "GUNW", "--limit", "1")
        run("pipeline.process_gunw")
    if not a.skip_precip:
        run("pipeline.fetch_precip", "--start", (a.start or "2025-01-01")[:10])
    print("\nAll done. Commit docs/data/ and refresh the web app.")


if __name__ == "__main__":
    main()
