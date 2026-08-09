"""Consumer example for a DATE SourceConsensus instance."""
from __future__ import annotations
import json
from typing import Any
from eth_hash.auto import keccak

CONFIG = {
    "query_id": "LEDGERINDEXER_2_0_0_RELEASE_DATE",
    "question": "On what date was version 2.0.0 of LedgerIndexer officially released?",
    "fact_type": "DATE", "normalization_rules": {"case_policy": "PRESERVE"},
    "allowed_enum_values": [],
    "source_urls": [
        "https://raw.githubusercontent.com/GIFTEDLOV/source-consensus/7e58293b4b55fcf57dfc5e24d0d8a9f02e6c2d23/fixtures/corpus/01-all-agree/source-0-release-page.md",
        "https://raw.githubusercontent.com/GIFTEDLOV/source-consensus/7e58293b4b55fcf57dfc5e24d0d8a9f02e6c2d23/fixtures/corpus/01-all-agree/source-1-changelog.md",
        "https://raw.githubusercontent.com/GIFTEDLOV/source-consensus/7e58293b4b55fcf57dfc5e24d0d8a9f02e6c2d23/fixtures/corpus/01-all-agree/source-2-docs-announcement.md",
    ],
    "minimum_supporting_sources": 2, "conflict_threshold": 2,
    "require_pinned_evidence": True,
}

def expected_configuration_hash() -> str:
    payload = {"v": 1, **CONFIG}
    return "0x" + keccak(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hex()

def read_confirmed_date(oracle: Any) -> str:
    if oracle.configuration_hash() != expected_configuration_hash():
        raise RuntimeError("ORACLE_CONFIGURATION_MISMATCH")
    if oracle.get_config()["configuration_hash"] != expected_configuration_hash():
        raise RuntimeError("ORACLE_CONFIGURATION_MISMATCH")
    if len(oracle.get_sources()) != 3:
        raise RuntimeError("ORACLE_SOURCES_MISMATCH")
    if oracle.status() != "CONFIRMED":
        raise RuntimeError("FACT_NOT_CONFIRMED")
    value = oracle.value()
    record = json.loads(oracle.get_record())
    if record["configuration_hash"] != expected_configuration_hash() or record["normalized_value"] != value:
        raise RuntimeError("CANONICAL_RECORD_MISMATCH")
    return value
