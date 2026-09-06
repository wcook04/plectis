/* Plectis landing runtime scheduler.
   The landing is useful as plain HTML. Its shared docs controls and living
   field are progressive enhancements, so download their bytes at low priority
   but do not let both runtimes compile inside the first rendering task.

   Startup contract:
   - docs.js activates in the first idle slot after the first paint;
   - real intent activates docs.js immediately and preserves a first-click
     navigation trail even if the shared runtime has not executed yet;
   - art.js activates only after docs.js settles, then keeps its own low-power
     and reduced-motion gates. A reader who has asked for reduced motion or for
     data saving never downloads it at all: art.js would return on its own first
     line, so spending the bytes to learn that is the wrong answer to a stated
     preference;
   - native links, downloads, disclosure controls, and the CSS field remain the
     no-JS/failure fallback. */
(function () {
  'use strict';

  var doc = document;
  var root = doc.documentElement;
  if (!doc.querySelectorAll || !doc.createElement || !doc.body) return;

  var refs = {};
  var states = { docs: 'staged', art: 'staged' };
  var callbacks = { docs: [], art: [] };
  var templates = doc.querySelectorAll('template[data-plectis-runtime]');
  var i;

  function prefersReducedMotion() {
    try {
      return !!(window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    } catch (e) { return false; }
  }

  /* The two gates that are a reader's stated preference rather than a device
     guess. art.js owns the full gate — device memory, core count — and a
     mismatch here only ever costs or saves its 20KB, never correctness. */
  function fieldWanted() {
    if (prefersReducedMotion()) return false;
    try {
      if (navigator.connection && navigator.connection.saveData) return false;
    } catch (e) {}
    return true;
  }

  for (i = 0; i < templates.length; i += 1) {
    var name = templates[i].getAttribute('data-plectis-runtime');
    var ref = templates[i].content && templates[i].content.querySelector('script[src]');
    if (name && ref) refs[name] = ref.getAttribute('src');
  }
  if (!refs.docs) return;

  function mark(name, state) {
    states[name] = state;
    root.setAttribute('data-plectis-' + name + '-runtime', state);
  }

  function addPreload(name) {
    if (!refs[name]) return;
    var link = doc.createElement('link');
    link.rel = 'preload';
    link.as = 'script';
    link.href = refs[name];
    try { link.fetchPriority = 'low'; } catch (e) {}
    doc.head.appendChild(link);
  }

  function flush(name) {
    var queued = callbacks[name].slice();
    callbacks[name] = [];
    queued.forEach(function (cb) {
      try { cb(states[name]); } catch (e) {}
    });
  }

  function activate(name, callback) {
    if (callback) callbacks[name].push(callback);
    if (!refs[name]) {
      mark(name, 'failed');
      flush(name);
      return;
    }
    if (states[name] === 'ready' || states[name] === 'failed' ||
        states[name] === 'skipped') {
      flush(name);
      return;
    }
    if (states[name] === 'loading') return;

    mark(name, 'loading');
    var script = doc.createElement('script');
    script.src = refs[name];
    script.async = true;
    try { script.fetchPriority = 'low'; } catch (e) {}
    script.setAttribute('data-plectis-runtime-active', name);
    script.addEventListener('load', function () {
      mark(name, 'ready');
      flush(name);
    }, { once: true });
    script.addEventListener('error', function () {
      mark(name, 'failed');
      flush(name);
    }, { once: true });
    doc.body.appendChild(script);
  }

  function inputPending() {
    try {
      return !!(navigator.scheduling && navigator.scheduling.isInputPending &&
        navigator.scheduling.isInputPending());
    } catch (e) { return false; }
  }

  function queueArt() {
    if (!fieldWanted()) { mark('art', 'skipped'); return; }
    var run = function () { activate('art'); };
    if (window.requestIdleCallback) {
      window.requestIdleCallback(run, { timeout: 2200 });
    } else {
      window.setTimeout(run, 450);
    }
  }

  function docsSettled() {
    removeIntentListeners();
    queueArt();
  }

  function startDocs(callback) {
    activate('docs', callback);
  }

  function queueDocs() {
    var run = function () {
      if (inputPending()) {
        window.setTimeout(queueDocs, 180);
        return;
      }
      startDocs(docsSettled);
    };
    if (window.requestIdleCallback) {
      window.requestIdleCallback(run, { timeout: 900 });
    } else {
      window.setTimeout(run, 80);
    }
  }

  function afterFirstPaint(callback) {
    if (!window.requestAnimationFrame) {
      window.setTimeout(callback, 0);
      return;
    }
    window.requestAnimationFrame(function () {
      window.requestAnimationFrame(callback);
    });
  }

  function closestAction(target) {
    if (!target || !target.closest) return null;
    return target.closest('a[href], button, [data-term], [role="button"]');
  }

  function cleanText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  /* docs.js normally snapshots on pagehide. A genuinely instant first click
     can leave before that runtime executes, so seed the same bounded stack in
     the capture phase. If docs.js becomes ready before pagehide, its own write
     replaces this same-path row rather than duplicating it. */
  function primeNavigationTrail(anchor) {
    if (!anchor || states.docs === 'ready') return;
    var raw = anchor.getAttribute('href') || '';
    var target;
    try { target = new URL(raw, window.location.href); } catch (e) { return; }
    if (target.origin !== window.location.origin || target.pathname === window.location.pathname) return;

    try {
      var key = 'mc:viewstate:stack';
      var stack = JSON.parse(window.sessionStorage.getItem(key) || '[]');
      if (!Array.isArray(stack)) stack = [];
      var heading = doc.querySelector('main h1, h1');
      var active = doc.activeElement;
      var focus = null;
      if (active && active.id) focus = { by: 'id', v: active.id };
      else if (active && active.tagName === 'A' && active.getAttribute('href')) {
        focus = { by: 'href', v: active.getAttribute('href') };
      }
      var open = [];
      var details = doc.querySelectorAll('details[open][id]');
      for (var d = 0; d < details.length; d += 1) open.push(details[d].id);
      var row = {
        url: window.location.pathname + window.location.search + window.location.hash,
        path: window.location.pathname,
        title: heading ? cleanText(heading.textContent) : cleanText(doc.title) || 'previous view',
        y: window.pageYOffset || root.scrollTop || 0,
        open: open,
        focus: focus
      };
      if (stack.length && stack[stack.length - 1] && stack[stack.length - 1].path === row.path) {
        stack[stack.length - 1] = row;
      } else {
        stack.push(row);
      }
      window.sessionStorage.setItem(key, JSON.stringify(stack.slice(-6)));
    } catch (e) {}
  }

  function replay(target, type) {
    if (!target) return;
    if (type === 'pointerover') {
      try {
        var event = typeof window.PointerEvent === 'function'
          ? new window.PointerEvent('pointerover', { bubbles: true, pointerType: 'mouse' })
          : new Event('pointerover', { bubbles: true });
        target.dispatchEvent(event);
      } catch (e) {}
      return;
    }
    window.setTimeout(function () {
      try { target.click(); } catch (e) {}
    }, 0);
  }

  function onIntent(event) {
    if (states.docs === 'ready') return;
    var target = closestAction(event.target);
    if (!target) return;
    var anchor = target.closest && target.closest('a[href]');
    /* The outer `|| ''` is load-bearing. closestAction() also matches buttons,
       [data-term] and [role=button], and for those `anchor` is null, so the
       inner expression yields null and .charAt() below threw a TypeError —
       which aborted the handler before startDocs(). Hover intent on every
       non-anchor control on the landing was therefore dead until the idle
       activation caught up, and each hover logged an uncaught error. */
    var href = (anchor && (anchor.getAttribute('href') || '')) || '';
    /* In-page routes are handled immediately below and need no shared runtime
       on their hover path. */
    if (href.charAt(0) === '#') return;
    startDocs(function () {
      if (event.type === 'pointerover' && target.hasAttribute && target.hasAttribute('data-term')) {
        replay(target, 'pointerover');
      }
    });
  }

  function revealHash(raw) {
    if (!raw || raw.charAt(0) !== '#' || raw.length < 2) return null;
    var id;
    try { id = decodeURIComponent(raw.slice(1)); } catch (e) { id = raw.slice(1); }
    var target = doc.getElementById(id);
    if (!target) return null;
    /* Open only the disclosures the target is nested inside, outermost
       included. A link to a section means the section: it must not open the
       section's own first disclosure on the reader's behalf, which is how
       "How the project works" used to unfold a twelve-paper list. */
    var detail = target.closest && target.closest('details');
    while (detail) {
      detail.open = true;
      var parent = detail.parentElement;
      detail = parent && parent.closest ? parent.closest('details') : null;
    }
    return target;
  }

  var anchorRaf = 0;
  var anchorMotionToken = 0;
  function cancelAnchorMotion() {
    anchorMotionToken += 1;
    if (!anchorRaf) return;
    window.cancelAnimationFrame(anchorRaf);
    anchorRaf = 0;
  }

  function scrollTargetTop(target) {
    var y = window.pageYOffset || root.scrollTop || 0;
    var margin = 0;
    try { margin = parseFloat(window.getComputedStyle(target).scrollMarginTop) || 0; } catch (e) {}
    var top = y + target.getBoundingClientRect().top - margin;
    var limit = Math.max(0, root.scrollHeight - window.innerHeight);
    return Math.max(0, Math.min(limit, top));
  }

  function animateTo(target) {
    cancelAnchorMotion();
    var start = window.pageYOffset || root.scrollTop || 0;
    var end = scrollTargetTop(target);
    var distance = end - start;
    if (Math.abs(distance) < 2 || !window.requestAnimationFrame) {
      window.scrollTo(0, end);
      return;
    }
    /* Distance-scaled, but capped inside the site's motion budget: --motion-panel
       is 260ms for a disclosure, and a jump across the page should not read as
       four times slower than opening a fold. The old 260–520ms band spent its
       upper half feeling deliberate rather than responsive. The cubic ease-out
       below is the JS twin of --ease-out. */
    var duration = Math.min(380, Math.max(200, Math.abs(distance) * 0.12));
    var started = 0;
    var token = ++anchorMotionToken;
    function frame(now) {
      if (token !== anchorMotionToken) return;
      if (!started) started = now;
      var p = Math.min(1, (now - started) / duration);
      var eased = 1 - Math.pow(1 - p, 3);
      window.scrollTo(0, start + distance * eased);
      if (p < 1) anchorRaf = window.requestAnimationFrame(frame);
      else anchorRaf = 0;
    }
    anchorRaf = window.requestAnimationFrame(frame);
  }

  /* An in-page jump moves the eye; it must move the caret too. Without this the
     next Tab after following an in-page link continues from the LINK, not from
     the section the reader just asked for, so keyboard and screen-reader
     visitors are silently left behind by the scroll. preventScroll keeps the
     focus call from fighting the animation that is already running. */
  function focusTarget(target) {
    if (!target || typeof target.focus !== 'function') return;
    var focusable = /^(?:A|BUTTON|INPUT|SELECT|TEXTAREA|SUMMARY|DETAILS)$/
      .test(target.tagName) || target.hasAttribute('tabindex');
    if (!focusable) target.setAttribute('tabindex', '-1');
    try { target.focus({ preventScroll: true }); } catch (e) {}
  }

  function moveToHash(raw, addHistory) {
    var target = revealHash(raw);
    if (!target) return false;
    if (addHistory) {
      try {
        if (window.history && window.history.pushState) {
          if (window.location.hash === raw) window.history.replaceState(null, '', raw);
          else window.history.pushState(null, '', raw);
        } else {
          window.location.hash = raw;
        }
      } catch (e) {}
    }
    var reduced = false;
    try {
      reduced = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    } catch (e) {}
    var run = function () {
      if (reduced) target.scrollIntoView({ behavior: 'auto', block: 'start' });
      else animateTo(target);
      focusTarget(target);
    };
    if (window.requestAnimationFrame) window.requestAnimationFrame(run);
    else run();
    return true;
  }

  function onClick(event) {
    var target = closestAction(event.target);
    if (!target) return;
    var anchor = target.closest && target.closest('a[href]');
    /* Same null-anchor guard as onIntent: clicking any button on the landing
       threw here, in a capture-phase listener, before the runtime handoff
       below could run. */
    var href = (anchor && (anchor.getAttribute('href') || '')) || '';
    if (
      href.charAt(0) === '#' && event.button === 0 &&
      !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey
    ) {
      event.preventDefault();
      event.stopImmediatePropagation();
      moveToHash(href, true);
      return;
    }

    if (states.docs === 'ready') return;
    if (anchor) primeNavigationTrail(anchor);
    var needsRuntime = target.tagName === 'BUTTON';
    if (!needsRuntime) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    startDocs(function () { replay(target, 'click'); });
  }

  function removeIntentListeners() {
    doc.removeEventListener('pointerover', onIntent, true);
    doc.removeEventListener('focusin', onIntent, true);
    doc.removeEventListener('pointerdown', onIntent, true);
    doc.removeEventListener('keydown', onIntent, true);
  }

  addPreload('docs');
  mark('docs', 'staged');
  if (fieldWanted()) {
    addPreload('art');
    mark('art', 'staged');
  } else {
    mark('art', 'skipped');
  }

  doc.addEventListener('pointerover', onIntent, true);
  doc.addEventListener('focusin', onIntent, true);
  doc.addEventListener('pointerdown', onIntent, true);
  doc.addEventListener('keydown', onIntent, true);
  doc.addEventListener('click', onClick, true);

  window.addEventListener('wheel', cancelAnchorMotion, { passive: true, capture: true });
  window.addEventListener('touchstart', cancelAnchorMotion, { passive: true, capture: true });
  window.addEventListener('pointerdown', cancelAnchorMotion, { passive: true, capture: true });
  window.addEventListener('keydown', cancelAnchorMotion, true);
  window.addEventListener('popstate', function () {
    if (window.location.hash) moveToHash(window.location.hash, false);
  });

  afterFirstPaint(queueDocs);
})();
