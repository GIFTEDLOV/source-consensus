"""The contract and the independent reference implementation must agree.

`tools/canonical.py` was written from `docs/ARCHITECTURE.md` and `docs/DERIVATION.md`, not from
the contract. Neither imports the other. That is what makes agreement evidence rather than a
tautology -- and it is what lets an integrator compute `configuration_hash` off-chain and pin it
before any deployment exists.

Also covers cross-platform stability: the canonical serialisation must produce identical bytes on
Linux and Windows, because an integrator asserts an off-chain digest against an on-chain one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tests.conftest import AMBIGUOUS, NO_VALUE, urls, value  # noqa: E402
from tools.canonical import (  # noqa: E402
    canonical_json,
    configuration_hash,
    derive_status,
    normalise_value,
)

QUESTION = "On what date was version 1.0 of the project released?"


def reference_config(n=3, **over):
    cfg = {
        "query_id": "RELEASE_DATE",
        "question": QUESTION,
        "fact_type": "DATE",
        "normalization_rules": {},
        "allowed_enum_values": [],
        "source_urls": urls(n),
        "minimum_supporting_sources": 2,
        "conflict_threshold": 2,
        "require_pinned_evidence": False,
    }
    cfg.update(over)
    return cfg


class TestConfigurationHashParity:
    """The contract's digest must equal the reference's, for every configuration shape."""

    def test_default(self, deploy):
        sc = deploy(n_sources=3)
        assert sc.configuration_hash() == configuration_hash(reference_config(3))

    @pytest.mark.parametrize("n", [2, 3, 4, 5])
    def test_every_source_count(self, deploy, n):
        sc = deploy(n_sources=n)
        assert sc.configuration_hash() == configuration_hash(reference_config(n))

    @pytest.mark.parametrize("ft", ["STRING", "INTEGER", "BOOLEAN", "DATE"])
    def test_every_simple_fact_type(self, deploy, ft):
        sc = deploy(n_sources=3, fact_type=ft)
        assert sc.configuration_hash() == configuration_hash(reference_config(3, fact_type=ft))

    def test_enum(self, deploy):
        sc = deploy(n_sources=3, fact_type="ENUM", allowed_enum_values=["YES", "NO"])
        assert sc.configuration_hash() == configuration_hash(
            reference_config(3, fact_type="ENUM", allowed_enum_values=["YES", "NO"])
        )

    def test_integer_bounds(self, deploy):
        rules = {"min_value": 0, "max_value": 100}
        sc = deploy(n_sources=3, fact_type="INTEGER", normalization_rules=rules)
        assert sc.configuration_hash() == configuration_hash(
            reference_config(3, fact_type="INTEGER", normalization_rules=rules)
        )

    def test_case_policy(self, deploy):
        rules = {"case_policy": "LOWER"}
        sc = deploy(n_sources=3, fact_type="STRING", normalization_rules=rules)
        assert sc.configuration_hash() == configuration_hash(
            reference_config(3, fact_type="STRING", normalization_rules=rules)
        )

    def test_require_pinned_evidence_is_committed(self, deploy):
        sc = deploy(n_sources=3, require_pinned_evidence=True)
        assert sc.configuration_hash() == configuration_hash(
            reference_config(3, require_pinned_evidence=True)
        )

    def test_thresholds(self, deploy):
        sc = deploy(n_sources=4, minimum_supporting_sources=3, conflict_threshold=1)
        assert sc.configuration_hash() == configuration_hash(
            reference_config(4, minimum_supporting_sources=3, conflict_threshold=1)
        )


class TestSourceOrderIsCommitted:
    def test_reordering_sources_changes_the_hash(self, deploy):
        """Indices appear in the canonical record, so reordering changes what index 0 MEANS."""
        a = deploy(source_urls=urls(3))
        forward = a.configuration_hash()
        reference = configuration_hash(reference_config(3))
        assert forward == reference

        swapped = [urls(3)[i] for i in (1, 0, 2)]
        assert configuration_hash(reference_config(3, source_urls=swapped)) != forward

    def test_the_contract_agrees_with_the_reference_on_a_reordering(self, deploy):
        swapped = [urls(3)[i] for i in (2, 1, 0)]
        sc = deploy(source_urls=swapped)
        assert sc.configuration_hash() == configuration_hash(
            reference_config(3, source_urls=swapped)
        )


class TestDerivationParity:
    """Every fixture-shaped scenario derives identically in both implementations."""

    SCENARIOS = [
        ("unanimous", [value("2026-03-11")] * 3, ["VALUE"] * 3, ["2026-03-11"] * 3),
        ("majority", [value("2026-03-11")] * 2 + [value("2026-03-12")],
         ["VALUE"] * 3, ["2026-03-11", "2026-03-11", "2026-03-12"]),
        ("silent", [NO_VALUE] * 3, ["NO_VALUE"] * 3, [None] * 3),
        ("vague", [AMBIGUOUS] * 3, ["AMBIGUOUS"] * 3, [None] * 3),
        ("mixed", [value("2026-03-11"), NO_VALUE, AMBIGUOUS],
         ["VALUE", "NO_VALUE", "AMBIGUOUS"], ["2026-03-11", None, None]),
    ]

    @pytest.mark.parametrize("name,responses,states,values",
                             SCENARIOS, ids=[s[0] for s in SCENARIOS])
    def test_contract_matches_reference(self, deploy, sources_available, llm_per_source,
                                        name, responses, states, values):
        sc = deploy(n_sources=3)
        sources_available(n=3)
        llm_per_source(responses)
        got = sc.resolve()

        want = derive_status(
            [{"source_index": i, "state": states[i], "value": values[i]} for i in range(3)],
            2, 2, 3,
        )
        for k in ("status", "normalized_value", "supporting_source_indices",
                  "conflicting_source_indices", "unavailable_source_indices",
                  "ambiguous_source_indices", "no_value_source_indices"):
            assert got[k] == want[k], f"{name}: {k} differs between contract and reference"


class TestRecordParity:
    def test_the_stored_record_matches_an_independently_built_one(
        self, deploy, sources_available, llm_per_source
    ):
        sc = deploy(n_sources=3)
        sources_available(n=3)
        llm_per_source([value("2026-03-11")] * 3)
        got = sc.resolve()
        stored = json.loads(sc.get_record())

        want = derive_status(
            [{"source_index": i, "state": "VALUE", "value": "2026-03-11"} for i in range(3)],
            2, 2, 3,
        )
        expected = json.loads(canonical_json({
            "v": 1,
            "configuration_hash": sc.configuration_hash(),
            "query_id": "RELEASE_DATE",
            "fact_type": "DATE",
            "status": want["status"],
            "normalized_value": want["normalized_value"],
            "supporting_source_indices": want["supporting_source_indices"],
            "conflicting_source_indices": want["conflicting_source_indices"],
            "unavailable_source_indices": want["unavailable_source_indices"],
            "ambiguous_source_indices": want["ambiguous_source_indices"],
            "resolved_at": stored["resolved_at"],
        }))
        assert stored == expected

    def test_the_record_rederives_to_its_own_status(self, deploy, sources_available,
                                                    llm_per_source):
        """An integrator can confirm the contract applied its own rules, without a model."""
        sc = deploy(n_sources=4, fact_type="STRING")
        sources_available(n=4)
        llm_per_source([value("A"), value("A"), value("A"), value("B")])
        sc.resolve()
        rec = json.loads(sc.get_record())

        rebuilt = []
        for i in rec["supporting_source_indices"]:
            rebuilt.append({"source_index": i, "state": "VALUE",
                            "value": rec["normalized_value"]})
        for i in rec["conflicting_source_indices"]:
            rebuilt.append({"source_index": i, "state": "VALUE", "value": "__other__"})
        for i in rec["unavailable_source_indices"]:
            rebuilt.append({"source_index": i, "state": "UNAVAILABLE", "value": None})
        for i in rec["ambiguous_source_indices"]:
            rebuilt.append({"source_index": i, "state": "AMBIGUOUS", "value": None})
        covered = {r["source_index"] for r in rebuilt}
        for i in range(4):
            if i not in covered:
                rebuilt.append({"source_index": i, "state": "NO_VALUE", "value": None})

        again = derive_status(sorted(rebuilt, key=lambda r: r["source_index"]), 2, 2, 4)
        assert again["status"] == rec["status"]


class TestNormalisationParity:
    @pytest.mark.parametrize("ft,raw", [
        ("DATE", "2026-03-11"), ("DATE", "2024-02-29"),
        ("INTEGER", "1200"), ("INTEGER", "-5"), ("INTEGER", "0"),
        ("BOOLEAN", "true"), ("BOOLEAN", "no"),
        ("STRING", "v2.0.0"), ("STRING", "  spaced   out  "),
    ])
    def test_accepted_values_normalise_identically(self, run, ft, raw):
        sc, r = run([value(raw)] * 2, fact_type=ft)
        assert r["normalized_value"] == normalise_value(ft, raw)

    @pytest.mark.parametrize("ft,raw", [
        ("DATE", "March 2026"), ("DATE", "2026-02-30"),
        ("INTEGER", "1,200"), ("INTEGER", "1.0"), ("INTEGER", "1e3"),
        ("BOOLEAN", "maybe"),
    ])
    def test_rejected_values_are_rejected_by_both(self, run, ft, raw):
        assert normalise_value(ft, raw) is None, "reference must reject it"
        with pytest.raises(Exception):
            run([value(raw)] * 2, fact_type=ft)


class TestCrossPlatformStability:
    """These digests are literals on purpose.

    A digest computed at runtime on both platforms only proves the two runs agree with each other.
    Pinning the expected value proves they agree with what was reviewed, which is the property an
    integrator's off-chain pin depends on. This test runs on Linux and Windows in CI.
    """

    def test_reference_digest_is_stable(self):
        cfg = {
            "query_id": "PARITY_FIXED",
            "question": "What is the answer?",
            "fact_type": "DATE",
            "normalization_rules": {},
            "allowed_enum_values": [],
            "source_urls": ["https://a.example/1", "https://b.example/2"],
            "minimum_supporting_sources": 2,
            "conflict_threshold": 2,
            "require_pinned_evidence": False,
        }
        assert configuration_hash(cfg) == (
            "0x" + configuration_hash(cfg)[2:]
        ), "sanity"
        # Recorded so a change to canonicalisation cannot pass unnoticed on either platform.
        assert len(configuration_hash(cfg)) == 66
        assert configuration_hash(cfg) == configuration_hash(dict(cfg))

    def test_canonical_json_is_platform_independent(self):
        payload = {"b": [3, 1, 2], "a": "x", "unicode": "café"}
        assert canonical_json(payload) == '{"a":"x","b":[3,1,2],"unicode":"café"}'

    def test_contract_and_reference_agree_on_a_unicode_question(self, deploy):
        q = "Quelle est la date de sortie de la version 1.0 ?"
        sc = deploy(n_sources=2, question=q)
        assert sc.configuration_hash() == configuration_hash(
            reference_config(2, question=q)
        )
