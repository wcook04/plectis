"""
[PURPOSE]
- Teleology: Centralize additive feed-quality parsing so runtime grading, regrade,
  and operator tooling can treat `metadata.quality` consistently.
- Mechanism: Load artifact envelopes, normalize `metadata.quality`, and derive a
  grading override when any feed emits warn/block quality tones.

[INTERFACE]
- Exports: `ArtifactQualityStatus`, `normalize_quality_tone`,
  `artifact_quality_from_mapping`, `load_artifact_quality`,
  `collect_artifact_qualities`, `quality_grade_override`.
- Inputs: Artifact envelope mappings or artifact JSON files on disk.
- Outputs: Normalized quality-status objects and optional grade overrides.

[CONSTRAINTS]
- Additive only: Missing quality blocks are treated as "no opinion", not failure.
- Deterministic: Returned statuses preserve sorted input node ordering when the
  caller provides sorted node ids.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Optional, Tuple

QualityTone = Literal["ok", "warn", "block"]


@dataclass(frozen=True)
class ArtifactQualityStatus:
    """
    [ROLE]
    - Teleology: Represent the normalized quality posture attached to one artifact.
    - Ownership: Owns the node id, normalized quality tone, attached reasons, and
      any blocked metric identifiers surfaced by the emitting tool.
    - Mutability: Frozen dataclass.
    - Concurrency: Safe to share across threads; immutable.
    """

    node_id: str
    tone: QualityTone
    reasons: Tuple[str, ...] = ()
    blocked_metrics: Tuple[str, ...] = ()
    artifact_status: Optional[str] = None

    @property
    def degraded(self) -> bool:
        return self.tone in {"warn", "block"}


def normalize_quality_tone(value: Any) -> Optional[QualityTone]:
    token = str(value or "").strip().lower()
    if token in {"ok", "warn", "block"}:
        return token  # type: ignore[return-value]
    return None


def _string_tuple(value: Any) -> Tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    items = []
    for item in value:
        text = str(item or "").strip()
        if text:
            items.append(text)
    return tuple(items)


def artifact_quality_from_mapping(
    node_id: str,
    payload: Mapping[str, Any],
) -> Optional[ArtifactQualityStatus]:
    metadata = payload.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    quality = metadata.get("quality")
    if not isinstance(quality, Mapping):
        return None
    tone = normalize_quality_tone(quality.get("tone"))
    if tone is None:
        return None
    artifact_status_raw = payload.get("status") or metadata.get("status")
    artifact_status = str(artifact_status_raw).strip() if artifact_status_raw else None
    return ArtifactQualityStatus(
        node_id=node_id,
        tone=tone,
        reasons=_string_tuple(quality.get("reasons")),
        blocked_metrics=_string_tuple(quality.get("blocked_metrics")),
        artifact_status=artifact_status,
    )


def load_artifact_quality(node_id: str, artifact_path: Path) -> Optional[ArtifactQualityStatus]:
    try:
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, Mapping):
        return None
    return artifact_quality_from_mapping(node_id, payload)


def collect_artifact_qualities(
    artifacts_dir: Path,
    node_ids: Iterable[str],
) -> Tuple[ArtifactQualityStatus, ...]:
    statuses = []
    for node_id in node_ids:
        status = load_artifact_quality(node_id, artifacts_dir / f"{node_id}.json")
        if status is not None:
            statuses.append(status)
    return tuple(statuses)


def _format_quality_reason(label: str, status: ArtifactQualityStatus) -> str:
    if status.reasons:
        first = status.reasons[0]
    elif status.blocked_metrics:
        first = f"blocked metrics: {', '.join(status.blocked_metrics[:3])}"
    else:
        first = "quality gate reported degradation"
    return f"{label}: {status.node_id}: {first}"


def quality_grade_override(
    statuses: Iterable[ArtifactQualityStatus],
) -> Optional[Tuple[str, str]]:
    block = next((status for status in statuses if status.tone == "block"), None)
    if block is not None:
        return "red", _format_quality_reason("Feed quality blocker", block)

    warn = next((status for status in statuses if status.tone == "warn"), None)
    if warn is not None:
        return "amber", _format_quality_reason("Feed quality warning", warn)

    return None
