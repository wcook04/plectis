// The map's model and the wording layer, from a controlled overview.
import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from '../src/data.js';
import {
  availabilityWords, callerWords, classWords, fileWords, lastRunWords, moduleWords, recordWords, setLabels, sourceHref, stateWords,
} from '../src/evidence.js';
import { plainLead, renderWriteup } from '../src/markdown.js';
import { arrange, bloomDepths, layout, R, KEY_GAP, BLOOM_ROOM } from '../src/map/layout.js';

test('write-up fences reserve command actions for explicit shell languages', (t) => {
  const originalDocument = globalThis.document, originalNode = globalThis.Node;
  class TestNode {
    constructor(tag, text = '') { this.tag = tag; this.text = text; this.children = []; this.attributes = {}; }
    append(...children) { this.children.push(...children); }
    setAttribute(key, value) { this.attributes[key] = value; }
    addEventListener() {}
    get textContent() { return this.text + this.children.map((c) => c.textContent ?? c).join(''); }
  }
  globalThis.Node = TestNode;
  globalThis.document = { createElement: (tag) => new TestNode(tag), createTextNode: (text) => new TestNode('#text', text) };
  t.after(() => { globalThis.document = originalDocument; globalThis.Node = originalNode; });
  const nodes = (node) => [node, ...node.children.flatMap((child) => child instanceof TestNode ? nodes(child) : [])];
  for (const language of ['text', 'python', 'dafny', '']) {
    const text = '<unsafe> dirty[i] = roots[i] or any(dirty[d] for d in deps[i])';
    const rendered = renderWriteup('```' + language + '\n' + text + '\n```');
    const all = nodes(rendered);
    assert.equal(all.some((n) => n.tag === 'details' || n.tag === 'button'), false, language);
    assert.equal(all.find((n) => n.tag === 'pre').textContent, text);
    assert.doesNotMatch(rendered.textContent, /Run it yourself|Copy command/);
  }
  for (const language of ['sh', 'bash', 'zsh', 'shell']) {
    const rendered = renderWriteup('```' + language + '\npython3 scripts/check.py\n```');
    assert.ok(nodes(rendered).some((n) => n.tag === 'details'));
    assert.ok(nodes(rendered).some((n) => n.tag === 'button' && n.textContent === 'Copy command'));
    assert.match(rendered.textContent, /Run it yourself/);
  }
});

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

test('the layout puts every family in its own sector, leaves the key wedge open and keeps flowers apart', () => {
  const comps = ['a', 'b', 'c', 'd'].map((id, i) => ({ id, title: id, family: i < 2 ? 'entry_and_reveal' : 'formal_math_and_proof', backing: 'tool' }));
  const { sectors, angleOf } = arrange(comps);
  assert.equal(sectors.length, 2);
  for (const s of sectors) for (const id of s.members) assert.ok(angleOf.get(id) > s.lo && angleOf.get(id) < s.hi);
  const top = -Math.PI / 2;
  for (const s of sectors) assert.ok(s.lo >= top + KEY_GAP / 2 - 1e-9 && s.hi <= top + Math.PI * 2 - KEY_GAP / 2 + 1e-9, 'the wedge at the top holds no family');
  // Placement uses true footprints across all depths (radial candidates 300,
  // 248, 196): one bloom in (52 units) is not enough room, so a close
  // neighbour takes two; distant ones stay outermost. When every pair can be
  // cleared, no two flowers stand nearer than BLOOM_ROOM, and the result is
  // the same for the same input.
  assert.deepEqual(bloomDepths([0.1, 0.11, 2]), [0, 2, 0]);
  const spread = [0.1, 0.16, 0.6, 0.66, 1.2, 2];
  const placed = bloomDepths(spread);
  assert.deepEqual(bloomDepths(spread), placed, 'stable');
  const at = spread.map((a, i) => [Math.cos(a) * (R.kernel - placed[i] * R.bloom), Math.sin(a) * (R.kernel - placed[i] * R.bloom)]);
  for (let i = 0; i < at.length; i += 1) for (let j = i + 1; j < at.length; j += 1) {
    assert.ok(Math.hypot(at[i][0] - at[j][0], at[i][1] - at[j][1]) >= BLOOM_ROOM - 1e-9, 'footprints never meet');
  }
  // A kernel stands on its own component's radius, its stem out to the component.
  const m = build(overview(), 'rev');
  const L = layout(m);
  const k = L.kernels.find((x) => x.componentId === 'a');
  const comp = L.comps.find((c) => c.id === 'a');
  assert.equal(k.angle, comp.angle);
  assert.equal(k.r, R.kernel);
  assert.ok(k.r < k.generatedR && k.generatedR < k.callerR && k.callerR < R.component, 'kernel, generated code, caller, component, outward');
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


test('plain descriptions and guide manifest stay snapshot data; old indexes stay absent', () => {
  const data = overview();
  data.components[0].plain = 'A readable explanation.';
  data.components[0].plain_availability = 'available';
  data.explorer = { ...data.explorer, guides: { 'paper_modules/a.md': { ref: 'paper_modules/a.md', availability: 'available', sha256: 'abc' } } };
  const current = build(data, 'current');
  assert.equal(current.components[0].plain, 'A readable explanation.');
  assert.equal(current.components[0].plainAvailability, 'available');
  assert.deepEqual(current.links.guides, data.explorer.guides);
  const old = build({ components: [{ organ_id: 'old', summary: 'Recorded summary' }] }, 'old');
  assert.equal(old.components[0].plain, null);
  assert.equal(old.components[0].plainAvailability, 'unrecorded');
  assert.equal(old.links.guides, null);
  assert.equal(old.components[0].summary, 'Recorded summary');
  const absent = build({ components: [{ organ_id: 'absent', plain: 'Do not show', plain_availability: 'unavailable' }] }, 'absent');
  assert.equal(absent.components[0].plain, null);
});

test('each evidence row reads as a state word in the key order, never a fraction or a score', async () => {
  const { TRACKS, ordinal, ringState } = await import('../src/evidence.js');
  assert.deepEqual(TRACKS.map((t, i) => ordinal(i)), ['01', '02', '03', '04', '05', '06', '07', '08']);
  assert.ok(TRACKS.every((t) => t.line && t.line.length < 90), 'every ring has a one-line meaning');
  const track = (id) => TRACKS.find((t) => t.id === id);
  const none = { checks: {}, receipts: [] };
  assert.equal(ringState(track('proof'), none).word, 'Not recorded');
  assert.equal(ringState(track('proof'), { checks: { proof: true }, receipts: [] }).word, 'Recorded');
  assert.equal(ringState(track('replay'), { checks: { replay: true }, receipts: [] }).word, 'Configured, not run here');
  assert.equal(ringState(track('whole'), none).word, 'Unknown');
  const runs = { checks: { saved: true }, receipts: [{ availability: 'available' }, { availability: 'available' }, { availability: 'available' }, { availability: 'unavailable' }] };
  assert.equal(ringState(track('saved'), runs).word, '3 available · 1 missing');
  for (const t of TRACKS) assert.doesNotMatch(ringState(t, runs).word, /\b\d+ (of|\/) \d+\b|score|pass/i);
});
