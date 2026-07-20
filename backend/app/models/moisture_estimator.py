"""
Moisture estimation model — orchestrates fetch -> preprocess ->
VCI/SMI -> fuse, and folds in REAL phenology (growth stage) via
SOS detection on an NDVI time series (app/services/phenology.py),
matching the spec's "AI - Crop Phenology" block. Replaces the
earlier hardcoded days-after-sowing placeholder.
"""
from datetime import date, timedelta

from app.core.logger import get_logger
from app.schemas.moisture_schema import MoistureRequest, MoistureResult, MoisturePoint
from app.services.fusion import compute_vci, compute_smi, compute_smi_vh_ratio, fuse_moisture, classify_stress
from app.services.phenology import estimate_phenology

logger = get_logger(__name__)

# Real field registry — all 59 real GEE sample points across the
# Kapurthala AOI (previously only 4 of these 59 were registered,
# an arbitrary demo limit, not a data limit). Each point has real
# NDVI/SAR/rainfall/temperature data already loaded from
# data/labels/bhoomi_*.csv.
_FIELD_COORDS = {
    "F-K01": (31.398706, 75.387885),
    "F-K02": (31.398797, 75.387570),
    "F-K03": (31.398977, 75.387991),
    "F-K04": (31.399060, 75.390095),
    "F-K05": (31.399152, 75.389570),
    "F-K06": (31.399242, 75.389886),
    "F-K07": (31.399245, 75.388623),
    "F-K08": (31.399249, 75.387361),
    "F-K09": (31.399336, 75.388519),
    "F-K10": (31.399420, 75.390623),
    "F-K11": (31.399429, 75.387677),
    "F-K12": (31.399511, 75.390413),
    "F-K13": (31.399517, 75.388414),
    "F-K14": (31.399598, 75.391360),
    "F-K15": (31.399695, 75.389151),
    "F-K16": (31.399697, 75.388520),
    "F-K17": (31.399781, 75.390519),
    "F-K18": (31.399785, 75.389152),
    "F-K19": (31.399786, 75.388836),
    "F-K20": (31.399870, 75.391045),
    "F-K21": (31.399872, 75.390414),
    "F-K22": (31.399876, 75.388942),
    "F-K23": (31.399876, 75.389047),
    "F-K24": (31.399961, 75.390520),
    "F-K25": (31.399964, 75.389678),
    "F-K26": (31.400050, 75.391151),
    "F-K27": (31.400053, 75.389994),
    "F-K28": (31.400053, 75.390099),
    "F-K29": (31.400056, 75.389047),
    "F-K30": (31.400139, 75.391362),
    "F-K31": (31.400143, 75.390310),
    "F-K32": (31.400148, 75.388522),
    "F-K33": (31.400230, 75.391047),
    "F-K34": (31.400233, 75.390310),
    "F-K35": (31.400323, 75.390206),
    "F-K36": (31.400326, 75.389364),
    "F-K37": (31.400332, 75.387260),
    "F-K38": (31.400413, 75.390311),
    "F-K39": (31.400416, 75.389470),
    "F-K40": (31.400507, 75.389049),
    "F-K41": (31.400507, 75.389154),
    "F-K42": (31.400509, 75.388313),
    "F-K43": (31.400602, 75.387682),
    "F-K44": (31.400690, 75.388209),
    "F-K45": (31.400775, 75.389997),
    "F-K46": (31.400778, 75.389050),
    "F-K47": (31.400779, 75.388735),
    "F-K48": (31.400781, 75.387999),
    "F-K49": (31.400867, 75.389472),
    "F-K50": (31.400868, 75.389051),
    "F-K51": (31.400957, 75.389577),
    "F-K52": (31.401135, 75.390209),
    "F-K53": (31.401138, 75.389473),
    "F-K54": (31.401226, 75.390104),
    "F-K55": (31.401228, 75.389368),
    "F-K56": (31.401316, 75.390210),
    "F-K57": (31.401409, 75.389369),
    "F-K58": (31.401588, 75.389790),
    "F-K59": (31.401675, 75.390842),
}


