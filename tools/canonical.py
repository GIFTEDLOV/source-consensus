#!/usr/bin/env python3
"""Standalone reference implementation of the SourceConsensus canonical rules.

This module is deliberately NOT imported by the contract. When the contract exists it will be a
single deployable file carrying its own copy of this logic; this is an independent second
implementation written from `docs/ARCHITECTURE.md`, and the test suite will assert the two agree.
If they ever diverge, one of them is wrong and the tests say so.

It also lets an integrator compute an expected `configuration_hash` off-chain -- before deploying
anything -- so the value pinned in a consuming contract can be reviewed by both parties at
agreement time rather than read back from a deployment they have to trust.

Three things live here, and they are the three things that must be deterministic:

    normalise_value(fact_type, raw, rules)   surface form  -> canonical value, or None
    derive_status(source_results, config)    per-source values -> status + index sets
    configuration_hash(config)               immutable config -> 0x-prefixed keccak256

Usage as a library:

    from tools.canonical import configuration_hash, derive_status, normalise_value

Usage as a CLI:

    python tools/canonical.py hash    <config.json>
    python tools/canonical.py derive  <case.json>
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_VERSION = 1

# --------------------------------------------------------------------------------------------
# Vocabulary
# --------------------------------------------------------------------------------------------

FACT_STRING = "STRING"
FACT_INTEGER = "INTEGER"
FACT_BOOLEAN = "BOOLEAN"
FACT_DATE = "DATE"
FACT_ENUM = "ENUM"
FACT_TYPES = (FACT_STRING, FACT_INTEGER, FACT_BOOLEAN, FACT_DATE, FACT_ENUM)

# Per-source states. What ONE source yielded for the requested fact.
STATE_VALUE = "VALUE"
STATE_NO_VALUE = "NO_VALUE"
STATE_UNAVAILABLE = "UNAVAILABLE"
STATE_AMBIGUOUS = "AMBIGUOUS"
STATES = (STATE_VALUE, STATE_NO_VALUE, STATE_UNAVAILABLE, STATE_AMBIGUOUS)

# Aggregate statuses. What the CONTRACT derived across all sources.
STATUS_CONFIRMED = "CONFIRMED"
STATUS_CONFLICTED = "CONFLICTED"
STATUS_INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
STATUS_UNAVAILABLE = "UNAVAILABLE"
STATUSES = (STATUS_CONFIRMED, STATUS_CONFLICTED, STATUS_INSUFFICIENT, STATUS_UNAVAILABLE)

CASE_PRESERVE = "PRESERVE"
CASE_LOWER = "LOWER"
CASE_POLICIES = (CASE_PRESERVE, CASE_LOWER)

MAX_STRING_VALUE_LEN = 200

_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_INT_RE = re.compile(r"^-?(0|[1-9]\d*)$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


# --------------------------------------------------------------------------------------------
# Canonical text and JSON
# --------------------------------------------------------------------------------------------


def normalise_text(value: str) -> str:
    """Deterministic text normalisation applied to every stored and hashed string.

    NFC, CRLF/CR collapse to LF, control characters stripped, whitespace runs collapsed to one
    space, trimmed. The same logical input must produce identical bytes on Windows and Linux --
    the configuration hash depends on it.
    """
    out = unicodedata.normalize("NFC", value)
    out = out.replace("\r\n", "\n").replace("\r", "\n")
    out = _CONTROL_RE.sub("", out)
    out = re.sub(r"\s+", " ", out)
    return out.strip()


def canonical_json(payload: Any) -> str:
    """Key-sorted, separator-tight, non-ASCII-preserving JSON. The only serialisation used."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# --------------------------------------------------------------------------------------------
# Normalisation, per fact type
# --------------------------------------------------------------------------------------------


def _is_real_date(y: int, m: int, d: int) -> bool:
    if not 1 <= m <= 12 or d < 1:
        return False
    limit = _DAYS[m - 1]
    if m == 2 and (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)):
        limit = 29
    return d <= limit


