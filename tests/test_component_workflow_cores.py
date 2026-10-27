"""Workflow evidence remains retained and fails closed on changed deployed bytes."""
from pathlib import Path
import shutil

import pytest

from microcosm_core.projections.component_workflow_cores import (
    build_ownership_counterexample, build_workflow_cores,
)

ROOT = Path(__file__).resolve().parents[1]


def test_four_cores_bind_retained_sources_and_declared_replays():
    rows = build_workflow_cores(ROOT)
    assert [r['core_id'] for r in rows] == ['repair', 'compatibility', 'views', 'replay_admission']
    assert [r['retained_verification']['verified_tasks'] for r in rows] == [21, 41, 30, 16]
    assert [len(r['negative_controls']) for r in rows] == [1, 3, 2, 2]
    for row in rows:
        assert row['current_binding']['status'] == 'current_hash_binding_pass'
        assert row['fresh_prover_result']['status'] == 'not_run_by_index'
        assert row['requirements_review'] == {'status': 'unrecorded'}
        for ref in row['public_caller_refs'] + row['entry_theorem_refs']:
            path, symbol = ref.split('#')
            assert symbol in (ROOT / path).read_text()
        for control in row['negative_controls']:
            assert control['retained_result']['errors'] > 0
            assert control['fresh_result']['status'] == 'not_run_by_index'
    from microcosm_core.runtime_shell import RUNTIME_STEPS
    assert {r['component_id'] for r in rows[-1]['admitted_replay_routes']} == {s.organ_id for s in RUNTIME_STEPS}


def test_changed_generated_workflow_fails_binding(tmp_path):
    for relative in ('scripts/check', 'formal', 'src/plectis'):
        shutil.copytree(ROOT / relative, tmp_path / relative, ignore=shutil.ignore_patterns('__pycache__'))
    generated = tmp_path / 'src/plectis/repair/_generated/Repair.py'
    generated.write_text(generated.read_text() + '\n# changed\n')
    with pytest.raises(ValueError, match='identity changed'):
        build_workflow_cores(tmp_path)


def test_ownership_orders_match_actual_caller_evidence():
    record = build_ownership_counterexample(ROOT)
    from microcosm_core.organs.concurrency_mission_control import (
        classify_generated_surface_claim_lens, classify_concurrency_closure_state_lens,
    )
    by_id = {c['claim_id']: c for c in record['observations']}
    for order in record['orders']:
        case = {'drift_paths': [record['path']], 'claim_rows': [
            {'path': record['path'], **by_id[c]} for c in order['claim_ids']]}
        actual = classify_generated_surface_claim_lens(case)
        assert actual['classification'] == order['repaired_decision']
        assert actual['allowed_action'] == record['repaired_allowed_action']
        assert actual['owner_session_id'] == order['owner_session_id']
        assert classify_concurrency_closure_state_lens(case)['classification'] == record['closure_decision']
    assert record['orders'][0]['previous_decision'] != record['orders'][1]['previous_decision']
    assert record['requirements_review'] == {'status': 'unrecorded'}


@pytest.fixture
def copied_core(tmp_path):
    # No checker scripts are needed: the collector must execute its own trusted
    # checker implementation rather than code supplied by this data checkout.
    for relative in ('formal', 'src/plectis'):
        shutil.copytree(ROOT / relative, tmp_path / relative, ignore=shutil.ignore_patterns('__pycache__'))
    return tmp_path


@pytest.mark.parametrize('mutation', ['symlink', 'missing_source', 'negative_hash', 'shape', 'duplicate', 'unsafe_manifest'])
def test_untrusted_or_malformed_evidence_fails_closed(copied_core, mutation):
    import json
    root = copied_core
    metadata_path = root / 'formal/repair/metadata.json'
    metadata = json.loads(metadata_path.read_text())
    if mutation == 'symlink':
        path = root / 'src/plectis/repair/_generated/Repair.py'
        path.unlink()
        path.symlink_to(ROOT / 'src/plectis/repair/_generated/Repair.py')
    elif mutation == 'missing_source':
        (root / 'formal/repair/Repair.dfy').unlink()
    elif mutation == 'negative_hash':
        metadata['negative_source_sha256'] = '0' * 64
        metadata_path.write_text(json.dumps(metadata))
    elif mutation == 'shape':
        metadata_path.write_text('[]')
    elif mutation == 'duplicate':
        metadata_path.write_text('{"verified_tasks":21,"verified_tasks":21}')
    else:
        metadata['generated_python'] = {'../../../../outside.py': '0' * 64}
        metadata_path.write_text(json.dumps(metadata))
    with pytest.raises(ValueError):
        build_workflow_cores(root)


def test_data_checkout_checker_is_never_executed(copied_core):
    from microcosm_core.projections.component_workflow_cores import _binding
    checker = copied_core / 'scripts/check/check_repair_kernel.py'
    checker.parent.mkdir(parents=True)
    checker.write_text('raise AssertionError("untrusted checker executed")\n')
    _binding(copied_core, 'repair')


def test_interpretation_provenance_is_hash_bound():
    for row in build_workflow_cores(ROOT):
        manifests = {a['ref'] for a in row['artifact_bindings']}
        for field in ('statement_refs', 'assumption_refs', 'limit_refs'):
            assert set(row['interpretation_provenance'][field]) <= manifests
