"""Explorer metadata preserves source meaning and unknown evidence states."""
import json
from pathlib import Path

from microcosm_core.projections.component_explorer_metadata import (
    _receipt_summary, _source_revision, collect_explorer_metadata,
)

ROOT = Path(__file__).resolve().parents[1]


def test_owner_metadata_and_doctrine_grounding():
    data = collect_explorer_metadata(ROOT)
    organs = json.loads((ROOT / 'core/organ_registry.json').read_text())['implemented_organs']
    assert set(data['component_filters']) == {
        'family', 'evidence_class', 'truth_accounting_bucket', 'real_substrate_disposition'}
    for rows in data['component_filters'].values():
        assert sum(row['component_count'] for row in rows) == len(organs)
    nodes = {row['id']: row for row in data['doctrine']['nodes']}
    assert nodes['AX-1']['title'] == 'Derivation before assertion'
    assert any(row == {'from_id': 'P-2', 'to_id': 'AX-5', 'kind': 'rests_on',
                       'source_ref': 'PRINCIPLES.md::P-2'} for row in data['doctrine']['edges'])
    assert any(row['kind'] == 'anti_principle' for row in nodes.values())
    assert data['typed_relations']['status'] in {'observed', 'partially_observed'}
    assert all(row['kind'] == 'imports_runner' for row in data['typed_relations']['edges'])


def test_receipt_summary_is_bounded_and_never_infers_a_date(tmp_path):
    folder = tmp_path / 'receipts'
    folder.mkdir()
    path = folder / '20260101.json'
    path.write_text(json.dumps({'status': 'pass', 'fixture_id': 'bounded',
                                'created_at': '2026-02-31', 'source_body': 'secret',
                                'result': {'source': 'body'}}))
    row = _receipt_summary(tmp_path, 'receipts/20260101.json')
    assert row['availability'] == 'available'
    assert row['date_status'] == 'unrecorded'
    assert row['created_at'] is None
    assert row['recorded_fields'] == {'status': 'pass', 'fixture_id': 'bounded'}
    path.write_text(json.dumps({'created_at': '2026-01-01T12:00:00Z', 'error_count': 0}))
    row = _receipt_summary(tmp_path, 'receipts/20260101.json')
    assert row['created_at'] == '2026-01-01T12:00:00Z'
    assert row['recorded_fields'] == {'error_count': 0}
    assert _receipt_summary(tmp_path, '../outside.json')['availability'] == 'unavailable'


def test_export_without_git_has_no_exact_revision_claim(tmp_path):
    row = _source_revision(tmp_path)
    assert row['status'] == 'unknown'
    assert row['commit'] is None
    assert row['exact_source_links'] is False


def test_typed_imports_have_exact_line_evidence(tmp_path):
    from microcosm_core.projections.component_explorer_metadata import _typed_relations
    folder = tmp_path / 'src' / 'sample'
    folder.mkdir(parents=True)
    (folder / 'a.py').write_text('from . import b\nimport unrelated\n')
    (folder / 'b.py').write_text('pass\n')
    rows = [{'runner': 'sample.a', 'organ_id': 'a'}, {'runner': 'sample.b', 'organ_id': 'b'}]
    result = _typed_relations(tmp_path, rows)
    assert result['status'] == 'observed'
    assert len(result['edges']) == 1
    edge = result['edges'][0]
    assert edge['from_id'] == 'a' and edge['to_id'] == 'b'
    assert edge['source_ref'] == 'src/sample/a.py#L1'
    assert edge['line'] == 1 and len(edge['source_sha256']) == 64


def test_public_sources_reject_traversal_symlinks_and_oversize(tmp_path):
    import pytest
    from microcosm_core.projections.component_explorer_metadata import _load
    source = tmp_path / 'source.json'
    source.write_text('{}')
    (tmp_path / 'alias').symlink_to(tmp_path, target_is_directory=True)
    for ref in ('../outside', '/absolute', 'alias/source.json'):
        with pytest.raises((ValueError, OSError)):
            _load(tmp_path, ref)
    source.write_bytes(b' ' * 2_000_001)
    with pytest.raises(ValueError, match='byte limit'):
        _load(tmp_path, 'source.json')


