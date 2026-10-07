from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_matches_contract() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "udaan-api",
        "version": "0.1.0",
    }


def test_unknown_route_returns_error_shape() -> None:
    response = client.get("/unknown-route")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]
    assert body["error"]["code"] == "not_found"
