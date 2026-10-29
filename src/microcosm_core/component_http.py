"""Read-only, snapshot-backed HTTP API for the existing component claim index.

Only startup and explicit replacement read an index or opt-in saved evidence.
Requests use immutable encoded views and precomputed adjacency, never a
filesystem root or runner. Optional saved evidence reuses the admission owner.
"""
from __future__ import annotations

import argparse
import base64
from collections import OrderedDict, defaultdict, deque
import copy
import hashlib
import gzip
import ipaddress
import io
import json
from pathlib import Path
import re
from socketserver import ThreadingMixIn
import sys
import threading
import time
from types import MappingProxyType
from urllib.parse import parse_qsl
from wsgiref.simple_server import ServerHandler, WSGIRequestHandler, WSGIServer, make_server

from microcosm_core import component_api_contract, component_index, resource_root
from microcosm_core.schemas import loads_json_strict

API_SCHEMA = component_api_contract.API_SCHEMA
API_PREFIX = component_api_contract.API_PREFIX
MAX_INDEX_BYTES = 16 * 1024 * 1024
MAX_OVERVIEW_BYTES = component_api_contract.MAX_OVERVIEW_BYTES
MAX_QUERY_BYTES = 2048
MAX_CURSOR_BYTES = 512
MAX_PAGE_SIZE = component_api_contract.MAX_PAGE_SIZE
MAX_GRAPH_DEPTH = component_api_contract.MAX_GRAPH_DEPTH
MAX_GRAPH_EDGES = component_api_contract.MAX_GRAPH_EDGES
MAX_SEARCH_LENGTH = component_api_contract.MAX_SEARCH_LENGTH
_CLASSIFICATION_FIELDS = component_api_contract.CLASSIFICATION_FIELDS
_LABEL = re.compile(r"[a-z][a-z0-9_]*\Z")
_CORE = re.compile(r"[a-z][a-z0-9_]*\Z")
_PROOF = re.compile(r"proof::dafny::[a-z][a-z0-9_]*\Z")
_CLAIM = re.compile(r"claim::[a-z][a-z0-9_]*\Z")
_RULE = re.compile(r"(?:AX|P|AP)-[0-9]{1,3}\Z")
_RULE_KINDS = ("axiom", "principle", "anti_principle")
_CITATION_FIELDS = {"axiom": "axiom_refs", "principle": "principle_refs"}
_BAD_ESCAPE = re.compile(r"%(?![a-fA-F0-9]{2})")
_ABSOLUTE = re.compile(r"(?<![A-Za-z0-9_./])/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*")
_ID_FIELD = {"organ": "organ_id", "claim": "claim_id", "source_file": "path",
             "route": "task_class", "family": "family_id", "guide": "guide_id",
             "replay": "replay_id", "subclaim": "subclaim_id", "proof": "proof_id",
             "specification": "specification_id", "artifact": "artifact_id",
             "doctrine_ref": "value"}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _response_encoding(value):
    """Select an accepted representation; absent negotiation means identity."""
    if not value:
        return "identity"
    if len(value) > 2048:
        _bad("encoding header exceeds permitted length")
    qualities = {}
    for entry in value.split(","):
        token, *parameters = entry.lower().strip().split(";")
        quality = 1.0
        for parameter in parameters:
            name, sep, raw = parameter.strip().partition("=")
            if name == "q" and sep:
                if not re.fullmatch(r"(?:0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)", raw):
                    quality = 0.0
                else:
                    quality = float(raw)
        qualities[token.strip()] = quality
    gz = qualities.get("gzip", qualities.get("*", 0.0))
    identity = qualities.get("identity", 0.0 if qualities.get("*") == 0 else 1.0)
    if gz > 0 and ("identity" not in qualities or gz >= identity):
        return "gzip"
    if identity > 0:
        return "identity"
    raise APIError(406, "encoding_not_acceptable", "accept gzip or identity encoding")


def _encoded_response(body, encoding):
    if encoding == "gzip":
        body = gzip.compress(body, compresslevel=6, mtime=0)
    return body, '"' + hashlib.sha256(body).hexdigest() + '"'


class APIError(Exception):
    """A bounded public error, containing no filesystem exception details."""

    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


def _bad(message="invalid query parameters"):
    raise APIError(400, "invalid_parameters", message)


def _number(value, default, maximum):
    if value is None:
        return default
    if not re.fullmatch(r"[0-9]{1,5}", value) or not 1 <= int(value) <= maximum:
        _bad("integer parameter outside its permitted range")
    return int(value)


def _edge_key(edge):
    return tuple(sorted(edge.items()))


def _rule_key(identity):
    prefix, _, number = identity.partition("-")
    return (prefix, int(number))


