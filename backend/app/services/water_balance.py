"""
Real 8-day crop water balance: ETc (crop water demand) vs rainfall
received, producing a water deficit in mm — matching the spec's
"Crop Water Balance / Crop Water Requirement" block. Loads real
CHIRPS rainfall + GRIDMET ETo time series (exported via
gee_water_balance_timeseries.js) when available, using the SAME
system:index-based stable point grouping fix that was needed for
the SAR series (per-image reprojection drift affects these
collections too).

Falls back to fixed placeholder constants when no real export is
present yet, so the pipeline stays runnable end-to-end either way.
"""
import json
from datetime import date, datetime, timedelta

from app.core.logger import get_logger

logger = get_logger(__name__)

_RAINFALL_CSV_PATH = "data/labels/bhoomi_rainfall_timeseries.csv"
_ETO_CSV_PATH = "data/labels/bhoomi_pet_timeseries.csv"  # MOD16A2 PET — replaces GRIDMET, which doesn't cover India

# MOD16A2 PET band scale factor — raw values are in units of
# 0.1 mm per 8-day composite period.
_MOD16_PET_SCALE = 0.1

_rainfall_cache: dict | None = None
_eto_cache: dict | None = None

# Crop coefficient (Kc) by growth stage — FAO-56 style placeholder.
KC_BY_STAGE = {"Sowing": 0.35, "Vegetative": 0.75, "Flowering": 1.15, "Maturity": 0.6}

# Fallback constants used only when no real export is present.
_FALLBACK_ETO_MM_PER_DAY = 4.5
_FALLBACK_RAINFALL_MM_8DAY = 20.0


def _load_point_series(csv_path: str, value_column: str) -> dict[str, tuple[list[date], list[float]]]:
    """
    Generic loader for a single-value-per-date GEE export (rainfall
    or ETo), grouped by the stable point index in system:index rather
    than raw coordinates — same fix required for the SAR series,
    since CHIRPS/GRIDMET resampling can shift point coordinates
    slightly between dates too.
    """
    import pandas as pd

    df = pd.read_csv(csv_path)
    df["point_idx"] = df["system:index"].apply(lambda s: int(s.split("_")[-2]))
    df["parsed_date"] = df["date"].apply(lambda d: datetime.strptime(d, "%Y-%m-%d").date())

    grouped = df.groupby(["point_idx", "parsed_date"], as_index=False)[value_column].mean()
    coords_by_idx = df.groupby("point_idx")[".geo"].first().apply(lambda x: json.loads(x)["coordinates"])

    series_by_point = {}
    for point_idx, group in grouped.groupby("point_idx"):
        group_sorted = group.sort_values("parsed_date")
        lon, lat = coords_by_idx[point_idx]
        point_id = f"{lat:.6f}_{lon:.6f}"
        series_by_point[point_id] = (
            group_sorted["parsed_date"].tolist(),
            group_sorted[value_column].tolist(),
        )
    return series_by_point


def _get_series_near(cache: dict, lat: float, lon: float):
    if not cache:
        return None

    def point_distance(point_id: str) -> float:
        p_lat, p_lon = (float(v) for v in point_id.split("_"))
        return (p_lat - lat) ** 2 + (p_lon - lon) ** 2

    nearest_id = min(cache, key=point_distance)
    return cache[nearest_id]


def get_rainfall_8day_mm(lat: float, lon: float, end_date: date) -> float:
    """Real 8-day cumulative rainfall (mm) ending on end_date, summed from real CHIRPS daily values."""
    global _rainfall_cache
    if _rainfall_cache is None:
        try:
            _rainfall_cache = _load_point_series(_RAINFALL_CSV_PATH, "precipitation")
        except FileNotFoundError:
            _rainfall_cache = {}

    series = _get_series_near(_rainfall_cache, lat, lon)
    if series is None:
        logger.warning("No real rainfall data available — using fallback constant %.1f mm", _FALLBACK_RAINFALL_MM_8DAY)
        return _FALLBACK_RAINFALL_MM_8DAY

    dates, values = series
    window_start = end_date - timedelta(days=7)
    in_window = [v for d, v in zip(dates, values) if window_start <= d <= end_date]
    if not in_window:
        logger.warning("No real rainfall observations in window ending %s — using fallback", end_date)
        return _FALLBACK_RAINFALL_MM_8DAY
    return round(sum(in_window), 1)


