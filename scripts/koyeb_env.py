#!/usr/bin/env python3
"""Load a management credential from .env and run the official Koyeb CLI."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


class CredentialError(Exception):
    """A diagnostic that contains no credential values."""


def read_env(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        raise CredentialError("Cannot read the requested .env file.") from None
    values: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise CredentialError(f"Invalid .env assignment on line {number}.")
        if value.startswith(("'", '"')):
            quote = value[0]
            end = value.find(quote, 1)
            if end < 0:
                raise CredentialError(f"Unterminated .env quote on line {number}.")
            tail = value[end + 1 :].strip()
            if tail and not tail.startswith("#"):
                raise CredentialError(f"Unexpected .env content on line {number}.")
            value = value[1:end]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        if key in values:
            raise CredentialError(f"Duplicate .env key on line {number}.")
        values[key] = value
    return values


def resolve_token(value: str) -> str:
    value = value.strip()
    if not value:
        raise CredentialError("KOYEB_API_KEY is missing or empty in .env.")
    if value.startswith("op://"):
        if len(value[5:].split("/")) < 3 or any(not p for p in value[5:].split("/")):
            raise CredentialError("Use a full 1Password vault/item/field reference.")
        try:
            result = subprocess.run(
                ["op", "read", value], capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise CredentialError("Cannot resolve 1Password reference; check op installation and authentication.") from None
        if result.returncode != 0:
            raise CredentialError(f"1Password read failed (exit {result.returncode}); check authentication and field access.")
        value = result.stdout.strip()
    if not value or "\n" in value or "\r" in value or "\x00" in value:
        raise CredentialError("The resolved credential must be a nonempty single-line token.")
    return value


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--koyeb-bin", default="koyeb")
    if argv in (["--help"], ["-h"]):
        parser.print_help()
        return 0
    if "--" not in argv:
        parser.error("Use -- to separate launcher options from Koyeb arguments.")
    separator = argv.index("--")
    options = parser.parse_args(argv[:separator])
    args = argv[separator + 1 :]
    if not args:
        parser.error("Provide a Koyeb command after --.")
    for arg in args:
        if arg.split("=", 1)[0] in {"--token", "--debug-full", "--url"}:
            print("Error: token overrides, full credential debugging, and alternate API URLs are not supported by this launcher.", file=sys.stderr)
            return 2
    try:
        token = resolve_token(read_env(options.env_file).get("KOYEB_API_KEY", ""))
        child_env = os.environ.copy()
        child_env.pop("KOYEB_API_KEY", None)
        child_env["KOYEB_TOKEN"] = token
        child_env["KOYEB_URL"] = "https://app.koyeb.com"
        result = subprocess.run([options.koyeb_bin, *args], env=child_env)
        return result.returncode if result.returncode >= 0 else 128 - result.returncode
    except CredentialError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("Error: Cannot execute the Koyeb CLI; check installation and --koyeb-bin.", file=sys.stderr)
        return 127
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
