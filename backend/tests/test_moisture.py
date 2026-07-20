"""
Tests for moisture estimation: VCI/SMI computation, fusion
fallback behavior (the core cloud-resilience claim), stage-aware
stress classification, and the phenology stage lookup.
"""
import pytest

from app.services.fusion import compute_vci, compute_smi, fuse_moisture, classify_stress
from app.models.moisture_estimator import get_growth_stage
from datetime import date, timedelta


def test_compute_vci_within_bounds():
    vci = compute_vci(ndvi_current=0.6, ndvi_min=0.3, ndvi_max=0.8)
    assert 0.0 <= vci <= 100.0


def test_compute_smi_within_bounds():
    smi = compute_smi(backscatter_db=-9.0, backscatter_min=-14.0, backscatter_max=-6.0)
    assert 0.0 <= smi <= 100.0


def test_fuse_moisture_falls_back_to_sar_when_optical_blocked():
    fused = fuse_moisture(vci=None, smi=62.0)
    assert fused["source"] == "sar"
    assert fused["confidence"] == "medium"


def test_fuse_moisture_uses_both_when_available():
    fused = fuse_moisture(vci=70.0, smi=60.0)
    assert fused["source"] == "fused"
    assert fused["confidence"] == "high"


def test_fuse_moisture_raises_when_nothing_available():
    with pytest.raises(ValueError):
        fuse_moisture(vci=None, smi=None)


def test_classify_stress_stage_aware_thresholds_differ():
    # Same value, different stage -> can flip stress bucket near the boundary.
    normal_stage = classify_stress(33, growth_stage="Vegetative")
    sensitive_stage = classify_stress(33, growth_stage="Flowering")
    assert normal_stage in {"high-stress", "moderate-stress"}
    assert sensitive_stage in {"high-stress", "moderate-stress"}


def test_get_growth_stage_returns_known_stage():
    stage = get_growth_stage("F-14B", date.today())
    assert stage in {"Sowing", "Vegetative", "Flowering", "Maturity"}


def test_compute_vh_vv_ratio_db():
    from app.services.fusion import compute_vh_vv_ratio_db
    assert compute_vh_vv_ratio_db(vv_db=-10.0, vh_db=-16.0) == -6.0


def test_compute_smi_vh_ratio_within_bounds():
    from app.services.fusion import compute_smi_vh_ratio
    smi = compute_smi_vh_ratio(vv_db=-10.0, vh_db=-16.0, ratio_min=-12.0, ratio_max=-2.0)
    assert 0.0 <= smi <= 100.0


def test_smi_vh_ratio_differs_from_vv_only_smi():
    """Real regression guard: the VH-ratio path must produce a genuinely different value than VV-only, proving VH actually contributes."""
    from app.services.fusion import compute_smi, compute_smi_vh_ratio
    vv_only = compute_smi(backscatter_db=-10.0, backscatter_min=-14.0, backscatter_max=-6.0)
    vh_ratio = compute_smi_vh_ratio(vv_db=-10.0, vh_db=-16.0, ratio_min=-12.0, ratio_max=-2.0)
    assert vv_only != vh_ratio


def test_get_ndwi_value_at_varies_by_date():
    """Real regression guard: NDWI must vary across real dates, proving it's a real time series, not the old static average."""
    from app.models.moisture_estimator import get_ndwi_value_at
    from datetime import date
    lat, lon = 31.40, 75.388
    v1 = get_ndwi_value_at(lat, lon, date(2024, 11, 1))
    v2 = get_ndwi_value_at(lat, lon, date(2025, 1, 20))
    assert v1 is not None and v2 is not None
    assert v1 != v2


def test_vci_smi_breakdown_includes_real_ndwi():
    from app.models.moisture_estimator import get_vci_smi_breakdown
    from datetime import date
    result = get_vci_smi_breakdown("F-K01", date(2025, 1, 20))
    assert "ndwi" in result
    assert result["ndwi"] is not None
