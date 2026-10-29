// Loading-rule tests for the API client, with controlled responses.
// Run: node --test frontend/tests/
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  API_SCHEMA, ApiError, apiPath, withQuery, getEnvelope, latestOnly, loadTogether, Collection,
} from '../src/api.js';

const envelope = (data, revision = 'r1') => ({ schema_version: API_SCHEMA, snapshot_revision: revision, data });
const reply = (status, body) => new Response(typeof body === 'string' ? body : JSON.stringify(body), { status });
const fetchFrom = (handler) => async (url, init) => handler(url, init);

test('IDs are encoded as one path segment', () => {
  assert.equal(apiPath('proofs', 'proof::dafny::mcp_authority'), '/api/v1/proofs/proof%3A%3Adafny%3A%3Amcp_authority');
  assert.equal(apiPath('components', 'a/b'), '/api/v1/components/a%2Fb');
});

test('blank query values are omitted, never sent empty', () => {
  assert.equal(withQuery('/api/v1/components', { q: '  ', family: '', limit: 25 }), '/api/v1/components?limit=25');
  assert.equal(withQuery('/api/v1/components', { q: 'owner ship' }), '/api/v1/components?q=owner+ship');
});

test('error statuses become distinct kinds', async () => {
  const cases = [
    [404, { schema_version: API_SCHEMA, snapshot_revision: 'r', error: { code: 'unknown_id', message: 'unknown resource ID' } }, 'not_found'],
    [400, { schema_version: API_SCHEMA, snapshot_revision: 'r', error: { code: 'invalid_parameters', message: 'x'.repeat(900) } }, 'request'],
    [409, { schema_version: API_SCHEMA, snapshot_revision: 'r', error: { code: 'stale_cursor', message: 'snapshot changed' } }, 'stale_cursor'],
    [500, { schema_version: API_SCHEMA, error: { code: 'internal_error', message: 'request could not be completed' } }, 'server'],
    [502, 'component API unreachable', 'network'],
    [200, { schema_version: 'plectis_component_http_v2', snapshot_revision: 'r', data: {} }, 'schema'],
    [200, '<html>', 'schema'],
  ];
  for (const [status, body, kind] of cases) {
    const error = await getEnvelope('/x', { fetchImpl: fetchFrom(() => reply(status, body)) }).catch((e) => e);
    assert.ok(error instanceof ApiError, `${status} should throw`);
    assert.equal(error.kind, kind, `${status} -> ${kind}`);
    assert.ok(error.message.length <= 240);
  }
  const offline = await getEnvelope('/x', { fetchImpl: async () => { throw new TypeError('fetch failed'); } }).catch((e) => e);
  assert.equal(offline.kind, 'network');
});

test('a slow earlier search cannot replace a later one', async () => {
  const run = latestOnly();
  let release;
  const slow = run(() => new Promise((resolve) => { release = resolve; }));
  const fast = run(async () => 'later results');
  release('earlier results');
  assert.equal(await fast, 'later results');
  await assert.rejects(slow, (e) => e.kind === 'aborted');
});

test('parts from different revisions are retried once, then refused', async () => {
  let calls = 0;
  const flapping = fetchFrom((url) => { calls += 1; return reply(200, envelope({ url }, url.endsWith('b') ? 'r2' : 'r1')); });
  const error = await loadTogether(['/a', '/b'], { fetchImpl: flapping }).catch((e) => e);
  assert.equal(error.kind, 'revision');
  assert.equal(calls, 4, 'one retry, then an explicit state rather than a loop');

  let second = 0;
  const settles = fetchFrom((url) => reply(200, envelope({ url }, url.endsWith('b') && second++ === 0 ? 'r2' : 'r1')));
  const together = await loadTogether(['/a', '/b'], { fetchImpl: settles });
  assert.equal(together.revision, 'r1');
  assert.deepEqual(together.parts.map((p) => p.url), ['/a', '/b']);
});

test('a page from a new revision is not appended', async () => {
  const seen = [];
  let revision = 'r1';
  const fetchImpl = fetchFrom((url) => {
    seen.push(url);
    const cursor = new URL(url, 'http://x').searchParams.get('cursor');
    return reply(200, envelope({ items: [cursor ? 'b' : 'a'], total: 2, limit: 1, next_cursor: cursor ? null : 'c1' }, revision));
  });
  const list = new Collection('/api/v1/components', { q: 'owner', family: 'formal_math_and_proof' }, { pageSize: 1, fetchImpl });
  await list.first();
  assert.deepEqual(list.items, ['a']);
  revision = 'r2';
  await assert.rejects(list.more(), (e) => e.kind === 'revision');
  assert.deepEqual(list.items, ['a']);
  const second = new URL(seen[1], 'http://x').searchParams;
  assert.equal(second.get('q'), 'owner');
  assert.equal(second.get('family'), 'formal_math_and_proof');
  assert.equal(second.get('limit'), '1');
  assert.equal(second.get('cursor'), 'c1');
});
