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
  if (kind === 'kernel') root.append(svg('circle', { cx: 6, cy: 6, r: 4.4, fill: 'none', stroke: 'var(--weave-azure-glow)', 'stroke-width': 1.5 }), svg('circle', { cx: 6, cy: 6, r: 1.7, fill: 'var(--home-ember)' }));
  if (kind === 'task') root.append(svg('circle', { cx: 6, cy: 6, r: 1.6, fill: 'var(--home-ember)' }));
  if (kind === 'variant') root.append(svg('path', { d: 'M3.5 3.5l5 5M8.5 3.5l-5 5', stroke: 'currentColor', 'stroke-width': 1.2 }));
  if (kind === 'spoke') root.append(svg('path', { d: 'M1 6h10', stroke: 'var(--weave-azure-glow)', 'stroke-width': 0.9 }), svg('circle', { cx: 1.6, cy: 6, r: 1.3, fill: 'var(--weave-azure-glow)' }));
  if (kind === 'thread') root.append(svg('path', { d: 'M1 6h10', stroke: 'var(--home-ember)', 'stroke-width': 1.3 }));
  if (kind === 'wiring') root.append(svg('path', { d: 'M1 9 Q6 1 11 9', fill: 'none', stroke: 'var(--weave-azure-glow)', 'stroke-width': 1.2 }));
  if (kind === 'generated') root.append(svg('rect', { x: 3, y: 3, width: 6, height: 6, fill: 'none', stroke: 'var(--home-ember)', 'stroke-width': 1.2 }));
  if (kind === 'caller') root.append(svg('path', { d: 'M6 2.2L9.8 6 6 9.8 2.2 6z', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.2 }));
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
