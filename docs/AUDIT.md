# Full Contract Audit

Audit date: 2026-08-12. Scope: every line of `contracts/source_consensus.py`, the independent
reference, fixtures, tests, convergence and mutation harnesses, deployment tooling, CI, README, and
all current documentation.

## Findings remediated

| Severity | Finding | Remediation |
| --- | --- | --- |
| Critical | supporting-only consensus left decision-relevant source entries unbound | schema-v2 complete payload validation/comparison, leader self-derivation, storage revalidation/re-derivation |
| High | mutation harness declared compound edits but applied only the first | `apply_mutation` applies and validates both anchors; harness unit regression |
| Medium | JSON parser accepted an object embedded in surrounding or concatenated text | exact single-object parsing; only complete plain/markdown-fenced JSON accepted |
| Medium | model state/value schema repaired casing, whitespace, missing/null representation, and arbitrary extra fields | exact state and exact two-field schema; null required for non-VALUE; unknown fields rejected |
| Medium | `datetime.timestamp()` introduced float/host-timezone risk in stored time | timezone required; UTC conversion and integer timedelta arithmetic; fractional floor tested |
| Medium | STRING/ENUM coerced JSON booleans/integers into text | per-fact-type scalar requirements in contract and independent oracle |
| Low | year 0000 passed date surface validation | Gregorian year lower bound 1 in both implementations |
| Low | canonical record omitted the consensus-bound no-value set | schema-v2 record includes all five sets |
| Documentation | current T2 claims contradicted the required security boundary; record-alone re-derivation was overstated | README/architecture/derivation/consensus/convergence/integration/CI/build/release docs corrected |

No unresolved HIGH or CRITICAL issue remains. Exact-head CI, deployment and resolution finality,
live validator behavior, deployed-byte equality, and off-chain record derivation all passed and are
recorded in `RESUBMISSION.md` and the remediation JSON artifact.

The untouched rejected-release baseline passed 367 tests. The corrected suite passes 441 tests,
including R01–R28 and exhaustive 70,800-case derivation parity. All 26 executable mutants are killed:
12 historical mutations plus M01–M14, with zero survivors and zero broken mutants.

## Category verdicts

- configuration: bounded exact types, immutable source order, unique HTTPS/no credentials, pinning,
  thresholds, type-specific rules, normalized enum deduplication — PASS;
- configuration identity: every extraction/normalization/source/derivation/consensus semantic is
  direct or schema-version committed — PASS;
- derivation: reachability, zero values, ties, pluralities, thresholds, and index partitions checked
  exhaustively against an independent oracle — PASS;
- normalization: DATE/INTEGER/BOOLEAN/ENUM/STRING and wrong-scalar/floats covered — PASS;
- model/prompt: exact schema, no aggregate channel, isolated prompts, injection/fence cases — PASS;
- web: nondeterministic boundary, failure/empty handling, sanitation and visible bound — PASS;
- consensus/storage: complete payload and all aggregates bound; deterministic storage derivation — PASS;
- lifecycle/time: UNAVAILABLE-only retry, terminal replay guard, attempts/source detail, integer
  transaction timestamp — PASS;
- public interface: 9 methods, 8 view and 1 write, no accidental helper exposure — PASS;
- provenance/deployment: historical v1 preserved/superseded; corrected source, finalized deployment,
  finalized live resolution, votes, complete payload, and byte equality recorded — PASS.
