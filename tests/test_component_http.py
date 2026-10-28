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


def test_advertised_graph_counts_match_the_traversable_snapshot(snapshot):
    from collections import Counter
    graph = json.loads(snapshot.metadata)["graph"]
    assert graph["edge_kind_counts"] == dict(Counter(edge["kind"] for edge in snapshot.edges))
    assert set(graph["edge_kinds"]) == set(graph["edge_kind_counts"])
    for kind in {"rests_on", "violates"} & set(graph["edge_kinds"]):
        assert graph["edge_semantics"][kind]


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
        "/cores/{core_id}": "/cores/repair",
        "/doctrine/{rule_id}": "/doctrine/AX-4",
        "/graph": "/graph?type=organ&id=mcp_tool_authority_replay&max_edges=1",
    }
    for route, operations in contract["paths"].items():
        suffix = route.removeprefix(api.API_PREFIX)
        path = api.API_PREFIX + samples.get(suffix, suffix)
        if suffix == "/cores/{core_id}" and metadata.get("core_count", 0) == 0:
            assert transport(path)[0] == 404
            continue
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
    summaries = {row['ref']: row for row in raw.get('explorer', {}).get('receipt_summaries', [])}
    artifacts = {row["artifact_id"]: {**row, **({'summary': summaries[row['artifact_id']]}
                 if row['artifact_id'] in summaries else {})} for row in raw["nodes"]["artifact"]}
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
    summaries = {row['ref']: row for row in raw.get('explorer', {}).get('receipt_summaries', [])}
    artifacts = {row["artifact_id"]: {**row, **({'summary': summaries[row['artifact_id']]}
                 if row['artifact_id'] in summaries else {})} for row in raw["nodes"]["artifact"]}
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


def test_overview_agrees_with_existing_routes_and_transport(transport, snapshot):
    status, headers, body = transport('/api/v1/overview')
    assert status == 200 and len(body) <= api.MAX_OVERVIEW_BYTES
    overview = json.loads(body)
    assert overview['snapshot_revision'] == snapshot.revision
    data = overview['data']
    assert data['coverage'] == json.loads(transport('/api/v1/coverage')[2])['data']
    detailed = json.loads(transport('/api/v1/proofs?limit=100')[2])['data']['items']
    for compact, full in zip(data['kernels'], detailed, strict=True):
        for owner in (full, full['proof']):
            if owner.get('guide'):
                guide = owner['guide']
                if guide['availability'] == 'available':
                    assert hashlib.sha256(guide['text'].encode()).hexdigest() == guide['sha256']
                guide['text'] = None
        assert compact == full
    assert 'guides' not in data.get('explorer', {})
    assert data['receipts'] == [json.loads(snapshot.receipts[key]) for key in sorted(snapshot.receipts)]
    for row in data['components']:
        component = json.loads(transport('/api/v1/components/' + row['organ_id'])[2])['data']
        summary = json.loads(snapshot.summaries[row['organ_id']])
        assert all(row[key] == value for key, value in summary.items())
        assert row['proof_ids'] == [proof['proof']['proof_id'] for proof in component['proofs']]
        assert row['receipt_refs'] == [json.loads(snapshot.receipts[key])
                                      for key in snapshot.receipts_by_component[row['organ_id']]]
        expected = [edge['to'] for edge in snapshot.edges if edge['kind'] == 'wires_to'
                    and edge['from'] == row['organ_id']]
        assert row['wires_to'] == sorted(expected)
    status, head, empty = transport('/api/v1/overview', method='HEAD')
    assert status == 200 and empty == b''
    assert head['Content-Length'] == str(len(body)) and head['ETag'] == headers['ETag']
    assert transport('/api/v1/overview', headers={'If-None-Match': headers['ETag']})[0] == 304
    assert transport('/api/v1/overview?limit=1')[0] == 400


def test_overview_is_preencoded_without_io_or_request_compilation(snapshot, monkeypatch):
    app = api.ComponentApplication(snapshot, cache_size=0, cache_bytes=0)
    def forbidden(*args, **kwargs):
        raise AssertionError('request attempted source IO or view compilation')
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(component_index, 'compile_views', forbidden)
    monkeypatch.setattr(api, '_dispatch', forbidden)
    status, _, body = wsgi(app, '/api/v1/overview')
    assert status == 200 and body is snapshot.overview
    assert not app._cache and app._cached_bytes == 0


