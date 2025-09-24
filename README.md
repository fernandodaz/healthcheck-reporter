# healthcheck-reporter

Lightweight health reporter that probes database connectivity and reports via MQTT or REST API.

## Installation

```bash
pip install healthcheck-reporter
```

### Dev setup (with Pylint)

```bash
pip install -e .[dev]
```

## Usage

### MQTT Mode

```python
from healthcheck_reporter import Reporter, ReporterConfig

config = ReporterConfig(
    database_host="db.example.local",
    database_port=5432,
    database_name="appdb",
    database_password="secret",
    database_user="app",
    mqtt_host="mqtt.example.local",
    mqtt_port=1883,
    mqtt_client_id="service-A-health",
    mqtt_topic="services/health",
    mqtt_user=None,      # or "user"
    mqtt_password=None,  # or "password"
)

reporter = Reporter(
    config,
    mode="mqtt",
    interval_seconds=30.0,  # configurable, non-blocking
    debug_mode=False,       # set to True for testing status transitions
)

reporter.start()

# ... your service runs ...

# On shutdown
reporter.stop()
```

### REST API Mode

```python
from healthcheck_reporter import Reporter, ReporterConfig

config = ReporterConfig(
    database_host="db.example.local",
    database_port=5432,
    database_name="appdb",
    database_password="secret",
    database_user="app",
    api_host="0.0.0.0",  # or "127.0.0.1" for localhost only
    api_port=8080,
    api_path="api/whatever/health",  # customizable path
)

reporter = Reporter(
    config,
    mode="rest",
    debug_mode=False,       # set to True for testing status transitions
)

# This will start a FastAPI server on port 8080 in the background
reporter.start()  # Non-blocking, starts server in background thread

# ... your service continues running ...

# On shutdown
reporter.stop()
```

### Published payload

```json
{
  "database_status": "ok",
  "mqtt_client_id": "service-A-health",
  "unix_timestamp": 1735689600,
  "db_error_count": 0,
  "mqtt_error_count": 0,
  "db_failure_rate": 0.0,
  "mqtt_failure_rate": 0.0,
  "overall_status": "operational",
  "api_error_count": 0,
  "api_failure_rate": 0.0,
  "uptime": 12.34
}
```

### Notes
- A real PostgreSQL connection is attempted first (psycopg2 is required); otherwise it falls back to a TCP probe if the driver is unavailable in the environment.
- **Both modes**: `start()` runs in a background thread (non-blocking). Use `stop()` on shutdown.
- **REST mode**: The health endpoint returns the same JSON structure as MQTT and is available at `http://{api_host}:{api_port}/{api_path}`.
- **Grafana integration**: If Grafana hits the endpoint when it's down, it will get a connection error (expected behavior). The health reporter tracks API availability internally and reports it in the metrics.

### Metrics
When running in REST mode, a Prometheus endpoint is available at `/metrics`.
Point Prometheus to scrape `http://{api_host}:{api_port}/metrics`.

- Cumulative counters since process start:
  - `db_error_count`: number of failed DB probes
  - `mqtt_error_count`: number of failed MQTT publishes
  - `api_error_count`: number of failed API health checks (REST mode only)
- Failure rates (percentages):
  - `db_failure_rate`: failed DB probes / total DB probe attempts
  - `mqtt_failure_rate`: failed MQTT publishes / total MQTT publish attempts
  - `api_failure_rate`: failed API health checks / total API health check attempts (REST mode only)
- Derived overall status:
  - `operational`: DB is currently reachable and all failure rates < 20%
  - `degraded`: failure rate of DB, MQTT, or API >= 20%
  - `unavailable`: current DB probe failed or API is down (REST mode)
  - Numeric code metric (Prometheus): `healthcheck_overall_status_code` — 0 operational, 1 degraded, 2 unavailable
- Debug mode (`debug_mode=True`): alternates between "degraded" and "unavailable" every 5 seconds for testing

## Development

### Linting

- Run Pylint on the project:

```bash
pylint src/healthcheck_reporter
```

### Changelog
- See the full changelog at: https://github.com/fernandodazadev/healthcheck-reporter/blob/main/CHANGELOG.md