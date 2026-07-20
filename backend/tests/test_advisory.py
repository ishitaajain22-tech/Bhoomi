"""
Tests for the advisory engine: ETc computation, water-deficit
math, and the deficit-to-action translation. These are the
calculations that back the spec's "8-day crop water deficit and
irrigation advisory" requirement, so they're worth covering
directly rather than only via the full generate_advisory() path.
"""
from app.models.advisory_engine import compute_etc, compute_water_deficit, deficit_to_advisory


def test_compute_etc_uses_kc_for_stage():
    etc_flowering = compute_etc("Flowering", eto_mm_per_day=4.5, window_days=8)
    etc_sowing = compute_etc("Sowing", eto_mm_per_day=4.5, window_days=8)
    assert etc_flowering > etc_sowing  # Kc is higher at flowering than sowing


def test_compute_water_deficit_positive_when_demand_exceeds_rainfall():
    deficit = compute_water_deficit(etc_mm=30.0, rainfall_mm=10.0)
    assert deficit == 20.0


def test_compute_water_deficit_negative_means_surplus():
    deficit = compute_water_deficit(etc_mm=20.0, rainfall_mm=35.0)
    assert deficit < 0


def test_deficit_to_advisory_no_irrigation_when_surplus():
    action, amount = deficit_to_advisory(-5.0)
    assert action == "No irrigation needed"
    assert amount is None


def test_deficit_to_advisory_urgent_when_large_deficit():
    action, amount = deficit_to_advisory(25.0)
    assert action == "Irrigate within 48 hours"
    assert amount == 25.0


def test_deficit_to_advisory_moderate_when_small_deficit():
    action, amount = deficit_to_advisory(10.0)
    assert action == "Irrigate within 4 days"
    assert amount == 10.0