def test_runner_parse_errors_fail_instead_of_claiming_absence(tmp_path):
    import pytest
    from microcosm_core.projections.component_explorer_metadata import _typed_relations
    folder = tmp_path / 'src'
    folder.mkdir()
    (folder / 'bad.py').write_text('def broken(')
    with pytest.raises(ValueError, match='invalid runner Python source'):
        _typed_relations(tmp_path, [{'runner': 'bad', 'organ_id': 'bad'}])
    (folder / 'alias.py').symlink_to(folder / 'bad.py')
    result = _typed_relations(tmp_path, [{'runner': 'alias', 'organ_id': 'alias'}])
    assert result['status'] == 'partially_observed'
    assert result['unavailable_component_ids'] == ['alias']


def test_receipt_hash_is_exact_source_bytes(tmp_path):
    import hashlib
    path = tmp_path / 'historical'
    path.mkdir()
    source = b'{ "status": "pass" }\n'
    (path / 'record.json').write_bytes(source)
    row = _receipt_summary(tmp_path, 'historical/record.json')
    assert row['artifact_sha256'] == hashlib.sha256(source).hexdigest()


def test_ssh_remote_identity_is_normalized_without_false_clean_claim(tmp_path, monkeypatch):
    import subprocess
    def fake_run(args, **kwargs):
        command = args[3:]
        values = {('rev-parse', '--show-toplevel'): str(tmp_path),
                  ('rev-parse', 'HEAD'): 'a' * 40,
                  ('status', '--porcelain', '--untracked-files=normal'): ' M source.py',
                  ('remote', 'get-url', 'origin'): 'git@github.com:wcook04/practical-formal-verification.git'}
        return subprocess.CompletedProcess(args, 0, values[tuple(command)], '')
    monkeypatch.setattr(subprocess, 'run', fake_run)
    result = _source_revision(tmp_path)
    assert result['repository'] == 'https://github.com/wcook04/practical-formal-verification'
    assert result['dirty'] is True
    assert result['exact_source_links'] is False


def test_disposition_descriptions_and_historical_receipts_follow_owners():
    result = collect_explorer_metadata(ROOT)
    assert all(row['description'] for row in result['component_filters']['real_substrate_disposition'])
    organs = json.loads((ROOT / 'core/organ_registry.json').read_text())['implemented_organs']
    refs = {row['ref'] for row in result['receipt_summaries']}
    assert {row['historical_source_authority_receipt'] for row in organs
            if row.get('historical_source_authority_receipt')} <= refs


def test_family_counts_follow_index_classification_instead_of_family_membership():
    from collections import Counter
    atlas = json.loads((ROOT / 'core/organ_atlas.json').read_text())['organs']
    payload = {'nodes': {'organ': atlas}}
    result = collect_explorer_metadata(ROOT, payload)
    actual = {row['value']: row['component_count'] for row in result['component_filters']['family']}
    assert actual == dict(Counter(row['family'] for row in atlas))
    # An index producer's accepted classification is the counting authority.
    changed = [dict(row) for row in atlas]
    previous = changed[0]['family']
    target = next(row['family'] for row in changed if row['family'] != previous)
    changed[0]['family'] = target
    changed_result = collect_explorer_metadata(ROOT, {'nodes': {'organ': changed}})
    counts = {row['value']: row['component_count'] for row in changed_result['component_filters']['family']}
    assert counts[previous] == actual[previous] - 1
    assert counts[target] == actual[target] + 1


def test_present_nonobject_or_malformed_receipt_keeps_artifact_availability(tmp_path):
    import hashlib
    path = tmp_path / 'receipt.json'
    for source in (b'{broken json', b'[]', b'\xff'):
        path.write_bytes(source)
        row = _receipt_summary(tmp_path, 'receipt.json')
        assert row['availability'] == 'available'
        assert row['availability_reason'] is None
        assert row['artifact_sha256'] == hashlib.sha256(source).hexdigest()
        assert row['recorded_fields'] == {}
        assert row['date_status'] == 'unrecorded'
    path.write_bytes(b'x' * 2_000_001)
    row = _receipt_summary(tmp_path, 'receipt.json')
    assert row['availability'] == 'unavailable'
    assert row['availability_reason'] == 'source_rejected'
    assert row['artifact_sha256'] is None
    assert _receipt_summary(tmp_path, 'absent.json')['availability_reason'] == 'source_unavailable'
