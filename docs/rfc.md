# RFC: Technical Architecture & Specification for Koyeb Skill

**RFC Identifier**: RFC-20261002-KOYEB-SKILL
**Status**: Implemented; 17 Offline Tests and Read-Only Smoke Checks Verified
**Root Skill**: `skills/koyeb/SKILL.md`
**Launcher Script**: `scripts/koyeb_env.py`
**Metrics Reader**: `scripts/request_metrics.py`

---

## 1. Context & Motivation

Koyeb is a developer-friendly serverless platform providing global deployments, automatic TLS, and dynamic scaling down to zero. The official Koyeb CLI (`koyeb`) is written in Go and exposes commands for all platform resources.

However, when AI agents interact with the CLI directly, four recurring engineering risks emerge:
1. Passing secrets via command-line arguments (e.g. `--token`) creates security vulnerabilities via process listings and execution logs.
2. The official CLI does not automatically parse `.env` files; it relies on environment variables or a configuration file in `~/.koyeb.yaml`.
3. Lack of strict validation allows agents to inadvertently pass destructive flags (e.g. `--debug-full`, which logs full HTTP requests including authentication headers) or redirect API endpoints (`--url`).
4. Native CLI metrics retrieval (`koyeb metrics get`) flattens missing samples (`null`) to `0` and streams unbuffered chained JSON frames without metric name or step filtering, creating false-idle decisions during scale-to-zero evaluations.

This RFC specifies the architecture of a zero-dependency Python launcher (`scripts/koyeb_env.py`), a dedicated lossless request metrics reader (`scripts/request_metrics.py`), and a modular Markdown skill system (`skills/koyeb/`).
Architectural rule: No generic API client; only narrow lossless metric reader exception.

---

## 2. High-Level Architecture

```
+-------------------------------------------------------------------+
|                        AI Agent Context                           |
|       (OpenCode / Claude Code / Cursor / Codex / Engineer)        |
+-------------------------------------------------------------------+
               |                                   |
               | Operational CLI commands          | Read-only request metrics
               v                                   v
+------------------------------------+   +------------------------------------+
|        scripts/koyeb_env.py        |   |    scripts/request_metrics.py      |
| 1. Parse launcher options          |   | 1. Parse --service-id, --start,    |
| 2. Parse .env (strict grammar)     |   |    --end, --step, --env-file       |
| 3. Validate & sanitize argv        |   | 2. Resolve token via koyeb_env     |
| 4. Resolve KOYEB_API_KEY (literal  |   | 3. Send HTTPS GET to:              |
|    or op:// via 1Password CLI)     |   |    /v1/streams/metrics             |
| 5. Inject sanitized KOYEB_TOKEN    |   | 4. Output lossless raw JSON        |
| 6. Execute official koyeb CLI      |   |    (preserves null vs 0 samples)   |
| 7. Propagate exit code & stdio     |   +------------------------------------+
+------------------------------------+                     |
               |                                           |
               v                                           | HTTPS GET
+------------------------------------+                     | (HTTP_THROUGHPUT)
|     Official Koyeb CLI (v5.12.0)   |                     |
+------------------------------------+                     |
               |                                           |
               +--------------------+----------------------+
                                    |
                                    v HTTPS API
                      +---------------------------+
                      |        Koyeb Cloud        |
                      +---------------------------+
```

---

## 3. Launcher Specification (`scripts/koyeb_env.py`)

### 3.1 Invocation Syntax
```bash
python3 scripts/koyeb_env.py [--env-file PATH] [--koyeb-bin PATH] -- <koyeb-cli-args...>
```

- `--env-file PATH`: Optional path to target environment file. Defaults to `./.env` in current working directory.
- `--koyeb-bin PATH`: Optional path to the official `koyeb` binary. Defaults to searching `PATH` via `shutil.which("koyeb")`.
- `--`: Mandatory argument separator separating launcher options from arguments passed directly to the Koyeb CLI.

### 3.2 Argument Validation & Safety Filters
The launcher must inspect all arguments following `--` before process execution:
- **Reject `--token` and `--token=...`**: Prohibits agents from overriding credentials or exposing tokens on the command line.
- **Reject `--debug-full`**: Prohibits enabling Go HTTP dump debugging that logs sensitive authentication headers.
- **Reject `--url` and `--url=...`**: Prevents redirection of API traffic to untrusted endpoints or proxy listeners.

If any prohibited flag is encountered, the launcher must terminate immediately with exit code `2` and an explanatory error message to `stderr`.

