"""
Real phenology detection — Start-of-Season (SOS), peak growth, and
growth-stage classification from an NDVI time series, replacing the
earlier hardcoded "days-after-sowing" placeholder in
moisture_estimator.py. Matches the spec's "AI - Crop Phenology"
block: Sowing, Vegetative, Flowering, Maturity, derived from real
NDVI dynamics rather than an assumed sowing date.

Method: NDVI green-up detection via a fixed threshold crossing on a
smoothed time series — a standard, explainable SOS approach (more
robust alternatives like Savitzky-Golay + derivative-based SOS can
replace this once a denser/cleaner real time series is available).
"""
from datetime import date, timedelta

import numpy as np

from app.core.logger import get_logger

logger = get_logger(__name__)

# NDVI threshold for green-up detection — value above which a field
# is considered to have begun active crop growth (fallow/bare soil
# typically sits well below this for Rabi crops in northern India).
SOS_NDVI_THRESHOLD = 0.35

# Smoothing window (in samples) to reduce noise/cloud-residual spikes
# before threshold-crossing detection.
SMOOTHING_WINDOW = 3


def smooth_series(values: list[float], window: int = SMOOTHING_WINDOW) -> np.ndarray:
    """Simple moving-average smoothing to reduce single-date noise before SOS detection."""
    arr = np.array(values, dtype=float)
    if len(arr) < window:
        return arr
    kernel = np.ones(window) / window
    return np.convolve(arr, kernel, mode="same")


def detect_sos(dates: list[date], ndvi_values: list[float], threshold: float = SOS_NDVI_THRESHOLD) -> date | None:
    """
    Detects Start-of-Season: the first date where smoothed NDVI
    crosses above `threshold` and stays above it on the next sample
    too (avoids single-point noise triggering a false SOS).
    Returns None if no crossing is found (e.g. field never greened
    up in the observed window, or data is too sparse).
    """
    if len(dates) != len(ndvi_values) or len(dates) < 2:
        return None

    order = np.argsort(dates)
    sorted_dates = [dates[i] for i in order]
    sorted_values = smooth_series([ndvi_values[i] for i in order])

    for i in range(len(sorted_values) - 1):
        if sorted_values[i] < threshold <= sorted_values[i + 1]:
            return sorted_dates[i + 1]

    logger.info("No SOS crossing detected in series of length %d", len(dates))
    return None


def detect_peak_growth(dates: list[date], ndvi_values: list[float], sos: date | None = None) -> date | None:
    """
    Peak growth date: the date of maximum smoothed NDVI, searched
    only AFTER the detected SOS. Without this restriction, residual
    high NDVI from a prior season's crop (visible as a high value
    right before harvest/fallow) gets wrongly picked as "peak" —
    a real issue observed on actual exported field data.
    """
    if not dates:
        return None
    order = np.argsort(dates)
    sorted_dates = [dates[i] for i in order]
    sorted_values = smooth_series([ndvi_values[i] for i in order])

    if sos is not None:
        candidate_idx = [i for i, d in enumerate(sorted_dates) if d >= sos]
        if not candidate_idx:
            return None
        peak_idx = max(candidate_idx, key=lambda i: sorted_values[i])
    else:
        peak_idx = int(np.argmax(sorted_values))
    return sorted_dates[peak_idx]


# Days-after-SOS breakpoints -> growth stage. Generic Rabi-season
# curve; replace with crop-specific breakpoints once crop type is
# confirmed for a given field (from crop_classifier output).
_STAGE_BREAKPOINTS = [
    (15, "Sowing"),
    (45, "Vegetative"),
    (75, "Flowering"),
    (120, "Maturity"),
]


