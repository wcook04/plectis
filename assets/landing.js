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

/* Glossary cue (2026-09-14). A small fixed chip, bottom-right, mounted here so
   the homepage has it before docs.js's idle slot; docs.js carries the same
   IIFE for maths/docs pages and is a no-op if this already ran
   (data-glossary-hint). Keep the two copies in sync. It sits opposite the
   bottom-left "back" pill. It stays open, saying one line, until the
   reader closes it; the close control puts it away for good (localStorage).
   On touch screens it starts folded to its mark and unfolds on a press. The glossary
   page itself does not need it. Not in landing HTML: the visible-word budget
   is full. */
(function () {
  var root = document.documentElement;
  if (!document.body || !document.createElement) return;
  if (root.getAttribute('data-glossary-hint')) return;
  try { if (localStorage.getItem('plectis-glossary-hint-dismissed')) return; } catch (e) {}
  if (/\/glossary\.html$/.test(window.location.pathname || '')) {
    root.setAttribute('data-glossary-hint', 'skip');
    return;
  }
  var firstTerm = document.querySelector('a.narrative-ref--term[data-term]');
  if (!firstTerm) {
    root.setAttribute('data-glossary-hint', 'skip');
    return;
  }
  var touch = false;
  try { touch = !!(window.matchMedia && window.matchMedia('(hover: none)').matches); } catch (e) {}
  var glossaryHref = (firstTerm.getAttribute('href') || '').split('#')[0] || 'docs/glossary.html';

  var hint = document.createElement('aside');
  hint.className = 'glossary-hint';
  hint.setAttribute('role', 'note');
  hint.setAttribute('aria-label', 'Glossary');

  var mark = document.createElement('button');
  mark.type = 'button';
  mark.className = 'glossary-hint__mark';
  mark.setAttribute('aria-label', 'Glossary tip');
  mark.setAttribute('aria-expanded', 'true');
  mark.textContent = '?';

  var body = document.createElement('div');
  body.className = 'glossary-hint__body';
  var inner = document.createElement('div');
  var text = document.createElement('div');
  text.className = 'glossary-hint__text';

  var p1 = document.createElement('p');
  p1.className = 'glossary-hint__lead';
  p1.appendChild(document.createTextNode(touch
    ? 'Tap any technical term for its definition. '
    : 'Hover any technical term for its definition. '));
  var all = document.createElement('a');
  all.href = glossaryHref;
  all.textContent = 'Glossary';
  p1.appendChild(all);

  var p2 = document.createElement('p');
  p2.className = 'glossary-hint__more';
  p2.appendChild(document.createTextNode('Contest or clarify a definition: '));
  var mail = document.createElement('a');
  mail.href = 'mailto:williamwkcook@gmail.com';
  mail.textContent = 'email me';
  p2.appendChild(mail);
  p2.appendChild(document.createTextNode(' and the correction is credited.'));

  text.appendChild(p1);
  text.appendChild(p2);
  inner.appendChild(text);
  body.appendChild(inner);

  var close = document.createElement('button');
  close.type = 'button';
  close.className = 'glossary-hint__close';
  close.setAttribute('aria-label', 'Dismiss glossary tip');
  close.textContent = '×';

  hint.appendChild(mark);
  hint.appendChild(body);
  hint.appendChild(close);
  document.body.appendChild(hint);
  root.setAttribute('data-glossary-hint', 'shown');

  var gone = false;

  function setCompact(on) {
    hint.classList.toggle('is-compact', on);
    hint.classList.remove('is-open');
    mark.setAttribute('aria-expanded', on ? 'false' : 'true');
  }

  function finish() {
    if (hint.parentNode) hint.parentNode.removeChild(hint);
  }

  function dismiss() {
    if (gone) return;
    gone = true;
    try { localStorage.setItem('plectis-glossary-hint-dismissed', '1'); } catch (e) {}
    root.setAttribute('data-glossary-hint', 'away');
    hint.classList.add('is-away');
    hint.addEventListener('transitionend', finish);
    window.setTimeout(finish, 400);
  }


  /* The mark pins the chip open when it is folded, and folds it when it is
     open; on a touch screen the chip starts folded so the reading area stays
     clear, and the mark is the way in. */
  mark.addEventListener('click', function () {
    if (hint.classList.contains('is-compact')) {
      var open = !hint.classList.contains('is-open');
      hint.classList.toggle('is-open', open);
      mark.setAttribute('aria-expanded', open ? 'true' : 'false');
    } else {
      setCompact(true);
    }
  });

  close.addEventListener('click', function () {
    dismiss();
    var main = document.querySelector('main');
    if (main && main.focus) {
      main.setAttribute('tabindex', '-1');
      main.focus({ preventScroll: true });
    }
  });

  /* Desktop: the cue stays open until the reader closes it. Touch: it
     starts folded so the small screen stays clear. */
  if (touch) setCompact(true);
})();

