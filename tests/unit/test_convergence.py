import json
import subprocess
import sys

from tools.convergence import load_cases, summarize


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


def test_full_payload_disagreement_is_not_reported_as_consensus():
    case = next(case for case in load_cases() if case["id"] == "01-all-agree")
    attempts = []
    for model_index, model in enumerate(("model-a", "model-b")):
        for result in case["source_results"]:
            parsed = {"state": result["state"], "value": result.get("value")}
            if model_index == 1 and result["source_index"] == 2:
                parsed = {"state": "NO_VALUE", "value": None}
            attempts.append({
                "model": model,
                "fixture": case["id"],
                "repeat": 0,
                "source_index": result["source_index"],
                "parsed_response": parsed,
                "rejection_category": None,
            })

    metrics = summarize(attempts)
    assert metrics["aggregate_status_agreement"] == {"n": 1, "N": 1}
    assert metrics["full_per_source_payload_agreement"] == {"n": 0, "N": 1}
    assert metrics["per_source_state_agreement"] == {"n": 2, "N": 3}
    assert metrics["supporting_set_agreement"] == {"n": 0, "N": 1}
    assert metrics["end_to_end_consensus_pass_rate"] == {"n": 0, "N": 1}
