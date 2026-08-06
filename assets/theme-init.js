/* Pre-paint theme apply. Loaded as a blocking <script src> in <head> so the
   saved (or system) theme is stamped on <html> before first paint — a returning
   visitor who chose a non-system theme never sees a flash of the other one.
   Tiny and dependency-free on purpose; the header toggle itself lives in
   docs.js. Keep the storage key ('plectis-theme') in sync with docs.js. */
(function () {
  try {
    var s = localStorage.getItem('plectis-theme');
    var dark = s === 'dark' ||
      (s !== 'light' && window.matchMedia &&
       window.matchMedia('(prefers-color-scheme: dark)').matches);
    var t = dark ? 'dark' : 'light';
    var root = document.documentElement;
    root.setAttribute('data-theme', t);
    root.style.colorScheme = t;
  } catch (e) {}
})();
