"""The tiered comparator: what validators must agree on, and what they need not.

The rule under test (docs/DERIVATION.md section 7):

  T1 strict     status, normalised value, supporting indices, and the (state, value) of every
                supporting source.
  T2 recorded   which non-supporting bucket each remaining source fell into -- NOT compared.
  T3 free       anything else -- never compared, never stored.

`TestNonSupportingBucketsAreNotConsensusCritical` is the named marker for STAGE3_RISK_T2_BUCKETS.
**These tests prove the RULE holds. They do not prove real models exercise it safely** -- that is a
convergence measurement, and Stage 3 owes it. A green run here must not be read as empirical
evidence about model behaviour.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.canonical import derive_status  # noqa: E402


def results(*pairs):
    out = []
    for i, p in enumerate(pairs):
        if isinstance(p, tuple):
            out.append({"source_index": i, "state": p[0], "value": p[1]})
        else:
            out.append({"source_index": i, "state": p, "value": None})
    return out


def derive(*pairs, minimum=2, conflict=2):
    rs = results(*pairs)
    return derive_status(rs, minimum, conflict, len(rs))


V = "VALUE"

DECISION_FIELDS = ("status", "normalized_value", "supporting_source_indices")


class TestNonSupportingBucketsAreNotConsensusCritical:
    """STAGE3_RISK_T2_BUCKETS -- the marker Stage 3's harness must measure against.

    Every pair below is two honest validators differing ONLY in how they classified a
    non-supporting source. None of those states supports a value, so none can move a row in the
    derivation table -- and these tests assert exactly that, field by field.
    """

    @pytest.mark.parametrize("a,b,label", [
        ("NO_VALUE", "AMBIGUOUS", "a vague page read two defensible ways"),
        ("NO_VALUE", "UNAVAILABLE", "a slow host one node gave up on"),
        ("AMBIGUOUS", "UNAVAILABLE", "a page that half-loaded"),
    ])
    def test_swapping_a_non_supporting_bucket_cannot_change_the_decision(self, a, b, label):
        left = derive((V, "X"), (V, "X"), a)
        right = derive((V, "X"), (V, "X"), b)
        for f in DECISION_FIELDS:
            assert left[f] == right[f], f"{label}: {f} changed with the bucket"
        assert left["status"] == "CONFIRMED"

    def test_the_buckets_themselves_do_differ(self):
        """The distinction is observable -- that is the point of keeping it."""
        left = derive((V, "X"), (V, "X"), "NO_VALUE")
        right = derive((V, "X"), (V, "X"), "AMBIGUOUS")
        assert left["no_value_source_indices"] != right["no_value_source_indices"]
        assert left["ambiguous_source_indices"] != right["ambiguous_source_indices"]

    def test_two_non_supporting_sources_may_both_differ(self):
        left = derive((V, "X"), (V, "X"), "NO_VALUE", "AMBIGUOUS")
        right = derive((V, "X"), (V, "X"), "AMBIGUOUS", "NO_VALUE")
        for f in DECISION_FIELDS:
            assert left[f] == right[f]

    def test_a_bucket_change_that_alters_reachability_DOES_change_the_decision(self):
        """The boundary of the exemption: UNAVAILABLE reduces `reachable`, so enough of them
        genuinely change the outcome and validators SHOULD disagree."""
        left = derive((V, "X"), "NO_VALUE", "NO_VALUE")
        right = derive((V, "X"), "UNAVAILABLE", "UNAVAILABLE")
        assert left["status"] == "INSUFFICIENT_EVIDENCE"
        assert right["status"] == "UNAVAILABLE"

    def test_a_supporting_source_moving_DOES_change_the_decision(self):
        """T1 is strict: if a validator's own extraction changes who supports the value, it
        genuinely disagrees and must reject."""
        left = derive((V, "X"), (V, "X"), (V, "X"))
        right = derive((V, "X"), (V, "X"), "NO_VALUE")
        assert left["supporting_source_indices"] != right["supporting_source_indices"]


class TestSupportingSetIsStrict:
    def test_same_status_from_a_different_supporting_set_is_still_a_disagreement(self):
        """Agreeing on the conclusion from a different evidence base is agreement by
        coincidence, and the comparator must not accept it."""
        left = derive((V, "X"), (V, "X"), (V, "Y"))
        right = derive((V, "X"), (V, "Y"), (V, "X"))
        assert left["status"] == right["status"] == "CONFIRMED"
        assert left["supporting_source_indices"] == [0, 1]
        assert right["supporting_source_indices"] == [0, 2]
        assert left["supporting_source_indices"] != right["supporting_source_indices"]

    def test_the_same_value_from_the_same_sources_agrees(self):
        assert derive((V, "X"), (V, "X"), "NO_VALUE") == derive((V, "X"), (V, "X"), "NO_VALUE")


class TestValidatorRejectsMalformedLeaderProposals:
    """Structural validation happens before any comparison, so a malformed proposal is rejected
    outright rather than compared field by field."""

    def test_leader_error_is_not_agreed_with(self, deploy, sources_available, llm_per_source):
        from tests.conftest import value

        sc = deploy(n_sources=2)
        sources_available(n=2)
        llm_per_source([value("2026-03-11"), "not json"])
        with pytest.raises(Exception):
            sc.resolve()
        assert sc.is_resolved() is False


class TestConsensusScopeIsDocumented:
    def test_the_risk_marker_exists_in_the_contract(self):
        """A green suite must not be mistaken for a convergence measurement. The marker is the
        hook Stage 3's harness searches for."""
        src = (ROOT / "contracts" / "source_consensus.py").read_text(encoding="utf-8")
        assert "STAGE3_RISK_T2_BUCKETS" in src
        assert "leader-recorded" in src, "the marker must say what the limitation IS"

    def test_the_derivation_doc_states_the_consequence(self):
        doc = (ROOT / "docs" / "DERIVATION.md").read_text(encoding="utf-8")
        assert "leader's partition" in doc
        assert "not consensus-backed" in doc
