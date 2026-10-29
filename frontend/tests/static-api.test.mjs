// The static API answers like the component API from exported files.
// Run: node --test frontend/tests/
import test from 'node:test';
import assert from 'node:assert/strict';
import { API_SCHEMA, Collection, getEnvelope } from '../src/api.js';
import { createStaticApi, fileId } from '../src/static-api.js';
import { routePath, at } from '../src/base.js';

const env = (data) => ({ schema_version: API_SCHEMA, snapshot_revision: 'r'.repeat(64), data });
const row = (id, family, title = id) => ({ organ_id: id, title, summary: `${title} summary`, classification: { family } });
const files = {
  'api/v1/index.json': env({ component_filters: { family: [{ value: 'alpha' }, { value: 'beta' }] } }),
  'api/v1/components.json': env({ items: [row('a1', 'alpha', 'Owner check'), row('a2', 'alpha'), row('b1', 'beta', 'Replay owner')], total: 3 }),
  [`api/v1/proofs/${fileId('proof::dafny::x')}.json`]: env({ proof: { proof_id: 'proof::dafny::x' } }),
  'api/v1/graph.json': env({
    nodes: [['organ', 'a1', { value: 'a1' }], ['organ', 'a2', { value: 'a2' }], ['proof', 'p', { value: 'p' }]],
    edges: [{ kind: 'proven_by', from_type: 'organ', from: 'a1', to_type: 'proof', to: 'p' },
      { kind: 'wires_to', from_type: 'organ', from: 'a2', to_type: 'organ', to: 'a1' }],
    edge_kinds: ['proven_by', 'wires_to'],
  }),
};
const fetchImpl = createStaticApi(async (rel) => structuredClone(files[rel] ?? null));

test('IDs become safe file names', () => {
  assert.equal(fileId('proof::dafny::x'), 'proof~3a~3adafny~3a~3ax');
  assert.equal(fileId('a_b-1.2'), 'a_b-1.2');
});

test('search and filters combine, and pages share one revision', async () => {
  const list = new Collection('/api/v1/components', { q: 'OWNER', family: 'alpha' }, { pageSize: 1, fetchImpl });
  await list.first();
  assert.deepEqual(list.items.map((i) => i.organ_id), ['a1']);
  assert.equal(list.total, 1);
  const all = new Collection('/api/v1/components', {}, { pageSize: 2, fetchImpl });
  await all.first();
  await all.more();
  assert.deepEqual(all.items.map((i) => i.organ_id), ['a1', 'a2', 'b1']);
  assert.equal(all.nextCursor, null);
});

test('bad parameters and unknown IDs keep the API error kinds', async () => {
  await assert.rejects(getEnvelope('/api/v1/components?family=gamma', { fetchImpl }), { kind: 'request' });
  await assert.rejects(getEnvelope('/api/v1/components?q=+', { fetchImpl }), { kind: 'request' });
  await assert.rejects(getEnvelope('/api/v1/components?limit=2&cursor=bm9wZQ', { fetchImpl }), { kind: 'request' });
  await assert.rejects(getEnvelope('/api/v1/components/zz', { fetchImpl }), { kind: 'not_found' });
  const proof = await getEnvelope('/api/v1/proofs/proof%3A%3Adafny%3A%3Ax', { fetchImpl });
  assert.equal(proof.data.proof.proof_id, 'proof::dafny::x');
});

test('graph neighbourhoods follow depth, direction and truncation', async () => {
  const one = (await getEnvelope('/api/v1/graph?type=organ&id=a2', { fetchImpl })).data;
  assert.deepEqual(one.nodes.map((n) => n.id), ['a1', 'a2']);
  const two = (await getEnvelope('/api/v1/graph?type=organ&id=a2&depth=2', { fetchImpl })).data;
  assert.deepEqual(two.nodes.map((n) => `${n.type}:${n.id}`), ['organ:a1', 'organ:a2', 'proof:p']);
  const inbound = (await getEnvelope('/api/v1/graph?type=organ&id=a2&direction=in', { fetchImpl })).data;
  assert.equal(inbound.edges.length, 0);
  const capped = (await getEnvelope('/api/v1/graph?type=organ&id=a1&max_edges=1', { fetchImpl })).data;
  assert.equal(capped.truncated, true);
  await assert.rejects(getEnvelope('/api/v1/graph?type=organ&id=nope', { fetchImpl }), { kind: 'not_found' });
});

test('page paths map onto the mount point and back', () => {
  assert.equal(at('/catalogue'), `${new URL('../', new URL('../src/base.js', import.meta.url)).pathname}catalogue`);
  assert.equal(routePath(at('/components/x')), '/components/x');
  assert.equal(routePath(at('/catalogue.html')), '/catalogue');
  assert.equal(routePath(at('/')), '/');
  assert.equal(at('#main'), '#main');
});
