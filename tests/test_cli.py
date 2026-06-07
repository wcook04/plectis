from __future__ import annotations

import contextlib
from collections import Counter
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

from microcosm_core import cli
from microcosm_core import project_substrate
from microcosm_core import runtime_evidence_index
from microcosm_core.runtime_shell import (
    PRODUCT_PATH_DEMOTED_ORGAN_IDS,
    PROOF_LAB_FIRST_SCREEN_COMMAND,
    PROOF_LAB_RECEIPT_REF,
    PROOF_LAB_ROUTE_REF,
    RuntimeShell,
    SOURCE_OPEN_BODY_POLICY,
    VERIFIER_EXECUTION_LENS_COMMAND,
    VERIFIER_EXECUTION_RECEIPT_REF,
)
from runtime_fixture_tree import copy_microcosm_runtime_root, copytree_fixture


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
ROOT_HELP_COMMAND_FLOOR = 35
ROOT_COMMAND_DOCS = (
    "README.md",
    "QUICKSTART.md",
    "AGENTS.md",
    "ARCHITECTURE.md",
    "SECURITY.md",
)


def _accepted_registry_rows(root: Path) -> list[dict[str, object]]:
    registry = json.loads((root / "core/organ_registry.json").read_text(encoding="utf-8"))
    return [
        row
        for row in registry["implemented_organs"]
        if row.get("status") == "accepted_current_authority"
    ]


def _accepted_organ_count(root: Path) -> int:
    return len(_accepted_registry_rows(root))


def _demoted_organ_count() -> int:
    return len(PRODUCT_PATH_DEMOTED_ORGAN_IDS)


def _adapter_backed_organ_count(root: Path) -> int:
    return _accepted_organ_count(root) - _demoted_organ_count()


def _adapter_registry_rows(root: Path) -> list[dict[str, object]]:
    demoted = set(PRODUCT_PATH_DEMOTED_ORGAN_IDS)
    return [
        row
        for row in _accepted_registry_rows(root)
        if row.get("organ_id") not in demoted
    ]


def _adapter_evidence_class_count(root: Path) -> int:
    return len(_expected_adapter_evidence_class_counts(root))


def _expected_adapter_evidence_class_counts(root: Path) -> dict[str, int]:
    return dict(
        Counter(str(row["evidence_class"]) for row in _adapter_registry_rows(root))
    )


def _expected_adapter_truth_bucket_counts(root: Path) -> dict[str, int]:
    return dict(
        Counter(
            str(row["truth_accounting_bucket"])
            for row in _adapter_registry_rows(root)
        )
    )


