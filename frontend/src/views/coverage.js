// What the index covers, one measure at a time. Each measure keeps its own
// denominator and the API's own words for what it counts; the measures
// overlap and are never added or averaged. Whole-claim coverage is shown as
// unknown, as the API reports it. One square per component, grouped by
// family, after the Lean Exposition checks map (site/src/checks/CheckMap.tsx).

import { apiPath, loadTogether, withQuery } from '../api.js';
import { backingGlyph, h } from '../dom.js';
import { BACKING_OF, BACKING_WORDS, FAMILY_NAME, FAMILY_ORDER, count } from '../evidence.js';
import { failure } from './component.js';

const MEASURE_WORDS = {
  available_authority_artifacts: 'A saved authority record is available',
  configured_replay_routes: 'A replay is declared',
  narrow_domain_contracts: 'A selected computation has a modeled contract',
  retained_proof_metadata: 'A retained Dafny proof record exists',
  index_time_hash_bindings: 'Proof and generated files were hash-bound when the index was built',
  generated_runtime_bindings: 'Generated code is linked to its caller',
  source_linked_mutation_controls: 'Broken-variant checks are linked to source',
  historical_lean_receipt_observations: 'A saved record observed a Lean run',
};
const MEASURE_ORDER = Object.keys(MEASURE_WORDS);
const FORMAL = new Set(['narrow_domain_contracts', 'retained_proof_metadata', 'index_time_hash_bindings', 'generated_runtime_bindings', 'source_linked_mutation_controls']);

