"""
Shared evaluation metrics for both the crop classifier and the
moisture model — Overall Accuracy + Kappa for classification
(per spec's evaluation parameters), plus the coverage-comparison
stat that backs the "fused vs optical-only" wow-factor claim on
the pitch slide. Run standalone or imported by training scripts.
"""
import numpy as np
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix


def classification_report(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Overall Accuracy + Kappa coefficient, as named in the spec's evaluation parameters."""
    return {
        "overall_accuracy": round(accuracy_score(y_true, y_pred), 3),
        "kappa": round(cohen_kappa_score(y_true, y_pred), 3),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }


def regression_error(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """RMSE/MAE for continuous outputs like moisture index or water deficit."""
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    return {"rmse": round(rmse, 3), "mae": round(mae, 3)}


def coverage_comparison(total_dates: int, optical_usable_dates: int, fused_usable_dates: int) -> dict:
    """
    Quantifies the optical-only vs fused coverage gap over a date
    window — the exact number that should back the slide claim
    "X% coverage during monsoon vs Y% optical-only".
    """
    return {
        "optical_coverage_pct": round(optical_usable_dates / total_dates * 100, 1),
        "fused_coverage_pct": round(fused_usable_dates / total_dates * 100, 1),
        "coverage_gain_pct": round((fused_usable_dates - optical_usable_dates) / total_dates * 100, 1),
    }
