/* Plectis: the system map.
   The earlier software toolkit's components, drawn as a precision schematic
   in which every part shows how it connects to every other.

   The shared path runs across the middle as the datum line, its steps as
   stations in their declared order. The families are plates above and below
   it, each standing on the line's side of the drawing and as deep as its own
   components need, so a small family is a small plate. Every component is a
   mark on one lattice that runs through the whole drawing: marks on its
   points, wiring in the gutters between them, plate edges a fixed tolerance
   inside the lattice lines. A mark's form and colour are set by its
   evidence class.

   The declared links between two families travel together as one cable. It
   leaves each plate through a connector on the edge facing the shared path,
   with one pin for every link it carries, and runs to the other plate in a
   lane beside the line; lanes are evenly spaced, and a cable that crosses
   the line passes under it, clear of the station names. A cable is a count
   of declarations, nothing more: pointing at a component draws its own
   links out of their cables, from its mark through its pin to every
   component it names or is named by, with a dot at the naming end and a bar
   at the named end.

   Three levels, each a step down. At rest the drawing reads as the families
   round the shared path. A family selected on the map (or pointed at in the
   landing's list) opens: its plate expands into a sheet that names every
   component, its links inside the family drawn as nested brackets, and a
   card beside it describes the family. A component selected there gets the
   card: what it does, what backs it, the components it names and those that
   name it. Escape, a click on empty ground, or the back line on the sheet or
   the card steps back one level.

   Everything drawn comes from docs/architecture-graph-scene.json, the scene
   the architecture map reads; the script parses it once and keeps only what
   it draws. Family membership is navigation grouping. A declared link is the
   source's own declaration, not proof that one component calls another, nor
   of causation, maturity or correctness. Colour belongs to evidence alone:
   ember marks the components whose evidence runs real tools, and everything
   else is ink. Every number drawn is a count from the scene.

   Motion has a cause or is the figure's one opening. As soon as the scene is
   read the drawing shows its blueprint: the line and the plates' outlines,
   the lattice points faint. When it first comes into view and is still, the
   blueprint is built out once, in about a second and a quarter: the line
   draws, the plates seat onto their outlines in two short beats, the marks
   set, the connectors and cables route in along their lanes, and the names
   come up. A plate opens into its sheet from its own rectangle and closes
   back into it; the card arrives from what was selected and returns to it.
   Under the pointer a component's links trace out once, in their declared
   direction, and settle. Nothing moves while the reader is idle. A keyboard
   step, an instant arrival and reduced motion land in the final state at
   once. The canvas paints on demand, caps the device pixel ratio at 2, and
   runs no motion off screen or in a hidden tab. */
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
  /* Two short beats, each settling hard: most of the way, a breath, home. */
  function beats(t) {
    if (t <= 0) return 0;
    if (t >= 1) return 1;
    if (t < 0.56) return 0.78 * DETENT(t / 0.56);
    if (t < 0.64) return 0.78;
    return 0.78 + 0.22 * DETENT((t - 0.64) / 0.36);
  }

  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }
  function unit(t) { return t <= 0 ? 0 : t >= 1 ? 1 : t; }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function isObj(v) { return !!v && typeof v === 'object' && !Array.isArray(v); }
  function str(v) { return typeof v === 'string' && v.trim() ? v.trim() : null; }
  function lowerFirst(text) { return text ? text.charAt(0).toLowerCase() + text.slice(1) : text; }
  function plural(n, one, many) { return n === 1 ? one : many; }
  function total(list) { var t = 0; for (var i = 0; i < list.length; i++) t += list[i]; return t; }

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
    // The links between two families travel together as one cable.
    var cables = [], cableAt = Object.create(null);
    links.forEach(function (l, li) {
      var fa = comps[l[0]].fam, fb = comps[l[1]].fam;
      if (fa === fb) { families[fa].within++; return; }
      families[fa].cross++; families[fb].cross++;
      var lo = Math.min(fa, fb), hi = Math.max(fa, fb), key = lo + '-' + hi;
      if (cableAt[key] === undefined) { cableAt[key] = cables.length; cables.push({ fa: lo, fb: hi, links: [] }); }
      cables[cableAt[key]].links.push(li);
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
    if (links.length) legend.push({ cls: 'link', count: links.length, label: 'Declared link' });

    return {
      families: families, comps: comps, links: links, cables: cables, steps: steps, legend: legend,
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
  // Adds a route to the current path, from `from` pixels along it for
  // `upto` pixels (the whole route when both are left out).
  function tracePath(ctx, path, upto, from) {
    var start = from || 0, end = upto == null ? Infinity : start + upto, at = 0, started = false;
    for (var i = 0; i < path.prims.length && at < end; i++) {
      var q = path.prims[i], a0 = at, a1 = at + q.len;
      at = a1;
      if (a1 <= start) continue;
      var f0 = Math.max(0, (start - a0) / q.len), f1 = Math.min(1, (end - a0) / q.len);
      if (f1 <= f0) continue;
      if (q.arc) {
        var s0 = q.a0 + q.sweep * f0, s1 = q.a0 + q.sweep * f1;
        if (!started) { ctx.moveTo(q.cx + q.r * Math.cos(s0), q.cy + q.r * Math.sin(s0)); started = true; }
        ctx.arc(q.cx, q.cy, q.r, s0, s1, q.sweep < 0);
      } else {
        var x0 = q.from[0] + (q.to[0] - q.from[0]) * f0, y0 = q.from[1] + (q.to[1] - q.from[1]) * f0;
        if (!started) { ctx.moveTo(x0, y0); started = true; }
        ctx.lineTo(q.from[0] + (q.to[0] - q.from[0]) * f1, q.from[1] + (q.to[1] - q.from[1]) * f1);
      }
    }
  }
  // A rectangle with its four corners cut at 45 degrees.
  function chamfered(x0, y0, x1, y1, k) {
    k = Math.max(0, Math.min(k, (x1 - x0) / 2, (y1 - y0) / 2));
    return [[x0 + k, y0], [x1 - k, y0], [x1, y0 + k], [x1, y1 - k], [x1 - k, y1], [x0 + k, y1], [x0, y1 - k], [x0, y0 + k]];
  }
  // Greedy interval packing: shortest spans first, each into the first lane
  // free along its whole span (with a margin), so a span inside another
  // always sits nearer the plates and the two never cross.
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
     when the box is taller than wide, so a phone gets a vertical line with
     the plates either side. Families keep the scene's order: the first half
     along the top row, the rest along the bottom, as the landing's family
     list reads. */
  function layoutSchematic(model, w, h, measure, dpr, opts) {
    opts = opts || {};
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

    /* Type: one size for each kind of word. */
    var fEng = clamp(11.4 * rs, 9.2, 13.6), fStep = clamp(10.4 * rs, 8.6, 12.2), fLeg = clamp(10.2 * rs, 8.6, 11.8);
    var fontEng = '500 ' + fEng.toFixed(2) + 'px ' + SERIF;
    var fontCount = '400 ' + fEng.toFixed(2) + 'px ' + SERIF;
    var fontLeg = '400 ' + fLeg.toFixed(2) + 'px ' + SERIF;
    var lineEng = whole(fEng * 1.28), lineLeg = whole(fLeg * 1.85);
    var asc = 0.74, desc = 0.26;

    /* Lengths, all set from the box. */
    var m = whole(clamp(14 * s, 8, 20));
    var padX = whole(clamp(9 * s, 6, 13)), padY = whole(clamp(7 * s, 5, 11));
    var g = 2 * whole(clamp(4 * s, 2.5, 6));               // between neighbouring plates
    var gm = whole(clamp(5 * s, 3.5, 7));                  // the edge channel inside a plate
    var cham = clamp(5 * s, 3.5, 7);
    var rb = clamp(3.2 * s, 2.2, 4.6);                     // every bend of every route
    var laneGap = whole(clamp(4 * s, 3, 6)), laneMargin = whole(clamp(9 * s, 6, 12));
    var depthStep = clamp(2.4 * s, 1.8, 3.2);              // a plate's side, drawn as an offset band
    var pinL = whole(depthStep + clamp(2 * s, 1.5, 3)), pinQ = Math.max(1 / dpr, whole(clamp(1.5 * s, 0.75, 2.5)));
    var railH = 2 * whole(clamp(1.75 * s, 1.25, 2.4)), tickL = whole(clamp(4 * s, 3, 6)), gapL = whole(clamp(4 * s, 3, 6));
    var capGap = clamp(1.6 * s, 1.2, 2.4);
    var sepC = whole(clamp(7 * s, 5, 9));                  // between neighbouring connectors on an edge
    var clearN = whole(clamp(5 * s, 4, 7));                // a crossing keeps this far from a name or a tick
    var mr = clamp(4.4 * Math.pow(s, 0.6), 3, 6.4);        // a component mark's radius

    /* The key along the foot: the five classes with their counts, then the
       declared link, in a grid whose columns line up, in as few rows as fit. */
    var legend = null;
    if (!opts.noLegend && model.legend.length) {
      var items = model.legend.map(function (it) {
        var lw = measure(it.label, fontLeg), cw = measure(String(it.count), fontLeg);
        var glyph = it.cls === 'link' ? whole(clamp(17 * s, 13, 23)) : whole(2 * mr + 2);
        var gi = whole(clamp(6 * s, 4, 8)), gc = whole(clamp(4.5 * s, 3, 6));
        return { cls: it.cls, label: it.label, count: it.count, lw: lw, cw: cw, glyph: glyph, gi: gi, gc: gc,
                 w: glyph + gi + lw + gc + cw };
      });
      var legGap = whole(clamp(22 * s, 12, 30)), roomL = w - 2 * m, nL = items.length;
      var tries = [nL, Math.ceil(nL / 2), Math.ceil(nL / 3), 1].filter(function (v, i, a) { return a.indexOf(v) === i; });
      for (var ti = 0; ti < tries.length && !legend; ti++) {
        var cols = tries[ti], rowsL = Math.ceil(nL / cols), colW = [];
        for (var c = 0; c < cols; c++) {
          colW[c] = 0;
          for (var r = 0; r < rowsL; r++) { var it = items[r * cols + c]; if (it) colW[c] = Math.max(colW[c], it.w); }
        }
        var lwid = total(colW) + legGap * (cols - 1);
        if (lwid <= roomL || cols === 1) legend = { items: items, cols: cols, rows: rowsL, colW: colW, width: lwid, gap: legGap };
      }
    }
    var legendH = legend ? legend.rows * lineLeg + whole(padY * 1.2) : 0;

    var X0 = m, Y0 = m, X1 = w - m, Y1 = h - m - legendH;
    var VW = portrait ? Y1 - Y0 : X1 - X0, VH = portrait ? X1 - X0 : Y1 - Y0;
    if (VW < 80 || VH < 80) return opts.noLegend ? geo : layoutSchematic(model, w, h, measure, dpr, { noLegend: true });
    function T(vx, vy) { return portrait ? [X0 + vy, Y0 + vx] : [X0 + vx, Y0 + vy]; }

    /* The stations' names, alternating sides of the line so neighbours never
       crowd: set smaller where two on one side would meet, and given up
       below a floor (a station then names itself when pointed at). */
    var fontStep = 'italic 400 ' + fStep.toFixed(2) + 'px ' + SERIF;
    var stepLabels = model.steps.map(function (st, i) {
      return { text: st.title, tw: measure(st.title, fontStep), side: i % 2 === 0 ? -1 : 1 };
    });
    var stepNames = nStep > 0;
    var widestStep = stepLabels.reduce(function (t, l) { return Math.max(t, l.tw); }, 0);
    if (!portrait && nStep > 2) {
      var roomS = 2 * (VW - widestStep) / (nStep - 1) - 10;
      if (widestStep > roomS) {
        var shrink = roomS / widestStep;
        if (shrink < 0.78) stepNames = false;
        else {
          fStep *= shrink;
          fontStep = 'italic 400 ' + fStep.toFixed(2) + 'px ' + SERIF;
          stepLabels.forEach(function (l) { l.tw = measure(l.text, fontStep); });
          widestStep = stepLabels.reduce(function (t, l) { return Math.max(t, l.tw); }, 0);
        }
      }
    }
    if (portrait && 2 * widestStep > 0.2 * VH) stepNames = false;
    var lineStep = whole(fStep * 1.2);
    var labDepth = stepNames ? (portrait ? widestStep : lineStep) : 0;
    var halfBand = whole(railH / 2 + tickL + (stepNames ? gapL + labDepth : 2));

    /* A family's name: on one line where its plate allows, else in two
       balanced lines that never end on an ampersand; its count at the far
       end of the line nearest the plate's outer edge. */
    var engr = model.families.map(function (f) {
      var count = String(f.members.length), cw = measure(count, fontCount), gapC = whole(clamp(10 * s, 6, 14));
      var words = f.title.split(/\s+/), two = null;
      for (var cut = 1; cut < words.length; cut++) {
        if (words[cut - 1] === '&') continue;
        var a = words.slice(0, cut).join(' '), b = words.slice(cut).join(' ');
        var wid = Math.max(measure(a, fontEng), measure(b, fontEng));
        if (!two || wid < two.w - 0.5) two = { lines: [a, b], w: wid };
      }
      return { count: count, cw: cw, gapC: gapC, oneW: measure(f.title, fontEng), two: two };
    });
    function nameW(fi, lines) { var e = engr[fi]; return (lines === 1 || !e.two ? e.oneW : e.two.w) + e.gapC + e.cw; }
    function nameLines(fi, lines) { return lines === 1 || !engr[fi].two ? [model.families[fi].title] : engr[fi].two.lines; }

    var topN = Math.ceil(nFam / 2), famRows = [[], []];
    model.families.forEach(function (f, i) { famRows[i < topN ? 0 : 1].push(i); });

    /* One row of plates at pitch p on a lattice of N columns. Every plate
       takes whole columns; the choice weighs, in order: fewer rows of marks,
       names on one line, few empty places, and an even rhythm of gaps. On a
       phone the name takes whole columns at the head of its plate. */
    function bandCols(fi, lines, p) {
      return Math.ceil((padY * 1.2 + fEng + (lines - 1) * lineEng + padY) / p - 1e-6);
    }
    // The edge a plate needs for its terminals (one per cable, a pin pitch
    // per link) and its tie, with a gap between each and room at the corners.
    var edgeNeed = model.families.map(function (f, fi) {
      var need = sepC + 2 * (cham + 3);
      model.cables.forEach(function (cb) {
        if (cb.fa === fi || cb.fb === fi) need += (cb.links.length - 1) * pinQ + sepC;
      });
      return need;
    });
    function allocate(row, N, p) {
      var k = row.length;
      var n = row.map(function (fi) { return model.families[fi].members.length; });
      // The column counts worth trying for each plate: those that change its
      // rows or its name's lines.
      var options = row.map(function (fi, j) {
        var opts2 = [];
        var edge = Math.max(1, Math.ceil((edgeNeed[fi] + g) / p - 1e-6));
        if (portrait) {
          var tb = bandCols(fi, 2, p);
          for (var mc = 1; mc <= n[j]; mc++) {
            if (Math.ceil(n[j] / mc) !== Math.ceil(n[j] / (mc + 1)) || mc === n[j]) {
              opts2.push({ cols: Math.max(tb + mc, edge), marks: mc, lines: 2, band: tb });
            }
          }
          return opts2;
        }
        var two = Math.max(1, edge, Math.ceil((nameW(fi, 2) + 2 * padX + g) / p - 1e-6));
        var one = Math.max(1, Math.ceil((nameW(fi, 1) + 2 * padX + g) / p - 1e-6));
        var set = [two, one];
        for (var rr = 1; rr <= n[j]; rr++) set.push(Math.ceil(n[j] / rr));
        set.filter(function (v, i, a) { return v >= two && v <= N && a.indexOf(v) === i; }).sort(function (a, b) { return a - b; })
          .forEach(function (cols) { opts2.push({ cols: cols, marks: Math.min(cols, n[j]), lines: cols >= one ? 1 : 2, band: 0 }); });
        return opts2;
      });
      if (options.some(function (o) { return !o.length; })) return null;
      var best = null, pick = [];
      (function walk(j, used) {
        if (j === k) {
          var left = N - used, rows = pick.map(function (o, i) { return Math.ceil(n[i] / o.marks); });
          var deep = Math.max.apply(null, rows);
          var empty = 0, twoLines = 0;
          pick.forEach(function (o, i) { empty += rows[i] * o.marks - n[i] + (o.cols - o.band - o.marks) * rows[i] * 0.6; if (o.lines === 2) twoLines++; });
          var gaps = k - 1, per = gaps ? Math.floor(left / gaps) : 0, rem = left - per * gaps;
          var cost = deep * 3 + twoLines * 0.6 + empty * 0.35 + (rem ? 0.6 + 0.3 * rem : 0) + per * gaps * 0.12;
          if (!best || cost < best.cost - 1e-9) best = { cost: cost, pick: pick.slice(), rows: rows, per: per, rem: rem };
          return;
        }
        options[j].forEach(function (o) {
          if (used + o.cols + (k - j - 1) > N) return;
          pick[j] = o;
          walk(j + 1, used + o.cols);
        });
      })(0, 0);
      return best;
    }

    /* Where a crossing may pass the line: clear of every station's name and
       tick by a few pixels, and of the crossings already placed: by a few
       pixels in the corridor, by both terminals and a gap on a plate edge
       the two share. */
    function freeAt(x, me, placed, stations) {
      for (var i = 0; i < stations.length; i++) {
        if (Math.abs(x - stations[i]) < clearN + 1.5) return false;
        if (stepNames) {
          var hw = (portrait ? lineStep : stepLabels[i].tw) / 2 + clearN;
          if (Math.abs(x - stations[i]) < hw) return false;
        }
      }
      for (var k = 0; k < placed.length; k++) {
        var o = placed[k], shares = (!!me.top && o.top === me.top) || (!!me.bot && o.bot === me.bot);
        var need = shares ? (o.w + me.w) / 2 + sepC : clearN + 1;
        if (Math.abs(x - o.x) < need) return false;
      }
      return true;
    }
    // The free stretches of [lo, hi] once the forbidden ones are taken out.
    function freeStretches(lo, hi, bad) {
      bad.sort(function (a, b) { return a[0] - b[0]; });
      var out = [], cur = lo;
      for (var i = 0; i < bad.length && cur < hi; i++) {
        if (bad[i][1] <= cur) continue;
        if (bad[i][0] > cur) out.push([cur, Math.min(bad[i][0], hi)]);
        cur = Math.max(cur, bad[i][1]);
      }
      if (cur < hi) out.push([cur, hi]);
      return out;
    }
    // The place nearest the target that is free, on the device-pixel grid.
    function nearestFree(target, lo, hi, me, placed, stations) {
      if (lo > hi) return null;
      var bad = [], e = 1 / dpr;
      stations.forEach(function (sx, i) {
        var hw = clearN + 1.5;
        if (stepNames) hw = Math.max(hw, (portrait ? lineStep : stepLabels[i].tw) / 2 + clearN);
        bad.push([sx - hw, sx + hw]);
      });
      placed.forEach(function (o) {
        var shares = (!!me.top && o.top === me.top) || (!!me.bot && o.bot === me.bot);
        var need = shares ? (o.w + me.w) / 2 + sepC : clearN + 1;
        bad.push([o.x - need, o.x + need]);
      });
      var best = null;
      freeStretches(lo, hi, bad).forEach(function (iv) {
        if (iv[1] - iv[0] < 2 * e) return;
        var x = half(clamp(target, iv[0] + e, iv[1] - e));
        if (!freeAt(x, me, placed, stations)) return;
        if (best === null || Math.abs(x - target) < Math.abs(best - target)) best = x;
      });
      return best;
    }

    /* Everything that depends on the pitch: the plates, the stations, the
       connectors, the cables and their lanes, and the height they need. */
    function trial(p) {
      var N = Math.floor((VW + g) / p);
      if (N < 1) return null;
      var extent = N * p - g, lx0 = (VW - extent) / 2;
      function colX(c) { return half(lx0 - g / 2 + (c + 0.5) * p); }
      var plates = [], rowPlates = [[], []], cost = 0;
      for (var ri = 0; ri < 2; ri++) {
        var row = famRows[ri];
        if (!row.length) continue;
        var al = allocate(row, N, p);
        if (!al) return null;
        cost += al.cost;
        var at = Math.floor(al.rem / 2);
        row.forEach(function (fi, j) {
          var o = al.pick[j];
          var b = { fam: fi, row: ri, side: ri === 0 ? 1 : -1, index: plates.length, c0: at, cols: o.cols, band: o.band,
                    markCols: o.marks, rows: al.rows[j], lines: nameLines(fi, o.lines) };
          b.vx0 = colX(at) - p / 2 + g / 2;
          b.vx1 = colX(at + o.cols - 1) + p / 2 - g / 2;
          at += o.cols + al.per;
          var titleBlock = fEng + (b.lines.length - 1) * lineEng;
          b.depth = portrait ?
            Math.max(gm + p / 2 + (b.rows - 1) * p + mr + padY * 1.4, nameW(fi, 2) + 2 * padX + 2) :
            gm + p / 2 + (b.rows - 1) * p + mr + padY + titleBlock + padY * 1.15;
          b.depth = whole(b.depth);
          plates.push(b);
          rowPlates[ri].push(b);
        });
        // On a phone the plates either side of the line make two clean
        // columns: every plate in a row is as deep as the deepest.
        if (portrait) {
          var deepest = rowPlates[ri].reduce(function (t, b) { return Math.max(t, b.depth); }, 0);
          rowPlates[ri].forEach(function (b) { b.depth = deepest; });
        }
      }
      var railX0 = half(lx0), railX1 = half(lx0 + extent);
      var first = stepNames && nStep ? (portrait ? lineStep : stepLabels[0].tw) : 0;
      var last = stepNames && nStep ? (portrait ? lineStep : stepLabels[nStep - 1].tw) : 0;
      var sx0 = railX0 + Math.max(padX * 1.5, first / 2 + 3), sx1 = railX1 - Math.max(padX * 1.5, last / 2 + 3);
      var stations = model.steps.map(function (st, i) { return half(nStep > 1 ? sx0 + (sx1 - sx0) * i / (nStep - 1) : (railX0 + railX1) / 2); });

      // Connector room on a plate's line-side edge.
      function edgeLo(b, wd) { return b.vx0 + cham + 3 + wd / 2; }
      function edgeHi(b, wd) { return b.vx1 - cham - 3 - wd / 2; }
      var plateOf = []; plates.forEach(function (b) { plateOf[b.fam] = b; });
      var crossed = [], penalty = 0;
      var cables = model.cables.map(function (cb, k) {
        var A = plateOf[cb.fa], B = plateOf[cb.fb], n = cb.links.length;
        return { k: k, A: A, B: B, count: n, w: (n - 1) * pinQ, same: A.row === B.row };
      });
      // Cables across the line first, the busiest first: straight down where
      // the two plates overlap, else a single jog in one corridor.
      cables.filter(function (c) { return !c.same; }).sort(function (a, b) { return b.count - a.count || a.k - b.k; }).forEach(function (c) {
        var top = c.A.row === 0 ? c.A : c.B, bot = top === c.A ? c.B : c.A;
        c.top = top; c.bot = bot;
        var me = { top: top, bot: bot, w: c.w };
        var lo = Math.max(edgeLo(top, c.w), edgeLo(bot, c.w)), hi = Math.min(edgeHi(top, c.w), edgeHi(bot, c.w));
        var x = lo <= hi ? nearestFree((lo + hi) / 2, lo, hi, me, crossed, stations) : null;
        if (x !== null) { c.mode = 'straight'; c.x = x; c.xTop = x; c.xBot = x; }
        else {
          // The jog runs in the corridor of the plate the crossing misses;
          // only that plate's edge holds the crossing.
          var tc = (top.vx0 + top.vx1) / 2, bc = (bot.vx0 + bot.vx1) / 2;
          var meB = { top: null, bot: bot, w: c.w }, meT = { top: top, bot: null, w: c.w };
          var xb = nearestFree(clamp(tc, edgeLo(bot, c.w), edgeHi(bot, c.w)), edgeLo(bot, c.w), edgeHi(bot, c.w), meB, crossed, stations);
          var xt = nearestFree(clamp(bc, edgeLo(top, c.w), edgeHi(top, c.w)), edgeLo(top, c.w), edgeHi(top, c.w), meT, crossed, stations);
          if (xb !== null && (xt === null || Math.abs(xb - tc) <= Math.abs(xt - bc))) { c.mode = 'jogTop'; c.x = xb; c.xBot = xb; c.xTop = null; me = meB; }
          else if (xt !== null) { c.mode = 'jogBot'; c.x = xt; c.xTop = xt; c.xBot = null; me = meT; }
          else { c.mode = 'jogTop'; c.x = half(clamp(tc, edgeLo(bot, c.w), edgeHi(bot, c.w))); c.xBot = c.x; c.xTop = null; me = meB; penalty += 24; }
        }
        me.x = c.x;
        crossed.push(me);
      });
      // Each plate's edge holds its terminals and its tie to the line. The
      // crossings hold their places. The tie goes near the plate's middle,
      // on the lattice where it can be, clear of the names on its side, of
      // every crossing, and of the ties from the other side (two ties in
      // line would read as one line through), and only where every other
      // terminal still finds a place: each terminal then takes the free
      // place nearest the side of the plate it leads to, widest first,
      // keeping a gap to each neighbour. A rule that has to give way (last
      // first, only where an edge has no other choice) makes this pitch the
      // worse choice.
      var tieXs = [];
      plates.forEach(function (b) {
        var fixed = [], free = [];
        function put(c, x) { if (c.A === b) c.xa = half(x); else c.xb = half(x); }
        cables.forEach(function (c) {
          if (c.A !== b && c.B !== b) return;
          var other = c.A === b ? c.B : c.A;
          if (!c.same) {
            var mine = b === c.top ? c.xTop : c.xBot;
            if (mine !== null && mine !== undefined) {
              fixed.push([mine - c.w / 2 - sepC / 2, mine + c.w / 2 + sepC / 2]);
              put(c, mine);
              return;
            }
            free.push({ c: c, want: clamp(c.x, edgeLo(b, c.w), edgeHi(b, c.w)) });
          } else {
            free.push({ c: c, want: other.vx0 > b.vx0 ? edgeHi(b, c.w) : edgeLo(b, c.w) });
          }
        });
        free.sort(function (u, v) { return v.c.w - u.c.w || u.want - v.want || u.c.k - v.c.k; });
        // Places the free terminals around what is taken; null if one has no
        // place.
        function pack(taken0) {
          var taken = taken0.slice(), at = [];
          for (var f = 0; f < free.length; f++) {
            var it = free[f], hw = it.c.w / 2 + sepC / 2, lo = edgeLo(b, it.c.w), hi = Math.max(lo, edgeHi(b, it.c.w));
            var cands = [it.want], best = null;
            taken.forEach(function (iv) { cands.push(iv[0] - hw - 0.01, iv[1] + hw + 0.01); });
            cands.forEach(function (x) {
              x = clamp(x, lo, hi);
              for (var t = 0; t < taken.length; t++) if (x - hw < taken[t][1] && x + hw > taken[t][0]) return;
              if (best === null || Math.abs(x - it.want) < Math.abs(best - it.want)) best = x;
            });
            if (best === null) return null;
            taken.push([best - hw, best + hw]);
            at.push(best);
          }
          return at;
        }
        var mid = (b.vx0 + b.vx1) / 2, lo = b.vx0 + cham + 4, hi = b.vx1 - cham - 4, e = 1 / dpr;
        var lattice = [];
        for (var cc = b.c0; cc < b.c0 + b.cols; cc++) lattice.push(half(colX(cc) + p / 2), half(colX(cc)));
        // The places a tie may take at a level of strictness: on the
        // lattice first (a gutter or a column), nearest the middle, then the
        // free places nearest the middle, then a few more along each free
        // stretch.
        function candidates(strict) {
          var bad = fixed.map(function (iv) { return [iv[0] - sepC / 2, iv[1] + sepC / 2]; });
          if (strict >= 0) {
            stations.forEach(function (sx, st) {
              bad.push([sx - clearN * 2, sx + clearN * 2]);
              if (strict > 0 && stepNames && stepLabels[st].side === -b.side) {
                var hw = (portrait ? lineStep : stepLabels[st].tw) / 2 + clearN;
                bad.push([sx - hw, sx + hw]);
              }
            });
            crossed.forEach(function (o) { if (o.top !== b && o.bot !== b) bad.push([o.x - clearN * 2, o.x + clearN * 2]); });
            if (strict > 1) tieXs.forEach(function (o) { if (o.row !== b.row) bad.push([o.x - p * 0.75, o.x + p * 0.75]); });
          }
          var free = freeStretches(lo, hi, bad).filter(function (iv) { return iv[1] - iv[0] >= 2 * e; });
          function inside(x) { return free.some(function (iv) { return x > iv[0] && x < iv[1]; }); }
          var out = lattice.filter(inside).sort(function (u, v) { return Math.abs(u - mid) - Math.abs(v - mid) || u - v; });
          var more = [];
          free.forEach(function (iv) {
            var near = half(clamp(mid, iv[0] + e, iv[1] - e));
            more.push(near);
            for (var x = iv[0] + e; x <= iv[1] - e; x += Math.max(4, (iv[1] - iv[0]) / 8)) more.push(half(x));
          });
          more.sort(function (u, v) { return Math.abs(u - mid) - Math.abs(v - mid) || u - v; });
          return out.concat(more.filter(inside));
        }
        var tie = null, placedAt = null;
        for (var strict = 2; strict >= -1 && tie === null; strict--) {
          var cand = candidates(strict);
          for (var i = 0; i < cand.length; i++) {
            var res = pack(fixed.concat([[cand[i] - sepC / 2, cand[i] + sepC / 2]]));
            if (!res) continue;
            tie = cand[i];
            placedAt = res;
            penalty += strict === 2 ? 0 : strict === 1 ? 1 : strict === 0 ? 12 : 24;
            break;
          }
        }
        if (tie === null) {
          // No place holds everything: the tie keeps the middle and the
          // terminals take what is left.
          tie = lattice.length ? lattice.slice().sort(function (u, v) { return Math.abs(u - mid) - Math.abs(v - mid); })[0] : half(mid);
          placedAt = pack(fixed) || free.map(function (it) { return clamp(it.want, edgeLo(b, it.c.w), Math.max(edgeLo(b, it.c.w), edgeHi(b, it.c.w))); });
          penalty += 30;
        }
        free.forEach(function (it, k) { put(it.c, placedAt[k]); });
        b.bindX = tie;
        tieXs.push({ x: tie, row: b.row });
      });
      // Lanes: cables within a row run beside the plates, nested; the jogs of
      // cables across the line run beside it.
      var laneItems = [[[], []], [[], []]];   // [row][0 beside the plates, 1 beside the line]
      cables.forEach(function (c) {
        if (c.same) {
          c.lo = Math.min(c.xa, c.xb); c.hi = Math.max(c.xa, c.xb); c.key = 's' + c.k;
          laneItems[c.A.row][0].push(c);
        } else if (c.mode !== 'straight') {
          var xt = c.top === c.A ? c.xa : c.xb, xbt = c.bot === c.A ? c.xa : c.xb;
          c.lo = Math.min(xt, xbt); c.hi = Math.max(xt, xbt); c.key = 'c' + c.k;
          laneItems[c.mode === 'jogTop' ? 0 : 1][1].push(c);
        }
      });
      var laneCount = [0, 1].map(function (ri) {
        return [packLanes(laneItems[ri][0], 3), packLanes(laneItems[ri][1], 3)];
      });
      function corridor(ri) {
        var a = laneCount[ri][0], b = laneCount[ri][1];
        var hgt = 2 * laneMargin + Math.max(0, a - 1) * laneGap + Math.max(0, b - 1) * laneGap + (a && b ? laneGap * 2 : 0);
        return whole(Math.max(hgt, laneMargin * 2 + pinL));
      }
      var dTop = rowPlates[0].reduce(function (t, b) { return Math.max(t, b.depth); }, 0);
      var dBot = rowPlates[1].reduce(function (t, b) { return Math.max(t, b.depth); }, 0);
      var cTop = corridor(0), cBot = rowPlates[1].length ? corridor(1) : 0;
      return { p: p, N: N, cost: cost + penalty, colX: colX, plates: plates, rowPlates: rowPlates, cables: cables, stations: stations,
               railX0: railX0, railX1: railX1, laneCount: laneCount, dTop: dTop, dBot: dBot, cTop: cTop, cBot: cBot,
               need: dTop + cTop + 2 * halfBand + cBot + dBot };
    }

    // The pitch: every one that fits is weighed by how well its rows set
    // (fewer rows, names on one line, few empty places, an even rhythm)
    // against its size, in even numbers of device pixels so half a pitch is
    // whole too.
    var pMax = clamp(40 * s, 18, 58), pMin = Math.max(2 * mr + 7, 14), fit = null, p, tried = {}, weighed = [];
    for (p = pMax; p >= pMin; p -= 0.5) {
      var even = Math.max(2 / dpr, Math.floor(p * dpr / 2) * 2 / dpr);
      if (tried[even]) continue;
      tried[even] = true;
      var tr = trial(even);
      if (!tr) continue;
      tr.score = tr.cost - 0.75 * even;
      weighed.push({ p: even, cost: Math.round(tr.cost * 100) / 100, score: Math.round(tr.score * 100) / 100, fits: tr.need <= VH });
      if (tr.need > VH) continue;
      if (!fit || tr.score < fit.score - 1e-9) fit = tr;
    }
    geo.weighed = weighed;
    if (!fit) {
      if (legend) return layoutSchematic(model, w, h, measure, dpr, { noLegend: true });
      while (mr > 2.4 && !fit) {
        mr -= 0.25;
        var tr2 = trial(Math.max(2 / dpr, Math.floor((2 * mr + 6) * dpr / 2) * 2 / dpr));
        if (tr2) fit = tr2;
      }
      if (!fit) return geo;
      geo.cramped = true;
    }
    p = fit.p;
    var plates = fit.plates, colX = fit.colX;

    // Spare height opens the corridors (up to half of it), then centres the
    // drawing.
    var slack = Math.max(0, VH - fit.need);
    var open = Math.min(slack * 0.5, 2 * whole(clamp(22 * s, 10, 30)));
    var top0 = (slack - open) / 2;
    var inTop = half(top0 + fit.dTop);
    var cy = half(inTop + fit.cTop + open / 2 + halfBand);
    var inBot = half(cy + halfBand + fit.cBot + open / 2);
    var spineTop = cy - halfBand, spineBot = cy + halfBand;

    plates.forEach(function (b) {
      if (b.side > 0) { b.vyIn = inTop; b.vyOut = inTop - b.depth; } else { b.vyIn = inBot; b.vyOut = inBot + b.depth; }
      b.hdr = b.vyIn + b.side * pinL;
      b.edgeY = b.vyIn - b.side * gm;
    });

    /* The lattice places: rows from the line outward, left to right. */
    var slots = [];
    plates.forEach(function (b) {
      model.families[b.fam].members.forEach(function (ci, k) {
        var row = Math.floor(k / b.markCols), col = k % b.markCols;
        var vx = colX(b.c0 + b.band + col);
        var vy = half(b.vyIn - b.side * (gm + p / 2 + row * p));
        slots[ci] = { plate: b.index, row: row, col: col, vx: vx, vy: vy, gutter: vy + b.side * p / 2 };
      });
    });

    /* Lanes and cables. */
    function laneY(c) {
      var ri = c.same ? c.A.row : (c.mode === 'jogTop' ? 0 : 1), k = c.lane;
      var nearPlates = c.same;
      if (ri === 0) return half(nearPlates ? inTop + laneMargin + k * laneGap : spineTop - laneMargin - k * laneGap);
      return half(nearPlates ? inBot - laneMargin - k * laneGap : spineBot + laneMargin + k * laneGap);
    }
    var cableGeo = fit.cables.map(function (c) {
      var A = c.A, B = c.B, pts;
      if (c.same) {
        var ly = laneY(c);
        pts = [[c.xa, A.hdr], [c.xa, ly], [c.xb, ly], [c.xb, B.hdr]];
      } else if (c.mode === 'straight' && Math.abs(c.xa - c.xb) < 0.01) {
        pts = [[c.xa, A.hdr], [c.xb, B.hdr]];
      } else {
        // The jog: along the lane in one corridor, then straight across the
        // line at the crossing. (A straight cable whose connectors could not
        // both hold the crossing jogs beside the line.)
        var ly2 = c.mode === 'straight' ? half(spineTop - laneMargin) : laneY(c);
        pts = [[c.xa, A.hdr], [c.xa, ly2], [c.xb, ly2], [c.xb, B.hdr]];
      }
      return { k: c.k, A: A, B: B, count: c.count, w: c.w, xa: c.xa, xb: c.xb, pts: simplify(pts),
               mode: c.mode, lane: c.lane, crossX: c.same ? null : c.x };
    });
    // Every link of a cable has a pin at each end, set left to right by the
    // place of the component it serves, so the wiring inside never crosses
    // itself needlessly.
    var pinOf = [];
    cableGeo.forEach(function (cg, k) {
      var cb = model.cables[cg.k];
      [cg.A, cg.B].forEach(function (b, end) {
        var xc = end === 0 ? cg.xa : cg.xb;
        var order = cb.links.map(function (li) {
          var l = model.links[li], ci = model.comps[l[0]].fam === b.fam ? l[0] : l[1];
          return { li: li, x: slots[ci].vx, row: slots[ci].row, ci: ci };
        }).sort(function (u, v) { return u.x - v.x || u.row - v.row || u.li - v.li; });
        order.forEach(function (o, i) {
          var px = half(xc - cg.w / 2 + i * pinQ);
          (pinOf[o.li] = pinOf[o.li] || {})[b.fam] = { x: px, cable: k, end: end };
        });
      });
    });

    /* A component's way to its pin: down its own gutter toward the line,
       along a column gutter to the edge channel, along the channel to the
       pin, out through the edge, and along the connector's bar to the
       cable. */
    function toPin(ci, pin, xc) {
      var sl = slots[ci], b = plates[sl.plate], sd = b.side;
      var pts = [[sl.vx, sl.vy + sd * (mr + capGap)], [sl.vx, sl.gutter]];
      if (Math.abs(sl.gutter - b.edgeY) > 0.5) {
        var gx = pin.x >= sl.vx ? sl.vx + p / 2 : sl.vx - p / 2;
        if (gx > b.vx1 - 1) gx = sl.vx - p / 2;
        if (gx < b.vx0 + 1) gx = sl.vx + p / 2;
        pts.push([gx, sl.gutter], [gx, b.edgeY]);
      }
      pts.push([pin.x, b.edgeY], [pin.x, b.hdr], [xc, b.hdr]);
      return pts;
    }
    var routes = model.links.map(function (l, li) {
      var A = slots[l[0]], B = slots[l[1]], PA = plates[A.plate], PB = plates[B.plate], pts;
      if (A.plate === B.plate) {
        pts = [[A.vx, A.vy + PA.side * (mr + capGap)], [A.vx, A.gutter]];
        if (A.row !== B.row) {
          var xv = B.vx > A.vx ? B.vx - p / 2 : B.vx < A.vx ? B.vx + p / 2 : A.vx + p / 2;
          if (xv > PA.vx1 - 1 || xv < PA.vx0 + 1) xv = A.vx + (xv > A.vx ? -p / 2 : p / 2);
          pts.push([xv, A.gutter], [xv, B.gutter]);
        }
        pts.push([B.vx, B.gutter], [B.vx, B.vy + PB.side * (mr + capGap)]);
      } else {
        var pa = pinOf[li][PA.fam], pb = pinOf[li][PB.fam], cg = cableGeo[pa.cable];
        var mid = pa.end === 0 ? cg.pts : cg.pts.slice().reverse();
        var xca = pa.end === 0 ? cg.xa : cg.xb, xcb = pb.end === 0 ? cg.xa : cg.xb;
        pts = toPin(l[0], pa, xca).concat(mid).concat(toPin(l[1], pb, xcb).reverse());
      }
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
      var x0 = half(b.vx0), x1 = half(b.vx1), y0 = half(Math.min(b.vyIn, b.vyOut)), y1 = half(Math.max(b.vyIn, b.vyOut));
      var c0 = T(x0, y0), c1 = T(x1, y1);
      var rect = { x0: Math.min(c0[0], c1[0]), y0: Math.min(c0[1], c1[1]), x1: Math.max(c0[0], c1[0]), y1: Math.max(c0[1], c1[1]) };
      var from = T(b.bindX, b.vyIn), to = T(b.bindX, b.side > 0 ? cy - railH / 2 : cy + railH / 2);
      return { fam: b.fam, row: b.row, side: b.side, order: b.index, rect: rect, lines: b.lines,
               bind: { from: from, to: to }, rows: b.rows, cols: b.cols };
    });
    var cablesOut = cableGeo.map(function (cg) {
      var path = roundedPath(cg.pts.map(function (q) { return T(q[0], q[1]); }), rb);
      function conn(b, xc) {
        // The terminal: a bar one pin pitch long for every link the cable
        // carries, just clear of the plate's edge.
        var hw = Math.max(1.5, cg.w / 2 + 0.75);
        return { pins: cg.count, bar: [T(xc - hw, b.hdr), T(xc + hw, b.hdr)], at: T(xc, b.hdr), fam: b.fam };
      }
      return { fa: cg.A.fam, fb: cg.B.fam, count: cg.count, path: path, ends: [conn(cg.A, cg.xa), conn(cg.B, cg.xb)],
               crosses: !!cg.crossX || cg.crossX === 0 };
    });
    var railA = T(fit.railX0, cy - railH / 2), railB = T(fit.railX1, cy + railH / 2);
    var rail = { x0: Math.min(railA[0], railB[0]), y0: Math.min(railA[1], railB[1]),
                 x1: Math.max(railA[0], railB[0]), y1: Math.max(railA[1], railB[1]) };
    var stationGeo = fit.stations.map(function (vx, i) {
      var q = T(vx, cy);
      return { x: q[0], y: q[1], side: stepLabels[i] ? stepLabels[i].side : 1 };
    });

    /* Words: a family's name along its plate's outer edge (on a phone, at
       its head) with the count at the far end; step names beside their
       ticks; the key along the foot. */
    var labels = [];
    plateGeo.forEach(function (gp, gi) {
      var b = plates[gi], e = engr[b.fam];
      var x0 = gp.rect.x0 + padX, x1 = gp.rect.x1 - padX, lines = gp.lines, baseY, countLine;
      if (portrait || b.side > 0) { baseY = gp.rect.y0 + padY * 1.2 + fEng * asc; countLine = 0; }
      else { baseY = gp.rect.y1 - padY * 1.15 - fEng * desc - (lines.length - 1) * lineEng; countLine = lines.length - 1; }
      baseY = whole(baseY);
      var yc = baseY + countLine * lineEng;
      lines.forEach(function (text, li) {
        // Each line fits the room it has (beside the count on its line);
        // where a plate is too narrow the name is shortened, never overlapped.
        var room = x1 - x0 - (li === countLine ? e.cw + e.gapC : 0);
        text = fitWith(text, Math.max(12, room), fontEng, measure);
        var y = baseY + li * lineEng, tw = measure(text, fontEng);
        if (tw > room + 0.5 || text.length < 4) return;
        labels.push({ kind: 'family', fam: b.fam, text: text, font: fontEng, x: x0, y: y, align: 'left',
                      box: { x0: x0 - 2, x1: x0 + tw + 2, y0: y - fEng * asc - 1, y1: y + fEng * desc + 1 } });
      });
      labels.push({ kind: 'count', fam: b.fam, text: e.count, font: fontCount, x: x1, y: yc, align: 'right',
                    box: { x0: x1 - e.cw - 2, x1: x1 + 2, y0: yc - fEng * asc - 1, y1: yc + fEng * desc + 1 } });
    });
    if (stepNames) {
      stationGeo.forEach(function (st, i) {
        var l = stepLabels[i], x, y, align, off = railH / 2 + tickL + gapL;
        if (!portrait) {
          x = st.x; align = 'center';
          y = whole(l.side < 0 ? st.y - off - fStep * desc : st.y + off + fStep * asc);
        } else {
          y = whole(st.y + fStep * 0.32);
          if (l.side < 0) { x = st.x - off; align = 'right'; } else { x = st.x + off; align = 'left'; }
        }
        var bx0 = align === 'center' ? x - l.tw / 2 : align === 'right' ? x - l.tw : x;
        labels.push({ kind: 'step', step: i, text: l.text, font: fontStep, x: x, y: y, align: align,
                      box: { x0: bx0 - 1, x1: bx0 + l.tw + 1, y0: y - fStep * asc - 1, y1: y + fStep * desc + 1 } });
      });
    }
    // The key: its columns aligned, its left edge on the drawing's.
    var legendGeo = [], drawLeft = Infinity, drawRight = -Infinity;
    plateGeo.forEach(function (gp) { drawLeft = Math.min(drawLeft, gp.rect.x0); drawRight = Math.max(drawRight, gp.rect.x1); });
    drawLeft = Math.min(drawLeft, rail.x0); drawRight = Math.max(drawRight, rail.x1);
    if (legend) {
      var lx = clamp(drawLeft, m * 0.5, Math.max(m * 0.5, w - m * 0.5 - legend.width));
      legend.items.forEach(function (it, i) {
        var r = Math.floor(i / legend.cols), c = i % legend.cols, x = lx;
        for (var k = 0; k < c; k++) x += legend.colW[k] + legend.gap;
        var y = whole(h - m * 0.75 - (legend.rows - 1 - r) * lineLeg - fLeg * desc);
        var tx = x + it.glyph + it.gi, cx2 = tx + it.lw + it.gc;
        legendGeo.push({ cls: it.cls, x: x, y: y - fLeg * 0.33, w: it.glyph });
        labels.push({ kind: 'legend', text: it.label, font: fontLeg, x: tx, y: y, align: 'left',
                      box: { x0: x - 1, x1: tx + it.lw + 1, y0: y - fLeg * asc - 1, y1: y + fLeg * desc + 1 } });
        labels.push({ kind: 'legend-count', text: String(it.count), font: fontLeg, x: cx2, y: y, align: 'left',
                      box: { x0: cx2 - 1, x1: cx2 + it.cw + 1, y0: y - fLeg * asc - 1, y1: y + fLeg * desc + 1 } });
      });
    }

    geo.ok = true;
    geo.dpr = dpr;
    geo.half = half;
    geo.whole = whole;
    geo.portrait = portrait;
    geo.scale = s;
    geo.m = m;
    geo.padX = padX;
    geo.padY = padY;
    geo.marks = marks;
    geo.mr = mr;
    geo.pitch = p;
    geo.rb = rb;
    geo.capGap = capGap;
    geo.cham = cham;
    geo.plates = plateGeo;
    geo.routes = routes;
    geo.cables = cablesOut;
    geo.rail = rail;
    geo.stations = stationGeo;
    geo.stepNames = stepNames;
    geo.tickL = tickL;
    geo.railH = railH;
    geo.labelReach = railH / 2 + tickL + gapL;
    geo.labels = labels;
    geo.legend = legendGeo;
    geo.fieldH = Y1 + m * 0.5;
    geo.left = drawLeft;
    geo.right = drawRight;
    geo.explode = clamp(14 * s, 8, 18);
    geo.lanes = [fit.laneCount[0][0] + fit.laneCount[0][1], fit.laneCount[1][0] + fit.laneCount[1][1]];
    geo.depthStep = depthStep;
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
     nearest, each turned with the same bend radius as the cables. Wide
     canvases keep a column on the right for the card. */
  function layoutSheet(model, geo, f, measure) {
    var fam = model.families[f], n = fam.members.length, s = geo.scale;
    var wide = geo.w >= 520;
    var x0 = geo.half(geo.m), x1 = geo.w - geo.m;
    var head = geo.lineEng + geo.padY * 2.2;
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
    var crumbText = '‹ All families', sepText = ' / ';
    var crumbW = measure(crumbText, geo.fontCount), sepW = measure(sepText, geo.fontCount);
    if (wide) {
      // As wide as the longest name needs, between 42% and 60% of the canvas;
      // the rest is the card's.
      var longest = fam.members.reduce(function (t, ci) { return Math.max(t, measure(model.comps[ci].label, nameFont)); }, 0);
      longest = Math.max(longest, crumbW + sepW + measure(fam.title, geo.fontEng) + 24 - (nameX - x0));
      x1 = geo.half(clamp(nameX + longest + geo.padX + 2, geo.w * 0.42, geo.w * 0.6));
    }
    var y0 = geo.half(geo.m), top = y0 + head;
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
    var countText = String(n), cw = measure(countText, geo.fontCount);
    var y1 = geo.half(top + n * rowH + geo.padY);
    var ty = geo.whole(y0 + geo.padY * 1.3 + geo.fEng * 0.74);
    // The header is the trail: "‹ All families /" (a way back to the whole
    // drawing) and the family's name.
    var crumb = { text: crumbText, sep: sepText, x: x0 + geo.padX, w: crumbW + sepW, textW: crumbW,
                  box: { x0: x0 + geo.padX - 6, x1: x0 + geo.padX + crumbW + 4, y0: ty - geo.fEng - 6, y1: ty + geo.fEng * 0.5 + 6 } };
    return {
      fam: f, rect: { x0: x0, y0: y0, x1: x1, y1: y1 }, rows: rows, brackets: brackets, rowH: rowH,
      nameFont: nameFont, nameSize: nameSize, crumb: crumb, head: head,
      title: fitWith(fam.title, x1 - x0 - 2 * geo.padX - cw - 12 - crumb.w, geo.fontEng, measure),
      titleY: ty, count: countText,
      card: wide ? { x0: geo.half(x1 + clamp(12 * s, 8, 16)), x1: geo.w - geo.m * 0.6 } : null
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
    var band = stage.closest ? stage.closest('[data-atlas]') : null;
    var caption = stage.querySelector('.system-caption');
    var base = canvas.getAttribute('data-system-base') || '';
    var src = canvas.getAttribute('data-system-src');

    var model = null, geo = null, palette = {};
    var cssW = 0, cssH = 0, layoutDpr = 1;

    /* ---- State ------------------------------------------------------- */
    var hover = null;        // what the pointer is on: {kind: 'comp'|'family'|'step'|'crumb', i}
    var pin = null;          // the selection: {fam, comp} (comp -1 at the family level)
    var preview = -1;        // a family opened from the landing's list
    var rowHover = -1;       // the family row under the pointer, before its preview opens
    var keyComp = -1;        // a component reached with the arrow keys from a family row
    var listHover = -1;      // a component pointed at in the card's lists
    var rows = [], rowTimer = null, dwellTimer = null;
    var expanded = Object.create(null);   // the card lists opened in full, by component and side

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
        face: inkA('--s-face', 0.028, 0.04),
        side: inkA('--s-side', 0.07, 0.09),
        edge: inkA('--s-edge', 0.34, 0.34),
        rail: inkA('--s-rail', 0.5, 0.48),
        railEdge: inkA('--s-rail-edge', 0.62, 0.6),
        bind: inkA('--s-bind', 0.34, 0.36),
        trace: inkA('--s-trace', 0.1, 0.12),
        cable: inkA('--s-cable', 0.26, 0.28),
        pin: inkA('--s-pin', 0.38, 0.4),
        ghost: inkA('--s-ghost', 0.26, 0.28),
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
      // The caption below the drawing starts on the drawing's left edge.
      if (geo && geo.ok && stage.style && stage.style.setProperty) {
        stage.style.setProperty('--system-inset', Math.round(clamp(geo.left, 8, 28)) + 'px');
      }
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

    /* The opening, in milliseconds from its first frame, built over the
       blueprint: the line draws, the plates seat onto their outlines, the
       marks set, the ties and connectors come out, the cables route in
       along their lanes, and the names come up. */
    var OPEN_SPINE = [0, 420];
    var OPEN_PLATE = [90, 55, 470];          // start, per plate in reading order, duration
    var OPEN_MARK = [250, 55, 7, 230];       // start, per plate, per component, duration
    var OPEN_BIND = [520, 30, 260];
    var OPEN_CONN = [600, 30, 200];
    var OPEN_WORDS = [560, 360];
    var OPEN_CABLE = [700, 260, 360];        // start, spread across the cables, duration
    var OPEN_END = OPEN_CABLE[0] + OPEN_CABLE[1] + OPEN_CABLE[2];
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
    // A drawing that arrives without a move (a keyboard step, an address
    // that names it, reduced motion) is shown finished at once.
    function finishOpening() {
      if (opened && openState !== 'running') return;
      opened = true;
      motion.open = null;
      openState = 'done';
      paint();
    }

    /* A sheet opens over 420ms (the plate expands from its own rectangle,
       every mark travelling to its row) and closes over 340ms by the same
       path; one family's sheet gives way to another's by a 180ms cross-fade.
       A keyboard step, reduced motion or a hidden tab change at once. */
    var SHEET_OPEN = 420, SHEET_CLOSE = 340, SWAP_MS = 180;
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
    var FOCUS_IN = 180, FOCUS_HOLD = 140, FOCUS_OUT = 220, RETICLE_MS = 140, TRACE_MS = 420;
    var focusMix = 0, focusWas = null, focusHeld = null, snapFocus = false;
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
      if (hover && hover.kind !== 'crumb') return hover;
      if (keyComp >= 0) return { kind: 'comp', i: keyComp };
      if (rowHover >= 0) return { kind: 'family', i: rowHover };
      return null;
    }
    function trackFocus() {
      var f = currentFocus(), snap = snapFocus || !canAnimate();
      snapFocus = false;
      if (sameFocus(f, focusWas)) return f || focusHeld;
      if (snap) {
        // A keyboard step: the new focus is simply there.
        motion.focus = null;
        focusMix = f ? 1 : 0;
        focusHeld = null;
      } else if (f && !focusWas) {
        focusHeld = null;
        fadeFocus(1, FOCUS_IN * (1 - focusMix), 0);
      } else if (!f && focusWas) {
        focusHeld = focusWas;
        fadeFocus(0, FOCUS_OUT, FOCUS_HOLD);
      }
      motion.reticle = !snap && f && (f.kind === 'comp' || f.kind === 'step') ? { start: null, ms: 0 } : null;
      motion.trace = !snap && f && f.kind === 'comp' ? { start: null, ms: 0 } : null;
      wake();
      focusWas = f;
      return f || focusHeld;
    }
    function dimmed(base) { return 1 - (1 - base) * focusMix; }

    /* ---- Visibility -------------------------------------------------- */
    /* The opening starts once the drawing is well in view and still. While
       the landing's slider is carrying the system slide in (a start event
       for it without its end), it waits for the end, or 1.2 seconds; a
       slide that arrives at once is shown finished. Until then the drawing
       is its blueprint, painted once, even off screen, so the slide arrives
       carrying it. */
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
    function slideMoving() {
      if (!band || !band.querySelectorAll) return false;
      var shown = band.querySelectorAll('[data-atlas-slide].is-shown');
      return !!shown && shown.length > 1;
    }
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
      if (d.instant) {
        sliding = false;
        if (slideTimer) { clearTimeout(slideTimer); slideTimer = null; }
        if (model) finishOpening(); else arrivedAtOnce = true;
        return;
      }
      if (d.phase === 'start') {
        sliding = true;
        if (slideTimer) clearTimeout(slideTimer);
        slideTimer = setTimeout(function () { sliding = false; slideTimer = null; maybeOpen(); }, 1200);
      } else if (d.phase === 'end') {
        sliding = false;
        if (slideTimer) { clearTimeout(slideTimer); slideTimer = null; }
        maybeOpen();
      }
    });
    var arrivedAtOnce = !!(window.location && /^#system$/.test(window.location.hash || ''));
    if (slideMoving()) {
      // The script arrived while the slide was already moving.
      sliding = true;
      slideTimer = setTimeout(function () { sliding = false; slideTimer = null; maybeOpen(); }, 1200);
    }

    /* ---- Paint ------------------------------------------------------- */
    var hair = 0.5, placed = [];
    // Line widths in CSS pixels, never finer than one device pixel.
    function lw(px) { return Math.max(px, hair); }
    function paint() {
      if (document.hidden) { dirty = true; return; }
      dirty = false;
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      var w = canvas.clientWidth || 0, h = canvas.clientHeight || 0;
      if (w !== cssW || h !== cssH || dpr !== layoutDpr) relayout();
      var bw = Math.round(w * dpr), bh = Math.round(h * dpr);
      if (canvas.width !== bw || canvas.height !== bh) { canvas.width = bw; canvas.height = bh; }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      hair = 1 / dpr;
      placed = [];
      if (!geo || !geo.ok || openState === 'idle') return;
      if (openState === 'waiting') { drawBlueprint(1); announce(null); return; }
      var focus = trackFocus();
      var lit = litOf(focus);
      var sheet = sheetFam >= 0 && sheetMix > 0 ? sheetOf(sheetFam) : null;
      var back = sheet ? 1 - MOVE(unit(sheetMix * 1.15)) : 1;     // how present the overview is
      if (openState === 'running') drawBlueprint(1);
      var plate = back > 0.01 ? placePlate(focus, sheet) : null;
      if (back > 0.01) {
        drawBindings(lit, back);
        drawCables(lit, back);
        drawRail(lit, back);
        drawPlates(lit, back, sheet);
        drawConnectors(lit, back);
        drawLitRoutes(lit, back, sheet);
        drawMarks(lit, back, sheet);
        if (!sheet) drawCaps(lit, geo.routes, 1);
        drawWords(lit, back, sheet, plate);
      }
      drawLegend(lit);
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

    /* The blueprint: the line and the plates' outlines as construction
       lines, the lattice points faint, no words. It is the whole drawing
       before the opening and fades out under it as the parts arrive. */
    function drawBlueprint(alpha) {
      var r = geo.rail;
      ctx.lineWidth = hair;
      ctx.strokeStyle = palette.ghost;
      // The line's construction line stays only ahead of the line drawing
      // over it.
      var tr = openState === 'running' ? DETENT(phase(OPEN_SPINE[0], OPEN_SPINE[1])) : 0;
      ctx.globalAlpha = alpha;
      ctx.beginPath();
      if (tr < 1) {
        if (!geo.portrait) { ctx.moveTo(r.x0 + (r.x1 - r.x0) * tr, (r.y0 + r.y1) / 2); ctx.lineTo(r.x1, (r.y0 + r.y1) / 2); }
        else { ctx.moveTo((r.x0 + r.x1) / 2, r.y0 + (r.y1 - r.y0) * tr); ctx.lineTo((r.x0 + r.x1) / 2, r.y1); }
        ctx.stroke();
      }
      // Its stations, as short construction ticks.
      if (tr < 1) {
        ctx.beginPath();
        geo.stations.forEach(function (st) {
          var at = geo.portrait ? (st.y - r.y0) / (r.y1 - r.y0) : (st.x - r.x0) / (r.x1 - r.x0);
          if (at < tr) return;
          var reach = geo.railH / 2 + geo.tickL * 0.6;
          if (!geo.portrait) { ctx.moveTo(st.x, st.y - reach); ctx.lineTo(st.x, st.y + reach); }
          else { ctx.moveTo(st.x - reach, st.y); ctx.lineTo(st.x + reach, st.y); }
        });
        ctx.stroke();
      }
      if (ctx.setLineDash) ctx.setLineDash([3, 3]);
      ctx.lineJoin = 'miter';
      geo.plates.forEach(function (gp) {
        var t = openState === 'running' ? unit(phase(OPEN_PLATE[0] + OPEN_PLATE[1] * gp.order, OPEN_PLATE[2]) * 1.6) : 0;
        if (t >= 1) return;
        ctx.globalAlpha = alpha * (1 - t);
        polyPath(chamfered(gp.rect.x0, gp.rect.y0, gp.rect.x1, gp.rect.y1, geo.cham));
        ctx.stroke();
      });
      if (ctx.setLineDash) ctx.setLineDash([]);
      ctx.fillStyle = palette.ghost;
      model.comps.forEach(function (c, i) {
        var mk = geo.marks[i], g2 = geo.plates[mk.plate];
        var t = openState === 'running' ? phase(OPEN_MARK[0] + OPEN_MARK[1] * g2.order + OPEN_MARK[2] * c.slot, OPEN_MARK[3]) : 0;
        if (t >= 1) return;
        ctx.globalAlpha = alpha * (1 - t) * 1.6;
        ctx.beginPath();
        ctx.arc(mk.x, mk.y, Math.max(0.9, geo.mr * 0.22), 0, TAU);
        ctx.fill();
      });
      ctx.globalAlpha = 1;
    }

    // During the opening a plate stands off from its outline and seats in
    // two beats; its components and words go with it.
    function plateOffset(g2) {
      if (openState !== 'running') return [0, 0];
      var t = beats(phase(OPEN_PLATE[0] + OPEN_PLATE[1] * g2.order, OPEN_PLATE[2]));
      var d = -(1 - t) * geo.explode * g2.side;
      return geo.portrait ? [d, 0] : [0, d];
    }
    function plateAlpha(g2) { return DETENT(phase(OPEN_PLATE[0] + OPEN_PLATE[1] * g2.order, OPEN_PLATE[2] * 0.55)); }

    // The cables and lit routes pass under the line: nothing they draw
    // enters the line's own band.
    function clipOutLine() {
      var r = geo.rail, k = 1.5;
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, geo.w, geo.h);
      ctx.rect(r.x0 - 0.5, r.y0 - k, r.x1 - r.x0 + 1, r.y1 - r.y0 + 2 * k);
      ctx.clip('evenodd');
    }

    function drawRail(lit, back) {
      var r = geo.rail, t = DETENT(phase(OPEN_SPINE[0], OPEN_SPINE[1]));
      if (t <= 0) return;
      var horizontal = !geo.portrait;
      var len = horizontal ? r.x1 - r.x0 : r.y1 - r.y0;
      var x1 = horizontal ? r.x0 + len * t : r.x1, y1 = horizontal ? r.y1 : r.y0 + len * t;
      ctx.globalAlpha = back;
      // The line itself: two hairlines with a faint band between, closed by
      // a stop at each end.
      ctx.fillStyle = palette.side;
      ctx.fillRect(r.x0, r.y0, x1 - r.x0, y1 - r.y0);
      ctx.strokeStyle = palette.rail;
      ctx.lineWidth = hair;
      ctx.beginPath();
      if (horizontal) {
        ctx.moveTo(r.x0, r.y0); ctx.lineTo(x1, r.y0);
        ctx.moveTo(r.x0, r.y1); ctx.lineTo(x1, r.y1);
      } else {
        ctx.moveTo(r.x0, r.y0); ctx.lineTo(r.x0, y1);
        ctx.moveTo(r.x1, r.y0); ctx.lineTo(r.x1, y1);
      }
      ctx.stroke();
      var stop = geo.railH / 2 + geo.tickL * 0.75;
      ctx.lineWidth = lw(1);
      ctx.strokeStyle = palette.railEdge;
      ctx.beginPath();
      if (horizontal) {
        var my = (r.y0 + r.y1) / 2;
        ctx.moveTo(r.x0, my - stop); ctx.lineTo(r.x0, my + stop);
        if (t >= 1) { ctx.moveTo(r.x1, my - stop); ctx.lineTo(r.x1, my + stop); }
      } else {
        var mx = (r.x0 + r.x1) / 2;
        ctx.moveTo(mx - stop, r.y0); ctx.lineTo(mx + stop, r.y0);
        if (t >= 1) { ctx.moveTo(mx - stop, r.y1); ctx.lineTo(mx + stop, r.y1); }
      }
      ctx.stroke();
      // Station ticks: across the line, and on toward the step's name.
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
          ctx.moveTo(st.x, st.y - reach * (st.side < 0 ? 1 : 0.5));
          ctx.lineTo(st.x, st.y + reach * (st.side > 0 ? 1 : 0.5));
        } else {
          ctx.moveTo(st.x - reach * (st.side < 0 ? 1 : 0.5), st.y);
          ctx.lineTo(st.x + reach * (st.side > 0 ? 1 : 0.5), st.y);
        }
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    }

    // Each family's tie to the shared path: a dashed line from the plate's
    // edge to the line, ending in a joint on it.
    function drawBindings(lit, back) {
      geo.plates.forEach(function (gp) {
        var t = DETENT(phase(OPEN_BIND[0] + OPEN_BIND[1] * gp.order, OPEN_BIND[2]));
        if (t <= 0) return;
        var b = gp.bind, on = lit.fam === gp.fam && lit.focus && lit.focus.kind === 'family';
        var x = b.from[0] + (b.to[0] - b.from[0]) * t, y = b.from[1] + (b.to[1] - b.from[1]) * t;
        ctx.globalAlpha = back * (lit.comps && lit.fam !== gp.fam ? dimmed(0.45) : 1);
        ctx.strokeStyle = on ? palette.traceHot : palette.bind;
        ctx.lineWidth = lw(on ? 0.9 : 0.6);
        if (ctx.setLineDash) ctx.setLineDash([2, 2.5]);
        ctx.beginPath();
        ctx.moveTo(b.from[0], b.from[1]);
        ctx.lineTo(x, y);
        ctx.stroke();
        if (ctx.setLineDash) ctx.setLineDash([]);
        if (t >= 1) {
          ctx.fillStyle = on ? palette.traceHot : palette.railEdge;
          ctx.beginPath();
          ctx.arc(b.to[0], b.to[1], clamp(1.5 * geo.scale, 1.2, 2.2), 0, TAU);
          ctx.fill();
        }
      });
      ctx.globalAlpha = 1;
    }

    /* The cables: one hairline each, at rest a quiet texture. They route in
       during the opening from both of their connectors toward the middle. */
    function cableLit(cb, lit) {
      if (!lit.focus) return 0;
      if (lit.focus.kind === 'family') return cb.fa === lit.fam || cb.fb === lit.fam ? 1 : 0;
      return 0;
    }
    function drawCables(lit, back) {
      var list = geo.cables, n = list.length;
      if (!n) return;
      clipOutLine();
      ctx.lineCap = 'butt';
      ctx.lineJoin = 'round';
      ctx.lineWidth = hair;
      var quiet = lit.focus && lit.focus.kind !== 'step' ? dimmed(0.4) : 1;
      list.forEach(function (cb, i) {
        var t = MOVE(phase(OPEN_CABLE[0] + OPEN_CABLE[1] * (i / Math.max(1, n - 1)), OPEN_CABLE[2]));
        if (t <= 0) return;
        var on = cableLit(cb, lit);
        ctx.globalAlpha = back * (on ? Math.max(quiet, focusMix) : quiet);
        ctx.strokeStyle = on ? palette.traceHot : palette.cable;
        ctx.lineWidth = on ? lw(0.85) : hair;
        ctx.beginPath();
        if (t >= 1) tracePath(ctx, cb.path);
        else {
          var L = cb.path.length, part = L * t / 2;
          tracePath(ctx, cb.path, part, 0);
          tracePath(ctx, cb.path, part, L - part);
        }
        ctx.stroke();
      });
      ctx.restore();
      ctx.globalAlpha = 1;
    }
    // A connector: a terminal bar as long as the links its cable carries
    // (a pin pitch each), drawn out from its middle in the opening.
    function drawConnectors(lit, back) {
      ctx.lineCap = 'butt';
      geo.cables.forEach(function (cb) {
        var on = cableLit(cb, lit);
        cb.ends.forEach(function (end) {
          var gp = plateOf(end.fam), t = DETENT(phase(OPEN_CONN[0] + OPEN_CONN[1] * gp.order, OPEN_CONN[2]));
          if (t <= 0) return;
          var o = plateOffset(gp), a = end.bar[0], b = end.bar[1], mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2;
          ctx.globalAlpha = back * (lit.focus && lit.focus.kind !== 'step' && !on ? dimmed(0.45) : 1);
          ctx.strokeStyle = on ? palette.traceHot : palette.pin;
          ctx.lineWidth = lw(1.5);
          ctx.beginPath();
          ctx.moveTo(mx + (a[0] - mx) * t + o[0], my + (a[1] - my) * t + o[1]);
          ctx.lineTo(mx + (b[0] - mx) * t + o[0], my + (b[1] - my) * t + o[1]);
          ctx.stroke();
        });
      });
      ctx.globalAlpha = 1;
    }

    function plateRectNow(gp, sheet) {
      var r = gp.rect, o = plateOffset(gp);
      if (!sheet || sheet.fam !== gp.fam) return { x0: r.x0 + o[0], y0: r.y0 + o[1], x1: r.x1 + o[0], y1: r.y1 + o[1] };
      var t = MOVE(sheetMix), R = sheet.rect;
      return { x0: lerp(r.x0, R.x0, t), y0: lerp(r.y0, R.y0, t), x1: lerp(r.x1, R.x1, t), y1: lerp(r.y1, R.y1, t) };
    }
    function drawPlates(lit, back, sheet) {
      ctx.lineJoin = 'miter';
      geo.plates.forEach(function (gp) {
        if (sheet && sheet.fam === gp.fam) return;   // drawn forward, with the sheet
        var a = plateAlpha(gp);
        if (a <= 0) return;
        var R = plateRectNow(gp, null), poly = chamfered(R.x0, R.y0, R.x1, R.y1, geo.cham);
        var forward = lit.fam === gp.fam && lit.focus && lit.focus.kind === 'family';
        var fade = lit.comps && lit.fam !== gp.fam ? dimmed(0.55) : 1;
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

    // The routes in focus, drawn out of their cables: a component's links
    // out (heavier) and in, traced together in their declared direction; a
    // family's links inside it.
    function drawLitRoutes(lit, back, sheet) {
      var f = lit.focus;
      if (sheet || !f || f.kind === 'step' || openState !== 'done') return;
      clipOutLine();
      ctx.lineCap = 'butt';
      ctx.lineJoin = 'round';
      drawLit(geo.routes, f, back);
      ctx.restore();
    }
    function drawLit(routes, f, alpha) {
      var mt = motion.trace, grow = mt ? DETENT(unit(mt.ms / TRACE_MS)) : 1;
      var groups = f.kind === 'comp' ?
        [[function (r) { return r.a === f.i; }, lw(1.1), grow, 1], [function (r) { return r.b === f.i; }, lw(0.8), grow, 1]] :
        [[function (r) { return model.comps[r.a].fam === f.i && model.comps[r.b].fam === f.i; }, hair, 1, 0.42]];
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
      ctx.globalAlpha = 1;
    }
    // End caps on the routes in focus: a dot where a link leaves the
    // component that names the other, a bar where it reaches the one named.
    function drawCaps(lit, routes, alpha) {
      var f = lit.focus;
      if (!f || f.kind !== 'comp' || openState !== 'done') return;
      var mt = motion.trace, a = mt ? DETENT(unit((mt.ms - TRACE_MS * 0.7) / (TRACE_MS * 0.3))) : 1;
      if (a <= 0) return;
      var bar = clamp(3.2 * geo.scale, 2.5, 4.4);
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
      var mk = geo.marks[i], g2 = geo.plates[mk.plate], o = plateOffset(g2);
      if (sheet && sheet.fam === model.comps[i].fam) {
        var row = sheet.rows[model.comps[i].slot], t = MOVE(travelOf(sheet, model.comps[i].slot));
        return [lerp(mk.x + o[0], row.x, t), lerp(mk.y + o[1], row.y, t)];
      }
      return [mk.x + o[0], mk.y + o[1]];
    }
    /* In a sheet the marks leave their plate one after another, in reading
       order, each on a straight run to its row; closing runs the same
       schedule backward, so the last to arrive is the first to leave. */
    var TRAVEL = 0.46;
    function departOf(sheet, slot) {
      var n = sheet.rows.length;
      return 0.06 + 0.42 * (n > 1 ? slot / (n - 1) : 0);
    }
    function travelOf(sheet, slot) { return unit((sheetMix - departOf(sheet, slot)) / TRAVEL); }
    function drawMarks(lit, back, sheet) {
      var mr = geo.mr;
      model.comps.forEach(function (c, i) {
        var mk = geo.marks[i];
        if (!mk) return;
        if (sheet && sheet.fam === c.fam) return;   // drawn with the sheet
        var g2 = geo.plates[mk.plate];
        var t = phase(OPEN_MARK[0] + OPEN_MARK[1] * g2.order + OPEN_MARK[2] * c.slot, OPEN_MARK[3]);
        if (t <= 0) return;
        var e = DETENT(t), r = mr * (0.25 + 0.75 * e), at = markAt(i, null);
        var on = sheet ? false : (!lit.comps || lit.comps[i]);
        var mix = sheet ? 1 : focusMix;
        if (on) markShape(at[0], at[1], r, c.cls, colorOf(c), e * back);
        else {
          // Out of focus a mark greys: its own colour fades as the grey comes
          // up, so ember never turns into a muddy tint of itself.
          markShape(at[0], at[1], r, c.cls, colorOf(c), e * (1 - mix) * back);
          markShape(at[0], at[1], r, c.cls, palette.grey, e * mix * back);
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
      // Step names first, then the plates' names and counts.
      var order = geo.labels.filter(function (l) { return l.kind === 'step'; })
        .concat(geo.labels.filter(function (l) { return l.kind === 'family' || l.kind === 'count'; }));
      order.forEach(function (l) {
        var alpha = a * back, color = palette.text, o = [0, 0];
        if (l.kind === 'family' || l.kind === 'count') {
          var g2 = plateOf(l.fam);
          if (g2) o = plateOffset(g2);
          if (sheet && sheet.fam === l.fam) return;   // the sheet carries its own title
          if (lit.comps && lit.fam !== l.fam) alpha *= dimmed(0.45);
          if (lit.fam === l.fam) color = palette.ink;
          if (l.kind === 'count') color = lit.fam === l.fam ? palette.text : palette.faint;
        } else if (l.kind === 'step') {
          if (lit.step === l.step) color = palette.ink;
          else if (lit.comps && !sheet) alpha *= dimmed(0.6);
        }
        var box = { x0: l.box.x0 + o[0], x1: l.box.x1 + o[0], y0: l.box.y0 + o[1], y1: l.box.y1 + o[1] };
        for (var c = 0; c < cover.length; c++) if (boxesMeet(box, cover[c], 0)) return;
        if (!claim(box)) return;
        ctx.font = l.font;
        ctx.textAlign = l.align;
        ctx.fillStyle = color;
        ctx.globalAlpha = alpha;
        ctx.fillText(l.text, l.x + o[0], l.y + o[1]);
      });
      ctx.textAlign = 'left';
      ctx.globalAlpha = 1;
    }
    // The key stays at every level: the sheet's marks read by it too.
    function drawLegend(lit) {
      var a = DETENT(phase(OPEN_WORDS[0], OPEN_WORDS[1]));
      if (a <= 0) return;
      ctx.textBaseline = 'alphabetic';
      geo.labels.forEach(function (l) {
        if (l.kind !== 'legend' && l.kind !== 'legend-count') return;
        if (!claim(l.box)) return;
        ctx.font = l.font;
        ctx.textAlign = 'left';
        ctx.fillStyle = l.kind === 'legend' ? palette.text : palette.faint;
        ctx.globalAlpha = a;
        ctx.fillText(l.text, l.x, l.y);
      });
      geo.legend.forEach(function (g2) {
        if (g2.cls === 'link') {
          // A short route with its two caps: how a declared link reads.
          var y = g2.y, x0 = g2.x + 1.5, x1 = g2.x + g2.w - 1.5, bar = clamp(3.2 * geo.scale, 2.5, 4.4);
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
          markShape(g2.x + geo.mr + 1, g2.y, geo.mr, g2.cls, EMBER[g2.cls] ? palette.ember : palette.ink, a);
        }
      });
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
      // The plate comes forward: an opaque face a step above the receding
      // drawing, its side deeper than any plate at rest.
      ctx.globalAlpha = 1;
      polyPath(poly);
      ctx.fillStyle = palette.ground;
      ctx.fill();
      slab(poly, geo.depthStep * (1 + 0.6 * t), palette.face, palette.side);
      ctx.lineJoin = 'miter';
      ctx.lineWidth = lw(0.9);
      ctx.strokeStyle = palette.edge;
      polyPath(poly);
      ctx.stroke();
      // Its contents come up as it opens, row by row from the top; a family
      // giving way fades out.
      if (from && from !== sheet) drawSheetBody(from, lit, (1 - swapMix), 1, true);
      drawSheetBody(sheet, lit, from ? swapMix : 1, t, false);
    }
    // A row's name comes up as its mark arrives.
    function rowReveal(sheet, i) {
      return unit((travelOf(sheet, i) - 0.62) / 0.38);
    }
    function drawSheetBody(sheet, lit, alpha, travel, leaving) {
      var f = lit.focus, focusComp = f && f.kind === 'comp' && model.comps[f.i].fam === sheet.fam ? f.i : -1;
      var settle = leaving ? 1 : unit((sheetMix - 0.55) / 0.45);
      // The family's links inside it: the brackets, one stroke at rest, the
      // focused component's own traced out over them.
      if (alpha * settle > 0.002) {
        ctx.lineCap = 'butt';
        ctx.lineJoin = 'round';
        ctx.beginPath();
        sheet.brackets.forEach(function (r) { tracePath(ctx, r, r.length * (leaving ? 1 : MOVE(settle))); });
        ctx.globalAlpha = alpha * settle * (focusComp >= 0 ? dimmed(0.35) : 1);
        ctx.lineWidth = hair;
        ctx.strokeStyle = palette.trace;
        ctx.stroke();
        if (focusComp >= 0 && !leaving) {
          drawLit(sheet.brackets, { kind: 'comp', i: focusComp }, alpha * settle);
          drawCaps({ focus: { kind: 'comp', i: focusComp } }, sheet.brackets, alpha * settle);
        }
      }
      // The trail along the top, the count at the far end.
      var head = alpha * unit((sheetMix - 0.35) / 0.4);
      if (leaving) head = alpha;
      ctx.textBaseline = 'alphabetic';
      ctx.globalAlpha = head;
      ctx.textAlign = 'left';
      ctx.font = geo.fontCount;
      var crumbOn = hover && hover.kind === 'crumb';
      ctx.fillStyle = crumbOn ? palette.ink : palette.faint;
      ctx.fillText(sheet.crumb.text, sheet.crumb.x, sheet.titleY);
      if (crumbOn) {
        ctx.fillRect(sheet.crumb.x, sheet.titleY + 2, sheet.crumb.textW, hair);
      }
      ctx.fillStyle = palette.faint;
      ctx.fillText(sheet.crumb.sep, sheet.crumb.x + sheet.crumb.textW, sheet.titleY);
      ctx.font = geo.fontEng;
      ctx.fillStyle = palette.ink;
      ctx.fillText(sheet.title, sheet.crumb.x + sheet.crumb.w, sheet.titleY);
      ctx.textAlign = 'right';
      ctx.font = geo.fontCount;
      ctx.fillStyle = palette.faint;
      ctx.fillText(sheet.count, sheet.rect.x1 - geo.padX, sheet.titleY);
      ctx.textAlign = 'left';
      // A hairline under the trail, the width of the sheet.
      ctx.fillStyle = palette.edge;
      ctx.globalAlpha = head * 0.6;
      ctx.fillRect(sheet.rect.x0 + geo.padX, geo.half(sheet.rect.y0 + sheet.head - geo.padY * 0.6), sheet.rect.x1 - sheet.rect.x0 - 2 * geo.padX, hair);
      // Rows: the mark travels from its plate; the name comes up beside it.
      var lc = lit.comps;
      sheet.rows.forEach(function (row, i) {
        var c = model.comps[row.comp];
        var on = focusComp < 0 || (lc && lc[row.comp]);
        var at = leaving ? [row.x, row.y] : markAt(row.comp, sheet);
        var markAlpha = leaving ? alpha : 1;
        if (on) markShape(at[0], at[1], geo.mr, c.cls, colorOf(c), markAlpha);
        else {
          markShape(at[0], at[1], geo.mr, c.cls, colorOf(c), markAlpha * (1 - focusMix));
          markShape(at[0], at[1], geo.mr, c.cls, palette.grey, markAlpha * focusMix);
        }
        var reveal = leaving ? 1 : rowReveal(sheet, i);
        if (reveal <= 0) return;
        ctx.font = sheet.nameFont;
        ctx.fillStyle = row.comp === focusComp ? palette.ink : palette.text;
        ctx.globalAlpha = alpha * reveal * (on ? 1 : dimmed(0.4));
        ctx.fillText(row.text, row.nameX + (1 - reveal) * 6, row.y + sheet.nameSize * 0.34);
      });
      ctx.globalAlpha = 1;
    }

    /* ---- Focus marks ------------------------------------------------- */
    // The reticle: four corner ticks that close in on the focus from a third
    // larger, over 140ms, once per change of focus.
    function drawReticle(x, y, q) {
      var mo = motion.reticle, t = mo ? DETENT(unit(mo.ms / RETICLE_MS)) : 1;
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
    /* A name plate for the thing in focus on the overview (in a sheet the
       names are already written). A component's plate sits in the gutter
       between two rows of marks, where no mark can be, on the side away
       from its own links; a station's sits beside the line. Any word it
       would cover gives way while the reader points. */
    function placePlate(focus, sheet) {
      if (!focus || !geo || sheet) return null;
      var an = focusAnchor(focus, null);
      if (!an) return null;
      var title, sub = null;
      if (focus.kind === 'comp') title = model.comps[focus.i].label;
      else if (focus.kind === 'step') {
        title = model.steps[focus.i].title;
        sub = 'Step ' + (focus.i + 1) + ' of ' + model.steps.length + ' on the shared path';
      } else return null;
      var F = geo.fonts, pad = clamp(7 * geo.scale, 5, 9);
      var tw = measure(title, F.plate), sw = sub ? measure(sub, F.plateSub) : 0;
      var pw = Math.min(geo.w - 16, Math.max(tw, sw) + 2 * pad);
      var ph = F.plateSize * 1.25 + (sub ? F.plateSubSize * 1.3 : 0) + pad * 1.1;
      var lead = clamp(9 * geo.scale, 6, 12), run = clamp(8 * geo.scale, 5, 11);
      var cands = [];
      if (focus.kind === 'comp') {
        // In the gutter bands either side of the mark's row: away from the
        // line first (the component's own links leave toward it). Where the
        // lattice is too fine to hold a plate between two rows, there is no
        // plate: the reticle marks the component and the caption names it.
        var gp = geo.plates[geo.marks[focus.i].plate], away = geo.portrait ? -1 : -gp.side, p2 = geo.pitch;
        var maxH = p2 - 2 * geo.mr - 3;
        if (ph > maxH) { pad = Math.max(2, pad - (ph - maxH) / 1.1); ph = F.plateSize * 1.25 + pad * 1.1; }
        if (ph > maxH + 0.01) return null;
        [away, -away].forEach(function (dy, k) {
          var cyB = an.y + dy * p2 / 2;
          [1, -1].forEach(function (dx, j) {
            var kx = an.x + dx * (an.q + lead);
            var x0 = dx > 0 ? kx + run : kx - run - pw;
            cands.push({ box: { x0: x0, x1: x0 + pw, y0: cyB - ph / 2, y1: cyB + ph / 2 }, d: [dx, dy],
                         sx: an.x + dx * an.q, sy: an.y + dy * an.q, kx: kx, ky: cyB, pref: k * 0.4 + j * 0.1 });
          });
        });
      } else {
        // A station already carries its name beside the line; a plate is
        // drawn only where the names gave way, clear of the line on either
        // side, its leader running straight from the tick.
        if (geo.stepNames) return null;
        var reach = geo.railH / 2 + geo.tickL + 6;
        [-1, 1].forEach(function (sd, k) {
          var box;
          if (!geo.portrait) {
            var y0 = sd < 0 ? an.y - reach - ph : an.y + reach;
            box = { x0: an.x - pw / 2, x1: an.x + pw / 2, y0: y0, y1: y0 + ph };
            cands.push({ box: box, d: [1, sd], sx: an.x, sy: an.y + sd * (geo.railH / 2 + geo.tickL), kx: an.x,
                         ky: sd < 0 ? box.y1 : box.y0, pref: k * 0.1, straight: true });
          } else {
            var x0 = sd < 0 ? an.x - reach - pw : an.x + reach;
            box = { x0: x0, x1: x0 + pw, y0: an.y - ph / 2, y1: an.y + ph / 2 };
            cands.push({ box: box, d: [sd, 1], sx: an.x + sd * (geo.railH / 2 + geo.tickL), sy: an.y,
                         kx: sd < 0 ? box.x1 : box.x0, ky: an.y, pref: k * 0.1, straight: true });
          }
        });
      }
      // The focus's own routes, as straight runs, so the plate can keep off
      // them where it has the choice.
      var runs = [];
      if (focus.kind === 'comp') {
        geo.routes.forEach(function (r) {
          if (r.a !== focus.i && r.b !== focus.i) return;
          for (var k = 1; k < r.points.length; k++) runs.push([r.points[k - 1], r.points[k]]);
        });
      }
      function crosses(box, run) {
        var a = run[0], b = run[1];
        var x0 = Math.min(a[0], b[0]), x1 = Math.max(a[0], b[0]), y0 = Math.min(a[1], b[1]), y1 = Math.max(a[1], b[1]);
        return x1 >= box.x0 - 1 && x0 <= box.x1 + 1 && y1 >= box.y0 - 1 && y0 <= box.y1 + 1;
      }
      var best = null;
      cands.forEach(function (c) {
        var box = c.box, score = c.pref;
        if (box.x0 < 4 || box.x1 > geo.w - 4 || box.y0 < 4 || box.y1 > geo.fieldH - 2) score += 100;
        geo.labels.forEach(function (l) { if (boxesMeet(box, l.box, 1)) score += /legend/.test(l.kind) ? 60 : 4; });
        geo.marks.forEach(function (mk, i) {
          if (i === (focus.kind === 'comp' ? focus.i : -1)) return;
          if (mk.x + geo.mr > box.x0 - 2 && mk.x - geo.mr < box.x1 + 2 && mk.y + geo.mr > box.y0 - 1 && mk.y - geo.mr < box.y1 + 1) score += 40;
        });
        runs.forEach(function (run) { if (crosses(box, run)) score += 1.5; });
        // A station's plate stays in the corridor, off the plates.
        if (focus.kind === 'step') geo.plates.forEach(function (g3) { if (boxesMeet(box, g3.rect, 0)) score += 30; });
        if (!best || score < best.score) best = { score: score, c: c };
      });
      // A plate is never put over a mark or off the drawing.
      if (focus.kind === 'comp' && best.score >= 40) return null;
      var b2 = best.c, bx = b2.box;
      if (bx.x0 < 4) { bx.x1 += 4 - bx.x0; bx.x0 = 4; }
      if (bx.x1 > geo.w - 4) { bx.x0 -= bx.x1 - geo.w + 4; bx.x1 = geo.w - 4; }
      if (bx.y0 < 4) { bx.y1 += 4 - bx.y0; bx.y0 = 4; }
      return { box: bx, title: title, sub: sub, best: b2, pad: pad, anchor: an, ph: ph };
    }
    function drawFocus(focus, lit, sheet, plate) {
      if (!focus) return;
      var an = focusAnchor(focus, sheet);
      if (an) drawReticle(an.x, an.y, an.q);
      if (!plate) return;
      var b = plate.best, F = geo.fonts, t = motion.reticle ? DETENT(unit(motion.reticle.ms / RETICLE_MS)) : 1;
      ctx.globalAlpha = t;
      // The leader: a hairline elbow from the reticle's corner to the plate
      // (straight out from a station's tick).
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = lw(0.7);
      ctx.beginPath();
      ctx.moveTo(b.sx, b.sy);
      if (b.straight) ctx.lineTo(b.kx, b.ky);
      else {
        ctx.lineTo(b.sx, b.ky);
        ctx.lineTo(b.d[0] > 0 ? plate.box.x0 : plate.box.x1, b.ky);
      }
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
      var ty = plate.sub ? plate.box.y0 + plate.pad * 0.55 + F.plateSize * 0.98 :
        (plate.box.y0 + plate.box.y1) / 2 + F.plateSize * 0.34;
      ctx.fillText(fitWith(plate.title, plate.box.x1 - plate.box.x0 - 2 * plate.pad, F.plate, measure), plate.box.x0 + plate.pad, ty);
      if (plate.sub) {
        ctx.font = F.plateSub;
        ctx.fillStyle = palette.faint;
        ctx.fillText(plate.sub, plate.box.x0 + plate.pad, ty + F.plateSubSize * 1.3);
      }
      ctx.globalAlpha = 1;
    }

    /* ---- Words for the reader ---------------------------------------- */
    // "Verifier Lab Kernel (Formal math & proof) checks a contract."
    function whoWords(c, withFamily) {
      var who = c.label + (withFamily ? ' (' + model.families[c.fam].title + ')' : '');
      return c.cls ? who + ' ' + lowerFirst(CLASS_WORDS[c.cls]) + '.' : who + '.';
    }
    // "It names 10 components and 18 name it."
    function namesWords(c) {
      var o = c.out.length, n = c.inc.length;
      if (!o && !n) return 'It names no other component, and none names it.';
      var a = o ? 'It names ' + o + ' ' + plural(o, 'component', 'components') : 'It names no other component';
      var b = n ? (n === 1 ? 'one names it' : n + ' name it') : 'none names it';
      return a + (o ? ' and ' : ', and ') + b + '.';
    }
    function familyWords(f) {
      var n = f.members.length;
      return n + ' ' + plural(n, 'component', 'components') + ', with ' + f.within + ' ' +
        plural(f.within, 'link', 'links') + ' among them and ' + f.cross + ' to other families.';
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
        if (hc) text = whoWords(hc, false) + ' ' + namesWords(hc);
        else if (c) text = trail(['All families', F.title, c.label]) + '.';
        else text = trail(['All families', F.title]) + '. Select a component to see what it does.';
      } else if (focus && focus.kind === 'comp') {
        var cc = model.comps[focus.i];
        text = whoWords(cc, true) + ' ' + namesWords(cc);
      } else if (focus && focus.kind === 'family') {
        var ff = model.families[focus.i];
        text = ff.title + ': ' + ff.members.length + ' ' + plural(ff.members.length, 'component', 'components') + '. Select it to see their names.';
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
          if (now) snapFocus = true;
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
          else if (e.key === 'Escape' && keyComp >= 0) { keyComp = -1; snapFocus = true; draw(); e.stopPropagation(); return; }
          else return;
          e.preventDefault();
          keyComp = list[at];
          snapFocus = true;
          draw();
        });
      });
    }
    function openPreview(fam, now) {
      if (pin && pin.fam === fam) { preview = -1; syncSheet(now); renderCard(now); return; }
      preview = fam;
      syncSheet(now);
      renderCard(now);
    }

    /* ---- The card ---------------------------------------------------- */
    /* Beside an open sheet, a card in the column the sheet leaves free (on a
       narrow screen, the whole drawing): the family and its summary, or the
       selected component with what it does, what backs it, the components it
       names and those naming it (point at one to light it, select it to go
       there), and its pages. A family's card comes out from behind the
       sheet's edge; a component's opens out of its row; stepping back
       returns each the way it came. */
    var card = null, cardShows = null, cardToken = 0;
    // After a keyboard step the card that replaces the one in focus takes the
    // focus, so the reader's place is never lost to the page.
    var focusCard = false;
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
    function peerList(label, ids, key) {
      var p = el('p', 'system-card__peers');
      p.appendChild(el('span', 'system-card__peers-label', label + ' '));
      var full = !!expanded[key], shown = full || ids.length <= 5 ? ids : ids.slice(0, 4);
      shown.forEach(function (ci, k) {
        // A name in the sentence, inline so its comma stays with it, that
        // answers like a button: point at it to light it, select it to go.
        var b = el('span', 'system-card__peer', model.comps[ci].label);
        b.setAttribute('role', 'button');
        b.setAttribute('tabindex', '0');
        var choose = function (instant) {
          listHover = -1;
          if (instant) focusCard = true;
          pinTo({ fam: model.comps[ci].fam, comp: ci }, !!instant);
        };
        b.addEventListener('pointerenter', function () { listHover = ci; draw(); });
        b.addEventListener('pointerleave', function () { if (listHover === ci) { listHover = -1; draw(); } });
        b.addEventListener('focus', function () { listHover = ci; draw(); });
        b.addEventListener('blur', function () { if (listHover === ci) { listHover = -1; draw(); } });
        b.addEventListener('click', function () { choose(false); });
        b.addEventListener('keydown', function (e) {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(true); }
        });
        p.appendChild(b);
        var lastShown = k === shown.length - 1, more = shown.length < ids.length;
        if (!lastShown) p.appendChild(document.createTextNode(k === shown.length - 2 && !more ? ' and ' : ', '));
      });
      if (shown.length < ids.length) {
        // The rest of the list, one press away.
        p.appendChild(document.createTextNode(' and '));
        var more = el('button', 'system-card__more', (ids.length - shown.length) + ' more');
        more.setAttribute('type', 'button');
        more.setAttribute('aria-label', 'Show all ' + ids.length);
        more.addEventListener('click', function () {
          expanded[key] = true;
          renderCard(true);
          // Focus moves to the first name the press revealed.
          var list = card && card.querySelector ? card.querySelector('[data-peers="' + key + '"]') : null;
          var names = list && list.querySelectorAll ? list.querySelectorAll('.system-card__peer') : [];
          if (names[4] && names[4].focus) names[4].focus();
        });
        p.appendChild(more);
      }
      p.appendChild(document.createTextNode('.'));
      p.setAttribute('data-peers', key);
      return p;
    }
    function cardKind() {
      var fam = shownFamily();
      if (fam < 0) return null;
      var c0 = pin && preview < 0 && pin.fam === fam && pin.comp >= 0;
      return c0 ? 'comp:' + pin.comp : 'fam:' + fam;
    }
    function renderCard(instant) {
      if (!document.createElement || !stage.appendChild || !model) return;
      var fam = shownFamily(), kind = cardKind(), was = cardShows;
      if (fam < 0) { hideCard(instant, was); return; }
      var narrow = !(sheetOf(fam) || {}).card;
      var isComp = kind && kind.indexOf('comp:') === 0;
      // A narrow screen has no room beside the sheet: the family's sheet
      // stands alone, and a component's card takes the whole drawing (its
      // first line leads back), so nothing is ever half covered.
      if (narrow && !isComp) { hideCard(true, was); return; }
      if (!card) {
        card = el('div', 'system-card');
        card.setAttribute('role', 'group');
        card.setAttribute('tabindex', '-1');
        card.hidden = true;
        stage.appendChild(card);
      }
      var token = ++cardToken;
      var rebuild = function () {
        if (token !== cardToken) return;
        fill(fam);
        card.hidden = false;
        placeCard();
        cardShows = kind;
        if (focusCard) {
          focusCard = false;
          if (card.focus) { try { card.focus({ preventScroll: true }); } catch (e) { card.focus(); } }
        }
      };
      var swapping = was && kind && was.indexOf('fam:') === 0 && kind.indexOf('fam:') === 0;
      if (swapping) {
        // One family's card gives way to another's in place, as their sheets
        // cross-fade.
        rebuild();
        return;
      }
      if (was && was !== kind && !card.hidden && !instant && canAnimate() && card.animate) {
        // The card that was showing goes back the way it came, then the new
        // one arrives.
        var out = cardMotion(was, false);
        if (out) {
          var anim = card.animate(out.frames, { duration: 150, easing: 'cubic-bezier(0.65, 0, 0.35, 1)', fill: 'forwards' });
          anim.onfinish = function () {
            if (token !== cardToken) return;
            rebuild();
            try { anim.cancel(); } catch (e) {}
            arrive(kind, 0);
          };
          return;
        }
      }
      var fresh = !was || card.hidden;
      rebuild();
      if (was !== kind && !instant) arrive(kind, fresh && kind.indexOf('fam:') === 0 ? SHEET_OPEN * 0.55 : 0);
    }
    // How the card moves for what it shows: a family's card wipes out from
    // the sheet's edge; a component's opens out of its row's line.
    function cardMotion(kind, coming) {
      if (!card || !geo || !geo.ok || !kind) return null;
      var fam = shownFamily(), sheet = sheetOf(fam);
      if (!sheet || !sheet.card) return null;
      var full = 'inset(0px 0px 0px 0px)', from;
      if (kind.indexOf('comp:') === 0) {
        var ci = +kind.slice(5), row = model.comps[ci] ? sheet.rows[model.comps[ci].slot] : null;
        var hgt = card.offsetHeight || 200, top = parseFloat(card.style.top) || 0;
        var y = row ? clamp(row.y - top, 0, hgt) : 0;
        from = 'inset(' + Math.round(y) + 'px 0px ' + Math.round(Math.max(0, hgt - y - 1)) + 'px 0px)';
      } else {
        from = 'inset(0px 100% 0px 0px)';
      }
      var shift = kind.indexOf('fam:') === 0 ? 'translateX(-10px)' : 'translateX(-6px)';
      var a = { clipPath: from, opacity: 0.4, transform: shift }, b = { clipPath: full, opacity: 1, transform: 'none' };
      return { frames: coming ? [a, b] : [b, a] };
    }
    function arrive(kind, delay) {
      if (!card || !card.animate || !canAnimate()) return;
      var mo = cardMotion(kind, true);
      if (!mo) return;
      try {
        card.animate(mo.frames, { duration: kind.indexOf('fam:') === 0 ? 260 : 300, delay: delay || 0,
                                  easing: 'cubic-bezier(0.16, 1, 0.3, 1)', fill: 'backwards' });
      } catch (e) {}
    }
    function hideCard(instant, was) {
      if (!card || card.hidden) { cardShows = null; return; }
      var token = ++cardToken;
      cardShows = null;
      if (!instant && was && canAnimate() && card.animate) {
        var mo = cardMotion(was, false);
        if (mo) {
          var anim = card.animate(mo.frames, { duration: 160, easing: 'cubic-bezier(0.65, 0, 0.35, 1)', fill: 'forwards' });
          anim.onfinish = function () {
            if (token !== cardToken) return;
            card.hidden = true;
            try { anim.cancel(); } catch (e) {}
          };
          return;
        }
      }
      card.hidden = true;
    }
    function fill(fam) {
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
        // A press from the keyboard (a click with no pointer detail) lands at once.
        back.addEventListener('click', function (e) {
          var keyed = !!e && e.detail === 0;
          if (keyed) focusCard = true;
          pinTo({ fam: fam, comp: -1 }, keyed);
        });
        var trailP = el('p', 'system-card__trail');
        trailP.appendChild(back);
        card.appendChild(trailP);
        card.appendChild(el('p', 'system-card__title', title));
        var meta = ((c.cls ? CLASS_WORDS[c.cls] + '.' : '') + (c.basis ? ' Evidence: ' + lowerFirst(c.basis) + '.' : '')).trim();
        if (meta) card.appendChild(el('p', 'system-card__meta', meta));
        if (c.line) card.appendChild(el('p', 'system-card__line', c.line));
        // The ways out come before the lists, so they stay in view on a
        // short screen; the lists may run on below them.
        // Two ways out: the component's own page (which leads on to its paper
        // module), or the paper module where there is no page; and the full
        // architecture map, opened on this component.
        if (c.page) links.push(go(c.page, 'Component page', true));
        else if (c.reader) links.push(go(c.reader, 'Paper module', true));
        links.push(go(c.mapHref, 'Architecture map', !c.page && !c.reader));
        actions(links);
        var ci = pin.comp;
        if (c.out.length) card.appendChild(peerList('It names', c.out, ci + '-out'));
        if (c.inc.length) card.appendChild(peerList('Named by', c.inc, ci + '-in'));
        if (!c.out.length && !c.inc.length) card.appendChild(el('p', 'system-card__meta', 'It names no other component, and none names it.'));
        else card.appendChild(el('p', 'system-card__note', 'A declared link is not proof that one calls the other.'));
        links = null;
      } else {
        title = F.title;
        card.appendChild(el('p', 'system-card__title', title));
        card.appendChild(el('p', 'system-card__meta', familyWords(F)));
        if (F.summary) card.appendChild(el('p', 'system-card__line', F.summary));
        card.appendChild(el('p', 'system-card__note', 'Select a component to see what it does and what it names.'));
        if (F.page) links.push(go(F.page, 'Family page', true));
        links.push(go(F.mapHref, 'Architecture map', !F.page));
      }
      card.setAttribute('aria-label', title);
      if (links) actions(links);
    }
    function placeCard() {
      if (!card || card.hidden || !geo || !geo.ok || !card.style) return;
      var fam = shownFamily(), sheet = sheetOf(fam);
      if (!sheet) return;
      if (sheet.card) {
        if (card.classList) card.classList.remove('system-card--full');
        card.style.height = '';
        // The card stops where the drawing does, above the key.
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
      // A second click opens the page of what the first selected, even while
      // its sheet is still opening.
      if (event.detail >= 2) {
        var c2 = hit && hit.kind === 'comp' ? hit.i : (!hit && pin && pin.comp >= 0 ? pin.comp : -1);
        var f2 = hit && hit.kind === 'family' ? hit.i : (!hit && pin && pin.comp < 0 ? pin.fam : -1);
        var target = c2 >= 0 ? model.comps[c2].page || model.comps[c2].mapHref :
          f2 >= 0 ? model.families[f2].page || model.families[f2].mapHref : null;
        if (target) { window.location.href = target; return; }
      }
      // While a sheet opens or closes nothing on the canvas answers.
      if (!hit && sheetFam >= 0 && sheetMix < 1) return;
      if (!hit || hit.kind === 'outside') { stepBack(); return; }
      if (hit.kind === 'crumb') { preview = -1; pinTo(null, false); return; }
      if (hit.kind === 'comp') { pinTo({ fam: model.comps[hit.i].fam, comp: hit.i }, false); return; }
      if (hit.kind === 'family') { pinTo({ fam: hit.i, comp: -1 }, false); return; }
    });
    // Escape is a keyboard step, so it lands at once.
    document.addEventListener('keydown', function (event) {
      if (event.key !== 'Escape' || (!pin && preview < 0)) return;
      stepBack(true);
    });
    // One level up: a component to its family, a family to the overview.
    function stepBack(instant) {
      if (preview >= 0) { preview = -1; syncSheet(!!instant); renderCard(!!instant); draw(); return; }
      if (!pin) return;
      if (pin.comp >= 0) pinTo({ fam: pin.fam, comp: -1 }, !!instant);
      else pinTo(null, !!instant);
    }
    function pinTo(target, instant) {
      pin = target;
      listHover = -1;
      if (!fineQuery || !fineQuery.matches) hover = null;
      if (instant) snapFocus = true;
      syncSheet(instant);
      renderCard(instant);
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
          weighed: (geo.weighed || []).slice(),
          level: shownFamily() < 0 ? 'overview' : (pin && pin.comp >= 0 && preview < 0 ? 'component' : 'family'),
          moving: moving(),
          components: model.comps.map(function (c, i) {
            return { id: c.id, label: c.label, family: model.families[c.fam].id, cls: c.cls,
                     x: geo.marks[i].x, y: geo.marks[i].y };
          }),
          plates: geo.plates.map(function (g2) {
            return { id: model.families[g2.fam].id, title: model.families[g2.fam].title,
                     count: model.families[g2.fam].members.length, row: g2.row, rows: g2.rows, cols: g2.cols,
                     rect: { x0: g2.rect.x0, y0: g2.rect.y0, x1: g2.rect.x1, y1: g2.rect.y1 } };
          }),
          stations: geo.stations.map(function (st, i) { return { id: model.steps[i].id, title: model.steps[i].title, x: st.x, y: st.y }; }),
          rail: { x0: geo.rail.x0, y0: geo.rail.y0, x1: geo.rail.x1, y1: geo.rail.y1 },
          ties: geo.plates.map(function (g2) { return { row: g2.row, from: g2.bind.from.slice(), to: g2.bind.to.slice() }; }),
          cables: geo.cables.map(function (cb) {
            return { from: model.families[cb.fa].id, to: model.families[cb.fb].id, count: cb.count, crosses: cb.crosses,
                     points: cb.path.points.map(function (q) { return [q[0], q[1]]; }),
                     pins: cb.ends.map(function (e) { return e.pins; }),
                     terminals: cb.ends.map(function (e) {
                       return { family: model.families[e.fam].id, a: e.bar[0].slice(), b: e.bar[1].slice() };
                     }) };
          }),
          links: geo.routes.map(function (r) {
            return { source: model.comps[r.a].id, target: model.comps[r.b].id, length: r.length,
                     points: r.points.map(function (q) { return [q[0], q[1]]; }) };
          }),
          labels: geo.labels.map(function (l) { return { kind: l.kind, text: l.text, box: l.box }; }),
          drawn: placed.map(function (b) { return { x0: b.x0, y0: b.y0, x1: b.x1, y1: b.y1 }; }),
          focus: currentFocus(), hover: hover, pinned: pin, preview: preview >= 0 ? model.families[preview].id : null,
          sheet: sheetFam >= 0 && sheetMix > 0 ? (function (sh) {
            return { family: model.families[sh.fam].id, rect: sh.rect, card: sh.card, mix: sheetMix,
                     rows: sh.rows.map(function (r) { return { id: model.comps[r.comp].id, text: r.text, y: r.y, box: r.box }; }),
                     brackets: sh.brackets.length };
          })(sheetOf(sheetFam)) : null
        };
      }
    };
    window.PlectisSystemMap = api;

    readPalette();
    if (!src || typeof fetch !== 'function') return api;
    // The scene is asked for at once, so it is usually read before the slide
    // arrives; the blueprint is painted as soon as it is.
    fetch(src, { cache: 'no-cache' }).then(function (res) {
      if (res && res.ok === false) throw new Error('scene ' + res.status);
      return res.json();
    }).then(function (json) {
      model = readScene(json, base);
      json = null;
      if (!model || !model.comps.length) throw new Error('empty scene');
      relayout();
      wireRows();
      // A reader who cannot have motion, or a drawing that arrived without a
      // move, gets the finished drawing at once; otherwise it is a blueprint
      // until it is first in view and still.
      if (reduceMotion || !window.requestAnimationFrame || document.hidden || arrivedAtOnce) { opened = true; openState = 'done'; }
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
