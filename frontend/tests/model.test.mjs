// The map's model and the wording layer, from controlled responses.
import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from '../src/data.js';
import { availabilityWords, classWords, lastRunWords, moduleWords, stateWords } from '../src/evidence.js';
import { arrange, spreadKernels, threadAngle, R } from '../src/map/layout.js';

const summary = (id, family, cls, subclaims = []) => ({
  organ_id: id, title: id.replace(/_/g, ' '), summary: `${id} summary`, claim_id: `claim::${id}`,
  classification: { family, evidence_class: cls, truth_accounting_bucket: 'real_runtime_receipt' }, formal_subclaim_ids: subclaims,
});
const proof = (name, sub, tasks) => ({
  proof: { proof_id: `proof::dafny::${name}`, module: name, retained_verification: { verified_tasks: tasks, dafny_version: '4.11.0+x' }, negative_controls: [{ source_ref: 'a.dfy' }], generated_refs: ['g.py'], current_binding: { status: 'current_hash_binding_pass' } },
  modeled_contracts: [{ subclaim_id: sub, statement: 'S', requirements_review: { status: 'unrecorded' } }],
});

test('components join their kernels through the subclaim, and wiring is kept once', () => {
  const model = build({
    revision: 'r1',
    meta: {},
    coverage: {},
    summaries: [
      summary('a', 'formal_math_and_proof', 'bounded_runtime_computation', ['subclaim::k']),
      summary('b', 'formal_math_and_proof', 'semantic_validator'),
      summary('c', 'entry_and_reveal', 'mystery_class'),
    ],
    proofs: [proof('K', 'subclaim::k', 7)],
    perComponent: [
      { id: 'a', receipts: [{ ref: 'r/a.json', availability: 'available' }], wires: ['b', 'zzz'] },
      { id: 'b', receipts: [{ ref: 'r/b.json', availability: 'unavailable', reason: 'not included in this checkout' }], wires: ['a'] },
      { id: 'c', receipts: [], wires: [] },
    ],
    details: [{ component_id: 'a', claim: { card: { assurance_facets: { generated_runtime_binding: { consumer_refs: ['src/a.py#run'] } } } } }],
  });
  assert.equal(model.byId.get('a').kernelId, 'proof::dafny::K');
  assert.equal(model.kernelById.get('proof::dafny::K').componentId, 'a');
  assert.deepEqual(model.kernelById.get('proof::dafny::K').consumerRefs, ['src/a.py#run']);
  assert.deepEqual(model.wires, [['a', 'b']], 'unknown ends are dropped and pairs kept once');
  assert.equal(model.byId.get('c').backing, 'unknown');
  assert.equal(model.totals.tasks, 7);
  assert.equal(model.totals.unavailable, 1);
});

test('the layout puts every family in its own sector and every kernel apart', () => {
  const comps = ['a', 'b', 'c', 'd'].map((id, i) => ({ id, title: id, family: i < 2 ? 'entry_and_reveal' : 'formal_math_and_proof', backing: 'tool' }));
  const { sectors, angleOf } = arrange(comps);
  assert.equal(sectors.length, 2);
  for (const s of sectors) for (const id of s.members) assert.ok(angleOf.get(id) > s.lo && angleOf.get(id) < s.hi);
  const spread = spreadKernels([0.1, 0.11, 0.12]);
  const gaps = spread.map((a, i) => Math.abs(a - spread[(i + 1) % spread.length]));
  assert.ok(Math.min(...gaps.slice(0, 2)) >= 96 / R.kernel - 1e-6, 'crowded kernels are pushed apart');
  assert.equal(threadAngle(0, 1, R.kernel), 0);
  assert.ok(Math.abs(threadAngle(0, 1, R.component) - 1) < 1e-9);
});

test('states are worded separately and unknown values are named, never coloured as success', () => {
  assert.match(stateWords('whole_claim', 'unknown')[0], /not been established/);
  assert.match(stateWords('whole_claim', 'unknown')[1], /not a pass/);
  assert.match(stateWords('formal_contract', 'partial')[1], /not a proof of the whole component/);
  const [text, , known] = stateWords('fresh_prover', 'ran_yesterday');
  assert.equal(known, false);
  assert.match(text, /Unrecognised value: ran_yesterday/);
  assert.match(classWords('evidence_class', 'new_class'), /Unrecognised/);
  assert.deepEqual(availabilityWords({ availability: 'unavailable', reason: 'not included in this checkout' }),
    ['Not in this snapshot. The index gives the reason: not included in this checkout.', false]);
  assert.match(lastRunWords({ recorded_status: 'pass', created_at: '2026-05-27T02:26:22+00:00' }), /27 May 2026 recorded a pass\. It is a historical record/);
  assert.equal(moduleWords('OwnershipClassification'), 'Ownership classification');
});
