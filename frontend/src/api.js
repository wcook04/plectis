// Read-only client for the Plectis component API (plectis_component_http_v1).
//
// Every response is an envelope {schema_version, snapshot_revision, data}. The
// revision is a digest of the served index: not a Git commit, a timestamp or a
// proof certificate. This module keeps the loading rules of
// docs/guides/frontend-implementation.md in one place: schema checks, error
// kinds, superseded requests, cursor paging within one revision, and combined
// views whose parts must come from the same snapshot.

export const API_SCHEMA = 'plectis_component_http_v1';
export const API_ROOT = '/api/v1';
const MESSAGE_LIMIT = 240;

/**
 * kind is one of: network, schema, request (400), not_found (404),
 * stale_cursor (409), server (5xx), revision (parts disagree), aborted.
 */
export class ApiError extends Error {
  constructor(kind, message, { status = 0, code = '', revision = '' } = {}) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    this.code = code;
    this.revision = revision;
  }
}

/** Join path segments, encoding each full ID (claim and proof IDs contain colons). */
export function apiPath(...segments) {
  return [API_ROOT, ...segments.map((s) => encodeURIComponent(String(s)))].join('/');
}

/** Build a query string, omitting blank values: the API rejects empty parameters. */
export function withQuery(path, params = {}) {
  const pairs = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && String(v).trim() !== '');
  if (!pairs.length) return path;
  return `${path}?${new URLSearchParams(pairs.map(([k, v]) => [k, String(v)])).toString()}`;
}

function bounded(text) {
  const value = typeof text === 'string' ? text : '';
  return value.length > MESSAGE_LIMIT ? `${value.slice(0, MESSAGE_LIMIT - 1)}…` : value;
}

/** Fetch one API URL and return {revision, data}, or throw an ApiError. */
export async function getEnvelope(url, { signal, fetchImpl = globalThis.fetch } = {}) {
  let response;
  try {
    response = await fetchImpl(url, { signal, headers: { Accept: 'application/json' } });
  } catch (error) {
    if (error && error.name === 'AbortError') throw new ApiError('aborted', 'request superseded');
    throw new ApiError('network', 'The component API could not be reached.');
  }
  let body = null;
  try {
    body = JSON.parse(await response.text());
  } catch (error) {
    if (error && error.name === 'AbortError') throw new ApiError('aborted', 'request superseded');
    body = null;
  }
  if (!body || typeof body !== 'object') {
    // The development proxy answers 502 in plain text when the API is down.
    if (!response.ok) throw new ApiError('network', 'The component API could not be reached.', { status: response.status });
    throw new ApiError('schema', 'The response was not JSON.', { status: response.status });
  }
  if (body.schema_version !== API_SCHEMA) {
    throw new ApiError('schema', `Expected ${API_SCHEMA}; received ${bounded(String(body.schema_version))}.`, { status: response.status });
  }
  if (!response.ok) {
    const code = String(body.error?.code || '');
    const message = bounded(body.error?.message) || `HTTP ${response.status}`;
    const kind = response.status === 404 ? 'not_found'
      : response.status === 409 && code === 'stale_cursor' ? 'stale_cursor'
        : response.status >= 400 && response.status < 500 ? 'request' : 'server';
    throw new ApiError(kind, message, { status: response.status, code, revision: body.snapshot_revision || '' });
  }
  if (typeof body.snapshot_revision !== 'string' || !('data' in body)) {
    throw new ApiError('schema', 'The response envelope is incomplete.', { status: response.status });
  }
  return { revision: body.snapshot_revision, data: body.data };
}

/**
 * Run only the newest of overlapping calls. Starting a call aborts the one
 * before it, and a result that arrives after a newer call started is refused,
 * so a slow early search can never replace later results.
 */
export function latestOnly() {
  let controller = null;
  let sequence = 0;
  return async function run(task) {
    controller?.abort();
    controller = new AbortController();
    const mine = ++sequence;
    const result = await task(controller.signal);
    if (mine !== sequence) throw new ApiError('aborted', 'request superseded');
    return result;
  };
}

/**
 * Load several envelopes that must describe one snapshot. A mismatch is
 * retried once from scratch; a second mismatch becomes an explicit
 * 'revision' error instead of an endless reload loop.
 */
export async function loadTogether(urls, options = {}) {
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const parts = await Promise.all(urls.map((url) => getEnvelope(url, options)));
    const revisions = new Set(parts.map((p) => p.revision));
    if (revisions.size === 1) return { revision: parts[0].revision, parts: parts.map((p) => p.data) };
  }
  throw new ApiError('revision', 'The component index changed while this view was loading.');
}

/** One filtered, paged collection held to a single snapshot revision. */
export class Collection {
  constructor(path, params = {}, { pageSize = 25, fetchImpl } = {}) {
    this.path = path;
    this.params = { ...params, limit: pageSize };
    this.fetchImpl = fetchImpl;
    this.items = [];
    this.total = 0;
    this.revision = '';
    this.nextCursor = null;
  }

  async first(signal) {
    const { revision, data } = await getEnvelope(withQuery(this.path, this.params), { signal, fetchImpl: this.fetchImpl });
    this.revision = revision;
    this.items = [...data.items];
    this.total = data.total;
    this.nextCursor = data.next_cursor;
    return this;
  }

  /** Append the next page; the cursor travels with the unchanged parameters. */
  async more(signal) {
    if (!this.nextCursor) return this;
    const url = withQuery(this.path, { ...this.params, cursor: this.nextCursor });
    const { revision, data } = await getEnvelope(url, { signal, fetchImpl: this.fetchImpl });
    if (revision !== this.revision) {
      throw new ApiError('revision', 'The component index changed; this list must restart.', { revision });
    }
    this.items = this.items.concat(data.items);
    this.total = data.total;
    this.nextCursor = data.next_cursor;
    return this;
  }
}
