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
})();
