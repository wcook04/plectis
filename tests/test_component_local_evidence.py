"""Saved-run fixtures test admission only; no component runner executes."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from microcosm_core.component_local_evidence import load_local_run_evidence, validate_local_run_evidence

ROOT = Path(__file__).resolve().parents[1]


def test_disabled_does_no_io(monkeypatch):
    monkeypatch.setattr(Path, 'stat', lambda *a, **k: pytest.fail('disabled loader did IO'))
    value = load_local_run_evidence('/does/not/exist', {}, None)
    validate_local_run_evidence(value)
    assert value['status'] == 'disabled' and value['runs'] == []


@pytest.fixture
def saved(tmp_path):
    from microcosm_core.component_replay import _json_digest, _route_policy
    from microcosm_core.runtime_shell import RUNTIME_STEPS
    from microcosm_core.receipts import receipt_payload_digest
    root = tmp_path / 'project'
    (root / 'core').mkdir(parents=True)
    registry_bytes = (ROOT / 'core/organ_registry.json').read_bytes()
    (root / 'core/organ_registry.json').write_bytes(registry_bytes)
    registry = json.loads(registry_bytes)['implemented_organs']
    index = {'nodes': {'organ': [{'organ_id': r['organ_id']} for r in registry],
                       'artifact': [{'artifact_id': 'core/organ_registry.json', 'availability': 'available',
                                     'sha256': hashlib.sha256(registry_bytes).hexdigest()}]}}
    run = root / '.microcosm/component-replays/run-test'
    run.mkdir(parents=True)
    organ_id = 'pattern_binding_contract'
    selected = next(s for s in RUNTIME_STEPS if s.organ_id == organ_id)
    policy = next(r for r in registry if r['organ_id'] == organ_id)
    spec = {'component_id': organ_id, 'input_ref': selected.example_rel,
            'evidence_class': policy['evidence_class'], 'claim_digest': _json_digest(_route_policy(selected, policy)), 'native_kind': 0}
    source = {'source_inventory_scheme': 'package_roots_v1', 'runtime_package_digest_scheme': 'tree_type_path_bytes_posix_mode_v2',
              'runtime_package_tree_sha256': {'microcosm_core': 'a' * 64, 'plectis': 'b' * 64},
              'runtime_source_scope': ['microcosm_core/**', 'plectis/**'],
              'route_contract_sha256': _json_digest([_route_policy(s, {}) for s in RUNTIME_STEPS])}
    source['runtime_source_tree_sha256'] = _json_digest(source['runtime_package_tree_sha256'])
    identity = _json_digest(source)
    receipt = {'organ_id': organ_id, 'status': 'pass'}
    receipt_path = run / organ_id / selected.receipt_name
    receipt_path.parent.mkdir()
    data = json.dumps(receipt).encode()
    receipt_path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    payload = receipt_payload_digest(receipt)
    observation = {**spec, 'runner_component_id': organ_id, 'receipt_component_id': organ_id,
                   'source_before': identity, 'source_after': identity, 'input_before': 'c' * 64, 'input_after': 'c' * 64,
                   'runner_payload_digest': payload, 'receipt_payload_digest': payload, 'receipt_digest': digest,
                   'runner_status': 'pass', 'receipt_status': 'pass', 'runner_verdict': 'pass', 'receipt_verdict': 'pass',
                   'runner_native_kind': 0, 'receipt_native_kind': 0, 'receipt_present': True}
    observation.pop('native_kind')
    summary = {'schema_version': 'plectis_component_replay_gate_v2', 'scope': 'component',
               'selected_organ_ids': [organ_id], 'component_count': 1, 'status': 'pass', 'execution_state': 'pass',
               'failed_components': [], 'summary_ref': str(run / 'component-replays.json'),
               'source': source, 'source_after': source, 'source_identity_material': source, 'source_identity': identity,
               'source_inventory_scheme': 'package_roots_v1', 'runtime_source_scope': source['runtime_source_scope'],
               'results': [{'organ_id': organ_id, 'status': 'pass', 'receipt_written': True,
                            'primary_receipt_write_count': 1, 'receipt_ref': str(receipt_path), 'receipt_sha256': digest}],
               'admission': {'kernel': 'plectis.replay.accept', 'accepted': True, 'run_id': run.name,
                             'registry_specs': [spec], 'observations': [observation]}}
    path = run / 'component-replays.json'
    path.write_text(json.dumps(summary))
    return root, index, run, path, receipt_path, summary


def test_saved_observations_rechecked_without_runner_execution(saved, monkeypatch):
    root, index, run, _, _, _ = saved
    import microcosm_core.component_replay as host
    monkeypatch.setattr(host, 'replay_components', lambda *a, **k: pytest.fail('runner invoked'))
    value = load_local_run_evidence(root, index, run.parent)
    validate_local_run_evidence(value)
    row = value['runs'][0]
    assert row['admission']['rechecked_accepted'] is True
    assert row['current_source_binding']['status'] == 'unknown'
    assert row['input_freshness']['status'] == 'unknown'
    assert row['recorded_time']['status'] == 'unrecorded'
    encoded = json.dumps(value)
    assert str(root) not in encoded
    assert 'receipt_ref' not in encoded
    assert value == load_local_run_evidence(root, index, run)


@pytest.mark.parametrize('mutation', ['summary_symlink', 'receipt_symlink', 'receipt_changed', 'policy_changed', 'registry_changed', 'duplicate', 'nonfinite', 'outside_receipt', 'oversize', 'source_identity'])
def test_invalid_saved_evidence_is_rejected_without_private_errors(saved, mutation):
    root, index, run, path, receipt_path, summary = saved
    if mutation.endswith('symlink'):
        target = path if mutation.startswith('summary') else receipt_path
        outside = root / 'elsewhere.json'
        outside.write_bytes(target.read_bytes())
        target.unlink()
        target.symlink_to(outside)
    elif mutation == 'receipt_changed':
        receipt_path.write_text('{"organ_id":"wrong","status":"pass"}')
    elif mutation == 'policy_changed':
        summary['admission']['registry_specs'][0]['claim_digest'] = '0' * 64
        path.write_text(json.dumps(summary))
    elif mutation == 'registry_changed':
        (root / 'core/organ_registry.json').write_text('{}')
    elif mutation == 'duplicate':
        path.write_text('{"status":"pass","status":"pass"}')
    elif mutation == 'nonfinite':
        path.write_text('{"value":NaN}')
    elif mutation == 'outside_receipt':
        summary['results'][0]['receipt_ref'] = '/outside/secret.json'
        path.write_text(json.dumps(summary))
    elif mutation == 'oversize':
        path.write_bytes(b' ' * (2 * 1024 * 1024 + 1))
    else:
        summary['source_identity'] = '0' * 64
        path.write_text(json.dumps(summary))
    with pytest.raises(ValueError) as error:
        load_local_run_evidence(root, index, run.parent)
    assert str(error.value) == 'explicit local saved-run evidence rejected'


def test_run_count_is_bounded(saved):
    root, index, run, *_ = saved
    for i in range(32):
        (run.parent / f'run-extra{i}').mkdir()
    with pytest.raises(ValueError):
        load_local_run_evidence(root, index, run.parent)


def test_public_overlay_schema_rejects_claim_escalation(saved):
    root, index, run, *_ = saved
    value = load_local_run_evidence(root, index, run)
    value['runs'][0]['fresh_execution']['status'] = 'pass'
    with pytest.raises(ValueError):
        validate_local_run_evidence(value)


def test_blocked_saved_admission_is_rechecked_and_not_called_pass(saved):
    root, index, run, path, _, summary = saved
    summary.update(status='blocked', execution_state='admission_rejected', failed_components=['pattern_binding_contract'])
    summary['admission']['accepted'] = False
    summary['admission']['observations'][0]['runner_status'] = 'failed'
    path.write_text(json.dumps(summary))
    value = load_local_run_evidence(root, index, run)
    validate_local_run_evidence(value, index)
    assert value['runs'][0]['admission']['rechecked_accepted'] is False
    assert value['runs'][0]['recorded_status'] == 'blocked'
    assert value['runs'][0]['receipt_sha256'] is None


def test_total_byte_bound_includes_registry_summary_and_receipt(saved, monkeypatch):
    root, index, run, path, receipt, _ = saved
    import microcosm_core.component_local_evidence as local
    size = (root / 'core/organ_registry.json').stat().st_size + path.stat().st_size + receipt.stat().st_size
    monkeypatch.setattr(local, 'MAX_TOTAL_BYTES', size - 1)
    with pytest.raises(ValueError):
        load_local_run_evidence(root, index, run)


def test_secret_payload_never_published(saved):
    root, index, run, _, receipt, _ = saved
    receipt.write_text(json.dumps({'organ_id': 'pattern_binding_contract', 'status': 'pass',
                                 'token': 'ghp_' + 'a' * 40}))
    with pytest.raises(ValueError) as error:
        load_local_run_evidence(root, index, run)
    assert 'ghp_' not in str(error.value)


def test_pure_schema_binds_component_universe(saved):
    root, index, run, *_ = saved
    value = load_local_run_evidence(root, index, run)
    altered = copy.deepcopy(index)
    altered['nodes']['organ'] = []
    with pytest.raises(ValueError):
        validate_local_run_evidence(value, altered)


@pytest.mark.parametrize('field,value', [('admission', []), ('recorded_status', []), ('source_identity', 'bad'),
                                         ('summary_sha256', None), ('component_id', '../bad')])
def test_pure_schema_malformed_rows_fail_cleanly(saved, field, value):
    root, index, run, *_ = saved
    overlay = load_local_run_evidence(root, index, run)
    overlay['runs'][0][field] = value
    with pytest.raises(ValueError):
        validate_local_run_evidence(overlay, index)
