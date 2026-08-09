from pathlib import Path

import pytest

from tools.make_deployable import build


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "contracts" / "source_consensus.py"
HEADER = '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }'


def test_deployable_preserves_runner_header_and_ast(tmp_path):
    target = tmp_path / "source_consensus_deployable.py"
    build(CANONICAL, target)
    raw = target.read_bytes()
    assert raw.startswith((HEADER + "\n").encode("ascii"))
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in raw
    assert raw[:1] == b"#"


@pytest.mark.parametrize(
    "prefix",
    [
        "\ufeff",
        " ",
        "\n",
        "# a comment\n",
    ],
)
def test_deployable_rejects_anything_before_runner_header(tmp_path, prefix):
    source = tmp_path / "bad.py"
    source.write_text(prefix + HEADER + "\nfrom genlayer import *\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="runner header|BOM"):
        build(source, tmp_path / "out.py")


def test_ci_build_reads_canonical_and_writes_the_deployable_artifact():
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "python tools/make_deployable.py contracts/source_consensus.py artifacts/source_consensus_deployable.py" in ci
