/* Resolve a legacy full-paper fragment before optional reader enhancements.
   Ordinary contents links work without JavaScript; complete HTML is explicit. */
(function () {
  'use strict';
  function arrive() {
    var id;
    try { id = decodeURIComponent(window.location.hash.slice(1)); } catch (e) { return; }
    var link = id && document.getElementById(id);
    if (!link || !link.closest('[data-paper-anchor-routes]')) return;
    // All destinations are same-origin static pages emitted with this edition.
    window.location.replace(link.href);
  }
  arrive();
  window.addEventListener('hashchange', arrive);
})();
