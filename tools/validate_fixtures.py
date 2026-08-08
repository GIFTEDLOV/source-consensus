#!/usr/bin/env python3
"""Validate every fixture case. Four checks, all fatal.

1. **Schema** -- each `fixtures/cases/*.json` validates against `fixtures/schema/fixture.schema.json`.
2. **Structural consistency** -- source indices are dense and match the configured URL count;
   `VALUE` results carry a value that normalises under the declared `fact_type`; non-`VALUE`
   results carry no value.
3. **Derivation** -- the declared `expected` is exactly what `tools/canonical.py` computes from
   the declared per-source results. This makes the fixture corpus an executable check on the
   status-derivation rules *before any contract exists*, which is the whole reason it is written
   at Stage 1.
4. **URL policy** -- every source URL is `https://`, within 400 characters, and commit-pinned to
   a 40-hex sha. An unpinned fixture source fails the build, because a validator that fetches it
   later would not necessarily read the bytes the expectation was written against.

    python tools/validate_fixtures.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.canonical import (  # noqa: E402
    STATE_VALUE,
    configuration_hash,
    derive_status,
    normalise_value,
)

CASES = ROOT / "fixtures" / "cases"
SCHEMA = ROOT / "fixtures" / "schema" / "fixture.schema.json"

_PINNED = re.compile(
    r"^https://raw\.githubusercontent\.com/[^/]+/[^/]+/[0-9a-f]{40}/"
)


def main() -> int:
    try:
        import jsonschema
    except ImportError:
        print("FAIL -- jsonschema is required:  pip install jsonschema==4.23.0", file=sys.stderr)
        return 1

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    files = sorted(CASES.glob("*.json"))
    if not files:
        print("FAIL -- no fixture cases found", file=sys.stderr)
        return 1

    errors: list[str] = []
    categories: set[str] = set()
    statuses: set[str] = set()

    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        case = json.loads(path.read_text(encoding="utf-8"))

        # 1. Schema
        schema_errors = sorted(validator.iter_errors(case), key=lambda e: list(e.path))
        if schema_errors:
            for e in schema_errors:
                loc = "/".join(str(p) for p in e.path) or "(root)"
                errors.append(f"{rel}: schema: {loc}: {e.message}")
            continue

        if case["id"] != path.stem:
            errors.append(f"{rel}: id {case['id']!r} does not match filename")

        cfg = case["config"]
        n_sources = len(cfg["source_urls"])
        categories.add(case["category"])
        statuses.add(case["expected"]["status"])

        # 2. Structural consistency
        indices = [r["source_index"] for r in case["source_results"]]
        if sorted(indices) != list(range(n_sources)):
            errors.append(
                f"{rel}: source_results must cover indices 0..{n_sources - 1} exactly once "
                f"(got {sorted(indices)})"
            )
        for r in case["source_results"]:
            if r["state"] == STATE_VALUE:
                if r["value"] is None:
                    errors.append(f"{rel}: source {r['source_index']} is VALUE with no value")
                    continue
                norm = normalise_value(cfg["fact_type"], r["value"], {
                    **cfg["normalization_rules"],
                    "allowed_enum_values": cfg["allowed_enum_values"],
                })
                if norm is None:
                    errors.append(
                        f"{rel}: source {r['source_index']} value {r['value']!r} does not "
                        f"normalise under fact_type {cfg['fact_type']}"
                    )
                elif norm != r["value"]:
                    errors.append(
                        f"{rel}: source {r['source_index']} value {r['value']!r} is not already "
                        f"canonical (normalises to {norm!r}); fixtures record canonical values"
                    )
            elif r["value"] is not None:
                errors.append(
                    f"{rel}: source {r['source_index']} is {r['state']} but carries a value"
                )

        if cfg["fact_type"] == "ENUM" and not cfg["allowed_enum_values"]:
            errors.append(f"{rel}: fact_type ENUM requires allowed_enum_values")
        if cfg["fact_type"] != "ENUM" and cfg["allowed_enum_values"]:
            errors.append(f"{rel}: allowed_enum_values is only meaningful for fact_type ENUM")
        if cfg["minimum_supporting_sources"] > n_sources:
            errors.append(
                f"{rel}: minimum_supporting_sources {cfg['minimum_supporting_sources']} exceeds "
                f"the {n_sources} configured sources -- unsatisfiable by construction"
            )

        # 3. Derivation -- the declared expectation must be DERIVED, not asserted
        got = derive_status(
            case["source_results"],
            cfg["minimum_supporting_sources"],
            cfg["conflict_threshold"],
            n_sources,
        )
        want = case["expected"]
        if got["status"] != want["status"]:
            errors.append(
                f"{rel}: expected status {want['status']} but the rules derive {got['status']}"
            )
        if got["normalized_value"] != want["normalized_value"]:
            errors.append(
                f"{rel}: expected value {want['normalized_value']!r} but the rules derive "
                f"{got['normalized_value']!r}"
            )

        # 4. URL policy
        for i, u in enumerate(cfg["source_urls"]):
            if not u.startswith("https://"):
                errors.append(f"{rel}: source {i} is not https")
            if len(u) > 400:
                errors.append(f"{rel}: source {i} exceeds 400 characters")
            if not _PINNED.match(u):
                errors.append(f"{rel}: source {i} is not commit-pinned to a 40-hex sha: {u}")

        # Configuration hash must be computable from the declared config.
        try:
            configuration_hash(cfg)
        except SystemExit as exc:
            errors.append(f"{rel}: configuration_hash unavailable: {exc}")

    if errors:
        print(f"FAIL -- {len(errors)} problem(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(
        f"OK -- {len(files)} fixture case(s), {len(categories)} categories, "
        f"{len(statuses)} of 4 statuses exercised, all schema-valid, "
        "derivations recomputed, and commit-pinned."
    )
    missing = {"CONFIRMED", "CONFLICTED", "INSUFFICIENT_EVIDENCE", "UNAVAILABLE"} - statuses
    if missing:
        print(f"   note: no fixture yet exercises {', '.join(sorted(missing))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
