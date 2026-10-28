import pytest

from flyway import create_app
from flyway import simulate


@pytest.fixture(scope="module")
def client():
    return create_app().test_client()


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200 and b"Flyway" in r.data


def test_meta(client):
    j = client.get("/api/meta").get_json()
    assert len(j["species"]) == 7 and j["grid"]["weeks"] == 52
    assert "not eBird" in j["data_note"]


def test_frames_binary_size(client):
    r = client.get("/api/species/wood-thrush/frames.bin")
    assert r.status_code == 200
    assert len(r.data) == simulate.WEEKS * simulate.HEIGHT * simulate.WIDTH


def test_unknown_species_404(client):
    assert client.get("/api/species/dodo").status_code == 404
    assert client.get("/api/species/dodo/frames.bin").status_code == 404
    assert client.get("/api/species/dodo/analysis").status_code == 404


def test_basemap_and_track(client):
    assert client.get("/api/basemap").get_json()["features"]
    t = client.get("/api/track/hawk").get_json()
    assert len(t["points"]) > 100
    assert "Not a tagged bird" in t["note"]


def test_compare(client):
    rows = client.get("/api/compare").get_json()
    assert len(rows) == 7 and all("summary" in r for r in rows)