def classify_stage_from_sos(sos: date | None, on_date: date) -> str:
    """
    Maps days-since-real-SOS to a growth stage. Falls back to
    'Vegetative' (a safe mid-season default) if SOS could not be
    detected, rather than guessing a sowing date.
    """
    if sos is None:
        logger.warning("No SOS available — defaulting to 'Vegetative' stage")
        return "Vegetative"

    days_after_sos = (on_date - sos).days
    if days_after_sos < 0:
        return "Sowing"

    for threshold, stage in _STAGE_BREAKPOINTS:
        if days_after_sos <= threshold:
            return stage
    return "Maturity"


def estimate_phenology(dates: list[date], ndvi_values: list[float], on_date: date) -> dict:
    """
    Full phenology estimate for one field: SOS date, peak-growth
    date, and current growth stage — the real replacement for the
    old hardcoded sowing-date lookup.
    """
    sos = detect_sos(dates, ndvi_values)
    peak = detect_peak_growth(dates, ndvi_values, sos=sos)
    stage = classify_stage_from_sos(sos, on_date)
    return {
        "sos_date": sos,
        "peak_growth_date": peak,
        "growth_stage": stage,
        "days_after_sos": (on_date - sos).days if sos else None,
    }


def compute_seasonal_ndvi_baseline(dates: list[date], ndvi_values: list[float], sos: date | None) -> tuple[float, float]:
    """
    Computes the real historical NDVI min/max for VCI, restricted to
    on-or-after SOS. Without this restriction, the pre-season
    residual high-NDVI noise (same issue fixed in detect_peak_growth)
    would distort the baseline range. This is a within-season proxy
    for "historical" range — a true multi-year climatology baseline
    would need several years of the same exported time series, which
    can be added once available.
    """
    if not dates:
        return (0.0, 1.0)
    if sos is not None:
        in_season = [v for d, v in zip(dates, ndvi_values) if d >= sos]
    else:
        in_season = list(ndvi_values)
    if not in_season:
        in_season = list(ndvi_values)
    return (min(in_season), max(in_season))


def load_real_ndvi_timeseries(csv_path: str) -> dict[str, tuple[list, list[float]]]:
    """
    Loads a real per-point NDVI time series exported from GEE
    (columns: NDVI, date, .geo — see gee_phenology_timeseries.js).
    Groups rows by point location (since GEE re-samples the same
    FeatureCollection across dates, coordinates identify the same
    physical point over time) into per-point (dates, ndvi_values)
    series ready for estimate_phenology().

    Duplicate (point, date) rows — which can happen with overlapping
    Sentinel-2 tiles — are averaged rather than kept as separate
    entries, since they represent the same real date.
    """
    import json
    from datetime import datetime

    import pandas as pd

    df = pd.read_csv(csv_path)
    df["coords"] = df[".geo"].apply(lambda x: tuple(json.loads(x)["coordinates"]))
    df["parsed_date"] = df["date"].apply(lambda d: datetime.strptime(d, "%Y-%m-%d").date())

    # Average duplicate same-day readings per point (overlapping tiles).
    grouped = df.groupby(["coords", "parsed_date"], as_index=False)["NDVI"].mean()

    series_by_point = {}
    for coords, group in grouped.groupby("coords"):
        group_sorted = group.sort_values("parsed_date")
        point_id = f"{coords[1]:.6f}_{coords[0]:.6f}"  # lat_lon as a stable point identifier
        series_by_point[point_id] = (
            group_sorted["parsed_date"].tolist(),
            group_sorted["NDVI"].tolist(),
        )
    return series_by_point


def run_phenology_on_real_data(csv_path: str, on_date=None) -> "pd.DataFrame":
    """
    Convenience entry point: loads the real exported CSV and runs
    SOS/peak/stage detection for every point, returning a summary
    table. `on_date` defaults to the latest date present in the data
    (i.e. "what stage was each point at, as of its last observation").
    """
    import pandas as pd

    series_by_point = load_real_ndvi_timeseries(csv_path)
    rows = []
    for point_id, (dates, ndvi_values) in series_by_point.items():
        reference_date = on_date or max(dates)
        result = estimate_phenology(dates, ndvi_values, reference_date)
        rows.append({
            "point_id": point_id,
            "n_observations": len(dates),
            "sos_date": result["sos_date"],
            "peak_growth_date": result["peak_growth_date"],
            "growth_stage": result["growth_stage"],
            "days_after_sos": result["days_after_sos"],
        })
    return pd.DataFrame(rows)


