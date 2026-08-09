# Consensus Notes

The model extracts one `(state, value)` pair per source. The contract, not the model, derives the
aggregate status. Normalization is strict and deterministic: malformed `VALUE` output is rejected;
it is never repaired into a guess.

Derivation follows `docs/DERIVATION.md`: too few reachable sources yields `UNAVAILABLE`; two
supported contenders or a top tie yields `CONFLICTED`; a unique value meeting the minimum yields
`CONFIRMED`; otherwise the result is `INSUFFICIENT_EVIDENCE`. Supporting, conflicting, unavailable,
ambiguous, and no-value indices preserve the evidence partition.

GenLayer's T1 comparator checks status, normalized value, supporting indices, and the value/state of
each supporting source. Non-supporting buckets are recorded but not compared, because an
`AMBIGUOUS` versus `NO_VALUE` distinction cannot change the answer. Stage 3 measures how often that
tradeoff occurs in real models; no convergence claim is made without denominators.
