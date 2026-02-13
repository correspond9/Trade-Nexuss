#!/usr/bin/env python3
"""
Simple container health-check script that uses Python stdlib (no extra deps).
Usage: `python tools/container_health_check.py [base_url]`
If `HEALTH_URL` env var is set it will be used as base URL.
"""
import sys
import os
import urllib.request


def check(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            print(f"OK {url} -> {r.status}")
            return 0
    except Exception as e:
        print(f"ERR {url} -> {e}", file=sys.stderr)
        return 1


def main():
    base = os.getenv("HEALTH_URL") or (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000")
    targets = [f"{base.rstrip('/')}/health"]
    # Add an optional API read endpoint if needed
    if os.getenv("HEALTH_API_ENDPOINT"):
        targets.append(f"{base.rstrip('/')}/{os.getenv('HEALTH_API_ENDPOINT').lstrip('/')}")

    rc = 0
    for t in targets:
        rc |= check(t)
    sys.exit(rc)


if __name__ == '__main__':
    main()
