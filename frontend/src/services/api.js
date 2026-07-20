import { fields as mockFields, coverageStats, moistureTimeline } from "../data/mockData";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function safeFetch(path, fallback) {
  try {
    const res = await fetch(`${BASE_URL}${path}`);
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    return await res.json();
  } catch {
    // Backend not running yet — serve demo data so the interface always feels alive.
    return fallback;
  }
}

function toFieldCard(fieldMeta, advisory) {
  return {
    id: fieldMeta.field_id,
    latitude: fieldMeta.latitude,
    longitude: fieldMeta.longitude,
    name: `Field ${fieldMeta.field_id}`,
    village: "Kapurthala, Punjab",
    crop: advisory.predicted_crop,
    stage: advisory.growth_stage,
    area: "—",
    moisture: advisory.stress_level,
    moistureValue: advisory.moisture_value,
    advisory: {
      action: advisory.action,
      amount: advisory.amount_mm ? `≈${advisory.amount_mm} mm` : "—",
      reason: advisory.reason,
      confidence: advisory.confidence,
      source: advisory.data_source,
      sosDate: advisory.sos_date,
      peakGrowthDate: advisory.peak_growth_date,
      daysAfterSos: advisory.days_after_sos,
      vci: advisory.vci,
      smi: advisory.smi,
      ndwi: advisory.ndwi,
      stressLevel: advisory.stress_level,
      moistureValue: advisory.moisture_value,
      etcMm: advisory.etc_mm,
      etoMmPerDay: advisory.eto_mm_per_day,
      rainfallMm: advisory.rainfall_mm,
      deficitMm: advisory.deficit_mm,
      predictedCropMulticlass: advisory.predicted_crop_multiclass,
      confidenceMulticlass: advisory.confidence_multiclass,
    },
  };
}

export async function pingBackend() {
  try {
    const res = await fetch(`${BASE_URL}/health`, { signal: AbortSignal.timeout(3000) });
    return res.ok;
  } catch {
    return false;
  }
}

export async function getFields() {
  try {
    const fieldList = await fetch(`${BASE_URL}/api/fields`).then((r) => {
      if (!r.ok) throw new Error("fields fetch failed");
      return r.json();
    });

    const cards = await Promise.all(
      fieldList.map(async (f) => {
        const advisory = await fetch(`${BASE_URL}/api/advisory/${f.field_id}`).then((r) => r.json());
        return toFieldCard(f, advisory);
      })
    );
    return cards;
  } catch {
    // Backend not running yet — serve demo data so the interface always feels alive.
    return mockFields;
  }
}

export function getCoverageStats() {
  return safeFetch("/api/coverage", coverageStats);
}

export function getCommandAreaAdvisory(areaId = "CA-KPT01") {
  return safeFetch(`/api/command-areas/${areaId}/advisory`, null);
}

export function getValidationMetrics() {
  return safeFetch("/api/validation", null);
}

export function getFieldPhenology(fieldId) {
  return safeFetch(`/api/fields/${fieldId}/phenology`, null);
}

export function getMethodology() {
  return safeFetch("/api/methodology", null);
}

export function getMoistureTimeline(fieldId) {
  return safeFetch(`/api/moisture/${fieldId}/timeline`, moistureTimeline);
}

export function getAdvisory(fieldId) {
  const field = mockFields.find((f) => f.id === fieldId);
  return safeFetch(`/api/advisory/${fieldId}`, field?.advisory ?? null);
}
