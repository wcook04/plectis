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
  var states = { docs: 'staged', art: 'staged', universe: 'staged', system: 'staged' };
  var callbacks = { docs: [], art: [], universe: [], system: [] };
  var templates = doc.querySelectorAll('template[data-plectis-runtime]');
  var i;

  function prefersReducedMotion() {
    try {
      return !!(window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    } catch (e) { return false; }
  }

  /* Save-Data is the reader's stated preference against the drawing. Reduced
     motion is a preference against movement, not against the image: art.js
     paints the finished weave at once for those readers (one paint, no
     reveal), where this gate used to leave an empty 95px band in the first
     screen (critique, 4 October 2026). art.js owns the full gate, and a
     mismatch here only ever costs or saves its 20KB, never correctness. */
  function fieldWanted() {
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

  /* A prefetch, not a preload, for a runtime the reader may never ask for:
     a preload that goes unused logs a console warning, and the system
     drawing's script runs only once the reader moves the map band. */
  var prefetched = {};
  function addPrefetch(name) {
    if (!refs[name] || prefetched[name] || states[name] !== 'staged') return;
    prefetched[name] = true;
    var link = doc.createElement('link');
    link.rel = 'prefetch';
    link.as = 'script';
    link.href = refs[name];
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
    // The system drawing loads because the reader just asked for it.
    try { script.fetchPriority = name === 'system' ? 'high' : 'low'; } catch (e) {}
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

  /* The universe map teaser fetches about 300KB of map data, so it starts
     only when the mathematics band comes within a screen of the viewport. */
  function queueUniverse() {
    var stage = doc.querySelector('[data-universe-stage]');
    if (!stage || !refs.universe) { mark('universe', 'skipped'); return; }
    var run = function () { activate('universe'); };
    if (!('IntersectionObserver' in window)) {
      window.setTimeout(run, 1200);
      return;
    }
    var watcher = new IntersectionObserver(function (entries) {
      for (var n = 0; n < entries.length; n += 1) {
        if (entries[n].isIntersecting) {
          watcher.disconnect();
          run();
          // The band's second drawing is one click away from here, so its
          // script is fetched into the cache now, at the lowest priority.
          addPrefetch('system');
          return;
        }
      }
    }, { rootMargin: '700px 0px' });
    watcher.observe(stage);
  }

  /* The map band asks for the system drawing on the reader's first sign of
     intent (pointer or focus on its switch or arrow, a click, #system in the
     address); see the map band block at the end of this file. */
  doc.addEventListener('plectis:runtime', function (event) {
    var name = event && event.detail && event.detail.name;
    if (name === 'system') activate('system');
  });

  function docsSettled() {
    removeIntentListeners();
    queueArt();
    queueUniverse();
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
    if (type === 'pointerover' || type === 'focusin') {
      // Loading the full runtime must preserve the intent that started it.
      // Match docs-loader's current-target guard: a departed hover or focus
      // must not open an old term after the script finishes downloading.
      if (type === 'focusin') {
        if (doc.activeElement !== target) return;
      } else {
        try { if (!target.matches || !target.matches(':hover')) return; }
        catch (e) { return; }
      }
      try {
        // The shared glossary consumes mouseover, rather than pointerover.
        var event = type === 'focusin'
          ? new Event('focusin', { bubbles: true })
          : new MouseEvent('mouseover', { bubbles: true });
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
      if ((event.type === 'pointerover' || event.type === 'focusin') &&
          target.hasAttribute && target.hasAttribute('data-term')) {
        replay(target, event.type);
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
    /* A link into the map band names a drawing: #system (or anything inside
       it) brings the system drawing into the band at once, #mathematics and
       the problem rows bring the mathematics back. A slide itself is the
       band's full height, so the jump lands on the band. */
    var band = target.closest && target.closest('[data-atlas]');
    if (band) {
      var slide = target.closest('[data-atlas-slide]');
      var view = slide ? slide.getAttribute('data-atlas-slide') : 'mathematics';
      try {
        doc.dispatchEvent(new CustomEvent('plectis:atlas-reveal', { detail: { view: view } }));
      } catch (e) {}
      if (target === slide) target = band;
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
    /* An in-page jump is a move the eye follows, so it eases in and out
       (--ease-move): the cubic ease-out it used covered half of a 2,600px
       jump in its first frames and the reader lost where they came from
       (critique, 4 October 2026). A long jump (over two screens) lands 240px
       short at once and glides the last stretch, easing out, so the reader
       sees where they arrive. Durations stay inside the motion budget. */
    var glide = false;
    var screen = window.innerHeight || 800;
    if (Math.abs(distance) > screen * 2) {
      start = distance > 0 ? end - 240 : end + 240;
      window.scrollTo(0, start);
      distance = end - start;
      glide = true;
    }
    var duration = glide ? 280 :
      Math.min(600, Math.max(320, 200 + 90 * Math.log(1 + Math.abs(distance) / 300) / Math.LN2));
    var started = 0;
    var token = ++anchorMotionToken;
    function frame(now) {
      if (token !== anchorMotionToken) return;
      if (!started) started = now;
      var p = Math.min(1, (now - started) / duration);
      var eased = glide ? 1 - Math.pow(1 - p, 3) :
        (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);
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
    /* The map band's switch and arrows and the results carousel's arrows are
       run by this file, not by docs.js. Holding their clicks until docs.js
       had loaded left them dead for seconds on a slow line, and the replay
       then moved the band after the reader had given up (4 October 2026). */
    var landingControl = target.closest && target.closest('[data-atlas], [data-results-carousel]');
    var needsRuntime = target.tagName === 'BUTTON' && !landingControl;
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
   bottom-left "back" pill. It says its line once and folds to its mark when
   reading starts; the close control puts it away for good (localStorage).
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

  /* Desktop: the cue says its line once, then folds to its mark when the
     reader starts reading (the first real scroll) or uses a term, so it
     never sits over a button or a figure for the rest of the page. Touch:
     it starts folded so the small screen stays clear. */
  /* On a short laptop screen the open chip would sit on the plait's band (at
     1280x800 it covered the band's right third, and the contract keeps the
     drawing clear of text), so there it starts folded to its mark, which
     still opens it. Landing only: the docs pages have no band, so docs.js's
     copy needs no twin of this check. */
  var band = document.querySelector('[data-plait-band]');
  function overBand() {
    if (!band || !band.getBoundingClientRect) return false;
    var chipBox = hint.getBoundingClientRect();
    var bandBox = band.getBoundingClientRect();
    return chipBox.top < bandBox.bottom && chipBox.bottom > bandBox.top &&
      chipBox.left < bandBox.right && chipBox.right > bandBox.left;
  }
  // The band settles once the web fonts arrive, so look again then and at
  // load; a chip the reader has already folded or opened is left alone.
  function foldIfOverBand() {
    if (gone || hint.classList.contains('is-compact') || hint.classList.contains('is-open')) return;
    if (overBand()) setCompact(true);
  }
  if (touch) {
    setCompact(true);
  } else {
    foldIfOverBand();
    try { if (document.fonts && document.fonts.ready) document.fonts.ready.then(foldIfOverBand); } catch (e) {}
    window.addEventListener('load', foldIfOverBand, { once: true });
  }
  if (!touch) {
    var folded = false;
    var onScroll = function () { if ((window.scrollY || 0) > 240) foldOnce(); };
    var onTerm = function (ev) {
      var t = ev.target;
      if (t && t.closest && t.closest('a.narrative-ref--term, [data-term-preview-only]')) foldOnce();
    };
    var foldOnce = function () {
      if (folded || gone) return;
      folded = true;
      if (!hint.classList.contains('is-compact')) setCompact(true);
      window.removeEventListener('scroll', onScroll);
      document.removeEventListener('pointerover', onTerm, true);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    document.addEventListener('pointerover', onTerm, true);
  }
})();

/* Results carousel (2026-10-04). The strongest results sit in one fixed
   window; the arrows, the left and right keys and a swipe move between them,
   and the window never changes size. Without this script the window is a
   horizontal strip that scrolls and snaps, so every result stays reachable.
   Slides out of view are inert, so a keyboard only meets the visible one.
   A click or swipe plays one move; a key press lands at once, because a
   keyboard action never waits on an animation. */
(function () {
  var root = document.querySelector('[data-results-carousel]');
  if (!root) return;
  var track = root.querySelector('.home-results__track');
  var slides = track ? Array.prototype.slice.call(track.children) : [];
  var prev = root.querySelector('[data-results-prev]');
  var next = root.querySelector('[data-results-next]');
  var count = root.querySelector('[data-results-count]');
  if (!track || slides.length < 2 || !prev || !next) return;
  var index = 0;
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  root.classList.add('is-live');
  if (reduced) root.classList.add('is-still');

  function show(target, direction, instant) {
    index = (target + slides.length) % slides.length;
    if (instant) {
      root.classList.add('is-instant');
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(function () { root.classList.remove('is-instant'); });
      });
    }
    track.style.transform = 'translateX(' + (-100 * index) + '%)';
    root.setAttribute('data-direction', direction > 0 ? 'next' : 'prev');
    slides.forEach(function (slide, i) {
      var on = i === index;
      slide.classList.toggle('is-active', on);
      slide.setAttribute('aria-hidden', on ? 'false' : 'true');
      if ('inert' in slide) slide.inert = !on;
    });
    if (count) count.textContent = (index + 1) + ' / ' + slides.length;
  }

  prev.addEventListener('click', function () { show(index - 1, -1); });
  next.addEventListener('click', function () { show(index + 1, 1); });
  root.addEventListener('keydown', function (event) {
    if (event.target && /^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName)) return;
    if (event.key === 'ArrowRight') { event.preventDefault(); show(index + 1, 1, true); }
    else if (event.key === 'ArrowLeft') { event.preventDefault(); show(index - 1, -1, true); }
  });
  var startX = null;
  track.addEventListener('pointerdown', function (event) { startX = event.clientX; }, { passive: true });
  track.addEventListener('pointerup', function (event) {
    if (startX === null) return;
    var dx = event.clientX - startX;
    startX = null;
    if (Math.abs(dx) > 48) show(index + (dx < 0 ? 1 : -1), dx < 0 ? 1 : -1);
  }, { passive: true });
  show(0, 1, true);
})();

/* The map band (2026-10-04). Will asked for an arrow that "scrolls that
   horizontal slice, from left to right, all the way wall to wall ... bounded
   of where the map is", and a switch between "system versus maths" that
   "animatedly moves that away". The band holds two drawings in a track as
   wide as the window: the mathematics (the eight problems beside the universe
   map) and the system (the earlier software's components beside their
   drawing).

   - A click on the switch or an edge arrow moves the whole slice in one eased
     move (--ease-move over 720ms: a camera move across a full window, inside
     the budget for a data graphic). Each drawing travels a little further
     than its text, so the slice reads as two layers, and the switch's thumb
     slides with it.
   - Arrow keys on the switch, reduced motion and links into the band land at
     once: a keyboard action never waits on an animation.
   - The slide out of view is inert, hidden from assistive technology and not
     painted, so a keyboard meets only the drawing on screen.
   - Resting the pointer on an edge arrow leans the slice a few pixels toward
     the drawing it opens, so the arrow shows where it goes before it is
     pressed; leaving lets it settle back.
   - The system drawing's script and data load on the first sign of intent
     (pointer or focus on its switch or arrow, a click, #system in the
     address), through the runtime scheduler above.
   - plectis:atlas {view, previous, phase: start|end, instant} tells the two
     drawings when the band moves, so the one leaving can let go of a hover.
   Without this script the band is a strip that scrolls and snaps. */
(function () {
  var band = document.querySelector('[data-atlas]');
  if (!band || !band.querySelector) return;
  var viewport = band.querySelector('.home-atlas__viewport');
  var track = band.querySelector('[data-atlas-track]');
  if (!viewport || !track) return;
  var slides = Array.prototype.slice.call(track.querySelectorAll('[data-atlas-slide]'));
  if (slides.length < 2) return;
  var views = slides.map(function (slide) { return slide.getAttribute('data-atlas-slide'); });
  var tabs = Array.prototype.slice.call(band.querySelectorAll('[data-atlas-go]'));
  var prev = band.querySelector('[data-atlas-prev]');
  var next = band.querySelector('[data-atlas-next]');
  var MOVE_MS = 720;
  var LEAN_PX = 26;
  var reduced = false;
  try { reduced = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); } catch (e) {}
  var index = 0;
  var lean = 0;
  var token = 0;
  var settleTimer = 0;
  var leanTimer = 0;
  var fine = false;
  try { fine = !!(window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches); } catch (e) {}

  function emit(name, detail) {
    try { document.dispatchEvent(new CustomEvent(name, { detail: detail })); } catch (e) {}
  }
  function want() { emit('plectis:runtime', { name: 'system' }); }

  band.classList.add('is-live');
  if (reduced) band.classList.add('is-still');
  // A fragment followed before this ran may have scrolled the fallback strip.
  viewport.scrollLeft = 0;

  function place() {
    track.style.transform = 'translate3d(calc(' + (-100 * index) + '% + ' + lean + 'px), 0, 0)';
  }

  function syncControls() {
    band.setAttribute('data-atlas-view', views[index]);
    tabs.forEach(function (tab) {
      var on = tab.getAttribute('data-atlas-go') === views[index];
      tab.setAttribute('aria-selected', on ? 'true' : 'false');
      tab.tabIndex = on ? 0 : -1;
    });
    if (prev) {
      prev.hidden = false;
      prev.classList.toggle('is-away', index === 0);
    }
    if (next) {
      next.hidden = false;
      next.classList.toggle('is-away', index === slides.length - 1);
    }
  }

  function setPresence(slide, on) {
    if ('inert' in slide) slide.inert = !on;
    if (on) slide.removeAttribute('aria-hidden');
    else slide.setAttribute('aria-hidden', 'true');
  }

  /* The drawings ride a nearer layer: each covers a few per cent more ground
     than its text on the way out and on the way in, then rests exactly in
     place (no fill, so nothing keeps a transform or a layer afterwards). */
  function parallax(from, to, dir) {
    if (reduced || !Element.prototype.animate) return;
    var timing = { duration: MOVE_MS, easing: 'cubic-bezier(0.65, 0, 0.35, 1)' };
    var out = slides[from].querySelector('.home-split__figure');
    var inn = slides[to].querySelector('.home-split__figure');
    try {
      if (out) out.animate([{ transform: 'none' }, { transform: 'translate3d(' + (-dir * 7) + '%, 0, 0)' }], timing);
      if (inn) inn.animate([{ transform: 'translate3d(' + (dir * 9) + '%, 0, 0)' }, { transform: 'none' }], timing);
    } catch (e) {}
  }

  function show(target, options) {
    options = options || {};
    var to = typeof target === 'number' ? target : views.indexOf(target);
    if (to < 0 || to >= slides.length) return;
    var from = index;
    var instant = !!options.instant || reduced;
    window.clearTimeout(leanTimer);
    if (views[to] === 'system') want();
    if (to === from) {
      if (lean) { lean = 0; track.style.transitionDuration = ''; place(); }
      return;
    }
    index = to;
    lean = 0;
    token += 1;
    var mine = token;
    window.clearTimeout(settleTimer);
    track.style.transitionDuration = '';
    band.classList.toggle('is-instant', instant);
    slides.forEach(function (slide, i) {
      slide.classList.add('is-shown');
      setPresence(slide, i === index);
    });
    syncControls();
    emit('plectis:atlas', { view: views[index], previous: views[from], phase: 'start', instant: instant });
    if (!instant) parallax(from, to, to > from ? 1 : -1);
    place();
    if (options.remember) {
      try {
        if (window.history && window.history.replaceState) {
          window.history.replaceState(window.history.state, '', '#' + (views[index] === 'system' ? 'system' : 'mathematics'));
        }
      } catch (e) {}
    }
    var settle = function () {
      if (mine !== token) return;
      band.classList.remove('is-instant');
      slides.forEach(function (slide, i) { slide.classList.toggle('is-shown', i === index); });
      emit('plectis:atlas', { view: views[index], previous: views[from], phase: 'end', instant: instant });
    };
    if (instant) {
      // Two frames: the jump paints with transitions off, then they return.
      window.requestAnimationFrame(function () { window.requestAnimationFrame(settle); });
    } else {
      settleTimer = window.setTimeout(settle, MOVE_MS + 40);
    }
  }

  /* Lean toward the drawing an edge arrow opens, after a short dwell so a
     pointer passing over the arrow on its way somewhere else moves nothing. */
  function leanToward(dir) {
    if (reduced || !fine) return;
    window.clearTimeout(leanTimer);
    leanTimer = window.setTimeout(function () {
      lean = -dir * LEAN_PX;
      track.style.transitionDuration = '260ms';
      place();
    }, 90);
  }
  function settleLean() {
    window.clearTimeout(leanTimer);
    if (!lean) return;
    lean = 0;
    track.style.transitionDuration = '220ms';
    place();
  }

  tabs.forEach(function (tab) {
    var view = tab.getAttribute('data-atlas-go');
    tab.addEventListener('click', function () { show(view, { remember: true }); });
    if (view === 'system') {
      tab.addEventListener('pointerenter', want);
      tab.addEventListener('focus', want);
    }
  });
  var list = band.querySelector('[role="tablist"]');
  if (list) {
    list.addEventListener('keydown', function (event) {
      var key = event.key;
      var to = key === 'ArrowRight' ? index + 1 : key === 'ArrowLeft' ? index - 1 :
        key === 'Home' ? 0 : key === 'End' ? slides.length - 1 : null;
      if (to === null) return;
      event.preventDefault();
      to = Math.max(0, Math.min(slides.length - 1, to));
      show(to, { instant: true, remember: true });
      var tab = tabs[to];
      if (tab && tab.focus) tab.focus();
    });
  }
  [[prev, -1], [next, 1]].forEach(function (pair) {
    var button = pair[0];
    var dir = pair[1];
    if (!button) return;
    button.addEventListener('click', function () { show(index + dir, { remember: true }); });
    button.addEventListener('pointerenter', function (event) {
      if (event.pointerType !== 'mouse') return;
      if (index + dir >= 0 && index + dir < slides.length && views[index + dir] === 'system') want();
      leanToward(dir);
    });
    button.addEventListener('pointerleave', settleLean);
  });

  /* A swipe on a touch screen: a clearly horizontal stroke of 56px or more.
     The viewport takes horizontal touch strokes (touch-action: pan-y), so the
     page still scrolls vertically under a thumb. */
  var sx = null;
  var sy = 0;
  viewport.addEventListener('pointerdown', function (event) {
    if (event.pointerType !== 'touch') return;
    sx = event.clientX;
    sy = event.clientY;
  }, { passive: true });
  viewport.addEventListener('pointerup', function (event) {
    if (sx === null) return;
    var dx = event.clientX - sx;
    var dy = event.clientY - sy;
    sx = null;
    if (Math.abs(dx) > 56 && Math.abs(dx) > 1.6 * Math.abs(dy)) {
      show(index + (dx < 0 ? 1 : -1), { remember: true });
    }
  }, { passive: true });
  viewport.addEventListener('pointercancel', function () { sx = null; }, { passive: true });

  document.addEventListener('plectis:atlas-reveal', function (event) {
    var view = event && event.detail && event.detail.view;
    if (view) show(view, { instant: true });
  });
  function fromHash() {
    var raw = window.location.hash || '';
    if (raw.length < 2) return null;
    var id;
    try { id = decodeURIComponent(raw.slice(1)); } catch (e) { id = raw.slice(1); }
    var el = document.getElementById(id);
    if (!el || !band.contains(el)) return null;
    var slide = el.closest && el.closest('[data-atlas-slide]');
    return slide ? slide.getAttribute('data-atlas-slide') : 'mathematics';
  }
  window.addEventListener('hashchange', function () {
    var view = fromHash();
    if (view) show(view, { instant: true });
  });

  slides.forEach(function (slide, i) {
    slide.classList.toggle('is-shown', i === 0);
    setPresence(slide, i === 0);
  });
  syncControls();
  place();
  var initial = fromHash();
  if (initial && initial !== views[0]) show(initial, { instant: true });
})();
