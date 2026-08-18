/* Pre-paint theme apply. Loaded as a blocking <script src> in <head> so the
   saved (or system) theme is stamped on <html> before first paint — a returning
   visitor who chose a non-system theme never sees a flash of the other one.
   Tiny and dependency-free on purpose; the header toggle itself lives in
   docs.js. Keep the storage key ('plectis-theme') in sync with docs.js. */
(function () {
  /* Only the storage read can throw (Safari private mode, blocked storage).
     Wrapping the whole body in one try meant a throw there also skipped the
     stamp, and with it style.colorScheme — so a dark-mode visitor got a light
     scrollbar and light form controls until docs.js loaded 219KB later. The
     stylesheet's :root:not([data-theme]) rules cover the page colours in that
     case; the UA-level colour scheme is what needs stamping regardless. */
  var s = null;
  try { s = localStorage.getItem('plectis-theme'); } catch (e) {}
  var dark = s === 'dark' ||
    (s !== 'light' && window.matchMedia &&
     window.matchMedia('(prefers-color-scheme: dark)').matches);
  var t = dark ? 'dark' : 'light';
  var root = document.documentElement;
  root.setAttribute('data-theme', t);
  try { root.style.colorScheme = t; } catch (e) {}

  /* Two different questions get two different flags, and conflating them costs
     something either way.
       .js       (added by docs.js)   = the shared runtime is READY.
       .scripting (added right here)  = scripting is AVAILABLE.
     The stylesheet uses .js to keep the page tools invisible until they
     actually work, so that one must stay late. But the term layer's JS-off
     fallback is the opposite: html:not(.scripting) is the one place a term link
     still draws an underline, because without JS there is no hover preview and
     the rule is the only signal the word leads to a definition. Keyed on .js it
     would paint an underline under every term on the page until docs.js ran a
     second later, then flash them all away. Stamped here, in the blocking head
     script, a reader with JS never matches the fallback at all. */
  root.classList.add('scripting');
})();
