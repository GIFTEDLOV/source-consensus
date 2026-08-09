# Build Plan — SourceConsensus

Five stages. **Each stage requires explicit approval before the next begins.** Stage 2 does not
start until `ARCHITECTURE.md` is approved.

**Stage 5 is required, not optional.** The Intelligent Contracts submission form requires a GenLayer
Explorer contract URL, which only a deployment produces. It is listed last because it depends on
everything before it, not because it is deferrable — and this plan says so here so that no later
document can quietly reclassify it.

---

## Stage 1 — Research and architecture *(complete — approved)*

**Delivered**

- `docs/OVERLAP-RESEARCH.md` — ecosystem audit with the closest competitor's contract **read at
  source level** and quoted by line number, self-overlap disclosure, risk analysis, acceptance-bar
  scoring, and a **MODIFY** recommendation with six required modifications.
- `docs/ARCHITECTURE.md` — problem statement, integrators, API, bounds, source states, normalisation,
  deterministic status derivation, configuration hash, canonical record, lifecycle, consensus tiers,
  threat model, evidence policy, malformed-output handling, limitations, example integrations. Every
  open design question from the brief is answered in place, including the three where the answer
  differs from the brief's stated preference (§5 `AMBIGUOUS`, §10.1 retryable `UNAVAILABLE`, §11
  rejecting strict per-source equality).
- `fixtures/` — **nine** cases covering all four statuses and nine categories, a JSON Schema, and a
  25-document commit-pinned evidence corpus.
- `tools/` — `canonical.py` (independent reference implementation of normalisation, derivation and
  the configuration hash), `make_fixtures.py`, `validate_fixtures.py`, `check_evidence_urls.py`,
  `check_line_endings.py`, `source_hash.py`.
- Repository quality controls: pinned dependencies, LF enforcement, secret scan, fixture validation
  including live URL verification, reproducibility manifest, stage guard, Windows parity.

**Explicitly not delivered:** any contract code. `contracts/` does not exist and will not until this
stage is approved.

**Exit criteria:** architecture approved; recommendation accepted; no critical overlap outstanding.

---

## Stage 2 — Contract implementation *(complete)*

**Delivered:** `contracts/source_consensus.py` (one deployable file, 9 public methods, 1 write), `tools/mutation_test.py`, and a Direct Mode suite. `genvm-lint check` and `validate` both clean against the pinned runner.

Two corrections were forced by implementation and are recorded in place:

- **`DERIVATION.md` §3, the tie uniqueness clause.** The first truth table let a `conflict_threshold` above the tied count fall through to row 4, where the lexicographic tie-break -- which exists only to pin determinism -- silently chose the winner of a dead heat. A test written from the table caught it before the contract shipped. The clause is now explicit and mutation-tested.
- **Storage field names.** `status` and `value` are public view methods, so the storage fields behind them are `resolved_status` and `resolved_value`; the original names shadowed the methods and `genvm-lint` reported 8 public methods instead of 9.

<details>
<summary>Original Stage 2 plan</summary>

**Deliverable:** `contracts/source_consensus.py`, a single deployable file.

1. Constants and bounds exactly as `ARCHITECTURE.md` §4.
2. Storage dataclasses. No floats, no admin fields, no setters.
3. Validation helpers: `query_id` regex, length bounds, URL validation, enum-membership checks.
4. `__init__`: validate, canonicalise, compute `configuration_hash` (§8), store. **No network access
   and no LLM call in the constructor** — deployment stays cheap, deterministic, and separately
   testable from resolution.
5. `normalise_value` — pure, per fact type (§6).
6. `derive_status` — pure, total, unit-testable in isolation (§7). The only producer of a status.
7. `_extract_one_source` — the per-source prompt, with sentinel fencing, sanitisation and clamping
   (§12). One source per prompt, never two.
8. `_agree` — the tiered comparator (§11), pure, testable against synthetic result lists.
9. `resolve` — guards, fetch, `gl.vm.run_nondet(leader_fn, validator_fn)`, single terminal write.
10. Views, including `configuration_hash`, `status`, `value`, and `get_record`.

**Constraints on the work.** Clean-room from this architecture document. No code, prompt text,
storage layout or comparator logic carried over from `semantic-constraint`, `uptimebond`,
`constitutioncourt`, or `intelligent-oracle`. `docs/PROVENANCE.md` is written at this stage and
states that explicitly.

**Mutation testing starts here, not later.** The first mutations must cover the derivation precedence
(§7 rules 1–4), normalisation rejection, and the prompt fences.

