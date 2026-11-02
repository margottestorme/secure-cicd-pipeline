from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_import_config():
    response = client.post("/config/import", params={"raw_yaml": "key: value"})
    assert response.status_code == 200
    assert response.json() == {"parsed": {"key": "value"}}
