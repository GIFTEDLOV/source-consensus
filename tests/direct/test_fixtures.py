"""The nine Stage 1 fixtures, driven end to end through the real contract.

The fixtures were written before the contract existed and their expected statuses are recomputed
by `tools/canonical.py` rather than hardcoded (`tools/validate_fixtures.py`). Running them through
the contract closes the loop: the corpus, the reference implementation and the contract must all
agree, and any two of them agreeing is not enough.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from tools.canonical import configuration_hash, derive_status  # noqa: E402

CASES = sorted((ROOT / "fixtures" / "cases").glob("*.json"))
assert CASES, "no fixture cases found"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def response_for(result: dict) -> str:
    """The model response a correct extraction would produce for one source."""
    state = result["state"]
    if state == "VALUE":
        return json.dumps({"state": "VALUE", "value": result["value"]})
    if state == "UNAVAILABLE":
        # Never produced by the model -- the contract determines it from a failed fetch. The web
        # mock returns 404 for these, so this response is never reached.
        return json.dumps({"state": "NO_VALUE"})
    return json.dumps({"state": state})


@pytest.mark.parametrize("path", CASES, ids=[p.stem for p in CASES])
class TestFixtureCases:
    def test_contract_derives_the_expected_status(self, path, direct_deploy, direct_vm):
        case = load(path)
        cfg = case["config"]
        results = sorted(case["source_results"], key=lambda r: r["source_index"])

        sc = direct_deploy(
            "contracts/source_consensus.py",
            cfg["query_id"], cfg["question"], cfg["fact_type"], cfg["source_urls"],
            cfg["minimum_supporting_sources"], cfg["conflict_threshold"],
            cfg["normalization_rules"], cfg["allowed_enum_values"],
            cfg["require_pinned_evidence"],
        )

        # Mock each configured URL: available unless the fixture declares it UNAVAILABLE.
        for i, url in enumerate(cfg["source_urls"]):
            tail = url.rsplit("/", 1)[-1].replace(".", r"\.")
            if results[i]["state"] == "UNAVAILABLE":
                direct_vm.mock_web(rf".*{tail}", {"status": 404, "body": ""})
            else:
                direct_vm.mock_web(rf".*{tail}", {"status": 200, "body": f"source {i} body"})
        direct_vm.mock_web(r".*", {"status": 404, "body": ""})

        def handler(data):
            prompt = data.get("prompt", "")
            for i in range(len(cfg["source_urls"])):
                if f"SOURCE_INDEX: {i}\n" in prompt:
                    return {"ok": response_for(results[i])}
            raise AssertionError("prompt carries no SOURCE_INDEX marker")

        direct_vm._live_llm_handler = handler

        got = sc.resolve()
        assert got["status"] == case["expected"]["status"], case.get("notes", "")
        assert got["normalized_value"] == case["expected"]["normalized_value"]

    def test_contract_matches_the_reference_index_sets(self, path, direct_deploy, direct_vm):
        case = load(path)
        cfg = case["config"]
        results = sorted(case["source_results"], key=lambda r: r["source_index"])
        n = len(cfg["source_urls"])

        want = derive_status(results, cfg["minimum_supporting_sources"],
                             cfg["conflict_threshold"], n)

        sc = direct_deploy(
            "contracts/source_consensus.py",
            cfg["query_id"], cfg["question"], cfg["fact_type"], cfg["source_urls"],
            cfg["minimum_supporting_sources"], cfg["conflict_threshold"],
            cfg["normalization_rules"], cfg["allowed_enum_values"],
            cfg["require_pinned_evidence"],
        )
        for i, url in enumerate(cfg["source_urls"]):
            tail = url.rsplit("/", 1)[-1].replace(".", r"\.")
            if results[i]["state"] == "UNAVAILABLE":
                direct_vm.mock_web(rf".*{tail}", {"status": 404, "body": ""})
            else:
                direct_vm.mock_web(rf".*{tail}", {"status": 200, "body": f"source {i} body"})
        direct_vm.mock_web(r".*", {"status": 404, "body": ""})

        def handler(data):
            prompt = data.get("prompt", "")
            for i in range(n):
                if f"SOURCE_INDEX: {i}\n" in prompt:
                    return {"ok": response_for(results[i])}
            raise AssertionError("no SOURCE_INDEX")

        direct_vm._live_llm_handler = handler
        got = sc.resolve()

        for k in ("supporting_source_indices", "conflicting_source_indices",
                  "unavailable_source_indices", "ambiguous_source_indices"):
            assert got[k] == want[k], f"{k} differs from the reference implementation"

    def test_configuration_hash_matches_the_reference(self, path, direct_deploy, direct_vm):
        case = load(path)
        cfg = case["config"]
        sc = direct_deploy(
            "contracts/source_consensus.py",
            cfg["query_id"], cfg["question"], cfg["fact_type"], cfg["source_urls"],
            cfg["minimum_supporting_sources"], cfg["conflict_threshold"],
            cfg["normalization_rules"], cfg["allowed_enum_values"],
            cfg["require_pinned_evidence"],
        )
        assert sc.configuration_hash() == configuration_hash(cfg)


class TestFixtureCoverage:
    """The corpus must keep exercising what it claims to."""

    def test_all_four_statuses_are_covered(self):
        statuses = {load(p)["expected"]["status"] for p in CASES}
        assert statuses == {"CONFIRMED", "CONFLICTED", "INSUFFICIENT_EVIDENCE", "UNAVAILABLE"}

    def test_every_source_state_is_exercised(self):
        states = {r["state"] for p in CASES for r in load(p)["source_results"]}
        assert states == {"VALUE", "NO_VALUE", "UNAVAILABLE", "AMBIGUOUS"}

    def test_every_case_is_commit_pinned(self):
        import re

        pinned = re.compile(r"^https://raw\.githubusercontent\.com/[^/]+/[^/]+/[0-9a-f]{40}/")
        for p in CASES:
            for url in load(p)["config"]["source_urls"]:
                assert pinned.match(url), f"{p.stem}: unpinned source {url}"

    def test_case_ids_are_unique_and_match_filenames(self):
        ids = [load(p)["id"] for p in CASES]
        assert len(ids) == len(set(ids))
        assert ids == [p.stem for p in CASES]
