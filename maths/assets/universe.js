/* Plectis — universe map renderer.
   Draws the Lean corpus graph on a canvas from a pre-computed layout file.
   No libraries, no physics: coordinates are decided at build time so the
   picture is identical on every visit and the first paint costs one fetch
   and one draw. The canvas is an enhancement — every object it shows is
   also in the HTML index on the universe page, so nothing is canvas-only.
   All colour comes from CSS custom properties, re-read on theme change.

   Interaction model (universe page): hover previews an object in the side
   inspector and lights its connections; click pins the full card there and
   dims everything the object does not touch; Esc or an empty click unpins.
   A pinned object is addressable as #o=<id>, so views can be shared. The
   landing teaser keeps a single caption line instead — no inspector, no
   cursor-chasing tooltip anywhere.

   Two things the picture encodes beyond position. A checked claim's glyph
   is its status from the record: a filled disc is proved, formalised or a
   verified finite instance; a half disc is unconditional progress; a ring
   is a conditional reduction; a faint ring is open or cited only. And every
   object placed with a problem — claim, review family, paper, argument step
   or Lean module — carries the reason it sits there (the record names it,
   its Lean namespace or folder, its statement, the step it builds on), which
   the inspector states and which the map uses to keep a problem's whole
   sector lit when the problem is focused. Module containment and imports
   appear as bounded local connections when an object is inspected; the
   universe itself stays an overview of the programmes. */
