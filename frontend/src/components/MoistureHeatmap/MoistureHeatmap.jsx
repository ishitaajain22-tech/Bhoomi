import "./MoistureHeatmap.css";

const W = 520;
const H = 150;
const PAD = 28;

function toPoints(data, key) {
  const usable = data.filter((d) => d[key] !== null);
  const max = 100;
  const stepX = (W - PAD * 2) / (data.length - 1);
  return usable.map((d) => {
    const i = data.indexOf(d);
    return {
      x: PAD + i * stepX,
      y: H - PAD - (d[key] / max) * (H - PAD * 1.6),
      value: d[key],
    };
  });
}

export default function MoistureHeatmap({ timeline }) {
  if (!timeline || timeline.length === 0) return null;

  const sarPoints = toPoints(timeline, "sar");
  const opticalPoints = toPoints(timeline, "optical");
  const sarPath = sarPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  const stepX = (W - PAD * 2) / (timeline.length - 1);

  return (
    <div className="heatmap">
      <div className="heatmap__head">
        <p className="heatmap__eyebrow">Root-zone moisture · last 8 days</p>
        <div className="heatmap__legend">
          <span><i className="heatmap__dot heatmap__dot--sar" /> SAR (continuous)</span>
          <span><i className="heatmap__dot heatmap__dot--optical" /> Optical (gaps on cloudy days)</span>
        </div>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} className="heatmap__svg" role="img" aria-label="Moisture timeline chart">
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} className="heatmap__axis" />

        <path d={sarPath} className="heatmap__line heatmap__line--sar" fill="none" />
        {sarPoints.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="3" className="heatmap__point heatmap__point--sar" />
        ))}
        {opticalPoints.map((p, i) => (
          <circle key={i} cx={p.x} cy={p.y} r="3.5" className="heatmap__point heatmap__point--optical" />
        ))}

        {timeline.map((d, i) => (
          <text key={d.day} x={PAD + i * stepX} y={H - 6} textAnchor="middle" className="heatmap__tick">
            {d.day.split(" ")[1]}
          </text>
        ))}
      </svg>
    </div>
  );
}
