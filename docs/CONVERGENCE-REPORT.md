# Stage 3 Convergence Report

## Decision rules

The harness measures the contract's T1 comparator as written: status, normalized aggregate value,
supporting indices, and every supporting source's `(state, value)` must agree. Non-supporting bucket
differences are recorded but do not count as disagreement. HTTP 402, HTTP 429, provider errors,
transport failures, empty content, and truncation are rejection/availability outcomes, not model
disagreement. Every reported metric uses an explicit `n/N` denominator.

## Harness

Run offline validation with:

```bash
python tools/convergence.py
```

For the opt-in OpenRouter measurement, set `OPENROUTER_API_KEY` at runtime and run:

```bash
OPENROUTER_API_KEY=... python tools/convergence.py --repeats 2
```

The harness uses the five configured models, all nine fixtures, deterministic temperature `0`,
contract-aligned one-source prompts, and JSONL logging in `artifacts/convergence.jsonl`. Raw response,
parsed response, rejection category, usage, cost, and finish reason fields are retained. The key is
never stored in the repository.

## Offline result

The nine fixture derivations and adversarial rejection cases pass offline. No OpenRouter key was
available during this release preparation, so real-model metrics are deliberately **not-run**, not
invented. Consequently valid/attempted, per-model success, status agreement, normalized-value
agreement, supporting-index agreement, per-source VALUE agreement, bucket disagreement,
cross-model agreement, repeatability, injection failure rate, and end-to-end pass rate have no
honest `n/N` result yet.

## Adversarial coverage

Offline tests cover question/fact-type/status redefinition attempts, fake status JSON, forged source
indices, contradictory/ambiguous dates, normalization-equivalent values, control/trap values, and
schema rejection. The existing direct-mode corpus additionally covers sentinel fencing, source
omission, unknown indices, forbidden fields, oversized evidence, and majority-wrong evidence.

## Remaining risk

The unresolved empirical risk is model convergence, especially T2 differences among non-supporting
`NO_VALUE`, `AMBIGUOUS`, and unavailable buckets and repeatability under provider variation. Run the
exact command above with a funded key before claiming production convergence; the harness refuses to
turn transport or credit failures into disagreement statistics.
