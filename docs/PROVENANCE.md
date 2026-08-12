# Provenance

> **Historical release status:** the successful deployment below, commit
> `89af051b9091dbff2eede243fea9afa5636c38b2`, and tag `v1.0.0-bradbury` are preserved exactly as
> rejected-release evidence. They are
> `SUPERSEDED_AFTER_STEWARD_CONSENSUS_BINDING_REVIEW`. The deployment finalized and executed as
> recorded, but its schema-version-1 comparator did not bind every source entry later consumed by
> final derivation. Nothing below should be cited as the current secure release.

SourceConsensus was implemented clean-room from `docs/ARCHITECTURE.md`, `docs/DERIVATION.md`, and
the pinned evidence fixtures. The contract contains no copied code, prompt text, storage layout, or
comparator logic from the overlap projects disclosed in `docs/OVERLAP-RESEARCH.md`.

Stage 3 offline convergence and adversarial checks pass. Real-model convergence was not run because
`OPENROUTER_API_KEY` was not available; no metrics are claimed.

Stage 5 preflight used Bradbury chain ID `4221`, RPC `https://rpc-bradbury.genlayer.com`, and the
generated encrypted `player3` account (`0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7`, unlocked,
2.993294722883001753 GEN). The exact expected configuration hash was
`0x14000a8af1488048755b93a32a7fa31ded90897e62d28aad875dc9a087d427cc`.

One deployment transaction was submitted, and never resubmitted:

- transaction: `0xadcfdfde51d0ceb70e56b7ec00cf1898df438b67ba0bc357ac5ed7169c2ddbb5`
- returned address: `0xCB9919a98b40285843Dc7bb2150B52Af2D890961`
- receipt: `ACCEPTED`, `FINISHED_WITH_ERROR`, not `FINALIZED`/`FINISHED_WITH_RETURN`
- execution hash: `0xf73a4659a070176f95899abf3487e751c4ca77887939adda7a679a40bf064053`
- failure: initial canonical source exceeded Bradbury pubdata/gas limits; the first AST-equivalent artifact submission omitted the required GenVM runner header and failed with `VMError(invalid_contract absent_runner_comment)`. The failed calldata encoded a 47,006-byte source beginning with whitespace, not `#`; its SHA-256 was `fadf00a93aca46a8634ee77a60d55aa034a4a6fe8285f425b26251ca3bc64fde`. The corrected build preserves the exact header as byte 0 and rejects BOMs, leading whitespace, blank lines, or non-first headers.
- canonical source SHA-256: `1167a1f67dc5e09f4db1da4ad5f9cc3d19598cb4a1b1bd23c60dd9b16d4427fd`
- corrected deployable artifact SHA-256: `a43e7aae4e12121b62a89961c0791f4361f897b4be43b47fdb4f28e44a481c39`

The packaging-fix branch was merged as `b0d888b2fb2e5f3dd6db4978eb5382de5f5235e8` after all CI
checks passed, including deployable `genvm-lint`, 354 tests, and 12/12 mutations. Two corrected
deployments were then submitted, each exactly once and never resubmitted:

- transaction: `0x8a287cf0b34becb4380b0f8af4cd97c4be39197de52c7a785b6f77944832e998`
- returned address: `0x742E0C7C5d7A375b6d1bf1ED82114819ccD270AF`
- consensus: `AGREE`
- execution: `FINISHED_WITH_ERROR`
- execution hash: `0x6fb9a7c4e5802134be17c4c41070469225e56284c7e637ad4984b4d3df286038`
- failure: `[EXPECTED] source_urls must be a list`
- root cause: the installed GenLayer CLI parses complex arguments with `JSON.parse`; the PowerShell
  command supplied backslash-escaped quotes inside a single-quoted token, so JSON parsing failed and
  the constructor received the whole `source_urls` token as a string. The CLI's `array:` text is a
  help label, not a literal prefix.
- runner result: the exact line-1 header was accepted; the trace logged only a warning that the
  runner comment did not start with version, then failed during constructor validation
- code check: bytecode is present at the returned address, but constructor execution failed, so it
  is not a usable initialized SourceConsensus contract
- player3 balance: `2.988620238152751753 GEN` before; `2.984091408481575003 GEN` after
- nonce: `6` before; `7` after

No `resolve()` transaction was submitted. The failed constructor means no `get_config()`,
`configuration_hash()`, or initial-state claim is valid for this address. Stage 5 remains blocked;
the CLI array encoding must be corrected and reviewed before any future deployment decision.

The latest corrected deployment was submitted only after fail-closed preflight and PR #5 CI passed.
It was mistakenly invoked through the PowerShell CLI path rather than the requested native JS
transport; this is preserved as an execution-process failure:

