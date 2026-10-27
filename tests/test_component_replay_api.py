from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from microcosm_core import component_replay as replay
from microcosm_core.receipts import write_json_atomic


@pytest.fixture(autouse=True)
def isolated_hash_root(tmp_path, monkeypatch):
    code = tmp_path / 'executing-runtime'
    code.mkdir()
    for name in ('microcosm_core', 'plectis'):
        (code / name).mkdir()
        (code / name / 'version.py').write_text('VERSION = 1\n')
    monkeypatch.setattr(replay, 'CODE_ROOT', code)


def step(name='probe', runner=None):
    return SimpleNamespace(organ_id=name, example_rel='input', receipt_name='result.json', runner=runner or record)


def record(source, out, command):
    out.mkdir(parents=True)
    result = {'organ_id': out.name, 'status': 'pass'}
    write_json_atomic(out / 'result.json', result)
    return result


def setup_root(root):
    (root / 'input').mkdir(exist_ok=True)
    return root / '.microcosm/replays'


def run(root, *, steps=None, registry=None, provider=None, organ_id='probe', out=None):
    steps = [step()] if steps is None else steps
    registry = [{'organ_id': route.organ_id} for route in steps] if registry is None else registry
    return replay.replay_component(root, out or root / '.microcosm/replays', organ_id,
                                   declared_steps=steps, registry_rows=registry,
                                   route_provider=provider or (lambda: steps))


@pytest.mark.parametrize('kind', ['empty_runtime', 'empty_registry', 'duplicate_runtime', 'duplicate_registry',
                                 'mismatch', 'narrow_provider', 'duplicate_provider', 'unknown', 'nonexact'])
def test_invalid_universes_or_exact_id_are_rejected_without_output_or_runner(tmp_path, kind):
    setup_root(tmp_path)
    def forbidden(*args):
        pytest.fail('invalid selection executed')
    steps = [step(runner=forbidden), step('other', forbidden)]
    registry = [{'organ_id': route.organ_id} for route in steps]
    provider = lambda: steps
    organ_id = 'probe'
    if kind == 'empty_runtime': steps = []
    if kind == 'empty_registry': registry = []
    if kind == 'duplicate_runtime': steps = [steps[0], steps[0]]
    if kind == 'duplicate_registry': registry = [registry[0], registry[0]]
    if kind == 'mismatch': registry[1]['organ_id'] = 'missing'
    if kind == 'narrow_provider': provider = lambda: steps[:1]
    if kind == 'duplicate_provider': provider = lambda: [steps[0], steps[0]]
    if kind == 'unknown': organ_id = 'missing'
    if kind == 'nonexact': organ_id = 'probe '
    with pytest.raises(replay.ReplaySelectionError):
        run(tmp_path, steps=steps, registry=registry, provider=provider, organ_id=organ_id)
    assert not (tmp_path / '.microcosm').exists()


def test_one_component_admission_retains_full_route_snapshot_and_writes_fresh_summary(tmp_path):
    setup_root(tmp_path)
    called = []
    def selected(source, out, command):
        called.append(out.name)
        return record(source, out, command)
    def forbidden(*args):
        pytest.fail('unselected component executed')
    routes = [step(runner=selected), step('other', forbidden)]
    result = run(tmp_path, steps=routes)
    assert result['status'] == 'pass' and result['admission']['accepted'] is True
    assert result['scope'] == 'component' and result['selected_organ_ids'] == ['probe']
    assert result['component_count'] == 1 and called == ['probe']
    assert [row['component_id'] for row in result['admission']['registry_specs']] == ['probe']
    expected = replay._json_digest([replay._route_policy(route, {}) for route in routes])
    assert result['source']['route_contract_sha256'] == expected
    assert result['source']['route_contract_sha256'] != replay._json_digest([replay._route_policy(routes[0], {})])
    assert json.loads(Path(result['summary_ref']).read_text()) == result
    second = run(tmp_path, steps=routes)
    assert second['summary_ref'] != result['summary_ref']
    assert Path(result['summary_ref']).is_relative_to(tmp_path / '.microcosm')


def test_changed_unselected_route_rejects_selected_admission(tmp_path):
    setup_root(tmp_path)
    routes = []
    def selected(source, out, command):
        routes[1] = SimpleNamespace(**{**vars(routes[1]), 'example_rel': 'changed-route'})
        return record(source, out, command)
    routes.extend([step(runner=selected), step('other')])
    result = run(tmp_path, steps=routes, provider=lambda: routes)
    assert result['status'] == 'blocked' and result['execution_state'] == 'source_changed'


