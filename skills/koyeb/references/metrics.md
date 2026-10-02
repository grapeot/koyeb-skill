# Metrics Streaming, Telemetry Semantics & Traffic Diagnostics Reference

This reference documents telemetry collection, native official Koyeb CLI v5.12.0 streaming behavior, the lossless request metrics reader, `null` versus `0` sample semantics, and multi-factor traffic classification for autonomous agents.

---

## 1. Native CLI Metrics Exploration (`metrics get`)

The official Koyeb CLI retrieves performance and request metrics using the `metrics get` command:

```bash
# Query service metrics over a bounded time window
python3 scripts/koyeb_env.py -- metrics get --service example-app/example-service \
  --start 2026-01-01T00:00:00Z --end 2026-01-01T01:00:00Z -o json
```

### Verified CLI Streaming Realities (v5.12.0)
- **Chained JSON Objects**: When `-o json` is requested, the native CLI emits independent JSON objects (one per metric name) rather than a single top-level JSON array or wrapper object:
  ```json
  {"metric_name":"CPU_TOTAL_PERCENT","data":[{"timestamp":"2026-01-01T00:00:00Z","value":0.02}]}
  {"metric_name":"HTTP_THROUGHPUT","data":[{"timestamp":"2026-01-01T00:00:00Z","value":0}]}
  ```
  Passing this output directly into standard `json.load()` fails with a JSON decode error. Automated callers must parse JSON frames iteratively:
  ```python
  # Safe stdlib parsing of chained JSON frames from CLI stdout
  import json
  frames = [json.loads(line) for line in stdout_text.strip().splitlines() if line.strip()]
  ```
