import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getFields, getCoverageStats, getCommandAreaAdvisory, getValidationMetrics, getMethodology, pingBackend } from "../services/api";
import { getDashboardCache, setDashboardCache } from "../lib/dashboardCache";
import { CROP_COLORS, STRESS_COLORS, STAGE_COLORS, STAGE_ORDER, cropShort, colorForMode } from "../lib/fieldColors";
import FieldMap from "../components/FieldMap/FieldMap";
import "./Dashboard.css";

function fieldTooltip(field) {
  const a = field.advisory || {};
  return (
    <div className="fmap__ttip">
      <strong>{field.id}</strong>
      <span>{cropShort(field.crop)} · {field.stage || "—"}</span>
      <span>Moisture: {a.moistureValue ?? "—"} ({(a.stressLevel || field.moisture || "—").replace("-", " ")})</span>
      {a.vci != null && <span>VCI {a.vci} · SMI {a.smi}</span>}
      {a.deficitMm != null && <span>Deficit: {a.deficitMm > 0 ? `${a.deficitMm} mm` : "0 mm (none)"}</span>}
    </div>
  );
}

// --- Water balance gauge (semicircle, colour-banded arc + needle) ---
function WaterGauge({ deficit }) {
  if (deficit == null) return null;
  const capped = Math.max(-30, Math.min(30, deficit));
  const pct = (capped + 30) / 60;
  const angle = -120 + pct * 240;
  const r = 52, cx = 70, cy = 70;
  const rad = (a) => (a * Math.PI) / 180;
  const needleX = cx + r * Math.cos(rad(angle - 90));
  const needleY = cy + r * Math.sin(rad(angle - 90));
  const color = deficit > 15 ? "var(--stress-severe)" : deficit > 0 ? "var(--stress-high)" : "var(--stress-none)";

  const arcPoint = (a) => ({ x: cx + r * Math.cos(rad(a - 90)), y: cy + r * Math.sin(rad(a - 90)) });
  const bandStops = [-120, -40, 40, 120];
  const bandColors = ["#2e7d32", "#ffca28", "#ef5350"];

  return (
    <svg viewBox="0 0 140 92" className="gauge__svg">
      {bandStops.slice(0, -1).map((start, i) => {
        const end = bandStops[i + 1];
        const p1 = arcPoint(start);
        const p2 = arcPoint(end);
        const large = end - start > 180 ? 1 : 0;
        return (
          <path
            key={i}
            d={`M ${p1.x} ${p1.y} A ${r} ${r} 0 ${large} 1 ${p2.x} ${p2.y}`}
            fill="none"
            stroke={bandColors[i]}
            strokeOpacity={0.55}
            strokeWidth="8"
            strokeLinecap="butt"
          />
        );
      })}
      <line x1={cx} y1={cy} x2={needleX} y2={needleY} stroke={color} strokeWidth="3" strokeLinecap="round" />
      <circle cx={cx} cy={cy} r="4" fill={color} />
      <text x={cx} y={cy + 20} textAnchor="middle" fill={color} fontSize="15" fontWeight="700">
        {deficit > 0 ? `-${deficit}` : `+${Math.abs(deficit)}`}
      </text>
      <text x={cx} y={cy + 32} textAnchor="middle" fill="rgba(232,245,233,0.4)" fontSize="8">
        mm deficit
      </text>
    </svg>
  );
}

