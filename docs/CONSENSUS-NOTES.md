# Consensus Notes

Schema version 2 binds the complete ordered per-source payload. The leader and each validator fetch
the same immutable configured URL list independently and extract one `(state, normalized value)`
pair per isolated prompt. The contract, not the model, derives the aggregate.

Before independent extraction, a validator requires exactly N states and values, exact state
vocabulary, canonical VALUE scalars, and null for non-VALUE states. It runs `_derive_status` over
the leader payload and requires exact equality for status, normalized aggregate value, supporting,
conflicting, unavailable, ambiguous, and no-value indices. It then independently reproduces all N
source pairs and the aggregate. Any source mismatch is `DISAGREE`.

Post-consensus deterministic code validates the returned payload again and re-derives storage from
its bound states/values. This intentionally supersedes schema version 1's supporting-only boundary.
The stronger rule may reduce liveness under fetch/model variance, but no decision-relevant or public
diagnostic field remains outside the Equivalence Principle.

Derivation follows [`DERIVATION.md`](DERIVATION.md): insufficient reachability yields
`UNAVAILABLE`; qualifying competing values or a top tie yield `CONFLICTED`; a unique leader meeting
minimum support yields `CONFIRMED`; otherwise the result is `INSUFFICIENT_EVIDENCE`.