def _doctrine_views(index):
    """Precompute rule rows and details from validated doctrine and citation edges."""
    doctrine = index.get("explorer", {}).get("doctrine", {})
    nodes = doctrine.get("nodes", [])
    kinds = {row["id"]: row["kind"] for row in nodes}
    citations = defaultdict(list)
    for edge in index["edges"]:
        if (edge["kind"] == "grounded_in_doctrine" and edge["to"] in kinds
                and edge.get("ref_kind") in _CITATION_FIELDS):
            citations[edge["to"]].append({
                "component_id": edge["from"], "ref_kind": edge["ref_kind"],
                "basis": "authored_atlas_row",
                "source_ref": "core/organ_atlas.json::organs[{}].{}".format(
                    edge["from"], _CITATION_FIELDS[edge["ref_kind"]])})
    related = {identity: {"rests_on": set(), "violates": set(), "principles": set(), "failure_modes": set()}
               for identity in kinds}
    for edge in doctrine.get("edges", []):
        source, target = edge["from_id"], edge["to_id"]
        if edge["kind"] == "rests_on":
            related[source]["rests_on"].add(target)
            related[target]["principles"].add(source)
        else:
            related[source]["violates"].add(target)
            related[target]["failure_modes"].add(source)
    # A failure mode names the axioms it would break. A component is exposed
    # to it when its atlas row cites one of those axioms: derived from two
    # authored relations, not a check and not an observed incident.
    exposure = {}
    for identity, kind in kinds.items():
        if kind != "anti_principle":
            continue
        through = defaultdict(set)
        for axiom_id in related[identity]["violates"]:
            for row in citations[axiom_id]:
                through[row["component_id"]].add(axiom_id)
        exposure[identity] = [{"component_id": component_id,
                               "through_axiom_ids": sorted(axioms, key=_rule_key),
                               "basis": "derived_from_violated_axiom_citations"}
                              for component_id, axioms in sorted(through.items())]
    rules, details = [], {}
    for node in nodes:
        identity = node["id"]
        exposed = exposure.get(identity, [])
        cited = sorted(citations[identity], key=lambda row: (row["component_id"], row["ref_kind"]))
        component_ids = sorted({row["component_id"] for row in cited})
        lists = {key: sorted(value, key=_rule_key) for key, value in related[identity].items()}
        axiom = node.get("axiom")
        rules.append({**{key: node[key] for key in ("id", "kind", "title", "plain", "source_ref")},
                      "component_ids": component_ids, "cited_by_count": len(component_ids),
                      "witness_component_ids": list(axiom["routing"]["witness_component_ids"]) if axiom else [],
                      **lists, "support_verdict": axiom["support"]["verdict"] if axiom else None,
                      "reader_plain": node["reader"]["plain"],
                      "enforced_in_component_ids": list(node["reader"]["enforced_in_component_ids"]),
                      "exposed_component_ids": [row["component_id"] for row in exposed],
                      "exposed_count": len(exposed)})
        details[identity] = {**copy.deepcopy(node), "component_ids": component_ids,
                             "cited_by_count": len(component_ids), "citations": cited, **lists,
                             "exposure": copy.deepcopy(exposed), "exposed_count": len(exposed)}
    counts = {kind: sum(1 for row in nodes if row["kind"] == kind) for kind in _RULE_KINDS}
    counts["citations"] = sum(len(rows) for rows in citations.values())
    listing = {"rules": rules, "edges": copy.deepcopy(doctrine.get("edges", [])),
               "sources": copy.deepcopy(doctrine.get("sources", [])), "counts": counts}
    return listing, details


def _overview_record(record):
    """Retain guide identity and plain lead; full Markdown belongs to detail."""
    result = dict(record)
    if isinstance(result.get("guide"), dict):
        result["guide"] = {**result["guide"], "text": None}
    if isinstance(result.get("proof"), dict):
        result["proof"] = _overview_record(result["proof"])
    return result


def _overview_explorer(explorer):
    result = {key: value for key, value in explorer.items() if key != "guides"}
    if "cores" in result:
        result["cores"] = [_overview_record(row) for row in result["cores"]]
    return result


def _map_receipt(receipt):
    """Keep only the receipt identity and recorded facts read by the map."""
    result = {key: value for key, value in receipt.items()
              if key in {"ref", "artifact_id", "availability", "kind", "reason"}}
    if "summary" in receipt:
        summary = receipt["summary"]
        result["summary"] = {key: value for key, value in summary.items()
                             if key in {"created_at", "date_status", "availability_reason"}}
        result["summary"]["recorded_fields"] = {
            key: value for key, value in summary["recorded_fields"].items()
            if key in {"status", "fixture_id", "case_count"}}
    return result


def _map_overview(overview):
    """Project the initial map payload once; the complete overview stays intact."""
    result = {key: value for key, value in overview.items() if key not in {"receipts", "wiring"}}
    result["components"] = [{**row, "receipt_refs": [_map_receipt(receipt) for receipt in row["receipt_refs"]]}
                            for row in overview["components"]]
    retained_cores = overview["explorer"].get("cores", [])
    if retained_cores:
        # The map reader gives explorer.cores precedence. Preserve that order
        # when replacing the duplicate with the enriched top-level records.
        cores_by_id = {row["core_id"]: row for row in overview["cores"]}
        result["cores"] = [cores_by_id[row["core_id"]] for row in retained_cores]
    result["explorer"] = {key: value for key, value in overview["explorer"].items()
                          if key not in {"receipt_summaries", "proof_details", "cores"}}
    return result


