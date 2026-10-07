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

  /* The map band's caption rows carry the drawings' buttons at the foot of
     the band, where the chip stands when the band fills the window. While a
     caption row that reaches the chip's column is in the bottom strip of the
     window, the chip steps out of the way (landing only, 4 October 2026). */
  var captions = document.querySelectorAll('.home-universe__caption, .home-system__caption');
  if (captions.length && 'IntersectionObserver' in window) {
    // Rows in the bottom strip, judged against the chip's column from live
    // boxes: a row that slid in from the right edge settles elsewhere.
    var inStrip = [];
    // And either drawing's card wherever it stands in the window's lower
    // right corner, where the chip lives: the chip never sits over a card's
    // frame (it stood inside the mathematics card at 1280 and across the
    // system card's edge at 1440, critique of 5 October 2026).
    var inCorner = [];
    var updateTuck = function () {
      var limit = (window.innerWidth || 0) - 96;
      var tuck = inStrip.some(function (row) { return row.getBoundingClientRect().right > limit; }) ||
        inCorner.some(function (card) {
          var r = card.getBoundingClientRect();
          return r.width > 0 && r.right > limit && r.left < (window.innerWidth || 0) && r.bottom > (window.innerHeight || 0) - 90;
        });
      hint.classList.toggle('is-tucked', tuck);
    };
    var cornerWatch = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var at = inCorner.indexOf(entry.target);
        if (entry.isIntersecting && at < 0) inCorner.push(entry.target);
        if (!entry.isIntersecting && at >= 0) inCorner.splice(at, 1);
      });
      updateTuck();
    }, { rootMargin: '-86% 0px 0px -88%' });
    Array.prototype.forEach.call(document.querySelectorAll('.home-universe, .home-system'), function (card) { cornerWatch.observe(card); });
    var tuckWatch = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var at = inStrip.indexOf(entry.target);
        if (entry.isIntersecting && at < 0) inStrip.push(entry.target);
        if (!entry.isIntersecting && at >= 0) inStrip.splice(at, 1);
      });
      updateTuck();
    }, { rootMargin: '-86% 0px 0px 0px' });
    for (var ci = 0; ci < captions.length; ci += 1) tuckWatch.observe(captions[ci]);
    document.addEventListener('plectis:atlas', function (event) {
      if (event.detail && event.detail.phase === 'end') updateTuck();
    });
    window.addEventListener('resize', updateTuck, { passive: true });
  }

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
  /* The open chip never stands on a drawing. On a short laptop screen it sat
     on the plait's band (at 1280x800 it covered the band's right third, and
     the contract keeps the drawing clear of text), and with the mathematics
     map on the first screen it covered the map's right edge at 1512 and at
     1920 (critique of 5 October 2026). Where it would, it starts folded to
     its mark, which still opens it, and a short first scroll that brings a
     drawing under it folds it too. A drawing in the slide the switch has
     put away is hidden and does not count. Landing only: the docs pages
     have no band or maps, so docs.js's copy needs no twin of this check. */
  var drawings = document.querySelectorAll('[data-plait-band], .home-universe, .home-system');
  function overDrawing() {
    var chipBox = hint.getBoundingClientRect();
    return Array.prototype.some.call(drawings, function (drawing) {
      var box = drawing.getBoundingClientRect();
      return box.width > 0 && chipBox.top < box.bottom && chipBox.bottom > box.top &&
        chipBox.left < box.right && chipBox.right > box.left &&
        window.getComputedStyle(drawing).visibility !== 'hidden';
    });
  }
  // The band settles once the web fonts arrive, so look again then and at
  // load; a chip the reader has already folded or opened is left alone.
  function foldIfOverDrawing() {
    if (gone || hint.classList.contains('is-compact') || hint.classList.contains('is-open')) return;
    if (overDrawing()) setCompact(true);
  }
  if (touch) {
    setCompact(true);
  } else {
    foldIfOverDrawing();
    try { if (document.fonts && document.fonts.ready) document.fonts.ready.then(foldIfOverDrawing); } catch (e) {}
    window.addEventListener('load', foldIfOverDrawing, { once: true });
  }
  if (!touch) {
    var folded = false;
    var onScroll = function () {
      if ((window.scrollY || 0) > 240) foldOnce();
      else foldIfOverDrawing();
    };
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

  /* On a phone every place the folded mark could stand is on the reading
     column: a critique of 5 October 2026 found it over the problem list,
     the videos and the essay. So once reading starts (the same first real
     scroll that folds the open chip on a wider screen) the mark steps
     aside, and it stands again when the reader is back at the top of the
     page; the header keeps the way to the glossary. Keep in step with
     docs.js. */
  var narrow = null;
  try { narrow = window.matchMedia ? window.matchMedia('(max-width: 620px)') : null; } catch (e) {}
  if (narrow) {
    var stepAside = function () {
      var aside = narrow.matches && (window.scrollY || 0) > 240;
      if (aside && hint.classList.contains('is-open')) setCompact(true);
      hint.classList.toggle('is-aside', aside);
    };
    stepAside();
    window.addEventListener('scroll', stepAside, { passive: true });
    if (narrow.addEventListener) narrow.addEventListener('change', stepAside);
    else if (narrow.addListener) narrow.addListener(stepAside);
  }
})();

