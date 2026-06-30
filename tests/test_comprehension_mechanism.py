"""Mechanism-fidelity comprehension lane.

Guards the fix for projection-induced under-reading: a cold agent must be able to read
what each organ actually computes / verifies / rejects -- not the lossy one-line atlas
gloss -- across every organ in one pass. Earned 2026-06-29 after a frontier agent
under-read the finance (Diebold-Mariano / Hansen SPA) and Erdos (ord_Q(b)=lcm(F)) organs
from their short glosses.
"""
from __future__ import annotations

import re

from microcosm_core import comprehension as C
from microcosm_core import cli


def _real_inputs() -> dict:
    return C.load_inputs()


# Internal claim-boundary vocabulary that the public-scope scrub (_public_scope_text)
# rewrites before these registries reach any reader surface (ORGANS.md / organ_atlas
# already scrub the same card/one_line/authority_ceiling fields). The mechanism slice
# is a public reader surface over the SAME two registries, so it must carry the scrubbed
# phrasing, not the raw source phrasing. Each token below is verified absent after the
# scrub; a hit means the projection stopped routing through _public_scope_text or a new
# raw term slipped past the substitution table.
_INTERNAL_JARGON = (
    re.compile(r"\bprivate[ -]root\b", re.IGNORECASE),
    re.compile(r"\braw[ -]seed\b", re.IGNORECASE),
    re.compile(r"\braw operator voice\b", re.IGNORECASE),
    re.compile(r"\brelease\b", re.IGNORECASE),
    re.compile(r"\bpublication\b", re.IGNORECASE),
    re.compile(r"\bprovider dispatch\b", re.IGNORECASE),
)


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
    assert [n["organ_id"] for n in pack.get("substance_nodes", [])] == [
        "lean_proof_search_lab_runtime",
        "finite_erdos_denominator_certificate_strike",
        "agent_sabotage_scheming_monitor_replay",
        "finance_forecast_evaluation_spine",
        "generated_projection_drift_runtime",
    ]


def test_slice_mechanism_text_renders_substance_lines() -> None:
    pack = C.comprehend(mode="mechanism", inputs=_real_inputs())
    text = cli._render_comprehend_card(pack)

    assert "Mechanism substance examples:" in text
    assert "Mechanism lines:" in text
    assert text.index("Mechanism substance examples:") < text.index("Mechanism lines:")
    assert "Lean Proof-Search Lab Runtime" in text
    assert "Gated external-tool proof-search lab" in text
    assert "Finite Erdos Denominator-Order Certificate Strike" in text
    assert "ord_Q(b)=lcm(F)" in text
    assert "Sabotage-Monitor Contract Replay" in text
    assert "What this does NOT claim:" in text


def test_mechanism_shards_carry_no_raw_claim_boundary_jargon() -> None:
    """The mechanism projection must match the scrubbed public reader surfaces.

    The capsule/mechanism registries carry raw internal claim-boundary vocabulary
    (private-root, raw-seed, raw operator voice, release/publication/provider
    dispatch). Every other public projection of these registries softens that prose
    through ``_public_scope_text``; the mechanism slice (added 2026-06-29) is the
    surface that historically bypassed it. This guard fails if the routing is removed.
    """
    mech_by = _real_inputs()["mechanism_by_organ"]
    violations = []
    for oid, shard in mech_by.items():
        blob = " ".join(str(shard.get(f, "")) for f in ("line", "body", "ceiling"))
        for pat in _INTERNAL_JARGON:
            if pat.search(blob):
                violations.append(f"  {oid}: {pat.pattern} -> ...{pat.search(blob).group()}...")
    assert not violations, (
        "mechanism shards leak raw claim-boundary jargon instead of the public-scope "
        "scrubbed phrasing every other reader surface carries -- ensure _mechanism_index "
        "routes line/body/ceiling through _public_scope_text:\n" + "\n".join(violations)
    )