def normalise_value(fact_type: str, raw: Any, rules: Mapping[str, Any] | None = None) -> str | None:
    """Canonicalise one extracted value, or return None if it does not conform.

    None means "this is not a usable value of this type". The contract treats a `VALUE` state
    carrying a non-conforming value as a MALFORMED RESPONSE, not as an ambiguous source: a model
    that cannot produce a conforming value is required to say `AMBIGUOUS` instead. Repairing the
    value here would be guessing at intent, and two nodes guessing independently is a divergence.
    """
    rules = dict(rules or {})
    if raw is None:
        return None
    if isinstance(raw, bool):  # bool is an int subclass; catch it before INTEGER
        text = "true" if raw else "false"
    elif isinstance(raw, int):
        text = str(raw)
    elif isinstance(raw, str):
        text = raw
    else:
        return None

    text = normalise_text(text)
    if not text:
        return None

    if fact_type == FACT_DATE:
        m = _DATE_RE.match(text)
        if not m:
            return None
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if not _is_real_date(y, mo, d):
            return None
        return f"{y:04d}-{mo:02d}-{d:02d}"

    if fact_type == FACT_INTEGER:
        if not _INT_RE.match(text):
            return None
        n = int(text)
        lo = rules.get("min_value")
        hi = rules.get("max_value")
        if lo is not None and n < int(lo):
            return None
        if hi is not None and n > int(hi):
            return None
        return str(n)

    if fact_type == FACT_BOOLEAN:
        low = text.lower()
        if low in ("true", "yes"):
            return "true"
        if low in ("false", "no"):
            return "false"
        return None

    if fact_type == FACT_ENUM:
        allowed = [normalise_text(a) for a in (rules.get("allowed_enum_values") or [])]
        if rules.get("case_policy", CASE_PRESERVE) == CASE_LOWER:
            low = text.lower()
            for a in allowed:
                if a.lower() == low:
                    return a
            return None
        return text if text in allowed else None

    if fact_type == FACT_STRING:
        if rules.get("case_policy", CASE_PRESERVE) == CASE_LOWER:
            text = text.lower()
        if len(text) > MAX_STRING_VALUE_LEN:
            return None
        return text

    return None


# --------------------------------------------------------------------------------------------
# Deterministic status derivation -- THE decision function
# --------------------------------------------------------------------------------------------


