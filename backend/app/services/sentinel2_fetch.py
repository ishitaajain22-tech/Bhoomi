"""
Fetches Sentinel-2 optical imagery for a given field and date
range. Mirrors sentinel1_fetch.py's interface so the fusion
layer can treat both sources uniformly. Also flags when a
requested date is too cloud-obscured to use — that flag is what
drives the frontend's "no usable signal" readout in optical-only
mode.
"""
from datetime import date

from app.core.config import get_settings
from app.core.logger import get_logger
from app.services.geo_utils import point_to_bbox

logger = get_logger(__name__)
settings = get_settings()

CLOUD_COVER_THRESHOLD_PCT = 30.0


def fetch_sentinel2_scene(latitude: float, longitude: float, target_date: date):
    """
    Returns optical band data (B04/B08 etc., used for NDVI/NDWI)
    for the bounding box around (latitude, longitude) near
    target_date, plus a cloud_blocked flag if cloud cover on
    that pass exceeds the usable threshold.
    """
    bbox = point_to_bbox(latitude, longitude)
    logger.info("Fetching Sentinel-2 scene for bbox=%s near %s", bbox.as_list(), target_date)

    if not settings.sentinel_hub_client_id:
        logger.warning("No Sentinel Hub credentials configured — returning mock optical scene")
        return _mock_scene(target_date)

    raise NotImplementedError("Wire in sentinelhub-py SHRequest for Sentinel-2 L2A here, with cloud-mask filtering")


def _mock_scene(target_date: date, cloud_cover_pct: float = 65.0):
    """Mock scene defaulting to high cloud cover — mirrors the monsoon-week scenario the pitch is built on."""
    blocked = cloud_cover_pct > CLOUD_COVER_THRESHOLD_PCT
    return {
        "date": target_date.isoformat(),
        "bands": {} if blocked else {"B04": None, "B08": None},
        "cloud_cover_pct": cloud_cover_pct,
        "cloud_blocked": blocked,
        "source": "optical",
    }
