---
name: koyeb
description: Operate Koyeb serverless applications, services, deployments, sleep/wake lifecycles, domains, and secrets using the official Koyeb CLI and standard-library launcher.
---

# Koyeb Operations Skill

## 1. Goal & Outcome
Teach autonomous AI agents and engineers to inspect, diagnose, deploy, configure, scale, and manage Koyeb cloud workloads safely and deterministically without exposing management credentials or inventing non-existent CLI flags.

### Key Capabilities
- **Inventory & Diagnostics**: Query applications, services, deployments, and instances via official CLI JSON output, and inspect build/runtime/platform logs.
- **Controlled Deployments**: Execute authorized updates, rebuilds, and configuration changes using `--skip-build` and `--wait` where appropriate; availability requirements come from the project runbook.
- **Sleep & Scale Management**: Configure light and deep sleep idle delays down to zero (`--min-scale 0`) without false-positive wakeups or false-negative diagnoses.
- **Secrets & Domains**: Mount encrypted runtime secrets (`{{secret.NAME}}`) and configure custom domains via Koyeb-managed CNAME targets.

---

## 2. Resource Hierarchy & Precedence
Operations follow a strict separation of scopes and three-tier precedence:

1. **Public Skill (This Repository)**: Generic, transferable Koyeb CLI execution patterns, argument rules, and output verification contracts. Contains NO hardcoded account IDs, token values, or local file paths.
2. **Private Overlay (`.env` / 1Password)**: Target credential resolution (`KOYEB_API_KEY` as literal string or `op://` reference), local workspace paths, and optional CLI targeting flags (`--organization`, `--project`). Discovered via local `AGENTS.md`, `CLAUDE.md`, or workspace routing files.
3. **Project Policy & Runbooks**: Application-specific topology, instance sizing, target regions, sleep timeout schedules, external database migrations, and external DNS records.

### Precedence Contract
```
Explicit User Task > Applicable Project Policy/Runbook > Current Live Configuration
```
- Never assume global defaults for instance sizes, regions, or sleep delays (e.g., 5m light / 0 deep is an illustrative example, not a universal policy).
- Authorized tasks (e.g., user requesting redeploy, scale, or delete) must proceed without redundant interactive reconfirmation prompts.
- Agent decides sequence autonomously; prescriptive order is enforced only where strict dependencies exist (e.g., secret creation prior to service reference, domain creation prior to CNAME retrieval).

---

## 3. Launcher Execution Contract
All Koyeb CLI invocations must execute through the zero-dependency launcher `scripts/koyeb_env.py` to prevent credential exposure in process argument tables (`argv`) or shell history:

```bash
# Standard syntax (uses ./.env by default)
python3 scripts/koyeb_env.py -- <koyeb-args...>

# Explicit environment file or binary
python3 scripts/koyeb_env.py --env-file /path/to/.env --koyeb-bin /path/to/koyeb -- <koyeb-args...>
```

### Safety Rules & Exit Codes
- **Prohibited Flags**: The launcher explicitly rejects `--token`, `--debug-full`, and `--url` (exits with code `2`). Never pass tokens in `argv`.
- **Credential Parsing**: Reads `KOYEB_API_KEY` from `.env`. Rejects duplicate keys or malformed assignments (exits code `1`). Resolves `op://` references via `op read` (30s timeout).
- **Environment Isolation**: Injects `KOYEB_TOKEN`, removes `KOYEB_API_KEY`, pins `KOYEB_URL=https://app.koyeb.com`. Ambient credentials never silently override target `.env`.
- **Exit Propagation**: Preserves child exit status verbatim (e.g., code `127` if binary missing; signal standard `128 + signal`).
- **Organization / Project Targeting**: Specify `--organization <org>` or `--project <proj>` explicitly in forwarded arguments when multiple organizations or workspaces exist.

---

## 4. Operational Workflow & Command Patterns

### A. Discovery & Inspection
Always prioritize structured JSON output (`-o json`) when inspecting state:
```bash
# List applications and services
python3 scripts/koyeb_env.py -- apps list -o json
python3 scripts/koyeb_env.py -- services list --app example-app --name example-service -o json

# Detailed resource inspection
python3 scripts/koyeb_env.py -- services get example-app/example-service -o json
python3 scripts/koyeb_env.py -- services describe example-app/example-service -o json
python3 scripts/koyeb_env.py -- deployments list --service example-app/example-service --app example-app -o json
python3 scripts/koyeb_env.py -- instances list --service example-app/example-service --app example-app -o json
```
*Note*: `services list` does not support `--limit` or `--offset` flags. Check item count and native array length; do not assume omitted rows are missing.

