// What a proof page and a map card show of a verified computation: its
// specification as the retained Dafny text, the broken variants the verifier
// rejected as the lines they change, and, for the ownership classifier, the
// paper's repair played through. Everything is set as text from the
// index's bounded, hash-bound excerpts; nothing is fetched from source.

import { h } from '../dom.js';
import { count, dayWords, fileWords, identifierWords, sourceHref } from '../evidence.js';

const KEYWORDS = new Set(('predicate function method lemma requires ensures invariant decreases var if then else while '
  + 'return returns forall exists datatype module import reads modifies assert assume calc match case ghost static '
  + 'opened include type class const in by old fresh label break yield new this').split(' '));
const TYPES = new Set('int nat bool seq set map multiset string char real array object'.split(' '));
const TOKEN = /(\/\/.*$)|("(?:[^"\\]|\\.)*")|(\b\d+\b)|(<==>|==>|<==|::|:=|&&|\|\||!=|==|<=|>=)|([A-Za-z_][A-Za-z0-9_']*)|(\s+)|(.)/gm;

/** One line of Dafny as spans: keywords, types, numbers, comments and the declared name. */
function dafnyLine(line, name) {
  const out = [];
  let m;
  TOKEN.lastIndex = 0;
  while ((m = TOKEN.exec(line))) {
    const [tok, comment, str, num, op, word] = m;
    let cls = '';
    if (comment) cls = 'tok-c';
    else if (str) cls = 'tok-s';
    else if (num) cls = 'tok-n';
    else if (op) cls = 'tok-o';
    else if (word) cls = KEYWORDS.has(word) ? 'tok-k' : TYPES.has(word) ? 'tok-t' : word === name ? 'tok-d' : '';
    out.push(cls ? h('span', { class: cls }, tok) : tok);
    if (m.index === TOKEN.lastIndex) TOKEN.lastIndex += 1;
  }
  return out;
}

/** The common indentation of a block, so an excerpt reads flush left. */
function dedent(lines) {
  const pad = Math.min(...lines.filter((l) => l.trim()).map((l) => l.match(/^ */)[0].length));
  return Number.isFinite(pad) ? lines.map((l) => l.slice(pad)) : lines;
}

const KIND_WORDS = { predicate: 'Predicate', function: 'Function', method: 'Method', lemma: 'Lemma' };

/** A declaration from the retained source, with its line numbers and a link to exact source. */
export function excerptBlock(excerpt, source, { open = false, role = '' } = {}) {
  const lines = dedent(excerpt.text.replace(/\n$/, '').split('\n'));
  const href = sourceHref(source, excerpt.ref, [excerpt.lineStart, excerpt.lineEnd]);
  const code = h('pre', { class: 'dafny', tabindex: '0' }, h('code', {}, lines.map((line, i) => h('span', { class: 'dafny__line' },
    h('span', { class: 'dafny__no', 'aria-hidden': 'true' }, String(excerpt.lineStart + i)),
    h('span', { class: 'dafny__text' }, dafnyLine(line, excerpt.name))))));
  return h('details', { class: 'excerpt', open: open || null },
    h('summary', {},
      h('span', { class: 'excerpt__kind' }, KIND_WORDS[excerpt.kind] || identifierWords(excerpt.kind)),
      h('code', { class: 'excerpt__name' }, excerpt.name),
      role ? h('span', { class: 'excerpt__role' }, role) : null,
      h('span', { class: 'excerpt__lines figures' }, `lines ${excerpt.lineStart}–${excerpt.lineEnd}`)),
    code,
    href ? h('p', { class: 'excerpt__src' }, h('a', { href, rel: 'noopener', target: '_blank' }, 'View in source ↗')) : null);
}

/**
 * The specification: the declarations it names first, then the entry
 * theorems and the computation. Retained text only; a reference with no
 * excerpt is listed by name.
 */
