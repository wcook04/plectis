/* Why I'm building this: the plait over the four views, and the tabs.

   The plait is the landing weave's grammar (assets/art.js) at the scale of
   one band: two cables, brick red and steel blue, crossing with real over
   and under breaks. Loose threads gather into the cables at the start, and
   the cables cross at each view's station and drop a thread into it. It is
   SVG, so it keeps the site's inks in both themes. It is drawn once, at
   rest: no reveal and no loop, so every view is usable at once. A resize
   redraws it once, debounced.

   The tabs show one of Will's three further paragraphs at a time; the views
   that paragraph is about keep full strength and their threads take the
   selection ink, the others step back. Without this file every paragraph
   stands in order, the tab row stays hidden and the views stand plain.
   Nothing leaves the page: no fetches, no storage. */
(function () {
  'use strict';

  var SVGNS = 'http://www.w3.org/2000/svg';
  var section = document.querySelector('[data-why]');
  if (!section) return;
  var stage = section.querySelector('[data-why-stage]');
  var svg = section.querySelector('[data-why-plait]');
  var ways = Array.prototype.slice.call(section.querySelectorAll('[data-why-way]'));
  var dropGroups = {};
  var focusSet = null;
  var hot = null;
  /* The stage size the plait was last drawn for. */
  var lastW = 0;
  var lastH = 0;

  /* ── Tabs ─────────────────────────────────────────────────────────── */
  var tablist = section.querySelector('[data-why-tabs]');
  var tabs = tablist ? Array.prototype.slice.call(tablist.querySelectorAll('[data-why-tab]')) : [];
  var panels = Array.prototype.slice.call(section.querySelectorAll('[data-why-panel]'));

  function applyFocus() {
    ways.forEach(function (way) {
      var name = way.getAttribute('data-why-way');
      var chosen = !!focusSet && focusSet.indexOf(name) >= 0;
      var quiet = !!focusSet && !chosen;
      way.classList.toggle('is-chosen', chosen);
      way.classList.toggle('is-quiet', quiet);
      var group = dropGroups[name];
      if (group) {
        group.classList.toggle('is-chosen', chosen);
        group.classList.toggle('is-quiet', quiet && hot !== name);
        group.classList.toggle('is-hot', hot === name);
      }
    });
  }

  function select(index, moveFocus) {
    tabs.forEach(function (tab, i) {
      var on = i === index;
      tab.setAttribute('aria-selected', on ? 'true' : 'false');
      tab.tabIndex = on ? 0 : -1;
      var panel = panels[i];
      if (!panel) return;
      panel.classList.toggle('is-current', on);
      panel.tabIndex = on ? 0 : -1;
      if (on) {
        panel.removeAttribute('inert');
        panel.removeAttribute('aria-hidden');
      } else {
        panel.setAttribute('inert', '');
        panel.setAttribute('aria-hidden', 'true');
      }
    });
    if (moveFocus && tabs[index]) tabs[index].focus();
    if (panels[index]) {
      focusSet = (panels[index].getAttribute('data-why-focus') || '').split(/\s+/).filter(Boolean);
      applyFocus();
    }
  }

  if (tabs.length && tabs.length === panels.length) {
    panels.forEach(function (panel, i) {
      panel.setAttribute('role', 'tabpanel');
      panel.setAttribute('aria-labelledby', tabs[i].id);
    });
    tablist.hidden = false;
    section.classList.add('is-live');
    select(0, false);
    tabs.forEach(function (tab, i) {
      tab.addEventListener('click', function () { select(i, false); });
      tab.addEventListener('keydown', function (event) {
        var next = null;
        if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (i + 1) % tabs.length;
        else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (i - 1 + tabs.length) % tabs.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = tabs.length - 1;
        if (next === null) return;
        event.preventDefault();
        select(next, true);
      });
    });
  }

  ways.forEach(function (way) {
    var name = way.getAttribute('data-why-way');
    var on = function () { hot = name; applyFocus(); };
    var off = function () { if (hot === name) { hot = null; applyFocus(); } };
    way.addEventListener('pointerenter', on);
    way.addEventListener('pointerleave', off);
    way.addEventListener('focusin', on);
    way.addEventListener('focusout', off);
  });

  /* ── The plait ────────────────────────────────────────────────────── */
  if (!stage || !svg || !ways.length) return;

  function el(name, attrs, parent) {
    var node = document.createElementNS(SVGNS, name);
    for (var key in attrs) {
      if (Object.prototype.hasOwnProperty.call(attrs, key)) node.setAttribute(key, attrs[key]);
    }
    if (parent) parent.appendChild(node);
    return node;
  }

  function smooth(t) {
    t = Math.max(0, Math.min(1, t));
    return t * t * (3 - 2 * t);
  }

  /* Deterministic noise, so the loose threads are the same every visit. */
  function rng(seed) {
    var s = seed >>> 0;
    return function () {
      s = (s + 0x6D2B79F5) >>> 0;
      var t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function geometry() {
    var box = stage.getBoundingClientRect();
    if (box.width < 160 || box.height < 60) return null;
    var vertical = getComputedStyle(section).getPropertyValue('--why-axis').trim() === 'y';
    var stageCs = getComputedStyle(stage);
    var nodes = ways.map(function (way) {
      var frame = way.querySelector('[data-why-anchor]') || way;
      var r = frame.getBoundingClientRect();
      return {
        name: way.getAttribute('data-why-way'),
        s: vertical ? r.top + r.height / 2 - box.top : r.left + r.width / 2 - box.left,
        edge: vertical ? r.left - box.left : r.top - box.top
      };
    });
    return {
      w: box.width,
      h: box.height,
      vertical: vertical,
      lane: vertical ? parseFloat(stageCs.paddingLeft) / 2 : parseFloat(stageCs.paddingTop) * 0.46,
      start: 0,
      end: vertical ? box.height : box.width,
      nodes: nodes
    };
  }

  /* Phase along the axis: a crossing (phase a multiple of pi) at every
     station, and two full twists between neighbouring stations when there
     is room, as the funnel plait in art.js crosses at each step. */
  function phaseFn(nodes) {
    var s = nodes.map(function (n) { return n.s; });
    var gaps = [];
    for (var i = 1; i < s.length; i += 1) gaps.push(s[i] - s[i - 1]);
    var mean = gaps.length ? gaps.reduce(function (a, b) { return a + b; }, 0) / gaps.length : 200;
    var twists = function (gap) { return gap > 180 ? 4 : 2; };
    var rate = (Math.PI * twists(mean)) / mean;
    var at = [0];
    for (var j = 1; j < s.length; j += 1) at.push(at[j - 1] + Math.PI * twists(gaps[j - 1]));
    return function (x) {
      if (x <= s[0]) return (x - s[0]) * rate;
      for (var k = 1; k < s.length; k += 1) {
        if (x <= s[k]) return at[k - 1] + ((x - s[k - 1]) / (s[k] - s[k - 1])) * (at[k] - at[k - 1]);
      }
      return at[at.length - 1] + (x - s[s.length - 1]) * rate;
    };
  }

  function line(points) {
    var d = '';
    for (var i = 0; i < points.length; i += 1) {
      d += (d ? 'L' : 'M') + points[i][0].toFixed(1) + ' ' + points[i][1].toFixed(1);
    }
    return d;
  }

  function draw() {
    var box = stage.getBoundingClientRect();
    lastW = box.width;
    lastH = box.height;
    var g = geometry();
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    dropGroups = {};
    if (!g) return;
    svg.setAttribute('viewBox', '0 0 ' + g.w.toFixed(1) + ' ' + g.h.toFixed(1));

    var P = function (s, t) { return g.vertical ? [t, s] : [s, t]; };
    var c = g.lane;
    var amp = Math.max(5, Math.min(11, c * 0.34));
    var phase = phaseFn(g.nodes);
    var first = g.nodes[0].s;
    var last = g.nodes[g.nodes.length - 1].s;
    var frayEnd = Math.max(g.start + 24, Math.min(first - 46, g.start + 96));
    var tieEnd = Math.min(g.end - 4, last + Math.max(60, (g.end - last) * 0.75));

    var env = function (x) {
      return smooth((x - frayEnd) / Math.max(30, (first - frayEnd) * 0.9)) *
        (1 - smooth((x - last - 18) / Math.max(30, tieEnd - last - 18)));
    };
    var offset = function (x, sign) { return c + sign * amp * Math.sin(phase(x)) * env(x); };

    function cable(sign, fine) {
      var pts = [];
      for (var x = frayEnd; x <= tieEnd + 0.01; x += 2.5) {
        var t = offset(x, sign);
        if (fine) t += 2.1 * Math.cos(phase(x) * 1.5 + (sign > 0 ? 0 : 1.7)) * env(x);
        pts.push(P(x, t));
      }
      return line(pts);
    }

    function segment(sign, from, to) {
      var pts = [];
      for (var x = from; x <= to + 0.01; x += 1.5) pts.push(P(x, offset(x, sign)));
      return line(pts);
    }

    var plait = el('g', { 'class': 'why-plait' }, svg);

    /* Loose threads gathering into the two cables. */
    var rand = rng(257);
    var fray = el('g', { 'class': 'why-plait__frays' }, plait);
    var spread = c * (g.vertical ? 0.9 : 0.95);
    for (var i = 0; i < 12; i += 1) {
      var from = (rand() * 2 - 1) * spread;
      var bend = 0.35 + rand() * 0.4;
      var pts = [];
      for (var x = g.start; x <= frayEnd + 0.01; x += 3) {
        var u = (x - g.start) / Math.max(1, frayEnd - g.start);
        pts.push(P(x, c + from * (1 - smooth(Math.pow(u, bend)))));
      }
      el('path', { d: line(pts), 'class': 'why-plait__fray why-plait__fray--' + (i % 2 === 0 ? 'ember' : 'ice') }, fray);
    }

    /* The two cables, each a main thread and a fine one wound round it. */
    var cables = el('g', { 'class': 'why-plait__cables' }, plait);
    [[1, 'ember'], [-1, 'ice']].forEach(function (pair) {
      ['fine', 'main'].forEach(function (kind) {
        el('path', { d: cable(pair[0], kind === 'fine'),
          'class': 'why-plait__cable why-plait__cable--' + pair[1] + ' why-plait__cable--' + kind }, cables);
      });
    });

    /* Over and under: at every crossing one cable is redrawn over a gap in
       the page's ground, alternating as in a true plait. */
    var crossings = el('g', { 'class': 'why-plait__crossings' }, plait);
    var k = 0;
    var prev = Math.floor(phase(frayEnd) / Math.PI);
    for (var x2 = frayEnd + 1; x2 <= tieEnd; x2 += 1) {
      var q = Math.floor(phase(x2) / Math.PI);
      if (q === prev) continue;
      prev = q;
      if (env(x2) < 0.12) continue;
      var w = Math.max(6, Math.min(12, (Math.PI / Math.max(0.001, phase(x2 + 1) - phase(x2))) * 0.28));
      var sign = k % 2 === 0 ? 1 : -1;
      var seg = segment(sign, x2 - w, x2 + w);
      var grp = el('g', {}, crossings);
      el('path', { d: seg, 'class': 'why-plait__gap' }, grp);
      el('path', { d: seg, 'class': 'why-plait__cable why-plait__cable--main why-plait__cable--' + (sign > 0 ? 'ember' : 'ice') }, grp);
      k += 1;
    }

    /* A station at each view: one thread dropped from the crossing to the
       frame's edge. The chosen tab's views take the selection ink. */
    var drops = el('g', { 'class': 'why-plait__drops' }, plait);
    g.nodes.forEach(function (node) {
      var group = el('g', { 'class': 'why-plait__drop-group', 'data-drop': node.name }, drops);
      dropGroups[node.name] = group;
      var a = P(node.s, c + 3);
      var b = P(node.s, node.edge - 3);
      if (Math.abs(g.vertical ? b[0] - a[0] : b[1] - a[1]) > 4) {
        el('path', { d: line([a, b]), 'class': 'why-plait__drop' }, group);
      }
      el('circle', { cx: a[0].toFixed(1), cy: a[1].toFixed(1), r: '2.6', 'class': 'why-plait__node' }, group);
    });

    applyFocus();
  }

  draw();

  var timer = 0;
  var redraw = function () {
    clearTimeout(timer);
    timer = setTimeout(function () {
      var r = stage.getBoundingClientRect();
      if (Math.abs(r.width - lastW) < 1 && Math.abs(r.height - lastH) < 1) return;
      draw();
    }, 140);
  };
  if ('ResizeObserver' in window) {
    new ResizeObserver(redraw).observe(stage);
  } else {
    window.addEventListener('resize', redraw);
  }
  /* Images arriving late change the frames' heights on narrow screens, and
     a late font can move the frames' centres without resizing the stage. */
  Array.prototype.forEach.call(stage.querySelectorAll('img'), function (img) {
    if (!img.complete) img.addEventListener('load', redraw, { once: true });
  });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(draw);
})();
