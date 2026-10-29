"""Serve the component explorer and proxy its API on one local origin.

The explorer is static files. Its browser code fetches relative ``/api/v1``
URLs; this server forwards those requests to ``plectis serve-components``
unchanged, so the page and the API share an origin without CORS. It executes
nothing. Its one route of its own, ``/guides/component/<id>`` and
``/guides/core/<id>``, serves the write-up the snapshot names for that
component or core, read from this checkout only while its bytes match the
SHA-256 the served snapshot records for it; otherwise it answers 409.
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
import gzip
import re
import threading
import hashlib
import http.client
import json
import ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import subprocess
import sys
import urllib.parse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
API_PREFIX = "/api/v1"
# Request headers worth forwarding, and response headers the client reads.
FORWARD_REQUEST = ("Accept", "If-None-Match", "Accept-Encoding")
FORWARD_RESPONSE = ("Content-Type", "Content-Length", "Content-Encoding", "Vary", "ETag", "Cache-Control", "Allow",
                    "X-Content-Type-Options", "X-Plectis-Snapshot-Revision")
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml",
         ".woff2": "font/woff2", ".png": "image/png", ".ico": "image/x-icon",
         ".txt": "text/plain; charset=utf-8"}
STATIC_DIRS = ("assets", "src")
GUIDE_PREFIX = "/guides/"
GUIDE_ROOTS = ("paper_modules/", "formal/")
GUIDE_LIMIT = 256 * 1024
STATIC_CACHE_BYTES = 8 * 1024 * 1024
STATIC_CACHE_ENTRIES = 64
COMPRESSIBLE = {".html", ".js", ".mjs", ".css", ".json", ".svg", ".txt"}


def _static_encoding(value, compressible):
    """Negotiate cached text compression without importing the backend runtime."""
    if not value:
        return "identity"
    if len(value) > 2048:
        return None
    qualities = {}
    for entry in value.lower().split(","):
        token, *params = entry.strip().split(";")
        quality = 1.0
        for param in params:
            name, sep, raw = param.strip().partition("=")
            if name == "q" and sep:
                quality = float(raw) if re.fullmatch(r"(?:0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)", raw) else 0.0
        qualities[token.strip()] = quality
    gz = qualities.get("gzip", qualities.get("*", 0.0)) if compressible else 0.0
    identity = qualities.get("identity", 0.0 if qualities.get("*") == 0 else 1.0)
    if gz > 0 and ("identity" not in qualities or gz >= identity):
        return "gzip"
    return "identity" if identity > 0 else None


class ExplorerHandler(BaseHTTPRequestHandler):
    # Browsers can revalidate ETag-only API responses over HTTP/1.1.
    protocol_version = "HTTP/1.1"
    timeout = 15
    server_version = "PlectisExplorer"
    sys_version = ""

    def do_GET(self):
        self._handle(send_body=True)

    def do_HEAD(self):
        self._handle(send_body=False)

    def _refuse(self):
        # Do not parse an unread rejected request body as another request.
        self.close_connection = True
        self._send(405, b'{"error":{"code":"method_not_allowed","message":"only GET and HEAD are available"}}',
                   {"Content-Type": "application/json; charset=utf-8", "Allow": "GET, HEAD"}, True)

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _refuse

    def _handle(self, send_body):
        path = urllib.parse.urlsplit(self.path).path
        if path == API_PREFIX or path.startswith(API_PREFIX + "/"):
            self._proxy(send_body)
        elif path.startswith(GUIDE_PREFIX):
            self._guide(path, send_body)
        else:
            self._static(path, send_body)

    def _proxy(self, send_body):
        """Forward one request, keeping its path, query, status and headers."""
        headers = {name: self.headers[name] for name in FORWARD_REQUEST if self.headers.get(name)}
        connection = http.client.HTTPConnection(self.server.backend_host, self.server.backend_port, timeout=15)
        try:
            connection.request(self.command, self.path, headers=headers)
            response = connection.getresponse()
            body = response.read()
            kept = {name: response.getheader(name) for name in FORWARD_RESPONSE if response.getheader(name)}
            self._send(response.status, body, kept, send_body)
        except OSError:
            # The browser reports this as a failed network read, never as API data.
            self._send(502, b"component API unreachable", {"Content-Type": "text/plain; charset=utf-8",
                                                           "Cache-Control": "no-store"}, send_body)
        finally:
            connection.close()

    def _problem(self, status, code, message, send_body):
        body = json.dumps({"error": {"code": code, "message": message}}).encode()
        self._send(status, body, {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}, send_body)

    def _guide(self, path, send_body):
        """Serve one write-up, only while it matches the hash the snapshot records."""
        parts = path[len(GUIDE_PREFIX):].split("/")
        if len(parts) != 2 or parts[0] not in ("component", "core") or not parts[1]:
            self._problem(404, "not_found", "no such write-up route", send_body)
            return
        kind, ident = parts[0], urllib.parse.unquote(parts[1])
        route = "components" if kind == "component" else "cores"
        connection = http.client.HTTPConnection(self.server.backend_host, self.server.backend_port, timeout=15)
        try:
            connection.request("GET", f"{API_PREFIX}/{route}/{urllib.parse.quote(ident, safe='')}")
            response = connection.getresponse()
            status, raw = response.status, response.read()
        except OSError:
            self._send(502, b"component API unreachable", {"Content-Type": "text/plain; charset=utf-8",
                                                           "Cache-Control": "no-store"}, send_body)
            return
        finally:
            connection.close()
        if status != 200:
            self._problem(404 if status == 404 else 502, "not_found" if status == 404 else "api_error",
                          f"the component API answered {status}", send_body)
            return
        envelope = json.loads(raw)
        data = envelope.get("data") or {}
        if kind == "component":
            ref = (data.get("guide") or {}).get("ref")
            rows = [a for a in data.get("artifacts") or [] if a.get("availability") == "available"]
        else:
            ref = data.get("guide_ref")
            rows = data.get("artifact_bindings") or []
        digest = next((row.get("sha256") for row in rows if row.get("ref") == ref), None)
        if not ref or not digest or not ref.endswith(".md") or not ref.startswith(GUIDE_ROOTS) or ".." in ref:
            self._problem(404, "no_guide", "the snapshot records no write-up for this", send_body)
            return
        target = (ROOT / ref).resolve()
        if ROOT not in target.parents or not target.is_file() or target.stat().st_size > GUIDE_LIMIT:
            self._problem(404, "no_guide", "the write-up is not in this checkout", send_body)
            return
        body = target.read_bytes()
        if hashlib.sha256(body).hexdigest() != digest:
            self._problem(409, "stale_guide", "the write-up changed after the index was built", send_body)
            return
        self._send(200, body, {"Content-Type": "text/markdown; charset=utf-8", "Cache-Control": "no-cache",
                               "ETag": f'"{digest}"', "X-Plectis-Guide-Ref": ref,
                               "X-Plectis-Snapshot-Revision": str(envelope.get("snapshot_revision", ""))}, send_body)

    def _static(self, path, send_body):
        """Serve a file below frontend/, or the app shell for any page route."""
        relative = urllib.parse.unquote(path).lstrip("/")
        target = (HERE / relative).resolve() if relative else HERE / "index.html"
        top = relative.split("/", 1)[0]
        if top in STATIC_DIRS or relative in ("index.html", "favicon.ico"):
            if HERE not in target.parents or not target.is_file() or target.suffix not in TYPES:
                self._send(404, b"not found", {"Content-Type": "text/plain; charset=utf-8"}, send_body)
                return
        else:
            # Client-side routes (/components/<id>, /coverage, ...) all load the shell.
            target = HERE / "index.html"
        encoding = _static_encoding(self.headers.get("Accept-Encoding", ""), target.suffix in COMPRESSIBLE)
        if encoding is None:
            self._send(406, b"no acceptable asset encoding", {"Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store"}, send_body)
            return
        try:
            body, etag = self.server.static_asset(target, encoding)
        except OSError:
            self._send(404, b"not found", {"Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store"}, send_body)
            return
        headers = {"Content-Type": TYPES[target.suffix], "Cache-Control": "no-cache", "ETag": etag,
                   "Vary": "Accept-Encoding"}
        if encoding == "gzip":
            headers["Content-Encoding"] = "gzip"
        incoming = self.headers.get("If-None-Match", "")
        unchanged = len(incoming) <= 2048 and any(
            part.strip().removeprefix("W/") in {etag, "*"} for part in incoming.split(","))
        self._send(304 if unchanged else 200, b"" if unchanged else body, headers, send_body)

    def _send(self, status, body, headers, send_body):
        self.send_response(status)
        for name, value in headers.items():
            if name != "Content-Length":
                self.send_header(name, value)
        if status != 304:
            self.send_header("Content-Length", headers.get("Content-Length", str(len(body))))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        if send_body and status != 304:
            self.wfile.write(body)

    def log_message(self, format, *args):
        """Keep queries and identifiers out of the terminal by default."""


class ExplorerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, backend):
        parts = urllib.parse.urlsplit(backend)
        self.backend_host, self.backend_port = parts.hostname, parts.port or 80
        self._assets, self._asset_bytes = OrderedDict(), 0
        self._asset_pending = {}
        self._asset_lock = threading.Lock()
        super().__init__(address, ExplorerHandler)

    def static_asset(self, path, encoding):
        """Cache exact bytes; concurrent misses share work only for the same file."""
        while True:
            stat = path.stat()
            signature = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
            with self._asset_lock:
                cached = self._assets.get(path)
                if cached is not None and cached[0] == signature:
                    self._assets.move_to_end(path)
                    return cached[1][encoding]
                pending = self._asset_pending.get(path)
                if pending is None:
                    pending = self._asset_pending[path] = threading.Event()
                    break
            pending.wait()

        try:
            # Disk reads and compression for unrelated files proceed together.
            body = path.read_bytes()
            compressed = gzip.compress(body, compresslevel=6, mtime=0) if path.suffix in COMPRESSIBLE else None
            variants = {"identity": (body, '"' + hashlib.sha256(body).hexdigest() + '"')}
            if compressed is not None:
                variants["gzip"] = (compressed, '"' + hashlib.sha256(compressed).hexdigest() + '"')
            cost = len(body) + (len(compressed) if compressed is not None else 0)
            with self._asset_lock:
                previous = self._assets.pop(path, None)
                if previous is not None:
                    self._asset_bytes -= previous[2]
                if cost <= STATIC_CACHE_BYTES:
                    self._assets[path] = (signature, variants, cost)
                    self._asset_bytes += cost
                    while len(self._assets) > STATIC_CACHE_ENTRIES or self._asset_bytes > STATIC_CACHE_BYTES:
                        self._asset_bytes -= self._assets.popitem(last=False)[1][2]
            return variants[encoding]
        finally:
            with self._asset_lock:
                self._asset_pending.pop(path, None)
                pending.set()


def _start_backend(port):
    """Run the component API from this checkout as a child process."""
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [str(ROOT / "src"), os.environ.get("PYTHONPATH")])))
    child = subprocess.Popen([sys.executable, "-m", "plectis", "serve-components", "--port", str(port)],
                             cwd=ROOT, env=env, stdout=subprocess.PIPE, text=True)
    line = child.stdout.readline().strip()
    if child.poll() is not None or not line:
        raise SystemExit("explorer: the component API did not start")
    print(line, flush=True)
    return child


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8767, help="explorer port (default 8767)")
    parser.add_argument("--backend", default="http://127.0.0.1:8766", help="component API origin")
    parser.add_argument("--start-backend", action="store_true",
                        help="also start `plectis serve-components` from this checkout")
    args = parser.parse_args(argv)
    backend = urllib.parse.urlsplit(args.backend)
    if backend.scheme != "http" or not backend.hostname or not ipaddress.ip_address(backend.hostname).is_loopback:
        parser.error("--backend must be an http:// loopback address")
    child = _start_backend(backend.port or 80) if args.start_backend else None
    try:
        with ExplorerServer(("127.0.0.1", args.port), args.backend) as server:
            print(f"Component explorer: http://127.0.0.1:{server.server_port}/ (API proxied to {args.backend})",
                  flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        if child is not None:
            child.terminate()
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
