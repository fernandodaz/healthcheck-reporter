# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2025-09-23
### Changed
- Breaking: JSON payload timestamp field renamed from `timestamp` (ISO 8601 string) to `unix_timestamp` (integer seconds since epoch).

### Added
- Prometheus metrics endpoint at `/metrics` when running in REST mode.
  - Exposes gauges: `healthcheck_database_ok`, `healthcheck_db_error_count`, `healthcheck_mqtt_error_count`, `healthcheck_api_error_count`,
    `healthcheck_db_failure_rate_percent`, `healthcheck_mqtt_failure_rate_percent`, `healthcheck_api_failure_rate_percent`, `healthcheck_uptime_seconds`, and labeled `healthcheck_overall_status`.
- Dependency: `prometheus-client`.

## [0.2.2] - 2025-09-23
### Added
- Configurable status thresholds via constructor parameters:
  - `degraded_threshold_percent` (default 20.0)
  - `unavailable_threshold_percent` (default 100.0)
- Threshold evaluation centralized in `HealthReport.to_dict()`.

## [0.2.1] - 2025-09-23
### Changed
- Centralized DTO: added `HealthReport.to_dict()` and updated REST/MQTT to use it.
- Moved all derived fields computation (failure rates, overall status, database_status, timestamp) into `to_dict()` to avoid duplication.
- Ensured `uptime` appears in REST response and MQTT payload.

### Fixed
- Typing: imported `Literal` and removed unnecessary type ignores by narrowing Optionals.

## [0.2.0] - 2025-09-23
### Added
- Modular architecture:
  - core: `ReporterConfig`, `HealthReport`
  - probes: DB connectivity probes
  - transport: MQTT publisher and FastAPI server
  - reporter: report builder and orchestrator
- REST mode (FastAPI) with non-blocking background server
- MQTT mode publishing with QoS 1 and reconnect
- psycopg2 PostgreSQL probe with TCP fallback
- Failure counters and rates for DB, MQTT, and API
- Overall status: `operational`, `degraded`, `unavailable`
- Debug mode to alternate status for testing
- Configurable API host/port/path
- Startup logs for mode and connection details
- Uptime metric field `uptime` (seconds) reflecting service runtime

### Changed
- Public API now exposed via `from healthcheck_reporter import Reporter, ReporterConfig, HealthReport`
- README updated for MQTT and REST examples

### Removed
- Legacy `health_checker.py` and `models.py`
