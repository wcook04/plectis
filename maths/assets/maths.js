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

/* Problem-local import map. All data and file links are built into the page.
   The list is the object: a file name selects it, GitHub stays on the row,
   and local imports expand under the selected file. There is no separate
   diagram. */
(function () {
  'use strict';
  document.querySelectorAll('[data-source-map]').forEach(function (map) {
    var graph = JSON.parse(map.dataset.sourceMap);
    var nodes = new Map(graph.nodes.map(function (n) { return [n.id, n]; }));
    var entries = Array.prototype.slice.call(map.querySelectorAll('[data-module]'));
    var search = map.querySelector('[data-module-search]');
    var direct = map.querySelector('[data-direct-only]');
    var selectedId = null;

    function element(tag, text, cls) {
      var el = document.createElement(tag);
      if (text) el.textContent = text;
      if (cls) el.className = cls;
      return el;
    }
    function shortName(node) {
      return node.label.split('.').pop();
    }
    function related(id, asSource) {
      var key = asSource ? 'source' : 'target';
      var other = asSource ? 'target' : 'source';
      var ids = [];
      for (var i = 0; i < graph.edges.length; i++) {
        if (graph.edges[i][key] === id) ids.push(graph.edges[i][other]);
      }
      return ids;
    }
    function nameButton(row) {
      return row.querySelector(':scope > .source-file__name, :scope > button');
    }
    function relLine(label, ids) {
      var line = element('div', '', 'source-file__rel');
      line.appendChild(element('span', label, 'source-file__rel-k'));
      if (!ids.length) {
        line.appendChild(element('span', '—', 'source-file__rel-empty'));
        return line;
      }
      ids.forEach(function (rid) {
        var node = nodes.get(rid);
        if (!node) return;
        var button = element('button', shortName(node));
        button.type = 'button';
        button.dataset.selectModule = rid;
        button.title = node.path || node.label;
        line.appendChild(button);
      });
      return line;
    }
    function clearSelection() {
      selectedId = null;
      entries.forEach(function (row) {
        row.classList.remove('is-selected');
        var name = nameButton(row);
        if (name) name.setAttribute('aria-pressed', 'false');
        var extra = row.querySelector('.source-file__rels');
        if (extra) extra.remove();
      });
    }
    function select(id) {
      var node = nodes.get(id);
      if (!node) return;
      if (selectedId === id) {
        clearSelection();
        return;
      }
      clearSelection();
      selectedId = id;
      var row = null;
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].dataset.module === id) { row = entries[i]; break; }
      }
      if (!row) return;
      row.classList.add('is-selected');
      var name = nameButton(row);
      if (name) name.setAttribute('aria-pressed', 'true');
      var box = element('div', '', 'source-file__rels');
      box.setAttribute('aria-live', 'polite');
      box.appendChild(relLine('Imports', related(id, true)));
      box.appendChild(relLine('Used by', related(id, false)));
      row.appendChild(box);
      if (row.scrollIntoView) {
        try { row.scrollIntoView({ block: 'nearest', inline: 'nearest' }); } catch (err) { row.scrollIntoView(); }
      }
    }
    map.addEventListener('click', function (event) {
      var button = event.target.closest('[data-select-module]');
      if (button) select(button.dataset.selectModule);
    });
    function filter() {
      var q = (search && search.value || '').trim().toLowerCase();
      var onlyDirect = !!(direct && direct.checked);
      var shown = 0;
      entries.forEach(function (row) {
        var hide = (onlyDirect && row.dataset.direct !== 'true') ||
          row.textContent.toLowerCase().indexOf(q) === -1;
        row.hidden = hide;
        if (!hide) shown++;
      });
      var status = map.querySelector('[data-map-count]');
      if (status) status.textContent = shown === entries.length ? '' : (shown + ' of ' + entries.length);
      if (selectedId) {
        var still = false;
        for (var i = 0; i < entries.length; i++) {
          if (entries[i].dataset.module === selectedId && !entries[i].hidden) still = true;
        }
        if (!still) clearSelection();
      }
    }
    if (search) search.addEventListener('input', filter);
    if (direct) direct.addEventListener('change', filter);
    var controls = map.querySelector('[data-map-controls]');
    if (controls) controls.hidden = false;
    var list = map.querySelector('.source-files');
    if (list && entries.length > 18) list.classList.add('is-long');
    filter();
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
