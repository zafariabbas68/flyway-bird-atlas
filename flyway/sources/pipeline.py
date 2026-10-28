"""Download-and-convert steps for real data. Each function takes `http_get` so tests can mock it."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from .. import observed, simulate
from ..geo import haversine_km
from ..species_data import SPECIES
from . import gibs
from .gbif import Gbif, collect

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "flyway" / "data"
IMG_DIR = ROOT / "static" / "img" / "real"
REAL_DIR = simulate.CACHE_DIR / "real"
AMERICAS = (simulate.LON_MIN, simulate.LAT_MIN, simulate.LON_MAX, simulate.LAT_MAX)
HERO_BBOX = (-130.0, -10.0, -40.0, 48.0)   # 90 x 58 degrees, about the shape of a wide screen

NE_BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
NE_FILES = {
    "ne_land.geojson": "ne_50m_land.geojson",
    "ne_countries.geojson": "ne_50m_admin_0_boundary_lines_land.geojson",
    "ne_lakes.geojson": "ne_50m_lakes.geojson",
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def _manifest_update(**entries) -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    p = IMG_DIR / "manifest.json"
    try:
        m = json.loads(p.read_text())
    except (OSError, ValueError):
        m = {}
    m.update(entries)
    m["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    p.write_text(json.dumps(m, indent=1))


# ------------------------------------------------------------- coastlines
def _round(c, nd=3):
    return [_round(x, nd) for x in c] if isinstance(c[0], list) else [round(c[0], nd), round(c[1], nd)]


def _any_in_bbox(coords, bbox) -> bool:
    if isinstance(coords[0], (int, float)):
        return bbox[0] <= coords[0] <= bbox[2] and bbox[1] <= coords[1] <= bbox[3]
    return any(_any_in_bbox(c, bbox) for c in coords)


def trim_geojson(gj: dict, bbox=(-180.0, -60.0, -8.0, 86.0)) -> dict:
    feats = []
    for f in gj.get("features", []):
        g = f.get("geometry")
        if g and _any_in_bbox(g["coordinates"], bbox):
            feats.append({"type": "Feature", "properties": {}, "geometry": {"type": g["type"], "coordinates": _round(g["coordinates"])}})
    return {"type": "FeatureCollection", "features": feats}


def fetch_coast(http_get, out_dir: Path = DATA_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for local, remote in NE_FILES.items():
        _log(f"  Natural Earth {remote}")
        gj = trim_geojson(json.loads(http_get(NE_BASE + remote).decode("utf-8")))
        (out_dir / local).write_text(json.dumps(gj, separators=(",", ":")), encoding="utf-8")
        _log(f"    saved {local} ({len(gj['features'])} features)")


# ---------------------------------------------------------------- imagery
def _download_image(http_get, url_fn, size, retries_smaller=True):
    w, h = size
    last = None
    for scale in (1.0, 0.6):
        try:
            data = http_get(url_fn((int(w * scale), int(h * scale))))
            if gibs.looks_like_image(data):
                return data, (int(w * scale), int(h * scale))
            last = RuntimeError("service returned text instead of an image: " + data[:200].decode("utf-8", "replace"))
        except RuntimeError as exc:
            last = exc
        if not retries_smaller:
            break
    raise last  # type: ignore[misc]


def fetch_imagery(http_get, res: float = 0.12, out_dir: Path = IMG_DIR) -> dict:
    """Monthly Earth imagery for the whole of the Americas (Blue Marble, plus NDVI if offered)."""
    _log("  reading the GIBS layer list ...")
    layers = gibs.parse_layers(http_get(gibs.capabilities_url()))
    _log(f"  {len(layers)} layers available")
    bbox = AMERICAS
    size = (round((bbox[2] - bbox[0]) / res), round((bbox[3] - bbox[1]) / res))
    result = {}

    bm = (gibs.find_layer(layers, ["bluemarble", "nextgeneration"], prefer=["BlueMarble_NextGeneration"])
          or gibs.find_layer(layers, ["bluemarble"], avoid=["bathymetry"], prefer=["BlueMarble_ShadedRelief"])
          or gibs.find_layer(layers, ["bluemarble"]))
    if bm:
        times = gibs.monthly_times(layers[bm]["time"])
        subdaily = False
        _log(f"  Blue Marble layer: {bm}  ({len(times)} time steps)")
        d = out_dir / "bluemarble"
        d.mkdir(parents=True, exist_ok=True)
        files, stamps, months = [], [], []
        targets = times if times else [None]
        for t in targets:
            when = gibs.fmt_time(t, subdaily) if t else None
            url_fn = lambda sz, when=when: gibs.getmap_url(bm, bbox, sz, when, "image/jpeg")  # noqa: E731
            data, got = _download_image(http_get, url_fn, size)
            name = f"month_{t.month:02d}.jpg" if t else "static.jpg"
            (d / name).write_bytes(data)
            files.append(f"bluemarble/{name}"); stamps.append(when); months.append(t.month if t else 0)
            _log(f"    {name}  {got[0]}x{got[1]}  {len(data) // 1024} KB")
        result["bluemarble"] = {"layer": bm, "bbox": list(bbox), "size": list(got), "files": files,
                                "months": months, "times": stamps, "attribution": gibs.ACK}
    else:
        _log("  ! no Blue Marble layer found in GIBS; skipping")

    nd = gibs.find_layer(layers, ["ndvi", "terra"], prefer=["MODIS_Terra_NDVI_8Day"])
    if nd:
        times = gibs.monthly_times(layers[nd]["time"])
        _log(f"  NDVI layer: {nd}  ({len(times)} months)")
        d = out_dir / "ndvi"
        d.mkdir(parents=True, exist_ok=True)
        files, months, stamps = [], [], []
        for t in times:
            when = gibs.fmt_time(t, False)
            url_fn = lambda sz, when=when: gibs.getmap_url(nd, bbox, sz, when, "image/png", transparent=True)  # noqa: E731
            try:
                data, got = _download_image(http_get, url_fn, size)
            except RuntimeError as exc:
                _log(f"    ! {t.strftime('%b')} skipped: {exc}")
                continue
            name = f"month_{t.month:02d}.png"
            (d / name).write_bytes(data)
            files.append(f"ndvi/{name}"); months.append(t.month); stamps.append(when)
            _log(f"    {name}  {got[0]}x{got[1]}  {len(data) // 1024} KB")
        if len(files) >= 6:
            result["ndvi"] = {"layer": nd, "bbox": list(bbox), "size": list(got), "files": files,
                              "months": months, "times": stamps, "attribution": gibs.ACK}
    else:
        _log("  (no NDVI layer found; the green wave map stays procedural)")
    _manifest_update(**result)
    return result


def _best_window(points, days: int):
    """Start time of the `days`-long window with the greatest distance travelled."""
    best, best_t = -1.0, None
    ts = [datetime.fromisoformat(p["t"].replace("Z", "+00:00")) for p in points]
    j = 0
    for i in range(len(points)):
        while j < len(points) - 1 and ts[j + 1] - ts[i] <= timedelta(days=days):
            j += 1
        d = float(haversine_km(points[i]["lon"], points[i]["lat"], points[j]["lon"], points[j]["lat"]))
        if d > best:
            best, best_t = d, ts[i]
    return best_t.replace(minute=0, second=0, microsecond=0) if best_t else None


def fetch_goes(http_get, days: int = 4, step_hours: int = 2, res: float = 0.06,
               track: dict | None = None, out_dir: Path = IMG_DIR) -> dict:
    """Real GOES-East true-colour frames for a short window (aligned to a real GPS track if given)."""
    layers = gibs.parse_layers(http_get(gibs.capabilities_url()))
    layer = gibs.find_layer(layers, ["goes", "east", "geocolor"], prefer=["GOES-East_ABI_GeoColor"])
    if not layer:
        raise RuntimeError("No GOES-East GeoColor layer found in the GIBS layer list. "
                           "Run `python scripts/fetch_real_data.py layers goes` to see what is offered.")
    ext = layers[layer]["time"]
    lo, hi = min(s for s, _, _ in ext), max(e for _, e, _ in ext)
    aligned = False
    if track and len(track.get("points", [])) > 3:
        start = _best_window(track["points"], days)
        aligned = start is not None
    else:
        start = gibs.pick_window(ext, days=days)
    if start is None:
        raise RuntimeError("Could not choose a time window.")
    if start < lo or start + timedelta(days=days) > hi:
        raise RuntimeError(f"The GPS window {start:%Y-%m-%d} is outside the GOES layer's dates ({lo:%Y-%m-%d} to {hi:%Y-%m-%d}). "
                           "Use a track from within that period, or omit --track.")
    n = int(days * 24 / step_hours) + 1
    size = (round((HERO_BBOX[2] - HERO_BBOX[0]) / res), round((HERO_BBOX[3] - HERO_BBOX[1]) / res))
    d = out_dir / "goes"
    d.mkdir(parents=True, exist_ok=True)
    frames = []
    _log(f"  GOES layer {layer}: {n} frames from {start:%Y-%m-%d %H:%M} UTC, every {step_hours} h")
    for k in range(n):
        t = start + timedelta(hours=k * step_hours)
        url_fn = lambda sz, t=t: gibs.getmap_url(layer, HERO_BBOX, sz, gibs.fmt_time(t, True), "image/jpeg")  # noqa: E731
        try:
            data, got = _download_image(http_get, url_fn, size)
        except RuntimeError as exc:
            _log(f"    ! frame {k} skipped: {exc}")
            continue
        name = f"frame_{k:03d}.jpg"
        (d / name).write_bytes(data)
        frames.append({"t": t.isoformat().replace("+00:00", "Z"), "file": f"goes/{name}"})
        if k % 6 == 0:
            _log(f"    {name}  {got[0]}x{got[1]}  {len(data) // 1024} KB")
    if len(frames) < 4:
        raise RuntimeError("Too few GOES frames could be downloaded.")
    out = {"goes": {"layer": layer, "bbox": list(HERO_BBOX), "size": list(got), "frames": frames,
                    "step_hours": step_hours, "track_aligned": aligned, "attribution": gibs.ACK}}
    _manifest_update(**out)
    return out["goes"]


# ------------------------------------------------------------ observations
def fetch_observations(http_get, species_ids=None, cell: float = 3.0, workers: int = 3,
                       year_range: str | None = "2010,2024", min_effort: float = 100.0,
                       cache_dir: Path | None = None, out_dir: Path = REAL_DIR) -> dict:
    gb = Gbif(http_get, cache_dir or (DATA_DIR / "cache_gbif"), year_range)
    specs = [s for s in SPECIES if not species_ids or s["id"] in species_ids]
    if not specs:
        raise RuntimeError("No matching species ids.")
    aves = gb.match("Aves", rank="CLASS")
    _log(f"  GBIF taxon keys: Aves={aves}")
    regions = {s["id"]: observed.region_for(s, cell=cell) for s in specs}
    ub = (min(r[0] for r in regions.values()), min(r[1] for r in regions.values()),
          max(r[2] for r in regions.values()), max(r[3] for r in regions.values()))
    urows, ucols, ucells = observed.make_cells(ub, cell)
    _log(f"  all-bird effort over {len(ucells)} cells of {cell} degrees ...")
    prog = lambda d, n: _log(f"    {d}/{n}")  # noqa: E731
    eff = collect(gb, aves, ucells, workers, prog)
    effort = np.zeros((12, urows, ucols))
    for (r, c), v in eff.items():
        effort[:, r, c] = v

    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        prov = json.loads((out_dir / "provenance.json").read_text())
    except (OSError, ValueError):
        prov = {}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for spec in specs:
        b = regions[spec["id"]]
        key = gb.match(spec["latin"])
        rows, cols, cells = observed.make_cells(b, cell)
        _log(f"  {spec['common']} (taxonKey {key}): {len(cells)} cells")
        res = collect(gb, key, cells, workers, prog)
        counts = np.zeros((12, rows, cols))
        for (r, c), v in res.items():
            counts[:, r, c] = v
        r0 = int(round((ub[3] - b[3]) / cell)); c0 = int(round((b[0] - ub[0]) / cell))
        eff_sub = effort[:, r0:r0 + rows, c0:c0 + cols]
        raw, frames, _cov = observed.frames_from_counts(counts, eff_sub, b, cell, min_effort)
        analysis = observed.analyse(spec["id"], raw)
        (out_dir / f"{spec['id']}.frames.u8").write_bytes(frames.tobytes())
        (out_dir / f"{spec['id']}.analysis.json").write_text(json.dumps(analysis))
        prov[spec["id"]] = {
            "source": "GBIF.org occurrence search (includes the eBird Observation Dataset, CC BY 4.0)",
            "taxonKey": key, "records_in_region": int(counts.sum()), "all_bird_records_in_region": int(eff_sub.sum()),
            "cell_degrees": cell, "years": year_range, "min_effort_per_cell_month": min_effort, "queried": today,
            "method": "share of all bird records that are this species, per 3-degree cell and month, interpolated to weeks",
        }
        _log(f"    {int(counts.sum()):,} records used")
    prov["_citation"] = (f"GBIF.org ({today}) GBIF Occurrence Search API. Records of human observations "
                         f"{year_range or 'all years'}; includes the eBird Observation Dataset (Cornell Lab of Ornithology). "
                         "For a formal citation, make a GBIF download to obtain a DOI.")
    (out_dir / "provenance.json").write_text(json.dumps(prov, indent=1))
    return prov
