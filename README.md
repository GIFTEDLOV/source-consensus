# SourceConsensus

**What single value do these specific public sources say, and do they agree?**

SourceConsensus is a reusable GenLayer Intelligent Contract primitive. One deployment resolves one
immutable typed question from 2–5 explicit public HTTPS sources. It has no admin, mutable source
list, search, parties, escrow, payout, or value-transfer logic.

> **Security-remediation status:** `v1.0.0-bradbury` deployed and finalized successfully, but the
> steward rejected its consensus boundary. Validators bound aggregate/supporting detail while the
> contract later derived storage from every leader-provided source entry. That deployment is
> `SUPERSEDED_AFTER_STEWARD_CONSENSUS_BINDING_REVIEW` and must not be resubmitted as secure.
>
> Corrected release `v1.0.1-bradbury` binds every per-source state and normalized value, verifies
> the leader aggregate by deterministic re-derivation, independently reproduces the full
> extraction, and re-derives storage from the same validated payload. Its new Bradbury contract is
> [`0x2084107B5274FB82FDE29Bbe4794517309AdE2b9`](https://explorer-bradbury.genlayer.com/contract/0x2084107B5274FB82FDE29Bbe4794517309AdE2b9),
> deployed and resolved to finality from exact-head CI run
> [31593257570](https://github.com/GIFTEDLOV/source-consensus/actions/runs/31593257570).

## Contract model

The model receives exactly one source per prompt and returns exactly one JSON object:

```json
{"state":"VALUE|NO_VALUE|AMBIGUOUS","value":"canonical scalar or null"}
```

`UNAVAILABLE` is determined only by the contract's fetch outcome. The model has no field for an
aggregate status, threshold, confidence, source list, or other source. The contract normalizes each
VALUE and deterministically derives one of four statuses:

| Precedence | Condition | Status | Lifecycle |
| --- | --- | --- | --- |
| 1 | reachable sources are fewer than `minimum_supporting_sources` | `UNAVAILABLE` | retryable |
| 2 | multiple values reach `conflict_threshold`, or the lead is tied | `CONFLICTED` | terminal |
| 3 | one unique value reaches `minimum_supporting_sources` | `CONFIRMED` | terminal |
| 4 | otherwise | `INSUFFICIENT_EVIDENCE` | terminal |

Conflict precedes confirmation. A 3–2 split is `CONFLICTED` when both values reach the configured
conflict threshold; a tie can never confirm through lexicographic ordering.

Every result exposes five disjoint, sorted index sets: supporting, conflicting, unavailable,
ambiguous, and no-value. Source order is immutable and hash-significant.

## Steward Consensus-Binding Remediation

Old schema version 1 compared the leader's status, normalized aggregate value, supporting indices,
and supporting source pairs. It did not bind every non-supporting source entry. Post-consensus code
then consumed all leader states and values, so unchecked entries could change a claimed
`CONFIRMED A` payload into `CONFLICTED` during storage derivation.

Schema version 2 authenticates one canonical payload containing:

- exactly N states and N values in configured source order;
- every exact per-source state and canonical normalized value;
- status and normalized aggregate value;
- all five derived index sets.

A validator rejects malformed arrays or source pairs, re-derives the leader aggregate, independently
fetches/extracts all N sources, compares every pair by index, and independently derives all aggregate
fields. After consensus, storage validates the payload again and derives from its states/values; it
does not trust leader aggregate fields. The schema bump intentionally changes every configuration
hash so corrected deployments cannot reuse the identity of the rejected semantics.

## Types and normalization

| Type | Canonical form | Rejected examples |
| --- | --- | --- |
| `DATE` | real Gregorian `YYYY-MM-DD`, years 0001–9999 | vague or impossible dates |
| `INTEGER` | strict base-10 string, optional minus, optional configured bounds | floats, exponent, commas, booleans |
| `BOOLEAN` | `true` / `false` (`yes` / `no` normalize explicitly) | `1`, `0`, uncertain text |
| `ENUM` | declared member; optional case-insensitive lookup returns declared spelling | undeclared values |
| `STRING` | whitespace-normalized, optional lower-case policy, at most 200 chars | lists, objects, floats, oversized text |

Malformed model output is rejected, not repaired. This includes surrounding commentary, multiple
JSON payloads, missing or unexpected fields, unknown or non-exact states, model-supplied
`UNAVAILABLE`, forbidden aggregate/confidence fields, non-null values on non-VALUE states, and any
VALUE that fails configured normalization.

## Prompt and evidence boundary

Each configured URL is HTTPS, unique, bounded, ordered, and classified as pinned or mutable.
`require_pinned_evidence=true` fails closed unless every URL is commit- or content-addressed.
Evidence is fetched only inside the nondeterministic block, normalized, visibly truncated at 24,000
characters, and has fence-like text neutralized before prompting.

One source is never in context while another is extracted. Source text therefore cannot directly
change the question, type, index, source membership, thresholds, another source's availability, or
the final status. It can still lie about its own fact. If enough configured sources are wrong in the
same direction, SourceConsensus can confirm a wrong value; source selection remains the integrator's
responsibility.

## Immutable configuration identity

`configuration_hash()` is keccak256 over canonical schema version, query ID, question, fact type,
normalization rules, enum membership, ordered source URLs, thresholds, and pinned-evidence policy.
Enum order is canonicalized because membership is a set; source order is preserved because indices
are semantic. [`tools/canonical.py`](tools/canonical.py) is the independent off-chain oracle.

## Public interface

GenVM lint reports 9 public methods: 1 write and 8 views.

- write: `resolve()`;
- views: `status()`, `value()`, `get_result()`, `get_record()`, `is_resolved()`, `get_sources()`,
  `get_config()`, `configuration_hash()`.

`CONFIRMED`, `CONFLICTED`, and `INSUFFICIENT_EVIDENCE` cannot be replayed. `UNAVAILABLE` records the
complete bound source detail, increments attempts, and leaves the query open for a later retry.
`resolved_at` is derived in integer arithmetic from the timezone-qualified transaction datetime.

## Verification

```powershell
python -m pytest
python tools/validate_fixtures.py
python tools/convergence.py
python tools/mutation_test.py
python tools/source_hash.py --check
python tools/check_evidence_urls.py
python tools/make_deployable.py contracts/source_consensus.py artifacts/source_consensus_deployable.py
```

The offline convergence harness does not claim real-model measurements. Without
`OPENROUTER_API_KEY`, provider metrics are explicitly `not-run`. With a key, consensus compatibility
requires complete ordered source-payload agreement and reports state, normalized-value, every
aggregate field, and repeatability with explicit n/N denominators.

Historical deployment provenance is retained in [`docs/PROVENANCE.md`](docs/PROVENANCE.md). The
current architecture, derivation, runtime due diligence, threat model, deployment gate, and concise
steward package are in [`docs/`](docs/).

## License

MIT. See [`LICENSE`](LICENSE).
