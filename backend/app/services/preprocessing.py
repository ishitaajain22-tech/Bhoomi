"""
Converts raw band data into the derived indices the models
actually consume: NDVI/NDWI from optical bands, and normalized
backscatter from SAR VV/VH. Keeps this math out of the fetchers
(which only deal with raw API responses) and out of the models
(which should only see clean, ready-to-use features).
"""
import numpy as np

from app.core.logger import get_logger

logger = get_logger(__name__)


def compute_ndvi(red_band: np.ndarray, nir_band: np.ndarray) -> np.ndarray:
    """Normalized Difference Vegetation Index — crop vigor signal from optical bands."""
    denom = nir_band + red_band
    denom = np.where(denom == 0, 1e-6, denom)
    return (nir_band - red_band) / denom


def compute_ndwi(nir_band: np.ndarray, swir_band: np.ndarray) -> np.ndarray:
    """Normalized Difference Water Index — surface moisture signal from optical bands."""
    denom = nir_band + swir_band
    denom = np.where(denom == 0, 1e-6, denom)
    return (nir_band - swir_band) / denom


def normalize_backscatter(vv: np.ndarray, vh: np.ndarray) -> dict[str, np.ndarray]:
    """
    Converts raw SAR backscatter (linear power) to dB scale and
    computes the VV/VH ratio, which correlates with soil/canopy
    moisture content.
    """
    vv_db = 10 * np.log10(np.clip(vv, 1e-6, None))
    vh_db = 10 * np.log10(np.clip(vh, 1e-6, None))
    ratio = np.where(vh != 0, vv / np.where(vh == 0, 1e-6, vh), 0)
    return {"vv_db": vv_db, "vh_db": vh_db, "vv_vh_ratio": ratio}


def scale_to_moisture_index(value: np.ndarray, low: float, high: float) -> np.ndarray:
    """Linearly rescales a raw index into a 0-100 moisture index for the advisory layer."""
    clipped = np.clip(value, low, high)
    return (clipped - low) / (high - low) * 100
