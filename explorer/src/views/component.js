// One component, read as a page: what it does in plain words, its write-up,
// and beside it the same column of checks the map draws round the ring.
// Facts the API keeps apart stay apart: the verified kernel, the saved runs
// and what is not established each have their own place, and nothing is
// shown as a path or a command for the reader to decode.

import { ApiError, apiPath, getEnvelope, withQuery } from '../api.js';
import { getModel } from '../data.js';
import { backingGlyph, h, keyGlyph, ringSwatch, ruleGlyph } from '../dom.js';
import {
  TRACKS, classDescription, classWords, count, dayWords, familyName, proofShortName, ruleKindWords, setLabels, stateWords,
} from '../evidence.js';
import { renderGuide } from '../markdown.js';
import { runsStrip } from './proofparts.js';

const INK_CLASS = { ran: 'ink-ran', stated: 'ink-stated', saved: 'ink-saved', unknown: 'ink-unknown' };

export async function mountComponent(root, { id, signal }) {
  const page = h('div', { class: 'page' }, h('p', { class: 'muted', role: 'status' }, 'Loading the component…'));
  root.append(page);
  let model, detail;
  try {
    // Both reads use the same cancellation signal; neither depends on the other.
    const readParts = () => Promise.all([
      getModel({ signal }), getEnvelope(apiPath('components', id), { signal }),
    ]);
    let envelope;
    [model, envelope] = await readParts();
    if (envelope.revision !== model.revision) {
      [model, envelope] = await readParts();
      if (envelope.revision !== model.revision) throw new ApiError('revision', 'The component index changed while loading.');
    }
    setLabels(model.filters);
    if (!model.byId.has(id)) throw new ApiError('not_found', `No component ${id}`);
    detail = envelope.data;
  } catch (error) {
    if (signal?.aborted) return () => {};
    page.replaceChildren(failure(error, id));
    return () => {};
  }
  if (signal?.aborted) return () => {};
  const c = model.byId.get(id);
  const claim = detail.claim || {};
  const facets = claim.card?.assurance_facets || {};
  const kernel = c.kernelId ? model.kernelById.get(c.kernelId) : null;
  document.title = `${c.title} · Practical formal verification`;

  const fact = (facet, status, glyph) => {
    const [text, caution, known] = stateWords(facet, status);
    return h('li', { class: `fact${known ? '' : ' fact--unknown'}` }, glyph,
      h('span', {}, h('span', { class: 'fact__text' }, text), caution ? h('span', { class: 'fact__caution' }, caution) : null));
  };
  const section = (sid, title, ...content) => h('section', { id: `s-${sid}`, 'aria-labelledby': `h-${sid}` }, h('h2', { id: `h-${sid}` }, title), ...content);

  const plain = h('p', { class: 'page-plain' }, c.plain || c.summary);
  const writeup = renderGuide(detail.guide, model.links, { skipPlain: !!c.plain });

  const main = h('div', { class: 'reader__steps' },
    section('claim', 'What it covers',
      h('div', { class: 'limit' }, claim.claim_ceiling_restated || claim.claim_ceiling || 'No limit is written down.')),
    kernel ? section('contract', 'Its proved part',
      h('p', { class: 'small' }, 'One decision inside this component is made by a small computation whose code a prover has checked against written rules. The component calls that checked code; the rest of the component is outside the proof.'),
      h('div', { class: 'kernel-callout' },
        h('p', { class: 'kernel-callout__name' }, keyGlyph('kernel'), proofShortName(kernel)),
        h('p', { class: 'statement' }, kernel.statement),
        h('p', { class: 'small muted' }, `${count(kernel.verifiedTasks || 0, 'proof check')} passed, and ${count(kernel.mutants.length, 'deliberately broken version')} rejected.`),
        h('div', { class: 'actions' }, h('a', { class: 'btn btn--ink', href: `/proofs/${encodeURIComponent(kernel.id)}`, 'data-route': '' }, 'Open the proof page')))) : null,
    section('writeup', 'In detail', writeup),
    section('records', `Past runs (${c.receipts.length})`,
      h('p', { class: 'small muted' }, 'Saved results of earlier runs, newest first. They are old results, not checks of today\'s code.'),
      runsStrip(c.receipts, model.source)),
    doctrineSection(model, c),
    connectionsSection(model, c),
    section('open', 'What isn’t checked',
      h('ul', { class: 'facts' },
        fact('whole_claim', facets.whole_claim?.status, keyGlyph('absent')),
        fact('requirements_review', facets.requirements_review?.status, keyGlyph('absent')),
        fact('fresh_replay', detail.evidence_state?.fresh_replay?.status, keyGlyph('absent')),
        fact('current_backend_binding', detail.evidence_state?.current_backend_binding?.status, keyGlyph('absent'))),
      h('div', { class: 'actions' },
        h('a', { class: 'btn btn--ink', href: `/#o=${encodeURIComponent(`comp:${id}`)}`, 'data-route': '' }, 'Show it on the map'),
        h('a', { class: 'btn', href: withQuery('/graph', { type: 'organ', id }), 'data-route': '' }, 'Related records'))));

  const aside = h('aside', { class: 'reader__figure checks-aside', 'aria-label': 'Checks recorded for it' },
    h('p', { class: 'checks-aside__title' }, 'Checks recorded for it'),
    h('ul', { class: 'column' }, [...TRACKS].map((t) => {
      const has = t.ink === 'unknown' ? 'unknown' : c.checks[t.id] ? 'has' : 'empty';
      return h('li', { class: `column__row${has === 'empty' ? ' is-empty' : ''}` },
        ringSwatch(t, has),
        h('span', { class: 'column__title' }, t.title), h('span', { class: 'column__by' }, t.checker));
    })),
    h('p', { class: 'note' }, 'Filled means the check is recorded for this component; empty means it is not. The hatched one is unknown for every component.'),
    h('ul', { class: 'facts' },
      h('li', { class: 'fact' }, backingGlyph(c.backing, kernel ? 'mark--proved' : 'mark'),
        h('span', {}, classWords('evidence_class', c.evidenceClass), h('span', { class: 'fact__caution' }, classDescription('evidence_class', c.evidenceClass)))),
      facets.host_tests?.status ? fact('host_tests', facets.host_tests.status, keyGlyph('caller')) : null));

  page.replaceChildren(
    h('nav', { class: 'trail', 'aria-label': 'Breadcrumb' },
      h('a', { href: '/', 'data-route': '' }, 'Map'), h('span', { 'aria-hidden': 'true' }, '/'),
      h('a', { href: withQuery('/catalogue', { family: c.family }), 'data-route': '' }, familyName(c.family))),
    h('h1', { class: 'page-title' }, c.title),
    plain,
    h('div', { class: 'reader reader--component' }, main, aside));
  return () => {};
}