def get_ndvi_time_series(field_id: str, lat: float, lon: float, end_date: date) -> tuple[list[date], list[float]]:
    """
    Pulls a real NDVI time series for SOS detection. Uses the actual
    GEE-exported series in data/labels/bhoomi_ndvi_timeseries.csv
    when available (real Kapurthala AOI data), matched to the
    nearest sample point to (lat, lon). Falls back to a placeholder
    Rabi-season curve if the real CSV isn't present or no field
    coordinates are known — keeps the pipeline runnable everywhere.
    """
    real_series = _get_real_series_near(lat, lon, end_date)
    if real_series is not None:
        return real_series

    logger.warning("No real NDVI series available for field %s — using placeholder curve", field_id)
    season_start = end_date - timedelta(days=150)
    dates, ndvi_values = [], []
    current = season_start
    while current <= end_date:
        day_offset = (current - season_start).days
        if day_offset < 50:
            val = 0.18
        elif day_offset < 100:
            val = 0.2 + 0.55 * ((day_offset - 50) / 50)
        else:
            val = 0.78 - 0.25 * ((day_offset - 100) / 50)
        dates.append(current)
        ndvi_values.append(val)
        current += timedelta(days=10)
    return dates, ndvi_values


_REAL_NDVI_CSV_PATH = "data/labels/bhoomi_ndvi_timeseries.csv"
_real_series_cache: dict | None = None


def _get_real_series_near(lat: float, lon: float, end_date: date):
    """Loads the real exported CSV (cached) and returns the series for the closest sample point, if within range."""
    global _real_series_cache
    if _real_series_cache is None:
        try:
            from app.services.phenology import load_real_ndvi_timeseries
            _real_series_cache = load_real_ndvi_timeseries(_REAL_NDVI_CSV_PATH)
        except FileNotFoundError:
            _real_series_cache = {}

    if not _real_series_cache:
        return None

    def point_distance(point_id: str) -> float:
        p_lat, p_lon = (float(v) for v in point_id.split("_"))
        return (p_lat - lat) ** 2 + (p_lon - lon) ** 2

    nearest_id = min(_real_series_cache, key=point_distance)
    dates, ndvi_values = _real_series_cache[nearest_id]
    filtered = [(d, v) for d, v in zip(dates, ndvi_values) if d <= end_date]
    if not filtered:
        return None
    f_dates, f_values = zip(*filtered)
    return list(f_dates), list(f_values)


def get_ndvi_value_at(field_id: str, lat: float, lon: float, target_date: date, tolerance_days: int = 6) -> float | None:
    """
    Returns the real NDVI value nearest to target_date from the
    exported time series, if a real observation exists within
    `tolerance_days`. Returns None if the nearest real observation
    is too far away — this naturally reflects real satellite-revisit
    gaps (e.g. cloud cover) rather than inventing a value.
    """
    real_series = _get_real_series_near(lat, lon, target_date + timedelta(days=tolerance_days))
    if real_series is None:
        return None
    dates, ndvi_values = real_series
    if not dates:
        return None

    closest_idx = min(range(len(dates)), key=lambda i: abs((dates[i] - target_date).days))
    if abs((dates[closest_idx] - target_date).days) > tolerance_days:
        return None
    return ndvi_values[closest_idx]


def get_ndvi_seasonal_baseline(field_id: str, lat: float, lon: float, on_date: date) -> tuple[float, float]:
    """Real seasonal NDVI min/max (post-SOS) for VCI — replaces the old hardcoded (0.40, 0.75) baseline."""
    from app.services.phenology import detect_sos, compute_seasonal_ndvi_baseline

    dates, ndvi_values = get_ndvi_time_series(field_id, lat, lon, on_date)
    sos = detect_sos(dates, ndvi_values)
    return compute_seasonal_ndvi_baseline(dates, ndvi_values, sos)


_REAL_NDWI_CSV_PATH = "data/labels/bhoomi_ndwi_timeseries.csv"
_real_ndwi_cache: dict | None = None


def _get_real_ndwi_series_near(lat: float, lon: float):
    """Loads the real exported NDWI CSV (cached) and returns the series for the closest sample point."""
    global _real_ndwi_cache
    if _real_ndwi_cache is None:
        try:
            from app.services.phenology import load_real_ndwi_timeseries
            _real_ndwi_cache = load_real_ndwi_timeseries(_REAL_NDWI_CSV_PATH)
        except FileNotFoundError:
            _real_ndwi_cache = {}

    if not _real_ndwi_cache:
        return None

    def point_distance(point_id: str) -> float:
        p_lat, p_lon = (float(v) for v in point_id.split("_"))
        return (p_lat - lat) ** 2 + (p_lon - lon) ** 2

    nearest_id = min(_real_ndwi_cache, key=point_distance)
    return _real_ndwi_cache[nearest_id]


