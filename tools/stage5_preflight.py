#!/usr/bin/env python3
"""Fail-closed checks for the exact Stage 5 deployment inputs."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.canonical import configuration_hash


HEADER_PREFIX = '# { "Depends": "py-genlayer:'
HEADER_SUFFIX = '" }'


def _without_docstrings(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))

    class Strip(ast.NodeTransformer):
        def _strip(self, node: ast.AST) -> ast.AST:
            body = getattr(node, "body", None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr):
                value = getattr(body[0], "value", None)
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    node.body = body[1:]
            return self.generic_visit(node)

        visit_Module = _strip
        visit_FunctionDef = _strip
        visit_AsyncFunctionDef = _strip
        visit_ClassDef = _strip

    return ast.dump(Strip().visit(tree), include_attributes=False)


def _json_token(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def validate(canonical: Path, artifact: Path, config: dict[str, Any], expected_hash: str | None = None) -> dict[str, Any]:
    canonical_text = canonical.read_text(encoding="utf-8")
    canonical_lines = canonical_text.splitlines()
    artifact_bytes = artifact.read_bytes()
    artifact_text = artifact_bytes.decode("utf-8")
    artifact_lines = artifact_text.splitlines()

    if artifact_bytes.startswith(b"\xef\xbb\xbf"):
        raise SystemExit("FAIL: deployable artifact contains a UTF-8 BOM")
    if b"\r" in artifact_bytes:
        raise SystemExit("FAIL: deployable artifact contains CR line endings")
    if not canonical_lines or not canonical_lines[0].startswith(HEADER_PREFIX) or not canonical_lines[0].endswith(HEADER_SUFFIX):
        raise SystemExit("FAIL: canonical source does not have the exact pinned runner header on line 1")
    if not artifact_lines or artifact_lines[0] != canonical_lines[0] or not artifact_bytes.startswith(b"#"):
        raise SystemExit("FAIL: deployable artifact runner header is not byte 0 and line 1")
    if _without_docstrings(canonical) != _without_docstrings(artifact):
        raise SystemExit("FAIL: canonical/deployable AST parity check failed")

    required = ("query_id", "question", "fact_type", "source_urls", "minimum_supporting_sources",
                "conflict_threshold", "normalization_rules", "allowed_enum_values",
                "require_pinned_evidence")
    missing = [key for key in required if key not in config]
    if missing:
        raise SystemExit(f"FAIL: missing constructor fields: {missing}")
    args = [config[key] for key in required]
    expected_types = (str, str, str, list, int, int, dict, list, bool)
    for index, (value, expected) in enumerate(zip(args, expected_types)):
        if type(value) is not expected:
            raise SystemExit(f"FAIL: constructor arg {index} is {type(value).__name__}, expected {expected.__name__}")
    if not args[3] or not all(type(url) is str and url.startswith("https://") for url in args[3]):
        raise SystemExit("FAIL: source_urls must be a non-empty list of https strings")

    cli_tokens = [args[0], args[1], args[2], _json_token(args[3]), str(args[4]), str(args[5]),
                  _json_token(args[6]), _json_token(args[7]), str(args[8]).lower()]
    parsed_source_urls = json.loads(cli_tokens[3])
    if type(parsed_source_urls) is not list or parsed_source_urls != args[3]:
        raise SystemExit("FAIL: source_urls CLI token does not round-trip as the intended list")
    if expected_hash is not None:
        observed = configuration_hash(config)
        if observed != expected_hash:
            raise SystemExit(f"FAIL: configuration_hash {observed} != expected {expected_hash}")

    return {
        "artifact_bytes": len(artifact_bytes),
        "artifact_sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        "constructor_arg_count": len(args),
        "constructor_types": [type(value).__name__ for value in args],
        "source_urls_count": len(args[3]),
        "cli_args": cli_tokens,
        "configuration_hash": configuration_hash(config),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical", type=Path, default=ROOT / "contracts/source_consensus.py")
    parser.add_argument("--artifact", type=Path, default=ROOT / "artifacts/source_consensus_deployable.py")
    parser.add_argument("--config", type=Path, default=ROOT / "examples/stage5-date-config.json")
    parser.add_argument("--expected-configuration-hash")
    args = parser.parse_args()
    result = validate(args.canonical, args.artifact, json.loads(args.config.read_text(encoding="utf-8")), args.expected_configuration_hash)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
