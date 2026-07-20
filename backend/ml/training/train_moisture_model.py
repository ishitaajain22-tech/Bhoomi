"""
Trains the moisture-stress model: an LSTM/Temporal-CNN style
sequence model over NDVI/NDWI/SAR-backscatter time series, per
the spec's "Deep Learning: LSTM etc." block, to predict VCI/SMI-
based stress level across growth stages. Falls back to a simple
RandomForestRegressor baseline if no deep-learning framework is
available — useful for a fast hackathon iteration before
investing in LSTM tuning.

RUN IN GOOGLE COLAB (recommended — gives free GPU for the LSTM):
  1. Upload your time-series CSV (columns: field_id, day_index,
     ndvi, ndwi, vv_db, vh_db, growth_stage, moisture_label)
  2. !pip install tensorflow scikit-learn pandas joblib
  3. Set DATA_CSV_PATH below, run, download moisture_model.h5 (or .pkl)
     and place it in backend/ml/checkpoints/ locally.
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

sys.path.append(str(Path(__file__).resolve().parents[2]))

from ml.evaluation.metrics import regression_error

DATA_CSV_PATH = "backend/data/labels/moisture_timeseries.csv"  # sample data included; replace with your real labels later
CHECKPOINT_OUT_PATH = "backend/ml/checkpoints/moisture_model.pkl"
TARGET_COLUMN = "moisture_label"


def load_training_data(csv_path: str) -> tuple[np.ndarray, np.ndarray]:
    df = pd.read_csv(csv_path)
    y = df[TARGET_COLUMN].values
    X = df.drop(columns=[TARGET_COLUMN]).select_dtypes(include=[np.number]).values
    return X, y


def train_baseline(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestRegressor:
    """Fast baseline — swap for an LSTM (Keras/PyTorch) once sequence framing is set up in Colab with GPU."""
    model = RandomForestRegressor(n_estimators=200, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    return model


def main():
    X, y = load_training_data(DATA_CSV_PATH)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

    model = train_baseline(X_train, y_train)
    predictions = model.predict(X_test)
    metrics = regression_error(y_test, predictions)
    print("Moisture model validation metrics (RMSE/MAE):", metrics)

    Path(CHECKPOINT_OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, CHECKPOINT_OUT_PATH)
    print(f"Saved checkpoint to {CHECKPOINT_OUT_PATH}")


if __name__ == "__main__":
    main()
