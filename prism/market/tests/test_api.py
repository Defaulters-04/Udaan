"""Tests for the Market Machine FastAPI endpoints."""

from fastapi.testclient import TestClient
from prism.market.api import app


client = TestClient(app)


def test_api_get_config():
    """GET /market/config returns defaults properly."""
    response = client.get("/market/config")
    assert response.status_code == 200
    data = response.json()
    assert data["w_demand_level"] == 0.25
    assert data["w_trend"] == 0.30
    assert data["w_pay_yield"] == 0.20
    assert data["w_low_disruption"] == 0.15
    assert data["w_local_demand"] == 0.10
    assert data["cost_floor"] == 50000.0


def test_api_evaluate_post():
    """POST /market/evaluate evaluates demo catalogue snapshot."""
    response = client.post("/market/evaluate", json={"student_region": "bengaluru"})
    assert response.status_code == 200
    data = response.json()

    assert "reports" in data
    assert "sorted_careers" in data
    assert "low_confidence_careers" in data

    assert len(data["reports"]) == 8
    first = data["sorted_careers"][0]
    assert "F_market" in first
    assert "F_market_central" in first
    assert "F_market_optimistic" in first
    assert first["F_market"] <= first["F_market_central"] <= first["F_market_optimistic"] + 1e-4


def test_api_sensitivity_post():
    """POST /market/sensitivity runs Monte Carlo perturbation."""
    response = client.post("/market/sensitivity", json={"n": 100, "seed": 42})
    assert response.status_code == 200
    data = response.json()

    assert "results" in data
    assert data["runs"] == 100
    assert data["seed"] == 42
    assert len(data["results"]) == 8


def test_api_handoff_rank_post():
    """POST /handoff/rank performs composite ranking and gating."""
    payload = {
        "careers": [
            {
                "career_id": "ai_ml_engineer",
                "F_student": 85.0,
                "F_family": 75.0,
                "F_market": 80.0,
                "G_fin": 1,
                "G_acad": 1,
            },
            {
                "career_id": "blocked_pathway",
                "F_student": 90.0,
                "F_family": 80.0,
                "F_market": 85.0,
                "G_fin": 0,
                "G_acad": 1,
            },
        ]
    }
    response = client.post("/handoff/rank", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert len(data["ranked"]) == 1
    assert data["ranked"][0]["career_id"] == "ai_ml_engineer"
    assert len(data["blocked"]) == 1
    assert data["blocked"][0]["career_id"] == "blocked_pathway"


def test_api_health_check():
    """GET /market/health returns status ok."""
    response = client.get("/market/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
