# README ↔ Contract Parity Register

Reviewed against `contracts/source_consensus.py` schema version 2 on 2026-08-12.

| README claim | Classification | Evidence |
| --- | --- | --- |
| one typed value per deployment; 2–5 explicit sources | MATCHES CODE | immutable constructor and `MIN_SOURCES`/`MAX_SOURCES` |
| no admin, mutable list, search, escrow, payout, or value transfer | MATCHES CODE | lint surface is 8 views + `resolve`; no setters/value APIs |
| one isolated prompt per source | MATCHES CODE | `extract_all` loop and prompt-isolation adversarial tests |
| model cannot choose aggregate status | MATCHES CODE | exact two-field model schema; aggregate fields forbidden; `_derive_status` only producer |
| complete per-source consensus binding | MATCHES CODE | `_validate_consensus_payload`, `_agree`, 28-case regression matrix |
| source order and identity are immutable/hash-significant | MATCHES CODE | ordered storage/config payload and reordering hash tests |
| deterministic type normalization and no floats | MATCHES CODE | per-type direct/reference tests; float rejection; integer timestamp path |
| four statuses; conflict/tie precedence | MATCHES CODE | 70,800 exhaustive contract/reference derivations |
| UNAVAILABLE retryable; other three terminal | MATCHES CODE | lifecycle and mutation tests |
| five source index sets | MATCHES CODE | result/record/source partition tests |
| pinning fails closed | MATCHES CODE | URL classifier and constructor tests; live URL checker |
| prompt injection cannot change control fields | MATCHES CODE | structural prompt isolation and adversarial corpus/tests |
| majority-wrong evidence can confirm wrong value | MATCHES CODE | documented limitation and adversarial test |
| 9 public methods: 8 view, 1 write | MATCHES CODE | GenVM lint/semantic schema output |
| configuration hash commits consensus semantics | MATCHES CODE | schema v2 plus per-field hash-change/reference tests |
| v1 deployment is current secure release | HISTORICAL ONLY | explicitly superseded after steward rejection |
| real-provider convergence measured | STALE claim removed | provider run remains NOT RUN without a key |
| current corrected Bradbury address/tag/CI | MATCHES LIVE RELEASE | README links the finalized schema-v2 address, corrected tag, and exact-head green CI |

Final parity verdict: all current behavior/security and live-release claims match corrected code and
the finalized Bradbury evidence.
