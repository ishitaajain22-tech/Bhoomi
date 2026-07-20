"""
Pydantic models for command-area level output — aggregating
field-level advisories into the canal-command-area planning view
the spec explicitly asks for ("irrigation advisory maps for canal
command areas"), rather than only per-field results.
"""
from pydantic import BaseModel, Field

from app.schemas.advisory_schema import AdvisoryResult


class CommandAreaFieldSummary(BaseModel):
    field_id: str
    latitude: float
    longitude: float
    advisory: AdvisoryResult


class CommandAreaResult(BaseModel):
    area_id: str
    area_name: str
    total_fields: int
    fields_needing_irrigation: int
    fields_at_risk_pct: float = Field(..., description="% of fields with a non-zero irrigation deficit")
    average_deficit_mm: float
    total_irrigation_volume_mm: float = Field(..., description="Sum of recommended irrigation depth across all fields")
    fields: list[CommandAreaFieldSummary]
