from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


class SmokeCheckError(Exception):
    """Raised when a smoke receipt is missing or contradicts the public floor."""


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SmokeCheckError(f"{path.name}: missing required smoke receipt")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SmokeCheckError(f"{path.name}: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise SmokeCheckError(f"{path.name}: expected a JSON object")
    return payload


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise SmokeCheckError(f"{path.name}: missing required smoke receipt")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise SmokeCheckError(f"{path.name}: empty smoke receipt")
    return text


def _expect_status(payload: dict[str, Any], *, name: str, status: str = "pass") -> None:
    actual = payload.get("status")
    if actual != status:
        raise SmokeCheckError(f"{name}: expected status {status!r}, got {actual!r}")


def _expect_false(
    payload: dict[str, Any],
    *,
    name: str,
    key: str,
    source: str | None = None,
) -> None:
    actual = payload.get(key)
    if actual is not False:
        label = f"{source}.{key}" if source else key
        raise SmokeCheckError(f"{name}: expected {label} false, got {actual!r}")


def _expect_authority_false(
    payload: dict[str, Any],
    *,
    name: str,
    key: str,
) -> None:
    authority_ceiling = payload.get("authority_ceiling")
    if not isinstance(authority_ceiling, dict):
        raise SmokeCheckError(f"{name}: missing authority_ceiling object")
    actual = authority_ceiling.get(key)
    if actual is not False:
        raise SmokeCheckError(
            f"{name}: expected authority_ceiling.{key} false, got {actual!r}",
        )


def _expect_nonnegative_int(
    payload: dict[str, Any],
    *,
    name: str,
    key: str,
) -> int:
    actual = payload.get(key)
    if not isinstance(actual, int) or isinstance(actual, bool) or actual < 0:
        raise SmokeCheckError(f"{name}: expected nonnegative integer {key}, got {actual!r}")
    return actual


def _expect_positive_surface_count(
    payload: dict[str, Any],
    *,
    name: str,
    key: str,
) -> int:
    surface_counts = payload.get("surface_counts")
    if not isinstance(surface_counts, dict):
        raise SmokeCheckError(f"{name}: missing surface_counts object")
    actual = surface_counts.get(key)
    if not isinstance(actual, int) or isinstance(actual, bool) or actual <= 0:
        raise SmokeCheckError(
            f"{name}: expected positive surface_counts.{key}, got {actual!r}",
        )
    return actual


def _expect_surface_count(
    payload: dict[str, Any],
    *,
    name: str,
    key: str,
    expected: int,
) -> int:
    surface_counts = payload.get("surface_counts")
    if not isinstance(surface_counts, dict):
        raise SmokeCheckError(f"{name}: missing surface_counts object")
    actual = surface_counts.get(key)
    if actual != expected:
        raise SmokeCheckError(
            f"{name}: expected surface_counts.{key} {expected}, got {actual!r}",
        )
    return expected


def _surface_count(payload: dict[str, Any], *, name: str, key: str) -> int:
    surface_counts = payload.get("surface_counts")
    if not isinstance(surface_counts, dict):
        raise SmokeCheckError(f"{name}: missing surface_counts object")
    actual = surface_counts.get(key)
    if not isinstance(actual, int) or isinstance(actual, bool) or actual < 0:
        raise SmokeCheckError(
            f"{name}: expected nonnegative integer surface_counts.{key}, got {actual!r}",
        )
    return actual


def check_smoke_outputs(smoke_out: Path) -> dict[str, Any]:
    hello = _read_text(smoke_out / "hello.txt")
    if not hello.splitlines()[0].startswith("Microcosm first screen"):
        raise SmokeCheckError("hello.txt: first line must start with Microcosm first screen")

    version = _read_text(smoke_out / "version.txt")
    if not version.startswith("microcosm "):
        raise SmokeCheckError(f"version.txt: expected microcosm version line, got {version!r}")

    first_screen = _read_json(smoke_out / "first-screen-card.json")
    tour = _read_json(smoke_out / "tour-card.json")
    status = _read_json(smoke_out / "status-card.json")
    served_status = _read_json(smoke_out / "served-status-card.json")
    authority = _read_json(smoke_out / "authority-card.json")
    workingness = _read_json(smoke_out / "workingness-card.json")
    legibility = _read_json(smoke_out / "legibility-scorecard.json")
    stripping_guard = _read_json(smoke_out / "stripping-guard.json")

    for name, payload in (
        ("first-screen-card.json", first_screen),
        ("tour-card.json", tour),
        ("status-card.json", status),
        ("served-status-card.json", served_status),
        ("authority-card.json", authority),
        ("workingness-card.json", workingness),
        ("legibility-scorecard.json", legibility),
        ("stripping-guard.json", stripping_guard),
    ):
        _expect_status(payload, name=name)

    if tour.get("card_status") != "clear":
        raise SmokeCheckError(
            f"tour-card.json: expected card_status 'clear', got {tour.get('card_status')!r}",
        )
    if workingness.get("card_status") != "clear":
        raise SmokeCheckError(
            "workingness-card.json: expected card_status 'clear', "
            f"got {workingness.get('card_status')!r}",
        )

    private_path_hit_count = _expect_nonnegative_int(
        served_status,
        name="served-status-card.json",
        key="private_path_hit_count",
    )
    if private_path_hit_count != 0:
        raise SmokeCheckError(
            "served-status-card.json: expected zero private path hits, "
            f"got {private_path_hit_count}",
        )
    _expect_false(
        served_status,
        name="served-status-card.json",
        key="release_authorized",
    )
    _expect_false(
        served_status,
        name="served-status-card.json",
        key="provider_calls_authorized",
    )

    authority_organ_count = _expect_positive_surface_count(
        authority,
        name="authority-card.json",
        key="organ_authority_count",
    )
    _expect_false(
        authority,
        name="authority-card.json",
        key="unsafe_payload_bodies_exported",
    )
    _expect_authority_false(
        authority,
        name="authority-card.json",
        key="release_authorized",
    )

    mapped_organ_count = _surface_count(
        workingness,
        name="workingness-card.json",
        key="mapped_organ_count",
    )
    _expect_surface_count(
        workingness,
        name="workingness-card.json",
        key="missing_standard_count",
        expected=0,
    )
    _expect_surface_count(
        workingness,
        name="workingness-card.json",
        key="missing_failure_modes_count",
        expected=0,
    )
    _expect_authority_false(
        workingness,
        name="workingness-card.json",
        key="release_authorized",
    )

    _expect_false(
        legibility,
        name="legibility-scorecard.json",
        key="release_authorized",
    )
    _expect_false(
        legibility,
        name="legibility-scorecard.json",
        key="unsafe_payload_bodies_in_receipt",
    )
    _expect_false(
        stripping_guard,
        name="stripping-guard.json",
        key="release_authorized",
    )
    _expect_false(
        stripping_guard,
        name="stripping-guard.json",
        key="unsafe_payload_bodies_in_receipt",
    )

    return {
        "status": "pass",
        "smoke_out": str(smoke_out),
        "version": version,
        "authority_organ_count": authority_organ_count,
        "workingness_card_status": workingness["card_status"],
        "mapped_organ_count": mapped_organ_count,
        "missing_standard_count": 0,
        "missing_failure_modes_count": 0,
        "private_path_hit_count": private_path_hit_count,
    }


def print_summary(summary: dict[str, Any]) -> None:
    print("Microcosm smoke check: pass")
    print(f"receipts: {summary['smoke_out']}")
    print(
        "authority: pass "
        f"({summary['authority_organ_count']} organ authority rows, release false)",
    )
    print(
        "workingness: "
        f"{summary['workingness_card_status']} "
        f"({summary['mapped_organ_count']} mapped, "
        f"{summary['missing_standard_count']} missing standards, "
        f"{summary['missing_failure_modes_count']} missing failure modes)",
    )
    print(
        "served status: pass "
        f"({summary['private_path_hit_count']} private path hits)",
    )
    print(f"version: {summary['version']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Microcosm smoke receipts and print a compact pass summary.",
    )
    parser.add_argument(
        "--smoke-out",
        default=".microcosm/smoke",
        help="Directory containing smoke receipts written by make smoke.",
    )
    args = parser.parse_args(argv)

    try:
        summary = check_smoke_outputs(Path(args.smoke_out))
    except SmokeCheckError as exc:
        print("Microcosm smoke check: fail", file=sys.stderr)
        print(f"reason: {exc}", file=sys.stderr)
        return 1
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
