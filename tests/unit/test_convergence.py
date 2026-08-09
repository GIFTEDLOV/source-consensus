import json
import subprocess
import sys


def test_offline_convergence_validation_without_key(tmp_path):
    report = tmp_path / "report.json"
    result = subprocess.run([sys.executable, "tools/convergence.py", "--report", str(report)],
                            capture_output=True, text=True, check=True)
    data = json.loads(report.read_text(encoding="utf-8"))
    assert data["mode"] == "offline"
    assert len(data["fixtures"]) == 9
    assert all(item["pass"] for item in data["fixtures"])
    assert all(item["pass"] for item in data["adversarial"])
    assert "not-run" in data["network_measurement"]
