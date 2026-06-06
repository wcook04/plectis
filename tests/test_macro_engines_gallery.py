from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from microcosm_core import cli
from microcosm_core import macro_engines_gallery
from microcosm_core.macro_engines_gallery import RECEIPT_NAME, run


def test_macro_engines_gallery_discovers_macro_cards_and_runs_probe_pair(
    tmp_path: Path,
) -> None:
    result = run(tmp_path / "macro_engines_gallery")

    assert result["status"] == "pass"
    assert result["batch7_visible"] is True
    assert result["batch9_visible"] is True
    assert result["earlier_macro_probe_visible"] is True
    assert "batch7_macro_engines_capsule" in result["probe_ids"]
    assert "batch9_macro_engines_capsule" in result["probe_ids"]
    assert "engine_room_demo" in result["probe_ids"]
    assert result["gallery_card_count"] >= 5
    assert result["copied_source_digest_summary"]["pass_count"] >= 3
    assert result["authority_ceiling"]["release_authorized"] is False
    assert result["authority_ceiling"]["publication_authorized"] is False
    assert result["authority_ceiling"]["private_root_equivalence_claim"] is False

    probes_by_id = {row["organ_id"]: row for row in result["probes"]}
    batch7 = probes_by_id["batch7_macro_engines_capsule"]
    assert batch7["status"] == "pass"
    assert batch7["source_module_count"] == 15
    assert batch7["observed_negative_case_count"] == 9
    assert batch7["missing_negative_cases"] == []

    batch9 = probes_by_id["batch9_macro_engines_capsule"]
    assert batch9["status"] == "pass"
    assert batch9["source_module_count"] == 13
    assert batch9["observed_negative_case_count"] == 13
    assert batch9["missing_negative_cases"] == []

    engine_room = probes_by_id["engine_room_demo"]
    assert engine_room["status"] == "pass"
    assert engine_room["observed_negative_case_count"] >= 1
    assert engine_room["missing_negative_cases"] == []

    cards_by_id = {row["organ_id"]: row for row in result["gallery_cards"]}
    assert cards_by_id["batch7_macro_engines_capsule"]["claim_ceiling"]
    assert cards_by_id["batch7_macro_engines_capsule"]["source_module_manifest"][
        "digest_status"
    ] == "pass"
    assert cards_by_id["batch9_macro_engines_capsule"]["claim_ceiling"]
    assert cards_by_id["batch9_macro_engines_capsule"]["source_module_manifest"][
        "digest_status"
    ] == "pass"

    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "private-root equivalence" in result["anti_claim"]
    assert (tmp_path / "macro_engines_gallery" / RECEIPT_NAME).is_file()


def test_cli_macro_engines_gallery_route(tmp_path: Path, capsys) -> None:
    status = cli.main(["macro-engines-gallery", "run", "--out", str(tmp_path / "demo")])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert status == 0
    assert payload["status"] == "pass"
    assert payload["batch7_visible"] is True
    assert payload["batch9_visible"] is True
    assert "batch7_macro_engines_capsule" in payload["probe_ids"]
    assert "batch9_macro_engines_capsule" in payload["probe_ids"]
    assert (tmp_path / "demo" / RECEIPT_NAME).is_file()


def test_macro_engines_gallery_engine_room_probe_uses_semantic_negative_without_answer_key(
    tmp_path: Path,
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_run(input_path: Path, out_dir: Path, command: str | None = None) -> dict[str, Any]:
        negative = json.loads(
            (Path(input_path) / "missing_expected_target_negative.json").read_text(
                encoding="utf-8"
            )
        )
        captured["negative"] = negative
        return {
            "status": "pass",
            "observed_negative_case_count": 1,
            "observed_negative_cases": ["missing_expected_target_negative"],
            "missing_negative_cases": [],
            "error_codes": ["ENGINE_ROOM_EXPECTED_TARGET_MISSING"],
            "source_module_manifest": {},
            "receipt_paths": [],
        }

    monkeypatch.setattr(macro_engines_gallery.engine_room_demo, "run", fake_run)

    result = macro_engines_gallery._run_engine_room(tmp_path / "unused", tmp_path / "out")

    negative = captured["negative"]
    assert "expected_error_code" not in negative
    assert "engine_room_target_that_should_not_exist" in negative["expected_jewel_targets"]
    assert result["status"] == "pass"