@pytest.mark.parametrize('mutation', ['wrong_receipt', 'source_changed'])
def test_wrong_receipt_and_mutated_source_never_admit(tmp_path, mutation):
    setup_root(tmp_path)
    source = tmp_path / 'src/value.py'
    source.parent.mkdir()
    source.write_text('before')
    def runner(input_dir, out, command):
        out.mkdir(parents=True)
        result = {'organ_id': 'probe', 'status': 'pass'}
        write_json_atomic(out / 'result.json', {**result, 'organ_id': 'wrong'} if mutation == 'wrong_receipt' else result)
        if mutation == 'source_changed': source.write_text('after')
        return result
    result = run(tmp_path, steps=[step(runner=runner)])
    assert result['status'] == 'blocked' and result['admission']['accepted'] is False
    assert result['execution_state'] == ('source_changed' if mutation == 'source_changed' else 'admission_rejected')


def test_missing_input_and_unknown_runner_failure_are_distinct(tmp_path):
    missing = run(tmp_path)
    assert missing['status'] == 'blocked' and missing['execution_state'] == 'missing_input'
    setup_root(tmp_path)
    def unknown(*args): raise RuntimeError('unclassified backend failure')
    failure = run(tmp_path, steps=[step(runner=unknown)])
    assert failure['status'] == 'blocked' and failure['execution_state'] == 'unknown'
    assert failure['results'][0]['error'] == 'RuntimeError'


def test_native_route_applied_once_and_missing_tool_cannot_pass(tmp_path, monkeypatch):
    from microcosm_core.runtime_shell import RUNTIME_STEPS
    from microcosm_core.organs import lean_proof_search_lab_runtime as lab
    fixture_ref = 'fixtures/first_wave/lean_proof_search_lab_runtime/input'
    (tmp_path / fixture_ref).mkdir(parents=True)
    native_calls = []
    actual_native = replay.native_replay_step
    def native_once(route):
        native_calls.append(route.organ_id)
        return actual_native(route)
    def native(source, out, command):
        assert source == tmp_path / fixture_ref
        out.mkdir(parents=True)
        result = {'organ_id': lab.ORGAN_ID, 'status': 'locked', 'tool_state': lab.TOOL_MISSING,
                  'verification_performed': False, 'execution_witness_mode': lab.EXECUTION_LOCKED}
        write_json_atomic(out / lab.RESULT_NAME, result)
        return result
    monkeypatch.setattr(lab, 'run', native)
    monkeypatch.setattr(replay, 'native_replay_step', native_once)
    declared = next(route for route in RUNTIME_STEPS if route.organ_id == lab.ORGAN_ID)
    result = run(tmp_path, steps=[declared], organ_id=lab.ORGAN_ID)
    assert native_calls == [lab.ORGAN_ID]
    assert result['status'] == 'blocked' and result['execution_state'] == 'tool_unavailable'
    assert result['results'][0]['input_ref'] == fixture_ref
    assert result['admission']['accepted'] is False


@pytest.mark.parametrize('target', ['external', 'source', 'linked_parent', 'linked_microcosm'])
def test_output_confined_before_execution(tmp_path, target):
    setup_root(tmp_path)
    external = tmp_path / 'outside'
    external.mkdir()
    if target == 'external': out = external
    elif target == 'source': out = tmp_path / 'src'
    elif target == 'linked_parent':
        (tmp_path / '.microcosm').mkdir()
        (tmp_path / '.microcosm/link').symlink_to(external, target_is_directory=True)
        out = tmp_path / '.microcosm/link/replays'
    else:
        (tmp_path / '.microcosm').symlink_to(external, target_is_directory=True)
        out = tmp_path / '.microcosm/replays'
    with pytest.raises(ValueError):
        run(tmp_path, out=out)
    assert list(external.iterdir()) == []


