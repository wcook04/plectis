// One verified computation, read in the paper's order: what it states, the
// specification as retained Dafny text, what the verifier recorded, the
// broken variants it rejected, the generated code and who calls it, and what
// is not established. A component kernel and a workflow core share the page.
// Everything comes from the overview's single snapshot, so the component, the
// excerpts and the ownership repair can never come from different revisions.

import { withQuery } from '../api.js';
import { getModel } from '../data.js';
import { h, keyGlyph } from '../dom.js';
import { callerWords, count, fileWords, moduleWords, proofShortName, setLabels, sourceHref, stateWords } from '../evidence.js';
import { chainFigure, followSections } from './chain.js';
import { failure } from './component.js';
import { loadWriteup } from '../markdown.js';
import { ownershipFigure, specificationParts, variantsPart } from './proofparts.js';

export async function mountProof(root, { id }) {
  const page = h('div', { class: 'page' }, h('p', { class: 'muted', role: 'status' }, 'Loading the proof…'));
  root.append(page);
  let model;
  try {
    model = await getModel();
    setLabels(model.filters);
  } catch (error) {
    page.replaceChildren(failure(error, id));
    return () => {};
  }
  const kernel = model.kernelById.get(id);
  const core = kernel ? null : model.cores.find((c) => c.proofId === id || c.id === id);
  const p = kernel || core;
  if (!p) {
    const box = failure({ kind: 'not_found' }, id);
    box.querySelector('h1').textContent = 'No proof with this ID';
    box.querySelector('.page-lede').textContent = `The index has no verified computation “${id}”.`;
    page.replaceChildren(box);
    return () => {};
  }
  const name = kernel ? proofShortName(kernel) : core.id === 'replay_admission' ? 'Replay admission' : moduleWords(core.id);
  const component = kernel && kernel.componentId ? model.byId.get(kernel.componentId) : null;
  document.title = `${name} · Practical formal verification`;
  const source = model.source;
  const fact = (facet, status, glyph) => {
    const [text, caution, known] = stateWords(facet, status);
    return h('li', { class: `fact${known ? '' : ' fact--unknown'}` }, glyph, h('span', {}, h('span', { class: 'fact__text' }, text), caution ? h('span', { class: 'fact__caution' }, caution) : null));
  };
  // Files named in words, each a link to exact source when there is one.
  const named = (ref, words = fileWords(ref)) => {
    const href = sourceHref(source, ref);
    return href ? h('a', { href, rel: 'noopener', target: '_blank' }, words) : h('span', {}, words);
  };
  const andList = (items) => items.flatMap((item, i) => (i === 0 ? [item] : [i === items.length - 1 ? ' and ' : ', ', item]));
  const folder = (refs) => {
    const dirs = [...new Set(refs.map((r) => r.split('/').slice(0, -1).join('/')))].sort((a, b) => a.length - b.length);
    const dir = dirs[0] || '';
    return source && dir ? `${source.repository}/tree/${source.commit}/${dir}` : null;
  };
  const sections = [];
  const section = (sid, title, ...content) => {
    const el = h('section', { id: `s-${sid}`, 'aria-labelledby': `h-${sid}` }, h('h2', { id: `h-${sid}` }, title), ...content);
    sections.push({ id: sid, el });
    return el;
  };

  const body = h('div', { class: 'reader__steps prose' });
  body.append(section('statement', 'What it promises',
    h('p', { class: 'statement' }, p.statement),
    kernel ? h('div', { class: 'split' },
      h('div', {}, h('h3', {}, 'What it takes in'), h('p', { class: 'small' }, kernel.inputModel)),
      h('div', {}, h('h3', {}, 'Assumptions'), h('p', { class: 'small' }, kernel.assumptions)))
      : h('div', {}, h('h3', {}, 'Assumptions'), h('p', { class: 'small' }, core.assumptions)),
    h('div', { class: 'limit' }, h('span', { class: 'limit__label' }, 'What the proof leaves out'), p.limits || 'No limit is written down.')));
  if (core) {
    const holder = h('div', {}, h('p', { class: 'muted small' }, 'Loading the write-up…'));
    loadWriteup('core', core.id, model.links).then((el) => holder.replaceChildren(el));
    body.append(section('writeup', 'The write-up', holder));
  }
  if (model.ownership && model.ownership.proof_id === id) {
    body.append(section('repair', 'Why the rules had to change',
      h('p', { class: 'small' }, 'This is the worked example from the paper. The old rule picked the first matching claim, so its advice depended on the order of the records. The fixed rules give a live claim priority whatever the order.'),
      ownershipFigure(model.ownership, source)));
  }
  body.append(section('spec', 'The written rules, as proved',
    h('p', { class: 'small muted' }, 'The parts of the Dafny source that state the rules, prove them, and compute the answer, with their line numbers.'),
    specificationParts(p, source)));
  body.append(section('verified', 'What the prover found',
    h('ul', { class: 'facts' },
      h('li', { class: 'fact' }, keyGlyph('task'), h('span', {}, `Dafny ${String(p.dafnyVersion).split('+')[0]} passed ${count(p.verifiedTasks || 0, 'proof check')}.`,
        h('span', { class: 'fact__caution' }, 'A saved result from when the proof was last run; this page does not run the prover.'))),
      fact('proof_binding', p.binding, keyGlyph('generated')))));
  body.append(section('variants', 'Broken versions it rejected', variantsPart(p, source)));
  const generatedLink = folder(p.generatedRefs);
  if (kernel) {
    const trusted = [kernel.adapterRef, ...kernel.trustedHostRefs].filter(Boolean);
    body.append(section('generated', 'Generated code and its caller',
      h('p', {}, `The Dafny compiler turned the verified module into ${count(kernel.generatedRefs.length, 'Python file')}. `,
        component ? h('span', {}, h('a', { href: `/components/${encodeURIComponent(component.id)}`, 'data-route': '' }, component.title), ' calls that code; it does not run a hand-written copy of the decision.') : null,
        generatedLink ? h('span', {}, ' ', h('a', { href: generatedLink, rel: 'noopener', target: '_blank' }, 'Browse the generated code ↗')) : null),
      trusted.length ? h('p', { class: 'small muted' }, 'Outside the proof, and trusted to work: its ', andList(trusted.map((r) => named(r))), ', plus the Dafny compiler and Python itself.') : null));
  } else {
    body.append(section('generated', 'Generated code and its callers',
      h('p', {}, `The Dafny compiler turned the verified module into ${count(core.generatedRefs.length, 'Python file')}, which the toolkit's own operations call.`,
        generatedLink ? h('span', {}, ' ', h('a', { href: generatedLink, rel: 'noopener', target: '_blank' }, 'Browse the generated code ↗')) : null),
      h('ul', { class: 'callers' }, core.callers.map((ref) => {
        const { api, fn } = callerWords(ref);
        return h('li', {}, named(ref, `${api} · ${fn.replace(/_/g, ' ')}`));
      }))));
    if (core.admitted.length) {
      body.append(section('routes', `The ${core.admitted.length} reruns it would judge`,
        h('p', { class: 'small muted' }, 'One per component. It accepts a rerun only if every component is covered and each result matches what was saved. Nothing has been rerun here.'),
        h('ul', { class: 'route-list' }, core.admitted.map((a) => h('li', { title: a.route },
          h('a', { href: `/components/${encodeURIComponent(a.componentId)}`, 'data-route': '' }, model.byId.get(a.componentId)?.title || a.componentId))))));
    }
  }
  body.append(section('fresh', 'What isn’t checked',
    h('ul', { class: 'facts' },
      fact('fresh_prover', p.freshProver, keyGlyph('absent')),
      fact('requirements_review', p.requirementsReview, keyGlyph('absent')),
      fact('current_backend_binding', 'not_checked', keyGlyph('absent'))),
    h('div', { class: 'actions' },
      component ? h('a', { class: 'btn btn--ink', href: `/components/${encodeURIComponent(component.id)}`, 'data-route': '' }, `Its component: ${component.title}`) : null,
      h('a', { class: 'btn', href: `/#o=${encodeURIComponent(kernel ? `kernel:${id}` : `core:${core.id}`)}`, 'data-route': '' }, 'Show it on the map'),
      kernel ? h('a', { class: 'btn', href: withQuery('/graph', { type: 'proof', id }), 'data-route': '' }, 'Related records') : null)));

  const steps = [
    { id: 'statement', title: 'The promise', note: 'what one computation must do', state: 'stated', ink: 'azure', shape: 'kernel' },
    ...(model.ownership && model.ownership.proof_id === id ? [{ id: 'repair', title: 'The fix', note: 'why the rules changed', state: 'stated', ink: 'azure' }] : []),
    { id: 'spec', title: 'Written rules', note: count(p.excerpts?.length || 0, 'piece') + ' of Dafny', state: 'stated', ink: 'azure' },
    { id: 'verified', title: 'Proved', note: `${count(p.verifiedTasks || 0, 'proof check')} passed`, state: 'recorded', ink: 'red' },
    { id: 'variants', title: 'Broken versions caught', note: count(p.mutants.length, 'deliberate mistake'), state: 'recorded', ink: 'red', shape: 'diamond' },
    { id: 'generated', title: 'Compiled and called', note: 'the proved code is the code that runs', state: 'recorded', ink: 'red', shape: 'square' },
    ...(core && core.admitted.length ? [{ id: 'routes', title: 'Reruns it judges', note: count(core.admitted.length, 'component'), state: 'configured', ink: 'azure' }] : []),
    { id: 'fresh', title: 'Not checked', note: 'no new run, no review of the rules', state: 'absent', ink: 'faint' },
  ];
  const figure = chainFigure(steps, { label: `The evidence for ${name}` });
  page.replaceChildren(
    h('nav', { class: 'trail', 'aria-label': 'Breadcrumb' },
      h('a', { href: '/', 'data-route': '' }, 'Map'), h('span', { 'aria-hidden': 'true' }, '/'),
      component ? h('a', { href: `/components/${encodeURIComponent(component.id)}`, 'data-route': '' }, component.title) : h('span', {}, kernel ? 'No component found' : 'Workflow cores'),
      h('span', { 'aria-hidden': 'true' }, '/'), h('span', {}, id)),
    h('h1', { class: 'page-title' }, name),
    h('p', { class: 'page-lede' }, kernel
      ? `A small computation inside ${component ? component.title : 'a component'}. Its rules are written in Dafny, a prover checked the code against them, and the checked code is compiled into the Python that the component calls. The proof covers this computation, not the whole component.`
      : 'A small computation that the toolkit itself uses. Its rules are written in Dafny, a prover checked the code against them, and the checked code is compiled into the Python that the toolkit calls.'),
    h('p', { class: 'note figures' }, `Read from snapshot ${model.revision.slice(0, 12)}.${source ? ` Source links open the code at commit ${source.commit.slice(0, 10)}.` : ''}`),
    h('div', { class: 'reader reader--proof' }, body, h('div', { class: 'reader__figure' }, figure.el)));
  figure.onPick((sid) => document.getElementById(`s-${sid}`)?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' }));
  return followSections(sections, (sid) => figure.setCurrent(sid));
}
