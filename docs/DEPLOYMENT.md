# Deployment

This document contains the pre-transaction procedure and the recorded Stage 5 attempts. The first
attempt did not finalize, so no resolve transaction was submitted for it.

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
`https://explorer.genlayer.com/contract/<address>` after deployment.

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
