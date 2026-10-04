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

  /* Same control the docs runtime injects, appended to the topbar links,
     with the same sun and moon, so the switch looks alike on every page. */
  var SUN = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path></svg>';
  var MOON = '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"></path></svg>';
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
      '<span class="theme-toggle__ico theme-toggle__ico--sun">' + SUN + '</span>' +
      '<span class="theme-toggle__ico theme-toggle__ico--moon">' + MOON + '</span>' +
      '<span class="theme-toggle__knob"></span>' +
      '</span>';
    btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(KEY, next); } catch (e) {}
      flip(next);
    });
    nav.appendChild(btn);
    toggle = btn;
    apply(resolved());
  }

  /* The flip. For the moment the scheme changes no colour transition runs
     (.vt-theme in style.css), so nothing smears through the page. Where
     view transitions exist, the new scheme then fades in over the old in
     200ms, one cross-dissolve of the whole page: a same-document transition,
     never a link transition, so navigation never waits on it. Reduced
     motion, a hidden tab or an older browser get the same quiet flip,
     instantly. The canvases repaint in their own listeners, and the
     transition's new view is live, so they arrive inside the dissolve. */
  function quiet(next) {
    root.classList.add('vt-theme');
    apply(next);
    void root.offsetWidth;
    var lift = function () { root.classList.remove('vt-theme'); };
    if (window.requestAnimationFrame) {
      window.requestAnimationFrame(function () { window.requestAnimationFrame(lift); });
    } else {
      window.setTimeout(lift, 50);
    }
  }
  function flip(next) {
    var reduce = false;
    try { reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}
    if (reduce || typeof document.startViewTransition !== 'function' ||
        document.visibilityState === 'hidden') {
      quiet(next);
      return;
    }
    var transition;
    root.classList.add('vt-theme');
    try {
      transition = document.startViewTransition(function () { apply(next); });
    } catch (e) {
      root.classList.remove('vt-theme');
      quiet(next);
      return;
    }
    var done = function () { root.classList.remove('vt-theme'); };
    transition.finished.then(done, done);
    transition.ready.then(function () {
      try {
        root.animate(
          { opacity: [0, 1] },
          { duration: 200, easing: 'cubic-bezier(0.2, 0.75, 0.25, 1)', pseudoElement: '::view-transition-new(root)' }
        );
      } catch (e) {}
    }, function () {});
  }

  /* Follow OS changes only while the reader has not chosen explicitly. */
  if (mq && mq.addEventListener) {
    mq.addEventListener('change', function () {
      if (stored() !== 'dark' && stored() !== 'light') quiet(resolved());
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

/* A link to a folded section opens it. The header's "Papers" link lands on
   the overview's paper list, which is folded by default; the shared runtime
   opens a targeted fold when it loads, and this covers the same-page click
   and a reader who arrives before that runtime is ready. */
(function () {
  'use strict';
  function openTarget() {
    var id = '';
    try { id = decodeURIComponent((window.location.hash || '').slice(1)); } catch (e) { return; }
    if (!id) return;
    var target = document.getElementById(id);
    if (target && target.tagName === 'DETAILS' && !target.open) target.open = true;
  }
  window.addEventListener('hashchange', openTarget);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', openTarget);
  } else {
    openTarget();
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
  function revealHash(initial) {
    var id = hashId();
    if (selectFromPage(id, {force: true, fromPaper: true})) return;
    document.querySelectorAll('[data-source-map]').forEach(function (map) {
      if (map.__clearSelection) map.__clearSelection();
    });
    var target = document.getElementById(id);
    if (!target) return;
    var opened = false;
    for (var parent = target; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS' && !parent.open) { parent.open = true; opened = true; }
    }
    // The browser already resolves an initial manuscript fragment. Repeating
    // that scroll forces layout across a long paper before its reader mounts.
    // A newly opened disclosure and a source-map selection still need their
    // lightweight fallback; later fragment changes keep their normal reveal.
    if (initial !== true || opened || document.querySelector('[data-source-map]')) target.scrollIntoView();
  }
  window.addEventListener('hashchange', revealHash);
  window.addEventListener('popstate', revealHash);
  revealHash(true);
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
  // Some manuscripts typeset a complete Lean name as math. Keep its exact
  // TeX attribute for export, but present that literal with the same name
  // control as inline code. Mixed expressions remain typeset mathematics.
  document.querySelectorAll('.paper-stage .math.inline[data-tex]').forEach(function (math) {
    if (math.closest('a')) return;
    var literal = math.getAttribute('data-tex').match(/^\\\(\s*\\(?:mathtt|mathrm)\{([^{}]+)\}\s*\\\)$/);
    if (!literal) return;
    var name = literal[1].replace(/\\_/g, '_');
    if (name.length < 36 || !/^[A-Za-z][\w.'/]*$/.test(name)) return;
    var code = document.createElement('code');
    code.textContent = name;
    math.replaceChildren(code);
  });
  document.querySelectorAll('.paper-stage p code, .paper-stage li code').forEach(function (code) {
    var name = code.textContent.trim();
    if (code.closest('a, pre, button') || name.length < 36) return;
    var file = /^(?:[\w.-]+\/)*[\w.]+\.lean$/.test(name);
    if (!file && !/^[A-Za-z][\w.']*$/.test(name)) return;
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
  var overflowTabStops = new WeakMap();
  var equations = Array.prototype.slice.call(document.querySelectorAll('.paper-stage .math.display'));
  var inline = Array.prototype.slice.call(document.querySelectorAll('.paper-stage .math.inline[data-math-rendered]:not([data-math-compact])'))
    .filter(function (math) { return !math.closest('table, pre'); })
    .map(function (math) {
      var flow = document.createElement('span');
      flow.className = 'math-inline-flow';
      math.parentNode.insertBefore(flow, math);
      flow.appendChild(math);
      // Keep prose punctuation beside an equation when it needs its own line.
      // It stays outside data-tex, so source-text export retains it too.
      var next = flow.nextSibling;
      if (next && next.nodeType === 3) {
        var punctuation = next.textContent.match(/^\s*[.,;:!?]+/);
        if (punctuation) {
          flow.appendChild(document.createTextNode(punctuation[0]));
          next.textContent = next.textContent.slice(punctuation[0].length);
        }
      }
      return {math: math, flow: flow};
    });
  // Blocks below a heading lay out lazily (content-visibility in maths.css).
  // Measuring a skipped block would force it to render, so only expressions
  // already on screen are measured; the rest are measured as they arrive.
  function onScreen(node) {
    return typeof node.checkVisibility !== 'function' ||
      node.checkVisibility({contentVisibilityAuto: true});
  }
  function measure() {
    measureItems(inline.filter(function (item) { return onScreen(item.math); }),
      equations.filter(onScreen));
  }
  // Visit section children directly: matching the child exclusion against
  // every typeset equation descendant is costly in a long manuscript.
  var lazyBlocks = new Set();
  document.querySelectorAll('.paper-stage section').forEach(function (section) {
    Array.prototype.forEach.call(section.children, function (block) {
      if (!block.matches('h1, h2, h3, h4, h5, h6, section')) lazyBlocks.add(block);
    });
  });
  var blockItems = new Map();
  var pendingInline = new Set(), pendingDisplay = new Set();
  var scheduled = false, fullMeasure = false;
  function indexItem(node, kind, item) {
    var block = node;
    while (block && !lazyBlocks.has(block)) block = block.parentElement;
    if (!block) return;
    var items = blockItems.get(block);
    if (!items) { items = {inline: [], display: []}; blockItems.set(block, items); }
    items[kind].push(item);
  }
  inline.forEach(function (item) { indexItem(item.math, 'inline', item); });
  equations.forEach(function (equation) { indexItem(equation, 'display', equation); });
  // A visibility event only queues its own expressions. Several newly visible
  // blocks share one frame, rather than rescanning the entire manuscript and
  // forcing layout separately for each block.
  blockItems.forEach(function (items, block) {
    block.addEventListener('contentvisibilityautostatechange', function (event) {
      if (event.skipped) return;
      items.inline.forEach(function (item) { pendingInline.add(item); });
      items.display.forEach(function (equation) { pendingDisplay.add(equation); });
      schedule(false);
    });
  });
  function measureItems(inlineItems, displayItems) {
    // Read the natural inline layout once, then promote only expressions
    // whose indivisible content is wider than their paragraph. Tables already
    // own their scrolling. This also restores inline flow on wider screens.
    inlineItems.forEach(function (item) {
      if (item.flow.hasAttribute('data-math-overflow')) item.flow.removeAttribute('data-math-overflow');
    });
    var wide = inlineItems.filter(function (item) {
      var math = item.math;
      var paragraph = math.closest('p, li, td, th, .paper-stage');
      return paragraph && math.getBoundingClientRect().width > paragraph.clientWidth + 2;
    });
    wide.forEach(function (item) { item.flow.setAttribute('data-math-overflow', 'true'); });
    // Read all scroll geometry before changing tabindex or accessibility
    // attributes: those writes must not invalidate layout between reads.
    var scrollItems = displayItems.concat(inlineItems.map(function (item) { return item.flow; }));
    var overflows = scrollItems.map(function (equation) {
      return equation.scrollWidth > equation.clientWidth + 2;
    });
    scrollItems.forEach(function (equation, index) {
      var overflow = overflows[index];
      if (overflow) {
        if (!overflowTabStops.has(equation)) overflowTabStops.set(equation, equation.getAttribute('tabindex'));
        equation.setAttribute('tabindex', '0');
        equation.setAttribute('data-math-scroll', 'true');
        if (equation.classList.contains('math')) {
          // Keep the expression's assistive MathML as its accessible content.
          equation.removeAttribute('role');
          equation.removeAttribute('aria-label');
          equation.setAttribute('aria-description', 'Scroll horizontally to read the full expression');
        } else {
          equation.setAttribute('role', 'group');
          equation.setAttribute('aria-label', 'Equation; scroll horizontally to read the full expression');
        }
      } else {
        if (overflowTabStops.has(equation)) {
          var previous = equation.getAttribute('data-term-help') === 'notation'
            ? equation.getAttribute('data-term-tabindex') : null;
          if (previous === null) previous = overflowTabStops.get(equation);
          if (previous === null) equation.removeAttribute('tabindex');
          else equation.setAttribute('tabindex', previous);
          overflowTabStops.delete(equation);
        }
        equation.removeAttribute('data-math-scroll');
        equation.removeAttribute('role');
        equation.removeAttribute('aria-label');
        equation.removeAttribute('aria-description');
      }
    });
  }
  function schedule(measureAll) {
    if (measureAll !== false) fullMeasure = true;
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(function () {
      scheduled = false;
      if (fullMeasure) {
        fullMeasure = false;
        measure();
      } else {
        measureItems(Array.from(pendingInline).filter(function (item) { return onScreen(item.math); }),
          Array.from(pendingDisplay).filter(onScreen));
      }
      pendingInline.clear();
      pendingDisplay.clear();
    });
  }
  window.addEventListener('resize', schedule);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(schedule);
  schedule();
})();

/* Explain fixed TeX operators through the shared glossary. Variable letters
   and custom macros retain the meaning assigned by each manuscript. */
(function () {
  'use strict';
  var terms = Object.freeze({
    sum: 'sum', prod: 'product', forall: 'universal_quantifier',
    exists: 'existential_quantifier', in: 'set_membership',
    subseteq: 'subset', cup: 'set_union', cap: 'set_intersection'
  });
  var textArguments = Object.freeze({
    text: 1, textrm: 1, texttt: 1, textsf: 1, textbf: 1, textit: 1,
    mathtt: 1, mathrm: 1, operatorname: 1, url: 1, href: 2,
    label: 1, ref: 1, eqref: 1, cite: 1
  });
  function scan(tex) {
    var ids = [], seen = Object.create(null), at = 0;
    function argument() {
      while (/\s/.test(tex.charAt(at)) && at < tex.length) at++;
      if (tex.charAt(at) !== '{') return;
      var depth = 1;
      at++;
      while (at < tex.length && depth) {
        var ch = tex.charAt(at++);
        if (ch === '\\') at++;
        else if (ch === '{') depth++;
        else if (ch === '}') depth--;
      }
    }
    while (at < tex.length) {
      var ch = tex.charAt(at++);
      if (ch === '%') {
        while (at < tex.length && tex.charAt(at) !== '\n') at++;
        continue;
      }
      if (ch !== '\\') continue;
      var begin = at;
      while (/[A-Za-z]/.test(tex.charAt(at)) && at < tex.length) at++;
      if (begin === at) { at++; continue; }
      var command = tex.slice(begin, at);
      if (/^(?:def|gdef|edef|newcommand|renewcommand|providecommand|DeclareMathOperator)$/.test(command)) return [];
      if (command === 'begin' && /^\s*\{(?:verbatim\*?|lstlisting|minted)\}/.test(tex.slice(at))) return [];
      if (command === 'verb') {
        if (tex.charAt(at) === '*') at++;
        var delimiter = tex.charAt(at++);
        while (at < tex.length && tex.charAt(at) !== delimiter) at++;
        at++;
        continue;
      }
      if (Object.prototype.hasOwnProperty.call(textArguments, command)) {
        if (tex.charAt(at) === '*') at++;
        for (var n = 0; n < textArguments[command]; n++) argument();
        continue;
      }
      var id = Object.prototype.hasOwnProperty.call(terms, command) ? terms[command] : null;
      if (id && !seen[id]) { seen[id] = true; ids.push(id); }
    }
    return ids;
  }
  var parsed = new WeakMap(), registered = new WeakSet();
  var introduced = Object.create(null);
  var runtime = document.currentScript;
  var glossary = runtime && runtime.src ? new URL('../../docs/glossary.html', runtime.src).href : null;
  function hrefForId(id) {
    return glossary && glossary + '#glossary-' + id.replace(/_/g, '-');
  }
  function registerAll() {
    var api = window.PlectisTermHelp;
    if (!api || typeof api.registerNotation !== 'function') return;
    document.querySelectorAll('.math[data-tex]').forEach(function (math) {
      if (registered.has(math)) return;
      if (!parsed.has(math)) parsed.set(math, Object.freeze(scan(math.getAttribute('data-tex') || '')));
      var ids = parsed.get(math);
      // Most manuscript expressions contain no supported fixed operator. Read
      // their small TeX attribute before querying the generated equation tree.
      if (!ids.length || math.closest('a, button, pre, code') || math.querySelector('button, code')) return;
      // Every operator gets a keyboard introduction; repeated definitions do
      // not turn every equation into another stop through the manuscript.
      var keyboardFocus = !math.closest('[hidden], details:not([open])') &&
        ids.some(function (id) { return !introduced[id]; });
      if (api.registerNotation(math, ids, {hrefForId: hrefForId, keyboardFocus: keyboardFocus})) {
        math.setAttribute('data-term-tabindex', keyboardFocus ? '0' : '-1');
        registered.add(math);
        if (keyboardFocus) ids.forEach(function (id) { introduced[id] = true; });
      }
    });
  }
  registerAll();
  document.addEventListener('plectis:term-help-ready', registerAll, {once: true});
})();

/* A fresh manuscript fragment can be readable before optional docs controls.
   Limit geometric settling, but retain reader interruption until docs takes
   over: a slow off-screen font must not make the later initial scroll win. */
(function earlyPaperArrival() {
  'use strict';
  var started = false;
  function start() {
    if (started) return;
    started = true;
    var hash = window.location.hash;
    if (!hash || hash.length < 2) return;
    var id;
    try { id = decodeURIComponent(hash.slice(1)); } catch (e) { return; }
    var stage = document.querySelector('.paper-stage');
    var header = document.querySelector('.docs-topbar');
    var target = document.getElementById(id);
    if (!stage || !header || !target || !stage.contains(target) ||
        !header.getBoundingClientRect || !target.getBoundingClientRect) return;
    var root = document.documentElement;
    var url = window.location.pathname + window.location.search + hash;
    try {
      var navigation = window.performance && window.performance.getEntriesByType
        ? window.performance.getEntriesByType('navigation')[0] : null;
      // A history arrival owns native/saved scroll, even without a snapshot.
      if (navigation && (navigation.type === 'back_forward' || navigation.type === 'reload')) return;
      if (!navigation && window.performance && window.performance.navigation &&
          (window.performance.navigation.type === 2 || window.performance.navigation.type === 1)) return;
      var raw = window.sessionStorage && window.sessionStorage.getItem('mc:viewstate:restore');
      var pending = raw ? JSON.parse(raw) : null;
      if (pending && pending.path === window.location.pathname) return;
    } catch (e) {
      // Inaccessible storage is the ordinary no-snapshot path. A corrupt
      // snapshot likewise remains for its existing owner to interpret.
    }
    var MARK = 'data-plectis-paper-arrival-interrupted';
    var handoff = root.getAttribute('data-plectis-docs-runtime');
    if (handoff === 'ready' || handoff === 'failed') return;
    var settling = true, listening = true, queued = false, remaining = 0;
    var layoutObserver = null, headerObserver = null, handoffObserver = null;
    var headerHeight = 0;
    var events = ['wheel', 'touchstart', 'pointerdown', 'keydown'];
    var now = function () { return window.performance && window.performance.now ? window.performance.now() : Date.now(); };
    var deadline = now() + 2400;
    function sameArrival() {
      return window.location.pathname + window.location.search + window.location.hash === url;
    }
    function endSettling() {
      settling = false;
      if (layoutObserver) layoutObserver.disconnect();
      window.removeEventListener('load', afterLoad);
      window.clearTimeout(timer);
    }
    function finish() {
      if (!listening) return;
      listening = false;
      endSettling();
      events.forEach(function (name) { window.removeEventListener(name, interrupt, true); });
      window.removeEventListener('hashchange', finish);
      window.removeEventListener('pagehide', finish);
      if (handoffObserver) handoffObserver.disconnect();
      if (headerObserver) headerObserver.disconnect();
      root.removeAttribute(MARK);
    }
    function interrupt(event) {
      if (!event.isTrusted || !listening || !sameArrival()) return;
      var state = root.getAttribute('data-plectis-docs-runtime');
      if (state === 'ready' || state === 'failed') { finish(); return; }
      root.setAttribute(MARK, url);
      endSettling();
    }
    function publishHeader(height) {
      if (height > 0 && height !== headerHeight) {
        headerHeight = height;
        root.style.setProperty('--topbar-h', height + 'px');
        document.body.style.setProperty('--topbar-h', height + 'px');
      }
    }
    function tick() {
      queued = false;
      if (!settling || !sameArrival()) return;
      if (now() >= deadline) { endSettling(); return; }
      var height = Math.ceil(header.getBoundingClientRect().height);
      var top = target.getBoundingClientRect().top;
      if (height > 0) {
        publishHeader(height);
        if (Math.abs(top - height - 8) > 1) {
          var previous = root.style.scrollBehavior;
          root.style.scrollBehavior = 'auto';
          try { window.scrollTo(0, (window.pageYOffset || 0) + top - height - 8); }
          finally { root.style.scrollBehavior = previous; }
        }
      }
      remaining -= 1;
      if (remaining > 0) queue(remaining);
    }
    function queue(frames) {
      if (!settling || !sameArrival()) return;
      remaining = Math.max(remaining, frames || 2);
      if (!queued) {
        queued = true;
        if (window.requestAnimationFrame) window.requestAnimationFrame(tick);
        else tick();
      }
    }
    function afterLoad() { queue(3); }
    events.forEach(function (name) { window.addEventListener(name, interrupt, { passive: true, capture: true }); });
    window.addEventListener('hashchange', finish);
    window.addEventListener('pagehide', finish);
    if (window.ResizeObserver) {
      layoutObserver = new ResizeObserver(function () { queue(2); });
      layoutObserver.observe(target);
      // Header metrics remain accurate after the scroll-settling deadline or
      // a reader gesture. This observer measures one node and never scrolls.
      headerObserver = new ResizeObserver(function () {
        publishHeader(Math.ceil(header.getBoundingClientRect().height));
        queue(2);
      });
      headerObserver.observe(header);
    }
    if (window.MutationObserver) {
      handoffObserver = new MutationObserver(function () {
        var state = root.getAttribute('data-plectis-docs-runtime');
        if (state === 'ready' || state === 'failed') finish();
      });
      handoffObserver.observe(root, { attributes: true, attributeFilter: ['data-plectis-docs-runtime'] });
    }
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { queue(3); });
    window.addEventListener('load', afterLoad, { once: true });
    var timer = window.setTimeout(endSettling, 2400);
    queue(3);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