**Exit criteria:** `genvm-lint check` and `genvm-lint validate` both clean against the pinned runner;
contract is LF-only; `stage-guard` now demands direct tests, which Stage 3 supplies.

</details>

---

## Stage 3 — Direct-mode tests, adversarial tests, and convergence *(complete — offline; real-model run not available)*

**3a — Pure-function tests (no VM, no LLM)**

- `derive_status`: exhaustive over the precedence table, including every boundary at
  `minimum_supporting_sources` and `conflict_threshold`, and the tie-break determinism.
- `normalise_value`: per type, including `2026-02-30`, leap years, `1,200`, `1e3`, out-of-range
  integers, non-member enums, over-length strings.
- `configuration_hash`: stable under re-serialisation, **changes when source URLs are reordered**
  (§8), changes on any field edit, agrees with `tools/canonical.py`, identical on Linux and Windows.

**3b — Direct-mode tests**

- Construction: every bound violation reverts with a distinct message; 1 source reverts; 6 sources
  revert; `minimum_supporting_sources` > source count reverts; `ENUM` without values reverts.
- The nine fixture cases end to end with mocked web and LLM responses, asserting exact status, value,
  and all four index sets.
- Terminality: a second `resolve` after `CONFIRMED` / `CONFLICTED` / `INSUFFICIENT_EVIDENCE` reverts;
  **a retry after `UNAVAILABLE` is permitted** (§10.1) and cannot overwrite a terminal status under
  any ordering.
- A failed resolution writes no state.
- Record: `get_record` re-derives to the stored status when run through `tools/canonical.py`.

**3c — Adversarial tests**

- The `06` injection corpus: assert no path exists by which a source can set a status, change the
  fact type, add an index, or speak for another source.
- Model returns an unknown `source_index` → rejected, not dropped.
- Model omits a source → rejected, not auto-filled.
- Model returns a status field → rejected.
- Model returns `VALUE` with a non-normalising payload → rejected, not repaired.
- Sentinel string embedded in source text → neutralised.
- Oversized source → clamped deterministically; identical twice.
- Two competing values where one has more support → `CONFLICTED`, never plurality (§7 rule 2).

**3d — Mutation testing**

Breaking each load-bearing behaviour in turn and re-running: the four derivation precedence rules,
the tie-break, normalisation rejection, index-set construction, the prompt fences, and the T1
comparator. A mutation that survives is a hole and fails the build. **A mutation counts as caught
only when named tests fail**, never when the process merely exits non-zero.

**3e — Convergence measurement**

The open question from `ARCHITECTURE.md` §11: does the T1 rule converge across real models? An
opt-in, no-chain harness runs the contract's own prompt and comparator against several models via a
provider key, over the nine fixtures. **Decision thresholds are recorded before the run**, so the
outcome cannot be fitted to the data afterwards.

If `supporting_source_indices` diverges across models even where the status agrees, T1 is wrong and
must be revised before any convergence claim is made.

**Exit criteria:** every architecture invariant has at least one test that fails if the invariant is
removed; suite green in CI on Python 3.12; no test asserts on prose; all mutations caught; the
convergence run either executed and reported, or explicitly marked not-run with the reason.

---

## Stage 4 — Integration documentation and two working examples *(complete)*

- `docs/INTEGRATION.md` — intended integrators, dependency assumptions, constructor configuration,
  how to choose sources that converge, computing `configuration_hash` off-chain, pinning it in a
  consuming contract, every public method, canonical record verification, schema versioning, error
  handling, terminal semantics, safe patterns and anti-patterns, limitations.
- `docs/CONSENSUS-NOTES.md` — the deterministic-derivation argument and the tiered comparator,
  written to be lifted by other builders. This is the transferable idea.
- **Two working, tested integration examples** (required modification 6 in `OVERLAP-RESEARCH.md` §6):
  a consuming contract that pins `configuration_hash` and branches on all four statuses, and an
  off-chain triage script that acts on the index sets. Both must use the real API, contain no
  invented methods, be tested, and be linted in CI so they cannot rot into pseudocode.

**Exit criteria:** a builder who has not read this repository can deploy an instance and read a
result using the README alone.

---

## Stage 5 — Bradbury deployment and one live resolution *(COMPLETE)*

- `docs/DEPLOYMENT.md` written **before** any transaction is signed: network, RPC, chain ID, source
  hash, constructor fields, expected `configuration_hash`, deployment command, verification
  procedure, failure/recovery, explorer URL pattern.