/* Results carousel: quiet arrows, a count and one readable theorem at a time.
   Live slides use normal block layout so native fragment and focus scrolling
   cannot fight a horizontal transform. Inactive slides are hidden and inert.
   Without JavaScript, all results remain in a scrollable, snapping strip. */
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
  root.classList.add('is-live');
  var reduceMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  // Keep the overview in the results owner: its figures are copies of the
  // actual inlined plates, never a second catalogue of mathematical claims.
  // Its rules live in style.css, so the band can paint as the overview from
  // its first frame: a stylesheet this script fetched late used to show the
  // first result's sheet for a moment on every refresh (Will, 6 October
  // 2026: "when I refresh the page, it flashes that white box thing").
  var overview = false;
  var overviewButtons = [];
  var overviewControl;
  var views;

  /* Each result leads with its plate, explained in two registers (Will,
     6 October 2026): intuitive by default, and on the switch "the technical
     version of what the intuitive is showing". The choice holds while the
     reader turns through the results. */
  var modes = Array.prototype.slice.call(root.querySelectorAll('[data-results-mode]'));
  function setMode(mode) {
    root.setAttribute('data-results-mode', mode);
    modes.forEach(function (button) {
      button.setAttribute('aria-pressed', button.getAttribute('data-results-mode') === mode ? 'true' : 'false');
    });
    // The technical reading shows the whole drawing with its annotations.
    if (mode === 'technical') stopStory();
  }
  modes.forEach(function (button) {
    button.addEventListener('click', function () { setMode(button.getAttribute('data-results-mode')); });
  });
  setMode('intuitive');

  /* "Read the theorem" opens the statement, proof idea, boundary and sources
     under the plate, on every result at once, so a reader who wants the
     theorems keeps them while turning; the stylesheet unrolls it and draws
     the statement's rule down. Closed, it is hidden from the tab order. */
  var theoremButtons = Array.prototype.slice.call(root.querySelectorAll('[data-results-theorem]'));
  function setTheorem(open, from) {
    root.classList.toggle('is-theorem-open', open);
    theoremButtons.forEach(function (button) {
      button.setAttribute('aria-expanded', open ? 'true' : 'false');
      button.textContent = open ? 'Hide the theorem' : 'Read the theorem';
    });
    if (open && from) {
      var region = document.getElementById(from.getAttribute('aria-controls'));
      if (region && region.scrollIntoView) {
        window.setTimeout(function () {
          region.scrollIntoView({ block: 'nearest', behavior: reduceMotion ? 'auto' : 'smooth' });
        }, reduceMotion ? 0 : 240);
      }
    }
  }
  theoremButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      setTheorem(!root.classList.contains('is-theorem-open'), button);
    });
  });

  /* The plate's story (7 October 2026; Will: the intuitive one could be
     "animated too to ... communicate the underlying ideas"). A plate with
     beats is drawn in stages, each while its sentence is read: the whole
     drawing first stands faint, as an engraver's underdrawing, then stage
     by stage its strokes are ruled on in the direction the argument runs,
     its regions hatched stroke after stroke, its points and numerals set,
     and the result's own ember burned in, arriving hot and cooling to the
     ink. The sentence being read is in ink, the ones to come faint. Then
     the drawing rests whole, which is all a reader with reduced motion, a
     thumbnail or the problem page sees. A sentence held under the pointer
     shows the drawing as it stood when that sentence was read; a sentence
     clicked holds the story there; "Replay" tells it again. A plate told in
     scenes (7 October 2026, Will: "so fucking good looking and clear")
     can change as well as grow: a scene stands for a few stages and leaves,
     and a moved object glides to its new place. */
  var EMBER_MS = 784;
  var story = null;
  function numberOf(node, name) { return parseInt(node.getAttribute(name), 10) || 0; }
  function plateOf(slide) {
    return slide && slide.querySelector ? slide.querySelector('.home-result-plate svg.plate') : null;
  }
  function stageGroups(svg) {
    return svg && svg.querySelectorAll ? Array.prototype.slice.call(svg.querySelectorAll('.pl-stage')) : [];
  }
  function beatsOf(slide) {
    return slide && slide.querySelectorAll ? Array.prototype.slice.call(slide.querySelectorAll('.home-result-plate__beat[data-beat]')) : [];
  }
  // A scene (data-until) stands from its stage until the stage it names,
  // then leaves; a resting group stands from its stage to the end.
  function untilOf(group) {
    var until = parseInt(group.getAttribute('data-until'), 10);
    return isNaN(until) ? Infinity : until;
  }
  function standsAt(group, n) {
    var k = numberOf(group, 'data-stage');
    return k <= n && n <= untilOf(group);
  }
  // A moved object (data-glide="dx dy"): it arrives inked, sliding in from
  // that offset in plate units, rather than being drawn again.
  function glideOf(group) {
    var parts = (group.getAttribute('data-glide') || '').split(/\s+/).map(Number);
    return parts.length === 2 && isFinite(parts[0]) && isFinite(parts[1]) ? parts : null;
  }
  function markBeats(run, n) {
    run.beats.forEach(function (beat) {
      var k = numberOf(beat, 'data-beat');
      beat.classList.toggle('is-reading', k === n);
      beat.classList.toggle('is-read', k < n);
    });
  }
  // The hot ink a burned stroke arrives in, and its glow (the night sheet
  // only: on paper a glow reads as a blur, so there it is transparent).
  function plateInk(svg, name, fallback) {
    var value = window.getComputedStyle ? window.getComputedStyle(svg).getPropertyValue(name) : '';
    return (value || '').trim() || fallback;
  }
  // How long a stroke's dash must be to draw it on. A path's dash pattern
  // restarts at each of its subpaths, so a path of many strokes (a region's
  // hatching, a row of ticks, a ring of petals) is drawn by growing every
  // stroke at once from where it starts, as far as the longest: the dash is
  // that stroke's length, and the region fills as one sweep of the burin.
  function strokeRun(mark) {
    var total = 0;
    try { total = mark.getTotalLength(); } catch (err) { return 0; }
    if (mark.tagName.toLowerCase() !== 'path') return total;
    var parts = (mark.getAttribute('d') || '').split(/(?=M)/).filter(function (part) { return /\S/.test(part); });
    if (parts.length < 2) return total;
    var longest = 0, probe = null;
    parts.forEach(function (part) {
      var seg = /^M\s*(-?[\d.]+)[ ,]+(-?[\d.]+)\s*L\s*(-?[\d.]+)[ ,]+(-?[\d.]+)\s*$/.exec(part.trim());
      var length = 0;
      if (seg) length = Math.sqrt(Math.pow(seg[3] - seg[1], 2) + Math.pow(seg[4] - seg[2], 2));
      else {
        if (!probe) { probe = document.createElementNS('http://www.w3.org/2000/svg', 'path'); mark.parentNode.appendChild(probe); }
        probe.setAttribute('d', part);
        try { length = probe.getTotalLength(); } catch (err) { length = 0; }
      }
      if (length > longest) longest = length;
    });
    if (probe && probe.parentNode) probe.parentNode.removeChild(probe);
    return longest || total;
  }
  // One stage: every mark it holds, in the order the plate drew them.
  function drawStage(run, groups) {
    var marks = [];
    groups.forEach(function (group) {
      group.classList.add('is-drawn');
      var glide = glideOf(group);
      if (glide && group.animate) {
        run.anims.push(group.animate([
          { transform: 'translate(' + glide[0] + 'px, ' + glide[1] + 'px)' },
          { transform: 'translate(0px, 0px)' }
        ], { duration: 980, easing: 'cubic-bezier(0.65, 0, 0.35, 1)', fill: 'backwards' }));
        return;
      }
      Array.prototype.forEach.call(group.querySelectorAll('path, line, polyline, polygon, circle, ellipse, rect, text'), function (mark) {
        // The technical marks are hidden while the story is told.
        if (!(mark.closest && mark.closest('.pl-tech'))) marks.push(mark);
      });
    });
    var hot = plateInk(run.svg, '--pl-hot', '#c5533f');
    var glow = plateInk(run.svg, '--pl-glow', 'transparent');
    var spread = Math.min(560, marks.length * 46);
    marks.forEach(function (mark, i) {
      if (!mark.animate) return;
      var delay = marks.length > 1 ? Math.round(spread * i / (marks.length - 1)) : 0;
      var style = window.getComputedStyle(mark);
      var stroked = mark.tagName.toLowerCase() !== 'text' && style.stroke && style.stroke !== 'none' &&
        (!style.strokeDasharray || style.strokeDasharray === 'none') && typeof mark.getTotalLength === 'function';
      var length = 0;
      if (stroked) length = strokeRun(mark);
      var animation;
      if (length > 0.5) {
        var key = /--key\b/.test(mark.getAttribute('class') || '');
        mark.style.strokeDasharray = length + ' ' + length;
        run.dashed.push(mark);
        if (key) {
          // Burned in: the ember arrives hot and cools to its ink.
          var ink = style.stroke;
          animation = mark.animate([
            { strokeDashoffset: length, stroke: hot, filter: 'drop-shadow(0 0 1.6px ' + glow + ')' },
            { strokeDashoffset: 0, stroke: hot, filter: 'drop-shadow(0 0 1.6px ' + glow + ')', offset: 0.62 },
            { strokeDashoffset: 0, stroke: ink, filter: 'drop-shadow(0 0 0px ' + glow + ')' }
          ], { duration: EMBER_MS * 1.6, delay: delay, easing: 'cubic-bezier(0.45, 0.05, 0.2, 1)', fill: 'backwards' });
        } else {
          animation = mark.animate([{ strokeDashoffset: length }, { strokeDashoffset: 0 }],
            { duration: EMBER_MS, delay: delay, easing: 'cubic-bezier(0.45, 0.05, 0.2, 1)', fill: 'backwards' });
        }
      } else {
        // Points, numerals and grounds are set: they rise into place.
        var point = /^(circle|ellipse)$/i.test(mark.tagName) && !/pl-ring|pl-ground|pl-ref/.test(mark.getAttribute('class') || '');
        if (point) {
          mark.style.transformBox = 'fill-box';
          mark.style.transformOrigin = 'center';
          run.dashed.push(mark);
        }
        animation = mark.animate(point
          ? [{ opacity: 0, transform: 'scale(0.3)' }, { opacity: 1, transform: 'scale(1)' }]
          : [{ opacity: 0 }, { opacity: 1 }],
          { duration: point ? 520 : 460, delay: delay + (point ? 0 : 120), easing: 'cubic-bezier(0.16, 1, 0.3, 1)', fill: 'backwards', composite: 'replace' });
      }
      run.anims.push(animation);
    });
  }
  function stopStory() {
    var run = story;
    story = null;
    if (!run) return;
    run.timers.forEach(function (timer) { clearTimeout(timer); });
    run.anims.forEach(function (animation) { try { animation.cancel(); } catch (err) {} });
    run.dashed.forEach(function (mark) {
      mark.style.strokeDasharray = '';
      mark.style.transformBox = '';
      mark.style.transformOrigin = '';
    });
    stageGroups(run.svg).forEach(function (group) { group.classList.remove('is-drawn'); group.classList.remove('is-retired'); });
    run.svg.classList.remove('is-pending');
    run.slide.classList.remove('is-telling');
    run.beats.forEach(function (beat) { beat.classList.remove('is-reading'); beat.classList.remove('is-read'); });
    syncReplay(run.slide);
  }
  function playStory(slide) {
    stopStory();
    if (reduceMotion || overview || root.getAttribute('data-results-mode') === 'technical') return;
    var svg = plateOf(slide);
    var groups = stageGroups(svg);
    if (!svg || !svg.animate || !groups.length) return;
    var numbers = [];
    groups.forEach(function (group) {
      var n = numberOf(group, 'data-stage');
      if (numbers.indexOf(n) < 0) numbers.push(n);
    });
    numbers.sort(function (a, b) { return a - b; });
    var run = { slide: slide, svg: svg, beats: beatsOf(slide), timers: [], anims: [], dashed: [] };
    story = run;
    svg.classList.add('is-pending');
    slide.classList.add('is-telling');
    syncReplay(slide);
    var at = 420;
    numbers.forEach(function (n) {
      var beat = run.beats.filter(function (b) { return numberOf(b, 'data-beat') === n; })[0];
      var mine = groups.filter(function (group) { return numberOf(group, 'data-stage') === n; });
      run.timers.push(setTimeout(function () {
        if (story !== run) return;
        markBeats(run, n);
        retireBefore(run, n);
        drawStage(run, mine);
      }, at));
      // Time to read the sentence and look at what it drew: about a quarter
      // of a second a word, never less than the drawing itself takes, and
      // at most ten seconds (a sentence can be held: click it).
      var words = beat ? (beat.textContent || '').split(/\s+/).filter(Boolean).length : 10;
      at += Math.max(EMBER_MS * 1.6 + 1400, Math.min(10000, 1600 + words * 240));
    });
    run.timers.push(setTimeout(function () { if (story === run) stopStory(); }, at));
  }
  // Scenes whose last stage has passed leave as the next stage begins.
  function retireBefore(run, n) {
    stageGroups(run.svg).forEach(function (group) {
      if (group.classList.contains('is-drawn') && untilOf(group) < n) group.classList.add('is-retired');
    });
  }
  // A sentence clicked (or chosen with Enter) holds the drawing at its
  // stage: what stood before it stands, its own stage is drawn, and the
  // story waits there until another sentence is chosen, "Skip to the end"
  // shows the whole drawing, or the result changes. With reduced motion the
  // stage simply appears, so every reader can step through the scenes.
  function stepTo(slide, n) {
    var svg = plateOf(slide);
    var groups = stageGroups(svg);
    if (!svg || !groups.length || overview || root.getAttribute('data-results-mode') === 'technical') return;
    stopStory();
    var run = { slide: slide, svg: svg, beats: beatsOf(slide), timers: [], anims: [], dashed: [], held: n };
    story = run;
    svg.classList.add('is-pending');
    slide.classList.add('is-telling');
    groups.forEach(function (group) {
      if (numberOf(group, 'data-stage') < n && standsAt(group, n)) group.classList.add('is-drawn');
    });
    markBeats(run, n);
    var mine = groups.filter(function (group) { return numberOf(group, 'data-stage') === n; });
    if (reduceMotion || !svg.animate) mine.forEach(function (group) { group.classList.add('is-drawn'); });
    else drawStage(run, mine);
    syncReplay(slide);
  }
  // Play when the plate is on screen, once per opening.
  var seenObserver = null;
  function playWhenSeen(slide) {
    if (reduceMotion || !plateOf(slide)) return;
    var Observer = window.IntersectionObserver;
    if (typeof Observer !== 'function') { playStory(slide); return; }
    if (seenObserver) seenObserver.disconnect();
    seenObserver = new Observer(function (records) {
      records.forEach(function (record) {
        if (!record.isIntersecting) return;
        seenObserver.disconnect();
        if (slides[index] === slide && !overview) playStory(slide);
      });
    }, { threshold: 0.35 });
    seenObserver.observe(plateOf(slide));
  }
  // "Replay" under a story's sentences; while it plays it skips to the end.
  function syncReplay(slide) {
    var button = slide && slide.querySelector ? slide.querySelector('[data-results-replay]') : null;
    if (!button) return;
    var telling = !!(story && story.slide === slide);
    button.textContent = telling ? (reduceMotion ? 'Show the whole drawing' : 'Skip to the end') : 'Replay';
    button.setAttribute('aria-label', telling ? 'Show the whole drawing now' : 'Draw the figure again, stage by stage');
    button.hidden = reduceMotion && !telling;
  }
  slides.forEach(function (slide) {
    var svg = plateOf(slide);
    if (!stageGroups(svg).length) return;
    var words = slide.querySelector('.home-result-plate__intuitive');
    if (words && words.parentNode && typeof document.createElement === 'function') {
      var replay = document.createElement('button');
      replay.type = 'button';
      replay.className = 'home-result-plate__replay';
      replay.setAttribute('data-results-replay', '');
      replay.addEventListener('click', function () {
        if (story && story.slide === slide) stopStory(); else playStory(slide);
      });
      words.parentNode.insertBefore(replay, words.nextSibling);
      syncReplay(slide);
    }
    beatsOf(slide).forEach(function (beat) {
      var n = numberOf(beat, 'data-beat');
      function trace(on) {
        if (story && story.slide === slide) return;
        svg.classList.toggle('is-tracing', on);
        beat.classList.toggle('is-traced', on);
        stageGroups(svg).forEach(function (group) {
          group.classList.toggle('is-at', on && standsAt(group, n));
          group.classList.toggle('is-traced', on && numberOf(group, 'data-stage') === n);
        });
      }
      beat.setAttribute('tabindex', '0');
      beat.setAttribute('role', 'button');
      beat.setAttribute('data-step', '');
      beat.addEventListener('click', function () { trace(false); stepTo(slide, n); });
      beat.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); trace(false); stepTo(slide, n); }
      });
      beat.addEventListener('pointerenter', function () { trace(true); });
      beat.addEventListener('pointerleave', function () { trace(false); });
    });
  });

  /* The contents (Type B reviews, 6 October 2026): every result by its
     problem and short title ("#1041" "Degree-seven counterexample"), so a
     reader can go straight to any of them; arrows and "1 / 12" said more
     existed but not what. Built from each slide's data-result-label, so the
     slides stay the one source; always visible, never a fold. It stands
     above the open result, not under it: results run from about 230 to 400px
     tall, and an index under them moved by up to 140px with each choice, so
     the next choice was never where the last one had been. Above, its place
     depends on the window and the labels alone, and a choice opens the
     result below it with no scroll. The entries run across the rows, in the
     order the arrows and the count walk them. */
  var entries = [];
  var labelled = slides.every(function (slide) { return slide.getAttribute('data-result-label'); });
  var win = root.querySelector('.home-results__window');
  if (labelled && win && win.parentNode && typeof document.createElement === 'function') {
    var contents = document.createElement('nav');
    contents.className = 'home-results__contents';
    contents.setAttribute('aria-label', 'All ' + slides.length + ' results');
    var list = document.createElement('ol');
    slides.forEach(function (slide, i) {
      var label = slide.getAttribute('data-result-label');
      var cut = label.indexOf(': ');
      var item = document.createElement('li');
      var entry = document.createElement('button');
      entry.type = 'button';
      entry.className = 'home-results__entry';
      if (slide.id) entry.setAttribute('aria-controls', slide.id);
      var num = document.createElement('span');
      num.className = 'home-results__entry-num';
      num.textContent = cut > 0 ? label.slice(0, cut) : '';
      var name = document.createElement('span');
      name.className = 'home-results__entry-name';
      name.textContent = cut > 0 ? label.slice(cut + 2) : label;
      var drawing = plateOf(slide);
      if (drawing) {
        var figure = drawing.cloneNode(true);
        // SVG masks, hatch patterns and accessibility ids must stay unique
        // when the same plate also appears in the enlarged result below.
        var ids = {};
        Array.prototype.forEach.call(figure.querySelectorAll('[id]'), function (node) {
          ids[node.id] = 'overview-' + node.id;
          node.id = ids[node.id];
        });
        Array.prototype.forEach.call(figure.querySelectorAll('*'), function (node) {
          Array.prototype.slice.call(node.attributes).forEach(function (attr) {
            var value = attr.value.replace(/url\(#([^)]*)\)/g, function (match, id) {
              return ids[id] ? 'url(#' + ids[id] + ')' : match;
            });
            if (attr.name === 'href' || attr.name === 'xlink:href') {
              if (ids[value.slice(1)]) value = '#' + ids[value.slice(1)];
            }
            if (value !== attr.value) node.setAttribute(attr.name, value);
          });
        });
        figure.removeAttribute('aria-labelledby');
        figure.removeAttribute('aria-describedby');
        figure.setAttribute('aria-hidden', 'true');
        figure.setAttribute('focusable', 'false');
        var preview = document.createElement('span');
        preview.className = 'home-results__preview';
        preview.hidden = true;
        preview.appendChild(figure);
        entry.appendChild(preview);
      }
      entry.appendChild(num);
      entry.appendChild(name);
      entry.addEventListener('click', function () {
        var wasOverview = overview;
        var change = function () {
          setOverview(false, false);
          show(i, true);
          if (wasOverview) {
            // A figure opens into its own reading; focus follows it instead
            // of remaining on a thumbnail which has just disappeared.
            slides[i].tabIndex = -1;
            slides[i].focus({ preventScroll: true });
          }
        };
        var turn = wasOverview ? morph(thumbOf(i), change, function () { return plateOf(slides[i]); }) : null;
        if (!turn) change();
        afterTurn(turn, slides[i]);
      });
      item.appendChild(entry);
      list.appendChild(item);
      entries.push(entry);
    });
    contents.appendChild(list);
    win.parentNode.insertBefore(contents, win);
    // Only offer the all-figure view when the source build contains every
    // plate. A partially integrated edition keeps the existing text index.
    if (entries.every(function (entry) { return entry.querySelector('.home-results__preview'); })) {
      root.classList.add('has-overview');
      views = document.createElement('div');
      views.className = 'home-results__views';
      views.setAttribute('role', 'group');
      views.setAttribute('aria-label', 'Results view');
      [['overview', 'All eight'], ['focus', 'One result']].forEach(function (choice) {
        var button = document.createElement('button');
        button.type = 'button';
        button.className = 'home-results__view';
        button.setAttribute('data-results-view', choice[0]);
        button.textContent = choice[1];
        button.addEventListener('click', function () {
          var toOverview = choice[0] === 'overview';
          if (toOverview === overview) return;
          var change = function () { setOverview(toOverview, true); };
          var turn = toOverview
            ? morph(plateOf(slides[index]), change, function () { return thumbOf(index); })
            : morph(thumbOf(index), change, function () { return plateOf(slides[index]); });
          if (!turn) change();
          if (!toOverview) afterTurn(turn, slides[index]);
        });
        views.appendChild(button);
        overviewButtons.push(button);
      });
      overviewControl = overviewButtons[0];
      root.querySelector('.home-results__controls').insertBefore(views, prev);
    }
  }
  function thumbOf(i) {
    var entry = entries[i];
    return entry && entry.querySelector ? entry.querySelector('.home-results__preview svg') : null;
  }

  /* Between the eight and the one, the chosen drawing travels: the
     thumbnail grows into the plate, or the plate settles back into its
     place among the eight, while the band's head and the page stay where
     they are (Will, 6 October 2026: switching "should surely stay within the
     same space on the website, so it's not, like, moving"). A browser
     without view transitions, or a reader asking for less motion, gets the
     change at once. */
  function morph(from, change, target) {
    if (reduceMotion || !from || typeof document.startViewTransition !== 'function') return null;
    from.style.viewTransitionName = 'result-plate';
    var turn;
    try {
      turn = document.startViewTransition(function () {
        from.style.viewTransitionName = '';
        change();
        var to = target();
        if (to) to.style.viewTransitionName = 'result-plate';
      });
    } catch (err) {
      from.style.viewTransitionName = '';
      return null;
    }
    var clear = function () { var to = target(); if (to) to.style.viewTransitionName = ''; };
    turn.finished.then(clear, clear);
    return turn;
  }
  function afterTurn(turn, slide) {
    if (turn && turn.finished) turn.finished.then(function () { playWhenSeen(slide); }, function () { playWhenSeen(slide); });
    else playWhenSeen(slide);
  }

  // A thumbnail shows the drawing, not its sheet (7 October 2026; Will: the
  // eight were "not lined up and arranged nicely"). Each plate leaves its own
  // margins on its 720 by 500 sheet, and the overview hides its labels, so a
  // thumbnail of the whole sheet floated its drawing at a different place in
  // every cell. Once the thumbnail is shown, its viewBox closes on what it
  // draws, with one even margin, and the drawing stands on the cell's bottom
  // edge, so the eight share a baseline above their names.
  function cropPreview(svg) {
    if (!svg || svg.getAttribute('data-cropped') || typeof svg.getBBox !== 'function') return;
    var box;
    try { box = svg.getBBox(); } catch (err) { return; }
    if (!box || box.width < 24 || box.height < 24) return;
    var pad = 0.035 * Math.max(box.width, box.height);
    var round = function (v) { return Math.round(v * 10) / 10; };
    svg.setAttribute('viewBox', [round(box.x - pad), round(box.y - pad), round(box.width + 2 * pad), round(box.height + 2 * pad)].join(' '));
    svg.setAttribute('preserveAspectRatio', 'xMidYMax meet');
    svg.setAttribute('data-cropped', '');
  }
  function setOverview(on, updateHash) {
    overview = !!on && root.classList.contains('has-overview');
    if (overview) stopStory();
    root.classList.toggle('is-overview', overview);
    entries.forEach(function (entry) {
      var preview = entry.querySelector('.home-results__preview');
      if (preview) preview.hidden = !overview;
      if (preview && overview) cropPreview(preview.querySelector('svg'));
    });
    if (win) win.hidden = overview;
    prev.hidden = next.hidden = overview;
    overviewButtons.forEach(function (button) {
      button.setAttribute('aria-pressed', (button.getAttribute('data-results-view') === 'overview') === overview ? 'true' : 'false');
    });
    if (count) count.textContent = overview ? slides.length + ' problems' : (index + 1) + ' / ' + slides.length;
    if (updateHash && window.history && window.history.replaceState) {
      window.history.replaceState(null, '', '#' + (overview ? 'result-overview' : slides[index].id));
    }
  }

  function show(target, updateHash) {
    var from = index;
    var focusedReading = slides[from] === document.activeElement;
    index = (target + slides.length) % slides.length;
    if (index !== from) stopStory();
    // A turn the reader made draws the new statement's rule down like a pen
    // (style.css, .is-turned); the first result at load arrives still.
    if (updateHash && index !== from) root.classList.add('is-turned');
    slides.forEach(function (slide, i) {
      var on = i === index;
      slide.classList.toggle('is-active', on);
      slide.setAttribute('aria-hidden', on ? 'false' : 'true');
      if ('inert' in slide) slide.inert = !on;
    });
    if (focusedReading && index !== from) {
      slides[index].tabIndex = -1;
      slides[index].focus({ preventScroll: true });
    }
    entries.forEach(function (entry, i) {
      if (i === index) entry.setAttribute('aria-current', 'true');
      else entry.removeAttribute('aria-current');
    });
    if (count) count.textContent = overview ? slides.length + ' problems' : (index + 1) + ' / ' + slides.length;
    if (updateHash && slides[index].id && window.history && window.history.replaceState) {
      window.history.replaceState(null, '', '#' + slides[index].id);
    }
  }
  function fromHash() {
    var id = window.location.hash.slice(1);
    if (!id) return false;
    if (id === 'result-overview' && overviewControl) {
      setOverview(true, false);
      root.scrollIntoView({ block: 'start', behavior: 'auto' });
      return true;
    }
    // Results that left the band when it became one per problem keep their
    // fragments: each opens its problem's result (data-result-aliases).
    var target = slides.findIndex(function (slide) {
      return slide.id === id || (' ' + (slide.getAttribute('data-result-aliases') || '') + ' ').indexOf(' ' + id + ' ') >= 0;
    });
    if (target >= 0) {
      setOverview(false, false);
      show(target, false);
      root.scrollIntoView({ block: 'start', behavior: 'auto' });
      playWhenSeen(slides[target]);
    }
    return target >= 0;
  }
  function turnTo(target) {
    show(target, true);
    playWhenSeen(slides[index]);
  }
  prev.addEventListener('click', function () { turnTo(index - 1); });
  next.addEventListener('click', function () { turnTo(index + 1); });
  // Arrows page the results from anywhere in the band except a control that
  // names a result of its own: with focus on "#243 Cubic-rate
  // irrationality", an arrow that opened #1049 would leave focus naming one
  // result and the page showing another. The contents are plain buttons
  // (Tab moves, Enter or Space opens); the arrows and the count keep theirs.
  root.addEventListener('keydown', function (event) {
    if (overview || (event.target.closest && event.target.closest('[data-results-view], button[data-results-mode]'))) return;
    if (event.target && (/^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName) || event.target.isContentEditable || (event.target.closest && event.target.closest('a, .home-results__contents, [data-results-theorem], [data-results-replay]')))) return;
    if (event.key === 'ArrowRight') { event.preventDefault(); turnTo(index + 1); }
    else if (event.key === 'ArrowLeft') { event.preventDefault(); turnTo(index - 1); }
    else if (event.key === 'Home') { event.preventDefault(); turnTo(0); }
    else if (event.key === 'End') { event.preventDefault(); turnTo(slides.length - 1); }
  });
  var start = null;
  track.addEventListener('pointerdown', function (event) {
    if (event.pointerType === 'mouse' || (event.target.closest && event.target.closest('a, button, select'))) return;
    start = { x: event.clientX, y: event.clientY };
  }, { passive: true });
  track.addEventListener('pointercancel', function () { start = null; }, { passive: true });
  track.addEventListener('pointerup', function (event) {
    if (!start) return;
    var dx = event.clientX - start.x, dy = event.clientY - start.y;
    start = null;
    if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.5) turnTo(index + (dx < 0 ? 1 : -1));
  }, { passive: true });
  window.addEventListener('hashchange', fromHash);
  show(0, false);
  if (!fromHash()) setOverview(true, false);
})();