export async function mountCoverage(root) {
  const page = h('div', { class: 'page' }, h('p', { class: 'muted', role: 'status' }, 'Loading coverage…'));
  root.append(page);
  let coverage, list, revision;
  try {
    ({ revision, parts: [coverage, list] } = await loadTogether([apiPath('coverage'), withQuery(apiPath('components'), { limit: 100 })]));
  } catch (error) {
    page.replaceChildren(failure(error, 'coverage'));
    return () => {};
  }
  document.title = 'Coverage · Plectis components';
  const comps = list.items;
  const byFamily = new Map();
  for (const c of comps) {
    const f = c.classification?.family || 'unclassified';
    if (!byFamily.has(f)) byFamily.set(f, []);
    byFamily.get(f).push(c);
  }
  const families = [...byFamily.keys()].sort((a, b) => (FAMILY_ORDER.indexOf(a) + 1 || 99) - (FAMILY_ORDER.indexOf(b) + 1 || 99));
  const presence = coverage.component_presence || {};
  const keys = [...MEASURE_ORDER.filter((k) => presence[k]), ...Object.keys(presence).filter((k) => !MEASURE_WORDS[k])];

  const squares = (ids, formal) => {
    const set = new Set(ids);
    const wrap = h('div', { class: 'squares', 'aria-hidden': 'true' });
    for (const f of families) {
      const group = h('div', { class: 'squares__family', title: FAMILY_NAME[f] || f });
      for (const c of byFamily.get(f)) {
        const on = set.has(c.organ_id);
        group.append(h('a', {
          class: `sq ${on ? (formal ? 'sq--proved' : 'sq--on') : 'sq--off'}`,
          href: `/components/${encodeURIComponent(c.organ_id)}`, 'data-route': '', tabindex: '-1',
          title: `${c.title}: ${on ? 'counted' : 'not counted'}`,
        }));
      }
      wrap.append(group);
    }
    return wrap;
  };
  const listOf = (ids) => {
    const ul = h('ul', { class: 'rows' });
    for (const id of ids) {
      const c = comps.find((x) => x.organ_id === id);
      ul.append(h('li', { class: 'row' }, h('a', { href: `/components/${encodeURIComponent(id)}`, 'data-route': '' },
        backingGlyph(BACKING_OF[c?.classification?.evidence_class] || 'unknown', 'mark'), h('span', { class: 'row__title' }, c ? c.title : id),
        h('span', { class: 'row__sub' }, c ? FAMILY_NAME[c.classification?.family] || '' : 'Not in the component list'))));
    }
    return ul;
  };

  const measures = h('div', { class: 'measures' });
  for (const key of keys) {
    const m = presence[key];
    const ids = m.component_ids || [];
    measures.append(h('section', { class: 'measure', 'aria-labelledby': `m-${key}` },
      h('div', { class: 'measure__head' },
        h('h3', { class: 'measure__name', id: `m-${key}`, style: 'margin:0' }, MEASURE_WORDS[key] || `${key.replace(/_/g, ' ')} (not recognised by this explorer)`),
        h('span', { class: 'measure__count' }, `${m.numerator} of ${m.denominator} components`)),
      h('p', { class: 'measure__kind' }, `What it counts: ${m.kind}.`),
      squares(ids, FORMAL.has(key)),
      ids.length && ids.length < comps.length ? h('details', {}, h('summary', { class: 'small' }, `List the ${count(ids.length, 'component')}`), listOf(ids)) : null));
  }

  const whole = coverage.whole_claim_coverage || {};
  const fresh = coverage.fresh_results || {};
  const classCounts = coverage.evidence_class_counts || {};
  const classRows = h('table', { class: 'table', style: 'max-width:520px' },
    h('thead', {}, h('tr', {}, h('th', {}, 'How components are backed'), h('th', { class: 'num' }, 'Components'))),
    h('tbody', {}, Object.entries(classCounts).map(([cls, n]) => h('tr', {},
      h('td', {}, h('span', { class: 'key' }, backingGlyph(BACKING_OF[cls] || 'unknown', 'mark'), BACKING_WORDS[BACKING_OF[cls]] || cls)),
      h('td', { class: 'num' }, String(n))))));

  page.replaceChildren(
    h('nav', { class: 'trail', 'aria-label': 'Breadcrumb' }, h('a', { href: '/', 'data-route': '' }, 'Evidence map'), h('span', { 'aria-hidden': 'true' }, '/'), h('span', {}, 'Coverage')),
    h('h1', { class: 'page-title' }, 'What the index covers'),
    h('p', { class: 'page-lede' }, `Each measure below counts components out of ${coverage.denominator?.count ?? comps.length} registered ones, with its own meaning. The measures overlap, so they are never added, and none of them is a score.`),
    h('p', { class: 'note figures' }, `Snapshot ${revision.slice(0, 12)}. Denominator: ${coverage.denominator?.kind || 'registered components'}, from ${coverage.denominator?.source_ref || 'the registry'}.`),
    h('h2', {}, 'Whole-claim coverage'),
    h('div', { class: 'measure' },
      h('div', { class: 'measure__head' }, h('span', { class: 'measure__name' }, 'Each component\'s whole claim, mapped to evidence'),
        h('span', { class: 'measure__count' }, whole.numerator == null ? 'Unknown' : `${whole.numerator} of ${whole.denominator}`)),
      h('p', { class: 'measure__kind' }, `Status: ${String(whole.status || 'unrecorded').replace(/_/g, ' ')}. This is not zero coverage, not zero defects and not a pass.`),
      h('div', { class: 'squares', 'aria-hidden': 'true' }, families.map((f) => h('div', { class: 'squares__family' }, byFamily.get(f).map(() => h('span', { class: 'sq sq--unknown' })))))),
    h('h2', {}, 'Presence of each kind of evidence'),
    h('p', { class: 'prose small muted' }, 'Red squares count retained formal evidence about a selected computation; ink squares count declarations and saved records. A square links to its component.'),
    measures,
    h('h2', {}, 'Fresh results'),
    h('ul', { class: 'facts prose' },
      h('li', { class: 'fact' }, h('span', {}), h('span', {}, `Fresh prover results recorded: ${fresh.prover?.recorded_count ?? 0}. Status: ${String(fresh.prover?.status || '').replace(/_/g, ' ')}.`)),
      h('li', { class: 'fact' }, h('span', {}), h('span', {}, `Fresh replay results recorded: ${fresh.replay?.recorded_count ?? 0}. Status: ${String(fresh.replay?.status || '').replace(/_/g, ' ')}.`))),
    h('h2', {}, 'How the components are backed'),
    classRows,
    h('h2', {}, 'The index\'s own notes'),
    h('ul', { class: 'prose' }, (coverage.notes || []).map((n) => h('li', {}, n))));
  return () => {};
}
