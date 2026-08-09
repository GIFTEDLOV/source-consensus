import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { isDeepStrictEqual } from "node:util";

const ROOT = resolve(process.cwd());
export const DEPLOYABLE_PATH = resolve(ROOT, "artifacts/source_consensus_deployable.py");
export const EXPECTED_ARTIFACT_SHA256 =
  "a43e7aae4e12121b62a89961c0791f4361f897b4be43b47fdb4f28e44a481c39";
export const EXPECTED_HEADER =
  '# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }';
export const EXPECTED_SENDER = "0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7";
export const EXPECTED_CHAIN_ID = 4221;
export const EXPECTED_CONFIGURATION_HASH =
  "0x14000a8af1488048755b93a32a7fa31ded90897e62d28aad875dc9a087d427cc";
export const EXPECTED_DEPLOYMENT_FIXTURE = {
  queryId: "LEDGERINDEXER_2_0_0_RELEASE_DATE",
  question: "On what date was version 2.0.0 of LedgerIndexer officially released?",
  factType: "DATE",
  sourceUrls: [
    "https://raw.githubusercontent.com/GIFTEDLOV/source-consensus/7e58293b4b55fcf57dfc5e24d0d8a9f02e6c2d23/fixtures/corpus/01-all-agree/source-0-release-page.md",
    "https://raw.githubusercontent.com/GIFTEDLOV/source-consensus/7e58293b4b55fcf57dfc5e24d0d8a9f02e6c2d23/fixtures/corpus/01-all-agree/source-1-changelog.md",
    "https://raw.githubusercontent.com/GIFTEDLOV/source-consensus/7e58293b4b55fcf57dfc5e24d0d8a9f02e6c2d23/fixtures/corpus/01-all-agree/source-2-docs-announcement.md",
  ],
  minimumSupportingSources: 2,
  conflictThreshold: 2,
  normalizationRules: { case_policy: "PRESERVE" },
  allowedEnumValues: [],
  requirePinnedEvidence: true,
};
export const EXPECTED_SOURCE_SHA256 = [
  "32c795eb56f720b214d67313d3dc1a10ace0d42686b08cc57c141e38bfd30ddf",
  "8bc4de1b9fa70b1940a9fdaceb68265677c96117d160690629086c76135bdd05",
  "9bdc58c09d909c0f9476a35bc4e864f37182df22a0a5041b6f5a43196b3253b1",
];

export const sourceUrls = EXPECTED_DEPLOYMENT_FIXTURE.sourceUrls;
export const constructorArgs = [
  EXPECTED_DEPLOYMENT_FIXTURE.queryId,
  EXPECTED_DEPLOYMENT_FIXTURE.question,
  EXPECTED_DEPLOYMENT_FIXTURE.factType,
  sourceUrls,
  EXPECTED_DEPLOYMENT_FIXTURE.minimumSupportingSources,
  EXPECTED_DEPLOYMENT_FIXTURE.conflictThreshold,
  EXPECTED_DEPLOYMENT_FIXTURE.normalizationRules,
  EXPECTED_DEPLOYMENT_FIXTURE.allowedEnumValues,
  EXPECTED_DEPLOYMENT_FIXTURE.requirePinnedEvidence,
];

const ARGUMENT_TYPES = [
  "string",
  "string",
  "string",
  "Array<string>",
  "number",
  "number",
  "object",
  "Array<string>",
  "boolean",
];

function fail(message) {
  throw new Error(`Stage 5 attempt 4 preflight failed: ${message}`);
}

function assert(condition, message) {
  if (!condition) fail(message);
}

function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

export function assertConstructorTransport() {
  assert(Array.isArray(constructorArgs), "constructorArgs is not an Array");
  assert(constructorArgs.length === 9, `constructorArgs length is ${constructorArgs.length}`);
  assert(Array.isArray(sourceUrls), "sourceUrls is not an Array");
  assert(sourceUrls.every(value => typeof value === "string"), "sourceUrls contains a non-string");
  assert(constructorArgs[3] === sourceUrls, "constructorArgs[3] is not sourceUrls by reference");
  assert(typeof constructorArgs[3] !== "string", "source_urls was converted to a scalar string");
  assert(sourceUrls.length === 3, `sourceUrls length is ${sourceUrls.length}`);
  assert(constructorArgs[7].every(value => typeof value === "string"), "enum values are not strings");
  assert(typeof constructorArgs[0] === "string", "arg[0] is not string");
  assert(typeof constructorArgs[1] === "string", "arg[1] is not string");
  assert(typeof constructorArgs[2] === "string", "arg[2] is not string");
  assert(Number.isInteger(constructorArgs[4]), "arg[4] is not an integer");
  assert(Number.isInteger(constructorArgs[5]), "arg[5] is not an integer");
  assert(constructorArgs[6] && typeof constructorArgs[6] === "object" && !Array.isArray(constructorArgs[6]), "arg[6] is not a dict");
  assert(typeof constructorArgs[8] === "boolean", "arg[8] is not boolean");
  return true;
}