/* Credit ledger frame (2026-10-05). The entries stand side by side in Will's
   fixed frame ("it stays in that frame and then you can scroll through them,
   but the frame stays the same"), showing whole entries, two at a time on a
   wide screen. The arrows page by what the frame shows and the count names the
   entries in view; the frame itself stays focusable, so arrow keys, a
   trackpad or a swipe scroll it natively. Without this script the frame keeps
   its thin scrollbar and the arrows stay hidden. */
(function () {
  var frame = document.getElementById('credit-list');
  var controls = document.querySelector('[data-credit-controls]');
  if (!frame || !controls || !frame.querySelectorAll) return;
  var items = Array.prototype.slice.call(frame.querySelectorAll('.home-credit-entry'));
  var prev = controls.querySelector('[data-credit-prev]');
  var next = controls.querySelector('[data-credit-next]');
  var count = controls.querySelector('[data-credit-count]');
  if (items.length < 2 || !prev || !next || !count) return;
  controls.hidden = false;
  frame.classList.add('is-live');

  function update() {
    var box = frame.getBoundingClientRect();
    var first = -1, last = -1;
    items.forEach(function (item, i) {
      var r = item.getBoundingClientRect();
      if (r.left >= box.left - 4 && r.right <= box.right + 4) {
        if (first < 0) first = i;
        last = i;
      }
    });
    if (first < 0) return;
    count.textContent = (first === last ? String(first + 1) : (first + 1) + '–' + (last + 1)) + ' of ' + items.length;
    prev.disabled = first === 0;
    next.disabled = last === items.length - 1;
  }
  function page(direction) {
    var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    frame.scrollBy({ left: direction * frame.clientWidth, behavior: still ? 'auto' : 'smooth' });
  }
  prev.addEventListener('click', function () { page(-1); });
  next.addEventListener('click', function () { page(1); });
  var pending = 0;
  function soon() {
    if (pending) return;
    pending = window.requestAnimationFrame(function () { pending = 0; update(); });
  }
  frame.addEventListener('scroll', soon, { passive: true });
  window.addEventListener('resize', soon);
  update();
})();

/* The map band (2026-10-04). Will asked for an arrow that "scrolls that
   horizontal slice, from left to right, all the way wall to wall ... bounded
   of where the map is", and a switch between "system versus maths" that
   "animatedly moves that away". The band holds two drawings in a track as
   wide as the window: the mathematics (the eight problems beside the universe
   map) and the system (the earlier software's components beside their
   drawing).

   - A click on the switch or an edge arrow moves the whole slice in one eased
     move (620ms on --atlas-ease, which leaves at once and settles slowly: a
     camera move across a full window, inside the budget for a data graphic).
     Each drawing travels a little further
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
  // 620ms on a curve that leaves at once (cubic-bezier(0.45, 0, 0.2, 1)): the
  // symmetric ease it replaced held the slice within 26px for the first tenth
  // of a second, so the click felt ignored (critique, 5 October 2026).
  var MOVE_MS = 620;
  var MOVE_EASE = 'cubic-bezier(0.45, 0, 0.2, 1)';
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
    var timing = { duration: MOVE_MS, easing: MOVE_EASE };
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
    // While the slice moves the edge arrows step out, so neither stands over
    // the text of a slide passing beneath it.
    band.classList.toggle('is-moving', !instant);
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
      band.classList.remove('is-moving');
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