/* Collapsed bands (2026-09-14). Below the hero the landing is a list of
   section headings. Each band is closed until its heading is clicked,
   except the recordings band (#demo-videos), which stays open so the three
   walkthroughs are in view. "Expand all" in the page tools opens every band
   and every disclosure, and turns into "Collapse all". Collapse all leaves
   the recordings open. A link into a band opens it. Without scripts
   nothing is collapsed: the page stays complete. */
(function collapsedBands() {
  'use strict';
  var doc = document;
  var main = doc.getElementById('main');
  var toggle = doc.querySelector('[data-landing-expand]');
  if (!main || !toggle) return;

  var bands = [];
  var sections = Array.prototype.slice.call(main.querySelectorAll('section.section'));
  sections.forEach(function (section) {
    if (section.id === 'short-link-reader' || section.classList.contains('hero')) return;
    var head = section.querySelector('.section__head') || section.querySelector('.eyebrow');
    if (!head) return;
    var extra = [];
    if (section.id === 'problems') {
      var tail = doc.getElementById('boundaries');
      if (tail) extra.push(tail);
    }
    var band = {
      section: section,
      head: head,
      extra: extra,
      open: false,
      stayOpen: section.id === 'demo-videos'
    };
    head.classList.add('band-head');
    head.setAttribute('role', 'button');
    head.setAttribute('tabindex', '0');
    /* The closed band shows one line of its first sentence. When the sentence
       is longer than the line, the stylesheet fades the line out at its edge
       instead of cutting it with an ellipsis; a sentence that fits is left
       whole, so the flag is measured rather than assumed. */
    var gist = head.querySelector('h2 + p');
    band.measure = function () {
      if (!gist || band.open) return;
      gist.removeAttribute('data-band-overflow');
      if (gist.scrollWidth > gist.clientWidth + 1) gist.setAttribute('data-band-overflow', '');
    };
    band.set = function (open) {
      if (band.stayOpen) open = true;
      band.open = open;
      section.classList.toggle('is-collapsed', !open);
      extra.forEach(function (el) { el.classList.toggle('is-collapsed', !open); });
      head.setAttribute('aria-expanded', open ? 'true' : 'false');
      band.measure();
    };
    function onActivate(ev) {
      if (ev.target && ev.target.closest && ev.target.closest('a')) return;
      ev.preventDefault();
      band.set(!band.open);
      syncToggle();
    }
    head.addEventListener('click', onActivate);
    head.addEventListener('keydown', function (ev) {
      if (ev.key === 'Enter' || ev.key === ' ') onActivate(ev);
    });
    band.set(band.stayOpen);
    bands.push(band);
  });
  if (!bands.length) return;

  var expanded = false;
  function syncToggle() {
    expanded = bands.every(function (b) { return b.open; });
    toggle.setAttribute('aria-pressed', expanded ? 'true' : 'false');
    var label = toggle.querySelector('.docs-pagetool__text') || toggle;
    label.textContent = expanded ? 'Collapse all' : 'Expand all';
  }
  toggle.hidden = false;
  toggle.addEventListener('click', function () {
    var open = !expanded;
    bands.forEach(function (b) { b.set(open || b.stayOpen); });
    var details = main.querySelectorAll('details');
    for (var i = 0; i < details.length; i += 1) details[i].open = open;
    syncToggle();
  });

  /* A hash link into a band opens that band, so deep links keep working. */
  function openForHash() {
    var raw = window.location.hash;
    if (!raw || raw.length < 2) return;
    var id;
    try { id = decodeURIComponent(raw.slice(1)); } catch (e) { id = raw.slice(1); }
    var target = doc.getElementById(id);
    if (!target) return;
    bands.forEach(function (b) {
      if (b.section.contains(target) || b.extra.some(function (el) { return el.contains(target); })) {
        b.set(true);
      }
    });
    syncToggle();
  }
  window.addEventListener('hashchange', openForHash);
  openForHash();
  syncToggle();
  doc.documentElement.setAttribute('data-landing-bands', 'on');
  /* The band styles apply once the attribute is on, so measure after them. */
  bands.forEach(function (b) { b.measure(); });
  var measureTimer = 0;
  window.addEventListener('resize', function () {
    window.clearTimeout(measureTimer);
    measureTimer = window.setTimeout(function () {
      bands.forEach(function (b) { b.measure(); });
    }, 120);
  }, { passive: true });
})();

