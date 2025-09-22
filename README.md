# healthcheck-reporter

Lightweight health reporter that periodically probes database TCP connectivity and publishes a JSON report to MQTT.

## Installation

```bash
pip install healthcheck-reporter
```

## Usage

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
    interval_seconds=30.0,  # configurable, non-blocking
)

reporter.start()

# ... your service runs ...

# On shutdown
reporter.stop()
```

### Published payload

```json
{
  "database_status": "ok",
  "mqtt_client_id": "service-A-health",
  "timestamp": "2025-01-01T00:00:00+00:00",
  "db_error_count": 0,
  "mqtt_error_count": 0,
  "db_failure_rate": 0.0,
  "mqtt_failure_rate": 0.0,
  "overall_status": "operational"
}
```

### Notes
- A real PostgreSQL connection is attempted first (psycopg2 is required); otherwise it falls back to a TCP probe if the driver is unavailable in the environment.
- MQTT publish uses QoS 1 and reconnects if needed.
- `start()` runs a background thread (non-blocking). Use `stop()` on shutdown.

### Metrics
- Cumulative counters since process start:
  - `db_error_count`: number of failed DB probes
  - `mqtt_error_count`: number of failed MQTT publishes
- Failure rates (percentages):
  - `db_failure_rate`: failed DB probes / total DB probe attempts
  - `mqtt_failure_rate`: failed MQTT publishes / total MQTT publish attempts
- Derived overall status:
  - `operational`: DB is currently reachable and failure rates < 20%
  - `degraded`: failure rate of DB or MQTT >= 20%
  - `unavailable`: current DB probe failed