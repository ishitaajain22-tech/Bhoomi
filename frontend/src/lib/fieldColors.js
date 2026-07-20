// Pure field-classification -> colour/label logic, pulled out of
// Dashboard.jsx so it can actually be unit tested (see
// fieldColors.test.js) instead of only being exercised by clicking
// around the rendered app.
//
// Palette is deliberately restrained and grounded in the real
// subject matter, matching styles/tokens.css:
//  - wheat gold (#c9a24b)  -> the crop itself, and the app's one
//    primary accent, reused here because "wheat = gold" is an
//    intuitive, grounded mapping, not an arbitrary category color.
//  - slate-blue (#5b8aa6)  -> rice AND water/irrigation-depth data.
//    Also intentional: rice paddies are flooded, water is blue.
//  - a real green -> amber -> rust ramp for STRESS and DEPTH data
//    specifically, because stress/urgency is a legitimate case for
//    traffic-light semantics (unlike using alarm colors on prose).

export const CROP_COLORS = {
  "Wintercereal_Wheat_or_Mustard": "#c9a24b",
  "Rice_Kharif": "#5b8aa6",
  "Non_wintercereal": "#6b7280",
  default: "#7a9b5c",
};

export const STRESS_COLORS = {
  "adequate": "#7a9b5c",
  "moderate-stress": "#c4863a",
  "high-stress": "#a6472b",
};

export const STAGE_COLORS = {
  "Sowing": "#c3d1ab",
  "Vegetative": "#7a9b5c",
  "Flowering": "#4f6b3a",
  "Maturity": "#a6472b",
};

export const STAGE_ORDER = ["Sowing", "Vegetative", "Flowering", "Maturity"];

export function cropShort(crop) {
  if (!crop) return "—";
  if (crop.includes("Wheat")) return "Wheat";
  if (crop.includes("Rice")) return "Rice";
  if (crop.includes("Non")) return "Non-cereal";
  return crop.slice(0, 8);
}

// Deficit (mm) -> irrigation-depth colour bucket, matches the legend
// shown under the irrigation mini-map (None / 0-10 / 10-20 / 20+).
export function depthColor(deficitMm) {
  const d = deficitMm ?? 0;
  if (d <= 0) return "#3d5a2c";
  if (d <= 10) return "#7fa8c2";
  if (d <= 20) return "#5b8aa6";
  return "#345a70";
}

export function colorForMode(field, mode) {
  if (mode === "crop") return CROP_COLORS[field.crop] || CROP_COLORS.default;
  if (mode === "stress") return STRESS_COLORS[field.moisture] || "#6b7280";
  if (mode === "stage") return STAGE_COLORS[field.stage] || "#7a9b5c";
  if (mode === "depth") return depthColor(field.advisory?.deficitMm);
  return "#7a9b5c";
}
