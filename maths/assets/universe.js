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
    universe: 15,
    problem: 13.5,
    integration_surface: 11,
    paper: 5.5,
    human_document: 6,
    public_claim: 3.6,
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
  var SERIF = '"Plectis Serif", "Plectis Math", "Iowan Old Style", Georgia, serif';

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
  /* A connection in words, from the object on the card: the first phrase
     when it is the edge's source, the second when it is the target. The
     edges run Comparator → result (replayed, queued), Palomar → result,
     paper → result, claim → result (a shared declaration), problem →
     paper, and universe → problem, paper, document and claim. */
  var REL_PHRASE = {
    replayed: ['Replayed', 'Replayed by'],
    queued: ['Will replay', 'Queued for a replay by'],
    holds_prepared: ['Holds prepared', 'Prepared for'],
    states: ['States', 'Stated in'],
    same_lean_declaration: ['Shares a Lean declaration with', 'Shares a Lean declaration with'],
    explained_by: ['Written up in', 'Writes up'],
    contains: ['Contains', 'Part of'],
    interpreted_by: ['Described in', 'Describes'],
    publishes: ['Publishes', 'Published by']
  };
  function relPhrase(rel, out) {
    var pair = REL_PHRASE[rel];
    if (pair) return pair[out ? 0 : 1];
    var text = relText(rel);
    return text.charAt(0).toUpperCase() + text.slice(1);
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
    var paperSequence = {};
    // Boxes taken by labels and anchor discs in the frame being drawn.
    var labelBoxes = [];
    // Two boxes collide when they share more than a sliver: a label may
    // graze the padding round a disc, it may not cover the disc.
    var LABEL_GRACE = 2;
    function labelCollides(box) {
      for (var b = 0; b < labelBoxes.length; b++) {
        var p = labelBoxes[b];
        if (p.owner !== undefined && p.owner === box.owner) continue;
        if (box.x0 < p.x1 - LABEL_GRACE && box.x1 > p.x0 + LABEL_GRACE &&
            box.y0 < p.y1 - LABEL_GRACE && box.y1 > p.y0 + LABEL_GRACE) return true;
      }
      return false;
    }
    // The name plates of the hovered and the selected result in the frame
    // being drawn. They are placed before anything is lettered, so a name a
    // plate would half cover steps aside while the reader points.
    var plateBoxes = [];
    function underPlate(box) {
      for (var b = 0; b < plateBoxes.length; b++) {
        var p = plateBoxes[b];
        if (box.x0 < p.x1 - LABEL_GRACE && box.x1 > p.x0 + LABEL_GRACE &&
            box.y0 < p.y1 - LABEL_GRACE && box.y1 > p.y0 + LABEL_GRACE) return true;
      }
      return false;
    }
    var bands = [];
    /* A statement card's Lean statements and Comparator checks arrive on
       first opening, from the experience API; the teaser never asks. */
    var detailUrl = canvas.getAttribute('data-universe-detail');
    var detail = null;
    var detailLoading = false;
    /* A result's card quotes its paper. Each paper's excerpts (the printed
       environment, its maths as MathML) come in one small file, fetched the
       first time the pointer or a pin reaches one of its results. */
    var excerptRoutes = {};
    var excerpts = {};
    var excerptLoading = {};
    // Which place a pinned result's quote shows when two papers state it.
    var quoteAt = -1;
    /* The data's routes (papers/…, problems/…) are relative to maths/. The
       landing draws the teaser from the site root and names that directory
       in data-universe-base; without it a dot opened /papers/… and 404ed. */
    var routeBase = canvas.getAttribute('data-universe-base') || '';
    function route(href) {
      if (!href || /^(?:[a-z][a-z0-9+.-]*:|\/|#)/i.test(href)) return href;
      return routeBase + href;
    }

    function readPalette() {
      var styles = getComputedStyle(document.documentElement);
      palette = { edge: cssColor(styles, '--u-edge', 'rgba(0,0,0,0.12)'),
                  plate: cssColor(styles, '--u-plate', 'rgba(127,127,127,0.07)'),
                  edgeHot: cssColor(styles, '--u-edge-hot', 'rgba(60,90,160,0.5)'),
                  halo: cssColor(styles, '--u-halo', 'rgba(226,168,62,0.35)'),
                  rim: cssColor(styles, '--u-rim', 'rgba(0,0,0,0.3)'),
                  ground: cssColor(styles, '--surface', '#fffdf7'),
                  ink: cssColor(styles, '--ink', '#211318'),
                  faint: cssColor(styles, '--faint', '#786359'),
                  muted: cssColor(styles, '--muted', '#6b5f58') };
      for (var kind in KIND_COLOR) {
        palette[kind] = cssColor(styles, KIND_COLOR[kind], '#888888');
      }
      darkGround = groundIsDark(palette.ground);
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
      // With the results ring shown, the frame holds its titles as well:
      // the outer band, the gap, two lines of text and a margin to spare.
      if (bands.length && !lensOff.paper_statement) {
        var outer = 0;
        for (var b = 0; b < bands.length; b++) outer = Math.max(outer, bandRadii(bands[b])[1] || 0);
        var room = Math.min(w, h) / 2 - 56;
        if (outer && room > 40) k = Math.min(k, room / (outer + 6));
      }
      k = Math.max(0.001, k);
      fittedScale = k;
      viewIsFitted = true;
      viewWidth = w; viewHeight = h;
      view.k = k;
      view.tx = w / 2 - k * (minX + maxX) / 2;
      view.ty = h / 2 - k * (minY + maxY) / 2;
    }

    /* ---- Camera ------------------------------------------------------ */
    /* A move between views eases over a third of a second, so the reader
       keeps their bearings; it is skipped under reduced motion. The centre
       of the view travels in a straight line and the scale geometrically,
       which keeps the move from swooping. */
    var cameraFrame = 0;
    var reduceMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
    function easeInOut(t) {
      return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    /* The page's first view opens from the centre out, the way the map
       reads: the core, then the orbit, the claims and the results, over a
       little more than a second. It plays once, only on the map's own page,
       and never under reduced motion, in a hidden tab, or when a link opens
       on a chosen object. */
    /* Focus fades in: the first hover or selection dims the rest of the
       field over a sixth of a second rather than at once. Moving from one
       object to the next keeps the dimming as it is. Letting go holds the
       dim a moment (FOCUS_HOLD), then eases it out, the field still dimmed
       toward the object let go of; a new focus picks up from wherever that
       fade has reached and never restarts from nothing. So the gap between
       two dots under a sweeping pointer no longer snaps the field bright
       and dark again (it strobed: measured 33.8 to 40.5 luminance three
       times in a 1.2s sweep). Name plates follow the pointer at once.
       Skipped under reduced motion. */
    var FOCUS_IN = 180, FOCUS_HOLD = 140, FOCUS_OUT = 220;
    var focusMix = 1, focusWas = -1, focusFrame = 0, focusFade = null, focusHeld = -1;
    function fadeFocus(to, dur, delay) {
      if (reduceMotion || !window.requestAnimationFrame) {
        focusMix = to;
        focusFade = null;
        if (to === 0) focusHeld = -1;
        return;
      }
      focusFade = { from: focusMix, to: to, dur: Math.max(1, dur), delay: delay, start: null };
      if (!focusFrame) focusFrame = requestMotionFrame(stepFocusFade);
    }
    function stepFocusFade(now) {
      focusFrame = 0;
      var f = focusFade;
      if (!f) return;
      if (f.start === null) f.start = now;
      var t = Math.max(0, Math.min(1, (now - f.start - f.delay) / f.dur));
      focusMix = f.from + (f.to - f.from) * (1 - (1 - t) * (1 - t));
      if (t < 1) {
        focusFrame = requestMotionFrame(stepFocusFade);
      } else {
        focusFade = null;
        if (f.to === 0) focusHeld = -1;
      }
      draw();
    }
    // The object the field dims toward: the focus, or, while the dim eases
    // out, the one just let go of.
    function trackFocus(focus) {
      if (focus >= 0 && focusWas < 0) {
        if (!focusFade) focusMix = 0;
        focusHeld = -1;
        fadeFocus(1, FOCUS_IN * (1 - focusMix), 0);
      } else if (focus < 0 && focusWas >= 0) {
        focusHeld = focusWas;
        fadeFocus(0, FOCUS_OUT, FOCUS_HOLD);
      }
      if (focus !== focusWas) {
        // A selection plays its moment once; focus returning to it after a
        // hover elsewhere does not play it again.
        startPulse(focus >= 0 && focus === selected && selected === pulsedSelection ? -1 : focus);
        if (focus >= 0 && focus === selected) pulsedSelection = selected;
      }
      focusWas = focus;
      return focus >= 0 ? focus : focusHeld;
    }
    var pulsedSelection = -1;
    // What a dimmed thing's alpha is, part way through the fade.
    function dimmed(base) { return 1 - (1 - base) * focusMix; }

    /* ---- Light ------------------------------------------------------- */
    /* Light belongs to the evidence, as colour does, and the ground stays
       flat. On the dark ground a replayed result glows faintly, an ember,
       so the checked ring reads as lit before a word is read; on paper a
       glow would only smudge the mark, so there the ember stays a mark. The
       mark in focus glows in either scheme. */
    var darkGround = false;
    // Measured on the landing at 1280 and 1440: below about a fifth, the
    // halo at a band's edge does not register at all.
    var EMBER_REST = 0.22, EMBER_LIT = 0.36, EMBER_REACH = 4.4;
    function groundIsDark(color) {
      var rgb = null, hex = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(color || '');
      if (hex) {
        var h = hex[1].length === 3 ? hex[1].replace(/(.)/g, '$1$1') : hex[1];
        rgb = [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
      } else {
        var fn = /^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)/i.exec(color || '');
        if (fn) rgb = [+fn[1], +fn[2], +fn[3]];
      }
      return !!rgb && (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255 < 0.35;
    }
    // One soft disc per colour, drawn once: white light masked to the
    // colour, so its edge fades to nothing rather than through grey.
    var glowSprites = {};
    function glowSprite(color) {
      if (Object.prototype.hasOwnProperty.call(glowSprites, color)) return glowSprites[color];
      var sprite = document.createElement ? document.createElement('canvas') : null;
      var g = sprite && sprite.getContext ? sprite.getContext('2d') : null;
      if (g && g.createRadialGradient) {
        sprite.width = sprite.height = 64;
        var light = g.createRadialGradient(32, 32, 0, 32, 32, 32);
        light.addColorStop(0, 'rgba(255,255,255,1)');
        light.addColorStop(0.28, 'rgba(255,255,255,0.55)');
        light.addColorStop(0.62, 'rgba(255,255,255,0.13)');
        light.addColorStop(1, 'rgba(255,255,255,0)');
        g.fillStyle = light;
        g.fillRect(0, 0, 64, 64);
        g.globalCompositeOperation = 'source-in';
        g.fillStyle = color;
        g.fillRect(0, 0, 64, 64);
      } else {
        sprite = null;
      }
      glowSprites[color] = sprite;
      return sprite;
    }
    function drawGlow(x, y, radius, color, alpha) {
      if (alpha <= 0.002 || radius <= 0) return;
      var sprite = glowSprite(color);
      if (!sprite) return;
      ctx.globalAlpha = Math.min(1, alpha);
      ctx.drawImage(sprite, x - radius, y - radius, radius * 2, radius * 2);
    }

    /* One orchestrated moment shows where a result's evidence goes. A
       reader who settles on a result sees its mark send out one ripple and
       a bead of light run along each of its threads; when Comparator
       replayed the result, Comparator answers with a brief glow. It waits a
       tenth of a second, so a pointer sweeping across a band leaves no
       trail, plays once in about a second and a half, and is skipped under
       reduced motion, which keeps the still glow. */
    var PULSE_WAIT = 110, PULSE_RIPPLE = 720, PULSE_TRAVEL = 620, PULSE_STAGGER = 70, PULSE_BLOOM = 560;
    var PULSE_THREADS = 4;
    var PULSE_END = PULSE_WAIT + (PULSE_THREADS - 1) * PULSE_STAGGER + PULSE_TRAVEL + PULSE_BLOOM;
    var pulse = { at: -1, ms: 1e9, frame: 0 };
    function startPulse(at) {
      if (pulse.frame && window.cancelAnimationFrame) cancelMotionFrame(pulse.frame);
      pulse.frame = 0;
      pulse.at = at;
      pulse.ms = 1e9;
      if (at < 0 || reduceMotion || !window.requestAnimationFrame || document.hidden) return;
      pulse.ms = 0;
      var start = null;
      var step = function (now) {
        if (start === null) start = now;
        pulse.ms = now - start;
        pulse.frame = pulse.ms < PULSE_END ? requestMotionFrame(step) : 0;
        draw();
      };
      pulse.frame = requestMotionFrame(step);
    }
    function pulsePhase(delay, length) {
      var t = (pulse.ms - delay) / length;
      return t <= 0 ? 0 : t >= 1 ? 1 : t;
    }
    // A result's threads, in the order their beads leave it: the edges the
    // focus already lights, toward the checking surfaces first.
    function pulseThreads(focus, hot) {
      var n = nodes[focus];
      if (!n || (n.kind !== 'paper_statement' && n.kind !== 'public_claim')) return [];
      var rows = [];
      hot.forEach(function (at) {
        var other = edges[at][0] === focus ? edges[at][1] : edges[at][0];
        if (nodes[other]) rows.push(other);
      });
      rows.sort(function (a, b) {
        return (nodes[b].kind === 'integration_surface') - (nodes[a].kind === 'integration_surface');
      });
      return rows.slice(0, PULSE_THREADS).map(function (other, k) {
        return { other: other, delay: PULSE_WAIT + k * PULSE_STAGGER };
      });
    }
    function focusColor(n) {
      if (n.kind === 'problem') return palette.problem;
      if (n.kind === 'universe') return palette.universe;
      return glyphColor(n);
    }
    // Under the marks: the embers, the glow round the focus, and the glow
    // Comparator answers with.
    function drawLight(focus, near, searching, threads, rs, w, h) {
      var i, n, x, y;
      ctx.globalCompositeOperation = darkGround ? 'lighter' : 'source-over';
      if (darkGround && !lensOff.paper_statement) {
        for (i = 0; i < nodes.length; i++) {
          n = nodes[i];
          if (n.kind !== 'paper_statement' || n.tier !== 'replayed' || !visible(n)) continue;
          if (searching && !matches(n)) continue;
          x = n.x * view.k + view.tx; y = n.y * view.k + view.ty;
          if (x < -30 || y < -30 || x > w + 30 || y > h + 30) continue;
          var lit = focus >= 0 && (i === focus || near[i]);
          var fade = focus >= 0 && !lit ? 1 - focusMix : 1;
          drawGlow(x, y, n.r * rs * EMBER_REACH, palette.integration_surface,
                   (lit ? EMBER_LIT : EMBER_REST) * fade * revealAlpha(3));
        }
      }
      if (focus >= 0 && nodes[focus] && visible(nodes[focus])) {
        n = nodes[focus];
        x = n.x * view.k + view.tx; y = n.y * view.k + view.ty;
        var r = n.r * rs + 1.5;
        var swell = 1 - Math.pow(1 - pulsePhase(0, 240), 2);
        drawGlow(x, y, r * (n.kind === 'problem' || n.kind === 'universe' ? 2.6 : 5.2), focusColor(n),
                 (darkGround ? 0.62 : 0.3) * swell);
        if (n.tier === 'replayed') {
          threads.forEach(function (th) {
            var m = nodes[th.other];
            if (m.id === 'integration:palomar' || m.kind !== 'integration_surface') return;
            var b = pulsePhase(th.delay + PULSE_TRAVEL, PULSE_BLOOM);
            if (b <= 0 || b >= 1) return;
            drawGlow(m.x * view.k + view.tx, m.y * view.k + view.ty, m.r * rs * 4.2,
                     palette.integration_surface, (darkGround ? 0.85 : 0.45) * Math.sin(Math.PI * b));
          });
        }
      }
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
    }
    // Over the marks: the ripple and the beads.
    function drawPulse(focus, threads, rs) {
      if (focus < 0 || pulse.at !== focus || pulse.ms >= PULSE_END) return;
      var n = nodes[focus];
      var x = n.x * view.k + view.tx, y = n.y * view.k + view.ty;
      var r = n.r * rs + 1.5, color = focusColor(n);
      var t = pulsePhase(PULSE_WAIT, PULSE_RIPPLE);
      if (t > 0 && t < 1) {
        var e = 1 - Math.pow(1 - t, 3);
        ctx.globalAlpha = 0.6 * (1 - e);
        ctx.lineWidth = 1.3;
        ctx.strokeStyle = color;
        ctx.beginPath();
        ctx.arc(x, y, r + 3 + e * Math.max(16, r * 1.6), 0, Math.PI * 2);
        ctx.stroke();
      }
      var size = Math.max(0.8, rs);
      threads.forEach(function (th) {
        var p = pulsePhase(th.delay, PULSE_TRAVEL);
        if (p <= 0 || p >= 1) return;
        var m = nodes[th.other];
        var mx = m.x * view.k + view.tx, my = m.y * view.k + view.ty;
        var fade = Math.min(1, p * 6, (1 - p) * 6);
        var q = easeInOut(p);
        var bx = x + (mx - x) * q, by = y + (my - y) * q;
        ctx.globalCompositeOperation = darkGround ? 'lighter' : 'source-over';
        drawGlow(bx, by, 10 * size, color, (darkGround ? 0.9 : 0.5) * fade);
        ctx.globalCompositeOperation = 'source-over';
        // The tail is three fading dots, in the map's own language of marks.
        ctx.fillStyle = color;
        for (var d = 3; d >= 1; d--) {
          var qd = easeInOut(Math.max(0, p - d * 0.035));
          ctx.globalAlpha = fade * (0.56 - d * 0.14);
          ctx.beginPath();
          ctx.arc(x + (mx - x) * qd, y + (my - y) * qd, Math.max(0.7, (2.2 - d * 0.4) * size), 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.globalAlpha = fade;
        ctx.fillStyle = darkGround ? palette.ink : color;
        ctx.beginPath();
        ctx.arc(bx, by, 2.2 * size, 0, Math.PI * 2);
        ctx.fill();
      });
      ctx.globalAlpha = 1;
    }

    /* Each ring fades in after the one inside it, in reading order: the
       core, the orbit, the claims, the results, then the words. One layer
       never cuts through a mark or a letter, and the whole opening is under
       a second. */
    var reveal = 1, revealMs = 1e9;
    var REVEAL_DELAY = [0, 90, 180, 270, 450], REVEAL_FADE = 420;
    var REVEAL_END = REVEAL_DELAY[REVEAL_DELAY.length - 1] + REVEAL_FADE;
    function revealAlpha(layer) {
      if (reveal >= 1) return 1;
      var t = (revealMs - REVEAL_DELAY[layer]) / REVEAL_FADE;
      if (t <= 0) return 0;
      return t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
    }
    function revealLayer(kind) {
      if (kind === 'universe' || kind === 'integration_surface') return 0;
      if (kind === 'problem' || kind === 'paper') return 1;
      if (kind === 'public_claim' || kind === 'mathematical_object') return 2;
      return 3;
    }
    function startReveal() {
      if (reduceMotion || !window.requestAnimationFrame || document.hidden) {
        if (reveal < 1) { reveal = 1; draw(); }
        return;
      }
      var start = null;
      reveal = 0;
      revealMs = 0;
      var step = function (now) {
        if (start === null) start = now;
        revealMs = now - start;
        if (revealMs >= REVEAL_END) reveal = 1;
        draw();
        if (reveal < 1) requestMotionFrame(step);
      };
      requestMotionFrame(step);
    }
    /* Reduced motion is followed live: turning it on part-way stops the
       opening, the evidence moment and the focus fade, and draws the still
       map. (The tests' stand-in matchMedia has no listener, hence the
       guards.) */
    var reduceQuery = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
    function followReduceMotion() {
      reduceMotion = !!(reduceQuery && reduceQuery.matches);
      if (!reduceMotion) return;
      reveal = 1;
      if (pulse.frame && window.cancelAnimationFrame) cancelMotionFrame(pulse.frame);
      pulse.frame = 0;
      pulse.ms = 1e9;
      if (focusFrame && window.cancelAnimationFrame) cancelMotionFrame(focusFrame);
      focusFrame = 0;
      focusFade = null;
      focusHeld = -1;
      focusMix = 1;
      if (overviewReady) draw();
    }
    if (reduceQuery && typeof reduceQuery.addEventListener === 'function') {
      reduceQuery.addEventListener('change', followReduceMotion);
    } else if (reduceQuery && typeof reduceQuery.addListener === 'function') {
      reduceQuery.addListener(followReduceMotion);
    }
    function cameraTo(target, fitted) {
      var w = canvas.clientWidth, h = canvas.clientHeight;
      if (cameraFrame && window.cancelAnimationFrame) cancelMotionFrame(cameraFrame);
      cameraFrame = 0;
      var finish = function () {
        view.k = target.k; view.tx = target.tx; view.ty = target.ty;
        viewIsFitted = !!fitted;
        draw();
      };
      if (reduceMotion || !window.requestAnimationFrame || !w) { finish(); return; }
      var from = { k: view.k, cx: (w / 2 - view.tx) / view.k, cy: (h / 2 - view.ty) / view.k };
      var to = { k: target.k, cx: (w / 2 - target.tx) / target.k, cy: (h / 2 - target.ty) / target.k };
      // Slow in and slow out, as statistical-graphics studies recommend for
      // a move the eye must follow (Heer and Robertson 2007); a deeper zoom
      // takes a little longer, never more than two thirds of a second.
      var start = null;
      var duration = Math.min(650, 300 + 120 * Math.abs(Math.log(to.k / from.k) / Math.LN2));
      viewIsFitted = false;
      var step = function (now) {
        if (start === null) start = now;
        var t = Math.min(1, (now - start) / duration);
        var e = easeInOut(t);
        var k = from.k * Math.pow(to.k / from.k, e);
        var cx = from.cx + (to.cx - from.cx) * e, cy = from.cy + (to.cy - from.cy) * e;
        view.k = k; view.tx = w / 2 - cx * k; view.ty = h / 2 - cy * k;
        draw();
        if (t < 1) cameraFrame = requestMotionFrame(step);
        else { cameraFrame = 0; finish(); }
      };
      cameraFrame = requestMotionFrame(step);
    }
    function frameOf(indices, maxK) {
      var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      indices.forEach(function (i) {
        var n = nodes[i];
        if (n.x < minX) minX = n.x;
        if (n.x > maxX) maxX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.y > maxY) maxY = n.y;
      });
      var w = canvas.clientWidth, h = canvas.clientHeight, pad = 56;
      var k = Math.min((w - pad * 2) / Math.max(1, maxX - minX), (h - pad * 2) / Math.max(1, maxY - minY));
      k = Math.max(fittedScale, Math.min(maxK, k));
      return { k: k, tx: w / 2 - k * (minX + maxX) / 2, ty: h / 2 - k * (minY + maxY) / 2 };
    }
    function fitAnimated() {
      var keep = { k: view.k, tx: view.tx, ty: view.ty };
      fit();
      var target = { k: view.k, tx: view.tx, ty: view.ty };
      view.k = keep.k; view.tx = keep.tx; view.ty = keep.ty;
      cameraTo(target, true);
    }

    function centerOn(i) {
      if (i < 0 || !nodes[i]) return;
      var n = nodes[i];
      // The core and the verification hubs reach across the whole ring, so
      // opening one frames the field rather than the hub.
      if (n.kind === 'universe' || n.kind === 'integration_surface') { fitAnimated(); return; }
      // A problem frames its whole sector: papers, claims and its band.
      if (n.kind === 'problem' && n.sector) {
        var members = [i];
        for (var j = 0; j < nodes.length; j++) {
          if (j !== i && visible(nodes[j]) && nodes[j].sector &&
              sectorProblems(nodes[j]).indexOf(n.sector) !== -1 && nodes[j].kind !== 'lean_module') {
            members.push(j);
          }
        }
        cameraTo(frameOf(members, 3), false);
        return;
      }
      // A result is shown close enough to read its neighbours' numbers.
      var k = n.kind === 'paper_statement' ? Math.max(view.k, 3.2) : (view.k < 1.1 ? 1.6 : view.k);
      cameraTo({ k: k, tx: canvas.clientWidth / 2 - n.x * k, ty: canvas.clientHeight / 2 - n.y * k }, false);
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
      // A paper result keeps its whole paper lit: the run of the band that
      // paper occupies, in the order the stepper walks it.
      if (n.kind === 'paper_statement' && paperSequence[n.paperId]) {
        paperSequence[n.paperId].forEach(function (k) { set[k] = true; });
      }
      // And the same result where the other paper states it.
      (n.twins || []).forEach(function (t) { set[t.at] = true; });
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
        // A queued result carries a pip in the ground colour, so colour is
        // never the only thing telling it from a replayed one.
        if (tier === 'lean' && r * 0.38 >= 0.8) {
          ctx.beginPath();
          ctx.arc(x, y, r * 0.38, 0, Math.PI * 2);
          ctx.fillStyle = palette.ground;
          ctx.fill();
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
      // No Lean statement is not Lean's colour: it is drawn in the quiet ink.
      if (n.kind === 'paper_statement' && n.tier === 'none') return palette.faint;
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

    // Camera and animation frames change positions and ink, not topology.
    // Reuse the same ordered connections until their inputs change.
    var frameGraphCache = null;
    function frameGraph(focus) {
      var narrow = canvas.clientWidth < 600;
      if (frameGraphCache && frameGraphCache.nodes === nodes &&
          frameGraphCache.focus === focus && frameGraphCache.narrow === narrow) return frameGraphCache;
      var near = neighbourSet(focus);
      var hot = incidentEdges(focus), hotSet = {};
      hot.forEach(function (at) { hotSet[at] = true; });
      var quiet = [], availableEdges = 0;
      for (var i = 0; i < edges.length; i++) {
        var ea = nodes[edges[i][0]], eb = nodes[edges[i][1]];
        if (!ea || !eb || !visible(ea) || !visible(eb)) continue;
        availableEdges++;
        if (overviewEdge(i) && !hotSet[i]) quiet.push(i);
      }
      frameGraphCache = { nodes: nodes, focus: focus, narrow: narrow, near: near,
        hot: hot, quiet: quiet, availableEdges: availableEdges, threads: pulseThreads(focus, hot) };
      return frameGraphCache;
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
      if (f.kind === 'integration_surface') return 'on';
      if (f.kind === 'universe') return 'rest';
      if (f.sector && sectorProblems(f).indexOf(b.sector) !== -1) return 'on';
      return 'off';
    }
    function evidenceColor(key) {
      return key === 'replayed' ? palette.integration_surface :
        key === 'none' ? palette.faint : palette.paper_statement;
    }

    /* A selected result threads its paper's results in order, row by row,
       the way a star chart draws a constellation. Long jumps between rows
       are left out. */
    function drawConstellation(focus) {
      if (focus < 0 || nodes[focus].kind !== 'paper_statement') return;
      var k = view.k;
      // A result stated in both papers threads across to where the other
      // paper states it: one dashed line per counterpart.
      var twins = nodes[focus].twins || [];
      if (twins.length) {
        var f = nodes[focus];
        ctx.globalAlpha = 0.9;
        ctx.strokeStyle = palette.integration_surface;
        ctx.lineWidth = 1.2;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        for (var t = 0; t < twins.length; t++) {
          var m = nodes[twins[t].at];
          if (!m || !visible(m)) continue;
          ctx.moveTo(f.x * k + view.tx, f.y * k + view.ty);
          ctx.lineTo(m.x * k + view.tx, m.y * k + view.ty);
        }
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.globalAlpha = 1;
      }
      var seq = paperSequence[nodes[focus].paperId];
      if (!seq || seq.length < 2) return;
      var limit = 26 * k;
      ctx.globalAlpha = 0.55;
      ctx.strokeStyle = palette.edgeHot;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (var j = 1; j < seq.length; j++) {
        var a = nodes[seq[j - 1]], b = nodes[seq[j]];
        var ax = a.x * k + view.tx, ay = a.y * k + view.ty, bx = b.x * k + view.tx, by = b.y * k + view.ty;
        if ((ax - bx) * (ax - bx) + (ay - by) * (ay - by) > limit * limit) continue;
        ctx.moveTo(ax, ay);
        ctx.lineTo(bx, by);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    /* The ground of the field: a soft light at the centre, the way a chart
       of the sky darkens toward its rim, and one faint orbit through the
       problems so the ring reads as a single structure. */
    function drawGround(w, h) {
      var outer = 0;
      for (var i = 0; i < bands.length; i++) outer = Math.max(outer, bandRadii(bands[i])[1] || 0);
      if (!outer) return;
      // The ground stays flat: no light at the centre, which would read as
      // emphasis the data does not carry.
      var k = view.k;
      var orbit = 0, count = 0;
      for (var pid in problemIndex) {
        var p = nodes[problemIndex[pid]];
        if (!p || !visible(p)) continue;
        orbit += Math.sqrt(p.x * p.x + p.y * p.y);
        count++;
      }
      if (!count) return;
      ctx.globalAlpha = 0.7 * revealAlpha(1);
      ctx.strokeStyle = palette.edge;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(view.tx, view.ty, orbit / count * k, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    /* A problem is drawn as a small copy of the core, a ring round a point,
       in ink: colour on the field stays with the evidence, and the only
       colour a problem carries is its own evidence ring. */
    function drawProblemMark(n, x, y, r, ink, withRing) {
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = palette.ground;
      ctx.fill();
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = ink;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(x, y, Math.max(1.4, r * 0.28), 0, Math.PI * 2);
      ctx.fillStyle = ink;
      ctx.fill();
      if (withRing) drawProblemRing(n, x, y, r);
    }

    /* Each problem's marker carries its own evidence: a thin ring around
       the disc, split in proportion like its band's gauge. */
    function drawProblemRing(n, x, y, r) {
      var b = null;
      for (var i = 0; i < bands.length; i++) if (bands[i].sector === n.sector) { b = bands[i]; break; }
      if (!b || lensOff.paper_statement) return;
      var total = 0, key;
      for (key in b.evidence) total += b.evidence[key];
      if (!total) return;
      var at = -Math.PI / 2, rr = r + 3.5;
      ctx.lineWidth = 2.4;
      ctx.lineCap = 'butt';
      for (var j = 0; j < EVIDENCE_ORDER.length; j++) {
        key = EVIDENCE_ORDER[j];
        if (!b.evidence[key]) continue;
        var to = at + Math.PI * 2 * b.evidence[key] / total;
        ctx.strokeStyle = evidenceColor(key);
        var keepAlpha = ctx.globalAlpha;
        ctx.globalAlpha = keepAlpha * EVIDENCE_GAUGE_ALPHA[key];
        ctx.beginPath();
        ctx.arc(x, y, rr, at, to);
        ctx.stroke();
        ctx.globalAlpha = keepAlpha;
        at = to;
      }
    }

    /* The claims ring is drawn the way the results ring is: each block of
       claims on a faint plate, so the field reads as rings of segments. A
       problem's block travels on its band, a shared block on its caption. */
    function drawClaimPlate(shape, state) {
      var k = view.k, pad = 9;
      var lo = shape[0] - pad / shape[2], hi = shape[1] + pad / shape[2];
      var outerR = (shape[3] + pad) * k, innerR = Math.max(0, (shape[2] - pad) * k);
      var ra = revealAlpha(2);
      ctx.globalAlpha = (state === 'off' ? dimmed(0.35) : 1) * ra;
      ctx.fillStyle = palette.plate;
      ctx.beginPath();
      ctx.arc(view.tx, view.ty, outerR, lo, hi);
      ctx.arc(view.tx, view.ty, innerR, hi, lo, true);
      ctx.closePath();
      ctx.fill();
      // Its two long edges are ruled, like an engraved scale.
      ctx.globalAlpha = (state === 'off' ? 0.6 - 0.4 * focusMix : 0.6) * ra;
      ctx.strokeStyle = palette.edge;
      ctx.lineWidth = 0.8;
      ctx.beginPath();
      ctx.arc(view.tx, view.ty, outerR, lo, hi);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(view.tx, view.ty, innerR, lo, hi);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    /* A selected or hovered object lights its whole sector as one slice,
       from just inside the orbit out past its band, so a problem reads at
       once with its papers, its claims and its results. */
    function drawSectorSlice(focus) {
      if (focus < 0 || !bands.length) return;
      var f = nodes[focus];
      if (!f || f.kind === 'universe' || f.kind === 'integration_surface') return;
      var pids = sectorProblems(f);
      if (!pids.length) return;
      var k = view.k, orbit = 0, count = 0;
      for (var pid in problemIndex) {
        var p = nodes[problemIndex[pid]];
        if (p) { orbit += Math.sqrt(p.x * p.x + p.y * p.y); count++; }
      }
      if (!count) return;
      var inner = Math.max(0, (orbit / count - 34) * k);
      for (var i = 0; i < bands.length; i++) {
        var b = bands[i];
        if (pids.indexOf(b.sector) === -1) continue;
        var outer = (bandRadii(b)[1] + 12) * k;
        if (!(outer > inner)) continue;
        // One flat wash, edged with a hairline, like a highlighted region on
        // a printed chart.
        ctx.fillStyle = palette.halo;
        ctx.globalAlpha = 0.5 * focusMix;
        ctx.beginPath();
        ctx.arc(view.tx, view.ty, outer, b.lo - 0.012, b.hi + 0.012);
        ctx.arc(view.tx, view.ty, inner, b.hi + 0.012, b.lo - 0.012, true);
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 0.3 * focusMix;
        ctx.lineWidth = 0.75;
        ctx.strokeStyle = palette.ink;
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }
    function drawClaimPlates(focus) {
      if (lensOff.public_claim) return;
      var f = focus >= 0 ? nodes[focus] : null;
      var quiet = !f || f.kind === 'universe' || f.kind === 'integration_surface';
      var near = f ? sectorProblems(f) : [];
      for (var i = 0; i < bands.length; i++) {
        if (bands[i].claims) drawClaimPlate(bands[i].claims, quiet ? 'rest' : near.indexOf(bands[i].sector) !== -1 ? 'on' : 'off');
      }
      for (var j = 0; j < captions.length; j++) {
        var c = captions[j];
        if (!c.claims) continue;
        var pair = (c.sector || '').split('+');
        var touched = pair.some(function (pid) { return near.indexOf(pid) !== -1; });
        drawClaimPlate(c.claims, quiet ? 'rest' : touched ? 'on' : 'off');
      }
    }

    function drawBandPlates(focus) {
      if (!bands.length || lensOff.paper_statement) return;
      var k = view.k;
      for (var i = 0; i < bands.length; i++) {
        var b = bands[i], radii = bandRadii(b);
        if (!isFinite(radii[0])) continue;
        var state = bandState(b, focus);
        var pad = 6;
        var ra = revealAlpha(3);
        ctx.globalAlpha = (state === 'off' ? dimmed(0.35) : 1) * ra;
        ctx.fillStyle = palette.plate;
        ctx.beginPath();
        ctx.arc(view.tx, view.ty, (radii[1] + pad) * k, b.lo, b.hi);
        ctx.arc(view.tx, view.ty, Math.max(0, (radii[0] - pad) * k), b.hi, b.lo, true);
        ctx.closePath();
        ctx.fill();
        // Both long edges are ruled. The evidence gauge, which repeats what
        // the dots and the title already say, shows only for a band in
        // focus.
        ctx.globalAlpha = (state === 'off' ? 0.6 - 0.4 * focusMix : 0.6) * ra;
        ctx.strokeStyle = palette.edge;
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.arc(view.tx, view.ty, (radii[1] + pad) * k, b.lo, b.hi);
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(view.tx, view.ty, Math.max(0, (radii[0] - pad) * k), b.lo, b.hi);
        ctx.stroke();
        var total = 0, key;
        for (key in b.evidence) total += b.evidence[key];
        var at = b.lo, gaugeR = (radii[0] - pad - 5) * k;
        if (total && gaugeR > 0 && state === 'on') {
          ctx.lineWidth = Math.max(1.6, 2.4 * Math.min(1, k / 0.6));
          ctx.lineCap = 'butt';
          var hair = 1.5 / gaugeR;
          for (var j = 0; j < EVIDENCE_ORDER.length; j++) {
            key = EVIDENCE_ORDER[j];
            if (!b.evidence[key]) continue;
            var to = at + (b.hi - b.lo) * b.evidence[key] / total;
            ctx.globalAlpha = (state === 'off' ? dimmed(0.35) : 1) * EVIDENCE_GAUGE_ALPHA[key];
            ctx.strokeStyle = evidenceColor(key);
            // A part too short for its hair of air is drawn whole; an arc
            // whose end came before its start would run the long way round.
            var from = at + (at > b.lo ? hair : 0), till = to - (to < b.hi - 1e-9 ? hair : 0);
            if (till <= from) { from = at; till = to; }
            ctx.beginPath();
            ctx.arc(view.tx, view.ty, gaugeR, from, till);
            ctx.stroke();
            at = to;
          }
        }
        // A selected problem threads a guide out to its band, through its
        // claims; at rest the sector's alignment says the same thing.
        var p = problemIndex[b.sector] !== undefined ? nodes[problemIndex[b.sector]] : null;
        if (p && visible(p) && gaugeR > 0 && state === 'on') {
          var dist = Math.sqrt(p.x * p.x + p.y * p.y) || 1;
          var ux = p.x / dist, uy = p.y / dist;
          var from = dist * k + p.r * radiusScale() + 3;
          ctx.globalAlpha = 0.9;
          ctx.strokeStyle = palette.edge;
          ctx.lineWidth = 1;
          ctx.setLineDash([2, 4]);
          ctx.beginPath();
          ctx.moveTo(view.tx + ux * from, view.ty + uy * from);
          ctx.lineTo(view.tx + ux * (gaugeR - 4), view.ty + uy * (gaugeR - 4));
          ctx.stroke();
          ctx.setLineDash([]);
        }
      }
      // Graduations: a fine tick in each gap between two sectors, across the
      // results ring, the way a dial marks its divisions.
      var sorted = bands.slice().sort(function (a, c) { return a.lo - c.lo; });
      var r0 = Infinity, r1 = 0;
      sorted.forEach(function (sb) { var rr = bandRadii(sb); r0 = Math.min(r0, rr[0]); r1 = Math.max(r1, rr[1]); });
      if (sorted.length > 1 && isFinite(r0)) {
        ctx.globalAlpha = (focus >= 0 ? 0.45 : 0.85) * revealAlpha(3);
        ctx.strokeStyle = palette.edge;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (var s = 0; s < sorted.length; s++) {
          var cur = sorted[s], nxt = sorted[(s + 1) % sorted.length];
          var mid = (cur.hi + nxt.lo + (s + 1 === sorted.length ? Math.PI * 2 : 0)) / 2;
          var cx = Math.cos(mid), sy = Math.sin(mid);
          ctx.moveTo(view.tx + cx * (r0 - 16) * k, view.ty + sy * (r0 - 16) * k);
          ctx.lineTo(view.tx + cx * (r1 + 12) * k, view.ty + sy * (r1 + 12) * k);
        }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }

    /* Close in, a result shows its printed number above its dot, so a band
       reads as the paper's own sequence. */
    function drawStatementNumbers(focus, near, searching, w, h) {
      if (view.k < 3 || lensOff.paper_statement) return;
      ctx.font = '600 9px ' + SERIF;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      ctx.lineWidth = 3;
      ctx.lineJoin = 'round';
      var rs = radiusScale();
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (n.kind !== 'paper_statement' || !n.num || !visible(n) || i === focus) continue;
        if (focus >= 0 && !near[i]) continue;
        if (searching && !matches(n)) continue;
        var x = n.x * view.k + view.tx, y = n.y * view.k + view.ty;
        if (x < -10 || y < -10 || x > w + 10 || y > h + 10) continue;
        var ly = y - n.r * rs - 4;
        var half = ctx.measureText(n.num).width / 2 + 1;
        var box = { x0: x - half, x1: x + half, y0: ly - 8, y1: ly + 2, owner: i };
        if (labelCollides(box)) continue;
        labelBoxes.push(box);
        ctx.strokeStyle = palette.ground;
        ctx.strokeText(n.num, x, ly);
        ctx.fillStyle = palette.faint;
        ctx.fillText(n.num, x, ly);
      }
    }
    /* Which way a label reads along the ring. Over the top it runs
       clockwise, under the bottom anticlockwise. Near either side both run
       bottom to top, so the two sides never read in opposite directions,
       but only while the letters lean at most 15 degrees past upright: a
       label just above the right-hand side reading upward would lie on its
       back. */
    function readsDownward(mid) {
      var deg = Math.atan2(Math.sin(mid), Math.cos(mid)) * 180 / Math.PI;
      if (deg >= -15 && deg <= 40) return true;
      if (deg >= 165 || deg <= -140) return false;
      return deg > 0;
    }

    function drawBandLabels(focus, w, h) {
      if (!bands.length || lensOff.paper_statement) return;
      if (!pageMode && w < 520) return;
      var k = view.k;
      var items = [];
      // A narrow field, or a ring drawn small (the teaser), keeps the number
      // and a compact count: full names would run into each other. The ring
      // decides once, by its smallest band, so one title never reads in a
      // different style from its neighbours.
      var innermost = Infinity;
      for (var r0 = 0; r0 < bands.length; r0++) {
        var outer = bandRadii(bands[r0])[1];
        if (isFinite(outer)) innermost = Math.min(innermost, outer);
      }
      var narrow = w < 560 || innermost * k < 220;
      for (var i = 0; i < bands.length; i++) {
        var b = bands[i], radii = bandRadii(b);
        if (!isFinite(radii[1])) continue;
        var state = bandState(b, focus);
        if (state === 'off') continue;
        var total = 0;
        for (var key in b.evidence) total += b.evidence[key];
        // A clear gap between the plate's edge and the first line of text.
        var base = (radii[1] + 6) * k + 15;
        var count = { text: (b.evidence.replayed || 0) + (narrow ? '/' + total : ' of ' + total + ' replayed'),
                      font: '400 11px ' + SERIF, color: palette.muted, alpha: 1 };
        var titleText = b.title ? (narrow ? b.title.split(' ')[0] : b.title) : '';
        // A count never stands without its problem's number: wherever the
        // band labels show, so does the title, short on a narrow field.
        var title = titleText ?
          { text: titleText, font: '600 12px ' + SERIF, color: palette.ink, alpha: state === 'on' ? 1 : 0.86 } : null;
        items.push({ band: b, base: base, mid: (b.lo + b.hi) / 2, count: count, title: title });
      }
      // Each label's half-width as an angle at its radius.
      function halfSpan(item) {
        ctx.font = item.count.font;
        var width = ctx.measureText(item.count.text).width;
        if (item.title) {
          ctx.font = item.title.font;
          width = Math.max(width, ctx.measureText(item.title.text).width);
        }
        return width / (2 * (item.base + 13)) + 0.02;
      }
      items.sort(function (a, b) { return a.mid - b.mid; });
      // Relax overlaps into the gaps between bands before giving anything up.
      for (var pass = 0; pass < 6; pass++) {
        for (var j = 0; j < items.length; j++) {
          var a = items[j], c = items[(j + 1) % items.length];
          var cMid = c.mid + (j + 1 === items.length ? Math.PI * 2 : 0);
          var gap = (cMid - halfSpan(c)) - (a.mid + halfSpan(a));
          if (gap >= 0) continue;
          var shift = -gap / 2;
          a.mid = Math.max(a.band.lo - 0.2, a.mid - shift);
          c.mid = Math.min(c.band.hi + 0.2, c.mid + shift);
        }
      }
      // Whatever still collides keeps its number and drops its name.
      for (var m = 0; m < items.length; m++) {
        var prev = items[(m - 1 + items.length) % items.length], cur = items[m];
        var prevMid = prev.mid - (m === 0 ? Math.PI * 2 : 0);
        if (cur.title && items.length > 1 && (cur.mid - halfSpan(cur)) < (prevMid + halfSpan(prev))) {
          cur.title.text = cur.title.text.split(' ')[0];
        }
      }
      for (var n = 0; n < items.length; n++) {
        var item = items[n], lower = readsDownward(item.mid);
        // Reading downward the name sits inside the count; upward, outside.
        var rows = item.title ? (lower ? [item.title, item.count] : [item.count, item.title]) : [item.count];
        // Under a name plate both lines step aside together. Their room
        // stays taken, so no other label moves while the reader points.
        var covered = false;
        for (var li = 0; li < rows.length; li++) {
          if (underPlate(arcRunBox(rows[li], item.base + li * 13, item.mid))) covered = true;
        }
        for (li = 0; li < rows.length; li++) {
          if (covered) labelBoxes.push(arcRunBox(rows[li], item.base + li * 13, item.mid));
          else drawArcText(rows[li], item.base + li * 13, item.mid, lower);
        }
      }
      ctx.textBaseline = 'alphabetic';
      ctx.textAlign = 'center';
    }

    /* Upright text along a circle about the field's centre, centred on an
       angle. The upper half reads clockwise, the lower half anticlockwise,
       so neither runs upside down. */
    /* Where each letter of a run sits, measured once per font and text: a
       letter's centre is the width of the text before it plus half its own,
       so the face's kerning survives on the curve. */
    var arcPlaces = {};
    function arcLetters(text) {
      var key = ctx.font + '|' + text;
      if (arcPlaces[key]) return arcPlaces[key];
      var out = { width: ctx.measureText(text).width, letters: [] };
      for (var i = 0; i < text.length; i++) {
        var ch = text.charAt(i);
        if (ch === ' ') continue;
        out.letters.push([ch, ctx.measureText(text.slice(0, i)).width + ctx.measureText(ch).width / 2]);
      }
      arcPlaces[key] = out;
      return out;
    }
    function drawArcText(row, radius, mid, lower) {
      ctx.font = row.font;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.lineWidth = 3;
      ctx.lineJoin = 'round';
      var dir = lower ? -1 : 1;
      var run = arcLetters(row.text);
      var span = run.width / radius;
      var at = mid - dir * span / 2;
      // Every halo goes down before any letter, so no halo clips the letter
      // beside it.
      for (var pass = 0; pass < 2; pass++) {
        for (var i = 0; i < run.letters.length; i++) {
          var angle = at + dir * run.letters[i][1] / radius;
          ctx.save();
          ctx.translate(view.tx + radius * Math.cos(angle), view.ty + radius * Math.sin(angle));
          ctx.rotate(angle + (lower ? -Math.PI / 2 : Math.PI / 2));
          ctx.globalAlpha = row.alpha * revealAlpha(4);
          if (pass === 0) {
            ctx.strokeStyle = palette.ground;
            ctx.strokeText(run.letters[i][0], 0, 0);
          } else {
            ctx.fillStyle = row.color;
            ctx.fillText(run.letters[i][0], 0, 0);
          }
          ctx.restore();
        }
      }
      ctx.globalAlpha = 1;
      labelBoxes.push(arcRunBox(row, radius, mid));
    }
    // A run's box, from its two ends and its middle, so later labels keep
    // clear of it.
    function arcRunBox(row, radius, mid) {
      ctx.font = row.font;
      var span = arcLetters(row.text).width / radius;
      var ends = [mid - span / 2, mid, mid + span / 2];
      var box = { x0: Infinity, x1: -Infinity, y0: Infinity, y1: -Infinity };
      for (var e = 0; e < ends.length; e++) {
        var ex = view.tx + radius * Math.cos(ends[e]), ey = view.ty + radius * Math.sin(ends[e]);
        box.x0 = Math.min(box.x0, ex - 7); box.x1 = Math.max(box.x1, ex + 7);
        box.y0 = Math.min(box.y0, ey - 7); box.y1 = Math.max(box.y1, ey + 7);
      }
      return box;
    }

    function drawCaptions(focus, w, h) {
      var i;
      /* A shared block must remain named in the fitted overview. Its
         compact callout sits beyond the band titles, on the shared edge
         between the two sectors; the line runs from the block out along
         that edge, an annotation and not a graph relationship. */
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
          var cr = Math.sqrt(c.x * c.x + c.y * c.y) || 1;
          var dx = c.x / cr, dy = c.y / cr;
          var bandOuter = 0;
          for (var bi = 0; bi < bands.length; bi++) bandOuter = Math.max(bandOuter, bandRadii(bands[bi])[1] || 0);
          var fromR = c.reach ? c.reach + 6 : cr * 1.8;
          var toR = bandOuter ? bandOuter + 58 : cr * 2.35;
          var calloutX = Math.max(captionHalf, Math.min(captionRight, dx * toR * view.k + view.tx));
          var calloutY = Math.max(14, Math.min(h - 14, dy * toR * view.k + view.ty + 8));
          // The band titles are already placed. Pushed off its own edge by
          // the zoom controls, the name steps up or down until it clears them.
          var shifts = [0, 16, -16, 32, -32, 48, -48];
          for (var sh = 0; sh < shifts.length; sh++) {
            var tryY = Math.max(14, Math.min(h - 14, calloutY + shifts[sh]));
            if (!labelCollides({ x0: calloutX - captionHalf, x1: calloutX + captionHalf, y0: tryY - 8, y1: tryY + 8 })) {
              calloutY = tryY;
              break;
            }
          }
          var calloutBox = { x0: calloutX - captionHalf, x1: calloutX + captionHalf, y0: calloutY - 8, y1: calloutY + 8 };
          labelBoxes.push(calloutBox);
          // Under a name plate the callout and its line step aside together.
          if (underPlate(calloutBox)) continue;
          ctx.globalAlpha = 0.85 * revealAlpha(4);
          ctx.strokeStyle = palette.faint;
          ctx.lineWidth = 0.65;
          ctx.setLineDash([2, 3]);
          ctx.beginPath();
          ctx.moveTo(dx * fromR * view.k + view.tx, dy * fromR * view.k + view.ty);
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
        labelBoxes.push({ x0: cx - 90, x1: cx + 90, y0: cy - 16, y1: cy + 14 });
        var align = c.reach ? 'center' : c.x > 20 ? 'left' : c.x < -20 ? 'right' : 'center';
        ctx.font = 'italic 600 11.5px ' + SERIF;
        var textWidth = ctx.measureText(c.text).width;
        if (c.sub) {
          ctx.font = 'italic 400 10.5px ' + SERIF;
          textWidth = Math.max(textWidth, ctx.measureText(c.sub).width);
        }
        var textLeft = align === 'left' ? cx : align === 'right' ? cx - textWidth : cx - textWidth / 2;
        if (underPlate({ x0: textLeft - 2, x1: textLeft + textWidth + 2,
                         y0: cy - (c.sub ? 16 : 9), y1: cy + (c.sub ? 15 : 7) })) continue;
        ctx.textAlign = align;
        ctx.globalAlpha = (focus >= 0 ? 0.45 : 0.85) * revealAlpha(4);
        // Captions sit on the same paper halo as the node labels, so they
        // stay legible where they cross a ring of claims.
        ctx.lineJoin = 'round';
        ctx.lineWidth = 4;
        ctx.strokeStyle = palette.ground;
        ctx.fillStyle = palette.faint;
        ctx.font = 'italic 600 11.5px ' + SERIF;
        ctx.strokeText(c.text, cx, cy - (c.sub ? 7 : 0));
        ctx.fillText(c.text, cx, cy - (c.sub ? 7 : 0));
        if (c.sub) {
          ctx.font = 'italic 400 10.5px ' + SERIF;
          ctx.strokeText(c.sub, cx, cy + 8);
          ctx.fillText(c.sub, cx, cy + 8);
        }
        ctx.globalAlpha = 1;
      }
      ctx.textBaseline = 'alphabetic';
    }

    /* A hovered or selected result sits in a dense field, so its name goes
       beside it on a plate, toward the open side of the map, never across
       the band under it. Outward first; the other side only when it has
       more room. A name longer than the room is shortened: the card has it
       whole. */
    function namePlate(i, rs, w) {
      var n = nodes[i];
      ctx.font = '500 12px ' + SERIF;
      var text = clip(n.shortLabel, 60);
      var lx = n.x * view.k + view.tx, ly = n.y * view.k + view.ty;
      var y = ly + n.r * rs + 15;
      var tw = ctx.measureText(text).width, gap = n.r * rs + 16;
      var roomRight = w - 14 - (lx + gap), roomLeft = lx - gap - 14;
      var side = n.x >= 0 ? 1 : -1;
      var room = side > 0 ? roomRight : roomLeft;
      if (room < tw && (side > 0 ? roomLeft : roomRight) > room) {
        side = -side;
        room = side > 0 ? roomRight : roomLeft;
      }
      if (room >= 90) {
        if (tw > room) {
          text = clip(text, Math.max(8, Math.floor(text.length * room / tw) - 1));
          tw = ctx.measureText(text).width;
        }
        lx += side * (gap + tw / 2);
        y = ly + 4;
      } else if (tw > w - 28) {
        text = clip(text, Math.max(8, Math.floor(text.length * (w - 28) / tw) - 1));
      }
      var width = ctx.measureText(text).width, half = width / 2 + 6;
      var x = Math.max(half, Math.min(w - half, lx));
      var x0 = Math.max(2, Math.min(w - width - 2, x - width / 2));
      return { text: text, x: x, y: y, box: { x0: x0 - 9, x1: x0 + width + 9, y0: y - 16, y1: y + 7, owner: i } };
    }

    /* Focus, evidence, opening and camera motion share one display frame.
       Every callback advances on the same timestamp before the canvas paints;
       direct pointer/filter feedback and the no-RAF fallback stay immediate. */
    var motionFrame = 0, motionSerial = 0, motionCallbacks = {};
    var advancingMotion = false, motionNeedsPaint = false;
    function requestMotionFrame(callback) {
      var id = ++motionSerial;
      motionCallbacks[id] = callback;
      if (!motionFrame && !advancingMotion) {
        motionFrame = window.requestAnimationFrame(advanceMotion);
      }
      return id;
    }
    function cancelMotionFrame(id) {
      delete motionCallbacks[id];
    }
    function advanceMotion(now) {
      motionFrame = 0;
      var due = motionCallbacks;
      motionCallbacks = {};
      advancingMotion = true;
      Object.keys(due).forEach(function (id) { due[id](now); });
      advancingMotion = false;
      if (motionNeedsPaint) {
        motionNeedsPaint = false;
        paint();
      }
      if (!motionFrame && Object.keys(motionCallbacks).length) {
        motionFrame = window.requestAnimationFrame(advanceMotion);
      }
    }
    function draw() {
      if (advancingMotion) { motionNeedsPaint = true; return; }
      paint();
    }
    function paint() {
      // The backing store stops at twice the CSS size, as the plait's does: a
      // three-times screen would paint 2.25 times the pixels on every camera
      // frame for no visible gain. The glow sprites draw in CSS pixels.
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      var w = canvas.clientWidth, h = canvas.clientHeight;
      if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
        canvas.width = Math.round(w * dpr);
        canvas.height = Math.round(h * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      var searching = query.length >= 2;
      // Dimming, the lit sector and the threads follow the focus, and for a
      // moment after it goes, the object just let go of; plates follow the
      // pointer.
      var focus = trackFocus(focusIndex());
      var graph = frameGraph(focus), near = graph.near;
      var i, n, x, y;
      /* A phone fits the whole field into a few hundred pixels; marks drawn
         at desktop size would then cover each other, so they shrink with the
         fitted scale and grow back as the reader zooms in. */
      var rs = radiusScale();
      labelBoxes = [];
      // The hovered and the selected result name themselves on plates. The
      // plates are placed first, so the band titles and the shared callout,
      // lettered before the labels, can step aside from under them.
      plateBoxes = [];
      [hover, selected].forEach(function (at, k) {
        if (at < 0 || (k === 1 && at === hover)) return;
        var pn = nodes[at];
        if (!pn || !visible(pn) || (pn.kind !== 'paper_statement' && pn.kind !== 'public_claim')) return;
        var px = pn.x * view.k + view.tx, py = pn.y * view.k + view.ty;
        if (px < -60 || py < -60 || px > w + 60 || py > h + 60) return;
        plateBoxes.push(namePlate(at, rs, w).box);
      });

      drawGround(w, h);
      drawSectorSlice(focus);
      drawClaimPlates(focus);
      drawBandPlates(focus);

      var hot = graph.hot, quiet = graph.quiet, availableEdges = graph.availableEdges;
      var shownEdges = quiet.length + hot.length;
      drawEdgeSet(quiet, (focus >= 0 ? 0.65 - 0.35 * focusMix : 0.65) * revealAlpha(1), 0.65, palette.edge);
      drawEdgeSet(hot, 1, 1.25, palette.edgeHot);
      drawConstellation(focus);
      var threads = graph.threads;
      drawLight(focus, near, searching, threads, rs, w, h);
      // The band titles go down first, outside the rings, so every label
      // placed after them (the shared callout, the node labels) keeps clear.
      drawBandLabels(focus, w, h);


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
        alpha *= revealAlpha(revealLayer(n.kind));
        var undimmed = alpha;
        var ghost = focus >= 0 && i !== focus && !near[i];
        if (ghost) alpha = Math.min(alpha, dimmed(0.25));
        ctx.globalAlpha = alpha;
        if (i === hover || i === selected) r = n.r * rs + 1.5;
        if (n.kind === 'universe') {
          // The core is a ring round a point: the Lean source everything
          // here is checked against, drawn as a mark, not a mass.
          ctx.beginPath();
          ctx.arc(x, y, r, 0, Math.PI * 2);
          ctx.fillStyle = palette.ground;
          ctx.fill();
          ctx.lineWidth = 1.8;
          ctx.strokeStyle = palette.universe;
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(x, y, Math.max(1.6, r * 0.32), 0, Math.PI * 2);
          ctx.fillStyle = palette.universe;
          ctx.fill();
          // Two faint rings round it, the way a chart marks its pole.
          ctx.lineWidth = 1;
          ctx.strokeStyle = palette.edge;
          ctx.globalAlpha = alpha * 0.7;
          ctx.beginPath();
          ctx.arc(x, y, r + 8 * rs, 0, Math.PI * 2);
          ctx.stroke();
          ctx.globalAlpha = alpha * 0.35;
          ctx.beginPath();
          ctx.arc(x, y, r + 17 * rs, 0, Math.PI * 2);
          ctx.stroke();
          ctx.globalAlpha = alpha;
        } else if (n.id === 'integration:palomar') {
          // Palomar holds a prepared corpus, nothing submitted: a ring.
          ctx.beginPath();
          ctx.arc(x, y, r - 1, 0, Math.PI * 2);
          ctx.fillStyle = palette.ground;
          ctx.fill();
          ctx.lineWidth = 2;
          ctx.strokeStyle = palette.integration_surface;
          ctx.stroke();
        } else if (n.kind === 'problem') {
          if (ghost && focusMix < 1) {
            ctx.globalAlpha = undimmed * (1 - focusMix);
            drawProblemMark(n, x, y, r, palette.problem, true);
          }
          if (ghost) {
            ctx.globalAlpha = undimmed * focusMix * 0.5;
            drawProblemMark(n, x, y, r, palette.faint, false);
          } else {
            drawProblemMark(n, x, y, r, palette.problem, true);
          }
        } else if (ghost) {
          // Context recedes to a quiet grey, not to a muddy tint of its own
          // colour, so the focus holds the only colour on the field. While
          // the focus fades in, the colour crossfades into the grey.
          if (focusMix < 1) {
            ctx.globalAlpha = undimmed * (1 - focusMix);
            drawGlyph(x, y, r, glyphColor(n), n.tier);
            if (n.kind === 'problem') drawProblemRing(n, x, y, r);
          }
          ctx.globalAlpha = undimmed * focusMix * 0.5;
          drawGlyph(x, y, r, palette.faint, n.tier);
        } else {
          drawGlyph(x, y, r, glyphColor(n), n.tier);
          if (n.kind === 'problem') drawProblemRing(n, x, y, r);
        }
        if (i === selected) {
          // The selected object keeps a crisp ring, so it stays findable
          // when the camera moves or the field is busy.
          ctx.globalAlpha = 1;
          ctx.lineWidth = 1.5;
          ctx.strokeStyle = palette.ink;
          ctx.beginPath();
          ctx.arc(x, y, r + (n.kind === 'problem' ? 8 : 5), 0, Math.PI * 2);
          ctx.stroke();
        } else if (i === hover) {
          // A hovered mark answers with one fine ring, not a filled halo.
          ctx.globalAlpha = 0.6;
          ctx.lineWidth = 1.25;
          ctx.strokeStyle = palette.ink;
          ctx.beginPath();
          ctx.arc(x, y, r + (n.kind === 'problem' ? 7 : 5), 0, Math.PI * 2);
          ctx.stroke();
        }
        ctx.globalAlpha = 1;
      }
      drawPulse(focus, threads, rs);

      // The shared callout goes over the dots, so a band never covers it.
      drawCaptions(focus, w, h);

      /* Labels are placed, not just drawn. Each is a box on the field, taken
         in priority order: the selected or hovered object, then the
         problems, the hubs and the core, their second lines, then the rest.
         A label that would land on a placed label or on an anchor's disc is
         left out; its object still names itself on hover and in the rail. */
      ctx.textAlign = 'center';
      ctx.lineJoin = 'round';
      for (i = 0; i < nodes.length; i++) {
        n = nodes[i];
        if (!visible(n)) continue;
        if (n.kind !== 'problem' && n.kind !== 'universe' && n.kind !== 'integration_surface') continue;
        var ax = n.x * view.k + view.tx, ay = n.y * view.k + view.ty, ar = n.r * rs + 4;
        labelBoxes.push({ x0: ax - ar, x1: ax + ar, y0: ay - ar, y1: ay + ar, owner: i });
      }
      // Glyphs a problem's label must not sit on: the claims and papers that
      // crowd round each problem.
      var glyphBoxes = [];
      for (i = 0; i < nodes.length; i++) {
        n = nodes[i];
        if (!visible(n) || (n.kind !== 'public_claim' && n.kind !== 'paper')) continue;
        var gx = n.x * view.k + view.tx, gy = n.y * view.k + view.ty, gr = n.r * rs + 3;
        if (gx < -40 || gy < -40 || gx > w + 40 || gy > h + 40) continue;
        glyphBoxes.push({ x0: gx - gr, x1: gx + gr, y0: gy - gr, y1: gy + gr });
      }
      // The checking surfaces' names hang under their discs. A problem's
      // name that lands just below them reads as a third line of their
      // caption (#257's did, at the foot of the core), so that room is kept.
      var captionZones = [];
      for (i = 0; i < nodes.length; i++) {
        n = nodes[i];
        if (!visible(n) || n.kind !== 'integration_surface') continue;
        var zx = n.x * view.k + view.tx, zy = n.y * view.k + view.ty, zr = n.r * rs;
        ctx.font = '600 13px ' + SERIF;
        var zw = ctx.measureText(n.shortLabel || '').width;
        if (n.sub) { ctx.font = '400 11px ' + SERIF; zw = Math.max(zw, ctx.measureText(n.sub).width); }
        captionZones.push({ x0: zx - zw / 2 - 12, x1: zx + zw / 2 + 12,
                            y0: zy - zr - 8, y1: zy + zr + 19 + (n.sub ? 13 : 0) + 12 });
      }
      function glyphHits(box) {
        var count = 0;
        for (var g = 0; g < glyphBoxes.length; g++) {
          var q = glyphBoxes[g];
          if (box.x0 < q.x1 && box.x1 > q.x0 && box.y0 < q.y1 && box.y1 > q.y0) count++;
        }
        for (g = 0; g < captionZones.length; g++) {
          q = captionZones[g];
          if (box.x0 < q.x1 && box.x1 > q.x0 && box.y0 < q.y1 && box.y1 > q.y0) count += 10;
        }
        return count;
      }
      var candidates = [];
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
        var font = (big ? '600 13px ' : '500 12px ') + SERIF;
        ctx.font = font;
        var text = clip(n.shortLabel, isFocus ? 60 : 42);
        if (n.kind === 'problem' && (w < 600 || view.k < 1.1)) {
          var number = n.id.match(/(?:^|[:_])(\d+)$/);
          if (number) text = '#' + number[1];
        }
        var half = ctx.measureText(text).width / 2 + 6;
        var labelY = ly + n.r * rs + 15;
        if (n.kind === 'problem') {
          // Toward the centre, where the field is open: the papers sit on
          // the orbit either side of the disc and its claims outward. Along
          // the orbit, then outward, only when that spot is taken.
          var distance = Math.sqrt(n.x * n.x + n.y * n.y) || 1;
          var ux = n.x / distance, uy = n.y / distance;
          var dirs = [[-ux, -uy], [-uy, ux], [uy, -ux], [ux, uy]];
          var px = lx, py = ly, chosen = null, fewest = Infinity;
          // Each side at the disc's edge first, then one step out, past the
          // paper that sits on the orbit beside it.
          search: for (var d = 0; d < dirs.length; d++) {
            for (var step = 0; step < 2; step++) {
              var dx = dirs[d][0], dy = dirs[d][1];
              var off = n.r * rs + 10 + (half - 6) * Math.abs(dx) + 8 * Math.abs(dy) + step * 16;
              var cxp = Math.max(half, Math.min(w - half, px + dx * off)), cyp = py + dy * off + 4;
              var textHalf = half - 6;
              var trial = { x0: cxp - textHalf - 3, x1: cxp + textHalf + 3, y0: cyp - 13, y1: cyp + 5 };
              var hits = glyphHits(trial);
              if (hits < fewest) { fewest = hits; chosen = [cxp, cyp]; }
              if (!hits) break search;
            }
          }
          lx = chosen[0];
          labelY = chosen[1];
        }
        // A hovered or selected result or claim names itself on a plate,
        // where the frame's first step already placed it.
        var plate = false;
        if (isFocus && (n.kind === 'paper_statement' || n.kind === 'public_claim')) {
          var placed = namePlate(i, rs, w);
          text = placed.text;
          lx = placed.x;
          labelY = placed.y;
          half = ctx.measureText(text).width / 2 + 6;
          plate = true;
        }
        lx = Math.max(half, Math.min(w - half, lx));
        // The core and the two checking surfaces name themselves first: a
        // problem's number is also on its band's title.
        var priority = isFocus ? 10 : n.kind === 'universe' ? 9 :
          n.kind === 'integration_surface' ? 8.5 : n.kind === 'problem' ? 8 : 3;
        // The core's name goes above it when the checking surfaces below
        // take the room, as they do on a phone; a checking surface's name
        // goes beside its disc, on the side away from the other one.
        var alt = n.kind === 'universe' ? { x: lx, y: ly - n.r * rs - 9 } :
          n.kind === 'integration_surface' ? { x: n.x * view.k + view.tx, y: ly + 4,
            side: n.x < 0 ? -1 : 1, r: n.r * rs } : null;
        candidates.push({ text: text, x: lx, y: labelY, font: font, size: big ? 13 : 12, plate: plate, alt: alt,
                          color: palette.ink, priority: priority, owner: i, order: candidates.length });
        // A quieter second line: a hub's reach. It waits for room.
        if (n.sub && !isFocus && w >= 420 && n.kind !== 'problem') {
          candidates.push({ text: clip(n.sub, 36), x: lx, y: labelY + 13, font: '400 11px ' + SERIF, size: 11,
                            color: palette.faint, priority: 5, owner: i, order: candidates.length });
        }
      }
      candidates.sort(function (a, b) { return b.priority - a.priority || a.order - b.order; });
      for (var ci = 0; ci < candidates.length; ci++) {
        var cand = candidates[ci];
        ctx.font = cand.font;
        var width = ctx.measureText(cand.text).width;
        var cx0 = Math.max(2, Math.min(w - width - 2, cand.x - width / 2));
        var box = { x0: cx0 - 2, x1: cx0 + width + 2, y0: cand.y - cand.size + 1, y1: cand.y + 4, owner: cand.owner };
        if (cand.priority < 10 && cand.alt && labelCollides(box)) {
          cand.x = cand.alt.side ? cand.alt.x + cand.alt.side * (cand.alt.r + 6 + width / 2) : cand.alt.x;
          cand.y = cand.alt.y;
          cx0 = Math.max(2, Math.min(w - width - 2, cand.x - width / 2));
          box = { x0: cx0 - 2, x1: cx0 + width + 2, y0: cand.y - cand.size + 1, y1: cand.y + 4, owner: cand.owner };
        }
        if (cand.priority < 10 && labelCollides(box)) continue;
        // A new plate eases out of its mark over a sixth of a second; its
        // room is taken at once, so nothing else moves while it arrives.
        var enter = cand.plate && cand.owner === pulse.at ? 1 - Math.pow(1 - Math.min(1, pulse.ms / 160), 2) : 1;
        if (enter < 1) {
          var ownerX = nodes[cand.owner].x * view.k + view.tx;
          ctx.save();
          ctx.translate((1 - enter) * 6 * (cand.x >= ownerX ? -1 : 1), 0);
        }
        if (cand.plate) {
          box = { x0: cx0 - 9, x1: cx0 + width + 9, y0: cand.y - cand.size - 4, y1: cand.y + 7, owner: cand.owner };
          ctx.beginPath();
          if (typeof ctx.roundRect === 'function') ctx.roundRect(box.x0, box.y0, box.x1 - box.x0, box.y1 - box.y0, 6);
          else ctx.rect(box.x0, box.y0, box.x1 - box.x0, box.y1 - box.y0);
          ctx.globalAlpha = 0.94 * enter;
          ctx.fillStyle = palette.ground;
          ctx.fill();
          ctx.globalAlpha = enter;
          ctx.lineWidth = 1;
          ctx.strokeStyle = palette.faint;
          ctx.stroke();
        }
        labelBoxes.push(box);
        ctx.globalAlpha = revealAlpha(4) * enter;
        ctx.lineWidth = 4;
        ctx.strokeStyle = palette.ground;
        ctx.strokeText(cand.text, cx0 + width / 2, cand.y);
        ctx.fillStyle = cand.color;
        ctx.fillText(cand.text, cx0 + width / 2, cand.y);
        ctx.globalAlpha = 1;
        if (enter < 1) ctx.restore();
      }
      drawStatementNumbers(focus, near, searching, w, h);
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
      // A phone's fitted field shrinks the marks, down to half. Zooming in
      // past the fitted view they grow a little more, so a close band reads
      // as solid marks rather than specks; the fitted view itself is
      // unchanged.
      var k = view.k;
      // A monitor's field is drawn larger, and its marks grow with it (up to
      // half again) so a band stays a dense ring rather than spaced specks;
      // a laptop or the teaser, under about 680px, keeps the design size.
      var room = Math.min(canvas.clientWidth || 0, canvas.clientHeight || 0);
      var grow = Math.min(1.5, Math.max(1, room / 680));
      var base = Math.min(grow, Math.max(0.5, k / 0.6));
      var from = Math.max(0.6, fittedScale || 0.6);
      if (k <= from) return base;
      return Math.min(1.9, base * (1 + 0.45 * Math.log(k / from) / Math.LN2));
    }

    function nodeAt(px, py) {
      var best = -1, bestD = 14 * 14;
      var rs = radiusScale();
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (!visible(n)) continue;
        var x = n.x * view.k + view.tx, y = n.y * view.k + view.ty;
        var d = (x - px) * (x - px) + (y - py) * (y - py);
        // Every mark answers within a 24px target, however small it is drawn.
        var reach = Math.max(12, n.r * rs + 6);
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

    /* The rail at rest reads the map for a newcomer: what a dot is, the
       evidence across all results in one bar, and the eight problems as rows
       a keyboard can reach, each with its own gauge. The object inventory
       folds away below. */
    function gaugeHtml(counts, label) {
      var total = 0, key;
      for (key in counts) total += counts[key];
      if (!total) return '';
      var segs = '', words = [];
      for (var j = 0; j < EVIDENCE_ORDER.length; j++) {
        key = EVIDENCE_ORDER[j];
        if (!counts[key]) continue;
        segs += '<span class="universe-gauge__seg universe-gauge__seg--' + key + '" style="flex-grow:' + counts[key] + '"></span>';
        words.push(fmtCount(counts[key]) + ' ' + EVIDENCE_TEXT[key]);
      }
      return '<span class="universe-gauge" role="img" aria-label="' + escapeHtml((label ? label + ': ' : '') + words.join(', ')) + '">' + segs + '</span>';
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
      var parts = [];
      if (evidence.total) {
        var totals = {};
        for (var q = 0; q < nodes.length; q++) {
          if (nodes[q].kind === 'paper_statement' && visible(nodes[q])) totals[nodes[q].tier] = (totals[nodes[q].tier] || 0) + 1;
        }
        // The placard above already gives the totals; the rail names how to
        // read the field.
        parts.push('<h2 class="universe-inspector__title">Reading the map</h2>');
        var problemCount = 0;
        for (var pc = 0; pc < nodes.length; pc++) if (nodes[pc].kind === 'problem' && visible(nodes[pc])) problemCount++;
        parts.push('<p class="universe-inspector__body">From the centre out, one ring for each layer:</p>');
        parts.push('<ol class="universe-rings">' +
          '<li>' + dotHtml('universe') + '<span>the Lean universe, with Comparator and Palomar</span></li>' +
          '<li>' + dotHtml('problem') + '<span>' + problemCount + ' problems, each between its two papers</span></li>' +
          '<li>' + dotHtml('public_claim') + '<span>the claims in each problem’s record</span></li>' +
          '<li>' + dotHtml('paper_statement') + '<span>every result the papers state</span></li>' +
          '</ol>');
        parts.push('<p class="universe-inspector__body">Comparator’s colour marks a result whose Lean statement a replay has checked. ' +
          'A sector’s width is its number of results. ' +
          'Select a problem to frame its sector, or a result to read its Lean and its replay.</p>');
        parts.push('<div class="universe-overview__gauge">' + gaugeHtml(totals, 'All paper results') + '</div>');
        parts.push(evidence.html);
      } else {
        parts.push('<p class="universe-inspector__kind">The universe</p>');
        parts.push('<h2 class="universe-inspector__title">' + shown + ' objects in view</h2>');
      }
      if (bands.length) {
        var problemRows = bands.map(function (b) {
          var at = problemIndex[b.sector];
          if (at === undefined) return '';
          var total = 0;
          for (var key in b.evidence) total += b.evidence[key];
          return '<li><button type="button" class="universe-problem" data-universe-go="' + at + '">' +
            '<span class="universe-problem__name">' + escapeHtml(b.title || nodes[at].shortLabel) + '</span>' +
            '<span class="universe-problem__count">' + (b.evidence.replayed || 0) + '/' + total + '</span>' +
            gaugeHtml(b.evidence, b.title) + '</button></li>';
        }).join('');
        parts.push('<h3 class="universe-inspector__sub">Problems</h3><ul class="universe-problems">' + problemRows + '</ul>');
      }
      if (status.total) {
        parts.push('<details class="universe-connections"><summary>Headline claims by status <b>' + status.total + '</b></summary>' + status.html + '</details>');
      }
      parts.push('<details class="universe-connections"><summary>Everything in view <b>' + shown + '</b></summary>' +
        '<ul class="universe-inspector__census">' + rows + '</ul>' +
        captions.map(function (c) {
          return '<p class="universe-inspector__note">The fan inside the ring is ' + escapeHtml(c.sub || '') + ', ' + escapeHtml(c.text) + '.</p>';
        }).join('') + '</details>');
      var s = statementMeta && statementMeta.summary;
      if (s) {
        parts.push('<p class="universe-inspector__note">' + fmtCount(s.lean_declarations) +
          ' Lean declarations in ' + fmtCount(s.lean_files) + ' files state these results. Source: the ' +
          (statementMeta.ledger ? '<a href="' + escapeHtml(statementMeta.ledger) + '" data-link-kind="exogenous" rel="external noopener" target="_blank">coverage ledger</a>' : 'coverage ledger') +
          '.</p>');
      }
      parts.push('<p class="universe-inspector__hint">Press <kbd>/</kbd> to find a theorem or a Lean name; with a result selected, <kbd>←</kbd> and <kbd>→</kbd> walk its paper.</p>');
      return parts.join('');
    }

    function connectionRows(i) {
      var owner = nodes[i];
      var rows = (adj[i] || []).slice();
      rows.sort(function (p, q) {
        var a = nodes[p.to], b = nodes[q.to];
        var byKind = kindOrder(a.kind) - kindOrder(b.kind);
        if (byKind) return byKind;
        return a.label < b.label ? -1 : a.label > b.label ? 1 : 0;
      });
      // Said in words: "Replayed by Comparator", "Stated in The Binary
      // Totient Series". A short group reads as one line; a long one folds
      // under its count.
      var groups = {}, order = [];
      for (var j = 0; j < rows.length; j++) {
        var row = rows[j];
        var m = nodes[row.to];
        var key = row.rel + ':' + row.out + ':' + m.kind;
        if (!groups[key]) { groups[key] = { kind: m.kind, phrase: relPhrase(row.rel, row.out), rel: row.rel, out: row.out, items: [] }; order.push(key); }
        groups[key].items.push({ to: row.to, html: '<button type="button" class="universe-goto" data-universe-go="' + row.to + '">' +
          dotHtml(m.kind) + '<span class="universe-goto__label">' + escapeHtml(clip(m.label, 68)) + '</span></button>' });
      }
      var html = '';
      for (var g = 0; g < order.length; g++) {
        var group = groups[order[g]];
        // A paper's States list walks the same source order as Previous/Next.
        // Generic relation groups keep their kind/name order, including a
        // partial or foreign paper sequence that cannot establish this order.
        if (owner.kind === 'paper' && group.kind === 'paper_statement' &&
            group.rel === 'states' && group.out && group.items.every(function (item) {
              var statement = nodes[item.to];
              return owner.id === 'paper:' + statement.paperId &&
                typeof statement.seq === 'number' && isFinite(statement.seq);
            })) {
          group.items.sort(function (a, b) { return nodes[a.to].seq - nodes[b.to].seq; });
        }
        var items = group.items.map(function (item) { return item.html; }).join('');
        var many = (KIND_PLURAL[group.kind] || group.kind).toLowerCase();
        html += group.items.length <= 3
          ? '<li class="universe-link"><span class="universe-link__how">' + escapeHtml(group.phrase) + '</span>' +
            items + '</li>'
          : '<li class="universe-link"><details class="universe-link__fold"><summary><span class="universe-link__how">' +
            escapeHtml(group.phrase) + '</span> ' + group.items.length + ' ' + escapeHtml(many) + '</summary>' +
            items + '</details></li>';
      }
      return { html: html ? '<ul class="universe-links">' + html + '</ul>' : '', total: rows.length };
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
      if (n.paper) return { href: route(n.paper), external: false };
      if (n.page) return { href: route(n.page), external: false };
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
    // The short paper before the long record, wherever places are listed.
    var SIDE_ORDER = { short: 0, long: 1 };

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
        // One label over the list; each row is a declaration and its line.
        rows.push('<a class="universe-open' + (primary ? ' universe-open--primary' : '') + '" href="' + escapeHtml(lean[j].href) + externalAttrs() + '>' +
          (j === 0 ? '<span class="universe-open__verb">' + (lean.length > 1 ? 'In Lean, on GitHub' : 'Lean source on GitHub') + '</span>' : '') +
          '<span class="universe-open__where"><code>' + nameHtml(lean[j].name) + '</code>, line ' + lean[j].line + '</span></a>');
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
        if (selected >= 0 || hover >= 0) refreshInspector();
      }).catch(function () {
        detailLoading = false;
        detailUrl = null;
        if (selected >= 0) refreshInspector();
      });
    }

    function evidenceSentence(n) {
      var how = n.lean_status === 'exact_or_stronger' ? 'Lean states it or something stronger' : 'Lean states it exactly';
      var text;
      if (n.lean_status === 'exact' || n.lean_status === 'exact_or_stronger') {
        text = n.comparator_status === 'compared' ? how + ', and Comparator has replayed that statement.' :
          how + '; its Comparator replay is queued' + (n.comparator_queued_at ? ' since ' + n.comparator_queued_at : '') + '.';
      } else if (n.lean_status === 'modulo_named_input') {
        text = 'Lean states it under named inputs.';
      } else {
        text = 'No Lean statement is recorded for it yet.';
      }
      if (n.palomar_status === 'prepared') text += ' It is in the corpus prepared for Palomar; nothing has been submitted.';
      else if (n.palomar_status === 'pending') text += ' It joins the Palomar corpus once Comparator has replayed it.';
      return text;
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
          (s.receipts_href ? extLink(s.receipts_href, 'The receipts') + ' and the ' : 'The ') +
          (repo ? extLink(repo, 'Comparator corpus') : 'corpus') + ' are public.</p>';
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

    // A Lean name has no spaces, so a narrow card broke it mid-word
    // ("…ResidueProj / ection"). It may break after a dot or an underscore.
    function nameHtml(text) {
      var safe = escapeHtml(String(text || ''));
      if (/\s/.test(safe) || safe.length < 20) return safe;
      return safe.replace(/([._])(?=[^._])/g, '$1<wbr>');
    }

    /* ---- A paper result's card ---------------------------------------- */
    /* The card reads in the order a reader asks. What does the paper say?
       Its own words, quoted, maths typeset. How far has that been checked?
       Lean, then Comparator, then Palomar, a sentence each. What is it tied
       to? The claims and results on the same Lean theorems. The Lean code
       and the Comparator files wait one step down for whoever wants them,
       and every way out (the paper, the TeX, GitHub) is a button. */

    var ROLE_NAME = { short: 'the short paper', long: 'the long record' };
    var TAB_NAME = { short: 'Short paper', long: 'Long record' };
    function roleName(m) { return ROLE_NAME[m.side] || 'the paper'; }
    // A name the paper prints in lower case ("conditional numerical
    // thresholds") heads the card with a capital; markup and maths are left be.
    function capitalFirst(text) {
      return /^[a-z]/.test(text) ? text.charAt(0).toUpperCase() + text.slice(1) : text;
    }
    // "Theorem 6.3 (Two-channel and dyadic cap sufficiency)" → number, name.
    function splitLabel(label) {
      var text = String(label || '');
      var m = /^(.*?)\s*\((.*)\)\s*$/.exec(text);
      return m ? { number: m[1], name: m[2] } : { number: text, name: '' };
    }

    function loadExcerpts(pid) {
      var href = excerptRoutes[pid];
      if (!href || excerpts[pid] || excerptLoading[pid]) return;
      excerptLoading[pid] = true;
      fetch(route(href)).then(function (r) { return r.json(); }).then(function (payload) {
        var table = {};
        (payload.excerpts || []).forEach(function (row) {
          table[row[0]] = { name: row[1] || '', body: row[2] || '' };
        });
        excerpts[pid] = table;
        excerptLoading[pid] = false;
        refreshResultCard(pid);
      }).catch(function () {
        excerpts[pid] = {};
        excerptLoading[pid] = false;
        refreshResultCard(pid);
      });
    }
    // The quote arrives after the card: draw it again if it is still on show.
    function refreshResultCard(pid) {
      var at = selected >= 0 ? selected : hover;
      if (at < 0 || !nodes[at] || nodes[at].kind !== 'paper_statement') return;
      var shown = [at].concat((nodes[at].twins || []).map(function (t) { return t.at; }));
      if (!shown.some(function (k) { return nodes[k].paperId === pid; })) return;
      if (pageMode) { refreshInspector(); return; }
      // On the landing the column's card quotes the result once its words
      // arrive: the same pin or hover, sent again with them.
      if (companionApi) {
        stage.dispatchEvent(new CustomEvent(selected >= 0 ? 'universe:select' : 'universe:hover',
          { detail: companionSummary(at) }));
      }
    }
    // A result's quote: {name, body}; null when its paper has none; undefined
    // while the file is on its way.
    function excerptOf(i) {
      var m = nodes[i];
      if (!excerptRoutes[m.paperId]) return null;
      var table = excerpts[m.paperId];
      if (!table) { loadExcerpts(m.paperId); return undefined; }
      return table[m.id] || null;
    }

    // Every place a result is stated, the short paper first.
    function placesOf(i) {
      var places = [{ at: i, via: null }].concat((nodes[i].twins || []).map(function (t) {
        return { at: t.at, via: t.via };
      }));
      places.sort(function (a, b) {
        return (SIDE_ORDER[nodes[a.at].side] || 0) - (SIDE_ORDER[nodes[b.at].side] || 0) ||
          (nodes[a.at].seq || 0) - (nodes[b.at].seq || 0);
      });
      return places;
    }

    function quoteHtml(i, pinned) {
      var places = placesOf(i);
      var tabs = pinned ? places.slice(0, 3) : [];
      var place = places[0];
      var want = pinned && quoteAt >= 0 ? quoteAt : i;
      for (var p = 0; p < places.length; p++) if (places[p].at === want) place = places[p];
      if (!pinned) place = { at: i, via: null };
      var m = nodes[place.at];
      var html = '<figure class="universe-quote">';
      if (tabs.length > 1) {
        // Two papers state it: a tab for each, the reader's choice kept.
        html += '<div class="universe-quote__tabs" role="tablist" aria-label="Where it is stated">' +
          tabs.map(function (t) {
            var tm = nodes[t.at];
            // "Short paper, 5.2": short enough for two tabs on one line.
            return '<button type="button" role="tab" class="universe-quote__tab" aria-selected="' +
              (t.at === place.at) + '" data-universe-place="' + t.at + '" aria-label="' +
              escapeHtml(capitalFirst(roleName(tm)) + ', ' + splitLabel(tm.label).number) + '">' +
              (TAB_NAME[tm.side] || 'Paper') + ', ' + escapeHtml(tm.num || splitLabel(tm.label).number) + '</button>';
          }).join('') + '</div>';
      } else {
        html += '<figcaption class="universe-quote__from">From ' + roleName(m) +
          (m.paperTitle ? ', <cite>' + escapeHtml(m.paperTitle) + '</cite>' : '') + '</figcaption>';
      }
      var ex = excerptOf(place.at);
      if (ex === undefined) {
        html += '<p class="universe-quote__wait">Loading the paper’s words…</p>';
      } else if (ex && ex.body) {
        // The card's title already names this result; another paper's
        // statement carries its own name.
        var named = place.at !== i && ex.name ? '<p class="universe-quote__name">' + ex.name + '</p>' : '';
        html += '<blockquote class="universe-quote__text">' + named + ex.body + '</blockquote>';
      }
      if (place.via && place.via !== 'the same label') {
        html += '<p class="universe-quote__via">Shown with this result because both papers cite the same Lean theorem for it.</p>';
      }
      var go = [];
      if (m.paper) {
        // universe-open--primary is the hook the site's navigation warming
        // (docs.js) reads to fetch a pinned card's paper ahead of the click.
        go.push('<a class="universe-go universe-go--primary universe-open--primary" href="' +
          escapeHtml(route(m.paper)) + '">Read it in the paper</a>');
      }
      if (m.tex && statementMeta && statementMeta.tex_source_base) {
        go.push(extLink(statementMeta.tex_source_base + m.tex, 'TeX source' + (m.line ? ', line ' + m.line : ''), 'universe-go'));
      }
      if (pinned && place.at !== i) {
        go.push('<button type="button" class="universe-go" data-universe-go="' + place.at + '">Select it on the map</button>');
      }
      if (go.length) html += '<p class="universe-quote__go">' + go.join('') + '</p>';
      if (pinned && places.length > tabs.length) {
        html += '<p class="universe-quote__more">' + (places.length - tabs.length) +
          ' more results in the other paper cite the same Lean theorems.</p>';
      }
      return html + '</figure>';
    }

    // The namespace every declaration shares ("Erdos249257."), said once.
    function sharedNamespace(decls) {
      var first = String(decls[0].name);
      var cut = first.lastIndexOf('.');
      while (cut > 0) {
        var prefix = first.slice(0, cut + 1);
        if (decls.every(function (d) { return String(d.name).indexOf(prefix) === 0; })) return prefix;
        cut = first.lastIndexOf('.', cut - 1);
      }
      return '';
    }

    function leanListHtml(n, more) {
      var decls = n.decls || [];
      if (!decls.length) return '';
      var sigs = more && more.statements ? more.statements : {};
      var ns = sharedNamespace(decls);
      var items = decls.map(function (d) {
        var name = ns ? String(d.name).slice(ns.length) : String(d.name);
        return '<li>' + extLink(d.href, '<code>' + nameHtml(name) + '</code>', 'universe-lean__name') +
          (d.line ? '<span class="universe-lean__line">line ' + d.line + '</span>' : '') +
          (sigs[d.name] ? '<pre class="universe-lean__code"><code>' + escapeHtml(sigs[d.name]) + '</code></pre>' : '') +
          '</li>';
      });
      return '<details class="universe-lean" data-keep="lean"><summary>Show the Lean' +
        (decls.length > 1 ? ' (' + decls.length + ' theorems)' : '') + '</summary>' +
        (ns ? '<p class="universe-lean__where">Each sits in the namespace <code>' + escapeHtml(ns.slice(0, -1)) + '</code>; the names open the source on GitHub.</p>' : '') +
        '<ol class="universe-lean__list">' + items.join('') + '</ol></details>';
    }

    function checkHtml(state, station, sentence, more) {
      return '<li class="universe-check universe-check--' + state + ' universe-check--' + station.toLowerCase() + '">' +
        '<span class="universe-check__mark" aria-hidden="true"></span>' +
        '<div class="universe-check__body"><p class="universe-check__text"><b>' + station + '.</b> ' + sentence + '</p>' +
        (more || '') + '</div></li>';
    }

    function checksHtml(n, pinned) {
      var more = pinned && detail && detail.statements ? detail.statements[n.id] || null : null;
      if (pinned && !detail && detailUrl) loadDetail();
      var decls = n.decls || [];
      var rows = [];
      // Lean: how its statement stands to the printed one.
      var lean = n.lean_status || 'none';
      var count = decls.length > 1 ? ', in ' + decls.length + ' theorems' : '';
      var leanMore = '';
      if (pinned) {
        if (more && more.relation_note) {
          var typeset = more.html_mathml && more.html_mathml.relation_note;
          leanMore += '<p class="universe-check__more">How the Lean statement gives the printed one: ' +
            (typeset || noteHtml(more.relation_note)) + '</p>';
        }
        if (n.lean_reason) {
          leanMore += '<p class="universe-check__more">' + (n.lean_reason_html || noteHtml(n.lean_reason)) + '</p>';
        }
        var inputs = more && (more.named_inputs || []).length ? more.named_inputs : null;
        if (inputs) {
          leanMore += '<details class="universe-lean" data-keep="inputs"><summary>Show the named inputs (' + inputs.length + ')</summary>' +
            '<ol class="universe-lean__list">' + inputs.map(function (input) {
              return '<li>' + extLink(input.href, '<code>' + nameHtml(input.name) + '</code>', 'universe-lean__name') +
                (input.text ? '<pre class="universe-lean__code"><code>' + escapeHtml(input.text) + '</code></pre>' : '') + '</li>';
            }).join('') + '</ol></details>';
        }
        leanMore += leanListHtml(n, more);
      }
      if (lean === 'exact') {
        rows.push(checkHtml('done', 'Lean', 'It states this result exactly' + count + '.', leanMore));
      } else if (lean === 'exact_or_stronger') {
        rows.push(checkHtml('done', 'Lean', 'It states this result or something stronger' + count + '.', leanMore));
      } else if (lean === 'modulo_named_input') {
        var names = (n.named_inputs || []).length;
        rows.push(checkHtml('part', 'Lean', 'It states this result from ' +
          (names ? names + ' named input' + (names > 1 ? 's' : '') : 'named inputs') +
          ' it has not proved yet' + count + '.', leanMore));
      } else {
        rows.push(checkHtml('none', 'Lean', 'No Lean statement is recorded for it yet.', leanMore));
      }
      // Comparator: the replay of the Lean statement, with its files.
      if (n.comparator_status === 'compared') {
        var replay = (detail && detail.replay) || {};
        var runId = replay.run_id || (n.comparator_runs || [])[0] || (statementMeta && statementMeta.summary && statementMeta.summary.replay_run);
        var runHref = replay.href || (statementMeta && statementMeta.summary && statementMeta.summary.replay_href);
        var entries = n.comparator_entries || [];
        // A receipt is per corpus entry, so the acceptance is the entry's.
        var said = 'It replayed this result: from the Lean statement alone (the challenge) it checked that the proof ' +
          '(the solution) proves exactly that statement.';
        var run = runId ? (runHref ? extLink(runHref, 'run ' + escapeHtml(runId)) : 'run ' + escapeHtml(runId)) : '';
        if (entries.length) {
          said += (run ? ' In ' + run + ' its' : ' Its') + ' corpus entr' + (entries.length > 1 ? 'ies ' : 'y ') +
            entries.map(escapeHtml).join(' and ') + ' passed, the Lean kernel and nanoda ' +
            (entries.length > 1 ? 'accepting each.' : 'both accepting it.');
        } else if (run) {
          said += ' It passed in ' + run + ', the Lean kernel and nanoda both accepting its corpus entry.';
        }
        var cmpMore = '';
        if (more && (more.checks || []).length) {
          var byEntry = {}, order = [];
          more.checks.forEach(function (check) {
            if (!byEntry[check.entry]) { byEntry[check.entry] = check; order.push(check.entry); }
          });
          cmpMore = '<p class="universe-check__links">' + order.map(function (entry) {
            var check = byEntry[entry], links = [];
            if (check.receipt) links.push(extLink(check.receipt, 'Receipt', 'universe-go universe-go--small'));
            if (check.challenge) links.push(extLink(check.challenge, 'Challenge', 'universe-go universe-go--small'));
            if (check.solution) links.push(extLink(check.solution, 'Solution', 'universe-go universe-go--small'));
            return (order.length > 1 ? '<span class="universe-check__entry">' + escapeHtml(entry) + '</span>' : '') + links.join('');
          }).join('') + '</p>';
          if (more.checks.some(function (check) { return !check.same_as_lean; })) {
            cmpMore += '<p class="universe-check__more">The challenge states it in an equivalent form; the evidence record prints both.</p>';
          }
        }
        rows.push(checkHtml('done', 'Comparator', said, cmpMore));
      } else if (lean === 'exact' || lean === 'exact_or_stronger') {
        rows.push(checkHtml('queued', 'Comparator', 'Its replay is queued' +
          (n.comparator_queued_at ? ' since ' + escapeHtml(n.comparator_queued_at) : '') + '.'));
      } else {
        rows.push(checkHtml('none', 'Comparator', 'Nothing to replay until Lean states it exactly.'));
      }
      // Palomar: a prepared corpus; nothing has been submitted.
      if (n.palomar_status === 'prepared') {
        rows.push(checkHtml('ready', 'Palomar', 'It is in the corpus prepared for Palomar. Nothing has been submitted.'));
      } else if (n.palomar_status === 'pending') {
        rows.push(checkHtml('none', 'Palomar', 'It joins the prepared corpus once Comparator has replayed it.'));
      } else {
        rows.push(checkHtml('none', 'Palomar', 'It is not in the prepared corpus.'));
      }
      var html = '<h3 class="universe-inspector__sub">How it is checked</h3><ol class="universe-checks">' + rows.join('') + '</ol>';
      if (more && more.record) {
        html += '<p class="universe-check__record">' + extLink(more.record, 'The evidence record for this result', 'universe-go universe-go--small') + '</p>';
      }
      if (pinned && !detail && detailUrl) {
        html += '<p class="universe-inspector__hint">Loading the Lean statements and Comparator files…</p>';
      }
      return html;
    }

    // The claims and results that rest on the same Lean theorems; a click
    // selects one.
    function relatedHtml(i) {
      var n = nodes[i];
      var skip = {};
      skip[i] = true;
      (n.twins || []).forEach(function (t) { skip[t.at] = true; });
      var rows = [];
      (adj[i] || []).forEach(function (e) {
        var m = nodes[e.to];
        if (skip[e.to] || (m.kind !== 'paper_statement' && m.kind !== 'public_claim')) return;
        skip[e.to] = true;
        rows.push(e.to);
      });
      if (!rows.length) return '';
      rows.sort(function (a, b) {
        return kindOrder(nodes[a].kind) - kindOrder(nodes[b].kind) ||
          (nodes[a].label < nodes[b].label ? -1 : nodes[a].label > nodes[b].label ? 1 : 0);
      });
      return '<h3 class="universe-inspector__sub">On the same Lean theorems</h3><ul class="universe-related">' +
        rows.map(function (at) {
          var m = nodes[at];
          return '<li><button type="button" class="universe-goto" data-universe-go="' + at + '">' + dotHtml(m.kind) +
            '<span class="universe-goto__label">' + escapeHtml(clip(m.label, 90)) + '</span>' +
            '<span class="universe-goto__rel">' + escapeHtml(KIND_LABEL[m.kind] || m.kind) + '</span></button></li>';
        }).join('') + '</ul>';
    }

    function resultCardHtml(i, pinned) {
      var n = nodes[i];
      var lab = splitLabel(n.label);
      var ex = excerptOf(i);
      var head = '<p class="universe-inspector__kind">' + dotHtml(n.kind) + 'Paper result</p>';
      if (pinned) {
        head = '<div class="universe-inspector__head">' + head +
          '<button type="button" class="universe-inspector__clear" data-universe-clear aria-label="Close this card (Esc)">Close</button></div>';
      }
      var problem = n.sector && problemIndex[n.sector] !== undefined;
      var parts = [head,
        '<h2 class="universe-inspector__title">' + capitalFirst(ex && ex.name ? ex.name : escapeHtml(lab.name || lab.number)) + '</h2>',
        '<p class="universe-result__where">' + (lab.name ? '<b>' + escapeHtml(lab.number) + '</b> in ' : 'In ') +
          roleName(n) + (problem ? ' on ' + problemChipHtml(n.sector) : '') + '</p>'];
      if (n.tier) {
        parts.push('<p class="universe-inspector__meta"><span class="universe-chip universe-chip--' + escapeHtml(n.tier) + '">' +
          glyphHtml(n.tier) + escapeHtml(EVIDENCE_TEXT[n.tier] || n.tier) + '</span></p>');
      }
      var seq = paperSequence[n.paperId];
      if (pinned && seq && seq.length > 1 && n.seq != null) {
        // Walk the paper: the previous and next results in the order it
        // states them (the arrow keys do the same).
        parts.push('<div class="universe-step" role="group" aria-label="Step through this paper’s results">' +
          '<button type="button" class="universe-step__btn" data-universe-step="-1"' +
          (n.seq === 0 ? ' disabled' : '') + '><span aria-hidden="true">←</span> Previous</button>' +
          '<span class="universe-step__at">Result ' + (n.seq + 1) + ' of ' + seq.length + '</span>' +
          '<button type="button" class="universe-step__btn" data-universe-step="1"' +
          (n.seq === seq.length - 1 ? ' disabled' : '') + '>Next <span aria-hidden="true">→</span></button>' +
          '</div>');
      }
      parts.push(quoteHtml(i, pinned));
      if (!pinned) {
        parts.push('<p class="universe-inspector__evidence">' + escapeHtml(evidenceSentence(n)) + '</p>');
        parts.push('<p class="universe-inspector__hint">Click to keep this card; double-click to read it in the paper.</p>');
        return parts.join('');
      }
      parts.push(checksHtml(n, true));
      parts.push(relatedHtml(i));
      if (canCopy) {
        parts.push('<button type="button" class="universe-inspector__copy" data-universe-copy>Copy a link to this</button>');
      }
      return parts.join('');
    }

    function cardHtml(i, pinned) {
      var n = nodes[i];
      if (n.kind === 'paper_statement') return resultCardHtml(i, pinned);
      var head = '<p class="universe-inspector__kind">' + dotHtml(n.kind) +
        escapeHtml(KIND_LABEL[n.kind] || n.kind) + '</p>';
      if (pinned) {
        head = '<div class="universe-inspector__head">' + head +
          '<button type="button" class="universe-inspector__clear" data-universe-clear aria-label="Close this card (Esc)">Close</button></div>';
      }
      var parts = [head,
        '<h2 class="universe-inspector__title">' + nameHtml(n.label) + '</h2>'];
      var chips = '';
      if (n.status) {
        chips += '<span class="universe-chip">' + (n.tier ? glyphHtml(n.tier) : '') + escapeHtml(n.status) + '</span>';
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
          parts.push('<h3 class="universe-inspector__sub">How it connects</h3>');
          if (n.kind === 'integration_surface') {
            parts.push('<p class="universe-inspector__hint">The map lights every result it reaches.</p>');
          }
          parts.push(rows.html);
        }
        if (canCopy) {
          parts.push('<button type="button" class="universe-inspector__copy" data-universe-copy>Copy a link to this</button>');
        }
      } else {
        parts.push('<p class="universe-inspector__hint">Click to keep this card and see what it connects to; double-click to open it.</p>');
      }
      return parts.join('');
    }

    // A disclosure the reader opened (the Lean code, the named inputs) stays
    // open while the card is drawn again: when its files arrive, and from one
    // result to the next.
    var keptOpen = {};
    var panel = pageMode && stage.closest ? stage.closest('.universe-panel') : null;
    // Detail and quoted words arrive independently of the reader's actions.
    // Keep an active link's exact occurrence when those files rebuild its card.
    // Intentional pin, step and quote-tab changes retain their own focus rules.
    function refreshInspector() {
      var active = document.activeElement, href = null, occurrence = 0;
      if (inspector && active && inspector.contains(active) && active.tagName === 'A') {
        href = active.getAttribute('href');
        var before = inspector.querySelectorAll('a[href]');
        for (var i = 0; i < before.length && before[i] !== active; i++) {
          if (before[i].getAttribute('href') === href) occurrence++;
        }
      }
      renderInspector();
      if (!href) return;
      // A focusout handler may have deliberately moved focus while the old
      // node was removed. That newer choice outranks the hydrated card.
      var now = document.activeElement;
      if (now && now !== document.body && now !== document.documentElement && now !== active) return;
      var after = inspector.querySelectorAll('a[href]'), n = 0;
      for (var j = 0; j < after.length; j++) {
        if (after[j].getAttribute('href') !== href || n++ !== occurrence) continue;
        try { after[j].focus({ preventScroll: true }); } catch (err) { after[j].focus(); }
        break;
      }
    }

    function renderInspector() {
      if (!inspector) return;
      // A pinned card takes the column; the placard keeps its title and search.
      if (panel) panel.classList.toggle('is-reading', selected >= 0);
      if (inspector.querySelectorAll) {
        Array.prototype.forEach.call(inspector.querySelectorAll('details[data-keep]'), function (d) {
          keptOpen[d.getAttribute('data-keep')] = d.open;
        });
      }
      // A pinned card stays put: the pointer crossing other dots on its way
      // to the rail names them on the field and leaves the card alone.
      if (hover >= 0 && hover !== selected && selected < 0) {
        inspector.innerHTML = cardHtml(hover, false);
        inspector.classList.add('is-preview');
      } else if (selected >= 0) {
        inspector.innerHTML = cardHtml(selected, true);
        inspector.classList.remove('is-preview');
      } else {
        inspector.innerHTML = overviewHtml();
        inspector.classList.remove('is-preview');
      }
      if (inspector.querySelectorAll) {
        Array.prototype.forEach.call(inspector.querySelectorAll('details[data-keep]'), function (d) {
          if (keptOpen[d.getAttribute('data-keep')]) d.open = true;
        });
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

    /* The paper a pinned result opens in starts loading at once, so its
       button, or a double-click, opens without the wait. Where the browser
       takes speculation rules the page is prepared whole (a prerender); the
       document also goes into the cache, so a browser that declines to
       prerender (an embedded view, a busy machine) still opens it from
       there. On the map the site's navigation warming (docs.js) already
       fetches the pinned card's paper, so the map asks only for the
       prerender. One page at a time, for a pin only, never a hover, and
       never when the reader has asked to save data. */
    var warmedHref = null;
    var warmNodes = [];
    function warmPaper(i) {
      var target = i >= 0 && nodes[i] ? primaryTarget(nodes[i]) : null;
      if (!target || target.external || typeof document.createElement !== 'function' || !document.head) return;
      var connection = typeof navigator !== 'undefined' ? navigator.connection : null;
      if (connection && connection.saveData) return;
      var href;
      try { href = new URL(target.href, window.location.href).href; } catch (err) { return; }
      if (href === warmedHref) return;
      warmedHref = href;
      warmNodes.forEach(function (node) { if (node.parentNode) node.parentNode.removeChild(node); });
      warmNodes = [];
      if (typeof HTMLScriptElement !== 'undefined' && HTMLScriptElement.supports &&
          HTMLScriptElement.supports('speculationrules')) {
        var rules = document.createElement('script');
        rules.type = 'speculationrules';
        rules.textContent = JSON.stringify({ prerender: [{ source: 'list', urls: [href] }] });
        warmNodes.push(rules);
      }
      if (!pageMode) {
        var link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = href;
        warmNodes.push(link);
      }
      warmNodes.forEach(function (node) { document.head.appendChild(node); });
    }

    function pin(i, center) {
      var restoreFocus = inspector && inspector.contains(document.activeElement);
      if (i !== selected) quoteAt = -1;
      selected = i;
      hover = -1;
      canvas.classList.remove('is-over');
      if (i >= 0) pendingId = null;
      warmPaper(i);
      renderInspector();
      if (restoreFocus) {
        var nextFocus = inspector.querySelector('[data-universe-clear]') || searchIn;
        if (nextFocus) nextFocus.focus({ preventScroll: true });
      }
      updateHash();
      if (center && i >= 0) centerOn(i);
      draw();
    }

    // Where the card sits under the map (a phone, a narrow window), a tap on
    // a dot brings the card into view; the map is one scroll back up. Beside
    // the map, or already on screen, nothing moves.
    function revealCard() {
      if (!inspector || !inspector.getBoundingClientRect || !inspector.scrollIntoView) return;
      var card = inspector.getBoundingClientRect();
      var field = canvas.getBoundingClientRect();
      if (card.top < field.bottom - 4 || card.top < (window.innerHeight || 0) * 0.7) return;
      inspector.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
    }

    function stepStatement(dir) {
      if (selected < 0 || !nodes[selected]) return;
      var n = nodes[selected];
      var seq = paperSequence[n.paperId];
      if (!seq || n.seq == null) return;
      var at = n.seq + dir;
      if (at < 0 || at >= seq.length) return;
      pin(seq[at], true);
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
      if (n.kind === 'paper_statement' && EVIDENCE_TEXT[n.tier]) text += ', ' + EVIDENCE_TEXT[n.tier];
      // With the companion beside the drawing the column reads the object in
      // full, so the caption only names it, in one line, and its box never
      // grows.
      if (companionApi) text = clip(n.label, 34);
      caption.textContent = text;
      caption.classList.add('is-shown');
    }

    /* ---- Companion (landing) -----------------------------------------
       Beside the teaser the landing lists the eight problems. A companion
       script (universe-companion.js) turns that column into a page for
       whatever the pointer is over: the map announces each object it hovers
       and lights a problem's sector when the column asks. It loads only on a
       fine pointer, and only where the list stands beside the drawing. */
    var companionApi = null;

    function companionSummary(i) {
      var n = nodes[i];
      var decls = n.decls || [];
      var target = primaryTarget(n);
      // A result's own words, once its paper's excerpts are here; asking
      // starts the fetch, and the card is sent again when they arrive.
      var quote = n.kind === 'paper_statement' ? excerptOf(i) : null;
      return {
        quote: quote ? quote.body : null,
        id: n.id, kind: n.kind, kindLabel: KIND_LABEL[n.kind] || n.kind,
        label: n.label, sector: n.sector || null, tier: n.tier || null,
        evidence: n.kind === 'paper_statement' ? (EVIDENCE_TEXT[n.tier] || null) : null,
        lean_status: n.lean_status || null,
        comparator_queued_at: n.comparator_queued_at || null,
        status: n.status || null, statement: n.statement || null,
        side: n.side || null, paperId: n.paperId || null, paperTitle: n.paperTitle || null,
        href: target && !target.external ? target.href : null,
        // The Lean source line on GitHub: the first declaration's, else the
        // object's own.
        github: (decls[0] && decls[0].href) || (n.lean && n.lean.length ? n.lean[0].href : null) ||
          n.source_github || null,
        mapHref: route('universe.html#o=' + encodeURIComponent(n.id))
      };
    }

    /* Beside the problems column a click pins a result instead of leaving
       the page: the column's card holds it, with buttons to its place in
       the paper, its Lean source on GitHub and the full map. The pinned dot
       keeps its ring; a click on it again, or on empty ground, lets it go.
       Its moment has already played under the pointer. */
    function pinInTeaser(i) {
      selected = i;
      if (i >= 0) pulsedSelection = i;
      warmPaper(i);
      draw();
      if (companionApi) {
        stage.dispatchEvent(new CustomEvent('universe:select', { detail: i >= 0 ? companionSummary(i) : null }));
        // Let go under the pointer, the card reads what the pointer is on.
        if (i < 0 && hover >= 0) announce(hover);
      }
    }

    function companionTallies() {
      var out = {};
      nodes.forEach(function (n, i) {
        if (n.kind === 'problem' && n.sector) {
          out[n.sector] = { index: i, results: 0, replayed: 0, lean: 0, modulo: 0, none: 0, claims: 0 };
        }
      });
      nodes.forEach(function (n) {
        var t = n.sector ? out[n.sector] : null;
        if (!t) return;
        if (n.kind === 'paper_statement') {
          t.results++;
          if (t[n.tier] !== undefined) t[n.tier]++;
        } else if (n.kind === 'public_claim') {
          t.claims++;
        }
      });
      return out;
    }

    // The column asks for a problem's sector to be lit (a row or a chip under
    // the pointer, or a row's link in focus); null lets the drawing rest.
    function lightProblem(sector) {
      var i = sector && problemIndex[sector] !== undefined ? problemIndex[sector] : -1;
      if (i === hover) return;
      hover = i;
      draw();
      showCaption(i);
    }

    function announce(i) {
      if (!companionApi) return;
      stage.dispatchEvent(new CustomEvent('universe:hover', { detail: i >= 0 ? companionSummary(i) : null }));
    }

    function loadCompanion(spec) {
      if (pageMode || companionApi || !spec || !spec.script) return;
      var section = stage.closest ? stage.closest('section') : null;
      var host = section ? section.querySelector('.home-split__text') : null;
      if (!host || !host.querySelector('li.home-problem[data-problem-id]')) return;
      if (!window.matchMedia || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
      if (typeof window.CustomEvent !== 'function') return;
      companionApi = {
        stage: stage, host: host, route: route, reduceMotion: reduceMotion,
        dataUrl: route(spec.data), tallies: companionTallies(), light: lightProblem,
        // The column lets a pin go (Escape, leaving the band, another problem).
        release: function () { if (selected >= 0) { selected = -1; draw(); } }
      };
      var style = document.createElement('link');
      style.rel = 'stylesheet';
      style.href = route(spec.style);
      document.head.appendChild(style);
      var script = document.createElement('script');
      script.src = route(spec.script);
      script.async = true;
      script.onload = function () {
        if (window.PlectisUniverseCompanion) window.PlectisUniverseCompanion.attach(companionApi);
      };
      document.head.appendChild(script);
    }

    /* ---- Data --------------------------------------------------------- */

    function degreeBonus(kind, degree) {
      // Every kind keeps one size. A mark that grew with its connections
      // would suggest a quantity the legend never names.
      return 0;
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
      if (data.excerpts) {
        excerptRoutes = {};
        data.excerpts.forEach(function (pair) { excerptRoutes[pair[0]] = pair[1]; });
      }
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
          row.lean_reason_html = n.lean_reason_html || null;
          row.comparator_queued_at = n.comparator_queued_at || null;
          row.named_inputs = n.named_inputs || [];
          row.comparator_entries = n.comparator_entries ||
            (n.cmp_entries || []).map(function (k) { return statementMeta ? statementMeta.comparator_entries[k] : String(k); });
          row.comparator_runs = n.comparator_runs ||
            (n.cmp_runs || []).map(function (k) { return statementMeta ? statementMeta.comparator_runs[k] : String(k); });
          row.decls = declarationsOf(n);
          row.tex = n.tex || (n.line && statementMeta && statementMeta.tex_paths[row.paperId] ?
            statementMeta.tex_paths[row.paperId] + '#L' + n.line : null);
          var lineMatch = row.tex ? /#L(\d+)$/.exec(row.tex) : null;
          row.line = n.line || (lineMatch ? parseInt(lineMatch[1], 10) : 0);
          // The printed number ("2.1") labels the dot once the reader zooms in.
          var numMatch = /^[A-Z][A-Za-z]*\.?\s+([A-Z]?\d+(?:\.\d+)*)/.exec(row.label || '');
          row.num = numMatch ? numMatch[1] : null;
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
      // Each paper's results in the order the paper states them, so a card
      // can step to the previous or next one.
      paperSequence = {};
      for (i = 0; i < nodes.length; i++) {
        if (nodes[i].kind !== 'paper_statement') continue;
        (paperSequence[nodes[i].paperId] = paperSequence[nodes[i].paperId] || []).push(i);
      }
      Object.keys(paperSequence).forEach(function (pid) {
        var seq = paperSequence[pid];
        seq.sort(function (a, b) {
          return (nodes[a].line || 0) - (nodes[b].line || 0) || (nodes[a].id < nodes[b].id ? -1 : 1);
        });
        seq.forEach(function (idx, at) { nodes[idx].seq = at; });
      });
      // A result the other paper also states: the same label, or a Lean
      // declaration both cite. Its card lists every place it appears.
      var twinSlots = {};
      for (i = 0; i < nodes.length; i++) {
        var tn = nodes[i];
        if (tn.kind !== 'paper_statement') continue;
        tn.twins = [];
        var slots = ['label|' + tn.sector + '|' + tn.paperLabel];
        (tn.decls || []).forEach(function (d) { slots.push('decl|' + tn.sector + '|' + d.name); });
        for (var si = 0; si < slots.length; si++) {
          (twinSlots[slots[si]] = twinSlots[slots[si]] || []).push(i);
        }
      }
      Object.keys(twinSlots).forEach(function (slot) {
        var list = twinSlots[slot];
        if (list.length < 2) return;
        var via = slot.indexOf('label|') === 0 ? 'the same label' : 'a Lean declaration both cite';
        list.forEach(function (a) {
          list.forEach(function (b) {
            if (a === b || nodes[a].paperId === nodes[b].paperId) return;
            var have = nodes[a].twins.filter(function (t) { return t.at === b; })[0];
            if (!have) nodes[a].twins.push({ at: b, via: via });
            else if (via === 'the same label') have.via = via;
          });
        });
      });
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
      refreshInspector();
      resolvePending();
      // Input can arrive before either graph response; refresh the same
      // guarded combobox view without reopening a departed search field.
      renderResults();
    }

    readPalette();
    if (pageMode && window.location.hash.indexOf('#o=') === 0) {
      try {
        pendingId = decodeURIComponent(window.location.hash.slice(3));
      } catch (err) { pendingId = null; }
    }
    var dataUrl = canvas.getAttribute('data-universe-src');
    fetchGraphJson(dataUrl).then(function (data) {
      validateOverview(data);
      overviewGeneration = data.generation_id || null;
      overviewReady = true;
      if (loadFullBtn) loadFullBtn.disabled = false;
      // The reveal starts closed, so the load's own draw shows no flash of
      // the whole map before the first frame opens it.
      var opening = pageMode && !pendingId && !reduceMotion && !!window.requestAnimationFrame && !document.hidden;
      // A teaser (the landing, the maths overview) plays the same opening
      // once, when the drawing first comes into view, so the reader sees the
      // rings arrive in reading order instead of a finished picture that was
      // drawn offscreen. It waits closed, and a hidden tab opens it at once.
      var teaserOpening = !pageMode && !reduceMotion && !!window.requestAnimationFrame &&
        !document.hidden && 'IntersectionObserver' in window;
      if (opening || teaserOpening) { reveal = 0; revealMs = 0; }
      ingest(data);
      if (opening) startReveal();
      if (teaserOpening) {
        var seen = new IntersectionObserver(function (entries) {
          for (var i = 0; i < entries.length; i += 1) {
            if (!entries[i].isIntersecting) continue;
            seen.disconnect();
            startReveal();
            return;
          }
        }, { threshold: 0.35 });
        seen.observe(canvas);
      }
      if (!pageMode) loadCompanion(data.companion);
    }).catch(function () {
      stage.classList.add('is-unavailable');
    });
    // A canvas neither waits for a web font nor redraws when one arrives, so
    // ask for the serif faces the labels use and draw again once they load.
    if (document.fonts && document.fonts.load) {
      Promise.all([
        document.fonts.load('600 10px "Plectis Serif"'),
        document.fonts.load('400 11px "Plectis Serif"'),
        document.fonts.load('500 12px "Plectis Serif"'),
        document.fonts.load('italic 600 11px "Plectis Serif"')
      ]).then(function () {
        // Letter places measured in the fallback face no longer hold.
        arcPlaces = {};
        if (nodes.length) draw();
      }, function () {});
    }

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
        if (pageMode) renderInspector(); else { showCaption(i); announce(i); }
      }
    });
    canvas.addEventListener('pointerleave', function () {
      if (hover === -1) return;
      hover = -1;
      canvas.classList.remove('is-over');
      draw();
      if (pageMode) renderInspector(); else { showCaption(-1); announce(-1); }
    });
    canvas.addEventListener('click', function (event) {
      if (moved) return;
      var rect = canvas.getBoundingClientRect();
      var i = nodeAt(event.clientX - rect.left, event.clientY - rect.top);
      // A double-click reads the object where it lives: a result at its
      // place in its paper, in this tab. The first click has already pinned
      // it, which set its paper loading.
      if (event.detail === 2 && i >= 0) { openTarget(nodes[i]); return; }
      if (pageMode) {
        // First click pins; a second click on the pinned object opens it.
        if (i >= 0 && i === selected) { openTarget(nodes[i]); return; }
        pin(i, false);
        if (i >= 0) revealCard();
        return;
      }
      if (companionApi && (i >= 0 || selected >= 0)) {
        pinInTeaser(i >= 0 && i !== selected ? i : -1);
        return;
      }
      // Without the column a click opens the full map on the object, whose
      // card carries the same ways out; no click jumps straight to GitHub.
      if (i >= 0) { window.location.href = route('universe.html#o=' + encodeURIComponent(nodes[i].id)); return; }
      var target = canvas.getAttribute('data-universe-href');
      if (target) window.location.href = target;
    });

    /* Pan and zoom only on the dedicated page; the landing teaser stays a
       fixed portrait so scrolling past it never fights the wheel. */
    if (pageMode) {
      var px0 = 0, py0 = 0;
      /* Two fingers pinch: the distance between them scales the view about
         their midpoint, and the midpoint's travel pans it. */
      var pointers = {}, pinch = null;
      function pointerIds() { return Object.keys(pointers); }
      function pinchState() {
        var ids = pointerIds(), a = pointers[ids[0]], b = pointers[ids[1]];
        return { dist: Math.max(1, Math.sqrt((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y))),
                 mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 };
      }
      function releasePointer(event) {
        delete pointers[event.pointerId];
        if (pointerIds().length < 2) pinch = null;
      }
      canvas.addEventListener('pointerdown', function (event) {
        pointers[event.pointerId] = { x: event.clientX, y: event.clientY };
        if (pointerIds().length === 2) {
          pinch = pinchState();
          panning = false;
          moved = true;
          return;
        }
        panning = true;
        moved = false;
        canvas.classList.add('is-panning');
        px0 = event.clientX; py0 = event.clientY;
        if (canvas.setPointerCapture) canvas.setPointerCapture(event.pointerId);
      });
      canvas.addEventListener('pointerup', function (event) {
        releasePointer(event);
        panning = false;
        canvas.classList.remove('is-panning');
        if (canvas.releasePointerCapture) canvas.releasePointerCapture(event.pointerId);
      });
      canvas.addEventListener('pointercancel', function (event) {
        releasePointer(event);
        panning = false;
        canvas.classList.remove('is-panning');
      });
      canvas.addEventListener('pointermove', function (event) {
        if (pointers[event.pointerId]) pointers[event.pointerId] = { x: event.clientX, y: event.clientY };
        if (pinch && pointerIds().length >= 2) {
          var now = pinchState(), rect = canvas.getBoundingClientRect();
          view.tx += now.mx - pinch.mx;
          view.ty += now.my - pinch.my;
          zoomAt(now.mx - rect.left, now.my - rect.top, now.dist / pinch.dist);
          pinch = now;
          return;
        }
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
      /* Over the map the wheel zooms about the pointer, as a map does;
         beside it the page scrolls. A scroll already moving the page carries
         on when the map slides under the pointer, so reading past the map
         never catches in it: a wheel event on the map within a moment of one
         elsewhere still scrolls. A pinch (ctrlKey) always zooms. */
      var pageWheelAt = -1e9;
      if (window.addEventListener) {
        window.addEventListener('wheel', function (event) {
          if (event.target !== canvas) pageWheelAt = event.timeStamp || Date.now();
        }, { passive: true, capture: true });
      }
      canvas.addEventListener('wheel', function (event) {
        var now = event.timeStamp || Date.now();
        if (!event.ctrlKey && !event.metaKey && now - pageWheelAt < 350) {
          pageWheelAt = now;
          return;
        }
        event.preventDefault();
        var rect = canvas.getBoundingClientRect();
        // Lines and pages arrive as their own units; one notch of a wheel is
        // about a fifth, a pinch's small steps add up smoothly.
        var dy = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? canvas.clientHeight : 1);
        dy = Math.max(-240, Math.min(240, dy));
        zoomAt(event.clientX - rect.left, event.clientY - rect.top,
          Math.exp(-dy * (event.ctrlKey ? 0.01 : 0.0022)));
      }, { passive: false });

      document.addEventListener('keydown', function (event) {
        var tag = event.target && event.target.tagName;
        var typing = tag === 'INPUT' || tag === 'TEXTAREA' || (event.target && event.target.isContentEditable);
        if (event.key === 'Escape' && selected >= 0) { pin(-1, false); return; }
        if (!typing && (event.key === 'ArrowLeft' || event.key === 'ArrowRight') &&
            selected >= 0 && nodes[selected].kind === 'paper_statement') {
          event.preventDefault();
          stepStatement(event.key === 'ArrowLeft' ? -1 : 1);
          return;
        }
        if (event.key === '/' && !typing && searchIn) {
          event.preventDefault();
          searchIn.focus();
          searchIn.select();
        }
      });

      stage.querySelectorAll('[data-universe-zoom]').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var mode = btn.getAttribute('data-universe-zoom');
          if (mode === 'fit') { fitAnimated(); return; }
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
        // A quote's reference to another result on the map selects it there;
        // with a modifier it opens in the paper as a link does.
        var ref = event.target.closest ? event.target.closest('[data-universe-ref]') : null;
        if (ref && !(event.metaKey || event.ctrlKey || event.shiftKey)) {
          var at = byId[ref.getAttribute('data-universe-ref')];
          if (at !== undefined) {
            event.preventDefault();
            pin(at, true);
            return;
          }
        }
        // A result two papers state: the tab chooses whose words it shows.
        var tab = event.target.closest ? event.target.closest('[data-universe-place]') : null;
        if (tab) {
          quoteAt = parseInt(tab.getAttribute('data-universe-place'), 10);
          renderInspector();
          var again = inspector.querySelector('[data-universe-place="' + quoteAt + '"]');
          if (again) again.focus({ preventScroll: true });
          return;
        }
        if (event.target.closest && event.target.closest('[data-universe-clear]')) {
          pin(-1, false);
          return;
        }
        var stepBtn = event.target.closest ? event.target.closest('[data-universe-step]') : null;
        if (stepBtn) {
          var dir = parseInt(stepBtn.getAttribute('data-universe-step'), 10);
          stepStatement(dir);
          // Keep the reader's place on the control they used.
          var again = inspector.querySelector('[data-universe-step="' + dir + '"]:not([disabled])') ||
            inspector.querySelector('[data-universe-step]:not([disabled])');
          if (again) again.focus({ preventScroll: true });
          return;
        }
        var copy = event.target.closest ? event.target.closest('[data-universe-copy]') : null;
        if (copy) {
          navigator.clipboard.writeText(window.location.href).then(function () {
            copy.textContent = 'Link copied';
          }, function () {
            copy.textContent = 'Copy failed; use the address bar';
          });
        }
      });
    }

    /* ---- Controls ----------------------------------------------------- */

    function afterFilterChange() {
      frameGraphCache = null;
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

    /* ---- Search results --------------------------------------------- */
    /* Typing lists the first matches under the field; the arrow keys pick
       one and Enter opens it. With no pick, Enter still steps through every
       match on the map in kind order. */
    var resultsBox = document.querySelector('[data-universe-results]');
    var activeResult = -1;
    var RESULT_CAP = 8;
    function resultContext(n) {
      if (n.kind === 'paper_statement') {
        var where = n.sector && problemIndex[n.sector] !== undefined ? nodes[problemIndex[n.sector]].shortLabel + ' ' : '';
        return where + (n.side === 'long' ? 'long record' : 'short paper');
      }
      if (n.sector && problemIndex[n.sector] !== undefined && n.kind !== 'problem') {
        return (KIND_LABEL[n.kind] || n.kind) + ', ' + nodes[problemIndex[n.sector]].shortLabel;
      }
      return KIND_LABEL[n.kind] || n.kind;
    }
    function closeResults() {
      activeResult = -1;
      if (!resultsBox) return;
      resultsBox.hidden = true;
      resultsBox.innerHTML = '';
      if (searchIn) {
        searchIn.setAttribute('aria-expanded', 'false');
        searchIn.removeAttribute('aria-activedescendant');
      }
    }
    function renderResults() {
      if (!resultsBox || !searchIn) return;
      if (query.length < 2 || !matchList.length || document.activeElement !== searchIn) { closeResults(); return; }
      var top = matchList.slice(0, RESULT_CAP);
      if (activeResult >= top.length) activeResult = top.length - 1;
      resultsBox.innerHTML = top.map(function (idx, at) {
        var n = nodes[idx];
        var mark = n.kind === 'paper_statement' || n.kind === 'public_claim' ? glyphHtml(n.tier) : dotHtml(n.kind);
        return '<li role="option" id="universe-result-' + at + '" class="universe-result' +
          (at === activeResult ? ' is-active' : '') + '" aria-selected="' + (at === activeResult) +
          '" data-universe-go="' + idx + '">' + mark +
          '<span class="universe-result__label">' + escapeHtml(clip(n.label, 72)) + '</span>' +
          '<span class="universe-result__where">' + escapeHtml(resultContext(n)) + '</span></li>';
      }).join('') + (matchList.length > RESULT_CAP ?
        '<li class="universe-result universe-result--more" role="presentation">' + fmtCount(matchList.length - RESULT_CAP) +
        ' more lit on the map; Enter steps through all ' + fmtCount(matchList.length) + '</li>' : '');
      resultsBox.hidden = false;
      searchIn.setAttribute('aria-expanded', 'true');
      if (activeResult >= 0) searchIn.setAttribute('aria-activedescendant', 'universe-result-' + activeResult);
      else searchIn.removeAttribute('aria-activedescendant');
    }
    if (resultsBox) {
      // Keep focus in the field while a pointer picks a result.
      resultsBox.addEventListener('mousedown', function (event) {
        event.preventDefault();
        var item = event.target.closest ? event.target.closest('[data-universe-go]') : null;
        if (!item) return;
        var idx = parseInt(item.getAttribute('data-universe-go'), 10);
        closeResults();
        if (!isNaN(idx) && nodes[idx]) pin(idx, true);
      });
    }

    if (searchIn) {
      function syncSearchFromInput() {
        var restoredQuery = normalizeSearchText(searchIn.value);
        if (restoredQuery === query) return;
        query = restoredQuery;
        activeResult = -1;
        countMatches();
        draw();
        renderResults();
      }
      searchIn.addEventListener('input', syncSearchFromInput);
      searchIn.addEventListener('focus', function () { syncSearchFromInput(); renderResults(); });
      searchIn.addEventListener('blur', function () { closeResults(); });
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
          closeResults();
          draw();
          event.stopPropagation();
          return;
        }
        if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && resultsBox && !resultsBox.hidden) {
          event.preventDefault();
          var count = Math.min(RESULT_CAP, matchList.length);
          if (!count) return;
          activeResult = event.key === 'ArrowDown' ? (activeResult + 1) % count :
            (activeResult <= 0 ? count - 1 : activeResult - 1);
          renderResults();
          return;
        }
        if (event.key !== 'Enter') return;
        syncSearchFromInput();
        if (!matchList.length) return;
        event.preventDefault();
        if (activeResult >= 0 && matchList[activeResult] !== undefined) {
          var chosen = matchList[activeResult];
          closeResults();
          pin(chosen, true);
          return;
        }
        var at = matchList.indexOf(selected);
        var next = at < 0 ? 0 : (at + (event.shiftKey ? matchList.length - 1 : 1)) % matchList.length;
        pin(matchList[next], true);
        searchIn.focus({ preventScroll: true });
      });
    }

    // Data may arrive from independent caches. Validate a whole handoff before
    // ingest mutates selection, adjacency or the currently working overview.
    var overviewReady = false;
    var overviewGeneration = null;
    if (loadFullBtn) loadFullBtn.disabled = true;

    function fetchGraphJson(url) {
      return fetch(url).then(function (response) {
        if (response.ok === false) throw new Error('Map data request failed');
        return response.json();
      });
    }

    function nodeIndex(rows, positioned) {
      if (!Array.isArray(rows) || !rows.length) throw new Error('Map has no objects');
      var ids = Object.create(null);
      rows.forEach(function (node) {
        if (!node || typeof node.id !== 'string' || !node.id || ids[node.id]) {
          throw new Error('Map object identity is missing or duplicated');
        }
        ids[node.id] = true;
        if (positioned && !finitePoint([node.x, node.y])) {
          throw new Error('Map object has no finite position');
        }
      });
      return ids;
    }

    function finitePoint(point) {
      return Array.isArray(point) && point.length === 2 && point.every(function (value) {
        return typeof value === 'number' && isFinite(value);
      });
    }

    function validateOverview(data) {
      if (!data || !Array.isArray(data.edges)) throw new Error('Invalid map overview');
      nodeIndex(data.nodes, true);
      data.edges.forEach(function (edge) {
        if (!Array.isArray(edge) || edge.length < 2 || edge.length > 3 ||
            !edge.every(function (value) { return typeof value === 'number' && value >= 0 && value % 1 === 0; }) ||
            edge[0] >= data.nodes.length || edge[1] >= data.nodes.length ||
            (edge.length === 3 && (!Array.isArray(data.relations) ||
              edge[2] >= data.relations.length || typeof data.relations[edge[2]] !== 'string'))) {
          throw new Error('Overview connection does not resolve');
        }
      });
    }

    function validateComplete(graph, layout) {
      if (!graph || !Array.isArray(graph.edges) || !layout || !layout.positions) {
        throw new Error('Invalid complete map');
      }
      if (overviewGeneration && layout.generation_id !== overviewGeneration) {
        throw new Error('Map assets belong to different generations');
      }
      var ids = nodeIndex(graph.nodes, false);
      var pos = layout.positions;
      if (Object.keys(pos).length !== graph.nodes.length) throw new Error('Map layout coverage differs');
      graph.nodes.forEach(function (node) {
        if (!Object.prototype.hasOwnProperty.call(pos, node.id) || !finitePoint(pos[node.id])) {
          throw new Error('Complete map object has no finite position');
        }
      });
      var edgeIds = Object.create(null);
      graph.edges.forEach(function (edge) {
        if (!edge || !ids[edge.source] || !ids[edge.target]) {
          throw new Error('Complete map connection does not resolve');
        }
        var key = JSON.stringify([edge.source, edge.relation || 'linked', edge.target]);
        if (edgeIds[key]) throw new Error('Complete map connection is duplicated');
        edgeIds[key] = true;
      });
    }

    function loadFull() {
      if (!loadFullBtn || !overviewReady || fullLoaded || fullLoading) return;
      fullLoading = true;
      loadFullBtn.disabled = true;
      loadFullBtn.textContent = 'Loading the complete universe…';
      var graphUrl = loadFullBtn.getAttribute('data-graph-src');
      var layoutUrl = loadFullBtn.getAttribute('data-layout-src');
      Promise.all([
        fetchGraphJson(graphUrl),
        fetchGraphJson(layoutUrl)
      ]).then(function (results) {
        var graph = results[0], layout = results[1];
        validateComplete(graph, layout);
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
