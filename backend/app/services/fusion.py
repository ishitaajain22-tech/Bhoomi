"""
Computes the spec-named stress indices — Vegetation Condition
Index (VCI) from optical NDVI history and Soil Moisture Index
(SMI) from SAR backscatter — then fuses them into a stage-aware
stress classification. Replaces the earlier generic "fused
moisture index" with the exact indices the problem statement
names under "Moisture Stress Detection".
"""
from app.core.logger import get_logger

logger = get_logger(__name__)

# Relative weight when both VCI and SMI are available. SMI carries
# slightly more weight because SAR is the all-weather fallback.
VCI_WEIGHT = 0.45
SMI_WEIGHT = 0.55


def compute_vci(ndvi_current: float, ndvi_min: float, ndvi_max: float) -> float:
    """
    Vegetation Condition Index: positions current NDVI within its
    historical min-max range for the same period, 0-100 scale.
    Standard VCI formula per the spec.
    """
    if ndvi_max == ndvi_min:
        return 50.0
    vci = (ndvi_current - ndvi_min) / (ndvi_max - ndvi_min) * 100
    return round(max(0.0, min(100.0, vci)), 1)


def compute_smi(backscatter_db: float, backscatter_min: float, backscatter_max: float) -> float:
    """
    Soil Moisture Index from VV alone, positioned within its
    historical range, 0-100 scale. Kept as the fallback path when
    VH isn't available; compute_smi_vh_ratio below is preferred
    when both VV and VH are present (matches the spec's named
    "Ratio (VH/VV)" SAR feature, more robust to surface-roughness
    noise than VV alone).
    """
    if backscatter_max == backscatter_min:
        return 50.0
    smi = (backscatter_db - backscatter_min) / (backscatter_max - backscatter_min) * 100
    return round(max(0.0, min(100.0, smi)), 1)


def compute_vh_vv_ratio_db(vv_db: float, vh_db: float) -> float:
    """VH/VV ratio in dB-difference form (vh - vv), the spec's named cross-polarization SAR feature."""
    return vh_db - vv_db


def compute_smi_vh_ratio(
    vv_db: float, vh_db: float, ratio_min: float, ratio_max: float
) -> float:
    """
    Soil Moisture Index from the real VH/VV cross-polarization
    ratio, not VV alone. Cross-pol ratio is more sensitive to
    vegetation/soil moisture structure than co-pol VV alone, and
    is exactly the "Ratio (VH/VV)" feature the spec names under
    SAR features — this closes a real gap where VH was fetched
    but never actually used in stress calculation.
    """
    ratio = compute_vh_vv_ratio_db(vv_db, vh_db)
    if ratio_max == ratio_min:
        return 50.0
    smi = (ratio - ratio_min) / (ratio_max - ratio_min) * 100
    return round(max(0.0, min(100.0, smi)), 1)


def fuse_moisture(vci: float | None, smi: float | None) -> dict:
    """
    Returns {"value": float, "source": "fused"|"sar"|"optical", "confidence": "high"|"medium"}.
    SMI (SAR-derived) is used alone when optical/VCI is cloud-blocked —
    this fallback is what keeps stress detection alive through monsoon clouds.
    """
    if vci is None and smi is None:
        raise ValueError("No usable signal from either VCI or SMI")

    if vci is not None and smi is not None:
        value = SMI_WEIGHT * smi + VCI_WEIGHT * vci
        return {"value": round(value, 1), "source": "fused", "confidence": "high"}

    if smi is not None:
        logger.info("VCI unavailable (cloud-blocked) — falling back to SMI-only stress estimate")
        return {"value": round(smi, 1), "source": "sar", "confidence": "medium"}

    logger.info("SMI unavailable — falling back to VCI-only stress estimate")
    return {"value": round(vci, 1), "source": "optical", "confidence": "medium"}


def classify_stress(moisture_value: float, growth_stage: str | None = None) -> str:
    """
    Buckets the fused 0-100 index into stress categories. Thresholds
    shift slightly by growth stage since the same index value means
    different things at flowering vs. maturity (stage-wise stress
    interpretation, per spec).
    """
    sensitive_stages = {"Flowering", "Boll formation", "Panicle initiation", "Grand growth"}
    high_cut, mod_cut = (35, 58) if growth_stage in sensitive_stages else (30, 55)

    if moisture_value < high_cut:
        return "high-stress"
    if moisture_value < mod_cut:
        return "moderate-stress"
    return "adequate"
