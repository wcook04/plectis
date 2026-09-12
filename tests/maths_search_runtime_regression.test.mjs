// Exercise the production corpus merge and query scorer without a browser build.
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
const source = readFileSync(process.env.MICROCOSM_DOCS_JS || new URL('../assets/docs.js', import.meta.url), 'utf8');
const merge = source.match(/function mcSearchIndexRecords\(\) \{([\s\S]*?)\n  \}/)?.[0];
const score = source.match(/function score\(rec, qs\) \{([\s\S]*?)\n    \}/)?.[0];
assert.ok(merge && score, 'production search functions are available');
function palette(payload) {
  const context = { window: { __MICROCOSM_INDEX__: payload } };
  vm.runInNewContext(`${merge}\n${score}\nrecords = mcSearchIndexRecords(); rank = score;`, context);
  return context;
}

test('maths titles and abstracts participate in the same query results as software and terms', () => {
  const payload = {
    records: [{ label: 'Agent tools', kind: 'page', text: 'Software components' }],
    terms: [{ label: 'Mersenne', kind: 'term', text: 'A glossary definition' }],
    maths: [{ label: 'Erdős #257 — Reciprocal Mersenne Subseries', kind: 'Maths paper',
      text: 'The infinite target remains open.', url: '../maths/papers/erdos257.html' }],
  };
  const before = JSON.stringify(payload);
  const { records, rank } = palette(payload);
  const matches = Array.from(records).filter(record => rank(record, ['mersenne']) >= 0);
  assert.equal(matches.length, 2);
  assert.ok(matches.some(record => record.kind === 'Maths paper'));
  assert.ok(records.some(record => rank(record, ['257', 'open']) >= 0));
  assert.equal(JSON.stringify(payload), before, 'search must not mutate a corpus projection');
});

test('maths-only, software-only, and absent index projections remain usable', () => {
  const maths = { label: 'The factorial-denominator series', kind: 'Maths problem', tags: ['erdos_68'] };
  assert.equal(palette({ maths: [maths] }).records[0], maths);
  assert.equal(palette({ records: [maths] }).records.length, 1);
  assert.equal(palette(undefined).records.length, 0);
});