def test_mechanism_reader_surfaces_are_public_scope_scrubbed() -> None:
    """End-to-end: the rendered registry-derived mechanism fields are scrubbed too.

    Only the fields projected from the two registries are checked -- the pack's own
    hardcoded scaffolding prose (non_goals, what_not_to_trust) legitimately keeps
    'release'/'publication' and is not a registry projection.
    """
    inputs = _real_inputs()
    # mechanism slice: each node carries a registry-derived mechanism line + ceiling.
    slice_pack = C.comprehend(mode="mechanism", inputs=inputs)
    rendered = [
        f"{n.get('mechanism', '')} {n.get('claim_ceiling', '')}"
        for n in slice_pack.get("selected_nodes") or []
    ]
    # whole_substrate_map: each organ row carries a budget-safe mechanism line.
    sm_pack = C.comprehend(mode="self-model", target="whole_substrate_map", inputs=inputs)
    rendered += [
        str(o.get("mechanism", ""))
        for fam in sm_pack.get("whole_substrate_map") or []
        for o in fam.get("organs") or []
    ]
    # per-organ pack: summary.mechanism carries the full registry-derived body.
    organ_pack = C.comprehend(
        mode="organ", organ_id="batch4_proof_authority_runtime", inputs=inputs
    )
    rendered.append(str(organ_pack["summary"].get("mechanism", "")))

    assert len(rendered) >= 80
    for text in rendered:
        for pat in _INTERNAL_JARGON:
            hit = pat.search(text)
            assert hit is None, f"reader surface leaks raw jargon {pat.pattern!r}: {text!r}"


def test_assessment_goals_route_to_mechanism_without_hijacking_named_systems() -> None:
    """Whole-substrate impression goals must enter the mechanism lane first.

    The classifier is deliberately narrower than "evaluate": named-system goals such
    as the finance forecasting demo still need the organ/task route, while "is
    finance thin?" is an assessment of the family/component set and must open the
    mechanism slice before judgement.
    """
    inputs = _real_inputs()
    for goal in (
        "how impressive is Plectis?",
        "what do the components actually do?",
        "is finance thin?",
        "what do all organs do?",
        "evaluate component quality",
    ):
        mode, target, note = C.route_goal(goal, inputs)
        assert (mode, target, note) == (
            "mechanism",
            None,
            "assessment_requires_mechanism_slice",
        )
        contract = C.compile_first_action(inputs, inputs["root"], goal)
        assert contract["routing"]["basis"] == "mechanism_assessment_goal"
        assert contract["routing"]["packet_id"] == "mechanism_index"
        assert contract["first_action"]["action_kind"] == "open_packet"
        assert "--slice mechanism" in contract["first_action"]["command"]
        assert "what each organ computes" in contract["reading_boundary"]["stop_condition"]

    finance = C.compile_first_action(
        inputs, inputs["root"], "How do I evaluate the finance forecasting system?"
    )
    assert finance["owner"]["organ_id"] == "finance_forecast_evaluation_spine"
    assert finance["routing"]["basis"] == "task_class_route_match"
    assert "finance-forecast-evaluation-spine" in finance["first_action"]["command"]


def test_authority_and_self_model_carry_public_front_door_claim() -> None:
    """The source-body-free packets must not underclaim Plectis as a local router.

    README is the human front door, but coding agents often start from
    ``comprehend --self-model`` or ``--slice authority``. Those packets need the
    same mechanism-first identity and ceiling grammar so the agent sees the
    product, evidence discipline, and boundary in one pass.
    """
    inputs = _real_inputs()
    expected = C.public_cross_section_claim(88)

    authority = C.comprehend(mode="authority", inputs=inputs)
    assert expected in authority["summary"]["what_this_is"]
    assert any(
        "plectis comprehend --slice mechanism" in route
        for route in authority["summary"]["what_to_inspect_next"]
    )
    claim_node = next(
        node
        for node in authority["selected_nodes"]
        if node["kind"] == "public_claim_ceiling"
    )
    assert expected in claim_node["what_is_here"]
    assert "bounded public replays" in claim_node["what_backs_it"]
    assert "No hosted service" in authority["do_not_claim"]
    rendered_authority = cli._render_comprehend_card(authority)
    assert expected in rendered_authority
    assert "No hosted service" in rendered_authority

    self_model = C.comprehend(mode="self-model", inputs=inputs)
    first_lines = self_model["read_me_first"]
    assert first_lines[0] == expected
    assert "mechanisms -> evidence discipline -> local runtime" in " ".join(first_lines[:3])
    assert "--slice mechanism" in " ".join(first_lines[:4])
    assert "Microcosm is a" not in " ".join(first_lines[:4])
    rendered_self_model = cli._render_comprehend_card(self_model)
    assert expected in rendered_self_model
    assert "No hosted service" in rendered_self_model
