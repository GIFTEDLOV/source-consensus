# SourceConsensus Resubmission

## Rejection

> "The contract's final result is not fully protected by validator consensus. The validator checks
> only the supporting sources, but the contract later recalculates the stored status from every
> leader-provided source result, so unchecked entries can change a confirmed result into a conflict.
> Please have validators bind all per-source states and values used by the final derivation, or
> recompute from a fully verified payload, then resubmit matching source and deployment."

The rejection is accepted. This is a correction, not an appeal.

## Root cause and exploit

Schema version 1 compared the aggregate status/value, supporting indices, and supporting source
pairs. It did not compare all other source states/values. `resolve()` then called `_derive_status`
over the full leader payload. With five sources, an honest extraction `[A,A,A,NO_VALUE,NO_VALUE]`
derives `CONFIRMED A`; a leader could advertise that aggregate while returning `[A,A,A,B,B]`, which
derives `CONFLICTED` after consensus.

Historical evidence: commit `89af051b9091dbff2eede243fea9afa5636c38b2`, tag
`v1.0.0-bradbury`, contract `0x8cf322A235AB2C3F15732DF39e5F6177af3E0626`. It is
`SUPERSEDED_AFTER_STEWARD_CONSENSUS_BINDING_REVIEW`.

## Remediation

Schema version 2 validates exactly N ordered states and values, exact states, canonical normalized
VALUE scalars, and null non-VALUE entries. Validators re-derive and compare all leader aggregate
fields, independently reproduce all source pairs, compare every pair by index, and independently
derive all aggregate fields. Post-consensus storage validates again and derives only from the bound
states/values.

The configuration hash includes schema version, so all corrected deployment identities differ from
schema version 1 even when the bounded fact and source URLs are unchanged.

## Regression and audit proof

- steward matrix: R01–R28 executable cases;
- new consensus/storage mutations: M01–M14, in addition to all historical mutations;
- exhaustive contract/reference derivation parity: 70,800 combinations for N=2…5;
- rejected-release baseline: 367/367 tests passed before remediation;
- corrected local suite: 441/441 tests passed; 26/26 executable mutants caught
  (12 historical plus 14 rejection-specific), with zero survivors or broken mutants;
- complete constructor, normalization, parser, prompt, web, retry, timestamp, storage, interface,
  fixture, deployment-preflight, and documentation parity audit;
- real-provider convergence: NOT RUN without a provider key; corrected Bradbury resolution is the
  required live independent-validator evidence.

## Corrected source, deployment, and live proof

The corrected deployment source commit is
`f818e9c6dc16f72e01a25baa2d8acdc750bfe16e`; the evidence-only release commit is tagged
`v1.0.1-bradbury` after this document is committed. Canonical source is 60,586 bytes,
SHA-256 `9cc2fa9d7d8ae97d3e10ba865bd7426bae6eeac98d226dbe0ca8b6bab8f9bb65`.
The reproducibly generated and actually submitted deployable is 51,585 bytes, SHA-256
`e0a732644683c8af6c15cdd781ef85c98eacddcb0febbec5df1fd6d1209796b9`. Bradbury's
`gen_getContractCode` returned exactly those bytes after finality.

Exact-head CI run [31593257570](https://github.com/GIFTEDLOV/source-consensus/actions/runs/31593257570)
passed all jobs. Schema-v2 configuration hash is
`0x33d4880006e882e213ba73cb2bbbb223b01eb5d5808eadaf3054ab807fed9955`.

- network/chain: Genlayer Bradbury Testnet / `4221`;
- sender: `0xe0f17bef0587c3b66d2eb4bbe705dff821abdde7`;
- finalized deployment: `0x6404c2364b5ba936ea891febb89a9365930cdbe3d77a97b31871b8e0bd7a745b`;
- new contract: [`0x2084107B5274FB82FDE29Bbe4794517309AdE2b9`](https://explorer-bradbury.genlayer.com/contract/0x2084107B5274FB82FDE29Bbe4794517309AdE2b9);
- deployment consensus: round 0, 5/5 `AGREE`, no rotations, `FINISHED_WITH_RETURN`;
- finalized resolution: `0x678630dbae18b324cfdf46df25230e68ec8b28067e05373cdc463d2247c182c8`;
- resolution consensus: round 0, votes `AGREE, AGREE, TIMEOUT, TIMEOUT, AGREE`, no rotations,
  `FINISHED_WITH_RETURN`;
- final result: `CONFIRMED` / `2026-03-11`.

The finalized complete source payload is index 0 `VALUE/2026-03-11`, index 1
`VALUE/2026-03-11`, and index 2 `VALUE/2026-03-11`. The independent reference derives supporting
`[0,1,2]`, all other index sets empty, and `CONFIRMED/2026-03-11`; its canonical record is exactly
equal to `get_record()`. The machine-readable before/after, votes, hashes, full payload, and equality
proof are in `artifacts/steward-consensus-binding-remediation.json`.

The source submitted for review will be the exact commit connected by the reproducibility evidence
to the exact bytes returned by Bradbury for the new address. The old address will not be reused.
