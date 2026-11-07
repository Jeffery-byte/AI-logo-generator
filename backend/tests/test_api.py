"""API compatibility checks; Google and paid provider calls are never used."""
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "initialize_google_auth", lambda: False)
    monkeypatch.setattr(main, "CREDENTIALS", None)
    monkeypatch.setattr(main, "PROJECT_ID", None)
    main.rate_limits.clear()
    with TestClient(main.app) as test_client:
        yield test_client


def payload():
    return {
        "business_info": {"name": "Demo", "industry": "Technology"},
        "style": {"style_type": "modern", "color_palette": ["#123456"]},
        "variations": 1,
    }


def test_health_without_cloud_credentials(client):
    result = client.get("/api/v1/health")
    assert result.status_code == 200
    assert result.json()["credentials_configured"] is False


@pytest.mark.parametrize("variations", [0, 3, None])
def test_invalid_variation_count(client, variations):
    body = payload()
    body["variations"] = variations
    assert client.post("/api/v1/generate-logos", json=body).status_code == 422


@pytest.mark.parametrize("style", [
    {"style_type": "unknown", "color_palette": ["#123456"]},
    {"style_type": "modern", "color_palette": []},
])
def test_invalid_style(client, style):
    body = payload()
    body["style"] = style
    assert client.post("/api/v1/generate-logos", json=body).status_code == 422


def test_missing_cloud_credentials_fail_before_generation(client, monkeypatch):
    async def forbidden(_):
        pytest.fail("Provider must not be called without credentials")
    monkeypatch.setattr(main.VertexImagenLogoGenerator, "create_vertex_logos", forbidden)
    assert client.post("/api/v1/generate-logos", json=payload()).status_code == 500


def test_provider_rate_limit_is_preserved(client, monkeypatch):
    monkeypatch.setattr(main, "CREDENTIALS", object())
    monkeypatch.setattr(main, "PROJECT_ID", "test-project")
    async def limited(_):
        raise HTTPException(status_code=429, detail="Provider limit")
    monkeypatch.setattr(main.VertexImagenLogoGenerator, "create_vertex_logos", limited)
    response = client.post("/api/v1/generate-logos", json=payload())
    assert response.status_code == 429
    assert response.json()["detail"] == "Provider limit"


def test_startup_does_not_run_paid_diagnostics_by_default(monkeypatch):
    monkeypatch.delenv("RUN_STARTUP_DIAGNOSTICS", raising=False)
    monkeypatch.setattr(main, "initialize_google_auth", lambda: True)
    async def forbidden():
        pytest.fail("Startup must not run paid diagnostics by default")
    monkeypatch.setattr(main.VertexAIDiagnostics, "full_vertex_diagnostic", forbidden)
    with TestClient(main.app) as test_client:
        assert test_client.get("/").status_code == 200
