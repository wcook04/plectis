"""Serve the component explorer and proxy its API on one local origin.

The explorer is static files. Its browser code fetches relative ``/api/v1``
URLs; this server forwards those requests to ``plectis serve-components``
unchanged, so the page and the API share an origin without CORS. It adds no
route, executes nothing and reads no repository file outside ``frontend/``.
"""

from __future__ import annotations

import argparse
import http.client
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
FORWARD_REQUEST = ("Accept", "If-None-Match")
FORWARD_RESPONSE = ("Content-Type", "Content-Length", "ETag", "Cache-Control", "Allow",
                    "X-Content-Type-Options", "X-Plectis-Snapshot-Revision")
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
         ".json": "application/json; charset=utf-8", ".svg": "image/svg+xml",
         ".woff2": "font/woff2", ".png": "image/png", ".ico": "image/x-icon",
         ".txt": "text/plain; charset=utf-8"}
STATIC_DIRS = ("assets", "src")


class ExplorerHandler(BaseHTTPRequestHandler):
    server_version = "PlectisExplorer"
    sys_version = ""

    def do_GET(self):
        self._handle(send_body=True)

    def do_HEAD(self):
        self._handle(send_body=False)

    def _refuse(self):
        self._send(405, b'{"error":{"code":"method_not_allowed","message":"only GET and HEAD are available"}}',
                   {"Content-Type": "application/json; charset=utf-8", "Allow": "GET, HEAD"}, True)

    do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _refuse

    def _handle(self, send_body):
        path = urllib.parse.urlsplit(self.path).path
        if path == API_PREFIX or path.startswith(API_PREFIX + "/"):
            self._proxy(send_body)
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
        body = target.read_bytes()
        self._send(200, body, {"Content-Type": TYPES[target.suffix], "Cache-Control": "no-cache"}, send_body)

    def _send(self, status, body, headers, send_body):
        self.send_response(status)
        for name, value in headers.items():
            if name != "Content-Length":
                self.send_header(name, value)
        if status != 304:
            self.send_header("Content-Length", str(len(body)))
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
        super().__init__(address, ExplorerHandler)


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
