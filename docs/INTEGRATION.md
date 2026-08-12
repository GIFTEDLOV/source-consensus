# Integration

SourceConsensus is deployed once for one immutable, typed question. An integrator supplies 2-5
public URLs, a question, a fact type, thresholds, and optional normalization rules. The constructor
does no network work. `resolve()` is the only write; it is terminal for `CONFIRMED`, `CONFLICTED`,
and `INSUFFICIENT_EVIDENCE`, while `UNAVAILABLE` is retryable.

The public API is exactly: `resolve()`, `status()`, `value()`, `get_result()`, `get_record()`,
`is_resolved()`, `get_sources()`, `get_config()`, and `configuration_hash()`.

Compute the expected hash before deployment with `python tools/canonical.py hash config.json`.
Pin that digest in a consuming contract and compare it before trusting a result. Check `status()`
before `value()`; a non-confirmed value is empty. `get_record()` is canonical JSON. Verify it against
the immutable configuration and the complete ordered state/value payload from `get_sources()`, then
run `tools/canonical.py` derivation; the exact status, value, and all five index sets must match.

Schema version 2 requires validators to agree on every source state and normalized value, not only
supporting sources. Integrators may therefore treat every stored source diagnostic as
consensus-bound, while accepting that strict full-payload agreement can reduce liveness for mutable
or intermittently available sources.

Use commit-pinned sources when reproducibility matters. Never let source text supply instructions,
thresholds, statuses, or indices. Treat `CONFLICTED` as escalation, `INSUFFICIENT_EVIDENCE` as a
source/question quality failure, and `UNAVAILABLE` as a retryable fetch failure. See the working
examples in `examples/typed_release_date.py` and `examples/enum_product_status.py`.
