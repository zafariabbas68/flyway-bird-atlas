"""Turn real observation counts (GBIF/eBird records) into weekly map frames.

What the numbers mean
---------------------
For each grid cell and calendar month we have
    S = number of records of the species,   E = number of records of ALL birds (effort).
The map shows the *reporting frequency*  F = S / (E + k): out of the bird records made
in that place and month, how big a share were this species. Dividing by effort removes
most of the "birdwatchers go where it is nice" bias that raw counts have.

This is a real, observation-based signal, but it is NOT eBird Status & Trends abundance
(which uses a far more sophisticated statistical model). Months are interpolated to weeks
with a smooth curve, and coarse cells are bilinearly resampled, so fine detail is limited
by the cell size you choose.
"""
from __future__ import annotations

import numpy as np

from . import simulate as sim
from .geo import haversine_km

MONTH_CENTRE_DOY = np.array([15.5, 45.0, 74.5, 105.0, 135.5, 166.0, 196.5, 227.5, 258.0, 288.5, 319.0, 349.5])
BAND = sim.LAT_BAND_DEG


def region_for(spec: dict, margin: float = 12.0, cell: float = 3.0):
    """Bounding box (lon0, lat0, lon1, lat1) that comfortably contains a species' range."""
    xs, ys = [], []
    for key in ("breeding", "winter"):
        for lon, lat, sx, sy, _w in spec[key]:
            xs += [lon - 2.2 * sx, lon + 2.2 * sx]
            ys += [lat - 2.2 * sy, lat + 2.2 * sy]
    for lon, lat in spec["route_spring"] + (spec.get("route_fall") or []):
        xs.append(lon); ys.append(lat)
    lon0 = max(sim.LON_MIN, np.floor((min(xs) - margin) / cell) * cell)
    lon1 = min(sim.LON_MAX, np.ceil((max(xs) + margin) / cell) * cell)
    lat0 = max(sim.LAT_MIN, np.floor((min(ys) - margin) / cell) * cell)
    lat1 = min(sim.LAT_MAX, np.ceil((max(ys) + margin) / cell) * cell)
    return float(lon0), float(lat0), float(lon1), float(lat1)


def make_cells(bounds, cell: float):
    """[(row, col, (lon0, lat0, lon1, lat1))] with row 0 at the north edge."""
    lon0, lat0, lon1, lat1 = bounds
    cols = int(round((lon1 - lon0) / cell))
    rows = int(round((lat1 - lat0) / cell))
    out = []
    for r in range(rows):
        for c in range(cols):
            out.append((r, c, (lon0 + c * cell, lat1 - (r + 1) * cell, lon0 + (c + 1) * cell, lat1 - r * cell)))
    return rows, cols, out


def months_to_weeks(a: np.ndarray) -> np.ndarray:
    """(12, ...) -> (52, ...) periodic, smooth (cosine) interpolation between month centres."""
    out = np.empty((52,) + a.shape[1:], dtype=np.float64)
    for w in range(52):
        d = (w + 0.5) * 7.0
        j = int(np.searchsorted(MONTH_CENTRE_DOY, d, side="right")) % 12
        i = (j - 1) % 12
        ci, cj = MONTH_CENTRE_DOY[i], MONTH_CENTRE_DOY[j]
        span = (cj - ci) % 365.0
        s = ((d - ci) % 365.0) / span
        s = s * s * (3 - 2 * s)
        out[w] = a[i] * (1 - s) + a[j] * s
    return out


def resample_to_grid(a: np.ndarray, bounds, cell: float) -> np.ndarray:
    """(T, rows, cols) cell values -> (T, HEIGHT, WIDTH) on the display grid (bilinear)."""
    lon0, lat0, lon1, lat1 = bounds
    t, rows, cols = a.shape
    lon = sim.LON_MIN + (np.arange(sim.WIDTH) + 0.5) * sim.RES
    lat = sim.LAT_MAX - (np.arange(sim.HEIGHT) + 0.5) * sim.RES
    fc = (lon - lon0) / cell - 0.5
    fr = (lat1 - lat) / cell - 0.5
    inside_c = (lon >= lon0) & (lon <= lon1)
    inside_r = (lat >= lat0) & (lat <= lat1)
    c0 = np.clip(np.floor(fc).astype(int), 0, cols - 1); c1 = np.clip(c0 + 1, 0, cols - 1)
    r0 = np.clip(np.floor(fr).astype(int), 0, rows - 1); r1 = np.clip(r0 + 1, 0, rows - 1)
    wc = np.clip(fc - np.floor(fc), 0, 1)[None, None, :]
    wr = np.clip(fr - np.floor(fr), 0, 1)[None, :, None]
    g = lambda rr, cc: a[:, rr[:, None], cc[None, :]]  # noqa: E731
    out = (g(r0, c0) * (1 - wr) * (1 - wc) + g(r0, c1) * (1 - wr) * wc
           + g(r1, c0) * wr * (1 - wc) + g(r1, c1) * wr * wc)
    out = out * (inside_r[:, None] & inside_c[None, :])[None]
    return out