export function buildDeployableCode() {
  const bytes = readFileSync(DEPLOYABLE_PATH);
  assert(bytes.length === 47090, `deployable byte length is ${bytes.length}`);
  assert(bytes[0] === 0x23, "first byte is not '#'");
  assert(!(bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf), "UTF-8 BOM present");
  assert(!bytes.includes(0x0d), "CR line ending present");
  const firstLine = bytes.toString("utf8").split("\n", 1)[0];
  assert(firstLine === EXPECTED_HEADER, "Depends header is not exact line 1");
  const observed = sha256(bytes);
  assert(observed === EXPECTED_ARTIFACT_SHA256, `artifact sha256 is ${observed}`);
  return new Uint8Array(bytes);
}

function addressOf(client) {
  const account = client.account;
  return String(typeof account === "string" ? account : account?.address || "").toLowerCase();
}

function printArgumentTypes() {
  for (let index = 0; index < constructorArgs.length; index += 1) {
    console.log(`arg[${index}]: ${ARGUMENT_TYPES[index]}`);
  }
}

export async function preTransactionGate(client) {
  const code = buildDeployableCode();
  assertConstructorTransport();
  const sender = addressOf(client);
  assert(sender === EXPECTED_SENDER, `sender is ${sender}`);
  assert(Number(client.chain?.id) === EXPECTED_CHAIN_ID, `chain id is ${client.chain?.id}`);
  assert(/bradbury/i.test(String(client.chain?.name || client.chain?.id)), "network is not Bradbury");
  const balance = await client.getBalance({ address: sender });
  const nonce = await client.getCurrentNonce({ address: sender });
  console.log("PRE-TRANSACTION GATE");
  console.log("network: Bradbury PASS");
  console.log(`chain_id: ${client.chain.id} PASS`);
  console.log(`sender: ${sender} PASS`);
  console.log(`nonce: ${nonce}`);
  console.log(`balance_wei: ${balance}`);
  console.log(`artifact: ${DEPLOYABLE_PATH}`);
  console.log(`artifact_sha256: ${EXPECTED_ARTIFACT_SHA256} PASS`);
  console.log("first_byte: # PASS");
  console.log("bom: absent PASS");
  console.log(`depends_line_1: ${EXPECTED_HEADER} PASS`);
  console.log("bytes: 47090 PASS");
  console.log("ast_equivalence: supplied by make_deployable/preflight PASS");
  console.log("constructor_arg_count: 9 PASS");
  printArgumentTypes();
  console.log("source_urls Array.isArray: true PASS");
  console.log("source_urls elements: string PASS");
  console.log("source_urls nested native array: true PASS");
  console.log("native transport: client.deployContract({ code, args: constructorArgs }) PASS");
  return { code, sender, balance: String(balance), nonce, args: constructorArgs };
}

export async function submitDeployment(client, code) {
  assertConstructorTransport();
  return client.deployContract({ code, args: constructorArgs });
}

function transactionAddress(receipt) {
  return receipt.data?.contract_address || receipt.txDataDecoded?.contractAddress;
}

function executionResult(receipt) {
  return receipt.txExecutionResultName || receipt.executionResultName || receipt.consensus_data?.leader_receipt?.[0]?.execution_result;
}

function requireSuccessfulReceipt(receipt, phase) {
  const consensus = receipt.resultName || receipt.consensusStatusName || receipt.status_name;
  const execution = executionResult(receipt);
  if (consensus && consensus !== "AGREE") fail(`${phase} consensus is ${consensus}`);
  if (execution !== "FINISHED_WITH_RETURN" && execution !== "SUCCESS") {
    fail(`${phase} execution is ${execution || "unknown"}`);
  }
}

async function read(client, address, functionName) {
  return client.readContract({ address, functionName, args: [] });
}

function expectedConfig(sender) {
  return {
    schema_version: 1,
    query_id: EXPECTED_DEPLOYMENT_FIXTURE.queryId,
    question: EXPECTED_DEPLOYMENT_FIXTURE.question,
    fact_type: EXPECTED_DEPLOYMENT_FIXTURE.factType,
    case_policy: "PRESERVE",
    min_value: null,
    max_value: null,
    allowed_enum_values: [],
    source_count: sourceUrls.length,
    minimum_supporting_sources: EXPECTED_DEPLOYMENT_FIXTURE.minimumSupportingSources,
    conflict_threshold: EXPECTED_DEPLOYMENT_FIXTURE.conflictThreshold,
    require_pinned_evidence: EXPECTED_DEPLOYMENT_FIXTURE.requirePinnedEvidence,
    deployer: sender,
    resolved: false,
    attempts: 0,
    configuration_hash: EXPECTED_CONFIGURATION_HASH,
  };
}

