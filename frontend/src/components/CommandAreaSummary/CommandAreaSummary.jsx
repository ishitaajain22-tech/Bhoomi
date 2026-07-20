import "./CommandAreaSummary.css";

export default function CommandAreaSummary({ data }) {
  if (!data) return null;

  return (
    <div className="cas">
      <p className="cas__eyebrow">Canal Command Area</p>
      <h3 className="cas__title">{data.area_name}</h3>

      <div className="cas__stats">
        <div className="cas__stat">
          <span className="cas__stat-value">{data.fields_needing_irrigation}/{data.total_fields}</span>
          <span className="cas__stat-label">fields need irrigation now</span>
        </div>
        <div className="cas__stat">
          <span className="cas__stat-value">{data.fields_at_risk_pct}%</span>
          <span className="cas__stat-label">of command area at risk</span>
        </div>
        <div className="cas__stat">
          <span className="cas__stat-value">{data.total_irrigation_volume_mm}<small>mm</small></span>
          <span className="cas__stat-label">total irrigation volume needed</span>
        </div>
      </div>
    </div>
  );
}
