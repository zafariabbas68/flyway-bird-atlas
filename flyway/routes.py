"""HTTP routes: the page, plus a small JSON/binary API."""
from __future__ import annotations

from flask import Blueprint, Response, abort, jsonify, render_template

from . import simulate, store
from .basemap import get_basemap
from .species_data import SPECIES, get_species
from .tracks import build_track, load_movebank_csv

bp = Blueprint("flyway", __name__)

_track_cache: dict | None = None


def _public_species(sp: dict, full: bool = False) -> dict:
    out = {
        "id": sp["id"],
        "common": sp["common"],
        "latin": sp["latin"],
        "group": sp["group"],
        "color": sp["color"],
        "strategy": sp["strategy"],
        "tagline": sp["tagline"],
        "view": sp["view"],
    }
    if full:
        out["steps"] = sp["steps"]
    return out


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/healthz")
def healthz():
    return jsonify(status="ok")


@bp.get("/api/meta")
def api_meta():
    return jsonify(
        {
            "title": "Flyway",
            "grid": simulate.GRID_META,
            "species": [_public_species(sp, full=True) for sp in SPECIES],
            "basemap_source": get_basemap().get("properties", {}).get("source"),
            "data": {
                "mode": store.mode(),
                "species": {sp["id"]: store.kind(sp["id"]) for sp in SPECIES},
                "provenance": store.provenance(),
                "imagery": store.imagery_manifest().get("available", False),
            },
            "data_note": (
                "All abundance surfaces, routes and tracks in this project are modelled "
                "for illustration. They are not eBird data and not real GPS tags."
            ),
        }
    )


@bp.get("/api/species")
def api_species():
    return jsonify([_public_species(sp) for sp in SPECIES])


@bp.get("/api/species/<species_id>")
def api_species_one(species_id: str):
    sp = get_species(species_id)
    if sp is None:
        abort(404)
    return jsonify(_public_species(sp, full=True))


@bp.get("/api/species/<species_id>/frames.bin")
def api_frames(species_id: str):
    if get_species(species_id) is None:
        abort(404)
    data = store.load_frames_bytes(species_id)
    resp = Response(data, mimetype="application/octet-stream")
    resp.headers["Cache-Control"] = "public, max-age=3600"
    resp.headers["X-Grid"] = f"{simulate.WEEKS}x{simulate.HEIGHT}x{simulate.WIDTH}"
    return resp


@bp.get("/api/species/<species_id>/analysis")
def api_analysis(species_id: str):
    if get_species(species_id) is None:
        abort(404)
    return jsonify(store.load_analysis(species_id))


@bp.get("/api/compare")
def api_compare():
    rows = []
    for sp in SPECIES:
        a = store.load_analysis(sp["id"])
        rows.append({**_public_species(sp), "summary": a["summary"],
                     "centroid_lat": a["centroid_lat"], "moving_share": a["moving_share"]})
    return jsonify(rows)


@bp.get("/api/basemap")
def api_basemap():
    resp = jsonify(get_basemap())
    resp.headers["Cache-Control"] = "public, max-age=3600"
    return resp


@bp.get("/api/imagery")
def api_imagery():
    resp = jsonify(store.imagery_manifest())
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@bp.get("/api/track/hawk")
def api_track():
    global _track_cache
    if _track_cache is None:
        real = load_movebank_csv(store.TRACK_CSV) if store.TRACK_CSV.exists() else None
        _track_cache = real or build_track()
    return jsonify(_track_cache)
