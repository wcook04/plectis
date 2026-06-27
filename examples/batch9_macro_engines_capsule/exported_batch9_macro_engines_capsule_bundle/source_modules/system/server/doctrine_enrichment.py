"""
[PURPOSE]
- Teleology: Enrich inspector file details with doctrine linkage (mechanisms, concepts, principles)
  so the operator can drill from code → theory → intent without leaving the Inspector.
- Mechanism:
  1. Load all mechanism JSONs once at init (caches `code_loci[].path` for fast file→mechanism lookup).
  2. Load all concept JSONs once (caches `concept_edges` from mechanisms for file→concept transitivity).
  3. Load active family raw_seed_principles.json (caches principles by id for principle_edge resolution).
  4. Build reverse indices so a single file path resolves to a compact doctrine envelope.
  5. Expose doctrine detail lookup (by id) for drill-down drawers.
- Non-goal: Does not rewrite doctrine, does not depend on full kernel navigation state.

[INTERFACE]
- Exports: DoctrineEnrichmentService
- Methods:
    - `get_file_doctrine(rel_path) -> dict` — envelope of mechanisms, concepts, principles, related files
    - `get_doctrine_detail(doctrine_id) -> dict | None` — full concept/mechanism/principle payload
    - `get_family_principles_summary() -> dict` — active family principle count + title

[FLOW]
1. Instantiation walks `codex/doctrine/mechanisms/mech_*.json`, `concepts/con_*.json`, and the active
   phase `raw_seed_principles.json` file (best-effort fallback if not present).
2. Reverse indices map: path → mechanisms → concepts → principles.
3. Per-file enrichment resolves all of these in O(1) dict lookups.
4. Related files are the union of siblings that share at least one mechanism or one concept.

[DEPENDENCIES]
- stdlib only (json, pathlib, glob, typing)
- Filesystem under `codex/doctrine/` and active `obsidian/` phase family.

[CONSTRAINTS]
- Read-only. No mutation, no kernel imports, no heavy runtime.
- Gracefully degrades if doctrine files are missing (returns empty envelopes, not errors).
- Caches are loaded once per service instance; the caller owns refresh cadence.
- Limits on returned items (default 8 mechanisms, 8 concepts, 12 related files) keep payloads compact.
- When-needed: Open when an inspector or server route needs file-to-doctrine enrichment without opening mechanism, concept, and principle JSONs by hand.
- Escalates-to: system/server/inspector.py::InspectorService.inspect_file; system/server/schemas.py::DoctrineDetailSchema; codex/doctrine/system_map.json
- Navigation-group: server_backend
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("server.doctrine_enrichment")

_MAX_MECHANISMS = 8
_MAX_CONCEPTS = 8
_MAX_PRINCIPLES = 8
_MAX_RELATED = 12
_MAX_FOCUS_LINES = 4


class DoctrineEnrichmentService:
    """
    [ROLE]
    - Teleology: Central doctrine-to-file enrichment service shared by the inspector HTTP routes.
    - Ownership: Server singleton; initialized alongside `InspectorService` in main.py.
    - Mutability: Caches mechanisms/concepts/principles once at init; methods are read-only.
    - Concurrency: Safe for concurrent reads (no shared mutable state after init).
    - When-needed: Open when backend inspection flows need one cached doctrine index instead of repeated ad hoc scans of doctrine JSON.
    - Escalates-to: system/server/inspector.py::InspectorService; codex/doctrine/system_map.json
    """

    def __init__(self, repo_root: Path):
        self.root = Path(repo_root)
        self._mechanisms_by_id: Dict[str, Dict[str, Any]] = {}
        self._mechanisms_by_path: Dict[str, List[Dict[str, Any]]] = {}
        self._concepts_by_id: Dict[str, Dict[str, Any]] = {}
        self._principles_by_id: Dict[str, Dict[str, Any]] = {}
        self._concept_to_mechanisms: Dict[str, Set[str]] = {}
        self._mechanism_to_concepts: Dict[str, Set[str]] = {}
        self._concept_to_principles: Dict[str, Set[str]] = {}
        self._principle_source: Optional[str] = None
        self._active_family: Optional[str] = None
        self._load_all()

    # ------------------------------------------------------------------
    # INIT LOADERS
    # ------------------------------------------------------------------

    def _load_all(self) -> None:
        try:
            self._load_mechanisms()
            self._load_concepts()
            self._load_principles()
            self._build_reverse_indices()
            logger.info(
                "DoctrineEnrichmentService ready: %d mechanisms (%d paths), %d concepts, %d principles",
                len(self._mechanisms_by_id),
                len(self._mechanisms_by_path),
                len(self._concepts_by_id),
                len(self._principles_by_id),
            )
        except Exception:
            logger.exception("DoctrineEnrichmentService init failed; continuing with empty caches")

    def _load_mechanisms(self) -> None:
        mech_dir = self.root / "codex" / "doctrine" / "mechanisms"
        if not mech_dir.exists():
            return
        for mf in sorted(mech_dir.glob("mech_*.json")):
            data = _safe_load_json(mf)
            if not isinstance(data, dict):
                continue
            mid = str(data.get("id") or "").strip()
            if not mid:
                continue
            data["_source_file"] = f"codex/doctrine/mechanisms/{mf.name}"
            self._mechanisms_by_id[mid] = data
            loci = data.get("code_loci", [])
            if isinstance(loci, list):
                for locus in loci:
                    if not isinstance(locus, dict):
                        continue
                    path = _normalize_path(locus.get("path"))
                    if not path:
                        continue
                    entry = {
                        "mechanism_id": mid,
                        "title": str(data.get("title", "")),
                        "statement": str(data.get("statement", "")),
                        "role": str(locus.get("role", "")),
                        "functions": list(locus.get("functions") or []),
                        "source_file": data["_source_file"],
                        "tags": list(data.get("tags") or []),
                        "scope": str(data.get("scope", "")),
                        "status": str(data.get("status", "")),
                        "drift_sensitivity": str(data.get("drift_sensitivity", "")),
                    }
                    self._mechanisms_by_path.setdefault(path, []).append(entry)

    def _load_concepts(self) -> None:
        con_dir = self.root / "codex" / "doctrine" / "concepts"
        if not con_dir.exists():
            return
        for cf in sorted(con_dir.glob("con_*.json")):
            data = _safe_load_json(cf)
            if not isinstance(data, dict):
                continue
            cid = str(data.get("id") or "").strip()
            if not cid:
                continue
            data["_source_file"] = f"codex/doctrine/concepts/{cf.name}"
            self._concepts_by_id[cid] = data

    def _load_principles(self) -> None:
        # Try system_map first (fast path, already computed)
        sm_path = self.root / "codex" / "doctrine" / "system_map.json"
        sm = _safe_load_json(sm_path) if sm_path.exists() else None
        if isinstance(sm, dict):
            identity = sm.get("identity") or {}
            self._active_family = str(identity.get("active_family") or "")
            principles = sm.get("principles")
            if isinstance(principles, list):
                for p in principles:
                    if not isinstance(p, dict):
                        continue
                    pid = str(p.get("id") or "").strip()
                    if pid:
                        self._principles_by_id[pid] = p
                self._principle_source = "system_map"

        # If system_map didn't have full principle records, try the active phase raw_seed_principles.json
        phase_dir = self._resolve_active_phase_dir()
        if phase_dir is not None:
            rsp = phase_dir / "raw_seed" / "raw_seed_principles.json"
            rsp_data = _safe_load_json(rsp) if rsp.exists() else None
            if isinstance(rsp_data, dict):
                pr_list = rsp_data.get("principles")
                if isinstance(pr_list, list):
                    for p in pr_list:
                        if not isinstance(p, dict):
                            continue
                        pid = str(p.get("id") or "").strip()
                        if pid:
                            existing = self._principles_by_id.get(pid, {})
                            existing.update(p)
                            self._principles_by_id[pid] = existing
                    self._principle_source = "raw_seed_principles"

    def _resolve_active_phase_dir(self) -> Optional[Path]:
        # Best-effort: active family = highest numbered phase family in obsidian/okay lets do this/
        base = self.root / "obsidian" / "okay lets do this"
        if not base.exists():
            return None
        try:
            families = sorted(
                [p for p in base.iterdir() if p.is_dir() and not p.name.startswith(".")],
                reverse=True,
            )
        except OSError:
            return None
        for fam in families:
            if (fam / "raw_seed").exists() or (fam / "raw_seed.md").exists():
                return fam
        return families[0] if families else None

    def _build_reverse_indices(self) -> None:
        # concept → mechanisms (from mechanism.concept_edges)
        for mid, mech in self._mechanisms_by_id.items():
            edges = mech.get("concept_edges") or []
            if not isinstance(edges, list):
                continue
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                target = str(edge.get("target") or "").strip()
                if not target:
                    continue
                self._concept_to_mechanisms.setdefault(target, set()).add(mid)
                self._mechanism_to_concepts.setdefault(mid, set()).add(target)

        # concept → principles (from concept.principle_edges)
        for cid, concept in self._concepts_by_id.items():
            p_edges = concept.get("principle_edges") or []
            if not isinstance(p_edges, list):
                continue
            for edge in p_edges:
                if edge is None:
                    continue
                if isinstance(edge, dict):
                    target = str(edge.get("target") or "").strip()
                else:
                    target = str(edge).strip()
                if target:
                    self._concept_to_principles.setdefault(cid, set()).add(target)

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def get_file_doctrine(self, rel_path: str) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: Return the compact doctrine envelope for a single file path.
        - Guarantee: Always returns a dict with the shape described below, even if empty.
        - When-needed: Open when a file-detail response needs mechanism, concept, principle, and related-file cards for one repo-relative path.
        - Escalates-to: system/server/main.py::get_codex_file; system/server/schemas.py::CodexFileDetailSchema

        Returns:
          {
            "mechanisms": [{mechanism_id, title, statement, role, functions[], tags[], source_file, scope, status, drift_sensitivity}, ...],
            "concepts":   [{id, title, statement, tags[], source_file, via_mechanism_ids[]}, ...],
            "principles": [{id, title, statement, tags[], via_concept_ids[]}, ...],
            "related_files": [{path, via_mechanism, mechanism_title, role}, ...],
            "counts": {mechanisms, concepts, principles, related_files},
          }
        """
        rel_path = _normalize_path(rel_path) or ""
        mechanism_entries = self._mechanisms_by_path.get(rel_path, [])
        if not mechanism_entries:
            return _empty_envelope()

        mechanisms_out: List[Dict[str, Any]] = []
        seen_mids: Set[str] = set()
        for entry in mechanism_entries:
            mid = entry["mechanism_id"]
            if mid in seen_mids:
                continue
            seen_mids.add(mid)
            mechanisms_out.append({
                "mechanism_id": mid,
                "title": entry["title"],
                "statement": _truncate(entry["statement"], 280),
                "role": entry["role"],
                "functions": entry["functions"][:6],
                "tags": entry["tags"][:6],
                "source_file": entry["source_file"],
                "scope": entry["scope"],
                "status": entry["status"],
                "drift_sensitivity": entry["drift_sensitivity"],
            })
            if len(mechanisms_out) >= _MAX_MECHANISMS:
                break

        # Concepts via mechanism.concept_edges
        concept_via: Dict[str, List[str]] = {}
        for mid in seen_mids:
            for cid in self._mechanism_to_concepts.get(mid, set()):
                concept_via.setdefault(cid, []).append(mid)

        concepts_out: List[Dict[str, Any]] = []
        for cid, via_mids in concept_via.items():
            concept = self._concepts_by_id.get(cid)
            if not concept:
                continue
            concepts_out.append({
                "id": cid,
                "title": str(concept.get("title", "")),
                "statement": _truncate(str(concept.get("statement", "")), 260),
                "tags": list(concept.get("tags") or [])[:6],
                "source_file": concept.get("_source_file", ""),
                "via_mechanism_ids": via_mids[:4],
                "scope": str(concept.get("scope", "")),
                "status": str(concept.get("status", "")),
            })
        concepts_out.sort(key=lambda x: x["id"])
        concepts_out = concepts_out[:_MAX_CONCEPTS]

        # Principles via concept.principle_edges
        principle_via: Dict[str, List[str]] = {}
        for cid in concept_via:
            for pid in self._concept_to_principles.get(cid, set()):
                principle_via.setdefault(pid, []).append(cid)

        principles_out: List[Dict[str, Any]] = []
        for pid, via_cids in principle_via.items():
            principle = self._principles_by_id.get(pid, {})
            principles_out.append({
                "id": pid,
                "title": str(principle.get("title", "")),
                "statement": _truncate(str(principle.get("statement", "")), 240),
                "tags": list(principle.get("tags") or [])[:6] if isinstance(principle.get("tags"), list) else [],
                "via_concept_ids": via_cids[:4],
            })
        principles_out.sort(key=lambda x: x["id"])
        principles_out = principles_out[:_MAX_PRINCIPLES]

        # Related files: other files with at least one shared mechanism
        related: List[Dict[str, Any]] = []
        related_seen: Set[Tuple[str, str]] = set()
        for mid in seen_mids:
            mech = self._mechanisms_by_id.get(mid, {})
            loci = mech.get("code_loci", [])
            if not isinstance(loci, list):
                continue
            for locus in loci:
                if not isinstance(locus, dict):
                    continue
                other = _normalize_path(locus.get("path"))
                if not other or other == rel_path:
                    continue
                key = (other, mid)
                if key in related_seen:
                    continue
                related_seen.add(key)
                related.append({
                    "path": other,
                    "via_mechanism": mid,
                    "mechanism_title": str(mech.get("title", "")),
                    "role": str(locus.get("role", "")),
                })
                if len(related) >= _MAX_RELATED:
                    break
            if len(related) >= _MAX_RELATED:
                break

        return {
            "mechanisms": mechanisms_out,
            "concepts": concepts_out,
            "principles": principles_out,
            "related_files": related,
            "counts": {
                "mechanisms": len(mechanisms_out),
                "concepts": len(concepts_out),
                "principles": len(principles_out),
                "related_files": len(related),
            },
        }

    def get_doctrine_detail(self, doctrine_id: str) -> Optional[Dict[str, Any]]:
        """
        [ACTION]
        - Teleology: Return the full normalized doctrine payload for any mechanism, concept, or principle id.
        - Guarantee: Returns None if the id is not recognized.
        - When-needed: Open when the inspector drawer already has a doctrine id and needs the full normalized payload behind that card.
        - Escalates-to: system/server/main.py::get_codex_doctrine_detail; system/server/schemas.py::DoctrineDetailSchema; codex/doctrine/system_map.json
        """
        doctrine_id = (doctrine_id or "").strip()
        if not doctrine_id:
            return None
        if doctrine_id.startswith("mech_"):
            data = self._mechanisms_by_id.get(doctrine_id)
            if not data:
                return None
            return self._project_mechanism(data)
        if doctrine_id.startswith("con_"):
            data = self._concepts_by_id.get(doctrine_id)
            if not data:
                return None
            return self._project_concept(data)
        if doctrine_id.startswith("pri_"):
            data = self._principles_by_id.get(doctrine_id)
            if not data:
                return None
            return self._project_principle(data)
        return None

    def _project_mechanism(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "kind": "mechanism",
            "id": data.get("id"),
            "title": data.get("title", ""),
            "statement": data.get("statement", ""),
            "scope": data.get("scope", ""),
            "status": data.get("status", ""),
            "drift_sensitivity": data.get("drift_sensitivity", ""),
            "tags": list(data.get("tags") or []),
            "code_loci": list(data.get("code_loci") or [])[:10],
            "concept_edges": list(data.get("concept_edges") or [])[:10],
            "upstream": list(data.get("upstream") or [])[:10],
            "downstream": list(data.get("downstream") or [])[:10],
            "evidence": list(data.get("evidence") or [])[:6],
            "tests": list(data.get("tests") or [])[:6],
            "failure_modes": list(data.get("failure_modes") or [])[:6],
            "decision_examples": list(data.get("decision_examples") or [])[:4],
            "note": _truncate(str(data.get("note") or ""), 800),
            "source_file": data.get("_source_file", ""),
        }

    def _project_concept(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "kind": "concept",
            "id": data.get("id"),
            "title": data.get("title", ""),
            "statement": data.get("statement", ""),
            "scope": data.get("scope", ""),
            "status": data.get("status", ""),
            "tags": list(data.get("tags") or []),
            "principle_edges": [e for e in (data.get("principle_edges") or []) if e is not None][:10],
            "mechanism_edges": list(data.get("mechanism_edges") or [])[:10],
            "evidence": list(data.get("evidence") or [])[:6],
            "tests": list(data.get("tests") or [])[:6],
            "failure_modes": list(data.get("failure_modes") or [])[:6],
            "decision_examples": list(data.get("decision_examples") or [])[:4],
            "note": _truncate(str(data.get("note") or ""), 800),
            "source_file": data.get("_source_file", ""),
        }

    def _project_principle(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "kind": "principle",
            "id": data.get("id"),
            "title": data.get("title", ""),
            "statement": data.get("statement", ""),
            "scope": data.get("scope", ""),
            "status": data.get("status", ""),
            "tags": list(data.get("tags") or []),
            "edges": list(data.get("edges") or [])[:10],
            "evidence": list(data.get("evidence") or [])[:6],
            "failure_modes": list(data.get("failure_modes") or [])[:6],
            "decision_examples": list(data.get("decision_examples") or [])[:4],
            "note": _truncate(str(data.get("note") or ""), 800),
            "source_file": "",
        }

    def get_summary(self) -> Dict[str, Any]:
        """
        [ACTION]
        - Teleology: Return a compact service summary for health / debug views.
        - When-needed: Open when a backend health or debug surface needs doctrine cache counts without fetching any per-file enrichment.
        - Escalates-to: system/server/inspector.py::InspectorService.get_doctrine_service; codex/doctrine/system_map.json
        """
        return {
            "mechanisms": len(self._mechanisms_by_id),
            "mechanism_paths": len(self._mechanisms_by_path),
            "concepts": len(self._concepts_by_id),
            "principles": len(self._principles_by_id),
            "active_family": self._active_family,
            "principle_source": self._principle_source,
        }


# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------


def _safe_load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _normalize_path(raw: Any) -> str:
    if raw is None:
        return ""
    s = str(raw).strip().replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _empty_envelope() -> Dict[str, Any]:
    return {
        "mechanisms": [],
        "concepts": [],
        "principles": [],
        "related_files": [],
        "counts": {"mechanisms": 0, "concepts": 0, "principles": 0, "related_files": 0},
    }
