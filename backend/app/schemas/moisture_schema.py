"""
Pydantic models for moisture stress detection: request carries
the field + time window, response carries the moisture index,
its stress category, and which sensor(s) actually produced it
(SAR, optical, or fused) — this last part is what proves the
system kept working through cloud cover.
"""
from datetime import date
from pydantic import BaseModel, Field


class MoisturePoint(BaseModel):
    date: date
    moisture_value: float = Field(..., ge=0.0, le=100.0)
    source: str = Field(..., description="'sar', 'optical', or 'fused'")


class MoistureRequest(BaseModel):
    field_id: str
    start_date: date
    end_date: date


class MoistureResult(BaseModel):
    field_id: str
    stress_level: str = Field(..., description="'adequate', 'moderate-stress', or 'high-stress'")
    current_value: float
    timeline: list[MoisturePoint]