def _public_text(value, field=""):
    """Reject host paths in text too, retaining declared portable /tmp examples."""
    if isinstance(value, str):
        if re.search(r"[A-Za-z]:[\\/]|\\\\|(?i:file://)|(?<!:)//", value):
            raise ValueError("host path in public snapshot")
        for match in _ABSOLUTE.finditer(value.replace("<run>", "RUN").replace("<slug>", "SLUG")):
            if not (field in {"command", "first_command", "validator_command"}
                    and match.group().startswith("/tmp/")):
                raise ValueError("host path in public snapshot")
    elif isinstance(value, dict):
        for key, child in value.items():
            _public_text(key)
            _public_text(child, key)
    elif isinstance(value, list):
        for child in value:
            _public_text(child, field)


class ComponentSnapshot:
    """Private preindexed copies of one validated public index revision."""

    def __setattr__(self, name, value):
        if getattr(self, "_sealed", False):
            raise AttributeError("component snapshots are immutable")
        object.__setattr__(self, name, value)

    def __init__(self, index, *, fresh_runs=None, evidence_root=None, local_run_evidence=None):
        # Detach before validation: later caller mutation cannot change requests.
        index = copy.deepcopy(index)
        canonical = _json(index)
        if len(canonical) > MAX_INDEX_BYTES:
            raise ValueError("component index exceeds snapshot size limit")
        views = component_index.compile_views(index)
        # Source text exceptions are admitted by the strict index validator first.
        from microcosm_core.component_explorer_validation import public_text_view
        _public_text(public_text_view(index))
        from microcosm_core.component_local_evidence import load_local_run_evidence, validate_local_run_evidence
        if local_run_evidence is not None:
            if fresh_runs is not None or evidence_root is not None:
                raise ValueError("choose one explicit local evidence source")
            local_runs = copy.deepcopy(local_run_evidence)
        else:
            if evidence_root is not None and fresh_runs is None:
                raise ValueError("evidence root requires explicit saved-run directory")
            root = evidence_root if evidence_root is not None else (
                resource_root.microcosm_root() if fresh_runs is not None else None)
            local_runs = load_local_run_evidence(root, index, fresh_runs)
        validate_local_run_evidence(local_runs, index)
        encoded_runs = _json(local_runs)
        if len(encoded_runs) > 1024 * 1024:
            raise ValueError("local evidence summary exceeds response limit")
        self.local_runs = encoded_runs
        revision_bytes = canonical if local_runs["status"] == "disabled" else _json({"index": index, "local_runs": local_runs})
        self.revision = hashlib.sha256(revision_bytes).hexdigest()
        summaries = views["list"]
        organs = {row["organ_id"]: row for row in index["nodes"]["organ"]}
        self.components, self.summaries = {}, {}
        for row in summaries:
            identity = row["organ_id"]
            classification = {key: organs[identity][key] for key in _CLASSIFICATION_FIELDS}
            view = views["by_component"][identity]
            view["classification"] = row["classification"] = classification
            self.components[identity], self.summaries[identity] = _json(view), _json(row)
        self.claims = {row["claim_id"]: _json(row) for row in index["nodes"]["claim"]}
        self.proofs = {identity: _json(view) for identity, view in views["by_proof"].items()}
        self.filters = {key: defaultdict(set) for key in _CLASSIFICATION_FIELDS}
        for row in index["nodes"]["organ"]:
            for key in _CLASSIFICATION_FIELDS:
                self.filters[key][row[key]].add(row["organ_id"])
        self.ids = tuple(sorted(self.components))
        self.search_text = MappingProxyType({row["organ_id"]: "\n".join(
            row[field] for field in ("organ_id", "title", "summary")).casefold()
            for row in summaries})
        self.nodes = {}
        for kind, rows in index["nodes"].items():
            for row in rows:
                self.nodes[(kind, row[_ID_FIELD[kind]])] = _json(row)
        doctrine = index.get("explorer", {}).get("doctrine", {})
        for row in doctrine.get("nodes", []):
            self.nodes[("doctrine_ref", row["id"])] = _json({"value": row["id"], **row})
        artifacts = {row["artifact_id"]: row for row in index["nodes"]["artifact"]}
        receipt_ids = {edge[side] for edge in index["edges"] for side in ("from", "to")
                       if edge[side + "_type"] == "receipt"}
        self.receipts_by_component = {}
        for key, view in views["by_component"].items():
            refs = view["claim"]["card"]["evidence"]
            self.receipts_by_component[key] = tuple(sorted({refs["authority_receipt_ref"],
                                                          *refs["historical_receipt_refs"]}))
            # Validated card evidence can include omitted assets without graph edges.
            receipt_ids.update(self.receipts_by_component[key])
        receipt_summaries = {row["ref"]: row for row in
                             index.get("explorer", {}).get("receipt_summaries", [])}
        receipt_views = {key: {**artifacts[key], **(
            {"summary": receipt_summaries[key]} if key in receipt_summaries else {})}
                         for key in sorted(receipt_ids)}
        self.receipts = {key: _json(value) for key, value in receipt_views.items()}
        self.cores = {key: _json(value) for key, value in views.get("cores", {}).items()}
        self.coverage = _json(views["coverage"])
        doctrine_listing, doctrine_details = _doctrine_views(index)
        self.doctrine = _json(doctrine_listing)
        self.rules = {key: _json(value) for key, value in doctrine_details.items()}
        outgoing_by_component, routes_by_component = defaultdict(list), defaultdict(set)
        for edge in index["edges"]:
            if edge["from_type"] == "organ":
                outgoing_by_component[edge["from"]].append(edge)
            if edge["from_type"] == "route" and edge["to_type"] == "organ":
                routes_by_component[edge["to"]].add(edge["from"])
        summary_by_id = {row["organ_id"]: row for row in summaries}
        overview_components = []
        for identity in self.ids:
            row = dict(summary_by_id[identity])
            view = views["by_component"][identity]
            outgoing = outgoing_by_component[identity]
            row.update(proof_ids=[item["proof"]["proof_id"] for item in view["proofs"]],
                       receipt_refs=[receipt_views[key]
                                     for key in self.receipts_by_component[identity]],
                       wires_to=sorted(edge["to"] for edge in outgoing if edge["kind"] == "wires_to"),
                       doctrine_ref_ids=sorted({edge["to"] for edge in outgoing
                                                if edge["to_type"] == "doctrine_ref"}),
                       route_ids=sorted(routes_by_component[identity]))
            overview_components.append(row)
        overview = {"components": overview_components,
                    "kernels": [_overview_record(views["by_proof"][key]) for key in sorted(self.proofs)],
                    "receipts": [receipt_views[key] for key in sorted(self.receipts)],
                    "wiring": [dict(edge) for edge in index["edges"] if edge["kind"] == "wires_to"],
                    "coverage": views["coverage"],
                    "cores": [_overview_record(views["cores"][key]) for key in sorted(self.cores)],
                    "local_runs": local_runs,
                    "explorer": _overview_explorer(views.get("explorer", index.get("explorer", {})))}
        self.overview = _json(self.envelope(overview))
        if len(self.overview) > MAX_OVERVIEW_BYTES:
            raise ValueError("component overview exceeds encoded response limit")
        self.overview_etag = '"' + hashlib.sha256(self.overview).hexdigest() + '"'
        self.overview_gzip, self.overview_gzip_etag = _encoded_response(self.overview, "gzip")
        self.map_overview, self.map_overview_etag = _encoded_response(
            _json(self.envelope(_map_overview(overview))), "identity")
        self.map_overview_gzip, self.map_overview_gzip_etag = _encoded_response(self.map_overview, "gzip")
        doctrine_edges = [{"kind": row["kind"], "from_type": "doctrine_ref",
                           "from": row["from_id"], "to_type": "doctrine_ref", "to": row["to_id"],
                           "source_ref": row["source_ref"]} for row in doctrine.get("edges", [])]
        self.edges = tuple(sorted([*index["edges"], *doctrine_edges], key=_edge_key))
        self.edge_kinds = frozenset([*index["graph"]["edge_kinds"],
                                    *(row["kind"] for row in doctrine_edges)])
        adjacency = defaultdict(list)
        for position, edge in enumerate(self.edges):
            for side, direction in (("from", "out"), ("to", "in")):
                node = (edge[side + "_type"], edge[side])
                if node not in self.nodes:
                    self.nodes[node] = _json(artifacts[edge[side]] if node[0] == "receipt"
                                             else {"value": node[1]})
                for selected in (None, edge["kind"]):
                    adjacency[(node, direction, selected)].append(position)
                    adjacency[(node, "both", selected)].append(position)
        self.adjacency = {key: tuple(sorted(set(value))) for key, value in adjacency.items()}
        self.graph_types = frozenset(kind for kind, _ in self.nodes)
        self.metadata = {"index_schema": index["schema_version"],
                         "component_count": len(self.components), "proof_count": len(self.proofs),
                         "receipt_count": len(self.receipts),
                         "component_filters": {key: [{"value": value, "component_count": len(ids)}
                                                     for value, ids in sorted(lookup.items(), key=lambda row: str(row[0]))]
                                               for key, lookup in self.filters.items()},
                         "graph": copy.deepcopy(index["graph"]),
                         "evidence_state": {"index_state": "retained_generated_snapshot",
                                            "current_backend_binding": {"status": "not_checked"},
                                            "fresh_prover": {"status": "not_recorded_by_index"},
                                            "fresh_replay": {"status": "not_recorded_by_index"}},
                         "limits": {"page_size": MAX_PAGE_SIZE, "graph_depth": MAX_GRAPH_DEPTH,
                                    "graph_edges": MAX_GRAPH_EDGES, "search_length": MAX_SEARCH_LENGTH,
                                    "overview_bytes": MAX_OVERVIEW_BYTES},
                         "contract": {"openapi": API_PREFIX + "/openapi.json",
                                      "version": component_api_contract.CONTRACT_VERSION},
                         "execution": "unavailable_over_http"}
        self.metadata["graph"]["edge_kinds"] = sorted(self.edge_kinds)
        counts = defaultdict(int)
        for edge in self.edges:
            counts[edge["kind"]] += 1
        self.metadata["graph"]["edge_kind_counts"] = dict(sorted(counts.items()))
        if doctrine_edges:
            self.metadata["graph"]["edge_semantics"].update({
                "rests_on": "Authored principle cites an axiom as its basis; not a formal implication.",
                "violates": "Authored anti-principle identifies an axiom it violates; not an observed incident.",
                "failure_mode_exposure": ("Derived: a component is exposed to a failure mode when its atlas row "
                                          "cites an axiom the failure mode violates; not a check and not an "
                                          "observed incident.")})
        labels = index.get("explorer", {}).get("component_filters", {})
        for key, rows in self.metadata["component_filters"].items():
            owned = {row["value"]: row for row in labels.get(key, [])}
            for row in rows:
                if row["value"] in owned:
                    row.update({field: owned[row["value"]][field]
                                for field in ("label", "description", "label_basis")
                                if field in owned[row["value"]]})
        if "source_revision" in index.get("explorer", {}):
            self.metadata["source_revision"] = copy.deepcopy(index["explorer"]["source_revision"])
        self.metadata["local_runs"] = {key: value for key, value in local_runs.items() if key != "runs"}
        self.metadata["local_runs"]["run_count"] = len(local_runs["runs"])
        self.metadata["core_count"] = len(self.cores)
        self.metadata["doctrine_count"] = len(self.rules)
        self.metadata = _json(self.metadata)
        self.edges = tuple(MappingProxyType(edge) for edge in self.edges)
        self.filters = {key: MappingProxyType({value: frozenset(ids) for value, ids in lookup.items()})
                        for key, lookup in self.filters.items()}
        for name in ("components", "summaries", "claims", "proofs", "filters",
                     "nodes", "receipts", "receipts_by_component", "adjacency", "cores", "rules"):
            setattr(self, name, MappingProxyType(getattr(self, name)))
        self._sealed = True

    def envelope(self, data):
        return {"schema_version": API_SCHEMA, "snapshot_revision": self.revision, "data": data}


