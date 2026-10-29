// Check the static API against recorded server answers (used by export_static.py).
// Run: node frontend/tests/static_parity.mjs <export-dir> <cases.json>
import { readFile } from 'node:fs/promises';
import { isDeepStrictEqual } from 'node:util';
import path from 'node:path';
import { createStaticApi } from '../src/static-api.js';

const [root, casesFile] = process.argv.slice(2);
const load = async (relative) => {
  try { return JSON.parse(await readFile(path.join(root, relative), 'utf8')); } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
};
const fetchStatic = createStaticApi(load);
const cases = JSON.parse(await readFile(casesFile, 'utf8'));
const failures = [];
for (const c of cases) {
  if (c.url) {
    const response = await fetchStatic(c.url);
    const body = JSON.parse(await response.text());
    if (response.status !== c.status || !isDeepStrictEqual(body, c.body)) failures.push({ url: c.url, status: response.status, expected: c.status, body: JSON.stringify(body).slice(0, 300), want: JSON.stringify(c.body).slice(0, 300) });
    continue;
  }
  const pages = [];
  let cursor = null;
  do {
    const url = cursor ? `${c.list}&cursor=${encodeURIComponent(cursor)}` : c.list;
    const response = await fetchStatic(url);
    const body = JSON.parse(await response.text());
    if (response.status !== 200) { pages.push({ status: response.status, body }); break; }
    const { items, total, limit, next_cursor: next } = body.data;
    pages.push({ items, total, limit, more: Boolean(next) });
    cursor = next;
  } while (cursor && pages.length < 200);
  if (!isDeepStrictEqual(pages, c.pages)) failures.push({ list: c.list, pages: pages.length, expected: c.pages.length });
}
console.log(`static parity: ${cases.length - failures.length} of ${cases.length} cases equal to the server`);
if (failures.length) {
  for (const f of failures.slice(0, 10)) console.error(JSON.stringify(f));
  process.exit(1);
}
