#!/usr/bin/env python3
"""Prompt-shelf fingerprints — match-substrate for B-lane capture.

Reads the ``## Prompt`` fenced body out of each current item note under
``obsidian/prompt_shelf/items/*.md`` and emits a fingerprint manifest at
``state/prompt_shelf/prompt_fingerprints.json`` that downstream observers
(operator-ChatGPT CDP, ``ask_ai`` inline hook, manual paste-pad sweep) use to
recognize a submitted user message as one of the cockpit slots.

The submitted user message *is* the tag; the operator never types metadata.
Match strategy is layered, robust to small variations (extra dashes, smart
quotes, missing fence markers, extra pasted context after the prompt):

  1. **Anchor**: a normalized substring drawn from the first ~80 chars of the
     canonical prompt body. Each cockpit slot has a unique opener sentence;
     when multiple anchors are present, the earliest raw-text position wins.
  2. **Distinctive sentence presence**: count how many of the prompt's
     sentences appear (substring, normalized) inside the submitted text. Hits
     ≥ ``DISTINCTIVE_HIT_THRESHOLD`` win.
  3. **Token Jaccard fallback**: bag-of-words Jaccard on tokens of length
     ≥ ``MIN_TOKEN_LEN``; threshold ``JACCARD_THRESHOLD``. Catches cases where
     anchor was disturbed (e.g. operator copied "starting from line 2" of the
     fence).

CLI
---
    prompt_shelf_fingerprints.py --print     # emit JSON to stdout
    prompt_shelf_fingerprints.py --write     # write canonical fingerprints
    prompt_shelf_fingerprints.py --check     # non-zero on drift vs disk
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
ITEMS_DIR = REPO_ROOT / "obsidian" / "prompt_shelf" / "items"
PROJECTION_PATH = REPO_ROOT / "state" / "prompt_shelf" / "prompt_fingerprints.json"

SCHEMA_VERSION = "1.0.0"
ANCHOR_LEN = 80
DISTINCTIVE_HIT_THRESHOLD = 3
JACCARD_THRESHOLD = 0.85
MIN_TOKEN_LEN = 4

# Map item-note slug → cockpit slot label. The cockpit_slot frontmatter on
# each item note is the authoritative source; we cross-check against this map.
SLOT_BY_SLUG = {
    "surface_exploration": "A0",
    "type_a_autonomous_continue": "A3",
    "instantiation": "B1",
    "continue_intelligently": "B2",
    "semantic_carryforward": "B2.2",
    "visual_refinement": "B2.3",
    "generalized_snippet_research": "B2.4",
    "context_compaction": "B3",
    "autonomous_seed": "B6",
    "codex_goal_author": "B7",
}


@dataclass
class PromptFingerprint:
    slot: str
    slug: str
    item_path: str
    body_sha256: str
    anchor: str
    sentences: list[str]
    distinctive_sentences: list[str]
    tokens: list[str]


def _normalize(text: str) -> str:
    """Lowercase, normalize quotes/dashes/whitespace for robust substring match."""
    text = text.lower()
    # Smart quotes → straight; em/en dashes → hyphen
    text = text.translate(str.maketrans({
        "‘": "'", "’": "'",
        "“": '"', "”": '"',
        "—": "-", "–": "-",
        "…": "...",
    }))
    # Collapse all whitespace runs to single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _index_preserving_normalize(text: str) -> str:
    """Normalize only 1:1 substitutions so match offsets stay raw-comparable."""
    text = text.lower()
    return text.translate(str.maketrans({
        "‘": "'", "’": "'",
        "“": '"', "”": '"',
        "—": "-", "–": "-",
    }))


def _anchor_position(submitted_text: str, anchor: str) -> int | None:
    """Return anchor start in raw-text coordinates, tolerating whitespace runs."""
    if not submitted_text or not anchor:
        return None
    tokens = anchor.split()
    if not tokens:
        return None
    pattern = r"\s+".join(re.escape(t) for t in tokens)
    match = re.search(pattern, _index_preserving_normalize(submitted_text))
    return match.start() if match else None


def _split_sentences(text: str) -> list[str]:
    """Split prompt body into sentences. Conservative — splits on .!? at end of clause."""
    # Drop empty leading/trailing tokens
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"\'\(\[—-])", text.strip())
    return [p.strip() for p in parts if p.strip()]


def _tokenize(text: str) -> set[str]:
    """Bag-of-tokens for Jaccard. Tokens are alphanum runs of length ≥ MIN_TOKEN_LEN."""
    return {t for t in re.findall(r"[a-z0-9]+", text) if len(t) >= MIN_TOKEN_LEN}


def _extract_prompt_body(item_path: Path) -> tuple[str, str]:
    """Return (raw_body, slug) from an item note's first fenced ``text`` block under ``## Prompt``."""
    text = item_path.read_text()
    # Locate ## Prompt header then the next fenced block
    prompt_idx = text.find("\n## Prompt")
    if prompt_idx == -1:
        raise ValueError(f"{item_path} has no ## Prompt section")
    sub = text[prompt_idx:]
    # Find first ```text or ``` fence after the header
    fence_match = re.search(r"```(?:text)?\s*\n(.*?)\n```", sub, flags=re.DOTALL)
    if not fence_match:
        raise ValueError(f"{item_path} has no fenced prompt body under ## Prompt")
    body = fence_match.group(1).strip()
    slug = item_path.stem
    return body, slug


