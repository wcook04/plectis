"""Executable candidate proof across resolver and actual description readers."""
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from microcosm_core.component_descriptions import (
    ComponentDescriptionError, enrich_description_atlas, enrich_organ_route_rows,
    load_description_atlas, resolve_component_capsules,
)
from microcosm_core import comprehension, doctrine_lattice, first_screen_composition
from microcosm_core.projections import (
    organ_atlas, agent_entry_composition, concept_mechanism_read_model,
    organ_discoverability_matrix,
)
from microcosm_core.validators import entry_projection_faithfulness

HERE = Path(__file__).resolve().parents[1]
LIVE = HERE
INDEX_CANDIDATE = HERE
SCRIPT = HERE / 'scripts/build/build_code_lens_join_index.py'
spec = importlib.util.spec_from_file_location('candidate_code_lens', SCRIPT)
code_lens = importlib.util.module_from_spec(spec)
spec.loader.exec_module(code_lens)
CARD = 'Counts fixture routes; it does not authorize release.'
LINE = 'Count fixture routes.'
CEILING = 'No release authority; fixture routes only.'
NORMATIVE = 'Registry contract assertion remains independently normative.'
STALE = 'STALE_PERMISSIVE_DESCRIPTION_guarantees_correctness'


def write(root, ref, payload):
    path = root / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + '\n')


def source_pair():
    return ({'schema_version': 'organ_atlas_v1', 'organs': [{
        'organ_id': 'foo', 'display_name': 'Foo Routes', 'family': 'fixture_family',
        'specialty': ['routing'], 'first_command': 'microcosm foo --card',
        'paper_module_ref': 'paper_modules/foo.md', 'wiring_note': 'Explicit fixture wiring.',
        'wires_to': [], 'mechanism_refs': [], 'code_loci': [],
        'human_gloss': STALE, 'agent_gloss': STALE, 'claim_ceiling_restated': STALE,
    }]}, {'paper_modules': [{
        'id': 'paper_module.foo', 'legacy_markdown_projection': 'paper_modules/foo.md',
        'subjects': [{'kind': 'organ', 'ref': 'foo'}],
        'compression': {'card': CARD, 'one_line': LINE, 'authority_ceiling': CEILING},
    }]})


@pytest.fixture
def root(tmp_path):
    atlas, capsules = source_pair()
    write(tmp_path, 'core/organ_atlas.json', atlas)
    write(tmp_path, 'core/paper_module_capsules.json', capsules)
    write(tmp_path, 'core/organ_registry.json', {'implemented_organs': [{
        'organ_id': 'foo', 'status': 'accepted_current_authority',
        'claim_ceiling': NORMATIVE, 'runner': 'microcosm_core.organs.foo',
        'evidence_class': 'fixture_replay', 'validator_command': 'microcosm foo --card',
        'generated_receipts': [],
    }]})
    write(tmp_path, organ_atlas.FAMILIES_REL, {'families': [{
        'family_id': 'fixture_family', 'label': 'Fixture family', 'organ_ids': ['foo'],
    }]})
    write(tmp_path, organ_atlas.EVIDENCE_CLASSES_REL, {'organ_evidence_classes': [{
        'organ_id': 'foo', 'evidence_class': 'fixture_replay',
    }]})
    write(tmp_path, organ_atlas.KERNEL_REL, {'primitives': []})
    write(tmp_path, 'core/standards_registry.json', {'standards': []})
    write(tmp_path, 'atlas/entry_packet.json', {})
    write(tmp_path, 'atlas/agent_task_routes.json', {'routes': [{
        'task_class': 'agent-entry', 'primary_organ_id': 'foo',
        'first_command': 'microcosm foo --card',
        'relevant_organs': [{'organ_id': 'foo', 'claim_ceiling_restated': STALE}],
    }], 'organ_glance_ladder': [{'family_id': 'fixture_family', 'organs': [{
        'organ_id': 'foo', 'display_name': 'Foo Routes', 'family': 'fixture_family',
        'one_line': STALE, 'card': STALE, 'authority_ceiling': STALE,
        'claim_ceiling_restated': STALE, 'capsule_id': 'wrong',
        'capsule_join_status': 'wrong', 'first_command': 'microcosm foo --card',
    }]}]})
    (tmp_path / 'paper_modules').mkdir()
    (tmp_path / 'paper_modules/foo.md').write_text('# Foo\n')
    (tmp_path / 'src/microcosm_core').mkdir(parents=True)
    (tmp_path / 'src/microcosm_core/cli.py').write_text('def parser(subparsers):\n    subparsers.add_parser("foo")\n')
    return tmp_path


