from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


class SmokeCheckError(Exception):
    """Raised when a smoke receipt is missing or contradicts the public floor."""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SmokeCheckError(f"{path.name}: missing required smoke receipt")
    if path.stat().st_size == 0:
        raise SmokeCheckError(
            f"{path.name}: file is empty (0 bytes) — likely a stale or partial "
            "smoke run; re-run `make smoke`"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SmokeCheckError(f"{path.name}: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SmokeCheckError(f"{path.name}: expected a JSON object")
    return payload


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise SmokeCheckError(f"{path.name}: missing required smoke receipt")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise SmokeCheckError(f"{path.name}: empty smoke receipt")
    return text


def _expect_status(payload: dict[str, Any], *, name: str, status: str = "pass") -> None:
    actual = payload.get("status")
    if actual != status:
        raise SmokeCheckError(f"{name}: expected status {status!r}, got {actual!r}")


def _expect_object(payload: dict[str, Any], *, name: str, key: str) -> dict[str, Any]:
    actual = payload.get(key)
    if not isinstance(actual, dict):
        raise SmokeCheckError(f"{name}: missing {key} object")
    return actual


def _expect_false(
    payload: dict[str, Any],
    *,
    name: str,
    key: str,
    source: str | None = None,
) -> None:
    actual = payload.get(key)
    if actual is not False:
        label = f"{source}.{key}" if source else key
        raise SmokeCheckError(f"{name}: expected {label} false, got {actual!r}")


def _expect_nested_false(
    payload: dict[str, Any],
    *,
    name: str,
    object_key: str,
    key: str,
) -> None:
    parent = _expect_object(payload, name=name, key=object_key)
    actual = parent.get(key)
    if actual is not False:
        raise SmokeCheckError(
            f"{name}: expected {object_key}.{key} false, got {actual!r}",
        )


def _expect_authority_false(
    payload: dict[str, Any],
    *,
    name: str,
    key: str,
) -> None:
    authority_ceiling = payload.get("authority_ceiling")
    if not isinstance(authority_ceiling, dict):
        raise SmokeCheckError(f"{name}: missing authority_ceiling object")
    actual = authority_ceiling.get(key)
    if actual is not False:
        raise SmokeCheckError(
            f"{name}: expected authority_ceiling.{key} false, got {actual!r}",
        )


def _expect_nonnegative_int(
    payload: dict[str, Any],
    *,
    name: str,
    key: str,
) -> int:
    actual = payload.get(key)
    if not isinstance(actual, int) or isinstance(actual, bool) or actual < 0:
        raise SmokeCheckError(f"{name}: expected nonnegative integer {key}, got {actual!r}")
    return actual


def _expect_positive_surface_count(
    payload: dict[str, Any],
    *,
    name: str,
    key: str,
) -> int:
    surface_counts = payload.get("surface_counts")
    if not isinstance(surface_counts, dict):
        raise SmokeCheckError(f"{name}: missing surface_counts object")
    actual = surface_counts.get(key)
    if not isinstance(actual, int) or isinstance(actual, bool) or actual <= 0:
        raise SmokeCheckError(
            f"{name}: expected positive surface_counts.{key}, got {actual!r}",
        )
    return actual


def _expect_surface_count(
    payload: dict[str, Any],
    *,
    name: str,
    key: str,
    expected: int,
) -> int:
    surface_counts = payload.get("surface_counts")
    if not isinstance(surface_counts, dict):
        raise SmokeCheckError(f"{name}: missing surface_counts object")
    actual = surface_counts.get(key)
    if actual != expected:
        raise SmokeCheckError(
            f"{name}: expected surface_counts.{key} {expected}, got {actual!r}",
        )
    return expected


def _surface_count(payload: dict[str, Any], *, name: str, key: str) -> int:
    surface_counts = payload.get("surface_counts")
    if not isinstance(surface_counts, dict):
        raise SmokeCheckError(f"{name}: missing surface_counts object")
    actual = surface_counts.get(key)
    if not isinstance(actual, int) or isinstance(actual, bool) or actual < 0:
        raise SmokeCheckError(
            f"{name}: expected nonnegative integer surface_counts.{key}, got {actual!r}",
        )
    return actual


def _preview_count(payload: dict[str, Any], *, name: str, key: str) -> int:
    preview = payload.get(key)
    if not isinstance(preview, dict):
        raise SmokeCheckError(f"{name}: missing {key} object")
    actual = preview.get("count")
    if not isinstance(actual, int) or isinstance(actual, bool) or actual < 0:
        raise SmokeCheckError(f"{name}: expected nonnegative integer {key}.count, got {actual!r}")
    return actual


def _workingness_import_signature(payload: dict[str, Any], *, name: str) -> dict[str, Any]:
    preview = payload.get("source_body_import_exception_preview")
    if not isinstance(preview, dict):
        raise SmokeCheckError(
            f"{name}: missing source_body_import_exception_preview object",
        )
    status = preview.get("status")
    if not isinstance(status, str) or not status:
        raise SmokeCheckError(
            f"{name}: expected source_body_import_exception_preview.status string, got {status!r}",
        )
    return {
        "source_body_import_exception_count": _preview_count(
            payload,
            name=name,
            key="source_body_import_exception_preview",
        ),
        "source_body_import_exception_status": status,
        "rows_with_source_body_imports": _surface_count(
            payload,
            name=name,
            key="rows_with_source_body_imports",
        ),
        "source_open_body_material_count": _surface_count(
            payload,
            name=name,
            key="source_open_body_material_count",
        ),
    }


def _live_workingness_card(root: Path = MICROCOSM_ROOT) -> dict[str, Any]:
    env = os.environ.copy()
    src_path = str(root / "src")
    env["PYTHONPATH"] = (
        src_path
        if not env.get("PYTHONPATH")
        else os.pathsep.join([src_path, env["PYTHONPATH"]])
    )
    result = subprocess.run(
        [sys.executable, "-m", "microcosm_core", "workingness", "--card"],
        cwd=root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise SmokeCheckError(
            "workingness-card.json: could not regenerate live workingness card "
            f"for freshness comparison: {stderr}",
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SmokeCheckError(
            "workingness-card.json: live workingness command emitted invalid JSON",
        ) from exc
    if not isinstance(payload, dict):
        raise SmokeCheckError(
            "workingness-card.json: live workingness command did not emit a JSON object",
        )
    return payload


def _expect_workingness_import_signature_fresh(workingness: dict[str, Any]) -> dict[str, Any]:
    receipt_signature = _workingness_import_signature(
        workingness,
        name="workingness-card.json",
    )
    live_signature = _workingness_import_signature(
        _live_workingness_card(),
        name="live workingness --card",
    )
    if receipt_signature != live_signature:
        raise SmokeCheckError(
            "workingness-card.json: stale source-body import signature; "
            f"receipt {json.dumps(receipt_signature, sort_keys=True)}, "
            f"live {json.dumps(live_signature, sort_keys=True)}; re-run `make smoke`",
    )
    return receipt_signature


def _expect_proof_lab_status_cache_bound(status: dict[str, Any]) -> str:
    front_door = _expect_object(status, name="status-card.json", key="front_door")
    proof_lab = front_door.get("proof_lab")
    if not isinstance(proof_lab, dict):
        raise SmokeCheckError("status-card.json: missing front_door.proof_lab object")

    cache_status = proof_lab.get("cache_status")
    if cache_status in {"stale_cached_receipt", "missing_cached_receipt"}:
        raise SmokeCheckError(
            "status-card.json: proof_lab_cache must be pass after proof-lab "
            f"smoke receipt, got cache_status {cache_status!r}",
        )
    if proof_lab.get("fresh_receipt_required") is not False:
        raise SmokeCheckError(
            "status-card.json: proof_lab fresh_receipt_required must be false "
            "after proof-lab smoke receipt",
        )

    front_door_status = _expect_object(
        status,
        name="status-card.json",
        key="front_door_status",
    )
    surface_statuses = front_door_status.get("surface_statuses")
    if not isinstance(surface_statuses, dict):
        raise SmokeCheckError(
            "status-card.json: missing front_door_status.surface_statuses object",
        )
    surface_status = surface_statuses.get("proof_lab_cache")
    if surface_status != "pass":
        raise SmokeCheckError(
            "status-card.json: proof_lab_cache must be pass after proof-lab "
            f"smoke receipt, got surface status {surface_status!r}",
        )
    actionable = front_door_status.get("actionable_surface_ids")
    if not isinstance(actionable, list):
        raise SmokeCheckError(
            "status-card.json: missing front_door_status.actionable_surface_ids list",
        )
    if "proof_lab_cache" in actionable:
        raise SmokeCheckError(
            "status-card.json: proof_lab_cache must not remain actionable "
            "after proof-lab smoke receipt",
        )
    return str(cache_status)


def check_smoke_outputs(smoke_out: Path) -> dict[str, Any]:
    hello = _read_text(smoke_out / "hello.txt")
    if not hello.splitlines()[0].startswith("Microcosm first screen"):
        raise SmokeCheckError("hello.txt: first line must start with Microcosm first screen")

    version = _read_text(smoke_out / "version.txt")
    if not version.startswith("microcosm "):
        raise SmokeCheckError(f"version.txt: expected microcosm version line, got {version!r}")

    first_screen = _read_json(smoke_out / "first-screen-card.json")
    tour = _read_json(smoke_out / "tour-card.json")
    proof_lab = _read_json(smoke_out / "proof-lab-card.json")
    status = _read_json(smoke_out / "status-card.json")
    served_status = _read_json(smoke_out / "served-status-card.json")
    authority = _read_json(smoke_out / "authority-card.json")
    workingness = _read_json(smoke_out / "workingness-card.json")
    legibility = _read_json(smoke_out / "legibility-scorecard.json")
    stripping_guard = _read_json(smoke_out / "stripping-guard.json")
    first_action = _read_json(smoke_out / "first-action.json")

    for name, payload in (
        ("first-screen-card.json", first_screen),
        ("tour-card.json", tour),
        ("proof-lab-card.json", proof_lab),
        ("status-card.json", status),
        ("served-status-card.json", served_status),
        ("authority-card.json", authority),
        ("workingness-card.json", workingness),
        ("legibility-scorecard.json", legibility),
        ("stripping-guard.json", stripping_guard),
    ):
        _expect_status(payload, name=name)

    if tour.get("card_status") != "clear":
        raise SmokeCheckError(
            f"tour-card.json: expected card_status 'clear', got {tour.get('card_status')!r}",
        )
    if workingness.get("card_status") != "clear":
        raise SmokeCheckError(
            "workingness-card.json: expected card_status 'clear', "
            f"got {workingness.get('card_status')!r}",
        )

    private_path_hit_count = _expect_nonnegative_int(
        served_status,
        name="served-status-card.json",
        key="private_path_hit_count",
    )
    if private_path_hit_count != 0:
        raise SmokeCheckError(
            "served-status-card.json: expected zero private path hits, "
            f"got {private_path_hit_count}",
        )
    _expect_false(
        served_status,
        name="served-status-card.json",
        key="release_authorized",
    )
    _expect_false(
        served_status,
        name="served-status-card.json",
        key="provider_calls_authorized",
    )

    _expect_nested_false(
        proof_lab,
        name="proof-lab-card.json",
        object_key="safe_to_show",
        key="proof_correctness_claim",
    )
    _expect_authority_false(
        proof_lab,
        name="proof-lab-card.json",
        key="formal_proof_authority",
    )
    _expect_authority_false(
        proof_lab,
        name="proof-lab-card.json",
        key="release_authorized",
    )
    _expect_authority_false(
        proof_lab,
        name="proof-lab-card.json",
        key="provider_calls_authorized",
    )
    proof_lab_cache_status = _expect_proof_lab_status_cache_bound(status)

    authority_organ_count = _expect_positive_surface_count(
        authority,
        name="authority-card.json",
        key="organ_authority_count",
    )
    _expect_false(
        authority,
        name="authority-card.json",
        key="unsafe_payload_bodies_exported",
    )
    _expect_authority_false(
        authority,
        name="authority-card.json",
        key="release_authorized",
    )

    mapped_organ_count = _surface_count(
        workingness,
        name="workingness-card.json",
        key="mapped_organ_count",
    )
    _expect_surface_count(
        workingness,
        name="workingness-card.json",
        key="missing_standard_count",
        expected=0,
    )
    _expect_surface_count(
        workingness,
        name="workingness-card.json",
        key="missing_failure_modes_count",
        expected=0,
    )
    _expect_authority_false(
        workingness,
        name="workingness-card.json",
        key="release_authorized",
    )
    workingness_import_signature = _expect_workingness_import_signature_fresh(
        workingness,
    )

    _expect_false(
        legibility,
        name="legibility-scorecard.json",
        key="release_authorized",
    )
    _expect_false(
        legibility,
        name="legibility-scorecard.json",
        key="unsafe_payload_bodies_in_receipt",
    )
    _expect_false(
        stripping_guard,
        name="stripping-guard.json",
        key="release_authorized",
    )
    _expect_false(
        stripping_guard,
        name="stripping-guard.json",
        key="unsafe_payload_bodies_in_receipt",
    )

    # The goal-shaped product: the smoke goal must come back as a complete
    # first-action contract, not a doc-shaped answer.
    if first_action.get("found") is not True:
        raise SmokeCheckError(
            "first-action.json: contract did not resolve the smoke goal",
        )
    fa_action = first_action.get("first_action")
    fa_command = (
        str(fa_action.get("command") or "") if isinstance(fa_action, dict) else ""
    )
    if not fa_command.startswith("PYTHONPATH=src python3 -m microcosm_core"):
        raise SmokeCheckError(
            "first-action.json: command is not the cold-runnable source form",
        )
    if "<" in fa_command:
        raise SmokeCheckError(
            "first-action.json: command carries an unresolved placeholder",
        )
    fa_proof = first_action.get("proof_path")
    if not isinstance(fa_proof, dict) or not (
        fa_proof.get("runnable_validator")
        or fa_proof.get("validator_command")
        or fa_proof.get("validation_commands")
    ):
        raise SmokeCheckError("first-action.json: missing proof path")
    fa_boundary = first_action.get("reading_boundary")
    if not isinstance(fa_boundary, dict) or not (
        fa_boundary.get("stop_condition") or fa_boundary.get("fallback_guidance")
    ):
        raise SmokeCheckError("first-action.json: missing reading boundary")
    if not str(first_action.get("do_not_claim") or "").strip():
        raise SmokeCheckError("first-action.json: missing claim ceiling")

    return {
        "status": "pass",
        "smoke_out": str(smoke_out),
        "version": version,
        "authority_organ_count": authority_organ_count,
        "workingness_card_status": workingness["card_status"],
        "mapped_organ_count": mapped_organ_count,
        "missing_standard_count": 0,
        "missing_failure_modes_count": 0,
        "source_body_import_exception_count": workingness_import_signature[
            "source_body_import_exception_count"
        ],
        "private_path_hit_count": private_path_hit_count,
        "proof_lab_cache_status": proof_lab_cache_status,
    }


def print_summary(summary: dict[str, Any]) -> None:
    print("Microcosm smoke check: pass")
    print(f"receipts: {summary['smoke_out']}")
    print(
        "authority: pass "
        f"({summary['authority_organ_count']} organ authority rows, release false)",
    )
    print(
        "workingness: "
        f"{summary['workingness_card_status']} "
        f"({summary['mapped_organ_count']} mapped, "
        f"{summary['missing_standard_count']} missing standards, "
        f"{summary['missing_failure_modes_count']} missing failure modes, "
        f"{summary['source_body_import_exception_count']} source-body exceptions)",
    )
    print(
        "served status: pass "
        f"({summary['private_path_hit_count']} private path hits)",
    )
    print("proof lab: pass (cache bound, proof correctness false)")
    print("first action: contract pass")
    print(f"version: {summary['version']}")


def main(argv: list[str] | None = None) -> int:
    """CLI entry that validates Microcosm smoke receipts against the public floor.

    - Teleology: Post-`make smoke` gate confirming the smoke receipts exist and assert the public floor (release/provider not authorized, zero private-path hits, required surface counts).
    - Guarantee: On all checks passing, prints a compact pass summary and returns 0; on any failure prints "fail" + reason to stderr and returns 1.
    - Fails: missing/empty/invalid receipt, wrong status, or a violated floor (e.g. release_authorized not false, private path hits) -> SmokeCheckError -> caught, exit 1.
    - Reads: .microcosm/smoke/*.json and *.txt receipts under --smoke-out (via check_smoke_outputs).
    - When-needed: CI/operator validation that a smoke run produced safe, complete receipts before trusting the build.
    - Escalates-to: check_smoke_outputs (the receipt-by-receipt assertions).
    """
    parser = argparse.ArgumentParser(
        description="Validate Microcosm smoke receipts and print a compact pass summary.",
    )
    parser.add_argument(
        "--smoke-out",
        default=".microcosm/smoke",
        help="Directory containing smoke receipts written by make smoke.",
    )
    args = parser.parse_args(argv)

    try:
        summary = check_smoke_outputs(Path(args.smoke_out))
    except SmokeCheckError as exc:
        print("Microcosm smoke check: fail", file=sys.stderr)
        print(f"reason: {exc}", file=sys.stderr)
        return 1
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
