"""Flyway - an animated, scroll-driven bird migration atlas."""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from .simulate import ensure_all

ROOT = Path(__file__).resolve().parent.parent


def create_app(prebuild: bool = True) -> Flask:
    app = Flask(
        __name__,
        static_folder=str(ROOT / "static"),
        template_folder=str(ROOT / "templates"),
    )
    app.config["JSON_SORT_KEYS"] = False
    app.json.sort_keys = False  # Flask >= 2.2

    if prebuild:
        # Builds any missing/out-of-date species grids (about 2 seconds in total).
        ensure_all(verbose=True)

    from .routes import bp

    app.register_blueprint(bp)
    return app
