import { describe, it, expect } from "vitest";
import { cropShort, depthColor, colorForMode, CROP_COLORS, STRESS_COLORS, STAGE_COLORS } from "./fieldColors";

describe("cropShort", () => {
  it("shortens the real wintercereal label to Wheat", () => {
    expect(cropShort("Wintercereal_Wheat_or_Mustard")).toBe("Wheat");
  });
  it("shortens the real rice label to Rice", () => {
    expect(cropShort("Rice_Kharif")).toBe("Rice");
  });
  it("shortens the real non-wintercereal label", () => {
    expect(cropShort("Non_wintercereal")).toBe("Non-cereal");
  });
  it("handles missing crop gracefully", () => {
    expect(cropShort(null)).toBe("—");
    expect(cropShort(undefined)).toBe("—");
  });
});

describe("depthColor", () => {
  it("treats zero/negative deficit as 'no irrigation needed' colour", () => {
    expect(depthColor(0)).toBe("#3d5a2c");
    expect(depthColor(-3)).toBe("#3d5a2c");
    expect(depthColor(null)).toBe("#3d5a2c");
    expect(depthColor(undefined)).toBe("#3d5a2c");
  });
  it("buckets a small deficit into the 0-10mm colour", () => {
    expect(depthColor(8.6)).toBe("#7fa8c2"); // real F-K01 value
  });
  it("buckets a mid deficit into the 10-20mm colour", () => {
    expect(depthColor(15)).toBe("#5b8aa6");
  });
  it("buckets a large deficit (e.g. real max 22.8mm) into the 20+ colour", () => {
    expect(depthColor(22.8)).toBe("#345a70");
  });
});

describe("colorForMode", () => {
  const field = {
    crop: "Wintercereal_Wheat_or_Mustard",
    moisture: "high-stress",
    stage: "Flowering",
    advisory: { deficitMm: 22.8 },
  };

  it("colours by crop", () => {
    expect(colorForMode(field, "crop")).toBe(CROP_COLORS["Wintercereal_Wheat_or_Mustard"]);
  });
  it("colours by stress level", () => {
    expect(colorForMode(field, "stress")).toBe(STRESS_COLORS["high-stress"]);
  });
  it("colours by growth stage", () => {
    expect(colorForMode(field, "stage")).toBe(STAGE_COLORS["Flowering"]);
  });
  it("colours by irrigation depth bucket", () => {
    expect(colorForMode(field, "depth")).toBe(depthColor(22.8));
  });
  it("falls back to the default crop colour for an unrecognised crop", () => {
    expect(colorForMode({ crop: "Something_New" }, "crop")).toBe(CROP_COLORS.default);
  });
  it("a field with no active advisory (Maturity-stage cutoff) colours as 'no irrigation needed'", () => {
    // Real post-fix behaviour: Maturity-stage fields get amount_mm=null,
    // so deficitMm is undefined on the advisory — must not crash and
    // must colour as "none", not silently show a stale deficit colour.
    const maturityField = { advisory: { deficitMm: undefined } };
    expect(colorForMode(maturityField, "depth")).toBe("#3d5a2c");
  });
});