def test_overview_encoded_limit_is_admission_boundary(raw, monkeypatch):
    monkeypatch.setattr(api, 'MAX_OVERVIEW_BYTES', 1)
    with pytest.raises(ValueError, match='overview exceeds encoded response limit'):
        api.ComponentSnapshot(raw)



def test_cores_and_explorer_use_same_snapshot_views(transport, snapshot):
    _, _, body = transport('/api/v1/overview')
    overview = json.loads(body)['data']
    status, _, body = transport('/api/v1/cores?limit=100')
    assert status == 200
    full_cores = json.loads(body)['data']['items']
    assert len(full_cores) == len(overview['cores'])
    for row, full in zip(overview['cores'], full_cores, strict=True):
        status, headers, body = transport('/api/v1/cores/' + row['core_id'])
        assert status == 200 and json.loads(body)['data'] == full
        if full.get('guide'):
            guide = full['guide']
            if guide['availability'] == 'available':
                assert hashlib.sha256(guide['text'].encode()).hexdigest() == guide['sha256']
            guide['text'] = None
        assert full == row
        assert headers['X-Plectis-Snapshot-Revision'] == snapshot.revision
    assert transport('/api/v1/cores/absent')[0] == 404
    assert transport('/api/v1/cores/core::dafny::repair')[0] == 400
    assert transport('/api/v1/cores?component=x')[0] == 400



def test_explorer_contract_declares_bounded_source_and_evidence_shapes():
    schemas = api.component_api_contract.openapi_document()['components']['schemas']
    for name in ('SourceExcerpt', 'ChangedLine', 'NegativeControl', 'DoctrineNode',
                 'DoctrineEdge', 'SourceRevision', 'ReceiptSummary', 'ArtifactBinding'):
        Draft202012Validator.check_schema(schemas[name])
    excerpt = {'ref': 'formal/example.dfy#Exact', 'kind': 'lemma', 'name': 'Exact',
               'line_start': 1, 'line_end': 2, 'text': 'lemma Exact() {}',
               'source_sha256': 'a' * 64, 'text_sha256': 'b' * 64}
    validator = Draft202012Validator({**schemas['SourceExcerpt'], 'components': {'schemas': schemas}})
    validator.validate(excerpt)
    assert list(validator.iter_errors({**excerpt, 'line_start': 0}))
    assert list(validator.iter_errors({**excerpt, 'text': 'x' * (24 * 1024 + 1)}))
    Draft202012Validator(schemas['ChangedLine']).validate(
        {'line': 1, 'original': None, 'mutated': '// added line'})
    proof = schemas['Proof']['properties']
    assert 'component_ids' in proof and 'claim_ids' in proof
    assert 'excerpts' in proof['proof']['properties']


def test_server_overload_never_blocks_accept_loop_or_shutdown(app):
    import socket
    import time
    server = make_server('127.0.0.1', 0, app, server_class=api.ComponentHTTPServer,
                         handler_class=api._QuietHandler)
    worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    worker.start()
    clients = []
    shutdown = None
    try:
        for _ in range(8):
            client = socket.create_connection(server.server_address, timeout=1)
            client.sendall(b'GET /api/v1 HTTP/1.1\r\nX-Held: ')
            clients.append(client)
        deadline = time.monotonic() + 1
        while server._slots._value and time.monotonic() < deadline:
            threading.Event().wait(.005)
        assert server._slots._value == 0
        overload = socket.create_connection(server.server_address, timeout=1)
        clients.append(overload)
        try:
            assert overload.recv(1) == b''
        except ConnectionResetError:
            pass
        shutdown = threading.Thread(target=server.shutdown, daemon=True)
        shutdown.start()
        shutdown.join(timeout=.5)
        assert not shutdown.is_alive(), 'overload blocked the server accept loop'
    finally:
        for client in clients:
            client.close()
        if shutdown is None:
            server.shutdown()
        else:
            shutdown.join(timeout=2)
        server.server_close()
        worker.join(timeout=2)
    assert not worker.is_alive()


