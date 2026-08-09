# Release Checklist

Stage 4 is documentation and tested examples only. The release remains blocked until Stage 5
records one Bradbury deployment and one finalized live resolution.

Before tagging `v1.0.0-bradbury`, update `PROVENANCE.md`, `DEPLOYMENT.md`, this file, and README with
the deployment transaction, address, Explorer URL, resolve transaction, validator votes, execution
result, GEN cost, timestamps, deployed source hash, expected/observed configuration hash, final
status/value, and independently re-derived record. Run the full final audit: lint, validation,
tests, mutations, examples, fixtures, canonical parity, Windows/Linux parity, line endings, hashes,
links, placeholders, stale-reference and secret scans, and CI. Do not move older tags.
