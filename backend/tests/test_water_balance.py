"""
Tests for water_balance.py — verifies real-data point grouping
(same system:index-based fix needed for SAR) and the fallback
behavior when no real rainfall/ETo export exists yet, so the
advisory pipeline never breaks regardless of data availability.
"""
import json
from datetime import date, datetime

import pandas as pd

from app.services.water_balance import (
    _load_point_series,
    get_rainfall_8day_mm,
    get_eto_mm_per_day,
    compute_etc,
    compute_water_deficit,
)


def _write_fake_series_csv(tmp_path, value_column: str, value_by_date: dict):
    rows = []
    for point_idx in range(2):
        lon = 75.388 + point_idx * 0.01  # distinct coordinates per point
        lat = 31.400 + point_idx * 0.01
        for date_str, val in value_by_date.items():
            rows.append({
                "system:index": f"FAKE_{date_str}_{point_idx}_0",
                value_column: val + point_idx,
                "date": date_str,
                ".geo": f'{{"type":"Point","coordinates":[{lon},{lat}]}}',
            })
    path = tmp_path / f"fake_{value_column}.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return str(path)


def test_load_point_series_groups_by_stable_index(tmp_path):
    csv_path = _write_fake_series_csv(tmp_path, "precipitation", {"2024-10-02": 5.0, "2024-10-03": 8.0})
    series = _load_point_series(csv_path, "precipitation")
    assert len(series) == 2  # 2 distinct points
    for point_id, (dates, values) in series.items():
        assert len(dates) == 2  # both real dates present, not collapsed to 1


def test_get_rainfall_falls_back_when_no_real_csv():
    # Nonexistent point far from any cached data -> fallback constant.
    rainfall = get_rainfall_8day_mm(lat=0.0, lon=0.0, end_date=date(2099, 1, 1))
    assert rainfall > 0  # fallback constant, not zero/crash


def test_get_eto_falls_back_when_no_real_csv():
    eto = get_eto_mm_per_day(lat=0.0, lon=0.0, on_date=date(2099, 1, 1))
    assert eto > 0


def test_compute_etc_scales_with_eto():
    etc_low = compute_etc("Flowering", eto_mm_per_day=3.0, window_days=8)
    etc_high = compute_etc("Flowering", eto_mm_per_day=6.0, window_days=8)
    assert etc_high > etc_low


def test_compute_water_deficit_basic():
    assert compute_water_deficit(etc_mm=25.0, rainfall_mm=10.0) == 15.0
    assert compute_water_deficit(etc_mm=10.0, rainfall_mm=25.0) == -15.0


def test_get_eto_converts_mod16_pet_units_correctly(tmp_path, monkeypatch):
    """
    MOD16A2's PET band is an 8-day SUM in units of 0.1mm, not a
    daily mm/day value (unlike GRIDMET, which doesn't cover India
    and was replaced). Verifies the scale-factor + /8 conversion
    produces a sane mm/day figure rather than a raw 8-day total.
    """
    import pandas as pd
    import app.services.water_balance as wb

    rows = [{
        "system:index": "FAKE_2025-01-15_0_0",
        "PET": 240,  # raw MOD16 units: 240 * 0.1 = 24mm over 8 days -> 3.0 mm/day
        "date": "2025-01-15",
        ".geo": '{"type":"Point","coordinates":[75.388,31.400]}',
    }]
    csv_path = tmp_path / "fake_pet.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    monkeypatch.setattr(wb, "_ETO_CSV_PATH", str(csv_path))
    monkeypatch.setattr(wb, "_eto_cache", None)

    from datetime import date
    eto = wb.get_eto_mm_per_day_mod16(lat=31.400, lon=75.388, on_date=date(2025, 1, 15))
    assert eto == 3.0


def test_day_length_hours_longer_in_summer_than_winter():
    """Sanity check: day length should be longer near summer solstice than winter solstice, for a northern latitude."""
    from app.services.water_balance import day_length_hours
    winter_day_length = day_length_hours(latitude_deg=31.4, day_of_year=355)  # ~Dec 21
    summer_day_length = day_length_hours(latitude_deg=31.4, day_of_year=172)  # ~Jun 21
    assert summer_day_length > winter_day_length


def test_thornthwaite_monthly_pet_increases_with_temperature():
    from app.services.water_balance import compute_thornthwaite_monthly_pet
    cold_temps = {(2025, 1): 10.0, (2025, 2): 12.0, (2024, 12): 11.0}
    warm_temps = {(2025, 1): 25.0, (2025, 2): 27.0, (2024, 12): 24.0}

    cold_pet = compute_thornthwaite_monthly_pet(cold_temps, latitude=31.4)
    warm_pet = compute_thornthwaite_monthly_pet(warm_temps, latitude=31.4)

    assert warm_pet[(2025, 1)] > cold_pet[(2025, 1)]


def test_get_eto_thornthwaite_real_data_seasonal_pattern():
    """
    Using the real uploaded ERA5-Land temperature data: ETo should
    be lower in cold January than in warmer October/March, which is
    the physically correct seasonal pattern for northern India.
    """
    from app.services.water_balance import get_eto_mm_per_day_thornthwaite

    lat, lon = 31.40, 75.388
    eto_jan = get_eto_mm_per_day_thornthwaite(lat, lon, date(2025, 1, 15))
    eto_oct = get_eto_mm_per_day_thornthwaite(lat, lon, date(2024, 10, 15))
    assert eto_jan < eto_oct
    assert eto_jan > 0