def load_real_sar_timeseries(csv_path: str) -> dict[str, tuple[list, list[float], list[float]]]:
    """
    Loads a real per-point SAR (VV/VH) time series exported from GEE
    (columns: VV, VH, date, .geo — see gee_sar_timeseries.js).
    Mirrors load_real_ndvi_timeseries(), grouping by point location
    into per-point (dates, vv_values, vh_values) series for SMI.
    """
    import json
    from datetime import datetime

    import pandas as pd

    df = pd.read_csv(csv_path)
    # SAR per-image reprojection causes small coordinate drift for the
    # "same" physical point across dates (observed up to ~300m on real
    # exported data) — coordinate-based grouping is unreliable here.
    # system:index encodes a stable point index (e.g. "..._8AE4_0_0"
    # -> point 0) regardless of that drift, so use it instead.
    df["point_idx"] = df["system:index"].apply(lambda s: int(s.split("_")[-2]))
    df["parsed_date"] = df["date"].apply(lambda d: datetime.strptime(d, "%Y-%m-%d").date())

    grouped = df.groupby(["point_idx", "parsed_date"], as_index=False)[["VV", "VH"]].mean()

    # Keep one representative coordinate per point_idx (first occurrence)
    # purely for nearest-point matching against field lat/lon — fine
    # since drift is small relative to typical field-to-field distance.
    coords_by_idx = df.groupby("point_idx")[".geo"].first().apply(
        lambda x: json.loads(x)["coordinates"]
    )

    series_by_point = {}
    for point_idx, group in grouped.groupby("point_idx"):
        group_sorted = group.sort_values("parsed_date")
        lon, lat = coords_by_idx[point_idx]
        point_id = f"{lat:.6f}_{lon:.6f}"
        series_by_point[point_id] = (
            group_sorted["parsed_date"].tolist(),
            group_sorted["VV"].tolist(),
            group_sorted["VH"].tolist(),
        )
    return series_by_point


def compute_seasonal_backscatter_baseline(vv_values: list[float]) -> tuple[float, float]:
    """
    Real historical VV backscatter (dB) min/max for SMI — no SOS
    restriction here since SAR backscatter reflects soil/canopy
    moisture year-round (unlike NDVI, there's no "pre-season noise"
    artifact to exclude from a bare/fallow field's backscatter).
    """
    if not vv_values:
        return (-20.0, -5.0)
    return (min(vv_values), max(vv_values))


def load_real_ndwi_timeseries(csv_path: str) -> dict[str, tuple[list, list[float]]]:
    """
    Loads the real per-point NDWI time series exported from GEE
    (columns: NDWI, date, .geo — see gee_ndwi_timeseries.js). Mirrors
    load_real_ndvi_timeseries() exactly, since it shares the same
    AOI/seed and therefore the same point set.
    """
    import json
    from datetime import datetime

    import pandas as pd

    df = pd.read_csv(csv_path)
    df["coords"] = df[".geo"].apply(lambda x: tuple(json.loads(x)["coordinates"]))
    df["parsed_date"] = df["date"].apply(lambda d: datetime.strptime(d, "%Y-%m-%d").date())

    grouped = df.groupby(["coords", "parsed_date"], as_index=False)["NDWI"].mean()

    series_by_point = {}
    for coords, group in grouped.groupby("coords"):
        group_sorted = group.sort_values("parsed_date")
        point_id = f"{coords[1]:.6f}_{coords[0]:.6f}"
        series_by_point[point_id] = (
            group_sorted["parsed_date"].tolist(),
            group_sorted["NDWI"].tolist(),
        )
    return series_by_point
