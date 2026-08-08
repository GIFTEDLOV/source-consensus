#!/usr/bin/env python3
"""Fail if any tracked text file under the guarded paths contains a CR byte.

The fixture corpus is served over HTTPS as commit-pinned evidence that validators fetch, and it
is hashed in MANIFEST.sha256. A stray CRLF changes both the hash and the bytes a validator reads,
so line endings are a correctness concern here, not a style one.

`.gitattributes` normalises on checkout; this verifies the normalisation actually held. The two
are not redundant: a file written by a tool after checkout bypasses the attribute entirely.

Usage:  python tools/check_line_endings.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARDED = ("contracts", "docs", "examples", "fixtures", "tools", ".github")
SUFFIXES = {".py", ".md", ".json", ".yml", ".yaml", ".toml", ".txt", ".cfg", ".sha256"}


def main() -> int:
    offenders: list[str] = []
    checked = 0

    for top in GUARDED:
        base = ROOT / top
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in SUFFIXES:
                continue
            checked += 1
            if b"\r" in path.read_bytes():
                offenders.append(str(path.relative_to(ROOT)).replace("\\", "/"))

    if offenders:
        print(f"FAIL -- CR byte found in {len(offenders)} file(s):", file=sys.stderr)
        for o in offenders:
            print(f"  - {o}", file=sys.stderr)
        print("\nFix: ensure .gitattributes is applied, then re-normalise:", file=sys.stderr)
        print("  git add --renormalize . && git commit", file=sys.stderr)
        return 1

    print(f"OK -- {checked} file(s) checked, all LF-only.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
