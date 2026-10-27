// Related records: a bounded neighbourhood from the API, drawn round its
// starting node and listed in full beside the drawing. A node is named by its
// type and ID together; each edge kind keeps its name and, where the API
// gives one, its meaning. A truncated result says so and claims nothing
// about completeness.

import { apiPath, getEnvelope, latestOnly, withQuery } from '../api.js';
import { backingGlyph, h, svg } from '../dom.js';
import { BACKING_OF } from '../evidence.js';
import { failure } from './component.js';

const KIND_INK = {
  has_retained_formal_proof: 'red', binds_generated_executable: 'red', establishes_model_contract: 'red', has_formal_subclaim: 'red',
  specified_by: 'red', relies_on_trusted_host: 'red', consumed_at_runtime_hook: 'red', challenged_by_test: 'red',
  grounded_in_doctrine: 'azure', wires_to: 'azure', asserts_claim: 'azure', explained_by_primary_guide: 'azure',
};
const INK = { red: 'var(--home-ember)', azure: 'var(--weave-azure-glow)', ink: 'var(--edge)' };
const words = (k) => String(k || '').replace(/_/g, ' ');

export async function mountGraph(root, { url, navigate }) {
  const page = h('div', { class: 'page' });
  root.append(page);
  const params = {
    type: url.searchParams.get('type') || 'organ',
    id: url.searchParams.get('id') || '',
    depth: url.searchParams.get('depth') || '1',
    max_edges: url.searchParams.get('max_edges') || '100',
    direction: url.searchParams.get('direction') || 'both',
    edge_kind: url.searchParams.get('edge_kind') || '',
  };
  if (!params.id) {
    page.append(h('h1', { class: 'page-title' }, 'Related records'),
      h('p', { class: 'page-lede' }, 'Open this page from a component, proof or record to see what it connects to. ', h('a', { href: '/catalogue', 'data-route': '' }, 'Find a component'), '.'));
    return () => {};
  }
  let meta;
  try { meta = (await getEnvelope('/api/v1')).data; } catch (error) { page.append(failure(error, params.id)); return () => {}; }
  const limits = meta.limits || { graph_depth: 3, graph_edges: 500 };
  const semantics = meta.graph?.edge_semantics || {};
  const select = (name, options, value) => h('select', { name, 'aria-label': name.replace(/_/g, ' ') }, options.map(([v, label]) => h('option', { value: v, selected: v === value ? 'selected' : null }, label)));
  const controls = h('form', { class: 'controls', onsubmit: (e) => e.preventDefault() },
    h('label', {}, 'Depth ', select('depth', Array.from({ length: limits.graph_depth }, (_, i) => [String(i + 1), String(i + 1)]), params.depth)),
    h('label', {}, 'Direction ', select('direction', [['both', 'both'], ['out', 'outgoing'], ['in', 'incoming']], params.direction)),
    h('label', {}, 'Edge kind ', select('edge_kind', [['', 'any'], ...(meta.graph?.edge_kinds || []).map((k) => [k, words(k)])], params.edge_kind)),
    h('label', {}, 'At most ', h('input', { name: 'max_edges', type: 'number', min: 1, max: limits.graph_edges, value: params.max_edges, style: 'width:6em' }), ' edges'));
  const out = h('div', {});
  page.append(
    h('nav', { class: 'trail', 'aria-label': 'Breadcrumb' }, h('a', { href: '/', 'data-route': '' }, 'Evidence map'), h('span', { 'aria-hidden': 'true' }, '/'), h('span', {}, 'Related records')),
    h('h1', { class: 'page-title' }, 'Related records'),
    h('p', { class: 'page-lede' }, h('span', {}, `Starting at the ${words(params.type)} `), h('code', {}, params.id), '. Each record is named by its type and ID; each line by the kind of relation the index records.'),
    controls, out);
  const run = latestOnly();
  controls.addEventListener('change', () => {
    const form = new FormData(controls);
    for (const key of ['depth', 'direction', 'edge_kind', 'max_edges']) params[key] = String(form.get(key) || '');
    const n = Math.max(1, Math.min(limits.graph_edges, Number(params.max_edges) || 100));
    params.max_edges = String(n);
    history.replaceState(null, '', withQuery('/graph', params));
    load();
  });

  async function load() {
    out.replaceChildren(h('p', { class: 'muted', role: 'status' }, 'Loading…'));
    let env;
    try {
      env = await run((signal) => getEnvelope(withQuery(apiPath('graph'), params), { signal }));
    } catch (error) {
      if (error.kind === 'aborted') return;
      const box = failure(error, params.id);
      if (error.kind === 'not_found') box.querySelector('h1').textContent = 'No record with this type and ID';
      if (error.kind === 'request') {
        box.querySelector('h1').textContent = 'The API could not use these settings';
        box.append(h('button', { type: 'button', class: 'btn', onclick: () => navigate(withQuery('/graph', { type: params.type, id: params.id }), { replace: true }) }, 'Reset the settings'));
      }
      out.replaceChildren(box);
      return;
    }
    out.replaceChildren(render(env.data, env.revision));
  }

  function render(g, revision) {
    const rootKey = `${g.root.type}|${g.root.id}`;
    const nodes = new Map(g.nodes.map((n) => [`${n.type}|${n.id}`, n]));
    const depthOf = new Map([[rootKey, 0]]);
    const adjacency = new Map();
    for (const e of g.edges) {
      const a = `${e.from_type}|${e.from}`, b = `${e.to_type}|${e.to}`;
      if (!adjacency.has(a)) adjacency.set(a, []);
      if (!adjacency.has(b)) adjacency.set(b, []);
      adjacency.get(a).push([b, e]);
      adjacency.get(b).push([a, e]);
    }
    const queue = [rootKey];
    while (queue.length) {
      const cur = queue.shift();
      for (const [next] of adjacency.get(cur) || []) if (!depthOf.has(next)) { depthOf.set(next, depthOf.get(cur) + 1); queue.push(next); }
    }
    // Ring 1 is grouped by the kind of edge that reaches it, so a kind reads as a sector.
    const first = [...depthOf.entries()].filter(([, d]) => d === 1).map(([k]) => k);
    const kindOf = (k) => (adjacency.get(k) || []).find(([o]) => o === rootKey)?.[1].kind || '';
    first.sort((a, b) => kindOf(a).localeCompare(kindOf(b)) || a.localeCompare(b));
    const pos = new Map([[rootKey, [0, 0]]]);
    const R1 = 200, R2 = 300, R3 = 360;
    first.forEach((k, i) => { const a = -Math.PI / 2 + (i + 0.5) * (Math.PI * 2 / Math.max(1, first.length)); pos.set(k, [Math.cos(a) * R1, Math.sin(a) * R1, a]); });
    for (const ring of [2, 3]) {
      const members = [...depthOf.entries()].filter(([, d]) => d === ring).map(([k]) => k);
      const parentAngle = (k) => {
        const p = (adjacency.get(k) || []).map(([o]) => pos.get(o)).find((q) => q && q[2] !== undefined);
        return p ? p[2] : 0;
      };
      members.sort((a, b) => parentAngle(a) - parentAngle(b));
      members.forEach((k, i) => {
        const a = -Math.PI / 2 + (i + 0.5) * (Math.PI * 2 / Math.max(1, members.length));
        const r = ring === 2 ? R2 : R3;
        pos.set(k, [Math.cos(a) * r, Math.sin(a) * r, a]);
      });
    }
    const size = 820;
    const fig = svg('svg', { class: 'graph-figure', viewBox: `${-size / 2} ${-size / 2} ${size} ${size}`, role: 'img', 'aria-label': `Records within ${g.depth} steps of ${g.root.type} ${g.root.id}. The list beside the drawing holds the same relations.` });
    for (const e of g.edges) {
      const a = pos.get(`${e.from_type}|${e.from}`), b = pos.get(`${e.to_type}|${e.to}`);
      if (!a || !b) continue;
      fig.append(svg('line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1], stroke: INK[KIND_INK[e.kind] || 'ink'], 'stroke-width': KIND_INK[e.kind] ? 1.2 : 0.8, opacity: 0.7,
        'stroke-dasharray': e.kind === 'wires_to' ? '4 3' : null }, svg('title', {}, `${words(e.kind)}: ${e.from_type} ${e.from} → ${e.to_type} ${e.to}`)));
    }
    const labelled = first.length <= 40;
    for (const [k, p] of pos) {
      const n = nodes.get(k);
      const [type, id] = k.split('|');
      const isRoot = k === rootKey;
      const g1 = svg('g', { transform: `translate(${p[0]} ${p[1]})` }, svg('title', {}, `${type}: ${id}`));
      g1.append(nodeMark(type, n, isRoot));
      if (isRoot || (depthOf.get(k) === 1 && labelled)) {
        const anchor = isRoot ? 'middle' : Math.cos(p[2]) >= 0 ? 'start' : 'end';
        const dx = isRoot ? 0 : Math.cos(p[2]) * 12, dy = isRoot ? 26 : Math.sin(p[2]) * 12 + 4;
        g1.append(svg('text', { x: dx, y: dy, 'text-anchor': anchor, 'font-weight': isRoot ? 700 : 400 }, shortId(id)));
      }
      fig.append(g1);
    }
    // The plain list: every returned relation, grouped by kind.
    const byKind = new Map();
    for (const e of g.edges) {
      if (!byKind.has(e.kind)) byKind.set(e.kind, []);
      byKind.get(e.kind).push(e);
    }
    const groups = h('div', { class: 'edge-groups' });
    for (const [kind, list] of [...byKind.entries()].sort()) {
      const ul = h('ul', { class: 'ref-list' });
      for (const e of list) {
        ul.append(h('li', {}, endLink(e.from_type, e.from), h('span', { class: 'muted' }, ` ${words(kind)} → `), endLink(e.to_type, e.to),
          e.ref_kind || e.role ? h('span', { class: 'muted' }, ` (${e.ref_kind || e.role})`) : null));
      }
      groups.append(h('h3', {}, `${words(kind)} (${list.length})`), semantics[kind] ? h('p', { class: 'note' }, semantics[kind]) : null, ul);
    }
    return h('div', {},
      g.truncated
        ? h('div', { class: 'state state--error', role: 'status' }, h('strong', {}, `Truncated at ${g.max_edges} edges. `), 'The index has more relations within this depth; this view makes no claim to be complete. Raise the limit or choose one edge kind.')
        : h('p', { class: 'note figures' }, `${g.edges.length} relations among ${g.nodes.length} records, within ${g.depth} ${g.depth === 1 ? 'step' : 'steps'}, ${g.direction === 'both' ? 'in both directions' : g.direction === 'in' ? 'incoming' : 'outgoing'}. Snapshot ${revision.slice(0, 12)}.`),
      h('div', { class: 'graph-layout' }, h('div', {}, fig, h('p', { class: 'note' }, 'Red lines join retained formal evidence; azure lines are stated relations (claims, doctrine, declared wiring, dashed); grey lines are navigation and saved records.')), groups));
  }

  function endLink(type, id) {
    const label = h('span', {}, h('span', { class: 'muted' }, `${type} `), h('span', { class: 'ref' }, id));
    if (type === 'organ') return h('a', { href: `/components/${encodeURIComponent(id)}`, 'data-route': '' }, label);
    if (type === 'proof') return h('a', { href: `/proofs/${encodeURIComponent(id)}`, 'data-route': '' }, label);
    if (['claim', 'subclaim', 'route', 'family', 'doctrine_ref'].includes(type)) {
      return h('a', { href: withQuery('/graph', { type, id }), 'data-route': '' }, label);
    }
    return label;
  }

  load();
  return () => {};
}

