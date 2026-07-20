"""
Reshapes the multi-class WorldCereal export (bhoomi_multiclass_worldcereal.csv,
columns: wintercereals, maize, springcereals classification scores)
into a single real multi-class crop_label column, by taking the
crop type with the highest real classification confidence per
point. Pixels where no product fires above threshold are labeled
'Other/Unclassified' rather than forced into a guessed class.

Run this after exporting via gee_multiclass_worldcereal.js and
downloading the CSV into backend/data/labels/.
"""
import json

import pandas as pd

INPUT_CSV = "data/labels/bhoomi_multiclass_worldcereal.csv"
OUTPUT_CSV = "data/labels/crop_ground_truth_multiclass.csv"
CONFIDENCE_THRESHOLD = 50  # WorldCereal classification scores are 0-100

PRODUCT_COLUMNS = ["wintercereals", "maize", "springcereals"]
LABEL_NAMES = {
    "wintercereals": "Wintercereal_Wheat_or_Mustard",
    "maize": "Maize",
    "springcereals": "Springcereal",
}


def assign_multiclass_label(row) -> str:
    scores = {col: row[col] for col in PRODUCT_COLUMNS if col in row and pd.notna(row[col])}
    if not scores:
        return "Other_Unclassified"
    best_product, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score < CONFIDENCE_THRESHOLD:
        return "Other_Unclassified"
    return LABEL_NAMES[best_product]


def main():
    df = pd.read_csv(INPUT_CSV)
    df["crop_label"] = df.apply(assign_multiclass_label, axis=1)

    print("Real multi-class label distribution:")
    print(df["crop_label"].value_counts())

    # NDVI/NDWI/VV/VH aren't in this export (WorldCereal-only sample) —
    # merge with the existing real ground truth on nearest point if
    # available, otherwise this CSV alone gives label distribution
    # only, useful for sanity-checking before a fuller multi-class
    # ground-truth merge.
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