def test_compatibility_preserves_structure_and_does_not_mutate_inputs():
    atlas, capsules = source_pair()
    originals = deepcopy((atlas, capsules))
    enriched = enrich_description_atlas(atlas, capsules)
    row = enriched['organs'][0]
    assert row['human_gloss'] == row['agent_gloss'] == row['card'] == CARD
    assert row['claim_ceiling_restated'] == row['authority_ceiling'] == CEILING
    assert row['one_line'] == LINE
    for key in ('organ_id', 'display_name', 'family', 'specialty', 'first_command', 'wires_to', 'paper_module_ref', 'wiring_note'):
        assert row[key] == atlas['organs'][0][key]
    assert row['description_source_ref'] == 'core/paper_module_capsules.json#paper_module.foo'
    assert row['description_source_fields']['agent_gloss'] == 'compression.card'
    assert (atlas, capsules) == originals
    row['specialty'].append('cannot mutate source')
    assert (atlas, capsules) == originals


def test_88_actual_primary_bindings_seven_bridges_and_two_explicit_subject_omissions():
    atlas = json.loads((LIVE / 'core/organ_atlas.json').read_text())
    capsules = json.loads((LIVE / 'core/paper_module_capsules.json').read_text())
    result = enrich_description_atlas(atlas, capsules)
    rows = {row['organ_id']: row for row in result['organs']}
    assert len(rows) == 88
    assert Counter(row['capsule_join_status'] for row in rows.values()) == {'direct': 81, 'paper_module_ref_bridge': 7}
    bridges = {
        'mathematical_strategy_atlas_hypothesis_scorer': 'paper_module.mathematical_strategy_atlas',
        'tactic_portfolio_availability_probe': 'paper_module.tactic_portfolio_availability',
        'target_shape_tactic_routing_gate': 'paper_module.target_shape_tactic_routing',
        'undeclared_library_prior_symbol_classifier': 'paper_module.undeclared_library_prior_classifier',
        'ring2_premise_retrieval_precision_recall_harness': 'paper_module.ring2_premise_precision_recall',
        'provider_context_recipe_budget_policy': 'paper_module.provider_context_recipe_budget',
        'pattern_assimilation_step': 'paper_module.pattern_assimilation',
    }
    assert {oid: row['capsule_id'] for oid, row in rows.items() if row['capsule_join_status'] == 'paper_module_ref_bridge'} == bridges
    assert {oid for oid, row in rows.items() if row['capsule_subject_status'] == 'explicit_ref_subject_unrecorded'} == {
        'batch7_oracle_sibling_capsule', 'batch7_demo_take_console_capsule',
    }
    assert all(row['description_join_ref'] == atlas_row['paper_module_ref'] for row, atlas_row in zip(result['organs'], atlas['organs']))


def test_actual_canonical_cards_pass_description_validation_with_source_norms_preserved(root):
    for ref in ('core/organ_atlas.json', 'core/paper_module_capsules.json', 'core/organ_registry.json',
                organ_atlas.FAMILIES_REL, organ_atlas.EVIDENCE_CLASSES_REL, organ_atlas.KERNEL_REL):
        data = (LIVE / ref).read_bytes()
        path = root/ref; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        assert hashlib.sha256(path.read_bytes()).digest() == hashlib.sha256(data).digest()
    model = organ_atlas.load_model(root)
    assert model['coverage']['registry_organ_count'] == 88
    assert model['coverage']['overclaim_cards'] == []
    assert model['coverage']['ceiling_without_negation'] == []
    assert model['coverage']['empty_gloss_fields'] == []
    assert model['coverage']['capsule_join_status_counts'] == {'direct': 81, 'paper_module_ref_bridge': 7}
    registry = json.loads((root/'core/organ_registry.json').read_text())
    normative = {row['organ_id']: row['claim_ceiling'] for row in registry['implemented_organs'] if row['status'] == 'accepted_current_authority'}
    for family in model['families']:
        for row in family['cards']:
            assert row['claim_ceiling'] == normative[row['organ_id']]
            assert row['human_gloss'] == row['agent_gloss'] == row['compression_card']




@pytest.mark.parametrize('field', ['one_line', 'card', 'authority_ceiling'])
def test_missing_or_blank_compression_blocks(field):
    atlas, capsules = source_pair()
    capsules['paper_modules'][0]['compression'][field] = '  '
    with pytest.raises(ComponentDescriptionError, match='missing_capsule_compression'):
        enrich_description_atlas(atlas, capsules)


