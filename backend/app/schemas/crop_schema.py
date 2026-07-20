"""
Pydantic models for crop-type classification: what the API
accepts as input (a field's location + imagery reference) and
what it returns (predicted crop, growth stage, confidence).
"""
from pydantic import BaseModel, Field


class CropClassificationRequest(BaseModel):
    field_id: str
    latitude: float
    longitude: float
    acquisition_date: str = Field(..., description="ISO date of the satellite pass used")


class CropClassificationResult(BaseModel):
    field_id: str
    predicted_crop: str
    growth_stage: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    source_bands: list[str] = Field(default_factory=list, description="Spectral bands used, e.g. NDVI, NDWI")
