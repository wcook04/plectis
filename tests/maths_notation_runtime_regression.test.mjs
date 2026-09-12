import { test } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';

const source = readFileSync(process.env.PLECTIS_MATHS_JS || new URL(
  '../../../tools/meta/dissemination/maths_site_assets/maths.js', import.meta.url), 'utf8');
const marker = '/* Explain fixed TeX operators through the shared glossary.';
assert.ok(source.includes(marker), 'maths runtime includes the notation registration module');
const scanner = source.slice(source.indexOf(marker));

function expression(tex, { linked = false, literal = false, hidden = false } = {}) {
  const attrs = { 'data-tex': tex };
  return {
    innerHTML: '<mjx-container>typeset expression</mjx-container><math><mi>x</mi></math>',
    reads: 0,
    getAttribute(name) { if (name === 'data-tex') this.reads++; return attrs[name] ?? null; },
    setAttribute(name, value) { attrs[name] = value; },
    closest(selector) { return (selector.startsWith('[hidden]') ? hidden : linked) ? {} : null; },
    querySelector() { return literal ? {} : null; },
  };
}

function run(expressions, { delayed = false, src = 'https://preview.example/plectis/maths/assets/maths.js?v=123' } = {}) {
  const listeners = new Map(), calls = [];
  const api = { registerNotation(element, ids, options) {
    calls.push({ element, ids: Array.from(ids), href: options.hrefForId(ids[0]), keyboardFocus: options.keyboardFocus });
    return true;
  } };
  const window = delayed ? {} : { PlectisTermHelp: api };
  const document = {
    currentScript: { src },
    querySelectorAll() { return expressions; },
    addEventListener(name, callback) { listeners.set(name, callback); },
  };
  vm.runInNewContext(scanner, { window, document, URL });
  return { calls, ready() { window.PlectisTermHelp = api; listeners.get('plectis:term-help-ready')(); } };
}

test('fixed operators resolve in source order and deduplicate equivalent spellings', () => {
  const formula = expression(String.raw`\forall x\in A,\;\sum_{n=1}^{N}x_n\subseteq B\subset C\cup D\cap E,\exists y,\prod_i y_i`);
  const { calls } = run([formula]);
  assert.deepEqual(calls[0].ids, ['universal_quantifier', 'set_membership', 'sum', 'subset',
    'set_union', 'set_intersection', 'existential_quantifier', 'product']);
  assert.equal(calls[0].href, 'https://preview.example/plectis/docs/glossary.html#glossary-universal-quantifier');
});

test('control-word boundaries, literal arguments, comments, and variable letters do not invent meanings', () => {
  const snippets = [
    String.raw`x f g A B \infty \subsetneq \subset 90^\circ \constructor`,
    String.raw`\text{literal \sum and {nested \prod}}\operatorname*{\exists}\label{\cap}`,
    String.raw`\href{https://example.test/\sum}{\forall}\url{\prod}\verb|\in|`,
    '% \\sum \\prod\n x + y',
    String.raw`\newcommand{\foo}{\sum}\foo`,
    String.raw`\begin{verbatim}\sum\end{verbatim}`,
  ];
  assert.equal(run(snippets.map(tex => expression(tex))).calls.length, 0);
  assert.deepEqual(run([expression('\\% \\sum_i x_i % \\prod\n \\exists y')]).calls[0].ids,
    ['sum', 'existential_quantifier']);
});

test('registration preserves equation bytes and parses each element once across readiness', () => {
  const formula = expression(String.raw`\sum_i x_i`);
  const noHelp = expression('x + y');
  const before = formula.innerHTML;
  const runtime = run([formula, noHelp]);
  runtime.ready();
  runtime.ready();
  assert.equal(runtime.calls.length, 1);
  assert.equal(formula.reads, 1);
  assert.equal(noHelp.reads, 1);
  assert.equal(formula.innerHTML, before);
  assert.equal(formula.getAttribute('data-tex'), String.raw`\sum_i x_i`);
});

test('late shared controller registers once while linked formulas and literal proof names remain untouched', () => {
  const formula = expression(String.raw`\sum_i x_i`);
  const linked = expression(String.raw`\prod_i x_i`, { linked: true });
  const literal = expression(String.raw`\texttt{\sum}`, { literal: true });
  const runtime = run([formula, linked, literal], { delayed: true });
  assert.equal(runtime.calls.length, 0);
  assert.equal(formula.reads, 0);
  runtime.ready();
  assert.equal(runtime.calls.length, 1);
  assert.equal(linked.reads, 0);
  assert.equal(literal.reads, 0);
});

test('glossary destination follows the actual deployment prefix', () => {
  const { calls } = run([expression(String.raw`\in A`)], {
    src: 'http://127.0.0.1:8767/stix/maths/assets/maths.js?v=abc',
  });
  assert.equal(calls[0].href, 'http://127.0.0.1:8767/stix/docs/glossary.html#glossary-set-membership');
});

test('each operator has a keyboard introduction without repeating every equation in tab order', () => {
  const { calls } = run([
    expression(String.raw`\sum_i x_i`), expression(String.raw`\sum_j y_j`),
    expression(String.raw`\forall x`), expression(String.raw`\sum_i x_i,\exists n`),
    expression(String.raw`\prod_i x_i`, { hidden: true }), expression(String.raw`\prod_i y_i`),
  ]);
  assert.equal(calls.length, 6, 'all expressions retain pointer and touch help');
  assert.deepEqual(calls.map(call => call.keyboardFocus), [true, false, true, true, false, true]);
});

for (const preferred of ['0', '-1']) test(`resizing restores the intended ${preferred} notation tab stop and mathematical name`, () => {
  const attrs = new Map([['data-term-help', 'notation'], ['tabindex', '0'], ['data-term-tabindex', preferred]]);
  const equation = {
    scrollWidth: 220, clientWidth: 120,
    classList: { contains(name) { return name === 'math'; } },
    getAttribute(name) { return attrs.get(name) ?? null; },
    setAttribute(name, value) { attrs.set(name, value); },
    removeAttribute(name) { attrs.delete(name); },
  };
  const events = new Map();
  const document = {
    querySelectorAll(selector) { return selector === '.paper-stage .math.display' ? [equation] : []; },
  };
  const window = { addEventListener(name, callback) { events.set(name, callback); } };
  const start = source.indexOf('/* Make only overflowing equations keyboard-scrollable.');
  assert.ok(start >= 0, 'exercise the actual equation overflow module');
  vm.runInNewContext(source.slice(start, source.indexOf(marker)), {
    document, window, requestAnimationFrame(callback) { callback(); },
  });
  assert.equal(attrs.get('data-math-scroll'), 'true');
  assert.equal(attrs.get('tabindex'), '0');
  assert.equal(attrs.has('aria-label'), false);
  assert.equal(attrs.has('role'), false);
  assert.match(attrs.get('aria-description'), /Scroll horizontally/);
  equation.clientWidth = 400;
  events.get('resize')();
  assert.equal(attrs.get('tabindex'), preferred);
  assert.equal(attrs.has('data-math-scroll'), false);
  assert.equal(attrs.has('aria-description'), false);
  equation.clientWidth = 120;
  events.get('resize')();
  assert.equal(attrs.get('tabindex'), '0');
  equation.clientWidth = 400;
  events.get('resize')();
  assert.equal(attrs.get('tabindex'), preferred, 'repeated phone-to-desktop resize does not accumulate tab stops');
});
