# Provenance

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

No `resolve()` transaction was submitted for the failed attempt. No final status/value, validator
vote record, observed configuration hash, or Explorer contract URL exists for the returned address
because that deployment did not finalize and is not a usable contract. A corrected deployment is
permitted only after the packaging-fix CI run is green; its transaction and all subsequent reads
will be appended below without overwriting this failure record.
