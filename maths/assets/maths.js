/* Plectis — maths subsite runtime.
   Small on purpose: the docs runtime (docs.js) is not loaded on maths pages,
   so this file carries the two behaviours the chrome needs — the theme
   toggle and the mobile sidebar drawer — with the same storage key,
   attributes, and markup the docs runtime uses, so the control looks and
   acts identically across subsites. Everything else on maths pages is
   static HTML; the universe canvas has its own file. */
(function () {
  'use strict';

  var KEY = 'plectis-theme';
  var root = document.documentElement;
  var mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function resolved() {
    var s = stored();
    if (s === 'dark' || s === 'light') return s;
    return mq && mq.matches ? 'dark' : 'light';
  }
  function apply(theme) {
    root.setAttribute('data-theme', theme);
    try { root.style.colorScheme = theme; } catch (e) {}
    if (toggle) toggle.setAttribute('aria-checked', theme === 'dark' ? 'true' : 'false');
    document.dispatchEvent(new CustomEvent('plectis:theme', { detail: theme }));
  }

  /* Same control the docs runtime injects, appended to the topbar links. */
  var toggle = null;
  function mountToggle() {
    var nav = document.querySelector('.docs-topbar__links');
    if (!nav || nav.querySelector('.theme-toggle')) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'theme-toggle';
    btn.setAttribute('role', 'switch');
    btn.setAttribute('aria-label', 'Dark mode');
    btn.innerHTML =
      '<span class="theme-toggle__track" aria-hidden="true">' +
      '<span class="theme-toggle__ico theme-toggle__ico--sun"></span>' +
      '<span class="theme-toggle__ico theme-toggle__ico--moon"></span>' +
      '<span class="theme-toggle__knob"></span>' +
      '</span>';
    btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(KEY, next); } catch (e) {}
      apply(next);
    });
    nav.appendChild(btn);
    toggle = btn;
    apply(resolved());
  }

  /* Follow OS changes only while the reader has not chosen explicitly. */
  if (mq && mq.addEventListener) {
    mq.addEventListener('change', function () {
      if (stored() !== 'dark' && stored() !== 'light') apply(resolved());
    });
  }

  function mountDrawer() {
    var btn = document.querySelector('.docs-menu-btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var open = document.body.classList.toggle('nav-open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    /* A tap on a sidebar link should close the drawer it navigated from. */
    var sidebar = document.querySelector('.docs-sidebar');
    if (sidebar) {
      sidebar.addEventListener('click', function (event) {
        var target = event.target;
        if (target && target.closest && target.closest('a')) {
          document.body.classList.remove('nav-open');
          btn.setAttribute('aria-expanded', 'false');
        }
      });
    }
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && document.body.classList.contains('nav-open')) {
        document.body.classList.remove('nav-open');
        btn.setAttribute('aria-expanded', 'false');
        btn.focus();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      mountToggle();
      mountDrawer();
    });
  } else {
    mountToggle();
    mountDrawer();
  }
})();

/* Problem-local import map. All data and file links are built into the page. */
(function () {
  'use strict';
  document.querySelectorAll('[data-source-map]').forEach(function (map) {
    var graph = JSON.parse(map.dataset.sourceMap);
    var nodes = new Map(graph.nodes.map(function (n) { return [n.id, n]; }));
    var panel = map.querySelector('[data-connections]');
    var entries = Array.from(map.querySelectorAll('[data-module]'));
    var search = map.querySelector('[data-module-search]');
    var direct = map.querySelector('[data-direct-only]');
    function element(tag, text, cls) {
      var el = document.createElement(tag);
      if (text) el.textContent = text;
      if (cls) el.className = cls;
      return el;
    }
    function column(title, ids) {
      var col = element('div', '', 'connection-column');
      col.appendChild(element('h3', title));
      if (!ids.length) col.appendChild(element('p', 'None in this map', 'note'));
      var list = element('ul');
      ids.forEach(function (id) {
        var n = nodes.get(id);
        var li = element('li');
        var button = element('button', n.label.split('.').pop());
        button.type = 'button';
        button.title = n.path || n.label;
        button.dataset.selectModule = id;
        li.appendChild(button);
        list.appendChild(li);
      });
      col.appendChild(list);
      return col;
    }
    function select(id) {
      var n = nodes.get(id);
      if (!n) return;
      panel.replaceChildren();
      panel.appendChild(column('Imported by', graph.edges.filter(function (e) { return e.target === id; }).map(function (e) { return e.source; })));
      var selected = element('div', '', 'connection-selected');
      selected.appendChild(element('span', 'Selected file', 'eyebrow'));
      selected.appendChild(element('h3', n.label.split('.').pop()));
      selected.appendChild(element('p', n.role || n.path || n.label));
      var link = element('a', 'Open on GitHub ↗', 'btn btn--primary');
      link.href = n.source_github;
      link.rel = 'external noopener';
      selected.appendChild(link);
      panel.appendChild(selected);
      panel.appendChild(column('Imports', graph.edges.filter(function (e) { return e.source === id; }).map(function (e) { return e.target; })));
      panel.hidden = false;
      entries.forEach(function (row) {
        row.querySelector('button').setAttribute('aria-pressed', row.dataset.module === id ? 'true' : 'false');
      });
    }
    map.addEventListener('click', function (event) {
      var button = event.target.closest('[data-select-module]');
      if (button) select(button.dataset.selectModule);
    });
    function filter() {
      var q = search.value.trim().toLowerCase();
      var shown = 0;
      entries.forEach(function (row) {
        row.hidden = (direct.checked && row.dataset.direct !== 'true') || row.textContent.toLowerCase().indexOf(q) === -1;
        if (!row.hidden) shown++;
      });
      map.querySelector('[data-map-count]').textContent = shown + ' of ' + entries.length + ' files';
    }
    search.addEventListener('input', filter);
    direct.addEventListener('change', filter);
    map.querySelector('[data-map-controls]').hidden = false;
    filter();
    if (entries.length) select(entries[0].dataset.module);
  });
  // Deep links into a collapsed research section reveal their destination.
  function revealHash() {
    if (!location.hash) return;
    var target;
    try { target = document.getElementById(decodeURIComponent(location.hash.slice(1))); } catch (e) { return; }
    if (!target) return;
    for (var parent = target; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
    target.scrollIntoView();
  }
  window.addEventListener('hashchange', revealHash);
  revealHash();
})();
