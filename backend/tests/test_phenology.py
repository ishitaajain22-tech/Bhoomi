"""
Tests for real SOS-based phenology detection — verifies the
threshold-crossing logic against synthetic but realistic NDVI
curves (fallow -> green-up -> peak -> senescence), since this is
the core algorithm the spec's phenology block depends on.
"""
from datetime import date, timedelta

from app.services.phenology import detect_sos, detect_peak_growth, classify_stage_from_sos, estimate_phenology


def _build_synthetic_curve(start: date, n_points: int = 30, step_days: int = 5):
    dates, ndvi = [], []
    for i in range(n_points):
        d = start + timedelta(days=i * step_days)
        day_offset = i * step_days
        if day_offset < 50:
            val = 0.15
        elif day_offset < 100:
            val = 0.2 + 0.6 * ((day_offset - 50) / 50)
        else:
            val = 0.8 - 0.3 * ((day_offset - 100) / 50)
        dates.append(d)
        ndvi.append(val)
    return dates, ndvi


def test_detect_sos_finds_greenup_crossing():
    dates, ndvi = _build_synthetic_curve(date(2024, 10, 1))
    sos = detect_sos(dates, ndvi)
    assert sos is not None
    assert date(2024, 11, 20) <= sos <= date(2024, 12, 15)  # green-up window


def test_detect_sos_returns_none_for_flat_series():
    dates = [date(2024, 10, 1) + timedelta(days=i * 5) for i in range(10)]
    ndvi = [0.1] * 10  # never greens up
    assert detect_sos(dates, ndvi) is None


def test_detect_peak_growth_finds_max():
    dates, ndvi = _build_synthetic_curve(date(2024, 10, 1))
    sos = detect_sos(dates, ndvi)
    peak = detect_peak_growth(dates, ndvi, sos=sos)
    assert peak is not None
    assert peak >= sos
    assert date(2024, 12, 20) <= peak <= date(2025, 1, 20)


def test_detect_peak_growth_ignores_pre_sos_residual_high_ndvi():
    """
    Real exported field data showed leftover high NDVI from a prior
    season right before harvest/fallow, which must NOT be picked as
    this season's peak. Simulate that exact pattern here.
    """
    dates = [date(2024, 10, 1) + timedelta(days=i * 5) for i in range(20)]
    ndvi = [0.8, 0.75, 0.6, 0.5, 0.1, 0.08, 0.06, 0.07, 0.1, 0.18,
            0.33, 0.44, 0.55, 0.58, 0.85, 0.7, 0.4, 0.2, 0.15, 0.11]
    sos = detect_sos(dates, ndvi)
    peak = detect_peak_growth(dates, ndvi, sos=sos)
    assert peak >= sos  # must not land in the early pre-SOS high-NDVI noise


def test_classify_stage_defaults_safely_without_sos():
    stage = classify_stage_from_sos(None, date(2025, 1, 1))
    assert stage == "Vegetative"


def test_classify_stage_progresses_with_days_after_sos():
    sos = date(2024, 12, 1)
    assert classify_stage_from_sos(sos, sos + timedelta(days=5)) == "Sowing"
    assert classify_stage_from_sos(sos, sos + timedelta(days=30)) == "Vegetative"
    assert classify_stage_from_sos(sos, sos + timedelta(days=60)) == "Flowering"
    assert classify_stage_from_sos(sos, sos + timedelta(days=130)) == "Maturity"


def test_estimate_phenology_full_pipeline():
    dates, ndvi = _build_synthetic_curve(date(2024, 10, 1))
    result = estimate_phenology(dates, ndvi, on_date=dates[-1])
    assert result["sos_date"] is not None
    assert result["peak_growth_date"] is not None
    assert result["growth_stage"] in {"Sowing", "Vegetative", "Flowering", "Maturity"}
    assert result["days_after_sos"] >= 0


def test_load_real_sar_timeseries_groups_by_stable_point_index(tmp_path):
    """
    Regression test for a real bug: grouping SAR points by exact
    coordinates failed because per-image reprojection causes small
    coordinate drift (~hundreds of meters) for the same physical
    point across dates. Verifies system:index-based grouping
    produces multi-date series, not single-observation series.
    """
    import pandas as pd
    from app.services.phenology import load_real_sar_timeseries

    csv_path = tmp_path / "fake_sar.csv"
    rows = []
    for date_str, vv_base in [("2024-10-02", -12.0), ("2024-10-08", -11.0), ("2024-10-14", -13.0)]:
        for point_idx in range(3):
            # Simulate small coordinate drift per date, same point_idx
            lon = 75.388 + point_idx * 0.001 + 0.00001 * hash(date_str) % 5
            lat = 31.400 + point_idx * 0.001
            rows.append({
                "system:index": f"S1A_FAKE_{date_str}_{point_idx}_0",
                "VV": vv_base + point_idx,
                "VH": vv_base - 5 + point_idx,
                "date": date_str,
                ".geo": f'{{"type":"Point","coordinates":[{lon},{lat}]}}',
            })
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    series = load_real_sar_timeseries(str(csv_path))
    assert len(series) == 3  # 3 distinct points
    for point_id, (dates, vv_values, vh_values) in series.items():
        assert len(dates) == 3  # each point has all 3 real dates, not 1