@pytest.mark.parametrize('mode', ['duplicate_id', 'duplicate_guide', 'contradictory_subject', 'unknown_explicit', 'fragment_on_other_file', 'missing_capsule', 'duplicate_atlas'])
def test_invalid_sources_never_fall_back_to_stale_gloss(mode):
    atlas, capsules = source_pair()
    if mode == 'duplicate_id':
        capsules['paper_modules'].append(deepcopy(capsules['paper_modules'][0]))
    elif mode == 'duplicate_guide':
        other = deepcopy(capsules['paper_modules'][0]); other['id'] = 'paper_module.other'
        capsules['paper_modules'].append(other)
    elif mode == 'contradictory_subject':
        capsules['paper_modules'][0]['subjects'] = [{'kind': 'organ', 'ref': 'other'}]
    elif mode == 'unknown_explicit':
        atlas['organs'][0]['paper_module_ref'] = 'paper_modules/missing.md'
    elif mode == 'fragment_on_other_file':
        atlas['organs'][0]['paper_module_ref'] = 'core/not_capsules.json#paper_module.foo'
    elif mode == 'missing_capsule':
        capsules['paper_modules'] = []
    elif mode == 'duplicate_atlas':
        atlas['organs'].append(deepcopy(atlas['organs'][0]))
    with pytest.raises(ComponentDescriptionError):
        enrich_description_atlas(atlas, capsules)


def test_ambiguous_unreferenced_subject_blocks_but_explicit_primary_resolves():
    atlas, capsules = source_pair()
    other = deepcopy(capsules['paper_modules'][0])
    other.update(id='paper_module.other', legacy_markdown_projection='paper_modules/other.md')
    capsules['paper_modules'].append(other)
    assert resolve_component_capsules(atlas['organs'], capsules['paper_modules'])['foo'][0]['id'] == 'paper_module.foo'
    atlas['organs'][0].pop('paper_module_ref')
    with pytest.raises(ComponentDescriptionError, match='ambiguous_organ_capsule'):
        resolve_component_capsules(atlas['organs'], capsules['paper_modules'])


def test_missing_canonical_file_blocks_every_file_reader(root):
    (root / 'core/paper_module_capsules.json').unlink()
    for read in (load_description_atlas, comprehension.load_inputs,
                 doctrine_lattice._atlas_organs, concept_mechanism_read_model._organ_atlas_by_id,
                 organ_atlas.load_model, organ_discoverability_matrix.build_organ_discoverability_matrix,
                 agent_entry_composition.build_agent_entry_composition,
                 first_screen_composition._organ_glance_ladder_rows):
        with pytest.raises(FileNotFoundError):
            read(root=root)


def test_comprehension_short_card_beats_mechanism_and_stale_text(root):
    assert len(CARD) < 120
    write(root, 'core/mechanism_sources.json', {'mechanisms': [{'runs_in': ['foo'], 'statement': STALE}]})
    write(root, 'core/component_public_synopses.json', {'synopses': {'foo': STALE}})
    inputs = comprehension.load_inputs(root)
    pack = comprehension.compile_organ(inputs, 'foo')
    assert pack['summary']['mechanism'] == organ_atlas._public_scope_text(CARD)
    assert pack['summary']['what_not_to_trust'] == CEILING
    assert pack['selected_nodes'][0]['agent_gloss'] == CARD
    assert inputs['synopsis_by_organ']['foo'] == LINE
    assert STALE not in json.dumps(pack)


def test_doctrine_real_source_and_instance_keep_normative_claim(root):
    rows = doctrine_lattice._organ_source_rows(root)
    assert rows[0]['agent_gloss'] == CARD
    assert rows[0]['registry_payload']['claim_ceiling'] == NORMATIVE
    instance = doctrine_lattice.build_organ_instance_from_source_row(rows[0], root, resolution_context={
        'standard': {}, 'paper_capsules': {}, 'known_organs': {'foo'},
    })
    assert instance['role'] == instance['statement'] == CARD
    assert instance['organ_payload']['claim_ceiling'] == CEILING
    assert instance['organ_payload']['source_registry_row']['claim_ceiling'] == NORMATIVE
    assert any(ref['path'].endswith('#paper_module.foo') for ref in instance['source_refs'])
    assert STALE not in json.dumps(instance)


def test_concept_doctrine_builder_uses_canonical_description(root):
    rows = concept_mechanism_read_model.build_organ_doctrine_rows(root)
    assert rows[0]['concept_binding']['source_gloss'] == CARD
    assert rows[0]['surface_refs']['description'].endswith('#paper_module.foo')
    assert STALE not in json.dumps(rows)


