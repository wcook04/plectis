// The explorer's shared frame: full screen, fit and zoom, the folding panel,
// the narrow Map / Details switch and stage-size events. Adapted from the
// Plectis site's assets/explorer.js (ai_workflow sites/microcosm), which
// wires the same frame for the universe and system maps; the logic is kept,
// wrapped as a function that returns a teardown so a route can unmount it.

export function wireExplorer(root) {
  const cleanups = [];
  const on = (target, type, fn, opts) => { target.addEventListener(type, fn, opts); cleanups.push(() => target.removeEventListener(type, fn, opts)); };
  const fire = (name, detail) => root.dispatchEvent(new CustomEvent(name, { bubbles: true, detail: detail || {} }));

  // Full screen, with a within-window fallback that Escape leaves.
  const fsButtons = [...root.querySelectorAll('[data-explorer-fullscreen]')];
  const fsEnabled = !!(document.fullscreenEnabled || document.webkitFullscreenEnabled);
  let windowMode = false;
  const host = document.documentElement;
  const fsElement = () => document.fullscreenElement || document.webkitFullscreenElement || null;
  function syncFs() {
    const onScreen = windowMode || fsElement() === host || fsElement() === root;
    document.documentElement.classList.toggle('is-map-fullscreen', onScreen);
    root.classList.toggle('is-fullscreen', onScreen);
    for (const b of fsButtons) {
      b.setAttribute('aria-pressed', onScreen ? 'true' : 'false');
      const label = b.querySelector('[data-explorer-fullscreen-label]');
      const text = onScreen ? 'Exit full screen' : 'Full screen';
      if (label) label.textContent = text; else b.setAttribute('aria-label', text);
      b.title = onScreen ? 'Exit full screen (Esc)' : 'Full screen';
    }
    requestAnimationFrame(() => fire('explorer:resize'));
  }
  for (const b of fsButtons) {
    on(b, 'click', () => {
      if (windowMode) { windowMode = false; syncFs(); return; }
      if (fsElement()) {
        const exit = document.exitFullscreen || document.webkitExitFullscreen;
        try { const done = exit.call(document); if (done && done.then) done.then(syncFs, syncFs); } catch { syncFs(); }
        return;
      }
      const expand = () => { windowMode = true; syncFs(); };
      const req = host.requestFullscreen || host.webkitRequestFullscreen;
      if (!fsEnabled || !req) { expand(); return; }
      try { const p = req.call(host); if (p && p.then) p.then(syncFs, expand); } catch { expand(); }
    });
  }
  on(document, 'fullscreenchange', syncFs);
  on(document, 'webkitfullscreenchange', syncFs);
  on(document, 'keydown', (event) => {
    if (event.key === 'Escape' && windowMode) {
      windowMode = false;
      syncFs();
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);
  syncFs();

  // The reading panel folds away and comes back from the same control.
  const panel = root.querySelector('.explorer__panel');
  const narrow = window.matchMedia('(max-width: 899px)');
  function syncPanel() {
    const folded = root.classList.contains('is-panel-collapsed');
    if (panel) panel.inert = folded && !narrow.matches;
    for (const b of root.querySelectorAll('[data-explorer-panel-toggle]')) {
      b.setAttribute('aria-expanded', folded ? 'false' : 'true');
      const label = b.querySelector('[data-explorer-panel-label]');
      const text = folded ? 'Show panel' : 'Hide panel';
      if (label) label.textContent = text; else b.setAttribute('aria-label', text);
    }
  }
  syncPanel();

  const views = [...root.querySelectorAll('[data-explorer-view]')];
  function showView(which) {
    root.setAttribute('data-explorer-shown', which);
    for (const b of views) b.setAttribute('aria-pressed', b.getAttribute('data-explorer-view') === which ? 'true' : 'false');
    if (which === 'map') fire('explorer:resize');
  }
  on(root, 'click', (ev) => {
    const t = ev.target instanceof Element ? ev.target : null;
    if (!t) return;
    if (t.closest('[data-explorer-fit]')) { ev.preventDefault(); fire('explorer:fit'); return; }
    const zoom = t.closest('[data-explorer-zoom]');
    if (zoom) { ev.preventDefault(); fire('explorer:zoom', { direction: zoom.getAttribute('data-explorer-zoom') === 'out' ? -1 : 1 }); return; }
    if (t.closest('[data-explorer-panel-toggle]')) {
      ev.preventDefault();
      root.classList.toggle('is-panel-collapsed');
      syncPanel();
      requestAnimationFrame(() => fire('explorer:resize'));
      return;
    }
    const view = t.closest('[data-explorer-view]');
    if (view) { ev.preventDefault(); showView(view.getAttribute('data-explorer-view')); }
  });
  on(root, 'explorer:selected', () => { if (narrow.matches) showView('details'); });
  showView(root.getAttribute('data-explorer-shown') || 'map');

  return () => {
    for (const undo of cleanups) undo();
    document.documentElement.classList.remove('is-map-fullscreen');
    if (fsElement()) (document.exitFullscreen || document.webkitExitFullscreen)?.call(document);
  };
}
