// The component API answered from a static export, for hosts with no server.
//
// frontend/export_static.py copies every response the explorer can request
// from `plectis serve-components` into files under api/v1/ and guides/. This
// module answers the same URLs from those files, with the same envelope,
// statuses and error codes, so api.js keeps every loading rule unchanged.
// Two routes take open-ended queries and are computed here from exported
// data instead: the component list (search, filters, cursor paging) and the
// typed graph neighbourhood. Both follow src/microcosm_core/component_http.py
// line for line, and export_static.py refuses to publish unless this code
// gives identical answers to the server for every graph node and for
// every filter and search it checks (compared as parsed JSON).

import { API_ROOT, API_SCHEMA } from './api.js';

const CLASSIFICATION_FIELDS = ['family', 'evidence_class', 'real_substrate_disposition', 'truth_accounting_bucket'];
const ID_PATTERNS = {
  components: /^[a-z][a-z0-9_]*$/,
  claims: /^claim::[a-z][a-z0-9_]*$/,
  proofs: /^proof::dafny::[a-z][a-z0-9_]*$/,
  cores: /^[a-z][a-z0-9_]*$/,
  doctrine: /^(?:AX|P|AP)-[0-9]{1,3}$/,
};
const LABEL = /^[a-z][a-z0-9_]*$/;
const MAX_PAGE_SIZE = 100;
const MAX_GRAPH_DEPTH = 3;
const MAX_GRAPH_EDGES = 500;
const MAX_SEARCH_LENGTH = 160;

/** The file name an ID is exported under: safe characters kept, others as ~hex. */
export function fileId(id) {
  return String(id).replace(/[^A-Za-z0-9_.-]/g, (c) => `~${c.charCodeAt(0).toString(16).padStart(2, '0')}`);
}

class Problem extends Error {
  constructor(status, code, message) { super(message); this.status = status; this.code = code; }
}
const bad = (message = 'invalid query parameters') => { throw new Problem(400, 'invalid_parameters', message); };

function number(value, fallback, maximum) {
  if (value === undefined) return fallback;
  if (!/^[0-9]{1,5}$/.test(value) || Number(value) < 1 || Number(value) > maximum) bad('integer parameter outside its permitted range');
  return Number(value);
}

function allowed(query, names) {
  for (const key of Object.keys(query)) if (!names.includes(key)) bad('unknown query parameter');
}

function parameters(search) {
  const result = {};
  for (const [key, value] of new URLSearchParams(search)) {
    if (key in result || !key || !value) bad();
    result[key] = value;
  }
  return result;
}

// Python's tuple order on (type, id): code-point comparison, never locale order.
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const nodeKey = (type, id) => `${type}\u0000${id}`;

function base64url(text) {
  const bytes = new TextEncoder().encode(text);
  let binary = '';
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function unbase64url(token) {
  const binary = atob(token.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (token.length % 4)) % 4));
  return new TextDecoder('utf-8', { fatal: true }).decode(Uint8Array.from(binary, (c) => c.charCodeAt(0)));
}

/**
 * Build the static API over a loader. load(relativePath) resolves to the
 * parsed JSON of one exported file, or null when the file does not exist.
 * Returns fetchImpl(url) for api.js's getEnvelope.
 */
