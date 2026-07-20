import "./MethodologyFooter.css";

export default function MethodologyFooter() {
  return (
    <footer className="methfooter">
      <div className="methfooter__row">
        <span className="methfooter__label">Data sources</span>
        <span className="methfooter__value">Sentinel-1 (SAR) · Sentinel-2 (optical) · ESA WorldCereal · CHIRPS rainfall · ERA5-Land temperature</span>
      </div>
      <div className="methfooter__row">
        <span className="methfooter__label">Crop classifier</span>
        <span className="methfooter__value">Random Forest, real Kapurthala data — 88.5% accuracy, κ = 0.45</span>
      </div>
      <div className="methfooter__row">
        <span className="methfooter__label">Phenology</span>
        <span className="methfooter__value">Real NDVI-based Start-of-Season detection, not assumed sowing dates</span>
      </div>
      <div className="methfooter__row">
        <span className="methfooter__label">Water balance</span>
        <span className="methfooter__value">Thornthwaite ETo from real temperature · real CHIRPS rainfall · 8-day deficit</span>
      </div>
      <div className="methfooter__row methfooter__row--relevance">
        <span className="methfooter__label">Relevance</span>
        <span className="methfooter__value">Designed to extend PMKSY, Digital Agriculture Mission, NMSA, and PMFBY with a near-real-time, command-area-scale water-stress layer</span>
      </div>
    </footer>
  );
}