- **Fixed Metric Set**: The CLI command always fetches 9 predefined metrics: `CPU_TOTAL_PERCENT`, `MEM_RSS`, `HTTP_THROUGHPUT`, `HTTP_RESPONSE_TIME_50P`, `HTTP_RESPONSE_TIME_90P`, `HTTP_RESPONSE_TIME_99P`, `HTTP_RESPONSE_TIME_MAX`, `PUBLIC_DATA_TRANSFER_IN`, and `PUBLIC_DATA_TRANSFER_OUT`.
- **No Name or Step Filters**: The CLI does **not** provide `--name` or `--step` flags. Do not invent non-existent flags such as `--name HTTP_THROUGHPUT` or `--step 1h` for the CLI.
- **Service vs. Instance Scope**: Service-level queries provide HTTP throughput segmented by status code family (e.g. `2xx`, `4xx`, `5xx`). Instance-level queries provide only CPU and memory, which are unsuitable for detecting application request activity.
- **Lossy Zero Flattening**: In the official CLI source ([`metrics_get.go`](https://github.com/koyeb/koyeb-cli/blob/v5.12.0/pkg/koyeb/metrics_get.go)), `MetricsJSONData` uses non-null `float64` and reads `.GetValue()`. Verified raw `null` samples become `0` in CLI JSON; per-series labels are flattened away. A timestamp grid of CLI zeros does not establish complete numeric telemetry coverage.

---

## 2. Lossless Request Metrics Reader (`scripts/request_metrics.py`)

To support automated zero-traffic decisions, scale-to-zero validation, and fleet telemetry retention without lossy conversions, this repository provides a dedicated, read-only standard-library reader:

```bash
# Query lossless HTTP throughput for a specific service ID
python3 scripts/request_metrics.py \
  --service-id example-service-id \
  --start 2026-01-01T00:00:00Z \
  --end 2026-01-01T01:00:00Z \
  --step 5m \
  --env-file ./.env
```

### Reader Architecture & Endpoint Exception
- **Strict Boundary**: This script represents an explicit, narrow read-only exception justified by the lossy conversion in the official CLI. It is not a generic REST API client or multi-resource mutation tool.
- **Target Endpoint**: Sends a fixed HTTPS GET request to `https://app.koyeb.com/v1/streams/metrics`. Do not query `/v1/metrics`, which returns HTTP `404 Not Found`.
- **Duration Format**: The `--step` parameter requires valid Go duration strings (e.g. `5m`, `1h`, default `1h`). Bare numeric integers (such as `300` or `3600`) are rejected with an error by the upstream API.
- **Payload Preservation**: Writes the raw JSON stream object containing per-series labels, timestamps, and explicit `null` samples, preserving the distinction between no sample and numeric zero:
  ```json
  {
    "metrics": [
      {
        "labels": {"code": "2xx", "service_id": "example-service-id"},
        "samples": [
          {"timestamp": "2026-01-01T00:00:00Z", "value": null},
          {"timestamp": "2026-01-01T00:05:00Z", "value": 0.0},
          {"timestamp": "2026-01-01T00:10:00Z", "value": 7}
        ]
      }
    ]
  }
  ```
- **Safe Authentication**: Reuses `scripts/koyeb_env.py` credential parsing (`KOYEB_API_KEY` as literal token or `op://` reference). HTTP failures return sanitized status codes without printing sensitive authorization headers or tokens.

---

## 3. Practical Semantics: Null vs. Zero & 3-State Classification

Interpreting serverless traffic requires distinguishing between explicit zero measurements and missing telemetry samples:

| State | Telemetry Condition | Operational Interpretation & Action |
| :--- | :--- | :--- |
| **Positive Traffic** | Any sample with `HTTP_THROUGHPUT > 0` or verified incoming HTTP log | **Active Workload**. Confirms recent usage, including web crawlers, bots, scanners, 404 requests, and external synthetic monitors. Project policy dictates scaling or sleep thresholds; the skill does not enforce a global default. |
| **Verified Zero Measurements** | Numeric `0` across complete coverage, collection is known valid, and no contradictory request logs | **Zero observed measurements** for the stated interval. State the source and coverage rather than claiming the service was never used. |
| **Unknown / Candidate** | All-null, mixed null/zero gaps, unavailable history, or query errors without positive evidence | **Insufficient evidence**. Candidate for evaluation, not proof of abandonment; do not automatically sleep or delete on this basis. |

### Telemetry Decision Rules
1. **Never Treat Null as Zero**: A raw `null` is an absent sample; its cause is not established by the response. The native CLI masks this by emitting `0`, leading to false idle conclusions.
2. **Sample Count Is Not Request Count**: Count positive buckets for activity evidence, not visitors. Confirm units and aggregation semantics before summing metric values; do not assume every metric is a rate or that all metrics share one aggregation rule.
3. **Step Aggregation Fidelity**: Experiments on active control services confirmed that `1h` and `5m` steps preserve aggregated traffic values, but this does not guarantee identical aggregation curves across all custom metrics.
4. **Coverage Accounting**: State explicit coverage (e.g., "12 of 12 5-minute intervals reported numeric 0.0") before classifying a workload as idle.
5. **Multi-Series Label Inspection**: Inspect all returned status code families. Positive `4xx` or `5xx` values still represent recorded requests; they are not proof of successful business use or of a particular sleep state.

---

## 4. Telemetry Validation, Health & Log Cross-Checks

Metrics should never be evaluated in isolation. Autonomous decisions must cross-correlate telemetry with platform lifecycle events and application logs:

### A. Active Baseline Control & Stale Telemetry
- Always compare unknown candidates against known active baseline controls to verify that platform telemetry ingestion is operational.
- Real-world platform testing identified services exhibiting all-null metric series while simultaneously recording positive platform wake events:
  ```
   New request received. Waking up from deep sleep.
  ```
- **Rule**: Metrics alone cannot prove that a service was never accessed. Positive wake events are authoritative proof of recent external traffic even when metrics streams are null.
- Telemetry ingestion may experience propagation lag; avoid assuming a service is inactive immediately following deployment.

### B. Internal Health Checks vs. External Activity
- Internal Koyeb platform health checks (e.g. hitting `/health` or `/`) generate frequent HTTP access logs.
- **Rule**: Inspect `definition.health_checks` and request source where available. Internal platform pingers are not external traffic, but an external monitor may request the same path. Path matching alone cannot prove the source; qualify ambiguous health-only logs.
- Distinguish incoming application access logs from outbound HTTP client logs generated by background worker tasks.

### C. Query Windows & Log Retention Boundaries
- **Metric Retention**: Koyeb UI and documentation cite a 7-day metrics window, but the underlying streaming API has successfully fulfilled 14-day queries displaying historical traffic older than 7 days. Do not hardcode a rigid 7-day API cap, nor guarantee 14-day retention for every account tier indefinitely.
- **Log Retention**: Documentation lists plan-dependent retention of 1 to 30 days. In the tested account a 14-day query failed; a recent 7-day query succeeded while the preceding 7-day chunk returned HTTP `400`. Do not generalize that response to every account or version.
- **Query Failure $\neq$ Inactivity**: Split long queries into bounded intervals to diagnose the available window, recording success/errors per interval. Chunking cannot recover unavailable history. An API error is not an empty log or proof of zero activity.
- **Query Formatting**: Use explicit ISO 8601 UTC timestamps (e.g. `2026-01-01T00:00:00Z`). For live streaming, pass `--tail` as a boolean switch. Avoid complex escaped regular expressions that have triggered HTTP `500` errors on the upstream streaming API; prefer simple text substring filtering.

---

## 5. Verification Workflow for Traffic Audits

When evaluating services for scale-to-zero candidates or sleep policy adjustments:

1. **Resolve Target ID**: Retrieve the internal service ID using `koyeb services get example-app/example-service -o json`.
2. **Execute Lossless Telemetry Query**: Run `scripts/request_metrics.py` across the target audit window (e.g. prior 7 days).
3. **Cross-Check Platform Logs**: Query bounded runtime logs using `services logs` over recent wake intervals to check for platform wake logs or incoming requests.
4. **Verify Baseline Telemetry**: Confirm telemetry pipeline health by checking an active baseline service within the same account.
5. **Classify Outcome**: Apply the 3-state criteria (Positive Traffic, Verified Zero, or Unknown/Candidate).
6. **Guardrail**: Never delete resources or alter sleep configurations automatically based on telemetry alone without explicit user task authorization.

---

## 6. Official References & Source Links

- [Official Koyeb CLI Repository](https://github.com/koyeb/koyeb-cli)
- [Official Koyeb Metrics Documentation](https://www.koyeb.com/docs/run-and-scale/metrics)
- [Koyeb CLI `metrics_get.go` Source](https://github.com/koyeb/koyeb-cli/blob/v5.12.0/pkg/koyeb/metrics_get.go)
- [Official API client metrics endpoint](https://github.com/koyeb/koyeb-api-client-go/blob/master/api/v1/koyeb/api_metrics.go)
