import math

from backend.app.geo import haversine_nm


def test_haversine_nm_distance_sf_to_la():
    """Distance between KSFO (~37.6213, -122.3790) and KLAX (~33.9416, -118.4085) should be ~294 NM."""
    d_nm = haversine_nm(37.6213, -122.3790, 33.9416, -118.4085)
    assert math.isclose(d_nm, 294, rel_tol=0.02)


def test_haversine_nm_zero_distance():
    d_nm = haversine_nm(40.0, -120.0, 40.0, -120.0)
    assert d_nm == 0

