# Release Checklist

Stages 1-4 are complete. Three failed Bradbury deployment attempts remain preserved in
`PROVENANCE.md`. The native deploy-script attempt 4 completed constructor execution and exactly one
live `resolve()` with `FINISHED_WITH_RETURN`, but both transactions remain protocol status
`ACCEPTED`; Bradbury has not exposed literal `FINALIZED`.

Before tagging `v1.0.0-bradbury`, the only remaining gate is literal Bradbury `FINALIZED` status for
the recorded deployment and resolve transactions. The evidence files already contain the
deployment address, Explorer URL, both transaction hashes, validator votes, execution results,
GEN cost, timestamps, deployed source hash, expected/observed configuration hash, final status/value,
and independently re-derived record. Run the full final audit after finality is available. Do not
move older tags.
