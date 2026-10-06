/* Plectis: the plait.
   Two cables of fine thread, one brick red and one steel blue, plaited across
   the top of the landing (the inks of the entangled-photon yin-yang Will keyed
   the palette to, held at a mature chroma: never neon). The mark is two woven strands; this is the same
   weave at the scale of the page. Each cable is a rope of hairline threads
   wound round its own axis, and the two cables cross with real over and
   under breaks, the way a braid or knot diagram is drawn.

   Motion and heat contract (unchanged from the earlier field):
   - One paint, then nothing. The weave is drawn once into an offscreen
     canvas and revealed left to right over about a second and a half,
     behind a soft front that two points of light ride, one per cable (the
     needles). No ambient animation loop survives the reveal, so an idle or
     background tab costs nothing.
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

  /* Palettes. Night: a brick red that warms to coral at its front threads
     and a steel blue that lifts to a pale sky, both held at a mature chroma
     (Will, 4 October: "a bit of glow, prudent, not flamboyant"). Day: the
     same two inks printed on paper. The cores are the eyes: each cable's
     core is drawn in the other cable's ink. */
  function palette(dark) {
    if (dark) {
      return {
        warmBack: [160, 63, 60], warmFront: [230, 123, 109],
        coolBack: [53, 96, 143], coolFront: [147, 197, 230],
        warmCore: [225, 115, 102], coolCore: [123, 178, 217],
        alpha: 0.62, glow: 0.5, width: 1.0, blend: 'lighter',
        coreWidth: 1.25, coreAlpha: 0.92, channel: 0.8
      };
    }
    return {
      warmBack: [209, 137, 128], warmFront: [147, 43, 39],
      coolBack: [124, 156, 185], coolFront: [37, 83, 124],
      warmCore: [154, 50, 44], coolCore: [42, 89, 130],
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

  /* A band marked data-plait-band="contained" (the glossary masthead) holds
     the weave inside its own box rather than across the window, and is
     painted once with no reveal: the entrance belongs to the landing. */
  function contained() {
    var el = stage();
    return !!el && el.getAttribute('data-plait-band') === 'contained';
  }

  function stageBox() {
    var el = stage();
    if (!el) return null;
    var r = el.getBoundingClientRect();
    if (r.height < 40 || (contained() && r.width < 160)) return null;
    return {
      top: Math.round(r.top + (window.pageYOffset || 0)),
      left: Math.round(r.left + (window.pageXOffset || 0)),
      width: Math.round(r.width),
      height: Math.round(r.height)
    };
  }

  function bandWidth(box) {
    return contained() ? box.width : Math.max(320, root.clientWidth || window.innerWidth);
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
     where the mask fades it out, and its axis undulates gently.
     5 October 2026: a quieter rhythm. The weave divides the introduction from
     the maps, so it reads as two coherent cables first and as thread second:
     about six crossings across a laptop window instead of nine, fewer and
     slower-turning threads in each rope, and a shallower drift of the axis.
     The band is a little shorter, so the cables take a larger share of it;
     a longer period with a flatter rope read as ribbon, not cable. */
  /* 6 October 2026: the landing's plait is composed, not repeated (Type B
     art direction, after Anni Albers on stripes set by the structure). Its
     pitch is no longer constant: the crossing rate is integrated from a
     frequency that is slow and open at the margins and gathers into one
     tight knot just right of centre, above the place the atlas begins, where
     the cables are drawn close and their ropes thicken as a pulled braid
     does. Fewer, longer interlacings either side, so the eye travels to the
     knot and on down into the map. Every crossing is still a true over and
     under. The glossary's contained band keeps the even plait. */
  var KNOT = 0.585;
  function geometry(W, H, composed) {
    var narrow = W < 760;
    var swell = function (u) { return Math.sin(Math.PI * Math.max(0, Math.min(1, u))); };
    var base = Math.max(300, Math.min(540, W * 0.3));
    var knotW = narrow ? 0.12 : 0.072;
    var knot = composed
      ? function (u) { var d = (u - KNOT) / knotW; return Math.exp(-d * d); }
      : function () { return 0; };
    /* Crossings per pixel: under half the even plait's rate at the margins,
       nearly three times it in the knot. The phase is its
       running integral, tabled at 2px and read back by interpolation. */
    var freq = composed
      ? function (u) { return (0.46 + 2.3 * knot(u)) / base; }
      : function () { return 1 / base; };
    var lo = -Math.round(base), hi = Math.round(W + base), dx = 2;
    var table = [0], acc = 0, x;
    for (x = lo + dx; x <= hi + dx; x += dx) {
      acc += Math.PI * 2 * dx * freq((x - dx / 2) / W);
      table.push(acc);
    }
    var zero = (function () {
      var i = Math.floor((0 - lo) / dx), f = ((0 - lo) / dx) - i;
      return table[i] + (table[i + 1] - table[i]) * f;
    })();
    return {
      W: W,
      H: H,
      period: base,
      ropeTwist: Math.max(58, Math.min(92, W * 0.056)),
      strands: narrow ? 9 : 11,
      lo: lo,
      hi: hi,
      phase: function (xx) {
        var t = (Math.max(lo, Math.min(hi, xx)) - lo) / dx;
        var i = Math.min(table.length - 2, Math.floor(t)), f = t - i;
        return table[i] + (table[i + 1] - table[i]) * f - zero;
      },
      centre: function (u) {
        return H * (0.5 + 0.055 * Math.sin(Math.PI * 2 * (0.7 * u + 0.08)));
      },
      sep: function (u) {
        return composed
          ? H * (0.24 - 0.155 * knot(u)) * (0.7 + 0.3 * swell(u))
          : H * (0.145 + 0.075 * swell(u));
      },
      rope: function (u) {
        return composed
          ? H * (0.044 + 0.018 * swell(u) + 0.028 * knot(u))
          : H * (0.058 + 0.032 * swell(u));
      }
    };
  }

  function cableY(g, x, k) {
    var u = x / g.W;
    return g.centre(u) + g.sep(u) * Math.cos(g.phase(x) + k * Math.PI);
  }

  function cableDepth(g, x, k) {
    return Math.sin(g.phase(x) + k * Math.PI);
  }

  /* Where the cables stand furthest apart (phase a multiple of pi): the
     chunk boundaries, each chunk holding exactly one crossing. */
  function apexes(g) {
    var out = [];
    var m = Math.floor(g.phase(g.lo) / Math.PI);
    var x = g.lo;
    out.push(x);
    for (x = g.lo; x <= g.hi; x += 1) {
      var n = Math.floor(g.phase(x) / Math.PI);
      if (n !== m) { out.push(x); m = n; }
    }
    out.push(g.hi);
    return out;
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
    var count = g.W < 760 ? 3 : 5;
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
    var g = geometry(W, H, !contained());
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, W, H);
    c.globalCompositeOperation = pal.blend;
    c.lineCap = 'round';

    /* Chunks run between the points where the cables are furthest apart, so
       each chunk holds exactly one crossing and one cable is in front; the
       front cable alternates, chunk by chunk, as in a true plait. */
    var cuts = apexes(g);
    for (var chunk = 0; chunk + 1 < cuts.length; chunk += 1) {
      // Which cable is in front follows the phase's half-turn, exactly as the
      // even plait's chunk parity did (its first chunk began at -pi).
      var m = Math.floor(g.phase((cuts[chunk] + cuts[chunk + 1]) / 2) / Math.PI);
      var frontK = Math.abs(m) % 2 === 1 ? 0 : 1;
      var backK = 1 - frontK;
      var x0 = Math.max(-20, cuts[chunk]);
      var x1 = Math.min(W + 20, cuts[chunk + 1]);
      if (x1 > x0) {
        drawCable(c, g, pal, backK, x0, x1, 1);
        drawCore(c, g, pal, backK, x0, x1);
        eraseUnder(c, g, frontK, x0, x1, 1);
        c.globalCompositeOperation = pal.blend;
        drawCable(c, g, pal, frontK, x0, x1, 1);
        drawCore(c, g, pal, frontK, x0, x1);
      }
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

  /* The two needles: one point of light at the front of each cable, in that
     cable's front ink, carried along the cable's axis as the weave is drawn.
     They wind round each other as they travel, the yin-yang turning through
     time that the plait is a side view of, and the one behind dims as its
     cable does. On the night ground they glow; on paper they are two small
     points of ink with a faint wash. They exist only while the reveal runs. */
  function drawNeedles(c, g, pal, x, dpr, p) {
    if (x < 0 || x > g.W) return;
    var fade = Math.min(1, p / 0.08) * Math.min(1, (1 - p) / 0.12);
    if (fade <= 0) return;
    var dark = pal.blend === 'lighter';
    c.save();
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.globalCompositeOperation = dark ? 'lighter' : 'source-over';
    for (var k = 0; k < 2; k += 1) {
      var y = cableY(g, x, k);
      var z = (cableDepth(g, x, k) + 1) / 2;
      var col = k === 0 ? pal.warmFront : pal.coolFront;
      var a = fade * (0.35 + 0.65 * z);
      var rgb = col[0] + ',' + col[1] + ',' + col[2];
      var reach = dark ? 16 : 7;
      var halo = c.createRadialGradient(x, y, 0, x, y, reach);
      halo.addColorStop(0, 'rgba(' + rgb + ',' + (a * (dark ? 0.55 : 0.22)).toFixed(3) + ')');
      halo.addColorStop(1, 'rgba(' + rgb + ',0)');
      c.fillStyle = halo;
      c.beginPath();
      c.arc(x, y, reach, 0, Math.PI * 2);
      c.fill();
      c.fillStyle = 'rgba(' + rgb + ',' + (a * (dark ? 0.95 : 0.8)).toFixed(3) + ')';
      c.beginPath();
      c.arc(x, y, dark ? 1.9 : 1.5, 0, Math.PI * 2);
      c.fill();
    }
    c.restore();
  }

  /* The reveal draws the finished weave in from the left behind a soft front
     (about a seventh of the width), so the thread appears rather than being
     uncovered by a hard edge, and the needles ride the middle of that front.
     The front runs on past the right edge so the last of the weave arrives
     whole, and the final frame is the finished picture with no needles. */
  function reveal(off, W, H, dpr, immediate, gen) {
    if (!ctx) return;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (immediate) {
      ctx.drawImage(off, 0, 0);
      return;
    }
    var g = geometry(W, H, !contained());
    var pal = palette(isDark());
    var feather = Math.round(Math.min(240, Math.max(90, W * 0.14)) * dpr);
    var t0 = 0;
    var dur = 1500;
    function frame(now) {
      if (gen !== generation || !ctx) return;
      if (!t0) t0 = now;
      var p = Math.min(1, (now - t0) / dur);
      var e = 1 - Math.pow(1 - p, 3);
      var front = Math.round((canvas.width + feather) * e);
      var w = Math.max(1, Math.min(canvas.width, front));
      ctx.globalCompositeOperation = 'source-over';
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (p >= 1) {
        ctx.drawImage(off, 0, 0);
      } else {
        ctx.drawImage(off, 0, 0, w, canvas.height, 0, 0, w, canvas.height);
        var tail = front - feather;
        var soft = ctx.createLinearGradient(tail, 0, front, 0);
        soft.addColorStop(0, 'rgba(0,0,0,0)');
        soft.addColorStop(1, 'rgba(0,0,0,1)');
        ctx.globalCompositeOperation = 'destination-out';
        ctx.fillStyle = soft;
        ctx.fillRect(Math.max(0, tail), 0, w - Math.max(0, tail), canvas.height);
        ctx.globalCompositeOperation = 'source-over';
        drawNeedles(ctx, g, pal, (front - feather * 0.55) / dpr, dpr, p);
      }
      if (p < 1) {
        revealFrame = window.requestAnimationFrame(frame);
      } else {
        revealFrame = 0;
      }
    }
    revealFrame = window.requestAnimationFrame(frame);
  }

  function paint(animate) {
    var box = stageBox();
    if (!box) {
      if (wrap && contained()) teardown();
      return;
    }
    if (!wrap && !build()) return;
    var W = bandWidth(box);
    var H = box.height;
    lastW = W;
    lastH = H;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    wrap.style.top = box.top + 'px';
    wrap.style.height = H + 'px';
    wrap.style.left = contained() ? box.left + 'px' : '';
    wrap.style.width = contained() ? W + 'px' : '';
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
    var box = stageBox();
    if (!wrap) {
      if (box && contained()) paint(false);
      return;
    }
    if (!box) {
      if (contained()) teardown();
      return;
    }
    var W = contained() ? box.width : root.clientWidth || window.innerWidth;
    if (Math.abs(W - lastW) >= 2 || Math.abs(box.height - lastH) >= 4) {
      paint(false);
      return;
    }
    wrap.style.top = box.top + 'px';
    if (contained()) wrap.style.left = box.left + 'px';
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
    paint(!contained());
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
