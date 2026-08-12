# Release Checklist

`v1.0.0-bradbury` is immutable historical evidence and
`SUPERSEDED_AFTER_STEWARD_CONSENSUS_BINDING_REVIEW`. Never move, delete, or reuse it.

The corrected release candidate is schema version 2. A new tag (expected
`v1.0.1-bradbury`) may be created only after:

- the 28-case steward matrix and all historical/new mutations pass;
- full tests, fixtures, reference parity, exhaustive derivation, convergence-offline, deployment
  preflight, GenVM lint, and semantic validation pass;
- canonical source and generated deployable hashes/byte counts are recorded and reproducible;
- the reviewed commit is pushed and exact-head GitHub Actions is green;
- a new Bradbury deployment reaches `FINALIZED` with matching submitted bytes;
- one corrected live `resolve()` reaches `FINALIZED`;
- every stored source state/value is read back and independently derives the exact stored result;
- provenance, remediation JSON, README, deployment docs, and `RESUBMISSION.md` contain the final
  address, transactions, votes, hashes, finality, and tag.

Do not tag a commit that contains placeholders or unverified live evidence.
