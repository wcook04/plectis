"""Validate immutable explorer extensions as pure data, preserving text guards."""
import copy
from collections import Counter
import hashlib
import json
from pathlib import Path

import pytest

from microcosm_core.component_explorer_validation import validate_explorer, public_text_view
from microcosm_core.projections.component_explorer_metadata import collect_explorer_metadata
from microcosm_core.projections.component_proof_excerpts import build_proof_enrichments
from microcosm_core.projections.component_workflow_cores import build_workflow_cores, build_ownership_counterexample

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def explorer_index():
    index = json.loads((ROOT / 'receipts/code_lens/code_lens_join_index_v0.json').read_text())
    index['explorer'] = {
        'schema_version': 'plectis_component_explorer_v1',
        'proof_details': {'proof::dafny::' + p.parent.name: build_proof_enrichments(ROOT, json.loads(p.read_text()))
                          for p in (ROOT / 'formal/components').glob('*/metadata.json')},
        'cores': build_workflow_cores(ROOT),
        'ownership_example': build_ownership_counterexample(ROOT),
        **collect_explorer_metadata(ROOT),
    }
    # Saved index classification is authoritative for this compatibility fixture.
    counts = Counter(row['family'] for row in index['nodes']['organ'])
    for row in index['explorer']['component_filters']['family']:
        row['component_count'] = counts[row['value']]
    return index


def test_real_extension_is_valid_and_masking_does_not_mutate_input(explorer_index):
    validate_explorer(explorer_index)
    view = public_text_view(explorer_index)
    detail = next(iter(view['explorer']['proof_details'].values()))
    original = next(iter(explorer_index['explorer']['proof_details'].values()))
    assert detail['excerpts'][0]['text'] == 'VALIDATED_PUBLIC_DAFNY_EXCERPT'
    assert original['excerpts'][0]['text'] != detail['excerpts'][0]['text']
    assert view['explorer']['component_filters'] == explorer_index['explorer']['component_filters']
    assert view['explorer']['cores'] == explorer_index['explorer']['cores']
    from microcosm_core.component_index import _safe
    _safe(view)


def test_no_optional_extension_remains_compatible():
    index = {'nodes': {}}
    validate_explorer(index)
    assert public_text_view(index) == index
    assert public_text_view(index) is not index


@pytest.mark.parametrize('attack', ['source_hash', 'text', 'extra_body', 'tasks', 'fresh', 'manifest', 'count_bool', 'negative_diff', 'unknown_root'])
def test_tampered_extensions_fail_closed(explorer_index, attack):
    index = copy.deepcopy(explorer_index)
    data = index['explorer']
    detail = next(iter(data['proof_details'].values()))
    if attack == 'source_hash':
        detail['excerpts'][0]['source_sha256'] = '0' * 64
    elif attack == 'text':
        detail['excerpts'][0]['text'] += '// changed\n'
    elif attack == 'extra_body':
        detail['excerpts'][0]['source_body'] = 'method Extra() {}'
    elif attack == 'tasks':
        detail['retained_verification_details']['tasks'] = [{'name': 'RowExact', 'kind': 'lemma'}]
    elif attack == 'fresh':
        data['cores'][0]['fresh_prover_result']['status'] = 'pass'
    elif attack == 'manifest':
        next(row for row in data['cores'][0]['artifact_bindings'] if row['ref'] == data['cores'][0]['specification_refs'][0])['sha256'] = '0' * 64
    elif attack == 'count_bool':
        data['cores'][0]['retained_verification']['verified_tasks'] = True
    elif attack == 'negative_diff':
        next(iter(detail['negative_control_details'].values()))['changed_lines'][0]['mutated'] += ' // drift'
    elif attack == 'unknown_root':
        data['arbitrary_source'] = 'method Extra() {}'
    with pytest.raises(ValueError):
        public_text_view(index)


