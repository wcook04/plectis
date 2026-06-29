"""Mechanism-fidelity comprehension lane.

Guards the fix for projection-induced under-reading: a cold agent must be able to read
what each organ actually computes / verifies / rejects -- not the lossy one-line atlas
gloss -- across every organ in one pass. Earned 2026-06-29 after a frontier agent
under-read the finance (Diebold-Mariano / Hansen SPA) and Erdos (ord_Q(b)=lcm(F)) organs
from their short glosses.
"""
from __future__ import annotations

from microcosm_core import comprehension as C


def _real_inputs() -> dict:
    return C.load_inputs()


def test_mechanism_index_ladder_and_fallback() -> None:
    """The precedence join is deterministic: card -> statement -> gloss."""
    atlas_by = {
        "card_organ": {"agent_gloss": "short gloss A", "claim_ceiling_restated": "no X"},
        "stmt_organ": {"agent_gloss": "short gloss B", "claim_ceiling_restated": "no Y"},
        "gloss_organ": {"agent_gloss": "G" * 200, "claim_ceiling_restated": "no Z"},
    }
    capsules = {
        "paper_modules": [
            {
                "compression": {
                    "card": "C" * 150,
                    "one_line": "card organ one line",
                    "authority_ceiling": "card ceiling",
                },
                "subjects": [{"kind": "organ", "ref": "card_organ"}],
            }
        ]
    }
    mechanisms = {
        "mechanisms": [
            {"statement": "stmt organ computes a thing exactly", "runs_in": ["stmt_organ"]}
        ]
    }
    idx = C._mechanism_index(capsules, mechanisms, atlas_by)
    # card rung wins when card >= 120 chars; line + ceiling come from the capsule.
    assert idx["card_organ"]["body"] == "C" * 150
    assert idx["card_organ"]["line"] == "card organ one line"
    assert idx["card_organ"]["ceiling"] == "card ceiling"
    # statement rung when no card; ceiling falls back to the atlas claim ceiling.
    assert idx["stmt_organ"]["body"] == "stmt organ computes a thing exactly"
    assert idx["stmt_organ"]["ceiling"] == "no Y"
    # gloss rung when neither card nor statement is present.
    assert idx["gloss_organ"]["body"] == "G" * 200


def test_all_organs_resolve_a_mechanism_shard() -> None:
    inputs = _real_inputs()
    atlas_by = inputs["atlas_by_organ"]
    mech_by = inputs["mechanism_by_organ"]
    assert len(atlas_by) >= 80
    missing = [oid for oid in atlas_by if not (mech_by.get(oid) or {}).get("line")]
    assert not missing, f"organs with no mechanism line: {missing}"
    thin = [oid for oid in atlas_by if len((mech_by.get(oid) or {}).get("body", "")) < 120]
    assert not thin, f"organs with a sub-120-char mechanism body: {thin}"


def test_high_regret_organs_name_their_machinery() -> None:
    """The organs a sampling agent mis-judged must name their real machinery."""
    mech_by = _real_inputs()["mechanism_by_organ"]

    def body(oid: str) -> str:
        return (mech_by.get(oid) or {}).get("body", "")

    fin = body("finance_forecast_evaluation_spine")
    assert "Diebold-Mariano" in fin and ("Hansen" in fin or "SPA" in fin)
    erd = body("finite_erdos_denominator_certificate_strike")
    assert "ord_Q" in erd and "lcm" in erd
    sab = body("agent_sabotage_scheming_monitor_replay")
    assert "counterfactual" in sab or "monitor" in sab
    assert "RMS" in body("batch8_audio_level_rms_port")


def test_mechanism_surfaces_do_not_leak_source_bodies() -> None:
    inputs = _real_inputs()
    assert not C._pack_leaks_source_body(C.comprehend(mode="mechanism", inputs=inputs))
    sm = C.comprehend(mode="self-model", target="whole_substrate_map", inputs=inputs)
    assert not C._pack_leaks_source_body(sm)


def test_comprehend_organ_carries_full_mechanism_body() -> None:
    inputs = _real_inputs()
    pack = C.comprehend(
        mode="organ", organ_id="finance_forecast_evaluation_spine", inputs=inputs
    )
    assert pack.get("found")
    assert "Diebold-Mariano" in pack["summary"].get("mechanism", "")


def test_whole_substrate_map_rows_carry_mechanism() -> None:
    pack = C.comprehend(
        mode="self-model", target="whole_substrate_map", inputs=_real_inputs()
    )
    organs = [o for fam in (pack.get("whole_substrate_map") or []) for o in fam["organs"]]
    assert organs
    assert all(o.get("mechanism") for o in organs), "whole_substrate_map row missing mechanism"


def test_slice_mechanism_lists_every_organ() -> None:
    pack = C.comprehend(mode="mechanism", inputs=_real_inputs())
    nodes = pack.get("selected_nodes") or []
    assert len(nodes) >= 80
    assert all(n.get("mechanism") for n in nodes)
