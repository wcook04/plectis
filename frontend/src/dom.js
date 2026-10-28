// Building DOM from data. Recorded text is always set as text, never parsed
// as HTML; commands and paths are shown, never interpreted.

export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === false || value === null || value === undefined) continue;
    if (key === 'class') el.className = value;
    else if (key === 'text') el.textContent = value;
    else if (key.startsWith('on') && typeof value === 'function') el.addEventListener(key.slice(2), value);
    else if (key === 'dataset') Object.assign(el.dataset, value);
    else el.setAttribute(key, value === true ? '' : String(value));
  }
  append(el, children);
  return el;
}

export function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

const SVGNS = 'http://www.w3.org/2000/svg';
export function svg(tag, attrs = {}, ...children) {
  const el = document.createElementNS(SVGNS, tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === false || value === null || value === undefined) continue;
    el.setAttribute(key, String(value));
  }
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

// The system map's five 12-unit marks (sites/microcosm/assets/system-map.js
// GLYPHS), built as elements so they share the canvas's shapes.
export function backingGlyph(backing, extraClass = '') {
  const root = svg('svg', { class: `glyph ${extraClass}`.trim(), viewBox: '0 0 12 12', width: 12, height: 12, 'aria-hidden': 'true', focusable: 'false', fill: 'currentColor', stroke: 'currentColor', 'stroke-width': 0 });
  const ring = () => svg('circle', { cx: 6, cy: 6, r: 4.1, fill: 'none', 'stroke-width': 1.5 });
  switch (backing) {
    case 'tool': root.append(svg('circle', { cx: 6, cy: 6, r: 4.7 })); break;
    case 'bounded': root.append(ring(), svg('path', { d: 'M6 1.9a4.1 4.1 0 0 1 0 8.2z' })); break;
    case 'import': root.append(svg('rect', { x: 1.8, y: 1.8, width: 8.4, height: 8.4, rx: 1.1 })); break;
    case 'contract': root.append(ring(), svg('circle', { cx: 6, cy: 6, r: 1.8 })); break;
    case 'computes': root.append(ring()); break;
    default: root.append(svg('circle', { cx: 6, cy: 6, r: 2.2 }));
  }
  return root;
}

/** Small marks for the key: a saved record, an absent one, a kernel. */
export function keyGlyph(kind) {
  const root = svg('svg', { viewBox: '0 0 12 12', width: 12, height: 12, 'aria-hidden': 'true', focusable: 'false' });
  if (kind === 'record') root.append(svg('circle', { cx: 6, cy: 6, r: 2, fill: 'currentColor' }));
  if (kind === 'absent') root.append(svg('circle', { cx: 6, cy: 6, r: 2.8, fill: 'none', stroke: 'currentColor', 'stroke-dasharray': '1.2 1.3' }));
  if (kind === 'kernel') root.append(svg('circle', { cx: 6, cy: 6, r: 5, fill: 'none', stroke: 'var(--weave-red)', 'stroke-width': 1.1 }), svg('circle', { cx: 6, cy: 6, r: 2.6, fill: 'none', stroke: 'var(--weave-azure-glow)', 'stroke-width': 1 }), svg('circle', { cx: 6, cy: 6, r: 1, fill: 'var(--weave-red)' }));
  if (kind === 'task') root.append(svg('circle', { cx: 6, cy: 6, r: 1.6, fill: 'var(--home-ember)' }));
  if (kind === 'variant') root.append(svg('path', { d: 'M3.5 3.5l5 5M8.5 3.5l-5 5', stroke: 'currentColor', 'stroke-width': 1.2 }));
  if (kind === 'spoke') root.append(svg('path', { d: 'M1 6h10', stroke: 'var(--weave-azure-glow)', 'stroke-width': 0.9 }), svg('circle', { cx: 1.6, cy: 6, r: 1.3, fill: 'var(--weave-azure-glow)' }));
  if (kind === 'thread') root.append(svg('path', { d: 'M1 6h10', stroke: 'var(--home-ember)', 'stroke-width': 1.3 }));
  if (kind === 'wiring') root.append(svg('path', { d: 'M1 9 Q6 1 11 9', fill: 'none', stroke: 'var(--weave-azure-glow)', 'stroke-width': 1.2 }));
  if (kind === 'generated') root.append(svg('rect', { x: 3, y: 3, width: 6, height: 6, fill: 'none', stroke: 'var(--home-ember)', 'stroke-width': 1.2 }));
  if (kind === 'caller') root.append(svg('path', { d: 'M6 2.2L9.8 6 6 9.8 2.2 6z', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.2 }));
  // A citation as the map draws it: round the rim, then down into a column.
  if (kind === 'cites') root.append(svg('path', { d: 'M1 2.5h9.5M8 2.5v8.5', fill: 'none', stroke: 'var(--m-doctrine)', 'stroke-width': 1.2 }), svg('circle', { cx: 8, cy: 2.5, r: 1.5, fill: 'var(--m-doctrine)' }));
  return root;
}

