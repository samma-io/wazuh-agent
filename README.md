
# Wazuh Agent in Docker

This Dockerized Wazuh agent is designed **not to monitor its local container**, but instead to act as a **data ingestion proxy** that receives external JSON data via a custom-built API and forwards it to a Wazuh manager. This setup is ideal for forwarding logs, alerts, or structured security data from various sources into your Wazuh ecosystem.

> ⚠️ This container is not for host monitoring. It acts only as a relay to ingest remote or aggregated data.

---

## How It Works

- Auto-registers with the Wazuh manager using an enrollment token
- Disables all local system monitoring checks (CPU, RAM, filesystem, etc.)
- Includes a helper endpoint to verify if the agent is connected to the Wazuh manager
- Accepts JSON payloads via a simple API and forwards them to the manager socket interface

---

## API Behavior

A minimal REST API is launched alongside the agent to receive external JSON data. Any valid JSON object POSTed to this API is passed along to the manager as if it came from a regular agent.

- **No validation or transformation** — acts as a dumb pipe
- Designed for **speed and simplicity**
- Useful for mass ingestion of pre-formatted logs or events

### Example Usage

```bash
curl -X POST http://<agent-ip>:5000/event \
  -H "Content-Type: application/json" \
  -d '{"event_type":"login","user":"admin","status":"success","timestamp":"2025-04-12T15:45:00Z"}'
```

---

## Configuration

All configuration is handled via environment variables. Below is a Docker Compose snippet showing how to configure the container:

```yaml
services:
  wazuh-agent:
    image: custom/wazuh-agent:latest
    environment:
      - MANAGER_URL=192.168.1.36         # IP or hostname of the Wazuh manager
      - MANAGER_PORT=32466               # Manager port (should map to 1515 inside container)
      - SERVER_URL=192.168.1.36          # Worker/Manager node for syslog-like data (usually 1514)
      - SERVER_PORT=30851                # Should route to 1514 (UDP/TCP)
      - NAME=docker-relay-33             # Unique agent name (must be different per instance)
      - GROUP=default                    # Wazuh agent group (must exist in the manager)
      - ENROL_TOKEN=CUSTOM_PASSWORD      # Enrollment token (preconfigured in Wazuh)
    ports:
      - "5000:5000"                      # API listener for incoming JSON data
```

### Required Environment Variables

| Variable       | Description                                                  |
|----------------|--------------------------------------------------------------|
| `MANAGER_URL`  | IP address of the Wazuh manager                              |
| `MANAGER_PORT` | Port to connect to the Wazuh manager for enrollment (default: 1515) |
| `SERVER_URL`   | Wazuh manager/server to send data to                         |
| `SERVER_PORT`  | Port for forwarding event data (default: 1514)               |
| `NAME`         | Unique agent name (must be unique per instance)             |
| `GROUP`        | Wazuh group name (must exist)                                |
| `ENROL_TOKEN`  | Token for automatic enrollment                               |

---

## Production Readiness

> 🚧 **Not yet production-ready.** This container is experimental and primarily for development, testing, or custom integrations.

### To-do for production:

- Add TLS support for the API endpoint
- Input validation and schema enforcement
- Rate limiting and logging
- Docker healthcheck and retry logic

### Contributions welcome!

Feel free to fork and PR improvements or raise issues if you want to enhance the functionality.

---

## Example Use Cases

- Aggregating security events from multiple services or IoT devices
- Ingesting logs from non-Wazuh-compatible systems via custom exporters
- Bridging cloud event sources into your on-prem Wazuh manager

---

