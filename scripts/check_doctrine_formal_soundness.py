#!/usr/bin/env python3
"""Formal-statement soundness gate for the doctrine enrichment cards.

The coverage projection (build_doctrine_enrichment_health.py) counts *presence*
of enrichment fields; the public-site tests check that every formal LaTeX field
*renders* without a raw fallback. Neither checks that the symbol table is sound.

This gate closes that gap. For every enrichment record's `formal` block it
enforces a single, expert-defensible contract:

  1. No dangling symbol.   Every entry in `formal.symbols` must actually appear
     in `formal.latex`. (Catches a symbol table that documents a term the
     formula never uses, e.g. AX-3 once declared holds(u,cred) with no `holds`
     in the formula.)

  2. No undefined symbol.  Every *free variable* and every *named operator*
     (\\mathrm{...}, \\mathcal{...}, \\operatorname{...}) that appears in the
     formula must have an entry in `formal.symbols`. (Catches a formula that
     uses F, policy, world, or strength with nothing in the table naming them.)

Standard logical / relational / lattice connectives, grouping delimiters, and
self-describing verdict constants (\\mathsf{...}) are common formal vocabulary
and need no glossary entry; structural roman connectors (\\mathrm{else},
\\mathrm{where}, \\mathrm{otherwise}) are exempt for the same reason.

This is a *reader-soundness* gate, not a support gate: it never reads or writes
axiom support, never raises a claim ceiling, and treats the enrichment latex as
a reviewed rendering of the source clause (P-15). It only asks that the rendered
formula and its symbol table agree with each other.

Macro vocabulary mirrors the bounded renderer in
tools/meta/dissemination/build_microcosm_public_site.py (_LATEX_SYMBOLS /
_LATEX_TEXTOPS / _LATEX_DROP); keep them aligned if the renderer grammar grows.

Usage:
  python3 scripts/check_doctrine_formal_soundness.py --check     # exit 1 on any defect
  python3 scripts/check_doctrine_formal_soundness.py --json      # machine report
  python3 scripts/check_doctrine_formal_soundness.py --explain AX-3   # show atoms
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_DEFAULT = Path(__file__).resolve().parents[1] / "core" / "doctrine_enrichment.json"

# --- macro classification (mirrors the bounded renderer grammar) ----------

# Greek letters are *variables*; if a formula uses one it must be defined.
GREEK_VARS = {
    "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta",
    "theta", "vartheta", "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron",
    "pi", "varpi", "rho", "varrho", "sigma", "varsigma", "tau", "upsilon",
    "phi", "varphi", "chi", "psi", "omega",
    "Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Upsilon",
    "Phi", "Psi", "Omega", "ell",
}

# Everything below is common formal vocabulary: connectives, relations, order /
# lattice operators, set ops, quantifiers, grouping, and well-known constants.
# Using one of these needs no symbol-table entry.
CONNECTIVE_MACROS = {
    # arrows / implication / quantifiers
    "Rightarrow", "Leftrightarrow", "Leftarrow", "rightarrow", "leftarrow",
    "leftrightarrow", "implies", "iff", "to", "gets", "mapsto", "longmapsto",
    "hookrightarrow", "forall", "exists", "nexists",
    # set / membership
    "in", "notin", "ni", "subseteq", "subset", "supseteq", "supset",
    "cap", "cup", "setminus", "uplus", "emptyset", "varnothing",
    # comparison / equivalence
    "leq", "le", "geq", "ge", "neq", "ne", "equiv", "approx", "cong",
    "leqslant", "geqslant", "preceq", "succeq", "prec", "succ",
    # logic
    "land", "wedge", "lor", "vee", "lnot", "neg",
    # order / lattice
    "top", "bot", "perp", "sqsubseteq", "sqsubset", "sqsupseteq", "sqsupset",
    "sqcap", "sqcup", "bigsqcap", "bigsqcup", "bigwedge", "bigvee",
    "bigcap", "bigcup",
    # arithmetic-ish / misc operators and constants
    "circ", "cdot", "times", "ast", "star", "bullet", "oplus", "otimes", "odot",
    "bigoplus", "bigotimes", "sum", "prod", "coprod", "int",
    "models", "vdash", "dashv", "therefore", "because",
    "ldots", "cdots", "dots", "vdots",
    "infty", "partial", "nabla", "angle", "Box", "Diamond", "square",
    # delimiters / bars
    "langle", "rangle", "lceil", "rceil", "lfloor", "rfloor",
    "lvert", "rvert", "lVert", "rVert", "vert", "Vert",
    "mid", "parallel", "nmid", "lbrace", "rbrace", "backslash",
}

# Size / delimiter hints carry no symbol content (dropped by the renderer).
DROP_MACROS = {
    "big", "Big", "bigg", "Bigg", "bigl", "bigr", "Bigl", "Bigr",
    "bigm", "Bigm", "left", "right", "displaystyle", "textstyle",
    "limits", "nolimits", "mathopen", "mathclose",
}

TEXTOPS = {"text", "mathrm", "mathsf", "mathbf", "mathit", "mathtt",
           "operatorname", "mathbb", "mathcal"}
# Spacing macros (carry no symbol content) and escaped literals / delimiters.
SPACE_MACROS = {",", ";", ":", "!", " ", "quad", "qquad"}
LITERAL_TOKENS = {"{", "}", "|", "%", "&", "#", "$", "_", "^", "\\", "."}
# Roman text that reads as a connective, not a named operator.
STRUCTURAL_KEYWORDS = {"else", "where", "otherwise", "given", "if", "then"}
# \mathsf{...} (and pure style ops) name self-describing verdict constants.
VERDICT_TEXTOPS = {"mathsf", "mathbf", "mathit", "mathtt", "mathbb", "text"}
# \mathcal / \mathrm / \operatorname name content operators that need defining.
CONTENT_TEXTOPS = {"mathrm", "mathcal", "operatorname"}

_SPACE_MACRO_RE = re.compile(r"\\[,;:!]|\\quad|\\qquad|\\ ")


def _normalize(s: str) -> str:
    """Prepare a symbol string for literal containment checks.

    Teleology: make dangling-symbol detection robust to TeX spacing commands and
    human whitespace in doctrine symbol-table entries.
    Guarantee: returns a string with supported spacing macros and all whitespace
    removed, so `x`, `x\\,`, and `x ` compare the same.
    Fails: never raises for falsey input because it stringifies `s or ""`; only
    unexpected `re` engine failures would propagate.
    Reads: the supplied string only.
    Writes: nothing.
    Non-goal: not a LaTeX parser and not semantic equivalence.
    """
    s = _SPACE_MACRO_RE.sub("", str(s or ""))
    return re.sub(r"\s+", "", s)


def atoms(latex: str) -> dict[str, set[str]]:
    """Extract the reviewable vocabulary from one bounded-LaTeX formula.

    Teleology: separate formula vocabulary that needs a symbol-table definition
    from common logic/connective syntax and self-describing verdict constants.
    Guarantee: returns sets for free Latin variables, Greek variables, named
    content operators, verdict constants, structural connectors, and connectives.
    Fails: malformed or unknown macros are surfaced as named atoms for review
    instead of raising; falsey input becomes an empty scan.
    Reads: the supplied LaTeX string only.
    Writes: nothing.
    Non-goal: does not execute LaTeX, prove mathematical truth, or infer
    bindings from natural-language labels.
    """
    s = str(latex or "")
    free: set[str] = set()
    greek: set[str] = set()
    named: set[str] = set()
    verdicts: set[str] = set()
    structural: set[str] = set()
    conn: set[str] = set()
    i, n = 0, len(s)

    def read_group(k: int) -> tuple[str, int]:
        """Read a brace group starting at `k` and return its body plus next index.

        Teleology: consume the body of a text operator without treating nested
        braces as separate top-level tokens.
        Guarantee: returns `(body, next_index)` for a balanced group and the
        remaining suffix plus `len(s)` for an unterminated group.
        Fails: does not raise for unterminated braces; the caller sees the
        resulting token shape.
        Reads: the enclosing `s` string and the starting index.
        Writes: nothing.
        Non-goal: does not validate LaTeX grouping globally.
        """
        depth, start = 0, k
        while k < len(s):
            if s[k] == "{":
                depth += 1
            elif s[k] == "}":
                depth -= 1
                if depth == 0:
                    return s[start + 1:k], k + 1
            k += 1
        return s[start + 1:], len(s)

    def skip_script_arg(k: int) -> int:
        """Skip the argument after `_` or `^` without auditing its inner letters.

        Teleology: prevent script modifiers such as the `i` in `x_i` from being
        counted as independent free variables.
        Guarantee: returns the index after one braced group, macro, single
        character, or trailing position following a script marker.
        Fails: never raises for a missing argument; returns the current or final
        index after the best-effort skip.
        Reads: the enclosing `s` string and the starting index.
        Writes: nothing.
        Non-goal: does not parse nested math semantics inside scripts.
        """
        while k < len(s) and s[k] == " ":
            k += 1
        if k < len(s) and s[k] == "{":
            _, k = read_group(k)
            return k
        if k < len(s) and s[k] == "\\":
            m = re.match(r"\\([A-Za-z]+|.)", s[k:])
            return k + 1 + len(m.group(1)) if m else k + 1
        return k + 1 if k < n else k

    while i < n:
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([A-Za-z]+|.)", s[i:])
            if not m:
                i += 1
                continue
            name = m.group(1)
            i += 1 + len(name)
            if name in TEXTOPS:
                while i < n and s[i] == " ":
                    i += 1
                if i < n and s[i] == "{":
                    inner, i = read_group(i)
                    # The whole group is the operator NAME, not a list of free
                    # variables; nested operators (deref(tok)) appear as separate
                    # \mathrm tokens in the main scan, not inside this group.
                    inner_norm = inner.strip()
                    token = f"\\{name}{{{inner_norm}}}"
                    if name in VERDICT_TEXTOPS:
                        verdicts.add(token)
                    elif inner_norm in STRUCTURAL_KEYWORDS:
                        structural.add(token)
                    else:  # content operator (mathrm / mathcal / operatorname)
                        named.add(token)
                continue
            if name in SPACE_MACROS or name in LITERAL_TOKENS:
                continue
            if name in GREEK_VARS:
                greek.add(f"\\{name}")
            elif name in CONNECTIVE_MACROS or name in DROP_MACROS:
                conn.add(f"\\{name}")
            else:
                # unknown macro: surface it as a named op so it is reviewed
                named.add(f"\\{name}")
            continue
        if c in ("_", "^"):
            i = skip_script_arg(i + 1)
            continue
        if c == "{" or c == "}":
            i += 1
            continue
        if c.isalpha():
            free.add(c)
            i += 1
            continue
        i += 1

    return {
        "free": free,
        "greek": greek,
        "named": named,
        "verdicts": verdicts,
        "structural": structural,
        "connectives": conn,
    }


def audit_record(rec: dict) -> dict:
    """Compare one formal block's formula with its symbol table.

    Teleology: enforce reader soundness between a formal formula and its
    declared symbol table.
    Guarantee: returns id, kind, dangling declared symbols, undefined variables,
    undefined operators, and a clean flag for one enrichment record.
    Fails: malformed or missing `formal`/`symbols` structures degrade to empty
    strings/lists rather than raising.
    Reads: the supplied record only.
    Writes: nothing.
    Non-goal: a clean result does not prove the doctrine clause, validate
    support evidence, or raise the record's authority ceiling.
    """
    formal = rec.get("formal") or {}
    latex = str(formal.get("latex") or "")
    symbols = formal.get("symbols") or []
    sym_strings = [str(s.get("sym") or "") for s in symbols if str(s.get("sym") or "").strip()]

    # 1) dangling: each declared symbol must appear in the formula.
    norm_latex = _normalize(latex)
    dangling = [s for s in sym_strings if _normalize(s) not in norm_latex]

    # 2) undefined: each free var / named op in the formula must be declared.
    f = atoms(latex)
    # Build the vocabulary the symbol table *defines* (union of atoms over syms,
    # plus the verbatim normalized sym strings for compound coverage).
    declared_free: set[str] = set()
    declared_greek: set[str] = set()
    declared_named: set[str] = set()
    for s in sym_strings:
        a = atoms(s)
        declared_free |= a["free"]
        declared_greek |= a["greek"]
        declared_named |= a["named"] | a["verdicts"]

    undefined_vars = sorted(
        [v for v in f["free"] if v not in declared_free]
        + [g for g in f["greek"] if g not in declared_greek and g.lstrip("\\") not in {x.lstrip("\\") for x in declared_greek}]
    )
    undefined_ops = sorted([op for op in f["named"] if op not in declared_named])

    clean = not dangling and not undefined_vars and not undefined_ops
    return {
        "id": rec.get("id"),
        "kind": rec.get("kind"),
        "dangling": dangling,
        "undefined_vars": undefined_vars,
        "undefined_ops": undefined_ops,
        "clean": clean,
    }


def run(path: Path) -> dict:
    """Audit every formal enrichment record in one doctrine file.

    Teleology: provide the reusable report body for CLI checks and the aggregate
    doctrine-health projection.
    Guarantee: returns source path, total audited formal records, clean/defective
    counts, and per-record audit rows; records without `formal` are skipped.
    Fails: propagates `FileNotFoundError` and `json.JSONDecodeError` for the
    supplied path.
    Reads: `core/doctrine_enrichment.json` or the supplied path.
    Writes: nothing.
    Non-goal: does not own field-presence coverage for records without formal
    blocks.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records") or []
    results = [audit_record(r) for r in records if r.get("formal")]
    defects = [r for r in results if not r["clean"]]
    return {
        "source": str(path),
        "total": len(results),
        "clean": len(results) - len(defects),
        "defective": len(defects),
        "results": results,
    }


