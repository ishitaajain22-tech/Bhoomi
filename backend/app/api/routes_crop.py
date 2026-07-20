"""
Endpoints for crop-type classification. Thin layer: validates
input via crop_schema, delegates the actual prediction to
models/crop_classifier.py, and returns a typed response.
No ML logic lives here on purpose, so the model can be swapped
or retrained without touching the API contract.
"""
from fastapi import APIRouter, HTTPException

from app.schemas.crop_schema import CropClassificationRequest, CropClassificationResult
from app.models.crop_classifier import classify_crop
from app.core.logger import get_logger

router = APIRouter(prefix="/crop", tags=["crop"])
logger = get_logger(__name__)


@router.post("/classify", response_model=CropClassificationResult)
def classify(request: CropClassificationRequest):
    try:
        return classify_crop(request)
    except Exception as exc:
        logger.exception("Crop classification failed for field %s", request.field_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{field_id}", response_model=CropClassificationResult)
def get_crop_for_field(field_id: str):
    """Convenience lookup used by the frontend field list."""
    from app.models.crop_classifier import get_cached_classification

    result = get_cached_classification(field_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"No crop classification found for {field_id}")
    return result
