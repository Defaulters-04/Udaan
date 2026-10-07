"""Tests for the PRISM Conflict Index FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from engine.conflict.api import app

client = TestClient(app)


def test_api_get_config():
    """GET /conflict/config returns default weights and thresholds."""
    response = client.get("/conflict/config")
    assert response.status_code == 200
    data = response.json()
    assert data["w_risk"] == 0.25
    assert data["w_domain"] == 0.25
    assert data["w_relocation"] == 0.25
    assert data["w_time"] == 0.25
    assert data["conflict_threshold"] == 0.40


def test_api_overall_post():
    """POST /conflict/overall evaluates family alignment."""
    payload = {
        "student": {
            "risk_appetite": 0.8,
            "domain_preference": {"Technology & Engineering": 5.0},
            "relocation_willingness": 0.7,
            "max_years_to_income": 4.0,
        },
        "parent": {
            "risk": 0.2,
            "domain_ratings": {"Technology & Engineering": 2.0},
            "relocation_willingness": 0.3,
            "max_years_to_income": 2.0,
        },
    }
    response = client.post("/conflict/overall", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "overall_conflict" in data
    assert "risk_conflict" in data
    assert "domain_conflict" in data
    assert "relocation_conflict" in data
    assert "time_conflict" in data
    assert "diagnosis_summary" in data
    assert data["is_high_conflict"] is True
    assert data["risk_conflict"]["gap"] == pytest.approx(0.6)


def test_api_career_post():
    """POST /conflict/career evaluates conflict for a specific route."""
    payload = {
        "student": {"risk_appetite": 0.9},
        "parent": {"risk": 0.1},
        "route": {
            "career_id": "software_engineer",
            "route_id": "btech_cse",
            "career_risk": 0.9,
            "domain": "Technology & Engineering",
            "relocation_need": 0.5,
            "years_to_first_income": 4.0,
        },
    }
    response = client.post("/conflict/career", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["career_id"] == "software_engineer"
    assert data["route_id"] == "btech_cse"
    assert data["risk_gap"] > 0.7
    assert data["is_high_conflict"] is True


def test_api_evaluate_post():
    """POST /conflict/evaluate evaluates portfolio of routes."""
    payload = {
        "student": {"risk_appetite": 0.5},
        "parent": {"risk": 0.5},
        "routes": [
            {
                "career_id": "c1",
                "route_id": "r1",
                "career_risk": 0.5,
                "domain": "tech",
                "relocation_need": 0.5,
                "years_to_first_income": 4.0,
            },
            {
                "career_id": "c2",
                "route_id": "r2",
                "career_risk": 0.9,
                "domain": "arts",
                "relocation_need": 0.8,
                "years_to_first_income": 6.0,
            },
        ],
    }
    response = client.post("/conflict/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "overall" in data
    assert len(data["career_conflicts"]) == 2
    assert "avg_career_conflict" in data


def test_api_negotiate_post():
    """POST /conflict/negotiate evaluates Negotiation Explorer compromise zone."""
    payload = {
        "student": {"risk_appetite": 0.8},
        "parent": {"risk": 0.3},
        "careers": [
            {
                "career_id": "ai_researcher",
                "route_id": "btech_mtech",
                "career_name": "AI Researcher",
                "student_fit": 0.90,
                "family_viability": 0.40,
                "market_score": 0.85,
                "career_risk": 0.80,
                "is_financially_viable": True,
            },
            {
                "career_id": "cloud_architect",
                "route_id": "bca_mca",
                "career_name": "Cloud Architect",
                "student_fit": 0.80,
                "family_viability": 0.85,
                "market_score": 0.88,
                "career_risk": 0.40,
                "is_financially_viable": True,
            },
            {
                "career_id": "bank_po",
                "route_id": "govt_exam",
                "career_name": "Bank PO",
                "student_fit": 0.35,
                "family_viability": 0.95,
                "market_score": 0.70,
                "career_risk": 0.10,
                "is_financially_viable": True,
            },
        ],
        "alpha": 0.5,
    }
    response = client.post("/conflict/negotiate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["alpha"] == 0.5
    assert data["total_careers_evaluated"] == 3
    assert data["compromise_zone_count"] >= 1
    # Cloud Architect should be top ranked compromise
    top = data["ranked_careers"][0]
    assert top["career_id"] == "cloud_architect"
    assert top["is_in_compromise_zone"] is True


def test_api_health_check():
    """GET /conflict/health returns status ok."""
    response = client.get("/conflict/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "prism-conflict-engine"}
