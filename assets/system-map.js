/* Plectis: the system map.
   The earlier software toolkit's components, drawn as a precision schematic:
   an exploded elevation of one engineered object, in which every part shows
   how it connects to every other.

   The shared path runs across the middle as the structural spine, its steps
   as stations with tick rules, in their declared order. The families are
   plates stacked above and below it, each sized by its components and joined
   to the spine by an assembly line (every family uses the shared path). The
   components are marks on one lattice, their form and colour set by their
   evidence class. The declared links are traces routed orthogonally with one
   bend radius: along the gutters of a plate, and between plates in lanes
   beside the spine, one lane per pair of plates. A trace meets a component
   with an end cap: a dot where it leaves the component that names the other,
   a bar where it reaches the component named.

   Three levels, each a step down. At rest the whole structure reads as the
   families round the shared path. A family selected on the map (or pointed
   at in the landing's list) comes forward: its plate opens into a sheet that
   names every component, its links inside the family drawn as nested
   brackets, while everything else recedes and a card beside it describes
   the family. A component selected there gets the card: what it does, what
   backs it, the components it names and those that name it. Escape, or a
   click on empty ground, steps back one level.

   Everything drawn comes from docs/architecture-graph-scene.json, the scene
   the architecture map reads; the script parses it once and keeps only what
   it draws. Family membership is navigation grouping. A named neighbour is
   the source's own declaration, not proof that one component calls another,
   nor of causation, maturity or correctness. Colour belongs to evidence
   alone: ember marks the components whose evidence runs real tools, and
   everything else is ink. Every number drawn is a count from the scene.

   Motion has a cause or is the figure's one opening. The structure assembles
   once, when it first comes into view and has settled: the spine draws out,
   the plates settle onto it from their exploded places, the components set,
   and the links route in last, in about a second and a quarter. A plate
   opens and closes in concert, every mark travelling to its place. Under
   the pointer a component's links trace out in their declared direction and
   settle. Nothing moves while the reader is idle; under reduced motion every
   final state is drawn at once. The canvas paints on demand, caps the device
   pixel ratio at 2, and does not paint off screen or in a hidden tab. */
