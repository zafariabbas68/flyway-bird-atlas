"""Basemap loader: Natural Earth if present, otherwise the built-in outlines."""
from __future__ import annotations

import json
from pathlib import Path

from .basemap_builtin import build_geojson

DATA_DIR = Path(__file__).resolve().parent / "data"
NE_LAND = DATA_DIR / "ne_land.geojson"
NE_COUNTRIES = DATA_DIR / "ne_countries.geojson"
NE_LAKES = DATA_DIR / "ne_lakes.geojson"

_cache: dict | None = None


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def get_basemap() -> dict:
    """Return a FeatureCollection whose features carry properties.kind in
    {land, lake, border, country}."""
    global _cache
    if _cache is not None:
        return _cache

    land = _load(NE_LAND) if NE_LAND.exists() else None
    if not land:
        _cache = build_geojson()
        return _cache

    feats = []
    for f in land.get("features", []):
        f = dict(f)
        f["properties"] = {"kind": "land"}
        feats.append(f)
    countries = _load(NE_COUNTRIES) if NE_COUNTRIES.exists() else None
    for f in (countries or {}).get("features", []):
        f = dict(f)
        f["properties"] = {"kind": "country"}
        feats.append(f)
    lakes = _load(NE_LAKES) if NE_LAKES.exists() else None
    for f in (lakes or {}).get("features", []):
        f = dict(f)
        f["properties"] = {"kind": "lake"}
        feats.append(f)
    _cache = {"type": "FeatureCollection", "features": feats,
              "properties": {"source": "natural-earth"}}
    return _cache