def _first_run_path_by_step_id(path: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    by_step = {str(row.get("step_id")): row for row in path if row.get("step_id")}
    assert len(by_step) == len(path)
    return by_step


def _assert_commands_in_order(
    path: list[dict[str, object]],
    expected_commands: list[str],
) -> None:
    commands = [str(row.get("command") or "") for row in path]
    cursor = -1
    for command in expected_commands:
        assert command in commands[cursor + 1 :]
        cursor = commands.index(command, cursor + 1)


def _assert_step_command(
    by_step: dict[str, dict[str, object]],
    step_id: str,
    command: str,
) -> None:
    assert by_step[step_id]["command"] == command


def _assert_step_command_prefix(
    by_step: dict[str, dict[str, object]],
    step_id: str,
    command_prefix: str,
) -> None:
    assert str(by_step[step_id]["command"]).startswith(command_prefix)


def _copy_public_entry_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    copytree_fixture(
        MICROCOSM_ROOT / "core",
        public_root / "core",
        prefer_hardlinks=False,
    )
    copytree_fixture(MICROCOSM_ROOT / "atlas", public_root / "atlas")
    copytree_fixture(MICROCOSM_ROOT / "paper_modules", public_root / "paper_modules")
    copytree_fixture(MICROCOSM_ROOT / "skills", public_root / "skills")
    (public_root / "src/microcosm_core").mkdir(parents=True)
    shutil.copy2(
        MICROCOSM_ROOT / "src/microcosm_core/cli.py",
        public_root / "src/microcosm_core/cli.py",
    )
    shutil.copy2(MICROCOSM_ROOT / "README.md", public_root / "README.md")
    shutil.copy2(MICROCOSM_ROOT / "AGENTS.md", public_root / "AGENTS.md")
    shutil.copy2(MICROCOSM_ROOT / "AGENT_ROUTES.md", public_root / "AGENT_ROUTES.md")
    (public_root / "receipts/first_wave").mkdir(parents=True)
    return public_root


def _copy_runtime_root(tmp_path: Path) -> Path:
    return copy_microcosm_runtime_root(
        tmp_path,
        MICROCOSM_ROOT,
        static_refs=("examples", "src", "standards"),
        mutable_refs=(
            "core",
            "receipts/first_wave",
            "receipts/preflight",
            "receipts/runtime_shell/demo_project",
        ),
    )


def _copy_workingness_root(tmp_path: Path) -> Path:
    return _copy_runtime_root(tmp_path)


def _make_scratch_project(tmp_path: Path) -> Path:
    project = tmp_path / "scratch"
    (project / "src/app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Scratch\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        '[project]\nname = "scratch"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (project / "src/app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "tests/test_app.py").write_text(
        "from app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    return project


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _read_local_json(port: int, path: str, *, timeout: float = 5.0) -> dict:
    with urlopen(f"http://127.0.0.1:{port}{path}", timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _microcosm_cli_env() -> dict[str, str]:
    env = os.environ.copy()
    src_ref = str(MICROCOSM_ROOT / "src")
    env["PYTHONPATH"] = (
        src_ref
        if not env.get("PYTHONPATH")
        else f"{src_ref}{os.pathsep}{env['PYTHONPATH']}"
    )
    return env


def _run_microcosm_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "microcosm_core.cli", *args],
        cwd=MICROCOSM_ROOT,
        env=_microcosm_cli_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
    )


def _run_microcosm_cli_in_process(*args: str) -> subprocess.CompletedProcess[str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            return_code = cli.main(list(args))
    except SystemExit as exc:
        return_code = exc.code if isinstance(exc.code, int) else 1
    return subprocess.CompletedProcess(
        [sys.executable, "-m", "microcosm_core.cli", *args],
        return_code,
        stdout.getvalue(),
        stderr.getvalue(),
    )


def _root_help_command_names(help_output: str) -> list[str]:
    commands: list[str] = []
    in_positional_arguments = False
    for line in help_output.splitlines():
        if line == "positional arguments:":
            in_positional_arguments = True
            continue
        if line == "options:":
            break
        if (
            not in_positional_arguments
            or not line.startswith("    ")
            or line.startswith("      ")
        ):
            continue
        command_name = line.split(maxsplit=1)[0]
        if command_name != "<command>":
            commands.append(command_name)
    return commands


def _documented_microcosm_command_names() -> set[str]:
    command_names: set[str] = set()
    pattern = re.compile(r"`(microcosm\s+[^`\n]*(?:\n[^`]*)?)`")
    for relpath in ROOT_COMMAND_DOCS:
        text = (MICROCOSM_ROOT / relpath).read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            normalized = " ".join(match.group(1).split())
            parts = normalized.split()
            if len(parts) < 2 or parts[1].startswith("-"):
                continue
            command_names.add(parts[1])
    return command_names


def _strip_markdown_fenced_blocks(text: str) -> str:
    return re.sub(
        r"```.*?```",
        lambda match: "\n" * match.group(0).count("\n"),
        text,
        flags=re.S,
    )


def _bare_documented_microcosm_command_spans(command_names: set[str]) -> list[str]:
    failures: list[str] = []
    pattern = re.compile(r"`([^`]+)`")
    for relpath in ROOT_COMMAND_DOCS:
        text = (MICROCOSM_ROOT / relpath).read_text(encoding="utf-8")
        scan_text = _strip_markdown_fenced_blocks(text)
        for match in pattern.finditer(scan_text):
            normalized = " ".join(match.group(1).split())
            parts = normalized.split()
            if len(parts) < 2 or parts[0] == "microcosm":
                continue
            if parts[0] not in command_names:
                continue
            line = text[: match.start()].count("\n") + 1
            failures.append(f"{relpath}:{line}: `{normalized}`")
    return failures


def _assert_body_floor_blocking_details(details: dict) -> None:
    assert details["status"] == "blocked"
    assert details["defect_count"] >= 1
    assert details["defect_preview"]
    first_defect = details["defect_preview"][0]
    assert first_defect["target_ref"]
    assert first_defect["defect_codes"]
    assert first_defect["body_text_in_receipt"] is False
    assert details["full_defects_ref"] == (
        "microcosm status::macro_body_import_floor.defects"
    )


def _expected_actionable_surface_ids(front_door_status: dict) -> set[str]:
    return {
        surface_id
        for surface_id, status in front_door_status["surface_statuses"].items()
        if status == "actionable"
    }


def test_package_metadata_describes_runtime_spine() -> None:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload["project"]
    description = project["description"]

    assert "repo -> .microcosm" in description
    assert "inspectable work substrate" in description
    assert "first-slice" not in description
    assert project["readme"] == "README.md"
    assert project["license"] == "Apache-2.0"
    assert project["license-files"] == ["LICENSE"]
    assert project["authors"] == [
        {"name": "William Cook", "email": "williamwkcook@gmail.com"}
    ]
    assert project["optional-dependencies"]["test"] == [
        "numpy>=2,<3",
        "pandas>=3,<4",
        "pytest>=8,<9",
        "requests>=2,<3",
    ]
    assert "License :: OSI Approved :: Apache Software License" not in project["classifiers"]
    assert payload["project"]["urls"]["Homepage"] == "https://github.com/wcook04/microcosm-substrate"
    assert payload["project"]["urls"]["Source"].endswith("/microcosm-substrate")
    assert "Macro-System" not in payload["project"]["urls"]
    assert (MICROCOSM_ROOT / "LICENSE").read_text(encoding="utf-8").startswith("Apache License")


def test_cli_help_routes_cold_readers_before_drilldown_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    first_line = output.splitlines()[0]
    assert first_line == "usage: microcosm [-h] [--version] <command> ..."
    assert "{init,index" not in first_line
    assert "First-screen route:" in output
    assert (
        "microcosm hello --reader "
        "{cold_cloner|skeptical_reviewer|agent|domain_specialist} "
        "<project> branch by reader"
    ) in output
    assert (
        "reader aliases: cold-cloner, interesting-parts, skeptical-reviewer, "
        "reviewer, type-a-agent, domain-specialist"
    ) in output
    assert (
        "microcosm tour --card <project> build .microcosm and read "
        "route/state/proof refs"
    ) in output
    assert (
        "microcosm first-screen --card <project> emit the compact JSON "
        "first-screen card"
        in output
    )
    assert (
        "microcosm agent-entry-composition --task "
        "{agent-entry|ai-safety|evaluation|finance|formal-methods|interesting-parts|reviewer} emit Type A/human route card"
    ) in output
    assert "microcosm agent-entry-composition --task agent-entry emit" not in output
    assert (
        "microcosm status --card <project> read the compressed "
        "project/runtime status lens"
    ) in output
    assert (
        "microcosm status-card <project> alias for the compact status lens"
        in output
    )
    assert "microcosm spine --card          read the compact runtime spine lens" in output
    assert (
        "microcosm run --card examples/runtime_shell/demo_project replay the public "
        "runtime demo"
    ) in output
    assert "microcosm authority --card      read the compact authority ceiling lens" in output
    assert (
        "microcosm intake --card         read the compact intake/projection bridge lens"
        in output
    )
    assert (
        "microcosm workingness --card    read the compact behavior/failure lens"
        in output
    )
    assert "microcosm workingness           inspect behavior evidence and failure gaps" in output
    assert "microcosm proof-lab --card      read the cached verifier-lab receipt card" in output
    assert "microcosm proof-lab --out /tmp/microcosm-proof-lab" in output
    assert (
        "microcosm observe --card <project> read compact route/work/event/evidence refs"
        in output
    )
    assert (
        "microcosm observe <project>     inspect route/work/event/evidence chain"
        in output
    )
    assert "microcosm serve <project>       open the local observatory" in output
    assert (
        "microcosm compile --card <project> read cached .microcosm state; "
        "stale cache exits 1"
    ) in output
    assert (
        "microcosm compile <project>     rebuild local .microcosm state "
        "after the first-screen check"
    ) in output
    assert output.index("microcosm tour --card <project>") < output.index(
        "microcosm first-screen --card <project>"
    )
    assert output.index("microcosm first-screen --card <project>") < (
        output.index("microcosm status --card <project>")
    )
    assert output.index("microcosm status --card <project>") < output.index(
        "microcosm status-card <project>"
    )
    assert output.index("microcosm status-card <project>") < output.index(
        "microcosm spine --card"
    )
    assert output.index("microcosm spine --card") < output.index(
        "microcosm run --card examples/runtime_shell/demo_project"
    )
    assert output.index(
        "microcosm run --card examples/runtime_shell/demo_project"
    ) < output.index("microcosm authority --card")
    assert output.index("microcosm authority --card") < output.index(
        "microcosm intake --card"
    )
    assert output.index("microcosm intake --card") < output.index(
        "microcosm workingness --card"
    )
    assert output.index("microcosm workingness --card") < output.index(
        "microcosm workingness           inspect behavior evidence and failure gaps"
    )
    assert output.index("microcosm workingness") < output.index(
        "microcosm proof-lab --card"
    )
    assert output.index("microcosm proof-lab --card") < output.index(
        "microcosm proof-lab --out /tmp/microcosm-proof-lab"
    )
    assert output.index(
        "microcosm proof-lab --out /tmp/microcosm-proof-lab"
    ) < output.index("microcosm serve <project>")
    assert output.index("microcosm serve <project>") < output.index(
        "microcosm compile --card <project>"
    )
    assert output.index("microcosm compile --card <project>") < output.index(
        "microcosm compile <project>"
    )
    assert output.index("microcosm compile <project>") < output.index(
        "microcosm tour <project>        inspect full route cards"
    )
    assert "no provider calls, source mutation, release," in output
    assert "Receipts are evidence drilldowns after the behavior route is visible." in output
    for command in [
        "init",
        "index",
        "catalog",
        "architecture",
        "compile",
        "python-lens",
        "graph",
        "explain",
        "status",
        "proof-lab",
        "spine",
        "tour",
        "first-screen",
        "authority",
        "run",
        "pattern-route-readiness",
        "finance-forecast-evaluation-spine",
        "finance-eval-spine",
        "executable-doctrine-grammar",
        "formal-math-readiness-gate",
        "standards-meta-diagnostics",
        "cold-reader-route-map",
        "macro-projection-import-protocol",
        "agent-route-observability-runtime",
        "bridge-phase-continuity-runtime",
        "voice-to-doctrine-self-improvement-loop",
        "routing-anti-patterns-registry",
        "serve",
        "patterns",
        "route",
        "work",
        "evidence",
    ]:
        assert command in output

    for command in [
        "workingness",
        "prediction-lens",
        "market-boundary",
        "corpus-lens",
        "trace-lens",
        "repair-loop",
        "evidence-cells",
        "proof-loop-depth",
        "verifier-lab-execution-spine-lens",
        "landing-replay",
        "view-quality",
        "projection-safety",
        "drift-control",
        "spatial-simulation",
        "circuit-attribution",
        "route-cleanup",
        "projection-import-map",
        "import-projector",
        "option-surface-lens",
        "stripping-guard",
        "standards-control",
        "hook-coverage",
        "replay-gauntlet",
        "benchmark-lab",
        "legibility-scorecard",
        "intake",
        "reveal",
    ]:
        assert command in output
    for help_text in [
        "inspect proof loop depth without proving correctness",
        "show navigation route cleanup evidence",
        "show runtime projection intake board",
        "show public reveal walkthrough board",
        "replay the local public runtime demo",
        "show project route/work/event/evidence graph",
        "inspect project pattern observations",
        "list runtime routes or project route candidates",
        "create or run project-local reversible work",
        "validate pattern route-readiness bundle",
        "validate finance-evaluation fixture bundle",
        "validate executable doctrine bundles",
        "run formal math readiness bundle",
        "run standards meta-diagnostics bundle",
        "run cold-reader route-map bundle",
        "run macro projection import bundle",
        "validate route observability bundles",
        "run bridge continuity bundle",
        "run voice-to-doctrine bundle",
        "run routing anti-patterns registry bundle",
        "create project-local .microcosm state",
        "classify project files into public repo roles",
        "show project architecture-kernel primitives",
    ]:
        assert help_text in output
    for drilldown_command in [
        "private-state-scan",
        "verifier-lab-kernel",
        "agentic-vulnerability-discovery-patch-proof-replay",
    ]:
        assert drilldown_command not in output


def test_cli_root_help_listed_commands_have_help_routes() -> None:
    root_help = _run_microcosm_cli_in_process("--help")
    assert root_help.returncode == 0, root_help.stderr
    commands = _root_help_command_names(root_help.stdout)

    assert len(commands) >= ROOT_HELP_COMMAND_FLOOR
    assert len(commands) == len(set(commands))

    failures: list[str] = []
    for command in commands:
        command_help = _run_microcosm_cli_in_process(command, "--help")
        if command_help.returncode != 0:
            failures.append(
                f"{command}: rc={command_help.returncode} stderr={command_help.stderr[-500:]}"
            )
            continue
        if f"usage: microcosm {command}" not in command_help.stdout:
            failures.append(f"{command}: missing command-specific usage line")

    assert not failures, "\n".join(failures)


def test_cli_status_card_help_explains_alias_and_boundaries() -> None:
    help_result = _run_microcosm_cli("status-card", "--help")

    assert help_result.returncode == 0, help_result.stderr
    output = help_result.stdout
    assert "usage: microcosm status-card [-h] [project]" in output
    assert "Alias for the compact first-screen project/runtime status lens." in output
    assert "project path with .microcosm state; omit for runtime-only status" in output
    assert "Equivalent command:" in output
    assert "microcosm status --card <project>" in output
    assert "Next command:" in output
    assert "microcosm tour --card <project>" in output
    assert "Boundaries: local-first only; no provider calls" in output
    assert "credential-equivalent live-access authority" in output


def test_cli_status_help_names_cold_clone_check_path() -> None:
    help_result = _run_microcosm_cli("status", "--help")

    assert help_result.returncode == 0, help_result.stderr
    output = help_result.stdout
    assert "Cold-clone check path:" in output
    assert "microcosm status --card <project>" in output
    assert "make check" in output
    assert "make smoke" in output
    assert "make ci" in output
    assert "status card is the compact route/state/evidence lens" in output
    assert "fast preflight" in output
    assert "public green floor" in output
    assert "authorize release" in output
    assert "provider calls" in output
    assert "source mutation" in output
    assert "proof" in output
    assert "whole-system" in output


def test_cli_agent_entry_composition_help_describes_task_route_selector() -> None:
    help_result = _run_microcosm_cli("agent-entry-composition", "--help")

    assert help_result.returncode == 0, help_result.stderr
    assert "task string to normalize into an agent task route" in help_result.stdout
    assert "task string to normalize into the agent-entry route" not in help_result.stdout
    assert "Task selector examples:" in help_result.stdout
    assert (
        "microcosm agent-entry-composition --task evaluation --viewer human --card --check"
        in help_result.stdout
    )
    assert (
        "reviewer, skeptical-reviewer, and skeptical-review route to the\n"
        "ai-safety task route"
    ) in help_result.stdout
    assert (
        "Use evaluation for the cold route-map/receipt evaluator\n"
        "path; receipt/evidence meaning questions route there too"
    ) in help_result.stdout
    assert '"What is interesting here?" routes to\ninteresting-parts' in help_result.stdout
    assert (
        '"Show me formal methods" routes to formal-methods'
        in help_result.stdout
    )
    assert "does\nnot authorize release, provider calls" in help_result.stdout


def test_cli_evidence_help_explains_receipt_interpretation() -> None:
    help_result = _run_microcosm_cli("evidence", "--help")

    assert help_result.returncode == 0, help_result.stderr
    output = help_result.stdout
    assert "Reviewer path:" in output
    assert "microcosm evidence list <project> --limit 25" in output
    assert "microcosm evidence inspect --project <project> <evidence_ref>" in output
    assert "Receipts are evidence drilldowns after behavior is visible" in output
    assert "source refs, schema versions, command witnesses" in output
    assert "not by themselves authorize release" in output
    assert "provider calls" in output
    assert "source mutation" in output
    assert "proof" in output
    assert "correctness" in output
    assert "whole-system" in output


def test_cli_public_reveal_walkthrough_help_names_fixture_and_boundary() -> None:
    help_result = _run_microcosm_cli("public-reveal-walkthrough", "--help")

    assert help_result.returncode == 0, help_result.stderr
    output = help_result.stdout
    assert "Runnable fixture example:" in output
    assert (
        "microcosm public-reveal-walkthrough run --input "
        "fixtures/first_wave/public_reveal_walkthrough/input --out "
        "/tmp/microcosm-public-reveal-walkthrough"
    ) in output
    assert "validates bounded public reveal behavior" in output
    assert "does\nnot authorize release" in output
    assert "hosted deployment" in output
    assert "provider\ncalls" in output
    assert "private-data equivalence" in output
    assert "whole-system correctness" in output


def test_cli_agent_benchmark_integrity_help_names_fixture_and_boundary() -> None:
    help_result = _run_microcosm_cli(
        "agent-benchmark-integrity-anti-gaming-replay",
        "--help",
    )

    assert help_result.returncode == 0, help_result.stderr
    output = help_result.stdout
    assert "Runnable fixture example:" in output
    assert (
        "microcosm agent-benchmark-integrity-anti-gaming-replay "
        "run-benchmark-integrity-bundle --input "
        "examples/agent_benchmark_integrity_anti_gaming_replay/"
        "exported_benchmark_integrity_bundle --out "
        "/tmp/microcosm-agent-benchmark-integrity"
    ) in output
    assert "validates a public benchmark-integrity replay bundle" in output
    assert "does not run a live benchmark" in output
    assert "score agent capability" in output
    assert "call\nproviders" in output
    assert "access private or hidden-gold bodies" in output
    assert "authorize release" in output


def test_root_doc_microcosm_commands_are_discoverable_from_root_help() -> None:
    root_help = _run_microcosm_cli("--help")
    assert root_help.returncode == 0, root_help.stderr
    help_commands = set(_root_help_command_names(root_help.stdout))

    missing = sorted(_documented_microcosm_command_names() - help_commands)

    assert not missing


def test_root_doc_command_spans_include_microcosm_entrypoint() -> None:
    root_help = _run_microcosm_cli("--help")
    assert root_help.returncode == 0, root_help.stderr
    command_names = (
        set(_root_help_command_names(root_help.stdout))
        | set(cli.PUBLIC_BUNDLE_COMMAND_HELP)
        | {command for command, _ in cli.PUBLIC_LENS_COMMAND_HELP}
    )

    failures = _bare_documented_microcosm_command_spans(command_names)

    assert not failures, "\n".join(failures)


def test_cli_work_help_exposes_route_explanation_actions() -> None:
    root_help = _run_microcosm_cli("--help")
    assert root_help.returncode == 0, root_help.stderr
    assert "work" in _root_help_command_names(root_help.stdout)
    assert "create or run project-local reversible work" in root_help.stdout
    assert "transactions" in root_help.stdout

    work_help = _run_microcosm_cli("work", "--help")
    assert work_help.returncode == 0, work_help.stderr
    assert "usage: microcosm work" in work_help.stdout
    assert "create" in work_help.stdout
    assert "run" in work_help.stdout
    assert "record a project-local work transaction from a selected" in work_help.stdout
    assert "route" in work_help.stdout
    assert "execute the project-local work transaction simulation" in work_help.stdout

    create_help = _run_microcosm_cli("work", "create", "--help")
    assert create_help.returncode == 0, create_help.stderr
    assert "usage: microcosm work create" in create_help.stdout
    assert "--route" in create_help.stdout
    assert "route id to snapshot" in create_help.stdout

    run_help = _run_microcosm_cli("work", "run", "--help")
    assert run_help.returncode == 0, run_help.stderr
    assert "usage: microcosm work run" in run_help.stdout
    assert "--work-id" in run_help.stdout
    assert "work id to run" in run_help.stdout


def test_cli_proof_lab_card_exits_zero_for_actionable_cache_status() -> None:
    result = _run_microcosm_cli("proof-lab", "--card")
    assert result.returncode == 0, result.stderr

    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "microcosm_proof_lab_first_screen_card_v1"
    assert payload["status"] in {"pass", "stale_cached_receipt"}
    assert payload["safe_to_show"]["proof_correctness_claim"] is False
    if payload["status"] == "stale_cached_receipt":
        assert payload["cache_action"]["status"] == "actionable"
        assert payload["cache_action"]["command"] == (
            "microcosm proof-lab --out /tmp/microcosm-proof-lab"
        )
        assert payload["fresh_receipt_required"] is True
        assert payload["status_scope"] == "route_presence_not_cache_freshness"


def test_cli_proof_lab_card_effective_stale_status_controls_action_fields() -> None:
    payload = cli._proof_lab_first_screen_card(
        {
            "status": "stale_cached_receipt",
            "cache_status": "canonical_receipt_read",
            "proof_lab_component_metrics": {},
            "receipt_paths": [
                "/tmp/microcosm-proof-lab/example_verifier_lab_receipt.json"
            ],
            "proof_lab_route_id": "formal_prover_context_strategy_gate",
            "proof_lab_route_component_count": 9,
            "body_in_receipt": False,
            "authority_ceiling": {"status": "pass"},
            "anti_claim": "bounded proof-lab receipt only",
        },
        input_path=str(cli.DEFAULT_PROOF_LAB_INPUT),
        out_dir="/tmp/microcosm-proof-lab",
        command="microcosm proof-lab --card --out /tmp/microcosm-proof-lab",
    )

    assert payload["status"] == "stale_cached_receipt"
    assert payload["cache_status"] == "canonical_receipt_read"
    assert payload["fresh_receipt_required"] is True
    assert payload["status_scope"] == "route_presence_not_cache_freshness"
    assert payload["cache_action"]["status"] == "actionable"
    assert payload["receipt_ref"] == (
        "/tmp/microcosm-proof-lab/example_verifier_lab_receipt.json"
    )


def test_cli_proof_lab_card_accepts_project_argument_for_first_screen_parity() -> None:
    result = _run_microcosm_cli("proof-lab", "--card", ".")
    assert result.returncode == 0, result.stderr

    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "microcosm_proof_lab_first_screen_card_v1"
    assert payload["command"].startswith("microcosm proof-lab --card")
    assert " ." not in payload["command"]


@pytest.mark.parametrize(
    ("argv", "schema_version", "canonical_command"),
    (
        (
            ("spine", "--card", "."),
            "microcosm_public_runtime_spine_card_v1",
            "microcosm spine --card",
        ),
        (
            ("intake", "--card", "."),
            "microcosm_runtime_reveal_import_bridge_card_v1",
            "microcosm intake --card",
        ),
        (
            ("projection-import-map", "--card", "."),
            "microcosm_public_projection_import_map_lens_v1",
            "microcosm projection-import-map",
        ),
        (
            ("legibility-scorecard", "."),
            "microcosm_public_cold_reader_legibility_scorecard_lens_v1",
            "microcosm legibility-scorecard",
        ),
    ),
)
def test_cli_public_lens_accepts_project_argument_for_first_screen_parity(
    argv: tuple[str, ...],
    schema_version: str,
    canonical_command: str,
) -> None:
    result = _run_microcosm_cli(*argv)
    assert result.returncode == 0, result.stderr

    payload = json.loads(result.stdout)
    assert payload["schema_version"] == schema_version
    assert payload["command"] == canonical_command
    assert " ." not in payload["command"]


def test_cli_circuit_attribution_card_smoke(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(["circuit-attribution", "--card", "."])

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload, sort_keys=True)
    assert status == 0
    assert payload["schema_version"] == (
        "mechanistic_interpretability_circuit_attribution_replay_command_card_v1"
    )
    assert payload["command"] == "microcosm circuit-attribution --card"
    assert payload["source_command"] == "microcosm circuit-attribution"
    assert payload["endpoint"] == "/circuit-attribution"
    assert payload["output_economy"]["full_lens_exported"] is False
    assert payload["body_floor"]["features_in_card"] is False
    assert payload["body_floor"]["attribution_replays_in_card"] is False
    assert "features" not in payload
    assert "attribution_replays" not in payload
    assert len(encoded) < 7000


def test_cli_bridge_phase_continuity_runtime_accepts_card_flag(tmp_path: Path) -> None:
    out_dir = tmp_path / "bridge_receipts"
    result = _run_microcosm_cli(
        "bridge-phase-continuity-runtime",
        "run",
        "--input",
        "fixtures/second_wave/bridge_phase_continuity_runtime/input",
        "--out",
        out_dir.as_posix(),
        "--card",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "bridge_phase_continuity_runtime_command_card_v2"
    assert payload["status"] == "pass"
    assert payload["synthetic_transport_summary"]["transport_label"] == (
        "synthetic_transport"
    )
    assert "fake_transport_summary" not in payload
    assert (out_dir / "continuation_packet.json").is_file()


@pytest.mark.parametrize(
    "argv",
    (
        ("bridge-phase-continuity-runtime", "--help"),
        ("bridge-phase-continuity-runtime", "run", "--help"),
    ),
)
def test_cli_bridge_phase_continuity_runtime_help_matches_documented_shape(
    argv: tuple[str, ...],
) -> None:
    result = _run_microcosm_cli(*argv)

    assert result.returncode == 0, result.stderr
    assert (
        "microcosm bridge-phase-continuity-runtime run --input INPUT --out OUT [--card]"
        in result.stdout
    )
    assert (
        "microcosm bridge-phase-continuity-runtime [-h] --input INPUT --out OUT"
        not in result.stdout
    )


def test_cli_proof_lab_card_exit_code_keeps_missing_cache_nonzero() -> None:
    assert (
        cli._proof_lab_card_exit_code(
            {
                "status": "stale_cached_receipt",
                "cache_action": {"status": "actionable"},
            }
        )
        == 0
    )
    assert (
        cli._proof_lab_card_exit_code(
            {
                "status": "missing_cached_receipt",
                "cache_action": {"status": "missing"},
            }
        )
        == 1
    )


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("macro-projection-import-protocol", "run-projection-bundle"),
        ("verifier-lab-kernel", "run-kernel-bundle"),
        (
            "agentic-vulnerability-discovery-patch-proof-replay",
            "run-patch-proof-bundle",
        ),
        ("mcp-tool-authority-replay", "run-tool-authority-bundle"),
    ],
)
def test_cli_hidden_drilldown_commands_remain_callable(
    command: str,
    expected: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main([command, "--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    assert f"usage: microcosm {command}" in output
    assert expected in output


def test_cli_root_evidence_list_uses_compact_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    receipt_path = public_root / "receipts/runtime_shell/demo/result.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": "demo_receipt_v1",
                "status": "pass",
                "organ_id": "demo_organ",
                "command": "microcosm demo",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "MICROCOSM_ROOT", public_root)

    assert cli.main(["evidence", "list"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"
    assert payload["evidence_list_mode"] == "compact_runtime_evidence_index_v1"
    assert payload["receipt_count"] == 1
    evidence_row = payload["evidence"][0]
    assert "evidence_contract" not in evidence_row
    assert "inspect_command" not in evidence_row
    assert "evidence_contract_ref" not in evidence_row
    assert (
        evidence_row["evidence_contract_summary"]["payload_boundary"]
        == "inspect_drilldown"
    )
    assert payload["full_contract_drilldown"] == {
        "command_template": "microcosm evidence inspect <receipt_ref>",
        "row_key": "receipt_ref",
        "field": "evidence_contract",
    }


def test_runtime_evidence_index_rejects_duplicate_receipt_keys(tmp_path: Path) -> None:
    public_root = tmp_path / "microcosm-substrate"
    receipt_path = public_root / "receipts/runtime_shell/demo/result.json"
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(
        '{"schema_version": "demo_receipt_v1", "status": "blocked", "status": "pass"}',
        encoding="utf-8",
    )

    payload = runtime_evidence_index.list_runtime_evidence(public_root)

    evidence_row = payload["evidence"][0]
    assert evidence_row["status"] == "unknown"
    assert (
        evidence_row["evidence_contract_summary"]["real_runtime_receipt"]
        is False
    )


def test_cli_root_evidence_list_can_be_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    receipt_dir = public_root / "receipts/runtime_shell/demo"
    receipt_dir.mkdir(parents=True)
    for index in range(3):
        (receipt_dir / f"result_{index}.json").write_text(
            json.dumps(
                {
                    "schema_version": "demo_receipt_v1",
                    "status": "pass",
                    "organ_id": f"demo_organ_{index}",
                }
            ),
            encoding="utf-8",
        )
    monkeypatch.setattr(cli, "MICROCOSM_ROOT", public_root)

    assert cli.main(["evidence", "list", "--limit", "2"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["receipt_count"] == 3
    assert payload["returned_receipt_count"] == 2
    assert payload["limit"] == 2
    assert payload["truncated"] is True
    assert len(payload["evidence"]) == 2


def test_runtime_evidence_list_only_summarizes_returned_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    receipt_dir = public_root / "receipts/runtime_shell/demo"
    receipt_dir.mkdir(parents=True)
    for index in range(5):
        (receipt_dir / f"result_{index}.json").write_text(
            json.dumps({"status": "pass", "organ_id": f"demo_organ_{index}"}),
            encoding="utf-8",
        )
    summarized_refs: list[str] = []

    def compact_summary(path: Path, root: Path) -> dict[str, object]:
        summarized_refs.append(path.relative_to(root).as_posix())
        return {
            "receipt_ref": summarized_refs[-1],
            "status": "pass",
        }

    monkeypatch.setattr(
        runtime_evidence_index,
        "compact_receipt_summary",
        compact_summary,
    )

    payload = runtime_evidence_index.list_runtime_evidence(public_root, limit=2)

    assert payload["receipt_count"] == 5
    assert payload["returned_receipt_count"] == 2
    assert payload["truncated"] is True
    assert summarized_refs == [
        "receipts/runtime_shell/demo/result_0.json",
        "receipts/runtime_shell/demo/result_1.json",
    ]


def test_runtime_evidence_limited_path_selection_preserves_count_and_order(
    tmp_path: Path,
) -> None:
    receipt_dir = tmp_path / "receipts"
    rows = [
        receipt_dir / "result_z.json",
        receipt_dir / "result_b.json",
        receipt_dir / "result_a.json",
        receipt_dir / "result_c.json",
    ]

    count, selected = runtime_evidence_index._bounded_sorted_paths(iter(rows), 2)

    assert count == 4
    assert [path.name for path in selected] == [
        "result_a.json",
        "result_b.json",
    ]


def test_cli_first_screen_text_projection_is_package_backed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(
        ["first-screen", "--format", "text", "--reader", "peer_developer", "."]
    )

    text = capsys.readouterr().out
    assert status == 0
    assert text.startswith("Microcosm first screen\n")
    assert "First run: microcosm tour --card ." in text
    assert (
        "observatory: microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 7"
        in text
    )
    assert "A local evidence router; doctrine names boundaries" in text
    assert "Reader branch: Peer developer" in text
    assert "  First action: Run `microcosm tour --card .`." in text
    assert "  Proof: `microcosm observe --card .`" in text
    assert "Authority ceiling:" in text
    assert "reader_routes" not in text
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text


def test_cli_first_screen_accepts_interesting_parts_alias(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(
        ["first-screen", "--format", "text", "--reader", "interesting-parts", "."]
    )

    text = capsys.readouterr().out
    assert status == 0
    assert "Reader branch: GitHub visitor" in text
    assert "Command: microcosm hello --reader interesting-parts ." in text
    assert "Text card: microcosm first-screen --format text --reader interesting-parts ." in text
    assert "Proof: `microcosm tour --card .`" in text


def test_cli_first_screen_json_projection_preserves_shared_first_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    status = cli.main(["first-screen", "."])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_first_screen_compact_card_v1"
    assert payload["status"] == "pass"
    assert payload["shared_first_command"] == "microcosm tour --card ."
    assert payload["compact_projection_of"] == "microcosm_first_screen_composition_card_v1"
    assert payload["drilldowns"]["full_json"] == "microcosm first-screen --full ."
    assert payload["drilldowns"]["observatory"] == (
        "microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 7"
    )
    assert payload["output_policy"]["default_json_is_first_screen_projection"] is True

    status = cli.main(["first-screen", "--full", "."])
    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_first_screen_composition_card_v1"
    assert payload["shared_first_command"] == "microcosm tour --card ."
    assert (
        payload["entry_surface_contract"]["shared_behavior_surface"]
        == payload["shared_first_command"]
    )
    assert payload["observatory_landing_frame"]["serve_command"] == (
        "microcosm serve . --host 127.0.0.1 --port 8765"
    )
    assert payload["observatory_landing_frame"]["bounded_validation_command"] == (
        "microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 7"
    )
    assert any(
        row.get("command") == "microcosm serve . --host 127.0.0.1 --port 8765"
        and row.get("endpoint") == "/"
        for row in payload["drilldowns"]
    )
    assert any(
        row.get("command")
        == "microcosm serve . --host 127.0.0.1 --port 8765 --max-requests 7"
        and row.get("endpoint") == "/"
        for row in payload["drilldowns"]
    )
    assert (
        payload["comparison_frame"]["purpose"]
        == "make_rigor_visible_without_claim_inflation"
    )
    assert payload["state_write_boundary"] == {
        "schema_version": "microcosm_first_screen_state_write_boundary_v1",
        "this_card_writes_microcosm_state": False,
        "this_card_status_scope": "composition_contract_only_not_local_run_result",
        "shared_first_command": "microcosm tour --card .",
        "shared_first_command_writes_state": True,
        "state_dir": ".microcosm",
        "behavioral_proof_command": "microcosm tour --card .",
        "front_door_status_ref": "microcosm tour --card .::front_door_status",
        "reader_action": (
            "Run the shared first command to write .microcosm state and read "
            "front_door_status before treating the first screen as behavior."
        ),
        "safe_to_show": {
            "source_files_mutated": False,
            "provider_calls_authorized": False,
            "release_or_hosting_authorized": False,
            "proof_correctness_claim": False,
        },
    }
    assert {route["reader_route_id"] for route in payload["reader_routes"]} == {
        "public_github_visitor",
        "safety_evals_engineer",
        "hiring_reviewer",
        "peer_developer",
        "domain_specialist",
        "type_a_agent",
    }


def test_cli_status_card_can_overlay_project_route_state(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)
    project_substrate.compile_project(project)

    status_rc = cli.main(["status", "--card", str(project)])
    payload = json.loads(capsys.readouterr().out)
    project_ref = "<project>"

    assert len(json.dumps(payload, sort_keys=True)) < 12000
    assert payload["card_command"] == f"microcosm status --card {project_ref}"
    assert payload["source_files_mutated"] is False
    assert "next_commands" not in payload
    assert payload["front_door"]["front_door_status_ref"] == (
        f"microcosm status --card {project_ref}::front_door_status"
    )
    front_door_status = payload["front_door_status"]
    body_floor_blocked = (
        front_door_status["surface_statuses"].get("macro_body_import_floor")
        != "pass"
    )
    assert status_rc == (1 if body_floor_blocked else 0)
    assert front_door_status["status"] == (
        "blocked" if body_floor_blocked else "pass"
    )
    if body_floor_blocked:
        assert "macro_body_import_floor" in front_door_status[
            "blocking_surface_ids"
        ]
        _assert_body_floor_blocking_details(
            front_door_status["blocking_surface_details"]["macro_body_import_floor"]
        )
    else:
        assert front_door_status["blocking_surface_ids"] == []
    assert front_door_status["surface_statuses"]["project_state"] == "pass"
    assert front_door_status["surface_statuses"]["route_selection_proof"] == "pass"
    assert front_door_status["surface_statuses"]["route_explanation"] == "pass"
    assert front_door_status["surface_statuses"]["state_write_proof"] == "pass"
    assert front_door_status["surface_statuses"]["proof_lab"] == "pass"
    proof_lab_cache_status = payload["front_door"]["proof_lab"]["cache_status"]
    assert set(front_door_status["actionable_surface_ids"]) == (
        _expected_actionable_surface_ids(front_door_status)
    )
    assert front_door_status["surface_statuses"]["proof_lab_cache"] == (
        "actionable"
        if proof_lab_cache_status == "stale_cached_receipt"
        else "pass"
    )
    assert front_door_status["surface_statuses"]["observatory"] == "actionable"
    assert "required_surface_ids" not in front_door_status
    assert front_door_status["surface_statuses"][
        "workingness_failure_envelope"
    ] in {"clear", "actionable"}
    assert (
        front_door_status["drilldown_blocked_surface_ids_ref"]
        == f"microcosm tour {project_ref}::front_door_status."
        "drilldown_blocked_surface_ids"
    )
    assert payload["front_door"]["project_state_status"] == "pass"
    assert payload["front_door"]["selected_route_id"] == "readme_onboarding_route"
    route_selection_proof = payload["front_door"]["route_selection_proof"]
    assert route_selection_proof["status"] == "pass"
    assert (
        route_selection_proof["schema_version"]
        == "microcosm_project_route_selection_proof_v1"
    )
    assert route_selection_proof["selected_route_id"] == "readme_onboarding_route"
    assert route_selection_proof["route_id_available_in_state"] is True
    assert route_selection_proof["route_explanation_status"] == "pass"
    assert route_selection_proof["observatory_route_proof_ref"] == (
        f"microcosm serve {project_ref}::first_screen_route_proof"
    )
    assert payload["front_door"]["route_explanation_command"] == (
        f"microcosm explain {project_ref} readme_onboarding_route"
    )
    route_explanation = payload["front_door"]["route_explanation"]
    assert route_explanation["status"] == "pass"
    assert route_explanation["route_id"] == "readme_onboarding_route"
    assert route_explanation["selected_work_status"] == "closed"
    assert route_explanation["source_files_mutated"] is False
    assert route_explanation["event_ref_count"] >= 1
    assert route_explanation["evidence_ref_count"] >= 1
    assert route_explanation["reader_drilldown_count"] == 4
    assert route_explanation["drilldown_ref"] == (
        f"microcosm explain {project_ref} readme_onboarding_route"
    )
    assert "reader_drilldowns" not in route_explanation
    assert "readme_onboarding_route" in payload["front_door"][
        "available_project_route_ids"
    ]
    assert payload["front_door"]["project_state"]["state_dir_exists"] is True
    assert payload["front_door"]["project_state"]["state_write_result_ref"] == (
        f"microcosm tour --card {project_ref}::state_write_result"
    )
    assert payload["front_door"]["project_state"]["state_write_status_ref"] == (
        f"microcosm tour --card {project_ref}::front_door_status."
        "surface_statuses.state_write"
    )
    assert (
        payload["front_door"]["project_state"]["status_card_writes_microcosm_state"]
        is False
    )
    state_write_proof = payload["front_door"]["state_write_proof"]
    assert state_write_proof["status"] == "pass"
    assert state_write_proof["state_write_result_ref"] == (
        f"microcosm tour --card {project_ref}::state_write_result"
    )
    assert state_write_proof["state_write_status_ref"] == (
        f"microcosm tour --card {project_ref}::front_door_status."
        "surface_statuses.state_write"
    )
    assert state_write_proof["project_state_ref"] == "front_door.project_state"
    assert state_write_proof["observe_ref"] == (
        f"microcosm observe {project_ref}::state_write_proof"
    )
    assert state_write_proof["observe_writes_microcosm_state"] is False
    assert state_write_proof["status_card_writes_microcosm_state"] is False
    assert state_write_proof["safe_to_show"]["source_files_mutated"] is False
    assert payload["front_door"]["project_state"][
        "available_project_route_id_count"
    ] >= len(payload["front_door"]["project_state"]["available_project_route_ids"])
    proof_lab = payload["front_door"]["proof_lab"]
    assert proof_lab["status"] == "pass"
    assert proof_lab["endpoint"] == "/proof-lab"
    assert proof_lab["route_id"] == "formal_prover_context_strategy_gate"
    assert proof_lab["route_component_count"] == 9
    assert proof_lab["proof_bodies_exported"] is False
    assert proof_lab["proof_correctness_claim"] is False
    observatory = payload["front_door"]["observatory"]
    assert observatory["status"] == "actionable"
    assert observatory["validation_status"] == "not_evaluated_in_status_card"
    assert observatory["command"] == (
        f"microcosm serve {project_ref} --host 127.0.0.1 "
        "--port 8765 --max-requests 7"
    )
    assert observatory["interactive_command"] == (
        f"microcosm serve {project_ref} --host 127.0.0.1 --port 8765"
    )
    assert observatory["endpoint"] == "/project/observatory"
    assert observatory["compact_endpoint"] == "/project/observatory-card"
    assert observatory["project_observe_endpoint"] == "/project/observe"
    assert observatory["route_explanation_endpoint"] == (
        "/project/explain/readme_onboarding_route"
    )
    assert observatory["first_screen_route_proof_ref"] == (
        f"microcosm serve {project_ref}::first_screen_route_proof"
    )
    assert observatory["project_observe_command"] == (
        f"microcosm observe --card {project_ref}"
    )
    assert observatory["status_card_ref"] == (
        f"microcosm status --card {project_ref}"
    )
    assert observatory["source_files_mutated"] is False
    assert observatory["provider_calls_authorized"] is False
    assert observatory["model_field_count"] == 13
    body_floor = payload["front_door"]["source_open_body_import_floor"]
    assert body_floor["status"] == front_door_status["surface_statuses"][
        "macro_body_import_floor"
    ]
    assert body_floor["summary_ref"] == (
        "microcosm status --card::macro_body_import_floor"
    )
    assert (
        body_floor["public_safe_body_material_count"]
        == payload["substrate_counts"][
            "copied_non_secret_macro_body_material_count"
        ]
    )
    assert body_floor["verified_source_module_family_count"] >= 20
    assert body_floor["latest_verified_source_module_family_ids"]
    assert all(
        isinstance(family_id, str)
        for family_id in body_floor["latest_verified_source_module_family_ids"]
    )
    assert body_floor["body_text_exported_in_status"] is False
    assert body_floor["body_text_exported_in_receipts"] is False
    assert payload["workingness"]["source_body_count_kind"] == "per_organ_row_sum"


def test_cli_status_card_alias_matches_status_card(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)
    project_substrate.compile_project(project)

    alias_rc = cli.main(["status-card", str(project)])
    alias_payload = json.loads(capsys.readouterr().out)
    canonical_rc = cli.main(["status", "--card", str(project)])
    canonical_payload = json.loads(capsys.readouterr().out)

    assert alias_rc == canonical_rc
    assert alias_payload == canonical_payload
    assert alias_payload["card_command"] == "microcosm status --card <project>"


def test_cli_status_card_preserves_relative_project_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)
    project_substrate.compile_project(project)
    monkeypatch.chdir(tmp_path)

    status_rc = cli.main(["status-card", "scratch"])
    payload = json.loads(capsys.readouterr().out)

    assert status_rc == (1 if payload["status"] == "blocked" else 0)
    assert payload["project_ref"] == "scratch"
    assert payload["card_command"] == "microcosm status --card scratch"
    assert payload["front_door"]["project_ref"] == "scratch"
    assert payload["front_door"]["primary_command"] == "microcosm tour --card scratch"
    assert payload["front_door"]["project_state"]["state_write_result_ref"] == (
        "microcosm tour --card scratch::state_write_result"
    )
    assert payload["front_door"]["observatory"]["status_card_ref"] == (
        "microcosm status --card scratch"
    )


def test_cli_full_status_preserves_project_route_overlay(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)
    project_substrate.compile_project(project)

    assert cli.main(["status", str(project)]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["project_ref"] == "<project>"
    assert payload["front_door"]["project_ref"] == "<project>"
    assert payload["front_door"]["project_state_status"] == "pass"
    assert payload["front_door"]["selected_route_id"] == "readme_onboarding_route"
    assert payload["front_door"]["route_explanation_command"] == (
        "microcosm explain <project> readme_onboarding_route"
    )
    assert payload["front_door"]["route_selection_proof"]["status"] == "pass"
    assert payload["front_door"]["observatory"]["status"] == "actionable"
    assert (
        payload["front_door"]["observatory"]["validation_status"]
        == "not_evaluated_in_status_card"
    )
    assert (
        payload["front_door"]["available_project_route_id_count"]
        >= len(payload["front_door"]["available_project_route_ids"])
    )
    assert "readme_onboarding_route" in payload["front_door"][
        "available_project_route_ids"
    ]
    assert payload["front_door_status"]["surface_statuses"]["project_state"] == (
        "pass"
    )
    assert payload["front_door_status"]["surface_statuses"]["observatory"] == (
        "actionable"
    )
    assert "observatory" in payload["front_door_status"]["actionable_surface_ids"]
    assert payload["status_card"]["front_door"]["selected_route_id"] == (
        "readme_onboarding_route"
    )
    assert payload["status_card"]["front_door"]["observatory"]["status"] == (
        "actionable"
    )
    assert payload["status_card"]["front_door"]["project_state_status"] == "pass"
    assert payload["project_front_door_status"]["selected_route_id"] == (
        "readme_onboarding_route"
    )
    minimal_steps = {
        row["step_id"]: row for row in payload["front_door"]["minimal_command_path"]
    }
    assert minimal_steps["inspect_project_observe"]["selected_route_id"] == (
        "readme_onboarding_route"
    )
    assert minimal_steps["inspect_route_causal_chain"]["selected_route_id"] == (
        "readme_onboarding_route"
    )
    assert minimal_steps["inspect_route_causal_chain"]["command"] == (
        "microcosm explain <project> readme_onboarding_route"
    )
    assert minimal_steps["drill_receipts_only_after_behavior"][
        "evidence_ref_count"
    ] >= 1


def test_cli_status_card_before_tour_exposes_project_recovery(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)

    assert cli.main(["status", "--card", str(project)]) == 0
    payload = json.loads(capsys.readouterr().out)
    project_ref = "<project>"

    assert payload["status"] == "blocked"
    assert payload["card_command"] == f"microcosm status --card {project_ref}"
    assert payload["source_files_mutated"] is False
    assert payload["next_commands"] == [
        f"microcosm tour --card {project_ref}",
        f"microcosm status --card {project_ref}",
        f"microcosm compile {project_ref}",
    ]
    front_door = payload["front_door"]
    project_state = front_door["project_state"]
    recovery = project_state["recovery"]
    assert project_state["status"] == "missing_state"
    assert project_state["state_dir_exists"] is False
    assert project_state["existing_state_ref_count"] == 0
    assert project_state["route_count"] == 0
    assert project_state["recovery_command"] == (
        f"microcosm tour --card {project_ref}"
    )
    assert project_state["status_after_recovery_command"] == (
        f"microcosm status --card {project_ref}"
    )
    assert recovery["status"] == "actionable"
    assert recovery["blocked_surface_id"] == "project_state"
    assert recovery["primary_command"] == f"microcosm tour --card {project_ref}"
    assert recovery["alternate_command"] == f"microcosm compile {project_ref}"
    assert recovery["provider_calls_authorized"] is False
    assert recovery["source_files_mutated"] is False
    assert front_door["project_recovery"] == recovery
    assert front_door["observatory"]["status"] == "actionable"

    front_door_status = payload["front_door_status"]
    assert front_door_status["status"] == "blocked"
    assert front_door_status["surface_statuses"]["project_state"] == "missing_state"
    assert "project_state" in front_door_status["blocking_surface_ids"]
    assert front_door_status["blocking_surface_details"]["project_state"][
        "primary_recovery_command"
    ] == f"microcosm tour --card {project_ref}"
    assert front_door_status["blocking_surface_details"]["project_state"][
        "status_after_recovery_command"
    ] == f"microcosm status --card {project_ref}"


def test_cli_tour_card_relative_external_project_writes_caller_project_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)
    monkeypatch.chdir(project)

    tour_rc = cli.main(["tour", "--card", "."])
    tour_card = json.loads(capsys.readouterr().out)
    status_rc = cli.main(["status", "--card", "."])
    status_card = json.loads(capsys.readouterr().out)

    body_floor_blocked = (
        status_card["front_door_status"]["surface_statuses"].get(
            "macro_body_import_floor"
        )
        != "pass"
    )
    assert tour_rc == (1 if body_floor_blocked else 0)
    assert status_rc == (1 if body_floor_blocked else 0)
    assert (project / ".microcosm/routes.json").is_file()
    assert tour_card["compile_summary"]["selected_route_id"] == (
        status_card["front_door"]["selected_route_id"]
    )
    assert status_card["front_door"]["project_state"]["state_dir_exists"] is True
    assert status_card["front_door_status"]["surface_statuses"]["project_state"] == (
        "pass"
    )
    assert status_card["front_door_status"]["surface_statuses"][
        "state_write_proof"
    ] == "pass"


def test_cli_tour_on_fresh_project_exposes_first_screen_microcosm(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_tour = MICROCOSM_ROOT / "receipts/runtime_shell/public_ten_minute_tour.json"
    source_tour_before = source_tour.read_text(encoding="utf-8")
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)
    project = _make_scratch_project(tmp_path)

    tour_rc = cli.main(["tour", str(project)])
    payload = json.loads(capsys.readouterr().out)
    first_screen = payload["first_screen"]
    front_door_status = payload["front_door_status"]
    body_floor_blocked = (
        payload["surface_statuses"].get("macro_body_import_floor") != "pass"
    )

    assert tour_rc == (1 if body_floor_blocked else 0)
    assert payload["status"] == ("blocked" if body_floor_blocked else "pass")
    assert first_screen["schema_version"] == "microcosm_cold_reader_first_screen_v1"
    assert first_screen["intent"] == "bring_folder_run_local_path_inspect_state_then_drill_receipts"
    assert first_screen["selected_route_id"] == "readme_onboarding_route"
    assert first_screen["generated_state"]["state_dir"] == ".microcosm"
    expected_state_refs = {
        ".microcosm/project_manifest.json",
        ".microcosm/architecture.json",
        ".microcosm/state_index.json",
        ".microcosm/graph.json",
        ".microcosm/catalog.json",
        ".microcosm/python_lens.json",
        ".microcosm/patterns.json",
        ".microcosm/routes.json",
        ".microcosm/work_items.json",
        ".microcosm/events.jsonl",
        ".microcosm/explanations/",
        ".microcosm/evidence/",
    }
    assert set(first_screen["generated_state"]["refs"]) == expected_state_refs
    for ref in expected_state_refs:
        assert (project / ref).exists()
    assert first_screen["behavior_surfaces"] == {
        "route_state_ref": ".microcosm/routes.json",
        "work_state_ref": ".microcosm/work_items.json",
        "event_log_ref": ".microcosm/events.jsonl",
        "evidence_dir_ref": ".microcosm/evidence/",
        "graph_ref": ".microcosm/graph.json",
        "project_observe_command": "microcosm observe --card <project>",
        "project_observe_full_command": "microcosm observe <project>",
        "project_observe_endpoint": "/project/observe",
        "observatory_command": (
            "microcosm serve <project> --host 127.0.0.1 --port 8765 "
            "--max-requests 7"
        ),
        "observatory_bounded_validation_command": (
            "microcosm serve <project> --host 127.0.0.1 --port 8765 "
            "--max-requests 7"
        ),
        "observatory_interactive_command": (
            "microcosm serve <project> --host 127.0.0.1 --port 8765"
        ),
    }
    assert first_screen["route_explanation"]["command"] == (
        "microcosm explain <project> readme_onboarding_route"
    )
    assert first_screen["route_explanation"]["endpoint"] == (
        "/project/explain/readme_onboarding_route"
    )
    assert first_screen["proof_surface"]["status"] == "pass"
    assert first_screen["proof_surface"]["route_id"] == "formal_prover_context_strategy_gate"
    assert first_screen["safe_to_show"]["project_local_state_refs_visible"] is True
    assert first_screen["safe_to_show"]["credential_equivalent_payloads_exported"] is False
    assert first_screen["safe_to_show"]["receipt_refs_visible_after_behavior"] is True
    assert front_door_status["status"] == (
        "blocked" if body_floor_blocked else "pass"
    )
    if body_floor_blocked:
        assert "macro_body_import_floor" in front_door_status["blocking_surface_ids"]
        _assert_body_floor_blocking_details(
            front_door_status["blocking_surface_details"]["macro_body_import_floor"]
        )
    else:
        assert front_door_status["blocking_surface_ids"] == []
    assert front_door_status["drilldown_warning_surface_ids"] == [
        "authority",
        "intake",
    ]
    assert front_door_status["safe_to_show"]["blocking_surface_ids_visible"] is True
    step_ids = [row["step_id"] for row in first_screen["minimal_command_path"]]
    assert step_ids.index("inspect_first_screen") < step_ids.index(
        "drill_receipts_only_after_behavior"
    )
    assert step_ids.index("inspect_status_card") < step_ids.index(
        "inspect_workingness"
    )
    assert step_ids.index("inspect_workingness") < step_ids.index(
        "compile_project"
    )
    assert step_ids.index("run_first_screen_proof_lab") < step_ids.index(
        "inspect_project_observe"
    )
    assert step_ids.index("inspect_project_observe") < step_ids.index(
        "open_observatory"
    )
    observe_step = {
        row["step_id"]: row for row in first_screen["minimal_command_path"]
    }["inspect_project_observe"]
    assert observe_step["command"] == "microcosm observe --card <project>"
    assert observe_step["full_drilldown"] == "microcosm observe <project>"
    assert observe_step["endpoint"] == "/project/observe"
    assert step_ids.index("run_first_screen_proof_lab") < step_ids.index(
        "inspect_python_routes"
    )
    observatory_step = {
        row["step_id"]: row for row in first_screen["minimal_command_path"]
    }["open_observatory"]
    assert observatory_step["command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 "
        "--max-requests 7"
    )
    assert observatory_step["interactive_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert observatory_step["endpoint"] == "/project/observatory-card"
    assert observatory_step["expanded_endpoint"] == "/project/observatory"

    status_rc = cli.main(["status", "--card", str(project)])
    status_card = json.loads(capsys.readouterr().out)
    assert len(json.dumps(status_card, sort_keys=True)) < 13000
    status_body_floor_blocked = (
        status_card["front_door_status"]["surface_statuses"].get(
            "macro_body_import_floor"
        )
        != "pass"
    )
    assert status_body_floor_blocked is body_floor_blocked
    assert status_rc == (1 if status_body_floor_blocked else 0)
    assert status_card["status"] == (
        "blocked" if status_body_floor_blocked else "pass"
    )
    if status_body_floor_blocked:
        assert "macro_body_import_floor" in status_card["front_door_status"][
            "blocking_surface_ids"
        ]
        body_floor_detail = status_card["front_door_status"][
            "blocking_surface_details"
        ]["macro_body_import_floor"]
        _assert_body_floor_blocking_details(body_floor_detail)
        assert body_floor_detail["defect_preview_compacted"] is True
        assert body_floor_detail["defect_preview_count"] >= len(
            body_floor_detail["defect_preview"]
        )
        assert len(body_floor_detail["defect_preview"]) == 1
    else:
        assert status_card["front_door_status"]["blocking_surface_ids"] == []
        assert (
            status_card["front_door_status"]["surface_statuses"][
                "workingness_failure_envelope"
            ]
            == "clear"
        )
    assert (
        status_card["front_door_status"]["surface_statuses"]["project_state"]
        == "pass"
    )
    assert status_card["front_door"]["project_state_status"] == "pass"
    assert status_card["front_door"]["selected_route_id"] == "readme_onboarding_route"
    assert status_card["front_door"]["route_selection_proof"]["status"] == "pass"
    assert (
        status_card["front_door_status"]["surface_statuses"][
            "route_selection_proof"
        ]
        == "pass"
    )
    assert status_card["front_door_status"]["surface_statuses"]["proof_lab"] == "pass"
    assert status_card["front_door"]["proof_lab"]["cache_status"] in {
        "cached_receipt_read",
        "stale_cached_receipt",
    }
    proof_lab_cache_status = status_card["front_door"]["proof_lab"]["cache_status"]
    assert set(
        status_card["front_door_status"]["actionable_surface_ids"]
    ) == _expected_actionable_surface_ids(status_card["front_door_status"])
    if proof_lab_cache_status == "stale_cached_receipt":
        assert status_card["front_door_status"]["surface_statuses"][
            "proof_lab_cache"
        ] == "actionable"
        assert "proof_lab_cache" in status_card["front_door_status"][
            "actionable_surface_ids"
        ]
    assert (
        status_card["front_door_status"]["surface_statuses"]["observatory"]
        == "actionable"
    )
    assert status_card["front_door"]["state_dir_exists"] is True
    assert status_card["front_door"]["route_explanation"]["status"] == "pass"
    assert status_card["front_door"]["route_explanation"][
        "selected_work_status"
    ] == "closed"
    assert status_card["front_door"]["route_explanation"][
        "source_files_mutated"
    ] is False
    assert status_card["workingness"]["status"] == status_card[
        "front_door_status"
    ]["surface_statuses"]["workingness_failure_envelope"]
    assert status_card["workingness"]["failure_envelope_status"] == status_card[
        "front_door_status"
    ]["surface_statuses"]["workingness_failure_envelope"]
    assert status_card["proof_lab"]["status"] == "pass"
    assert status_card["front_door"]["proof_lab"]["status"] == "pass"
    assert (
        status_card["front_door"]["proof_lab"]["receipt_ref"]
        == PROOF_LAB_RECEIPT_REF
    )
    assert status_card["front_door"]["observatory"]["endpoint"] == (
        "/project/observatory"
    )
    assert status_card["front_door"]["observatory"]["compact_endpoint"] == (
        "/project/observatory-card"
    )
    assert status_card["front_door"]["observatory"][
        "bounded_validation_command"
    ] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 "
        "--max-requests 7"
    )
    assert status_card["front_door"]["observatory"]["command"] == (
        status_card["front_door"]["observatory"]["bounded_validation_command"]
    )
    assert status_card["front_door"]["observatory"]["interactive_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert status_card["front_door"]["observatory"][
        "bounded_validation_request_count"
    ] == 7
    assert status_card["front_door"]["observatory"]["project_observe_command"] == (
        "microcosm observe --card <project>"
    )
    assert status_card["front_door"]["observatory"]["status"] == "actionable"
    assert (
        status_card["front_door"]["observatory"]["validation_status"]
        == "not_evaluated_in_status_card"
    )
    assert status_card["macro_body_import_floor"]["schema_version"] == (
        "microcosm_project_status_body_import_floor_ref_v1"
    )
    assert status_card["macro_body_import_floor"]["project_mode_compacted"] is True
    assert status_card["macro_body_import_floor"]["ref"] == (
        "front_door.source_open_body_import_floor"
    )
    assert (
        status_card["macro_body_import_floor"]["verified_source_module_family_count"]
        == status_card["front_door"]["source_open_body_imports"][
            "verified_source_module_family_count"
        ]
    )
    body_floor = status_card["front_door"]["source_open_body_import_floor"]
    assert body_floor["direct_source_module_manifest_count"] >= 30
    assert body_floor["direct_source_module_manifest_material_count"] >= 170
    route_observability_spotlight = next(
        spotlight
        for spotlight in body_floor["source_module_family_spotlights"]
        if spotlight["spotlight_id"] == "agent_route_observability_runtime"
    )
    assert route_observability_spotlight["family_count"] >= 9
    assert route_observability_spotlight["notable_family_ids"]
    assert all(
        isinstance(family_id, str)
        for family_id in route_observability_spotlight["notable_family_ids"]
    )
    assert status_card["payload_boundary_audit"]["status"] == "pass"
    assert source_tour.read_text(encoding="utf-8") == source_tour_before


def test_cli_status_card_matches_observatory_card_reader_lens(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)

    assert cli.main(["tour", str(project)]) in {0, 1}
    capsys.readouterr()
    status_rc = cli.main(["status", "--card", str(project)])
    status_card = json.loads(capsys.readouterr().out)
    observatory = RuntimeShell(MICROCOSM_ROOT).project_observatory(
        project,
        persist_receipts=False,
    )
    observatory_card = observatory["observatory_card"]

    status_front_door = status_card["front_door"]
    status_front_door_status = status_card["front_door_status"]
    status_body_floor = status_front_door["source_open_body_import_floor"]
    observatory_body_floor = observatory_card["source_open_body_import_floor"]
    body_floor_blocked = (
        status_front_door_status["surface_statuses"].get("macro_body_import_floor")
        != "pass"
    )

    assert status_rc == (1 if body_floor_blocked else 0)
    assert status_front_door_status["status"] == (
        "blocked" if body_floor_blocked else "pass"
    )
    assert status_front_door["observatory"]["status"] == "actionable"
    assert (
        status_front_door["observatory"]["validation_status"]
        == "not_evaluated_in_status_card"
    )
    assert status_front_door_status["surface_statuses"]["observatory"] == (
        "actionable"
    )
    assert "observatory" in status_front_door_status["actionable_surface_ids"]
    assert observatory_card["status"] in {"pass", "blocked"}
    assert observatory["front_door_status"]["status"] in {"pass", "blocked"}
    if body_floor_blocked:
        assert "macro_body_import_floor" in status_front_door_status[
            "blocking_surface_ids"
        ]
        _assert_body_floor_blocking_details(
            status_front_door_status["blocking_surface_details"][
                "macro_body_import_floor"
            ]
        )
        assert "macro_body_import_floor" in observatory_card[
            "first_screen_route_proof"
        ]["blocking_surface_ids"]
    else:
        assert status_front_door_status["blocking_surface_ids"] == []
        if observatory_card["status"] == "pass":
            assert (
                observatory_card["first_screen_route_proof"][
                    "blocking_surface_ids"
                ]
                == []
            )
        else:
            assert observatory_card["first_screen_route_proof"][
                "blocking_surface_ids"
            ]
    assert observatory_card["surface_statuses"]["state_inspection"] == "pass"
    assert observatory_card["state_inspection"]["status"] == "pass"
    assert observatory_card["state_inspection"]["missing_first_screen_refs"] == []
    assert ".microcosm/routes.json" in (
        observatory_card["state_inspection"]["first_screen_refs"]
    )
    assert status_front_door["proof_lab"]["status"] == "pass"
    assert observatory_card["proof_lab"]["status"] == "pass"
    assert status_front_door["proof_lab"]["route_id"] == (
        observatory_card["proof_lab"]["route_id"]
    )
    assert status_front_door["observatory"]["status"] == "actionable"
    assert status_front_door["observatory"]["compact_endpoint"] == (
        observatory_card["endpoint"]
    )
    assert status_front_door["observatory"]["bounded_validation_command"] == (
        observatory_card["bounded_validation_command"]
    )
    assert status_front_door["observatory"]["interactive_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert status_front_door["observatory"]["bounded_validation_request_count"] == (
        observatory_card["bounded_validation_request_count"]
    )
    assert status_front_door["observatory"]["project_observe_endpoint"] == (
        observatory_card["json_drilldowns"]["project_observe"]
    )
    assert status_front_door["observatory"]["project_observe_command"] == (
        "microcosm observe --card <project>"
    )
    assert observatory["observatory_card"] == observatory_card
    assert status_card["payload_boundary_audit"]["status"] == "pass"
    assert observatory_card["safe_to_show"]["provider_calls_authorized"] is False
    assert observatory_card["safe_to_show"]["source_files_mutated"] is False
    assert observatory_card["safe_to_show"]["proof_correctness_claim"] is False
    assert (
        status_body_floor["public_safe_body_material_count"]
        == observatory_body_floor["public_safe_body_material_count"]
    )
    assert (
        status_body_floor["public_safe_body_material_counts_by_class"]
        == observatory_body_floor["public_safe_body_material_counts_by_class"]
    )
    assert status_body_floor["latest_verified_source_module_family_ids"] == (
        observatory_body_floor["latest_verified_source_module_family_ids"]
    )
    assert status_body_floor["source_module_family_spotlights"] == (
        observatory_body_floor["source_module_family_spotlights"]
    )
    assert status_body_floor["body_text_exported_in_status"] is False
    assert observatory_body_floor["body_text_exported_in_status"] is False
    assert observatory_body_floor["body_text_exported_in_receipts"] is False


def test_cli_observe_card_is_compact_peer_developer_handoff(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)
    assert cli.main(["tour", "--card", str(project)]) in {0, 1}
    capsys.readouterr()

    assert cli.main(["observe", "--card", str(project)]) == 0
    card = json.loads(capsys.readouterr().out)

    assert card["schema_version"] == "microcosm_project_observe_card_v1"
    assert card["status"] == "pass"
    assert card["card_status"] == "pass"
    assert card["command"] == f"microcosm observe --card {project}"
    assert card["full_command"] == f"microcosm observe {project}"
    assert card["endpoint"] is None
    assert card["endpoint_available"] is False
    assert card["full_endpoint"] == "/project/observe"
    assert card["selected_route_id"] == "readme_onboarding_route"
    assert card["event_count"] >= 1
    assert "events" not in card
    assert card["state_write_proof"]["status"] == "pass"
    assert card["state_write_proof"]["observe_writes_microcosm_state"] is False
    assert card["state_write_proof"]["source_files_mutated"] is False
    assert card["causal_chain_summary"]["status"] == "pass"
    assert card["causal_chain_summary"]["graph"]["node_count"] > 0
    assert card["safe_to_show"]["provider_calls_authorized"] is False
    assert card["safe_to_show"]["source_files_mutated"] is False


def test_cli_serve_process_exposes_first_screen_project_routes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    project = _make_scratch_project(tmp_path)
    assert cli.main(["tour", "--card", str(project)]) in {0, 1}
    capsys.readouterr()

    port = _free_loopback_port()
    env = os.environ.copy()
    src_ref = str(MICROCOSM_ROOT / "src")
    env["PYTHONPATH"] = (
        src_ref
        if not env.get("PYTHONPATH")
        else f"{src_ref}{os.pathsep}{env['PYTHONPATH']}"
    )
    command = [
        sys.executable,
        "-m",
        "microcosm_core.cli",
        "serve",
        str(project),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--max-requests",
        "7",
    ]
    process = subprocess.Popen(
        command,
        cwd=MICROCOSM_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    status_card: dict | None = None
    try:
        deadline = time.monotonic() + 45
        last_error: BaseException | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate(timeout=1)
                pytest.fail(
                    "microcosm serve exited before first-screen endpoints were readable: "
                    f"rc={process.returncode}\nstdout={stdout[-1000:]}\nstderr={stderr[-1000:]}"
                )
            try:
                status_card = _read_local_json(port, "/project/status")
                break
            except (
                ConnectionError,
                OSError,
                TimeoutError,
                URLError,
                json.JSONDecodeError,
            ) as exc:
                last_error = exc
                time.sleep(0.2)

        if status_card is None:
            pytest.fail(
                f"microcosm serve did not expose /project/status: {last_error!r}"
            )

        selected_route_id = status_card["front_door"]["selected_route_id"]
        observatory_card = _read_local_json(port, "/project/observatory-card")
        first_screen = _read_local_json(port, "/project/first-screen")
        project_observe = _read_local_json(port, "/project/observe")
        proof_lab = _read_local_json(port, "/proof-lab")
        explanation = _read_local_json(port, f"/project/explain/{selected_route_id}")
        status = _read_local_json(port, "/status")

        assert status_card["schema_version"] == "microcosm_runtime_status_card_v1"
        assert status_card["front_door"]["project_state_status"] == "pass"
        assert status_card["front_door"]["route_selection_proof"]["status"] == "pass"
        assert status_card["front_door"]["route_explanation"]["status"] == "pass"
        assert status_card["source_files_mutated"] is False
        assert (
            status_card["front_door"]["observatory"]["compact_endpoint"]
            == "/project/observatory-card"
        )
        assert (
            status_card["front_door"]["observatory"]["project_observe_endpoint"]
            == "/project/observe"
        )

        assert (
            observatory_card["schema_version"]
            == "microcosm_project_observatory_card_v1"
        )
        assert observatory_card["selected_route_id"] == selected_route_id
        assert observatory_card["surface_statuses"]["route"] == "pass"
        assert observatory_card["surface_statuses"]["work"] == "pass"
        assert observatory_card["surface_statuses"]["evidence"] == "pass"
        assert observatory_card["surface_statuses"]["graph"] == "pass"
        assert observatory_card["state_inspection"]["status"] == "pass"
        assert observatory_card["state_inspection"]["missing_first_screen_refs"] == []
        assert observatory_card["safe_to_show"]["provider_calls_authorized"] is False
        assert observatory_card["safe_to_show"]["source_files_mutated"] is False
        assert observatory_card["safe_to_show"]["proof_correctness_claim"] is False
        assert first_screen["schema_version"] == "microcosm_first_screen_compact_card_v1"
        assert first_screen["status"] == "pass"
        causal_summary = observatory_card["causal_chain_summary"]
        assert causal_summary["route"]["title"] == "Inspect README onboarding"
        assert causal_summary["route"]["grounded_ref_count"] >= 1
        assert causal_summary["route"]["pattern_ref_count"] >= 1
        assert causal_summary["event_rows_shown"] >= 4
        assert causal_summary["evidence_rows_shown"] >= 4
        assert causal_summary["graph"]["node_count"] > 0
        assert causal_summary["graph"]["edge_count"] > 0
        assert causal_summary["graph"]["graph_ref"] == ".microcosm/graph.json"

        assert (
            project_observe["schema_version"]
            == "microcosm_project_observe_result_v1"
        )
        assert project_observe["status"] == "pass"
        assert project_observe["selected_route_id"] == selected_route_id
        state_write_proof = project_observe["state_write_proof"]
        assert state_write_proof["status"] == "pass"
        assert state_write_proof["state_write_result_ref"] == (
            f"microcosm tour --card {project}::state_write_result"
        )
        assert state_write_proof["state_write_status_ref"] == (
            f"microcosm tour --card {project}::front_door_status."
            "surface_statuses.state_write"
        )
        assert state_write_proof["state_inspection_status_ref"] == (
            f"microcosm tour --card {project}::front_door_status."
            "surface_statuses.state_inspection"
        )
        assert state_write_proof["observe_writes_microcosm_state"] is False
        assert state_write_proof["status_card_writes_microcosm_state"] is False
        assert state_write_proof["safe_to_show"]["source_files_mutated"] is False
        assert project_observe["causal_chain"]["status"] == "pass"
        assert project_observe["safe_to_show"]["provider_calls_authorized"] is False
        assert project_observe["safe_to_show"]["source_files_mutated"] is False

        assert (
            proof_lab["schema_version"]
            == "microcosm_first_screen_proof_lab_route_card_v1"
        )
        assert proof_lab["endpoint"] == "/proof-lab"
        assert proof_lab["safe_to_show"]["provider_payloads_omitted"] is True
        assert proof_lab["safe_to_show"]["credential_equivalent_payloads_omitted"] is True

        assert explanation["schema_version"] == "microcosm_route_explanation_v1"
        assert explanation["status"] == "pass"
        assert explanation["route_id"] == selected_route_id
        assert explanation["causal_chain_proof"]["source_files_mutated"] is False

        assert status["project_front_door_status"]["status"] == "pass"
        assert (
            status["project_front_door_status"]["selected_route_id"]
            == selected_route_id
        )
        assert status["project_front_door_status"]["source_files_mutated"] is False
        returncode = process.wait(timeout=10)
        stdout, stderr = process.communicate(timeout=1)
        assert returncode == 0
        assert f"http://127.0.0.1:{port}" in stdout
        assert "max_requests=7" in stdout
        assert stderr == ""
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()


def test_cli_serve_reports_busy_port_without_traceback(tmp_path: Path) -> None:
    project = _make_scratch_project(tmp_path)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = int(sock.getsockname()[1])
        result = _run_microcosm_cli(
            "serve",
            str(project),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--max-requests",
            "1",
        )
        default_result = _run_microcosm_cli(
            "serve",
            str(project),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        )

    assert result.returncode == 2
    assert result.stdout == ""
    assert f"microcosm serve could not bind http://127.0.0.1:{port}" in result.stderr
    assert "address already in use" in result.stderr
    assert "--port" in result.stderr
    assert "Traceback" not in result.stderr
    assert "ThreadingHTTPServer" not in result.stderr
    assert default_result.returncode == 2
    assert default_result.stdout == ""
    assert (
        f"microcosm serve could not bind http://127.0.0.1:{port}"
        in default_result.stderr
    )
    assert "--max-requests 7" in default_result.stderr
    assert "Traceback" not in default_result.stderr
    assert "ThreadingHTTPServer" not in default_result.stderr


def test_cli_pattern_route_readiness_accepts_exported_bundle(tmp_path: Path) -> None:
    out_dir = tmp_path / "pattern-route-readiness"
    status = cli.main(
        [
            "pattern-route-readiness",
            "validate-bundle",
            "--input",
            str(MICROCOSM_ROOT / "examples/pattern_binding_contract/exported_route_readiness_bundle"),
            "--out",
            str(out_dir),
        ]
    )

    result = json.loads(
        (out_dir / "exported_route_readiness_bundle_validation_result.json").read_text(
            encoding="utf-8"
        )
    )
    assert status == 0
    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_route_readiness_bundle"
    assert result["route_readiness_summary"]["status"] == "ok"
    assert result["selection_contract"]["selector_must_open"] == [
        "row_to_organ_router",
        "organ_route_cards",
        "organ_fixture_specs",
        "route_readiness_audit",
    ]
    assert result["authority_ceiling"]["public_leaf_authority"] is False


def test_cli_spine_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(["spine"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_runtime_spine_v1"
    assert payload["status"] == "pass"
    assert payload["surface_counts"]["adapter_backed_organ_count"] == (
        _adapter_backed_organ_count(MICROCOSM_ROOT)
    )
    assert payload["surface_counts"]["product_path_demoted_organ_count"] == (
        _demoted_organ_count()
    )
    first_run_by_step = _first_run_path_by_step_id(payload["first_run_path"])
    _assert_commands_in_order(
        payload["first_run_path"],
        [
            "microcosm tour --card <project>",
            "microcosm python-lens <project>",
            "microcosm spine",
            "microcosm authority",
            "microcosm prediction-lens",
            "microcosm market-boundary",
            "microcosm corpus-lens",
            "microcosm trace-lens",
            "microcosm repair-loop",
            "microcosm evidence-cells",
            "microcosm proof-loop-depth",
            PROOF_LAB_FIRST_SCREEN_COMMAND,
            VERIFIER_EXECUTION_LENS_COMMAND,
        ],
    )
    expected_step_commands = {
        "run_compact_tour_card": "microcosm tour --card <project>",
        "inspect_python_lens": "microcosm python-lens <project>",
        "inspect_public_spine": "microcosm spine",
        "inspect_authority_map": "microcosm authority",
        "inspect_prediction_lens": "microcosm prediction-lens",
        "inspect_market_prediction_boundary": "microcosm market-boundary",
        "inspect_corpus_lens": "microcosm corpus-lens",
        "inspect_verifier_trace_repair_lens": "microcosm trace-lens",
        "inspect_verifier_repair_loop": "microcosm repair-loop",
        "inspect_formal_evidence_cells": "microcosm evidence-cells",
        "inspect_proof_loop_depth": "microcosm proof-loop-depth",
        "inspect_verifier_lab_kernel": PROOF_LAB_FIRST_SCREEN_COMMAND,
        "inspect_verifier_lab_execution_spine": VERIFIER_EXECUTION_LENS_COMMAND,
        "inspect_work_landing_replay": "microcosm landing-replay",
        "inspect_view_quality_action_map": "microcosm view-quality",
        "inspect_projection_safety_audit": "microcosm projection-safety",
        "inspect_projection_drift_control": "microcosm drift-control",
        "inspect_route_cleanup_contract": "microcosm route-cleanup",
        "inspect_projection_import_map": "microcosm projection-import-map",
        "inspect_import_projector_contract": "microcosm import-projector",
        "inspect_compression_profile_option_surface": "microcosm option-surface-lens",
        "inspect_public_private_stripping_guard": "microcosm stripping-guard",
        "inspect_standards_control": "microcosm standards-control",
        "inspect_hook_intervention_coverage": "microcosm hook-coverage",
        "inspect_agent_reliability_replay_gauntlet": "microcosm replay-gauntlet",
        "inspect_repository_benchmark_transaction_lab": "microcosm benchmark-lab",
        "inspect_public_legibility_scorecard": "microcosm legibility-scorecard",
        "inspect_cold_reader_route_map": "microcosm cold-reader-route-map run-route-map-bundle",
    }
    for step_id, command in expected_step_commands.items():
        _assert_step_command(first_run_by_step, step_id, command)
    expected_prefix_commands = {
        "inspect_durable_agent_work_landing_replay": "microcosm durable-agent-work-landing-replay",
        "inspect_research_replication_rubric_artifact_replay": "microcosm research-replication-rubric-artifact-replay",
        "inspect_world_model_projection_drift_control_room": "microcosm world-model-projection-drift-control-room",
        "inspect_spatial_world_model_counterfactual_simulation_replay": "microcosm spatial-world-model-counterfactual-simulation-replay",
        "inspect_mechanistic_interpretability_circuit_attribution_replay": "microcosm mechanistic-interpretability-circuit-attribution-replay",
        "inspect_agent_memory_temporal_conflict_replay": "microcosm agent-memory-temporal-conflict-replay",
        "inspect_sleeper_memory_poisoning_quarantine_replay": "microcosm sleeper-memory-poisoning-quarantine-replay",
        "inspect_mcp_tool_authority_replay": "microcosm mcp-tool-authority-replay",
        "inspect_proof_derived_governed_mutation_authorization": "microcosm proof-derived-governed-mutation-authorization",
        "inspect_belief_state_process_reward_replay": "microcosm belief-state-process-reward-replay",
        "inspect_agent_sandbox_policy_escape_replay": "microcosm agent-sandbox-policy-escape-replay",
        "inspect_indirect_prompt_injection_information_flow_policy_replay": "microcosm indirect-prompt-injection-information-flow-policy-replay",
        "inspect_agentic_vulnerability_discovery_patch_proof_replay": "microcosm agentic-vulnerability-discovery-patch-proof-replay",
        "inspect_certificate_kernel_execution_lab": "microcosm certificate-kernel-execution-lab",
    }
    for step_id, command_prefix in expected_prefix_commands.items():
        _assert_step_command_prefix(first_run_by_step, step_id, command_prefix)
    assert payload["first_screen_proof_lab"]["status"] == "pass"
    assert payload["first_screen_proof_lab"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    proof_lab_step = first_run_by_step["inspect_verifier_lab_kernel"]
    assert proof_lab_step["route_ref"] == PROOF_LAB_ROUTE_REF
    assert proof_lab_step["receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert proof_lab_step["route_component_count"] == (
        payload["first_screen_proof_lab"]["route_component_count"]
    )
    assert first_run_by_step["inspect_verifier_lab_execution_spine"]["receipt_ref"] == (
        VERIFIER_EXECUTION_RECEIPT_REF
    )
    assert payload["authority_ceiling"]["release_authorized"] is False


def test_cli_authority_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_authority = (
        MICROCOSM_ROOT / "receipts/runtime_shell/public_authority_map.json"
    )
    source_reveal = (
        MICROCOSM_ROOT
        / "receipts/runtime_shell/public_reveal/public_reveal_view.json"
    )
    source_authority_before = source_authority.read_text(encoding="utf-8")
    source_reveal_before = source_reveal.read_text(encoding="utf-8")
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["authority"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_authority_map_v2"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm authority"
    assert payload["unsafe_payload_bodies_exported"] is False
    assert payload["payload_boundary"]["source_open_default"] is True
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["surface_counts"]["organ_authority_count"] == (
        _adapter_backed_organ_count(MICROCOSM_ROOT)
    )
    assert payload["surface_counts"]["surface_authority_count"] >= (
        _adapter_backed_organ_count(MICROCOSM_ROOT)
    )
    assert payload["surface_counts"]["organ_evidence_class_count"] == (
        _adapter_evidence_class_count(MICROCOSM_ROOT)
    )
    expected_truth_bucket_counts = _expected_adapter_truth_bucket_counts(MICROCOSM_ROOT)
    assert payload["surface_counts"]["copied_non_secret_macro_body_count"] == (
        expected_truth_bucket_counts["copied_non_secret_macro_body"]
    )
    assert (
        payload["surface_counts"]["copied_non_secret_macro_body_material_count"]
        == payload["macro_body_import_floor"]["public_safe_body_material_count"]
    )
    assert payload["surface_counts"]["copied_non_secret_macro_body_material_count"] >= 411
    assert payload["surface_counts"]["mixed_public_safe_macro_import_assay_status"] == "pass"
    assert payload["evidence_class_registry"]["fail_closed_no_default"] is True
    assert payload["count_scope"]["evidence_class_counts"].startswith(
        "adapter_backed_organ_rows_by_evidence_class"
    )
    assert "not copied source-body material files" in payload["count_scope"][
        "evidence_class_counts"
    ]
    assert "material row, not by organ evidence class" in payload["count_scope"][
        "public_safe_body_material_count"
    ]
    assert payload["evidence_class_counts"] == (
        _expected_adapter_evidence_class_counts(public_root)
    )
    organ_authority_by_id = {row["organ_id"]: row for row in payload["organ_authority"]}
    assert (
        organ_authority_by_id["materials_chemistry_closed_loop_lab_safety_replay"][
            "evidence_class"
        ]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["agent_sandbox_policy_escape_replay"][
            "evidence_class"
        ]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["formal_math_lean_proof_witness"]["evidence_class"]
        == "external_subprocess_witness"
    )
    assert (
        organ_authority_by_id["verifier_lab_kernel"]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["proof_diagnostic_evidence_spine"]["evidence_class"]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["durable_agent_work_landing_replay"]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["proof_derived_governed_mutation_authorization"][
            "evidence_class"
        ]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["world_model_projection_drift_control_room"]["evidence_class"]
        == "semantic_validator"
    )
    assert (
        organ_authority_by_id["spatial_world_model_counterfactual_simulation_replay"][
            "evidence_class"
        ]
        == "bounded_runtime_computation"
    )
    assert (
        organ_authority_by_id[
            "mechanistic_interpretability_circuit_attribution_replay"
        ]["evidence_class"]
        == "bounded_runtime_computation"
    )
    assert (
        organ_authority_by_id["research_replication_rubric_artifact_replay"]["evidence_class"]
        == "algorithmic_projection"
    )
    assert (
        organ_authority_by_id["agentic_vulnerability_discovery_patch_proof_replay"][
            "evidence_class"
        ]
        == "algorithmic_projection"
    )
    assert any(row["surface_id"] == "project_python_lens" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/authority" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/tour" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/market-boundary" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/hook-coverage" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/replay-gauntlet" for row in payload["surface_authority"])
    assert any(
        row["surface_id"] == "public_verifier_lab_kernel_lens"
        and row["provider_hypothesis_proof_authority"] is False
        and row["route_id"] == "formal_prover_context_strategy_gate"
        and row["receipt_ref"] == PROOF_LAB_RECEIPT_REF
        and row["route_component_count"] == 9
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_verifier_lab_execution_spine_lens"
        and row["bounded_public_external_witness_only"] is True
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_agent_sabotage_scheming_monitor_replay_lens"
        and row["runtime_mode"] == "drilldown_only"
        and row["product_path_role"] == "drilldown_regression_not_runtime_spine"
        for row in payload["surface_authority"]
    )
    assert any(row["surface_id"] == "public_mcp_tool_authority_replay_lens" for row in payload["surface_authority"])
    assert any(
        row["surface_id"]
        == "public_proof_derived_governed_mutation_authorization_lens"
        for row in payload["surface_authority"]
    )
    assert source_authority.read_text(encoding="utf-8") == source_authority_before
    assert source_reveal.read_text(encoding="utf-8") == source_reveal_before
    assert any(
        row["surface_id"] == "public_belief_state_process_reward_replay_lens"
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_agent_sandbox_policy_escape_replay_lens"
        for row in payload["surface_authority"]
    )
    assert any(
        row["surface_id"] == "public_indirect_prompt_injection_information_flow_policy_replay_lens"
        for row in payload["surface_authority"]
    )
    assert any(row["endpoint"] == "/corpus" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/trace" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/repair-loop" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/evidence-cells" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/proof-loop-depth" for row in payload["surface_authority"])
    assert any(
        row["endpoint"] == "/verifier-lab-execution-spine"
        for row in payload["surface_authority"]
    )
    assert any(row["endpoint"] == "/landing-replay" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/view-quality" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/projection-safety" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/drift-control" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/spatial-simulation" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/circuit-attribution" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/route-cleanup" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/projection-import-map" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/import-projector" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/option-surface-lens" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/stripping-guard" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/standards-control" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/benchmark-lab" for row in payload["surface_authority"])
    assert any(row["endpoint"] == "/legibility-scorecard" for row in payload["surface_authority"])


def test_cli_authority_card_exposes_top_level_false_authority_booleans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["authority", "--card"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_authority_card_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm authority --card"
    assert payload["release_authorized"] is False
    assert payload["provider_calls_authorized"] is False
    assert payload["source_mutation_authorized"] is False
    assert payload["release_authorized"] == (
        payload["authority_ceiling"]["release_authorized"]
    )
    assert payload["provider_calls_authorized"] == (
        payload["authority_ceiling"]["provider_calls_authorized"]
    )
    assert payload["source_mutation_authorized"] == (
        payload["authority_ceiling"]["source_mutation_authorized"]
    )


def test_cli_authority_card_accepts_project_argument_for_first_screen_parity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = _copy_runtime_root(tmp_path)

    status = cli.main(["authority", "--card", str(public_root)])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_authority_card_v1"
    assert payload["command"] == "microcosm authority --card"
    assert payload["release_authorized"] is False


def test_cli_workingness_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = _copy_workingness_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["workingness"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_workingness_failure_map_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm workingness"
    assert payload["endpoint"] == "/workingness"
    assert payload["completeness_status"] == "complete_failure_modes"
    assert payload["map_generation_status"] == "pass"
    assert payload["failure_envelope_status"] == "clear"
    assert payload["mapped_organ_count"] == _accepted_organ_count(public_root)
    assert payload["adapter_backed_organ_count"] == (
        _adapter_backed_organ_count(public_root)
    )
    assert payload["demoted_drilldown_count"] == _demoted_organ_count()
    assert payload["missing_standard_count"] == 0
    assert payload["missing_failure_modes_count"] == 0
    assert payload["rows_with_failure_modes"] == _accepted_organ_count(public_root)
    assert payload["accepted_status_is_not_evidence_strength"] is True
    assert payload["not_a_scorecard"] is True
    assert payload["gap_preview"]["status"] == "clear"
    assert payload["surface_counts"]["mapped_organ_count"] == (
        _accepted_organ_count(public_root)
    )
    assert payload["surface_counts"]["adapter_backed_organ_count"] == (
        _adapter_backed_organ_count(public_root)
    )
    assert payload["surface_counts"]["demoted_drilldown_count"] == (
        _demoted_organ_count()
    )
    assert payload["surface_counts"]["missing_failure_modes_count"] == 0
    rows_by_id = {row["thing_id"]: row for row in payload["thing_failure_map"]}
    assert rows_by_id["verifier_lab_kernel"]["workingness_state"] == (
        "evidence_backed_runtime_spine"
    )
    assert rows_by_id["agent_monitor_redteam_falsification_replay"][
        "workingness_state"
    ] == "demoted_regression_drilldown"
    assert (public_root / payload["workingness_map_ref"]).is_file()


def test_cli_workingness_card_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = _copy_workingness_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["workingness", "--card"])

    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload, sort_keys=True)
    assert status == 0
    assert payload["schema_version"] == "microcosm_workingness_command_speed_card_v1"
    assert payload["status"] == "pass"
    assert payload["card_status"] == "clear"
    assert payload["command"] == "microcosm workingness --card"
    assert payload["source_command"] == "microcosm workingness"
    assert payload["drilldown_command"] == "microcosm workingness"
    assert payload["endpoint"] == "/workingness-card"
    assert payload["full_endpoint"] == "/workingness"
    assert payload["drilldown_endpoint"] == "/workingness"
    assert payload["completeness_status"] == "complete_failure_modes"
    assert payload["surface_counts"]["mapped_organ_count"] == (
        _accepted_organ_count(public_root)
    )
    assert payload["surface_counts"]["adapter_backed_organ_count"] == (
        _adapter_backed_organ_count(public_root)
    )
    assert payload["surface_counts"]["demoted_drilldown_count"] == (
        _demoted_organ_count()
    )
    assert payload["surface_counts"]["rows_with_failure_modes"] == (
        _accepted_organ_count(public_root)
    )
    assert payload["surface_counts"]["missing_standard_count"] == 0
    assert payload["surface_counts"]["missing_failure_modes_count"] == 0
    assert payload["output_economy"]["thing_failure_map_exported"] is False
    assert payload["output_economy"]["known_failure_mode_rows_exported"] is False
    assert payload["output_economy"]["receipt_persisted"] is False
    assert "thing_failure_map" not in payload
    assert "known_failure_modes" not in encoded
    assert len(encoded) < 8000
    assert not (
        public_root / "receipts/runtime_shell/workingness_failure_map.json"
    ).exists()


def test_cli_workingness_card_accepts_project_argument_for_first_screen_parity(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = _copy_workingness_root(tmp_path)

    status = cli.main(["workingness", "--card", str(public_root)])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_workingness_command_speed_card_v1"
    assert payload["command"] == "microcosm workingness --card"
    assert payload["card_status"] == "clear"


def test_cli_tour_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_tour = MICROCOSM_ROOT / "receipts/runtime_shell/public_ten_minute_tour.json"
    source_tour_before = source_tour.read_text(encoding="utf-8")
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["tour"])

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "microcosm_public_ten_minute_tour_v1"
    assert payload["status"] == "pass"
    assert payload["command"] == "microcosm tour <project>"
    assert payload["endpoint"] == "/tour"
    assert payload["time_budget_minutes"] == 10
    assert payload["compile_summary"]["headline"] == "repo -> .microcosm"
    assert payload["snapshot_policy"]["test_runs_should_use_temp_public_root"] is True
    assert payload["authority_ceiling"]["release_authorized"] is False
    assert payload["first_screen"]["schema_version"] == (
        "microcosm_cold_reader_first_screen_v1"
    )
    assert payload["first_screen"]["primary_command"] == (
        "microcosm tour --card <project>"
    )
    assert payload["first_screen"]["minimal_command_path"][0]["command"] == (
        payload["first_screen"]["primary_command"]
    )
    assert payload["first_screen"]["selected_route_id"] == (
        payload["compile_summary"]["selected_route_id"]
    )
    assert payload["selected_route_id"] == payload["first_screen"]["selected_route_id"]
    assert payload["first_screen"]["route_explanation"]["command"] == (
        f"microcosm explain <project> {payload['first_screen']['selected_route_id']}"
    )
    assert payload["first_screen"]["generated_state"]["state_dir"] == ".microcosm"
    assert payload["first_screen"]["proof_surface"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert payload["first_screen"]["behavior_surfaces"]["observatory_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
    )
    assert payload["first_screen"]["behavior_surfaces"][
        "observatory_interactive_command"
    ] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert payload["first_screen"]["behavior_surfaces"]["project_observe_command"] == (
        "microcosm observe --card <project>"
    )
    assert payload["first_screen"]["behavior_surfaces"][
        "project_observe_full_command"
    ] == (
        "microcosm observe <project>"
    )
    assert payload["first_screen"]["behavior_surfaces"]["project_observe_endpoint"] == (
        "/project/observe"
    )
    assert payload["command_path"][0] == "microcosm tour --card <project>"
    assert "microcosm status --card" in payload["command_path"]
    assert "microcosm workingness" in payload["command_path"]
    assert "microcosm observe --card <project>" in payload["command_path"]
    assert "/workingness-card" in payload["endpoint_path"]
    assert "/project/observe" in payload["endpoint_path"]
    assert any(
        row["step_id"] == "inspect_status_card"
        for row in payload["first_screen"]["minimal_command_path"]
    )
    assert any(
        row["step_id"] == "inspect_workingness"
        for row in payload["first_screen"]["minimal_command_path"]
    )
    tour_step_ids = [
        row["step_id"] for row in payload["first_screen"]["minimal_command_path"]
    ]
    assert tour_step_ids.index("inspect_status_card") < tour_step_ids.index(
        "inspect_workingness"
    )
    assert tour_step_ids.index("inspect_workingness") < tour_step_ids.index(
        "compile_project"
    )
    assert tour_step_ids.index("run_first_screen_proof_lab") < tour_step_ids.index(
        "inspect_project_observe"
    )
    assert tour_step_ids.index("inspect_project_observe") < tour_step_ids.index(
        "open_observatory"
    )
    tour_steps_by_id = {
        row["step_id"]: row for row in payload["first_screen"]["minimal_command_path"]
    }
    assert tour_steps_by_id["open_observatory"]["interactive_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert tour_step_ids.index("run_first_screen_proof_lab") < tour_step_ids.index(
        "inspect_python_routes"
    )
    assert any(
        card["card_id"] == "status_and_workingness"
        and card["workingness_command"] == "microcosm workingness --card"
        for card in payload["route_cards"]
    )
    assert payload["first_screen_proof_lab"]["status"] == "pass"
    assert payload["first_screen_proof_lab"]["route_id"] == (
        "formal_prover_context_strategy_gate"
    )
    assert payload["first_screen_proof_lab"]["route_ref"] == PROOF_LAB_ROUTE_REF
    assert payload["first_screen_proof_lab"]["receipt_ref"] == PROOF_LAB_RECEIPT_REF
    assert any(
        card["card_id"] == "verifier_lab_kernel"
        and card["route_component_count"] == 9
        for card in payload["route_cards"]
    )
    assert (public_root / payload["tour_ref"]).is_file()
    assert source_tour.read_text(encoding="utf-8") == source_tour_before


def test_cli_tour_prefers_project_public_root_for_installed_clone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    (public_root / "core").mkdir(parents=True)
    (public_root / "standards").mkdir()
    (public_root / "core/organ_evidence_classes.json").write_text("{}", encoding="utf-8")
    (public_root / "core/organ_registry.json").write_text("{}", encoding="utf-8")
    (
        public_root / "standards/std_microcosm_first_screen_composition_root.json"
    ).write_text("{}", encoding="utf-8")
    captured: dict[str, object] = {}

    def fake_runtime_main(args: list[str], *, root: Path | None = None) -> int:
        captured["args"] = args
        captured["root"] = root
        print('{"status":"pass"}')
        return 0

    monkeypatch.setattr(cli.runtime_shell, "main", fake_runtime_main)

    status = cli.main(["tour", str(public_root)])

    assert status == 0
    assert json.loads(capsys.readouterr().out) == {"status": "pass"}
    assert captured["args"] == ["tour", str(public_root)]
    assert captured["root"] == public_root.resolve(strict=False)


def test_cli_tour_card_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    public_root = _copy_runtime_root(tmp_path)
    monkeypatch.setattr(cli.runtime_shell, "public_root", lambda: public_root)

    status = cli.main(["tour", "--card"])

    stdout = capsys.readouterr().out
    payload = json.loads(stdout)
    encoded = json.dumps(payload, sort_keys=True)
    body_floor_blocked = (
        payload["surface_statuses"].get("macro_body_import_floor") != "pass"
    )
    assert status == (1 if body_floor_blocked else 0)
    assert payload["schema_version"] == "microcosm_tour_command_speed_card_v1"
    assert payload["status"] == ("blocked" if body_floor_blocked else "pass")
    assert payload["card_status"] == ("blocked" if body_floor_blocked else "clear")
    assert payload["command"] == "microcosm tour --card <project>"
    assert payload["source_command"] == "microcosm tour <project>"
    assert payload["drilldown_command"] == "microcosm tour <project>"
    assert payload["endpoint"] == "/tour"
    assert payload["first_screen"]["primary_command"] == (
        "microcosm tour --card <project>"
    )
    assert "reader_routes" not in payload["first_screen"]
    assert payload["first_screen"]["reader_routes_ref"] == (
        "atlas/entry_packet.json::reader_first_screen_routes"
    )
    assert (
        payload["first_screen"]["minimal_steps"][0]["command"]
        == "microcosm tour --card <project>"
    )
    compact_steps_by_id = {
        row["step_id"]: row for row in payload["first_screen"]["minimal_steps"]
    }
    assert compact_steps_by_id["open_observatory"]["command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
    )
    assert compact_steps_by_id["open_observatory"]["interactive_command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765"
    )
    assert payload["first_screen"]["minimal_step_count"] == 10
    assert payload["first_screen"]["project_observe_command"] == (
        "microcosm observe --card <project>"
    )
    assert payload["state_refs"]["route_state_ref"] == ".microcosm/routes.json"
    assert payload["state_refs"]["work_state_ref"] == ".microcosm/work_items.json"
    assert payload["state_refs"]["event_log_ref"] == ".microcosm/events.jsonl"
    assert payload["state_refs"]["evidence_dir_ref"] == ".microcosm/evidence/"
    assert payload["state_refs"]["graph_ref"] == ".microcosm/graph.json"
    assert payload["state_refs"]["ref_count"] >= 8
    assert "refs" not in payload["state_refs"]
    assert payload["state_inspection"]["status"] == "pass"
    assert payload["state_inspection"]["state_dir"] == ".microcosm"
    assert payload["state_inspection"]["state_dir_exists"] is True
    assert payload["state_inspection"]["state_file_count"] >= 8
    assert payload["state_inspection"]["state_ref_count"] >= 8
    assert payload["state_inspection"]["inspect_command"] == (
        "find <project>/.microcosm -maxdepth 2 -type f | sort"
    )
    assert payload["state_inspection"]["route_state_json_check_command"] == (
        "python3 -m json.tool <project>/.microcosm/routes.json"
    )
    assert ".microcosm/routes.json" in payload["state_inspection"]["first_screen_refs"]
    assert ".microcosm/graph.json" in payload["state_inspection"]["first_screen_refs"]
    state_write_result = payload["state_write_result"]
    assert state_write_result["schema_version"] == (
        "microcosm_tour_card_state_write_result_v1"
    )
    assert state_write_result["status"] == "pass"
    assert state_write_result["status_scope"] == "project_local_state_write_only"
    assert state_write_result["command"] == "microcosm tour --card <project>"
    assert state_write_result["writes_microcosm_state"] == (
        state_write_result["project_compile_state_written"]
    )
    assert state_write_result["compile_cache_status"] in {
        "cached_state_read",
        "missing_cache",
        "stale_cached_state",
        "fresh_cached_state",
    }
    assert state_write_result["compile_cache_source_ref"] in {
        None,
        ".microcosm/state_index.json",
    }
    assert state_write_result["state_dir"] == ".microcosm"
    assert state_write_result["state_dir_exists"] is True
    assert state_write_result["state_file_count"] == (
        payload["state_inspection"]["state_file_count"]
    )
    assert state_write_result["source_files_mutated"] is False
    assert state_write_result["first_screen_map_ref"] == (
        "microcosm first-screen <project>::state_write_boundary"
    )
    assert state_write_result["front_door_status_ref"] == "front_door_status"
    assert state_write_result["inspect_command"] == (
        "find <project>/.microcosm -maxdepth 2 -type f | sort"
    )
    assert state_write_result["route_state_json_check_command"] == (
        "python3 -m json.tool <project>/.microcosm/routes.json"
    )
    assert "state availability proof" in state_write_result["reader_action"]
    assert "Cached pass cards reuse current state" in state_write_result["reader_action"]
    assert state_write_result["safe_to_show"] == {
        "project_local_state_refs_visible": True,
        "source_files_mutated": False,
        "provider_calls_authorized": False,
        "release_or_hosting_authorized": False,
        "proof_correctness_claim": False,
    }
    assert payload["observatory"]["compact_endpoint"] == "/project/observatory-card"
    assert payload["observatory"]["status_card_endpoint"] == "/project/status"
    assert payload["observatory"]["command"] == (
        "microcosm serve <project> --host 127.0.0.1 --port 8765 --max-requests 7"
    )
    assert payload["observatory"]["project_observe_endpoint"] == "/project/observe"
    assert payload["observatory"]["project_observe_ref"] == (
        "microcosm serve <project>::/project/observe"
    )
    assert payload["observatory"]["route_explanation_endpoint"] == (
        "/project/explain/readme_onboarding_route"
    )
    assert payload["observatory"]["first_screen_route_proof_ref"] == (
        "microcosm serve <project>::first_screen_route_proof"
    )
    assert (
        "microcosm observe --card examples/runtime_shell/demo_project"
        in payload["next_commands"]
    )
    assert payload["status_card"]["command"] == "microcosm status --card <project>"
    assert payload["surface_statuses"]["compile"] == "pass"
    assert payload["surface_statuses"]["state_write"] == "pass"
    assert payload["surface_statuses"]["state_inspection"] == "pass"
    assert payload["surface_statuses"]["proof_lab"] == "pass"
    assert payload["surface_statuses"]["proof_lab_cache"] in {"pass", "actionable"}
    assert payload["surface_statuses"]["workingness_card"] == "pass"
    assert (
        payload["front_door_status"]["schema_version"]
        == "microcosm_tour_card_front_door_status_v1"
    )
    assert payload["front_door_status"]["status"] == payload["status"]
    assert payload["front_door_status"]["surface_statuses"] == payload["surface_statuses"]
    assert (
        payload["front_door_status"]["blocking_surface_ids"]
        == payload["blocking_surface_ids"]
    )
    assert payload["front_door_status"]["blocking_surface_details_ref"] == (
        "blocking_surface_details"
    )
    assert (
        payload["front_door_status"]["safe_to_show"]["blocking_surface_ids_visible"]
        is True
    )
    assert (
        payload["front_door_status"]["authority_ceiling"]["proof_correctness_claim"]
        is False
    )
    if body_floor_blocked:
        assert "macro_body_import_floor" in payload["blocking_surface_ids"]
        _assert_body_floor_blocking_details(
            payload["blocking_surface_details"]["macro_body_import_floor"]
        )
    else:
        assert payload["blocking_surface_ids"] == []
    assert payload["workingness"]["command"] == "microcosm workingness --card"
    assert payload["output_economy"]["full_route_cards_exported"] is False
    assert payload["output_economy"]["route_cards_by_id_exported"] is False
    assert payload["output_economy"]["full_command_path_exported"] is False
    assert payload["output_economy"]["full_endpoint_path_exported"] is False
    assert payload["output_economy"]["state_refs_exported"] is True
    assert payload["output_economy"]["state_inspection_exported"] is True
    assert payload["output_economy"]["state_write_result_exported"] is True
    assert payload["output_economy"]["observatory_refs_exported"] is True
    assert payload["output_economy"]["receipt_persisted"] is False
    assert payload["output_economy"]["reader_routes_exported"] is False
    assert "route_cards" not in payload
    assert "route_cards_by_id" not in payload
    assert "endpoint_path" not in payload
    assert "command_path" not in payload
    assert len(encoded) < 14500
    assert len(stdout.encode("utf-8")) < 15000
    assert not (
        public_root / "receipts/runtime_shell/public_ten_minute_tour.json"
    ).exists()


def test_cli_tour_card_reports_tracked_receipt_refresh_env(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("MICROCOSM_TRACKED_RECEIPT_WRITES", raising=False)
    monkeypatch.delenv("MICROCOSM_RUNTIME_RECEIPT_WRITES", raising=False)

    status = cli.main(["tour", "--card"])

    payload = json.loads(capsys.readouterr().out)
    policy = payload["receipt_write_policy"]
    assert status == 0
    assert policy["public_tour_receipt_ref"] == (
        "receipts/runtime_shell/public_ten_minute_tour.json"
    )
    assert policy["compact_card_writes_public_tour_receipt"] is False
    assert policy["full_tour_attempts_public_tour_receipt_write"] is True
    assert policy["full_tour_writes_public_tour_receipt"] is False
    assert policy["tracked_receipt_refresh_requires_env"] is True
    assert policy["tracked_receipt_refresh_env"] == (
        "MICROCOSM_TRACKED_RECEIPT_WRITES=1"
    )


def test_cli_macro_projection_plan_smoke(capsys: pytest.CaptureFixture[str]) -> None:
    status = cli.main(
        [
            "macro-projection-import-protocol",
            "plan",
            "--input",
            (
                MICROCOSM_ROOT
                / "examples/macro_projection_import_protocol/exported_projection_import_bundle"
            ).as_posix(),
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["schema_version"] == "macro_projection_import_intake_preview_v1"
    assert payload["projection_intake_board"]["ready_cell_count"] == sum(
        payload["projection_intake_board"]["projection_status_counts"].values()
    )
    assert payload["projection_intake_board"]["blocked_cell_count"] == 0
    assert payload["projection_intake_board"]["projection_status_counts"][
        "self_hosted_status_protocol_landed"
    ] == 1
    assert payload["projection_intake_board"]["open_actionable_cell_count"] == 0
    assert payload["authority_ceiling"]["release_authorized"] is False


def test_cli_public_entry_docs_smoke_uses_temp_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    public_root = _copy_public_entry_tree(tmp_path)
    monkeypatch.chdir(public_root)
    out = Path("receipts/first_wave/public_entry_docs_validation.json")

    status = cli.main(
        [
            "public-entry-docs",
            "--root",
            ".",
            "--out",
            out.as_posix(),
        ]
    )

    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert status == 0
    assert receipt["status"] == "pass"
    assert receipt["blocking_codes"] == []
    assert receipt["secret_exclusion_scan"]["body_in_receipt"] is False
    assert receipt["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert receipt["payload_boundary"]["source_open_default"] is True
    assert receipt["payload_boundary"]["unsafe_payload_bodies_in_receipt"] is False
    text = out.read_text(encoding="utf-8")
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
