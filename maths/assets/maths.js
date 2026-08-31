/* Plectis — maths subsite runtime.
   Small on purpose: the docs runtime (docs.js) is not loaded on maths pages,
   so this file carries the two behaviours the chrome needs — the theme
   toggle and the mobile sidebar drawer — with the same storage key,
   attributes, and markup the docs runtime uses, so the control looks and
   acts identically across subsites. Everything else on maths pages is
   static HTML; the universe canvas has its own file. */
(function () {
  'use strict';

  var KEY = 'plectis-theme';
  var root = document.documentElement;
  var mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;

  function stored() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function resolved() {
    var s = stored();
    if (s === 'dark' || s === 'light') return s;
    return mq && mq.matches ? 'dark' : 'light';
  }
  function apply(theme) {
    root.setAttribute('data-theme', theme);
    try { root.style.colorScheme = theme; } catch (e) {}
    if (toggle) toggle.setAttribute('aria-checked', theme === 'dark' ? 'true' : 'false');
    document.dispatchEvent(new CustomEvent('plectis:theme', { detail: theme }));
  }

  /* Same control the docs runtime injects, appended to the topbar links. */
  var toggle = null;
  function mountToggle() {
    var nav = document.querySelector('.docs-topbar__links');
    if (!nav || nav.querySelector('.theme-toggle')) return;
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'theme-toggle';
    btn.setAttribute('role', 'switch');
    btn.setAttribute('aria-label', 'Dark mode');
    btn.innerHTML =
      '<span class="theme-toggle__track" aria-hidden="true">' +
      '<span class="theme-toggle__ico theme-toggle__ico--sun"></span>' +
      '<span class="theme-toggle__ico theme-toggle__ico--moon"></span>' +
      '<span class="theme-toggle__knob"></span>' +
      '</span>';
    btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(KEY, next); } catch (e) {}
      apply(next);
    });
    nav.appendChild(btn);
    toggle = btn;
    apply(resolved());
  }

  /* Follow OS changes only while the reader has not chosen explicitly. */
  if (mq && mq.addEventListener) {
    mq.addEventListener('change', function () {
      if (stored() !== 'dark' && stored() !== 'light') apply(resolved());
    });
  }

  function mountDrawer() {
    var btn = document.querySelector('.docs-menu-btn');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var open = document.body.classList.toggle('nav-open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    /* A tap on a sidebar link should close the drawer it navigated from. */
    var sidebar = document.querySelector('.docs-sidebar');
    if (sidebar) {
      sidebar.addEventListener('click', function (event) {
        var target = event.target;
        if (target && target.closest && target.closest('a')) {
          document.body.classList.remove('nav-open');
          btn.setAttribute('aria-expanded', 'false');
        }
      });
    }
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && document.body.classList.contains('nav-open')) {
        document.body.classList.remove('nav-open');
        btn.setAttribute('aria-expanded', 'false');
        btn.focus();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      mountToggle();
      mountDrawer();
    });
  } else {
    mountToggle();
    mountDrawer();
  }
})();