def _fmt(report: dict) -> str:
    """Render the formal-soundness report for a terminal reader.

    Teleology: turn the machine report into concise CI/local-check text without
    changing the audit contract.
    Guarantee: groups each defective record by id/kind and lists dangling
    declarations, undefined variables, and undefined operators.
    Fails: raises `KeyError` if called with a dict that is not the report shape
    produced by `run`.
    Reads: the supplied report dict only.
    Writes: nothing.
    Non-goal: not a machine interface; JSON output remains the stable contract.
    """
    lines = [
        f"doctrine formal soundness: {report['clean']}/{report['total']} clean, "
        f"{report['defective']} with defects",
        "",
    ]
    for r in report["results"]:
        if r["clean"]:
            continue
        lines.append(f"  {r['id']} ({r['kind']}):")
        if r["dangling"]:
            lines.append(f"    dangling (declared, not in formula): {r['dangling']}")
        if r["undefined_vars"]:
            lines.append(f"    undefined variables (in formula, not declared): {r['undefined_vars']}")
        if r["undefined_ops"]:
            lines.append(f"    undefined operators (in formula, not declared): {r['undefined_ops']}")
    if report["defective"] == 0:
        lines.append("  all formal statements sound: every symbol defined, no danglers.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry for the doctrine formal-statement soundness gate.

    - Teleology: Operator/CI front door enforcing symbol/formula agreement on every enrichment `formal` block (no dangling declared symbol, no undefined free var or named operator).
    - Guarantee: Prints a human or --json report (or, with --explain ID, the extracted atoms for one record); with --check returns 1 if any record is defective, else 0.
    - Fails: --explain on an unknown id -> "no record <ID>" on stderr, exit 2; missing/invalid --path -> json.JSONDecodeError/FileNotFoundError -> uncaught traceback.
    - Reads: core/doctrine_enrichment.json (or --path).
    - When-needed: CI-gating or debugging doctrine formal blocks; --explain to inspect one record's symbol atoms.
    - Escalates-to: run (full audit), audit_record + atoms (per-record symbol extraction).
    """
    ap = argparse.ArgumentParser(description="Doctrine formal-statement soundness gate.")
    ap.add_argument("--path", default=str(REPO_DEFAULT), help="doctrine_enrichment.json")
    ap.add_argument("--check", action="store_true", help="exit 1 on any defect")
    ap.add_argument("--json", action="store_true", help="emit machine report")
    ap.add_argument("--explain", metavar="ID", help="print extracted atoms for one record")
    args = ap.parse_args(argv)

    path = Path(args.path)
    if args.explain:
        data = json.loads(path.read_text(encoding="utf-8"))
        rec = next((r for r in data.get("records", []) if r.get("id") == args.explain), None)
        if not rec:
            print(f"no record {args.explain}", file=sys.stderr)
            return 2
        print(json.dumps({"id": args.explain, "atoms": {k: sorted(v) for k, v in atoms(rec["formal"]["latex"]).items()}, "audit": audit_record(rec)}, indent=2, ensure_ascii=False))
        return 0

    report = run(path)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(_fmt(report))
    if args.check and report["defective"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