// The rules its record lists, each in plain words where the doctrine's
// reader content has them, and each opening that rule on the map's halo.
function doctrineSection(model, c) {
  const rules = (c.ruleIds || []).map((id) => model.ruleById.get(id)).filter(Boolean);
  if (!rules.length) return null;
  return h('section', { id: 's-rules' }, h('h2', {}, `Rules its record lists (${rules.length})`),
    h('p', { class: 'small muted' }, 'The axioms (basic assumptions) and principles (working rules) its own record lists.'),
    h('ul', { class: 'doctrine' }, rules.map((r) => h('li', {},
      h('a', { href: `/#o=${encodeURIComponent(`rule:${r.id}`)}`, 'data-route': '' }, ruleGlyph(r.kind), ' ', h('span', { class: `doc-id doc-id--${r.kind}` }, r.id), ' ', h('strong', {}, r.title)),
      h('span', { class: 'muted small' }, ` · ${ruleKindWords(r.kind)}`),
      r.reader?.plain ? h('p', { class: 'small', style: 'margin:0.25rem 0 0' }, r.reader.plain) : null))));
}

function connectionsSection(model, c) {
  const wired = model.wires.filter(([a, b]) => a === c.id || b === c.id).map(([a, b]) => (a === c.id ? b : a));
  const imports = [...c.importsOut.map((e) => [e.to, true]), ...c.importsIn.map((e) => [e.from, false])];
  if (!wired.length && !imports.length) return null;
  const row = (id, sub) => {
    const other = model.byId.get(id);
    if (!other) return null;
    return h('li', { class: 'row' }, h('a', { href: `/components/${encodeURIComponent(id)}`, 'data-route': '' },
      backingGlyph(other.backing, other.kernelId ? 'mark--proved' : 'mark'), h('span', { class: 'row__title' }, other.title),
      h('span', { class: 'row__sub' }, sub)));
  };
  return h('section', { id: 's-links' }, h('h2', {}, `Connections (${wired.length + imports.length})`),
    h('p', { class: 'small muted' }, 'Connections declared in the source code. They say these components are meant to work together, not that one has called the other.'),
    h('ul', { class: 'rows' },
      imports.map(([id, out]) => row(id, out ? 'Its code imports this one' : 'This one\'s code imports it')),
      wired.map((id) => row(id, `Declared connection · ${familyName(model.byId.get(id)?.family)}`))));
}

export function failure(error, id) {
  const wrap = h('div', {});
  if (error.kind === 'not_found') {
    wrap.append(h('h1', { class: 'page-title' }, 'No component with this ID'),
      h('p', { class: 'page-lede' }, `There is no component with the ID “${id}”. IDs come from the project’s list of components and are not made from titles.`));
  } else if (error.kind === 'network') {
    wrap.append(h('h1', { class: 'page-title' }, 'The data server is not reachable'),
      h('p', { class: 'page-lede' }, 'Start the explorer from the repository with make explorer, then reload this page.'));
  } else if (error.kind === 'schema') {
    wrap.append(h('h1', { class: 'page-title' }, 'The data server sent a format this explorer cannot read'), h('p', { class: 'page-lede' }, error.message));
  } else if (error.kind === 'revision') {
    wrap.append(h('h1', { class: 'page-title' }, 'The data changed while loading'),
      h('p', { class: 'page-lede' }, 'The parts of this page came from different snapshots twice, so none of them is shown. ', h('a', { href: window.location.href, 'data-route': '' }, 'Load it again'), '.'));
  } else {
    wrap.append(h('h1', { class: 'page-title' }, 'This page could not be loaded'), h('p', { class: 'page-lede' }, error.message));
  }
  wrap.append(h('div', { class: 'actions' }, h('a', { class: 'btn', href: '/', 'data-route': '' }, 'Open the map'), h('a', { class: 'btn', href: '/catalogue', 'data-route': '' }, 'Search the components')));
  return wrap;
}

export { dayWords };
