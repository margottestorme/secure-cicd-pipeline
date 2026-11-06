# secure-cicd-pipeline

A self-hosted Jenkins pipeline that scans a small FastAPI service for secrets, code
vulnerabilities, vulnerable dependencies, and container CVEs on every build — and blocks
the build when it finds one. Dependency updates are automated with Renovate.

## Why this exists

Most portfolio CI/CD demos just run tests. This one demonstrates a "shift-left" security
pipeline: static analysis, dependency scanning, container scanning, and secret detection
are wired into the build itself, so a vulnerable commit never reaches a built image.

## Architecture

```
GitHub repo (this one)
      │
      ▼
Jenkins (Docker Compose, configured as code via JCasC)
      │   docker.sock mounted → Jenkins can build/run sibling containers
      ▼
Jenkinsfile stages:
  1. Clean previous reports
  2. Install deps & unit tests        (pytest)
  3. Secrets scan                     (gitleaks)
  4. SAST                             (semgrep, p/python ruleset)
  5. Dependency scan (SCA)            (pip-audit)
  6. Build image                      (docker build)
  7. Container image scan             (trivy, CRITICAL/HIGH)
      │
      ▼
Renovate (GitHub App) opens PRs for outdated dependencies,
which re-trigger this same pipeline.
```

Each scanner runs in its own disposable container, invoked from the Jenkinsfile via the
Docker socket mounted into the Jenkins container (Docker-outside-of-Docker). Jenkins
itself is provisioned declaratively: plugins (`jenkins/plugins.txt`), the admin user, and
the pipeline job are all defined in `jenkins/casc.yaml` (Jenkins Configuration as Code) —
no manual click-through setup.

## Demo application

`app/main.py` is a minimal FastAPI service with two endpoints used as the scan target:

- `POST /config/import` — parses a YAML snippet.
- `GET /status/upstream` — checks the status of an upstream URL (restricted to an
  allow-list of hosts).

## The pipeline catching real issues

This repo's own commit history is the demo. The pipeline was run against an earlier,
intentionally vulnerable version of the code and dependencies, then against the fixed
version:

| Stage | Before | After |
|---|---|---|
| Unit tests | ✅ | ✅ |
| Secrets (gitleaks) | ✅ | ✅ |
| SAST (semgrep) | ❌ 2 blocking findings | ✅ 0 findings |
| Dependency scan (pip-audit) | ❌ 21 known CVEs | ✅ none found |
| Build image | ❌ failed (Python version mismatch) | ✅ succeeds |
| Image scan (trivy) | ❌ 45 HIGH CVEs, no fix available | ✅ 0 CRITICAL/HIGH |

What semgrep caught:
- Unsafe YAML deserialization (`yaml.load(..., Loader=yaml.Loader)` instead of
  `yaml.safe_load`) in `/config/import`.
- A server-side request forgery (SSRF): the `url` query parameter was passed straight
  into `requests.get()` with no validation in `/status/upstream`.

What pip-audit caught: `fastapi==0.95.0` pulled in a `starlette` version with over a
dozen known CVEs, and the pinned `requests`/`pyyaml` versions had known vulnerabilities
fixed in later releases.

What trivy caught: the Debian-based `python:3.9-slim` (and later `python:3.12-slim`)
base images carried dozens of OS-level CVEs, several with no vendor fix yet available at
scan time. Switching the base image to `python:3.12-alpine` brought CRITICAL/HIGH
findings to zero — Alpine's minimal package set has a much smaller attack surface, and
the app's only compiled dependency (`pydantic-core`, used by FastAPI) ships a musllinux
wheel, so no build toolchain was needed.

One finding needed human judgement rather than a code change: semgrep's SSRF rule kept
flagging `requests.get(url, ...)` even after the allow-list check was added, because its
generic taint rule doesn't recognize that specific validation as a sanitizer. The fix was
a documented inline suppression (`# nosemgrep: ...` with a comment explaining why),
rather than silencing the rule project-wide — closing a false positive should leave a
trail, not just make the scanner quiet.

## Running it locally

Requires Docker Desktop.

```sh
cp .env.example .env            # edit the admin password before anything public-facing
docker compose up -d --build
```

Jenkins comes up pre-configured at **http://localhost:8081** (admin user/password from
`.env`) with the `secure-cicd-pipeline` job already created and pointed at this repo's
`Jenkinsfile`. Trigger a build from the Jenkins UI, or:

```sh
curl -u admin:<password> -X POST http://localhost:8081/job/secure-cicd-pipeline/build
```

To run the app itself without Jenkins:

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest tests/
uvicorn app.main:app --reload
```

## Dependency updates (Renovate)

`renovate.json` configures [Renovate](https://docs.renovatebot.com/) to open grouped PRs
for outdated Python dependencies, with vulnerability alerts enabled. Each PR re-runs this
pipeline, so a dependency bump that introduces a new CVE or breaks a test is caught
before merge — the same loop used to produce the "after" results above, now automated.

## Known limitations (and why)

- **Docker-outside-of-Docker on Docker Desktop**: sibling containers launched from inside
  Jenkins (via the mounted `docker.sock`) are created by the *host* daemon, which cannot
  resolve paths inside the Jenkins container's own filesystem. The Jenkinsfile works
  around this with `HOST_WORKSPACE`, an environment variable holding the real host-side
  path (set in `docker-compose.yml`). In production you'd avoid this entirely by using a
  dedicated Jenkins agent with Docker installed directly, rather than sharing the host
  socket.
- **Demo credentials**: the default Jenkins admin password in `.env.example` is a
  placeholder — change it before exposing Jenkins beyond localhost.
- **`jenkins_home/` is a local bind mount**, gitignored, and only exists for local runs —
  it is not part of the pipeline's portable state.
