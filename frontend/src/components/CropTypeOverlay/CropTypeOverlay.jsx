import { useState } from "react";
import "./CropTypeOverlay.css";

const STRESS_ORDER = ["high-stress", "moderate-stress", "adequate"];

const stressMeta = {
  "high-stress": { dot: "danger", label: "High stress" },
  "moderate-stress": { dot: "amber", label: "Moderate stress" },
  adequate: { dot: "sar", label: "Adequate" },
};

export default function CropTypeOverlay({ fields, activeId, onSelect }) {
  const grouped = STRESS_ORDER.map((key) => ({
    key,
    meta: stressMeta[key],
    items: fields.filter((f) => f.moisture === key),
  })).filter((g) => g.items.length > 0);

  // Default-open the group containing the active field, else the first group.
  const defaultOpen = grouped.find((g) => g.items.some((f) => f.id === activeId))?.key || grouped[0]?.key;
  const [openKey, setOpenKey] = useState(defaultOpen);

  return (
    <div className="croplist">
      <p className="croplist__eyebrow">Fields · Kapurthala, Punjab</p>
      <p className="croplist__count">{fields.length} real fields in this command area</p>

      <div className="croplist__groups">
        {grouped.map((g) => {
          const isOpen = openKey === g.key;
          return (
            <div key={g.key} className="croplist__group">
              <button className="croplist__group-head" onClick={() => setOpenKey(isOpen ? null : g.key)}>
                <span className={`croplist__dot croplist__dot--${g.meta.dot}`} />
                <span className="croplist__group-label">{g.meta.label}</span>
                <span className="croplist__group-count">{g.items.length}</span>
                <span className={`croplist__chevron ${isOpen ? "is-open" : ""}`}>⌄</span>
              </button>

              {isOpen && (
                <ul className="croplist__list">
                  {g.items.map((f) => (
                    <li key={f.id}>
                      <button
                        className={`croplist__item ${activeId === f.id ? "is-active" : ""}`}
                        onClick={() => onSelect(f.id)}
                      >
                        <span className="croplist__info">
                          <span className="croplist__name">{f.name}</span>
                          <span className="croplist__sub">{f.crop} · {f.area}</span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
