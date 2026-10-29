"""Pure-data validation and narrowly scoped source-text masking for the explorer.

No files or build helpers are read. Source membership is checked at build time;
this reader checks the retained source identity and internal excerpt digests.
"""
from __future__ import annotations
import copy
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import PurePosixPath
import re

from microcosm_core.component_api_contract import MAX_GUIDE_BYTES, MAX_PLAIN_BYTES, MAX_GUIDES_BYTES

SCHEMA = 'plectis_component_explorer_v1'
_HASH = re.compile(r'[a-f0-9]{64}\Z')
_SECRET = re.compile(r'sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY')
# Unlike the generic prose guard, slash operators and comments are permitted.
_PRIVATE = re.compile(r'(?<![\w/])/(?:Users|home|Volumes|private|etc|var|root|opt|mnt|proc|sys)(?:/|\b)|(?<!\w)[A-Za-z]:[\\/]|\\\\[A-Za-z0-9]|\bfile:|~/', re.I)
_BODY_KEYS = {'source_body', 'source_text', 'docstring', 'raw_source', 'raw_body', 'code_body'}


def _require(ok, message='invalid component explorer'):
    if not ok:
        raise ValueError(message)


def _keys(value, keys):
    _require(type(value) is dict and set(value) == set(keys), 'invalid explorer fields')


def _text(value, limit=4000):
    _require(type(value) is str and len(value.encode('utf-8')) <= limit, 'unbounded explorer text')
    _require(not _SECRET.search(value) and not _PRIVATE.search(value), 'private text in explorer')


def _hash(value):
    _require(type(value) is str and bool(_HASH.fullmatch(value)), 'invalid explorer hash')


def _int(value, minimum=0, maximum=100000):
    _require(type(value) is int and minimum <= value <= maximum, 'invalid explorer count')


def _ref(value):
    _text(value, 500)
    path = value.split('#')[0].split('::')[0]
    pure = PurePosixPath(path)
    _require(bool(path) and str(pure) == path and not pure.is_absolute() and '..' not in pure.parts
             and '\\' not in path and ':' not in path and not any(ord(c) < 32 for c in value),
             'invalid explorer reference')
    return path


def _list(value, maximum=1000):
    _require(type(value) is list and len(value) <= maximum, 'unbounded explorer list')


def _refs(value, maximum=1000):
    _list(value, maximum)
    for ref in value:
        _ref(ref)
    _require(len(value) == len(set(value)), 'duplicate explorer reference')


