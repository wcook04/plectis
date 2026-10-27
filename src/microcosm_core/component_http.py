"""Read-only, snapshot-backed HTTP API for the existing component claim index.

Only startup and explicit replacement read an index. Requests use immutable
encoded views and precomputed adjacency, never a filesystem root or runner.
This module has no dependency beyond the standard library and component_index.
"""
from __future__ import annotations

import argparse
import base64
from collections import OrderedDict, defaultdict, deque
import copy
import hashlib
import ipaddress
import json
from pathlib import Path
import re
from socketserver import ThreadingMixIn
import sys
import threading
from types import MappingProxyType
from urllib.parse import parse_qsl
from wsgiref.simple_server import ServerHandler, WSGIRequestHandler, WSGIServer, make_server

from microcosm_core import component_index, resource_root
from microcosm_core.schemas import loads_json_strict

API_SCHEMA = "plectis_component_http_v1"
API_PREFIX = "/api/v1"
MAX_INDEX_BYTES = 16 * 1024 * 1024
MAX_QUERY_BYTES = 2048
MAX_CURSOR_BYTES = 512
MAX_PAGE_SIZE = 100
MAX_GRAPH_DEPTH = 3
MAX_GRAPH_EDGES = 500
_CLASSIFICATION_FIELDS = ("family", "evidence_class", "real_substrate_disposition", "truth_accounting_bucket")
_LABEL = re.compile(r"[a-z][a-z0-9_]*\Z")
_PROOF = re.compile(r"proof::dafny::[a-z][a-z0-9_]*\Z")
_CLAIM = re.compile(r"claim::[a-z][a-z0-9_]*\Z")
_BAD_ESCAPE = re.compile(r"%(?![a-fA-F0-9]{2})")
_ABSOLUTE = re.compile(r"(?<![A-Za-z0-9_./])/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*")
_ID_FIELD = {"organ": "organ_id", "claim": "claim_id", "source_file": "path",
             "route": "task_class", "family": "family_id", "guide": "guide_id",
             "replay": "replay_id", "subclaim": "subclaim_id", "proof": "proof_id",
             "specification": "specification_id", "artifact": "artifact_id"}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


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

    def __init__(self, index):
        # Detach before validation: later caller mutation cannot change requests.
        index = copy.deepcopy(index)
        canonical = _json(index)
        if len(canonical) > MAX_INDEX_BYTES:
            raise ValueError("component index exceeds snapshot size limit")
        _public_text(index)
        views = component_index.compile_views(index)
        self.revision = hashlib.sha256(canonical).hexdigest()
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
        self.nodes = {}
        for kind, rows in index["nodes"].items():
            for row in rows:
                self.nodes[(kind, row[_ID_FIELD[kind]])] = _json(row)
        artifacts = {row["artifact_id"]: row for row in index["nodes"]["artifact"]}
        receipt_ids = {edge[side] for edge in index["edges"] for side in ("from", "to")
                       if edge[side + "_type"] == "receipt"}
        self.receipts = {key: _json(artifacts[key]) for key in sorted(receipt_ids)}
        self.coverage = _json(views["coverage"])
        self.receipts_by_component = {}
        for key, encoded in self.components.items():
            view = json.loads(encoded)
            refs = view["claim"]["card"]["evidence"]
            self.receipts_by_component[key] = tuple(sorted({refs["authority_receipt_ref"],
                                                          *refs["historical_receipt_refs"]}))
        self.edges = tuple(sorted(index["edges"], key=_edge_key))
        self.edge_kinds = frozenset(index["graph"]["edge_kinds"])
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
                                    "graph_edges": MAX_GRAPH_EDGES},
                         "execution": "unavailable_over_http"}
        self.metadata = _json(self.metadata)
        self.edges = tuple(MappingProxyType(edge) for edge in self.edges)
        self.filters = {key: MappingProxyType({value: frozenset(ids) for value, ids in lookup.items()})
                        for key, lookup in self.filters.items()}
        for name in ("components", "summaries", "claims", "proofs", "filters",
                     "nodes", "receipts", "receipts_by_component", "adjacency"):
            setattr(self, name, MappingProxyType(getattr(self, name)))
        self._sealed = True

    def envelope(self, data):
        return {"schema_version": API_SCHEMA, "snapshot_revision": self.revision, "data": data}


