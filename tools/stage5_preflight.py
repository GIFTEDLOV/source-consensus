#!/usr/bin/env python3
"""Fail-closed checks for the exact Stage 5 deployment inputs."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.canonical import configuration_hash


HEADER_PREFIX = '# { "Depends": "py-genlayer:'
HEADER_SUFFIX = '" }'
EXPECTED_HASH_PATTERN = re.compile(r"^0x[0-9a-f]{64}$")
FACT_TYPES = {"STRING", "INTEGER", "BOOLEAN", "DATE", "ENUM"}
CASE_POLICIES = {"PRESERVE", "LOWER"}
MIN_SOURCES = 2
MAX_SOURCES = 5
MAX_QUERY_ID_LEN = 64
MAX_QUESTION_LEN = 300
MAX_URL_LEN = 400
MAX_ENUM_VALUES = 16
MAX_ENUM_VALUE_LEN = 64
MIN_SUPPORT_FLOOR = 2
MAX_CONFLICT_THRESHOLD = 5
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _normalise_text(value: str) -> str:
    out = value.replace("\r\n", "\n").replace("\r", "\n")
    out = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", out)
    return re.sub(r"\s+", " ", out).strip()


def _require_len(field: str, value: Any, limit: int) -> str:
    if type(value) is not str:
        raise SystemExit(f"FAIL: {field} must be a string")
    out = _normalise_text(value)
    if not out:
        raise SystemExit(f"FAIL: {field} must not be empty")
    if len(out) > limit:
        raise SystemExit(f"FAIL: {field} exceeds {limit} characters")
    return out


def _strict_int(field: str, value: Any) -> int:
    if type(value) is not int:
        raise SystemExit(f"FAIL: {field} must be an integer")
    return value


def _is_pinned(url: str) -> bool:
    if url.startswith("https://raw.githubusercontent.com/"):
        parts = url[len("https://raw.githubusercontent.com/") :].split("/")
        if len(parts) >= 4 and HEX40.fullmatch(parts[2]):
            return True
    if url.startswith("https://github.com/"):
        parts = url[len("https://github.com/") :].split("/")
        if len(parts) >= 5 and parts[2] in ("blob", "raw") and HEX40.fullmatch(parts[3]):
            return True
    if url.startswith("https://arweave.net/"):
        ident = url[len("https://arweave.net/") :].split("/")[0].split("?")[0]
        if len(ident) == 43 and re.fullmatch(r"[A-Za-z0-9_-]{43}", ident):
            return True
    return bool(
        re.match(r"^https://[^/]+/ipfs/[A-Za-z0-9]{46,}", url)
        or re.match(r"^https://[A-Za-z0-9]{46,}\.ipfs\.[^/]+/", url)
    )


def _validate_url(index: int, value: Any) -> str:
    url = _require_len(f"source_urls[{index}]", value, MAX_URL_LEN)
    if not url.startswith("https://"):
        raise SystemExit(f"FAIL: source_urls[{index}] must use https://")
    if any(char.isspace() for char in url):
        raise SystemExit(f"FAIL: source_urls[{index}] contains whitespace")
    authority = url[len("https://") :].split("/")[0]
    if not authority:
        raise SystemExit(f"FAIL: source_urls[{index}] has an empty host")
    if "@" in authority:
        raise SystemExit(f"FAIL: source_urls[{index}] embeds credentials")
    return url


def _validate_constructor_invariants(config: dict[str, Any]) -> list[Any]:
    required = ("query_id", "question", "fact_type", "source_urls", "minimum_supporting_sources",
                "conflict_threshold", "normalization_rules", "allowed_enum_values",
                "require_pinned_evidence")
    missing = [key for key in required if key not in config]
    if missing:
        raise SystemExit(f"FAIL: missing constructor fields: {missing}")

    query_id = _require_len("query_id", config["query_id"], MAX_QUERY_ID_LEN)
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", query_id):
        raise SystemExit("FAIL: query_id does not match the constructor identifier rule")
    _require_len("question", config["question"], MAX_QUESTION_LEN)
    fact_type = config["fact_type"]
    if type(fact_type) is not str or fact_type not in FACT_TYPES:
        raise SystemExit(f"FAIL: fact_type must be one of {sorted(FACT_TYPES)}")

    source_urls = config["source_urls"]
    if type(source_urls) is not list:
        raise SystemExit("FAIL: source_urls must be a list")
    if not MIN_SOURCES <= len(source_urls) <= MAX_SOURCES:
        raise SystemExit(f"FAIL: source_urls count must be between {MIN_SOURCES} and {MAX_SOURCES}")
    clean_urls = []
    for index, raw_url in enumerate(source_urls):
        url = _validate_url(index, raw_url)
        if url in clean_urls:
            raise SystemExit(f"FAIL: duplicate source url at index {index}")
        clean_urls.append(url)
    pinned = config["require_pinned_evidence"]
    if type(pinned) is not bool:
        raise SystemExit("FAIL: require_pinned_evidence must be boolean")
    if pinned and not all(_is_pinned(url) for url in clean_urls):
        raise SystemExit("FAIL: every source URL must be commit/content pinned")

    min_support = _strict_int("minimum_supporting_sources", config["minimum_supporting_sources"])
    if min_support < MIN_SUPPORT_FLOOR or min_support > len(clean_urls):
        raise SystemExit("FAIL: minimum_supporting_sources violates constructor bounds")
    conflict_threshold = _strict_int("conflict_threshold", config["conflict_threshold"])
    if not 1 <= conflict_threshold <= MAX_CONFLICT_THRESHOLD or conflict_threshold > len(clean_urls):
        raise SystemExit("FAIL: conflict_threshold violates constructor bounds")

    rules = config["normalization_rules"]
    if type(rules) is not dict:
        raise SystemExit("FAIL: normalization_rules must be an object")
    unknown = set(rules) - {"case_policy", "min_value", "max_value"}
    if unknown:
        raise SystemExit(f"FAIL: unknown normalization rules: {sorted(unknown)}")
    case_policy = rules.get("case_policy", "PRESERVE")
    if type(case_policy) is not str or case_policy not in CASE_POLICIES:
        raise SystemExit("FAIL: invalid case_policy")
    if case_policy == "LOWER" and fact_type not in {"STRING", "ENUM"}:
        raise SystemExit("FAIL: LOWER case_policy applies only to STRING and ENUM")
    has_min = "min_value" in rules
    has_max = "max_value" in rules
    if (has_min or has_max) and fact_type != "INTEGER":
        raise SystemExit("FAIL: min_value/max_value apply only to INTEGER")
    low = _strict_int("normalization_rules.min_value", rules["min_value"]) if has_min else 0
    high = _strict_int("normalization_rules.max_value", rules["max_value"]) if has_max else 0
    if has_min and has_max and low > high:
        raise SystemExit("FAIL: min_value exceeds max_value")

    enum_values = config["allowed_enum_values"]
    if type(enum_values) is not list:
        raise SystemExit("FAIL: allowed_enum_values must be a list")
    if fact_type == "ENUM":
        if not 2 <= len(enum_values) <= MAX_ENUM_VALUES:
            raise SystemExit("FAIL: ENUM requires 2 to 16 allowed values")
        seen = set()
        for index, raw_value in enumerate(enum_values):
            value = _require_len(f"allowed_enum_values[{index}]", raw_value, MAX_ENUM_VALUE_LEN)
            comparable = value.lower() if case_policy == "LOWER" else value
            if comparable in seen:
                raise SystemExit("FAIL: duplicate allowed_enum_value after normalization")
            seen.add(comparable)
    elif enum_values:
        raise SystemExit("FAIL: allowed_enum_values is only valid for ENUM")

    return [query_id, _normalise_text(config["question"]), fact_type, clean_urls,
            min_support, conflict_threshold, rules, enum_values, pinned]


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
    if not isinstance(expected_hash, str) or not EXPECTED_HASH_PATTERN.fullmatch(expected_hash):
        raise SystemExit("FAIL: --expected-configuration-hash is required and must be a 0x-prefixed 32-byte hash")
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

    args = _validate_constructor_invariants(config)
    expected_types = (str, str, str, list, int, int, dict, list, bool)
    for index, (value, expected) in enumerate(zip(args, expected_types)):
        if type(value) is not expected:
            raise SystemExit(f"FAIL: constructor arg {index} is {type(value).__name__}, expected {expected.__name__}")
    cli_tokens = [args[0], args[1], args[2], _json_token(args[3]), str(args[4]), str(args[5]),
                  _json_token(args[6]), _json_token(args[7]), str(args[8]).lower()]
    parsed_source_urls = json.loads(cli_tokens[3])
    if type(parsed_source_urls) is not list or parsed_source_urls != args[3]:
        raise SystemExit("FAIL: source_urls CLI token does not round-trip as the intended list")
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
    parser.add_argument("--expected-configuration-hash", required=True)
    args = parser.parse_args()
    result = validate(args.canonical, args.artifact, json.loads(args.config.read_text(encoding="utf-8")), args.expected_configuration_hash)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
