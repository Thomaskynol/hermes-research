#!/usr/bin/env python3
"""Service status for the three local endpoints — read-only probe.

    python service_status.py [--json]

For each service: STOPPED = port closed (nothing listening — the normal
state when the service was never started); BROKEN = port open but the
health endpoint errors; UP = healthy. Stopped is not broken: these
services start on demand, they are not daemons.

Endpoints come from env (RETRIEVER_ENDPOINT, SEARX_URL, EMBEDDING_SERVER_URL)
with the sync_config.py defaults. Never starts anything.
"""

import argparse
import json
import os
import socket
import sys
import urllib.request as u
from urllib.parse import urlparse

DEFAULTS = {
    "vast": (os.environ.get("RETRIEVER_ENDPOINT",
                            "http://127.0.0.1:8001/"), "/health"),
    "searxng": (os.environ.get("SEARX_URL",
                               "http://127.0.0.1:8888/"), "/healthz"),
    "embeddings": (os.environ.get("EMBEDDING_SERVER_URL",
                                  "http://172.17.0.1:8082/v1"), "/models"),
}


def check(name: str, base: str, health_path: str) -> dict:
    parsed = urlparse(base)
    host, port = parsed.hostname or "127.0.0.1", parsed.port or 80
    try:
        socket.create_connection((host, port), timeout=5).close()
    except OSError as exc:
        return {"service": name, "endpoint": base, "status": "STOPPED",
                "detail": f"port {port} closed ({type(exc).__name__})"}
    url = base.rstrip("/") + health_path
    try:
        with u.urlopen(url, timeout=15) as resp:
            code = resp.status
            body = resp.read(400).decode("utf-8", "replace")
    except Exception as exc:
        return {"service": name, "endpoint": base, "status": "BROKEN",
                "detail": f"port open, health check failed: "
                          f"{type(exc).__name__}: {str(exc)[:120]}"}
    if code == 200:
        return {"service": name, "endpoint": base, "status": "UP",
                "detail": f"HTTP 200, {body[:100]}"}
    return {"service": name, "endpoint": base, "status": "BROKEN",
            "detail": f"health returned HTTP {code}"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    results = [check(n, b, p) for n, (b, p) in DEFAULTS.items()]
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"{r['service']:10} {r['status']:8} {r['endpoint']}  {r['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
