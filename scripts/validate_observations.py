
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flyway import simulate  # noqa: E402
from flyway.sources import pipeline  # noqa: E402
from flyway.sources.http import http_get  # noqa: E402
from flyway.species_data import SPECIES  # noqa: E402

HALVES = (("2010,2016", "A"), ("2017,2024", "B"))


def _load(out: Path, sid: str):
    f = np.frombuffer((out / f"{sid}.frames.u8").read_bytes(), np.uint8).reshape(simulate.WEEKS, simulate.HEIGHT, simulate.WIDTH)
    a = json.loads((out / f"{sid}.analysis.json").read_text())
    return f.astype(float), a


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 3 or x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _crossings(c: np.ndarray):
    """Fractional week when the centroid latitude crosses its own mid-level going north, then going south."""
    if np.isnan(c).any() or np.ptp(c) < 3.0:        # resident or too little movement to time
        return float("nan"), float("nan")
    m = (c.max() + c.min()) / 2.0
    spring = autumn = float("nan")
    for w in range(1, len(c)):
        if np.isnan(spring) and c[w - 1] < m <= c[w]:
            spring = w - 1 + (m - c[w - 1]) / (c[w] - c[w - 1])
        elif not np.isnan(spring) and np.isnan(autumn) and c[w - 1] >= m > c[w]:
            autumn = w - 1 + (m - c[w - 1]) / (c[w] - c[w - 1])
    return spring, autumn


def compare(fa, aa, fb, ab) -> dict:
    mask = (fa.sum(0) > 0) & (fb.sum(0) > 0)                       # cells with data in both halves
    weekly = [_pearson(fa[w][mask], fb[w][mask]) for w in range(fa.shape[0])]
    # seasonal-change agreement: remove each cell's own yearly mean, so the fixed range outline does not count
    da = (fa - fa.mean(0))[:, mask].ravel()
    db = (fb - fb.mean(0))[:, mask].ravel()
    ca = np.array([np.nan if v is None else v for v in aa["centroid_lat"]], float)
    cb = np.array([np.nan if v is None else v for v in ab["centroid_lat"]], float)
    ok = ~np.isnan(ca) & ~np.isnan(cb)
    sa, aa_ = _crossings(ca)
    sb, ab_ = _crossings(cb)
    return {
        "cells": int(mask.sum()),
        "map_r_mean": float(np.nanmean(weekly)),
        "map_r_min": float(np.nanmin(weekly)),
        "change_r": _pearson(da, db),
        "centroid_mae_deg": float(np.mean(np.abs(ca[ok] - cb[ok]))),
        "spring_diff": abs(sa - sb),
        "autumn_diff": abs(aa_ - ab_),
    }


def run(http, species_ids, cell, workers, out_md: Path) -> list[dict]:
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        outs = {}
        for years, tag in HALVES:
            outs[tag] = Path(tmp) / tag
            print(f"== records from {years} ==")
            pipeline.fetch_observations(http, species_ids, cell=cell, workers=workers, year_range=years,
                                        out_dir=outs[tag], cache_dir=pipeline.DATA_DIR / "cache_gbif")
        for spec in SPECIES:
            if species_ids and spec["id"] not in species_ids:
                continue
            (fa, aa), (fb, ab) = _load(outs["A"], spec["id"]), _load(outs["B"], spec["id"])
            m = compare(fa, aa, fb, ab)
            rows.append({"species": spec["common"], **m})
    fmt = lambda v: 'n/a' if np.isnan(v) else f'{v:.1f}'  # noqa: E731
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        "# Validation: split-half stability of the observed maps", "",
        f"Generated {today}. Cells of {cell} degrees. Half A uses records from 2010 to 2016, half B from 2017 to 2024.", "",
        "| Species | Cells in both | Map correlation (mean of 52 weeks) | Weakest week | Seasonal-change correlation | Centroid latitude difference (deg) | Spring timing difference (weeks) | Autumn timing difference (weeks) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(f"| {r['species']} | {r['cells']} | {r['map_r_mean']:.2f} | {r['map_r_min']:.2f} | {r['change_r']:.2f} | "
                     f"{r['centroid_mae_deg']:.1f} | {fmt(r['spring_diff'])} | {fmt(r['autumn_diff'])} |")
    lines += ["", "**How to read this.** Map correlation compares the two halves cell by cell and week by week, but is helped by the fixed "
              "range outline. Seasonal-change correlation removes each cell's own yearly mean, so it only credits agreement about how "
              "birds move. Timing difference is the gap between the halves in the week the population's average latitude crosses its "
              "mid-level, going north (spring) and south (autumn); n/a means the species moves too little to time. "
              "Values near 1 (and small gaps) mean the pattern does not depend on which years were used, so the method is reproducible. "
              "This tests stability, not accuracy: both halves share the same biases "
              "(where and when people watch birds). Accuracy needs an independent reference, listed in `docs/REFERENCES.md`.", ""]
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="5 degree cells")
    ap.add_argument("--cell", type=float, default=3.0)
    ap.add_argument("--species", help="comma separated ids")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    ids = [s.strip() for s in a.species.split(",")] if a.species else None
    try:
        run(http_get, ids, 5.0 if a.quick else a.cell, a.workers, Path(__file__).resolve().parent.parent / "docs" / "VALIDATION.md")
    except RuntimeError as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
