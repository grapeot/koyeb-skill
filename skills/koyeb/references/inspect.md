# Resource Inspection & Diagnostics Reference

This reference covers inventory discovery, state inspection, JSON parsing, pagination behaviors, and log diagnostics using official Koyeb CLI v5.12.0 commands via the launcher.

---

## 1. Inventory & Resource Querying

Always append `-o json` when querying resources to obtain structured, parseable attributes.

### A. Applications
```bash
# List all applications
python3 scripts/koyeb_env.py -- apps list -o json

# Get application summary
python3 scripts/koyeb_env.py -- apps get example-app -o json

# Detailed application description (includes domains and service summaries)
python3 scripts/koyeb_env.py -- apps describe example-app -o json
```

### B. Services
Always specify `--app <app_name>` when querying services to avoid ambiguity:
```bash
# List services within an application (optionally filtered by name)
python3 scripts/koyeb_env.py -- services list --app example-app -o json
python3 scripts/koyeb_env.py -- services list --app example-app --name example-service -o json

# Get service metadata (uses app/service positional notation)
python3 scripts/koyeb_env.py -- services get example-app/example-service -o json

# Describe full service status (active deployment, routes, scale, and ports)
python3 scripts/koyeb_env.py -- services describe example-app/example-service -o json
```

### C. Deployments & Instances
A service maintains multiple historical deployments. The `latest` deployment is not necessarily the currently `active` serving deployment:
```bash
# List deployments for a specific service
python3 scripts/koyeb_env.py -- deployments list --app example-app --service example-app/example-service -o json

# Inspect a specific deployment by ID
python3 scripts/koyeb_env.py -- deployments get d1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d -o json

# List active and historical instances for a service
python3 scripts/koyeb_env.py -- instances list --app example-app --service example-app/example-service -o json
```

---

## 2. Pagination Realities & The REST Fallback Policy

### CLI Pagination Realities
- **No Limit/Offset Flags in CLI**: The official Koyeb CLI `services list` command **does not** support `--limit`, `--offset`, or `--page` flags. Do not invent non-existent flags.
- **Inspect Response Count**: When parsing JSON responses, check the array length. Never assume an omitted service or deployment does not exist; check native CLI filtering flags (`--name`, `--app`).
- **Internal CLI Handling**: The inspected `services list` implementation requests pages of 100 using `limit`/`offset` until the API count is covered. It omits database services, which are listed separately with the database commands. Verify other list commands rather than assuming identical behavior.

### REST Fallback Policy (Strict Boundary)
If and only if an agent encounters hard evidence of CLI truncation where older records cannot be queried through the CLI:
1. Do **not** write or introduce an external Python API client library.
2. An authorized fallback may query the official REST API using an existing HTTP tool and separately resolved credentials. The launcher injects credentials only into its CLI child; it does not export them into the caller's shell.
3. Koyeb's REST API uses standard `limit` and `offset` query parameters (e.g. `GET https://app.koyeb.com/v1/services?limit=100&offset=0`). Do not invent proprietary page tokens.
4. Note that detailed configuration definitions are often stored under deployment objects (`/v1/deployments/<id>`) rather than service summaries.

---

## 3. Log Diagnostics & Time Windows

Koyeb separates build logs (compilation, image building) from runtime logs (container execution).

### A. Tail Live Logs
The `--tail` flag in Koyeb CLI is a **boolean switch** (enable tailing), **not** an integer line count. Passing a numeric argument (e.g. `--tail 50`) is invalid syntax:

```bash
# Stream runtime logs (caller must enforce a bounded timeout)
python3 scripts/koyeb_env.py -- services logs example-service --app example-app --tail

# Stream build logs for diagnosing compilation or image assembly failures
python3 scripts/koyeb_env.py -- services logs example-service --app example-app --type build --tail
```

### B. Historical Bounded Logs & Window Limits
To retrieve historical logs without indefinite streaming, use explicit ISO 8601 UTC timestamps:
```bash
python3 scripts/koyeb_env.py -- services logs example-service --app example-app --type runtime \
  --start-time 2026-01-01T00:00:00Z --end-time 2026-01-01T00:10:00Z
```