(function () {
  'use strict';

  var SERIF = '"Plectis Serif", "Plectis Math", "Plectis Serif Fallback", "Iowan Old Style", Georgia, serif';
  var TAU = Math.PI * 2;

  /* ---- Curves ------------------------------------------------------- */
  /* The site's two curves, solved exactly: an arrival settles hard,
     cubic-bezier(0.16, 1, 0.3, 1); a move eases in and out,
     (0.65, 0, 0.35, 1). No bounce, no overshoot. */
  function cubicBezier(x1, y1, x2, y2) {
    var cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    var cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    function sx(t) { return ((ax * t + bx) * t + cx) * t; }
    function sy(t) { return ((ay * t + by) * t + cy) * t; }
    function dx(t) { return (3 * ax * t + 2 * bx) * t + cx; }
    return function (x) {
      if (!(x > 0)) return 0;
      if (x >= 1) return 1;
      var t = x, i;
      for (i = 0; i < 8; i++) {
        var err = sx(t) - x, d = dx(t);
        if (Math.abs(err) < 1e-6) return sy(t);
        if (Math.abs(d) < 1e-6) break;
        t -= err / d;
        if (t < 0 || t > 1) break;
      }
      var lo = 0, hi = 1;
      t = x;
      for (i = 0; i < 32; i++) {
        var v = sx(t);
        if (Math.abs(v - x) < 1e-6) break;
        if (v < x) lo = t; else hi = t;
        t = (lo + hi) / 2;
      }
      return sy(t);
    };
  }
  var DETENT = cubicBezier(0.16, 1, 0.3, 1);
  var MOVE = cubicBezier(0.65, 0, 0.35, 1);

  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function unit(t) { return t <= 0 ? 0 : t >= 1 ? 1 : t; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function isObj(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
  function str(v) { return typeof v === 'string' && v.trim() ? v.trim() : null; }
  function lowerFirst(text) { return text ? text.charAt(0).toLowerCase() + text.slice(1) : text; }
  function plural(n, one, many) { return n === 1 ? one : many; }

  /* ---- Colour -------------------------------------------------------- */
  function parseColor(c) {
    c = String(c || '').trim();
    var m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(c);
    if (m) {
      var h = m[1].length === 3 ? m[1].replace(/(.)/g, '$1$1') : m[1];
      return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16), 1];
    }
    m = /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:\s*[,/]\s*([\d.]+)(%?))?\s*\)$/i.exec(c);
    if (m) {
      var a = m[4] == null ? 1 : (m[5] ? parseFloat(m[4]) / 100 : +m[4]);
      return [+m[1], +m[2], +m[3], a];
    }
    return null;
  }
  function rgba(rgb, a) {
    return 'rgba(' + Math.round(rgb[0]) + ',' + Math.round(rgb[1]) + ',' + Math.round(rgb[2]) + ',' +
      (Math.round(clamp(a, 0, 1) * 1000) / 1000) + ')';
  }
  function luminance(rgb) {
    return rgb ? (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255 : 1;
  }

  /* ---- Evidence ------------------------------------------------------ */
  /* Five classes, named in plain words, each with its own mark, so colour is
     never the only signal. Ember marks the two that run real tools; the
     other three are ink. */
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
  var EMBER = { tool: true, bounded: true };
  function classOf(ev) {
    if (!isObj(ev)) return null;
    if (CLASS_OF[ev.class_id]) return CLASS_OF[ev.class_id];
    if (ev.runs_real_tools === true) return 'tool';
    var rank = +ev.rank;
    if (rank >= 5) return 'import';
    if (rank >= 4) return 'contract';
    return rank > 0 ? 'computes' : null;
  }

  /* ---- Scene --------------------------------------------------------- */
  /* Reads the published scene into the few things the drawing needs. Bad
     rows (duplicate ids, edges to unknown nodes, repeated edges) are dropped
     and the rest is kept; the landing never throws on a stale or partial
     scene. A scene built before the per-object details existed still lays
     out: its marks carry no class, its legend lists only the links, and its
     buttons go to the architecture map, whose #map= addresses are part of
     the data contract. */
  function routeWith(base, docsHref, siteHref) {
    var d = str(docsHref);
    if (d) return /^(?:[a-z][a-z0-9+.-]*:|\/|#)/i.test(d) ? d : base + d;
    return str(siteHref);
  }
  function humanize(key) {
    var t = String(key).replace(/_/g, ' ');
    return t.charAt(0).toUpperCase() + t.slice(1);
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
    var seen = Object.create(null);
    var areaNodes = [], compNodes = [], stepNodes = [];
    scene.nodes.forEach(function (n, at) {
      if (!isObj(n)) return;
      var id = str(n.id);
      if (!id || seen[id]) return;
      seen[id] = { node: n, at: at };
      if (n.kind === 'area') areaNodes.push(n);
      else if (n.kind === 'wired_component' || n.kind === 'component') compNodes.push(n);
      else if (n.kind === 'spine_step') stepNodes.push(n);
    });
    function detailOf(n) {
      var body = details[str(n.inspector_ref) || 'inspector:' + n.id];
      return isObj(body) ? body : null;
    }
    function routesOf(n, d) {
      if (d && isObj(d.routes)) return d.routes;
      return isObj(nodeRoutes[n.id]) ? nodeRoutes[n.id] : {};
    }
    function mapRoute(id, r) {
      return routeWith(base, r.map_href, r.site_map_href) ||
        base + 'architecture.html#map=' + encodeURIComponent(id);
    }

    var families = [], famAt = Object.create(null);
    areaNodes.forEach(function (n) {
      var key = n.id.replace(/^area:/, '');
      if (famAt[key] !== undefined) return;
      var d = detailOf(n), r = routesOf(n, d);
      famAt[key] = families.length;
      families.push({
        id: n.id, key: key,
        title: str(d && d.title) || str(n.label) || humanize(key),
        summary: str(d && d.summary) || str(n.summary),
        page: routeWith(base, r.primary_reader_href, r.site_primary_reader_href),
        mapHref: mapRoute(n.id, r),
        members: []
      });
    });

    var comps = [], compAt = Object.create(null);
    compNodes.forEach(function (n) {
      var d = detailOf(n);
      var key = str(d && d.family_id) || (str(n.parent_cluster_id) || '').replace(/^cluster:/, '');
      if (!key) return;
      if (famAt[key] === undefined) {
        famAt[key] = families.length;
        families.push({ id: 'area:' + key, key: key,
          title: clusterLabel['cluster:' + key] || humanize(key), summary: null, page: null,
          mapHref: base + 'architecture.html#map=' + encodeURIComponent('area:' + key), members: [] });
      }
      var ev = d && isObj(d.evidence) ? d.evidence : null;
      var r = routesOf(n, d);
      compAt[n.id] = comps.length;
      comps.push({
        id: n.id,
        label: str(d && d.public_label) || str(d && d.title) || str(n.label) || n.id,
        fam: famAt[key],
        cls: classOf(ev),
        basis: str(ev && ev.basis),
        line: str(d && d.summary_line),
        page: routeWith(base, r.component_detail_href, r.site_component_detail_href),
        reader: routeWith(base, r.primary_reader_href, r.site_primary_reader_href),
        mapHref: mapRoute(n.id, r),
        out: [], inc: []
      });
    });

    var links = [], linkSeen = Object.create(null), edgeSeen = Object.create(null);
    var spineNext = Object.create(null), spinePrev = Object.create(null), bindCount = 0;
    var dropped = 0;
    (Array.isArray(scene.edges) ? scene.edges : []).forEach(function (e) {
      if (!isObj(e)) { dropped++; return; }
      var eid = str(e.id);
      if (eid) {
        if (edgeSeen[eid]) { dropped++; return; }
        edgeSeen[eid] = true;
      }
      var s = str(e.source), t = str(e.target);
      if (!s || !t || !seen[s] || !seen[t]) { dropped++; return; }
      var rel = e.relation || e.kind;
      if (rel === 'declared_dependency_untyped') {
        var a = compAt[s], b = compAt[t];
        if (a === undefined || b === undefined || a === b) { dropped++; return; }
        if (linkSeen[a + '>' + b]) { dropped++; return; }
        linkSeen[a + '>' + b] = true;
        links.push([a, b]);
        comps[a].out.push(b);
        comps[b].inc.push(a);
      } else if (rel === 'spine_sequence') {
        if (!spineNext[s]) spineNext[s] = t;
        spinePrev[t] = true;
      } else if (rel === 'binds_to_shared_path') {
        bindCount++;
      }
    });

    // The shared path's steps in their declared order: follow the sequence
    // from its one head; a broken chain falls back to the steps' own order.
    var stepOf = Object.create(null);
    stepNodes.forEach(function (n) { stepOf[n.id] = n; });
    var ordered = [];
    var heads = stepNodes.filter(function (n) { return !spinePrev[n.id]; });
    if (heads.length === 1) {
      var used = Object.create(null), at = heads[0];
      while (at && !used[at.id]) { used[at.id] = true; ordered.push(at); at = stepOf[spineNext[at.id]]; }
    }
    if (ordered.length !== stepNodes.length) {
      ordered = stepNodes.slice().sort(function (a, b) {
        var oa = a.metrics && isFinite(a.metrics.order) ? +a.metrics.order : 1e9;
        var ob = b.metrics && isFinite(b.metrics.order) ? +b.metrics.order : 1e9;
        return oa - ob || seen[a.id].at - seen[b.id].at;
      });
    }
    var steps = ordered.map(function (n, i) {
      var d = detailOf(n), r = routesOf(n, d);
      return { id: n.id, title: str(d && d.title) || str(n.label) || humanize(n.id), order: i + 1, mapHref: mapRoute(n.id, r) };
    });

    // A family is drawn only when it has components; indices are remapped.
    var keep = families.map(function () { return false; });
    comps.forEach(function (c) { keep[c.fam] = true; });
    var remap = [], kept = [];
    families.forEach(function (f, i) { if (keep[i]) { remap[i] = kept.length; kept.push(f); } });
    families = kept;
    comps.forEach(function (c, i) { c.fam = remap[c.fam]; families[c.fam].members.push(i); });
    families.forEach(function (f) { f.within = 0; f.cross = 0; });
    links.forEach(function (l) {
      var fa = comps[l[0]].fam, fb = comps[l[1]].fam;
      if (fa === fb) families[fa].within++;
      else { families[fa].cross++; families[fb].cross++; }
    });
    // Components are set by evidence class (the legend's order), then by how
    // many components they name or are named by, then by name.
    families.forEach(function (f) {
      f.members.sort(function (a, b) {
        var ca = comps[a].cls ? CLASS_ORDER.indexOf(comps[a].cls) : 9;
        var cb = comps[b].cls ? CLASS_ORDER.indexOf(comps[b].cls) : 9;
        var da = comps[a].out.length + comps[a].inc.length, db = comps[b].out.length + comps[b].inc.length;
        return ca - cb || db - da || (comps[a].label < comps[b].label ? -1 : comps[a].label > comps[b].label ? 1 : a - b);
      });
      f.members.forEach(function (ci, slot) { comps[ci].slot = slot; });
    });

    var legend = [];
    CLASS_ORDER.forEach(function (cls) {
      var count = comps.filter(function (c) { return c.cls === cls; }).length;
      if (count) legend.push({ cls: cls, count: count, label: CLASS_WORDS[cls] });
    });
    if (links.length) legend.push({ cls: 'link', count: links.length, label: 'Names another' });

    return {
      families: families, comps: comps, links: links, steps: steps, legend: legend,
      bindCount: bindCount, dropped: dropped,
      stale: !Object.keys(details).length
    };
  }

  /* ---- Routed paths -------------------------------------------------- */
  // Drops repeated points and points in the middle of a straight run.
  function simplify(pts) {
    var out = [];
    pts.forEach(function (q) {
      var last = out[out.length - 1];
      if (last && Math.abs(last[0] - q[0]) < 0.01 && Math.abs(last[1] - q[1]) < 0.01) return;
      out.push([q[0], q[1]]);
      while (out.length >= 3) {
        var a = out[out.length - 3], b = out[out.length - 2], c = out[out.length - 1];
        var cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]);
        if (Math.abs(cross) > 0.01) break;
        out.splice(out.length - 2, 1);
      }
    });
    return out;
  }
  /* An orthogonal polyline as lines and quarter arcs, every bend the same
     radius (smaller only where a run is too short to hold it), each piece
     with its length, so a route can be drawn part of the way. */
  function roundedPath(pts, rb) {
    var prims = [], length = 0, n = pts.length, cur;
    function line(a, b) {
      var len = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (len < 0.01) return;
      prims.push({ arc: false, from: a, to: b, len: len });
      length += len;
    }
    if (n < 2) return { prims: prims, length: 0, points: pts };
    cur = pts[0];
    for (var i = 1; i < n; i++) {
      var p0 = pts[i - 1], p1 = pts[i];
      if (i === n - 1) { line(cur, p1); break; }
      var p2 = pts[i + 1];
      var inLen = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]), outLen = Math.hypot(p2[0] - p1[0], p2[1] - p1[1]);
      var din = [(p1[0] - p0[0]) / inLen, (p1[1] - p0[1]) / inLen];
      var dout = [(p2[0] - p1[0]) / outLen, (p2[1] - p1[1]) / outLen];
      var r = Math.min(rb, inLen * (i === 1 ? 1 : 0.5), outLen * (i + 1 === n - 1 ? 1 : 0.5));
      var t1 = [p1[0] - din[0] * r, p1[1] - din[1] * r];
      var t2 = [p1[0] + dout[0] * r, p1[1] + dout[1] * r];
      line(cur, t1);
      var cross = din[0] * dout[1] - din[1] * dout[0];
      if (r > 0.05 && Math.abs(cross) > 0.5) {
        var ccx = t1[0] + dout[0] * r, ccy = t1[1] + dout[1] * r, len = r * Math.PI / 2;
        prims.push({ arc: true, cx: ccx, cy: ccy, r: r, a0: Math.atan2(t1[1] - ccy, t1[0] - ccx),
                     sweep: cross > 0 ? Math.PI / 2 : -Math.PI / 2, from: t1, to: t2, len: len });
        length += len;
        cur = t2;
      } else {
        line(t1, p1);
        cur = p1;
      }
    }
    return { prims: prims, length: length, points: pts };
  }
  // Adds a route to the current path, from its start for `upto` pixels.
  function tracePath(ctx, path, upto, dx, dy) {
    var left = upto == null ? Infinity : upto, started = false;
    dx = dx || 0; dy = dy || 0;
    for (var i = 0; i < path.prims.length && left > 0; i++) {
      var q = path.prims[i], f = Math.min(1, left / q.len);
      if (!started) { ctx.moveTo(q.from[0] + dx, q.from[1] + dy); started = true; }
      if (q.arc) ctx.arc(q.cx + dx, q.cy + dy, q.r, q.a0, q.a0 + q.sweep * f, q.sweep < 0);
      else ctx.lineTo(q.from[0] + dx + (q.to[0] - q.from[0]) * f, q.from[1] + dy + (q.to[1] - q.from[1]) * f);
      left -= q.len;
    }
  }
  // A rectangle with its four corners cut at 45 degrees.
  function chamfered(x0, y0, x1, y1, k) {
    k = Math.max(0, Math.min(k, (x1 - x0) / 2, (y1 - y0) / 2));
    return [[x0 + k, y0], [x1 - k, y0], [x1, y0 + k], [x1, y1 - k], [x1 - k, y1], [x0 + k, y1], [x0, y1 - k], [x0, y0 + k]];
  }
  // Greedy interval packing: shortest spans first, each into the first lane
  // free along its whole span (with a margin).
  function packLanes(items, margin) {
    var lanes = [];
    items.slice().sort(function (a, b) {
      return (a.hi - a.lo) - (b.hi - b.lo) || a.lo - b.lo || (a.key < b.key ? -1 : a.key > b.key ? 1 : 0);
    }).forEach(function (it) {
      for (var k = 0; ; k++) {
        if (!lanes[k]) lanes[k] = [];
        var clash = lanes[k].some(function (iv) { return it.lo < iv[1] + margin && it.hi > iv[0] - margin; });
        if (!clash) { lanes[k].push([it.lo, it.hi]); it.lane = k; break; }
      }
    });
    return lanes.length;
  }

  /* ---- Layout -------------------------------------------------------- */
  /* Decided entirely by the scene and the canvas box, so the drawing is the
     same on every visit. It is laid out in a landscape frame and transposed
     when the box is taller than wide, so a phone gets a vertical spine with
     the plates either side. Families keep the scene's order: the first half
     along the top row, the rest along the bottom, as the landing's family
     list reads. Everything stands on one lattice of pitch p: components on
     its points, traces in the gutters half a pitch between them. */
  function layoutSchematic(model, w, h, measure, dpr, opts) {
    var geo = { w: w, h: h, ok: false };
    dpr = dpr || 1;
    // The device-pixel grid: lengths in whole device pixels and line centres
    // on the middle of a device pixel, so a one-pixel hairline lands on one
    // pixel row or column and never smears across two.
    function whole(v) { return Math.round(v * dpr) / dpr; }
    function half(v) { return (Math.floor(v * dpr) + 0.5) / dpr; }
    var nFam = model.families.length, nStep = model.steps.length;
    if (!(w >= 160 && h >= 120) || !nFam) return geo;
    var portrait = h > w * 1.04;
    var s = clamp(Math.min(w / 677, h / 569), 0.5, 1.7), rs = Math.sqrt(s);
    var fEng = clamp(11.2 * rs, 9, 13.5), fStep = clamp(10.6 * rs, 8.6, 12.5), fLeg = clamp(10.2 * rs, 8.6, 12);
    var fontEng = '500 ' + fEng.toFixed(2) + 'px ' + SERIF;
    var fontCount = '400 ' + fEng.toFixed(2) + 'px ' + SERIF;
    var fontStep = 'italic 400 ' + fStep.toFixed(2) + 'px ' + SERIF;
    var fontLeg = '400 ' + fLeg.toFixed(2) + 'px ' + SERIF;
    var mr = clamp(4.4 * Math.pow(s, 0.6), 3, 6.4);       // a component mark's radius
    var m = whole(clamp(12 * s, 7, 18));                   // margin inside the canvas
    var padX = clamp(9 * s, 6, 13), padY = clamp(7 * s, 5, 11);
    var gap = clamp(8 * s, 5, 12), gm = whole(clamp(5 * s, 3.5, 7));
    var cham = clamp(5 * s, 3.5, 7);                       // the plates' chamfer
    var rb = clamp(3.2 * s, 2.2, 4.6);                     // every bend of every trace
    var laneGap = Math.max(1 / dpr, whole(clamp(3 * s, 2.2, 3.8))), laneMargin = whole(clamp(6 * s, 4, 9));
    var railH = 2 * whole(clamp(3.5 * s, 2.5, 4.75)), tickL = clamp(4 * s, 3, 6), gapL = clamp(4 * s, 3, 6);
    var capGap = clamp(1.6 * s, 1.2, 2.4);
    var lineEng = fEng * 1.3, lineLeg = fLeg * 1.62;
    var asc = 0.74, desc = 0.26;

    /* The legend runs along the foot: the five classes with their counts,
       then the trace with its two end caps, in as few rows as fit. */
    var legItems = model.legend.map(function (it) {
      var lw = measure(it.label, fontLeg), cw = measure(String(it.count), fontLeg);
      var glyph = it.cls === 'link' ? clamp(18 * s, 14, 24) : 2 * mr + 2;
      return { cls: it.cls, label: it.label, count: it.count, lw: lw, cw: cw, glyph: glyph,
               w: glyph + clamp(5 * s, 4, 7) + lw + clamp(4 * s, 3, 6) + cw };
    });
    var innerW = w - 2 * m, legGap = clamp(16 * s, 10, 24);
    function rowWidth(row) { return row.reduce(function (t, it) { return t + it.w; }, 0) + legGap * Math.max(0, row.length - 1); }
    var legRows = [];
    if (legItems.length) {
      for (var per = legItems.length; per >= 1; per--) {
        var trial = [];
        for (var li0 = 0; li0 < legItems.length; li0 += per) trial.push(legItems.slice(li0, li0 + per));
        // Balance the rows: the same number of rows with the most even split.
        var nRows = trial.length, even = Math.ceil(legItems.length / nRows);
        trial = [];
        for (var li1 = 0; li1 < legItems.length; li1 += even) trial.push(legItems.slice(li1, li1 + even));
        if (trial.every(function (r) { return rowWidth(r) <= innerW; })) { legRows = trial; break; }
      }
      if (!legRows.length) legRows = legItems.map(function (it) { return [it]; });
    }
    if (opts && opts.noLegend) legRows = [];
    var legendH = legRows.length ? legRows.length * lineLeg + padY * 0.5 : 0;

    var X0 = m, Y0 = m, X1 = w - m, Y1 = h - m - legendH;
    var VW = portrait ? Y1 - Y0 : X1 - X0, VH = portrait ? X1 - X0 : Y1 - Y0;
    if (VW < 80 || VH < 80) return geo;
    function T(vx, vy) { return portrait ? [X0 + vy, Y0 + vx] : [X0 + vx, Y0 + vy]; }

    /* The spine: one rail across the frame with a station per step, evenly
       spaced, each named beside its tick rule, the names alternating sides so
       neighbours never crowd. */
    var stepLabels = model.steps.map(function (st, i) {
      var tw = measure(st.title, fontStep), th = fStep * 1.2;
      return { text: st.title, tw: tw, th: th, side: i % 2 === 0 ? -1 : 1 };
    });
    var sx0, sx1;
    function placeStations() {
      var firstW = stepLabels.length ? (portrait ? stepLabels[0].th : stepLabels[0].tw) : 0;
      var lastW = stepLabels.length ? (portrait ? stepLabels[stepLabels.length - 1].th : stepLabels[stepLabels.length - 1].tw) : 0;
      sx0 = Math.max(padX * 1.5, firstW / 2 + 2);
      sx1 = VW - Math.max(padX * 1.5, lastW / 2 + 2);
    }
    placeStations();
    // Two landscape names that share a side stand two stations apart; when
    // even that is too tight they are set smaller, and below a floor the
    // names give way and the stations keep their ticks.
    var stepNames = true;
    if (!portrait && nStep > 2) {
      var room = 2 * (sx1 - sx0) / (nStep - 1) - 10;
      var widest = Math.max.apply(null, stepLabels.map(function (l) { return l.tw; }));
      if (widest > room) {
        var shrink = room / widest;
        if (shrink < 0.78) stepNames = false;
        else {
          fStep *= shrink;
          fontStep = 'italic 400 ' + fStep.toFixed(2) + 'px ' + SERIF;
          stepLabels.forEach(function (l) { l.tw = measure(l.text, fontStep); l.th = fStep * 1.2; });
          placeStations();
        }
      }
    }
    // Beside a vertical spine the names would take a third of a narrow
    // width; there they give way, and a station names itself when pointed
    // at or tapped.
    if (portrait && 2 * stepLabels.reduce(function (t, l) { return Math.max(t, l.tw); }, 0) > 0.2 * VH) stepNames = false;
    var labDepth = stepNames ? stepLabels.reduce(function (t, l) { return Math.max(t, portrait ? l.tw : l.th); }, 0) : 0;
    var halfBand = railH / 2 + tickL + (stepNames ? gapL + labDepth : 2);
    var stations = model.steps.map(function (st, i) {
      return { vx: half(nStep > 1 ? sx0 + (sx1 - sx0) * i / (nStep - 1) : VW / 2) };
    });
    // A vertical trace that crosses the spine must not run through a name.
    function crossesName(vx) {
      if (!stepNames) return false;
      for (var i = 0; i < stations.length; i++) {
        var half = (portrait ? stepLabels[i].th : stepLabels[i].tw) / 2 + 3;
        if (Math.abs(vx - stations[i].vx) < half) return true;
      }
      return false;
    }

    /* The plates. A row is shared by its families in proportion to their
       components, but never narrower than the family's engraving. */
    var topN = Math.ceil(nFam / 2);
    var rows = [[], []];
    model.families.forEach(function (f, i) { rows[i < topN ? 0 : 1].push(i); });
    function wrapName(text, maxW, font) {
      var words = text.split(/\s+/), lines = [], cur = '';
      words.forEach(function (word) {
        var next = cur ? cur + ' ' + word : word;
        if (!cur || measure(next, font) <= maxW) cur = next;
        else { lines.push(cur); cur = word; }
      });
      if (cur) lines.push(cur);
      return lines;
    }
    var engr = model.families.map(function (f) {
      var nameW = measure(f.title, fontEng), countText = String(f.members.length);
      var cw = measure(countText, fontCount), gapC = clamp(10 * s, 6, 14);
      var words = f.title.split(/\s+/), best = nameW + gapC + cw;
      for (var cut = 1; cut < words.length; cut++) {
        var wa = measure(words.slice(0, cut).join(' '), fontEng), wb = measure(words.slice(cut).join(' '), fontEng);
        best = Math.min(best, Math.max(wa, wb) + gapC + cw);
      }
      return { nameW: nameW, countText: countText, cw: cw, gapC: gapC, minW: best };
    });
    var depthGuess = (VH - 2 * halfBand) / 2 - 2 * padY - 30 * s;
    var extraMin = {};
    function minPlate(fi) {
      var e = engr[fi], least;
      if (portrait) {
        var nl = wrapName(model.families[fi].title, Math.max(30, depthGuess - e.cw - e.gapC), fontEng).length;
        least = nl * lineEng + padY * 1.4 + 2 * mr + 2 * gm + 8;
      } else {
        least = Math.max(e.minW + 2 * padX, 2 * mr + 2 * gm + 8);
      }
      return Math.max(least, extraMin[fi] || 0);
    }
    function allocate(row, ri) {
      var total = VW - gap * (row.length - 1);
      var minW = row.map(minPlate), n = row.map(function (fi) { return model.families[fi].members.length; });
      var widths = row.map(function () { return 0; }), fixed = row.map(function () { return false; });
      for (var iter = 0; iter <= row.length; iter++) {
        var free = total, freeN = 0;
        row.forEach(function (fi, j) { if (fixed[j]) free -= widths[j]; else freeN += n[j]; });
        var changed = false;
        row.forEach(function (fi, j) { if (!fixed[j]) widths[j] = freeN ? free * n[j] / freeN : free / row.length; });
        row.forEach(function (fi, j) {
          if (!fixed[j] && widths[j] < minW[j]) { widths[j] = minW[j]; fixed[j] = true; changed = true; }
        });
        if (!changed) break;
      }
      var sum = widths.reduce(function (t, v) { return t + v; }, 0);
      if (sum > total) widths = widths.map(function (v) { return v * total / sum; });
      var at = 0;
      return row.map(function (fi, j) {
        var b = { fam: fi, row: ri, vx0: at, vx1: at + widths[j] };
        at += widths[j] + gap;
        return b;
      });
    }
    var rowPlates, plates;
    function buildPlates() {
      rowPlates = [allocate(rows[0], 0), allocate(rows[1], 1)];
      plates = [];
      rowPlates.forEach(function (row, ri) {
        row.forEach(function (b) {
          var e = engr[b.fam], f = model.families[b.fam];
          var roomE = (b.vx1 - b.vx0) - 2 * padX;
          // Across a portrait plate the name takes its narrowest setting in
          // two lines, and the plate is made deep enough to hold it.
          if (portrait) b.lines = wrapName(f.title, Math.max(20, e.minW - e.cw - e.gapC + 0.5), fontEng);
          else b.lines = measure(f.title, fontEng) + e.gapC + e.cw <= roomE ? [f.title] :
            wrapName(f.title, Math.max(20, roomE - e.cw - e.gapC), fontEng);
          b.band = b.lines.length * lineEng + padY * 0.9;
          b.side = ri === 0 ? 1 : -1;   // the spine lies below a top plate, above a bottom one
          b.index = plates.length;
          plates.push(b);
        });
      });
    }
    buildPlates();

    // The lattice a plate holds at pitch p: columns across its width, rows
    // filled from the spine outward.
    function latticeOf(b, p) {
      var n = model.families[b.fam].members.length;
      var inner = (b.vx1 - b.vx0) - 2 * gm - (portrait ? b.band : 0);
      var colsMax = Math.max(1, Math.floor(inner / p));
      var rowsN = Math.ceil(n / Math.min(colsMax, n));
      return { cols: Math.ceil(n / rowsN), rows: rowsN };
    }
    function plateDepth(b, lat, p) {
      var d = gm + p / 2 + (lat.rows - 1) * p + mr + padY + (portrait ? padY : b.band);
      return portrait ? Math.max(d, engr[b.fam].minW + 2 * padX + 2) : d;
    }
    function columns(b, lat, p) {
      var cx = (b.vx0 + b.vx1) / 2 + (portrait ? b.band / 2 : 0), xs = [];
      var first = half(cx - (lat.cols - 1) * p / 2);
      for (var c = 0; c < lat.cols; c++) xs.push(first + c * p);
      return xs;
    }

    /* Ports and lanes. A trace leaves its plate down the gutter beside its
       component and reaches the other plate up the gutter beside the target.
       Between plates it runs in a lane beside the spine: one lane per pair
       of plates, packed so lanes sharing a corridor never overlap. Lanes
       between plates of one row sit next to the plates; lanes that cross the
       spine sit next to it, so few traces cross. */
    function planRoutes(p) {
      var slots = [];
      plates.forEach(function (b) {
        var lat = latticeOf(b, p), xs = columns(b, lat, p);
        b.lat = lat; b.xs = xs;
        model.families[b.fam].members.forEach(function (ci, at) {
          slots[ci] = { plate: b.index, row: Math.floor(at / lat.cols), col: at % lat.cols, vx: xs[at % lat.cols] };
        });
      });
      var bundles = Object.create(null), list = [], crossLinks = [];
      model.links.forEach(function (l, li) {
        var A = slots[l[0]], B = slots[l[1]];
        if (A.plate === B.plate) return;
        var PA = plates[A.plate], PB = plates[B.plate];
        var xo = B.vx >= A.vx ? A.vx + p / 2 : A.vx - p / 2;
        var xi = xo <= B.vx ? B.vx - p / 2 : B.vx + p / 2;
        if (PA.row !== PB.row && crossesName(xi)) {
          var cands = [B.vx - p / 2, B.vx + p / 2, B.vx - 1.5 * p, B.vx + 1.5 * p, B.vx - 2.5 * p, B.vx + 2.5 * p];
          for (var k = 0; k < cands.length; k++) {
            var cx = cands[k];
            if (cx > PB.vx0 + gm - 0.1 && cx < PB.vx1 - gm + 0.1 && !crossesName(cx)) { xi = cx; break; }
          }
        }
        var same = PA.row === PB.row;
        var key = same ? 's' + Math.min(A.plate, B.plate) + '-' + Math.max(A.plate, B.plate) : 'c' + A.plate + '>' + B.plate;
        var bd = bundles[key];
        if (!bd) { bd = bundles[key] = { key: key, corridor: PA.row, same: same, lo: Infinity, hi: -Infinity, lane: 0 }; list.push(bd); }
        bd.lo = Math.min(bd.lo, xo, xi);
        bd.hi = Math.max(bd.hi, xo, xi);
        crossLinks.push({ li: li, xo: xo, xi: xi, bundle: bd });
      });
      var counts = [0, 1].map(function (ri) {
        return {
          same: packLanes(list.filter(function (bd) { return bd.corridor === ri && bd.same; }), 4),
          cross: packLanes(list.filter(function (bd) { return bd.corridor === ri && !bd.same; }), 4)
        };
      });
      return { slots: slots, crossLinks: crossLinks, counts: counts };
    }
    function corridorH(plan, ri) {
      var c = plan.counts[ri], ns = c.same, nc = c.cross;
      if (!ns && !nc) return laneMargin * 2;
      return 2 * laneMargin + Math.max(0, ns - 1) * laneGap + Math.max(0, nc - 1) * laneGap + (ns && nc ? laneGap * 2.5 : 0);
    }
    function totalNeed(p) {
      var plan = planRoutes(p);
      var dTop = rowPlates[0].reduce(function (t, b) { return Math.max(t, plateDepth(b, b.lat, p)); }, 0);
      var dBot = rowPlates[1].reduce(function (t, b) { return Math.max(t, plateDepth(b, b.lat, p)); }, 0);
      return { plan: plan, dTop: dTop, dBot: dBot,
               need: dTop + corridorH(plan, 0) + 2 * halfBand + corridorH(plan, 1) + dBot };
    }
    var p, fit;
    function searchPitch() {
      p = clamp(34 * s, 18, 48);
      var pMin = 2 * mr + 6;
      fit = totalNeed(p);
      while (p > pMin && fit.need > VH) { p -= 0.5; fit = totalNeed(p); }
      while (mr > 2.4 && fit.need > VH) { mr -= 0.25; p = Math.max(2 * mr + 5, p - 0.25); fit = totalNeed(p); }
      // An even number of device pixels, so half a pitch is whole too.
      p = Math.max(2 / dpr, Math.floor(p * dpr / 2) * 2 / dpr);
      fit = totalNeed(p);
    }
    searchPitch();
    // A small family whose plate would take more rows than its row's largest
    // family is widened to fit in as many, so no plate deepens a row alone.
    var widened = false;
    rowPlates.forEach(function (row) {
      if (!row.length) return;
      var big = row.reduce(function (a, b) {
        return model.families[b.fam].members.length > model.families[a.fam].members.length ? b : a;
      }, row[0]);
      row.forEach(function (b) {
        if (b.lat.rows <= big.lat.rows) return;
        var n = model.families[b.fam].members.length;
        var need = Math.ceil(n / big.lat.rows) * p + 2 * gm + (portrait ? b.band : 0) + 1;
        if (need > b.vx1 - b.vx0) { extraMin[b.fam] = need; widened = true; }
      });
    });
    if (widened) { buildPlates(); searchPitch(); }
    // On a box too small for everything, the legend gives way first (the
    // marks are explained again in the card); nothing is drawn over it.
    if (fit.need > VH + 0.5 && legRows.length) return layoutSchematic(model, w, h, measure, dpr, { noLegend: true });
    geo.cramped = fit.need > VH + 0.5;
    var plan = fit.plan;

    // Spare height opens the corridors a little (the exploded spacing), then
    // centres the whole drawing.
    var slack = Math.max(0, VH - fit.need);
    var open = Math.min(slack, 2 * clamp(12 * s, 7, 18));
    var cTop = corridorH(plan, 0) + open / 2, cBot = corridorH(plan, 1) + open / 2;
    var top0 = (slack - open) / 2;
    halfBand = whole(halfBand);
    var inTop = half(top0 + fit.dTop);
    var cy = half(inTop + cTop + halfBand);
    var inBot = half(cy + halfBand + cBot);
    var spineTop = cy - halfBand, spineBot = cy + halfBand;

    // Every plate in a row takes the row's depth, so their outer edges and
    // the baselines of their names line up.
    plates.forEach(function (b) {
      var depth = whole(b.side > 0 ? fit.dTop : fit.dBot);
      if (b.side > 0) { b.vyIn = inTop; b.vyOut = inTop - depth; } else { b.vyIn = inBot; b.vyOut = inBot + depth; }
    });
    var slots = plan.slots;
    slots.forEach(function (sl) {
      var b = plates[sl.plate];
      sl.vy = b.vyIn - b.side * (gm + p / 2 + sl.row * p);
      sl.gutter = sl.vy + b.side * p / 2;
    });
    function laneY(bd) {
      var k = bd.lane;
      if (bd.corridor === 0) return bd.same ? inTop + laneMargin + k * laneGap : spineTop - laneMargin - k * laneGap;
      return bd.same ? inBot - laneMargin - k * laneGap : spineBot + laneMargin + k * laneGap;
    }

    /* Routes: every declared link, start to end, in the declared direction. */
    var crossOf = Object.create(null);
    plan.crossLinks.forEach(function (cl) { crossOf[cl.li] = cl; });
    var routes = model.links.map(function (l, li) {
      var A = slots[l[0]], B = slots[l[1]], PA = plates[A.plate], PB = plates[B.plate];
      var S = [A.vx, A.vy + PA.side * (mr + capGap)], E = [B.vx, B.vy + PB.side * (mr + capGap)];
      var pts = [S, [A.vx, A.gutter]];
      if (A.plate === B.plate) {
        if (A.row !== B.row) {
          var xv = B.vx > A.vx ? B.vx - p / 2 : B.vx < A.vx ? B.vx + p / 2 : A.vx + p / 2;
          pts.push([xv, A.gutter], [xv, B.gutter]);
        }
        pts.push([B.vx, B.gutter]);
      } else {
        var cl = crossOf[li], ly = laneY(cl.bundle);
        pts.push([cl.xo, A.gutter], [cl.xo, ly], [cl.xi, ly], [cl.xi, B.gutter], [B.vx, B.gutter]);
      }
      pts.push(E);
      var path = roundedPath(simplify(pts).map(function (q) { return T(q[0], q[1]); }), rb);
      path.a = l[0]; path.b = l[1];
      return path;
    });

    /* Geometry in canvas space. */
    var marks = model.comps.map(function (c, i) {
      var q = T(slots[i].vx, slots[i].vy);
      return { x: q[0], y: q[1], plate: slots[i].plate };
    });
    var plateGeo = plates.map(function (b) {
      var x0 = half(b.vx0), x1 = half(b.vx1), y0 = Math.min(b.vyIn, b.vyOut), y1 = Math.max(b.vyIn, b.vyOut);
      var c0 = T(x0, y0), c1 = T(x1, y1);
      var rect = { x0: Math.min(c0[0], c1[0]), y0: Math.min(c0[1], c1[1]), x1: Math.max(c0[0], c1[0]), y1: Math.max(c0[1], c1[1]) };
      // The assembly line: from the plate's spine-side edge to the rail, at
      // the column nearest the plate's middle whose line clears every name.
      var mid = (x0 + x1) / 2, bind = null;
      var order = b.xs.slice().sort(function (u, v) { return Math.abs(u - mid) - Math.abs(v - mid) || u - v; });
      for (var k = 0; k < order.length; k++) { if (!crossesName(order[k])) { bind = order[k]; break; } }
      if (bind === null) bind = order[0];
      var from = T(bind, b.vyIn), to = T(bind, b.side > 0 ? cy - railH / 2 : cy + railH / 2);
      return { fam: b.fam, row: b.row, side: b.side, order: b.index, rect: rect, lines: b.lines,
               bind: { from: from, to: to } };
    });
    var railA = T(half(padX * 0.5), cy - railH / 2), railB = T(half(VW - padX * 0.5), cy + railH / 2);
    var rail = { x0: Math.min(railA[0], railB[0]), y0: Math.min(railA[1], railB[1]),
                 x1: Math.max(railA[0], railB[0]), y1: Math.max(railA[1], railB[1]) };
    var stationGeo = stations.map(function (st, i) {
      var q = T(st.vx, cy);
      return { x: q[0], y: q[1], side: stepLabels[i].side };
    });

    /* Words: family names along each plate's outer edge (portrait: its top)
       with the count at the far end; step names beside their tick rules; the
       legend along the foot. */
    var labels = [];
    plateGeo.forEach(function (g, gi) {
      var b = plates[gi], e = engr[b.fam];
      var x0 = g.rect.x0 + padX, x1 = g.rect.x1 - padX, baseY, lines = g.lines;
      if (portrait || b.side > 0) baseY = g.rect.y0 + padY * 0.9 + fEng * asc;
      else baseY = g.rect.y1 - padY * 0.9 - fEng * desc - (lines.length - 1) * lineEng;
      var countLine = portrait || b.side > 0 ? 0 : lines.length - 1, yc = baseY + countLine * lineEng;
      lines.forEach(function (text, li) {
        // Each line fits the room it has (beside the count on its line);
        // where a plate is too narrow the name is shortened, never overlapped.
        var room = x1 - x0 - (li === countLine ? e.cw + e.gapC : 0);
        text = fitWith(text, Math.max(12, room), fontEng, measure);
        var y = baseY + li * lineEng, tw = measure(text, fontEng);
        if (tw > room || text.length < 5) return;
        labels.push({ kind: 'family', fam: b.fam, text: text, font: fontEng, x: x0, y: y, align: 'left',
                      box: { x0: x0 - 2, x1: x0 + tw + 2, y0: y - fEng * asc - 1, y1: y + fEng * desc + 1 } });
      });
      labels.push({ kind: 'count', fam: b.fam, text: e.countText, font: fontCount, x: x1, y: yc, align: 'right',
                    box: { x0: x1 - e.cw - 2, x1: x1 + 2, y0: yc - fEng * asc - 1, y1: yc + fEng * desc + 1 } });
    });
    if (stepNames) {
      stationGeo.forEach(function (st, i) {
        var l = stepLabels[i], x, y, align, off = railH / 2 + tickL + gapL;
        if (!portrait) {
          x = st.x; align = 'center';
          y = l.side < 0 ? st.y - off - fStep * desc : st.y + off + fStep * asc;
        } else {
          y = st.y + fStep * 0.32;
          if (l.side < 0) { x = st.x - off; align = 'right'; } else { x = st.x + off; align = 'left'; }
        }
        var bx0 = align === 'center' ? x - l.tw / 2 : align === 'right' ? x - l.tw : x;
        labels.push({ kind: 'step', step: i, text: l.text, font: fontStep, x: x, y: y, align: align,
                      box: { x0: bx0 - 1, x1: bx0 + l.tw + 1, y0: y - fStep * asc - 1, y1: y + fStep * desc + 1 } });
      });
    }
    var legend = [];
    if (legRows.length) {
      var gapIn = clamp(5 * s, 4, 7), gapC2 = clamp(4 * s, 3, 6);
      legRows.forEach(function (row, ri) {
        var x = w / 2 - rowWidth(row) / 2;
        var y = h - m * 0.7 - (legRows.length - 1 - ri) * lineLeg - fLeg * desc;
        row.forEach(function (it) {
          var lx = x + it.glyph + gapIn, cxText = lx + it.lw + gapC2;
          legend.push({ cls: it.cls, x: x, y: y - fLeg * 0.32, w: it.glyph });
          labels.push({ kind: 'legend', text: it.label, font: fontLeg, x: lx, y: y, align: 'left',
                        box: { x0: x - 1, x1: lx + it.lw + 1, y0: y - fLeg * asc - 1, y1: y + fLeg * desc + 1 } });
          labels.push({ kind: 'legend-count', text: String(it.count), font: fontLeg, x: cxText, y: y, align: 'left',
                        box: { x0: cxText - 1, x1: cxText + it.cw + 1, y0: y - fLeg * asc - 1, y1: y + fLeg * desc + 1 } });
          x += it.w + legGap;
        });
      });
    }

    geo.ok = true;
    geo.dpr = dpr;
    geo.half = half;
    geo.portrait = portrait;
    geo.scale = s;
    geo.m = m;
    geo.padX = padX;
    geo.padY = padY;
    geo.marks = marks;
    geo.mr = mr;
    geo.pitch = p;
    geo.rb = rb;
    geo.laneGap = laneGap;
    geo.capGap = capGap;
    geo.cham = cham;
    geo.plates = plateGeo;
    geo.routes = routes;
    geo.rail = rail;
    geo.stations = stationGeo;
    geo.stepNames = stepNames;
    geo.tickL = tickL;
    geo.railH = railH;
    geo.labelReach = railH / 2 + tickL + gapL;
    geo.labels = labels;
    geo.legend = legend;
    geo.fieldH = Y1 + m * 0.5;
    geo.explode = clamp(12 * s, 7, 16);
    geo.lanes = [plan.counts[0].same + plan.counts[0].cross, plan.counts[1].same + plan.counts[1].cross];
    geo.depthStep = clamp(2.6 * s, 2, 3.4);
    geo.fontEng = fontEng;
    geo.fontCount = fontCount;
    geo.fEng = fEng;
    geo.lineEng = lineEng;
    geo.panels = {};
    geo.fonts = { plate: '500 ' + clamp(12 * rs, 10.5, 14).toFixed(2) + 'px ' + SERIF,
                  plateSub: 'italic 400 ' + clamp(10.5 * rs, 9, 12).toFixed(2) + 'px ' + SERIF,
                  plateSize: clamp(12 * rs, 10.5, 14), plateSubSize: clamp(10.5 * rs, 9, 12),
                  name: '400 ' + clamp(10.8 * rs, 9.5, 12.5).toFixed(2) + 'px ' + SERIF,
                  nameSize: clamp(10.8 * rs, 9.5, 12.5) };
    return geo;
  }

  /* A family's sheet: its plate opened forward. Every component is a row,
     its mark and its name in reading order; the family's links inside it
     are brackets to the left of the marks, nested by span with the shortest
     nearest, each turned with the same bend radius as the traces. Wide
     canvases keep a column on the right for the card. */
  function layoutSheet(model, geo, f, measure) {
    var fam = model.families[f], n = fam.members.length, s = geo.scale;
    var wide = geo.w >= 520;
    var x0 = geo.m, x1 = geo.w - geo.m;
    var head = geo.lineEng + geo.padY * 1.8;
    var avail = geo.fieldH - 2 * geo.m - head - geo.padY;
    var rowH = clamp(avail / Math.max(1, n), 11, 30);
    var inside = [];
    model.links.forEach(function (l) {
      if (model.comps[l[0]].fam !== f || model.comps[l[1]].fam !== f) return;
      var ra = model.comps[l[0]].slot, rb2 = model.comps[l[1]].slot;
      inside.push({ a: l[0], b: l[1], ra: ra, rb: rb2, lo: Math.min(ra, rb2), hi: Math.max(ra, rb2),
                    key: l[0] + '>' + l[1], lane: 0 });
    });
    var nLanes = packLanes(inside, 0.2);
    var laneGap = Math.max(1 / geo.dpr, Math.round(clamp(2.3 * s, 1.8, 3) * geo.dpr) / geo.dpr);
    var markX = geo.half(x0 + geo.padX + nLanes * laneGap + geo.mr + clamp(8 * s, 6, 10));
    var nameX = markX + geo.mr + clamp(8 * s, 6, 10);
    // Names never stand taller than their rows.
    var nameSize = Math.min(geo.fonts.nameSize, rowH * 0.78);
    var nameFont = '400 ' + nameSize.toFixed(2) + 'px ' + SERIF;
    if (wide) {
      // As wide as the longest name needs, between 42% and 60% of the canvas;
      // the rest is the card's.
      var longest = fam.members.reduce(function (t, ci) { return Math.max(t, measure(model.comps[ci].label, nameFont)); }, 0);
      longest = Math.max(longest, measure(fam.title, geo.fontEng) + 40);
      x1 = geo.half(clamp(nameX + longest + geo.padX + 2, geo.w * 0.42, geo.w * 0.6));
    }
    var y0 = geo.m, top = y0 + head;
    var rows = fam.members.map(function (ci, i) {
      var y = geo.half(top + (i + 0.5) * rowH);
      var maxW = x1 - geo.padX - nameX;
      var text = fitWith(model.comps[ci].label, maxW, nameFont, measure);
      return { comp: ci, y: y, x: markX, nameX: nameX, text: text, full: text === model.comps[ci].label,
               box: { x0: x0, x1: x1, y0: y - rowH / 2, y1: y + rowH / 2 } };
    });
    var stub = geo.mr + geo.capGap;
    var brackets = inside.map(function (it) {
      var lx = markX - stub - clamp(5 * s, 4, 7) - it.lane * laneGap;
      var ya = rows[it.ra].y, yb = rows[it.rb].y;
      var path = roundedPath([[markX - stub, ya], [lx, ya], [lx, yb], [markX - stub, yb]], geo.rb);
      path.a = it.a; path.b = it.b;
      return path;
    });
    var e = { countText: String(n), cw: measure(String(n), geo.fontCount) };
    var y1 = top + n * rowH + geo.padY;
    // The header is the trail: "All families /" (a way back to the whole
    // drawing) and the family's name.
    var crumbText = 'All families', sepText = ' / ';
    var cw0 = measure(crumbText, geo.fontCount), sw0 = measure(sepText, geo.fontCount);
    var ty = y0 + geo.padY * 1.1 + geo.fEng * 0.74;
    var crumb = { text: crumbText, sep: sepText, x: x0 + geo.padX, w: cw0 + sw0, textW: cw0,
                  box: { x0: x0 + geo.padX - 4, x1: x0 + geo.padX + cw0 + 4, y0: ty - geo.fEng - 5, y1: ty + geo.fEng * 0.5 + 5 } };
    return {
      fam: f, rect: { x0: x0, y0: y0, x1: x1, y1: y1 }, rows: rows, brackets: brackets, rowH: rowH,
      nameFont: nameFont, nameSize: nameSize,
      crumb: crumb,
      title: fitWith(fam.title, x1 - x0 - 2 * geo.padX - e.cw - 12 - crumb.w, geo.fontEng, measure),
      titleY: y0 + geo.padY * 1.1 + geo.fEng * 0.74, count: e.countText,
      card: wide ? { x0: x1 + clamp(12 * s, 8, 16), x1: geo.w - geo.m * 0.6 } : null
    };
  }
  function fitWith(text, maxW, font, measure) {
    if (measure(text, font) <= maxW) return text;
    var cut = text;
    while (cut.length > 4 && measure(cut + '…', font) > maxW) cut = cut.slice(0, -1);
    return cut.replace(/\s+$/, '') + '…';
  }

  /* ---- Geometry helpers ---------------------------------------------- */
  function pointInRect(x, y, r) { return x >= r.x0 && x <= r.x1 && y >= r.y0 && y <= r.y1; }
  function boxesMeet(a, b, grace) {
    grace = grace || 0;
    return a.x0 < b.x1 - grace && a.x1 > b.x0 + grace && a.y0 < b.y1 - grace && a.y1 > b.y0 + grace;
  }

  /* ---- Mount --------------------------------------------------------- */
  function mount(stage) {
    var canvas = stage.querySelector('canvas.system-canvas') || stage.querySelector('canvas');
    if (!canvas || !canvas.getContext || stage.getAttribute('data-system-ready')) return null;
    stage.setAttribute('data-system-ready', '1');
    var ctx = canvas.getContext('2d');
    if (!ctx) return null;
    var section = stage.closest ? stage.closest('section') : null;
    var caption = stage.querySelector('.system-caption');
    var base = canvas.getAttribute('data-system-base') || '';
    var src = canvas.getAttribute('data-system-src');

    var model = null, geo = null, palette = {};
    var cssW = 0, cssH = 0, layoutDpr = 1;

    /* ---- State ------------------------------------------------------- */
    var hover = null;        // what the pointer is on: {kind: 'comp'|'family'|'step', i}
    var pin = null;          // the selection: {fam, comp} (comp -1 at the family level)
    var preview = -1;        // a family opened from the landing's list
    var rowHover = -1;       // the family row under the pointer, before its preview opens
    var keyComp = -1;        // a component reached with the arrow keys from a family row
    var listHover = -1;      // a component pointed at in the card's lists
    var rows = [], rowTimer = null, dwellTimer = null;

    /* ---- Palette ----------------------------------------------------- */
    /* Every colour is a custom property (--s-*) read here and again on each
       theme change. Until the stylesheet defines them, the map derives the
       same values from the site's --ink, --surface and ember. */
    function readPalette() {
      var st = window.getComputedStyle ? window.getComputedStyle(document.documentElement) : null;
      function tok(name, fallback) {
        var v = st && st.getPropertyValue ? st.getPropertyValue(name) : '';
        v = v && String(v).trim();
        return v || fallback;
      }
      var ground = tok('--s-ground', tok('--surface', '#fffdf7'));
      var dark = luminance(parseColor(ground)) < 0.35;
      var ink = tok('--s-ink', tok('--ink', dark ? '#f2e6d4' : '#211318'));
      var inkRgb = parseColor(ink) || (dark ? [242, 230, 212, 1] : [33, 19, 24, 1]);
      function inkA(name, light, night) { return tok(name, rgba(inkRgb, dark ? night : light)); }
      palette = {
        ink: ink, ground: ground, dark: dark,
        ember: tok('--s-ember', tok('--u-integration', dark ? '#e08a58' : '#b0512a')),
        face: inkA('--s-face', 0.03, 0.045),
        side: inkA('--s-side', 0.075, 0.1),
        edge: inkA('--s-edge', 0.36, 0.36),
        rail: inkA('--s-rail', 0.15, 0.17),
        railEdge: inkA('--s-rail-edge', 0.62, 0.6),
        bind: inkA('--s-bind', 0.3, 0.32),
        trace: inkA('--s-trace', 0.095, 0.11),
        traceHot: inkA('--s-trace-hot', 0.86, 0.9),
        text: inkA('--s-text', 0.74, 0.76),
        faint: inkA('--s-faint', 0.52, 0.54),
        grey: inkA('--s-grey', 0.22, 0.26)
      };
    }

    function measureWith(font) {
      return function (text, f) {
        ctx.font = f || font;
        var mt = ctx.measureText(String(text));
        return mt && isFinite(mt.width) ? mt.width : String(text).length * 6;
      };
    }
    var measure = measureWith('11px ' + SERIF);
    function relayout() {
      cssW = canvas.clientWidth || 0;
      cssH = canvas.clientHeight || 0;
      layoutDpr = Math.min(window.devicePixelRatio || 1, 2);
      geo = model ? layoutSchematic(model, cssW, cssH, measure, layoutDpr) : null;
    }
    function sheetOf(f) {
      if (!geo || !geo.ok || f < 0) return null;
      if (!geo.panels[f]) geo.panels[f] = layoutSheet(model, geo, f, measure);
      return geo.panels[f];
    }

    /* ---- Motion ------------------------------------------------------ */
    /* One display frame serves every moving part; it is requested only while
       one of them is moving and never at rest. */
    var reduceQuery = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    var reduceMotion = !!(reduceQuery && reduceQuery.matches);
    var fineQuery = window.matchMedia ? window.matchMedia('(hover: hover) and (pointer: fine)') : null;
    var frame = 0;
    var motion = { open: null, focus: null, reticle: null, trace: null, sheet: null, swap: null };
    function canAnimate() {
      return !reduceMotion && !!window.requestAnimationFrame && !document.hidden && onScreen;
    }
    function moving() {
      return !!(motion.open || motion.focus || motion.reticle || motion.trace || motion.sheet || motion.swap);
    }
    function wake() {
      if (!frame && moving() && window.requestAnimationFrame) frame = window.requestAnimationFrame(tick);
    }
    function tick(now) {
      frame = 0;
      if (!canAnimate()) { settleAll(); paint(); return; }
      advance(now);
      paint();
      // paint() may itself have woken a frame (a new focus fade); never two.
      if (moving() && !frame) frame = window.requestAnimationFrame(tick);
    }
    function settleAll() {
      if (motion.open) { motion.open = null; openState = 'done'; }
      if (motion.focus) { focusMix = motion.focus.to; if (motion.focus.to === 0) focusHeld = null; motion.focus = null; }
      if (motion.sheet) { sheetMix = motion.sheet.to; motion.sheet = null; if (sheetMix === 0) sheetFam = -1; }
      if (motion.swap) { motion.swap = null; swapFrom = -1; }
      motion.reticle = null;
      motion.trace = null;
    }
    function advance(now) {
      var mo;
      if ((mo = motion.open)) {
        if (mo.start === null) mo.start = now;
        openMs = now - mo.start;
        if (openMs >= OPEN_END) { motion.open = null; openState = 'done'; openMs = OPEN_END; }
      }
      if ((mo = motion.focus)) {
        if (mo.start === null) mo.start = now;
        var tf = unit((now - mo.start - mo.delay) / mo.dur);
        focusMix = mo.from + (mo.to - mo.from) * (1 - (1 - tf) * (1 - tf));
        if (tf >= 1) { motion.focus = null; if (mo.to === 0) focusHeld = null; }
      }
      if ((mo = motion.reticle)) {
        if (mo.start === null) mo.start = now;
        mo.ms = now - mo.start;
        if (mo.ms >= RETICLE_MS) motion.reticle = null;
      }
      if ((mo = motion.trace)) {
        if (mo.start === null) mo.start = now;
        mo.ms = now - mo.start;
        if (mo.ms >= TRACE_MS) motion.trace = null;
      }
      if ((mo = motion.sheet)) {
        if (mo.start === null) mo.start = now;
        var ts = unit((now - mo.start) / mo.dur);
        sheetMix = mo.from + (mo.to - mo.from) * ts;
        if (ts >= 1) { motion.sheet = null; if (mo.to === 0) sheetFam = -1; }
      }
      if ((mo = motion.swap)) {
        if (mo.start === null) mo.start = now;
        swapMix = unit((now - mo.start) / SWAP_MS);
        if (swapMix >= 1) { motion.swap = null; swapFrom = -1; }
      }
    }

    /* The opening, in milliseconds from its first frame: the spine draws
       out, the plates settle onto it, the components set, the assembly lines
       join plates to spine, and the links route in last. */
    var OPEN_SPINE = [0, 380];
    var OPEN_PLATE = [200, 45, 420];        // start, per plate in reading order, duration
    var OPEN_MARK = [300, 45, 6, 220];      // start, per plate, per component, duration
    var OPEN_BIND = [520, 35, 240];
    var OPEN_WORDS = [520, 320];
    var OPEN_LINKS = [660, 220, 340];       // start, spread across the links, duration
    var OPEN_END = OPEN_LINKS[0] + OPEN_LINKS[1] + OPEN_LINKS[2];
    var openState = 'idle', openMs = 0, opened = false;
    function phase(start, dur) {
      if (openState !== 'running') return 1;
      return unit((openMs - start) / dur);
    }
    function startOpening() {
      if (opened || !geo || !geo.ok) return;
      opened = true;
      if (!canAnimate()) { openState = 'done'; paint(); return; }
      openState = 'running';
      openMs = 0;
      motion.open = { start: null };
      wake();
    }

    /* A sheet opens over 380ms (the plate travels forward, every mark to its
       row) and closes over 300ms; one family's sheet gives way to another's
       by a 180ms cross-fade. A keyboard step, reduced motion or a hidden
       tab change at once. */
    var SHEET_OPEN = 380, SHEET_CLOSE = 300, SWAP_MS = 180;
    var sheetFam = -1, sheetMix = 0, swapFrom = -1, swapMix = 1;
    function shownFamily() {
      if (preview >= 0) return preview;
      return pin ? pin.fam : -1;
    }
    function syncSheet(instant) {
      var want = shownFamily(), quick = instant || !canAnimate();
      if (want >= 0) {
        if (sheetFam < 0 || sheetMix <= 0) {
          sheetFam = want;
          if (quick) { sheetMix = 1; motion.sheet = null; }
          else { motion.sheet = { start: null, from: sheetMix, to: 1, dur: SHEET_OPEN * (1 - sheetMix) + 1 }; }
        } else if (want !== sheetFam) {
          if (quick || sheetMix < 0.5) { sheetFam = want; swapFrom = -1; motion.swap = null; }
          else { swapFrom = sheetFam; sheetFam = want; swapMix = 0; motion.swap = { start: null }; }
          if (sheetMix < 1) {
            if (quick) { sheetMix = 1; motion.sheet = null; }
            else motion.sheet = { start: null, from: sheetMix, to: 1, dur: SHEET_OPEN * (1 - sheetMix) + 1 };
          }
        } else if (sheetMix < 1 && (!motion.sheet || motion.sheet.to !== 1)) {
          if (quick) { sheetMix = 1; motion.sheet = null; }
          else motion.sheet = { start: null, from: sheetMix, to: 1, dur: SHEET_OPEN * (1 - sheetMix) + 1 };
        }
      } else if (sheetFam >= 0 && (!motion.sheet || motion.sheet.to !== 0)) {
        if (quick) { sheetMix = 0; sheetFam = -1; motion.sheet = null; }
        else motion.sheet = { start: null, from: sheetMix, to: 0, dur: SHEET_CLOSE * sheetMix + 1 };
      }
      wake();
    }

    /* Focus fades in over a sixth of a second and lets go after a short
       hold, as on the universe map, so a pointer sweeping across the marks
       never strobes the drawing. A component's links trace out once per new
       focus, all together, in their declared direction. */
    var FOCUS_IN = 180, FOCUS_HOLD = 140, FOCUS_OUT = 220, RETICLE_MS = 140, TRACE_MS = 380;
    var focusMix = 0, focusWas = null, focusHeld = null;
    function sameFocus(a, b) { return a === b || (!!a && !!b && a.kind === b.kind && a.i === b.i); }
    function fadeFocus(to, dur, delay) {
      if (!canAnimate()) { focusMix = to; motion.focus = null; if (to === 0) focusHeld = null; return; }
      motion.focus = { start: null, from: focusMix, to: to, dur: Math.max(1, dur), delay: delay };
      wake();
    }
    // What is lit: in a sheet, the component pointed at, stepped to or
    // selected; on the overview, whatever the pointer or the list is on.
    function currentFocus() {
      if (sheetFam >= 0 && sheetMix > 0) {
        if (listHover >= 0) return { kind: 'comp', i: listHover };
        if (hover && hover.kind === 'comp') return hover;
        if (keyComp >= 0) return { kind: 'comp', i: keyComp };
        if (pin && pin.comp >= 0 && pin.fam === sheetFam) return { kind: 'comp', i: pin.comp };
        return null;
      }
      if (hover) return hover;
      if (keyComp >= 0) return { kind: 'comp', i: keyComp };
      if (rowHover >= 0) return { kind: 'family', i: rowHover };
      return null;
    }
    function trackFocus() {
      var f = currentFocus();
      if (sameFocus(f, focusWas)) return f || focusHeld;
      if (f && !focusWas) {
        focusHeld = null;
        fadeFocus(1, FOCUS_IN * (1 - focusMix), 0);
      } else if (!f && focusWas) {
        focusHeld = focusWas;
        fadeFocus(0, FOCUS_OUT, FOCUS_HOLD);
      }
      motion.reticle = f && (f.kind === 'comp' || f.kind === 'step') && canAnimate() ? { start: null, ms: 0 } : null;
      motion.trace = f && f.kind === 'comp' && canAnimate() ? { start: null, ms: 0 } : null;
      wake();
      focusWas = f;
      return f || focusHeld;
    }
    function dimmed(base) { return 1 - (1 - base) * focusMix; }

    /* ---- Visibility -------------------------------------------------- */
    /* The opening starts once the drawing is well in view and still. While
       the landing's slider is carrying the system slide in (a start event
       for it without its end), it waits for the end, or 1.2 seconds; a
       slide that arrives at once, or none at all, opens on half visibility. */
    var onScreen = !('IntersectionObserver' in window);
    var dirty = true, sliding = false, slideTimer = null, visibleEnough = onScreen;
    if ('IntersectionObserver' in window) {
      var io = new window.IntersectionObserver(function (entries) {
        for (var i = 0; i < entries.length; i++) {
          var e = entries[i];
          onScreen = !!e.isIntersecting && e.intersectionRatio > 0;
          visibleEnough = onScreen && e.intersectionRatio >= 0.5;
        }
        if (!onScreen) { settleAll(); return; }
        if (dirty) paint();
        maybeOpen();
      }, { threshold: [0, 0.5, 0.75] });
      io.observe(canvas);
    }
    function maybeOpen() {
      if (opened || !geo || !geo.ok || !visibleEnough || sliding) return;
      startOpening();
    }
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) { settleAll(); return; }
      if (dirty) paint();
    });
    document.addEventListener('plectis:atlas', function (event) {
      var d = event && event.detail || {};
      if (d.phase === 'start' && d.previous === 'system' && d.view !== 'system') {
        // Leaving: nothing stays lit while the drawing slides out.
        hover = null; rowHover = -1; keyComp = -1; listHover = -1;
        if (canvas.classList) canvas.classList.remove('is-over');
        settleAll();
        paint();
        return;
      }
      if (d.view !== 'system') return;
      if (d.phase === 'start' && !d.instant) {
        sliding = true;
        if (slideTimer) clearTimeout(slideTimer);
        slideTimer = setTimeout(function () { sliding = false; slideTimer = null; maybeOpen(); }, 1200);
      } else if (d.phase === 'end') {
        sliding = false;
        if (slideTimer) { clearTimeout(slideTimer); slideTimer = null; }
        maybeOpen();
      }
    });

    /* ---- Paint ------------------------------------------------------- */
    var hair = 0.5, placed = [];
    // Line widths in CSS pixels, never finer than one device pixel.
    function lw(px) { return Math.max(px, hair); }
    function paint() {
      if (!onScreen || document.hidden) { dirty = true; return; }
      dirty = false;
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      var w = canvas.clientWidth || 0, h = canvas.clientHeight || 0;
      if (w !== cssW || h !== cssH || dpr !== layoutDpr) relayout();
      var bw = Math.round(w * dpr), bh = Math.round(h * dpr);
      if (canvas.width !== bw || canvas.height !== bh) { canvas.width = bw; canvas.height = bh; }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      hair = 1 / dpr;
      if (!geo || !geo.ok || openState === 'idle' || openState === 'waiting') return;
      var focus = trackFocus();
      var lit = litOf(focus);
      var sheet = sheetFam >= 0 && sheetMix > 0 ? sheetOf(sheetFam) : null;
      var back = sheet ? 1 - 0.95 * MOVE(sheetMix) : 1;     // how present the overview is
      placed = [];
      var plate = placePlate(focus, sheet);
      drawSpine(lit, back);
      drawBindings(lit, back);
      drawPlates(lit, back, sheet);
      drawTraces(lit, back, sheet);
      drawMarks(lit, back, sheet);
      if (!sheet) drawCaps(lit, geo.routes, 1);
      drawWords(lit, back, sheet, plate);
      if (sheet) drawSheet(sheet, lit, swapFrom >= 0 && motion.swap ? sheetOf(swapFrom) : null);
      drawFocus(focus, lit, sheet, plate);
      // Words and rows follow the live focus; only the drawing's dimming
      // holds a moment after the pointer lets go.
      announce(focusWas);
      syncRows(focusWas);
    }
    function draw() { paint(); }

    function polyPath(poly, dx, dy) {
      dx = dx || 0; dy = dy || 0;
      ctx.beginPath();
      for (var i = 0; i < poly.length; i++) {
        if (i) ctx.lineTo(poly[i][0] + dx, poly[i][1] + dy); else ctx.moveTo(poly[i][0] + dx, poly[i][1] + dy);
      }
      ctx.closePath();
    }
    // A plate face with its side: the side shows as an exact offset band
    // along two edges, never a blur.
    function slab(poly, depth, face, side) {
      ctx.beginPath();
      poly.forEach(function (q, i) { if (i) ctx.lineTo(q[0] + depth, q[1] + depth); else ctx.moveTo(q[0] + depth, q[1] + depth); });
      ctx.closePath();
      poly.forEach(function (q, i) { if (i) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); });
      ctx.closePath();
      ctx.fillStyle = side;
      ctx.fill('evenodd');
      polyPath(poly);
      ctx.fillStyle = face;
      ctx.fill();
    }

    // What the focus lights: a component, the components it names and those
    // naming it; a family, its components; a step, its station.
    function litOf(focus) {
      var lit = { focus: focus, comps: null, fam: -1, step: -1 };
      if (!focus || !model) return lit;
      if (focus.kind === 'comp') {
        var c = model.comps[focus.i];
        lit.comps = Object.create(null);
        lit.comps[focus.i] = 'self';
        c.out.forEach(function (j) { lit.comps[j] = lit.comps[j] || 'near'; });
        c.inc.forEach(function (j) { lit.comps[j] = lit.comps[j] || 'near'; });
        lit.fam = c.fam;
      } else if (focus.kind === 'family') {
        lit.fam = focus.i;
        lit.comps = Object.create(null);
        model.families[focus.i].members.forEach(function (j) { lit.comps[j] = 'member'; });
      } else if (focus.kind === 'step') {
        lit.step = focus.i;
      }
      return lit;
    }

    // During the opening a plate stands off from the spine by its exploded
    // distance and settles into place; its components and words go with it.
    function plateOffset(g) {
      if (openState !== 'running') return [0, 0];
      var t = DETENT(phase(OPEN_PLATE[0] + OPEN_PLATE[1] * g.order, OPEN_PLATE[2]));
      var d = -(1 - t) * geo.explode * g.side;
      return geo.portrait ? [d, 0] : [0, d];
    }
    function plateAlpha(g) { return DETENT(phase(OPEN_PLATE[0] + OPEN_PLATE[1] * g.order, OPEN_PLATE[2] * 0.6)); }

    function drawSpine(lit, back) {
      var r = geo.rail, t = DETENT(phase(OPEN_SPINE[0], OPEN_SPINE[1]));
      if (t <= 0) return;
      var horizontal = !geo.portrait;
      var len = horizontal ? r.x1 - r.x0 : r.y1 - r.y0;
      var x1 = horizontal ? r.x0 + len * t : r.x1, y1 = horizontal ? r.y1 : r.y0 + len * t;
      var poly = chamfered(r.x0, r.y0, x1, y1, Math.min(geo.railH * 0.45, 2.4));
      ctx.globalAlpha = back;
      slab(poly, geo.depthStep * 0.6, palette.rail, palette.side);
      ctx.lineWidth = lw(0.75);
      ctx.strokeStyle = palette.railEdge;
      ctx.lineJoin = 'miter';
      polyPath(poly);
      ctx.stroke();
      // Station tick rules: across the rail, and on toward the step's name.
      geo.stations.forEach(function (st, i) {
        var at = horizontal ? (st.x - r.x0) / len : (st.y - r.y0) / len;
        var a = openState === 'running' ? DETENT(unit((openMs - OPEN_SPINE[1] * at) / 160)) : 1;
        if (a <= 0) return;
        var on = lit.step === i;
        var reach = geo.railH / 2 + geo.tickL;
        ctx.globalAlpha = a * back * (lit.comps ? dimmed(0.6) : 1);
        ctx.strokeStyle = on ? palette.traceHot : palette.railEdge;
        ctx.lineWidth = on ? lw(1.1) : lw(0.75);
        ctx.beginPath();
        if (horizontal) {
          ctx.moveTo(st.x, st.y - reach * (st.side < 0 ? 1 : 0.55));
          ctx.lineTo(st.x, st.y + reach * (st.side > 0 ? 1 : 0.55));
        } else {
          ctx.moveTo(st.x - reach * (st.side < 0 ? 1 : 0.55), st.y);
          ctx.lineTo(st.x + reach * (st.side > 0 ? 1 : 0.55), st.y);
        }
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    function drawBindings(lit, back) {
      if (ctx.setLineDash) ctx.setLineDash([2, 2.4]);
      ctx.lineWidth = lw(0.6);
      geo.plates.forEach(function (g) {
        var t = DETENT(phase(OPEN_BIND[0] + OPEN_BIND[1] * g.order, OPEN_BIND[2]));
        if (t <= 0) return;
        var b = g.bind, on = lit.fam === g.fam && lit.focus && lit.focus.kind === 'family';
        ctx.globalAlpha = back * (lit.comps && lit.fam !== g.fam ? dimmed(0.5) : 1);
        ctx.strokeStyle = on ? palette.traceHot : palette.bind;
        ctx.beginPath();
        ctx.moveTo(b.from[0], b.from[1]);
        ctx.lineTo(b.from[0] + (b.to[0] - b.from[0]) * t, b.from[1] + (b.to[1] - b.from[1]) * t);
        ctx.stroke();
      });
      if (ctx.setLineDash) ctx.setLineDash([]);
      ctx.globalAlpha = 1;
    }

    function plateRectNow(g, sheet) {
      var r = g.rect, o = plateOffset(g);
      if (!sheet || sheet.fam !== g.fam) return { x0: r.x0 + o[0], y0: r.y0 + o[1], x1: r.x1 + o[0], y1: r.y1 + o[1] };
      var t = MOVE(sheetMix), R = sheet.rect;
      return { x0: lerp(r.x0, R.x0, t), y0: lerp(r.y0, R.y0, t), x1: lerp(r.x1, R.x1, t), y1: lerp(r.y1, R.y1, t) };
    }
    function drawPlates(lit, back, sheet) {
      ctx.lineJoin = 'miter';
      geo.plates.forEach(function (g) {
        if (sheet && sheet.fam === g.fam) return;   // drawn forward, with the sheet
        var a = plateAlpha(g);
        if (a <= 0) return;
        var R = plateRectNow(g, null), poly = chamfered(R.x0, R.y0, R.x1, R.y1, geo.cham);
        var forward = lit.fam === g.fam && lit.focus && lit.focus.kind === 'family';
        var fade = lit.comps && lit.fam !== g.fam ? dimmed(0.55) : 1;
        ctx.globalAlpha = a * back;
        slab(poly, geo.depthStep * (forward ? 1.6 : 1), palette.face, palette.side);
        ctx.globalAlpha = a * back * fade;
        ctx.lineWidth = forward ? lw(1) : hair;
        ctx.strokeStyle = forward ? palette.traceHot : palette.edge;
        polyPath(poly);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    function drawTraces(lit, back, sheet) {
      var routes = geo.routes, n = routes.length, f = lit.focus;
      if (!n) return;
      ctx.lineCap = 'butt';
      ctx.lineJoin = 'round';
      // At rest every route is one stroke of one path, so traces sharing a
      // gutter or a lane draw once, at one weight. During the opening each
      // routes in from its start.
      var restAlpha = (lit.comps && !sheet ? dimmed(0.3) : 1) * back;
      ctx.beginPath();
      routes.forEach(function (r, i) {
        var t = phase(OPEN_LINKS[0] + OPEN_LINKS[1] * (i / Math.max(1, n - 1)), OPEN_LINKS[2]);
        if (t <= 0) return;
        if (sheet && (model.comps[r.a].fam === sheet.fam || model.comps[r.b].fam === sheet.fam)) return;
        tracePath(ctx, r, r.length * MOVE(t));
      });
      ctx.globalAlpha = restAlpha;
      ctx.lineWidth = hair;
      ctx.strokeStyle = palette.trace;
      ctx.stroke();
      if (sheet || !f || f.kind === 'step' || openState !== 'done') { ctx.globalAlpha = 1; return; }
      drawLit(routes, f, 1);
      ctx.globalAlpha = 1;
    }
    // The routes in focus: a component's links out (heavier) and in, traced
    // out together in their declared direction; a family's links inside it,
    // then those to or from other families.
    function drawLit(routes, f, alpha) {
      var mt = motion.trace, grow = mt ? DETENT(unit(mt.ms / TRACE_MS)) : 1;
      var groups = f.kind === 'comp' ?
        [[function (r) { return r.a === f.i; }, lw(1.15), grow, 1], [function (r) { return r.b === f.i; }, lw(0.85), grow, 1]] :
        [[function (r) { return model.comps[r.a].fam === f.i && model.comps[r.b].fam === f.i; }, lw(0.85), 1, 1],
         [function (r) { return (model.comps[r.a].fam === f.i) !== (model.comps[r.b].fam === f.i); }, lw(0.6), 1, 0.55]];
      groups.forEach(function (gp) {
        ctx.beginPath();
        var any = false;
        routes.forEach(function (r) { if (gp[0](r)) { tracePath(ctx, r, r.length * gp[2]); any = true; } });
        if (!any) return;
        ctx.globalAlpha = Math.max(0.25, focusMix) * gp[3] * alpha;
        ctx.lineWidth = gp[1];
        ctx.strokeStyle = palette.traceHot;
        ctx.stroke();
      });
    }
    // End caps on the routes in focus: a dot where a link leaves the
    // component that names the other, a bar where it reaches the one named.
    function drawCaps(lit, routes, alpha) {
      var f = lit.focus;
      if (!f || f.kind !== 'comp' || openState !== 'done') return;
      var mt = motion.trace, a = mt ? DETENT(unit((mt.ms - TRACE_MS * 0.7) / (TRACE_MS * 0.3))) : 1;
      if (a <= 0) return;
      var bar = clamp(3.4 * geo.scale, 2.6, 4.6);
      ctx.globalAlpha = a * Math.max(0.25, focusMix) * alpha;
      ctx.fillStyle = palette.traceHot;
      ctx.strokeStyle = palette.traceHot;
      ctx.lineWidth = lw(1.1);
      routes.forEach(function (r) {
        if (r.a !== f.i && r.b !== f.i) return;
        var pts = r.points, s0 = pts[0], e0 = pts[pts.length - 1], e1 = pts[pts.length - 2];
        ctx.beginPath();
        ctx.arc(s0[0], s0[1], 1.45, 0, TAU);
        ctx.fill();
        var ux = e0[0] - e1[0], uy = e0[1] - e1[1], ul = Math.hypot(ux, uy) || 1;
        ctx.beginPath();
        ctx.moveTo(e0[0] - uy / ul * bar, e0[1] + ux / ul * bar);
        ctx.lineTo(e0[0] + uy / ul * bar, e0[1] - ux / ul * bar);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    function markShape(x, y, r, cls, color, alpha) {
      if (alpha <= 0.002) return;
      ctx.globalAlpha = alpha;
      ctx.fillStyle = color;
      ctx.strokeStyle = color;
      if (cls === 'tool') {
        ctx.beginPath();
        ctx.arc(x, y, r * 0.72, 0, TAU);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(x, y, r + 0.9, 0, TAU);
        ctx.lineWidth = lw(0.75);
        ctx.stroke();
      } else if (cls === 'bounded') {
        ctx.beginPath();
        ctx.arc(x, y, r, 0, TAU);
        ctx.arc(x, y, r * 0.42, 0, TAU, true);
        ctx.fill('evenodd');
      } else if (cls === 'import') {
        ctx.beginPath();
        ctx.arc(x, y, r, 0, TAU);
        ctx.fill();
      } else if (cls === 'contract') {
        ctx.beginPath();
        ctx.arc(x, y, r * 0.4, 0, TAU);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(x, y, r - 0.55, 0, TAU);
        ctx.lineWidth = 1.1;
        ctx.stroke();
      } else if (cls === 'computes') {
        ctx.beginPath();
        ctx.arc(x, y, r - 0.6, 0, TAU);
        ctx.lineWidth = 1.2;
        ctx.stroke();
      } else {
        ctx.beginPath();
        ctx.arc(x, y, r * 0.5, 0, TAU);
        ctx.fill();
      }
    }
    function colorOf(c) { return EMBER[c.cls] ? palette.ember : palette.ink; }
    // Where a component's mark stands now: on its plate, on its way into the
    // sheet, or in its row of the sheet.
    function markAt(i, sheet) {
      var mk = geo.marks[i], g = geo.plates[mk.plate], o = plateOffset(g);
      if (sheet && sheet.fam === model.comps[i].fam) {
        var row = sheet.rows[model.comps[i].slot], t = MOVE(sheetMix);
        return [lerp(mk.x + o[0], row.x, t), lerp(mk.y + o[1], row.y, t)];
      }
      return [mk.x + o[0], mk.y + o[1]];
    }
    function drawMarks(lit, back, sheet) {
      var mr = geo.mr;
      model.comps.forEach(function (c, i) {
        var mk = geo.marks[i];
        if (!mk) return;
        if (sheet && sheet.fam === c.fam) return;   // drawn with the sheet
        var g = geo.plates[mk.plate];
        var t = phase(OPEN_MARK[0] + OPEN_MARK[1] * g.order + OPEN_MARK[2] * c.slot, OPEN_MARK[3]);
        if (t <= 0) return;
        var e = DETENT(t), r = mr * (0.6 + 0.4 * e), at = markAt(i, null);
        var on = sheet ? false : (!lit.comps || lit.comps[i]);
        var mix = sheet ? MOVE(sheetMix) : focusMix;
        if (on) markShape(at[0], at[1], r, c.cls, colorOf(c), e);
        else {
          // Out of focus a mark greys: its own colour fades as the grey comes
          // up, so ember never turns into a muddy tint of itself.
          markShape(at[0], at[1], r, c.cls, colorOf(c), e * (1 - mix) * (sheet ? back : 1));
          markShape(at[0], at[1], r, c.cls, palette.grey, e * mix * (sheet ? 0.16 : 1));
        }
      });
      ctx.globalAlpha = 1;
    }

    /* ---- Words and the label manager ---------------------------------- */
    // Boxes are placed in priority order; a word whose box would meet one
    // already placed gives way rather than collide.
    function claim(box) {
      for (var i = 0; i < placed.length; i++) if (boxesMeet(box, placed[i], 0.5)) return false;
      placed.push(box);
      return true;
    }
    function drawWords(lit, back, sheet, plate) {
      var a = DETENT(phase(OPEN_WORDS[0], OPEN_WORDS[1]));
      if (a <= 0) return;
      ctx.textBaseline = 'alphabetic';
      if (plate) claim(plate.box);
      var cover = sheet ? [sheetRectNow(sheet)] : [];
      if (sheet && sheet.card && sheetMix > 0.5) cover.push({ x0: sheet.card.x0, x1: geo.w, y0: 0, y1: geo.h });
      // The legend first (it is always there), then step names, then the
      // plates' names and counts.
      var order = geo.labels.filter(function (l) { return l.kind === 'legend' || l.kind === 'legend-count'; })
        .concat(geo.labels.filter(function (l) { return l.kind === 'step'; }))
        .concat(geo.labels.filter(function (l) { return l.kind === 'family' || l.kind === 'count'; }));
      order.forEach(function (l) {
        var alpha = a, color = palette.text, o = [0, 0];
        var legendWord = l.kind === 'legend' || l.kind === 'legend-count';
        if (l.kind === 'family' || l.kind === 'count') {
          var g = plateOf(l.fam);
          if (g) o = plateOffset(g);
          if (sheet && sheet.fam === l.fam) return;   // the sheet carries its own title
          if (lit.comps && lit.fam !== l.fam) alpha *= dimmed(0.45);
          if (lit.fam === l.fam) color = palette.ink;
        } else if (l.kind === 'step') {
          if (lit.step === l.step) color = palette.ink;
          else if (lit.comps && !sheet) alpha *= dimmed(0.6);
        } else if (l.kind === 'legend-count') {
          color = palette.faint;
        }
        var box = { x0: l.box.x0 + o[0], x1: l.box.x1 + o[0], y0: l.box.y0 + o[1], y1: l.box.y1 + o[1] };
        if (!legendWord) {
          alpha *= back;
          for (var c = 0; c < cover.length; c++) if (boxesMeet(box, cover[c], 0)) return;
        }
        if (!claim(box)) return;
        ctx.font = l.font;
        ctx.textAlign = l.align;
        ctx.fillStyle = color;
        ctx.globalAlpha = alpha;
        ctx.fillText(l.text, l.x + o[0], l.y + o[1]);
      });
      geo.legend.forEach(function (g) {
        if (g.cls === 'link') {
          // A short trace with its two caps: how a named neighbour reads.
          var y = g.y, x0 = g.x + 1.5, x1 = g.x + g.w - 1.5, bar = clamp(3.4 * geo.scale, 2.6, 4.6);
          ctx.globalAlpha = a;
          ctx.strokeStyle = palette.ink;
          ctx.fillStyle = palette.ink;
          ctx.lineWidth = lw(0.85);
          ctx.beginPath();
          ctx.moveTo(x0, y);
          ctx.lineTo(x1, y);
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(x0, y, 1.45, 0, TAU);
          ctx.fill();
          ctx.lineWidth = lw(1.1);
          ctx.beginPath();
          ctx.moveTo(x1, y - bar);
          ctx.lineTo(x1, y + bar);
          ctx.stroke();
        } else {
          markShape(g.x + geo.mr + 1, g.y, geo.mr, g.cls, EMBER[g.cls] ? palette.ember : palette.ink, a);
        }
      });
      ctx.textAlign = 'left';
      ctx.globalAlpha = 1;
    }
    function plateOf(fam) {
      for (var i = 0; i < geo.plates.length; i++) if (geo.plates[i].fam === fam) return geo.plates[i];
      return null;
    }

    /* ---- The sheet --------------------------------------------------- */
    function sheetRectNow(sheet) {
      return plateRectNow(plateOf(sheet.fam), sheet);
    }
    function drawSheet(sheet, lit, from) {
      var t = MOVE(sheetMix), R = sheetRectNow(sheet);
      var poly = chamfered(R.x0, R.y0, R.x1, R.y1, geo.cham);
      // The plate comes forward: an opaque face a full step above the
      // receding drawing, its side deeper than any plate at rest.
      ctx.globalAlpha = 1;
      polyPath(poly);
      ctx.fillStyle = palette.ground;
      ctx.fill();
      slab(poly, geo.depthStep * (1 + 0.8 * t), palette.face, palette.side);
      ctx.lineJoin = 'miter';
      ctx.lineWidth = lw(0.9);
      ctx.strokeStyle = palette.edge;
      polyPath(poly);
      ctx.stroke();
      // Its contents settle in as it arrives; a family giving way fades out.
      var settle = unit((sheetMix - 0.55) / 0.45);
      if (from && from !== sheet) drawSheetBody(from, lit, (1 - swapMix) * settle, 1, true);
      drawSheetBody(sheet, lit, (from ? swapMix : 1) * settle, t, false);
    }
    function drawSheetBody(sheet, lit, alpha, travel, leaving) {
      var f = lit.focus, focusComp = f && f.kind === 'comp' && model.comps[f.i].fam === sheet.fam ? f.i : -1;
      // The family's links inside it: the brackets, one stroke at rest, the
      // focused component's own traced out over them.
      if (alpha > 0.002) {
        ctx.lineCap = 'butt';
        ctx.lineJoin = 'round';
        ctx.beginPath();
        sheet.brackets.forEach(function (r) { tracePath(ctx, r, r.length * (leaving ? 1 : MOVE(alpha))); });
        ctx.globalAlpha = alpha * (focusComp >= 0 ? dimmed(0.35) : 1);
        ctx.lineWidth = hair;
        ctx.strokeStyle = palette.trace;
        ctx.stroke();
        if (focusComp >= 0 && !leaving) {
          drawLit(sheet.brackets, { kind: 'comp', i: focusComp }, alpha);
          drawCaps({ focus: { kind: 'comp', i: focusComp } }, sheet.brackets, alpha);
        }
      }
      // The title along the top, the count at the far end.
      ctx.textBaseline = 'alphabetic';
      ctx.globalAlpha = alpha;
      ctx.fillStyle = palette.ink;
      ctx.font = geo.fontEng;
      ctx.textAlign = 'left';
      ctx.font = geo.fontCount;
      ctx.fillStyle = hover && hover.kind === 'crumb' ? palette.ink : palette.faint;
      ctx.fillText(sheet.crumb.text, sheet.crumb.x, sheet.titleY);
      ctx.fillStyle = palette.faint;
      ctx.fillText(sheet.crumb.sep, sheet.crumb.x + sheet.crumb.textW, sheet.titleY);
      ctx.font = geo.fontEng;
      ctx.fillStyle = palette.ink;
      ctx.fillText(sheet.title, sheet.crumb.x + sheet.crumb.w, sheet.titleY);
      ctx.textAlign = 'right';
      ctx.font = geo.fontCount;
      ctx.fillStyle = palette.text;
      ctx.fillText(sheet.count, sheet.rect.x1 - geo.padX, sheet.titleY);
      ctx.textAlign = 'left';
      // Rows: the mark travels from its plate; the name settles beside it.
      var lc = lit.comps;
      sheet.rows.forEach(function (row) {
        var c = model.comps[row.comp];
        var on = focusComp < 0 || (lc && lc[row.comp]);
        var at = leaving ? [row.x, row.y] : markAt(row.comp, sheet);
        var markAlpha = leaving ? alpha : 1;
        if (on) markShape(at[0], at[1], geo.mr, c.cls, colorOf(c), markAlpha);
        else {
          markShape(at[0], at[1], geo.mr, c.cls, colorOf(c), markAlpha * (1 - focusMix));
          markShape(at[0], at[1], geo.mr, c.cls, palette.grey, markAlpha * focusMix);
        }
        ctx.font = sheet.nameFont;
        ctx.fillStyle = row.comp === focusComp ? palette.ink : palette.text;
        ctx.globalAlpha = alpha * (on ? 1 : dimmed(0.4));
        ctx.fillText(row.text, row.nameX, row.y + sheet.nameSize * 0.34);
      });
      ctx.globalAlpha = 1;
    }

    /* ---- Focus marks ------------------------------------------------- */
    // The reticle: four corner ticks that close in on the focus from a third
    // larger, over 140ms, once per change of focus.
    function drawReticle(x, y, q) {
      var mr = motion.reticle, t = mr ? DETENT(unit(mr.ms / RETICLE_MS)) : 1;
      var qq = q * (1.35 - 0.35 * t), arm = Math.max(3, q * 0.5);
      ctx.globalAlpha = t;
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = lw(1);
      ctx.lineCap = 'butt';
      ctx.lineJoin = 'miter';
      [[-1, -1], [1, -1], [1, 1], [-1, 1]].forEach(function (d) {
        var cx = x + d[0] * qq, cy = y + d[1] * qq;
        ctx.beginPath();
        ctx.moveTo(cx - d[0] * arm, cy);
        ctx.lineTo(cx, cy);
        ctx.lineTo(cx, cy - d[1] * arm);
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }
    function focusAnchor(f, sheet) {
      if (!f || !geo) return null;
      if (f.kind === 'comp') {
        if (sheet && model.comps[f.i].fam !== sheet.fam) return null;
        var at = markAt(f.i, sheet);
        return { x: at[0], y: at[1], q: geo.mr + clamp(4.5 * geo.scale, 3.5, 6) };
      }
      if (f.kind === 'step' && !sheet) {
        var st = geo.stations[f.i];
        return st ? { x: st.x, y: st.y, q: geo.railH / 2 + geo.tickL + 2 } : null;
      }
      return null;
    }
    // A name plate for the thing in focus on the overview (in a sheet the
    // names are already written). It is placed before any word, so a word it
    // would cover gives way while the reader points.
    function placePlate(focus, sheet) {
      if (!focus || !geo || sheet) return null;
      var an = focusAnchor(focus, null);
      if (!an) return null;
      var title, sub = null;
      if (focus.kind === 'comp') title = model.comps[focus.i].label;
      else if (focus.kind === 'step') {
        title = model.steps[focus.i].title;
        sub = 'step ' + (focus.i + 1) + ' of ' + model.steps.length + ' on the shared path';
      } else return null;
      var F = geo.fonts, pad = clamp(7 * geo.scale, 5, 9);
      var tw = measure(title, F.plate), sw = sub ? measure(sub, F.plateSub) : 0;
      var pw = Math.min(geo.w - 16, Math.max(tw, sw) + 2 * pad);
      var ph = F.plateSize * 1.25 + (sub ? F.plateSubSize * 1.3 : 0) + pad * 1.1;
      var lead = clamp(11 * geo.scale, 8, 14), run = clamp(9 * geo.scale, 6, 12);
      var best = null;
      [[1, -1], [-1, -1], [1, 1], [-1, 1]].forEach(function (d, k) {
        var sx = an.x + d[0] * an.q, sy = an.y + d[1] * an.q;
        var kx = sx + d[0] * lead, ky = sy + d[1] * lead;
        var x0 = d[0] > 0 ? kx + run : kx - run - pw;
        var box = { x0: x0, x1: x0 + pw, y0: ky - ph / 2, y1: ky + ph / 2 };
        var score = k * 0.1;
        if (box.x0 < 6 || box.x1 > geo.w - 6 || box.y0 < 6 || box.y1 > geo.fieldH - 4) score += 100;
        geo.labels.forEach(function (l) { if (boxesMeet(box, l.box, 1)) score += l.kind === 'legend' || l.kind === 'legend-count' ? 50 : 3; });
        geo.marks.forEach(function (mk, i) {
          if (i !== (focus.kind === 'comp' ? focus.i : -1) &&
              mk.x > box.x0 - 4 && mk.x < box.x1 + 4 && mk.y > box.y0 - 4 && mk.y < box.y1 + 4) score += 0.6;
        });
        if (!best || score < best.score) best = { score: score, box: box, d: d, sx: sx, sy: sy, kx: kx, ky: ky };
      });
      var bx = best.box;
      if (bx.x0 < 4) { bx.x1 += 4 - bx.x0; bx.x0 = 4; }
      if (bx.x1 > geo.w - 4) { bx.x0 -= bx.x1 - geo.w + 4; bx.x1 = geo.w - 4; }
      if (bx.y0 < 4) { bx.y1 += 4 - bx.y0; bx.y0 = 4; }
      return { box: bx, title: title, sub: sub, best: best, pad: pad, anchor: an };
    }
    function drawFocus(focus, lit, sheet, plate) {
      if (!focus) return;
      var an = focusAnchor(focus, sheet);
      if (an) drawReticle(an.x, an.y, an.q);
      if (!plate) return;
      var b = plate.best, F = geo.fonts, t = motion.reticle ? DETENT(unit(motion.reticle.ms / RETICLE_MS)) : 1;
      ctx.globalAlpha = t;
      // The leader: a hairline elbow from the reticle's corner to the plate.
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = lw(0.7);
      ctx.beginPath();
      ctx.moveTo(b.sx, b.sy);
      ctx.lineTo(b.kx, b.ky);
      ctx.lineTo(b.d[0] > 0 ? plate.box.x0 : plate.box.x1, b.ky);
      ctx.stroke();
      var poly = chamfered(plate.box.x0, plate.box.y0, plate.box.x1, plate.box.y1, 2.5);
      polyPath(poly);
      ctx.fillStyle = palette.ground;
      ctx.fill();
      ctx.lineWidth = lw(0.75);
      ctx.strokeStyle = palette.edge;
      ctx.stroke();
      ctx.fillStyle = palette.ink;
      ctx.font = F.plate;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'alphabetic';
      var ty = plate.box.y0 + plate.pad * 0.55 + F.plateSize * 0.98;
      ctx.fillText(fitWith(plate.title, plate.box.x1 - plate.box.x0 - 2 * plate.pad, F.plate, measure), plate.box.x0 + plate.pad, ty);
      if (plate.sub) {
        ctx.font = F.plateSub;
        ctx.fillStyle = palette.faint;
        ctx.fillText(plate.sub, plate.box.x0 + plate.pad, ty + F.plateSubSize * 1.3);
      }
      ctx.globalAlpha = 1;
    }

    /* ---- Words for the reader ---------------------------------------- */
    function classWords(c) { return c.cls ? CLASS_WORDS[c.cls] + '.' : ''; }
    function namesWords(c, short) {
      var o = c.out.length, n = c.inc.length;
      if (!o && !n) return 'It names no other component, and none names it.';
      var a = o ? 'Names ' + o + ' ' + (short ? plural(o, 'other', 'others') : plural(o, 'other component', 'other components')) : 'Names no other component';
      var b = n ? (n === 1 ? 'one names it' : n + ' name it') : 'none names it';
      return a + '; ' + b + '.';
    }
    function familyWords(f) {
      var n = f.members.length;
      return n + ' ' + plural(n, 'component', 'components') + '; ' + f.within + ' ' +
        plural(f.within, 'link', 'links') + ' among them, ' + f.cross + ' with other families.';
    }
    function stepWords(i) {
      var n = model.steps.length, nf = model.families.length;
      var who = model.bindCount >= nf ? 'every family uses' : model.bindCount + ' of the ' + nf + ' families use';
      return model.steps[i].title + ': step ' + (i + 1) + ' of ' + n + ' on the shared path ' + who + '.';
    }
    /* The caption says where the reader is, as a trail ("All families /
       Formal math & proof / Verifier Lab Kernel"), then what is pointed at,
       in a plain sentence. */
    var spoken = '';
    function trail(parts) { return parts.join(' / '); }
    function announce(focus) {
      if (!caption || !model) return;
      var text, fam = shownFamily();
      if (fam >= 0 && sheetMix > 0) {
        var F = model.families[fam];
        var c = pin && pin.fam === fam && pin.comp >= 0 && preview < 0 ? model.comps[pin.comp] : null;
        var hc = focus && focus.kind === 'comp' && (!c || focus.i !== pin.comp) ? model.comps[focus.i] : null;
        if (hc) text = hc.label + '. ' + classWords(hc) + ' ' + namesWords(hc, true);
        else if (c) text = trail(['All families', F.title, c.label]) + '.';
        else text = trail(['All families', F.title]) + '. ' + F.members.length + ' ' + plural(F.members.length, 'component', 'components') + '.';
      } else if (focus && focus.kind === 'comp') {
        var cc = model.comps[focus.i];
        text = cc.label + ', ' + model.families[cc.fam].title + '. ' + classWords(cc) + ' ' + namesWords(cc, true);
      } else if (focus && focus.kind === 'family') {
        var ff = model.families[focus.i];
        text = ff.title + ', ' + ff.members.length + ' ' + plural(ff.members.length, 'component', 'components') + '. Select it to see their names.';
      } else if (focus && focus.kind === 'step') {
        text = stepWords(focus.i);
      } else {
        text = 'All families. Select one to see its components.';
      }
      text = text.replace(/\s+/g, ' ').trim();
      if (text !== spoken) { spoken = text; caption.textContent = text; }
    }

    /* ---- Family rows ------------------------------------------------- */
    /* The landing's list of families works the drawing: pointing at a row
       lights its plate at once and, after a short dwell, opens its sheet
       (the next row then opens at once); a row in keyboard focus opens its
       sheet straight away, and the arrow keys walk its components, Enter
       selecting the one reached. The rows stay links to the family pages. */
    function syncRows(focus) {
      var fam = shownFamily();
      if (fam < 0 && focus && model) fam = focus.kind === 'family' ? focus.i : focus.kind === 'comp' ? model.comps[focus.i].fam : -1;
      rows.forEach(function (row) {
        if (row.el.classList) row.el.classList.toggle('is-current', fam >= 0 && row.fam === fam);
      });
    }
    function wireRows() {
      if (!section || !section.querySelectorAll || !model) return;
      var famById = Object.create(null);
      model.families.forEach(function (f, i) { famById[f.id] = i; });
      Array.prototype.forEach.call(section.querySelectorAll('.home-family[data-system-family]'), function (el) {
        var fam = famById[el.getAttribute('data-system-family')];
        if (fam === undefined) return;
        rows.push({ el: el, fam: fam });
        function enter(now) {
          if (rowTimer) { clearTimeout(rowTimer); rowTimer = null; }
          if (dwellTimer) { clearTimeout(dwellTimer); dwellTimer = null; }
          rowHover = fam;
          if (now || preview >= 0) openPreview(fam, now);
          else dwellTimer = setTimeout(function () { dwellTimer = null; if (rowHover === fam) openPreview(fam, false); }, 520);
          draw();
        }
        function leave() {
          if (dwellTimer) { clearTimeout(dwellTimer); dwellTimer = null; }
          if (rowTimer) clearTimeout(rowTimer);
          rowTimer = setTimeout(function () {
            rowTimer = null; rowHover = -1; keyComp = -1;
            if (preview >= 0) { preview = -1; syncSheet(false); renderCard(); }
            draw();
          }, 250);
        }
        el.addEventListener('pointerenter', function (e) {
          if ((e && e.pointerType === 'touch') || (fineQuery && !fineQuery.matches)) return;
          enter(false);
        });
        el.addEventListener('pointerleave', function (e) {
          if ((e && e.pointerType === 'touch') || (fineQuery && !fineQuery.matches)) return;
          leave();
        });
        el.addEventListener('focusin', function () { enter(true); });
        el.addEventListener('focusout', leave);
        el.addEventListener('keydown', function (e) {
          var list = model.families[fam].members, at = keyComp >= 0 ? list.indexOf(keyComp) : -1;
          if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { at = Math.min(list.length - 1, at + 1); }
          else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { at = at < 0 ? 0 : Math.max(0, at - 1); }
          else if (e.key === 'Enter' && keyComp >= 0) {
            // Enter selects the component reached; the selection takes over
            // from the arrow keys, so Escape then steps back a level.
            e.preventDefault();
            var chosen = keyComp;
            keyComp = -1; preview = -1;
            pinTo({ fam: fam, comp: chosen }, true);
            return;
          }
          else if (e.key === 'Escape' && keyComp >= 0) { keyComp = -1; draw(); e.stopPropagation(); return; }
          else return;
          e.preventDefault();
          keyComp = list[at];
          draw();
        });
      });
    }
    function openPreview(fam, now) {
      if (pin && pin.fam === fam) { preview = -1; syncSheet(now); renderCard(); return; }
      preview = fam;
      syncSheet(now);
      renderCard();
    }

    /* ---- The card ---------------------------------------------------- */
    /* Beside an open sheet, a card in the column the sheet leaves free (or,
       on a narrow screen, over the half the selection is not in): the family
       and its summary, or the selected component with what it does, what
       backs it, the components it names and those naming it (point at one
       to light it, select it to go there), and its pages. */
    var card = null;
    function el(tag, cls, text) {
      var node = document.createElement(tag);
      if (cls) node.className = cls;
      if (text != null) node.textContent = text;
      return node;
    }
    function go(href, text, primary) {
      var a = el('a', 'system-card__go' + (primary ? ' system-card__go--primary' : ''), text);
      a.setAttribute('href', href);
      return a;
    }
    function actions(links) {
      var row = el('p', 'system-card__actions');
      links.forEach(function (a) { row.appendChild(a); });
      card.appendChild(row);
    }
    function peerList(label, ids) {
      var p = el('p', 'system-card__peers');
      p.appendChild(el('span', 'system-card__peers-label', label + ' '));
      var shown = ids.slice(0, 4);
      shown.forEach(function (ci, k) {
        // A name in the sentence, inline so its comma stays with it, that
        // answers like a button: point at it to light it, select it to go.
        var b = el('span', 'system-card__peer', model.comps[ci].label);
        b.setAttribute('role', 'button');
        b.setAttribute('tabindex', '0');
        var choose = function () { listHover = -1; pinTo({ fam: model.comps[ci].fam, comp: ci }, false); };
        b.addEventListener('pointerenter', function () { listHover = ci; draw(); });
        b.addEventListener('pointerleave', function () { if (listHover === ci) { listHover = -1; draw(); } });
        b.addEventListener('focus', function () { listHover = ci; draw(); });
        b.addEventListener('blur', function () { if (listHover === ci) { listHover = -1; draw(); } });
        b.addEventListener('click', choose);
        b.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(); }
        });
        p.appendChild(b);
        if (k < shown.length - 1) p.appendChild(document.createTextNode(k === shown.length - 2 && ids.length <= 4 ? ' and ' : ', '));
      });
      if (ids.length > 4) p.appendChild(document.createTextNode(' and ' + (ids.length - 4) + ' more'));
      p.appendChild(document.createTextNode('.'));
      return p;
    }
    function renderCard() {
      if (!document.createElement || !stage.appendChild || !model) return;
      var fam = shownFamily();
      if (fam < 0) { if (card) card.hidden = true; return; }
      var narrow = !(sheetOf(fam) || {}).card;
      var c0 = pin && preview < 0 && pin.fam === fam && pin.comp >= 0;
      // A narrow screen has no room beside the sheet: the family's sheet
      // stands alone, and a component's card takes the whole drawing (its
      // first line leads back), so nothing is ever half covered.
      if (narrow && !c0) { if (card) card.hidden = true; return; }
      if (!card) {
        card = el('div', 'system-card');
        card.setAttribute('role', 'group');
        stage.appendChild(card);
      }
      while (card.firstChild) card.removeChild(card.firstChild);
      var F = model.families[fam], title, links = [];
      var c = pin && preview < 0 && pin.fam === fam && pin.comp >= 0 ? model.comps[pin.comp] : null;
      if (c) {
        title = c.label;
        var back = el('button', 'system-card__back');
        back.setAttribute('type', 'button');
        back.appendChild(el('span', 'system-card__back-mark', '‹'));
        back.lastChild.setAttribute('aria-hidden', 'true');
        back.appendChild(document.createTextNode(' ' + F.title));
        back.setAttribute('aria-label', 'Back to ' + F.title);
        back.addEventListener('click', function () { pinTo({ fam: fam, comp: -1 }, false); });
        var trailP = el('p', 'system-card__trail');
        trailP.appendChild(back);
        card.appendChild(trailP);
        card.appendChild(el('p', 'system-card__title', title));
        var meta = ((c.cls ? CLASS_WORDS[c.cls] + '.' : '') + (c.basis ? ' Backed by: ' + lowerFirst(c.basis) + '.' : '')).trim();
        if (meta) card.appendChild(el('p', 'system-card__meta', meta));
        if (c.line) card.appendChild(el('p', 'system-card__line', c.line));
        // The ways out come before the lists, so they stay in view on a
        // short screen; the lists may run on below them.
        if (c.page) links.push(go(c.page, 'Component page', true));
        if (c.reader) links.push(go(c.reader, 'Paper module'));
        links.push(go(c.mapHref, 'In the architecture map', !c.page));
        actions(links);
        if (c.out.length) card.appendChild(peerList('It names', c.out));
        if (c.inc.length) card.appendChild(peerList('Named by', c.inc));
        if (!c.out.length && !c.inc.length) card.appendChild(el('p', 'system-card__meta', 'It names no other component, and none names it.'));
        else card.appendChild(el('p', 'system-card__note', 'A named neighbour is not proof that one calls the other.'));
        links = null;
      } else {
        title = F.title;
        card.appendChild(el('p', 'system-card__title', title));
        card.appendChild(el('p', 'system-card__meta', familyWords(F)));
        if (F.summary) card.appendChild(el('p', 'system-card__line', F.summary));
        card.appendChild(el('p', 'system-card__note', 'Select a component for what it does and what it names.'));
        if (F.page) links.push(go(F.page, 'Family page', true));
        links.push(go(F.mapHref, 'In the architecture map', !F.page));
      }
      card.setAttribute('aria-label', title);
      if (links) actions(links);
      card.hidden = false;
      placeCard();
    }
    function placeCard() {
      if (!card || card.hidden || !geo || !geo.ok || !card.style) return;
      var fam = shownFamily(), sheet = sheetOf(fam);
      if (!sheet) return;
      var inset = geo.m * 0.6;
      if (sheet.card) {
        if (card.classList) card.classList.remove('system-card--full');
        card.style.height = '';
        // The card stops where the drawing does, above the legend.
        card.style.left = Math.round(sheet.card.x0) + 'px';
        card.style.top = Math.round(sheet.rect.y0) + 'px';
        card.style.width = Math.round(sheet.card.x1 - sheet.card.x0) + 'px';
        card.style.maxHeight = Math.round(geo.fieldH - sheet.rect.y0 - geo.m * 0.4) + 'px';
        return;
      }
      // Narrow: the component's card is the whole view, edge to edge.
      if (card.classList) card.classList.add('system-card--full');
      card.style.left = '0px';
      card.style.top = '0px';
      card.style.width = Math.round(geo.w) + 'px';
      card.style.maxHeight = 'none';
      card.style.height = Math.round(geo.h) + 'px';
    }

    /* ---- Pointer ----------------------------------------------------- */
    function hitTest(x, y) {
      if (!geo || !geo.ok || openState !== 'done') return null;
      var sheet = sheetFam >= 0 && sheetMix >= 1 ? sheetOf(sheetFam) : null;
      if (sheet) {
        if (!pointInRect(x, y, sheet.rect)) return { kind: 'outside' };
        if (pointInRect(x, y, sheet.crumb.box)) return { kind: 'crumb' };
        for (var r = 0; r < sheet.rows.length; r++) {
          var row = sheet.rows[r];
          if (y >= row.box.y0 && y < row.box.y1 && x >= row.box.x0 && x <= row.box.x1) return { kind: 'comp', i: row.comp };
        }
        return { kind: 'sheet' };
      }
      if (sheetFam >= 0) return null;
      // Every mark answers within at least 12px of its centre (a 24px target).
      var best = -1, bestD = Infinity, reachM = Math.max(12, Math.min(16, geo.pitch * 0.5));
      geo.marks.forEach(function (mk, i) {
        var d = Math.hypot(mk.x - x, mk.y - y);
        if (d < reachM && d < bestD) { best = i; bestD = d; }
      });
      if (best >= 0) return { kind: 'comp', i: best };
      for (var l = 0; l < geo.labels.length; l++) {
        var lb = geo.labels[l];
        if (lb.kind === 'step' && x >= lb.box.x0 - 3 && x <= lb.box.x1 + 3 && y >= lb.box.y0 - 3 && y <= lb.box.y1 + 3) return { kind: 'step', i: lb.step };
      }
      var reachS = geo.labelReach + 4;
      for (var s = 0; s < geo.stations.length; s++) {
        var st = geo.stations[s];
        var along = geo.portrait ? Math.abs(y - st.y) : Math.abs(x - st.x);
        var across = geo.portrait ? Math.abs(x - st.x) : Math.abs(y - st.y);
        if (along <= 12 && across <= reachS) return { kind: 'step', i: s };
      }
      for (var b = 0; b < geo.plates.length; b++) {
        if (pointInRect(x, y, geo.plates[b].rect)) return { kind: 'family', i: geo.plates[b].fam };
      }
      return null;
    }
    function local(event) {
      var rect = canvas.getBoundingClientRect ? canvas.getBoundingClientRect() : { left: 0, top: 0 };
      return [event.clientX - rect.left, event.clientY - rect.top];
    }
    function hoverable(hit) { return !!hit && hit.kind !== 'outside' && hit.kind !== 'sheet'; }
    canvas.addEventListener('pointermove', function (event) {
      if (event.pointerType === 'touch' || (fineQuery && !fineQuery.matches)) return;
      var q = local(event), hit = hitTest(q[0], q[1]);
      var h = hoverable(hit) ? hit : null;
      if (canvas.classList) canvas.classList.toggle('is-over', h ? true : !!(hit && hit.kind === 'outside'));
      if (!sameFocus(h, hover)) { hover = h; draw(); }
    });
    canvas.addEventListener('pointerleave', function () {
      if (canvas.classList) canvas.classList.remove('is-over');
      if (!hover) return;
      hover = null;
      draw();
    });
    canvas.addEventListener('click', function (event) {
      if (openState === 'running') settleAll();
      var q = local(event), hit = hitTest(q[0], q[1]);
      if (event.detail >= 2 && hit && hit.kind === 'comp') {
        var target = model.comps[hit.i].page || model.comps[hit.i].mapHref;
        if (target) { window.location.href = target; return; }
      }
      if (event.detail >= 2 && hit && hit.kind === 'family') {
        var fpage = model.families[hit.i].page || model.families[hit.i].mapHref;
        if (fpage) { window.location.href = fpage; return; }
      }
      if (!hit || hit.kind === 'outside') { stepBack(); return; }
      if (hit.kind === 'crumb') { preview = -1; pinTo(null, false); return; }
      if (hit.kind === 'comp') { pinTo({ fam: model.comps[hit.i].fam, comp: hit.i }, false); return; }
      if (hit.kind === 'family') { pinTo({ fam: hit.i, comp: -1 }, false); return; }
    });
    document.addEventListener('keydown', function (event) {
      if (event.key !== 'Escape' || (!pin && preview < 0)) return;
      stepBack();
    });
    // One level up: a component to its family, a family to the overview.
    function stepBack() {
      if (preview >= 0) { preview = -1; syncSheet(false); renderCard(); draw(); return; }
      if (!pin) return;
      if (pin.comp >= 0) pinTo({ fam: pin.fam, comp: -1 }, false);
      else pinTo(null, false);
    }
    function pinTo(target, instant) {
      pin = target;
      listHover = -1;
      if (!fineQuery || !fineQuery.matches) hover = null;
      syncSheet(instant);
      renderCard();
      draw();
    }

    /* ---- Data -------------------------------------------------------- */
    function lookup(id) {
      if (!model || !id) return null;
      for (var i = 0; i < model.comps.length; i++) if (model.comps[i].id === id) return { fam: model.comps[i].fam, comp: i };
      for (var f = 0; f < model.families.length; f++) if (model.families[f].id === id) return { fam: f, comp: -1 };
      return null;
    }
    var pending = null;
    var api = {
      // Lights a family in place, as pointing at its row does (null clears).
      focusFamily: function (id) {
        if (!model) { pending = pending || {}; pending.family = id; return; }
        var t = id ? lookup(id) : null;
        rowHover = t && t.comp < 0 ? t.fam : -1;
        draw();
      },
      // Opens a family's sheet or selects a component (null: the overview).
      select: function (id) {
        if (!model) { pending = pending || {}; pending.select = id; return; }
        preview = -1;
        pinTo(id ? lookup(id) : null, false);
      },
      // Read-only: the drawing's geometry and state, for tests and audits.
      snapshot: function () {
        if (!model || !geo || !geo.ok) return { ready: false, open: openState };
        return {
          ready: true, stale: model.stale, portrait: geo.portrait, width: geo.w, height: geo.h, open: openState,
          dropped: model.dropped, pitch: geo.pitch, markRadius: geo.mr, lanes: geo.lanes.slice(),
          level: shownFamily() < 0 ? 'overview' : (pin && pin.comp >= 0 && preview < 0 ? 'component' : 'family'),
          components: model.comps.map(function (c, i) {
            return { id: c.id, label: c.label, family: model.families[c.fam].id, cls: c.cls,
                     x: geo.marks[i].x, y: geo.marks[i].y };
          }),
          plates: geo.plates.map(function (g) {
            return { id: model.families[g.fam].id, title: model.families[g.fam].title,
                     count: model.families[g.fam].members.length, row: g.row,
                     rect: { x0: g.rect.x0, y0: g.rect.y0, x1: g.rect.x1, y1: g.rect.y1 } };
          }),
          stations: geo.stations.map(function (st, i) { return { id: model.steps[i].id, title: model.steps[i].title, x: st.x, y: st.y }; }),
          links: geo.routes.map(function (r) {
            return { source: model.comps[r.a].id, target: model.comps[r.b].id, length: r.length,
                     points: r.points.map(function (q) { return [q[0], q[1]]; }) };
          }),
          labels: geo.labels.map(function (l) { return { kind: l.kind, text: l.text, box: l.box }; }),
          drawn: placed.map(function (b) { return { x0: b.x0, y0: b.y0, x1: b.x1, y1: b.y1 }; }),
          focus: currentFocus(), hover: hover, pinned: pin, preview: preview >= 0 ? model.families[preview].id : null,
          sheet: sheetFam >= 0 && sheetMix > 0 ? (function (sh) {
            return { family: model.families[sh.fam].id, rect: sh.rect, card: sh.card,
                     rows: sh.rows.map(function (r) { return { id: model.comps[r.comp].id, text: r.text, y: r.y, box: r.box }; }),
                     brackets: sh.brackets.length };
          })(sheetOf(sheetFam)) : null
        };
      }
    };
    window.PlectisSystemMap = api;

    readPalette();
    if (!src || typeof fetch !== 'function') return api;
    fetch(src, { cache: 'no-cache' }).then(function (res) {
      if (res && res.ok === false) throw new Error('scene ' + res.status);
      return res.json();
    }).then(function (json) {
      model = readScene(json, base);
      json = null;
      if (!model || !model.comps.length) throw new Error('empty scene');
      relayout();
      wireRows();
      // The drawing waits, closed, until it is first in view and still; a
      // reader who cannot have motion gets the finished drawing at once.
      if (reduceMotion || !window.requestAnimationFrame || document.hidden) { opened = true; openState = 'done'; }
      else openState = 'waiting';
      paint();
      maybeOpen();
      if (pending) {
        if (pending.family !== undefined) api.focusFamily(pending.family);
        if (pending.select !== undefined) api.select(pending.select);
        pending = null;
      }
    }).catch(function () {
      if (stage.classList) stage.classList.add('is-unavailable');
    });

    /* ---- Housekeeping ------------------------------------------------ */
    function refit() {
      if (!model) return;
      relayout();
      paint();
      placeCard();
    }
    if ('ResizeObserver' in window) {
      new window.ResizeObserver(function () {
        if ((canvas.clientWidth || 0) !== cssW || (canvas.clientHeight || 0) !== cssH) refit();
      }).observe(canvas);
    } else {
      window.addEventListener('resize', refit);
    }
    function retheme() { readPalette(); paint(); }
    document.addEventListener('plectis:theme', retheme);
    var schemeQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
    if (schemeQuery && typeof schemeQuery.addEventListener === 'function') schemeQuery.addEventListener('change', retheme);
    // Reduced motion is followed live: turning it on mid-way finishes every
    // motion at once and draws the still structure.
    function followReduce() {
      reduceMotion = !!(reduceQuery && reduceQuery.matches);
      if (!reduceMotion) return;
      settleAll();
      if (!opened) { opened = true; openState = 'done'; }
      paint();
    }
    if (reduceQuery && typeof reduceQuery.addEventListener === 'function') reduceQuery.addEventListener('change', followReduce);
    // A canvas neither waits for a web font nor redraws when one arrives.
    if (document.fonts && document.fonts.load) {
      Promise.all([
        document.fonts.load('500 11px "Plectis Serif"'),
        document.fonts.load('400 11px "Plectis Serif"'),
        document.fonts.load('italic 400 11px "Plectis Serif"')
      ]).then(function () { if (model) refit(); }, function () {});
    }
    return api;
  }

  function boot() {
    var stages = document.querySelectorAll('[data-system-stage]');
    Array.prototype.forEach.call(stages, function (stage) { mount(stage); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
