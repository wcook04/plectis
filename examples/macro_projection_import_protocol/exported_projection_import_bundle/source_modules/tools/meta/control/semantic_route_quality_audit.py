"""
[PURPOSE]
- Teleology: Audit semantic-routing edges on each new drift snapshot by dispatching
  Kimi K2 (via NVIDIA NIM) at a bounded sample of drift-pressured nodes, then
  amplifying or suppressing existing edges through the derived_plus_evidence
  side-channel. Always-awake via metabolismd + reactions_engine; never
  unnecessary because the reactions layer dedupes on drift signal_digest.
- Mechanism: Loads route_drift.json and route_graph.json, samples top-K drift
  entries, builds a per-node audit prompt from the node's neighbors, calls
  nvidia_nim.chat_completion with moonshotai/kimi-k2-thinking, parses the
  JSON response, and emits `confirmation` / `rejected` evidence rows via
  semantic_routing.confirm_route. Never writes to the graph directly.

[INTERFACE]
- Exports: main (CLI entry), run_audit (library entry returning a report dict).
- Reads: state/semantic_routing/route_drift.json, route_graph.json, route_status.json;
  codex/standards/std_semantic_routing.json; NVIDIA_* env vars.
- Writes: codex/ledger/semantic_routing/route_evidence.jsonl (via confirm_route),
  state/semantic_routing/route_quality_audit/<iso>.json (per-cycle report),
  stdout (JSON summary for reactions_ledger.jsonl consumption).

[FLOW]
- Resolve repo root -> load drift + graph -> fingerprint drift snapshot ->
  reuse an existing completed report if the digest has already been audited ->
  sample N drifts -> per drift: build prompt -> NIM call -> parse JSON ->
  emit evidence rows -> aggregate report -> write report file -> print summary JSON.
- When-needed: Open when wiring the resident routing-quality lane or when the
  audit op's shape changes (new model, new sample strategy, new evidence kinds).
- Escalates-to: codex/doctrine/skills/kernel/routing_quality_improver.md

[CONSTRAINTS]
- Guarantee: Never mutates route_graph.json, route_status.json, or the standard.
  Only appends to codex/ledger/semantic_routing/route_evidence.jsonl through
  confirm_route. One cycle = one drift snapshot digest.
- Guarantee: Drift digests exclude timestamp and evidence-output churn, so K2 is
  not called again for the same drift work set unless `--force` is explicit.
- Non-goal: Does not propose axis-family or source-kind additions. Does not
  manufacture edges that cosine similarity never named. Does not persist K2
  chain-of-thought.
- Scope: Internal development lane; not customer-facing. K2 responses that
  fail JSON parse are logged and skipped, not auto-repaired.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from system.lib import nvidia_nim  # noqa: E402
from system.lib import semantic_routing  # noqa: E402


DEFAULT_SAMPLE = 8
DEFAULT_MAX_NEIGHBORS = 5
DEFAULT_MODEL = nvidia_nim.DEFAULT_ROUTING_AUDIT_MODEL  # moonshotai/kimi-k2-thinking
DEFAULT_MAX_TOKENS = 1800
AUDIT_REPORT_DIR = REPO_ROOT / "state" / "semantic_routing" / "route_quality_audit"


SYSTEM_PROMPT = (
    "You are a semantic-routing quality auditor. You review edges in a derived-plus-evidence "
    "route graph. The graph is rebuilt from embeddings; your output does NOT modify the graph. "
    "You emit evidence that reorders existing edges within a capped boost. You never invent "
    "edges and you never propose axis-family changes.\n\n"
    "For each candidate neighbor, classify the edge as:\n"
    "  - strong: the target row carries real navigable signal for the source row within the "
    "named axis family. The semantic_score is not wrong.\n"
    "  - weak: cosine caught surface similarity but the claim/mechanism/trigger is actually "
    "different. The edge exists but misleads navigation.\n"
    "  - uncertain: you cannot tell from the previews. This is fine. Do not fabricate confidence.\n\n"
    "Return STRICT JSON matching this shape exactly:\n"
    "{\n"
    '  "confirm_edges":   [{"target_row_key": "...", "confidence": 0.0, "reason": "..."}],\n'
    '  "weak_edges":      [{"target_row_key": "...", "reason": "..."}],\n'
    '  "uncertain_edges": [{"target_row_key": "...", "reason": "..."}],\n'
    '  "notes": "optional free-form observation; not treated as authority"\n'
    "}"
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S-%fZ")


def _atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _drift_snapshot_digest(drift: dict[str, Any]) -> str:
    return semantic_routing.route_drift_snapshot_digest(drift)[:16]


def _latest_completed_report_for_digest(drift_digest: str, *, dry_run: bool) -> dict[str, Any] | None:
    if not drift_digest:
        return None
    candidates = sorted(AUDIT_REPORT_DIR.glob(f"{drift_digest}_*.json"), reverse=True)
    for path in candidates:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if report.get("status") != "ok":
            continue
        if not dry_run and bool(report.get("dry_run")):
            continue
        totals = report.get("totals") if isinstance(report.get("totals"), dict) else {}
        if int(totals.get("nim_errors") or 0) or int(totals.get("parse_errors") or 0):
            continue
        report = dict(report)
        report.setdefault("report_path", str(path.relative_to(REPO_ROOT)))
        return report
    return None


def sample_drift_nodes(drift: dict[str, Any], *, sample: int) -> list[dict[str, Any]]:
    drifts = drift.get("drifts") or []
    if not drifts:
        return []
    seen_rows: set[str] = set()
    chosen: list[dict[str, Any]] = []
    for entry in drifts:
        if not isinstance(entry, dict):
            continue
        row_key = str(entry.get("source_row_key") or "").strip()
        if not row_key or row_key in seen_rows:
            continue
        seen_rows.add(row_key)
        chosen.append(entry)
        if len(chosen) >= sample:
            break
    return chosen


def _node_neighbors(graph: dict[str, Any], row_key: str, *, max_neighbors: int) -> list[dict[str, Any]]:
    nodes = graph.get("nodes") or {}
    node = nodes.get(row_key) or {}
    candidates: list[dict[str, Any]] = []
    same_kind = node.get("same_kind_neighbors") or []
    for n in same_kind:
        if isinstance(n, dict):
            candidates.append(dict(n))
    cross = node.get("neighbors_by_target_kind") or {}
    if isinstance(cross, dict):
        for _kind, rows in cross.items():
            if not isinstance(rows, list):
                continue
            for n in rows:
                if isinstance(n, dict):
                    candidates.append(dict(n))
    candidates.sort(key=lambda c: -float(c.get("semantic_score") or 0.0))
    return candidates[:max_neighbors]


def _node_text_preview(graph: dict[str, Any], row_key: str) -> str:
    nodes = graph.get("nodes") or {}
    node = nodes.get(row_key) or {}
    title = str(node.get("title") or "").strip()
    return title[:400]


def build_audit_prompt(
    drift_entry: dict[str, Any],
    *,
    graph: dict[str, Any],
    plane_tldr: str,
    max_neighbors: int,
) -> dict[str, Any]:
    source_row_key = str(drift_entry.get("source_row_key") or "")
    source_kind = str(drift_entry.get("source_kind") or "")
    source_id = str(drift_entry.get("source_id") or "")
    source_facet = str(drift_entry.get("source_facet") or "")
    neighbors = _node_neighbors(graph, source_row_key, max_neighbors=max_neighbors)
    nodes = graph.get("nodes") or {}
    source_node = nodes.get(source_row_key) or {}
    axis_family = str(source_node.get("axis_family") or "")

    neighbor_rows: list[dict[str, Any]] = []
    for n in neighbors:
        target_row_key = str(n.get("target_row_key") or n.get("row_key") or "")
        if not target_row_key:
            continue
        target_title = _node_text_preview(graph, target_row_key)
        neighbor_rows.append(
            {
                "target_row_key": target_row_key,
                "target_kind": str(n.get("target_kind") or ""),
                "target_facet": str(n.get("target_facet") or ""),
                "semantic_score": float(n.get("semantic_score") or 0.0),
                "text_preview": target_title,
            }
        )

    return {
        "plane_tldr": plane_tldr,
        "axis_family": axis_family,
        "source_row": {
            "source_kind": source_kind,
            "artifact_id": source_id,
            "facet": source_facet,
            "row_key": source_row_key,
            "text_preview": _node_text_preview(graph, source_row_key),
            "drift_reason": drift_entry.get("drift_reason"),
        },
        "candidate_neighbors": neighbor_rows,
    }


def _extract_json_block(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        try:
            return json.loads(text[first : last + 1])
        except json.JSONDecodeError:
            return None
    return None


def audit_node_with_k2(
    prompt_payload: dict[str, Any],
    *,
    model: str,
    max_tokens: int,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {"_dry_run": True, "confirm_edges": [], "weak_edges": [], "uncertain_edges": [], "notes": "dry-run; K2 not called"}
    user_prompt = (
        "Audit the following routing-node neighborhood. Respond with strict JSON.\n\n"
        + json.dumps(prompt_payload, indent=2, sort_keys=True)
    )
    try:
        response_text = nvidia_nim.chat_completion(
            prompt=user_prompt,
            config={
                "model": model,
                "system_prompt": SYSTEM_PROMPT,
                "max_tokens": max_tokens,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
        )
    except Exception as exc:  # noqa: BLE001
        return {"_error": f"nim_call_failed: {exc}", "confirm_edges": [], "weak_edges": [], "uncertain_edges": []}

    parsed = _extract_json_block(response_text) or {}
    if not isinstance(parsed, dict):
        return {"_error": "response_not_object", "raw_preview": response_text[:400], "confirm_edges": [], "weak_edges": [], "uncertain_edges": []}
    return {
        "confirm_edges": parsed.get("confirm_edges") or [],
        "weak_edges": parsed.get("weak_edges") or [],
        "uncertain_edges": parsed.get("uncertain_edges") or [],
        "notes": str(parsed.get("notes") or "")[:600],
        "_raw_response_length": len(response_text),
    }


def _row_key_to_artifact_token(row_key: str) -> str:
    # row_key is "source_kind:artifact_id:facet". artifact_token is "source_kind:artifact_id".
    parts = row_key.split(":")
    if len(parts) >= 2:
        return parts[0] + ":" + parts[1]
    return row_key


def persist_evidence(
    *,
    repo_root: Path,
    source_row_key: str,
    audit_decision: dict[str, Any],
    operation_id: str,
    dry_run: bool,
) -> dict[str, Any]:
    outcome = {"confirmations_written": 0, "rejections_written": 0, "errors": [], "dry_run": dry_run}
    if dry_run:
        outcome["confirmations_skipped"] = len(audit_decision.get("confirm_edges") or [])
        outcome["rejections_skipped"] = len(audit_decision.get("weak_edges") or [])
        return outcome

    source_artifact = _row_key_to_artifact_token(source_row_key)

    for edge in audit_decision.get("confirm_edges") or []:
        if not isinstance(edge, dict):
            continue
        target_row_key = str(edge.get("target_row_key") or "").strip()
        if not target_row_key:
            continue
        target_artifact = _row_key_to_artifact_token(target_row_key)
        confidence = edge.get("confidence")
        reason = str(edge.get("reason") or "")[:280]
        note = f"quality_audit_confirm conf={confidence}: {reason}"
        try:
            result = semantic_routing.confirm_route(
                repo_root,
                source_token=source_artifact,
                target_token=target_artifact,
                evidence_kind="confirmation",
                actor_id="k2_routing_audit",
                note=note,
                operation_id=operation_id,
            )
            if "error" in result:
                outcome["errors"].append({"stage": "confirm", "edge": target_row_key, "detail": result["error"]})
            else:
                outcome["confirmations_written"] += 1
        except Exception as exc:  # noqa: BLE001
            outcome["errors"].append({"stage": "confirm", "edge": target_row_key, "detail": str(exc)[:200]})

    for edge in audit_decision.get("weak_edges") or []:
        if not isinstance(edge, dict):
            continue
        target_row_key = str(edge.get("target_row_key") or "").strip()
        if not target_row_key:
            continue
        target_artifact = _row_key_to_artifact_token(target_row_key)
        reason = str(edge.get("reason") or "")[:280]
        note = f"weak_edge_flag: {reason}"
        try:
            result = semantic_routing.confirm_route(
                repo_root,
                source_token=source_artifact,
                target_token=target_artifact,
                evidence_kind="rejected",
                actor_id="k2_routing_audit",
                note=note,
                operation_id=operation_id,
            )
            if "error" in result:
                outcome["errors"].append({"stage": "reject", "edge": target_row_key, "detail": result["error"]})
            else:
                outcome["rejections_written"] += 1
        except Exception as exc:  # noqa: BLE001
            outcome["errors"].append({"stage": "reject", "edge": target_row_key, "detail": str(exc)[:200]})

    return outcome


def _load_plane_tldr() -> str:
    module_path = REPO_ROOT / "codex" / "doctrine" / "paper_modules" / "semantic_routing_plane.md"
    try:
        text = module_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r"## TLDR \(compressed view\)\s*\n\n(.+?)\n\n## ", text, re.DOTALL)
    if match:
        return match.group(1).strip()[:2400]
    return ""


def run_audit(
    *,
    sample: int,
    model: str,
    max_neighbors: int,
    max_tokens: int,
    dry_run: bool,
    force: bool = False,
) -> dict[str, Any]:
    started_at = _iso_now()
    drift = semantic_routing.load_route_drift(REPO_ROOT)

    if not drift or drift.get("drift_count") == 0 or not (drift.get("drifts") or []):
        return {
            "kind": "semantic_route_quality_audit",
            "status": "skipped",
            "reason": "no_drift",
            "started_at": started_at,
            "drift_snapshot_digest": None,
        }

    drift_digest = _drift_snapshot_digest(drift)
    if not force:
        existing = _latest_completed_report_for_digest(drift_digest, dry_run=dry_run)
        if existing:
            return {
                "kind": "semantic_route_quality_audit",
                "schema_version": "semantic_route_quality_audit_v1",
                "status": "skipped",
                "reason": "drift_snapshot_already_audited",
                "dry_run": dry_run,
                "started_at": started_at,
                "drift_snapshot_digest": drift_digest,
                "existing_operation_id": existing.get("operation_id"),
                "existing_report_path": existing.get("report_path"),
                "existing_finished_at": existing.get("finished_at"),
                "existing_totals": existing.get("totals") or {},
            }

    graph = semantic_routing.load_route_graph(REPO_ROOT)
    chosen = sample_drift_nodes(drift, sample=sample)
    plane_tldr = _load_plane_tldr()

    operation_id = f"semantic_route_quality_audit_{drift_digest}"
    per_node_results: list[dict[str, Any]] = []
    totals = {"confirmations_written": 0, "rejections_written": 0, "errors": 0, "nim_errors": 0, "parse_errors": 0}

    for entry in chosen:
        source_row_key = str(entry.get("source_row_key") or "")
        if not source_row_key:
            continue
        prompt_payload = build_audit_prompt(entry, graph=graph, plane_tldr=plane_tldr, max_neighbors=max_neighbors)
        if not prompt_payload["candidate_neighbors"]:
            per_node_results.append({"source_row_key": source_row_key, "status": "no_neighbors"})
            continue
        decision = audit_node_with_k2(
            prompt_payload,
            model=model,
            max_tokens=max_tokens,
            dry_run=dry_run,
        )
        if "_error" in decision:
            totals["nim_errors"] += 1
            per_node_results.append({"source_row_key": source_row_key, "status": "error", "detail": decision["_error"]})
            continue
        outcome = persist_evidence(
            repo_root=REPO_ROOT,
            source_row_key=source_row_key,
            audit_decision=decision,
            operation_id=operation_id,
            dry_run=dry_run,
        )
        totals["confirmations_written"] += int(outcome.get("confirmations_written") or 0)
        totals["rejections_written"] += int(outcome.get("rejections_written") or 0)
        totals["errors"] += len(outcome.get("errors") or [])
        per_node_results.append(
            {
                "source_row_key": source_row_key,
                "axis_family": prompt_payload.get("axis_family"),
                "candidate_count": len(prompt_payload["candidate_neighbors"]),
                "decision_counts": {
                    "confirm": len(decision.get("confirm_edges") or []),
                    "weak": len(decision.get("weak_edges") or []),
                    "uncertain": len(decision.get("uncertain_edges") or []),
                },
                "persist_outcome": outcome,
                "notes": decision.get("notes") or "",
            }
        )

    finished_at = _iso_now()
    report = {
        "kind": "semantic_route_quality_audit",
        "schema_version": "semantic_route_quality_audit_v1",
        "status": "ok",
        "dry_run": dry_run,
        "started_at": started_at,
        "finished_at": finished_at,
        "operation_id": operation_id,
        "drift_snapshot_digest": drift_digest,
        "drift_generated_at": drift.get("generated_at"),
        "drift_count": drift.get("drift_count"),
        "sampled_count": len(chosen),
        "model": nvidia_nim._normalize_model_id(model),
        "max_neighbors": max_neighbors,
        "max_tokens": max_tokens,
        "totals": totals,
        "per_node": per_node_results,
    }
    report_path = AUDIT_REPORT_DIR / f"{drift_digest}_{started_at}.json"
    _atomic_write_json(report_path, report)
    report["report_path"] = str(report_path.relative_to(REPO_ROOT))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Signal-gated K2 audit over the semantic routing plane's drift snapshot. "
        "Emits only append-only evidence rows; never mutates the graph."
    )
    parser.add_argument("--sample", type=int, default=DEFAULT_SAMPLE, help="How many drift-pressured nodes to audit per cycle (default 8).")
    parser.add_argument("--max-neighbors", type=int, default=DEFAULT_MAX_NEIGHBORS, help="Max neighbors per audited node (default 5).")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"NVIDIA NIM chat model or alias (default {DEFAULT_MODEL}).")
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="K2 max_tokens budget per call (default 1800).")
    parser.add_argument("--dry-run", action="store_true", help="Skip NIM calls and evidence writes; still writes a report.")
    parser.add_argument("--force", action="store_true", help="Spend K2/NIM even when this drift digest already has a completed report.")
    args = parser.parse_args(argv)

    try:
        report = run_audit(
            sample=args.sample,
            model=args.model,
            max_neighbors=args.max_neighbors,
            max_tokens=args.max_tokens,
            dry_run=args.dry_run,
            force=args.force,
        )
    except Exception as exc:  # noqa: BLE001
        fail = {"kind": "semantic_route_quality_audit", "status": "error", "detail": str(exc)[:400]}
        print(json.dumps(fail, indent=2))
        return 2

    print(json.dumps(report, indent=2))
    return 0 if report.get("status") in ("ok", "skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