def _tree(value, depth=0):
    _require(depth <= 12, 'explorer nesting limit')
    if type(value) is str:
        _text(value, 30000)
    elif type(value) is dict:
        _require(len(value) <= 1000 and not set(value) & _BODY_KEYS, 'unbounded explorer object')
        for key, child in value.items():
            _text(key, 500)
            _tree(child, depth + 1)
    elif type(value) is list:
        _list(value, 1000)
        for child in value:
            _tree(child, depth + 1)
    else:
        _require(value is None or type(value) in (int, bool), 'invalid explorer scalar')


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _proof_detail(detail, proof, specification_refs):
    _keys(detail, {'excerpts', 'retained_verification_details', 'negative_control_details'})
    rows = detail['excerpts']
    _list(rows, 32)
    expected = set(specification_refs + proof['entry_theorem_refs'])
    _require(len(rows) == len(expected), 'missing proof excerpts')
    seen = set()
    prefix = proof['metadata_ref'].rsplit('/', 1)[0] + '/'
    source_paths = set()
    for row in rows:
        _keys(row, {'ref', 'kind', 'name', 'line_start', 'line_end', 'text', 'source_sha256', 'text_sha256'})
        _ref(row['ref'])
        _require(row['ref'] in expected and row['ref'] not in seen and row['ref'].startswith(prefix), 'unbound excerpt reference')
        seen.add(row['ref'])
        source_paths.add(row['ref'].split('#')[0])
        _require(row['ref'].endswith('#' + row['name']) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', row['name']), 'invalid excerpt name')
        _require(row['kind'] in {'function', 'predicate', 'lemma', 'method'}, 'invalid excerpt kind')
        _int(row['line_start'], 1)
        _int(row['line_end'], row['line_start'], row['line_start'] + 299)
        _text(row['text'], 24 * 1024)
        _require(len(row['text'].splitlines()) == row['line_end'] - row['line_start'] + 1, 'excerpt line mismatch')
        _hash(row['source_sha256'])
        _hash(row['text_sha256'])
        _require(row['source_sha256'] == proof['current_binding']['source_sha256'], 'excerpt source hash mismatch')
        _require(hashlib.sha256(row['text'].encode()).hexdigest() == row['text_sha256'], 'excerpt text hash mismatch')
    _require(len(source_paths) == 1, 'mixed excerpt sources')
    retained = detail['retained_verification_details']
    _keys(retained, {'tasks', 'tasks_availability', 'tasks_reason'})
    _require(retained['tasks'] == [] and retained['tasks_availability'] == 'unrecorded', 'invented retained tasks')
    _text(retained['tasks_reason'])
    negatives = detail['negative_control_details']
    _require(type(negatives) is dict, 'invalid negative controls')
    expected_controls = {row['source_ref']: row for row in proof['negative_controls']}
    _require(set(negatives) == set(expected_controls), 'negative-control coverage mismatch')
    for ref, row in negatives.items():
        _ref(ref)
        _hash(expected_controls[ref]['source_sha256'])
        _require(ref.startswith(prefix + 'negative/'), 'unbound negative source')
        _keys(row, {'changed_lines', 'description', 'description_basis', 'changed_lines_sha256'})
        _text(row['description'], 8000)
        _require(row['description'].startswith('Replaces ') and row['description'].endswith('.'), 'invalid mutation description')
        _require(row['description_basis'] == 'retained_mutation_recipe', 'invalid mutation description basis')
        _list(row['changed_lines'], 64)
        _require(bool(row['changed_lines']), 'empty mutation diff')
        previous = 0
        for change in row['changed_lines']:
            _keys(change, {'line', 'original', 'mutated'})
            _int(change['line'], previous + 1)
            previous = change['line']
            _require(change['original'] != change['mutated'], 'unchanged mutation line')
            for field in ('original', 'mutated'):
                if change[field] is not None:
                    _text(change[field], 4000)
                    _require('\n' not in change[field] and '\r' not in change[field], 'multiline mutation line')
        _hash(row['changed_lines_sha256'])
        _require(_digest(row['changed_lines']) == row['changed_lines_sha256'], 'mutation diff hash mismatch')
    _require(len(json.dumps(detail, ensure_ascii=False).encode()) <= 160 * 1024, 'proof enrichment limit')


def _manifest(rows):
    _list(rows, 32)
    result = {}
    for row in rows:
        _keys(row, {'ref', 'sha256'})
        _ref(row['ref'])
        _hash(row['sha256'])
        _require(row['ref'] not in result, 'duplicate artifact binding')
        result[row['ref']] = row['sha256']
    return result


def _cores(rows, component_ids):
    _list(rows, 4)
    _require(len(rows) == 4, 'missing workflow cores')
    seen = set()
    for row in rows:
        extra = {'admitted_replay_routes', 'replay_route_basis'} if row.get('core_id') == 'replay_admission' else set()
        _keys(row, {'core_id', 'proof_id', 'language', 'module', 'metadata_ref', 'guide_ref', 'statement', 'assumptions', 'limits', 'requirements_review', 'specification_refs', 'entry_theorem_refs', 'retained_verification', 'current_binding', 'fresh_prover_result', 'generated_refs', 'public_caller_refs', 'negative_controls', 'artifact_bindings', 'interpretation_provenance'} | extra)
        core = row['core_id']
        _require(core in {'repair', 'compatibility', 'views', 'replay_admission'} and core not in seen, 'invalid core identity')
        seen.add(core)
        _text(row['module'], 100)
        _text(row['statement'], 4000)
        for field in ('assumptions', 'limits'):
            _list(row[field], 16)
            _require(bool(row[field]), 'missing core limits or assumptions')
            for text in row[field]:
                _text(text, 4000)
        name = 'replay' if core == 'replay_admission' else core
        base = 'formal/' + name + '/'
        _require(row['proof_id'] == 'core::dafny::' + core and row['language'] == 'dafny', 'invalid core proof identity')
        _require(row['metadata_ref'] == base + 'metadata.json' and row['guide_ref'] == base + 'README.md', 'invalid core owners')
        for field in ('specification_refs', 'entry_theorem_refs', 'generated_refs', 'public_caller_refs'):
            _refs(row[field], 32)
        retained = row['retained_verification']
        _keys(retained, {'basis', 'verified_tasks', 'dafny_version', 'tasks', 'task_names_status'})
        _require(retained['basis'] == 'recorded_metadata' and retained['tasks'] == [] and retained['task_names_status'] == 'unrecorded', 'invented core tasks')
        _int(retained['verified_tasks'], 1)
        _text(retained['dafny_version'], 200)
        _require(row['fresh_prover_result'] == {'status': 'not_run_by_index'}, 'invented core execution')
        binding = row['current_binding']
        _keys(binding, {'status', 'assessment_time_basis', 'source_sha256', 'generated_python', 'checker_ref'})
        _require(binding['status'] == 'current_hash_binding_pass' and binding['assessment_time_basis'] == 'index_generation_only', 'invalid core binding basis')
        _require(binding['checker_ref'] == f'scripts/check/check_{name}_kernel.py', 'invalid core checker')
        manifest = _manifest(row['artifact_bindings'])
        provenance = row['interpretation_provenance']
        _keys(provenance, {'basis', 'statement_refs', 'assumption_refs', 'limit_refs'})
        _require(provenance['basis'] == 'authored summary of named formal guides and declarations', 'invalid core interpretation basis')
        provenance_refs = set()
        for field in ('statement_refs', 'assumption_refs', 'limit_refs'):
            _refs(provenance[field], 8)
            _require(bool(provenance[field]), 'missing interpretation provenance')
            provenance_refs.update(provenance[field])
        required = provenance_refs | {row['metadata_ref'], row['guide_ref'], *row['specification_refs'], *row['generated_refs'], *(r.split('#')[0] for r in row['public_caller_refs'])}
        for filename, digest in binding['source_sha256'].items():
            _require(manifest.get(base + filename) == digest, 'core source manifest mismatch')
            _hash(digest)
        _require(set(row['specification_refs']) == {base + f for f in binding['source_sha256']}, 'core source coverage mismatch')
        generated = {f'src/plectis/{name}/_generated/' + f: h for f, h in binding['generated_python'].items()}
        _require(set(generated) == set(row['generated_refs']), 'core generated coverage mismatch')
        for ref, digest in generated.items():
            _hash(digest)
            _require(manifest.get(ref) == digest, 'core generated manifest mismatch')
        _list(row['negative_controls'], 16)
        for control in row['negative_controls']:
            _keys(control, {'source_ref', 'source_sha256', 'retained_result', 'fresh_result'})
            _ref(control['source_ref'])
            _require(control['source_ref'].startswith(base + 'negative/'), 'invalid core negative source')
            _hash(control['source_sha256'])
            _require(manifest.get(control['source_ref']) == control['source_sha256'], 'core negative manifest mismatch')
            required.add(control['source_ref'])
            _keys(control['retained_result'], {'basis', 'verified_tasks', 'errors'} | ({'exit_code'} if name == 'views' else set()))
            if name == 'views':
                _int(control['retained_result']['exit_code'], 1, 255)
            _require(control['retained_result']['basis'] == 'recorded_metadata' and control['fresh_result'] == {'status': 'not_run_by_index'}, 'invented negative execution')
            _int(control['retained_result']['verified_tasks'])
            _int(control['retained_result']['errors'], 1)
        _require(set(manifest) == required, 'core artifact coverage mismatch')
        for ref in row['entry_theorem_refs']:
            _require(ref.split('#')[0] in row['specification_refs'] and '#' in ref, 'unbound core theorem')
        if extra:
            _list(row['admitted_replay_routes'], 200)
            for route in row['admitted_replay_routes']:
                _keys(route, {'component_id', 'route'})
                _require(route['component_id'] in component_ids, 'unknown admitted component')


_DOCTRINE_SOURCES = ['AXIOMS.md', 'PRINCIPLES.md', 'ANTI_PRINCIPLES.md', 'core/axiom_organ_routing.json', 'core/doctrine_enrichment.json']


def _reader(value, component_ids):
    _keys(value, {'basis', 'source_ref', 'plain', 'analogy', 'why_it_matters', 'potential_misread', 'governs',
                  'requires', 'refuses', 'example', 'counterexample', 'enforced_in_component_ids', 'does_not_prove'})
    _require(value['basis'] == 'authored_reader_enrichment' and value['source_ref'] == 'core/doctrine_enrichment.json',
             'invalid doctrine reader basis')
    for field in ('plain', 'why_it_matters', 'potential_misread', 'governs', 'requires', 'refuses', 'counterexample', 'does_not_prove'):
        _text(value[field], 1200)
    analogy = value['analogy']
    _keys(analogy, {'text', 'maps', 'boundary'})
    _text(analogy['text'], 1200)
    _text(analogy['boundary'], 1200)
    _list(analogy['maps'], 16)
    for row in analogy['maps']:
        _keys(row, {'doctrine', 'analogy'})
        _text(row['doctrine'], 1200)
        _text(row['analogy'], 1200)
    _keys(value['example'], {'text', 'component_ids'})
    _text(value['example']['text'], 1200)
    _components(value['example']['component_ids'], component_ids)
    _components(value['enforced_in_component_ids'], component_ids)
_DOCTRINE_ID = {'axiom': re.compile(r'AX-[0-9]{1,3}\Z'), 'principle': re.compile(r'P-[0-9]{1,3}\Z'),
                'anti_principle': re.compile(r'AP-[0-9]{1,3}\Z')}


def _strings(value, limit=500, maximum=32):
    _list(value, maximum)
    for item in value:
        _text(item, limit)


def _components(value, component_ids):
    _strings(value, 200)
    _require(set(value) <= component_ids and len(value) == len(set(value)), 'unknown witness component')


def _axiom(value, axiom_id, component_ids):
    _keys(value, {'formal_clause', 'lineage', 'anti_axiom', 'routing', 'obligations', 'support'})
    _text(value['formal_clause'], 1000)
    _strings(value['lineage'], 200)
    _text(value['anti_axiom'], 200)
    routing = value['routing']
    _keys(routing, {'basis', 'source_ref', 'witness_strength', 'witness_component_ids', 'witness_surfaces', 'negative_case_codes'})
    _require(routing['basis'] == 'authored_routing_registry'
             and routing['source_ref'] == f'core/axiom_organ_routing.json::rows[{axiom_id}]', 'invalid axiom routing basis')
    _text(routing['witness_strength'], 100)
    _components(routing['witness_component_ids'], component_ids)
    _refs(routing['witness_surfaces'], 32)
    _strings(routing['negative_case_codes'], 200)
    _list(value['obligations'], 16)
    _require(bool(value['obligations']), 'missing axiom obligations')
    seen = set()
    for item in value['obligations']:
        _keys(item, {'obligation_id', 'predicate', 'required', 'declared_status', 'computed_status',
                     'witness_component_ids', 'witness_surfaces', 'negative_case_codes', 'witness_gaps'})
        _text(item['obligation_id'], 200)
        _require(item['obligation_id'].startswith(axiom_id + '.O') and item['obligation_id'] not in seen, 'invalid axiom obligation')
        seen.add(item['obligation_id'])
        _text(item['predicate'], 1000)
        _require(type(item['required']) is bool, 'invalid obligation requirement')
        for field in ('declared_status', 'computed_status'):
            _text(item[field], 200)
        _components(item['witness_component_ids'], component_ids)
        _refs(item['witness_surfaces'], 32)
        _strings(item['negative_case_codes'], 200)
        _strings(item['witness_gaps'], 200, 16)
    support = value['support']
    _keys(support, {'basis', 'checker_id', 'verdict', 'hand_stamped_witness_strength',
                    'hand_stamped_strong_not_certifiable', 'strong_blocked_reasons'})
    _require(support['basis'] == 'index_time_computed', 'invalid axiom support basis')
    for field, limit in (('checker_id', 200), ('verdict', 200), ('hand_stamped_witness_strength', 100)):
        _text(support[field], limit)
    _require(type(support['hand_stamped_strong_not_certifiable']) is bool, 'invalid hand-stamp flag')
    _strings(support['strong_blocked_reasons'], 500, 16)


def _doctrine(doctrine, component_ids):
    _keys(doctrine, {'schema_version', 'sources', 'nodes', 'edges'})
    _require(doctrine['schema_version'] == 'plectis_explorer_doctrine_v2', 'invalid doctrine schema')
    _require(type(doctrine['sources']) is list and [r.get('ref') if type(r) is dict else None
             for r in doctrine['sources']] == _DOCTRINE_SOURCES, 'invalid doctrine sources')
    _manifest(doctrine['sources'])
    _list(doctrine['nodes'], 200)
    _list(doctrine['edges'], 1000)
    ids = {}
    for node in doctrine['nodes']:
        base = {'id', 'title', 'plain', 'kind', 'source_ref', 'statement', 'statement_sha256', 'reader'}
        _require(type(node) is dict, 'invalid doctrine node')
        _keys(node, base | ({'axiom'} if node.get('kind') == 'axiom' else set()))
        _require(node['kind'] in _DOCTRINE_ID and type(node['id']) is str and node['id'] not in ids
                 and bool(_DOCTRINE_ID[node['kind']].fullmatch(node['id'])), 'invalid doctrine node')
        for field in ('id', 'title', 'plain'):
            _text(node[field], 1200)
        ids[node['id']] = node['kind']
        _ref(node['source_ref'])
        source = {'axiom': 'AXIOMS.md', 'principle': 'PRINCIPLES.md', 'anti_principle': 'ANTI_PRINCIPLES.md'}[node['kind']]
        _require(node['source_ref'] == source + '::' + node['id'], 'invalid doctrine source reference')
        _text(node['statement'], 4000)
        _require(bool(node['statement'].strip()), 'empty doctrine statement')
        _hash(node['statement_sha256'])
        _require(hashlib.sha256(node['statement'].encode('utf-8')).hexdigest() == node['statement_sha256'],
                 'doctrine statement hash mismatch')
        _reader(node['reader'], component_ids)
        if node['kind'] == 'axiom':
            _axiom(node['axiom'], node['id'], component_ids)
    for edge in doctrine['edges']:
        _keys(edge, {'from_id', 'to_id', 'kind', 'source_ref'})
        _require(edge['from_id'] in ids and edge['to_id'] in ids and edge['kind'] in {'rests_on', 'violates'}, 'invalid doctrine edge')
        expected = 'principle' if edge['kind'] == 'rests_on' else 'anti_principle'
        _require(ids[edge['from_id']] == expected and ids[edge['to_id']] == 'axiom', 'invalid doctrine edge endpoints')
        _ref(edge['source_ref'])


def _metadata(row, component_ids):
    _keys(row, {'component_filters', 'doctrine', 'source_revision', 'typed_relations', 'receipt_summaries'})
    filters = row['component_filters']
    _keys(filters, {'family', 'evidence_class', 'truth_accounting_bucket', 'real_substrate_disposition'})
    for rows in filters.values():
        _list(rows, 100)
        for item in rows:
            _keys(item, {'value', 'label', 'description', 'component_count', 'label_basis'})
            for field in ('value', 'label', 'description'):
                _text(item[field], 1200)
            _int(item['component_count'], 0, len(component_ids))
            _require(item['label_basis'] in {'authored_owner', 'identifier_words'}, 'invalid label basis')
    _doctrine(row['doctrine'], component_ids)
    revision = row['source_revision']
    _keys(revision, {'status', 'commit', 'dirty', 'repository', 'exact_source_links'})
    _require(revision['status'] in {'recorded', 'unknown'} and type(revision['exact_source_links']) is bool, 'invalid source revision')
    if revision['status'] == 'recorded':
        _require(type(revision['commit']) is str and re.fullmatch(r'[a-f0-9]{40,64}', revision['commit']) and type(revision['dirty']) is bool, 'invalid recorded revision')
    else:
        _require(revision['commit'] is None and revision['dirty'] is None and not revision['exact_source_links'], 'invented source revision')
    _require(revision['repository'] is None or re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', revision['repository']), 'invalid source repository')
    _require(not revision['exact_source_links'] or revision['status'] == 'recorded' and revision['dirty'] is False and revision['repository'] is not None, 'unbound source links')
    relations = row['typed_relations']
    _keys(relations, {'status', 'edges', 'unavailable_component_ids', 'reason'})
    _require(relations['status'] in {'observed', 'partially_observed'}, 'invalid import observation')
    _list(relations['edges'], 1000)
    for edge in relations['edges']:
        _keys(edge, {'from_id', 'to_id', 'kind', 'source_ref', 'line', 'source_sha256'})
        _require(edge['from_id'] in component_ids and edge['to_id'] in component_ids and edge['kind'] == 'imports_runner', 'invalid typed relation')
        _int(edge['line'], 1)
        _ref(edge['source_ref'])
        _require(edge['source_ref'].endswith('#L' + str(edge['line'])), 'import source line mismatch')
        _hash(edge['source_sha256'])
    _list(relations['unavailable_component_ids'], 200)
    _require(set(relations['unavailable_component_ids']) <= component_ids, 'unknown unavailable component')
    _list(row['receipt_summaries'], 1000)
    for summary in row['receipt_summaries']:
        _keys(summary, {'ref', 'availability', 'created_at', 'date_status', 'recorded_fields', 'artifact_sha256', 'availability_reason'})
        _ref(summary['ref'])
        if summary['availability'] == 'available':
            _hash(summary['artifact_sha256'])
            _require(summary['availability_reason'] is None, 'available receipt has an unavailable reason')
        else:
            _require(summary['artifact_sha256'] is None, 'invented receipt hash')
            _require(summary['availability_reason'] in {'source_unavailable', 'source_rejected'}, 'missing receipt availability reason')
        _require(summary['availability'] in {'available', 'unavailable'} and summary['date_status'] in {'recorded', 'unrecorded'}, 'invalid receipt availability')
        _require((summary['created_at'] is None) == (summary['date_status'] == 'unrecorded'), 'invented receipt date')
        if summary['created_at'] is not None:
            _text(summary['created_at'], 100)
            try:
                datetime.fromisoformat(summary['created_at'].replace('Z', '+00:00'))
            except ValueError as exc:
                raise ValueError('invalid receipt date') from exc
        _require(type(summary['recorded_fields']) is dict and set(summary['recorded_fields']) <= {'status', 'result', 'fixture_id', 'case_count', 'passed_count', 'failed_count', 'positive_case_count', 'negative_case_count', 'error_count', 'warning_count'}, 'unbounded receipt fields')
        for value in summary['recorded_fields'].values():
            _require(type(value) in (str, int, bool), 'invalid receipt scalar')
            if type(value) is str:
                _text(value, 160)


def _ownership(row, proof_ids):
    _keys(row, {'artifact_bindings', 'example_id', 'proof_id', 'source_refs', 'path', 'observations', 'orders', 'previous_decision_basis', 'repaired_allowed_action', 'closure_decision', 'closure_allowed_action', 'test_refs', 'requirements_review', 'limits'})
    _require(row['example_id'] == 'ownership_stale_before_live' and row['proof_id'] in proof_ids, 'invalid ownership identity')
    _refs(row['source_refs'], 4)
    _refs(row['test_refs'], 4)
    _ref(row['path'])
    manifest = _manifest(row['artifact_bindings'])
    _require(set(manifest) == {*row['source_refs'], *(r.split('#')[0] for r in row['test_refs'])}, 'ownership manifest mismatch')
    _list(row['observations'], 2)
    _require(len(row['observations']) == 2, 'missing ownership observations')
    for item in row['observations']:
        _keys(item, {'claim_id', 'session_id', 'claim_state'})
        _require(item['claim_state'] in {'stale', 'live'}, 'invalid ownership observation')
    claim_ids = {r['claim_id'] for r in row['observations']}
    _list(row['orders'], 2)
    _require(len(row['orders']) == 2, 'missing ownership orders')
    for order in row['orders']:
        _keys(order, {'claim_ids', 'previous_decision', 'repaired_decision', 'owner_session_id'})
        _require(len(order['claim_ids']) == 2 and set(order['claim_ids']) == claim_ids and order['repaired_decision'] == 'owned_live', 'invalid ownership order')


def _metadata_bindings(index, data):
    organs = {row['organ_id']: row for row in index['nodes']['organ']}
    facts = {row['artifact_id']: row for row in index['nodes']['artifact']}
    for field, rows in data['component_filters'].items():
        expected = Counter(row[field] for row in organs.values())
        actual = {row['value']: row['component_count'] for row in rows}
        _require(len(actual) == len(rows) and actual == expected, 'classification filter coverage mismatch')
    relations = data['typed_relations']
    unavailable = relations['unavailable_component_ids']
    _require(len(unavailable) == len(set(unavailable)), 'duplicate unavailable component')
    _require((relations['status'] == 'observed') == (not unavailable), 'typed relation status mismatch')
    seen = set()
    for edge in relations['edges']:
        identity = (edge['from_id'], edge['to_id'], edge['line'])
        _require(identity not in seen, 'duplicate typed relation')
        seen.add(identity)
        runner = organs[edge['from_id']]['runner_source_ref']
        _require(edge['source_ref'] == runner + '#L' + str(edge['line']), 'typed relation runner mismatch')
        fact = facts.get(runner, {})
        _require(fact.get('availability') == 'available' and fact.get('sha256') == edge['source_sha256'], 'typed relation source hash mismatch')
        _require(edge['from_id'] not in unavailable, 'relation from unavailable runner')
    owned = set()
    for claim in index['nodes']['claim']:
        evidence = claim['card']['evidence']
        owned.update(evidence['historical_receipt_refs'])
        owned.add(evidence['authority_receipt_ref'])
    seen = set()
    for summary in data['receipt_summaries']:
        ref = summary['ref']
        _require(ref in owned and ref not in seen, 'unowned or duplicate receipt summary')
        seen.add(ref)
        fact = facts.get(ref, {})
        if summary['availability'] == 'available':
            _require(fact.get('availability') == 'available', 'receipt availability mismatch')
            if fact.get('sha256') is not None:
                _require(summary['artifact_sha256'] == fact['sha256'], 'receipt summary hash mismatch')


def plain_lead(text):
    """Extract the first authored In plain terms block, without synthesizing prose."""
    lines = text.splitlines()
    for start, line in enumerate(lines):
        match = re.fullmatch(r'>\s*\*\*In plain terms\.\*\*\s*(.*)', line)
        if match:
            parts = [match.group(1)]
            for continuation in lines[start + 1:]:
                if not continuation.startswith('>'):
                    break
                parts.append(continuation[1:].strip())
            plain = ' '.join(' '.join(parts).split())
            _require(bool(plain), 'empty guide plain lead')
            _text(plain, MAX_PLAIN_BYTES)
            return plain
        # The lead must precede the first subsection, not be buried in examples.
        if line.startswith('## '):
            break
    return None


def _guides(index, data):
    guides = data.get('guides')
    if 'guides' not in data:
        return
    _require(type(guides) is dict and len(guides) <= 128, 'invalid guide manifest')
    _require(len(json.dumps(guides, ensure_ascii=False).encode()) <= MAX_GUIDES_BYTES, 'guide manifest byte limit')
    components = {row['ref'] for row in index['nodes']['guide']}
    proofs = {row['formal_readme_ref'] for row in index['nodes']['subclaim']}
    cores = {row['guide_ref']: next(b['sha256'] for b in row['artifact_bindings'] if b['ref'] == row['guide_ref'])
             for row in data['cores']}
    _require(set(guides) == components | proofs | set(cores), 'guide coverage mismatch')
    artifacts = {row['ref']: row for row in index['nodes']['artifact']}
    for ref, guide in guides.items():
        _keys(guide, {'ref', 'sha256', 'text', 'availability', 'plain', 'plain_availability'})
        _ref(ref)
        _require(guide['ref'] == ref and guide['availability'] == 'available', 'invalid retained guide identity')
        _require(bool(re.fullmatch(r'paper_modules/[a-z][a-z0-9_]*\.md|formal/(?:components/[a-z][a-z0-9_]*|repair|compatibility|views|replay)/README\.md', ref)), 'invalid guide owner')
        _text(guide['text'], MAX_GUIDE_BYTES)
        _hash(guide['sha256'])
        _require(hashlib.sha256(guide['text'].encode('utf-8')).hexdigest() == guide['sha256'], 'guide text hash mismatch')
        expected = cores.get(ref, artifacts.get(ref, {}).get('sha256'))
        _require(expected == guide['sha256'], 'guide source binding mismatch')
        plain = plain_lead(guide['text'])
        _require(ref not in components or plain is not None, 'component guide missing plain lead')
        _require(guide['plain'] == plain and guide['plain_availability'] == ('available' if plain else 'unrecorded'), 'guide plain lead mismatch')


def validate_explorer(index: dict) -> None:
    """Validate optional explorer data without I/O or proof execution."""
    if 'explorer' not in index:
        return
    data = index['explorer']
    allowed = {'schema_version', 'proof_details', 'cores', 'ownership_example', 'component_filters', 'doctrine', 'source_revision', 'typed_relations', 'receipt_summaries', 'requirements_reviews', 'claim_clause_coverage', 'guides'}
    _require(type(data) is dict and set(data) <= allowed and {'schema_version', 'proof_details', 'cores', 'ownership_example', 'component_filters', 'doctrine', 'source_revision', 'typed_relations', 'receipt_summaries'} <= set(data), 'invalid explorer root fields')
    _require(data['schema_version'] == SCHEMA, 'invalid explorer schema')
    _tree({key: value for key, value in data.items() if key != 'guides'})
    _require(len(json.dumps(data, ensure_ascii=False, allow_nan=False).encode()) <= 2 * 1024 * 1024, 'explorer size limit')
    proofs = {p['proof_id']: p for p in index['nodes']['proof']}
    _require(type(data['proof_details']) is dict and set(data['proof_details']) == set(proofs), 'proof-detail coverage mismatch')
    subclaims = {s['subclaim_id'].split('::')[-1]: s for s in index['nodes']['subclaim']}
    for proof_id, detail in data['proof_details'].items():
        slug = proof_id.split('::')[-1]
        _proof_detail(detail, proofs[proof_id], subclaims[slug]['specification_refs'])
    components = {o['organ_id'] for o in index['nodes']['organ']}
    _cores(data['cores'], components)
    _guides(index, data)
    _ownership(data['ownership_example'], set(proofs))
    _metadata({key: data[key] for key in ('component_filters', 'doctrine', 'source_revision', 'typed_relations', 'receipt_summaries')}, components)
    _metadata_bindings(index, data)


def public_text_view(index: dict) -> dict:
    """Return an independent copy masking only validated source-syntax fields."""
    validate_explorer(index)
    result = copy.deepcopy(index)
    for guide in result.get('explorer', {}).get('guides', {}).values():
        guide['text'] = 'VALIDATED_PUBLIC_GUIDE_TEXT'
        if guide['plain'] is not None:
            guide['plain'] = 'VALIDATED_PUBLIC_GUIDE_PLAIN'
    if result.get('explorer', {}).get('source_revision', {}).get('repository') is not None:
        result['explorer']['source_revision']['repository'] = 'VALIDATED_PUBLIC_REPOSITORY_URL'
    for detail in result.get('explorer', {}).get('proof_details', {}).values():
        for row in detail['excerpts']:
            row['text'] = 'VALIDATED_PUBLIC_DAFNY_EXCERPT'
        for row in detail['negative_control_details'].values():
            row['description'] = 'VALIDATED_RETAINED_MUTATION_DESCRIPTION'
            for change in row['changed_lines']:
                for field in ('original', 'mutated'):
                    if change[field] is not None:
                        change[field] = 'VALIDATED_PUBLIC_DAFNY_LINE'
    return result
