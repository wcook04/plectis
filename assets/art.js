/* Plectis: the plait.
   Two cables of fine thread, one ember and one ultramarine, plaited across
   the top of the landing. The mark is two woven strands; this is the same
   weave at the scale of the page. Each cable is a rope of hairline threads
   wound round its own axis, and the two cables cross with real over and
   under breaks, the way a braid or knot diagram is drawn.

   Motion and heat contract (unchanged from the earlier field):
   - One paint, then nothing. The weave is drawn once into an offscreen
     canvas and revealed left to right over about a second and a half. No
     ambient animation loop survives the reveal, so an idle or background
     tab costs nothing.
   - Nothing is painted while the document is hidden.
   - prefers-reduced-motion paints the finished weave with no reveal.
   - Save-data keeps the static CSS composition and starts nothing.
   - A resize repaints once, debounced. A theme change repaints once.
   - The static CSS wash in style.css stays authoritative for no-JS readers
     and for any failure; this file fades in over it and removes itself
     cleanly if the canvas cannot be created.
   - Nothing leaves the page: no fetches, no storage, no third-party code
     (CSP: 'self'). */
(function () {
  'use strict';

  if (!window.matchMedia || !window.requestAnimationFrame) return;
  var doc = document;
  var root = doc.documentElement;

  try {
    if (navigator.connection && navigator.connection.saveData) return;
  } catch (e) {}

  var mqMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var mqDark = window.matchMedia('(prefers-color-scheme: dark)');

  var wrap = null;
  var canvas = null;
  var ctx = null;
  var resizeTimer = 0;
  var revealFrame = 0;
  var lastW = 0;
  var lastH = 0;
  var generation = 0;

  function isDark() {
    var t = root.getAttribute('data-theme');
    if (t === 'dark') return true;
    if (t === 'light') return false;
    return mqDark.matches;
  }

  /* Deterministic noise, so the weave is the same picture on every visit. */
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

  function smooth(a, b, x) {
    var t = Math.max(0, Math.min(1, (x - a) / (b - a)));
    return t * t * (3 - 2 * t);
  }

  function mix(a, b, t) {
    return [
      Math.round(a[0] + (b[0] - a[0]) * t),
      Math.round(a[1] + (b[1] - a[1]) * t),
      Math.round(a[2] + (b[2] - a[2]) * t)
    ];
  }

  /* Palettes. Night: the ember stays in the orange register (never yellow or
     white-gold) and the cool cable is a real ultramarine that lifts to ice at
     its front threads. Day: the same two inks printed on paper. The cores
     are the eyes: each cable's core is drawn in the other cable's ink. */
  function palette(dark) {
    if (dark) {
      return {
        warmBack: [176, 66, 34], warmFront: [255, 158, 92],
        coolBack: [52, 74, 186], coolFront: [184, 204, 255],
        warmCore: [255, 146, 80], coolCore: [128, 152, 255],
        alpha: 0.62, glow: 0.5, width: 1.0, blend: 'lighter',
        coreWidth: 1.25, coreAlpha: 0.92, channel: 0.8
      };
    }
    return {
      warmBack: [190, 100, 64], warmFront: [140, 46, 16],
      coolBack: [110, 130, 200], coolFront: [30, 52, 142],
      warmCore: [168, 62, 26], coolCore: [36, 60, 156],
      alpha: 0.64, glow: 0, width: 0.95, blend: 'source-over',
      coreWidth: 1.15, coreAlpha: 0.86, channel: 0.85
    };
  }

  /* The weave lives inside an empty band the page reserves for it, between
     the introduction and the figures, so it never sits under a line of text.
     The canvas spans the full width at the band's position. */
  function stage() {
    return doc.querySelector('[data-plait-band]');
  }

  function stageBox() {
    var el = stage();
    if (!el) return null;
    var r = el.getBoundingClientRect();
    if (r.height < 40) return null;
    return { top: Math.round(r.top + (window.pageYOffset || 0)), height: Math.round(r.height) };
  }

  function stageHeight() {
    var box = stageBox();
    return box ? box.height : 0;
  }

  function build() {
    wrap = doc.createElement('div');
    wrap.className = 'plait';
    wrap.setAttribute('aria-hidden', 'true');
    canvas = doc.createElement('canvas');
    wrap.appendChild(canvas);
    try {
      ctx = canvas.getContext('2d');
    } catch (e) {
      ctx = null;
    }
    if (!ctx) {
      wrap = null;
      canvas = null;
      return false;
    }
    doc.body.insertBefore(wrap, doc.body.firstChild);
    return true;
  }

  /* Geometry, in CSS pixels. u runs 0..1 across the width, H is the band.
     The plait swells towards the middle of the page and thins at the edges,
     where the mask fades it out, and its axis undulates gently. */
  function geometry(W, H) {
    var narrow = W < 760;
    var swell = function (u) { return Math.sin(Math.PI * Math.max(0, Math.min(1, u))); };
    return {
      W: W,
      H: H,
      period: Math.max(240, Math.min(400, W * 0.235)),
      ropeTwist: Math.max(54, Math.min(84, W * 0.05)),
      strands: narrow ? 10 : 13,
      centre: function (u) {
        return H * (0.5 + 0.075 * Math.sin(Math.PI * 2 * (0.82 * u + 0.08)));
      },
      sep: function (u) {
        return H * (0.13 + 0.07 * swell(u));
      },
      rope: function (u) {
        return H * (0.05 + 0.03 * swell(u));
      }
    };
  }

  function cableY(g, x, k) {
    var u = x / g.W;
    var phi = (Math.PI * 2 * x) / g.period;
    return g.centre(u) + g.sep(u) * Math.cos(phi + k * Math.PI);
  }

  function cableDepth(g, x, k) {
    var phi = (Math.PI * 2 * x) / g.period;
    return Math.sin(phi + k * Math.PI);
  }

  /* Draw one cable's threads between x0 and x1. Opacity follows depth twice:
     a thread at the front of its rope is brighter, and the whole cable dims
     while it passes behind the other. Segments are grouped into opacity
     buckets so a thread is a handful of strokes, not hundreds. */
  function drawCable(c, g, pal, k, x0, x1, scale) {
    var n = g.strands;
    var step = 2;
    var back = k === 0 ? pal.warmBack : pal.coolBack;
    var front = k === 0 ? pal.warmFront : pal.coolFront;
    var buckets = 7;
    var j, x, b;
    for (j = 0; j < n; j += 1) {
      var theta = (Math.PI * 2 * j) / n;
      var paths = [];
      for (b = 0; b < buckets; b += 1) paths.push([]);
      var prev = null;
      /* The last sample lands exactly on x1, so a thread meets its own
         continuation in the next chunk with no gap at the join. */
      for (x = x0; ; x = Math.min(x + step, x1)) {
        var u = x / g.W;
        var psi = (Math.PI * 2 * x) / g.ropeTwist + theta;
        var y = cableY(g, x, k) + g.rope(u) * Math.cos(psi);
        if (prev) {
          var d = (Math.sin(psi) + 1) / 2;
          var z = (cableDepth(g, x, k) + 1) / 2;
          var level = Math.pow(d, 1.6) * (0.5 + 0.5 * z);
          var bucket = Math.min(buckets - 1, Math.floor(level * buckets));
          paths[bucket].push(prev[0], prev[1], x, y);
        }
        prev = [x, y];
        if (x >= x1) break;
      }
      for (b = 0; b < buckets; b += 1) {
        var segs = paths[b];
        if (!segs.length) continue;
        var t = (b + 0.5) / buckets;
        var col = mix(back, front, t);
        var a = pal.alpha * (0.14 + 0.86 * t);
        c.strokeStyle = 'rgba(' + col[0] + ',' + col[1] + ',' + col[2] + ',' + a.toFixed(3) + ')';
        c.lineWidth = scale * pal.width * (0.55 + 0.75 * t);
        c.beginPath();
        for (var s = 0; s < segs.length; s += 4) {
          c.moveTo(segs[s], segs[s + 1]);
          c.lineTo(segs[s + 2], segs[s + 3]);
        }
        c.stroke();
      }
    }
  }

  /* The eye of each cable. A yin-yang turning as it travels left to right,
     seen from the side, is this plait: each half sweeps out one cable, and
     the dot of the other colour inside it sweeps out a thin thread along that
     cable's axis. So the ember cable carries an ultramarine core and the
     ultramarine cable an ember one. The core sits in a narrow cut channel, so
     it reads as an inlaid thread rather than mixing into the rope, and it
     dims with its cable as the cable passes behind. Butt caps let the core of
     one chunk meet the next without a doubled joint. */
  function drawCore(c, g, pal, k, x0, x1) {
    var col = k === 0 ? pal.coolCore : pal.warmCore;
    var pts = [];
    var x, s;
    for (x = x0; x < x1; x += 3) pts.push(x, cableY(g, x, k));
    pts.push(x1, cableY(g, x1, k));
    function trace() {
      c.beginPath();
      c.moveTo(pts[0], pts[1]);
      for (var i = 2; i < pts.length; i += 2) c.lineTo(pts[i], pts[i + 1]);
    }
    var grad = c.createLinearGradient(x0, 0, x1, 0);
    var stops = 8;
    for (s = 0; s <= stops; s += 1) {
      var z = (cableDepth(g, x0 + ((x1 - x0) * s) / stops, k) + 1) / 2;
      var a = pal.coreAlpha * (0.45 + 0.55 * z);
      grad.addColorStop(s / stops, 'rgba(' + col[0] + ',' + col[1] + ',' + col[2] + ',' + a.toFixed(3) + ')');
    }
    c.save();
    c.lineCap = 'butt';
    c.lineJoin = 'round';
    c.globalCompositeOperation = 'destination-out';
    c.strokeStyle = 'rgba(0,0,0,' + pal.channel + ')';
    c.lineWidth = pal.coreWidth + 2;
    trace();
    c.stroke();
    c.globalCompositeOperation = 'source-over';
    c.strokeStyle = grad;
    c.lineWidth = pal.coreWidth;
    trace();
    c.stroke();
    c.restore();
  }

  /* The break where one cable passes over the other: erase a band along the
     front cable before drawing it, as in a knot diagram. The crossing sits
     mid-chunk, so the erase stops 2px short of each join with butt caps: a
     round cap bit a half-disc out of the rope already drawn at every crest,
     which read as scales down the cable, and an erase reaching the join
     column left a hairline there. */
  function eraseUnder(c, g, k, x0, x1, scale) {
    var a = x0 + 2;
    var b = x1 - 2;
    c.save();
    c.globalCompositeOperation = 'destination-out';
    c.strokeStyle = 'rgba(0,0,0,0.9)';
    c.lineCap = 'butt';
    c.lineJoin = 'round';
    c.beginPath();
    c.moveTo(a, cableY(g, a, k));
    for (var x = a + 3; x < b; x += 3) c.lineTo(x, cableY(g, x, k));
    c.lineTo(b, cableY(g, b, k));
    c.lineWidth = 2 * g.rope(((x0 + x1) / 2) / g.W) + 7 * scale;
    c.stroke();
    c.restore();
  }

  /* A few loose fibres leave the cables and drift, so the weave reads as
     thread rather than as a diagram. */
  function drawFibres(c, g, pal, scale) {
    var rand = rng(2604);
    var count = g.W < 760 ? 4 : 8;
    for (var i = 0; i < count; i += 1) {
      var k = i % 2;
      var xStart = g.W * (0.08 + 0.84 * rand());
      var len = 120 + 220 * rand();
      var dir = rand() < 0.5 ? -1 : 1;
      var bend = g.H * (0.06 + 0.14 * rand()) * dir;
      var col = k === 0 ? pal.warmFront : pal.coolFront;
      var steps = Math.ceil(len / 3);
      for (var s = 0; s < steps; s += 1) {
        var t0 = s / steps;
        var t1 = (s + 1) / steps;
        var xa = xStart + len * t0;
        var xb = xStart + len * t1;
        var ya = cableY(g, xa, k) + bend * t0 * t0;
        var yb = cableY(g, xb, k) + bend * t1 * t1;
        var a = pal.alpha * 0.55 * Math.sin(Math.PI * t0) * (1 - t0 * 0.6);
        c.strokeStyle = 'rgba(' + col[0] + ',' + col[1] + ',' + col[2] + ',' + a.toFixed(3) + ')';
        c.lineWidth = scale * 0.6;
        c.beginPath();
        c.moveTo(xa, ya);
        c.lineTo(xb, yb);
        c.stroke();
      }
    }
  }

  function paintInto(target, W, H, dpr, dark) {
    var c = target.getContext('2d');
    var pal = palette(dark);
    var g = geometry(W, H);
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, W, H);
    c.globalCompositeOperation = pal.blend;
    c.lineCap = 'round';

    /* Chunks run between the points where the cables are furthest apart, so
       each chunk holds exactly one crossing and one cable is in front. */
    var half = g.period / 2;
    var start = -half;
    var chunk = 0;
    while (start < W + half) {
      var end = start + half;
      var frontK = chunk % 2 === 0 ? 0 : 1;
      var backK = 1 - frontK;
      var x0 = Math.max(-20, start);
      var x1 = Math.min(W + 20, end);
      if (x1 > x0) {
        drawCable(c, g, pal, backK, x0, x1, 1);
        drawCore(c, g, pal, backK, x0, x1);
        eraseUnder(c, g, frontK, x0, x1, 1);
        c.globalCompositeOperation = pal.blend;
        drawCable(c, g, pal, frontK, x0, x1, 1);
        drawCore(c, g, pal, frontK, x0, x1);
      }
      start = end;
      chunk += 1;
    }
    drawFibres(c, g, pal, 1);

    /* Night only: a soft halo, as if the threads carried their own light. */
    if (pal.glow > 0 && typeof c.filter === 'string') {
      try {
        var copy = doc.createElement('canvas');
        copy.width = target.width;
        copy.height = target.height;
        copy.getContext('2d').drawImage(target, 0, 0);
        c.save();
        c.setTransform(1, 0, 0, 1, 0, 0);
        c.globalCompositeOperation = 'lighter';
        c.globalAlpha = pal.glow;
        c.filter = 'blur(' + Math.round(7 * dpr) + 'px)';
        c.drawImage(copy, 0, 0);
        c.restore();
      } catch (e) {}
    }
  }

  function reveal(off, W, H, dpr, immediate, gen) {
    if (!ctx) return;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (immediate) {
      ctx.drawImage(off, 0, 0);
      return;
    }
    var t0 = 0;
    var dur = 1500;
    function frame(now) {
      if (gen !== generation || !ctx) return;
      if (!t0) t0 = now;
      var p = Math.min(1, (now - t0) / dur);
      var e = 1 - Math.pow(1 - p, 3);
      var w = Math.max(1, Math.round(canvas.width * e));
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(off, 0, 0, w, canvas.height, 0, 0, w, canvas.height);
      if (p < 1) {
        revealFrame = window.requestAnimationFrame(frame);
      } else {
        revealFrame = 0;
      }
    }
    revealFrame = window.requestAnimationFrame(frame);
  }

  function paint(animate) {
    if (!wrap && !build()) return;
    var W = Math.max(320, root.clientWidth || window.innerWidth);
    var box = stageBox();
    if (!box) return;
    var H = box.height;
    lastW = W;
    lastH = H;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    wrap.style.top = box.top + 'px';
    wrap.style.height = H + 'px';
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    canvas.style.width = W + 'px';
    canvas.style.height = H + 'px';

    var off = doc.createElement('canvas');
    off.width = canvas.width;
    off.height = canvas.height;
    try {
      paintInto(off, W, H, dpr, isDark());
    } catch (e) {
      teardown();
      return;
    }
    generation += 1;
    if (revealFrame) {
      window.cancelAnimationFrame(revealFrame);
      revealFrame = 0;
    }
    reveal(off, W, H, dpr, !animate || mqMotion.matches, generation);
    root.classList.add('plait-live');
  }

  function teardown() {
    if (revealFrame) window.cancelAnimationFrame(revealFrame);
    revealFrame = 0;
    root.classList.remove('plait-live');
    if (wrap && wrap.parentNode) wrap.parentNode.removeChild(wrap);
    wrap = null;
    canvas = null;
    ctx = null;
  }

  /* Late fonts and reflow can move the band without resizing the window, so
     the wrapper follows its top; only a change of size repaints. */
  function follow() {
    if (!wrap) return;
    var box = stageBox();
    if (!box) return;
    var W = root.clientWidth || window.innerWidth;
    if (Math.abs(W - lastW) >= 2 || Math.abs(box.height - lastH) >= 4) {
      paint(false);
      return;
    }
    wrap.style.top = box.top + 'px';
  }

  function onResize() {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(follow, 160);
  }

  function onTheme() {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(function () { paint(false); }, 60);
  }

  function start() {
    if (!stage()) return;
    paint(true);
    window.addEventListener('resize', onResize, { passive: true });
    window.addEventListener('load', follow);
    try {
      if (doc.fonts && doc.fonts.ready) doc.fonts.ready.then(follow);
    } catch (e) {}
    if (window.MutationObserver) {
      new MutationObserver(onTheme)
        .observe(root, { attributes: true, attributeFilter: ['data-theme'] });
    }
    try {
      mqDark.addEventListener('change', onTheme);
    } catch (e) {
      if (mqDark.addListener) mqDark.addListener(onTheme);
    }
  }

  function whenVisible() {
    if (doc.visibilityState !== 'hidden') {
      start();
      return;
    }
    function onVis() {
      if (doc.visibilityState === 'hidden') return;
      doc.removeEventListener('visibilitychange', onVis);
      start();
    }
    doc.addEventListener('visibilitychange', onVis);
  }

  if (doc.readyState === 'loading') {
    doc.addEventListener('DOMContentLoaded', whenVisible);
  } else {
    whenVisible();
  }
})();
