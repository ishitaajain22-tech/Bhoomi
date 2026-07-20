"""
Dedicated phenology endpoint — exposes the full real SOS/peak/stage
detail (and the underlying NDVI series for charting) as its own
resource, rather than folding it into the advisory response. This
also gives the frontend a real reason to have a dedicated field
detail page instead of one flat dashboard.
"""
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.models.moisture_estimator import get_ndvi_time_series, _FIELD_COORDS
from app.services.phenology import estimate_phenology

router = APIRouter(prefix="/fields", tags=["phenology"])


@router.get("/{field_id}/phenology")
def field_phenology(field_id: str, reference_date: date | None = Query(None)):
    if field_id not in _FIELD_COORDS:
        raise HTTPException(status_code=404, detail=f"Field {field_id} not found")

    lat, lon = _FIELD_COORDS[field_id]
    on_date = reference_date or date(2025, 3, 20)
    dates, ndvi_values = get_ndvi_time_series(field_id, lat, lon, on_date)
    result = estimate_phenology(dates, ndvi_values, on_date)

    return {
        "field_id": field_id,
        "sos_date": result["sos_date"].isoformat() if result["sos_date"] else None,
        "peak_growth_date": result["peak_growth_date"].isoformat() if result["peak_growth_date"] else None,
        "growth_stage": result["growth_stage"],
        "days_after_sos": result["days_after_sos"],
        "ndvi_series": [
            {"date": d.isoformat(), "ndvi": round(v, 3)} for d, v in zip(dates, ndvi_values)
        ],
    }
