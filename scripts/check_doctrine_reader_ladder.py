#!/usr/bin/env python3
"""Reader-ladder accessibility gate for the doctrine enrichment cards.

The formal-soundness gate (check_doctrine_formal_soundness.py) governs the
EXPERT end of each doctrine object: symbol/formula agreement. This gate governs
the LAY end: a plain reading and a bounded analogy that give a non-expert a
clean mental handle without weakening the source boundary.

The load-bearing rule is the ANALOGY BOUNDARY. An analogy without an explicit
"where this stops" is itself a laundering vector: it lets a vivid metaphor stand
in for doctrine the source never carried. So every analogy must name its limit,
and the lay layer may never claim that an analogy or example PROVES the object.

Per-object contract (the `reader_ladder` block):
  - plain:           one short, literal lay sentence (no jargon, no symbols).
  - analogy.text:    one concrete everyday analogy.
  - analogy.maps:    >=1 {doctrine, analogy} correspondence, so the fidelity of
                     the analogy is inspectable (the anti-laundering map).
  - analogy.boundary: where the analogy stops; must signal a limit.
  - why_it_matters:  why a reader should care, in practical terms.
  - potential_misread:  the tempting but wrong takeaway.

Reader-soundness rules enforced:
  - lay fields carry NO LaTeX / math symbols (those live in the formal layer);
  - lay fields use NO public-vocab-banned visible term (receipt, substrate,
    organ, ...) -- mirrors BANNED_VISIBLE_TERMS in the public-site builder;
  - lay fields use NO grandiosity / "not X, but Y" framing;
  - the affirmative lay fields (plain, analogy.text, why_it_matters) make NO
    proof/guarantee claim (a "does not prove" disclaimer is fine in boundary /
    potential_misread, where naming the limit is the point).

This is reader content, never support evidence: like the formal gate it never
reads or raises axiom support (P-15).

Usage:
  python3 scripts/check_doctrine_reader_ladder.py --check
  python3 scripts/check_doctrine_reader_ladder.py --json
  python3 scripts/check_doctrine_reader_ladder.py --explain AX-1
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_DEFAULT = Path(__file__).resolve().parents[1] / "core" / "doctrine_enrichment.json"

# Mirror of BANNED_VISIBLE_TERMS in tools/meta/dissemination/build_microcosm_public_site.py.
# Keep aligned with the public-site firewall; the lay layer is public-facing.
BANNED_VISIBLE_TERMS = (
    "acceptance", "receipt", "claim ceiling", "claim-ceiling", "workitem",
    "raw seed", "raw-seed", "annex", "batch", "capsule", "closeout",
    "macro", "substrate", "organ",
)

# Grandiosity / AI-tell framings the doctrine voice rules forbid.
BANNED_FRAMINGS = (
    "conscience", "worldview", "world view", "mind-blowing", "mind blowing",
    "broadest laws", "wants its work to check out",
    "governs how the system is allowed to behave",
)
_NOT_BUT_RE = re.compile(r"\bnot\b[^.;]{1,30},?\s+but\b", re.IGNORECASE)
# Affirmative proof/guarantee claims (word-boundary; "improve"/"proving" are safe).
_PROOF_RE = re.compile(r"\b(prove|proves|proved|proof|guarantee|guarantees|guaranteed)\b", re.IGNORECASE)
# Math leakage into a lay field.
_MATH_RE = re.compile(r"[\\$]|[⊑⊒⊏⊐⊓⊔⨅⨆∧∨¬∀∃∈∉≤≥≠⇒⇔→↦⊤⊥∅⟨⟩φρτλσμα]|_\{|\^\{")
# A boundary must actually signal a limit.
_LIMIT_RE = re.compile(r"\b(stop|stops|does not|doesn't|do not|don't|not |isn't|only|beyond|no more than|cannot|can't|never)\b", re.IGNORECASE)

PLAIN_MAX_CHARS = 320
PLAIN_MAX_SENTENCES = 3


def _banned_terms(text: str) -> list[str]:
    low = (text or "").lower()
    return [t for t in BANNED_VISIBLE_TERMS if t in low]


def _banned_framings(text: str) -> list[str]:
    low = (text or "").lower()
    hits = [t for t in BANNED_FRAMINGS if t in low]
    if _NOT_BUT_RE.search(text or ""):
        hits.append("not-X-but-Y framing")
    return hits


def _sentences(text: str) -> int:
    return len([s for s in re.split(r"[.;]\s+|[.;]$", (text or "").strip()) if s.strip()])


def audit_record(rec: dict) -> dict:
    rl = rec.get("reader_ladder")
    issues: list[str] = []
    if not isinstance(rl, dict):
        return {"id": rec.get("id"), "kind": rec.get("kind"), "issues": ["no reader_ladder block"], "clean": False}

    plain = str(rl.get("plain") or "").strip()
    why = str(rl.get("why_it_matters") or "").strip()
    misread = str(rl.get("potential_misread") or "").strip()
    analogy = rl.get("analogy") if isinstance(rl.get("analogy"), dict) else {}
    a_text = str(analogy.get("text") or "").strip()
    a_boundary = str(analogy.get("boundary") or "").strip()
    a_maps = analogy.get("maps") if isinstance(analogy.get("maps"), list) else []

    # presence
    if not plain:
        issues.append("plain missing")
    if not a_text:
        issues.append("analogy.text missing")
    if not a_boundary:
        issues.append("analogy.boundary missing")
    if not why:
        issues.append("why_it_matters missing")
    if not misread:
        issues.append("potential_misread missing")

    # plain shape
    if plain:
        if len(plain) > PLAIN_MAX_CHARS:
            issues.append(f"plain too long ({len(plain)} > {PLAIN_MAX_CHARS} chars)")
        if _sentences(plain) > PLAIN_MAX_SENTENCES:
            issues.append(f"plain too many sentences ({_sentences(plain)} > {PLAIN_MAX_SENTENCES})")

    # anti-laundering: the analogy must map and must bound.
    if not a_maps:
        issues.append("analogy.maps empty (need >=1 doctrine->analogy correspondence)")
    else:
        for i, m in enumerate(a_maps):
            if not (isinstance(m, dict) and str(m.get("doctrine") or "").strip() and str(m.get("analogy") or "").strip()):
                issues.append(f"analogy.maps[{i}] needs non-empty doctrine and analogy")
                continue
            # maps render to readers too: hold them to the vocab / math floor.
            for side in ("doctrine", "analogy"):
                val = str(m.get(side) or "")
                for term in _banned_terms(val):
                    issues.append(f"analogy.maps[{i}].{side}: banned visible term '{term}'")
                if _MATH_RE.search(val):
                    issues.append(f"analogy.maps[{i}].{side}: math/LaTeX leaked into a lay field")
    if a_boundary and not _LIMIT_RE.search(a_boundary):
        issues.append("analogy.boundary does not signal a limit (no stop/does-not/only/...)")

    # voice + vocab + no-overclaim across the lay fields
    affirmative = {"plain": plain, "analogy.text": a_text, "why_it_matters": why}
    all_fields = {**affirmative, "analogy.boundary": a_boundary, "potential_misread": misread}
    for fname, val in all_fields.items():
        for term in _banned_terms(val):
            issues.append(f"{fname}: banned visible term '{term}'")
        for fr in _banned_framings(val):
            issues.append(f"{fname}: banned framing '{fr}'")
        if _MATH_RE.search(val or ""):
            issues.append(f"{fname}: math/LaTeX leaked into a lay field")
    for fname, val in affirmative.items():
        if _PROOF_RE.search(val or ""):
            issues.append(f"{fname}: proof/guarantee claim in an affirmative lay field (allowed only in boundary/potential_misread)")

    return {"id": rec.get("id"), "kind": rec.get("kind"), "issues": issues, "clean": not issues}


def run(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records") or []
    results = [audit_record(r) for r in records]
    defects = [r for r in results if not r["clean"]]
    return {
        "source": str(path),
        "total": len(results),
        "clean": len(results) - len(defects),
        "defective": len(defects),
        "results": results,
    }


def _fmt(report: dict) -> str:
    lines = [f"doctrine reader ladder: {report['clean']}/{report['total']} clean, {report['defective']} with defects", ""]
    for r in report["results"]:
        if r["clean"]:
            continue
        lines.append(f"  {r['id']} ({r['kind']}):")
        for it in r["issues"]:
            lines.append(f"    {it}")
    if report["defective"] == 0:
        lines.append("  every object has a sound plain reading and a bounded analogy.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry for the doctrine reader-ladder accessibility gate.

    - Teleology: Operator/CI front door enforcing each enrichment object's lay layer (plain reading + bounded analogy with maps/boundary, no laundering, banned visible term, or affirmative overclaim).
    - Guarantee: Prints a human or --json report (or, with --explain ID, one record's reader_ladder + audit); with --check returns 1 if any record is defective, else 0.
    - Fails: --explain on an unknown id -> "no record <ID>" on stderr, exit 2; missing/invalid --path -> json.JSONDecodeError/FileNotFoundError -> uncaught traceback.
    - Reads: core/doctrine_enrichment.json (or --path).
    - When-needed: CI-gating or debugging the lay reader layer; --explain to inspect one record's ladder.
    - Escalates-to: run (full audit), audit_record (per-record lay-field checks).
    """
    ap = argparse.ArgumentParser(description="Doctrine reader-ladder accessibility gate.")
    ap.add_argument("--path", default=str(REPO_DEFAULT))
    ap.add_argument("--check", action="store_true", help="exit 1 on any defect")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--explain", metavar="ID")
    args = ap.parse_args(argv)
    path = Path(args.path)
    if args.explain:
        data = json.loads(path.read_text(encoding="utf-8"))
        rec = next((r for r in data.get("records", []) if r.get("id") == args.explain), None)
        if not rec:
            print(f"no record {args.explain}", file=sys.stderr)
            return 2
        print(json.dumps({"reader_ladder": rec.get("reader_ladder"), "audit": audit_record(rec)}, indent=2, ensure_ascii=False))
        return 0
    report = run(path)
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else _fmt(report))
    if args.check and report["defective"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
