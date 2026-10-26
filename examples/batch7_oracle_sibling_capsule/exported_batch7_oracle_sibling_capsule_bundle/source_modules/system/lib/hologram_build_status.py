"""
[PURPOSE]
- Teleology: Provide one machine-readable helper for stale hologram phase status
  so control-plane code and automated reactions never need to scrape terminal
  output from `python3 kernel.py --build status`.
- Mechanism: Delegate to `tools.meta.builder.hologram_status()`, normalize the
  stale phase list, and emit the exact rebuild command the kernel CLI would
  recommend for those stale slices.

[INTERFACE]
- Exports: load_hologram_build_status returns hologram_build_status_v1 with stale phases and recommended rebuild command.
- Writes: None.

[FLOW]
- Mechanism: Ask the owner builder for status, normalize stale phases and select the kernel-equivalent rebuild command.

[DEPENDENCIES]
- Couples: tools.meta.builder.hologram_status owns phase freshness inspection.

[CONSTRAINTS]
- Atomicity: Reads current builder status; does not launch a rebuild.
- Orders: Stale phase normalization gives reproducible command selection for the same status.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def load_hologram_build_status(repo_root: Path) -> dict[str, Any]:
    from tools.meta import builder

    status = builder.hologram_status(str(repo_root))
    phases = status.get("phases") if isinstance(status.get("phases"), dict) else {}
    stale_phase_ids = [
        str(phase_id).strip()
        for phase_id, phase_payload in phases.items()
        if isinstance(phase_payload, dict) and bool(phase_payload.get("stale"))
    ]
    stale_phase_ids = [phase_id for phase_id in stale_phase_ids if phase_id]
    phase_list = ",".join(stale_phase_ids)
    rebuild_command = (
        f"python3 kernel.py --build --build-phases {phase_list}"
        if phase_list
        else "python3 kernel.py --build status"
    )
    return {
        "kind": "hologram_build_status",
        "schema_version": "hologram_build_status_v1",
        "exists": bool(status.get("exists")),
        "all_current": bool(status.get("all_current")),
        "stale_count": len(stale_phase_ids),
        "stale_phase_ids": stale_phase_ids,
        "rebuild_command": rebuild_command,
        "generated_at": status.get("generated_at"),
        "source": "tools.meta.builder.hologram_status",
    }