def load_snapshot(index_file=None, *, fresh_runs=None, evidence_root=None):
    """Read one explicitly selected or packaged index; invalid input fails closed."""
    path = (Path(index_file) if index_file is not None
            else resource_root.microcosm_root() / component_index.INDEX_REF)
    if path.is_symlink() or not path.is_file():
        raise ValueError("component index must be a regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INDEX_BYTES + 1)
    if len(raw) > MAX_INDEX_BYTES:
        raise ValueError("component index exceeds snapshot size limit")
    return ComponentSnapshot(loads_json_strict(raw.decode("utf-8"), "component index"),
                             fresh_runs=fresh_runs, evidence_root=evidence_root)


def _parameters(raw):
    if (type(raw) is not str or len(raw.encode("utf-8")) > MAX_QUERY_BYTES
            or _BAD_ESCAPE.search(raw)):
        _bad("query string exceeds limits or has malformed encoding")
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True,
                          encoding="utf-8", errors="strict", max_num_fields=12)
    except (ValueError, UnicodeError):
        _bad("malformed query string")
    result = {}
    for key, value in pairs:
        if key in result or not key or not value or any(ord(c) < 32 or ord(c) == 127 for c in key + value):
            _bad()
        result[key] = value
    return result


def _allowed(query, names):
    if set(query) - set(names):
        _bad("unknown query parameter")


