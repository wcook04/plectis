from __future__ import annotations

import importlib.util
import io
import json
import re
import sys
import tempfile
import types
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    main_for_spec,
    public_root_for_path,
    run_crown_jewel_organ,
    validate_source_manifest,
)
from microcosm_core.schemas import read_json_strict


ORGAN_ID = "batch12_release_claim_language_gate"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"

EXPECTED_NEGATIVE_CASES = {
    "affirmative_open_source_production_ready_blocks": (
        "BATCH12_RELEASE_CLAIM_ACTIVE_BLOCKER",
    ),
    "assert_clear_returns_exit_2": ("BATCH12_RELEASE_CLAIM_ASSERT_CLEAR_EXIT_2",),
    "private_control_plane_public_reader_blocks": (
        "BATCH12_RELEASE_PRIVATE_CONTROL_PLANE_LEAK",
    ),
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch12_release_claim_language_gate_lexical_scan_only",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "nlp_semantic_truth": False,
    "whole_system_correctness_claim": False,
    "portability_gate_passed": False,
    "secret_scan_passed": False,
}

ANTI_CLAIM = (
    "Batch 12 release claim-language gate validation executes the copied macro "
    "lexical gate over public-safe markdown fixtures. It is not release "
    "approval, publication authority, semantic NLP truth, complete secret "
    "detection, portability proof, or whole-system correctness."
)

SOURCE_REQUIRED_ANCHORS = {
    "tools/meta/dissemination/release_claim_language_gate.py": (
        "RISKY_PHRASES",
        "NEGATIVE_CONTEXT_MARKERS",
        "META_FORBIDDEN_CONTEXT_MARKERS",
        "private_control_plane_leak",
        "def _classify_hit",
        "def build_gate",
    )
}

PUBLIC_FALLBACK_RISKY_PHRASES = (
    {
        "id": "release_ready",
        "family": "claim_overreach",
        "pattern": r"\brelease[- ]ready\b|\bready to publish\b|\bpublication[- ]ready\b|\bpublish[- ]ready\b",
    },
    {
        "id": "publicly_released",
        "family": "claim_overreach",
        "pattern": r"\bpublicly released\b|\breleased publicly\b",
    },
    {
        "id": "source_available",
        "family": "claim_overreach",
        "pattern": r"\bsource[- ]available\b",
    },
    {
        "id": "open_source",
        "family": "claim_overreach",
        "pattern": r"\bopen[- ]source\b|\bopen source\b",
    },
    {
        "id": "production_ready",
        "family": "claim_overreach",
        "pattern": r"\bproduction[- ]ready\b",
    },
    {
        "id": "release_authorization_disclaimer",
        "family": "private_control_plane_leak",
        "pattern": (
            r"\b(?:does\s+not|doesn't|do\s+not|don't|cannot|not)\s+"
            r"(?:authorize|authorise|approve|grant)\s+"
            r"(?:a\s+)?(?:public\s+)?(?:release|publication|publishing|hosting|recipient\s+sends?)\b"
        ),
    },
    {
        "id": "release_authority_surface",
        "family": "private_control_plane_leak",
        "pattern": (
            r"\b(?:release|publication|publishing|hosting|recipient\s+sends?)\s+"
            r"(?:authority|authorization|authorisation|approval|gate|owner|decision)\b"
        ),
    },
)

PUBLIC_FALLBACK_NEGATIVE_CONTEXT_MARKERS = (
    "not ",
    "not-",
    "do not claim",
    "forbidden",
    "blocked",
    "omitted",
    "negative context",
)

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 12 release claim-language gate",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=("release_gate_fixture.json",),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "examples/batch12_release_claim_language_gate/"
        "exported_batch12_release_claim_language_gate_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _load_json(path: Path) -> dict[str, Any]:
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else {}


