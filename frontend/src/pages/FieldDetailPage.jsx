import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import AdvisoryCard from "../components/AdvisoryCard/AdvisoryCard";
import { getFieldPhenology, getAdvisory } from "../services/api";
import "./FieldDetailPage.css";

function PhenologyChart({ series }) {
  if (!series?.length) return null;
  const W = 640, H = 180, PAD = 30;
  const max = Math.max(...series.map((d) => d.ndvi), 1);
  const stepX = (W - PAD * 2) / (series.length - 1);
  const points = series.map((d, i) => ({
    x: PAD + i * stepX,
    y: H - PAD - (d.ndvi / max) * (H - PAD * 1.6),
  }));
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="phenochart">
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} className="phenochart__axis" />
      <path d={path} className="phenochart__line" fill="none" />
      {points.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="2.5" className="phenochart__point" />)}
    </svg>
  );
}

export default function FieldDetailPage() {
  const { fieldId } = useParams();
  const [phenology, setPhenology] = useState(null);
  const [advisory, setAdvisory] = useState(null);

  useEffect(() => {
    getFieldPhenology(fieldId).then(setPhenology);
    getAdvisory(fieldId).then(setAdvisory);
  }, [fieldId]);

  return (
    <div className="fielddetail">
      <Link to="/" className="fielddetail__back">← Back to overview</Link>
      <h1 className="fielddetail__title">Field {fieldId}</h1>
      <p className="fielddetail__sub">Full real phenology, moisture, and water-balance detail</p>

      {phenology && (
        <section className="fielddetail__section">
          <h2 className="fielddetail__heading">Phenology — real NDVI series</h2>
          <p className="fielddetail__meta">
            SOS detected <strong>{phenology.sos_date || "not detected"}</strong> · Peak growth{" "}
            <strong>{phenology.peak_growth_date || "—"}</strong> · Stage <strong>{phenology.growth_stage}</strong>
            {phenology.days_after_sos != null && <> · {phenology.days_after_sos} days into season</>}
          </p>
          <PhenologyChart series={phenology.ndvi_series} />
        </section>
      )}

      {advisory && (
        <section className="fielddetail__section">
          <h2 className="fielddetail__heading">Irrigation advisory</h2>
          <AdvisoryCard field={{ advisory: {
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
            stressLevel: advisory.stress_level,
            etcMm: advisory.etc_mm,
            etoMmPerDay: advisory.eto_mm_per_day,
            rainfallMm: advisory.rainfall_mm,
            deficitMm: advisory.deficit_mm,
          }, id: fieldId, name: `Field ${fieldId}`, crop: advisory.predicted_crop, stage: advisory.growth_stage }} />
        </section>
      )}
    </div>
  );
}
