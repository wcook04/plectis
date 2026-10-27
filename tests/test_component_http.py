"""Actual HTTP transport and adversarial boundaries for the public index API."""
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
from http.client import HTTPConnection
import io
import json
import os
from pathlib import Path
import subprocess
import threading
from types import SimpleNamespace
from urllib.parse import quote, urlencode
from wsgiref.simple_server import make_server

import pytest
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate as validate_openapi

from microcosm_core import component_http as api, component_index


@pytest.fixture(scope="session")
def index_file():
    selected = os.environ.get("PLECTIS_COMPONENT_API_INDEX")
    return Path(selected) if selected else api.resource_root.microcosm_root() / component_index.INDEX_REF


@pytest.fixture(scope="session")
def raw(index_file):
    return json.loads(index_file.read_text())


@pytest.fixture(scope="session")
def snapshot(raw):
    return api.ComponentSnapshot(raw)


@pytest.fixture
def app(snapshot):
    return api.ComponentApplication(snapshot)


@pytest.fixture
def transport(app):
    server = make_server("127.0.0.1", 0, app, server_class=api.ComponentHTTPServer,
                         handler_class=api._QuietHandler)
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()

    def request(path="/api/v1", method="GET", headers=None):
        client = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        try:
            client.request(method, path, headers=headers or {})
            response = client.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            client.close()

    yield request
    server.shutdown()
    server.server_close()
    worker.join(timeout=5)
    assert not worker.is_alive()


def wsgi(app, path="/api/v1", query="", method="GET"):
    result = []
    body = b"".join(app({"REQUEST_METHOD": method, "PATH_INFO": path, "QUERY_STRING": query},
                        lambda status, headers: result.append((int(status[:3]), dict(headers)))))
    return *result[0], body


def changed_index(raw, text="New public summary for replacement."):
    result = copy.deepcopy(raw)
    claim = result["nodes"]["claim"][0]
    claim["card"]["summary"] = text
    fields = {"title": claim["card"]["title"], "summary": text,
              "claim_ceiling": claim.get("claim_ceiling"),
              "claim_ceiling_restated": claim.get("claim_ceiling_restated")}
    claim["card"]["claim_text_sha256"] = component_index._digest(fields)
    return result


def test_http_metadata_head_conditional_and_no_false_freshness(transport):
    status, headers, body = transport()
    assert status == 200
    data = json.loads(body)
    assert data["schema_version"] == api.API_SCHEMA
    assert data["data"]["component_count"] == 88
    assert data["data"]["evidence_state"]["fresh_prover"]["status"] == "not_recorded_by_index"
    status, head, empty = transport(method="HEAD")
    assert status == 200 and empty == b""
    assert head["Content-Length"] == str(len(body)) and head["ETag"] == headers["ETag"]
    for etag in (headers["ETag"], "W/" + headers["ETag"], '"other", ' + headers["ETag"], "*"):
        status, conditional, empty = transport(headers={"If-None-Match": etag})
        assert status == 304 and not empty
        assert conditional["ETag"] == headers["ETag"]


