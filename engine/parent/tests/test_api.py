"""Tests for the Parent Machine FastAPI endpoints."""

from fastapi.testclient import TestClient
from prism.parent.api import app


client = TestClient(app)


def test_api_get_config():
    """GET /parent/config returns defaults properly."""
    response = client.get("/parent/config")
    assert response.status_code == 200
    data = response.json()
    assert data["savings_share"] == 0.50
    assert data["surplus_share"] == 0.25
    assert data["annual_loan_rate"] == 0.10
    assert data["loan_term_months"] == 84
    assert data["rb_gate_max"] == 0.50
    assert data["dsr_gate_max"] == 0.20


def test_api_evaluate_post():
    """POST /parent/evaluate performs full evaluation and returns reports."""
    payload = {
        "profile": {
            "savings": 300000.0,
            "monthly_surplus": 5000.0,
            "household_income": 40000.0,
            "existing_emis": 0.0,
            "loan_max": 300000.0,
            "domain_ratings": {"technology": 4},
            "sector_ratings": {"govt": 3, "private": 4, "entrepreneurship": 3},
            "min_salary": 600000.0,
            "max_years_to_income": 5.0,
            "relocation_willingness": 0.8,
            "risk": 0.5,
        },
        "routes": [
            {
                "career_id": "software_engineer",
                "route_id": "btech_cs_demo",
                "tuition": 350000.0,
                "living": 150000.0,
                "exam_equipment": 0.0,
                "grant": 0.0,
                "duration_years": 4.0,
                "starting_salary": 700000.0,
                "years_to_first_income": 4.0,
                "career_risk": 0.4,
                "relocation_need": 0.5,
                "domain": "technology",
                "sector": "private",
                "g_acad": 1,
            }
        ],
    }

    response = client.post("/parent/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "career_results" in data
    assert "reports" in data
    assert "blocked_list" in data

    career_res = data["career_results"]["software_engineer"]
    assert career_res["best_route"]["route_id"] == "btech_cs_demo"
    assert career_res["best_route"]["gate_cleared"] == 1
    assert career_res["f_family_career"] > 0
    assert len(data["blocked_list"]) == 0


def test_api_evaluate_with_config_overrides_and_blocked_route():
    """POST /parent/evaluate accepts config overrides and returns actionable blocked list."""
    payload = {
        "profile": {
            "S": 100000.0,
            "M": 2000.0,
            "M_inc": 25000.0,
            "E_exist": 2000.0,
            "L_max": 200000.0,
            "domain_ratings": {"medicine": 5},
            "sector_ratings": {"govt": 4, "private": 3, "entrepreneurship": 2},
            "Sal_p": 800000.0,
            "T_p": 6.0,
            "rho_p": 0.5,
            "R_p": 0.3,
        },
        "routes": [
            {
                "career_id": "doctor",
                "route_id": "expensive_private_mbbs",
                "T": 1500000.0,
                "L": 400000.0,
                "E_exam": 50000.0,
                "G": 0.0,
                "Y": 5.5,
                "Y1": 900000.0,
                "t_r": 5.5,
                "R_c": 0.2,
                "rho_c": 0.6,
                "domain": "medicine",
                "sector": "private",
            }
        ],
        "config": {
            "annual_loan_rate": 0.09,
            "loan_term_months": 96,
        },
    }

    response = client.post("/parent/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert len(data["blocked_list"]) == 1
    blocked = data["blocked_list"][0]
    assert blocked["route_id"] == "expensive_private_mbbs"
    assert blocked["funding_gap"] > 0
    assert blocked["shortfall_grant_needed"] > 0
    assert "grant/scholarship" in blocked["suggestion"]


def test_api_health_check():
    """GET /parent/health returns healthy status."""
    response = client.get("/parent/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