def _distinctive_sentences(sentences_by_slot: dict[str, list[str]]) -> dict[str, list[str]]:
    """Sentences that appear in exactly one slot. Used to disambiguate near-miss matches."""
    counts: dict[str, list[str]] = {}
    for slot, sents in sentences_by_slot.items():
        for s in sents:
            counts.setdefault(s, []).append(slot)
    distinctive: dict[str, list[str]] = {slot: [] for slot in sentences_by_slot}
    for sent, owners in counts.items():
        if len(owners) == 1:
            distinctive[owners[0]].append(sent)
    return distinctive


def build_fingerprints(items_dir: Path = ITEMS_DIR) -> list[PromptFingerprint]:
    if not items_dir.is_dir():
        raise FileNotFoundError(f"items dir not found: {items_dir}")

    # First pass: extract bodies + sentences
    sentences_by_slot: dict[str, list[str]] = {}
    raw_bodies: dict[str, tuple[str, Path]] = {}  # slot → (body, path)
    for item_path in sorted(items_dir.glob("*.md")):
        slug = item_path.stem
        slot = SLOT_BY_SLUG.get(slug)
        if slot is None:
            continue  # not a cockpit-current item
        body, slug = _extract_prompt_body(item_path)
        norm_body = _normalize(body)
        sentences_by_slot[slot] = [_normalize(s) for s in _split_sentences(body)]
        raw_bodies[slot] = (body, item_path)

    distinctive = _distinctive_sentences(sentences_by_slot)

    # Second pass: emit fingerprints
    out: list[PromptFingerprint] = []
    for slot, (body, item_path) in raw_bodies.items():
        norm_body = _normalize(body)
        anchor = norm_body[:ANCHOR_LEN]
        body_sha = hashlib.sha256(norm_body.encode("utf-8")).hexdigest()
        rel_path = item_path.relative_to(REPO_ROOT).as_posix()
        out.append(PromptFingerprint(
            slot=slot,
            slug=item_path.stem,
            item_path=rel_path,
            body_sha256=body_sha,
            anchor=anchor,
            sentences=sentences_by_slot[slot],
            distinctive_sentences=distinctive[slot],
            tokens=sorted(_tokenize(norm_body)),
        ))
    out.sort(key=lambda f: f.slot)
    return out


@dataclass
class MatchResult:
    slot: str | None
    confidence: float
    method: str  # anchor | distinctive | jaccard | none
    matched_anchor: str | None = None
    matched_anchor_position: int | None = None
    matched_sentences: list[str] = field(default_factory=list)
    jaccard_score: float = 0.0


