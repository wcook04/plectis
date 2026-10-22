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
      drawCables();
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
      drawCables();
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
    if (!node || (open && !beside())) { map.classList.remove('is-tracing'); lightCables([]); return; }
    var path = (node.getAttribute('data-map-path') || '').split(' ').filter(Boolean);
    if (path.length < 2) { map.classList.remove('is-tracing'); lightCables([]); return; }
    path.forEach(function (id, i) {
      var li = nodes[id];
      if (!li) return;
      if (i > 0) { li.classList.add('is-lit'); lit.push(li); }
      if (i > 0 && i < path.length - 1) { li.classList.add('is-lit-tail'); }
    });
    var stem = tree.querySelector('[data-film-stem="' + path[1].replace(/^film-/, '') + '"]');
    if (stem) { stem.classList.add('is-lit'); lit.push(stem); }
    map.classList.add('is-tracing');
    lightCables(path.slice(1));
  }
  // Beside a reading, the open film's route stays lit between pointings.
  function rest() { if (beside()) trace(current && open ? current : null); }

  /* The cables (19 October 2026). Beside a reading, the map draws how the
     series is joined: from the introduction one cable per branch, each in its
     branch's ink, run as a ribbon out of the introduction's frame and peeled
     off to its branch the way the plait's cables close in (art.js), then a
     short reach in the same ink from a branch to the film it leads to. A
     dotted quiet cable reaches the projects the introduction shows. With
     another film open, the ribbon leaves the panel beside "Back to the
     introduction", the words that name its source. Pointing at a film lights
     its cable and steps the others back; a light runs once along it from the
     introduction (the maths map's bead, universe.js drawPulse). On a first
     visit the cables draw out from the introduction once.
     The geometry is adapted from Magic UI's AnimatedBeam (MIT License,
     Copyright (c) Magic UI; magicuidesign/magicui@85f97fd27b05,
     apps/www/registry/magicui/animated-beam.tsx): an SVG laid over the
     container, each path measured from two elements' boxes relative to the
     container and measured again by a ResizeObserver. Changed: plain DOM
     instead of React state and Motion; routed ribbons with rounded turns
     instead of one curve between centres; one draw on a first visit and one
     light per pointing, in place of the endless gradient sweep; none with
     reduced motion. Without this script the stylesheet's own lines stand. */
  var layout = map.querySelector('.film-map__layout');
  var NS = 'http://www.w3.org/2000/svg';
  var cables = null;      // the drawing
  var cableOf = {};       // node key -> { g, path, dot, length }
  var cableLayer = null;
  var beadLayer = null;
  var shape = null;       // the geometry the drawing was made for
  var SP = 4;             // between the ribbon's strands
  var VS = 7;             // between the strands' turns
  var R = 10;             // the radius of a turn
  function quietMotion() {
    if (reducedMotion()) return true;
    try { if (navigator.connection && navigator.connection.saveData) return true; } catch (e) {}
    return false;
  }
  function inkOf(el) { return el ? ((el.getAttribute('class') || '').match(/film-map__ink--[a-z]+/) || [''])[0] : ''; }
  function cableRoot() {
    if (!cables) {
      cables = doc.createElementNS(NS, 'svg');
      cables.setAttribute('class', 'film-map__cables');
      cables.setAttribute('aria-hidden', 'true');
      cables.setAttribute('focusable', 'false');
      cableLayer = doc.createElementNS(NS, 'g');
      beadLayer = doc.createElementNS(NS, 'g');
      beadLayer.setAttribute('class', 'film-map__bead');
      beadLayer.setAttribute('opacity', '0');
      for (var i = 0; i < 4; i++) beadLayer.appendChild(doc.createElementNS(NS, 'circle'));
      cables.appendChild(cableLayer);
      cables.appendChild(beadLayer);
      layout.insertBefore(cables, layout.firstChild);
    }
    return cables;
  }
  // Where the ribbon leaves the panel: the introduction's frame, or the way
  // back to it when another reading is open.
  function cableSource(box) {
    var key = open || fallback;
    var reading = readings[key];
    if (!reading) return null;
    var frame = key === fallback ? reading.querySelector('.film-map__media .film-poster') : null;
    var back = key !== fallback ? reading.querySelector('.film-map__back') : null;
    var el = frame || back;
    if (!el || !el.getClientRects().length) return null;
    var r = el.getBoundingClientRect();
    var panel = shelf.getBoundingClientRect();
    return { x: (frame ? r.right : Math.max(r.right, panel.right)) - box.left, y: r.top + r.height / 2 - box.top,
             lead: back ? r.right - box.left + 8 : null };
  }
  function entry(node, box) {
    var still = node.querySelector('.film-map__still');
    var el = still && still.getClientRects().length ? still : node.querySelector('.film-map__title');
    if (!el || !el.getClientRects().length) return null;
    var r = el.getBoundingClientRect();
    return { x: r.left - box.left, y: r.top + Math.min(r.height / 2, still ? r.height / 2 : 12) - box.top, left: r.left - box.left };
  }
  function arc(x, y, sweep) { return ' A ' + R + ' ' + R + ' 0 0 ' + sweep + ' ' + x + ' ' + y; }
  // One strand: along the ribbon, a turn, down (or up) its own run, a turn,
  // and into its film's frame. A strand whose film is level with it runs on
  // in one easy curve.
  function strand(x0, y0, turn, ex, ey) {
    var dy = ey - y0;
    if (Math.abs(dy) < 2 * R + 1) {
      var k = (ex - x0) / 2;
      return 'M ' + x0 + ' ' + y0 + ' C ' + (x0 + k) + ' ' + y0 + ' ' + (ex - k) + ' ' + ey + ' ' + ex + ' ' + ey;
    }
    var down = dy > 0, s = down ? 1 : -1;
    return 'M ' + x0 + ' ' + y0 + ' H ' + (turn - R) + arc(turn, y0 + s * R, down ? 1 : 0) +
      ' V ' + (ey - s * R) + arc(turn + R, ey, down ? 0 : 1) + ' H ' + ex;
  }
  function add(key, d, cls, end) {
    var g = doc.createElementNS(NS, 'g');
    g.setAttribute('class', cls);
    var path = doc.createElementNS(NS, 'path');
    path.setAttribute('d', d);
    g.appendChild(path);
    var dot = null;
    if (end) {
      dot = doc.createElementNS(NS, 'circle');
      dot.setAttribute('cx', end.x); dot.setAttribute('cy', end.y); dot.setAttribute('r', '2.25');
      g.appendChild(dot);
    }
    cableLayer.appendChild(g);
    var length = 0;
    try { length = path.getTotalLength(); } catch (e) {}
    cableOf[key] = { g: g, path: path, dot: dot, length: length };
  }
  function drawCables() {
    if (!layout || !home) return;
    if (!beside()) { if (cables) cables.setAttribute('hidden', ''); map.classList.remove('film-map--wired'); shape = null; return; }
    var box = layout.getBoundingClientRect();
    var src = cableSource(box);
    if (!src) { if (cables) cables.setAttribute('hidden', ''); shape = null; return; }
    cableRoot().removeAttribute('hidden');
    map.classList.add('film-map--wired');
    // A notice that moved nothing keeps the drawing (and any drawing-out).
    var sig = [Math.round(src.x), Math.round(src.y), Math.round(box.width)].concat(
      Array.prototype.map.call(tree.querySelectorAll('.film-map__still, .film-map__node--shown .film-map__title'), function (el) {
        var r = el.getBoundingClientRect();
        return Math.round(r.left - box.left) + ',' + Math.round(r.top - box.top) + ',' + Math.round(r.height);
      })).join(' ');
    if (sig === shape) return;
    while (cableLayer.firstChild) cableLayer.removeChild(cableLayer.firstChild);
    cableOf = {};
    // The introduction's strands: its branches and the projects it shows.
    var targets = [];
    Array.prototype.forEach.call(tree.querySelectorAll('.film-map__depth--1, .film-map__node--shown'), function (node) {
      var end = entry(node, box);
      if (!end) return;
      var shown = node.classList.contains('film-map__node--shown');
      targets.push({ key: node.getAttribute('data-map-node'), end: end, ink: shown ? '' : inkOf(node), shown: shown });
    });
    if (!targets.length) return;
    targets.sort(function (a, b) { return a.end.y - b.end.y; });
    var n = targets.length;
    // The turns stand in the open channel between the panel and the map's
    // column, clear of the map's own words.
    var reach = Math.min(Math.min.apply(null, targets.map(function (t) { return t.end.x; })) - 8,
                         tree.getBoundingClientRect().left - box.left - 4);
    var x0 = src.x + 1;
    // The turns stand in the open channel between the panel and the frames;
    // the lowest strand turns first, so no strand crosses another.
    var ups = targets.filter(function (t, i) { t.y0 = src.y + (i - (n - 1) / 2) * SP; return t.end.y < t.y0 - 2 * R; });
    var downs = targets.filter(function (t) { return t.end.y > t.y0 + 2 * R; }).reverse();
    var room = Math.max(ups.length, downs.length);
    var first = Math.max(x0 + R + 6, (x0 + reach) / 2 - (room - 1) * VS / 2);
    ups.forEach(function (t, i) { t.turn = first + i * VS; });
    downs.forEach(function (t, i) { t.turn = first + i * VS; });
    if (src.lead !== null && src.lead < x0) {
      add('lead', 'M ' + src.lead + ' ' + src.y + ' H ' + x0, 'film-map__cable film-map__cable--lead');
    }
    targets.forEach(function (t) {
      var ex = t.end.x - 6;
      add(t.key, strand(x0, t.y0, t.turn || first, ex, t.end.y),
          'film-map__cable' + (t.shown ? ' film-map__cable--quiet' : ' ' + t.ink), t.shown ? null : { x: ex, y: t.end.y });
    });
    // A branch's reach to the film it leads to, across the gap between them.
    var gap = parseFloat(window.getComputedStyle(tree).columnGap) || 40;
    Array.prototype.forEach.call(tree.querySelectorAll('.film-map__depth--2'), function (node) {
      var end = entry(node, box);
      if (!end) return;
      var ex = end.x - 6, sx = end.x - gap + 8;
      if (ex - sx < 10) return;
      add(node.getAttribute('data-map-node'), 'M ' + sx + ' ' + end.y + ' H ' + ex,
          'film-map__cable film-map__cable--reach ' + inkOf(node), { x: ex, y: end.y });
    });
    lightCables(litKeys || []);
    shape = sig;
  }

  // The lit route's cables come up to full ink; the rest step back with the
  // stylesheet's lines (.is-tracing).
  var litKeys = [];
  function lightCables(keys) {
    litKeys = keys;
    Object.keys(cableOf).forEach(function (key) {
      var g = cableOf[key].g;
      if (keys.indexOf(key) >= 0) g.classList.add('is-lit'); else g.classList.remove('is-lit');
    });
  }

  /* A light runs once from the introduction to the film the reader points
     at, so the series reads as a route. It waits a tenth of a second, so a
     pointer sweeping across the map leaves no trail, then travels in about
     half a second and is gone. Never for a key press, never with reduced
     motion or Save-Data, never in a hidden tab. */
  var beadTimer = 0, beadFrame = 0;
  function stopBead() {
    if (beadTimer) { window.clearTimeout(beadTimer); beadTimer = 0; }
    if (beadFrame) { window.cancelAnimationFrame(beadFrame); beadFrame = 0; }
    if (beadLayer) beadLayer.setAttribute('opacity', '0');
  }
  function runBead(keys) {
    stopBead();
    if (!cables || quietMotion() || doc.hidden || !window.requestAnimationFrame) return;
    var legs = keys.map(function (k) { return cableOf[k]; }).filter(function (c) { return c && c.length > 0; });
    if (!legs.length) return;
    var total = legs.reduce(function (sum, c) { return sum + c.length; }, 0);
    var ms = Math.max(460, Math.min(700, 380 + total * 0.6));
    beadTimer = window.setTimeout(function () {
      beadTimer = 0;
      beadLayer.setAttribute('class', 'film-map__bead ' + inkOf(legs[legs.length - 1].g));
      var dots = beadLayer.childNodes;
      var at = function (d) {
        d = Math.max(0, Math.min(total, d));
        for (var i = 0; i < legs.length; i++) {
          if (d <= legs[i].length || i === legs.length - 1) return legs[i].path.getPointAtLength(Math.min(d, legs[i].length));
          d -= legs[i].length;
        }
        return null;
      };
      var t0 = null;
      var step = function (now) {
        if (t0 === null) t0 = now;
        var t = Math.min(1, (now - t0) / ms);
        var q = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
        beadLayer.setAttribute('opacity', String(Math.min(1, t * 6, (1 - t) * 6)));
        for (var i = 0; i < dots.length; i++) {
          var p = at((q - i * 0.035) * total);
          if (!p) continue;
          dots[i].setAttribute('cx', p.x); dots[i].setAttribute('cy', p.y);
          dots[i].setAttribute('r', String(i ? 2.7 - i * 0.45 : 3.4));
        }
        beadFrame = t < 1 ? window.requestAnimationFrame(step) : 0;
        if (!beadFrame) beadLayer.setAttribute('opacity', '0');
      };
      beadFrame = window.requestAnimationFrame(step);
    }, 110);
  }

  /* The cables draw out from the introduction once, on a reader's first
     visit: the ribbon's strands one after another, then the reaches. About
     seven tenths of a second, then still; a later visit finds them drawn. */
  var DRAWN = 'plectis.filmMap.drawn';
  function firstVisit() {
    try { return !window.localStorage.getItem(DRAWN); } catch (e) { return false; }
  }
  function drawOut() {
    if (!cables || quietMotion() || !firstVisit()) return;
    try { window.localStorage.setItem(DRAWN, '1'); } catch (e) { return; }
    var strands = [], reaches = [];
    Object.keys(cableOf).forEach(function (key) {
      var c = cableOf[key];
      (c.g.classList.contains('film-map__cable--reach') ? reaches : strands).push(c);
    });
    var play = function (c, delay, ms) {
      if (!c.length || !c.path.animate) return;
      var L = c.length + 1;
      try {
        c.path.animate([{ strokeDasharray: L + ' ' + L, strokeDashoffset: L },
                        { strokeDasharray: L + ' ' + L, strokeDashoffset: 0 }],
                       { duration: ms, delay: delay, easing: 'cubic-bezier(0.16, 1, 0.3, 1)', fill: 'backwards' });
        if (c.dot) c.dot.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 140, delay: delay + ms * 0.7, fill: 'backwards' });
      } catch (e) {}
    };
    strands.forEach(function (c, i) { play(c, i * 45, 520); });
    reaches.forEach(function (c, i) { play(c, 440 + i * 40, 220); });
  }

  if (layout && 'ResizeObserver' in window) {
    try { new ResizeObserver(function () { drawCables(); }).observe(layout); } catch (e) {}
  }
  try { if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(function () { drawCables(); }); } catch (e) {}
  var finePointer = false;
  try { finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches; } catch (e) {}
  var pointed = null;
  if (finePointer) {
    tree.addEventListener('pointerover', function (event) {
      var card = event.target.closest && event.target.closest('.film-map__card');
      var node = card ? card.closest('[data-map-node]') : null;
      if (node === pointed) return;
      pointed = node;
      trace(node);
      if (node && beside()) runBead((node.getAttribute('data-map-path') || '').split(' ').filter(Boolean).slice(1));
      else stopBead();
    });
    tree.addEventListener('pointerleave', function () { pointed = null; stopBead(); trace(null); rest(); });
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
  /* Arrow keys move between the map's entries: up and down through the
     branches (and the projects under them), right from a branch to the film
     it leads to, left back; Home and End to the first and last. Tab keeps
     its own order; these keys only move focus, which lights the route. */
  function entryLink(node) { return node ? node.querySelector('.film-map__title a') : null; }
  function visibleNode(node) { var a = entryLink(node); return a && a.getClientRects().length ? node : null; }
  function rows() {
    var out = [];
    var all = Array.prototype.filter.call(tree.querySelectorAll('[data-map-node]'), visibleNode);
    if (!beside()) return all.map(function (node) { return [node]; });
    all.forEach(function (node) {
      if (node.classList.contains('film-map__depth--2')) return;
      var key = node.getAttribute('data-map-node');
      var row = [node];
      all.forEach(function (other) {
        var path = (other.getAttribute('data-map-path') || '').split(' ');
        if (other.classList.contains('film-map__depth--2') && path[path.length - 2] === key) row.push(other);
      });
      out.push(row);
    });
    return out;
  }
  tree.addEventListener('keydown', function (event) {
    if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    var key = event.key;
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].indexOf(key) < 0) return;
    var link = event.target && event.target.closest ? event.target.closest('.film-map__title a') : null;
    if (!link || !tree.contains(link)) return;
    var grid = rows(), r = -1, c = -1;
    grid.forEach(function (row, i) { row.forEach(function (node, j) { if (node.contains(link)) { r = i; c = j; } }); });
    if (r < 0) return;
    var to = null;
    if (key === 'ArrowDown' && r < grid.length - 1) to = grid[r + 1][Math.min(c, grid[r + 1].length - 1)];
    if (key === 'ArrowUp' && r > 0) to = grid[r - 1][Math.min(c, grid[r - 1].length - 1)];
    if (key === 'ArrowRight' && c < grid[r].length - 1) to = grid[r][c + 1];
    if (key === 'ArrowLeft' && c > 0) to = grid[r][c - 1];
    if (key === 'Home') to = grid[0][0];
    if (key === 'End') to = grid[grid.length - 1][0];
    if (!to) return;
    event.preventDefault();
    var target = entryLink(to);
    try { target.focus({ preventScroll: false }); } catch (e) { target.focus(); }
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
      drawCables();
    };
    if (window.requestAnimationFrame) window.requestAnimationFrame(go); else go();
  } else {
    arm();
    drawCables();
    // The first visit's drawing waits for the type to settle (so the cables
    // are measured once), and for the map to be in view.
    if (cables && beside() && firstVisit() && !quietMotion()) {
      cableLayer.setAttribute('opacity', '0');
      var started = false;
      var reveal = function () {
        if (started) return;
        started = true;
        drawCables();
        cableLayer.removeAttribute('opacity');
        drawOut();
      };
      var whenSeen = function () {
        var box = tree.getBoundingClientRect();
        if ((box.top < window.innerHeight && box.bottom > 0) || !('IntersectionObserver' in window)) { reveal(); return; }
        var watch = new IntersectionObserver(function (entries) {
          if (!entries.some(function (entry) { return entry.isIntersecting; })) return;
          watch.disconnect();
          reveal();
        }, { threshold: 0.2 });
        watch.observe(tree);
      };
      var settled = false;
      var once = function () { if (!settled) { settled = true; whenSeen(); } };
      try { if (doc.fonts && doc.fonts.status !== 'loaded') { doc.fonts.ready.then(once); window.setTimeout(once, 700); } else once(); } catch (e) { once(); }
    }
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
