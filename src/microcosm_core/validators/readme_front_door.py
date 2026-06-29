"""
README human-front-door binding validator (the binding plane).

This validator is the missing third plane of the public entry assurance model:

  - Truth plane: machine contracts (entry_packet.json, cli.py, the registries)
    where exactness belongs, enforced by validators/public_entry_docs.py.
  - Human-experience plane: README.md, curated prose judged by structural
    first-screen legibility and cold-reader comprehension, NOT by exact strings.
  - Binding plane (this module): check the rendered README against the truth
    plane WITHOUT dictating editorial wording. The witness command must resolve
    to the canonical first command; links must resolve to real destinations;
    the approved banner must exist; the hero must not leak internal ontology;
    and the prose must not overclaim beyond its evidence.

It deliberately queries SEMANTIC STRUCTURE (heading tree, hero region, fenced
code blocks, links, the banner, the human-text witness) and BINDINGS (witness ->
entry packet, links -> files), never a hand-written snapshot of the README's prose.
That is what lets the human front door evolve freely while its truth stays
bound. Reuses the overclaim patterns from public_entry_docs so the no-overclaim
guard has one owner.

Authority ceiling: this is a first-screen legibility + projection-binding read
model. It does not prove reader comprehension, authorize release or publication,
claim private-root equivalence, call providers, mutate source, prove
correctness, or certify production readiness.

[PURPOSE]
- Teleology: Exposes `microcosm_core.validators.readme_front_door` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: CHECKER_ID, HERO_BANNED_PATTERNS, validate_readme_front_door, main
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: microcosm_core.receipts, microcosm_core.schemas, microcosm_core.validators.public_entry_docs
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict
from microcosm_core.validators.public_entry_docs import (
    PUBLIC_ENTRY_OVERCLAIM_PATTERNS,
)


CHECKER_ID = "checker.microcosm.validators.readme_front_door"

# Terms that must not appear in the HERO (banner + H1 + promise + link rail,
# i.e. everything before the first H2). They are technically true lower down,
# but in the first impression they are internal ontology or jargon that costs a
# cold reader recognition. Progressive disclosure, not deception.
HERO_BANNED_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\.microcosm\b", "compatibility-state-dir"),
    (r"\bmicrocosm_core\b", "package-internal-name"),
    (r"(?<![./\w])microcosm(?![_\w])", "former-public-name"),
    (r"\b\w+_route\b", "internal-route-id"),
    (r"\baccepted_current_authority\b", "registry-status-token"),
    (r"\bevidence_class\b", "evidence-taxonomy-token"),
    (r"/Users/", "raw-local-path"),
    (r"\bclick here\b", "low-scent-link-label"),
)
FRONT_DOOR_SIGNIFICANCE_WORD_LIMIT = 850
FRONT_DOOR_LOCAL_ONLY_WORD_LIMIT = 180
FRONT_DOOR_CLAIM_GRAMMAR_WORD_LIMIT = 1500
FRONT_DOOR_REQUIRED_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"\bpublic\b.{0,80}\bexecutable\b|\bexecutable\b.{0,80}\bpublic\b",
        "public-executable-identity",
    ),
    (r"\bmechanisms?\b|\bcomponents?\b", "mechanism-or-component-surface"),
    (r"\bformal proof\b", "formal-proof-family"),
    (r"\bagent (?:reliability and safety|safety|reliability)\b", "agent-safety-family"),
    (r"\b(?:research and forecasting|research/forecasting|forecasting)\b", "research-forecasting-family"),
    (r"\bprojection[- ]drift\b", "projection-drift-family"),
    (r"\bvalidators?\b", "validator-family"),
    (r"\bwork landing\b", "work-landing-family"),
    (r"\bcontinuity\b", "continuity-family"),
    (r"\bevidence class\b", "evidence-class-boundary"),
    (r"\bauthority ceiling\b", "authority-ceiling-boundary"),
)
FRONT_DOOR_LOCAL_ONLY_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bsmall,\s+source-open tool\b", "small-tool-primary-frame"),
    (
        r"\brun one command\b.{0,160}\blocal record\b",
        "run-one-command-local-record-primary-frame",
    ),
    (r"\blocal evidence router\b", "local-evidence-router-primary-frame"),
)
FRONT_DOOR_CLAIM_GRAMMAR_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"\bmechanisms?\s*[-=]+>\s*evidence discipline\s*[-=]+>\s*local runtime\b",
        "mechanism-evidence-runtime-read-order",
    ),
    (r"\bunderclaimed?\b|\bunderclaiming\b", "underclaim-guard"),
    (r"\bunderread\b", "underclaim-underread-guard"),
    (r"\boverclaimed?\b|\boverclaiming\b", "overclaim-guard"),
    (r"\boverread\b", "overclaim-overread-guard"),
    (
        r"\bresearch prototype\b.{0,80}\bdeveloper tool\b",
        "prototype-developer-tool-ceiling",
    ),
    (r"\bnot a hosted service\b", "hosted-service-ceiling"),
    (r"\bproduction-security\b", "production-security-ceiling"),
    (r"\bprofessional-advice\b", "professional-advice-ceiling"),
    (r"\bprovider-affiliated\b", "provider-affiliation-ceiling"),
    (r"\btrading or investment-advice\b", "trading-investment-ceiling"),
    (r"\bformal-proof correctness\b", "formal-proof-correctness-ceiling"),
    (r"\bsource-mutation authority\b", "source-mutation-ceiling"),
    (r"\brelease authority\b", "release-authority-ceiling"),
    (r"\bprivate-root equivalent\b", "private-root-equivalence-ceiling"),
    (r"\bcopied non-secret source bodies\b", "copied-non-secret-source-boundary"),
    (r"\bbounded public replays\b", "bounded-public-replay-boundary"),
)
FRONT_DOOR_FAMILY_CEILING_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"\bformal-proof cluster\b.{0,260}\bnot theorem-proof authority\b",
        "formal-proof-family-ceiling",
    ),
    (
        r"\bagent safety cluster\b.{0,260}\bnot production safety approval\b",
        "agent-safety-family-ceiling",
    ),
    (
        r"\bresearch cluster\b.{0,320}\bnot domain expertise\b.{0,120}\btrack-record authority\b",
        "research-family-ceiling",
    ),
    (
        r"\bprojection-drift cluster\b.{0,320}\bnot permission to export private/live material\b",
        "projection-drift-family-ceiling",
    ),
    (
        r"\bwork-continuity cluster\b.{0,260}\bnot authority to mutate\b",
        "work-continuity-family-ceiling",
    ),
)


def _word_window(text: str, limit: int) -> str:
    """
    [ACTION]
    Return the first `limit` whitespace-separated tokens as a single string.

    - Teleology: front-door weighting checks need a bounded first-reader window,
      not an exact prose snapshot.
    - Guarantee: preserves token order and lower-level punctuation while capping
      the scanned region by word count.
    - Fails: never raises.
    - Reads: call arguments only.
    - Writes: return values.
    """
    return " ".join(text.split()[:limit])


def _registry_component_count(public_root: Path) -> int | None:
    """
    [ACTION]
    Return the implemented public component count from the governed registry.

    - Teleology: allow an above-fold component count only when it is bound to the
      same registry that owns the system map.
    - Guarantee: returns the implemented_organs row count when the registry is
      available and well-shaped; otherwise None.
    - Fails: propagates JSON/schema IO failures from read_json_strict only when
      the file exists but is invalid.
    - Reads: <public_root>/core/organ_registry.json.
    - Writes: return values.
    """
    registry_path = public_root / "core/organ_registry.json"
    if not registry_path.is_file():
        return None
    registry = read_json_strict(registry_path)
    rows = registry.get("implemented_organs") if isinstance(registry, dict) else None
    return len(rows) if isinstance(rows, list) else None


def _hero_region(text: str) -> str:
    """
    [ACTION]
    Return everything before the first level-2 (``## ``) heading.

    - Teleology: the first-impression region a cold reader meets before any
      section break: banner, H1, promise, and link rail.
    - Guarantee: returns text up to the first line beginning ``## ``; whole text
      when there is none.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    marker = "\n## "
    return text.split(marker, 1)[0] if marker in text else text


def _headings(text: str) -> list[tuple[int, str]]:
    """
    [ACTION]
    - Teleology: Implements `_headings` for `microcosm_core.validators.readme_front_door` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    out: list[tuple[int, str]] = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
        if m:
            out.append((len(m.group(1)), m.group(2).strip()))
    return out


def _anchor_slug(heading: str) -> str:
    """
    [ACTION]
    - Teleology: Implements `_anchor_slug` for `microcosm_core.validators.readme_front_door` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


def _markdown_links(text: str) -> list[tuple[str, str]]:
    # [label](dest) but not images ![alt](src)
    """
    [ACTION]
    - Teleology: Implements `_markdown_links` for `microcosm_core.validators.readme_front_door` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return [
        (m.group(1), m.group(2))
        for m in re.finditer(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)", text)
    ]


def _fenced_blocks(text: str) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_fenced_blocks` for `microcosm_core.validators.readme_front_door` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return re.findall(r"```[^\n]*\n(.*?)```", text, flags=re.DOTALL)


def validate_readme_front_door(
    public_root: Path,
    out: Path | None = None,
    *,
    command: str = "pytest",
) -> dict[str, Any]:
    """
    [ACTION]
    Validate README.md as a human front door bound to the truth plane.

    - Reads: <public_root>/README.md, <public_root>/atlas/entry_packet.json, and
      the banner / link destinations referenced by the README.
    - Returns: a receipt dict with status pass/blocked, per-check findings, and
      a blocking_codes list. Writes the receipt to ``out`` when provided.
    - Fails closed: any structural gap, broken binding, hero ontology leak, or
      overclaim sets status='blocked' with a specific code.
    - Teleology: Implements `validate_readme_front_door` for `microcosm_core.validators.readme_front_door` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Writes: return values, declared filesystem outputs.
    """
    readme_path = public_root / "README.md"
    text = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    hero = _hero_region(text)
    normalized = " ".join(text.split())
    blocking: list[str] = []
    findings: dict[str, Any] = {}

    # --- 1. single H1, present, named ---
    h1s = [h for level, h in _headings(text) if level == 1]
    findings["h1"] = h1s[0] if h1s else None
    if h1s != ["Plectis"]:
        blocking.append("README_H1_NOT_PLECTIS")

    # --- 2. approved banner with useful alt, resolving to a real file ---
    banner = re.search(
        r"<img\b[^>]*?\bsrc\s*=\s*\"([^\"]+)\"[^>]*?>", hero, flags=re.DOTALL
    )
    alt = None
    banner_src = None
    if banner:
        banner_src = banner.group(1)
        alt_m = re.search(r"\balt\s*=\s*\"([^\"]*)\"", banner.group(0))
        alt = alt_m.group(1).strip() if alt_m else ""
    findings["banner_src"] = banner_src
    findings["banner_alt_present"] = bool(alt)
    if not banner_src:
        blocking.append("README_BANNER_MISSING")
    else:
        if not alt:
            blocking.append("README_BANNER_ALT_MISSING")
        if not banner_src.startswith("http"):
            if not (readme_path.parent / banner_src).is_file():
                blocking.append("README_BANNER_FILE_UNRESOLVED")
        # em-dash in alt is a hard ban (operator voice); use a colon.
        if alt and "—" in alt:
            blocking.append("README_BANNER_ALT_EM_DASH")

    # --- 3. recognition promise (a bold span) in the hero ---
    findings["hero_promise_present"] = bool(re.search(r"\*\*.+?\*\*", hero, re.DOTALL))
    if not findings["hero_promise_present"]:
        blocking.append("README_HERO_PROMISE_MISSING")

    # --- 4. a compact route rail in the hero (>= 3 links) ---
    hero_links = _markdown_links(hero)
    findings["hero_link_count"] = len(hero_links)
    if len(hero_links) < 3:
        blocking.append("README_ROUTE_RAIL_MISSING")

    # --- 5. no internal ontology / jargon in the hero ---
    hero_lower = hero.lower()
    hero_leaks = sorted(
        {
            label
            for pattern, label in HERO_BANNED_PATTERNS
            if re.search(pattern, hero_lower)
        }
    )
    findings["hero_banned_terms"] = hero_leaks
    if hero_leaks:
        blocking.append("README_HERO_ONTOLOGY_LEAK")

    # --- 6. the first reader window leads with mechanism significance, not local-record framing ---
    front_window = _word_window(text, FRONT_DOOR_SIGNIFICANCE_WORD_LIMIT)
    front_lower = front_window.lower()
    missing_significance = sorted(
        label
        for pattern, label in FRONT_DOOR_REQUIRED_PATTERNS
        if not re.search(pattern, front_lower, flags=re.DOTALL)
    )
    registry_count = _registry_component_count(public_root)
    count_claims = {
        int(match.group(1))
        for match in re.finditer(
            r"\b(\d+)\s+(?:bounded\s+)?(?:components?|mechanisms?|organs?)\b",
            front_lower,
        )
    }
    count_claim_bound = False
    if registry_count is not None:
        count_claim_bound = count_claims == {registry_count}
    local_only_window = _word_window(text, FRONT_DOOR_LOCAL_ONLY_WORD_LIMIT).lower()
    local_only_frames = sorted(
        label
        for pattern, label in FRONT_DOOR_LOCAL_ONLY_PATTERNS
        if re.search(pattern, local_only_window, flags=re.DOTALL)
    )
    claim_grammar_window = _word_window(
        text, FRONT_DOOR_CLAIM_GRAMMAR_WORD_LIMIT
    ).lower()
    missing_claim_grammar = sorted(
        label
        for pattern, label in FRONT_DOOR_CLAIM_GRAMMAR_PATTERNS
        if not re.search(pattern, claim_grammar_window, flags=re.DOTALL)
    )
    missing_family_ceilings = sorted(
        label
        for pattern, label in FRONT_DOOR_FAMILY_CEILING_PATTERNS
        if not re.search(pattern, claim_grammar_window, flags=re.DOTALL)
    )
    findings["front_door_required_context_missing"] = missing_significance
    findings["registry_component_count"] = registry_count
    findings["front_door_component_count_claims"] = sorted(count_claims)
    findings["registry_component_count_bound_in_front_door"] = count_claim_bound
    findings["front_door_local_only_frames"] = local_only_frames
    findings["front_door_claim_grammar_missing"] = missing_claim_grammar
    findings["front_door_family_ceilings_missing"] = missing_family_ceilings
    if missing_significance:
        blocking.append("README_FRONT_DOOR_SIGNIFICANCE_MISSING")
    if registry_count is None or not count_claim_bound:
        blocking.append("README_FRONT_DOOR_COMPONENT_COUNT_UNBOUND")
    if local_only_frames:
        blocking.append("README_FRONT_DOOR_LOCAL_ONLY_FRAME")
    if missing_claim_grammar:
        blocking.append("README_FRONT_DOOR_CLAIM_GRAMMAR_MISSING")
    if missing_family_ceilings:
        blocking.append("README_FRONT_DOOR_FAMILY_CEILING_MISSING")

    # --- 7. witness command present AND bound to the canonical first command ---
    entry_packet_path = public_root / "atlas/entry_packet.json"
    first_command = ""
    if entry_packet_path.is_file():
        entry_packet = read_json_strict(entry_packet_path)
        first_command = str(entry_packet.get("first_command") or "")
    # the canonical witness stripped of its <project> placeholder
    witness_stem = first_command.replace(" <project>", "").strip()
    blocks = _fenced_blocks(text)
    witness_present = bool(witness_stem) and any(witness_stem in b for b in blocks)
    findings["canonical_first_command"] = first_command
    findings["witness_command_bound"] = witness_present
    if not witness_stem:
        blocking.append("README_WITNESS_BINDING_UNAVAILABLE")
    elif not witness_present:
        blocking.append("README_WITNESS_COMMAND_UNBOUND")

    # --- 8. all relative links resolve (files + same-doc anchors) ---
    slugs = {_anchor_slug(h) for _, h in _headings(text)}
    broken: list[str] = []
    for _label, dest in _markdown_links(text):
        if dest.startswith(("http://", "https://", "mailto:")):
            continue
        file_part, _, anchor = dest.partition("#")
        if file_part:
            if not (readme_path.parent / file_part).exists():
                broken.append(dest)
        elif anchor and anchor not in slugs:
            broken.append(dest)
    findings["broken_links"] = broken
    if broken:
        blocking.append("README_BROKEN_LINK")

    # --- 9. no overclaim beyond evidence (reuse the public-entry patterns) ---
    overclaims = sorted(
        p for p in PUBLIC_ENTRY_OVERCLAIM_PATTERNS if re.search(p, normalized.lower())
    )
    findings["overclaim_patterns"] = overclaims
    if overclaims:
        blocking.append("README_OVERCLAIM")

    # --- 10. compatibility lineage note present (but not in the hero) ---
    findings["compatibility_note_present"] = "Microcosm became Plectis" in text
    if not findings["compatibility_note_present"]:
        blocking.append("README_COMPATIBILITY_NOTE_MISSING")

    # --- 11. the primary human witness is a TEXT projection, not raw JSON ---
    # The first demonstration a human meets must be the human-readable summary;
    # the machine JSON card stays available as a deeper route (check 6 binds the
    # canonical first command). This guards against regressing the "See it work"
    # block back to a raw JSON-only witness.
    findings["human_text_witness_present"] = any(
        "plectis tour --format text" in b for b in blocks
    )
    if not findings["human_text_witness_present"]:
        blocking.append("README_HUMAN_WITNESS_MISSING")

    receipt = {
        "checker_id": CHECKER_ID,
        "command": command,
        "status": "pass" if not blocking else "blocked",
        "blocking_codes": sorted(set(blocking)),
        "findings": findings,
        "authority_ceiling": {
            "first_screen_legibility_and_binding_only": True,
            "reader_comprehension_guarantee": False,
            "release_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "whole_system_correctness_claim": False,
        },
    }
    if out is not None:
        write_json_atomic(out, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.validators.readme_front_door` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description="Validate the README human front door.")
    parser.add_argument("--root", default=".", help="public root containing README.md")
    parser.add_argument("--out", default=None, help="optional receipt path")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    out = Path(args.out).resolve() if args.out else None
    receipt = validate_readme_front_door(root, out, command="cli")
    print(f"readme front door: {receipt['status']}")
    for code in receipt["blocking_codes"]:
        print(f"  blocked: {code}")
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
