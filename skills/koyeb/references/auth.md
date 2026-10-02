# Authentication & Launcher Reference

This reference documents the security architecture, `.env` file parsing grammar, credential resolution mechanisms, and execution boundary implemented by `scripts/koyeb_env.py`.

---

## 1. Authentication Architecture

Koyeb cloud operations require an API token for authentication. To prevent credential leaks in agent traces, shell histories, and system process listings (`ps`), credentials must never be passed via command-line arguments (such as `--token`).

The launcher script (`scripts/koyeb_env.py`) serves as a minimal, standard-library credential adapter. It resolves the management token from an environment file and injects it into the official Koyeb CLI via environment variables:

```
+-----------------------------------------------------------+
| .env File (./.env or --env-file)                          |
| KOYEB_API_KEY=replace-with-your-key                       |
|   or                                                      |
| KOYEB_API_KEY=op://your-vault/your-item/your-field        |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
| scripts/koyeb_env.py                                      |
| 1. Parses strict .env grammar (rejects duplicate keys)    |
| 2. Resolves token (literal or op read via subprocess)     |
| 3. Validates child arguments (rejects prohibited flags)   |
| 4. Sanitizes environment:                                 |
|    - child_env["KOYEB_TOKEN"] = resolved_token            |
|    - child_env["KOYEB_URL"] = "https://app.koyeb.com"     |
|    - child_env.pop("KOYEB_API_KEY")                       |
+-----------------------------------------------------------+
                             |
                             v
+-----------------------------------------------------------+
| Official Koyeb CLI (`koyeb`) Subprocess                   |
| Reads KOYEB_TOKEN natively via Go Viper environment       |
+-----------------------------------------------------------+
```

---

## 2. Launcher Command Syntax

```bash
# Default invocation (looks for ./.env in current working directory)
python3 scripts/koyeb_env.py -- <koyeb-args...>

# Explicit environment file path
python3 scripts/koyeb_env.py --env-file /path/to/.env -- <koyeb-args...>

# Explicit Koyeb binary path
python3 scripts/koyeb_env.py --koyeb-bin /usr/local/bin/koyeb -- <koyeb-args...>

# Combined launcher options
python3 scripts/koyeb_env.py --env-file /path/to/.env --koyeb-bin /usr/local/bin/koyeb -- <koyeb-args...>
```

### Argument Separator (`--`)
The `--` token is mandatory. Arguments preceding `--` are parsed by the Python launcher (`--env-file`, `--koyeb-bin`). Arguments following `--` are validated and forwarded directly to the official Koyeb CLI.

---

## 3. Strict `.env` Grammar & Parser Contract

The launcher implements a deterministic standard-library `.env` parser designed to prevent injection vulnerabilities:

1. **Permitted Syntax**:
   - Optional `export ` prefix (e.g., `export KOYEB_API_KEY="replace-with-your-key"`).
   - Key names matching `^[A-Za-z_][A-Za-z0-9_]*$`.
   - Literal strings enclosed in single quotes (`'`) or double quotes (`"`).
   - Trailing comments preceded by whitespace and `#` on unquoted lines (e.g., `KEY=value # comment`).
2. **Duplicate Key Rejection**:
   - If a key is defined more than once in the file, parsing terminates immediately with exit code `1` and reports the offending line number.
3. **No Shell Expansion or Command Substitution**:
   - Variable expansion (`$VAR`, `${VAR}`) and command evaluation (`$(cmd)`, `` `cmd` ``) are NOT evaluated. The literal characters are preserved as-is.
4. **No Multiline Values**:
   - Multiline strings are not supported. Values must fit on a single line.
5. **Selective Variable Ingestion**:
   - The launcher reads and processes **only** `KOYEB_API_KEY`. Other variables defined in `.env` are deliberately **not** forwarded to the child process environment.

---

## 4. Credential Resolution: Literal vs. 1Password (`op://`)

### Literal Tokens
When `KOYEB_API_KEY` contains a raw string (e.g. `replace-with-your-key`), it is trimmed and validated. Empty or whitespace-only values fail closed immediately.

### 1Password References (`op://`)
When `KOYEB_API_KEY` begins with `op://`:
- The URI format must include vault, item, and field components: `op://your-vault/your-item/your-field`.
- The launcher executes `op read "<reference>"` via subprocess with a **30-second timeout**.
- The launcher does **not** rely on `op run`; it invokes `op read` directly for the single reference.
- **Error Masking**: If `op read` fails or exits non-zero, raw `stdout` and `stderr` are completely suppressed. The launcher outputs a generic message with the exit code (e.g., `Error: 1Password read failed (exit 7)`), preventing credential or URI leakage.
- *Service Account Notice*: If using a 1Password Service Account token (`OP_SERVICE_ACCOUNT_TOKEN`), ensure the account has read access to the target vault. `op read` with full URI paths requires no additional flags.

### No Ambient Credential Fallback
The launcher enforces zero ambient fallback. If `KOYEB_API_KEY` is missing or empty in the `.env` file, the launcher does **not** check the ambient environment for an existing `KOYEB_TOKEN` or `KOYEB_API_KEY`. It exits with code `1`.

---

## 5. Security Guardrails & Prohibited Flags

The launcher inspects all forwarded CLI arguments before process spawning. The following flags are strictly prohibited:

| Prohibited Flag | Rationale | Exit Code |
| :--- | :--- | :--- |
| `--token`, `--token=...` | Prevents exposing management credentials in process arguments (`argv`). | `2` |
| `--debug-full` | Prevents dumping complete HTTP requests including `Authorization` headers. | `2` |
| `--url`, `--url=...` | Prevents redirecting API traffic to untrusted or proxy endpoints. | `2` |

### Process & Security Boundaries
- **No Blanket Redaction of CLI Output**: The launcher does not buffer or filter native CLI `stdout` and `stderr`. Standard output is streamed directly to the terminal. Caution: commands like `koyeb secrets reveal` print secret values to `stdout`; agents must avoid executing reveal commands or logging raw outputs.
- **Local Privileged Process Boundary**: Injected environment variables (`KOYEB_TOKEN`) are visible to local privileged users (root) via `/proc/<pid>/environ` or `ps -E`. This wrapper prevents accidental logging and argv exfiltration, but does not provide hardware-isolated memory protection against root-level local processes.
- **Explicit File Targeting**: The launcher only reads the file explicitly specified by `--env-file` (or default `./.env`). It never scans user home directories or dotfiles for credentials.

---

## 6. Organization & Workspace Selection

When managing infrastructure across multiple organizations or Koyeb workspaces, do not attempt to encode workspace identifiers into `.env` keys. Instead, specify the official CLI flags explicitly after `--`:

```bash
# Explicit organization targeting
python3 scripts/koyeb_env.py -- apps list --organization example-org

# Explicit project targeting
python3 scripts/koyeb_env.py -- apps list --project example-project
```

---

## 7. Exit Code Reference

| Exit Code | Meaning |
| :--- | :--- |
| `0` | Command completed successfully. |
| `1` | Credential error: missing `.env`, empty `KOYEB_API_KEY`, duplicate key, or failed `op read`. |
| `2` | Prohibited flag detected (`--token`, `--debug-full`, `--url`) or launcher argument syntax error. |
| `127` | Koyeb binary not found in system `PATH` or invalid `--koyeb-bin` path. |
| `128 + N` | Child process terminated by signal `N` (e.g. `130` for SIGINT / Ctrl+C). |
| *Other* | Native exit code passed through directly from the official Koyeb CLI. |
