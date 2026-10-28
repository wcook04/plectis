// Routes, theme and navigation for the component explorer.
//
//   /                         the evidence map (selection in #o=<key>)
//   /catalogue?q=&family=...  search and filters, paged from the API
//   /components/<organ_id>    one component: claim and limit first
//   /proofs/<proof_id>        one retained proof view
//   /coverage                 each measure with its denominator
//   /graph?type=&id=          one-hop related records, drawn and listed

import { clear, h } from './dom.js';
// Each route owns its data and labels. A catalogue visit does not download
// the map engine or wait for unrelated overview metadata.
const pages = {
  map: () => import('./views/explorer.js').then((m) => m.mountExplorer),
  catalogue: () => import('./views/catalogue.js').then((m) => m.mountCatalogue),
  component: () => import('./views/component.js').then((m) => m.mountComponent),
  proof: () => import('./views/proof.js').then((m) => m.mountProof),
  coverage: () => import('./views/coverage.js').then((m) => m.mountCoverage),
  graph: () => import('./views/graph.js').then((m) => m.mountGraph),
};

const main = document.getElementById('main');
let unmount = null;
let activeMount = null;
let renderRun = 0;

function route(url) {
  const path = url.pathname.replace(/\/+$/, '') || '/';
  const parts = path.split('/').filter(Boolean).map((s) => decodeURIComponent(s));
  if (path === '/') return { name: 'map', load: pages.map };
  if (parts[0] === 'catalogue' && parts.length === 1) return { name: 'catalogue', load: pages.catalogue };
  if (parts[0] === 'components' && parts.length === 2) return { name: 'component', load: pages.component, id: parts[1] };
  if (parts[0] === 'proofs' && parts.length === 2) return { name: 'proof', load: pages.proof, id: parts[1] };
  if (parts[0] === 'coverage' && parts.length === 1) return { name: 'coverage', load: pages.coverage };
  if (parts[0] === 'graph' && parts.length === 1) return { name: 'graph', load: pages.graph };
  return { name: 'missing', load: async () => mountMissing };
}

function mountMissing(root) {
  root.append(h('div', { class: 'page' },
    h('h1', { class: 'page-title' }, 'No page here'),
    h('p', { class: 'page-lede' }, 'This address is not one of the explorer\'s pages. ', h('a', { href: '/', 'data-route': '' }, 'Open the evidence map'), '.')));
  return () => {};
}

async function render() {
  const mine = ++renderRun;
  activeMount?.abort();
  const controller = new AbortController();
  activeMount = controller;
  if (unmount) { try { unmount(); } catch { /* a view that failed to mount has nothing to release */ } }
  unmount = null;
  const url = new URL(window.location.href);
  const r = route(url);
  document.documentElement.classList.toggle('is-explorer', r.name === 'map');
  for (const link of document.querySelectorAll('[data-nav]')) {
    const current = link.getAttribute('data-nav') === r.name;
    if (current) link.setAttribute('aria-current', 'page'); else link.removeAttribute('aria-current');
  }
  clear(main).append(h('div', { class: 'page route-loading', role: 'status' }, 'Loading the page…'));
  try {
    const mount = await r.load();
    // Dynamic imports cannot be aborted. Check ownership before the imported
    // page can append DOM, start a request or install event listeners.
    if (mine !== renderRun || controller.signal.aborted) return;
    clear(main);
    const dispose = (await mount(main, { id: r.id, url, navigate, signal: controller.signal })) || null;
    if (mine !== renderRun) { dispose?.(); return; }
    unmount = dispose;
  } catch (error) {
    if (mine !== renderRun || controller.signal.aborted) return;
    controller.abort();
    clear(main).append(h('div', { class: 'page', role: 'alert' },
      h('h1', { class: 'page-title' }, 'This page could not be loaded'),
      h('p', { class: 'page-lede' }, 'The page code is unavailable. Reload to try again.'),
      h('button', { type: 'button', class: 'btn', onclick: () => window.location.reload() }, 'Reload')));
  }
}

export function navigate(href, { replace = false } = {}) {
  const url = new URL(href, window.location.href);
  if (url.origin !== window.location.origin) { window.location.href = url.href; return; }
  if (replace) history.replaceState(null, '', url.href); else history.pushState(null, '', url.href);
  const pending = render();
  if (!url.hash) window.scrollTo(0, 0);
  return pending;
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

// The selected view loads its own snapshot or catalogue metadata.
render();
