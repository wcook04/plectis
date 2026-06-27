(function () {
  'use strict';

  document.documentElement.classList.add('js');

  // One site-relative asset resolver for the runtime. assets/ live at the site
  // root, so a page under docs/ reaches them with ../assets/ and the root
  // landing with assets/. Prefer deriving from this script's own URL (robust at
  // any depth) with a pathname fallback, so the graph inspector and object
  // coverage panel resolve assets/ correctly whether they run under docs/ or at
  // the site root -- a hard-coded ../assets/ 404s when docs.js runs on the
  // landing map.
  function mcAssetUrl(name) {
    try {
      var scripts = Array.prototype.slice.call(document.querySelectorAll('script[src]'));
      var docsScript = scripts.filter(function (s) {
        return /(?:^|\/)docs\.js(?:[?#].*)?$/.test(s.getAttribute('src') || s.src || '');
      }).pop();
      var src = docsScript && (docsScript.src || docsScript.getAttribute('src'));
      if (src) return src.replace(/docs\.js(?:[?#].*)?$/, name);
    } catch (e) {}
    return (window.location && window.location.pathname || '').indexOf('/docs/') !== -1
      ? '../assets/' + name
      : 'assets/' + name;
  }

  var mcSearchIndexState = 'idle';
  var mcSearchIndexCallbacks = [];
  function mcSearchIndexRecords() {
    var data = window.__MICROCOSM_INDEX__ || {};
    var records = data.records || [];
    return records && records.length ? records : [];
  }

  function completeSearchIndex(records) {
    mcSearchIndexState = records && records.length ? 'ready' : 'failed';
    var queued = mcSearchIndexCallbacks.slice();
    mcSearchIndexCallbacks = [];
    queued.forEach(function (cb) { cb(records || []); });
  }

  function existingSearchIndexScript() {
    var tagged = document.querySelector('script[data-search-index]');
    if (tagged) return tagged;
    var scripts = Array.prototype.slice.call(document.querySelectorAll('script[src]'));
    return scripts.filter(function (s) {
      return /(?:^|\/)search-index\.js(?:[?#].*)?$/.test(s.getAttribute('src') || s.src || '');
    }).pop() || null;
  }

  function withSearchIndex(cb) {
    var records = mcSearchIndexRecords();
    if (records.length) {
      mcSearchIndexState = 'ready';
      cb(records);
      return;
    }
    if (mcSearchIndexState === 'failed') {
      cb([]);
      return;
    }
    mcSearchIndexCallbacks.push(cb);
    if (mcSearchIndexState === 'loading') return;
    mcSearchIndexState = 'loading';

    var existing = existingSearchIndexScript();
    if (existing) {
      existing.addEventListener('load', function () { completeSearchIndex(mcSearchIndexRecords()); });
      existing.addEventListener('error', function () { completeSearchIndex([]); });
      return;
    }

    var s = document.createElement('script');
    s.src = mcAssetUrl('search-index.js');
    s.async = true;
    s.setAttribute('data-search-index', '');
    s.addEventListener('load', function () { completeSearchIndex(mcSearchIndexRecords()); });
    s.addEventListener('error', function () {
      if (window.console && console.warn) console.warn('Microcosm: search-index.js failed to load; site search unavailable.');
      completeSearchIndex([]);
    });
    document.head.appendChild(s);
  }

  function cleanText(text) {
    return String(text || '').replace(/\s+/g, ' ').trim();
  }

  function safeNavigationUrl(raw) {
    var value = String(raw || '').trim();
    if (!value || /^(javascript|data|vbscript):/i.test(value)) return '';
    try {
      var target = new URL(value, window.location.href);
      if (target.origin !== window.location.origin) return '';
      return target.href;
    } catch (e) {
      return '';
    }
  }

  function safeExternalUrl(raw) {
    var value = String(raw || '').trim();
    if (!value) return '';
    try {
      var target = new URL(value, window.location.href);
      return target.protocol === 'https:' ? target.href : '';
    } catch (e) {
      return '';
    }
  }

  function cloneText(node, options) {
    if (!node) return '';
    var clone = node.cloneNode(true);
    var selectors = [
      '.copy-btn',
      '.page-export-btn',
      '.page-export-status',
      '.docs-pagetools',
      '[data-pagetools]',
      '[data-page-export]',
      '[data-site-export]',
      '[data-site-download]',
      '[data-comp-filter]',
      '[data-comp-empty]',
      '[hidden]'
    ];
    if (options && options.dropLabels) selectors.push('.comp-card__klabel');
    selectors.forEach(function (selector) {
      Array.prototype.forEach.call(clone.querySelectorAll(selector), function (el) {
        el.parentNode.removeChild(el);
      });
    });
    return cleanText(clone.textContent);
  }

  function copyTextSync(text) {
    try {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.className = 'copy-proxy';
      document.body.appendChild(ta);
      ta.select();
      try { ta.setSelectionRange(0, text.length); } catch (e) {}
      var ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch (err) {
      return false;
    }
  }

  var srLive = null;
  function announce(message) {
    if (!srLive) {
      srLive = document.createElement('div');
      srLive.className = 'sr-only';
      srLive.setAttribute('role', 'status');
      srLive.setAttribute('aria-live', 'polite');
      document.body.appendChild(srLive);
    }
    srLive.textContent = '';
    window.setTimeout(function () { srLive.textContent = message; }, 30);
  }

  function flashCopy(btn, ok, restoreLabel) {
    btn.textContent = ok ? 'Copied' : 'Press Cmd/Ctrl+C';
    announce(ok ? 'Copied to clipboard' : 'Copy failed. Press Command or Control C to copy.');
    window.clearTimeout(btn.__copyTimer);
    btn.__copyTimer = window.setTimeout(function () { btn.textContent = restoreLabel; }, 1400);
  }

  function makeStatusFlash(btn, status, defaultHtml) {
    var timer;
    return function (label, ok) {
      btn.classList.toggle('is-copied', !!ok);
      if (status) status.textContent = label;
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        btn.innerHTML = defaultHtml;
        btn.classList.remove('is-copied');
        if (status) status.textContent = '';
      }, 1800);
    };
  }

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function buildResultPacket(rec) {
    var p = {
      packet_schema: 'microcosm_public_result_packet_v1',
      derived_from: 'search-index',
      label: rec.label,
      kind: rec.kind,
      route: rec.url,
    };
    if (rec.family) p.family = rec.family;
    if (rec.tags && rec.tags.length) p.tags = rec.tags;
    if (rec.command) p.command = rec.command;
    if (rec.graph_node_id) p.graph_node_id = rec.graph_node_id;
    if (rec.evidence_url) p.evidence_url = rec.evidence_url;
    if (rec.source_url) p.source_url = rec.source_url;
    if (rec.text) p.summary = rec.text;
    return p;
  }

  function selectRawText(text) {
    try {
      var previous = document.querySelector('.copy-proxy[data-export-proxy]');
      if (previous && previous.parentNode) previous.parentNode.removeChild(previous);
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.setAttribute('data-export-proxy', '');
      ta.className = 'copy-proxy';
      document.body.appendChild(ta);
      ta.select();
      try { ta.setSelectionRange(0, text.length); } catch (e) {}
    } catch (err) {}
  }

  function selectTextNode(node) {
    try {
      var range = document.createRange();
      range.selectNodeContents(node);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    } catch (e) {}
  }

  function isDocumentScroller(node) {
    return !node || node === window || node === document || node === document.body ||
      node === document.documentElement || node === document.scrollingElement;
  }

  function scrollPaddingTop() {
    try {
      var raw = window.getComputedStyle(document.documentElement).getPropertyValue('scroll-padding-top');
      var value = parseFloat(raw);
      return isNaN(value) ? 0 : value;
    } catch (e) {
      return 0;
    }
  }

  function scrollAnchorFor(target) {
    if (!target) return null;
    if (target.tagName === 'DETAILS' && typeof target.querySelector === 'function') {
      return target.querySelector('summary') || target;
    }
    return target;
  }

  function scrollContainerFor(target) {
    var node = target && (target.parentElement || target.parentNode);
    while (node && node.nodeType === 1 && node !== document.body && node !== document.documentElement) {
      try {
        var style = window.getComputedStyle(node);
        var overflowY = style ? String(style.overflowY || style.overflow || '') : '';
        if (/(auto|scroll|overlay)/.test(overflowY) && node.scrollHeight > node.clientHeight + 1) {
          return node;
        }
      } catch (e) {}
      node = node.parentElement || node.parentNode;
    }
    return document.scrollingElement || document.documentElement || document.body;
  }

  function scrollContainerTop(scroller) {
    if (isDocumentScroller(scroller)) {
      return window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0;
    }
    return scroller.scrollTop || 0;
  }

  function setScrollContainerTop(scroller, top) {
    top = Math.max(0, top || 0);
    if (isDocumentScroller(scroller)) {
      window.scrollTo(0, top);
      return;
    }
    scroller.scrollTop = top;
  }

  function withAutoScroll(scroller, fn) {
    var style = isDocumentScroller(scroller)
      ? (document.documentElement && document.documentElement.style)
      : (scroller && scroller.style);
    if (!style) {
      fn();
      return;
    }
    var previous = style.scrollBehavior;
    style.scrollBehavior = 'auto';
    try { fn(); } finally { style.scrollBehavior = previous; }
  }

  function openAncestorDetails(target) {
    var opened = [];
    var node = target;
    while (node && node.nodeType === 1) {
      if (node.tagName === 'DETAILS') {
        if (!node.open) {
          node.open = true;
          if (node.id) opened.push(node.id);
        }
      }
      node = node.parentNode;
    }
    return opened;
  }

  function alignTarget(target) {
    var anchor = scrollAnchorFor(target);
    if (!anchor || typeof anchor.getBoundingClientRect !== 'function') return;
    var scroller = scrollContainerFor(anchor);
    var y;
    if (isDocumentScroller(scroller)) {
      y = anchor.getBoundingClientRect().top + scrollContainerTop(scroller) - scrollPaddingTop();
    } else if (typeof scroller.getBoundingClientRect === 'function') {
      y = anchor.getBoundingClientRect().top - scroller.getBoundingClientRect().top + scrollContainerTop(scroller) - 10;
    } else {
      y = scrollContainerTop(scroller);
    }
    withAutoScroll(scroller, function () { setScrollContainerTop(scroller, y); });
  }

  function scheduleAlignment(target, frames) {
    if (typeof window.requestAnimationFrame !== 'function') {
      alignTarget(target);
      return;
    }
    frames = frames || 3;
    var tick = function () {
      alignTarget(target);
      frames -= 1;
      if (frames > 0) window.requestAnimationFrame(tick);
    };
    window.requestAnimationFrame(tick);
  }

  function previewReceipt(target, index) {
    var anchor = scrollAnchorFor(target) || target;
    var scroller = scrollContainerFor(anchor);
    var rect = target && target.getBoundingClientRect ? target.getBoundingClientRect() : null;
    return {
      ok: !!target,
      id: target && target.id ? target.id : null,
      index: index || null,
      hash: target && target.id ? '#' + target.id : null,
      scroller: isDocumentScroller(scroller) ? 'document' : (scroller.id ? '#' + scroller.id : cleanText(scroller.className || scroller.tagName || 'element')),
      scrollTop: Math.round(scrollContainerTop(scroller)),
      top: rect ? Math.round(rect.top) : null,
      bottom: rect ? Math.round(rect.bottom) : null
    };
  }

  function previewTargets(selector) {
    try {
      return Array.prototype.slice.call(document.querySelectorAll(selector));
    } catch (e) {
      return [];
    }
  }

  function scrollPreviewTarget(target, index) {
    if (!target) return { ok: false, reason: 'target_not_found' };
    openAncestorDetails(target);
    alignTarget(target);
    scheduleAlignment(target, 3);
    return previewReceipt(target, index);
  }

  window.__microcosmPreview = {
    listDiagrams: function () {
      return previewTargets('[data-reader-stage="diagram"], .pm-diagram').map(function (target, i) {
        return previewReceipt(target, i + 1);
      });
    },
    scrollToDiagram: function (which) {
      var targets = previewTargets('[data-reader-stage="diagram"], .pm-diagram');
      var target = null;
      var index = null;
      if (typeof which === 'string' && which.charAt(0) === '#') {
        target = document.getElementById(which.slice(1));
        index = targets.indexOf(target) + 1 || null;
      } else {
        var n = Number(which || 1);
        index = isFinite(n) && n > 0 ? Math.floor(n) : 1;
        target = targets[index - 1] || null;
      }
      return scrollPreviewTarget(target, index);
    },
    scrollToSelector: function (selector) {
      return scrollPreviewTarget(previewTargets(String(selector || ''))[0] || null, null);
    },
    scrollToHash: function (hash) {
      var id = String(hash || window.location.hash || '').replace(/^#/, '');
      return scrollPreviewTarget(id ? document.getElementById(id) : null, null);
    }
  };

  (function openTargetDetails() {
    function hasPendingExactRestore() {
      try {
        var raw = window.sessionStorage && window.sessionStorage.getItem('mc:viewstate:restore');
        if (!raw) return false;
        var pending = JSON.parse(raw);
        return !!(pending && pending.path === window.location.pathname);
      } catch (e) {
        return false;
      }
    }
    function openTo(hash) {
      if (!hash || hash.charAt(0) !== '#') return;
      var id;
      try { id = decodeURIComponent(hash.slice(1)); } catch (e) { id = hash.slice(1); }
      if (!id) return;
      var target = document.getElementById(id);
      if (!target) return;
      openAncestorDetails(target);
      if (!hasPendingExactRestore()) {
        scheduleAlignment(target);
      }
    }
    window.addEventListener('hashchange', function () { openTo(window.location.hash); });
    if (window.location.hash) { openTo(window.location.hash); }
  })();

  (function viewState() {
    var KEY_STACK = 'mc:viewstate:stack';     // breadcrumb trail of views behind this one
    var KEY_RESTORE = 'mc:viewstate:restore'; // a pending exact restore for this load
    var MAX_DEPTH = 6;
    var ss;
    try { ss = window.sessionStorage; var probe = '__mc_vs'; ss.setItem(probe, '1'); ss.removeItem(probe); }
    catch (e) { return; }

    function read(key) { try { var v = ss.getItem(key); return v ? JSON.parse(v) : null; } catch (e) { return null; } }
    function write(key, val) { try { ss.setItem(key, JSON.stringify(val)); } catch (e) {} }
    function drop(key) { try { ss.removeItem(key); } catch (e) {} }
    function clampStack(stack) {
      stack = stack && stack.length ? stack.slice(Math.max(0, stack.length - MAX_DEPTH)) : [];
      return stack.filter(function (entry) { return entry && entry.path && entry.url; });
    }
    function readStack() {
      var stack = clampStack(read(KEY_STACK));
      write(KEY_STACK, stack);
      return stack;
    }
    drop('mc:viewstate:prev');

    function navType() {
      try {
        var nav = (performance.getEntriesByType && performance.getEntriesByType('navigation')) || [];
        if (nav.length && nav[0].type) return nav[0].type;
      } catch (e) {}
      try {
        var legacy = performance.navigation;
        if (legacy) {
          if (legacy.type === 2) return 'back_forward';
          if (legacy.type === 1) return 'reload';
          if (legacy.type === 0) return 'navigate';
        }
      } catch (e) {}
      return 'unknown';
    }
    function focusAnchor() {
      var el = document.activeElement;
      if (!el || el.nodeType !== 1 || el === document.body || el === document.documentElement) return null;
      if (el.id) { try { if (document.getElementById(el.id) === el) return { by: 'id', v: el.id }; } catch (e) {} }
      if (el.tagName === 'A' && el.getAttribute) {
        var href = el.getAttribute('href');
        if (href) return { by: 'href', v: href };
      }
      return null;
    }
    function findFocus(anchor) {
      if (!anchor) return null;
      try {
        if (anchor.by === 'id') return document.getElementById(anchor.v);
        if (anchor.by === 'href') {
          var links = document.getElementsByTagName('a'), i;
          for (i = 0; i < links.length; i++) { if (links[i].getAttribute('href') === anchor.v) return links[i]; }
        }
      } catch (e) {}
      return null;
    }
    function pageTitle() {
      // "How it fits together · Microcosm" -> "How it fits together"; a landing
      // title with no middot but a colon ("Microcosm: a public ...") trims at the
      // colon so the pill label stays short.
      var t = cleanText((document.title || '').split('·')[0]);
      if (t.indexOf(':') !== -1) t = cleanText(t.split(':')[0]);
      return t || 'previous view';
    }
    function openDetailIds() {
      var ids = [], list = document.querySelectorAll('details[open][id]'), i;
      for (i = 0; i < list.length; i++) ids.push(list[i].id);
      return ids;
    }
    function snapshot() {
      return {
        url: location.pathname + location.search + location.hash,
        path: location.pathname,
        title: pageTitle(),
        y: window.pageYOffset || document.documentElement.scrollTop || 0,
        open: openDetailIds(),
        focus: focusAnchor()
      };
    }

    // Record the view we leave. pagehide fires for every navigation away -- an
    // anchor, the map's scripted double-click jump, a sidebar link, Back/Forward.
    // On a forward hop we push the view being left so the destination can offer an
    // exact return; the return hop itself sets `suppress`, so going back never
    // re-pushes the page we are leaving (which would become a spurious forward).
    var suppress = false;
    window.addEventListener('pagehide', function () {
      if (suppress) { suppress = false; return; }
      var stack = readStack(), leaving = snapshot(), top = stack[stack.length - 1];
      if (top && top.path === leaving.path) {
        stack[stack.length - 1] = leaving; // same path again -> refresh in place, don't stack dupes
      } else {
        stack.push(leaving);
        if (stack.length > MAX_DEPTH) stack = stack.slice(stack.length - MAX_DEPTH);
      }
      write(KEY_STACK, stack);
    });

    // Reconcile the trail with where we landed, using HOW we got here:
    //   - back_forward / an explicit history traversal (browser Back/Forward, or a
    //     back-forward-cache restore): the visitor moved backward, so the landed
    //     page sits behind the trail's head -- truncate everything from its first
    //     occurrence forward (this also drops the page pagehide just pushed).
    //   - navigate / reload / unknown (a forward click, INCLUDING a click to a page
    //     seen earlier): keep the trail; only strip a self-push of THIS page from
    //     the top (how reload and a re-click of the current page record themselves).
    //     Never strip an earlier occurrence, so a forward click to a previously
    //     visited page stays a reversible forward hop -- the core "whenever you
    //     click anything" promise.
    function reconcile(traversal) {
      var stack = readStack(), here = location.pathname, i;
      if (traversal || navType() === 'back_forward') {
        for (i = 0; i < stack.length; i++) {
          if (stack[i].path === here) { write(KEY_STACK, stack.slice(0, i)); return; }
        }
        return;
      }
      var changed = false;
      while (stack.length && stack[stack.length - 1].path === here) { stack.pop(); changed = true; }
      if (changed) write(KEY_STACK, stack);
    }

    // Apply a pending exact restore (the visitor clicked the affordance): reopen
    // the cards they had open, return focus to where they were, then scroll to
    // their old position -- twice, since opening <details> and focusing can reflow
    // the page under the first scroll correction (focus runs before the scrolls so
    // a no-preventScroll fallback can't leave them off-position).
    function applyPendingRestore() {
      var pending = read(KEY_RESTORE);
      if (!pending || pending.path !== location.pathname) return;
      drop(KEY_RESTORE);
      var run = function () {
        (pending.open || []).forEach(function (id) {
          var el = document.getElementById(id);
          if (el && el.tagName === 'DETAILS') el.open = true;
        });
        var focusEl = findFocus(pending.focus);
        if (focusEl && typeof focusEl.focus === 'function') {
          try { focusEl.focus({ preventScroll: true }); } catch (e) { try { focusEl.focus(); } catch (e2) {} }
        }
        var y = pending.y || 0;
        window.scrollTo(0, y);
        window.requestAnimationFrame(function () { window.scrollTo(0, y); });
      };
      if (document.readyState === 'complete') run();
      else window.addEventListener('load', run, { once: true });
    }

    // Offer the affordance whenever the trail holds a real previous page, so any
    // context-changing click is reversible -- not only deep scrolls or open cards.
    // Each click pops one hop and restores it exactly; repeated clicks unwind the
    // whole trail back to the exact place the visitor started. Idempotent: it
    // clears any existing pill first, so it can safely re-run on a back-forward-
    // cache restore without stacking duplicate buttons.
    function renderAffordance() {
      var old = document.querySelector('.viewback');
      if (old && old.parentNode) old.parentNode.removeChild(old);
      // body.has-viewback lets CSS reserve bottom clearance so page content can
      // always scroll clear of the fixed pill; kept in lockstep with the pill.
      if (document.body) document.body.classList.remove('has-viewback');

      var trail = readStack();
      var prev = trail.length ? trail[trail.length - 1] : null;
      if (!prev || !prev.path || prev.path === location.pathname) return;

      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'viewback';
      btn.setAttribute(
        'aria-label',
        'Back to previous view: ' + prev.title
      );
      var arrow = document.createElement('span');
      arrow.className = 'viewback__arrow';
      arrow.setAttribute('aria-hidden', 'true');
      arrow.textContent = '←';
      var lab = document.createElement('span');
      lab.className = 'viewback__label';
      lab.appendChild(document.createTextNode('Back to '));
      var where = document.createElement('span');
      where.className = 'viewback__where';
      where.textContent = prev.title;
      lab.appendChild(where);
      btn.appendChild(arrow);
      btn.appendChild(lab);
      var remove = function () {
        btn.classList.remove('is-shown');
        if (document.body) document.body.classList.remove('has-viewback');
        setTimeout(function () { if (btn.parentNode) btn.parentNode.removeChild(btn); }, 240);
      };
      btn.addEventListener('click', function () {
        var stack = readStack();
        var target = stack.length ? stack[stack.length - 1] : prev;
        write(KEY_STACK, stack.slice(0, -1)); // drop the hop we are about to take
        write(KEY_RESTORE, target);
        suppress = true;                       // the return hop must not re-push this page
        location.href = target.url;
      });
      btn.addEventListener('keydown', function (ev) {
        if (ev.key === 'Escape') { ev.stopPropagation(); remove(); }
      });
      (document.body || document.documentElement).appendChild(btn);
      if (document.body) document.body.classList.add('has-viewback');
      window.requestAnimationFrame(function () { btn.classList.add('is-shown'); });
      // Entrance shows the full label (the feature announcing itself); after a
      // beat it folds to the arrow chip. CSS owns the fold and unfolds it on
      // hover/focus; this only arms the rest state.
      setTimeout(function () { btn.classList.add('is-rested'); }, 2600);
    }

    // Run order on a normal load: reconcile the trail, apply any pending restore,
    // then draw the pill from the settled trail.
    reconcile();
    applyPendingRestore();
    renderAffordance();

    // Back-forward-cache restore: the page is shown again from memory with no fresh
    // load, so nothing above re-ran while the trail may have advanced. Treat it as a
    // history traversal -- re-reconcile and rebuild the pill so its label and action
    // match the live trail (the cache already restored scroll and open state).
    window.addEventListener('pageshow', function (ev) {
      if (!ev.persisted) return;
      drop(KEY_RESTORE);
      reconcile(true);
      renderAffordance();
    });
  })();

  // --- Mobile sidebar drawer -------------------------------------------------
  (function drawer() {
    var btn = document.querySelector('.docs-menu-btn');
    var sidebar = document.querySelector('.docs-sidebar');
    if (!btn || !sidebar) return;
    // ARIA reconciliation (runtime). The build-time shell ships the button as
    // <button aria-label="Toggle navigation">Menu</button>, but that aria-label
    // overrides the visible "Menu" text without containing it -- a WCAG 2.5.3
    // (Label in Name) violation flagged by Lighthouse on mobile. Drop the redundant
    // label so the visible text IS the accessible name; aria-expanded + aria-controls
    // still convey the toggle. Runs every load, so it survives owner HTML regen (the
    // builder-side fix is captured for the clean-source --write).
    if (btn.textContent.trim()) btn.removeAttribute('aria-label');
    function setOpen(open) {
      document.body.classList.toggle('nav-open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      // Move focus into the drawer when it opens so keyboard/SR users land in the
      // newly-revealed navigation instead of staying on the overlaid toggle. The
      // sidebar is visibility:hidden when closed, so this only runs once the
      // nav-open class above has made it focusable. Focus return on close is
      // handled by the Escape and outside-click paths (a link click navigates).
      if (open) {
        var firstLink = sidebar.querySelector('a');
        if (firstLink) firstLink.focus();
      }
    }
    btn.addEventListener('click', function () {
      setOpen(!document.body.classList.contains('nav-open'));
    });
    sidebar.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') setOpen(false);
    });
    document.addEventListener('keydown', function (e) {
      // Scope this global listener to the actual open state: act (and return focus
      // to the toggle) only when the drawer is open, so a stray Escape elsewhere
      // does not poke the nav button's state or yank focus.
      if (e.key === 'Escape' && document.body.classList.contains('nav-open')) {
        setOpen(false);
        btn.focus();
      }
    });
    document.addEventListener('click', function (e) {
      if (document.body.classList.contains('nav-open') &&
          !e.target.closest('.docs-sidebar') && !e.target.closest('.docs-menu-btn')) {
        setOpen(false);
        btn.focus();
      }
    });
  })();

  // --- Docs sidebar scroll memory --------------------------------------------
  (function sidebarScrollMemory() {
    var sidebar = document.querySelector('[data-docs-sidebar]') || document.querySelector('.docs-sidebar');
    if (!sidebar) return;
    var KEY = 'mc:docs-sidebar-scroll-top';
    var storage = null;
    try {
      storage = window.sessionStorage;
      var probe = '__mc_sidebar_scroll';
      storage.setItem(probe, '1');
      storage.removeItem(probe);
    } catch (e) {
      storage = null;
    }
    if (!storage) return;

    function savedTop() {
      var raw = storage.getItem(KEY);
      if (raw === null || raw === '') return null;
      var top = Number(raw);
      return isFinite(top) && top >= 0 ? top : null;
    }

    function clamp(top) {
      var max = Math.max(0, (sidebar.scrollHeight || 0) - (sidebar.clientHeight || 0));
      return Math.max(0, Math.min(top, max));
    }

    function restore() {
      var top = savedTop();
      if (top === null) return;
      sidebar.scrollTop = clamp(top);
    }

    function save() {
      storage.setItem(KEY, String(Math.max(0, Math.round(sidebar.scrollTop || 0))));
    }

    restore();
    if (window.requestAnimationFrame) window.requestAnimationFrame(restore);
    window.addEventListener('load', restore, { once: true });
    sidebar.addEventListener('scroll', save, { passive: true });
    sidebar.addEventListener('click', function (e) {
      if (e.target && e.target.closest && e.target.closest('a[href]')) save();
    }, true);
    window.addEventListener('pagehide', save);
  })();

  // --- On-this-page scrollspy ------------------------------------------------
  (function scrollspy() {
    if (!('IntersectionObserver' in window)) return;
    var links = Array.prototype.slice.call(document.querySelectorAll('.docs-toc a[href^="#"]'));
    if (!links.length) return;
    var byId = {};
    links.forEach(function (link) {
      var id = decodeURIComponent(link.getAttribute('href').slice(1));
      if (id) byId[id] = link;
    });
    var headings = Object.keys(byId)
      .map(function (id) { return document.getElementById(id); })
      .filter(Boolean);
    if (!headings.length) return;
    var visible = {};
    function highlight() {
      var current = null;
      for (var i = 0; i < headings.length; i++) {
        if (visible[headings[i].id]) { current = headings[i].id; break; }
      }
      // Always clear first, so scrolling past the last heading (into the footer /
      // pager) doesn't leave the previous link stuck highlighted.
      links.forEach(function (l) { l.classList.remove('is-current'); });
      if (current && byId[current]) byId[current].classList.add('is-current');
    }
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) { visible[entry.target.id] = entry.isIntersecting; });
      highlight();
    }, { rootMargin: '0px 0px -68% 0px', threshold: 0 });
    headings.forEach(function (h) { observer.observe(h); });
  })();

  // --- On-this-page rides the page scroll (no second scrollbar) -------------
  // When the rail is taller than the viewport, a fixed sticky `top` strands its
  // lower entries off-screen. Rather than give the rail its own scrollbar, drive
  // its sticky `top` from page-scroll progress: pinned below the header at the
  // top of the page, sliding up in proportion as you scroll so lower entries
  // come into view, bottom-aligned when you reach the end. One scrollbar (page),
  // and the rail always shows the region near where you are reading.
  (function tocRidesPage() {
    var toc = document.querySelector('.docs-toc');
    if (!toc) return;
    var HEADER = 58, GAP = 24, ticking = false;
    function place() {
      ticking = false;
      var vh = window.innerHeight;
      var h = toc.offsetHeight;
      if (h <= vh - HEADER - GAP) { toc.style.top = HEADER + 'px'; return; }
      var maxTop = HEADER;             // page top: rail pinned below the header
      var minTop = vh - h - GAP;       // page end: rail bottom-aligned (negative)
      var pageOverflow = document.documentElement.scrollHeight - vh;
      var p = pageOverflow > 0 ? Math.min(1, Math.max(0, window.scrollY / pageOverflow)) : 0;
      toc.style.top = (maxTop - (maxTop - minTop) * p) + 'px';
    }
    function onScroll() { if (!ticking) { ticking = true; requestAnimationFrame(place); } }
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    place();
  })();

  // --- Evidence-spine wash (landing) ----------------------------------------
  // One-time, cause-and-effect motion: when the first-loop list scrolls into
  // view, its step numbers light in sequence (CSS owns the animation). The list
  // is identical static text without JS, and reduced-motion readers are
  // excluded both here and in the stylesheet.
  (function loopSpine() {
    var list = document.querySelector('[data-loop-spine]');
    if (!list || !('IntersectionObserver' in window)) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        list.classList.add('loop-spine-live');
        observer.disconnect();
      });
    }, { threshold: 0.35 });
    observer.observe(list);
  })();

  // --- Copy buttons on code blocks ------------------------------------------
  (function copyButtons() {
    var blocks = Array.prototype.slice.call(document.querySelectorAll('.docs-article pre'));
    if (!blocks.length) return;

    blocks.forEach(function (pre) {
      var code = pre.querySelector('code');
      if (!code) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'copy-btn';
      btn.textContent = 'Copy';
      btn.setAttribute('aria-label', 'Copy code to clipboard');
      var timer;
      function flash(label, ok) {
        btn.textContent = label;
        btn.classList.toggle('is-copied', !!ok);
        announce(ok ? 'Copied to clipboard' : 'Press Command or Control C to copy');
        clearTimeout(timer);
        timer = setTimeout(function () {
          btn.textContent = 'Copy';
          btn.classList.remove('is-copied');
        }, 1600);
      }
      btn.addEventListener('click', function () {
        if (copyTextSync(code.textContent)) { flash('Copied', true); return; }
        // Last resort: hand the user a ready-to-copy selection.
        selectTextNode(code);
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(code.textContent).then(
            function () { flash('Copied', true); },
            function () { flash('Press to copy', false); }
          );
        } else {
          flash('Press to copy', false);
        }
      });
      pre.appendChild(btn);
    });
  })();

  // --- Page text JSON export -------------------------------------------------
  (function pageExport() {
    var buttons = Array.prototype.slice.call(document.querySelectorAll('[data-page-export]'));
    if (!buttons.length) return;

    var SITE_PATH_MARKER = '/sites/microcosm/';

    function normalizeSitePath(pathname) {
      var path = String(pathname || '').replace(/\\/g, '/');
      var markerIndex = path.indexOf(SITE_PATH_MARKER);
      if (markerIndex !== -1) {
        path = path.slice(markerIndex + SITE_PATH_MARKER.length);
      } else {
        var docsIndex = path.lastIndexOf('/docs/');
        if (docsIndex !== -1) path = path.slice(docsIndex + 1);
        else path = path.split('/').filter(Boolean).pop() || 'index.html';
      }
      path = path.replace(/^\/+/, '');
      if (!path) path = 'index.html';
      if (/\/$/.test(path)) path += 'index.html';
      return path;
    }

    function currentSitePath() {
      return normalizeSitePath(window.location && window.location.pathname);
    }

    function siteHrefFromUrl(url) {
      return normalizeSitePath(url.pathname) + (url.search || '') + (url.hash || '');
    }

    function publicSiteHref(href) {
      var value = String(href || '').trim();
      if (!value) return '';
      try {
        var url = new URL(value, window.location.href);
        if (url.protocol === 'mailto:') return url.href;
        if (/^(?:javascript|data|vbscript):$/i.test(url.protocol)) return '';
        if ((url.protocol === 'http:' || url.protocol === 'https:') && url.origin !== window.location.origin) {
          return url.href;
        }
        return siteHrefFromUrl(url);
      } catch (e) {
        return value.replace(/^file:\/\/[^#?]*/, currentSitePath());
      }
    }

    function currentPageHref() {
      return publicSiteHref(
        (window.location && (window.location.pathname + window.location.search + window.location.hash)) || ''
      );
    }

    function metaDescription() {
      var meta = document.querySelector('meta[name="description"]');
      return meta ? cleanText(meta.getAttribute('content')) : '';
    }

    function headingRows(article) {
      return Array.prototype.slice.call(article.querySelectorAll('h1, h2, h3')).map(function (heading, index) {
        return {
          index: index,
          level: Number(heading.tagName.slice(1)),
          id: heading.id || null,
          text: cloneText(heading, { dropLabels: true })
        };
      }).filter(function (row) { return row.text; });
    }

    function sectionRows(article) {
      var headings = Array.prototype.slice.call(article.querySelectorAll('h1, h2, h3'));
      return headings.map(function (heading, index) {
        var level = Number(heading.tagName.slice(1));
        var parts = [];
        var node = heading.nextElementSibling;
        while (node) {
          if (/^H[1-3]$/.test(node.tagName) && Number(node.tagName.slice(1)) <= level) break;
          var text = cloneText(node, { dropLabels: true });
          if (text) parts.push(text);
          node = node.nextElementSibling;
        }
        return {
          index: index,
          level: level,
          id: heading.id || null,
          heading: cloneText(heading, { dropLabels: true }),
          text: cleanText(parts.join('\n\n'))
        };
      }).filter(function (row) { return row.heading || row.text; });
    }

    function linkRows(article) {
      return Array.prototype.slice.call(article.querySelectorAll('a[href]')).map(function (link) {
        return {
          text: cleanText(link.textContent),
          href: publicSiteHref(link.getAttribute('href'))
        };
      }).filter(function (row) { return row && row.text && row.href; });
    }

    function blockRows(article) {
      var selector = 'h1, h2, h3, p, li, pre';
      return Array.prototype.slice.call(article.querySelectorAll(selector)).map(function (node, index) {
        var text = cloneText(node, { dropLabels: false });
        if (!text) return null;
        return {
          index: index,
          type: node.tagName.toLowerCase(),
          id: node.id || null,
          text: text
        };
      }).filter(Boolean);
    }

    function componentRows(article) {
      return Array.prototype.slice.call(article.querySelectorAll('.comp-card')).map(function (card, index) {
        function many(selector) {
          return Array.prototype.slice.call(card.querySelectorAll(selector))
            .map(function (node) { return cleanText(node.textContent); })
            .filter(Boolean);
        }
        function links(selector) {
          return Array.prototype.slice.call(card.querySelectorAll(selector + ' a[href]')).map(function (link) {
            return {
              text: cleanText(link.textContent),
              href: publicSiteHref(link.getAttribute('href'))
            };
          }).filter(function (row) { return row.text && row.href; });
        }
        return {
          index: index,
          anchor: card.id || null,
          name: cloneText(card.querySelector('.name'), { dropLabels: true }),
          summary: cloneText(card.querySelector('.comp-card__job'), { dropLabels: true }),
          does: cloneText(card.querySelector('.comp-card__what'), { dropLabels: true }),
          does_not_prove: cloneText(card.querySelector('.comp-card__scope'), { dropLabels: true }),
          run: cloneText(card.querySelector('.comp-card__cmd code'), { dropLabels: true }),
          evidence: many('.comp-card__evidence .comp-chip'),
          tags: many('.comp-card__tags-row .tag'),
          links_to: links('.comp-card__links'),
          source_links: links('.comp-card__source')
        };
      }).filter(function (row) { return row.name; });
    }

    function buildPayload(article) {
      var title = cleanText((article.querySelector('h1') || document.querySelector('title') || {}).textContent);
      var sourceText = cloneText(article, { dropLabels: false });
      var sections = sectionRows(article);
      var components = componentRows(article);
      return {
        schema_version: 'microcosm_page_text_export_v1',
        artifact_kind: 'page_text_export',
        generated_at: new Date().toISOString(),
        source: {
          site: 'Microcosm',
          title: title,
          description: metaDescription(),
          url: currentPageHref(),
          path: currentSitePath()
        },
        reader_contract: {
          source_text_authority: 'source_text',
          sections_are_navigation_projection: true,
          component_rows_are_extracted_from_visible_component_cards: components.length > 0
        },
        counts: {
          characters: sourceText.length,
          headings: article.querySelectorAll('h1, h2, h3').length,
          links: article.querySelectorAll('a[href]').length,
          sections: sections.length,
          components: components.length
        },
        source_text: sourceText,
        headings: headingRows(article),
        links: linkRows(article),
        sections: sections,
        source_blocks: blockRows(article),
        components: components
      };
    }

    // Readable transcription of the whole view, every collapsed card expanded.
    // textContent already ignores a <details> open/closed state, so this reads as
    // if a reader had expanded everything and transcribed it by hand -- a cleaner
    // result than Cmd-A/Cmd-C, which would miss every collapsed card body. Block
    // elements (and a few labelled spans) become their own lines; inline element
    // boundaries get a separating space so adjacent spans (e.g. an analogy map's
    // "X is like Y") do not run together.
    function readablePageText(article) {
      var SKIP_TAG = { SCRIPT: 1, STYLE: 1, SVG: 1, BUTTON: 1, NOSCRIPT: 1, TEMPLATE: 1 };
      var SKIP_CLASS = ['copy-btn', 'page-export-btn', 'page-export-status',
        'docs-pagetools', 'docs-pager', 'breadcrumb', 'docs-toc', 'sr-only',
        'copy-proxy'];
      var BLOCK = { H1: 1, H2: 1, H3: 1, H4: 1, H5: 1, H6: 1, P: 1, LI: 1,
        SECTION: 1, DETAILS: 1, SUMMARY: 1, TR: 1, BLOCKQUOTE: 1, FIGCAPTION: 1,
        DD: 1, DT: 1, PRE: 1 };
      function skip(node) {
        if (SKIP_TAG[node.tagName]) return true;
        if (node.hidden) return true;
        if (node.getAttribute && node.getAttribute('aria-hidden') === 'true') return true;
        var cl = node.classList;
        if (cl) { for (var i = 0; i < SKIP_CLASS.length; i++) { if (cl.contains(SKIP_CLASS[i])) return true; } }
        return false;
      }
      function walk(node) {
        if (node.nodeType === 3) return node.nodeValue.replace(/\s+/g, ' ');
        if (node.nodeType !== 1) return '';
        if (skip(node)) return '';
        var inner = '';
        for (var c = node.firstChild; c; c = c.nextSibling) {
          var piece = walk(c);
          if (!piece) continue;
          // separate adjacent inline elements so spans don't fuse
          inner += (c.nodeType === 1 && inner && !/\s$/.test(inner)) ? (' ' + piece) : piece;
        }
        var cl = node.classList;
        // a labelled span ("In plain terms", "Analogy", ...) becomes "Label: "
        if (cl && cl.contains('dcard__label')) {
          var lt = inner.replace(/\s+/g, ' ').trim();
          return lt ? '\n' + lt + ': ' : '';
        }
        var asBlock = BLOCK[node.tagName] || (cl && cl.contains('dcard__map'));
        if (asBlock) {
          var bt = inner.replace(/[ \t]+/g, ' ').replace(/\s*\n\s*/g, '\n').trim();
          return bt ? '\n' + bt + '\n' : '';
        }
        return inner;
      }
      return walk(article)
        .replace(/[ \t]+/g, ' ')
        .replace(/[ \t]*\n[ \t]*/g, '\n')
        .replace(/\n{3,}/g, '\n\n')
        .trim();
    }

    function pageSlug() {
      var leaf = currentSitePath().split('/').pop() || 'page';
      return leaf.replace(/\.html?$/i, '') || 'page';
    }

    function downloadFile(filename, text, mime) {
      try {
        var blob = new Blob([text], { type: mime || 'application/json' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.rel = 'noopener';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.setTimeout(function () { URL.revokeObjectURL(url); }, 1000);
        return true;
      } catch (e) {
        return false;
      }
    }

    function copyOrSelect(text, flash, okLabel) {
      if (copyTextSync(text)) { flash(okLabel, true); return; }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(
          function () { flash(okLabel, true); },
          function () { selectRawText(text); flash('Selected for copy', false); }
        );
      } else {
        selectRawText(text);
        flash('Selected for copy', false);
      }
    }

    buttons.forEach(function (btn) {
      var action = (btn.getAttribute('data-page-export') || '').toLowerCase();
      var statusId = btn.getAttribute('aria-describedby');
      var status = statusId ? document.getElementById(statusId) : null;
      var flash = makeStatusFlash(btn, status, btn.innerHTML);
      btn.addEventListener('click', function () {
        var article = btn.closest('.docs-article') || document.querySelector('.docs-article');
        if (!article) return;

        if (action === 'text') {
          var prose = readablePageText(article);
          copyOrSelect(prose, flash, 'Copied page text');
          return;
        }

        var payload = buildPayload(article);
        var json = JSON.stringify(payload, null, 2);

        if (action === 'download') {
          var ok = downloadFile(pageSlug() + '.json', json);
          if (ok) { flash('Downloaded JSON', true); }
          else { copyOrSelect(json, flash, 'JSON selected for copy'); }
          return;
        }

        // default (bare data-page-export): copy structured JSON to the clipboard
        var message = payload.counts.components
          ? ('Copied ' + payload.counts.components + ' components as JSON')
          : 'Copied structured page JSON';
        copyOrSelect(json, flash, message);
      });
    });
  })();

  // --- Whole-site structured packet export ----------------------------------
  (function siteExport() {
    var controls = Array.prototype.slice.call(document.querySelectorAll('[data-site-export], [data-site-download]'));
    if (!controls.length) return;
    var packetConfigs = {
      orientation: {
        kind: 'orientation',
        filename: 'ai-orientation-packet.js',
        scriptAttr: 'data-ai-orientation-packet',
        fallbackFilename: 'microcosm-ai-concise-orientation-guide.md',
        unavailable: 'Concise guide unavailable',
        loadWarning: 'Microcosm: ai-orientation-packet.js failed to load; concise guide export unavailable.'
      },
      full: {
        kind: 'full',
        filename: 'site-packet.js',
        scriptAttr: 'data-site-packet',
        fallbackFilename: 'microcosm-site-map.json',
        unavailable: 'Site map unavailable',
        loadWarning: 'Microcosm: site-packet.js failed to load; site map export unavailable.'
      },
      'reader-digest': {
        kind: 'reader-digest',
        // Raw root JSON, not a script packet. The landing control is a real
        // same-origin <a href download>; JS only announces the click and leaves
        // the browser's native download path intact, except for file:// previews
        // where Chrome ignores download="" and opens JSON in the tab.
        filename: 'ai-reader-digest-packet.js',
        scriptAttr: 'data-ai-reader-digest-packet',
        textGlobal: '__MICROCOSM_AI_READER_DIGEST_JSON__',
        fetchPath: 'microcosm-ai-reader-digest.json',
        fallbackFilename: 'microcosm-ai-reader-digest.json',
        unavailable: 'Reader digest unavailable',
        loadWarning: 'Microcosm: ai-reader-digest-packet.js failed to load; local file download unavailable.'
      },
      'review-packet': {
        kind: 'review-packet',
        // The single primary AI handoff capsule; static file first, so it works
        // with JS off, stale user activation rules, strict browsers, and file
        // previews that reject async fetch->Blob downloads.
        filename: 'ai-review-packet.js',
        scriptAttr: 'data-ai-review-packet',
        textGlobal: '__MICROCOSM_AI_REVIEW_PACKET_JSON__',
        fetchPath: 'microcosm-ai-review-packet.json',
        fallbackFilename: 'microcosm-ai-review-packet.json',
        unavailable: 'Review packet unavailable',
        loadWarning: 'Microcosm: ai-review-packet.js failed to load; local file download unavailable.'
      }
    };
    var callbacks = {};
    var loading = {};
    Object.keys(packetConfigs).forEach(function (kind) {
      callbacks[kind] = [];
      loading[kind] = false;
    });

    function packetKind(btn) {
      var raw = String(btn.getAttribute('data-site-packet-kind') || '').trim().toLowerCase();
      return packetConfigs[raw] ? raw : 'full';
    }

    function getPacket(config) {
      var packet = config.kind === 'orientation'
        ? window.__MICROCOSM_AI_ORIENTATION_PACKET__
        : window.__MICROCOSM_SITE_PACKET__;
      return packet && typeof packet === 'object' ? packet : null;
    }

    function getTextPacket(config) {
      var key = config.textGlobal || '';
      var text = key ? window[key] : null;
      return typeof text === 'string' && text ? text : null;
    }

    function assetUrl(config) {
      var src = document.currentScript && document.currentScript.src;
      if (!src) {
        var scripts = Array.prototype.slice.call(document.querySelectorAll('script[src]'));
        var docsScript = scripts.filter(function (script) {
          return /(?:^|\/)docs\.js(?:[?#].*)?$/.test(script.getAttribute('src') || script.src || '');
        }).pop();
        src = docsScript && (docsScript.src || docsScript.getAttribute('src'));
      }
      if (src) return src.replace(/docs\.js(?:[?#].*)?$/, config.filename);
      return window.location.pathname.indexOf('/docs/') !== -1 ? '../assets/' + config.filename : 'assets/' + config.filename;
    }

    function complete(config, packet) {
      loading[config.kind] = false;
      var queued = callbacks[config.kind].slice();
      callbacks[config.kind] = [];
      queued.forEach(function (cb) { cb(packet); });
    }

    function loadPacket(config, cb) {
      var packet = getPacket(config);
      if (packet) { cb(packet); return; }
      callbacks[config.kind].push(cb);
      if (loading[config.kind]) return;
      loading[config.kind] = true;

      var existing = document.querySelector('script[' + config.scriptAttr + ']');
      if (existing) {
        if (existing.getAttribute('data-loaded') === 'true') {
          complete(config, getPacket(config));
          return;
        }
        existing.addEventListener('load', function () { complete(config, getPacket(config)); });
        existing.addEventListener('error', function () { complete(config, null); });
        return;
      }

      var s = document.createElement('script');
      s.src = assetUrl(config);
      s.async = true;
      s.setAttribute(config.scriptAttr, '');
      s.addEventListener('load', function () {
        s.setAttribute('data-loaded', 'true');
        complete(config, getPacket(config));
      });
      s.addEventListener('error', function () {
        if (window.console && console.warn) console.warn(config.loadWarning);
        complete(config, null);
      });
      document.head.appendChild(s);
    }

    function loadTextPacket(config, cb) {
      var text = getTextPacket(config);
      if (text) { cb(text); return; }
      callbacks[config.kind].push(cb);
      if (loading[config.kind]) return;
      loading[config.kind] = true;

      var existing = document.querySelector('script[' + config.scriptAttr + ']');
      if (existing) {
        if (existing.getAttribute('data-loaded') === 'true') {
          complete(config, getTextPacket(config));
          return;
        }
        existing.addEventListener('load', function () { complete(config, getTextPacket(config)); });
        existing.addEventListener('error', function () { complete(config, null); });
        return;
      }

      var s = document.createElement('script');
      s.src = assetUrl(config);
      s.async = true;
      s.setAttribute(config.scriptAttr, '');
      s.addEventListener('load', function () {
        s.setAttribute('data-loaded', 'true');
        complete(config, getTextPacket(config));
      });
      s.addEventListener('error', function () {
        if (window.console && console.warn) console.warn(config.loadWarning);
        complete(config, null);
      });
      document.head.appendChild(s);
    }

    function safeDownloadFilename(raw, fallback) {
      fallback = fallback || 'microcosm-site-map.json';
      var value = String(raw || fallback).trim();
      value = value.replace(/[\\/:*?"<>|]+/g, '-').replace(/\s+/g, '-');
      if (!value) value = fallback;
      if (!/\.json$/i.test(value)) value += '.json';
      return value;
    }

    function downloadJson(filename, json) {
      if (typeof Blob === 'undefined' || !window.URL || !window.URL.createObjectURL) return false;
      try {
        var blob = new Blob([json], { type: 'application/json;charset=utf-8' });
        var url = window.URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = safeDownloadFilename(filename, 'microcosm-site-map.json');
        a.rel = 'noopener';
        a.className = 'copy-proxy';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.setTimeout(function () { window.URL.revokeObjectURL(url); }, 1000);
        return true;
      } catch (e) {
        return false;
      }
    }

    function concisePayload(packet) {
      if (packet && packet.copy_brief && typeof packet.copy_brief === 'object') return packet.copy_brief;
      return packet;
    }

    function exportText(config, payload) {
      if (
        config.kind === 'orientation' &&
        payload &&
        typeof payload.copy_text_markdown === 'string' &&
        payload.copy_text_markdown
      ) {
        return payload.copy_text_markdown;
      }
      return JSON.stringify(payload, null, 2);
    }

    function copyMessage(config, payload, packet) {
      if (config.kind === 'orientation') {
        var pages = payload && payload.source_pages ? payload.source_pages : [];
        return 'Concise guide copied - ' + pages.length + ' source pages for your AI assistant';
      }
      var counts = (packet && packet.counts) || {};
      return 'JSON map copied - ' + (counts.page_count || 0) + ' pages and ' + (counts.component_count || 0) + ' components indexed';
    }

    function useNativeDownload(btn, flash) {
      var href = btn.tagName === 'A' ? btn.getAttribute('href') : '';
      if (window.location.protocol === 'file:') return false;
      if (!href || !btn.hasAttribute('download')) return false;
      flash('Download started - attach it to your AI assistant', true);
      return true;
    }

    function downloadTextPacket(btn, config, flash, event) {
      if (event && event.preventDefault) { event.preventDefault(); event.stopPropagation(); }
      var filename = btn.getAttribute('data-download-filename') || btn.getAttribute('download') || config.fallbackFilename;
      var text = getTextPacket(config);
      if (!text) {
        loadTextPacket(config, function () {});
        flash('Preparing download - press again in a moment', false);
        return;
      }
      if (downloadJson(filename, text)) {
        flash('Download started - attach it to your AI assistant', true);
      } else {
        flash('Could not start the download. Use the direct file links under Advanced.', false);
      }
    }

    function fetchDownload(btn, config, flash, event) {
      if (window.location.protocol === 'file:' && config.textGlobal) {
        downloadTextPacket(btn, config, flash, event);
        return;
      }

      // Same-origin static packets must keep their native href/download path.
      // Async fetch->Blob synthetic clicks are not reliable across browsers
      // because user activation can be gone by the time the fetch completes.
      if (useNativeDownload(btn, flash)) return;

      // Non-native controls must download or honestly fail; they must not open
      // a raw JSON tab. Neutralise navigation before support checks or async
      // work.
      if (event && event.preventDefault) { event.preventDefault(); event.stopPropagation(); }
      var url = btn.getAttribute('data-download-url')
        || ((btn.tagName === 'A' && btn.href) ? btn.href : config.fetchPath);
      var filename = btn.getAttribute('data-download-filename') || btn.getAttribute('download') || config.fallbackFilename;
      var failMessage = 'Could not start the download. Use the direct file links under Advanced.';
      if (typeof fetch !== 'function' || typeof Blob === 'undefined' || !window.URL || !window.URL.createObjectURL) {
        flash(failMessage, false);
        return;
      }
      fetch(url, { credentials: 'same-origin', cache: 'no-store' })
        .then(function (res) {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          return res.text();
        })
        .then(function (text) {
          // Byte-identical payload: no reparse/re-serialize, so the file keeps
          // its committed source_fingerprint bytes.
          if (!downloadJson(filename, text)) throw new Error('blob-download-failed');
          flash('Download started - attach it to your AI assistant', true);
        })
        .catch(function (err) {
          // Honest failure only. Auto-opening the raw JSON here would recreate
          // the exact failure this path exists to prevent.
          if (window.console && console.error) console.error('Microcosm packet download failed', err);
          flash(failMessage, false);
        });
    }

    controls.forEach(function (btn) {
      var statusId = btn.getAttribute('aria-describedby');
      var status = statusId ? document.getElementById(statusId) : null;
      var flash = makeStatusFlash(btn, status, btn.innerHTML);
      btn.addEventListener('click', function (event) {
        var config = packetConfigs[packetKind(btn)];
        if (config.fetchPath) { fetchDownload(btn, config, flash, event); return; }
        loadPacket(config, function (packet) {
          if (!packet) { flash(config.unavailable, false); return; }
          var payload = btn.hasAttribute('data-site-export') && config.kind === 'orientation'
            ? concisePayload(packet)
            : packet;
          var text = exportText(config, payload);
          if (btn.hasAttribute('data-site-download')) {
            var json = JSON.stringify(payload, null, 2);
            var filename = btn.getAttribute('data-download-filename') || (packet.delivery && packet.delivery.recommended_full_filename) || config.fallbackFilename;
            if (downloadJson(filename, json)) {
              flash(config.kind === 'full' ? 'JSON map download started' : 'Download started - attach it to your AI assistant', true);
            } else {
              selectRawText(json);
              flash('JSON selected for copy', false);
            }
            return;
          }
          var message = copyMessage(config, payload, packet);
          function fallbackCopy() {
            if (copyTextSync(text)) { flash(message, true); return; }
            selectRawText(text);
            flash(config.kind === 'orientation' ? 'Concise guide selected for copy' : 'Site packet selected for copy', false);
          }
          if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(
              function () { flash(message, true); },
              fallbackCopy
            );
          } else {
            fallbackCopy();
          }
        });
      });
    });

    if (window.location.protocol === 'file:') {
      ['review-packet', 'reader-digest'].forEach(function (kind) {
        loadTextPacket(packetConfigs[kind], function () {});
      });
    }
  })();

  // --- Copy a question set ([data-qset] box) or its <pre> prompt fallback ----
  (function questionsCopy() {
    var failMsg = 'Copy failed. Select the text and press Command or Control C.';
    Array.prototype.forEach.call(document.querySelectorAll('[data-copy-questions]'), function (btn) {
      var statusId = btn.getAttribute('aria-describedby');
      var status = statusId ? document.getElementById(statusId) : null;
      var flash = makeStatusFlash(btn, status, btn.innerHTML);
      btn.addEventListener('click', function () {
        var box = btn.closest('[data-qset]') || btn.closest('.ai-questions');
        var items = box ? box.querySelectorAll('li') : [];
        var text = Array.prototype.map.call(items, function (li) {
          return li.textContent.replace(/\s+/g, ' ').trim();
        }).join('\n');
        if (!text && box) {
          var pre = box.querySelector('pre');
          if (pre) text = pre.textContent.replace(/\s+/g, ' ').trim();
        }
        if (!text) { flash('Nothing to copy', false); return; }
        if (copyTextSync(text)) { flash('Copied', true); return; }
        if (typeof navigator !== 'undefined' && navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(
            function () { flash('Copied', true); },
            function () { flash(failMsg, false); }
          );
        } else {
          flash(failMsg, false);
        }
      });
    });
  })();

  // --- Client-side component filter -----------------------------------------
  (function componentFilter() {
    var toolbar = document.querySelector('[data-comp-filter]');
    var input = document.getElementById('comp-filter-input');
    if (!toolbar || !input) return;
    var items = Array.prototype.slice.call(document.querySelectorAll('.comp-item'));
    if (!items.length) return;
    var groups = Array.prototype.slice.call(document.querySelectorAll('[data-comp-group]'));
    var status = document.getElementById('comp-filter-status');
    var empty = document.querySelector('[data-comp-empty]');
    var countLabel = toolbar.getAttribute('data-comp-count-label') || 'components';
    var total = items.length;
    var urlKey = toolbar.getAttribute('data-comp-filter-param') || 'filter';
    var canWriteUrl = !!(window.history && window.history.replaceState && window.URLSearchParams);
    var rows = items.map(function (li) {
      return {
        el: li,
        hay: String(li.getAttribute('data-search') || '').toLowerCase(),
        hidden: li.hasAttribute('hidden')
      };
    });
    var groupRows = groups.map(function (g) {
      return {
        el: g,
        items: Array.prototype.slice.call(g.querySelectorAll('.comp-item'))
      };
    });
    var pendingFrame = 0;

    function readUrlFilter() {
      if (!window.URLSearchParams) return '';
      try {
        return (new URLSearchParams(window.location.search || '')).get(urlKey) || '';
      } catch (e) {
        return '';
      }
    }

    function writeUrlFilter(value) {
      if (!canWriteUrl) return;
      try {
        var params = new URLSearchParams(window.location.search || '');
        if (value) params.set(urlKey, value);
        else params.delete(urlKey);
        var query = params.toString();
        var next = window.location.pathname + (query ? '?' + query : '') + window.location.hash;
        window.history.replaceState(null, '', next);
      } catch (e) {}
    }

    var initialFilter = readUrlFilter();
    if (initialFilter) input.value = initialFilter;

    toolbar.removeAttribute('hidden'); // reveal now that JS can power it

    function setHidden(el, hidden) {
      if (hidden) {
        if (!el.hasAttribute('hidden')) el.setAttribute('hidden', '');
      } else if (el.hasAttribute('hidden')) {
        el.removeAttribute('hidden');
      }
    }

    function apply(options) {
      var q = input.value.trim().toLowerCase();
      if (!options || !options.skipUrl) writeUrlFilter(input.value.trim());
      var shown = 0;
      rows.forEach(function (row) {
        var hide = !!q && row.hay.indexOf(q) === -1;
        setHidden(row.el, hide);
        row.hidden = hide;
        if (!hide) shown++;
      });
      groupRows.forEach(function (group) {
        var hasVisible = group.items.some(function (item) { return !item.hasAttribute('hidden'); });
        setHidden(group.el, !hasVisible);
      });
      if (empty) {
        setHidden(empty, shown !== 0);
      }
      if (status) {
        status.textContent = q ? (shown + ' of ' + total + ' shown') : (total + ' ' + countLabel);
      }
    }

    function scheduleApply() {
      if (pendingFrame) cancelAnimationFrame(pendingFrame);
      pendingFrame = requestAnimationFrame(function () {
        pendingFrame = 0;
        apply();
      });
    }

    input.addEventListener('input', scheduleApply);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { input.value = ''; apply(); }
    });
    window.addEventListener('popstate', function () {
      input.value = readUrlFilter();
      apply({ skipUrl: true });
    });
    if (empty) {
      var clearBtn = empty.querySelector('[data-comp-clear]');
      if (clearBtn) clearBtn.addEventListener('click', function () {
        input.value = '';
        apply();
        input.focus();
      });
    }
    apply({ skipUrl: true });
  })();

  // --- Command palette: site-wide search over the generated index -----------
  // Lazily loads window.__MICROCOSM_INDEX__ (a static, same-origin projection of
  // content-graph.json via <script src>) when the visitor opens search. Degrades
  // to a clear empty state if absent.
  (function search() {
    var modal = document.querySelector('[data-search-modal]');
    var input = modal && modal.querySelector('[data-search-input]');
    var list = modal && modal.querySelector('[data-search-results]');
    var emptyEl = modal && modal.querySelector('[data-search-empty]');
    var countEl = modal && modal.querySelector('[data-search-count]');
    var openers = document.querySelectorAll('[data-search-open]');
    var index = mcSearchIndexRecords();
    var searchIndexStatus = index.length ? 'ready' : 'idle';
    if (!modal || !input || !list) return;

    // ARIA semantics reconciliation (runtime). The build-time shell ships the
    // results <ul> as role="listbox", and rows historically carried role="option".
    // But every row holds real interactive controls (Copy command / Open source /
    // Copy packet ...), and an option's descendants are exposed as presentational,
    // so nested buttons/links inside an option are invalid ARIA. We are not a
    // combobox either (the input declares no combobox role / aria-activedescendant).
    // A "correct" listbox is impossible without removing the per-row actions, so we
    // demote the popup to an ordinary list: drop the listbox role here (this runs on
    // every load, so it survives owner HTML regeneration), keep rows as plain list
    // items with genuine focusable controls, and announce the active row via the
    // live region during arrow nav. The dialog focus trap keeps controls reachable.
    list.removeAttribute('role');

    // The build-time shell ships the search field with an aria-label but no id or
    // name; a nameless/idless form control trips a Chrome DevTools best-practice
    // issue (the field can't be referred to or autofill-mapped). Stamp a stable
    // name/id at runtime so the console stays clean -- runs every load, so it
    // survives owner HTML regeneration (the builder-side fix is captured for the
    // clean-source --write). Only set what's missing so an owner fix wins.
    if (!input.getAttribute('name')) input.setAttribute('name', 'microcosm-search');
    if (!input.id) input.id = 'cmdk-search-input';

    var KIND = { component: 'Component', area: 'Area', page: 'Page', 'paper module': 'Paper module' };
    // Kinds absent from KIND fall back to their raw id; snake_case ones (e.g.
    // source_ref) would otherwise surface as "source_ref" in the result chip,
    // screen-reader announcement, and count summary. Humanise underscores so
    // every kind label reads public-voiced wherever it is shown.
    function kindLabel(k) { return KIND[k] || String(k).replace(/_/g, ' '); }
    // Role descriptor: the two object kinds play different reader roles -- a paper
    // module is the explanation you read, a component is the spec/evidence record.
    // Surfacing the role on every result row teaches the split inside search itself,
    // not only on the pages and the map panel. Derived from the existing kind; no new
    // search-index field.
    var ROLE = { component: 'spec & evidence', 'paper module': 'explanation' };
    function roleLabel(k) { return ROLE[k] || ''; }
    var results = [];
    var active = -1;
    var renderFrame = 0;
    var emptyDefault = null; // build-time empty-state copy, captured on first miss

    function tokens(s) { return s.toLowerCase().split(/\s+/).filter(Boolean); }

    function setEmptyState(message) {
      list.innerHTML = '';
      results = [];
      active = -1;
      if (emptyEl) {
        if (emptyDefault == null) emptyDefault = emptyEl.textContent;
        emptyEl.textContent = message || emptyDefault;
        emptyEl.removeAttribute('hidden');
      }
      if (countEl) countEl.textContent = '';
    }

    function ensureSearchIndex(cb) {
      if (index.length) {
        searchIndexStatus = 'ready';
        if (cb) cb();
        return;
      }
      searchIndexStatus = 'loading';
      withSearchIndex(function (records) {
        index = records || [];
        searchIndexStatus = index.length ? 'ready' : 'failed';
        if (cb) cb();
      });
    }

    function score(rec, qs) {
      var label = String(rec.label || '').toLowerCase();
      var hay = (label + ' ' + (rec.family || '') + ' ' + (rec.tags || []).join(' ') + ' ' + (rec.text || '')).toLowerCase();
      var s = 0;
      for (var i = 0; i < qs.length; i++) {
        var t = qs[i];
        if (hay.indexOf(t) === -1) return -1; // every token must appear somewhere
        if (label.indexOf(t) === 0) s += 6;
        else if (label.indexOf(t) !== -1) s += 3;
        else s += 1;
      }
      // Intent-aware bias. A code-shaped query (an identifier, command, or path)
      // wants the component spec; a natural-language query wants the paper-module
      // write-up that explains it. Pages stay lightly boosted as orientation.
      var codey = false;
      for (var ci = 0; ci < qs.length; ci++) {
        if (/[_/.]|--/.test(qs[ci])) { codey = true; break; }
      }
      if (codey) {
        if (rec.kind === 'component') s += 2;
      } else if (rec.kind === 'paper module') {
        s += 2;
      } else if (rec.kind === 'page') {
        s += 1;
      }
      return s;
    }

    function go(url) {
      // A record without a url stringifies to the literal 'undefined' via
      // getAttribute('data-url'); bail rather than navigate to a same-origin 404.
      if (!url || url === 'undefined') return;
      var safe = safeNavigationUrl(url);
      if (safe) window.location.href = safe;
    }

    function paint() {
      var items = list.children;
      for (var i = 0; i < items.length; i++) {
        if (i === active) {
          items[i].classList.add('is-active');
          items[i].scrollIntoView({ block: 'nearest' });
        } else {
          items[i].classList.remove('is-active');
        }
      }
    }

    // Announce the active row to screen readers during arrow navigation. The list
    // is no longer a listbox (no aria-selected / aria-activedescendant), so this
    // polite live-region update is what makes keyboard row-stepping perceivable.
    function announceActive() {
      if (active < 0 || !results[active]) return;
      var rec = results[active];
      var rl = roleLabel(rec.kind);
      announce(kindLabel(rec.kind) + (rl ? ' (' + rl + ')' : '') + ': ' + rec.label + ' (' + (active + 1) + ' of ' + results.length + ')');
    }

    function render() {
      if (!index.length) {
        setEmptyState(
          searchIndexStatus === 'failed'
            ? 'Search index unavailable. Use the docs navigation links instead.'
            : 'Loading search index...'
        );
        return;
      }
      var qs = tokens(input.value.trim());
      if (!qs.length) {
        // Empty state: lead with the sections (pages) so the palette opens as a
        // "jump to" map, then a taste of content, not 8 arbitrary records.
        var pageRecs = index.filter(function (r) { return r.kind === 'page'; });
        var otherRecs = index.filter(function (r) { return r.kind !== 'page'; });
        results = pageRecs.concat(otherRecs).slice(0, 10);
      } else {
        var scored = [];
        for (var i = 0; i < index.length; i++) {
          var sc = score(index[i], qs);
          if (sc >= 0) scored.push([sc, i, index[i]]);
        }
        scored.sort(function (a, b) { return b[0] - a[0] || a[1] - b[1]; });
        results = scored.slice(0, 30).map(function (r) { return r[2]; });
      }
      list.innerHTML = '';
      results.forEach(function (rec) {
        var li = document.createElement('li');
        li.className = 'cmdk__item';
        li.setAttribute('data-url', rec.url);
        var kind = document.createElement('span');
        kind.className = 'cmdk__kind';
        kind.textContent = kindLabel(rec.kind);
        var label = document.createElement('span');
        label.className = 'cmdk__label';
        label.textContent = rec.label;
        // Evidence-rank parity with the map inspector: show the strength signal
        // inline after the title when the record carries it (components only).
        if (typeof rec.evidence_rank === 'number') {
          var rankEl = document.createElement('span');
          rankEl.className = 'cmdk__rank';
          rankEl.textContent = rec.evidence_rank + '/5';
          rankEl.setAttribute('aria-label', 'evidence rank ' + rec.evidence_rank + ' of 5');
          label.appendChild(rankEl);
        }
        var meta = document.createElement('span');
        meta.className = 'cmdk__meta';
        // Scent parity with the map inspector: lead with the one-line statement
        // (what it does), keep the area as context. Previously a component with a
        // family showed only the bare area word and hid its statement entirely.
        // The reader role (explanation vs spec & evidence) leads the line so the
        // component/paper-module split is legible in the result list itself.
        var metaBits = [];
        if (rec.family) metaBits.push(rec.family);
        if (rec.text && rec.text !== rec.family) metaBits.push(rec.text);
        var rl = roleLabel(rec.kind);
        if (rl) {
          var roleSpan = document.createElement('span');
          roleSpan.className = 'cmdk__role';
          roleSpan.textContent = rl;
          meta.appendChild(roleSpan);
        }
        var metaRest = metaBits.join(' · ');
        if (metaRest) meta.appendChild(document.createTextNode((rl ? ' · ' : '') + metaRest));
        li.appendChild(kind);
        li.appendChild(label);
        li.appendChild(meta);
        // Search Actions v2: a local command palette over the object record. Each
        // action is offered only when the record carries the backing data, so there
        // are no dead affordances. Copy is synchronous execCommand (the deploy
        // Permissions-Policy blocks the async Clipboard API); links are same-origin
        // (#map=, evidence anchor) or a real external public source ref.
        // stopPropagation so the row's primary "open" navigation does not also fire.
        var actions = [];
        if (rec.command) {
          var copyBtn = document.createElement('button');
          copyBtn.type = 'button';
          copyBtn.className = 'cmdk__action';
          copyBtn.textContent = 'Copy command';
          copyBtn.setAttribute('data-command', rec.command);
          copyBtn.tabIndex = -1; // mouse/active-row only; keep the Tab trap input->Close
          copyBtn.addEventListener('click', function (ev) {
            ev.stopPropagation();
            var btn = ev.currentTarget;
            flashCopy(btn, copyTextSync(btn.getAttribute('data-command')), 'Copy command');
          });
          actions.push(copyBtn);
        }
        var mapHref = rec.graph_node_id ? safeNavigationUrl('architecture.html#map=' + encodeURIComponent(rec.graph_node_id)) : '';
        if (mapHref) {
          var mapLink = document.createElement('a');
          mapLink.className = 'cmdk__action';
          mapLink.tabIndex = -1;
          mapLink.textContent = 'Show in map';
          mapLink.setAttribute('href', mapHref);
          mapLink.addEventListener('click', function (ev) { ev.stopPropagation(); close(); });
          actions.push(mapLink);
        }
        var evHref = rec.evidence_url ? safeNavigationUrl(rec.evidence_url) : '';
        if (evHref) {
          var evLink = document.createElement('a');
          evLink.className = 'cmdk__action';
          evLink.tabIndex = -1;
          evLink.textContent = 'Open evidence';
          evLink.setAttribute('href', evHref);
          evLink.addEventListener('click', function (ev) { ev.stopPropagation(); close(); });
          actions.push(evLink);
        }
        var srcHref = rec.source_url ? safeExternalUrl(rec.source_url) : '';
        if (srcHref) {
          var srcLink = document.createElement('a');
          srcLink.className = 'cmdk__action';
          srcLink.tabIndex = -1;
          srcLink.textContent = 'Open source';
          srcLink.setAttribute('href', srcHref);
          srcLink.setAttribute('target', '_blank');
          srcLink.setAttribute('rel', 'noopener noreferrer');
          srcLink.addEventListener('click', function (ev) { ev.stopPropagation(); });
          actions.push(srcLink);
        }
        // Carry any result out as a compact, source-bound packet. This is a
        // RESULT packet derived from the loaded search index -- a subset of the
        // canonical object map -- and is labelled as such (packet_schema +
        // derived_from) rather than claiming to be the full object-map record,
        // which arrives once a page loads assets/object-map.js. Sync execCommand
        // copy (the async Clipboard API is blocked by the deploy policy); no fetch.
        var packetBtn = document.createElement('button');
        packetBtn.type = 'button';
        packetBtn.className = 'cmdk__action';
        packetBtn.textContent = 'Copy packet';
        packetBtn.tabIndex = -1;
        packetBtn.addEventListener('click', function (ev) {
          ev.stopPropagation();
          var btn = ev.currentTarget;
          flashCopy(btn, copyTextSync(JSON.stringify(buildResultPacket(rec), null, 2)), 'Copy packet');
        });
        actions.push(packetBtn);
        if (actions.length) {
          var actionRow = document.createElement('div');
          actionRow.className = 'cmdk__actions';
          actions.forEach(function (node) { actionRow.appendChild(node); });
          li.appendChild(actionRow);
        }
        li.addEventListener('click', function () { go(this.getAttribute('data-url')); });
        list.appendChild(li);
      });
      active = results.length ? 0 : -1;
      paint();
      if (emptyEl) {
        if (results.length) {
          emptyEl.setAttribute('hidden', '');
        } else {
          // No results. Make the dead-end directive and query-aware instead of the
          // generic "keep typing" default -- but only ever via textContent (no HTML,
          // so the echoed query can't inject), and restore the build-time default
          // for the query-less case so this stays behaviour, not a copy fork.
          if (emptyDefault == null) emptyDefault = emptyEl.textContent;
          var q = input.value.trim();
          emptyEl.textContent = q
            ? ('No matches for “' + q + '”. Try a component, area, or evidence term.')
            : emptyDefault;
          emptyEl.removeAttribute('hidden');
        }
      }
      if (countEl) {
        if (!results.length) {
          countEl.textContent = '';
        } else if (!input.value.trim()) {
          countEl.textContent = results.length + ' suggestions';
        } else {
          var byKind = {};
          results.forEach(function (r) { var k = kindLabel(r.kind); byKind[k] = (byKind[k] || 0) + 1; });
          var parts = Object.keys(byKind).sort(function (a, b) { return byKind[b] - byKind[a]; })
            .map(function (k) { return byKind[k] + ' ' + k.toLowerCase() + (byKind[k] > 1 ? 's' : ''); });
          countEl.textContent = results.length + ' matches · ' + parts.join(', ');
        }
      }
    }

    function scheduleRender() {
      if (renderFrame) cancelAnimationFrame(renderFrame);
      renderFrame = requestAnimationFrame(function () {
        renderFrame = 0;
        render();
      });
    }

    var returnFocusTo = null;
    function open() {
      returnFocusTo = document.activeElement;
      modal.removeAttribute('hidden');
      document.body.classList.add('cmdk-open');
      for (var i = 0; i < openers.length; i++) openers[i].setAttribute('aria-expanded', 'true');
      input.value = '';
      ensureSearchIndex(render);
      render();
      input.focus();
    }
    function close() {
      modal.setAttribute('hidden', '');
      document.body.classList.remove('cmdk-open');
      for (var i = 0; i < openers.length; i++) openers[i].setAttribute('aria-expanded', 'false');
      // Return focus to whatever opened the dialog (keyboard/SR users were dumped
      // at <body> start before this).
      if (returnFocusTo && returnFocusTo.focus) { returnFocusTo.focus(); }
      returnFocusTo = null;
    }

    // The modal declares aria-modal="true"; keep Tab focus inside it while open.
    modal.addEventListener('keydown', function (ev) {
      if (ev.key !== 'Tab') return;
      var focusable = Array.prototype.filter.call(
        modal.querySelectorAll('a[href], button:not([disabled]), input, [tabindex="0"]'),
        // Keep only elements that are actually in the tab order AND rendered. The
        // selector matches every a[href]/button regardless of tabindex, so exclude
        // the row actions we set to tabindex=-1 (el.tabIndex < 0). getClientRects()
        // is empty for display:none but non-empty for merely scrolled-out or
        // position:fixed controls, so it is a robust visibility test (offsetParent
        // was null for position:fixed and non-null for off-screen-in-overflow).
        function (el) { return el.tabIndex >= 0 && el.getClientRects().length > 0; }
      );
      if (!focusable.length) return;
      var first = focusable[0], last = focusable[focusable.length - 1];
      if (ev.shiftKey && document.activeElement === first) { ev.preventDefault(); last.focus(); }
      else if (!ev.shiftKey && document.activeElement === last) { ev.preventDefault(); first.focus(); }
    });

    for (var o = 0; o < openers.length; o++) openers[o].addEventListener('click', open);
    var closers = modal.querySelectorAll('[data-search-close]');
    for (var c = 0; c < closers.length; c++) closers[c].addEventListener('click', close);

    input.addEventListener('input', function () {
      if (!index.length && searchIndexStatus !== 'loading') ensureSearchIndex(render);
      scheduleRender();
    });
    input.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowDown') { ev.preventDefault(); if (results.length) { active = (active + 1) % results.length; paint(); announceActive(); } }
      else if (ev.key === 'ArrowUp') { ev.preventDefault(); if (results.length) { active = (active - 1 + results.length) % results.length; paint(); announceActive(); } }
      else if (ev.key === 'Enter') { ev.preventDefault(); if (active >= 0 && results[active]) go(results[active].url); }
      else if (ev.key === 'Escape') { ev.preventDefault(); close(); }
    });

    document.addEventListener('keydown', function (ev) {
      if (document.body.classList.contains('cmdk-open')) return;
      var isSlash = ev.key === '/';
      var isCmdK = (ev.metaKey || ev.ctrlKey) && (ev.key === 'k' || ev.key === 'K');
      if (!isSlash && !isCmdK) return;
      var tag = (ev.target && ev.target.tagName) || '';
      if (isSlash && (tag === 'INPUT' || tag === 'TEXTAREA' || (ev.target && ev.target.isContentEditable))) return;
      ev.preventDefault();
      open();
    });
  })();

  // --- Architecture map: neighbour isolation + focus paths ------------------
  // Progressive enhancement over the build-time SVG. With JS off the diagram is
  // a static, readable picture and every component node is still a real link.
  (function graphMap() {
    var fig = document.querySelector('[data-graph]');
    if (!fig) return;
    var svg = fig.querySelector('.gsvg');
    var nodes = [].slice.call(fig.querySelectorAll('.gnode'));
    var edges = [].slice.call(fig.querySelectorAll('.gedge'));
    var focusBtns = [].slice.call(fig.querySelectorAll('[data-graph-focus]'));
    if (!svg || !nodes.length) return;

    var adj = {};
    edges.forEach(function (edge) {
      var s = edge.getAttribute('data-source');
      var t = edge.getAttribute('data-target');
      (adj[s] = adj[s] || {})[t] = 1;
      (adj[t] = adj[t] || {})[s] = 1;
    });

    // Per-node metadata, read straight from the build-time SVG (no network, no
    // second packet): full label from <title>, kind from the gnode-- class,
    // cluster from data-cluster, and the node's own public route from its link.
    var byId = {};
    nodes.forEach(function (n) { byId[n.getAttribute('data-id')] = n; });
    // Bridge graph nodes to their public object record via the search index
    // (records carry graph_node_id). Lazy-loaded only when a component is pinned,
    // so the docs page and landing cover do not pay this parse cost at startup.
    var recByNode = {};
    var graphSearchState = 'idle';
    function indexGraphSearchRecords(recs) {
      for (var i = 0; i < recs.length; i++) {
        if (recs[i] && recs[i].graph_node_id) recByNode[recs[i].graph_node_id] = recs[i];
      }
      if (recs.length) graphSearchState = 'ready';
    }
    var initialGraphRecords = mcSearchIndexRecords();
    if (initialGraphRecords.length) indexGraphSearchRecords(initialGraphRecords);
    function ensureGraphSearchIndex(cb) {
      if (graphSearchState === 'ready') { if (cb) cb(); return; }
      if (graphSearchState !== 'loading') graphSearchState = 'loading';
      withSearchIndex(function (records) {
        records = records || [];
        indexGraphSearchRecords(records);
        if (!records.length) graphSearchState = 'failed';
        if (cb) cb();
      });
    }

    // Rich public-object detail -- the evidence rank and the honest "does not
    // prove" ceiling -- ships as the same same-origin object-map.js the source
    // page already consumes (window.__MICROCOSM_OBJECTS__; CSP script-src 'self',
    // not a fetch). The map page never preloads it, so the landing pays nothing;
    // we lazy-inject on the first pin and upgrade the inspector in place. Keyed by
    // graph_node_id -- the same bridge recByNode uses -- so the join is exact.
    // Degrades silently to the search-index inspector if the packet is absent.
    var objByNode = {};
    var objMapState = 'idle'; // idle | loading | ready | failed
    function indexObjectMap(map) {
      var objs = (map && map.objects) || [];
      for (var i = 0; i < objs.length; i++) {
        if (objs[i] && objs[i].graph_node_id) objByNode[objs[i].graph_node_id] = objs[i];
      }
      objMapState = 'ready';
    }
    if (window.__MICROCOSM_OBJECTS__) indexObjectMap(window.__MICROCOSM_OBJECTS__);
    function ensureObjectMap(cb) {
      if (objMapState === 'ready') { if (cb) cb(); return; }
      if (window.__MICROCOSM_OBJECTS__) { indexObjectMap(window.__MICROCOSM_OBJECTS__); if (cb) cb(); return; }
      function settle() {
        if (window.__MICROCOSM_OBJECTS__) { indexObjectMap(window.__MICROCOSM_OBJECTS__); if (cb) cb(); }
        else { objMapState = 'failed'; }
      }
      var existing = document.querySelector('script[data-object-map]');
      if (existing) {
        existing.addEventListener('load', settle);
        existing.addEventListener('error', function () { objMapState = 'failed'; });
        return;
      }
      objMapState = 'loading';
      var s = document.createElement('script');
      s.src = mcAssetUrl('object-map.js');
      s.setAttribute('data-object-map', '');
      s.addEventListener('load', settle);
      s.addEventListener('error', function () { objMapState = 'failed'; if (window.console && console.warn) console.warn('Microcosm: object-map.js failed to load; map inspector detail omitted.'); });
      document.head.appendChild(s);
    }

    // --- Whole-map salience grammar: bridges, local links, and hubs ----------
    // The build-time SVG draws every declared link at one weight, so the "Whole
    // map" view buries the cards under their own cross-card wiring. Restore the
    // card hierarchy as the first read by classifying each link once, from the
    // in-page geometry: a link whose endpoints sit in different cards is a
    // "bridge" (a quiet background line by default), one inside a single card is
    // "local" (legible but restrained). High-degree nodes become hubs so the few
    // real connectors keep their labels at rest. Hover, focus, and selection (the
    // is-isolating / is-active states) override all of it to reveal a node's full
    // fan. Pure runtime enhancement over the static SVG — no network — so with JS
    // off the diagram stays the readable, all-weight picture it already is.
    // Degree threshold for hub promotion, measured in distinct neighbours (the
    // same adjacency the inspector uses, so reciprocal A<->B links count once).
    // The live graph's distribution has a clean break here: a handful of
    // singleton high-degree connectors sit at >= 8, above a wide shelf at <= 7 —
    // so this promotes the few real hubs, not a quarter of the map.
    var HUB_MIN_DEGREE = 8;
    function clusterOf(id) {
      var n = byId[id];
      return n ? (n.getAttribute('data-cluster') || '') : '';
    }
    var edgesLayer = svg.querySelector('.gedges');
    edges.forEach(function (ed) {
      var sc = clusterOf(ed.getAttribute('data-source'));
      var tc = clusterOf(ed.getAttribute('data-target'));
      // Unknown endpoints (shouldn't happen) stay local so a link is never hidden.
      var bridge = !!(sc && tc && sc !== tc);
      ed.classList.add(bridge ? 'gedge--bridge' : 'gedge--local');
      // Paint bridges first so cross-card wires sit beneath within-card structure
      // (SVG paints in document order; nodes are a later group, so stay on top).
      if (bridge && edgesLayer) edgesLayer.insertBefore(ed, edgesLayer.firstChild);
    });
    nodes.forEach(function (n) {
      var near = adj[n.getAttribute('data-id')];
      if (near && Object.keys(near).length >= HUB_MIN_DEGREE) n.classList.add('is-hub');
    });
    // Opt-in flag: the resting demotion / label LOD only applies once this
    // classification has run, so there is no flash of demotion and the JS-off
    // fallback is exactly the build-time SVG.
    fig.classList.add('has-salience');

    // ── Workbench geometry layer (Wave 33: dock + badge + gutter router) ─────
    // Pure runtime enhancement over the fixed build-time SVG. Reads the 9 cluster
    // rects + every node centre once (positions are build-time-fixed), then docks
    // the inspector, paints a durable active-node badge, and re-routes only the
    // pinned node's cross-card edges through the gutters so they stop slicing card
    // titles. Gated behind .has-workbench, so with scripting off the static SVG is
    // byte-identical to today. No network: geometry is read straight off the SVG.
    var SVGNS = 'http://www.w3.org/2000/svg';
    var TITLE_BAND = 44;        // top strip of each cluster box reserved for its label
    var CLEAR = 6;             // clearance kept off box edges when porting in/out
    var EPS = 0.5;
    var MAX_ROUTE_FACTOR = 2.2; // reject a route longer than 2.2x the straight chord
    var ROUTE_FAN_MAX = 6;      // above this many routable bridges, keep the radial fan
    var LANE_PITCH = 9;         // px offset between parallel routes sharing a corridor
    var TURN_W = 14;            // candidate-scorer penalty per bend
    var ORIENT_W = 90;         // candidate-scorer penalty for skirting an orientation box
    var ORIENT_INFLATE = 14;    // extra clearance applied around orientation boxes

    // Read the nine cluster boxes straight off the SVG (the obstacle set). Each
    // carries a title-band sub-rect (top 44px). Robust to a future builder
    // re-layout: lattice lines are derived from the rects, never hardcoded.
    var boxes = [].slice.call(svg.querySelectorAll('.gcluster__box')).map(function (r) {
      var x = parseFloat(r.getAttribute('x')), y = parseFloat(r.getAttribute('y'));
      var w = parseFloat(r.getAttribute('width')), h = parseFloat(r.getAttribute('height'));
      return { x: x, y: y, w: w, h: h, band: { x: x, y: y, w: w, h: TITLE_BAND }, orientation: false };
    });
    var VB = (svg.getAttribute('viewBox') || '0 0 1152 966').split(/\s+/).map(parseFloat);
    var SCENE = { x: VB[0] || 0, y: VB[1] || 0, w: VB[2] || 1152, h: VB[3] || 966 };

    // Node centre = the dot circle's (cx,cy); the label sits below it.
    var centre = {};
    nodes.forEach(function (n) {
      var dot = n.querySelector('.gnode__dot');
      if (dot) centre[n.getAttribute('data-id')] = {
        x: parseFloat(dot.getAttribute('cx')),
        y: parseFloat(dot.getAttribute('cy'))
      };
    });
    function centreOf(id) { return centre[id] || null; }
    function boxIndexOfPoint(px, py) {
      for (var i = 0; i < boxes.length; i++) {
        var b = boxes[i];
        if (px >= b.x && px <= b.x + b.w && py >= b.y && py <= b.y + b.h) return i;
      }
      return -1;
    }
    function boxOfPoint(px, py) { var i = boxIndexOfPoint(px, py); return i < 0 ? null : boxes[i]; }

    // Lattice lines, derived from the rects (uniform grid => closed-form gutters).
    function uniqSortedInt(vals) {
      var seen = {}, out = [];
      vals.forEach(function (v) { var k = Math.round(v); if (!seen[k]) { seen[k] = 1; out.push(k); } });
      out.sort(function (a, b) { return a - b; });
      return out;
    }
    var colX = uniqSortedInt(boxes.map(function (b) { return b.x; }));
    var rowY = uniqSortedInt(boxes.map(function (b) { return b.y; }));
    var boxW = boxes.length ? boxes[0].w : 364, boxH = boxes.length ? boxes[0].h : 302;
    var vGutterX = [];
    for (var ci = 0; ci < colX.length - 1; ci++) vGutterX.push((colX[ci] + boxW + colX[ci + 1]) / 2);
    var leftMarginX = (SCENE.x + colX[0]) / 2;
    var rightMarginX = (colX[colX.length - 1] + boxW + (SCENE.x + SCENE.w)) / 2;
    var hGutterY = [];
    for (var ri = 0; ri < rowY.length - 1; ri++) hGutterY.push((rowY[ri] + boxH + rowY[ri + 1]) / 2);
    var topMarginY = (SCENE.y + rowY[0]) / 2;
    var botMarginY = (rowY[rowY.length - 1] + boxH + (SCENE.y + SCENE.h)) / 2;
    function colOf(b) { for (var i = 0; i < colX.length; i++) if (Math.abs(b.x - colX[i]) < 1) return i; return -1; }
    function rowOf(b) { for (var i = 0; i < rowY.length; i++) if (Math.abs(b.y - rowY[i]) < 1) return i; return -1; }

    // ---- verifier primitives (the atlasEdgeRouter safety contract) ----------
    // Axis-aligned segment a->b through a rect interior (boundary touch = clear).
    function segHitsRect(ax, ay, bx, by, r) {
      var x0 = r.x, y0 = r.y, x1 = r.x + r.w, y1 = r.y + r.h;
      if (Math.abs(ay - by) < EPS) { // horizontal
        if (ay <= y0 + EPS || ay >= y1 - EPS) return false;
        return Math.max(ax, bx) > x0 + EPS && Math.min(ax, bx) < x1 - EPS;
      }
      if (ax <= x0 + EPS || ax >= x1 - EPS) return false; // vertical
      return Math.max(ay, by) > y0 + EPS && Math.min(ay, by) < y1 - EPS;
    }
    // Any-orientation segment vs rect interior (decides if a STRAIGHT edge needs a
    // route): mirrors atlasEdgeRouter chordCrossesAnyObstacle. Liang-Barsky clip.
    function segCrossesRectAny(ax, ay, bx, by, r) {
      var x0 = r.x + EPS, y0 = r.y + EPS, x1 = r.x + r.w - EPS, y1 = r.y + r.h - EPS;
      var dx = bx - ax, dy = by - ay, t0 = 0, t1 = 1;
      var p = [-dx, dx, -dy, dy], q = [ax - x0, x1 - ax, ay - y0, y1 - ay];
      for (var i = 0; i < 4; i++) {
        if (Math.abs(p[i]) < 1e-9) { if (q[i] < 0) return false; }
        else { var t = q[i] / p[i]; if (p[i] < 0) { if (t > t1) return false; if (t > t0) t0 = t; }
               else { if (t < t0) return false; if (t < t1) t1 = t; } }
      }
      return t0 < t1;
    }
    // Does the straight chord (excluding its two host boxes) cross any box interior
    // or any title band? If not, the straight edge is already clean -> do not route.
    function chordCrossesObstacle(src, tgt, exA, exB) {
      for (var j = 0; j < boxes.length; j++) {
        if (j === exA || j === exB) continue;
        if (segCrossesRectAny(src.x, src.y, tgt.x, tgt.y, boxes[j])) return true;
      }
      // host title bands still count (a chord can clip its own card's title strip)
      for (var k = 0; k < boxes.length; k++) {
        if (segCrossesRectAny(src.x, src.y, tgt.x, tgt.y, boxes[k].band)) return true;
      }
      return false;
    }
    // Safety gate: does an orthogonal polyline cross ANY box interior EXCEPT the two
    // host boxes? The entry/exit stubs legitimately sit inside the endpoints' cards,
    // so exempting them is what makes routing fire at all (the blocker fix). The
    // title band is inside its box, so clearing non-host interiors clears their titles.
    function polylineHitsAnyBoxExcept(pts, exA, exB) {
      for (var i = 0; i < pts.length - 1; i++)
        for (var j = 0; j < boxes.length; j++) {
          if (j === exA || j === exB) continue;
          if (segHitsRect(pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y, boxes[j])) return true;
        }
      return false;
    }
    // An orientation box must never be crossed even when it is a host (component
    // fans steer wide of "Seven areas" / "Shared path primitives"). Inflated test.
    function polylineHitsOrientation(pts) {
      for (var j = 0; j < boxes.length; j++) {
        if (!boxes[j].orientation) continue;
        var b = boxes[j], inf = { x: b.x - ORIENT_INFLATE, y: b.y - ORIENT_INFLATE,
                                  w: b.w + 2 * ORIENT_INFLATE, h: b.h + 2 * ORIENT_INFLATE };
        for (var i = 0; i < pts.length - 1; i++)
          if (segHitsRect(pts[i].x, pts[i].y, pts[i + 1].x, pts[i + 1].y, inf)) return true;
      }
      return false;
    }
    function manhattanLen(pts) {
      var d = 0;
      for (var i = 0; i < pts.length - 1; i++) d += Math.abs(pts[i + 1].x - pts[i].x) + Math.abs(pts[i + 1].y - pts[i].y);
      return d;
    }
    function bendCount(pts) {
      var b = 0;
      for (var i = 1; i < pts.length - 1; i++) {
        var ax = pts[i].x - pts[i - 1].x, ay = pts[i].y - pts[i - 1].y;
        var bx = pts[i + 1].x - pts[i].x, by = pts[i + 1].y - pts[i].y;
        if (Math.abs(ax * by - ay * bx) > EPS) b++;
      }
      return b;
    }
    function orientAdjacency(pts) {
      // count segment midpoints that fall within ORIENT_INFLATE of an orientation box
      var hits = 0;
      for (var j = 0; j < boxes.length; j++) {
        if (!boxes[j].orientation) continue;
        var b = boxes[j];
        for (var i = 0; i < pts.length - 1; i++) {
          var mx = (pts[i].x + pts[i + 1].x) / 2, my = (pts[i].y + pts[i + 1].y) / 2;
          if (mx > b.x - ORIENT_INFLATE && mx < b.x + b.w + ORIENT_INFLATE &&
              my > b.y - ORIENT_INFLATE && my < b.y + b.h + ORIENT_INFLATE) { hits++; break; }
        }
      }
      return hits;
    }
    function simplify(pts) {
      if (pts.length <= 2) return pts.slice();
      var out = [pts[0]];
      for (var i = 1; i < pts.length - 1; i++) {
        var a = out[out.length - 1], b = pts[i], c = pts[i + 1];
        var coincident = Math.abs(a.x - b.x) < EPS && Math.abs(a.y - b.y) < EPS;
        var collinear = (Math.abs(a.x - b.x) < EPS && Math.abs(b.x - c.x) < EPS) ||
                        (Math.abs(a.y - b.y) < EPS && Math.abs(b.y - c.y) < EPS);
        if (!coincident && !collinear) out.push(b);
      }
      out.push(pts[pts.length - 1]);
      return out;
    }
    function pointsToPath(pts, rad) {
      rad = rad || 6;
      if (pts.length < 2) return '';
      if (pts.length === 2) return 'M ' + pts[0].x + ' ' + pts[0].y + ' L ' + pts[1].x + ' ' + pts[1].y;
      function d2(a, b) { return Math.sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y)); }
      function towards(f, t, d) { var L = d2(f, t) || 1; return { x: f.x + (t.x - f.x) / L * d, y: f.y + (t.y - f.y) / L * d }; }
      var out = 'M ' + pts[0].x + ' ' + pts[0].y;
      for (var k = 1; k < pts.length - 1; k++) {
        var p0 = pts[k - 1], p1 = pts[k], p2 = pts[k + 1];
        var rr = Math.min(rad, d2(p0, p1) / 2, d2(p1, p2) / 2);
        var a = towards(p1, p0, rr), b = towards(p1, p2, rr);
        out += ' L ' + a.x + ' ' + a.y + ' Q ' + p1.x + ' ' + p1.y + ' ' + b.x + ' ' + b.y;
      }
      var last = pts[pts.length - 1];
      return out + ' L ' + last.x + ' ' + last.y;
    }

    // Mark the two orientation cluster boxes (row-0 "Seven areas" + "Shared path
    // primitives") so the scorer/inflation steer component fans wide of them. The
    // box is found GEOMETRICALLY from a member node (data-cluster is semantic, not
    // the box). Consumed by orientAdjacency / polylineHitsOrientation below.
    var ORIENTATION_CLUSTERS = { 'cluster:areas': 1, 'cluster:shared_spine': 1, 'shared_path': 1 };
    nodes.forEach(function (n) {
      var dc = n.getAttribute('data-cluster') || '', did = n.getAttribute('data-id') || '';
      if (!ORIENTATION_CLUSTERS[dc] && did !== 'shared_path' && did.indexOf('area:') !== 0 && did.indexOf('primitive:') !== 0) return;
      var c = centreOf(did); if (!c) return;
      var b = boxOfPoint(c.x, c.y); if (b) b.orientation = true;
    });

    fig.classList.add('has-workbench'); // the one gate for the whole wave

    // Operating contract, made visible above the map (a JS-on enhancement). The
    // static figcaption describes the no-JS behaviour -- a click opens a card,
    // which is exactly what happens with scripting off. Now that the pin-first
    // activation below is wired, rewrite it to the contract a visitor actually
    // gets, including how to leave a selection.
    var graphCap = fig.querySelector('.system-map__graphcap');
    if (graphCap) {
      // The landing cover shows only the areas + shared path (no components), so
      // its caption must not promise "every public component"; the docs full map
      // does. Consumer-aware so each surface describes what it actually renders.
      graphCap.textContent = fig.getAttribute('data-graph-consumer') === 'landing'
        ? 'The seven public areas and the shared path they bind to. Hover or select an area or the shared path to read it on the right; open the full map to follow any single component to its evidence and source.'
        : 'An interactive picture of the seven public areas, the shared path, and every public component. Hover a node to preview its links; click to pin it and read its full name and declared links below; double-click (or the panel button) to open its page, the paper-module write-up where one exists, otherwise the component spec. Press Esc, or Whole map, to return to the overview.';
    }

    var KIND_WORD = {
      shared_spine: 'Shared path',
      spine_step: 'Shared-path step',
      area: 'Public area',
      component: 'Component',
      wired_component: 'Component'
    };
    function prettySlug(value) {
      return String(value || '').replace(/^[^:]+:/, '').replace(/_/g, ' ').trim();
    }
    function kindOf(node) {
      var m = (node.getAttribute('class') || '').match(/gnode--(\w+)/);
      return m ? m[1] : '';
    }
    function labelOf(node) {
      if (!node) return '';
      var title = node.querySelector('title');
      if (title && title.textContent) return title.textContent.trim();
      var lab = node.querySelector('.gnode__label');
      return lab ? lab.textContent.trim() : (node.getAttribute('data-id') || '');
    }
    function hrefOf(node) {
      var hit = node.querySelector('.gnode__hit');
      return hit ? graphPageHref(hit.getAttribute('href')) : '';
    }
    function graphPageHref(raw) {
      var value = String(raw || '').trim();
      if (!value) return '';
      if (fig.getAttribute('data-graph-consumer') === 'landing' &&
          !/^(?:https?:|#|\/|mailto:|docs\/)/i.test(value)) {
        return 'docs/' + value;
      }
      return value;
    }

    var lockedSet = null;
    var pinnedId = null;
    var activeGraphState = '';
    var panelState = '';
    var hoverFrame = 0;
    var pendingHoverId = null;

    function clearActiveClasses() {
      fig.classList.remove('is-isolating');
      nodes.forEach(function (n) { n.classList.remove('is-active', 'is-neighbour', 'is-dim'); });
      edges.forEach(function (ed) { ed.classList.remove('is-active', 'is-dim'); });
      hideBadge();
      clearRoutes();
      resetLabels();
    }

    function clearActive() {
      if (activeGraphState === 'clear') return;
      activeGraphState = 'clear';
      clearActiveClasses();
      revealRestingHubs();
    }

    function cancelPendingHover() {
      if (hoverFrame) cancelAnimationFrame(hoverFrame);
      hoverFrame = 0;
      pendingHoverId = null;
    }

    function scheduleHover(id) {
      pendingHoverId = id;
      if (hoverFrame) return;
      hoverFrame = requestAnimationFrame(function () {
        var nextId = pendingHoverId;
        hoverFrame = 0;
        pendingHoverId = null;
        if (nextId) {
          isolate(nextId);
          renderNode(nextId);
        }
      });
    }

    function applyFocus(set) {
      var key = 'focus:' + Object.keys(set).sort().join('|');
      if (activeGraphState === key) return;
      activeGraphState = key;
      clearActiveClasses();
      fig.classList.add('is-isolating');
      nodes.forEach(function (n) {
        if (set[n.getAttribute('data-id')]) n.classList.remove('is-dim');
        else n.classList.add('is-dim');
      });
      edges.forEach(function (ed) {
        var s = ed.getAttribute('data-source');
        var t = ed.getAttribute('data-target');
        if (set[s] && set[t]) ed.classList.remove('is-dim');
        else ed.classList.add('is-dim');
      });
    }

    function isolate(id) {
      var key = 'isolate:' + id;
      if (activeGraphState === key) return;
      activeGraphState = key;
      fig.classList.add('is-isolating');
      var near = adj[id] || {};
      nodes.forEach(function (n) {
        var nid = n.getAttribute('data-id');
        n.classList.remove('is-active', 'is-neighbour', 'is-dim');
        if (nid === id) n.classList.add('is-active');
        else if (near[nid]) n.classList.add('is-neighbour');
        else n.classList.add('is-dim');
      });
      edges.forEach(function (ed) {
        var s = ed.getAttribute('data-source');
        var t = ed.getAttribute('data-target');
        if (s === id || t === id) { ed.classList.add('is-active'); ed.classList.remove('is-dim'); }
        else { ed.classList.add('is-dim'); ed.classList.remove('is-active'); }
      });
      showBadge(id);
      revealFocusLabels(id);
      if (pinnedId === id) routeActiveFan(id); // route only the deliberate pin
    }

    // ── Gutter router (Wave 33) ─────────────────────────────────────────────
    // For a FIXED regular lattice with uniform gutters, a clean orthogonal route is
    // closed-form: leave the source box into a bounding gutter (clamped out of the
    // title band), travel gutter centre-lines (never a card interior, never a
    // title), enter the target box. No heap / no Hanan grid / no A* — O(1) per edge.
    // Safety contract (atlasEdgeRouter): a straight edge is replaced ONLY by a route
    // verified clear of every NON-HOST box (entry/exit stubs legitimately sit inside
    // the endpoints' own cards) and not absurdly long; else the straight line stays,
    // so routing can never make the picture worse. We also (1) only route a chord
    // that actually crosses something, (2) SCORE candidates and pick the cheapest
    // (bends + orientation-skirting), not the first legal one.
    function clampPortX(b, x) { return Math.max(b.x + CLEAR, Math.min(b.x + b.w - CLEAR, x)); }
    function clampPortY(b, y) { return Math.max(b.y + TITLE_BAND + CLEAR, Math.min(b.y + b.h - CLEAR, y)); }

    // Returns the best clean polyline for src->tgt, or null. laneShift offsets the
    // chosen gutter lanes so parallel routes sharing a corridor read as a ribbon.
    function routeGutter(src, tgt, laneShift) {
      laneShift = laneShift || 0;
      var sbi = boxIndexOfPoint(src.x, src.y), tbi = boxIndexOfPoint(tgt.x, tgt.y);
      if (sbi < 0 || tbi < 0 || sbi === tbi) return null;
      var sb = boxes[sbi], tb = boxes[tbi];
      var sCol = colOf(sb), sRow = rowOf(sb), tCol = colOf(tb), tRow = rowOf(tb);

      var vLanes;
      if (sCol === tCol) {
        vLanes = [sCol === 0 ? leftMarginX : vGutterX[sCol - 1],
                  sCol === colX.length - 1 ? rightMarginX : vGutterX[sCol]];
      } else {
        var loC = Math.min(sCol, tCol), hiC = Math.max(sCol, tCol);
        vLanes = [];
        for (var g = loC; g < hiC; g++) vLanes.push(vGutterX[g]);
        var sCx = sb.x + sb.w / 2;
        vLanes.sort(function (a, b) { return Math.abs(a - sCx) - Math.abs(b - sCx); });
      }
      var hLanes;
      if (sRow === tRow) {
        hLanes = [sRow === 0 ? topMarginY : hGutterY[sRow - 1],
                  sRow === rowY.length - 1 ? botMarginY : hGutterY[sRow]];
        // Bias the same-row lane toward the target's vertical offset.
        if (tgt.y < src.y) hLanes.reverse();
      } else {
        var loR = Math.min(sRow, tRow), hiR = Math.max(sRow, tRow);
        hLanes = [];
        for (var h2 = loR; h2 < hiR; h2++) hLanes.push(hGutterY[h2]);
        var sCy = sb.y + sb.h / 2;
        hLanes.sort(function (a, b) { return Math.abs(a - sCy) - Math.abs(b - sCy); });
      }

      var maxLen = MAX_ROUTE_FACTOR * (Math.abs(tgt.x - src.x) + Math.abs(tgt.y - src.y) + 1);
      var sExitX = clampPortX(sb, src.x), sExitY = clampPortY(sb, src.y);
      var tEntX = clampPortX(tb, tgt.x), tEntY = clampPortY(tb, tgt.y);
      var best = null, bestScore = Infinity;

      function consider(poly) {
        poly = simplify(poly);
        if (poly.length < 2) return;
        if (polylineHitsAnyBoxExcept(poly, sbi, tbi)) return;
        if (polylineHitsOrientation(poly)) return;   // wide of orientation cards
        var len = manhattanLen(poly);
        if (len > maxLen) return;
        var score = len + TURN_W * bendCount(poly) + ORIENT_W * orientAdjacency(poly);
        if (score < bestScore) { bestScore = score; best = poly; }
      }

      for (var vi = 0; vi < vLanes.length; vi++) {
        for (var hi = 0; hi < hLanes.length; hi++) {
          var vx = vLanes[vi] + laneShift, hy = hLanes[hi] + laneShift;
          // A — vertical-first
          consider([
            { x: src.x, y: src.y }, { x: src.x, y: sExitY },
            { x: vx, y: sExitY }, { x: vx, y: hy },
            { x: tEntX, y: hy }, { x: tEntX, y: tgt.y }, { x: tgt.x, y: tgt.y }
          ]);
          // B — horizontal-first
          consider([
            { x: src.x, y: src.y }, { x: sExitX, y: src.y },
            { x: sExitX, y: hy }, { x: vx, y: hy },
            { x: vx, y: tEntY }, { x: tgt.x, y: tEntY }, { x: tgt.x, y: tgt.y }
          ]);
        }
      }
      return best;
    }

    // Overlay group inserted before .gnodes so routed paths sit UNDER the dots but
    // over the cluster boxes.
    var routesLayer = document.createElementNS(SVGNS, 'g');
    routesLayer.setAttribute('class', 'groutes');
    routesLayer.setAttribute('aria-hidden', 'true');
    var nodesLayer = svg.querySelector('.gnodes');
    if (nodesLayer && nodesLayer.parentNode) nodesLayer.parentNode.insertBefore(routesLayer, nodesLayer);
    else svg.appendChild(routesLayer);

    function clearRoutes() {
      while (routesLayer.firstChild) routesLayer.removeChild(routesLayer.firstChild);
      edges.forEach(function (ed) { ed.classList.remove('is-routed'); });
    }

    // Re-route the active node's BRIDGE fan, BUT only when it is sparse enough that
    // orthogonal routing reads better than a radial starburst (ROUTE_FAN_MAX). Local
    // edges and the structural spine/binds families are never routed. Parallel edges
    // sharing a (srcBox->tgtBox) corridor are offset by LANE_PITCH so they read as a
    // ribbon, not one fat ambiguous line. Each route passes the host-exempt + length
    // + orientation gates or its straight line stands. O(1) per edge; route-on-pin.
    function routeActiveFan(id) {
      clearRoutes();
      var src = centreOf(id); if (!src) return;
      // 1) collect routable bridge edges for this node
      var cand = [];
      edges.forEach(function (ed) {
        if (!ed.classList.contains('is-active') || !ed.classList.contains('gedge--bridge')) return;
        if (ed.classList.contains('gedge--spine_sequence') || ed.classList.contains('gedge--binds_to_shared_path')) return;
        var s = ed.getAttribute('data-source'), t = ed.getAttribute('data-target');
        var otherId = (s === id) ? t : s;
        var tgt = centreOf(otherId); if (!tgt) return;
        var sbi = boxIndexOfPoint(src.x, src.y), tbi = boxIndexOfPoint(tgt.x, tgt.y);
        if (sbi < 0 || tbi < 0 || sbi === tbi) return; // geometry/semantics disagree -> keep straight
        if (!chordCrossesObstacle(src, tgt, sbi, tbi)) return; // clean diagonal -> keep straight
        cand.push({ ed: ed, s: s, t: t, tgt: tgt, sbi: sbi, tbi: tbi });
      });
      // 2) FAN CAP: a dense hub reads better as a radial fan than as bundles.
      if (cand.length > ROUTE_FAN_MAX) return;
      // 3) group by corridor for lane offsetting
      var byCorridor = {};
      cand.forEach(function (c) {
        var key = c.sbi + '>' + c.tbi;
        (byCorridor[key] = byCorridor[key] || []).push(c);
      });
      Object.keys(byCorridor).forEach(function (key) {
        var group = byCorridor[key], k = group.length;
        group.forEach(function (c, i) {
          var shift = (i - (k - 1) / 2) * LANE_PITCH;
          var poly = routeGutter(src, c.tgt, shift);
          if (!poly && shift !== 0) poly = routeGutter(src, c.tgt, 0); // fall back to centre lane
          if (!poly || poly.length < 2) return;
          if (polylineHitsAnyBoxExcept(poly, c.sbi, c.tbi)) return; // final safety gate
          var path = document.createElementNS(SVGNS, 'path');
          path.setAttribute('class', 'groute');
          path.setAttribute('d', pointsToPath(poly, 7));
          path.setAttribute('data-source', c.s);
          path.setAttribute('data-target', c.t);
          routesLayer.appendChild(path);
          c.ed.classList.add('is-routed'); // CSS hides the straight twin it replaced
        });
      });
    }

    // --- Selected-node inspector (workbench panel) ---------------------------
    // A runtime-built surface so a hovered/pinned node shows its declared links,
    // honest relation semantics, and its own route. Pinning writes a #map=<id>
    // hash so a selection is deep-linkable and survives back/forward — all from
    // the in-page SVG, with no fetch (CSP connect-src 'none' stays intact).
    var REL_NOTE = 'Lines are declared navigation links between public objects, with evidence and scope checked on each object card.';
    var panel = document.createElement('aside');
    panel.className = 'gpanel';
    panel.setAttribute('data-graph-inspector', '');
    // A labelled landmark (not aria-live — the panel updates on hover, which would
    // spam announcements; the focused node carries its own aria-label).
    panel.setAttribute('role', 'region');
    panel.setAttribute('aria-label', 'Selected node details');
    fig.appendChild(panel);

    // Dock the inspector beside the graph with ZERO DOM re-parenting: tag the
    // figure's existing direct children with dock roles + add .is-docked; the
    // two-column layout + scale-preserving graph column is pure CSS (style.css),
    // so tab order, the appended panel, and the SVG are untouched, and JS-off has
    // neither the roles nor the class. The capped graph column gets a keyboard-
    // scroll affordance only when the SVG overflows it (re-checked on resize).
    (function dock() {
      var cap = fig.querySelector('.system-map__graphcap');
      var focus = fig.querySelector('.gfocus');
      var legend = fig.querySelector('.glegend');
      var scroll = fig.querySelector('.gscroll');
      if (cap) cap.setAttribute('data-dock', 'cap');
      if (focus) focus.setAttribute('data-dock', 'focus');
      if (legend) legend.setAttribute('data-dock', 'legend');
      if (scroll) scroll.setAttribute('data-dock', 'scroll');
      panel.setAttribute('data-dock', 'panel');
      fig.classList.add('is-docked');
      if (scroll) {
        var syncScrollAffordance = function () {
          var overflows = (scroll.scrollHeight > scroll.clientHeight + 2) ||
                          (scroll.scrollWidth > scroll.clientWidth + 2);
          if (overflows) {
            scroll.setAttribute('tabindex', '0');
            scroll.setAttribute('aria-label', 'Map, scrollable — use arrow keys');
          } else if (scroll !== document.activeElement) {
            // Never strip the active element's tabindex (would drop focus to body).
            scroll.removeAttribute('tabindex');
            scroll.removeAttribute('aria-label');
          }
        };
        syncScrollAffordance();
        window.addEventListener('resize', syncScrollAffordance, { passive: true });
        // The SVG now scales to fill the column, so the scroll affordance must be
        // re-checked whenever the column itself changes size -- not only on a window
        // resize (the inspector dock, the mobile drawer, or a font reflow can change
        // the track width without one). ResizeObserver catches those element-level
        // changes; the window listener stays as the universal fallback.
        if (typeof ResizeObserver === 'function') {
          try { new ResizeObserver(function () { syncScrollAffordance(); }).observe(scroll); }
          catch (e) {}
        }
      }
    })();

    // The badge is the SPATIAL anchor (full name + relation count, ON the map); the
    // docked inspector is the TEXTUAL record (links, note, actions) — not redundant.
    // Native SVG rect+text (createElementNS; el() builds HTML and would not render
    // here). aria-hidden, because the inspector heading + the announce() on pin name
    // the active node (no double-announce). Placed to dodge the title band, its own
    // node label, and its own incident fan; clamped inside the viewBox.
    var badge = document.createElementNS(SVGNS, 'g');
    badge.setAttribute('class', 'gbadge');
    badge.setAttribute('aria-hidden', 'true');
    var badgeRect = document.createElementNS(SVGNS, 'rect');
    badgeRect.setAttribute('class', 'gbadge__box');
    badgeRect.setAttribute('rx', '6');
    var badgeText = document.createElementNS(SVGNS, 'text');
    badgeText.setAttribute('class', 'gbadge__text');
    badge.appendChild(badgeRect);
    badge.appendChild(badgeText);
    svg.appendChild(badge); // last child -> above the .gnodes group
    function relCount(id) {
      return Object.keys(adj[id] || {}).filter(function (k) { return byId[k]; }).length;
    }
    function hideBadge() { badge.style.display = 'none'; }
    hideBadge();
    function rectsOverlap(ax, ay, aw, ah, bx, by, bw, bh) {
      return ax < bx + bw && ax + aw > bx && ay < by + bh && ay + ah > by;
    }
    function showBadge(id) {
      var c = centreOf(id), node = byId[id];
      if (!c || !node) { hideBadge(); return; }
      var n = relCount(id);
      badgeText.textContent = labelOf(node) + '  ·  ' + n + (n === 1 ? ' link' : ' links');
      badge.style.display = '';
      var bb;
      try { bb = badgeText.getBBox(); } // one layout read per selection (route-on-pin)
      catch (e) { hideBadge(); return; } // not rendered (display:none / detached) -> no badge, don't throw out of activation
      var padX = 8, padY = 5;
      var w = bb.width + padX * 2, h = bb.height + padY * 2;
      var labelGap = 30;          // clear the node's own label (baseline cy+24.9)
      var hostBox = boxOfPoint(c.x, c.y);
      var bx = c.x - w / 2;
      var by = c.y + labelGap;    // below the dot + its label by default

      // If the chip would cover the node's own incident neighbours (straight
      // intra-box edges), flip it above the dot.
      var coversFan = false;
      var near = adj[id] || {};
      for (var nb in near) {
        if (!byId[nb]) continue;
        var nc = centreOf(nb); if (!nc) continue;
        if (rectsOverlap(bx, by, w, h, nc.x - 6, nc.y - 6, 12, 12)) { coversFan = true; break; }
      }
      if ((hostBox && by + h > hostBox.y + hostBox.h - 2) || coversFan) by = c.y - labelGap - h;

      // Never sit on a title band: push clear if it overlaps any box's top strip.
      for (var i = 0; i < boxes.length; i++) {
        var b = boxes[i];
        if (rectsOverlap(bx, by, w, h, b.x, b.y, b.w, TITLE_BAND)) {
          var below = b.y + TITLE_BAND + 2;
          // only push down if that does not shove it off the host bottom
          if (!hostBox || below + h <= hostBox.y + hostBox.h - 2) by = below;
        }
      }
      bx = Math.max(SCENE.x + 2, Math.min(SCENE.x + SCENE.w - w - 2, bx));
      by = Math.max(SCENE.y + 2, Math.min(SCENE.y + SCENE.h - h - 2, by));
      badgeRect.setAttribute('x', bx); badgeRect.setAttribute('y', by);
      badgeRect.setAttribute('width', w); badgeRect.setAttribute('height', h);
      badgeText.setAttribute('x', bx + padX);
      badgeText.setAttribute('y', by + padY + bb.height * 0.78);
    }

    // ── Full-label de-clutter (Wave 34) ──────────────────────────────────────
    // The build-time <text> labels are truncated to ~16 chars; the full name only
    // lived in the badge / inspector / <title>. Swap a label to its FULL name
    // whenever it is actually shown (the focused neighbourhood, a hovered card's
    // members, or the resting hubs), then greedily DEMOTE back to the truncated
    // form the minority that would overlap an already-placed label — so full names
    // appear without re-creating the label hairball the LOD removed. Widths are
    // measured ONCE at init (getComputedTextLength is scale-independent user units,
    // matching the cx/cy space), so each reveal is layout-free.
    var LABEL_DY = 24.9, LABEL_H = 15;
    nodes.forEach(function (n) {
      var t = n.querySelector('.gnode__label'); if (!t) return;
      var ti = n.querySelector('title');
      n.__short = t.textContent;
      n.__full = (ti && ti.textContent) ? ti.textContent.trim() : n.__short;
      t.textContent = n.__full;
      try { n.__fullW = t.getComputedTextLength(); } catch (e) { n.__fullW = n.__full.length * 6.4; }
      t.textContent = n.__short;
      var perChar = n.__full.length ? (n.__fullW / n.__full.length) : 6.4;
      n.__shortW = n.__short.length * perChar;
    });
    function labelRect(n, full) {
      var c = centreOf(n.getAttribute('data-id')); if (!c) return null;
      var w = full ? n.__fullW : n.__shortW;
      return { x: c.x - w / 2, y: c.y + LABEL_DY - 11, w: w, h: LABEL_H, cx: c.x };
    }
    var labelTouched = [];
    function resetLabels() {
      if (!labelTouched) { labelTouched = []; return; }
      labelTouched.forEach(function (n) {
        var t = n.querySelector('.gnode__label');
        if (t) {
          t.textContent = n.__short;
          t.setAttribute('text-anchor', 'middle');
          var c = centreOf(n.getAttribute('data-id')); if (c) t.setAttribute('x', c.x);
        }
        n.classList.remove('is-fulllabel', 'is-labelsuppressed');
      });
      labelTouched = [];
    }
    function rHit(a, b) { return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y; }
    // Reveal full labels for ids (priority order); demote overlappers to short.
    // `avoid` seeds occupied rects (e.g. the active node's badge).
    function declutterLabels(ids, avoid) {
      var placed = (avoid || []).slice();
      ids.forEach(function (id) {
        var n = byId[id]; if (!n || !n.__full) return;
        var t = n.querySelector('.gnode__label'); if (!t) return;
        labelTouched.push(n);
        var fb = labelRect(n, true); if (!fb) return;
        var anchor = 'middle', tx = fb.cx;          // edge-clamp so a long full name
        if (fb.x < SCENE.x + 2) { anchor = 'start'; tx = SCENE.x + 2; fb.x = tx; }            // never spills past the
        else if (fb.x + fb.w > SCENE.x + SCENE.w - 2) { anchor = 'end'; tx = SCENE.x + SCENE.w - 2; fb.x = tx - fb.w; } // viewBox (clipped)
        if (placed.some(function (p) { return rHit(fb, p); })) {
          t.textContent = n.__short; t.setAttribute('text-anchor', 'middle'); t.setAttribute('x', fb.cx);
          n.classList.remove('is-fulllabel');
          var sb = labelRect(n, false); if (sb) placed.push(sb);
        } else {
          t.textContent = n.__full; t.setAttribute('text-anchor', anchor); t.setAttribute('x', tx);
          n.classList.add('is-fulllabel'); placed.push(fb);
        }
      });
    }
    var HUB_IDS = nodes.filter(function (n) { return n.classList.contains('is-hub'); }).map(function (n) { return n.getAttribute('data-id'); });
    function revealRestingHubs() { resetLabels(); declutterLabels(HUB_IDS, []); }
    // Focus reveal: the active node carries the badge, so suppress its own label
    // and reveal its neighbours' full names around it (steering clear of the badge).
    function revealFocusLabels(id) {
      resetLabels();
      var aN = byId[id]; if (aN) { aN.classList.add('is-labelsuppressed'); labelTouched.push(aN); }
      var avoid = [];
      if (badge.style.display !== 'none') avoid.push({ x: +badgeRect.getAttribute('x'), y: +badgeRect.getAttribute('y'), w: +badgeRect.getAttribute('width'), h: +badgeRect.getAttribute('height') });
      declutterLabels(Object.keys(adj[id] || {}).filter(function (nid) { return byId[nid]; }), avoid);
    }

    // A row of pin chips: each opens (pins + inspects) its node, keeping the
    // visitor on the map. Shared by the resting index and reused styling-wise by
    // the per-node neighbour list.
    function chipRow(nodeList) {
      var sorted = nodeList.slice().sort(function (a, b) {
        var la = labelOf(a).toLowerCase(), lb = labelOf(b).toLowerCase();
        return la < lb ? -1 : (la > lb ? 1 : 0);
      });
      var ul = el('ul', 'gpanel__links');
      sorted.forEach(function (n) {
        var nid = n.getAttribute('data-id');
        var li = document.createElement('li');
        var b = el('button', 'gpanel__nbr', labelOf(n));
        b.type = 'button';
        b.addEventListener('click', function () { select(nid, true); });
        wireChip(b, nid);
        li.appendChild(b);
        ul.appendChild(li);
      });
      return ul;
    }

    // ── Bidirectional chip <-> graph highlight (Wave 33) ─────────────────────
    // Hovering/focusing a neighbour chip lifts its node + the connecting edge
    // (straight line OR routed path). Non-committal layer over the pinned isolate
    // state — never moves focus, never mutates the selection or history. Non-colour
    // cue (outline + stroke-weight).
    function edgeElsBetween(aId, bId) {
      var hits = [];
      edges.forEach(function (ed) {
        var s = ed.getAttribute('data-source'), t = ed.getAttribute('data-target');
        if ((s === aId && t === bId) || (s === bId && t === aId)) hits.push(ed);
      });
      [].slice.call(routesLayer.querySelectorAll('.groute')).forEach(function (p) {
        var s = p.getAttribute('data-source'), t = p.getAttribute('data-target');
        if ((s === aId && t === bId) || (s === bId && t === aId)) hits.push(p);
      });
      return hits;
    }
    function activeAnchorId() {
      if (pinnedId && byId[pinnedId]) return pinnedId;
      return activeGraphState.indexOf('isolate:') === 0 ? activeGraphState.slice(8) : '';
    }
    function litClear() {
      nodes.forEach(function (n) { n.classList.remove('is-chiplit'); });
      edges.forEach(function (e) { e.classList.remove('is-chiplit'); });
      [].slice.call(routesLayer.querySelectorAll('.groute')).forEach(function (p) { p.classList.remove('is-chiplit'); });
    }
    function litFor(nid) {
      litClear();
      var n = byId[nid]; if (n) n.classList.add('is-chiplit');
      var anchor = activeAnchorId();
      if (anchor) edgeElsBetween(anchor, nid).forEach(function (e) { e.classList.add('is-chiplit'); });
    }
    function wireChip(btn, nid) {
      btn.setAttribute('data-nbr-id', nid);
      btn.addEventListener('mouseenter', function () { litFor(nid); }, { passive: true });
      btn.addEventListener('mouseleave', litClear, { passive: true });
      btn.addEventListener('focus', function () { litFor(nid); });
      btn.addEventListener('blur', litClear);
    }

    function renderDefault() {
      var key = 'default:' + (pinnedId || '');
      if (panelState === key) return;
      panelState = key;
      panel.classList.remove('is-pinned');
      panel.innerHTML = '';
      // A cold reader lands on a map of mostly unlabelled rings, so the resting
      // panel is a "start here" index, not a passive hint: the operating contract,
      // the handful of hub connectors, and the seven areas as chips that
      // pin-and-inspect on click (keeping the visitor on the map), plus a jump
      // into name search. Hubs/areas are static, so this builds once and the
      // panelState guard keeps every later restore() a no-op.
      panel.appendChild(el('p', 'gpanel__hint',
        'Hover a node to preview its links. Click to pin it and read its full name and declared links here. Press Esc, or Whole map, to clear.'));
      var hubs = nodes.filter(function (n) { return n.classList.contains('is-hub'); });
      if (hubs.length) {
        panel.appendChild(el('p', 'gpanel__links-label', 'Most-connected components (' + hubs.length + ')'));
        panel.appendChild(chipRow(hubs));
      }
      var areas = nodes.filter(function (n) { return kindOf(n) === 'area'; });
      if (areas.length) {
        panel.appendChild(el('p', 'gpanel__links-label', 'Public areas (' + areas.length + ')'));
        panel.appendChild(chipRow(areas));
      }
      var searchOpener = document.querySelector('[data-search-open]');
      if (searchOpener) {
        var actions = el('div', 'gpanel__actions');
        var find = el('button', 'gpanel__share', 'Find a component by name');
        find.type = 'button';
        find.addEventListener('click', function () { searchOpener.click(); });
        actions.appendChild(find);
        panel.appendChild(actions);
      }
    }

    function renderNode(id) {
      var node = byId[id];
      if (!node) return;
      var key = 'node:' + id + ':' + (pinnedId === id ? 'pinned' : 'preview');
      if (panelState === key) return;
      panelState = key;
      panel.classList.toggle('is-pinned', pinnedId === id);
      panel.innerHTML = '';

      var head = el('div', 'gpanel__head');
      head.appendChild(el('span', 'gpanel__kind', KIND_WORD[kindOf(node)] || 'Node'));
      var pinBtn = el('button', 'gpanel__pin', pinnedId === id ? 'Unpin' : 'Pin');
      pinBtn.type = 'button';
      pinBtn.setAttribute('aria-pressed', pinnedId === id ? 'true' : 'false');
      pinBtn.addEventListener('click', function () {
        if (pinnedId === id) { unpin(); } else { select(id, true); }
      });
      head.appendChild(pinBtn);
      panel.appendChild(head);

      panel.appendChild(el('h3', 'gpanel__title', labelOf(node)));
      var where = prettySlug(node.getAttribute('data-cluster'));
      if (where) panel.appendChild(el('p', 'gpanel__where', where));

      // What it does: the one-line job, read from the search index. Component
      // pins lazy-load that index and rerender; structural nodes keep their
      // build-time data-summary, so the landing pays nothing.
      var jobRec = recByNode[id];
      if (!jobRec && pinnedId === id && graphSearchState !== 'failed' && id.indexOf('component:') === 0) {
        ensureGraphSearchIndex(function () {
          if (pinnedId === id && recByNode[id]) { panelState = ''; renderNode(id); }
        });
      }
      // Structural nodes (area, shared path) carry their one-line job as a
      // data-summary on the node itself, so the inspector explains them with no
      // fetch; components keep their richer search-index record.
      var jobText = (jobRec && jobRec.text) ? jobRec.text : node.getAttribute('data-summary');
      if (jobText) panel.appendChild(el('p', 'gpanel__job', jobText));
      var nodeCount = node.getAttribute('data-count');
      if (nodeCount) panel.appendChild(el('p', 'gpanel__count', nodeCount + ' components'));

      // Reader detail from the public object map: the evidence rank and the scope
      // limit -- the same honesty signals the source page shows,
      // surfaced where a reader actually explores. Renders when the object is in;
      // only a pinned node (a deliberate click, never a hover) kicks the lazy load
      // and re-renders itself, so the landing and idle hovers pay nothing.
      var obj = objByNode[id];
      if (obj) {
        var auth = obj.authority || {};
        var ev = auth.evidence || {};
        if (ev && (ev.rank != null || ev.kind)) {
          var erow = el('div', 'gpanel__evidence');
          if (ev.rank != null) erow.appendChild(el('span', 'gpanel__rank', 'Evidence ' + ev.rank + '/5'));
          if (ev.kind) erow.appendChild(el('span', 'gpanel__evkind', ev.kind));
          if (ev.runs_real_tools) erow.appendChild(el('span', 'gpanel__evtool', 'runs real tools'));
          panel.appendChild(erow);
        }
        if (auth.does_not_prove) {
          panel.appendChild(el('p', 'gpanel__links-label', 'Scope limit'));
          panel.appendChild(el('p', 'gpanel__ceiling', auth.does_not_prove));
        }
      } else if (pinnedId === id && objMapState !== 'failed' && id.indexOf('component:') === 0) {
        // Only component nodes resolve to an object record; areas / spine /
        // shared_path never do, so they must not trigger the multi-MB object
        // packet -- this keeps the landing cover from ever fetching it.
        ensureObjectMap(function () {
          if (pinnedId === id && objByNode[id]) { panelState = ''; renderNode(id); }
        });
      }

      var near = Object.keys(adj[id] || {}).filter(function (nid) { return byId[nid]; });
      near.sort(function (a, b) {
        var la = labelOf(byId[a]).toLowerCase(), lb = labelOf(byId[b]).toLowerCase();
        return la < lb ? -1 : (la > lb ? 1 : 0);
      });
      panel.appendChild(el('p', 'gpanel__links-label',
        near.length ? ('Declared links (' + near.length + ')') : 'No declared links'));
      if (near.length) {
        var ul = el('ul', 'gpanel__links');
        near.forEach(function (nid) {
          var li = document.createElement('li');
          var b = el('button', 'gpanel__nbr', labelOf(byId[nid]));
          b.type = 'button';
          b.addEventListener('click', function () { select(nid, true); });
          wireChip(b, nid);
          li.appendChild(b);
          ul.appendChild(li);
        });
        panel.appendChild(ul);
      }

      panel.appendChild(el('p', 'gpanel__note', REL_NOTE));

      var actions = el('div', 'gpanel__actions');
      var rec = recByNode[id];
      var objContent = (obj && obj.content) || {};
      var href = hrefOf(node);
      var primaryHref = href || graphPageHref(objContent.primary_reader_href || (rec && rec.primary_reader_url) || '');
      if (primaryHref) {
        var primaryLabel = /(?:^|\/)paper-module-/.test(primaryHref) ? 'Read paper module' : 'Open component spec';
        var open = el('a', 'gpanel__open', primaryLabel);
        open.setAttribute('href', primaryHref);
        actions.appendChild(open);
      }
      // On a projected consumer (the landing cover) the figure carries the full
      // map destination; offer it carrying the SAME canonical node, so a reader
      // drills from the overview into the docs zoom with the node still selected.
      var fullMapHref = fig.getAttribute('data-graph-full-map-href');
      if (fullMapHref) {
        var openFull = el('a', 'gpanel__open', 'Open in the full map');
        openFull.setAttribute('href', fullMapHref.split('#')[0] + hashFor(id));
        actions.appendChild(openFull);
      }
      var share = el('button', 'gpanel__share', 'Copy link to this view');
      share.type = 'button';
      share.addEventListener('click', function () {
        replaceHashTo(id);
        var ok = copyTextSync(window.location.href);
        share.textContent = ok ? 'Link copied' : 'Press Cmd/Ctrl+C';
        announce(ok ? 'Link to this view copied to clipboard' : 'Copy failed. Press Command or Control C to copy.');
        setTimeout(function () { share.textContent = 'Copy link to this view'; }, 1600);
      });
      actions.appendChild(share);
      // Object actions: when this node resolves to a public object record, let a
      // visitor copy its command, jump to its evidence/source, or carry it out as
      // a result packet -- the same affordances as the search palette, now in the
      // graph. Offered only where the record carries the data (no dead actions).
      if (rec) {
        var componentDetailHref = graphPageHref(
          objContent.component_detail_href || rec.component_detail_url || ''
        );
        if (
          componentDetailHref &&
          safeNavigationUrl(componentDetailHref) &&
          safeNavigationUrl(componentDetailHref) !== safeNavigationUrl(primaryHref)
        ) {
          var detailA = el('a', 'gpanel__act', 'Open component detail');
          detailA.setAttribute('href', componentDetailHref);
          actions.appendChild(detailA);
        }
        if (rec.command) {
          var cmdBtn = el('button', 'gpanel__act', 'Copy command');
          cmdBtn.type = 'button';
          cmdBtn.setAttribute('data-command', rec.command);
          cmdBtn.addEventListener('click', function (ev) {
            ev.stopPropagation();
            flashCopy(cmdBtn, copyTextSync(cmdBtn.getAttribute('data-command')), 'Copy command');
          });
          actions.appendChild(cmdBtn);
        }
        var evHref = rec.evidence_url ? safeNavigationUrl(rec.evidence_url) : '';
        if (evHref) {
          var evA = el('a', 'gpanel__act', 'Open evidence');
          evA.setAttribute('href', evHref);
          actions.appendChild(evA);
        }
        var srcHref = rec.source_url ? safeExternalUrl(rec.source_url) : '';
        if (srcHref) {
          var srcA = el('a', 'gpanel__act', 'Open source');
          srcA.setAttribute('href', srcHref);
          srcA.setAttribute('target', '_blank');
          srcA.setAttribute('rel', 'noopener noreferrer');
          actions.appendChild(srcA);
        }
        var pktBtn = el('button', 'gpanel__act', 'Copy packet');
        pktBtn.type = 'button';
        pktBtn.addEventListener('click', function (ev) {
          ev.stopPropagation();
          flashCopy(pktBtn, copyTextSync(JSON.stringify(buildResultPacket(rec), null, 2)), 'Copy packet');
        });
        actions.appendChild(pktBtn);
      }
      panel.appendChild(actions);
    }

    // --- Reversible selection history ---------------------------------------
    // A map should be a place a visitor can leave the way they came. A
    // user-initiated pin pushes a #map=<id> entry, so browser Back (and Esc, and
    // the Whole-map control) returns to the overview and Forward re-pins.
    // replaceState would deep-link the view but silently swallow that step,
    // stranding the visitor on a selected node. clearHash uses replaceState, not
    // history.back(): a deep-linked first load has no overview entry behind it,
    // so we normalise the current URL rather than risk navigating off the page.
    function hashFor(id) { return '#map=' + encodeURIComponent(id); }
    function pushHash(id) {
      var target = hashFor(id);
      if (window.location.hash === target) return;
      if (window.history && window.history.pushState) window.history.pushState(null, '', target);
      else window.location.hash = target;
    }
    function replaceHashTo(id) {
      var target = hashFor(id);
      if (window.location.hash === target) return;
      if (window.history && window.history.replaceState) window.history.replaceState(null, '', target);
      else window.location.hash = target;
    }
    function clearHash() {
      if (!window.location.hash) return;
      if (window.history && window.history.replaceState) {
        window.history.replaceState(null, '', window.location.pathname + window.location.search);
      } else {
        window.location.hash = '';
      }
    }

    function restore() {
      cancelPendingHover();
      if (pinnedId && byId[pinnedId]) { isolate(pinnedId); renderNode(pinnedId); }
      else if (lockedSet) { applyFocus(lockedSet); renderDefault(); }
      else { clearActive(); renderDefault(); }
    }

    // UI-only state changes (no history mutation): used on popstate, where the
    // history has already moved, so re-pushing would double the entry.
    function showNodeUI(id, scroll) {
      pinnedId = id;
      isolate(id);
      renderNode(id);
      syncTwinCurrent(id);
      announce(labelOf(byId[id]) + ' selected, ' + relCount(id) +
        (relCount(id) === 1 ? ' declared link' : ' declared links'));
      if (scroll && byId[id] && byId[id].scrollIntoView) byId[id].scrollIntoView({ block: 'center' });
    }
    function showOverviewUI() { pinnedId = null; restore(); syncTwinCurrent(''); }

    // Presentation-only preselection (landing cover): populate the panel for a
    // node on first paint without announcing, pushing history, or writing the
    // hash. Only an explicit visitor action does those.
    function presetSelection(id) {
      if (!byId[id]) return;
      pinnedId = id;
      isolate(id);
      renderNode(id);
      syncTwinCurrent(id);
    }

    function select(id, pin) {
      if (!byId[id]) return;
      cancelPendingHover();
      if (pin) pinnedId = id;
      isolate(id);
      renderNode(id);
      if (pin) {
        pushHash(id);
        syncTwinCurrent(id);
        // Gate to pin only (not hover): the region is intentionally not aria-live,
        // so the badge/selection is otherwise silent to AT on a keyboard pin.
        announce(labelOf(byId[id]) + ' pinned, ' + relCount(id) +
          (relCount(id) === 1 ? ' declared link' : ' declared links'));
      }
    }
    function clearToOverview() { cancelPendingHover(); pinnedId = null; clearHash(); restore(); syncTwinCurrent(''); }
    function unpin() { clearToOverview(); }

    nodes.forEach(function (n) {
      var id = n.getAttribute('data-id');
      var linked = !!hrefOf(n);
      // A11y for the focusable SVG group: a linked area/component node already
      // exposes a focusable inner <a> (carrying the node title), so drop the
      // redundant second tab stop on the wrapper; a non-link spine/primitive node
      // stays focusable and gets a button role + an accessible name. focusin/out
      // bubble, so the inspector still fires whichever element receives focus.
      if (linked) {
        n.setAttribute('tabindex', '-1');
      } else {
        n.setAttribute('role', 'button');
        n.setAttribute('aria-label', labelOf(n));
      }
      n.addEventListener('mouseenter', function () { scheduleHover(id); }, { passive: true });
      n.addEventListener('focusin', function () { scheduleHover(id); });
      // Do not restore when focus moves INTO the inspector panel: the dock makes
      // the panel co-visible and invites a Tab into it, and restore() would destroy
      // the preview panel before focus lands (dropping focus to <body>).
      n.addEventListener('focusout', function (ev) {
        if (ev.relatedTarget && panel.contains(ev.relatedTarget)) return;
        restore();
      });
      // One activation grammar for every node: a pointer click pins it and opens
      // the inspector instead of jumping away, so the map is no longer a minefield
      // where some nodes navigate on click and others select. For a linked
      // area/component the native navigation is intercepted and re-offered as the
      // explicit "Open card" panel action (and a deliberate double-click); with JS
      // off the inner <a> still navigates, so the static page is unchanged.
      n.addEventListener('click', function (ev) {
        if (linked) {
          // Keyboard activation of the link (click with detail === 0) keeps its
          // announced role -- Enter opens the card -- while focus alone already
          // previews the node and the panel's Pin button offers a keyboard pin.
          if (ev.detail === 0) return;
          ev.preventDefault();
        }
        select(id, true);
      });
      if (linked) {
        // Power-user path, kept deliberate (not the accidental result of a single
        // press): a double-click opens the component's card.
        n.addEventListener('dblclick', function (ev) {
          ev.preventDefault();
          var href = hrefOf(n);
          if (href) window.location.assign(href);
        });
      } else {
        // Spine/primitive nodes carry no link of their own; Enter/Space pins them.
        n.addEventListener('keydown', function (ev) {
          if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); select(id, true); }
        });
      }
    });
    fig.addEventListener('mouseleave', restore, { passive: true });

    // ── Textual twin as a coequal selector (landing cover) ───────────────────
    // The native area/path list beside the map is the no-JS fallback AND the
    // SVG's promised text equivalent. With JS on, each item selects the SAME
    // canonical node in place instead of navigating, and a visible "current"
    // marker stays in sync across both surfaces. Absent on docs (no twin) -> the
    // wiring is an empty no-op there.
    var twin = document.querySelector('[data-graph-twin]');
    var twinItems = twin ? [].slice.call(twin.querySelectorAll('[data-graph-select]')) : [];
    function syncTwinCurrent(id) {
      twinItems.forEach(function (item) {
        var on = item.getAttribute('data-graph-select') === id;
        item.classList.toggle('is-current', on);
        if (on) item.setAttribute('aria-current', 'true');
        else item.removeAttribute('aria-current');
      });
    }
    twinItems.forEach(function (item) {
      var nid = item.getAttribute('data-graph-select');
      item.addEventListener('click', function (ev) {
        if (!byId[nid]) return;        // no such node -> let the link navigate
        if (ev.detail === 0) return;   // keyboard activation -> follow the link (Enter opens the page)
        ev.preventDefault();
        select(nid, true);
      });
    });

    // ── Cluster-hover local label expansion (Wave 33) ───────────────────────
    // Hovering a cluster box reveals the routine component labels INSIDE just that
    // card (a local LOD lift) without entering the isolate state. Bind each cluster
    // <g> to its member nodes by geometric containment, tag those nodes, and toggle
    // a per-node class on hover. DENSITY-GATED: the densest cards (Import & drift =
    // 20, Formal math = 17) are exactly where Wave-31 LOD matters most, so skip the
    // reveal for boxes over LABEL_REVEAL_MAX members. Suppressed while isolating so a
    // pinned/hovered node's fan always wins. Pointer-only; adds no tab stop.
    var LABEL_REVEAL_MAX = 9;
    var boxMembers = boxes.map(function () { return 0; });
    nodes.forEach(function (n) {
      var c = centreOf(n.getAttribute('data-id')); if (!c) return;
      var idx = boxIndexOfPoint(c.x, c.y);
      if (idx >= 0) { n.setAttribute('data-box-idx', String(idx)); boxMembers[idx]++; }
    });
    [].slice.call(svg.querySelectorAll('.gcluster')).forEach(function (g) {
      var rect = g.querySelector('.gcluster__box'); if (!rect) return;
      var bx = parseFloat(rect.getAttribute('x')), by = parseFloat(rect.getAttribute('y'));
      var idx = -1;
      for (var i = 0; i < boxes.length; i++) { if (Math.abs(boxes[i].x - bx) < 1 && Math.abs(boxes[i].y - by) < 1) { idx = i; break; } }
      if (idx < 0 || boxMembers[idx] > LABEL_REVEAL_MAX) return; // dense cards keep LOD
      g.addEventListener('mouseenter', function () {
        if (fig.classList.contains('is-isolating')) return;
        var members = [];
        nodes.forEach(function (n) { if (n.getAttribute('data-box-idx') === String(idx)) { n.classList.add('is-clusterlabel'); members.push(n.getAttribute('data-id')); } });
        resetLabels();
        declutterLabels(HUB_IDS.concat(members), []); // hubs keep priority, then this card's members
      }, { passive: true });
      g.addEventListener('mouseleave', function () {
        nodes.forEach(function (n) { n.classList.remove('is-clusterlabel'); });
        revealRestingHubs();
      }, { passive: true });
    });

    focusBtns.forEach(function (btn) {
      // Expose the selected focus view to assistive tech, not just via the colour.
      btn.setAttribute('aria-pressed', btn.classList.contains('is-active') ? 'true' : 'false');
      btn.addEventListener('click', function () {
        focusBtns.forEach(function (b) { b.classList.remove('is-active'); b.setAttribute('aria-pressed', 'false'); });
        btn.classList.add('is-active');
        btn.setAttribute('aria-pressed', 'true');
        pinnedId = null; clearHash();
        var ids = (btn.getAttribute('data-nodes') || '').split(/\s+/).filter(Boolean);
        if (!ids.length) { lockedSet = null; clearActive(); renderDefault(); return; }
        var set = {};
        ids.forEach(function (id) { set[id] = 1; });
        lockedSet = set;
        applyFocus(set);
        renderDefault();
      });
    });

    // Deep link + reversible Back/Forward: #map=<node id> pins and reveals a node.
    // popstate (Back/Forward) and hashchange (a manual URL edit, or the no-pushState
    // fallback) both reflect the URL into the UI without re-touching history; the
    // pinnedId guard keeps them idempotent so the two never double-apply.
    function syncFromLocation(scroll) {
      var m = (window.location.hash || '').match(/^#map=(.+)$/);
      var id = m ? decodeURIComponent(m[1]) : '';
      if (id && byId[id]) { if (pinnedId !== id) showNodeUI(id, scroll); }
      else if (pinnedId) { showOverviewUI(); }
    }
    window.addEventListener('popstate', function () { syncFromLocation(false); });
    window.addEventListener('hashchange', function () { syncFromLocation(false); });

    // Escape converges on the overview from anywhere inside the map (the search
    // dialog owns its own Escape and sits outside this figure, so no conflict),
    // joining browser Back, the Whole-map pill, and the panel's Unpin. Return
    // focus to the Whole-map control so keyboard users are not stranded.
    fig.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape' && pinnedId) {
        // Focus a stable, live target BEFORE tearing down the panel: clearToOverview
        // -> renderDefault wipes panel.innerHTML, destroying the Pin button that may
        // currently hold focus. Focus home first (fall back to the figure) so focus
        // never transits <body> and is never stranded if the home control is absent.
        var home = fig.querySelector('[data-graph-focus="all"]');
        if (home && home.focus) { home.focus(); }
        else if (fig.focus) { if (!fig.hasAttribute('tabindex')) fig.setAttribute('tabindex', '-1'); fig.focus(); }
        clearToOverview();
      }
    });

    // ── Wire-list enrichment (Wave 35) ───────────────────────────────────────
    // The build-time .wire-list (the text "Explicit component wiring" index, and
    // the no-JS / mobile fallback for the graph) emits each component + a bare
    // "N declared links" COUNT — no targets, nothing clickable, uninterpretable.
    // Rebuild each row's targets from the in-page graph: the source's actual
    // declared neighbours, each a link to its card (the node's own href), so the
    // text index says what connects to what AND is navigable. Matches the row to
    // its node by display name. Gated by .is-enriched, so with JS off the static
    // count list (the builder's output) is unchanged. The builder emitting these
    // links directly (so JS-off benefits too) is the deferred half.
    (function enrichWireList() {
      var list = document.querySelector('.wire-list'); if (!list) return;
      // Directed out-adjacency (source -> target): this section is "source-declared"
      // wiring and the build-time counts are out-degree, so undirected adj would
      // also pull in inbound links and inflate every count.
      var outAdj = {};
      edges.forEach(function (ed) {
        var s = ed.getAttribute('data-source'), t = ed.getAttribute('data-target');
        (outAdj[s] = outAdj[s] || {})[t] = 1;
      });
      var nameToNode = {};
      nodes.forEach(function (n) { nameToNode[labelOf(n)] = n; });
      function targetLink(node) {
        var href = hrefOf(node), e;
        if (href) { e = document.createElement('a'); e.setAttribute('href', href); }
        else { e = document.createElement('span'); }
        e.className = 'wire-target'; e.textContent = labelOf(node); return e;
      }
      var enriched = 0;
      [].slice.call(list.querySelectorAll('li')).forEach(function (li) {
        var srcEl = li.querySelector('.wire-source'), tgtEl = li.querySelector('.wire-targets');
        if (!srcEl || !tgtEl) return;
        var srcNode = nameToNode[srcEl.textContent.trim()]; if (!srcNode) return;
        var near = Object.keys(outAdj[srcNode.getAttribute('data-id')] || {}).filter(function (nid) { return byId[nid]; });
        near.sort(function (a, b) { var la = labelOf(byId[a]).toLowerCase(), lb = labelOf(byId[b]).toLowerCase(); return la < lb ? -1 : (la > lb ? 1 : 0); });
        // Source name becomes a link to its own card.
        var sHref = hrefOf(srcNode);
        if (sHref) { var sa = document.createElement('a'); sa.className = 'wire-source-link'; sa.setAttribute('href', sHref); sa.textContent = labelOf(srcNode); srcEl.textContent = ''; srcEl.appendChild(sa); }
        // Targets become the actual neighbour card-links.
        tgtEl.textContent = '';
        if (!near.length) { tgtEl.appendChild(document.createTextNode('no declared links')); }
        else near.forEach(function (nid, i) {
          tgtEl.appendChild(targetLink(byId[nid]));
          if (i < near.length - 1) tgtEl.appendChild(document.createTextNode(', '));
        });
        enriched++;
      });
      if (enriched) list.classList.add('is-enriched');
    })();

    renderDefault();
    syncFromLocation(true);
    // Landing cover: with no deep-linked node, preselect the figure's default
    // (the shared-path hub) so the panel is populated on first paint. Pure
    // presentation state -- no announce, no hash, no history. Docs figures carry
    // no default-select attribute, so this is a landing-only no-op there.
    if (!pinnedId) {
      var presetId = fig.getAttribute('data-graph-default-select');
      if (presetId && byId[presetId]) presetSelection(presetId);
    }
    if (!pinnedId) revealRestingHubs(); // resting overview shows full hub names (a deep-link pins instead)
  })();

  // --- Visible object coverage (source page) --------------------------------
  // The honesty control plane, made visible. Lazily loads the generated object
  // map as a same-origin <script> (CSP script-src 'self'; this is not a fetch and
  // does not touch connect-src 'none') and renders the live per-kind coverage from
  // window.__MICROCOSM_OBJECTS__. Degrades to nothing if the packet is absent.
  (function objectCoverage() {
    var statusGrid = document.querySelector('.status-grid');
    if (!statusGrid) return; // only the source page carries the projection-status panel

    function loadObjects(cb) {
      if (window.__MICROCOSM_OBJECTS__) { cb(window.__MICROCOSM_OBJECTS__); return; }
      var existing = document.querySelector('script[data-object-map]');
      if (existing) {
        // The tag may have already finished loading; re-check the global so the
        // callback is not dropped (mirrors the freshly-injected guard below).
        if (window.__MICROCOSM_OBJECTS__) { cb(window.__MICROCOSM_OBJECTS__); return; }
        existing.addEventListener('load', function () { if (window.__MICROCOSM_OBJECTS__) cb(window.__MICROCOSM_OBJECTS__); });
        return;
      }
      var s = document.createElement('script');
      s.src = mcAssetUrl('object-map.js');
      s.setAttribute('data-object-map', '');
      s.addEventListener('load', function () { if (window.__MICROCOSM_OBJECTS__) cb(window.__MICROCOSM_OBJECTS__); });
      // object-map.js is never preloaded, so source.html always hits this fresh
      // inject; without an error handler a 404/blocked/parse failure left 'load'
      // unfired and the coverage panel silently absent with no signal. Keep the
      // degrade-to-nothing UX but make a real failure observable.
      s.addEventListener('error', function () { if (window.console && console.warn) console.warn('Microcosm: object-map.js failed to load; object coverage panel omitted.'); });
      document.head.appendChild(s);
    }

    function render(map) {
      if (!map || !map.coverage || document.querySelector('.obj-coverage')) return;
      var section = el('section', 'obj-coverage');
      section.setAttribute('aria-labelledby', 'object-coverage');
      var h = el('h2', null, 'Public object coverage');
      h.id = 'object-coverage';
      section.appendChild(h);
      section.appendChild(el('p', 'muted',
        'Every public-safe thing on this site is one canonical object with a route or a typed omission. '
        + 'This is the live per-kind coverage from the object map (' + map.object_count + ' objects across '
        + map.coverage.length + ' kinds), generated from the same content graph this page is built from.'));
      // A kind links to its landing page only when all its objects share one
      // internal page (component -> components.html, etc.); area/page/source vary
      // or are external, so those stay plain.
      var pageByKind = {};
      (map.objects || []).forEach(function (o) {
        var r = o.route || '';
        var page = r.indexOf('://') === -1 ? r.split('#')[0] : '';
        if (!page) { if (!(o.kind in pageByKind)) pageByKind[o.kind] = null; return; }
        if (!(o.kind in pageByKind)) pageByKind[o.kind] = page;
        else if (pageByKind[o.kind] !== page) pageByKind[o.kind] = null;
      });
      // Reader-decision layer: nearly every kind is complete on every binding that
      // applies, so leading with the raw matrix buries the only signal -- the
      // exceptions. Compute complete-vs-exception and show that first; the full
      // per-kind matrix drops into an audit drawer below.
      var BINDINGS = [
        { key: 'routeable', label: 'route' }, { key: 'searchable', label: 'search' },
        { key: 'graph_linked', label: 'map' }, { key: 'source_linked', label: 'source' },
        { key: 'evidence_linked', label: 'evidence' }, { key: 'command_linked', label: 'command' }
      ];
      var completeKinds = [], exceptions = [];
      map.coverage.forEach(function (row) {
        var total = row.object_count || 0, partials = [];
        BINDINGS.forEach(function (b) {
          var v = row[b.key];
          // 0 (or a missing key) means the binding does not apply to this kind -- the
          // matrix shows a dash, not a zero -- so it is not a coverage exception. Only
          // partial coverage (some but not all objects bound) is.
          if (typeof v !== 'number' || v === 0 || v === total) return;
          partials.push(b.label + ' ' + v + '/' + total);
        });
        var omitted = (typeof row.omitted === 'number' && row.omitted > 0) ? row.omitted : 0;
        if (partials.length || omitted) {
          exceptions.push({ kind: row.kind, total: total, partials: partials, omitted: omitted });
        } else { completeKinds.push(row.kind); }
      });
      var cap1 = function (s) { return s.charAt(0).toUpperCase() + s.slice(1); };
      var summary = el('div', 'obj-coverage__summary');
      var lead = el('p', 'obj-coverage__lead');
      lead.appendChild(el('strong', null, String(completeKinds.length)));
      lead.appendChild(document.createTextNode(' of ' + map.coverage.length
        + ' kinds are fully covered — every binding that applies (route, search, map, source, evidence, command) reaches all of the kind’s objects.'));
      summary.appendChild(lead);
      if (exceptions.length) {
        summary.appendChild(el('p', 'obj-coverage__exhead',
          exceptions.length === 1 ? 'The one exception:' : ('The ' + exceptions.length + ' exceptions:')));
        var exdl = el('dl', 'obj-coverage__exceptions');
        exceptions.forEach(function (ex) {
          var parts = [];
          ex.partials.forEach(function (p) { parts.push(cap1(p)); });
          if (ex.omitted) parts.push('Omitted ' + ex.omitted + '/' + ex.total);
          var rowEl = document.createElement('div');
          rowEl.appendChild(el('dt', null, ex.kind));
          rowEl.appendChild(el('dd', null, parts.join('; ') + '.'));
          exdl.appendChild(rowEl);
        });
        summary.appendChild(exdl);
      }
      section.appendChild(summary);
      // Factored as a matrix, not repeated prose: the metric word lives once in the
      // column header, so each row carries only its kind and the bare counts. Total
      // is the object count; each remaining column is how many of those objects carry
      // that binding, with an em dash where the binding does not apply to the kind.
      var COLS = [
        { key: 'object_count', label: 'Total', always: true },
        { key: 'routeable', label: 'Routed' },
        { key: 'searchable', label: 'Search' },
        { key: 'graph_linked', label: 'Map' },
        { key: 'source_linked', label: 'Source' },
        { key: 'evidence_linked', label: 'Evidence' },
        { key: 'command_linked', label: 'Command' },
        { key: 'omitted', label: 'Omitted' }
      ];
      var table = el('table', 'obj-coverage__table');
      table.appendChild(el('caption', 'obj-coverage__caption',
        'Per-kind coverage. Total is the object count; each other column counts how many of '
        + 'those objects carry that public binding. A dash means the binding does not apply to the kind.'));
      var thead = document.createElement('thead');
      var htr = document.createElement('tr');
      var kh = el('th', 'obj-coverage__kind-head', 'Kind');
      kh.setAttribute('scope', 'col');
      htr.appendChild(kh);
      COLS.forEach(function (c) {
        var th = el('th', 'obj-coverage__num-head', c.label);
        th.setAttribute('scope', 'col');
        htr.appendChild(th);
      });
      thead.appendChild(htr);
      table.appendChild(thead);
      var tbody = document.createElement('tbody');
      map.coverage.forEach(function (row) {
        var tr = document.createElement('tr');
        var kth = document.createElement('th');
        kth.setAttribute('scope', 'row');
        kth.className = 'obj-coverage__kind-cell';
        var page = pageByKind[row.kind];
        if (page) {
          var ka = el('a', 'obj-coverage__kind', row.kind);
          ka.setAttribute('href', page);
          kth.appendChild(ka);
        } else {
          kth.appendChild(el('span', 'obj-coverage__kind', row.kind));
        }
        tr.appendChild(kth);
        COLS.forEach(function (c) {
          var v = row[c.key];
          var has = c.always || (typeof v === 'number' && v > 0);
          var td = el('td', has ? 'obj-coverage__num' : 'obj-coverage__num obj-coverage__num--na',
            has ? String(typeof v === 'number' ? v : 0) : '—');
          td.setAttribute('data-label', c.label);
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
      var audit = el('details', 'obj-coverage__audit');
      audit.appendChild(el('summary', 'obj-coverage__audit-toggle', 'Full per-kind matrix'));
      audit.appendChild(table);
      section.appendChild(audit);
      if (map.omission_reasons && map.omission_reasons.length) {
        // Omission reasons arrive as raw snake_case tokens; humanise to readable
        // prose for the public surface (underscores become spaces — same words,
        // nothing invented). Spaces also give the long reason natural wrap points
        // so it no longer overflows. Raw tokens kept in data-raw for provenance.
        var reasonProse = map.omission_reasons.map(function (r) {
          return String(r || '').replace(/_/g, ' ').trim();
        }).join('; ');
        var omitP = el('p', 'muted', 'Typed omissions: ' + reasonProse + '.');
        omitP.setAttribute('data-raw', map.omission_reasons.join(', '));
        section.appendChild(omitP);
      }
      section.appendChild(el('p', 'muted',
        'Coverage counts what is projected and wired into the site, not what is important or proven. '
        + 'It is an honesty ledger: a high count means an object is reachable and source-bound, not that it is correct.'));
      // Surface the agent-readable doorway (otherwise unlinked from the human site).
      var agent = el('p', 'muted');
      agent.appendChild(document.createTextNode('Machine-readable: '));
      var llms = el('a', null, 'llms.txt');
      llms.setAttribute('href', '../llms.txt');
      agent.appendChild(llms);
      agent.appendChild(document.createTextNode(' (the agent doorway) and '));
      var omj = el('a', null, 'object-map.json');
      omj.setAttribute('href', '../object-map.json');
      agent.appendChild(omj);
      agent.appendChild(document.createTextNode(' (every object, its route, source, and coverage) are generated for agents and humans alike -- no scraping, no API.'));
      section.appendChild(agent);
      statusGrid.parentNode.insertBefore(section, statusGrid.nextSibling);
    }

    loadObjects(render);
  })();

  // --- Public-label firewall: strip the batch-number prefix from card subtitles -
  // A few paper-module subtitles ship in the generated HTML as "Set N <name>",
  // leaking the internal authoring batch number into the public card. The builder
  // already strips that prefix for the primary component name (span.name keeps
  // e.g. "Market Dashboard Read-Model Bundle" with no "Set 12"), so the subtitle
  // is the lone surface still showing it. Normalise conservatively: remove only an
  // unambiguous leading "Set <number>" batch token and keep every remaining word
  // verbatim, so the subtitle reads as the component's own canonical name. The raw
  // label is preserved in data-raw for provenance. (The trailing "Bundle" word is
  // the builder's canonical name, not scaffolding to remove here — see backlog.)
  (function stripBatchPrefixFromCardSubtitles() {
    var SET_PREFIX = /^Set\s+\d+\s+(\S.*)$/;
    var titles = document.querySelectorAll('.comp-card__pm-title');
    Array.prototype.forEach.call(titles, function (node) {
      if (node.hasAttribute('data-raw')) return; // idempotent: never double-strip
      var raw = node.textContent.trim();
      var m = SET_PREFIX.exec(raw);
      if (!m) return;
      var clean = m[1].trim();
      if (!clean) return; // never blank a title
      node.setAttribute('data-raw', raw);
      node.textContent = clean;
    });
  })();

  // Architecture-atlas carousel: turns the static view cards into a swipeable,
  // click-through carousel (prev/next + dots on desktop, native swipe on touch).
  // No-JS fallback: the track is a scroll-snap container, so it still scrolls.
  (function initAtlasCarousel() {
    var atlas = document.querySelector('[data-atlas]');
    if (!atlas) return;
    var track = atlas.querySelector('[data-atlas-track]');
    if (!track) return;
    var slides = Array.prototype.slice.call(track.children);
    if (slides.length < 2) return;
    var prev = atlas.querySelector('[data-atlas-prev]');
    var next = atlas.querySelector('[data-atlas-next]');
    var dotsWrap = atlas.querySelector('[data-atlas-dots]');
    var statusEl = atlas.querySelector('[data-atlas-status]');
    function prefersReduced() {
      return !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    }
    function slideName(i) {
      var t = slides[i] && slides[i].querySelector('.video-card__tag');
      return t ? t.textContent.trim() : '';
    }

    function setActive(i) {
      dots.forEach(function (d, j) { d.setAttribute('aria-current', j === i ? 'true' : 'false'); });
      if (prev) prev.disabled = i <= 0;
      if (next) next.disabled = i >= slides.length - 1;
      if (statusEl) {
        // "3 of 8 · Code map" -- a named position readout. Once the view count
        // grows past a few, bare dots stop being a usable discovery control; this
        // line tells you where you are and what you are looking at, and (aria-live)
        // announces the change to assistive tech.
        var name = slideName(i);
        statusEl.textContent = (i + 1) + ' of ' + slides.length + (name ? ' · ' + name : '');
      }
    }
    function scrollToSlide(i) {
      var s = slides[i];
      var target = s.offsetLeft - (track.clientWidth - s.clientWidth) / 2;
      // Honour prefers-reduced-motion: the JS scrollTo API is not governed by the
      // CSS scroll-behavior reset, so gate the smooth animation explicitly.
      track.scrollTo({ left: Math.max(0, target), behavior: prefersReduced() ? 'auto' : 'smooth' });
      setActive(i);
    }
    function activeIndex() {
      var center = track.scrollLeft + track.clientWidth / 2;
      var best = 0, bestDist = Infinity;
      slides.forEach(function (s, i) {
        var d = Math.abs((s.offsetLeft + s.clientWidth / 2) - center);
        if (d < bestDist) { bestDist = d; best = i; }
      });
      return best;
    }
    var dots = slides.map(function (s, i) {
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'atlas__dot';
      b.setAttribute('aria-label', 'Go to view ' + (i + 1));
      b.addEventListener('click', function () { scrollToSlide(i); });
      if (dotsWrap) dotsWrap.appendChild(b);
      return b;
    });
    function update() { setActive(activeIndex()); }
    function go(dir) { scrollToSlide(Math.max(0, Math.min(slides.length - 1, activeIndex() + dir))); }
    if (prev) prev.addEventListener('click', function () { go(-1); });
    if (next) next.addEventListener('click', function () { go(1); });
    // The track is a focusable region (tabindex=0): let arrow keys page through
    // the views, so keyboard users are not limited to dragging the scrollbar.
    track.addEventListener('keydown', function (ev) {
      if (ev.key === 'ArrowLeft' || ev.key === 'Left') { ev.preventDefault(); go(-1); }
      else if (ev.key === 'ArrowRight' || ev.key === 'Right') { ev.preventDefault(); go(1); }
    });
    var raf = 0;
    track.addEventListener('scroll', function () {
      if (raf) return;
      raf = window.requestAnimationFrame(function () { raf = 0; update(); });
    }, { passive: true });
    window.addEventListener('resize', update);
    update();
  })();

  // ---- Governed term layer: hover/focus preview + nonmodal lens ----
  // Progressive enhancement over the build-compiled term links: JS-off leaves a
  // real glossary anchor; JS-on adds a hover preview + nonmodal lens (Back/Esc
  // close, focus returns). Reads window.__MICROCOSM_INDEX__.terms (one source).
  (function () {
    var idx = window.__MICROCOSM_INDEX__ || {};
    var terms = (idx && idx.terms) || [];
    if (!terms.length) return;
    var anchors = document.querySelectorAll('a.narrative-ref--term[data-term]');
    if (!anchors.length) return;

    var byId = {};
    for (var i = 0; i < terms.length; i++) {
      var record = terms[i];
      var key = String((record && record.object_id) || '').replace(/^term:/, '');
      if (key) byId[key] = record;
    }

    // Reuses the module-scope el(tag, cls, text) helper (single-sourced).
    function placeFloater(node, anchor) {
      node.hidden = false;
      var rect = anchor.getBoundingClientRect();
      var width = node.offsetWidth;
      var height = node.offsetHeight;
      var left = Math.min(Math.max(8, rect.left), Math.max(8, window.innerWidth - width - 8));
      var top = rect.bottom + 8;
      if (top + height > window.innerHeight - 8) {
        top = Math.max(8, rect.top - height - 8);
      }
      node.style.left = left + 'px';
      node.style.top = top + 'px';
    }

    // One shared two-tier preview (WCAG 1.4.13: dismissible, hoverable, persistent).
    // Tier 0 is a one- or two-sentence hover preview; tier 1 expands it short->long
    // in place and offers a link through to the full glossary entry. The "real full"
    // (related terms, example route, usage counts) lives on the glossary page, so the
    // inline preview stays deliberately small.
    var tip = el('div', 'term-tip');
    tip.id = 'mc-term-tip';
    tip.setAttribute('role', 'tooltip');
    tip.hidden = true;
    var tipLabel = el('div', 'term-tip__label');
    var tipText = el('div', 'term-tip__text');
    var tipDeep = el('div', 'term-tip__deep');
    tipDeep.hidden = true;
    var tipFull = el('a', 'term-tip__full', 'See this in the glossary ->');
    tipFull.hidden = true;
    tipFull.tabIndex = -1; // the term remains the keyboard path; this is a pointer affordance
    var tipCue = el('div', 'term-tip__cue');
    tip.appendChild(tipLabel);
    tip.appendChild(tipText);
    tip.appendChild(tipDeep);
    tip.appendChild(tipFull);
    tip.appendChild(tipCue);
    document.body.appendChild(tip);
    var tipFor = null;     // the term anchor the preview currently describes
    var tier = 0;          // 0 = short hover preview, 1 = expanded short->long
    var tipHideTimer = 0;

    function renderTier(data, anchor) {
      tipLabel.textContent = data.preferred_label || data.label || '';
      if (tier === 1) {
        tip.classList.add('is-expanded');
        tipText.textContent = data.reader_card || data.reader_preview || data.text || '';
        if (data.reader_deep && data.reader_deep !== data.reader_card) {
          tipDeep.textContent = data.reader_deep; tipDeep.hidden = false;
        } else { tipDeep.hidden = true; }
        var href = anchor.getAttribute('href');
        if (href && safeNavigationUrl(href)) { tipFull.href = href; tipFull.hidden = false; }
        else { tipFull.hidden = true; }
        tipCue.textContent = 'Click again to open the glossary entry';
      } else {
        tip.classList.remove('is-expanded');
        tipText.textContent = data.reader_preview || data.text || data.reader_card || '';
        tipDeep.hidden = true;
        tipFull.hidden = true;
        tipCue.textContent = 'Click to expand here and stay on this page';
      }
    }
    function showTip(anchor) {
      var data = byId[anchor.getAttribute('data-term')];
      if (!data) return;
      if (tipHideTimer) { clearTimeout(tipHideTimer); tipHideTimer = 0; }
      if (tipFor !== anchor) tier = 0; // a different term always starts collapsed
      tipFor = anchor;
      anchor.setAttribute('aria-describedby', tip.id);
      renderTier(data, anchor);
      placeFloater(tip, anchor);
    }
    function expandTip(anchor) {
      var data = byId[anchor.getAttribute('data-term')];
      if (!data) return;
      if (tipHideTimer) { clearTimeout(tipHideTimer); tipHideTimer = 0; }
      tier = 1;
      tipFor = anchor;
      anchor.setAttribute('aria-describedby', tip.id);
      renderTier(data, anchor);
      placeFloater(tip, anchor); // reposition: the card grew
    }
    function hideTip() {
      tip.hidden = true;
      tier = 0;
      if (tipFor) { tipFor.removeAttribute('aria-describedby'); tipFor = null; }
    }
    function scheduleHideTip() {
      if (tipHideTimer) clearTimeout(tipHideTimer);
      tipHideTimer = setTimeout(hideTip, 160); // grace so the pointer can land on the tip
    }
    tip.addEventListener('mouseenter', function () {
      if (tipHideTimer) { clearTimeout(tipHideTimer); tipHideTimer = 0; }
    });
    tip.addEventListener('mouseleave', scheduleHideTip);

    // Escape dismisses the preview; the term anchor itself is the only control.
    document.addEventListener('keydown', function (ev) {
      if ((ev.key === 'Escape' || ev.key === 'Esc') && !tip.hidden) hideTip();
    });
    // A click outside the preview (and off the active term) dismisses it. Clicks
    // inside the preview (the glossary link) pass straight through to navigate.
    document.addEventListener('click', function (ev) {
      if (tip.hidden) return;
      if (tip.contains(ev.target)) return;
      var onTerm = ev.target.closest ? ev.target.closest('a.narrative-ref--term') : null;
      if (onTerm === tipFor) return;
      hideTip();
    });
    window.addEventListener('resize', function () {
      if (!tip.hidden && tipFor) placeFloater(tip, tipFor);
    });

    for (var k = 0; k < anchors.length; k++) {
      (function (anchor) {
        anchor.addEventListener('mouseenter', function () { showTip(anchor); });
        anchor.addEventListener('mouseleave', scheduleHideTip);
        anchor.addEventListener('focus', function () { showTip(anchor); });
        anchor.addEventListener('blur', scheduleHideTip);
        anchor.addEventListener('click', function (ev) {
          // Modified / non-primary clicks (and no-JS) keep the native link straight
          // to the glossary entry. Otherwise the first activation expands the preview
          // short->long; the second falls through to the native href -> full entry.
          if (ev.button !== 0 || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
          if (tipFor !== anchor || tier === 0) {
            ev.preventDefault();
            expandTip(anchor);
          }
        });
      })(anchors[k]);
    }
  })();

})();

/* ===== Open Questions essay (docs/open-questions.html) ===== */
/* Progressive enhancement only. Native <details> already gives per-item
   disclosure, and deep links to individual paragraphs work without this.
   This adds scoped bulk controls and ancestor-opening for deep links. */
(function(){
  "use strict";
  if (!document.querySelector(".oq-list")) return;
  var parents = Array.prototype.slice.call(document.querySelectorAll(".oq-q"));

  /* ---- Page-level: staged expand. Questions -> all evidence -> collapse ----
     Stage 1 opens the five questions (first layer). Stage 2 also opens every
     evidence line (to the floor). Stage 3 collapses everything. ---- */
  var head = document.querySelector(".oq-fivehead");
  var allFacets = Array.prototype.slice.call(document.querySelectorAll(".oq-facet"));
  if (head && parents.length){
    var allBtn = document.createElement("button");
    allBtn.className = "oq-btn";
    allBtn.type = "button";
    var stage = function(){
      if (parents.some(function(d){ return !d.open; })) return "questions";
      if (allFacets.some(function(d){ return !d.open; })) return "evidence";
      return "collapse";
    };
    var syncAll = function(){
      var s = stage();
      allBtn.textContent = s === "questions" ? "Open all questions"
                         : s === "evidence"  ? "Open all evidence too"
                         : "Collapse all";
      allBtn.setAttribute("aria-expanded", s === "questions" ? "false" : "true");
    };
    allBtn.addEventListener("click", function(){
      var s = stage();
      if (s === "questions"){ parents.forEach(function(d){ d.open = true; }); }
      else if (s === "evidence"){ allFacets.forEach(function(d){ d.open = true; }); }
      else { allFacets.forEach(function(d){ d.open = false; }); parents.forEach(function(d){ d.open = false; }); }
      syncAll();
    });
    parents.forEach(function(d){ d.addEventListener("toggle", syncAll); });
    allFacets.forEach(function(d){ d.addEventListener("toggle", syncAll); });
    var hint = head.querySelector(".oq-fivehead__hint");
    head.insertBefore(allBtn, hint);
    syncAll();
  }

  /* ---- Per-question: expand / collapse all of THIS question's evidence ---- */
  parents.forEach(function(parent){
    var body = parent.querySelector(".oq-q__body");
    var facets = Array.prototype.slice.call(parent.querySelectorAll(".oq-facet"));
    if (!body || !facets.length) return;
    var controls = document.createElement("div");
    controls.className = "oq-q__controls";
    var btn = document.createElement("button");
    btn.className = "oq-mini";
    btn.type = "button";
    btn.setAttribute("aria-expanded","false");
    btn.textContent = "Expand all evidence";
    var sync = function(){
      var anyClosed = facets.some(function(d){ return !d.open; });
      btn.textContent = anyClosed ? "Expand all evidence" : "Collapse evidence";
      btn.setAttribute("aria-expanded", anyClosed ? "false" : "true");
    };
    btn.addEventListener("click", function(){
      var anyClosed = facets.some(function(d){ return !d.open; });
      facets.forEach(function(d){ d.open = anyClosed; });
      sync();
    });
    facets.forEach(function(d){ d.addEventListener("toggle", sync); });
    controls.appendChild(btn);
    body.insertBefore(controls, body.firstChild);
  });

  /* ---- Deep links: open every ancestor <details> of the target ---- */
  var openAncestors = function(el){
    var node = el;
    while (node && node !== document.body){
      if (node.tagName === "DETAILS" && !node.open) node.open = true;
      node = node.parentNode;
    }
  };
  var revealHash = function(){
    if (!location.hash) return;
    var target;
    try { target = document.querySelector(location.hash); } catch(e){ return; }
    if (!target) return;
    openAncestors(target);
    window.requestAnimationFrame(function(){ target.scrollIntoView({block:"start"}); });
  };
  window.addEventListener("hashchange", revealHash);
  revealHash();
})();
