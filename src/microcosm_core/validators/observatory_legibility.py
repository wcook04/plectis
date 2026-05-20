from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from microcosm_core.private_state_scan import PASS, load_forbidden_classes, scan_paths
from microcosm_core.receipts import write_json_atomic
from microcosm_core.runtime_shell import RuntimeShell


CHECKER_ID = "checker.microcosm.validators.observatory_legibility"


def _public_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _rows(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _html_private_hits(html: str) -> list[str]:
    return [
        needle
        for needle in [
            "/Users/",
            "src/ai_workflow",
            "Library/Application Support/Google/" + "Chrome",
            "sk" + "-",
        ]
        if needle in html
    ]


def validate_legibility(
    root: str | Path,
    project: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    public_root = Path(root).resolve(strict=False)
    project_path = Path(project).expanduser().resolve(strict=False)
    output_file = Path(out_path)
    shell = RuntimeShell(public_root)
    model = shell.project_observatory(project_path)
    html = shell._observatory_html(project_path)
    causal = model.get("causal_chain", {}) if isinstance(model.get("causal_chain"), dict) else {}
    route = causal.get("route", {}) if isinstance(causal.get("route"), dict) else {}
    work = causal.get("work_transaction", {}) if isinstance(causal.get("work_transaction"), dict) else {}
    pattern_bindings = causal.get("pattern_bindings", [])
    standard_bindings = causal.get("standard_bindings", [])
    events = causal.get("events", [])
    evidence = causal.get("evidence", [])
    if not isinstance(pattern_bindings, list):
        pattern_bindings = []
    if not isinstance(standard_bindings, list):
        standard_bindings = []
    if not isinstance(events, list):
        events = []
    if not isinstance(evidence, list):
        evidence = []

    html_assertions = {
        "root_is_not_raw_json_only": "Causal Chain" in html and "<details>" in html and html.find("Causal Chain") < html.find("<pre>"),
        "causal_chain_section_present": "Causal Chain" in html,
        "route_id_visible": bool(route.get("route_id")) and str(route.get("route_id")) in html,
        "pattern_binding_visible": any(
            isinstance(row, dict) and row.get("resolved") is True and str(row.get("pattern_id")) in html
            for row in pattern_bindings
        ),
        "standard_binding_visible": any(
            isinstance(row, dict) and row.get("resolved") is True and str(row.get("standard_id")) in html
            for row in standard_bindings
        ),
        "work_state_history_visible": (
            "created -> selected -> planned -> executed_simulation -> closed" in html
            or "created -&gt; selected -&gt; planned -&gt; executed_simulation -&gt; closed" in html
        ),
        "event_refs_visible": bool(events) and any(str(row.get("event_id")) in html for row in events if isinstance(row, dict)),
        "evidence_refs_visible": bool(evidence)
        and any(str(row.get("evidence_ref")) in html for row in evidence if isinstance(row, dict)),
        "evidence_marked_drilldown": "Evidence is drilldown" in html,
        "release_ceiling_visible": "Release remains unauthorized" in html,
        "provider_ceiling_visible": "Provider calls authorized" in html,
        "source_mutation_ceiling_visible": "Source mutation authorized" in html,
        "private_paths_absent": not _html_private_hits(html),
    }
    model_assertions = {
        "model_status_pass": model.get("status") == PASS,
        "route_pattern_refs_present": bool(route.get("pattern_refs")),
        "route_standard_refs_present": bool(route.get("standard_pressure_refs")),
        "pattern_bindings_resolve": bool(pattern_bindings)
        and all(isinstance(row, dict) and row.get("resolved") is True for row in pattern_bindings),
        "standard_bindings_resolve": bool(standard_bindings)
        and all(isinstance(row, dict) and row.get("resolved") is True for row in standard_bindings),
        "work_transaction_present": bool(work.get("work_id")),
        "work_state_history_present": bool(work.get("state_history")),
        "events_present": bool(events),
        "evidence_present": bool(evidence),
        "release_authorized": model.get("release_authorized") is True,
        "provider_calls_authorized": model.get("provider_calls_authorized") is True,
        "source_mutation_authorized": model.get("source_mutation_authorized") is True,
    }
    blocking_codes: list[str] = []
    for key, ok in html_assertions.items():
        if not ok:
            blocking_codes.append(f"OBSERVATORY_HTML_{key.upper()}_FAILED")
    for key, ok in model_assertions.items():
        if key in {"release_authorized", "provider_calls_authorized", "source_mutation_authorized"}:
            if ok:
                blocking_codes.append(f"OBSERVATORY_MODEL_{key.upper()}_FAILED")
            continue
        if not ok:
            blocking_codes.append(f"OBSERVATORY_MODEL_{key.upper()}_FAILED")

    state = project_path / ".microcosm"
    scan_paths_input = [
        path
        for path in [
            public_root / "README.md",
            public_root / "src/microcosm_core/runtime_shell.py",
            state / "graph.json",
            state / "work_items.json",
        ]
        if path.is_file()
    ]
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = scan_paths(scan_paths_input, forbidden_classes=policy, display_root=public_root)
    safe_scan = dict(scan)
    safe_scan.pop("forbidden_output_fields", None)
    if safe_scan.get("blocking_hit_count"):
        blocking_codes.append("OBSERVATORY_PRIVATE_STATE_SCAN_BLOCKED")

    blocking_codes = sorted(set(blocking_codes))
    status = PASS if not blocking_codes else "blocked"
    receipt = {
        "schema_version": "observatory_legibility_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "command": command,
        "project_ref": project_path.name,
        "selected_route_id": model.get("selected_route_id"),
        "html_sections_present": {
            "project_summary": "Project" in html,
            "causal_chain": "Causal Chain" in html,
            "project_graph": "Project Graph" in html,
            "work_transaction": "Work Transaction" in html,
            "events_and_evidence": "Events and Evidence" in html,
            "kernel_and_standards": "Kernel and Standards" in html,
            "json_drilldowns": "JSON Drilldowns" in html,
        },
        "endpoint_summary": model.get("json_drilldowns", {}),
        "causal_chain_proof": {
            "route_id": route.get("route_id"),
            "pattern_binding_ids": [
                row.get("pattern_id") for row in pattern_bindings if isinstance(row, dict)
            ],
            "standard_binding_ids": [
                row.get("standard_id") for row in standard_bindings if isinstance(row, dict)
            ],
            "work_id": work.get("work_id"),
            "state_history": [
                row.get("state")
                for row in work.get("state_history", [])
                if isinstance(row, dict)
            ]
            if isinstance(work.get("state_history"), list)
            else [],
            "event_count": len(events),
            "evidence_count": len(evidence),
        },
        "html_assertions": html_assertions,
        "model_assertions": model_assertions,
        "blocking_codes": blocking_codes,
        "private_state_scan": safe_scan,
        "authority_ceiling": {
            "release_authorized": False,
            "hosting_authorized": False,
            "publication_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "private_data_equivalence_authorized": False,
        },
        "anti_claim": "Observatory legibility validates only the local browser/read model over public project state. It does not authorize release, hosting, provider calls, source mutation, private-data equivalence, live Task Ledger mutation, or production readiness.",
        "receipt_paths": [_public_relative(public_root, output_file)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Microcosm observatory legibility")
    parser.add_argument("--root", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.observatory_legibility "
        f"--root {args.root} --project {Path(args.project).name} --out {args.out}"
    )
    receipt = validate_legibility(args.root, args.project, args.out, command=command)
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