def frames_from_counts(species_counts: np.ndarray, effort: np.ndarray, bounds, cell: float,
                       min_effort: float = 100.0):
    """species_counts, effort: (12, rows, cols). Returns (raw (52,H,W) float, frames uint8, coverage)."""
    s = np.asarray(species_counts, dtype=float)
    e = np.asarray(effort, dtype=float)
    known = e >= min_effort
    k = max(20.0, 0.05 * float(np.median(e[known])) if known.any() else 20.0)
    freq = np.where(known, s / (e + k), 0.0)
    wk_f = months_to_weeks(freq)
    wk_m = months_to_weeks(known.astype(float))
    num = resample_to_grid(wk_f * wk_m, bounds, cell)
    den = resample_to_grid(wk_m, bounds, cell)
    raw = np.where(den > 0.3, num / np.maximum(den, 1e-6), 0.0)
    sigma = float(np.clip(cell / sim.RES * 0.33, 0.8, 4.0))
    gy, gx = sim._gaussian_matrix(sim.HEIGHT, sigma), sim._gaussian_matrix(sim.WIDTH, sigma)
    raw = np.stack([gy @ raw[w] @ gx.T for w in range(52)])
    nz = raw[raw > 1e-9]
    vmax = float(np.percentile(nz, 99.7)) if nz.size else 1.0
    frames = (np.clip(raw / vmax, 0, 1) ** 0.5 * 255).round().astype(np.uint8)
    return raw, frames, den.max(axis=0) > 0.3


def analyse(species_id: str, raw: np.ndarray) -> dict:
    """Same JSON shape as the simulated analysis, computed from observed maps."""
    lon = sim.LON_MIN + (np.arange(sim.WIDTH) + 0.5) * sim.RES
    lat = sim.LAT_MAX - (np.arange(sim.HEIGHT) + 0.5) * sim.RES
    mass = raw.sum(axis=(1, 2))
    mass = np.maximum(mass, 1e-12)
    cen_lat = (raw.sum(axis=2) * lat[None, :]).sum(axis=1) / mass
    cen_lon = (raw.sum(axis=1) * lon[None, :]).sum(axis=1) / mass
    var = (raw.sum(axis=2) * (lat[None, :] - cen_lat[:, None]) ** 2).sum(axis=1) / mass
    n_bands = int(round((sim.LAT_MAX - sim.LAT_MIN) / BAND))
    hov = np.zeros((52, n_bands))
    rowsum = raw.sum(axis=2)
    for w in range(52):
        hist, _ = np.histogram(lat, bins=n_bands, range=(sim.LAT_MIN, sim.LAT_MAX), weights=rowsum[w])
        hov[w] = hist / mass[w]

    p = raw / mass[:, None, None]
    turnover = np.array([0.5 * np.abs(p[w] - p[w - 1]).sum() for w in range(52)])
    rel = turnover / max(float(turnover.max()), 1e-9)

    iw, ib = int(np.argmin(cen_lat)), int(np.argmax(cen_lat))
    gc = float(haversine_km(cen_lon[iw], cen_lat[iw], cen_lon[ib], cen_lat[ib]))
    vel = np.array([cen_lat[(w + 1) % 52] - cen_lat[w - 1] for w in range(52)])

    def leg(a: int, b: int, sign: int):
        idx = [(a + k) % 52 for k in range(((b - a) % 52) + 1)] or [a]
        v = sign * vel[idx]
        peak = idx[int(np.argmax(v))]
        hit = [i for i, x in zip(idx, v) if x >= 0.25 * max(float(v.max()), 1e-9)]
        return peak, (hit[0] if hit else idx[0]), (hit[-1] if hit else idx[-1])

    sp_peak, sp_first, sp_last = leg(iw, ib, +1)
    fa_peak, fa_first, fa_last = leg(ib, iw, -1)
    sp_days = max(7, ((sp_last - sp_first) % 52 + 1) * 7)
    fa_days = max(7, ((fa_last - fa_first) % 52 + 1) * 7)

    areas = np.array([(raw[w] >= 0.05 * raw[w].max()).sum() if raw[w].max() > 0 else 0 for w in range(52)], float)
    return {
        "id": species_id, "kind": "observed",
        "centroid_lat": np.round(cen_lat, 2).tolist(), "centroid_lon": np.round(cen_lon, 2).tolist(),
        "lat_spread": np.round(np.sqrt(var), 2).tolist(),
        "moving_share": np.round(rel, 4).tolist(),
        "spring_share": np.round(np.where(vel > 0, rel, 0), 4).tolist(),
        "fall_share": np.round(np.where(vel < 0, rel, 0), 4).tolist(),
        "hovmoller": {"lat_min": sim.LAT_MIN, "lat_max": sim.LAT_MAX, "band_deg": BAND,
                      "values": np.round(hov, 4).tolist()},
        "summary": {
            "great_circle_km": int(round(gc, -1)), "spring_route_km": int(round(gc, -1)), "fall_route_km": int(round(gc, -1)),
            "spring_days": int(sp_days), "fall_days": int(fa_days),
            "spring_speed_km_day": int(round(gc / sp_days)), "fall_speed_km_day": int(round(gc / fa_days)),
            "spring_first_week": int(sp_first), "spring_last_week": int(sp_last), "spring_peak_week": int(sp_peak),
            "fall_first_week": int(fa_first), "fall_last_week": int(fa_last), "fall_peak_week": int(fa_peak),
            "share_of_year_travelling": round((sp_days + fa_days) / 365.0, 3),
            "max_share_in_transit": 1.0,
            "winter_lat": round(float(cen_lat[iw]), 1), "breeding_lat": round(float(cen_lat[ib]), 1),
            "latitude_shift": round(float(cen_lat[ib] - cen_lat[iw]), 1),
            "range_expansion": round(float(areas.max() / max(areas.min(), 1.0)), 2),
        },
    }