@pytest.mark.parametrize('private', ['/Users/alice/private.txt', '/home/alice/private.txt', 'C:\\Users\\alice\\private.txt', 'sk-' + 'a' * 32])
def test_source_fields_do_not_hide_secrets_or_home_paths(explorer_index, private):
    index = copy.deepcopy(explorer_index)
    row = next(iter(index['explorer']['proof_details'].values()))['excerpts'][0]
    row['text'] = row['text'].replace('\n', ' // ' + private + '\n', 1)
    row['text_sha256'] = hashlib.sha256(row['text'].encode()).hexdigest()
    with pytest.raises(ValueError, match='private text'):
        public_text_view(index)


def test_comments_division_are_accepted_only_in_validated_source_slots(explorer_index):
    index = copy.deepcopy(explorer_index)
    row = next(iter(index['explorer']['proof_details'].values()))['excerpts'][0]
    row['text'] = row['text'].replace('\n', ' // comment / divisor\n', 1)
    row['text_sha256'] = hashlib.sha256(row['text'].encode()).hexdigest()
    from microcosm_core.component_index import _safe
    _safe(public_text_view(index))
    index['explorer']['typed_relations']['reason'] = 'arbitrary /forbidden/path'
    with pytest.raises(ValueError):
        _safe(public_text_view(index))


@pytest.mark.parametrize('attack', ['filter_count', 'filter_duplicate', 'filter_missing', 'runner_path', 'runner_hash', 'relation_duplicate', 'relation_status', 'receipt_duplicate', 'receipt_unowned', 'receipt_hash', 'receipt_availability'])
def test_metadata_cross_bindings_fail_closed(explorer_index, attack):
    index = copy.deepcopy(explorer_index)
    data = index['explorer']
    if attack == 'filter_count':
        data['component_filters']['family'][0]['component_count'] += 1
    elif attack == 'filter_duplicate':
        data['component_filters']['family'].append(copy.deepcopy(data['component_filters']['family'][0]))
    elif attack == 'filter_missing':
        data['component_filters']['family'].pop()
    elif attack == 'runner_path':
        data['typed_relations']['edges'][0]['source_ref'] = 'src/other.py#L' + str(data['typed_relations']['edges'][0]['line'])
    elif attack == 'runner_hash':
        data['typed_relations']['edges'][0]['source_sha256'] = '0' * 64
    elif attack == 'relation_duplicate':
        data['typed_relations']['edges'].append(copy.deepcopy(data['typed_relations']['edges'][0]))
    elif attack == 'relation_status':
        data['typed_relations']['status'] = 'partially_observed'
    elif attack == 'receipt_duplicate':
        data['receipt_summaries'].append(copy.deepcopy(data['receipt_summaries'][0]))
    elif attack == 'receipt_unowned':
        data['receipt_summaries'][0]['ref'] = 'receipts/unowned.json'
    elif attack == 'receipt_hash':
        facts = {r['artifact_id']: r for r in index['nodes']['artifact']}
        row = next(r for r in data['receipt_summaries'] if r['availability'] == 'available' and facts[r['ref']].get('sha256'))
        row['artifact_sha256'] = '0' * 64
    elif attack == 'receipt_availability':
        row = next(r for r in data['receipt_summaries'] if r['availability'] == 'unavailable')
        row.update(availability='available', artifact_sha256='0' * 64)
    with pytest.raises(ValueError):
        validate_explorer(index)


def test_repository_mask_is_narrow_and_copy_only(explorer_index):
    index = copy.deepcopy(explorer_index)
    index['explorer']['source_revision']['repository'] = 'https://github.com/wcook04/plectis'
    view = public_text_view(index)
    assert view['explorer']['source_revision']['repository'] == 'VALIDATED_PUBLIC_REPOSITORY_URL'
    assert index['explorer']['source_revision']['repository'] == 'https://github.com/wcook04/plectis'
    index['explorer']['source_revision']['repository'] = 'https://example.com/private'
    with pytest.raises(ValueError):
        public_text_view(index)


