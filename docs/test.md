# Test Strategy & Quality Assurance Plan

**Project**: Koyeb Skill (`grapeot/koyeb-skill`)
**Status**: 17 Offline Tests and Read-Only Smoke Checks Verified
**Target Test Suites**: `tests/test_koyeb_env.py` (verified), `tests/test_request_metrics.py` (planned)
**Evaluations**: `evals/evals.json`

---

## 1. Testing Philosophy & Guardrails

1. **Strict Offline Unit Testing**:
   - Automated unit tests must run offline without internet connectivity.
   - External CLI tools (`koyeb`, `op`) and HTTP networking (`urllib.request`) must be intercepted with deterministic stubs or standard library mocks (`unittest.mock`).
   - No automated tests may create, mutate, or delete live cloud infrastructure.
2. **Zero Secret Leakage Verification**:
   - Every test case involving credentials must assert that secrets do not appear in command line arguments, process listings, log outputs, or error tracebacks.
3. **Exit Code & Stream Preservation**:
   - Tests must assert that child process return codes and stdio streams pass through unaltered.
4. **Lossless Telemetry Fixtures**:
   - Test fixtures for metrics stream responses must explicitly preserve `null` sample values to verify that the reader does not mimic the native CLI's lossy flattening to `0`.
5. **Architectural Guardrail**:
   - No generic API client; only narrow lossless metric reader exception.

---

## 2. Unit Test Matrix

### 2.1 Launcher Test Suite (`tests/test_koyeb_env.py` — Verified)

The unit test suite (`tests/test_koyeb_env.py`) uses Python's built-in `unittest` framework to validate `scripts/koyeb_env.py`. All 12 tests passed on 2026-10-02. Read-only CLI 5.12.0 smoke checks passed for credential resolution, resource inspection, service listing, and bounded lifecycle logs. Scenario prompts are authored, not cross-harness benchmark results.

| Test ID | Test Category | Target Behavior | Expected Outcome |
| :--- | :--- | :--- | :--- |
| `TC-AUTH-01` | Auth: Literal Token | `KOYEB_API_KEY=literal-key-value` in `.env` | Launcher sets `KOYEB_TOKEN=literal-key-value` in child env; child process receives it. |
| `TC-AUTH-02` | Auth: 1Password Ref | `KOYEB_API_KEY=op://vault/item/field` in `.env` | Launcher invokes `op read`, resolves token, injects as `KOYEB_TOKEN`. |
| `TC-AUTH-03` | Auth: Missing `.env` | Specified or default `.env` does not exist | Fails closed with clean error; exits code `1`. |
| `TC-AUTH-04` | Auth: Empty Token | `KOYEB_API_KEY=` or whitespace only | Fails closed with clean error; exits code `1`. |
| `TC-AUTH-05` | Auth: Malformed Syntax | Invalid assignment or unterminated quoted value | Rejects `.env` file; fails closed without guessing. |
| `TC-AUTH-06` | Auth: No Expansion | Value containing `$VAR` or `$(cmd)` | Literal string preserved without shell interpolation or command execution. |
| `TC-AUTH-07` | Auth: Failed `op read` | `op read` exits non-zero or fails | Sanitized error returned; raw `stderr`, reference URI, and tokens suppressed. |
| `TC-ARGV-01` | CLI: Argv Preservation | Arguments passed after `--` (`apps list -o json`) | Forwarded verbatim to child process `koyeb` binary in exact order. |
| `TC-ARGV-02` | CLI: Exit Code | Child process exits with code `0`, `1`, or `127` | Launcher exits with the exact same return code. |
| `TC-ARGV-03` | CLI: Custom Env File | `--env-file /custom/path/.env` | Launcher reads from custom path instead of default `./.env`. |
| `TC-ARGV-04` | CLI: Custom Binary | `--koyeb-bin /custom/bin/koyeb` | Launcher invokes specified binary instead of searching `PATH`. |
| `TC-SEC-01` | Security: Token in Argv | Forwarded args contain `--token` or `--token=...` | Terminated immediately with error; child process NOT spawned; exits code `2`. |
| `TC-SEC-02` | Security: Debug Full Flag | Forwarded args contain `--debug-full` | Terminated immediately with error; child process NOT spawned; exits code `2`. |
| `TC-SEC-03` | Security: Custom URL Flag | Forwarded args contain `--url` or `--url=...` | Terminated immediately with error; child process NOT spawned; exits code `2`. |
| `TC-SEC-04` | Security: Ambient Token | Ambient `KOYEB_TOKEN` exists in parent shell | Ambient token overwritten by value resolved from current `.env` file. |
| `TC-SEC-05` | Security: Argv Secret Check | Command line passed to child process inspected | Verified that secret token is never present in child `argv`. |

### 2.2 Request Metrics Reader Test Suite (`tests/test_request_metrics.py` — Verified)

Five standard-library reader tests mocking `urllib.request.urlopen` passed alongside the 12 launcher tests. Read-only smoke checks verified actual null, zero, and positive metric samples through the reader with .env/1Password authentication. No application endpoints were requested by these checks.

