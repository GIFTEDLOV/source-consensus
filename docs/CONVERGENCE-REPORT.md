# Convergence Report

## Corrected decision rule

Schema version 2 requires exact agreement on the complete ordered source payload. A convergence run
is consensus-compatible only if validators agree on every per-source state and normalized value and
on all deterministically derived aggregate fields. Matching status alone is insufficient.

The harness reports explicit n/N metrics for:

- full per-source payload agreement;
- per-source state agreement;
- per-source normalized-value agreement;
- aggregate status and normalized-value agreement;
- supporting, conflicting, unavailable, ambiguous, and no-value set agreement;
- within-model repeatability;
- end-to-end consensus-compatible fixtures.

HTTP 402/429, provider errors, and transport failures are separately excluded from model-disagreement
denominators. Empty output, malformed JSON/schema, and normalization failure remain visible rejected
responses.

## Commands and current evidence

```powershell
python tools/convergence.py
$env:OPENROUTER_API_KEY='runtime-only'; python tools/convergence.py --repeats 2
```

Offline mode validates the fixture derivations and adversarial rejection categories. No provider key
is available in the repository, so real-provider convergence is **NOT RUN** and no percentages are
fabricated. Raw online attempts, when explicitly enabled, are JSONL with model, fixture, repeat,
source index, raw/parsed response, rejection category, usage, cost, and finish reason.

Direct-mode tests use mocks and establish rule correctness, not empirical model convergence. The new
Bradbury live resolve is the required independent-validator evidence for the corrected release. If
strict full-payload agreement reduces liveness, the failure must be diagnosed and preserved; the
consensus boundary must not be weakened.