@pytest.fixture(scope='module')
def reader_index():
    from microcosm_core.projections.component_explorer_metadata import collect_reader_guides
    index = json.loads((ROOT / 'receipts/code_lens/code_lens_join_index_v0.json').read_text())
    component_refs = {row['ref'] for row in index['nodes']['guide']}
    refs = component_refs | {row['formal_readme_ref'] for row in index['nodes']['subclaim']}
    facts = {row['ref']: row for row in index['nodes']['artifact']}
    bindings = {ref: facts[ref]['sha256'] for ref in refs}
    bindings.update({row['guide_ref']: next(b['sha256'] for b in row['artifact_bindings']
                                          if b['ref'] == row['guide_ref'])
                     for row in index['explorer']['cores']})
    index['explorer']['guides'] = collect_reader_guides(ROOT, component_refs, bindings)
    return index


def test_reader_views_are_snapshot_only_and_detached(reader_index, monkeypatch):
    from microcosm_core.component_index import compile_views
    def no_io(*args, **kwargs):
        raise AssertionError('reader views must not read source files')
    monkeypatch.setattr(Path, 'open', no_io)
    monkeypatch.setattr(Path, 'read_text', no_io)
    monkeypatch.setattr(Path, 'read_bytes', no_io)
    views = compile_views(reader_index)
    assert all(row['plain'] and row['plain_availability'] == 'available' for row in views['list'])
    for kind in ('by_component', 'by_proof', 'cores'):
        assert all(row['guide']['text'] and row['guide']['availability'] == 'available'
                   for row in views[kind].values())
    component = next(iter(views['by_component'].values()))
    ref = component['guide']['ref']
    component['guide']['text'] = 'changed by caller'
    assert reader_index['explorer']['guides'][ref]['text'] != 'changed by caller'
    masked = public_text_view(reader_index)
    assert masked['explorer']['guides'][ref]['text'] == 'VALIDATED_PUBLIC_GUIDE_TEXT'


@pytest.mark.parametrize('attack', ['text', 'plain', 'hash', 'missing', 'extra', 'oversize', 'private', 'no_lead'])
def test_reader_manifest_rejects_tampering(reader_index, attack):
    index = copy.deepcopy(reader_index)
    guides = index['explorer']['guides']
    ref = next(ref for ref in guides if ref.startswith('paper_modules/'))
    guide = guides[ref]
    if attack == 'text':
        guide['text'] += ' changed'
    elif attack == 'plain':
        guide['plain'] = 'Invented explanation'
    elif attack == 'hash':
        guide['sha256'] = '0' * 64
    elif attack == 'missing':
        del guides[ref]
    elif attack == 'extra':
        guides['paper_modules/unowned.md'] = copy.deepcopy(guide)
    elif attack == 'oversize':
        from microcosm_core.component_api_contract import MAX_GUIDE_BYTES
        guide['text'] = 'x' * (MAX_GUIDE_BYTES + 1)
    elif attack == 'private':
        guide['text'] = '/home/example/private-key'
        guide['sha256'] = hashlib.sha256(guide['text'].encode()).hexdigest()
    elif attack == 'no_lead':
        guide['text'] = '# Missing explanation\n'
        guide['sha256'] = hashlib.sha256(guide['text'].encode()).hexdigest()
        next(row for row in index['nodes']['artifact'] if row['ref'] == ref)['sha256'] = guide['sha256']
        guide['plain'] = None
        guide['plain_availability'] = 'unrecorded'
    with pytest.raises(ValueError):
        validate_explorer(index)


@pytest.mark.parametrize("without_explorer", [False, True])
def test_legacy_indexes_keep_explicit_unrecorded_guides(reader_index, without_explorer):
    from microcosm_core.component_index import compile_views
    index = copy.deepcopy(reader_index)
    del index['explorer']['guides']
    if without_explorer:
        del index['explorer']
    views = compile_views(index)
    assert all(row['plain'] is None and row['plain_availability'] == 'unrecorded' for row in views['list'])
    for kind in ('by_component', 'by_proof', 'cores'):
        assert all(row['guide']['text'] is None and row['guide']['availability'] == 'unrecorded'
                   for row in views[kind].values())