def test_lowlevel_does_not_change_environment_bytecode_or_receipt_observers(tmp_path):
    from microcosm_core.receipts import observe_receipt_writes
    setup_root(tmp_path)
    before_env = dict(os.environ)
    before_bytecode = sys.dont_write_bytecode
    observations = []
    with observe_receipt_writes(observations.append):
        result = run(tmp_path)
        write_json_atomic(tmp_path / '.microcosm/after.json', {'done': True})
    assert result['status'] == 'pass' and len(observations) == 2
    assert dict(os.environ) == before_env and sys.dont_write_bytecode == before_bytecode
    assert observations[-1].target == (tmp_path / '.microcosm/after.json').resolve()


def test_installed_cli_registers_exact_component_route_and_preserves_exit_codes(tmp_path, monkeypatch, capsys):
    from microcosm_core import cli, runtime_shell
    setup_root(tmp_path)
    (tmp_path / 'core').mkdir()
    (tmp_path / 'core/organ_registry.json').write_text(json.dumps({'implemented_organs': [{'organ_id': 'probe'}]}))
    monkeypatch.setattr(runtime_shell, 'RUNTIME_STEPS', (step(),))
    assert cli.main(['component-replay', 'probe', '--root', str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)['scope'] == 'component'
    assert cli.main(['component-replay', 'unknown', '--root', str(tmp_path)]) == 2
    assert json.loads(capsys.readouterr().err)['error_code'] == 'unknown_component'
    def blocked(source, out, command):
        result = {'organ_id': 'probe', 'status': 'blocked'}
        out.mkdir(parents=True)
        write_json_atomic(out / 'result.json', result)
        return result
    monkeypatch.setattr(runtime_shell, 'RUNTIME_STEPS', (step(runner=blocked),))
    assert cli.main(['component-replay', 'probe', '--root', str(tmp_path), '--format', 'text']) == 1
    assert '1 selected component' in capsys.readouterr().out


def test_existing_checker_keeps_complete_gate_and_adds_selected_organ(tmp_path, monkeypatch, capsys):
    from importlib.util import module_from_spec, spec_from_file_location
    path = Path(__file__).resolve().parents[1] / 'scripts/check/check_component_replays.py'
    spec = spec_from_file_location('candidate_component_gate', path)
    gate = module_from_spec(spec)
    spec.loader.exec_module(gate)
    setup_root(tmp_path)
    (tmp_path / 'core').mkdir()
    (tmp_path / 'core/organ_registry.json').write_text(json.dumps({'implemented_organs': [
        {'organ_id': 'probe'}, {'organ_id': 'other'}]}))
    monkeypatch.setattr(gate, 'RUNTIME_STEPS', (step(), step('other')))
    selected_out = tmp_path / '.microcosm/selected'
    assert gate.main(['--root', str(tmp_path), '--out', str(selected_out), '--organ', 'probe']) == 0
    selected = json.loads(next(selected_out.glob('run-*/component-replays.json')).read_text())
    assert selected['component_count'] == 1 and selected['scope'] == 'component'
    complete_out = tmp_path / '.microcosm/complete'
    # Historical all-run global changes are preserved by the script. Keep those
    # effects local to this test through monkeypatch's restoration.
    monkeypatch.setenv('MICROCOSM_TRACKED_RECEIPT_WRITES', os.environ.get('MICROCOSM_TRACKED_RECEIPT_WRITES', '0'))
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', os.environ.get('PYTHONDONTWRITEBYTECODE', '1'))
    monkeypatch.setattr(sys, 'dont_write_bytecode', sys.dont_write_bytecode)
    assert gate.main(['--root', str(tmp_path), '--out', str(complete_out)]) == 0
    complete = json.loads(next(complete_out.glob('run-*/component-replays.json')).read_text())
    assert complete['component_count'] == 2 and 'scope' not in complete
    assert '2 components, 0 failures' in capsys.readouterr().out
    with pytest.raises(SystemExit) as usage:
        gate.main(['--root', str(tmp_path), '--out', str(selected_out), '--organ', 'unknown'])
    assert usage.value.code == 2


@pytest.mark.parametrize('receipt_name', ['../escaped.json', '/tmp/escaped.json', '.', '', 'subdir/result.json'])
def test_invalid_primary_receipt_name_rejects_before_output(tmp_path, receipt_name):
    setup_root(tmp_path)
    selected = step()
    selected.receipt_name = receipt_name
    with pytest.raises(replay.ReplaySelectionError) as denied:
        run(tmp_path, steps=[selected])
    assert denied.value.code == 'invalid_receipt_name'
    assert not (tmp_path / '.microcosm').exists()
