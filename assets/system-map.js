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
      var d = '';
      pieces.forEach(function (pc) {
        if (pc[1] - pc[0] < minPiece || pc[3] - pc[2] < minPiece) return;
        d += 'M' + edgeRun(Lx, Ly, pc[0], pc[1], false) + 'L' + edgeRun(Rx, Ry, pc[2], pc[3], true) + 'Z';
      });
      return d;
    }
    // The points of one edge between two fractional sample indices, as
    // "x y L x y ..." (reversed if asked).
    function edgeRun(X, Y, from, to, reverse) {
      var list = [];
      function at(f) { var i = Math.min(X.length - 2, Math.floor(f)), t = f - i; return nf(X[i] + (X[i + 1] - X[i]) * t) + ' ' + nf(Y[i] + (Y[i + 1] - Y[i]) * t); }
      list.push(at(from));
      for (var i = Math.floor(from) + 1; i < to; i++) list.push(nf(X[i]) + ' ' + nf(Y[i]));
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
      var hubs = pinned ? { order: spec.order.slice(), candidates: [{ order: spec.order.slice() }], ms: 0, pinned: true } :
        hubOrder(A, bridges.map(function (r) { return r.on; }), spec.hubOpts);
      // Of the best orders, the one whose bridges draw with fewest crossings.
      var chosen = null;
      hubs.candidates.forEach(function (cand) {
        var p = Object.create(null);
        cand.order.forEach(function (id, k) { p[id] = k; });
        var plan = bridgePlan(n, bridges.map(function (r) { return r.on.map(function (h) { return p[h]; }); }), cap);
        if (!chosen || plan.total < chosen.plan.total - 1e-9) chosen = { order: cand.order, pos: p, plan: plan };
      });
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
      // Checks, for the record.
      var ids = Object.keys(glyphs), minGap = Infinity, lineGap = Infinity, minR = Infinity, drawn = 0;
      for (var i = 0; i < ids.length; i++) for (var j = i + 1; j < ids.length; j++) {
        var p = glyphs[ids[i]], q = glyphs[ids[j]];
        minGap = Math.min(minGap, Math.hypot(p.x - q.x, p.y - q.y) - (p.size + q.size) / 2);
      }
      lines.forEach(function (ln) {
        ln.polar.forEach(function (pp) { minR = Math.min(minR, pp[1]); });
        ids.forEach(function (id) {
          if (id === ln.from || id === ln.to) return;
          var g = glyphs[id];
          ln.pts.forEach(function (pt) { lineGap = Math.min(lineGap, Math.hypot(pt[0] - g.x, pt[1] - g.y) - g.size / 2); });
        });
      });
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
        stats: { glyphGap: minGap, lineGlyphGap: lineGap, nearestToCentre: minR, labelR: rLabel, planCrossings: plan.crossings,
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
      bundle: bundle, taper: taper, fibreStroke: fibreStroke, strokeGaps: strokeGaps,
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
    return { rules: rules, principles: order.principles, axioms: order.axioms, failures: order.failures, comp: comp, verdicts: verdicts,
             enforcedBy: tested ? 'tests' : 'card' };
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
    var base = holder.getAttribute('data-system-base') || '';
    var src = holder.getAttribute('data-system-src');
    var doctrineSrc = holder.getAttribute('data-system-doctrine') ||
      (src ? src.replace(/[^\/]*(?:[?#].*)?$/, 'doctrine-manifest.json') : null);

    var reduceQuery = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    var reduceMotion = !!(reduceQuery && reduceQuery.matches);

    var model = null, D = null, ring = null, map = null;
    // Where the reader is: a level and what is chosen there.
    //   system | family (fam) | component (comp) | doctrine | rule (rule)
    var at = { level: 'system', fam: -1, comp: -1, rule: null };
    var trail = [];
    var hoverKey = null, pending = null, revealed = false, onScreen = true, doctrineState = 'pending', forceReveal = false;

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
    var tip = h('div', 'sm-tip');
    tip.hidden = true;
    tip.setAttribute('aria-hidden', 'true');
    var live = h('p', 'sm-live');
    live.setAttribute('aria-live', 'polite');
    root.appendChild(head);
    root.appendChild(caption);
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
      if (pageMode && !how.fromAddress) writeAddress(!!how.replace);
      render(how);
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
    function setHover(key, anchor) {
      if (key === hoverKey) { if (anchor) showTipFor(key, anchor); return; }
      hoverKey = key;
      if (map) map.preview(key);
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

    /* ---- Rendering ---- */
    // The card's height less its drawing's, once laid out: what the circle
    // leaves room for on the landing, so the card fits the window.
    var chromeH = 0, refitting = false;
    function fitHeight() {
      if (pageMode || refitting || !map || !stage.getBoundingClientRect || !map.svg.getBoundingClientRect) return;
      if (stage.classList && stage.classList.contains('is-parked')) return;
      if (stage.style && stage.style.removeProperty) stage.style.removeProperty('--sm-floor');
      var c = stage.getBoundingClientRect().height - map.svg.getBoundingClientRect().height;
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
      if (!map) { map = buildMap(); clear(area); area.appendChild(map.el); }
      root.setAttribute('data-view', at.level);
      map.select(at, how);
      if (at.level === 'system') fitHeight();
      column.sync(how);
      measureFloor();
      column.refit();
      announce();
      if (how.keyed) focusKey(how.focusTo || keyOf(at) || null);
    }
    // The map is laid out again for a new size; the view stays as it was.
    function relayout() {
      if (!model) return;
      hoverKey = null;
      hideTip();
      renderKey();
      map = buildMap();
      clear(area);
      area.appendChild(map.el);
      map.select(at, { instant: true });
      // A new layout at the top level fits the card to the window again.
      if (at.level === 'system') fitHeight();
      measureFloor();
      column.refit();
    }
    function renderHead() {
      clear(crumbList);
      var path = ancestors(at).concat([copyAt(at)]);
      path.forEach(function (a, k) {
        var li = h('li', 'sm-crumbs__item');
        var label = a.level === 'system' ? 'System' : a.level === 'doctrine' ? 'The doctrine' : capital(nameOf(a));
        if (k === path.length - 1) {
          var here = h('span', 'sm-crumbs__here', label);
          here.setAttribute('aria-current', 'location');
          li.appendChild(here);
        } else {
          var b = button('sm-crumbs__go', label);
          b.addEventListener('click', function (e) {
            navigate(a, { keyed: keyedClick(e), back: true, focusTo: keyOf(path[k + 1]) });
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
    // What the red lines are, for the key.
    function aboutLines() {
      if (onlyNamed()) return 'Red lines are the relations each component’s own record lists, not read from the code.';
      var none = unconnected();
      return 'Red lines are derived from the code: each one rests on the place in the code where one component runs another, ' +
        'reads its saved results or checks its copied files.' + (none ? ' ' + none + ' of the ' + model.comps.length + ' components have none.' : '');
    }
    function linkNote() {
      if (onlyNamed()) return 'Listed in a component’s own record, not read from the code.';
      return model.codeBase && model.links.some(function (l) { return !!l.ev; }) ?
        'Each is derived from the code; Code opens the file that makes it.' : 'Each connection is derived from the code.';
    }
    function captionText() {
      var n = model.comps.length;
      if (at.level === 'family') {
        var F = model.families[at.fam];
        return F.title + ': its ' + countWords(F.members.length, 'component', 'components') + ' and their ' + linkNoun(2) + ', inside the family and out to the others.';
      }
      if (at.level === 'component') {
        var c = model.comps[at.comp];
        var rules = D ? ', azure lines to the rules its paper module cites.' : '.';
        if (!c.out.length && !c.inc.length) return c.label + (onlyNamed() ? ': its record lists no related components' : ': no code connections to other components') +
          (D ? '; azure lines to the rules its paper module cites.' : '.');
        if (onlyNamed()) return c.label + ': red lines to the components listed as related' + rules;
        return c.label + ': red lines for its code connections' + rules;
      }
      if (at.level === 'doctrine') {
        return 'The doctrine: ' + countWords(D.axioms.length, 'axiom', 'axioms') + ' on a ring. A rule tied to one axiom sits just outside it; a rule tied to several stands between them.';
      }
      if (at.level === 'rule') {
        var r = D.rules[at.rule];
        if (r.kind === 'failure') return r.title + ': lit with the axioms it threatens and the components ' + (D.enforcedBy === 'tests' ?
          'where a test shows it enforced' + (r.partly.length ? ' or checks part of it' : '') + '.' : 'its card names as enforcing it.');
        var into = r.kind === 'axiom' ? 'the principles and failure modes tied to it' : 'the axioms it rests on';
        return r.title + ': lit with ' + into + ', and azure lines out to the components whose paper modules cite it.';
      }
      var none = unconnected();
      return n + ' components round the rim in ' + numberWord(model.families.length) + ' families' +
        (none ? ', ' + none + ' of them with no code connection,' : '') +
        (D ? (none ? ' and' : ',') + ' the doctrine at the centre' : '') + '. Select any of them to light what it touches.';
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

    /* ---- The map ---- */
    function familyIndex(key) {
      for (var i = 0; i < model.families.length; i++) if (model.families[i].key === key) return i;
      return -1;
    }
    // Words are measured in a drawing that stays in the page, out of sight.
    var measurer = null;
    function textWidth(text, cls) {
      if (!measurer) {
        var box = sv('svg', { 'class': 'sm-measure', width: 1, height: 1, 'aria-hidden': 'true', focusable: 'false' });
        root.appendChild(box);
        measurer = sv('g');
        box.appendChild(measurer);
      }
      var t = sv('text', { 'class': cls });
      t.textContent = text;
      measurer.appendChild(t);
      var w = t.getComputedTextLength ? t.getComputedTextLength() : 0;
      measurer.removeChild(t);
      return w > 0 ? w : String(text).length * (/sector__name|plate|centre/.test(cls) ? 8.6 : 7.4);
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
      return clamp(Math.min(byWidth, Math.max(byHeight, 180)), 140, 430);
    }
    /* On the map's own page every component is named round the rim when the
       room allows: the largest of 16, 15 or 14px whose circle fits the window
       (and failing that, its width), the names set along their radii, the
       sector names outside them. */
    function namedPlan(width, depth) {
      if (!pageMode) return null;
      var widest = 0, head = 0;
      model.comps.forEach(function (c) { widest = Math.max(widest, textWidth(c.label, 'sm-rimname')); });
      // A family's own name stands along the radius in the gap before its
      // run, as a header to the names that follow.
      model.families.forEach(function (F) {
        head = Math.max(head, textWidth(F.title, 'sm-sector__name') + 10 + textWidth(countLine(F), 'sm-sector__count'));
      });
      var top = area.getBoundingClientRect ? area.getBoundingClientRect().top + (window.pageYOffset || 0) : 250;
      var avail = (window.innerHeight || 900) - Math.max(0, top) - 72;
      var plans = [16, 15, 14].map(function (fs) {
        var k = fs / 16, pitch = fs + 2, slot = 20;
        var arc = model.comps.length * pitch + ring.order.length * (slot + 2 * pitch);
        var rName = Math.max(arc / TAU, 240 + depth + 6);
        var outer = rName + Math.max(widest * k, head) + 6;
        return { fs: fs, pitch: pitch, slot: slot, rName: rName, R: rName - depth - 6, outer: outer,
                 size: Math.ceil(2 * outer), widest: widest * k };
      });
      for (var i = 0; i < plans.length; i++) if (plans[i].size <= width && plans[i].size <= avail) return plans[i];
      for (var j = plans.length - 1; j >= 0; j--) if (plans[j].size <= width) return plans[j];
      return null;
    }
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

    function buildMap() {
      var el = h('div', 'sm-body sm-body--ring');
      var width = Math.max(320, (area.getBoundingClientRect ? area.getBoundingClientRect().width : 0) || 760);
      var order = ring.order, nF = order.length, nComp = model.comps.length;
      var depth = rimDepth();
      var named = namedPlan(width, depth);
      var R = named ? named.R : landingRadius(width, depth);
      var labelR1 = R + depth + 13, labelR2 = labelR1 + 18;
      var size = named ? named.size : Math.ceil(2 * (labelR2 + 12));
      var cx = width / 2, cy = size / 2;
      // Lines grow more slowly than the ring, so a large drawing stays fine.
      var s = R / 320, rs = Math.sqrt(s), ws = Math.pow(s, 0.6);
      var svg = sv('svg', { 'class': 'sm-ring' + (named ? ' is-named' : '') + (!revealed && motionOK() ? ' awaits-reveal' : ''), width: fx(width), height: size,
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
      [defs, gScale, gRest, gNeck, gSpans, gLight, gCore, gRim, gLabels, gPlates, gMarks].forEach(function (g) { svg.appendChild(g); });

      /* ---- The rim ---- */
      /* One spacing for every component round the ring; a sector is as wide
         as its run and its name need; whatever is left is shared out so the
         circle closes. With every name round the rim the spacing is the
         names' own. */
      var labelW = model.families.map(function (F) {
        return Math.max(textWidth(F.title, 'sm-sector__name'), textWidth(countLine(F), 'sm-sector__count'));
      });
      // With every name round the rim, a family's name stands in the gap
      // before its run, so the gap is a slot and a spacing either side of it,
      // and a sector needs no more room than its run.
      var gapA = named ? (named.slot + 2 * named.pitch) / named.rName : 16 / R;
      function floorOf(fi) { return named ? 0 : (labelW[fi] + 26) / labelR1; }
      function needAt(p) {
        var total = nF * gapA;
        order.forEach(function (fi) {
          total += Math.max(model.families[fi].members.length * p, floorOf(fi));
        });
        return total;
      }
      var pitch;
      if (named) pitch = named.pitch / named.rName;
      else {
        var lo = 7 / R, hi = 22 / R;
        for (var it = 0; it < 30; it++) { var mid = (lo + hi) / 2; if (needAt(mid) <= TAU) lo = mid; else hi = mid; }
        pitch = lo;
      }
      var pitchPx = pitch * R, spare = Math.max(0, TAU - needAt(pitch)) / nF;
      // Every mark at least ten pixels, so its cut survives a reader's zoom.
      var markSize = clamp(pitchPx - 2, 10, 11.5);
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
      var rName = named ? named.rName : 0;

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
          var g = Math.sqrt(Math.max(1, n || S.links.length)), tw = TRUNK[S.role];
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
      function litPath(dr, cuts, cls, wire) {
        if (dr.t === 'trunk') {
          var S = sheaves[dr.si], hubKey = 'comp:' + model.comps[S.h].id, famKey = 'fam:' + model.families[S.fam].key;
          return sv('path', { 'class': cls + ' sm-route--' + S.kind + ' is-trunk', d: itemD(dr.it, true, cuts, dr.n),
            'data-from': dr.reverse ? famKey : hubKey, 'data-to': dr.reverse ? hubKey : famKey, 'data-n': String(dr.n) });
        }
        var x = dr.x, kind = x.l.kind || 'named';
        return sv('path', { 'class': cls + (wire ? ' sm-wire' : '') + ' sm-route--' + kind + (dr.t === 'twig' ? ' is-twig' : routes[x.k].local ? ' is-local' : ''),
          d: dr.t === 'twig' ? itemD(dr.it, true, cuts) : fibreD(x.k, true, cuts),
          'data-from': 'comp:' + model.comps[x.a].id, 'data-to': 'comp:' + model.comps[x.b].id });
      }
      // How lit pieces draw in: a lone link from its own end; a ribbon and
      // its parting fibres in turn, from the end the light starts at.
      function revealItems(draws) {
        var wRed = 2 * 1.85 * ws * 1.3 * 1.2 + 3;
        return draws.map(function (dr) {
          if (dr.t === 'link') return { pts: routes[dr.x.k].pts, reverse: dr.x.a !== model.links[dr.x.k][0], w: wRed };
          if (dr.t === 'trunk') return { pts: dr.it.pts, reverse: dr.reverse, w: wRed * Math.sqrt(dr.n), delay: dr.reverse ? 260 : 0, dur: 460 };
          return { pts: dr.it.pts, reverse: dr.reverse, w: wRed, delay: dr.after ? 380 : 0, dur: 340 };
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
      // points (no more than two pixels apart) passes over.
      function glyphHits(pts, skip, pad) {
        var n = 0;
        Object.keys(rule).forEach(function (id) {
          if (id === skip) return;
          var q = rule[id], room = q.half + pad, rr = room * room;
          for (var i = 0; i < pts.length; i++) {
            var dx = pts[i][0] - q.x, dy = pts[i][1] - q.y;
            if (dx * dx + dy * dy < rr) { n++; return; }
          }
        });
        return n;
      }
      function inLabel(pts) {
        if (!labelBox) return false;
        for (var i = 0; i < pts.length; i++) {
          if (pts[i][0] > labelBox.x0 && pts[i][0] < labelBox.x1 && pts[i][1] > labelBox.y0 && pts[i][1] < labelBox.y1) return true;
        }
        return false;
      }
      function cubic(p0, p1, p2, p3) {
        var len = dist(p0, p1) + dist(p1, p2) + dist(p2, p3), n = clamp(Math.ceil(len / 2), 4, 600), out = [];
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
        function consider(run, extra) {
          run = trimTo(run, G, q.half + 2);
          var cost = (inLabel(run) ? 1e6 : 0) + glyphHits(run, id, 1.5) * 120 + turning(run) * 40 + polyLen(run) * 0.04 + (extra || 0);
          if (!best || cost < best.cost) best = { cost: cost, pts: run };
        }
        [-72, -54, -36, 36, 54, 72].forEach(function (deg) {
          var an = deg * Math.PI / 180, c = Math.cos(an), sn = Math.sin(an);
          var d = [ux * c - uy * sn, ux * sn + uy * c];
          [0.3, 0.44].forEach(function (k1) {
            [0.28, 0.42].forEach(function (k2) {
              consider(cubic(P0, [P0[0] + t0[0] * k1 * L, P0[1] + t0[1] * k1 * L], [G[0] + d[0] * k2 * L, G[1] + d[1] * k2 * L], G));
            });
          });
        });
        if (best.cost >= 1e6 && labelBox) {
          // Straight across the centre: by way of a point beside its name.
          var bw = (labelBox.x1 - labelBox.x0) / 2 + 10, bh = (labelBox.y1 - labelBox.y0) / 2 + 10;
          [[cx - bw, cy], [cx + bw, cy], [cx, cy - bh], [cx, cy + bh]].forEach(function (V) {
            var dv = [G[0] - P0[0], G[1] - P0[1]], dl = Math.sqrt(dv[0] * dv[0] + dv[1] * dv[1]) || 1, k = 0.22 * L;
            dv = [dv[0] / dl, dv[1] / dl];
            var a1 = cubic(P0, [P0[0] + t0[0] * 0.3 * L, P0[1] + t0[1] * 0.3 * L], [V[0] - dv[0] * k, V[1] - dv[1] * k], V);
            var a2 = cubic(V, [V[0] + dv[0] * k, V[1] + dv[1] * k], [G[0] + (ux * 0.8 - uy * 0.6) * 0.2 * L, G[1] + (uy * 0.8 + ux * 0.6) * 0.2 * L], G);
            consider(a1.concat(a2.slice(1)), 200);
          });
        }
        return best.pts;
      }
      // From a component's mark to a rule; a rule's lines out to the rim are
      // the same lines, read from the other end.
      function ray(ci, id) {
        var key = ci + '|' + id;
        if (!rayCache[key]) rayCache[key] = Math.abs(turn(comp[ci].a, rule[id].a)) <= NEAR ? nearRay(comp[ci], id) : farRay(comp[ci], id);
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
      var tickEls = Object.create(null), sectorScale = [];
      order.forEach(function (fi) {
        var S = sectors[fi], F = model.families[fi];
        var g = sv('g', { 'class': 'sm-scale__sector', 'data-fam': F.key });
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
        sectorScale[fi] = g;
      });

      /* ---- The doctrine's own relations ---- */
      // The necklace's orbit, a guide in the ground's own line tone, as the
      // mathematics slide draws the orbit of its problems.
      var neck = null, spanEls = Object.create(null);
      if (core) {
        neck = sv('circle', { 'class': 'sm-necklace', cx: fx(cx), cy: fx(cy), r: fx(hubR) });
        gNeck.appendChild(neck);
        core.lines.forEach(function (ln) {
          var key = ln.from + '>' + ln.to;
          var p = sv('path', { 'class': 'sm-span sm-span--' + (ln.kind === 'failure' ? 'threat' : 'rest') + (ln.role === 'bridge' ? ' is-chord' : '') + ' sm-wire',
            d: Loom.lineD(ln.pts), 'data-from': 'rule:' + ln.from, 'data-to': 'rule:' + ln.to });
          gSpans.appendChild(p);
          spanEls[key] = { el: p, pts: ln.pts, item: ln.from, axiom: ln.to };
        });
      }

      /* ---- Nodes: focusable, named, each with a target the size of its place ---- */
      var nodes = Object.create(null);
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
      model.comps.forEach(function (c, ci) {
        if (!comp[ci]) return;
        var C = comp[ci];
        var g = node('comp:' + c.id, C.x, C.y, 'sm-node--comp', c.label + ', ' + model.families[c.fam].title +
          (c.cls ? '; ' + lowerFirst(CLASS_WORDS[c.cls]) : '') + '. Select to light its links and rules.', Math.max(6, pitchPx / 2), markSize / 2 + 1.6);
        g.__ci = ci;
        g.appendChild(glyph(GLYPHS[c.cls] || GLYPHS.none, markSize));
        g.appendChild(sv('circle', { 'class': 'sm-focus-ring', r: fx(markSize / 2 + 3.5) }));
        if (named) {
          var deg = C.a * 180 / Math.PI, right = Math.cos(C.a) >= 0, off = rName - R;
          var t = sv('text', { 'class': 'sm-rimname sm-rimname--' + named.fs + ' sm-note', 'dominant-baseline': 'central',
            'text-anchor': right ? 'start' : 'end',
            transform: 'rotate(' + fx(right ? deg : deg + 180) + ') translate(' + fx(right ? off : -off) + ' 0)' });
          t.textContent = c.label;
          g.appendChild(t);
        }
        g.addEventListener('click', function (e) { if (e && e.stopPropagation) e.stopPropagation(); goComponent(ci, { keyed: keyedClick(e) }); });
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
          g.addEventListener('click', function (e) { if (e && e.stopPropagation) e.stopPropagation(); goDoctrine(id, { keyed: keyedClick(e) }); });
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
        cpop.appendChild(ct);
        cg.appendChild(cpop);
        cg.appendChild(sv('circle', { 'class': 'sm-focus-ring', r: fx(Math.max(14, centreClear - 4)) }));
        cg.addEventListener('click', function (e) { if (e && e.stopPropagation) e.stopPropagation(); goDoctrine(null, { keyed: keyedClick(e) }); });
        hoverable(cg, 'doctrine', cg);
        gCore.appendChild(cg);
      }

      /* ---- The sector names, set along the outside of the ring ---- */
      var labelBoxes = [];   // per family: sample boxes along both rows, for the plates to keep clear of
      // With every name round the rim, a family's name stands along the
      // radius in the gap before its run, its count after it, reading outward
      // like the names it heads.
      if (named) order.forEach(function (fi) {
        var S = sectors[fi], F = model.families[fi], a = S.lo - gapA / 2;
        var right = Math.cos(a) >= 0, deg = a * 180 / Math.PI;
        var g = sv('g', { 'class': 'sm-node sm-node--fam sm-node--head', 'data-sm-key': 'fam:' + F.key, role: 'button', tabindex: '0',
          'aria-label': F.title + ': ' + countLine(F) + '. Select to light the family.',
          transform: 'translate(' + pt(polar(cx, cy, rName, a)) + ') rotate(' + fx(right ? deg : deg + 180) + ')' });
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
        g.addEventListener('click', function (e) { if (e && e.stopPropagation) e.stopPropagation(); goFamily(fi, { keyed: keyedClick(e) }); });
        hoverable(g, 'fam:' + F.key, g);
        gLabels.appendChild(g);
        nodes['fam:' + F.key] = g;
        labelBoxes[fi] = { g: g, boxes: [] };
      });
      else order.forEach(function (fi, k) {
        var S = sectors[fi], F = model.families[fi], lower = readsDownward(S.mid);
        var rows = lower ? [[F.title, 'sm-sector__name', labelR1], [countLine(F), 'sm-sector__count', labelR2]] :
          [[countLine(F), 'sm-sector__count', labelR1], [F.title, 'sm-sector__name', labelR2]];
        var g = sv('g', { 'class': 'sm-node sm-node--fam', 'data-sm-key': 'fam:' + F.key, role: 'button', tabindex: '0',
          'aria-label': F.title + ': ' + countLine(F) + '. Select to light the family.' });
        var spanHit = Math.max(S.hi - S.lo, (labelW[fi] + 26) / labelR1);
        g.appendChild(sv('path', { 'class': 'sm-hit sm-hit--band', d: arcFor(cx, cy, (labelR1 + labelR2) / 2, S.mid, spanHit, lower), 'stroke-width': 40 }));
        var samples = [];
        rows.forEach(function (row, j) {
          var id = 'sm-arc-' + mounted + '-' + k + '-' + j, w = textWidth(row[0], row[1]);
          var span = Math.min(TAU * 0.45, (w + 60) / row[2]);
          defs.appendChild(sv('path', { id: id, d: arcFor(cx, cy, row[2], S.mid, span, lower) }));
          var t = sv('text', { 'class': row[1] + (row[1] === 'sm-sector__name' ? ' sm-label' : ' sm-note'), 'dominant-baseline': 'central' });
          var tp = sv('textPath', { href: '#' + id, startOffset: '50%', 'text-anchor': 'middle' });
          if (tp.setAttributeNS) tp.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', '#' + id);
          tp.textContent = row[0];
          t.appendChild(tp);
          g.appendChild(t);
          var half = (w / 2 + 4) / row[2];
          for (var a = S.mid - half; a <= S.mid + half + 1e-9; a += 7 / row[2]) {
            var p = polar(cx, cy, row[2], a);
            samples.push({ x0: p[0] - 8, x1: p[0] + 8, y0: p[1] - 9, y1: p[1] + 9 });
          }
        });
        g.appendChild(sv('path', { 'class': 'sm-focus-band', d: arcFor(cx, cy, (labelR1 + labelR2) / 2, S.mid, spanHit, lower), 'stroke-width': 42 }));
        g.addEventListener('click', function (e) { if (e && e.stopPropagation) e.stopPropagation(); goFamily(fi, { keyed: keyedClick(e) }); });
        hoverable(g, 'fam:' + F.key, g);
        gLabels.appendChild(g);
        nodes['fam:' + F.key] = g;
        labelBoxes[fi] = { g: g, boxes: samples };
      });
      // An empty click steps back a level.
      svg.addEventListener('click', function () { if (at.level !== 'system') up({}); });

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
      var reveals = [], revealN = 0;
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
        Object.keys(spanEls).forEach(function (k) { spanEls[k].el.classList.toggle('is-lit', !!L.spans[k]); });
        var moving = !how.instant && !how.keyed && motionOK();
        // The azure lines, each from the end its light starts at.
        var az = L.cites.map(function (x) {
          var pts = ray(x.ci, x.id);
          return { x: x, pts: x.out ? pts.slice().reverse() : pts };
        });
        // The weave: every lit line, and the fibres at rest beneath them.
        var litK = Object.create(null), strands = [], refs = [], draws = litDraws(L.links);
        L.links.forEach(function (x) { litK[x.k] = true; });
        draws.forEach(function (dr) {
          var pts = dr.t === 'link' ? routes[dr.x.k].pts : dr.it.pts, pair = dr.t === 'link' ? routes[dr.x.k].pair : dr.it.pair;
          var w = dr.t === 'link' ? widthOf(dr.x.k, true) : itemWidth(dr.it, true, dr.n);
          strands.push({ pts: pts, ink: 'red', rank: 1, width: w, bundle: pair >= 0 ? 'pair' + pair : null });
          refs.push({ t: 'lit', dr: dr });
        });
        // A piece at rest is lit when every link it carries is.
        var litItem = function (it) { return it.links.every(function (k) { return !!litK[k]; }); };
        if (restDrawn && az.length) items.forEach(function (it) {
          if (litItem(it)) return;
          strands.push({ pts: it.pts, ink: 'red', rank: 0, width: itemWidth(it, false), bundle: it.pair >= 0 ? 'pair' + it.pair : null });
          refs.push({ t: 'rest', it: it });
        });
        az.forEach(function (a) {
          strands.push({ pts: a.pts, ink: 'azure', rank: 1, width: +AZ_W, bundle: s.level === 'component' ? 'fan' : null });
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
        if (moving) {
          revealAlong(gLitRed, revealItems(draws), 40, 720);
          revealAlong(gLitAz, az.map(function (a) { return { pts: a.pts, w: +AZ_W + 4 }; }), 60, 760);
          Object.keys(L.spans).forEach(function (k) {
            var sp = spanEls[k], sl = L.spans[k];
            if (sp) drawIn(sp.el, sl.stage ? 520 : 40, 460);
          });
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
        plates(L.plates, moving);
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
         that finds no room is listed in the column all the same. On the
         map's own page every name is already round the rim. */
      var PLATE_MAX = 14, PLATE_LEAD = 20;
      // The ways a name can be set on a plate: on one line, or on two or
      // three lines broken where they come out most nearly equal (a narrow
      // room at the sides of the ring takes them). Never cut.
      function plateShapes(text) {
        var one = textWidth(text, 'sm-plate__text');
        var out = [{ lines: [text], w: one + 16, h: 26, cost: 0 }];
        var words = text.split(' ');
        if (words.length > 1) {
          var best2 = null;
          for (var k = 1; k < words.length; k++) {
            var a = words.slice(0, k).join(' '), b = words.slice(k).join(' ');
            var wide = Math.max(textWidth(a, 'sm-plate__text'), textWidth(b, 'sm-plate__text'));
            if (!best2 || wide < best2.wide) best2 = { lines: [a, b], wide: wide };
          }
          if (best2.wide < one - 24) out.push({ lines: best2.lines, w: best2.wide + 16, h: 26 + PLATE_LEAD, cost: 22 });
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
          if (best3.wide < out[out.length - 1].w - 16 - 14) out.push({ lines: best3.lines, w: best3.wide + 16, h: 26 + 2 * PLATE_LEAD, cost: 60 });
        }
        return out;
      }
      function plates(list, moving) {
        Object.keys(labelBoxes).forEach(function (fi) { labelBoxes[fi].g.classList.remove('is-covered'); });
        if (named || !list.length) return;
        var placed = [], covered = Object.create(null), shown = 0;
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
          if (shown >= PLATE_MAX || !comp[ci]) return;
          var C = comp[ci], c = model.comps[ci], self = rank === 0 && at.level === 'component';
          var r0 = R + 16 + C.bar + (C.enf ? 5 : 2);
          var best = null;
          plateShapes(c.label).forEach(function (shape) {
            var w = shape.w, hgt = shape.h;
            [0, 10, 22, 36, 52, 70, 90].forEach(function (lift) {
              var rl = Math.max(furn + 6, r0 + 4) + lift;
              var e = polar(cx, cy, rl, C.a), s0 = polar(cx, cy, r0, C.a);
              // The leader's bend stays on the drawing too, never out under
              // the key or the caption.
              if (e[0] < 4 || e[0] > width - 4 || e[1] < 4 || e[1] > size - 4) return;
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
                  if (box.x0 < 4 || box.x1 > width - 4 || box.y0 < 4 || box.y1 > size - 4) return;
                  if (!outside(box)) return;
                  var ey = clamp(e[1], box.y0 + 4, box.y1 - 4), ex = side > 0 ? box.x0 : box.x1;
                  var legs = [[s0[0], s0[1], e[0], e[1]], [e[0], e[1], ex, ey]];
                  if (Math.abs(cos) < 0.42 && v === 0) legs = [[s0[0], s0[1], e[0], e[1]], [e[0], e[1], e[0], Math.sin(C.a) < 0 ? box.y1 : box.y0]];
                  var legBoxes = legs.map(function (L4) { return segBox(L4[0], L4[1], L4[2], L4[3]); });
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
          best.cov.forEach(function (fi) { covered[fi] = true; });
          shown++;
          // In a rule's view a name is framed as its mark is: the rule's ink
          // where a test shows the rule enforced, lighter and open where a
          // test checks a part of it.
          var how = at.level === 'rule' && lit && lit.comps ? lit.comps[ci] : null;
          var g = sv('g', { 'class': 'sm-plate' + (self ? ' sm-plate--self' : '') + (how === 'enforce' ? ' sm-plate--full' : how === 'partly' ? ' sm-plate--part' : ''),
            'data-sm-plate': 'comp:' + c.id });
          var dl = '';
          best.legs.forEach(function (L4) { dl += 'M' + fx(L4[0]) + ' ' + fx(L4[1]) + 'L' + fx(L4[2]) + ' ' + fx(L4[3]); });
          g.appendChild(sv('path', { 'class': 'sm-leader sm-wire', d: dl, 'data-from': 'comp:' + c.id, 'data-to': null }));
          var b = best.box, sh = best.shape;
          g.appendChild(sv('rect', { 'class': 'sm-plate__box', x: fx(Math.round(b.x0) + 0.5), y: fx(Math.round(b.y0) + 0.5), width: Math.round(sh.w), height: sh.h, rx: 3 }));
          sh.lines.forEach(function (lineText, li) {
            var t = sv('text', { 'class': 'sm-plate__text sm-label', x: fx(b.x0 + sh.w / 2), y: fx(b.y0 + 13 + li * PLATE_LEAD), 'text-anchor': 'middle', 'dominant-baseline': 'central' });
            t.textContent = lineText;
            g.appendChild(t);
          });
          gPlates.appendChild(g);
          if (moving && motionOK() && g.animate) {
            try { g.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 180, delay: 120 + rank * 30, easing: EASE, fill: 'backwards' }); } catch (e) {}
          }
        });
        Object.keys(covered).forEach(function (fi) { labelBoxes[fi].g.classList.add('is-covered'); });
        lit.plated = shown;
      }

      /* ---- Pointing: the node named and lit, its own lines shown lightly ---- */
      var previewG = sv('g', { 'class': 'sm-preview', 'aria-hidden': 'true' });
      svg.insertBefore(previewG, gCore);
      function preview(key) {
        clear(previewG);
        Object.keys(nodes).forEach(function (k) { nodes[k].classList.toggle('is-hover', k === key); });
        if (!key || at.level !== 'system') return;
        var s = null;
        if (key.indexOf('comp:') === 0) { var ci = nodes[key] ? nodes[key].__ci : -1; if (ci >= 0) s = { level: 'component', comp: ci, fam: model.comps[ci].fam }; }
        else if (key.indexOf('rule:') === 0) s = { level: 'rule', rule: key.slice(5) };
        else if (key.indexOf('fam:') === 0) s = { level: 'family', fam: familyIndex(key.slice(4)) };
        if (!s || (s.level === 'family' && s.fam < 0)) return;
        var L = lightOf(s);
        litDraws(L.links).forEach(function (dr) { previewG.appendChild(litPath(dr, null, 'sm-route is-preview', false)); });
        L.cites.forEach(function (x) { previewG.appendChild(sv('path', { 'class': 'sm-rline is-preview', d: Loom.lineD(ray(x.ci, x.id)) })); });
      }

      /* ---- The first sight: the map assembles once ---- */
      /* The scale sweeps round from the top, sector by sector, the marks
         arriving along it; the doctrine blooms from the centre out (its name,
         the necklace, the axioms, their satellites, the rules between them
         and their lines); the sector names settle; the fibres at rest run out
         along their own lines last, each from the component it leaves. About
         a second and a quarter, once. */
      function assemble() {
        if (!motionOK()) return;
        function anim(elx, frames, delay, dur) {
          if (!elx || !elx.animate) return;
          try { elx.animate(frames, { duration: dur, delay: delay, easing: 'cubic-bezier(0.2, 0.7, 0.2, 1)', fill: 'backwards' }); } catch (e) {}
        }
        var POP = [{ opacity: 0, transform: 'scale(0.35)' }, { opacity: 1, transform: 'scale(1)' }];
        order.forEach(function (fi, k) {
          var S = sectors[fi];
          var frac = norm(S.mid + Math.PI / 2) / TAU;
          anim(sectorScale[fi], [{ opacity: 0 }, { opacity: 1 }], frac * 420, 360);
          model.families[fi].members.forEach(function (ci) {
            var f2 = norm(comp[ci].a + Math.PI / 2) / TAU;
            var n = nodes['comp:' + model.comps[ci].id];
            anim(n && n.querySelector ? n.querySelector('.sm-pop') : null, POP, 60 + f2 * 480, 300);
          });
          anim(labelBoxes[fi] && labelBoxes[fi].g, [{ opacity: 0 }, { opacity: 1 }], 620 + k * 30, 380);
        });
        if (D && core) {
          anim(nodes.doctrine && nodes.doctrine.querySelector('.sm-pop'), [{ opacity: 0 }, { opacity: 1 }], 0, 360);
          anim(neck, [{ opacity: 0 }, { opacity: 1 }], 80, 420);
          Object.keys(rule).forEach(function (id) {
            var q = rule[id], n = nodes['rule:' + id];
            var delay = q.role === 'hub' ? 160 : q.role === 'satellite' ? 300 : 380;
            anim(n && n.querySelector ? n.querySelector('.sm-pop') : null, POP, delay + norm(q.a + Math.PI / 2) / TAU * 160, 320);
          });
          Object.keys(spanEls).forEach(function (k) { drawIn(spanEls[k].el, 420, 460); });
        }
        if (restDrawn) {
          // A ribbon runs out before its parting fibres when its component
          // acts on the others, after them when they act on it.
          var w0 = 2 * 0.95 * ws * 1.3 * 1.25 + 3;
          revealAlong(gRest, items.map(function (it) {
            if (it.part === 'link') return { pts: it.pts, w: w0, delay: norm(comp[model.links[it.links[0]][0]].a + Math.PI / 2) / TAU * 200 };
            var S = sheaves[it.sheaf], at0 = norm(comp[S.h].a + Math.PI / 2) / TAU * 200, out = S.role === 'out';
            if (it.part === 'trunk') return { pts: it.pts, w: w0 * Math.sqrt(it.links.length), reverse: !out, delay: at0 + (out ? 0 : 260), dur: 420 };
            return { pts: it.pts, w: w0, reverse: !out, delay: at0 + (out ? 340 : 0), dur: 340 };
          }), 560, 680);
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
        el: el, svg: svg, R: R, cx: cx, cy: cy, pitch: pitchPx, sectors: sectors, named: named ? named.fs : 0,
        core: core ? { order: core.order.slice(), ring: fx(hubR), outer: fx(coreOuter), pinned: !!core.stats.orderPinned,
                       bridges: Object.keys(rule).filter(function (id) { return rule[id].role === 'bridge'; }).length,
                       glyphGap: fx(coreGap), lineGap: fx(core.stats.lineGlyphGap), nearest: fx(core.stats.nearestToCentre),
                       smallest: fx(Object.keys(rule).reduce(function (m, id) { return Math.min(m, rule[id].size); }, Infinity)) } : null,
        // Where the drawing stands, for tests and audits: its centre, the ring,
        // the radius rule lines come into the core from, the centre's name.
        frame: { cx: fx(cx), cy: fx(cy), R: fx(R), gate: fx(rGate), near: fx(NEAR * 180 / Math.PI),
                 label: labelBox ? { x0: fx(labelBox.x0), x1: fx(labelBox.x1), y0: fx(labelBox.y0), y1: fx(labelBox.y1) } : null },
        select: select, preview: preview, rove: rove, assemble: assemble, route: route,
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

    /* ---- The tip: a name where the pointer or the keyboard is ---- */
    function tipText(key) {
      if (key === 'doctrine') return { title: 'The doctrine', sub: D ? countWords(D.axioms.length, 'axiom', 'axioms') + ', ' + countWords(D.principles.length, 'principle', 'principles') + ' and ' + countWords(D.failures.length, 'failure mode', 'failure modes') : null };
      if (key.indexOf('comp:') === 0) {
        for (var i = 0; i < model.comps.length; i++) if ('comp:' + model.comps[i].id === key) {
          var c = model.comps[i];
          return { title: c.label, sub: model.families[c.fam].title + (c.cls ? ' · ' + lowerFirst(CLASS_WORDS[c.cls]) : '') };
        }
      }
      if (key.indexOf('rule:') === 0 && D && D.rules[key.slice(5)]) {
        var r = D.rules[key.slice(5)];
        return { title: r.title, sub: KIND_WORDS[r.kind] + (r.plain ? '. ' + r.plain : '') };
      }
      if (key.indexOf('fam:') === 0) {
        var F = model.families[familyIndex(key.slice(4))];
        return F ? { title: F.title, sub: countLine(F) + (F.inside ? ', ' + countFigure(F.inside, linkNoun(1), linkNoun(2)) + ' among them' : '') } : null;
      }
      return null;
    }
    function showTipFor(key, anchor) {
      var t = tipText(key);
      if (!t || !anchor || !anchor.getBoundingClientRect || !root.getBoundingClientRect) return;
      clear(tip);
      tip.appendChild(h('span', 'sm-tip__title', t.title));
      if (t.sub) tip.appendChild(h('span', 'sm-tip__sub', t.sub));
      tip.hidden = false;
      var rr = root.getBoundingClientRect(), b = anchor.getBoundingClientRect();
      var w = tip.offsetWidth || 0, hgt = tip.offsetHeight || 0;
      var x = clamp(b.left - rr.left + b.width / 2 - w / 2, 6, Math.max(6, rr.width - w - 6));
      var y = b.top - rr.top - hgt - 10;
      if (y < 6) y = b.bottom - rr.top + 10;
      if (tip.style) { tip.style.left = fx(x) + 'px'; tip.style.top = fx(y) + 'px'; }
    }
    function hideTip() { tip.hidden = true; }

    /* ---- The column beside the map ---- */
    /* At the top level the column is the band's heading, its sentence, the
       families (the page's own list, which works without this script) and a
       way into the doctrine. Below it, a panel laid over the column is the
       readable index of whatever the map lights: one name to a line, each a
       way to that thing, each lighting its mark where it stands. A long list
       shows eight and the rest on request; a long page scrolls in place and
       says so; the links at its foot stay in view. */
    var column = makeColumn();
    function makeColumn() {
      var host = section && section.querySelector ? section.querySelector('.home-split__text') : null;
      var noop = { sync: function () {}, lit: function () {}, state: function () { return null; }, ready: function () {}, rows: function () {}, refit: function () {} };
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
      function goLink(href, text, primary) {
        var a = h('a', 'sc__go' + (primary ? ' sc__go--primary' : ''), text);
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
        b.addEventListener('click', function (e) { onPress(e); });
        b.addEventListener('pointerenter', function () { pulse(key); });
        b.addEventListener('pointerleave', function () { unpulse(key); });
        b.addEventListener('focus', function () { pulse(key); });
        b.addEventListener('blur', function () { unpulse(key); });
        li.appendChild(b);
        return li;
      }
      function pulse(key) {
        var n = map && map.nodeOf(key);
        if (!n) return;
        n.classList.add('is-pulse');
        showTipFor(key, n);
      }
      function unpulse(key) {
        var n = map && map.nodeOf(key);
        if (n) n.classList.remove('is-pulse');
        hideTip();
      }
      function list(label, items, capKey, count, two) {
        var wrap = h('div', 'sc__block');
        var headEl = h('p', 'sc__label');
        headEl.appendChild(h('span', null, label));
        headEl.appendChild(h('span', 'sc__label-n', ' · ' + (count === undefined ? items.length : count)));
        wrap.appendChild(headEl);
        var ul = h('ul', 'sc__list' + (two && items.length > 1 ? ' sc__list--two' : ''));
        var cap = capKey && caps[capKey] !== undefined ? caps[capKey] : 8;
        var open = !capKey || opened[capKey] || items.length <= cap + 1, showN = open ? items.length : cap;
        items.slice(0, showN).forEach(function (li) { ul.appendChild(li); });
        if (capKey && opened[capKey] && items.length > cap) wrap.setAttribute('data-opened', '1');
        if (capKey && !opened[capKey]) {
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
      function scroller(node) {
        var sc = h('div', 'sc__scroll');
        sc.setAttribute('tabindex', '0');
        node.appendChild(sc);
        return sc;
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
      function ruleItem(id, note) {
        return item('rule:' + id, D.rules[id].title, note || null, function (e) { goDoctrine(id, { keyed: keyedClick(e) }); },
          { cls: 'sc__item--rule', rule: D.rules[id].kind });
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
        headEl.appendChild(h('h3', 'sc__title', F.title));
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
            return none === F.members.length ? ' None of its components has one.' : none ? ' ' + none + ' of its ' + F.members.length + ' components have none.' : '';
          })()));
        node.appendChild(headEl);
        var sc = scroller(node);
        sc.appendChild(list('Its components', F.members.map(function (ci) { return compItem(ci, null); }), 'fam:' + fi));
        partners.sort(function (p, q) { return q.n - p.n; });
        if (partners.length) {
          sc.appendChild(list(capital(linkNoun(2)) + ' with other families', partners.map(function (p) {
            var G = model.families[p.fam];
            return item('fam:' + G.key, G.title, p.out + ' to, ' + p.inn + ' from', function (e) { goFamily(p.fam, { keyed: keyedClick(e) }); });
          }), null));
        }
        sc.appendChild(line('sc__note', linkNote()));
        var act = actions([F.page ? goLink(F.page, 'Family page', true) : null]);
        if (act) node.appendChild(act);
        return node;
      }

      function compPage(ci) {
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
        var sc = scroller(node);
        if (info) {
          var enf = function (id) { return info.enforces.indexOf(id) >= 0 ? 'Enforced here' : info.partly.indexOf(id) >= 0 ? 'Partly checked here' : null; };
          var noted = function (ids) { return ids.some(function (id) { return !!enf(id); }); };
          // The principles and the axioms its paper module cites, in one list,
          // each with its own glyph.
          var cited = ordered(info.gov, D.principles).concat(ordered(info.abide, D.axioms));
          if (cited.length) sc.appendChild(list('Its ' + lowerFirst(info.source || 'paper module') + ' cites', cited.map(function (id) { return ruleItem(id, enf(id)); }),
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
        var act = actions([
          c.page ? goLink(c.page, 'Component page', true) : null,
          c.reader ? goLink(c.reader, 'Paper module', !c.page) : null,
          c.source ? goLink(c.source, 'Source', false) : null
        ]);
        if (act) node.appendChild(act);
        return node;
      }

      function doctrinePage() {
        var node = page('doctrine');
        var headEl = h('div', 'sc__head');
        headEl.appendChild(line('sc__kicker sc__kicker--doctrine', 'At the centre'));
        headEl.appendChild(h('h3', 'sc__title', 'The doctrine'));
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
        headEl.appendChild(h('h3', 'sc__title', r.title));
        if (r.plain) headEl.appendChild(line('sc__lede', r.plain));
        node.appendChild(headEl);
        var sc = scroller(node);
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
        var act = actions([r.doctrine ? goLink(r.doctrine, 'Read its doctrine card', true) : null]);
        if (act) node.appendChild(act);
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
        return at.level === 'rule' ? rulePage(at.rule) : at.level === 'doctrine' ? doctrinePage() :
          at.level === 'family' ? famPage(at.fam) : compPage(at.comp);
      }
      // A page built again in place (a list opened), its scroll kept.
      function rebuild(focusGroup) {
        if (!shown) return;
        var sc = shown.node.querySelector ? shown.node.querySelector('.sc__scroll') : null, top = sc ? sc.scrollTop : 0;
        var node = build();
        panel.replaceChild ? panel.replaceChild(node, shown.node) : (panel.removeChild(shown.node), panel.appendChild(node));
        shown.node = node;
        fitScroll(node);
        var sc2 = node.querySelector ? node.querySelector('.sc__scroll') : null;
        if (sc2) sc2.scrollTop = top;
        if (focusGroup && node.querySelectorAll) {
          var g = Array.prototype.filter.call(node.querySelectorAll('.sc__group-btn'), function (b) { return b.getAttribute('aria-expanded') !== null; });
          if (g[0] && g[0].focus) g[0].focus();
        }
      }
      function sync(how) {
        how = how || {};
        wireDoctrineRow();
        var key = wantKey();
        if (!key) { close(); return; }
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
        panel.inert = false;
        panel.removeAttribute('aria-hidden');
        if (panel.classList) panel.classList.add('is-open');
        if (host.classList) host.classList.add('sc-host--open');
        node = tighten(node);
        fitScroll(node);
        if (motionOK() && !how.instant && node.animate) {
          try { node.animate([{ opacity: 0, transform: 'translateY(6px)' }, { opacity: 1, transform: 'none' }], { duration: 300, easing: EASE }); } catch (e) {}
        }
        // Replacing a long phone column can leave its new title behind the
        // sticky header after the browser preserves the old scroll position.
        if (pageMode && window.requestAnimationFrame) window.requestAnimationFrame(function () {
          if (!shown || shown.node !== node || !document.querySelector || !window.scrollBy) return;
          var bar = document.querySelector('.docs-topbar');
          var title = node.querySelector('.sc__title');
          if (!bar || !title) return;
          var edge = Math.max(0, bar.getBoundingClientRect().bottom) + 12;
          var top = title.getBoundingClientRect().top;
          if (top < edge) window.scrollBy({ top: top - edge, behavior: 'instant' });
        });
      }
      function close() {
        var old = shown && shown.node;
        shown = null;
        panel.inert = true;
        panel.setAttribute('aria-hidden', 'true');
        if (panel.classList) panel.classList.remove('is-open');
        if (host.classList) host.classList.remove('sc-host--open');
        if (old && old.parentNode) old.parentNode.removeChild(old);
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
        sync: sync, lit: lit, rows: wireRows,
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
    // The map band's two slides share one height. While the system slide is
    // away its card is parked (folded to nothing), so a tall view never
    // leaves the mathematics slide standing in empty space.
    function park(on) {
      if (!slide || pageMode || !stage.classList) return;
      stage.classList.toggle('is-parked', !!on);
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
      if (map.svg.classList) map.svg.classList.remove('awaits-reveal');
      map.assemble();
    }
    // Without the opening (reduced motion, or a view chosen before it), the
    // map simply shows.
    function settleReveal() {
      revealed = true;
      if (map && map.svg.classList) map.svg.classList.remove('awaits-reveal');
    }
    // The card keeps the whole system's height as its least, so a view
    // never makes the band jump shorter.
    function measureFloor() {
      if (at.level !== 'system' || !stage.style || !stage.getBoundingClientRect) return;
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
          ring: map ? { radius: map.R, pitch: map.pitch, named: map.named, core: map.core, frame: map.frame, sheaves: map.sheaves,
                        order: ring.order.map(function (fi) { return model.families[fi].id; }) } : null,
          counts: { families: model.families.length, components: model.comps.length, links: model.links.length,
                    bands: model.pairs.length, dropped: model.dropped, kinds: model.kinds.slice() },
          lit: L ? { comps: Object.keys(L.comps).length, rules: Object.keys(L.rules).length, routes: L.links.length, lines: L.cites.length,
                     spans: Object.keys(L.spans).length, reticles: L.reticles.slice(), open: L.open.slice(), plates: L.plated || 0 } : null,
          weave: map ? map.weave() : null,
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
    var frame = 0, lastWidth = 0;
    function refresh() {
      if (!model || !map) return;
      var w = area.getBoundingClientRect ? area.getBoundingClientRect().width : 0;
      if (w && Math.abs(w - lastWidth) > 1) { lastWidth = w; relayout(); }
      measureFloor();
      column.refit();
    }
    function watchSize() {
      lastWidth = area.getBoundingClientRect ? area.getBoundingClientRect().width : 0;
      var raf = window.requestAnimationFrame || function (fn) { return setTimeout(fn, 16); };
      function later() { if (frame) return; frame = raf(function () { frame = 0; refresh(); }); }
      if ('ResizeObserver' in window) new window.ResizeObserver(later).observe(area);
      if (window.addEventListener) window.addEventListener('resize', later);
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
