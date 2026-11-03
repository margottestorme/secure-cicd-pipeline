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


def test_upstream_status_rejects_non_allowlisted_host():
    response = client.get("/status/upstream", params={"url": "https://internal.local/metadata"})
    assert response.status_code == 400


def test_upstream_status_rejects_non_https():
    response = client.get("/status/upstream", params={"url": "http://httpbin.org"})
    assert response.status_code == 400
