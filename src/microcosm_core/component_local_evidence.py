"""Explicit startup-only saved-run evidence; never execute a component or prover.

Admission rechecks supplied host observations, not their authenticity or age.
Only allowlisted detached summaries leave this loader. No caller should invoke
this loader while handling an HTTP request.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile

MAX_RUNS = 32
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
_RUN = re.compile(r'run-[A-Za-z0-9_-]{1,100}\Z')


def _path(path: Path) -> Path:
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('local evidence symlink rejected')
    return path


def _read(path: Path, budget: list[int]) -> bytes:
    path = _path(path)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_FILE_BYTES:
            raise ValueError('local evidence file bound exceeded')
        data = stream.read(MAX_FILE_BYTES + 1)
    _path(path)
    budget[0] += len(data)
    if len(data) > MAX_FILE_BYTES or budget[0] > MAX_TOTAL_BYTES:
        raise ValueError('local evidence byte bound exceeded')
    return data


def _object(data: bytes) -> dict:
    def unique(pairs):
        row = {}
        for key, value in pairs:
            if key in row:
                raise ValueError('duplicate local evidence key')
            row[key] = value
        return row
    def constant(_):
        raise ValueError('nonfinite local evidence value')
    try:
        result = json.loads(data, object_pairs_hook=unique, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('invalid local evidence JSON') from exc
    if type(result) is not dict:
        raise ValueError('local evidence must be an object')
    return result


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_local_run_evidence(root, index, directory=None) -> dict:
    """Load only an explicit directory and finish every read before returning.

    A directory contains direct run-* children, or is itself one run-* folder.
    Saved absolute receipt references must still match that original layout.
    An admission decision worker runs at startup against immutable bounded
    copies; no runner, native proof witness, model provider or prover executes.
    """
    result = {'status': 'disabled' if directory is None else 'loaded',
              'evidence_kind': 'explicit_local_saved_run', 'runs': [],
              'observation_authenticity': 'trusted_local_files_not_authenticated',
              'fresh_execution': {'status': 'not_run_by_server'},
              'assessment_time_basis': 'server_startup_only'}
    if directory is None:
        return result
    try:
        return _load(root, index, directory, result)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RuntimeError, RecursionError) as exc:
        # Neither paths, saved payloads nor raw parser/worker errors escape.
        raise ValueError('explicit local saved-run evidence rejected') from None


def _load(root, index, directory, result):
    from microcosm_core.component_index import _safe
    from microcosm_core.component_replay import (
        _json_digest, _route_policy, _validate_replay_selection, native_replay_step,
    )
    from microcosm_core.component_replay_worker import _validate_worker_replay
    from microcosm_core.runtime_shell import RUNTIME_STEPS

    root = _path(Path(root))
    base = Path(directory)
    base = _path(base if base.is_absolute() else root / base)
    if not base.is_dir():
        raise ValueError('missing explicit directory')
    if _RUN.fullmatch(base.name):
        runs = [base]
    else:
        runs = []
        # Bounded enumeration; unrelated files are not opened or recursed into.
        with os.scandir(base) as entries:
            count = 0
            for entry in entries:
                count += 1
                if count > 256:
                    raise ValueError('local evidence directory entry bound exceeded')
                if _RUN.fullmatch(entry.name):
                    if entry.is_symlink() or not entry.is_dir(follow_symlinks=False):
                        raise ValueError('invalid run directory')
                    runs.append(Path(entry.path))
                    if len(runs) > MAX_RUNS:
                        raise ValueError('local evidence run bound exceeded')
    budget = [0]
    registry_bytes = _read(root / 'core/organ_registry.json', budget)
    registry = _object(registry_bytes)['implemented_organs']
    artifacts = {row['artifact_id']: row for row in index['nodes']['artifact']}
    registry_fact = artifacts.get('core/organ_registry.json')
    if (not registry_fact or registry_fact.get('availability') != 'available'
            or registry_fact.get('sha256') != _digest(registry_bytes)):
        raise ValueError('current registry differs from indexed registry')
    index_ids = {row['organ_id'] for row in index['nodes']['organ']}
    if {row['organ_id'] for row in registry} != index_ids:
        raise ValueError('index component universe differs from current registry')
    by_id = {row['organ_id']: row for row in registry}
    for run in sorted(runs):
        _path(run)
        summary_path = run / 'component-replays.json'
        summary_bytes = _read(summary_path, budget)
        summary = _object(summary_bytes)
        ids = summary.get('selected_organ_ids')
        if type(ids) is not list or len(ids) != 1 or type(ids[0]) is not str or ids[0] not in index_ids:
            raise ValueError('invalid selected component')
        organ_id = ids[0]
        selected, full_routes = _validate_replay_selection(organ_id, RUNTIME_STEPS, registry, lambda: RUNTIME_STEPS)
        native = native_replay_step(selected)
        expected_spec = {'component_id': organ_id, 'input_ref': native.example_rel,
                         'evidence_class': str(by_id[organ_id].get('evidence_class') or by_id[organ_id].get('current_evidence_scope') or native.input_mode),
                         'claim_digest': _json_digest(_route_policy(native, by_id[organ_id])),
                         'native_kind': {'lean_proof_search_lab_runtime': 1, 'formal_math_lean_proof_witness': 2}.get(organ_id, 0)}
        if summary.get('admission', {}).get('registry_specs') != [expected_spec]:
            raise ValueError('saved registry policy differs from current policy')
        if summary.get('summary_ref') != str(summary_path):
            raise ValueError('saved summary reference mismatch')
        rows = summary.get('results')
        if type(rows) is not list or len(rows) != 1 or type(rows[0]) is not dict:
            raise ValueError('invalid saved results')
        accepted = summary['admission'].get('accepted')
        receipt_bytes = None
        if accepted is True:
            receipt_path = Path(rows[0]['receipt_ref'])
            receipt_name = native.receipt_name
            if receipt_path != run / organ_id / receipt_name:
                raise ValueError('saved receipt reference mismatch')
            receipt_bytes = _read(receipt_path, budget)
            saved = _object(receipt_bytes)
            _safe(saved)  # refuse private text, secret-shaped or source-body payloads
        # Reuse the real admission/receipt verifier against bounded immutable
        # copies. Its internal reads cannot race or expand original local files.
        with tempfile.TemporaryDirectory(prefix='plectis-local-evidence-') as temp:
            out = Path(temp)
            copied_run = out / run.name
            copied_run.mkdir()
            detached = copy.deepcopy(summary)
            detached['summary_ref'] = str(copied_run / summary_path.name)
            if receipt_bytes is not None:
                copied_receipt = copied_run / organ_id / native.receipt_name
                copied_receipt.parent.mkdir()
                copied_receipt.write_bytes(receipt_bytes)
                detached['results'][0]['receipt_ref'] = str(copied_receipt)
            Path(detached['summary_ref']).write_text(json.dumps(detached, allow_nan=False))
            _validate_worker_replay(detached, root, out, organ_id, native, full_routes)
        result['runs'].append({
            'component_id': organ_id, 'run_id': run.name, 'recorded_status': summary['status'],
            'admission': {'recorded_accepted': accepted, 'rechecked_accepted': accepted, 'basis': 'saved_host_observations'},
            'summary_sha256': _digest(summary_bytes),
            'receipt_sha256': _digest(receipt_bytes) if receipt_bytes is not None else None,
            'source_identity': summary['source_identity'],
            'current_policy_binding': 'matches_current_registry_policy',
            'indexed_registry_binding': 'matches_indexed_registry_bytes',
            'current_source_binding': {'status': 'unknown', 'reason': 'saved source inventory is not a new source observation'},
            'input_freshness': {'status': 'unknown'}, 'recorded_time': {'status': 'unrecorded'},
            'fresh_execution': {'status': 'not_run_by_server'},
        })
    validate_local_run_evidence(result, index)
    return result


def validate_local_run_evidence(value, index=None):
    """Validate detached startup evidence without any filesystem or execution."""
    from microcosm_core.component_index import _safe
    if (type(value) is not dict or set(value) != {'status', 'evidence_kind', 'runs', 'observation_authenticity', 'fresh_execution', 'assessment_time_basis'}
            or type(value['status']) is not str or value['status'] not in {'disabled', 'loaded'}
            or value['evidence_kind'] != 'explicit_local_saved_run'
            or value['observation_authenticity'] != 'trusted_local_files_not_authenticated'
            or value['fresh_execution'] != {'status': 'not_run_by_server'}
            or value['assessment_time_basis'] != 'server_startup_only'
            or type(value['runs']) is not list or len(value['runs']) > MAX_RUNS
            or (value['status'] == 'disabled' and value['runs'])):
        raise ValueError('invalid local saved-run overlay')
    component_ids = {row['organ_id'] for row in index['nodes']['organ']} if index is not None else None
    seen = set()
    fields = {'component_id', 'run_id', 'recorded_status', 'admission', 'summary_sha256', 'receipt_sha256', 'source_identity', 'current_policy_binding', 'indexed_registry_binding', 'current_source_binding', 'input_freshness', 'recorded_time', 'fresh_execution'}
    for row in value['runs']:
        if type(row) is not dict or set(row) != fields:
            raise ValueError('invalid local saved-run record')
        if (type(row['component_id']) is not str or not re.fullmatch(r'[a-z][a-z0-9_]{0,150}', row['component_id'])
                or type(row['run_id']) is not str or not _RUN.fullmatch(row['run_id']) or row['run_id'] in seen
                or type(row['recorded_status']) is not str or row['recorded_status'] not in {'pass', 'blocked'}):
            raise ValueError('invalid local saved-run identity')
        if component_ids is not None and row['component_id'] not in component_ids:
            raise ValueError('local saved-run component absent from index')
        seen.add(row['run_id'])
        accepted = row['recorded_status'] == 'pass'
        if (type(row['admission']) is not dict or row['admission'] != {'recorded_accepted': accepted, 'rechecked_accepted': accepted, 'basis': 'saved_host_observations'}
                or type(row['admission'].get('recorded_accepted')) is not bool
                or type(row['admission'].get('rechecked_accepted')) is not bool
                or row['current_policy_binding'] != 'matches_current_registry_policy'
                or row['indexed_registry_binding'] != 'matches_indexed_registry_bytes'
                or row['current_source_binding'] != {'status': 'unknown', 'reason': 'saved source inventory is not a new source observation'}
                or row['input_freshness'] != {'status': 'unknown'} or row['recorded_time'] != {'status': 'unrecorded'}
                or row['fresh_execution'] != {'status': 'not_run_by_server'}):
            raise ValueError('invalid local saved-run evidence basis')
        for key in ('summary_sha256', 'source_identity', 'receipt_sha256'):
            digest = row[key]
            if key == 'receipt_sha256' and digest is None and not accepted:
                continue
            if type(digest) is not str or not re.fullmatch(r'[0-9a-f]{64}', digest):
                raise ValueError('invalid local saved-run digest')
    _safe(value)