def derive_status(
    source_results: Sequence[Mapping[str, Any]],
    minimum_supporting_sources: int,
    conflict_threshold: int,
    source_count: int,
) -> dict:
    """Map per-source results to one aggregate status and four index sets.

    Pure, total, and the only place a status value is ever produced. The model never emits a
    status; it emits per-source `(state, value)` pairs and this function decides.

    Precedence is load-bearing:

      1. Too few sources were REACHABLE to have met the threshold even with perfect extraction
         -> UNAVAILABLE. The failure is fetch, not fact, and the two must not be conflated.
      2. Two or more distinct values each reach `conflict_threshold`
         -> CONFLICTED. Checked BEFORE confirmation, deliberately: a genuine dispute must not be
         resolved by plurality. An oracle that silently picks the more popular of two contested
         answers is worse than one that reports the contest.
      3. The leading value reaches `minimum_supporting_sources` and nothing competes with it
         -> CONFIRMED.
      4. Otherwise the sources were reachable but did not produce enough usable agreement
         -> INSUFFICIENT_EVIDENCE.
    """
    by_index: dict[int, Mapping[str, Any]] = {int(r["source_index"]): r for r in source_results}

    supporting: list[int] = []
    conflicting: list[int] = []
    unavailable: list[int] = []
    ambiguous: list[int] = []
    no_value: list[int] = []

    tally: dict[str, list[int]] = {}
    for idx in range(source_count):
        r = by_index.get(idx)
        state = (r or {}).get("state", STATE_UNAVAILABLE)
        if state == STATE_UNAVAILABLE:
            unavailable.append(idx)
        elif state == STATE_AMBIGUOUS:
            ambiguous.append(idx)
        elif state == STATE_NO_VALUE:
            no_value.append(idx)
        elif state == STATE_VALUE:
            tally.setdefault(str(r["value"]), []).append(idx)

    reachable = source_count - len(unavailable)

    def result(status: str, value: str | None, sup: list[int], con: list[int]) -> dict:
        return {
            "status": status,
            "normalized_value": value,
            "supporting_source_indices": sorted(sup),
            "conflicting_source_indices": sorted(con),
            "unavailable_source_indices": sorted(unavailable),
            "ambiguous_source_indices": sorted(ambiguous),
            "no_value_source_indices": sorted(no_value),
        }

    # 1. Fetch failure dominates.
    if reachable < minimum_supporting_sources:
        return result(STATUS_UNAVAILABLE, None, [], [])

    if not tally:
        return result(STATUS_INSUFFICIENT, None, [], [])

    # Deterministic ordering: most support first, then lexicographic value. The tie-break is not
    # cosmetic -- two nodes must pick the same leader from the same tally.
    ranked = sorted(tally.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    top_value, top_indices = ranked[0]

    contenders = [v for v, idxs in ranked if len(idxs) >= conflict_threshold]

    # A tie at the top is a dispute no threshold setting may resolve. The lexicographic tie-break
    # exists to pin determinism, never to pick a winner -- without this clause, a conflict_threshold
    # above the tied count would let row 4 confirm whichever value sorted first.
    top_count = len(top_indices)
    tied_at_top = sum(1 for _, idxs in ranked if len(idxs) == top_count)

    # 2. Genuine dispute.
    if len(contenders) >= 2 or tied_at_top >= 2:
        con = sorted(i for v, idxs in tally.items() for i in idxs)
        return result(STATUS_CONFLICTED, None, [], con)

    # 3. Confirmed.
    if top_count >= minimum_supporting_sources:
        others = sorted(i for v, idxs in tally.items() if v != top_value for i in idxs)
        return result(STATUS_CONFIRMED, top_value, top_indices, others)

    # 4. Reachable, but not enough agreement. Every VALUE index is recorded as conflicting so a
    #    near-miss is visible: the query was almost answered, not untouched.
    every = sorted(i for _, idxs in tally.items() for i in idxs)
    return result(STATUS_INSUFFICIENT, None, [], every)


# --------------------------------------------------------------------------------------------
# Configuration hash
# --------------------------------------------------------------------------------------------


def _keccak256(data: bytes) -> bytes:
    try:
        from eth_hash.auto import keccak  # type: ignore

        return keccak(data)
    except Exception:  # pragma: no cover - explicit failure beats a silent wrong digest
        raise SystemExit(
            "keccak256 unavailable. Install it:  pip install 'eth-hash[pycryptodome]'\n"
            "A different hash function would silently produce a different configuration_hash."
        )


def configuration_payload(config: Mapping[str, Any]) -> dict:
    """Everything immutable that can change the outcome or the consensus rules.

    `source_urls` order is PRESERVED and is part of the digest, unlike every other list here.
    Source indices are referenced by the canonical record, so reordering the URLs changes what
    index 0 means -- that is a different configuration, not a re-spelling of the same one.
    """
    rules = dict(config.get("normalization_rules") or {})
    rules.setdefault("case_policy", CASE_PRESERVE)
    return {
        "v": SCHEMA_VERSION,
        "query_id": normalise_text(config["query_id"]),
        "question": normalise_text(config["question"]),
        "fact_type": config["fact_type"],
        "normalization_rules": {k: rules[k] for k in sorted(rules)},
        "allowed_enum_values": sorted(
            normalise_text(v) for v in (config.get("allowed_enum_values") or [])
        ),
        "source_urls": [normalise_text(u) for u in config["source_urls"]],
        "minimum_supporting_sources": int(config["minimum_supporting_sources"]),
        "conflict_threshold": int(config["conflict_threshold"]),
        "require_pinned_evidence": bool(config.get("require_pinned_evidence", False)),
    }


def configuration_hash(config: Mapping[str, Any]) -> str:
    payload = configuration_payload(config)
    return "0x" + _keccak256(canonical_json(payload).encode("utf-8")).hex()


# --------------------------------------------------------------------------------------------
# Canonical fact record
# --------------------------------------------------------------------------------------------


def canonical_record(
    config_hash: str,
    query_id: str,
    fact_type: str,
    derivation: Mapping[str, Any],
    resolved_at: int,
) -> str:
    """Key-sorted JSON of the decision-critical fields only.

    Excluded on purpose: reasoning, raw page text, model names, validator addresses, submitter,
    per-source quotes. None of it is decision-critical and all of it is either prose or identity.
    """
    payload = {
        "v": SCHEMA_VERSION,
        "configuration_hash": config_hash,
        "query_id": normalise_text(query_id),
        "fact_type": fact_type,
        "status": derivation["status"],
        "normalized_value": derivation["normalized_value"],
        "supporting_source_indices": sorted(derivation["supporting_source_indices"]),
        "conflicting_source_indices": sorted(derivation["conflicting_source_indices"]),
        "unavailable_source_indices": sorted(derivation["unavailable_source_indices"]),
        "ambiguous_source_indices": sorted(derivation["ambiguous_source_indices"]),
        "resolved_at": int(resolved_at),
    }
    return canonical_json(payload)


def _main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    cmd, path = argv[1], argv[2]
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

    if cmd == "hash":
        print(configuration_hash(data))
        return 0
    if cmd == "derive":
        cfg = data["config"] if "config" in data else data
        out = derive_status(
            data["source_results"],
            int(cfg["minimum_supporting_sources"]),
            int(cfg["conflict_threshold"]),
            len(cfg["source_urls"]),
        )
        print(canonical_json(out))
        return 0

    print(f"unknown command {cmd!r}")
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
