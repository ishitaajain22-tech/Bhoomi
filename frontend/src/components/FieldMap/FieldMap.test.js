import { describe, it, expect } from "vitest";
import { buildVoronoiCells } from "./FieldMap";

// A small real-shaped sample: 6 points loosely modelled on the real
// Kapurthala cluster's scale (tight, sub-0.01-degree spread).
const samplePoints = [
  { id: "F-K01", latitude: 31.398706, longitude: 75.387885 },
  { id: "F-K02", latitude: 31.399102, longitude: 75.388310 },
  { id: "F-K03", latitude: 31.398950, longitude: 75.387600 },
  { id: "F-K04", latitude: 31.399400, longitude: 75.388050 },
  { id: "F-K05", latitude: 31.398500, longitude: 75.388400 },
  { id: "F-K06", latitude: 31.399050, longitude: 75.387950 },
];

describe("buildVoronoiCells", () => {
  it("produces exactly one polygon per field with coordinates", () => {
    const cells = buildVoronoiCells(samplePoints);
    expect(cells).toHaveLength(samplePoints.length);
  });

  it("every returned cell references a real field id from the input", () => {
    const cells = buildVoronoiCells(samplePoints);
    const inputIds = new Set(samplePoints.map((f) => f.id));
    cells.forEach((cell) => expect(inputIds.has(cell.field.id)).toBe(true));
  });

  it("every polygon has at least 3 vertices (a valid closed shape)", () => {
    const cells = buildVoronoiCells(samplePoints);
    cells.forEach((cell) => expect(cell.latlngs.length).toBeGreaterThanOrEqual(3));
  });

  it("polygon vertices are [lat, lon] pairs within the padded bounding box", () => {
    const cells = buildVoronoiCells(samplePoints);
    const [[minLat, minLon], [maxLat, maxLon]] = cells[0].bounds;
    cells.forEach((cell) => {
      cell.latlngs.forEach(([lat, lon]) => {
        expect(lat).toBeGreaterThanOrEqual(minLat);
        expect(lat).toBeLessThanOrEqual(maxLat);
        expect(lon).toBeGreaterThanOrEqual(minLon);
        expect(lon).toBeLessThanOrEqual(maxLon);
      });
    });
  });

  it("silently drops fields missing lat/lon instead of crashing", () => {
    const withMissing = [...samplePoints, { id: "F-BAD", latitude: null, longitude: null }];
    const cells = buildVoronoiCells(withMissing);
    expect(cells.find((c) => c.field.id === "F-BAD")).toBeUndefined();
    expect(cells).toHaveLength(samplePoints.length);
  });

  it("returns an empty array for fewer than 2 points (can't tessellate)", () => {
    expect(buildVoronoiCells([samplePoints[0]])).toEqual([]);
    expect(buildVoronoiCells([])).toEqual([]);
  });
});
