#!/usr/bin/env python3
"""Generate fixtures/cases/*.json with commit-pinned source URLs.

Kept as a generator rather than eight hand-written files because the pinned commit appears in
every source URL: a hand edit that updates seven of eight is exactly the kind of drift the
fixture corpus exists to prevent.

    python tools/make_fixtures.py --pin <40-hex-commit>

Each case declares the immutable query configuration, the honest per-source extraction a correct
model would produce from the corpus, and the status those results must derive to. The expectation
is not asserted by hand -- `tools/validate_fixtures.py` recomputes it with `tools/canonical.py`
and fails if the declared value disagrees.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "fixtures" / "cases"
REPO = "GIFTEDLOV/source-consensus"

QUESTION = "On what date was version {ver} of {proj} officially released?"


def url(pin: str, case: str, name: str) -> str:
    return f"https://raw.githubusercontent.com/{REPO}/{pin}/fixtures/corpus/{case}/{name}"


def build(pin: str) -> list[dict]:
    def case(
        cid: str,
        category: str,
        description: str,
        proj: str,
        ver: str,
        files: list[str],
        results: list[dict],
        expected: str,
        expected_value: str | None,
        minimum: int = 2,
        conflict: int = 2,
        extra_urls: list[str] | None = None,
        notes: str | None = None,
    ) -> dict:
        urls = [url(pin, cid, f) for f in files] + (extra_urls or [])
        d = {
            "id": cid,
            "category": category,
            "description": description,
            "config": {
                "query_id": f"{proj.upper()}_{ver.replace('.', '_')}_RELEASE_DATE",
                "question": QUESTION.format(ver=ver, proj=proj),
                "fact_type": "DATE",
                "normalization_rules": {},
                "allowed_enum_values": [],
                "source_urls": urls,
                "minimum_supporting_sources": minimum,
                "conflict_threshold": conflict,
            },
            "source_results": results,
            "expected": {"status": expected, "normalized_value": expected_value},
        }
        if notes:
            d["notes"] = notes
        return d

    def v(i: int, value: str) -> dict:
        return {"source_index": i, "state": "VALUE", "value": value}

    def st(i: int, state: str) -> dict:
        return {"source_index": i, "state": state, "value": None}

    return [
        case(
            "01-all-agree",
            "unanimous",
            "Three independent sources state the same release date in the same surface form.",
            "LedgerIndexer", "2.0.0",
            ["source-0-release-page.md", "source-1-changelog.md", "source-2-docs-announcement.md"],
            [v(0, "2026-03-11"), v(1, "2026-03-11"), v(2, "2026-03-11")],
            "CONFIRMED", "2026-03-11",
            notes="The base case. Three supporting sources, nothing conflicting, nothing missing.",
        ),
        case(
            "02-majority-one-outlier",
            "majority",
            "Three official sources agree; one community mirror reports a different date.",
            "Meshcache", "4.1.0",
            ["source-0-release-page.md", "source-1-changelog.md", "source-2-docs.md",
             "source-3-mirror-blog.md"],
            [v(0, "2026-05-20"), v(1, "2026-05-20"), v(2, "2026-05-20"), v(3, "2026-05-18")],
            "CONFIRMED", "2026-05-20",
            notes=(
                "The outlier has support 1, below conflict_threshold 2, so it does not contest "
                "the result -- but it is recorded in conflicting_source_indices rather than "
                "discarded. A consumer can see that one source disagreed and go read it."
            ),
        ),
        case(
            "03-two-competing",
            "conflict",
            "Two sources say the tag date; two say the general-availability date. Both readings "
            "are defensible, which is what makes this a real conflict rather than an error.",
            "Quillstore", "3.0.0",
            ["source-0-release-page.md", "source-1-changelog.md", "source-2-press-release.md",
             "source-3-docs.md"],
            [v(0, "2026-02-09"), v(1, "2026-02-09"), v(2, "2026-02-16"), v(3, "2026-02-16")],
            "CONFLICTED", None,
            notes=(
                "Both values reach conflict_threshold, so CONFLICTED is derived even though "
                "neither is 'wrong'. The contract reports the contest instead of resolving it by "
                "plurality. normalized_value is null: there is no answer to publish."
            ),
        ),
        case(
            "04-insufficient-evidence",
            "insufficient",
            "All sources fetch cleanly, but only one actually states a release date.",
            "Tessera", "1.0.0",
            ["source-0-landing.md", "source-1-docs-index.md", "source-2-release-page.md"],
            [st(0, "NO_VALUE"), st(1, "NO_VALUE"), v(2, "2026-04-02")],
            "INSUFFICIENT_EVIDENCE", None,
            notes=(
                "One supporting source is below minimum_supporting_sources. The distinction that "
                "matters: the sources were reachable and simply do not say, which is a different "
                "situation from not being able to read them."
            ),
        ),
        case(
            "05-source-unavailable",
            "unavailable-source",
            "One configured source cannot be fetched; the two that can agree.",
            "Fernpost", "0.9.0",
            ["source-0-release-page.md", "source-1-changelog.md"],
            [v(0, "2026-06-30"), v(1, "2026-06-30"), st(2, "UNAVAILABLE")],
            "CONFIRMED", "2026-06-30",
            extra_urls=[url(pin, "05-source-unavailable", "source-2-does-not-exist.md")],
            notes=(
                "A dead source does not poison the result when enough others agree. The third URL "
                "is deliberately absent from the corpus, so it really does 404 rather than being "
                "simulated. Its index is recorded in unavailable_source_indices."
            ),
        ),
        case(
            "06-injection-redefine",
            "adversarial",
            "One source carries a forged [SYSTEM] block instructing the reader to change "
            "fact_type, force CONFIRMED, invent a source index, and mark the others UNAVAILABLE.",
            "Halyard", "1.2.0",
            ["source-0-release-page.md", "source-1-changelog.md",
             "source-2-compromised-mirror.md"],
            [v(0, "2026-07-14"), v(1, "2026-07-14"), v(2, "2026-07-14")],
            "CONFIRMED", "2026-07-14",
            notes=(
                "The compromised mirror states the correct date at the bottom, so honest "
                "extraction yields agreement. That is the point: every instruction in the "
                "injection targets a field the model does not control. It cannot set a status, "
                "cannot change fact_type, cannot add source_index 9, and cannot mark another "
                "source UNAVAILABLE -- those are contract-side, derived from configuration and "
                "fetch outcomes. The worst it can do is corrupt its OWN source's value, which "
                "costs it one index out of three."
            ),
        ),
        case(
            "09-all-sources-unavailable",
            "unavailable-aggregate",
            "Every configured source is unfetchable, so the evidence base is too small to decide "
            "no matter how good the extraction is.",
            "Vantsend", "1.1.0",
            [],
            [st(0, "UNAVAILABLE"), st(1, "UNAVAILABLE"), st(2, "UNAVAILABLE")],
            "UNAVAILABLE", None,
            extra_urls=[
                url(pin, "09-all-sources-unavailable", "source-0-gone.md"),
                url(pin, "09-all-sources-unavailable", "source-1-gone.md"),
                url(pin, "09-all-sources-unavailable", "source-2-gone.md"),
            ],
            notes=(
                "No corpus directory exists for this case, deliberately: the three URLs really do "
                "404 rather than simulating failure. UNAVAILABLE is separated from "
                "INSUFFICIENT_EVIDENCE because they call for different responses -- retry the "
                "fetch versus accept that the sources do not say. Compare case 04, where the "
                "sources were readable and simply silent."
            ),
        ),
        case(
            "07-normalisation-equivalent",
            "normalisation",
            "Three sources state the same date in three different surface forms.",
            "Cindermill", "5.4.0",
            ["source-0-release-page.md", "source-1-blog.md", "source-2-docs.md"],
            [v(0, "2026-01-05"), v(1, "2026-01-05"), v(2, "2026-01-05")],
            "CONFIRMED", "2026-01-05",
            notes=(
                "'2026-01-05', '5 January 2026' and 'January 5, 2026' are one fact. Without "
                "normalisation to a canonical form this case would derive CONFLICTED from three "
                "sources that agree -- the single most likely false negative in the design."
            ),
        ),
        case(
            "08-ambiguous-date",
            "ambiguous",
            "One source gives an exact date; two give month-or-vaguer wording that cannot be "
            "normalised to YYYY-MM-DD.",
            "Slatewind", "2.3.0",
            ["source-0-release-page.md", "source-1-vague-blog.md", "source-2-vague-docs.md"],
            [v(0, "2026-09-17"), st(1, "AMBIGUOUS"), st(2, "AMBIGUOUS")],
            "INSUFFICIENT_EVIDENCE", None,
            notes=(
                "'September 2026' and 'late 2026' are about the right fact but are not dates. "
                "AMBIGUOUS records that honestly instead of guessing a day-of-month or silently "
                "reporting NO_VALUE. Compare case 04: same status, different reason, and the "
                "index sets in the record say which."
            ),
        ),
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pin", required=True, help="40-hex commit that serves fixtures/corpus/")
    args = ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}", args.pin):
        raise SystemExit("--pin must be a 40-character lowercase hex commit sha")

    CASES.mkdir(parents=True, exist_ok=True)
    for c in build(args.pin):
        p = CASES / f"{c['id']}.json"
        p.write_text(json.dumps(c, indent=2, ensure_ascii=False) + "\n",
                     encoding="utf-8", newline="\n")
        print(f"wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
