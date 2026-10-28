// Coverage, one kind of check at a time: the map's rings, laid out as rows
// of squares, one square per component, grouped by family (after the Lean
// Exposition checks map, site/src/checks/CheckMap.tsx). Each row keeps its
// own count out of every component; the rows overlap and are never added.

import { getModel } from '../data.js';
import { backingGlyph, h, ringStyle, ringSwatch } from '../dom.js';
import { BACKING_ORDER, CLASS_OF_BACKING, FAMILY_ORDER, TRACKS, classDescription, classWords, count, familyName, setLabels } from '../evidence.js';
import { failure } from './component.js';

const INK_CLASS = { ran: 'ink-ran', stated: 'ink-stated', saved: 'ink-saved', unknown: 'ink-unknown' };

export async function mountCoverage(root, { signal } = {}) {
  const page = h('div', { class: 'page' }, h('p', { class: 'muted', role: 'status' }, 'Loading…'));
  root.append(page);
  let model;
  try {
    model = await getModel({ signal });
    setLabels(model.filters);
  } catch (error) {
    if (signal?.aborted) return () => {};
    page.replaceChildren(failure(error, 'coverage'));
    return () => {};
  }
  if (signal?.aborted) return () => {};
  document.title = 'Coverage · Practical formal verification';
  const families = [...new Set(model.components.map((c) => c.family))]
    .sort((a, b) => (FAMILY_ORDER.indexOf(a) + 1 || 99) - (FAMILY_ORDER.indexOf(b) + 1 || 99));
  const byFamily = new Map(families.map((f) => [f, model.components.filter((c) => c.family === f)
    .sort((a, b) => BACKING_ORDER.indexOf(a.backing) - BACKING_ORDER.indexOf(b.backing) || a.title.localeCompare(b.title))]));
  const total = model.components.length;

  const rows = TRACKS.map((track) => {
    const n = track.ink === 'unknown' ? null : model.components.filter((c) => c.checks[track.id]).length;
    const squares = h('div', { class: `squares ${INK_CLASS[track.ink]}`, style: ringStyle(track) || null }, families.map((f) => h('div', { class: 'squares__family', title: familyName(f) },
      byFamily.get(f).map((c) => {
        const on = track.ink === 'unknown' ? 'unknown' : c.checks[track.id] ? 'on' : 'off';
        return h('a', {
          class: `sq sq--${on}`, href: `/components/${encodeURIComponent(c.id)}`, 'data-route': '', tabindex: '-1',
          title: `${c.title}: ${on === 'on' ? 'yes' : on === 'off' ? 'no' : 'unknown'}`,
        });
      }))));
    return h('div', { class: 'measure' },
      h('div', { class: 'measure__head' },
        h('span', { class: 'measure__name' }, ringSwatch(track), ' ', track.title),
        h('span', { class: 'measure__count' }, n === null ? 'Unknown' : `${n} of ${total}`)),
      h('p', { class: 'measure__kind' }, `${track.words} Checked by: ${track.checker}${track.when ? `, ${track.when}` : ''}.`),
      squares);
  });

  const classRows = h('table', { class: 'table', style: 'max-width:640px' },
    h('thead', {}, h('tr', {}, h('th', {}, 'What kind of component'), h('th', { class: 'num' }, 'How many'))),
    h('tbody', {}, BACKING_ORDER.map((b) => {
      const cls = CLASS_OF_BACKING[b];
      const n = model.components.filter((c) => c.evidenceClass === cls).length;
      return h('tr', {},
        h('td', {}, h('span', { class: 'key' }, backingGlyph(b, 'mark'), classWords('evidence_class', cls)),
          classDescription('evidence_class', cls) ? h('div', { class: 'small muted' }, classDescription('evidence_class', cls)) : null),
        h('td', { class: 'num' }, String(n)));
    })));

  page.replaceChildren(
    h('nav', { class: 'trail', 'aria-label': 'Breadcrumb' }, h('a', { href: '/', 'data-route': '' }, 'Map'), h('span', { 'aria-hidden': 'true' }, '/'), h('span', {}, 'Coverage')),
    h('h1', { class: 'page-title' }, 'What is checked, component by component'),
    h('p', { class: 'page-lede' }, `Each row below is one kind of check, and each square is one of the ${total} components, grouped by family. These are the same rings as on the map, laid out flat. The rows overlap, so they do not add up, and none of them is a score.`),
    h('p', { class: 'note figures' }, `Read from snapshot ${model.revision.slice(0, 12)}. Click a square to open that component.`),
    h('div', { class: 'measures' }, rows),
    h('h2', {}, 'Nothing is run by this page'),
    h('p', { class: 'prose' }, 'Every result here was saved earlier. This page does not run the prover, the tests or any rerun, so it cannot say whether today\'s code still matches the saved results.'),
    h('h2', {}, 'What kinds of component there are'),
    classRows);
  return () => {};
}
