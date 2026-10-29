// The map's model and the wording layer, from a controlled overview.
import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from '../src/data.js';
import {
  availabilityWords, callerWords, classWords, fileWords, lastRunWords, moduleWords, recordWords, setLabels, sourceHref, stateWords,
} from '../src/evidence.js';
import { plainLead } from '../src/markdown.js';
import { arrange, spreadKernels, threadAngle, R, KEY_GAP } from '../src/map/layout.js';

const component = (id, family, cls, extra = {}) => ({
  organ_id: id, title: id.replace(/_/g, ' '), summary: `${id} summary`, claim_id: `claim::${id}`,
  classification: { family, evidence_class: cls, truth_accounting_bucket: 'real_runtime_receipt' },
  formal_subclaim_ids: [], proof_ids: [], receipt_refs: [], wires_to: [], doctrine_ref_ids: [], route_ids: [], ...extra,
});
const kernelView = (name, componentId, tasks) => ({
  component_ids: [componentId], claim_ids: [`claim::${componentId}`],
  proof: {
    proof_id: `proof::dafny::${name}`, module: name,
    retained_verification: { verified_tasks: tasks, dafny_version: '4.11.0+x' },
    negative_controls: [{ source_ref: 'formal/x/negative/A.dfy', retained_result: { errors: 2, verified_tasks: 5 } }],
    excerpts: [{ ref: 'formal/x/K.dfy#Spec', kind: 'predicate', name: 'Spec', line_start: 3, line_end: 5, text: 'predicate Spec() { true }\n' }],
    generated_refs: ['src/x/_generated/K.py'], current_binding: { status: 'current_hash_binding_pass' },
  },
  modeled_contracts: [{ subclaim_id: `subclaim::${name}`, statement: 'S', requirements_review: { status: 'unrecorded' } }],
});
const overview = () => ({
  components: [
    component('a', 'formal_math_and_proof', 'bounded_runtime_computation', {
      proof_ids: ['proof::dafny::K'], wires_to: ['b', 'zzz'], doctrine_ref_ids: ['AX-1'],
      receipt_refs: [{ ref: 'receipts/a.json', availability: 'available', summary: { created_at: '2026-05-27T02:26:22+00:00', date_status: 'recorded', recorded_fields: { status: 'pass' } } }],
    }),
    component('b', 'formal_math_and_proof', 'semantic_validator', {
      wires_to: ['a'], receipt_refs: [{ ref: 'state/b.json', availability: 'unavailable', reason: 'source_unavailable' }],
    }),
    component('c', 'entry_and_reveal', 'mystery_class'),
  ],
  kernels: [kernelView('K', 'a', 7)],
  cores: [],
  coverage: { component_presence: { retained_proof_metadata: { component_ids: ['a'] }, configured_replay_routes: { component_ids: ['a', 'b', 'c'] } } },
  explorer: {
    cores: [{ core_id: 'replay_admission', proof_id: 'core::dafny::replay_admission', module: 'ReplayAdmission', statement: 'R', guide_ref: 'formal/replay/README.md',
      retained_verification: { verified_tasks: 16 }, negative_controls: [], public_caller_refs: ['src/plectis/replay/_api.py#accept'],
      admitted_replay_routes: [{ component_id: 'a', route: 'a.validate' }] }],
    doctrine: { nodes: [{ id: 'AX-1', kind: 'axiom', title: 'Derivation before assertion' }], edges: [] },
    typed_relations: { edges: [{ from_id: 'b', to_id: 'a', kind: 'imports_runner', source_ref: 'src/b.py#L3', line: 3 }] },
    source_revision: { status: 'recorded', exact_source_links: true, repository: 'https://github.com/wcook04/plectis', commit: 'a'.repeat(40) },
    component_filters: { family: [{ value: 'formal_math_and_proof', label: 'Formal Math & Proof', description: 'd', component_count: 2 }] },
  },
});

test('the overview joins kernels, cores, checks, records and links into one model', () => {
  const model = build(overview(), 'r1');
  assert.equal(model.byId.get('a').kernelId, 'proof::dafny::K');
  assert.equal(model.kernelById.get('proof::dafny::K').componentId, 'a');
  assert.equal(model.kernelById.get('proof::dafny::K').excerpts[0].lineStart, 3);
  assert.equal(model.kernelById.get('proof::dafny::K').mutants[0].errors, 2);
  assert.deepEqual(model.wires, [['a', 'b']], 'unknown ends are dropped and pairs kept once');
  assert.equal(model.byId.get('c').backing, 'unknown');
  assert.equal(model.byId.get('a').checks.proof, true);
  assert.equal(model.byId.get('b').checks.proof, false);
  assert.equal(model.byId.get('c').checks.replay, true);
  assert.equal(model.byId.get('a').checks.whole, null, 'whole-claim coverage is unknown, never true or false');
  assert.equal(model.byId.get('a').replayRoute, 'a.validate');
  assert.equal(model.byId.get('a').receipts[0].status, 'pass');
  assert.equal(model.byId.get('b').importsOut[0].to, 'a');
  assert.equal(model.coreById.get('replay_admission').admitted.length, 1);
  assert.equal(model.links.proofIdOfDir.get('replay'), 'core::dafny::replay_admission');
  assert.equal(model.links.proofIdOfDir.get('K'), 'proof::dafny::K');
  assert.equal(model.totals.tasks, 7);
  assert.equal(model.totals.coreTasks, 16);
  assert.equal(model.totals.unavailable, 1);
  assert.equal(model.doctrine.get('AX-1').title, 'Derivation before assertion');
});

