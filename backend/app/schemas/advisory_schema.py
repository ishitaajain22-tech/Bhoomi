"""
Pydantic models for the irrigation advisory — the final, plain
-language output the farmer actually sees. Wraps the underlying
crop + moisture results into one actionable recommendation with
a stated confidence and reasoning, so the API never returns a
bare number without context.
"""
from pydantic import BaseModel, Field


class AdvisoryResult(BaseModel):
    field_id: str
    predicted_crop: str
    predicted_crop_multiclass: str | None = None
    confidence_multiclass: float | None = None
    growth_stage: str
    sos_date: str | None = Field(None, description="Detected Start-of-Season date (ISO), or null if undetected")
    peak_growth_date: str | None = Field(None, description="Detected peak-growth date (ISO), or null if undetected")
    days_after_sos: int | None = None
    vci: float | None = Field(None, description="Vegetation Condition Index, 0-100, from real NDVI")
    smi: float | None = Field(None, description="Soil Moisture Index, 0-100, from real SAR VH/VV ratio")
    ndwi: float | None = Field(None, description="Real per-date NDWI from real Sentinel-2 Green/NIR time series")
    moisture_value: float
    stress_level: str = Field(..., description="'adequate', 'moderate-stress', or 'high-stress'")
    eto_mm_per_day: float
    etc_mm: float = Field(..., description="8-day crop water demand")
    rainfall_mm: float = Field(..., description="Real 8-day cumulative rainfall")
    deficit_mm: float
    action: str = Field(..., description="e.g. 'Irrigate within 48 hours' or 'No irrigation needed'")
    amount_mm: float | None = Field(None, description="Recommended irrigation depth in millimetres")
    reason: str
    confidence: str = Field(..., description="'high', 'medium', or 'low'")
    data_source: str = Field(..., description="'SAR (Sentinel-1)', 'Optical (Sentinel-2)', or 'Fused (S1 + S2)'")
