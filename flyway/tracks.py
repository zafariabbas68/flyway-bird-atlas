"""Illustrative GPS-style track for the opening globe (a Broad-winged Hawk).

This is *simulated*, not a tagged bird. It follows the well-known Atlantic /
Gulf / Central American soaring route and only advances during daylight, which
reproduces the stop-start staircase look of real soaring-bird tracks.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from .geo import haversine_km, polyline_position, polyline_length_km

ROUTE = [
    (-75.99, 40.63),   # Pennsylvania ridge
    (-79.5, 36.0), (-84.0, 32.5), (-88.5, 30.5), (-93.0, 29.3),
    (-96.8, 27.5),     # Texas coast
    (-97.8, 23.0), (-96.8, 19.5),   # Veracruz
    (-93.5, 17.2), (-90.0, 15.8), (-86.5, 13.5), (-84.0, 10.5),
    (-80.0, 8.9),      # Panama
    (-77.3, 7.5), (-75.5, 5.0), (-74.5, 2.0), (-76.0, -1.5), (-76.5, -4.5),
]

START = datetime(2025, 9, 10, 0, 0, tzinfo=timezone.utc)
END = datetime(2025, 11, 12, 0, 0, tzinfo=timezone.utc)
STEP_HOURS = 3


def build_track(seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    total_km = polyline_length_km(ROUTE)
    travelled = 0.0
    t = START
    points = []
    day_rest = {}
    while t <= END:
        pos = polyline_position(ROUTE, travelled / total_km)
        lon, lat = float(pos[0]), float(pos[1])
        points.append({"t": t.isoformat().replace("+00:00", "Z"), "lon": round(lon, 4), "lat": round(lat, 4)})
        # local solar hour
        local_hour = (t.hour + lon / 15.0) % 24
        day_key = t.date().isoformat()
        if day_key not in day_rest:
            # about one day in six is a rest day (weather, roost)
            day_rest[day_key] = rng.random() < 0.16
            day_rest[day_key + "_f"] = rng.uniform(0.65, 1.2)
        flying = (9.0 <= local_hour <= 17.0) and not day_rest[day_key]
        if flying and travelled < total_km:
            speed_kmh = 38.0 * day_rest[day_key + "_f"]
            travelled = min(total_km, travelled + speed_kmh * STEP_HOURS)
        t += timedelta(hours=STEP_HOURS)
        if travelled >= total_km and t > START + timedelta(days=60):
            break

    # a tiny bit of GPS noise, then drop fixes after arrival
    for p in points:
        p["lon"] = round(p["lon"] + float(rng.normal(0, 0.03)), 4)
        p["lat"] = round(p["lat"] + float(rng.normal(0, 0.03)), 4)
    last_move = max(i for i in range(1, len(points))
                    if haversine_km(points[i]["lon"], points[i]["lat"], points[i - 1]["lon"], points[i - 1]["lat"]) > 5)
    points = points[: last_move + 8]

    return {
        "name": "Illustrative Broad-winged Hawk",
        "source": "simulated",
        "note": "Simulated track based on a typical fall route. Not a tagged bird.",
        "route_km": int(round(total_km, -1)),
        "points": points,
    }


def load_movebank_csv(path, bin_hours: int = 3, max_points: int = 900):
    """Read a Movebank CSV export (columns: timestamp, location-long, location-lat).

    Keeps one fix per `bin_hours` so a year of GPS data stays light. Returns None if the
    file has no usable rows.
    """
    import csv

    rows = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            try:
                t = datetime.fromisoformat(r["timestamp"].strip().replace(" ", "T").replace("Z", "+00:00"))
                if t.tzinfo is None:
                    t = t.replace(tzinfo=timezone.utc)
                lon, lat = float(r["location-long"]), float(r["location-lat"])
            except (KeyError, ValueError):
                continue
            rows.append((t, lon, lat))
    if len(rows) < 3:
        return None
    rows.sort()
    kept, last_bin = [], None
    for t, lon, lat in rows:
        b = int(t.timestamp() // (bin_hours * 3600))
        if b != last_bin:
            kept.append((t, lon, lat)); last_bin = b
    step = max(1, len(kept) // max_points)
    kept = kept[::step]
    pts = [{"t": t.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"), "lon": round(lon, 4), "lat": round(lat, 4)}
           for t, lon, lat in kept]
    km = polyline_length_km([(p["lon"], p["lat"]) for p in pts])
    return {
        "name": "Tagged Broad-winged Hawk",
        "source": "movebank",
        "note": "GPS track exported from Movebank. Credit the data owner as required by the dataset licence.",
        "route_km": int(round(km, -1)),
        "points": pts,
    }
