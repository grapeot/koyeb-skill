# AGENTS.md - Agent Operating Guidelines

This repository is an English public, Markdown-first Koyeb operations skill (`grapeot/koyeb-skill`). All AI agents contributing to or operating within this repository must adhere strictly to the following instructions.

---

## 1. Operating Principles & Language

- **Language**: English only across all documentation, code, commit messages, and reviews.
- **State Tracking**: Keep [`docs/working.md`](docs/working.md) up to date. Every phase transition, design decision, or notable milestone must be recorded there immediately.
- **Fictional Fixtures & Examples**: All examples, mock responses, tests, documentation, and configuration templates must strictly use fictional identifiers:
  - Applications & Services: `example-app`, `example-service`
  - Hostnames & Domains: `example.com`, `example-app.koyeb.app`
  - Credentials & Keys: `replace-with-your-key`
  - 1Password References: `op://your-vault/your-item/your-field`
  - Do NOT introduce real personal/organizational account IDs, emails, domain names, local home paths, or live tokens.

---

## 2. Python Environment & Development

- **Python Version**: Python 3.10+ standard library. The planned launcher script (`scripts/koyeb_env.py`) must remain pure standard library with zero external runtime dependencies.
- **Virtual Environment**:
  - When setting up local virtual environments for development, testing, or linting tooling, use `uv`:
    ```bash
    # Check for .venv, create if absent
    uv venv
    source .venv/bin/activate
    # Install dependencies with uv pip
    uv pip install <package>
    ```
  - Do not use plain `pip install`.

---

## 3. Testing & Privacy Verification

- **Offline Unit Testing**:
  - All automated unit tests under `tests/` must use Python's built-in `unittest` framework.
  - Subprocess calls (`op`, `koyeb`) must be intercepted with offline stubs/mocks.
  - Tests must never require active internet access, live Koyeb accounts, or real 1Password vaults.
- **Privacy & Leak Audits**:
  - Prior to completing any code change, verify that credentials are never passed via command line arguments (`sys.argv`), logged in plain text, stored in scratch files, or leaked via exception tracebacks.
  - Suppress raw `op` stdout/stderr on resolution failure. Native Koyeb CLI streams are intentionally preserved; do not claim blanket redaction or publish raw secret-reveal output.

---

## 4. Git Safety & Commit Hygiene

- **Specific Authorization Required**:
  - Remote mutation actions (`git push`, creating releases, publishing tags) require explicit user instruction.
  - Never execute `git add -A` or `git add .`. Only stage explicitly created or modified files.
  - Before staging and committing, scan files for private data (secrets, local paths, personal names).
- **Recoverability**:
  - Prefer non-destructive edits or recoverable operations (`trash` over `rm`).

---

## 5. Current Scope Discipline

- **Implementation Phase Authorized**:
  - The implementation phase has been explicitly authorized by the user.
  - Deliverables include authoring the root skill (`skills/koyeb/SKILL.md`), reference guides (`skills/koyeb/references/`), scenario evaluations (`evals/evals.json`), pull request summary (`.agent-pr-body.md`), and updating repository documentation (`README.md`, `docs/`).
  - Do not modify Python source (`scripts/koyeb_env.py`), existing unit tests (`tests/test_koyeb_env.py`), CI workflows, `.gitignore`, or `.env`.
  - Maintain offline boundaries: never execute live Koyeb CLI mutations against production, never read `.env`, and never execute git publish or remote push commands.
   - Keep verification status factual: offline tests and read-only CLI smoke checks passed; scenario prompts remain unbenchmarked unless actually executed.
