"""
[PURPOSE]
- Teleology: Provide canonical regular expressions and utility functions for extracting and normalizing
  contract specifications across the system, preventing discovery drift as new contracts are added.
- Mechanism: Centralizes the grammar for three recognized contract reference formats:
  `codex/contracts/foo.md` (path), `[CONTRACT: foo.md]` (tag), and `See Contract: codex/contracts/foo.md`
  (prose reference). All three formats are recognized by both extraction and normalization functions.

[INTERFACE]
- Reads: Arbitrary text strings and contract token strings.
- Writes: No direct I/O; pure string processing.
- Fails: Never raises; returns None or empty collections on non-matching input.

[FLOW]
- Three regexes cover the three recognized formats.
- canonical_contract_name: resolve any single token (any format) to a bare filename.
- extract_contract_fnames: scan text for all contract references and return sorted unique filenames.
- normalize_contracts: accept string or list input and return sorted canonical name list.

[DEPENDENCIES]
- Python stdlib: re, pathlib, typing.

[CONSTRAINTS]
- Both .md and .json extensions are recognized.
- Functions must remain side-effect free.
- When-needed: Open when a caller needs the canonical parser for mixed contract-reference formats before indexing or validating contract mentions.
- Escalates-to: system/lib/codex_paths.py::normalize_read_path; codex/CODEX.md
- Navigation-group: kernel_lib
"""

import re
from pathlib import Path
from typing import List, Optional, Any, Set

# Shared pattern for allowed contract filenames
FILENAME_PATTERN = r"[A-Za-z0-9_.\-]+\.(?:md|json)"

CONTRACT_PATH_RE = re.compile(rf"codex/contracts/({FILENAME_PATTERN})\b")
CONTRACT_TAG_RE = re.compile(rf"\[CONTRACT:\s*({FILENAME_PATTERN})\s*\]")
CONTRACT_NAME_RE = re.compile(rf"^{FILENAME_PATTERN}$")
CONTRACT_REF_RE = re.compile(rf"See Contract:\s*codex/contracts/({FILENAME_PATTERN})")


def canonical_contract_name(token: str) -> Optional[str]:
    """
    [ACTION]
    - Teleology: Collapse one contract reference token into the canonical bare filename representation used across registry and validation flows.
    - Mechanism: Test the token against the tag, prose-reference, path, and bare-name patterns in that order and return the captured filename on the first match.
    - Guarantee: Returns a bare contract filename for recognized formats and None for blank or unrecognized input.
    - Fails: None.
    - When-needed: Open when a caller has one contract token in unknown format and needs the canonical filename before storing or comparing it.
    - Escalates-to: system/lib/codex_paths.py::normalize_read_path; codex/CODEX.md
    """
    raw = (token or "").strip()
    if not raw:
        return None

    # Try specific formats first
    for regex in [CONTRACT_TAG_RE, CONTRACT_REF_RE, CONTRACT_PATH_RE]:
        match = regex.search(raw)
        if match:
            return match.group(1)

    # Finally try bare name
    if CONTRACT_NAME_RE.fullmatch(raw):
        return raw
    return None


def extract_contract_fnames(text: str) -> List[str]:
    """
    [ACTION]
    - Teleology: Recover every contract filename mentioned in a freeform text surface without forcing callers to run multiple regex passes themselves.
    - Mechanism: Scan the text with the shared path and tag regexes, collect matching filenames into a set, and return them in sorted order.
    - Guarantee: Returns a sorted list of unique contract filenames or [] for empty input.
    - Fails: None.
    - When-needed: Open when indexing or validating documentation text that may mention contracts in mixed path, tag, or prose forms.
    - Escalates-to: system/lib/codex_paths.py::normalize_read_path; codex/CODEX.md
    """
    if not text:
        return []

    found: Set[str] = set()
    # CONTRACT_PATH_RE is the most general and will find refs inside tags/prose too
    # We use findall to get all occurrences in one pass
    for match in CONTRACT_PATH_RE.findall(text):
        found.add(match)

    # Tags might use just the filename [CONTRACT: foo.md]
    for match in CONTRACT_TAG_RE.findall(text):
        found.add(match)

    return sorted(found)


def normalize_contracts(value: Any) -> List[str]:
    """
    [ACTION]
    - Teleology: Normalize caller-supplied contract references into one deduplicated filename list regardless of whether the input arrived as a scalar or list.
    - Mechanism: Accept either a string or a list of strings, reuse canonical_contract_name() for each string candidate, and return the unique filenames in sorted order.
    - Guarantee: Returns a sorted list of canonical bare filenames and silently skips non-string list items or unrecognized inputs.
    - Fails: None.
    - When-needed: Open when a config or artifact field may contain one or many contract references and the caller needs the canonical normalized list form.
    - Escalates-to: system/lib/codex_paths.py::normalize_read_path; codex/CODEX.md
    """
    if isinstance(value, str):
        canonical = canonical_contract_name(value)
        return [canonical] if canonical else []

    if isinstance(value, list):
        found: Set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            canonical = canonical_contract_name(item)
            if canonical:
                found.add(canonical)
        return sorted(found)

    return []
