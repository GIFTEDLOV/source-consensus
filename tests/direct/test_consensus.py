"""Executable coverage for the complete validator-bound consensus payload.

This file is the regression suite for the steward finding that rejected v1.0.0-bradbury.  The
old comparator checked only aggregate fields plus supporting sources, even though post-consensus
derivation consumed every source entry.  These tests execute the contract's comparator directly
and require every per-source state/value and every derived aggregate field to be bound.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.canonical import derive_status  # noqa: E402

A = "2026-03-11"
B = "2026-04-01"
C = "2026-05-09"
AGGREGATE_FIELDS = (
    "status",
    "normalized_value",
    "supporting_source_indices",
    "conflicting_source_indices",
    "unavailable_source_indices",
    "ambiguous_source_indices",
    "no_value_source_indices",
)


def _module(deploy, n: int):
    proxy = deploy(n_sources=n, minimum_supporting_sources=min(3, n), conflict_threshold=2)
    instance = object.__getattribute__(proxy, "_instance")
    return sys.modules[instance.__class__.__module__]


def _payload(pairs, minimum=3, conflict=2):
    states = [state for state, _ in pairs]
    values = [value for _, value in pairs]
    records = [
        {"source_index": i, "state": state, "value": value}
        for i, (state, value) in enumerate(pairs)
    ]
    result = derive_status(records, minimum, conflict, len(records))
    result["states"] = states
    result["values"] = values
    return result


def _agree(module, leader, own, minimum=3, conflict=2):
    return module._agree(
        leader,
        own,
        len(own["states"]),
        "DATE",
        "PRESERVE",
        None,
        None,
        [],
        minimum,
        conflict,
    )


def _prepare_storage(module, payload, minimum=3, conflict=2):
    return module._prepare_storage_result(
        payload,
        len(payload["states"]),
        "DATE",
        "PRESERVE",
        None,
        None,
        [],
        minimum,
        conflict,
    )


def _confirmed_five():
    return _payload([
        ("VALUE", A),
        ("VALUE", A),
        ("VALUE", A),
        ("NO_VALUE", None),
        ("NO_VALUE", None),
    ])


def _override(payload, **changes):
    out = copy.deepcopy(payload)
    out.update(changes)
    return out


class TestStewardRejectionRegression:
    def test_r01_non_supporting_no_value_tampered_to_value_is_rejected(self, deploy):
        own = _confirmed_five()
        leader = copy.deepcopy(own)
        leader["states"][4], leader["values"][4] = "VALUE", B
        assert _agree(_module(deploy, 5), leader, own) is False

    def test_r02_two_unchecked_entries_cannot_turn_confirmed_into_conflicted(self, deploy):
        own = _confirmed_five()
        leader = copy.deepcopy(own)
        for i in (3, 4):
            leader["states"][i], leader["values"][i] = "VALUE", B
        # This is the steward's exact exploit: the advertised result is CONFIRMED A while the
        # complete leader payload deterministically derives CONFLICTED.
        assert _agree(_module(deploy, 5), leader, own) is False

    def test_r03_unavailable_tampered_to_value_is_rejected(self, deploy):
        own = _payload([("VALUE", A), ("VALUE", A), ("VALUE", A), ("UNAVAILABLE", None)])
        leader = copy.deepcopy(own)
        leader["states"][3], leader["values"][3] = "VALUE", B
        assert _agree(_module(deploy, 4), leader, own) is False

    def test_r04_ambiguous_tampered_to_value_is_rejected(self, deploy):
        own = _payload([("VALUE", A), ("VALUE", A), ("VALUE", A), ("AMBIGUOUS", None)])
        leader = copy.deepcopy(own)
        leader["states"][3], leader["values"][3] = "VALUE", B
        assert _agree(_module(deploy, 4), leader, own) is False

    def test_r05_no_value_tampered_to_unavailable_when_reachability_changes(self, deploy):
        own = _payload([("VALUE", A), ("VALUE", A), ("NO_VALUE", None)], minimum=3)
        leader = copy.deepcopy(own)
        leader["states"][2] = "UNAVAILABLE"
        assert _agree(_module(deploy, 3), leader, own, minimum=3) is False

    def test_r06_unavailable_tampered_to_no_value_when_status_may_change(self, deploy):
        own = _payload([("VALUE", A), ("VALUE", A), ("UNAVAILABLE", None)], minimum=3)
        leader = copy.deepcopy(own)
        leader["states"][2] = "NO_VALUE"
        assert _agree(_module(deploy, 3), leader, own, minimum=3) is False

    def test_r07_any_non_supporting_normalized_value_change_is_rejected(self, deploy):
        own = _payload([("VALUE", A), ("VALUE", A), ("VALUE", A), ("VALUE", B)])
        leader = copy.deepcopy(own)
        leader["values"][3] = C
        assert _agree(_module(deploy, 4), leader, own) is False

    def test_r08_state_change_is_rejected_even_if_advertised_aggregate_is_unchanged(self, deploy):
        own = _confirmed_five()
        leader = copy.deepcopy(own)
        leader["states"][4] = "AMBIGUOUS"
        assert _agree(_module(deploy, 5), leader, own) is False

    def test_r09_value_change_is_rejected_even_if_advertised_aggregate_is_unchanged(self, deploy):
        own = _payload([("VALUE", A), ("VALUE", A), ("VALUE", A), ("VALUE", B)])
        leader = copy.deepcopy(own)
        leader["values"][3] = C
        assert _agree(_module(deploy, 4), leader, own) is False

    @pytest.mark.parametrize(
        "label,payload,changes,minimum",
        [
            pytest.param(
                "R10",
                _payload([("VALUE", A), ("VALUE", A), ("VALUE", A), ("VALUE", B), ("VALUE", B)]),
                {"status": "CONFIRMED", "normalized_value": A,
                 "supporting_source_indices": [0, 1, 2], "conflicting_source_indices": [3, 4]},
                3,
                id="r10-confirmed-advertisement-over-conflicted-payload",
            ),
            pytest.param(
                "R11", _confirmed_five(),
                {"status": "INSUFFICIENT_EVIDENCE", "normalized_value": None,
                 "supporting_source_indices": [], "conflicting_source_indices": []},
                3,
                id="r11-insufficient-advertisement-over-confirmed-payload",
            ),
            pytest.param(
                "R12", _confirmed_five(),
                {"status": "UNAVAILABLE", "normalized_value": None,
                 "supporting_source_indices": [], "conflicting_source_indices": []},
                3,
                id="r12-unavailable-advertisement-over-confirmed-payload",
            ),
        ],
    )
    def test_r10_r12_leader_aggregate_must_match_own_payload(
        self, deploy, label, payload, changes, minimum
    ):
        del label
        assert _agree(
            _module(deploy, len(payload["states"])),
            _override(payload, **changes),
            payload,
            minimum=minimum,
        ) is False

    @pytest.mark.parametrize(
        "field,wrong",
        [
            pytest.param("supporting_source_indices", [0, 1], id="r13-wrong-supporting-set"),
            pytest.param("conflicting_source_indices", [4], id="r14-wrong-conflicting-set"),
            pytest.param("unavailable_source_indices", [4], id="r15-wrong-unavailable-set"),
            pytest.param("ambiguous_source_indices", [4], id="r16-wrong-ambiguous-set"),
            pytest.param("no_value_source_indices", [3], id="r17-wrong-no-value-set"),
        ],
    )
    def test_r13_r17_every_derived_index_set_is_bound(self, deploy, field, wrong):
        own = _confirmed_five()
        assert _agree(_module(deploy, 5), _override(own, **{field: wrong}), own) is False

    @pytest.mark.parametrize(
        "field,operation",
        [
            pytest.param("states", "short", id="r18-states-too-short"),
            pytest.param("states", "long", id="r19-states-too-long"),
            pytest.param("values", "short", id="r20-values-too-short"),
            pytest.param("values", "long", id="r21-values-too-long"),
        ],
    )
    def test_r18_r21_array_lengths_are_exact(self, deploy, field, operation):
        own = _confirmed_five()
        leader = copy.deepcopy(own)
        if operation == "short":
            leader[field] = leader[field][:-1]
        else:
            leader[field] = leader[field] + (["NO_VALUE"] if field == "states" else [None])
        assert _agree(_module(deploy, 5), leader, own) is False

    @pytest.mark.parametrize(
        "state,value",
        [
            pytest.param("UNKNOWN", None, id="r22-unknown-state"),
            pytest.param("VALUE", None, id="r23-value-with-null"),
            pytest.param("NO_VALUE", A, id="r24-non-value-with-value"),
            pytest.param("VALUE", "2026-02-30", id="r25-unnormalizable-value"),
        ],
    )
    def test_r22_r25_malformed_source_entries_are_rejected(self, deploy, state, value):
        own = _confirmed_five()
        leader = copy.deepcopy(own)
        leader["states"][4], leader["values"][4] = state, value
        assert _agree(_module(deploy, 5), leader, own) is False

    def test_r26_source_order_manipulation_is_rejected(self, deploy):
        own = _payload([("VALUE", A), ("VALUE", A), ("VALUE", A), ("VALUE", B), ("NO_VALUE", None)])
        leader = copy.deepcopy(own)
        leader["states"][3], leader["states"][4] = leader["states"][4], leader["states"][3]
        leader["values"][3], leader["values"][4] = leader["values"][4], leader["values"][3]
        assert _agree(_module(deploy, 5), leader, own) is False

    def test_r27_any_independently_different_source_pair_is_rejected(self, deploy):
        leader = _confirmed_five()
        own = copy.deepcopy(leader)
        own["states"][4] = "AMBIGUOUS"
        own["no_value_source_indices"] = [3]
        own["ambiguous_source_indices"] = [4]
        assert _agree(_module(deploy, 5), leader, own) is False

    def test_r28_complete_matching_payload_is_accepted(self, deploy):
        payload = _confirmed_five()
        assert _agree(_module(deploy, 5), payload, copy.deepcopy(payload)) is True


class TestValidatorRejectsMalformedLeaderProposals:
    def test_leader_error_is_not_agreed_with(self, deploy, sources_available, llm_per_source):
        from tests.conftest import value

        sc = deploy(n_sources=2)
        sources_available(n=2)
        llm_per_source([value(A), "not json"])
        with pytest.raises(Exception):
            sc.resolve()
        assert sc.is_resolved() is False


class TestPostConsensusStorageBoundary:
    @pytest.mark.parametrize(
        "changes",
        [
            {"status": "INSUFFICIENT_EVIDENCE"},
            {"normalized_value": B},
            {"conflicting_source_indices": [4]},
        ],
        ids=("status", "normalized-value", "conflicting-set"),
    )
    def test_storage_rejects_unverified_leader_aggregates(self, deploy, changes):
        payload = _override(_confirmed_five(), **changes)
        assert _prepare_storage(_module(deploy, 5), payload) is None

    def test_storage_rejects_an_unverified_source_payload(self, deploy):
        payload = _confirmed_five()
        payload["states"][4], payload["values"][4] = "VALUE", B
        assert _prepare_storage(_module(deploy, 5), payload) is None

    def test_storage_rederives_instead_of_consuming_advertised_fields(self, deploy):
        payload = _confirmed_five()
        prepared = _prepare_storage(_module(deploy, 5), payload)
        assert prepared["final"]["status"] == "CONFIRMED"
        assert prepared["final"]["normalized_value"] == A

    def test_leader_self_derivation_gate_is_executable(self, deploy):
        module = _module(deploy, 5)
        payload = _override(_confirmed_five(), status="INSUFFICIENT_EVIDENCE")
        assert module._validate_consensus_payload(
            payload, 5, "DATE", "PRESERVE", None, None, [], 3, 2
        ) is None

    def test_malformed_value_is_rejected_even_when_raw_aggregate_is_self_consistent(self, deploy):
        module = _module(deploy, 5)
        payload = _payload([
            ("VALUE", A), ("VALUE", A), ("VALUE", A),
            ("NO_VALUE", None), ("VALUE", "2026-02-30"),
        ])
        # `_derive_status` treats the invalid spelling as an opaque distinct value, so all
        # aggregates are internally consistent. Only canonical type validation can reject it.
        assert payload["status"] == "CONFIRMED"
        assert payload["conflicting_source_indices"] == [4]
        assert module._validate_consensus_payload(
            payload, 5, "DATE", "PRESERVE", None, None, [], 3, 2
        ) is None


class TestConsensusScopeIsDocumented:
    def test_contract_declares_complete_payload_binding(self):
        module_text = (ROOT / "contracts" / "source_consensus.py").read_text(encoding="utf-8")
        assert "FULL_CONSENSUS_PAYLOAD_FIELDS" in module_text
        assert "STAGE3_RISK_T2_BUCKETS" not in module_text

    def test_derivation_doc_rejects_the_historical_t2_rule(self):
        doc = (ROOT / "docs" / "DERIVATION.md").read_text(encoding="utf-8")
        assert "every per-source state and normalized value" in doc
        assert "T2 recorded" not in doc


def test_aggregate_field_list_is_complete():
    assert len(AGGREGATE_FIELDS) == 7