def _blocked_exercise(findings: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "status": "blocked",
        "mechanism_count": 1,
        "mechanisms": [
            {
                "mechanism_id": "release_claim_language_gate",
                "source_symbols": ["_classify_hit", "build_gate", "main --assert-clear"],
                "status": "blocked",
                "positive_boundary_clear": False,
                "negative_cases": [],
            }
        ],
        "safe_gate_summary": None,
        "active_gate_summary": None,
        "computed_negative_case_count": 0,
        "error_codes": sorted(
            {
                str(row.get("error_code"))
                for row in findings
                if row.get("error_code")
            }
        ),
        "findings": findings,
    }


def _load_fixture(input_dir: Path, findings: list[dict[str, Any]]) -> dict[str, Any]:
    path = input_dir / "release_gate_fixture.json"
    if not path.is_file():
        findings.append(
            finding(
                "BATCH12_RELEASE_FIXTURE_MISSING",
                "release_gate_fixture.json is required.",
                subject_id=path.name,
            )
        )
        return {}
    try:
        payload = read_json_strict(path)
    except Exception as exc:
        findings.append(
            finding(
                "BATCH12_RELEASE_FIXTURE_INVALID_JSON",
                "Release claim-language fixture must be strict JSON with unique keys.",
                subject_id=path.name,
                observed=f"{type(exc).__name__}: {exc}",
            )
        )
        return {}
    if not isinstance(payload, dict):
        findings.append(
            finding(
                "BATCH12_RELEASE_FIXTURE_NOT_OBJECT",
                "Release claim-language fixture must be a JSON object.",
                subject_id=path.name,
                observed=type(payload).__name__,
            )
        )
        return {}
    return payload


def _source_target(source_manifest: Mapping[str, Any], source_ref: str) -> Path:
    manifest = Path(str(source_manifest.get("source_manifest_path") or ""))
    if not manifest.is_file():
        raise FileNotFoundError("source manifest path unavailable")
    manifest_payload = _load_json(manifest)
    for row in manifest_payload.get("modules", []):
        if isinstance(row, dict) and row.get("source_ref") == source_ref:
            return manifest.parent / str(row.get("path") or "")
    raise FileNotFoundError(source_ref)


def _load_source_module(source_manifest: Mapping[str, Any]) -> Any:
    if _source_module_public_stubbed(source_manifest):
        return _PublicFallbackReleaseClaimGate
    target = _source_target(
        source_manifest,
        "tools/meta/dissemination/release_claim_language_gate.py",
    )
    spec = importlib.util.spec_from_file_location(
        "batch12_release_claim_language_gate_source",
        target,
    )
    if spec is None or spec.loader is None:
        raise ImportError(str(target))
    module = importlib.util.module_from_spec(spec)
    sentinel = object()
    previous_yaml = sys.modules.get("yaml", sentinel)
    if previous_yaml is sentinel:
        yaml_stub = types.ModuleType("yaml")

        def safe_load(text: str) -> dict[str, Any]:
            entries = []
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("- path:"):
                    entries.append({"path": stripped.split(":", 1)[1].strip()})
            return {"include": {"documentation": {"entries": entries}}}

        yaml_stub.safe_load = safe_load
        sys.modules["yaml"] = yaml_stub
    try:
        spec.loader.exec_module(module)
    finally:
        if previous_yaml is sentinel:
            sys.modules.pop("yaml", None)
        else:
            sys.modules["yaml"] = previous_yaml
    return module


def _source_module_public_stubbed(source_manifest: Mapping[str, Any]) -> bool:
    manifest = Path(str(source_manifest.get("source_manifest_path") or ""))
    if not manifest.is_file():
        return False
    manifest_payload = _load_json(manifest)
    omissions = manifest_payload.get("release_substitution_omissions", [])
    return (
        not manifest_payload.get("modules")
        and isinstance(omissions, list)
        and any(
            isinstance(row, Mapping)
            and row.get("source_ref")
            == "tools/meta/dissemination/release_claim_language_gate.py"
            and (
                row.get("release_substitution", {}).get("substitution")
                if isinstance(row.get("release_substitution"), Mapping)
                else None
            )
            == "public_safe_stub"
            for row in omissions
        )
    )