### 3.3 `.env` Grammar Subset Specification
The parser must adhere to a deterministic, minimal subset of `.env` parsing:
- **Blank lines & Comments**: Empty lines and lines starting with `#` (ignoring leading whitespace) are ignored.
- **Prefixes**: Optional `export ` prefix is permitted and stripped.
- **Key Syntax**: Must match regex `^[A-Za-z_][A-Za-z0-9_]*$`.
- **Value Syntax**:
  - Unquoted string: `KEY=value` (trimmed of trailing whitespace). Inline comments (`#`) are permitted only if preceded by whitespace.
  - Single-quoted string: `KEY='literal'` (treated verbatim; internal `#` is not a comment).
  - Double-quoted string: `KEY="literal"` (treated verbatim; internal `#` is not a comment).
- **Prohibited Features**:
  - Variable expansion (`$VAR`, `${VAR}`).
  - Command substitution (`$(cmd)`, `` `cmd` ``).
  - Multiline values or escape sequence expansions (`\n`, `\t`).
- **Precedence**: The key parsed from the specified `.env` file is authoritative. Ambient environment variables (such as an existing `KOYEB_TOKEN`) must not override the `.env` value.

### 3.4 Credential Resolution
The launcher searches for `KOYEB_API_KEY`:
1. If value begins with `op://`:
   - Invoke `op read "<reference>"` via `subprocess.run(["op", "read", ref], capture_output=True, text=True)`.
   - If execution fails (non-zero returncode) or `op` is not found, raise a sanitized error:
     ```
     Error: Failed to resolve 1Password credential reference. Verify 1Password CLI authentication.
     ```
   - Raw `stdout`, `stderr`, and reference parameters must not be dumped into unhandled exception tracebacks.
2. If value is a literal string:
   - Use the string directly.
3. If value is empty, whitespace-only, or missing:
   - Fail closed immediately with exit code `1`.

### 3.5 Process Execution & Environment Injection
- **Target Variable**: The official Koyeb CLI utilizes Go's `viper` library:
  ```go
  viper.SetEnvPrefix("koyeb")
  viper.AutomaticEnv()
  ```
  Viper binds the CLI flag `token` to the environment variable `KOYEB_TOKEN`. Therefore, the resolved credential is set as `child_env["KOYEB_TOKEN"] = token`.
- **Sanitization**: Delete any ambient `KOYEB_API_KEY` from `child_env` before launching the process.
- **Subprocess Call**: Direct `subprocess.run([koyeb_bin, *forwarded_args], env=child_env, check=False)`.
- **Stream Preservation**: Standard input, output, and error streams flow through directly without buffering.
- **Exit Code Propagation**: The launcher exits with the exact return code of the child process (`sys.exit(proc.returncode)`).

### 3.6 Lossless Request Metrics Reader Specification (`scripts/request_metrics.py`)
To overcome the lossy zero-flattening behavior in official CLI metrics, this companion reader provides a narrow read-only exception:
- **Invocation**: `python3 scripts/request_metrics.py --service-id ID --start ISO8601 --end ISO8601 [--step 1h] [--env-file ./.env]`
- **Required Arguments**:
  - `--service-id`: The unique Koyeb service identifier (resolved via `services get -o json`).
  - `--start`: Timezone-aware ISO 8601 UTC timestamp.
  - `--end`: Timezone-aware ISO 8601 UTC timestamp.
- **Optional Arguments**:
  - `--step`: Go duration string (e.g. `5m`, `1h`, default `1h`). Bare integers (`300`, `3600`) are rejected by the upstream API.
  - `--env-file`: Target `.env` file (default `./.env`).
- **Credential Resolution**: Imports and reuses credential parsing functions from `scripts/koyeb_env.py` (`KOYEB_API_KEY` literal or `op://` reference).
- **Target Endpoint**: Fixed HTTPS GET to `https://app.koyeb.com/v1/streams/metrics?name=HTTP_THROUGHPUT&service_id=<id>&start=<iso>&end=<iso>&step=<duration>`. The speculative endpoint `/v1/metrics` is prohibited (returns 404).
- **Lossless Output**: Writes successful JSON metrics objects, preserving `null` vs numeric `0` samples, timestamps, and per-series labels such as `code` and `service_id`.
- **Safety & Error Handling**: 30-second timeout; HTTP errors emit sanitized status codes only without echoing authorization headers or tokens; malformed responses produce clean stderr errors.

---

## 4. Official Koyeb CLI v5.12.0 Verified Semantics

Based on verification of official release `v5.12.0`:
1. **Command Structure**:
   - `koyeb apps [list|get|describe|init|create|delete]`
   - `koyeb services [list|get|describe|create|update|redeploy|pause|resume|delete|logs]`
   - `koyeb deployments [list|get|describe]`
   - `koyeb instances [list|get|describe]`
   - `koyeb domains [list|get|describe|create|delete]`
   - `koyeb secrets [list|get|describe|create|update|delete]`
   - `koyeb metrics [get]`
