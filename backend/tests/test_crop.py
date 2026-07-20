"""
Tests for crop classification: feature-building helpers and the
API-facing classify_crop() mock path. Real model inference tests
should be added once a trained checkpoint exists.
"""
import numpy as np

from app.models.crop_classifier import (
    build_temporal_spectral_profile,
    extract_textural_features,
    classify_crop,
)
from app.schemas.crop_schema import CropClassificationRequest


def test_build_temporal_spectral_profile_shape():
    profile = build_temporal_spectral_profile([0.3, 0.5, 0.6], [0.1, 0.2, 0.15])
    # 3 ndvi + 3 ndwi + 3 ndvi stats + 3 ndwi stats = 12
    assert profile.shape == (12,)


def test_extract_textural_features_returns_three_values():
    band = np.random.rand(8, 8)
    features = extract_textural_features(band)
    assert features.shape == (3,)
    assert all(np.isfinite(features))


def test_classify_crop_returns_valid_result_with_or_without_checkpoint():
    """
    Works whether a real checkpoint is present (real model inference)
    or not (mock fallback) — both paths must return a valid, complete
    CropClassificationResult.
    """
    request = CropClassificationRequest(
        field_id="F-TEST", latitude=29.0, longitude=77.0, acquisition_date="2026-06-01"
    )
    result = classify_crop(request)
    assert result.field_id == "F-TEST"
    assert 0.0 <= result.confidence <= 1.0
    assert result.predicted_crop
