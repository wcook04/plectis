#!/usr/bin/env python3
"""Check that this repository's paper corpus still matches its manuscripts.

Generated file. This script is copied verbatim into each public repository by
``export_paper_corpus.py`` in the private system repository; edit it there.

The corpus under ``docs/papers/`` is exported by a tool that needs pandoc and a
checkout of both public repositories. Neither is available here, so this check
does not regenerate anything. It verifies the one thing that can be verified
locally and cheaply: every manuscript recorded in ``corpus.json`` still hashes to
the value the corpus was built from.

That catches the failure that actually happens -- someone edits a paper and the
generated text silently keeps describing the old one -- using nothing but the
standard library, so it can run in any CI job.

Exit status is 0 when the corpus is current, 1 when a manuscript has moved on,
and 2 when the corpus is missing or unreadable.

    python3 docs/papers/check_paper_corpus.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

CORPUS_REL = "docs/papers/corpus.json"


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    corpus_path = repo_root / CORPUS_REL
    try:
        corpus = json.loads(corpus_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read {CORPUS_REL}: {exc}", file=sys.stderr)
        return 2

    stale: list[str] = []
    missing: list[str] = []
    checked = 0

    for paper in corpus.get("papers", []):
        source_rel = paper.get("local_source")
        expected = paper.get("source_sha256")
        if not source_rel or not expected:
            continue
        source_path = repo_root / source_rel
        try:
            actual = "sha256:" + hashlib.sha256(source_path.read_bytes()).hexdigest()
        except OSError:
            missing.append(source_rel)
            continue
        checked += 1
        if actual != expected:
            stale.append(
                f"{paper.get('paper_id')}: {source_rel}\n"
                f"    corpus was built from {expected}\n"
                f"    the file now hashes to {actual}"
            )

    if missing:
        for rel in missing:
            print(f"missing manuscript: {rel}", file=sys.stderr)
        return 2

    if stale:
        print("The paper corpus is out of date.\n", file=sys.stderr)
        for row in stale:
            print(f"  {row}", file=sys.stderr)
        print(
            "\nThe generated text under docs/papers/ no longer describes these "
            "manuscripts.\nRe-export it from the private system repository:\n"
            "    ./repo-python tools/meta/dissemination/export_paper_corpus.py --write",
            file=sys.stderr,
        )
        return 1

    print(f"paper corpus current: {checked} manuscripts match their recorded hashes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
