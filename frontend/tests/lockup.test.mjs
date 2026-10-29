// The header lockup (wcook04.github.io docs/family.md, "The lockup"): the
// Plectis plait opens Will Cook's home page, a rule, then the flower mark and
// the site's name open the map. Nothing in it loads from another host.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const header = html.slice(html.indexOf('<header'), html.indexOf('</header>'));

test('the header starts with the plait home link, a rule, then the site link to the map', () => {
  const home = header.match(/<a class="fam-lockup__home" href="([^"]+)"[^>]*><img src="([^"]+)" alt="([^"]+)"/);
  assert.ok(home, 'plait link');
  assert.equal(home[1], 'https://wcook04.github.io/');
  assert.equal(home[2], '/assets/plectis.svg');
  assert.equal(home[3], 'Will Cook: all websites and films');
  assert.ok(existsSync(new URL('../assets/plectis.svg', import.meta.url)));
  const rule = header.indexOf('class="fam-lockup__rule" aria-hidden="true"');
  const site = header.indexOf('<a class="fam-lockup__site" href="/" data-route>');
  assert.ok(header.indexOf('fam-lockup__home') < rule && rule < site, 'plait, rule, site in that order');
  assert.match(header, /<svg class="fam-mark"[^>]*aria-hidden="true"/);
  assert.match(header, /<span class="fam-lockup__name" translate="no">Practical Formal Verification<\/span><\/a>/);
  assert.doesNotMatch(header, /wordmark/);
});

test('the lockup loads nothing from another host', () => {
  assert.doesNotMatch(header, /\ssrc="(https?:)?\/\//);
});
