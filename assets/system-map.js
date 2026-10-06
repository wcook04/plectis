/* Plectis: the system map.

   The earlier software drawn as one circle, the sibling of the mathematics
   slide's universe map, so a reader learns one map and reads both. Its own
   character is the weave: Plectis is Latin for "you weave", and here the
   machinery and its rules are drawn as two inks interlocked.

     Rim      The 88 components as marks on a graduated scale, one tick each,
              in seven family sectors bracketed and named outside the ring
              (the family, then its count). A mark's cut says how the
              component is backed. Outside each tick a fine azure bar steps
              once for every rule the component's paper module cites; a
              crossbar caps it where a rule is shown enforced there, an open
              one where a narrower part of a rule is checked.
     Fibres   The connections between components, each a tapered filled
              outline: out of a mark along its radius, gathered at its
              family's hub, along a swoop to the other family's hub and out
              again, bundled with every connection between the same two
              families; inside a family, a short U just within the rim. Thin
              where it leaves, fuller in the bundle, so direction reads
              without arrowheads. Each kind of connection has its texture.
     Centre   The doctrine as a necklace round its name: the twelve axioms
              on a ring with the rules tied to several of them standing
              between them, and each rule tied to one axiom its satellite
              just outside. Every rests-on and threatens line is a short
              curve that leaves and lands along the radius.

   Two inks with one meaning each: red is a connection between components,
   azure is a rule. Selecting is the same gesture from either end. A
   component lights inward (the rules its paper module cites, and the axioms
   those principles rest on) and outward along its connections, each named
   on a plate; a rule lights outward to every component whose paper module
   cites it, the components where it is shown enforced framed by a reticle.
   A rule line never travels round the core: near ones bend in like rays,
   far ones go straight across it, never behind its name. Where a lit red
   line and an azure one cross, one passes over the other, as in a plait.
   Each lit line appears once from the end its light starts at; reduced
   motion shows it at once.

   What the data says, and so what is drawn: a red line is a connection read
   from the code, one of three kinds (a component runs another, reads the
   results another saved, or checks the files copied from another), each in
   its own texture; an older scene's red lines are the relations a
   component's own record lists, and say so. An azure line is a citation by
   a component's paper module. "Enforced in" is where a test shows a rule
   holding (until that manifest exists, what the rule's card names). No line
   ever stands for anything else.

   Every word is real text, set at the page's body size or larger (notes at
   seven eighths of it), on one SVG drawing laid out for the space it has.
   The column beside the map is the readable index of whatever is lit. The
   trail above the map, Escape and Back step out again.

   On its own page (docs/system-map.html, 5 October 2026) the map is an
   explorer, the mathematics map's sibling: the drawing fitted whole to its
   stage, and every word in the reading panel beside it. Names come by
   levels of detail: at rest the families round the outside; chosen, a
   family's own components along its arc; pointed at, a component's name
   on a plate and its relations lit; zoomed (the frame's controls, the
   wheel, a pinch), every name that stands whole in view, and a drag moves
   the zoomed map. The landing's Expand link is kept on the drawing's
   choice, so the explorer opens on what the reader was looking at.

   Everything drawn comes from docs/architecture-graph-scene.json and
   docs/doctrine-manifest.json. Every number is a count from that data. */
(function () {
  'use strict';

  var SVGNS = 'http://www.w3.org/2000/svg';

  /* ---- The loom ------------------------------------------------------------ */
  /* The map's own primitives: the weave (over and under wherever a red line
     and an azure one cross), the fibres (connections bundled through their
     families' hubs, drawn as tapered filled outlines) and the doctrine's
     necklace. Plain functions with no page: points are [x, y] in the
     drawing's pixels, polar points [angle, radius]. */
  var Loom = (function () {
    'use strict';

    /* ---- Small helpers ------------------------------------------------------ */
    var TAU = Math.PI * 2;
    function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
    function norm(a) { a %= TAU; return a < 0 ? a + TAU : a; }
    // The signed shorter turn from angle a to angle b.
    function turn(a, b) { var d = norm(b - a); return d > Math.PI ? d - TAU : d; }
    function circMean(angles, weights) {
      var x = 0, y = 0;
      for (var i = 0; i < angles.length; i++) {
        var w = weights ? weights[i] : 1;
        x += w * Math.cos(angles[i]);
        y += w * Math.sin(angles[i]);
      }
      return Math.sqrt(x * x + y * y) < 1e-9 ? (angles.length ? angles[0] : 0) : Math.atan2(y, x);
    }
    function smooth01(t) { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); }
    function nf(v) { return String(Math.round(v * 100) / 100); }
    function now() { return typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now(); }
    // A small deterministic generator (mulberry32), so every order is the
    // same picture on every visit.
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
    function polarXY(cx, cy, list) {
      var out = new Array(list.length);
      for (var i = 0; i < list.length; i++) {
        out[i] = [cx + list[i][1] * Math.cos(list[i][0]), cy + list[i][1] * Math.sin(list[i][0])];
      }
      return out;
    }

    /* ---- Paths ---------------------------------------------------------------- */

    /* toPolyline(d, tol) -> [[[x, y], ...], ...]
       SVG path data (every command, absolute or relative) flattened to one
       polyline per subpath; curves and arcs are sampled so a chord strays no
       more than about `tol` pixels (default 0.5) from the curve. Use it to hand
       the weave paths that were built as `d` strings. */
    function toPolyline(d, tol) {
      tol = tol || 0.5;
      var NUM = /[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?/y;
      var i = 0, n = d.length, out = [], cur = null;
      var x = 0, y = 0, sx = 0, sy = 0, lcx = 0, lcy = 0, lqx = 0, lqy = 0, last = '';
      function ws() { while (i < n && (d.charCodeAt(i) <= 32 || d[i] === ',')) i++; }
      function num() { ws(); NUM.lastIndex = i; var m = NUM.exec(d); if (!m) throw new Error('path data: number expected at ' + i); i = NUM.lastIndex; return +m[0]; }
      function flag() { ws(); var c = d[i++]; if (c !== '0' && c !== '1') throw new Error('path data: flag expected at ' + (i - 1)); return c === '1' ? 1 : 0; }
      function more() { ws(); return i < n && /[-+.\d]/.test(d[i]); }
      function steps(len) { return clamp(Math.ceil(Math.sqrt(len / tol) * 0.9), 2, 120); }
      function lineTo(px, py) { cur.push([px, py]); x = px; y = py; }
      function cubic(x1, y1, x2, y2, x3, y3) {
        var len = Math.hypot(x1 - x, y1 - y) + Math.hypot(x2 - x1, y2 - y1) + Math.hypot(x3 - x2, y3 - y2);
        var k = steps(len), x0 = x, y0 = y;
        for (var j = 1; j <= k; j++) {
          var t = j / k, u = 1 - t;
          cur.push([u * u * u * x0 + 3 * u * u * t * x1 + 3 * u * t * t * x2 + t * t * t * x3,
                    u * u * u * y0 + 3 * u * u * t * y1 + 3 * u * t * t * y2 + t * t * t * y3]);
        }
        x = x3; y = y3;
      }
      function quad(x1, y1, x2, y2) {
        var len = Math.hypot(x1 - x, y1 - y) + Math.hypot(x2 - x1, y2 - y1);
        var k = steps(len), x0 = x, y0 = y;
        for (var j = 1; j <= k; j++) {
          var t = j / k, u = 1 - t;
          cur.push([u * u * x0 + 2 * u * t * x1 + t * t * x2, u * u * y0 + 2 * u * t * y1 + t * t * y2]);
        }
        x = x2; y = y2;
      }
      function arc(rx, ry, phi, fa, fs, x2, y2) {
        // Endpoint to centre parameterisation (SVG 1.1, appendix F.6).
        if (!rx || !ry) { lineTo(x2, y2); return; }
        rx = Math.abs(rx); ry = Math.abs(ry);
        var cp = Math.cos(phi * Math.PI / 180), sp = Math.sin(phi * Math.PI / 180);
        var dx = (x - x2) / 2, dy = (y - y2) / 2;
        var x1p = cp * dx + sp * dy, y1p = -sp * dx + cp * dy;
        var lam = x1p * x1p / (rx * rx) + y1p * y1p / (ry * ry);
        if (lam > 1) { rx *= Math.sqrt(lam); ry *= Math.sqrt(lam); }
        var num2 = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p;
        var den = rx * rx * y1p * y1p + ry * ry * x1p * x1p;
        var co = (fa === fs ? -1 : 1) * Math.sqrt(Math.max(0, num2 / (den || 1)));
        var cxp = co * rx * y1p / ry, cyp = -co * ry * x1p / rx;
        var ccx = cp * cxp - sp * cyp + (x + x2) / 2, ccy = sp * cxp + cp * cyp + (y + y2) / 2;
        var t1 = Math.atan2((y1p - cyp) / ry, (x1p - cxp) / rx);
        var t2 = Math.atan2((-y1p - cyp) / ry, (-x1p - cxp) / rx);
        var dt = t2 - t1;
        if (fs && dt < 0) dt += TAU;
        if (!fs && dt > 0) dt -= TAU;
        var k = steps(Math.abs(dt) * Math.max(rx, ry));
        for (var j = 1; j <= k; j++) {
          var t = t1 + dt * j / k, ex = rx * Math.cos(t), ey = ry * Math.sin(t);
          cur.push([ccx + cp * ex - sp * ey, ccy + sp * ex + cp * ey]);
        }
        x = x2; y = y2;
      }
      while (true) {
        ws();
        if (i >= n) break;
        var c = d[i];
        if (/[MmLlHhVvCcSsQqTtAaZz]/.test(c)) i++;
        else if (last && last !== 'Z' && last !== 'z') c = last === 'M' ? 'L' : last === 'm' ? 'l' : last;
        else throw new Error('path data: command expected at ' + i);
        var rel = c === c.toLowerCase(), ox = rel ? x : 0, oy = rel ? y : 0, C = c.toUpperCase();
        if (C === 'M') {
          x = num() + ox; y = num() + oy; sx = x; sy = y;
          cur = [[x, y]]; out.push(cur);
        } else if (C === 'Z') {
          if (cur && (x !== sx || y !== sy)) lineTo(sx, sy);
          x = sx; y = sy;
        } else {
          if (!cur) { cur = [[x, y]]; out.push(cur); }
          if (C === 'L') lineTo(num() + ox, num() + oy);
          else if (C === 'H') lineTo(num() + ox, y);
          else if (C === 'V') lineTo(x, num() + oy);
          else if (C === 'C') {
            var a1 = num() + ox, b1 = num() + oy, a2 = num() + ox, b2 = num() + oy, a3 = num() + ox, b3 = num() + oy;
            lcx = a2; lcy = b2; cubic(a1, b1, a2, b2, a3, b3);
          } else if (C === 'S') {
            var r1 = /[CS]/i.test(last) ? 2 * x - lcx : x, s1 = /[CS]/i.test(last) ? 2 * y - lcy : y;
            var a4 = num() + ox, b4 = num() + oy, a5 = num() + ox, b5 = num() + oy;
            lcx = a4; lcy = b4; cubic(r1, s1, a4, b4, a5, b5);
          } else if (C === 'Q') {
            var q1 = num() + ox, w1 = num() + oy, q2 = num() + ox, w2 = num() + oy;
            lqx = q1; lqy = w1; quad(q1, w1, q2, w2);
          } else if (C === 'T') {
            var q3 = /[QT]/i.test(last) ? 2 * x - lqx : x, w3 = /[QT]/i.test(last) ? 2 * y - lqy : y;
            lqx = q3; lqy = w3; quad(q3, w3, num() + ox, num() + oy);
          } else if (C === 'A') {
            var rx = num(), ry = num(), ph = num(), fa = flag(), fs = flag();
            arc(rx, ry, ph, fa, fs, num() + ox, num() + oy);
          }
        }
        last = c;
        // Implicit repeats of the same command.
        while (C !== 'Z' && more()) {
          rel = c === c.toLowerCase(); ox = rel ? x : 0; oy = rel ? y : 0;
          if (C === 'M' || C === 'L') lineTo(num() + ox, num() + oy);
          else if (C === 'H') lineTo(num() + ox, y);
          else if (C === 'V') lineTo(x, num() + oy);
          else if (C === 'C') { var e1 = num() + ox, f1 = num() + oy, e2 = num() + ox, f2 = num() + oy; lcx = e2; lcy = f2; cubic(e1, f1, e2, f2, num() + ox, num() + oy); }
          else if (C === 'S') { var g1 = 2 * x - lcx, h1 = 2 * y - lcy, e3 = num() + ox, f3 = num() + oy; lcx = e3; lcy = f3; cubic(g1, h1, e3, f3, num() + ox, num() + oy); }
          else if (C === 'Q') { var e4 = num() + ox, f4 = num() + oy; lqx = e4; lqy = f4; quad(e4, f4, num() + ox, num() + oy); }
          else if (C === 'T') { var g2 = 2 * x - lqx, h2 = 2 * y - lqy; lqx = g2; lqy = h2; quad(g2, h2, num() + ox, num() + oy); }
          else if (C === 'A') { var rx2 = num(), ry2 = num(), ph2 = num(), fa2 = flag(), fs2 = flag(); arc(rx2, ry2, ph2, fa2, fs2, num() + ox, num() + oy); }
          if (C === 'M') c = rel ? 'l' : 'L';
        }
      }
      return out.filter(function (p) { return p.length > 1; });
    }

    // Cumulative length along a polyline.
    function measure(pts) {
      var c = new Float64Array(pts.length);
      for (var i = 1; i < pts.length; i++) c[i] = c[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      return c;
    }

    /* resample(pts, step) -> { p: [[x, y], ...], len, step }
       The polyline at even spacing (the last point exact), the spacing as
       near `step` as divides the length. */
    function resample(pts, step) {
      var cum = measure(pts), len = cum[cum.length - 1];
      var k = Math.max(1, Math.round(len / step)), h = len / k, out = [pts[0].slice()], j = 1;
      for (var i = 1; i < k; i++) {
        var s = i * h;
        while (j < pts.length - 1 && cum[j] < s) j++;
        var seg = cum[j] - cum[j - 1], t = seg > 0 ? (s - cum[j - 1]) / seg : 0;
        out.push([pts[j - 1][0] + (pts[j][0] - pts[j - 1][0]) * t, pts[j - 1][1] + (pts[j][1] - pts[j - 1][1]) * t]);
      }
      out.push(pts[pts.length - 1].slice());
      return { p: out, len: len, step: h };
    }

    /* pointAt(pts, s) -> { x, y, tx, ty }: the point at arc length s and the
       unit direction of travel there. */
    function pointAt(pts, s, cum) {
      cum = cum || measure(pts);
      var n = pts.length, lo = 1, hi = n - 1;
      s = clamp(s, 0, cum[n - 1]);
      while (lo < hi) { var mid = (lo + hi) >> 1; if (cum[mid] < s) lo = mid + 1; else hi = mid; }
      var a = pts[lo - 1], b = pts[lo], seg = cum[lo] - cum[lo - 1] || 1, t = (s - cum[lo - 1]) / seg;
      return { x: a[0] + (b[0] - a[0]) * t, y: a[1] + (b[1] - a[1]) * t, tx: (b[0] - a[0]) / seg, ty: (b[1] - a[1]) / seg };
    }

    /* lineD(pts) -> path data for a polyline, straight segments. */
    function lineD(pts) {
      if (!pts.length) return '';
      var d = 'M' + nf(pts[0][0]) + ' ' + nf(pts[0][1]);
      for (var i = 1; i < pts.length; i++) d += 'L' + nf(pts[i][0]) + ' ' + nf(pts[i][1]);
      return d;
    }

    /* ---- Curves in polar form -------------------------------------------------- */
    /* Every line inside the ring is shaped in polar coordinates, then set on the
       page: a curve whose control points keep their angle at an end leaves and
       lands along the radius, and a curve whose control radii all stay above r
       never comes nearer the centre than r. */

    // A cubic Bézier in polar form, sampled about every `px` pixels.
    function polarBezier(c0, c1, c2, c3, px, out, skipFirst) {
      out = out || [];
      var rm = (c0[1] + c3[1]) / 2;
      var span = Math.abs(c1[0] - c0[0]) * c0[1] + Math.abs(c2[0] - c1[0]) * rm + Math.abs(c3[0] - c2[0]) * c3[1] +
        Math.abs(c1[1] - c0[1]) + Math.abs(c2[1] - c1[1]) + Math.abs(c3[1] - c2[1]);
      var k = clamp(Math.ceil(span / (px || 3)), 3, 160);
      for (var j = skipFirst ? 1 : 0; j <= k; j++) {
        var t = j / k, u = 1 - t, b0 = u * u * u, b1 = 3 * u * u * t, b2 = 3 * u * t * t, b3 = t * t * t;
        out.push([b0 * c0[0] + b1 * c1[0] + b2 * c2[0] + b3 * c3[0], b0 * c0[1] + b1 * c1[1] + b2 * c2[1] + b3 * c3[1]]);
      }
      return out;
    }

    /* polarSpline(ctrl, beta, px) -> polar points
       A clamped uniform cubic B-spline through polar control points (angles
       unwrapped), straightened by `beta` as in Holten's hierarchical edge
       bundling: each inner control point is drawn toward the even run between
       the two ends by (1 - beta). In polar form that run is the arc at the
       ends' radius, so a weaker bundle rides nearer the rim. beta 1 keeps the
       control polygon; 0 is the plain arc. */
    function polarSpline(ctrl, beta, px) {
      var n = ctrl.length - 1, P = new Array(n + 1);
      for (var i = 0; i <= n; i++) {
        var c = ctrl[i];
        if (i === 0 || i === n || !(beta < 1)) { P[i] = c; continue; }
        var t = i / n;
        P[i] = [beta * c[0] + (1 - beta) * (ctrl[0][0] + t * (ctrl[n][0] - ctrl[0][0])),
                beta * c[1] + (1 - beta) * (ctrl[0][1] + t * (ctrl[n][1] - ctrl[0][1]))];
      }
      var Q = [P[0], P[0]].concat(P, [P[n], P[n]]), out = [];
      for (var s = 0; s + 3 < Q.length; s++) {
        var p0 = Q[s], p1 = Q[s + 1], p2 = Q[s + 2], p3 = Q[s + 3];
        var span = Math.abs(p2[0] - p1[0]) * (p1[1] + p2[1]) / 2 + Math.abs(p2[1] - p1[1]);
        var k = clamp(Math.ceil(span / (px || 3)), 1, 80);
        for (var j = s === 0 ? 0 : 1; j <= k; j++) {
          var u = j / k, u2 = u * u, u3 = u2 * u, v = 1 - u;
          var b0 = v * v * v / 6, b1 = (3 * u3 - 6 * u2 + 4) / 6, b2 = (-3 * u3 + 3 * u2 + 3 * u + 1) / 6, b3 = u3 / 6;
          out.push([b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0], b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1]]);
        }
      }
      return out;
    }

    /* ---- Fibre routes ---------------------------------------------------------- */

    /* bundle(spec) -> [{ pts, polar, local, pair, lane }] in the order of spec.links
       Radial hierarchical edge bundling for a ring of components in families.
       spec = {
         cx, cy          the ring's centre
         R               the radius the component marks sit on
         at              each component's angle
         group           each component's family index
         hub             each family's hub angle (its sector's middle)
         links           [[from, to], ...] component indices
         rimR            where a route leaves its mark              (R - 9)
         hubR            the family hubs' ring                       (0.79 R)
         lanes           [deepest, shallowest] travel radii          ([0.57 R, 0.73 R])
         beta            Holten's bundling strength                  (0.85)
         leave           how far a route runs radially first         (0.05 R)
         shape           'swoop' (default) or 'lanes' (see below)
         swoopGain       depth of a swoop per radian travelled, px   ((hubR - lanes[0]) / pi)
         fibrePitch      gap between fibres of one pair, px          (0.9)
         localGain       depth of a family's own arc per radian, x R (0.2)
         localDepth      [shallowest, deepest] family arc, px        ([7, 0.17 R])
         px              sampling step, px                           (3)
       }
       A link between families runs from its mark straight in, through its
       family's hub, the shorter way round to the other family's hub, and out
       to the far mark, never through the centre: every control point stays
       at or outside lanes[0], and the spline is drawn in polar form, so it
       cannot come nearer. 'swoop' dips from hub to hub, deepest at the middle
       and the deeper the further it travels, like nested arcs of an arc
       diagram: pairs leaving a hub the same way share their first stretch
       and then part, which is what makes a bundle read as a rope. 'lanes'
       gives each family pair its own concentric lane instead (the shortest
       stretches shallowest), for a ruled look. The fibres of one pair lie
       side by side, the one reaching widest the deepest, so they do not
       cross one another. A link inside one family is a U just inside the rim
       whose depth grows with the angle it spans; a pair of links both ways
       between two components draws as two, the second a little deeper.
       `pair` (the family-pair index, -1 for a link inside one family) is the
       natural bundle key for the weave. */
    function bundle(spec) {
      var R = spec.R, cx = spec.cx, cy = spec.cy;
      var rimR = spec.rimR || R - 9, hubR = spec.hubR || 0.79 * R;
      var lanes = spec.lanes || [0.57 * R, 0.73 * R], beta = spec.beta == null ? 0.85 : spec.beta;
      var leave = spec.leave || 0.05 * R, pitch = spec.fibrePitch == null ? 0.9 : spec.fibrePitch;
      var gain = spec.localGain == null ? 0.2 : spec.localGain, ldep = spec.localDepth || [7, 0.17 * R];
      var px = spec.px || 3, shape = spec.shape || 'swoop';
      var swoop = spec.swoopGain == null ? (hubR - lanes[0]) / Math.PI : spec.swoopGain;
      var at = spec.at, group = spec.group, hub = spec.hub, links = spec.links;
      // The pairs of families with links between them, each travelling the
      // shorter way between its hubs.
      var pairAt = Object.create(null), pairs = [];
      links.forEach(function (l, k) {
        var ga = group[l[0]], gb = group[l[1]];
        if (ga === gb) return;
        var lo = Math.min(ga, gb), hi = Math.max(ga, gb), key = lo + '-' + hi;
        if (pairAt[key] === undefined) {
          var t = turn(hub[lo], hub[hi]);
          pairAt[key] = pairs.length;
          pairs.push({ lo: lo, hi: hi, travel: t, s: t >= 0 ? norm(hub[lo]) : norm(hub[hi]), len: Math.abs(t), members: [] });
        }
        pairs[pairAt[key]].members.push(k);
      });
      // Lanes: the shortest stretches shallowest; a pair takes the shallowest
      // lane no overlapping shorter pair holds.
      function within(a, p) { var d = norm(a - p.s); return d <= p.len + 1e-6; }
      function overlaps(p, q) { return within(p.s, q) || within(q.s, p) || within(p.s + p.len, q) || within(q.s + q.len, p); }
      var byLen = pairs.slice().sort(function (p, q) { return p.len - q.len || p.lo - q.lo || p.hi - q.hi; });
      byLen.forEach(function (p, i) {
        var used = Object.create(null);
        for (var j = 0; j < i; j++) if (overlaps(p, byLen[j])) used[byLen[j].lane] = true;
        var lane = 0;
        while (used[lane]) lane++;
        p.lane = lane;
      });
      var nLanes = 1 + pairs.reduce(function (m, p) { return Math.max(m, p.lane); }, 0);
      var laneGap = nLanes > 1 ? Math.min(14, (lanes[1] - lanes[0]) / (nLanes - 1)) : 0;
      pairs.forEach(function (p) { p.r = lanes[1] - p.lane * laneGap; });
      // Fibres side by side in their band: the one reaching widest deepest.
      var offset = Object.create(null);
      pairs.forEach(function (p) {
        var reach = p.members.map(function (k) {
          var l = links[k], from = group[l[0]] === p.lo ? l[0] : l[1], to = from === l[0] ? l[1] : l[0];
          var dir = p.travel >= 0 ? 1 : -1;
          // How far outside the hubs the two ends sit, along the travel.
          var w = -dir * turn(hub[p.lo], at[from]) + dir * turn(hub[p.hi], at[to]);
          return { k: k, w: w };
        }).sort(function (x, y) { return y.w - x.w || x.k - y.k; });
        var m = reach.length;
        reach.forEach(function (x, j) { offset[x.k] = (j - (m - 1) / 2) * pitch; });
      });
      return links.map(function (l, k) {
        var a = l[0], b = l[1], ga = group[a], gb = group[b];
        if (ga === gb) {
          var sw = turn(at[a], at[b]);
          // Both directions of a pair of links stay visible: the second a
          // little deeper.
          var twin = 0;
          for (var j = 0; j < k; j++) if (links[j][0] === b && links[j][1] === a) twin = 1;
          var h = clamp(gain * Math.abs(sw) * R, ldep[0], ldep[1]) + twin * 2.2;
          var e = 4 / 3 * h;
          var pol = polarBezier([at[a], rimR], [at[a], rimR - e], [at[a] + sw, rimR - e], [at[a] + sw, rimR], px);
          return { pts: polarXY(cx, cy, pol), polar: pol, local: true, pair: -1, lane: -1 };
        }
        var p = pairs[pairAt[Math.min(ga, gb) + '-' + Math.max(ga, gb)]];
        var dir = ga === p.lo ? (p.travel >= 0 ? 1 : -1) : (p.travel >= 0 ? -1 : 1);
        var hA = hub[ga], travel = ga === p.lo ? p.travel : -p.travel;
        var A0 = hA + turn(hA, at[a]), hB = hA + travel, B1 = hB + turn(hub[gb], at[b]);
        var ctrl = [[A0, rimR], [A0, rimR - leave], [hA, hubR]];
        if (shape === 'lanes') {
          // Concentric lanes: the pair's own ring, entered and left near the hubs.
          var rl = p.r + offset[k];
          var lead = Math.min(0.09, Math.abs(travel) * 0.18) * dir;
          var span = travel - 2 * lead, steps = Math.max(1, Math.ceil(Math.abs(span) / 0.32));
          for (var s = 0; s <= steps; s++) ctrl.push([hA + lead + span * s / steps, rl]);
        } else {
          // A swoop: down from the hub and back up to the other, deepest at
          // the middle and deeper the further it travels, like nested arcs of
          // an arc diagram; pairs that leave a hub the same way share their
          // first stretch, then part.
          var depth = Math.min(hubR - lanes[0], swoop * Math.abs(travel)) + offset[k];
          [0.2, 0.4, 0.5, 0.6, 0.8].forEach(function (t) {
            ctrl.push([hA + travel * t, hubR - depth * Math.sin(Math.PI * t)]);
          });
        }
        ctrl.push([hB, hubR], [B1, rimR - leave], [B1, rimR]);
        var pol2 = polarSpline(ctrl, beta, px);
        return { pts: polarXY(cx, cy, pol2), polar: pol2, local: false, pair: pairs.indexOf(p), lane: p.lane };
      });
    }

    /* taper(profile) -> function (s, len) -> width in px
       profile = {
         start   width where the fibre leaves its component   (0.3)
         body    width in the bundle                          (1.3)
         end     width where it reaches the far component     (0.65)
         rise    px over which it grows from start to body    (34)
         fall    px over which it narrows to its end          (26)
         swell   extra fraction of body at the middle         (0.18)
       }
       Thin where it leaves, fuller in the bundle, parting at the far end; the
       two ends differ, so the drawing carries direction without arrowheads. */
    function taper(p) {
      p = p || {};
      var w0 = p.start == null ? 0.3 : p.start, wb = p.body == null ? 1.3 : p.body, w1 = p.end == null ? 0.65 : p.end;
      var rise = p.rise || 34, fall = p.fall || 26, swell = p.swell == null ? 0.18 : p.swell;
      return function (s, len) {
        var r = Math.min(rise, 0.42 * len), f = Math.min(fall, 0.4 * len);
        var w = wb + (w0 - wb) * (1 - smooth01(s / r)) + (w1 - wb) * (1 - smooth01((len - s) / f));
        var t = len > 0 ? s / len : 0, bump = Math.sin(Math.PI * t);
        return Math.max(0.08, w + wb * swell * bump * bump);
      };
    }

    /* fibreStroke(pts, opts) -> path data: the route as filled outlines
       pts     the route's centre line (a polyline)
       opts = {
         width     a number, or function (s, len) -> px (see taper)
         cuts      the gaps from weave(), for this route   ([])
         step      sampling step along the route, px        (2.2)
         minPiece  shortest piece kept between two gaps, px (2.4)
       }
       Fill it, never stroke it. Each gap from the weave is cut parallel to the
       line passing over, at a constant clearance from it, so the ends of the
       line beneath are clean and the gap reads as the same width at every
       angle. Pieces left shorter than minPiece are dropped rather than drawn
       as specks. */
    function fibreStroke(pts, opts) {
      opts = opts || {};
      if (!pts || pts.length < 2) return '';
      var rs = resample(pts, opts.step || 2.2), P = rs.p, n = P.length, len = rs.len, h = rs.step;
      var wf = typeof opts.width === 'function' ? opts.width : (function (c) { return function () { return c; }; })(opts.width || 1);
      var Lx = new Float64Array(n), Ly = new Float64Array(n), Rx = new Float64Array(n), Ry = new Float64Array(n);
      for (var i = 0; i < n; i++) {
        var a = P[Math.max(0, i - 1)], b = P[Math.min(n - 1, i + 1)];
        var tx = b[0] - a[0], ty = b[1] - a[1], tl = Math.hypot(tx, ty) || 1;
        var nx = -ty / tl, ny = tx / tl, w = wf(i * h, len) / 2;
        Lx[i] = P[i][0] + nx * w; Ly[i] = P[i][1] + ny * w;
        Rx[i] = P[i][0] - nx * w; Ry[i] = P[i][1] - ny * w;
      }
      var gaps = edgeGaps(opts.cuts || [], P, h, Lx, Ly, Rx, Ry, wf, len);
      var minPiece = (opts.minPiece == null ? 2.4 : opts.minPiece) / h;
      // The pieces between the gaps, on both edges at once.
      var pieces = [], fromL = 0, fromR = 0;
      gaps.forEach(function (g) {
        pieces.push([fromL, g.inL, fromR, g.inR]);
        fromL = g.outL; fromR = g.outR;
      });
      pieces.push([fromL, n - 1, fromR, n - 1]);
      var keepL = edgeKeep(Lx, Ly, 0.1), keepR = edgeKeep(Rx, Ry, 0.1);
      var d = '';
      pieces.forEach(function (pc) {
        if (pc[1] - pc[0] < minPiece || pc[3] - pc[2] < minPiece) return;
        d += 'M' + edgeRun(Lx, Ly, pc[0], pc[1], false, keepL) + 'L' + edgeRun(Rx, Ry, pc[2], pc[3], true, keepR) + 'Z';
      });
      return d;
    }
    /* The samples of an edge worth writing: where the edge runs straight to
       within `tol` px, the samples between the ends of the run add nothing
       to the picture and only lengthen the path the browser parses and
       fills. A sample is kept wherever leaving it out would move any sample
       since the last one kept further than tol from the chord. */
    function edgeKeep(X, Y, tol) {
      var n = X.length, keep = new Uint8Array(n);
      if (n < 3) { keep.fill(1); return keep; }
      keep[0] = 1; keep[n - 1] = 1;
      var a = 0;
      for (var i = 2; i < n; i++) {
        var dx = X[i] - X[a], dy = Y[i] - Y[a], L = Math.sqrt(dx * dx + dy * dy);
        if (i - a > 48) { keep[i - 1] = 1; a = i - 1; continue; }
        if (L < 1e-9) continue;
        for (var j = a + 1; j < i; j++) {
          if (Math.abs((X[j] - X[a]) * dy - (Y[j] - Y[a]) * dx) / L > tol) { keep[i - 1] = 1; a = i - 1; break; }
        }
      }
      return keep;
    }
    /* coarse(pts, tol) -> the same polyline with the points that lie within
       tol px of a straight run left out, kept on the array so it is made
       once. The weave finds its crossings on these: a crossing moves by
       well under half a pixel, and the search, which tests segments
       against segments, has a fifth as many to test. */
    function coarse(pts, tol) {
      if (pts.__coarse) return pts.__coarse;
      var n = pts.length;
      if (n < 4) return (pts.__coarse = pts);
      var X = new Float64Array(n), Y = new Float64Array(n);
      for (var i = 0; i < n; i++) { X[i] = pts[i][0]; Y[i] = pts[i][1]; }
      var keep = edgeKeep(X, Y, tol || 0.15), out = [];
      for (var k = 0; k < n; k++) if (keep[k]) out.push(pts[k]);
      try { Object.defineProperty(pts, '__coarse', { value: out, enumerable: false }); } catch (e) {}
      return out;
    }
    // The points of one edge between two fractional sample indices, as
    // "x y L x y ..." (reversed if asked), the samples between kept ones
    // left out.
    function edgeRun(X, Y, from, to, reverse, keep) {
      var list = [];
      function at(f) { var i = Math.min(X.length - 2, Math.floor(f)), t = f - i; return nf(X[i] + (X[i + 1] - X[i]) * t) + ' ' + nf(Y[i] + (Y[i + 1] - Y[i]) * t); }
      list.push(at(from));
      for (var i = Math.floor(from) + 1; i < to; i++) if (!keep || keep[i]) list.push(nf(X[i]) + ' ' + nf(Y[i]));
      list.push(at(Math.min(to, X.length - 1)));
      if (reverse) list.reverse();
      return list.join('L');
    }
    // Where each edge of an outline enters and leaves the clear band either
    // side of the line passing over, merged where two gaps meet.
    function edgeGaps(cuts, P, h, Lx, Ly, Rx, Ry, wf, len) {
      var n = P.length, out = [];
      cuts.slice().sort(function (p, q) { return p.s - q.s; }).forEach(function (c) {
        var ic = c.s / h, wu = wf(c.s, len);
        var sin = Math.max(0.2, c.sin || 1), reach = (c.h + wu) / sin + 3 * h;
        var lo = Math.max(0, Math.floor(ic - reach / h)), hi = Math.min(n - 1, Math.ceil(ic + reach / h));
        var gl = band(Lx, Ly, c, lo, hi, ic), gr = band(Rx, Ry, c, lo, hi, ic);
        if (!gl || !gr) {
          // The edge never meets the over line near here (a very short or
          // very wide piece): cut square instead.
          var half = (c.h + wu / 2 * Math.abs(c.cos || 0)) / sin / h;
          gl = gr = [Math.max(0, ic - half), Math.min(n - 1, ic + half)];
        }
        out.push({ inL: gl[0], outL: gl[1], inR: gr[0], outR: gr[1] });
      });
      // Merge overlapping gaps.
      var merged = [];
      out.forEach(function (g) {
        var m = merged[merged.length - 1];
        if (m && (g.inL <= m.outL || g.inR <= m.outR)) {
          m.outL = Math.max(m.outL, g.outL); m.outR = Math.max(m.outR, g.outR);
          m.inL = Math.min(m.inL, g.inL); m.inR = Math.min(m.inR, g.inR);
        } else merged.push(g);
      });
      return merged;
    }
    // On one edge, the stretch around sample ic whose signed distance from the
    // over line is under the clearance.
    function band(X, Y, c, lo, hi, ic) {
      function dist(i) { return (X[i] - c.x) * c.nx + (Y[i] - c.y) * c.ny; }
      // The sign change nearest the crossing.
      var best = -1, bd = Infinity;
      for (var i = lo; i < hi; i++) {
        var d0 = dist(i), d1 = dist(i + 1);
        if ((d0 <= 0 && d1 >= 0) || (d0 >= 0 && d1 <= 0)) { var dd = Math.abs(i + 0.5 - ic); if (dd < bd) { bd = dd; best = i; } }
      }
      if (best < 0) return null;
      var H = c.h, k = best, entry, exit;
      while (k >= lo && Math.abs(dist(k)) < H) k--;
      if (k < lo) entry = lo;
      else { var a = dist(k), b = dist(k + 1), tgt = a > 0 ? H : -H; entry = k + (a - tgt) / ((a - b) || 1); }
      k = best + 1;
      while (k <= hi && Math.abs(dist(k)) < H) k++;
      if (k > hi) exit = hi;
      else { var a2 = dist(k - 1), b2 = dist(k), tgt2 = b2 > 0 ? H : -H; exit = k - 1 + (a2 - tgt2) / ((a2 - b2) || 1); }
      return [clamp(entry, 0, X.length - 1), clamp(exit, 0, X.length - 1)];
    }

    /* strokeGaps(pts, cuts, width) -> path data for a plain stroked line with
       the weave's gaps (cut square, so use stroke-linecap: butt). For a line
       drawn with stroke rather than fibreStroke. */
    function strokeGaps(pts, cuts, width) {
      var cum = measure(pts), len = cum[cum.length - 1], iv = [];
      (cuts || []).forEach(function (c) {
        var sin = Math.max(0.2, c.sin || 1), g = (c.h + (width || 1) / 2 * Math.abs(c.cos || 0)) / sin;
        iv.push([c.s - g, c.s + g]);
      });
      iv.sort(function (p, q) { return p[0] - q[0]; });
      var keep = [], from = 0;
      iv.forEach(function (g) { if (g[0] > from) keep.push([from, g[0]]); from = Math.max(from, g[1]); });
      if (from < len) keep.push([from, len]);
      var d = '';
      keep.forEach(function (k) {
        if (k[1] - k[0] < 1.5) return;
        var run = [], a = pointAt(pts, k[0], cum);
        run.push([a.x, a.y]);
        for (var i = 0; i < pts.length; i++) if (cum[i] > k[0] && cum[i] < k[1]) run.push(pts[i]);
        var b = pointAt(pts, k[1], cum);
        run.push([b.x, b.y]);
        d += lineD(run);
      });
      return d;
    }

    /* ---- The weave ------------------------------------------------------------ */

    /* weave(strands, opts) -> { cuts, crossings, stats }
       strands  [{ pts, ink, rank, width, bundle }]: pts a polyline; ink 'red'
                or 'azure' (any two names); rank a number, higher for what is
                lit; width a number or function (s, len) -> px (a taper);
                bundle an optional key shared by strands that travel together
                (a rope of fibres of one family pair, a fan of rule lines
                leaving one end), so they weave as one.
       opts = {
         rankTolerance  ranks this close weave as equals                  (0)
         clearance      clear space either side of the line passing over (1.1)
         minAngle       crossings shallower than this many degrees are not
                        woven; the line drawn later simply covers        (16)
         endGuard       no gap within this many px of a line's ends      (9)
         merge          two meetings of one pair this close (px along the
                        line) are one crossing                           (1.2)
         ropeGap        crossings of the same two bundles this close (px)
                        are one crossing of the bundles                  (4)
         ropeMin        strands a lesser bundle needs to count as a rope (3)
         ropeWidth      and how tight it must be, px along each thread   (6)
         dive           whether a lit thread dives under ropes      (true)
         cell           grid cell for the spatial index, px              (28)
       }
       Finds every crossing between strands of different inks with a uniform
       grid of segments (each segment tested only against segments sharing a
       cell, each pair once), then decides over and under, bundle by bundle.
       Crossings between the same two bundles that lie together are a single
       unit, so a rope passes a ribbon whole. Units between equals alternate
       along every bundle, as in a plait: each bundle takes a phase, chosen
       breadth first from the most important and then improved by flips, so
       its k-th unit passes over when k + phase is even and both sides of a
       unit agree; where a cycle of crossings makes that impossible, the more
       important bundle keeps its rhythm. Across ranks, the lit thread passes
       over single strands (never broken by a stray fibre) and meets tight
       ropes alternately, over one and under the next. Returns, for each
       strand, the cuts it takes where it passes under ({ s, x, y, nx, ny, h,
       sin, cos, over }, sorted by s; hand them to fibreStroke or strokeGaps),
       and, for inspection, every crossing and every unit (its two bundle keys,
       strand counts, ranks, place along each bundle and who passed over).
       Run it again whenever the lit set, and so the ranks or widths, changes. */
    function weave(strands, opts) {
      opts = opts || {};
      var t0 = now();
      var tolR = opts.rankTolerance || 0, clear = opts.clearance == null ? 1.1 : opts.clearance;
      var minSin = Math.sin((opts.minAngle == null ? 16 : opts.minAngle) * Math.PI / 180);
      var guard = opts.endGuard == null ? 9 : opts.endGuard, cell = opts.cell || 28;
      var S = strands.map(function (st, i) {
        var cum = measure(st.pts);
        var wv = st.width, wfn = typeof wv === 'function' ? wv : (function (c) { return function () { return c; }; })(wv || 1);
        return { i: i, pts: st.pts, cum: cum, len: cum[cum.length - 1], ink: st.ink, rank: st.rank || 0, w: wfn, xs: [] };
      });
      var inks = [];
      S.forEach(function (s) { if (inks.indexOf(s.ink) < 0) inks.push(s.ink); });
      var crossings = [], segCount = 0;
      S.forEach(function (s) { segCount += s.pts.length - 1; });
      if (inks.length === 2) {
        // Index the ink with fewer segments; query with the other.
        var count = [0, 0];
        S.forEach(function (s) { count[inks.indexOf(s.ink)] += s.pts.length - 1; });
        var ix = count[0] <= count[1] ? inks[0] : inks[1];
        var grid = new Map(), segS = [], segK = [];
        S.forEach(function (s) {
          if (s.ink !== ix) return;
          for (var k = 0; k < s.pts.length - 1; k++) {
            var a = s.pts[k], b = s.pts[k + 1], id = segS.length;
            segS.push(s.i); segK.push(k);
            var x0 = Math.floor(Math.min(a[0], b[0]) / cell), x1 = Math.floor(Math.max(a[0], b[0]) / cell);
            var y0 = Math.floor(Math.min(a[1], b[1]) / cell), y1 = Math.floor(Math.max(a[1], b[1]) / cell);
            for (var gx = x0; gx <= x1; gx++) for (var gy = y0; gy <= y1; gy++) {
              var key = gx * 100003 + gy, bucket = grid.get(key);
              if (bucket) bucket.push(id); else grid.set(key, [id]);
            }
          }
        });
        var stamp = new Int32Array(segS.length).fill(-1), q = 0;
        S.forEach(function (s) {
          if (s.ink === ix) return;
          for (var k = 0; k < s.pts.length - 1; k++, q++) {
            var a = s.pts[k], b = s.pts[k + 1];
            var x0 = Math.floor(Math.min(a[0], b[0]) / cell), x1 = Math.floor(Math.max(a[0], b[0]) / cell);
            var y0 = Math.floor(Math.min(a[1], b[1]) / cell), y1 = Math.floor(Math.max(a[1], b[1]) / cell);
            for (var gx = x0; gx <= x1; gx++) for (var gy = y0; gy <= y1; gy++) {
              var bucket = grid.get(gx * 100003 + gy);
              if (!bucket) continue;
              for (var m = 0; m < bucket.length; m++) {
                var id = bucket[m];
                if (stamp[id] === q) continue;
                stamp[id] = q;
                var o = S[segS[id]], kk = segK[id], c = o.pts[kk], e = o.pts[kk + 1];
                var rx = b[0] - a[0], ry = b[1] - a[1], sx = e[0] - c[0], sy = e[1] - c[1];
                var den = rx * sy - ry * sx;
                if (Math.abs(den) < 1e-12) continue;
                var qx = c[0] - a[0], qy = c[1] - a[1];
                var t = (qx * sy - qy * sx) / den, u = (qx * ry - qy * rx) / den;
                if (t < 0 || t >= 1 || u < 0 || u >= 1) continue;
                var la = Math.hypot(rx, ry), lb = Math.hypot(sx, sy);
                var sa = s.cum[k] + t * la, sb = o.cum[kk] + u * lb;
                if (sa < guard || sa > s.len - guard || sb < guard || sb > o.len - guard) continue;
                var sinv = Math.abs(den) / (la * lb), cosv = (rx * sx + ry * sy) / (la * lb);
                crossings.push({ a: s.i, b: o.i, sa: sa, sb: sb, x: a[0] + rx * t, y: a[1] + ry * t,
                                 ta: [rx / la, ry / la], tb: [sx / lb, sy / lb], sin: sinv, cos: cosv });
              }
            }
          }
        });
      }
      // One crossing per place: where two lines meet twice within `merge` px
      // (a sharp turn at a vertex), the eye sees one crossing, so the weave
      // makes one.
      var merge = opts.merge == null ? 1.2 : opts.merge;
      crossings.sort(function (p, q) { return p.a - q.a || p.b - q.b || p.sa - q.sa; });
      crossings = crossings.filter(function (c, k) {
        var p = crossings[k - 1];
        return !(p && p.a === c.a && p.b === c.b && Math.abs(p.sa - c.sa) < merge);
      });
      // Units. A strand's bundle is its own key unless it names one (a rope of
      // fibres sharing a family pair, a ribbon of rule lines sharing an end);
      // the woven crossings between one bundle of each ink that lie within
      // ropeGap px of one another are a single crossing of the two bundles.
      var ropeMin = opts.ropeMin == null ? 3 : opts.ropeMin, ropeGap = opts.ropeGap == null ? 4 : opts.ropeGap;
      var keyOf = S.map(function (s, i) { var b = strands[i].bundle; return s.ink + (b != null ? ':' + b : '#' + i); });
      var byPair = new Map();
      crossings.forEach(function (c) {
        c.woven = c.sin >= minSin;
        if (!c.woven) { c.over = -1; return; }
        var ka = keyOf[c.a], kb = keyOf[c.b], key = ka + '|' + kb;
        var list = byPair.get(key);
        if (list) list.push(c); else byPair.set(key, [c]);
      });
      var units = [];
      byPair.forEach(function (list) {
        var n = list.length, parent = new Int32Array(n);
        for (var i = 0; i < n; i++) parent[i] = i;
        function root(i) { while (parent[i] !== i) { parent[i] = parent[parent[i]]; i = parent[i]; } return i; }
        if (n > 1) {
          for (var i2 = 0; i2 < n; i2++) for (var j2 = i2 + 1; j2 < n; j2++) {
            if (Math.abs(list[i2].x - list[j2].x) <= ropeGap && Math.abs(list[i2].y - list[j2].y) <= ropeGap &&
                Math.hypot(list[i2].x - list[j2].x, list[i2].y - list[j2].y) <= ropeGap) parent[root(i2)] = root(j2);
          }
        }
        var groups = Object.create(null);
        for (var k = 0; k < n; k++) { var r = root(k); (groups[r] = groups[r] || []).push(list[k]); }
        Object.keys(groups).forEach(function (r) {
          var cs = groups[r], A = Object.create(null), B = Object.create(null), na = 0, nb = 0, ra = -Infinity, rb = -Infinity, ta = 0, tb = 0;
          cs.forEach(function (c) {
            if (!A[c.a]) { A[c.a] = 1; na++; ra = Math.max(ra, S[c.a].rank); }
            if (!B[c.b]) { B[c.b] = 1; nb++; rb = Math.max(rb, S[c.b].rank); }
            ta += c.sa / (S[c.a].len || 1); tb += c.sb / (S[c.b].len || 1);
          });
          units.push({ cs: cs, ka: keyOf[cs[0].a], kb: keyOf[cs[0].b], na: na, nb: nb, ra: ra, rb: rb, ta: ta / cs.length, tb: tb / cs.length });
        });
      });
      // Which units alternate: two bundles of equal standing always do; a more
      // important bundle passes over a single strand of a lesser one, and
      // meets a lesser rope (ropeMin strands or more) alternately.
      // A lesser bundle counts as a rope only where it is tight: along each
      // strand of the greater one, its crossings fall within ropeWidth px.
      var ropeWidth = opts.ropeWidth == null ? 6 : opts.ropeWidth;
      function tight(u, hiA) {
        var range = Object.create(null);
        u.cs.forEach(function (c) {
          var h = hiA ? c.a : c.b, at = hiA ? c.sa : c.sb, r = range[h];
          if (!r) range[h] = [at, at]; else { r[0] = Math.min(r[0], at); r[1] = Math.max(r[1], at); }
        });
        for (var h in range) if (range[h][1] - range[h][0] > ropeWidth) return false;
        return true;
      }
      units.forEach(function (u) {
        if (Math.abs(u.ra - u.rb) <= tolR) u.alt = true;
        else {
          var hiA = u.ra > u.rb;
          u.alt = (hiA ? u.nb : u.na) >= ropeMin && tight(u, hiA);
          if (!u.alt) u.over = hiA ? 'a' : 'b';
        }
      });
      // Each bundle's alternating units, numbered along it.
      var nodes = new Map();
      function node(key) { var nd = nodes.get(key); if (!nd) { nd = { key: key, units: [], rank: -Infinity, len: 0, phase: -1 }; nodes.set(key, nd); } return nd; }
      S.forEach(function (s, i) { var nd = node(keyOf[i]); nd.rank = Math.max(nd.rank, s.rank); nd.len += s.len; });
      units.forEach(function (u) { if (u.alt) { node(u.ka).units.push(u); node(u.kb).units.push(u); } });
      nodes.forEach(function (nd) {
        nd.units.sort(function (p, q) { return (p.ka === nd.key ? p.ta : p.tb) - (q.ka === nd.key ? q.ta : q.tb); });
        nd.units.forEach(function (u, k) { if (u.ka === nd.key) u.ia = k; else u.ib = k; });
      });
      var order = Array.from(nodes.values()).sort(function (p, q) { return q.rank - p.rank || q.len - p.len || (p.key < q.key ? -1 : 1); });
      order.forEach(function (nd, k) { nd.importance = k; });
      // Phases, breadth first from the most important bundle, so both
      // bundles at a unit agree on who passes over.
      order.forEach(function (rootNd) {
        if (rootNd.phase >= 0 || !rootNd.units.length) return;
        rootNd.phase = 0;
        var queue = [rootNd];
        for (var qi = 0; qi < queue.length; qi++) {
          var p = queue[qi];
          p.units.forEach(function (u) {
            var other = nodes.get(u.ka === p.key ? u.kb : u.ka);
            if (other.phase < 0) { other.phase = p.phase ^ 1 ^ ((u.ia + u.ib) & 1); queue.push(other); }
          });
        }
      });
      function bad(u) { return ((u.ia + nodes.get(u.ka).phase) & 1) === ((u.ib + nodes.get(u.kb).phase) & 1); }
      for (var pass = 0; pass < 12; pass++) {
        var flipped = false;
        order.forEach(function (nd) {
          if (nd.phase < 0) return;
          var before = 0, after = 0;
          nd.units.forEach(function (u) { if (bad(u)) before++; });
          nd.phase ^= 1;
          nd.units.forEach(function (u) { if (bad(u)) after++; });
          if (after < before) flipped = true; else nd.phase ^= 1;
        });
        if (!flipped) break;
      }
      var cuts = S.map(function () { return []; }), conflicts = 0, woven = 0, alternating = 0, ropes = 0;
      units.forEach(function (u) {
        woven += u.cs.length;
        if (u.alt && Math.abs(u.ra - u.rb) > tolR) ropes++;
        var side = u.over;
        if (u.alt) {
          alternating++;
          var NA = nodes.get(u.ka), NB = nodes.get(u.kb);
          var oa = ((u.ia + NA.phase) & 1) === 0, ob = ((u.ib + NB.phase) & 1) === 0;
          if (oa !== ob) side = oa ? 'a' : 'b';
          else {
            conflicts++;
            var prefA = NA.importance < NB.importance;
            side = prefA ? (oa ? 'a' : 'b') : (ob ? 'b' : 'a');
          }
        }
        u.cs.forEach(function (c) {
          var over = side === 'a' ? c.a : c.b, under = over === c.a ? c.b : c.a, O = S[over];
          var so = over === c.a ? c.sa : c.sb, su = under === c.a ? c.sa : c.sb, tov = over === c.a ? c.ta : c.tb;
          c.over = over;
          cuts[under].push({ s: su, x: c.x, y: c.y, nx: -tov[1], ny: tov[0], h: O.w(so, O.len) / 2 + clear,
                             sin: c.sin, cos: c.cos, over: over });
        });
      });
      cuts.forEach(function (list) { list.sort(function (p, q) { return p.s - q.s; }); });
      return {
        cuts: cuts, crossings: crossings, units: units,
        stats: { strands: S.length, segments: segCount, crossings: crossings.length, woven: woven, units: units.length,
                 alternating: alternating, conflicts: conflicts, ropes: ropes, ms: now() - t0 }
      };
    }

    /* ---- Rule lines: fine, straight, radial ------------------------------------ */

    /* polarRun(way, corner, px) -> polar points
       A line through polar waypoints [[angle, radius], ...] whose every run is
       either radial (two waypoints at one angle) or a true arc (two at one
       radius), each corner rounded with radius `corner` px (less where a run
       is short). Set it on the page with polarXY. The grammar of every rule
       line: straight runs and arcs, as drawn with a ruling pen and compass. */
    function polarRun(way, corner, px) {
      px = px || 3;
      corner = corner == null ? 6 : corner;
      var pts = [];
      way.forEach(function (w) { var p = pts[pts.length - 1]; if (!p || Math.abs(p[0] - w[0]) > 1e-9 || Math.abs(p[1] - w[1]) > 1e-9) pts.push(w); });
      var out = [pts[0].slice()];
      function radial(p, q) { return Math.abs(q[0] - p[0]) < 1e-9; }
      function concentric(p, q) { return Math.abs(q[1] - p[1]) < 1e-9; }
      function len(p, q) { return radial(p, q) ? Math.abs(q[1] - p[1]) : concentric(p, q) ? Math.abs(q[0] - p[0]) * p[1] : Math.hypot(Math.abs(q[0] - p[0]) * (p[1] + q[1]) / 2, q[1] - p[1]); }
      function toward(p, q, d) {
        var L = len(p, q) || 1, t = Math.min(1, d / L);
        return [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t];
      }
      function run(p, q) {
        var k = Math.max(1, Math.ceil(len(p, q) / px));
        for (var j = 1; j <= k; j++) out.push([p[0] + (q[0] - p[0]) * j / k, p[1] + (q[1] - p[1]) * j / k]);
      }
      var cur = pts[0];
      for (var i = 1; i < pts.length; i++) {
        var c = pts[i];
        if (i === pts.length - 1) { run(cur, c); break; }
        var nx = pts[i + 1], k = Math.min(corner, len(cur, c), len(c, nx) / 2);
        if (k < 0.3) { run(cur, c); cur = c; continue; }
        var A = toward(c, cur, k), B = toward(c, nx, k);
        run(cur, A);
        var XY = polarXY(0, 0, [A, c, B]);
        for (var s = 1; s <= 7; s++) {
          var u = s / 7, v = 1 - u;
          var x = v * v * XY[0][0] + 2 * v * u * XY[1][0] + u * u * XY[2][0];
          var y = v * v * XY[0][1] + 2 * v * u * XY[1][1] + u * u * XY[2][1];
          out.push([c[0] + turn(c[0], Math.atan2(y, x)), Math.hypot(x, y)]);
        }
        cur = B;
      }
      return out;
    }

    /* ruleFan(spec) -> [{ pts, target, radius }] (one polyline per target, in order)
       Azure lines that share one end: from a component on the rim in to the
       rules its page cites, or from a rule out to the components citing it.
       spec = {
         cx, cy
         from     { a, r }: the shared end (angle, radius)
         to       [{ a, r, port, hook }]: each other end. The line runs in on
                  angle `port` (default a) to radius r; `hook`, if given, is
                  the short curve (page points) from there onto a glyph that
                  could not be reached straight down its radius (see
                  clearPort)
         ring     [near, far]: the band the lines travel round, near on the
                  shared end's side
         pitch    gap between lines travelling side by side, px     (1.7);
                  0 lays every line going one way on a single spine at
                  `near`, from which each peels off at its own angle like
                  a tooth of a comb (the map's choice: calm and fine)
         spread   gap between lines leaving the shared end, px      (1.5);
                  0 makes them leave as one trunk
         gather   px over which lines leaving a glyph fan out from one point
                  (0: they leave already side by side, as from a rim mark)
         corner   radius of the rounded corners, px                 (7)
       }
       Each line runs radially from the shared end to its own radius in the
       band, round the band as a concentric arc, then radially to its far end:
       straight runs and true arcs (polarRun), never a free curve. The longer
       a line's trip round the ring, the nearer the shared end it turns, and
       the lines leave side by side in the order they turn off, so no two
       lines of one fan cross. */
    function ruleFan(spec) {
      var cx = spec.cx, cy = spec.cy, F = spec.from, T = spec.to;
      var near = spec.ring[0], far = spec.ring[1], sgn = far >= near ? 1 : -1;
      var pitch = spec.pitch == null ? 1.7 : spec.pitch, spread = spec.spread == null ? 1.5 : spec.spread;
      var corner = spec.corner == null ? 7 : spec.corner, gather = spec.gather || 0, px = spec.px || 3;
      var items = T.map(function (t, i) {
        var port = t.port == null ? t.a : t.port;
        return { i: i, t: t, sweep: turn(F.a, port) };
      });
      var eps = 0.003;
      var ccw = items.filter(function (x) { return x.sweep < -eps; }).sort(function (p, q) { return p.sweep - q.sweep || p.i - q.i; });
      var cw = items.filter(function (x) { return x.sweep > eps; }).sort(function (p, q) { return q.sweep - p.sweep || p.i - q.i; });
      var straight = items.filter(function (x) { return Math.abs(x.sweep) <= eps; });
      var room = Math.abs(far - near);
      [ccw, cw].forEach(function (g) {
        var p = g.length > 1 ? Math.min(pitch, room / (g.length - 1)) : 0;
        g.forEach(function (x, k) { x.rr = near + sgn * k * p; });
      });
      straight.forEach(function (x) { x.rr = near; });
      var ribbon = ccw.concat(straight, cw.slice().reverse()), m = ribbon.length;
      ribbon.forEach(function (x, j) { x.off = (j - (m - 1) / 2) * spread; });
      var out = new Array(T.length);
      items.forEach(function (x) {
        var a0 = F.a + x.off / Math.max(F.r, 1), port = F.a + x.sweep, rr = x.rr, tr = x.t.r;
        var dirR = rr >= F.r ? 1 : -1, pol = [], way;
        var g = gather ? Math.min(gather, Math.abs(rr - F.r) * 0.6) : 0;
        if (g > 0) {
          polarBezier([F.a, F.r], [F.a, F.r + dirR * g * 0.55], [a0, F.r + dirR * g * 0.45], [a0, F.r + dirR * g], 2, pol);
          way = [[a0, F.r + dirR * g]];
        } else way = [[a0, F.r]];
        if (Math.abs(x.sweep) <= eps) {
          // Straight in: an S onto the end's own angle if the ribbon set it aside.
          var last = way[0];
          polarBezier(last, [last[0], (last[1] + tr) / 2], [port, (last[1] + tr) / 2], [port, tr], px, pol, pol.length > 0);
        } else {
          way.push([a0, rr], [port, rr], [port, tr]);
          var run = polarRun(way, corner, px);
          pol = pol.concat(pol.length ? run.slice(1) : run);
        }
        var pts = polarXY(cx, cy, pol);
        if (x.t.hook) pts = pts.concat(x.t.hook.slice(1));
        out[x.i] = { pts: pts, target: x.i, radius: rr };
      });
      return out;
    }

    /* clearPort(glyphs, id, rFrom, opts) -> { port, r, hook }
       How a rule line should arrive at glyph `id` from radius rFrom: straight
       down the glyph's own radius when that run is clear of every other
       glyph; else down the nearest clear radius beside it (`port`) to radius
       `r`, then along `hook`, a short curve (page points) onto the glyph.
       glyphs = { id: { a, r, size } }; opts = { cx, cy, clearance (3),
       stepDeg (1.5), maxDeg (14) } */
    function clearPort(glyphs, id, rFrom, opts) {
      opts = opts || {};
      var G = glyphs[id], clear = opts.clearance == null ? 3 : opts.clearance;
      var step = (opts.stepDeg || 1.5) * Math.PI / 180, most = (opts.maxDeg || 14) * Math.PI / 180;
      var sideOut = rFrom > G.r ? 1 : -1, edge = G.r + sideOut * (G.size / 2 + 2);
      function clearRun(a, r0, r1) {
        var lo = Math.min(r0, r1), hi = Math.max(r0, r1);
        for (var k in glyphs) {
          if (k === id) continue;
          var O = glyphs[k];
          if (O.r < lo - O.size || O.r > hi + O.size) continue;
          var rr = clamp(O.r, lo, hi);
          var dx = rr * Math.cos(a) - O.r * Math.cos(O.a), dy = rr * Math.sin(a) - O.r * Math.sin(O.a);
          if (Math.hypot(dx, dy) < O.size / 2 + clear) return false;
        }
        return true;
      }
      if (clearRun(G.a, rFrom, edge)) return { port: G.a, r: edge, hook: null };
      var stop = G.r + sideOut * (G.size + 7);
      for (var d = step; d <= most + 1e-9; d += step) {
        var cands = [G.a + d, G.a - d];
        for (var c = 0; c < 2; c++) {
          if (!clearRun(cands[c], rFrom, stop)) continue;
          var pol = polarBezier([cands[c], stop], [cands[c], G.r + (stop - G.r) * 0.45], [G.a, G.r + (stop - G.r) * 0.75], [G.a, edge], 2);
          return { port: cands[c], r: stop, hook: polarXY(opts.cx || 0, opts.cy || 0, pol) };
        }
      }
      return { port: G.a, r: edge, hook: null };
    }

    /* trimEnds(pts, r0, r1) -> pts with everything within r0 px (straight-line
       distance) of the first point and within r1 px of the last removed, so a
       line stops short of the glyphs it joins. */
    function trimEnds(pts, r0, r1) {
      var a = pts[0], b = pts[pts.length - 1];
      function inside(p) { return Math.hypot(p[0] - a[0], p[1] - a[1]) < r0 || Math.hypot(p[0] - b[0], p[1] - b[1]) < r1; }
      var out = [];
      for (var i = 0; i < pts.length; i++) {
        var inI = inside(pts[i]);
        if (i > 0 && inside(pts[i - 1]) !== inI) {
          var p = pts[i - 1], q = pts[i], lo = 0, hi = 1, inP = !inI;
          for (var k = 0; k < 24; k++) {
            var mid = (lo + hi) / 2, x = [p[0] + (q[0] - p[0]) * mid, p[1] + (q[1] - p[1]) * mid];
            if (inside(x) === inP) lo = mid; else hi = mid;
          }
          var t = (lo + hi) / 2;
          out.push([p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]);
        }
        if (!inI) out.push(pts[i]);
      }
      return out.length > 1 ? out : pts;
    }

    /* ---- The doctrine core ----------------------------------------------------- */

    // For each set of places on a ring of n (a bit mask), the shortest arc
    // holding them all: the place it starts at and how many steps it runs.
    function coverTable(n) {
      var size = 1 << n, st = new Int8Array(size), ln = new Int8Array(size);
      for (var m = 1; m < size; m++) {
        var bits = [];
        for (var p = 0; p < n; p++) if (m & (1 << p)) bits.push(p);
        if (bits.length === 1) { st[m] = bits[0]; ln[m] = 0; continue; }
        var bestGap = -1, start = 0;
        for (var k = 0; k < bits.length; k++) {
          var a = bits[k], b = bits[(k + 1) % bits.length], gap = (b - a + n) % n || n;
          if (gap > bestGap) { bestGap = gap; start = b; }
        }
        st[m] = start; ln[m] = n - bestGap;
      }
      return { start: st, len: ln };
    }
    // The places strictly inside an arc, as a mask, for every start and length.
    function interiorTable(n) {
      var t = new Int32Array(n * (n + 1));
      for (var s = 0; s < n; s++) for (var l = 0; l <= n; l++) {
        var m = 0;
        for (var k = 1; k < l; k++) m |= 1 << ((s + k) % n);
        t[s * (n + 1) + l] = m;
      }
      return t;
    }
    /* The cost of an order: the bridges' spans, plus a weight per crossing,
       plus a little for long spans. Two bridges cross when their spans partly
       overlap, or when one holds the other and reaches a hub strictly inside
       it (its riser to that hub must pass the inner one's lane). */
    function makeCost(n, groups, opts) {
      var table = coverTable(n), inner = interiorTable(n), n1 = n + 1;
      var crossW = opts.crossWeight == null ? 2 : opts.crossWeight, sqW = opts.squareWeight == null ? 0.05 : opts.squareWeight;
      var G = groups.length, mask = new Int32Array(G), S = new Int32Array(G), L = new Int32Array(G);
      return function cost(pos, detail) {
        var length = 0, sq = 0, x = 0, g, i, j, k;
        for (g = 0; g < G; g++) {
          var m = 0, grp = groups[g];
          for (k = 0; k < grp.length; k++) m |= 1 << pos[grp[k]];
          mask[g] = m; S[g] = table.start[m]; L[g] = table.len[m];
          length += L[g]; sq += L[g] * L[g];
        }
        for (i = 0; i < G; i++) {
          var si = S[i], li = L[i];
          for (j = i + 1; j < G; j++) {
            var sj = S[j], lj = L[j];
            var ds = (sj - si + n) % n, de = (sj + lj - si + 2 * n) % n;
            var inS = ds > 0 && ds < li, inE = de > 0 && de < li, outS = ds > li, outE = de > li;
            if ((inS && outE) || (inE && outS)) { x++; continue; }
            var jInI = ds + lj <= li, iInJ = ((si - sj + n) % n) + li <= lj;
            if ((jInI && (mask[i] & inner[sj * n1 + lj])) || (iInJ && (mask[j] & inner[si * n1 + li]))) x++;
          }
        }
        var c = length + crossW * x + sqW * sq;
        return detail ? { cost: c, length: length, crossings: x, covers: Array.prototype.slice.call(L) } : c;
      };
    }
    /* hubCost(order, groups, opts) -> { cost, length, crossings, covers }
       The cost hubOrder minimises, for any given order (to compare a pinned
       order with a fresh one, or to test). opts as for hubOrder. */
    function hubCost(order, groups, opts) {
      var n = order.length, idx = Object.create(null), pos = new Int32Array(n);
      order.forEach(function (h, i) { idx[h] = i; pos[i] = i; });
      var G = groups.map(function (g) { return g.map(function (h) { return idx[h]; }).filter(function (i) { return i !== undefined; }); })
        .filter(function (g) { return g.length > 1; });
      return makeCost(n, G, opts || {})(pos, true);
    }
    // An order's name up to turning and mirroring, to tell orders apart.
    function orderKey(o) {
      var n = o.length, at = o.indexOf(0), a = [], b = [];
      for (var k = 0; k < n; k++) { a.push(o[(at + k) % n]); b.push(o[(at - k + n) % n]); }
      var x = a.join(','), y = b.join(',');
      return x < y ? x : y;
    }

    /* hubOrder(hubs, groups, opts) -> { order, cost, length, crossings, covers, candidates, ms }
       hubs    the hub ids (the axioms)
       groups  for each rule tied to two or more hubs, the ids it is tied to
       opts = {
         seed (7)  restarts (6)  steps (2500)
         crossWeight   cost of a crossing between two bridges, in hub steps  (2)
         squareWeight  cost of each span squared, so long ones stay few     (0.05)
         keep          how many of the best distinct orders to return        (6)
       }
       The circular order of the hubs that keeps the bridges short and
       uncrossed. A bridge's span is the fewest hub steps of an arc holding
       all its hubs. Simulated annealing over swaps, reversals and moves from
       seeded starts, then exhaustive local swaps and reversals until none
       improves. `candidates` holds the best distinct orders (up to turning
       and mirroring), best first, for a layout to choose among. */
    function hubOrder(hubs, groups, opts) {
      opts = opts || {};
      var t0 = now(), n = hubs.length, idx = Object.create(null);
      hubs.forEach(function (h, i) { idx[h] = i; });
      var G = groups.map(function (g) { return g.map(function (h) { return idx[h]; }).filter(function (i) { return i !== undefined; }); })
        .filter(function (g) { return g.length > 1; });
      var cost = makeCost(n, G, opts), rand = rng(opts.seed == null ? 7 : opts.seed);
      var restarts = opts.restarts || 6, steps = opts.steps || 2500, keepN = opts.keep || 6;
      var pos = new Int32Array(n);
      function costOf(order) { for (var k = 0; k < n; k++) pos[order[k]] = k; return cost(pos); }
      var pool = Object.create(null);
      function remember(o, c) {
        var key = orderKey(o);
        if (!pool[key] || pool[key].c > c) pool[key] = { c: c, o: o.slice() };
      }
      function polish(o, c) {
        var improved = true;
        while (improved) {
          improved = false;
          for (var a = 0; a < n; a++) for (var b = a + 1; b < n; b++) {
            var sw = o.slice(), t = sw[a]; sw[a] = sw[b]; sw[b] = t;
            var cs = costOf(sw);
            if (cs < c - 1e-9) { o = sw; c = cs; improved = true; continue; }
            var rv = o.slice(0, a).concat(o.slice(a, b + 1).reverse(), o.slice(b + 1)), cr = costOf(rv);
            if (cr < c - 1e-9) { o = rv; c = cr; improved = true; }
          }
        }
        return { o: o, c: c };
      }
      for (var rs = 0; rs < restarts; rs++) {
        var o = hubs.map(function (h, i) { return i; });
        for (var k = n - 1; k > 0; k--) { var j = Math.floor(rand() * (k + 1)), t = o[k]; o[k] = o[j]; o[j] = t; }
        var c = costOf(o), best = { o: o.slice(), c: c };
        for (var st = 0; st < steps; st++) {
          var temp = 3 * Math.pow(0.003, st / steps);
          var a = Math.floor(rand() * n), b = Math.floor(rand() * n), r = rand(), o2 = o.slice();
          if (a === b) b = (a + 1) % n;
          if (r < 0.4) { var tt = o2[a]; o2[a] = o2[b]; o2[b] = tt; }
          else if (r < 0.75) { var lo = Math.min(a, b), hi = Math.max(a, b); while (lo < hi) { var t2 = o2[lo]; o2[lo] = o2[hi]; o2[hi] = t2; lo++; hi--; } }
          else { var it = o2.splice(a, 1)[0]; o2.splice(b, 0, it); }
          var c2 = costOf(o2);
          if (c2 <= c || rand() < Math.exp((c - c2) / temp)) { o = o2; c = c2; }
          if (c < best.c - 1e-9) best = { o: o.slice(), c: c };
        }
        var p = polish(best.o, best.c);
        remember(p.o, p.c);
      }
      var cands = Object.keys(pool).map(function (k) { return pool[k]; }).sort(function (p, q) { return p.c - q.c; }).slice(0, keepN);
      var top = cands[0];
      for (var q = 0; q < n; q++) pos[top.o[q]] = q;
      var det = cost(pos, true);
      return {
        order: top.o.map(function (i) { return hubs[i]; }), cost: det.cost, length: det.length, crossings: det.crossings, covers: det.covers,
        candidates: cands.map(function (x) { return { order: x.o.map(function (i) { return hubs[i]; }), cost: x.c }; }), ms: now() - t0
      };
    }

    /* bridgePlan(n, bridges, cap) -> { bridges, chords, crossings, depth, total }
       The inside of the hub ring as a circular arc diagram. Hubs stand at
       places 0..n-1; each bridge glyph stands in a gap between two hubs
       inside its own span (at most `cap` to a gap); each of its lines is a
       chord from the glyph to one of its hubs, drawn as a U whose depth is
       the chord's lane (0 the shallowest). A chord held inside another rides
       shallower, so chords cross only where their ends interleave round the
       ring; the gaps are chosen (from each bridge's median hub, then by
       single moves until none helps) to make those crossings as few and the
       chords as short as they can be. Chords that do not overlap may share a
       lane; the two halves of one bridge may meet under its own glyph.
       Runs on flat typed arrays: the layout tries a few hundred plans. */
    function bridgePlan(n, bridges, cap) {
      var table = coverTable(n), EPS = 1e-6;
      var B = bridges.map(function (places, i) {
        var m = 0;
        places.forEach(function (p) { m |= 1 << p; });
        var s = table.start[m], L = table.len[m];
        var offs = places.map(function (p) { return (p - s + n) % n; }).sort(function (a, b) { return a - b; });
        var mid = offs.length % 2 ? offs[(offs.length - 1) / 2] : (offs[offs.length / 2 - 1] + offs[offs.length / 2]) / 2;
        var mean = offs.reduce(function (t, o) { return t + o; }, 0) / offs.length;
        return { i: i, places: places, s: s, L: L, offs: offs, mid: mid, mean: mean, gap: 0, frac: 0.5 };
      });
      var count = new Int32Array(n);
      B.slice().sort(function (x, y) { return x.L - y.L || x.i - y.i; }).forEach(function (x) {
        var opts = [];
        for (var j = 0; j < x.L; j++) opts.push(j);
        opts.sort(function (p, q) { return Math.abs(p + 0.5 - x.mid) - Math.abs(q + 0.5 - x.mid) || p - q; });
        var free = opts.filter(function (j) { return count[(x.s + j) % n] < cap; });
        x.gap = free.length ? free[0] : opts[0];
        count[(x.s + x.gap) % n]++;
      });
      var NC = 0;
      B.forEach(function (b) { NC += b.offs.length; });
      var cB = new Int32Array(NC), cHub = new Float64Array(NC), cGly = new Float64Array(NC), cA = new Float64Array(NC);
      var cLen = new Float64Array(NC), cDepth = new Int32Array(NC), ord = new Int32Array(NC);
      var sP = new Float64Array(2 * NC), sD = new Int32Array(2 * NC), gapList = [];
      for (var g0 = 0; g0 < n; g0++) gapList.push([]);
      function mod(v) { v %= n; return v < 0 ? v + n : v; }
      function same(p, q) { var d = Math.abs(mod(p - q)); return d < EPS || n - d < EPS; }
      function setFracs() {
        // Within a gap, the glyph whose hubs lie further clockwise sits clockwise.
        for (var g = 0; g < n; g++) gapList[g].length = 0;
        for (var i = 0; i < B.length; i++) gapList[(B[i].s + B[i].gap) % n].push(B[i]);
        for (var g2 = 0; g2 < n; g2++) {
          var list = gapList[g2];
          if (list.length === 1) { list[0].frac = 0.5; continue; }
          list.sort(function (x, y) { return (x.mean - x.gap) - (y.mean - y.gap) || x.i - y.i; });
          for (var k = 0; k < list.length; k++) list[k].frac = 0.32 + 0.36 * k / (list.length - 1);
        }
      }
      function plan() {
        setFracs();
        var k = 0, i, j;
        for (var bi = 0; bi < B.length; bi++) {
          var b = B[bi], u = b.gap + b.frac;
          for (j = 0; j < b.offs.length; j++, k++) {
            var o = b.offs[j], lo = o < u ? o : u, hi = o < u ? u : o;
            cB[k] = bi; cHub[k] = (b.s + o) % n; cGly[k] = (b.s + u) % n; cA[k] = (b.s + lo) % n; cLen[k] = hi - lo; ord[k] = k;
          }
        }
        // Shortest chords first (insertion sort: a few dozen chords).
        for (i = 1; i < NC; i++) {
          var v = ord[i], lv = cLen[v], q = i - 1;
          while (q >= 0 && (cLen[ord[q]] > lv || (cLen[ord[q]] === lv && ord[q] > v))) { ord[q + 1] = ord[q]; q--; }
          ord[q + 1] = v;
        }
        // Depths: below everything a chord holds, clear of what it overlaps.
        for (var idx = 0; idx < NC; idx++) {
          var c = ord[idx], floor = 0, used = 0;
          for (j = 0; j < idx; j++) {
            var e = ord[j], d0 = mod(cA[e] - cA[c]), d1 = mod(cA[c] - cA[e]), dc = d0 > n - EPS ? 0 : d0;
            if (dc + cLen[e] <= cLen[c] + EPS && !(same(cA[c], cA[e]) && Math.abs(cLen[c] - cLen[e]) < EPS)) floor = Math.max(floor, cDepth[e] + 1);
            var touch = Math.abs(d0 - cLen[c]) < EPS || Math.abs(d1 - cLen[e]) < EPS;
            var over = touch ? cB[c] !== cB[e] : (d0 < cLen[c] - EPS || d1 < cLen[e] - EPS);
            if (over && cDepth[e] < 30) used |= 1 << cDepth[e];
          }
          var d = floor;
          while (d < 30 && (used & (1 << d))) d++;
          cDepth[c] = d;
        }
        // Stalks: each hub's and glyph's riser reaches its deepest chord.
        var ns = 0;
        for (i = 0; i < NC; i++) {
          for (var w = 0; w < 2; w++) {
            var p = w ? cGly[i] : cHub[i], found = -1;
            for (var t = 0; t < ns; t++) if (same(sP[t], p)) { found = t; break; }
            if (found < 0) { sP[ns] = p; sD[ns] = cDepth[i]; ns++; } else if (cDepth[i] > sD[found]) sD[found] = cDepth[i];
          }
        }
        // A chord crosses every stalk strictly inside it that reaches deeper.
        var x = 0, depth = 0, length = 0;
        for (i = 0; i < NC; i++) {
          if (cDepth[i] > depth) depth = cDepth[i];
          length += cLen[i];
          for (var s2 = 0; s2 < ns; s2++) {
            if (sD[s2] <= cDepth[i] || same(sP[s2], cHub[i]) || same(sP[s2], cGly[i])) continue;
            var dd = mod(sP[s2] - cA[i]);
            if (dd > EPS && dd < cLen[i] - EPS) x++;
          }
        }
        var off = 0;
        for (i = 0; i < B.length; i++) off += Math.abs(B[i].gap + 0.5 - B[i].mid);
        return { crossings: x, depth: depth, total: 1000 * x + 25 * depth + 6 * length + 2 * off };
      }
      var cur = plan();
      for (var pass = 0; pass < 30; pass++) {
        var better = false;
        for (var bi2 = 0; bi2 < B.length; bi2++) {
          var bb = B[bi2], g1 = bb.gap, best = cur.total, bg = g1;
          count[(bb.s + g1) % n]--;
          for (var j2 = 0; j2 < bb.L; j2++) {
            if (j2 === g1 || count[(bb.s + j2) % n] >= cap) continue;
            bb.gap = j2;
            var sc = plan();
            if (sc.total < best - 1e-9) { best = sc.total; bg = j2; }
          }
          bb.gap = bg;
          count[(bb.s + bb.gap) % n]++;
          if (bg !== g1) { cur = plan(); better = true; }
        }
        if (!better) break;
      }
      cur = plan();
      var chords = [];
      for (var z = 0; z < NC; z++) chords.push({ b: cB[z], hub: cHub[z], glyph: cGly[z], a: cA[z], len: cLen[z], depth: cDepth[z] });
      return { bridges: B, chords: chords, crossings: cur.crossings, depth: cur.depth, total: cur.total };
    }

    /* coreLayout(spec) -> { order, glyphs, lines, plan, stats, ... }
       spec = {
         cx, cy
         axioms      [id, ...]
         rules       [{ id, kind: 'principle' | 'failure', on: [axiom ids] }]
         rLabel      radius kept clear for the centre's name
         rHub        the necklace: the axioms, and the bridges between them
         rSat        the satellites' ring, outside the necklace
         size        { axiom, principle, failure } glyph sizes, px   (13, 10, 10)
         lanePitch   px between chord depths                          (4.2)
         satOffset   px either side of a hub's radius, at rSat        (9.5)
         gapCap      bridge glyphs one gap between hubs may hold      (2)
         gapEmpty    share of the ring an empty gap takes, against one
                     more share per glyph standing in a gap           (1.3)
         evenHubs    true to space the hubs evenly instead            (false)
         chordShape  'arc' (a U, default) or 'lane' (ruled: down, round, up)
         corner      corner radius of ruled lines, px                 (4)
         start       angle of the first hub                           (-pi/2)
         align       optional { id: { a, w } }: turn, and if it helps mirror,
                     the core so each rule sits near the angle given (the
                     mean angle of the components citing it, weighted)
         order       a pinned hub order: used while it names exactly these
                     axioms; else hubOrder decides and the layout takes
                     whichever of its best orders draws with fewest crossings
         hubOpts     options for hubOrder
         checks      true to also count the crossings actually drawn, pair
                     by pair (about 100 ms; for tests and audits)
       }
       A rule resting on (or guarding) one axiom is that hub's satellite on
       rSat: principles on the anticlockwise side of the hub's radius,
       failure modes on the clockwise side, so a rule line can always come
       straight down to the hub between them. A rule tied to several axioms
       is a bridge: its glyph stands on the necklace in a gap between two of
       its own hubs (bridgePlan chooses which), and each of its lines is a U
       that leaves the glyph along its radius, sags to the depth its nesting
       needs and rises into the hub along the hub's radius. The necklace is
       paced by what stands on it, so the thirty glyphs on it fall at an even
       step and the twelve hubs never beat out a dial. Every control radius
       of every line lies between the glyph and its lane, so no line comes
       nearer the centre than the deepest lane, which stays outside rLabel;
       no chord crosses the centre. stats reports the smallest gap between
       two glyphs, the nearest a line comes to a glyph it does not join, the
       nearest any line comes to the centre and the crossings drawn. */
    var corePlans = new Map();
    function coreLayout(spec) {
      var t0 = now(), cx = spec.cx, cy = spec.cy, A = spec.axioms, n = A.length;
      var size = spec.size || { axiom: 13, principle: 10, failure: 10 };
      var rH = spec.rHub, rS = spec.rSat, rLabel = spec.rLabel || 0;
      var pitch = spec.lanePitch || 4.2, corner = spec.corner == null ? 4 : spec.corner;
      var satOff = spec.satOffset || 9.5, cap = spec.gapCap || 2;
      var rules = spec.rules, bridges = rules.filter(function (r) { return r.on.length > 1; });
      // A pinned order is used only while it names exactly today's axioms;
      // otherwise the doctrine has changed and the order is chosen afresh.
      var pinned = Array.isArray(spec.order) && spec.order.length === n &&
        spec.order.slice().sort().join('|') === A.slice().sort().join('|');
      var planKey = JSON.stringify([A, bridges.map(function (r) { return r.on; }), pinned ? spec.order : null, cap, spec.hubOpts || null]);
      var cached = corePlans.get(planKey), hubs, chosen;
      if (cached) { hubs = cached.hubs; chosen = cached.chosen; }
      else {
        hubs = pinned ? { order: spec.order.slice(), candidates: [{ order: spec.order.slice() }], ms: 0, pinned: true } :
          hubOrder(A, bridges.map(function (r) { return r.on; }), spec.hubOpts);
        // Of the best orders, the one whose bridges draw with fewest crossings.
        chosen = null;
        hubs.candidates.forEach(function (cand) {
          var p = Object.create(null);
          cand.order.forEach(function (id, k) { p[id] = k; });
          var plan = bridgePlan(n, bridges.map(function (r) { return r.on.map(function (h) { return p[h]; }); }), cap);
          if (!chosen || plan.total < chosen.plan.total - 1e-9) chosen = { order: cand.order, pos: p, plan: plan };
        });
        corePlans.set(planKey, {hubs: hubs, chosen: chosen});
        if (corePlans.size > 8) corePlans.delete(corePlans.keys().next().value);
      }
      var order = chosen.order, hubPos = chosen.pos, plan = chosen.plan, slot = TAU / n;
      // The gaps between hubs share the ring by what they hold: an empty gap
      // `gapEmpty` units, one more for each bridge glyph standing in it, so
      // all the glyphs on the ring sit at an even pace and the twelve hubs
      // never fall into the even beat of a dial.
      var occupancy = new Float64Array(n), gapEmpty = spec.gapEmpty == null ? 1.3 : spec.gapEmpty;
      plan.bridges.forEach(function (b) { occupancy[(b.s + b.gap) % n] += 1; });
      var widths = [], cum = [0], total = 0;
      for (var gi = 0; gi < n; gi++) { widths.push(spec.evenHubs ? 1 : gapEmpty + occupancy[gi]); total += widths[gi]; }
      for (var gj = 0; gj < n; gj++) cum.push(cum[gj] + widths[gj] * n / total);
      var start = spec.start == null ? -Math.PI / 2 : spec.start, flip = 1;
      if (spec.align) {
        var bestC = Infinity;
        [1, -1].forEach(function (fl) {
          for (var deg = 0; deg < 360; deg += 1) {
            var st = deg * Math.PI / 180, c = 0;
            order.forEach(function (id, k) { var w = spec.align[id]; if (w && w.w) c += w.w * Math.abs(turn(st + fl * cum[k] * slot, w.a)); });
            if (c < bestC - 1e-9) { bestC = c; start = st; flip = fl; }
          }
        });
      }
      // Angle of a place on the hub ring (places may be fractional and run past n).
      function at(p) {
        var turns = Math.floor(p / n), q = p - turns * n, k = Math.min(n - 1, Math.floor(q)), f = q - k;
        return start + flip * (turns * n + cum[k] + f * (cum[k + 1] - cum[k])) * slot;
      }
      var glyphs = Object.create(null);
      order.forEach(function (id, k) { glyphs[id] = { id: id, kind: 'axiom', role: 'hub', a: norm(at(k)), r: rH, size: size.axiom, on: [], place: k }; });
      var perHub = Object.create(null);
      rules.forEach(function (r) {
        if (r.on.length !== 1 || !glyphs[r.on[0]]) return;
        (perHub[r.on[0]] = perHub[r.on[0]] || { principle: [], failure: [] })[r.kind].push(r);
      });
      Object.keys(perHub).forEach(function (h) {
        ['principle', 'failure'].forEach(function (kind) {
          var side = (kind === 'principle' ? -1 : 1) * flip;
          perHub[h][kind].forEach(function (r, j) {
            var off = (satOff + j * (size[kind] + 6)) / rS;
            glyphs[r.id] = { id: r.id, kind: kind, role: 'satellite', a: norm(glyphs[h].a + side * off), r: rS, size: size[kind], on: r.on.slice(), hub: h };
          });
        });
      });
      var laneTop = rH - size.axiom / 2 - 6, deepest = laneTop - plan.depth * pitch;
      if (deepest < rLabel + 3 && plan.depth > 0) pitch = (laneTop - rLabel - 3) / plan.depth;
      function laneR(l) { return laneTop - l * pitch; }
      var chordDepth = Object.create(null), bridgeAt = Object.create(null);
      plan.chords.forEach(function (c) { chordDepth[c.b + ':' + c.hub] = c.depth; });
      plan.bridges.forEach(function (b, i) {
        var r = bridges[i];
        bridgeAt[r.id] = i;
        glyphs[r.id] = { id: r.id, kind: r.kind, role: 'bridge', a: norm(at(b.s + b.gap + b.frac)), r: rH, size: size[r.kind],
                         on: r.on.slice(), span: b.L, from: b.s, place: b.s + b.gap + b.frac };
      });
      // Lines.
      var lines = [];
      rules.forEach(function (r) {
        var g = glyphs[r.id];
        if (!g) return;
        r.on.forEach(function (h) {
          var H = glyphs[h];
          if (!H) return;
          var way, pol;
          if (g.role === 'satellite') {
            // One smooth S: up the hub's radius, over, and down onto the
            // satellite along its own.
            var r0 = rH + H.size / 2 + 2, r1 = rS - g.size / 2 - 2, aH = g.a + turn(g.a, H.a), k = (r1 - r0) * 0.55;
            pol = polarBezier([aH, r0], [aH, r0 + k], [g.a, r1 - k], [g.a, r1], 1.5);
          } else {
            // Unwrapped along the bridge's own span, so the lane runs the
            // right way round.
            var ph = g.from + ((hubPos[h] - g.from + n) % n), lr = laneR(chordDepth[bridgeAt[r.id] + ':' + hubPos[h]]);
            var ag = at(g.place), ah = at(ph), rg = rH - g.size / 2 - 2, rh = rH - H.size / 2 - 2;
            if (spec.chordShape === 'lane') {
              // Ruled: down, round the lane, up.
              pol = polarRun([[ag, rg], [ag, lr], [ah, lr], [ah, rh]], corner, 2);
            } else {
              // A U: down from the glyph along its radius, sagging to the
              // chord's depth at its middle, up into the hub along the hub's.
              pol = polarBezier([ag, rg], [ag, rg - 4 / 3 * (rg - lr)], [ah, rh - 4 / 3 * (rh - lr)], [ah, rh], 2);
            }
          }
          lines.push({ from: r.id, to: h, kind: r.kind, role: g.role, polar: pol, pts: polarXY(cx, cy, pol),
                       depth: g.role === 'bridge' ? chordDepth[bridgeAt[r.id] + ':' + hubPos[h]] : -1 });
        });
      });
      Object.keys(glyphs).forEach(function (id) { var q = glyphs[id]; q.x = cx + q.r * Math.cos(q.a); q.y = cy + q.r * Math.sin(q.a); });
      // Checks, for the record. How near a line comes to a glyph it does not
      // join tests every point of every line against every glyph, so it is
      // reckoned only when it is asked for (a test or an audit), never as
      // a view is drawn.
      var ids = Object.keys(glyphs), minGap = Infinity, minR = Infinity, drawn = 0, lineGapMemo = null;
      for (var i = 0; i < ids.length; i++) for (var j = i + 1; j < ids.length; j++) {
        var p = glyphs[ids[i]], q = glyphs[ids[j]];
        minGap = Math.min(minGap, Math.hypot(p.x - q.x, p.y - q.y) - (p.size + q.size) / 2);
      }
      lines.forEach(function (ln) { ln.polar.forEach(function (pp) { minR = Math.min(minR, pp[1]); }); });
      function lineGlyphGap() {
        if (lineGapMemo !== null) return lineGapMemo;
        var gap = Infinity;
        lines.forEach(function (ln) {
          ids.forEach(function (id) {
            if (id === ln.from || id === ln.to) return;
            var g = glyphs[id];
            ln.pts.forEach(function (pt) { gap = Math.min(gap, Math.hypot(pt[0] - g.x, pt[1] - g.y) - g.size / 2); });
          });
        });
        return (lineGapMemo = gap);
      }
      // Counting the crossings actually drawn tests every pair of lines
      // against each other: a check for tests and audits (spec.checks), not
      // something a page needs to pay for at load.
      if (spec.checks) {
        for (var a1 = 0; a1 < lines.length; a1++) for (var b1 = a1 + 1; b1 < lines.length; b1++) {
          var L1 = lines[a1], L2 = lines[b1];
          if (L1.from === L2.from || L1.to === L2.to) continue;
          if (polyCross(L1.pts, L2.pts)) drawn++;
        }
      } else drawn = null;
      return {
        order: order, start: start, flip: flip, glyphs: glyphs, lines: lines, laneTop: laneTop, pitch: pitch, hubs: hubs, plan: plan,
        stats: { glyphGap: minGap, get lineGlyphGap() { return lineGlyphGap(); }, nearestToCentre: minR, labelR: rLabel, planCrossings: plan.crossings,
                 lanes: plan.depth + 1, crossingsDrawn: drawn, orderPinned: !!hubs.pinned, hubOrderMs: hubs.ms, ms: now() - t0 }
      };
    }
    // Whether two polylines cross anywhere (proper crossings only).
    function polyCross(P, Q) {
      for (var i = 0; i < P.length - 1; i++) {
        var a = P[i], b = P[i + 1];
        for (var j = 0; j < Q.length - 1; j++) {
          var c = Q[j], e = Q[j + 1];
          var rx = b[0] - a[0], ry = b[1] - a[1], sx = e[0] - c[0], sy = e[1] - c[1], den = rx * sy - ry * sx;
          if (Math.abs(den) < 1e-12) continue;
          var qx = c[0] - a[0], qy = c[1] - a[1], t = (qx * sy - qy * sx) / den, u = (qx * ry - qy * rx) / den;
          if (t > 1e-6 && t < 1 - 1e-6 && u > 1e-6 && u < 1 - 1e-6) return true;
        }
      }
      return false;
    }

    return {
      // paths
      toPolyline: toPolyline, measure: measure, resample: resample, pointAt: pointAt, lineD: lineD, trimEnds: trimEnds,
      // polar curves
      polarXY: polarXY, polarBezier: polarBezier, polarSpline: polarSpline, polarRun: polarRun,
      // fibres
      bundle: bundle, taper: taper, fibreStroke: fibreStroke, strokeGaps: strokeGaps, coarse: coarse,
      // the weave
      weave: weave,
      // rule lines
      ruleFan: ruleFan, clearPort: clearPort,
      // the core
      hubOrder: hubOrder, hubCost: hubCost, bridgePlan: bridgePlan, coreLayout: coreLayout, coverTable: coverTable,
      // helpers the map may share
      turn: turn, norm: norm, circMean: circMean, rng: rng
    };
  })();

  /* ---- Words --------------------------------------------------------- */
  function isObj(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
  function str(v) { return typeof v === 'string' && v.trim() ? v.trim() : null; }
  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function plural(n, one, many) { return n === 1 ? one : many; }
  var SMALL = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven',
    'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty'];
  function numberWord(n) { return n >= 0 && n < SMALL.length ? SMALL[n] : String(n); }
  function countWords(n, one, many) { return numberWord(n) + ' ' + plural(n, one, many); }
  function countFigure(n, one, many) { return (n ? String(n) : 'no') + ' ' + plural(n, one, many); }
  function capital(t) { return t ? t.charAt(0).toUpperCase() + t.slice(1) : t; }
  function lowerFirst(t) { return t ? t.charAt(0).toLowerCase() + t.slice(1) : t; }
  function andList(items) {
    if (items.length < 2) return items.join('');
    return items.slice(0, -1).join(', ') + ' and ' + items[items.length - 1];
  }
  function byText(a, b) { return a < b ? -1 : a > b ? 1 : 0; }
  function humanize(key) {
    var t = String(key).replace(/^[a-z]+:/, '').replace(/[_-]+/g, ' ');
    return t.charAt(0).toUpperCase() + t.slice(1);
  }
  function uniq(list) {
    var seen = Object.create(null);
    return list.filter(function (x) { if (seen[x]) return false; seen[x] = true; return true; });
  }

  /* Authored prose runs long and now and then carries a file name or a dash;
     the column shows its opening sentences, up to a readable length, and
     stops before the first sentence that is not plain words. */
  var UNPLAIN = /—|–|\b[a-z0-9]+_[a-z0-9_]+\b|\b(?:AX|AP|P)-\d+\b/;
  function sentencesOf(text) {
    var out = [], re = /[.!?]["”’)]?\s+(?=[A-Z“"(])/g, from = 0, m;
    while ((m = re.exec(text))) {
      var end = m.index + m[0].replace(/\s+$/, '').length;
      out.push(text.slice(from, end).trim());
      from = m.index + m[0].length;
    }
    if (from < text.length) out.push(text.slice(from).trim());
    return out.filter(Boolean);
  }
  function trimProse(text, most) {
    var list = sentencesOf(String(text || '').replace(/\s+/g, ' ').trim()), kept = [], len = 0;
    for (var i = 0; i < list.length; i++) {
      var s = list[i];
      if (UNPLAIN.test(s)) break;
      if (kept.length && len + s.length + 1 > most) break;
      if (!kept.length && s.length > most * 1.4) break;
      kept.push(s);
      len += s.length + 1;
    }
    return kept.length ? kept.join(' ') : null;
  }

  /* ---- Evidence -------------------------------------------------------- */
  /* Five ways a component is backed, each named in plain words and cut as
     its own mark, so the ink is never the only signal. */
  var CLASS_ORDER = ['tool', 'bounded', 'import', 'contract', 'computes'];
  var CLASS_OF = {
    external_subprocess_witness: 'tool',
    bounded_runtime_computation: 'bounded',
    verified_macro_body_import: 'import',
    semantic_validator: 'contract',
    algorithmic_projection: 'computes'
  };
  var CLASS_WORDS = {
    tool: 'Runs a real tool',
    bounded: 'Runs a bounded computation',
    import: 'Imports checked source',
    contract: 'Checks a contract',
    computes: 'Computes from its sources'
  };
  function classOf(ev) {
    if (!isObj(ev)) return null;
    if (CLASS_OF[ev.class_id]) return CLASS_OF[ev.class_id];
    if (ev.runs_real_tools === true) return 'tool';
    var rank = +ev.rank;
    if (rank >= 5) return 'import';
    if (rank >= 4) return 'contract';
    return rank > 0 ? 'computes' : null;
  }
  // One 12-unit glyph per class: a disc, a half disc, a square, a ringed
  // dot, a ring.
  var GLYPHS = {
    tool: '<circle cx="6" cy="6" r="4.7"/>',
    bounded: '<circle cx="6" cy="6" r="4.1" fill="none" stroke-width="1.5"/><path d="M6 1.9a4.1 4.1 0 0 1 0 8.2z"/>',
    import: '<rect x="1.8" y="1.8" width="8.4" height="8.4" rx="1.1"/>',
    contract: '<circle cx="6" cy="6" r="4.1" fill="none" stroke-width="1.5"/><circle cx="6" cy="6" r="1.8"/>',
    computes: '<circle cx="6" cy="6" r="4.1" fill="none" stroke-width="1.5"/>',
    none: '<circle cx="6" cy="6" r="2.2"/>'
  };
  function glyphSvg(cls) {
    return '<svg class="sm-glyph" viewBox="0 0 12 12" width="12" height="12" aria-hidden="true" focusable="false" ' +
      'fill="currentColor" stroke="currentColor" stroke-width="0">' + (GLYPHS[cls] || GLYPHS.none) + '</svg>';
  }

  /* ---- The scene ------------------------------------------------------- */
  /* Reads the published scene into the few things the drawing needs. Bad
     rows (duplicate ids, edges to unknown nodes, repeated links) are dropped
     and the rest is kept; a scene built before the per-component details
     existed still draws, with its names and families from the nodes. */
  function routeWith(base, docsHref, siteHref) {
    var d = str(docsHref);
    if (d) return /^(?:[a-z][a-z0-9+.-]*:|\/|#)/i.test(d) ? d : base + d;
    return str(siteHref);
  }
  function webUrl(v) { var u = str(v); return u && /^https?:\/\//i.test(u) ? u : null; }
  /* The kinds of link between two components, from the relation's name: a
     component runs another, reads the results another saved, or checks the
     files copied from another (read from the code); an older scene has only
     the relations a component's own record lists, with no direction worth
     reading. */
  var LINK_KIND = { runs: 'runs', reads_results_of: 'reads', checks_copies_of: 'checks', declared_dependency_untyped: 'named' };
  var LINK_ORDER = ['runs', 'reads', 'checks', 'named', 'other'];
  var LINK_WORDS = {
    runs: { out: 'Runs', inc: 'Run by', key: 'Runs' },
    reads: { out: 'Reads results of', inc: 'Results read by', key: 'Reads saved results of' },
    checks: { out: 'Checks copies of', inc: 'Copies checked by', key: 'Checks the copied files of' },
    named: { out: 'Listed as related', inc: 'Listed as related', key: 'Listed as related' },
    other: { out: 'Connects to', inc: 'Connected from', key: 'Other connections' }
  };
  // The same relations as the explorer's panel reads them, each a heading
  // over the components at its other end.
  var RELATION_WORDS = {
    runs: { out: 'Runs', inc: 'Run by' },
    reads: { out: 'Reads the saved results of', inc: 'Its saved results are read by' },
    checks: { out: 'Checks the copied files of', inc: 'Its copied files are checked by' },
    named: { both: 'Listed as related' },
    other: { out: 'Connects to', inc: 'Connected from' }
  };
  // Where in the code a connection comes from: the first file its evidence
  // names, and the lines it names there.
  function evidenceOf(e) {
    var list = Array.isArray(e.evidence) ? e.evidence : isObj(e.evidence) ? [e.evidence] : [];
    var path = null, lo = Infinity, hi = -Infinity;
    list.forEach(function (ev) {
      if (!isObj(ev) || !str(ev.path)) return;
      if (!path) path = str(ev.path);
      if (str(ev.path) !== path) return;
      (Array.isArray(ev.lines) ? ev.lines : []).forEach(function (n) {
        if (typeof n === 'number' && n > 0) { lo = Math.min(lo, n); hi = Math.max(hi, n); }
      });
    });
    return path ? { path: path, from: isFinite(lo) ? lo : 0, to: isFinite(hi) ? hi : 0 } : null;
  }
  function readScene(json, base) {
    var scene = isObj(json) && isObj(json.scene) ? json.scene : json;
    if (!isObj(scene) || !Array.isArray(scene.nodes)) return null;
    var details = isObj(scene.inspectors) ? scene.inspectors : {};
    var nodeRoutes = isObj(json) && isObj(json.node_routes) ? json.node_routes : {};
    var clusterLabel = Object.create(null);
    (Array.isArray(scene.clusters) ? scene.clusters : []).forEach(function (c) {
      if (isObj(c) && str(c.id)) clusterLabel[c.id] = str(c.label);
    });
    var seen = Object.create(null), areaNodes = [], compNodes = [];
    scene.nodes.forEach(function (n) {
      if (!isObj(n)) return;
      var id = str(n.id);
      if (!id || seen[id]) return;
      seen[id] = true;
      if (n.kind === 'area') areaNodes.push(n);
      else if (n.kind === 'wired_component' || n.kind === 'component') compNodes.push(n);
    });
    function detailOf(n) {
      var d = details[str(n.inspector_ref) || 'inspector:' + n.id];
      return isObj(d) ? d : null;
    }
    function routesOf(n, d) {
      if (d && isObj(d.routes)) return d.routes;
      return isObj(nodeRoutes[n.id]) ? nodeRoutes[n.id] : {};
    }
    function mapHref(address) { return base + 'system-map.html#map=' + encodeURIComponent(address); }

    var families = [], famAt = Object.create(null);
    function addFamily(key, n, d, r) {
      famAt[key] = families.length;
      families.push({
        id: 'area:' + key, key: key,
        title: str(d && d.title) || str(n && n.label) || clusterLabel['cluster:' + key] || humanize(key),
        summary: str(d && d.summary) || str(n && n.summary),
        page: r ? routeWith(base, r.primary_reader_href, r.site_primary_reader_href) : null,
        mapHref: mapHref('family:' + key),
        members: [], inside: 0
      });
    }
    areaNodes.forEach(function (n) {
      var key = n.id.replace(/^area:/, '');
      if (famAt[key] !== undefined) return;
      var d = detailOf(n);
      addFamily(key, n, d, routesOf(n, d));
    });

    var comps = [], compAt = Object.create(null), codeBase = null;
    compNodes.forEach(function (n) {
      var d = detailOf(n);
      var key = str(d && d.family_id) || (str(n.parent_cluster_id) || '').replace(/^cluster:/, '');
      if (!key) return;
      if (famAt[key] === undefined) addFamily(key, null, null, null);
      var ev = d && isObj(d.evidence) ? d.evidence : null;
      var r = routesOf(n, d), source = null;
      (d && Array.isArray(d.source_links) ? d.source_links : []).forEach(function (l) {
        if (!source && isObj(l) && /^source$/i.test(str(l.label) || '')) source = webUrl(l.url);
      });
      // The repository the sources are published in, for links to a line.
      var cb = source && /^(https:\/\/github\.com\/[^\/]+\/[^\/]+\/blob\/[^\/]+\/)/.exec(source);
      if (cb && !codeBase) codeBase = cb[1];
      compAt[n.id] = comps.length;
      comps.push({
        id: n.id,
        label: str(d && d.public_label) || str(d && d.title) || str(n.label) || humanize(n.id),
        fam: famAt[key], cls: classOf(ev), basis: str(ev && ev.basis),
        line: str(d && d.summary_line), what: str(d && d.what_it_does),
        page: routeWith(base, r.component_detail_href, r.site_component_detail_href),
        reader: routeWith(base, r.primary_reader_href, r.site_primary_reader_href),
        source: source, mapHref: mapHref(n.id),
        out: [], inc: []
      });
    });

    var links = [], linkSeen = Object.create(null), verdicts = Object.create(null), dropped = 0;
    var kindsSeen = Object.create(null);
    (Array.isArray(scene.edges) ? scene.edges : []).forEach(function (e) {
      if (!isObj(e)) { dropped++; return; }
      var a = compAt[str(e.source)], b = compAt[str(e.target)];
      // A relation between other things (the spine's steps, the areas) is
      // not a link between components.
      if (a === undefined && b === undefined) return;
      var kind = LINK_KIND[str(e.relation) || str(e.kind) || ''] || 'other';
      if (a === undefined || b === undefined || a === b || linkSeen[a + '>' + b + '>' + kind]) { dropped++; return; }
      linkSeen[a + '>' + b + '>' + kind] = true;
      if (str(e.verdict)) verdicts[a + '>' + b] = str(e.verdict);
      var l = [a, b];
      l.kind = kind;
      l.ev = evidenceOf(e);
      links.push(l);
      if (comps[a].out.indexOf(b) < 0) comps[a].out.push(b);
      if (comps[b].inc.indexOf(a) < 0) comps[b].inc.push(a);
      kindsSeen[kind] = true;
    });

    // A family is drawn only when it has components.
    var keep = families.map(function () { return false; });
    comps.forEach(function (c) { keep[c.fam] = true; });
    var remap = [], kept = [];
    families.forEach(function (f, i) { if (keep[i]) { remap[i] = kept.length; kept.push(f); } });
    families = kept;
    comps.forEach(function (c, i) { c.fam = remap[c.fam]; families[c.fam].members.push(i); });
    // A family's members read by how they are backed, then by name.
    families.forEach(function (f) {
      f.members.sort(function (a, b) {
        var ca = comps[a].cls ? CLASS_ORDER.indexOf(comps[a].cls) : 9;
        var cb = comps[b].cls ? CLASS_ORDER.indexOf(comps[b].cls) : 9;
        return ca - cb || byText(comps[a].label, comps[b].label) || a - b;
      });
    });
    // The links between two families, both directions summed and each kept.
    var pairAt = Object.create(null), pairs = [];
    links.forEach(function (l) {
      var fa = comps[l[0]].fam, fb = comps[l[1]].fam;
      if (fa === fb) { families[fa].inside++; return; }
      var lo = Math.min(fa, fb), hi = Math.max(fa, fb), key = lo + '-' + hi;
      if (pairAt[key] === undefined) { pairAt[key] = pairs.length; pairs.push({ a: lo, b: hi, n: 0, ab: 0, ba: 0 }); }
      var p = pairs[pairAt[key]];
      p.n++;
      if (fa === lo) p.ab++; else p.ba++;
    });
    var classes = CLASS_ORDER.filter(function (cls) { return comps.some(function (c) { return c.cls === cls; }); });
    return { families: families, comps: comps, links: links, pairs: pairs, classes: classes, verdicts: verdicts, codeBase: codeBase,
             kinds: LINK_ORDER.filter(function (k) { return kindsSeen[k]; }),
             dropped: dropped, stale: !Object.keys(details).length };
  }

  /* ---- The doctrine ------------------------------------------------------ */
  /* docs/doctrine-manifest.json: twelve axioms, twenty principles, seventeen
     failure modes; which axioms each principle rests on; which axioms each
     failure mode threatens; where each rule is enforced (where a test shows
     the whole rule, where a test checks a narrower part of it, and what its
     card names that no test shows yet; an older manifest has only what the
     card names); and, for every component, the principles and the axioms its
     paper module cites. Rows naming an unknown rule or component are
     dropped, never guessed at. */
  var KIND_WORDS = { axiom: 'Axiom', principle: 'Principle', failure: 'Failure mode' };
  // The styles a rule's name is set in on the drawing: the chosen rule's tag
  // (its kind over its name), and the names of the rules a view lights.
  var TAG_KIND = 'sm-tag__kind', TAG_TITLE = 'sm-tag__title', RULE_NAME = 'sm-rname';
  function readDoctrine(json, model, base) {
    if (!isObj(json) || !Array.isArray(json.axioms) || !Array.isArray(json.principles) || !model) return null;
    var rules = Object.create(null), lists = { axiom: [], principle: [], failure: [] }, tested = false;
    // A relation is an id, or (once checked against the code) an object
    // holding its id and a verdict; the verdict is kept beside the relation.
    var verdicts = Object.create(null);
    function ids(v, owner, rel) {
      if (!Array.isArray(v)) return [];
      return v.map(function (x) {
        if (typeof x === 'string') return x;
        if (isObj(x) && str(x.id)) {
          if (owner && str(x.verdict)) verdicts[rel + ':' + owner + '>' + str(x.id)] = str(x.verdict);
          return str(x.id);
        }
        return null;
      }).filter(Boolean);
    }
    [['axioms', 'axiom'], ['principles', 'principle'], ['anti_principles', 'failure']].forEach(function (pair) {
      (Array.isArray(json[pair[0]]) ? json[pair[0]] : []).forEach(function (r) {
        if (!isObj(r) || !str(r.id) || !str(r.title) || rules[r.id]) return;
        rules[r.id] = {
          id: r.id, kind: pair[1], title: str(r.title), plain: str(r.plain),
          doctrine: str(r.doctrine) ? routeWith(base, r.doctrine) : null,
          restsOn: ids(r.rests_on, r.id, 'rests_on'), guards: ids(r.guards, r.id, 'guards'), negates: ids(r.negates, r.id, 'negates'),
          enforcedIds: ids(r.enforced_in, r.id, 'enforced_in'), partlyIds: ids(r.partly_enforced_in, r.id, 'partly_enforced_in'),
          cardIds: ids(r.named_in_card, r.id, 'named_in_card'), enforced: [], partly: [], namedOnly: [],
          grounds: [], threatenedBy: [], brokenBy: [], cited: 0
        };
        if (Array.isArray(r.partly_enforced_in) || Array.isArray(r.named_in_card)) tested = true;
        lists[pair[1]].push(r.id);
      });
    });
    function known(kind) { return function (id) { return !!rules[id] && rules[id].kind === kind; }; }
    // One relation each way, derived from one side so the two always agree:
    // a principle rests on axioms; a failure mode threatens axioms and breaks
    // principles.
    Object.keys(rules).forEach(function (id) {
      var r = rules[id];
      r.restsOn = uniq(r.restsOn.filter(known('axiom')));
      r.guards = uniq(r.guards.filter(known('axiom')));
      r.negates = uniq(r.negates.filter(known('principle')));
    });
    lists.principle.forEach(function (p) { rules[p].restsOn.forEach(function (a) { rules[a].grounds.push(p); }); });
    lists.failure.forEach(function (f) {
      rules[f].guards.forEach(function (a) { rules[a].threatenedBy.push(f); });
      rules[f].negates.forEach(function (p) { rules[p].brokenBy.push(f); });
    });
    var compAt = Object.create(null);
    model.comps.forEach(function (c, i) { compAt[c.id] = i; });
    function compsOf(list) { return uniq(list.map(function (cid) { return compAt[cid]; }).filter(function (i) { return i !== undefined; })); }
    Object.keys(rules).forEach(function (id) {
      var r = rules[id];
      r.enforced = compsOf(r.enforcedIds);
      r.partly = compsOf(r.partlyIds).filter(function (i) { return r.enforced.indexOf(i) < 0; });
      r.namedOnly = tested ? compsOf(r.cardIds).filter(function (i) { return r.enforced.indexOf(i) < 0 && r.partly.indexOf(i) < 0; }) : [];
    });
    var comp = model.comps.map(function () { return { gov: [], abide: [], enforces: [], partly: [], source: null, missing: true }; });
    (Array.isArray(json.components) ? json.components : []).forEach(function (row) {
      if (!isObj(row)) return;
      var i = compAt[row.id];
      if (i === undefined || !comp[i].missing) return;
      comp[i] = { gov: uniq(ids(row.governed_by, row.id, 'governed_by').filter(known('principle'))),
                  abide: uniq(ids(row.abides_by, row.id, 'abides_by').filter(known('axiom'))), enforces: [], partly: [],
                  source: str(row.citation_source), missing: false };
    });
    Object.keys(rules).forEach(function (id) {
      rules[id].enforced.forEach(function (ci) { comp[ci].enforces.push(id); });
      rules[id].partly.forEach(function (ci) { comp[ci].partly.push(id); });
    });
    comp.forEach(function (info) {
      info.gov.forEach(function (p) { rules[p].cited++; });
      info.abide.forEach(function (a) { rules[a].cited++; });
    });
    var order = doctrineOrder(rules, lists);
    // listed: each kind in the manifest's own order, the order the
    // explorer's lists keep; the orders above are the drawing's.
    return { rules: rules, principles: order.principles, axioms: order.axioms, failures: order.failures, comp: comp, verdicts: verdicts,
             enforcedBy: tested ? 'tests' : 'card', listed: lists };
  }

  /* ---- Orders ------------------------------------------------------------- */
  function positions(list) {
    var p = Object.create(null);
    list.forEach(function (id, i) { p[id] = i; });
    return p;
  }
  // Crossings between two ordered columns: two lines cross when their ends
  // come in opposite orders.
  function crossCount(edges, pl, pr) {
    var c = 0;
    for (var i = 0; i < edges.length; i++) {
      for (var j = i + 1; j < edges.length; j++) {
        var a = pl[edges[i][0]] - pl[edges[j][0]], b = pr[edges[i][1]] - pr[edges[j][1]];
        if (a * b < 0) c++;
      }
    }
    return c;
  }
  function slant(edges, pl, pr, nl, nr) {
    var s = 0;
    edges.forEach(function (e) { s += Math.abs(pl[e[0]] / Math.max(1, nl - 1) - pr[e[1]] / Math.max(1, nr - 1)); });
    return s;
  }
  function bary(list, other, nbrs) {
    var po = positions(other), at = positions(list);
    function mean(id) {
      var xs = nbrs(id).map(function (x) { return po[x]; }).filter(function (x) { return x !== undefined; });
      if (!xs.length) return at[id] * Math.max(1, other.length - 1) / Math.max(1, list.length - 1);
      return xs.reduce(function (s, x) { return s + x; }, 0) / xs.length;
    }
    var m = Object.create(null);
    list.forEach(function (id) { m[id] = mean(id); });
    return list.slice().sort(function (a, b) { return m[a] - m[b] || at[a] - at[b]; });
  }
  // Each item in turn tries every place in its column and keeps the best.
  function sift(list, cost) {
    var best = cost(list);
    for (var pass = 0; pass < 4; pass++) {
      var improved = false;
      for (var i = 0; i < list.length; i++) {
        var item = list[i], rest = list.slice(0, i).concat(list.slice(i + 1)), at = i, low = best;
        for (var k = 0; k <= rest.length; k++) {
          if (k === i) continue;
          var c = cost(rest.slice(0, k).concat([item], rest.slice(k)));
          if (c < low - 1e-9) { low = c; at = k; }
        }
        if (at !== i) { list = rest.slice(0, at).concat([item], rest.slice(at)); best = low; improved = true; }
      }
      if (!improved) break;
    }
    return list;
  }
  /* The doctrine's rows in one fixed order: the principles and axioms set
     so the lines between them cross as little as they can (barycentres,
     then each row tries every place), the failure modes against the axioms
     the same way. The order is the map's and never changes with a view. */
  function doctrineOrder(rules, lists) {
    var P = lists.principle.slice(), A = lists.axiom.slice(), F = lists.failure.slice();
    var rest = [], guard = [];
    P.forEach(function (p) { rules[p].restsOn.forEach(function (a) { rest.push([p, a]); }); });
    F.forEach(function (f) { rules[f].guards.forEach(function (a) { guard.push([a, f]); }); });
    function cost(pl, al) {
      var pp = positions(pl), pa = positions(al);
      return crossCount(rest, pp, pa) + 0.01 * slant(rest, pp, pa, pl.length, al.length);
    }
    var best = { c: cost(P, A), P: P.slice(), A: A.slice() };
    for (var it = 0; it < 12; it++) {
      P = bary(P, A, function (p) { return rules[p].restsOn; });
      A = bary(A, P, function (a) { return rules[a].grounds; });
      var c = cost(P, A);
      if (c < best.c - 1e-9) best = { c: c, P: P.slice(), A: A.slice() };
    }
    P = best.P; A = best.A;
    P = sift(P, function (l) { return cost(l, A); });
    A = sift(A, function (l) { return cost(P, l); });
    F = bary(F, A, function (f) { return rules[f].guards; });
    F = sift(F, function (l) {
      var pa = positions(A), pf = positions(l);
      return crossCount(guard, pa, pf) + 0.01 * slant(guard, pa, pf, A.length, l.length);
    });
    return { principles: P, axioms: A, failures: F };
  }

  /* ---- The ring's order --------------------------------------------------- */
  function permutations(n, visit) {
    var a = [], c = [], i = 0, k;
    for (k = 0; k < n; k++) { a.push(k); c.push(0); }
    visit(a.slice());
    while (i < n) {
      if (c[i] < i) {
        var j = i % 2 === 0 ? 0 : c[i], t = a[j];
        a[j] = a[i]; a[i] = t;
        visit(a.slice());
        c[i]++;
        i = 0;
      } else { c[i] = 0; i++; }
    }
  }
  // On a circle of n places, an arc runs clockwise from s for len places.
  // Two bands cross where their arcs interleave: one end of one falls
  // strictly inside the other and its other end outside. Bands that share a
  // family meet there and are ordered so they do not cross.
  function slotsCross(x, y, n) {
    var ex = [x.s, (x.s + x.len) % n], ey = [y.s, (y.s + y.len) % n];
    if (ex[0] === ey[0] || ex[0] === ey[1] || ex[1] === ey[0] || ex[1] === ey[1]) return false;
    function inside(p) { var d = (p - x.s + n) % n; return d > 0 && d < x.len; }
    return inside(ey[0]) !== inside(ey[1]);
  }
  /* The families round the ring, the first at the top: every order of the
     rest is tried (six families make 720) and the one whose bands cross least
     and run shortest wins; among equals the one nearest the published order,
     so the list beside the map reads round it in the same order. */
  function familyRing(model) {
    var n = model.families.length, pairs = model.pairs, best = null;
    var ids = model.families.map(function (f, i) { return i; });
    if (n < 3) return { order: ids, crossings: 0 };
    function moved(order) {
      var d = 0;
      for (var i = 0; i < order.length; i++) for (var j = i + 1; j < order.length; j++) if (order[i] > order[j]) d++;
      return d;
    }
    function score(order) {
      var slot = [];
      order.forEach(function (f, i) { slot[f] = i; });
      var arcs = pairs.map(function (p) {
        var a = slot[p.a], b = slot[p.b], d = (b - a + n) % n;
        return d <= n - d ? { s: a, len: d } : { s: b, len: n - d };
      });
      var length = 0, crossings = 0;
      arcs.forEach(function (x, i) {
        length += pairs[i].n * x.len;
        for (var j = i + 1; j < arcs.length; j++) if (slotsCross(x, arcs[j], n)) crossings++;
      });
      return { order: order, crossings: crossings, length: length, key: crossings * 1e6 + length * 100 + moved(order) };
    }
    permutations(n - 1, function (rest) {
      var s = score([0].concat(rest.map(function (k) { return k + 1; })));
      if (!best || s.key < best.key) best = s;
    });
    return best;
  }

  /* ---- Geometry ------------------------------------------------------------ */
  /* The few helpers the drawing shares. Its lines are made by the loom
     above: polar curves that leave and land along the radius, the fibres'
     bundles and tapers, the doctrine's necklace and the weave. */
  var TAU = Math.PI * 2;
  function fx(v) { return Math.round(v * 100) / 100; }
  function norm(a) { a %= TAU; return a < 0 ? a + TAU : a; }
  function polar(cx, cy, r, a) { return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; }
  function pt(p) { return fx(p[0]) + ' ' + fx(p[1]); }
  function circMean(angles, weights) {
    var x = 0, y = 0;
    angles.forEach(function (a, i) { var w = weights ? weights[i] : 1; x += w * Math.cos(a); y += w * Math.sin(a); });
    if (Math.sqrt(x * x + y * y) < 1e-6) return angles.length ? angles[0] : 0;
    return Math.atan2(y, x);
  }
  // The signed shorter turn from a to b.
  function turn(a, b) { var d = norm(b - a); return d > Math.PI ? d - TAU : d; }
  // An arc of a circle about the centre, for text set along it: clockwise
  // on the upper half, anticlockwise on the lower, so no word is upside down.
  function arcFor(cx, cy, r, mid, span, lower) {
    var a0 = lower ? mid + span / 2 : mid - span / 2, a1 = lower ? mid - span / 2 : mid + span / 2;
    return 'M' + pt(polar(cx, cy, r, a0)) + 'A' + fx(r) + ' ' + fx(r) + ' 0 ' + (span > Math.PI ? 1 : 0) + ' ' + (lower ? 0 : 1) + ' ' + pt(polar(cx, cy, r, a1));
  }
  /* Which way a sector's name reads round the ring: over the top clockwise,
     under the bottom anticlockwise; near either side both run bottom to top,
     as on the mathematics slide, so the two sides never read in opposite
     directions, while the letters lean at most 15 degrees past upright. */
  function readsDownward(mid) {
    var deg = Math.atan2(Math.sin(mid), Math.cos(mid)) * 180 / Math.PI;
    if (deg >= -15 && deg <= 40) return true;
    if (deg >= 165 || deg <= -140) return false;
    return deg > 0;
  }
  var DOCTRINE_GLYPHS = {
    axiom: '<circle cx="6" cy="6" r="4.6" fill="none" stroke-width="1.5"/><circle cx="6" cy="6" r="1.9"/>',
    principle: '<path d="M6 1.3L10.7 6L6 10.7L1.3 6Z" fill="none" stroke-width="1.6"/>',
    failure: '<path d="M2.4 2.4L9.6 9.6M9.6 2.4L2.4 9.6" fill="none" stroke-width="1.8" stroke-linecap="round"/>'
  };
  function doctrineSvg(kind) {
    return '<svg class="sm-glyph" viewBox="0 0 12 12" width="12" height="12" aria-hidden="true" focusable="false" ' +
      'fill="currentColor" stroke="currentColor" stroke-width="0">' + DOCTRINE_GLYPHS[kind] + '</svg>';
  }

  /* ---- Mount --------------------------------------------------------------- */
  var mounted = 0;
  function mount(stage) {
    var holder = stage.querySelector('[data-system-src]');
    if (!holder || stage.getAttribute('data-system-ready')) return null;
    stage.setAttribute('data-system-ready', '1');
    mounted++;
    var section = stage.closest ? stage.closest('section') : null;
    var slide = stage.closest ? stage.closest('[data-atlas-slide]') : null;
    // On its own page (docs/system-map.html) the map's selection is the
    // page's address, so a view can be shared and the browser's Back
    // retraces it.
    var pageMode = !!(stage.closest && stage.closest('[data-system-page]'));
    // There it is a map explorer (5 October 2026), the sibling of the
    // mathematics map: the drawing fills the stage, fitted to it whole, and
    // the reading panel beside it is the only place words go. The frame
    // (assets/explorer.js) asks for a fit or a zoom and says when the stage
    // changes size; the map draws, fits and selects.
    var explorerEl = pageMode && stage.closest ? stage.closest('[data-explorer]') : null;
    var explorer = !!explorerEl;
    var base = holder.getAttribute('data-system-base') || '';
    var src = holder.getAttribute('data-system-src');
    var doctrineSrc = holder.getAttribute('data-system-doctrine') ||
      (src ? src.replace(/[^\/]*(?:[?#].*)?$/, 'doctrine-manifest.json') : null);

    var reduceQuery = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    var reduceMotion = !!(reduceQuery && reduceQuery.matches);

    // map: the drawing on screen; baseMap: the whole system as it rests,
    // which every camera is reckoned from; camNow: the camera map is drawn
    // for (null is the whole system).
    var model = null, D = null, ring = null, map = null, baseMap = null, camNow = null;
    // The explorer's own zoom: undefined while the camera follows the choice,
    // null for the whole map (Fit), a camera where the reader zoomed or moved.
    var userCam;
    // Ids for the paths and masks a drawing defines: two drawings stand in
    // the page while the camera moves, so they count on from one another.
    var arcN = 0, revealN = 0;
    // Where the reader is: a level and what is chosen there.
    //   system | family (fam) | component (comp) | doctrine | rule (rule)
    var at = { level: 'system', fam: -1, comp: -1, rule: null };
    var trail = [];
    var hoverKey = null, pending = null, revealed = false, onScreen = true, doctrineState = 'pending', forceReveal = false;
    // The relation a row in the panel is pointed at for (its kind and its
    // direction from the chosen component's side), so the drawing singles
    // out that one line and the readout says that one sentence.
    var hoverRel = null;
    /* What the reader is examining in the explorer's panel (6 October 2026,
       a Type B review of the system view with Will's go-ahead): a
       component's view (its overview, its code connections or the rules its
       paper module cites), the doctrine's category, what has been typed
       into a find, a family of connections chosen to stand alone, and the
       connections and rules the drawing is narrowed to as a result. The
       view and the category hold from one choice to the next; a find and a
       narrowing belong to the choice they were made in. All of it survives
       full screen, the panel folded and a new layout, which redraw the map
       and keep the panel. */
    var inspect = { view: 'overview', cat: 'axiom', key: null, find: Object.create(null), scope: null, narrow: null };

    /* ---- Elements ---- */
    function h(tag, cls, text) {
      var n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text != null) n.textContent = text;
      return n;
    }
    function sv(tag, attrs) {
      var n = document.createElementNS ? document.createElementNS(SVGNS, tag) : document.createElement(tag);
      if (attrs) Object.keys(attrs).forEach(function (k) { if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, attrs[k]); });
      return n;
    }
    function button(cls, text) {
      var b = h('button', cls, text);
      b.setAttribute('type', 'button');
      return b;
    }
    function clear(n) { while (n && n.firstChild) n.removeChild(n.firstChild); }
    function keyed(scope, key) {
      if (!scope || !scope.querySelectorAll) return [];
      return Array.prototype.filter.call(scope.querySelectorAll('[data-sm-key]'), function (n) {
        return n.getAttribute('data-sm-key') === key;
      });
    }

    var root = h('div', 'sm');
    root.setAttribute('role', 'group');
    root.setAttribute('aria-label', 'System map');
    var head = h('div', 'sm-head');
    var crumbs = h('nav', 'sm-crumbs');
    crumbs.setAttribute('aria-label', 'Where you are in the map');
    var crumbList = h('ol', 'sm-crumbs__list');
    crumbs.appendChild(crumbList);
    var backBtn = button('sm-back');
    backBtn.hidden = true;
    head.appendChild(crumbs);
    head.appendChild(backBtn);
    var caption = h('p', 'sm-caption');
    var area = h('div', 'sm-area');
    // The drawing's own box inside the area: while the camera moves it holds
    // the view being left and the view arriving, one over the other.
    var view = h('div', 'sm-view');
    area.appendChild(view);
    // What the pointer or the keyboard is on, read out in a place of its own
    // (on the landing, over the card's sentence; in the explorer, in the
    // stage's corner), never over the drawing it describes.
    var tip = h('div', 'sm-readout');
    tip.hidden = true;
    tip.setAttribute('aria-hidden', 'true');
    var live = h('p', 'sm-live');
    live.setAttribute('aria-live', 'polite');
    /* A narrowing is labelled beside the controls that made it, in the strip
       of views that stays in reach at the top of the panel: a line saying
       what the drawing shows of the whole ("The map shows 15 of 42 code
       connections: reads the saved results of Formal math & proof") and a
       way to show them all again. A label over the drawing covered the
       family names round its top. The panel keeps every row and count. */
    function syncScope() {
      if (!explorer || !explorerEl.querySelector) return;
      var bar = explorerEl.querySelector('[data-system-panel] .sc__tabs');
      var N = narrowNow(), old = bar ? bar.querySelector('.sc__scopebar') : null;
      if (!bar) return;
      if (!N) { if (old && old.parentNode) old.parentNode.removeChild(old); return; }
      var box = old || h('div', 'sc__scopebar'), text = old ? old.querySelector('.sc__scopebar-text') : null;
      if (!old) {
        box.setAttribute('role', 'status');
        text = h('p', 'sc__scopebar-text');
        var all = button('sc__scopebar-all', 'Show all');
        all.addEventListener('click', function (e) {
          var key = keyOf(at), keyedIt = keyedClick(e);
          inspect.scope = null;
          Object.keys(inspect.find).forEach(function (k) { if (k.indexOf(key + '|') === 0) delete inspect.find[k]; });
          inspect.narrow = null;
          column.again();
          if (map) map.inspect();
          if (keyedIt) {
            var tab = explorerEl.querySelector('[data-system-panel] .sc__tab[aria-selected="true"]');
            if (tab && tab.focus) tab.focus();
          }
        });
        box.appendChild(text);
        box.appendChild(all);
        bar.appendChild(box);
      }
      text.textContent = N.text || '';
    }
    // In the explorer the trail stands in the panel's head, the one way back,
    // and the view's sentence opens its page in the panel; the stage holds
    // the drawing, its controls and its key, and nothing else.
    if (explorer) {
      var panelHead = explorerEl.querySelector('.explorer__head');
      crumbs.className = 'sm-crumbs sm-trail';
      if (panelHead) panelHead.appendChild(crumbs);
      if (root.classList) root.classList.add('sm--explorer');
    } else {
      root.appendChild(head);
      root.appendChild(caption);
    }
    root.appendChild(area);
    root.appendChild(tip);
    root.appendChild(live);
    var keySlot = stage.querySelector('.sm-keyslot');
    var keyBox = h('div', 'sm-key');

    /* ---- Navigation ---- */
    var SYSTEM = { level: 'system', fam: -1, comp: -1, rule: null };
    var DOCTRINE = { level: 'doctrine', fam: -1, comp: -1, rule: null };
    function copyAt(a) { return { level: a.level, fam: a.fam, comp: a.comp, rule: a.rule }; }
    function sameAt(a, b) { return a.level === b.level && a.fam === b.fam && a.comp === b.comp && a.rule === b.rule; }
    // The levels above a view, nearest last: the trail along the top.
    function ancestors(a) {
      if (a.level === 'family' || a.level === 'doctrine') return [copyAt(SYSTEM)];
      if (a.level === 'component') return [copyAt(SYSTEM), { level: 'family', fam: a.fam, comp: -1, rule: null }];
      if (a.level === 'rule') return [copyAt(SYSTEM), copyAt(DOCTRINE)];
      return [];
    }
    function navigate(next, how) {
      how = how || {};
      if (!model) return;
      if ((next.level === 'doctrine' || next.level === 'rule') && !D) return;
      var prev = copyAt(at);
      if (sameAt(prev, next)) { if (how.keyed) focusKey(keyOf(at)); return; }
      if (!how.noTrail) { trail.push(prev); if (trail.length > 60) trail.shift(); }
      at = copyAt(next);
      // A new choice frames itself: a zoom the reader made is let go.
      userCam = undefined;
      if (pageMode && !how.fromAddress) writeAddress(!!how.replace);
      render(how);
      if (at.level !== 'system') warm(keyOf(at));
      // The explorer's frame brings the reading forward on a phone.
      if (explorer && !how.fromAddress && at.level !== 'system' && explorerEl.dispatchEvent && typeof CustomEvent === 'function') {
        try { explorerEl.dispatchEvent(new CustomEvent('explorer:selected', { bubbles: true, detail: { level: at.level } })); } catch (e) {}
      }
    }
    function goSystem(how) { navigate(copyAt(SYSTEM), how); }
    function goFamily(fi, how) { navigate({ level: 'family', fam: fi, comp: -1, rule: null }, how); }
    function goComponent(ci, how) { navigate({ level: 'component', fam: model.comps[ci].fam, comp: ci, rule: null }, how); }
    function goDoctrine(rule, how) {
      if (!D) return;
      navigate(rule && D.rules[rule] ? { level: 'rule', fam: -1, comp: -1, rule: rule } : copyAt(DOCTRINE), how);
    }
    // Escape and the nearest crumb: one level up.
    function up(how) {
      var above = ancestors(at);
      if (!above.length) return false;
      how = how || {};
      how.back = true;
      how.focusTo = keyOf(at);
      navigate(above[above.length - 1], how);
      return true;
    }
    // Back: the view the reader came from, when the trail does not already
    // lead there.
    function backTarget() {
      var last = trail[trail.length - 1];
      if (!last) return null;
      var above = ancestors(at);
      for (var i = 0; i < above.length; i++) if (sameAt(above[i], last)) return null;
      return last;
    }
    function back(how) {
      var target = backTarget();
      if (!target) return false;
      how = how || {};
      how.back = true;
      if (pageMode && addressed && window.history && window.history.back) { window.history.back(); return true; }
      trail.pop();
      how.noTrail = true;
      navigate(target, how);
      return true;
    }
    function keyOf(a) {
      if (a.level === 'component') return 'comp:' + model.comps[a.comp].id;
      if (a.level === 'family') return 'fam:' + model.families[a.fam].key;
      if (a.level === 'rule') return 'rule:' + a.rule;
      if (a.level === 'doctrine') return 'doctrine';
      return null;
    }
    function nameOf(a) {
      if (a.level === 'rule') return D.rules[a.rule].title;
      if (a.level === 'doctrine') return 'the doctrine';
      if (a.level === 'component') return model.comps[a.comp].label;
      if (a.level === 'family') return model.families[a.fam].title;
      return 'the whole system';
    }

    /* ---- Opening a page ---- */
    /* Everything on the map has a page on the site: a component its own
       page (or, without one, its paper module), a rule its card on the
       doctrine page, a family its page, the doctrine its page. A click
       chooses; a second click on what is chosen, or a double click, opens
       its page (Will, 5 October 2026: if you "select and click it" it
       should "take you to that in the website and load really quick").
       Enter does the same from the keyboard, and a click with Cmd or Ctrl
       opens the page in a new tab. */
    function pageOf(key) {
      if (!model || !key) return null;
      if (key === 'doctrine' || key.indexOf('rule:') === 0) {
        if (!D) return null;
        if (key !== 'doctrine') { var r = D.rules[key.slice(5)]; return r && r.doctrine ? r.doctrine : null; }
        var any = Object.keys(D.rules).map(function (id) { return D.rules[id].doctrine; }).filter(Boolean)[0];
        return any ? any.replace(/#.*$/, '') : null;
      }
      if (key.indexOf('fam:') === 0) { var fi = familyIndex(key.slice(4)); return fi >= 0 ? model.families[fi].page || null : null; }
      for (var i = 0; key.indexOf('comp:') === 0 && i < model.comps.length; i++) {
        if ('comp:' + model.comps[i].id === key) return model.comps[i].page || model.comps[i].reader || null;
      }
      return null;
    }
    function openWords(key) {
      if (key === 'doctrine') return 'Click again to open the doctrine';
      if (key.indexOf('rule:') === 0) return 'Click again to read its card';
      if (key.indexOf('fam:') === 0) return 'Click again to open the family’s page';
      return 'Click again to open its page';
    }
    function openPage(key, e) {
      var href = pageOf(key);
      if (!href) return false;
      hideTip();
      if (e && (e.metaKey || e.ctrlKey) && window.open) { window.open(href, '_blank', 'noopener'); return true; }
      if (window.location && window.location.assign) window.location.assign(href);
      else if (window.location) window.location.href = href;
      return true;
    }
    var lastPress = null;
    function press(e, key, go) {
      if (e && e.stopPropagation) e.stopPropagation();
      var keyedIt = keyedClick(e), t = nowMs();
      if (!keyedIt && e && e.detail >= 2 && lastPress && t - lastPress.at < 700) { openPage(lastPress.key, e); return; }
      if (!keyedIt && e && (e.metaKey || e.ctrlKey) && openPage(key, e)) return;
      if (!keyedIt && key === keyOf(at) && openPage(key, e)) return;
      lastPress = keyedIt ? null : { key: key, at: t };
      go({ keyed: keyedIt });
    }
    /* What a choice can open is fetched as it is chosen, so the second click
       lands at once: one page at a time, never under Save-Data. Where the
       browser takes speculation rules and the page's policy admits them the
       page is prerendered whole; the document also goes into the cache by
       prefetch, or by a plain fetch where prefetch is off (Safari). */
    var warmed = null, warmNodes = [];

    function warm(key) {
      var href = pageOf(key);
      if (!href || !document.head || typeof document.createElement !== 'function') return;
      var conn = typeof navigator !== 'undefined' ? navigator.connection : null;
      if (conn && conn.saveData) return;
      var url;
      try { url = new URL(href, window.location.href); } catch (e) { return; }
      url.hash = '';
      if (url.href === warmed) return;
      warmed = url.href;
      warmNodes.forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
      warmNodes = [];
      // Warm bytes only. Rendering a second document competes with map input.
      var link = document.createElement('link');
      if (link.relList && link.relList.supports && link.relList.supports('prefetch')) {
        link.rel = 'prefetch';
        link.href = url.href;
        warmNodes.push(link);
      } else if (typeof fetch === 'function') {
        try { fetch(url.href, { credentials: 'same-origin' }).catch(function () {}); } catch (e) {}
      }
      warmNodes.forEach(function (n) { document.head.appendChild(n); });
    }

    /* ---- The address (own page only) ---- */
    var addressed = false;
    function hashOf(a) {
      if (a.level === 'rule') return '#map=' + encodeURIComponent('doctrine:' + a.rule);
      if (a.level === 'doctrine') return '#map=doctrine';
      if (a.level === 'component') return '#map=' + encodeURIComponent(model.comps[a.comp].id);
      if (a.level === 'family') return '#map=' + encodeURIComponent('family:' + model.families[a.fam].key);
      return '';
    }
    function writeAddress(replace) {
      var hist = window.history, loc = window.location;
      if (!hist || !loc || !hist.replaceState) return;
      var want = hashOf(at);
      if ((loc.hash || '') === want) return;
      var url = want || (loc.pathname || '') + (loc.search || '');
      try {
        if (replace || !hist.pushState) hist.replaceState(hist.state || null, '', url);
        else { hist.pushState(null, '', url); addressed = true; }
      } catch (e) {}
    }
    function parseAddress(hash) {
      var m = /^#map=([^&]*)/.exec(hash || '');
      if (!m) return null;
      var id;
      try { id = decodeURIComponent(m[1]); } catch (e) { return null; }
      if (!id || id === 'system') return copyAt(SYSTEM);
      if (id === 'doctrine' || id.indexOf('doctrine:') === 0) {
        var rid = id.slice(9);
        return { level: rid ? 'rule' : 'doctrine', fam: -1, comp: -1, rule: rid || null, needsDoctrine: true };
      }
      var fam = /^(?:family|area):(.+)$/.exec(id);
      if (fam) { var f = familyIndex(fam[1]); return f >= 0 ? { level: 'family', fam: f, comp: -1, rule: null } : null; }
      for (var c = 0; c < model.comps.length; c++) {
        if (model.comps[c].id === id) return { level: 'component', fam: model.comps[c].fam, comp: c, rule: null };
      }
      return null;
    }
    function settleAddress(want) {
      if (want.level === 'rule' && !D.rules[want.rule]) return copyAt(DOCTRINE);
      return { level: want.level, fam: want.fam, comp: want.comp, rule: want.rule };
    }
    // The address the page arrived with is where the reader starts: it
    // leaves nothing behind it to go back to.
    function arriveAt() {
      if (!model) return;
      var want = parseAddress((window.location && window.location.hash) || '');
      if (!want) return;
      if (want.needsDoctrine && !D) { pending = pending || {}; pending.arrival = true; return; }
      navigate(settleAddress(want), { fromAddress: true, noTrail: true, instant: true });
    }
    function followAddress() {
      if (!model) return;
      var want = parseAddress((window.location && window.location.hash) || '');
      if (!want) {
        if (window.location && window.location.hash) return;
        want = copyAt(SYSTEM);
      }
      if (want.needsDoctrine && !D) { pending = pending || {}; pending.address = true; return; }
      want = settleAddress(want);
      var last = trail[trail.length - 1];
      if (last && sameAt(last, want)) { trail.pop(); navigate(want, { fromAddress: true, noTrail: true, back: true }); }
      else navigate(want, { fromAddress: true });
    }

    /* ---- Pointing ---- */
    // What the pointer or the keyboard is on, lit lightly over the view.
    // rel: the one relation a connection's row is pointed at for.
    function relId(rel) { return rel ? rel.kind + '|' + rel.dir : ''; }
    function setHover(key, anchor, rel) {
      rel = key ? rel || null : null;
      if (key === hoverKey && relId(rel) === relId(hoverRel)) { if (anchor) showTipFor(key, anchor); return; }
      hoverKey = key;
      hoverRel = rel;
      if (map) map.preview(key, rel);
      column.lit(key);
      if (key && anchor) showTipFor(key, anchor);
      else if (!key) hideTip();
    }
    function hoverable(el, key, anchor) {
      el.addEventListener('pointerenter', function (e) {
        if (e && e.pointerType === 'touch') return;
        setHover(key, anchor || el);
      });
      el.addEventListener('pointerleave', function (e) {
        if (e && e.pointerType === 'touch') return;
        if (hoverKey === key) setHover(null);
      });
      el.addEventListener('focus', function () { setHover(key, anchor || el); });
      el.addEventListener('blur', function () { if (hoverKey === key) setHover(null); });
    }
    function keyedClick(e) { return !!e && e.detail === 0; }
    function focusKey(key) {
      var el = null;
      if (key && map) el = map.nodeOf(key);
      if (!el && key) {
        var hits = keyed(root, key);
        for (var i = 0; i < hits.length; i++) if (hits[i].getAttribute('tabindex') !== null || hits[i].tagName === 'BUTTON') { el = hits[i]; break; }
      }
      if (!el && map) el = map.firstNode();
      if (el) {
        if (map) map.rove(el);
        if (el.focus) { try { el.focus({ preventScroll: true }); } catch (e) { el.focus(); } }
      }
    }

    /* ---- Motion ---- */
    var EASE = 'cubic-bezier(0.22, 0.7, 0.18, 1)';
    function motionOK() { return !reduceMotion && !!root.animate && !document.hidden; }
    function nowMs() { return typeof performance !== 'undefined' && performance.now ? performance.now() : Date.now(); }
    // The camera's curve: cubic-bezier(0.3, 0.1, 0.12, 1). It leaves at once,
    // so the move is seen to answer the click within a frame or two (a
    // symmetric slow-in held the drawing still for a tenth of a second), and
    // it settles slowly, so the eye lands with it.
    function cameraEase(t) {
      var x1 = 0.3, y1 = 0.1, x2 = 0.12, y2 = 1, u = t;
      for (var i = 0; i < 8; i++) {
        var x = 3 * (1 - u) * (1 - u) * u * x1 + 3 * (1 - u) * u * u * x2 + u * u * u - t;
        var dx = 3 * (1 - u) * (1 - u) * x1 + 6 * (1 - u) * u * (x2 - x1) + 3 * u * u * (1 - x2);
        if (Math.abs(x) < 1e-5 || !dx) break;
        u = clamp(u - x / dx, 0, 1);
      }
      return 3 * (1 - u) * (1 - u) * u * y1 + 3 * (1 - u) * u * u * y2 + u * u * u;
    }

    /* ---- The camera ---- */
    /* A choice about one part of the ring brings the reader closer to it,
       as the mathematics map does when it opens a problem: a family is
       framed with each of its components named along its arc; a component
       with everything it lights (its connections and the rules it cites);
       the doctrine fills the drawing. A rule reaches round the whole ring,
       so a rule, like the whole system, is seen from the usual distance.
       The view is drawn afresh for its camera, so marks, lines and words
       keep their own sizes, and the move between two views carries both
       drawings along one path, the view left fading as the view arrived at
       comes in. Under reduced motion, or from the keyboard, the view simply
       changes. In the explorer the same closer looks frame each choice in
       its stage, and the reader's own zoom stands until the next choice. */
    var KMAX = 2.4;
    function camOf(k, cx, cy, names, nameSize) {
      names = names === undefined ? -1 : names;
      if (!(k > 1.06) && names < 0) return null;
      return { k: k, cx: cx, cy: cy, names: names, nameSize: nameSize || 15, R0: baseMap.R0, size: baseMap.size, width: baseMap.width, crowded: !!baseMap.crowded };
    }
    // The zooms to try, from the closest wanted down to the least allowed.
    function zooms(top, least) {
      var out = [];
      for (var k = top; k > least + 1e-6; k *= 0.95) out.push(k);
      out.push(least);
      return out;
    }
    function boxOfPoints(list) {
      var b = { x0: Infinity, x1: -Infinity, y0: Infinity, y1: -Infinity };
      list.forEach(function (p) {
        if (p[0] < b.x0) b.x0 = p[0];
        if (p[0] > b.x1) b.x1 = p[0];
        if (p[1] < b.y0) b.y0 = p[1];
        if (p[1] > b.y1) b.y1 = p[1];
      });
      return b;
    }
    // A family close enough for its components' names to stand side by
    // side along its arc (a name every font size and a little more round
    // the rim), the arc and the names together centred in the drawing. The
    // closest such look whose names all fit is taken, at 15px and failing
    // that 14px; where none fits, no closer look.
    // The room a closer look may fill: the drawing less its edge band, and
    // in the explorer less the bands its controls and its key stand in.
    function roomBox(pad) {
      var B = baseMap;
      return { x0: pad, x1: B.width - pad, y0: pad + (explorer ? frameInset.top : 0), y1: B.size - pad - (explorer ? frameInset.bottom : 0) };
    }
    function famCamera(fi) {
      var B = baseMap, F = model.families[fi];
      if (!F || !F.members.length || !(B.pitch > 0)) return null;
      // pad: the band at the drawing's edges where a camera's view fades out.
      var W = B.width, H = B.size, pad = 20;
      function frame(names, k) {
        var pts = [];
        names.forEach(function (n) {
          var c = Math.cos(n.a), s = Math.sin(n.a), r = k * B.R0, r2 = r + B.depth + 8 + n.w;
          pts.push([c * (r - 16), s * (r - 16)], [c * r2 - s * 10, s * r2 + c * 10], [c * r2 + s * 10, s * r2 - c * 10]);
        });
        return boxOfPoints(pts);
      }
      var sizes = [15, 14];
      for (var si = 0; si < sizes.length; si++) {
        var fs = sizes[si], cls = 'sm-rimname sm-rimname--' + fs;
        var names = F.members.map(function (ci) { return { a: B.comp[ci].a, w: textWidth(model.comps[ci].label, cls) }; });
        var least = Math.max(1, (fs + 2) / B.pitch), top = Math.max(least, Math.min(KMAX, (fs + 5) / B.pitch));
        if (least > KMAX) continue;
        var tries = zooms(top, least);
        for (var t = 0; t < tries.length; t++) {
          var b = frame(names, tries[t]);
          var room = roomBox(pad);
          if (b.x1 - b.x0 <= room.x1 - room.x0 && b.y1 - b.y0 <= room.y1 - room.y0) {
            return camOf(tries[t], (room.x0 + room.x1) / 2 - (b.x0 + b.x1) / 2, (room.y0 + room.y1) / 2 - (b.y0 + b.y1) / 2, fi, fs);
          }
        }
      }
      return null;
    }
    // A component and all it lights, with room round them for the plates
    // that name what it touches (its own plate, with the arrow to its page,
    // first): the closest look at which every plate still fits.
    function litCamera(a) {
      var B = baseMap, L = B.lightOf(a), W = B.width, H = B.size, margin = 20;
      var comps = Object.keys(L.comps).map(Number).filter(function (ci) { return !!B.comp[ci]; });
      var rules = Object.keys(L.rules).filter(function (id) { return !!B.rule[id]; });
      if (!comps.length) return null;
      var plateW = Object.create(null);
      L.plates.slice(0, 14).forEach(function (ci, rank) {
        plateW[ci] = Math.min(230, textWidth(model.comps[ci].label, 'sm-plate__text') + 16 + (rank === 0 ? 22 : 0));
      });
      function frame(k) {
        var pts = [], r = k * B.R0;
        comps.forEach(function (ci) {
          var C = B.comp[ci], c = Math.cos(C.a), s = Math.sin(C.a);
          pts.push([c * r, s * r]);
          if (plateW[ci] === undefined) return;
          // Its plate: out along the radius past the rim's furniture, then
          // beside the leader's end (over the top and under the foot, hung
          // above or below it).
          var re = r + B.depth + 12, ex = c * re, ey = s * re, w = plateW[ci];
          if (Math.abs(c) < 0.42) pts.push([ex - w / 2, ey + (s < 0 ? -34 : 34)], [ex + w / 2, ey + (s < 0 ? -34 : 34)]);
          else pts.push([ex + (c > 0 ? w + 8 : -w - 8), ey - 15], [ex + (c > 0 ? w + 8 : -w - 8), ey + 15]);
        });
        rules.forEach(function (id) { var q = B.rule[id]; pts.push([(q.x - B.cx) * k, (q.y - B.cy) * k]); });
        return boxOfPoints(pts);
      }
      var tries = zooms(KMAX, 1.12);
      for (var t = 0; t < tries.length; t++) {
        var b = frame(tries[t]);
        var room = roomBox(margin);
        if (b.x1 - b.x0 <= room.x1 - room.x0 && b.y1 - b.y0 <= room.y1 - room.y0) {
          return camOf(tries[t], (room.x0 + room.x1) / 2 - (b.x0 + b.x1) / 2, (room.y0 + room.y1) / 2 - (b.y0 + b.y1) / 2, -1);
        }
      }
      return null;
    }
    // The doctrine, filling the drawing. In the explorer it is fitted with
    // the names set beside its glyphs (6 October 2026: a review found the
    // largest area given to its empty centre while names at its edge had no
    // room): the necklace and its satellites stand in the room the controls
    // and the key leave, with a band round them for a name's width.
    function coreCamera() {
      var B = baseMap;
      if (!(B.coreOuter > 0)) return null;
      var k = Math.min(B.width, B.size) * 0.46 / B.coreOuter, cx = B.cx, cy = B.cy;
      if (explorer) {
        var room = roomBox(20), nameW = 150, nameH = 42;
        k = Math.min(k, ((room.x1 - room.x0) / 2 - nameW) / B.coreOuter, ((room.y1 - room.y0) / 2 - nameH) / B.coreOuter);
        cx = (room.x0 + room.x1) / 2;
        cy = (room.y0 + room.y1) / 2;
      }
      return camOf(clamp(k, 1, 2.2), cx, cy, -1);
    }
    function cameraFor(a) {
      if (!baseMap || !model || !a) return null;
      // In the explorer the reader's own zoom stands until the next choice.
      if (explorer && userCam !== undefined) return userCam;
      if (pageMode && !explorer) return null;
      if (a.level === 'family') return famCamera(a.fam);
      if (a.level === 'component') return litCamera(a);
      if (a.level === 'doctrine') return D ? coreCamera() : null;
      return null;
    }
    function sameCamera(a, b) {
      if (!a || !b) return !a && !b;
      return a.names === b.names && a.width === b.width && Math.abs(a.k / b.k - 1) < 0.03 && Math.abs(a.cx - b.cx) < 4 && Math.abs(a.cy - b.cy) < 4;
    }

    /* ---- The explorer's zoom ---- */
    /* A deliberate zoom (the + and - controls, the wheel or a pinch) and a
       drag that moves a zoomed map. Close enough, every component is named
       along its radius where the names stand clear of one another; the
       family's names and its run keep their places, so nothing jumps. While
       the hand is moving the drawing is carried by a transform; when it
       rests, it is drawn again for the new camera, so marks, lines and words
       keep their own sizes. Hover never moves the map. */
    var KMAX_PAGE = 4.2, ZOOM_STEP = 1.6;
    // The camera the drawing now shows (a gesture's while one is moving).
    var gesture = null;
    function viewCam() { return gesture ? gesture.cam : camOr(camNow); }
    // A camera looking at the whole map from k times closer, the point P of
    // the drawing (in its own pixels) held where it is.
    function zoomedCam(from, k, P) {
      var B = baseMap;
      k = clamp(k, 1, KMAX_PAGE);
      if (k <= 1.02) return null;
      var s = k / from.k, cx = P[0] - s * (P[0] - from.cx), cy = P[1] - s * (P[1] - from.cy);
      return clampCam({ k: k, cx: cx, cy: cy });
    }
    // The ring's centre may travel well past the stage's edges, at the
    // whole map's scale as at any other, as the mathematics map moves
    // (Will, 6 October 2026: "it should just be the exact same as the
    // mathematics one, where you can, like, click and then move around");
    // some of the ring always stays in reach, and zooming out draws it back
    // to its resting place.
    function clampCam(c) {
      var B = baseMap, room = (0.6 + 0.75 * c.k) * B.R0;
      var camera = camOf(c.k, clamp(c.cx, B.cx - room, B.cx + room), clamp(c.cy, B.cy - room, B.cy + room), 'all', 15);
      if (c.k <= 1.02) camera.names = -1;
      return camera;
    }
    // The transform that shows a drawing made for camera L as camera Z.
    function carryTo(L, Z) {
      var sc = Z.k / L.k;
      return 'translate(' + fx(Z.cx - sc * L.cx) + 'px, ' + fx(Z.cy - sc * L.cy) + 'px) scale(' + (Math.round(sc * 1e4) / 1e4) + ')';
    }
    function setView(cam, how) {
      if (!model || !baseMap) return;
      settleGesture(false);
      userCam = cam;
      if (!sameCamera(cam, camNow)) shoot(cam, how || {});
      syncZoomed();
    }
    // The point of the drawing a button zoom holds still: the thing chosen,
    // where it stands, or the middle of the view.
    function zoomAnchor(dir) {
      var B = baseMap, V = viewCam();
      if (dir > 0 && map && at.level === 'component' && B.comp[at.comp]) {
        var C = B.comp[at.comp];
        return [V.cx + V.k * (C.x - B.cx), V.cy + V.k * (C.y - B.cy)];
      }
      if (dir > 0 && map && at.level === 'family' && B.sectors[at.fam]) {
        var m = B.sectors[at.fam].mid, r = B.R0;
        return [V.cx + V.k * r * Math.cos(m), V.cy + V.k * r * Math.sin(m)];
      }
      return [B.cx, B.cy];
    }
    function zoomBy(dir, how) {
      if (!model || !baseMap) return;
      var V = viewCam(), k = V.k * Math.pow(ZOOM_STEP, dir);
      setView(zoomedCam(V, k, zoomAnchor(dir)), how);
    }
    // A gesture in progress: the drawing on screen carried to the camera the
    // hand asks for; drawn again for it a moment after the hand rests.
    var gestureTimer = 0;
    function moveGesture(cam) {
      if (!map) return;
      if (!gesture) {
        settleMove();
        gesture = { layer: camOr(camNow), cam: camOr(camNow) };
        if (map.el.classList) map.el.classList.add('is-moving');
        hideTip();
      }
      gesture.cam = cam || camOr(null);
      if (map.el.style) map.el.style.transform = carryTo(gesture.layer, gesture.cam);
      syncZoomed();
    }
    function settleGesture(draw) {
      if (gestureTimer) { clearTimeout(gestureTimer); gestureTimer = 0; }
      var g = gesture;
      if (!g) return;
      gesture = null;
      var cam = g.cam && (g.cam.k > 1.02 || Math.abs(g.cam.cx - baseMap.cx) > 0.5 ||
        Math.abs(g.cam.cy - baseMap.cy) > 0.5) ? clampCam(g.cam) : null;
      if (draw === false) {
        if (map && map.el.style) map.el.style.transform = '';
        if (map && map.el.classList) map.el.classList.remove('is-moving');
        return;
      }
      userCam = cam;
      var old = map;
      if (!sameCamera(cam, camNow)) shoot(cam, { instant: true });
      if (old && old.el.style) old.el.style.transform = '';
      if (old && old.el.classList) old.el.classList.remove('is-moving');
      syncZoomed();
    }
    function restGesture() {
      if (gestureTimer) clearTimeout(gestureTimer);
      gestureTimer = setTimeout(function () { gestureTimer = 0; settleGesture(true); }, 170);
    }
    function syncZoomed() {
      if (!explorer || !area.classList) return;
      var V = viewCam();
      area.classList.toggle('is-zoomed', V.k > 1.02);
      syncFocus();
      syncInset(V, !!gesture);
    }
    /* Focus. A choice frames itself; once the reader fits the map or zooms
       and moves away from it, "Focus" frames it again. It shows only while
       there is a framing to go back to, and keeps its place in the
       controls while it waits, so they never shift. */
    var focusBtn = null, ownMemo = { key: null, base: null, cam: null };
    // The camera a choice frames itself with, whatever the reader has done
    // since (kept while the choice and the layout stand, since a drag asks
    // for it at every step).
    function ownCamera(a) {
      var key = keyOf(a);
      if (ownMemo.key === key && ownMemo.base === baseMap) return ownMemo.cam;
      var keep = userCam;
      userCam = undefined;
      var c = cameraFor(a);
      userCam = keep;
      ownMemo = { key: key, base: baseMap, cam: c };
      return c;
    }
    function syncFocus() {
      if (!focusBtn) return;
      var own = model && baseMap && at.level !== 'system' && at.level !== 'rule' ? ownCamera(at) : null;
      var show = !!own && userCam !== undefined && !sameCamera(own, gesture ? gesture.cam : camNow);
      if (focusBtn.classList) focusBtn.classList.toggle('is-idle', !show);
      focusBtn.disabled = !show;
      focusBtn.setAttribute('aria-hidden', show ? 'false' : 'true');
    }
    function refocus(how) {
      if (!model || !baseMap || at.level === 'system') return;
      settleGesture(false);
      userCam = undefined;
      var want = cameraFor(at);
      if (!sameCamera(want, camNow)) shoot(want, how || {});
      syncZoomed();
    }
    /* The inset: where a closer view stands in the whole. A small ring of
       the families' runs, the doctrine at its middle, what is chosen as a
       dot, and the view as a frame that travels with the camera. It shows
       only while the view is closer than the whole map, and is never
       pressed: Fit and the trail are the ways back. */
    var inset = null;
    function makeInset() {
      if (!explorer || inset || !root.appendChild) return;
      var box = h('div', 'sm-inset');
      box.setAttribute('aria-hidden', 'true');
      var s = sv('svg', { 'class': 'sm-inset__svg', viewBox: '-50 -50 100 100', width: 88, height: 88, focusable: 'false' });
      var arcs = sv('g', { 'class': 'sm-inset__arcs' });
      var core = sv('circle', { 'class': 'sm-inset__core', cx: 0, cy: 0, r: 13 });
      var dot = sv('circle', { 'class': 'sm-inset__dot', cx: 0, cy: 0, r: 2.6 });
      var frame = sv('rect', { 'class': 'sm-inset__view', x: 0, y: 0, width: 1, height: 1 });
      [arcs, core, dot, frame].forEach(function (n) { s.appendChild(n); });
      box.appendChild(s);
      root.appendChild(box);
      inset = { box: box, arcs: arcs, core: core, dot: dot, frame: frame, drawn: null };
    }
    var INSET_R = 34;
    function insetPoint(B, x, y) { var u = INSET_R / B.R0; return [(x - B.cx) * u, (y - B.cy) * u]; }
    function syncInset(V, live) {
      if (!inset || !baseMap || !model) return;
      var B = baseMap;
      // The families' runs, drawn again only for a new layout.
      if (inset.drawn !== B) {
        clear(inset.arcs);
        ring.order.forEach(function (fi) {
          var S = B.sectors[fi];
          if (!S) return;
          var a0 = S.runFrom, a1 = S.runTo, p0 = polar(0, 0, INSET_R, a0), p1 = polar(0, 0, INSET_R, a1);
          inset.arcs.appendChild(sv('path', { 'class': 'sm-inset__arc', 'data-fam': model.families[fi].key,
            d: 'M' + pt(p0) + 'A' + INSET_R + ' ' + INSET_R + ' 0 ' + (a1 - a0 > Math.PI ? 1 : 0) + ' 1 ' + pt(p1) }));
        });
        inset.core.setAttribute('r', fx(INSET_R * (B.coreOuter > 0 ? B.coreOuter / B.R0 : 0.4)));
        inset.drawn = B;
      }
      Array.prototype.forEach.call(inset.arcs.children || [], function (p) {
        if (p.classList) p.classList.toggle('is-self', at.fam >= 0 && p.getAttribute('data-fam') === model.families[at.fam].key);
      });
      // What is chosen, as a dot where it stands.
      var spot = null;
      if (at.level === 'component' && B.comp[at.comp]) spot = insetPoint(B, B.comp[at.comp].x, B.comp[at.comp].y);
      else if (at.level === 'rule' && B.rule[at.rule]) spot = insetPoint(B, B.rule[at.rule].x, B.rule[at.rule].y);
      inset.dot.setAttribute('cx', spot ? fx(spot[0]) : 0);
      inset.dot.setAttribute('cy', spot ? fx(spot[1]) : 0);
      if (inset.dot.classList) {
        inset.dot.classList.toggle('is-shown', !!spot);
        inset.dot.classList.toggle('is-rule', at.level === 'rule');
      }
      // The view: the drawing's box as the camera sees it, in the ring's
      // own units, carried by a transform so it can travel with the move.
      var on = V.k > 1.02;
      if (inset.box.classList) {
        inset.box.classList.toggle('is-shown', on);
        inset.box.classList.toggle('is-live', !!live);
      }
      if (!on) return;
      var tl = insetPoint(B, B.cx + (0 - V.cx) / V.k, B.cy + (0 - V.cy) / V.k);
      var br = insetPoint(B, B.cx + (B.width - V.cx) / V.k, B.cy + (B.size - V.cy) / V.k);
      if (inset.frame.style) inset.frame.style.transform = 'translate(' + fx(tl[0]) + 'px, ' + fx(tl[1]) + 'px) scale(' + fx(Math.max(0.5, br[0] - tl[0])) + ', ' + fx(Math.max(0.5, br[1] - tl[1])) + ')';
    }
    function wireExplorer() {
      if (!explorer || wireExplorer.done) return;
      wireExplorer.done = true;
      makeInset();
      var tools = explorerEl.querySelector ? explorerEl.querySelector('.explorer__tools') : null;
      if (tools && tools.insertBefore) {
        focusBtn = button('explorer-tool explorer-tool--focus is-idle', 'Focus');
        focusBtn.setAttribute('title', 'Frame what is chosen (F)');
        focusBtn.disabled = true;
        focusBtn.setAttribute('aria-hidden', 'true');
        tools.insertBefore(focusBtn, tools.firstChild);
        focusBtn.addEventListener('click', function (e) { refocus({ keyed: keyedClick(e) }); });
        // The reading panel folds away for a larger map and comes back from
        // the same place (assets/explorer.js does the folding); full screen
        // keeps it, so the map, the panel and the controls enlarge together.
        var panelEl = explorerEl.querySelector('.explorer__panel');
        if (!tools.querySelector('[data-explorer-panel-toggle]')) {
          var fold = button('explorer-tool explorer-tool--panel');
          fold.setAttribute('data-explorer-panel-toggle', '');
          var folded = !!(explorerEl.classList && explorerEl.classList.contains('is-panel-collapsed'));
          fold.setAttribute('aria-expanded', folded ? 'false' : 'true');
          if (panelEl && panelEl.id) fold.setAttribute('aria-controls', panelEl.id);
          fold.setAttribute('title', folded ? 'Show the reading panel' : 'Hide the reading panel');
          var ico = h('span', 'explorer-tool__ico');
          ico.setAttribute('aria-hidden', 'true');
          ico.innerHTML = '<svg viewBox="0 0 16 16" focusable="false"><rect x="1.75" y="2.75" width="12.5" height="10.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/>' +
            '<path d="M6 3v10" stroke="currentColor" stroke-width="1.5"/></svg>';
          fold.appendChild(ico);
          var lab = h('span', null, folded ? 'Show panel' : 'Hide panel');
          lab.setAttribute('data-explorer-panel-label', '');
          fold.appendChild(lab);
          tools.insertBefore(fold, tools.firstChild);
        }
      }
      explorerEl.addEventListener('explorer:fit', function () { if (model) setView(null, {}); });
      explorerEl.addEventListener('explorer:zoom', function (e) { zoomBy(e && e.detail && e.detail.direction < 0 ? -1 : 1, {}); });
      explorerEl.addEventListener('explorer:resize', function () { requestRefresh(); });
      // The wheel, or a pinch on a trackpad, zooms about the pointer.
      area.addEventListener('wheel', function (e) {
        if (!model || !baseMap || !area.getBoundingClientRect) return;
        if (e.preventDefault) e.preventDefault();
        var r = area.getBoundingClientRect(), P = [e.clientX - r.left, e.clientY - r.top];
        var dy = e.deltaY * (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);
        var V = viewCam(), k = clamp(V.k * Math.exp(-dy * (e.ctrlKey ? 0.01 : 0.0022)), 1, KMAX_PAGE);
        moveGesture(k > 1.02 ? zoomedCam(V, k, P) : null);
        restGesture();
      }, { passive: false });
      // A drag moves the map at every scale; two fingers pinch it. A press that moves
      // is no click: it never chooses or steps back.
      var pointers = Object.create(null), drag = null, moved = false;
      function pts() { return Object.keys(pointers).map(function (id) { return pointers[id]; }); }
      area.addEventListener('pointerdown', function (e) {
        if (!model || !baseMap || (e.button && e.button !== 0)) return;
        var r = area.getBoundingClientRect();
        pointers[e.pointerId] = [e.clientX - r.left, e.clientY - r.top];
        var list = pts();
        drag = { start: list.map(function (p) { return p.slice(); }), cam: viewCam(), n: list.length, r: r };
        moved = false;
      });
      area.addEventListener('pointermove', function (e) {
        if (!drag || !pointers[e.pointerId]) return;
        var r = drag.r;
        pointers[e.pointerId] = [e.clientX - r.left, e.clientY - r.top];
        var list = pts();
        if (list.length !== drag.n) { drag = { start: list.map(function (p) { return p.slice(); }), cam: viewCam(), n: list.length, r: r }; return; }
        if (list.length >= 2) {
          var d0 = Math.hypot(drag.start[0][0] - drag.start[1][0], drag.start[0][1] - drag.start[1][1]);
          var d1 = Math.hypot(list[0][0] - list[1][0], list[0][1] - list[1][1]);
          var mid0 = [(drag.start[0][0] + drag.start[1][0]) / 2, (drag.start[0][1] + drag.start[1][1]) / 2];
          var mid1 = [(list[0][0] + list[1][0]) / 2, (list[0][1] + list[1][1]) / 2];
          if (!(d0 > 4)) return;
          var k = clamp(drag.cam.k * d1 / d0, 1, KMAX_PAGE), z = k > 1.02 ? zoomedCam(drag.cam, k, mid0) : null;
          if (z) z = clampCam({ k: z.k, cx: z.cx + mid1[0] - mid0[0], cy: z.cy + mid1[1] - mid0[1] });
          moved = true;
          moveGesture(z);
          return;
        }
        var dx = list[0][0] - drag.start[0][0], dy = list[0][1] - drag.start[0][1];
        // The same 3px a press may wander and still be a click on the
        // mathematics map.
        if (!moved && dx * dx + dy * dy < 9) return;
        moved = true;
        if (e.preventDefault) e.preventDefault();
        if (area.setPointerCapture && !drag.captured) { drag.captured = true; try { area.setPointerCapture(e.pointerId); } catch (err) {} }
        if (area.classList) area.classList.add('is-dragging');
        moveGesture(clampCam({ k: drag.cam.k, cx: drag.cam.cx + dx, cy: drag.cam.cy + dy }));
      });
      function lift(e) {
        if (!pointers[e.pointerId]) return;
        delete pointers[e.pointerId];
        if (pts().length) { var r = drag ? drag.r : area.getBoundingClientRect(), list = pts(); drag = { start: list.map(function (p) { return p.slice(); }), cam: viewCam(), n: list.length, r: r }; return; }
        drag = null;
        if (gesture) settleGesture(true);
        if (area.classList) area.classList.remove('is-dragging');
      }
      area.addEventListener('pointerup', lift);
      area.addEventListener('pointercancel', lift);
      // The click that ends a drag is swallowed before it reaches the map.
      area.addEventListener('click', function (e) {
        if (!moved) return;
        moved = false;
        if (e.stopPropagation) e.stopPropagation();
        if (e.preventDefault) e.preventDefault();
      }, true);
      // + and - zoom, 0 fits and the arrows move the map (Shift for a long
      // step), from anywhere on the stage; on a focused mark the arrows
      // walk the marks instead (the drawing's own handler claims them).
      stage.addEventListener('keydown', function (e) {
        if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.altKey) return;
        var t = e.target;
        if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) return;
        var arrow = { ArrowLeft: [1, 0], ArrowRight: [-1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] }[e.key];
        if (arrow && model && baseMap) {
          e.preventDefault();
          var V = viewCam(), stepPx = e.shiftKey ? 240 : 80;
          setView(clampCam({ k: V.k, cx: V.cx + arrow[0] * stepPx, cy: V.cy + arrow[1] * stepPx }), { keyed: true });
          return;
        }
        if (e.key === '+' || e.key === '=') { e.preventDefault(); zoomBy(1, { keyed: true }); }
        else if (e.key === '-' || e.key === '_') { e.preventDefault(); zoomBy(-1, { keyed: true }); }
        else if (e.key === '0') { e.preventDefault(); setView(null, { keyed: true }); }
        else if ((e.key === 'f' || e.key === 'F') && focusBtn && !focusBtn.disabled) { e.preventDefault(); refocus({ keyed: true }); }
      });
    }
    /* The move. Each drawing is laid out for its own camera; while the
       camera travels from one to the other (its scale geometrically, the
       point it looks at in a straight line, slow in and slow out, as Heer
       and Robertson recommend for a move the eye must follow) both drawings
       ride the same path as one picture, the new one coming in over the
       old as it settles. Only transform and opacity animate. */
    var flight = null;
    function camOr(c) { return c || { k: 1, cx: baseMap.cx, cy: baseMap.cy }; }
    function track(from, to, layer, n) {
      var c0x = baseMap.cx, c0y = baseMap.cy, Dx = baseMap.width / 2, Dy = baseMap.size / 2, out = [];
      var qa = [c0x + (Dx - from.cx) / from.k, c0y + (Dy - from.cy) / from.k];
      var qb = [c0x + (Dx - to.cx) / to.k, c0y + (Dy - to.cy) / to.k];
      for (var i = 0; i < n; i++) {
        var e = cameraEase(i / (n - 1)), k = from.k * Math.pow(to.k / from.k, e);
        var qx = qa[0] + (qb[0] - qa[0]) * e, qy = qa[1] + (qb[1] - qa[1]) * e, sc = k / layer.k;
        var tx = k * (c0x - layer.cx / layer.k - qx) + Dx, ty = k * (c0y - layer.cy / layer.k - qy) + Dy;
        out.push({ transform: 'translate(' + fx(tx) + 'px, ' + fx(ty) + 'px) scale(' + (Math.round(sc * 1e4) / 1e4) + ')', offset: i / (n - 1) });
      }
      return out;
    }
    function settleMove() {
      var p = pendingShot;
      if (p) {
        // A move that set off before its view was drawn, overtaken: the
        // view on screen stops where it is drawn, for its own camera.
        pendingShot = null;
        if (p.anim) { try { p.anim.cancel(); } catch (e) {} }
        if (p.old.el.classList) p.old.el.classList.remove('is-moving');
        if (map === p.old) camNow = p.from;
      }
      var f = flight;
      if (!f) return;
      flight = null;
      f.anims.forEach(function (an) { try { an.cancel(); } catch (e) {} });
      if (f.old && f.old !== map && f.old.el.parentNode) f.old.el.parentNode.removeChild(f.old.el);
      [f.old, f.next].forEach(function (x) {
        if (x && x.el.classList) { x.el.classList.remove('is-moving'); x.el.classList.remove('is-leaving'); }
      });
    }
    // A return to a recent camera reuses its geometry and event targets.
    // The cache is bounded and discarded for any geometry/font change.
    var cameraMaps = new Map();
    function cameraMap(want) {
      var key = JSON.stringify(want), found = cameraMaps.get(key);
      if (found) return found;
      var drawn = buildMap(want);
      cameraMaps.set(key, drawn);
      if (cameraMaps.size > 3) cameraMaps.delete(cameraMaps.keys().next().value);
      return drawn;
    }
    // How long a move takes: longer the further the camera travels and the
    // more it changes scale, never more than two thirds of a second.
    function moveDuration(A, Z) {
      var Dx = baseMap.width / 2, Dy = baseMap.size / 2;
      var travel = Math.sqrt(Math.pow((Dx - A.cx) / A.k - (Dx - Z.cx) / Z.k, 2) + Math.pow((Dy - A.cy) / A.k - (Dy - Z.cy) / Z.k, 2));
      return Math.round(Math.min(680, 340 + 170 * Math.abs(Math.log(Z.k / A.k) / Math.LN2) + 0.12 * travel));
    }
    /* Leaving at once. A view not drawn before takes a while to draw, so
       where the move is animated the view on screen sets off along the
       camera's path in the frame the click lands in (the move runs on the
       compositor and keeps its pace while the page works), and the view
       arriving is drawn once that frame is on screen, joining the move
       where it has got to and coming in over the view it replaces. The
       click is answered in the next frame, however long the new view takes
       to draw. A page not being painted (hidden, or with no frames) draws
       the new view at once. */
    var pendingShot = null;
    function afterPaint(fn) {
      var raf = window.requestAnimationFrame;
      if (typeof raf !== 'function' || document.visibilityState !== 'visible') { fn(); return; }
      raf.call(window, function () { setTimeout(fn, 0); });
    }
    function shoot(want, how) {
      settleMove();
      var old = map, from = camNow;
      var key = want ? JSON.stringify(want) : null;
      if (want && key && !cameraMaps.has(key) && motionOK() && !how.instant && !how.keyed && onScreen && !!old && !!old.el.animate &&
          document.visibilityState === 'visible' && typeof window.requestAnimationFrame === 'function') {
        lead(old, from, want, how);
        return;
      }
      var next = want ? cameraMap(want) : baseMap;
      var carry = motionOK() && !how.instant && !how.keyed && onScreen && !!old && old !== next && !!old.el.animate;
      map = next;
      camNow = want;
      if (next.el.parentNode !== view) view.appendChild(next.el);
      var seen = {};
      Object.keys(how).forEach(function (key) { seen[key] = how[key]; });
      if (carry) seen.later = 170;
      next.select(at, seen);
      if (!carry) {
        if (old && old !== next && old.el.parentNode) old.el.parentNode.removeChild(old.el);
        return;
      }
      var A = camOr(from), Z = camOr(want);
      var dur = moveDuration(A, Z);
      var anims = [];
      old.el.classList.add('is-moving');
      old.el.classList.add('is-leaving');
      next.el.classList.add('is-moving');
      try {
        anims.push(old.el.animate(track(A, Z, A, 14), { duration: dur, easing: 'linear', fill: 'both' }));
        anims.push(next.el.animate(track(A, Z, Z, 14), { duration: dur, easing: 'linear', fill: 'both' }));
        anims.push(old.el.animate([{ opacity: 1 }, { opacity: 1, offset: 0.22 }, { opacity: 0, offset: 0.56 }, { opacity: 0 }], { duration: dur, easing: 'linear', fill: 'both' }));
        anims.push(next.el.animate([{ opacity: 0 }, { opacity: 0, offset: 0.08 }, { opacity: 1, offset: 0.46 }, { opacity: 1 }], { duration: dur, easing: 'linear', fill: 'both' }));
      } catch (e) {}
      var mine = { old: old, next: next, anims: anims };
      flight = mine;
      tipHushUntil = nowMs() + dur + 160;
      hideTip();
      var done = function () { if (flight === mine) settleMove(); };
      if (anims[1]) anims[1].onfinish = done;
      setTimeout(done, dur + 90);
    }
    // The view on screen sets off; the view arriving is drawn after this
    // frame. Only transform moves until then: the view on screen keeps its
    // place in the page, so nothing round the drawing shifts.
    function lead(old, from, want, how) {
      var A = camOr(from), Z = camOr(want), dur = moveDuration(A, Z), anim = null;
      if (old.el.classList) old.el.classList.add('is-moving');
      try { anim = old.el.animate(track(A, Z, A, 14), { duration: dur, easing: 'linear', fill: 'both' }); } catch (e) { anim = null; }
      camNow = want;
      tipHushUntil = nowMs() + dur + 160;
      hideTip();
      var mine = { old: old, from: from, want: want, how: how, A: A, Z: Z, dur: dur, start: nowMs(), anim: anim };
      pendingShot = mine;
      afterPaint(function () { if (pendingShot === mine) { pendingShot = null; arrive(mine); } });
    }
    function arrive(p) {
      var next = cameraMap(p.want), old = p.old, elapsed = Math.min(p.dur, nowMs() - p.start), rest = Math.max(0, p.dur - elapsed);
      map = next;
      if (next.el.parentNode !== view) view.appendChild(next.el);
      var seen = {};
      Object.keys(p.how).forEach(function (key) { seen[key] = p.how[key]; });
      // The light runs once the camera is nearly there.
      seen.later = Math.max(0, 170 - elapsed);
      next.select(at, seen);
      if (old.el.classList) old.el.classList.add('is-leaving');
      if (next.el.classList) next.el.classList.add('is-moving');
      var anims = p.anim ? [p.anim] : [], fade = Math.max(90, Math.min(220, rest));
      try {
        anims.push(next.el.animate(track(p.A, p.Z, p.Z, 14), { duration: p.dur, delay: -elapsed, easing: 'linear', fill: 'both' }));
        anims.push(old.el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: fade, easing: 'linear', fill: 'forwards' }));
        anims.push(next.el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: Math.round(fade * 0.7), easing: EASE, fill: 'backwards' }));
      } catch (e) {}
      var mine = { old: old, next: next, anims: anims };
      flight = mine;
      var done = function () { if (flight === mine) settleMove(); };
      setTimeout(done, Math.max(rest, fade) + 90);
    }

    /* ---- Rendering ---- */
    // The card's height less its drawing's, once laid out: what the circle
    // leaves room for on the landing, so the card fits the window.
    var chromeH = 0, refitting = false;
    function fitHeight() {
      if (pageMode || refitting || !map || !stage.getBoundingClientRect || !map.svg.getBoundingClientRect) return;
      if (stage.classList && stage.classList.contains('is-parked')) return;
      if (stage.style && stage.style.removeProperty) stage.style.removeProperty('--sm-floor');
      // The card less its drawing's area (not the drawing: beside its column
      // the area may stand taller than the circle, and that room is not
      // chrome, or the circle would shrink each time it was fitted).
      var c = stage.getBoundingClientRect().height - Math.max(area.getBoundingClientRect().height, 0);
      if (!(area.getBoundingClientRect().height > 0)) c = stage.getBoundingClientRect().height - map.svg.getBoundingClientRect().height;
      if (!(c > 0) || Math.abs(c - chromeH) < 3) return;
      chromeH = c;
      refitting = true;
      relayout();
      refitting = false;
    }
    function render(how) {
      how = how || {};
      if (!model) return;
      hideTip();
      renderHead();
      caption.textContent = captionText();
      renderKey();
      if (!map) { baseMap = map = buildMap(null); camNow = null; clear(view); view.appendChild(map.el); }
      root.setAttribute('data-view', at.level);
      // The camera frames what the view is about; where it moves, the view
      // is drawn again for it and the reader is carried there.
      var want = cameraFor(at);
      if (!sameCamera(want, camNow)) shoot(want, how);
      else map.select(at, how);
      if (at.level === 'system') fitHeight();
      column.sync(how);
      measureFloor();
      column.refit();
      announce();
      syncExpand();
      syncZoomed();
      if (how.keyed) focusKey(how.focusTo || keyOf(at) || null);
    }
    /* The landing's way into the full map (the atlas bar's "Expand map",
       a[data-system-expand]) follows the drawing's choice, so a reader looking
       at a component arrives at the explorer with it still chosen. */
    function syncExpand() {
      if (pageMode || !model || !document.querySelectorAll) return;
      var href = base + 'system-map.html' + hashOf(at);
      Array.prototype.forEach.call(document.querySelectorAll('a[data-system-expand]'), function (a) {
        if (a.getAttribute('href') !== href) a.setAttribute('href', href);
      });
    }
    // The map is laid out again for a new size; the view stays as it was.
    function relayout() {
      if (!model) return;
      cameraMaps.clear();
      textWidths = Object.create(null);
      wordWidths = Object.create(null);
      settleMove();
      // A new stage is fitted afresh; a zoom made for the old one is let go.
      if (explorer) { settleGesture(false); userCam = undefined; }
      hoverKey = null;
      hideTip();
      renderKey();
      baseMap = buildMap(null);
      camNow = cameraFor(at);
      map = camNow ? buildMap(camNow) : baseMap;
      clear(view);
      view.appendChild(map.el);
      map.select(at, { instant: true });
      // A new layout at the top level fits the card to the window again.
      if (at.level === 'system') fitHeight();
      measureFloor();
      column.refit();
      syncZoomed();
    }
    function renderHead() {
      clear(crumbList);
      var path = ancestors(at).concat([copyAt(at)]);
      // The explorer's trail is the panel's compact context line: the levels
      // above what is chosen, each a way back to it (what is chosen is the
      // title of the page under it). At rest the panel's own title and
      // sentence stand instead.
      if (explorer) {
        path = ancestors(at);
        var headEl = explorerEl.querySelector('.explorer__head');
        if (headEl && headEl.classList) headEl.classList.toggle('is-collapsed', at.level !== 'system');
        crumbs.hidden = !path.length;
      }
      path.forEach(function (a, k) {
        var li = h('li', 'sm-crumbs__item');
        var label = a.level === 'system' ? (explorer ? 'The system map' : 'System') : a.level === 'doctrine' ? 'The doctrine' : capital(nameOf(a));
        if (!explorer && k === path.length - 1) {
          var here = h('span', 'sm-crumbs__here', label);
          here.setAttribute('aria-current', 'location');
          li.appendChild(here);
        } else {
          var b = button('sm-crumbs__go', label);
          b.addEventListener('click', function (e) {
            navigate(a, { keyed: keyedClick(e), back: true, focusTo: keyOf(path[k + 1] || copyAt(at)) });
          });
          li.appendChild(b);
        }
        crumbList.appendChild(li);
      });
      var target = backTarget();
      backBtn.hidden = !target;
      if (target) {
        var words = 'Back to ' + nameOf(target);
        backBtn.textContent = '';
        var mark = h('span', 'sm-back__mark', '‹');
        mark.setAttribute('aria-hidden', 'true');
        backBtn.appendChild(mark);
        backBtn.appendChild(document.createTextNode(' ' + words));
        backBtn.setAttribute('aria-label', words);
        backBtn.removeAttribute('title');
        if (backBtn.getBoundingClientRect && crumbs.getBoundingClientRect) {
          var bb = backBtn.getBoundingClientRect(), cb = crumbs.getBoundingClientRect();
          if (bb.height > 0 && cb.height > 0 && bb.top > cb.top + cb.height / 2) {
            backBtn.lastChild.textContent = ' Back';
            backBtn.setAttribute('title', words);
          }
        }
      }
    }
    backBtn.addEventListener('click', function (e) { back({ keyed: keyedClick(e) }); });

    function onlyNamed() { return !!model && model.kinds.length > 0 && model.kinds.every(function (k) { return k === 'named'; }); }
    function linkNoun(n) { return onlyNamed() ? plural(n, 'listed relation', 'listed relations') : plural(n, 'code connection', 'code connections'); }
    // How many components have no code connection at all (none is claimed
    // for a scene of listed relations).
    function unconnected() {
      if (!model || onlyNamed() || !model.links.length) return 0;
      return model.comps.filter(function (c) { return !c.out.length && !c.inc.length; }).length;
    }
    // The file a connection comes from, on the repository the components'
    // sources are published in. No line anchor: the published repository can
    // lag the source the evidence lines were read from, and a wrong line is
    // worse than a whole file.
    function codeHref(a, b) {
      if (!model || !model.codeBase) return null;
      for (var i = 0; i < model.links.length; i++) {
        var l = model.links[i];
        if (!l.ev || !((l[0] === a && l[1] === b) || (l[0] === b && l[1] === a))) continue;
        return model.codeBase + l.ev.path.split('/').map(encodeURIComponent).join('/');
      }
      return null;
    }
    /* One component's code connections: each a link of the scene, in the
       scene's own order, with its kind, the way it runs from this
       component's side, the component at its other end, that one's family
       and the file holding the code that establishes it. Every row, count,
       line, narrowing and sentence the explorer shows of a component's
       connections is read from this one list, so the panel and the drawing
       tell one story: a count of connections is a count of these, never of
       the distinct components they reach. */
    function relationsOf(ci) {
      var out = [];
      if (!model || ci < 0) return out;
      model.links.forEach(function (l, k) {
        if (l[0] !== ci && l[1] !== ci) return;
        var other = l[0] === ci ? l[1] : l[0];
        out.push({ k: k, kind: l.kind, dir: l.kind === 'named' ? 'both' : l[0] === ci ? 'out' : 'inc', other: other,
                   fam: model.comps[other].fam, href: linkHref(l) });
      });
      return out;
    }
    function linkHref(l) {
      return model && model.codeBase && l && l.ev ? model.codeBase + l.ev.path.split('/').map(encodeURIComponent).join('/') : null;
    }
    // The relations under their verbs: each kind in the scene's order, out
    // before in; a listed relation has no direction worth reading.
    function relationGroups(ci) {
      var rels = relationsOf(ci), groups = [];
      LINK_ORDER.forEach(function (kind) {
        (kind === 'named' ? ['both'] : ['out', 'inc']).forEach(function (dir) {
          var mine = rels.filter(function (x) { return x.kind === kind && x.dir === dir; });
          if (mine.length) groups.push({ kind: kind, dir: dir, rels: mine });
        });
      });
      return groups;
    }
    // One relation as a sentence, the component acting first, so reversing
    // the viewpoint never reverses what the code does.
    var RELATION_VERBS = { runs: 'runs', reads: 'reads the saved results of', checks: 'checks the copied files of',
                           named: 'is listed as related to', other: 'connects to' };
    function relationSentence(kind, dir, self, other) {
      var a = dir === 'inc' ? other : self, b = dir === 'inc' ? self : other;
      return a + ' ' + (RELATION_VERBS[kind] || RELATION_VERBS.other) + ' ' + b + '.';
    }
    // How a rule stands in a component, in the words the panel, the readout
    // and the drawing's frames share: cited by its paper module, enforced
    // there by a test, a narrower part of it checked there by a test. The
    // three never stand for one another.
    var HELD_WORDS = {
      full: 'Enforced here: a test shows the rule’s core requirement in this component.',
      part: 'Partly checked here: a test shows a narrower part of the rule in this component.'
    };
    function heldIn(ci, id) {
      var info = D && D.comp[ci];
      if (!info) return null;
      return info.enforces.indexOf(id) >= 0 ? 'full' : info.partly.indexOf(id) >= 0 ? 'part' : null;
    }
    function citesRule(ci, id) {
      var info = D && D.comp[ci];
      return !!info && (info.gov.indexOf(id) >= 0 || info.abide.indexOf(id) >= 0);
    }
    // What the drawing is narrowed to, when it belongs to what is chosen.
    function narrowNow() {
      var N = inspect.narrow;
      return N && model && N.key && N.key === keyOf(at) ? N : null;
    }

    // What the red lines are, for the key.
    function aboutLines() {
      if (onlyNamed()) return 'Red lines are the relations each component’s own record lists, not read from the code.';
      var none = unconnected();
      return 'Red lines are derived from the code: each one rests on the place in the code where one component runs another, ' +
        'reads its saved results or checks its copied files.' + (none ? ' ' + none + ' of the ' + model.comps.length + ' components ' + (none === 1 ? 'has' : 'have') + ' none.' : '');
    }
    function linkNote() {
      if (onlyNamed()) return 'Listed in a component’s own record, not read from the code.';
      return model.codeBase && model.links.some(function (l) { return !!l.ev; }) ?
        'Each is derived from the code; Code opens the file that makes it.' : 'Each connection is derived from the code.';
    }
    // The view's sentence, as what it is about and what the map shows of it.
    function captionParts() {
      var n = model.comps.length;
      if (at.level === 'family') {
        var F = model.families[at.fam];
        return [F.title, 'its ' + countWords(F.members.length, 'component', 'components') + ' and their ' + linkNoun(2) + ', inside the family and out to the others.'];
      }
      if (at.level === 'component') {
        var c = model.comps[at.comp];
        var rules = D ? ', azure lines to the rules its paper module cites.' : '.';
        if (!c.out.length && !c.inc.length) return [c.label, (onlyNamed() ? 'its record lists no related components' : 'no code connections to other components') +
          (D ? '; azure lines to the rules its paper module cites.' : '.')];
        if (onlyNamed()) return [c.label, 'red lines to the components listed as related' + rules];
        return [c.label, 'red lines for its code connections' + rules];
      }
      if (at.level === 'doctrine') {
        return ['The doctrine', countWords(D.axioms.length, 'axiom', 'axioms') + ' on a ring. A rule tied to one axiom sits just outside it; a rule tied to several stands between them.'];
      }
      if (at.level === 'rule') {
        var r = D.rules[at.rule];
        if (r.kind === 'failure') return [r.title, 'lit with the axioms it threatens and the components ' + (D.enforcedBy === 'tests' ?
          'where a test shows it enforced' + (r.partly.length ? ' or checks part of it' : '') + '.' : 'its card names as enforcing it.')];
        var into = r.kind === 'axiom' ? 'the principles and failure modes tied to it' : 'the axioms it rests on';
        return [r.title, 'lit with ' + into + ', and azure lines out to the components whose paper modules cite it.'];
      }
      var none = unconnected();
      return [null, n + ' components round the rim in ' + numberWord(model.families.length) + ' families' +
        (none ? ', ' + none + ' of them with no code connection,' : '') +
        (D ? (none ? ' and' : ',') + ' the doctrine at the centre' : '') + '. Select any of them to light what it touches.'];
    }
    // The card's trail already names what is chosen, in bold, just above;
    // the sentence says only what the map shows of it (a Type B review, 6
    // October 2026, found the name said three times over).
    function captionText() {
      var p = captionParts();
      return p[0] ? capital(p[1]) : p[1];
    }
    function announce() {
      var text;
      if (at.level === 'rule') text = KIND_WORDS[D.rules[at.rule].kind] + ': ' + D.rules[at.rule].title + '.';
      else if (at.level === 'doctrine') text = 'The doctrine.';
      else if (at.level === 'family') text = model.families[at.fam].title + ': ' + countWords(model.families[at.fam].members.length, 'component', 'components') + '.';
      else if (at.level === 'component') {
        var c = model.comps[at.comp];
        var touching = model.links.filter(function (l) { return l[0] === at.comp || l[1] === at.comp; }).length;
        text = c.label + ': ' + countFigure(touching, linkNoun(1), linkNoun(2)) + '.';
      } else text = 'The whole system.';
      live.textContent = text;
    }

    /* ---- The key ---- */
    /* One row in plain words: each kind of connection the data holds in its
       own texture, the rule lines and the three kinds of rule; in a rule's
       own view, its marks of enforcement too. The marks round the rim, the
       doctrine's own lines and the weave wait behind a small disclosure at
       its end, so the drawing never ends in rows of legend; every mark the
       map draws is named in one or the other. */
    var keyOpen = false;
    function keyItem(it) {
      var span = h('span', 'sm-key__item');
      var mark = h('span', 'sm-key__mark');
      mark.setAttribute('aria-hidden', 'true');
      if (it.glyph) { mark.className = 'sm-key__mark sm-key__mark--comp'; mark.innerHTML = glyphSvg(it.glyph); }
      else if (it.doctrine) { mark.className = 'sm-key__mark sm-key__mark--rule'; mark.innerHTML = doctrineSvg(it.doctrine); }
      else if (it.line) mark.className = 'sm-key__line sm-key__line--' + it.line;
      else if (it.reticle) mark.className = 'sm-key__reticle' + (it.reticle === 'part' ? ' sm-key__reticle--part' : '');
      else if (it.bar) mark.className = 'sm-key__bar';
      else if (it.cap) mark.className = 'sm-key__cap' + (it.cap === 'part' ? ' sm-key__cap--part' : '');
      else if (it.weave) mark.className = 'sm-key__weave';
      else if (it.sheaf) {
        // A ribbon that parts into three fibres.
        mark.className = 'sm-key__mark sm-key__mark--sheaf';
        mark.innerHTML = '<svg viewBox="0 0 26 12" width="26" height="12" aria-hidden="true" focusable="false"><path fill="currentColor" ' +
          'd="M0 6C5 5.2 9 3.6 14 3.6L26 1.2V2.2L15.5 4.7L26 5.5V6.5L15.5 7.3L26 9.8V10.8L14 8.4C9 8.4 5 6.8 0 6Z"/></svg>';
      }
      span.appendChild(mark);
      span.appendChild(h('span', 'sm-note', it.text));
      return span;
    }
    // Where a rule is said to be enforced: by a test (the manifest that
    // derives it from passing tests), or, until that manifest exists, by
    // each rule's doctrine card.
    function byTests() { return !!D && D.enforcedBy === 'tests'; }
    function renderKey() {
      clear(keyBox);
      var row = h('div', 'sm-key__row');
      // What the view draws: each kind of connection the data holds, in its
      // own texture (a rule's view draws none, and names its frames instead);
      // the rule lines; the three kinds of rule.
      var ruleView = !!D && (at.level === 'rule' || at.level === 'doctrine');
      var items = ruleView ? [] : model.kinds.map(function (k) { return { line: 'k-' + k, text: LINK_WORDS[k].key }; });
      if (D) {
        if (at.level !== 'doctrine') items.push({ line: 'azure', text: 'Cited by its paper module' });
        items.push({ doctrine: 'axiom', text: 'Axiom' }, { doctrine: 'principle', text: 'Principle' }, { doctrine: 'failure', text: 'Failure mode' });
        if (at.level === 'doctrine') items.push({ line: 'span', text: 'Rests on' }, { line: 'threat', text: 'Threatens' });
        if (at.level === 'rule') {
          var r = D.rules[at.rule];
          if (r.enforced.length) items.push({ reticle: 'full', text: byTests() ? 'Enforced here' : 'Enforced here, by its card' });
          if (r.partly.length) items.push({ reticle: 'part', text: 'Partly checked here' });
        }
      }
      // The explorer's key on the stage is this one row; every other mark is
      // named in the panel, under how the map is drawn, so the stage never
      // grows rows of legend over the drawing. Its lines and its marks are
      // two groups, so where the row must break it breaks between them.
      if (explorer) {
        var lines = h('span', 'sm-key__group'), marks = h('span', 'sm-key__group');
        items.forEach(function (it) { (it.line ? lines : marks).appendChild(keyItem(it)); });
        [lines, marks].forEach(function (g) { if (g.firstChild) row.appendChild(g); });
        keyBox.appendChild(row);
        renderPanelKey();
        return;
      }
      items.forEach(function (it) { row.appendChild(keyItem(it)); });
      var more = button('sm-key__more sm-note', 'Key');
      more.setAttribute('aria-expanded', keyOpen ? 'true' : 'false');
      more.setAttribute('aria-label', 'Key: every mark in the map');
      more.addEventListener('click', function (e) {
        keyOpen = !keyOpen;
        renderKey();
        if (keyedClick(e)) { var again = keyBox.querySelector && keyBox.querySelector('.sm-key__more'); if (again && again.focus) again.focus(); }
      });
      row.appendChild(more);
      keyBox.appendChild(row);
      if (!keyOpen) return;
      var rest = h('div', 'sm-key__row sm-key__row--more');
      model.classes.forEach(function (cls) { rest.appendChild(keyItem({ glyph: cls, text: CLASS_WORDS[cls] })); });
      if (map && map.sheaves && map.sheaves.length) rest.appendChild(keyItem({ sheaf: true, text: 'One component’s lines to several in one family travel as one ribbon' }));
      if (D) {
        var full = D.comp.some(function (info) { return info.enforces.length > 0; }), part = D.comp.some(function (info) { return info.partly.length > 0; });
        rest.appendChild(keyItem({ bar: true, text: 'One step for each rule its paper module cites' }));
        if (full) rest.appendChild(keyItem({ cap: 'full', text: byTests() ? 'A test shows a rule enforced here' : 'A rule’s card says it is enforced here' }));
        if (part) rest.appendChild(keyItem({ cap: 'part', text: 'A test checks part of a rule here' }));
        rest.appendChild(keyItem({ line: 'span', text: 'Rests on' }));
        rest.appendChild(keyItem({ line: 'threat', text: 'Threatens' }));
        rest.appendChild(keyItem({ weave: true, text: 'Where a red line and an azure line cross, one passes over the other' }));
      }
      keyBox.appendChild(rest);
      // About these lines: where the red ones come from, and how many
      // components have none.
      if (model.links.length) keyBox.appendChild(h('p', 'sm-key__about sm-note', aboutLines()));
    }
    var panelKeyState = null;
    function renderPanelKey() {
      var about = explorerEl && explorerEl.querySelector ? explorerEl.querySelector('.system-explorer__about') : null;
      var want = (D ? 'd' : '-') + (baseMap && baseMap.sheaves ? baseMap.sheaves.length : 0);
      if (!about || !model || want === panelKeyState) return;
      panelKeyState = want;
      var old = about.querySelector('.sm-key--panel');
      if (old && old.parentNode) old.parentNode.removeChild(old);
      var box = h('div', 'sm-key sm-key--panel');
      var list = h('div', 'sm-key__row sm-key__row--list');
      var all = model.classes.map(function (cls) { return { glyph: cls, text: CLASS_WORDS[cls] }; });
      model.kinds.forEach(function (k) { all.push({ line: 'k-' + k, text: LINK_WORDS[k].key }); });
      if (baseMap && baseMap.sheaves && baseMap.sheaves.length) all.push({ sheaf: true, text: 'One component’s lines to several in one family travel as one ribbon' });
      if (D) {
        var full = D.comp.some(function (info) { return info.enforces.length > 0; }), part = D.comp.some(function (info) { return info.partly.length > 0; });
        all.push({ line: 'azure', text: 'Cited by its paper module' });
        all.push({ doctrine: 'axiom', text: 'Axiom' }, { doctrine: 'principle', text: 'Principle' }, { doctrine: 'failure', text: 'Failure mode' });
        all.push({ line: 'span', text: 'Rests on' }, { line: 'threat', text: 'Threatens' });
        all.push({ bar: true, text: 'One step for each rule its paper module cites' });
        if (full) all.push({ cap: 'full', text: byTests() ? 'A test shows a rule enforced here' : 'A rule’s card says it is enforced here' });
        if (part) all.push({ cap: 'part', text: 'A test checks part of a rule here' });
        all.push({ weave: true, text: 'Where a red line and an azure line cross, one passes over the other' });
      }
      all.forEach(function (it) { list.appendChild(keyItem(it)); });
      box.appendChild(list);
      if (model.links.length) box.appendChild(h('p', 'sm-key__about', aboutLines()));
      about.appendChild(box);
    }

    /* ---- The map ---- */
    function familyIndex(key) {
      for (var i = 0; i < model.families.length; i++) if (model.families[i].key === key) return i;
      return -1;
    }
    /* Words are measured in a drawing that stays in the page, out of sight,
       a batch at a time: every word of every style the map sets is read in
       one layout, once, and a name is as wide as its words and the spaces
       between them. Measuring a name at a time made each choice wait on a
       layout for every word it set (about forty milliseconds a choice). */
    var measurer = null, textWidths = Object.create(null), wordWidths = Object.create(null);
    function measureWords(pairs) {
      var want = [], seen = Object.create(null);
      pairs.forEach(function (p) {
        var key = p[1] + '\n' + p[0];
        if (wordWidths[key] === undefined && !seen[key]) { seen[key] = true; want.push(p); }
      });
      if (!want.length) return;
      if (!measurer) {
        var box = sv('svg', { 'class': 'sm-measure', width: 1, height: 1, 'aria-hidden': 'true', focusable: 'false' });
        root.appendChild(box);
        measurer = sv('g');
        box.appendChild(measurer);
      }
      var nodes = want.map(function (p) {
        var t = sv('text', { 'class': p[1] });
        t.textContent = p[0];
        measurer.appendChild(t);
        return t;
      });
      nodes.forEach(function (t, i) {
        var w = t.getComputedTextLength ? t.getComputedTextLength() : 0;
        wordWidths[want[i][1] + '\n' + want[i][0]] = w > 0 ? w : 0;
      });
      nodes.forEach(function (t) { measurer.removeChild(t); });
    }
    // Every word of these names in these styles, and each style's space
    // (the width of "n n" less that of "nn"), measured together.
    function prewarm(list) {
      var pairs = [], styles = Object.create(null);
      list.forEach(function (it) {
        styles[it[1]] = true;
        String(it[0]).split(' ').forEach(function (w) { if (w) pairs.push([w, it[1]]); });
      });
      Object.keys(styles).forEach(function (cls) { pairs.push(['nn', cls], ['n n', cls]); });
      measureWords(pairs);
    }
    function textWidth(text, cls) {
      var key = cls + '\n' + text;
      if (textWidths[key] !== undefined) return textWidths[key];
      prewarm([[text, cls]]);
      var words = String(text).split(' '), w = 0, gap = (wordWidths[cls + '\nn n'] || 0) - (wordWidths[cls + '\nnn'] || 0);
      for (var i = 0; i < words.length; i++) w += words[i] ? wordWidths[cls + '\n' + words[i]] || 0 : 0;
      w += (words.length - 1) * gap;
      return (textWidths[key] = w > 0 ? w : String(text).length * (/sector__name|plate|centre/.test(cls) ? 8.6 : 7.4));
    }
    function countLine(F) { return countFigure(F.members.length, 'component', 'components'); }
    // How many rules a component's paper module cites, and how strongly a
    // rule is shown to hold there: enforced, or a narrower part of it checked.
    function citesOf(ci) { var info = D && D.comp[ci]; return info && !info.missing ? info.gov.length + info.abide.length : 0; }
    function enforcement(ci) {
      var info = D && D.comp[ci];
      if (!info) return null;
      return info.enforces.length ? 'full' : info.partly.length ? 'part' : null;
    }
    // A rule's share of a component's bar, in pixels.
    var BAR_PX = 0.8;
    // How far the rim's furniture reaches past the marks: the scale (its
    // base 9px out, a tick to 13px), then the bar of the rules the paper
    // module cites, then the mark of a rule enforced there.
    function rimDepth() {
      var most = 0;
      if (D) model.comps.forEach(function (c, i) { most = Math.max(most, citesOf(i)); });
      return 16 + most * BAR_PX + (D ? 6 : 0);
    }
    // How big the circle is on the landing: as wide as the drawing allows
    // and no taller than the window leaves room for, within bounds.
    function landingRadius(width, depth) {
      var vh = window.innerHeight || 900, room = depth + 13 + 18 + 12;
      // The bar under the map (its key, and the way to the full map) takes
      // what its key needs; a second row of key comes out of the circle.
      var bar = keySlot && keySlot.parentNode && keySlot.parentNode.getBoundingClientRect ? keySlot.parentNode.getBoundingClientRect().height : 0;
      var byWidth = width / 2 - room;
      // Everything in the card but the drawing, as measured once it has been
      // laid out (until then, an estimate): the window's height less the bar
      // along its top is what the card may take.
      var chrome = chromeH > 0 ? chromeH : 135 + Math.max(0, bar - 56);
      var byHeight = (vh - 75 - chrome) / 2 - room;
      // Beside its column the card is exactly as tall as the mathematics
      // slide (one frame for both drawings, 5 October 2026), so the band
      // never grows when the switch turns to the system: the circle takes
      // what that height leaves.
      var row = mathsRow();
      if (row > 0) byHeight = Math.min(byHeight, (row - chrome) / 2 - room);
      return clamp(Math.min(byWidth, Math.max(byHeight, 180)), 140, 430);
    }
    // The mathematics slide's height beside its column, where the band
    // lays the two slides out side by side (0 elsewhere).
    function mathsRow() {
      if (pageMode || !slide || !slide.parentNode || !framedBand()) return 0;
      var other = slide.parentNode.querySelector ? slide.parentNode.querySelector('[data-atlas-slide="mathematics"] .home-split') : null;
      var r = other && other.getBoundingClientRect ? other.getBoundingClientRect() : null;
      return r && r.height > 0 ? r.height : 0;
    }
    function framedBand() {
      try { return !!(window.matchMedia && window.matchMedia('(min-width: 961px)').matches); } catch (e) { return false; }
    }
    /* The explorer fits the whole circle, its family names round the outside
       included, to the stage it has, with a modest margin. The controls in
       the stage's top right and the key in its bottom left stand over the
       drawing: where either would touch the circle, its band is kept clear
       and the circle takes the rest. Where the circle cannot stand whole
       (a very small stage), it keeps a least size and the reader zooms. */
    var avoidRects = [];
    function explorerFit(depth, bare) {
      var box = area.getBoundingClientRect ? area.getBoundingClientRect() : null;
      var W = Math.max(280, box && box.width || 0) || 760, H = Math.max(280, box && box.height || 0) || 640;
      // bare: no room is kept for the family names round the outside.
      var reach = bare ? depth + 10 : depth + 13 + 18 + 12, gut = clamp(Math.round(Math.min(W, H) * 0.03), 14, 34);
      function rel(el) {
        if (!el || !el.getBoundingClientRect || !box) return null;
        var r = el.getBoundingClientRect();
        if (!(r.width > 0 && r.height > 0)) return null;
        return { x0: r.left - box.left, x1: r.right - box.left, y0: r.top - box.top, y1: r.bottom - box.top };
      }
      // The key's own words, not its row's full width.
      var keyR = null;
      if (keyBox && keyBox.querySelectorAll) {
        Array.prototype.forEach.call(keyBox.querySelectorAll('.sm-key__item, .sm-key__more'), function (n) {
          var q = rel(n);
          if (!q) return;
          keyR = keyR ? { x0: Math.min(keyR.x0, q.x0), x1: Math.max(keyR.x1, q.x1), y0: Math.min(keyR.y0, q.y0), y1: Math.max(keyR.y1, q.y1) } : q;
        });
      }
      var toolsR = rel(explorerEl.querySelector('.explorer__tools'));
      function place(top, bottom) {
        var h = H - top - bottom, r = Math.min(W - 2 * gut, h - 2 * gut) / 2 - reach;
        return { R: r, cx: W / 2, cy: top + h / 2, outer: r + reach };
      }
      function touches(q, p) {
        if (!q) return false;
        var nx = clamp(p.cx, q.x0, q.x1), ny = clamp(p.cy, q.y0, q.y1);
        return Math.sqrt((nx - p.cx) * (nx - p.cx) + (ny - p.cy) * (ny - p.cy)) < p.outer + 6;
      }
      var top = 0, bottom = 0, p = place(0, 0);
      for (var pass = 0; pass < 2; pass++) {
        if (touches(toolsR, p)) top = Math.max(top, toolsR.y1 + 2 - gut * 0.5);
        if (touches(keyR, p)) bottom = Math.max(bottom, H - keyR.y0 + 2 - gut * 0.5);
        p = place(top, bottom);
      }
      // The inset in the bottom right, shown while the view is closer than
      // the whole map: no name or plate is set under it.
      avoidRects = [toolsR, keyR, { x0: W - 14 - 88, x1: W - 14, y0: H - 14 - 88, y1: H - 14 }].filter(Boolean);
      frameInset = { top: toolsR ? Math.max(0, toolsR.y1 + 4) : 0, bottom: keyR ? Math.max(0, H - keyR.y0 + 4) : 0 };
      return { width: W, height: H, R: Math.max(96, p.R), cx: p.cx, cy: p.cy };
    }
    var frameInset = { top: 0, bottom: 0 };
    /* The drawing's radii, as fractions of R (the radius the marks sit on):
       the doctrine's necklace (the axioms, and the rules tied to several of
       them) and the satellites just outside it; the lanes the fibres swoop
       through on their way between two families, and the families' hubs
       they gather at; how deep a link inside one family dips below the rim;
       how far a fibre runs straight in from its mark. */
    var RING = { hub: 0.4, sat: 0.495, lanes: [0.612, 0.78], famHub: 0.815, localDepth: 0.14, leave: 0.045 };
    /* The order of the axioms round the necklace with the fewest crossings
       among the rules that join several of them (22 crossings in 9 depths,
       the best of forty searches over the drawing itself). It is used while
       it names exactly these axioms; a changed doctrine is ordered afresh. */
    var HUB_ORDER = ['AX-12', 'AX-5', 'AX-8', 'AX-6', 'AX-10', 'AX-4', 'AX-11', 'AX-9', 'AX-3', 'AX-2', 'AX-7', 'AX-1'];
    // Code connections are few enough to draw at rest; hundreds of listed
    // relations are left to the choices that light them.
    var REST_MOST = 90;
    // Each kind of connection in its own weight (and texture, below).
    var KIND_WIDTH = { runs: 1, reads: 0.86, checks: 1.3, named: 0.8, other: 0.9 };
    // A rule line comes in round the outside of the core this far at most
    // (a seventh of the way round); a rule further round is reached across
    // the core.
    var NEAR = 50 * Math.PI / 180;

    /* cam, when given, is a closer look at the same drawing: the ring drawn
       k times larger with its centre at (cx, cy) in a box of the whole
       system's size. Every angle stays the whole system's, so a mark keeps
       its place round the ring; what grows is the room between things.
       Marks, lines and words keep their own sizes, the way a map keeps its
       type as it zooms. */
    // Every name a drawing may set, in every style it may set it in.
    function allNames() {
      var out = [['Doctrine', 'sm-centre__label']];
      model.families.forEach(function (F) { out.push([F.title, 'sm-sector__name'], [countLine(F), 'sm-sector__count']); });
      model.comps.forEach(function (c) {
        out.push([c.label, 'sm-plate__text'], [c.label, 'sm-rimname sm-rimname--15'], [c.label, 'sm-rimname sm-rimname--14']);
      });
      if (D) Object.keys(D.rules).forEach(function (id) {
        var r = D.rules[id];
        out.push([r.title, TAG_TITLE], [r.title, RULE_NAME], [KIND_WORDS[r.kind], TAG_KIND]);
      });
      return out;
    }
    function buildMap(cam) {
      var el = h('div', 'sm-body sm-body--ring');
      prewarm(allNames());
      var order = ring.order, nF = order.length, nComp = model.comps.length;
      var depth = rimDepth();
      // The explorer's drawing is its stage, the circle fitted inside it.
      var fit = !cam && explorer ? explorerFit(depth) : null;
      var width = cam ? cam.width : fit ? fit.width : Math.max(320, (area.getBoundingClientRect ? area.getBoundingClientRect().width : 0) || 760);
      // R0: the ring as the whole system draws it; R: as this camera sees it.
      var R0 = cam ? cam.R0 : fit ? fit.R : landingRadius(width, depth), R = cam ? R0 * cam.k : R0;
      /* Crowded: a circle too small for every family's name to stand round
         it at its sector (a phone). The sectors then follow their runs alone
         and a family is named round the outside only where its name fits
         its own arc and the drawing; the explorer gives the ring the room
         the names would have taken. The panel names every family. */
      var crowded = cam ? !!cam.crowded : false;
      if (!cam) {
        var widest = model.families.map(function (F) {
          return Math.max(textWidth(F.title, 'sm-sector__name'), textWidth(countLine(F), 'sm-sector__count'));
        });
        var needs = function (r0) {
          var n = nF * 16 / r0;
          order.forEach(function (fi) { n += Math.max(model.families[fi].members.length * 7 / r0, (widest[fi] + 26) / (r0 + depth + 13)); });
          return n;
        };
        crowded = needs(R0) > TAU;
        if (crowded && fit) { fit = explorerFit(depth, true); R0 = R = fit.R; }
      }
      var labelR1 = R + depth + 13, labelR2 = labelR1 + 18, labelR10 = R0 + depth + 13;
      var size = cam ? cam.size : fit ? fit.height : Math.ceil(2 * (labelR10 + 18 + 12));
      var cx = cam ? cam.cx : fit ? fit.cx : width / 2, cy = cam ? cam.cy : fit ? fit.cy : size / 2;
      size = Math.round(size);
      // Lines grow more slowly than the ring, so a large drawing stays fine;
      // a closer look keeps the whole drawing's weights.
      var s = R0 / 320, rs = Math.sqrt(s), ws = Math.pow(s, 0.6);
      var svg = sv('svg', { 'class': 'sm-ring' + (cam ? ' is-camera' : '') + (!revealed && motionOK() ? ' awaits-reveal' : ''), width: fx(width), height: size,
        viewBox: '0 0 ' + fx(width) + ' ' + size, role: 'group',
        'aria-label': 'The system: ' + nComp + ' components round the rim in ' + numberWord(nF) + ' families' + (D ? ', the doctrine at the centre' : '') });
      var AZ_W = fx(Math.max(1, rs)), SPAN_W = fx(Math.max(0.9, 0.9 * rs));
      if (svg.style && svg.style.setProperty) {
        svg.style.setProperty('--sm-az', AZ_W + 'px');
        svg.style.setProperty('--sm-span', SPAN_W + 'px');
      }
      el.appendChild(svg);
      // Layers, back to front.
      var defs = sv('defs');
      var gScale = sv('g', { 'class': 'sm-scale', 'aria-hidden': 'true' });
      var gRest = sv('g', { 'class': 'sm-rest', 'aria-hidden': 'true' });
      var gNeck = sv('g', { 'class': 'sm-neck', 'aria-hidden': 'true' });
      var gSpans = sv('g', { 'class': 'sm-spans', 'aria-hidden': 'true' });
      var gLight = sv('g', { 'class': 'sm-light', 'aria-hidden': 'true' });
      var gLitRed = sv('g', { 'class': 'sm-light__red' }), gLitAz = sv('g', { 'class': 'sm-light__azure' });
      gLight.appendChild(gLitRed);
      gLight.appendChild(gLitAz);
      var gCore = sv('g', { 'class': 'sm-core' });
      var gRim = sv('g', { 'class': 'sm-rim' });
      var gLabels = sv('g', { 'class': 'sm-sectors' });
      var gPlates = sv('g', { 'class': 'sm-plates', 'aria-hidden': 'true' });
      var gMarks = sv('g', { 'class': 'sm-reticles', 'aria-hidden': 'true' });
      // The names a view sets on the drawing (the chosen rule's tag, the
      // rules a view lights), and over everything the name of what the
      // pointer or the keyboard is on.
      var gTags = sv('g', { 'class': 'sm-tags', 'aria-hidden': 'true' });
      var gHover = sv('g', { 'class': 'sm-hovers', 'aria-hidden': 'true' });
      // The light that runs along a choice's lines, above them, under the marks.
      var gFx = sv('g', { 'class': 'sm-fx', 'aria-hidden': 'true' });
      // A component's connections drawn one by one, each its own whole
      // route: those a narrowing in the panel keeps, and over them the one
      // relation being examined. Neither is a ribbon: in a focused view a
      // bundle stops acting as a highway. Beside each ribbon a choice
      // lights, how many connections it carries.
      var gScope = sv('g', { 'class': 'sm-scoped', 'aria-hidden': 'true' });
      var gTrace = sv('g', { 'class': 'sm-trace', 'aria-hidden': 'true' });
      var gCounts = sv('g', { 'class': 'sm-counts', 'aria-hidden': 'true' });
      [defs, gScale, gRest, gNeck, gSpans, gLight, gScope, gTrace, gFx, gCore, gRim, gLabels, gPlates, gCounts, gMarks, gTags, gHover].forEach(function (g) { svg.appendChild(g); });

      /* ---- The rim ---- */
      /* One spacing for every component round the ring; a sector is as wide
         as its run and its name need (crowded, its run alone); whatever is
         left is shared out so the circle closes. */
      var labelW = model.families.map(function (F) {
        return Math.max(textWidth(F.title, 'sm-sector__name'), textWidth(countLine(F), 'sm-sector__count'));
      });
      var gapA = 16 / R0;
      function floorOf(fi) { return crowded ? 0 : (labelW[fi] + 26) / labelR10; }
      function needAt(p) {
        var total = nF * gapA;
        order.forEach(function (fi) {
          total += Math.max(model.families[fi].members.length * p, floorOf(fi));
        });
        return total;
      }
      var lo = 7 / R0, hi = 22 / R0;
      for (var it = 0; it < 30; it++) { var mid = (lo + hi) / 2; if (needAt(mid) <= TAU) lo = mid; else hi = mid; }
      var pitch = lo;
      var pitchPx = pitch * R, spare = Math.max(0, TAU - needAt(pitch)) / nF;
      // Every mark at least ten pixels, so its cut survives a reader's zoom.
      var markSize = clamp(pitch * R0 - 2, 10, 11.5);
      var sectors = [], comp = [];
      var firstSpan = Math.max(model.families[order[0]].members.length * pitch, floorOf(order[0])) + spare;
      var a0 = -Math.PI / 2 - firstSpan / 2;
      order.forEach(function (fi) {
        var F = model.families[fi];
        var span = Math.max(F.members.length * pitch, floorOf(fi)) + spare;
        var midA = a0 + span / 2, runFrom = midA - F.members.length * pitch / 2;
        sectors[fi] = { fam: fi, lo: a0, hi: a0 + span, mid: midA, runFrom: runFrom, runTo: runFrom + F.members.length * pitch };
        F.members.forEach(function (ci, k) {
          var a = runFrom + (k + 0.5) * pitch, p = polar(cx, cy, R, a);
          comp[ci] = { a: a, x: p[0], y: p[1], bar: citesOf(ci) * BAR_PX, enf: enforcement(ci) };
        });
        a0 += span + gapA;
      });

      /* ---- The core: the doctrine as a necklace ---- */
      /* The twelve axioms stand on a ring with the rules tied to several of
         them between them, each in a gap between two of its own axioms; a
         rule tied to one axiom is its satellite just outside, principles on
         one side of the axiom's radius and failure modes on the other. Each
         rests-on or threatens line is a short curve that leaves and lands
         along the radius; none comes near the centre's name. The whole is
         turned toward the components whose paper modules cite each axiom. */
      var core = null, rule = Object.create(null), coreOuter = 0.3 * R, centreClear = 40, labelBox = null, hubR = RING.hub * R, coreGap = Infinity;
      if (D && D.axioms.length >= 3) {
        var align = Object.create(null);
        D.axioms.forEach(function (aid) {
          // An axiom wants to stand where the lines to it and to the rules
          // beside it come from.
          var x = 0, y = 0;
          D.comp.forEach(function (info, ci) {
            if (!comp[ci]) return;
            var w = info.abide.indexOf(aid) >= 0 ? 1 : 0;
            info.gov.forEach(function (pid) { var on = D.rules[pid].restsOn; if (on.indexOf(aid) >= 0) w += 1 / on.length; });
            x += w * Math.cos(comp[ci].a);
            y += w * Math.sin(comp[ci].a);
          });
          if (x || y) align[aid] = { a: Math.atan2(y, x), w: Math.sqrt(x * x + y * y) };
        });
        var labelWide = textWidth('Doctrine', 'sm-centre__label');
        centreClear = labelWide / 2 + 12;
        // Every glyph at least ten pixels, so its shape survives a reader's zoom.
        var gsz = { axiom: Math.max(11, 12.5 * rs), principle: Math.max(10, 10 * rs), failure: Math.max(10, 9.5 * rs) };
        var spec = {
          cx: cx, cy: cy, axioms: D.axioms,
          rules: D.principles.map(function (id) { return { id: id, kind: 'principle', on: D.rules[id].restsOn }; })
            .concat(D.failures.map(function (id) { return { id: id, kind: 'failure', on: D.rules[id].guards }; })),
          rLabel: Math.max(centreClear, 0.135 * R), rHub: RING.hub * R, rSat: RING.sat * R, size: gsz,
          lanePitch: 3.4 * s, satOffset: Math.max(10 * rs, gsz.principle / 2 + 3.5), corner: 3.2 * s, align: align, order: HUB_ORDER
        };
        core = Loom.coreLayout(spec);
        // Glyphs that would touch: an order chosen afresh for this doctrine,
        // then a wider necklace, a step at a time (a small drawing, or a
        // doctrine the pinned order was not searched for).
        if (core.stats.glyphGap < 2) {
          var fresh = Loom.coreLayout(Object.assign({}, spec, { order: null }));
          if (fresh.stats.glyphGap > core.stats.glyphGap) { core = fresh; spec.order = null; }
        }
        if (core.stats.glyphGap < 2) {
          // Hubs set evenly round the ring leave the most room between them
          // for satellites.
          var even = Loom.coreLayout(Object.assign({}, spec, { evenHubs: true }));
          if (even.stats.glyphGap > core.stats.glyphGap) { core = even; spec.evenHubs = true; }
        }
        for (var widen = 0; core.stats.glyphGap < 2 && widen < 6; widen++) {
          spec.rHub += 0.012 * R;
          spec.rSat += 0.012 * R;
          core = Loom.coreLayout(spec);
        }
        hubR = spec.rHub;
        // Two satellites of neighbouring axioms that would still touch: the
        // second crosses to the other side of its own axiom, after the
        // satellites already there, and its line is drawn again.
        var sats = Object.keys(core.glyphs).filter(function (id) { return core.glyphs[id].role === 'satellite'; });
        sats.forEach(function (idB) {
          var B = core.glyphs[idB];
          var clash = sats.some(function (idA) {
            var A = core.glyphs[idA];
            return idA !== idB && A.hub !== B.hub && Math.sqrt((A.x - B.x) * (A.x - B.x) + (A.y - B.y) * (A.y - B.y)) - (A.size + B.size) / 2 < 2;
          });
          if (!clash) return;
          var H = core.glyphs[B.hub], side = turn(H.a, B.a) > 0 ? -1 : 1, far = 0;
          sats.forEach(function (id) {
            var O = core.glyphs[id];
            if (O.hub === B.hub && id !== idB && (turn(H.a, O.a) > 0 ? 1 : -1) === side) far = Math.max(far, Math.abs(turn(H.a, O.a)) * O.r + O.size / 2);
          });
          var off = Math.max(spec.satOffset, far + 6 + B.size / 2) / B.r;
          B.a = norm(H.a + side * off);
          B.x = cx + B.r * Math.cos(B.a);
          B.y = cy + B.r * Math.sin(B.a);
          core.lines.forEach(function (ln) {
            if (ln.from !== idB) return;
            var r0 = H.r + H.size / 2 + 2, r1 = B.r - B.size / 2 - 2, aH = B.a + turn(B.a, H.a), k = (r1 - r0) * 0.55;
            ln.polar = Loom.polarBezier([aH, r0], [aH, r0 + k], [B.a, r1 - k], [B.a, r1], 1.5);
            ln.pts = Loom.polarXY(cx, cy, ln.polar);
          });
        });
        var gids = Object.keys(core.glyphs);
        for (var gi = 0; gi < gids.length; gi++) for (var gj = gi + 1; gj < gids.length; gj++) {
          var P = core.glyphs[gids[gi]], Q = core.glyphs[gids[gj]];
          coreGap = Math.min(coreGap, Math.sqrt((P.x - Q.x) * (P.x - Q.x) + (P.y - Q.y) * (P.y - Q.y)) - (P.size + Q.size) / 2);
        }
        Object.keys(core.glyphs).forEach(function (id) {
          var g = core.glyphs[id];
          rule[id] = { a: g.a, r: g.r, x: g.x, y: g.y, kind: g.kind, role: g.role, size: g.size, half: g.size / 2, hub: g.hub || null };
        });
        coreOuter = 0;
        Object.keys(rule).forEach(function (id) { coreOuter = Math.max(coreOuter, rule[id].r + rule[id].half); });
        coreOuter += 3;
        labelBox = { x0: cx - labelWide / 2 - 8, x1: cx + labelWide / 2 + 8, y0: cy - 13, y1: cy + 13 };
      }

      /* ---- Fibres: the links between components ---- */
      /* Out of a mark along its radius, in to its family's hub, along a swoop
         to the other family's hub (deeper the further it travels, never into
         the doctrine) and out to the far mark, bundled with every link
         between the same two families (hierarchical edge bundling, drawn in
         polar form). Inside one family a link is a short U just within the
         rim. Each is a filled outline that tapers: thin where it leaves its
         component, fuller in the bundle, parting at the far end, so the
         drawing carries direction without arrowheads. */
      var hubs = [];
      order.forEach(function (fi) { hubs[fi] = sectors[fi].mid; });
      var rimR = R - markSize / 2 - 3, famHubR = RING.famHub * R;
      /* Sheaves. Where one component has two or more links of one kind to
         the components of another family (one component reads the saved
         results of forty others), they travel as one ribbon, as wide as the
         links it carries allow, from its mark through the bundle to that
         family's hub, and part there into one short fibre to each, nested
         so the farthest runs deepest and none crosses another. A link
         belongs to the larger sheaf at either of its ends. */
      var SHEAF_MIN = 2;
      var sheaves = [], sheafOf = model.links.map(function () { return -1; });
      (function () {
        var groups = Object.create(null), list = [];
        model.links.forEach(function (l, k) {
          if (!comp[l[0]] || !comp[l[1]]) return;
          var fa = model.comps[l[0]].fam, fb = model.comps[l[1]].fam;
          if (fa === fb) return;
          [['out', l[0], fb], ['in', l[1], fa]].forEach(function (g) {
            var key = g[0] + '|' + g[1] + '|' + l.kind + '|' + g[2];
            if (!groups[key]) { groups[key] = { role: g[0], h: g[1], kind: l.kind, fam: g[2], links: [] }; list.push(groups[key]); }
            groups[key].links.push(k);
          });
        });
        list.sort(function (p, q) { return q.links.length - p.links.length || p.h - q.h || p.fam - q.fam || (p.role < q.role ? -1 : p.role > q.role ? 1 : 0); });
        list.forEach(function (g) {
          var free = g.links.filter(function (k) { return sheafOf[k] < 0; });
          if (free.length < SHEAF_MIN) return;
          free.forEach(function (k) { sheafOf[k] = sheaves.length; });
          sheaves.push({ role: g.role, h: g.h, kind: g.kind, fam: g.fam, links: free });
        });
      })();
      // One bundle for the links drawn alone and for each sheaf's ribbon,
      // the ribbon's far end a point at its family's hub.
      var bAt = model.comps.map(function (c, ci) { return comp[ci] ? comp[ci].a : 0; });
      var bGroup = model.comps.map(function (c) { return c.fam; });
      var bLinks = [], bOf = [];
      model.links.forEach(function (l, k) { bOf[k] = sheafOf[k] < 0 ? bLinks.push(l) - 1 : -1; });
      sheaves.forEach(function (S) {
        bAt.push(hubs[S.fam]);
        bGroup.push(S.fam);
        S.b = bLinks.push([S.h, bAt.length - 1]) - 1;
      });
      var bRoutes = bLinks.length ? Loom.bundle({
        cx: cx, cy: cy, R: R, at: bAt, group: bGroup, hub: hubs, links: bLinks,
        rimR: rimR, hubR: famHubR, lanes: [RING.lanes[0] * R, RING.lanes[1] * R], beta: 0.85,
        leave: RING.leave * R, fibrePitch: 0.4 * s, localGain: 0.22, localDepth: [7 * s, RING.localDepth * R], px: 2.5, shape: 'swoop'
      }) : [];
      // A ribbon parts where its last run out to the rim crosses the hubs'
      // ring; each fibre from there leaves along the ribbon, travels at its
      // own depth (the farthest deepest) and meets its mark along the radius.
      sheaves.forEach(function (S) {
        var rt = bRoutes[S.b], pol = rt.polar, cut = rt.pts.length - 1, mid = Math.floor(cut / 2);
        while (cut > mid && pol[cut - 1][1] > famHubR) cut--;
        S.pts = rt.pts.slice(0, cut + 1);
        S.pair = rt.pair;
        var aE = pol[cut][0], rE = pol[cut][1], room = Math.max(4, rimR - rE);
        S.end = { a: aE, r: rE };
        S.twig = Object.create(null);
        [-1, 1].forEach(function (side) {
          var mine = S.links.filter(function (k) {
            var m = S.role === 'out' ? model.links[k][1] : model.links[k][0];
            return (turn(aE, comp[m].a) >= 0 ? 1 : -1) === side;
          }).sort(function (p, q) {
            var mp = S.role === 'out' ? model.links[p][1] : model.links[p][0], mq = S.role === 'out' ? model.links[q][1] : model.links[q][0];
            return Math.abs(turn(aE, comp[mp].a)) - Math.abs(turn(aE, comp[mq].a)) || p - q;
          });
          mine.forEach(function (k, j) {
            var m = S.role === 'out' ? model.links[k][1] : model.links[k][0], am = aE + turn(aE, comp[m].a);
            var depth = rE + room * (0.86 - 0.62 * (mine.length > 1 ? j / (mine.length - 1) : 0));
            var tp = Loom.polarBezier([aE, rE], [aE, depth], [am, depth], [am, rimR], 2.5);
            S.twig[k] = Loom.polarXY(cx, cy, tp);
          });
        });
      });
      // Each link's whole route, end to end in its own direction: through
      // its sheaf's ribbon and its own fibre where it has one.
      var routes = model.links.map(function (l, k) {
        if (sheafOf[k] < 0) return bRoutes[bOf[k]];
        var S = sheaves[sheafOf[k]], whole = S.pts.concat(S.twig[k].slice(1));
        return { pts: S.role === 'out' ? whole : whole.slice().reverse(), local: false, pair: S.pair, lane: -1 };
      });
      var TAPER = {
        rest: Loom.taper({ start: 0.22 * ws, body: 0.95 * ws, end: 0.5 * ws, rise: 30 * s, fall: 22 * s, swell: 0.22 }),
        lit: Loom.taper({ start: 0.45 * ws, body: 1.85 * ws, end: 1.0 * ws, rise: 36 * s, fall: 26 * s, swell: 0.18 })
      };
      function widthOf(k, lit) {
        var base = lit ? TAPER.lit : TAPER.rest, f = KIND_WIDTH[model.links[k].kind] || 1;
        return f === 1 ? base : function (at, len) { return base(at, len) * f; };
      }
      /* What the fibre layer draws: a link's own fibre, a sheaf's ribbon or
         one of its parting fibres. A ribbon carrying n links is the square
         root of n fibres wide: it leaves its mark thin, is fullest in the
         bundle and is still broad where it parts; a parting fibre leaves the
         ribbon broad and meets its mark as a fibre does. */
      var items = [];
      model.links.forEach(function (l, k) {
        if (sheafOf[k] >= 0) return;
        items.push({ id: items.length, part: 'link', pts: routes[k].pts, kind: l.kind, local: !!routes[k].local, pair: routes[k].pair, links: [k], sheaf: -1 });
      });
      sheaves.forEach(function (S, si) {
        S.item = items.length;
        items.push({ id: items.length, part: 'trunk', pts: S.pts, kind: S.kind, local: false, pair: S.pair, links: S.links.slice(), sheaf: si });
        S.twigItem = Object.create(null);
        S.links.forEach(function (k) {
          S.twigItem[k] = items.length;
          items.push({ id: items.length, part: 'twig', pts: S.twig[k], kind: S.kind, local: false, pair: S.pair, links: [k], sheaf: si });
        });
      });
      var TRUNK = {
        out: Loom.taper({ start: 0.3, body: 1, end: 0.9, rise: 30 * s, fall: 8 * s, swell: 0.12 }),
        'in': Loom.taper({ start: 0.55, body: 1, end: 0.9, rise: 22 * s, fall: 8 * s, swell: 0.12 }),
        twigOut: Loom.taper({ start: 0.7, body: 0.72, end: 0.5, rise: 6 * s, fall: 14 * s, swell: 0 }),
        twigIn: Loom.taper({ start: 0.7, body: 0.72, end: 0.3, rise: 6 * s, fall: 14 * s, swell: 0 })
      };
      // n: how many links the ribbon carries in this drawing.
      function itemWidth(it, lit, n) {
        if (it.part === 'link') return widthOf(it.links[0], lit);
        var S = sheaves[it.sheaf], f = (KIND_WIDTH[it.kind] || 1) * (lit ? 1.85 : 0.95) * ws;
        if (it.part === 'trunk') {
          // At rest a ribbon is the square root of its links wide; lit, it
          // grows by the logarithm, so a choice's ribbons never stand
          // stronger than the marks and names they lead to (a ribbon of
          // twenty lit was four and a half fibres wide; it is now under
          // three).
          var nn = Math.max(1, n || S.links.length), g = lit ? 1 + 0.42 * Math.log(nn) / Math.LN2 : Math.sqrt(nn), tw = TRUNK[S.role];
          return function (at, len) { return tw(at, len) * f * g; };
        }
        var tt = S.role === 'out' ? TRUNK.twigOut : TRUNK.twigIn;
        return function (at, len) { return tt(at, len) * f; };
      }
      // A kind's texture, as cuts across its fibre: reading saved results is
      // dashed, checking copied files dotted, running another solid. Each
      // drawn piece carries its own whole pattern, so a ribbon reads as one.
      var texture = Object.create(null);
      // grow: how much longer the marks are (a ribbon's grow with its width,
      // so it reads as one long-dashed band, never a row of bricks); from:
      // how far the pattern starts along the piece (a parting fibre is whole
      // where it leaves its ribbon with the others).
      function textureOf(key, kind, pts, grow, from) {
        if (kind !== 'reads' && kind !== 'checks') return [];
        if (texture[key]) return texture[key];
        var cum = Loom.measure(pts), len = cum[cum.length - 1];
        grow = grow || 1; from = from || 0;
        var mark = (kind === 'reads' ? Math.max(5, 6.5 * ws) : Math.max(1.7, 2 * ws)) * grow;
        var gap = (kind === 'reads' ? Math.max(2.8, 3.4 * ws) : Math.max(2.6, 3 * ws)) * Math.sqrt(grow);
        var run = len - from, period = mark + gap, n = Math.max(0, Math.floor((run - mark) / period)), lead = from + (run - n * period - mark) / 2, out = [];
        // Whole marks from end to end, the pattern centred so both ends are ink.
        for (var i = 0; i < n; i++) {
          var at = lead + mark + i * period + gap / 2, p = Loom.pointAt(pts, at, cum);
          out.push({ s: at, x: p.x, y: p.y, nx: p.tx, ny: p.ty, h: gap / 2, sin: 1, cos: 0, over: -1 });
        }
        return (texture[key] = out);
      }
      function strokeOf(pts, kind, width, tex, cuts) {
        var all = tex;
        if (cuts && cuts.length) all = all.concat(cuts);
        return Loom.fibreStroke(pts, { width: width, cuts: all, step: 2, minPiece: kind === 'checks' ? 0.6 : 2.2 });
      }
      // A link drawn whole (lit alone): its full route.
      function fibreD(k, lit, cuts) {
        var pts = routes[k].pts, kind = model.links[k].kind;
        return strokeOf(pts, kind, widthOf(k, lit), textureOf('k' + k, kind, pts), cuts);
      }
      // A ribbon carries its kind's texture; its parting fibres are fine and
      // whole, so where they fan out to their marks they read as one brush.
      function itemTexture(it) {
        if (it.part === 'trunk') return textureOf('i' + it.id, it.kind, it.pts, Math.max(1, 0.85 * Math.sqrt(it.links.length)));
        return it.part === 'twig' ? [] : textureOf('i' + it.id, it.kind, it.pts);
      }
      function itemD(it, lit, cuts, n) { return strokeOf(it.pts, it.kind, itemWidth(it, lit, n), itemTexture(it), cuts); }
      /* At rest every code connection is drawn, quietly: where code actually
         runs code. A scene of hundreds of listed relations shows them only
         where a choice lights them. */
      var restEls = [], restCut = [], restDrawn = routes.length > 0 && model.links.length <= REST_MOST;
      if (restDrawn) items.forEach(function (it) {
        var attrs = { 'class': 'sm-fibre sm-fibre--' + (it.kind || 'named') + (it.local ? ' is-local' : '') + (it.part !== 'link' ? ' is-' + it.part : ''),
                      d: itemD(it, false, null) };
        if (it.part === 'trunk') {
          attrs['data-from'] = 'comp:' + model.comps[sheaves[it.sheaf].h].id;
          attrs['data-to'] = 'fam:' + model.families[sheaves[it.sheaf].fam].key;
          attrs['data-n'] = String(it.links.length);
        }
        var p = sv('path', attrs);
        gRest.appendChild(p);
        restEls[it.id] = p;
      });
      // What a set of lit links draws: a sheaf with two or more of them its
      // ribbon (as wide as those) and their parting fibres; a lone link its
      // whole route. Each piece knows the end its light starts from.
      function litDraws(xs) {
        var out = [], by = Object.create(null), order2 = [];
        xs.forEach(function (x) {
          var si = sheafOf[x.k];
          if (si < 0) { out.push({ t: 'link', x: x }); return; }
          if (!by[si]) { by[si] = []; order2.push(si); }
          by[si].push(x);
        });
        order2.forEach(function (si) {
          var g = by[si], S = sheaves[si];
          if (g.length < 2) { out.push({ t: 'link', x: g[0] }); return; }
          var fromHub = g[0].a === S.h;
          out.push({ t: 'trunk', si: si, xs: g, it: items[S.item], n: g.length, reverse: !fromHub });
          g.forEach(function (x) { out.push({ t: 'twig', si: si, x: x, it: items[S.twigItem[x.k]], reverse: !fromHub, after: fromHub }); });
        });
        return out;
      }
      // One lit piece as a path. A link's own fibre and a parting fibre are
      // wires (one for each lit link, from the end its light starts at); a
      // ribbon is drawn under them as the stretch they share.
      // Each lit piece also says what it carries, from the chosen end: its
      // kind, its direction and the family at its other end (a ribbon, of
      // its links), so a narrowing and a trace pick out exactly the
      // relations the panel names.
      function dirOf(x) { return x.l.kind === 'named' ? 'both' : x.l[0] === x.a ? 'out' : 'inc'; }
      function litPath(dr, cuts, cls, wire) {
        if (dr.t === 'trunk') {
          var S = sheaves[dr.si], hubKey = 'comp:' + model.comps[S.h].id, famKey = 'fam:' + model.families[S.fam].key;
          return sv('path', { 'class': cls + ' sm-route--' + S.kind + ' is-trunk', d: itemD(dr.it, true, cuts, dr.n),
            'data-from': dr.reverse ? famKey : hubKey, 'data-to': dr.reverse ? hubKey : famKey, 'data-n': String(dr.n),
            'data-kind': S.kind, 'data-dir': dirOf(dr.xs[0]), 'data-fam': model.families[S.fam].key });
        }
        var x = dr.x, kind = x.l.kind || 'named';
        return sv('path', { 'class': cls + (wire ? ' sm-wire' : '') + ' sm-route--' + kind + (dr.t === 'twig' ? ' is-twig' : routes[x.k].local ? ' is-local' : ''),
          d: dr.t === 'twig' ? itemD(dr.it, true, cuts) : fibreD(x.k, true, cuts),
          'data-from': 'comp:' + model.comps[x.a].id, 'data-to': 'comp:' + model.comps[x.b].id,
          'data-kind': kind, 'data-dir': dirOf(x), 'data-fam': model.families[model.comps[x.b].fam].key, 'data-k': String(x.k) });
      }
      // How lit pieces draw in: a lone link from its own end; a ribbon and
      // its parting fibres in turn, from the end the light starts at. The
      // light runs at one speed (about a pixel a millisecond), so it reaches
      // a near component before a far one, and every line is whole within
      // two thirds of a second.
      function speedDur(pts) { return clamp(Math.round(polyLen(pts)), 220, 640); }
      function revealItems(draws) {
        var wRed = 2 * 1.85 * ws * 1.3 * 1.2 + 3;
        return draws.map(function (dr) {
          if (dr.t === 'link') return { pts: routes[dr.x.k].pts, reverse: dr.x.a !== model.links[dr.x.k][0], w: wRed, dur: speedDur(routes[dr.x.k].pts) };
          var trunkDur = speedDur(sheaves[dr.si].pts), twigDur = 240;
          if (dr.t === 'trunk') return { pts: dr.it.pts, reverse: dr.reverse, w: wRed * Math.sqrt(dr.n), delay: dr.reverse ? Math.round(twigDur * 0.8) : 0, dur: trunkDur };
          return { pts: dr.it.pts, reverse: dr.reverse, w: wRed, delay: dr.after ? Math.round(trunkDur * 0.8) : 0, dur: twigDur };
        });
      }

      /* ---- Rule lines ---- */
      /* A rule a paper module cites is a fine azure line from the component's mark
         to the rule. To a rule within a seventh of the way round it bends in
         like a ray and lands along the rule's own radius, which the core
         keeps clear; to a rule further round it runs straight in and bends
         across the core, never behind the centre's name, and meets the rule
         from inside, turned off the rule's own lines. No line travels round
         the core. A glyph it passes stands over it, on its halo. */
      var rMark = R - markSize / 2 - 2;
      var rGate = coreOuter + Math.max(5, 7 * rs);
      var rayCache = Object.create(null);
      function dist(p, q) { return Math.sqrt((p[0] - q[0]) * (p[0] - q[0]) + (p[1] - q[1]) * (p[1] - q[1])); }
      // How many glyphs of the core, other than the given one, a run of
      // points passes over. A glyph far from the run's box is passed over
      // at once.
      var ruleIds = null;
      function glyphHits(pts, skip, pad) {
        if (!ruleIds) ruleIds = Object.keys(rule);
        var x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity, i;
        for (i = 0; i < pts.length; i++) {
          var p = pts[i];
          if (p[0] < x0) x0 = p[0];
          if (p[0] > x1) x1 = p[0];
          if (p[1] < y0) y0 = p[1];
          if (p[1] > y1) y1 = p[1];
        }
        var n = 0;
        for (var k = 0; k < ruleIds.length; k++) {
          if (ruleIds[k] === skip) continue;
          var q = rule[ruleIds[k]], room = q.half + pad, rr = room * room;
          if (q.x < x0 - room || q.x > x1 + room || q.y < y0 - room || q.y > y1 + room) continue;
          for (i = 0; i < pts.length; i++) {
            var dx = pts[i][0] - q.x, dy = pts[i][1] - q.y;
            if (dx * dx + dy * dy < rr) { n++; break; }
          }
        }
        return n;
      }
      function inLabel(pts, pad) {
        if (!labelBox) return false;
        pad = pad || 0;
        for (var i = 0; i < pts.length; i++) {
          if (pts[i][0] > labelBox.x0 - pad && pts[i][0] < labelBox.x1 + pad && pts[i][1] > labelBox.y0 - pad && pts[i][1] < labelBox.y1 + pad) return true;
        }
        return false;
      }
      function cubic(p0, p1, p2, p3, step) {
        var len = dist(p0, p1) + dist(p1, p2) + dist(p2, p3), n = clamp(Math.ceil(len / (step || 2)), 4, 600), out = [];
        for (var i = 0; i <= n; i++) {
          var t = i / n, u = 1 - t, b0 = u * u * u, b1 = 3 * u * u * t, b2 = 3 * u * t * t, b3 = t * t * t;
          out.push([b0 * p0[0] + b1 * p1[0] + b2 * p2[0] + b3 * p3[0], b0 * p0[1] + b1 * p1[1] + b2 * p2[1] + b3 * p3[1]]);
        }
        return out;
      }
      function radialRun(a, r0, r1) {
        var n = Math.max(1, Math.ceil(Math.abs(r1 - r0) / 2)), out = [];
        for (var i = 0; i <= n; i++) out.push(polar(cx, cy, r0 + (r1 - r0) * i / n, a));
        return out;
      }
      // A run of points cut where it comes within r of the point g.
      function trimTo(pts, g, r) {
        for (var i = pts.length - 1; i > 0; i--) {
          if (dist(pts[i - 1], g) >= r) {
            var a = pts[i - 1], b = pts[i], da = dist(a, g), db = dist(b, g), t = da === db ? 0 : (da - r) / (da - db);
            return pts.slice(0, i).concat([[a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]]);
          }
        }
        return pts;
      }
      // How much a run turns along its length, in radians.
      function turning(pts) {
        var t = 0, h0 = null;
        for (var i = 1; i < pts.length; i++) {
          var dx = pts[i][0] - pts[i - 1][0], dy = pts[i][1] - pts[i - 1][1];
          if (dx * dx + dy * dy < 0.01) continue;
          var h1 = Math.atan2(dy, dx);
          if (h0 !== null) t += Math.abs(turn(h0, h1));
          h0 = h1;
        }
        return t;
      }
      function nearRay(C, id) {
        var P = Loom.clearPort(core.glyphs, id, rGate, { cx: cx, cy: cy, clearance: 2.5 });
        var port = C.a + turn(C.a, P.port), rEnd = Math.max(rGate, P.r), k = rMark - rEnd;
        var pol = Loom.polarBezier([C.a, rMark], [C.a, rMark - 0.36 * k], [port, rEnd + 0.36 * k], [port, rEnd], 2);
        var pts = Loom.polarXY(cx, cy, pol);
        if (P.r < rEnd) pts = pts.concat(radialRun(port, rEnd, P.r).slice(1));
        return P.hook ? pts.concat(P.hook.slice(1)) : pts;
      }
      // A far ray: in from the mark along its radius, bending across the
      // core to meet the rule from inside, turned off the rule's own radius
      // (where its own lines run). Of a few ways in, the one that clears the
      // centre's name, passes fewest glyphs and bends least; failing a clear
      // way, it passes beside the name.
      function farRay(C, id) {
        var q = rule[id], G = [q.x, q.y];
        var P0 = polar(cx, cy, rMark, C.a), t0 = [-Math.cos(C.a), -Math.sin(C.a)], L = dist(P0, G);
        var ux = cx - q.x, uy = cy - q.y, ul = Math.sqrt(ux * ux + uy * uy) || 1;
        ux /= ul; uy /= ul;
        var best = null;
        // Each way in is judged on a coarse run, a point every six pixels
        // (each glyph's room and the name's box a pixel or so wider, so a
        // run that grazes one is never passed as clear); the way chosen is
        // drawn fine.
        function consider(make, extra) {
          var run = trimTo(make(6), G, q.half + 2);
          var cost = (inLabel(run, 3) ? 1e6 : 0) + glyphHits(run, id, 2.6) * 120 + turning(run) * 40 + polyLen(run) * 0.04 + (extra || 0);
          if (!best || cost < best.cost) best = { cost: cost, make: make };
        }
        [-72, -54, -36, 36, 54, 72].forEach(function (deg) {
          var an = deg * Math.PI / 180, c = Math.cos(an), sn = Math.sin(an);
          var d = [ux * c - uy * sn, ux * sn + uy * c];
          [0.3, 0.44].forEach(function (k1) {
            [0.28, 0.42].forEach(function (k2) {
              var c1 = [P0[0] + t0[0] * k1 * L, P0[1] + t0[1] * k1 * L], c2 = [G[0] + d[0] * k2 * L, G[1] + d[1] * k2 * L];
              consider(function (step) { return cubic(P0, c1, c2, G, step); });
            });
          });
        });
        if (best.cost >= 1e6 && labelBox) {
          // Straight across the centre: by way of a point beside its name.
          var bw = (labelBox.x1 - labelBox.x0) / 2 + 10, bh = (labelBox.y1 - labelBox.y0) / 2 + 10;
          [[cx - bw, cy], [cx + bw, cy], [cx, cy - bh], [cx, cy + bh]].forEach(function (V) {
            var dv = [G[0] - P0[0], G[1] - P0[1]], dl = Math.sqrt(dv[0] * dv[0] + dv[1] * dv[1]) || 1, k = 0.22 * L;
            dv = [dv[0] / dl, dv[1] / dl];
            consider(function (step) {
              var a1 = cubic(P0, [P0[0] + t0[0] * 0.3 * L, P0[1] + t0[1] * 0.3 * L], [V[0] - dv[0] * k, V[1] - dv[1] * k], V, step);
              var a2 = cubic(V, [V[0] + dv[0] * k, V[1] + dv[1] * k], [G[0] + (ux * 0.8 - uy * 0.6) * 0.2 * L, G[1] + (uy * 0.8 + ux * 0.6) * 0.2 * L], G, step);
              return a1.concat(a2.slice(1));
            }, 200);
          });
        }
        return trimTo(best.make(2), G, q.half + 2);
      }
      // From a component's mark to a rule; a rule's lines out to the rim are
      // the same lines, read from the other end.
      // Every rule line stops a few pixels short of its rule's glyph, so a
      // rule that sends forty lines out is still seen at their meeting
      // point, framed, and never buried in its own fan.
      function ray(ci, id) {
        var key = ci + '|' + id;
        if (!rayCache[key]) {
          var run = Math.abs(turn(comp[ci].a, rule[id].a)) <= NEAR ? nearRay(comp[ci], id) : farRay(comp[ci], id);
          rayCache[key] = trimTo(run, [rule[id].x, rule[id].y], rule[id].half + 6);
        }
        return rayCache[key];
      }

      /* ---- Every line the map draws is made here ---- */
      var route = {
        link: function (k) { return routes[k] ? routes[k].pts : []; },
        fibre: fibreD,
        ray: ray,
        span: function (key) { return spanEls[key] ? spanEls[key].pts : []; },
        d: function (pts) { return Loom.lineD(pts); }
      };

      /* ---- The scale round the rim ---- */
      // Per sector: a hairline base just outside the marks, one fine tick for
      // each component, the two ends turned up as a bracket. Outside it, each
      // component's bar: one step for each rule its paper module cites; a
      // crossbar caps it where a rule is enforced there, an open one where a
      // narrower part of a rule is checked.
      var tickEls = Object.create(null), scaleEls = [];
      order.forEach(function (fi) {
        var S = sectors[fi], F = model.families[fi];
        var g = sv('g', { 'class': 'sm-scale__sector', 'data-fam': F.key });
        scaleEls[fi] = g;
        var e0 = S.runFrom - pitch * 0.18, e1 = S.runTo + pitch * 0.18;
        g.appendChild(sv('path', { 'class': 'sm-tick sm-tick--base', d: 'M' + pt(polar(cx, cy, R + 9, e0)) +
          'A' + fx(R + 9) + ' ' + fx(R + 9) + ' 0 ' + (e1 - e0 > Math.PI ? 1 : 0) + ' 1 ' + pt(polar(cx, cy, R + 9, e1)) }));
        [e0, e1].forEach(function (a) {
          g.appendChild(sv('path', { 'class': 'sm-tick sm-tick--end', d: 'M' + pt(polar(cx, cy, R + 5, a)) + 'L' + pt(polar(cx, cy, R + 16, a)) }));
        });
        F.members.forEach(function (ci) {
          var C = comp[ci], c = model.comps[ci];
          var tk = sv('path', { 'class': 'sm-tick', 'data-sm-tick': c.id, d: 'M' + pt(polar(cx, cy, R + 9, C.a)) + 'L' + pt(polar(cx, cy, R + 13, C.a)) });
          g.appendChild(tk);
          tickEls[ci] = tk;
          if (C.bar > 0) {
            g.appendChild(sv('path', { 'class': 'sm-bar', d: 'M' + pt(polar(cx, cy, R + 16, C.a)) + 'L' + pt(polar(cx, cy, R + 16 + C.bar, C.a)) }));
          }
          if (C.enf) {
            var rr = R + 16 + C.bar + 2.2, half = 2.7 / rr, gap = 0.95 / rr;
            g.appendChild(sv('path', { 'class': 'sm-cap' + (C.enf === 'part' ? ' sm-cap--part' : ''), d: C.enf === 'full' ?
              'M' + pt(polar(cx, cy, rr, C.a - half)) + 'L' + pt(polar(cx, cy, rr, C.a + half)) :
              'M' + pt(polar(cx, cy, rr, C.a - half)) + 'L' + pt(polar(cx, cy, rr, C.a - gap)) + 'M' + pt(polar(cx, cy, rr, C.a + gap)) + 'L' + pt(polar(cx, cy, rr, C.a + half)) }));
          }
        });
        gScale.appendChild(g);
      });

      /* ---- The doctrine's own relations ---- */
      // The necklace's orbit, a guide in the ground's own line tone, as the
      // mathematics slide draws the orbit of its problems.
      var neck = null, spanEls = Object.create(null);
      if (core) {
        // Turned a quarter back, so its stroke begins at the top, as the
        // families' order does.
        neck = sv('circle', { 'class': 'sm-necklace', cx: fx(cx), cy: fx(cy), r: fx(hubR), transform: 'rotate(-90 ' + fx(cx) + ' ' + fx(cy) + ')' });
        gNeck.appendChild(neck);
        core.lines.forEach(function (ln) {
          var key = ln.from + '>' + ln.to;
          var p = sv('path', { 'class': 'sm-span sm-span--' + (ln.kind === 'failure' ? 'threat' : 'rest') + (ln.role === 'bridge' ? ' is-chord' : '') + ' sm-wire',
            d: Loom.lineD(ln.pts), 'data-from': 'rule:' + ln.from, 'data-to': 'rule:' + ln.to });
          gSpans.appendChild(p);
          spanEls[key] = { el: p, pts: ln.pts, item: ln.from, axiom: ln.to };
        });
      }

      /* A grid of boxes, for asking quickly whether a box would cover any of
         them: the names a zoom sets round the rim, the glyphs, the plates
         and the tags once placed. */
      function boxGrid(cell) {
        var cells = new Map(), all = [];
        function each(b, pad, fn) {
          var x0 = Math.floor((b.x0 - pad) / cell), x1 = Math.floor((b.x1 + pad) / cell);
          var y0 = Math.floor((b.y0 - pad) / cell), y1 = Math.floor((b.y1 + pad) / cell);
          for (var gx = x0; gx <= x1; gx++) for (var gy = y0; gy <= y1; gy++) if (fn(gx * 100003 + gy)) return true;
          return false;
        }
        return {
          all: all,
          add: function (b) {
            all.push(b);
            each(b, 0, function (key) { var l = cells.get(key); if (l) l.push(b); else cells.set(key, [b]); return false; });
          },
          hits: function (b, pad) {
            pad = pad || 0;
            return each(b, pad, function (key) {
              var l = cells.get(key);
              if (!l) return false;
              for (var i = 0; i < l.length; i++) {
                var q = l[i];
                if (b.x0 - pad < q.x1 && b.x1 + pad > q.x0 && b.y0 - pad < q.y1 && b.y1 + pad > q.y0) return true;
              }
              return false;
            });
          }
        };
      }

      // Whether a straight segment [x0, y0, x1, y1] passes over any box of a
      // grid, judged a few pixels at a time.
      function segmentHits(grid, s, pad) {
        var len = Math.hypot(s[2] - s[0], s[3] - s[1]), n = Math.max(1, Math.ceil(len / 5));
        for (var i = 0; i <= n; i++) {
          var x = s[0] + (s[2] - s[0]) * i / n, y = s[1] + (s[3] - s[1]) * i / n;
          if (grid.hits({ x0: x - 1, x1: x + 1, y0: y - 1, y1: y + 1 }, pad)) return true;
        }
        return false;
      }

      /* ---- Nodes: focusable, named, each with a target the size of its place ---- */
      var nodes = Object.create(null), nameBoxes = [], nameGrid = boxGrid(32), centreShown = false;
      function node(key, x, y, cls, label, hitR, haloR) {
        var g = sv('g', { 'class': 'sm-node ' + cls, 'data-sm-key': key, transform: 'translate(' + fx(x) + ' ' + fx(y) + ')',
          role: 'button', tabindex: '-1', 'aria-label': label });
        g.appendChild(sv('circle', { 'class': 'sm-hit', r: fx(hitR) }));
        if (haloR) g.appendChild(sv('circle', { 'class': 'sm-halo', r: fx(haloR) }));
        nodes[key] = g;
        return g;
      }
      function glyph(markup, z, extra) {
        var pop = sv('g', { 'class': 'sm-pop' });
        var mk = sv('g', { 'class': 'sm-mark' + (extra ? ' ' + extra : ''), transform: 'translate(' + fx(-z / 2) + ' ' + fx(-z / 2) + ') scale(' + fx(z / 12) + ')',
          fill: 'currentColor', stroke: 'currentColor', 'stroke-width': 0 });
        mk.innerHTML = markup;
        pop.appendChild(mk);
        return pop;
      }
      // A rule's glyph drawn at its own size: an axiom a ringed dot, a
      // principle a diamond, a failure mode a cross.
      function ruleGlyph(kind, z) {
        var pop = sv('g', { 'class': 'sm-pop' }), mk = sv('g', { 'class': 'sm-mark' });
        if (kind === 'axiom') {
          mk.appendChild(sv('circle', { 'class': 'sm-g sm-g--ring', r: fx(z / 2 - 0.8) }));
          mk.appendChild(sv('circle', { 'class': 'sm-g sm-g--dot', r: fx(Math.max(1.7, z * 0.17)) }));
        } else if (kind === 'principle') {
          var q = z / 2 - 0.5;
          mk.appendChild(sv('path', { 'class': 'sm-g sm-g--diamond', d: 'M0 ' + fx(-q) + 'L' + fx(q) + ' 0L0 ' + fx(q) + 'L' + fx(-q) + ' 0Z' }));
        } else {
          var e = z * 0.37;
          mk.appendChild(sv('path', { 'class': 'sm-g sm-g--cross', d: 'M' + fx(-e) + ' ' + fx(-e) + 'L' + fx(e) + ' ' + fx(e) + 'M' + fx(e) + ' ' + fx(-e) + 'L' + fx(-e) + ' ' + fx(e) }));
        }
        pop.appendChild(mk);
        return pop;
      }
      // The explorer's zoom names the components once their names stand
      // clear of one another round the rim (one name's height and a pixel
      // between neighbours), each only where it stands whole in view: never
      // cut by the stage's edge, never under its controls or its key.
      var namesClear = !!cam && cam.names === 'all' && pitchPx >= (cam.nameSize || 15) + 1;
      var namedComp = Object.create(null);
      function nameStands(C, label) {
        return spanStands(C.a, R + depth + 8, textWidth(label, 'sm-rimname sm-rimname--' + (cam.nameSize || 15)));
      }
      /* A zoomed component is named outward along its radius, past the
         rim's furniture, wherever its whole name stands in view, and nowhere
         else. A name set inward from the mark crossed every line on its way
         to the core and read as clutter (Will, 6 October 2026: "fix this
         ugliness"); a component whose name cannot stand outward waits for a
         closer look, the pointer, or its plate when it is lit. */
      var nameWay = Object.create(null);
      if (namesClear) model.comps.forEach(function (c, ci) {
        var C = comp[ci];
        if (C && C.x > 12 && C.x < width - 12 && C.y > 12 && C.y < size - 12 && nameStands(C, c.label)) nameWay[ci] = 'out';
      });
      // Whether a word set along the radius at angle a, from r0 for w pixels,
      // stands whole in view.
      function spanStands(a, r0, w) {
        var edge = 20;
        for (var f = 0; f <= 1.0001; f += 0.25) {
          var p = polar(cx, cy, r0 + w * f, a);
          if (p[0] < edge || p[0] > width - edge || p[1] < edge || p[1] > size - edge) return false;
          for (var q = 0; q < avoidRects.length; q++) {
            var A = avoidRects[q];
            if (p[0] > A.x0 - 8 && p[0] < A.x1 + 8 && p[1] > A.y0 - 10 && p[1] < A.y1 + 10) return false;
          }
        }
        return true;
      }
      model.comps.forEach(function (c, ci) {
        if (!comp[ci]) return;
        var C = comp[ci];
        var g = node('comp:' + c.id, C.x, C.y, 'sm-node--comp', c.label + ', ' + model.families[c.fam].title +
          (c.cls ? '; ' + lowerFirst(CLASS_WORDS[c.cls]) : '') + '. Select to light its links and rules.', Math.max(6, pitchPx / 2), markSize / 2 + 1.6);
        g.__ci = ci;
        g.appendChild(glyph(GLYPHS[c.cls] || GLYPHS.none, markSize));
        g.appendChild(sv('circle', { 'class': 'sm-focus-ring', r: fx(markSize / 2 + 3.5) }));
        // A family looked at closely names each of its components along its
        // radius, just outside the rim's furniture; so does the explorer's
        // zoom, every name that stands whole in view, and where a name would
        // run out of view it reads inward from the mark instead, over the
        // lines, on a halo of the ground, never into the doctrine.
        var way = !cam ? null : cam.names === c.fam ? 'out' : cam.names === 'all' ? nameWay[ci] || null : null;
        if (way) {
          var dg = C.a * 180 / Math.PI, rt = Math.cos(C.a) >= 0, nsz = 'sm-rimname--' + (cam.nameSize || 15);
          var out = depth + 8;
          var nw = textWidth(c.label, 'sm-rimname ' + nsz);
          namedComp[ci] = true;
          var tn = sv('text', { 'class': 'sm-rimname ' + nsz + ' sm-rimname--cam sm-note',
            'dominant-baseline': 'central', 'text-anchor': rt ? 'start' : 'end',
            transform: 'rotate(' + fx(rt ? dg : dg + 180) + ') translate(' + fx(rt ? out : -out) + ' 0)' });
          tn.textContent = c.label;
          g.appendChild(tn);
          for (var along = 0; along <= nw; along += 8) {
            var np = polar(cx, cy, R + out + along, C.a), nb = { x0: np[0] - 8, x1: np[0] + 8, y0: np[1] - 9, y1: np[1] + 9 };
            nameBoxes.push(nb);
            nameGrid.add(nb);
          }
        }
        g.addEventListener('click', function (e) { press(e, 'comp:' + c.id, function (how) { goComponent(ci, how); }); });
        hoverable(g, 'comp:' + c.id, g);
        gRim.appendChild(g);
      });
      if (D && core) {
        Object.keys(rule).forEach(function (id) {
          var r = D.rules[id], q = rule[id];
          var g = node('rule:' + id, q.x, q.y, 'sm-node--rule sm-node--' + q.kind + ' sm-node--' + (q.role === 'satellite' ? 'sat' : q.role),
            KIND_WORDS[q.kind] + ': ' + r.title + '. Select to light where it reaches.', Math.max(7.5, q.half + 2.5), q.half + 2.2);
          g.appendChild(ruleGlyph(q.kind, q.size));
          g.appendChild(sv('circle', { 'class': 'sm-focus-ring', r: fx(q.half + 3.5) }));
          g.addEventListener('click', function (e) { press(e, 'rule:' + id, function (how) { goDoctrine(id, how); }); });
          hoverable(g, 'rule:' + id, g);
          gCore.appendChild(g);
        });
      }
      if (D) {
        // The centre: the doctrine's name, which opens it.
        var cg = node('doctrine', cx, cy, 'sm-node--centre', 'The doctrine: ' + countWords(D.axioms.length, 'axiom', 'axioms') + ', ' +
          countWords(D.principles.length, 'principle', 'principles') + ' and ' + countWords(D.failures.length, 'failure mode', 'failure modes') +
          '. Select to light them all.', Math.max(14, centreClear - 4));
        cg.setAttribute('tabindex', '0');
        var ct = sv('text', { 'class': 'sm-centre__label sm-label', x: 0, y: 0, 'text-anchor': 'middle', 'dominant-baseline': 'central' });
        ct.textContent = 'Doctrine';
        var cpop = sv('g', { 'class': 'sm-pop' });
        // Under a camera the centre's name is set only where it stands whole.
        if (!cam || (labelBox && labelBox.x0 >= 18 && labelBox.x1 <= width - 18 && labelBox.y0 >= 18 && labelBox.y1 <= size - 18 &&
            !avoidRects.some(function (A) { return labelBox.x0 < A.x1 + 6 && labelBox.x1 > A.x0 - 6 && labelBox.y0 < A.y1 + 6 && labelBox.y1 > A.y0 - 6; }))) {
          cpop.appendChild(ct);
          centreShown = true;
        }
        cg.appendChild(cpop);
        cg.appendChild(sv('circle', { 'class': 'sm-focus-ring', r: fx(Math.max(14, centreClear - 4)) }));
        cg.addEventListener('click', function (e) { press(e, 'doctrine', function (how) { goDoctrine(null, how); }); });
        hoverable(cg, 'doctrine', cg);
        gCore.appendChild(cg);
      }

      /* ---- The sector names, set along the outside of the ring ---- */
      var labelBoxes = [];   // per family: sample boxes along both rows, for the plates to keep clear of
      // A family's name set along the radius at angle a from radius r, its
      // count after it, reading outward like the components' names it heads.
      function head(fi, a, r) {
        var F = model.families[fi];
        var right = Math.cos(a) >= 0, deg = a * 180 / Math.PI;
        var g = sv('g', { 'class': 'sm-node sm-node--fam sm-node--head', 'data-sm-key': 'fam:' + F.key, role: 'button', tabindex: '0',
          'aria-label': F.title + ': ' + countLine(F) + '. Select to light the family.',
          transform: 'translate(' + pt(polar(cx, cy, r, a)) + ') rotate(' + fx(right ? deg : deg + 180) + ')' });
        var tw = textWidth(F.title, 'sm-sector__name'), cw = textWidth(countLine(F), 'sm-sector__count');
        var x0 = right ? 0 : -(tw + 10 + cw);
        g.appendChild(sv('rect', { 'class': 'sm-hit', x: fx(x0 - 4), y: -12, width: fx(tw + cw + 18), height: 24 }));
        var t1 = sv('text', { 'class': 'sm-sector__name sm-label', x: fx(right ? 0 : -(cw + 10)), y: 0, 'text-anchor': right ? 'start' : 'end', 'dominant-baseline': 'central' });
        t1.textContent = F.title;
        var t2 = sv('text', { 'class': 'sm-sector__count sm-note', x: fx(right ? tw + 10 : 0), y: 0, 'text-anchor': right ? 'start' : 'end', 'dominant-baseline': 'central' });
        t2.textContent = countLine(F);
        g.appendChild(t1);
        g.appendChild(t2);
        g.appendChild(sv('rect', { 'class': 'sm-focus-box', x: fx(x0 - 5), y: -13, width: fx(tw + cw + 20), height: 26, rx: 4 }));
        g.addEventListener('click', function (e) { press(e, 'fam:' + F.key, function (how) { goFamily(fi, how); }); });
        hoverable(g, 'fam:' + F.key, g);
        gLabels.appendChild(g);
        nodes['fam:' + F.key] = g;
        labelBoxes[fi] = { g: g, boxes: [] };
      }
      // Where a family's two rows of words will stand, before any is set.
      function labelGeom(fi) {
        var S = sectors[fi], F = model.families[fi], lower = readsDownward(S.mid);
        var rows = lower ? [[F.title, 'sm-sector__name', labelR1], [countLine(F), 'sm-sector__count', labelR2]] :
          [[countLine(F), 'sm-sector__count', labelR1], [F.title, 'sm-sector__name', labelR2]];
        var samples = [], widths = [];
        rows.forEach(function (row) {
          var w = textWidth(row[0], row[1]), half = (w / 2 + 4) / row[2];
          widths.push(w);
          for (var a = S.mid - half; a <= S.mid + half + 1e-9; a += 7 / row[2]) {
            var p = polar(cx, cy, row[2], a);
            samples.push({ x0: p[0] - 8, x1: p[0] + 8, y0: p[1] - 9, y1: p[1] + 9 });
          }
        });
        // Crowded, a name stands only within its own family's arc.
        var ownArc = !crowded || rows.every(function (row, j) { return (widths[j] / 2 + 6) / row[2] <= (S.hi - S.lo + gapA) / 2; });
        return { lower: lower, rows: rows, widths: widths, samples: samples, ownArc: ownArc };
      }
      function standsWhole(q) {
        return !(q.x0 < 18 || q.x1 > width - 18 || q.y0 < 18 || q.y1 > size - 18 ||
          nameBoxes.some(function (b) { return q.x0 < b.x1 && q.x1 > b.x0 && q.y0 < b.y1 && q.y1 > b.y0; }) ||
          avoidRects.some(function (b) { return q.x0 < b.x1 && q.x1 > b.x0 && q.y0 < b.y1 && q.y1 > b.y0; }));
      }
      // Crowded, the families are named round the outside all together or
      // not at all (a lone name would look chosen); the panel names them.
      var crowdNamed = !crowded || cam || order.every(function (fi) {
        var L = labelGeom(fi);
        return L.ownArc && L.samples.every(standsWhole);
      });
      order.forEach(function (fi, k) {
        var S = sectors[fi], F = model.families[fi];
        // Under a camera a family's name is set only where it stands whole
        // on the drawing and clear of the names a closer look gives a
        // family's components, never cut by the drawing's edge; the family
        // looked at is named by the trail and by its components' own names.
        var L = labelGeom(fi), lower = L.lower, rows = L.rows, widths = L.widths, samples = L.samples;
        if (!crowdNamed || !L.ownArc || ((cam || crowded) && ((cam && cam.names === fi) || !samples.every(standsWhole)))) return;
        var g = sv('g', { 'class': 'sm-node sm-node--fam', 'data-sm-key': 'fam:' + F.key, role: 'button', tabindex: '0',
          'aria-label': F.title + ': ' + countLine(F) + '. Select to light the family.' });
        var spanHit = Math.max(S.hi - S.lo, (labelW[fi] + 26) / labelR1);
        g.appendChild(sv('path', { 'class': 'sm-hit sm-hit--band', d: arcFor(cx, cy, (labelR1 + labelR2) / 2, S.mid, spanHit, lower), 'stroke-width': 40 }));
        rows.forEach(function (row, j) {
          var id = 'sm-arc-' + mounted + '-' + (++arcN) + '-' + k + '-' + j, w = widths[j];
          var span = Math.min(TAU * 0.45, (w + 60) / row[2]);
          defs.appendChild(sv('path', { id: id, d: arcFor(cx, cy, row[2], S.mid, span, lower) }));
          var t = sv('text', { 'class': row[1] + (row[1] === 'sm-sector__name' ? ' sm-label' : ' sm-note'), 'dominant-baseline': 'central' });
          var tp = sv('textPath', { href: '#' + id, startOffset: '50%', 'text-anchor': 'middle' });
          if (tp.setAttributeNS) tp.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', '#' + id);
          tp.textContent = row[0];
          t.appendChild(tp);
          g.appendChild(t);
        });
        g.appendChild(sv('path', { 'class': 'sm-focus-band', d: arcFor(cx, cy, (labelR1 + labelR2) / 2, S.mid, spanHit, lower), 'stroke-width': 42 }));
        g.addEventListener('click', function (e) { press(e, 'fam:' + F.key, function (how) { goFamily(fi, how); }); });
        hoverable(g, 'fam:' + F.key, g);
        gLabels.appendChild(g);
        nodes['fam:' + F.key] = g;
        labelBoxes[fi] = { g: g, boxes: samples };
      });
      // Close enough for the components' names, a family whose name round
      // the outside gave way to them is named the same way they are: along
      // the radius in the gap before its run, where it stands whole.
      if (cam && (cam.names === 'all' || typeof cam.names === 'number')) order.forEach(function (fi, k) {
        if (labelBoxes[fi]) return;
        var F = model.families[fi];
        if (!F.members.some(function (ci) { return namedComp[ci]; })) return;
        var S = sectors[fi], P = sectors[order[(k - 1 + nF) % nF]];
        var gapAng = norm(S.runFrom - P.runTo), a = S.runFrom - Math.min(gapAng / 2, (pitch * 1.6));
        if (gapAng * R < 22) return;
        var w = textWidth(F.title, 'sm-sector__name') + 10 + textWidth(countLine(F), 'sm-sector__count');
        if (!spanStands(a, R + depth + 8, w)) return;
        head(fi, a, R + depth + 8);
      });
      // An empty click steps back a level; the second click of a double
      // click that lands on empty ground (the mark may have moved under it)
      // still opens what the first one chose.
      svg.addEventListener('click', function (e) {
        if (e && e.detail >= 2 && lastPress && nowMs() - lastPress.at < 700) { openPage(lastPress.key, e); return; }
        if (at.level !== 'system') up({});
      });

      /* ---- Light ---- */
      /* What a view lights, each relation with the direction its light runs:
         from a component inward to the rules its paper module cites and on to
         the axioms they rest on, and out along its connections; from a rule
         outward through its relations to every component whose paper module
         cites it, and to the components where it is shown enforced (framed)
         or a narrower part of it checked (an open frame). */
      function lightOf(s) {
        var L = { comps: Object.create(null), rules: Object.create(null), links: [], cites: [], spans: Object.create(null),
                  reticles: [], open: [], plates: [], families: Object.create(null), rim: false, core: false };
        if (!s || s.level === 'system') return L;
        if (s.level === 'family') {
          L.rim = true; L.core = !!D;
          L.families[s.fam] = 'self';
          model.families[s.fam].members.forEach(function (ci) { L.comps[ci] = 'member'; });
          model.links.forEach(function (l, k) {
            var fa = model.comps[l[0]].fam, fb = model.comps[l[1]].fam;
            if (fa !== s.fam && fb !== s.fam) return;
            var from = fa === s.fam ? l[0] : l[1], to = from === l[0] ? l[1] : l[0];
            L.links.push({ a: from, b: to, l: l, k: k });
            if (!L.comps[to]) { L.comps[to] = 'link'; L.families[model.comps[to].fam] = L.families[model.comps[to].fam] || 'link'; }
          });
          return L;
        }
        if (s.level === 'component') {
          var ci = s.comp, c = model.comps[ci];
          L.rim = true; L.core = !!D;
          L.comps[ci] = 'self';
          L.families[c.fam] = 'self';
          L.reticles.push('comp:' + c.id);
          L.plates.push(ci);
          var seen = Object.create(null);
          model.links.forEach(function (l, k) {
            if (l[0] !== ci && l[1] !== ci) return;
            var other = l[0] === ci ? l[1] : l[0];
            L.links.push({ a: ci, b: other, l: l, k: k });
            L.comps[other] = 'link';
            seen[other] = true;
          });
          // Names: the components in other families first, then its own, nearest first.
          Object.keys(seen).map(Number).sort(function (p, q) {
            var fp = model.comps[p].fam === c.fam ? 1 : 0, fq = model.comps[q].fam === c.fam ? 1 : 0;
            return fp - fq || Math.abs(turn(comp[ci].a, comp[p].a)) - Math.abs(turn(comp[ci].a, comp[q].a));
          }).forEach(function (x) { L.plates.push(x); });
          if (D) {
            var info = D.comp[ci], reached = Object.create(null);
            info.gov.forEach(function (pid) {
              if (!rule[pid]) return;
              L.rules[pid] = 'lit';
              L.cites.push({ ci: ci, id: pid, out: false });
              D.rules[pid].restsOn.forEach(function (aid) {
                if (!rule[aid]) return;
                L.rules[aid] = L.rules[aid] || 'lit';
                reached[aid] = true;
                L.spans[pid + '>' + aid] = { from: pid, stage: 1 };
              });
            });
            info.abide.forEach(function (aid) {
              if (reached[aid] || !rule[aid]) return;
              L.rules[aid] = 'lit';
              L.cites.push({ ci: ci, id: aid, out: false });
            });
            // Where a test shows a rule holding in this component, its glyph
            // is framed, as the component is framed in that rule's own view:
            // four corners where the rule is enforced here, two where a part
            // of it is checked. A rule its paper module does not cite is lit
            // and framed with no line, since a line is a citation.
            info.enforces.forEach(function (id) {
              if (!rule[id]) return;
              L.rules[id] = L.rules[id] || 'lit';
              L.reticles.push('rule:' + id);
            });
            info.partly.forEach(function (id) {
              if (!rule[id] || info.enforces.indexOf(id) >= 0) return;
              L.rules[id] = L.rules[id] || 'lit';
              L.open.push('rule:' + id);
            });
          }
          return L;
        }
        if (!D) return L;
        if (s.level === 'doctrine') {
          L.rim = true;
          Object.keys(rule).forEach(function (id) { L.rules[id] = 'lit'; });
          Object.keys(spanEls).forEach(function (k) { L.spans[k] = { from: spanEls[k].axiom, stage: 0 }; });
          return L;
        }
        var r = D.rules[s.rule];
        L.rim = true; L.core = true;
        L.rules[s.rule] = 'self';
        L.reticles.push('rule:' + s.rule);
        Object.keys(spanEls).forEach(function (k) {
          var sp = spanEls[k];
          if (sp.item !== s.rule && sp.axiom !== s.rule) return;
          L.spans[k] = { from: s.rule, stage: 0 };
          var other = sp.item === s.rule ? sp.axiom : sp.item;
          L.rules[other] = L.rules[other] || 'lit';
        });
        if (!rule[s.rule]) return L;
        D.comp.forEach(function (info, ci) {
          var cites = r.kind === 'principle' ? info.gov.indexOf(s.rule) >= 0 : r.kind === 'axiom' ? info.abide.indexOf(s.rule) >= 0 : false;
          if (cites && comp[ci]) { L.comps[ci] = 'cite'; L.cites.push({ ci: ci, id: s.rule, out: true }); }
        });
        r.enforced.forEach(function (ci) {
          if (!comp[ci]) return;
          if (!L.comps[ci]) L.cites.push({ ci: ci, id: s.rule, out: true });
          L.comps[ci] = 'enforce';
          L.reticles.push('comp:' + model.comps[ci].id);
          L.plates.push(ci);
        });
        r.partly.forEach(function (ci) {
          if (!comp[ci] || L.comps[ci] === 'enforce') return;
          if (!L.comps[ci]) L.cites.push({ ci: ci, id: s.rule, out: true });
          L.comps[ci] = 'partly';
          L.open.push('comp:' + model.comps[ci].id);
          L.plates.push(ci);
        });
        return L;
      }

      /* ---- Motion ---- */
      /* A lit line appears from the end its light starts at, once, in about
         seven tenths of a second. The fibres are filled shapes, so they show
         through a mask whose stroke runs along their centre lines; a mask is
         removed the moment its lines are whole. Reduced motion shows them at
         once. */
      var reveals = [];
      function polyLen(pts) { var n = 0; for (var i = 1; i < pts.length; i++) n += dist(pts[i - 1], pts[i]); return n; }
      function revealAlong(group, items, delay, dur) {
        if (!items.length || !motionOK() || !group.setAttribute) return;
        var id = 'sm-reveal-' + mounted + '-' + (++revealN);
        var mask = sv('mask', { id: id, maskUnits: 'userSpaceOnUse', x: 0, y: 0, width: fx(width), height: size });
        var rec = { group: group, mask: mask, anims: [], left: items.length };
        defs.appendChild(mask);
        group.setAttribute('mask', 'url(#' + id + ')');
        reveals.push(rec);
        items.forEach(function (it) {
          var pts = it.reverse ? it.pts.slice().reverse() : it.pts, len = polyLen(pts) + 4;
          var p = sv('path', { d: Loom.lineD(pts), fill: 'none', stroke: '#fff', 'stroke-width': fx(it.w), 'stroke-linecap': 'round',
            'stroke-linejoin': 'round', 'stroke-dasharray': fx(len) + ' ' + fx(len), 'stroke-dashoffset': fx(len) });
          mask.appendChild(p);
          var an = null;
          try {
            an = p.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: it.dur || dur, delay: delay + (it.delay || 0), easing: EASE, fill: 'forwards' });
          } catch (e) { an = null; }
          if (an) { rec.anims.push(an); an.onfinish = function () { if (--rec.left <= 0) unmask(rec); }; }
          else if (--rec.left <= 0) unmask(rec);
        });
      }
      /* The light that runs. As a lit line draws in from the end its light
         starts at, a short brighter stretch rides its front and is gone at
         the far end, and the mark it reaches answers once with a ring that
         closes on it: the relation is seen to travel from what is chosen to
         what it touches. Then nothing moves. */
      var HEAD = 22;
      function runLight(items, ink, delay, dur) {
        if (!items.length || !motionOK()) return;
        items.forEach(function (it) {
          var pts = it.reverse ? it.pts.slice().reverse() : it.pts, len = polyLen(pts);
          if (!(len > HEAD * 1.5)) return;
          var p = sv('path', { 'class': 'sm-head sm-head--' + ink, d: Loom.lineD(pts), 'stroke-width': fx(it.hw || 1.8),
            'stroke-dasharray': HEAD + ' ' + fx(len + HEAD), 'stroke-dashoffset': HEAD });
          gFx.appendChild(p);
          var an = null;
          try {
            an = p.animate([{ strokeDashoffset: HEAD, opacity: 0 }, { opacity: 1, offset: 0.05 }, { opacity: 0.95, offset: 0.8 }, { strokeDashoffset: HEAD - len, opacity: 0 }],
              { duration: it.dur || dur, delay: delay + (it.delay || 0), easing: EASE, fill: 'both' });
          } catch (e) { an = null; }
          if (an) an.onfinish = function () { if (p.parentNode) p.parentNode.removeChild(p); };
          else if (p.parentNode) p.parentNode.removeChild(p);
        });
      }
      function answer(x, y, r, ink, when) {
        if (!motionOK()) return;
        var c = sv('circle', { 'class': 'sm-answer sm-answer--' + ink, cx: fx(x), cy: fx(y), r: fx(r) });
        gFx.appendChild(c);
        var an = null;
        try {
          an = c.animate([{ opacity: 0, transform: 'scale(1.7)' }, { opacity: 0.7, offset: 0.35 }, { opacity: 0, transform: 'scale(1)' }],
            { duration: 380, delay: Math.max(0, when), easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)', fill: 'both' });
        } catch (e) { an = null; }
        if (an) an.onfinish = function () { if (c.parentNode) c.parentNode.removeChild(c); };
        else if (c.parentNode) c.parentNode.removeChild(c);
      }
      function unmask(rec) {
        if (rec.group.getAttribute && rec.group.getAttribute('mask') === 'url(#' + rec.mask.getAttribute('id') + ')') rec.group.removeAttribute('mask');
        if (rec.mask.parentNode) rec.mask.parentNode.removeChild(rec.mask);
        var i = reveals.indexOf(rec);
        if (i >= 0) reveals.splice(i, 1);
      }
      function stopReveals(group) {
        reveals.slice().forEach(function (rec) {
          if (group && rec.group !== group) return;
          rec.anims.forEach(function (an) { try { an.cancel(); } catch (e) {} });
          unmask(rec);
        });
      }
      // A stroked line (a span of the doctrine) draws in from its start.
      function drawIn(p, delay, dur) {
        if (!motionOK() || !p.getTotalLength || !p.animate) return;
        var len = p.getTotalLength();
        if (!(len > 1)) return;
        try {
          p.animate([{ strokeDasharray: len + ' ' + len, strokeDashoffset: len }, { strokeDasharray: len + ' ' + len, strokeDashoffset: 0 }],
            { duration: dur, delay: delay, easing: EASE, fill: 'backwards' });
        } catch (e) {}
      }
      function fadeIn(elx, delay, dur) {
        if (!motionOK() || !elx.animate) return;
        try { elx.animate([{ opacity: 0 }, { opacity: 1 }], { duration: dur, delay: delay || 0, easing: EASE, fill: 'backwards' }); } catch (e) {}
      }

      /* ---- The weave ---- */
      /* Wherever a lit red line and an azure one cross, one passes over and
         the line beneath is cut by a clean gap parallel to it, alternating
         along each line as in a plait; a lit line always passes over a stray
         fibre. Woven again for every choice, since what is lit changes. */
      // The clearance is wide enough that a crossing reads as over and under
      // from a reader's distance (judged at two thirds size on a large
      // screen), and no wider, so no line looks broken.
      var WEAVE = { rankTolerance: 0, clearance: Math.max(2.6, 3.2 * rs), minAngle: 16, endGuard: 10 * s, cell: 28,
                    ropeMin: 4, ropeGap: 4 * s, ropeWidth: 10 * s };
      var woven = null;

      /* ---- Choosing ---- */
      var lit = lightOf(null), litPaths = [];
      function select(s, how) {
        how = how || {};
        var L = lightOf(s);
        stopReveals();
        clear(gLitRed);
        clear(gLitAz);
        clear(gMarks);
        clear(gPlates);
        litPaths = [];
        svg.classList.toggle('is-selecting', s.level !== 'system');
        svg.classList.toggle('is-doctrine', s.level === 'doctrine');
        svg.classList.toggle('is-rule', s.level === 'rule');
        svg.classList.toggle('dims-rim', !!L.rim);
        svg.classList.toggle('dims-core', !!L.core);
        Object.keys(nodes).forEach(function (key) {
          var n = nodes[key], state = null;
          if (key.indexOf('comp:') === 0) state = L.comps[n.__ci] || null;
          else if (key.indexOf('rule:') === 0) state = L.rules[key.slice(5)] || null;
          else if (key.indexOf('fam:') === 0) state = L.families[familyIndex(key.slice(4))] || null;
          ['is-self', 'is-lit', 'is-member', 'is-link', 'is-cite', 'is-enforce', 'is-partly'].forEach(function (c) { n.classList.remove(c); });
          if (state === 'self') n.classList.add('is-self');
          else if (state) { n.classList.add('is-lit'); n.classList.add('is-' + state); }
        });
        if (nodes.doctrine) nodes.doctrine.classList.toggle('is-self', s.level === 'doctrine');
        Object.keys(tickEls).forEach(function (ci) { tickEls[ci].classList.toggle('is-lit', !!L.comps[ci]); });
        // A family chosen keeps its identity on the rim: its scale in its ink.
        scaleEls.forEach(function (g, fi) { if (g) g.classList.toggle('is-self', s.level === 'family' && s.fam === fi); });
        Object.keys(spanEls).forEach(function (k) { spanEls[k].el.classList.toggle('is-lit', !!L.spans[k]); });
        var moving = !how.instant && !how.keyed && motionOK();
        // The azure lines, each from the end its light starts at.
        var az = L.cites.map(function (x) {
          var pts = ray(x.ci, x.id), c = Loom.coarse(pts);
          return { x: x, pts: x.out ? pts.slice().reverse() : pts, wpts: x.out ? c.slice().reverse() : c };
        });
        // The weave: every lit line, and the fibres at rest beneath them.
        var litK = Object.create(null), strands = [], refs = [], draws = litDraws(L.links);
        L.links.forEach(function (x) { litK[x.k] = true; });
        draws.forEach(function (dr) {
          var pts = dr.t === 'link' ? routes[dr.x.k].pts : dr.it.pts, pair = dr.t === 'link' ? routes[dr.x.k].pair : dr.it.pair;
          var w = dr.t === 'link' ? widthOf(dr.x.k, true) : itemWidth(dr.it, true, dr.n);
          strands.push({ pts: Loom.coarse(pts), ink: 'red', rank: 1, width: w, bundle: pair >= 0 ? 'pair' + pair : null });
          refs.push({ t: 'lit', dr: dr });
        });
        // A piece at rest is lit when every link it carries is.
        var litItem = function (it) { return it.links.every(function (k) { return !!litK[k]; }); };
        if (restDrawn && az.length) items.forEach(function (it) {
          if (litItem(it)) return;
          strands.push({ pts: Loom.coarse(it.pts), ink: 'red', rank: 0, width: itemWidth(it, false), bundle: it.pair >= 0 ? 'pair' + it.pair : null });
          refs.push({ t: 'rest', it: it });
        });
        az.forEach(function (a) {
          strands.push({ pts: a.wpts, ink: 'azure', rank: 1, width: +AZ_W, bundle: s.level === 'component' ? 'fan' : null });
          refs.push({ t: 'az', a: a });
        });
        woven = az.length && strands.length > az.length ? Loom.weave(strands, WEAVE) : null;
        var cutRest = Object.create(null);
        refs.forEach(function (ref, i) {
          var cuts = woven ? woven.cuts[i] : null;
          if (ref.t === 'rest') {
            if (cuts && cuts.length) { restEls[ref.it.id].setAttribute('d', itemD(ref.it, false, cuts)); cutRest[ref.it.id] = true; }
          } else if (ref.t === 'lit') {
            var p = litPath(ref.dr, cuts, 'sm-route', true);
            gLitRed.appendChild(p);
            litPaths.push({ el: p, pts: ref.dr.t === 'link' ? routes[ref.dr.x.k].pts : ref.dr.it.pts, ink: 'red' });
          } else {
            var a = ref.a;
            var q = sv('path', { 'class': 'sm-rline sm-wire', d: cuts && cuts.length ? Loom.strokeGaps(a.pts, cuts, +AZ_W) : Loom.lineD(a.pts),
              'data-from': a.x.out ? 'rule:' + a.x.id : 'comp:' + model.comps[a.x.ci].id, 'data-to': a.x.out ? 'comp:' + model.comps[a.x.ci].id : 'rule:' + a.x.id });
            gLitAz.appendChild(q);
            litPaths.push({ el: q, pts: a.pts, ink: 'azure' });
          }
        });
        // Fibres at rest: those cut last time and not this time are whole
        // again, and a piece whose every link is lit steps under its light.
        restEls.forEach(function (p, id) {
          if (!p) return;
          if (restCut[id] && !cutRest[id]) p.setAttribute('d', itemD(items[id], false, null));
          restCut[id] = !!cutRest[id];
          p.classList.toggle('is-under', litItem(items[id]));
        });
        // later: how long a camera move keeps the new view out of sight
        // before its light can be seen to run.
        var later = how.later || 0, arrive = Object.create(null);
        clear(gFx);
        if (moving) {
          var redItems = revealItems(draws), azItems = az.map(function (a) { return { pts: a.pts, w: +AZ_W + 4, dur: speedDur(a.pts), hw: +AZ_W + 0.7 }; });
          revealAlong(gLitRed, redItems, 40 + later, 720);
          revealAlong(gLitAz, azItems, 60 + later, 760);
          runLight(redItems.map(function (it) { return { pts: it.pts, reverse: it.reverse, delay: it.delay, dur: it.dur, hw: 2.2 }; }), 'red', 40 + later, 720);
          runLight(azItems, 'azure', 60 + later, 760);
          Object.keys(L.spans).forEach(function (k) {
            var sp = spanEls[k], sl = L.spans[k];
            if (sp) drawIn(sp.el, (sl.stage ? 520 : 40) + later, 460);
          });
          // A name arrives as the light reaches its component.
          L.links.forEach(function (x) { arrive[x.b] = Math.min(arrive[x.b] || Infinity, 40 + later + Math.round(speedDur(routes[x.k].pts) * 0.85)); });
          az.forEach(function (a) { if (a.x.out) arrive[a.x.ci] = Math.min(arrive[a.x.ci] || Infinity, 60 + later + Math.round(speedDur(a.pts) * 0.85)); });
          // And where the light reaches a mark the view names, the mark
          // answers once: a component named on a plate, a rule a
          // component's paper module cites. A rule cited by forty
          // components answers only where it is named, never round the rim.
          var answers = [];
          L.plates.forEach(function (ci, rank) {
            var C = comp[ci];
            if (!C || rank === 0 && s.level === 'component' || arrive[ci] === undefined) return;
            answers.push({ x: C.x, y: C.y, r: markSize / 2 + 2.5, ink: s.level === 'rule' ? 'azure' : 'red', when: arrive[ci] + 40 });
          });
          if (s.level === 'component') az.forEach(function (a) {
            if (a.x.out || !rule[a.x.id]) return;
            var q = rule[a.x.id];
            answers.push({ x: q.x, y: q.y, r: q.half + 2.5, ink: 'azure', when: 60 + later + speedDur(a.pts) });
          });
          answers.sort(function (p, q) { return p.when - q.when; }).slice(0, 12).forEach(function (w) { answer(w.x, w.y, w.r, w.ink, w.when); });
        }
        // Frames round neighbouring marks share the room between them.
        var framed = L.reticles.concat(L.open).filter(function (key) { return key.indexOf('comp:') === 0 && nodes[key]; })
          .map(function (key) { return comp[nodes[key].__ci]; });
        var nearest = function (c) {
          var best = Infinity;
          framed.forEach(function (o) { if (o !== c) best = Math.min(best, Math.hypot(o.x - c.x, o.y - c.y)); });
          return best;
        };
        L.reticles.forEach(function (key, i) { reticle(key, moving, i === 0 ? 'self' : 'full', nearest); });
        L.open.forEach(function (key) { reticle(key, moving, 'part', nearest); });
        lit = L;
        chosen = s;
        emphasise();
        // The plates first, then the names, then the ribbons' counts, each
        // keeping clear of what is already set.
        label(moving, arrive, later);
      }
      /* ---- What the panel is examining ---- */
      /* The explorer's panel says which relation the reader is reading, and
         the drawing answers it: a component's connections view quiets its
         rule lines, its rules view quiets its code connections and their
         names, and a narrowing (a family of connections chosen to stand
         alone, or a find) draws just those connections, each its own route,
         over the rest stepped back. In the doctrine the category open in
         the panel is the one named on the drawing. The camera never moves
         for any of it. */
      var chosen = null, PLATE_BUDGET = 10;
      function emphasise() {
        var s = chosen || { level: 'system' }, comp1 = explorer && s.level === 'component', N = comp1 ? narrowNow() : null;
        svg.classList.toggle('is-view-code', comp1 && inspect.view === 'code');
        svg.classList.toggle('is-view-rules', comp1 && inspect.view === 'rules');
        ['axiom', 'principle', 'failure'].forEach(function (k) { svg.classList.toggle('is-cat-' + k, explorer && s.level === 'doctrine' && inspect.cat === k); });
        svg.classList.toggle('is-narrowed', !!(N && N.links));
        svg.classList.toggle('is-narrowed-rules', !!(N && N.rules));
        clear(gScope);
        litPaths.forEach(function (lp) {
          if (lp.ink !== 'azure') return;
          var to = lp.el.getAttribute('data-to') || '', from = lp.el.getAttribute('data-from') || '';
          var id = to.indexOf('rule:') === 0 ? to.slice(5) : from.indexOf('rule:') === 0 ? from.slice(5) : null;
          lp.el.classList.toggle('is-in-scope', !!(N && N.rules && id && N.rules.indexOf(id) >= 0));
        });
        if (N && N.links) N.links.forEach(function (k) {
          var l = model.links[k];
          if (!l || !routes[k]) return;
          gScope.appendChild(sv('path', { 'class': 'sm-route sm-route--' + (l.kind || 'named') + ' is-scoped', d: fibreD(k, true, null),
            'data-from': 'comp:' + model.comps[l[0]].id, 'data-to': 'comp:' + model.comps[l[1]].id, 'data-k': String(k) }));
        });
      }
      // The components a view names on plates. In the explorer a component
      // with more connections than fit on plates names none of them until
      // the reader narrows to a family or points at a row; every name keeps
      // its size, and every one is still listed in the panel. Its
      // rules view names no component but itself.
      function platesFor(L, s) {
        if (!explorer || !s || s.level !== 'component' || !L.plates.length) return L.plates;
        var self = L.plates.slice(0, 1), rest = L.plates.slice(1), N = narrowNow();
        if (inspect.view === 'rules') return self;
        if (N && N.links) {
          var keep = Object.create(null);
          N.links.forEach(function (k) { var l = model.links[k]; if (l) keep[l[0] === s.comp ? l[1] : l[0]] = true; });
          return self.concat(rest.filter(function (ci) { return keep[ci]; }));
        }
        return rest.length > PLATE_BUDGET ? self : L.plates;
      }
      // How many connections each lit ribbon carries (of those a narrowing
      // keeps), set beside the point where it parts: a ribbon is one kind of
      // connection to one family, so the count is of that kind alone. A
      // count that finds no clear place is left out; the panel has them all.
      function countRibbons() {
        clear(gCounts);
        var s = chosen;
        if (!explorer || !s || s.level !== 'component' || !lit) return;
        var N = narrowNow(), keepK = null;
        if (N && N.links) { keepK = Object.create(null); N.links.forEach(function (k) { keepK[k] = true; }); }
        var litK = Object.create(null);
        lit.links.forEach(function (x) { litK[x.k] = true; });
        sheaves.forEach(function (S) {
          if (S.h !== s.comp) return;
          var n = S.links.filter(function (k) { return litK[k] && (!keepK || keepK[k]); }).length;
          if (n < 3) return;
          var text = String(n), w = Math.ceil(textWidth(text, 'sm-count') + 10), hgt = 20;
          var a = polar(cx, cy, S.end.r, S.end.a);
          var spot = placeBox(a, 5, w, hgt, { inside: true, toward: [Math.cos(S.end.a), Math.sin(S.end.a)], steps: [2, 6, 12, 20, 30] });
          if (!spot) return;
          var g = sv('g', { 'class': 'sm-count-g sm-count-g--' + S.kind, 'data-sm-count': model.families[S.fam].key, 'data-kind': S.kind, 'data-n': text });
          var t = sv('text', { 'class': 'sm-count sm-note', x: fx((spot.box.x0 + spot.box.x1) / 2), y: fx((spot.box.y0 + spot.box.y1) / 2),
            'text-anchor': 'middle', 'dominant-baseline': 'central' });
          t.textContent = text;
          g.appendChild(t);
          gCounts.appendChild(g);
          annot.add(spot.box);
        });
      }
      function label(moving, arrive, later) {
        annot = boxGrid(28);
        clear(gPlates);
        plates(platesFor(lit, chosen), moving, arrive, later);
        annotate(lit, chosen, moving, later);
        countRibbons();
      }
      // The panel changed what it examines: the drawing answers at once.
      function reinspect() {
        if (!chosen) return;
        emphasise();
        label(false, null, 0);
        if (hoverKey) preview(hoverKey, hoverRel);
      }

      /* A reticle: four corner ticks round the object chosen, a target lock,
         in hairline. Round a component where a rule is shown enforced it is
         the rule's ink; where a narrower part of the rule is checked, an
         open frame of two corners. On the rim a frame stands along the
         mark's radius, and where the next framed mark is close it narrows to
         its share of the room between them (never wider than square), so
         no two frames touch. It eases in from a third wider. */
      function reticle(key, moving, kind, nearest) {
        var n = nodes[key];
        if (!n) return;
        var x, y, e, ew, turnBy = 0, onRim = key.indexOf('comp:') === 0;
        if (onRim) {
          var c = comp[n.__ci];
          x = c.x; y = c.y; e = markSize / 2 + 6.5;
          ew = Math.max(2.5, Math.min(e, (nearest ? nearest(c) : Infinity) / 2 - 1.25));
          turnBy = c.a * 180 / Math.PI - 90;
        } else { var q = rule[key.slice(5)]; if (!q) return; x = q.x; y = q.y; e = ew = q.half + 6.5; }
        var arm = Math.max(3, Math.min(6, e * 0.32)), armW = Math.min(arm, Math.max(1.5, ew * 0.45)), d = '';
        var corners = kind === 'part' ? [[-1, -1], [1, 1]] : [[-1, -1], [1, -1], [1, 1], [-1, 1]];
        corners.forEach(function (k) {
          var px = k[0] * ew, py = k[1] * e;
          d += 'M' + fx(px - k[0] * armW) + ' ' + fx(py) + 'H' + fx(px) + 'V' + fx(py - k[1] * arm);
        });
        var g = sv('g', { transform: onRim ? 'translate(' + fx(x) + ' ' + fx(y) + ') rotate(' + fx(turnBy) + ')' :
          'translate(' + fx(Math.round(x) + 0.5) + ' ' + fx(Math.round(y) + 0.5) + ')' });
        var p = sv('path', { 'class': 'sm-reticle' + (kind === 'self' ? '' : ' sm-reticle--' + kind) + (onRim ? ' sm-reticle--rim' : ''), d: d });
        g.appendChild(p);
        gMarks.appendChild(g);
        if (moving && motionOK() && p.animate) {
          try { p.animate([{ transform: 'scale(1.35)', opacity: 0 }, { transform: 'scale(1)', opacity: 1 }], { duration: 160, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' }); } catch (e) {}
        }
      }

      /* ---- Name plates ---- */
      /* Horizontal, at the body size, outside the rim, each on a hairline
         leader from the end of its component's furniture. Placed in order
         (the thing chosen first), each where it covers least: never over
         another plate or leader, a mark or the ring, never off the drawing.
         A sector's name under a plate steps aside while it shows. A name
         that finds no room is listed in the column all the same; a name a
         zoom has already set round the rim needs no plate. */
      var PLATE_MAX = 14, PLATE_LEAD = 20, GO_W = 22;
      // The ways a name can be set on a plate: on one line, or on two or
      // three lines broken where they come out most nearly equal (a narrow
      // room at the sides of the ring takes them). Never cut. extra: room
      // kept at the right for the arrow on the chosen component's plate.
      function plateShapes(text, extra) {
        extra = extra || 0;
        var one = textWidth(text, 'sm-plate__text');
        var out = [{ lines: [text], w: one + 16 + extra, h: 26, cost: 0 }];
        var words = text.split(' ');
        if (words.length > 1) {
          var best2 = null;
          for (var k = 1; k < words.length; k++) {
            var a = words.slice(0, k).join(' '), b = words.slice(k).join(' ');
            var wide = Math.max(textWidth(a, 'sm-plate__text'), textWidth(b, 'sm-plate__text'));
            if (!best2 || wide < best2.wide) best2 = { lines: [a, b], wide: wide };
          }
          if (best2.wide < one - 24) out.push({ lines: best2.lines, w: best2.wide + 16 + extra, h: 26 + PLATE_LEAD, cost: 22 });
        }
        if (words.length > 2) {
          var best3 = null;
          for (var i = 1; i < words.length - 1; i++) {
            for (var j = i + 1; j < words.length; j++) {
              var l3 = [words.slice(0, i).join(' '), words.slice(i, j).join(' '), words.slice(j).join(' ')];
              var w3 = Math.max(textWidth(l3[0], 'sm-plate__text'), textWidth(l3[1], 'sm-plate__text'), textWidth(l3[2], 'sm-plate__text'));
              if (!best3 || w3 < best3.wide) best3 = { lines: l3, wide: w3 };
            }
          }
          if (best3.wide < out[out.length - 1].w - extra - 16 - 14) out.push({ lines: best3.lines, w: best3.wide + 16 + extra, h: 26 + 2 * PLATE_LEAD, cost: 60 });
        }
        return out;
      }
      function plates(list, moving, arrive, later) {
        Object.keys(labelBoxes).forEach(function (fi) { labelBoxes[fi].g.classList.remove('is-covered'); });
        if (!list.length) return;
        var placed = [], covered = Object.create(null), shown = 0;
        // Under a camera a plate keeps clear of the band where the view fades.
        var edgeIn = cam ? 20 : 4;
        var furn = R + depth;
        function hits(a, b, pad) { return a.x0 - pad < b.x1 && a.x1 + pad > b.x0 && a.y0 - pad < b.y1 && a.y1 + pad > b.y0; }
        function segBox(x0, y0, x1, y1) { return { x0: Math.min(x0, x1) - 1.5, x1: Math.max(x0, x1) + 1.5, y0: Math.min(y0, y1) - 1.5, y1: Math.max(y0, y1) + 1.5 }; }
        function outside(b) {
          var nx = clamp(cx, b.x0, b.x1), ny = clamp(cy, b.y0, b.y1);
          return Math.sqrt((nx - cx) * (nx - cx) + (ny - cy) * (ny - cy)) >= furn + 3;
        }
        function labelsUnder(boxes) {
          var fams = [];
          Object.keys(labelBoxes).forEach(function (fi) {
            if (labelBoxes[fi].boxes.some(function (q) { return boxes.some(function (b) { return hits(b, q, 0); }); })) fams.push(fi);
          });
          return fams;
        }
        list.forEach(function (ci, rank) {
          // A component already named round the rim needs no plate.
          if (shown >= PLATE_MAX || !comp[ci] || namedComp[ci]) return;
          var C = comp[ci], c = model.comps[ci], self = rank === 0 && at.level === 'component';
          var r0 = R + 16 + C.bar + (C.enf ? 5 : 2);
          var best = null;
          // The chosen component's own plate is a way to its page: its name
          // and an arrow, a click away (as is a second click on its mark).
          var go = self && !!pageOf('comp:' + c.id);
          plateShapes(c.label, go ? GO_W : 0).forEach(function (shape) {
            var w = shape.w, hgt = shape.h;
            [0, 10, 22, 36, 52, 70, 90].forEach(function (lift) {
              var rl = Math.max(furn + 6, r0 + 4) + lift;
              var e = polar(cx, cy, rl, C.a), s0 = polar(cx, cy, r0, C.a);
              // The leader's bend stays on the drawing too, never out under
              // the key or the caption.
              if (e[0] < edgeIn || e[0] > width - edgeIn || e[1] < edgeIn || e[1] > size - edgeIn) return;
              var cos = Math.cos(C.a), sides = Math.abs(cos) < 0.42 ? [cos >= 0 ? 1 : -1, cos >= 0 ? -1 : 1] : [cos >= 0 ? 1 : -1];
              sides.forEach(function (side, si) {
                [0, -1, 1, -2, 2].forEach(function (v) {
                  var x0 = side > 0 ? e[0] + 5 : e[0] - 5 - w, y0 = e[1] - hgt / 2 + v * (hgt / 2 + 3);
                  if (Math.abs(cos) < 0.42 && v === 0) {
                    // Over the top or under the bottom: hung above or below the leader's end.
                    y0 = Math.sin(C.a) < 0 ? e[1] - hgt - 2 : e[1] + 2;
                    x0 = side > 0 ? e[0] - 10 : e[0] + 10 - w;
                  }
                  var box = { x0: x0, x1: x0 + w, y0: y0, y1: y0 + hgt };
                  if (box.x0 < edgeIn || box.x1 > width - edgeIn || box.y0 < edgeIn || box.y1 > size - edgeIn) return;
                  if (!outside(box)) return;
                  // Never under the explorer's controls or its key.
                  var avoid = avoidRects;
                  for (var av = 0; av < avoid.length; av++) if (hits(box, avoid[av], 6)) return;
                  var ey = clamp(e[1], box.y0 + 4, box.y1 - 4), ex = side > 0 ? box.x0 : box.x1;
                  var legs = [[s0[0], s0[1], e[0], e[1]], [e[0], e[1], ex, ey]];
                  if (Math.abs(cos) < 0.42 && v === 0) legs = [[s0[0], s0[1], e[0], e[1]], [e[0], e[1], e[0], Math.sin(C.a) < 0 ? box.y1 : box.y0]];
                  var legBoxes = legs.map(function (L4) { return segBox(L4[0], L4[1], L4[2], L4[3]); });
                  // Never over a name a zoom has set round the rim.
                  if (nameGrid.hits(box, 3) || legs.some(function (L4) { return segmentHits(nameGrid, L4, 1); })) return;
                  for (var q = 0; q < placed.length; q++) {
                    if (hits(box, placed[q].box, 5)) return;
                    for (var m = 0; m < placed[q].legs.length; m++) if (hits(box, placed[q].legs[m], 3)) return;
                    for (var m2 = 0; m2 < legBoxes.length; m2++) if (hits(legBoxes[m2], placed[q].box, 2)) return;
                  }
                  var cov = labelsUnder([box].concat(legBoxes));
                  var cost = lift + (si ? 24 : 0) + Math.abs(v) * 6 + cov.length * 260 + shape.cost +
                    cov.filter(function (fi) { return !covered[fi]; }).length * 140;
                  if (!best || cost < best.cost) best = { cost: cost, box: box, legs: legs, legBoxes: legBoxes, cov: cov, side: side, shape: shape };
                });
              });
            });
          });
          if (!best) return;
          if (self && best.cov.length && best.cost > 2000) return;
          placed.push({ box: best.box, legs: best.legBoxes });
          // The rules' names placed after the plates keep clear of them.
          if (annot) {
            annot.add(best.box);
            best.legs.forEach(function (L4) { addSegment(annot, L4); });
          }
          best.cov.forEach(function (fi) { covered[fi] = true; });
          shown++;
          // In a rule's view a name is framed as its mark is: the rule's ink
          // where a test shows the rule enforced, lighter and open where a
          // test checks a part of it.
          var how = at.level === 'rule' && lit && lit.comps ? lit.comps[ci] : null;
          var g = sv('g', { 'class': 'sm-plate' + (self ? ' sm-plate--self' : '') + (go ? ' sm-plate--go' : '') + (how === 'enforce' ? ' sm-plate--full' : how === 'partly' ? ' sm-plate--part' : ''),
            'data-sm-plate': 'comp:' + c.id });
          var dl = '';
          best.legs.forEach(function (L4) { dl += 'M' + fx(L4[0]) + ' ' + fx(L4[1]) + 'L' + fx(L4[2]) + ' ' + fx(L4[3]); });
          g.appendChild(sv('path', { 'class': 'sm-leader sm-wire', d: dl, 'data-from': 'comp:' + c.id, 'data-to': null }));
          var b = best.box, sh = best.shape, textW = sh.w - (go ? GO_W : 0);
          g.appendChild(sv('rect', { 'class': 'sm-plate__box', x: fx(Math.round(b.x0) + 0.5), y: fx(Math.round(b.y0) + 0.5), width: Math.round(sh.w), height: sh.h, rx: 3 }));
          sh.lines.forEach(function (lineText, li) {
            var t = sv('text', { 'class': 'sm-plate__text sm-label', x: fx(b.x0 + textW / 2), y: fx(b.y0 + 13 + li * PLATE_LEAD), 'text-anchor': 'middle', 'dominant-baseline': 'central' });
            t.textContent = lineText;
            g.appendChild(t);
          });
          if (go) {
            var arrow = sv('text', { 'class': 'sm-plate__go', x: fx(b.x0 + sh.w - 10), y: fx(b.y0 + sh.h / 2), 'text-anchor': 'end', 'dominant-baseline': 'central' });
            arrow.textContent = '→';
            g.appendChild(arrow);
            g.addEventListener('click', function (e) { if (e && e.stopPropagation) e.stopPropagation(); openPage('comp:' + c.id, e); });
          }
          gPlates.appendChild(g);
          if (moving && motionOK() && g.animate) {
            var when = arrive && arrive[ci] !== undefined ? arrive[ci] : 120 + (later || 0) + rank * 30;
            try { g.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 140, delay: Math.min(1200, when), easing: EASE, fill: 'backwards' }); } catch (e) {}
          }
        });
        Object.keys(covered).forEach(function (fi) { labelBoxes[fi].g.classList.add('is-covered'); });
        lit.plated = shown;
      }

      /* ---- Tags and names on the drawing ---- */
      /* What a view is about is named on the drawing beside its mark, so the
         eye finds it there and needs the column only to read on: the chosen
         rule on a tag (its kind over its name, framed in the rule's ink,
         the arrow to its card), and where they stand clear the names of the
         rules the view lights (those a component's paper module cites, the
         axioms a rule rests on or threatens, the twelve axioms when the
         doctrine fills the drawing). Each is set where it covers no mark,
         glyph, word or plate, off the rim's band and inside the drawing's
         edges, as near its mark and as clear of the lit lines as it can be,
         on a hairline leader where it stands apart. A name with no such
         place is left to the column, which lists every one. */
      var annot = null, litPts = null, staticObs = null, tagged = Object.create(null);
      function addSegment(grid, s) {
        var len = Math.hypot(s[2] - s[0], s[3] - s[1]), n = Math.max(1, Math.ceil(len / 5));
        for (var i = 0; i <= n; i++) {
          var x = s[0] + (s[2] - s[0]) * i / n, y = s[1] + (s[3] - s[1]) * i / n;
          grid.add({ x0: x - 1.5, x1: x + 1.5, y0: y - 1.5, y1: y + 1.5 });
        }
      }
      // What no name may cover: the marks, the glyphs, the centre's name,
      // the families' names and the names a zoom set round the rim.
      function obstacles() {
        if (staticObs) return staticObs;
        staticObs = boxGrid(28);
        model.comps.forEach(function (c, ci) {
          var C = comp[ci];
          if (C) staticObs.add({ x0: C.x - markSize / 2 - 3, x1: C.x + markSize / 2 + 3, y0: C.y - markSize / 2 - 3, y1: C.y + markSize / 2 + 3 });
        });
        Object.keys(rule).forEach(function (id) {
          var q = rule[id], e = q.half + 3;
          staticObs.add({ x0: q.x - e, x1: q.x + e, y0: q.y - e, y1: q.y + e });
        });
        // The centre's name keeps a wider berth: a name set close beside it
        // reads as one line of words with it.
        if (labelBox && centreShown) staticObs.add({ x0: labelBox.x0 - 14, x1: labelBox.x1 + 14, y0: labelBox.y0 - 12, y1: labelBox.y1 + 12 });
        Object.keys(labelBoxes).forEach(function (fi) { labelBoxes[fi].boxes.forEach(function (b) { staticObs.add(b); }); });
        nameBoxes.forEach(function (b) { staticObs.add(b); });
        return staticObs;
      }
      // Whether a box reaches into the rim's band: the marks and their
      // furniture, from just inside the marks to the end of the bars.
      var bandIn = R - markSize / 2 - 5, bandOut = R + depth + 5;
      function nearFar(b) {
        var nx = clamp(cx, b.x0, b.x1), ny = clamp(cy, b.y0, b.y1);
        return [Math.hypot(nx - cx, ny - cy), Math.max(Math.hypot(b.x0 - cx, b.y0 - cy), Math.hypot(b.x1 - cx, b.y0 - cy),
          Math.hypot(b.x0 - cx, b.y1 - cy), Math.hypot(b.x1 - cx, b.y1 - cy))];
      }
      // Points along what a view lights, a few pixels apart, counted by area.
      function pointGrid(cell) {
        var cells = new Map();
        return {
          add: function (x, y) {
            var key = Math.floor(x / cell) * 100003 + Math.floor(y / cell), l = cells.get(key);
            if (l) l.push(x, y); else cells.set(key, [x, y]);
          },
          count: function (b) {
            var n = 0, gx1 = Math.floor(b.x1 / cell), gy0 = Math.floor(b.y0 / cell), gy1 = Math.floor(b.y1 / cell);
            for (var gx = Math.floor(b.x0 / cell); gx <= gx1; gx++) for (var gy = gy0; gy <= gy1; gy++) {
              var l = cells.get(gx * 100003 + gy);
              if (!l) continue;
              for (var i = 0; i < l.length; i += 2) if (l[i] >= b.x0 && l[i] <= b.x1 && l[i + 1] >= b.y0 && l[i + 1] <= b.y1) n++;
            }
            return n;
          }
        };
      }
      function litPoints(L) {
        var g = pointGrid(24);
        litPaths.forEach(function (lp) { for (var i = 0; i < lp.pts.length; i += 2) g.add(lp.pts[i][0], lp.pts[i][1]); });
        Object.keys(L.spans).forEach(function (k) {
          var sp = spanEls[k];
          if (sp) for (var i = 0; i < sp.pts.length; i += 2) g.add(sp.pts[i][0], sp.pts[i][1]);
        });
        return g;
      }
      // Sixteen ways out from a mark (thirty-two for the chosen rule's tag,
      // which must find room), and how far out along each to try.
      var DIRS = [], DIRS32 = [];
      for (var di = 0; di < 16; di++) DIRS.push([Math.cos(di * Math.PI / 8), Math.sin(di * Math.PI / 8)]);
      for (var dj = 0; dj < 32; dj++) DIRS32.push([Math.cos(dj * Math.PI / 16), Math.sin(dj * Math.PI / 16)]);
      /* A place for a box w by hgt beside the point a, whose mark reaches
         rA px round it: the box stands wholly beyond rA + a step along one of
         the sixteen ways, and the nearest clear place wins, a place over lit
         lines paying for every few pixels of them. opts.inside keeps the box
         inside the rim; opts.outside, outside it; opts.toward [x, y] leans
         the choice that way. Returns { box, u, leader } or null. */
      function placeBox(a, rA, w, hgt, opts) {
        opts = opts || {};
        var obs = obstacles(), edge = cam ? 22 : 8, best = null, toward = opts.toward || null, dirs = opts.dirs || DIRS;
        var steps = opts.steps || [3, 10, 20, 34, 52, 76, 106];
        for (var si = 0; si < steps.length; si++) {
          var dd = rA + steps[si];
          for (var k = 0; k < dirs.length; k++) {
            var u = dirs[k], s = Math.abs(u[0]) * w / 2 + Math.abs(u[1]) * hgt / 2;
            var bx = a[0] + u[0] * (dd + s), by = a[1] + u[1] * (dd + s);
            var box = { x0: bx - w / 2, x1: bx + w / 2, y0: by - hgt / 2, y1: by + hgt / 2 };
            if (box.x0 < edge || box.x1 > width - edge || box.y0 < edge || box.y1 > size - edge) continue;
            var nf2 = nearFar(box);
            if (nf2[0] < bandOut && nf2[1] > bandIn) continue;
            if (opts.inside && nf2[1] > bandIn) continue;
            if (opts.outside && nf2[0] < bandOut) continue;
            var blocked = false;
            var avoid = avoidRects;
            for (var q = 0; q < avoid.length && !blocked; q++) {
              var A = avoid[q];
              if (box.x0 < A.x1 + 6 && box.x1 > A.x0 - 6 && box.y0 < A.y1 + 6 && box.y1 > A.y0 - 6) blocked = true;
            }
            if (blocked || obs.hits(box, 2) || (annot && annot.hits(box, 4))) continue;
            var lines = litPts ? litPts.count({ x0: box.x0 - 2, x1: box.x1 + 2, y0: box.y0 - 2, y1: box.y1 + 2 }) : 0;
            var cost = steps[si] + lines * 8 + (toward ? (1 - (u[0] * toward[0] + u[1] * toward[1])) * 10 : 0);
            if (best && cost >= best.cost) continue;
            // Its leader, from the mark's edge to the box's nearest point,
            // passes over no other mark or glyph.
            var nx = clamp(a[0], box.x0, box.x1), ny = clamp(a[1], box.y0, box.y1), L = Math.hypot(nx - a[0], ny - a[1]);
            var leader = L > rA + 8 ? [a[0] + (nx - a[0]) / L * rA, a[1] + (ny - a[1]) / L * rA, nx, ny] : null;
            if (leader && segmentHits(obs, [leader[0] + (nx - a[0]) / L * 3, leader[1] + (ny - a[1]) / L * 3, nx, ny], 0)) continue;
            best = { cost: cost, box: box, u: u, leader: leader };
          }
          // A clear place this near beats anything further out.
          if (best && best.cost <= (si + 1 < steps.length ? steps[si + 1] : Infinity)) break;
        }
        return best;
      }
      // A name broken into the fewest lines no wider than `most`, the lines
      // as nearly equal as the words allow.
      function balance(text, cls, most) {
        if (textWidth(text, cls) <= most) return [text];
        var words = text.split(' '), two = null, three = null, i, j;
        for (i = 1; i < words.length; i++) {
          var a2 = words.slice(0, i).join(' '), b2 = words.slice(i).join(' ');
          var w2 = Math.max(textWidth(a2, cls), textWidth(b2, cls));
          if (!two || w2 < two.wide) two = { lines: [a2, b2], wide: w2 };
        }
        if (two && two.wide <= most) return two.lines;
        for (i = 1; i < words.length - 1; i++) for (j = i + 1; j < words.length; j++) {
          var l3 = [words.slice(0, i).join(' '), words.slice(i, j).join(' '), words.slice(j).join(' ')];
          var w3 = Math.max(textWidth(l3[0], cls), textWidth(l3[1], cls), textWidth(l3[2], cls));
          if (!three || w3 < three.wide) three = { lines: l3, wide: w3 };
        }
        return three && (!two || three.wide < two.wide) ? three.lines : two ? two.lines : [text];
      }
      function linesWide(lines, cls) { return lines.reduce(function (m, l) { return Math.max(m, textWidth(l, cls)); }, 0); }
      function arriveIn(g, delay, from) {
        if (!motionOK() || !g.animate) return;
        var k = [{ opacity: 0 }, { opacity: 1 }];
        if (from) k = [{ opacity: 0, transform: 'translate(' + fx(from[0]) + 'px, ' + fx(from[1]) + 'px)' }, { opacity: 1, transform: 'none' }];
        try { g.animate(k, { duration: 200, delay: Math.max(0, Math.min(1200, delay)), easing: EASE, fill: 'backwards' }); } catch (e) {}
      }
      /* The chosen rule's tag: its kind over its name, framed in the rule's
         ink, the arrow to its card at the end of the kind's line. It is the
         first thing placed after the plates, so it takes the best room. */
      // The tag's shapes, roomiest first: its kind over its name, the name
      // broken narrower; then, where a small drawing has no room for those,
      // the name alone (the glyph and the column say its kind), the arrow
      // at the end of its last line.
      var TAG_SHAPES = [{ kind: true, most: 236 }, { kind: true, most: 176 }, { kind: true, most: 132 },
                        { kind: false, most: 236 }, { kind: false, most: 160 }, { kind: false, most: 112 }];
      function drawTag(id, moving, later) {
        var q = rule[id], r = D.rules[id];
        if (!q || !r) return false;
        var kind = KIND_WORDS[r.kind], go = !!r.doctrine, lines = null, w = 0, hgt = 0, spot = null, shape = null;
        for (var m = 0; m < TAG_SHAPES.length && !spot; m++) {
          shape = TAG_SHAPES[m];
          lines = balance(r.title, TAG_TITLE, shape.most);
          var lastW = textWidth(lines[lines.length - 1], TAG_TITLE) + (go && !shape.kind ? 22 : 0);
          w = Math.ceil(Math.max(shape.kind ? textWidth(kind, TAG_KIND) + (go ? 24 : 0) : 0, linesWide(lines, TAG_TITLE), lastW) + 24);
          hgt = shape.kind ? 8 + 18 + 3 + lines.length * 20 + 8 : 7 + lines.length * 20 + 7;
          spot = placeBox([q.x, q.y], q.half + 9, w, hgt, { inside: true, dirs: DIRS32, steps: [3, 8, 14, 22, 32, 44, 58, 76, 98, 124, 154, 190] });
        }
        if (!spot) return false;
        var b = spot.box, top = shape.kind ? b.y0 + 8 + 18 + 3 : b.y0 + 7;
        var g = sv('g', { 'class': 'sm-tag sm-tag--' + r.kind + (go ? ' sm-tag--go' : ''), 'data-sm-tag': 'rule:' + id });
        if (spot.leader) g.appendChild(sv('path', { 'class': 'sm-tag__leader', d: 'M' + fx(spot.leader[0]) + ' ' + fx(spot.leader[1]) + 'L' + fx(spot.leader[2]) + ' ' + fx(spot.leader[3]) }));
        g.appendChild(sv('rect', { 'class': 'sm-tag__box', x: fx(Math.round(b.x0) + 0.5), y: fx(Math.round(b.y0) + 0.5), width: w, height: hgt, rx: 3 }));
        if (shape.kind) {
          var tk = sv('text', { 'class': TAG_KIND, x: fx(b.x0 + 12), y: fx(b.y0 + 8 + 9), 'dominant-baseline': 'central' });
          tk.textContent = kind;
          g.appendChild(tk);
        }
        lines.forEach(function (ln, i) {
          var t = sv('text', { 'class': TAG_TITLE + ' sm-label', x: fx(b.x0 + 12), y: fx(top + 10 + i * 20), 'dominant-baseline': 'central' });
          t.textContent = ln;
          g.appendChild(t);
        });
        if (go) {
          var arrow = sv('text', { 'class': 'sm-tag__go', x: fx(b.x0 + w - 11), y: fx(shape.kind ? b.y0 + 8 + 9 : top + 10 + (lines.length - 1) * 20),
            'text-anchor': 'end', 'dominant-baseline': 'central' });
          arrow.textContent = '→';
          g.appendChild(arrow);
          g.addEventListener('click', function (e) { if (e && e.stopPropagation) e.stopPropagation(); openPage('rule:' + id, e); });
        }
        gTags.appendChild(g);
        annot.add(b);
        if (spot.leader) addSegment(annot, spot.leader);
        if (moving) arriveIn(g, 110 + (later || 0), [-spot.u[0] * 6, -spot.u[1] * 6]);
        return true;
      }
      /* A rule's name in its ink, on a halo of the ground that parts the
         lines beneath it, beside its glyph: set to read away from the glyph
         (from its left edge to the right of a glyph, from its right edge to
         the left, centred above or below). */
      function drawName(id, into, opts) {
        opts = opts || {};
        var q = rule[id], r = D.rules[id];
        if (!q || !r) return false;
        // Its shapes, widest first, as the tag's.
        var mosts = [opts.most || 220, 150, 112], lead = 18, lines = null, w = 0, hgt = 0, spot = null;
        for (var m = 0; m < mosts.length && !spot; m++) {
          var next = balance(r.title, RULE_NAME, mosts[m]);
          if (lines && next.join('|') === lines.join('|')) continue;
          lines = next;
          w = Math.ceil(linesWide(lines, RULE_NAME) + 8);
          hgt = lines.length * lead + 4;
          spot = placeBox([q.x, q.y], q.half + 6, w, hgt, { inside: true, steps: opts.steps || [2, 7, 14, 24, 38, 56] });
        }
        if (!spot) return false;
        var b = spot.box, u = spot.u, anchor = u[0] > 0.35 ? 'start' : u[0] < -0.35 ? 'end' : 'middle';
        var tx = anchor === 'start' ? b.x0 + 4 : anchor === 'end' ? b.x1 - 4 : (b.x0 + b.x1) / 2;
        var g = sv('g', { 'class': 'sm-rname-g' + (opts.cls ? ' ' + opts.cls : ''), 'data-sm-name': 'rule:' + id });
        if (spot.leader) g.appendChild(sv('path', { 'class': 'sm-rname__leader', d: 'M' + fx(spot.leader[0]) + ' ' + fx(spot.leader[1]) + 'L' + fx(spot.leader[2]) + ' ' + fx(spot.leader[3]) }));
        lines.forEach(function (ln, i) {
          var t = sv('text', { 'class': RULE_NAME + ' sm-note', x: fx(tx), y: fx(b.y0 + 2 + lead / 2 + i * lead), 'text-anchor': anchor, 'dominant-baseline': 'central' });
          t.textContent = ln;
          g.appendChild(t);
        });
        into.appendChild(g);
        if (into === gTags) {
          annot.add(b);
          if (spot.leader) addSegment(annot, spot.leader);
        }
        if (opts.delay !== undefined) arriveIn(g, opts.delay);
        return true;
      }
      // The names a view sets, in the order they matter.
      function annotate(L, s, moving, later) {
        clear(gTags);
        clear(gHover);
        tagged = Object.create(null);
        litPts = litPoints(L);
        if (!D || !core || !s) return;
        var put = function (id, opts) { if (!tagged['rule:' + id] && drawName(id, gTags, opts)) tagged['rule:' + id] = true; };
        if (s.level === 'rule' && rule[s.rule]) {
          var r = D.rules[s.rule];
          if (drawTag(s.rule, moving, later)) tagged['rule:' + s.rule] = true;
          // The few rules it stands on or threatens, named; an axiom's own
          // many principles and failure modes wait for the pointer.
          var near = r.kind === 'principle' ? r.restsOn : r.kind === 'failure' ? r.guards : r.grounds.concat(r.threatenedBy);
          if (near.length <= 4) near.forEach(function (id) { put(id, { delay: moving ? 360 + (later || 0) : undefined }); });
        } else if (s.level === 'component') {
          var info = D.comp[s.comp], rank = function (id) {
            return info.enforces.indexOf(id) >= 0 ? 0 : info.partly.indexOf(id) >= 0 ? 1 : D.rules[id].kind === 'principle' ? 2 : 3;
          };
          // The rules shown holding here first, then the principles and the
          // axioms its paper module cites.
          var cited = Object.create(null);
          L.cites.forEach(function (x) { cited[x.id] = true; });
          var ids = uniq(info.enforces.concat(info.partly, Object.keys(cited))).filter(function (id) { return !!rule[id]; })
            .sort(function (p, q2) { return rank(p) - rank(q2); });
          // The explorer's views share the names out: its connections view
          // names no rule (their lines step back), its rules view as many as
          // stand clear, its overview eight.
          var most = !explorer ? 5 : inspect.view === 'code' ? 0 : inspect.view === 'rules' ? 14 : 8, n = 0;
          ids.forEach(function (id) {
            if (n >= most) return;
            var when = !moving ? undefined : cited[id] ? 60 + (later || 0) + Math.round(speedDur(ray(s.comp, id)) * 0.9) : 260 + (later || 0);
            if (!tagged['rule:' + id] && drawName(id, gTags, { delay: when, steps: [2, 7, 14, 24, 38, 56, 80] })) { tagged['rule:' + id] = true; n++; }
          });
        } else if (s.level === 'doctrine') {
          // The category open in the explorer's panel is the one named; the
          // axioms otherwise.
          var cat = explorer ? inspect.cat : 'axiom', ids2 = cat === 'principle' ? D.principles : cat === 'failure' ? D.failures : D.axioms;
          ids2.forEach(function (id, k) { put(id, { cls: 'sm-rname-g--' + cat, most: 200, delay: moving ? 220 + k * 24 + (later || 0) : undefined }); });
        }
      }
      // The name of whatever the pointer is on, when the drawing does not
      // already show it: a rule's beside its glyph, a component's on a
      // plate outside the rim. Never added to what the names keep clear of.
      function hoverName(key) {
        clear(gHover);
        if (!key || tagged[key] || !model || nowMs() < tipHushUntil) return;
        if (key.indexOf('rule:') === 0) {
          // Pointed at, a name may stand further off, on its leader.
          if (D && core && rule[key.slice(5)]) drawName(key.slice(5), gHover, { cls: 'sm-rname-g--hover', steps: [2, 7, 14, 24, 38, 56, 80, 110, 150, 196] });
          return;
        }
        if (key.indexOf('comp:') !== 0 || !nodes[key]) return;
        var ci = nodes[key].__ci, C = comp[ci];
        if (namedComp[ci] || (svg.querySelector && svg.querySelector('[data-sm-plate="' + key + '"]'))) return;
        var text = model.comps[ci].label, tw = textWidth(text, 'sm-plate__text'), w = Math.ceil(tw + 16), hgt = 26;
        var spot = placeBox([C.x, C.y], markSize / 2 + 8, w, hgt, { outside: true, toward: [Math.cos(C.a), Math.sin(C.a)], steps: [4, 12, 22, 36, 54] });
        if (!spot) return;
        var b = spot.box, g = sv('g', { 'class': 'sm-plate sm-plate--hover', 'data-sm-hover': key });
        if (spot.leader) g.appendChild(sv('path', { 'class': 'sm-leader', d: 'M' + fx(spot.leader[0]) + ' ' + fx(spot.leader[1]) + 'L' + fx(spot.leader[2]) + ' ' + fx(spot.leader[3]) }));
        g.appendChild(sv('rect', { 'class': 'sm-plate__box', x: fx(Math.round(b.x0) + 0.5), y: fx(Math.round(b.y0) + 0.5), width: w, height: hgt, rx: 3 }));
        var t = sv('text', { 'class': 'sm-plate__text sm-label', x: fx(b.x0 + w / 2), y: fx(b.y0 + 13), 'text-anchor': 'middle', 'dominant-baseline': 'central' });
        t.textContent = text;
        g.appendChild(t);
        gHover.appendChild(g);
      }

      /* ---- Pointing: the node named and lit, its own lines shown lightly ---- */
      var previewG = sv('g', { 'class': 'sm-preview', 'aria-hidden': 'true' });
      svg.insertBefore(previewG, gCore);
      /* Pointing at something the view lights (on the map or in the
         column) singles out its own lines to what is chosen: they keep
         their ink and the view's other lit lines step back. */
      function traced(key) {
        if (!key || !lit || at.level === 'system' || at.level === 'family') return false;
        if (key.indexOf('comp:') === 0) return !!nodes[key] && !!lit.comps[nodes[key].__ci];
        if (key.indexOf('rule:') === 0) return !!lit.rules[key.slice(5)];
        return false;
      }
      /* A connection pointed at (its mark, or its row in the panel) is drawn
         whole, from the chosen component to it along its own route, never
         left as a parting fibre at the end of a ribbon that stays lit: the
         reader never has to guess whether two lines overlap or join. A row
         names one relation (rel: its kind and direction), so a pair joined
         two ways shows only the way that row reads. A small chevron at its
         middle points the way the code acts. */
      function chevron(pts) {
        var cum = Loom.measure(pts), len = cum[cum.length - 1];
        if (!(len > 28)) return null;
        var p = Loom.pointAt(pts, len * 0.56, cum), tx = p.tx, ty = p.ty, nx = -ty, ny = tx, a = 5.5, b = 4.2;
        var d = 'M' + fx(p.x - tx * a + nx * b) + ' ' + fx(p.y - ty * a + ny * b) + 'L' + fx(p.x + tx * a * 0.6) + ' ' + fx(p.y + ty * a * 0.6) +
          'L' + fx(p.x - tx * a - nx * b) + ' ' + fx(p.y - ty * a - ny * b);
        return sv('path', { 'class': 'sm-trace__dir', d: d });
      }
      function trace(key, rel) {
        var on = traced(key);
        svg.classList.toggle('is-tracing', on);
        clear(gTrace);
        var fits = function (el) { return !rel || (el.getAttribute('data-kind') === rel.kind && el.getAttribute('data-dir') === rel.dir); };
        var ends = function (el) { return on && (el.getAttribute('data-from') === key || el.getAttribute('data-to') === key) && fits(el); };
        litPaths.forEach(function (lp) { lp.el.classList.toggle('is-traced', ends(lp.el)); });
        Object.keys(spanEls).forEach(function (k) { spanEls[k].el.classList.toggle('is-traced', ends(spanEls[k].el)); });
        Array.prototype.forEach.call(gTags.children || [], function (g) {
          if (g.classList) g.classList.toggle('is-traced', on && g.getAttribute('data-sm-name') === key);
        });
        if (!on || !lit || key.indexOf('comp:') !== 0 || at.level !== 'component') return;
        var ci = nodes[key].__ci;
        lit.links.forEach(function (x) {
          if (x.b !== ci || !routes[x.k] || (rel && (x.l.kind !== rel.kind || dirOf(x) !== rel.dir))) return;
          gTrace.appendChild(sv('path', { 'class': 'sm-route sm-route--' + (x.l.kind || 'named') + ' is-traced', d: fibreD(x.k, true, null),
            'data-from': 'comp:' + model.comps[x.l[0]].id, 'data-to': 'comp:' + model.comps[x.l[1]].id, 'data-kind': x.l.kind, 'data-dir': dirOf(x), 'data-k': String(x.k) }));
          var c = chevron(routes[x.k].pts);
          if (c) gTrace.appendChild(c);
        });
      }
      function preview(key, rel) {
        clear(previewG);
        hoverName(key);
        trace(key, rel);
        Object.keys(nodes).forEach(function (k) { nodes[k].classList.toggle('is-hover', k === key); });
        // Inside a family, a component pointed at shows its own relations
        // over the family's, which step back while it is pointed at.
        var peek = !!key && at.level === 'family' && key.indexOf('comp:') === 0;
        svg.classList.toggle('is-peeking', peek);
        if (!key || (at.level !== 'system' && !peek)) return;
        var s = null;
        if (key.indexOf('comp:') === 0) { var ci = nodes[key] ? nodes[key].__ci : -1; if (ci >= 0) s = { level: 'component', comp: ci, fam: model.comps[ci].fam }; }
        else if (key.indexOf('rule:') === 0) s = { level: 'rule', rule: key.slice(5) };
        else if (key.indexOf('fam:') === 0) s = { level: 'family', fam: familyIndex(key.slice(4)) };
        if (!s || (s.level === 'family' && s.fam < 0)) return;
        var L = lightOf(s);
        litDraws(L.links).forEach(function (dr) { previewG.appendChild(litPath(dr, null, 'sm-route is-preview', false)); });
        L.cites.forEach(function (x) { previewG.appendChild(sv('path', { 'class': 'sm-rline is-preview', d: Loom.lineD(ray(x.ci, x.id)) })); });
      }

      /* ---- The first sight: the lines run out once ---- */
      /* The rim, its names and the doctrine's glyphs are already in place as
         the drawing arrives (an empty frame used to slide in, and its marks
         then popped in one by one for a second more). Once it has landed,
         the doctrine's own lines draw out from its rules, and the fibres at
         rest run out along their own lines, each from the component it
         leaves, a little after one another round the ring. Two thirds of a
         second, once; then nothing moves. */
      function assemble() {
        if (!motionOK()) return;
        // The guides draw first, as an instrument is ruled: each family's
        // scale base clockwise from the top, and the necklace's orbit from
        // the top round.
        scaleEls.forEach(function (g) {
          if (!g || !g.querySelector) return;
          var base = g.querySelector('.sm-tick--base'), S = sectors[familyIndex(g.getAttribute('data-fam'))];
          if (base && S) drawIn(base, Math.round(norm(S.runFrom + Math.PI / 2) / TAU * 260), 300);
        });
        if (neck) drawIn(neck, 0, 560);
        if (D && core) Object.keys(spanEls).forEach(function (k) { drawIn(spanEls[k].el, 40, 380); });
        if (restDrawn) {
          // A ribbon runs out before its parting fibres when its component
          // acts on the others, after them when they act on it.
          var w0 = 2 * 0.95 * ws * 1.3 * 1.25 + 3;
          revealAlong(gRest, items.map(function (it) {
            if (it.part === 'link') return { pts: it.pts, w: w0, delay: norm(comp[model.links[it.links[0]][0]].a + Math.PI / 2) / TAU * 140 };
            var S = sheaves[it.sheaf], at0 = norm(comp[S.h].a + Math.PI / 2) / TAU * 140, out = S.role === 'out';
            if (it.part === 'trunk') return { pts: it.pts, w: w0 * Math.sqrt(it.links.length), reverse: !out, delay: at0 + (out ? 0 : 180), dur: 320 };
            return { pts: it.pts, w: w0, reverse: !out, delay: at0 + (out ? 240 : 0), dur: 240 };
          }), 60, 460);
        }
      }

      /* ---- Keys: round a ring and between rings ---- */
      function angleOf(key) {
        if (key.indexOf('comp:') === 0) return comp[nodes[key].__ci].a;
        if (key.indexOf('rule:') === 0) return rule[key.slice(5)].a;
        if (key.indexOf('fam:') === 0) return sectors[familyIndex(key.slice(4))].mid;
        return -Math.PI / 2;
      }
      var rims = model.comps.map(function (c, i) { return i; }).filter(function (i) { return !!comp[i]; })
        .sort(function (p, q) { return norm(comp[p].a + Math.PI / 2) - norm(comp[q].a + Math.PI / 2); })
        .map(function (ci) { return 'comp:' + model.comps[ci].id; });
      var famKeys = order.map(function (fi) { return 'fam:' + model.families[fi].key; });
      // The doctrine's rings for the keys: the satellites outside, the
      // necklace (axioms and the rules between them).
      function ringKeys(test) {
        return Object.keys(rule).filter(function (id) { return test(rule[id]); })
          .sort(function (p, q) { return norm(rule[p].a + Math.PI / 2) - norm(rule[q].a + Math.PI / 2); })
          .map(function (id) { return 'rule:' + id; });
      }
      var rings = {
        outer: ringKeys(function (q) { return q.role === 'satellite'; }),
        neck: ringKeys(function (q) { return q.role !== 'satellite'; }),
        inner: []
      };
      function ringOf(id) { return rule[id].role === 'satellite' ? 'outer' : 'neck'; }
      function nearest(keys, a) {
        var best = null, bd = Infinity;
        keys.forEach(function (k) { var d = Math.abs(turn(angleOf(k), a)); if (d < bd) { bd = d; best = k; } });
        return best;
      }
      function step(keys, key, dir) {
        var i = keys.indexOf(key);
        return keys[(i + dir + keys.length) % keys.length];
      }
      svg.addEventListener('keydown', function (e) {
        var n = e.target && e.target.closest ? e.target.closest('.sm-node') : null;
        if (!n) return;
        var key = n.getAttribute('data-sm-key'), next = null, kind = key.split(':')[0];
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(key, true); return; }
        var right = e.key === 'ArrowRight', left = e.key === 'ArrowLeft', upKey = e.key === 'ArrowUp', down = e.key === 'ArrowDown';
        if (!right && !left && !upKey && !down) return;
        e.preventDefault();
        var a = angleOf(key);
        var outerRing = rings.outer.length ? rings.outer : rings.neck;
        if (kind === 'comp') next = right ? step(rims, key, 1) : left ? step(rims, key, -1) : upKey ? 'fam:' + model.families[model.comps[n.__ci].fam].key : (D && core ? nearest(outerRing, a) : null);
        else if (kind === 'fam') next = right ? step(famKeys, key, 1) : left ? step(famKeys, key, -1) : down ? 'comp:' + model.comps[model.families[familyIndex(key.slice(4))].members[0]].id : null;
        else if (kind === 'doctrine') next = upKey && core ? nearest(rings.neck, -Math.PI / 2) : null;
        else if (kind === 'rule') {
          var rk = ringOf(key.slice(5)), list = rings[rk];
          var inward = { outer: 'neck', neck: null }[rk];
          var outward = { neck: rings.outer.length ? 'outer' : null, outer: null }[rk];
          next = right ? step(list, key, 1) : left ? step(list, key, -1) :
            upKey ? (outward ? nearest(rings[outward], a) : nearest(rims, a)) : (inward ? nearest(rings[inward], a) : 'doctrine');
        }
        if (next && nodes[next]) { rove(nodes[next]); nodes[next].focus(); }
      });
      function activate(key, keyedIt) {
        var how = { keyed: !!keyedIt };
        // Enter on what is already chosen opens its page, as a second click does.
        if (key === keyOf(at) && openPage(key)) return;
        if (key === 'doctrine') goDoctrine(null, how);
        else if (key.indexOf('fam:') === 0) goFamily(familyIndex(key.slice(4)), how);
        else if (key.indexOf('comp:') === 0) goComponent(nodes[key].__ci, how);
        else if (key.indexOf('rule:') === 0) goDoctrine(key.slice(5), how);
      }
      // One rim or core node at a time takes the Tab key: the one last
      // reached; the family names and the centre always do.
      var roving = null;
      function rove(n) {
        if (roving && roving !== n && roving.getAttribute('data-sm-key').indexOf('fam:') !== 0 && roving.getAttribute('data-sm-key') !== 'doctrine') roving.setAttribute('tabindex', '-1');
        n.setAttribute('tabindex', '0');
        roving = n;
      }

      return {
        el: el, svg: svg, R: R, cx: cx, cy: cy, pitch: pitchPx, sectors: sectors,
        // What a camera is reckoned from: the whole system's ring and box,
        // and what any view would light.
        R0: R0, depth: depth, width: width, size: size, coreOuter: core ? coreOuter : 0, lightOf: lightOf, cam: cam || null, crowded: crowded,
        core: core ? { order: core.order.slice(), ring: fx(hubR), outer: fx(coreOuter), pinned: !!core.stats.orderPinned,
                       bridges: Object.keys(rule).filter(function (id) { return rule[id].role === 'bridge'; }).length,
                       glyphGap: fx(coreGap), get lineGap() { return fx(core.stats.lineGlyphGap); }, nearest: fx(core.stats.nearestToCentre),
                       smallest: fx(Object.keys(rule).reduce(function (m, id) { return Math.min(m, rule[id].size); }, Infinity)) } : null,
        // Where the drawing stands, for tests and audits: its centre, the ring,
        // the radius rule lines come into the core from, the centre's name.
        frame: { cx: fx(cx), cy: fx(cy), R: fx(R), gate: fx(rGate), near: fx(NEAR * 180 / Math.PI),
                 label: labelBox ? { x0: fx(labelBox.x0), x1: fx(labelBox.x1), y0: fx(labelBox.y0), y1: fx(labelBox.y1) } : null },
        select: select, preview: preview, rove: rove, assemble: assemble, route: route, inspect: reinspect,
        weave: function () { return woven ? woven.stats : null; },
        // The ribbons: which component, which way, of what kind, to which
        // family, carrying how many links.
        sheaves: sheaves.map(function (S) {
          return { from: 'comp:' + model.comps[S.h].id, role: S.role, kind: S.kind, family: model.families[S.fam].key, links: S.links.length };
        }),
        litPaths: function () { return litPaths; },
        nodeOf: function (key) { return nodes[key] || null; },
        firstNode: function () { return nodes[famKeys[0]] || null; },
        anchorOf: function (key) { return nodes[key] || null; },
        lit: function () { return lit; },
        nodes: nodes, comp: comp, rule: rule
      };
    }

    /* ---- The readout: what the pointer or the keyboard is on ---- */
    /* The drawing names the thing beside its mark (its plate, or its name);
       what it is, in a sentence, is read out in a place of its own that
       never moves and never covers the drawing: on the landing over the
       card's own sentence, in the same box, so nothing round it shifts; in
       the explorer in the stage's top left corner, or, when the thing
       pointed at stands there, its bottom right. What is already chosen
       says how to open it. A camera move slides marks under a pointer that
       has not moved, so nothing is read out until it settles. */
    /* In a component's or a rule's view, what is pointed at is read out as
       its relation to what is chosen: the code connection as a sentence
       with the component that acts first, or how the rule stands there
       (cited by its paper module, enforced there by a test, a part of it
       checked there by a test), each said apart. */
    function relationText(key, rel) {
      if (!model) return null;
      if (at.level === 'component' && key.indexOf('comp:') === 0) {
        var ci = at.comp, self = model.comps[ci].label, said = [];
        relationsOf(ci).forEach(function (x) {
          if ('comp:' + model.comps[x.other].id !== key || (rel && (x.kind !== rel.kind || x.dir !== rel.dir))) return;
          var s = relationSentence(x.kind, x.dir, self, model.comps[x.other].label);
          if (said.indexOf(s) < 0) said.push(s);
        });
        return said.length ? said.join(' ') : null;
      }
      if (!D) return null;
      var ci2 = -1, id = null;
      if (at.level === 'component' && key.indexOf('rule:') === 0) { ci2 = at.comp; id = key.slice(5); }
      else if (at.level === 'rule' && key.indexOf('comp:') === 0) {
        id = at.rule;
        for (var i = 0; i < model.comps.length; i++) if ('comp:' + model.comps[i].id === key) ci2 = i;
      }
      if (ci2 < 0 || !id || !D.rules[id]) return null;
      var words = [], held = heldIn(ci2, id), r = D.rules[id];
      if (r.kind !== 'failure') words.push(citesRule(ci2, id) ? 'Its paper module cites this rule.' : 'Its paper module does not cite this rule.');
      if (held) words.push(HELD_WORDS[held]);
      else if (r.kind !== 'failure' && D.enforcedBy === 'tests') words.push('No test marks it here.');
      return words.join(' ');
    }
    function tipText(key, rel) {
      var t = tipBase(key);
      if (!t) return t;
      var said = relationText(key, rel);
      if (said) t.text = said;
      return t;
    }
    function tipBase(key) {
      if (key === 'doctrine') {
        return { title: 'The doctrine', sub: D ? countWords(D.axioms.length, 'axiom', 'axioms') + ', ' + countWords(D.principles.length, 'principle', 'principles') +
          ' and ' + countWords(D.failures.length, 'failure mode', 'failure modes') : null, text: 'The rules the system is built on.' };
      }
      if (key.indexOf('comp:') === 0) {
        for (var i = 0; i < model.comps.length; i++) if ('comp:' + model.comps[i].id === key) {
          var c = model.comps[i];
          return { title: c.label, sub: model.families[c.fam].title + (c.cls ? ' · ' + lowerFirst(CLASS_WORDS[c.cls]) : ''), text: c.line };
        }
      }
      if (key.indexOf('rule:') === 0 && D && D.rules[key.slice(5)]) {
        var r = D.rules[key.slice(5)];
        return { title: r.title, sub: KIND_WORDS[r.kind], text: r.plain };
      }
      if (key.indexOf('fam:') === 0) {
        var F = model.families[familyIndex(key.slice(4))];
        return F ? { title: F.title, sub: countLine(F) + (F.inside ? ', ' + countFigure(F.inside, linkNoun(1), linkNoun(2)) + ' among them' : ''), text: F.summary } : null;
      }
      return null;
    }
    var litPlate = null, tipHushUntil = 0;
    function showTipFor(key, anchor) {
      if (litPlate) { litPlate.classList.remove('is-hover'); litPlate = null; }
      if (nowMs() < tipHushUntil) { hideTip(); return; }
      // A mark already named on a plate lights its plate as well.
      var plated = key && map && map.svg.querySelector ? map.svg.querySelector('[data-sm-plate="' + key + '"]') : null;
      if (plated) { plated.classList.add('is-hover'); litPlate = plated; }
      var t = key ? tipText(key, key === hoverKey ? hoverRel : null) : null;
      if (!t) { hideTip(); return; }
      clear(tip);
      var headLine = h('p', 'sm-readout__head');
      headLine.appendChild(h('span', 'sm-readout__title', t.title));
      if (t.sub) headLine.appendChild(h('span', 'sm-readout__kind', t.sub));
      tip.appendChild(headLine);
      var chosen = key === keyOf(at) && !!pageOf(key);
      if (chosen) tip.appendChild(h('p', 'sm-readout__hint', openWords(key)));
      else if (t.text) tip.appendChild(h('p', 'sm-readout__text', t.text));
      if (!explorer) {
        // The card's sentence steps aside and the readout takes its box.
        var top = caption.offsetTop || 0, left = caption.offsetLeft || 0, wide = caption.offsetWidth || 0, tall = caption.offsetHeight || 0;
        if (tip.style && tip.style.setProperty && wide > 0) {
          tip.style.setProperty('--sm-readout-x', left + 'px');
          tip.style.setProperty('--sm-readout-y', top + 'px');
          tip.style.setProperty('--sm-readout-w', wide + 'px');
          tip.style.setProperty('--sm-readout-h', Math.max(tall, 24) + 'px');
          tip.style.setProperty('--sm-readout-lines', String(Math.max(1, Math.floor(Math.max(tall, 24) / 24) - 1)));
        }
        if (caption.classList) caption.classList.add('is-read-over');
        tip.hidden = false;
        return;
      }
      // The explorer: the stage's top left, or its bottom right when the
      // thing pointed at stands under the top left.
      tip.hidden = false;
      var corner = 'tl';
      if (anchor && anchor.getBoundingClientRect && root.getBoundingClientRect) {
        var rr = root.getBoundingClientRect(), b = anchor.getBoundingClientRect();
        var w = tip.offsetWidth || 0, hgt = tip.offsetHeight || 0;
        if (b.left - rr.left < 18 + w + 24 && b.top - rr.top < 14 + hgt + 24) corner = 'br';
      }
      if (tip.classList) {
        tip.classList.toggle('sm-readout--tl', corner === 'tl');
        tip.classList.toggle('sm-readout--br', corner === 'br');
      }
    }
    function hideTip() {
      tip.hidden = true;
      if (caption.classList) caption.classList.remove('is-read-over');
      if (litPlate) { litPlate.classList.remove('is-hover'); litPlate = null; }
    }

    /* ---- The column beside the map ---- */
    /* At the top level the column is the band's heading, its sentence, the
       families (the page's own list, which works without this script) and a
       way into the doctrine. Below it, a panel laid over the column is the
       readable index of whatever the map lights: one name to a line, each a
       way to that thing, each lighting its mark where it stands. A long list
       shows eight and the rest on request; a long page scrolls in place and
       says so; the links at its foot stay in view. */
    var column = makeColumn();
    /* In the explorer the column is the panel's body: the overview the page
       carries (the families, how the map is drawn), then a family's page or
       a component's or a rule's in its place once one is chosen, read
       straight down to its end. Nothing is held back behind "show all", no
       description is shortened, and the body scrolls; the ways to the
       component's own pages close each page. */
    function makeColumn() {
      var host = explorer ? explorerEl.querySelector('[data-system-panel]') :
        section && section.querySelector ? section.querySelector('.home-split__text') : null;
      var noop = { sync: function () {}, lit: function () {}, state: function () { return null; }, ready: function () {}, rows: function () {}, refit: function () {}, again: function () {} };
      if (!host || !host.appendChild) return noop;
      if (host.classList) host.classList.add('sc-host');
      var familyList = host.querySelector ? host.querySelector('.home-families') : null;
      var panel = h('div', 'sc');
      panel.setAttribute('aria-hidden', 'true');
      panel.inert = true;
      host.appendChild(panel);
      var shown = null, opened = Object.create(null), doctrineRow = null, caps = Object.create(null), lean = false, bare = false, fold = false;

      // The family list follows the ring's order, each row lighting its
      // sector and opening it; a modified click still opens the family page.
      function wireRows() {
        if (!familyList || !familyList.querySelectorAll || !ring) return;
        var byId = Object.create(null);
        Array.prototype.forEach.call(familyList.querySelectorAll('.home-family[data-system-family]'), function (li) {
          byId[li.getAttribute('data-system-family')] = li;
        });
        ring.order.forEach(function (fi) {
          var F = model.families[fi], li = byId[F.id];
          if (!li) return;
          familyList.appendChild(li);
          var link = li.querySelector ? li.querySelector('a') : null;
          li.setAttribute('data-sm-key', 'fam:' + F.key);
          li.addEventListener('pointerenter', function (e) { if (!(e && e.pointerType === 'touch') && at.level === 'system') setHover('fam:' + F.key, map && map.anchorOf('fam:' + F.key)); });
          li.addEventListener('pointerleave', function () { if (hoverKey === 'fam:' + F.key) setHover(null); });
          if (link) {
            link.addEventListener('focus', function () { if (at.level === 'system') setHover('fam:' + F.key, map && map.anchorOf('fam:' + F.key)); });
            link.addEventListener('blur', function () { if (hoverKey === 'fam:' + F.key) setHover(null); });
            link.addEventListener('click', function (e) {
              if (e && (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button > 0)) return;
              // A second click on the family already chosen follows the
              // row's own link to the family's page.
              if (at.level === 'family' && at.fam === fi) return;
              if (e && e.preventDefault) e.preventDefault();
              goFamily(fi, { keyed: keyedClick(e) });
            });
          }
        });
        if (familyList.classList) familyList.classList.add('is-live');
      }
      // The way into the doctrine, under the families.
      function wireDoctrineRow() {
        if (!familyList || doctrineRow || !D) return;
        doctrineRow = h('p', 'sc-doctrine');
        var b = button('sc-doctrine__go');
        b.setAttribute('data-sm-key', 'doctrine');
        b.appendChild(h('span', 'sc-doctrine__name', 'The doctrine at the centre'));
        b.appendChild(h('span', 'sc-doctrine__count', D.axioms.length + ' axioms, ' + D.principles.length + ' principles, ' + D.failures.length + ' failure modes'));
        b.addEventListener('click', function (e) { goDoctrine(null, { keyed: keyedClick(e) }); });
        b.addEventListener('pointerenter', function () { if (at.level === 'system') setHover('doctrine', map && map.anchorOf('doctrine')); });
        b.addEventListener('pointerleave', function () { if (hoverKey === 'doctrine') setHover(null); });
        doctrineRow.appendChild(b);
        if (familyList.parentNode) familyList.parentNode.insertBefore(doctrineRow, familyList.nextSibling || null);
      }

      function line(cls, text) { return h('p', cls, text); }
      // primary: true, or a weight ('primary', 'secondary', 'quiet'): the
      // explorer's ways out are of unequal weight, its page first.
      function goLink(href, text, primary) {
        var weight = primary === true ? 'primary' : primary || '';
        var a = h('a', 'sc__go' + (weight ? ' sc__go--' + weight : ''), text);
        a.setAttribute('href', href);
        if (/^https?:/i.test(href)) a.setAttribute('rel', 'noopener');
        return a;
      }
      function actions(links) {
        var p = h('p', 'sc__actions');
        links.forEach(function (a) { if (a) p.appendChild(a); });
        return p.firstChild ? p : null;
      }
      // One name to a line: pressed, it goes there; pointed at, its mark on
      // the map lights and says its name.
      function item(key, text, note, onPress, opts) {
        opts = opts || {};
        var li = h('li', 'sc__li');
        var b = button('sc__item' + (opts.cls ? ' ' + opts.cls : ''));
        b.setAttribute('data-sm-key', key);
        if (opts.glyph !== undefined || opts.rule) {
          var mk = h('span', 'sc__mk' + (opts.rule ? ' sc__mk--rule' : ''));
          mk.setAttribute('aria-hidden', 'true');
          mk.innerHTML = opts.rule ? doctrineSvg(opts.rule) : glyphSvg(opts.glyph);
          b.appendChild(mk);
        }
        var body = h('span', 'sc__item-text');
        body.appendChild(h('span', 'sc__item-name', text));
        if (note) body.appendChild(h('span', 'sc__item-note', note));
        b.appendChild(body);
        // Where a test shows the rule holding here: a small frame at the
        // row's end, solid where it is enforced, broken where a part of it
        // is checked, as the map frames its glyph.
        if (opts.held) b.appendChild(h('span', 'sc__held sc__held--' + opts.held, opts.held === 'full' ? 'Enforced here' : 'Partly checked here'));
        b.addEventListener('click', function (e) { onPress(e); });
        b.addEventListener('pointerenter', function () { pulse(key, opts.rel); });
        b.addEventListener('pointerleave', function () { unpulse(key); });
        b.addEventListener('focus', function () { pulse(key, opts.rel); });
        b.addEventListener('blur', function () { unpulse(key); });
        li.appendChild(b);
        return li;
      }
      // A row pointed at finds its mark: the mark's ring closes once, the
      // map names it and singles out its lines to what is chosen, and the
      // readout says what it is.
      // rel: the one relation a connection's row reads, so the drawing
      // singles out that line alone and the readout says that sentence.
      function pulse(key, rel) {
        var n = map && map.nodeOf(key);
        if (!n) return;
        n.classList.add('is-pulse');
        setHover(key, n, rel);
      }
      function unpulse(key) {
        var n = map && map.nodeOf(key);
        if (n) n.classList.remove('is-pulse');
        if (hoverKey === key) setHover(null);
        else hideTip();
      }
      function list(label, items, capKey, count, two) {
        var wrap = h('div', 'sc__block');
        // A list under a section's own title needs no label of its own.
        if (label !== null) {
          var headEl = h('p', 'sc__label');
          headEl.appendChild(h('span', null, label));
          headEl.appendChild(h('span', 'sc__label-n', ' · ' + (count === undefined ? items.length : count)));
          wrap.appendChild(headEl);
        }
        var ul = h('ul', 'sc__list' + (two && items.length > 1 ? ' sc__list--two' : ''));
        var cap = capKey && caps[capKey] !== undefined ? caps[capKey] : 8;
        var open = explorer || !capKey || opened[capKey] || items.length <= cap + 1, showN = open ? items.length : cap;
        items.slice(0, showN).forEach(function (li) { ul.appendChild(li); });
        if (capKey && opened[capKey] && items.length > cap) wrap.setAttribute('data-opened', '1');
        if (capKey && !opened[capKey] && !explorer) {
          wrap.setAttribute('data-shown', String(showN));
          wrap.setAttribute('data-total', String(items.length));
          wrap.setAttribute('data-rows', String(two && items.length > 1 ? Math.ceil(showN / 2) : showN));
          // The rules a component's paper module cites give way last.
          wrap.setAttribute('data-trim', /^cites:/.test(capKey) ? '2' : '1');
        }
        wrap.appendChild(ul);
        if (!open) {
          var more = button('sc__all', 'Show all ' + items.length);
          more.addEventListener('click', function (e) {
            opened[capKey] = true;
            var keyedIt = keyedClick(e);
            rebuild();
            if (keyedIt && shown && shown.node.querySelector) {
              var again = shown.node.querySelector('[data-cap="' + capKey + '"] .sc__li:nth-child(' + ((caps[capKey] !== undefined ? caps[capKey] : 8) + 1) + ') .sc__item');
              if (again && again.focus) again.focus();
            }
          });
          wrap.appendChild(more);
        }
        wrap.setAttribute('data-cap', capKey || '');
        return wrap;
      }
      function page(kind) { return h('div', 'sc__page sc__page--' + kind); }
      // The page's lists: in the column, a box of their own that scrolls; in
      // the explorer, the panel's body scrolls them with the rest.
      function scroller(node) {
        var sc = h('div', explorer ? 'sc__flow' : 'sc__scroll');
        if (!explorer) sc.setAttribute('tabindex', '0');
        node.appendChild(sc);
        return sc;
      }
      // A page's title: the explorer's panel has the page's one h1 above it.
      function titleOf(text) { return h(explorer ? 'h2' : 'h3', 'sc__title', text); }
      // What the map shows for this view, in one plain sentence (in the
      // explorer, where the stage carries no caption).
      function onMap(headEl) {
        if (!explorer) return;
        var said = captionParts()[1];
        if (said) headEl.appendChild(line('sc__onmap', 'On the map: ' + said));
      }
      function compItem(x, note) {
        var n = model.comps[x];
        return item('comp:' + n.id, n.label, note === undefined ? (bare ? null : model.families[n.fam].title) : note,
          function (e) { goComponent(x, { keyed: keyedClick(e) }); }, { glyph: n.cls });
      }
      // A code connection: the other component, the ways the code joins
      // them, and a link to the line of code that does it.
      function codeItem(ci, x, note) {
        var li = compItem(x, note), href = codeHref(ci, x);
        if (!href) return li;
        if (li.classList) li.classList.add('sc__li--code');
        var a = h('a', 'sc__code', 'Code');
        a.setAttribute('href', href);
        a.setAttribute('target', '_blank');
        a.setAttribute('rel', 'noopener');
        a.setAttribute('aria-label', 'The code file joining ' + model.comps[ci].label + ' and ' + model.comps[x].label);
        li.appendChild(a);
        return li;
      }
      // Rule names short enough to stand two to a row in the column.
      function shortNames(ids) {
        var wide = host && host.getBoundingClientRect ? host.getBoundingClientRect().width : 0;
        return wide >= 400 && ids.every(function (id) { return D.rules[id].title.length <= Math.floor(wide / 16.5); });
      }
      // held: 'full' or 'part' where a test shows the rule holding in the
      // component the page is about.
      function ruleItem(id, note, held) {
        return item('rule:' + id, D.rules[id].title, note || null, function (e) { goDoctrine(id, { keyed: keyedClick(e) }); },
          { cls: 'sc__item--rule', rule: D.rules[id].kind, held: held || null });
      }
      function ordered(ids, order) {
        var p = positions(order);
        return ids.slice().sort(function (a, b) { return p[a] - p[b]; });
      }
      function byFamily(ids) {
        var pos = positions(ring.order);
        return ids.slice().sort(function (a, b) {
          return pos[model.comps[a].fam] - pos[model.comps[b].fam] || byText(model.comps[a].label, model.comps[b].label);
        });
      }

      function famPage(fi) {
        var F = model.families[fi];
        var node = page('fam');
        var headEl = h('div', 'sc__head');
        headEl.appendChild(line('sc__kicker', 'Family · ' + countWords(F.members.length, 'component', 'components')));
        headEl.appendChild(titleOf(F.title));
        if (F.summary) headEl.appendChild(line('sc__lede', F.summary));
        var to = 0, from = 0, partners = [];
        model.pairs.forEach(function (p) {
          if (p.a !== fi && p.b !== fi) return;
          var other = p.a === fi ? p.b : p.a, out = p.a === fi ? p.ab : p.ba, inn = p.a === fi ? p.ba : p.ab;
          to += out; from += inn;
          partners.push({ fam: other, out: out, inn: inn, n: p.n });
        });
        headEl.appendChild(line('sc__meta', capital(countFigure(F.inside, linkNoun(1), linkNoun(2))) + ' among its components; ' +
          countFigure(to, linkNoun(1), linkNoun(2)) + ' to other families and ' + countFigure(from, linkNoun(1), linkNoun(2)) + ' from them.' +
          (function () {
            if (!unconnected()) return '';
            var none = F.members.filter(function (ci) { return !model.comps[ci].out.length && !model.comps[ci].inc.length; }).length;
            return none === F.members.length ? ' None of its components has one.' : none ? ' ' + none + ' of its ' + F.members.length + ' components ' + (none === 1 ? 'has' : 'have') + ' none.' : '';
          })()));
        node.appendChild(headEl);
        var act = actions([F.page ? goLink(F.page, 'Family page', true) : null]);
        if (act) node.appendChild(act);
        var sc = scroller(node);
        onMap(sc);
        sc.appendChild(list('Its components', F.members.map(function (ci) { return compItem(ci, null); }), 'fam:' + fi));
        partners.sort(function (p, q) { return q.n - p.n; });
        if (partners.length) {
          sc.appendChild(list(capital(linkNoun(2)) + ' with other families', partners.map(function (p) {
            var G = model.families[p.fam];
            return item('fam:' + G.key, G.title, p.out + ' to, ' + p.inn + ' from', function (e) { goFamily(p.fam, { keyed: keyedClick(e) }); });
          }), null));
        }
        sc.appendChild(line('sc__note', linkNote()));
        return node;
      }

      /* ---- The explorer's inspector (6 October 2026) ----
         A Type B review of the system view, with Will's go-ahead: a
         component with forty-two connections pushed the rules its paper
         module cites below a long scroll, each row repeated its family, and
         the whole doctrine was one list. Each choice now opens on a compact
         head (its title, what it does, how it is backed, its ways out of
         unequal weight) and one strip of views, so every relation is one
         step away whatever the length of the others. */
      var stripN = 0;
      // A strip of views over one page, with the tab behaviour readers know:
      // the arrows, Home and End move along it and show each view at once (a
      // view is already built, so showing it costs nothing), and Tab moves
      // on into the view.
      function viewStrip(label, list, current, pick) {
        var bar = h('div', 'sc__tabs'), strip = h('div', 'sc__tablist'), panels = Object.create(null), btns = [];
        var uid = 'sc' + mounted + '-' + (++stripN);
        strip.setAttribute('role', 'tablist');
        strip.setAttribute('aria-label', label);
        bar.appendChild(strip);
        list.forEach(function (t, i) {
          var b = button('sc__tab');
          b.setAttribute('role', 'tab');
          b.setAttribute('id', uid + '-' + t.id);
          b.setAttribute('aria-controls', uid + '-' + t.id + '-panel');
          b.setAttribute('data-view', t.id);
          b.appendChild(h('span', 'sc__tab-name', t.text));
          if (t.n !== undefined && t.n !== null) b.appendChild(h('span', 'sc__tab-n', String(t.n)));
          var p = h('div', 'sc__panel sc__panel--' + t.id);
          p.setAttribute('role', 'tabpanel');
          p.setAttribute('id', uid + '-' + t.id + '-panel');
          p.setAttribute('aria-labelledby', uid + '-' + t.id);
          panels[t.id] = p;
          btns.push(b);
          b.addEventListener('click', function () { show(t.id, true); });
          b.addEventListener('keydown', function (e) {
            var n = btns.length, to = e.key === 'ArrowRight' ? (i + 1) % n : e.key === 'ArrowLeft' ? (i - 1 + n) % n :
              e.key === 'Home' ? 0 : e.key === 'End' ? n - 1 : -1;
            if (to < 0) return;
            if (e.preventDefault) e.preventDefault();
            if (e.stopPropagation) e.stopPropagation();
            show(list[to].id, true);
            if (btns[to].focus) btns[to].focus();
          });
          strip.appendChild(b);
        });
        function show(id, user) {
          if (!panels[id]) id = list[0].id;
          list.forEach(function (t, i) {
            var on = t.id === id;
            btns[i].setAttribute('aria-selected', on ? 'true' : 'false');
            btns[i].setAttribute('tabindex', on ? '0' : '-1');
            panels[t.id].hidden = !on;
          });
          if (user) pick(id);
          return id;
        }
        var shownId = show(current, false);
        return {
          el: bar, panels: panels, first: shownId,
          show: function (id, keyedIt) { show(id, true); var b = btns[list.map(function (t) { return t.id; }).indexOf(id)]; if (keyedIt && b && b.focus) b.focus(); },
          // A tab's count, while a find narrows what it holds.
          count: function (id, text) {
            var b = btns[list.map(function (t) { return t.id; }).indexOf(id)], n = b && b.querySelector ? b.querySelector('.sc__tab-n') : null;
            if (n) n.textContent = text;
          }
        };
      }
      function findText(v) { return String(v || '').toLowerCase().replace(/\s+/g, ' ').trim(); }
      // A find over one list: what is typed is kept with the choice (so it
      // survives full screen and the panel folded), Escape in the box clears
      // it, and a line under it says how many of the list it shows.
      function finder(label, stateKey, apply) {
        var wrap = h('div', 'sc__find');
        var uid = 'sc' + mounted + '-find-' + (++stripN);
        var lab = h('label', 'sc__find-label', label);
        lab.setAttribute('for', uid);
        var input = h('input', 'sc__find-input');
        input.setAttribute('type', 'search');
        input.setAttribute('id', uid);
        input.setAttribute('autocomplete', 'off');
        input.setAttribute('spellcheck', 'false');
        input.setAttribute('placeholder', label);
        input.setAttribute('aria-describedby', uid + '-n');
        var said = h('p', 'sc__find-n');
        said.setAttribute('id', uid + '-n');
        said.setAttribute('aria-live', 'polite');
        input.value = inspect.find[stateKey] || '';
        function run() {
          inspect.find[stateKey] = input.value;
          said.textContent = apply(findText(input.value)) || '';
        }
        input.addEventListener('input', run);
        input.addEventListener('keydown', function (e) {
          if (e.key !== 'Escape' || !input.value) return;
          if (e.preventDefault) e.preventDefault();
          if (e.stopPropagation) e.stopPropagation();
          input.value = '';
          run();
        });
        wrap.appendChild(lab);
        wrap.appendChild(input);
        wrap.appendChild(said);
        return { el: wrap, input: input, run: run };
      }
      // The rules a component's paper module cites, in the manifest's order:
      // its principles, then its axioms.
      function citedOf(info) {
        if (!info || !D) return [];
        var L = D.listed || { principle: D.principles, axiom: D.axioms };
        return L.principle.filter(function (id) { return info.gov.indexOf(id) >= 0; })
          .concat(L.axiom.filter(function (id) { return info.abide.indexOf(id) >= 0; }));
      }
      function listedOf(kind) { return (D.listed && D.listed[kind]) || (kind === 'axiom' ? D.axioms : kind === 'principle' ? D.principles : D.failures); }
      function inListed(ids) {
        var order = listedOf('axiom').concat(listedOf('principle'), listedOf('failure')), p = positions(order);
        return ids.slice().sort(function (a, b) { return p[a] - p[b]; });
      }
      // The narrowing the panel asks of the drawing: the connections a family
      // chosen to stand alone and a find keep, and the rules a find keeps,
      // with the words of its label in the strip of views.
      function renarrow(ci, wantFocus) {
        var c = model.comps[ci], selKey = 'comp:' + c.id, rels = relationsOf(ci);
        var sc = inspect.scope && inspect.scope.key === selKey ? inspect.scope : null;
        var q = findText(inspect.find[selKey + '|code']), rq = findText(inspect.find[selKey + '|rules']);
        var N = { key: selKey, links: null, rules: null, text: null, total: rels.length };
        if (sc || q) {
          var kept = rels.filter(function (x) {
            if (sc && !(x.kind === sc.kind && x.dir === sc.dir && x.fam === sc.fam)) return false;
            return !q || codeMatch(x, q);
          });
          N.links = kept.map(function (x) { return x.k; });
          var bits = [];
          if (sc) bits.push(lowerFirst(RELATION_WORDS[sc.kind][sc.dir]) + ' ' + model.families[sc.fam].title);
          if (q) bits.push('matching “' + inspect.find[selKey + '|code'].trim() + '”');
          N.text = 'The map shows ' + kept.length + ' of ' + rels.length + ' ' + linkNoun(rels.length) + ': ' + bits.join(', ') + '.';
        }
        if (rq && D && D.comp[ci]) {
          var info = D.comp[ci], all = citedOf(info);
          N.rules = all.filter(function (id) { return findText(D.rules[id].title).indexOf(rq) >= 0; });
          var rt = N.rules.length + ' of the ' + all.length + ' ' + plural(all.length, 'rule', 'rules') + ' its paper module cites, matching “' + inspect.find[selKey + '|rules'].trim() + '”.';
          N.text = N.text ? N.text + ' And ' + rt : 'The map shows ' + rt;
        }
        var next = N.links || N.rules ? N : null, was = narrowNow();
        inspect.narrow = next;
        syncScope();
        // The drawing answers only a narrowing that changed.
        var sig = function (x) { return x ? (x.links || []).join(',') + '|' + (x.rules || []).join(',') : ''; };
        if (map && sig(was) !== sig(next)) map.inspect();
        if (wantFocus) wantFocus();
      }
      function codeMatch(x, q) {
        return findText(model.comps[x.other].label).indexOf(q) >= 0 || findText(model.families[x.fam].title).indexOf(q) >= 0;
      }
      // A code connection's row: the component at the other end (pointed at,
      // the drawing draws this one relation whole; pressed, the map goes
      // there), and, quieter, the source file whose code establishes it.
      function codeRow(ci, x) {
        var n = model.comps[x.other];
        var li = item('comp:' + n.id, n.label, null, function (e) { goComponent(x.other, { keyed: keyedClick(e) }); },
          { glyph: n.cls, rel: { kind: x.kind, dir: x.dir } });
        li.setAttribute('data-k', String(x.k));
        if (x.href) {
          var path = model.links[x.k].ev.path;
          if (li.classList) li.classList.add('sc__li--code');
          var a = h('a', 'sc__code', 'Source file');
          a.setAttribute('href', x.href);
          a.setAttribute('target', '_blank');
          a.setAttribute('rel', 'noopener');
          a.setAttribute('title', path);
          a.setAttribute('aria-label', 'Source file establishing this connection, on GitHub: ' + path.split('/').pop());
          li.appendChild(a);
        }
        return li;
      }

      /* A component in the explorer. Its head is compact and stays the same
         in every view: its title (its family is the trail above it, once),
         what it does in a sentence, how it is backed, and its ways out by
         weight (its component page, then its paper module, then its source).
         Under it one strip of views: an overview (a short account of its
         relations, each a way to its view, and its whole description), its
         code connections, and the rules its paper module cites. The
         connections stand under their verbs, out before in, and under each
         verb by family round the ring, in the scene's order; a family's
         heading shows its connections alone on the drawing, and a find
         narrows a long list and the drawing together. A component with no
         connection keeps the view, which says so in a sentence and leads to
         its rules. The views are kept from one component to the next. */
      function compReading(ci) {
        var c = model.comps[ci], info = D ? D.comp[ci] : null, selKey = 'comp:' + c.id;
        if (info && info.missing) info = null;
        var node = page('comp');
        var headEl = h('div', 'sc__head');
        headEl.appendChild(titleOf(c.label));
        if (c.line) headEl.appendChild(line('sc__lede', c.line));
        if (c.cls || c.basis) {
          var meta = line('sc__meta sc__meta--mark', '');
          if (c.cls) {
            var gm = h('span', 'sc__mk');
            gm.setAttribute('aria-hidden', 'true');
            gm.innerHTML = glyphSvg(c.cls);
            meta.appendChild(gm);
          }
          meta.appendChild(h('span', null, ((c.cls ? CLASS_WORDS[c.cls] + '.' : '') + (c.basis ? ' Evidence: ' + lowerFirst(c.basis) + '.' : '')).trim()));
          headEl.appendChild(meta);
        }
        node.appendChild(headEl);
        var act = actions([
          c.page ? goLink(c.page, 'Component page', 'primary') : null,
          c.reader ? goLink(c.reader, 'Paper module', c.page ? 'secondary' : 'primary') : null,
          c.source ? goLink(c.source, /^https:\/\/github\.com\//i.test(c.source) ? 'Source on GitHub' : 'Source', 'quiet') : null
        ]);
        if (act) node.appendChild(act);
        var flow = scroller(node);
        var groups = relationGroups(ci), total = 0;
        groups.forEach(function (g) { total += g.rels.length; });
        var cited = citedOf(info), source = lowerFirst(info && info.source || 'paper module');
        var views = [{ id: 'overview', text: 'Overview' }, { id: 'code', text: onlyNamed() ? 'Relations' : 'Connections', n: total }];
        if (info) views.push({ id: 'rules', text: 'Rules', n: cited.length });
        var strip = viewStrip('Views of ' + c.label, views, inspect.view, function (v) { inspect.view = v; if (map) map.inspect(); });
        flow.appendChild(strip.el);

        // Overview: its relations in a few lines, each a way to its view.
        var ov = strip.panels.overview, sum = h('ul', 'sc__sum');
        function sumRow(view, big, small) {
          var li = h('li', 'sc__sum-li'), b = button('sc__sum-go sc__sum-go--' + view);
          b.setAttribute('data-to-view', view);
          b.appendChild(h('span', 'sc__sum-big', big));
          small.forEach(function (s) { if (s) b.appendChild(h('span', 'sc__sum-small', s)); });
          b.addEventListener('click', function (e) { strip.show(view, keyedClick(e)); });
          li.appendChild(b);
          sum.appendChild(li);
        }
        sumRow('code', total ? capital(countFigure(total, linkNoun(1), linkNoun(2))) : onlyNamed() ? 'No listed relations' : 'No code connections',
          groups.map(function (g) { return RELATION_WORDS[g.kind][g.dir] + ' ' + countFigure(g.rels.length, 'component', 'components'); }));
        if (info) {
          sumRow('rules', capital(countFigure(cited.length, 'rule', 'rules')) + ' its ' + source + ' cites', [
            info.enforces.length ? 'Enforced here by a test: ' + countFigure(info.enforces.length, 'rule', 'rules') : null,
            info.partly.length ? 'Partly checked here by a test: ' + countFigure(info.partly.length, 'rule', 'rules') : null
          ]);
        }
        ov.appendChild(sum);
        var what = trimProse(c.what, 1e6);
        if (what && what !== c.line) {
          var about = h('section', 'sc__section sc__section--about');
          about.appendChild(h('h3', 'sc__section-title', 'What it does'));
          about.appendChild(line('sc__body', what));
          ov.appendChild(about);
        }

        // Connections, under their verbs, then by family.
        var cp = strip.panels.code, rows = [], fams = [], secs = [];
        if (!total) {
          cp.appendChild(line('sc__zero', onlyNamed() ? 'Its record lists no related components.' : 'No code connections of the kinds the map draws.'));
          if (!onlyNamed()) cp.appendChild(line('sc__note', 'Its code does not run another component, read another’s saved results or check another’s copied files, and no other component’s code does any of these to it.'));
          if (info) {
            var jump = button('sc__jump', capital(countFigure(cited.length, 'rule', 'rules')) + ' its ' + source + ' cites');
            jump.addEventListener('click', function (e) { strip.show('rules', keyedClick(e)); });
            cp.appendChild(jump);
          }
        } else {
          cp.appendChild(line('sc__onmap', 'On the map: each in red, its texture its kind. Point at a row to draw that one connection whole; choose a family to show its connections alone.'));
          var f = total >= 8 ? finder('Filter these ' + linkNoun(2), selKey + '|code', function (q) {
            var shown = 0;
            rows.forEach(function (r) { var on = !q || codeMatch(r.x, q); r.li.hidden = !on; if (on) shown++; });
            fams.forEach(function (fr) { fr.wrap.hidden = !fr.rows.some(function (r) { return !r.li.hidden; }); });
            secs.forEach(function (sr) { sr.el.hidden = !sr.rows.some(function (r) { return !r.li.hidden; }); });
            renarrow(ci);
            return q ? 'Showing ' + shown + ' of ' + total + ' ' + linkNoun(total) + '.' : '';
          }) : null;
          if (f) cp.appendChild(f.el);
          groups.forEach(function (g) {
            var sec = h('section', 'sc__rel'), mine = [];
            var title = h('h3', 'sc__rel-title');
            title.appendChild(h('span', null, RELATION_WORDS[g.kind][g.dir]));
            title.appendChild(h('span', 'sc__label-n', ' · ' + g.rels.length));
            sec.appendChild(title);
            ring.order.forEach(function (fi) {
              var those = g.rels.filter(function (x) { return x.fam === fi; });
              if (!those.length) return;
              var wrap = h('div', 'sc__famgroup'), F = model.families[fi];
              var fb = button('sc__fam');
              var on = !!inspect.scope && inspect.scope.key === selKey && inspect.scope.kind === g.kind && inspect.scope.dir === g.dir && inspect.scope.fam === fi;
              fb.setAttribute('aria-pressed', on ? 'true' : 'false');
              fb.setAttribute('data-sm-key', 'fam:' + F.key);
              fb.setAttribute('title', 'Show only these ' + countFigure(those.length, linkNoun(1), linkNoun(2)) + ' on the map');
              fb.appendChild(h('span', 'sc__fam-name', F.title));
              fb.appendChild(h('span', 'sc__fam-n', String(those.length)));
              fb.addEventListener('click', function (e) {
                var was = fb.getAttribute('aria-pressed') === 'true';
                inspect.scope = was ? null : { key: selKey, kind: g.kind, dir: g.dir, fam: fi };
                fams.forEach(function (fr) { fr.btn.setAttribute('aria-pressed', !was && fr.btn === fb ? 'true' : 'false'); });
                renarrow(ci);
                if (keyedClick(e) && fb.focus) fb.focus();
              });
              wrap.appendChild(fb);
              var ul = h('ul', 'sc__list sc__list--code'), rws = [];
              those.forEach(function (x) {
                var li = codeRow(ci, x), r = { li: li, x: x };
                rows.push(r); rws.push(r); mine.push(r);
                ul.appendChild(li);
              });
              wrap.appendChild(ul);
              sec.appendChild(wrap);
              fams.push({ btn: fb, wrap: wrap, rows: rws });
            });
            cp.appendChild(sec);
            secs.push({ el: sec, rows: mine });
          });
          cp.appendChild(line('sc__note', onlyNamed() ? linkNote() : model.codeBase && model.links.some(function (l) { return !!l.ev; }) ?
            'Each is derived from the code. Source file opens the file whose code establishes that connection.' : 'Each connection is derived from the code.'));
          if (f) f.run();
        }

        // The rules its paper module cites, in the doctrine's ink.
        if (info) {
          var rp = strip.panels.rules, rrows = [];
          rp.appendChild(h('h3', 'sc__section-title sc__rules-title', 'Rules its ' + source + ' cites' + (cited.length ? ' · ' + cited.length : '')));
          if (cited.length) rp.appendChild(line('sc__onmap', 'On the map: an azure line to each. A frame round a rule’s mark is a test showing it here: four corners where it is enforced, two where a part of it is checked.'));
          var rf = cited.length >= 10 ? finder('Filter these rules', selKey + '|rules', function (q) {
            var shown = 0;
            rrows.forEach(function (r) { var on = !q || findText(D.rules[r.id].title).indexOf(q) >= 0; r.li.hidden = !on; if (on) shown++; });
            renarrow(ci);
            return q ? 'Showing ' + shown + ' of ' + cited.length + ' ' + plural(cited.length, 'rule', 'rules') + '.' : '';
          }) : null;
          if (rf) rp.appendChild(rf.el);
          if (cited.length) {
            var ul2 = h('ul', 'sc__list sc__list--rules');
            cited.forEach(function (id) {
              var li = ruleItem(id, null, heldIn(ci, id));
              rrows.push({ li: li, id: id });
              ul2.appendChild(li);
            });
            var blk = h('div', 'sc__block');
            blk.appendChild(ul2);
            rp.appendChild(blk);
          } else rp.appendChild(line('sc__note', 'Its ' + source + ' cites no rule.'));
          [['enforces', 'Also enforced here'], ['partly', 'Also partly checked here']].forEach(function (pair) {
            var extra = info[pair[0]].filter(function (id) { return cited.indexOf(id) < 0; });
            if (extra.length) rp.appendChild(list(pair[1], inListed(extra).map(function (id) {
              return ruleItem(id, KIND_WORDS[D.rules[id].kind]);
            }), null));
          });
          var held = info.enforces.length + info.partly.length;
          if (byTests()) {
            var note = h('div', 'sc__heldnote');
            if (info.enforces.length) note.appendChild(line('sc__note', HELD_WORDS.full));
            if (info.partly.length) note.appendChild(line('sc__note', HELD_WORDS.part));
            note.appendChild(line('sc__note', held ? 'A citation is what its ' + source + ' refers to; only a test marks a rule enforced or partly checked here.' :
              'No test marks any rule here. A citation is what its ' + source + ' refers to.'));
            if (held && c.page) {
              var rec = h('p', 'sc__note sc__note--go');
              rec.appendChild(goLink(c.page.replace(/#.*$/, '') + '#evidence', 'Its evidence record', 'quiet'));
              note.appendChild(rec);
            }
            rp.appendChild(note);
          } else rp.appendChild(line('sc__note', 'Where a rule is enforced is what its doctrine card names.'));
          if (rf) rf.run();
        }
        renarrow(ci);
        var flowPanels = [strip.panels.overview, strip.panels.code];
        if (info) flowPanels.push(strip.panels.rules);
        flowPanels.forEach(function (p) { flow.appendChild(p); });
        return node;
      }

      /* The doctrine in the explorer: its three kinds as three views (the
         axioms, the principles, the failure modes, each in the manifest's
         order), one find over all of them, and how the diagram is arranged
         in a note at the end. The kind open here is the one named on the
         drawing. */
      function doctrineCatalogue() {
        var node = page('doctrine');
        var headEl = h('div', 'sc__head');
        headEl.appendChild(line('sc__kicker sc__kicker--doctrine', 'At the centre'));
        headEl.appendChild(titleOf('The doctrine'));
        headEl.appendChild(line('sc__lede', 'The rules the system is built on. A principle rests on axioms and a failure mode threatens them.'));
        node.appendChild(headEl);
        var flow = scroller(node);
        var cats = [{ id: 'axiom', text: 'Axioms', many: 'axioms', one: 'axiom' }, { id: 'principle', text: 'Principles', many: 'principles', one: 'principle' },
                    { id: 'failure', text: 'Failure modes', many: 'failure modes', one: 'failure mode' }];
        var rows = { axiom: [], principle: [], failure: [] };
        var strip = viewStrip('The doctrine’s rules by kind', cats.map(function (k) { return { id: k.id, text: k.text, n: listedOf(k.id).length }; }), inspect.cat,
          function (v) { inspect.cat = v; if (map) map.inspect(); if (f) f.run(); });
        flow.appendChild(strip.el);
        var f = finder('Find a rule or failure mode', 'doctrine', function (q) {
          var found = {};
          cats.forEach(function (k) {
            var n = 0;
            rows[k.id].forEach(function (r) { var on = !q || findText(D.rules[r.id].title).indexOf(q) >= 0; r.li.hidden = !on; if (on) n++; });
            found[k.id] = n;
            strip.count(k.id, q ? n + ' of ' + listedOf(k.id).length : String(listedOf(k.id).length));
          });
          if (!q) return '';
          var here = cats.filter(function (k) { return k.id === inspect.cat; })[0];
          var say = capital(numberWord(found[here.id])) + ' of the ' + listedOf(here.id).length + ' ' + here.many + ' ' + (found[here.id] === 1 ? 'matches' : 'match') + '.';
          var else_ = cats.filter(function (k) { return k.id !== here.id && found[k.id]; }).map(function (k) { return countFigure(found[k.id], k.one, k.many); });
          return say + (else_.length ? ' Also ' + andList(else_) + ' under ' + (else_.length > 1 ? 'their own views' : 'its own view') + '.' : '');
        });
        flow.appendChild(f.el);
        cats.forEach(function (k) {
          var p = strip.panels[k.id], ul = h('ul', 'sc__list sc__list--doctrine');
          listedOf(k.id).forEach(function (id) {
            var li = ruleItem(id);
            rows[k.id].push({ li: li, id: id });
            ul.appendChild(li);
          });
          p.appendChild(ul);
          flow.appendChild(p);
        });
        var how = h('details', 'sc__how');
        var sum = h('summary', 'sc__how-summary', 'How this diagram is arranged');
        how.appendChild(sum);
        how.appendChild(line('sc__body', capital(countWords(D.axioms.length, 'axiom', 'axioms')) + ' stand on a ring at the centre. A rule tied to one axiom sits just outside it; a rule tied to several stands on the ring between them. ' +
          'A fine line joins a principle to each axiom it rests on, and a dotted line joins a failure mode to each axiom it threatens. The components round the rim stay as they are.'));
        how.appendChild(line('sc__body', byTests() ? 'A rule is marked enforced in a component only where a test shows it.' : 'Each rule’s doctrine card names the components where it is enforced.'));
        flow.appendChild(how);
        f.run();
        return node;
      }

      // Where a rule stands in a component: its row, and, quieter, the
      // component's evidence record, which gives its evidence and the limits
      // of its scope.
      function evidenceRow(ci) {
        var li = compItem(ci, null), c = model.comps[ci];
        if (c.page) {
          if (li.classList) li.classList.add('sc__li--code');
          var a = h('a', 'sc__code', 'Evidence record');
          a.setAttribute('href', c.page.replace(/#.*$/, '') + '#evidence');
          a.setAttribute('aria-label', 'Evidence record of ' + c.label);
          li.appendChild(a);
        }
        return li;
      }
      // Which components' paper modules cite a rule, by family; while none
      // is open the families run on, each a way to its components.
      function citeReach(id) {
        var r = D.rules[id], citing = [];
        D.comp.forEach(function (info, ci) {
          if ((r.kind === 'principle' ? info.gov : info.abide).indexOf(id) >= 0) citing.push(ci);
        });
        var wrap = h('div', 'sc__block');
        wrap.appendChild(line('sc__label', !citing.length ? 'No paper module cites it' : citing.length === 1 ? 'Cited by one component’s paper module' :
          'Cited by the paper modules of ' + citing.length + ' of ' + model.comps.length + ' components'));
        var anyOpen = ring.order.some(function (fi) { return !!opened['cite:' + id + ':' + fi]; });
        var foldKey = 'fams:' + id, folded = fold && citing.length > 0 && !anyOpen && !opened[foldKey];
        if (folded) {
          var unfold = button('sc__all', 'Show by family');
          unfold.addEventListener('click', function (e) { opened[foldKey] = true; rebuild(keyedClick(e) ? foldKey : null); });
          wrap.appendChild(unfold);
        }
        var groups = h('ul', 'sc__list' + (anyOpen ? '' : ' sc__list--flow'));
        ring.order.forEach(function (fi) {
          var mine = citing.filter(function (ci) { return model.comps[ci].fam === fi; });
          if (!mine.length) return;
          var li = h('li', 'sc__li sc__group');
          var key = 'cite:' + id + ':' + fi, isOpen = !!opened[key];
          var g = button('sc__item sc__group-btn');
          g.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
          g.setAttribute('data-sm-key', 'fam:' + model.families[fi].key);
          var txt = h('span', 'sc__item-text');
          txt.appendChild(h('span', 'sc__item-name', model.families[fi].title));
          txt.appendChild(h('span', 'sc__item-note', String(mine.length)));
          g.appendChild(txt);
          g.addEventListener('click', function (e) { opened[key] = !opened[key]; rebuild(keyedClick(e) ? key : null); });
          li.appendChild(g);
          if (isOpen) {
            var inner = h('ul', 'sc__list sc__list--inner');
            mine.sort(function (p, q) { return byText(model.comps[p].label, model.comps[q].label); })
              .forEach(function (ci) { inner.appendChild(compItem(ci, null)); });
            li.appendChild(inner);
          }
          groups.appendChild(li);
        });
        if (!folded) wrap.appendChild(groups);
        return wrap;
      }
      function partOf(cls, title) {
        var s = h('section', 'sc__section sc__section--' + cls);
        s.appendChild(h('h3', 'sc__section-title', title));
        return s;
      }
      /* A rule in the explorer, read in the order a reader asks of it: what
         it means; what it rests on and what threatens it, apart; where a
         test shows it in a component, enforced or a part of it checked,
         each component with its evidence record; and which components'
         paper modules cite it. Citation, enforcement and partial checking
         are three lists with three counts, and no count is read off the
         others. */
      function ruleReading(id) {
        var r = D.rules[id];
        var node = page('rule');
        var headEl = h('div', 'sc__head');
        headEl.appendChild(line('sc__kicker sc__kicker--doctrine', KIND_WORDS[r.kind]));
        headEl.appendChild(titleOf(r.title));
        if (r.plain) headEl.appendChild(line('sc__lede', r.plain));
        node.appendChild(headEl);
        var act = actions([r.doctrine ? goLink(r.doctrine, 'Read its doctrine card', true) : null]);
        if (act) node.appendChild(act);
        var flow = scroller(node);
        onMap(flow);
        var ties = partOf('ties', r.kind === 'principle' ? 'Foundations and threats' : r.kind === 'axiom' ? 'What rests on it and what threatens it' : 'What it threatens');
        if (r.kind === 'principle') {
          ties.appendChild(r.restsOn.length ? list('Rests on', inListed(r.restsOn).map(function (x) { return ruleItem(x); }), null) : line('sc__note', 'It rests on no axiom in the manifest.'));
          ties.appendChild(r.brokenBy.length ? list('Threatened by', inListed(r.brokenBy).map(function (x) { return ruleItem(x); }), null) : line('sc__note', 'No failure mode is recorded as threatening it.'));
        } else if (r.kind === 'axiom') {
          if (r.grounds.length) ties.appendChild(list('Principles that rest on it', inListed(r.grounds).map(function (x) { return ruleItem(x); }), null));
          if (r.threatenedBy.length) ties.appendChild(list('Failure modes that threaten it', inListed(r.threatenedBy).map(function (x) { return ruleItem(x); }), null));
        } else {
          if (r.guards.length) ties.appendChild(list('Axioms', inListed(r.guards).map(function (x) { return ruleItem(x); }), null));
          if (r.negates.length) ties.appendChild(list('Principles', inListed(r.negates).map(function (x) { return ruleItem(x); }), null));
        }
        flow.appendChild(ties);
        var ev = partOf('evidence', 'Evidence in components');
        if (byTests()) {
          if (r.enforced.length) ev.appendChild(list('Enforced in', byFamily(r.enforced).map(evidenceRow), null));
          if (r.partly.length) ev.appendChild(list('Partly checked in', byFamily(r.partly).map(evidenceRow), null));
          if (!r.enforced.length && !r.partly.length) ev.appendChild(line('sc__note', 'No test marks this rule in any component.'));
          else ev.appendChild(line('sc__note', 'Enforced: a test shows the rule’s core requirement in that component. Partly checked: a test shows a narrower part of it there. Each mark holds for that component alone.'));
        } else if (r.enforced.length) ev.appendChild(list('Enforced in, by its card', byFamily(r.enforced).map(function (x) { return compItem(x); }), null));
        if (r.namedOnly.length) {
          var quiet = list('Named in its doctrine card, not yet demonstrated by a test', byFamily(r.namedOnly).map(function (x) { return compItem(x); }), null);
          if (quiet.classList) quiet.classList.add('sc__block--quiet');
          ev.appendChild(quiet);
        }
        flow.appendChild(ev);
        if (r.kind !== 'failure') {
          var reach = partOf('reach', 'Citation reach');
          reach.appendChild(citeReach(id));
          reach.appendChild(line('sc__note', 'A citation is what a paper module refers to; it carries no test.'));
          flow.appendChild(reach);
        }
        return node;
      }

      function compPage(ci) {
        if (explorer) return compReading(ci);
        var c = model.comps[ci], F = model.families[c.fam], info = D ? D.comp[ci] : null;
        var node = page('comp');
        var headEl = h('div', 'sc__head');
        headEl.appendChild(line('sc__kicker', F.title));
        headEl.appendChild(h('h3', 'sc__title', c.label));
        if (c.line) headEl.appendChild(line('sc__lede', c.line));
        var what = trimProse(c.what, 170);
        if (what && what !== c.line && !lean) headEl.appendChild(line('sc__body', what));
        if (c.cls || c.basis) {
          var meta = line('sc__meta sc__meta--mark', '');
          if (c.cls) {
            var gm = h('span', 'sc__mk');
            gm.setAttribute('aria-hidden', 'true');
            gm.innerHTML = glyphSvg(c.cls);
            meta.appendChild(gm);
          }
          meta.appendChild(h('span', null, ((c.cls ? CLASS_WORDS[c.cls] + '.' : '') + (c.basis ? ' Evidence: ' + lowerFirst(c.basis) + '.' : '')).trim()));
          headEl.appendChild(meta);
        }
        node.appendChild(headEl);
        var act = actions([
          c.page ? goLink(c.page, 'Component page', true) : null,
          c.reader ? goLink(c.reader, 'Paper module', !c.page) : null,
          c.source ? goLink(c.source, 'Source', false) : null
        ]);
        if (act) node.appendChild(act);
        var sc = scroller(node);
        if (info) {
          var held = function (id) { return info.enforces.indexOf(id) >= 0 ? 'full' : info.partly.indexOf(id) >= 0 ? 'part' : null; };
          var noted = function (ids) { return ids.some(function (id) { return !!held(id); }); };
          // The principles and the axioms its paper module cites, in one list,
          // each with its own glyph, a rule shown holding here framed at the
          // row's end.
          var cited = ordered(info.gov, D.principles).concat(ordered(info.abide, D.axioms));
          if (cited.length) sc.appendChild(list('Its ' + lowerFirst(info.source || 'paper module') + ' cites', cited.map(function (id) { return ruleItem(id, null, held(id)); }),
            'cites:' + ci, undefined, !noted(cited) && shortNames(cited)));
          // Rules shown holding here that its paper module does not cite (the
          // failure modes it guards against, for the most part).
          [['enforces', 'Enforced here'], ['partly', 'Partly checked here']].forEach(function (pair) {
            var extra = info[pair[0]].filter(function (id) {
              var r = D.rules[id];
              return r.kind === 'failure' || (r.kind === 'principle' && info.gov.indexOf(id) < 0) || (r.kind === 'axiom' && info.abide.indexOf(id) < 0);
            });
            if (extra.length) sc.appendChild(list(pair[1], ordered(extra, D.axioms.concat(D.principles, D.failures)).map(function (id) {
              return ruleItem(id, KIND_WORDS[D.rules[id].kind]);
            }), pair[0] + ':' + ci));
          });
        }
        // The relations a record lists have no direction worth reading: one
        // list. Code connections are one list too, each component named once
        // with the ways the code connects them, from this component's side.
        var named = uniq(model.links.filter(function (l) { return l.kind === 'named' && (l[0] === ci || l[1] === ci); }).map(function (l) { return l[0] === ci ? l[1] : l[0]; }));
        if (named.length) sc.appendChild(list(LINK_WORDS.named.out, byFamily(named).map(function (x) { return compItem(x); }), 'named:' + ci));
        var ways = Object.create(null), others = [];
        LINK_ORDER.forEach(function (kind) {
          if (kind === 'named') return;
          model.links.forEach(function (l) {
            if (l.kind !== kind || (l[0] !== ci && l[1] !== ci)) return;
            var other = l[0] === ci ? l[1] : l[0], word = l[0] === ci ? LINK_WORDS[kind].out : LINK_WORDS[kind].inc;
            if (!ways[other]) { ways[other] = []; others.push(other); }
            if (ways[other].indexOf(word) < 0) ways[other].push(word);
          });
        });
        if (others.length) sc.appendChild(list('Code connections', byFamily(others).map(function (x) { return codeItem(ci, x, ways[x].join(' · ')); }), 'code:' + ci));
        if (!c.out.length && !c.inc.length) sc.appendChild(line('sc__note', onlyNamed() ? 'Its record lists no related components.' :
          'No code connections. Its code does not run, read or check another component, and no other component’s code runs, reads or checks it.'));
        else sc.appendChild(line('sc__note', linkNote()));
        return node;
      }

      function doctrinePage() {
        var node = page('doctrine');
        var headEl = h('div', 'sc__head');
        headEl.appendChild(line('sc__kicker sc__kicker--doctrine', 'At the centre'));
        headEl.appendChild(titleOf('The doctrine'));
        headEl.appendChild(line('sc__lede', 'The rules the system is built on. A principle rests on axioms and a failure mode threatens them. ' +
          'Tied to one axiom, it sits just outside it; tied to several, it stands on the ring between them. ' +
          (D.enforcedBy === 'tests' ? 'A rule is marked enforced in a component only where a test shows it.' :
            'Each rule’s doctrine card names the components where it is enforced.')));
        node.appendChild(headEl);
        var sc = scroller(node);
        sc.appendChild(list('Axioms', ordered(D.axioms, D.axioms).map(function (id) { return ruleItem(id); }), 'all:axioms', undefined, shortNames(D.axioms)));
        sc.appendChild(list('Principles', ordered(D.principles, D.principles).map(function (id) { return ruleItem(id); }), 'all:principles'));
        sc.appendChild(list('Failure modes', ordered(D.failures, D.failures).map(function (id) { return ruleItem(id); }), 'all:failures', undefined, shortNames(D.failures)));
        return node;
      }

      function rulePage(id) {
        var r = D.rules[id];
        var node = page('rule');
        var headEl = h('div', 'sc__head');
        headEl.appendChild(line('sc__kicker sc__kicker--doctrine', KIND_WORDS[r.kind]));
        headEl.appendChild(titleOf(r.title));
        if (r.plain) headEl.appendChild(line('sc__lede', r.plain));
        node.appendChild(headEl);
        var act = actions([r.doctrine ? goLink(r.doctrine, 'Read its doctrine card', true) : null]);
        if (act) node.appendChild(act);
        var sc = scroller(node);
        onMap(sc);
        if (r.kind === 'principle') {
          if (r.restsOn.length) sc.appendChild(list('Rests on', ordered(r.restsOn, D.axioms).map(function (x) { return ruleItem(x); }), null));
          if (r.brokenBy.length) sc.appendChild(list('Failure modes that threaten it', ordered(r.brokenBy, D.failures).map(function (x) { return ruleItem(x); }), 'thr:' + id, undefined, shortNames(r.brokenBy)));
        } else if (r.kind === 'axiom') {
          if (r.grounds.length) sc.appendChild(list('Principles that rest on it', ordered(r.grounds, D.principles).map(function (x) { return ruleItem(x); }), 'gr:' + id));
          if (r.threatenedBy.length) sc.appendChild(list('Failure modes that threaten it', ordered(r.threatenedBy, D.failures).map(function (x) { return ruleItem(x); }), 'thr:' + id, undefined, shortNames(r.threatenedBy)));
        } else {
          if (r.guards.length) sc.appendChild(list('Threatens these axioms', ordered(r.guards, D.axioms).map(function (x) { return ruleItem(x); }), null, undefined, shortNames(r.guards)));
          if (r.negates.length) sc.appendChild(list('Threatens these principles', ordered(r.negates, D.principles).map(function (x) { return ruleItem(x); }), 'neg:' + id));
        }
        if (r.enforced.length) sc.appendChild(list('Enforced in', byFamily(r.enforced).map(function (x) { return compItem(x); }), 'enf:' + id));
        if (r.partly.length) sc.appendChild(list('Partly checked in', byFamily(r.partly).map(function (x) { return compItem(x); }), 'part:' + id));
        // What the card names that no test shows yet: listed quietly, here
        // only, and never drawn in the map.
        if (r.namedOnly.length) {
          var quiet = list('Named in its doctrine card, not yet demonstrated by a test', byFamily(r.namedOnly).map(function (x) { return compItem(x); }), 'card:' + id);
          if (quiet.classList) quiet.classList.add('sc__block--quiet');
          sc.appendChild(quiet);
        }
        if (r.kind !== 'failure') {
          var citing = [];
          D.comp.forEach(function (info, ci) {
            if ((r.kind === 'principle' ? info.gov : info.abide).indexOf(id) >= 0) citing.push(ci);
          });
          var wrap = h('div', 'sc__block');
          wrap.appendChild(line('sc__label', !citing.length ? 'No paper module cites it' : citing.length === 1 ? 'Cited by one component’s paper module' :
            'Cited by the paper modules of ' + citing.length + ' of ' + model.comps.length + ' components'));
          // While none is open the families run on, each name whole on its
          // line; opened, they stand one to a row with the components beneath.
          // In a column too short for them they wait behind one button.
          var anyOpen = ring.order.some(function (fi) { return !!opened['cite:' + id + ':' + fi]; });
          var foldKey = 'fams:' + id, folded = fold && citing.length > 0 && !anyOpen && !opened[foldKey];
          if (folded) {
            var unfold = button('sc__all', 'Show by family');
            unfold.addEventListener('click', function (e) { opened[foldKey] = true; rebuild(keyedClick(e) ? foldKey : null); });
            wrap.appendChild(unfold);
          }
          var groups = h('ul', 'sc__list' + (anyOpen ? '' : ' sc__list--flow'));
          ring.order.forEach(function (fi) {
            var mine = citing.filter(function (ci) { return model.comps[ci].fam === fi; });
            if (!mine.length) return;
            var li = h('li', 'sc__li sc__group');
            var key = 'cite:' + id + ':' + fi, isOpen = !!opened[key];
            var g = button('sc__item sc__group-btn');
            g.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
            g.setAttribute('data-sm-key', 'fam:' + model.families[fi].key);
            var txt = h('span', 'sc__item-text');
            txt.appendChild(h('span', 'sc__item-name', model.families[fi].title));
            txt.appendChild(h('span', 'sc__item-note', String(mine.length)));
            g.appendChild(txt);
            g.addEventListener('click', function (e) { opened[key] = !opened[key]; rebuild(keyedClick(e) ? key : null); });
            li.appendChild(g);
            if (isOpen) {
              var inner = h('ul', 'sc__list sc__list--inner');
              mine.sort(function (p, q) { return byText(model.comps[p].label, model.comps[q].label); })
                .forEach(function (ci) { inner.appendChild(compItem(ci, null)); });
              li.appendChild(inner);
            }
            groups.appendChild(li);
          });
          if (!folded) wrap.appendChild(groups);
          sc.appendChild(wrap);
        }
        return node;
      }

      function wantKey() {
        if (!model) return null;
        if (at.level === 'rule') return D ? 'rule:' + at.rule : null;
        if (at.level === 'doctrine') return D ? 'doctrine' : null;
        if (at.level === 'family') return 'fam:' + at.fam;
        if (at.level === 'component') return 'comp:' + at.comp + ':' + (D ? 1 : 0);
        return null;
      }
      function build() {
        return at.level === 'rule' ? (explorer ? ruleReading(at.rule) : rulePage(at.rule)) : at.level === 'doctrine' ? (explorer ? doctrineCatalogue() : doctrinePage()) :
          at.level === 'family' ? famPage(at.fam) : compPage(at.comp);
      }
      // A page built again in place (a list opened), its scroll kept.
      function rebuild(focusGroup) {
        if (!shown) return;
        var sc = shown.node.querySelector ? shown.node.querySelector('.sc__scroll') : null, top = sc ? sc.scrollTop : 0, hostTop = explorer ? host.scrollTop : 0;
        var node = build();
        panel.replaceChild ? panel.replaceChild(node, shown.node) : (panel.removeChild(shown.node), panel.appendChild(node));
        shown.node = node;
        syncScope();
        fitScroll(node);
        var sc2 = node.querySelector ? node.querySelector('.sc__scroll') : null;
        if (sc2) sc2.scrollTop = top;
        if (explorer) host.scrollTop = hostTop;
        if (focusGroup && node.querySelectorAll) {
          var g = Array.prototype.filter.call(node.querySelectorAll('.sc__group-btn'), function (b) { return b.getAttribute('aria-expanded') !== null; });
          if (g[0] && g[0].focus) g[0].focus();
        }
      }
      function sync(how) {
        how = how || {};
        wireDoctrineRow();
        var key = wantKey();
        // A find and a narrowing belong to the choice they were made in; the
        // view and the doctrine's category hold from one choice to the next.
        var sel = model ? keyOf(at) : null;
        if (sel !== inspect.key) {
          inspect.key = sel;
          inspect.find = Object.create(null);
          inspect.scope = null;
          inspect.narrow = null;
          syncScope();
        }
        if (!key) { close(); return; }
        // A page built again for the same choice (the doctrine arriving)
        // keeps the panel where the reader had scrolled it.
        var again = !!shown && shown.key === 'stale' && explorer, keepTop = again ? host.scrollTop : 0;
        if (shown && shown.key === key) return;
        caps = Object.create(null);
        lean = false;
        bare = false;
        fold = false;
        var node = build();
        var old = shown && shown.node;
        if (old && old.parentNode) old.parentNode.removeChild(old);
        panel.appendChild(node);
        shown = { key: key, node: node };
        syncScope();
        panel.inert = false;
        panel.removeAttribute('aria-hidden');
        if (panel.classList) panel.classList.add('is-open');
        if (host.classList) host.classList.add('sc-host--open');
        // The explorer's page is read whole from its top; the column's is
        // fitted to the column.
        if (explorer) host.scrollTop = keepTop;
        else { node = tighten(node); fitScroll(node); }
        // The card comes in as the column's own words step out (90ms), so
        // the two never stand over each other and the column is never empty.
        if (motionOK() && !how.instant && node.animate) {
          try { node.animate([{ opacity: 0, transform: 'translateY(6px)' }, { opacity: 1, transform: 'none' }], { duration: 220, delay: 60, easing: EASE, fill: 'backwards' }); } catch (e) {}
        }
      }
      function close() {
        var old = shown && shown.node;
        shown = null;
        panel.inert = true;
        panel.setAttribute('aria-hidden', 'true');
        if (panel.classList) panel.classList.remove('is-open');
        if (host.classList) host.classList.remove('sc-host--open');
        if (old && old.parentNode) old.parentNode.removeChild(old);
        if (explorer && old) host.scrollTop = 0;
      }
      // A page fits its column: a long list shows its first eight names (as
      // few as four when the column is short) with the rest on request, and
      // short rule names stand two to a row. Only a list the reader opens in
      // full makes the page scroll, in whole rows.
      function overflows(node) {
        var sc = node.querySelector ? node.querySelector('.sc__scroll') : null;
        return !!sc && sc.scrollHeight > sc.clientHeight + 1;
      }
      // While a page is taller than its column, it gives up what matters
      // least first, and is built again each time: the longer description;
      // each component's family beside its name; rows from the list taking
      // the most (the rules a paper module cites last, none below two or
      // four names); a rule's citing families, behind one button; and last,
      // lists down to one or two names, then to their labels and the way to
      // show them all. A list the reader has opened in full stays open.
      function tighten(node) {
        // The fewest names a list keeps: first; then in a very short column;
        // and last, none (its label and the way to show them all).
        var FLOORS = [{ 1: 2, 2: 4 }, { 1: 1, 2: 2 }, { 1: 0, 2: 1 }];
        // A list gives up two names at a time, down to its floor, and only
        // while it can still close (a list of n shows n - 2 names at most).
        function pickFrom(floor) {
          var pick = null, pickNext = 0;
          Array.prototype.forEach.call(node.querySelectorAll('[data-shown]'), function (w) {
            var t = +w.getAttribute('data-trim'), s = +w.getAttribute('data-shown');
            var next = Math.max(floor[t], s - 2);
            if (s <= floor[t] || +w.getAttribute('data-total') <= next + 1) return;
            var pt = pick ? +pick.getAttribute('data-trim') : 9;
            if (!pick || t < pt || (t === pt && +w.getAttribute('data-rows') > +pick.getAttribute('data-rows'))) { pick = w; pickNext = next; }
          });
          return pick ? { w: pick, next: pickNext } : null;
        }
        for (var round = 0; round < 32 && overflows(node); round++) {
          if (!node.querySelectorAll || node.querySelector('[data-opened]')) break;
          if (!lean && node.querySelector('.sc__body')) {
            lean = true;
          } else if (!bare && node.querySelector('.sc__item-note')) {
            // A component's family beside its name goes next: the map and
            // its tip say where each one stands.
            bare = true;
          } else {
            // With every list at its first floor, a rule's citing families
            // fold behind one button before any list goes lower.
            var got = pickFrom(FLOORS[0]);
            if (got) caps[got.w.getAttribute('data-cap')] = got.next;
            else if (!fold && node.querySelector('.sc__list--flow')) fold = true;
            else if ((got = pickFrom(FLOORS[1]) || pickFrom(FLOORS[2]))) caps[got.w.getAttribute('data-cap')] = got.next;
            else break;
          }
          var next = build();
          if (node.parentNode) node.parentNode.replaceChild(next, node);
          node = next;
          if (shown) shown.node = node;
        }
        return node;
      }
      function fitScroll(node) {
        var sc = node.querySelector ? node.querySelector('.sc__scroll') : null;
        if (!sc) return;
        // Taller than its room, the list shows whole rows: its height is cut
        // back to the foot of the last row that fits, and the rest scrolls.
        function snap() {
          if (!sc.style || !sc.getBoundingClientRect || !sc.querySelectorAll) return;
          sc.style.maxHeight = '';
          if (!(sc.scrollHeight > sc.clientHeight + 1)) return;
          var top = sc.getBoundingClientRect().top - sc.scrollTop, room = sc.clientHeight, fit = 0;
          Array.prototype.forEach.call(sc.querySelectorAll('.sc__item, .sc__label, .sc__note, .sc__all'), function (row) {
            var b = row.getBoundingClientRect(), foot = b.bottom - top;
            if (b.height > 0 && foot <= room - 6 && foot > fit) fit = foot;
          });
          if (fit > 40) sc.style.maxHeight = Math.ceil(fit + 8) + 'px';
        }
        snap();
        function update() {
          if (sc.classList) sc.classList.toggle('has-overflow', sc.scrollHeight > sc.clientHeight + 1);
        }
        sc.addEventListener('scroll', update, { passive: true });
        update();
        node.__update = function () { snap(); update(); };
      }
      function lit(key) {
        [familyList, shown && shown.node, doctrineRow].forEach(function (scope) {
          if (!scope || !scope.querySelectorAll) return;
          Array.prototype.forEach.call(scope.querySelectorAll('[data-sm-key]'), function (n) {
            if (n.classList) n.classList.toggle('is-lit', !!key && n.getAttribute('data-sm-key') === key);
          });
          if (scope.getAttribute && scope.getAttribute('data-sm-key') && scope.classList) scope.classList.toggle('is-lit', scope.getAttribute('data-sm-key') === key);
        });
      }
      return {
        sync: sync, lit: lit, rows: wireRows, again: function () { rebuild(); },
        refit: function () { if (shown && shown.node && shown.node.__update) shown.node.__update(); },
        ready: function () { wireDoctrineRow(); if (shown) { shown.key = 'stale'; sync({ instant: true }); } },
        state: function () {
          if (!shown) return null;
          var t = shown.node.querySelector ? shown.node.querySelector('.sc__title') : null;
          return { key: shown.key, title: t ? t.textContent : null };
        }
      };
    }

    /* ---- Keys and the band ---- */
    function active() {
      if (slide && (slide.inert || (slide.getAttribute && slide.getAttribute('aria-hidden') === 'true'))) return false;
      return onScreen;
    }
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape' || e.defaultPrevented || !model || !active()) return;
      var t = e.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
      hideTip();
      if (up({ keyed: true })) { if (e.preventDefault) e.preventDefault(); }
    });
    // The map band's two slides share one height. Stacked (a narrow
    // window), while the system slide is away its card is parked (folded to
    // nothing), so a tall view never leaves the mathematics slide standing
    // in empty space. Beside its column the card is the mathematics slide's
    // height already, so it stays laid out, ready, as the slide arrives.
    function park(on) {
      if (!slide || pageMode || !stage.classList) return;
      stage.classList.toggle('is-parked', !!on && !framedBand());
    }
    if (slide && (slide.inert || (slide.getAttribute && slide.getAttribute('aria-hidden') === 'true'))) park(true);
    document.addEventListener('plectis:atlas', function (event) {
      var d = event && event.detail || {};
      if (d.phase === 'start' && d.previous === 'system' && d.view !== 'system') { setHover(null); hideTip(); }
      if (d.view === 'system' && d.phase === 'start') park(false);
      if (d.view !== 'system' && d.phase === 'end') park(true);
      if (d.view === 'system' && d.phase === 'end') { park(false); refresh(); reveal(); }
    });
    if ('IntersectionObserver' in window) {
      onScreen = false;
      var io = new window.IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          onScreen = !!e.isIntersecting;
          if (e.isIntersecting && e.intersectionRatio >= 0.35) reveal();
        });
      }, { threshold: [0, 0.35, 0.6] });
      io.observe(stage);
    }
    // The first time the map is seen it assembles, once, with the doctrine
    // in place (or without it, when the doctrine is slow or cannot be had).
    function reveal() {
      if (revealed || !map) return;
      if (!motionOK() || at.level !== 'system') { settleReveal(); return; }
      if (slide && (slide.inert || (slide.getAttribute && slide.getAttribute('aria-hidden') === 'true'))) return;
      if (doctrineSrc && doctrineState === 'pending' && !forceReveal) return;
      revealed = true;
      [map, baseMap].forEach(function (m) { if (m && m.svg.classList) m.svg.classList.remove('awaits-reveal'); });
      map.assemble();
    }
    // Without the opening (reduced motion, or a view chosen before it), the
    // map simply shows: the view on screen and the whole system kept for the
    // way back.
    function settleReveal() {
      revealed = true;
      [map, baseMap].forEach(function (m) { if (m && m.svg.classList) m.svg.classList.remove('awaits-reveal'); });
    }
    // The card keeps the whole system's height as its least, so a view
    // never makes the band jump shorter.
    function measureFloor() {
      if (explorer || at.level !== 'system' || !stage.style || !stage.getBoundingClientRect) return;
      if (stage.classList && stage.classList.contains('is-parked')) return;
      if (stage.style.removeProperty) stage.style.removeProperty('--sm-floor');
      var hgt = stage.getBoundingClientRect().height;
      if (hgt > 0 && stage.style.setProperty) stage.style.setProperty('--sm-floor', Math.ceil(hgt) + 'px');
    }

    /* ---- The public face ---- */
    function lookup(id) {
      if (!model || !id) return null;
      var fam = /^(?:area|family):(.+)$/.exec(id);
      if (fam) { var f = familyIndex(fam[1]); return f >= 0 ? { fam: f } : null; }
      for (var i = 0; i < model.comps.length; i++) if (model.comps[i].id === id) return { comp: i };
      return null;
    }
    function boxOf(el) {
      var r = el.getBoundingClientRect();
      return { x: fx(r.left), y: fx(r.top), w: fx(r.width), h: fx(r.height) };
    }
    var api = {
      // Lights a family where it stands, as pointing at its name does (null clears).
      focusFamily: function (id) {
        if (!model) { pending = pending || {}; pending.family = id; return; }
        var t = id ? lookup(id) : null;
        var key = t && t.fam !== undefined ? 'fam:' + model.families[t.fam].key : null;
        setHover(key, key && map ? map.anchorOf(key) : null);
      },
      // Selects a family ('area:<key>' or 'family:<key>'), a component
      // ('component:<id>'), the doctrine ('doctrine' or 'doctrine:<rule>'),
      // or the whole system (null).
      select: function (id, opts) {
        if (!model) { pending = pending || {}; pending.select = id; return; }
        opts = opts || {};
        if (id === 'doctrine' || (typeof id === 'string' && id.indexOf('doctrine:') === 0)) {
          if (!D) { pending = pending || {}; pending.select = id; return; }
          goDoctrine(id.slice(9) || null, { instant: !!opts.instant });
          return;
        }
        var t = id ? lookup(id) : null;
        if (!t) { goSystem({ instant: !!opts.instant }); return; }
        if (t.fam !== undefined) goFamily(t.fam, { instant: !!opts.instant });
        else goComponent(t.comp, { instant: !!opts.instant });
      },
      // Selects a rule (an axiom, principle or failure mode id).
      selectRule: function (id) { api.select(id ? 'doctrine:' + id : 'doctrine'); },
      lens: function (name) { if (model) { if (name === 'doctrine') goDoctrine(null); else goSystem(); } },
      up: function () { return up({}); },
      back: function () { return back({}); },
      // Read-only: where the reader is, what is lit, and the box of every
      // word and the ends of every line, for tests and audits.
      snapshot: function () {
        if (!model) return { ready: false };
        var labels = [], wires = [];
        if (root.querySelectorAll) {
          Array.prototype.forEach.call(root.querySelectorAll('.sm-label, .sm-note'), function (n) {
            if (n.closest && n.closest('[hidden]')) return;
            var keyEl = n.closest ? n.closest('[data-sm-key]') : null;
            labels.push({ text: n.textContent, kind: n.classList && n.classList.contains('sm-label') ? 'label' : 'note',
                          key: keyEl ? keyEl.getAttribute('data-sm-key') : null, box: boxOf(n) });
          });
          Array.prototype.forEach.call(root.querySelectorAll('.sm-wire'), function (p) {
            wires.push({ from: p.getAttribute('data-from'), to: p.getAttribute('data-to'),
                         kind: (p.getAttribute('class') || '').split(' ')[0], lit: !!(p.classList && p.classList.contains('is-lit')) });
          });
        }
        var L = map ? map.lit() : null;
        return {
          ready: true, stale: model.stale, doctrine: !!D, view: at.level,
          family: at.fam >= 0 ? model.families[at.fam].id : null, component: at.comp >= 0 ? model.comps[at.comp].id : null, rule: at.rule,
          caption: caption.textContent,
          crumbs: Array.prototype.map.call(crumbList.children || [], function (li) { return li.textContent; }),
          back: backBtn.hidden ? null : backBtn.getAttribute('aria-label'),
          ring: map ? { radius: map.R, pitch: map.pitch, crowded: !!map.crowded, core: map.core, frame: map.frame, sheaves: map.sheaves,
                        order: ring.order.map(function (fi) { return model.families[fi].id; }) } : null,
          counts: { families: model.families.length, components: model.comps.length, links: model.links.length,
                    bands: model.pairs.length, dropped: model.dropped, kinds: model.kinds.slice() },
          lit: L ? { comps: Object.keys(L.comps).length, rules: Object.keys(L.rules).length, routes: L.links.length, lines: L.cites.length,
                     spans: Object.keys(L.spans).length, reticles: L.reticles.slice(), open: L.open.slice(), plates: L.plated || 0 } : null,
          weave: map ? map.weave() : null,
          // How close the camera stands (null: the whole system), and the
          // family it names round the rim, if any.
          camera: camNow ? { k: fx(camNow.k), cx: fx(camNow.cx), cy: fx(camNow.cy), names: camNow.names === 'all' ? 'all' : camNow.names >= 0 ? model.families[camNow.names].id : null } : null,
          labels: labels, wires: wires, hover: hoverKey, column: column.state(), trail: trail.length
        };
      }
    };
    window.PlectisSystemMap = api;

    /* ---- Data ---- */
    if (!src || typeof fetch !== 'function') return api;
    fetch(src, { cache: 'no-cache' }).then(function (res) {
      if (res && res.ok === false) throw new Error('scene ' + res.status);
      return res.json();
    }).then(function (json) {
      model = readScene(json, base);
      json = null;
      if (!model || !model.comps.length) throw new Error('empty scene');
      ring = familyRing(model);
      clear(holder);
      holder.appendChild(root);
      if (keySlot) { clear(keySlot); keySlot.appendChild(keyBox); } else root.appendChild(keyBox);
      if (stage.classList) stage.classList.add('is-ready');
      column.rows();
      render({ instant: true });
      watchSize();
      wireExplorer();
      if (pageMode) {
        arriveAt();
        if (window.addEventListener) {
          window.addEventListener('popstate', followAddress);
          window.addEventListener('hashchange', followAddress);
        }
      }
      if (pending) {
        if (pending.family !== undefined) api.focusFamily(pending.family);
        if (pending.select !== undefined && !/^doctrine/.test(pending.select || '')) api.select(pending.select);
      }
      loadDoctrine();
      reveal();
      // A doctrine slow to arrive does not hold the map back for long.
      setTimeout(function () { forceReveal = true; reveal(); }, 2600);
    }).catch(function () {
      if (stage.classList) stage.classList.add('is-unavailable');
    });
    function loadDoctrine() {
      if (!doctrineSrc) return;
      fetch(doctrineSrc, { cache: 'no-cache' }).then(function (res) {
        if (res && res.ok === false) throw new Error('doctrine ' + res.status);
        return res.json();
      }).then(function (json) {
        D = readDoctrine(json, model, base);
        doctrineState = D ? 'ok' : 'failed';
        if (!D) { reveal(); return; }
        // The doctrine takes the centre: the map is laid out again with it.
        relayout();
        renderHead();
        caption.textContent = captionText();
        renderKey();
        column.ready();
        if (pageMode && pending && pending.arrival) { pending.arrival = false; arriveAt(); }
        else if (pageMode && pending && pending.address) { pending.address = false; followAddress(); }
        else if (pending && pending.select !== undefined && /^doctrine/.test(pending.select || '')) {
          var s = pending.select;
          pending.select = undefined;
          api.select(s);
        }
        reveal();
      }).catch(function () { doctrineState = 'failed'; reveal(); });
    }

    /* ---- Housekeeping ---- */
    var frame = 0, lastWidth = 0, lastRow = 0, lastHeight = 0;
    // Laid out again for a new width, or, beside its column, for a new
    // height of the mathematics slide the card matches; the explorer's
    // stage, for a new width or height.
    function areaHeight() { return explorer && area.getBoundingClientRect ? area.getBoundingClientRect().height : 0; }
    function refresh() {
      if (!model || !map) return;
      var w = area.getBoundingClientRect ? area.getBoundingClientRect().width : 0, row = mathsRow(), hh = areaHeight();
      if ((w && Math.abs(w - lastWidth) > 1) || Math.abs(row - lastRow) > 2 || (hh && Math.abs(hh - lastHeight) > 1)) {
        lastWidth = w; lastRow = row; lastHeight = hh; relayout();
      }
      measureFloor();
      column.refit();
    }
    function requestRefresh() {
      var raf = window.requestAnimationFrame || function (fn) { return setTimeout(fn, 16); };
      if (frame) return;
      frame = raf(function () { frame = 0; refresh(); });
    }
    function watchSize() {
      lastWidth = area.getBoundingClientRect ? area.getBoundingClientRect().width : 0;
      lastHeight = areaHeight();
      lastRow = mathsRow();
      // The mathematics slide reflows as the window changes; the card follows.
      var mathsSplit = slide && slide.parentNode && slide.parentNode.querySelector ? slide.parentNode.querySelector('[data-atlas-slide="mathematics"] .home-split') : null;
      if (mathsSplit && 'ResizeObserver' in window) new window.ResizeObserver(function () { requestRefresh(); }).observe(mathsSplit);
      if ('ResizeObserver' in window) new window.ResizeObserver(requestRefresh).observe(area);
      if (window.addEventListener) window.addEventListener('resize', requestRefresh);
      if (document.fonts && document.fonts.ready && document.fonts.ready.then) document.fonts.ready.then(function () { if (model) relayout(); }, function () {});
    }
    function followReduce() { reduceMotion = !!(reduceQuery && reduceQuery.matches); }
    if (reduceQuery && typeof reduceQuery.addEventListener === 'function') reduceQuery.addEventListener('change', followReduce);
    return api;
  }

  // The parts that need no page, for the tests that check them directly.
  window.PlectisSystemMapCore = {
    readScene: readScene, readDoctrine: readDoctrine, familyRing: familyRing, Loom: Loom,
    trimProse: trimProse, classOf: classOf, CLASS_WORDS: CLASS_WORDS
  };

  function boot() {
    var stages = document.querySelectorAll('[data-system-stage]');
    Array.prototype.forEach.call(stages, function (stage) { mount(stage); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
