from __future__ import annotations

import threading
from pathlib import Path
from urllib.request import urlopen

from microcosm_core import project_substrate
from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_observatory_landing_declares_explicit_theme_contract(tmp_path: Path) -> None:
    project = tmp_path / "scratch_project"
    (project / "src/app").mkdir(parents=True)
    (project / "README.md").write_text("# Scratch\n", encoding="utf-8")
    (project / "pyproject.toml").write_text("[project]\nname='scratch'\nversion='0.1.0'\n", encoding="utf-8")
    (project / "src/app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    project_substrate.init_project(project)
    project_substrate.index_project(project)
    project_substrate.propose_routes(project)
    project_substrate.explain_route(project, "readme_onboarding_route")
    created = project_substrate.create_work(project, "readme_onboarding_route")
    project_substrate.run_work(project, str(created["work_id"]))

    shell = RuntimeShell(MICROCOSM_ROOT)
    server = shell.serve("127.0.0.1", 0, project)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urlopen(f"http://{host}:{port}/", timeout=20) as response:
            html = response.read().decode("utf-8")
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert ":root { color-scheme: light; }" in html
    assert "background: #f8fafc" in html
    assert "color: #111827" in html
    assert ".panel { background: #ffffff" in html
    assert "a { color: #1d4ed8; }" in html
