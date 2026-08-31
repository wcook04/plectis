/* Plectis — universe map renderer.
   Draws the Lean corpus graph on a canvas from a pre-computed layout file.
   No libraries, no physics: coordinates are decided at build time so the
   picture is identical on every visit and the first paint costs one fetch
   and one draw. The canvas is an enhancement — every object it shows is
   also in the HTML index on the universe page, so nothing is canvas-only.
   All colour comes from CSS custom properties, re-read on theme change. */
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
  var KIND_RADIUS = {
    universe: 10,
    problem: 7.5,
    paper: 5,
    human_document: 4,
    public_claim: 3.2,
    comparator_review_family: 2.8,
    registry_review_unit: 4.5,
    integration_surface: 6,
    lean_module: 1.7,
    mathematical_object: 2.4
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

  function cssColor(styles, name, fallback) {
    var v = styles.getPropertyValue(name).trim();
    return v || fallback;
  }

  function mount(stage) {
    var canvas = stage.querySelector('canvas');
    if (!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext('2d');
    var tip = stage.querySelector('.universe-tip');
    var pageMode = canvas.classList.contains('universe-canvas--page');
    var inspector = document.querySelector('[data-universe-inspector]');
    var countOut = document.querySelector('[data-universe-count]');
    var searchIn = document.querySelector('[data-universe-search]');
    var loadFullBtn = document.querySelector('[data-universe-load-full]');

    var nodes = [];
    var edges = [];
    var view = { k: 1, tx: 0, ty: 0 };
    var hover = -1;
    var selected = -1;
    var query = '';
    var lensOff = {};
    var palette = {};
    var fullLoaded = false;

    function readPalette() {
      var styles = getComputedStyle(document.documentElement);
      palette = { edge: cssColor(styles, '--u-edge', 'rgba(0,0,0,0.12)'),
                  edgeHot: cssColor(styles, '--u-edge-hot', 'rgba(60,90,160,0.5)'),
                  halo: cssColor(styles, '--u-halo', 'rgba(226,168,62,0.35)'),
                  ink: cssColor(styles, '--ink', '#211318'),
                  faint: cssColor(styles, '--faint', '#786359') };
      for (var kind in KIND_COLOR) {
        palette[kind] = cssColor(styles, KIND_COLOR[kind], '#888888');
      }
    }

    function visible(node) {
      if (lensOff[node.kind]) return false;
      return true;
    }
    function matches(node) {
      if (query.length < 2) return true;
      return node.label.toLowerCase().indexOf(query) !== -1;
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
      var pad = 34;
      var k = Math.min((w - pad * 2) / Math.max(1, maxX - minX),
                       (h - pad * 2) / Math.max(1, maxY - minY));
      view.k = k;
      view.tx = w / 2 - k * (minX + maxX) / 2;
      view.ty = h / 2 - k * (minY + maxY) / 2;
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
      var i, n;

      ctx.lineWidth = 0.6;
      ctx.strokeStyle = palette.edge;
      ctx.beginPath();
      for (i = 0; i < edges.length; i++) {
        var a = nodes[edges[i][0]], b = nodes[edges[i][1]];
        if (!a || !b || !visible(a) || !visible(b)) continue;
        if (hover >= 0 && (edges[i][0] === hover || edges[i][1] === hover)) continue;
        ctx.moveTo(a.x * view.k + view.tx, a.y * view.k + view.ty);
        ctx.lineTo(b.x * view.k + view.tx, b.y * view.k + view.ty);
      }
      ctx.stroke();

      if (hover >= 0) {
        ctx.lineWidth = 1.1;
        ctx.strokeStyle = palette.edgeHot;
        ctx.beginPath();
        for (i = 0; i < edges.length; i++) {
          if (edges[i][0] !== hover && edges[i][1] !== hover) continue;
          var ha = nodes[edges[i][0]], hb = nodes[edges[i][1]];
          if (!visible(ha) || !visible(hb)) continue;
          ctx.moveTo(ha.x * view.k + view.tx, ha.y * view.k + view.ty);
          ctx.lineTo(hb.x * view.k + view.tx, hb.y * view.k + view.ty);
        }
        ctx.stroke();
      }

      for (i = 0; i < nodes.length; i++) {
        n = nodes[i];
        if (!visible(n)) continue;
        var x = n.x * view.k + view.tx, y = n.y * view.k + view.ty;
        if (x < -20 || y < -20 || x > w + 20 || y > h + 20) continue;
        var r = n.r;
        var dim = searching && !matches(n);
        ctx.globalAlpha = dim ? 0.14 : 1;
        if (i === hover || i === selected) {
          ctx.fillStyle = palette.halo;
          ctx.beginPath();
          ctx.arc(x, y, r + 6, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.fillStyle = palette[n.kind] || palette.faint;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      ctx.font = '600 12px ' + '"Iowan Old Style", Palatino, Georgia, serif';
      ctx.textAlign = 'center';
      for (i = 0; i < nodes.length; i++) {
        n = nodes[i];
        if (!visible(n)) continue;
        var wantLabel = n.kind === 'problem' || n.kind === 'universe' ||
          n.kind === 'integration_surface' || i === hover || i === selected ||
          (view.k > 2.1 && (n.kind === 'paper' || n.kind === 'human_document'));
        if (!wantLabel) continue;
        var lx = n.x * view.k + view.tx, ly = n.y * view.k + view.ty;
        if (lx < -40 || ly < -40 || lx > w + 40 || ly > h + 40) continue;
        if (query.length >= 2 && !matches(n) && i !== hover) continue;
        ctx.fillStyle = palette.ink;
        ctx.fillText(n.shortLabel, lx, ly + n.r + 14);
      }
    }

    function nodeAt(px, py) {
      var best = -1, bestD = 13 * 13;
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (!visible(n)) continue;
        var x = n.x * view.k + view.tx, y = n.y * view.k + view.ty;
        var d = (x - px) * (x - px) + (y - py) * (y - py);
        var reach = Math.max(9, n.r + 5);
        if (d < Math.min(bestD, reach * reach)) { best = i; bestD = d; }
      }
      return best;
    }

    function showTip(i, px, py) {
      if (!tip) return;
      if (i < 0) { tip.classList.remove('is-shown'); return; }
      var n = nodes[i];
      var kind = KIND_LABEL[n.kind] || n.kind;
      var status = n.status ? '<span class="universe-tip__status">' + escapeHtml(n.status) + '</span>' : '';
      tip.innerHTML = '<span class="universe-tip__kind">' + escapeHtml(kind) + '</span>' +
        escapeHtml(n.label) + (status ? '<br>' + status : '');
      var w = stage.clientWidth;
      tip.style.left = Math.min(px + 14, w - 310) + 'px';
      tip.style.top = (py + 16) + 'px';
      tip.classList.add('is-shown');
    }

    function escapeHtml(text) {
      return String(text).replace(/[&<>"']/g, function (ch) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch];
      });
    }

    function inspect(i) {
      selected = i;
      if (!inspector) return;
      if (i < 0) { inspector.hidden = true; return; }
      var n = nodes[i];
      var parts = ['<p class="universe-inspector__kind">' + escapeHtml(KIND_LABEL[n.kind] || n.kind) +
        (n.status ? ' &middot; ' + escapeHtml(n.status) : '') + '</p>'];
      parts.push('<h3>' + escapeHtml(n.label) + '</h3>');
      if (n.statement) parts.push('<p>' + escapeHtml(n.statement) + '</p>');
      if (n.boundary) parts.push('<p>' + escapeHtml(n.boundary) + '</p>');
      var links = [];
      if (n.page) links.push('<a href="' + escapeHtml(n.page) + '">Open on this site</a>');
      if (n.source_github) {
        links.push('<a class="source-link" href="' + escapeHtml(n.source_github) +
          '" data-link-kind="exogenous" rel="external noopener">View source on GitHub</a>');
      }
      parts.push('<div class="universe-inspector__links">' + links.join(' ') + '</div>');
      inspector.innerHTML = parts.join('');
      inspector.hidden = false;
      draw();
    }

    function ingest(data) {
      nodes = data.nodes.map(function (n) {
        return {
          id: n.id, kind: n.kind, label: n.label,
          shortLabel: n.short || n.label,
          status: n.status || null, statement: n.statement || null,
          boundary: n.boundary || null,
          page: n.page || null, source_github: n.source_github || null,
          x: n.x, y: n.y, r: n.r || KIND_RADIUS[n.kind] || 2
        };
      });
      edges = data.edges;
      hover = -1;
      selected = -1;
      fit();
      draw();
      if (countOut) {
        countOut.textContent = String(nodes.length) + ' objects, ' + String(edges.length) + ' connections shown';
      }
    }

    readPalette();
    var dataUrl = canvas.getAttribute('data-universe-src');
    fetch(dataUrl).then(function (r) { return r.json(); }).then(function (data) {
      ingest(data);
    }).catch(function () {
      stage.classList.add('is-unavailable');
    });

    canvas.addEventListener('pointermove', function (event) {
      if (panning) return;
      var rect = canvas.getBoundingClientRect();
      var i = nodeAt(event.clientX - rect.left, event.clientY - rect.top);
      if (i !== hover) { hover = i; draw(); }
      showTip(i, event.clientX - rect.left, event.clientY - rect.top);
      canvas.style.cursor = i >= 0 ? 'pointer' : (pageMode ? 'grab' : 'crosshair');
    });
    canvas.addEventListener('pointerleave', function () {
      hover = -1;
      showTip(-1, 0, 0);
      draw();
    });
    canvas.addEventListener('click', function (event) {
      var rect = canvas.getBoundingClientRect();
      var i = nodeAt(event.clientX - rect.left, event.clientY - rect.top);
      if (pageMode) { inspect(i); return; }
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
    var panning = false;
    if (pageMode) {
      var px0 = 0, py0 = 0;
      canvas.addEventListener('pointerdown', function (event) {
        panning = true;
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
        view.tx += event.clientX - px0;
        view.ty += event.clientY - py0;
        px0 = event.clientX; py0 = event.clientY;
        draw();
      });
      canvas.addEventListener('wheel', function (event) {
        event.preventDefault();
        var rect = canvas.getBoundingClientRect();
        var mx = event.clientX - rect.left, my = event.clientY - rect.top;
        var factor = Math.exp(-event.deltaY * 0.0016);
        var k = Math.min(9, Math.max(0.35, view.k * factor));
        factor = k / view.k;
        view.tx = mx - (mx - view.tx) * factor;
        view.ty = my - (my - view.ty) * factor;
        view.k = k;
        draw();
      }, { passive: false });
    }

    document.querySelectorAll('[data-universe-lens]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var kinds = btn.getAttribute('data-universe-lens').split(' ');
        var pressed = btn.getAttribute('aria-pressed') === 'true';
        btn.setAttribute('aria-pressed', pressed ? 'false' : 'true');
        kinds.forEach(function (kind) { lensOff[kind] = pressed; });
        draw();
      });
    });

    if (searchIn) {
      searchIn.addEventListener('input', function () {
        query = searchIn.value.trim().toLowerCase();
        draw();
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
              page: pages[n.id] || null, source_github: n.source_github,
              x: at[0], y: at[1], r: KIND_RADIUS[n.kind] || 2
            });
          });
          var builtEdges = [];
          graph.edges.forEach(function (edge) {
            var a = index[edge.source], b = index[edge.target];
            if (a !== undefined && b !== undefined) builtEdges.push([a, b]);
          });
          ingest({ nodes: built, edges: builtEdges });
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
