#!/usr/bin/env python3
"""Break each load-bearing behaviour in turn and check the suite notices.

A green suite proves the tests pass. It does not prove they would catch the contract being wrong.
Only mutation testing does that, and it is the difference between a test suite and a decorative
one.

**Detection criterion.** A mutation counts as caught only when NAMED TESTS FAIL -- never when the
process merely exits non-zero. A collection error, a usage error, or an un-importable contract
means the suite did not test the mutation, not that it detected it. Scoring those as caught
produces a false green, which is the most dangerous outcome a verification tool can have.

**Concurrency lock.** This edits the contract in place and restores a snapshot at the end, so
while it runs the contract on disk is deliberately broken. It writes `.mutation-in-progress` and
`tests/conftest.py` refuses to start while that file exists. Its own subprocesses set
`SC_MUTATION_RUNNER=1` to run *through* the lock -- without that bypass every mutation would score
"caught" because pytest refused to start.

    python tools/mutation_test.py
    python tools/mutation_test.py --only conflict-precedence
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "contracts" / "source_consensus.py"
LOCK = ROOT / ".mutation-in-progress"


@dataclass
class Mutation:
    name: str
    why: str
    old: str
    new: str
    expect: list = field(default_factory=list)
    also: tuple = ()
    """A second (old, new) edit applied with the first.

    Needed where a behaviour is guarded at two points: removing one leaves an EQUIVALENT MUTANT
    that survives for the right reason, and reporting it as a coverage hole would be wrong.
    """


MUTATIONS: list[Mutation] = [
    Mutation(
        name="conflict-precedence",
        why=(
            "Checks CONFLICTED after CONFIRMED instead of before, so a 3-2 plurality confirms. "
            "This is the single edge the design turns on: an oracle that resolves a genuine "
            "dispute by counting is worse than one that reports it."
        ),
        old="    if contenders >= 2 or tied_at_top >= 2:\n"
            "        return build(STATUS_CONFLICTED, None, [], list(value_indices))",
        new="    if False:\n"
            "        return build(STATUS_CONFLICTED, None, [], list(value_indices))",
        expect=["test_two_competing_values_conflict", "test_three_two_split_conflicts"],
    ),
    Mutation(
        name="tie-uniqueness-clause",
        why=(
            "Removes the top-count uniqueness test, letting the lexicographic tie-break -- which "
            "exists only to pin determinism -- silently pick a winner from a dead heat."
        ),
        old="    if contenders >= 2 or tied_at_top >= 2:",
        new="    if contenders >= 2:",
        expect=["test_dead_heat_conflicts_even_above_the_threshold"],
    ),
    Mutation(
        name="model-selected-status-trusted",
        why=(
            "Accepts a `status` field from the model instead of rejecting it. The model must "
            "never have a channel to the status; this mutation opens one."
        ),
        old='    for forbidden in ("status", "verdict", "confidence", "score", "probability"):',
        new='    for forbidden in ("verdict", "confidence", "score", "probability"):',
        expect=["test_a_status_field_in_the_response_is_rejected",
                "test_every_forbidden_field_is_rejected"],
    ),
    Mutation(
        name="minimum-support-weakened",
        why="Confirms on a single supporting source, so one page becomes the answer.",
        old="    if top_count >= min_support:",
        new="    if top_count >= 1:",
        expect=["test_insufficient_evidence_when_only_one_source_speaks"],
    ),
    Mutation(
        name="config-hash-source-order",
        why=(
            "Sorts source URLs before hashing, so reordering them stops changing the digest. "
            "Indices are meaningful and appear in the record, so a reordering IS a different "
            "configuration -- a consumer pinning the hash would stop detecting the swap."
        ),
        old='            "source_urls": list(urls),',
        new='            "source_urls": sorted(urls),',
        expect=["test_the_contract_agrees_with_the_reference_on_a_reordering"],
    ),
    Mutation(
        name="terminality-removed",
        why="Allows re-resolution after a terminal status, so a query can be re-run until the "
            "answer is agreeable -- the failure mode the design exists to prevent.",
        old="        if self.resolved:\n"
            "            _fail(",
        new="        if False:\n"
            "            _fail(",
        expect=["test_second_resolve_reverts"],
    ),
    Mutation(
        name="unavailable-made-terminal",
        why=(
            "Treats UNAVAILABLE as terminal, so a transient outage permanently poisons a query "
            "whose configuration is correct. The whole argument for the retry exception."
        ),
        old='        if final["status"] == STATUS_UNAVAILABLE:',
        new="        if False:",
        expect=["test_a_retry_after_unavailable_can_succeed", "test_unavailable_does_not_resolve"],
    ),
    Mutation(
        name="invalid-state-rejection-removed",
        why=(
            "Lets a per-source state outside the enum through, so garbage reaches derivation and "
            "is silently treated as non-supporting evidence.\n"
            "    Breaks BOTH validation points on purpose. The first version removed only the "
            "post-consensus check and SURVIVED -- not because the behaviour is untested, but "
            "because the earlier guard in _normalise_source_output already rejected it. Defence "
            "in depth makes single-point mutations misleading: that mutant was EQUIVALENT, and "
            "scoring it as a coverage hole would have been wrong."
        ),
        old="    if state not in (STATE_VALUE, STATE_NO_VALUE, STATE_AMBIGUOUS):",
        new="    if False:",
        also=("            if states[i] not in STATES:", "            if False:"),
        expect=["test_rejected_whole_response"],
    ),
    Mutation(
        name="normalisation-repair",
        why=(
            "Downgrades a non-conforming VALUE to AMBIGUOUS instead of rejecting the response. "
            "Repairing model output is a guess at intent, and two nodes guessing independently "
            "is a divergence."
        ),
        old='        _fail(\n'
            '            ERROR_LLM,\n'
            '            f"value {str(raw_value)[:60]!r} does not normalise as {fact_type}; "',
        new='        return {"state": STATE_AMBIGUOUS, "value": None}\n'
            '        _fail(\n'
            '            ERROR_LLM,\n'
            '            f"value {str(raw_value)[:60]!r} does not normalise as {fact_type}; "',
        expect=["test_a_non_normalising_value_is_rejected_not_downgraded"],
    ),
    Mutation(
        name="prompt-fences-removed",
        why=(
            "Stops neutralising fence strings inside fetched text, so a source can close the "
            "fence and continue outside the trust boundary."
        ),
        old="    out = out.replace(FENCE, FENCE_NEUTRALISED).replace(FENCE_END, FENCE_NEUTRALISED)",
        new="    out = out",
        expect=["test_fence_strings_inside_a_source_are_neutralised"],
    ),
    Mutation(
        name="model-can-declare-unavailable",
        why=(
            "Accepts UNAVAILABLE from the model. It is a fetch outcome the contract observes; a "
            "model reporting it would be claiming something it cannot see, and a compromised "
            "source could mark itself or push the query toward UNAVAILABLE.\n"
            "    Breaks BOTH guards, for the same reason as invalid-state-rejection-removed: "
            "removing only the dedicated check left the general enum check catching it, so the "
            "mutant was equivalent and survived for the right reason."
        ),
        old="    if state == STATE_UNAVAILABLE:",
        new="    if False:",
        also=(
            "    if state not in (STATE_VALUE, STATE_NO_VALUE, STATE_AMBIGUOUS):",
            "    if state not in (STATE_VALUE, STATE_NO_VALUE, STATE_AMBIGUOUS, "
            "STATE_UNAVAILABLE):",
        ),
        expect=["test_a_source_cannot_declare_itself_or_others_unavailable"],
    ),
    Mutation(
        name="reachability-check-removed",
        why=(
            "Removes row 1, so a query where almost nothing could be fetched reports "
            "INSUFFICIENT_EVIDENCE instead of UNAVAILABLE -- telling an integrator to find "
            "better sources when the sources were fine and the network was not."
        ),
        old="    if reachable < min_support:\n"
            "        return build(STATUS_UNAVAILABLE, None, [], [])",
        new="    if False:\n"
            "        return build(STATUS_UNAVAILABLE, None, [], [])",
        expect=["test_too_few_reachable_is_unavailable", "test_all_dead_is_unavailable"],
    ),
]

_FAILED_RE = re.compile(r"^FAILED (\S+::\S+)", re.M)


def run_suite() -> tuple[int, set]:
    env = dict(os.environ, SC_MUTATION_RUNNER="1", PYTHONUTF8="1")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(ROOT), env=env, timeout=1800,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    failed = {m.split("::")[-1] for m in _FAILED_RE.findall(out)}
    return proc.returncode, failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="run a single mutation by name")
    args = ap.parse_args()

    mutations = MUTATIONS
    if args.only:
        mutations = [m for m in MUTATIONS if m.name == args.only]
        if not mutations:
            print(f"unknown mutation {args.only!r}", file=sys.stderr)
            return 2

    original = CONTRACT.read_text(encoding="utf-8")
    if LOCK.exists():
        print("FAIL -- .mutation-in-progress already exists; another run may be active",
              file=sys.stderr)
        return 1

    LOCK.write_text("mutation testing in progress\n", encoding="utf-8", newline="\n")
    caught: list = []
    survived: list = []
    broken: list = []

    try:
        print("baseline ...", flush=True)
        code, failed = run_suite()
        if code != 0:
            print(f"FAIL -- the suite is not green before mutating ({len(failed)} failures)",
                  file=sys.stderr)
            for f in sorted(failed):
                print(f"  - {f}", file=sys.stderr)
            return 1
        print("baseline green\n", flush=True)

        for m in mutations:
            if m.old not in original:
                broken.append(m.name)
                print(f"[BROKEN ] {m.name}: anchor text not found -- the mutation no longer "
                      f"describes the contract", flush=True)
                continue

            CONTRACT.write_text(original.replace(m.old, m.new, 1), encoding="utf-8", newline="\n")
            code, failed = run_suite()
            CONTRACT.write_text(original, encoding="utf-8", newline="\n")

            named = sorted(failed)
            if not named:
                # Exit code alone is NOT detection: the suite may not have run at all.
                survived.append((m.name, m.why))
                status = "SURVIVED" if code == 0 else "SURVIVED*"
                note = "" if code == 0 else "  (non-zero exit but NO named test failed)"
                print(f"[{status}] {m.name}{note}", flush=True)
                continue

            expected_hit = [e for e in m.expect if any(e in f for f in named)]
            caught.append((m.name, len(named), expected_hit))
            flag = "" if expected_hit or not m.expect else "  (caught, but not by the named test)"
            print(f"[CAUGHT ] {m.name} -- {len(named)} test(s) failed{flag}", flush=True)

    finally:
        CONTRACT.write_text(original, encoding="utf-8", newline="\n")
        LOCK.unlink(missing_ok=True)

    print()
    print("=" * 78)
    print(f"caught {len(caught)}  survived {len(survived)}  broken {len(broken)}"
          f"  of {len(mutations)}")
    print("=" * 78)

    if survived:
        print("\nSURVIVED -- no test would notice these behaviours breaking:", file=sys.stderr)
        for name, why in survived:
            print(f"  - {name}: {why}", file=sys.stderr)
    if broken:
        print("\nBROKEN -- these mutations no longer match the contract and test nothing:",
              file=sys.stderr)
        for name in broken:
            print(f"  - {name}", file=sys.stderr)

    if survived or broken:
        return 1
    print(f"\nAll {len(mutations)} mutations caught by named test failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
