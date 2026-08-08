# Overlap Research — SourceConsensus

**Stage:** 1 · **Date:** 2026-08-08 · **Recommendation: MODIFY** (§6)

The purpose of this document is to find out whether SourceConsensus should exist, and to say so
honestly if it should not. It was written before any contract code, and the recommendation is
**MODIFY rather than GO** because the acceptance-bar analysis lands at **63/80 as briefed** — two
points under the threshold — for reasons set out in §5 and §7.

Two overlap risks are disclosed up front rather than argued away at the end:

1. **`genlayerlabs/intelligent-oracle` already resolves facts from multiple public sources.** It is
   an official repository. The category is occupied.
2. **The author's own `GIFTEDLOV/semantic-constraint` uses the same architectural method** — the
   model emits atoms, the contract derives the decision — and was deployed days ago. A reviewer
   looking at both submissions will see one idea applied twice.

Neither is fatal, but both are real, and the case for this project has to survive them.

---

## 1. Method

| Source | What was examined |
| --- | --- |
| `genlayerlabs/intelligent-oracle` | **Full contract source read** — `intelligent-contracts/IntelligentOracle.py`, 338 lines, plus the factory and four tests |
| `genlayerlabs/genlayer-acp-evaluator` | **Full contract source read** — `contracts/acp_evaluator.py`, 131 lines |
| GenLayer docs, prediction-market example | Contract source and prose |
| `genlayerlabs` GitHub organisation | All 47 public repositories enumerated |
| GenLayer equivalence-principle documentation | The four consensus APIs and when each applies |
| `GIFTEDLOV/semantic-constraint` | The author's own prior submission (self-overlap, §4) |

Comparisons below quote line numbers from the sources actually read. Where a claim could not be
verified from source, it is marked as such.

## 2. The closest competitor: `intelligent-oracle`

> <https://github.com/genlayerlabs/intelligent-oracle> — *"describe any prediction-market question
> in natural language and let GenLayer's intelligent contracts resolve it from real-world sources."*

This is the nearest thing that exists, it is official, and it overlaps substantially. What it does:

- Accepts `title`, `description`, `potential_outcomes`, `rules`, and either `resolution_urls` or
  `data_source_domains`.
- On `resolve()`, loops over each source, renders it with `gl.nondet.web.render(url, mode="text")`,
  and asks an LLM to pick an outcome **for that source**.
- Then makes a **second LLM call** that reads all the per-source analyses and picks the final
  outcome across them.
- Reaches consensus with `gl.eq_principle.prompt_comparative(fn, principle="`outcome` field must be
  exactly the same. All other fields must be similar")`.

### The one difference that matters

`IntelligentOracle.py` lines 281–299:

```python
result = gl.eq_principle.prompt_comparative(
    evaluate_all_sources,
    principle="`outcome` field must be exactly the same. All other fields must be similar",
)
result_dict = _parse_json_dict(result)
self.analysis = json.dumps(result_dict)
...
self.outcome = result_dict["outcome"]      # line 299
```

**Cross-source reconciliation is an LLM judgement, and the final outcome is a string the model
wrote.** The contract's only checks are membership in `potential_outcomes` and two sentinel values
(`UNDETERMINED`, `ERROR`). When three sources disagree, an LLM decides what that disagreement means,
and the reasoning that produced the decision is stored as free-form prose (`self.analysis`).

SourceConsensus proposes the opposite split. The model is asked only *"what value does **this one**
source state?"*, once per source. Everything after that — whether the sources agree, whether a
competing value is serious enough to constitute a conflict, whether there is enough evidence at all
— is pure contract arithmetic over the per-source values (`ARCHITECTURE.md` §7).

| | `IntelligentOracle` | SourceConsensus |
| --- | --- | --- |
| Per-source extraction | LLM | LLM |
| **Cross-source reconciliation** | **LLM (second prompt)** | **deterministic contract logic** |
| Final status | model writes the string | derived, model has no field for it |
| Disagreement | collapsed into one word + prose | four index sets, on chain |
| Answer shape | free-text outcome from a list | typed, normalised value |
| Consensus rule | NL principle judged by an LLM | set comparison over decision-critical fields |
| Config identity | none | `configuration_hash` |
| Stored prose | `self.analysis` (JSON blob) | none |

### Where `intelligent-oracle` is better

Stated plainly, because a comparison that only flatters one side is not research:

- **It is more flexible.** Free-text outcomes handle questions SourceConsensus cannot express as a
  typed value. "Who won the election?" is natural there; here it needs an ENUM declared up front.
- **`data_source_domains` allows evidence supplied at resolution time**, restricted by domain. That
  is genuinely useful for questions where the URL is not knowable at deployment. SourceConsensus
  deliberately gives this up (`ARCHITECTURE.md` §9) and is narrower for it.
- **It ships a factory** and has a working front end at intelligentoracle.com. It is a product;
  this is a primitive.