export async function verifyInitialization(client, address, sender) {
  const config = await read(client, address, "get_config");
  const normalized = { ...config, deployer: String(config.deployer).toLowerCase() };
  assert(isDeepStrictEqual(normalized, expectedConfig(sender)), "get_config does not match constructor configuration");
  const sources = await read(client, address, "get_sources");
  assert(sources.length === sourceUrls.length, "get_sources count mismatch");
  for (let index = 0; index < sourceUrls.length; index += 1) {
    assert(sources[index].url === sourceUrls[index], `get_sources URL mismatch at ${index}`);
    assert(sources[index].state === "" && sources[index].value === "", `source ${index} is not initially empty`);
  }
  assert(await read(client, address, "configuration_hash") === EXPECTED_CONFIGURATION_HASH, "configuration_hash mismatch");
  assert((await read(client, address, "is_resolved")) === false, "contract is initially resolved");
  console.log("get_config: every observable field PASS");
  console.log("get_sources: pinned URLs and empty initial state PASS");
  console.log(`configuration_hash: ${EXPECTED_CONFIGURATION_HASH} PASS`);
  console.log("is_resolved: false PASS");
  return config;
}

async function verifyPinnedSources() {
  for (let index = 0; index < sourceUrls.length; index += 1) {
    const response = await fetch(sourceUrls[index]);
    assert(response.ok, `source ${index} returned HTTP ${response.status}`);
    const bytes = new Uint8Array(await response.arrayBuffer());
    const observed = sha256(bytes);
    assert(observed === EXPECTED_SOURCE_SHA256[index], `source ${index} hash mismatch`);
    console.log(`source[${index}] pinned bytes/hash PASS`);
  }
}

export async function resolveFixture(client, address, sender) {
  await verifyPinnedSources();
  const tx = await client.writeContract({ address, functionName: "resolve", args: [], value: 0n });
  writeFileSync(resolve(ROOT, "artifacts/stage5-attempt4-resolve.json"), JSON.stringify({ transaction: tx, address, sender }, null, 2) + "\n");
  console.log(`resolve transaction: ${tx}`);
  const receipt = await client.waitForTransactionReceipt({ hash: tx, retries: 200, interval: 5000 });
  requireSuccessfulReceipt(receipt, "resolve");
  const status = await read(client, address, "status");
  const value = await read(client, address, "value");
  const result = await read(client, address, "get_result");
  const record = await read(client, address, "get_record");
  assert(status === "CONFIRMED", `final status is ${status}`);
  assert(value === "2026-03-11", `final value is ${value}`);
  assert(result.status === status && result.normalized_value === value, "get_result is inconsistent");
  const parsedRecord = JSON.parse(record);
  assert(parsedRecord.configuration_hash === EXPECTED_CONFIGURATION_HASH, "record configuration hash mismatch");
  assert(parsedRecord.status === status && parsedRecord.normalized_value === value, "canonical record mismatch");
  assert(isDeepStrictEqual(parsedRecord.supporting_source_indices, [0, 1, 2]), "supporting bucket mismatch");
  assert(isDeepStrictEqual(parsedRecord.conflicting_source_indices, []), "conflicting bucket mismatch");
  assert((await read(client, address, "configuration_hash")) === EXPECTED_CONFIGURATION_HASH, "configuration hash changed");
  assert((await read(client, address, "is_resolved")) === true, "contract is not resolved");
  return { tx, receipt, status, value, result, record };
}

export default async function main(client) {
  const gate = await preTransactionGate(client);
  await client.initializeConsensusSmartContract();
  const transaction = await submitDeployment(client, gate.code);
  writeFileSync(resolve(ROOT, "artifacts/stage5-attempt4-deployment.json"), JSON.stringify({ transaction, sender: gate.sender, nonce: gate.nonce, balance: gate.balance }, null, 2) + "\n");
  console.log(`deployment transaction: ${transaction}`);
  const receipt = await client.waitForTransactionReceipt({ hash: transaction, retries: 200, interval: 5000 });
  requireSuccessfulReceipt(receipt, "deployment");
  const address = transactionAddress(receipt);
  assert(address, "deployment address missing from receipt");
  console.log(`deployment address: ${address}`);
  await verifyInitialization(client, address, gate.sender);
  const result = await resolveFixture(client, address, gate.sender);
  console.log("Stage 5 deployment and resolve completed", { transaction, address, result });
}
