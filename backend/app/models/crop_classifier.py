"""
Crop-type classification model wrapper — aligned to the real
trained checkpoint built from GEE-extracted Sentinel-1/2 features
(NDVI, NDWI, VV, VH) over the Kapurthala AOI, using ESA WorldCereal
as the crop-type label proxy. Falls back to mock predictions if no
checkpoint exists, so the API never breaks during early development.

Note: the multi-temporal spectral-profile / GLCM-texture helpers
below are kept for future use (e.g. once a richer labeled dataset
with multiple time steps is available), but current inference uses
the simpler real feature set the trained checkpoint was fit on.
"""
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, cohen_kappa_score

from app.core.config import get_settings
from app.core.logger import get_logger
from app.schemas.crop_schema import CropClassificationRequest, CropClassificationResult

logger = get_logger(__name__)
settings = get_settings()

_MOCK_CACHE: dict[str, CropClassificationResult] = {}
_MODEL: RandomForestClassifier | None = None

# Real checkpoint's feature order — must match the columns used in
# the Colab/GEE reshape step (ndvi_t1, ndwi_t1, vv, vh).
REAL_FEATURE_COLUMNS = ["ndvi", "ndwi", "vv", "vh"]


def _checkpoint_path() -> Path:
    return Path(settings.model_checkpoint_dir) / "crop_classifier.pkl"


def _load_model() -> RandomForestClassifier | None:
    global _MODEL
    if _MODEL is not None:
        return _MODEL
    checkpoint = _checkpoint_path()
    if not checkpoint.exists():
        return None
    _MODEL = joblib.load(checkpoint)
    logger.info("Loaded crop classifier checkpoint from %s", checkpoint)
    return _MODEL


def build_temporal_spectral_profile(ndvi_series: list[float], ndwi_series: list[float]) -> np.ndarray:
    """
    Builds a multi-temporal spectral profile feature vector — kept
    for future use once a multi-date labeled dataset is available.
    Not used by the current real-data checkpoint (single-snapshot).
    """
    ndvi = np.array(ndvi_series, dtype=float)
    ndwi = np.array(ndwi_series, dtype=float)
    return np.concatenate([
        ndvi,
        ndwi,
        [ndvi.mean(), ndvi.max(), ndvi.std()],
        [ndwi.mean(), ndwi.max(), ndwi.std()],
    ])


def extract_textural_features(band: np.ndarray) -> np.ndarray:
    """GLCM-style textural features — kept for future use, not used by the current real checkpoint."""
    flat = band.flatten()
    contrast = float(np.var(flat))
    homogeneity = float(1.0 / (1.0 + contrast))
    energy = float(np.mean(flat ** 2))
    return np.array([contrast, homogeneity, energy])


def train_model(features: np.ndarray, labels: np.ndarray) -> RandomForestClassifier:
    """Trains the Random Forest on whatever feature set is passed in."""
    model = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42, class_weight="balanced")
    model.fit(features, labels)
    return model


def validate_model(model: RandomForestClassifier, features: np.ndarray, ground_truth_labels: np.ndarray) -> dict:
    """Returns Overall Accuracy + Kappa coefficient against ground-truth samples, per spec."""
    predictions = model.predict(features)
    return {
        "overall_accuracy": round(accuracy_score(ground_truth_labels, predictions), 3),
        "kappa": round(cohen_kappa_score(ground_truth_labels, predictions), 3),
    }