test('an old index without the explorer extension still builds', () => {
  const data = overview();
  delete data.explorer;
  const model = build(data, 'r2');
  assert.equal(model.cores.length, 0);
  assert.equal(model.source, null);
  assert.equal(model.doctrine.size, 0);
});

test('source links go to the recorded commit, and never for state or unsafe paths', () => {
  const source = { repository: 'https://github.com/wcook04/plectis', commit: 'b'.repeat(40) };
  assert.equal(sourceHref(source, 'formal/x/K.dfy#Spec', [3, 5]), `https://github.com/wcook04/plectis/blob/${'b'.repeat(40)}/formal/x/K.dfy#L3-L5`);
  assert.equal(sourceHref(source, 'state/private.json'), null);
  assert.equal(sourceHref(source, '../escape.py'), null);
  assert.equal(sourceHref(null, 'formal/x/K.dfy'), null);
});

test('the layout puts every family in its own sector, leaves the key wedge open and keeps kernels apart', () => {
  const comps = ['a', 'b', 'c', 'd'].map((id, i) => ({ id, title: id, family: i < 2 ? 'entry_and_reveal' : 'formal_math_and_proof', backing: 'tool' }));
  const { sectors, angleOf } = arrange(comps);
  assert.equal(sectors.length, 2);
  for (const s of sectors) for (const id of s.members) assert.ok(angleOf.get(id) > s.lo && angleOf.get(id) < s.hi);
  const top = -Math.PI / 2;
  for (const s of sectors) assert.ok(s.lo >= top + KEY_GAP / 2 - 1e-9 && s.hi <= top + Math.PI * 2 - KEY_GAP / 2 + 1e-9, 'the wedge at the top holds no family');
  const spread = spreadKernels([0.1, 0.11, 0.12]);
  const gaps = spread.map((a, i) => Math.abs(a - spread[(i + 1) % spread.length]));
  assert.ok(Math.min(...gaps.slice(0, 2)) >= 96 / R.kernel - 1e-6, 'crowded kernels are pushed apart');
  assert.equal(threadAngle(0, 1, R.kernel), 0);
  assert.ok(Math.abs(threadAngle(0, 1, R.component) - 1) < 1e-9);
});

test('states are worded separately and unknown values are named, never coloured as success', () => {
  assert.match(stateWords('whole_claim', 'unknown')[0], /Nobody has worked out/);
  assert.match(stateWords('whole_claim', 'unknown')[1], /not a pass/);
  assert.match(stateWords('formal_contract', 'partial')[1], /outside that proof/);
  const [text, , known] = stateWords('fresh_prover', 'ran_yesterday');
  assert.equal(known, false);
  assert.match(text, /Unrecognised value: ran_yesterday/);
  setLabels({ evidence_class: [{ value: 'algorithmic_projection', label: 'Algorithmic projection', description: 'd' }] });
  assert.equal(classWords('evidence_class', 'algorithmic_projection'), 'Algorithmic projection');
  assert.match(classWords('evidence_class', 'new_class'), /Unrecognised/, 'a labelled facet names an unlabelled value as unrecognised');
  assert.equal(classWords('bucket_without_labels', 'real_runtime_receipt'), 'Real runtime receipt');
  assert.deepEqual(availabilityWords({ availability: 'unavailable', reason: 'not_included' }), ['Missing from this snapshot (not included).', false]);
  assert.match(lastRunWords({ recorded_status: 'pass', created_at: '2026-05-27T02:26:22+00:00' }), /27 May 2026, passed\. It is an old result/);
  assert.equal(recordWords({ availability: 'available', status: 'pass', createdAt: '2026-05-27T02:26:22+00:00' }), 'Passed on 27 May 2026.');
  assert.equal(moduleWords('OwnershipClassification'), 'Ownership classification');
  assert.equal(fileWords('src/plectis/components/_sealed_kernel.py'), 'sealed kernel');
  assert.deepEqual(callerWords('src/plectis/repair/_host.py#make_plan'), { api: 'plectis.repair', fn: 'make_plan' });
});

test('a write-up\'s plain lead is read from its opening block quote', () => {
  assert.equal(plainLead('# T\n\n> **In plain terms.** One. Two\n> three.\n\nBody.'), 'One. Two three.');
  assert.equal(plainLead('# T\n\n> A quotation.\n\nBody.'), null);
  assert.equal(plainLead('# T\n\nNo lead.'), null);
});