- **It is official.** That matters for adoption regardless of technical merit.

## 3. Other implementations examined

### `genlayer-acp-evaluator` — 131 lines

Scores a deliverable 0–100 and derives a verdict band. **It already does the thing this project
would like to claim as its principle.** Line 64 carries the comment:

```python
# Derive verdict from score band — never trust LLM verdict string
```

**So "do not let the model name the outcome" is not novel in this ecosystem.** It is established
practice in an official contract, and any claim to have invented it would be false. What
`acp_evaluator` does *not* do is multi-source: it evaluates one submission, and its consensus rule
accepts numeric tolerance (`abs(proposed["score"] - local["score"]) <= score_tolerance`, line 99),
which is precisely the score-and-tolerance pattern SourceConsensus avoids.

### GenLayer docs — prediction market example

A single hard-coded BBC Sport URL, one LLM call, no multi-source verification and no fallback. It is
a tutorial, not a competitor, but it establishes that the documented pattern is single-source.

### The wider organisation

47 repositories enumerated. Nothing else in `genlayerlabs` is a fact-resolution contract: the
remainder are infrastructure (`genvm`, `genlayer-cli`, `genlayer-py`, `genlayer-js`, the studio, the
linter, the testing suite), the `genswarms` agent product line, or unrelated experiments. No
registry of fact oracles, no multi-source agreement primitive, no typed-fact contract was found.

**Not verified:** hackathon submissions and private repositories are not enumerable. A similar
contract may exist unpublished. This document claims only what public sources support.

## 4. Self-overlap — the disclosure that matters most

The author has just published **`GIFTEDLOV/semantic-constraint`**, deployed to Bradbury on
2026-08-07. It answers *"does this artifact satisfy these natural-language requirements?"* and its
central design rule is:

> The model labels criteria. The contract derives the outcome.

SourceConsensus's central design rule is:

> The model extracts per-source values. The contract derives the status.

**That is the same idea.** So are several of the mechanisms: an identity hash over the immutable
configuration, a canonical record excluding prose, independent validator fetching, no floats
anywhere, and rejection rather than repair of malformed model output. A reviewer who reads both
submissions will notice, and would be right to.

| | SemanticConstraint | SourceConsensus |
| --- | --- | --- |
| Question | does **one artifact** meet **N requirements**? | what is **one value**, per **N sources**? |
| Evidence | 1 artifact (+ optional context) | 2–5 independent sources, each equally weighted |
| Model emits | a label per criterion | a `(state, value)` per source |
| Decision object | a **partition of criteria** | an **agreement across sources** + one typed value |
| Failure mode it exists to prevent | a persuasive artifact talking its way to SATISFIED | one wrong source silently becoming the answer |
| Output | four-way outcome over a criteria set | four-way status + a normalised value |

The decision objects genuinely differ — a partition over requirements is not an agreement across
sources, and neither reduces to the other. But **the method is reused, and the novelty score in §7
reflects that rather than pretending otherwise.**

`docs/PROVENANCE.md` will carry the clean-room statement at Stage 2. To be explicit now: no contract
code, prompt text, storage layout or comparator logic will be copied from `semantic-constraint`,
`uptimebond`, or `constitutioncourt`. The *approach* to repository quality controls (stage guard,
pinned corpus, manifest, LF enforcement) is carried over deliberately as methodology, and this
sentence is the disclosure.

## 5. Is SourceConsensus distinct?

**Distinct enough to build, not distinct enough to call novel.** Splitting the claim:

**Supported by the research**

- No public GenLayer contract performs **deterministic cross-source reconciliation**. Where multiple
  sources exist, an LLM merges them (§2).
- No public GenLayer contract exposes **which sources supported, contested, were unreachable, or
  were too vague** as structured on-chain data. Disagreement is collapsed into one word.
- No public GenLayer contract implements **typed facts with per-type normalisation**. Without it,
  `2026-01-05` and `January 5, 2026` are two answers, and a unanimous corpus reads as a conflict —
  the failure fixture `07-normalisation-equivalent` is built around.
- The distinction between **UNAVAILABLE (could not look) and INSUFFICIENT_EVIDENCE (looked, nothing
  there)** is not drawn anywhere examined. `IntelligentOracle` has one `Error` state for both.

**Not claimed**

- Not that multi-source fact resolution is new. `intelligent-oracle` does it and is official.
- Not that "the contract derives the outcome" is new. `acp_evaluator` does it, in a comment, at line
  64.
- Not that `configuration_hash` is new *for this author* — it is `constraint_hash` from
  `semantic-constraint` with different fields. It appears to be new **in the ecosystem**, on this
  research, but that is a weaker claim than it would be from a different author.

## 6. Recommendation: **MODIFY**

Not GO, because the concept as briefed scores **63/80** (§7) against a 65 threshold, and because the
category is occupied by an official implementation.

