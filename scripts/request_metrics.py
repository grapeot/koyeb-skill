#!/usr/bin/env python3
"""Lossless read-only reader for Koyeb HTTP request metrics."""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

from koyeb_env import CredentialError, read_env, resolve_token


def parse_time(value: str) -> datetime.datetime:
    try:
        timestamp = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError
        return timestamp
    except ValueError:
        raise ValueError("Invalid ISO 8601 timestamp: must be timezone-aware (e.g. 2026-01-01T00:00:00Z)") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--step", default="1h")
    args = parser.parse_args(argv)
    try:
        start, end = parse_time(args.start), parse_time(args.end)
        if start >= end:
            raise ValueError("Invalid time range: start timestamp must be before end timestamp")
        if not args.service_id.strip():
            raise ValueError("A valid Koyeb service ID is required (--service-id)")
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    try:
        token = resolve_token(read_env(args.env_file).get("KOYEB_API_KEY", ""))
        query = urllib.parse.urlencode({"name": "HTTP_THROUGHPUT", "service_id": args.service_id,
                                        "start": start.isoformat(), "end": end.isoformat(), "step": args.step})
        request = urllib.request.Request("https://app.koyeb.com/v1/streams/metrics?" + query,
                                         headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read())
        if not isinstance(body, dict) or not isinstance(body.get("metrics"), list):
            raise ValueError
        output = json.dumps(body, ensure_ascii=False, allow_nan=False)
        print(output)
        return 0
    except CredentialError as error:
        print(f"Error: {error}", file=sys.stderr)
    except urllib.error.HTTPError as error:
        print(f"Error: Koyeb metrics stream request failed with HTTP status {error.code}", file=sys.stderr)
    except (urllib.error.URLError, OSError):
        print("Error: Network or transport error while fetching metrics", file=sys.stderr)
    except (ValueError, TypeError):
        print("Error: Malformed or unexpected JSON response structure received from metrics endpoint", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