export function specificationParts(proof, source) {
  const byRef = new Map(proof.excerpts.map((e) => [e.ref, e]));
  const spec = proof.specificationRefs.map((r) => byRef.get(r)).filter(Boolean);
  const entry = proof.entryTheoremRefs.map((r) => byRef.get(r)).filter(Boolean);
  const shown = new Set([...spec, ...entry]);
  const rest = proof.excerpts.filter((e) => !shown.has(e));
  const wrap = h('div', { class: 'spec' });
  if (!proof.excerpts.length) {
    wrap.append(h('p', { class: 'small muted' }, `No Dafny text was saved with this snapshot. The rules are named ${[...proof.specificationRefs, ...proof.entryTheoremRefs].map((r) => r.split('#').pop()).join(', ')}.`));
    return wrap;
  }
  spec.forEach((e, i) => wrap.append(excerptBlock(e, source, { open: i < 2, role: 'states' })));
  entry.forEach((e) => wrap.append(excerptBlock(e, source, { role: e.kind === 'lemma' ? 'proves' : 'computes' })));
  rest.forEach((e) => wrap.append(excerptBlock(e, source)));
  const missing = [...proof.specificationRefs, ...proof.entryTheoremRefs].filter((r) => !byRef.has(r));
  if (missing.length) wrap.append(h('p', { class: 'small muted' }, `No text was saved for ${missing.map((r) => r.split('#').pop()).join(', ')}.`));
  wrap.append(h('p', { class: 'note' }, `Copied from the Dafny source when this snapshot was made, and checked against the source's fingerprint; ${count(proof.excerpts.length, 'piece')} shown.`));
  return wrap;
}

/** Where two lines differ: common head and tail, changed middle. */
function splitChange(a, b) {
  let i = 0;
  while (i < a.length && i < b.length && a[i] === b[i]) i += 1;
  let j = 0;
  while (j < a.length - i && j < b.length - i && a[a.length - 1 - j] === b[b.length - 1 - j]) j += 1;
  return [a.slice(0, i), a.slice(i, a.length - j), b.slice(i, b.length - j), a.slice(a.length - j)];
}

/** One broken variant: the lines it changes, and what the verifier recorded. */
export function variantBlock(variant, source, verifiedTasks) {
  const name = String(variant.ref || '').split('/').pop().replace(/\.dfy$/, '');
  const rows = variant.changedLines.map((l) => {
    const [head, was, now, tail] = splitChange(l.original.trim(), l.mutated.trim());
    return h('div', { class: 'diff' },
      h('div', { class: 'diff__row diff__row--was' }, h('span', { class: 'diff__mark', 'aria-label': 'Proved line' }, 'proved'), h('span', { class: 'diff__no figures' }, String(l.line)),
        h('code', {}, head, h('mark', { class: 'diff__was' }, was), tail)),
      h('div', { class: 'diff__row diff__row--now' }, h('span', { class: 'diff__mark', 'aria-label': 'Broken line' }, 'broken'), h('span', { class: 'diff__no figures' }, String(l.line)),
        h('code', {}, head, h('mark', { class: 'diff__now' }, now), tail)));
  });
  const href = sourceHref(source, variant.ref);
  const verdict = variant.errors != null
    ? `The prover rejected this version, with ${count(variant.errors, 'error')}.`
    : 'The saved results list it as rejected.';
  return h('div', { class: 'variant' },
    h('p', { class: 'variant__head' }, h('span', { class: 'variant__cross', 'aria-hidden': 'true' }, '×'),
      href ? h('a', { href, rel: 'noopener', target: '_blank' }, h('code', {}, name)) : h('code', {}, name)),
    rows.length ? rows : h('p', { class: 'small muted' }, 'The changed line was not saved.'),
    h('p', { class: 'small muted' }, verdict));
}

export function variantsPart(proof, source) {
  if (!proof.mutants.length) return h('p', { class: 'small muted' }, 'No broken versions are saved.');
  return h('div', { class: 'variants' }, proof.mutants.map((m) => variantBlock(m, source, proof.verifiedTasks)),
    h('p', { class: 'note' }, 'Each one is the proved computation with a single deliberate mistake. If the prover had accepted one, the rules would be too loose to catch that mistake. It rejected them all.'));
}

// The two decisions the paper's ownership table names, in its words.
const DECISION_WORDS = {
  stale_release: 'release the stale claim',
  owned_live: 'protect the live owner and wait',
};
const decisionWords = (code) => DECISION_WORDS[code] || identifierWords(code);

/**
 * The ownership repair (paper section "Worked behavior"), from the index's
 * structured record: the same two claims in both orders, under the former
 * first-match rule and under the repaired rule. Switching the rule moves the
 * selection; the previous decision flips with the order, the repaired one
 * does not.
 */
