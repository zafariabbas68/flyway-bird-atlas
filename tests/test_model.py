import numpy as np

from flyway import simulate
from flyway.geo import haversine_km, polyline_length_km, polyline_position
from flyway.species_data import SPECIES


def test_haversine_known_distance():
    # New York to London is about 5,570 km
    d = float(haversine_km(-74.0, 40.7, -0.12, 51.5))
    assert 5500 < d < 5650


def test_polyline_position_endpoints():
    pts = [(-90, 20), (-90, 30), (-85, 40)]
    assert np.allclose(polyline_position(pts, 0.0), pts[0])
    assert np.allclose(polyline_position(pts, 1.0), pts[-1])
    assert polyline_length_km(pts) > 2000


def test_species_definitions_are_complete():
    ids = [s["id"] for s in SPECIES]
    assert len(ids) == len(set(ids)) == 7
    for s in SPECIES:
        assert len(s["steps"]) == 5 and s["steps"][0]["week"] is None
        assert all(0 <= st["week"] <= 51 for st in s["steps"][1:])


def test_simulation_shape_and_seasonality():
    spec = next(s for s in SPECIES if s["id"] == "wood-thrush")
    res = simulate.simulate_species(spec, n=1500)
    assert res.frames.shape == (52, simulate.HEIGHT, simulate.WIDTH)
    assert res.frames.dtype == np.uint8 and res.frames.max() == 255
    lat = res.analysis["centroid_lat"]
    # summer centroid is well north of winter centroid
    assert lat[26] - lat[2] > 8
    # most birds are stationary in midwinter and midsummer
    assert res.analysis["moving_share"][2] < 0.05
    assert res.analysis["moving_share"][26] < 0.05


def test_simulation_is_deterministic():
    spec = SPECIES[0]
    a = simulate.simulate_species(spec, n=800).frames
    b = simulate.simulate_species(spec, n=800).frames
    assert np.array_equal(a, b)


def test_hawk_is_more_synchronised_than_sparrow():
    by = {s["id"]: s for s in SPECIES}
    hawk = simulate.simulate_species(by["broad-winged-hawk"], n=1500).analysis["moving_share"]
    sparrow = simulate.simulate_species(by["white-throated-sparrow"], n=1500).analysis["moving_share"]
    assert max(hawk) > max(sparrow) - 0.05
