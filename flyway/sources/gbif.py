"""GBIF (Global Biodiversity Information Facility) occurrence counts, no API key.

Used endpoints (documented, public):
  * GET /v1/species/match?name=...                     -> usageKey
  * GET /v1/occurrence/search?taxonKey=..&month ..
        &geometry=POLYGON((...))&limit=0&facet=month   -> counts per month inside a box
GBIF includes the eBird Observation Dataset (CC BY 4.0) among its sources.
"""
from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote, urlencode

API = "https://api.gbif.org/v1"


def wkt_box(lon0: float, lat0: float, lon1: float, lat1: float) -> str:
    """Counter-clockwise polygon (GBIF requires CCW ring order)."""
    return f"POLYGON(({lon0} {lat0},{lon1} {lat0},{lon1} {lat1},{lon0} {lat1},{lon0} {lat0}))"


class Gbif:
    def __init__(self, http_get, cache_dir: Path | None = None, year_range: str | None = "2010,2024"):
        self.get = http_get
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.year_range = year_range
        self.requests = 0
        self._lock = threading.Lock()
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    # -- cached JSON GET
    def _json(self, url: str):
        key = hashlib.sha1(url.encode()).hexdigest()
        if self.cache_dir:
            p = self.cache_dir / f"{key}.json"
            if p.exists():
                return json.loads(p.read_text())
        data = json.loads(self.get(url).decode("utf-8"))
        with self._lock:
            self.requests += 1
        if self.cache_dir:
            (self.cache_dir / f"{key}.json").write_text(json.dumps(data))
        return data

    def match(self, name: str, rank: str | None = None) -> int:
        q = {"name": name}
        if rank:
            q["rank"] = rank
        info = self._json(f"{API}/species/match?{urlencode(q)}")
        key = info.get("usageKey") or info.get("speciesKey") or info.get("classKey")
        if not key:
            raise RuntimeError(f"GBIF could not match the name {name!r}: {info}")
        return int(key)

    def month_counts(self, taxon_key: int, box: tuple[float, float, float, float]) -> list[int]:
        """Records per calendar month (index 0 = January) inside box=(lon0,lat0,lon1,lat1)."""
        params = {
            "taxonKey": taxon_key, "hasCoordinate": "true", "hasGeospatialIssue": "false",
            "basisOfRecord": "HUMAN_OBSERVATION", "limit": 0, "facet": "month", "facetLimit": 12,
        }
        if self.year_range:
            params["year"] = self.year_range
        url = f"{API}/occurrence/search?{urlencode(params)}&geometry={quote(wkt_box(*box))}"
        return parse_month_facet(self._json(url))


def parse_month_facet(resp: dict) -> list[int]:
    out = [0] * 12
    for facet in resp.get("facets", []) or []:
        if str(facet.get("field", "")).upper() != "MONTH":
            continue
        for c in facet.get("counts", []) or []:
            try:
                m = int(str(c.get("name")).strip())
            except ValueError:
                continue
            if 1 <= m <= 12:
                out[m - 1] = int(c.get("count", 0))
    return out


def collect(gbif: Gbif, taxon_key: int, cells: list[tuple], workers: int = 3, progress=None) -> dict:
    """cells: [(row, col, (lon0,lat0,lon1,lat1))] -> {(row,col): [12 counts]}"""
    results: dict = {}
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(gbif.month_counts, taxon_key, box): (r, c) for r, c, box in cells}
        for fut in as_completed(futs):
            results[futs[fut]] = fut.result()
            done += 1
            if progress and (done % 25 == 0 or done == len(futs)):
                progress(done, len(futs))
    return results