def classify_crop(request: CropClassificationRequest) -> CropClassificationResult:
    model = _load_model()
    if model is None:
        logger.warning("No crop classifier checkpoint found — returning mock prediction")
        result = _mock_prediction(request)
        _MOCK_CACHE[request.field_id] = result
        return result

    # Live path: uses the SAME real NDVI/VV/VH data sources that
    # power moisture_estimator (get_ndvi_value_at, get_vv_value_at,
    # get_vh_value_at) — previously this checked unrelated mock
    # fetchers and used a fixed placeholder feature array, which
    # gave a coincidentally-correct answer without actually using
    # real per-field data.
    from datetime import date as _date
    from app.models.moisture_estimator import get_ndvi_value_at, get_vv_value_at, get_vh_value_at

    target_date = _date.fromisoformat(request.acquisition_date) if request.acquisition_date else _date.today()
    real_ndvi = get_ndvi_value_at(request.field_id, request.latitude, request.longitude, target_date)
    real_vv = get_vv_value_at(request.latitude, request.longitude, target_date)
    real_vh = get_vh_value_at(request.latitude, request.longitude, target_date)

    if real_ndvi is None or real_vv is None or real_vh is None:
        logger.warning("No real NDVI/VV/VH observation near %s for field %s — returning mock prediction",
                        target_date, request.field_id)
        result = _mock_prediction(request)
        _MOCK_CACHE[request.field_id] = result
        return result

    # Real per-date NDWI lookup (gee_ndwi_timeseries.js export), closing
    # the earlier gap where this was a single static dataset-wide
    # average. Falls back to that average only if no real observation
    # is found near this date/location.
    from app.models.moisture_estimator import get_ndwi_value_at

    real_ndwi = get_ndwi_value_at(request.latitude, request.longitude, target_date)
    if real_ndwi is None:
        real_ndwi = _get_real_average_ndwi()

    features = np.array([[real_ndvi, real_ndwi, real_vv, real_vh]])
    prediction = model.predict(features)[0]
    confidence = float(model.predict_proba(features).max())

    # Real growth stage from the same SOS-based phenology function the
    # advisory engine uses — previously hardcoded to "Unknown" here on
    # the (correct, but easy to misread) assumption that nothing calls
    # this endpoint for growth stage. Anyone inspecting this endpoint
    # directly (e.g. via /docs) would see a field that looks dead/
    # broken; wiring it up removes that false signal at negligible
    # extra cost (the phenology cache is already warm by this point).
    from app.models.moisture_estimator import get_phenology_details
    try:
        growth_stage = get_phenology_details(request.field_id, target_date)["growth_stage"]
    except Exception:
        growth_stage = "Unknown"

    result = CropClassificationResult(
        field_id=request.field_id,
        predicted_crop=str(prediction),
        growth_stage=growth_stage,
        confidence=round(confidence, 3),
        source_bands=REAL_FEATURE_COLUMNS,
    )
    _MOCK_CACHE[request.field_id] = result
    return result


_average_ndwi_cache: float | None = None


def _get_real_average_ndwi(csv_path: str = "data/labels/crop_ground_truth_real.csv") -> float:
    """Real average NDWI from the single-snapshot ground-truth dataset — a disclosed proxy, not per-field/date."""
    global _average_ndwi_cache
    if _average_ndwi_cache is not None:
        return _average_ndwi_cache
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        _average_ndwi_cache = float(df["ndwi_t1"].mean())
    except FileNotFoundError:
        _average_ndwi_cache = 0.55  # last-resort fallback if even the snapshot dataset is missing
    return _average_ndwi_cache


def get_cached_classification(field_id: str) -> CropClassificationResult | None:
    return _MOCK_CACHE.get(field_id)


def _mock_prediction(request: CropClassificationRequest) -> CropClassificationResult:
    return CropClassificationResult(
        field_id=request.field_id,
        predicted_crop="Wintercereal_Wheat_or_Mustard",
        growth_stage="Tillering",
        confidence=0.81,
        source_bands=REAL_FEATURE_COLUMNS,
    )


_RICE_WHEAT_MODEL: RandomForestClassifier | None = None


def _load_rice_wheat_model() -> RandomForestClassifier | None:
    global _RICE_WHEAT_MODEL
    if _RICE_WHEAT_MODEL is not None:
        return _RICE_WHEAT_MODEL
    checkpoint = Path(settings.model_checkpoint_dir) / "rice_wheat_classifier.pkl"
    if not checkpoint.exists():
        return None
    _RICE_WHEAT_MODEL = joblib.load(checkpoint)
    logger.info("Loaded rice-wheat classifier from %s", checkpoint)
    return _RICE_WHEAT_MODEL


def classify_rice_wheat(kharif_ndvi: float, kharif_vv: float, kharif_vh: float, rabi_ndvi: float) -> dict:
    """
    Multi-class rice vs wheat classification using the real Kharif-
    season features. Returns the predicted class and confidence.
    Falls back cleanly if checkpoint doesn't exist.
    """
    model = _load_rice_wheat_model()
    if model is None:
        return {"predicted_crop_multiclass": None, "confidence_multiclass": None}

    features = [[kharif_ndvi, kharif_vv, kharif_vh, rabi_ndvi]]
    prediction = model.predict(features)[0]
    confidence = round(float(model.predict_proba(features).max()), 3)
    return {"predicted_crop_multiclass": str(prediction), "confidence_multiclass": confidence}
