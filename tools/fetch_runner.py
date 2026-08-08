#!/usr/bin/env python3
"""Seed the direct-mode runner cache with the PINNED GenVM release.

## Why this exists

`genlayer-test` 0.29.2 resolves its runner tarball from whatever is currently the **latest**
release of `genlayerlabs/genvm`, and downloads `genvm-universal.tar.xz` from it. Two things go
wrong with that in CI:

1. **Newer releases do not publish that asset.** v0.3.0-rc7 ships platform-specific tarballs only;
   the universal bundle moved to the separate `genvm-manager` repository. The download 404s and
   every direct-mode test fails with `HTTPError: 404` from `download_artifacts`, which looks like
   a contract failure and is not.
2. **"Latest" is not a pin.** Even when it resolves, it tracks a moving target, and
   `genvm-manager`'s universal bundles carry a *newer runner generation* than this contract pins
   -- verified: `genvm-manager` v0.6.0-rc2 contains neither `1jb45aa8…` nor std `11rhn002…`.

So the version is pinned here, and the download is verified rather than trusted: the tarball is
only installed if the runner this contract actually declares is inside it. The failure mode is a
loud error, not a silent test run against the wrong runtime.

The ~217 MB download is cached by `actions/cache` in CI, keyed on the release and runner hash.

    python tools/fetch_runner.py            # seed the cache
    python tools/fetch_runner.py --verify   # confirm the pinned runner is present
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

# Pinned deliberately. Bumping this is a decision, not a side effect of a new upstream release.
GENVM_RELEASE = "v0.2.16"
ASSET = "genvm-universal.tar.xz"
URL = f"https://github.com/genlayerlabs/genvm/releases/download/{GENVM_RELEASE}/{ASSET}"

CACHE = Path.home() / ".cache" / "gltest-direct"
TARBALL = CACHE / f"genvm-universal-{GENVM_RELEASE}.tar.xz"

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "contracts" / "source_consensus.py"

# The std-lib generation the pinned runner resolves to. Recorded so `--verify` checks both halves
# of the pair rather than only the runner the header names.
EXPECTED_STD = "11rhn002yfajawsz7fai6mykznbxkxs6l91iskj5cm82c92qhy3v"


def pinned_runner() -> str:
    """Read the runner hash out of the contract header -- the single source of truth."""
    first = CONTRACT.read_text(encoding="utf-8").splitlines()[0]
    m = re.search(r'"Depends":\s*"py-genlayer:([0-9a-z]+)"', first)
    if not m:
        raise SystemExit(f"FAIL: no py-genlayer runner pin in {CONTRACT.name} line 1")
    return m.group(1)


def member_path(runner_type: str, digest: str) -> str:
    """Where a runner lives inside the bundle.

    The archive shards by the first two characters of the hash:

        runners/py-genlayer/1j/b45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6.tar

    Searching for the whole 51-character hash as a substring therefore never matches -- a `/`
    sits in the middle of it. The first version of this file did exactly that and rejected a
    tarball that was perfectly correct.
    """
    return f"runners/{runner_type}/{digest[:2]}/{digest[2:]}.tar"


def members_contain(path: Path, wanted: dict) -> dict:
    """`wanted` maps runner_type -> hash. Returns which were found."""
    targets = {member_path(t, h): (t, h) for t, h in wanted.items()}
    found = {t: False for t in wanted}
    with tarfile.open(path, "r:xz") as tf:
        for name in tf.getnames():
            hit = targets.get(name)
            if hit:
                found[hit[0]] = True
            if all(found.values()):
                break
    return found


def download() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    print(f"downloading {URL}")
    with tempfile.NamedTemporaryFile(delete=False, dir=CACHE, suffix=".part") as tmp:
        tmp_path = Path(tmp.name)
        with urllib.request.urlopen(URL, timeout=900) as r:
            shutil.copyfileobj(r, tmp)
    size = tmp_path.stat().st_size
    print(f"downloaded {size:,} bytes")

    runner = pinned_runner()
    found = members_contain(tmp_path, {"py-genlayer": runner,
                                       "py-lib-genlayer-std": EXPECTED_STD})
    missing = [k for k, v in found.items() if not v]
    if missing:
        tmp_path.unlink(missing_ok=True)
        raise SystemExit(
            "FAIL: the downloaded tarball does not contain the pinned runner.\n"
            f"      missing: {missing}\n"
            f"      release: {GENVM_RELEASE}\n"
            "      Refusing to install it -- running the suite against a different runtime would\n"
            "      produce results that do not describe the deployed contract."
        )

    tmp_path.replace(TARBALL)
    print(f"installed {TARBALL}")
    print(f"  contains runner {runner}")
    print(f"  contains std    {EXPECTED_STD}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true",
                    help="check the cached tarball carries the pinned runner; download nothing")
    args = ap.parse_args()

    runner = pinned_runner()

    if args.verify:
        if not TARBALL.exists():
            print(f"FAIL: {TARBALL} is missing; run without --verify first", file=sys.stderr)
            return 1
        found = members_contain(TARBALL, {"py-genlayer": runner,
                                          "py-lib-genlayer-std": EXPECTED_STD})
        missing = [k for k, v in found.items() if not v]
        if missing:
            print(f"FAIL: cached tarball is missing {missing}", file=sys.stderr)
            return 1
        print(f"OK -- cached runner cache carries {runner} and std {EXPECTED_STD}")
        return 0

    if TARBALL.exists():
        found = members_contain(TARBALL, {"py-genlayer": runner,
                                          "py-lib-genlayer-std": EXPECTED_STD})
        if all(found.values()):
            print(f"already cached: {TARBALL}")
            return 0
        print("cached tarball does not carry the pinned runner; re-downloading")
        TARBALL.unlink()

    download()
    return 0


if __name__ == "__main__":
    sys.exit(main())
