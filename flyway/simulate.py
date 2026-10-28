"""Agent-based annual-cycle model that produces 52 weekly abundance grids.

How it works (mirrors the *shape* of eBird-style weekly abundance products):

1. Draw N individual birds. Each gets a wintering site and a breeding site drawn
   from the species' Gaussian-mixture ranges, plus its own spring and fall
   departure dates and trip durations.
2. Each bird follows a personal polyline (winter -> waypoints -> breeding, and
   back) with random stopovers, so the population forms a moving wave rather
   than a single dot.
3. For each of the 52 weeks, every bird's position is binned onto a lon/lat
   grid and blurred with a Gaussian kernel. That gives a smooth relative
   abundance surface per week.
4. All weeks of a species are rescaled with one shared maximum, so brightness is
   comparable across the whole year (the same approach used for real data).

The same pass also produces analysis series (centroid latitude, share of birds
in transit, latitude-by-week distribution) used by the dashboard.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .geo import cumulative_lengths, haversine_km, position_along
from .species_data import SPECIES, get_species

# --------------------------------------------------------------------- grid
LON_MIN, LON_MAX = -170.0, -40.0
LAT_MIN, LAT_MAX = -30.0, 72.0
RES = 0.75
WIDTH = int(round((LON_MAX - LON_MIN) / RES))   # 173 columns
HEIGHT = int(round((LAT_MAX - LAT_MIN) / RES))  # 136 rows
WEEKS = 52
N_BIRDS = 6000
BLUR_SIGMA_CELLS = 1.4
LAT_BAND_DEG = 2.0

CACHE_DIR = Path(__file__).resolve().parent / "cache"
MODEL_VERSION = 3

GRID_META = {
    "lon_min": LON_MIN,
    "lon_max": LON_MAX,
    "lat_min": LAT_MIN,
    "lat_max": LAT_MAX,
    "res": RES,
    "width": WIDTH,
    "height": HEIGHT,
    "weeks": WEEKS,
}


@dataclass
class SimResult:
    frames: np.ndarray  # (52, H, W) uint8
    analysis: dict


# ------------------------------------------------------------------ helpers
def _sample_mixture(components, n: int, rng: np.random.Generator) -> np.ndarray:
    comps = np.asarray(components, dtype=float)
    w = comps[:, 4] / comps[:, 4].sum()
    pick = rng.choice(len(comps), size=n, p=w)
    out = np.empty((n, 2))
    out[:, 0] = comps[pick, 0] + rng.normal(size=n) * comps[pick, 2]
    out[:, 1] = comps[pick, 1] + rng.normal(size=n) * comps[pick, 3]
    out[:, 1] = np.clip(out[:, 1], LAT_MIN + 1, LAT_MAX - 1)
    out[:, 0] = np.clip(out[:, 0], LON_MIN + 1, LON_MAX - 1)
    return out


def _gaussian_matrix(size: int, sigma: float) -> np.ndarray:
    idx = np.arange(size)
    m = np.exp(-0.5 * ((idx[:, None] - idx[None, :]) / sigma) ** 2)
    return m / m.sum(axis=1, keepdims=True)


def _build_routes(start, end, waypoints, corridor, rng):
    """(n, K, 2) polylines: start -> jittered waypoints -> end."""
    n = start.shape[0]
    wps = np.asarray(waypoints, dtype=float)
    k = len(wps)
    shared = rng.normal(size=(n, 1, 2)) * corridor  # whole-route lateral offset
    indep = rng.normal(size=(n, k, 2)) * corridor * 0.35
    mid = wps[None, :, :] + shared + indep
    return np.concatenate([start[:, None, :], mid, end[:, None, :]], axis=1)


def _stopover_curve(n: int, hops: int, pause_frac: float, rng):
    """Time-warp breakpoints. Returns (tb, pb) each (n, 2*hops+1).

    tb: normalised time breakpoints in [0,1]; pb: route progress at those times.
    Pauses keep progress constant, flights advance it.
    """
    fly = rng.uniform(0.6, 1.4, size=(n, hops))
    pause = rng.uniform(0.0, 1.0, size=(n, hops - 1)) * pause_frac * 2.0
    segs_t = np.zeros((n, 2 * hops - 1))
    segs_p = np.zeros((n, 2 * hops - 1))
    segs_t[:, 0::2] = fly / fly.sum(axis=1, keepdims=True) * (1.0)
    segs_p[:, 0::2] = fly / fly.sum(axis=1, keepdims=True)
    if hops > 1:
        segs_t[:, 1::2] = pause
    # normalise total time to 1
    total_t = segs_t.sum(axis=1, keepdims=True)
    segs_t = segs_t / total_t
    tb = np.concatenate([np.zeros((n, 1)), np.cumsum(segs_t, axis=1)], axis=1)
    pb = np.concatenate([np.zeros((n, 1)), np.cumsum(segs_p, axis=1)], axis=1)
    return tb, np.clip(pb, 0, 1)


def _progress(tb, pb, tau):
    """Evaluate the stopover curve at normalised time tau (n,) -> progress (n,)."""
    n, m = tb.shape
    tau = np.clip(tau, 0.0, 1.0)
    idx = np.clip((tb <= tau[:, None]).sum(axis=1) - 1, 0, m - 2)
    rows = np.arange(n)
    den = np.maximum(tb[rows, idx + 1] - tb[rows, idx], 1e-9)
    f = (tau - tb[rows, idx]) / den
    return pb[rows, idx] + (pb[rows, idx + 1] - pb[rows, idx]) * f


# ----------------------------------------------------------------- the model
def spec_fingerprint(spec: dict) -> str:
    raw = json.dumps(
        {k: spec[k] for k in spec if k not in ("steps", "tagline")}, sort_keys=True, default=str
    )
    raw += f"|{MODEL_VERSION}|{N_BIRDS}|{RES}|{BLUR_SIGMA_CELLS}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def simulate_species(spec: dict, n: int = N_BIRDS, seed: int | None = None) -> SimResult:
    if seed is None:
        seed = int(hashlib.md5(spec["id"].encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)

    winter = _sample_mixture(spec["winter"], n, rng)
    breed = _sample_mixture(spec["breeding"], n, rng)

    wp_spring = spec["route_spring"]
    wp_fall = spec.get("route_fall") or list(reversed(wp_spring))
    spring_routes = _build_routes(winter, breed, wp_spring, spec["corridor"], rng)
    fall_routes = _build_routes(breed, winter, wp_fall, spec["corridor"], rng)
    cum_s = cumulative_lengths(spring_routes)
    cum_f = cumulative_lengths(fall_routes)

    ds_mu, ds_sd, ts_mu, ts_sd = spec["spring"]
    df_mu, df_sd, tf_mu, tf_sd = spec["fall"]
    ds = np.clip(rng.normal(ds_mu, ds_sd, n), 1, 30)
    ts = np.clip(rng.normal(ts_mu, ts_sd, n), 2.5, 16)
    df = np.clip(rng.normal(df_mu, df_sd, n), ds + ts + 2, 46)
    tf = np.clip(rng.normal(tf_mu, tf_sd, n), 2.5, 16)
    # a trip that would run past the end of the year is shortened slightly
    tf = np.minimum(tf, 51.0 - df)

    hops = 7
    tb_s, pb_s = _stopover_curve(n, hops, spec["pause"], rng)
    tb_f, pb_f = _stopover_curve(n, hops, spec["pause"], rng)

    # persistent "home range" offsets so birds are not stacked at a single point
    home_w = rng.normal(size=(n, 2)) * 0.6
    home_b = rng.normal(size=(n, 2)) * 0.6

    gy = _gaussian_matrix(HEIGHT, BLUR_SIGMA_CELLS)
    gx = _gaussian_matrix(WIDTH, BLUR_SIGMA_CELLS)

    raw = np.zeros((WEEKS, HEIGHT, WIDTH), dtype=np.float32)
    moving_frac = np.zeros(WEEKS)
    spring_frac = np.zeros(WEEKS)
    fall_frac = np.zeros(WEEKS)
    cen_lat = np.zeros(WEEKS)
    cen_lon = np.zeros(WEEKS)
    lat_sd = np.zeros(WEEKS)
    n_bands = int(round((LAT_MAX - LAT_MIN) / LAT_BAND_DEG))
    hov = np.zeros((WEEKS, n_bands))

    for w in range(WEEKS):
        t = w + 0.5
        pos = np.empty((n, 2))
        in_spring = (t >= ds) & (t < ds + ts)
        in_fall = (t >= df) & (t < df + tf)
        at_breed = (t >= ds + ts) & (t < df)
        at_winter = ~(in_spring | in_fall | at_breed)

        pos[at_winter] = winter[at_winter] + home_w[at_winter]
        pos[at_breed] = breed[at_breed] + home_b[at_breed]

        if in_spring.any():
            sel = np.where(in_spring)[0]
            tau = (t - ds[sel]) / ts[sel]
            p = _progress(tb_s[sel], pb_s[sel], tau)
            pos[sel] = position_along(spring_routes[sel], cum_s[sel], p)
            spread = spec["corridor"] * 0.5 * np.sin(np.pi * p)[:, None]
            pos[sel] += rng.normal(size=(sel.size, 2)) * spread
        if in_fall.any():
            sel = np.where(in_fall)[0]
            tau = (t - df[sel]) / tf[sel]
            p = _progress(tb_f[sel], pb_f[sel], tau)
            pos[sel] = position_along(fall_routes[sel], cum_f[sel], p)
            spread = spec["corridor"] * 0.5 * np.sin(np.pi * p)[:, None]
            pos[sel] += rng.normal(size=(sel.size, 2)) * spread

        pos[:, 0] = np.clip(pos[:, 0], LON_MIN + 0.01, LON_MAX - 0.01)
        pos[:, 1] = np.clip(pos[:, 1], LAT_MIN + 0.01, LAT_MAX - 0.01)

        # --- bin to grid (row 0 = north)
        col = ((pos[:, 0] - LON_MIN) / RES).astype(int).clip(0, WIDTH - 1)
        row = ((LAT_MAX - pos[:, 1]) / RES).astype(int).clip(0, HEIGHT - 1)
        counts = np.bincount(row * WIDTH + col, minlength=HEIGHT * WIDTH).reshape(HEIGHT, WIDTH)
        raw[w] = gy @ counts.astype(np.float32) @ gx.T

        moving = in_spring | in_fall
        moving_frac[w] = moving.mean()
        spring_frac[w] = in_spring.mean()
        fall_frac[w] = in_fall.mean()
        cen_lat[w] = pos[:, 1].mean()
        cen_lon[w] = pos[:, 0].mean()
        lat_sd[w] = pos[:, 1].std()
        hist, _ = np.histogram(pos[:, 1], bins=n_bands, range=(LAT_MIN, LAT_MAX))
        hov[w] = hist / n

    # --- shared scaling across the year, then sqrt for visual balance
    nz = raw[raw > 1e-4]
    vmax = float(np.percentile(nz, 99.7)) if nz.size else 1.0
    frames = (np.clip(raw / vmax, 0, 1) ** 0.5 * 255).round().astype(np.uint8)

    # --- summary metrics
    gc_km = haversine_km(winter[:, 0], winter[:, 1], breed[:, 0], breed[:, 1])
    route_km = cum_s[:, -1]
    fall_km = cum_f[:, -1]
    spring_days = ts * 7
    fall_days = tf * 7

    def first_week(series, thresh):
        hit = np.where(series >= thresh)[0]
        return int(hit[0]) if hit.size else None

    def last_week(series, thresh):
        hit = np.where(series >= thresh)[0]
        return int(hit[-1]) if hit.size else None

    spring_thresh = max(0.04, spring_frac.max() * 0.25)
    fall_thresh = max(0.04, fall_frac.max() * 0.25)

    analysis = {
        "id": spec["id"],
        "kind": "simulated",
        "centroid_lat": np.round(cen_lat, 2).tolist(),
        "centroid_lon": np.round(cen_lon, 2).tolist(),
        "lat_spread": np.round(lat_sd, 2).tolist(),
        "moving_share": np.round(moving_frac, 4).tolist(),
        "spring_share": np.round(spring_frac, 4).tolist(),
        "fall_share": np.round(fall_frac, 4).tolist(),
        "hovmoller": {
            "lat_min": LAT_MIN,
            "lat_max": LAT_MAX,
            "band_deg": LAT_BAND_DEG,
            "values": np.round(hov, 4).tolist(),  # [week][band] south -> north
        },
        "summary": {
            "great_circle_km": int(round(float(np.median(gc_km)), -1)),
            "spring_route_km": int(round(float(np.median(route_km)), -1)),
            "fall_route_km": int(round(float(np.median(fall_km)), -1)),
            "spring_days": int(round(float(np.median(spring_days)))),
            "fall_days": int(round(float(np.median(fall_days)))),
            "spring_speed_km_day": int(round(float(np.median(route_km / spring_days)))),
            "fall_speed_km_day": int(round(float(np.median(fall_km / fall_days)))),
            "spring_first_week": first_week(spring_frac, spring_thresh),
            "spring_last_week": last_week(spring_frac, spring_thresh),
            "spring_peak_week": int(spring_frac.argmax()),
            "fall_first_week": first_week(fall_frac, fall_thresh),
            "fall_last_week": last_week(fall_frac, fall_thresh),
            "fall_peak_week": int(fall_frac.argmax()),
            "share_of_year_travelling": round(float(np.median((ts + tf) / 52.0)), 3),
            "max_share_in_transit": round(float(moving_frac.max()), 3),
            "winter_lat": round(float(np.median(winter[:, 1])), 1),
            "breeding_lat": round(float(np.median(breed[:, 1])), 1),
            "latitude_shift": round(float(np.median(breed[:, 1]) - np.median(winter[:, 1])), 1),
            "range_expansion": round(float(_range_area_ratio(raw)), 2),
        },
    }
    return SimResult(frames=frames, analysis=analysis)


def _range_area_ratio(raw: np.ndarray) -> float:
    """Ratio of the area covered by the species in its widest week vs. narrowest.

    'Area' = number of grid cells holding at least 5% of that week's peak cell.
    """
    areas = []
    for w in range(raw.shape[0]):
        mx = raw[w].max()
        areas.append(int((raw[w] >= 0.05 * mx).sum()) if mx > 0 else 0)
    areas = np.asarray(areas, dtype=float)
    lo = max(areas.min(), 1.0)
    return float(areas.max() / lo)


# ------------------------------------------------------------------- caching
def _paths(species_id: str):
    return CACHE_DIR / f"{species_id}.frames.u8", CACHE_DIR / f"{species_id}.analysis.json"


def ensure_species(spec: dict, force: bool = False, verbose: bool = False) -> None:
    frames_path, analysis_path = _paths(spec["id"])
    fp = spec_fingerprint(spec)
    if not force and frames_path.exists() and analysis_path.exists():
        try:
            if json.loads(analysis_path.read_text()).get("fingerprint") == fp:
                return
        except (OSError, ValueError):
            pass
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"[flyway] simulating {spec['common']} ...", flush=True)
    result = simulate_species(spec)
    result.analysis["fingerprint"] = fp
    frames_path.write_bytes(result.frames.tobytes())
    analysis_path.write_text(json.dumps(result.analysis))


def ensure_all(force: bool = False, verbose: bool = False) -> None:
    for spec in SPECIES:
        ensure_species(spec, force=force, verbose=verbose)


def load_frames_bytes(species_id: str) -> bytes:
    spec = get_species(species_id)
    if spec is None:
        raise KeyError(species_id)
    ensure_species(spec)
    return _paths(species_id)[0].read_bytes()


def load_analysis(species_id: str) -> dict:
    spec = get_species(species_id)
    if spec is None:
        raise KeyError(species_id)
    ensure_species(spec)
    return json.loads(_paths(species_id)[1].read_text())
