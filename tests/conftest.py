"""Shared fixtures and builders for the SourceConsensus test suite.

Direct mode runs the contract in-process with mocked web and LLM responses, so every test here is
deterministic and offline. No network, no simulator, no LLM, no GEN.

The one thing worth understanding before reading a test: `llm_per_source` mocks a DIFFERENT
response per source URL. That is not convenience -- it is the only way to test a contract that
extracts each source in its own prompt, and a single catch-all mock would silently hide the
property the design rests on.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CONTRACT = "contracts/source_consensus.py"

PIN = "https://raw.githubusercontent.com/GIFTEDLOV/source-consensus/" + "a" * 40
MUTABLE = "https://example.invalid/live/page"


def pytest_configure(config):
    """Refuse to run while the contract may be mutated.

    `tools/mutation_test.py` edits the contract in place and restores it afterwards. A suite run
    that overlaps one reads a deliberately broken contract and reports failures that look real and
    are not -- and an edit made during a run is silently discarded when the tool restores its
    snapshot.
    """
    if os.environ.get("SC_MUTATION_RUNNER") == "1":
        # The mutation tool's own subprocesses must run THROUGH the lock -- that is the whole
        # point of the tool. Without this bypass every mutation scores "caught" for the wrong
        # reason (pytest refuses to start, the tool counts a non-zero exit as detection), which is
        # a false green.
        return

    lock = ROOT / ".mutation-in-progress"
    if lock.exists():
        raise pytest.UsageError(
            f"{lock.name} exists: tools/mutation_test.py is running and the contract on disk may "
            "be mutated. Wait for it to finish, or delete the lock if no run is active."
        )


def src(n: int) -> str:
    """A distinct commit-pinned source URL for index n."""
    return f"{PIN}/source-{n}.md"


def urls(n: int) -> list:
    return [src(i) for i in range(n)]


def response(state: str, value=None) -> str:
    """One source's model response, as raw JSON text."""
    body: dict = {"state": state, "value": value}
    return json.dumps(body)


def value(v) -> str:
    return response("VALUE", v)


NO_VALUE = response("NO_VALUE")
AMBIGUOUS = response("AMBIGUOUS")


@pytest.fixture
def deploy(direct_deploy):
    """Deploy a SourceConsensus with sensible defaults."""

    def _deploy(
        query_id="RELEASE_DATE",
        question="On what date was version 1.0 of the project released?",
        fact_type="DATE",
        source_urls=None,
        minimum_supporting_sources=2,
        conflict_threshold=2,
        normalization_rules=None,
        allowed_enum_values=None,
        require_pinned_evidence=False,
        n_sources=3,
    ):
        return direct_deploy(
            CONTRACT,
            query_id,
            question,
            fact_type,
            urls(n_sources) if source_urls is None else source_urls,
            minimum_supporting_sources,
            conflict_threshold,
            {} if normalization_rules is None else normalization_rules,
            [] if allowed_enum_values is None else allowed_enum_values,
            require_pinned_evidence,
        )

    return _deploy


@pytest.fixture
def sources_available(direct_vm):
    """Make every source fetch succeed, with per-source body text."""

    def _available(bodies=None, n=3, default="Source body text."):
        for i in range(n):
            body = default if bodies is None else bodies[i]
            if body is None:
                # A source that fails to fetch: no mock registered means the catch-all below
                # decides, so register an explicit failure instead.
                direct_vm.mock_web(rf".*source-{i}\.md", {"status": 404, "body": ""})
            else:
                direct_vm.mock_web(rf".*source-{i}\.md", {"status": 200, "body": body})
        direct_vm.mock_web(r".*", {"status": 404, "body": ""})

    return _available


@pytest.fixture
def llm_per_source(direct_vm):
    """Answer each source's prompt differently, keyed on the SOURCE_INDEX the prompt carries.

    The contract emits `SOURCE_INDEX: <i>` inside the fence, so matching on it proves the prompts
    really are per-source. A single catch-all mock would pass even if the contract concatenated
    every source into one prompt -- exactly the design property that must not regress.
    """
    captured: list = []

    def _llm(responses: list):
        def handler(data):
            prompt = data.get("prompt", "")
            captured.append(prompt)
            idx = None
            for i in range(len(responses)):
                if f"SOURCE_INDEX: {i}\n" in prompt:
                    idx = i
                    break
            if idx is None:
                raise AssertionError("prompt carries no SOURCE_INDEX marker")
            # Returned as RAW TEXT, which is what `exec_prompt` actually yields. Pre-parsing it
            # here would bypass the contract's own parser and hide every malformed-output path
            # the suite is supposed to exercise.
            return {"ok": responses[idx]}

        direct_vm._live_llm_handler = handler
        return captured

    return _llm


@pytest.fixture
def run(deploy, sources_available, llm_per_source):
    """Deploy, mock N sources as available, answer each with the given response, resolve."""

    def _run(responses: list, bodies=None, **kwargs):
        n = kwargs.pop("n_sources", len(responses))
        sc = deploy(n_sources=n, **kwargs)
        sources_available(bodies=bodies, n=n)
        llm_per_source(responses)
        return sc, sc.resolve()

    return _run
