from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
PROFILE = MICROCOSM_ROOT / "scripts/public_repo_profile.py"


def _run(*args: str, cwd: Path = MICROCOSM_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(PROFILE), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_profile_passes_on_this_repository() -> None:
    result = _run("--root", str(MICROCOSM_ROOT), "--json")
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "pass"
    assert report["failures"] == []
    assert report["mode"] == "python_research_tool"
    # The remaining root documents are classified pending-migration surfaces,
    # every one owned by the root migration plan; nothing is unclassified.
    allow = report["root_allowlist"]
    assert allow["unclassified_entries"] == []
    for plan in allow["classified_pending_migration"].values():
        assert plan == "docs/maintainers/root-migration-plan.md"
        assert (MICROCOSM_ROOT / plan).is_file()
    # First-screen shape held.
    first_screen = report["readme_first_screen"]
    assert first_screen["h1"] == "Plectis"
    assert first_screen["hero_install_block"] is True
    assert first_screen["foreign_repo_links_in_hero"] == []
    assert first_screen["legacy_name_leaks"] == []
    # Version metadata agrees between citation and packaging.
    versions = report["version_consistency"]
    assert versions["citation_cff"] == versions["build_metadata"]
    # A pass is presentation legibility only.
    assert report["authority_ceiling"]["release_authorized"] is False


def test_profile_fails_on_unclassified_root_clutter(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text(
        "# Thing\n\n[a](LICENSE) [b](CONTRIBUTING.md)\n\n"
        "```bash\npip install thing\n```\n\n## More\n",
        encoding="utf-8",
    )
    for name in ("LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CITATION.cff",
                 "CHANGELOG.md", "pyproject.toml"):
        (root / name).write_text("placeholder\n", encoding="utf-8")
    (root / ".github/ISSUE_TEMPLATE").mkdir(parents=True)
    (root / "INTERNAL_DOCTRINE.md").write_text("private ops\n", encoding="utf-8")

    result = _run("--root", str(root), "--json")
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "fail"
    assert "INTERNAL_DOCTRINE.md" in report["root_allowlist"]["unclassified_entries"]
    assert any("root_allowlist" in failure for failure in report["failures"])


def test_profile_fails_when_hero_promotes_unrelated_repository(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / ".github/ISSUE_TEMPLATE").mkdir(parents=True)
    for name in ("LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CITATION.cff",
                 "CHANGELOG.md", "pyproject.toml"):
        (root / name).write_text("placeholder\n", encoding="utf-8")
    (root / "README.md").write_text(
        "# Plectis\n\n"
        "[other](https://github.com/wcook04/plectis-lean-erdos249-257) "
        "[a](LICENSE) [b](CONTRIBUTING.md)\n\n"
        "```bash\npip install plectis\n```\n\n## More\n",
        encoding="utf-8",
    )

    result = _run("--root", str(root), "--json")
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert any(
        "unrelated repository promoted above the fold" in failure
        for failure in report["failures"]
    )