- transaction: `0x0fdc2ca07dc43700378f8b72679ef1ae5a35c2135c96dc70b43b593821283e41`
- returned address: `0x908dC0774677a6cB5Ab4c0d51FE2096c08a3B6d8`
- consensus: `AGREE`
- execution: `FINISHED_WITH_ERROR`
- execution hash: `0x41752ebd9af24a8dac68fa90d59b0c9f4f7aff7d5fcdb3620063d3d2ef850957`
- failure: `[EXPECTED] source_urls must be a list`
- root cause: Windows PowerShell native argument marshalling removed embedded JSON quote characters
  from the variable passed to the Node CLI, so the installed CLI again received a string
- trace warning: `runner comment does not start with version, using default`; no
  `absent_runner_comment` occurred
- code check: bytecode is present, but constructor execution failed; this is not a usable initialized
  SourceConsensus contract
- player3 balance: `2.988620238152751753 GEN` before; `2.979383521792548153 GEN` after
- nonce: `7` before; `8` after

No `resolve()` transaction was submitted for this failed attempt. Another deployment required a
JavaScript deploy script or direct GenLayer client call that passes a native array. The runner
warning was still under investigation at this point in the historical record; the later source-level
analysis and successful constructor evidence are recorded below.

Attempt 4 preparation was preserved separately from the three submitted transactions. The official
GenLayer deploy-script path is implemented in `deploy/04_stage5_attempt4.js`; it reads only
`artifacts/source_consensus_deployable.py` and passes the nine in-code constructor values directly to
`client.deployContract({ code, args: constructorArgs })`. A mock-client test records the exact
received arguments and proves that `source_urls` remains the same native `Array<string>` object at
index 3. The resulting attempt-4 transaction is recorded below.

The literal warning string is absent from the installed `genlayer` CLI, `genlayer-js`, and locally
extracted Python runner sources; it appears in Bradbury's GenVM trace. The installed/current runner
documentation separates the optional GenVM engine version line from the JSON `Depends` dependency:
the exact hashed `py-genlayer` header remains the runtime dependency selector, while the warning
describes the default engine-version field. This is documented evidence, not a header change; a
the successful constructor and exact accepted-state source bytes provide operational evidence that
the header was accepted; the later protocol-finality result is recorded below.

Attempt 4 succeeded through deployment, initialization, and one live resolution using the official
native deploy-script transport:

- pre-balance / nonce: `2.979383521792548153 GEN` / `8`
- deployment tx: `0xcbd90283f8f7a62d3b039d878473845a0136187307afc12e4d29b8d25879ed31`
- contract: `0x8cf322A235AB2C3F15732DF39e5F6177af3E0626`
- deployment execution hash: `0x3c29e3a1a72c9218fbb9a6fb6e273fc747f23d2c3450c72a67af569619569926`
- deployment: `ACCEPTED`, `AGREE`, `FINISHED_WITH_RETURN`, 5/5 validator votes `AGREE`, 3 initial rotations
- accepted-state source: 47,090 bytes, exact deployable SHA-256
  `a43e7aae4e12121b62a89961c0791f4361f897b4be43b47fdb4f28e44a481c39`
- resolve tx: `0x278a67c29f2c109f41cee1bee3604d2adee8c047e13d4dc46e2c65e213460733`
- resolve execution hash: `0x01dd37e78c28557c57a28e6d7907bc244378c94005f05d1a4c113baee85c9ff2`
- resolve: `ACCEPTED`, `AGREE`, `FINISHED_WITH_RETURN`, 4 `AGREE` and 1 `TIMEOUT` vote, 3 initial rotations
- final state: `CONFIRMED`, `2026-03-11`; supporting `[0,1,2]`, all other buckets empty
- expected and observed configuration hash:
  `0x14000a8af1488048755b93a32a7fa31ded90897e62d28aad875dc9a087d427cc`
- final balance / nonce: `2.974018148455848753 GEN` / `10`; total GEN cost:
  `0.005365373336699400 GEN`
- Explorer: `https://explorer-bradbury.genlayer.com/contract/0x8cf322A235AB2C3F15732DF39e5F6177af3E0626`

Independent read-back confirmed every `get_config()` field, all three `get_sources()` entries,
`get_result()`, `get_record()`, `status()`, `value()`, `is_resolved()`, and unchanged
`configuration_hash()`. The canonical record re-derives to the observed result.

Read-only finality closure observations on `2026-08-09` returned the following through
`gen_getTransactionStatus`:

- deployment observed `2026-08-09T14:41:33.4597799Z`: `Finalized`, status code `7`
- resolve observed `2026-08-09T14:41:33.8895858Z`: `Finalized`, status code `7`

`gen_getContractState` returned state for both `accepted` and `finalized` at
`2026-08-09T14:42:57.7043519Z` and `2026-08-09T14:42:59.6410351Z`. Each response contained
299,932 hex characters and had the same response fingerprint
`832d5664e73a74c3b043037e7eef66b2e5cf953b600b273641389a33e56e1584`.

Finalized-state readback at `2026-08-09T14:44:22.312Z` independently confirmed every observable
`get_config()` field, `is_resolved() == true`, status `CONFIRMED`, value `2026-03-11`, and the
expected configuration hash `0x14000a8af1488048755b93a32a7fa31ded90897e62d28aad875dc9a087d427cc`.
No additional transaction was submitted.
