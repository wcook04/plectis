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

  function align(target) {
    if (!target || typeof window.requestAnimationFrame !== 'function') return;
    var anchor = target;
    if (target.tagName === 'DETAILS' && target.querySelector) {
      anchor = target.querySelector('summary') || target;
    }
    if (!anchor || typeof anchor.scrollIntoView !== 'function') return;
    var frames = 2;
    var tick = function () {
      frames -= 1;
      try { anchor.scrollIntoView({ block: 'start', inline: 'nearest' }); }
      catch (e) { try { anchor.scrollIntoView(); } catch (e2) {} }
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

  if (reveal()) return;
  if (!targetId()) return;

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
})();
