import "./AdvisoryCard.css";

const confidenceLabel = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
};

function WaterBalanceBars({ etcMm, rainfallMm, deficitMm }) {
  const max = Math.max(etcMm, rainfallMm, 1);
  return (
    <div className="advisory__waterbar">
      <div className="advisory__waterbar-row">
        <span className="advisory__waterbar-label">ETc (demand)</span>
        <div className="advisory__waterbar-track">
          <div className="advisory__waterbar-fill advisory__waterbar-fill--demand" style={{ width: `${(etcMm / max) * 100}%` }} />
        </div>
        <span className="advisory__waterbar-value">{etcMm} mm</span>
      </div>
      <div className="advisory__waterbar-row">
        <span className="advisory__waterbar-label">Rainfall</span>
        <div className="advisory__waterbar-track">
          <div className="advisory__waterbar-fill advisory__waterbar-fill--rain" style={{ width: `${(rainfallMm / max) * 100}%` }} />
        </div>
        <span className="advisory__waterbar-value">{rainfallMm} mm</span>
      </div>
      <div className="advisory__waterbar-deficit">
        = <strong>{deficitMm > 0 ? `${deficitMm} mm deficit` : `${Math.abs(deficitMm)} mm surplus`}</strong>
      </div>
    </div>
  );
}

export default function AdvisoryCard({ field }) {
  if (!field) return null;
  const { advisory } = field;
  const urgent = advisory.action.toLowerCase().includes("irrigate");

  return (
    <div className={`advisory ${urgent ? "advisory--urgent" : "advisory--ok"}`}>
      <div className="advisory__top">
        <span className="advisory__field">{field.id}</span>
        <span className="advisory__crop">{field.crop} · {field.stage}</span>
      </div>

      {advisory.sosDate && (
        <div className="advisory__phenology">
          <span className="advisory__phenology-badge">SOS detected {advisory.sosDate}</span>
          {advisory.daysAfterSos != null && <span className="advisory__phenology-sub">{advisory.daysAfterSos} days into season</span>}
          {advisory.peakGrowthDate && <span className="advisory__phenology-sub">Peak growth {advisory.peakGrowthDate}</span>}
        </div>
      )}

      <p className="advisory__action">{advisory.action}</p>
      {advisory.amount !== "—" && <p className="advisory__amount">{advisory.amount}</p>}

      {advisory.etcMm != null && (
        <WaterBalanceBars etcMm={advisory.etcMm} rainfallMm={advisory.rainfallMm} deficitMm={advisory.deficitMm} />
      )}

      <div className="advisory__indices">
        {advisory.vci != null && <span className="advisory__index-chip advisory__index-chip--vci">VCI {advisory.vci}</span>}
        {advisory.smi != null && <span className="advisory__index-chip advisory__index-chip--smi">SMI {advisory.smi}</span>}
        {advisory.ndwi != null && <span className="advisory__index-chip">NDWI {advisory.ndwi?.toFixed(2)}</span>}
        {advisory.predictedCropMulticlass && (
          <span className="advisory__index-chip advisory__index-chip--multi">
            {advisory.predictedCropMulticlass.replace("_", " ")}
            {advisory.confidenceMulticlass && ` · ${Math.round(advisory.confidenceMulticlass * 100)}%`}
          </span>
        )}
        <span className="advisory__index-chip">{advisory.stressLevel}</span>
      </div>

      <p className="advisory__reason">{advisory.reason}</p>

      <div className="advisory__meta">
        <span className="advisory__source">{advisory.source}</span>
        <span className="advisory__confidence">{confidenceLabel[advisory.confidence]}</span>
      </div>
    </div>
  );
}
