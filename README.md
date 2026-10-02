# Koyeb Skill (`grapeot/koyeb-skill`)

An English public, Markdown-first skill repository designed to equip autonomous AI agents and engineers with reliable workflows for [Koyeb](https://www.koyeb.com/) serverless infrastructure.

This skill teaches agents reliable cloud inventory discovery, diagnostics, deployment, configuration, sleep/wake lifecycle management, instance scaling, custom domains, and secret operations with authoritative outcome verification.

> **Project Phase: Implemented & Evolving**
> The root skill, six reference guides, credential launcher, and lossless request metrics reader are implemented. All 17 offline tests passed. Read-only smoke checks verified native CLI 5.12.0 operations and preservation of raw metric nulls, zero values, positive values, and labels. Agent evaluation prompts are provided but have not been benchmarked across harnesses.

---

## Architecture & Principles

1. **Official CLI Authority**: Cloud operations are performed using the official [Koyeb CLI](https://github.com/koyeb/koyeb-cli) binary (verified baseline `v5.12.0`). Check installed command help when using other versions. The skill does not implement or maintain a generic Python API client or daemon. An explicit, narrow read-only exception is provided solely for `scripts/request_metrics.py` to retrieve lossless HTTP request telemetry streams where the native CLI performs lossy zero-flattening.
2. **Minimal Standard-Library Launcher**: A lightweight Python launcher (`scripts/koyeb_env.py`) serves as a credential adapter. It parses `.env` files, resolves credentials, and delegates directly to the official CLI via standard subprocess execution without external dependencies.
3. **Markdown-First Agent Guidance**: Operational intelligence resides in structured Markdown instructions under `skills/koyeb/`, employing progressive disclosure to keep agent context windows focused.
4. **Strict Scope Separation**:
   - **Public Skill**: Transferable platform mechanisms, CLI invocation patterns, output parsing, and verification checks.
   - **Private Overlay**: Account credentials, 1Password vault references, and local environment paths.
   - **Project Runbooks**: App-specific sizing, sleep policies, custom domains, and external service ties (e.g., databases, reverse proxies, SSO).

---

## Prerequisites

- **Python**: Python 3.10 or newer (standard library only; zero external package dependencies).
- **Koyeb CLI**: Official [Koyeb CLI](https://github.com/koyeb/koyeb-cli) `v5.12.0` or higher installed in system `PATH` (or specified via `--koyeb-bin`) for operational commands. Note: the narrow lossless request metrics reader (`scripts/request_metrics.py`) uses standard Python library only and does not require the `koyeb` binary. See [Koyeb CLI Installation](https://www.koyeb.com/docs/build-and-deploy/cli/installation).
- **1Password CLI (Optional)**: `op` CLI installed and authenticated only if using `op://` credential references in `.env`.

---

## Installation for AI Agents

To install this skill into an agent-enabled workspace (e.g., OpenCode, Claude Code, Cursor, Codex):

1. **Provide the repository URL to your agent**:
   > "Please install the Koyeb skill from https://github.com/grapeot/koyeb-skill"
2. **Agent Setup Steps**:
   - Clones or references this repository into your workspace.
   - Inspects your workspace routing guide (e.g., `AGENTS.md`, `CLAUDE.md`, or `WORKSPACE.md`).
   - Adds **exactly one** root pointer to `skills/koyeb/SKILL.md` in your skills index or agent prompt.
   - Keeps your local overlay (credentials and account configuration) separate in `.env`.

### Skill Entry Points
- **Root Skill**: [`skills/koyeb/SKILL.md`](skills/koyeb/SKILL.md)
- **Reference Guides**:
  - [`skills/koyeb/references/auth.md`](skills/koyeb/references/auth.md) — Authentication, launcher options, and credential isolation.
  - [`skills/koyeb/references/inspect.md`](skills/koyeb/references/inspect.md) — Inventory queries, status checking, logs, and JSON parsing.
  - [`skills/koyeb/references/changes.md`](skills/koyeb/references/changes.md) — Deployments, environment variables, `skip-build`, and scaling.
  - [`skills/koyeb/references/sleep.md`](skills/koyeb/references/sleep.md) — Light and deep sleep configurations, idle timeouts, and wake tests.
  - [`skills/koyeb/references/metrics.md`](skills/koyeb/references/metrics.md) — Telemetry streaming, null vs. 0 semantics, and traffic diagnostics.
  - [`skills/koyeb/references/fleet.md`](skills/koyeb/references/fleet.md) — Multi-service orchestration and external runbook integration.

---

## Launcher Usage & Credential Resolution

The launcher loads the management credential from `.env` and passes it through the child environment rather than command arguments. Native CLI output is unchanged; it is not a general-purpose secret-redaction layer:

```bash
# Display help via the launcher
python3 scripts/koyeb_env.py -- --help

# List applications using default ./.env
python3 scripts/koyeb_env.py -- apps list -o json

# Query services within an application
python3 scripts/koyeb_env.py -- services list --app example-app -o json

# Inspect service details with an explicit environment file
python3 scripts/koyeb_env.py --env-file /path/to/.env -- services describe example-app/example-service -o json

# Stream service logs (--tail is a boolean flag)
python3 scripts/koyeb_env.py -- services logs example-service --app example-app --tail

# Explore native metrics (multiple JSON frames; null samples become 0)
python3 scripts/koyeb_env.py -- metrics get --service example-app/example-service \
  --start 2026-01-01T00:00:00Z --end 2026-01-02T00:00:00Z -o json

# Keep nulls and labels when auditing request activity (use a resolved service ID)
python3 scripts/request_metrics.py --service-id example-service-id \
  --start 2026-01-01T00:00:00Z --end 2026-01-02T00:00:00Z --step 1h
```

### Supported `.env` Formats

The launcher consumes `KOYEB_API_KEY` from your local `.env`:

```bash
# Option A: Literal API token
KOYEB_API_KEY=replace-with-your-key

# Option B: 1Password vault reference (resolved via `op read`)
KOYEB_API_KEY=op://your-vault/your-item/your-field
```

- **Credential Isolation**: Tokens are injected directly as `KOYEB_TOKEN` into the child process environment. Dangerous flags (`--token`, `--debug-full`, `--url`) are blocked with exit code `2`.
- **Targeting Workspaces**: Pass `--organization <org>` or `--project <proj>` directly after `--` when managing multi-tenant accounts.

---

## Documentation Links

- [Official Koyeb Documentation](https://www.koyeb.com/docs)
- [Official Koyeb CLI Repository](https://github.com/koyeb/koyeb-cli)
- [Product Requirements Document (PRD)](docs/prd.md) — Problem statement, requirements, and scope boundaries.
- [Technical Architecture RFC](docs/rfc.md) — Launcher specifications, parser grammar, security model, and CLI semantics.
- [Test Strategy & Plan](docs/test.md) — Offline unit testing, subprocess stubs, and scenario evaluations.
- [Working Log & State Tracker](docs/working.md) — Milestones, task checklist, and project history.

---

## License

[MIT License](LICENSE) &copy; 2026 grapeot.
