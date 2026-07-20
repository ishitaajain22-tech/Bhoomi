import { useMemo, useRef, useCallback, useEffect } from "react";
import { MapContainer, TileLayer, Polygon, Tooltip, Rectangle } from "react-leaflet";
import { Delaunay } from "d3-delaunay";
import "leaflet/dist/leaflet.css";
import "./FieldMap.css";

/**
 * Turns the 59 real Kapurthala sample points (real lat/lon from GEE
 * exports) into farm-parcel-shaped polygons via Voronoi tessellation,
 * clipped to a padded bounding box around the real point extent.
 *
 * This is an honest visualization technique, not fabricated field
 * boundaries: each cell is simply "the area closer to sample point A
 * than to any other sample point," which is the standard way to turn
 * point observations into an area map when true parcel-boundary
 * geometry isn't available. Every color, every number in the tooltip
 * still traces back to a real field_id + real backend advisory.
 */
export function buildVoronoiCells(fields) {
  const withCoords = fields.filter((f) => f.latitude != null && f.longitude != null);
  if (withCoords.length < 2) return [];

  const lats = withCoords.map((f) => f.latitude);
  const lons = withCoords.map((f) => f.longitude);
  const latPad = (Math.max(...lats) - Math.min(...lats)) * 0.35 || 0.0006;
  const lonPad = (Math.max(...lons) - Math.min(...lons)) * 0.35 || 0.0006;
  const minLat = Math.min(...lats) - latPad;
  const maxLat = Math.max(...lats) + latPad;
  const minLon = Math.min(...lons) - lonPad;
  const maxLon = Math.max(...lons) + lonPad;

  // d3-delaunay works in plain xy, so x = lon, y = lat (flip later on render)
  const points = withCoords.map((f) => [f.longitude, f.latitude]);
  const delaunay = Delaunay.from(points);
  const voronoi = delaunay.voronoi([minLon, minLat, maxLon, maxLat]);

  return withCoords.map((f, i) => {
    const cell = voronoi.cellPolygon(i);
    if (!cell) return null;
    // Leaflet wants [lat, lon]
    const latlngs = cell.map(([lon, lat]) => [lat, lon]);
    return { field: f, latlngs, bounds: [[minLat, minLon], [maxLat, maxLon]] };
  }).filter(Boolean);
}

function fieldBounds(fields) {
  const withCoords = fields.filter((f) => f.latitude != null && f.longitude != null);
  if (!withCoords.length) return null;
  const lats = withCoords.map((f) => f.latitude);
  const lons = withCoords.map((f) => f.longitude);
  const latPad = (Math.max(...lats) - Math.min(...lats)) * 0.25 || 0.0008;
  const lonPad = (Math.max(...lons) - Math.min(...lons)) * 0.25 || 0.0008;
  return [
    [Math.min(...lats) - latPad, Math.min(...lons) - lonPad],
    [Math.max(...lats) + latPad, Math.max(...lons) + lonPad],
  ];
}

export default function FieldMap({
  fields = [],
  activeId,
  onSelect,
  getColor,
  getTooltip,
  showOutline = true,
}) {
  const cells = useMemo(() => buildVoronoiCells(fields), [fields]);
  const bounds = useMemo(() => fieldBounds(fields), [fields]);
  const mapRef = useRef(null);
  const wrapRef = useRef(null);

  const handleReady = useCallback((map) => {
    mapRef.current = map;
    // Leaflet measures its container at mount time. If that container's
    // final size isn't settled yet (flex/grid layout still resolving —
    // this is a 3-column layout, so whichever panel's column hasn't
    // finished settling its width loses), Leaflet fits its initial
    // zoom/center to the WRONG container size and gets stuck there.
    // invalidateSize() alone only fixes tile rendering at that same
    // wrong zoom — it does NOT re-fit the view. Explicitly calling
    // fitBounds() again after each invalidateSize() forces Leaflet to
    // recompute the correct zoom/center now that the container size
    // is right, which is what actually fixes a panel that mounted
    // zoomed out to a whole subcontinent instead of the real field
    // cluster.
    const refit = () => {
      map.invalidateSize();
      map.fitBounds(bounds);
    };
    setTimeout(refit, 0);
    setTimeout(refit, 250);
  }, [bounds]);

  useEffect(() => {
    if (!wrapRef.current) return undefined;
    const ro = new ResizeObserver(() => {
      if (!mapRef.current) return;
      mapRef.current.invalidateSize();
      mapRef.current.fitBounds(bounds);
    });
    ro.observe(wrapRef.current);
    return () => ro.disconnect();
  }, [bounds]);

  if (!fields.length) {
    return <div className="fmap__empty">Loading fields…</div>;
  }
  if (!cells.length || !bounds) {
    return (
      <div className="fmap__empty fmap__empty--warn">
        No coordinates in this field data.<br />Is the backend running and reachable?
      </div>
    );
  }

  return (
    <div className="fmap" ref={wrapRef}>
      <MapContainer
        bounds={bounds}
        className="fmap__leaflet"
        zoomControl={false}
        attributionControl={false}
        scrollWheelZoom={true}
        whenReady={(e) => handleReady(e.target)}
      >
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          maxZoom={20}
          maxNativeZoom={19}
        />
        {cells.map(({ field, latlngs }) => {
          const isActive = field.id === activeId;
          const color = getColor(field);
          return (
            <Polygon
              key={field.id}
              positions={latlngs}
              pathOptions={{
                color: isActive ? "#ffffff" : color,
                weight: isActive ? 2.5 : showOutline ? 1 : 0,
                fillColor: color,
                fillOpacity: isActive ? 0.78 : 0.55,
                opacity: 1,
              }}
              eventHandlers={{
                click: () => onSelect?.(field.id),
              }}
            >
              {getTooltip && (
                <Tooltip sticky opacity={0.96} className="fmap__tooltip">
                  {getTooltip(field)}
                </Tooltip>
              )}
            </Polygon>
          );
        })}
      </MapContainer>
    </div>
  );
}
