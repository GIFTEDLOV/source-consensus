# CI — exact jobs

Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). Triggers: `push` to any branch,
`pull_request`, `workflow_dispatch`. Runner: `ubuntu-latest` (plus `windows-latest` for job 8).
Python: **3.12**, pinned — `genlayer-test` and `genlayer-py` both declare `requires_python >=3.12`.

Jobs whose subject does not exist yet do not silently pass. They are governed by `stage-guard`,
which asserts the repository is in a *coherent* state for whatever stage it is in.

---

## Job 1 — `stage-guard`

**Purpose:** make it impossible for a green badge to imply contract test coverage that does not
exist.

```
contracts/*.py present?   tests/direct/*.py present?   Result
-----------------------   --------------------------   -----------------------------------------
no                        no                           PASS  — "Stage 1: no contract, none claimed"
no                        yes                          FAIL  — tests without a contract under test
yes                       no                           FAIL  — contract without direct-mode tests
yes                       yes                          PASS  — proceeds to lint + test jobs
```

At Stage 1 this job passes *and prints the stage* into the CI summary, so a reader of a green badge
sees `Stage 1 — research and architecture only` rather than an implied clean test run. It becomes a
hard gate the moment Stage 2 adds a contract file.

## Job 2 — `line-endings`

Fails if any byte `0x0D` appears under `contracts/`, `docs/`, `examples/`, `fixtures/`, `tools/`, or
`.github/`. `.gitattributes` normalises on checkout; this verifies the normalisation actually held,
which matters because the fixture corpus is hashed (job 5) and served over HTTPS as evidence — a
CRLF would change both the hash and the bytes a validator reads.

The two are not redundant: a file written by a tool *after* checkout bypasses the attribute
entirely. Implementation: `tools/check_line_endings.py`.

## Job 3 — `secret-scan`

`gitleaks` 8.30.1, invoked as a pinned binary rather than through `gitleaks-action`, with
`fetch-depth: 0`. Two passes: `gitleaks git` over the full commit history and `gitleaks dir` over
the working tree. Any finding fails the build.

**Why the binary, not the action.** `gitleaks-action` scans only the push range, which it forms as
`<base>^..<head>`. When the base is the repository's root commit that expression is unresolvable and
the action exits 1 having scanned zero bytes — a failure that looks like a finding but is not one,
and which would equally have hidden a real finding behind a broken scan.

No allowlist file. There are no credentials in this repository by design: nothing in Stages 1–4
authenticates to anything.

## Job 4 — `fixtures`

`python tools/validate_fixtures.py`. Four checks, all fatal:

1. **Schema** — every `fixtures/cases/*.json` validates against `fixtures/schema/fixture.schema.json`
   (Draft 2020-12, `jsonschema==4.23.0`).
2. **Structural consistency** — source indices are dense and match the configured URL count; a
   `VALUE` result carries a payload that normalises under the declared `fact_type` **and is already
   canonical**; non-`VALUE` results carry no value; `ENUM` has allowed values and nothing else does.
3. **Derivation** — the declared `expected` is recomputed with `tools/canonical.py` and must match.
   This makes the fixture corpus an executable check on the status-derivation rules **before any
   contract exists**, which is the whole reason it is written at Stage 1.
4. **URL policy** — every source URL is `https://`, within 400 characters, and commit-pinned to a
   40-hex sha.

The job then **regenerates `fixtures/cases/` from `tools/make_fixtures.py` and fails on any diff.**
The cases are generated because the pinned commit appears in every URL; a hand edit that updates
eight of nine is exactly the drift the corpus exists to prevent.

## Job 5 — `source-hash`

`python tools/source_hash.py --check`. Recomputes SHA-256 over every file in `fixtures/corpus/` and
(from Stage 2) `contracts/` and `build/`, comparing against `MANIFEST.sha256`.

**Why this exists.** The corpus is served to validators as commit-pinned evidence. If a corpus file
changes without the manifest and the pinned URLs changing with it, the fixture expectations silently
stop describing what validators actually read. Regenerate deliberately with `--write`.

## Job 6 — `evidence-urls`

`python tools/check_evidence_urls.py`. Fetches **every pinned source URL** and compares the served
bytes to the local corpus, byte for byte. Sources a fixture declares `UNAVAILABLE` are asserted to
**404** — a dead source that came back to life would change those cases' derivations.

This catches a rewritten history, a force-pushed branch, a deleted commit, or a corpus file edited
without re-pinning. A commit-pinned URL is only worth pinning if it still serves what it promised.

## Job 7 — `lint-contract` *(active from Stage 2)*

