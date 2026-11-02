import yaml
import requests
from fastapi import FastAPI

app = FastAPI(title="secure-cicd-pipeline demo API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/config/import")
def import_config(raw_yaml: str):
    """Parse a YAML config snippet submitted by a client."""
    config = yaml.load(raw_yaml, Loader=yaml.Loader)
    return {"parsed": config}


@app.get("/status/upstream")
def upstream_status(url: str):
    """Forward a status check to an upstream URL."""
    response = requests.get(url, timeout=5)
    return {"status_code": response.status_code}
