
from __future__ import annotations

import json
import os
from pathlib import Path

from . import simulate

REAL_DIR = simulate.CACHE_DIR / "real"
IMG_DIR = Path(__file__).resolve().parent.parent / "static" / "img" / "real"
TRACK_CSV = Path(__file__).resolve().parent / "data" / "tracks" / "hawk.csv"


def mode() -> str:
    return os.environ.get("FLYWAY_DATA", "auto").lower()


def _paths(species_id: str):
    return REAL_DIR / f"{species_id}.frames.u8", REAL_DIR / f"{species_id}.analysis.json"


def has_real(species_id: str) -> bool:
    if mode() == "simulated":
        return False
    f, a = _paths(species_id)
    return f.exists() and a.exists()


def kind(species_id: str) -> str:
    return "observed" if has_real(species_id) else "simulated"


def load_frames_bytes(species_id: str) -> bytes:
    if has_real(species_id):
        return _paths(species_id)[0].read_bytes()
    return simulate.load_frames_bytes(species_id)


def load_analysis(species_id: str) -> dict:
    if has_real(species_id):
        return json.loads(_paths(species_id)[1].read_text())
    a = simulate.load_analysis(species_id)
    a.setdefault("kind", "simulated")
    return a


def provenance() -> dict:
    p = REAL_DIR / "provenance.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def imagery_manifest() -> dict:
    p = IMG_DIR / "manifest.json"
    try:
        m = json.loads(p.read_text())
    except (OSError, ValueError):
        return {"available": False}
    m["available"] = True
    return m