def load_snapshot(index_file=None):
    """Read one explicitly selected or packaged index; invalid input fails closed."""
    path = (Path(index_file) if index_file is not None
            else resource_root.microcosm_root() / component_index.INDEX_REF)
    if path.is_symlink() or not path.is_file():
        raise ValueError("component index must be a regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_INDEX_BYTES + 1)
    if len(raw) > MAX_INDEX_BYTES:
        raise ValueError("component index exceeds snapshot size limit")
    return ComponentSnapshot(loads_json_strict(raw.decode("utf-8"), "component index"))


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
    if path == API_PREFIX:
        _allowed(query, {})
        return json.loads(snapshot.metadata)
    if path == API_PREFIX + "/graph":
        return _graph(snapshot, query)
    if path == API_PREFIX + "/coverage":
        _allowed(query, {})
        return json.loads(snapshot.coverage)
    parts = path.removeprefix(API_PREFIX + "/").split("/")
    if not path.startswith(API_PREFIX + "/") or len(parts) not in (1, 2):
        raise APIError(404, "not_found", "unknown API route")
    resource = parts[0]
    if len(parts) == 2:
        _allowed(query, {})
        identity = parts[1]
        stores = {"components": (snapshot.components, _LABEL),
                  "claims": (snapshot.claims, _CLAIM), "proofs": (snapshot.proofs, _PROOF)}
        if resource not in stores:
            raise APIError(404, "not_found", "unknown API route")
        store, pattern = stores[resource]
        if not pattern.fullmatch(identity):
            _bad("malformed resource ID")
        if identity not in store:
            raise APIError(404, "unknown_id", "unknown resource ID")
        return json.loads(store[identity])
    if resource == "components":
        _allowed(query, {*_CLASSIFICATION_FIELDS, "limit", "cursor"})
        ids = set(snapshot.ids)
        for name, lookup in snapshot.filters.items():
            if name in query:
                if not _LABEL.fullmatch(query[name]) or query[name] not in lookup:
                    _bad("unknown component filter")
                ids.intersection_update(lookup[query[name]])
        rows = [snapshot.summaries[key] for key in sorted(ids)]
        identity = [resource, *[query.get(key) for key in _CLASSIFICATION_FIELDS]]
    elif resource in {"claims", "proofs"}:
        _allowed(query, {"limit", "cursor"})
        store = snapshot.claims if resource == "claims" else snapshot.proofs
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

    def replace_index(self, index):
        """Validate and build off-lock, then atomically replace all derived state."""
        replacement = ComponentSnapshot(index)
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
            key = (snapshot.revision, path, tuple(sorted(query.items())))
            with self._lock:
                cached = self._cache.get(key)
                if cached is not None:
                    self._cache.move_to_end(key)
            if cached is None:
                body = _json(snapshot.envelope(_dispatch(snapshot, path, query)))
                etag = '"' + hashlib.sha256(body).hexdigest() + '"'
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
            headers.extend([("ETag", etag), ("Cache-Control", "public, max-age=0, must-revalidate")])
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
                   405: "Method Not Allowed", 409: "Conflict", 500: "Internal Server Error"}
        headers.extend([("X-Content-Type-Options", "nosniff"),
                        ("X-Plectis-Snapshot-Revision", snapshot.revision)])
        if status != 304:
            headers.extend([("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
        start_response(str(status) + " " + phrases[status], headers)
        return [b"" if method == "HEAD" else body]


class _QuietHandler(WSGIRequestHandler):
    def handle(self):
        """Adapt the standard-library handler to declare its threaded contract."""
        self.raw_requestline = self.rfile.readline(65537)
        if len(self.raw_requestline) > 65536:
            self.requestline, self.request_version, self.command = "", "", ""
            self.send_error(414)
            return
        if not self.parse_request():
            return
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

    def __init__(self, *args, **kwargs):
        self._slots = threading.BoundedSemaphore(8)
        super().__init__(*args, **kwargs)

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(5)
        return connection, address

    def process_request(self, request, client_address):
        self._slots.acquire()
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
    parser.add_argument("--host", default="127.0.0.1", help="loopback address only")
    parser.add_argument("--port", type=int, default=8766)


def serve(args):
    """Serve a validated snapshot on loopback; expose no runtime execution."""
    try:
        address = ipaddress.ip_address(args.host)
        if not address.is_loopback or address.version != 4 or not 0 <= args.port <= 65535:
            raise ValueError()
        application = ComponentApplication(load_snapshot(args.index))
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
