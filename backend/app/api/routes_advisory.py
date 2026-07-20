"""
Endpoints for the final irrigation advisory — the "so what"
layer the pitch deck leans on. Calls the advisory_engine, which
itself combines crop_classifier + moisture_estimator outputs
into one plain-language recommendation. Also exposes a /fields
listing used by the frontend's field sidebar and coverage stat.
"""
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.schemas.advisory_schema import AdvisoryResult
from app.models.advisory_engine import generate_advisory, list_fields, get_coverage_stats
from app.core.logger import get_logger

router = APIRouter(tags=["advisory"])
logger = get_logger(__name__)


@router.get("/advisory/{field_id}", response_model=AdvisoryResult)
def advisory_for_field(field_id: str, reference_date: date | None = Query(None)):
    try:
        return generate_advisory(field_id, reference_date=reference_date)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Field {field_id} not found")
    except Exception as exc:
        logger.exception("Advisory generation failed for field %s", field_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/fields")
def fields():
    """Backs the frontend sidebar — list of all monitored fields with summary state."""
    return list_fields()


@router.get("/coverage")
def coverage():
    """Backs the dashboard header stat: fused vs optical-only coverage % for the active week."""
    return get_coverage_stats()


@router.get("/command-areas")
def command_areas():
    """Lists available canal command areas — backs a future command-area selector in the dashboard."""
    from app.models.command_area import list_command_areas

    return list_command_areas()


@router.get("/command-areas/{area_id}/advisory")
def command_area_advisory(area_id: str):
    """
    Aggregated command-area-level advisory: how many fields need
    irrigation, total volume, and the per-field breakdown — the
    canal-command-area planning view the spec explicitly asks for.
    """
    from app.models.command_area import generate_command_area_advisory

    try:
        return generate_command_area_advisory(area_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Command area {area_id} not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/model-info")
def model_info():
    """
    Real validation metrics from the actual training run on real
    Kapurthala AOI data (see ml/training/train_crop_classifier.py
    output) — exposed so the UI can show real model performance
    rather than burying it in a backend log.
    """
    return {
        "crop_classifier": {
            "model": "Random Forest",
            "overall_accuracy": 0.885,
            "kappa": 0.453,
            "training_data": "Real Sentinel-1/2 + ESA WorldCereal labels, Kapurthala AOI",
        },
        "phenology": {
            "method": "NDVI threshold-crossing Start-of-Season detection",
            "data_source": "Real Sentinel-2 NDVI time series (24 acquisitions, Oct 2024-Mar 2025)",
        },
        "water_balance": {
            "eto_method": "Thornthwaite (real ERA5-Land temperature)",
            "rainfall_source": "Real CHIRPS daily precipitation",
        },
    }