2. **Output Formatting**:
   - Structured JSON is available via `-o json` on resource inspection commands (`apps`, `services`, `deployments`, `instances`, `secrets`, `domains`).
   - Log streaming commands (`koyeb services logs`) output unstructured or stream-delimited logs. Agents must not assume identical JSON envelopes between resource queries and log streams.
3. **Deployment Semantics**:
   - `--skip-build`: Reuses previously built container image from the last successful deployment, skipping rebuild while generating a new deployment record.
   - `--save-only`: Persists configuration changes to the service definition without triggering immediate deployment.
4. **Sleep & Scaling Mechanics**:
   - Separate flags exist for idle timeout: `--light-sleep-delay` and `--deep-sleep-delay`.
   - Setting a timeout to `0` disables that specific sleep stage.
   - Sleep requires autoscaling down to zero (`--min-scale 0`). If minimum scale is $> 0$, the service remains active continuously.
   - **Always-on CLI refusal**: Passing `--light-sleep-delay` or `--deep-sleep-delay` (even `0`) when `--min-scale 1` is explicitly disallowed by the CLI and causes an execution error.
   - **Control-plane calls do not wake instances**: Running `koyeb services describe` or `koyeb instances list` queries the Koyeb control plane without triggering instance wake.
   - **Data-plane traffic wakes instances**: Inbound HTTP requests to the public application URL reset the idle timer and initiate instance wake-up.
   - Verification of sleep state requires inspecting deployment and instance state together with explicit sleep/wake lifecycle logs; a stopped instance alone does not identify the sleep mode.
5. **Metrics Streaming Realities**:
    - Service-scoped `metrics get` queries 9 metrics in sequence; no `--name` or `--step` flags exist in CLI. Instance-scoped queries fetch CPU and memory only.
   - Emits chained JSON objects on stdout under `-o json`.
    - CLI source ([`metrics_get.go`](https://github.com/koyeb/koyeb-cli/blob/v5.12.0/pkg/koyeb/metrics_get.go)) flattens raw `null` samples to `0` via `.GetValue()`, creating lossy metrics that justify the narrow reader exception.

---

## 5. Skill System Design (`skills/koyeb/`)

The skill follows the progressive disclosure pattern to minimize agent token consumption:

```
skills/koyeb/
├── SKILL.md                 # Root skill: core patterns, commands, guardrails (150-250 lines)
└── references/
    ├── auth.md              # Credential resolution, launcher options, 1Password setup
    ├── inspect.md           # Resource discovery, status verification, JSON parsing
    ├── changes.md           # Deployments, env vars, scaling, skip-build, save-only
    ├── sleep.md             # Light/deep sleep configuration, idle timers, wake tests
    ├── metrics.md           # Metrics streaming, JSON frames, null vs. 0 semantics
    └── fleet.md             # Multi-service topologies, batch ops, runbook integration
```

### 5.1 Root Skill (`SKILL.md`)
Serves as the single global entry point. It contains:
- Quick reference table of launcher commands and lossless metrics reader.
- Standard inspection-action-verification loop.
- Core guardrails (never use `--token`, verify deployment status beyond `save-only`).
- Routing pointers to specialized reference files.

### 5.2 Reference Modules
- **`auth.md`**: Explains `.env` formatting, `op://` syntax, launcher flags, and distinction between management tokens and runtime secrets.
- **`inspect.md`**: Guides agents on querying applications, checking deployment states (such as `PENDING`, `STARTING`, `HEALTHY`, and `SLEEPING`), and viewing logs with time bounds.
- **`changes.md`**: Details updating services, mounting Koyeb secrets, using `skip-build`, scaling replicas, and rolling back.
- **`sleep.md`**: Clarifies light vs deep sleep parameters, `--min-scale 0` requirement, and procedures for testing wake-up latency.
- **`metrics.md`**: Documents telemetry collection, native CLI chained JSON frames, lossless reader usage, and 3-state traffic classification.
- **`fleet.md`**: Outlines patterns for inspecting multi-service applications and connecting them to external project runbooks.

---

## 6. Cross-System Boundaries & External Integrations

Koyeb services rarely run in isolation; they often connect to external infrastructure:
- **Managed Databases** (e.g. Neon, Supabase, Cloud SQL): Koyeb services connect via runtime environment variables referencing Koyeb secrets. The skill does not provision or run migrations on external databases.
- **Reverse Proxies & Ingress** (e.g. Cloudflare, NGINX): Koyeb manages custom domains via CNAME records pointing to `koyeb.app`. External DNS modification is deferred to project DNS runbooks.
- **Identity Providers (SSO)** (e.g. Logto, Clerk): Authentication callbacks point to the service URL. Reconfiguration is handled via project-level runbooks.

Agents must output exact Koyeb endpoints and resource identifiers, delegating cross-system modifications to explicit project runbooks.
