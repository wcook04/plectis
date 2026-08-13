/* Deep-link opener for the generated docs pages.

   Every docs page is static HTML, and this runs before <body> has parsed, so
   the first lookup necessarily misses and the reveal has to be retried as the
   document streams in. Two rules keep those retries from becoming a nuisance:

   - The reader wins. Any wheel, touch, key or pointer input retires the whole
     mechanism at once. A realignment landing 420ms after someone has started
     reading is not a correction, it is the page pulling them back. The align
     loop's own scrollTo fires scroll events, so scroll itself cannot be the
     signal — the four input events are.
   - The observer is bounded. A hash that never resolves (a renamed section, a
     stale link in an old email) used to leave a childList+subtree observer on
     documentElement for the life of the session, re-running the lookup on every
     mutation the shared docs runtime later makes. It now retires on a deadline,
     and the whole opener retires once the page has settled. */
(function () {
  'use strict';

  var alignRaf = 0;
  var framesLeft = 0;
  var anchorEl = null;
  var observer = null;
  var timers = [];
  var stopped = false;
  var placedY = -1;

  function targetId() {
    var hash = window.location && window.location.hash;
    if (!hash || hash.charAt(0) !== '#') return '';
    try { return decodeURIComponent(hash.slice(1)); }
    catch (e) { return hash.slice(1); }
  }

  function openAncestors(target) {
    var node = target;
    while (node && node.nodeType === 1) {
      if (node.tagName === 'DETAILS') node.open = true;
      node = node.parentNode;
    }
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

  function scrollY() {
    return window.pageYOffset || document.documentElement.scrollTop || 0;
  }

  function scrollToAnchor(anchor) {
    if (!anchor) return;
    if (typeof anchor.getBoundingClientRect === 'function' && typeof window.scrollTo === 'function') {
      var y = anchor.getBoundingClientRect().top + scrollY() - scrollPaddingTop();
      window.scrollTo(0, Math.max(0, y));
      return;
    }
    if (typeof anchor.scrollIntoView === 'function') {
      try { anchor.scrollIntoView({ block: 'start', inline: 'nearest' }); }
      catch (e) { try { anchor.scrollIntoView(); } catch (e2) {} }
    }
  }

  var INTERRUPTS = ['wheel', 'touchstart', 'pointerdown', 'keydown'];

  function onInterrupt() { stop(); }

  function attachInterrupts() {
    for (var i = 0; i < INTERRUPTS.length; i += 1) {
      window.addEventListener(INTERRUPTS[i], onInterrupt, { passive: true, capture: true });
    }
  }

  function detachInterrupts() {
    for (var i = 0; i < INTERRUPTS.length; i += 1) {
      window.removeEventListener(INTERRUPTS[i], onInterrupt, true);
    }
  }

  function stop() {
    if (stopped) return;
    stopped = true;
    if (alignRaf) { window.cancelAnimationFrame(alignRaf); alignRaf = 0; }
    framesLeft = 0;
    anchorEl = null;
    if (observer) { observer.disconnect(); observer = null; }
    for (var i = 0; i < timers.length; i += 1) window.clearTimeout(timers[i]);
    timers.length = 0;
    detachInterrupts();
  }

  /* Late layout — a disclosure opening, a wide table settling — moves the
     target after the first placement, so the alignment is held for a few
     frames. It is abandoned the moment the page has moved by more than a
     rounding wobble since this loop last placed it, because then something
     other than this loop is driving the scroll. */
  function tick() {
    alignRaf = 0;
    if (stopped || !anchorEl) return;
    if (placedY >= 0 && Math.abs(scrollY() - placedY) > 4) { stop(); return; }
    framesLeft -= 1;
    scrollToAnchor(anchorEl);
    placedY = scrollY();
    if (framesLeft > 0) alignRaf = window.requestAnimationFrame(tick);
  }

  function align(target) {
    if (stopped || !target || typeof window.requestAnimationFrame !== 'function') return;
    var anchor = target;
    if (target.tagName === 'DETAILS' && target.querySelector) {
      anchor = target.querySelector('summary') || target;
    }
    anchorEl = anchor;
    framesLeft = 4;
    if (alignRaf) window.cancelAnimationFrame(alignRaf);
    alignRaf = window.requestAnimationFrame(tick);
  }

  function reveal() {
    if (stopped) return false;
    var id = targetId();
    if (!id) return false;
    var target = document.getElementById(id);
    if (!target) return false;
    openAncestors(target);
    align(target);
    return true;
  }

  if (!targetId()) return;
  attachInterrupts();
  reveal();

  if ('MutationObserver' in window) {
    observer = new MutationObserver(function () {
      if (reveal() && observer) { observer.disconnect(); observer = null; }
    });
    observer.observe(document.documentElement || document, {
      childList: true,
      subtree: true
    });
    timers.push(window.setTimeout(function () {
      if (observer) { observer.disconnect(); observer = null; }
    }, 4000));
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (reveal() && observer) { observer.disconnect(); observer = null; }
  }, { once: true });
  window.addEventListener('load', function () { reveal(); }, { once: true });
  timers.push(window.setTimeout(reveal, 120));
  timers.push(window.setTimeout(reveal, 420));
  /* The page has arrived by now. Release the input listeners rather than
     leaving four capture-phase handlers on every docs page for the session. */
  timers.push(window.setTimeout(stop, 800));
})();