class _PublicFallbackReleaseClaimGate:
    """Public replacement used only when the private macro body is stubbed."""

    @staticmethod
    def _manifest_entries(repo_root: Path) -> list[str]:
        manifest = repo_root / "publication_manifest.yaml"
        if not manifest.is_file():
            return []
        entries: list[str] = []
        for line in manifest.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("- path:"):
                entries.append(stripped.split(":", 1)[1].strip())
        return entries

    @staticmethod
    def _classify(line: str, *, family: str) -> tuple[str, str]:
        normalized = line.lower()
        if family == "private_control_plane_leak":
            return (
                "active_claim_blocker",
                "public reader copy must not expose release authorization control-plane language",
            )
        if any(marker in normalized for marker in PUBLIC_FALLBACK_NEGATIVE_CONTEXT_MARKERS):
            return (
                "boundary_or_negative_context",
                "line marks the phrase as forbidden, blocked, omitted, or explicitly not claimed",
            )
        return "active_claim_blocker", "public reader copy asserts release status"

    @classmethod
    def build_gate(cls, repo_root: Path) -> dict[str, Any]:
        root = Path(repo_root)
        hits: list[dict[str, Any]] = []
        for rel in cls._manifest_entries(root):
            path = root / rel
            if not path.is_file():
                continue
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for phrase in PUBLIC_FALLBACK_RISKY_PHRASES:
                    if not re.search(str(phrase["pattern"]), line, flags=re.IGNORECASE):
                        continue
                    classification, reason = cls._classify(
                        line,
                        family=str(phrase["family"]),
                    )
                    hits.append(
                        {
                            "path": rel,
                            "line_number": line_number,
                            "phrase_id": phrase["id"],
                            "phrase_family": phrase["family"],
                            "classification": classification,
                            "reason": reason,
                            "body_in_receipt": False,
                        }
                    )
        active_count = sum(
            1 for hit in hits if hit["classification"] == "active_claim_blocker"
        )
        boundary_count = sum(
            1 for hit in hits if hit["classification"] == "boundary_or_negative_context"
        )
        status = (
            "active_claim_blocked"
            if active_count
            else "clear_boundary_only"
            if boundary_count
            else "clear"
        )
        return {
            "schema_version": "public_fallback_release_claim_language_gate_v1",
            "status": status,
            "ok": active_count == 0,
            "summary": {
                "active_claim_blocker_count": active_count,
                "boundary_or_negative_context_count": boundary_count,
                "claim_surface_count": len(cls._manifest_entries(root)),
            },
            "hits": hits,
            "public_stub_fallback": True,
            "body_in_receipt": False,
        }

    @classmethod
    def main(cls, argv: list[str] | None = None) -> int:
        args = list(argv or [])
        repo_root = Path(".")
        output: Path | None = None
        assert_clear = False
        idx = 0
        while idx < len(args):
            arg = args[idx]
            if arg == "--repo-root" and idx + 1 < len(args):
                repo_root = Path(args[idx + 1])
                idx += 2
            elif arg == "--output" and idx + 1 < len(args):
                output = Path(args[idx + 1])
                idx += 2
            elif arg == "--assert-clear":
                assert_clear = True
                idx += 1
            else:
                idx += 1
        payload = cls.build_gate(repo_root)
        if output is not None:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        print(
            json.dumps(
                {"ok": payload["ok"], "status": payload["status"]},
                sort_keys=True,
            )
        )
        return 2 if assert_clear and not payload["ok"] else 0


