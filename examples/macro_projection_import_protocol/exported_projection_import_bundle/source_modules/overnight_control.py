#!/usr/bin/env python3
"""
Compatibility launcher for the canonical orchestration control plane.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from system.lib.repo_env import maybe_reexec_into_repo_python

REPO_ROOT = Path(__file__).resolve().parent
if __name__ == "__main__":
    maybe_reexec_into_repo_python(REPO_ROOT)

from system.control.orchestration import (
    build_orchestration_brief,
    build_orchestration_state,
    render_orchestration_brief,
    write_orchestration_artifacts,
)


def build_brief(*, phase_token: str | None = None) -> dict[str, Any]:
    return build_orchestration_brief(
        build_orchestration_state(repo_root=REPO_ROOT, phase_token=phase_token)
    )


def render_markdown(brief: Mapping[str, Any]) -> str:
    return render_orchestration_brief(brief)


def write_brief(
    brief: Mapping[str, Any],
    *,
    json_path: Path | None = None,
    markdown_path: Path | None = None,
) -> dict[str, str]:
    state = build_orchestration_state(repo_root=REPO_ROOT, phase_token=None)
    wrote = write_orchestration_artifacts(repo_root=REPO_ROOT)
    brief_json = Path(json_path) if json_path else REPO_ROOT / wrote["brief_json_path"]
    brief_md = Path(markdown_path) if markdown_path else REPO_ROOT / wrote["brief_markdown_path"]
    if json_path:
        brief_json.write_text(json.dumps(dict(brief), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if markdown_path:
        brief_md.write_text(render_orchestration_brief(brief), encoding="utf-8")
    return {
        "json_path": str(brief_json.relative_to(REPO_ROOT)) if brief_json.is_absolute() and brief_json.is_relative_to(REPO_ROOT) else str(brief_json),
        "markdown_path": str(brief_md.relative_to(REPO_ROOT)) if brief_md.is_absolute() and brief_md.is_relative_to(REPO_ROOT) else str(brief_md),
        "state_path": wrote["state_path"],
        "active_driver": str(state.get("active_driver") or ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit or write the canonical orchestration control state and brief.")
    parser.add_argument("--phase", default=None, help="Optional phase token. Defaults to the active phase.")
    parser.add_argument("--status", action="store_true", help="Print orchestration_state.json payload without side effects beyond refresh.")
    parser.add_argument("--write", action="store_true", help="Write orchestration_state.json plus orchestration_brief.json/.md.")
    args = parser.parse_args()

    if args.write:
        payload = write_orchestration_artifacts(repo_root=REPO_ROOT, phase_token=str(args.phase or "").strip() or None)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    state = build_orchestration_state(repo_root=REPO_ROOT, phase_token=str(args.phase or "").strip() or None)
    if args.status:
        print(json.dumps(state, indent=2, ensure_ascii=False))
        return 0

    print(json.dumps(build_orchestration_brief(state), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
