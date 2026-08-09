# Release Checklist

Stages 1-5 are complete. Three failed Bradbury deployment attempts remain preserved in
`PROVENANCE.md`. The native deploy-script attempt 4 completed constructor execution and exactly one
live `resolve()` with `FINISHED_WITH_RETURN`; both transactions subsequently reached protocol
`FINALIZED` with status code `7`.

Before tagging `v1.0.0-bradbury`, the evidence files contain the
deployment address, Explorer URL, both transaction hashes, validator votes, execution results,
GEN cost, timestamps, deployed source hash, expected/observed configuration hash, final status/value,
independently re-derived record, and finalized-state evidence. Run the full final audit. Do not move
older tags.

The final preflight review fixes are included: `--expected-configuration-hash` is mandatory and
the validator rejects every deterministic constructor-invalid source, threshold, URL, normalization,
enum, and type configuration before deployment. Regression tests cover both fail-closed findings.
