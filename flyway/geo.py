"""Small geographic helpers (no external dependencies beyond NumPy)."""
from __future__ import annotations

import numpy as np

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lon1, lat1, lon2, lat2):
    """Great-circle distance in km. Works on scalars or NumPy arrays."""
    lon1, lat1, lon2, lat2 = map(np.radians, (lon1, lat1, lon2, lat2))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def polyline_length_km(points) -> float:
    pts = np.asarray(points, dtype=float)
    return float(np.sum(haversine_km(pts[:-1, 0], pts[:-1, 1], pts[1:, 0], pts[1:, 1])))


def cumulative_lengths(routes: np.ndarray) -> np.ndarray:
    """routes: (n, K, 2) lon/lat. Returns (n, K) cumulative km along each route."""
    seg = haversine_km(routes[:, :-1, 0], routes[:, :-1, 1], routes[:, 1:, 0], routes[:, 1:, 1])
    cum = np.zeros((routes.shape[0], routes.shape[1]))
    cum[:, 1:] = np.cumsum(seg, axis=1)
    return cum


def position_along(routes: np.ndarray, cum: np.ndarray, progress: np.ndarray) -> np.ndarray:
    """Vectorised point-at-fraction for many polylines.

    routes: (n, K, 2), cum: (n, K), progress: (n,) in [0, 1] -> (n, 2)
    """
    n, k, _ = routes.shape
    total = cum[:, -1]
    target = np.clip(progress, 0.0, 1.0) * total
    idx = (cum <= target[:, None]).sum(axis=1) - 1
    idx = np.clip(idx, 0, k - 2)
    rows = np.arange(n)
    seg_len = np.maximum(cum[rows, idx + 1] - cum[rows, idx], 1e-9)
    frac = (target - cum[rows, idx]) / seg_len
    p0 = routes[rows, idx]
    p1 = routes[rows, idx + 1]
    return p0 + (p1 - p0) * frac[:, None]


def polyline_position(points, fraction: float):
    """Point at a given fraction of the total length of a single polyline."""
    pts = np.asarray(points, dtype=float)
    seg = haversine_km(pts[:-1, 0], pts[:-1, 1], pts[1:, 0], pts[1:, 1])
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    target = min(max(fraction, 0.0), 1.0) * cum[-1]
    i = int(np.clip(np.searchsorted(cum, target, side="right") - 1, 0, len(pts) - 2))
    f = (target - cum[i]) / max(cum[i + 1] - cum[i], 1e-9)
    return pts[i] + (pts[i + 1] - pts[i]) * f
