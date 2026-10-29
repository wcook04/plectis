"""The component explorer's development server: static shell and same-origin proxy.

The browser client fetches relative /api/v1 URLs. frontend/serve.py must pass
them to `plectis serve-components` unchanged (path, query, status, ETag,
snapshot revision, 304 and error bodies), serve only files below frontend/,
and answer client routes with the app shell. Its one route of its own serves
a component's or core's write-up only while the file's bytes match the
SHA-256 the served snapshot records for it.
"""

import hashlib
from http.client import HTTPConnection
import importlib.util
import json
from pathlib import Path
import threading
from wsgiref.simple_server import make_server

import pytest

from microcosm_core import component_http as api, component_index

ROOT = Path(__file__).resolve().parents[1]


def _load_serve():
    spec = importlib.util.spec_from_file_location("plectis_frontend_serve", ROOT / "frontend" / "serve.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _start(server):
    worker = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    worker.start()
    return worker


@pytest.fixture(scope="module")
def backend():
    index = json.loads((api.resource_root.microcosm_root() / component_index.INDEX_REF).read_text())
    app = api.ComponentApplication(api.ComponentSnapshot(index))
    server = make_server("127.0.0.1", 0, app, server_class=api.ComponentHTTPServer, handler_class=api._QuietHandler)
    worker = _start(server)
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    worker.join(timeout=5)


@pytest.fixture(scope="module")
def explorer(backend):
    serve = _load_serve()
    server = serve.ExplorerServer(("127.0.0.1", 0), backend)
    worker = _start(server)

    def request(path, method="GET", headers=None):
        client = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        try:
            client.request(method, path, headers=headers or {})
            response = client.getresponse()
            return response.status, {k.lower(): v for k, v in response.getheaders()}, response.read()
        finally:
            client.close()

    yield request
    server.shutdown()
    server.server_close()
    worker.join(timeout=5)


def test_client_routes_load_the_app_shell(explorer):
    for path in ("/", "/components/mcp_tool_authority_replay", "/proofs/proof%3A%3Adafny%3A%3Amcp_authority", "/coverage"):
        status, headers, body = explorer(path)
        assert status == 200
        assert headers["content-type"].startswith("text/html")
        assert b'src="/src/main.js"' in body
    status, headers, _ = explorer("/src/main.js")
    assert status == 200 and headers["content-type"].startswith("text/javascript")


def test_only_files_below_frontend_are_served(explorer):
    for path in ("/serve.py", "/src/../serve.py", "/assets/../../README.md", "/assets/%2e%2e/%2e%2e/README.md", "/src/missing.js"):
        status, _, body = explorer(path)
        assert status in (200, 404)
        assert b"ExplorerHandler" not in body and b"# Plectis" not in body
        if status == 200:
            assert b'src="/src/main.js"' in body


def test_api_requests_pass_through_unchanged(explorer, backend):
    status, headers, body = explorer("/api/v1/components?q=ownership&limit=2")
    assert status == 200
    envelope = json.loads(body)
    assert envelope["schema_version"] == "plectis_component_http_v1"
    assert headers["x-plectis-snapshot-revision"] == envelope["snapshot_revision"]
    assert headers["etag"].startswith('"')
    status, headers2, body2 = explorer("/api/v1/components?q=ownership&limit=2", headers={"If-None-Match": headers["etag"]})
    assert status == 304 and body2 == b""
    status, _, body = explorer("/api/v1/components/no_such_component")
    assert status == 404 and json.loads(body)["error"]["code"] == "unknown_id"
    status, _, body = explorer("/api/v1/components?q=%20")
    assert status == 400 and json.loads(body)["error"]["code"] == "invalid_parameters"
    status, headers, body = explorer("/api/v1/coverage", method="HEAD")
    assert status == 200 and body == b"" and headers["x-plectis-snapshot-revision"]


def test_writes_are_refused(explorer):
    status, headers, body = explorer("/api/v1/components", method="POST")
    assert status == 405 and headers["allow"] == "GET, HEAD"
    assert json.loads(body)["error"]["code"] == "method_not_allowed"


def test_an_unreachable_backend_is_a_gateway_error_not_data():
    serve = _load_serve()
    server = serve.ExplorerServer(("127.0.0.1", 0), "http://127.0.0.1:9")
    worker = _start(server)
    try:
        client = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        client.request("GET", "/api/v1")
        response = client.getresponse()
        assert response.status == 502
        assert response.getheader("Content-Type").startswith("text/plain")
        assert b"unreachable" in response.read()
        client.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_write_ups_are_served_when_they_match_the_snapshot(explorer):
    status, headers, body = explorer("/guides/component/mcp_tool_authority_replay")
    assert status == 200
    assert headers["content-type"].startswith("text/markdown")
    ref = headers["x-plectis-guide-ref"]
    assert ref == "paper_modules/mcp_tool_authority_replay.md"
    assert headers["etag"] == f'"{hashlib.sha256(body).hexdigest()}"'
    assert body == (ROOT / ref).read_bytes()
    status, headers, body = explorer("/guides/core/views")
    assert status == 200 and headers["x-plectis-guide-ref"].startswith("formal/")
    for path in ("/guides/component/no_such_component", "/guides/other/views", "/guides/component", "/guides/component/a/b"):
        status, _, body = explorer(path)
        assert status == 404 and json.loads(body)["error"]["code"] in ("not_found", "no_guide")


def test_a_changed_write_up_is_refused_not_served(backend, tmp_path):
    serve = _load_serve()
    guide = tmp_path / "paper_modules" / "mcp_tool_authority_replay.md"
    guide.parent.mkdir(parents=True)
    guide.write_text("# Edited after the index was built\n")
    serve.ROOT = tmp_path
    server = serve.ExplorerServer(("127.0.0.1", 0), backend)
    worker = _start(server)
    try:
        client = HTTPConnection("127.0.0.1", server.server_port, timeout=10)
        client.request("GET", "/guides/component/mcp_tool_authority_replay")
        response = client.getresponse()
        body = response.read()
        client.close()
        assert response.status == 409
        assert json.loads(body)["error"]["code"] == "stale_guide"
        assert b"Edited after" not in body
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