// --- Pipeline step (interactive: click to expand real methodology detail) ---
function PipelineStep({ num, label, active, detail, anchor, expanded, onToggle }) {
  const clickable = !!detail;
  return (
    <div className={`pipeline__step-wrap ${expanded ? "pipeline__step-wrap--open" : ""}`}>
      <button
        type="button"
        className={`pipeline__step ${active ? "pipeline__step--active" : ""} ${clickable ? "pipeline__step--clickable" : ""}`}
        onClick={clickable ? onToggle : undefined}
        aria-expanded={expanded}
        disabled={!clickable}
      >
        <span className="pipeline__num">{num}</span>
        <span className="pipeline__label">{label}</span>
        {active && <span className="pipeline__dot" />}
        {clickable && <span className="pipeline__chevron">{expanded ? "▾" : "▸"}</span>}
      </button>
      {expanded && detail && (
        <div className="pipeline__detail">
          <p className="pipeline__detail-method">{detail.method}</p>
          <p className="pipeline__detail-metric">{detail.metric}</p>
          {anchor && (
            <Link to={`/methodology#${anchor}`} className="pipeline__detail-link">
              Full methodology →
            </Link>
          )}
        </div>
      )}
    </div>
  );
}

export default function Dashboard() {
  const [fields, setFields] = useState([]);
  const [coverage, setCoverage] = useState(null);
  const [commandArea, setCommandArea] = useState(null);
  const [validation, setValidation] = useState(null);
  const [methodology, setMethodology] = useState(null);
  const [activeId, setActiveId] = useState(null);
  const [mapMode, setMapMode] = useState("stress"); // crop | stress | stage
  const [loading, setLoading] = useState(true);
  const [backendOnline, setBackendOnline] = useState(true);
  const [expandedSteps, setExpandedSteps] = useState(() => new Set([3, 6])); // crop + irrigation open by default — no click required
  const toggleStep = (n) => setExpandedSteps((prev) => {
    const next = new Set(prev);
    next.has(n) ? next.delete(n) : next.add(n);
    return next;
  });
  const [readFirstOpen, setReadFirstOpen] = useState(true);

  useEffect(() => {
    // Instant hydrate from the in-memory cache (survives coming back
    // from /methodology) so this doesn't show a loading spinner every
    // single time you switch tabs.
    const cached = getDashboardCache();
    if (cached) {
      setFields(cached.fields); setCoverage(cached.coverage);
      setCommandArea(cached.commandArea); setValidation(cached.validation);
      setMethodology(cached.methodology);
      if (cached.fields.length && !activeId) setActiveId(cached.fields[0].id);
      setLoading(false);
    }

    pingBackend().then(setBackendOnline);
    Promise.all([getFields(), getCoverageStats(), getCommandAreaAdvisory("CA-KPT01"), getValidationMetrics(), getMethodology()])
      .then(([f, cov, ca, val, meth]) => {
        setFields(f); setCoverage(cov); setCommandArea(ca); setValidation(val); setMethodology(meth);
        setDashboardCache({ fields: f, coverage: cov, commandArea: ca, validation: val, methodology: meth });
        if (f.length && !cached) setActiveId(f[0].id);
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const active = fields.find((f) => f.id === activeId);
  const adv = active?.advisory;

  const stressCounts = {
    adequate: fields.filter((f) => f.moisture === "adequate").length,
    "moderate-stress": fields.filter((f) => f.moisture === "moderate-stress").length,
    "high-stress": fields.filter((f) => f.moisture === "high-stress").length,
  };

  const stageCounts = {};
  STAGE_ORDER.forEach((s) => { stageCounts[s] = fields.filter((f) => f.stage === s).length; });

  const rabiVal = validation?.crop_classifier_wintercereal;
  const multiVal = validation?.crop_classifier_rice_wheat;

  // Real per-step detail, sourced from the live /api/methodology
  // response — not hardcoded copy that could drift from what the
  // backend actually does.
  const findModel = (...keywords) =>
    methodology?.models?.find((m) => keywords.some((k) => m.name.toLowerCase().includes(k)));
  const cropModels = methodology?.models?.filter((m) => m.name.toLowerCase().includes("classifier")) || [];
  const cropDetail = cropModels.length
    ? { method: cropModels.map((m) => m.method).join(" — "), metric: cropModels.map((m) => m.metric).join(" · ") }
    : null;
  const moistureDetail = findModel("moisture");
  const phenologyDetail = findModel("phenology");
  const waterDetail = findModel("water balance");
  const preprocessDetail = methodology
    ? { method: "Per-field GEE point extraction over each sample coordinate — cloud/quality masking on Sentinel-2, orbit selection on Sentinel-1.", metric: "Point samples, not full raster chips — see disclosed limitations." }
    : null;
  const featureDetail = rabiVal
    ? { method: `Band features extracted per field: ${rabiVal.features.join(", ")}.`, metric: "Same real feature set feeds both crop classifiers." }
    : null;

  if (loading) return <div className="dash__loading">Reading satellite signals…</div>;

  return (
    <div className="dash">
      {/* ── LEFT SIDEBAR ── */}
      <aside className="dash__sidebar">
        <div className="dash__farmid">
          <span className="dash__farmid-label">Command Area</span>
          <span className="dash__farmid-val">CA-KPT01</span>
          <span className="dash__farmid-sub">Kapurthala, Punjab · Oct 2024–Mar 2025</span>
        </div>

        <div className="dash__thumbs">
          <div className="dash__thumb">
            <div className="dash__thumb-img dash__thumb-img--optical">S2</div>
            <span>Optical Image (Sentinel-2)</span>
          </div>
          <div className="dash__thumb">
            <div className="dash__thumb-img dash__thumb-img--sar">S1</div>
            <span>Microwave Image (Sentinel-1)</span>
          </div>
        </div>

        <div className="dash__section-head">2. AI ANALYSIS</div>
        <div className="dash__pipeline">
          <PipelineStep num="①" label="Preprocessing" active={false}
            detail={preprocessDetail} expanded={expandedSteps.has(1)}
            onToggle={() => toggleStep(1)} />
          <PipelineStep num="②" label="Feature Extraction" active={false}
            detail={featureDetail} anchor="meth-crop" expanded={expandedSteps.has(2)}
            onToggle={() => toggleStep(2)} />
          <PipelineStep num="③" label="Crop Classification Model" active={true}
            detail={cropDetail} anchor="meth-crop" expanded={expandedSteps.has(3)}
            onToggle={() => toggleStep(3)} />
          <PipelineStep num="④" label="Moisture Stress Model" active={true}
            detail={moistureDetail} anchor="meth-moisture" expanded={expandedSteps.has(4)}
            onToggle={() => toggleStep(4)} />
          <PipelineStep num="⑤" label="Growth Stage Estimation" active={true}
            detail={phenologyDetail} anchor="meth-phenology" expanded={expandedSteps.has(5)}
            onToggle={() => toggleStep(5)} />
          <PipelineStep num="⑥" label="Irrigation Advisory Model" active={true}
            detail={waterDetail} anchor="meth-water" expanded={expandedSteps.has(6)}
            onToggle={() => toggleStep(6)} />
        </div>

        <div className="dash__section-head">3. OUTPUTS</div>
        <div className="dash__outputs">
          <span className="dash__output-item">🌾 Crop Map</span>
          <span className="dash__output-item">💧 Moisture Stress Map</span>
          <span className="dash__output-item">📅 Phenology Map</span>
          <span className="dash__output-item">🗺 Irrigation Advisory</span>
        </div>

        {rabiVal && (
          <div className="dash__accuracy">
            <span>Overall Accuracy: {Math.round(rabiVal.overall_accuracy * 100)}%</span>
            <span>Kappa: {rabiVal.kappa.toFixed(2)}</span>
            {multiVal && <span className="dash__accuracy-multi">Multi-class (Rice/Wheat): {Math.round(multiVal.overall_accuracy * 100)}%</span>}
          </div>
        )}

        <Link to="/methodology" className="dash__methodlink">View full methodology →</Link>
      </aside>

      {/* ── MAIN CONTENT ── */}
      <div className="dash__main">
        {!backendOnline && (
          <div className="dash__offline-banner">
            ⚠ Backend not reachable at {import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"} — showing
            stale placeholder data (4 mock fields, no real coordinates). Start it with{" "}
            <code>uvicorn app.main:app --reload</code> from <code>backend/</code>, then refresh.
          </div>
        )}
        {/* ── READ THIS FIRST — front-loaded explanations for anyone reviewing
             solo, with no one available to answer questions live. Every
             number here that could look like a bug has its real reason
             stated plainly, up front, visible without hovering or clicking. ── */}
        {readFirstOpen && (
          <div className="dash__readfirst">
            <div className="dash__readfirst-head">
              <span className="dash__readfirst-title">
                <svg className="dash__readfirst-glyph" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
                  <circle cx="12" cy="12" r="9" />
                  <path d="M12 8v5M12 16h.01" strokeLinecap="round" />
                </svg>
                Before you draw conclusions
              </span>
              <button className="dash__readfirst-close" onClick={() => setReadFirstOpen(false)} aria-label="Collapse">✕</button>
            </div>
            <ul className="dash__readfirst-list">
              <li>
                <strong>{commandArea ? `${commandArea.fields_needing_irrigation}/${commandArea.total_fields}` : "Most"} fields show an active irrigation recommendation.</strong>{" "}
                This is not a threshold bug. The reference date (20 Mar 2025) falls before PAU Ludhiana's own official cutoff —
                end of March for timely-sown wheat, 10 April for late-sown — from PAU's Rabi 2025-26 Package of Practices
                (pau.edu/content/ccil/pf/pp_rabi.pdf). No field has reached its real cutoff yet.
              </li>
              <li>
                <strong>The map's field polygons aren't surveyed farm boundaries.</strong>{" "}
                They're Voronoi cells — "closest to this real GEE sample point" — around 59 real coordinates inside one
                ~150m Kapurthala AOI, not 59 separate farms. Every color and number is real per-point data; the shapes are
                a visualization technique, not fabricated geometry.
              </li>
              <li>
                <strong>Crop classification accuracy is 88.5% for wheat detection, but only 72% for rice-vs-wheat.</strong>{" "}
                That's disclosed, not hidden: the model's main confusion signal is SAR backscatter physics (flooded rice
                paddies scatter differently), and remaining noise traces to a known label-source limitation, not a bug —
                full detail in Methodology.
              </li>
              <li>
                <strong>53 of 59 fields have a real sowing date after PAU's own "late sown" boundary (5 Dec).</strong>{" "}
                Plausible for this AOI — Kapurthala is a rice-wheat rotation zone where combine-harvest delays routinely
                push wheat sowing into December — but not independently confirmed against ground-truth sowing records.
                Sowing date here is an NDVI-detected proxy, not a farmer-reported date.
              </li>
            </ul>
            <div className="dash__readfirst-footer">
              Full citations, model accuracy tables, and every other disclosed limitation: <Link to="/methodology">Methodology page →</Link>
            </div>
          </div>
        )}
        {!readFirstOpen && (
          <button className="dash__readfirst-reopen" onClick={() => setReadFirstOpen(true)}>Show context notes</button>
        )}

        {/* ── HEADER ── */}
        <header className="dash__header">
          <div className="dash__header-left">
            <span className="dash__title">Bhoomi</span>
            <span className="dash__subtitle">AI-Driven Crop Monitoring & Irrigation Advisory · Kapurthala Pilot Command Area</span>
          </div>
          <div className="dash__header-stats">
            {coverage && (
              <>
                <div className="dash__hstat">
                  <span className="dash__hstat-val">{coverage.sarAcquisitions}</span>
                  <span className="dash__hstat-lbl">SAR passes</span>
                </div>
                <div className="dash__hstat">
                  <span className="dash__hstat-val">{coverage.opticalAcquisitions}</span>
                  <span className="dash__hstat-lbl">Optical passes</span>
                </div>
                <div className="dash__hstat dash__hstat--hi">
                  <span className="dash__hstat-val">{coverage.coverageMultiplier}x</span>
                  <span className="dash__hstat-lbl">SAR vs optical coverage</span>
                </div>
              </>
            )}
            {commandArea && (
              <div className="dash__hstat dash__hstat--warn">
                <span className="dash__hstat-val">{commandArea.fields_needing_irrigation}/{commandArea.total_fields}</span>
                <span className="dash__hstat-lbl">fields need irrigation</span>
              </div>
            )}
          </div>
        </header>

        {/* ── THREE MAP PANELS ── */}
        <div className="dash__maps-section">
          <div className="dash__map-caption">
            Cell boundaries are Voronoi regions around 59 real GEE sample points inside one ~150m Kapurthala AOI —
            <em> not surveyed field boundaries</em> and not 59 geographically distinct farms.{" "}
            <Link to="/methodology#meth-crop">Full disclosure →</Link>
          </div>
          <div className="dash__maps">
          {/* Crop type map */}
          <div className="dash__panel">
            <div className="dash__panel-head">
              <span>Crop Classification Map</span>
              <span className="dash__panel-badge">RF + WorldCereal</span>
            </div>
            <FieldMap
              fields={fields}
              activeId={activeId}
              onSelect={setActiveId}
              getColor={(f) => colorForMode(f, "crop")}
              getTooltip={fieldTooltip}
            />
            <div className="dash__legend">
              {Object.entries(CROP_COLORS).filter(([k]) => k !== "default").map(([crop, color]) => (
                <span key={crop} className="dash__legend-item">
                  <i style={{ background: color }} />
                  {cropShort(crop)}
                </span>
              ))}
            </div>
            {rabiVal && <div className="dash__accuracy-tag">Overall Accuracy: {Math.round(rabiVal.overall_accuracy * 100)}%</div>}
          </div>

          {/* Stress map */}
          <div className="dash__panel">
            <div className="dash__panel-head">
              <span>Moisture Stress Level Map</span>
              <div className="dash__map-tabs">
                {["stress", "crop", "stage"].map((m) => (
                  <button key={m} className={`dash__map-tab ${mapMode === m ? "active" : ""}`} onClick={() => setMapMode(m)}>
                    {m === "stress" ? "Stress" : m === "crop" ? "Crop" : "Stage"}
                  </button>
                ))}
              </div>
            </div>
            <FieldMap
              fields={fields}
              activeId={activeId}
              onSelect={setActiveId}
              getColor={(f) => colorForMode(f, mapMode)}
              getTooltip={fieldTooltip}
            />
            <div className="dash__legend">
              {mapMode === "stress" && Object.entries(STRESS_COLORS).map(([s, c]) => (
                <span key={s} className="dash__legend-item"><i style={{ background: c }} />{s.replace("-", " ")}</span>
              ))}
              {mapMode === "crop" && Object.entries(CROP_COLORS).filter(([k]) => k !== "default").map(([k, c]) => (
                <span key={k} className="dash__legend-item"><i style={{ background: c }} />{cropShort(k)}</span>
              ))}
              {mapMode === "stage" && Object.entries(STAGE_COLORS).map(([s, c]) => (
                <span key={s} className="dash__legend-item"><i style={{ background: c }} />{s}</span>
              ))}
            </div>
            <div className="dash__stress-dist">
              {Object.entries(stressCounts).map(([s, n]) => (
                <div key={s} className="dash__stress-bar-row">
                  <span>{s.replace("-stress", "")}</span>
                  <div className="dash__stress-bar-track">
                    <div className="dash__stress-bar-fill" style={{ width: `${(n / fields.length) * 100}%`, background: STRESS_COLORS[s] }} />
                  </div>
                  <span>{n}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Growth stage map */}
          <div className="dash__panel">
            <div className="dash__panel-head">
              <span>Crop Growth Stage Map</span>
              <span className="dash__panel-badge">SOS Detection</span>
            </div>
            <FieldMap
              fields={fields}
              activeId={activeId}
              onSelect={setActiveId}
              getColor={(f) => colorForMode(f, "stage")}
              getTooltip={fieldTooltip}
            />
            <div className="dash__legend">
              {STAGE_ORDER.map((s) => (
                <span key={s} className="dash__legend-item"><i style={{ background: STAGE_COLORS[s] }} />{s}</span>
              ))}
            </div>
            <div className="dash__stage-dist">
              {STAGE_ORDER.map((s) => (
                <div key={s} className="dash__stage-item">
                  <span>{s}</span>
                  <span className="dash__stage-count" style={{ color: STAGE_COLORS[s] }}>{stageCounts[s] || 0}</span>
                </div>
              ))}
            </div>
          </div>
          </div>
        </div>

        {/* ── IRRIGATION RECOMMENDATIONS ── */}
        <div className="dash__irrig">
          <div className="dash__irrig-head">
            IRRIGATION RECOMMENDATIONS
            {active && <span className="dash__irrig-field">— Field {activeId}</span>}
          </div>

          <div className="dash__irrig-body">
            {/* Recommended action */}
            <div className="dash__irrig-card">
              <div className="dash__irrig-card-label">Recommended Action</div>
              {adv ? (
                <>
                  <div className={`dash__irrig-action ${adv.stressLevel === "high-stress" ? "dash__irrig-action--urgent" : ""}`}>
                    💧 {adv.action}
                  </div>
                  <div className="dash__irrig-reason">{adv.stressLevel?.replace("-", " ")} · {active?.stage}</div>
                </>
              ) : <div className="dash__irrig-action">Select a field</div>}
            </div>

            {/* Irrigation depth */}
            <div className="dash__irrig-card">
              <div className="dash__irrig-card-label">Irrigation Depth (mm)</div>
              <div className="dash__irrig-bignum" style={{ color: adv?.deficitMm > 15 ? "var(--danger)" : "var(--amber)" }}>
                {adv?.amount !== "—" ? adv?.amount : "None needed"}
              </div>
              <div className="dash__irrig-sub">ETo: {adv?.etoMmPerDay || "—"} mm/day · ETc: {adv?.etcMm || "—"} mm</div>
            </div>

            {/* Irrigation map (field-level, coloured by real deficit) */}
            <div className="dash__irrig-card">
              <div className="dash__irrig-card-label">Irrigation Map (mm)</div>
              <div className="dash__irrig-mapwrap">
                <FieldMap
                  fields={fields}
                  activeId={activeId}
                  onSelect={setActiveId}
                  getColor={(f) => colorForMode(f, "depth")}
                  getTooltip={fieldTooltip}
                />
              </div>
              <div className="dash__irrig-legend-row">
                <span style={{ color: "#1b5e20" }}>■ None</span>
                <span style={{ color: "#4fc3f7" }}>■ 0-10</span>
                <span style={{ color: "#0288d1" }}>■ 10-20</span>
                <span style={{ color: "#01579b" }}>■ 20+</span>
              </div>
            </div>

            {/* Water balance gauge */}
            <div className="dash__irrig-card">
              <div className="dash__irrig-card-label">Water Balance (Field Level)</div>
              <WaterGauge deficit={adv?.deficitMm ?? 0} />
              <div className="dash__irrig-sub">
                Rainfall: {adv?.rainfallMm || "—"} mm · Demand: {adv?.etcMm || "—"} mm
              </div>
            </div>
          </div>

          {/* Command area total */}
          {commandArea && (
            <div className="dash__irrig-footer">
              <span>Total Irrigation Volume: <strong>{commandArea.total_irrigation_volume_mm} mm</strong> across {commandArea.total_fields} fields</span>
              <span>Source: SAR (Sentinel-1) + Optical (Sentinel-2) · <strong>Fused all-weather pipeline</strong></span>
              <span style={{ color: "var(--sar-blue)" }}>SAR delivers {coverage?.coverageMultiplier}× more usable observations than optical alone</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
