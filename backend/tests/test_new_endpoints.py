"""
Tests for the dedicated phenology and methodology endpoints —
verified via FastAPI's TestClient (not direct function calls,
since Query() defaults only resolve through real request handling).
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_field_phenology_returns_real_series():
    resp = client.get("/api/fields/F-K01/phenology")
    assert resp.status_code == 200
    data = resp.json()
    assert data["field_id"] == "F-K01"
    assert data["sos_date"] is not None
    assert len(data["ndvi_series"]) > 10


def test_field_phenology_unknown_field_404s():
    resp = client.get("/api/fields/F-NONEXISTENT/phenology")
    assert resp.status_code == 404


def test_methodology_returns_all_sections():
    resp = client.get("/api/methodology")
    assert resp.status_code == 200
    data = resp.json()
    assert "data_sources" in data
    assert "models" in data
    assert "disclosed_limitations" in data
    assert len(data["disclosed_limitations"]) >= 3
