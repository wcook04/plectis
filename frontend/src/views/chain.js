// The evidence chain for one component, drawn as a sticky figure beside the
// reading column. Its order is the paper's chain (property, specification,
// verification, generated code, caller, run record) followed by the facts the
// index keeps separately. A step that is not recorded is drawn hollow and its
// link dashed; an unknown is hatched. The section in view lights its step,
// following the Lean Exposition reader's "follow the text" pane
// (lean-exposition site/src/reader/ReaderPage.tsx, page/MapPane.tsx).

import { h, svg } from '../dom.js';

const ROW = 58;
const INK = {
  red: 'var(--home-ember)',
  azure: 'var(--weave-azure-glow)',
  ink: 'var(--ink)',
  faint: 'var(--m-faint)',
};

/**
 * steps: [{ id, title, note, state: 'recorded'|'stated'|'configured'|'absent'|'unknown', ink, shape }]
 * Returns { el, setCurrent(id) }.
 */
export function chainFigure(steps, { label }) {
  const width = 420;
  const height = steps.length * ROW + 24;
  const root = svg('svg', { class: 'chain-figure', viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': label });
  const defs = svg('defs', {},
    svg('pattern', { id: 'chain-hatch', width: 4, height: 4, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' },
      svg('line', { x1: 0, y1: 0, x2: 0, y2: 4, stroke: 'var(--muted)', 'stroke-width': 1.4 })));
  root.append(defs);
  const x = 28;
  steps.forEach((step, i) => {
    const y = 26 + i * ROW;
    if (i < steps.length - 1) {
      const next = steps[i + 1];
      const broken = next.state === 'absent' || next.state === 'unknown' || step.state === 'absent';
      root.append(svg('line', {
        x1: x, y1: y + 11, x2: x, y2: y + ROW - 11,
        stroke: broken ? 'var(--muted)' : INK[step.ink] || INK.ink,
        'stroke-width': broken ? 1 : 1.6,
        'stroke-dasharray': broken ? '2 4' : null,
        opacity: broken ? 0.7 : 0.85,
      }));
    }
    const g = svg('g', { class: 'chain-step', 'data-step': step.id, tabindex: 0, role: 'link', 'aria-label': `${step.title}. ${step.note}` });
    g.append(mark(step, x, y));
    g.append(svg('text', { x: x + 26, y: y - 1, 'font-size': 15, 'font-weight': 600, fill: 'var(--ink)' }, step.title));
    g.append(svg('text', { x: x + 26, y: y + 17, 'font-size': 12.5, fill: 'var(--muted)' }, step.note));
    root.append(g);
  });
  const el = h('figure', { class: 'chain', style: 'margin:0' }, root,
    h('figcaption', { class: 'note' }, 'Filled: recorded in the snapshot. Hollow: only written down, or not recorded. Hatched: unknown. Red marks something a program ran; blue marks something written down.'));
  return {
    el,
    setCurrent(id) {
      root.classList.toggle('has-current', !!id);
      for (const g of root.querySelectorAll('.chain-step')) g.classList.toggle('is-current', g.getAttribute('data-step') === id);
    },
    onPick(fn) {
      root.addEventListener('click', (e) => {
        const g = e.target instanceof Element ? e.target.closest('.chain-step') : null;
        if (g) fn(g.getAttribute('data-step'));
      });
      root.addEventListener('keydown', (e) => {
        const g = e.target instanceof Element ? e.target.closest('.chain-step') : null;
        if (g && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); fn(g.getAttribute('data-step')); }
      });
    },
  };
}

function mark(step, x, y) {
  const color = INK[step.ink] || INK.ink;
  const filled = step.state === 'recorded';
  const g = svg('g', {});
  const common = { stroke: color, 'stroke-width': 1.6 };
  if (step.state === 'unknown') {
    g.append(svg('circle', { cx: x, cy: y + 4, r: 9, fill: 'url(#chain-hatch)', stroke: 'var(--muted)', 'stroke-width': 1.2 }));
    return g;
  }
  const fill = filled ? color : 'var(--page)';
  if (step.shape === 'square') g.append(svg('rect', { x: x - 7.5, y: y - 3.5, width: 15, height: 15, rx: 1.5, fill, ...common }));
  else if (step.shape === 'diamond') g.append(svg('path', { d: `M${x} ${y - 6}L${x + 10} ${y + 4}L${x} ${y + 14}L${x - 10} ${y + 4}z`, fill, ...common }));
  else if (step.shape === 'kernel') {
    g.append(svg('circle', { cx: x, cy: y + 4, r: 9, fill: 'var(--page)', stroke: INK.azure, 'stroke-width': 1.8 }));
    g.append(svg('circle', { cx: x, cy: y + 4, r: 3.4, fill: INK.red }));
  } else if (step.shape === 'records') {
    for (let i = 0; i < 3; i += 1) g.append(svg('circle', { cx: x - 7 + i * 7, cy: y + 4, r: 2.6, fill: filled ? color : 'none', stroke: color, 'stroke-width': 1 }));
  } else {
    g.append(svg('circle', { cx: x, cy: y + 4, r: 8.5, fill, ...common, 'stroke-dasharray': step.state === 'absent' ? '2 2.5' : null }));
  }
  return g;
}

/** Light the step whose section stands under a line 35% down the window. */
export function followSections(sections, onCurrent) {
  let frame = 0;
  let current = null;
  const update = () => {
    frame = 0;
    const line = window.innerHeight * 0.35;
    let found = sections[0]?.id || null;
    for (const s of sections) {
      const r = s.el.getBoundingClientRect();
      if (r.top <= line) found = s.id;
    }
    if (found !== current) { current = found; onCurrent(found); }
  };
  const onScroll = () => { if (!frame) frame = requestAnimationFrame(update); };
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll);
  update();
  return () => {
    window.removeEventListener('scroll', onScroll);
    window.removeEventListener('resize', onScroll);
    if (frame) cancelAnimationFrame(frame);
  };
}
