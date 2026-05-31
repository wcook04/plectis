from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

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


def _get_response(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 5,
) -> tuple[str, bytes]:
    last_error: Exception | None = None
    for _ in range(40):
        try:
            request = Request(url, headers=headers or {})
            with urlopen(request, timeout=timeout) as response:
                return response.headers.get("Content-Type", ""), response.read()
        except URLError as exc:
            last_error = exc
            time.sleep(0.05)
    raise AssertionError(f"server did not answer {url}") from last_error


def _get(url: str, *, timeout: float = 5) -> bytes:
    _content_type, body = _get_response(url, timeout=timeout)
    return body


def test_project_serve_quickstart_budget_covers_root_and_documented_drilldowns(
    tmp_path: Path,
) -> None:
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(root=MICROCOSM_ROOT)
    port = _free_loopback_port()
    server = shell.serve("127.0.0.1", port, project, max_requests=7)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    routes = [
        ("/", "text/html", None),
        ("/project/status", "application/json", "microcosm_runtime_status_card_v1"),
        (
            "/project/first-screen",
            "application/json",
            "microcosm_first_screen_compact_card_v1",
        ),
        (
            "/project/observatory-card",
            "application/json",
            "microcosm_project_observatory_card_v1",
        ),
        (
            "/workingness-card",
            "application/json",
            "microcosm_workingness_command_speed_card_v1",
        ),
        (
            "/project/first-screen-full",
            "application/json",
            "microcosm_first_screen_composition_card_v1",
        ),
        (
            "/project/observatory",
            "application/json",
            "microcosm_project_observatory_v1",
        ),
    ]
    seen_paths: list[str] = []

    try:
        for path, content_type_prefix, schema_version in routes:
            content_type, body = _get_response(
                f"http://127.0.0.1:{port}{path}",
                timeout=45,
            )
            seen_paths.append(path)
            assert content_type.startswith(content_type_prefix)
            if schema_version is None:
                assert b"Microcosm Observatory" in body
                continue
            payload = json.loads(body.decode("utf-8"))
            assert payload["schema_version"] == schema_version
        thread.join(timeout=5)
        assert not thread.is_alive()
    finally:
        if thread.is_alive():
            server.shutdown()
            thread.join(timeout=5)
        server.server_close()

    assert seen_paths == [path for path, _content_type, _schema in routes]


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
        status_card = json.loads(
            _get(f"http://127.0.0.1:{port}/project/status").decode("utf-8")
        )
        observatory_card = json.loads(
            _get(f"http://127.0.0.1:{port}/project/observatory-card").decode("utf-8")
        )
        projection_import_map = json.loads(
            _get(f"http://127.0.0.1:{port}/projection-import-map").decode("utf-8")
        )
        workingness_card = json.loads(
            _get(f"http://127.0.0.1:{port}/workingness-card").decode("utf-8")
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
    assert "/projection-import-map" in root
    assert first_screen["schema_version"] == "microcosm_first_screen_compact_card_v1"
    assert first_screen_full["schema_version"] == (
        "microcosm_first_screen_composition_card_v1"
    )
    assert status_card["schema_version"] == "microcosm_runtime_status_card_v1"
    assert status_card["status"] == "pass"
    assert status_card["front_door"]["project_state"]["status"] == "pass"
    assert status_card["front_door"]["state_write_proof"]["status"] == "pass"
    assert status_card["front_door"]["selected_route_id"] == "readme_onboarding_route"
    assert observatory_card["schema_version"] == "microcosm_project_observatory_card_v1"
    assert observatory_card["first_screen_endpoint"] == "/project/first-screen"
    assert observatory_card["first_screen_full_endpoint"] == (
        "/project/first-screen-full"
    )
    assert observatory_card["workingness_endpoint"] == "/workingness-card"
    assert observatory_card["workingness_drilldown_endpoint"] == "/workingness"
    assert observatory_card["full_observatory_endpoint"] == "/project/observatory"
    assert observatory_card["selected_route_id"] == "readme_onboarding_route"
    assert observatory_card["runtime_bridge"]["bridge_id"] == (
        "intake_observatory_bridge"
    )
    assert observatory_card["runtime_bridge"]["open_actionable_cell_count"] == 0
    assert observatory_card["runtime_bridge"]["endpoints"]["proof_lab"] == "/proof-lab"
    assert (
        observatory_card["runtime_bridge"]["projection_status_counts"][
            "runtime_bridge_landed"
        ]
        == 1
    )
    assert (
        projection_import_map["schema_version"]
        == "microcosm_public_projection_import_map_lens_v1"
    )
    assert projection_import_map["status"] == "pass"
    assert (
        workingness_card["schema_version"]
        == "microcosm_workingness_command_speed_card_v1"
    )
    assert workingness_card["endpoint"] == "/workingness-card"
    assert workingness_card["full_endpoint"] == "/workingness"
    assert "thing_failure_map" not in workingness_card
    assert tour["schema_version"] == "microcosm_tour_command_speed_card_v1"
    assert tour["selected_route_id"] == "readme_onboarding_route"


def test_project_serve_observatory_card_prefers_closed_work_transaction(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(root=MICROCOSM_ROOT)
    project_substrate.compile_project(
        project,
        python_lens_scan_mode=project_substrate.PYTHON_LENS_SCAN_FIRST_SCREEN,
    )
    created = project_substrate.create_work(
        project,
        "readme_onboarding_route",
        refresh_architecture=False,
    )
    assert created["work_id"] == "work_0002"
    explanation = project_substrate.explain_route(
        project,
        "readme_onboarding_route",
        refresh_architecture=False,
    )
    assert explanation["causal_chain_proof"]["selected_work_id"] == "work_0001"
    assert explanation["causal_chain_proof"]["selected_work_status"] == "closed"
    explanation_path = (
        project
        / project_substrate.STATE_DIR
        / "explanations"
        / "readme_onboarding_route.json"
    )
    stale_explanation = json.loads(explanation_path.read_text(encoding="utf-8"))
    stale_explanation["causal_chain_proof"]["selected_work_id"] = "work_0002"
    stale_explanation["causal_chain_proof"]["selected_work_status"] = "created"
    explanation_path.write_text(
        json.dumps(stale_explanation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    port = _free_loopback_port()
    server = shell.serve("127.0.0.1", port, project)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        status_card = json.loads(
            _get(f"http://127.0.0.1:{port}/project/status").decode("utf-8")
        )
        observatory_card = json.loads(
            _get(f"http://127.0.0.1:{port}/project/observatory-card").decode("utf-8")
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    route_explanation = status_card["front_door"]["route_explanation"]
    work_transaction = observatory_card["causal_chain_summary"]["work_transaction"]
    assert route_explanation["selected_work_id"] == "work_0001"
    assert route_explanation["selected_work_status"] == "closed"
    assert observatory_card["surface_statuses"]["work"] == "pass"
    assert work_transaction["work_id"] == "work_0001"
    assert work_transaction["status"] == "closed"
    assert work_transaction["source_files_mutated"] is False


def test_project_serve_json_drilldowns_negotiate_browser_html(tmp_path: Path) -> None:
    project = _scratch_project(tmp_path)
    shell = RuntimeShell(root=MICROCOSM_ROOT)
    port = _free_loopback_port()
    server = shell.serve("127.0.0.1", port, project)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        api_content_type, api_body = _get_response(
            f"http://127.0.0.1:{port}/project/observatory",
            headers={"Accept": "application/json"},
            timeout=45,
        )
        browser_content_type, browser_body = _get_response(
            f"http://127.0.0.1:{port}/project/observatory",
            headers={
                "Accept": (
                    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                )
            },
            timeout=45,
        )
        default_content_type, default_body = _get_response(
            f"http://127.0.0.1:{port}/project/observatory",
            timeout=45,
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()

    api_payload = json.loads(api_body.decode("utf-8"))
    default_payload = json.loads(default_body.decode("utf-8"))
    browser_html = browser_body.decode("utf-8")

    assert api_content_type.startswith("application/json")
    assert default_content_type.startswith("application/json")
    assert api_payload["schema_version"] == "microcosm_project_observatory_v1"
    assert default_payload["schema_version"] == "microcosm_project_observatory_v1"
    assert browser_content_type.startswith("text/html")
    assert "Microcosm JSON Drilldown" in browser_html
    assert "/project/observatory" in browser_html
    assert "microcosm_project_observatory_v1" in browser_html
    assert 'data-format="application/json"' in browser_html


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
            _get(
                f"http://127.0.0.1:{port}/project/observatory",
                timeout=45,
            ).decode("utf-8")
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