def test_discoverability_builder_uses_canonical_ceiling_and_exact_primary(root):
    matrix = organ_discoverability_matrix.build_organ_discoverability_matrix(root)
    row = matrix['rows'][0]
    assert row['authority_ceiling'] == CEILING
    assert row['paper_module']['ref'] == 'paper_modules/foo.md'
    assert STALE not in json.dumps(matrix)


def test_agent_entry_card_keeps_normative_and_descriptive_ceilings_separate(root):
    atlas = load_description_atlas(root)
    registry = json.loads((root / 'core/organ_registry.json').read_text())
    card = agent_entry_composition._organ_card(organ_id='foo', atlas_by_id={'foo': atlas['organs'][0]},
        registry_by_id={'foo': registry['implemented_organs'][0]}, evidence_by_id={}, doctrine_by_id={}, role='test')
    assert card['claim_ceiling'] == NORMATIVE
    assert card['claim_ceiling_restated'] == CEILING
    assert card['agent_gloss'] == CARD
    assert card['evidence_refs']['description'].endswith('#paper_module.foo')
    assert STALE not in json.dumps(card)


def test_generated_routes_are_refreshed_before_first_screen_and_entry_glance(root):
    rows, _ = first_screen_composition._organ_glance_ladder_rows(root)
    assert rows[0]['card'] == CARD and rows[0]['one_line'] == LINE
    routes = json.loads((root / 'atlas/agent_task_routes.json').read_text())
    refreshed = enrich_organ_route_rows(routes, load_description_atlas(root))
    glance = agent_entry_composition._accepted_organ_glance(refreshed)
    assert STALE not in json.dumps(glance)
    assert STALE in json.dumps(routes), 'reader must not mutate saved route sources'
    sample = first_screen_composition._representative_substrate_glance(root)
    assert STALE not in json.dumps(sample)
    row = routes['organ_glance_ladder'][0]['organs'][0]
    row.pop('card'); row.pop('one_line'); row['human_gloss'] = STALE
    write(root, 'atlas/agent_task_routes.json', routes)
    assert first_screen_composition._organ_glance_ladder_rows(root)[0][0]['card'] == CARD


def test_agent_entry_public_builder_uses_shared_input_view(root):
    result = agent_entry_composition.build_agent_entry_composition(root=root)
    assert STALE not in json.dumps(result)
    assert CARD in json.dumps(result)


def test_code_lens_builder_canonicalizes_before_existing_safety_screen(root):
    atlas = json.loads((root / 'core/organ_atlas.json').read_text())
    caps = json.loads((root / 'core/paper_module_capsules.json').read_text())
    registry = json.loads((root / 'core/organ_registry.json').read_text())
    lens = {'payload_boundary': {'source_bodies_exported': False}, 'symbol_capsule_rows': []}
    index = code_lens.build_join_index(lens, registry, atlas=atlas, capsules=caps)
    claim = index['nodes']['claim'][0]
    assert claim['claim_ceiling'] == NORMATIVE
    assert claim['claim_ceiling_restated'] == CEILING
    assert index['generated_from']['component_descriptions'].startswith('core/paper_module_capsules.json')
    assert STALE not in json.dumps(index)
    secret = 'sk-' + 'A' * 22
    caps['paper_modules'][0]['compression']['authority_ceiling'] = secret
    index = code_lens.build_join_index(lens, registry, atlas=atlas, capsules=caps)
    assert index['nodes']['claim'][0]['claim_ceiling_restated'] is None
    assert secret not in json.dumps(index)


def test_code_lens_explicit_description_source_is_validated_and_legacy_v2_is_preserved(capsys):
    atlas, _ = source_pair()
    # The index owner's preserved four-argument API remains v2. Explicit
    # canonical input cannot silently degrade to a stale atlas fallback.
    legacy = code_lens.build_join_index({'symbol_capsule_rows': []}, {'implemented_organs': []}, atlas=atlas)
    assert legacy['schema_version'] == 'microcosm_code_lens_join_index_v2'
    with pytest.raises(ComponentDescriptionError, match='missing_paper_module_capsules'):
        code_lens.build_join_index({'symbol_capsule_rows': []}, {'implemented_organs': []}, atlas=atlas, capsules={})
    with pytest.raises(SystemExit) as stop:
        code_lens.main(['--help'])
    assert stop.value.code == 0
    assert '--capsules' in capsys.readouterr().out


