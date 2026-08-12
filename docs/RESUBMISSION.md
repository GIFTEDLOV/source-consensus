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

This section must contain no placeholders when tagged:

- remediation commit: PENDING;
- corrected tag: PENDING;
- canonical source SHA-256 / bytes: PENDING;
- deployable SHA-256 / bytes: PENDING;
- configuration hash: PENDING;
- CI run: PENDING;
- Bradbury deployment transaction / new address / finalized evidence: PENDING;
- corrected resolve transaction / votes / finalized evidence: PENDING;
- complete stored source payload and independent derivation: PENDING.

The source submitted for review will be the exact commit connected by the reproducibility evidence
to the exact bytes returned by Bradbury for the new address. The old address will not be reused.