// The doctrine's three marks (system-map.js DOCTRINE_GLYPHS): an axiom a
// ringed dot, a principle a diamond, a failure mode a cross.
const RULE_MARKS = {
  axiom: () => [svg('circle', { cx: 6, cy: 6, r: 4.6, fill: 'none', 'stroke-width': 1.5 }), svg('circle', { cx: 6, cy: 6, r: 1.9 })],
  principle: () => [svg('path', { d: 'M6 1.3L10.7 6L6 10.7L1.3 6Z', fill: 'none', 'stroke-width': 1.6 })],
  anti_principle: () => [svg('path', { d: 'M2.4 2.4L9.6 9.6M9.6 2.4L2.4 9.6', fill: 'none', 'stroke-width': 1.8, 'stroke-linecap': 'round' })],
};
export function ruleGlyph(kind, extraClass = '') {
  const root = svg('svg', { class: `glyph rule-mark rule-mark--${kind} ${extraClass}`.trim(), viewBox: '0 0 12 12', width: 12, height: 12, 'aria-hidden': 'true', focusable: 'false', fill: 'currentColor', stroke: 'currentColor', 'stroke-width': 0 });
  root.append(...(RULE_MARKS[kind] || RULE_MARKS.principle)());
  return root;
}

export function clear(el) { while (el.firstChild) el.firstChild.remove(); return el; }

/** The CSS that gives an element a coverage ring's own colour (tokens.css --ring-*). */
export const ringStyle = (track) => (track.ink === 'unknown' ? '' : `--ink-fill: var(--ring-${track.id})`);

/** A swatch in a ring's colour: filled, empty, or hatched for unknown. */
export function ringSwatch(track, state = 'has', extraClass = '') {
  const cls = `swatch${track.ink === 'unknown' ? ' ink-unknown' : ''}${state === 'empty' ? ' is-empty' : ''}${extraClass ? ` ${extraClass}` : ''}`;
  return h('span', { class: cls, style: state === 'empty' ? null : ringStyle(track) || null, 'aria-hidden': 'true' });
}

/** A copy button for a declared command; it copies text and runs nothing. */
export function copyButton(text, label = 'Copy command') {
  const btn = h('button', { type: 'button', class: 'textbtn copy' }, label);
  btn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = 'Copied';
    } catch {
      btn.textContent = 'Select the text to copy it';
    }
    setTimeout(() => { btn.textContent = label; }, 1600);
  });
  return btn;
}

export function announce(text) {
  const live = document.querySelector('[data-announce]');
  if (live) { live.textContent = ''; setTimeout(() => { live.textContent = text; }, 30); }
}

/**
 * A proved computation as the map draws it: a proof dial. A red ring
 * graduated with N fine ticks, one per passed proof check (the exact count);
 * a blue inner ring (the written rules) round a red dot (the checked code),
 * or the count N as a numeral when `numeral` is set; and M small crosses, the
 * broken copies the prover rejected, on an arc outside the ring (×M when M
 * is more than 4).
 */
export function dialGlyph(n = 0, m = 0, size = 44, { numeral = size >= 36 } = {}) {
  const r = 15, c = 22;
  const root = svg('svg', { class: 'dial', viewBox: '0 0 44 44', width: size, height: size, 'aria-hidden': 'true', focusable: 'false' });
  const N = Math.max(0, n | 0);
  const ticks = svg('g', { class: 'dial__ticks' });
  const tick = r * 0.26;
  if (N && (2 * Math.PI * (r - tick / 2)) / N >= 1.7) {
    for (let i = 0; i < N; i += 1) {
      const a = -Math.PI / 2 + (i / N) * 2 * Math.PI;
      ticks.append(svg('line', { x1: c + Math.cos(a) * (r - tick), y1: c + Math.sin(a) * (r - tick), x2: c + Math.cos(a) * r, y2: c + Math.sin(a) * r }));
    }
  } else if (N) {
    ticks.append(svg('circle', { class: 'dial__band', cx: c, cy: c, r: r - tick / 2, 'stroke-width': tick }));
  }
  const inner = numeral && N ? r * 0.58 : r * 0.46;
  root.append(svg('circle', { class: 'dial__face', cx: c, cy: c, r }), ticks,
    svg('circle', { class: 'dial__ring', cx: c, cy: c, r }),
    svg('circle', { class: 'dial__rules', cx: c, cy: c, r: inner }));
  if (numeral && N) {
    const t = svg('text', { class: 'dial__num', x: c, y: c + 0.3, 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': Math.min(10, inner * (String(N).length > 2 ? 1.0 : 1.2)) });
    t.textContent = String(N);
    root.append(t);
  } else {
    root.append(svg('circle', { class: 'dial__code', cx: c, cy: c, r: Math.max(1.6, inner * 0.42) }));
  }
  const M = Math.max(0, m | 0);
  const arm = 1.7, R = r + 4.2, step = 0.34;
  if (M > 4) {
    const t = svg('text', { class: 'dial__many', x: c, y: c + R + 0.5, 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': 6 });
    t.textContent = `×${M}`;
    root.append(t);
  } else {
    for (let j = 0; j < M; j += 1) {
      const a = Math.PI / 2 + (j - (M - 1) / 2) * step;
      const x = c + Math.cos(a) * R, y = c + Math.sin(a) * R;
      root.append(svg('path', { class: 'dial__cross', d: `M${x - arm} ${y - arm}L${x + arm} ${y + arm}M${x + arm} ${y - arm}L${x - arm} ${y + arm}` }));
    }
  }
  return root;
}
/** The old name, kept for any caller not yet moved. */
export const flowerGlyph = dialGlyph;
