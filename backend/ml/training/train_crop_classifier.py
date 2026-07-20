"""
Trains the Random Forest crop-type classifier on multi-temporal
spectral profiles + GLCM textural features, validates against
ground-truth labels (Overall Accuracy + Kappa), and saves the
checkpoint that app/models/crop_classifier.py loads at inference.

RUN IN GOOGLE COLAB (recommended for this hackathon):
  1. Upload or mount your AOI's labeled ground-truth CSV
     (columns: field_id, ndvi_t1..tN, ndwi_t1..tN, texture_*, crop_label)
  2. !pip install scikit-learn pandas joblib
  3. Set DATA_CSV_PATH below to your uploaded file's path
  4. Run this script; download crop_classifier.pkl at the end
     and place it in backend/ml/checkpoints/ locally.

Can also be run locally: `python train_crop_classifier.py`
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.append(str(Path(__file__).resolve().parents[2]))  # allow `app.*` imports when run standalone

from app.models.crop_classifier import train_model, validate_model
from ml.evaluation.metrics import classification_report

# --- Configure for your environment ---
DATA_CSV_PATH = "backend/data/labels/crop_ground_truth_real.csv"  # real GEE-derived data (Kapurthala AOI)
CHECKPOINT_OUT_PATH = "backend/ml/checkpoints/crop_classifier.pkl"
LABEL_COLUMN = "crop_label"
FEATURE_COLUMNS = ["ndvi_t1", "ndwi_t1", "vv", "vh"]  # crop_confidence excluded — leaks the WorldCereal label


def load_training_data(csv_path: str) -> tuple[np.ndarray, np.ndarray]:
    """
    Loads the real GEE-derived ground truth CSV (ndvi_t1, ndwi_t1, vv,
    vh, crop_label). crop_confidence is intentionally excluded as a
    feature since it's WorldCereal's own confidence in the label
    itself — including it would be data leakage, not a real signal.
    """
    df = pd.read_csv(csv_path)
    labels = df[LABEL_COLUMN].values
    features = df[FEATURE_COLUMNS].values
    return features, labels


def main():
    features, labels = load_training_data(DATA_CSV_PATH)
    X_train, X_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.25, random_state=42, stratify=labels
    )

    model = train_model(X_train, y_train)
    metrics = validate_model(model, X_test, y_test)
    report = classification_report(y_test, model.predict(X_test))

    print("Validation metrics:", metrics)
    print("Full classification report:", report)

    Path(CHECKPOINT_OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, CHECKPOINT_OUT_PATH)
    print(f"Saved checkpoint to {CHECKPOINT_OUT_PATH}")


if __name__ == "__main__":
    main()
