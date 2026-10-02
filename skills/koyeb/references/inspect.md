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
A service has multiple historical deployments. The `latest` deployment is not necessarily the currently `active` serving deployment:
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

## 3. Log Diagnostics & Error Investigation

Koyeb separates build logs (compilation, image building) from runtime logs (container execution).

### A. Tail Live Logs
The `--tail` flag in Koyeb CLI is a **boolean switch** (enable tailing), **not** an integer line count. Passing a numeric argument (e.g. `--tail 50`) is invalid syntax.

```bash
# Stream runtime logs (caller must enforce a bounded timeout)
python3 scripts/koyeb_env.py -- services logs example-service --app example-app --tail

# Stream build logs for diagnosing compilation or image assembly failures
python3 scripts/koyeb_env.py -- services logs example-service --app example-app --type build --tail
```

### B. Historical Bounded Logs
To retrieve historical logs without indefinite streaming, use explicit ISO 8601 UTC timestamps:
```bash
python3 scripts/koyeb_env.py -- services logs example-service --app example-app --type runtime \
  --start-time 2026-01-01T00:00:00Z --end-time 2026-01-01T00:10:00Z
```

### C. Streaming Process Control
When an agent or script invokes a tailing command:
- The streaming process must be governed by a **bounded timeout enforced by the caller** (e.g. timeout after 30 seconds).
- Do not let streaming log processes hang indefinitely in the background.

---

## 4. Diagnostic Interpretation & Common Edge Cases

### Deployment and Instance Status
Treat deployment and instance state as separate resource types. Deployment states such as `PENDING`, `STARTING`, `HEALTHY`, and `SLEEPING` describe rollout or serving state; instance states such as `ALLOCATING`, `STARTING`, `HEALTHY`, `STOPPING`, and `STOPPED` describe individual runtime lifecycles. Read current status messages and build/runtime logs for the actual cause. A stopped historical instance does not establish that the active deployment is sleeping.

### Root Path HTTP 404 vs Broken Service
- Many backend APIs and microservices only register routes at subpaths (e.g., `/api/v1/health` or `/graphql`) and return HTTP `404 Not Found` at the root `/`.
- **Diagnosis Guideline**: An HTTP `404` at `https://example-app.koyeb.app/` does **not** indicate service failure. Check `services describe` for healthy container status and inspect the project runbook for the configured healthcheck path.