#### Log Retention & Query Boundaries
- **Plan-Specific Retention**: Log retention varies by account plan tier (typically between 1 and 30 days).
- **Observed HTTP 400 Boundary**: In the tested account, a 14-day request failed, the recent 7-day chunk succeeded, and the preceding chunk returned HTTP `400`. Treat this as observed availability, not a universal endpoint rule.
- **Chunking Cannot Recover Missing History**: Smaller bounds can locate the available interval but cannot establish that unavailable older logs contained no requests.
- **Query Failure $\neq$ Empty Log $\neq$ Inactivity**: A log retrieval failure or 400 error is not an empty log and must never be reported as evidence of zero traffic or non-use.
- **Log Streaming Filters**: Avoid complex escaped regular expressions in CLI log filters, which have been observed to cause HTTP `500` errors on the upstream stream handler; use simple text substrings instead. (Do not assume regex is globally unsupported, but exercise caution with escaped characters).
- **Metrics vs. Logs Time Windows**: The metric streaming API has successfully fulfilled queries up to 14 days (despite UI documentation showing 7 days). Do not hardcode a rigid 7-day maximum for the metric API, nor guarantee 14-day log retention.

### C. Streaming Process Control
When an agent or script invokes a tailing command:
- The streaming process must be governed by a **bounded timeout enforced by the caller** (e.g. timeout after 30 seconds).
- Do not let streaming log processes hang indefinitely in the background.

---

## 4. Health Status Nuances & Diagnostic Interpretation

### A. Service Status vs. Active & Latest Deployment State
Always inspect both `latest_deployment_id` and `active_deployment_id` in `services get -o json`. A service status reflects composite health, not just the newest build:

1. **Service `HEALTHY`, Active Deployment `SLEEPING`**:
   - `service.status = HEALTHY`
   - `service.active_deployment_id = d5e6f7a8` (Deployment status: `SLEEPING`)
   - **Meaning**: The active deployment is sleeping, not currently running merely because the service summary says healthy. Supported incoming traffic can wake it; verify the actual public route before claiming the application works.

2. **Service `DEGRADED`, Latest Deployment `ERROR`**:
   - `service.status = DEGRADED`
   - `service.latest_deployment_id = d9a0b1c2` (Deployment status: `ERROR`)
   - `service.active_deployment_id = d5e6f7a8` (Deployment status: `HEALTHY` or `SLEEPING`)
   - **Meaning**: A newer deployment failed but an older active deployment remains. It may be serving or sleeping; do not infer a complete outage from `DEGRADED` alone. Inspect that deployment and actual endpoint evidence.

3. **Service `UNHEALTHY`, No Active Deployment**:
   - `service.status = UNHEALTHY`
   - `service.active_deployment_id = null`
   - `service.latest_deployment_id = d9a0b1c2` (Deployment status: `ERROR`)
   - **Meaning**: No deployment is serving traffic and the latest deployment failed. The service is down.
   - **No Auto-Deletion**: Koyeb does not automatically delete failed or unhealthy services; they remain present for diagnostic review.

### B. Internal Platform Health Checks vs. External Requests
- **Configured Health Checks**: Inspect deployment `definition.health_checks` (for example an HTTP `/health` path), not just public routes.
- **Access Log Interpretation**: Internal HTTP checks can make logs busy without external traffic. The same path may also receive external probes, so use source evidence where available and qualify ambiguous health-only records.
- **Distinguish Log Direction**: Identify application HTTP access logs (incoming requests) and distinguish them from outgoing HTTP client logs emitted by background jobs or API clients.
- **Authoritative Wake Events**: Platform lifecycle logs recording:
  ```
   New request received. Waking up from deep sleep.
  ```
  provide definitive proof of external incoming traffic, even if metric stream samples are null.

### C. JSON Output Structures: Single vs. Chained Frames
- Resource queries (`apps get -o json`, `services get -o json`) return a **single valid JSON document** parseable with `json.loads()`.
- Native metric queries (`metrics get -o json`) return **chained JSON frames** (multiple independent JSON objects concatenated together). Callers must parse frames individually.

### D. Root Path HTTP 404 vs Broken Service
- Many backend APIs only expose routes at specific subpaths (e.g. `/api/v1` or `/health`) and return HTTP `404 Not Found` at the root path (`/`).
- **Diagnosis Guideline**: An HTTP `404` at `https://example-app.koyeb.app/` does **not** indicate service failure. Check `services describe` for healthy container status and inspect the project runbook for the designated health check endpoint.