def match(submitted_text: str, fingerprints: Iterable[PromptFingerprint]) -> MatchResult:
    """Match a submitted user message against the catalog. See module docstring for strategy."""
    norm = _normalize(submitted_text)
    fps = list(fingerprints)

    # 1. Anchor pass — earliest raw-text hit wins.
    anchor_hits: list[tuple[int, str, PromptFingerprint]] = []
    for fp in fps:
        position = _anchor_position(submitted_text, fp.anchor)
        if position is not None:
            anchor_hits.append((position, fp.slot, fp))
    if anchor_hits:
        position, _, fp = min(anchor_hits, key=lambda item: (item[0], item[1]))
        return MatchResult(
            slot=fp.slot, confidence=1.0, method="anchor",
            matched_anchor=fp.anchor, matched_anchor_position=position,
        )

    # 2. Distinctive-sentence pass
    best_distinctive = MatchResult(slot=None, confidence=0.0, method="none")
    for fp in fps:
        if not fp.distinctive_sentences:
            continue
        hits = [s for s in fp.distinctive_sentences if s and s in norm]
        if len(hits) >= DISTINCTIVE_HIT_THRESHOLD:
            score = len(hits) / max(1, len(fp.distinctive_sentences))
            if score > best_distinctive.confidence:
                best_distinctive = MatchResult(
                    slot=fp.slot, confidence=score, method="distinctive",
                    matched_sentences=hits[:5],
                )
    if best_distinctive.slot:
        return best_distinctive

    # 3. Jaccard fallback
    norm_tokens = _tokenize(norm)
    best_jaccard = MatchResult(slot=None, confidence=0.0, method="none")
    for fp in fps:
        fp_tokens = set(fp.tokens)
        if not fp_tokens:
            continue
        intersection = len(norm_tokens & fp_tokens)
        union = len(norm_tokens | fp_tokens)
        score = intersection / union if union else 0.0
        if score > best_jaccard.confidence:
            best_jaccard = MatchResult(
                slot=fp.slot, confidence=score, method="jaccard",
                jaccard_score=score,
            )
    if best_jaccard.confidence >= JACCARD_THRESHOLD:
        return best_jaccard

    return MatchResult(slot=None, confidence=best_jaccard.confidence,
                       method="none", jaccard_score=best_jaccard.confidence)


def projection_payload(fingerprints: list[PromptFingerprint]) -> dict[str, Any]:
    return {
        "__meta": {
            "schema_version": SCHEMA_VERSION,
            "artifact_kind": "prompt_shelf_fingerprints",
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "fingerprint_count": len(fingerprints),
            "anchor_len": ANCHOR_LEN,
            "distinctive_hit_threshold": DISTINCTIVE_HIT_THRESHOLD,
            "jaccard_threshold": JACCARD_THRESHOLD,
            "min_token_len": MIN_TOKEN_LEN,
            "source_root": ITEMS_DIR.relative_to(REPO_ROOT).as_posix(),
        },
        "fingerprints": [asdict(f) for f in fingerprints],
    }


def write_projection(payload: dict[str, Any], path: Path = PROJECTION_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--print", action="store_true", help="emit JSON to stdout")
    parser.add_argument("--write", action="store_true", help="write canonical projection")
    parser.add_argument("--check", action="store_true", help="exit non-zero on drift vs disk")
    args = parser.parse_args()

    fingerprints = build_fingerprints()
    payload = projection_payload(fingerprints)

    if args.write:
        write_projection(payload)
        print(f"wrote {PROJECTION_PATH.relative_to(REPO_ROOT)} "
              f"({len(fingerprints)} fingerprints)")
        return 0

    if args.check:
        if not PROJECTION_PATH.exists():
            print("projection missing on disk", file=sys.stderr)
            return 2
        on_disk = json.loads(PROJECTION_PATH.read_text())
        # Compare ignoring generated_at timestamp
        on_disk_meta = dict(on_disk.get("__meta", {}))
        on_disk_meta.pop("generated_at", None)
        new_meta = dict(payload["__meta"])
        new_meta.pop("generated_at", None)
        if (on_disk_meta == new_meta and
                on_disk.get("fingerprints") == payload["fingerprints"]):
            print("clean")
            return 0
        print("drift detected", file=sys.stderr)
        return 1

    if args.print or not (args.write or args.check):
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