Not REJECT, because no *critical* overlap exists: nothing found reconciles sources deterministically,
exposes per-source disagreement, or types the fact — and those three together change what an
integrator can rely on, not merely what the contract reports.

### Required modifications

1. **Lead with the deterministic-reconciliation contrast, not a feature list.** README and submission
   notes must name `intelligent-oracle`, cite line 299, and explain the split in the first section. A
   reviewer who finds that repository *after* reading an unqualified novelty claim will discount
   everything else.
2. **Make per-source disagreement a first-class output.** The four index sets must be in the canonical
   record, not derivable-only. This is the property no examined contract has, and it is what makes
   `CONFLICTED` actionable rather than merely a refusal.
3. **Type the fact and normalise it.** Without normalisation the design has a false-conflict rate that
   makes it worse than the thing it is competing with. Fixture `07` exists to hold this.
4. **Disclose the self-overlap in the README**, not only here. Same author, same method, days apart.
5. **Cap the surface.** No factory, no admin functions, no evidence supplied at resolution time, no
   free-form output schema. Every addition moves this toward being a second `intelligent-oracle`
   with fewer features.
6. **Prove reusability at Stage 4** with two worked integration examples, or drop the reusability
   claim from the README.

With 1–3 adopted, novelty moves 5 → 6 and ecosystem value 8 → 9, giving **65/80**, which clears the
bar by exactly one point. That is not a comfortable margin and the analysis does not pretend it is.

## 7. Acceptance-bar analysis

Scored out of 10 on eight axes; threshold 65/80 with no critical overlap. Reported in both forms —
as briefed, and with the §6 modifications.

| Axis | As briefed | Modified | Reasoning |
| --- | ---: | ---: | --- |
| Practical usefulness | 8 | 8 | Prediction-market resolution, insurance triggers, compliance attestation and release verification are real, funded decisions that turn on one bounded fact. Not 9: the fact must fit one typed value, which excludes narrative questions. |
| Reusability | 8 | 8 | No domain vocabulary, no value handling, configuration entirely in constructor arguments, cheap enum read for cross-contract use. Not 9 because reusability is asserted at Stage 1 and only demonstrated at Stage 4. |
| Need for intelligent consensus | 9 | 9 | Reading heterogeneous public pages for one fact is exactly what a deterministic contract cannot do, and a single oracle reintroduces the trusted party. Independent validator fetching is load-bearing. Not 10 because a centralised scraper would produce *an* answer — just not a trustless one. |
| **Novelty** | **5** | **6** | **5 as briefed:** `intelligent-oracle` occupies the category officially; `acp_evaluator` already derives outcomes rather than trusting the model's string; and the method is carried from the same author's `semantic-constraint`, published days earlier. **6 with modifications:** deterministic cross-source reconciliation, structured per-source disagreement, and typed normalisation are, on this research, unimplemented in the ecosystem — but they are increments on an occupied idea, not a new one. |
| Educational value | 8 | 8 | Three transferable lessons: reconcile deterministically rather than by prompt; normalise before comparing or unanimity reads as conflict; separate "could not look" from "nothing there". |
| Testability | 9 | 9 | `derive_status` and `normalise_value` are pure and exhaustively testable without a VM; the state and status spaces are small enough to enumerate; the fixture corpus is commit-pinned. Not 10 because end-to-end behaviour still depends on LLM extraction that can only be sampled. |
| Implementation simplicity | 8 | 8 | Smaller than the contract it is compared against: one value, one write, no factory, no admin surface, no floats. Not 9 because normalisation carries real per-type complexity. |
| Ecosystem value | 8 | **9** | 8 as briefed: a reusable primitive where the ecosystem currently has an application. 9 with modifications: `configuration_hash` makes an oracle's question pinnable by a consumer, and the four index sets make disagreement composable — two properties the ecosystem has no way to express today. |
| **Total** | **63 / 80** | **65 / 80** | |

**Reading of the result.** As briefed the concept is **two points short**, and the binding weakness
is novelty for a defensible reason: this is an occupied category, and the author has just shipped a
contract built the same way. With the modifications it reaches exactly the threshold. **The scores
were not tuned to clear the bar** — novelty at 5 is the honest number, and the fact that it lands
short is the reason the modifications are *required* rather than suggested.

**No critical overlap was found.**

---

## Sources

- [genlayerlabs/intelligent-oracle](https://github.com/genlayerlabs/intelligent-oracle)
- [genlayerlabs/genlayer-acp-evaluator](https://github.com/genlayerlabs/genlayer-acp-evaluator)
- [GenLayer docs — Prediction Market Contract](https://docs.genlayer.com/developers/intelligent-contracts/examples/prediction)
- [GenLayer docs — Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle)
- [GenLayer Labs GitHub organisation](https://github.com/genlayerlabs)
- [Intelligent Oracle product site](https://www.intelligentoracle.com/)
- [GIFTEDLOV/semantic-constraint](https://github.com/GIFTEDLOV/semantic-constraint) — self-overlap
