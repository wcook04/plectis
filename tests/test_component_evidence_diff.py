from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

from plectis.components.evidence_diff import diff_evidence
from plectis.components.evidence_diff import _adapter

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'examples/batch8_tools_tail_primitives_capsule/'
          'exported_batch8_tools_tail_primitives_capsule_bundle/source_modules/'
          'system/lib/observer_diff.py')


def original_diff():
    spec = importlib.util.spec_from_file_location('_evidence_original_test', SOURCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module.diff_evidence


@pytest.mark.parametrize(('lab', 'oracle'), [
    ([], []),
    ([{'ledger_id': 'x'}, {'ledger_id': 'x', 'v': 2}, {'bad': 1},
      {'ledger_id': 'z', 'v': 0}, {'ledger_id': 'z', 'v': 1}],
     [{'ledger_id': 'a', 'v': 1}, {'ledger_id': 'a', 'v': 3}, {'ledger_id': 'x'}]),
    ([None, {'ledger_id': ''}, {'ledger_id': '🧪'}, {'ledger_id': 'a'}, {'ledger_id': 'é'}],
     [{'ledger_id': '🧪'}, {'ledger_id': '漢'}, {'ledger_id': 'A'}]),
    ([{'ledger_id': 1}, {'ledger_id': 7, 'v': 1}, {'ledger_id': 7, 'v': 2}],
     [{'ledger_id': True}, {'ledger_id': 3.5}]),
    ([{'ledger_id': 7}], [{'ledger_id': 'seven'}]),
    ([{'ledger_id': 'ab'}, {'ledger_id': 'aa'}, {'ledger_id': 'a'}],
     [{'ledger_id': 'aa'}, {'ledger_id': 'aa', 'last': True}]),
    ([{'ledger_id': True}, {'ledger_id': 1.0, 'last': True}, {'ledger_id': 2.0}],
     [{'ledger_id': 1}, {'ledger_id': 2}]),
    ([{'ledger_id': None}, {'ledger_id': False}, {'ledger_id': 0}, {'ledger_id': -0.0}],
     [{'ledger_id': ''}]),
    ([{'ledger_id': -(10 ** 100)}, {'ledger_id': 1e-100}, {'ledger_id': -2.5}],
     [{'ledger_id': -(10 ** 100)}, {'ledger_id': 2e-100}]),
])
def test_normalized_rows_match_frozen_source(lab, oracle):
    expected = original_diff()(lab, oracle).to_json_dict()
    result = diff_evidence(lab, oracle)
    assert result == expected
    assert json.dumps(result, sort_keys=True) == json.dumps(expected, sort_keys=True)
    missed, extra, overlap = (set(result[k]) for k in
        ('missed_ledger_ids', 'extra_ledger_ids', 'overlap_ledger_ids'))
    assert not (missed & extra or missed & overlap or extra & overlap)
    assert missed | extra | overlap == {
        row['ledger_id'] for row in lab + oracle
        if isinstance(row, dict) and row.get('ledger_id')
    }


def test_adapter_rejects_invalid_payloads_before_kernel():
    for payload in (None, {}, {'lab': {}, 'oracle': []},
                    {'lab': [{'ledger_id': ['bad']}], 'oracle': []},
                    {'lab': [], 'oracle': [], 'other': True}):
        with pytest.raises(ValueError):
            _adapter.evaluate(payload, None, None)


def test_unorderable_ids_raise_instead_of_inventing_sort_order():
    lab = [{'ledger_id': 1}, {'ledger_id': 'one'}]
    with pytest.raises(TypeError):
        original_diff()(lab, [])
    with pytest.raises(RuntimeError, match='invalid output'):
        diff_evidence(lab, [])


def test_production_exercise_invokes_verified_public_wrapper(monkeypatch):
    import plectis.components.evidence_diff as verified
    from microcosm_core.organs import batch8_tools_tail_primitives_capsule as organ
    original = verified.diff_evidence
    calls = []

    def spy(lab, oracle):
        calls.append((lab, oracle))
        return original(lab, oracle)

    monkeypatch.setattr(verified, 'diff_evidence', spy)
    input_dir = ROOT / 'fixtures/first_wave/batch8_tools_tail_primitives_capsule/input'
    result = organ._exercise_observer_diff(organ._source_rows(input_dir, ROOT), ROOT)
    assert result['status'] == 'pass'
    assert result['source_execution_relation'] == 'verified_evidence_core_and_copied_prediction_body'
    assert len(calls) == 1


def test_negative_exercise_uses_verified_wrapper(monkeypatch):
    import plectis.components.evidence_diff as verified
    from microcosm_core.organs import batch8_tools_tail_primitives_capsule as organ
    original = verified.diff_evidence
    calls = []

    def spy(lab, oracle):
        calls.append((lab, oracle))
        return original(lab, oracle)

    monkeypatch.setattr(verified, 'diff_evidence', spy)
    fixture = ROOT / 'fixtures/first_wave/batch8_tools_tail_primitives_capsule/input'
    case = 'observer_diff_malformed_key_skipped'
    result = organ.evaluate_negative_case(case, fixture, organ.EXPECTED_NEGATIVE_CASES[case])
    assert result['status'] == 'blocked'
    assert result['error_codes'] == list(organ.EXPECTED_NEGATIVE_CASES[case])
    assert len(calls) == 1


def test_production_evidence_failure_propagates_without_frozen_source_fallback(monkeypatch):
    import plectis.components.evidence_diff as verified
    from microcosm_core.organs import batch8_tools_tail_primitives_capsule as organ

    def failed(_lab, _oracle):
        raise RuntimeError('verified evidence unavailable')

    monkeypatch.setattr(verified, 'diff_evidence', failed)
    input_dir = ROOT / 'fixtures/first_wave/batch8_tools_tail_primitives_capsule/input'
    with pytest.raises(RuntimeError, match='verified evidence unavailable'):
        organ._exercise_observer_diff(organ._source_rows(input_dir, ROOT), ROOT)