def _fixture_doc_name(
    fixture: Mapping[str, Any],
    key: str,
    default: str,
    findings: list[dict[str, Any]],
) -> str | None:
    name = str(fixture.get(key) or default)
    if any(ord(char) < 32 or ord(char) == 127 for char in name):
        findings.append(
            finding(
                "BATCH12_RELEASE_FIXTURE_PATH_CONTROL_CHAR",
                "Fixture-selected documentation file names must not contain control characters.",
                subject_id=key,
                observed=repr(name),
            )
        )
        return None
    if (
        not name
        or name in {".", ".."}
        or "/" in name
        or "\\" in name
        or Path(name).name != name
    ):
        findings.append(
            finding(
                "BATCH12_RELEASE_FIXTURE_PATH_UNSAFE",
                "Fixture-selected documentation file names must stay inside docs/.",
                subject_id=key,
                observed=name,
            )
        )
        return None
    return name


def _write_gate_fixture(
    root: Path,
    fixture: Mapping[str, Any],
    *,
    active: bool,
    findings: list[dict[str, Any]],
) -> bool:
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    safe_name = _fixture_doc_name(fixture, "safe_file", "safe_boundary.md", findings)
    active_name = _fixture_doc_name(
        fixture,
        "active_file",
        "affirmative_overclaim.md",
        findings,
    )
    if safe_name is None or active_name is None:
        return False
    if active and safe_name == active_name:
        findings.append(
            finding(
                "BATCH12_RELEASE_FIXTURE_DUPLICATE_DOC_NAME",
                "Active release-claim fixture text must not overwrite the safe boundary document.",
                subject_id="active_file",
                observed=active_name,
            )
        )
        return False
    (docs / safe_name).write_text(str(fixture.get("safe_text") or ""), encoding="utf-8")
    if active:
        (docs / active_name).write_text(
            str(fixture.get("active_text") or ""),
            encoding="utf-8",
        )
    entries = [{"path": f"docs/{safe_name}"}]
    if active:
        entries.append({"path": f"docs/{active_name}"})
    manifest = {
        "include": {
            "documentation": {
                "entries": entries,
            }
        }
    }
    (root / "publication_manifest.yaml").write_text(
        "include:\n  documentation:\n    entries:\n"
        + "".join(f"      - path: {row['path']}\n" for row in entries),
        encoding="utf-8",
    )
    return True


def _run_main_assert_clear(module: Any, root: Path) -> tuple[int, dict[str, Any]]:
    out = root / "release_claim_language_gate_v0.json"
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = module.main(
            [
                "--repo-root",
                str(root),
                "--output",
                str(out),
                "--assert-clear",
            ]
        )
    line = buffer.getvalue().strip()
    payload = json.loads(line) if line else {}
    return code, payload


def _active_phrase_ids(gate: Mapping[str, Any]) -> list[str]:
    return sorted(
        {
            str(hit.get("phrase_id"))
            for hit in gate.get("hits", [])
            if isinstance(hit, Mapping)
            and hit.get("classification") == "active_claim_blocker"
            and hit.get("phrase_id")
        }
    )


def _gate_status(gate: Mapping[str, Any]) -> str:
    return str(gate.get("status") or "")


