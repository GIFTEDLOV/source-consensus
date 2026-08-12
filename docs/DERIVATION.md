# Derivation — the truth table

**Written before `_derive_status` was coded**, as the Stage 2 brief requires. This document is the
specification; the contract implements it and `tools/canonical.py` implements it independently. If
the three ever disagree, at least one is wrong and the parity tests say so.

---

## 1. Inputs

| Input | Origin | Notes |
| --- | --- | --- |
| `results[i] = (state, value)` for every configured index | **model**, one prompt per source | `value` present iff `state == VALUE`, already normalised |
| `n` — configured source count | constructor | 2–5 |
| `min_support` — `minimum_supporting_sources` | constructor | 2–5, ≤ `n` |
| `conflict_threshold` | constructor | 1–5 |

The model supplies **only** the first row. Everything else is immutable configuration, and there is
no field anywhere in the response schema in which a model could express a status.

## 2. Derived quantities

```
unavailable  = { i : state[i] == UNAVAILABLE }
ambiguous    = { i : state[i] == AMBIGUOUS   }
no_value     = { i : state[i] == NO_VALUE    }
tally[v]     = { i : state[i] == VALUE and value[i] == v }        # normalised values
reachable    = n - |unavailable|
contenders   = { v : |tally[v]| >= conflict_threshold }
leader       = argmax |tally[v]|,  ties broken by lexicographic v   # see section 5
```

`reachable` counts sources that answered *at all*, including `NO_VALUE` and `AMBIGUOUS`. A source
that was read and had nothing useful to say was still **read**; only a fetch failure is unreachable.

## 3. The truth table

Evaluated top to bottom. **The first matching row wins** — the ordering is load-bearing and §4
justifies each edge.

| # | Condition | `status` | `normalized_value` | `supporting` | `conflicting` |
| --- | --- | --- | --- | --- | --- |
| 1 | `reachable < min_support` | `UNAVAILABLE` | `null` | `[]` | `[]` |
| 2 | `tally` is empty | `INSUFFICIENT_EVIDENCE` | `null` | `[]` | `[]` |
| 3 | `\|contenders\| >= 2` **or the top count is not unique** | `CONFLICTED` | `null` | `[]` | every `VALUE` index |
| 4 | `\|tally[leader]\| >= min_support` | `CONFIRMED` | `leader` | `tally[leader]` | every non-leader `VALUE` index |
| 5 | otherwise | `INSUFFICIENT_EVIDENCE` | `null` | `[]` | every `VALUE` index |

`unavailable`, `ambiguous` and `no_value` index sets are reported in **every** row, unchanged by
which row matched. They describe what happened to each source, not what was decided.

### The uniqueness clause in row 3, and why it was added

**This clause was missing from the first draft of this table, and a test caught it before the
contract shipped.** The failing case:

| `n` | `min` | `ct` | States | Without the clause | With it |
| ---: | ---: | ---: | --- | --- | --- |
| 4 | 2 | **3** | `B B A A` | `CONFIRMED A` | `CONFLICTED` |

With `conflict_threshold = 3`, neither value reaches it, so row 3's contender test does not fire.
Row 4 then asks only whether the *leader* has enough support — and the leader is chosen by the §5
tie-break, which is **lexicographic**. The result was `CONFIRMED "A"` because `A` sorts before `B`.

Confirming a dead-heat by alphabetical order is indefensible. A tie at the top is the clearest
possible dispute, and no threshold setting should be able to turn it into an answer. `ct` governs
whether a *lesser* competing value is serious enough to contest a genuine leader; it was never
meant to decide what happens when there is no leader at all.

The clause makes the tie-break's role explicit: it exists to pin *determinism* (§5), never to pick
a winner. `tools/mutation_test.py` removes the clause as one of its mutations.

### Worked rows

| Scenario | `n` | `min` | `ct` | States | Row | Result |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| Unanimous | 3 | 2 | 2 | `A A A` | 4 | `CONFIRMED A`, supporting `[0,1,2]` |
| Majority, one outlier | 4 | 2 | 2 | `A A A B` | 4 | `CONFIRMED A`, supporting `[0,1,2]`, conflicting `[3]` |
| **Plurality, two contenders** | 5 | 2 | 2 | `A A A B B` | **3** | **`CONFLICTED`** — *not* `CONFIRMED A` |
| Even split | 4 | 2 | 2 | `A A B B` | 3 | `CONFLICTED`, conflicting `[0,1,2,3]` |
| Sensitive threshold | 3 | 2 | 1 | `A A B` | 3 | `CONFLICTED` — `ct=1` makes any dissent a conflict |
| Tolerant threshold | 3 | 2 | 3 | `A A B` | 4 | `CONFIRMED A` — `B` never reaches `ct` |
| One value only | 3 | 2 | 2 | `A – –` | 5 | `INSUFFICIENT_EVIDENCE`, conflicting `[0]` |
| All silent | 3 | 2 | 2 | `– – –` | 2 | `INSUFFICIENT_EVIDENCE` |
| All vague | 3 | 2 | 2 | `? ? ?` | 2 | `INSUFFICIENT_EVIDENCE`, ambiguous `[0,1,2]` |
| One dead, two agree | 3 | 2 | 2 | `A A ✕` | 4 | `CONFIRMED A`, unavailable `[2]` |
| Two dead | 3 | 2 | 2 | `A ✕ ✕` | 1 | `UNAVAILABLE` — reachable 1 < 2 |
| All dead | 3 | 2 | 2 | `✕ ✕ ✕` | 1 | `UNAVAILABLE` |

