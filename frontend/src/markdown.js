// A component's write-up, rendered for reading.
//
// The write-ups (paper_modules/<id>.md, and each core's formal README) are
// prose with a few links, lists and command blocks. They are rendered here as
// elements built from text, never parsed as HTML. A link to another
// component's write-up or to a formal README opens that page in the explorer;
// a link to a file opens it at the index's source revision under its own
// words, never as a path; a command block folds away behind "Run it
// yourself", because a reader of the write-up is not asked to read commands.

import { copyButton, h } from './dom.js';
import { sourceHref } from './evidence.js';

/** Resolve a link in a write-up at `base` (a repository path) to a repository path. */
function resolvePath(base, href) {
  const parts = base.split('/').slice(0, -1);
  for (const seg of href.split('#')[0].split('/')) {
    if (!seg || seg === '.') continue;
    if (seg === '..') parts.pop(); else parts.push(seg);
  }
  return parts.join('/');
}

/**
 * Where a link goes: an explorer route for a write-up the model knows, a
 * link to exact source, an external page, or nothing.
 */
function linkTarget(href, base, ctx) {
  if (/^https?:\/\//i.test(href)) return { href, external: true };
  if (/^[a-z]+:/i.test(href) || href.startsWith('#')) return null;
  const path = resolvePath(base, href);
  const guide = /^paper_modules\/([\w.-]+)\.md$/.exec(path);
  if (guide && ctx.componentIds?.has(guide[1])) return { href: `/components/${encodeURIComponent(guide[1])}`, route: true };
  const formal = /^formal\/(?:components\/)?([\w-]+)\/README\.md$/.exec(path);
  if (formal && ctx.proofIdOfDir?.has(formal[1])) return { href: `/proofs/${encodeURIComponent(ctx.proofIdOfDir.get(formal[1]))}`, route: true };
  const src = sourceHref(ctx.source, path);
  return src ? { href: src, external: true } : null;
}

// A write-up's plain-language lead: a block quote that opens "In plain terms."
const PLAIN = /^\*\*In plain terms\.\*\*\s*(.*)$/s;

/** The plain-language lead of a write-up, as text, or null when it has none. */
export function plainLead(markdown) {
  const lines = String(markdown || '').replace(/\r\n?/g, '\n').split('\n');
  const at = lines.findIndex((l) => /^>\s?\*\*In plain terms\.\*\*/.test(l));
  if (at < 0) return null;
  const quote = [];
  for (let i = at; i < lines.length && /^>/.test(lines[i]); i += 1) quote.push(lines[i].replace(/^>\s?/, ''));
  const text = quote.join(' ').replace(/^\*\*In plain terms\.\*\*\s*/, '').replace(/\s+/g, ' ').trim();
  return text || null;
}

const INLINE = /(\[([^\]]+)\]\(([^)\s]+)\))|(`([^`]+)`)|(\*\*([^*]+)\*\*)|(\*([^*\s][^*]*)\*)|(_([^_\s][^_]*)_)/g;

function inline(text, base, ctx) {
  const out = [];
  let at = 0;
  let m;
  // A fresh expression per call: link text is rendered by a nested call,
  // which must not move this loop's position.
  const re = new RegExp(INLINE.source, 'g');
  while ((m = re.exec(text))) {
    if (m.index > at) out.push(text.slice(at, m.index));
    if (m[1]) {
      const target = linkTarget(m[3], base, ctx);
      const label = inline(m[2], base, ctx);
      if (!target) out.push(h('span', { class: 'md-nolink' }, label));
      else if (target.route) out.push(h('a', { href: target.href, 'data-route': '' }, label));
      else out.push(h('a', { href: target.href, rel: 'noopener', target: '_blank', class: 'md-ext' }, label));
    } else if (m[4]) out.push(h('code', {}, m[5]));
    else if (m[6]) out.push(h('strong', {}, m[7]));
    else if (m[8]) out.push(h('em', {}, m[9]));
    else if (m[10]) out.push(h('em', {}, m[11]));
    at = m.index + m[0].length;
  }
  if (at < text.length) out.push(text.slice(at));
  return out;
}

/**
 * Render a write-up into elements. Options: `base` is its repository path,
 * `skipTitle` drops the first heading (the page already shows the title).
 */
export function renderWriteup(markdown, { base = '', skipTitle = true, skipPlain = false, ...ctx } = {}) {
  const lines = String(markdown || '').replace(/\r\n?/g, '\n').split('\n');
  const root = h('div', { class: 'writeup' });
  let section = root;
  let i = 0;
  let titled = false;
  const para = [];
  const flush = () => {
    if (!para.length) return;
    section.append(h('p', {}, inline(para.join(' '), base, ctx)));
    para.length = 0;
  };
  while (i < lines.length) {
    const line = lines[i];
    const fence = /^```(\w*)\s*$/.exec(line);
    if (fence) {
      flush();
      const body = [];
      i += 1;
      while (i < lines.length && !/^```\s*$/.test(lines[i])) { body.push(lines[i]); i += 1; }
      i += 1;
      const text = body.join('\n');
      section.append(h('details', { class: 'md-run' },
        h('summary', {}, 'Run it yourself'),
        h('pre', { class: 'cmd' }, text), copyButton(text)));
      continue;
    }
    const head = /^(#{1,4})\s+(.*)$/.exec(line);
    if (head) {
      flush();
      if (head[1].length === 1 && !titled && skipTitle) { titled = true; i += 1; continue; }
      titled = true;
      const words = head[2].trim();
      // A section on verification is set apart: it is where the proof starts.
      const verification = /verif|proof|formal/i.test(words);
      section = h('section', { class: `md-section${verification ? ' md-section--formal' : ''}` },
        h(head[1].length <= 2 ? 'h3' : 'h4', {}, inline(words, base, ctx)));
      root.append(section);
      i += 1;
      continue;
    }
    if (/^>\s?/.test(line)) {
      flush();
      const quote = [];
      while (i < lines.length && /^>\s?/.test(lines[i])) { quote.push(lines[i].replace(/^>\s?/, '')); i += 1; }
      const text = quote.join(' ').trim();
      const plain = PLAIN.exec(text);
      if (plain && skipPlain) continue;
      section.append(plain
        ? h('p', { class: 'md-plain' }, inline(plain[1], base, ctx))
        : h('blockquote', {}, inline(text, base, ctx)));
      continue;
    }
    const item = /^\s*(?:[-*]|\d+\.)\s+(.*)$/.exec(line);
    if (item) {
      flush();
      const ordered = /^\s*\d+\./.test(line);
      const list = h(ordered ? 'ol' : 'ul', { class: 'md-list' });
      while (i < lines.length) {
        const m = /^\s*(?:[-*]|\d+\.)\s+(.*)$/.exec(lines[i]);
        if (!m) {
          // A wrapped continuation line belongs to the item above.
          if (lines[i].trim() && /^\s{2,}/.test(lines[i]) && list.lastChild) { list.lastChild.append(' ', ...inline(lines[i].trim(), base, ctx)); i += 1; continue; }
          break;
        }
        list.append(h('li', {}, inline(m[1], base, ctx)));
        i += 1;
      }
      section.append(list);
      continue;
    }
    if (!line.trim()) { flush(); i += 1; continue; }
    para.push(line.trim());
    i += 1;
  }
  flush();
  return root;
}

// Successful write-ups are cached within their expected model revision.
const fetched = new Map();
export function fetchWriteup(kind, id, expectedRevision = '') {
  const key = JSON.stringify([expectedRevision, kind, id]);
  if (!fetched.has(key)) {
    const pending = fetch(`/guides/${kind}/${encodeURIComponent(id)}`, { headers: { Accept: 'text/markdown' } })
      .then(async (r) => {
        const revision = r.headers.get('X-Plectis-Snapshot-Revision') || '';
        const status = r.ok && expectedRevision && revision !== expectedRevision ? 409 : r.status;
        return { status, text: status === 200 ? await r.text() : '', base: r.headers.get('X-Plectis-Guide-Ref') || '', revision };
      })
      .catch(() => ({ status: 0, text: '', base: '', revision: '' }))
      .then((result) => {
        if (result.status !== 200 && fetched.get(key) === pending) fetched.delete(key);
        return result;
      });
    fetched.set(key, pending);
  }
  return fetched.get(key);
}

/** Fetch and render the write-up for a component or a core; resolves to an element or a note. */
export async function loadWriteup(kind, id, ctx, options = {}) {
  const { status, text, base } = await fetchWriteup(kind, id, ctx.revision);
  if (status === 0) return h('p', { class: 'note' }, 'The write-up could not be read: the explorer server is not reachable.');
  if (status === 409) return h('p', { class: 'note' }, 'The write-up and this view no longer share a snapshot, so the write-up is not shown. Reload the view; rebuild the index if its recorded guide has changed.');
  if (status !== 200) return h('p', { class: 'note' }, 'No write-up is recorded for this in the index.');
  return renderWriteup(text, { base, ...ctx, ...options });
}

/** The plain-language lead for a component, or null while there is none. */
export async function loadPlain(kind, id, revision = '') {
  const { status, text } = await fetchWriteup(kind, id, revision);
  return status === 200 ? plainLead(text) : null;
}
