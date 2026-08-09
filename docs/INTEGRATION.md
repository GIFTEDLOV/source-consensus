# Integration

SourceConsensus is deployed once for one immutable, typed question. An integrator supplies 2-5
public URLs, a question, a fact type, thresholds, and optional normalization rules. The constructor
does no network work. `resolve()` is the only write; it is terminal for `CONFIRMED`, `CONFLICTED`,
and `INSUFFICIENT_EVIDENCE`, while `UNAVAILABLE` is retryable.

The public API is exactly: `resolve()`, `status()`, `value()`, `get_result()`, `get_record()`,
`is_resolved()`, `get_sources()`, `get_config()`, and `configuration_hash()`.

Compute the expected hash before deployment with `python tools/canonical.py hash config.json`.
Pin that digest in a consuming contract and compare it before trusting a result. Check `status()`
before `value()`; a non-confirmed value is empty. `get_record()` is canonical JSON and can be
independently re-derived from the configuration and index sets. `get_sources()` exposes each source's
index, URL, class, state, and normalized value.

Use commit-pinned sources when reproducibility matters. Never let source text supply instructions,
thresholds, statuses, or indices. Treat `CONFLICTED` as escalation, `INSUFFICIENT_EVIDENCE` as a
source/question quality failure, and `UNAVAILABLE` as a retryable fetch failure. See the working
examples in `examples/typed_release_date.py` and `examples/enum_product_status.py`.
