from __future__ import annotations

import argparse
import json
import threading
from pathlib import Path
from typing import Any
from urllib.request import urlopen

from microcosm_core.runtime_shell import RuntimeShell


def _private_path_hits(body: str, project_path: Path, public_root: Path) -> list[str]:
    needles = [
        project_path.resolve(strict=False).as_posix(),
        public_root.resolve(strict=False).as_posix(),
        "/Users/",
        "src/ai_workflow",
    ]
    return [needle for needle in needles if needle and needle in body]


def _read_served_json(
    *,
    host: str,
    port: int,
    endpoint: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    with urlopen(
        f"http://{host}:{port}{endpoint}",
        timeout=timeout_seconds,
    ) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{endpoint} did not return a JSON object")
    return payload


def _observatory_contract_failures(card: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if card.get("schema_version") != "microcosm_project_observatory_card_v1":
        failures.append("schema_version")
    if card.get("status") != "pass":
        failures.append("status")
    surface_statuses = card.get("surface_statuses")
    if not isinstance(surface_statuses, dict):
        failures.append("surface_statuses")
    else:
        for surface_id in (
            "route",
            "work",
            "evidence",
            "graph",
            "state_inspection",
        ):
            if surface_statuses.get(surface_id) != "pass":
                failures.append(f"surface_statuses.{surface_id}")
    state_inspection = card.get("state_inspection")
    if not isinstance(state_inspection, dict):
        failures.append("state_inspection")
    elif state_inspection.get("status") != "pass":
        failures.append("state_inspection.status")
    safe_to_show = card.get("safe_to_show")
    if not isinstance(safe_to_show, dict):
        failures.append("safe_to_show")
    else:
        for key in (
            "provider_calls_authorized",
            "source_files_mutated",
            "proof_correctness_claim",
            "release_authorized",
        ):
            if safe_to_show.get(key) is not False:
                failures.append(f"safe_to_show.{key}")
    return failures


def served_status_smoke(
    *,
    public_root: Path,
    project: Path,
    out: Path,
    host: str = "127.0.0.1",
    timeout_seconds: float = 90.0,
) -> dict[str, Any]:
    """Serve the runtime shell, fetch /project/status, and record a public-safe smoke receipt.

    - Teleology: end-to-end check that the served status endpoint returns a card with no private-path leakage.
    - Guarantee: starts/stops an ephemeral server, fetches the status card, and writes a receipt to `out`.
    - Fails: any private-path needle found in the served body -> receipt status 'blocked'.
    - Reads: project tree served by RuntimeShell at the /project/status endpoint.
    - Writes: `out` receipt JSON.
    """
    shell = RuntimeShell(public_root)
    project_path = project.expanduser()
    if not project_path.is_absolute():
        project_path = public_root / project_path
    project_path = project_path.resolve(strict=False)

    server = shell.serve(host, 0, project_path)
    server_host, server_port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        card = _read_served_json(
            host=server_host,
            port=server_port,
            endpoint="/project/status",
            timeout_seconds=timeout_seconds,
        )
        observatory_card = _read_served_json(
            host=server_host,
            port=server_port,
            endpoint="/project/observatory-card",
            timeout_seconds=timeout_seconds,
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    status_body = json.dumps(card, sort_keys=True)
    observatory_body = json.dumps(observatory_card, sort_keys=True)
    status_private_path_hits = _private_path_hits(status_body, project_path, public_root)
    observatory_private_path_hits = _private_path_hits(
        observatory_body,
        project_path,
        public_root,
    )
    private_path_hits = sorted(
        set(status_private_path_hits + observatory_private_path_hits)
    )
    observatory_contract_failures = _observatory_contract_failures(observatory_card)
    observatory_contract_status = (
        "pass" if not observatory_contract_failures else "blocked"
    )
    status = (
        "pass"
        if not private_path_hits and observatory_contract_status == "pass"
        else "blocked"
    )
    observatory_surface_statuses = (
        observatory_card.get("surface_statuses")
        if isinstance(observatory_card.get("surface_statuses"), dict)
        else {}
    )
    observatory_state_inspection = (
        observatory_card.get("state_inspection")
        if isinstance(observatory_card.get("state_inspection"), dict)
        else {}
    )
    observatory_safe_to_show = (
        observatory_card.get("safe_to_show")
        if isinstance(observatory_card.get("safe_to_show"), dict)
        else {}
    )
    receipt = {
        "schema_version": "microcosm_served_status_smoke_receipt_v1",
        "status": status,
        "endpoint": "/project/status",
        "observatory_endpoint": "/project/observatory-card",
        "timeout_seconds": timeout_seconds,
        "project_ref": card.get("project_ref"),
        "card_command": card.get("card_command"),
        "observatory_command": (
            card.get("front_door", {}).get("observatory", {}).get("command")
            if isinstance(card.get("front_door"), dict)
            else None
        ),
        "observatory_contract_status": observatory_contract_status,
        "observatory_contract_failures": observatory_contract_failures,
        "observatory_card_status": observatory_card.get("status"),
        "observatory_schema_version": observatory_card.get("schema_version"),
        "observatory_selected_route_id": observatory_card.get("selected_route_id"),
        "observatory_surface_statuses": {
            key: observatory_surface_statuses.get(key)
            for key in (
                "route",
                "work",
                "evidence",
                "graph",
                "state_inspection",
                "proof_lab",
            )
        },
        "observatory_state_inspection_status": observatory_state_inspection.get(
            "status"
        ),
        "observatory_safe_to_show": {
            key: observatory_safe_to_show.get(key)
            for key in (
                "provider_calls_authorized",
                "source_files_mutated",
                "proof_correctness_claim",
                "release_authorized",
            )
        },
        "status_private_path_hit_count": len(status_private_path_hits),
        "observatory_private_path_hit_count": len(observatory_private_path_hits),
        "private_path_hit_count": len(private_path_hits),
        "private_path_hits": private_path_hits,
        "source_files_mutated": False,
        "provider_calls_authorized": False,
        "release_authorized": False,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def main(argv: list[str] | None = None) -> int:
    """Parse args, run the served-status smoke, and return its exit code.

    - Teleology: CLI entry that runs the served /project/status public-safety smoke from the shell.
    - Guarantee: writes the smoke receipt to --out and returns 0 only when status is 'pass'.
    - Fails: receipt status != 'pass' (private-path leak) -> returns exit code 1.
    - Reads: --root public root and --project tree.
    - Writes: --out receipt JSON.
    """
    parser = argparse.ArgumentParser(
        description="Fetch served /project/status and record a public-safe smoke receipt.",
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--project", default=".")
    parser.add_argument("--out", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    args = parser.parse_args(argv)

    receipt = served_status_smoke(
        public_root=Path(args.root).expanduser().resolve(strict=False),
        project=Path(args.project),
        out=Path(args.out),
        host=args.host,
        timeout_seconds=args.timeout_seconds,
    )
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
