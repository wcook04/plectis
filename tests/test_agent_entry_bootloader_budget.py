"""Agent-entry bootloader contract.

Coding agents discover repo instruction files under hard context budgets
(for example, Codex documents a 32 KiB default combined project-doc cap).
The root agent entry therefore has to behave like a boot sector: the first
kilobytes must hand an arriving agent its first correct action and the
human/agent split, regardless of how large the full reference body is.

These tests pin the property, not the prose, so the entry files can keep
improving without re-pinning every paragraph.
"""

from __future__ import annotations

from pathlib import Path

MICROCOSM_ROOT = Path(__file__).resolve().parents[1]

# AGENTS.md byte ceiling: a must-not-grow ratchet, not an endorsement.
# Measured 60,307 bytes on 2026-06-11. Target after the reference-body
# compression mission (cap_quick_microcosm_readme_reference_body_wall_rep_
# 9ee89d860623 covers the sibling README wall; AGENTS follows the same
# inventory-first method) is <= 32_768 bytes so the whole file survives a
# default agent discovery budget.
AGENTS_MUST_NOT_GROW_CEILING = 61_440
AGENTS_TARGET_BUDGET = 32_768

BOOTLOADER_WINDOW = 4_096
REDIRECT_WINDOW = 1_024
ADAPTER_STUB_CEILING = 4_096


def _read_bytes(name: str) -> bytes:
    return (MICROCOSM_ROOT / name).read_bytes()


def test_agents_first_kilobytes_hand_an_agent_its_first_action() -> None:
    head = _read_bytes("AGENTS.md")[:BOOTLOADER_WINDOW].decode("utf-8", "replace")
    assert 'comprehend --first-action "<your goal>"' in head, (
        "AGENTS.md must give the first-action command inside the first "
        f"{BOOTLOADER_WINDOW} bytes; an agent reading only the head must "
        "leave with its first correct move."
    )


def test_agents_head_routes_humans_out_immediately() -> None:
    head = _read_bytes("AGENTS.md")[:REDIRECT_WINDOW].decode("utf-8", "replace")
    assert "[README.md](README.md)" in head, (
        "The human redirect must sit in the first "
        f"{REDIRECT_WINDOW} bytes of AGENTS.md."
    )


def test_agents_size_is_ratcheted_down_not_up() -> None:
    size = len(_read_bytes("AGENTS.md"))
    assert size <= AGENTS_MUST_NOT_GROW_CEILING, (
        f"AGENTS.md grew to {size} bytes (ceiling "
        f"{AGENTS_MUST_NOT_GROW_CEILING}). It already exceeds the "
        f"{AGENTS_TARGET_BUDGET}-byte agent-discovery target; move new "
        "inventory to the generated atlas (AGENT_ROUTES.md / ORGANS.md) "
        "instead of widening the root entry."
    )


def test_provider_adapters_stay_boot_sector_thin() -> None:
    for name in ("CLAUDE.md", "CODEX.md", "CURSOR.md"):
        body = _read_bytes(name)
        assert len(body) <= ADAPTER_STUB_CEILING, (
            f"{name} is {len(body)} bytes; provider adapters must stay thin "
            "stubs that route to AGENTS.md and add no authority."
        )
        assert b"AGENTS.md" in body, f"{name} must route to AGENTS.md."
