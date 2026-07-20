import { useState } from "react";
import "./MapView.css";

const stressFill = {
  "high-stress": "var(--danger)",
  "moderate-stress": "var(--amber)",
  adequate: "var(--sar-blue)",
};

const stressLabel = {
  "high-stress": "High stress",
  "moderate-stress": "Moderate stress",
  adequate: "Adequate",
};

// Small, scattered cloud patches (not one canvas-covering blob) — a
// qualitative monsoon-cloud illustration, not meant to literally
// obscure the field markers underneath.
const CLOUD_PATCHES = [
  { cx: 90, cy: 70, r: 36 },
  { cx: 200, cy: 50, r: 30 },
  { cx: 280, cy: 110, r: 38 },
  { cx: 130, cy: 170, r: 32 },
  { cx: 240, cy: 200, r: 28 },
];

function projectFields(fields) {
  if (!fields.length) return [];
  const lats = fields.map((f) => f.latitude);
  const lons = fields.map((f) => f.longitude);
  const latRange = Math.max(...lats) - Math.min(...lats) || 0.0001;
  const lonRange = Math.max(...lons) - Math.min(...lons) || 0.0001;
  const pad = 50;
  const w = 360 - pad * 2;
  const h = 260 - pad * 2;

  return fields.map((f) => ({
    ...f,
    x: pad + ((f.longitude - Math.min(...lons)) / lonRange) * w,
    y: pad + (1 - (f.latitude - Math.min(...lats)) / latRange) * h,
  }));
}

export default function MapView({ fields = [], activeId, onSelect, coverage }) {
  const [mode, setMode] = useState("fused");
  const projected = projectFields(fields);
  const showLabels = projected.length <= 12;

  const opticalPct = coverage?.opticalCoveragePct ?? 0;
  const fusedPct = coverage?.fusedCoveragePct ?? 0;
  const multiplier = coverage?.coverageMultiplier;

  return (
    <div className="mapview">
      <div className="mapview__head">
        <div>
          <p className="mapview__eyebrow">{coverage?.windowLabel || "Real Kapurthala AOI"}</p>
          <h3 className="mapview__title">Same season. Real fields.</h3>
        </div>
        <div className="mapview__toggle" role="tablist" aria-label="Data source">
          <button role="tab" aria-selected={mode === "optical"} className={mode === "optical" ? "is-active" : ""} onClick={() => setMode("optical")}>
            Optical only
          </button>
          <button role="tab" aria-selected={mode === "fused"} className={mode === "fused" ? "is-active" : ""} onClick={() => setMode("fused")}>
            SAR + Optical fused
          </button>
        </div>
      </div>

      <div className="mapview__canvas">
        <svg viewBox="0 0 360 260" className="mapview__svg" role="img" aria-label={`Field map, ${mode} view`}>
          <defs>
            <pattern id="grid" width="18" height="18" patternUnits="userSpaceOnUse">
              <path d="M18 0 L0 0 0 18" fill="none" stroke="rgba(241,236,224,0.06)" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="360" height="260" fill="url(#grid)" />

          {projected.map((f) => {
            const isActive = f.id === activeId;
            const fill = mode === "fused" ? stressFill[f.moisture] || "var(--sar-blue)" : "rgba(241,236,224,0.18)";
            return (
              <g key={f.id} opacity={mode === "optical" ? 0.4 : 1} onClick={() => onSelect?.(f.id)} style={{ cursor: "pointer" }}>
                <circle
                  cx={f.x}
                  cy={f.y}
                  r={isActive ? 9 : 5.5}
                  fill={fill}
                  fillOpacity={mode === "fused" ? (isActive ? 0.55 : 0.4) : 0.5}
                  stroke={fill}
                  strokeWidth={isActive ? 2 : 1}
                />
                {(showLabels || isActive) && (
                  <text x={f.x} y={f.y - (isActive ? 14 : 10)} textAnchor="middle" className="mapview__plot-label">
                    {f.id}
                  </text>
                )}
              </g>
            );
          })}

          {mode === "optical" &&
            CLOUD_PATCHES.map((c, i) => (
              <circle key={i} cx={c.cx} cy={c.cy} r={c.r} className="mapview__cloud" />
            ))}
        </svg>

        <div className="mapview__legend">
          {Object.entries(stressLabel).map(([key, label]) => (
            <span key={key} className="mapview__legend-item">
              <i className="mapview__legend-dot" style={{ background: stressFill[key] }} />
              {label}
            </span>
          ))}
        </div>

        <p className="mapview__disclosure">
          {fields.length} real sample points within one ~150m Kapurthala AOI plot — not separate distant farms.
        </p>

        <div className={`mapview__readout ${mode === "optical" ? "is-blind" : "is-clear"}`}>
          <span className="mapview__readout-dot" />
          {mode === "optical"
            ? `Optical alone: ${opticalPct}% of the season had a usable cloud-free pass`
            : `Fused SAR+optical: ${fusedPct}% of the season usable${multiplier ? ` — ${multiplier}x more observation days than optical alone` : ""}`}
        </div>
      </div>
    </div>
  );
}
