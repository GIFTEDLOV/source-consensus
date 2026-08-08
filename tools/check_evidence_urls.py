#!/usr/bin/env python3
"""Fetch every pinned fixture source and compare it to the local corpus, byte for byte.

A commit-pinned URL is only worth pinning if it still serves the bytes the expectation was
written against. This catches a rewritten history, a deleted commit, or a corpus file edited
without re-pinning -- three ways the fixtures could quietly stop describing reality.

URLs that are *expected* to 404 (the deliberately-absent sources in the unavailable cases) are
asserted to 404. A dead source that came back to life would change those cases' derivations.

    python tools/check_evidence_urls.py
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "fixtures" / "cases"
_PIN = re.compile(r"^https://raw\.githubusercontent\.com/[^/]+/[^/]+/([0-9a-f]{40})/(.+)$")


def fetch(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


def main() -> int:
    problems: list[str] = []
    checked = expected_404 = 0

    for path in sorted(CASES.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        states = {r["source_index"]: r["state"] for r in case["source_results"]}

        for i, url in enumerate(case["config"]["source_urls"]):
            m = _PIN.match(url)
            if not m:
                problems.append(f"{case['id']} source {i}: not a pinned raw URL: {url}")
                continue
            rel = m.group(2)
            local = ROOT / rel
            status, body = fetch(url)

            # Sources the fixture declares UNAVAILABLE must genuinely be absent.
            if states.get(i) == "UNAVAILABLE":
                expected_404 += 1
                if status == 200:
                    problems.append(
                        f"{case['id']} source {i}: declared UNAVAILABLE but the URL now serves "
                        f"200 -- the fixture's derivation is no longer what a validator would see"
                    )
                elif local.exists():
                    problems.append(
                        f"{case['id']} source {i}: declared UNAVAILABLE but {rel} exists locally"
                    )
                continue

            checked += 1
            if status != 200:
                problems.append(f"{case['id']} source {i}: HTTP {status} for {url}")
                continue
            if not local.exists():
                problems.append(f"{case['id']} source {i}: served 200 but {rel} is missing locally")
                continue
            served = hashlib.sha256(body).hexdigest()
            on_disk = hashlib.sha256(local.read_bytes()).hexdigest()
            if served != on_disk:
                problems.append(
                    f"{case['id']} source {i}: served bytes differ from {rel}\n"
                    f"      served  {served}\n      on disk {on_disk}"
                )

    if problems:
        print(f"FAIL -- {len(problems)} problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(
        f"OK -- {checked} pinned source(s) served 200 and are byte-identical to the local corpus; "
        f"{expected_404} declared-unavailable source(s) correctly absent."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