def test_trickle_headers_have_absolute_deadline(app):
    import socket
    import time
    server = make_server('127.0.0.1', 0, app, server_class=api.ComponentHTTPServer,
                         handler_class=api._QuietHandler)
    server.header_timeout = .25
    worker = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}, daemon=True)
    worker.start()
    client = socket.create_connection(server.server_address, timeout=1)
    client.settimeout(.04)
    started, sent, closed = time.monotonic(), 0, False
    try:
        client.sendall(b'GET /api/v1 HTTP/1.1\r\nX-Trickle: ')
        while time.monotonic() - started < 1:
            try:
                client.sendall(b'x')
                sent += 1
                if client.recv(1) == b'':
                    closed = True
                    break
            except socket.timeout:
                continue
            except (BrokenPipeError, ConnectionResetError):
                closed = True
                break
        elapsed = time.monotonic() - started
        assert closed and sent >= 3
        assert .15 <= elapsed < .8, elapsed
    finally:
        client.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
    assert not worker.is_alive()


def test_explorer_doctrine_and_receipt_summaries_survive_transport(raw, snapshot, transport):
    explorer = raw.get('explorer', {})
    metadata = json.loads(transport()[2])['data']
    for row in explorer.get('doctrine', {}).get('nodes', []):
        query = urlencode({'type': 'doctrine_ref', 'id': row['id'], 'max_edges': 500})
        status, _, body = transport('/api/v1/graph?' + query)
        assert status == 200
        graph = json.loads(body)['data']
        record = next(item['record'] for item in graph['nodes'] if item['id'] == row['id'])
        assert all(record[key] == value for key, value in row.items())
        for edge in explorer['doctrine']['edges']:
            if edge['from_id'] == row['id'] or edge['to_id'] == row['id']:
                assert edge['kind'] in metadata['graph']['edge_kinds']
                assert any(item['kind'] == edge['kind'] and item['from'] == edge['from_id']
                           and item['to'] == edge['to_id'] for item in graph['edges'])
    for row in explorer.get('receipt_summaries', []):
        if row['ref'] in snapshot.receipts:
            assert json.loads(snapshot.receipts[row['ref']])['summary'] == row


@pytest.fixture
def saved_local_runs(tmp_path):
    # Reuse the source owner's real admission fixture without executing a runner.
    from test_component_local_evidence import saved
    return saved.__wrapped__(tmp_path)


def test_explicit_saved_runs_bind_snapshot_and_serve_without_io(raw, saved_local_runs, monkeypatch):
    root, _, run, _, _, _ = saved_local_runs
    base = api.ComponentSnapshot(raw)
    snapshot = api.ComponentSnapshot(raw, fresh_runs=run, evidence_root=root)
    assert snapshot.revision != base.revision
    app = api.ComponentApplication(snapshot)
    def forbidden(*args, **kwargs):
        raise AssertionError('local evidence request attempted IO or execution')
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(Path, 'read_bytes', forbidden)
    from microcosm_core import component_local_evidence, component_replay
    monkeypatch.setattr(component_local_evidence, 'load_local_run_evidence', forbidden)
    monkeypatch.setattr(component_replay, 'replay_components', forbidden)
    status, headers, body = wsgi(app, '/api/v1/local-runs')
    assert status == 200
    payload = json.loads(body)
    data = payload['data']
    assert data['status'] == 'loaded' and len(data['runs']) == 1
    assert data['fresh_execution']['status'] == 'not_run_by_server'
    assert data['runs'][0]['admission']['rechecked_accepted'] is True
    assert data['runs'][0]['current_source_binding']['status'] == 'unknown'
    assert str(root) not in body.decode()
    overview = json.loads(wsgi(app, '/api/v1/overview')[2])
    assert overview['snapshot_revision'] == payload['snapshot_revision']
    assert overview['data']['local_runs'] == data
    status, head, empty = wsgi(app, '/api/v1/local-runs', method='HEAD')
    assert status == 200 and empty == b'' and head['ETag'] == headers['ETag']
    assert head['Content-Length'] == str(len(body))


