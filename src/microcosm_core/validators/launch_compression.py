from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from microcosm_core import project_substrate
from microcosm_core.private_state_scan import PASS, load_forbidden_classes, scan_paths
from microcosm_core.receipts import write_json_atomic
from microcosm_core.runtime_shell import RuntimeShell


CHECKER_ID = "checker.microcosm.validators.launch_compression"


def _public_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(root.resolve(strict=False)).as_posix()
    except ValueError:
        return path.as_posix()


def _first_lines(path: Path, count: int) -> str:
    return "\n".join(path.read_text(encoding="utf-8").splitlines()[:count])


def _private_hits(text: str) -> list[str]:
    return [
        needle
        for needle in [
            "/Users/",
            "src/ai_workflow",
            "Library/Application Support/Google/" + "Chrome",
            "sk" + "-",
        ]
        if needle in text
    ]


def _walk_state_files(project: Path) -> list[Path]:
    state = project / project_substrate.STATE_DIR
    if not state.is_dir():
        return []
    return [path for path in sorted(state.rglob("*")) if path.is_file()]


def validate_launch_compression(
    root: str | Path,
    project: str | Path,
    out_path: str | Path,
    *,
    command: str,
) -> dict[str, Any]:
    public_root = Path(root).resolve(strict=False)
    project_path = Path(project).expanduser().resolve(strict=False)
    output_file = Path(out_path)
    readme_path = public_root / "README.md"
    pyproject_path = public_root / "pyproject.toml"
    readme_first_screen = _first_lines(readme_path, 35)
    pyproject_text = pyproject_path.read_text(encoding="utf-8") if pyproject_path.is_file() else ""

    compiled = project_substrate.compile_project(project_path)
    shell = RuntimeShell(public_root)
    observatory_html = shell._observatory_html(project_path)
    state_files = _walk_state_files(project_path)
    state_text = "\n".join(path.read_text(encoding="utf-8") for path in state_files if path.suffix in {".json", ".jsonl"})
    first_screen_lower = readme_first_screen.lower()
    receipt_forward_needles = ["receipt", "adapter", "truth index", "organ registry", "reconstruction"]

    assertions = {
        "one_line_identity_present": "repo -> .microcosm" in readme_first_screen
        and "inspectable work substrate" in readme_first_screen,
        "one_command_quickstart_present": "microcosm compile ." in readme_first_screen,
        "try_it_on_your_repo_present": "try it on your repo" in first_screen_lower,
        "first_screen_not_receipt_forward": not any(needle in first_screen_lower for needle in receipt_forward_needles),
        "pyproject_description_compressed": "repo" in pyproject_text
        and ".microcosm" in pyproject_text,
        "compile_command_passes": compiled.get("status") == PASS,
        "compile_headline_compressed": compiled.get("headline") == "repo -> .microcosm",
        "compile_creates_local_state": (project_path / project_substrate.STATE_DIR).is_dir(),
        "compile_detects_patterns": int(compiled.get("passing_pattern_count") or 0) > 0,
        "compile_opens_routes": int(compiled.get("route_count") or 0) > 0,
        "compile_runs_work_transaction": bool(compiled.get("work_id")),
        "compile_emits_events": int(compiled.get("event_count") or 0) > 0,
        "compile_emits_evidence": int(compiled.get("evidence_count") or 0) > 0,
        "compile_does_not_mutate_source": compiled.get("source_files_mutated") is False,
        "observatory_shows_causal_chain": "Causal Chain" in observatory_html
        and str(compiled.get("selected_route_id") or "") in observatory_html,
        "evidence_marked_drilldown": "Evidence is drilldown" in observatory_html,
        "release_ceiling_visible": "Release remains unauthorized" in observatory_html,
        "private_paths_absent": not (
            _private_hits(readme_first_screen)
            or _private_hits(json.dumps(compiled, sort_keys=True))
            or _private_hits(observatory_html)
            or _private_hits(state_text)
        ),
    }
    blocking_codes = [
        f"LAUNCH_COMPRESSION_{key.upper()}_FAILED"
        for key, ok in assertions.items()
        if not ok
    ]

    scan_inputs = [
        path
        for path in [
            readme_path,
            public_root / "AGENTS.md",
            pyproject_path,
            project_path / ".microcosm/catalog.json",
            project_path / ".microcosm/routes.json",
            project_path / ".microcosm/work_items.json",
        ]
        if path.is_file()
    ]
    policy = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan = scan_paths(scan_inputs, forbidden_classes=policy, display_root=public_root)
    safe_scan = dict(scan)
    safe_scan.pop("forbidden_output_fields", None)
    if safe_scan.get("blocking_hit_count"):
        blocking_codes.append("LAUNCH_COMPRESSION_PRIVATE_STATE_SCAN_BLOCKED")

    blocking_codes = sorted(set(blocking_codes))
    status = PASS if not blocking_codes else "blocked"
    receipt = {
        "schema_version": "launch_compression_receipt_v1",
        "checker_id": CHECKER_ID,
        "status": status,
        "command": command,
        "project_ref": project_path.name,
        "one_line_identity": "repo -> .microcosm: turn any folder into an inspectable work substrate.",
        "quickstart_command": "microcosm compile .",
        "compiled_summary": {
            "headline": compiled.get("headline"),
            "file_count": compiled.get("file_count"),
            "passing_pattern_count": compiled.get("passing_pattern_count"),
            "route_count": compiled.get("route_count"),
            "selected_route_id": compiled.get("selected_route_id"),
            "work_id": compiled.get("work_id"),
            "event_count": compiled.get("event_count"),
            "evidence_count": compiled.get("evidence_count"),
            "open_observatory": compiled.get("open_observatory"),
        },
        "assertions": assertions,
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
        "anti_claim": "Launch-compression validation proves only that the public first screen and one-command local loop expose repo -> .microcosm without receipt-first UX. It does not authorize release, hosting, publication, provider calls, source mutation, private-data equivalence, or production readiness.",
        "receipt_paths": [_public_relative(public_root, output_file)],
    }
    write_json_atomic(output_file, receipt)
    return receipt


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Microcosm launch compression")
    parser.add_argument("--root", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = (
        "python -m microcosm_core.validators.launch_compression "
        f"--root {args.root} --project {Path(args.project).name} --out {args.out}"
    )
    receipt = validate_launch_compression(args.root, args.project, args.out, command=command)
    return 0 if receipt["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
