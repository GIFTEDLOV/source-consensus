# Threat Model

## Security invariant

No data may affect stored status, value, source record, or public index set unless validators bind
it at the immutable configured source index. Storage is a deterministic function of immutable
configuration, the complete consensus-bound source payload, deterministic derivation, and the
transaction datetime.

## Threats and controls

| Actor/boundary | Threats | Controls and residual risk |
| --- | --- | --- |
| malicious leader | fabricated/omitted/extra/reordered states or values; supporting-only exploit; contradictory status/value/sets | exact N arrays and canonical schema; leader self-derivation over all seven aggregate fields; exact per-index comparison; post-consensus revalidation/re-derivation |
| malicious source | SYSTEM/developer text, fake JSON, ignore instructions, other-source/threshold/status claims, fence closing, false fact | one source per prompt; evidence first and fenced; fence neutralization; contract-owned config/index/fetch state/status; residual: enough wrong sources can confirm a wrong value |
| malicious configuration | duplicate/insecure/credential URLs; mutable URL presented as pinned; impossible thresholds; invalid rules; poisoned enum duplicates | immutable constructor validation; HTTPS/unique/bounds; exact pin classifier; type-specific rules; normalized enum deduplication; hash commits semantics |
| network | unavailable or different availability; mutable drift; errors; empty/partial/oversized content | fetch outcome alone creates UNAVAILABLE; empty/failure unavailable; visible deterministic clamp; strict full-payload mismatch rejects; residual liveness cost is documented |
| model | malformed/multiple JSON; forbidden aggregate/confidence; invalid state/value; divergent classification | exact object/schema; output cap; no semantic repair; type normalization; full validator reproduction |
| derivation | tie selects lexical winner; conflict threshold edge; unchecked entry; array/set mismatch | exhaustive N=2…5 oracle parity; conflict before confirm; top-tie rule; 28-case steward matrix |
| storage/retry/time | raw leader payload stored; aggregate trusted; stale retry state; terminal replay; host-local/float time | `_prepare_storage_result`; deterministic re-derive; UNAVAILABLE-only retry; terminal guard; timezone-required integer timestamp conversion |
| deployment | wrong artifact/header/args/network/sender; shell mangling; stale hash/tag | reproducible builder; byte-0 header checks; native typed deploy script; exact-head CI and preflight; finalized byte readback |
| provenance | repository source differs from submitted bytes; old vulnerable address resubmitted | commit→source→artifact→transaction chain; deployed code hash check; immutable old tag marked superseded; new address/tag only after live proof |

The known liveness tradeoff is deliberate: validators may reject when a mutable page, network
outcome, or model classification differs. The steward-required integrity boundary must not be
weakened to improve convergence.