def _page(snapshot, encoded_rows, query, identity):
    limit = _number(query.get("limit"), 25, MAX_PAGE_SIZE)
    context = hashlib.sha256(_json([identity, limit])).hexdigest()
    offset = 0
    token = query.get("cursor")
    if token is not None:
        try:
            if len(token) > MAX_CURSOR_BYTES or not re.fullmatch(r"[A-Za-z0-9_-]+", token):
                raise ValueError()
            cursor = loads_json_strict(base64.b64decode(token + "=" * (-len(token) % 4),
                                                       altchars=b"-_", validate=True).decode("ascii"))
            if (type(cursor) is not dict or set(cursor) != {"revision", "context", "offset"}
                    or type(cursor["offset"]) is not int or cursor["offset"] < 0
                    or type(cursor["revision"]) is not str or not re.fullmatch("[0-9a-f]{64}", cursor["revision"])
                    or cursor["context"] != context):
                raise ValueError()
        except (ValueError, UnicodeError):
            raise APIError(400, "invalid_cursor", "cursor does not match this query") from None
        if cursor["revision"] != snapshot.revision:
            raise APIError(409, "stale_cursor", "snapshot changed; restart pagination")
        if cursor["offset"] > len(encoded_rows):
            raise APIError(400, "invalid_cursor", "cursor is outside this collection")
        offset = cursor["offset"]
    next_offset = offset + limit
    next_cursor = None
    if next_offset < len(encoded_rows):
        payload = _json({"revision": snapshot.revision, "context": context, "offset": next_offset})
        next_cursor = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
    return {"items": [json.loads(row) for row in encoded_rows[offset:next_offset]],
            "total": len(encoded_rows), "limit": limit, "next_cursor": next_cursor}