function shortId(id) {
  const s = String(id).split('/').pop().replace(/^(claim|subclaim|proof::dafny|replay|specification)::/, '');
  return s.length > 34 ? `${s.slice(0, 33)}…` : s;
}

function nodeMark(type, record, isRoot) {
  const r = isRoot ? 11 : 6;
  if (type === 'organ') {
    const g = backingGlyph(BACKING_OF[record?.record?.evidence_class || record?.evidence_class] || 'unknown', 'mark');
    g.setAttribute('x', -r); g.setAttribute('y', -r); g.setAttribute('width', r * 2); g.setAttribute('height', r * 2);
    return svg('g', {}, svg('circle', { r: r + 2, fill: 'var(--page)' }), g);
  }
  if (type === 'proof') return svg('g', {}, svg('circle', { r: r + 1, fill: 'var(--page)', stroke: 'var(--weave-azure-glow)', 'stroke-width': 1.6 }), svg('circle', { r: r * 0.4, fill: 'var(--home-ember)' }));
  if (type === 'claim' || type === 'subclaim' || type === 'specification') return svg('circle', { r, fill: 'var(--page)', stroke: 'var(--weave-azure-glow)', 'stroke-width': 1.5 });
  if (type === 'doctrine_ref') return svg('path', { d: `M0 ${-r}L${r} 0L0 ${r}L${-r} 0z`, fill: 'var(--page)', stroke: 'var(--weave-azure-glow)', 'stroke-width': 1.3 });
  if (type === 'receipt' || type === 'artifact') return svg('circle', { r: r * 0.55, fill: 'var(--ink)' });
  if (type === 'route') return svg('path', { d: `M0 ${-r}L${r} ${r * 0.8}L${-r} ${r * 0.8}z`, fill: 'var(--page)', stroke: 'var(--muted)', 'stroke-width': 1.2 });
  if (type === 'family') return svg('circle', { r: r + 3, fill: 'none', stroke: 'var(--ink)', 'stroke-width': 1.4 });
  return svg('rect', { x: -r * 0.7, y: -r * 0.7, width: r * 1.4, height: r * 1.4, fill: 'var(--page)', stroke: 'var(--muted)', 'stroke-width': 1.2 });
}
