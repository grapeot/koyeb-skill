# Test Strategy & Quality Assurance Plan

**Project**: Koyeb Skill (`grapeot/koyeb-skill`)
**Status**: Scaffold Contract
**Target Test Suite**: `tests/test_koyeb_env.py`
**Planned Evals**: `evals/evals.json`

---

## 1. Testing Philosophy & Guardrails

1. **Strict Offline Unit Testing**:
   - Automated unit tests must run offline without internet connectivity.
   - External CLI tools (`koyeb`, `op`) must be intercepted with deterministic stubs or standard library mocks (`unittest.mock`).
   - No automated tests may create, mutate, or delete live cloud infrastructure.
2. **Zero Secret Leakage Verification**:
   - Every test case involving credentials must assert that secrets do not appear in command line arguments, process listings, log outputs, or error tracebacks.
3. **Exit Code & Stream Preservation**:
   - Tests must assert that child process return codes and stdio streams pass through unaltered.

---

## 2. Unit Test Matrix (`tests/test_koyeb_env.py`)

The planned unit test suite will use Python's built-in `unittest` framework to validate `scripts/koyeb_env.py`.

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

---

## 3. Agent Evaluation Scenarios (`evals/evals.json`)

To ensure AI agents understand and adhere to the skill guidelines, an evals test harness will evaluate agent performance across standard prompts:

```json
[
  {
    "id": "eval-inventory-discovery",
    "prompt": "List all active Koyeb services in the example-app application and report their status.",
    "expected_tool": "python3 scripts/koyeb_env.py -- services list --app example-app -o json",
    "assertions": [
      "agent_uses_launcher",
      "agent_does_not_pass_token_flag",
      "agent_parses_json_output"
    ]
  },
  {
    "id": "eval-sleep-configuration",
    "prompt": "Configure example-app/example-service to enter Light Sleep after five idle minutes and disable Deep Sleep.",
    "expected_tool": "python3 scripts/koyeb_env.py -- services update example-service --app example-app --light-sleep-delay 5m --deep-sleep-delay 0 --min-scale 0",
    "assertions": [
      "agent_includes_min_scale_zero",
      "agent_distinguishes_light_and_deep_sleep",
      "agent_verifies_update_result"
    ]
  },
  {
    "id": "eval-deployment-verification",
    "prompt": "Trigger a redeploy of example-service using the previous build and verify it is live.",
    "expected_tool": "python3 scripts/koyeb_env.py -- services redeploy example-service --app example-app --skip-build",
    "assertions": [
      "agent_uses_skip_build",
      "agent_polls_deployment_status_until_running",
      "agent_does_not_stop_at_save_only"
    ]
  }
]
```

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
