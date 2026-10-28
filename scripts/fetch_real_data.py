"""Download REAL data for Flyway. Run this on your own computer (it needs internet).

    python scripts/fetch_real_data.py check            # which services can I reach?
    python scripts/fetch_real_data.py coast            # Natural Earth coastlines (public domain)
    python scripts/fetch_real_data.py imagery          # NASA monthly Earth imagery (Blue Marble, NDVI if offered)
    python scripts/fetch_real_data.py goes             # NASA/NOAA GOES-East satellite frames for the opening scene
    python scripts/fetch_real_data.py observations     # GBIF/eBird bird records -> weekly maps (20-60 min)
    python scripts/fetch_real_data.py all              # everything above
    python scripts/fetch_real_data.py layers goes      # list NASA layers whose name contains 'goes'

Useful options:
    observations --quick           5-degree cells, finishes in a few minutes
    observations --species wood-thrush,western-tanager
    goes --track flyway/data/tracks/hawk.csv     align the satellite window to a real Movebank GPS file
Nothing is hard to undo: delete flyway/cache/real, static/img/real or flyway/data/ne_*.geojson to go back.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flyway.sources import gibs, pipeline  # noqa: E402
from flyway.sources.gbif import API  # noqa: E402
from flyway.sources.http import http_get  # noqa: E402
from flyway.tracks import load_movebank_csv  # noqa: E402


def cmd_check(_a) -> int:
    tests = {
        "Natural Earth (GitHub)": pipeline.NE_BASE + "ne_110m_land.geojson",
        "NASA GIBS": gibs.capabilities_url(),
        "GBIF": f"{API}/species/match?name=Aves&rank=CLASS",
    }
    bad = 0
    for name, url in tests.items():
        try:
            n = len(http_get(url, timeout=60, retries=2))
            print(f"  OK    {name}  ({n // 1024} KB)")
        except Exception as exc:  # noqa: BLE001
            bad += 1
            print(f"  FAIL  {name}: {exc}")
    return 1 if bad else 0


def cmd_layers(a) -> int:
    layers = gibs.parse_layers(http_get(gibs.capabilities_url()))
    toks = [t.lower() for t in a.words]
    for name in sorted(layers):
        if all(t in name.lower() for t in toks):
            ext = layers[name]["time"]
            span = f"{ext[0][0]:%Y-%m-%d} to {ext[-1][1]:%Y-%m-%d} ({ext[-1][2]})" if ext else "no time dimension"
            print(f"  {name}   {span}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check"); sub.add_parser("coast")
    p = sub.add_parser("imagery"); p.add_argument("--res", type=float, default=0.12, help="degrees per pixel")
    p = sub.add_parser("goes")
    p.add_argument("--days", type=int, default=4); p.add_argument("--step-hours", type=int, default=2)
    p.add_argument("--track", help="Movebank CSV to align the window to")
    p = sub.add_parser("observations")
    p.add_argument("--cell", type=float, default=3.0); p.add_argument("--quick", action="store_true")
    p.add_argument("--species", help="comma separated ids"); p.add_argument("--workers", type=int, default=3)
    p.add_argument("--years", default="2010,2024")
    p = sub.add_parser("all"); p.add_argument("--quick", action="store_true")
    p = sub.add_parser("layers"); p.add_argument("words", nargs="*")
    a = ap.parse_args()

    try:
        if a.cmd == "check":
            return cmd_check(a)
        if a.cmd == "layers":
            return cmd_layers(a)
        if a.cmd in ("coast", "all"):
            print("Coastlines"); pipeline.fetch_coast(http_get)
        if a.cmd in ("imagery", "all"):
            print("Monthly imagery (NASA GIBS)"); pipeline.fetch_imagery(http_get, getattr(a, "res", 0.12))
        if a.cmd in ("goes", "all"):
            print("Opening-scene satellite frames (GOES-East via NASA GIBS)")
            track = load_movebank_csv(a.track) if getattr(a, "track", None) else None
            pipeline.fetch_goes(http_get, getattr(a, "days", 4), getattr(a, "step_hours", 2), track=track)
        if a.cmd in ("observations", "all"):
            print("Bird observations (GBIF)")
            quick = getattr(a, "quick", False)
            ids = [s.strip() for s in a.species.split(",")] if getattr(a, "species", None) else None
            pipeline.fetch_observations(http_get, ids, 5.0 if quick else getattr(a, "cell", 3.0),
                                        getattr(a, "workers", 3), getattr(a, "years", "2010,2024"))
    except RuntimeError as exc:
        print(f"\nStopped: {exc}", file=sys.stderr)
        return 1
    print("\nDone. Restart the server (python run.py) and hard-refresh the page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