export function createStaticApi(load) {
  let graph = null;
  const once = new Map();
  const cached = (path) => {
    if (!once.has(path)) once.set(path, load(path).catch((error) => { once.delete(path); throw error; }));
    return once.get(path);
  };

  async function revision() {
    const meta = await cached('api/v1/index.json');
    return meta?.snapshot_revision || '';
  }

  function reply(status, body) {
    const text = JSON.stringify(body);
    return { ok: status >= 200 && status < 300, status, headers: { get: () => null }, text: async () => text };
  }
  const envelope = async (data) => ({ schema_version: API_SCHEMA, snapshot_revision: await revision(), data });

  async function components(query) {
    allowed(query, [...CLASSIFICATION_FIELDS, 'q', 'limit', 'cursor']);
    const all = (await cached('api/v1/components.json')).data.items;
    const meta = (await cached('api/v1/index.json')).data;
    let rows = all;
    const search = (query.q || '').trim().toLowerCase();
    if ('q' in query) {
      if (!search || query.q.length > MAX_SEARCH_LENGTH) bad('search must contain 1 to 160 characters with non-whitespace text');
      rows = rows.filter((row) => [row.organ_id, row.title, row.summary].join('\n').toLowerCase().includes(search));
    }
    for (const name of CLASSIFICATION_FIELDS) {
      if (!(name in query)) continue;
      const known = (meta.component_filters?.[name] || []).some((f) => String(f.value) === query[name]);
      if (!LABEL.test(query[name]) || !known) bad('unknown component filter');
      // The server filters on the organ record; summaries carry it as classification.
      rows = rows.filter((row) => String(row.classification?.[name]) === query[name]);
    }
    const identity = ['components', ...CLASSIFICATION_FIELDS.map((k) => query[k] ?? null), ...(search ? [search] : [])];
    return page(rows, query, identity);
  }

  async function page(rows, query, identity) {
    const limit = number(query.limit, 25, MAX_PAGE_SIZE);
    const context = JSON.stringify([identity, limit]);
    const current = await revision();
    let offset = 0;
    if (query.cursor !== undefined) {
      let cursor;
      try {
        if (query.cursor.length > 512 || !/^[A-Za-z0-9_-]+$/.test(query.cursor)) throw new Error();
        cursor = JSON.parse(unbase64url(query.cursor));
        if (!cursor || typeof cursor !== 'object' || !Number.isInteger(cursor.offset) || cursor.offset < 0
          || typeof cursor.revision !== 'string' || cursor.context !== context) throw new Error();
      } catch {
        throw new Problem(400, 'invalid_cursor', 'cursor does not match this query');
      }
      if (cursor.revision !== current) throw new Problem(409, 'stale_cursor', 'snapshot changed; restart pagination');
      if (cursor.offset > rows.length) throw new Problem(400, 'invalid_cursor', 'cursor is outside this collection');
      offset = cursor.offset;
    }
    const next = offset + limit;
    const nextCursor = next < rows.length ? base64url(JSON.stringify({ revision: current, context, offset: next })) : null;
    return { items: rows.slice(offset, next), total: rows.length, limit, next_cursor: nextCursor };
  }

  async function loadGraph() {
    if (graph) return graph;
    const dump = (await cached('api/v1/graph.json')).data;
    const nodes = new Map(dump.nodes.map(([type, id, record]) => [nodeKey(type, id), { type, id, record }]));
    const adjacency = new Map();
    const add = (key, position) => { if (!adjacency.has(key)) adjacency.set(key, []); adjacency.get(key).push(position); };
    dump.edges.forEach((edge, position) => {
      for (const [side, direction] of [['from', 'out'], ['to', 'in']]) {
        const node = nodeKey(edge[`${side}_type`], edge[side]);
        for (const selected of [null, edge.kind]) {
          add(`${node}\u0000${direction}\u0000${selected ?? ''}`, position);
          add(`${node}\u0000both\u0000${selected ?? ''}`, position);
        }
      }
    });
    for (const [key, list] of adjacency) adjacency.set(key, [...new Set(list)].sort((a, b) => a - b));
    graph = { nodes, edges: dump.edges, adjacency, edgeKinds: new Set(dump.edge_kinds), types: new Set(dump.nodes.map(([t]) => t)) };
    return graph;
  }

  async function neighbourhood(query) {
    allowed(query, ['type', 'id', 'depth', 'max_edges', 'direction', 'edge_kind']);
    const g = await loadGraph();
    const { type, id } = query;
    if (!g.types.has(type) || id === undefined || id.length > 1000) bad('graph requires a known type and bounded ID');
    const root = nodeKey(type, id);
    if (!g.nodes.has(root)) throw new Problem(404, 'unknown_node', 'unknown typed graph node');
    const depth = number(query.depth, 1, MAX_GRAPH_DEPTH);
    const cap = number(query.max_edges, 100, MAX_GRAPH_EDGES);
    const direction = query.direction ?? 'both';
    const edgeKind = query.edge_kind ?? null;
    if (!['in', 'out', 'both'].includes(direction) || (edgeKind !== null && !g.edgeKinds.has(edgeKind))) bad('unknown graph direction or edge kind');
    const queue = [[root, 0]];
    const seen = new Set([root]);
    const selected = new Set();
    const nodes = new Set([root]);
    let truncated = false;
    while (queue.length && !truncated) {
      const [node, level] = queue.shift();
      if (level === depth) continue;
      for (const position of g.adjacency.get(`${node}\u0000${direction}\u0000${edgeKind ?? ''}`) || []) {
        if (selected.has(position)) continue;
        if (selected.size === cap) { truncated = true; break; }
        selected.add(position);
        const edge = g.edges[position];
        for (const side of ['from', 'to']) {
          const neighbour = nodeKey(edge[`${side}_type`], edge[side]);
          nodes.add(neighbour);
          if (!seen.has(neighbour)) { seen.add(neighbour); queue.push([neighbour, level + 1]); }
        }
      }
    }
    const ordered = [...nodes].map((key) => g.nodes.get(key))
      .sort((a, b) => cmp(a.type, b.type) || cmp(a.id, b.id));
    return {
      root: { type, id }, depth, max_edges: cap, direction, edge_kind: edgeKind, truncated,
      nodes: ordered.map((n) => ({ type: n.type, id: n.id, record: n.record })),
      edges: [...selected].sort((a, b) => a - b).map((position) => ({ ...g.edges[position] })),
    };
  }

  async function answer(url) {
    const parsed = new URL(url, 'http://static.invalid');
    const path = parsed.pathname;
    if (path !== API_ROOT && !path.startsWith(`${API_ROOT}/`)) throw new Problem(404, 'not_found', 'unknown API route');
    const query = parameters(parsed.search);
    const rest = path.slice(API_ROOT.length + 1);
    const fixed = { '': 'index', overview: 'overview', coverage: 'coverage', 'local-runs': 'local-runs', doctrine: 'doctrine' };
    if (rest in fixed) {
      let name = fixed[rest];
      if (rest === 'overview') {
        // The overview alone takes a query: view=map, the compact map snapshot.
        allowed(query, ['view']);
        if ('view' in query && query.view !== 'map') bad('unsupported overview view');
        if (query.view === 'map') name = 'overview-map';
      } else {
        allowed(query, []);
      }
      const body = await cached(`api/v1/${name}.json`);
      if (!body) throw new Problem(404, 'not_found', 'unknown API route');
      return body;
    }
    if (rest === 'graph') return envelope(await neighbourhood(query));
    if (rest === 'components') return envelope(await components(query));
    const parts = rest.split('/');
    if (parts.length === 2 && parts[0] in ID_PATTERNS) {
      allowed(query, []);
      const identity = decodeURIComponent(parts[1]);
      if (!ID_PATTERNS[parts[0]].test(identity)) bad('malformed resource ID');
      const body = await cached(`api/v1/${parts[0]}/${fileId(identity)}.json`);
      if (!body) throw new Problem(404, 'unknown_id', 'unknown resource ID');
      return body;
    }
    throw new Problem(404, 'not_found', 'This static copy does not include that API route.');
  }

  return async function staticFetch(url) {
    try {
      return reply(200, await answer(url));
    } catch (error) {
      if (!(error instanceof Problem)) throw error;
      return reply(error.status, { schema_version: API_SCHEMA, snapshot_revision: await revision(), error: { code: error.code, message: error.message } });
    }
  };
}

/** The loader for a hosted export: files beside the page, under `root`. */
export function fileLoader(root, fetchImpl = globalThis.fetch) {
  return async (relative) => {
    const response = await fetchImpl(root + relative, { headers: { Accept: 'application/json' } });
    if (response.status === 404) return null;
    if (!response.ok) throw new TypeError(`static file ${relative} answered ${response.status}`);
    return response.json();
  };
}