### B. Diagnostics & Historical Logs
```bash
# Historical runtime logs (UTC timestamps, bounded query)
python3 scripts/koyeb_env.py -- services logs example-service --app example-app --type runtime \
  --start-time 2026-01-01T00:00:00Z --end-time 2026-01-01T00:10:00Z

# Tail current logs (--tail is a boolean, not a line count)
python3 scripts/koyeb_env.py -- services logs example-service --app example-app --tail
```
*Rule*: Bounded callers must control streaming timeouts. Root HTTP 404 is not proof of service failure; check container status and application route paths.

### C. Configuration & Deployments
Updates merge existing configurations by default; use `--override` only when deliberately replacing definitions:
```bash
# Redeploy using existing build artifact (fast)
python3 scripts/koyeb_env.py -- services redeploy example-app/example-service --skip-build --wait

# Update configuration with sleep and scaling parameters
python3 scripts/koyeb_env.py -- services update example-app/example-service \
  --light-sleep-delay 5m --deep-sleep-delay 0 --min-scale 0 --max-scale 1 \
  --skip-build --wait --wait-timeout 5m
```
*Guardrails*:
- `--save-only` saves definition changes without deploying; never report a `save-only` update as an active deployment.
- Rebuilds: Code or Dockerfile changes require a full build; `--skip-build` is only valid when reusing prior successful images.

### D. Sleep & Wake Lifecycle
- Setting a delay to `0` individually disables that sleep tier (e.g. `--deep-sleep-delay 0`).
- Sleep requires autoscaling down to zero (`--min-scale 0`) on an eligible instance type.
- Control-plane CLI queries (`describe`, `list`) do NOT wake instances. Inbound HTTP data traffic wakes instances.
- Never poll public HTTP endpoints when waiting for sleep; polling resets the idle timer.

### E. Runtime Secrets & Custom Domains
```bash
# Create runtime secret via stdin (no argv exposure)
echo "example-secret-value" | python3 scripts/koyeb_env.py -- secrets create EXAMPLE_SECRET --value-from-stdin

# Attach secret reference to service environment (merges by default)
python3 scripts/koyeb_env.py -- services update example-app/example-service --env 'API_KEY={{secret.EXAMPLE_SECRET}}'

# Register custom domain and inspect intended CNAME
python3 scripts/koyeb_env.py -- domains create example.com --attach-to example-app
python3 scripts/koyeb_env.py -- domains get example.com -o json
```
*Boundary*: External DNS, managed databases, and reverse proxies belong to project runbooks. Koyeb commands only mutate Koyeb resources.

---

## 5. Output Verification & Reporting Contract
Upon completing an action, output a structured factual report containing:
1. **Target**: Exact application and service name (`example-app/example-service`).
2. **Action & Flags**: Summary of command executed (e.g., update with `--skip-build`).
3. **Before & After State**: Prior vs updated deployment ID, scaling limits, or sleep delays.
4. **Verification Evidence**: Live status from `services describe` or `instances list` (e.g. `HEALTHY`, `SLEEPING`), endpoint response, or log excerpt.
5. **Rollback Reference**: Prior deployment ID in case reversion is required.
6. **Privacy Invariant**: Allowlisted configuration fields only. Never dump raw environment variables, API tokens, or secret values.

### Example Output Report
```markdown
### Koyeb Operation Report
- **Target**: `example-app/example-service`
- **Action**: Update sleep delay and min-scale (`--light-sleep-delay 5m --min-scale 0 --skip-build --wait`)
- **Deployment**: `d1b2c3d4` -> `d5e6f7a8` (Status: `HEALTHY`)
- **Configuration Delta**: `min_scale: 1 -> 0`, `light_sleep_delay: 0 -> 300s`
- **Verification**: Configuration readback and application HTTP response passed; actual sleep/wake behavior remains unverified until explicit lifecycle logs are observed.
- **Rollback Ref**: Re-apply previous configuration using deployment `d1b2c3d4`.
```

---

## 6. Progressive Disclosure References
For deep-dive instructions, edge cases, and failure modes, consult:
- [`references/auth.md`](references/auth.md) — Launcher mechanics, 1Password integration, and credential safety boundaries.
- [`references/inspect.md`](references/inspect.md) — Inventory querying, JSON schemas, pagination caveats, and log diagnostics.
- [`references/changes.md`](references/changes.md) — Service creation, updates, `skip-build`, secrets mounting, and rollbacks.
- [`references/sleep.md`](references/sleep.md) — Light vs deep sleep mechanics, idle resets, latency metrics, and wake verification.
- [`references/fleet.md`](references/fleet.md) — Multi-service orchestration, batch updates, stop-on-failure policy, and runbooks.
