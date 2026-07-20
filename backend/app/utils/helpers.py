"""
Small shared utilities used across services/models that don't
belong to any single module: date-window helpers and basic
serialization helpers for numpy arrays in API responses.
"""
from datetime import date, timedelta

import numpy as np


def date_range(start: date, end: date):
    """Yields each date from start to end inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def eight_day_window(reference_date: date) -> tuple[date, date]:
    """Returns the 8-day window ending on reference_date, matching the spec's 8-day ETc cadence."""
    return reference_date - timedelta(days=7), reference_date


def to_serializable(value):
    """Converts numpy scalars/arrays to plain Python types for JSON responses."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def safe_round(value: float | None, ndigits: int = 1) -> float | None:
    """round() that tolerates None without raising."""
    return None if value is None else round(value, ndigits)
