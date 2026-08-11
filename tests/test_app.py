from fastapi.testclient import TestClient

from app.main import app


def test_app_starts_and_serves_ui():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "People Desk" in response.text
