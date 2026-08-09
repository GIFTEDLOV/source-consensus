import json
from pathlib import Path

import pytest

from tools.make_deployable import build
from tools.stage5_preflight import validate


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "contracts" / "source_consensus.py"
CONFIG = json.loads((ROOT / "examples/stage5-date-config.json").read_text(encoding="utf-8"))
EXPECTED_HASH = "0x14000a8af1488048755b93a32a7fa31ded90897e62d28aad875dc9a087d427cc"


def test_stage5_preflight_round_trips_all_constructor_types(tmp_path):
    artifact = tmp_path / "deployable.py"
    build(CANONICAL, artifact)
    result = validate(CANONICAL, artifact, CONFIG, EXPECTED_HASH)
    assert result["constructor_arg_count"] == 9
    assert result["constructor_types"] == ["str", "str", "str", "list", "int", "int", "dict", "list", "bool"]
    assert json.loads(result["cli_args"][3]) == CONFIG["source_urls"]


def test_stage5_preflight_rejects_a_bom(tmp_path):
    artifact = tmp_path / "bad.py"
    artifact.write_bytes(b"\xef\xbb\xbf" + CANONICAL.read_bytes())
    with pytest.raises(SystemExit, match="BOM"):
        validate(CANONICAL, artifact, CONFIG, EXPECTED_HASH)


def test_stage5_preflight_rejects_wrong_source_url_type(tmp_path):
    artifact = tmp_path / "deployable.py"
    build(CANONICAL, artifact)
    bad = dict(CONFIG, source_urls=CONFIG["source_urls"][0])
    with pytest.raises(SystemExit, match="source_urls must be a list"):
        validate(CANONICAL, artifact, bad, EXPECTED_HASH)


def test_stage5_preflight_requires_expected_configuration_hash(tmp_path):
    artifact = tmp_path / "deployable.py"
    build(CANONICAL, artifact)
    with pytest.raises(SystemExit, match="expected-configuration-hash is required"):
        validate(CANONICAL, artifact, CONFIG)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("source_urls", CONFIG["source_urls"][:1], "source_urls count"),
        ("source_urls", [f"https://example.com/{index}" for index in range(6)], "source_urls count"),
        ("source_urls", CONFIG["source_urls"] + [CONFIG["source_urls"][0]], "duplicate source"),
        ("minimum_supporting_sources", 4, "minimum_supporting_sources"),
        ("conflict_threshold", 6, "conflict_threshold"),
        ("source_urls", ["https://example.com/live"] * 3, "duplicate source"),
    ],
)
def test_stage5_preflight_mirrors_source_and_threshold_invariants(tmp_path, field, value, message):
    artifact = tmp_path / "deployable.py"
    build(CANONICAL, artifact)
    bad = dict(CONFIG, **{field: value})
    with pytest.raises(SystemExit, match=message):
        validate(CANONICAL, artifact, bad, EXPECTED_HASH)


def test_stage5_preflight_rejects_unpinned_sources_when_required(tmp_path):
    artifact = tmp_path / "deployable.py"
    build(CANONICAL, artifact)
    bad = dict(CONFIG, source_urls=["https://example.com/a", "https://example.com/b"])
    with pytest.raises(SystemExit, match="commit/content pinned"):
        validate(CANONICAL, artifact, bad, EXPECTED_HASH)
