from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_root_serves_html() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "AeroDisplay" in resp.text


def test_health_endpoint() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

