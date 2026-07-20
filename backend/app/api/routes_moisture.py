"""
Endpoints for moisture stress detection. Exposes a single-field
lookup and a timeline endpoint — the timeline is what powers the
frontend's MoistureHeatmap chart, including which data source
(SAR/optical/fused) backed each point.
"""
from datetime import date
from fastapi import APIRouter, HTTPException, Query

from app.schemas.moisture_schema import MoistureRequest, MoistureResult
from app.models.moisture_estimator import estimate_moisture, get_timeline
from app.core.logger import get_logger

router = APIRouter(prefix="/moisture", tags=["moisture"])
logger = get_logger(__name__)


@router.post("/estimate", response_model=MoistureResult)
def estimate(request: MoistureRequest):
    try:
        return estimate_moisture(request)
    except Exception as exc:
        logger.exception("Moisture estimation failed for field %s", request.field_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{field_id}/timeline")
def timeline(
    field_id: str,
    start: date | None = Query(None),
    end: date | None = Query(None),
):
    return get_timeline(field_id, start, end)
