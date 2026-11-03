from urllib.parse import urlparse

import requests
import yaml
from fastapi import FastAPI, HTTPException

app = FastAPI(title="secure-cicd-pipeline demo API")

ALLOWED_UPSTREAM_HOSTS = {"httpbin.org", "example.com"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/config/import")
def import_config(raw_yaml: str):
    """Parse a YAML config snippet submitted by a client."""
    config = yaml.safe_load(raw_yaml)
    return {"parsed": config}


@app.get("/status/upstream")
def upstream_status(url: str):
    """Forward a status check to an allow-listed upstream host."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_UPSTREAM_HOSTS:
        raise HTTPException(status_code=400, detail="URL must be https and target an allow-listed host")
    # url is validated against ALLOWED_UPSTREAM_HOSTS above; semgrep's generic taint
    # rule does not model this sanitizer and still flags the call below.
    response = requests.get(url, timeout=5)  # nosemgrep: python.flask.security.injection.ssrf-requests.ssrf-requests
    return {"status_code": response.status_code}
