import json
from pathlib import Path

import pytest

from tools.make_deployable import build
from tools.stage5_preflight import validate


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "contracts" / "source_consensus.py"
CONFIG = json.loads((ROOT / "examples/stage5-date-config.json").read_text(encoding="utf-8"))


def test_stage5_preflight_round_trips_all_constructor_types(tmp_path):
    artifact = tmp_path / "deployable.py"
    build(CANONICAL, artifact)
    result = validate(CANONICAL, artifact, CONFIG, "0x14000a8af1488048755b93a32a7fa31ded90897e62d28aad875dc9a087d427cc")
    assert result["constructor_arg_count"] == 9
    assert result["constructor_types"] == ["str", "str", "str", "list", "int", "int", "dict", "list", "bool"]
    assert json.loads(result["cli_args"][3]) == CONFIG["source_urls"]


def test_stage5_preflight_rejects_a_bom(tmp_path):
    artifact = tmp_path / "bad.py"
    artifact.write_bytes(b"\xef\xbb\xbf" + CANONICAL.read_bytes())
    with pytest.raises(SystemExit, match="BOM"):
        validate(CANONICAL, artifact, CONFIG)


def test_stage5_preflight_rejects_wrong_source_url_type(tmp_path):
    artifact = tmp_path / "deployable.py"
    build(CANONICAL, artifact)
    bad = dict(CONFIG, source_urls=CONFIG["source_urls"][0])
    with pytest.raises(SystemExit, match="constructor arg 3"):
        validate(CANONICAL, artifact, bad)