def get_ndwi_value_at(lat: float, lon: float, target_date: date, tolerance_days: int = 6) -> float | None:
    """
    Real NDWI value nearest to target_date, within tolerance — was
    previously only a single static snapshot from the ground-truth
    CSV; this closes that gap with a real time series, mirroring
    get_ndvi_value_at exactly.
    """
    series = _get_real_ndwi_series_near(lat, lon)
    if series is None:
        return None
    dates, ndwi_values = series
    if not dates:
        return None
    closest_idx = min(range(len(dates)), key=lambda i: abs((dates[i] - target_date).days))
    if abs((dates[closest_idx] - target_date).days) > tolerance_days:
        return None
    return ndwi_values[closest_idx]


_REAL_SAR_CSV_PATH = "data/labels/bhoomi_sar_timeseries.csv"
_real_sar_cache: dict | None = None


def _get_real_sar_series_near(lat: float, lon: float):
    """Loads the real exported SAR CSV (cached) and returns the VV/VH series for the closest sample point."""
    global _real_sar_cache
    if _real_sar_cache is None:
        try:
            from app.services.phenology import load_real_sar_timeseries
            _real_sar_cache = load_real_sar_timeseries(_REAL_SAR_CSV_PATH)
        except FileNotFoundError:
            _real_sar_cache = {}

    if not _real_sar_cache:
        return None

    def point_distance(point_id: str) -> float:
        p_lat, p_lon = (float(v) for v in point_id.split("_"))
        return (p_lat - lat) ** 2 + (p_lon - lon) ** 2

    nearest_id = min(_real_sar_cache, key=point_distance)
    return _real_sar_cache[nearest_id]  # (dates, vv_values, vh_values)


def get_vv_value_at(lat: float, lon: float, target_date: date, tolerance_days: int = 6) -> float | None:
    """Real VV backscatter (dB) nearest to target_date, within tolerance — mirrors get_ndvi_value_at."""
    series = _get_real_sar_series_near(lat, lon)
    if series is None:
        return None
    dates, vv_values, _ = series
    if not dates:
        return None
    closest_idx = min(range(len(dates)), key=lambda i: abs((dates[i] - target_date).days))
    if abs((dates[closest_idx] - target_date).days) > tolerance_days:
        return None
    return vv_values[closest_idx]


def get_vh_value_at(lat: float, lon: float, target_date: date, tolerance_days: int = 6) -> float | None:
    """Real VH backscatter (dB) nearest to target_date, within tolerance — mirrors get_vv_value_at."""
    series = _get_real_sar_series_near(lat, lon)
    if series is None:
        return None
    dates, _, vh_values = series
    if not dates:
        return None
    closest_idx = min(range(len(dates)), key=lambda i: abs((dates[i] - target_date).days))
    if abs((dates[closest_idx] - target_date).days) > tolerance_days:
        return None
    return vh_values[closest_idx]


def get_vv_seasonal_baseline(lat: float, lon: float) -> tuple[float, float]:
    """Real seasonal VV min/max for SMI — replaces the old hardcoded (-14.0, -6.0) baseline."""
    from app.services.phenology import compute_seasonal_backscatter_baseline

    series = _get_real_sar_series_near(lat, lon)
    if series is None:
        return (-20.0, -5.0)
    _, vv_values, _ = series
    return compute_seasonal_backscatter_baseline(vv_values)


def get_vh_vv_ratio_seasonal_baseline(lat: float, lon: float) -> tuple[float, float]:
    """
    Real seasonal VH-VV ratio (dB difference) min/max — the
    baseline for the cross-polarization SMI feature the spec
    names. Computed from the same real per-date VV/VH pairs
    already loaded for the field, not a separate export.
    """
    from app.services.fusion import compute_vh_vv_ratio_db

    series = _get_real_sar_series_near(lat, lon)
    if series is None:
        return (-12.0, -2.0)
    _, vv_values, vh_values = series
    ratios = [compute_vh_vv_ratio_db(vv, vh) for vv, vh in zip(vv_values, vh_values)]
    if not ratios:
        return (-12.0, -2.0)
    return (min(ratios), max(ratios))


