# Deployment

> Attempt 4 and `v1.0.0-bradbury` are
> `SUPERSEDED_AFTER_STEWARD_CONSENSUS_BINDING_REVIEW`. Their records below remain historical and are
> not altered or reused. The corrected deployment must be a new schema-version-2 instance from a
> new exact-head artifact after every gate in this document passes.

This document contains the pre-transaction procedure and the recorded Stage 5 attempts. The first
three attempts failed and remain preserved; the native deploy-script attempt 4 produced a usable
initialized contract and the single planned resolve transaction.

Target network: GenLayer Bradbury, chain ID `4221`. Before signing, verify the Bradbury RPC,
account provenance and balance, the final audited source hash, `genvm-lint check` and `validate`,
all tests and mutations, fixture and parity checks, and the source-size ceiling. Use one clean
canonical constructor configuration with three commit-pinned sources and an offline expected
`configuration_hash`. Deploy exactly one instance and persist the transaction hash immediately.

After finalization require `FINALIZED`, `FINISHED_WITH_RETURN`, deployed code, matching deployable
artifact hash, correct `get_config()` and `get_sources()`, matching `configuration_hash()`, and
`is_resolved() == false`. Re-fetch evidence, then perform exactly one `resolve()`. Verify its
finalized result, canonical record, all source buckets, unchanged configuration hash, validator
votes, and GEN cost. The Explorer URL will be recorded as
`https://explorer-bradbury.genlayer.com/contract/<address>` after deployment.

## Corrected-release gate

Before any new broadcast require a clean worktree, local HEAD equal to `origin/main`, green CI for
that exact commit, full tests and mutations green, GenVM lint and semantic validation green, fixture
and evidence URL checks green, deterministic deployable regeneration, recorded source/artifact
hashes and bytes, native typed constructor arguments, current Bradbury chain ID/RPC, expected sender,
and sufficient GEN. Stop on any mismatch. Wait for `FINALIZED`, not merely `ACCEPTED`, for both the
new deployment and the single corrected `resolve()`.

The successful historical native script is the transport pattern. A corrected script must use a new
filename and expected schema-v2 configuration hash; `deploy/04_stage5_attempt4.js` remains frozen as
historical v1 evidence.

## Steward-remediated deployment and resolution

Exact-head commit `f818e9c6dc16f72e01a25baa2d8acdc750bfe16e` passed CI run `31593257570`.
To prevent the installed CLI from executing every historical file in `deploy/`, only the corrected
script, `package.json`, and exact deployable were copied to an isolated temporary staging directory.
The old script was neither edited nor replayed.

- deployable: 51,585 bytes; SHA-256 `e0a732644683c8af6c15cdd781ef85c98eacddcb0febbec5df1fd6d1209796b9`;
- deployment transaction/address: `0x6404c2364b5ba936ea891febb89a9365930cdbe3d77a97b31871b8e0bd7a745b` /
  `0x2084107B5274FB82FDE29Bbe4794517309AdE2b9`;
- deployment: `FINALIZED`, round 0, 5/5 `AGREE`, no rotations, `FINISHED_WITH_RETURN`;
- deployed bytes: exact 51,585-byte/SHA-256 match;
- configuration hash: `0x33d4880006e882e213ba73cb2bbbb223b01eb5d5808eadaf3054ab807fed9955`;
- single resolve: `0x678630dbae18b324cfdf46df25230e68ec8b28067e05373cdc463d2247c182c8`;
- resolution: `FINALIZED`, round 0, 3 `AGREE`, 2 `TIMEOUT`, no rotations,
  `FINISHED_WITH_RETURN`; final `CONFIRMED / 2026-03-11`.

Every finalized source was `VALUE/2026-03-11`. Independent schema-v2 derivation reproduced
supporting `[0,1,2]`, all other sets empty, and the exact canonical record stored on chain.

## Attempt Record