def _first_screen_claim_rows(
    *,
    safe_gate: Mapping[str, Any],
    active_gate: Mapping[str, Any],
    publication_gate: Mapping[str, Any],
    control_plane_gate: Mapping[str, Any],
    computed_cases: list[dict[str, Any]],
    positive_boundary_clear: bool,
) -> list[dict[str, Any]]:
    case_lookup = {
        str(row.get("case_id")): bool(row.get("computed"))
        for row in computed_cases
        if isinstance(row, Mapping)
    }
    source_route = "tools/meta/dissemination/release_claim_language_gate.py::_classify_hit/build_gate"
    ceiling = AUTHORITY_CEILING["authority_ceiling"]
    return [
        {
            "row_id": "allowed_boundary_language_clears",
            "source_route": source_route,
            "fixture_role": "safe_boundary_text",
            "expected_status": "clear_boundary_only",
            "observed_status": _gate_status(safe_gate),
            "evaluator_signal": positive_boundary_clear,
            "observed_active_phrase_ids": _active_phrase_ids(safe_gate),
            "allowed_wording": "boundary-only no-release language is allowed as negative context",
            "blocked_wording": "release_ready/source_available/open_source/production_ready phrase ids",
            "downgrade_sentence": "This is lexical claim-language evidence, not release approval.",
            "authority_ceiling": ceiling,
        },
        {
            "row_id": "open_source_production_ready_blocks",
            "source_route": source_route,
            "fixture_role": "active_overclaim_text",
            "expected_status": "active_claim_blocked",
            "observed_status": _gate_status(active_gate),
            "evaluator_signal": case_lookup.get("affirmative_open_source_production_ready_blocks", False),
            "observed_active_phrase_ids": _active_phrase_ids(active_gate),
            "allowed_wording": "public-safe fixture text may describe the boundary",
            "blocked_wording": "open_source or production_ready phrase ids",
            "downgrade_sentence": "A blocked active phrase proves a claim ceiling, not a public release state.",
            "authority_ceiling": ceiling,
        },
        {
            "row_id": "publication_overclaim_blocks",
            "source_route": source_route,
            "fixture_role": "publication_overclaim_text",
            "expected_status": "active_claim_blocked",
            "observed_status": _gate_status(publication_gate),
            "evaluator_signal": _gate_status(publication_gate) == "active_claim_blocked",
            "observed_active_phrase_ids": _active_phrase_ids(publication_gate),
            "allowed_wording": "publication wording must stay under the separate release gate",
            "blocked_wording": "release_ready/publicly_released/source_available phrase ids",
            "downgrade_sentence": "The gate catches overclaim language; it does not decide publication.",
            "authority_ceiling": ceiling,
        },
        {
            "row_id": "private_control_plane_public_reader_blocks",
            "source_route": source_route,
            "fixture_role": "private_control_plane_leak_text",
            "expected_status": "active_claim_blocked",
            "observed_status": _gate_status(control_plane_gate),
            "evaluator_signal": case_lookup.get("private_control_plane_public_reader_blocks", False),
            "observed_active_phrase_ids": _active_phrase_ids(control_plane_gate),
            "allowed_wording": "outbound copy should omit private control-plane authority language",
            "blocked_wording": "release authority, release gate, publication owner",
            "downgrade_sentence": "The public reader sees a redacted boundary, not the private control plane.",
            "authority_ceiling": ceiling,
        },
    ]