export function ownershipFigure(example, source) {
  if (!example) return null;
  const claims = new Map(example.observations.map((o) => [o.claim_id, o]));
  let rule = 'previous';
  const rows = example.orders.map((order, i) => {
    const chips = order.claim_ids.map((id) => {
      const c = claims.get(id) || { claim_id: id, claim_state: 'unknown', session_id: '?' };
      return h('span', { class: `claim claim--${c.claim_state}`, 'data-claim': id },
        h('span', { class: 'claim__state' }, c.claim_state), h('span', { class: 'claim__session' }, `session ${c.session_id}`));
    });
    const decision = h('span', { class: 'own__decision' });
    const row = h('div', { class: 'own__row' },
      h('span', { class: 'own__order figures' }, `Order ${i + 1}`),
      h('span', { class: 'own__claims' }, chips[0], h('span', { class: 'own__then', 'aria-hidden': 'true' }, 'then'), chips[1]),
      decision);
    return { row, chips, decision, order };
  });
  const btnPrev = h('button', { type: 'button', class: 'seg', 'aria-pressed': 'true' }, 'Old rule');
  const btnNow = h('button', { type: 'button', class: 'seg', 'aria-pressed': 'false' }, 'Fixed rule');
  const verdict = h('p', { class: 'own__verdict', role: 'status' });
  function render() {
    btnPrev.setAttribute('aria-pressed', String(rule === 'previous'));
    btnNow.setAttribute('aria-pressed', String(rule === 'repaired'));
    const decisions = [];
    for (const { chips, decision, order } of rows) {
      const pick = rule === 'previous' ? 0 : order.claim_ids.findIndex((id) => claims.get(id)?.claim_state === 'live');
      chips.forEach((chip, j) => chip.classList.toggle('is-picked', j === pick));
      const code = rule === 'previous' ? order.previous_decision : order.repaired_decision;
      decisions.push(code);
      decision.replaceChildren(h('span', { class: `own__code${code === 'stale_release' ? ' is-unsafe' : ''}` }, code), ' ', decisionWords(code));
    }
    const same = decisions.every((d) => d === decisions[0]);
    verdict.textContent = same
      ? 'Under the fixed rule, both orders protect the person still working, whichever claim comes first.'
      : 'Under the old rule, the advice depends on the order: when the stale claim comes first, it hides the person still working.';
    verdict.classList.toggle('is-unsafe', !same);
  }
  btnPrev.addEventListener('click', () => { rule = 'previous'; render(); });
  btnNow.addEventListener('click', () => { rule = 'repaired'; render(); });
  render();
  const tests = example.test_refs.map((ref) => {
    const href = sourceHref(source, ref);
    const label = ref.split('#').pop();
    return h('li', {}, href ? h('a', { href, rel: 'noopener', target: '_blank' }, h('code', {}, label)) : h('code', {}, label));
  });
  return h('figure', { class: 'own' },
    h('div', { class: 'own__head' },
      h('p', { class: 'own__title' }, 'Two claims on one file, in both orders'),
      h('code', { class: 'own__path' }, example.path),
      h('div', { class: 'segs', role: 'group', 'aria-label': 'Selection rule' }, btnPrev, btnNow)),
    rows.map((r) => r.row),
    verdict,
    h('figcaption', { class: 'note' },
      'Each claim says a session is working on the file; one session has gone stale and the other is live. The example is saved with the snapshot; the old rule\'s code is not run here. ',
      example.limits.join(' '),
      tests.length ? h('span', {}, ' The tests ', h('ul', { class: 'inline-list' }, tests), ' run both orders through the real code.') : null));
}

/**
 * Saved runs as a row of dated marks, newest first: the date and what the
 * run recorded, with the record's own name only on hover. An absent record
 * is a hollow mark and never a link.
 */
export function runsStrip(receipts, source) {
  const sorted = [...receipts].sort((a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')));
  return h('ul', { class: 'runs' }, sorted.map((r) => {
    const ok = r.availability === 'available';
    const href = ok ? sourceHref(source, r.ref) : null;
    const status = !ok ? 'not in this snapshot' : r.status === 'pass' ? 'pass' : r.status || 'no recorded status';
    const inner = [h('span', { class: 'run__dot', 'aria-hidden': 'true' }),
      h('span', { class: 'run__date' }, r.createdAt ? dayWords(r.createdAt) : 'Undated'),
      h('span', { class: 'run__status' }, status)];
    return h('li', { class: `run${ok ? '' : ' is-absent'}${r.status === 'blocked' ? ' is-blocked' : ''}`, title: fileWords(r.ref) },
      href ? h('a', { href, rel: 'noopener', target: '_blank' }, inner) : inner);
  }));
}
