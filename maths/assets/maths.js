/* Plectis — maths subsite runtime.
   Theme toggle, mobile drawer, and deferred MathJax typesetting. The shared
   docs runtime still loads on these pages (copy-text, terms); this file only
   carries maths-specific behaviour. Do not stamp html.js here: that class
   means docs.js is ready, and the page-tools CSS keys off it. */
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

window.__plectisTypesetPage = function (MathJax) {
  /* A dossier inlines the short paper. The stage wraps article.lean-paper,
     so typeset each body child, not the whole stage. Visible chunks first;
     the rest wait for IntersectionObserver. */
  var stages = Array.prototype.slice.call(
    document.querySelectorAll('.paper-stage')
  );
  if (!stages.length) {
    return MathJax.typesetPromise();
  }
  function chunksOf(stage) {
    var root = stage.querySelector('.lean-paper__body') || stage;
    var kids = Array.prototype.filter.call(root.children, function (el) {
      return el.nodeType === 1 && el.tagName !== 'SCRIPT';
    });
    return kids.length ? kids : [stage];
  }
  var chunks = [];
  stages.forEach(function (stage) {
    chunksOf(stage).forEach(function (chunk) { chunks.push(chunk); });
  });
  function inView(el) {
    var r = el.getBoundingClientRect();
    var vh = window.innerHeight || 800;
    return r.bottom > 0 && r.top < vh + 240;
  }
  var queued = [];
  function already(node) {
    return queued.indexOf(node) !== -1;
  }
  function typeset(nodes) {
    var fresh = nodes.filter(function (node) { return !already(node); });
    fresh.forEach(function (node) { queued.push(node); });
    if (!fresh.length) return Promise.resolve();
    return MathJax.typesetPromise(fresh).then(function () {
      fresh.forEach(function (node) { node.classList.add('is-typeset'); });
    });
  }
  var first = chunks.filter(inView);
  if (!first.length) first = [chunks[0]];
  var rest = chunks.filter(function (chunk) {
    return first.indexOf(chunk) === -1;
  });
  return typeset(first).then(function () {
    if (!rest.length) return;
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          io.unobserve(entry.target);
          typeset([entry.target]);
        });
      }, { rootMargin: '640px 0px' });
      rest.forEach(function (node) { io.observe(node); });
    } else {
      var idle = window.requestIdleCallback || function (cb) { setTimeout(cb, 120); };
      function drain(index) {
        if (index >= rest.length) return;
        idle(function () {
          typeset([rest[index]]).then(function () { drain(index + 1); });
        });
      }
      drain(0);
    }
    var prefetch = window.requestIdleCallback || function (cb) { setTimeout(cb, 120); };
    prefetch(function () { typeset(rest.slice(0, 1)); });
    window.addEventListener('hashchange', function () {
      typeset(chunks.filter(inView));
    });
  });
};


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
    function rowFor(id) {
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].dataset.module === id) return entries[i];
      }
      return null;
    }
    function showRow(row, fromPaper) {
      if (!row || !row.scrollIntoView) return;
      var block = fromPaper ? 'center' : 'nearest';
      try { row.scrollIntoView({ block: block, inline: 'nearest' }); } catch (err) { row.scrollIntoView(); }
    }
    function select(id, opts) {
      opts = opts || {};
      var node = nodes.get(id);
      if (!node) return false;
      if (!opts.force && selectedId === id) {
        clearSelection();
        return true;
      }
      var row = rowFor(id);
      if (!row) return false;
      if (selectedId !== id) {
        clearSelection();
        selectedId = id;
        row.classList.add('is-selected');
        var name = nameButton(row);
        if (name) name.setAttribute('aria-pressed', 'true');
        var box = element('div', '', 'source-file__rels');
        box.setAttribute('aria-live', 'polite');
        box.appendChild(relLine('Imports', related(id, true)));
        box.appendChild(relLine('Used by', related(id, false)));
        row.appendChild(box);
      }
      if (opts.fromPaper) {
        try { map.scrollIntoView({ block: 'start' }); } catch (err) { map.scrollIntoView(); }
      }
      showRow(row, !!opts.fromPaper);
      return true;
    }
    map.__selectModule = select;
    map.__hasModule = function (id) { return nodes.has(id); };
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

  function moduleIdFromGithub(href) {
    var match = String(href || '').match(/\/(ErdosProblems\/.+?\.lean)(?:#|$)/);
    if (!match) return '';
    return 'lean-module:' + match[1].replace(/\.lean$/, '').replace(/\//g, '.');
  }
  function hashModuleId() {
    if (!location.hash) return '';
    try { return decodeURIComponent(location.hash.slice(1)); } catch (e) { return location.hash.slice(1); }
  }
  function selectFromPage(id, fromPaper) {
    if (!id) return false;
    var maps = document.querySelectorAll('[data-source-map]');
    var found = false;
    for (var i = 0; i < maps.length; i++) {
      if (typeof maps[i].__selectModule === 'function' && maps[i].__selectModule(id, { force: fromPaper, fromPaper: fromPaper })) {
        found = true;
      }
    }
    return found;
  }
  document.addEventListener('click', function (event) {
    var trigger = event.target.closest('[data-select-module], a[href*="/ErdosProblems/"]');
    if (!trigger) return;
    var id = trigger.getAttribute('data-select-module') || '';
    if (!id) id = moduleIdFromGithub(trigger.getAttribute('href') || '');
    if (!id) return;
    var map = document.querySelector('[data-source-map]');
    if (!map || typeof map.__hasModule !== 'function' || !map.__hasModule(id)) return;
    var fromPaper = !map.contains(trigger);
    if (fromPaper && trigger.tagName === 'A') {
      var href = trigger.getAttribute('href') || '';
      if (href.indexOf('github.com') !== -1 && !trigger.getAttribute('data-select-module')) {
        event.preventDefault();
        if (history.replaceState) history.replaceState(null, '', '#' + id);
        else location.hash = id;
      }
    }
    selectFromPage(id, fromPaper);
  });
  // Deep links into a collapsed research section reveal their destination.
  // Module hashes also select the matching Lean map row.
  function revealHash() {
    if (!location.hash) return;
    var raw = hashModuleId();
    var target;
    try { target = document.getElementById(raw); } catch (e) { target = null; }
    if (target) {
      for (var parent = target; parent; parent = parent.parentElement) {
        if (parent.tagName === 'DETAILS') parent.open = true;
      }
      target.scrollIntoView();
    }
    selectFromPage(raw, true);
  }
  window.addEventListener('hashchange', revealHash);
  revealHash();
})();
