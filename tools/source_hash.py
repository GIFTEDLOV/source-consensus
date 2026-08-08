#!/usr/bin/env python3
"""Reproducibility manifest: sha256 over every file that validators fetch or that is deployed.

The fixture corpus is served to validators as commit-pinned evidence. If a corpus file changes
without the manifest and the pinned URLs changing with it, the fixture expectations silently stop
describing what a validator actually reads. This makes that impossible to do by accident.

    python tools/source_hash.py --check    # verify (CI)
    python tools/source_hash.py --write    # regenerate, deliberately
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "MANIFEST.sha256"

# `contracts` and `build` are listed ahead of their existence: from Stage 2 the deployed artifact
# is part of the reproducibility record, and adding the directory later is a change nobody
# reviews. Missing directories are skipped silently, which is what makes that safe.
HASHED_DIRS = ("fixtures/corpus", "contracts", "build")

HEADER = [
    "# SourceConsensus reproducibility manifest",
    "# sha256 over raw bytes. Regenerate with: python tools/source_hash.py --write",
    "# Verified in CI by: python tools/source_hash.py --check",
]


def collect() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for top in HASHED_DIRS:
        base = ROOT / top
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            # Build artefacts are not source. They are gitignored, so hashing them makes the
            # manifest pass locally and fail in CI, where they do not exist.
            if "__pycache__" in path.parts or path.suffix in (".pyc", ".pyo"):
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            rows.append((digest, str(path.relative_to(ROOT)).replace("\\", "/")))
    return sorted(rows, key=lambda r: r[1])


def render(rows: list[tuple[str, str]]) -> str:
    return "\n".join(HEADER + [f"{d}  {p}" for d, p in rows]) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--write", action="store_true")
    args = ap.parse_args()

    rows = collect()
    if not rows:
        print("FAIL -- nothing to hash; expected fixtures/corpus/ to exist", file=sys.stderr)
        return 1

    if args.write:
        MANIFEST.write_text(render(rows), encoding="utf-8", newline="\n")
        print(f"wrote MANIFEST.sha256 -- {len(rows)} file(s)")
        return 0

    if not MANIFEST.exists():
        print("FAIL -- MANIFEST.sha256 is missing", file=sys.stderr)
        return 1

    recorded: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, _, path = line.partition("  ")
        recorded[path] = digest

    actual = {p: d for d, p in rows}
    problems: list[str] = []
    for path, digest in sorted(actual.items()):
        if path not in recorded:
            problems.append(f"not in manifest: {path}")
        elif recorded[path] != digest:
            problems.append(f"changed: {path}\n      recorded {recorded[path]}\n      actual   {digest}")
    for path in sorted(set(recorded) - set(actual)):
        problems.append(f"in manifest but missing on disk: {path}")

    if problems:
        print(f"FAIL -- {len(problems)} manifest problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print("\nIf the change was deliberate: python tools/source_hash.py --write", file=sys.stderr)
        return 1

    print(f"OK -- {len(actual)} file(s) match MANIFEST.sha256")
    return 0


if __name__ == "__main__":
    sys.exit(main())
