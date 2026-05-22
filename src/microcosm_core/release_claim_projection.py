from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.schemas import read_json_strict


PASS = "pass"
BLOCKED = "blocked"
CLAIM_CARD_REGISTRY_REL = Path("core/public_claim_cards.json")
ORGAN_EVIDENCE_REGISTRY_REL = Path("core/organ_evidence_classes.json")
README_REL = Path("README.md")
README_BEGIN = "<!-- BEGIN microcosm_release_claim_projection -->"
README_END = "<!-- END microcosm_release_claim_projection -->"

REQUIRED_CARD_FIELDS = (
    "claim_id",
    "audience",
    "plain_english_claim",
    "surface_refs",
    "evidence_class",
    "evidence_receipt_refs",
    "demo_ref",
    "negative_case_refs",
    "authority_ceiling",
    "anti_claim",
    "readme_slot",
    "render_status",
    "promotion_rule",
    "demotion_rule",
)
LOW_EVIDENCE_CLASSES = {"schema_contract", "synthetic_fixture_replay"}
LOW_RENDER_BANNED_PHRASES = (
    "live monitor",
    "live monitoring",
    "live sandbox",
    "live security",
    "detects attacks",
    "prevents attacks",
    "discovers vulnerabilities",
    "proves safety",
    "proves robustness",
    "mechanistic interpretability capability",
    "benchmark performance",
)


def public_root_for(path: str | Path) -> Path:
    resolved = Path(path).resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists() and candidate.name == "microcosm-substrate":
            return candidate
    return resolved


def _as_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str) and item]


def _split_ref(ref: str) -> str:
    return ref.split("::", 1)[0]


def _looks_like_path(ref: str) -> bool:
    if not ref or ref.startswith(("http://", "https://", "microcosm ")):
        return False
    return "/" in ref or ref.endswith((".json", ".jsonl", ".md", ".py", ".toml"))


def _path_exists(root: Path, ref: str) -> bool:
    path_ref = _split_ref(ref)
    return (root / path_ref).exists()


def _finding(code: str, message: str, *, subject_id: str, subject_kind: str) -> dict[str, Any]:
    return {
        "error_code": code,
        "message": message,
        "subject_id": subject_id,
        "subject_kind": subject_kind,
        "body_redacted": True,
    }


