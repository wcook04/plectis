from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from microcosm_core import cli
from microcosm_core.hypothesis_handoff import (
    AUTHORITY_POSTURE,
    EXPERT_RETURN_AUTHORITY,
    LANDING_ORDER,
    SCHEMA,
    STATUS_CHANGE_RULE,
    compile_packet,
    load_and_compile,
    validate_packet,
)


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/hypothesis_handoff/independent_evaluation.json"


def example_packet() -> dict:
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def test_worked_packet_is_valid_and_advisory() -> None:
    packet = example_packet()
    assert packet["schema"] == SCHEMA
    assert packet["authority_posture"] == AUTHORITY_POSTURE
    assert packet["expert_return"]["authority_posture"] == EXPERT_RETURN_AUTHORITY
    assert packet["expert_return"]["status_change_rule"] == STATUS_CHANGE_RULE
    assert packet["expert_return"]["landing_order"] == LANDING_ORDER
    assert validate_packet(packet) == []

    card = compile_packet(packet, source=str(EXAMPLE))
    assert card["status"] == "pass"
    assert card["ready_for_expert"] is True
    assert "does not establish truth" in card["authority_ceiling"]
    assert card["leading_hypothesis"]["confidence"] == "tentative"
    assert len(card["alternatives"]) == 2
    assert len(card["discriminating_evidence"]) == 2
    for target in packet["expert_return"]["landing_targets"]:
        assert (ROOT / target["path"]).is_file()


@pytest.mark.parametrize(
    ("mutate", "expected_error"),
    [
        (
            lambda packet: packet["leading_hypothesis"].update(
                {"confidence": "certain"}
            ),
            "confidence must be tentative",
        ),
        (
            lambda packet: packet["alternatives"][0].update(
                {"distinguished_by": ["discriminator.missing"]}
            ),
            "has unknown ids",
        ),
        (
            lambda packet: packet["leading_hypothesis"].update(
                {"evidence_against_or_missing": []}
            ),
            "must be a nonempty list",
        ),
        (
            lambda packet: packet["expert_return"].update(
                {"status_change_rule": "An expert answer immediately proves the claim."}
            ),
            "permits automatic promotion",
        ),
        (
            lambda packet: packet["discriminating_evidence"][0].update(
                {"result_map": packet["discriminating_evidence"][0]["result_map"][:1]}
            ),
            "needs at least two outcomes",
        ),
        (
            lambda packet: packet["discriminating_evidence"][0]["result_map"][
                0
            ].update({"supports_hypothesis_ids": ["hypothesis.missing"]}),
            "has unknown ids",
        ),
        (
            lambda packet: packet["expert_return"]["landing_targets"][0].update(
                {"path": "../private/evidence.json"}
            ),
            "safe repository-relative path",
        ),
    ],
)
def test_validator_rejects_authority_and_discrimination_gaps(
    mutate,
    expected_error: str,
) -> None:
    packet = copy.deepcopy(example_packet())
    mutate(packet)
    assert any(expected_error in error for error in validate_packet(packet))


def test_cli_json_and_text_are_read_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    before = EXAMPLE.read_bytes()
    assert (
        cli.main(
            [
                "hypothesis-handoff",
                "--input",
                str(EXAMPLE),
                "--format",
                "json",
            ]
        )
        == 0
    )
    card = json.loads(capsys.readouterr().out)
    assert card["status"] == "pass"
    assert card["ready_for_expert"] is True

    assert (
        cli.main(
            [
                "hypothesis-handoff",
                "--input",
                str(EXAMPLE),
                "--format",
                "text",
            ]
        )
        == 0
    )
    text = capsys.readouterr().out
    assert "Working lead — tentative; not a claim or probability:" in text
    assert "bearing: Selection can hide difficult" in text
    assert "ceiling: One repaired defect does not estimate" in text
    assert "Plausible alternatives:" in text
    assert "Evidence that would distinguish them:" in text
    assert "[supports: hypothesis.independent_cases_find_more_failures]" in text
    assert "Decisive returns if verified:" in text
    assert "Useful but route-only returns:" in text
    assert "Checked landing targets:" in text
    assert "Checked landing order:" in text
    assert "Required validation:" in text
    assert "No claim status changes" in text
    assert EXAMPLE.read_bytes() == before


def test_missing_or_malformed_input_fails_as_data(tmp_path: Path) -> None:
    missing = load_and_compile(tmp_path / "missing.json")
    assert missing["status"] == "fail"
    assert missing["ready_for_expert"] is False
    assert any("FileNotFoundError" in error for error in missing["errors"])

    malformed_path = tmp_path / "malformed.json"
    malformed_path.write_text("{", encoding="utf-8")
    malformed = load_and_compile(malformed_path)
    assert malformed["status"] == "fail"
    assert any("JSONDecodeError" in error for error in malformed["errors"])

    non_utf8_path = tmp_path / "non-utf8.json"
    non_utf8_path.write_bytes(b"\xff")
    non_utf8 = load_and_compile(non_utf8_path)
    assert non_utf8["status"] == "fail"
    assert any("UnicodeDecodeError" in error for error in non_utf8["errors"])
