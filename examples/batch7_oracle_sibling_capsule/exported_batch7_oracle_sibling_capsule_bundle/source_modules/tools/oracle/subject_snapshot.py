"""
[PURPOSE]
- Teleology: Expose a subject-run artifact as an explicit Oracle upstream tool output.
- Mechanism: Load a named artifact from `oracle_subject_run_dir` and return its data with
  subject-side provenance metadata.

[INTERFACE]
- Inputs: `config.runtime.oracle_subject_run_dir`, `config.artifact_id`.
- Outputs: Success envelope carrying hydrated metadata plus the original artifact data.
- Exports: `run`.

[FLOW]
- Resolve the subject run directory and requested artifact id.
- Load `<subject_run_dir>/artifacts/<artifact_id>.json`.
- Copy source metadata, attach Oracle subject provenance, and return the original data payload.

[DEPENDENCIES]
- json: Deserialize subject artifact JSON.
- pathlib.Path: Resolve the subject run artifact path.

[CONSTRAINTS]
- Read-only over subject-run artifact files; no writes or network calls occur here.
- When-needed: Open when Oracle needs to re-expose one subject-run artifact with explicit provenance instead of re-reading artifact JSON directly.
- Escalates-to: tools/oracle/subject_snapshot.py::run; tools/oracle/subject_index.py::run
- Navigation-group: market_intelligence
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Tuple


def _require_subject_run_dir(config: Dict[str, Any]) -> Path:
    runtime = config.get("runtime", {}) if isinstance(config, dict) else {}
    raw = runtime.get("oracle_subject_run_dir")
    if not raw:
        raise ValueError("oracle_subject_run_dir is required for oracle subject snapshot tools")
    run_dir = Path(str(raw))
    if not run_dir.exists():
        raise ValueError(f"oracle_subject_run_dir does not exist: {run_dir}")
    return run_dir


def _require_artifact_id(config: Dict[str, Any]) -> str:
    artifact_id = config.get("artifact_id") if isinstance(config, dict) else None
    if not isinstance(artifact_id, str) or not artifact_id.strip():
        raise ValueError("artifact_id is required for oracle subject snapshot tools")
    return artifact_id.strip()


def _load_artifact(subject_run_dir: Path, artifact_id: str) -> Tuple[Dict[str, Any], Any]:
    path = subject_run_dir / "artifacts" / f"{artifact_id}.json"
    if not path.exists():
        raise ValueError(f"Subject artifact does not exist: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Subject artifact is not a JSON object: {path}")
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata, payload.get("data")


def run(config: Dict[str, Any], run_dir: str | None = None) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Hydrate one named subject artifact into the Oracle subject-snapshot envelope.
    - Mechanism: Resolve the subject run directory and artifact id, load the artifact JSON, merge subject provenance keys onto metadata, and return the source data unmodified.
    - Reads: `config.runtime.oracle_subject_run_dir`, `config.artifact_id`, and `<run>/artifacts/<artifact_id>.json`.
    - Writes: None.
    - Guarantee: Returns `metadata.status="success"` plus `subject_run_id`, `source_artifact_id`, `hydrated_from_subject`, and the original artifact data payload.
    - Fails: Raises ValueError for missing subject run dir, missing artifact id, missing artifact file, or invalid artifact JSON shape.
    - When-needed: Open when wiring a single subject artifact into Oracle and you need the exact metadata hydration contract.
    - Escalates-to: tools/oracle/subject_index.py::run; tools/oracle/truth_diff_equity.py::run
    """
    del run_dir
    subject_run_dir = _require_subject_run_dir(config)
    artifact_id = _require_artifact_id(config)
    metadata, data = _load_artifact(subject_run_dir, artifact_id)
    metadata = dict(metadata)
    metadata.update(
        {
            "tool": "oracle_subject_snapshot",
            "status": "success",
            "subject_run_id": subject_run_dir.name,
            "source_artifact_id": artifact_id,
            "hydrated_from_subject": str(subject_run_dir),
        }
    )
    return {
        "metadata": metadata,
        "data": data,
    }
