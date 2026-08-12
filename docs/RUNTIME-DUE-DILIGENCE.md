# Runtime Due Diligence

Checked 2026-08-12 against official GenLayer documentation and the installed/pinned toolchain.

## Primary sources

- Equivalence Principle and `run_nondet` variants:
  https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle
- nondeterministic boundary:
  https://docs.genlayer.com/developers/intelligent-contracts/features/non-determinism
- web access and independent validator requests:
  https://docs.genlayer.com/developers/intelligent-contracts/features/web-access
- LLM calls and custom validation:
  https://docs.genlayer.com/developers/intelligent-contracts/features/calling-llms
- deploy scripts for typed/complex arguments:
  https://docs.genlayer.com/developers/intelligent-contracts/deploying/deploy-scripts
- Bradbury network (chain ID 4221): https://docs.genlayer.com/developers/networks
- transaction statuses and finality:
  https://docs.genlayer.com/understand-genlayer-protocol/core-concepts/transactions/transaction-statuses
- appeals/finality lifecycle:
  https://docs.genlayer.com/understand-genlayer-protocol/optimistic-democracy-how-genlayer-works
- Python receipt polling and `FINALIZED` enum:
  https://docs.genlayer.com/api-references/genlayer-py/api

## Installed and pinned observations

- GenLayer CLI: 0.39.1.
- `genlayer-test`: 0.29.2.
- `genvm-linter`: 0.11.0.
- contract dependency: `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`.
- cached GenVM bundle: v0.2.16; pinned std
  `11rhn002yfajawsz7fai6mykznbxkxs6l91iskj5cm82c92qhy3v`.

The pinned std exposes both `run_nondet` and `run_nondet_unsafe`. Its own API documentation calls
`run_nondet` the safer custom API because validator errors execute in a sandbox and are compared;
the current website emphasizes `run_nondet_unsafe` for custom handlers where the contract handles
all validator errors. SourceConsensus keeps the pinned-runtime `run_nondet` path: the validator is
pure/read-only, rejects malformed leader results with `False`, independently runs nondeterministic
fetch/LLM operations, and relies on the pinned sandboxed error behavior. This is a reviewed
runtime-specific choice, not an assumption from current unpinned examples.

All `gl.nondet.web.render` and `gl.nondet.exec_prompt` calls are reachable only from the leader or
validator functions passed to `run_nondet`. Configuration, timestamp conversion, post-consensus
validation/derivation, and storage writes remain outside that boundary. The closure captures only
primitive copies/lists built before entry; lint and semantic validation prove compatibility with the
pinned runner.

Bradbury `ACCEPTED` is provisional during the appeal window. Release evidence requires status code
7 / `FINALIZED` for deployment and resolve. Complex constructor arguments use the native deploy
script/client path because official CLI documentation states lists require deploy scripts and the
historical PowerShell scalar transport failed twice.