def test_discoverable_contract_matches_real_http_responses(transport):
    _, _, body = transport()
    metadata = json.loads(body)["data"]
    status, headers, body = transport(metadata["contract"]["openapi"])
    contract = json.loads(body)
    assert status == 200 and contract["info"]["version"] == metadata["contract"]["version"]
    validate_openapi(contract)
    samples = {
        "/components/{organ_id}": "/components/mcp_tool_authority_replay",
        "/claims/{claim_id}": "/claims/claim::mcp_tool_authority_replay",
        "/proofs/{proof_id}": "/proofs/proof::dafny::mcp_authority",
        "/graph": "/graph?type=organ&id=mcp_tool_authority_replay&max_edges=1",
    }
    for route, operations in contract["paths"].items():
        suffix = route.removeprefix(api.API_PREFIX)
        path = api.API_PREFIX + samples.get(suffix, suffix)
        code, _, payload = transport(path)
        assert code == 200, (route, payload)
        schema = operations["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        Draft202012Validator({**schema, "components": contract["components"]}).validate(json.loads(payload))
        code, head, empty = transport(path, method="HEAD")
        assert code == 200 and empty == b"" and head["Content-Length"] == str(len(payload))
    assert transport("/api/v1/openapi.json", headers={"If-None-Match": headers["ETag"]})[0] == 304
    assert transport("/api/v1/openapi.json?unused=1")[0] == 400
    assert transport("/api/v1/openapi.json", method="POST")[0] == 405


def test_search_pagination_filters_and_query_identity(transport, snapshot):
    # Deliberately search visible text rather than a known component identifier.
    query = {"q": "  THE  ", "limit": 1}
    expected = [key for key in snapshot.ids if "the" in snapshot.search_text[key]]
    assert len(expected) > 1
    rows = []
    while True:
        status, _, body = transport("/api/v1/components?" + urlencode(query))
        page = json.loads(body)["data"]
        assert status == 200 and page["total"] == len(expected)
        rows.extend(row["organ_id"] for row in page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
        # Equivalent casing and outer whitespace preserve the search identity.
        query.update(q="the", cursor=cursor)
    assert rows == expected
    status, _, body = transport("/api/v1/components?" + urlencode({"q": "the", "limit": 1}))
    cursor = json.loads(body)["data"]["next_cursor"]
    status, _, body = transport("/api/v1/components?" + urlencode({"q": "and", "limit": 1, "cursor": cursor}))
    assert status == 400 and json.loads(body)["error"]["code"] == "invalid_cursor"
    family = json.loads(snapshot.summaries[expected[0]])["classification"]["family"]
    status, _, body = transport("/api/v1/components?" + urlencode({"q": "the", "family": family, "limit": 100}))
    filtered = json.loads(body)["data"]
    assert status == 200 and filtered["items"]
    assert all(row["classification"]["family"] == family for row in filtered["items"])
    assert all(row["organ_id"] in expected for row in filtered["items"])


@pytest.mark.parametrize("query", ["", "   ", "x" * 161, "\x00", "\n"])
def test_invalid_search_is_bounded_client_error(transport, query):
    status, _, body = transport("/api/v1/components?" + urlencode({"q": query}))
    assert status == 400 and json.loads(body)["error"]["code"] == "invalid_parameters"


def test_search_no_matches_and_literal_metacharacters(transport):
    for query in ("does-not-exist-in-the-component-catalogue", ".*", "[a-z]+"):
        status, _, body = transport("/api/v1/components?" + urlencode({"q": query}))
        page = json.loads(body)["data"]
        assert status == 200 and page == {"items": [], "total": 0, "limit": 25, "next_cursor": None}


def test_component_claim_proof_and_receipt_views(transport, snapshot):
    key = "mcp_tool_authority_replay"
    status, _, body = transport("/api/v1/components/" + key)
    view = json.loads(body)["data"]
    assert status == 200 and view["component_id"] == key
    assert view["evidence_state"]["current_backend_binding"] == {"status": "not_checked"}
    assert view["proofs"] and view["subclaims"]
    for resource, identity in (("claims", "claim::" + key), ("proofs", "proof::dafny::mcp_authority")):
        status, _, body = transport("/api/v1/" + resource + "/" + quote(identity, safe=""))
        assert status == 200 and json.loads(body)["snapshot_revision"] == snapshot.revision
    status, _, body = transport("/api/v1/receipts?component=" + key)
    rows = json.loads(body)["data"]["items"]
    assert status == 200 and rows
    assert all(row["availability"] in {"available", "unavailable"} for row in rows)
    status, _, body = transport("/api/v1/receipts?component=pattern_assimilation_step&limit=100")
    rows = json.loads(body)["data"]["items"]
    absent = [row for row in rows if row["availability"] == "unavailable"]
    assert absent and all("href" not in row for row in absent)


def test_receipt_queries_cover_every_registered_component(transport, raw):
    artifacts = {row["artifact_id"]: row for row in raw["nodes"]["artifact"]}
    claims = {row["organ_id"]: row for row in raw["nodes"]["claim"]}
    registered = {row["organ_id"] for row in raw["nodes"]["organ"]}
    assert set(claims) == registered
    for component in sorted(registered):
        evidence = claims[component]["card"]["evidence"]
        expected = {evidence["authority_receipt_ref"], *evidence["historical_receipt_refs"]}
        rows, cursor = [], None
        while True:
            query = {"component": component, "limit": 100}
            if cursor is not None:
                query["cursor"] = cursor
            status, _, body = transport("/api/v1/receipts?" + urlencode(query))
            assert status == 200, (component, body)
            page = json.loads(body)["data"]
            assert page["total"] == len(expected)
            rows.extend(page["items"])
            cursor = page["next_cursor"]
            if cursor is None:
                break
        assert rows == [artifacts[reference] for reference in sorted(expected)]
        assert all("href" not in row for row in rows if row["availability"] == "unavailable")


def test_receipt_catalog_is_exact_authorized_union(transport, raw):
    artifacts = {row["artifact_id"]: row for row in raw["nodes"]["artifact"]}
    graph_refs = {edge[side] for edge in raw["edges"] for side in ("from", "to")
                  if edge[side + "_type"] == "receipt"}
    evidence_refs = set()
    for claim in raw["nodes"]["claim"]:
        evidence = claim["card"]["evidence"]
        evidence_refs.update({evidence["authority_receipt_ref"], *evidence["historical_receipt_refs"]})
    expected = graph_refs | evidence_refs
    unrelated_source_refs = {reference for reference, row in artifacts.items()
                             if reference not in expected and row.get("kind") == "file"
                             and reference.startswith("src/")}
    assert unrelated_source_refs
    rows, cursor = [], None
    while True:
        query = {"limit": 100}
        if cursor is not None:
            query["cursor"] = cursor
        status, _, body = transport("/api/v1/receipts?" + urlencode(query))
        assert status == 200
        page = json.loads(body)["data"]
        assert page["total"] == len(expected)
        rows.extend(page["items"])
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert rows == [artifacts[reference] for reference in sorted(expected)]
    assert not unrelated_source_refs.intersection(row["artifact_id"] for row in rows)


def test_existing_component_categories_filters_and_counts(transport, raw):
    status, _, body = transport()
    filters = json.loads(body)["data"]["component_filters"]
    assert status == 200
    for field, choices in filters.items():
        assert sum(row["component_count"] for row in choices) == len(raw["nodes"]["organ"])
        selected = choices[0]
        status, _, body = transport("/api/v1/components?" + urlencode({field: selected["value"], "limit": 100}))
        page = json.loads(body)["data"]
        assert status == 200 and page["total"] == selected["component_count"]
        assert all(row["classification"][field] == selected["value"] for row in page["items"])


def test_deterministic_pagination_and_context_binding(transport, snapshot):
    found, cursor = [], None
    while True:
        path = "/api/v1/components?limit=7" + ("&cursor=" + cursor if cursor else "")
        first = transport(path)
        assert first == transport(path)
        status, _, body = first
        page = json.loads(body)["data"]
        assert status == 200 and len(page["items"]) <= 7
        found.extend(row["organ_id"] for row in page["items"])
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert tuple(found) == snapshot.ids and len(set(found)) == 88
    _, _, body = transport("/api/v1/components?limit=7")
    cursor = json.loads(body)["data"]["next_cursor"]
    status, _, body = transport("/api/v1/components?limit=8&cursor=" + cursor)
    assert status == 400 and json.loads(body)["error"]["code"] == "invalid_cursor"


@pytest.mark.parametrize("suffix", ["limit=0", "limit=101", "limit=-1", "limit=1&limit=1",
    "unknown=x", "family=no_such_family", "cursor=" + "a" * 513, "cursor=%%%",
    "cursor=W10", "cursor=e30", "limit=%ZZ", "limit=%FF", "limit=", "limit",
    "cursor=" + "a" * 2049, "limit=1%00", "limit=1&" * 13])
def test_bad_queries_clear_json_errors(transport, suffix):
    status, _, body = transport("/api/v1/components?" + suffix)
    assert status == 400 and "error" in json.loads(body)
    assert b"Traceback" not in body and b"/Users/" not in body


def test_transport_oversized_request_line_is_json(transport):
    status, _, body = transport("/api/v1/components?cursor=" + "x" * 66000)
    assert status == 414 and json.loads(body)["error"]["code"] == "invalid_http_request"
    assert b"x" * 100 not in body


@pytest.mark.parametrize("path", ["/api/v1/components/../private.json", "/api/v1/components/%2e%2e",
    "/api/v1/components/%252e%252e", "/api/v1/components/x%2Fy", "/api/v1/components/x%5Cy",
    "/api/v1/components/mcp_tool_authority_replay%00", "/.microcosm/private.json",
    "/api/v1/files/private.json", "/api/v1/components/" + "x" * 1200])
def test_paths_never_serve_files(transport, path, tmp_path):
    (tmp_path / "private.json").write_text("PRIVATE_FILE_SENTINEL")
    status, _, body = transport(path)
    assert status in {400, 404}
    assert "error" in json.loads(body) and b"PRIVATE_FILE_SENTINEL" not in body


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"])
def test_no_http_mutation_or_execution(transport, method, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("runner invoked")
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    status, headers, body = transport("/api/v1/components/mcp_tool_authority_replay", method=method)
    assert status == 405 and headers["Allow"] == "GET, HEAD"
    assert json.loads(body)["error"]["code"] == "method_not_allowed"


def test_graph_typed_neighborhood_and_limits(transport):
    base = {"type": "claim", "id": "claim::mcp_tool_authority_replay", "depth": 3, "max_edges": 2}
    query = urlencode(base)
    status, _, body = transport("/api/v1/graph?" + query)
    data = json.loads(body)["data"]
    assert status == 200 and len(data["edges"]) == 2 and data["truncated"] is True
    assert len(data["nodes"]) <= 5
    assert len({(n["type"], n["id"]) for n in data["nodes"]}) == len(data["nodes"])
    assert body == transport("/api/v1/graph?" + query)[2]
    for parameters in ({"depth": 4}, {"max_edges": 501}, {"direction": "sideways"}, {"edge_kind": "fake"}):
        status, _, _ = transport("/api/v1/graph?" + urlencode({**base, **parameters}))
        assert status == 400
    status, _, body = transport("/api/v1/graph?type=claim&id=no_such_id")
    assert status == 404 and json.loads(body)["error"]["code"] == "unknown_node"
    status, _, _ = transport("/api/v1/graph?type=untyped&id=x")
    assert status == 400


def test_requests_use_no_filesystem_or_revalidating_reader(app, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("request read a file or revalidated whole index")
    for name in ("open", "read_bytes", "read_text", "stat", "glob", "rglob"):
        monkeypatch.setattr(Path, name, forbidden)
    monkeypatch.setattr(component_index, "validate_index", forbidden)
    monkeypatch.setattr(component_index, "get_component", forbidden)
    monkeypatch.setattr(component_index, "compile_views", forbidden)
    for path, query in (("/api/v1", ""), ("/api/v1/components", ""),
                        ("/api/v1/components/mcp_tool_authority_replay", ""),
                        ("/api/v1/graph", "type=claim&id=claim%3A%3Amcp_tool_authority_replay&depth=2")):
        assert wsgi(app, path, query)[0] == 200


def test_snapshot_input_detachment_and_cache_budget(raw):
    local = copy.deepcopy(raw)
    snapshot = api.ComponentSnapshot(local)
    app = api.ComponentApplication(snapshot, cache_size=2, cache_bytes=10000)
    local.clear()
    for path in ("/api/v1", "/api/v1/components", "/api/v1/proofs", "/api/v1/claims"):
        assert wsgi(app, path)[0] == 200
    assert len(app._cache) <= 2 and app._cached_bytes <= 10000
    with pytest.raises(TypeError):
        snapshot.components["x"] = b"{}"
    with pytest.raises(AttributeError):
        snapshot.revision = "different"


def test_atomic_replacement_stale_cursor_and_conditional_invalidation(app, raw):
    _, old_headers, old_body = wsgi(app, "/api/v1/components", "limit=7")
    old = json.loads(old_body)
    cursor = old["data"]["next_cursor"]
    revision = app.replace_index(changed_index(raw))
    assert revision != old["snapshot_revision"] and not app._cache
    status, _, body = wsgi(app, "/api/v1/components", "limit=7&cursor=" + cursor)
    assert status == 409 and json.loads(body)["error"]["code"] == "stale_cursor"
    _, new_headers, new_body = wsgi(app, "/api/v1/components", "limit=7")
    assert new_headers["ETag"] != old_headers["ETag"] and new_body != old_body
    bad = changed_index(raw)
    bad["schema_version"] = "bad"
    with pytest.raises(ValueError):
        app.replace_index(bad)
    assert app.revision == revision


def test_http_concurrent_request_state_isolation_and_replacement(transport, app, raw):
    paths = ["/api/v1/components/" + name for name in app._snapshot.ids[:10]]
    with ThreadPoolExecutor(max_workers=8) as workers:
        futures = [workers.submit(transport, paths[i % len(paths)]) for i in range(32)]
        app.replace_index(changed_index(raw))
        for i, future in enumerate(futures):
            status, headers, body = future.result(timeout=20)
            data = json.loads(body)
            assert status == 200 and data["data"]["component_id"] == paths[i % len(paths)].split("/")[-1]
            assert headers["X-Plectis-Snapshot-Revision"] == data["snapshot_revision"]
    assert all(key[0] == app.revision for key in app._cache)


def test_inflight_old_request_cannot_repopulate_replaced_cache(app, raw, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    original, old_revision = api._dispatch, app.revision

    def paused(snapshot, path, query):
        entered.set()
        assert release.wait(timeout=30)
        return original(snapshot, path, query)

    monkeypatch.setattr(api, "_dispatch", paused)
    with ThreadPoolExecutor(max_workers=1) as workers:
        pending = workers.submit(wsgi, app)
        assert entered.wait(timeout=5)
        new_revision = app.replace_index(changed_index(raw))
        release.set()
        status, headers, body = pending.result(timeout=5)
    assert status == 200 and json.loads(body)["snapshot_revision"] == old_revision
    assert headers["X-Plectis-Snapshot-Revision"] == old_revision
    assert new_revision != old_revision and not app._cache


@pytest.mark.parametrize("private", ["/Volumes/private-backend/session/secret.json",
    "/etc/passwd", "/secret", "C:\\private\\secret.json", "\\\\server\\private", "file:///private/key", "FILE://private-host/share"])
def test_private_paths_in_index_fail_closed(raw, private):
    with pytest.raises(ValueError):
        api.ComponentSnapshot(changed_index(raw, private))


@pytest.mark.parametrize("private", [">/Volumes/private/session.json", " >/secret", "//private-server/share"])
def test_path_punctuation_cannot_bypass_public_guard(raw, private):
    with pytest.raises(ValueError):
        api.ComponentSnapshot(changed_index(raw, private))


def test_invalid_snapshot_and_json_fail_closed(raw, tmp_path):
    for bad in ({}, {"schema_version": "bad"}, changed_index(raw)):
        if "nodes" in bad:
            bad["nodes"]["claim"][0]["card"]["source_body"] = "private source"
        with pytest.raises((ValueError, KeyError, TypeError)):
            api.ComponentSnapshot(bad)
    path = tmp_path / "bad.json"
    for payload in ('{"a":1,"a":2}', '{"schema_version":NaN}', '{}'):
        path.write_text(payload)
        with pytest.raises((ValueError, KeyError, TypeError)):
            api.load_snapshot(path)
    path.write_bytes(b"x" * (api.MAX_INDEX_BYTES + 1))
    with pytest.raises(ValueError):
        api.load_snapshot(path)


def test_wsgi_internal_errors_are_sanitized(app, monkeypatch):
    def broken(*args):
        raise OSError("private /Users/operator/secret.json")
    monkeypatch.setattr(api, "_dispatch", broken)
    status, _, body = wsgi(app)
    assert status == 500 and b"/Users" not in body and b"Traceback" not in body


@pytest.mark.parametrize("path,status", [("/api/v1/components/no_such_component", 404),
    ("/api/v1/claims/claim::no_such_component", 404), ("/api/v1/proofs/proof::dafny::no_such_proof", 404),
    ("/api/v1/components/Bad-ID", 400), ("/api/v1/claims/wrong", 400), ("/api/v1/proofs/wrong", 400)])
def test_unknown_and_malformed_ids(transport, path, status):
    observed, _, body = transport(path)
    assert observed == status and "error" in json.loads(body)


def test_cli_invalid_configuration_and_startup_errors_hide_paths(capsys, tmp_path):
    for host, port, index in (("0.0.0.0", 8766, None), ("127.0.0.1", -1, None),
                              ("127.0.0.1", 8766, str(tmp_path / "private-secret-index.json"))):
        assert api.serve(SimpleNamespace(host=host, port=port, index=index)) == 2
        output = capsys.readouterr().err
        assert "private-secret-index" not in output and "/Users/" not in output and "Traceback" not in output


def test_coverage_facets_keep_denominators_and_unknowns(transport, raw):
    status, _, body = transport("/api/v1/coverage")
    data = json.loads(body)["data"]
    assert status == 200 and data == component_index.coverage_view(raw)
    assert data["denominator"]["count"] == len(raw["nodes"]["organ"])
    registered = {row["organ_id"] for row in raw["nodes"]["organ"]}
    for metric in data["component_presence"].values():
        assert metric["denominator"] == len(registered)
        assert metric["numerator"] == len(metric["component_ids"])
        assert set(metric["component_ids"]) <= registered
        assert metric["component_ids"] == sorted(set(metric["component_ids"]))
    assert sum(data["evidence_class_counts"].values()) == len(registered)
    assert data["whole_claim_coverage"]["percentage"] is None
    for result in data["fresh_results"].values():
        assert result == {"status": "not_run_by_index", "recorded_count": 0}
