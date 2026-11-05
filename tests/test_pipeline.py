
import io, json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np
from PIL import Image

from flyway import simulate, observed
from flyway.sources import gibs, pipeline
from flyway.tracks import load_movebank_csv

FIX = Path(__file__).parent / "fixtures"


def _jpeg(w, h, rgb=(40, 120, 60), fmt="JPEG"):
    b = io.BytesIO(); Image.new("RGB", (w, h), rgb).save(b, fmt); return b.getvalue()


def mock_http(url, **_):
    q = parse_qs(urlparse(url).query)
    if "GetCapabilities" in url:
        return (FIX / "gibs_capabilities.xml").read_bytes()
    if "GetMap" in url:
        # WMS 1.3.0 bbox is lat-first
        lat0, lon0, lat1, lon1 = map(float, q["BBOX"][0].split(","))
        assert lat0 < lat1 and lon0 < lon1 and abs(lat0) <= 90
        return _jpeg(int(q["WIDTH"][0]) // 20, int(q["HEIGHT"][0]) // 20)
    if "species/match" in url:
        return json.dumps({"usageKey": 212 if q["name"][0] == "Aves" else 5000 + len(q["name"][0])}).encode()
    if "occurrence/search" in url:
        total = 4000 if q["taxonKey"][0] == "212" else 400
        return json.dumps({"count": total, "facets": [{"field": "MONTH", "counts": [
            {"name": str(m), "count": total * (1 + (m % 3))} for m in range(1, 13)]}]}).encode()
    raise AssertionError(url)


def test_gibs_capabilities_and_urls():
    layers = gibs.parse_layers((FIX / "gibs_capabilities.xml").read_bytes())
    assert gibs.find_layer(layers, ["goes", "east", "geocolor"]) == "GOES-East_ABI_GeoColor"
    t = gibs.monthly_times(layers["BlueMarble_NextGeneration"]["time"])
    assert [d.month for d in t] == list(range(1, 13))
    u = gibs.getmap_url("L", (-110, -12, -55, 50), (100, 100), "2024-10-08", "image/jpeg")
    assert "BBOX=-12%2C-110%2C50%2C-55" in u  # lat-first for WMS 1.3.0 / EPSG:4326


def test_imagery_and_goes_download(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "IMG_DIR", tmp_path)
    r = pipeline.fetch_imagery(mock_http, res=1.0, out_dir=tmp_path)
    assert len(r["bluemarble"]["files"]) == 12 and len(r["ndvi"]["files"]) == 12
    g = pipeline.fetch_goes(mock_http, days=1, step_hours=6, res=0.5, out_dir=tmp_path)
    assert len(g["frames"]) == 5
    m = json.loads((tmp_path / "manifest.json").read_text())
    assert {"bluemarble", "ndvi", "goes"} <= set(m)


def test_observations_pipeline(tmp_path):
    prov = pipeline.fetch_observations(mock_http, ["wood-thrush"], cell=5.0, workers=2,
                                       cache_dir=tmp_path / "c", out_dir=tmp_path / "o")
    assert prov["wood-thrush"]["records_in_region"] > 0
    fr = (tmp_path / "o" / "wood-thrush.frames.u8").read_bytes()
    assert len(fr) == simulate.WEEKS * simulate.HEIGHT * simulate.WIDTH
    a = json.loads((tmp_path / "o" / "wood-thrush.analysis.json").read_text())
    assert a["kind"] == "observed" and len(a["moving_share"]) == 52


def test_month_interpolation_periodic():
    a = np.ones((12, 2, 2)) * 5.0
    a[6] = 11.0                                   # a July peak
    w = observed.months_to_weeks(a)
    assert w.shape[0] == 52 and w.min() >= 5.0 - 1e-9 and w.max() <= 11.0 + 1e-9
    assert int(np.argmax(w[:, 0, 0])) in range(25, 29)      # peak lands in early July
    assert abs(w[0, 0, 0] - w[-1, 0, 0]) < 1e-6              # December and January agree: periodic


def test_movebank_loader(tmp_path):
    p = tmp_path / "t.csv"
    rows = ["timestamp,location-long,location-lat"] + [f"2023-10-0{d} 1{h}:00:00.000,{-80 - d - h * 0.01},{40 - d}" for d in range(1, 6) for h in range(0, 3)]
    p.write_text("\n".join(rows))
    t = load_movebank_csv(p)
    assert t["source"] == "movebank" and len(t["points"]) >= 5


def test_monthly_times_covers_all_twelve_months_for_8day_layers():
    from datetime import datetime, timezone
    ext = [(datetime(2000, 2, 18, tzinfo=timezone.utc), datetime(2026, 10, 20, tzinfo=timezone.utc), "P8D")]
    assert [d.month for d in gibs.monthly_times(ext)] == list(range(1, 13))
