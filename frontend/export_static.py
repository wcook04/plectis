"""Export the component explorer as static files for a host with no server.

The explorer normally reads ``plectis serve-components`` through ``serve.py``.
This script starts both from this checkout on free loopback ports, requests
every response the explorer can ask for (metadata, the overview, coverage,
every component, proof and core, the full component list, the doctrine and every
rule, and the typed graph), and writes them under ``api/v1/`` beside a copy
of the frontend. Write-ups travel inside the component, core and proof records. In the copy, ``src/static-api.js`` answers the same API
URLs from those files; it computes component search, filters and paging, and
graph neighbourhoods, from the exported data.

Before writing anything final it checks that the static answers equal the
server's: the graph neighbourhood of every node at the default settings and
of the proved kernels and components at every depth and direction, every
kind of link, truncation, and the component list for every filter value and
a set of searches, paged. A mismatch fails the export.

Every page route gets its own HTML file with relative asset paths, so the
export works under any subpath, for example GitHub Pages at
``/practical-formal-verification/explorer/``. ``export.json`` records the
snapshot revision, the commit it was exported from, the time and the SHA-256
of every file. The snapshot revision shown on the pages is unchanged; the
map's footer adds that the page is a static copy and when it was exported.

    python3 frontend/export_static.py --out /path/to/explorer
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import html
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import serve  # noqa: E402  (the explorer's own server and backend launcher)

SCHEMA = "plectis_component_explorer_static_export_v1"
COPIED = ("assets", "src")
FILTER_FIELDS = ("family", "evidence_class", "real_substrate_disposition", "truth_accounting_bucket")
SEARCHES = ("owner", "replay", "proof", "receipt", "a", "zzzz-no-match", "  Dafny ")


def file_id(identity: str) -> str:
    """The exported file name for an ID; must match fileId() in src/static-api.js."""
    safe = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")
    return "".join(c if c in safe else f"~{ord(c):02x}" for c in identity)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Explorer:
    """The real explorer stack on loopback: backend child plus serve.py proxy."""

    def __init__(self):
        backend_port = free_port()
        self.child = serve._start_backend(backend_port)
        self.server = serve.ExplorerServer(("127.0.0.1", 0), f"http://127.0.0.1:{backend_port}")
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def get(self, path: str):
        try:
            with urllib.request.urlopen(self.base + path, timeout=30) as response:
                return response.status, response.read(), response.headers
        except urllib.error.HTTPError as error:
            return error.code, error.read(), error.headers

    def json(self, path: str, expect=200):
        status, body, _ = self.get(path)
        if status != expect:
            raise SystemExit(f"export: {path} answered {status}, expected {expect}")
        return json.loads(body)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.child.terminate()
        try:
            self.child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.child.kill()


def api(*segments: str, **query) -> str:
    path = "/".join(["/api/v1", *(urllib.parse.quote(s, safe="") for s in segments)])
    pairs = {k: v for k, v in query.items() if v is not None}
    return path + ("?" + urllib.parse.urlencode(pairs) if pairs else "")


def write_json(out: Path, rel: str, value) -> None:
    target = out / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True), encoding="utf-8")


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def collect(explorer: Explorer, out: Path) -> dict:
    """Write every API answer the explorer can request; return what the pages need."""
    meta = explorer.json(api())
    revision = meta["snapshot_revision"]
    write_json(out, "api/v1/index.json", meta)
    overview = explorer.json(api("overview"))
    for name in ("overview", "overview-map", "coverage", "local-runs", "doctrine"):
        body = (overview if name == "overview" else explorer.json(api("overview", view="map")) if name == "overview-map"
                else explorer.json(api(name)))
        if body["snapshot_revision"] != revision:
            raise SystemExit("export: the snapshot changed during the export")
        write_json(out, f"api/v1/{name}.json", body)

    items, cursor = [], None
    while True:
        page = explorer.json(api("components", limit="100", cursor=cursor))
        items += page["data"]["items"]
        cursor = page["data"]["next_cursor"]
        if not cursor:
            break
    write_json(out, "api/v1/components.json", {"schema_version": meta["schema_version"], "snapshot_revision": revision,
                                               "data": {"items": items, "total": len(items)}})

    data = overview["data"]
    component_ids = [row["organ_id"] for row in data["components"]]
    if sorted(component_ids) != [row["organ_id"] for row in items]:
        raise SystemExit("export: the overview and the component list disagree")
    proof_ids = [k["proof"]["proof_id"] for k in data["kernels"]]
    core_ids = [c["core_id"] for c in data.get("cores", [])]
    from microcosm_core.component_http import load_snapshot
    snapshot = load_snapshot()
    if snapshot.revision != revision:
        raise SystemExit("export: the in-process snapshot is not the one being served")
    rule_ids = sorted(snapshot.rules)
    for kind, ids in (("components", component_ids), ("proofs", proof_ids), ("cores", core_ids), ("doctrine", rule_ids)):
        for identity in ids:
            body = explorer.json(api(kind, identity))
            if body["snapshot_revision"] != revision:
                raise SystemExit("export: the snapshot changed during the export")
            write_json(out, f"api/v1/{kind}/{file_id(identity)}.json", body)

    # Write-ups travel inside the component, core and proof records, so a
    # missing one stays recorded as missing there.
    guides = {}
    for kind, ids in (("components", component_ids), ("proofs", proof_ids), ("cores", core_ids)):
        for identity in ids:
            body = json.loads((out / f"api/v1/{kind}/{file_id(identity)}.json").read_text(encoding="utf-8"))
            state = (body["data"].get("guide") or {}).get("availability", "unrecorded")
            guides[state] = guides.get(state, 0) + 1

    # The graph as data: every node record and every edge in the server's order.
    graph = {"nodes": [[kind, identity, json.loads(record)] for (kind, identity), record in sorted(snapshot.nodes.items())],
             "edges": [dict(edge) for edge in snapshot.edges], "edge_kinds": sorted(snapshot.edge_kinds)}
    write_json(out, "api/v1/graph.json", {"schema_version": meta["schema_version"], "snapshot_revision": revision, "data": graph})
    return {"meta": meta, "revision": revision, "components": component_ids, "proofs": proof_ids,
            "cores": core_ids, "rules": rule_ids, "core_proofs": [c["proof_id"] for c in data.get("cores", []) if c.get("proof_id")],
            "nodes": [(kind, identity) for kind, identity, _ in graph["nodes"]], "edge_kinds": graph["edge_kinds"],
            "guides": guides}


def parity_cases(explorer: Explorer, facts: dict) -> list:
    """Server answers that the static API must reproduce exactly."""
    cases = []

    def case(url, **extra):
        status, body, _ = explorer.get(url)
        cases.append({"url": url, "status": status, "body": json.loads(body), **extra})

    for kind, identity in facts["nodes"]:
        case(api("graph", type=kind, id=identity))
    focus = [("organ", i) for i in facts["components"]] + [("proof", i) for i in facts["proofs"]]
    for kind, identity in focus:
        for depth in ("2", "3"):
            for direction in ("both", "in", "out"):
                case(api("graph", type=kind, id=identity, depth=depth, direction=direction))
        case(api("graph", type=kind, id=identity, depth="3", max_edges="7"))
    for edge_kind in facts["edge_kinds"]:
        for kind, identity in focus[:3] + focus[-2:]:
            case(api("graph", type=kind, id=identity, depth="2", edge_kind=edge_kind))
    case(api("graph", type="organ", id="no_such_component"))
    case(api("graph", type="organ", id=facts["components"][0], depth="9"))
    case(api("graph", type="organ", id=facts["components"][0], direction="sideways"))

    queries = [{}]
    for field in FILTER_FIELDS:
        queries += [{field: str(row["value"])} for row in facts["meta"]["data"]["component_filters"].get(field, [])]
    queries += [{"q": q} for q in SEARCHES]
    first = facts["meta"]["data"]["component_filters"]
    queries.append({"q": "a", **{f: str(first[f][0]["value"]) for f in FILTER_FIELDS[:2] if first.get(f)}})
    for query in queries:
        for limit in ("7", "25", "100"):
            pages, cursor = [], None
            while True:
                status, body, _ = explorer.get(api("components", limit=limit, cursor=cursor, **query))
                page = json.loads(body)
                if status != 200:
                    raise SystemExit(f"export: component list {query} answered {status}")
                pages.append({k: page["data"][k] for k in ("items", "total", "limit")} | {"more": bool(page["data"]["next_cursor"])})
                cursor = page["data"]["next_cursor"]
                if not cursor:
                    break
            cases.append({"list": api("components", limit=limit, **query), "pages": pages})
    case(api("components", family="no_such_family"))
    case(api("components", q=" "))
    case(api("components", unknown="x"))
    case(api("components", facts["components"][0]))
    case(api("components", "no_such_component"))
    case(api("components", "Bad-ID"))
    case(api("proofs", facts["proofs"][0]))
    case(api("proofs", "proof::dafny::no_such_proof"))
    case(api("cores", facts["cores"][0]) if facts["cores"] else api())
    case(api("overview"))
    case(api("overview", view="map"))
    case(api("overview", view="full"))
    case(api("doctrine"))
    for rule in facts["rules"]:
        case(api("doctrine", rule))
    case(api("doctrine", "AX-999"))
    case(api("doctrine", "bad"))
    case(api("coverage"))
    case(api())
    return cases


def check_parity(out: Path, cases: list) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "cases.json"
        path.write_text(json.dumps(cases), encoding="utf-8")
        result = subprocess.run(["node", str(HERE / "tests" / "static_parity.mjs"), str(out), str(path)],
                                capture_output=True, text=True)
    sys.stdout.write(result.stdout)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit("export: the static answers differ from the server; nothing was published")


def page_html(shell: str, route: str, stamp: str) -> str:
    """index.html for one route, with paths relative to that route's file."""
    up = "../" * route.count("/")
    # Every root-relative href or src becomes relative to this page's file.
    text = re.sub(r'(href|src)="/"', lambda m: f'{m.group(1)}="{up or "./"}"', shell)
    text = re.sub(r'(href|src)="/(?!/)', lambda m: f'{m.group(1)}="{up}', text)
    if '="/' in text.replace('="//', ''):
        raise SystemExit("export: index.html has a root-relative path the export does not rewrite")
    text = text.replace("to read the local component API", "to draw the map")
    meta = f'  <meta name="plectis-static-export" content="{html.escape(stamp, quote=True)}">\n'
    return text.replace("  <meta name=\"viewport\"", meta + "  <meta name=\"viewport\"", 1)


