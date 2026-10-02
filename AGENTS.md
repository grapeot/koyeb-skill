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
  - Subprocess error handling must explicitly sanitize `stdout` and `stderr`.

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

- **Scaffold Phase**:
  - This repository is currently in the scaffold stage.
  - Only write and maintain scaffold specification files: `README.md`, `AGENTS.md`, `.gitignore`, `.env.example`, `LICENSE`, and documents in `docs/`.
  - Do not create source scripts (`scripts/koyeb_env.py`), test implementations (`tests/`), or skill Markdown files (`skills/`) until explicitly requested in the implementation phase.
