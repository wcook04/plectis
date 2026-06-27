(function () {
  'use strict';

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

  function scrollToAnchor(anchor) {
    if (!anchor) return;
    if (typeof anchor.getBoundingClientRect === 'function' && typeof window.scrollTo === 'function') {
      var y = anchor.getBoundingClientRect().top + (window.pageYOffset || document.documentElement.scrollTop || 0) - scrollPaddingTop();
      window.scrollTo(0, Math.max(0, y));
      return;
    }
    if (typeof anchor.scrollIntoView === 'function') {
      try { anchor.scrollIntoView({ block: 'start', inline: 'nearest' }); }
      catch (e) { try { anchor.scrollIntoView(); } catch (e2) {} }
    }
  }

  function align(target) {
    if (!target || typeof window.requestAnimationFrame !== 'function') return;
    var anchor = target;
    if (target.tagName === 'DETAILS' && target.querySelector) {
      anchor = target.querySelector('summary') || target;
    }
    var frames = 4;
    var tick = function () {
      frames -= 1;
      scrollToAnchor(anchor);
      if (frames > 0) window.requestAnimationFrame(tick);
    };
    window.requestAnimationFrame(tick);
  }

  function reveal() {
    var id = targetId();
    if (!id) return false;
    var target = document.getElementById(id);
    if (!target) return false;
    openAncestors(target);
    align(target);
    return true;
  }

  if (!targetId()) return;
  reveal();

  var observer = null;
  if ('MutationObserver' in window) {
    observer = new MutationObserver(function () {
      if (reveal() && observer) observer.disconnect();
    });
    observer.observe(document.documentElement || document, {
      childList: true,
      subtree: true
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    if (reveal() && observer) observer.disconnect();
  }, { once: true });
  window.addEventListener('load', reveal, { once: true });
  window.setTimeout(reveal, 120);
  window.setTimeout(reveal, 420);
})();