def get_eto_mm_per_day_mod16(lat: float, lon: float, on_date: date, tolerance_days: int = 5) -> float:
    """
    Real reference ET (mm/day), derived from MODIS MOD16A2's PET
    band (8-day composite, units of 0.1mm — scale + /8 applied
    below). Secondary path: this AOI's MOD16A2 export came back
    empty (quality-masking over heterogeneous small-holder cropland),
    so this is currently a fallback within get_eto_mm_per_day, kept
    ready in case a non-empty MOD16A2 export becomes available.
    """
    global _eto_cache
    if _eto_cache is None:
        try:
            _eto_cache = _load_point_series(_ETO_CSV_PATH, "PET")
        except FileNotFoundError:
            _eto_cache = {}

    series = _get_series_near(_eto_cache, lat, lon)
    if series is None:
        return _FALLBACK_ETO_MM_PER_DAY

    dates, raw_values = series
    if not dates:
        return _FALLBACK_ETO_MM_PER_DAY
    closest_idx = min(range(len(dates)), key=lambda i: abs((dates[i] - on_date).days))
    if abs((dates[closest_idx] - on_date).days) > tolerance_days:
        return _FALLBACK_ETO_MM_PER_DAY

    pet_8day_total_mm = raw_values[closest_idx] * _MOD16_PET_SCALE
    return round(pet_8day_total_mm / 8, 2)


def get_eto_mm_per_day(lat: float, lon: float, on_date: date, tolerance_days: int = 5) -> float:
    """
    Real reference ET (mm/day). Primary path is Thornthwaite on real
    ERA5-Land temperature data (get_eto_mm_per_day_thornthwaite) —
    MOD16A2's PET band returned empty over this AOI (its quality
    masking commonly blanks small, heterogeneous cropland pixels),
    so Thornthwaite is the one actually backed by real data right
    now. Falls through to MOD16A2 (in case it has data) then the
    fixed constant, in that order.
    """
    thornthwaite_result = get_eto_mm_per_day_thornthwaite(lat, lon, on_date)
    if thornthwaite_result != _FALLBACK_ETO_MM_PER_DAY:
        return thornthwaite_result
    return get_eto_mm_per_day_mod16(lat, lon, on_date, tolerance_days)


def compute_etc(growth_stage: str, eto_mm_per_day: float, window_days: int = 8) -> float:
    """8-day crop water demand: ETc = Kc x ETo x window_days."""
    kc = KC_BY_STAGE.get(growth_stage, 0.6)
    return round(kc * eto_mm_per_day * window_days, 1)


def compute_water_deficit(etc_mm: float, rainfall_mm: float) -> float:
    """Deficit = crop demand minus rainfall received over the same window. Negative = surplus."""
    return round(etc_mm - rainfall_mm, 1)


# ===================================================================
# Thornthwaite ETo — used because MOD16A2's quality masking blanked
# out PET over our small heterogeneous AOI (common over fragmented
# Indian cropland). Thornthwaite only needs mean temperature + a
# day-length factor derived from latitude/day-of-year, both of which
# we have real data/geometry for.
# ===================================================================
import math

_TEMPERATURE_CSV_PATH = "data/labels/bhoomi_temperature_timeseries.csv"
_thornthwaite_cache: dict | None = None


