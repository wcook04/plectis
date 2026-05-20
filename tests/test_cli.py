from __future__ import annotations

import json
import shutil
import tomllib
from pathlib import Path

import pytest

from microcosm_core import cli


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _copy_public_entry_tree(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(MICROCOSM_ROOT / "paper_modules", public_root / "paper_modules")
    shutil.copytree(MICROCOSM_ROOT / "skills", public_root / "skills")
    shutil.copy2(MICROCOSM_ROOT / "README.md", public_root / "README.md")
    shutil.copy2(MICROCOSM_ROOT / "AGENTS.md", public_root / "AGENTS.md")
    (public_root / "receipts/first_wave").mkdir(parents=True)
    return public_root


def test_package_metadata_describes_runtime_spine() -> None:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = payload["project"]
    description = project["description"]

    assert "runtime-spine" in description
    assert "first-slice" not in description
    assert project["readme"] == "README.md"
    assert project["license"] == {"file": "LICENSE"}
    assert project["authors"] == [{"name": "Microcosm Substrate Contributors"}]
    assert "License :: OSI Approved :: Apache Software License" in project["classifiers"]
    assert payload["project"]["urls"]["Homepage"] == "https://github.com/wcook04/ai-workflow-proof"
    assert (MICROCOSM_ROOT / "LICENSE").read_text(encoding="utf-8").startswith("Apache License")


def test_cli_help_lists_public_runtime_spine_commands(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--help"])

    assert excinfo.value.code == 0
    output = capsys.readouterr().out
    for command in [
        "private-state-scan",
        "public-entry-docs",
        "standards-registry",
        "dependency-preflight",
        "fixture-freshness",
        "pattern-binding",
        "executable-doctrine-grammar",
        "proof-diagnostic-evidence-spine",
        "navigation-hologram-route-plane",
        "mission-transaction-work-spine",
        "agent-route-observability-runtime",
        "pattern-assimilation-step",
    ]:
        assert command in output


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
    assert receipt["private_state_scan"]["body_redacted"] is True
    text = out.read_text(encoding="utf-8")
    assert "/Users/" not in text
    assert "src/ai_workflow" not in text
    assert "matched_excerpt" not in text
    assert '"body":' not in text
