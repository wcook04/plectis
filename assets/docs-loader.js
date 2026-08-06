/* Plectis documentation runtime scheduler.

   The generated documentation is complete HTML: links, disclosures, source
   references, and every paragraph work before JavaScript. The shared docs.js
   runtime adds search, exact-return state, copy/export controls, maps, and term
   previews, but it is large enough that downloading and compiling it before
   DOMContentLoaded makes every docs route wait for controls the reader may not
   use.

   This small scheduler keeps that full runtime intact while moving it after the
   initial load. Real intent starts it immediately. A genuinely early enhanced
   click is replayed after activation; ordinary links remain native and receive
   the same bounded return-trail seed that docs.js would write on pagehide. If
   the runtime fails, links and disclosures remain the plain-HTML fallback. */
(function () {
  'use strict';

  var doc = document;
  var root = doc.documentElement;
  if (!doc.querySelector || !doc.createElement || !doc.body) return;

  var template = doc.querySelector('template[data-plectis-runtime="docs"]');
  var ref = template && template.content && template.content.querySelector('script[src]');
  var runtimeSrc = ref && ref.getAttribute('src');
  if (!runtimeSrc) return;

  var state = 'staged';
  var callbacks = [];
  var pendingHover = null;
  var replaying = false;

  function mark(next) {
    state = next;
    root.setAttribute('data-plectis-docs-runtime', next);
  }

  function flush() {
    var queued = callbacks.slice();
    callbacks = [];
    queued.forEach(function (callback) {
      try { callback(state); } catch (e) {}
    });
  }

  function removeIntentListeners() {
    doc.removeEventListener('mouseover', onIntent, true);
    doc.removeEventListener('focusin', onIntent, true);
    doc.removeEventListener('pointerdown', onIntent, true);
    doc.removeEventListener('keydown', onIntent, true);
    doc.removeEventListener('click', onClick, true);
  }

  function replayHover() {
    var target = pendingHover;
    pendingHover = null;
    if (!target || !target.matches) return;
    var active = doc.activeElement === target;
    var hovered = false;
    try { hovered = target.matches(':hover'); } catch (e) {}
    if (!active && !hovered) return;
    try {
      target.dispatchEvent(new MouseEvent('mouseover', { bubbles: true }));
    } catch (e) {}
  }

  function activate(callback) {
    if (callback) callbacks.push(callback);
    if (state === 'ready' || state === 'failed') {
      flush();
      return;
    }
    if (state === 'loading') return;

    mark('loading');
    var script = doc.createElement('script');
    script.src = runtimeSrc;
    script.async = true;
    script.setAttribute('data-plectis-runtime-active', 'docs');
    script.addEventListener('load', function () {
      mark('ready');
      removeIntentListeners();
      replayHover();
      flush();
    }, { once: true });
    script.addEventListener('error', function () {
      mark('failed');
      removeIntentListeners();
      flush();
    }, { once: true });
    doc.body.appendChild(script);
  }

  function closestAction(target) {
    if (!target || !target.closest) return null;
    return target.closest('a[href], button, summary, [role="button"]');
  }

  function isTerm(anchor) {
    return !!(anchor && anchor.matches &&
      anchor.matches('a.narrative-ref--term[data-term]'));
  }

  function cleanText(value) {
    return String(value || '').replace(/\s+/g, ' ').trim();
  }

  /* docs.js normally snapshots on pagehide. If an ordinary link is activated
     before it has loaded, seed the same bounded stack without delaying native
     navigation. Once ready, docs.js replaces this same-path row rather than
     adding a duplicate. */
  function primeNavigationTrail(anchor) {
    if (!anchor || state === 'ready') return;
    var raw = anchor.getAttribute('href') || '';
    var target;
    try { target = new URL(raw, window.location.href); } catch (e) { return; }
    if (target.origin !== window.location.origin ||
        target.pathname === window.location.pathname) return;

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
      for (var i = 0; i < details.length; i += 1) open.push(details[i].id);
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

  function replayClick(target, anchor) {
    window.setTimeout(function () {
      replaying = true;
      try {
        if (state === 'failed' && anchor) {
          window.location.href = anchor.href;
        } else {
          target.click();
        }
      } catch (e) {
        if (anchor) window.location.href = anchor.href;
      }
      replaying = false;
    }, 0);
  }

  function onIntent(event) {
    if (state === 'ready' || state === 'failed') return;
    var target = closestAction(event.target);
    if (!target) return;
    var anchor = target.closest && target.closest('a[href]');
    var href = (anchor && (anchor.getAttribute('href') || '')) || '';
    if (href.charAt(0) === '#') return;
    if ((event.type === 'mouseover' || event.type === 'focusin') && isTerm(anchor)) {
      pendingHover = anchor;
    }
    activate();
  }

  function onClick(event) {
    if (replaying || state === 'ready' || state === 'failed') return;
    var target = closestAction(event.target);
    if (!target) return;
    var anchor = target.closest && target.closest('a[href]');

    /* Modified and non-primary activations keep their native new-tab/download
       semantics. Pointer intent has already started the runtime when possible. */
    if (event.button !== 0 || event.metaKey || event.ctrlKey ||
        event.shiftKey || event.altKey) {
      activate();
      return;
    }

    /* Plain links should never feel slower because enhancement is cold. Term
       links and buttons are different: their first activation has a local
       preview/control contract, so hold that one click and replay it against
       the full runtime. */
    if (anchor && !isTerm(anchor)) {
      primeNavigationTrail(anchor);
      activate();
      return;
    }
    if (!isTerm(anchor) && target.tagName !== 'BUTTON' &&
        target.getAttribute('role') !== 'button') return;

    event.preventDefault();
    event.stopImmediatePropagation();
    activate(function () { replayClick(target, anchor); });
  }

  function queueAfterLoad() {
    var run = function () { activate(); };
    if (window.requestIdleCallback) {
      window.requestIdleCallback(run, { timeout: 1200 });
    } else {
      window.setTimeout(run, 80);
    }
  }

  mark('staged');
  doc.addEventListener('mouseover', onIntent, true);
  doc.addEventListener('focusin', onIntent, true);
  doc.addEventListener('pointerdown', onIntent, true);
  doc.addEventListener('keydown', onIntent, true);
  doc.addEventListener('click', onClick, true);

  /* Waiting for load keeps docs.js outside the critical navigation event. The
     idle slot then warms every control before a normal reader reaches it. */
  if (doc.readyState === 'complete') queueAfterLoad();
  else window.addEventListener('load', queueAfterLoad, { once: true });
})();