def day_length_hours(latitude_deg: float, day_of_year: int) -> float:
    """
    Mean daylight hours for a given latitude and day-of-year, via
    solar declination — the standard day-length adjustment
    Thornthwaite's formula requires.
    """
    lat_rad = math.radians(latitude_deg)
    declination = math.radians(23.45 * math.sin(math.radians(360 * (284 + day_of_year) / 365)))
    cos_hour_angle = -math.tan(lat_rad) * math.tan(declination)
    cos_hour_angle = max(-1.0, min(1.0, cos_hour_angle))
    hour_angle_deg = math.degrees(math.acos(cos_hour_angle))
    return (2 * hour_angle_deg) / 15


def compute_thornthwaite_monthly_pet(monthly_mean_temp_c: dict, latitude: float) -> dict:
    """
    Computes Thornthwaite monthly PET (mm/month) for each month in
    monthly_mean_temp_c (keyed by (year, month) -> mean temp in C).

    Honest limitation: Thornthwaite's heat index (I) is defined over
    a full 12-month annual cycle. With only ~6 months of real data
    (Oct-Mar, a Rabi season export), I is computed from the months
    actually available rather than a true annual cycle — a disclosed
    approximation, not a full climatological Thornthwaite estimate.
    """
    import calendar

    heat_index = sum((t / 5) ** 1.514 for t in monthly_mean_temp_c.values() if t > 0)
    a = (6.75e-7 * heat_index**3) - (7.71e-5 * heat_index**2) + (1.792e-2 * heat_index) + 0.49239

    monthly_pet = {}
    for (year, month), t in monthly_mean_temp_c.items():
        if t <= 0 or heat_index <= 0:
            monthly_pet[(year, month)] = 0.0
            continue
        unadjusted = 16 * (10 * t / heat_index) ** a
        days_in_month = calendar.monthrange(year, month)[1]
        mid_month_day_of_year = date(year, month, days_in_month // 2 + 1).timetuple().tm_yday
        n_hours = day_length_hours(latitude, mid_month_day_of_year)
        adjusted = unadjusted * (n_hours / 12) * (days_in_month / 30)
        monthly_pet[(year, month)] = round(adjusted, 2)
    return monthly_pet


def _build_thornthwaite_lookup(csv_path: str, latitude: float) -> dict:
    """Loads real daily temperature, aggregates to monthly means, returns {(year, month): mm/day} ETo."""
    import pandas as pd

    df = pd.read_csv(csv_path)
    df["parsed_date"] = df["date"].apply(lambda d: datetime.strptime(d, "%Y-%m-%d").date())
    df["temp_c"] = df["temperature_2m"] - 273.15  # Kelvin -> Celsius
    df["year_month"] = df["parsed_date"].apply(lambda d: (d.year, d.month))

    monthly_mean_temp_c = df.groupby("year_month")["temp_c"].mean().to_dict()
    monthly_pet_mm = compute_thornthwaite_monthly_pet(monthly_mean_temp_c, latitude)

    import calendar
    return {
        ym: round(pet_mm / calendar.monthrange(*ym)[1], 2)
        for ym, pet_mm in monthly_pet_mm.items()
    }


def get_eto_mm_per_day_thornthwaite(lat: float, lon: float, on_date: date) -> float:
    """
    Real ETo (mm/day) for on_date, via Thornthwaite on real ERA5-Land
    temperature data — the active ETo path, since MOD16A2 returned
    empty over this AOI. Falls back to the fixed constant if no real
    temperature export is present.
    """
    global _thornthwaite_cache
    if _thornthwaite_cache is None:
        try:
            _thornthwaite_cache = _build_thornthwaite_lookup(_TEMPERATURE_CSV_PATH, lat)
        except FileNotFoundError:
            _thornthwaite_cache = {}

    if not _thornthwaite_cache:
        return _FALLBACK_ETO_MM_PER_DAY

    key = (on_date.year, on_date.month)
    return _thornthwaite_cache.get(key, _FALLBACK_ETO_MM_PER_DAY)