(function () {
  'use strict';

  var KIND_COLOR = {
    universe: '--u-universe',
    problem: '--u-problem',
    public_claim: '--u-claim',
    paper_statement: '--u-statement',
    paper: '--u-paper',
    human_document: '--u-document',
    integration_surface: '--u-integration',
    lean_module: '--u-module',
    mathematical_object: '--u-object'
  };
  /* Base radii before the degree bonus. The first screen is several hundred
     objects; the paper results are the densest band on it, and the two
     starfield kinds stay small because the complete universe adds over a
     thousand of them. */
  var KIND_RADIUS = {
    universe: 13,
    problem: 11,
    integration_surface: 9,
    paper: 7,
    human_document: 6,
    public_claim: 5.4,
    mathematical_object: 2.8,
    paper_statement: 2.6,
    lean_module: 2
  };
  var KIND_LABEL = {
    universe: 'universe',
    problem: 'problem',
    public_claim: 'checked claim',
    paper_statement: 'paper result',
    paper: 'paper',
    human_document: 'repository document',
    integration_surface: 'verification surface',
    lean_module: 'Lean module',
    mathematical_object: 'argument step'
  };
  var KIND_PLURAL = {
    universe: 'Universe',
    problem: 'Problems',
    public_claim: 'Checked claims',
    paper_statement: 'Paper results',
    paper: 'Papers',
    human_document: 'Repository documents',
    integration_surface: 'Verification surfaces',
    lean_module: 'Lean modules',
    mathematical_object: 'Argument steps'
  };
  var KIND_DOT = {
    universe: 'dot--universe',
    problem: 'dot--problem',
    public_claim: 'dot--claim',
    paper_statement: 'dot--statement',
    paper: 'dot--paper',
    human_document: 'dot--document',
    integration_surface: 'dot--integration',
    lean_module: 'dot--module',
    mathematical_object: 'dot--object'
  };
  var KIND_ORDER = ['universe', 'problem', 'integration_surface', 'paper',
    'human_document', 'public_claim', 'paper_statement',
    'mathematical_object', 'lean_module'];
  /* A paper result's evidence, from the coverage ledger, folded into four
     glyphs: replayed by Comparator (Comparator's colour, filled); exact Lean
     with the replay queued (Lean colour, filled); Lean modulo named inputs
     (ring); no Lean statement (faint ring). */
  var EVIDENCE_ORDER = ['replayed', 'lean', 'modulo', 'none'];
  var EVIDENCE_TEXT = {
    replayed: 'replayed by Comparator',
    lean: 'exact Lean, replay queued',
    modulo: 'Lean modulo named inputs',
    none: 'no Lean statement'
  };
  /* Card rows read "Lean: states it exactly", "Comparator: replayed". */
  var LEAN_STATUS_TEXT = {
    exact: 'states it exactly',
    exact_or_stronger: 'states it or something stronger',
    modulo_named_input: 'states it under named inputs',
    none: 'no statement recorded'
  };
  var COMPARATOR_STATUS_TEXT = {
    compared: 'replayed',
    pending: 'replay queued',
    not_applicable: 'nothing to replay without an exact Lean statement'
  };
  function evidenceOf(node) {
    var lean = node.lean_status || 'none';
    if (lean === 'exact' || lean === 'exact_or_stronger') {
      return node.comparator_status === 'compared' ? 'replayed' : 'lean';
    }
    return lean === 'modulo_named_input' ? 'modulo' : 'none';
  }
  /* Claim status, exactly as the record spells it, folded into four glyphs. */
  var STATUS_TIER = {
    'proved here': 'proved',
    'formalised here': 'proved',
    'verified finite instance': 'proved',
    'unconditional progress': 'progress',
    'conditional reduction': 'conditional',
    'open': 'open',
    'cited only': 'open'
  };
  var STATUS_ORDER = ['proved here', 'formalised here', 'verified finite instance',
    'unconditional progress', 'conditional reduction', 'open', 'cited only'];
  var SERIF = '"Iowan Old Style", Palatino, Georgia, serif';

  function cssColor(styles, name, fallback) {
    var v = styles.getPropertyValue(name).trim();
    return v || fallback;
  }

  function clip(text, max) {
    text = String(text);
    if (text.length <= max) return text;
    var cut = text.slice(0, max - 1);
    var space = cut.lastIndexOf(' ');
    if (space > max * 0.6) cut = cut.slice(0, space);
    return cut + '…';
  }

  function escapeHtml(text) {
    return String(text).replace(/[&<>"']/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
    });
  }

  function kindOrder(kind) {
    var at = KIND_ORDER.indexOf(kind);
    return at < 0 ? KIND_ORDER.length : at;
  }

  function statusOrder(status) {
    var at = STATUS_ORDER.indexOf(status);
    return at < 0 ? STATUS_ORDER.length : at;
  }

  function relText(rel) {
    return String(rel || 'linked').replace(/_/g, ' ');
  }

  function tierOf(node) {
    if (node.kind === 'paper_statement') return node.evidence || evidenceOf(node);
    if (node.kind !== 'public_claim') return null;
    return STATUS_TIER[node.status] || 'proved';
  }

  function mount(stage) {
    var canvas = stage.querySelector('canvas');
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext('2d');
    var pageMode = canvas.classList.contains('universe-canvas--page');
    var caption = stage.querySelector('.universe-caption');
    var inspector = document.querySelector('[data-universe-inspector]');
    var countOut = document.querySelector('[data-universe-count]');
    var searchIn = document.querySelector('[data-universe-search]');
    var loadFullBtn = document.querySelector('[data-universe-load-full]');
    var canCopy = !!(navigator.clipboard && window.isSecureContext);

    var nodes = [];
    var edges = [];
    var relations = [];
    var captions = [];
    var adj = [];
    var byId = {};
    var problemIndex = {};
    var view = { k: 1, tx: 0, ty: 0 };
    var fittedScale = 1;
    var viewIsFitted = true;
    var viewWidth = 0, viewHeight = 0;
    var hover = -1;
    var selected = -1;
    var query = '';
    var matchList = [];
    var lensOff = {};
    /* A key that starts switched off keeps its kind hidden until the reader
       turns it on. The teaser has no keys; it leaves out the documents shell,
       which belongs to the page's own index. */
    var lensKeys = document.querySelectorAll('[data-universe-lens]');
    if (pageMode && lensKeys.length) {
      Array.prototype.forEach.call(lensKeys, function (btn) {
        if (btn.getAttribute('aria-pressed') !== 'false') return;
        String(btn.getAttribute('data-universe-lens') || '').split(' ').forEach(function (kind) {
          if (kind) lensOff[kind] = true;
        });
      });
    } else if (!pageMode) {
      lensOff.human_document = true;
    }
    var tierOff = {};
    var palette = {};
    var fullLoaded = false;
    var fullLoading = false;
    var pendingId = null;
    var countText = '';
    var statementMeta = null;
    var bands = [];
    /* A statement card's Lean statements and Comparator checks arrive on
       first opening, from the experience API; the teaser never asks. */
    var detailUrl = canvas.getAttribute('data-universe-detail');
    var detail = null;
    var detailLoading = false;

    function readPalette() {
      var styles = getComputedStyle(document.documentElement);
      palette = { edge: cssColor(styles, '--u-edge', 'rgba(0,0,0,0.12)'),
                  plate: cssColor(styles, '--u-plate', 'rgba(127,127,127,0.07)'),
                  edgeHot: cssColor(styles, '--u-edge-hot', 'rgba(60,90,160,0.5)'),
                  halo: cssColor(styles, '--u-halo', 'rgba(226,168,62,0.35)'),
                  rim: cssColor(styles, '--u-rim', 'rgba(0,0,0,0.3)'),
                  ground: cssColor(styles, '--surface', '#fffdf7'),
                  ink: cssColor(styles, '--ink', '#211318'),
                  faint: cssColor(styles, '--faint', '#786359') };
      for (var kind in KIND_COLOR) {
        palette[kind] = cssColor(styles, KIND_COLOR[kind], '#888888');
      }
    }

    function normalizeSearchText(text) {
      // Friendly labels use spaces where source titles use typographic
      // dashes. Keep other punctuation (including qualified IDs) literal;
      // this is separator equivalence, not fuzzy spelling or word order.
      return text.toLowerCase().replace(/[-\u2010-\u2014]/g, ' ')
        .replace(/\s+/g, ' ').trim();
    }

    function visible(node) {
      if (lensOff[node.kind]) return false;
      return !(node.tier && tierOff[node.tier]);
    }
    function matches(node) {
      if (query.length < 2) return true;
      return node.search.indexOf(query) !== -1;
    }
    function countMatches() {
      matchList = [];
      if (query.length < 2) return;
      for (var i = 0; i < nodes.length; i++) {
        if (visible(nodes[i]) && matches(nodes[i])) matchList.push(i);
      }
      matchList.sort(function (p, q) {
        var a = nodes[p], b = nodes[q];
        var byKind = kindOrder(a.kind) - kindOrder(b.kind);
        if (byKind) return byKind;
        return a.label < b.label ? -1 : a.label > b.label ? 1 : 0;
      });
    }

    function fit() {
      if (!nodes.length) return;
      var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      // The view frames what is shown: a hidden kind does not shrink it.
      var framed = nodes.filter(visible);
      if (!framed.length) framed = nodes;
      for (var i = 0; i < framed.length; i++) {
        var n = framed[i];
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      }
      var w = canvas.clientWidth, h = canvas.clientHeight;
      var pad = 40;
      var k = Math.min((w - pad * 2) / Math.max(1, maxX - minX),
                       (h - pad * 2) / Math.max(1, maxY - minY));
      k = Math.max(0.001, k);
      fittedScale = k;
      viewIsFitted = true;
      viewWidth = w; viewHeight = h;
      view.k = k;
      view.tx = w / 2 - k * (minX + maxX) / 2;
      view.ty = h / 2 - k * (minY + maxY) / 2;
    }

    function centerOn(i) {
      if (i < 0 || !nodes[i]) return;
      // The core and the verification hubs reach across the whole ring, so
      // opening one frames the field rather than the hub.
      if (nodes[i].kind === 'universe' || nodes[i].kind === 'integration_surface') { fit(); draw(); return; }
      viewIsFitted = false;
      if (view.k < 1.1) view.k = 1.6;
      view.tx = canvas.clientWidth / 2 - nodes[i].x * view.k;
      view.ty = canvas.clientHeight / 2 - nodes[i].y * view.k;
      draw();
    }

    /* The focused object is the pinned one, or the hovered one while a
       pointer is down on the field. Everything it does not touch recedes:
       graph neighbours stay lit, and so does the sector an object was
       placed in — a problem keeps its claims, families and papers; a claim
       keeps its problem. */
    function focusIndex() {
      return hover >= 0 ? hover : selected;
    }
    function sectorProblems(node) {
      if (!node.sector) return [];
      return node.sector.split('+');
    }
    function neighbourSet(i) {
      var set = {};
      if (i < 0) return set;
      var rows = adj[i] || [];
      var j;
      var n = nodes[i];
      for (j = 0; j < rows.length; j++) {
        if (n.kind !== 'universe' || nodes[rows[j].to].kind === 'problem') set[rows[j].to] = true;
      }
      if (n.kind === 'problem' && n.sector) {
        for (j = 0; j < nodes.length; j++) {
          if (j !== i && nodes[j].sector && sectorProblems(nodes[j]).indexOf(n.sector) !== -1) set[j] = true;
        }
      } else if (n.sector) {
        var pids = sectorProblems(n);
        for (j = 0; j < pids.length; j++) {
          if (problemIndex[pids[j]] !== undefined) set[problemIndex[pids[j]]] = true;
        }
      }
      return set;
    }

    /* A claim's glyph is its status. Rings are filled with the paper colour
       so the edges beneath do not read as marks inside them. */
    function drawGlyph(x, y, r, color, tier) {
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      if (!tier || tier === 'proved' || tier === 'replayed' || tier === 'lean') {
        ctx.fillStyle = color;
        ctx.fill();
        if (r >= 3.4) {
          ctx.lineWidth = 1;
          ctx.strokeStyle = palette.rim;
          ctx.stroke();
        }
        return;
      }
      if (tier === 'progress') {
        ctx.fillStyle = palette.ground;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(x, y, r, Math.PI / 2, Math.PI * 1.5);
        ctx.closePath();
        ctx.fillStyle = color;
        ctx.fill();
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = color;
        ctx.stroke();
        return;
      }
      ctx.fillStyle = palette.ground;
      ctx.fill();
      ctx.lineWidth = tier === 'conditional' ? 1.7 : tier === 'modulo' ? 1.4 : 1;
      ctx.strokeStyle = color;
      ctx.stroke();
    }

    /* Comparator's colour marks what it replayed, so a reader sees the hub's
       reach across the statement band without a single spoke drawn. */
    function glyphColor(n) {
      if (n.tier === 'replayed') return palette.integration_surface;
      return palette[n.kind] || palette.faint;
    }

    /* Placement gives the overview its hierarchy. Imports and redundant
       hub spokes are explored locally; painting them all at once obscures
       the very objects they connect. The full adjacency stays inspectable. */
    function incidentEdges(focus) {
      if (focus < 0) return [];
      // A hub's reach is the lit band; two dozen spokes to arbitrary
      // members of it would misstate which results it reaches.
      if (nodes[focus] && nodes[focus].kind === 'integration_surface') return [];
      var rows = [];
      for (var i = 0; i < edges.length; i++) {
        var e = edges[i];
        if (e[0] !== focus && e[1] !== focus) continue;
        var other = e[0] === focus ? e[1] : e[0];
        if (!visible(nodes[focus]) || !visible(nodes[other])) continue;
        if (nodes[focus].kind === 'universe' && nodes[other].kind !== 'problem') continue;
        rows.push({ edge: i, other: other });
      }
      rows.sort(function (a, b) {
        return kindOrder(nodes[a.other].kind) - kindOrder(nodes[b.other].kind) ||
          nodes[a.other].label.localeCompare(nodes[b.other].label) || a.edge - b.edge;
      });
      return rows.slice(0, canvas.clientWidth < 600 ? 12 : 24).map(function (row) { return row.edge; });
    }

    function overviewEdge(i) {
      var a = nodes[edges[i][0]], b = nodes[edges[i][1]];
      if (a.kind === 'lean_module' || b.kind === 'lean_module') return false;
      // Hundreds of statement links would bury the band they lead to; they
      // light when an end is selected, and every one stays in its card.
      if (a.kind === 'paper_statement' || b.kind === 'paper_statement') return false;
      if (a.kind === 'universe' || b.kind === 'universe') {
        return a.kind === 'problem' || b.kind === 'problem';
      }
      return true;
    }

    function drawEdgeSet(indices, alpha, width, color) {
      ctx.lineWidth = width;
      ctx.strokeStyle = color;
      ctx.globalAlpha = alpha;
      ctx.beginPath();
      for (var j = 0; j < indices.length; j++) {
        var i = indices[j];
        var a = nodes[edges[i][0]], b = nodes[edges[i][1]];
        ctx.moveTo(a.x * view.k + view.tx, a.y * view.k + view.ty);
        ctx.lineTo(b.x * view.k + view.tx, b.y * view.k + view.ty);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    /* ---- Statement bands --------------------------------------------- */
    /* Each problem's results form one band. A faint plate gathers its dots,
       a thin gauge inside it shows the band's evidence in proportion, and a
       count outside it says how many results Comparator replayed. The band
       is drawn from the layout's own description of it, not guessed from the
       dots, so a filtered band keeps its shape. */
    var EVIDENCE_GAUGE_ALPHA = { replayed: 1, lean: 1, modulo: 0.5, none: 0.35 };
    function bandRadii(b) {
      var r0 = Infinity, r1 = -Infinity;
      for (var side in b.rings) {
        r0 = Math.min(r0, b.rings[side][0]);
        r1 = Math.max(r1, b.rings[side][1]);
      }
      return [r0, r1];
    }
    function bandState(b, focus) {
      if (focus < 0) return 'rest';
      var f = nodes[focus];
      if (f.kind === 'universe' || f.kind === 'integration_surface') return 'rest';
      if (f.sector && sectorProblems(f).indexOf(b.sector) !== -1) return 'on';
      return 'off';
    }
    function evidenceColor(key) {
      return key === 'replayed' ? palette.integration_surface :
        key === 'none' ? palette.faint : palette.paper_statement;
    }
    function drawBandPlates(focus) {
      if (!bands.length || lensOff.paper_statement) return;
      var k = view.k;
      for (var i = 0; i < bands.length; i++) {
        var b = bands[i], radii = bandRadii(b);
        if (!isFinite(radii[0])) continue;
        var state = bandState(b, focus);
        var pad = 6;
        ctx.globalAlpha = state === 'off' ? 0.35 : 1;
        ctx.fillStyle = state === 'on' ? palette.halo : palette.plate;
        ctx.beginPath();
        ctx.arc(view.tx, view.ty, (radii[1] + pad) * k, b.lo, b.hi);
        ctx.arc(view.tx, view.ty, Math.max(0, (radii[0] - pad) * k), b.hi, b.lo, true);
        ctx.closePath();
        ctx.fill();
        // The gauge: one thin arc just inside the band, split in proportion.
        var total = 0, key;
        for (key in b.evidence) total += b.evidence[key];
        var at = b.lo, gaugeR = (radii[0] - pad - 5) * k;
        if (total && gaugeR > 0) {
          ctx.lineWidth = Math.max(2, 3.2 * Math.min(1, k / 0.6));
          ctx.lineCap = 'butt';
          for (var j = 0; j < EVIDENCE_ORDER.length; j++) {
            key = EVIDENCE_ORDER[j];
            if (!b.evidence[key]) continue;
            var to = at + (b.hi - b.lo) * b.evidence[key] / total;
            ctx.globalAlpha = (state === 'off' ? 0.35 : 1) * EVIDENCE_GAUGE_ALPHA[key];
            ctx.strokeStyle = evidenceColor(key);
            ctx.beginPath();
            ctx.arc(view.tx, view.ty, gaugeR, at, to);
            ctx.stroke();
            at = to;
          }
        }
      }
      ctx.globalAlpha = 1;
    }
    function drawBandLabels(focus, w, h) {
      if (!bands.length || lensOff.paper_statement) return;
      if (!pageMode && w < 520) return;
      var k = view.k;
      ctx.lineJoin = 'round';
      for (var i = 0; i < bands.length; i++) {
        var b = bands[i], radii = bandRadii(b);
        if (!isFinite(radii[1])) continue;
        var state = bandState(b, focus);
        if (state === 'off') continue;
        var total = 0;
        for (var key in b.evidence) total += b.evidence[key];
        // Two lines set along the ring outside the band, the way a star chart
        // names a constellation: whose band it is, and how far it has been
        // checked. They take no width beside the field, so no edge pushes
        // them back over the dots. A narrow teaser keeps the count alone.
        var mid = (b.lo + b.hi) / 2;
        var lower = Math.sin(mid) > 0;
        var base = (radii[1] + 6) * k + 9;
        var count = { text: (b.evidence.replayed || 0) + ' of ' + total + ' replayed', font: '400 11px ' + SERIF, color: palette.faint, alpha: 1 };
        var title = null;
        if (b.title && (pageMode || w >= 640)) {
          title = { text: b.title, font: '600 12px ' + SERIF, color: palette.ink, alpha: state === 'on' ? 1 : 0.85 };
          ctx.font = title.font;
          // A name wider than its band and a half shrinks to the number.
          if (ctx.measureText(title.text).width / (base + 13) > (b.hi - b.lo) * 1.5) {
            title.text = title.text.split(' ')[0];
          }
        }
        // Reading downward: on the upper half the name sits outside the
        // count; on the lower half, inside it.
        var rows = title ? (lower ? [title, count] : [count, title]) : [count];
        for (var li = 0; li < rows.length; li++) {
          drawArcText(rows[li], base + li * 13, mid, lower);
        }
      }
      ctx.textBaseline = 'alphabetic';
      ctx.textAlign = 'center';
    }

    /* Upright text along a circle about the field's centre, centred on an
       angle. The upper half reads clockwise, the lower half anticlockwise,
       so neither runs upside down. */
    function drawArcText(row, radius, mid, lower) {
      ctx.font = row.font;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.lineWidth = 3.5;
      ctx.lineJoin = 'round';
      var dir = lower ? -1 : 1;
      var span = ctx.measureText(row.text).width / radius;
      var at = mid - dir * span / 2;
      for (var i = 0; i < row.text.length; i++) {
        var ch = row.text.charAt(i);
        var cw = ctx.measureText(ch).width;
        var angle = at + dir * (cw / 2) / radius;
        ctx.save();
        ctx.translate(view.tx + radius * Math.cos(angle), view.ty + radius * Math.sin(angle));
        ctx.rotate(angle + (lower ? -Math.PI / 2 : Math.PI / 2));
        ctx.globalAlpha = row.alpha;
        ctx.strokeStyle = palette.ground;
        ctx.strokeText(ch, 0, 0);
        ctx.fillStyle = row.color;
        ctx.fillText(ch, 0, 0);
        ctx.restore();
        at += dir * cw / radius;
      }
      ctx.globalAlpha = 1;
    }

    function draw() {
      var dpr = window.devicePixelRatio || 1;
      var w = canvas.clientWidth, h = canvas.clientHeight;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      var searching = query.length >= 2;
      var focus = focusIndex();
      var near = neighbourSet(focus);
      var i, n, x, y;
      /* A phone fits the whole field into a few hundred pixels; marks drawn
         at desktop size would then cover each other, so they shrink with the
         fitted scale and grow back as the reader zooms in. */
      var rs = radiusScale();

      drawBandPlates(focus);

      var hot = incidentEdges(focus), hotSet = {};
      hot.forEach(function (at) { hotSet[at] = true; });
      var quiet = [], availableEdges = 0;
      for (i = 0; i < edges.length; i++) {
        var ea = nodes[edges[i][0]], eb = nodes[edges[i][1]];
        if (!ea || !eb || !visible(ea) || !visible(eb)) continue;
        availableEdges++;
        if (overviewEdge(i) && !hotSet[i]) quiet.push(i);
      }
      var shownEdges = quiet.length + hot.length;
      drawEdgeSet(quiet, focus >= 0 ? 0.3 : 0.65, 0.65, palette.edge);
      drawEdgeSet(hot, 1, 1.25, palette.edgeHot);

      /* A shared sector must remain named in the fitted overview. Its
         compact callout sits beyond the claim band; the line identifies
         that band and is an annotation, not a new graph relationship. */
      ctx.textBaseline = 'middle';
      for (i = 0; i < captions.length; i++) {
        var c = captions[i];
        var cx = c.x * view.k + view.tx, cy = c.y * view.k + view.ty;
        if (cx < -160 || cy < -40 || cx > w + 160 || cy > h + 40) continue;
        if (view.k < 1.1) {
          var compactText = c.text.replace(/^shared by /, 'Shared: ');
          ctx.font = '600 10px ' + SERIF;
          var captionHalf = ctx.measureText(compactText).width / 2 + 6;
          // Leave the right-hand zoom controls their own column.
          var captionRight = Math.max(captionHalf, w - 74 - captionHalf);
          var calloutX = Math.max(captionHalf, Math.min(captionRight, c.x * view.k * 2.35 + view.tx));
          var calloutY = Math.max(14, Math.min(h - 14, c.y * view.k * 2.35 + view.ty));
          ctx.globalAlpha = 0.85;
          ctx.strokeStyle = palette.faint;
          ctx.lineWidth = 0.65;
          ctx.setLineDash([2, 3]);
          ctx.beginPath();
          ctx.moveTo(c.x * view.k * 1.8 + view.tx, c.y * view.k * 1.8 + view.ty);
          ctx.lineTo(calloutX, calloutY - 8);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.textAlign = 'center';
          ctx.lineWidth = 3.5;
          ctx.strokeStyle = palette.ground;
          ctx.strokeText(compactText, calloutX, calloutY);
          ctx.fillStyle = palette.ink;
          ctx.fillText(compactText, calloutX, calloutY);
          ctx.globalAlpha = 1;
          continue;
        }
        ctx.textAlign = c.x > 20 ? 'left' : c.x < -20 ? 'right' : 'center';
        ctx.globalAlpha = focus >= 0 ? 0.45 : 0.85;
        ctx.fillStyle = palette.faint;
        ctx.font = 'italic 600 11.5px ' + SERIF;
        ctx.fillText(c.text, cx, cy - (c.sub ? 7 : 0));
        if (c.sub) {
          ctx.font = 'italic 400 10.5px ' + SERIF;
          ctx.fillText(c.sub, cx, cy + 8);
        }
        ctx.globalAlpha = 1;
      }
      ctx.textBaseline = 'alphabetic';

      var shown = 0;
      for (i = 0; i < nodes.length; i++) {
        n = nodes[i];
        if (!visible(n)) continue;
        shown++;
        x = n.x * view.k + view.tx;
        y = n.y * view.k + view.ty;
        if (x < -24 || y < -24 || x > w + 24 || y > h + 24) continue;
        var r = n.r * rs;
        if (n.kind === 'lean_module' && i !== focus) {
          r = Math.min(r, Math.max(0.45, view.k * 1.5));
        }
        var alpha = 1;
        if (n.tier === 'open' || n.tier === 'none') alpha = 0.7;
        if (n.kind === 'lean_module' && i !== focus) alpha = 0.45;
        var anchor = n.kind === 'problem' || n.kind === 'universe' || n.kind === 'integration_surface';
        if (searching && !matches(n) && !anchor) alpha = 0.12;
        if (focus >= 0 && i !== focus && !near[i]) alpha = Math.min(alpha, 0.25);
        ctx.globalAlpha = alpha;
        if (i === hover || i === selected) {
          r = n.r * rs + 1.5;
          ctx.fillStyle = palette.halo;
          ctx.beginPath();
          ctx.arc(x, y, r + 7, 0, Math.PI * 2);
          ctx.fill();
        }
        drawGlyph(x, y, r, glyphColor(n), n.tier);
        ctx.globalAlpha = 1;
      }

      /* Labels: anchors always; middle kinds once zoomed in; anything under
         the pointer or pinned. Every canvas label is clipped — full names
         live in the inspector — and sits on a paper halo for legibility. */
      ctx.textAlign = 'center';
      ctx.lineJoin = 'round';
      for (i = 0; i < nodes.length; i++) {
        n = nodes[i];
        if (!visible(n)) continue;
        var isFocus = i === hover || i === selected;
        var wantLabel = isFocus || n.kind === 'problem' || n.kind === 'universe' ||
          n.kind === 'integration_surface' ||
          (view.k > 1.7 && (n.kind === 'paper' || n.kind === 'human_document')) ||
          (view.k > 3.4 && n.kind === 'public_claim');
        if (!wantLabel) continue;
        var isAnchor = n.kind === 'problem' || n.kind === 'universe' || n.kind === 'integration_surface';
        if (searching && !matches(n) && !isFocus && !isAnchor) continue;
        if (focus >= 0 && i !== focus && !near[i] && !isFocus && !isAnchor) continue;
        var lx = n.x * view.k + view.tx, ly = n.y * view.k + view.ty;
        if (lx < -60 || ly < -60 || lx > w + 60 || ly > h + 60) continue;
        var big = n.kind === 'problem' || n.kind === 'universe' || n.kind === 'integration_surface';
        ctx.font = (big ? '700 13px ' : '600 12px ') + SERIF;
        var text = clip(n.shortLabel, isFocus ? 60 : 42);
        if (n.kind === 'problem' && (w < 600 || view.k < 1.1)) {
          var number = n.id.match(/(?:^|[:_])(\d+)$/);
          if (number) text = '#' + number[1];
        }
        // A label near the edge slides inward so it is never cut off.
        var half = ctx.measureText(text).width / 2 + 6;
        var labelY = ly + n.r * rs + 15;
        if (n.kind === 'problem') {
          var distance = Math.sqrt(n.x * n.x + n.y * n.y) || 1;
          var offset = n.r * rs + 17;
          lx += n.x / distance * offset;
          labelY = ly + n.y / distance * offset + 4;
        }
        lx = Math.max(half, Math.min(w - half, lx));
        ctx.lineWidth = 3.5;
        ctx.strokeStyle = palette.ground;
        ctx.strokeText(text, lx, labelY);
        ctx.fillStyle = palette.ink;
        ctx.fillText(text, lx, labelY);
        // A quieter second line: a problem's name, a hub's reach. It waits
        // for room: a problem's name only once the field is wide enough.
        var wantSub = n.sub && !isFocus && w >= 420 &&
          (n.kind !== 'problem' || (w >= 600 && view.k >= 0.45));
        if (wantSub) {
          ctx.font = '400 11px ' + SERIF;
          var subText = clip(n.sub, 36);
          var subHalf = ctx.measureText(subText).width / 2 + 6;
          var sx = Math.max(subHalf, Math.min(w - subHalf, lx));
          ctx.strokeText(subText, sx, labelY + 13);
          ctx.fillStyle = palette.faint;
          ctx.fillText(subText, sx, labelY + 13);
        }
      }
      drawBandLabels(focus, w, h);

      if (countOut) {
        var line = fmtCount(shown) + ' objects, ' + fmtCount(shownEdges) + ' of ' +
          fmtCount(availableEdges) + ' connections drawn';
        if (searching) {
          line += ' · ' + String(matchList.length) + (matchList.length === 1 ? ' match' : ' matches');
        }
        if (line !== countText) {
          countText = line;
          countOut.textContent = line;
        }
      }
    }

    function radiusScale() {
      return Math.min(1, Math.max(0.5, view.k / 0.6));
    }

    function nodeAt(px, py) {
      var best = -1, bestD = 14 * 14;
      var rs = radiusScale();
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (!visible(n)) continue;
        var x = n.x * view.k + view.tx, y = n.y * view.k + view.ty;
        var d = (x - px) * (x - px) + (y - py) * (y - py);
        var reach = Math.max(9, n.r * rs + 6);
        if (d < Math.min(bestD, reach * reach)) { best = i; bestD = d; }
      }
      return best;
    }

    /* ---- Inspector (universe page) ---------------------------------- */

    function dotHtml(kind) {
      return '<span class="dot ' + (KIND_DOT[kind] || '') + '" aria-hidden="true"></span>';
    }
    function glyphHtml(tier) {
      return '<span class="glyph glyph--' + (tier || 'proved') + '" aria-hidden="true"></span>';
    }
    function problemChipHtml(pid) {
      var at = problemIndex[pid];
      if (at === undefined) return escapeHtml(pid);
      return '<button type="button" class="universe-sector__go" data-universe-go="' + at + '">' +
        escapeHtml(nodes[at].shortLabel) + '</button>';
    }

    function statusCensusHtml(filter) {
      var counts = {};
      var total = 0;
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n.kind !== 'public_claim' || !visible(n)) continue;
        if (filter && !filter(n)) continue;
        counts[n.status || 'unstated'] = (counts[n.status || 'unstated'] || 0) + 1;
        total++;
      }
      if (!total) return { html: '', total: 0 };
      var keys = Object.keys(counts).sort(function (a, b) { return statusOrder(a) - statusOrder(b); });
      var rows = '';
      for (var j = 0; j < keys.length; j++) {
        rows += '<li>' + glyphHtml(STATUS_TIER[keys[j]]) + '<span>' + escapeHtml(keys[j]) +
          '</span><b>' + counts[keys[j]] + '</b></li>';
      }
      return { html: '<ul class="universe-inspector__census universe-inspector__census--status">' + rows + '</ul>', total: total };
    }

    function overviewHtml() {
      var counts = {};
      for (var i = 0; i < nodes.length; i++) {
        if (!visible(nodes[i])) continue;
        counts[nodes[i].kind] = (counts[nodes[i].kind] || 0) + 1;
      }
      var rows = '';
      var shown = 0;
      for (var j = 0; j < KIND_ORDER.length; j++) {
        var kind = KIND_ORDER[j];
        if (!counts[kind]) continue;
        shown += counts[kind];
        rows += '<li>' + dotHtml(kind) + '<span>' + escapeHtml(KIND_PLURAL[kind] || kind) +
          '</span><b>' + counts[kind] + '</b></li>';
      }
      var status = statusCensusHtml(null);
      var evidence = evidenceCensusHtml(null);
      var parts = ['<p class="universe-inspector__kind">The universe</p>',
        '<h2 class="universe-inspector__title">' + shown + ' objects in view</h2>',
        '<ul class="universe-inspector__census">' + rows + '</ul>'];
      if (evidence.total) {
        parts.push('<h3 class="universe-inspector__sub">Paper results by evidence (' + evidence.total + ')</h3>');
        parts.push(evidence.html);
        var s = statementMeta && statementMeta.summary;
        if (s) {
          parts.push('<p class="universe-inspector__note">' + fmtCount(s.lean_declarations) +
            ' Lean declarations in ' + fmtCount(s.lean_files) + ' files state these results; Comparator replays run over ' +
            fmtCount(s.comparator_entries) + ' corpus entries. Source: the ' +
            (statementMeta.ledger ? '<a href="' + escapeHtml(statementMeta.ledger) + '" data-link-kind="exogenous" rel="external noopener" target="_blank">coverage ledger</a>' : 'coverage ledger') +
            '.</p>');
        }
      }
      if (status.total) {
        parts.push('<h3 class="universe-inspector__sub">Claims by status (' + status.total + ')</h3>');
        parts.push(status.html);
      }
      for (var c = 0; c < captions.length; c++) {
        parts.push('<p class="universe-inspector__note">The band on the field is ' +
          escapeHtml(captions[c].sub || '') + ', ' + escapeHtml(captions[c].text) + '.</p>');
      }
      parts.push('<p class="universe-inspector__hint">Select an object to inspect its connections. The overview shows programme and result relationships; module links appear around the selected object. All connections remain available in its card. Press Esc to unpin.</p>');
      return parts.join('');
    }

    function connectionRows(i) {
      var rows = (adj[i] || []).slice();
      rows.sort(function (p, q) {
        var a = nodes[p.to], b = nodes[q.to];
        var byKind = kindOrder(a.kind) - kindOrder(b.kind);
        if (byKind) return byKind;
        return a.label < b.label ? -1 : a.label > b.label ? 1 : 0;
      });
      var groups = {}, order = [];
      for (var j = 0; j < rows.length; j++) {
        var row = rows[j];
        var m = nodes[row.to];
        var key = m.kind + ':' + row.rel + ':' + row.out;
        if (!groups[key]) { groups[key] = { kind: m.kind, rel: row.rel, out: row.out, rows: [] }; order.push(key); }
        groups[key].rows.push('<li><button type="button" class="universe-goto" data-universe-go="' + row.to + '">' +
          dotHtml(m.kind) +
          '<span class="universe-goto__label">' + escapeHtml(clip(m.label, 68)) + '</span>' +
          '<span class="universe-goto__rel">' + (row.out ? '→ ' : '← ') +
          escapeHtml(relText(row.rel)) + '</span>' +
          '</button></li>');
      }
      var html = '';
      for (var g = 0; g < order.length; g++) {
        var group = groups[order[g]];
        html += '<details class="universe-connections"' + (group.kind === 'problem' || rows.length <= 12 ? ' open' : '') + '>' +
          '<summary>' + escapeHtml(KIND_PLURAL[group.kind] || group.kind) +
          ' · ' + (group.out ? '→ ' : '← ') + escapeHtml(relText(group.rel)) +
          ' <b>' + group.rows.length + '</b></summary>' +
          '<ul class="universe-inspector__list">' + group.rows.join('') + '</ul></details>';
      }
      return { html: html, total: rows.length };
    }

    /* What sits with a problem, by status, with the shared fan named. */
    function sectorSummaryHtml(i) {
      var n = nodes[i];
      if (n.kind !== 'problem' || !n.sector) return '';
      var pid = n.sector;
      var own = statusCensusHtml(function (m) { return m.sector === pid; });
      var results = evidenceCensusHtml(function (m) { return m.sector === pid; });
      var parts = [];
      if (results.total) {
        parts.push('<h3 class="universe-inspector__sub">Paper results (' + results.total + ')</h3>');
        parts.push(results.html);
      }
      if (own.total) {
        parts.push('<h3 class="universe-inspector__sub">Claims placed here (' + own.total + ')</h3>');
        parts.push(own.html);
      }
      var shared = {};
      for (var j = 0; j < nodes.length; j++) {
        var m = nodes[j];
        if (m.kind !== 'public_claim' || !visible(m) || !m.sector || m.sector.indexOf('+') === -1) continue;
        var pids = sectorProblems(m);
        if (pids.indexOf(pid) === -1) continue;
        for (var k = 0; k < pids.length; k++) {
          if (pids[k] !== pid) shared[pids[k]] = (shared[pids[k]] || 0) + 1;
        }
      }
      for (var other in shared) {
        parts.push('<p class="universe-inspector__note">' + shared[other] + ' more claims sit in the fan shared with ' +
          problemChipHtml(other) + ': their Lean modules live in a namespace the two problems share.</p>');
      }
      var kinds = {};
      for (var q = 0; q < nodes.length; q++) {
        var s = nodes[q];
        if (s.kind === 'public_claim' || s.kind === 'paper_statement' || s.kind === 'problem' ||
            !visible(s) || !s.sector) continue;
        if (sectorProblems(s).indexOf(pid) === -1) continue;
        kinds[s.kind] = (kinds[s.kind] || 0) + 1;
      }
      var rows = '';
      for (var t = 0; t < KIND_ORDER.length; t++) {
        if (!kinds[KIND_ORDER[t]]) continue;
        rows += '<li>' + dotHtml(KIND_ORDER[t]) + '<span>' + escapeHtml(KIND_PLURAL[KIND_ORDER[t]]) +
          '</span><b>' + kinds[KIND_ORDER[t]] + '</b></li>';
      }
      if (rows) {
        parts.push('<h3 class="universe-inspector__sub">Also placed here</h3>');
        parts.push('<ul class="universe-inspector__census">' + rows + '</ul>');
      }
      return parts.join('');
    }

    /* Where a click takes the reader: the result's own place in a rendered
       paper when one carries its label; otherwise the object's page on this
       site; otherwise the Lean declaration line on GitHub. */
    function primaryTarget(n) {
      if (n.paper) return { href: n.paper, external: false };
      if (n.page) return { href: n.page, external: false };
      if (n.lean && n.lean.length) return { href: n.lean[0].href, external: true };
      if (n.source_github) return { href: n.source_github, external: true };
      return null;
    }
    function openTarget(n) {
      var target = primaryTarget(n);
      if (!target) return;
      if (target.external) window.open(target.href, '_blank', 'noopener');
      else window.location.href = target.href;
    }
    function externalAttrs() {
      return '" data-link-kind="exogenous" rel="external noopener" target="_blank"';
    }
    function openHtml(i, pinned) {
      var n = nodes[i];
      var rows = [];
      if (n.paper) {
        rows.push('<a class="universe-open universe-open--primary" href="' + escapeHtml(n.paper) + '">' +
          '<span class="universe-open__verb">Read this result in the paper</span>' +
          '<span class="universe-open__where">' + escapeHtml(n.paperTitle || 'paper') +
          (n.paperLabel ? ' <code>' + escapeHtml(n.paperLabel) + '</code>' : '') + '</span></a>');
      }
      if (n.page) {
        rows.push('<a class="universe-open' + (n.paper ? '' : ' universe-open--primary') + '" href="' + escapeHtml(n.page) + '">' +
          '<span class="universe-open__verb">Open on this site</span></a>');
      }
      var lean = n.lean || [];
      var cap = pinned ? 6 : 1;
      for (var j = 0; j < lean.length && j < cap; j++) {
        var primary = !n.paper && !n.page && j === 0;
        rows.push('<a class="universe-open' + (primary ? ' universe-open--primary' : '') + '" href="' + escapeHtml(lean[j].href) + externalAttrs() + '>' +
          '<span class="universe-open__verb">' + (j === 0 ? 'Lean source on GitHub' : 'Also proved at') + '</span>' +
          '<span class="universe-open__where"><code>' + escapeHtml(lean[j].name) + '</code> · line ' + lean[j].line + '</span></a>');
      }
      if (lean.length > cap) {
        rows.push('<span class="universe-open__more">… and ' + (lean.length - cap) + ' more declarations' + (pinned ? '' : ' when pinned') + '</span>');
      }
      if (n.source_github && !lean.length) {
        rows.push('<a class="universe-open' + (n.paper || n.page ? '' : ' universe-open--primary') + '" href="' + escapeHtml(n.source_github) + externalAttrs() + '>' +
          '<span class="universe-open__verb">View source on GitHub</span></a>');
      }
      if (!rows.length) return '';
      return '<div class="universe-inspector__open">' + rows.join('') + '</div>';
    }

    function placementHtml(i) {
      var n = nodes[i];
      if (n.kind === 'problem' || !n.placedBy) return '';
      var pids = sectorProblems(n);
      if (!pids.length) {
        return '<p class="universe-inspector__note universe-sector">Placed by the core: ' + escapeHtml(n.placedBy) + '.</p>';
      }
      var chips = [];
      for (var j = 0; j < pids.length; j++) chips.push(problemChipHtml(pids[j]));
      return '<p class="universe-inspector__note universe-sector">Placed with ' + chips.join(' and ') +
        ': ' + escapeHtml(n.placedBy) + '.</p>';
    }

    /* ---- Paper results (coverage ledger) ---------------------------- */

    function evidenceCensusHtml(filter) {
      var counts = {}, total = 0;
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n.kind !== 'paper_statement' || !visible(n)) continue;
        if (filter && !filter(n)) continue;
        counts[n.tier] = (counts[n.tier] || 0) + 1;
        total++;
      }
      if (!total) return { html: '', total: 0 };
      var rows = '';
      for (var j = 0; j < EVIDENCE_ORDER.length; j++) {
        var key = EVIDENCE_ORDER[j];
        if (!counts[key]) continue;
        rows += '<li>' + glyphHtml(key) + '<span>' + escapeHtml(EVIDENCE_TEXT[key]) +
          '</span><b>' + counts[key] + '</b></li>';
      }
      return { html: '<ul class="universe-inspector__census universe-inspector__census--status">' + rows + '</ul>', total: total };
    }

    function fmtCount(value) {
      return value == null ? '' : Number(value).toLocaleString('en-GB');
    }

    function extLink(href, text, cls) {
      return '<a' + (cls ? ' class="' + cls + '"' : '') + ' href="' + escapeHtml(href) +
        '" data-link-kind="exogenous" rel="external noopener" target="_blank">' + text + '</a>';
    }

    /* The evidence notes are Markdown with inline maths; the card shows code
       as code and maths without its dollar signs. */
    function noteHtml(text) {
      var out = escapeHtml(String(text || ''));
      out = out.replace(/\$`([^`]*)`\$/g, '$1').replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\$([^$]+)\$/g, '$1').replace(/\*([^*]+)\*/g, '$1');
      return out;
    }

    function loadDetail() {
      if (!detailUrl || detail || detailLoading) return;
      detailLoading = true;
      fetch(detailUrl).then(function (r) { return r.json(); }).then(function (payload) {
        detail = payload;
        detailLoading = false;
        if (selected >= 0 || hover >= 0) renderInspector();
      }).catch(function () {
        detailLoading = false;
        detailUrl = null;
        if (selected >= 0) renderInspector();
      });
    }

    function statementHtml(n, pinned) {
      var parts = [];
      var where = n.paperTitle ? escapeHtml(n.paperTitle) : 'its paper';
      if (n.side === 'long') where += ', the long record';
      else if (n.side === 'short') where += ', the short paper';
      parts.push('<p class="universe-inspector__note">Asserted in ' + where + '.</p>');
      var facts = [];
      facts.push('<li><b>Lean</b> ' + escapeHtml(LEAN_STATUS_TEXT[n.lean_status] || n.lean_status || 'not recorded') + '</li>');
      var cmp = COMPARATOR_STATUS_TEXT[n.comparator_status] || n.comparator_status || 'not recorded';
      if (n.comparator_status === 'pending' && n.comparator_queued_at) cmp += ' since ' + n.comparator_queued_at;
      facts.push('<li><b>Comparator</b> ' + escapeHtml(cmp) + '</li>');
      var pal = n.palomar_status === 'prepared' ? 'in the prepare-only corpus' :
        n.palomar_status === 'pending' ? 'waits on the Comparator replay' : 'not applicable';
      facts.push('<li><b>Palomar</b> ' + escapeHtml(pal) + '</li>');
      parts.push('<ul class="universe-inspector__facts">' + facts.join('') + '</ul>');
      if (n.lean_reason) {
        parts.push('<p class="universe-inspector__boundary">' + noteHtml(n.lean_reason) + '</p>');
      }
      var more = pinned && detail && detail.statements ? detail.statements[n.id] || null : null;
      if (pinned && !detail && detailUrl) {
        loadDetail();
        parts.push('<p class="universe-inspector__hint">Loading the Lean statements and Comparator checks…</p>');
      }
      if (more && more.relation_note) {
        parts.push('<p class="universe-inspector__note"><b>How the Lean form gives the paper’s statement.</b> ' +
          noteHtml(more.relation_note) + '</p>');
      }
      var decls = n.decls || [];
      if (decls.length) {
        var cap = pinned ? 10 : 2;
        var sigs = more && more.statements ? more.statements : {};
        var rows = decls.slice(0, cap).map(function (d) {
          var where = d.line ? '<span class="universe-decl__line">line ' + d.line + '</span>' : '';
          var row = '<li>' + extLink(d.href, '<code>' + escapeHtml(d.name) + '</code>') + where;
          if (sigs[d.name]) {
            row += '<details class="universe-decl__sig"><summary>Lean statement</summary><pre><code>' +
              escapeHtml(sigs[d.name]) + '</code></pre></details>';
          }
          return row + '</li>';
        });
        if (decls.length > cap) {
          rows.push('<li class="universe-open__more">… and ' + (decls.length - cap) + ' more' + (pinned ? '' : ' when pinned') + '</li>');
        }
        parts.push('<h3 class="universe-inspector__sub">Lean declarations (' + decls.length + ')</h3>' +
          '<ul class="universe-inspector__list universe-inspector__list--decls">' + rows.join('') + '</ul>');
      }
      if (more && (more.named_inputs || []).length) {
        parts.push('<h3 class="universe-inspector__sub">Named inputs</h3><ul class="universe-inspector__list universe-inspector__list--decls">' +
          more.named_inputs.map(function (input) {
            return '<li>' + extLink(input.href, '<code>' + escapeHtml(input.name) + '</code>') +
              (input.text ? '<pre><code>' + escapeHtml(input.text) + '</code></pre>' : '') + '</li>';
          }).join('') + '</ul>');
      } else if ((n.named_inputs || []).length) {
        parts.push('<p class="universe-inspector__note">Named inputs: ' + n.named_inputs.map(function (name) {
          return '<code>' + escapeHtml(name) + '</code>';
        }).join(', ') + '</p>');
      }
      if (more && (more.checks || []).length) {
        var byEntry = {}, order = [];
        more.checks.forEach(function (check) {
          if (!byEntry[check.entry]) { byEntry[check.entry] = []; order.push(check.entry); }
          byEntry[check.entry].push(check);
        });
        var restated = more.checks.some(function (check) { return !check.same_as_lean; });
        var rowsCmp = order.map(function (entry) {
          var check = byEntry[entry][0], links = [];
          if (check.challenge) links.push(extLink(check.challenge, 'Challenge'));
          if (check.solution) links.push(extLink(check.solution, 'Solution'));
          if (check.receipt) links.push(extLink(check.receipt, 'receipt'));
          return '<li><code>' + escapeHtml(entry) + '</code>' +
            (links.length ? ' <span class="universe-decl__links">' + links.join(', ') + '</span>' : '') + '</li>';
        });
        var replay = detail.replay || {};
        parts.push('<h3 class="universe-inspector__sub">Comparator replay</h3>' +
          '<ul class="universe-inspector__list universe-inspector__list--decls">' + rowsCmp.join('') + '</ul>' +
          '<p class="universe-inspector__note">Each entry passed' +
          (replay.href ? ' in ' + extLink(replay.href, 'run ' + escapeHtml(replay.run_id)) : '') +
          ', with the Lean kernel and nanoda both accepting it.' +
          (restated ? ' Here the Challenge restates the Lean declaration in another form; the evidence record prints both.' : '') +
          '</p>');
      }
      if (more && more.record) {
        parts.push('<p class="universe-inspector__note">' + extLink(more.record, 'The evidence record for this result', 'source-link') + '</p>');
      } else if (pinned && n.tex && statementMeta && statementMeta.tex_source_base) {
        parts.push('<p class="universe-inspector__note">' +
          extLink(statementMeta.tex_source_base + n.tex, 'The statement in the paper’s TeX source', 'source-link') + '</p>');
      }
      return parts.join('');
    }

    /* What a verification hub reaches, from the same ledger the band draws. */
    function surfaceHtml(n) {
      var s = statementMeta && statementMeta.summary;
      if (!s) return '';
      var cmp = s.comparator || {}, pal = s.palomar || {};
      var repo = statementMeta.comparator_repository;
      if (n.id === 'integration:comparator') {
        var axioms = (s.permitted_axioms || []).map(function (a) { return '<code>' + escapeHtml(a) + '</code>'; });
        var runText = s.replay_href ? extLink(s.replay_href, 'run ' + escapeHtml(s.replay_run)) : 'one replay';
        return '<p class="universe-inspector__body">Comparator has checked ' + fmtCount(cmp.compared) +
          ' of the ' + fmtCount(s.statements) + ' paper results, in ' + runText + ' over ' +
          fmtCount(s.comparator_entries) + ' corpus entries' +
          (s.corpus_commit ? ' at commit <code>' + escapeHtml(String(s.corpus_commit).slice(0, 7)) + '</code>' : '') +
          '. For each entry a Challenge file restates the Lean statements with no proofs, and Comparator checks that the Solution proves exactly those statements' +
          (axioms.length ? ' using no axioms beyond ' + (axioms.length > 1 ?
            axioms.slice(0, -1).join(', ') + ' and ' + axioms[axioms.length - 1] : axioms[0]) : '') +
          ', with the Lean kernel and nanoda both accepting it.' +
          (cmp.pending ? ' ' + fmtCount(cmp.pending) + ' more exact Lean statements are queued for the next replay.' : '') +
          '</p>' +
          '<p class="universe-inspector__note">Selecting Comparator lights every result it reaches. ' +
          (s.receipts_href ? extLink(s.receipts_href, 'The receipts', 'source-link') + ' and the ' : 'The ') +
          (repo ? extLink(repo, 'Comparator corpus', 'source-link') : 'corpus') + ' are public.</p>';
      }
      if (n.id === 'integration:palomar') {
        return '<p class="universe-inspector__body">' + fmtCount(pal.prepared) +
          ' replayed paper results sit in a prepare-only Palomar corpus. Preparation is not submission, review, registration or acceptance.</p>';
      }
      if (n.kind === 'universe') {
        return '<p class="universe-inspector__body">' + fmtCount(s.lean_declarations) + ' Lean declarations in ' +
          fmtCount(s.lean_files) + ' files state ' + fmtCount(s.lean_exact) + ' of the ' + fmtCount(s.statements) +
          ' paper results exactly; ' + fmtCount((s.lean || {}).modulo_named_input || 0) +
          ' more are stated under named inputs.</p>';
      }
      return '';
    }

    function cardHtml(i, pinned) {
      var n = nodes[i];
      var head = '<p class="universe-inspector__kind">' + dotHtml(n.kind) +
        escapeHtml(KIND_LABEL[n.kind] || n.kind) + '</p>';
      if (pinned) {
        head = '<div class="universe-inspector__head">' + head +
          '<button type="button" class="universe-inspector__clear" data-universe-clear>Unpin</button></div>';
      }
      var parts = [head,
        '<h2 class="universe-inspector__title">' + escapeHtml(n.label) + '</h2>'];
      var chips = '';
      if (n.status) {
        chips += '<span class="universe-chip">' + (n.tier ? glyphHtml(n.tier) : '') + escapeHtml(n.status) + '</span>';
      }
      if (n.kind === 'paper_statement' && n.tier) {
        chips += '<span class="universe-chip">' + glyphHtml(n.tier) + escapeHtml(EVIDENCE_TEXT[n.tier] || n.tier) + '</span>';
      }
      if (n.disposition) chips += '<span class="universe-chip">' + escapeHtml(n.disposition) + '</span>';
      if (chips) parts.push('<p class="universe-inspector__meta">' + chips + '</p>');
      var body = n.statement || n.question || null;
      if (body) parts.push('<p class="universe-inspector__body">' + escapeHtml(body) + '</p>');
      if (n.boundary) {
        parts.push('<p class="universe-inspector__boundary">' + escapeHtml(n.boundary) + '</p>');
      }
      if (n.subject) {
        parts.push('<p class="universe-inspector__note">Subject: ' + escapeHtml(n.subject) + '</p>');
      }
      if (n.kind === 'paper_statement') parts.push(statementHtml(n, pinned));
      if (n.kind === 'integration_surface' || n.kind === 'universe') parts.push(surfaceHtml(n));
      if (n.declaration_count != null) {
        var counts = String(n.declaration_count) + ' declarations';
        if (n.theorem_count != null) counts += ', ' + String(n.theorem_count) + ' theorems';
        parts.push('<p class="universe-inspector__note">' + counts + '</p>');
      }
      parts.push(placementHtml(i));
      parts.push(openHtml(i, pinned));
      if (pinned) {
        parts.push(sectorSummaryHtml(i));
        var rows = connectionRows(i);
        if (rows.total) {
          parts.push('<h3 class="universe-inspector__sub">Connections (' + rows.total + ')</h3>');
          parts.push('<p class="universe-inspector__hint">The map highlights up to ' +
            (canvas.clientWidth < 600 ? 12 : 24) + ' local connections. Expand a group below to inspect every connection, including those outside the current filters.</p>');
          parts.push(rows.html);
        }
        if (canCopy) {
          parts.push('<button type="button" class="universe-inspector__copy" data-universe-copy>Copy link to this object</button>');
        }
      } else {
        parts.push('<p class="universe-inspector__hint">Click to pin this card and list its connections; click the pinned object again to open it.</p>');
      }
      return parts.join('');
    }

    function renderInspector() {
      if (!inspector) return;
      if (hover >= 0 && hover !== selected) {
        inspector.innerHTML = cardHtml(hover, false);
        inspector.classList.add('is-preview');
      } else if (selected >= 0) {
        inspector.innerHTML = cardHtml(selected, true);
        inspector.classList.remove('is-preview');
      } else {
        inspector.innerHTML = overviewHtml();
        inspector.classList.remove('is-preview');
      }
    }

    function updateHash() {
      if (!pageMode || !window.history || !window.history.replaceState) return;
      var base = window.location.pathname + window.location.search;
      if (selected >= 0 && nodes[selected]) {
        window.history.replaceState(null, '', base + '#o=' + encodeURIComponent(nodes[selected].id));
      } else if (window.location.hash.indexOf('#o=') === 0) {
        window.history.replaceState(null, '', base);
      }
    }

    function pin(i, center) {
      var restoreFocus = inspector && inspector.contains(document.activeElement);
      selected = i;
      hover = -1;
      canvas.classList.remove('is-over');
      if (i >= 0) pendingId = null;
      renderInspector();
      if (restoreFocus) {
        var nextFocus = inspector.querySelector('[data-universe-clear]') || searchIn;
        if (nextFocus) nextFocus.focus({ preventScroll: true });
      }
      updateHash();
      if (center && i >= 0) centerOn(i);
      draw();
    }

    function resolvePending() {
      if (!pendingId) return;
      if (byId[pendingId] !== undefined) {
        pin(byId[pendingId], true);
        return;
      }
      // A shared link to a full-corpus object must open its card on first visit.
      if (!fullLoaded) loadFull();
    }

    /* ---- Caption (landing teaser) ------------------------------------ */

    function showCaption(i) {
      if (!caption) return;
      if (i < 0) {
        caption.classList.remove('is-shown');
        return;
      }
      var n = nodes[i];
      var text = (KIND_LABEL[n.kind] || n.kind) + ': ' + clip(n.label, 96);
      if (n.kind === 'paper_statement' && EVIDENCE_TEXT[n.tier]) text += ' · ' + EVIDENCE_TEXT[n.tier];
      caption.textContent = text;
      caption.classList.add('is-shown');
    }

    /* ---- Data --------------------------------------------------------- */

    function degreeBonus(kind, degree) {
      var cap = (kind === 'lean_module' || kind === 'mathematical_object') ? 1 : 3.5;
      return Math.min(cap, Math.sqrt(Math.max(0, degree - 1)) * 0.55);
    }

    /* The first screen names a declaration's file by index into one table;
       the complete graph spells each one out. Both become {name, href}. */
    function declarationsOf(n) {
      if (n.decls && statementMeta) {
        return n.decls.map(function (d) {
          var file = statementMeta.lean_files[d[1]] || '';
          return { name: d[0], line: d[2] || null,
                   href: statementMeta.lean_source_base + file + (d[2] ? '#L' + d[2] : '') };
        });
      }
      return (n.declarations || []).map(function (d) {
        return { name: d.name, href: d.href, line: d.line || null };
      });
    }

    function ingest(data) {
      var keepId = selected >= 0 && nodes[selected] ? nodes[selected].id : null;
      var keepView = nodes.length > 0;
      if (data.statements) statementMeta = data.statements;
      if (data.bands) bands = data.bands;
      nodes = data.nodes.map(function (n) {
        var row = {
          id: n.id, kind: n.kind, label: n.label,
          shortLabel: n.short || n.label,
          status: n.status || null, statement: n.statement || null,
          boundary: n.boundary || null, disposition: n.disposition || null,
          question: n.question || null, subject: n.subject || null,
          declaration_count: n.declaration_count != null ? n.declaration_count : null,
          theorem_count: n.theorem_count != null ? n.theorem_count : null,
          page: n.page || null, source_github: n.source_github || null,
          sector: n.sector || null, placedBy: n.placed_by || null,
          paper: n.paper || null, paperTitle: n.paper_title || null,
          paperLabel: n.paper_label || null, lean: n.lean || [],
          sub: n.sub || null,
          x: n.x, y: n.y, r: KIND_RADIUS[n.kind] || 2
        };
        if (n.kind === 'paper_statement') {
          /* The id is statement:<paper id>#<label>; the first screen leaves
             what the id, the tables and the sector already say unsaid. */
          var hash = n.id.indexOf('#');
          row.paperId = n.id.slice('statement:'.length, hash);
          row.paperLabel = row.paperLabel || n.id.slice(hash + 1);
          row.side = n.side || null;
          row.lean_status = n.lean_status || null;
          row.comparator_status = n.comparator_status || null;
          row.palomar_status = n.palomar_status || null;
          row.lean_reason = n.lean_reason || null;
          row.comparator_queued_at = n.comparator_queued_at || null;
          row.named_inputs = n.named_inputs || [];
          row.comparator_entries = n.comparator_entries ||
            (n.cmp_entries || []).map(function (k) { return statementMeta ? statementMeta.comparator_entries[k] : String(k); });
          row.comparator_runs = n.comparator_runs ||
            (n.cmp_runs || []).map(function (k) { return statementMeta ? statementMeta.comparator_runs[k] : String(k); });
          row.decls = declarationsOf(n);
          row.tex = n.tex || (n.line && statementMeta && statementMeta.tex_paths[row.paperId] ?
            statementMeta.tex_paths[row.paperId] + '#L' + n.line : null);
        }
        row.tier = tierOf(row);
        row.search = normalizeSearchText([row.label, row.id, row.status || '', row.disposition || '',
          row.subject || '', row.statement || '', row.paperLabel || '',
          row.tier && EVIDENCE_TEXT[row.tier] ? EVIDENCE_TEXT[row.tier] : '',
          (row.decls || []).map(function (d) { return d.name; }).join(' ')].join(' '));
        return row;
      });
      edges = data.edges;
      relations = data.relations || [];
      captions = data.captions || [];
      adj = new Array(nodes.length);
      byId = {};
      problemIndex = {};
      var degree = new Array(nodes.length);
      var i;
      for (i = 0; i < nodes.length; i++) {
        adj[i] = [];
        degree[i] = 0;
        byId[nodes[i].id] = i;
        if (nodes[i].kind === 'problem' && nodes[i].sector) problemIndex[nodes[i].sector] = i;
      }
      for (i = 0; i < nodes.length; i++) {
        var st = nodes[i];
        if (st.kind !== 'paper_statement') continue;
        var paperAt = byId['paper:' + st.paperId];
        if (!st.paperTitle && paperAt !== undefined) st.paperTitle = nodes[paperAt].label;
        if (!st.placedBy && st.sector && problemIndex[st.sector] !== undefined) {
          st.placedBy = 'it is stated in a paper on ' + nodes[problemIndex[st.sector]].shortLabel;
        }
      }
      for (i = 0; i < edges.length; i++) {
        var a = edges[i][0], b = edges[i][1];
        var rel = relations[edges[i][2]] || null;
        if (!nodes[a] || !nodes[b]) continue;
        adj[a].push({ to: b, rel: rel, out: true });
        adj[b].push({ to: a, rel: rel, out: false });
        degree[a]++;
        degree[b]++;
      }
      for (i = 0; i < nodes.length; i++) {
        nodes[i].r += degreeBonus(nodes[i].kind, degree[i]);
      }
      hover = -1;
      selected = keepId && byId[keepId] !== undefined ? byId[keepId] : -1;
      // A history-restored form value can predate this data response.
      if (searchIn) query = normalizeSearchText(searchIn.value);
      countMatches();
      // A fitted overview follows the new extent. An explored camera keeps
      // its exact scale and centre when complete data arrives.
      if (!keepView || viewIsFitted) fit();
      draw();
      renderInspector();
      resolvePending();
    }

    readPalette();
    if (pageMode && window.location.hash.indexOf('#o=') === 0) {
      try {
        pendingId = decodeURIComponent(window.location.hash.slice(3));
      } catch (err) { pendingId = null; }
    }
    var dataUrl = canvas.getAttribute('data-universe-src');
    fetch(dataUrl).then(function (r) { return r.json(); }).then(function (data) {
      ingest(data);
    }).catch(function () {
      stage.classList.add('is-unavailable');
    });

    /* ---- Pointer ------------------------------------------------------ */

    var panning = false;
    var moved = false;

    canvas.addEventListener('pointermove', function (event) {
      if (panning) return;
      var rect = canvas.getBoundingClientRect();
      var i = nodeAt(event.clientX - rect.left, event.clientY - rect.top);
      if (i !== hover) {
        hover = i;
        canvas.classList.toggle('is-over', i >= 0);
        draw();
        if (pageMode) renderInspector(); else showCaption(i);
      }
    });
    canvas.addEventListener('pointerleave', function () {
      if (hover === -1) return;
      hover = -1;
      canvas.classList.remove('is-over');
      draw();
      if (pageMode) renderInspector(); else showCaption(-1);
    });
    canvas.addEventListener('click', function (event) {
      if (moved) return;
      var rect = canvas.getBoundingClientRect();
      var i = nodeAt(event.clientX - rect.left, event.clientY - rect.top);
      if (pageMode) {
        // First click pins; a second click on the pinned object opens it.
        if (i >= 0 && i === selected) { openTarget(nodes[i]); return; }
        pin(i, false);
        return;
      }
      if (i >= 0) { openTarget(nodes[i]); return; }
      var target = canvas.getAttribute('data-universe-href');
      if (target) window.location.href = target;
    });

    /* Pan and zoom only on the dedicated page; the landing teaser stays a
       fixed portrait so scrolling past it never fights the wheel. */
    if (pageMode) {
      var px0 = 0, py0 = 0;
      canvas.addEventListener('pointerdown', function (event) {
        panning = true;
        moved = false;
        canvas.classList.add('is-panning');
        px0 = event.clientX; py0 = event.clientY;
        canvas.setPointerCapture(event.pointerId);
      });
      canvas.addEventListener('pointerup', function (event) {
        panning = false;
        canvas.classList.remove('is-panning');
        canvas.releasePointerCapture(event.pointerId);
      });
      canvas.addEventListener('pointercancel', function () {
        panning = false;
        canvas.classList.remove('is-panning');
      });
      canvas.addEventListener('pointermove', function (event) {
        if (!panning) return;
        var dx = event.clientX - px0, dy = event.clientY - py0;
        if (!moved && dx * dx + dy * dy < 9) return;
        moved = true;
        viewIsFitted = false;
        view.tx += dx;
        view.ty += dy;
        px0 = event.clientX; py0 = event.clientY;
        draw();
      });
      canvas.addEventListener('wheel', function (event) {
        event.preventDefault();
        var rect = canvas.getBoundingClientRect();
        zoomAt(event.clientX - rect.left, event.clientY - rect.top,
          Math.exp(-event.deltaY * 0.0016));
      }, { passive: false });

      document.addEventListener('keydown', function (event) {
        var tag = event.target && event.target.tagName;
        var typing = tag === 'INPUT' || tag === 'TEXTAREA' || (event.target && event.target.isContentEditable);
        if (event.key === 'Escape' && selected >= 0) { pin(-1, false); return; }
        if (event.key === '/' && !typing && searchIn) {
          event.preventDefault();
          searchIn.focus();
          searchIn.select();
        }
      });

      stage.querySelectorAll('[data-universe-zoom]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var mode = btn.getAttribute('data-universe-zoom');
          if (mode === 'fit') { fit(); draw(); return; }
          zoomAt(canvas.clientWidth / 2, canvas.clientHeight / 2,
            mode === 'in' ? 1.45 : 1 / 1.45);
        });
      });
    }

    function zoomAt(mx, my, factor) {
      // A phone's fitted map can already be below 0.3. A fixed lower bound
      // made its first zoom-out jump inward instead of zooming out.
      var k = Math.min(9, Math.max(Math.min(0.3, fittedScale / 2), view.k * factor));
      viewIsFitted = false;
      factor = k / view.k;
      view.tx = mx - (mx - view.tx) * factor;
      view.ty = my - (my - view.ty) * factor;
      view.k = k;
      draw();
    }

    /* ---- Inspector clicks -------------------------------------------- */

    if (inspector) {
      inspector.addEventListener('click', function (event) {
        var go = event.target.closest ? event.target.closest('[data-universe-go]') : null;
        if (go) {
          var i = parseInt(go.getAttribute('data-universe-go'), 10);
          if (!isNaN(i) && nodes[i]) pin(i, true);
          return;
        }
        if (event.target.closest && event.target.closest('[data-universe-clear]')) {
          pin(-1, false);
          return;
        }
        var copy = event.target.closest ? event.target.closest('[data-universe-copy]') : null;
        if (copy) {
          navigator.clipboard.writeText(window.location.href).then(function () {
            copy.textContent = 'Link copied';
          }, function () {
            copy.textContent = 'Copy failed — use the address bar';
          });
        }
      });
    }

    /* ---- Controls ----------------------------------------------------- */

    function afterFilterChange() {
      if (hover >= 0 && !visible(nodes[hover])) hover = -1;
      if (selected >= 0 && !visible(nodes[selected])) pin(-1, false);
      else renderInspector();
      countMatches();
      draw();
    }

    document.querySelectorAll('[data-universe-lens]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var kinds = btn.getAttribute('data-universe-lens').split(' ');
        var pressed = btn.getAttribute('aria-pressed') === 'true';
        btn.setAttribute('aria-pressed', pressed ? 'false' : 'true');
        kinds.forEach(function (kind) { lensOff[kind] = pressed; });
        afterFilterChange();
      });
    });
    document.querySelectorAll('[data-universe-tier]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var tier = btn.getAttribute('data-universe-tier');
        var pressed = btn.getAttribute('aria-pressed') === 'true';
        btn.setAttribute('aria-pressed', pressed ? 'false' : 'true');
        tierOff[tier] = pressed;
        afterFilterChange();
      });
    });

    if (searchIn) {
      function syncSearchFromInput() {
        var restoredQuery = normalizeSearchText(searchIn.value);
        if (restoredQuery === query) return;
        query = restoredQuery;
        countMatches();
        draw();
      }
      searchIn.addEventListener('input', syncSearchFromInput);
      searchIn.addEventListener('focus', syncSearchFromInput);
      // History traversal may restore form state after lifecycle handlers.
      // Reconcile in the following task, without changing the pin or view.
      function syncRestoredSearch() { setTimeout(syncSearchFromInput, 0); }
      window.addEventListener('pageshow', syncRestoredSearch);
      window.addEventListener('popstate', syncRestoredSearch);
      /* Enter steps through the matches in kind order, so a search for a
         word can be walked object by object without leaving the keyboard. */
      searchIn.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && searchIn.value) {
          searchIn.value = '';
          query = '';
          countMatches();
          draw();
          event.stopPropagation();
          return;
        }
        if (event.key !== 'Enter') return;
        syncSearchFromInput();
        if (!matchList.length) return;
        event.preventDefault();
        var at = matchList.indexOf(selected);
        var next = at < 0 ? 0 : (at + (event.shiftKey ? matchList.length - 1 : 1)) % matchList.length;
        pin(matchList[next], true);
        searchIn.focus({ preventScroll: true });
      });
    }

    function loadFull() {
      if (!loadFullBtn || fullLoaded || fullLoading) return;
      fullLoading = true;
      loadFullBtn.disabled = true;
      loadFullBtn.textContent = 'Loading the complete universe…';
      var graphUrl = loadFullBtn.getAttribute('data-graph-src');
      var layoutUrl = loadFullBtn.getAttribute('data-layout-src');
      Promise.all([
        fetch(graphUrl).then(function (r) { return r.json(); }),
        fetch(layoutUrl).then(function (r) { return r.json(); })
      ]).then(function (results) {
        var graph = results[0], layout = results[1];
        var pos = layout.positions || {};
        var pages = layout.pages || {};
        var sectors = layout.sectors || {};
        var links = layout.links || {};
        var subs = {};
        (layout.sub_labels || []).forEach(function (pair) { subs[pair[0]] = pair[1]; });
        var index = {};
        var built = [];
        graph.nodes.forEach(function (n) {
          var at = pos[n.id];
          if (!at) return;
          index[n.id] = built.length;
          var sector = sectors[n.id] || null;
          var link = links[n.id] || {};
          built.push({
            paper: link.paper, paper_title: link.paper_title,
            paper_label: link.paper_label, lean: link.lean,
            id: n.id, kind: n.kind, label: n.label,
            short: layout.short && layout.short[n.id] || n.label,
            sub: subs[n.id] || null,
            status: n.status, statement: n.statement, boundary: n.boundary,
            disposition: n.disposition, question: n.question, subject: n.subject,
            declaration_count: n.declaration_count, theorem_count: n.theorem_count,
            page: pages[n.id] || null, source_github: n.source_github,
            sector: sector ? sector[0] : null, placed_by: sector ? sector[1] : null,
            side: n.side, lean_status: n.lean_status, comparator_status: n.comparator_status,
            palomar_status: n.palomar_status, lean_reason: n.lean_reason,
            comparator_queued_at: n.comparator_queued_at, named_inputs: n.named_inputs,
            comparator_entries: n.comparator_entries, comparator_runs: n.comparator_runs,
            declarations: n.declarations,
            tex: n.kind === 'paper_statement' && n.source_github ?
              String(n.source_github).replace(/^.*\/blob\/main\//, '') : null,
            x: at[0], y: at[1]
          });
        });
        var builtEdges = [];
        var builtRelations = [];
        var relIndex = {};
        graph.edges.forEach(function (edge) {
          var a = index[edge.source], b = index[edge.target];
          if (a === undefined || b === undefined) return;
          var rel = String(edge.relation || 'linked');
          if (!(rel in relIndex)) {
            relIndex[rel] = builtRelations.length;
            builtRelations.push(rel);
          }
          builtEdges.push([a, b, relIndex[rel]]);
        });
        fullLoaded = true;
        fullLoading = false;
        ingest({ nodes: built, edges: builtEdges, relations: builtRelations,
                 captions: layout.captions || captions, bands: layout.bands || bands });
        loadFullBtn.textContent = 'Complete universe loaded';
        document.querySelectorAll('[data-universe-lens-full]').forEach(function (btn) {
          btn.hidden = false;
        });
      }).catch(function () {
        fullLoading = false;
        loadFullBtn.disabled = false;
        loadFullBtn.textContent = 'Load the complete universe';
      });
    }
    if (loadFullBtn) {
      loadFullBtn.addEventListener('click', loadFull);
    }

    if (pageMode) {
      window.addEventListener('hashchange', function () {
        if (window.location.hash.indexOf('#o=') !== 0) {
          pendingId = null;
          pin(-1, false);
          return;
        }
        try { pendingId = decodeURIComponent(window.location.hash.slice(3)); }
        catch (err) { return; }
        resolvePending();
      });
    }

    var resizeTimer = null;
    window.addEventListener('resize', function () {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        var w = canvas.clientWidth, h = canvas.clientHeight;
        if (w === viewWidth && h === viewHeight) return;
        if (viewIsFitted) fit();
        else {
          // Keep the same object under the centre when rotating a phone or
          // resizing a window; only Reset should discard an explored view.
          view.tx += (w - viewWidth) / 2;
          view.ty += (h - viewHeight) / 2;
          viewWidth = w; viewHeight = h;
        }
        draw();
      }, 120);
    });
    document.addEventListener('plectis:theme', function () {
      readPalette();
      draw();
    });
  }

  function boot() {
    document.querySelectorAll('[data-universe-stage]').forEach(mount);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
