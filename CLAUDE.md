# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repo provides two Dockerized Wazuh agent variants that register with a Wazuh manager and act as data relay/monitoring agents. Neither image is meant to monitor its own container's OS health — they relay external events.

## Two Images

| Image | Dockerfile | Purpose |
|---|---|---|
| `ingest` | `Dockerfile` | Runs the ingest REST API alongside the agent; used to forward JSON events from external systems into Wazuh |
| `regular` (node) | `Dockerfile.agent` | Standard monitoring agent that mounts host filesystem paths under `/hostfs/` for FIM/syscheck |

The ingest image includes `api/` (FastAPI app) and exposes port 9001 for incoming events. The node image omits the API.

## Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest tests/ -v

# Run a single test
pytest tests/test_api.py::TestSendMsg::test_default_decoder_is_wazuh_aws -v
```

Tests live in `tests/test_api.py`. `conftest.py` inserts `api/` into `sys.path` so `import api` resolves to `api/api.py`. All socket I/O is mocked — no Wazuh instance needed.

## Build & Run

```bash
# Build both images locally
docker compose build

# Run with docker compose (configure env vars in docker-compose.yml first)
docker compose up

# Build individual image
docker build -f Dockerfile -t wazuh-agent:ingest .
docker build -f Dockerfile.agent -t wazuh-agent:node .
```

## Required Environment Variables

All config is injected at runtime via `envsubst` from `config/ossec.tpl` or `config/ossec_node.tpl`:

| Variable | Description |
|---|---|
| `MANAGER_URL` | Wazuh manager IP (enrollment) |
| `MANAGER_PORT` | Manager enrollment port (maps to 1515) |
| `SERVER_URL` | Wazuh worker/server IP (event forwarding) |
| `SERVER_PORT` | Worker port (maps to 1514) |
| `NAME` | Unique agent name — must differ per instance |
| `GROUP` | Wazuh group (must pre-exist in manager) |
| `ENROL_TOKEN` | Enrollment token / authd password |

If `NAME` is not set, the entrypoint appends a random 10-char suffix automatically.

## Architecture

### Ingest image startup (`bin/entrypoint.sh`)
1. Writes `ENROL_TOKEN` to `/var/ossec/etc/authd.pass`
2. Renders `config/ossec.tpl` → `/var/ossec/etc/ossec.conf` via `envsubst`
3. Starts `wazuh-agent` (`/var/ossec/bin/wazuh-control start`)
4. Starts the FastAPI ingest server (`api/start.sh` — uvicorn on port 9001)
5. Starts the readiness HTTP server (`web/ready.sh` — python3 http.server on port 9000)
6. Tails Wazuh logs to stdout

### Ingest API (`api/api.py`)
- `PUT /` — accepts a single JSON object and writes it to the Wazuh Unix socket at `/var/ossec/queue/sockets/queue`
- `PUT /batch` — accepts a JSON array and sends each element individually
- The `decoder` field in the payload controls the Wazuh message header (`1:<decoder>:`); defaults to `Wazuh-AWS`

### Readiness probe (`web/ready.sh`)
Polls `/var/ossec/var/run/wazuh-agentd.state` every 39 seconds. Writes `ready.html` when status is `connected`; removes it otherwise. The HTTP server on port 9000 returns 200/404 accordingly.

### ossec.tpl vs ossec_node.tpl
- `ossec.tpl` (ingest image): disables rootcheck, syscollector, syscheck, SCA, active-response — pure relay
- `ossec_node.tpl` (node image): enables rootcheck, syscollector, syscheck, active-response with host paths mounted at `/hostfs/`

## CI/CD

GitHub Actions (`.github/workflows/docker-publish.yml`) builds and pushes both images to GHCR on pushes to `main`, version tags, and weekly on Sundays. Images are published as:
- `ghcr.io/<repo>` — ingest image
- `ghcr.io/<repo>-node` — node/agent image

## Deployment

`deploy/agent/docker/docker-compose.yaml` shows the production node deployment pattern: mount host filesystem directories under `/hostfs/` so the agent can monitor the host without running privileged.
