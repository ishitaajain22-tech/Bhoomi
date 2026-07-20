import "./ValidationBadge.css";

export default function ValidationBadge({ metrics }) {
  if (!metrics) return null;

  return (
    <div className="vbadge">
      <div className="vbadge__metric">
        <span className="vbadge__value">{Math.round(metrics.overall_accuracy * 100)}%</span>
        <span className="vbadge__label">Overall Accuracy</span>
      </div>
      <div className="vbadge__divider" />
      <div className="vbadge__metric">
        <span className="vbadge__value">{metrics.kappa.toFixed(2)}</span>
        <span className="vbadge__label">Kappa coefficient</span>
      </div>
      <div className="vbadge__divider" />
      <div className="vbadge__meta">
        <span>{metrics.n_samples} real samples · {metrics.model}</span>
        <span className="vbadge__honest">{metrics.note}</span>
      </div>
    </div>
  );
}
