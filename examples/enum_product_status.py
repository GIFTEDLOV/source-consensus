"""Consumer example for an ENUM SourceConsensus instance."""
from __future__ import annotations
import json
from typing import Any
from eth_hash.auto import keccak

CONFIG = {
    "query_id": "PRODUCT_STATUS_LEDGERINDEXER",
    "question": "What is the public product status of LedgerIndexer?",
    "fact_type": "ENUM", "normalization_rules": {"case_policy": "LOWER"},
    "allowed_enum_values": ["active", "deprecated", "maintenance"],
    "source_urls": [
        "https://api.github.com/repos/GIFTEDLOV/source-consensus",
        "https://github.com/GIFTEDLOV/source-consensus/releases",
        "https://github.com/GIFTEDLOV/source-consensus/commits/main",
    ],
    "minimum_supporting_sources": 2, "conflict_threshold": 2,
    "require_pinned_evidence": False,
}

def expected_configuration_hash() -> str:
    payload = {"v": 1, **CONFIG}
    payload["allowed_enum_values"] = sorted(payload["allowed_enum_values"])
    return "0x" + keccak(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hex()

def read_product_status(oracle: Any) -> str:
    if oracle.configuration_hash() != expected_configuration_hash() or oracle.get_config()["configuration_hash"] != expected_configuration_hash():
        raise RuntimeError("ORACLE_CONFIGURATION_MISMATCH")
    status = oracle.status()
    if status in {"CONFLICTED", "INSUFFICIENT_EVIDENCE", "UNAVAILABLE"}:
        raise RuntimeError("PRODUCT_STATUS_NOT_ACTIONABLE")
    if status != "CONFIRMED":
        raise RuntimeError("UNKNOWN_ORACLE_STATUS")
    value = oracle.value()
    record = json.loads(oracle.get_record())
    if record["normalized_value"] != value or record["status"] != "CONFIRMED":
        raise RuntimeError("CANONICAL_RECORD_MISMATCH")
    return value
