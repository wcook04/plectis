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


def served_status_smoke(
    *,
    public_root: Path,
    project: Path,
    out: Path,
    host: str = "127.0.0.1",
    timeout_seconds: float = 90.0,
) -> dict[str, Any]:
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
        with urlopen(
            f"http://{server_host}:{server_port}/project/status",
            timeout=timeout_seconds,
        ) as response:
            card = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    body = json.dumps(card, sort_keys=True)
    private_path_hits = _private_path_hits(body, project_path, public_root)
    status = "pass" if not private_path_hits else "blocked"
    receipt = {
        "schema_version": "microcosm_served_status_smoke_receipt_v1",
        "status": status,
        "endpoint": "/project/status",
        "timeout_seconds": timeout_seconds,
        "project_ref": card.get("project_ref"),
        "card_command": card.get("card_command"),
        "observatory_command": (
            card.get("front_door", {}).get("observatory", {}).get("command")
            if isinstance(card.get("front_door"), dict)
            else None
        ),
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
