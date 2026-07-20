import "./MissionStats.css";

export default function MissionStats({ commandArea, validation }) {
  if (!commandArea && !validation) return null;

  // Validation endpoint now returns two classifiers keyed by name
  const rabi = validation?.crop_classifier_wintercereal;
  const multi = validation?.crop_classifier_rice_wheat;

  return (
    <div className="mstats">
      {commandArea && (
        <>
          <div className="mstats__item mstats__item--alert">
            <span className="mstats__value">
              {commandArea.fields_needing_irrigation}<small>/{commandArea.total_fields}</small>
            </span>
            <span className="mstats__label">fields need irrigation</span>
          </div>
          <div className="mstats__item">
            <span className="mstats__value">
              {commandArea.total_irrigation_volume_mm}<small>mm</small>
            </span>
            <span className="mstats__label">total volume · {commandArea.area_name}</span>
          </div>
          <div className="mstats__sep" />
        </>
      )}

      {rabi && (
        <div className="mstats__classifier">
          <p className="mstats__classifier-label">Rabi wheat classifier</p>
          <div className="mstats__classifier-row">
            <span className="mstats__badge mstats__badge--acc">
              {Math.round(rabi.overall_accuracy * 100)}% acc
            </span>
            <span className="mstats__badge">κ {rabi.kappa.toFixed(2)}</span>
          </div>
          <p className="mstats__classifier-sub">{rabi.n_samples} real samples · ESA WorldCereal</p>
        </div>
      )}

      {multi && (
        <div className="mstats__classifier">
          <p className="mstats__classifier-label">Rice vs Wheat · multi-class</p>
          <div className="mstats__classifier-row">
            <span className="mstats__badge mstats__badge--acc">
              {Math.round(multi.overall_accuracy * 100)}% acc
            </span>
            <span className="mstats__badge">κ {multi.kappa.toFixed(2)}</span>
          </div>
          <p className="mstats__classifier-sub">
            {multi.n_samples} samples · Dynamic World · VV backscatter key feature
          </p>
        </div>
      )}
    </div>
  );
}
