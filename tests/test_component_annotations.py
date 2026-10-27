"""Explicit requirements records and clause mappings never imply whole coverage."""
import copy

import pytest

from microcosm_core.component_annotations import (
    claim_text_sha256, component_annotation_view, validate_annotations,
)


@pytest.fixture
def index():
    return {'nodes': {
        'claim': [{'organ_id': 'example', 'claim_id': 'claim::example',
                   'claim_ceiling': 'A bounded example claim.',
                   'card': {'formal_subclaim_ids': ['subclaim::example']}}],
        'subclaim': [{'subclaim_id': 'subclaim::example'}],
        'artifact': [{'artifact_id': 'tests/test_example.py', 'availability': 'available'},
                     {'artifact_id': 'receipts/example.json', 'availability': 'unavailable'}]},
        'explorer': {'requirements_reviews': [], 'claim_clause_coverage': []}}


def review():
    # Deliberately synthetic test data, not a saved source review.
    return {'review_id': 'synthetic_review', 'target_id': 'claim::example',
            'requirement': 'Protect every supplied live owner.', 'reviewer': 'Synthetic fixture reviewer',
            'reviewed_at': '2026-10-27', 'outcome': 'requires_revision',
            'limits': 'Fixture only; no actual review claimed.', 'evidence_refs': ['tests/test_example.py']}


def mapping(index):
    return {'component_id': 'example', 'claim_text_sha256': claim_text_sha256(index['nodes']['claim'][0]),
            'clauses': [{'clause_id': 'c1', 'text': 'Mapped clause', 'limits': 'Bounded supplied inputs.',
                         'evidence_refs': ['tests/test_example.py']},
                        {'clause_id': 'c2', 'text': 'Unmapped clause', 'limits': 'Evidence absent.', 'evidence_refs': []}]}


def test_default_annotations_are_unrecorded_and_unknown(index):
    validate_annotations(index)
    view = component_annotation_view(index, 'example')
    assert view['requirements_reviews'] == {'status': 'unrecorded', 'records': []}
    assert view['claim_clause_coverage']['status'] == 'unknown'
    assert view['claim_clause_coverage']['whole_claim_coverage'] == 'unknown'
    assert view['claim_clause_coverage']['mapped_clause_count'] is None


@pytest.mark.parametrize('target', ['claim::example', 'subclaim::example'])
@pytest.mark.parametrize('date', ['2026-10-27', '2026-10-27T12:30:00Z', '2026-10-27T12:30:00+01:00'])
def test_valid_review_dates_and_targets(index, target, date):
    row = review()
    row.update(target_id=target, reviewed_at=date)
    index['explorer']['requirements_reviews'] = [row]
    validate_annotations(index)
    view = component_annotation_view(index, 'example')
    assert view['requirements_reviews']['status'] == 'recorded'
    assert view['requirements_reviews']['records'][0]['outcome'] == 'requires_revision'


@pytest.mark.parametrize('field,value', [
    ('review_id', ''), ('target_id', 'claim::absent'), ('target_id', []),
    ('reviewer', ''), ('outcome', 'approved'), ('outcome', []),
    ('reviewed_at', '2026-02-30'), ('reviewed_at', '20261027'),
    ('reviewed_at', '2026-10-27T12:30:00'), ('evidence_refs', []),
    ('evidence_refs', ['receipts/example.json']), ('evidence_refs', ['missing.py']),
    ('evidence_refs', ['../escape.py']), ('evidence_refs', [{}]),
    ('evidence_refs', ['tests/test_example.py', 'tests/test_example.py']),
])
def test_invalid_review_record_is_rejected(index, field, value):
    row = review()
    row[field] = value
    index['explorer']['requirements_reviews'] = [row]
    with pytest.raises(ValueError):
        validate_annotations(index)


def test_duplicate_reviews_rejected(index):
    index['explorer']['requirements_reviews'] = [review(), review()]
    with pytest.raises(ValueError, match='identity'):
        validate_annotations(index)


def test_partial_and_fully_mapped_clauses_keep_whole_coverage_unknown(index):
    row = mapping(index)
    index['explorer']['claim_clause_coverage'] = [row]
    validate_annotations(index)
    view = component_annotation_view(index, 'example')
    assert view['claim_clause_coverage']['mapped_clause_count'] == 1
    assert view['claim_clause_coverage']['whole_claim_coverage'] == 'unknown'
    row['clauses'][1]['evidence_refs'] = ['tests/test_example.py']
    validate_annotations(index)
    assert component_annotation_view(index, 'example')['claim_clause_coverage']['whole_claim_coverage'] == 'unknown'


@pytest.mark.parametrize('mutation', ['stale', 'duplicate_component', 'duplicate_clause', 'unavailable', 'unknown_component', 'unhashable_component'])
def test_invalid_clause_mappings(index, mutation):
    row = mapping(index)
    index['explorer']['claim_clause_coverage'] = [row]
    if mutation == 'stale':
        index['nodes']['claim'][0]['claim_ceiling'] += ' Changed.'
    elif mutation == 'duplicate_component':
        index['explorer']['claim_clause_coverage'].append(copy.deepcopy(row))
    elif mutation == 'duplicate_clause':
        row['clauses'][1]['clause_id'] = 'c1'
    elif mutation == 'unavailable':
        row['clauses'][0]['evidence_refs'] = ['receipts/example.json']
    else:
        row['component_id'] = [] if mutation == 'unhashable_component' else 'missing'
    with pytest.raises(ValueError):
        validate_annotations(index)


def test_annotation_view_detaches_snapshot_lists(index):
    index['explorer']['requirements_reviews'] = [review()]
    index['explorer']['claim_clause_coverage'] = [mapping(index)]
    view = component_annotation_view(index, 'example')
    view['requirements_reviews']['records'][0]['reviewer'] = 'changed'
    view['claim_clause_coverage']['clauses'][0]['text'] = 'changed'
    assert index['explorer']['requirements_reviews'][0]['reviewer'] == 'Synthetic fixture reviewer'
    assert index['explorer']['claim_clause_coverage'][0]['clauses'][0]['text'] == 'Mapped clause'
