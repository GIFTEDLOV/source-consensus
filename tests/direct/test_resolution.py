"""Resolution end to end: every fact type, every source state, every derivation branch.

These drive the real contract with mocked web and LLM responses, one mocked response per source
keyed on the `SOURCE_INDEX` marker the prompt carries -- so a contract that stopped extracting
sources independently would fail here rather than passing on a catch-all mock.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tests.conftest import AMBIGUOUS, NO_VALUE, response, value  # noqa: E402


class TestDerivationBranches:
    """One test per row of docs/DERIVATION.md, driven through the real contract."""

    def test_unanimous_confirms(self, run):
        sc, r = run([value("2026-03-11")] * 3)
        assert r["status"] == "CONFIRMED"
        assert r["normalized_value"] == "2026-03-11"
        assert r["supporting_source_indices"] == [0, 1, 2]
        assert r["conflicting_source_indices"] == []

    def test_majority_with_outlier_below_threshold_confirms(self, run):
        sc, r = run([value("2026-05-20"), value("2026-05-20"), value("2026-05-20"),
                     value("2026-05-18")])
        assert r["status"] == "CONFIRMED"
        assert r["supporting_source_indices"] == [0, 1, 2]
        assert r["conflicting_source_indices"] == [3], "the dissenter is recorded, not discarded"

    def test_two_competing_values_conflict(self, run):
        sc, r = run([value("2026-02-09"), value("2026-02-09"),
                     value("2026-02-16"), value("2026-02-16")])
        assert r["status"] == "CONFLICTED"
        assert r["normalized_value"] is None
        assert r["supporting_source_indices"] == []
        assert r["conflicting_source_indices"] == [0, 1, 2, 3]

    def test_insufficient_evidence_when_only_one_source_speaks(self, run):
        sc, r = run([NO_VALUE, NO_VALUE, value("2026-04-02")])
        assert r["status"] == "INSUFFICIENT_EVIDENCE"
        assert r["normalized_value"] is None
        assert r["no_value_source_indices"] == [0, 1]
        assert r["conflicting_source_indices"] == [2], "the near-miss is visible"

    def test_all_silent_is_insufficient(self, run):
        sc, r = run([NO_VALUE] * 3)
        assert r["status"] == "INSUFFICIENT_EVIDENCE"
        assert r["no_value_source_indices"] == [0, 1, 2]

    def test_all_ambiguous_is_insufficient(self, run):
        sc, r = run([AMBIGUOUS] * 3)
        assert r["status"] == "INSUFFICIENT_EVIDENCE"
        assert r["ambiguous_source_indices"] == [0, 1, 2]

    def test_one_dead_source_does_not_poison_a_clear_result(self, run):
        sc, r = run([value("2026-06-30"), value("2026-06-30"), NO_VALUE],
                    bodies=["a", "b", None])
        assert r["status"] == "CONFIRMED"
        assert r["unavailable_source_indices"] == [2]
        assert r["supporting_source_indices"] == [0, 1]

    def test_too_few_reachable_is_unavailable(self, run):
        sc, r = run([value("2026-06-30"), NO_VALUE, NO_VALUE], bodies=["a", None, None])
        assert r["status"] == "UNAVAILABLE"
        assert r["unavailable_source_indices"] == [1, 2]

    def test_all_dead_is_unavailable(self, run):
        sc, r = run([NO_VALUE] * 3, bodies=[None, None, None])
        assert r["status"] == "UNAVAILABLE"
        assert r["unavailable_source_indices"] == [0, 1, 2]


class TestPluralityMustNotConfirm:
    """The edge the whole design turns on (docs/DERIVATION.md section 4)."""

    def test_three_two_split_conflicts(self, run):
        sc, r = run([value("A"), value("A"), value("A"), value("B"), value("B")],
                    fact_type="STRING")
        assert r["status"] == "CONFLICTED", "a 3-2 plurality is a dispute, not a confirmation"
        assert r["normalized_value"] is None

    def test_dead_heat_conflicts_even_above_the_threshold(self, run):
        sc, r = run([value("A"), value("A"), value("B"), value("B")],
                    fact_type="STRING", conflict_threshold=3)
        assert r["status"] == "CONFLICTED", "no threshold may turn a tie into an answer"

    def test_a_clear_leader_still_confirms(self, run):
        sc, r = run([value("A"), value("A"), value("A"), value("B")],
                    fact_type="STRING", conflict_threshold=3)
        assert r["status"] == "CONFIRMED" and r["normalized_value"] == "A"


class TestFactTypes:
    def test_date(self, run):
        sc, r = run([value("2026-03-11")] * 2, fact_type="DATE")
        assert r["normalized_value"] == "2026-03-11"

    def test_date_surface_forms_are_the_models_job_to_canonicalise(self, run):
        """The contract accepts only YYYY-MM-DD; the prompt instructs conversion."""
        sc, r = run([value("2026-03-11")] * 2, fact_type="DATE")
        assert r["status"] == "CONFIRMED"

    def test_vague_date_must_be_reported_ambiguous_not_guessed(self, run):
        sc, r = run([value("2026-09-17"), AMBIGUOUS, AMBIGUOUS], fact_type="DATE")
        assert r["status"] == "INSUFFICIENT_EVIDENCE"
        assert r["ambiguous_source_indices"] == [1, 2]

    @pytest.mark.parametrize("bad", ["March 2026", "2026-02-30", "2026-13-01", "11/03/2026"])
    def test_non_canonical_date_is_rejected_not_repaired(self, run, bad):
        with pytest.raises(Exception):
            run([value(bad)] * 2, fact_type="DATE")

    def test_integer(self, run):
        sc, r = run([value("1200")] * 2, fact_type="INTEGER")
        assert r["normalized_value"] == "1200"

    def test_integer_accepts_a_json_number(self, run):
        sc, r = run([value(1200)] * 2, fact_type="INTEGER")
        assert r["normalized_value"] == "1200"

    def test_negative_integer(self, run):
        sc, r = run([value("-5")] * 2, fact_type="INTEGER")
        assert r["normalized_value"] == "-5"

    @pytest.mark.parametrize("bad", ["1,200", "1.0", "1e3", "007", "+5", "twelve"])
    def test_malformed_integer_rejected(self, run, bad):
        with pytest.raises(Exception):
            run([value(bad)] * 2, fact_type="INTEGER")

    def test_integer_out_of_range_rejected(self, run):
        with pytest.raises(Exception):
            run([value("500")] * 2, fact_type="INTEGER",
                normalization_rules={"min_value": 0, "max_value": 100})

    def test_integer_in_range_accepted(self, run):
        sc, r = run([value("50")] * 2, fact_type="INTEGER",
                    normalization_rules={"min_value": 0, "max_value": 100})
        assert r["normalized_value"] == "50"

    @pytest.mark.parametrize("raw,expected", [
        ("true", "true"), ("TRUE", "true"), ("yes", "true"),
        ("false", "false"), ("no", "false"), (True, "true"), (False, "false"),
    ])
    def test_boolean_canonicalisation(self, run, raw, expected):
        sc, r = run([value(raw)] * 2, fact_type="BOOLEAN")
        assert r["normalized_value"] == expected

    @pytest.mark.parametrize("bad", ["maybe", "1", "0", "yep"])
    def test_boolean_rejects_non_canonical(self, run, bad):
        with pytest.raises(Exception):
            run([value(bad)] * 2, fact_type="BOOLEAN")

    def test_enum_membership(self, run):
        sc, r = run([value("YES")] * 2, fact_type="ENUM", allowed_enum_values=["YES", "NO"])
        assert r["normalized_value"] == "YES"

    def test_enum_rejects_undeclared_value(self, run):
        with pytest.raises(Exception):
            run([value("MAYBE")] * 2, fact_type="ENUM", allowed_enum_values=["YES", "NO"])

    def test_enum_case_sensitive_by_default(self, run):
        with pytest.raises(Exception):
            run([value("yes")] * 2, fact_type="ENUM", allowed_enum_values=["YES", "NO"])

    def test_enum_case_lower_maps_to_declared_spelling(self, run):
        sc, r = run([value("YES")] * 2, fact_type="ENUM", allowed_enum_values=["Yes", "No"],
                    normalization_rules={"case_policy": "LOWER"})
        assert r["normalized_value"] == "Yes"

    def test_string(self, run):
        sc, r = run([value("v2.0.0")] * 2, fact_type="STRING")
        assert r["normalized_value"] == "v2.0.0"

    def test_string_case_lower(self, run):
        sc, r = run([value("GA")] * 2, fact_type="STRING",
                    normalization_rules={"case_policy": "LOWER"})
        assert r["normalized_value"] == "ga"

    def test_string_too_long_rejected(self, run):
        with pytest.raises(Exception):
            run([value("x" * 201)] * 2, fact_type="STRING")


class TestNormalisationPreventsFalseConflict:
    def test_whitespace_variation_is_one_value(self, run):
        """Without collapse, '  a b' and 'a  b' would be two answers and derive CONFLICTED."""
        sc, r = run([value("a b"), value("  a   b  ")], fact_type="STRING")
        assert r["status"] == "CONFIRMED"
        assert r["normalized_value"] == "a b"

    def test_case_lower_makes_variants_agree(self, run):
        sc, r = run([value("GA"), value("ga")], fact_type="STRING",
                    normalization_rules={"case_policy": "LOWER"})
        assert r["status"] == "CONFIRMED"

    def test_without_case_policy_variants_conflict(self, run):
        """The default is case-SENSITIVE, and that is visible rather than implicit."""
        sc, r = run([value("GA"), value("ga")], fact_type="STRING")
        assert r["status"] == "CONFLICTED"


class TestNoFloatsAnywhere:
    def test_float_value_rejected(self, run):
        with pytest.raises(Exception):
            run([json.dumps({"state": "VALUE", "value": 1.5})] * 2, fact_type="INTEGER")

    def test_float_rejected_for_every_fact_type(self, run):
        for t in ("STRING", "INTEGER", "DATE", "BOOLEAN"):
            with pytest.raises(Exception):
                run([json.dumps({"state": "VALUE", "value": 2.0})] * 2, fact_type=t)

    def test_no_float_appears_in_the_result(self, run):
        sc, r = run([value("1200")] * 2, fact_type="INTEGER")
        for v in r.values():
            assert not isinstance(v, float)


class TestResultConsistency:
    def test_status_value_and_result_agree(self, run):
        sc, r = run([value("2026-03-11")] * 3)
        assert sc.status() == r["status"] == "CONFIRMED"
        assert sc.value() == r["normalized_value"] == "2026-03-11"
        assert sc.is_resolved() is True

    def test_value_is_empty_string_when_not_confirmed(self, run):
        sc, r = run([value("A"), value("A"), value("B"), value("B")], fact_type="STRING")
        assert sc.status() == "CONFLICTED"
        assert sc.value() == "", "the cheap view never returns null"
        assert r["normalized_value"] is None

    def test_every_index_appears_in_exactly_one_set(self, run):
        sc, r = run([value("A"), value("B"), NO_VALUE, AMBIGUOUS], fact_type="STRING",
                    bodies=["a", "b", "c", "d"])
        seen = (r["supporting_source_indices"] + r["conflicting_source_indices"]
                + r["unavailable_source_indices"] + r["ambiguous_source_indices"]
                + r["no_value_source_indices"])
        assert sorted(seen) == [0, 1, 2, 3]

    def test_get_sources_reflects_the_resolution(self, run):
        sc, r = run([value("2026-03-11"), value("2026-03-11"), NO_VALUE])
        states = [s["state"] for s in sc.get_sources()]
        assert states == ["VALUE", "VALUE", "NO_VALUE"]
        assert sc.get_sources()[0]["value"] == "2026-03-11"
        assert sc.get_sources()[2]["value"] == ""

    def test_config_reports_resolution_progress(self, run):
        sc, r = run([value("2026-03-11")] * 2)
        cfg = sc.get_config()
        assert cfg["resolved"] is True
        assert cfg["attempts"] == 1