def test_local_runs_disabled_and_untrusted_overlay_rejected(raw, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('default snapshot attempted filesystem IO')
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(Path, 'stat', forbidden)
    snapshot = api.ComponentSnapshot(raw)
    assert snapshot.revision == hashlib.sha256(api._json(raw)).hexdigest()
    value = json.loads(snapshot.local_runs)
    assert value['status'] == 'disabled' and not value['runs']
    assert wsgi(api.ComponentApplication(snapshot), '/api/v1/local-runs', 'path=private')[0] == 400
    for malicious in ({**value, 'path': '/private/run'}, {**value, 'runs': [{'source_body': 'private'}]},
                      {**value, 'status': 'fresh_proof_pass'}):
        with pytest.raises(ValueError):
            api.ComponentSnapshot(raw, local_run_evidence=malicious)


def _doctrine_nodes(raw):
    return {row["id"]: row for row in raw["explorer"]["doctrine"]["nodes"]}


def test_doctrine_list_counts_match_graph_citations(raw, transport):
    from collections import Counter
    status, headers, body = transport("/api/v1/doctrine")
    assert status == 200
    data = json.loads(body)["data"]
    nodes = _doctrine_nodes(raw)
    assert [row["id"] for row in data["rules"]] == list(nodes)
    assert data["counts"] == {"axiom": 12, "principle": 20, "anti_principle": 17,
                              "citations": data["counts"]["citations"]}
    citations = [edge for edge in raw["edges"] if edge["kind"] == "grounded_in_doctrine"
                 and edge["ref_kind"] in {"axiom", "principle"} and edge["to"] in nodes]
    assert data["counts"]["citations"] == len(citations)
    by_rule = Counter(edge["to"] for edge in citations)
    for row in data["rules"]:
        expected = sorted({edge["from"] for edge in citations if edge["to"] == row["id"]})
        assert row["component_ids"] == expected and row["cited_by_count"] == len(expected)
        assert by_rule[row["id"]] == len(expected)
        if row["kind"] == "axiom":
            assert row["support_verdict"] == nodes[row["id"]]["axiom"]["support"]["verdict"]
            assert row["witness_component_ids"] == nodes[row["id"]]["axiom"]["routing"]["witness_component_ids"]
        else:
            assert row["support_verdict"] is None and row["witness_component_ids"] == []
        assert row["rests_on"] == sorted({e["to_id"] for e in data["edges"] if e["from_id"] == row["id"] and e["kind"] == "rests_on"},
                                         key=api._rule_key)
        assert row["reader_plain"] == nodes[row["id"]]["reader"]["plain"]
        assert row["enforced_in_component_ids"] == nodes[row["id"]]["reader"]["enforced_in_component_ids"]
        assert row["failure_modes"] == sorted({e["from_id"] for e in data["edges"] if e["to_id"] == row["id"] and e["kind"] == "violates"},
                                              key=api._rule_key)
    assert data["sources"] == raw["explorer"]["doctrine"]["sources"]
    assert transport("/api/v1/doctrine", headers={"If-None-Match": headers["ETag"]})[0] == 304
    assert transport("/api/v1/doctrine?limit=5")[0] == 400


def test_doctrine_rule_detail_citations_and_errors(raw, snapshot, transport):
    nodes = _doctrine_nodes(raw)
    for identity in ("AX-4", "P-15", "AP-4"):
        status, headers, body = transport("/api/v1/doctrine/" + identity)
        assert status == 200
        data = json.loads(body)["data"]
        assert {key: data[key] for key in nodes[identity]} == nodes[identity]
        assert data["component_ids"] == sorted({row["component_id"] for row in data["citations"]})
        for row in data["citations"]:
            assert row["basis"] == "authored_atlas_row" and row["component_id"] in snapshot.components
            assert row["source_ref"] == "core/organ_atlas.json::organs[{}].{}_refs".format(
                row["component_id"], row["ref_kind"])
        assert ("axiom" in data) == (identity == "AX-4")
        assert transport("/api/v1/doctrine/" + identity, headers={"If-None-Match": headers["ETag"]})[0] == 304
    for malformed in ("ax-4", "AX-", "X-1", "AX-1000", "P-1.5"):
        status, _, body = transport("/api/v1/doctrine/" + malformed)
        assert status == 400 and json.loads(body)["error"]["code"] == "invalid_parameters"
    status, _, body = transport("/api/v1/doctrine/AX-99")
    assert status == 404 and json.loads(body)["error"]["code"] == "unknown_id"
    assert transport("/api/v1/doctrine/AX-4?x=1")[0] == 400


def test_axiom_support_and_witnesses_are_bounded_and_registered(raw, snapshot):
    nodes = _doctrine_nodes(raw)
    axioms = [row for row in nodes.values() if row["kind"] == "axiom"]
    assert len(axioms) == 12
    for row in nodes.values():
        assert ("axiom" in row) == (row["kind"] == "axiom")
        assert hashlib.sha256(row["statement"].encode()).hexdigest() == row["statement_sha256"]
        assert len(row["statement"].encode()) <= 4000
    for row in axioms:
        detail = row["axiom"]
        support = detail["support"]
        assert support["basis"] == "index_time_computed"
        assert support["checker_id"] == "checker.microcosm.validators.axiom_support_cover"
        assert support["verdict"]
        assert detail["routing"]["basis"] == "authored_routing_registry"
        witnesses = set(detail["routing"]["witness_component_ids"])
        for obligation in detail["obligations"]:
            witnesses.update(obligation["witness_component_ids"])
        assert witnesses <= set(snapshot.components)


def test_doctrine_edge_semantics_and_metadata_count(snapshot):
    metadata = json.loads(snapshot.metadata)
    semantics = metadata["graph"]["edge_semantics"]["grounded_in_doctrine"]
    assert "citation" in semantics and "not a check" in semantics
    assert metadata["doctrine_count"] == 49
    overview = json.loads(snapshot.overview)["data"]["explorer"]["doctrine"]
    assert overview["schema_version"] == "plectis_explorer_doctrine_v2"
    assert len(snapshot.overview) <= api.MAX_OVERVIEW_BYTES


def test_doctrine_routes_are_declared_in_openapi():
    from microcosm_core import component_api_contract as contract
    document = contract.openapi_document()
    assert {"/api/v1/doctrine", "/api/v1/doctrine/{rule_id}"} <= set(document["paths"])
    parameter = document["paths"]["/api/v1/doctrine/{rule_id}"]["get"]["parameters"][0]
    assert parameter["schema"]["pattern"] == "^(AX|P|AP)-[0-9]{1,3}$"
    schemas = document["components"]["schemas"]
    assert {"Doctrine", "DoctrineRule", "DoctrineRuleDetail", "AxiomDetail"} <= set(schemas)


@pytest.mark.parametrize("attack", ["witness", "statement", "support_basis", "extra", "schema", "reader_component", "reader_basis"])
def test_malformed_doctrine_snapshot_is_rejected(raw, attack):
    index = copy.deepcopy(raw)
    doctrine = index["explorer"]["doctrine"]
    axiom = doctrine["nodes"][0]
    if attack == "witness":
        axiom["axiom"]["routing"]["witness_component_ids"].append("not_a_component")
    elif attack == "statement":
        axiom["statement"] += " changed"
    elif attack == "support_basis":
        axiom["axiom"]["support"]["basis"] = "fresh_check"
    elif attack == "extra":
        doctrine["nodes"][-1]["axiom"] = axiom["axiom"]
    elif attack == "reader_component":
        doctrine["nodes"][-1]["reader"]["enforced_in_component_ids"].append("not_a_component")
    elif attack == "reader_basis":
        doctrine["nodes"][-1]["reader"]["basis"] = "test_result"
    else:
        doctrine["schema_version"] = "plectis_explorer_doctrine_v1"
    with pytest.raises(ValueError):
        api.ComponentSnapshot(index)


def test_encoded_overview_is_precomputed_and_has_distinct_validators(snapshot, monkeypatch):
    import gzip
    application = api.ComponentApplication(snapshot)

    def call(encoding, method="GET", etag=""):
        result = []
        body = b"".join(application({"REQUEST_METHOD": method, "PATH_INFO": "/api/v1/overview",
            "HTTP_ACCEPT_ENCODING": encoding, "HTTP_IF_NONE_MATCH": etag},
            lambda status, headers: result.append((int(status[:3]), dict(headers)))))
        return *result[0], body

    # Neither serialization nor compression may run on the overview read path.
    monkeypatch.setattr(api, "_encoded_response", lambda *args: pytest.fail("request-time compression"))
    status, headers, body = call("gzip")
    assert status == 200 and gzip.decompress(body) == snapshot.overview
    assert headers["Content-Encoding"] == "gzip" and headers["Vary"] == "Accept-Encoding"
    assert len(body) < len(snapshot.overview) // 2
    assert headers["ETag"] != snapshot.overview_etag
    status, head, empty = call("gzip", method="HEAD")
    assert status == 200 and empty == b"" and head["Content-Length"] == str(len(body))
    status, conditional, empty = call("gzip", etag=headers["ETag"])
    assert status == 304 and empty == b"" and "Content-Length" not in conditional
    assert conditional["Vary"] == "Accept-Encoding"
    status, identity, original = call("gzip;q=0")
    assert status == 200 and original == snapshot.overview and "Content-Encoding" not in identity
    status, _, original = call("identity", etag=headers["ETag"])
    assert status == 200 and original == snapshot.overview


@pytest.mark.parametrize("header,expected", [
    ("", "identity"), ("br, gzip;q=0.8", "gzip"), ("gzip;q=0, *;q=1", "identity"),
    ("*;q=1", "gzip"), ("gzip;q=0.2, identity;q=1", "identity"),
    ("gzip;q=1, identity;q=0", "gzip"), ("gzip;q=broken", "identity"),
])
def test_compression_negotiation(header, expected):
    assert api._response_encoding(header) == expected


def test_unacceptable_encoding_and_dynamic_cache_replacement(raw, transport, app):
    import gzip
    status, _, body = transport("/api/v1/components", headers={"Accept-Encoding": "gzip;q=0, identity;q=0"})
    assert status == 406 and json.loads(body)["error"]["code"] == "encoding_not_acceptable"
    status, first_headers, first = transport("/api/v1/components", headers={"Accept-Encoding": "gzip"})
    assert status == 200
    first_data = json.loads(gzip.decompress(first))
    app.replace_index(changed_index(raw))
    status, second_headers, second = transport("/api/v1/components", headers={"Accept-Encoding": "gzip", "If-None-Match": first_headers["ETag"]})
    assert status == 200 and second_headers["ETag"] != first_headers["ETag"]
    assert json.loads(gzip.decompress(second))["snapshot_revision"] != first_data["snapshot_revision"]


def test_map_overview_preserves_retained_fields_and_full_response(transport, snapshot):
    full_before = snapshot.overview
    full = json.loads(full_before)
    status, headers, body = transport('/api/v1/overview?view=map')
    assert status == 200 and body == snapshot.map_overview
    compact = json.loads(body)
    assert compact['snapshot_revision'] == full['snapshot_revision'] == snapshot.revision
    expected = copy.deepcopy(full)
    data = expected['data']
    del data['receipts'], data['wiring']
    cores_by_id = {row['core_id']: row for row in data['cores']}
    if data['explorer'].get('cores'):
        data['cores'] = [cores_by_id[row['core_id']] for row in data['explorer']['cores']]
    for key in ('receipt_summaries', 'proof_details', 'cores'):
        data['explorer'].pop(key, None)
    for component in data['components']:
        for receipt in component['receipt_refs']:
            for key in list(receipt):
                if key not in {'ref', 'artifact_id', 'availability', 'kind', 'reason', 'summary'}:
                    del receipt[key]
            if 'summary' in receipt:
                for key in list(receipt['summary']):
                    if key not in {'created_at', 'date_status', 'availability_reason', 'recorded_fields'}:
                        del receipt['summary'][key]
                fields = receipt['summary']['recorded_fields']
                for key in list(fields):
                    if key not in {'status', 'fixture_id', 'case_count'}:
                        del fields[key]
    assert compact == expected
    assert len(body) < len(full_before)
    assert headers['ETag'] != snapshot.overview_etag
    assert transport('/api/v1/overview')[2] == full_before == snapshot.overview


@pytest.mark.parametrize('query', ['view=', 'view=full', 'view=Map', 'view=map&view=map',
                                  'view=map&limit=1', 'view=map&extra=1', 'view=map%00'])
def test_map_overview_rejects_unsupported_query(app, query):
    status, _, body = wsgi(app, '/api/v1/overview', query)
    assert status == 400 and json.loads(body)['error']['code'] == 'invalid_parameters'


def test_map_overview_is_preencoded_for_get_head_and_conditional(snapshot, monkeypatch):
    import gzip
    application = api.ComponentApplication(snapshot, cache_size=0, cache_bytes=0)
    def forbidden(*args, **kwargs):
        pytest.fail('request attempted IO, compilation, serialization or compression')
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(component_index, 'compile_views', forbidden)
    monkeypatch.setattr(api, '_dispatch', forbidden)
    monkeypatch.setattr(api, '_json', forbidden)
    monkeypatch.setattr(api, '_map_overview', forbidden)
    monkeypatch.setattr(api, '_encoded_response', forbidden)
    def call(encoding, method='GET', etag=''):
        result = []
        body = b''.join(application({'REQUEST_METHOD': method, 'PATH_INFO': '/api/v1/overview',
            'QUERY_STRING': 'view=map', 'HTTP_ACCEPT_ENCODING': encoding, 'HTTP_IF_NONE_MATCH': etag},
            lambda status, headers: result.append((int(status[:3]), dict(headers)))))
        return *result[0], body
    validators = {snapshot.overview_etag, snapshot.overview_gzip_etag}
    for encoding in ('identity', 'gzip'):
        status, headers, body = call(encoding)
        assert status == 200 and headers['Vary'] == 'Accept-Encoding'
        assert headers['X-Plectis-Snapshot-Revision'] == snapshot.revision
        if encoding == 'gzip':
            assert body is snapshot.map_overview_gzip
            assert gzip.decompress(body) == snapshot.map_overview
            assert headers['Content-Encoding'] == 'gzip'
        else:
            assert body is snapshot.map_overview and 'Content-Encoding' not in headers
        assert headers['ETag'] not in validators
        validators.add(headers['ETag'])
        status, head, empty = call(encoding, 'HEAD')
        assert status == 200 and empty == b'' and head == headers
        assert head['Content-Length'] == str(len(body))
        status, conditional, empty = call(encoding, etag=headers['ETag'])
        assert status == 304 and empty == b'' and 'Content-Length' not in conditional
        assert conditional['ETag'] == headers['ETag']
        assert call(encoding, etag=snapshot.overview_etag)[0] == 200
    assert not application._cache and application._cached_bytes == 0


def test_map_overview_replacement_invalidates_both_representations(raw, app):
    previous = app._snapshot
    app.replace_index(changed_index(raw))
    current = app._snapshot
    assert current.revision != previous.revision
    assert current.map_overview_etag != previous.map_overview_etag
    assert current.map_overview_gzip_etag != previous.map_overview_gzip_etag
    status, headers, body = wsgi(app, '/api/v1/overview', 'view=map')
    assert status == 200 and body is current.map_overview
    assert json.loads(body)['snapshot_revision'] == current.revision


def test_map_overview_contract_describes_and_validates_both_views(snapshot):
    document = api.component_api_contract.openapi_document()
    validate_openapi(document)
    operation = document['paths']['/api/v1/overview']['get']
    view = next(row for row in operation['parameters'] if row['name'] == 'view')
    assert view['schema'] == {'enum': ['map']} and view['required'] is False
    schemas = document['components']['schemas']
    for name, payload in [('MapOverviewResponse', snapshot.map_overview), ('OverviewResponse', snapshot.overview)]:
        schema = {**schemas[name], 'components': {'schemas': schemas}}
        Draft202012Validator(schema).validate(json.loads(payload))
    schema = {**schemas['OverviewSelectionResponse'], 'components': {'schemas': schemas}}
    for payload in (snapshot.map_overview, snapshot.overview):
        Draft202012Validator(schema).validate(json.loads(payload))


def test_map_overview_preserves_retained_core_order_and_enriched_records(snapshot):
    full = json.loads(snapshot.overview)['data']
    compact = json.loads(snapshot.map_overview)['data']
    preferred = full['explorer'].get('cores') or full['cores']
    assert [row['core_id'] for row in compact['cores']] == [row['core_id'] for row in preferred]
    assert {row['core_id']: row for row in compact['cores']} == {row['core_id']: row for row in full['cores']}
    # Older indexes without the explorer list retain their top-level ordering.
    legacy = {**full, 'explorer': {key: value for key, value in full['explorer'].items() if key != 'cores'}}
    assert api._map_overview(legacy)['cores'] == full['cores']
