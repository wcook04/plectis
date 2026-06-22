"""README human-front-door binding validator (the binding plane).

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
code blocks, links, the banner, the diagram) and BINDINGS (witness -> entry
packet, links -> files), never a hand-written snapshot of the README's prose.
That is what lets the human front door evolve freely while its truth stays
bound. Reuses the overclaim patterns from public_entry_docs so the no-overclaim
guard has one owner.

Authority ceiling: this is a first-screen legibility + projection-binding read
model. It does not prove reader comprehension, authorize release or publication,
claim private-root equivalence, call providers, mutate source, prove
correctness, or certify production readiness.
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
    (r"\b\d+\s+(?:organs?|components?)\b", "hardcoded-component-count"),
    (r"/Users/", "raw-local-path"),
    (r"\bclick here\b", "low-scent-link-label"),
)


def _hero_region(text: str) -> str:
    """Return everything before the first level-2 (``## ``) heading.

    - Teleology: the first-impression region a cold reader meets before any
      section break: banner, H1, promise, and link rail.
    - Guarantee: returns text up to the first line beginning ``## ``; whole text
      when there is none.
    """
    marker = "\n## "
    return text.split(marker, 1)[0] if marker in text else text


def _headings(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*\S)\s*$", line)
        if m:
            out.append((len(m.group(1)), m.group(2).strip()))
    return out


def _anchor_slug(heading: str) -> str:
    slug = heading.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug


def _markdown_links(text: str) -> list[tuple[str, str]]:
    # [label](dest) but not images ![alt](src)
    return [
        (m.group(1), m.group(2))
        for m in re.finditer(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)", text)
    ]


def _fenced_blocks(text: str) -> list[str]:
    return re.findall(r"```[^\n]*\n(.*?)```", text, flags=re.DOTALL)


def validate_readme_front_door(
    public_root: Path,
    out: Path | None = None,
    *,
    command: str = "pytest",
) -> dict[str, Any]:
    """Validate README.md as a human front door bound to the truth plane.

    - Reads: <public_root>/README.md, <public_root>/atlas/entry_packet.json, and
      the banner / link destinations referenced by the README.
    - Returns: a receipt dict with status pass/blocked, per-check findings, and
      a blocking_codes list. Writes the receipt to ``out`` when provided.
    - Fails closed: any structural gap, broken binding, hero ontology leak, or
      overclaim sets status='blocked' with a specific code.
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

    # --- 6. witness command present AND bound to the canonical first command ---
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

    # --- 7. a vertical explanatory diagram (flowchart TD) ---
    findings["vertical_diagram_present"] = bool(
        re.search(r"```mermaid\s+flowchart\s+TD", text)
    )
    if not findings["vertical_diagram_present"]:
        blocking.append("README_VERTICAL_DIAGRAM_MISSING")

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

    # --- 11. numbered process diagram with a parity table ---
    # The explanatory diagram is a RUNTIME STORY: edges carry numbered
    # transitions, and an adjacent table restates the same numbers in prose
    # (which also serves as the accessible text equivalent). Assert the edge
    # numbering is sequential and unique and that the diagram edges and the table
    # steps agree. We check structure/parity, NOT the natural-language labels.
    mermaid_m = re.search(r"```mermaid\s+(.*?)```", text, flags=re.DOTALL)
    edge_numbers: list[int] = []
    if mermaid_m:
        # edge labels look like:  A -->|"1 · run Plectis locally"| B
        edge_numbers = [
            int(n) for n in re.findall(r"-->\s*\|\s*\"?\s*(\d+)", mermaid_m.group(1))
        ]
    # table step numbers: leading "| N |" cells in the step table rows
    table_numbers = [int(n) for n in re.findall(r"^\|\s*(\d+)\s*\|", text, re.MULTILINE)]
    findings["diagram_edge_numbers"] = edge_numbers
    findings["table_step_numbers"] = table_numbers
    expected_seq = list(range(1, len(edge_numbers) + 1))
    if not edge_numbers:
        blocking.append("README_DIAGRAM_EDGES_UNNUMBERED")
    elif edge_numbers != expected_seq:
        blocking.append("README_DIAGRAM_EDGE_NUMBERING_NONSEQUENTIAL")
    elif sorted(set(table_numbers)) != expected_seq:
        blocking.append("README_DIAGRAM_TABLE_PARITY_MISMATCH")

    # --- 12. the primary human witness is a TEXT projection, not raw JSON ---
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
