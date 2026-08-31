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
   cursor-chasing tooltip anywhere. */
(function () {
  'use strict';

  var KIND_COLOR = {
    universe: '--u-universe',
    problem: '--u-problem',
    public_claim: '--u-claim',
    paper: '--u-paper',
    human_document: '--u-document',
    integration_surface: '--u-integration',
    comparator_review_family: '--u-integration',
    registry_review_unit: '--u-integration',
    lean_module: '--u-module',
    mathematical_object: '--u-object'
  };
  /* Base radii before the degree bonus. The first screen is 192 objects, so
     it can afford to be generous; the two starfield kinds stay small because
     the complete universe adds over a thousand of them. */
  var KIND_RADIUS = {
    universe: 13,
    problem: 11,
    integration_surface: 9,
    paper: 7,
    registry_review_unit: 6.5,
    human_document: 6,
    public_claim: 5.2,
    comparator_review_family: 4.4,
    mathematical_object: 2.8,
    lean_module: 2
  };
  var KIND_LABEL = {
    universe: 'universe',
    problem: 'problem',
    public_claim: 'checked claim',
    paper: 'paper',
    human_document: 'repository document',
    integration_surface: 'verification surface',
    comparator_review_family: 'review family',
    registry_review_unit: 'prepared review unit',
    lean_module: 'Lean module',
    mathematical_object: 'argument step'
  };
  var KIND_PLURAL = {
    universe: 'Universe',
    problem: 'Problems',
    public_claim: 'Checked claims',
    paper: 'Papers',
    human_document: 'Repository documents',
    integration_surface: 'Verification surfaces',
    comparator_review_family: 'Review families',
    registry_review_unit: 'Prepared review units',
    lean_module: 'Lean modules',
    mathematical_object: 'Argument steps'
  };
  var KIND_DOT = {
    universe: 'dot--universe',
    problem: 'dot--problem',
    public_claim: 'dot--claim',
    paper: 'dot--paper',
    human_document: 'dot--document',
    integration_surface: 'dot--integration',
    comparator_review_family: 'dot--integration',
    registry_review_unit: 'dot--integration',
    lean_module: 'dot--module',
    mathematical_object: 'dot--object'
  };
  var KIND_ORDER = ['universe', 'problem', 'integration_surface', 'paper',
    'registry_review_unit', 'human_document', 'public_claim',
    'comparator_review_family', 'mathematical_object', 'lean_module'];
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

  function relText(rel) {
    return String(rel || 'linked').replace(/_/g, ' ');
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
    var adj = [];
    var view = { k: 1, tx: 0, ty: 0 };
    var hover = -1;
    var selected = -1;
    var query = '';
    var matchCount = 0;
    var lensOff = {};
    var palette = {};
    var fullLoaded = false;
    var pendingId = null;
    var countText = '';

    function readPalette() {
      var styles = getComputedStyle(document.documentElement);
      palette = { edge: cssColor(styles, '--u-edge', 'rgba(0,0,0,0.12)'),
                  edgeHot: cssColor(styles, '--u-edge-hot', 'rgba(60,90,160,0.5)'),
                  halo: cssColor(styles, '--u-halo', 'rgba(226,168,62,0.35)'),
                  rim: cssColor(styles, '--u-rim', 'rgba(0,0,0,0.3)'),
                  paper: cssColor(styles, '--surface', '#fffdf7'),
                  ink: cssColor(styles, '--ink', '#211318'),
                  faint: cssColor(styles, '--faint', '#786359') };
      for (var kind in KIND_COLOR) {
        palette[kind] = cssColor(styles, KIND_COLOR[kind], '#888888');
      }
    }

    function visible(node) {
      return !lensOff[node.kind];
    }
    function matches(node) {
      if (query.length < 2) return true;
      return node.label.toLowerCase().indexOf(query) !== -1;
    }
    function countMatches() {
      matchCount = 0;
      if (query.length < 2) return;
      for (var i = 0; i < nodes.length; i++) {
        if (visible(nodes[i]) && matches(nodes[i])) matchCount++;
      }
    }

    function fit() {
      if (!nodes.length) return;
      var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      }
      var w = canvas.clientWidth, h = canvas.clientHeight;
      var pad = 40;
      var k = Math.min((w - pad * 2) / Math.max(1, maxX - minX),
                       (h - pad * 2) / Math.max(1, maxY - minY));
      view.k = k;
      view.tx = w / 2 - k * (minX + maxX) / 2;
      view.ty = h / 2 - k * (minY + maxY) / 2;
    }

    function centerOn(i) {
      if (i < 0 || !nodes[i]) return;
      if (view.k < 1.1) view.k = 1.6;
      view.tx = canvas.clientWidth / 2 - nodes[i].x * view.k;
      view.ty = canvas.clientHeight / 2 - nodes[i].y * view.k;
      draw();
    }

    /* The focused object is the pinned one, or the hovered one while a
       pointer is down on the field. Everything it does not touch recedes. */
    function focusIndex() {
      return hover >= 0 ? hover : selected;
    }
    function neighbourSet(i) {
      var set = {};
      if (i < 0) return set;
      var rows = adj[i] || [];
      for (var j = 0; j < rows.length; j++) set[rows[j].to] = true;
      return set;
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

      /* Quiet edges first; when something is focused the rest recede. */
      ctx.lineWidth = 0.7;
      ctx.strokeStyle = palette.edge;
      ctx.globalAlpha = focus >= 0 ? 0.35 : 1;
      ctx.beginPath();
      for (i = 0; i < edges.length; i++) {
        if (focus >= 0 && (edges[i][0] === focus || edges[i][1] === focus)) continue;
        var a = nodes[edges[i][0]], b = nodes[edges[i][1]];
        if (!a || !b || !visible(a) || !visible(b)) continue;
        ctx.moveTo(a.x * view.k + view.tx, a.y * view.k + view.ty);
        ctx.lineTo(b.x * view.k + view.tx, b.y * view.k + view.ty);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;

      if (focus >= 0) {
        ctx.lineWidth = 1.6;
        ctx.strokeStyle = palette.edgeHot;
        ctx.beginPath();
        for (i = 0; i < edges.length; i++) {
          if (edges[i][0] !== focus && edges[i][1] !== focus) continue;
          var ha = nodes[edges[i][0]], hb = nodes[edges[i][1]];
          if (!ha || !hb || !visible(ha) || !visible(hb)) continue;
          ctx.moveTo(ha.x * view.k + view.tx, ha.y * view.k + view.ty);
          ctx.lineTo(hb.x * view.k + view.tx, hb.y * view.k + view.ty);
        }
        ctx.stroke();
      }

      var shown = 0;
      for (i = 0; i < nodes.length; i++) {
        n = nodes[i];
        if (!visible(n)) continue;
        shown++;
        x = n.x * view.k + view.tx;
        y = n.y * view.k + view.ty;
        if (x < -24 || y < -24 || x > w + 24 || y > h + 24) continue;
        var r = n.r;
        var alpha = 1;
        if (searching && !matches(n)) alpha = 0.12;
        if (focus >= 0 && i !== focus && !near[i]) alpha = Math.min(alpha, 0.25);
        ctx.globalAlpha = alpha;
        if (i === hover || i === selected) {
          r = n.r + 1.5;
          ctx.fillStyle = palette.halo;
          ctx.beginPath();
          ctx.arc(x, y, r + 7, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillStyle = palette[n.kind] || palette.faint;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
        if (r >= 3.4) {
          ctx.lineWidth = 1;
          ctx.strokeStyle = palette.rim;
          ctx.stroke();
        }
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
          (view.k > 1.7 && (n.kind === 'paper' || n.kind === 'human_document' ||
            n.kind === 'registry_review_unit')) ||
          (view.k > 3.4 && n.kind === 'public_claim');
        if (!wantLabel) continue;
        if (searching && !matches(n) && !isFocus) continue;
        if (focus >= 0 && i !== focus && !near[i] && !isFocus) continue;
        var lx = n.x * view.k + view.tx, ly = n.y * view.k + view.ty;
        if (lx < -60 || ly < -60 || lx > w + 60 || ly > h + 60) continue;
        var big = n.kind === 'problem' || n.kind === 'universe' || n.kind === 'integration_surface';
        ctx.font = (big ? '700 13px ' : '600 12px ') + SERIF;
        var text = clip(n.shortLabel, isFocus ? 60 : 42);
        ctx.lineWidth = 3.5;
        ctx.strokeStyle = palette.paper;
        ctx.strokeText(text, lx, ly + n.r + 15);
        ctx.fillStyle = palette.ink;
        ctx.fillText(text, lx, ly + n.r + 15);
      }

      if (countOut) {
        var line = String(shown) + ' objects, ' + String(edges.length) + ' connections shown';
        if (searching) line += ' · ' + String(matchCount) + ' match';
        if (line !== countText) {
          countText = line;
          countOut.textContent = line;
        }
      }
    }

    function nodeAt(px, py) {
      var best = -1, bestD = 14 * 14;
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (!visible(n)) continue;
        var x = n.x * view.k + view.tx, y = n.y * view.k + view.ty;
        var d = (x - px) * (x - px) + (y - py) * (y - py);
        var reach = Math.max(11, n.r + 6);
        if (d < Math.min(bestD, reach * reach)) { best = i; bestD = d; }
      }
      return best;
    }

    /* ---- Inspector (universe page) ---------------------------------- */

    function dotHtml(kind) {
      return '<span class="dot ' + (KIND_DOT[kind] || '') + '" aria-hidden="true"></span>';
    }

    function overviewHtml() {
      var counts = {};
      for (var i = 0; i < nodes.length; i++) {
        counts[nodes[i].kind] = (counts[nodes[i].kind] || 0) + 1;
      }
      var rows = '';
      for (var j = 0; j < KIND_ORDER.length; j++) {
        var kind = KIND_ORDER[j];
        if (!counts[kind]) continue;
        rows += '<li>' + dotHtml(kind) + '<span>' + escapeHtml(KIND_PLURAL[kind] || kind) +
          '</span><b>' + counts[kind] + '</b></li>';
      }
      return '<p class="universe-inspector__kind">The universe</p>' +
        '<h3 class="universe-inspector__title">' + nodes.length + ' objects in view</h3>' +
        '<ul class="universe-inspector__census">' + rows + '</ul>' +
        '<p class="universe-inspector__hint">Hover an object to preview it here. Click it to pin its card and light up everything it touches; press Esc to unpin.</p>';
    }

    function connectionRows(i) {
      var rows = (adj[i] || []).slice();
      rows.sort(function (p, q) {
        var a = nodes[p.to], b = nodes[q.to];
        var byKind = kindOrder(a.kind) - kindOrder(b.kind);
        if (byKind) return byKind;
        return a.label < b.label ? -1 : a.label > b.label ? 1 : 0;
      });
      var cap = 24;
      var html = '';
      for (var j = 0; j < rows.length && j < cap; j++) {
        var row = rows[j];
        var m = nodes[row.to];
        html += '<li><button type="button" class="universe-goto" data-universe-go="' + row.to + '">' +
          dotHtml(m.kind) +
          '<span class="universe-goto__label">' + escapeHtml(clip(m.label, 68)) + '</span>' +
          '<span class="universe-goto__rel">' + (row.out ? '→ ' : '← ') +
          escapeHtml(relText(row.rel)) + '</span>' +
          '</button></li>';
      }
      if (rows.length > cap) {
        html += '<li class="universe-goto__more">… and ' + (rows.length - cap) + ' more</li>';
      }
      return { html: html, total: rows.length };
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
        '<h3 class="universe-inspector__title">' + escapeHtml(n.label) + '</h3>'];
      var chips = '';
      if (n.status) chips += '<span class="universe-chip">' + escapeHtml(n.status) + '</span>';
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
      if (n.declaration_count != null) {
        var counts = String(n.declaration_count) + ' declarations';
        if (n.theorem_count != null) counts += ', ' + String(n.theorem_count) + ' theorems';
        parts.push('<p class="universe-inspector__note">' + counts + '</p>');
      }
      var links = [];
      if (n.page) links.push('<a href="' + escapeHtml(n.page) + '">Open on this site</a>');
      if (n.source_github) {
        links.push('<a class="source-link" href="' + escapeHtml(n.source_github) +
          '" data-link-kind="exogenous" rel="external noopener">View source on GitHub</a>');
      }
      if (links.length) {
        parts.push('<div class="universe-inspector__links">' + links.join(' ') + '</div>');
      }
      if (pinned) {
        var rows = connectionRows(i);
        if (rows.total) {
          parts.push('<h4 class="universe-inspector__sub">Connections (' + rows.total + ')</h4>');
          parts.push('<ul class="universe-inspector__list">' + rows.html + '</ul>');
        }
        if (canCopy) {
          parts.push('<button type="button" class="universe-inspector__copy" data-universe-copy>Copy link to this object</button>');
        }
      } else {
        parts.push('<p class="universe-inspector__hint">Click to pin this card and list its connections.</p>');
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
      selected = i;
      if (i >= 0) pendingId = null;
      renderInspector();
      updateHash();
      if (center && i >= 0) centerOn(i);
      draw();
    }

    function resolvePending() {
      if (!pendingId) return;
      for (var i = 0; i < nodes.length; i++) {
        if (nodes[i].id === pendingId) {
          pin(i, true);
          return;
        }
      }
    }

    /* ---- Caption (landing teaser) ------------------------------------ */

    function showCaption(i) {
      if (!caption) return;
      if (i < 0) {
        caption.classList.remove('is-shown');
        return;
      }
      var n = nodes[i];
      caption.textContent = (KIND_LABEL[n.kind] || n.kind) + ' — ' + clip(n.label, 96);
      caption.classList.add('is-shown');
    }

    /* ---- Data --------------------------------------------------------- */

    function degreeBonus(kind, degree) {
      var cap = (kind === 'lean_module' || kind === 'mathematical_object') ? 1 : 3.5;
      return Math.min(cap, Math.sqrt(Math.max(0, degree - 1)) * 0.55);
    }

    function ingest(data) {
      var keepId = selected >= 0 && nodes[selected] ? nodes[selected].id : null;
      nodes = data.nodes.map(function (n) {
        return {
          id: n.id, kind: n.kind, label: n.label,
          shortLabel: n.short || n.label,
          status: n.status || null, statement: n.statement || null,
          boundary: n.boundary || null, disposition: n.disposition || null,
          question: n.question || null, subject: n.subject || null,
          declaration_count: n.declaration_count != null ? n.declaration_count : null,
          theorem_count: n.theorem_count != null ? n.theorem_count : null,
          page: n.page || null, source_github: n.source_github || null,
          x: n.x, y: n.y, r: KIND_RADIUS[n.kind] || 2
        };
      });
      edges = data.edges;
      relations = data.relations || [];
      adj = new Array(nodes.length);
      var degree = new Array(nodes.length);
      var i;
      for (i = 0; i < nodes.length; i++) { adj[i] = []; degree[i] = 0; }
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
      selected = -1;
      if (keepId) pendingId = keepId;
      countMatches();
      fit();
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
      if (pageMode) { pin(i, false); return; }
      if (i >= 0) {
        var n = nodes[i];
        if (n.page) { window.location.href = n.page; return; }
        if (n.source_github) { window.open(n.source_github, '_blank', 'noopener'); return; }
      }
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
        if (event.key === 'Escape' && selected >= 0) pin(-1, false);
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
      var k = Math.min(9, Math.max(0.3, view.k * factor));
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

    document.querySelectorAll('[data-universe-lens]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var kinds = btn.getAttribute('data-universe-lens').split(' ');
        var pressed = btn.getAttribute('aria-pressed') === 'true';
        btn.setAttribute('aria-pressed', pressed ? 'false' : 'true');
        kinds.forEach(function (kind) { lensOff[kind] = pressed; });
        countMatches();
        draw();
      });
    });

    if (searchIn) {
      searchIn.addEventListener('input', function () {
        query = searchIn.value.trim().toLowerCase();
        countMatches();
        draw();
      });
      searchIn.addEventListener('keydown', function (event) {
        if (event.key !== 'Enter' || query.length < 2) return;
        var best = -1;
        for (var i = 0; i < nodes.length; i++) {
          if (!visible(nodes[i]) || !matches(nodes[i])) continue;
          if (best < 0 || kindOrder(nodes[i].kind) < kindOrder(nodes[best].kind)) best = i;
        }
        if (best >= 0) pin(best, true);
      });
    }

    if (loadFullBtn) {
      loadFullBtn.addEventListener('click', function () {
        if (fullLoaded) return;
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
          var index = {};
          var built = [];
          graph.nodes.forEach(function (n) {
            var at = pos[n.id];
            if (!at) return;
            index[n.id] = built.length;
            built.push({
              id: n.id, kind: n.kind, label: n.label,
              short: layout.short && layout.short[n.id] || n.label,
              status: n.status, statement: n.statement, boundary: n.boundary,
              disposition: n.disposition, question: n.question, subject: n.subject,
              declaration_count: n.declaration_count, theorem_count: n.theorem_count,
              page: pages[n.id] || null, source_github: n.source_github,
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
          ingest({ nodes: built, edges: builtEdges, relations: builtRelations });
          fullLoaded = true;
          loadFullBtn.textContent = 'Complete universe loaded';
          document.querySelectorAll('[data-universe-lens-full]').forEach(function (btn) {
            btn.hidden = false;
          });
        }).catch(function () {
          loadFullBtn.disabled = false;
          loadFullBtn.textContent = 'Load the complete universe';
        });
      });
    }

    var resizeTimer = null;
    window.addEventListener('resize', function () {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () { fit(); draw(); }, 120);
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
