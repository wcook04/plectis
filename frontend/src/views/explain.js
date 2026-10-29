// The map's key, opened as a window: what every ring, mark and line means,
// in plain words, with what a filled or empty cell says and what it does
// not. The wording comes from evidence.js, so the key, the panel and the
// pages say the same thing.

import { backingGlyph, h, keyGlyph, ringSwatch } from '../dom.js';
import { BACKING_ORDER, CLASS_OF_BACKING, TRACKS, classDescription, classWords } from '../evidence.js';

let dialog = null;

function ringEntry(track) {
  const rows = [
    ['Filled', track.filled],
    ['Empty', track.empty],
    ['It does not mean', track.not],
    ['For example', track.example],
  ].filter(([, text]) => text);
  return h('li', { class: 'explain__ring' },
    h('div', { class: 'explain__ring-head' }, ringSwatch(track, track.ink === 'unknown' ? 'unknown' : 'has'),
      h('h4', {}, track.title),
      h('span', { class: 'explain__by' }, `${track.checker}${track.when ? ` · ${track.when}` : ''}`)),
    h('p', {}, track.means),
    h('dl', {}, rows.map(([term, text]) => [h('dt', {}, term), h('dd', {}, text)])));
}

function build() {
  const close = h('button', { type: 'button', class: 'explain__close', 'aria-label': 'Close' }, '×');
  const body = h('div', { class: 'explain__body' },
    h('p', { class: 'explain__lede' }, 'The map has two parts. Inside the ring are the computations that are proved, with lines to the components that use them. Outside the ring are eight rings of checks. Every component has one cell in every ring, so reading outward from a component shows everything that checks it, and the empty cells show what does not.'),
    h('h3', {}, 'The eight rings, from the component outward'),
    h('ol', { class: 'explain__rings' }, TRACKS.map(ringEntry)),
    h('h3', {}, 'Empty and hatched cells'),
    h('ul', { class: 'explain__marks' },
      h('li', {}, h('span', { class: 'swatch is-empty', 'aria-hidden': 'true' }), h('span', {}, h('strong', {}, 'Not checked. '), 'No check of that kind is recorded for the component. That is not a failure: most components were never meant to have a proof.')),
      h('li', {}, h('span', { class: 'swatch ink-unknown', 'aria-hidden': 'true' }), h('span', {}, h('strong', {}, 'Unknown. '), 'Nobody knows yet. Only the outermost ring is hatched, for every component.'))),
    h('h3', {}, 'Inside the ring'),
    h('ul', { class: 'explain__marks' },
      h('li', {}, keyGlyph('kernel'), h('span', {}, h('strong', {}, 'Flowers. '), 'Each flower is one proved computation. The blue ring is its written rules and the red dot is the code checked against them. Each petal is one proof check that passed, and each small cross is a broken copy that the prover rejected.')),
      h('li', {}, keyGlyph('kernel'), h('span', {}, h('strong', {}, 'The centre. '), 'The replay checker sits in the middle: a proved computation that decides whether a rerun of every component is accepted. Around it are three proved computations the toolkit uses itself: repair plans which results can be kept after a change, compatibility checks that a replacement behaves like the original, and views makes a public report without reading private data.')),
      h('li', {}, keyGlyph('thread'), h('span', {}, h('strong', {}, 'Red threads. '), 'Each runs from a proved computation, through the Python made from it (the square) and the code that calls it (the diamond), to the component that uses it.')),
      h('li', {}, keyGlyph('spoke'), h('span', {}, h('strong', {}, 'Blue spokes. '), 'One for each component: the rerun that is set up for it, leading to the replay checker. Choose the replay checker to light them all.')),
      h('li', {}, keyGlyph('wiring'), h('span', {}, h('strong', {}, 'Blue curves. '), 'Connections declared in the source code between components. Choose a component to see its own, or press Wiring to see them all. A connection says two components are meant to work together, not that one has called the other.'))),
    h('h3', {}, 'The shape of each component'),
    h('ul', { class: 'explain__marks' },
      BACKING_ORDER.map((b) => h('li', {}, backingGlyph(b, 'mark'), h('span', {}, h('strong', {}, `${classWords('evidence_class', CLASS_OF_BACKING[b])}. `), classDescription('evidence_class', CLASS_OF_BACKING[b]) || ''))),
      h('li', {}, backingGlyph('tool', 'mark--proved'), h('span', {}, h('strong', {}, 'Drawn in red. '), 'The component has a proved computation inside it.'))),
    h('h3', {}, 'What the map does not do'),
    h('p', {}, 'Everything on the map comes from a snapshot of the project\'s saved results. The page runs nothing: no prover, no tests and no reruns. It shows what was checked and when, not whether today\'s code still passes.'));
  const el = h('dialog', { class: 'explain', 'aria-labelledby': 'explain-title' },
    h('div', { class: 'explain__head' }, h('h2', { id: 'explain-title' }, 'What the map shows'), close),
    body);
  close.addEventListener('click', () => el.close());
  // A click on the dimmed backdrop, outside the window, closes it.
  el.addEventListener('click', (e) => {
    const r = el.getBoundingClientRect();
    if (e.target === el && (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)) el.close();
  });
  document.body.append(el);
  return el;
}

/** Open the key window; it closes with its button, Escape, or a click outside it. */
export function openExplainer(focusTrack = null) {
  if (!dialog || !dialog.isConnected) dialog = build();
  if (!dialog.open) dialog.showModal();
  const body = dialog.querySelector('.explain__body');
  body.scrollTop = 0;
  if (focusTrack) {
    const i = TRACKS.findIndex((t) => t.id === focusTrack);
    body.querySelectorAll('.explain__ring')[i]?.scrollIntoView({ block: 'start' });
  }
}