def load_claim_registry(root: str | Path) -> dict[str, Any]:
    public_root = public_root_for(root)
    payload = read_json_strict(public_root / CLAIM_CARD_REGISTRY_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{CLAIM_CARD_REGISTRY_REL.as_posix()} must be a JSON object")
    return payload


def load_organ_evidence_registry(root: str | Path) -> dict[str, Any]:
    public_root = public_root_for(root)
    payload = read_json_strict(public_root / ORGAN_EVIDENCE_REGISTRY_REL)
    if not isinstance(payload, dict):
        raise ValueError(f"{ORGAN_EVIDENCE_REGISTRY_REL.as_posix()} must be a JSON object")
    return payload


def _organ_classes(payload: dict[str, Any]) -> dict[str, str]:
    rows = payload.get("organ_evidence_classes", [])
    if not isinstance(rows, list):
        return {}
    classes: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        organ_id = str(row.get("organ_id") or "")
        evidence_class = str(row.get("evidence_class") or "")
        if organ_id and evidence_class:
            classes[organ_id] = evidence_class
    return classes


def _claim_class_profiles(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    profiles = payload.get("allowed_claim_evidence_classes", {})
    return profiles if isinstance(profiles, dict) else {}


def _card_refs(card: dict[str, Any]) -> list[str]:
    refs = []
    for key in ("surface_refs", "evidence_receipt_refs", "negative_case_refs"):
        refs.extend(_as_strings(card.get(key)))
    demo_ref = card.get("demo_ref")
    if isinstance(demo_ref, str) and demo_ref:
        refs.append(demo_ref)
    return refs


def validate_claim_registry(root: str | Path) -> dict[str, Any]:
    public_root = public_root_for(root)
    registry = load_claim_registry(public_root)
    organ_registry = load_organ_evidence_registry(public_root)
    claim_profiles = _claim_class_profiles(registry)
    organ_classes = _organ_classes(organ_registry)
    cards = registry.get("claim_cards", [])
    findings: list[dict[str, Any]] = []

    if registry.get("schema_version") != "microcosm_public_claim_cards_v1":
        findings.append(
            _finding(
                "PUBLIC_CLAIM_REGISTRY_SCHEMA_UNSUPPORTED",
                "Claim-card registry must use microcosm_public_claim_cards_v1.",
                subject_id=str(registry.get("registry_id") or "public_claim_cards"),
                subject_kind="registry",
            )
        )
    if not isinstance(cards, list) or not cards:
        findings.append(
            _finding(
                "PUBLIC_CLAIM_CARD_ROWS_MISSING",
                "Claim-card registry must contain at least one claim_cards row.",
                subject_id=str(registry.get("registry_id") or "public_claim_cards"),
                subject_kind="registry",
            )
        )
        cards = []

    seen: set[str] = set()
    readme_rendered = 0
    evidence_counts: Counter[str] = Counter()
    for index, row in enumerate(cards):
        if not isinstance(row, dict):
            findings.append(
                _finding(
                    "PUBLIC_CLAIM_CARD_NOT_OBJECT",
                    "Claim-card rows must be JSON objects.",
                    subject_id=f"claim_card_{index}",
                    subject_kind="claim_card",
                )
            )
            continue
        claim_id = str(row.get("claim_id") or f"claim_card_{index}")
        if claim_id in seen:
            findings.append(
                _finding(
                    "PUBLIC_CLAIM_CARD_DUPLICATE_ID",
                    "Claim-card ids must be unique.",
                    subject_id=claim_id,
                    subject_kind="claim_card",
                )
            )
        seen.add(claim_id)
        for field in REQUIRED_CARD_FIELDS:
            value = row.get(field)
            if value in (None, "", [], {}):
                findings.append(
                    _finding(
                        "PUBLIC_CLAIM_CARD_FIELD_MISSING",
                        f"Claim card is missing required field {field}.",
                        subject_id=claim_id,
                        subject_kind="claim_card",
                    )
                )

        evidence_class = str(row.get("evidence_class") or "")
        if evidence_class not in claim_profiles:
            findings.append(
                _finding(
                    "PUBLIC_CLAIM_EVIDENCE_CLASS_UNKNOWN",
                    "Claim card references an unknown public evidence class.",
                    subject_id=claim_id,
                    subject_kind="claim_card",
                )
            )
        else:
            evidence_counts[evidence_class] += 1

        if row.get("readme_slot") == "first_screen" and row.get("render_status") == "rendered":
            readme_rendered += 1

        if evidence_class in LOW_EVIDENCE_CLASSES:
            if row.get("render_as_capability") is not False:
                findings.append(
                    _finding(
                        "SCHEMA_ONLY_RENDER_CAPABILITY_FORBIDDEN",
                        "Schema-only or synthetic-fixture claims must declare render_as_capability=false.",
                        subject_id=claim_id,
                        subject_kind="claim_card",
                    )
                )
            searchable = " ".join(
                str(row.get(key) or "")
                for key in ("plain_english_claim", "public_render_label", "promotion_rule")
            ).lower()
            for phrase in LOW_RENDER_BANNED_PHRASES:
                if phrase in searchable:
                    findings.append(
                        _finding(
                            "SCHEMA_ONLY_CAPABILITY_LANGUAGE_FORBIDDEN",
                            f"Schema-only claim uses capability phrase {phrase!r}.",
                            subject_id=claim_id,
                            subject_kind="claim_card",
                        )
                    )

        for organ_id in _as_strings(row.get("organ_evidence_class_refs")):
            if organ_id not in organ_classes:
                findings.append(
                    _finding(
                        "PUBLIC_CLAIM_ORGAN_EVIDENCE_REF_MISSING",
                        "Claim card references an organ without an evidence-class row.",
                        subject_id=f"{claim_id}:{organ_id}",
                        subject_kind="organ_evidence_class_ref",
                    )
                )

        for ref in _card_refs(row):
            if _looks_like_path(ref) and not _path_exists(public_root, ref):
                findings.append(
                    _finding(
                        "PUBLIC_CLAIM_REF_MISSING",
                        "Claim card references a missing public path.",
                        subject_id=f"{claim_id}:{ref}",
                        subject_kind="claim_ref",
                    )
                )

    if readme_rendered == 0:
        findings.append(
            _finding(
                "README_FIRST_SCREEN_CLAIMS_MISSING",
                "At least one rendered first_screen claim card is required.",
                subject_id=str(registry.get("registry_id") or "public_claim_cards"),
                subject_kind="registry",
            )
        )

    return {
        "schema_version": "microcosm_release_claim_projection_validation_v1",
        "created_at": utc_now(),
        "status": PASS if not findings else BLOCKED,
        "registry_ref": CLAIM_CARD_REGISTRY_REL.as_posix(),
        "organ_evidence_registry_ref": ORGAN_EVIDENCE_REGISTRY_REL.as_posix(),
        "claim_card_count": len([row for row in cards if isinstance(row, dict)]),
        "readme_rendered_claim_count": readme_rendered,
        "evidence_class_counts": dict(sorted(evidence_counts.items())),
        "findings": findings,
        "blocking_codes": sorted({str(item.get("error_code")) for item in findings}),
        "authority_ceiling": (
            "claim_projection_validation_only_no_release_provider_private_equivalence_"
            "source_mutation_or_benchmark_authority"
        ),
        "anti_claim": (
            "This validator checks claim-card projection shape, evidence refs, README drift, "
            "and schema-only demotion rules. It does not prove release readiness, live safety "
            "performance, or private-root equivalence."
        ),
    }


def _rendered_cards(registry: dict[str, Any]) -> list[dict[str, Any]]:
    cards = [row for row in registry.get("claim_cards", []) if isinstance(row, dict)]
    return sorted(
        [
            row
            for row in cards
            if row.get("readme_slot") == "first_screen"
            and row.get("render_status") == "rendered"
        ],
        key=lambda row: (int(row.get("display_order") or 0), str(row.get("claim_id") or "")),
    )


def render_readme_section(root: str | Path) -> str:
    registry = load_claim_registry(root)
    commands = _as_strings(registry.get("first_run_commands"))
    command_text = " -> ".join(f"`{command}`" for command in commands)
    cards = _rendered_cards(registry)
    lines = [
        README_BEGIN,
        "## Release Truth Snapshot",
        "",
        (
            "_This block is generated from `core/public_claim_cards.json` by "
            "`python -m microcosm_core.release_claim_projection --root . --check-readme`. "
            "Do not hand-edit inside the markers._"
        ),
        "",
        f"**Audience:** {registry.get('target_audience')}",
        "",
        f"**Run first:** {command_text}",
        "",
        "| First-contact claim | Evidence class | Backing proof | Boundary |",
        "|---|---|---|---|",
    ]
    for card in cards:
        label = str(card.get("public_render_label") or card.get("claim_id"))
        evidence_class = str(card.get("evidence_class") or "")
        proof_ref = str(card.get("demo_ref") or "")
        authority_ceiling = str(card.get("authority_ceiling") or "")
        lines.append(f"| {label} | `{evidence_class}` | `{proof_ref}` | {authority_ceiling} |")
    lines.extend(
        [
            "",
            (
                "**Demotion rule:** schema-only replay organs render as synthetic "
                "claim-schema fixtures unless a stronger `evidence_class` and receipt-backed "
                "demo are present."
            ),
            README_END,
        ]
    )
    return "\n".join(lines)


def readme_projection_status(root: str | Path) -> dict[str, Any]:
    public_root = public_root_for(root)
    readme_path = public_root / README_REL
    expected = render_readme_section(public_root)
    text = readme_path.read_text(encoding="utf-8")
    if README_BEGIN not in text or README_END not in text:
        return {
            "status": BLOCKED,
            "readme_ref": README_REL.as_posix(),
            "markers_present": False,
            "matches_projection": False,
            "findings": [
                _finding(
                    "README_PROJECTION_MARKERS_MISSING",
                    "README must contain the release claim projection markers.",
                    subject_id=README_REL.as_posix(),
                    subject_kind="readme",
                )
            ],
        }
    start = text.index(README_BEGIN)
    end = text.index(README_END, start) + len(README_END)
    actual = text[start:end]
    matches = actual == expected
    findings = []
    if not matches:
        findings.append(
            _finding(
                "README_PROJECTION_DRIFT",
                "README release truth snapshot does not match core/public_claim_cards.json.",
                subject_id=README_REL.as_posix(),
                subject_kind="readme",
            )
        )
    return {
        "status": PASS if matches else BLOCKED,
        "readme_ref": README_REL.as_posix(),
        "markers_present": True,
        "matches_projection": matches,
        "expected_line_count": len(expected.splitlines()),
        "actual_line_count": len(actual.splitlines()),
        "findings": findings,
    }


def write_readme_projection(root: str | Path) -> None:
    public_root = public_root_for(root)
    readme_path = public_root / README_REL
    expected = render_readme_section(public_root)
    text = readme_path.read_text(encoding="utf-8")
    if README_BEGIN not in text or README_END not in text:
        insertion = expected + "\n\n"
        readme_path.write_text(insertion + text, encoding="utf-8")
        return
    start = text.index(README_BEGIN)
    end = text.index(README_END, start) + len(README_END)
    readme_path.write_text(text[:start] + expected + text[end:], encoding="utf-8")


def build_receipt(root: str | Path, *, check_readme: bool) -> dict[str, Any]:
    validation = validate_claim_registry(root)
    readme_status = readme_projection_status(root) if check_readme else {
        "status": "not_checked",
        "readme_ref": README_REL.as_posix(),
    }
    status = PASS if validation["status"] == PASS and readme_status["status"] in {PASS, "not_checked"} else BLOCKED
    return {
        "schema_version": "microcosm_release_claim_projection_receipt_v1",
        "created_at": utc_now(),
        "status": status,
        "claim_registry": validation,
        "readme_projection": readme_status,
        "receipt_paths": [],
        "authority_ceiling": validation["authority_ceiling"],
        "anti_claim": validation["anti_claim"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m microcosm_core.release_claim_projection")
    parser.add_argument("--root", default=".")
    parser.add_argument("--out")
    parser.add_argument("--check-readme", action="store_true")
    parser.add_argument("--write-readme", action="store_true")
    args = parser.parse_args(argv)

    if args.write_readme:
        write_readme_projection(args.root)
    receipt = build_receipt(args.root, check_readme=args.check_readme)
    if args.out:
        out_path = public_root_for(args.root) / args.out
        receipt["receipt_paths"] = [str(Path(args.out))]
        write_json_atomic(out_path, receipt)
    else:
        import json

        print(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
