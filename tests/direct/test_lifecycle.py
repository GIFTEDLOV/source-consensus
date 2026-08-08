"""Terminality, and the one deliberate exception to it.

CONFIRMED, CONFLICTED and INSUFFICIENT_EVIDENCE are judgements about the world and are terminal:
re-resolving until the answer is agreeable is the failure mode this design exists to prevent.

UNAVAILABLE means "we could not look", and is retryable. A five-minute outage must not permanently
poison a query whose configuration is correct. docs/ARCHITECTURE.md section 10.1.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tests.conftest import AMBIGUOUS, NO_VALUE, value  # noqa: E402


class TestTerminality:
    @pytest.mark.parametrize("responses,expected", [
        ([value("2026-03-11")] * 3, "CONFIRMED"),
        ([value("A"), value("A"), value("B"), value("B")], "CONFLICTED"),
        ([NO_VALUE, NO_VALUE, value("2026-03-11")], "INSUFFICIENT_EVIDENCE"),
    ])
    def test_second_resolve_reverts(self, deploy, sources_available, llm_per_source,
                                    responses, expected):
        ft = "STRING" if expected == "CONFLICTED" else "DATE"
        sc = deploy(n_sources=len(responses), fact_type=ft)
        sources_available(n=len(responses))
        llm_per_source(responses)
        assert sc.resolve()["status"] == expected
        with pytest.raises(Exception):
            sc.resolve()

    def test_the_stored_result_is_unchanged_after_a_rejected_second_attempt(
        self, deploy, sources_available, llm_per_source
    ):
        sc = deploy(n_sources=3)
        sources_available(n=3)
        llm_per_source([value("2026-03-11")] * 3)
        sc.resolve()
        before = sc.get_record()
        with pytest.raises(Exception):
            sc.resolve()
        assert sc.get_record() == before
        assert sc.status() == "CONFIRMED"
        assert sc.value() == "2026-03-11"

    def test_is_resolved_flips_exactly_once(self, deploy, sources_available, llm_per_source):
        sc = deploy(n_sources=3)
        assert sc.is_resolved() is False
        sources_available(n=3)
        llm_per_source([value("2026-03-11")] * 3)
        sc.resolve()
        assert sc.is_resolved() is True


class TestUnavailableIsRetryable:
    """The one exception, and the reason it exists."""

    def test_unavailable_does_not_resolve(self, deploy, sources_available, llm_per_source):
        sc = deploy(n_sources=3)
        sources_available(bodies=[None, None, None], n=3)
        llm_per_source([NO_VALUE] * 3)
        r = sc.resolve()
        assert r["status"] == "UNAVAILABLE"
        assert r["resolved"] is False
        assert sc.is_resolved() is False

    def test_a_retry_after_unavailable_can_succeed(self, deploy, direct_vm, llm_per_source):
        """A transient outage must not permanently poison a correctly configured query."""
        sc = deploy(n_sources=3)

        direct_vm.mock_web(r".*", {"status": 503, "body": ""})
        llm_per_source([NO_VALUE] * 3)
        assert sc.resolve()["status"] == "UNAVAILABLE"
        assert sc.is_resolved() is False

        # The sources come back.
        direct_vm._web_mocks.clear()
        for i in range(3):
            direct_vm.mock_web(rf".*source-{i}\.md", {"status": 200, "body": "body"})
        llm_per_source([value("2026-03-11")] * 3)

        r = sc.resolve()
        assert r["status"] == "CONFIRMED"
        assert sc.is_resolved() is True
        assert sc.value() == "2026-03-11"

    def test_attempts_are_counted_across_retries(self, deploy, direct_vm, llm_per_source):
        sc = deploy(n_sources=3)
        direct_vm.mock_web(r".*", {"status": 503, "body": ""})
        llm_per_source([NO_VALUE] * 3)
        sc.resolve()
        sc.resolve()
        assert sc.get_config()["attempts"] == 2
        assert sc.is_resolved() is False

    def test_unavailable_records_source_detail_without_resolving(
        self, deploy, sources_available, llm_per_source
    ):
        sc = deploy(n_sources=3)
        sources_available(bodies=[None, None, "live"], n=3)
        llm_per_source([NO_VALUE, NO_VALUE, value("2026-03-11")])
        r = sc.resolve()
        assert r["status"] == "UNAVAILABLE"
        assert r["unavailable_source_indices"] == [0, 1]
        assert r["record"] == "", "an unresolved query publishes no canonical record"

    def test_a_terminal_status_cannot_be_overwritten_by_a_later_unavailable(
        self, deploy, direct_vm, llm_per_source
    ):
        """Ordering attack: confirm first, then make the sources fail and try again."""
        sc = deploy(n_sources=3)
        for i in range(3):
            direct_vm.mock_web(rf".*source-{i}\.md", {"status": 200, "body": "body"})
        llm_per_source([value("2026-03-11")] * 3)
        sc.resolve()

        direct_vm._web_mocks.clear()
        direct_vm.mock_web(r".*", {"status": 503, "body": ""})
        llm_per_source([NO_VALUE] * 3)
        with pytest.raises(Exception):
            sc.resolve()
        assert sc.status() == "CONFIRMED"
        assert sc.value() == "2026-03-11"


class TestFailedResolutionWritesNothing:
    def test_malformed_output_leaves_the_query_open(self, deploy, sources_available,
                                                    llm_per_source):
        sc = deploy(n_sources=3)
        sources_available(n=3)
        llm_per_source(['{"state": "NONSENSE"}'] * 3)
        with pytest.raises(Exception):
            sc.resolve()
        assert sc.is_resolved() is False
        assert sc.status() == "UNRESOLVED"
        assert sc.get_record() == ""

    def test_the_query_can_resolve_after_a_failed_attempt(self, deploy, sources_available,
                                                          llm_per_source):
        sc = deploy(n_sources=3)
        sources_available(n=3)
        llm_per_source(['{"state": "NONSENSE"}'] * 3)
        with pytest.raises(Exception):
            sc.resolve()
        llm_per_source([value("2026-03-11")] * 3)
        assert sc.resolve()["status"] == "CONFIRMED"


class TestCanonicalRecord:
    def test_record_is_key_sorted_json(self, deploy, sources_available, llm_per_source):
        import json

        sc = deploy(n_sources=3)
        sources_available(n=3)
        llm_per_source([value("2026-03-11")] * 3)
        sc.resolve()
        rec = json.loads(sc.get_record())
        assert list(rec) == sorted(rec)

    def test_record_carries_only_decision_fields(self, deploy, sources_available, llm_per_source):
        import json

        sc = deploy(n_sources=3)
        sources_available(n=3)
        llm_per_source([value("2026-03-11")] * 3)
        sc.resolve()
        rec = json.loads(sc.get_record())
        assert set(rec) == {
            "v", "configuration_hash", "query_id", "fact_type", "status", "normalized_value",
            "supporting_source_indices", "conflicting_source_indices",
            "unavailable_source_indices", "ambiguous_source_indices", "resolved_at",
        }

    def test_record_excludes_prose_and_identity(self, deploy, sources_available, llm_per_source):
        sc = deploy(n_sources=3)
        sources_available(n=3)
        llm_per_source([value("2026-03-11")] * 3)
        sc.resolve()
        rec = sc.get_record()
        for leaked in ("reasoning", "question", "url", "deployer", "submitter", "model",
                       "validator", "http"):
            assert leaked not in rec, f"{leaked!r} leaked into the canonical record"

    def test_repeated_reads_are_byte_identical(self, deploy, sources_available, llm_per_source):
        """A view that rebuilt the record per call could reorder it; this catches that.

        Byte-level determinism against an independent implementation is asserted in
        tests/direct/test_parity.py, which is the stronger claim.
        """
        sc = deploy(n_sources=3)
        sources_available(n=3)
        llm_per_source([value("2026-03-11")] * 3)
        sc.resolve()
        assert sc.get_record() == sc.get_record() == sc.get_result()["record"]

    def test_record_omits_no_value_indices_by_design(self, deploy, sources_available,
                                                     llm_per_source):
        """`no_value` is derivable from the other three plus the source count, so it is not
        stored -- the record carries the minimum that reproduces the decision."""
        import json

        sc = deploy(n_sources=3)
        sources_available(n=3)
        llm_per_source([value("2026-03-11"), value("2026-03-11"), NO_VALUE])
        sc.resolve()
        assert "no_value_source_indices" not in json.loads(sc.get_record())
        assert sc.get_result()["no_value_source_indices"] == [2], "still readable from get_result"
