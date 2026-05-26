from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _readme_text() -> str:
    return (MICROCOSM_ROOT / "README.md").read_text(encoding="utf-8")


def test_readme_first_screen_starts_with_hello_then_behavior() -> None:
    section = _readme_text().split("## Choose Your First Screen", 1)[1].split(
        "## Try It On Your Repo",
        1,
    )[0]

    assert "microcosm hello <project>" in section
    assert "microcosm tour --card <project>" in section
    assert "microcosm first-screen <project>" in section
    assert section.index("microcosm hello <project>") < section.index(
        "microcosm tour --card <project>"
    )
    assert section.index("microcosm tour --card <project>") < section.index(
        "microcosm first-screen <project>"
    )
    normalized_section = " ".join(section.split())
    assert (
        "`hello` is the text projection of the first-screen card."
        in normalized_section
    )
    assert "It is not a separate proof surface." in normalized_section
    assert "Evidence counts are accounting, not maturity scores." in section
    assert "Most projects do not publish that boundary" in section


def test_readme_installed_path_and_browser_surface_reuse_first_screen() -> None:
    text = _readme_text()
    direct_path = text.split(
        "Or run the same product CLI directly from the checkout without installing the\n"
        "entry point:",
        1,
    )[1].split("After the console command is installed, the first-screen path is:", 1)[
        0
    ]
    installed_path = text.split(
        "After the console command is installed, the first-screen path is:",
        1,
    )[1].split("The quickest human first screen is", 1)[0]
    browser_path = text.split(
        "`http://127.0.0.1:8765/project/status` for the same compact status-card lens",
        1,
    )[1].split("Use `microcosm status --card <project>`", 1)[0]

    direct_hello = "PYTHONPATH=src python3 -m microcosm_core.cli hello ."
    direct_tour_card = "PYTHONPATH=src python3 -m microcosm_core.cli tour --card ."
    assert direct_hello in direct_path
    assert direct_path.index(direct_hello) < direct_path.index(direct_tour_card)
    assert "microcosm hello ." in installed_path
    assert "microcosm first-screen ." in installed_path
    assert installed_path.index("microcosm hello .") < installed_path.index(
        "microcosm tour --card ."
    )
    assert installed_path.index("microcosm tour --card .") < installed_path.index(
        "microcosm first-screen ."
    )
    assert installed_path.index("microcosm first-screen .") < installed_path.index(
        "microcosm status --card ."
    )
    assert "http://127.0.0.1:8765/project/first-screen" in browser_path
    assert browser_path.index("/project/first-screen") < browser_path.index(
        "/project/observatory-card"
    )
