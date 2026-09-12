/* Plectis — maths subsite runtime.
   Theme, readable equation overflow, and local Lean navigation. The shared docs runtime owns
   the mobile drawer, copy-text, and terms; this file only
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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      mountToggle();
    });
  } else {
    mountToggle();
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
    var empty = document.createElement('p');
    empty.className = 'source-empty';
    empty.hidden = true;
    empty.appendChild(document.createTextNode('No files match these filters. '));
    var reset = document.createElement('button');
    reset.type = 'button';
    reset.textContent = 'Clear filters';
    empty.appendChild(reset);
    map.appendChild(empty);
    function clearFilters() {
      if (search) search.value = '';
      if (direct) direct.checked = false;
      filter();
    }
    reset.addEventListener('click', function () { clearFilters(); if (search) search.focus(); });

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
      if (row.hidden) clearFilters();
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
      if (opts.focus && nameButton(row)) nameButton(row).focus({preventScroll: true});
      return true;
    }
    map.__selectModule = select;
    map.__hasModule = function (id) { return nodes.has(id); };
    map.__clearSelection = clearSelection;
    function filter() {
      var q = (search && search.value || '').trim().toLowerCase();
      var onlyDirect = !!(direct && direct.checked);
      var shown = 0;
      entries.forEach(function (row) {
        var node = nodes.get(row.dataset.module) || {};
        var haystack = [node.label, node.path, row.dataset.module].join(' ').toLowerCase();
        var hide = (onlyDirect && row.dataset.direct !== 'true') ||
          haystack.indexOf(q) === -1;
        row.hidden = hide;
        if (!hide) shown++;
      });
      var status = map.querySelector('[data-map-count]');
      if (status) status.textContent = shown === entries.length ? '' : (shown + ' of ' + entries.length);
      empty.hidden = shown > 0;
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

  function hashId() {
    try { return decodeURIComponent(location.hash.slice(1)); }
    catch (e) { return location.hash.slice(1); }
  }
  function selectFromPage(id, options) {
    var maps = document.querySelectorAll('[data-source-map]');
    for (var i = 0; i < maps.length; i++) {
      if (typeof maps[i].__selectModule === 'function' && maps[i].__selectModule(id, options)) return true;
    }
    return false;
  }
  document.addEventListener('click', function (event) {
    var trigger = event.target.closest('[data-select-module]');
    if (!trigger || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    var id = trigger.getAttribute('data-select-module');
    var fromPaper = !trigger.closest('[data-source-map]');
    if (!selectFromPage(id, {force: true, fromPaper: fromPaper, focus: true})) return;
    event.preventDefault();
    if (hashId() !== id) history.pushState(null, '', '#' + encodeURIComponent(id));
  });
  // Deep links into a collapsed section reveal their destination; module
  // selections survive reload and browser Back/Forward as ordinary URLs.
  function revealHash() {
    var id = hashId();
    if (selectFromPage(id, {force: true, fromPaper: true})) return;
    document.querySelectorAll('[data-source-map]').forEach(function (map) {
      if (map.__clearSelection) map.__clearSelection();
    });
    var target = document.getElementById(id);
    if (!target) return;
    for (var parent = target; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
    target.scrollIntoView();
  }
  window.addEventListener('hashchange', revealHash);
  window.addEventListener('popstate', revealHash);
  revealHash();
})();

/* Keep long proof coordinates available without letting them dominate prose.
   The exact original code node stays in the button, so text/JSON export still
   includes its full name. Existing source links retain their normal action. */
(function () {
  'use strict';
  if (!HTMLElement.prototype.showPopover) return;
  var panel = document.createElement('div');
  panel.id = 'lean-identifier-detail';
  panel.className = 'lean-identifier-detail';
  panel.setAttribute('popover', 'auto');
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'Full Lean identifier');
  var title = document.createElement('p');
  title.className = 'lean-identifier-detail__title';
  var value = document.createElement('code');
  var actions = document.createElement('div');
  actions.className = 'lean-identifier-detail__actions';
  var copy = document.createElement('button');
  copy.type = 'button';
  copy.className = 'btn btn--ghost';
  copy.textContent = 'Copy name';
  var status = document.createElement('span');
  status.className = 'lean-identifier-detail__status';
  status.setAttribute('aria-live', 'polite');
  var close = document.createElement('button');
  close.type = 'button';
  close.className = 'btn btn--ghost';
  close.textContent = 'Close';
  actions.append(copy, status, close);
  panel.append(title, value, actions);
  document.body.appendChild(panel);
  var current = null;
  function position() {
    if (!current || !panel.matches(':popover-open')) return;
    var box = current.getBoundingClientRect();
    var left = Math.max(16, Math.min(box.left, innerWidth - panel.offsetWidth - 16));
    var top = box.bottom + 8;
    if (top + panel.offsetHeight > innerHeight - 16) top = Math.max(16, box.top - panel.offsetHeight - 8);
    panel.style.left = left + 'px';
    panel.style.top = top + 'px';
  }
  close.addEventListener('click', function () { panel.hidePopover(); if (current) current.focus({preventScroll: true}); });
  copy.addEventListener('click', async function () {
    try {
      await navigator.clipboard.writeText(value.textContent);
      status.textContent = 'Copied';
    } catch (e) { status.textContent = 'Select the name to copy'; }
  });
  panel.addEventListener('toggle', function (event) {
    if (current) current.setAttribute('aria-expanded', event.newState === 'open' ? 'true' : 'false');
  });
  window.addEventListener('resize', position);
  document.querySelectorAll('.paper-stage p code, .paper-stage li code').forEach(function (code) {
    var name = code.textContent.trim();
    if (code.closest('a, pre, button') || name.length < 36) return;
    var file = /^[\w.]+\.lean$/.test(name);
    if (!file && !/^[A-Za-z]\w*_[\w]*_[\w]*$/.test(name)) return;
    var button = document.createElement('button');
    button.type = 'button';
    button.className = 'lean-identifier';
    button.setAttribute('aria-label', 'Inspect ' + (file ? 'Lean file: ' : 'Lean declaration: ') + name);
    button.setAttribute('aria-haspopup', 'dialog');
    button.setAttribute('aria-controls', panel.id);
    button.setAttribute('aria-expanded', 'false');
    code.parentNode.insertBefore(button, code);
    button.appendChild(code);
    button.addEventListener('click', function () {
      if (current) current.setAttribute('aria-expanded', 'false');
      if (panel.matches(':popover-open')) panel.hidePopover();
      current = button;
      title.textContent = file ? 'Lean file' : 'Lean declaration';
      value.textContent = name;
      status.textContent = '';
      panel.showPopover();
      position();
    });
  });
})();

/* Make only overflowing equations keyboard-scrollable. These enhancements do not typeset or hide content. */
(function () {
  'use strict';
  var equations = Array.prototype.slice.call(document.querySelectorAll('.paper-stage .math.display'));
  function measure() {
    equations.forEach(function (equation) {
      var overflow = equation.scrollWidth > equation.clientWidth + 2;
      if (overflow) {
        equation.setAttribute('tabindex', '0');
        equation.setAttribute('role', 'group');
        equation.setAttribute('aria-label', 'Equation; scroll horizontally to read the full expression');
      } else {
        equation.removeAttribute('tabindex');
        equation.removeAttribute('role');
        equation.removeAttribute('aria-label');
      }
    });
  }
  var scheduled = false;
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(function () { scheduled = false; measure(); });
  }
  window.addEventListener('resize', schedule);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(schedule);
  schedule();
})();
