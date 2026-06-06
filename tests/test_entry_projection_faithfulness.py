from __future__ import annotations

import json

from microcosm_core.validators.entry_projection_faithfulness import (
    BLOCKED,
    PASS,
    evaluate_entry_projection_faithfulness,
    main,
)


def _atlas() -> dict[str, object]:
    return {
        "schema_version": "organ_atlas_v1",
        "organs": [
            {
                "organ_id": "pattern_binding_contract",
                "display_name": "Pattern Binding Contract",
                "human_gloss": "It checks that each declared pattern is properly hooked up.",
                "agent_gloss": "An agent runs it to validate public pattern rows.",
                "first_command": "microcosm pattern-route-readiness validate-bundle",
                "claim_ceiling_restated": "It validates only the public pattern contract.",
            }
        ],
    }


def test_blocks_projection_that_names_organ_but_suppresses_rich_card_fields() -> None:
    projection = {
        "components": [
            {
                "public_label": "Pattern Binding Contract",
                "specialty": ["architecture", "navigation", "rules"],
            }
        ]
    }

    card = evaluate_entry_projection_faithfulness(
        _atlas(),
        [("site_component_rows.json", projection)],
    )

    assert card["status"] == BLOCKED
    assert card["under_projected_count"] == 1
    finding = card["under_projected_rows"][0]
    assert finding["error_code"] == "rich_card_suppressed_by_projection"
    assert finding["organ_ids"] == ["pattern_binding_contract"]
    assert finding["has_first_command"] is False
    assert finding["has_authority_ceiling"] is False
    assert finding["has_rich_card_route"] is False
    assert "core/organ_atlas.json" in finding["owner_surface_mutation_guidance"]


def test_allows_compressed_route_when_command_ceiling_and_card_route_survive() -> None:
    projection = {
        "routes": [
            {
                "task_class": "architecture",
                "primary_display_name": "Pattern Binding Contract",
                "primary_organ_id": "pattern_binding_contract",
                "first_command": "microcosm pattern-route-readiness validate-bundle",
                "authority_boundary": "routing card only",
                "drilldown_target": "ORGANS.md#pattern-binding-contract",
            }
        ]
    }

    card = evaluate_entry_projection_faithfulness(
        _atlas(),
        [("agent_task_routes.json", projection)],
    )

    assert card["status"] == PASS
    assert card["projection_rows"][0]["projection_mode"] == "compressed_route_to_rich_card"
    assert card["under_projected_rows"] == []


def test_allows_inline_rich_projection() -> None:
    projection = {
        "components": [
            {
                "organ_id": "pattern_binding_contract",
                "human_gloss": "It checks that each declared pattern is properly hooked up.",
                "first_command": "microcosm pattern-route-readiness validate-bundle",
            }
        ]
    }

    card = evaluate_entry_projection_faithfulness(
        _atlas(),
        [("rich_component_rows.json", projection)],
    )

    assert card["status"] == PASS
    assert card["projection_rows"][0]["projection_mode"] == "inline_rich_card"


def test_real_agent_task_routes_remain_faithful_enough() -> None:
    code = main(["--root", ".", "--check"])

    assert code == 0


def test_cli_check_returns_nonzero_for_under_projected_rows(tmp_path, capsys) -> None:
    atlas_path = tmp_path / "organ_atlas.json"
    projection_path = tmp_path / "components.json"
    atlas_path.write_text(json.dumps(_atlas()), encoding="utf-8")
    projection_path.write_text(
        json.dumps(
            {
                "components": [
                    {
                        "public_label": "Pattern Binding Contract",
                        "what": "Source-backed component.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    code = main(
        [
            "--atlas",
            str(atlas_path),
            "--projection-json",
            str(projection_path),
            "--check",
        ]
    )

    assert code == 1
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == BLOCKED
    assert output["under_projected_rows"][0]["error_code"] == (
        "rich_card_suppressed_by_projection"
    )
