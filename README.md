# SourceConsensus

**What single value do these specific public sources say, and do they agree?**

A reusable GenLayer Intelligent Contract primitive. Not an application. It holds no value, has no
parties, settles nothing, and has no admin functions. It resolves one bounded, typed fact from 2–5
independently fetchable public sources and publishes a consensus-backed result other contracts can
branch on.

> **Status: Stage 1 — research and architecture. No contract exists yet.**
> Nothing has touched a network: no deployment, no wallet signature, no GEN.
> Nine fixture cases · commit-pinned evidence corpus · derivation rules executable today.
>
> **Recommendation: MODIFY**, scoring **63/80 as briefed** against a 65 threshold.
> The category is already occupied by an official implementation, and the method is carried from
> this author's previous submission. Both are disclosed in
> [`docs/OVERLAP-RESEARCH.md`](docs/OVERLAP-RESEARCH.md) before anything else is claimed.

---

## What already exists, and what is different

[`genlayerlabs/intelligent-oracle`](https://github.com/genlayerlabs/intelligent-oracle) already
resolves prediction-market questions from multiple real-world sources. It is official, it works, and
it is more flexible than this design in ways [`docs/OVERLAP-RESEARCH.md`](docs/OVERLAP-RESEARCH.md)
§2 sets out. **Multi-source fact resolution on GenLayer is not new and this repository does not claim
it is.**

The difference is one line. `IntelligentOracle.py` line 299:

```python
self.outcome = result_dict["outcome"]
```

The final answer is a string the model wrote. Reconciling several disagreeing sources is done by a
**second LLM call** whose prompt reads all the per-source analyses and picks the result.

SourceConsensus splits it the other way. The model is asked only *"what value does **this one**
source state?"* — once per source, each in its own prompt. Everything after that is arithmetic:

```
model  ->  [ {source 0: VALUE "2026-02-09"},
             {source 1: VALUE "2026-02-09"},
             {source 2: VALUE "2026-02-16"},
             {source 3: VALUE "2026-02-16"} ]

contract -> status = CONFLICTED        (two values, each reaching the threshold)
            value  = null
            supporting  = []
            conflicting = [0, 1, 2, 3]
```

No field in the model's response can hold a status. The contract derives it.

| | `intelligent-oracle` | SourceConsensus |
| --- | --- | --- |
| Per-source extraction | LLM | LLM |
| **Cross-source reconciliation** | **LLM (second prompt)** | **deterministic contract logic** |
| Final status | model writes the string | derived; no field exists for it |
| Disagreement | collapsed to one word + prose | four index sets, on chain |
| Answer shape | free text from a list | typed and normalised |
| Config identity | none | `configuration_hash` |

**Honest counterweight:** *"don't trust the model's verdict string"* is **not** novel here.
`genlayer-acp-evaluator` already does it, in a comment, at line 64. What appears to be unimplemented
in the ecosystem is doing it **across sources**, with typed normalisation and structured
disagreement. That is an increment on an occupied idea, and the novelty score says so.

## The four statuses

Derived by [`tools/canonical.py`](tools/canonical.py) `derive_status`, in this precedence:

| # | Condition | Status | What an integrator should do |
| --- | --- | --- | --- |
| 1 | too few sources reachable to have met the threshold | `UNAVAILABLE` | retry — this is a fetch failure, not a fact |
| 2 | ≥ 2 distinct values each reach `conflict_threshold` | `CONFLICTED` | escalate — the sources genuinely disagree |
| 3 | leading value reaches the minimum, nothing competes | `CONFIRMED` | act on the value |
| 4 | otherwise | `INSUFFICIENT_EVIDENCE` | better sources, or a better-typed question |

**Rule 2 sits before rule 3 deliberately.** When two values each have real support, the answer is
`CONFLICTED` *even if one has more support*. Resolving a genuine dispute by plurality is what a
prompt would do; refusing to is the point.

## Why the four index sets matter

Every result carries `supporting`, `conflicting`, `unavailable` and `ambiguous` source indices. They
are not decoration — **each one implies a different corrective action**:

```python
r = oracle.get_result()
if r["status"] == "CONFLICTED":
    review(competing_sources=r["conflicting_source_indices"])
elif r["status"] == "UNAVAILABLE":
    retry_later(dead=r["unavailable_source_indices"])
elif r["status"] == "INSUFFICIENT_EVIDENCE":
    if r["ambiguous_source_indices"]:
        suggest_retyping_the_query()   # sources answered, but vaguely
    else:
        suggest_better_sources()       # sources were simply silent
```

A status word alone cannot tell you whether to retry, escalate, re-type the question, or find better
sources. No contract examined during the research exposes this.

## Normalisation is not a detail

Three sources saying `2026-01-05`, `5 January 2026` and `January 5, 2026` are stating **one fact**.
Without normalisation to a canonical form, a unanimous corpus derives `CONFLICTED` — a silent false
negative that looks like diligence. Fixture `07-normalisation-equivalent` exists to hold this.

| Type | Canonical form | Rejected |
| --- | --- | --- |
| `DATE` | `YYYY-MM-DD`, real-calendar validated | `September 2026`, `2026-02-30` |
| `INTEGER` | strict base-10, bounded, **no floats** | `1,200`, `1.0`, `1e3` |
| `BOOLEAN` | `true` / `false` | anything else |
| `ENUM` | exact membership in declared values | undeclared values |
| `STRING` | normalised, ≤ 200 chars | longer values |

A `VALUE` whose payload does not normalise is a **malformed response**, not an ambiguous source: the
whole response is rejected. Repairing it would be guessing at intent, and two validators guessing
independently is a divergence.

## Prompt injection has no channel

Fixture `06-injection-redefine` carries a forged `[SYSTEM]` block demanding a changed `fact_type`, a
forced `CONFIRMED`, an invented `source_index 9`, and the other sources marked `UNAVAILABLE`. Every
one targets a field the model does not control:

| The injection asks for | Why it cannot happen |
| --- | --- |
| status `CONFIRMED` | no status field exists in the response schema |
| `fact_type` changed | constructor state, hashed into `configuration_hash` |
| add `source_index 9` | indices come from the configured URL list |
| mark other sources `UNAVAILABLE` | each source is extracted in **its own prompt** |

**The worst a compromised source can do is corrupt its own value** — costing it one index out of
2–5, visible in `conflicting_source_indices`.

**The honest residual:** if a *majority* of configured sources are wrong in the same direction, the
contract confirms the wrong value. That is a source-selection problem and no contract-side rigour
fixes it.

## Repository

```
docs/OVERLAP-RESEARCH.md   ecosystem audit, self-overlap disclosure, MODIFY recommendation
docs/ARCHITECTURE.md       the design; every open question answered in place
docs/BUILD-PLAN.md         five stages, quality controls, acceptance-bar analysis
docs/CI.md                 exact CI job definitions
tools/canonical.py         independent reference implementation -- normalisation, derivation, hash
tools/make_fixtures.py     generates the fixture cases so the pinned commit lives in one place
tools/validate_fixtures.py schema + structure + recomputed derivation + URL policy
tools/check_evidence_urls.py  fetches every pinned URL and compares bytes to the local corpus
fixtures/cases/            nine cases; all four statuses, nine categories
fixtures/corpus/           25 evidence documents, served commit-pinned over HTTPS
```

Try the rules yourself, without a contract:

```bash
pip install jsonschema "eth-hash[pycryptodome]"
python tools/validate_fixtures.py      # recomputes all nine expectations
python tools/canonical.py derive fixtures/cases/03-two-competing.json
```

## Self-overlap, disclosed

This author published [`GIFTEDLOV/semantic-constraint`](https://github.com/GIFTEDLOV/semantic-constraint)
days before this repository. Its rule is *"the model labels criteria, the contract derives the
outcome"*; this one's is *"the model extracts per-source values, the contract derives the status"*.
**That is the same method**, along with the identity hash, the prose-free canonical record, and the
no-floats rule.

The decision objects genuinely differ — a partition over requirements is not an agreement across
sources — but the method is reused, and the novelty score reflects that rather than pretending
otherwise. [`docs/OVERLAP-RESEARCH.md`](docs/OVERLAP-RESEARCH.md) §4 sets out the comparison in
full.

## Limitations

- One typed value per deployment. Multi-field facts need multiple instances.
- 2–5 sources. Broad survey questions are out of scope.
- **The answer is only as good as the source list.** A majority-wrong evidence base yields a
  confidently wrong `CONFIRMED`.
- Narrative answers cannot be expressed; `intelligent-oracle` is better for those.
- Live sources drift between fetches; `require_pinned_evidence` helps only where an immutable form
  exists.
- **Convergence is unmeasured.** Whether real models agree on `supporting_source_indices` is the
  largest open question — [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §11 states the risk and
  Stage 3 must measure it before any convergence claim is made.

## Stage 3 convergence

Run the offline harness with `python tools/convergence.py`. It validates all nine fixtures and
adversarial response categories without a key. An opt-in OpenRouter run uses five models, logs raw
JSONL responses, and reports metrics with explicit `n/N` denominators. HTTP 402/429, provider
errors, transport failures, and truncation are not counted as model disagreement. See
[`docs/CONVERGENCE-REPORT.md`](docs/CONVERGENCE-REPORT.md).

## Status of this repository

Stage 3 of five. The contract has direct-mode tests and mutation coverage. Offline convergence and
adversarial validation pass; real-model convergence remains explicitly not-run until a runtime
`OPENROUTER_API_KEY` is supplied. Stage 5 Bradbury deployment remains required.

Stage 5 — Bradbury deployment and one live resolution — is **required, not optional**: the
submission needs a GenLayer Explorer contract URL.

## Licence

MIT. See [`LICENSE`](LICENSE).
