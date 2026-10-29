// Routes, theme and navigation for the component explorer.
//
//   /                         the evidence map (selection in #o=<key>)
//   /catalogue?q=&family=...  search and filters, paged from the API
//   /components/<organ_id>    one component: claim and limit first
//   /proofs/<proof_id>        one retained proof view
//   /coverage                 each measure with its denominator
//   /graph?type=&id=          one-hop related records, drawn and listed

import { clear, h } from './dom.js';
import { mountExplorer } from './views/explorer.js';
import { mountCatalogue } from './views/catalogue.js';
import { mountComponent } from './views/component.js';
import { mountProof } from './views/proof.js';
import { mountCoverage } from './views/coverage.js';
import { mountGraph } from './views/graph.js';
import { loadFacets } from './views/catalogue-core.js';

const main = document.getElementById('main');
let unmount = null;

function route(url) {
  const path = url.pathname.replace(/\/+$/, '') || '/';
  const parts = path.split('/').filter(Boolean).map((s) => decodeURIComponent(s));
  if (path === '/') return { name: 'map', mount: mountExplorer };
  if (parts[0] === 'catalogue' && parts.length === 1) return { name: 'catalogue', mount: mountCatalogue };
  if (parts[0] === 'components' && parts.length === 2) return { name: 'component', mount: mountComponent, id: parts[1] };
  if (parts[0] === 'proofs' && parts.length === 2) return { name: 'proof', mount: mountProof, id: parts[1] };
  if (parts[0] === 'coverage' && parts.length === 1) return { name: 'coverage', mount: mountCoverage };
  if (parts[0] === 'graph' && parts.length === 1) return { name: 'graph', mount: mountGraph };
  return { name: 'missing', mount: mountMissing };
}

function mountMissing(root) {
  root.append(h('div', { class: 'page' },
    h('h1', { class: 'page-title' }, 'No page here'),
    h('p', { class: 'page-lede' }, 'This address is not one of the explorer\'s pages. ', h('a', { href: '/', 'data-route': '' }, 'Open the evidence map'), '.')));
  return () => {};
}

async function render() {
  if (unmount) { try { unmount(); } catch { /* a view that failed to mount has nothing to release */ } }
  unmount = null;
  const url = new URL(window.location.href);
  const r = route(url);
  document.documentElement.classList.toggle('is-explorer', r.name === 'map');
  for (const link of document.querySelectorAll('[data-nav]')) {
    const current = link.getAttribute('data-nav') === r.name;
    if (current) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  }
  clear(main);
  unmount = (await r.mount(main, { id: r.id, url, navigate })) || null;
}

export function navigate(href, { replace = false } = {}) {
  const url = new URL(href, window.location.href);
  if (url.origin !== window.location.origin) { window.location.href = url.href; return; }
  if (replace) history.replaceState(null, '', url.href); else history.pushState(null, '', url.href);
  render();
  if (!url.hash) window.scrollTo(0, 0);
}

document.addEventListener('click', (event) => {
  const a = event.target instanceof Element ? event.target.closest('a[data-route]') : null;
  if (!a || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  const url = new URL(a.getAttribute('href'), window.location.href);
  if (url.origin !== window.location.origin) return;
  event.preventDefault();
  navigate(url.href);
});
window.addEventListener('popstate', render);

// The theme switch remembers only a real choice (public-web-design skill):
// picking the system's own scheme clears the stored preference.
const toggle = document.querySelector('[data-theme-toggle]');
function syncToggle() {
  const dark = document.documentElement.getAttribute('data-theme') === 'dark';
  toggle.setAttribute('aria-checked', dark ? 'true' : 'false');
}
toggle.addEventListener('click', () => {
  const dark = document.documentElement.getAttribute('data-theme') !== 'dark';
  const root = document.documentElement;
  root.classList.add('theme-switching');
  root.setAttribute('data-theme', dark ? 'dark' : 'light');
  const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  try {
    if (dark === systemDark) localStorage.removeItem('plectis-theme'); else localStorage.setItem('plectis-theme', dark ? 'dark' : 'light');
  } catch { /* storage may be unavailable; the choice still applies to this page */ }
  syncToggle();
  document.dispatchEvent(new CustomEvent('plectis:theme'));
  requestAnimationFrame(() => requestAnimationFrame(() => root.classList.remove('theme-switching')));
});
syncToggle();

// Classification labels come from the API's metadata; every page reads them
// through evidence.js, so they are loaded once before the first page. A page
// still renders when the API is down, and shows its own error.
loadFacets().catch(() => {}).finally(render);
