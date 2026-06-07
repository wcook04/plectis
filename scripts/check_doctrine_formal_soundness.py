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
    """Collapse spacing so symbol/formula substring matching is robust."""
    s = _SPACE_MACRO_RE.sub("", str(s or ""))
    return re.sub(r"\s+", "", s)


def atoms(latex: str) -> dict[str, set[str]]:
    """Walk a bounded-LaTeX string and bucket the symbols it references.

    Returns sets: free_vars (single Latin letters in math italic), greek
    (greek-letter macros used as variables), named_ops (content operators, as
    the full \\mathrm{name} token), verdicts (\\mathsf{...} etc.), structural
    (\\mathrm{else}-style connectors), and connectives (everything common).
    Subscript / superscript *arguments* are treated as modifiers of the base
    symbol, not as independent free variables.
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
        # consume the argument of a _ or ^ so its inner letters are not counted
        # as free variables (they modify the preceding base symbol).
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
    """Return {dangling, undefined_vars, undefined_ops, clean} for one record."""
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
