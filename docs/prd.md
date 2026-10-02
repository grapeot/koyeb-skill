# Product Requirements Document (PRD): Koyeb Operations Skill

**Repository Identity**: `grapeot/koyeb-skill`
**Root Skill Target**: `skills/koyeb/SKILL.md`
**Status**: Implemented; 17 Offline Tests and Read-Only Smoke Checks Verified
**Date**: 2026-10-02

---

## 1. Executive Summary & Problem Statement

Autonomous AI coding agents (such as OpenCode, Claude Code, Cursor, and Codex) frequently need to manage cloud workloads on [Koyeb](https://www.koyeb.com/). However, unguided agent operations face severe reliability and security failure modes:
1. **Credential Exposure**: Agents often pass sensitive API tokens in command-line arguments (e.g. `--token <secret>`), exposing credentials in process tables (`ps`), shell histories, and execution logs.
2. **Brittle API Duplication**: Writing bespoke Python HTTP clients or SDK wrappers introduces API version drift, incomplete feature sets, and maintenance burdens.
3. **Ambiguous Lifecycle & Sleep Semantics**: Koyeb's dual-tier sleep system (light vs. deep sleep) requires specific configuration constraints (e.g. `--min-scale 0`). Agents often confuse control-plane queries (which do not wake instances) with data-plane HTTP requests (which reset idle timers).
4. **False Positive & Negative Verification**: An agent may assume a deployment succeeded when it was only saved (`save-only`), or believe a service is down when a root path returns `404` while application endpoints function normally.
5. **Boundary Conflation**: Agents often attempt to manage external systems (e.g. cloud SQL databases, DNS records, SSO providers) within a Koyeb context instead of delegating to specific project runbooks.

This project delivers a **public, Markdown-first skill and a minimal standard-library launcher** that empowers AI agents to perform secure, deterministic Koyeb operations using the official Koyeb CLI binary.

---

## 2. Objectives & Goals

- **Environment-Based Credential Injection**: Provide a Python standard-library launcher (`scripts/koyeb_env.py`) that loads `.env` files, resolves literal tokens or 1Password (`op://`) references, and injects them as `KOYEB_TOKEN` into the official CLI environment without printing the resolved management token or adding it to argv.
- **Official CLI Authority**: Use the official Koyeb CLI (`v5.12.0+`) for all cloud interactions. Reject speculative API client reimplementations.
- **Deterministic Outcome Verification**: Establish clear inspection protocols for verifying deployments, scaling changes, service health, and sleep/wake transitions.
- **Progressive Disclosure Skill Design**: Structure instructions into a concise root skill (`skills/koyeb/SKILL.md`, ~150–250 lines) with modular reference guides for auth, inspection, changes, sleep, and fleet operations.
- **Strict Scope Separation**: Maintain a clear separation between public transferable platform mechanisms, local private overlays (credentials, paths), and project-specific runbooks (service sizing, external databases, domains).

---

## 3. Non-Goals

- **No Generic API Client or Server**: We do not implement a generic REST API client, gRPC wrapper, daemon, or web service. An explicit, narrow read-only exception is permitted solely for `scripts/request_metrics.py` to retrieve lossless HTTP request telemetry streams where the official CLI performs lossy zero-flattening.
- **No Global Policy Mandates**: The skill does not enforce global defaults for sleep durations, replica counts, or fleet rollouts. Example configurations (e.g. 5m light / 0 deep sleep) are strictly illustrative.
- **No Direct Cross-System Mutation**: The skill does not directly reconfigure external cloud databases, third-party DNS providers, or SSO identity providers; it outputs verified endpoints and refers to external runbooks.
- **No Third-Party Python Dependencies**: The launcher and reader must not require external pip packages; they must run under standard Python 3.10+.

---

## 4. User Personas

1. **Autonomous AI Agents**: OpenCode, Claude Code, Cursor, and Codex executing infrastructure tasks autonomously within project repositories.
2. **Platform & DevOps Engineers**: Developers seeking a reproducible, secure CLI execution wrapper that integrates seamlessly with 1Password and local `.env` files.

---

## 5. Functional Requirements

### FR-1: Credential Resolution & Environment Injection
- **FR-1.1**: The launcher must parse `.env` files conforming to the specified strict subset (optional `export`, `KEY=value`, literal quotes, whitespace-delimited inline comments; no shell expansions).
- **FR-1.2**: Read `KOYEB_API_KEY`. If it contains an `op://` reference, resolve it via `op read` using standard subprocess execution.
- **FR-1.3**: Inject the resolved credential as `KOYEB_TOKEN` into the child environment.
- **FR-1.4**: Fail closed immediately if `KOYEB_API_KEY` is missing or empty.
- **FR-1.5**: Prohibit dangerous CLI flags: reject `--token`, `--debug-full`, and alternate endpoint `--url` to prevent accidental token override, exfiltration, or diagnostic leaks.
- **FR-1.6**: Omit credential values from launcher diagnostics and suppress failed `op` output. Preserve native CLI output rather than promising blanket redaction.

### FR-2: Resource Inventory & Inspection
- **FR-2.1**: Support structured discovery of applications (`koyeb apps list`), services (`koyeb services list`), deployments (`koyeb deployments list`), instances (`koyeb instances list`), domains (`koyeb domains list`), and secrets (`koyeb secrets list`).
- **FR-2.2**: Support and document JSON output formats (`-o json`) for reliable programmatic assertions.

### FR-3: Diagnostics & Log Retrieval
- **FR-3.1**: Support log streaming and filtered historical queries using `--start-time`, `--end-time`, and `--tail`.
- **FR-3.2**: Provide guidelines for diagnosing deployment failures via deployment status messages and container termination reasons.

### FR-4: Deployment & Lifecycle Management
- **FR-4.1**: Execute image-based updates, git-based rebuilds, and environment variable modifications.
- **FR-4.2**: Support the `skip-build` mechanism when triggering new deployments from previously built images.
- **FR-4.3**: Clearly distinguish between `save-only` updates (which save configurations without triggering a live deployment) and active deployments.

### FR-5: Sleep & Wake Lifecycle Operations
- **FR-5.1**: Support configuring light sleep (rapid-resume state) and deep sleep (resource-suspended state) idle timeouts.
- **FR-5.2**: Explicitly document that sleep features require `--min-scale 0`. Setting an idle timeout to `0` disables that specific sleep stage.
- **FR-5.3**: Enforce lifecycle verification: control-plane CLI calls do not wake services; active data-plane HTTP requests reset idle timers. Verification requires checking instance logs and state transitions.

### FR-6: Application Runtime Secrets
- **FR-6.1**: Clearly distinguish management tokens (`KOYEB_API_KEY`) from application runtime secrets. Application secrets must be managed via Koyeb secret resources (`koyeb secrets`) and mounted to services by reference.

### FR-7: Lossless Request Metrics Telemetry (Narrow Read-Only Exception)
- **FR-7.1**: Provide a dedicated Python standard-library reader (`scripts/request_metrics.py`) that performs a fixed HTTPS GET query to `https://app.koyeb.com/v1/streams/metrics` for request throughput metrics (`name=HTTP_THROUGHPUT`).
- **FR-7.2**: Accept required arguments `--service-id`, `--start`, and `--end` (timezone-aware ISO 8601 UTC), with optional `--step` (Go duration format, default `1h`) and `--env-file` (default `./.env`). Prohibit bare integer steps (`300`) and disallow speculative endpoints (e.g. `/v1/metrics`).
- **FR-7.3**: Preserve raw JSON output retaining `null` vs `0` sample values and per-series status code family labels without performing automatic idle classification or cloud mutations.
- **FR-7.4**: Report HTTP errors with status codes only; suppress sensitive authorization headers, tokens, and raw payloads.

---

## 6. Scope Boundaries & Precedence

| Tier | Responsibility | Location | Example |
| :--- | :--- | :--- | :--- |
| **Tier 1: Public Skill** | Transferable Koyeb CLI commands, verification patterns, launcher specifications | `skills/koyeb/`, `scripts/` | `koyeb services update --min-scale 0` |
| **Tier 2: Private Overlay** | Local paths, 1Password vault pointers, account IDs | Local workspace `.env` | `KOYEB_API_KEY=op://your-vault/your-item/your-field` |
| **Tier 3: Project Runbook** | Service sizing, app topologies, external DB/DNS integration | Project-specific docs | 5m light / 0 deep, external Postgres migration |

### Precedence Rule
When determining configuration values or deployment behavior:
$$\text{Explicit User Task} > \text{Project Runbook / Overlay} > \text{Current Live Configuration}$$

- User authorization for a specific action is sufficient; agents must not pause for repetitive confirmations.

---

## 7. Success Criteria & Verification Metrics

- **Management Credential Handling**: The launcher never adds the management token to child argv or emits it in its own diagnostics. Environment variables remain accessible to privileged local processes. Native CLI output is not a general-purpose secret-redaction layer.
- **Process Fidelity**: 100% preservation of official Koyeb CLI exit codes and stdio streams.
- **Agent Determinism**: AI agents successfully complete inventory, deployment, diagnostic, and sleep checks using the Markdown reference guides without human intervention.
