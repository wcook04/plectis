/* Plectis: the film map (15 October 2026).

   The Videos band is a map of films (tools/meta/dissemination/plectis_film_map.py;
   its rules are assets/film-map.css). This file makes it a place a reader can
   move through without leaving the band:

   - A film's title or still opens its reading in place of the map, under the
     same head: the still travels from the map into the reading while the rest
     crossfades (a view transition, as the results band's plate travels between
     the eight and the one in landing.js). "All videos", Escape or the browser's
     Back returns to the map exactly where the reader left it, with focus on the
     film they opened. The films next to a reading open from it the same way.
   - #film-<id> opens that reading on arrival and from any link on the page.
     The URL follows the reading, so a reading can be shared.
   - Pointing at a film, or focusing its title, lights its line from the
     introduction and steps the other lines back.
   - The lines run out from the introduction once, the first time the map comes
     into view, if it starts below the window. On screen at load, or with
     reduced motion, they are simply there.

   - On the landing's explorer (a programme with projects, film-map--home)
     the map stays beside the reading at laptop widths, as the maths Atlas
     keeps its map beside the selected object (universe.js select): the
     panel holds the introduction until another film or project is opened,
     the open one is marked on the map and its route stays lit. #project-<id>
     opens the reading the project shares with its film, or its own.

   Without this file the map is complete: every line is drawn by the stylesheet
   and every title jumps to its reading, listed under the map. Links that leave
   the site, and every link opened with a modifier key, keep their own
   behaviour. Nothing is fetched or stored. */
