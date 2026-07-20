"""
Tests for command-area aggregation — verifies the canal-command
-area-level rollup (spec's explicit requirement) correctly
aggregates real per-field advisories rather than just listing them.
"""
from datetime import date

import pytest

from app.models.command_area import generate_command_area_advisory, list_command_areas


def test_list_command_areas_returns_real_area():
    areas = list_command_areas()
    assert len(areas) >= 1
    assert any(a["area_id"] == "CA-KPT01" for a in areas)


def test_generate_command_area_advisory_aggregates_all_fields():
    result = generate_command_area_advisory("CA-KPT01", reference_date=date(2025, 1, 20))
    assert result.total_fields == 59
    assert len(result.fields) == 59
    assert 0 <= result.fields_at_risk_pct <= 100


def test_command_area_total_volume_matches_sum_of_field_deficits():
    result = generate_command_area_advisory("CA-KPT01", reference_date=date(2025, 1, 20))
    manual_sum = round(sum(f.advisory.amount_mm or 0.0 for f in result.fields), 1)
    assert result.total_irrigation_volume_mm == manual_sum


def test_generate_command_area_advisory_unknown_area_raises():
    with pytest.raises(KeyError):
        generate_command_area_advisory("CA-NONEXISTENT")
