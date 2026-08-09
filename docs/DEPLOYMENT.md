# Deployment

This document contains the pre-transaction procedure and the recorded Stage 5 attempts. Neither
attempt produced a usable initialized contract, so no resolve transaction was submitted.

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
