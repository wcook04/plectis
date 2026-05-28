from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from microcosm_core import project_substrate
from microcosm_core.runtime_shell import RuntimeShell


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "demo_project"
    project.mkdir()
    (project / "README.md").write_text("# Demo Project\n\nA tiny public project.\n", encoding="utf-8")
    src = project / "src"
    src.mkdir()
    (src / "demo.py").write_text("def hello() -> str:\n    return 'hello'\n", encoding="utf-8")
    return project


def _get(url: str) -> bytes:
    last_error: Exception | None = None
    for _ in range(40):
        try:
            with urlopen(url, timeout=5) as response:
                return response.read()
        except URLError as exc:
            last_error = exc
            time.sleep(0.05)
    raise AssertionError(f"server did not answer {url}") from last_error


def test_project_serve_landing_is_lazy_without_full_observatory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(root=MICROCOSM_ROOT)

    def fail_full_observatory(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("full project observatory should be lazy for landing/card entry")

    monkeypatch.setattr(shell, "project_observatory", fail_full_observatory)
    port = _free_loopback_port()
    start = time.perf_counter()
    server = shell.serve("127.0.0.1", port, project)
    serve_setup_ms = (time.perf_counter() - start) * 1000
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        root = _get(f"http://127.0.0.1:{port}/").decode("utf-8")
        first_screen = json.loads(
            _get(f"http://127.0.0.1:{port}/project/first-screen").decode("utf-8")
        )
        first_screen_full = json.loads(
            _get(f"http://127.0.0.1:{port}/project/first-screen-full").decode(
                "utf-8"
            )
        )
        observatory_card = json.loads(
            _get(f"http://127.0.0.1:{port}/project/observatory-card").decode("utf-8")
        )
        tour = json.loads(_get(f"http://127.0.0.1:{port}/tour").decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert serve_setup_ms < 500
    assert "Microcosm Observatory" in root
    assert "/project/observatory-card" in root
    assert "/project/observatory" in root
    assert first_screen["schema_version"] == "microcosm_first_screen_compact_card_v1"
    assert first_screen_full["schema_version"] == (
        "microcosm_first_screen_composition_card_v1"
    )
    assert observatory_card["schema_version"] == "microcosm_project_observatory_card_v1"
    assert observatory_card["first_screen_endpoint"] == "/project/first-screen"
    assert observatory_card["first_screen_full_endpoint"] == (
        "/project/first-screen-full"
    )
    assert observatory_card["full_observatory_endpoint"] == "/project/observatory"
    assert tour["schema_version"] == "microcosm_tour_command_speed_card_v1"


def test_project_serve_full_observatory_embeds_compact_tour(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(root=MICROCOSM_ROOT)

    def fail_full_tour(*_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("served observatory should not rebuild the full tour")

    monkeypatch.setattr(shell, "tour", fail_full_tour)
    port = _free_loopback_port()
    server = shell.serve("127.0.0.1", port, project)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        observatory = json.loads(
            _get(f"http://127.0.0.1:{port}/project/observatory").decode("utf-8")
        )
        tour = json.loads(_get(f"http://127.0.0.1:{port}/tour").decode("utf-8"))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    assert observatory["schema_version"] == "microcosm_project_observatory_v1"
    assert observatory["tour"]["schema_version"] == "microcosm_tour_command_speed_card_v1"
    assert observatory["tour_payload_policy"]["embedded_tour_payload"] == "compact_card"
    assert tour["schema_version"] == "microcosm_tour_command_speed_card_v1"


def test_project_deep_drilldowns_defer_full_python_lens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(root=MICROCOSM_ROOT)
    original_python_lens = project_substrate.python_lens
    scan_modes: list[str] = []

    def tracked_python_lens(
        project_path: str | Path,
        *,
        write_state: bool = True,
        refresh_architecture: bool = True,
        scan_mode: str = project_substrate.PYTHON_LENS_SCAN_FULL,
    ) -> dict[str, object]:
        scan_modes.append(scan_mode)
        if scan_mode == project_substrate.PYTHON_LENS_SCAN_FULL:
            raise AssertionError("public drilldowns should defer full Python lens scans")
        return original_python_lens(
            project_path,
            write_state=write_state,
            refresh_architecture=refresh_architecture,
            scan_mode=scan_mode,
        )

    monkeypatch.setattr(project_substrate, "python_lens", tracked_python_lens)

    tour_card = shell.tour_card(project)
    tour = shell.tour(project, persist_receipt=False)
    observatory = shell.project_observatory(project, persist_receipts=False)

    assert tour_card["schema_version"] == "microcosm_tour_command_speed_card_v1"
    assert tour["schema_version"] == "microcosm_public_ten_minute_tour_v1"
    assert observatory["schema_version"] == "microcosm_project_observatory_v1"
    assert (
        observatory["python_lens"]["schema_version"]
        == "microcosm_project_python_lens_v1"
    )
    assert scan_modes
    assert set(scan_modes) == {project_substrate.PYTHON_LENS_SCAN_FIRST_SCREEN}
