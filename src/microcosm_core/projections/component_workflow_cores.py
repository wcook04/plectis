"""Build-time projections of retained workflow evidence; never invoke a prover."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import runpy
import re

_TRUSTED_ROOT = Path(__file__).resolve().parents[3]
_MAX_ARTIFACT_BYTES = 2 * 1024 * 1024


def _read(root: Path, ref: str) -> bytes:
    if not isinstance(ref, str):
        raise ValueError("invalid artifact reference")
    parts = ref.split("/")
    if not parts or any(part in ("", ".", "..") for part in parts) or Path(ref).is_absolute():
        raise ValueError("invalid artifact reference")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("artifact must not use symlinks: " + ref)
    if not path.is_file() or path.stat().st_size > _MAX_ARTIFACT_BYTES:
        raise ValueError("missing or oversized artifact: " + ref)
    data = path.read_bytes()
    if len(data) > _MAX_ARTIFACT_BYTES:
        raise ValueError("oversized artifact: " + ref)
    return data


def _metadata(root: Path, name: str) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate metadata key")
            result[key] = value
        return result
    try:
        row = json.loads(_read(root, f"formal/{name}/metadata.json"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("invalid workflow metadata") from error
    if not isinstance(row, dict) or type(row.get("verified_tasks")) is not int or row["verified_tasks"] < 1:
        raise ValueError("invalid workflow metadata shape")
    if not isinstance(row.get("generated_python"), dict) or not row["generated_python"]:
        raise ValueError("invalid generated manifest")
    for ref, digest in row["generated_python"].items():
        if not isinstance(digest, str) or re.fullmatch("[0-9a-f]{64}", digest) is None:
            raise ValueError("invalid generated digest")
        _read(root, f"src/plectis/{name}/_generated/" + ref)
    # Check the entire inventory before the trusted loader touches it.
    generated = root / f"src/plectis/{name}/_generated"
    for path in generated.rglob("*"):
        if path.is_symlink():
            raise ValueError("generated inventory must not use symlinks")
    formal = root / f"formal/{name}"
    for path in formal.rglob("*"):
        if path.is_symlink():
            raise ValueError("formal inventory must not use symlinks")
    return row


# Interpretations follow formal/README.md and each linked formal guide.
_CORES = {
    'repair': ('Repair', 'The accepted plan is the unique least propagation of invalid inputs and blocked effects through a finite topologically ordered DAG.',
               ['Finite DAG in topological order; typed root and effect masks.', 'Complete dependencies and honest replayability observations are supplied by the caller.'],
               ['Dependency discovery, callbacks, persistence, external effects and execution cost are outside the theorem.'],
               ['AcceptedPlanIsLeast', 'AcceptedPlansAreUnique'], ['src/plectis/repair/_host.py#make_plan', 'src/plectis/repair/_host.py#check_plan']),
    'compatibility': ('Replay', 'An accepted relation preserves finite allowed input traces and outputs in supplied deterministic models; replay detects exactly words with a differing allowed prefix.',
                      ['Valid finite deterministic transition models and a supplied state relation.'],
                      ['Concrete-program correspondence, parsing, policy adequacy and host search are trusted.'],
                      ['CounterexampleCheckIsExact'], ['src/plectis/compatibility/_api.py#check_certificate', 'src/plectis/compatibility/_api.py#check_counterexample']),
    'views': ('Release', 'A checked mixed report compiles to a public-only program preserving its exact ordered public trace without reading private input slots.',
              ['Well-typed environment, fixed checked program and independently supplied public/private field policy.', 'Plan, schema, constants, row membership and row order are public.'],
              ['Upstream secret-dependent plan construction, policy correctness, host decoding, timing and other side channels are outside the theorem.'],
              ['CheckedNoninterference', 'SlicePreservesTrace', 'SliceIsPublicOnly'], ['src/plectis/views/_api.py#compile_public', 'src/plectis/views/_api.py#run_public']),
    'replay': ('ReplayAdmission', 'Acceptance is equivalent to complete unique coverage of a nonempty supplied registry with matching component, input, claim-policy, source, public payload and required witness observations.',
               ['A nonempty supplied registry slice and honestly extracted host observations.'],
               ['Execution authenticity, component semantics, receipt claim adequacy and filesystem/hash observations are outside the theorem.'],
               ['AdmissionExact'], ['src/plectis/replay/_api.py#accept', 'src/microcosm_core/component_replay.py#replay_components']),
}


def _binding(root: Path, name: str) -> None:
    # Only installed repository checker code is executed, never code from root.
    checker = runpy.run_path(str(_TRUSTED_ROOT / f'scripts/check/check_{name}_kernel.py'))
    generated = root / f'src/plectis/{name}/_generated'
    if name == 'views':
        checker['bindings'].__globals__['ROOT'] = root / 'formal/views'
        checker['bindings'](generated)
    elif name == 'replay':
        checker['check_binding'](root)
    else:
        checker['check_binding'](root, generated)


def build_workflow_cores(root: Path) -> list[dict]:
    """Check deployed byte bindings and compile four bounded evidence records."""
    root = Path(root).resolve()
    rows = []
    for name, (module, statement, assumptions, limits, theorems, callers) in _CORES.items():
        metadata = _metadata(root, name)
        try:
            _binding(root, name)
        except (KeyError, TypeError, AttributeError, FileNotFoundError) as error:
            raise ValueError('invalid workflow binding metadata or missing source') from error
        base = f'formal/{name}/'
        source = metadata.get('source', 'Release.dfy')
        sources = {source: metadata.get('source_sha256', metadata.get('sources', {}).get(source))}
        if 'dependency_source' in metadata:
            sources[metadata['dependency_source']] = metadata['dependency_source_sha256']
        negatives = []
        if name == 'views':
            for control, result in metadata['negative_controls'].items():
                relative = f'negative/{control}.dfy'
                negatives.append((relative, metadata['sources'][relative], result))
        elif name == 'replay':
            negatives = [(n, metadata['negative_sha256'][n], metadata['negative_results'][n]) for n in metadata['negative_sources']]
        else:
            for prefix in ('', 'replay_', 'completeness_'):
                key = prefix + 'negative_source'
                if key in metadata:
                    negatives.append((metadata[key], metadata[key + '_sha256'], {
                        'verified_tasks': metadata[prefix + 'negative_verified_tasks'],
                        'errors': metadata[prefix + 'negative_errors']}))
        core_id = 'replay_admission' if name == 'replay' else name
        row = {'core_id': core_id, 'proof_id': 'core::dafny::' + core_id, 'language': 'dafny',
               'module': module, 'metadata_ref': base + 'metadata.json', 'guide_ref': base + 'README.md',
               'statement': statement, 'assumptions': assumptions,
               'interpretation_provenance': {'basis': 'authored summary of named formal guides and declarations',
                   'statement_refs': ['formal/README.md', base + 'README.md'],
                   'assumption_refs': [base + 'README.md'], 'limit_refs': [base + 'README.md', 'formal/README.md']},
               'limits': limits + ['Dafny/Boogie/Z3, compiler, generated runtime, Python and host remain trusted.'],
               'requirements_review': {'status': 'unrecorded'},
               'specification_refs': [base + s for s in sources],
               'entry_theorem_refs': [base + source + '#' + t for t in theorems],
               'retained_verification': {'basis': 'recorded_metadata', 'verified_tasks': metadata['verified_tasks'],
                                         'dafny_version': metadata['dafny_version'],
                                         'tasks': [], 'task_names_status': 'unrecorded'},
               'current_binding': {'status': 'current_hash_binding_pass', 'assessment_time_basis': 'index_generation_only',
                                   'source_sha256': sources, 'generated_python': metadata['generated_python'],
                                   'checker_ref': f'scripts/check/check_{name}_kernel.py'},
               'fresh_prover_result': {'status': 'not_run_by_index'},
               'generated_refs': [f'src/plectis/{name}/_generated/' + p for p in sorted(metadata['generated_python'])],
               'public_caller_refs': callers,
               'negative_controls': [{'source_ref': base + p, 'source_sha256': digest,
                                      'retained_result': {'basis': 'recorded_metadata', **result},
                                      'fresh_result': {'status': 'not_run_by_index'}} for p, digest, result in negatives]}
        row['artifact_bindings'] = [
            {'ref': ref, 'sha256': hashlib.sha256(_read(root, ref)).hexdigest()}
            for ref in sorted({'formal/README.md', row['metadata_ref'], row['guide_ref'], *row['specification_refs'],
                               *row['generated_refs'], *(n['source_ref'] for n in row['negative_controls']),
                               *(ref.split('#')[0] for ref in callers)})]
        if name == 'replay':
            from microcosm_core.runtime_shell import RUNTIME_STEPS
            row['admitted_replay_routes'] = [{'component_id': step.organ_id, 'route': step.span} for step in RUNTIME_STEPS]
            row['replay_route_basis'] = 'declared RUNTIME_STEPS; admission is conditional on observations, not a recorded successful run'
        rows.append(row)
    return rows


def build_ownership_counterexample(root: Path) -> dict:
    """Project the documented counterexample; historical decisions are illustrative."""
    root = Path(root).resolve()
    guide = 'formal/components/ownership_classification/README.md'
    test = 'tests/test_component_ownership_classification.py'
    required = [guide, test, 'formal/components/ownership_classification/OwnershipClassification.dfy']
    for path in required:
        if not (root / path).is_file():
            raise ValueError('ownership evidence missing: ' + path)
    return {
        'artifact_bindings': [{'ref': ref, 'sha256': hashlib.sha256(_read(root, ref)).hexdigest()}
                              for ref in required],
        'example_id': 'ownership_stale_before_live', 'proof_id': 'proof::dafny::ownership_classification',
        'source_refs': [guide, 'formal/components/ownership_classification/OwnershipClassification.dfy'],
        'path': 'microcosm-substrate/AGENT_ROUTES.md',
        'observations': [{'claim_id': 'old_claim', 'session_id': 'old', 'claim_state': 'stale'},
                         {'claim_id': 'live_claim', 'session_id': 'active', 'claim_state': 'live'}],
        'orders': [{'claim_ids': ['old_claim', 'live_claim'], 'previous_decision': 'stale_release',
                    'repaired_decision': 'owned_live', 'owner_session_id': 'active'},
                   {'claim_ids': ['live_claim', 'old_claim'], 'previous_decision': 'owned_live',
                    'repaired_decision': 'owned_live', 'owner_session_id': 'active'}],
        'previous_decision_basis': 'documented former first-matching-claim policy; historical executable is not run',
        'repaired_allowed_action': 'do_not_patch_from_sibling_lane',
        'closure_decision': 'owned_live_handoff',
        'closure_allowed_action': 'handoff_to_live_owner_or_wait_for_release',
        'test_refs': [test + '#test_actual_generated_and_closure_routes_protect_live_owner_in_both_orders',
                      test + '#test_production_classifier_calls_core_and_protects_later_live_claim'],
        'requirements_review': {'status': 'unrecorded'},
        'limits': ['Supplied freshness and exact path IDs; no proof of real session liveness, locks or concurrency safety.',
                   'This source-grounded example records no new test or prover execution.'],
    }
