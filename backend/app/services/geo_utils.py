"""
Shared geospatial helpers: converting a field's lat/lon into a
bounding box for satellite API queries, and reprojecting/aligning
SAR and optical rasters so they overlay correctly pixel-for-pixel.
This co-registration step is the unglamorous work most hackathon
teams skip — get it wrong and fusion downstream is meaningless.
"""
from dataclasses import dataclass


@dataclass
class BoundingBox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def as_list(self) -> list[float]:
        return [self.min_lon, self.min_lat, self.max_lon, self.max_lat]


def point_to_bbox(latitude: float, longitude: float, buffer_deg: float = 0.01) -> BoundingBox:
    """Build a small bounding box around a field centroid for satellite queries."""
    return BoundingBox(
        min_lon=longitude - buffer_deg,
        min_lat=latitude - buffer_deg,
        max_lon=longitude + buffer_deg,
        max_lat=latitude + buffer_deg,
    )


def align_rasters(sar_array, optical_array, target_resolution_m: float = 10.0):
    """
    Resample SAR and optical arrays onto a common grid/resolution
    so per-pixel fusion is valid. Placeholder for rasterio/rioxarray
    reprojection logic — wire in actual CRS handling here.
    """
    raise NotImplementedError("Wire in rasterio reprojection once real imagery is loaded")