def get_vci_smi_breakdown(field_id: str, on_date: date) -> dict:
    """
    Returns real VCI and SMI as separate values (not just the fused
    moisture index) — the spec names these two indices explicitly,
    so showing them individually matters for credibility, not just
    the blended result.
    """
    lat, lon = _FIELD_COORDS.get(field_id, (0.0, 0.0))
    ndvi_min, ndvi_max = get_ndvi_seasonal_baseline(field_id, lat, lon, on_date)
    vv_min, vv_max = get_vv_seasonal_baseline(lat, lon)
    ratio_min, ratio_max = get_vh_vv_ratio_seasonal_baseline(lat, lon)

    real_ndvi = get_ndvi_value_at(field_id, lat, lon, on_date)
    vci = compute_vci(real_ndvi, ndvi_min, ndvi_max) if real_ndvi is not None else None

    real_vv = get_vv_value_at(lat, lon, on_date)
    real_vh = get_vh_value_at(lat, lon, on_date)
    if real_vv is not None and real_vh is not None:
        smi = compute_smi_vh_ratio(real_vv, real_vh, ratio_min, ratio_max)
    elif real_vv is not None:
        smi = compute_smi(real_vv, vv_min, vv_max)
    else:
        smi = None

    real_ndwi = get_ndwi_value_at(lat, lon, on_date)

    return {"vci": vci, "smi": smi, "ndwi": real_ndwi}


def get_growth_stage(field_id: str, on_date: date) -> str:
    return get_phenology_details(field_id, on_date)["growth_stage"]


def get_phenology_details(field_id: str, on_date: date) -> dict:
    """Full real phenology estimate (SOS date, days-after-SOS, stage) for a field, not just the stage string."""
    lat, lon = _FIELD_COORDS.get(field_id, (0.0, 0.0))
    dates, ndvi_values = get_ndvi_time_series(field_id, lat, lon, on_date)
    return estimate_phenology(dates, ndvi_values, on_date)


def estimate_moisture(request: MoistureRequest) -> MoistureResult:
    lat, lon = _FIELD_COORDS.get(request.field_id, (0.0, 0.0))
    points = _build_timeline(request.field_id, lat, lon, request.start_date, request.end_date)

    if not points:
        raise ValueError(
            f"No real NDVI or SAR observations found for field {request.field_id} "
            f"between {request.start_date} and {request.end_date}. "
            "This window likely falls outside the exported historical data range "
            "(currently Oct 2024-Mar 2025) — pass a reference_date within that "
            "range, or refresh the GEE export to cover the current date."
        )

    current = points[-1].moisture_value
    stage = get_growth_stage(request.field_id, request.end_date)
    return MoistureResult(
        field_id=request.field_id,
        stress_level=classify_stress(current, growth_stage=stage),
        current_value=current,
        timeline=points,
    )


def get_timeline(field_id: str, start: date | None, end: date | None) -> list[MoisturePoint]:
    lat, lon = _FIELD_COORDS.get(field_id, (0.0, 0.0))
    start = start or (date.today() - timedelta(days=8))
    end = end or date.today()
    return _build_timeline(field_id, lat, lon, start, end)


def _build_timeline(field_id: str, lat: float, lon: float, start: date, end: date) -> list[MoisturePoint]:
    points: list[MoisturePoint] = []
    ndvi_min, ndvi_max = get_ndvi_seasonal_baseline(field_id, lat, lon, end)
    vv_min, vv_max = get_vv_seasonal_baseline(lat, lon)
    ratio_min, ratio_max = get_vh_vv_ratio_seasonal_baseline(lat, lon)

    current = start
    while current <= end:
        real_ndvi = get_ndvi_value_at(field_id, lat, lon, current)
        vci = compute_vci(real_ndvi, ndvi_min, ndvi_max) if real_ndvi is not None else None

        real_vv = get_vv_value_at(lat, lon, current)
        real_vh = get_vh_value_at(lat, lon, current)
        if real_vv is not None and real_vh is not None:
            # Preferred path: real VH/VV cross-pol ratio, the spec's
            # named SAR feature — closes the gap where VH was fetched
            # but never actually used in moisture stress calculation.
            smi = compute_smi_vh_ratio(real_vv, real_vh, ratio_min, ratio_max)
        elif real_vv is not None:
            smi = compute_smi(real_vv, vv_min, vv_max)
        else:
            smi = None

        if vci is None and smi is None:
            # No real observation from either sensor near this date
            # (e.g. the reference date falls outside the exported
            # historical window) — skip rather than fabricate a value.
            logger.warning("No real VCI or SMI signal for %s on %s — skipping", field_id, current)
            current += timedelta(days=1)
            continue

        fused = fuse_moisture(vci, smi)
        points.append(MoisturePoint(date=current, moisture_value=fused["value"], source=fused["source"]))
        current += timedelta(days=1)
    return points