The canonical source was rejected by Bradbury with `BlockPubdataLimitReached`. The reproducible
`tools/make_deployable.py` build removed only comments/docstrings, proved AST equivalence, and reduced
the source from 55,630 to 47,090 bytes. The first generated artifact omitted the required GenVM
runner header, which the trace reported as `VMError(invalid_contract absent_runner_comment)`. The
receipt calldata proves the submitted 47,006-byte source began with whitespace and had SHA-256
`fadf00a93aca46a8634ee77a60d55aa034a4a6fe8285f425b26251ca3bc64fde`; the canonical source was not
the file sent to Bradbury. The reproducible builder now preserves the exact header as line 1 and
rejects BOMs or any preceding byte. The single submitted deploy transaction was
`0xadcfdfde51d0ceb70e56b7ec00cf1898df438b67ba0bc357ac5ed7169c2ddbb5`, returning address
`0xCB9919a98b40285843Dc7bb2150B52Af2D890961`; its receipt is `ACCEPTED` with
`FINISHED_WITH_ERROR` and `VMError(invalid_contract absent_runner_comment)`. GenLayer reports no
usable contract at that address. This is a deployment failure, not a successful release, and must
not be treated as a usable contract. The corrected attempt must use the generated artifact at
`artifacts/source_consensus_deployable.py`, whose current SHA-256 is
`a43e7aae4e12121b62a89961c0791f4361f897b4be43b47fdb4f28e44a481c39` and whose first line is the
official pinned runner header.

## Corrected Attempt Record

The packaging correction was merged as `b0d888b` after green CI. Exactly one corrected deployment
was submitted with the header-preserving artifact:

- transaction: `0x8a287cf0b34becb4380b0f8af4cd97c4be39197de52c7a785b6f77944832e998`
- address: `0x742E0C7C5d7A375b6d1bf1ED82114819ccD270AF`
- consensus: `AGREE`
- execution: `FINISHED_WITH_ERROR`
- execution hash: `0x6fb9a7c4e5802134be17c4c41070469225e56284c7e637ad4984b4d3df286038`
- trace failure: `[EXPECTED] source_urls must be a list`

The runner header was present and accepted. The installed CLI parses complex arguments using
`JSON.parse`; the PowerShell command supplied backslash-escaped quotes inside a single-quoted token,
so the JSON parse failed and `source_urls` arrived as a string. The CLI's `array:` text is a help
label, not a literal prefix. The address has bytecode but is not a usable initialized contract. This
transaction is final and must not be resubmitted or followed by `resolve()`.

## Latest Attempt Record

After PR #5 merged with green CI and the fail-closed preflight passed, one deployment was submitted.
It was mistakenly invoked through the PowerShell CLI path rather than the requested native JS
transport. The transaction was:

- transaction: `0x0fdc2ca07dc43700378f8b72679ef1ae5a35c2135c96dc70b43b593821283e41`
- address: `0x908dC0774677a6cB5Ab4c0d51FE2096c08a3B6d8`
- consensus: `AGREE`
- execution: `FINISHED_WITH_ERROR`
- execution hash: `0x41752ebd9af24a8dac68fa90d59b0c9f4f7aff7d5fcdb3620063d3d2ef850957`
- trace failure: `[EXPECTED] source_urls must be a list`

Windows PowerShell stripped the embedded quotes while marshalling the variable to the native Node
CLI. The CLI consequently received a string despite the local Python preflight and correct source
artifact. The trace also logged `runner comment does not start with version, using default`; no
`absent_runner_comment` occurred. The local pinned runner and official header format are valid, but
the Bradbury warning means the pinned-runtime guarantee is not proven harmless. Bytecode exists at
the returned address, but the constructor failed, so the address is not usable and must not receive
`resolve()`.

## Attempt 4 live evidence

The official deploy-script framework was launched with no constructor CLI arguments. The script
submitted exactly one new deployment transaction after the gate above:

- pre-balance: `2.979383521792548153 GEN`; pre-nonce: `8`
- deployment transaction: `0xcbd90283f8f7a62d3b039d878473845a0136187307afc12e4d29b8d25879ed31`
- returned contract: `0x8cf322A235AB2C3F15732DF39e5F6177af3E0626`
- execution hash: `0x3c29e3a1a72c9218fbb9a6fb6e273fc747f23d2c3450c72a67af569619569926`
- protocol status: `ACCEPTED`; consensus: `AGREE`; execution: `FINISHED_WITH_RETURN`
- initial rotations: `3`; round 0 votes: `5/5 AGREE`; created `2026-08-09T13:43:58Z`, last vote
  `2026-08-09T13:44:11Z`
- accepted-state source: `gen_getContractCode` returned 47,090 bytes matching deployable SHA-256
  `a43e7aae4e12121b62a89961c0791f4361f897b4be43b47fdb4f28e44a481c39` exactly
- Explorer: `https://explorer-bradbury.genlayer.com/contract/0x8cf322A235AB2C3F15732DF39e5F6177af3E0626`

`get_config()` matched every observable constructor field, including `deployer`, `source_count: 3`,
thresholds, `PRESERVE`, pinned evidence, and expected
`configuration_hash` `0x14000a8af1488048755b93a32a7fa31ded90897e62d28aad875dc9a087d427cc`. `get_sources()`
reported all three pinned URLs with `VALUE` and `2026-03-11`; `is_resolved()` was initially false.

The script then submitted exactly one `resolve()` transaction after independently re-fetching and
hashing all three pinned sources:

- resolve transaction: `0x278a67c29f2c109f41cee1bee3604d2adee8c047e13d4dc46e2c65e213460733`
- execution hash: `0x01dd37e78c28557c57a28e6d7907bc244378c94005f05d1a4c113baee85c9ff2`
- protocol status: `ACCEPTED`; consensus: `AGREE`; execution: `FINISHED_WITH_RETURN`
- initial rotations: `3`; round 0 votes: `4 AGREE`, `1 TIMEOUT`; `5/5` committed and revealed
- final status/value: `CONFIRMED` / `2026-03-11`
- buckets: supporting `[0, 1, 2]`; conflicting `[]`; unavailable `[]`; ambiguous `[]`; no-value `[]`
- canonical record independently re-derived from `get_record()` and configuration hash

The account ended at nonce `10` and balance `2.974018148455848753 GEN`; total cost across deployment
and resolve was `0.005365373336699400 GEN`.

Read-only finality closure at `2026-08-09T14:41:33Z` returned `Finalized` / status code `7` for both
the deployment and resolve transactions. At `2026-08-09T14:42:57Z`-`14:42:59Z`,
`gen_getContractState` returned both accepted and finalized state; both encoded states were 299,932
hex characters with the same SHA-256 fingerprint
`832d5664e73a74c3b043037e7eef66b2e5cf953b600b273641389a33e56e1584`. No additional transaction
was submitted.

## Attempt 4 transport gate (pre-transaction)

Attempt 4 is not a transaction record. The dedicated `deploy/04_stage5_attempt4.js` module uses the
official deploy-script callback and calls `client.deployContract({ code, args: constructorArgs })`.
All nine constructor values are built in the module; `constructorArgs[3] === sourceUrls` and
`Array.isArray(constructorArgs[3])` are asserted before the client call. The mock-client regression
test proves the received nested value is an array of three strings, with no `JSON.stringify`, shell
argument, or `process.argv` path.

The deployable artifact gate passes at 47,090 bytes with SHA-256
`a43e7aae4e12121b62a89961c0791f4361f897b4be43b47fdb4f28e44a481c39`, byte 0 `#`, no BOM, exact
line-1 `Depends` header, and AST parity with the canonical source. The runner warning was traced to
the GenVM text-runner parser's optional `v<...>` engine-version line: without that separate line it
selects its default engine version while the JSON `Depends` entry still identifies the content-hashed
`py-genlayer` dependency. The current runner documentation specifies the one-line hashed `Depends`
form used here, so the header was not changed. A successful Bradbury constructor and finalized
state are recorded above.
