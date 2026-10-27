// One retained proof view. The modeled statement, its assumptions and limits,
// the retained verification, the broken variants, the generated code and its
// callers, and the fresh-check state are separate sections, never a single
// verdict. The proof view names no component, so its component is found
// through the graph (proof <- subclaim <- claim <- component), in the same
// snapshot.

import { apiPath, loadTogether, withQuery } from '../api.js';
import { h, keyGlyph } from '../dom.js';
import { count, moduleWords, stateWords } from '../evidence.js';
import { chainFigure, followSections } from './chain.js';
import { failure } from './component.js';

export async function mountProof(root, { id }) {
  const page = h('div', { class: 'page' }, h('p', { class: 'muted', role: 'status' }, 'Loading the proof…'));
  root.append(page);
  let view, graph, revision;
  try {
    ({ revision, parts: [view, graph] } = await loadTogether([
      apiPath('proofs', id),
      withQuery(apiPath('graph'), { type: 'proof', id, depth: 3, direction: 'in', max_edges: 50 }),
    ]));
  } catch (error) {
    const box = failure(error, id);
    if (error.kind === 'not_found') box.querySelector('h1').textContent = 'No proof with this ID';
    page.replaceChildren(box);
    return () => {};
  }
  const p = view.proof || {};
  const owner = (graph.edges || []).find((e) => e.kind === 'asserts_claim' && e.from_type === 'organ');
  const componentId = owner ? owner.from : null;
  const contracts = view.modeled_contracts || [];
  document.title = `${moduleWords(p.module)} proof · Plectis components`;
  const fact = (facet, status, glyph) => {
    const [text, caution, known] = stateWords(facet, status);
    return h('li', { class: `fact${known ? '' : ' fact--unknown'}` }, glyph, h('span', {}, h('span', { class: 'fact__text' }, text), caution ? h('span', { class: 'fact__caution' }, caution) : null));
  };
  const refs = (list) => {
    const ul = h('ul', { class: 'ref-list' });
    for (const r of list) ul.append(h('li', {}, h('span', { class: 'ref' }, r)));
    if (!list.length) ul.append(h('li', { class: 'muted' }, 'None recorded.'));
    return ul;
  };
  const sections = [];
  const section = (sid, title, ...content) => {
    const el = h('section', { id: `s-${sid}`, 'aria-labelledby': `h-${sid}` }, h('h2', { id: `h-${sid}` }, title), ...content);
    sections.push({ id: sid, el });
    return el;
  };

  const body = h('div', { class: 'reader__steps prose' });
  contracts.forEach((c, i) => {
    body.append(section(i ? `statement-${i}` : 'statement', 'The modeled statement',
      h('p', { class: 'statement' }, c.statement),
      h('div', { class: 'split' },
        h('div', {}, h('h3', {}, 'Input model'), h('p', { class: 'small' }, c.input_model)),
        h('div', {}, h('h3', {}, 'Assumptions'), h('p', { class: 'small' }, c.assumptions))),
      h('div', { class: 'limit' }, h('span', { class: 'limit__label' }, 'What the model leaves out'), c.limits),
      h('h3', {}, 'Specification'), refs(c.specification_refs || []),
      h('h3', {}, 'Entry theorems'), refs(c.entry_theorem_refs || p.entry_theorem_refs || []),
      h('ul', { class: 'facts' }, fact('requirements_review', c.requirements_review?.status, keyGlyph('absent')))));
  });

  const negatives = h('ul', { class: 'ref-list' });
  for (const n of p.negative_controls || []) {
    const kept = n.retained_result || {};
    const name = moduleWords(String(n.source_ref || '').split('/').pop().replace(/\.dfy$/, ''));
    const verdict = typeof kept.errors === 'number'
      ? (kept.errors > 0 ? `the verifier reported ${count(kept.errors, 'error')}, so the variant is rejected` : 'the verifier reported no errors, so this variant was not rejected')
      : 'no error count is recorded';
    negatives.append(h('li', {}, h('strong', {}, name), h('br'), h('span', { class: 'ref' }, n.source_ref), h('br'),
      h('span', { class: 'muted' }, `In the retained record ${verdict}. ${stateWords('fresh_prover', n.fresh_result?.status)[0]}`)));
  }
  const tasks = p.retained_verification?.verified_tasks || 0;
  body.append(
    section('verified', 'Retained verification',
      h('ul', { class: 'facts' },
        h('li', { class: 'fact' }, keyGlyph('task'), h('span', {}, `Dafny ${String(p.retained_verification?.dafny_version || '').split('+')[0]} verified ${count(tasks, 'task')}.`,
          h('span', { class: 'fact__caution' }, `Basis: ${String(p.retained_verification?.basis || 'unrecorded').replace(/_/g, ' ')}. A recorded result tied to its recorded source, not a run during this request.`))),
        fact('proof_binding', p.current_binding?.status, keyGlyph('generated')))),
    section('variants', 'Deliberately broken variants',
      h('p', { class: 'small muted' }, 'Each changes the implementation and keeps the specification; the verifier is expected to reject it. Rejecting these chosen mistakes does not show that the specification captures every intended requirement.'),
      negatives),
    section('generated', 'Generated code and callers',
      h('p', { class: 'small' }, 'The verified Dafny compiles to this Python; the component calls it through its adapter. The compiler, adapter and host are trusted, outside the proof.'),
      h('h3', {}, 'Generated Python'), refs(p.generated_refs || []),
      h('h3', {}, 'Adapter and trusted host'), refs([p.adapter_ref, ...(p.trusted_host_refs || [])].filter(Boolean))),
    section('fresh', 'Fresh checks',
      h('ul', { class: 'facts' },
        fact('fresh_prover', p.fresh_prover_result?.status || view.fresh_prover?.status, keyGlyph('absent')),
        fact('current_backend_binding', view.current_backend_binding?.status, keyGlyph('absent'))),
      h('div', { class: 'actions' },
        componentId ? h('a', { class: 'btn btn--ink', href: `/components/${encodeURIComponent(componentId)}`, 'data-route': '' }, 'Open its component') : null,
        h('a', { class: 'btn', href: `/#o=${encodeURIComponent(`kernel:${id}`)}`, 'data-route': '' }, 'Show it on the map'),
        h('a', { class: 'btn', href: withQuery('/graph', { type: 'proof', id }), 'data-route': '' }, 'Related records'))));

  const figure = chainFigure([
    { id: 'statement', title: 'Modeled statement', note: 'a stated property of one computation', state: 'stated', ink: 'azure', shape: 'kernel' },
    { id: 'verified', title: 'Retained verification', note: `${count(tasks, 'task')} verified by Dafny`, state: 'recorded', ink: 'red' },
    { id: 'variants', title: 'Broken variants', note: `${count((p.negative_controls || []).length, 'variant')} rejected in the record`, state: 'recorded', ink: 'red', shape: 'diamond' },
    { id: 'generated', title: 'Generated code', note: 'hash-bound when the index was built', state: 'recorded', ink: 'red', shape: 'square' },
    { id: 'fresh', title: 'Fresh prover run', note: 'none recorded by this view', state: 'absent', ink: 'red' },
  ], { label: `The evidence for the ${moduleWords(p.module)} proof` });

  page.replaceChildren(
    h('nav', { class: 'trail', 'aria-label': 'Breadcrumb' },
      h('a', { href: '/', 'data-route': '' }, 'Evidence map'), h('span', { 'aria-hidden': 'true' }, '/'),
      componentId ? h('a', { href: `/components/${encodeURIComponent(componentId)}`, 'data-route': '' }, componentId) : h('span', {}, 'No component found'),
      h('span', { 'aria-hidden': 'true' }, '/'), h('span', {}, id)),
    h('h1', { class: 'page-title' }, `${moduleWords(p.module)}: modeled contract and retained proof`),
    h('p', { class: 'page-lede' }, `A ${p.language === 'dafny' ? 'Dafny' : p.language || 'formal'} specification of one selected computation, verified in the retained record. It is not a proof of the whole component.`),
    h('p', { class: 'note figures' }, `Snapshot ${revision.slice(0, 12)}. A digest of the index, not a Git commit or a proof certificate.`),
    h('div', { class: 'reader' }, body, h('div', { class: 'reader__figure' }, figure.el)));
  figure.onPick((sid) => document.getElementById(`s-${sid}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  return followSections(sections, (sid) => figure.setCurrent(sid));
}
