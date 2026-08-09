from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deploy" / "04_stage5_attempt4.js"


def test_stage5_deploy_script_passes_native_source_url_array_to_client():
    probe = """
import { constructorArgs, sourceUrls, assertConstructorTransport, submitDeployment } from './deploy/04_stage5_attempt4.js';
let received;
assertConstructorTransport();
const client = {
  deployContract: async ({ args }) => { received = args; return '0xmock'; },
};
assert(Array.isArray(constructorArgs));
assert(received === undefined);
assert(Array.isArray(sourceUrls));
assert(sourceUrls.every(value => typeof value === 'string'));
await submitDeployment(client, new Uint8Array([35]));
assert(received[3] === sourceUrls);
assert(Array.isArray(received[3]));
assert(received[3].length === 3);
console.log(JSON.stringify({ count: received.length, nestedArray: Array.isArray(received[3]), sameReference: received[3] === sourceUrls }));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", probe],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout.strip()) == {"count": 9, "nestedArray": True, "sameReference": True}


def test_stage5_deploy_script_has_no_constructor_serialization_path():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "client.deployContract({ code, args: constructorArgs })" in text
    assert "process.argv" not in text
    assert "sourceUrls = JSON.stringify" not in text
    assert "constructorArgs[3] === sourceUrls" in text