def test_file_reader_freshness_ignores_same_root_stale_atlas(root):
    before = comprehension.load_inputs(root)
    assert before['atlas_by_organ']['foo']['agent_gloss'] == CARD
    caps = json.loads((root / 'core/paper_module_capsules.json').read_text())
    caps['paper_modules'][0]['compression']['card'] = 'Updated canonical card; no live authority.'
    caps['paper_modules'][0]['compression']['authority_ceiling'] = 'No provider calls.'
    write(root, 'core/paper_module_capsules.json', caps)
    after = comprehension.load_inputs(root)
    assert after['atlas_by_organ']['foo']['agent_gloss'] == caps['paper_modules'][0]['compression']['card']
    assert doctrine_lattice._organ_source_rows(root)[0]['agent_gloss'] == caps['paper_modules'][0]['compression']['card']
    assert first_screen_composition._organ_glance_ladder_rows(root)[0][0]['card'] == caps['paper_modules'][0]['compression']['card']
    assert before['atlas_by_organ']['foo']['agent_gloss'] == CARD


def test_expected_organ_instances_do_not_cache_old_capsule_descriptions(root, monkeypatch):
    # Supply only unrelated structural resolution context; exercise the real
    # public expected-instance/source-reader/builder chain on both invocations.
    monkeypatch.setattr(doctrine_lattice, '_organ_resolution_context', lambda *args, **kw: {'standard': {}, 'known_organs': {'foo'}})
    # Preserve the final production signature's structural dependencies while
    # exercising its real capsule dependency on both calls.
    signature_refs = (*doctrine_lattice._SOURCE_PROJECTION_INPUTS['organ'],
                      *(doctrine_lattice._standard_rel(kind) for kind in doctrine_lattice.KIND_STANDARD_IDS))
    for ref in signature_refs:
        path = root / ref
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}' if path.suffix == '.json' else '# Fixture structural owner\n')
    before = doctrine_lattice.expected_organ_instances(root)
    capsules = json.loads((root/'core/paper_module_capsules.json').read_text())
    capsules['paper_modules'][0]['compression']['card'] = 'Second source version.'
    write(root, 'core/paper_module_capsules.json', capsules)
    after = doctrine_lattice.expected_organ_instances(root)
    assert before['foo']['role'] == CARD
    assert after['foo']['role'] == 'Second source version.'
    (root/'core/paper_module_capsules.json').unlink()
    with pytest.raises(FileNotFoundError):
        doctrine_lattice.expected_organ_instances(root)


def test_atlas_model_and_full_card_render_once_with_compatibility_keys(root):
    model = organ_atlas.load_model(root)
    card = model['families'][0]['cards'][0]
    assert card['human_gloss'] == card['agent_gloss'] == CARD
    assert card['claim_ceiling_restated'] == CEILING
    assert card['claim_ceiling'] == NORMATIVE
    text = organ_atlas.render_organs_md(model)
    assert STALE not in text
    assert '**What it makes visible:** ' + organ_atlas._public_scope_text(CARD) in text
    assert '**For agents:** ' + organ_atlas._public_scope_text(CARD) not in text


def test_faithfulness_cli_uses_joined_source_and_preserves_blocking(root, capsys):
    write(root, 'thin.json', {'components': [{'organ_id': 'foo', 'display_name': 'Foo Routes'}]})
    assert entry_projection_faithfulness.main(['--root', str(root), '--projection-json', str(root/'thin.json'), '--check']) == 1
    card = json.loads(capsys.readouterr().out)
    assert card['under_projected_count'] == 1
    assert 'core/paper_module_capsules.json' in card['under_projected_rows'][0]['owner_surface_mutation_guidance']
    assert card['description_ref'] == 'core/paper_module_capsules.json'


@pytest.mark.parametrize('card,ceiling,blocked', [
    ('The affirmative production-ready claim is blocked.', 'Neither live Git nor release authority.', False),
    ('This tool is production-ready.', 'No live authority.', True),
    ('The production-ready claim is blocked. This tool is production-ready.', 'No live authority.', True),
    ('Reads fixture data.', 'Certifies arbitrary correctness.', True),
])
def test_canonical_description_guard_distinguishes_blocked_claim_from_affirmative_grant(root, card, ceiling, blocked):
    capsules = json.loads((root/'core/paper_module_capsules.json').read_text())
    capsules['paper_modules'][0]['compression'].update(card=card, authority_ceiling=ceiling)
    write(root, 'core/paper_module_capsules.json', capsules)
    model = organ_atlas.load_model(root)
    assert bool(model['coverage']['overclaim_cards'] or model['coverage']['ceiling_without_negation']) is blocked
