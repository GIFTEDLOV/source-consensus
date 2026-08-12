"""The independent reference implementation, exercised without a VM.

`tools/canonical.py` was written from `docs/ARCHITECTURE.md` and `docs/DERIVATION.md` rather than
from the contract. These tests pin its behaviour on its own terms; `tests/direct/test_parity.py`
then asserts the contract agrees with it. Testing them separately is what makes the agreement
evidence rather than a tautology.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.canonical import (  # noqa: E402
    canonical_json,
    configuration_hash,
    derive_status,
    normalise_text,
    normalise_value,
)

BASE = {
    "query_id": "Q",
    "question": "What is the value?",
    "fact_type": "DATE",
    "normalization_rules": {},
    "allowed_enum_values": [],
    "source_urls": ["https://a.example/1", "https://b.example/2", "https://c.example/3"],
    "minimum_supporting_sources": 2,
    "conflict_threshold": 2,
    "require_pinned_evidence": False,
}


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


class TestTruthTable:
    """One test per row of docs/DERIVATION.md section 3, plus every worked row."""

    def test_row1_unreachable_dominates(self):
        r = derive((V, "A"), "UNAVAILABLE", "UNAVAILABLE")
        assert r["status"] == "UNAVAILABLE"
        assert r["normalized_value"] is None
        assert r["unavailable_source_indices"] == [1, 2]

    def test_row1_all_dead(self):
        assert derive("UNAVAILABLE", "UNAVAILABLE", "UNAVAILABLE")["status"] == "UNAVAILABLE"

    def test_row2_empty_tally(self):
        r = derive("NO_VALUE", "NO_VALUE", "NO_VALUE")
        assert r["status"] == "INSUFFICIENT_EVIDENCE"
        assert r["no_value_source_indices"] == [0, 1, 2]

    def test_row2_all_ambiguous(self):
        r = derive("AMBIGUOUS", "AMBIGUOUS", "AMBIGUOUS")
        assert r["status"] == "INSUFFICIENT_EVIDENCE"
        assert r["ambiguous_source_indices"] == [0, 1, 2]

    def test_row3_even_split(self):
        r = derive((V, "A"), (V, "A"), (V, "B"), (V, "B"))
        assert r["status"] == "CONFLICTED"
        assert r["normalized_value"] is None
        assert r["conflicting_source_indices"] == [0, 1, 2, 3]
        assert r["supporting_source_indices"] == []

    def test_row4_unanimous(self):
        r = derive((V, "A"), (V, "A"), (V, "A"))
        assert r["status"] == "CONFIRMED"
        assert r["normalized_value"] == "A"
        assert r["supporting_source_indices"] == [0, 1, 2]

    def test_row4_majority_with_outlier_below_threshold(self):
        r = derive((V, "A"), (V, "A"), (V, "A"), (V, "B"))
        assert r["status"] == "CONFIRMED"
        assert r["supporting_source_indices"] == [0, 1, 2]
        assert r["conflicting_source_indices"] == [3], "the outlier is recorded, not discarded"

    def test_row5_single_value_below_minimum(self):
        r = derive((V, "A"), "NO_VALUE", "NO_VALUE")
        assert r["status"] == "INSUFFICIENT_EVIDENCE"
        assert r["supporting_source_indices"] == []
        assert r["conflicting_source_indices"] == [0], "a near-miss is visible, not silent"


class TestPluralityIsNotConfirmation:
    """The single most important edge in the design (docs/DERIVATION.md section 4)."""

    def test_three_two_split_is_conflicted_not_confirmed(self):
        r = derive((V, "A"), (V, "A"), (V, "A"), (V, "B"), (V, "B"))
        assert r["status"] == "CONFLICTED", (
            "a 3-2 plurality must not confirm; reporting the dispute is the entire argument "
            "for this contract over an LLM that reconciles by prompt"
        )
        assert r["normalized_value"] is None

    def test_four_one_split_confirms_when_outlier_is_below_threshold(self):
        r = derive((V, "A"), (V, "A"), (V, "A"), (V, "A"), (V, "B"), conflict=2)
        assert r["status"] == "CONFIRMED"

    @pytest.mark.parametrize("ct,expected", [(1, "CONFLICTED"), (2, "CONFIRMED"), (3, "CONFIRMED")])
    def test_conflict_threshold_governs_a_lesser_competing_value(self, ct, expected):
        assert derive((V, "A"), (V, "A"), (V, "B"), conflict=ct)["status"] == expected


class TestTieAtTheTopIsAlwaysAConflict:
    """docs/DERIVATION.md section 3, the uniqueness clause.

    Regression cover for a real flaw: without it, a conflict_threshold set above the tied count
    left the lexicographic tie-break -- which exists only to pin determinism -- silently choosing
    the winner.
    """

    @pytest.mark.parametrize("ct", [1, 2, 3, 4])
    def test_a_dead_heat_never_confirms_at_any_threshold(self, ct):
        r = derive((V, "B"), (V, "B"), (V, "A"), (V, "A"), conflict=ct)
        assert r["status"] == "CONFLICTED", (
            f"a 2-2 tie confirmed at conflict_threshold={ct}; no threshold setting may turn a "
            "dead heat into an answer"
        )
        assert r["normalized_value"] is None

    def test_the_alphabetically_first_value_is_not_preferred(self):
        assert derive((V, "A"), (V, "A"), (V, "B"), (V, "B"), conflict=3)["normalized_value"] is None

    def test_a_three_way_tie_is_also_a_conflict(self):
        assert derive((V, "A"), (V, "B"), (V, "C"), conflict=3)["status"] == "CONFLICTED"

    def test_a_clear_leader_still_confirms(self):
        r = derive((V, "A"), (V, "A"), (V, "A"), (V, "B"), conflict=3)
        assert r["status"] == "CONFIRMED" and r["normalized_value"] == "A"


class TestBoundaries:
    @pytest.mark.parametrize("minimum,expected", [(2, "CONFIRMED"), (3, "INSUFFICIENT_EVIDENCE")])
    def test_minimum_support_boundary(self, minimum, expected):
        assert derive((V, "A"), (V, "A"), "NO_VALUE", minimum=minimum)["status"] == expected

    @pytest.mark.parametrize("dead,expected", [(1, "CONFIRMED"), (2, "UNAVAILABLE")])
    def test_reachability_boundary(self, dead, expected):
        pairs = [(V, "A"), (V, "A"), (V, "A")]
        for i in range(dead):
            pairs[2 - i] = "UNAVAILABLE"
        assert derive(*pairs, minimum=2)["status"] == expected


class TestDeterminism:
    def test_result_does_not_depend_on_input_order(self):
        """Two nodes must derive the same result from the same tally, however it is ordered."""
        a = derive((V, "B"), (V, "B"), (V, "A"), (V, "A"), conflict=3)
        b = derive((V, "A"), (V, "A"), (V, "B"), (V, "B"), conflict=3)
        assert a == b

    def test_index_sets_are_sorted(self):
        r = derive((V, "A"), "UNAVAILABLE", (V, "A"), "AMBIGUOUS", "NO_VALUE")
        for k in ("supporting_source_indices", "conflicting_source_indices",
                  "unavailable_source_indices", "ambiguous_source_indices",
                  "no_value_source_indices"):
            assert r[k] == sorted(r[k])

    def test_every_index_appears_exactly_once(self):
        r = derive((V, "A"), (V, "B"), "UNAVAILABLE", "AMBIGUOUS", "NO_VALUE")
        seen = (r["supporting_source_indices"] + r["conflicting_source_indices"]
                + r["unavailable_source_indices"] + r["ambiguous_source_indices"]
                + r["no_value_source_indices"])
        assert sorted(seen) == [0, 1, 2, 3, 4]


class TestNormalisation:
    @pytest.mark.parametrize("raw,expected", [
        ("2026-03-11", "2026-03-11"),
        ("2024-02-29", "2024-02-29"),
        ("2026-02-29", None),
        ("2026-02-30", None),
        ("2026-13-01", None),
        ("2026-00-10", None),
        ("0000-01-01", None),
        ("March 2026", None),
        ("2026-03", None),
        ("11/03/2026", None),
        ("", None),
    ])
    def test_date(self, raw, expected):
        assert normalise_value("DATE", raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("1200", "1200"), (1200, "1200"), ("-5", "-5"), ("0", "0"),
        ("1,200", None), ("1.0", None), ("1e3", None), ("+5", None),
        ("007", None), ("twelve", None), (1.5, None),
    ])
    def test_integer(self, raw, expected):
        assert normalise_value("INTEGER", raw) == expected

    def test_integer_bounds(self):
        rules = {"min_value": 0, "max_value": 100}
        assert normalise_value("INTEGER", "50", rules) == "50"
        assert normalise_value("INTEGER", "-1", rules) is None
        assert normalise_value("INTEGER", "101", rules) is None

    @pytest.mark.parametrize("raw,expected", [
        ("true", "true"), ("TRUE", "true"), ("yes", "true"), (True, "true"),
        ("false", "false"), ("no", "false"), (False, "false"),
        ("maybe", None), ("1", None), ("0", None),
    ])
    def test_boolean(self, raw, expected):
        assert normalise_value("BOOLEAN", raw) == expected

    def test_boolean_rejects_one_and_zero(self):
        """'1' is an integer, not a boolean. Accepting it would blur two fact types."""
        assert normalise_value("BOOLEAN", "1") is None

    def test_enum_exact_membership(self):
        rules = {"allowed_enum_values": ["YES", "NO"]}
        assert normalise_value("ENUM", "YES", rules) == "YES"
        assert normalise_value("ENUM", "yes", rules) is None
        assert normalise_value("ENUM", "MAYBE", rules) is None

    def test_enum_case_lower_maps_to_the_declared_spelling(self):
        rules = {"allowed_enum_values": ["Yes", "No"], "case_policy": "LOWER"}
        assert normalise_value("ENUM", "YES", rules) == "Yes"

    def test_string_length_bound(self):
        assert normalise_value("STRING", "x" * 200) == "x" * 200
        assert normalise_value("STRING", "x" * 201) is None

    def test_string_case_policy(self):
        assert normalise_value("STRING", "GA", {"case_policy": "LOWER"}) == "ga"
        assert normalise_value("STRING", "GA") == "GA"

    def test_whitespace_is_collapsed_so_surface_variation_is_one_value(self):
        assert normalise_value("STRING", "  a   b  ") == "a b"

    def test_no_float_survives_any_type(self):
        for t in ("STRING", "INTEGER", "BOOLEAN", "DATE", "ENUM"):
            assert normalise_value(t, 1.5, {"allowed_enum_values": ["1.5"]}) is None

    @pytest.mark.parametrize("fact_type,raw,rules", [
        ("DATE", 20260311, {}),
        ("STRING", 123, {}),
        ("STRING", True, {}),
        ("ENUM", 1, {"allowed_enum_values": ["1", "2"]}),
        ("ENUM", True, {"allowed_enum_values": ["true", "false"]}),
        ("BOOLEAN", 1, {}),
    ])
    def test_wrong_json_scalar_type_is_not_repaired(self, fact_type, raw, rules):
        assert normalise_value(fact_type, raw, rules) is None


class TestConfigurationHash:
    def test_deterministic(self):
        assert configuration_hash(BASE) == configuration_hash(dict(BASE))

    def test_source_order_changes_the_hash(self):
        """Indices are meaningful, so reordering sources is a DIFFERENT configuration."""
        swapped = dict(BASE)
        swapped["source_urls"] = [BASE["source_urls"][i] for i in (1, 0, 2)]
        assert configuration_hash(swapped) != configuration_hash(BASE)

    def test_enum_order_does_not_change_the_hash(self):
        """Enum membership is a set: the same values in a different order accept the same input."""
        a = dict(BASE, fact_type="ENUM", allowed_enum_values=["A", "B"])
        b = dict(BASE, fact_type="ENUM", allowed_enum_values=["B", "A"])
        assert configuration_hash(a) == configuration_hash(b)

    @pytest.mark.parametrize("field,newvalue", [
        ("query_id", "OTHER"),
        ("question", "A different question?"),
        ("fact_type", "STRING"),
        ("minimum_supporting_sources", 3),
        ("conflict_threshold", 1),
        ("require_pinned_evidence", True),
    ])
    def test_every_committed_field_changes_the_hash(self, field, newvalue):
        assert configuration_hash(dict(BASE, **{field: newvalue})) != configuration_hash(BASE)

    def test_normalization_rules_change_the_hash(self):
        a = dict(BASE, fact_type="INTEGER", normalization_rules={"min_value": 0})
        b = dict(BASE, fact_type="INTEGER", normalization_rules={"min_value": 1})
        assert configuration_hash(a) != configuration_hash(b)

    def test_enum_membership_changes_the_hash(self):
        a = dict(BASE, fact_type="ENUM", allowed_enum_values=["A", "B"])
        b = dict(BASE, fact_type="ENUM", allowed_enum_values=["A", "C"])
        assert configuration_hash(a) != configuration_hash(b)

    def test_source_identity_changes_the_hash(self):
        changed = dict(BASE, source_urls=[*BASE["source_urls"][:-1], "https://other.example/3"])
        assert configuration_hash(changed) != configuration_hash(BASE)

    def test_hash_is_0x_prefixed_keccak(self):
        h = configuration_hash(BASE)
        assert h.startswith("0x") and len(h) == 66


class TestCanonicalText:
    def test_crlf_and_cr_collapse(self):
        assert normalise_text("a\r\nb\rc") == "a b c"

    def test_control_characters_stripped(self):
        assert normalise_text("a\x00b\x1fc") == "abc"

    def test_json_is_key_sorted_and_tight(self):
        assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'