| Test ID | Test Category | Target Behavior | Expected Outcome |
| :--- | :--- | :--- | :--- |
| `TC-METRIC-01` | Reader: Parameter Encoding | Query params built from `--service-id`, `--start`, `--end`, `--step 1h` | Exact URL constructed with `name=HTTP_THROUGHPUT`, `step=1h`, and encoded parameters. |
| `TC-METRIC-02` | Reader: Step Forwarding | `--step 5m` | Forwards duration syntax unchanged; the API validates unsupported values. Bare numeric steps were rejected during read-only platform inspection. |
| `TC-METRIC-03` | Reader: Timestamp Validation | Naive vs timezone-aware ISO 8601 strings | Rejects naive timestamps; accepts valid UTC timestamps (e.g. `2026-01-01T00:00:00Z`). |
| `TC-METRIC-04` | Reader: Range Order | Start timestamp occurring after end timestamp | Rejects reversed range with clean error message. |
| `TC-METRIC-05` | Reader: Null Preservation | Upstream JSON fixture contains `null` sample values | Raw JSON output emitted verbatim; asserts `null` values are NOT converted to `0`. |
| `TC-METRIC-06` | Reader: HTTP Error Safety | Upstream server returns HTTP 401 or 500 | Reports HTTP status code only; asserts auth headers and tokens are suppressed. |
| `TC-METRIC-07` | Reader: Auth Resolution | Imports credential functions from `scripts/koyeb_env.py` | Seamlessly resolves literal token or `op://` reference from `.env`. |

---

## 3. Agent Evaluation Scenarios (`evals/evals.json`)

To ensure AI agents understand and adhere to the skill guidelines, 5 evaluation scenarios are defined in `evals/evals.json`:

1. **`eval-inventory-discovery`**: Query services in `example-app` with `-o json` without inventing `--limit` or exposing credentials.
2. **`eval-sleep-configuration`**: Configure 5m Light Sleep, 0 Deep Sleep, and `--min-scale 0` with `--skip-build`.
3. **`eval-deployment-verification`**: Trigger a redeployment using `--skip-build` and verify the deployment reaches `HEALTHY` (distinguishing from `save-only`).
4. **`eval-runtime-secret-attachment`**: Create a secret via stdin and attach it to a service environment using `{{secret.DATABASE_URL}}` interpolation syntax.
5. **`eval-historical-diagnostics`**: Query runtime logs using bounded ISO 8601 UTC timestamps with `--type runtime` (treating `--tail` as a boolean).

---

## 4. Real-World Operational Edge Cases & Failure Modes

The skill instructions specifically guard agents against the following real-world operational anomalies:

### 4.1 Duplicate Service Names Across Applications
- **Condition**: Koyeb allows identical service names within different applications (e.g. `api` inside `app-prod` and `app-staging`).
- **Hazard**: Omitting `--app <app_name>` may query the wrong service or fail unpredictably.
- **Guideline**: Require agents to always explicitly qualify service commands with `--app <app_name>`.

### 4.2 Result Pagination
- **Condition**: Accounts with numerous services or deployment records return paginated lists.
- **Hazard**: Agent falsely concludes a resource does not exist because it was truncated on page 1.
- **Guideline**: Inspect installed command help and response coverage. Use supported query filters such as `--app` and `--name`; do not invent a `--limit` flag for `services list`.

### 4.3 Root Path 404 vs Functional Application
- **Condition**: An API service serves routes at `/api/v1/health` while `/` returns HTTP `404 Not Found`.
- **Hazard**: Agent performs an HTTP GET on `https://example-app.koyeb.app/` and reports the service is broken.
- **Guideline**: Verify health via container state in `koyeb services describe` or query the specific application health path specified in the project runbook.

### 4.4 `save-only` vs Live Deployment
- **Condition**: A service update executed with `--save-only` persists definition changes but does not create an active deployment.
- **Hazard**: Agent claims a change is live in production when it was only saved as a draft.
- **Guideline**: Verify the new deployment becomes active and reaches `HEALTHY`, then probe the intended endpoint.

### 4.5 External Traffic Preventing Sleep
- **Condition**: A service configured with idle sleep fails to enter sleep state.
- **Hazard**: Agent assumes the sleep configuration failed.
- **Guideline**: Verify whether external health check monitors, crawlers, or active websocket connections are continuously resetting the idle timer.

### 4.6 Control-Plane Reads vs Data-Plane Wakeup
- **Condition**: Agent queries `koyeb services describe` or `koyeb instances list` to check if a service is asleep.
- **Hazard**: Agent fears running CLI queries will wake the sleeping instances.
- **Guideline**: Confirm control-plane queries are completely safe and do not wake instances.

---

## 5. Future Live Smoke Testing Protocol (Opt-In Only)

Live smoke tests against real Koyeb accounts are:
- Strictly opt-in and restricted to developer workstations with explicit authorization.
- Read-only (`apps list`, `services list`, `domains list`).
- Never run automatically in CI pipelines.
