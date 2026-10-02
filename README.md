# Koyeb Skill (`grapeot/koyeb-skill`)

An English public, Markdown-first skill repository designed to equip autonomous AI agents and engineers with reliable workflows for [Koyeb](https://www.koyeb.com/) serverless infrastructure.

This skill teaches agents reliable cloud inventory discovery, diagnostics, deployment, configuration, sleep/wake lifecycle management, instance scaling, custom domains, and secret operations with authoritative outcome verification.

> **Project Phase: Scaffold**
> This repository is currently in its scaffold definition phase. Architecture specifications, test plans, and documentation contracts are defined. The launcher script (`scripts/koyeb_env.py`), unit tests, and root skill (`skills/koyeb/SKILL.md`) are planned and pending implementation.

---

## Architecture & Principles

1. **Official CLI Authority**: Cloud operations are performed using the official Koyeb CLI binary (`v5.12.0+`). The skill does not implement or maintain a speculative Python API client or daemon.
2. **Minimal Standard-Library Launcher**: A lightweight Python launcher (`scripts/koyeb_env.py`, planned) parses `.env` files, resolves credentials, and delegates directly to the official CLI via standard subprocess execution.
3. **Markdown-First Agent Guidance**: Operational intelligence resides in structured Markdown instructions under `skills/koyeb/`, employing progressive disclosure to keep agent context windows focused.
4. **Strict Scope Separation**:
   - **Public Skill**: Transferable platform mechanisms, CLI invocation patterns, output parsing, and verification checks.
   - **Private Overlay**: Account credentials, 1Password vault references, and local environment paths.
   - **Project Runbooks**: App-specific sizing, sleep policies, custom domains, and external service ties (e.g., databases, reverse proxies, SSO).

---

## Prerequisites

- **Python**: Python 3.10 or newer (standard library only; no external package dependencies for the launcher).
- **Koyeb CLI**: Official [Koyeb CLI](https://github.com/koyeb/koyeb-cli) `v5.12.0` or higher installed in system `PATH` (or specified via `--koyeb-bin`).
- **1Password CLI (Optional)**: `op` CLI installed and authenticated only if using `op://` credential references in `.env`.

---

## Planned Usage

The planned launcher transparently loads configuration and runs the Koyeb CLI without exposing secrets in process arguments or logs:

```bash
# Display help via the launcher
python3 scripts/koyeb_env.py -- --help

# List applications using default ./.env
python3 scripts/koyeb_env.py -- apps list

# Query services within an application
python3 scripts/koyeb_env.py -- services list --app example-app

# Inspect service details with an explicit environment file
python3 scripts/koyeb_env.py --env-file /path/to/.env -- services describe example-service --app example-app

# Stream service logs
python3 scripts/koyeb_env.py -- services logs example-service --app example-app --tail
```

### Credential Resolution Contract

The launcher reads `KOYEB_API_KEY` from the target `.env` file:
- **Literal Token**: Injected directly as `KOYEB_TOKEN` into the child CLI process environment.
- **1Password Reference (`op://`)**: Resolved securely via `op read "op://your-vault/your-item/your-field"` prior to child execution.
- **Security Boundary**: The CLI process arguments never contain credentials (`--token` flag is explicitly prohibited). Errors sanitize outputs and suppress raw subprocess tokens.

---

## Agent Installation

To install this skill into an agent-enabled workspace (e.g., OpenCode, Claude Code, Cursor, Codex):

1. Provide the repository URL to your agent:
   > "Please install the Koyeb skill from https://github.com/grapeot/koyeb-skill"
2. The agent installer:
   - Clones or references this repository into your workspace.
   - Inspects your workspace routing guide (e.g., `AGENTS.md`, `CLAUDE.md`, or `WORKSPACE.md`).
   - Adds **exactly one** root pointer to `skills/koyeb/SKILL.md` in your skills index or agent prompt.

### Planned Root Skill Path
- Root Skill: [`skills/koyeb/SKILL.md`](skills/koyeb/SKILL.md)
- Reference Guides:
  - `skills/koyeb/references/auth.md` — Authentication, launcher options, and credential isolation.
  - `skills/koyeb/references/inspect.md` — Inventory queries, status checking, logs, and JSON parsing.
  - `skills/koyeb/references/changes.md` — Deployments, environment variables, `skip-build`, and scaling.
  - `skills/koyeb/references/sleep.md` — Light and deep sleep configurations, idle timeouts, and wake tests.
  - `skills/koyeb/references/fleet.md` — Multi-service orchestration and external runbook integration.

---

## Repository Documentation

- [Product Requirements Document (PRD)](docs/prd.md) — Problem statement, functional requirements, and scope boundaries.
- [Technical Architecture RFC](docs/rfc.md) — Launcher specifications, parser grammar, security model, and Koyeb CLI semantics.
- [Test Strategy & Plan](docs/test.md) — Offline unit testing, subprocess stubs, privacy audits, and scenario evaluations.
- [Working Log & State Tracker](docs/working.md) — Project milestones, task checklist, and historical changelog.

---

## License

[MIT License](LICENSE) &copy; 2026 grapeot.