def write_pages(out: Path, facts: dict, stamp: str) -> int:
    shell = (HERE / "index.html").read_text(encoding="utf-8")
    routes = ["", "catalogue", "coverage", "graph"]
    routes += [f"components/{i}" for i in facts["components"]]
    # Proof pages are addressed by kernel proof IDs, core IDs and core proof IDs.
    # A host decodes the URL before looking for the file, so the file keeps the ID.
    routes += [f"proofs/{i}" for i in sorted({*facts["proofs"], *facts["cores"], *facts["core_proofs"]})]
    for route in routes:
        target = out / (f"{route}.html" if route else "index.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page_html(shell, route, stamp), encoding="utf-8")
    return len(routes)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=HERE / "dist", help="output directory (replaced)")
    args = parser.parse_args(argv)
    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".explorer-export-", dir=out.parent))
    try:
        explorer = Explorer()
        try:
            facts = collect(explorer, staging)
            cases = parity_cases(explorer, facts)
        finally:
            explorer.close()
        for name in COPIED:
            shutil.copytree(HERE / name, staging / name, ignore=shutil.ignore_patterns(".DS_Store"))
        check_parity(staging, cases)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    commit = git("rev-parse", "HEAD")
    stamp_record = {"snapshot_revision": facts["revision"], "source_commit": commit,
                    "source_dirty": bool(git("status", "--porcelain", "--", "frontend", "src", "core", "paper_modules", "formal")),
                    "exported_at": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()}
    stamp = json.dumps(stamp_record, separators=(",", ":"), sort_keys=True)
    pages = write_pages(staging, facts, stamp)
    files = {p.relative_to(staging).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in sorted(staging.rglob("*")) if p.is_file()}
    write_json(staging, "export.json", {"schema_version": SCHEMA, **stamp_record, "pages": pages,
                                         "parity_cases": len(cases), "guides": facts["guides"], "files": files})
    if out.exists():
        shutil.rmtree(out)
    staging.rename(out)
    print(f"explorer export: {out} — snapshot {facts['revision'][:12]}, {pages} pages, {len(files)} files, "
          f"{len(cases)} parity cases equal to the server")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