def _graph(snapshot, query):
    _allowed(query, {"type", "id", "depth", "max_edges", "direction", "edge_kind"})
    kind, identity = query.get("type"), query.get("id")
    if kind not in snapshot.graph_types or identity is None or len(identity) > 1000:
        _bad("graph requires a known type and bounded ID")
    root = (kind, identity)
    if root not in snapshot.nodes:
        raise APIError(404, "unknown_node", "unknown typed graph node")
    depth = _number(query.get("depth"), 1, MAX_GRAPH_DEPTH)
    cap = _number(query.get("max_edges"), 100, MAX_GRAPH_EDGES)
    direction, edge_kind = query.get("direction", "both"), query.get("edge_kind")
    if direction not in {"in", "out", "both"} or edge_kind is not None and edge_kind not in snapshot.edge_kinds:
        _bad("unknown graph direction or edge kind")
    queue, seen, selected, nodes = deque([(root, 0)]), {root}, set(), {root}
    truncated = False
    while queue and not truncated:
        node, level = queue.popleft()
        if level == depth:
            continue
        for position in snapshot.adjacency.get((node, direction, edge_kind), ()):
            if position in selected:
                continue
            if len(selected) == cap:
                truncated = True
                break
            selected.add(position)
            edge = snapshot.edges[position]
            for side in ("from", "to"):
                neighbor = (edge[side + "_type"], edge[side])
                nodes.add(neighbor)
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append((neighbor, level + 1))
    return {"root": {"type": kind, "id": identity}, "depth": depth,
            "max_edges": cap, "direction": direction, "edge_kind": edge_kind,
            "truncated": truncated,
            "nodes": [{"type": key[0], "id": key[1], "record": json.loads(snapshot.nodes[key])}
                      for key in sorted(nodes)],
            "edges": [dict(snapshot.edges[position]) for position in sorted(selected)]}


def _dispatch(snapshot, path, query):
    if path == API_PREFIX + "/openapi.json":
        _allowed(query, {})
        return component_api_contract.openapi_document()
    if path == API_PREFIX:
        _allowed(query, {})
        return json.loads(snapshot.metadata)
    if path == API_PREFIX + "/local-runs":
        _allowed(query, {})
        return json.loads(snapshot.local_runs)
    if path == API_PREFIX + "/graph":
        return _graph(snapshot, query)
    if path == API_PREFIX + "/coverage":
        _allowed(query, {})
        return json.loads(snapshot.coverage)
    if path == API_PREFIX + "/doctrine":
        _allowed(query, {})
        return json.loads(snapshot.doctrine)
    parts = path.removeprefix(API_PREFIX + "/").split("/")
    if not path.startswith(API_PREFIX + "/") or len(parts) not in (1, 2):
        raise APIError(404, "not_found", "unknown API route")
    resource = parts[0]
    if len(parts) == 2:
        _allowed(query, {})
        identity = parts[1]
        stores = {"components": (snapshot.components, _LABEL),
                  "claims": (snapshot.claims, _CLAIM), "proofs": (snapshot.proofs, _PROOF),
                  "cores": (snapshot.cores, _CORE), "doctrine": (snapshot.rules, _RULE)}
        if resource not in stores:
            raise APIError(404, "not_found", "unknown API route")
        store, pattern = stores[resource]
        if not pattern.fullmatch(identity):
            _bad("malformed resource ID")
        if identity not in store:
            raise APIError(404, "unknown_id", "unknown resource ID")
        return json.loads(store[identity])
    if resource == "components":
        _allowed(query, {*_CLASSIFICATION_FIELDS, "q", "limit", "cursor"})
        ids = set(snapshot.ids)
        search = query.get("q", "").strip().casefold()
        if "q" in query:
            if not search or len(query["q"]) > MAX_SEARCH_LENGTH:
                _bad("search must contain 1 to 160 characters with non-whitespace text")
            ids = {identity for identity in ids if search in snapshot.search_text[identity]}
        for name, lookup in snapshot.filters.items():
            if name in query:
                if not _LABEL.fullmatch(query[name]) or query[name] not in lookup:
                    _bad("unknown component filter")
                ids.intersection_update(lookup[query[name]])
        rows = [snapshot.summaries[key] for key in sorted(ids)]
        identity = [resource, *[query.get(key) for key in _CLASSIFICATION_FIELDS]]
        if search:
            identity.append(search)
    elif resource in {"claims", "proofs", "cores"}:
        _allowed(query, {"limit", "cursor"})
        store = {"claims": snapshot.claims, "proofs": snapshot.proofs, "cores": snapshot.cores}[resource]
        rows, identity = [store[key] for key in sorted(store)], resource
    elif resource == "receipts":
        _allowed(query, {"component", "limit", "cursor"})
        component = query.get("component")
        if component is not None and component not in snapshot.receipts_by_component:
            raise APIError(404, "unknown_id", "unknown component ID")
        ids = snapshot.receipts_by_component[component] if component is not None else sorted(snapshot.receipts)
        rows, identity = [snapshot.receipts[key] for key in ids], [resource, component]
    else:
        raise APIError(404, "not_found", "unknown API route")
    return _page(snapshot, rows, query, identity)