def _evaluate(input_dir: Path, _public_root: Path, source_manifest: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    fixture = _load_fixture(input_dir, findings)
    if findings:
        return _blocked_exercise(findings)
    try:
        module = _load_source_module(source_manifest)
    except Exception as exc:
        findings.append(
            finding(
                "BATCH12_RELEASE_SOURCE_MODULE_UNAVAILABLE",
                "Release claim-language copied source module must be loadable before exercise.",
                observed=f"{type(exc).__name__}: {exc}",
            )
        )
        return _blocked_exercise(findings)
    source_module_substitution_fallback = module is _PublicFallbackReleaseClaimGate
    with tempfile.TemporaryDirectory(prefix="batch12-release-gate-") as tmp:
        safe_root = Path(tmp) / "safe"
        safe_root.mkdir(parents=True)
        safe_fixture_written = _write_gate_fixture(
            safe_root,
            fixture,
            active=False,
            findings=findings,
        )
        safe_gate = module.build_gate(safe_root) if safe_fixture_written else {}
        active_root = Path(tmp) / "active"
        active_root.mkdir(parents=True)
        active_fixture_written = _write_gate_fixture(
            active_root,
            fixture,
            active=True,
            findings=findings,
        )
        active_gate = module.build_gate(active_root) if active_fixture_written else {}
        if active_fixture_written:
            assert_clear_code, assert_clear_payload = _run_main_assert_clear(module, active_root)
        else:
            assert_clear_code, assert_clear_payload = -1, {}
        publication_fixture = dict(fixture)
        publication_fixture["active_file"] = "publication_overclaim.md"
        publication_fixture["active_text"] = str(
            fixture.get("publication_overclaim_text")
            or "This microcosm is publication-ready, publicly released, and source-available.\n"
        )
        publication_root = Path(tmp) / "publication"
        publication_root.mkdir(parents=True)
        publication_fixture_written = _write_gate_fixture(
            publication_root,
            publication_fixture,
            active=True,
            findings=findings,
        )
        publication_gate = (
            module.build_gate(publication_root) if publication_fixture_written else {}
        )
        control_plane_fixture = dict(fixture)
        control_plane_fixture["active_file"] = "private_control_plane_leak.md"
        control_plane_fixture["active_text"] = str(
            fixture.get("private_control_plane_leak_text")
            or (
                "This public page does not authorize release; release authority "
                "remains with the dissemination owner.\n"
            )
        )
        control_plane_root = Path(tmp) / "private_control_plane"
        control_plane_root.mkdir(parents=True)
        control_plane_fixture_written = _write_gate_fixture(
            control_plane_root,
            control_plane_fixture,
            active=True,
            findings=findings,
        )
        control_plane_gate = (
            module.build_gate(control_plane_root) if control_plane_fixture_written else {}
        )

    if findings:
        blocked = _blocked_exercise(findings)
        blocked["safe_gate_summary"] = safe_gate.get("summary")
        blocked["active_gate_summary"] = active_gate.get("summary")
        return blocked

    boundary_hits = [
        hit
        for hit in safe_gate.get("hits", [])
        if hit.get("classification") == "boundary_or_negative_context"
    ]
    active_hits = [
        hit
        for hit in active_gate.get("hits", [])
        if hit.get("classification") == "active_claim_blocker"
    ]
    computed_cases = [
        {
            "case_id": "affirmative_open_source_production_ready_blocks",
            "computed": active_gate.get("status") == "active_claim_blocked"
            and any(hit.get("phrase_id") == "open_source" for hit in active_hits)
            and any(hit.get("phrase_id") == "production_ready" for hit in active_hits),
            "observed": {
                "status": active_gate.get("status"),
                "active_phrase_ids": sorted({str(hit.get("phrase_id")) for hit in active_hits}),
            },
        },
        {
            "case_id": "assert_clear_returns_exit_2",
            "computed": assert_clear_code == 2 and assert_clear_payload.get("ok") is False,
            "observed": {"exit_code": assert_clear_code, "payload": assert_clear_payload},
        },
        {
            "case_id": "private_control_plane_public_reader_blocks",
            "computed": control_plane_gate.get("status") == "active_claim_blocked"
            and any(
                hit.get("phrase_family") == "private_control_plane_leak"
                for hit in control_plane_gate.get("hits", [])
                if isinstance(hit, Mapping)
                and hit.get("classification") == "active_claim_blocker"
            ),
            "observed": {
                "status": control_plane_gate.get("status"),
                "active_phrase_ids": _active_phrase_ids(control_plane_gate),
            },
        },
    ]
    release_claim_perturbation = {
        "probe_id": "publication_source_availability_overclaim_text_perturbation",
        "body_in_receipt": False,
        "safe_status": _gate_status(safe_gate),
        "active_status": _gate_status(active_gate),
        "publication_overclaim_status": _gate_status(publication_gate),
        "private_control_plane_status": _gate_status(control_plane_gate),
        "active_phrase_ids": _active_phrase_ids(active_gate),
        "publication_overclaim_phrase_ids": _active_phrase_ids(publication_gate),
        "private_control_plane_phrase_ids": _active_phrase_ids(control_plane_gate),
        "verdict_moved": _gate_status(safe_gate) == "clear_boundary_only"
        and _gate_status(publication_gate) == "active_claim_blocked",
        "private_control_plane_leak_blocked": (
            _gate_status(control_plane_gate) == "active_claim_blocked"
        ),
        "not_release_authority": True,
    }
    positive_boundary_clear = (
        safe_gate.get("status") == "clear_boundary_only"
        and bool(boundary_hits)
        and not safe_gate.get("summary", {}).get("active_claim_blocker_count")
    )
    first_screen_claim_rows = _first_screen_claim_rows(
        safe_gate=safe_gate,
        active_gate=active_gate,
        publication_gate=publication_gate,
        control_plane_gate=control_plane_gate,
        computed_cases=computed_cases,
        positive_boundary_clear=positive_boundary_clear,
    )
    if not positive_boundary_clear:
        findings.append(
            finding(
                "BATCH12_RELEASE_BOUNDARY_POSITIVE_NOT_CLEAR",
                "Boundary-only release language should clear as negative context.",
                observed=safe_gate.get("status"),
            )
        )
    for row in computed_cases:
        if not row["computed"]:
            findings.append(
                finding(
                    "BATCH12_RELEASE_CLAIM_CASE_NOT_OBSERVED",
                    "Release claim-language gate did not compute the expected case.",
                    case_id=str(row["case_id"]),
                    observed=row.get("observed"),
                )
            )
    return {
        "status": "pass" if not findings else "blocked",
        "mechanism_count": 1,
        "mechanisms": [
            {
                "mechanism_id": "release_claim_language_gate",
                "source_symbols": ["_classify_hit", "build_gate", "main --assert-clear"],
                "status": "pass" if not findings else "blocked",
                "positive_boundary_clear": positive_boundary_clear,
                "negative_cases": computed_cases,
            }
        ],
        "safe_gate_summary": safe_gate.get("summary"),
        "active_gate_summary": active_gate.get("summary"),
        "release_claim_perturbation": release_claim_perturbation,
        "first_screen_claim_rows": first_screen_claim_rows,
        "source_module_substitution_fallback": source_module_substitution_fallback,
        "computed_negative_case_count": sum(1 for row in computed_cases if row["computed"]),
        "error_codes": [
            code
            for case_codes in EXPECTED_NEGATIVE_CASES.values()
            for code in case_codes
        ],
        "findings": findings,
    }


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    input_path = Path(input_dir)
    public_root = public_root_for_path(input_path)
    source_manifest = validate_source_manifest(input_path, SPEC, public_root=public_root)
    exercise = _evaluate(input_path, public_root, source_manifest)
    findings = [
        *source_manifest.get("findings", []),
        *exercise.get("findings", []),
    ]
    if findings:
        return {
            "status": "blocked",
            "case_id": case_id,
            "error_codes": sorted(
                {
                    str(row.get("error_code"))
                    for row in findings
                    if row.get("error_code")
                }
            ),
            "body_in_receipt": False,
        }
    negative_cases = [
        row
        for mechanism in exercise.get("mechanisms", [])
        if isinstance(mechanism, Mapping)
        for row in mechanism.get("negative_cases", [])
        if isinstance(row, Mapping)
    ]
    for row in negative_cases:
        if row.get("case_id") == case_id and row.get("computed") is True:
            return {
                "status": "blocked",
                "case_id": case_id,
                "error_codes": list(expected_codes),
                "derived_from": "release_claim_language_gate_macro_execution",
                "observed": row.get("observed"),
                "body_in_receipt": False,
            }
    return {
        "status": "pass",
        "case_id": case_id,
        "error_codes": [],
        "derived_from": "release_claim_language_gate_macro_execution",
        "observed": {"computed_negative_case_ids": []},
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch12_release_claim_language_gate_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    return card_for_result(SPEC, result)


def main(argv: list[str] | None = None) -> int:
    return main_for_spec(
        SPEC,
        argv,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
        bundle_action="run-release-claim-language-gate-bundle",
    )


if __name__ == "__main__":
    raise SystemExit(main())