```
PYTHONUTF8=1 genvm-lint check    contracts/source_consensus.py
PYTHONUTF8=1 genvm-lint validate contracts/source_consensus.py
```

`genvm-linter==0.11.0`, pinned. `PYTHONUTF8=1` is required because the linter's human-readable
output emits U+2713, which raises `UnicodeEncodeError` under a non-UTF-8 default stdout encoding.
`validate` resolves and type-checks against the exact pinned runner hash, so this job also proves
the runner pin is real and current.

Guarded on `stage-guard`'s `has_contract` output, so a skip here can only mean "no contract exists",
never "a contract exists but was not linted".

## Job 8 — `direct-tests` *(active from Stage 3)*

**Why the runner is seeded explicitly.** `genlayer-test` 0.29.2 resolves its runner tarball from the
**latest** release of `genlayerlabs/genvm` and expects an asset named `genvm-universal.tar.xz`.
Newer releases no longer publish it — v0.3.0-rc7 ships platform-specific tarballs only, and the
universal bundle moved to the separate `genvm-manager` repository, whose builds carry a *newer
runner generation* than this contract pins. Left alone the download 404s inside
`download_artifacts`, and **every** direct-mode test fails with `HTTPError: 404` — a failure that
looks like a contract defect and is not.

`tools/fetch_runner.py` pins the release and **refuses to install a tarball that does not contain
the runner the contract header declares**, so the failure mode is a loud error rather than a silent
test run against the wrong runtime. The ~217 MB download is cached by `actions/cache@v4`, keyed on
the release and runner hash.

One detail worth recording, because it cost a debugging cycle: the archive shards runners by the
first two characters of the hash (`runners/py-genlayer/1j/b45aa8….tar`), so checking for the whole
51-character hash as a substring never matches. The first version of the verifier did that and
rejected a tarball that was perfectly correct.

`genlayer-test==0.29.2` direct mode — in-process, no simulator, no Docker, no network, no LLM calls
(web and prompt responses are mocked), no wallet, no GEN. Gated on `stage-guard`'s `has_tests`
output rather than on `hashFiles`, so a skip can only ever mean "no tests exist", which
`stage-guard` independently forbids once a contract is present.

## Job 9 — `mutation-tests` *(active from Stage 2)*

Breaks each load-bearing behaviour in turn and re-runs the suite: the four derivation precedence
rules, the tie-break, normalisation rejection, index-set construction, prompt fences, complete
source-payload comparator, leader self-derivation, and post-consensus storage boundary. A mutation
that survives means no test would notice that behaviour breaking, and fails
the build.

**Detection criterion.** A mutation counts as caught only when *named tests fail*, never when the
process merely exits non-zero. A collection error, a usage error, or an un-importable contract means
the suite did not test the mutation — not that it detected it.

The final `git diff --exit-code -- contracts/` guards against the tool leaving a mutated contract
behind if it were ever interrupted past its restore.

## Job 10 — `windows-parity`

Runs fixture validation, the reproducibility manifest and the line-ending check on
**`windows-latest`**.

**Why a second platform.** An integrator computes `configuration_hash` off-chain and asserts it
on-chain. That only works if the canonical serialisation produces identical bytes everywhere, and
asserting it on one platform proves nothing about the other. Direct-mode tests stay Linux-only
because the GenVM runner tarball is Linux-only; what runs on Windows is exactly the byte-level layer
whose portability is being claimed.

---

## Job graph

```
stage-guard ──┬── line-endings
              ├── secret-scan
              ├── fixtures
              ├── source-hash
              ├── evidence-urls
              ├── lint-contract      (Stage 2+)
              ├── direct-tests       (Stage 3+)
              ├── mutation-tests     (Stage 2+)
              └── windows-parity     (windows-latest)
```

`stage-guard` runs first and everything else `needs:` it, so a repository in an incoherent stage
state fails immediately rather than producing a partially-green matrix.

## Pinned versions

| Tool | Pin | Where |
| --- | --- | --- |
| Python | 3.12 | `.python-version`, `setup-python` |
| `genlayer-test` | 0.29.2 | `requirements-dev.txt` |
| `genvm-linter` | 0.11.0 | `requirements-dev.txt` |
| `pytest` | 8.3.4 | `requirements-dev.txt` |
| `jsonschema` | 4.23.0 | `requirements-dev.txt`, CI |
| `eth-hash[pycryptodome]` | 0.7.1 | CI (used by `tools/canonical.py`) |
| GenVM runner | `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6` | contract header (Stage 2) |
| `gitleaks` | 8.30.1 | workflow (`GITLEAKS_VERSION`) |
| `actions/checkout` | v4 | workflow |
| `actions/setup-python` | v5 | workflow |