(function () {
  'use strict';

  var doc = document;
  var map = doc.querySelector && doc.querySelector('[data-film-map]');
  if (!map || !window.history || !map.closest) return;
  var tree = map.querySelector('[data-film-map-tree]');
  var shelf = map.querySelector('[data-film-map-readings]');
  if (!tree || !shelf) return;

  // Each reading answers to its own address (film-<id>, project-<id>) and to
  // the address of the project that shares a film's reading.
  var readings = {};
  var routes = {};
  var nodes = {};
  var home = map.classList.contains('film-map--home');
  var fallback = null;
  Array.prototype.forEach.call(shelf.querySelectorAll('[data-map-reading]'), function (li) {
    var key = li.getAttribute('data-map-reading');
    readings[key] = li;
    routes[key] = key;
    (li.getAttribute('data-map-alias') || '').split(' ').forEach(function (alias) { if (alias) routes[alias] = key; });
    if (li.hasAttribute('data-map-default')) fallback = key;
  });
  Array.prototype.forEach.call(tree.querySelectorAll('[data-map-node]'), function (li) {
    nodes[li.getAttribute('data-map-node')] = li;
  });
  var aliases = ['videos', 'demo-videos', 'video-detail-ai-lab-1m', 'video-detail-ai-lab-5m', 'video-detail-ai-lab-30m'];

  function reducedMotion() {
    try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; }
  }

  function routeOf(raw) {
    if (!raw || raw.charAt(0) !== '#') return null;
    var id;
    try { id = decodeURIComponent(raw.slice(1)); } catch (e) { id = raw.slice(1); }
    return /^(film|project)-[a-z][a-z-]*$/.test(id) && routes[id] ? id : null;
  }

  // The map stays beside the reading (the explorer at laptop widths).
  function beside() {
    if (!home) return false;
    try { return window.matchMedia('(min-width: 70em)').matches; } catch (e) { return false; }
  }

  // What is open, where the reader was on the map when they left it, and how
  // many readings this page has pushed onto the history since then.
  var open = null;
  var leftAt = null;
  var depth = 0;

  function headerClearance() {
    var pad = 0;
    try { pad = parseFloat(window.getComputedStyle(doc.documentElement).scrollPaddingTop) || 0; } catch (e) {}
    return pad;
  }

  // The reading starts where the map did; bring its top under the header
  // when the reader opened it from further down the map.
  function revealReading(li) {
    var top = li.getBoundingClientRect().top;
    var clear = headerClearance();
    if (top < clear || top > window.innerHeight * 0.4) {
      window.scrollTo(0, Math.max(0, (window.pageYOffset || 0) + top - clear - 12));
    }
  }

  function titleLink(id) {
    var node = nodes[id];
    return node ? node.querySelector('.film-map__title a') : null;
  }

  // The open reading's node is marked on the map; with nothing open, the
  // introduction's, whose reading the panel holds.
  var current = null;
  function mark(key) {
    var node = nodes[key || fallback] || null;
    if (current === node) return;
    if (current) {
      current.classList.remove('is-current');
      var was = current.querySelector('.film-map__title a');
      if (was) was.removeAttribute('aria-current');
    }
    current = node;
    if (node && home) {
      node.classList.add('is-current');
      var link = node.querySelector('.film-map__title a');
      if (link) link.setAttribute('aria-current', 'true');
    }
  }
  function mapStill(id) {
    var node = nodes[id];
    return node ? node.querySelector('.film-map__still img') : null;
  }
  function readingStill(id) {
    var li = readings[id];
    return li ? li.querySelector('.film-map__media img') : null;
  }

  /* The chosen still travels (landing.js, morph): name it in the old view,
     move the name to its counterpart in the new one. Without view transitions,
     or with reduced motion, the change is immediate. */
  function morph(from, change, target) {
    if (reducedMotion() || !from || typeof doc.startViewTransition !== 'function') { change(); return null; }
    from.style.viewTransitionName = 'film-still';
    var turn;
    try {
      turn = doc.startViewTransition(function () {
        from.style.viewTransitionName = '';
        change();
        var to = target();
        if (to) to.style.viewTransitionName = 'film-still';
      });
    } catch (err) {
      from.style.viewTransitionName = '';
      change();
      return null;
    }
    var clear = function () { var to = target(); if (to) to.style.viewTransitionName = ''; };
    turn.finished.then(clear, clear);
    return turn;
  }

  function settle(id) {
    Object.keys(readings).forEach(function (key) {
      readings[key].classList.toggle('is-open', key === id);
    });
  }

  function show(id, push, route) {
    if (id === open) {
      try { readings[id].focus({ preventScroll: true }); } catch (e) {}
      return;
    }
    var from = open ? readingStill(open) : mapStill(id);
    if (!open) leftAt = window.pageYOffset || 0;
    trace(null);
    morph(from, function () {
      map.classList.add('is-reading');
      settle(id);
      open = id;
      mark(id);
      revealReading(readings[id]);
      try { readings[id].focus({ preventScroll: true }); } catch (e) {}
      rest();
      drawBeam(true);
    }, function () { return readingStill(id); });
    if (push) {
      depth += 1;
      // The map's own entry restores its scroll here, not the browser: the
      // browser would apply the map's offset to the shorter reading page
      // before this script could close it, showing the band below for a frame.
      // scrollRestoration belongs to the current entry and is copied to the
      // pushed one; hide() hands the map's entry back to the browser.
      try { window.history.scrollRestoration = 'manual'; } catch (e) {}
      try { window.history.pushState({ filmMap: id, filmDepth: depth }, '', '#' + (route || id)); } catch (e) {}
    }
  }

  function hide(restore) {
    if (!open) return;
    var id = open;
    var back = leftAt;
    leftAt = null;
    morph(readingStill(id), function () {
      map.classList.remove('is-reading');
      settle(null);
      open = null;
      mark(null);
      rest();
      drawBeam(true);
      if (!restore) return;
      if (back !== null && !beside()) window.scrollTo(0, back);
      // Focus lands on the film's title; nudge only if that title is out of
      // sight (a reading reached directly, or a neighbour further down).
      var link = titleLink(id);
      // Beside the map the two introductions live in the panel, not on the
      // stage: focus returns to the panel's link that leads to the one just
      // closed, or to the introduction the panel shows again.
      if (link && !link.getClientRects().length) {
        var panel = fallback && readings[fallback];
        link = panel ? (panel.querySelector('a[href="#' + id + '"]') || panel) : null;
      }
      if (link) {
        var box = link.getBoundingClientRect();
        if (box.top < headerClearance() || box.bottom > window.innerHeight - 16) {
          var still = nodes[id] && nodes[id].querySelector('.film-map__still');
          if (!still || !still.getClientRects().length) still = link;
          window.scrollTo(0, Math.max(0, (window.pageYOffset || 0) + still.getBoundingClientRect().top - headerClearance() - 24));
        }
      }
      if (link) { try { link.focus({ preventScroll: true }); } catch (e) {} }
      try { window.history.scrollRestoration = 'auto'; } catch (e) {}
    }, function () { return mapStill(id); });
  }

  // "All videos": unwind the readings this page pushed, so Back stays honest;
  // a reading the reader arrived at directly closes in place.
  function back() {
    if (!open) return;
    if (depth > 0) {
      var steps = depth;
      depth = 0;
      try { window.history.go(-steps); return; } catch (e) {}
    }
    try { window.history.replaceState(null, '', '#videos'); } catch (e) {}
    hide(true);
  }

  // Window capture runs before landing.js's document-level jump handler, so a
  // film link opens its reading instead of scrolling to a hidden entry.
  window.addEventListener('click', function (event) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    var anchor = event.target && event.target.closest ? event.target.closest('a[href]') : null;
    if (!anchor) return;
    var href = anchor.getAttribute('href') || '';
    if (anchor.hasAttribute('data-film-back') && map.contains(anchor)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      back();
      return;
    }
    var route = routeOf(href);
    if (route) {
      event.preventDefault();
      event.stopImmediatePropagation();
      show(routes[route], true, route);
      return;
    }
    // The band's own address (the header's Videos link, the old aliases)
    // means the band: close any reading and let the page make its jump.
    if (open && href.charAt(0) === '#' && aliases.indexOf(href.slice(1)) >= 0) {
      depth = 0;
      hide(false);
    }
  }, true);

  window.addEventListener('popstate', function (event) {
    var route = routeOf(window.location.hash);
    var state = event.state || window.history.state;
    if (route) {
      event.stopImmediatePropagation();
      depth = state && state.filmDepth ? state.filmDepth : 0;
      show(routes[route], false);
    } else if (open) {
      event.stopImmediatePropagation();
      depth = 0;
      hide(true);
    }
  }, true);

  map.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape' || !open) return;
    var t = event.target;
    if (t && (/^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName) || t.isContentEditable)) return;
    event.preventDefault();
    back();
  });

  /* Tracing: the film's path from the introduction lights; the rest steps back. */
  var lit = [];
  function trace(node) {
    lit.forEach(function (el) { el.classList.remove('is-lit'); el.classList.remove('is-lit-tail'); });
    lit = [];
    if (!node || (open && !beside())) { map.classList.remove('is-tracing'); return; }
    var path = (node.getAttribute('data-map-path') || '').split(' ').filter(Boolean);
    if (path.length < 2) { map.classList.remove('is-tracing'); return; }
    path.forEach(function (id, i) {
      var li = nodes[id];
      if (!li) return;
      if (i > 0) { li.classList.add('is-lit'); lit.push(li); }
      if (i > 0 && i < path.length - 1) { li.classList.add('is-lit-tail'); }
    });
    var stem = tree.querySelector('[data-film-stem="' + path[1].replace(/^film-/, '') + '"]');
    if (stem) { stem.classList.add('is-lit'); lit.push(stem); }
    map.classList.add('is-tracing');
  }
  // Beside a reading, the open film's route stays lit between pointings.
  function rest() { if (beside()) trace(current && open ? current : null); }

  /* The one drawn connection: from the open reading's still to its place on
     the map; with the introduction open, to the head of the trunk the
     projects hang from. Adapted from Magic UI's AnimatedBeam (MIT License,
     Copyright (c) Magic UI; magicuidesign/magicui@85f97fd27b05,
     apps/www/registry/magicui/animated-beam.tsx): an SVG laid over the
     container, the path measured from the two elements' boxes relative to
     the container and measured again by a ResizeObserver. Changed: plain
     DOM instead of React state and Motion; a curve between two facing edges
     instead of between centres; one short draw when the choice changes, in
     place of the endless gradient sweep; and none with reduced motion. */
  var layout = map.querySelector('.film-map__layout');
  var beam = null;
  var beamPath = null;
  var beamKey = undefined;
  function beamEnds() {
    if (!layout || !beside()) return null;
    var reading = readings[open || fallback];
    if (!reading) return null;
    var from = reading.querySelector('.film-map__media .film-poster') || reading.querySelector('.film__title');
    var node = current && open ? current : null;
    var lane = null;
    if (node && node.classList.contains('film-map__depth--2')) {
      var parentKey = (node.getAttribute('data-map-path') || '').split(' ').slice(-2)[0];
      lane = nodes[parentKey] || null;
    } else if (node && node.classList.contains('film-map__depth--1')) {
      lane = node;
    }
    // Every line ends in the trunk's channel beside the chosen entry (a
    // branch's still, a film's branch, or the entry itself), so no line
    // crosses a still or a word on the map. The projects the introduction
    // shows share one row; the line ends at that row's name ("Also in the
    // introduction"), so the second never seems to point at the first.
    var first = tree.querySelector('.film-map__depth--1 .film-map__still');
    var group = node && node.classList.contains('film-map__node--shown') ? tree.querySelector('.film-map__group') : null;
    var target = lane ? lane.querySelector('.film-map__still') : node ? (group || node.querySelector('.film-map__title')) : first;
    if (!from || !target || !first) return null;
    var box = layout.getBoundingClientRect();
    var a = from.getBoundingClientRect();
    var b = target.getBoundingClientRect();
    var gap = parseFloat(window.getComputedStyle(tree).getPropertyValue('--fm-col')) || 40;
    var sx = a.right - box.left, sy = a.top + a.height / 2 - box.top;
    var ex = first.getBoundingClientRect().left - box.left - gap / 2, ey = b.top + b.height / 2 - box.top;
    return { sx: sx, sy: sy, ex: ex, ey: ey, node: node };
  }
  function drawBeam(animate) {
    var ends = beamEnds();
    if (!ends) { if (beam) beam.setAttribute('hidden', ''); return; }
    if (!beam) {
      var ns = 'http://www.w3.org/2000/svg';
      beam = doc.createElementNS(ns, 'svg');
      beam.setAttribute('class', 'film-map__beam');
      beam.setAttribute('aria-hidden', 'true');
      beam.setAttribute('focusable', 'false');
      beamPath = doc.createElementNS(ns, 'path');
      beam.appendChild(beamPath);
      layout.insertBefore(beam, layout.firstChild);
    }
    beam.removeAttribute('hidden');
    var dx = Math.max(24, (ends.ex - ends.sx) / 2);
    beamPath.setAttribute('d', 'M ' + ends.sx + ',' + ends.sy + ' C ' + (ends.sx + dx) + ',' + ends.sy + ' ' +
      (ends.ex - dx) + ',' + ends.ey + ' ' + ends.ex + ',' + ends.ey);
    var ink = ends.node ? (ends.node.className.match(/film-map__ink--[a-z]+/) || [''])[0] : '';
    beamPath.setAttribute('class', ink ? 'film-map__beam--chosen ' + ink : '');
    var key = ends.node ? ends.node.getAttribute('data-map-node') : null;
    var changed = key !== beamKey;
    beamKey = key;
    if (!animate || !changed || reducedMotion() || !beamPath.animate || !beamPath.getTotalLength) return;
    try {
      var length = beamPath.getTotalLength();
      beamPath.animate([{ strokeDasharray: length + ' ' + length, strokeDashoffset: length },
                        { strokeDasharray: length + ' ' + length, strokeDashoffset: 0 }],
                       { duration: 380, easing: 'cubic-bezier(0.2, 0, 0, 1)' });
    } catch (e) {}
  }
  if (layout && 'ResizeObserver' in window) {
    try { new ResizeObserver(function () { drawBeam(false); }).observe(layout); } catch (e) {}
  }
  try { if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(function () { drawBeam(false); }); } catch (e) {}
  var finePointer = false;
  try { finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches; } catch (e) {}
  if (finePointer) {
    tree.addEventListener('pointerover', function (event) {
      var card = event.target.closest && event.target.closest('.film-map__card');
      trace(card ? card.closest('[data-map-node]') : null);
    });
    tree.addEventListener('pointerleave', function () { trace(null); rest(); });
  }
  // A project without a still: its name is the link in the Tab order; the
  // rest of its entry is that link's mouse-only twin, as a film's still is.
  tree.addEventListener('click', function (event) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    var t = event.target;
    if (!t || !t.closest || t.closest('a[href]')) return;
    var card = t.closest('.film-map__card--text');
    var link = card ? card.querySelector('.film-map__title a') : null;
    if (!link) return;
    try { if (String(window.getSelection())) return; } catch (e) {}
    link.click();
  });
  tree.addEventListener('focusin', function (event) {
    trace(event.target.closest ? event.target.closest('[data-map-node]') : null);
  });
  tree.addEventListener('focusout', function (event) {
    if (!event.relatedTarget || !tree.contains(event.relatedTarget)) { trace(null); rest(); }
  });

  /* The lines run out once, when a map that starts below the window first
     comes into view. */
  function arm() {
    if (reducedMotion() || !('IntersectionObserver' in window) || open) return;
    // The drawing is choreographed for the wide tree; the outline's lines
    // on a phone or tablet are simply there.
    var wide = false;
    try { wide = map.classList.contains('film-map--pyramid') && window.matchMedia('(min-width: 1120px)').matches; } catch (e) {}
    if (!wide) return;
    var box = tree.getBoundingClientRect();
    if (box.top < window.innerHeight && box.bottom > 0) return;
    map.classList.add('film-map--armed');
    var watch = new IntersectionObserver(function (entries) {
      if (!entries.some(function (entry) { return entry.isIntersecting; })) return;
      watch.disconnect();
      window.requestAnimationFrame(function () {
        map.classList.add('film-map--drawing');
        map.classList.remove('film-map--armed');
        window.setTimeout(function () { map.classList.remove('film-map--drawing'); }, 1300);
      });
    }, { threshold: 0, rootMargin: '0px 0px -22% 0px' });
    watch.observe(tree);
  }

  map.classList.add('film-map--live');
  var arrival = routeOf(window.location.hash);
  var first = arrival ? routes[arrival] : null;
  mark(null);
  if (first) {
    var state = window.history.state;
    depth = state && state.filmDepth ? state.filmDepth : 0;
    map.classList.add('is-reading');
    settle(first);
    open = first;
    mark(first);
    var go = function () {
      // Beside the map, a reading reached from a link opens where the
      // explorer stands: the page's name, the map and the reading together
      // when they share the first screen.
      var top = readings[first].getBoundingClientRect().top;
      if (!beside() || top > window.innerHeight * 0.45) readings[first].scrollIntoView({ block: 'start' });
      try { readings[first].focus({ preventScroll: true }); } catch (e) {}
      rest();
      drawBeam(false);
    };
    if (window.requestAnimationFrame) window.requestAnimationFrame(go); else go();
  } else {
    arm();
    drawBeam(false);
  }
})();

/* Third-party notice for the AnimatedBeam geometry adapted above.
MIT License

Copyright (c) Magic UI

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/