- Deploy one canonical instance with a real, bounded question over commit-pinned sources.
- Run exactly one live `resolve()`.
- Verify: consensus `FINALIZED`; execution `FINISHED_WITH_RETURN`; on-chain source matches the
  audited source; `configuration_hash()` equals the value computed off-chain **before** deployment;
  the record re-derives independently; all four index sets are present and consistent.
- `docs/PROVENANCE.md` updated with network, chain ID, addresses, transaction hashes, validator
  votes, expected and observed hashes, and the live result.

**If the live result differs from the offline expectation, record it and investigate.** Do not re-run
until it agrees. A divergence between an offline expectation and a real multi-validator result is a
finding, and one of the more valuable things a deployment can produce.

**Exit criteria:** a working GenLayer Explorer contract URL, and a live resolution whose result is
recorded whatever it turned out to be.

Stage 5 was the first stage that touched a network. Three failed deployment transactions are
preserved in the provenance record: the first omitted the runner header, and the next two used
scalar CLI transport for `source_urls`. The official native deploy-script attempt 4 then completed
with consensus `AGREE` and execution `FINISHED_WITH_RETURN`; `get_config()`, source bytes, the
configuration hash, and the initial unresolved state all matched. Exactly one live `resolve()` was
submitted and completed with `AGREE` / `FINISHED_WITH_RETURN`, returning `CONFIRMED` and
`2026-03-11`; its record and source buckets re-derived independently.

Read-only finality closure later returned `FINALIZED` / status code `7` for both transactions.
`gen_getContractState(status: finalized)` returned the deployed state, and the finalized reads
reproduced the expected configuration hash, `CONFIRMED` status, and `2026-03-11` value. No
additional transaction was submitted.

---

## 6. Repository quality controls

| Control | Mechanism | Active from |
| --- | --- | --- |
| Python pin | `.python-version` = 3.12; CI `setup-python` 3.12 | Stage 1 |
| Dependency pins | `requirements-dev.txt`, `==` pins throughout | Stage 1 |
| Runner pin | exact GenVM runner hash in the contract header; no `latest`, no `test` alias | Stage 2 |
| LF line endings | `.gitattributes` plus a CI job that fails on any CR byte under the guarded paths | Stage 1 |
| Secret scan | `gitleaks` over full history **and** the working tree, fails on any finding | Stage 1 |
| Fixture schema + derivation | `tools/validate_fixtures.py` — recomputes every expectation rather than trusting it | Stage 1 |
| Fixture generation is not hand-edited | CI regenerates `fixtures/cases/` and fails on a diff | Stage 1 |
| Live evidence verification | `tools/check_evidence_urls.py` — every pinned URL fetched and compared byte for byte; declared-unavailable sources asserted to 404 | Stage 1 |
| Reproducibility manifest | `tools/source_hash.py --check` against `MANIFEST.sha256` | Stage 1 |
| Cross-platform parity | derivation, hash and fixture checks on `windows-latest` | Stage 1 |
| Stage guard | fails if `contracts/*.py` exists without `tests/direct/*.py`, and vice versa | Stage 1 |
| Contract lint | `genvm-lint check` + `validate` under `PYTHONUTF8=1` | Stage 2 |
| Direct-mode tests | `pytest tests/ -v` | Stage 3 |
| Mutation testing | `tools/mutation_test.py`, contract restoration asserted by `git diff --exit-code` | Stage 2 |

### On placeholder tests

There are no tests at Stage 1, because there is no contract to test, and a test that passes with no
contract is a lie about coverage. CI therefore contains **no vacuously-passing test job**. The
`stage-guard` job encodes the Stage 1 state as an assertion in the opposite direction: it passes
while there is no contract, and **fails the moment a contract appears without direct tests beside
it.** The CI summary prints the stage explicitly, so a reader of a green badge sees "Stage 1 — no
contract, no contract tests claimed", not an implied clean test run.

---

## 7. Acceptance-bar analysis

Scored in `OVERLAP-RESEARCH.md` §7. Summary: **63/80 as briefed, 65/80 with the required
modifications**, threshold 65, no critical overlap. The recommendation is **MODIFY**, and the binding
weakness is novelty — the category is occupied by an official implementation and the method is
carried from the same author's previous submission.

The scores were not tuned to clear the threshold. Novelty at 5 as briefed is the honest number, and
the fact that it lands short is why the six modifications in `OVERLAP-RESEARCH.md` §6 are *required*
rather than suggested.
