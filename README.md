# Bhoomi — AI-Driven Crop Type, Moisture Stress Detection & Irrigation Advisory

Fuses optical (Sentinel-2) and microwave/SAR (Sentinel-1) satellite data to keep
crop and irrigation monitoring working through monsoon cloud cover.

## Structure
- `backend/` — FastAPI service: crop classification, moisture estimation, advisory engine
- `frontend/` — React/Vite dashboard
- `data/` — raw/processed satellite data and labels
- `notebooks/` — exploration and fusion experiments
- `docs/` — architecture notes and pitch deck

## Quick start (backend)
```
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-serve.txt
uvicorn app.main:app --reload
```
Check the terminal prints `Uvicorn running on http://127.0.0.1:8000` with
no errors before moving on to the frontend.

Use `requirements-serve.txt`, not `requirements.txt`, unless you
specifically need to re-run the GEE export scripts. `requirements.txt`
pins exact old versions (numpy==1.26.4 etc.) that have no prebuilt
wheel for newer Python — pip then tries to compile numpy from source
and fails with a "metadata-generation-failed" error. It also drags in
`rasterio`/`sentinelhub`, which need system GDAL libraries and aren't
used anywhere in the API's serving path (only by the offline
`app/services/sentinel1_fetch.py` / `sentinel2_fetch.py` export
scripts). `requirements-serve.txt` leaves versions unpinned so pip
picks whatever wheel matches your Python, and drops those two —
that's all the API itself needs to run.

## Quick start (frontend)
```
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Frontend tests
```
cd frontend
npm install
npm test
```
Covers the field colour/label classification logic
(`src/lib/fieldColors.js`) and the Voronoi tessellation that turns
real lat/lon sample points into map polygons
(`src/components/FieldMap/FieldMap.jsx`) — 20 tests.

## Dashboard maps
The three map panels and the irrigation mini-map render the real
Kapurthala sample points (`_FIELD_COORDS` in
`backend/app/models/moisture_estimator.py`) as an interactive Leaflet
map. Each field's Voronoi cell — "the area closer to that sample
point than to any other sample point" — is coloured by its real
predicted crop / stress level / growth stage / irrigation depth, so
the polygon patchwork always traces back to a real `field_id` and a
real backend response, never a fabricated boundary. Hover a cell for
its live metrics (VCI, SMI, deficit); click to make it the active
field driving the irrigation panel below.

The basemap is Esri World Imagery (free, no API key) — the dev/build
machine needs outbound internet access to `server.arcgisonline.com`
to load satellite tiles. If you're demoing somewhere offline, the
polygons still render on a blank canvas; only the imagery tiles
underneath will be missing.
