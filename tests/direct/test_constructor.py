"""Constructor validation. Every bound rejects, and rejects with a distinct message.

A constructor that accepts a bad configuration produces an instance that is wrong for its whole
life -- there is no setter to fix it and `configuration_hash` has already committed to the mistake.
So every rule is tested for rejection, not merely documented.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tests.conftest import MUTABLE, src, urls  # noqa: E402

PINNED = urls(3)


class TestQueryId:
    def test_valid(self, deploy):
        assert deploy(query_id="RELEASE_DATE").get_config()["query_id"] == "RELEASE_DATE"

    @pytest.mark.parametrize("bad", ["lowercase", "1STARTS_WITH_DIGIT", "HAS-DASH", "HAS SPACE",
                                     "_LEADING", ""])
    def test_rejected(self, deploy, bad):
        with pytest.raises(Exception):
            deploy(query_id=bad)

    def test_too_long(self, deploy):
        with pytest.raises(Exception):
            deploy(query_id="A" * 65)


class TestQuestion:
    def test_empty_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(question="")

    def test_too_long_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(question="x" * 301)


class TestFactType:
    @pytest.mark.parametrize("t", ["STRING", "INTEGER", "BOOLEAN", "DATE"])
    def test_accepted(self, deploy, t):
        assert deploy(fact_type=t).get_config()["fact_type"] == t

    def test_enum_accepted_with_values(self, deploy):
        sc = deploy(fact_type="ENUM", allowed_enum_values=["YES", "NO"])
        assert sc.get_config()["allowed_enum_values"] == ["YES", "NO"]

    @pytest.mark.parametrize("bad", ["FLOAT", "date", "", "OBJECT", "NUMBER"])
    def test_rejected(self, deploy, bad):
        with pytest.raises(Exception):
            deploy(fact_type=bad)


class TestSourceCount:
    @pytest.mark.parametrize("n", [2, 3, 4, 5])
    def test_accepted(self, deploy, n):
        assert deploy(n_sources=n).get_config()["source_count"] == n

    def test_one_source_rejected(self, deploy):
        """Below two there is no cross-source agreement, which is the entire point."""
        with pytest.raises(Exception):
            deploy(source_urls=[src(0)])

    def test_zero_sources_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(source_urls=[])

    def test_six_sources_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(n_sources=6)


class TestSourceUrls:
    def test_duplicate_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(source_urls=[src(0), src(1), src(0)])

    def test_adjacent_duplicate_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(source_urls=[src(0), src(0)])

    @pytest.mark.parametrize("bad", [
        "http://insecure.example/x",
        "ftp://old.example/x",
        "not-a-url",
        "https://",
        "https:// space.example/x",
        "https://user:pw@example.com/x",
        "",
    ])
    def test_malformed_rejected(self, deploy, bad):
        with pytest.raises(Exception):
            deploy(source_urls=[src(0), bad])

    def test_too_long_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(source_urls=[src(0), "https://e.example/" + "x" * 400])

    def test_url_class_is_recorded(self, deploy):
        sc = deploy(source_urls=[src(0), MUTABLE])
        classes = [s["url_class"] for s in sc.get_sources()]
        assert classes == ["PINNED", "MUTABLE"]


class TestRequirePinnedEvidence:
    def test_mutable_rejected_when_required(self, deploy):
        with pytest.raises(Exception):
            deploy(source_urls=[src(0), MUTABLE], require_pinned_evidence=True)

    def test_mutable_accepted_when_not_required(self, deploy):
        sc = deploy(source_urls=[src(0), MUTABLE], require_pinned_evidence=False)
        assert sc.get_config()["require_pinned_evidence"] is False

    def test_all_pinned_accepted_when_required(self, deploy):
        sc = deploy(n_sources=3, require_pinned_evidence=True)
        assert sc.get_config()["require_pinned_evidence"] is True

    @pytest.mark.parametrize("url", [
        "https://raw.githubusercontent.com/o/r/main/file.md",
        "https://raw.githubusercontent.com/o/r/" + "a" * 39 + "/file.md",
        "https://github.com/o/r/blob/main/file.md",
        "https://github.com/o/r/blob/v1.0.0/file.md",
    ])
    def test_branch_tag_and_short_hash_urls_cannot_masquerade_as_pinned(self, deploy, url):
        with pytest.raises(Exception):
            deploy(source_urls=[src(0), url], require_pinned_evidence=True)

    def test_exact_github_commit_url_is_pinned(self, deploy):
        url = "https://github.com/o/r/blob/" + "b" * 40 + "/file.md"
        sc = deploy(source_urls=[src(0), url], require_pinned_evidence=True)
        assert [source["url_class"] for source in sc.get_sources()] == ["PINNED", "PINNED"]


class TestThresholds:
    def test_minimum_below_floor_rejected(self, deploy):
        """One source agreeing with itself is not consensus."""
        with pytest.raises(Exception):
            deploy(minimum_supporting_sources=1)

    def test_minimum_zero_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(minimum_supporting_sources=0)

    def test_minimum_exceeding_source_count_rejected(self, deploy):
        """Unsatisfiable by construction -- CONFIRMED could never be reached."""
        with pytest.raises(Exception):
            deploy(n_sources=3, minimum_supporting_sources=4)

    def test_minimum_equal_to_source_count_accepted(self, deploy):
        assert deploy(n_sources=3, minimum_supporting_sources=3) is not None

    def test_conflict_threshold_zero_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(conflict_threshold=0)

    def test_conflict_threshold_exceeding_source_count_rejected(self, deploy):
        """No competing value could ever reach it, so CONFLICTED would be unreachable."""
        with pytest.raises(Exception):
            deploy(n_sources=3, conflict_threshold=4)

    @pytest.mark.parametrize("bad", [True, False, 1.5, "2", None])
    def test_non_integer_thresholds_rejected(self, deploy, bad):
        with pytest.raises(Exception):
            deploy(minimum_supporting_sources=bad)

    def test_boolean_is_not_an_integer(self, deploy):
        """`isinstance(True, int)` is True in Python; accepting it would let True mean 1."""
        with pytest.raises(Exception):
            deploy(conflict_threshold=True)


class TestEnumValidation:
    def test_enum_without_values_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(fact_type="ENUM", allowed_enum_values=[])

    def test_enum_with_one_value_rejected(self, deploy):
        """One value is not a choice."""
        with pytest.raises(Exception):
            deploy(fact_type="ENUM", allowed_enum_values=["ONLY"])

    def test_too_many_enum_values_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(fact_type="ENUM", allowed_enum_values=[f"V{i}" for i in range(17)])

    def test_duplicate_enum_values_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(fact_type="ENUM", allowed_enum_values=["YES", "NO", "YES"])

    def test_duplicate_after_case_normalisation_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(fact_type="ENUM", allowed_enum_values=["Yes", "YES"],
                   normalization_rules={"case_policy": "LOWER"})

    def test_duplicate_after_whitespace_normalisation_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(fact_type="ENUM", allowed_enum_values=["A  B", "A B"])

    def test_oversized_enum_value_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(fact_type="ENUM", allowed_enum_values=["A", "x" * 65])

    def test_enum_values_on_non_enum_type_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(fact_type="STRING", allowed_enum_values=["A", "B"])


class TestNormalizationRules:
    def test_unknown_rule_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(normalization_rules={"strip_html": True})

    def test_invalid_case_policy_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(fact_type="STRING", normalization_rules={"case_policy": "UPPER"})

    def test_case_policy_on_date_rejected(self, deploy):
        """Case has no meaning for a date; accepting it would imply it does something."""
        with pytest.raises(Exception):
            deploy(fact_type="DATE", normalization_rules={"case_policy": "LOWER"})

    def test_bounds_on_non_integer_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(fact_type="DATE", normalization_rules={"min_value": 0})

    def test_inverted_bounds_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(fact_type="INTEGER", normalization_rules={"min_value": 10, "max_value": 5})

    def test_valid_integer_bounds_accepted(self, deploy):
        sc = deploy(fact_type="INTEGER", normalization_rules={"min_value": 0, "max_value": 100})
        cfg = sc.get_config()
        assert cfg["min_value"] == 0 and cfg["max_value"] == 100

    def test_float_bound_rejected(self, deploy):
        with pytest.raises(Exception):
            deploy(fact_type="INTEGER", normalization_rules={"min_value": 1.5})


class TestInitialState:
    def test_starts_unresolved(self, deploy):
        sc = deploy()
        assert sc.is_resolved() is False
        assert sc.status() == "UNRESOLVED"
        assert sc.value() == ""
        assert sc.get_record() == ""

    def test_index_sets_start_empty(self, deploy):
        r = deploy().get_result()
        for k in ("supporting_source_indices", "conflicting_source_indices",
                  "unavailable_source_indices", "ambiguous_source_indices"):
            assert r[k] == []

    def test_sources_are_stored_in_configured_order(self, deploy):
        sc = deploy(n_sources=4)
        got = [s["url"] for s in sc.get_sources()]
        assert got == urls(4), "index position IS the source_index"

    def test_deployer_recorded_without_privilege(self, deploy):
        cfg = deploy().get_config()
        assert cfg["deployer"].startswith("0x")

    def test_no_admin_surface_exists(self, deploy):
        """The boundary is enforced by the absence of code: there is no setter to call."""
        sc = deploy()
        for forbidden in ("set_sources", "set_question", "update_config", "transfer_ownership",
                          "pause", "upgrade", "add_source", "set_status"):
            assert not hasattr(sc, forbidden), f"unexpected mutator {forbidden}"