class ComponentApplication:
    """Thread-safe WSGI callable, with a bounded cache and atomic replacement."""

    def __init__(self, snapshot, *, cache_size=64, cache_bytes=8 * 1024 * 1024):
        if (not isinstance(snapshot, ComponentSnapshot) or type(cache_size) is not int or not 0 <= cache_size <= 256
                or type(cache_bytes) is not int or not 0 <= cache_bytes <= 32 * 1024 * 1024):
            raise ValueError("invalid snapshot or cache size")
        self._snapshot = snapshot
        self._lock, self._cache, self._cache_size = threading.RLock(), OrderedDict(), cache_size
        self._cache_bytes, self._cached_bytes = cache_bytes, 0

    @property
    def revision(self):
        with self._lock:
            return self._snapshot.revision

    def replace_index(self, index, *, fresh_runs=None, evidence_root=None):
        """Validate and build off-lock, then atomically replace all derived state."""
        replacement = ComponentSnapshot(index, fresh_runs=fresh_runs, evidence_root=evidence_root)
        with self._lock:
            self._snapshot = replacement
            self._cache.clear()
            self._cached_bytes = 0
        return replacement.revision

    def __call__(self, environ, start_response):
        with self._lock:
            snapshot = self._snapshot
        method = environ.get("REQUEST_METHOD", "")
        status, headers = 200, []
        try:
            if method not in {"GET", "HEAD"}:
                raise APIError(405, "method_not_allowed", "only GET and HEAD are available")
            path = environ.get("PATH_INFO", "")
            if (type(path) is not str or len(path) > 1100 or "%" in path or "\\" in path
                    or any(ord(c) < 32 or ord(c) > 126 for c in path)):
                _bad("malformed API path")
            query = _parameters(environ.get("QUERY_STRING", ""))
            encoding = _response_encoding(environ.get("HTTP_ACCEPT_ENCODING", ""))
            key = (snapshot.revision, path, tuple(sorted(query.items())), encoding)
            with self._lock:
                cached = self._cache.get(key)
                if cached is not None:
                    self._cache.move_to_end(key)
            if path == API_PREFIX + "/overview":
                _allowed(query, {"view"})
                if "view" in query and query["view"] != "map":
                    _bad("unsupported overview view")
                if query.get("view") == "map":
                    cached = ((snapshot.map_overview_gzip, snapshot.map_overview_gzip_etag) if encoding == "gzip"
                              else (snapshot.map_overview, snapshot.map_overview_etag))
                else:
                    cached = ((snapshot.overview_gzip, snapshot.overview_gzip_etag) if encoding == "gzip"
                              else (snapshot.overview, snapshot.overview_etag))
            if cached is None:
                data = _dispatch(snapshot, path, query)
                # Tooling consumes a standard OpenAPI document, not our data envelope.
                body = _json(data if path == API_PREFIX + "/openapi.json" else snapshot.envelope(data))
                body, etag = _encoded_response(body, encoding)
                cached = (body, etag)
                with self._lock:
                    if self._snapshot is snapshot and self._cache_size and len(body) <= self._cache_bytes:
                        previous = self._cache.pop(key, None)
                        if previous is not None:
                            self._cached_bytes -= len(previous[0])
                        self._cache[key] = cached
                        self._cached_bytes += len(body)
                        while len(self._cache) > self._cache_size or self._cached_bytes > self._cache_bytes:
                            self._cached_bytes -= len(self._cache.popitem(last=False)[1][0])
            body, etag = cached
            headers.extend([("ETag", etag), ("Cache-Control", "public, max-age=0, must-revalidate"),
                            ("Vary", "Accept-Encoding")])
            if encoding == "gzip":
                headers.append(("Content-Encoding", "gzip"))
            incoming = environ.get("HTTP_IF_NONE_MATCH", "")
            if incoming and len(incoming) <= 2048 and any(
                    token.strip().removeprefix("W/") in {etag, "*"} for token in incoming.split(",")):
                status, body = 304, b""
        except APIError as error:
            status = error.status
            body = _json({"schema_version": API_SCHEMA, "snapshot_revision": snapshot.revision,
                          "error": {"code": error.code, "message": error.message}})
            headers.append(("Cache-Control", "no-store"))
            if status == 405:
                headers.append(("Allow", "GET, HEAD"))
        except Exception:
            # WSGI's default error path can include tracebacks. Never forward it.
            status, body = 500, _json({"schema_version": API_SCHEMA,
                                      "error": {"code": "internal_error", "message": "request could not be completed"}})
            headers.append(("Cache-Control", "no-store"))
        phrases = {200: "OK", 304: "Not Modified", 400: "Bad Request", 404: "Not Found",
                   405: "Method Not Allowed", 406: "Not Acceptable", 409: "Conflict", 500: "Internal Server Error"}
        headers.extend([("X-Content-Type-Options", "nosniff"),
                        ("X-Plectis-Snapshot-Revision", snapshot.revision)])
        if status != 304:
            headers.extend([("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
        start_response(str(status) + " " + phrases[status], headers)
        return [b"" if method == "HEAD" else body]


class _HeaderReader(io.RawIOBase):
    """Recompute the total header budget before each socket receive."""

    def __init__(self, connection, timeout):
        self.connection = connection
        self.deadline = time.monotonic() + timeout

    def readable(self):
        return True

    def readinto(self, buffer):
        if self.deadline is not None:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("request header deadline exceeded")
            self.connection.settimeout(min(remaining, 5))
        return self.connection.recv_into(buffer)


class _QuietHandler(WSGIRequestHandler):
    def setup(self):
        super().setup()
        self.rfile.close()
        self._header_reader = _HeaderReader(self.connection, self.server.header_timeout)
        self.rfile = io.BufferedReader(self._header_reader)

    def handle(self):
        try:
            self._handle_request()
        except (TimeoutError, ConnectionError):
            # Incomplete or abandoned headers are closed without reflecting input.
            return

    def _handle_request(self):
        """Adapt the standard-library handler to declare its threaded contract."""
        self.raw_requestline = self.rfile.readline(65537)
        if len(self.raw_requestline) > 65536:
            self.requestline, self.request_version, self.command = "", "", ""
            self.send_error(414)
            return
        if not self.parse_request():
            return
        self._header_reader.deadline = None
        self.connection.settimeout(5)
        handler = ServerHandler(self.rfile, self.wfile, self.get_stderr(),
                                self.get_environ(), multithread=True)
        handler.request_handler = self
        handler.run(self.server.get_app())

    def send_error(self, code, message=None, explain=None):
        """Keep HTTP parser errors bounded JSON, without echoing request text."""
        body = _json({"schema_version": API_SCHEMA,
                      "error": {"code": "invalid_http_request", "message": "invalid HTTP request"}})
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if getattr(self, "command", "") != "HEAD":
            self.wfile.write(body)

    def log_message(self, format, *args):
        """Suppress query strings and identifiers from request logs by default."""


class ComponentHTTPServer(ThreadingMixIn, WSGIServer):
    """Local server with at most eight request threads and bounded socket waits."""

    daemon_threads = True
    block_on_close = False
    request_queue_size = 16
    header_timeout = 5

    def __init__(self, *args, **kwargs):
        self._slots = threading.BoundedSemaphore(8)
        super().__init__(*args, **kwargs)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


def add_arguments(parser):
    """Share argument ownership between the installed CLI and module entrypoint."""
    parser.add_argument("--index", help="explicit curated v3 index; default is packaged index")
    parser.add_argument("--fresh-runs", help="explicit bounded saved-run directory; startup admission only, no execution")
    parser.add_argument("--evidence-root", help="source registry root for explicit saved-run admission; default packaged resource root")
    parser.add_argument("--host", default="127.0.0.1", help="loopback address only")
    parser.add_argument("--port", type=int, default=8766)


def serve(args):
    """Serve a validated snapshot on loopback; expose no runtime execution."""
    try:
        address = ipaddress.ip_address(args.host)
        if not address.is_loopback or address.version != 4 or not 0 <= args.port <= 65535:
            raise ValueError()
        if getattr(args, "evidence_root", None) is not None and getattr(args, "fresh_runs", None) is None:
            raise ValueError("evidence root requires explicit saved-run directory")
        application = ComponentApplication(load_snapshot(args.index,
            fresh_runs=getattr(args, "fresh_runs", None), evidence_root=getattr(args, "evidence_root", None)))
    except Exception:
        print("serve-components: invalid loopback configuration or component index", file=sys.stderr)
        return 2
    try:
        with make_server(args.host, args.port, application, server_class=ComponentHTTPServer,
                         handler_class=_QuietHandler) as server:
            print("Component API: http://{}:{}/api/v1 revision={}".format(
                args.host, server.server_port, application.revision), flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    except OSError:
        print("serve-components: could not bind loopback listener", file=sys.stderr)
        return 2


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    return serve(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