Legend: `A`/`B` = `VALUE`, `–` = `NO_VALUE`, `?` = `AMBIGUOUS`, `✕` = `UNAVAILABLE`.

## 4. Why the ordering is what it is

**Row 1 before everything.** If too few sources could be fetched, `min_support` was unreachable no
matter how good the extraction was. The failure is in the fetch, not in the world, and the two call
for opposite responses: retry versus accept. Putting row 1 anywhere else would report
`INSUFFICIENT_EVIDENCE` for a network outage and tell an integrator to find better sources when the
sources were fine.

This is also why row 1 is the only non-terminal status (`ARCHITECTURE.md` §10.1).

**Row 3 before row 4 — the single most important edge.** When two values each reach
`conflict_threshold`, the result is `CONFLICTED` **even when one has strictly more support**. The
`A A A B B` row is the case that matters: a plurality of 3–2 is *not* a confirmation.

An oracle that resolves a genuine dispute by counting is worse than one that reports the dispute,
because the integrator loses the ability to escalate — and escalation is precisely what a 3–2 split
on a funded decision should trigger. Plurality is what a reconciling prompt would do. Refusing to is
the entire argument for this contract over
[`intelligent-oracle`](https://github.com/genlayerlabs/intelligent-oracle) (`OVERLAP-RESEARCH.md`
§2), so weakening it would remove the reason the project exists.

`tools/mutation_test.py` breaks exactly this ordering as its first mutation.


**Row 2 before rows 3–5** is a convenience, not a semantic choice: with an empty tally, rows 3 and 4
cannot match and row 5 would produce the same answer. It is separated so the "reachable but nobody
stated the fact" case is legible in the code rather than emergent.

**Row 5 as the default.** Everything reachable that did not confirm and did not conflict is a
shortfall of usable agreement. Note it still reports `conflicting` indices: a lone `VALUE` that
failed to reach `min_support` is recorded, so an integrator can see the query was *nearly* answered
rather than untouched.

### A note from implementation: two mutations that survived for the right reason

Stage 2's first mutation run reported three problems, and two of them were **equivalent mutants**
rather than coverage holes. Removing the dedicated `UNAVAILABLE`-from-the-model guard survived
because the general enum check caught it one line later; removing the post-consensus state check
survived because `_normalise_source_output` had already rejected it. Defence in depth makes
single-point mutations misleading, so both now break **both** guard sites.

The third was a real defect, and in the *test* rather than the contract: `pytest.raises(Exception)`
accepted an incidental `TypeError` raised deep in `_derive_status` when an invalid state reached
the tally and `None` was sorted against a string. The test passed while the guard it claimed to
pin was gone. It now asserts the `[LLM_ERROR]` classification, so the response must be rejected
*deliberately* rather than merely crash. **A test that accepts any exception is not testing a
guard; it is testing that something, somewhere, went wrong.**

## 5. Determinism requirements

Two independent validators must derive byte-identical results from identical inputs, so every
ordering is pinned:

| Quantity | Rule |
| --- | --- |
| `leader` when two values tie on support | **most support first, then lexicographic on the normalised value.** Never insertion order, never dict iteration order. |
| All five index sets | ascending integer sort |
| `contenders` membership | `>=`, not `>` |
| Value comparison | exact string equality **after** normalisation (`ARCHITECTURE.md` §6) |

The tie-break is not cosmetic. With `A A B B` and `ct = 3`, no contender exists, row 4 fails on
support, and row 5 matches — but `leader` still appears in intermediate computation, and two nodes
that picked different leaders from the same tally would diverge on nothing observable today and on
something observable after any future change. Pinning it now costs one `sorted` key.

## 6. What the model cannot reach

Every field above is either configuration or a set derived from per-source `(state, value)` pairs.
There is no path from model output to:

- the status — no such field exists in the response schema;
- `min_support` or `conflict_threshold` — constructor state, committed to `configuration_hash`;
- the source count or any index — derived from the configured URL list;
- another source's state — each source is extracted in its own prompt with only its own text.

The strongest thing a fully compromised source can do is contribute one wrong `VALUE`, which lands
in `conflicting` and, if `conflict_threshold` is low, converts a confirmation into a conflict. It
can cause a **refusal to answer**. It cannot cause a **wrong answer** without a majority of the
configured sources agreeing with it.

## 7. Consensus scope

Schema version 2 has one consensus tier. Validators bind every per-source state and normalized value
at its immutable configured index. Before any independent fetch, a validator validates the leader
arrays, canonical value representation, and exact source count, then re-runs this document's
derivation over the leader payload. The derived result must exactly match all advertised aggregate
fields:

- `status`;
- `normalized_value`;
- `supporting_source_indices`;
- `conflicting_source_indices`;
- `unavailable_source_indices`;
- `ambiguous_source_indices`;
- `no_value_source_indices`.

The validator then independently extracts every source, compares every `(state, value)` pair by
index, independently derives the aggregate, and compares every field above. Post-consensus storage
validates the full payload again and derives from its states and values instead of trusting the
leader's aggregate.

This replaces the rejected schema-version-1 rule that left non-supporting buckets outside the
comparator even though final derivation consumed them. No decision-relevant or public diagnostic
field remains outside validator consensus.
