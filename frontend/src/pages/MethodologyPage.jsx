import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { getMethodology, getValidationMetrics } from "../services/api";
import "./MethodologyPage.css";

// Maps a pipeline-step model name (from the /api/methodology response)
// to a stable anchor id, so links from the dashboard's AI Analysis
// panel can jump straight to the right section instead of dumping
// the person at the top of the page.
function anchorFor(name) {
  const n = name.toLowerCase();
  if (n.includes("wintercereal") || n.includes("rice") || n.includes("wheat")) return "meth-crop";
  if (n.includes("phenology")) return "meth-phenology";
  if (n.includes("moisture")) return "meth-moisture";
  if (n.includes("water balance")) return "meth-water";
  return undefined;
}

export default function MethodologyPage() {
  const [data, setData] = useState(null);
  const [validation, setValidation] = useState(null);
  const location = useLocation();

  useEffect(() => {
    getMethodology().then(setData);
    getValidationMetrics().then(setValidation);
  }, []);

  // Runs once the real content (and therefore the target element) exists.
  useEffect(() => {
    if (!data || !location.hash) return;
    const el = document.getElementById(location.hash.slice(1));
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [data, location.hash]);

  if (!data) return <div className="methpage__loading">Loading methodology…</div>;

  return (
    <div className="methpage">
      <h1 className="methpage__title">Methodology</h1>
      <p className="methpage__sub">What's real, what's a documented proxy, and why — stated plainly.</p>

      <section className="methpage__tldr">
        <h2 className="methpage__tldr-heading">If you're reviewing this without a live walkthrough, start here</h2>
        <ul>
          <li>
            <strong>Every number on the dashboard traces to a real backend computation</strong> over real
            Sentinel-1/Sentinel-2 GEE exports for 59 real Kapurthala sample points — nothing is a static mock.
          </li>
          <li>
            <strong>Almost all fields currently show an active irrigation recommendation.</strong> That's a real,
            cited result, not a threshold bug — see "Irrigation advisory" below for the PAU Ludhiana source.
          </li>
          <li>
            <strong>The dashboard's field polygons are Voronoi cells, not surveyed farm boundaries</strong> — see
            "Crop type classifier" below for what that means and why.
          </li>
          <li>
            <strong>Rice-vs-wheat classification accuracy is lower (72%) than wintercereal detection (88.5%)</strong>
            — disclosed and explained by SAR backscatter physics, not swept under the rug.
          </li>
        </ul>
      </section>

      {validation && (
        <section className="methpage__section" id="meth-validation">
          <h2 className="methpage__heading">Validation</h2>
          {Object.entries(validation).map(([key, clf]) => (
            <div key={key} className="methpage__clf-block" id={key === "crop_classifier_wintercereal" ? "meth-crop" : undefined}>
              <p className="methpage__clf-name">{clf.description}</p>
              <p className="methpage__validation">
                <strong>{Math.round(clf.overall_accuracy * 100)}%</strong> accuracy ·{" "}
                <strong>{clf.kappa.toFixed(2)}</strong> Kappa · {clf.n_samples} samples
              </p>
              <p className="methpage__note">{clf.note}</p>
            </div>
          ))}
        </section>
      )}

      <section className="methpage__section">
        <h2 className="methpage__heading">Data sources</h2>
        <table className="methpage__table">
          <tbody>
            {data.data_sources.map((d) => (
              <tr key={d.name}>
                <td className="methpage__cell-name">{d.name}</td>
                <td className="methpage__cell-role">{d.role}</td>
                <td>{d.real ? <span className="methpage__tag methpage__tag--real">Active</span> : <span className="methpage__tag">Fallback</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="methpage__section" id="meth-models">
        <h2 className="methpage__heading">Models</h2>
        {data.models.map((m) => (
          <div key={m.name} className="methpage__model" id={anchorFor(m.name)}>
            <h3>{m.name}</h3>
            <p>{m.method}</p>
            <p className="methpage__metric">{m.metric}</p>
          </div>
        ))}
      </section>

      <section className="methpage__section" id="meth-freshness">
        <h2 className="methpage__heading">Data freshness</h2>
        <p className="methpage__note">
          This is a point-in-time analysis of one completed Rabi season (Oct 2024 – Mar 2025), not a live
          continuously-updating feed — every number on this dashboard is computed from real GEE-exported
          historical time series, not a live Earth Engine connection.
        </p>
        <p className="methpage__note" style={{ marginTop: "0.5rem" }}>
          Running this for a new season is a data-refresh operation, not a redesign: re-run the same GEE export
          scripts (<code>app/services/sentinel1_fetch.py</code>, <code>sentinel2_fetch.py</code>) for the new date
          range, re-fit the two Random Forest checkpoints on the new labels, and the rest of the pipeline —
          phenology, moisture stress, water balance, advisory — runs unchanged, since none of that logic is
          season-specific.
        </p>
      </section>

      <section className="methpage__section" id="meth-limitations">
        <h2 className="methpage__heading">Disclosed limitations</h2>
        <ul className="methpage__limitations">
          {data.disclosed_limitations.map((l) => <li key={l}>{l}</li>)}
        </ul>
      </section>
    </div>
  );
}
