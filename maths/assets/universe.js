/* Plectis — universe map renderer.
   Draws the Lean corpus graph on a canvas from a pre-computed layout file.
   No libraries, no physics: coordinates are decided at build time so the
   picture is identical on every visit and the first paint costs one fetch
   and one draw. The canvas is an enhancement — every object it shows is
   also in the HTML index on the universe page, so nothing is canvas-only.
   All colour comes from CSS custom properties, re-read on theme change.

   Interaction model (universe page, a full-window explorer since 5 October
   2026): the panel on the left reads the map in three levels, the eight
   problems at rest, a chosen problem (its question, short paper and
   results), a chosen result (its statement, its checks, its ways out).
   Hover previews an object in a layer over the panel, leaving the panel
   itself untouched, and lights its connections; click pins the card and
   dims everything the object does not touch; Esc or an empty click goes
   back a level. A pinned object is addressable as #o=<id>, so views can be
   shared. The landing teaser keeps a single caption line instead (its
   column, universe-companion.js, reads beside it); no cursor-chasing
   tooltip anywhere.

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
    // A claim is named by what it is; its status (proved, conditional,
    // open) is said by its glyph and chip, never by its kind's name.
    public_claim: 'claim',
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
    public_claim: 'Claims',
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
     with no replay recorded (Lean colour, filled); Lean modulo named inputs
     (ring); no Lean statement (faint ring). */
  var EVIDENCE_ORDER = ['replayed', 'lean', 'modulo', 'none'];
  var EVIDENCE_TEXT = {
    replayed: 'replayed by Comparator',
    lean: 'exact Lean, replay not recorded',
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
    pending: 'replay pending',
    not_applicable: 'nothing to replay without an exact Lean statement'
  };
  function comparatorReplayText(node) {
    if (node.comparator_status === 'pending' && node.comparator_queued_at) {
      return 'Its replay is queued since ' + node.comparator_queued_at + '.';
    }
    return 'No Comparator replay is recorded for this paper result.';
  }
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

  /* Colour, mixed as the stylesheet mixes it. A mark that drops back while
     another is in focus is mixed toward the ground's line tone in Oklab,
     as color-mix(in oklab, …) does on the system map, so it stays faded ink
     of its own hue and never turns a pastel or a neutral grey. A colour
     string is parsed once. */
  var parsedColors = {};
  function parseColor(text) {
    var key = String(text == null ? '' : text).trim();
    if (Object.prototype.hasOwnProperty.call(parsedColors, key)) return parsedColors[key];
    var out = null, m;
    if ((m = /^#([0-9a-f]{3,8})$/i.exec(key))) {
      var hex = m[1];
      if (hex.length === 3 || hex.length === 4) hex = hex.replace(/(.)/g, '$1$1');
      if (hex.length === 6 || hex.length === 8) {
        out = [parseInt(hex.slice(0, 2), 16) / 255, parseInt(hex.slice(2, 4), 16) / 255,
               parseInt(hex.slice(4, 6), 16) / 255, hex.length === 8 ? parseInt(hex.slice(6, 8), 16) / 255 : 1];
      }
    } else if ((m = /^rgba?\(\s*([\d.]+%?)[\s,]+([\d.]+%?)[\s,]+([\d.]+%?)(?:[\s,/]+([\d.]+%?))?\s*\)$/i.exec(key))) {
      var channel = function (v) { return /%$/.test(v) ? parseFloat(v) / 100 : parseFloat(v) / 255; };
      out = [channel(m[1]), channel(m[2]), channel(m[3]),
             m[4] == null ? 1 : /%$/.test(m[4]) ? parseFloat(m[4]) / 100 : parseFloat(m[4])];
    } else if ((m = /^color\(\s*srgb\s+([-\d.e]+)\s+([-\d.e]+)\s+([-\d.e]+)(?:\s*\/\s*([\d.]+%?))?\s*\)$/i.exec(key))) {
      out = [+m[1], +m[2], +m[3], m[4] == null ? 1 : /%$/.test(m[4]) ? parseFloat(m[4]) / 100 : +m[4]];
    }
    if (out && !out.every(function (v) { return isFinite(v); })) out = null;
    parsedColors[key] = out;
    return out;
  }
  function toLinear(c) { return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
  function toGamma(c) { return c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055; }
  function rgbToOklab(c) {
    var r = toLinear(c[0]), g = toLinear(c[1]), b = toLinear(c[2]);
    var l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
    var m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
    var s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
    return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
  }
  function oklabToRgb(c) {
    var l = c[0] + 0.3963377774 * c[1] + 0.2158037573 * c[2];
    var m = c[0] - 0.1055613458 * c[1] - 0.0638541728 * c[2];
    var s = c[0] - 0.0894841775 * c[1] - 1.2914855480 * c[2];
    l = l * l * l; m = m * m * m; s = s * s * s;
    return [toGamma(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s),
            toGamma(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s),
            toGamma(-0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)];
  }
  function rgbText(c) {
    var v = function (x) { return Math.round(Math.max(0, Math.min(1, x)) * 255); };
    return 'rgb(' + v(c[0]) + ', ' + v(c[1]) + ', ' + v(c[2]) + ')';
  }
  // What a translucent colour shows over an opaque ground.
  function overGround(c, ground) {
    if (c[3] >= 0.999) return c;
    return [c[0] * c[3] + ground[0] * (1 - c[3]), c[1] * c[3] + ground[1] * (1 - c[3]),
            c[2] * c[3] + ground[2] * (1 - c[3]), 1];
  }
  // color-mix(in oklab, a, b t): t of the way from a to b, as a CSS colour;
  // null when either colour cannot be read.
  function mixOklab(a, b, t, ground) {
    var ca = parseColor(a), cb = parseColor(b);
    if (!ca || !cb) return null;
    if (ground) { ca = overGround(ca, ground); cb = overGround(cb, ground); }
    var la = rgbToOklab(ca), lb = rgbToOklab(cb);
    return rgbText(oklabToRgb([la[0] + (lb[0] - la[0]) * t, la[1] + (lb[1] - la[1]) * t, la[2] + (lb[2] - la[2]) * t]));
  }

  function clip(text, max) {
    text = String(text);
    if (text.length <= max) return text;
    var cut = text.slice(0, max - 1);
    var space = cut.lastIndexOf(' ');
    if (space > max * 0.6) cut = cut.slice(0, space);
    return cut + '…';
  }

  /* A name is plain words. Two of the ledger's result names carry a
     Markdown link inside their parentheses ("Theorem 5.6 ([criterion using
     least common multiples](https://…))"), and a plate printed the link as
     it stands; the link's own words take its place. */
  function plainText(text) {
    return String(text == null ? '' : text)
      .replace(/\[([^\]]*)\]\((?:[^()\s]|\([^()\s]*\))*\)/g, '$1');
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
    /* Type on the field. The landing's teaser stands beside a column set at
       body size and is read from a laptop's distance (and at two thirds
       zoom on a wide monitor), so its words are set near that size: band
       titles 16px, their counts 14px, a name plate 15px, nothing under
       13px. The map's own page, a large field the reader zooms, keeps its
       smaller set. One table, so every label, plate and room the label
       manager reserves is measured in the face it is drawn in. */
    /* The full-window explorer (5 October 2026) draws its ring as large as
       the window allows, about the teaser's size or more, and is read from
       the same distance, so its words are set between the two: band
       titles 14px, a name plate 13.5px, the results' numbers 11.5px. */
    var inExplorer = pageMode && !!(canvas.closest && canvas.closest('[data-explorer]'));
    var TYPE = inExplorer ? {
      title: 14, count: 12.5, rowGap: 15, arcPad: 8,
      anchor: 14.5, small: 13, sub: 12, subGap: 14, below: 16.5,
      plate: 13.5, lead: 16.5, ascent: 18, descent: 8, oneLine: 340, twoAt: 180, keepOne: 250,
      callout: 11.5, number: 11
    } : pageMode ? {
      title: 12, count: 11, rowGap: 13, arcPad: 7,
      anchor: 13, small: 12, sub: 11, subGap: 13, below: 15,
      plate: 12, lead: 14.5, ascent: 16, descent: 7, oneLine: 300, twoAt: 160, keepOne: 220,
      callout: 10, number: 9
    } : {
      title: 16, count: 14, rowGap: 17, arcPad: 9,
      anchor: 15, small: 14, sub: 13, subGap: 15, below: 17,
      plate: 15, lead: 18, ascent: 20, descent: 9, oneLine: 375, twoAt: 200, keepOne: 275,
      callout: 13, number: 9
    };
    function face(weight, size, italic) {
      return (italic ? 'italic ' : '') + weight + ' ' + size + 'px ' + SERIF;
    }
    /* On the landing nothing crowds the card's edge: the outermost word of
       the drawing stands at least EDGE_CLEAR from the frame, and a name
       plate's box at least PLATE_EDGE from the canvas (clear of the corner
       registration marks, 10px in with 13px arms, and of the buttons under
       the canvas). The page's plates may come to 2px of its edge as before. */
    var EDGE_CLEAR = pageMode ? 0 : 32;
    var PLATE_EDGE = pageMode ? 2 : 24;
    var caption = stage.querySelector('.universe-caption');
    var replaySummary = stage.querySelector('.home-universe__legend');
    var inspector = document.querySelector('[data-universe-inspector]');
    var countOut = document.querySelector('[data-universe-count]');
    var searchIn = document.querySelector('[data-universe-search]');
    var loadFullBtn = document.querySelector('[data-universe-load-full]');
    var canCopy = !!(navigator.clipboard && window.isSecureContext);
    /* The map's own page is a full-window explorer (5 October 2026): one
       reading panel on the left whose body scrolls (data-universe-scroll),
       a layer over that body for what the pointer is on
       (data-universe-preview), and the drawing in the rest of the window
       with its controls and key laid over its corners. The shared frame
       (assets/explorer.js) asks for a fit, a zoom and a refit by event. */
    var explorerRoot = pageMode && canvas.closest ? canvas.closest('[data-explorer]') : null;
    var scrollBox = pageMode ? document.querySelector('[data-universe-scroll]') : null;
    var previewBox = pageMode ? document.querySelector('[data-universe-preview]') : null;

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
    // The panel's view at rest (the panel views, below): problems, index,
    // filters or about; a kept object reads over whichever it is.
    var panelView = 'problems';
    var indexCat = '', indexScope = '';
    var viewScroll = {}, viewStack = [], returnState = null, lastProblemAt = -1;
    var restBox = pageMode ? document.querySelector('[data-universe-rest]') : null;
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
    var paperScope = 'all';
    var sharedOnly = false;
    var checking = 'all';
    var overlapInput = document.querySelector('[data-universe-overlap]');
    var checkingInput = document.querySelector('[data-universe-checking]');
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
    /* A pinned card loads only its paper's Lean statements and Comparator
       checks. The complete API is a fallback for older data or a failed shard. */
    var detailUrl = canvas.getAttribute('data-universe-detail');
    var detailRoutes = {};
    var details = {};
    var detailLoading = {};
    var detailFailed = {};
    /* A result's card quotes its printed environment as MathML. A hover or
       pin loads one paper file, or one bounded batch for a large paper. */
    var excerptRoutes = {};
    var excerptBatchRoutes = {};
    var excerptBatchIds = {};
    var excerpts = {};
    var excerptLoading = {};
    var excerptLoaded = {};
    var excerptFailed = {};
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
                  // The explorer's drawing lies on the page's own flat ground.
                  ground: (explorerRoot && cssColor(styles, '--page', '')) || cssColor(styles, '--surface', '#fffdf7'),
                  ink: cssColor(styles, '--ink', '#211318'),
                  faint: cssColor(styles, '--faint', '#786359'),
                  muted: cssColor(styles, '--muted', '#6b5f58') };
      for (var kind in KIND_COLOR) {
        palette[kind] = cssColor(styles, KIND_COLOR[kind], '#888888');
      }
      darkGround = groundIsDark(palette.ground);
      // A kept (pinned) result is framed in the landing's ember, the colour
      // the column's card rule turns when it holds a result.
      palette.ember = cssColor(styles, '--home-ember', '') || palette.integration_surface;
      // The ground the canvas is actually seen on (on the landing a card
      // laid translucent over the page), and the line tone over it a mark
      // drops back toward: ink at 16% of the ground, as the system map's.
      palette.under = effectiveGround();
      palette.tone = palette.under ? mixOklab(palette.ink, rgbText(palette.under), 0.84, palette.under) : null;
      mixCache = {};
      shadeTableAt = -1;
    }
    // The colour behind the canvas: each translucent background on the way
    // up laid over the first opaque one (or over the surface colour).
    function effectiveGround() {
      var layers = [], el = canvas.parentElement || null;
      while (el && el.nodeType === 1 && layers.length < 12) {
        var cs = getComputedStyle(el);
        var c = cs && cs.backgroundColor ? parseColor(cs.backgroundColor) : null;
        if (c && c[3] > 0.004) {
          layers.push(c);
          if (c[3] >= 0.996) break;
        }
        el = el.parentElement;
      }
      var base = parseColor(palette.ground) || [1, 1, 1, 1];
      if (layers.length && layers[layers.length - 1][3] >= 0.996) base = layers.pop();
      for (var j = layers.length - 1; j >= 0; j--) base = overGround(layers[j], base);
      return [base[0], base[1], base[2], 1];
    }
    /* A mark that drops back is its own ink at DIM_INK of its strength
       over the tone (color-mix(in oklab, ink 30%, tone)), reached in
       steps as the focus fades in, so the ring keeps its hue and the lit
       sector rises out of it. */
    var DIM_INK = 0.3;
    var mixCache = {};
    function towardTone(color, amount) {
      if (!palette.tone || !color || amount <= 0) return color;
      var t = Math.round(Math.min(1, amount) * 40) / 40;
      var key = color + '|' + t;
      var hit = mixCache[key];
      if (hit === undefined) {
        hit = mixOklab(color, palette.tone, (1 - DIM_INK) * t, palette.under) || color;
        mixCache[key] = hit;
      }
      return hit;
    }
    // How far the mark being drawn has dropped back (0 at full ink). Every
    // mark that drops back in a frame drops back as far, so the frame keeps
    // one small table of the few inks it mixes.
    var shadeBy = 0, shadeTable = {}, shadeTableAt = -1;
    function shade(color) {
      if (shadeBy <= 0) return color;
      if (shadeTableAt !== shadeBy) { shadeTable = {}; shadeTableAt = shadeBy; }
      var hit = shadeTable[color];
      if (hit === undefined) hit = shadeTable[color] = towardTone(color, shadeBy);
      return hit;
    }

    function normalizeSearchText(text) {
      // Friendly labels use spaces where source titles use typographic
      // dashes. Keep other punctuation (including qualified IDs) literal;
      // this is separator equivalence, not fuzzy spelling or word order.
      return text.toLowerCase().replace(/[-\u2010-\u2014]/g, ' ')
        .replace(/\s+/g, ' ').trim();
    }

    /* Whether a node is shown is asked thousands of times a frame (every
       loop over the field, every pointer move) and changes only when a
       filter does: the answer is kept on the node until afterFilterChange
       or a new ingest moves visGen on. */
    var visGen = 1;
    function visible(node) {
      if (node._visGen === visGen) return node._vis;
      node._visGen = visGen;
      return (node._vis = shownByFilters(node));
    }
    function shownByFilters(node) {
      if (lensOff[node.kind]) return false;
      if (node.kind === 'paper_statement') {
        if (paperScope !== 'all' && node.side !== paperScope) return false;
        if (sharedOnly && !(node.twins || []).length) return false;
        if (checking === 'ordinary_proof' && node.proof_status !== 'ordinary_proof') return false;
        if (checking !== 'all' && checking !== 'ordinary_proof' && node.tier !== checking) return false;
      } else if (node.kind === 'public_claim' && checking === 'ordinary_proof' && node.proof_status !== 'ordinary_proof') {
        return false;
      }
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
      var tx = null, ty = null;
      // With the results ring shown, the frame holds its titles as well:
      // the outer band, the gap, two lines of text and a margin to spare.
      if (bands.length && !lensOff.paper_statement) {
        var outer = 0;
        for (var b = 0; b < bands.length; b++) outer = Math.max(outer, bandRadii(bands[b])[1] || 0);
        var room = Math.min(w, h) / 2 - 56;
        var band = !pageMode && w >= 520 ? titleExtents() : null;
        if (outer && band) {
          /* The teaser is fitted with its words, not by its ring: each side
             of the content is the ring (which grows with the scale) plus the
             words beyond it there (which do not), the level titles at three
             and nine o'clock taking width where the others take height. The
             content is fitted inside the canvas less EDGE_CLEAR all round
             and centred, so the outermost word stands at least that far from
             the frame on every side and a taller card gives breathing room,
             never a ring bigger than the width allows. */
          var R = outer + 6;
          // Under the canvas the card keeps a row for the key and the two
          // buttons; the drawing's foot keeps EDGE_CLEAR from that row, as
          // its head does from the frame, so the ring stands centred between
          // the two.
          var foot = Math.max(16, EDGE_CLEAR - footGap());
          var kx = (w - 2 * EDGE_CLEAR - band.left - band.right) / (2 * R);
          var ky = (h - EDGE_CLEAR - foot - band.top - band.bottom) / (2 * R);
          k = Math.min(k, kx, ky);
          if (k > 0) {
            tx = EDGE_CLEAR + band.left + k * R + ((w - 2 * EDGE_CLEAR) - (2 * k * R + band.left + band.right)) / 2;
            ty = EDGE_CLEAR + band.top + k * R + ((h - EDGE_CLEAR - foot) - (2 * k * R + band.top + band.bottom)) / 2;
          }
        } else if (outer && explorerRoot) {
          /* The explorer fits the ring with its words: the scale and the
             two lines of each band's title beyond it, all the way round,
             PAGE_EDGE clear of the drawing's edge and clear of the controls
             and the key over its corners. The ring is a circle, so the
             corners keep the controls and the key; the circle is as large
             as the nearest of them and the stage's short side allow. */
          var reach = pageWordsReach();
          var cx = w / 2, cy = h / 2;
          var limit = Math.min(w, h) / 2 - PAGE_EDGE;
          chromeBoxes().forEach(function (box) { limit = Math.min(limit, distanceToBox(cx, cy, box) - 10); });
          var kr = (limit - reach) / (outer + 6);
          if (kr > 0) {
            k = Math.min(k, kr);
            tx = cx;
            ty = cy;
          }
        } else if (outer && room > 40) {
          k = Math.min(k, room / (outer + 6));
        }
      }
      k = Math.max(0.001, k);
      fittedScale = k;
      viewIsFitted = true;
      viewWidth = w; viewHeight = h;
      view.k = k;
      view.tx = tx !== null ? tx : w / 2 - k * (minX + maxX) / 2;
      view.ty = ty !== null ? ty : h / 2 - k * (minY + maxY) / 2;
    }

    // How far the explorer's words reach past the ring's outer plate: the
    // scale's ticks, then the band titles' two lines (bandLabelLayout sets
    // the first at the tick ends plus seven pixels), with room for their
    // letters' height and the halo round them.
    var PAGE_EDGE = 16;
    function pageWordsReach() {
      return SCALE_GAP + SCALE_MARK + 7 + TYPE.rowGap + TYPE.title * 0.6 + 6;
    }
    /* The controls and the key laid over the explorer's drawing, as boxes in
       the canvas's own pixels (each line of the key on its own, since the
       key's box spans the stage while its words keep to the corner). The
       fit keeps the ring clear of them and a name plate steps round them.
       Measured once per size of the stage. */
    var chromeCache = null;
    function chromeBoxes() {
      if (!explorerRoot || typeof canvas.getBoundingClientRect !== 'function' || !stage.querySelectorAll) return [];
      if (chromeCache) return chromeCache;
      var base = canvas.getBoundingClientRect(), out = [];
      var els = Array.prototype.slice.call(stage.querySelectorAll('.explorer__tools, .explorer__legend > *'));
      els.forEach(function (el) {
        var r = el.getBoundingClientRect ? el.getBoundingClientRect() : null;
        if (!r || !(r.width > 0) || !(r.height > 0)) return;
        out.push({ x0: r.left - base.left, x1: r.right - base.left, y0: r.top - base.top, y1: r.bottom - base.top,
                   legend: !!(el.parentElement && el.parentElement.classList && el.parentElement.classList.contains('explorer__legend')) });
      });
      chromeCache = out;
      return out;
    }
    function distanceToBox(x, y, b) {
      var dx = Math.max(b.x0 - x, 0, x - b.x1), dy = Math.max(b.y0 - y, 0, y - b.y1);
      return Math.sqrt(dx * dx + dy * dy);
    }

    // How far below the canvas the card's caption row (the key and the
    // buttons) begins, in pixels; 0 where the canvas has no such row.
    function footGap() {
      var row = stage.querySelector ? stage.querySelector('.home-universe__caption') : null;
      if (!row || typeof row.getBoundingClientRect !== 'function' || typeof canvas.getBoundingClientRect !== 'function') return 0;
      var top = Infinity;
      Array.prototype.forEach.call(row.querySelectorAll ? row.querySelectorAll('a, .universe-key, .universe-caption') : [], function (el) {
        var r = el.getBoundingClientRect();
        if (r.height > 0) top = Math.min(top, r.top);
      });
      var bottom = canvas.getBoundingClientRect().bottom;
      return isFinite(top) && isFinite(bottom) ? Math.max(0, top - bottom) : 0;
    }
    // The problems' orbit, in the layout's units.
    function orbitRadius() {
      var orbit = 0, count = 0;
      for (var pid in problemIndex) {
        var p = nodes[problemIndex[pid]];
        if (p) { orbit += Math.sqrt(p.x * p.x + p.y * p.y); count++; }
      }
      return count ? orbit / count : 0;
    }
    /* The names inside the teaser's ring (the problems, the core, the
       checkers) are set to the ring: 15px where the orbit is wide, down to
       13px where a short card holds the ring small, so all eight numbers,
       the core and both checkers keep their names. At 15px a 1280 by 690
       window lost three of them. Nothing on the field is under 12px. */
    function fitInteriorType() {
      if (pageMode) return;
      var size = Math.max(13, Math.min(15, Math.round(orbitRadius() * view.k * 0.118)));
      if (size === TYPE.anchor) return;
      TYPE.anchor = size;
      TYPE.sub = Math.max(12, size - 2);
      TYPE.subGap = TYPE.sub + 2;
      TYPE.below = size + 2;
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
    /* When the landing's column lets the drawing go (it closes, or lets a
       kept result go), no pointer is sweeping between dots, so nothing is
       held: the field comes back in LET_GO, on the same beat as the column
       fading out, rather than a quarter of a second after it. */
    var LET_GO = 160, letGoNow = false;
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
        if (letGoNow) fadeFocus(0, LET_GO * focusMix, 0);
        else fadeFocus(0, FOCUS_OUT, FOCUS_HOLD);
      }
      letGoNow = false;
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
       glow would only smudge the mark, so there the ember stays a mark.
       Nothing else glows: the mark in focus is framed by its reticle and
       ring, precisely, never lit. */
    var darkGround = false;
    // Measured on the landing at 1280 and 1440: below about a fifth, the
    // halo at a band's edge does not register at all. An ember reaches a
    // little past its mark and no further (6 October 2026): at four and a
    // half radii the halos of a dense band ran together into an orange haze
    // that blurred the marks, and a close view swelled each into a soft
    // disc. Now it stays within a few pixels of its mark at any zoom, so
    // the band reads as warm, separate marks.
    var EMBER_REST = 0.26, EMBER_LIT = 0.4, EMBER_REACH = 2.9, EMBER_PX = 5;
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
       a bead run along each of its threads; when Comparator replayed the
       result, Comparator answers with one ripple of its own. It waits a
       tenth of a second, so a pointer sweeping across a band leaves no
       trail, plays once in about a second and a half, and is skipped under
       reduced motion, which keeps the still embers. */
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
        var ek = layerK(3);
        for (i = 0; i < nodes.length; i++) {
          n = nodes[i];
          if (n.kind !== 'paper_statement' || n.tier !== 'replayed' || !visible(n)) continue;
          if (searching && !matches(n)) continue;
          x = n.x * ek + view.tx; y = n.y * ek + view.ty;
          if (x < -30 || y < -30 || x > w + 30 || y > h + 30) continue;
          var lit = focus >= 0 && (i === focus || near[i]);
          var fade = focus >= 0 && !lit ? 1 - focusMix : 1;
          drawGlow(x, y, Math.min(n.r * rs * EMBER_REACH, n.r * rs + EMBER_PX), palette.integration_surface,
                   (lit ? EMBER_LIT : EMBER_REST) * fade * (reveal < 1 ? setAt(Math.atan2(n.y, n.x)) : 1));
        }
      }
      // The mark in focus is framed by its reticle, not lit: the embers are
      // the only light on the field.
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = 1;
    }
    // Over the marks: the ripple, the beads, and Comparator's answer. A
    // bead runs along its thread's route where the thread was routed round
    // the words between its ends.
    function drawPulse(focus, threads, rs, routes) {
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
        var path = routes && routes[th.other] && routes[th.other].points.length > 1 ? routes[th.other].points : [[x, y], [mx, my]];
        var fade = Math.min(1, p * 6, (1 - p) * 6);
        var q = easeInOut(p);
        var bead = alongRoute(path, q);
        // The tail is three fading dots, in the map's own language of marks.
        ctx.fillStyle = color;
        for (var d = 3; d >= 1; d--) {
          var tail = alongRoute(path, easeInOut(Math.max(0, p - d * 0.035)));
          ctx.globalAlpha = fade * (0.56 - d * 0.14);
          ctx.beginPath();
          ctx.arc(tail[0], tail[1], Math.max(0.7, (2.2 - d * 0.4) * size), 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.globalAlpha = fade;
        ctx.fillStyle = darkGround ? palette.ink : color;
        ctx.beginPath();
        ctx.arc(bead[0], bead[1], 2.2 * size, 0, Math.PI * 2);
        ctx.fill();
      });
      // A replayed result's bead reaches Comparator, which answers with one
      // ripple of its own, the same mark the result sent out. Palomar, which
      // holds a prepared corpus, does not answer.
      if (n.tier === 'replayed') {
        threads.forEach(function (th) {
          var m = nodes[th.other];
          if (m.id !== 'integration:comparator') return;
          var b = pulsePhase(th.delay + PULSE_TRAVEL, PULSE_BLOOM);
          if (b <= 0 || b >= 1) return;
          var e = 1 - Math.pow(1 - b, 3), mr = m.r * rs;
          ctx.globalAlpha = 0.7 * (1 - e);
          ctx.lineWidth = 1.3;
          ctx.strokeStyle = palette.integration_surface;
          ctx.beginPath();
          ctx.arc(m.x * view.k + view.tx, m.y * view.k + view.ty, mr + 2 + e * Math.max(12, mr * 1.1), 0, Math.PI * 2);
          ctx.stroke();
        });
      }
      ctx.globalAlpha = 1;
    }

    /* ---- Structure ----------------------------------------------------- */
    /* The field shows how it is built, the way a careful technical drawing
       does. Round the results ring runs a scale with one tick for every
       result: each sector's short paper first, then its long record, each
       in the order the paper states them, so the scale is the papers laid
       end to end and a tick's place is a result's place in its paper. Every
       tenth tick of a paper is longer and every fiftieth longer again, a
       mark stands between a sector's two papers, and the strongest marks are
       the boundaries between sectors, the ring's own divisions carried out
       to the scale. On the map page a cursor stands on the tick of the
       pinned result, so walking a paper walks the cursor along it, tick by
       tick. The object in focus is framed by four corner ticks, and any
       object but the core, the checkers and the problems (which carry their
       names at rest) is tied to its name plate by a hairline leader. Every
       mark is a datum or a boundary, and no number is drawn that the data
       does not hold. Straight
       hairlines are filled rectangles on the device-pixel grid, so each is
       one device pixel wide and never smeared across two. */
    var hairX = 0.5, hairY = 0.5, hairPx = 0.5;
    function snapX(v) { return Math.round(v / hairX) * hairX; }
    function snapY(v) { return Math.round(v / hairY) * hairY; }

    // The scale's ticks by count within a paper: [every, length, ink]. The
    // finest step drawn keeps its ticks three device pixels apart, so a
    // laptop's field shows every fifth result and a closer view every one.
    var SCALE_TICKS = [[50, 6, 0.5], [10, 4.5, 0.4], [5, 3, 0.3], [1, 2, 0.22]];
    var SCALE_GAP = 2.5, SCALE_MARK = 8, SCALE_PAPER = 6.5, SCALE_PITCH = 3;
    // Where this frame's scale stands (px from the centre), or 0 without one.
    var scaleR = 0;
    function scaleRadius(w) {
      if (!scaleRows.length || lensOff.paper_statement || (!pageMode && w < 520)) return 0;
      var outer = 0;
      for (var i = 0; i < bands.length; i++) {
        var r1 = bandRadii(bands[i])[1];
        if (isFinite(r1)) outer = Math.max(outer, r1);
      }
      var R = outer > 0 ? (outer + 6) * view.k + SCALE_GAP : 0;
      return R >= 90 ? R : 0;
    }
    // While the opening seats the results ring, the scale seats with it.
    function seatedScaleR() {
      return (scaleR - SCALE_GAP) * seatOf(3) + SCALE_GAP;
    }
    // Per sector, its results in scale order and where each paper's run
    // starts; per result, its row and place on the scale.
    var scaleRows = [], scaleSlot = {};
    /* One spacing for every tick round the ring. A sector is as wide as its
       results plus a floor, so a small sector spread its ticks wider and
       read as sparse beside a full one. Every tick now stands at the closest
       spacing any sector allows (less a twentieth, so no run meets a
       boundary), and each sector's run sits centred in it with clear ground
       at both ends: the scale's density is one everywhere, and a run's
       length is its count. */
    var SCALE_FILL = 0.95, scalePitch = 0;
    function buildScale() {
      scaleRows = [];
      scaleSlot = {};
      bands.forEach(function (b) {
        var pids = Object.keys(paperSequence).filter(function (pid) {
          var first = nodes[paperSequence[pid][0]];
          return !!first && first.sector === b.sector;
        });
        pids.sort(function (p, q) {
          var a = nodes[paperSequence[p][0]], c = nodes[paperSequence[q][0]];
          return (SIDE_ORDER[a.side] || 0) - (SIDE_ORDER[c.side] || 0) || (p < q ? -1 : p > q ? 1 : 0);
        });
        var row = { sector: b.sector, lo: b.lo, hi: b.hi, slots: [], breaks: [], papers: [] };
        pids.forEach(function (pid) {
          if (row.slots.length) row.breaks.push(row.slots.length);
          row.papers.push({ pid: pid, from: row.slots.length, count: paperSequence[pid].length });
          paperSequence[pid].forEach(function (i) {
            scaleSlot[i] = { row: scaleRows.length, at: row.slots.length };
            row.slots.push(i);
          });
        });
        if (row.slots.length) scaleRows.push(row);
      });
      scalePitch = Infinity;
      scaleRows.forEach(function (row) { scalePitch = Math.min(scalePitch, (row.hi - row.lo) / row.slots.length); });
      scalePitch = isFinite(scalePitch) ? scalePitch * SCALE_FILL : 0;
      scaleRows.forEach(function (row) {
        row.from = (row.lo + row.hi) / 2 - row.slots.length * scalePitch / 2;
      });
      penFrom = -Math.PI / 2;
      var nearest = Infinity;
      sectorGaps().forEach(function (gap) {
        var d = Math.abs(shortArc(-Math.PI / 2, gap));
        if (d < nearest) { nearest = d; penFrom = gap; }
      });
    }
    // The angle of a place on the scale: 0 is the start of its sector's run,
    // a whole number the edge between two results.
    function slotAngle(row, at) {
      return row.from + at * scalePitch;
    }
    // Half way across each gap between two sectors.
    function sectorGaps() {
      var sorted = bands.slice().sort(function (a, c) { return a.lo - c.lo; });
      var out = [];
      if (sorted.length < 2) return out;
      for (var s = 0; s < sorted.length; s++) {
        var cur = sorted[s], nxt = sorted[(s + 1) % sorted.length];
        out.push((cur.hi + nxt.lo + (s + 1 === sorted.length ? Math.PI * 2 : 0)) / 2);
      }
      return out;
    }
    var TURN = Math.PI * 2;
    // The short way round from one angle to another.
    function shortArc(from, to) {
      var d = (to - from) % TURN;
      if (d > Math.PI) d -= TURN;
      if (d < -Math.PI) d += TURN;
      return d;
    }

    // Room the scale gives up in this frame: under the plates and leaders,
    // and inside the reticles, no tick is drawn.
    var scaleYield = [];
    function yields(x0, y0, x1, y1) {
      var a = Math.min(x0, x1) - 0.5, b = Math.max(x0, x1) + 0.5, c = Math.min(y0, y1) - 0.5, d = Math.max(y0, y1) + 0.5;
      for (var j = 0; j < scaleYield.length; j++) {
        var q = scaleYield[j];
        if (a < q.x1 && b > q.x0 && c < q.y1 && d > q.y0) return true;
      }
      return false;
    }
    /* The scale, drawn. While a result or a paper is in focus that paper's
       run keeps its ink; with any other object of a sector, the sector's
       runs do; the rest recedes with the field. */
    function drawScale(focus, w, h) {
      if (!scaleR) return;
      var ra = revealAlpha(3);
      if (ra <= 0.01) return;
      var R = seatedScaleR();
      var f = focus >= 0 ? nodes[focus] : null, litPaper = null, litSectors = null;
      if (f && f.kind === 'paper_statement') litPaper = f.paperId;
      else if (f && f.kind === 'paper') litPaper = String(f.id).replace(/^paper:/, '');
      else if (f && f.sector && f.kind !== 'universe' && f.kind !== 'integration_surface') litSectors = sectorProblems(f);
      var rest = dimmed(0.4);
      var pitch = scalePitch * R, finest = 0;
      for (var l = 1; l < SCALE_TICKS.length; l++) {
        if (pitch * SCALE_TICKS[l][0] / hairPx >= SCALE_PITCH) finest = l;
      }
      var buckets = {}, order = [];
      function put(alpha, a, len) {
        if (alpha <= 0.01) return;
        var c = Math.cos(a), s = Math.sin(a);
        var x0 = view.tx + c * R, y0 = view.ty + s * R;
        if (x0 < -12 || y0 < -12 || x0 > w + 12 || y0 > h + 12) return;
        var x1 = view.tx + c * (R + len), y1 = view.ty + s * (R + len);
        if (yields(x0, y0, x1, y1)) return;
        var key = Math.round(alpha * 50);
        if (!buckets[key]) { buckets[key] = []; order.push(key); }
        buckets[key].push(x0, y0, x1, y1);
      }
      scaleRows.forEach(function (row) {
        var sectorOn = !litSectors || litSectors.indexOf(row.sector) !== -1;
        row.papers.forEach(function (paper) {
          var dim = (litPaper ? paper.pid === litPaper : sectorOn) ? 1 : rest;
          for (var j = 0; j < paper.count; j++) {
            var c = j + 1, level = SCALE_TICKS.length - 1;
            for (var q = 0; q < SCALE_TICKS.length - 1; q++) {
              if (c % SCALE_TICKS[q][0] === 0) { level = q; break; }
            }
            if (level > finest) continue;
            var ta = slotAngle(row, paper.from + j + 0.5);
            put(SCALE_TICKS[level][2] * dim * ra * setAt(ta), ta, SCALE_TICKS[level][1]);
          }
        });
        // Between the two papers.
        row.breaks.forEach(function (at) {
          var ba = slotAngle(row, at);
          put(0.55 * (sectorOn && !litPaper ? 1 : rest) * ra * setAt(ba), ba, SCALE_PAPER);
        });
      });
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = hairPx;
      ctx.lineCap = 'butt';
      order.forEach(function (key) {
        var run = buckets[key];
        ctx.globalAlpha = key / 50;
        ctx.beginPath();
        for (var j = 0; j < run.length; j += 4) {
          ctx.moveTo(run[j], run[j + 1]);
          ctx.lineTo(run[j + 2], run[j + 3]);
        }
        ctx.stroke();
      });
      // The boundaries between sectors are its strongest marks.
      var gaps = sectorGaps(), any = false;
      ctx.beginPath();
      gaps.forEach(function (mid) {
        var c = Math.cos(mid), s = Math.sin(mid);
        var x0 = view.tx + c * (R - 1.5), y0 = view.ty + s * (R - 1.5);
        var x1 = view.tx + c * (R + SCALE_MARK), y1 = view.ty + s * (R + SCALE_MARK);
        if (yields(x0, y0, x1, y1) || setAt(mid) < 1) return;
        ctx.moveTo(x0, y0);
        ctx.lineTo(x1, y1);
        any = true;
      });
      if (any) {
        ctx.globalAlpha = (0.72 - 0.2 * (focus >= 0 ? focusMix : 0)) * ra;
        ctx.lineWidth = hairPx * 2;
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }

    /* The cursor: a fine bar across the scale on the tick of the pinned
       result, cut clear of the ticks beside it. It is the map's own mark of
       the card's "Result 93 of 204": walking the paper with the arrow keys
       or the card's buttons moves both together, the short way round, in a
       little under a quarter of a second. Pinned from rest it appears where
       it belongs, without travel; let go, it holds a moment and fades where
       it stands. It never moves by itself, and a hover elsewhere leaves it
       where it is. */
    var CURSOR_MOVE = 220, CURSOR_IN = 140, CURSOR_HOLD = 140, CURSOR_OUT = 220;
    var cursor = { angle: 0, alpha: 0, target: null, turn: null, fade: null, frame: 0, of: -1 };
    function cursorTarget() {
      var i = pageMode ? selected : -1;
      if (i < 0 || !scaleR || !nodes[i] || !visible(nodes[i])) return null;
      var slot = scaleSlot[i];
      if (!slot) return null;
      return slotAngle(scaleRows[slot.row], slot.at + 0.5);
    }
    function aimCursor(force) {
      var to = cursorTarget();
      if (to === cursor.target && !force) return;
      cursor.target = to;
      // The result it marks, kept while it fades, so its tie fades with it.
      if (to !== null) cursor.of = selected;
      var still = force || reduceMotion || !window.requestAnimationFrame || document.hidden || !onScreen;
      if (to === null) {
        cursor.turn = null;
        if (still || cursor.alpha <= 0) { cursor.alpha = 0; cursor.fade = null; }
        else cursor.fade = { from: cursor.alpha, to: 0, dur: CURSOR_OUT, delay: CURSOR_HOLD, start: null };
      } else {
        if (still || cursor.alpha < 0.02) {
          cursor.angle = to;
          cursor.turn = null;
        } else {
          cursor.turn = { from: cursor.angle, by: shortArc(cursor.angle, to), start: null };
        }
        if (still) { cursor.alpha = 1; cursor.fade = null; }
        else if (cursor.alpha < 1) cursor.fade = { from: cursor.alpha, to: 1, dur: CURSOR_IN * (1 - cursor.alpha), delay: 0, start: null };
        else cursor.fade = null;
      }
      if (!still && (cursor.turn || cursor.fade) && !cursor.frame) cursor.frame = requestMotionFrame(stepCursor);
    }
    function stepCursor(now) {
      cursor.frame = 0;
      var busy = false;
      var tt = cursor.turn;
      if (tt) {
        if (tt.start === null) tt.start = now;
        var p = Math.min(1, (now - tt.start) / CURSOR_MOVE);
        cursor.angle = tt.from + tt.by * easeInOut(p);
        if (p < 1) busy = true; else cursor.turn = null;
      }
      var f = cursor.fade;
      if (f) {
        if (f.start === null) f.start = now;
        var q = Math.max(0, Math.min(1, (now - f.start - f.delay) / Math.max(1, f.dur)));
        cursor.alpha = f.from + (f.to - f.from) * (1 - (1 - q) * (1 - q));
        if (q < 1) busy = true; else cursor.fade = null;
      }
      if (busy) cursor.frame = requestMotionFrame(stepCursor);
      draw();
    }
    /* A fine dotted tie runs from the pinned result to its cursor, so the
       dot's place in the band and its place in its paper read as the same
       result, however far round the sector the two stand. It is laid under
       the marks, which stand over it, and walks with the cursor. */
    // The cursor's bar across the scale, [x0, y0, x1, y1], while it shows.
    function cursorBar() {
      if (!scaleR || cursor.alpha <= 0.01) return null;
      var R = seatedScaleR();
      var c = Math.cos(cursor.angle), s = Math.sin(cursor.angle);
      return [view.tx + c * (R - 4), view.ty + s * (R - 4), view.tx + c * (R + SCALE_MARK), view.ty + s * (R + SCALE_MARK)];
    }
    // Its room, taken when the frame is placed, so a reticle corner gives
    // way to it.
    function cursorRoom() {
      var bar = cursorBar();
      if (!bar) return null;
      return { x0: Math.min(bar[0], bar[2]) - 2, x1: Math.max(bar[0], bar[2]) + 2,
               y0: Math.min(bar[1], bar[3]) - 2, y1: Math.max(bar[1], bar[3]) + 2, owner: -2 };
    }
    function drawCursor(rs) {
      var bar = cursorBar();
      if (!bar) return;
      var x0 = bar[0], y0 = bar[1], x1 = bar[2], y1 = bar[3];
      var m = cursor.of >= 0 ? nodes[cursor.of] : null;
      if (m && visible(m)) {
        var mx = m.x * view.k + view.tx, my = m.y * view.k + view.ty;
        var vx = x0 - mx, vy = y0 - my, len = Math.sqrt(vx * vx + vy * vy);
        var from = reticleSize(m, rs) + 2;
        if (len > from + 4) {
          ctx.globalAlpha = 0.6 * cursor.alpha;
          ctx.strokeStyle = palette.ink;
          ctx.lineWidth = hairPx;
          ctx.lineCap = 'butt';
          ctx.setLineDash([1.5, 2.5]);
          ctx.beginPath();
          ctx.moveTo(mx + vx / len * from, my + vy / len * from);
          ctx.lineTo(x0, y0);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      }
      ctx.lineCap = 'butt';
      ctx.globalAlpha = cursor.alpha;
      ctx.strokeStyle = palette.ground;
      ctx.lineWidth = hairPx * 6;
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
      ctx.stroke();
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = hairPx * 2;
      ctx.beginPath();
      ctx.moveTo(x0, y0);
      ctx.lineTo(x1, y1);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    /* A reticle: four corner ticks round the object in focus, a target
       lock, on the square that touches the mark's focus ring at four points.
       It eases in from a third wider over a seventh of a second, once for
       each new focus; the pinned object keeps its own, a little firmer. A
       result's or claim's plate hangs off it on a leader. Comparator and
       Palomar, whose reach is the whole ring, answer with their lit bands
       instead. */
    var RETICLE_IN = 140, RETICLE_FROM = 1.35;
    function reticleSize(n, rs) {
      var r = n.r * rs + 1.5;
      return n.kind === 'problem' ? r + 7.5 : r + 5;
    }
    function reticleEase(i) {
      if (pulse.at !== i) return 1;
      return 1 - Math.pow(1 - Math.min(1, Math.max(0, pulse.ms) / RETICLE_IN), 3);
    }
    // The objects that carry a reticle in this frame, with the square each
    // settles on.
    function reticleTargets(rs, w, h) {
      var out = [];
      [selected, hover].forEach(function (at, k) {
        if (at < 0 || (k === 1 && at === selected) || !nodes[at] || !visible(nodes[at])) return;
        var n = nodes[at];
        if (n.kind === 'integration_surface') return;
        var x = n.x * view.k + view.tx, y = n.y * view.k + view.ty;
        if (x < -60 || y < -60 || x > w + 60 || y > h + 60) return;
        var s = reticleSize(n, rs);
        out.push({ at: at, x: x, y: y, s: s, box: { x0: x - s - 2, x1: x + s + 2, y0: y - s - 2, y1: y + s + 2 } });
      });
      return out;
    }
    // Drawn after every name is placed: a corner a name, a plate or the
    // cursor already holds is left out, and the corners drawn take their room.
    function drawReticles(rs, w, h) {
      reticleTargets(rs, w, h).forEach(function (t) {
        var e = reticleEase(t.at);
        if (e <= 0.01) return;
        var size = t.s * (RETICLE_FROM - (RETICLE_FROM - 1) * e);
        var x0 = snapX(t.x - size), x1 = snapX(t.x + size), y0 = snapY(t.y - size), y1 = snapY(t.y + size);
        var ax = Math.max(hairX * 4, snapX(Math.max(3, Math.min(8, size * 0.3)))),
            ay = Math.max(hairY * 4, snapY(Math.max(3, Math.min(8, size * 0.3))));
        // On the landing a kept result's frame is ember, quiet and plain
        // beside the ink frame of whatever the pointer is on.
        var kept = !pageMode && t.at === selected;
        ctx.globalAlpha = e * (t.at === selected ? (kept ? 0.95 : 0.92) : 0.72);
        ctx.fillStyle = kept ? palette.ember : palette.ink;
        // Each corner is one horizontal and one vertical run that meet
        // without overlapping, so no corner pixel is inked twice.
        [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]].forEach(function (c) {
          var hx = c[2] > 0 ? c[0] : c[0] - ax, vx = c[2] > 0 ? c[0] : c[0] - hairX;
          var hy = c[3] > 0 ? c[1] : c[1] - hairY, vy = c[3] > 0 ? c[1] + hairY : c[1] - ay;
          var box = { x0: Math.min(hx, vx) - 1, x1: Math.max(hx + ax, vx + hairX) + 1,
                      y0: Math.min(hy, vy) - 1, y1: Math.max(hy + hairY, vy + ay - hairY) + 1, owner: t.at };
          if (labelCollides(box)) return;
          ctx.fillRect(hx, hy, ax, hairY);
          ctx.fillRect(vx, vy, hairX, ay - hairY);
          labelBoxes.push(box);
        });
        ctx.globalAlpha = 1;
      });
    }
    // A leader, as runs of hairline: [x0, y0, x1, y1] each, level or upright.
    function drawLeader(runs, alpha, color) {
      if (!runs || !runs.length || alpha <= 0.01) return;
      ctx.globalAlpha = alpha;
      ctx.fillStyle = color || palette.ink;
      for (var j = 0; j < runs.length; j++) {
        var run = runs[j];
        if (run[1] === run[3]) {
          var a = snapX(Math.min(run[0], run[2])), b = snapX(Math.max(run[0], run[2]));
          if (b - a >= hairX) ctx.fillRect(a, snapY(run[1] - hairY / 2), b - a, hairY);
        } else {
          var c = snapY(Math.min(run[1], run[3])), d = snapY(Math.max(run[1], run[3]));
          if (d - c >= hairY) ctx.fillRect(snapX(run[0] - hairX / 2), c, hairX, d - c);
        }
      }
      ctx.globalAlpha = 1;
    }
    // The room a leader takes, so no label is set across it.
    function leaderBoxes(runs, owner) {
      return (runs || []).map(function (run) {
        return { x0: Math.min(run[0], run[2]) - 2, x1: Math.max(run[0], run[2]) + 2,
                 y0: Math.min(run[1], run[3]) - 2, y1: Math.max(run[1], run[3]) + 2, owner: owner };
      });
    }

    /* ---- Visibility ---------------------------------------------------- */
    /* Nothing is painted while the canvas is out of view (the landing's
       atlas slides it off screen) or its tab is hidden: a paint asked for
       then waits and is made once, when the canvas is back. Leaving view
       brings every motion to where it was going, so an opening cut short is
       spent rather than replayed. */
    var onScreen = true, paintPending = false;
    // The canvas box in device pixels, when the browser reports it.
    var deviceBox = null;
    function settleMotion() {
      // An opening under way is spent; one still waiting for the teaser to
      // come into view stays closed, so its first view is the assembly and
      // never a flash of the finished field.
      if (reveal < 1 && revealStarted) { reveal = 1; revealMs = 1e9; }
      if (revealFrame) { cancelMotionFrame(revealFrame); revealFrame = 0; }
      if (pulse.frame) { cancelMotionFrame(pulse.frame); pulse.frame = 0; }
      pulse.ms = 1e9;
      if (focusFrame) { cancelMotionFrame(focusFrame); focusFrame = 0; }
      if (focusFade) {
        focusMix = focusFade.to;
        if (focusFade.to === 0) focusHeld = -1;
        focusFade = null;
      }
      if (cameraFrame) { cancelMotionFrame(cameraFrame); cameraFrame = 0; }
      if (cameraGoal) cameraGoal(true);
      if (cursor.frame) { cancelMotionFrame(cursor.frame); cursor.frame = 0; }
      if (cursor.turn) { cursor.angle = cursor.turn.from + cursor.turn.by; cursor.turn = null; }
      if (cursor.fade) { cursor.alpha = cursor.fade.to; cursor.fade = null; }
      if (arrival.frame) { cancelMotionFrame(arrival.frame); arrival.frame = 0; }
      arrival.ms = 1e9;
      // With nothing left to advance, the shared frame is given back too.
      if (motionFrame && !Object.keys(motionCallbacks).length && window.cancelAnimationFrame) {
        window.cancelAnimationFrame(motionFrame);
        motionFrame = 0;
      }
      paintPending = true;
    }

    /* The field assembles from the centre out, one ring at a time, in
       reading order: the core, the orbit, the claims, the results with
       their scale, then the words. Each ring arrives with its structure (the
       orbit's line, the plates' rulings, the boundaries) and seats: it comes
       up from a fortieth inside its place and stops there, decelerating
       hard, so each lands with a definite stop rather than a drift. One
       layer never cuts through a mark or a letter, the rings are 110ms
       apart, and the whole opening takes a little over 0.8s. */
    /* The results ring is laid down rather than faded up (6 October 2026):
       once its plates are in place a pen runs once round the ring, clockwise
       from twelve o'clock, ruling the plates' edges as it goes, and each
       result sets into its plate as the pen passes it, its tick on the scale
       with it. The ring is the papers laid end to end, so the pen walks the
       record in the order the papers state it. The pen eases off the mark
       and then runs at one speed; the whole ring takes a little over half a
       second and the opening about a second. */
    var reveal = 1, revealMs = 1e9, revealFrame = 0, revealStarted = false;
    var REVEAL_DELAY = [0, 110, 220, 330, 600], REVEAL_FADE = 300, REVEAL_SEAT = 0.025;
    var SWEEP = 560, SWEEP_EASE = 0.15, SWEEP_SET = 0.3;
    var REVEAL_END = Math.max(REVEAL_DELAY[4] + REVEAL_FADE,
                              REVEAL_DELAY[3] + SWEEP * (1 + SWEEP_EASE / 2 + SWEEP_SET));
    // How far round the pen has come, as a share of the turn (beyond 1 once
    // it has passed twelve o'clock again; 2 when the opening is over).
    function penAt() {
      if (reveal >= 1) return 2;
      var t = (revealMs - REVEAL_DELAY[3]) / SWEEP;
      if (t <= 0) return 0;
      return t < SWEEP_EASE ? t * t / (2 * SWEEP_EASE) : t - SWEEP_EASE / 2;
    }
    // A place on the ring as a share of the turn, clockwise from where the
    // pen sets off: the division between two sectors nearest twelve
    // o'clock, so no sector is laid down in two halves.
    var penFrom = -Math.PI / 2;
    function turnShare(angle) {
      var a = (angle - penFrom) % TURN;
      return (a < 0 ? a + TURN : a) / TURN;
    }
    // How far a result at this angle has set (0 to 1).
    function setAt(angle) {
      if (reveal >= 1) return 1;
      var t = (penAt() - turnShare(angle)) / SWEEP_SET;
      return t <= 0 ? 0 : t >= 1 ? 1 : 1 - Math.pow(1 - t, 3);
    }
    function revealAlpha(layer) {
      if (reveal >= 1) return 1;
      var t = (revealMs - REVEAL_DELAY[layer]) / REVEAL_FADE;
      if (t <= 0) return 0;
      return t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
    }
    // A ring's radial seat during the opening: its scale about the centre.
    function seatOf(layer) {
      if (reveal >= 1) return 1;
      var t = (revealMs - REVEAL_DELAY[layer]) / REVEAL_FADE;
      if (t >= 1) return 1;
      return 1 - REVEAL_SEAT * Math.pow(1 - Math.max(0, t), 4);
    }
    function layerK(layer) {
      return reveal >= 1 ? view.k : view.k * seatOf(layer);
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
      revealStarted = true;
      var step = function (now) {
        revealFrame = 0;
        if (start === null) start = now;
        revealMs = now - start;
        if (revealMs >= REVEAL_END) reveal = 1;
        draw();
        if (reveal < 1) revealFrame = requestMotionFrame(step);
      };
      revealFrame = requestMotionFrame(step);
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
      if (revealFrame) cancelMotionFrame(revealFrame);
      revealFrame = 0;
      if (pulse.frame && window.cancelAnimationFrame) cancelMotionFrame(pulse.frame);
      pulse.frame = 0;
      pulse.ms = 1e9;
      if (focusFrame && window.cancelAnimationFrame) cancelMotionFrame(focusFrame);
      focusFrame = 0;
      focusFade = null;
      focusHeld = -1;
      focusMix = 1;
      if (cursor.frame) cancelMotionFrame(cursor.frame);
      cursor.frame = 0;
      aimCursor(true);
      if (arrival.frame) cancelMotionFrame(arrival.frame);
      arrival.frame = 0;
      arrival.ms = 1e9;
      if (overviewReady) draw();
    }
    if (reduceQuery && typeof reduceQuery.addEventListener === 'function') {
      reduceQuery.addEventListener('change', followReduceMotion);
    } else if (reduceQuery && typeof reduceQuery.addListener === 'function') {
      reduceQuery.addListener(followReduceMotion);
    }
    // A move under way lands where it was going if the canvas leaves view.
    var cameraGoal = null;
    /* A drill lights what it is about to frame before it moves (delay, in
       ms): the lit slice comes up, then the camera travels to it. Plates
       wait while the camera moves (a name re-placed on every frame of a move
       jumped from side to side) and arrive once it has settled. */
    function cameraTo(target, fitted, delay) {
      var w = canvas.clientWidth, h = canvas.clientHeight;
      if (cameraFrame && window.cancelAnimationFrame) cancelMotionFrame(cameraFrame);
      cameraFrame = 0;
      var finish = function (quiet) {
        cameraGoal = null;
        view.k = target.k; view.tx = target.tx; view.ty = target.ty;
        viewIsFitted = !!fitted;
        if (!quiet) draw();
      };
      cameraGoal = finish;
      if (reduceMotion || !window.requestAnimationFrame || !w || !onScreen) { finish(); return; }
      var from = { k: view.k, cx: (w / 2 - view.tx) / view.k, cy: (h / 2 - view.ty) / view.k };
      var to = { k: target.k, cx: (w / 2 - target.tx) / target.k, cy: (h / 2 - target.ty) / target.k };
      // Slow in and slow out, as statistical-graphics studies recommend for
      // a move the eye must follow (Heer and Robertson 2007); a deeper zoom
      // takes a little longer, never more than two thirds of a second.
      var start = null;
      var duration = Math.min(650, 300 + 120 * Math.abs(Math.log(to.k / from.k) / Math.LN2));
      /* A long way at a close scale (one sector's results to another's)
         flies: the view draws back part way over the ring and comes down on
         the new place, the path van Wijk and Nuij (2003) showed is the
         shortest for the eye, so the reader sees where they are going
         instead of a blur of marks sliding past. A short move keeps the
         straight glide. The flight takes as long as its path, up to 0.9s. */
      var flight = flightPath(from, to, Math.max(w, h));
      if (flight) duration = Math.max(duration, Math.min(900, flight.ms));
      viewIsFitted = false;
      var step = function (now) {
        if (start === null) start = now + (delay || 0);
        var t = Math.max(0, Math.min(1, (now - start) / duration));
        var e = easeInOut(t);
        var k, cx, cy;
        if (flight) {
          var at = flight.at(e);
          k = at[2]; cx = at[0]; cy = at[1];
        } else {
          k = from.k * Math.pow(to.k / from.k, e);
          cx = from.cx + (to.cx - from.cx) * e; cy = from.cy + (to.cy - from.cy) * e;
        }
        view.k = k; view.tx = w / 2 - cx * k; view.ty = h / 2 - cy * k;
        draw();
        if (t < 1) cameraFrame = requestMotionFrame(step);
        else { cameraFrame = 0; finish(); plateArrival(); }
      };
      cameraFrame = requestMotionFrame(step);
    }
    /* The smooth zoom path between two views (van Wijk and Nuij, "Smooth
       and efficient zooming and panning", 2003; the form d3's
       interpolateZoom uses). A view is its centre and the width of the field
       it shows; RHO sets how far the path draws back. Used only when the
       move crosses more than the view's own width at a close scale, where a
       straight glide would sweep the reader across marks too fast to read. */
    var RHO = 1.4;
    function flightPath(from, to, span) {
      var w0 = span / from.k, w1 = span / to.k;
      var dx = to.cx - from.cx, dy = to.cy - from.cy, d2 = dx * dx + dy * dy, u1 = Math.sqrt(d2);
      if (!(u1 > Math.min(w0, w1) * 0.9) || from.k <= fittedScale * 1.25 || to.k <= fittedScale * 1.25) return null;
      var rho2 = RHO * RHO, rho4 = rho2 * rho2;
      var b0 = (w1 * w1 - w0 * w0 + rho4 * d2) / (2 * w0 * rho2 * u1);
      var b1 = (w1 * w1 - w0 * w0 - rho4 * d2) / (2 * w1 * rho2 * u1);
      var r0 = Math.log(Math.sqrt(b0 * b0 + 1) - b0), r1 = Math.log(Math.sqrt(b1 * b1 + 1) - b1);
      var S = (r1 - r0) / RHO;
      if (!isFinite(S) || S <= 0) return null;
      var cosh = function (x) { return (Math.exp(x) + Math.exp(-x)) / 2; };
      var sinh = function (x) { return (Math.exp(x) - Math.exp(-x)) / 2; };
      var tanh = function (x) { var e2 = Math.exp(2 * x); return (e2 - 1) / (e2 + 1); };
      var c0 = cosh(r0);
      return {
        ms: S * 1000 * RHO / Math.SQRT2 * 0.62,
        at: function (t) {
          var s = t * S;
          var u = w0 / rho2 * (c0 * tanh(RHO * s + r0) - sinh(r0));
          var wide = w0 * c0 / cosh(RHO * s + r0);
          if (t >= 1) return [to.cx, to.cy, to.k];
          return [from.cx + u * dx / u1, from.cy + u * dy / u1, span / wide];
        }
      };
    }
    // Plates arrive over a sixth of a second once a camera move has settled.
    var PLATE_IN = 160, arrival = { ms: 1e9, frame: 0 };
    function plateArrival() {
      if (arrival.frame) cancelMotionFrame(arrival.frame);
      arrival.frame = 0;
      arrival.ms = 1e9;
      if (reduceMotion || !window.requestAnimationFrame || document.hidden || !onScreen) return;
      var start = null;
      arrival.ms = 0;
      var step = function (now) {
        if (start === null) start = now;
        arrival.ms = now - start;
        arrival.frame = arrival.ms < PLATE_IN ? requestMotionFrame(step) : 0;
        draw();
      };
      arrival.frame = requestMotionFrame(step);
    }
    function plateEase(ms) {
      return 1 - Math.pow(1 - Math.min(1, Math.max(0, ms) / PLATE_IN), 2);
    }
    function frameOf(indices, maxK, sector) {
      // A large canvas (a monitor) may come closer: the closest scale grows
      // with the window past a laptop's, so a framed sector fills a wide
      // screen as it fills a laptop's instead of shrinking into its middle.
      maxK *= Math.max(1, Math.min(canvas.clientWidth / 1000, canvas.clientHeight / 840));
      var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      var take = function (x, y) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      };
      indices.forEach(function (i) { take(nodes[i].x, nodes[i].y); });
      /* In the explorer a framed sector keeps its band's title in view: the
         title's two lines stand beyond the band, by their own reach in
         pixels, so the frame takes in the place they stand at the closest
         scale it allows (at a wider one they stand nearer, in the pad). */
      var band = inExplorer && sector ? bands.filter(function (b) { return b.sector === sector; })[0] : null;
      var outer = band ? bandRadii(band)[1] : 0;
      if (band && isFinite(outer) && outer > 0) {
        var mid = (band.lo + band.hi) / 2, reachR = outer + 6 + pageWordsReach() / maxK;
        take(reachR * Math.cos(mid), reachR * Math.sin(mid));
      }
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

    // The beat between a drill lighting its target and the camera leaving.
    var DRILL_BEAT = 90, RESULT_RUN = 6;
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
        cameraTo(frameOf(members, 3, n.sector), false, DRILL_BEAT);
        return;
      }
      // A paper frames its own results, the run its card walks.
      if (n.kind === 'paper') {
        var run = (paperSequence[String(n.id).replace(/^paper:/, '')] || []).filter(function (j) { return visible(nodes[j]); });
        if (run.length) { cameraTo(frameOf(run.concat([i]), 3, nodes[run[0]].sector), false, DRILL_BEAT); return; }
      }
      /* A result arrives among what explains it (7 October 2026): the run
         of its paper either side of it, close enough to read their numbers,
         and its band's title, so the frame shows where in the paper and the
         programme it stands rather than a lone dot in an empty region. Its
         far relations (the centre, Comparator) are left to their threads,
         which name them at the window's edge. */
      if (n.kind === 'paper_statement') {
        // Already in a readable view, well inside it: the reader's frame stays.
        var nx = n.x * view.k + view.tx, ny = n.y * view.k + view.ty;
        if (view.k >= 2.2 && nx > 90 && ny > 90 && nx < canvas.clientWidth - 90 && ny < canvas.clientHeight - 90) return;
        var seq = (paperSequence[n.paperId] || []).filter(function (j) { return visible(nodes[j]); });
        var at = seq.indexOf(i), local = [i];
        if (at >= 0) local = seq.slice(Math.max(0, at - RESULT_RUN), at + RESULT_RUN + 1);
        if (local.indexOf(i) < 0) local.push(i);
        var framed = frameOf(local, 3.4, n.sector);
        if (framed.k < 2.2) framed = { k: 2.2, tx: canvas.clientWidth / 2 - n.x * 2.2, ty: canvas.clientHeight / 2 - n.y * 2.2 };
        // The result itself stays well inside the frame, whatever its run.
        var sx = n.x * framed.k + framed.tx, sy = n.y * framed.k + framed.ty, inset = 90;
        framed.tx += Math.max(0, inset - sx) - Math.max(0, sx - (canvas.clientWidth - inset));
        framed.ty += Math.max(0, inset - sy) - Math.max(0, sy - (canvas.clientHeight - inset));
        cameraTo(framed, false);
        return;
      }
      var k = view.k < 1.1 ? 1.6 : view.k;
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
      // A mark that has dropped back is drawn in its own ink, faded (shade).
      color = shade(color);
      if (tier === 'ordinary_proof') {
        ctx.beginPath();
        ctx.moveTo(x, y - r * 1.25); ctx.lineTo(x + r * 1.25, y);
        ctx.lineTo(x, y + r * 1.25); ctx.lineTo(x - r * 1.25, y);
        ctx.closePath(); ctx.fillStyle = palette.ground; ctx.fill();
        ctx.strokeStyle = palette.paper ? shade(palette.paper) : color; ctx.lineWidth = 1.4; ctx.stroke();
        return;
      }
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
      var opening = reveal < 1;
      for (var j = 0; j < indices.length; j++) {
        var i = indices[j];
        var a = nodes[edges[i][0]], b = nodes[edges[i][1]];
        // While the rings seat, each end rides its own ring.
        var ak = opening ? layerK(revealLayer(a.kind)) : view.k, bk = opening ? layerK(revealLayer(b.kind)) : view.k;
        ctx.moveTo(a.x * ak + view.tx, a.y * ak + view.ty);
        ctx.lineTo(b.x * bk + view.tx, b.y * bk + view.ty);
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
        var f = nodes[focus], ref = referring(focus);
        ctx.strokeStyle = palette.integration_surface;
        ctx.setLineDash([3, 3]);
        for (var t = 0; t < twins.length; t++) {
          var m = nodes[twins[t].at];
          if (!m || !visible(m)) continue;
          // The counterpart in reference: the bridge a step heavier.
          var on = twins[t].at === ref;
          ctx.globalAlpha = on ? 0.9 + 0.1 * referMix : ref >= 0 ? 0.9 - 0.5 * referMix : 0.9;
          ctx.lineWidth = on ? 1.2 + 0.8 * referMix : 1.2;
          ctx.beginPath();
          ctx.moveTo(f.x * k + view.tx, f.y * k + view.ty);
          ctx.lineTo(m.x * k + view.tx, m.y * k + view.ty);
          ctx.stroke();
        }
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
      var k = layerK(1);
      var orbit = 0, count = 0;
      for (var pid in problemIndex) {
        var p = nodes[problemIndex[pid]];
        if (!p || !visible(p)) continue;
        orbit += Math.sqrt(p.x * p.x + p.y * p.y);
        count++;
      }
      if (!count) return;
      // A hairline: one device pixel, at the weight the old full pixel had.
      ctx.globalAlpha = revealAlpha(1);
      ctx.strokeStyle = palette.edge;
      ctx.lineWidth = hairPx;
      ctx.beginPath();
      ctx.arc(view.tx, view.ty, orbit / count * k, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    /* A problem is drawn as a small copy of the core, a ring round a point,
       in ink: colour on the field stays with the evidence, and the only
       colour a problem carries is its own evidence ring. */
    function drawProblemMark(n, x, y, r, ink, withRing) {
      ink = shade(ink);
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
        ctx.strokeStyle = shade(evidenceColor(key));
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
      var k = layerK(2), pad = 9;
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
      // Its two long edges are ruled, like an engraved scale, in hairline.
      ctx.globalAlpha = (state === 'off' ? 1 - 0.65 * focusMix : 1) * ra;
      ctx.strokeStyle = palette.edge;
      ctx.lineWidth = hairPx;
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
      // In a search most of the sector's marks step back, and a full wash
      // would become the heaviest thing on the canvas with almost nothing in
      // it; the region keeps its hairline edge and only a breath of tone.
      // Around a single result the region is its envelope, not its subject:
      // the plates and the result's own threads carry the tone.
      var wash = query.length >= 2 ? 0.16 : f.kind === 'paper_statement' ? 0.3 : 0.5;
      for (var i = 0; i < bands.length; i++) {
        var b = bands[i];
        if (pids.indexOf(b.sector) === -1) continue;
        var outer = (bandRadii(b)[1] + 12) * k;
        if (!(outer > inner)) continue;
        // One flat wash, edged with a hairline, like a highlighted region on
        // a printed chart.
        ctx.fillStyle = palette.halo;
        ctx.globalAlpha = wash * focusMix;
        ctx.beginPath();
        ctx.arc(view.tx, view.ty, outer, b.lo - 0.012, b.hi + 0.012);
        ctx.arc(view.tx, view.ty, inner, b.hi + 0.012, b.lo - 0.012, true);
        ctx.closePath();
        ctx.fill();
        ctx.globalAlpha = 0.42 * focusMix;
        ctx.lineWidth = hairPx;
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
      var k = layerK(3);
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
        // Both long edges are ruled, in hairline. The evidence gauge, which
        // repeats what the dots and the title already say, shows only for a
        // band in focus.
        // During the opening the pen rules each edge as it passes.
        var ruled = b.hi;
        if (reveal < 1) {
          var span = (b.hi - b.lo) / TURN;
          ruled = b.lo + (b.hi - b.lo) * Math.max(0, Math.min(1, (penAt() - turnShare(b.lo)) / (span || 1)));
        }
        if (ruled > b.lo + 1e-4) {
          ctx.globalAlpha = (state === 'off' ? 1 - 0.65 * focusMix : 1) * ra;
          ctx.strokeStyle = palette.edge;
          ctx.lineWidth = hairPx;
          ctx.beginPath();
          ctx.arc(view.tx, view.ty, (radii[1] + pad) * k, b.lo, ruled);
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(view.tx, view.ty, Math.max(0, (radii[0] - pad) * k), b.lo, ruled);
          ctx.stroke();
        }
        var total = 0, key;
        for (key in b.evidence) total += b.evidence[key];
        var at = b.lo, gaugeR = (radii[0] - pad - 5) * k;
        /* The gauge is the programme's whole tally (7 October 2026). With a
           single result in focus it is context, not the route being read,
           so it steps back to a hairline in its own colours: the long ember
           sweep no longer looks like the result's own thread, and the band's
           title still says the count in words. */
        var summary = focus >= 0 && nodes[focus] && nodes[focus].kind === 'paper_statement';
        if (total && gaugeR > 0 && state === 'on') {
          ctx.lineWidth = summary ? Math.max(1, hairPx * 1.5) : Math.max(1.6, 2.4 * Math.min(1, k / 0.6));
          ctx.lineCap = 'butt';
          var hair = 1.5 / gaugeR;
          for (var j = 0; j < EVIDENCE_ORDER.length; j++) {
            key = EVIDENCE_ORDER[j];
            if (!b.evidence[key]) continue;
            var to = at + (b.hi - b.lo) * b.evidence[key] / total;
            ctx.globalAlpha = (state === 'off' ? dimmed(0.35) : 1) * EVIDENCE_GAUGE_ALPHA[key] * (summary ? 0.55 : 1);
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
          ctx.globalAlpha = summary ? 0.35 : 0.9;
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
      // A fine line in each gap between two sectors, across the results
      // ring, marks the division. Where the scale is drawn the line runs on
      // into it as the scale's strongest mark.
      var gaps = sectorGaps();
      var r0 = Infinity, r1 = 0;
      bands.forEach(function (sb) { var rr = bandRadii(sb); r0 = Math.min(r0, rr[0]); r1 = Math.max(r1, rr[1]); });
      if (gaps.length && isFinite(r0)) {
        var tickTo = scaleR ? seatedScaleR() - 1.5 : (r1 + 12) * k;
        ctx.strokeStyle = palette.edge;
        ctx.lineWidth = hairPx * 1.5;
        for (var s = 0; s < gaps.length; s++) {
          var gapSet = setAt(gaps[s]);
          if (gapSet <= 0) continue;
          var cx = Math.cos(gaps[s]), sy = Math.sin(gaps[s]);
          ctx.globalAlpha = (focus >= 0 ? 0.6 : 1) * revealAlpha(3) * gapSet;
          ctx.beginPath();
          ctx.moveTo(view.tx + cx * (r0 - 16) * k, view.ty + sy * (r0 - 16) * k);
          ctx.lineTo(view.tx + cx * tickTo, view.ty + sy * tickTo);
          ctx.stroke();
        }
      }
      ctx.globalAlpha = 1;
    }

    /* Close in, a result shows its printed number above its dot, so a band
       reads as the paper's own sequence. */
    // Words that come with closeness come in with it (6 October 2026): over
    // the last stretch of a zoom to their scale they fade up, rather than
    // all appearing on the frame the threshold is crossed.
    function zoomIn(from, to) {
      var t = (view.k - from) / (to - from);
      if (t <= 0) return 0;
      if (t >= 1) return 1;
      return t * t * (3 - 2 * t);
    }
    function drawStatementNumbers(focus, near, searching, w, h) {
      var lod = zoomIn(2.4, 3);
      if (lod <= 0 || lensOff.paper_statement) return;
      ctx.globalAlpha = lod;
      ctx.font = face(600, TYPE.number);
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
        var box = { x0: x - half, x1: x + half, y0: ly - TYPE.number + 1, y1: ly + 2, owner: i };
        if (labelCollides(box)) continue;
        labelBoxes.push(box);
        ctx.strokeStyle = palette.ground;
        ctx.strokeText(n.num, x, ly);
        ctx.fillStyle = palette.faint;
        ctx.fillText(n.num, x, ly);
      }
      ctx.globalAlpha = 1;
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

    /* The band titles are laid out at the start of a frame, before the name
       plates are placed, so a plate can keep clear of them; they are drawn
       later, after the plates have taken their room. */
    // On the teaser a title within this angle of three or nine o'clock is
    // set level, out beside the scale, rather than turned on its side along
    // the ring, where its letters would lie at ninety degrees.
    var SIDE_COS = Math.cos(22.5 * Math.PI / 180), SIDE_GAP = 6;
    function sideOf(mid) {
      if (pageMode) return 0;
      var c = Math.cos(mid);
      return c >= SIDE_COS ? 1 : c <= -SIDE_COS ? -1 : 0;
    }
    // A band's two lines of words. Said as words, never as a fraction:
    // "20 of 20" on a small ring, whose centre reads "616 of 689 replayed"
    // beside Comparator, and "20 of 20 replayed" where the name has room.
    function bandWords(b, narrow) {
      var total = 0;
      for (var key in b.evidence) total += b.evidence[key];
      return { title: b.title ? (narrow ? b.title.split(' ')[0] : b.title) : '',
               count: (b.evidence.replayed || 0) + ' of ' + total + (narrow ? '' : ' replayed') };
    }
    // How far the teaser's words reach past the ring's outer plate on each
    // side, in pixels, for the fit: the arc titles' two lines beyond the
    // scale, and the level titles at the sides, measured in their own face.
    function titleExtents() {
      var arc = SCALE_GAP + SCALE_MARK + 4 + TYPE.title / 2 + TYPE.rowGap + TYPE.title / 2;
      var out = { top: arc, bottom: arc, left: arc, right: arc };
      bands.forEach(function (b) {
        var side = sideOf((b.lo + b.hi) / 2);
        if (!side) return;
        var words = bandWords(b, true);
        ctx.font = face(600, TYPE.title);
        var width = words.title ? ctx.measureText(words.title).width : 0;
        ctx.font = face(400, TYPE.count);
        width = Math.max(width, ctx.measureText(words.count).width);
        var reach = SCALE_GAP + SCALE_MARK + SIDE_GAP + width;
        if (side > 0) out.right = Math.max(out.right, reach);
        else out.left = Math.max(out.left, reach);
      });
      return out;
    }
    function bandLabelLayout(focus, w, h) {
      if (!bands.length || lensOff.paper_statement) return [];
      if (!pageMode && w < 520) return [];
      var k = view.k;
      var items = [];
      // A narrow field, or a ring drawn small, keeps the number and a
      // compact count: full names would run into each other. The ring
      // decides once, by its smallest band, so one title never reads in a
      // different style from its neighbours. The teaser always does: the
      // column beside it names every problem in full.
      var innermost = Infinity;
      for (var r0 = 0; r0 < bands.length; r0++) {
        var outer = bandRadii(bands[r0])[1];
        if (isFinite(outer)) innermost = Math.min(innermost, outer);
      }
      var narrow = !pageMode || w < 560 || innermost * k < 220;
      for (var i = 0; i < bands.length; i++) {
        var b = bands[i], radii = bandRadii(b);
        if (!isFinite(radii[1])) continue;
        var state = bandState(b, focus);
        if (state === 'off') continue;
        // A clear gap between the plate's edge and the first line of text;
        // with the scale drawn, every title stands outside it, all on one
        // circle. On the teaser the first line's middle stands half its
        // height and four pixels out from the tick ends, so its larger
        // letters clear them.
        var lift = SCALE_MARK + 4 + TYPE.title / 2;
        var base = pageMode ? Math.max((radii[1] + 6) * k + 15, scaleR ? scaleR + SCALE_MARK + 7 : 0) :
          Math.max((radii[1] + 6) * k + SCALE_GAP + lift, scaleR ? scaleR + lift : 0);
        var words = bandWords(b, narrow);
        var count = { text: words.count, font: face(400, TYPE.count), color: palette.muted, alpha: 1 };
        // A count never stands without its problem's number: wherever the
        // band labels show, so does the title, short on a narrow field.
        var title = words.title ?
          { text: words.title, font: face(600, TYPE.title), color: palette.ink, alpha: state === 'on' ? 1 : 0.86 } : null;
        var mid = (b.lo + b.hi) / 2;
        items.push({ band: b, base: base, mid: mid, side: sideOf(mid), count: count, title: title });
      }
      // Each label's half-width as an angle at its radius; a level title
      // takes its height along the ring instead.
      function halfSpan(item) {
        if (item.side) {
          var tall = (item.title ? TYPE.rowGap : 0) + (TYPE.title + TYPE.count) / 2;
          return (tall / 2 + 4) / item.base;
        }
        ctx.font = item.count.font;
        var width = ctx.measureText(item.count.text).width;
        if (item.title) {
          ctx.font = item.title.font;
          width = Math.max(width, ctx.measureText(item.title.text).width);
        }
        return width / (2 * (item.base + TYPE.rowGap)) + 0.02;
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
      return items.map(function (item) {
        if (item.side) return levelTitle(item);
        var lower = readsDownward(item.mid);
        // Reading downward the name sits inside the count; upward, outside.
        var rows = item.title ? (lower ? [item.title, item.count] : [item.count, item.title]) : [item.count];
        return { mid: item.mid, lower: lower, rows: rows.map(function (row, li) {
          var radius = item.base + li * TYPE.rowGap;
          return { row: row, radius: radius, box: arcRunBox(row, radius, item.mid),
                   boxes: pageMode ? null : arcRunBoxes(row, radius, item.mid) };
        }) };
      });
    }
    /* A title at three or nine o'clock, set level: the problem's number over
       its count, flush toward the ring, its column standing SIDE_GAP clear
       of the scale's tick ends over the whole height of its two lines. */
    function levelTitle(item) {
      var rows = item.title ? [item.title, item.count] : [item.count];
      var first = view.ty + item.base * Math.sin(item.mid) - (rows.length - 1) * TYPE.rowGap / 2;
      var top = first - TYPE.title / 2, bottom = first + (rows.length - 1) * TYPE.rowGap + TYPE.count / 2;
      var clearR = (scaleR || item.base - SCALE_MARK - 4 - TYPE.title / 2) + SCALE_MARK + SIDE_GAP;
      var dy = (top - view.ty) * (bottom - view.ty) <= 0 ? 0 :
        Math.min(Math.abs(top - view.ty), Math.abs(bottom - view.ty));
      var x = view.tx + item.side * Math.sqrt(Math.max(0, clearR * clearR - dy * dy));
      return { mid: item.mid, side: item.side, rows: rows.map(function (row, li) {
        ctx.font = row.font;
        var width = ctx.measureText(row.text).width, y = first + li * TYPE.rowGap;
        var size = row === item.title ? TYPE.title : TYPE.count;
        var x0 = item.side > 0 ? x : x - width;
        return { row: row, x: x, y: y, align: item.side > 0 ? 'left' : 'right',
                 box: { x0: x0 - 3, x1: x0 + width + 3, y0: y - size / 2 - 2, y1: y + size / 2 + 2 } };
      }) };
    }
    // Every band title's room is taken when the frame is placed, before
    // anything is drawn; a title under a name plate keeps its room.
    // The title lines' whole boxes in this frame: a thread is routed round
    // these (a few corners), while labels and the sector's index keep to
    // the finer chain along the letters.
    var titleRooms = [];
    function placeBandLabels(layout) {
      titleRooms = [];
      layout.forEach(function (item) {
        item.rows.forEach(function (r) {
          titleRooms.push(r.box);
          if (r.boxes) {
            r.boxes.forEach(function (b) { b.seg = true; labelBoxes.push(b); });
          } else labelBoxes.push(r.box);
        });
      });
    }
    function drawBandLabels(layout) {
      layout.forEach(function (item) {
        // Under a name plate both lines step aside together. Their room
        // stays taken, so no other label moves while the reader points.
        var covered = item.rows.some(function (r) { return (r.boxes || [r.box]).some(underPlate); });
        if (covered) return;
        item.rows.forEach(function (r) {
          if (item.side) drawLevelText(r);
          else drawArcText(r.row, r.radius, item.mid, item.lower);
        });
      });
      ctx.textBaseline = 'alphabetic';
      ctx.textAlign = 'center';
    }
    function drawLevelText(r) {
      ctx.font = r.row.font;
      ctx.textAlign = r.align;
      ctx.textBaseline = 'middle';
      ctx.lineWidth = 3;
      ctx.lineJoin = 'round';
      ctx.globalAlpha = r.row.alpha * revealAlpha(4);
      ctx.strokeStyle = palette.ground;
      ctx.strokeText(r.row.text, r.x, r.y);
      ctx.fillStyle = r.row.color;
      ctx.fillText(r.row.text, r.x, r.y);
      ctx.globalAlpha = 1;
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
    }
    // A run's room as a chain of small boxes along its letters. One box
    // round a run set diagonally is mostly empty corner, and a name that
    // fell in that corner was left out for nothing.
    function arcRunBoxes(row, radius, mid) {
      ctx.font = row.font;
      var span = arcLetters(row.text).width / radius, pad = TYPE.arcPad;
      var steps = Math.max(1, Math.ceil(span * radius / pad));
      var out = [];
      for (var e = 0; e <= steps; e++) {
        var a = mid - span / 2 + span * e / steps;
        var ex = view.tx + radius * Math.cos(a), ey = view.ty + radius * Math.sin(a);
        out.push({ x0: ex - pad, x1: ex + pad, y0: ey - pad, y1: ey + pad });
      }
      return out;
    }
    // A run's box, from its two ends and its middle, so later labels keep
    // clear of it (its room is taken when the frame is placed).
    function arcRunBox(row, radius, mid) {
      ctx.font = row.font;
      var span = arcLetters(row.text).width / radius, pad = TYPE.arcPad;
      var ends = [mid - span / 2, mid, mid + span / 2];
      var box = { x0: Infinity, x1: -Infinity, y0: Infinity, y1: -Infinity };
      for (var e = 0; e < ends.length; e++) {
        var ex = view.tx + radius * Math.cos(ends[e]), ey = view.ty + radius * Math.sin(ends[e]);
        box.x0 = Math.min(box.x0, ex - pad); box.x1 = Math.max(box.x1, ex + pad);
        box.y0 = Math.min(box.y0, ey - pad); box.y1 = Math.max(box.y1, ey + pad);
      }
      return box;
    }

    /* A shared block must remain named in the fitted overview. Its compact
       callout sits beyond the band titles, on the shared edge between the
       two sectors; the line runs from the block out along that edge, an
       annotation and not a graph relationship. Its place is decided when
       the frame is placed, after the band titles and before the anchors'
       names; it is drawn over the dots, so a band never covers it. */
    function placeCaptions(focus, w, h) {
      var out = [];
      for (var i = 0; i < captions.length; i++) {
        var c = captions[i];
        var cx = c.x * view.k + view.tx, cy = c.y * view.k + view.ty;
        if (cx < -160 || cy < -40 || cx > w + 160 || cy > h + 40) continue;
        if (view.k < 1.1) {
          var text = c.text.replace(/^shared by /, 'Shared claims: ');
          ctx.font = face(600, TYPE.callout);
          var half = ctx.measureText(text).width / 2 + 6, rise = TYPE.callout / 2 + 3;
          // Leave the map page's zoom controls their own column; on the
          // landing keep the words EDGE_CLEAR from the frame.
          var left = pageMode ? half : EDGE_CLEAR + half - 6;
          var right = pageMode ? Math.max(half, w - 74 - half) : w - EDGE_CLEAR - half + 6;
          var top = pageMode ? 14 : EDGE_CLEAR + rise, bottom = pageMode ? h - 14 : h - EDGE_CLEAR - rise;
          var cr = Math.sqrt(c.x * c.x + c.y * c.y) || 1;
          var dx = c.x / cr, dy = c.y / cr;
          var bandOuter = 0;
          for (var bi = 0; bi < bands.length; bi++) bandOuter = Math.max(bandOuter, bandRadii(bands[bi])[1] || 0);
          var fromR = c.reach ? c.reach + 6 : cr * 1.8;
          var toR = bandOuter ? bandOuter + 58 : cr * 2.35;
          var x = Math.max(left, Math.min(right, dx * toR * view.k + view.tx));
          var y = Math.max(top, Math.min(bottom, dy * toR * view.k + view.ty + 8));
          if (pageMode) {
            // On the page the words stand wholly outside the ring and its
            // scale: a line set level beside a ring at an angle reached
            // back over the results with its near end (it did, at 1280 by
            // 690). It moves out along its own direction until its box
            // clears the scale's ticks.
            var clearR = (bandOuter + 6) * view.k + SCALE_GAP + SCALE_MARK + 6;
            for (var out_t = Math.max(clearR, toR * view.k), it = 0; it < 80; it++, out_t += 4) {
              x = Math.max(left, Math.min(right, dx * out_t + view.tx));
              y = Math.max(top, Math.min(bottom, dy * out_t + view.ty + 8));
              if (distanceToBox(view.tx, view.ty, { x0: x - half, x1: x + half, y0: y - rise, y1: y + rise }) >= clearR) break;
            }
          }
          // The band titles are already placed. Pushed off its own edge by
          // the zoom controls, the name steps up or down until it clears them.
          var step = 2 * rise, shifts = [0, step, -step, 2 * step, -2 * step, 3 * step, -3 * step];
          for (var sh = 0; sh < shifts.length; sh++) {
            var tryY = Math.max(top, Math.min(bottom, y + shifts[sh]));
            if (!labelCollides({ x0: x - half, x1: x + half, y0: tryY - rise, y1: tryY + rise })) {
              y = tryY;
              break;
            }
          }
          var box = { x0: x - half, x1: x + half, y0: y - rise, y1: y + rise };
          labelBoxes.push(box);
          // Under a name plate the callout and its line step aside together.
          if (underPlate(box)) continue;
          out.push({ compact: true, caption: c, text: text, x: x, y: y, rise: rise,
                     from: [dx * fromR * view.k + view.tx, dy * fromR * view.k + view.ty] });
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
        out.push({ compact: false, caption: c, x: cx, y: cy, align: align });
      }
      return out;
    }
    function drawCaptions(plan, focus) {
      ctx.textBaseline = 'middle';
      plan.forEach(function (p) {
        var c = p.caption;
        if (p.compact) {
          // With a problem of its own in focus elsewhere, the callout drops
          // back with the field.
          var f = focus >= 0 ? nodes[focus] : null;
          var pair = String(c.sector || '').split('+');
          var related = !f || !f.sector || f.kind === 'universe' || f.kind === 'integration_surface' ||
            sectorProblems(f).some(function (pid) { return pair.indexOf(pid) !== -1; });
          ctx.globalAlpha = 0.85 * revealAlpha(4) * (related || pageMode ? 1 : 1 - 0.45 * focusMix);
          ctx.strokeStyle = palette.faint;
          ctx.lineWidth = 0.65;
          ctx.setLineDash([2, 3]);
          ctx.beginPath();
          ctx.moveTo(p.from[0], p.from[1]);
          ctx.lineTo(p.x, p.y - p.rise);
          ctx.stroke();
          ctx.setLineDash([]);
          ctx.font = face(600, TYPE.callout);
          ctx.textAlign = 'center';
          ctx.lineWidth = 3.5;
          ctx.strokeStyle = palette.ground;
          ctx.strokeText(p.text, p.x, p.y);
          ctx.fillStyle = palette.ink;
          ctx.fillText(p.text, p.x, p.y);
          ctx.globalAlpha = 1;
          return;
        }
        var cx = p.x, cy = p.y;
        ctx.textAlign = p.align;
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
      });
      ctx.textBaseline = 'alphabetic';
    }

    /* A hovered or selected result sits in a dense field, so its name goes
       beside it on a plate, toward the open side of the map, never across
       the band under it. Outward first; the other side only when it has
       more room. The name is read whole: a long one sets in two lines,
       broken where the two come out most nearly equal (three in a narrow
       room), and only a name too long even for that is shortened (the card
       has it whole). The plate stands clear of the mark's reticle and a little
       toward the open side of the field (up over its top half, down below),
       and a hairline leader leaves the reticle's corner on the plate's side
       and turns along to it; leaving from the corner, it never runs up the
       mark's radius into the scale. The place is chosen from six (beside
       either way, a little up or down, or hung under or over the mark), each
       in one, two or three lines, as the one that covers least of what the
       reader needs, the other marks of the field included: a plate laid
       over a band hides the very results it sits among. */
    var LEAD_RISE = 9, LEAD_RUN = 10, LEAD_GAP = 1.5;
    var PLATE_FONT = face(500, TYPE.plate), PLATE_LEAD = TYPE.lead, PLATE_ONE_LINE = TYPE.oneLine, LINE_COST = [0, 30, 250];
    // A plate's box above and below its first baseline, and the text's inset
    // from the box's side.
    var PLATE_UP = TYPE.ascent, PLATE_DOWN = TYPE.descent, PLATE_PAD = 9;
    // A name's balanced breaks into two and into three lines (the widest
    // line as narrow as it can be), measured once per name in the plate's
    // face.
    var plateBreaks = {};
    function balancedLines(text, count) {
      var key = count + '|' + text;
      if (Object.prototype.hasOwnProperty.call(plateBreaks, key)) return plateBreaks[key];
      var words = text.split(' '), best = null, b, c;
      var width = function (from, to) { return ctx.measureText(words.slice(from, to).join(' ')).width; };
      for (b = 1; b < words.length; b++) {
        if (count === 2) {
          var two = Math.max(width(0, b), width(b));
          if (!best || two < best.width) best = { lines: [words.slice(0, b).join(' '), words.slice(b).join(' ')], width: two };
          continue;
        }
        for (c = b + 1; c < words.length; c++) {
          var three = Math.max(width(0, b), width(b, c), width(c));
          if (!best || three < best.width) {
            best = { lines: [words.slice(0, b).join(' '), words.slice(b, c).join(' '), words.slice(c).join(' ')], width: three };
          }
        }
      }
      plateBreaks[key] = best;
      return best;
    }
    // As much of a name as fits two lines of the room: the first line takes
    // whole words, the second the rest, cut.
    function cutLines(text, room) {
      var words = text.split(' '), first = words[0];
      for (var b = 1; b < words.length; b++) {
        var more = first + ' ' + words[b];
        if (ctx.measureText(more).width > room) break;
        first = more;
      }
      var rest = text.slice(first.length + 1);
      if (!rest) return { lines: [clip(first, Math.max(8, Math.floor(first.length * room / ctx.measureText(first).width) - 1))], cut: 1 };
      var second = rest;
      if (ctx.measureText(second).width > room) {
        second = clip(rest, Math.max(6, Math.floor(rest.length * room / ctx.measureText(rest).width) - 1));
      }
      return { lines: [first, second], cut: rest.length - second.replace(/…$/, '').length };
    }
    // This frame's plates, by the object they name, placed once per frame;
    // and the pinned plate's place, kept while only the hover changes.
    var platePlaced = {}, pinnedPlate = null;
    // The side the last pinned plate took, so walking a paper keeps its
    // plates on one side while the room allows rather than flicking across.
    var plateHabit = null;
    // What a plate keeps clear of in the frame being drawn: the core, the two
    // checkers and the problems with the room their names take, and on the
    // landing the card's corner marks. A plate placed over one of them would
    // hide what the reader needs to find their way.
    var plateKeepOut = [];
    function keepOutBoxes(rs, w, h) {
      var out = [];
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (!visible(n) || (n.kind !== 'problem' && n.kind !== 'universe' && n.kind !== 'integration_surface')) continue;
        var x = n.x * view.k + view.tx, y = n.y * view.k + view.ty, r = n.r * rs;
        if (x < -80 || y < -80 || x > w + 80 || y > h + 80) continue;
        // The disc, with its focus ring and evidence ring: covering it hides
        // a mark, so it weighs most. Its name at rest weighs next: a name a
        // plate lies on is left out while the reader points. A band title
        // weighs least, since it steps aside and keeps its room.
        out.push({ x0: x - r - 4, x1: x + r + 4, y0: y - r - 4, y1: y + r + 4, weight: 6 });
        out.push({ x0: x - r - 9, x1: x + r + 9, y0: y - r - 9, y1: y + r + 9, weight: 1 });
        ctx.font = face(600, TYPE.anchor);
        var text = anchorText(n, w, false);
        var half = ctx.measureText(text).width / 2 + 6;
        var spot = n.kind === 'problem' ? problemLabelSpot(n, x, y, half, rs, w) : [x, y + r + TYPE.below];
        out.push({ x0: spot[0] - half, x1: spot[0] + half, y0: spot[1] - TYPE.anchor - 1, y1: spot[1] + 5, weight: 3, whole: true });
        if (n.sub && n.kind !== 'problem') {
          ctx.font = face(400, TYPE.sub);
          var sub = ctx.measureText(clip(n.sub, 36)).width / 2 + 4;
          out.push({ x0: x - sub, x1: x + sub, y0: spot[1] + 2, y1: spot[1] + TYPE.subGap + 5, weight: 2, whole: true });
        }
      }
      // The explorer's controls and key, over the drawing's corners: a
      // plate never lies under them.
      chromeBoxes().forEach(function (b) {
        out.push({ x0: b.x0 - 6, x1: b.x1 + 6, y0: b.y0 - 6, y1: b.y1 + 6, weight: 8 });
      });
      if (!pageMode) {
        out.push({ x0: 0, x1: 30, y0: 0, y1: 30, weight: 4 });
        out.push({ x0: w - 30, x1: w, y0: 0, y1: 30, weight: 4 });
      }
      // Every other mark weighs a little, so between two places the plate
      // takes the one over open ground rather than over a band's results.
      for (var j = 0; j < nodes.length; j++) {
        var m = nodes[j];
        if (!visible(m) || m.kind === 'problem' || m.kind === 'universe' || m.kind === 'integration_surface') continue;
        var mx = m.x * view.k + view.tx, my = m.y * view.k + view.ty, mr = m.r * rs + 1;
        if (mx < -20 || my < -20 || mx > w + 20 || my > h + 20) continue;
        out.push({ x0: mx - mr, x1: mx + mr, y0: my - mr, y1: my + mr, weight: 0.35 });
      }
      return out;
    }

    /* The names of the anchors (the core, the checkers, the problems) at
       rest. A problem's sits toward the centre, where the field is open: the
       papers sit on the orbit either side of the disc and its claims
       outward. Along the orbit, then outward, only when that spot is taken.
       The same places serve the labels and the plates that keep clear of
       them. */
    function anchorText(n, w, isFocus) {
      /* At rest a problem's two papers are named by what they are, "Short
         paper" and "Long paper", the way the card's tabs name them: a
         title cut to fit ("Reciprocal Sums and the Sylv…") said less, and
         the pair either side of each problem now reads as the structure it
         is. Pointed at, a paper names itself in full on its plate. */
      if (n.kind === 'paper' && !isFocus) {
        var run = paperSequence[String(n.id).replace(/^paper:/, '')];
        var side = run && nodes[run[0]] ? nodes[run[0]].side : null;
        if (TAB_NAME[side]) return TAB_NAME[side];
      }
      var text = clip(n.shortLabel, isFocus ? 60 : 42);
      if (n.kind === 'problem' && (w < 600 || view.k < 1.1)) {
        var number = n.id.match(/(?:^|[:_])(\d+)$/);
        if (number) text = '#' + number[1];
      }
      return text;
    }
    // Glyphs a problem's name must not sit on (the claims and papers that
    // crowd round each problem) and the room under the checkers' names,
    // gathered once a frame.
    var frameGlyphBoxes = [], frameCaptionZones = [];
    function gatherLabelObstacles(rs, w, h) {
      frameGlyphBoxes = [];
      frameCaptionZones = [];
      for (var i = 0; i < nodes.length; i++) {
        var n = nodes[i];
        if (!visible(n)) continue;
        if (n.kind === 'public_claim' || n.kind === 'paper') {
          var gx = n.x * view.k + view.tx, gy = n.y * view.k + view.ty, gr = n.r * rs + 3;
          if (gx < -40 || gy < -40 || gx > w + 40 || gy > h + 40) continue;
          frameGlyphBoxes.push({ x0: gx - gr, x1: gx + gr, y0: gy - gr, y1: gy + gr });
        } else if (n.kind === 'integration_surface') {
          // The checking surfaces' names hang under their discs. A problem's
          // name that lands just below them reads as a third line of their
          // caption (#257's did, at the foot of the core), so that room is
          // kept.
          var zx = n.x * view.k + view.tx, zy = n.y * view.k + view.ty, zr = n.r * rs;
          ctx.font = face(600, TYPE.anchor);
          var zw = ctx.measureText(n.shortLabel || '').width;
          if (n.sub) { ctx.font = face(400, TYPE.sub); zw = Math.max(zw, ctx.measureText(n.sub).width); }
          frameCaptionZones.push({ x0: zx - zw / 2 - 12, x1: zx + zw / 2 + 12,
                                   y0: zy - zr - 8, y1: zy + zr + TYPE.below + 4 + (n.sub ? TYPE.subGap : 0) + 12 });
        }
      }
    }
    function glyphHits(box) {
      var count = 0, g, q;
      for (g = 0; g < frameGlyphBoxes.length; g++) {
        q = frameGlyphBoxes[g];
        if (box.x0 < q.x1 && box.x1 > q.x0 && box.y0 < q.y1 && box.y1 > q.y0) count++;
      }
      for (g = 0; g < frameCaptionZones.length; g++) {
        q = frameCaptionZones[g];
        if (box.x0 < q.x1 && box.x1 > q.x0 && box.y0 < q.y1 && box.y1 > q.y0) count += 10;
      }
      return count;
    }
    // Every place a problem's name may take, the best first: the fewest
    // glyphs covered, then the order tried. The label manager falls back
    // along them when the first is taken by a name already placed (on a
    // small field "#68" lost its one place to "#1049" by four pixels).
    function problemLabelSpots(n, px, py, half, rs, w) {
      var distance = Math.sqrt(n.x * n.x + n.y * n.y) || 1;
      var ux = n.x / distance, uy = n.y / distance;
      var dirs = [[-ux, -uy], [-uy, ux], [uy, -ux], [ux, uy]];
      var halfTall = pageMode ? 8 : TYPE.anchor * 0.63, drop = pageMode ? 4 : TYPE.anchor / 3;
      var spots = [];
      for (var d = 0; d < dirs.length; d++) {
        for (var step = 0; step < 2; step++) {
          var dx = dirs[d][0], dy = dirs[d][1];
          var off = n.r * rs + 10 + (half - 6) * Math.abs(dx) + halfTall * Math.abs(dy) + step * 16;
          var cxp = Math.max(half, Math.min(w - half, px + dx * off)), cyp = py + dy * off + drop;
          var textHalf = half - 6;
          var hits = glyphHits({ x0: cxp - textHalf - 3, x1: cxp + textHalf + 3, y0: cyp - TYPE.anchor, y1: cyp + 5 });
          spots.push({ at: [cxp, cyp], hits: hits, order: spots.length });
        }
      }
      spots.sort(function (a, b) { return a.hits - b.hits || a.order - b.order; });
      return spots.map(function (s) { return s.at; });
    }
    function problemLabelSpot(n, px, py, half, rs, w) {
      var distance = Math.sqrt(n.x * n.x + n.y * n.y) || 1;
      var ux = n.x / distance, uy = n.y / distance;
      var dirs = [[-ux, -uy], [-uy, ux], [uy, -ux], [ux, uy]];
      var chosen = null, fewest = Infinity;
      // Half the name's height, and how far its baseline sits below its
      // middle, in the face the anchors are lettered in.
      var halfTall = pageMode ? 8 : TYPE.anchor * 0.63, drop = pageMode ? 4 : TYPE.anchor / 3;
      // Each side at the disc's edge first, then one step out, past the
      // paper that sits on the orbit beside it.
      search: for (var d = 0; d < dirs.length; d++) {
        for (var step = 0; step < 2; step++) {
          var dx = dirs[d][0], dy = dirs[d][1];
          var off = n.r * rs + 10 + (half - 6) * Math.abs(dx) + halfTall * Math.abs(dy) + step * 16;
          var cxp = Math.max(half, Math.min(w - half, px + dx * off)), cyp = py + dy * off + drop;
          var textHalf = half - 6;
          var trial = { x0: cxp - textHalf - 3, x1: cxp + textHalf + 3, y0: cyp - TYPE.anchor, y1: cyp + 5 };
          var hits = glyphHits(trial);
          if (hits < fewest) { fewest = hits; chosen = [cxp, cyp]; }
          if (!hits) break search;
        }
      }
      return chosen;
    }
    function weighted(box, weight) {
      return { x0: box.x0, x1: box.x1, y0: box.y0, y1: box.y1, weight: weight };
    }
    function overlapArea(box, list) {
      var sum = 0;
      for (var j = 0; j < list.length; j++) {
        var q = list[j];
        var dx = Math.min(box.x1, q.x1) - Math.max(box.x0, q.x0), dy = Math.min(box.y1, q.y1) - Math.max(box.y0, q.y0);
        if (!(dx > 0 && dy > 0)) continue;
        // A word a plate so much as grazes steps aside whole, so a graze
        // costs the word's whole room.
        if (q.whole) { if (dx > LABEL_GRACE && dy > LABEL_GRACE) sum += (q.x1 - q.x0) * (q.y1 - q.y0) * (q.weight || 1); }
        else sum += dx * dy * (q.weight || 1);
      }
      return sum;
    }
    // Everything but the core, the checkers and the problems, which carry
    // their names at rest, names itself on a plate when in focus.
    function namesOnPlate(n) {
      return n.kind !== 'problem' && n.kind !== 'universe' && n.kind !== 'integration_surface';
    }
    /* Beside the problems column the card already reads a result whole,
       title and all, so its plate on the drawing gives only the paper's own
       number ("Theorem 14.7"), the tie between the dot and the card, and
       does not say the same words twice in the same moment. A result the
       card is not showing (another one is kept there) is named in full. */
    /* On the map's own page the reading panel owns the title of the result
       it shows, kept or previewed (7 October 2026): the plate gives the
       paper's number, so the drawing and the page never set the same long
       title side by side. A result the panel is not showing is named in
       full. */
    function plateName(i) {
      var n = nodes[i];
      var full = n.kind === 'paper' ? n.label : n.shortLabel;
      if (pageMode) {
        if (n.kind !== 'paper_statement' || !inspector || (i !== selected && !(previewBox && i === previewTarget()))) return full;
        var own = splitLabel(n.label).number;
        return own && own !== n.label ? own : full;
      }
      if (n.kind !== 'paper_statement' || !companionApi || typeof companionApi.reads !== 'function') return full;
      if (selected >= 0 && i !== selected) return full;
      if (!companionApi.reads(n.sector)) return full;
      var number = splitLabel(n.label).number;
      return number && number !== n.label ? number : full;
    }
    function namePlate(i, rs, w, h) {
      var n = nodes[i];
      var habit = i === selected && plateHabit && plateHabit.paper && plateHabit.paper === n.paperId ? plateHabit : null;
      ctx.font = PLATE_FONT;
      // A paper's short name is cut for the ring; on its plate it is whole.
      var full = plateName(i);
      var fullWidth = ctx.measureText(full).width;
      var words = full.split(' ').length;
      var two = words > 1 && fullWidth > TYPE.twoAt ? balancedLines(full, 2) : null;
      var three = words > 2 && fullWidth > TYPE.twoAt ? balancedLines(full, 3) : null;
      var mx = n.x * view.k + view.tx, my = n.y * view.k + view.ty;
      var s = reticleSize(n, rs), gap = s + LEAD_RUN + PLATE_PAD, near = s + LEAD_RISE;
      var out = n.y < 0 ? -1 : 1, pref = n.x >= 0 ? 1 : -1;
      // How close the text may come to the canvas's side: the plate's box
      // then stands PLATE_EDGE inside it.
      var E = PLATE_EDGE + PLATE_PAD;
      // The ways a name can be set in a room: one line when it is short
      // enough, two balanced lines when it is long, three in a narrow room;
      // cut only when even three lines will not hold it.
      function shapes(room) {
        var list = [], oneFits = fullWidth <= Math.min(room, PLATE_ONE_LINE);
        if (oneFits) list.push({ lines: [full], width: fullWidth, cut: 0 });
        // A short name ("Reciprocal Mersenne Subseries") stays on one line
        // unless its room makes it break.
        if (two && two.width <= room && (!oneFits || fullWidth > TYPE.keepOne)) list.push({ lines: two.lines, width: two.width, cut: 0 });
        else if (!list.length && three && three.width <= room) list.push({ lines: three.lines, width: three.width, cut: 0 });
        if (!list.length) {
          var cut = cutLines(full, room);
          var wide = 0;
          cut.lines.forEach(function (line) { wide = Math.max(wide, ctx.measureText(line).width); });
          list.push({ lines: cut.lines, width: wide, cut: Math.max(1, cut.cut) });
        }
        return list;
      }
      // A plate's first baseline is y; each further line drops by the lead.
      function make(shape, cx, y) {
        var width = shape.width, extra = (shape.lines.length - 1) * PLATE_LEAD;
        // The whole plate, padding and edge, stays PLATE_EDGE inside the canvas.
        var x0 = Math.max(E, Math.min(w - width - E, cx - width / 2));
        return { lines: shape.lines, text: shape.lines.join(' '), cut: shape.cut, x: x0 + width / 2, y: y, width: width,
                 box: { x0: x0 - PLATE_PAD, x1: x0 + width + PLATE_PAD, y0: y - PLATE_UP, y1: y + PLATE_DOWN + extra, owner: i } };
      }
      // Beside the mark, a little up or down, its near edge a leader's run
      // from the reticle; or hung under or over the mark.
      function beside(side, v) {
        var room = side > 0 ? w - E - (mx + gap) : mx - gap - E;
        if (room < 80) return [];
        var mid = my + v * near;
        return shapes(room).map(function (shape) {
          var extra = (shape.lines.length - 1) * PLATE_LEAD;
          var half = (PLATE_UP + PLATE_DOWN + extra) / 2;
          if (mid - half < PLATE_EDGE || mid + half > h - PLATE_EDGE) return null;
          // The plate's middle sits level with the leader's run.
          var p = make(shape, mx + side * (gap + shape.width / 2), mid + (PLATE_UP - PLATE_DOWN - extra) / 2);
          var cx = mx + side * s;
          p.leader = [[cx, my + v * (s + LEAD_GAP), cx, mid], [cx, mid, side > 0 ? p.box.x0 : p.box.x1, mid]];
          return p;
        });
      }
      function hung(v) {
        return shapes(w - 2 * E - 6).map(function (shape) {
          var extra = (shape.lines.length - 1) * PLATE_LEAD;
          var y = v > 0 ? my + near + PLATE_UP : my - near - PLATE_DOWN - extra;
          if (y - PLATE_UP < PLATE_EDGE || y + PLATE_DOWN + extra > h - PLATE_EDGE) return null;
          var p = make(shape, mx, y);
          p.leader = [[mx, my + v * (s + LEAD_GAP), mx, v > 0 ? p.box.y0 : p.box.y1]];
          return p;
        });
      }
      var places = [beside(pref, out), beside(pref, -out), beside(-pref, out), beside(-pref, -out), hung(-out), hung(out)];
      var best = null, bestScore = Infinity;
      for (var t = 0; t < places.length; t++) {
        for (var u = 0; u < places[t].length; u++) {
          var p = places[t][u];
          if (!p) continue;
          p.place = t;
          // The least covered first. A cut name loses to any whole one (the
          // reader came for the name), a second line costs a little and a
          // third a good deal, and among equals the earlier, more natural
          // place wins.
          var cost = p.cut ? 3000 + 80 * p.cut : 0;
          var score = overlapArea(p.box, plateKeepOut) + cost + LINE_COST[p.lines.length - 1] + t;
          if (habit && t === habit.t) score -= 200;
          if (score < bestScore) { best = p; bestScore = score; }
        }
      }
      if (!best) {
        var fallback = shapes(w - 2 * E - 6)[0], fallExtra = (fallback.lines.length - 1) * PLATE_LEAD;
        best = make(fallback, mx, Math.max(PLATE_EDGE + PLATE_UP,
          Math.min(h - PLATE_EDGE - PLATE_DOWN - fallExtra, my + near + PLATE_UP)));
      }
      if (!best.leader) best.leader = [];
      if (i === selected) plateHabit = { paper: n.paperId || null, t: best.place };
      return best;
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
    // The explorer knows whether the reader has moved off the fitted view:
    // its key steps aside then, since a closer view brings marks under it.
    var exploredShown = false;
    function draw() {
      if (explorerRoot && exploredShown !== !viewIsFitted) {
        exploredShown = !viewIsFitted;
        explorerRoot.classList.toggle('is-explored', exploredShown);
      }
      // Out of view, or in a hidden tab, a paint waits and is made once the
      // canvas is back.
      if (!onScreen || document.hidden) { paintPending = true; return; }
      paintPending = false;
      if (advancingMotion) { motionNeedsPaint = true; return; }
      paint();
    }
    function paint() {
      // The backing store stops at twice the CSS size, as the plait's does: a
      // three-times screen would paint 2.25 times the pixels on every camera
      // frame for no visible gain. The glow sprites draw in CSS pixels.
      var dpr = Math.min(window.devicePixelRatio || 1, 2);
      var w = canvas.clientWidth, h = canvas.clientHeight;
      var bw = Math.round(w * dpr), bh = Math.round(h * dpr);
      // Where the browser gives the box in device pixels the backing store
      // takes exactly that size, so each pixel drawn is one pixel on the
      // screen and a hairline is never resampled across two.
      if (deviceBox && Math.abs(deviceBox[0] - w * dpr) < 2 && Math.abs(deviceBox[1] - h * dpr) < 2) {
        bw = deviceBox[0];
        bh = deviceBox[1];
      }
      if (canvas.width !== bw || canvas.height !== bh) {
        canvas.width = bw;
        canvas.height = bh;
      }
      var sx = w ? bw / w : dpr, sy = h ? bh / h : dpr;
      ctx.setTransform(sx, 0, 0, sy, 0, 0);
      hairX = 1 / sx;
      hairY = 1 / sy;
      hairPx = 2 / (sx + sy);
      ctx.clearRect(0, 0, w, h);
      // Kerning is asked for by name; left to the browser it can drop out at
      // the small sizes the labels use.
      if ('fontKerning' in ctx) ctx.fontKerning = 'normal';

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
      scaleR = scaleRadius(w);
      fitInteriorType();
      aimCursor(false);
      labelBoxes = [];
      // The hovered and the selected object name themselves on plates. The
      // plates and their leaders are placed first, so the band titles and
      // the shared callout, lettered before the labels, can step aside from
      // under them.
      plateBoxes = [];
      platePlaced = {};
      gatherLabelObstacles(rs, w, h);
      // No label is set under the explorer's controls or its key; the key
      // steps aside in a closer view, and gives its corner back then.
      chromeBoxes().forEach(function (b) {
        if (b.legend && exploredShown) return;
        labelBoxes.push({ x0: b.x0 - 4, x1: b.x1 + 4, y0: b.y0 - 4, y1: b.y1 + 4 });
      });
      var titleLayout = bandLabelLayout(focus, w, h);
      var reticles = reticleTargets(rs, w, h);
      plateKeepOut = [];
      if (hover >= 0 || selected >= 0) {
        plateKeepOut = keepOutBoxes(rs, w, h);
        // The band titles, the cursor and every reticle hold their room too.
        // A title in focus names where the reader is: a plate that grazed it
        // would hide it whole, so a graze costs it whole, more than laying
        // the plate over a band's results and less than covering a disc.
        titleLayout.forEach(function (item) {
          item.rows.forEach(function (r) {
            var t = weighted(r.box, 1);
            t.whole = true;
            plateKeepOut.push(t);
          });
        });
        var cursorAt = cursorTarget();
        if (cursorAt !== null) {
          var cc = Math.cos(cursorAt), cs = Math.sin(cursorAt), cR = seatedScaleR();
          var cx0 = view.tx + cc * (cR - 4), cy0 = view.ty + cs * (cR - 4);
          var cx1 = view.tx + cc * (cR + SCALE_MARK), cy1 = view.ty + cs * (cR + SCALE_MARK);
          plateKeepOut.push({ x0: Math.min(cx0, cx1) - 3, x1: Math.max(cx0, cx1) + 3,
                              y0: Math.min(cy0, cy1) - 3, y1: Math.max(cy0, cy1) + 3, weight: 4 });
        }
        reticles.forEach(function (t) { plateKeepOut.push(weighted(t.box, 4)); });
      }
      // The pinned plate is placed first and holds still; a hovered one keeps
      // clear of it. While the camera moves the plates wait.
      var moving = !!cameraFrame;
      [selected, hover].forEach(function (at, k) {
        if (moving || at < 0 || (k === 1 && at === selected)) return;
        var pn = nodes[at];
        if (!pn || !visible(pn) || !namesOnPlate(pn)) return;
        var px = pn.x * view.k + view.tx, py = pn.y * view.k + view.ty;
        if (px < -60 || py < -60 || px > w + 60 || py > h + 60) return;
        // The pinned plate keeps the place it was given until the pin, its
        // name or the view changes: a hover elsewhere never moves it.
        var placed, key = k === 0 ? [at, view.k, view.tx, view.ty, w, h, rs, plateName(at)].join('|') : null;
        if (key && pinnedPlate && pinnedPlate.key === key) placed = pinnedPlate.placed;
        else placed = namePlate(at, rs, w, h);
        if (key) pinnedPlate = { key: key, placed: placed };
        var lead = leaderBoxes(placed.leader, at);
        platePlaced[at] = placed;
        plateBoxes.push(placed.box);
        Array.prototype.push.apply(plateBoxes, lead);
        // Two plates, or a plate and the other's leader, never cross.
        plateKeepOut.push(weighted(placed.box, 12));
        lead.forEach(function (b) { plateKeepOut.push(weighted(b, 12)); });
      });

      /* Placing. Every word's room is taken before anything is drawn, in
         the order the words were always lettered: the cursor, the band
         titles outside the rings, the shared callout, the anchors' discs,
         then the names by priority. Nothing placed depends on a pixel
         drawn, so the drawing below can route the lit threads, and the lit
         sector's index, round the words they would otherwise run through. */
      var cursorBox = cursorRoom();
      if (cursorBox) labelBoxes.push(cursorBox);
      placeBandLabels(titleLayout);
      var calloutPlan = placeCaptions(focus, w, h);
      for (i = 0; i < nodes.length; i++) {
        n = nodes[i];
        if (!visible(n)) continue;
        if (n.kind !== 'problem' && n.kind !== 'universe' && n.kind !== 'integration_surface') continue;
        var ax = n.x * view.k + view.tx, ay = n.y * view.k + view.ty, ar = n.r * rs + 4;
        labelBoxes.push({ x0: ax - ar, x1: ax + ar, y0: ay - ar, y1: ay + ar, owner: i, disc: true });
      }
      var labelPlan = placeLabels(focus, near, searching, rs, w, h, moving);

      drawGround(w, h);
      if (pageMode) drawSectorSlice(focus);
      drawClaimPlates(focus);
      drawBandPlates(focus);
      if (!pageMode) drawSectorIndex(focus);
      scaleYield = plateBoxes.concat(reticles.map(function (t) { return t.box; }));
      drawScale(focus, w, h);
      drawCursor(rs);

      var hot = graph.hot, quiet = graph.quiet;
      drawEdgeSet(quiet, (focus >= 0 ? 0.65 - 0.35 * focusMix : 0.65) * revealAlpha(1), 0.65, palette.edge);
      // On the landing each lit thread is routed round the words it would
      // cross; the map's page draws them straight.
      var routes = !pageMode && focus >= 0 && hot.length ? threadRoutes(focus, hot, rs) : null;
      var grown = threadGrowth(focus);
      if (routes) drawThreads(routes, grown);
      else drawHotEdges(focus, hot, grown);
      drawConstellation(focus);
      var threads = graph.threads;
      drawLight(focus, near, searching, threads, rs, w, h);
      // The band titles go down first, outside the rings.
      drawBandLabels(titleLayout);

      var shown = 0, seating = reveal < 1;
      for (i = 0; i < nodes.length; i++) {
        n = nodes[i];
        if (!visible(n)) continue;
        shown++;
        var nk = seating ? layerK(revealLayer(n.kind)) : view.k;
        x = n.x * nk + view.tx;
        y = n.y * nk + view.ty;
        if (x < -24 || y < -24 || x > w + 24 || y > h + 24) continue;
        var r = n.r * rs;
        if (n.kind === 'lean_module' && i !== focus) {
          r = Math.min(r, Math.max(0.45, view.k * 1.5));
        }
        var alpha = 1;
        if ((n.tier === 'open' || n.tier === 'none') && !n.proof_status) alpha = 0.7;
        if (n.kind === 'lean_module' && i !== focus) alpha = 0.45;
        var anchor = n.kind === 'problem' || n.kind === 'universe' || n.kind === 'integration_surface';
        if (searching && !matches(n) && !anchor) alpha = 0.12;
        // A result sets into its plate as the opening's pen passes it: it
        // comes in a little large and settles to its size.
        var settle = 1;
        if (seating && n.kind === 'paper_statement') {
          settle = setAt(Math.atan2(n.y, n.x));
          alpha *= settle;
        } else {
          alpha *= revealAlpha(revealLayer(n.kind));
        }
        if (alpha <= 0.004) continue;
        var undimmed = alpha;
        var ghost = focus >= 0 && i !== focus && !near[i];
        // On the landing what drops back keeps its hue: its own ink mixed
        // toward the ground's line tone (faded ink, never a pastel or a
        // grey), as the system map beside it dims; the orange ring stays
        // orange and the lit sector rises out of it. The map's page keeps
        // its quiet grey.
        var faded = ghost && !pageMode && !!palette.tone;
        if (ghost && !faded) alpha = Math.min(alpha, dimmed(0.25));
        shadeBy = faded ? focusMix : 0;
        ctx.globalAlpha = alpha;
        if (i === hover || i === selected) r = n.r * rs + 1.5;
        if (settle < 1) r *= 1 + 0.45 * (1 - settle);
        if (n.kind === 'universe') {
          // The core is a ring round a point: the Lean source everything
          // here is checked against, drawn as a mark, not a mass.
          ctx.beginPath();
          ctx.arc(x, y, r, 0, Math.PI * 2);
          ctx.fillStyle = palette.ground;
          ctx.fill();
          ctx.lineWidth = 1.8;
          ctx.strokeStyle = shade(palette.universe);
          ctx.stroke();
          ctx.beginPath();
          ctx.arc(x, y, Math.max(1.6, r * 0.32), 0, Math.PI * 2);
          ctx.fillStyle = shade(palette.universe);
          ctx.fill();
          // Two faint rings round it, the way a chart marks its pole.
          ctx.lineWidth = 1;
          ctx.strokeStyle = palette.edge;
          ctx.globalAlpha = alpha * 0.7 * (1 - 0.5 * shadeBy);
          ctx.beginPath();
          ctx.arc(x, y, r + 8 * rs, 0, Math.PI * 2);
          ctx.stroke();
          ctx.globalAlpha = alpha * 0.35 * (1 - 0.5 * shadeBy);
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
          ctx.strokeStyle = shade(palette.integration_surface);
          ctx.stroke();
        } else if (n.kind === 'problem') {
          if (ghost && !faded && focusMix < 1) {
            ctx.globalAlpha = undimmed * (1 - focusMix);
            drawProblemMark(n, x, y, r, palette.problem, true);
          }
          if (ghost && !faded) {
            ctx.globalAlpha = undimmed * focusMix * 0.5;
            drawProblemMark(n, x, y, r, palette.faint, false);
          } else {
            drawProblemMark(n, x, y, r, palette.problem, true);
          }
        } else if (ghost && !faded) {
          // On the map's page, context recedes to a quiet grey, so the
          // focus holds the only colour on the field. While the focus fades
          // in, the colour crossfades into the grey.
          if (focusMix < 1) {
            ctx.globalAlpha = undimmed * (1 - focusMix);
            drawGlyph(x, y, r, glyphColor(n), n.proof_status || n.tier);
            if (n.kind === 'problem') drawProblemRing(n, x, y, r);
          }
          ctx.globalAlpha = undimmed * focusMix * 0.5;
          drawGlyph(x, y, r, palette.faint, n.proof_status || n.tier);
        } else {
          drawGlyph(x, y, r, glyphColor(n), n.proof_status || n.tier);
          if (n.kind === 'problem') drawProblemRing(n, x, y, r);
        }
        shadeBy = 0;
        if (i === selected) {
          // The selected object keeps a crisp ring, so it stays findable
          // when the camera moves or the field is busy. On the landing a
          // kept result's ring, like its reticle and its plate's edge, is
          // the ember the column's card turns when it holds a result, so a
          // kept result never reads as one merely pointed at.
          ctx.globalAlpha = pageMode ? 1 : 0.9;
          ctx.lineWidth = pageMode ? 1.5 : 1.25;
          ctx.strokeStyle = pageMode ? palette.ink : palette.ember;
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
      drawPulse(focus, threads, rs, routes);
      drawReferMark(focus, rs, w, h);

      // The shared callout goes over the dots, so a band never covers it.
      drawCaptions(calloutPlan, focus);
      drawLabels(labelPlan);
      if (pageMode && focus >= 0 && grown >= 1) drawExitNames(focus, hot, w, h);
      // The reticles go down once every name has its place.
      drawReticles(rs, w, h);
      drawStatementNumbers(focus, near, searching, w, h);
      if (countOut) {
        // Plain feedback for the legend and the search: how many of the
        // loaded objects are shown, and how many the search found. (The
        // count of connections drawn was the renderer's bookkeeping, not
        // something a reader asks.)
        var line = fmtCount(shown) + (shown === nodes.length ? ' shown' : ' of ' + fmtCount(nodes.length) + ' shown');
        if (searching) line += ', ' + (matchList.length ? fmtCount(matchList.length) + ' found' : 'none found');
        if (line !== countText) {
          countText = line;
          countOut.textContent = line;
        }
      }
    }

    /* Labels are placed, not just drawn. Each is a box on the field, taken
       in priority order: the selected or hovered object, then the problems,
       the hubs and the core, their second lines, then the rest. A label
       that would land on a placed label or on an anchor's disc is left out;
       its object still names itself on hover and in the rail. Placing takes
       each label's room (and a plate's leader's); drawing comes later. */
    function placeLabels(focus, near, searching, rs, w, h, moving) {
      var i, n, candidates = [];
      for (i = 0; i < nodes.length; i++) {
        n = nodes[i];
        if (!visible(n)) continue;
        var isFocus = i === hover || i === selected;
        var wantLabel = isFocus || n.kind === 'problem' || n.kind === 'universe' ||
          n.kind === 'integration_surface' ||
          (view.k > 1.7 && (n.kind === 'paper' || n.kind === 'human_document')) ||
          (view.k > 3.4 && n.kind === 'public_claim');
        // A paper's or a claim's name fades up as the view closes in.
        var lod = isFocus ? 1 : n.kind === 'paper' || n.kind === 'human_document' ? zoomIn(1.7, 2) :
          n.kind === 'public_claim' ? zoomIn(3.4, 3.8) : 1;
        if (!wantLabel) continue;
        var isAnchor = n.kind === 'problem' || n.kind === 'universe' || n.kind === 'integration_surface';
        if (searching && !matches(n) && !isFocus && !isAnchor) continue;
        if (focus >= 0 && i !== focus && !near[i] && !isFocus && !isAnchor) continue;
        var lx = n.x * view.k + view.tx, ly = n.y * view.k + view.ty;
        if (lx < -60 || ly < -60 || lx > w + 60 || ly > h + 60) continue;
        var size = isAnchor ? TYPE.anchor : TYPE.small;
        var font = face(isAnchor ? 600 : 500, size);
        ctx.font = font;
        var text = anchorText(n, w, isFocus);
        var half = ctx.measureText(text).width / 2 + 6;
        var labelY = ly + n.r * rs + TYPE.below, spots = null;
        if (n.kind === 'problem') {
          var chosen = problemLabelSpot(n, lx, ly, half, rs, w);
          // On the landing a problem's name keeps its other places in
          // reserve, worked out only if its first is taken.
          if (!pageMode) spots = { n: n, px: lx, py: ly, half: half };
          lx = chosen[0];
          labelY = chosen[1];
        }
        // A hovered or selected result or claim names itself on a plate,
        // where the frame's first step already placed it.
        var plate = null, leader = null;
        if (isFocus && namesOnPlate(n)) {
          if (moving) continue;
          plate = platePlaced[i] || namePlate(i, rs, w, h);
          text = plate.text;
          lx = plate.x;
          labelY = plate.y;
          leader = plate.leader;
          half = plate.width / 2 + 6;
          // A plate is lettered in the face it was measured in.
          font = PLATE_FONT;
          size = TYPE.plate;
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
          n.kind === 'integration_surface' ? { x: n.x * view.k + view.tx, y: ly + (pageMode ? 4 : 5),
            side: n.x < 0 ? -1 : 1, r: n.r * rs } : null;
        // On the landing an anchor whose sector has dropped back names
        // itself in the muted ink, as the system map's dimmed names do, so
        // the lit sector's own number rises with its marks.
        var dropped = !pageMode && !isFocus && focus >= 0 && i !== focus && !near[i];
        candidates.push({ text: text, x: lx, y: labelY, font: font, size: size, plate: plate, alt: alt, lod: lod,
                          spots: spots && !plate ? spots : null,
                          leader: leader, color: dropped ? fadeText(palette.ink, focusMix) : palette.ink,
                          priority: priority, owner: i, order: candidates.length });
        // A quieter second line: a hub's reach. It waits for room.
        if (n.sub && !isFocus && w >= 420 && n.kind !== 'problem') {
          candidates.push({ text: clip(n.sub, 36), x: lx, y: labelY + TYPE.subGap, font: face(400, TYPE.sub), size: TYPE.sub,
                            color: palette.faint, priority: 5, owner: i, order: candidates.length,
                            checker: n.kind === 'integration_surface' });
        }
      }
      /* The checkers' second lines ("616 of 689 replayed", "616 prepared")
         stand side by side under their names. On a small field they met,
         and read as one phrase; they spread apart, each outward by the same
         few pixels, to keep a clear gap. */
      var checkerSubs = candidates.filter(function (c) { return c.checker; });
      if (checkerSubs.length === 2) {
        var left = checkerSubs[0].x <= checkerSubs[1].x ? checkerSubs[0] : checkerSubs[1];
        var right = left === checkerSubs[0] ? checkerSubs[1] : checkerSubs[0];
        ctx.font = left.font;
        var clear = (right.x - ctx.measureText(right.text).width / 2) - (left.x + ctx.measureText(left.text).width / 2);
        if (clear < 14) {
          var spread = Math.min(pageMode ? 12 : 30, (14 - clear) / 2);
          left.x -= spread;
          right.x += spread;
        }
      }
      candidates.sort(function (a, b) { return b.priority - a.priority || a.order - b.order; });
      var plan = [];
      for (var ci = 0; ci < candidates.length; ci++) {
        var cand = candidates[ci];
        ctx.font = cand.font;
        var width = cand.plate ? cand.plate.width : ctx.measureText(cand.text).width;
        var cx0 = Math.max(2, Math.min(w - width - 2, cand.x - width / 2));
        var box = { x0: cx0 - 2, x1: cx0 + width + 2, y0: cand.y - cand.size + 1, y1: cand.y + 4, owner: cand.owner };
        if (cand.priority < 10 && cand.alt && labelCollides(box)) {
          cand.x = cand.alt.side ? cand.alt.x + cand.alt.side * (cand.alt.r + 6 + width / 2) : cand.alt.x;
          cand.y = cand.alt.y;
          cx0 = Math.max(2, Math.min(w - width - 2, cand.x - width / 2));
          box = { x0: cx0 - 2, x1: cx0 + width + 2, y0: cand.y - cand.size + 1, y1: cand.y + 4, owner: cand.owner };
        }
        // A problem's name taken from its first place tries its others.
        if (cand.priority < 10 && cand.spots && labelCollides(box)) {
          var others = problemLabelSpots(cand.spots.n, cand.spots.px, cand.spots.py, cand.spots.half, rs, w).slice(1);
          for (var si = 0; si < others.length && labelCollides(box); si++) {
            var sx = Math.max(2, Math.min(w - width - 2, others[si][0] - width / 2));
            var trial = { x0: sx - 2, x1: sx + width + 2, y0: others[si][1] - cand.size + 1, y1: others[si][1] + 4, owner: cand.owner };
            if (labelCollides(trial)) continue;
            cand.x = others[si][0];
            cand.y = others[si][1];
            cx0 = sx;
            box = trial;
          }
        }
        if (cand.priority < 10 && labelCollides(box)) continue;
        if (cand.plate && cand.leader) Array.prototype.push.apply(labelBoxes, leaderBoxes(cand.leader, cand.owner));
        if (cand.plate) {
          box = { x0: cand.plate.box.x0, x1: cand.plate.box.x1, y0: cand.plate.box.y0, y1: cand.plate.box.y1, owner: cand.owner };
        }
        labelBoxes.push(box);
        plan.push({ cand: cand, box: box, cx0: cx0, width: width });
      }
      return plan;
    }
    /* A lit thread whose far end is out of the view says where it goes,
       where it leaves (6 October 2026): close in on a result, its threads
       to Comparator, Palomar or the core run off the edge of the window,
       and a line that leads nowhere visible reads as arbitrary. Its far
       end's name stands just inside the edge on the thread, in the quiet
       italic of the map's second lines, and only where it takes no room
       another word holds. */
    function drawExitNames(focus, hot, w, h) {
      var f = nodes[focus];
      var fx = f.x * view.k + view.tx, fy = f.y * view.k + view.ty;
      if (fx < 0 || fy < 0 || fx > w || fy > h) return;
      var size = TYPE.sub, font = face(400, size, true), inset = 10;
      ctx.font = font;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      ctx.lineJoin = 'round';
      var said = {};
      hot.forEach(function (at) {
        var other = edges[at][0] === focus ? edges[at][1] : edges[at][0], o = nodes[other];
        if (!o || said[other]) return;
        if (o.kind !== 'universe' && o.kind !== 'integration_surface' && o.kind !== 'problem' && o.kind !== 'paper') return;
        var ox = o.x * view.k + view.tx, oy = o.y * view.k + view.ty;
        if (ox >= 0 && oy >= 0 && ox <= w && oy <= h) return;
        var span = clipSegment([fx, fy], [ox, oy], { x0: inset, x1: w - inset, y0: inset, y1: h - inset });
        if (!span) return;
        var len = Math.sqrt((ox - fx) * (ox - fx) + (oy - fy) * (oy - fy)) || 1;
        var ux = (ox - fx) / len, uy = (oy - fy) / len;
        var ex = fx + (ox - fx) * span[1], ey = fy + (oy - fy) * span[1];
        var text = o.kind === 'paper' ? anchorText(o, w, false) : clip(o.shortLabel, 28);
        var width = ctx.measureText(text).width;
        // Step back along the thread until the name stands clear.
        for (var back = 16; back <= 64; back += 12) {
          var cx = ex - ux * back, cy = ey - uy * back + size * 0.35;
          var box = { x0: cx - width / 2 - 3, x1: cx + width / 2 + 3, y0: cy - size, y1: cy + 4 };
          if (box.x0 < 2 || box.x1 > w - 2 || box.y0 < 2 || box.y1 > h - 2) continue;
          if (labelCollides(box) || underPlate(box)) continue;
          labelBoxes.push(box);
          said[other] = true;
          var lit = other === referring(focus);
          ctx.globalAlpha = lit ? 0.9 + 0.1 * referMix : 0.9;
          ctx.lineWidth = 4;
          ctx.strokeStyle = palette.ground;
          ctx.strokeText(text, cx, cy);
          ctx.fillStyle = lit && referMix > 0.5 ? referInk(other) : palette.muted;
          ctx.fillText(text, cx, cy);
          ctx.globalAlpha = 1;
          return;
        }
      });
    }
    function drawLabels(plan) {
      ctx.textAlign = 'center';
      ctx.textBaseline = 'alphabetic';
      ctx.lineJoin = 'round';
      plan.forEach(function (p) {
        var cand = p.cand, box = p.box;
        ctx.font = cand.font;
        // A kept result's plate takes the ember edge its ring and reticle
        // wear; one under the pointer keeps the ink hairline.
        var kept = !pageMode && !!cand.plate && cand.owner === selected;
        // A new plate eases out of its mark over a sixth of a second; its
        // room was taken at once, so nothing else moves while it arrives.
        var enter = !cand.plate ? 1 : Math.min(cand.owner === pulse.at ? plateEase(pulse.ms) : 1, plateEase(arrival.ms));
        if (cand.plate && cand.leader) {
          // The leader stands where it ends; the plate eases along it, over
          // its end, so the two never part.
          drawLeader(cand.leader, (kept ? 0.8 : 0.66) * enter, kept ? palette.ember : null);
        }
        if (enter < 1) {
          var ownerX = nodes[cand.owner].x * view.k + view.tx;
          ctx.save();
          ctx.translate((1 - enter) * 6 * (cand.x >= ownerX ? -1 : 1), 0);
        }
        var lines = [cand.text];
        if (cand.plate) {
          lines = cand.plate.lines;
          // The plate's edge is one device pixel, laid on the grid.
          var bx0 = snapX(box.x0) + hairX / 2, by0 = snapY(box.y0) + hairY / 2;
          var bw0 = snapX(box.x1) - snapX(box.x0) - hairX, bh0 = snapY(box.y1) - snapY(box.y0) - hairY;
          ctx.beginPath();
          if (typeof ctx.roundRect === 'function') ctx.roundRect(bx0, by0, bw0, bh0, 3);
          else ctx.rect(bx0, by0, bw0, bh0);
          // Opaque: nothing under a plate shows through it.
          ctx.globalAlpha = enter;
          ctx.fillStyle = palette.ground;
          ctx.fill();
          ctx.globalAlpha = (kept ? 0.9 : 0.5) * enter;
          ctx.lineWidth = hairPx;
          ctx.strokeStyle = kept ? palette.ember : palette.ink;
          ctx.stroke();
        }
        ctx.globalAlpha = revealAlpha(4) * enter * (cand.lod == null ? 1 : cand.lod);
        ctx.lineWidth = 4;
        ctx.strokeStyle = palette.ground;
        ctx.fillStyle = cand.color;
        var tx = cand.plate ? (box.x0 + box.x1) / 2 : p.cx0 + p.width / 2;
        // Every halo before any letter, so a second line's halo never
        // clips the first line's descenders.
        for (var li = 0; li < lines.length; li++) ctx.strokeText(lines[li], tx, cand.y + li * PLATE_LEAD);
        for (li = 0; li < lines.length; li++) ctx.fillText(lines[li], tx, cand.y + li * PLATE_LEAD);
        ctx.globalAlpha = 1;
        if (enter < 1) ctx.restore();
      });
    }
    // A name's ink moved toward the muted ink, by the focus's fade.
    function fadeText(color, amount) {
      if (!color || amount <= 0) return color;
      var t = Math.round(Math.min(1, amount) * 20) / 20;
      var key = 'text|' + color + '|' + t;
      var hit = mixCache[key];
      if (hit === undefined) {
        hit = mixOklab(color, palette.muted, t, palette.under) || color;
        mixCache[key] = hit;
      }
      return hit;
    }

    /* The lit sector, indexed rather than boxed. A filled slice ran its
       straight edges into the checkers' counts and the problems' names; the
       index is a hairline down each edge of the sector, in the gaps either
       side of its band, and one arc across it just outside the scale, the
       bracket a printed chart sets round a region. Each stops INDEX_CLEAR
       short of any word, so the arc parts round the sector's own title. */
    var INDEX_CLEAR = 6;
    function nearWord(x, y) {
      for (var b = 0; b < labelBoxes.length; b++) {
        var q = labelBoxes[b];
        if (q.disc) continue;
        if (x > q.x0 - INDEX_CLEAR && x < q.x1 + INDEX_CLEAR && y > q.y0 - INDEX_CLEAR && y < q.y1 + INDEX_CLEAR) return true;
      }
      return false;
    }
    function midAngle(a, b) { return a + shortArc(a, b) / 2; }
    function drawSectorIndex(focus) {
      if (focus < 0 || !bands.length || lensOff.paper_statement || focusMix <= 0.01) return;
      var f = nodes[focus];
      if (!f || f.kind === 'universe' || f.kind === 'integration_surface') return;
      var pids = sectorProblems(f);
      if (!pids.length) return;
      var orbit = 0, count = 0;
      for (var pid in problemIndex) {
        var p = nodes[problemIndex[pid]];
        if (p) { orbit += Math.sqrt(p.x * p.x + p.y * p.y); count++; }
      }
      if (!count) return;
      var sorted = bands.slice().sort(function (a, c) { return a.lo - c.lo; });
      var inner = Math.max(0, (orbit / count - 34) * view.k);
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = hairPx;
      ctx.lineCap = 'butt';
      ctx.globalAlpha = 0.55 * focusMix * revealAlpha(3);
      for (var s = 0; s < sorted.length; s++) {
        var b = sorted[s];
        if (pids.indexOf(b.sector) === -1) continue;
        var prev = sorted[(s - 1 + sorted.length) % sorted.length], next = sorted[(s + 1) % sorted.length];
        var from = sorted.length > 1 ? midAngle(prev.hi, b.lo) : b.lo - 0.03;
        var to = sorted.length > 1 ? midAngle(b.hi, next.lo) : b.hi + 0.03;
        var span = ((to - from) % TURN + TURN) % TURN;
        var outerR = scaleR ? seatedScaleR() + SCALE_MARK + 3 : (bandRadii(b)[1] + 12) * view.k;
        if (!(outerR > inner) || !span) continue;
        ctx.beginPath();
        // The two edges, each from the arc inward until a word is near.
        [from, from + span].forEach(function (a) {
          var c = Math.cos(a), sn = Math.sin(a), last = null;
          for (var r = outerR; r >= inner; r -= 1.5) {
            var x = view.tx + c * r, y = view.ty + sn * r;
            if (nearWord(x, y)) break;
            if (!last) ctx.moveTo(x, y);
            last = [x, y];
          }
          if (last) ctx.lineTo(last[0], last[1]);
        });
        // The arc across, in runs between the words it meets.
        var steps = Math.max(8, Math.ceil(span * outerR / 1.5)), run = false;
        for (var k = 0; k <= steps; k++) {
          var a = from + span * k / steps;
          var ax = view.tx + Math.cos(a) * outerR, ay = view.ty + Math.sin(a) * outerR;
          if (nearWord(ax, ay)) { run = false; continue; }
          if (!run) { ctx.moveTo(ax, ay); run = true; } else ctx.lineTo(ax, ay);
        }
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
    }

    /* Threads find their way round words. A lit thread from a result to
       Comparator, Palomar, its paper or a claim ran straight through any
       name between them, and a line through "#68" reads as a relation to
       #68 that the data does not hold. On the landing each thread now keeps
       THREAD_CLEAR from every word and anchor it does not end at: straight
       when it can; otherwise first inward (or last outward) along its outer
       end's own radius, so it leaves through its own sector, and then
       across; otherwise round the corners of what it would still cross. It
       ends at its far object's edge, and that object's own name is part of
       its edge: a thread arriving from below Comparator stops at "616 of
       689 replayed" rather than running up through it. */
    var THREAD_CLEAR = 4, routeCache = null;
    function screenOf(i) { return [nodes[i].x * view.k + view.tx, nodes[i].y * view.k + view.ty]; }
    function segLength(a, b) { return Math.sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1])); }
    // Where a segment enters a box, as a share of its length (Liang-Barsky):
    // [t0, t1], or null when it misses.
    function clipSegment(p, q, b) {
      var dx = q[0] - p[0], dy = q[1] - p[1], t0 = 0, t1 = 1;
      var checks = [[-dx, p[0] - b.x0], [dx, b.x1 - p[0]], [-dy, p[1] - b.y0], [dy, b.y1 - p[1]]];
      for (var c = 0; c < 4; c++) {
        var pp = checks[c][0], qq = checks[c][1];
        if (pp === 0) { if (qq < 0) return null; continue; }
        var t = qq / pp;
        if (pp < 0) { if (t > t0) t0 = t; } else if (t < t1) t1 = t;
        if (t1 < t0) return null;
      }
      return t1 > t0 ? [t0, t1] : null;
    }
    // How far a route runs within the clearance of the words it must keep
    // off.
    function routeIntrusion(points, obstacles) {
      var inside = 0;
      for (var j = 1; j < points.length; j++) {
        var p = points[j - 1], q = points[j], len = segLength(p, q);
        for (var o = 0; o < obstacles.length; o++) {
          var hit = clipSegment(p, q, obstacles[o]);
          if (hit) inside += (hit[1] - hit[0]) * len;
        }
      }
      return inside;
    }
    function insideBox(pt, b) { return pt[0] > b.x0 && pt[0] < b.x1 && pt[1] > b.y0 && pt[1] < b.y1; }
    // A route's bends rounded: each corner becomes a short curve that
    // leaves the straight run ROUTE_ROUND before the corner and joins the
    // next as far after it, the corner its control point.
    var ROUTE_ROUND = 12, ROUTE_GAP = 8;
    function roundRoute(pts) {
      if (pts.length < 3) return pts;
      var out = [pts[0]];
      for (var j = 1; j < pts.length - 1; j++) {
        var p = pts[j - 1], c = pts[j], q = pts[j + 1];
        var r = Math.min(ROUTE_ROUND, segLength(p, c) / 2, segLength(c, q) / 2);
        var lin = segLength(p, c) || 1, lout = segLength(c, q) || 1;
        var s0 = [c[0] + (p[0] - c[0]) * r / lin, c[1] + (p[1] - c[1]) * r / lin];
        var s1 = [c[0] + (q[0] - c[0]) * r / lout, c[1] + (q[1] - c[1]) * r / lout];
        out.push(s0);
        for (var k = 1; k < 6; k++) {
          var t = k / 6, u = 1 - t;
          out.push([u * u * s0[0] + 2 * u * t * c[0] + t * t * s1[0], u * u * s0[1] + 2 * u * t * c[1] + t * t * s1[1]]);
        }
        out.push(s1);
      }
      out.push(pts[pts.length - 1]);
      return out;
    }
    /* A thread ends at its far object's mark, a hair (2px) short of its
       edge, as every line on the map ends, going round that object's own
       name like any other word. Where going round would cost more than a
       tenth (a result under Comparator swung right round its caption to
       reach its disc), the thread runs straight on and stops at the name
       instead: the name is part of what it points at, never an unrelated
       word in its way. */
    function cutRoute(route, ends, B, rb) {
      var points = [route[0]];
      for (var j = 1; j < route.length; j++) {
        var p0 = route[j - 1], p1 = route[j], enter = 1;
        for (var e = 0; e < ends.length; e++) {
          var cut = clipSegment(p0, p1, ends[e]);
          if (cut && cut[0] < enter) enter = cut[0];
        }
        var dx = p1[0] - p0[0], dy = p1[1] - p0[1], fx = p0[0] - B[0], fy = p0[1] - B[1];
        var qa = dx * dx + dy * dy, qb = 2 * (fx * dx + fy * dy), qc = fx * fx + fy * fy - rb * rb;
        var root = qb * qb - 4 * qa * qc;
        if (qa > 0 && root >= 0) {
          var t = (-qb - Math.sqrt(root)) / (2 * qa);
          if (t >= 0 && t < enter) enter = t;
        }
        if (enter < 1) {
          points.push([p0[0] + dx * enter, p0[1] + dy * enter]);
          break;
        }
        points.push(p1);
      }
      return points;
    }
    function wayLength(points) {
      var total = 0;
      for (var j = 1; j < points.length; j++) total += segLength(points[j - 1], points[j]);
      return total;
    }
    function routeThread(a, b, rs) {
      var A = screenOf(a), B = screenOf(b);
      var obstacles = [], names = [];
      var rb = nodes[b].r * rs + 2;
      var pad = 150, lo = [Math.min(A[0], B[0]) - pad, Math.min(A[1], B[1]) - pad],
          hi = [Math.max(A[0], B[0]) + pad, Math.max(A[1], B[1]) + pad];
      var rooms = labelBoxes.filter(function (box) { return !box.seg; }).concat(titleRooms);
      for (var q = 0; q < rooms.length; q++) {
        var box = rooms[q];
        if (box.owner === -2) continue;
        if (box.disc && (box.owner === a || box.owner === b)) continue;
        var grown = { x0: box.x0 - THREAD_CLEAR, x1: box.x1 + THREAD_CLEAR, y0: box.y0 - THREAD_CLEAR, y1: box.y1 + THREAD_CLEAR };
        // A word either end stands inside cannot be kept off; it is not
        // counted.
        if (insideBox(A, grown) || insideBox(B, grown)) continue;
        if (grown.x1 < lo[0] || grown.x0 > hi[0] || grown.y1 < lo[1] || grown.y0 > hi[1]) continue;
        obstacles.push(grown);
        if (box.owner === b) names.push(grown);
      }
      // The way to the mark itself, round its name; and the way to its
      // name, where the thread may stop.
      var toMark = shortestWay(A, B, obstacles), markPoints = toMark ? cutRoute(toMark, [], B, rb) : null;
      if (names.length) {
        var toName = shortestWay(A, B, obstacles.filter(function (o) { return names.indexOf(o) === -1; }));
        var namePoints = toName ? cutRoute(toName, names, B, rb) : null;
        if (namePoints && (!markPoints || wayLength(markPoints) > 1.1 * wayLength(namePoints) + 8)) {
          return { points: namePoints };
        }
      }
      return { points: markPoints || cutRoute([A, B], [], B, rb) };
    }
    /* The way round: the shortest path from one end to the other that
       crosses no word, over the corners of the words near the straight
       line (each ROUTE_GAP outside its clearance), so it goes round a name
       on whichever side is shorter and never hugs it; null when there is
       none. */
    function shortestWay(A, B, obstacles) {
      var route = [A, B];
      if (routeIntrusion(route, obstacles) > 0) {
        route = null;
        var pts = [A, B];
        obstacles.forEach(function (o) {
          [[o.x0 - ROUTE_GAP, o.y0 - ROUTE_GAP], [o.x1 + ROUTE_GAP, o.y0 - ROUTE_GAP],
           [o.x1 + ROUTE_GAP, o.y1 + ROUTE_GAP], [o.x0 - ROUTE_GAP, o.y1 + ROUTE_GAP]].forEach(function (c) {
            if (!obstacles.some(function (other) { return insideBox(c, other); })) pts.push(c);
          });
        });
        var count = pts.length, dist = [], prev = [], done = [];
        for (var n0 = 0; n0 < count; n0++) { dist.push(Infinity); prev.push(-1); done.push(false); }
        dist[0] = 0;
        var clear = function (p, r) {
          var len = segLength(p, r);
          for (var o = 0; o < obstacles.length; o++) {
            var hit = clipSegment(p, r, obstacles[o]);
            if (hit && (hit[1] - hit[0]) * len > 0.5) return false;
          }
          return true;
        };
        for (;;) {
          var at = -1;
          for (var m = 0; m < count; m++) if (!done[m] && (at < 0 || dist[m] < dist[at])) at = m;
          if (at < 0 || !isFinite(dist[at]) || at === 1) break;
          done[at] = true;
          for (var v = 0; v < count; v++) {
            if (done[v]) continue;
            // A little for every bend, so of two near-equal ways the
            // straighter wins.
            var d = dist[at] + segLength(pts[at], pts[v]) + 10;
            if (d < dist[v] && clear(pts[at], pts[v])) { dist[v] = d; prev[v] = at; }
          }
        }
        if (isFinite(dist[1])) {
          var way = [], step = 1;
          while (step >= 0) { way.unshift(pts[step]); step = prev[step]; }
          route = roundRoute(way);
        }
      }
      return route;
    }
    function threadRoutes(focus, hot, rs) {
      var sig = 0;
      for (var q = 0; q < labelBoxes.length; q++) sig += labelBoxes[q].x0 * 3 + labelBoxes[q].y1 * 7;
      var key = [focus, view.k, view.tx, view.ty, hot.join(','), labelBoxes.length, sig.toFixed(2)].join('|');
      if (routeCache && routeCache.key === key) return routeCache.routes;
      var routes = {};
      hot.forEach(function (at) {
        var other = edges[at][0] === focus ? edges[at][1] : edges[at][0];
        if (nodes[other]) routes[other] = routeThread(focus, other, rs);
      });
      routeCache = { key: key, routes: routes };
      return routes;
    }
    /* The lit threads run out from the object in focus (6 October 2026):
       when a reader settles on something new, its threads are drawn from it
       toward what they reach, all at one speed, so a near neighbour is
       joined first and the farthest last, in a quarter of a second. The
       field shows the connection being made, then holds still. A focus that
       returns (a kept result after a hover elsewhere) and reduced motion
       show the threads whole. */
    var THREAD_GROW = 240;
    function threadGrowth(focus) {
      if (focus < 0 || pulse.at !== focus || pulse.ms >= THREAD_GROW) return 1;
      var t = Math.max(0, pulse.ms / THREAD_GROW);
      return 1 - Math.pow(1 - t, 3);
    }
    /* The lit edges on the map's page, straight, from the focus outward.
       A thread is light leaving the object in focus (7 October 2026): it
       is brightest where it starts, and one that runs far (to the centre,
       to Comparator, to a problem across the window or out of it) keeps its
       full ink only for the local reach, then cools toward its end, so the
       field near the subject is drawn in precise lines and the long rays to
       the hubs read as direction rather than as the brightest marks on the
       canvas. A near thread keeps its ink to its end, and a thread whose
       far end leaves the window ends at the edge, where its name is set. */
    var THREAD_LOCAL = 0.2, THREAD_FAR_ALPHA = 0.24;

    /* ---- References from the page (7 October 2026) ---------------------
       The kept result's page names things the figure also draws: the paper
       that states it, the same statement in the other paper (they cite one
       Lean declaration), Comparator's replay, Palomar's prepared corpus.
       Resting on, or tabbing to, such a reference identifies exactly that
       relation on the figure: its thread comes up to full ink and full
       length, the other threads step back, and its far end is ringed (or,
       off the window, its name at the edge is set in ink). The kept result
       stays the subject: nothing is selected, the camera does not move and
       the page is not redrawn. Only relations the record draws are
       referable; the Lean row names no object on the figure, so it has
       none. */
    var referAt = -1, referShown = -1, referMix = 0, referFrame = 0, referAnim = null, REFER_MS = 170;
    var referEl = null;
    function setRefer(j) {
      if (j === referAt) return;
      referAt = j;
      if (j >= 0) { if (referShown !== j) referMix = 0; referShown = j; }
      referAnim = { from: referMix, to: j >= 0 ? 1 : 0, start: null };
      if (reduceMotion || !window.requestAnimationFrame) {
        referMix = referAnim.to; referAnim = null;
        if (j < 0) referShown = -1;
        draw();
        return;
      }
      if (!referFrame) referFrame = requestMotionFrame(stepRefer);
    }
    function stepRefer(now) {
      referFrame = 0;
      var a = referAnim;
      if (!a) return;
      if (a.start === null) a.start = now;
      var t = Math.min(1, (now - a.start) / REFER_MS);
      referMix = a.from + (a.to - a.from) * (1 - (1 - t) * (1 - t));
      if (t < 1) referFrame = requestMotionFrame(stepRefer);
      else { referAnim = null; if (a.to === 0) referShown = -1; }
      draw();
    }
    // The object the page refers to, while the kept result is the focus.
    function referring(focus) {
      return focus >= 0 && focus === selected && referShown >= 0 && nodes[referShown] ? referShown : -1;
    }
    // Whether the figure draws a relation from result i to object j: a
    // thread of the record (its paper, Comparator, Palomar) or the shared
    // declaration that joins it to its counterpart in the other paper.
    function relationDrawn(i, j) {
      if (i < 0 || j < 0 || i === j || !nodes[i] || !nodes[j] || !visible(nodes[j])) return false;
      if ((nodes[i].twins || []).some(function (t) { return t.at === j; })) return true;
      var list = incidentEdges(i);
      for (var q = 0; q < list.length; q++) {
        var e = edges[list[q]];
        if ((e[0] === i && e[1] === j) || (e[1] === i && e[0] === j)) return true;
      }
      return false;
    }
    function referAttr(i, j) {
      return relationDrawn(i, j) ? ' data-universe-refer="' + j + '"' : '';
    }
    function referInk(j) {
      return nodes[j].kind === 'integration_surface' ? glyphColor(nodes[j]) : palette.ink;
    }
    // The far end of the relation in reference, ringed like a registration mark.
    function drawReferMark(focus, rs, w, h) {
      var ref = referring(focus);
      if (ref < 0 || referMix <= 0) return;
      var n = nodes[ref], x = n.x * view.k + view.tx, y = n.y * view.k + view.ty;
      if (x < -20 || y < -20 || x > w + 20 || y > h + 20) return;
      var r = n.r * rs + 5;
      ctx.strokeStyle = referInk(ref);
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = referMix;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.stroke();
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.35 * referMix;
      ctx.beginPath();
      ctx.arc(x, y, r + 4 + 3 * referMix, 0, Math.PI * 2);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    function fadedHot(part) {
      var keep = part == null ? THREAD_FAR_ALPHA : part;
      var key = 'hotfade|' + palette.edgeHot + '|' + keep;
      var hit = mixCache[key];
      if (hit === undefined) {
        var c = parseColor(palette.edgeHot);
        hit = c ? 'rgba(' + Math.round(c[0] * 255) + ', ' + Math.round(c[1] * 255) + ', ' + Math.round(c[2] * 255) +
          ', ' + (c[3] * keep).toFixed(3) + ')' : null;
        mixCache[key] = hit;
      }
      return hit;
    }
    function drawHotEdges(focus, hot, grown) {
      // While the rings seat, each end rides its own ring.
      if (focus < 0 || !nodes[focus] || reveal < 1) { drawEdgeSet(hot, 1, 1.25, palette.edgeHot); return; }
      var f = nodes[focus], fx = f.x * view.k + view.tx, fy = f.y * view.k + view.ty;
      var w = canvas.clientWidth, h = canvas.clientHeight, local = THREAD_LOCAL * Math.min(w, h);
      var ends = [], longest = 0;
      hot.forEach(function (at) {
        var o = nodes[edges[at][0] === focus ? edges[at][1] : edges[at][0]];
        if (!o) return;
        var ox = o.x * view.k + view.tx, oy = o.y * view.k + view.ty;
        var len = Math.sqrt((ox - fx) * (ox - fx) + (oy - fy) * (oy - fy));
        longest = Math.max(longest, len);
        ends.push([ox, oy, len, edges[at][0] === focus ? edges[at][1] : edges[at][0]]);
      });
      var reach = grown >= 1 ? Infinity : grown * longest;
      var faded = pageMode && ctx.createLinearGradient ? fadedHot() : null;
      var ref = referring(focus), rest = ref >= 0 ? 1 - 0.72 * referMix : 1, named = null;
      ctx.lineWidth = 1.25;
      ctx.globalAlpha = rest;
      var near = [];
      ends.forEach(function (e) {
        if (e[3] === ref) { named = e; return; }
        var share = e[2] > reach ? reach / e[2] : 1;
        if (share <= 0) return;
        var tx = fx + (e[0] - fx) * share, ty = fy + (e[1] - fy) * share;
        // Where the thread leaves the window, if it does.
        var span = clipSegment([fx, fy], [e[0], e[1]], { x0: 0, x1: w, y0: 0, y1: h });
        var shown = (span ? Math.min(span[1], share) : share) * e[2];
        var grad = faded && e[2] > local * 1.5 && shown > local ? ctx.createLinearGradient(fx, fy, e[0], e[1]) : null;
        if (!grad || typeof grad.addColorStop !== 'function') { near.push([tx, ty]); return; }
        // Full ink for the local reach, then cooling to the edge or the end.
        var hold = Math.min(0.9, local / e[2]), cool = Math.max(hold + 0.05, Math.min(1, shown / e[2]));
        grad.addColorStop(0, palette.edgeHot);
        grad.addColorStop(hold, palette.edgeHot);
        // Cooling eases out: most of the light is gone by halfway.
        grad.addColorStop(hold + (cool - hold) * 0.45, fadedHot(0.5));
        grad.addColorStop(cool, faded);
        if (cool < 1) grad.addColorStop(1, faded);
        ctx.strokeStyle = grad;
        ctx.beginPath();
        ctx.moveTo(fx, fy);
        ctx.lineTo(tx, ty);
        ctx.stroke();
      });
      if (near.length) {
        ctx.strokeStyle = palette.edgeHot;
        ctx.beginPath();
        near.forEach(function (e) { ctx.moveTo(fx, fy); ctx.lineTo(e[0], e[1]); });
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
      if (!named) return;
      // The relation in reference: whole, uncooled, a step heavier, in the
      // ink of what it reaches.
      ctx.strokeStyle = referInk(ref);
      ctx.lineWidth = 1.25 + 0.75 * referMix;
      ctx.globalAlpha = 0.55 + 0.45 * referMix;
      ctx.beginPath();
      ctx.moveTo(fx, fy);
      ctx.lineTo(named[0], named[1]);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    // The routed threads, in the lit thread's ink: a straight line, or a
    // curve drawn as its run of short pieces; while they grow, each is
    // drawn as far along its route as the growth has reached.
    function drawThreads(routes, grown) {
      ctx.lineWidth = 1.25;
      ctx.strokeStyle = palette.edgeHot;
      ctx.globalAlpha = 1;
      ctx.lineJoin = 'round';
      ctx.lineCap = 'butt';
      var keys = Object.keys(routes), lengths = {}, longest = 0;
      if (grown < 1) {
        keys.forEach(function (other) {
          var pts = routes[other].points;
          lengths[other] = pts && pts.length > 1 ? wayLength(pts) : 0;
          longest = Math.max(longest, lengths[other]);
        });
      }
      var reach = grown * longest;
      ctx.beginPath();
      keys.forEach(function (other) {
        var pts = routes[other].points;
        if (!pts || pts.length < 2) return;
        var left = grown < 1 ? reach : Infinity;
        ctx.moveTo(pts[0][0], pts[0][1]);
        for (var j = 1; j < pts.length && left > 0; j++) {
          var len = segLength(pts[j - 1], pts[j]);
          if (len <= left) { ctx.lineTo(pts[j][0], pts[j][1]); left -= len; continue; }
          var f = left / len;
          ctx.lineTo(pts[j - 1][0] + (pts[j][0] - pts[j - 1][0]) * f, pts[j - 1][1] + (pts[j][1] - pts[j - 1][1]) * f);
          left = 0;
        }
      });
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
    // A point a given share of the way along a route.
    function alongRoute(pts, share) {
      var total = 0, j;
      for (j = 1; j < pts.length; j++) total += segLength(pts[j - 1], pts[j]);
      var want = Math.max(0, Math.min(1, share)) * total;
      for (j = 1; j < pts.length; j++) {
        var len = segLength(pts[j - 1], pts[j]);
        if (want <= len || j === pts.length - 1) {
          var f = len ? Math.min(1, want / len) : 0;
          return [pts[j - 1][0] + (pts[j][0] - pts[j - 1][0]) * f, pts[j - 1][1] + (pts[j][1] - pts[j - 1][1]) * f];
        }
        want -= len;
      }
      return pts[pts.length - 1];
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
        rows += '<li>' + glyphHtml(STATUS_TIER[keys[j]]) + '<span>' + escapeHtml(capitalFirst(keys[j])) +
          '</span><b>' + counts[keys[j]] + '</b></li>';
      }
      return { html: '<ul class="universe-inspector__census universe-inspector__census--status">' + rows + '</ul>', total: total };
    }

    /* The panel reads the map in three levels (5 October 2026). At rest it
       orients: the counts said in words, the evidence across every result
       in one bar, and the eight problems as landmarks, each a row the
       keyboard reaches, with its own count and gauge. A problem chosen reads
       its question, its short paper (the précis whole, never cut) and its
       results in the order its papers state them. A result chosen reads its
       statement in the paper's words, how far it is checked, and the ways
       out; the problem shrinks to one line above it. Nothing folds. */
    function gaugeHtml(counts, label) {
      var total = 0, key;
      for (key in counts) total += counts[key];
      if (!total) return '';
      var segs = '', words = [], x = 0;
      for (var j = 0; j < EVIDENCE_ORDER.length; j++) {
        key = EVIDENCE_ORDER[j];
        if (!counts[key]) continue;
        segs += '<rect class="universe-gauge__seg universe-gauge__seg--' + key + '" x="' + x + '" width="' + counts[key] + '" height="1"/>';
        x += counts[key];
        words.push(fmtCount(counts[key]) + ' ' + EVIDENCE_TEXT[key]);
      }
      return '<svg class="universe-gauge" viewBox="0 0 ' + total + ' 1" preserveAspectRatio="none" role="img" aria-label="' + escapeHtml((label ? label + ': ' : '') + words.join(', ')) + '">' + segs + '</svg>';
    }

    // The map's own count of what it holds, said as a sentence.
    function summaryHtml() {
      var s = statementMeta && statementMeta.summary;
      if (!s || !s.statements) return '';
      var papers = {}, paperCount = 0, problems = 0;
      nodes.forEach(function (n) {
        if (n.kind === 'problem') problems++;
        if (n.kind === 'paper_statement' && n.paperId && !papers[n.paperId]) { papers[n.paperId] = true; paperCount++; }
      });
      return '<p class="universe-summary">' + fmtCount(s.statements) + ' results from ' + countWords(paperCount) +
        ' papers on ' + countWords(problems) + ' problems. Lean states ' + fmtCount(s.lean_exact) +
        ' of them exactly, in ' + fmtCount(s.lean_declarations) + ' declarations, and Comparator has replayed ' +
        fmtCount((s.comparator || {}).compared || 0) + '.</p>';
    }
    var COUNT_WORDS = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
      'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty'];
    function countWords(n) { return n >= 0 && n < COUNT_WORDS.length ? COUNT_WORDS[n] : fmtCount(n); }

    // A problem's results by evidence, among those the filters show.
    function sectorTally(pid) {
      var t = { total: 0, replayed: 0, lean: 0, modulo: 0, none: 0 };
      nodes.forEach(function (n) {
        if (n.kind !== 'paper_statement' || n.sector !== pid || !visible(n)) return;
        t.total++;
        if (t[n.tier] !== undefined) t[n.tier]++;
      });
      return t;
    }
    // "174 of its 186 results are replayed by Comparator; 6 more are exact
    // in Lean with no replay recorded; …"
    function tallySentence(t) {
      if (!t.total) return 'None of its results is shown with these filters.';
      var parts = [(t.replayed === t.total ? (t.total === 1 ? 'Its one result is' : 'All ' + t.total + ' of its results are') :
        t.replayed + ' of its ' + t.total + ' results ' + (t.replayed === 1 ? 'is' : 'are')) + ' replayed by Comparator'];
      if (t.lean) parts.push(t.lean + ' more ' + (t.lean === 1 ? 'is' : 'are') + ' exact in Lean with no replay recorded');
      if (t.modulo) parts.push(t.modulo + ' ' + (t.modulo === 1 ? 'is' : 'are') + ' stated in Lean under named inputs');
      if (t.none) parts.push(t.none + ' ' + (t.none === 1 ? 'has' : 'have') + ' no Lean statement yet');
      return parts.join('; ') + '.';
    }

    /* The Problems view (6 October 2026): the panel at rest is a guide to
       choosing a problem, with nothing appended. The lede (the head no
       longer carries it); the scope in two short lines and the way into the
       evidence in full; the eight problems, each a row the keyboard
       reaches, its title the row's largest words, how many of its results
       Comparator has replayed in figures that line up, and a slim strip of
       the same counts; then the results by evidence in four lines. How to
       read the map, where it comes from and every object as lists are
       views of their own (the panel views, below). */
    function ledeHtml() {
      var lede = inspector && inspector.getAttribute ? inspector.getAttribute('data-universe-lede') : null;
      return lede ? '<p class="universe-lede">' + escapeHtml(lede) + '</p>' : '';
    }
    function scopeLineHtml() {
      var s = statementMeta && statementMeta.summary;
      if (!s || !s.statements) return '';
      var papers = {}, paperCount = 0, problems = 0;
      nodes.forEach(function (n) {
        if (n.kind === 'problem') problems++;
        if (n.kind === 'paper_statement' && n.paperId && !papers[n.paperId]) { papers[n.paperId] = true; paperCount++; }
      });
      return '<p class="universe-scope-line"><span class="universe-scope-line__lead">' + fmtCount(problems) + ' problems, ' +
        fmtCount(paperCount) + ' problem papers</span><span class="universe-scope-line__totals">' + fmtCount(s.statements) +
        ' paper results, ' + fmtCount((s.comparator || {}).compared || 0) + ' replayed by Comparator.</span>' +
        (explorerRoot ? '<button type="button" class="universe-scope-line__go" data-universe-view-go="about" data-universe-view-at="evidence">The evidence in full</button>' : '') +
        '</p>';
    }

    function overviewHtml() {
      var shown = 0;
      for (var i = 0; i < nodes.length; i++) if (visible(nodes[i])) shown++;
      var parts = [ledeHtml(), explorerRoot ? scopeLineHtml() : summaryHtml()];
      var evidence = evidenceCensusHtml(null);
      if (!evidence.total) {
        parts.push('<p class="universe-inspector__body">No paper results match these filters; ' + fmtCount(shown) +
          ' other objects are shown. Change or reset the map filters to see more.</p>');
      }
      if (bands.length) {
        var problemCount = 0;
        var problemRows = bands.map(function (b) {
          var at = problemIndex[b.sector];
          if (at === undefined) return '';
          problemCount++;
          var t = sectorTally(b.sector), visibleEvidence = {};
          EVIDENCE_ORDER.forEach(function (key) { if (t[key]) visibleEvidence[key] = t[key]; });
          var p = nodes[at];
          return '<li><button type="button" class="universe-problem' + (at === lastProblemAt ? ' is-current' : '') +
            '" data-universe-go="' + at + '"' + (at === lastProblemAt ? ' aria-current="true"' : '') + '>' +
            '<span class="universe-problem__num">' + escapeHtml(p.shortLabel) + '</span>' +
            '<span class="universe-problem__name">' + escapeHtml(p.label) + '</span>' +
            '<span class="universe-problem__count">' + (t.total ? '<b>' + fmtCount(t.replayed) + '</b> of ' + fmtCount(t.total) +
              (t.total === 1 ? ' result' : ' results') + ' replayed' : 'No results shown') + '</span>' +
            gaugeHtml(visibleEvidence, p.shortLabel) + '</button></li>';
        }).join('');
        parts.push('<h2 class="universe-section__title universe-problems__title">The ' + countWords(problemCount) + ' problems</h2>' +
          '<ol class="universe-problems">' + problemRows + '</ol>');
      }
      if (evidence.total && explorerRoot) {
        parts.push('<h3 class="universe-inspector__sub">Results by evidence</h3>' + evidence.html);
      }
      if (bands.length) {
        parts.push('<p class="universe-inspector__hint">Choose a problem, here or on the map, to read its question, its short paper and its results. ' +
          'Drag to move the map and scroll to zoom; press <kbd>/</kbd> to find a theorem, and <kbd>Esc</kbd> to go back.</p>');
      }
      if (!explorerRoot) parts.push(evidenceInFullHtml());
      return parts.join('');
    }
    /* The evidence in full, in the How to read view: the results by
       evidence, the claims by status and the Lean behind them, counted over
       what the map shows; the fans inside the ring said in words. */
    function evidenceInFullHtml() {
      var parts = [];
      var evidence = evidenceCensusHtml(null);
      if (evidence.total) parts.push('<h4 class="universe-inspector__sub">Paper results by evidence</h4>' + evidence.html);
      var status = statusCensusHtml(null);
      if (status.total) parts.push('<h4 class="universe-inspector__sub">Claims in the records, by status</h4>' + status.html);
      var s = statementMeta && statementMeta.summary;
      if (s) {
        parts.push('<p class="universe-inspector__note">' + fmtCount(s.lean_declarations) +
          ' Lean declarations in ' + fmtCount(s.lean_files) + ' files state these results. Source: the ' +
          (statementMeta.ledger ? '<a href="' + escapeHtml(statementMeta.ledger) + '" data-link-kind="exogenous" rel="external noopener" target="_blank">coverage ledger</a>' : 'coverage ledger') +
          '.</p>');
      }
      if (evidence.total || status.total) {
        parts.push('<p class="universe-inspector__note">These counts follow the map filters' +
          (fullLoaded ? '.' : ' and the objects loaded so far.') + '</p>');
      }
      return parts.join('');
    }
    function captionsHtml() {
      return captions.map(function (c) {
        return 'The fan inside the ring is ' + escapeHtml(c.sub || '') + ', ' + escapeHtml(c.text) + '.';
      }).join(' ');
    }

    /* ---- A problem's card ------------------------------------------- */
    /* The problem's question and its short paper come from the landing's
       companion data (universe-companion.json: the question and précis set
       with their mathematics), fetched once, the first time a problem is
       read; until it arrives the card reads the map's own plain question. */
    var problemInfo = null, problemInfoState = 'idle';
    function loadProblemInfo() {
      if (problemInfoState !== 'idle' || !companionSpec || !companionSpec.data || typeof fetch !== 'function') return;
      problemInfoState = 'loading';
      fetch(route(companionSpec.data)).then(function (r) {
        if (r.ok === false) throw new Error('Problem descriptions unavailable');
        return r.json();
      }).then(function (payload) {
        if (!payload || !payload.problems) throw new Error('Problem descriptions missing');
        problemInfo = payload.problems;
        problemInfoState = 'ready';
        refreshInspector();
        if (previewAt >= 0) refreshPreview(true);
      }).catch(function () { problemInfoState = 'failed'; });
    }
    function problemInfoOf(n) {
      if (!problemInfo) { loadProblemInfo(); return null; }
      return n.sector ? problemInfo[n.sector] || null : null;
    }
    function itemRowHtml(at) {
      var m = nodes[at], lab = splitLabel(m.label);
      var mark = m.proof_status === 'ordinary_proof' && m.tier === 'none' ? 'ordinary_proof' : m.tier;
      return '<li><button type="button" class="universe-item" data-universe-go="' + at + '"' +
        ' aria-label="' + escapeHtml(m.label + ', ' + (EVIDENCE_TEXT[m.tier] || 'paper result')) + '">' +
        glyphHtml(mark) + '<span class="universe-item__num">' + escapeHtml(lab.number) + '</span>' +
        (lab.name ? '<span class="universe-item__name">' + escapeHtml(capitalFirst(lab.name)) + '</span>' : '') +
        '</button></li>';
    }
    function problemPapers(n) {
      var pids = Object.keys(paperSequence).filter(function (pid) {
        var first = nodes[paperSequence[pid][0]];
        return !!first && first.sector === n.sector;
      });
      pids.sort(function (p, q) {
        return (SIDE_ORDER[nodes[paperSequence[p][0]].side] || 0) - (SIDE_ORDER[nodes[paperSequence[q][0]].side] || 0) ||
          (p < q ? -1 : p > q ? 1 : 0);
      });
      return pids;
    }
    function problemCardHtml(i, pinned) {
      var n = nodes[i];
      var info = problemInfoOf(n);
      var head = '<p class="universe-inspector__kind universe-kicker">Erdős problem ' + escapeHtml(n.shortLabel) + '</p>';
      head = pinned ? cardHeadHtml(head) : previewHeadHtml(head);
      var parts = [head, '<h2 class="universe-inspector__title universe-inspector__title--problem">' + escapeHtml(n.label) + '</h2>'];
      if (n.status && n.status !== 'open') {
        parts.push('<p class="universe-inspector__meta"><span class="universe-chip universe-chip--status">' + escapeHtml(capitalFirst(n.status)) + '</span></p>');
      }
      // Until the set question arrives (a moment, once) the line waits
      // empty rather than flash the plain text's markup.
      var plainQuestion = !companionSpec || problemInfoState === 'failed';
      var question = info && info.question_html ? info.question_html : plainQuestion ? escapeHtml(n.question || '') : '';
      if (question) parts.push('<p class="universe-question">' + question + '</p>');
      if (info && info.note_html) parts.push('<p class="universe-inspector__note">' + info.note_html + '</p>');
      var t = sectorTally(n.sector), counts = {};
      EVIDENCE_ORDER.forEach(function (key) { if (t[key]) counts[key] = t[key]; });
      parts.push('<p class="universe-tally">' + escapeHtml(tallySentence(t)) + '</p>');
      if (t.total) parts.push('<div class="universe-overview__gauge">' + gaugeHtml(counts, n.shortLabel) + '</div>');
      var papers = info && info.papers || [];
      var short = papers.filter(function (p) { return p.label === 'Short paper'; })[0] || papers[0];
      var long = papers.filter(function (p) { return p !== short && p.page; })[0];
      if (short) {
        var go = [];
        if (short.page) {
          // universe-open--primary is the hook the site's navigation
          // warming (docs.js) reads; a chosen problem's next read is its
          // short paper.
          go.push('<a class="universe-go universe-go--primary' + (pinned ? ' universe-open--primary' : '') + '" href="' +
            escapeHtml(route(short.page)) + '">Read the short paper</a>');
        }
        if (short.pdf) {
          go.push(extLink(short.pdf, 'PDF' + (short.pages ? ', ' + short.pages + '&nbsp;pages' : ''), 'universe-go'));
        }
        if (long && long.page) go.push('<a class="universe-go" href="' + escapeHtml(route(long.page)) + '">The long record</a>');
        if (n.page) go.push('<a class="universe-go" href="' + escapeHtml(route(n.page)) + '">The problem’s page</a>');
        parts.push('<section class="universe-paper" aria-label="The short paper">' +
          '<p class="universe-label">The short paper</p>' +
          '<p class="universe-paper__title">' + (short.page ? '<a href="' + escapeHtml(route(short.page)) + '">' + short.title_html + '</a>' : short.title_html) + '</p>' +
          (short.precis_html ? '<p class="universe-precis">' + short.precis_html + '</p>' : '') +
          (go.length ? '<p class="universe-quote__go">' + go.join('') + '</p>' : '') + '</section>');
      } else if (n.page) {
        parts.push('<p class="universe-quote__go"><a class="universe-go universe-go--primary" href="' + escapeHtml(route(n.page)) + '">The problem’s page</a></p>');
      }
      if (!pinned) {
        parts.push('<p class="universe-inspector__hint">Click to choose it: its sector is framed and its results are listed here.</p>');
        return parts.join('');
      }
      // Its results, paper by paper, in the order each paper states them.
      var lists = problemPapers(n).map(function (pid) {
        var run = paperSequence[pid].filter(function (at) { return visible(nodes[at]); });
        if (!run.length) return '';
        var first = nodes[run[0]];
        var paper = papers.filter(function (p) { return p.id === pid; })[0];
        return '<p class="universe-list__from">' + capitalFirst(first.side === 'long' ? 'the long record' : roleName(first)) +
          (paper ? ', <cite>' + paper.title_html + '</cite>' : first.paperTitle ? ', <cite>' + escapeHtml(first.paperTitle) + '</cite>' : '') +
          ' <span class="universe-list__count">' + run.length + (run.length === 1 ? ' result' : ' results') + '</span></p>' +
          '<ol class="universe-list">' + run.map(itemRowHtml).join('') + '</ol>';
      }).join('');
      if (lists) {
        parts.push('<h3 class="universe-inspector__sub">Its results</h3>' +
          '<p class="universe-inspector__hint universe-inspector__hint--lead">Point at one to find it on the map; choose it to read it.</p>' + lists);
      }
      // Its papers, claims and Lean modules as lists: the index, scoped to
      // this problem, with a way back to this card.
      if (explorerRoot && n.sector && document.querySelector('[data-universe-pane="index"]')) {
        parts.push('<p class="universe-card__index"><button type="button" class="universe-go" data-universe-index-scope="' +
          escapeHtml(n.sector) + '">Everything on ' + escapeHtml(n.shortLabel) + ' in the index</button></p>');
      }
      parts.push(sectorSummaryHtml(i, true));
      if (canCopy) {
        parts.push('<button type="button" class="universe-inspector__copy" data-universe-copy>Copy a link to this</button>');
      }
      parts.push(stepBackHtml());
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
      // Totient Series". Every group lists all it names, each name whole;
      // a long group says its count under its phrase. Nothing folds.
      var groups = {}, order = [];
      for (var j = 0; j < rows.length; j++) {
        var row = rows[j];
        var m = nodes[row.to];
        var key = row.rel + ':' + row.out + ':' + m.kind;
        if (!groups[key]) { groups[key] = { kind: m.kind, phrase: relPhrase(row.rel, row.out), rel: row.rel, out: row.out, items: [] }; order.push(key); }
        groups[key].items.push({ to: row.to, html: m.kind === 'paper_statement' ? itemRowHtml(row.to) :
          '<li><button type="button" class="universe-goto" data-universe-go="' + row.to + '">' +
          dotHtml(m.kind) + '<span class="universe-goto__label">' + escapeHtml(m.label) + '</span></button></li>' });
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
        var many = (KIND_PLURAL[group.kind] || group.kind).toLowerCase();
        var head = '<li class="universe-link"><span class="universe-link__how">' + escapeHtml(group.phrase) +
          (group.items.length > 3 ? ' <span class="universe-link__count">' + group.items.length + ' ' + escapeHtml(many) + '</span>' : '') +
          '</span>';
        if (owner.kind === 'integration_surface' && group.kind === 'paper_statement') {
          html += head + checkerListsHtml(group.items) + '</li>';
          continue;
        }
        var items = group.items.map(function (item) { return item.html; }).join('');
        html += head + '<ul class="universe-list' + (group.kind === 'paper_statement' ? '' : ' universe-list--goto') + '">' + items + '</ul></li>';
      }
      return { html: html ? '<ul class="universe-links">' + html + '</ul>' : '', total: rows.length };
    }

    /* What Comparator replayed (or Palomar holds) is read as the problem
       cards read their results (6 October 2026): problem by problem in the
       order the map lists them, each paper under its own line, short paper
       first, every result in the order its paper states it. One long list
       sorted by name ran "6.4, 6.40, 6.49, 6.5, 6.52" and printed the same
       number twice from two papers with nothing to tell them apart. */
    function checkerListsHtml(items) {
      var bandAt = {};
      bands.forEach(function (b, k) { bandAt[b.sector] = k; });
      var runs = {}, order = [];
      items.forEach(function (item) {
        var m = nodes[item.to], key = m.paperId || '';
        if (!runs[key]) { runs[key] = { first: m, items: [] }; order.push(key); }
        runs[key].items.push(item);
      });
      order.sort(function (p, q) {
        var a = runs[p].first, b = runs[q].first;
        var pa = bandAt[a.sector], pb = bandAt[b.sector];
        pa = pa === undefined ? 1e3 : pa; pb = pb === undefined ? 1e3 : pb;
        return pa - pb || (SIDE_ORDER[a.side] || 0) - (SIDE_ORDER[b.side] || 0) || (p < q ? -1 : p > q ? 1 : 0);
      });
      return order.map(function (key) {
        var run = runs[key], first = run.first;
        run.items.sort(function (a, b) {
          var sa = nodes[a.to].seq, sb = nodes[b.to].seq;
          return (typeof sa === 'number' ? sa : 1e6) - (typeof sb === 'number' ? sb : 1e6);
        });
        var problem = first.sector && problemIndex[first.sector] !== undefined ? nodes[problemIndex[first.sector]].shortLabel : null;
        var where = capitalFirst(first.side === 'long' ? 'the long record' : roleName(first)) + (problem ? ' on ' + problem : '');
        return '<p class="universe-list__from">' + escapeHtml(where) +
          (first.paperTitle ? ', <cite>' + escapeHtml(first.paperTitle) + '</cite>' : '') +
          ' <span class="universe-list__count">' + run.items.length + (run.items.length === 1 ? ' result' : ' results') + '</span></p>' +
          '<ol class="universe-list">' + run.items.map(function (item) { return item.html; }).join('') + '</ol>';
      }).join('');
    }

    /* What sits with a problem, by status, with the shared fan named. */
    function sectorSummaryHtml(i, withoutResults) {
      var n = nodes[i];
      if (n.kind !== 'problem' || !n.sector) return '';
      var pid = n.sector;
      var own = statusCensusHtml(function (m) { return m.sector === pid; });
      var results = evidenceCensusHtml(function (m) { return m.sector === pid; });
      var parts = [];
      if (results.total && !withoutResults) {
        parts.push('<h3 class="universe-inspector__sub">Paper results (' + results.total + ')</h3>');
        parts.push(results.html);
      }
      if (own.total) {
        parts.push('<h3 class="universe-inspector__sub">Claims in its record (' + own.total + ')</h3>');
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
          // The paper's title says where; its TeX label is a source anchor,
          // not a word for the reader, and stays in the link only.
          '<span class="universe-open__where">' + escapeHtml(n.paperTitle || 'paper') + '</span></a>');
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
        rows += '<li>' + glyphHtml(key) + '<span>' + escapeHtml(capitalFirst(EVIDENCE_TEXT[key])) +
          '</span><b>' + counts[key] + '</b></li>';
      }
      return { html: '<ul class="universe-inspector__census universe-inspector__census--status">' + rows + '</ul>', total: total };
    }

    // One formatter, made once: toLocaleString builds a new one per call,
    // and the panel and the count line ask for dozens a frame.
    var countFormat = null;
    function fmtCount(value) {
      if (value == null) return '';
      if (countFormat === null) {
        try { countFormat = new Intl.NumberFormat('en-GB'); } catch (err) { countFormat = false; }
      }
      return countFormat ? countFormat.format(Number(value)) : Number(value).toLocaleString('en-GB');
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

    function detailHref(n) {
      if (detailUrl && details[detailUrl]) return detailUrl;
      var relative = detailRoutes[n.paperId];
      var expected = 'assets/statement-details/' + n.paperId + '.json';
      var href = relative && /^[a-z0-9-]+$/.test(n.paperId) &&
        relative.split('?')[0] === expected ? route(relative) : null;
      return href && !detailFailed[href] ? href : detailUrl;
    }

    function loadDetail(n) {
      var href = detailHref(n);
      if (!href || details[href] || detailLoading[href] || detailFailed[href]) return;
      detailLoading[href] = true;
      fetch(href).then(function (r) {
        if (r.ok === false) throw new Error('Statement details unavailable');
        return r.json();
      }).then(function (payload) {
        if (!payload || !payload.statements || (payload.paper && payload.paper !== n.paperId)) {
          throw new Error('Statement details belong to another paper');
        }
        details[href] = payload;
        delete detailLoading[href];
        if (selected >= 0 || hover >= 0) refreshInspector();
      }).catch(function () {
        delete detailLoading[href];
        detailFailed[href] = true;
        loadDetail(n);
        if (selected >= 0) refreshInspector();
      });
    }

    function evidenceSentence(n) {
      var how = n.lean_status === 'exact_or_stronger' ? 'Lean states it or something stronger' : 'Lean states it exactly';
      var text;
      if (n.lean_status === 'exact' || n.lean_status === 'exact_or_stronger') {
        text = n.comparator_status === 'compared' ? how + ', and Comparator has replayed that statement.' :
          how + '. ' + comparatorReplayText(n);
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
    /* A claim's words come from the record as plain text written with
       ASCII notation ("sum_{j<N} j^2", "d <= X", "N^(-8 xi)", "H_a"). The
       card sets that notation as a reader of mathematics expects
       (7 October 2026): subscripts and superscripts, ≤ ≥ ≠, ∑ and ∏, and a
       Greek letter where its name stands as a symbol. Only the marks of
       notation change; every symbol, number and word of the statement
       stays, and a Lean identifier (total_totient_series) is never read as
       a subscript, because a subscript's base is one letter standing on
       its own. */
    var GREEK_NAMES = { alpha: 'α', beta: 'β', gamma: 'γ', delta: 'δ', epsilon: 'ε', theta: 'θ', kappa: 'κ',
      lambda: 'λ', mu: 'μ', nu: 'ν', xi: 'ξ', rho: 'ρ', sigma: 'σ', tau: 'τ', phi: 'φ', chi: 'χ', psi: 'ψ', omega: 'ω',
      Gamma: 'Γ', Delta: 'Δ', Theta: 'Θ', Lambda: 'Λ', Sigma: 'Σ', Phi: 'Φ', Psi: 'Ψ', Omega: 'Ω' };
    var GREEK_WORD = /(^|[\s(=^_{,+\/−])(alpha|beta|gamma|delta|epsilon|theta|kappa|lambda|mu|nu|xi|rho|sigma|tau|phi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Sigma|Phi|Psi|Omega)(?![A-Za-z0-9])/g;
    var SUB_MARK = /(^|[^A-Za-z_])([A-Za-zΑ-Ωα-ω∑∏])_(\{[^{}]{1,24}\}|\([^()]{1,24}\)|[A-Za-z0-9]{1,3}(?![A-Za-z0-9_]))/g;
    var SUP_MARK = /([A-Za-z0-9)\]α-ω])\^(\{[^{}]{1,24}\}|\([^()]{1,24}\)|[+\-−]?[A-Za-z0-9α-ω]{1,4}(?![A-Za-z0-9_])|[+\-−](?![A-Za-z0-9]))/g;
    function markInner(text) {
      var inner = /^[{(]/.test(text) ? text.slice(1, -1) : text;
      return inner.replace(/(^|[\s(])-(?=[\dA-Za-zα-ω])/g, '$1−');
    }
    function notationHtml(text) {
      var s = escapeHtml(String(text || ''));
      if (!/[_^]|&lt;=|&gt;=|!=|\b(?:alpha|beta|gamma|delta|epsilon|theta|kappa|lambda|mu|nu|xi|rho|sigma|tau|phi|chi|psi|omega|Gamma|Delta|Theta|Lambda|Sigma|Phi|Psi|Omega)\b/.test(s)) return s;
      s = s.replace(/&lt;=/g, '≤').replace(/&gt;=/g, '≥').replace(/!=/g, '≠');
      s = s.replace(/(^|[^A-Za-z_])(sum|prod)_/g, function (m, pre, op) { return pre + (op === 'sum' ? '∑' : '∏') + '_'; });
      s = s.replace(GREEK_WORD, function (m, pre, name) { return pre + GREEK_NAMES[name]; });
      s = s.replace(SUB_MARK, function (m, pre, base, mark) { return pre + base + '<sub>' + markInner(mark) + '</sub>'; });
      s = s.replace(SUP_MARK, function (m, base, mark) { return base + '<sup>' + markInner(mark) + '</sup>'; });
      // A hyphen between two set terms ("3^(n+1)-2^(n+1)") is a minus.
      s = s.replace(/(<\/su[bp]>|\))-(?=[0-9(A-Za-z])/g, '$1\u2212');
      return s;
    }
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

    var ROLE_NAME = { short: 'the short paper', long: 'the long paper' };
    var TAB_NAME = { short: 'Short paper', long: 'Long paper' };
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

    function loadExcerpts(pid, href) {
      if (!href || excerptLoaded[href] || excerptFailed[href] || excerptLoading[href]) return;
      excerptLoading[href] = true;
      fetch(route(href)).then(function (r) {
        if (r.ok === false) throw new Error('Paper quote unavailable');
        return r.json();
      }).then(function (payload) {
        var expected = excerptBatchIds[href];
        if (!payload || !Array.isArray(payload.excerpts) || (payload.paper && payload.paper !== pid) ||
            (expected && (payload.paper !== pid || payload.source !== excerptRoutes[pid].split('/').pop() ||
              payload.excerpts.length !== Object.keys(expected).length))) {
          throw new Error('Paper quotes belong to another edition');
        }
        var table = {};
        payload.excerpts.forEach(function (row) {
          if (!Array.isArray(row) || typeof row[0] !== 'string' || row[0].indexOf('statement:' + pid + '#') !== 0 ||
              typeof row[1] !== 'string' || typeof row[2] !== 'string' || table[row[0]] || (expected && !expected[row[0]])) {
            throw new Error('Paper quote set is incomplete');
          }
          table[row[0]] = { name: row[1] || '', body: row[2] || '' };
        });
        // A late batch must never discard quotes loaded by a newer selection.
        var cached = excerpts[pid] || (excerpts[pid] = {});
        Object.keys(table).forEach(function (id) { cached[id] = table[id]; });
        excerptLoaded[href] = true;
        delete excerptLoading[href];
        refreshResultCard(pid);
      }).catch(function () {
        excerptFailed[href] = true;
        delete excerptLoading[href];
        refreshResultCard(pid);
      });
    }
    // The quote arrives after the card: draw it again if it is still on show.
    function refreshResultCard(pid) {
      // The page sets its words again only where they changed: the card and
      // the preview each compare what they would show.
      if (pageMode) { refreshInspector(); if (previewAt >= 0) refreshPreview(true); return; }
      var at = selected >= 0 ? selected : hover;
      if (at < 0 || !nodes[at] || nodes[at].kind !== 'paper_statement') return;
      var shown = [at].concat((nodes[at].twins || []).map(function (t) { return t.at; }));
      if (!shown.some(function (k) { return nodes[k].paperId === pid; })) return;
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
      var full = excerptRoutes[m.paperId];
      if (!full) return null;
      var table = excerpts[m.paperId];
      if (table && table[m.id]) return table[m.id];
      if (excerptLoaded[full]) return null;
      var href = excerptLoading[full] ? full : excerptBatchRoutes[m.id] || full;
      if (excerptLoaded[href] || excerptFailed[href]) href = full;
      if (excerptFailed[href]) return null;
      loadExcerpts(m.paperId, href);
      return undefined;
    }

    // Related statement locations, the short paper first. Shared formal support is not equivalence.
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
        // Related statements in two papers; retain the reader's chosen excerpt.
        // The row says why there are two: they share Lean support.
        html += '<div class="universe-quote__tabs" role="tablist" aria-label="Related statements in the two papers">' +
          ((nodes[i].twins || []).length ? '<span class="universe-quote__twins" aria-hidden="true">Shared Lean support</span>' : '') +
          tabs.map(function (t) {
            var tm = nodes[t.at];
            // "Short paper, 5.2": short enough for two tabs on one line.
            return '<button type="button" role="tab" class="universe-quote__tab" aria-selected="' +
              (t.at === place.at) + '" data-universe-place="' + t.at + '"' + (t.at !== i ? referAttr(i, t.at) : '') + ' aria-label="' +
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
      if (place.at !== i && place.via) {
        html += '<p class="universe-quote__via">These statements cite a common Lean declaration. Compare their hypotheses and conclusions; shared support does not establish equivalence.</p>';
      }
      var go = [];
      if (m.paper) {
        // universe-open--primary is the hook the site's navigation warming
        // (docs.js) reads to fetch a pinned card's paper ahead of the click.
        go.push('<a class="universe-go universe-go--primary universe-open--primary" href="' +
          escapeHtml(route(m.paper)) + '"' + (pinned && place.at === i ? referAttr(i, paperOf(i)) : '') + '>Read it in the paper</a>');
      }
      if (m.tex && statementMeta && statementMeta.tex_source_base) {
        go.push(extLink(statementMeta.tex_source_base + m.tex, 'TeX source' + (m.line ? ', line ' + m.line : ''), 'universe-go'));
      }
      if (pinned && place.at !== i) {
        go.push('<button type="button" class="universe-go" data-universe-go="' + place.at + '"' + referAttr(i, place.at) + '>Select it on the map</button>');
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
      // Under its own heading after the checks, never folded: the code is
      // the evidence an expert reads (5 October 2026).
      return '<section class="universe-lean" aria-label="Its Lean statements"><h3 class="universe-inspector__sub">' +
        (decls.length > 1 ? 'Its ' + decls.length + ' Lean theorems' : 'Its Lean theorem') + '</h3>' +
        (ns ? '<p class="universe-lean__where">' + (decls.length > 1 ? 'Each sits' : 'It sits') + ' in the namespace <code>' +
          escapeHtml(ns.slice(0, -1)) + '</code>; ' + (decls.length > 1 ? 'a name opens its' : 'the name opens its') + ' line on GitHub.</p>' :
          '<p class="universe-lean__where">' + (decls.length > 1 ? 'A name opens its' : 'The name opens its') + ' line on GitHub.</p>') +
        '<ol class="universe-lean__list">' + items.join('') + '</ol></section>';
    }

    function checkHtml(state, station, sentence, more, refer) {
      return '<li class="universe-check universe-check--' + state + ' universe-check--' + station.toLowerCase() + '"' + (refer || '') + '>' +
        '<span class="universe-check__mark" aria-hidden="true"></span>' +
        '<div class="universe-check__body"><p class="universe-check__text"><b>' + station + '.</b> ' + sentence + '</p>' +
        (more || '') + '</div></li>';
    }

    function paperOf(i) {
      var at = nodes[i] && nodes[i].paperId ? byId['paper:' + nodes[i].paperId] : undefined;
      return at === undefined ? -1 : at;
    }
    function hubAttr(n, id) {
      var i = byId[n.id], j = byId[id];
      return i === undefined || j === undefined ? '' : referAttr(i, j);
    }
    function checksHtml(n, pinned) {
      var href = detailHref(n);
      var detail = pinned && details[href];
      var more = pinned && detail && detail.statements ? detail.statements[n.id] || null : null;
      if (pinned && !detail) loadDetail(n);
      var decls = n.decls || [];
      var rows = [];
      // Lean: how its statement stands to the printed one.
      var lean = n.lean_status || 'none';
      var count = decls.length > 1 ? ', in ' + decls.length + ' theorems' : '';
      var leanMore = '';
      // The named inputs and the Lean code follow the three stations.
      var after = '';
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
          after += '<section class="universe-lean" aria-label="The named inputs"><h3 class="universe-inspector__sub">' +
            (inputs.length > 1 ? 'The ' + inputs.length + ' named inputs' : 'The named input') + '</h3>' +
            '<p class="universe-lean__where">What Lean takes as given here; ' + (inputs.length > 1 ? 'a name opens its' : 'the name opens its') + ' source on GitHub.</p>' +
            '<ol class="universe-lean__list">' + inputs.map(function (input) {
              return '<li>' + extLink(input.href, '<code>' + nameHtml(input.name) + '</code>', 'universe-lean__name') +
                (input.text ? '<pre class="universe-lean__code"><code>' + escapeHtml(input.text) + '</code></pre>' : '') + '</li>';
            }).join('') + '</ol></section>';
        }
        after += leanListHtml(n, more);
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
        rows.push(checkHtml('done', 'Comparator', said, cmpMore, pinned ? hubAttr(n, 'integration:comparator') : ''));
      } else if (lean === 'exact' || lean === 'exact_or_stronger') {
        rows.push(checkHtml(n.comparator_status === 'pending' && n.comparator_queued_at ? 'queued' : 'none', 'Comparator', escapeHtml(comparatorReplayText(n)), '',
          pinned ? hubAttr(n, 'integration:comparator') : ''));
      } else {
        rows.push(checkHtml('none', 'Comparator', 'Nothing to replay until Lean states it exactly.'));
      }
      // Palomar: a prepared corpus; nothing has been submitted.
      if (n.palomar_status === 'prepared') {
        rows.push(checkHtml('ready', 'Palomar', 'It is in the corpus prepared for Palomar. Nothing has been submitted.', '',
          pinned ? hubAttr(n, 'integration:palomar') : ''));
      } else if (n.palomar_status === 'pending') {
        rows.push(checkHtml('none', 'Palomar', 'It joins the prepared corpus once Comparator has replayed it.'));
      } else {
        rows.push(checkHtml('none', 'Palomar', 'It is not in the prepared corpus.'));
      }
      var html = '<h3 class="universe-inspector__sub">How it is checked</h3><ol class="universe-checks">' + rows.join('') + '</ol>';
      if (more && more.record) {
        html += '<p class="universe-check__record">' + extLink(more.record, 'The evidence record for this result', 'universe-go universe-go--small') + '</p>';
      }
      if (pinned && !detail && href && !detailFailed[href]) {
        html += '<p class="universe-inspector__hint">Loading the Lean statements and Comparator files…</p>';
      }
      return html + after;
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
            '<span class="universe-goto__label">' + escapeHtml(m.label) + '</span>' +
            '<span class="universe-goto__rel">' + escapeHtml(KIND_LABEL[m.kind] || m.kind) + '</span></button></li>';
        }).join('') + '</ul>';
    }

    /* The step bar carries a small copy of the map's scale for this paper:
       a tick per result (every fifth or tenth when they crowd, as on the
       map), every tenth longer, and a cursor on this result, so the card's
       "Result 17 of 18" and the map's cursor read as the same mark. */
    function stepScaleHtml(at, count) {
      var W = 96, H = 7, pitch = W / count, every = 50, path = '';
      [10, 5, 1].forEach(function (e) { if (pitch * e >= 2.5) every = e; });
      for (var j = 0; j < count; j++) {
        var c = j + 1;
        if (c % every) continue;
        var tall = c % 50 === 0 ? H : c % 10 === 0 ? 5 : c % 5 === 0 ? 3.5 : 2.5;
        // A one-pixel stroke centred on a half pixel lies on whole pixels.
        path += 'M' + (Math.floor((j + 0.5) * pitch) + 0.5) + ' ' + (H - tall) + 'V' + H;
      }
      // The cursor, two pixels wide, centres on a whole pixel.
      var x = Math.round((at + 0.5) * pitch);
      return '<svg class="universe-step__scale" viewBox="0 0 ' + W + ' ' + H + '" width="' + W + '" height="' + H +
        '" aria-hidden="true" focusable="false"><path class="universe-step__ticks" d="' + path + '"/>' +
        '<path class="universe-step__knock" d="M' + x + ' 0V' + H + '"/>' +
        '<path class="universe-step__cursor" d="M' + x + ' 0V' + H + '"/></svg>';
    }

    function proofHtml(n) {
      if (n.proof_status !== 'ordinary_proof') return '';
      return '<div class="universe-proof"><p class="universe-inspector__meta">' +
        '<span class="universe-chip">' + glyphHtml('ordinary_proof') + 'Ordinary proof in the paper</span></p>' +
        '<p class="universe-inspector__note">' + escapeHtml(n.proof_note || '') + '</p></div>';
    }

    /* A kept result reads as a page (7 October 2026): one running head
       (its problem), one folio line (the way through its paper, and the
       way back), then its title, where it is stated and how far it is
       checked in one line, and its statement, the largest uninterrupted
       thing in the panel. The preview keeps its kind and its Preview tag. */
    function resultCardHtml(i, pinned) {
      var n = nodes[i];
      var lab = splitLabel(n.label);
      var ex = excerptOf(i);
      var problem = n.sector && problemIndex[n.sector] !== undefined;
      var seq = paperSequence[n.paperId];
      var step = '';
      if (pinned && seq && seq.length > 1 && n.seq != null) {
        // Walk the paper: the previous and next results in the order it
        // states them (the arrow keys do the same).
        step = '<div class="universe-step" role="group" aria-label="Step through this paper’s results">' +
          '<button type="button" class="universe-step__btn" data-universe-step="-1"' +
          (adjacentStatement(n, -1) < 0 ? ' disabled' : '') + '><span aria-hidden="true">←</span> Previous</button>' +
          '<span class="universe-step__at">Result ' + (n.seq + 1) + ' of ' + seq.length +
          stepScaleHtml(n.seq, seq.length) + '</span>' +
          '<button type="button" class="universe-step__btn" data-universe-step="1"' +
          (adjacentStatement(n, 1) < 0 ? ' disabled' : '') + '>Next <span aria-hidden="true">→</span></button>' +
          '</div>';
      }
      var head;
      if (pinned) {
        // The kind is said by the line under the title ("Lemma 2.7 in the
        // long paper"); the head carries the folio and the way back.
        head = cardHeadHtml(step || '<span class="universe-folio__room"></span>').replace(
          'universe-inspector__head"', 'universe-inspector__head universe-folio"');
      } else {
        head = previewHeadHtml('<p class="universe-inspector__kind">' + dotHtml(n.kind) + 'Paper result</p>');
      }
      var status = n.tier ? '<span class="universe-chip universe-chip--' + escapeHtml(n.tier) + '">' +
        glyphHtml(n.tier) + escapeHtml(capitalFirst(EVIDENCE_TEXT[n.tier] || n.tier)) + '</span>' : '';
      // Once a result is chosen its problem shrinks to one line above it,
      // the way back up to the problem's own card.
      var parts = [problem ? contextLineHtml(n.sector) : '', head,
        '<h2 class="universe-inspector__title">' + capitalFirst(ex && ex.name ? ex.name : escapeHtml(lab.name || lab.number)) + '</h2>',
        '<p class="universe-result__where"><span class="universe-result__place"' + (pinned ? referAttr(i, paperOf(i)) : '') + '>' +
          (lab.name ? '<b>' + escapeHtml(lab.number) + '</b> in ' : 'In ') + roleName(n) + '</span>' + status + '</p>'];
      parts.push(proofHtml(n));
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
      parts.push(stepBackHtml());
      return parts.join('');
    }
    /* Where going back leads, said on every pinned card: the level the
       reader came down from by name ("go back to #257", "go back to the
       long record on #257"), the whole map, or simply closing the card. The
       card's head button does what Esc does, and says Back when there is a
       level to go back to. */
    function backTarget() {
      var last = trail.length ? trail[trail.length - 1] : null;
      if (!last || last.at !== selected) return { up: -1, moves: false, fitted: false };
      return { up: trail.length > 1 ? trail[trail.length - 2].at : -1,
               moves: !!last.before, fitted: !!(last.before && last.before.fitted) };
    }
    // A level's name, as the hint and the Back button say it.
    function placeName(i) {
      var n = nodes[i];
      if (!n) return 'the map';
      var problem = n.sector && problemIndex[n.sector] !== undefined ? nodes[problemIndex[n.sector]].shortLabel : null;
      if (n.kind === 'problem') return n.shortLabel;
      if (n.kind === 'paper') {
        var run = paperSequence[String(n.id).replace(/^paper:/, '')];
        var side = run && nodes[run[0]] ? nodes[run[0]].side : null;
        return (ROLE_NAME[side] || 'the paper') + (problem ? ' on ' + problem : '');
      }
      return clip(n.shortLabel, 40);
    }
    /* In the explorer a card at the top of its trail goes back to the view
       it was opened from, and its button names that view ("← Index"), so
       the way back never reads as a bare glyph or a vague Close. */
    function cardHeadHtml(head) {
      var back = backTarget();
      var up = back.up >= 0;
      var home = !up && explorerRoot ? viewName(panelView) : null;
      return '<div class="universe-inspector__head">' + head +
        '<button type="button" class="universe-inspector__clear" data-universe-clear aria-label="' +
        escapeHtml(up ? 'Back to ' + placeName(back.up) + ' (Esc)' : home ? 'Back to ' + home.long + ' (Esc)' : 'Close this card (Esc)') + '">' +
        (up ? '<span aria-hidden="true">←</span> Back' : home ? '<span aria-hidden="true">←</span> ' + escapeHtml(home.short) : 'Close') + '</button></div>';
    }
    /* A card the pointer is only resting on says so where a kept card has
       its Back or Close: the reader sees at a glance whether the panel is
       holding a choice or showing what is under the pointer (6 October
       2026). Only the explorer's preview layer shows such a card. */
    function previewHeadHtml(head) {
      if (!previewBox) return head;
      return '<div class="universe-inspector__head universe-inspector__head--preview">' + head +
        '<span class="universe-preview__tag">Preview</span></div>';
    }
    function stepBackHtml() {
      var back = backTarget(), where;
      if (back.up >= 0) where = 'go back to ' + escapeHtml(placeName(back.up));
      else if (explorerRoot && panelView !== 'problems') where = 'go back to ' + escapeHtml(viewName(panelView).long);
      else if (back.moves) where = back.fitted ? 'go back to the whole map' : 'go back to where you were';
      else where = 'close this card';
      return '<p class="universe-inspector__hint">Press <kbd>Esc</kbd> or click empty ground to ' + where + '.</p>';
    }

    // A result's problem, said in one line over its card: its number (a
    // button back to the problem's card) and its title.
    function contextLineHtml(pid) {
      var at = problemIndex[pid];
      if (at === undefined) return '';
      return '<p class="universe-context"><button type="button" class="universe-context__go" data-universe-go="' + at + '">' +
        'Erdős ' + escapeHtml(nodes[at].shortLabel) + '</button><span class="universe-context__title">' +
        escapeHtml(nodes[at].label) + '</span></p>';
    }
    // A card's first line names the kind of thing, in plain words.
    function kindLine(n) {
      if (n.id === 'integration:comparator') return 'Replay checker';
      if (n.id === 'integration:palomar') return 'Prepared corpus';
      if (n.kind === 'universe') return 'Centre of the map';
      return capitalFirst(KIND_LABEL[n.kind] || n.kind);
    }
    function cardHtml(i, pinned) {
      var n = nodes[i];
      if (n.kind === 'paper_statement') return resultCardHtml(i, pinned);
      if (n.kind === 'problem' && n.sector) return problemCardHtml(i, pinned);
      var head = '<p class="universe-inspector__kind">' + dotHtml(n.kind) +
        escapeHtml(kindLine(n)) + '</p>';
      head = pinned ? cardHeadHtml(head) : previewHeadHtml(head);
      var parts = [head,
        '<h2 class="universe-inspector__title">' + (n.kind === 'public_claim' && /\s/.test(n.label || '') ? notationHtml(n.label) : nameHtml(n.label)) + '</h2>'];
      var chips = '';
      if (n.status) {
        chips += '<span class="universe-chip">' + (n.tier ? glyphHtml(n.tier) : '') + escapeHtml(capitalFirst(n.status)) + '</span>';
      }
      if (n.disposition) chips += '<span class="universe-chip">' + escapeHtml(n.disposition) + '</span>';
      if (chips) parts.push('<p class="universe-inspector__meta">' + chips + '</p>');
      parts.push(proofHtml(n));
      var body = n.statement || n.question || null;
      var claim = n.kind === 'public_claim';
      // A claim's assertion is set as a statement, as a paper's result is.
      if (body) parts.push('<p class="universe-inspector__body' + (claim ? ' universe-claim__statement' : '') + '">' +
        (claim ? notationHtml(body) : escapeHtml(body)) + '</p>');
      if (n.boundary) {
        parts.push('<p class="universe-inspector__boundary">' + (claim ? notationHtml(n.boundary) : escapeHtml(n.boundary)) + '</p>');
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
        parts.push(stepBackHtml());
      } else {
        parts.push('<p class="universe-inspector__hint">Click to keep this card and see what it connects to; double-click to open it.</p>');
      }
      return parts.join('');
    }

    // The explorer (or the old page's panel) carries the level being read,
    // so the panel's overview-only sections step aside under a card.
    var panel = pageMode ? (explorerRoot || (stage.closest ? stage.closest('.universe-panel') : null)) : null;
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

    /* A display that sets several relations side by side, parted by the
       paper's wide spaces (\qquad: "u = …,  v = …,  gcd(u, v) = 1,"), is
       first set as an aligned stack when it is too wide for the measure
       (7 October 2026): one relation a line, in the paper's order, each on
       its relation sign, the equation's number on the first line. Every
       term and comma stays; only the wide spaces become line breaks. */
    var MATHML_NS = 'http://www.w3.org/1998/Math/MathML';
    var RELATION_SIGN = /^[=<>\u2260\u2264\u2265\u2261\u2248\u223c\u2243\u2245\u221d\u2282\u2286\u2208\u2192\u21a6\u27f9\u21d2\u21d4\u2223]$/;
    function stackRelations(el) {
      var math = el.querySelector && el.querySelector('math');
      if (!math || !document.createElementNS || el.getAttribute('data-stacked')) return false;
      var table = math.querySelector('mtable'), label = null, body;
      if (table) {
        var trs = table.querySelectorAll('mtr');
        if (trs.length !== 1 || trs[0].children.length > 2) return false;
        var cells = trs[0].children;
        body = cells[cells.length - 1];
        label = cells.length === 2 ? cells[0] : null;
      } else {
        body = math.children.length === 1 && math.children[0].localName === 'mrow' ? math.children[0] : math;
      }
      var parts = [[]];
      Array.prototype.forEach.call(body.childNodes, function (k) {
        var wide = k.localName === 'mspace' && parseFloat(k.getAttribute('width')) >= 1;
        if (wide) parts.push([]); else parts[parts.length - 1].push(k);
      });
      parts = parts.filter(function (p) { return p.some(function (k) { return k.nodeType === 1; }); });
      if (parts.length < 2) return false;
      var stack = document.createElementNS(MATHML_NS, 'mtable');
      stack.setAttribute('class', 'universe-stack');
      if (table && table.getAttribute('displaystyle')) stack.setAttribute('displaystyle', table.getAttribute('displaystyle'));
      parts.forEach(function (p, j) {
        var tr = document.createElementNS(MATHML_NS, 'mtr');
        if (label) tr.appendChild(j === 0 ? label : document.createElementNS(MATHML_NS, 'mtd'));
        var lhs = document.createElementNS(MATHML_NS, 'mtd'), rhs = document.createElementNS(MATHML_NS, 'mtd');
        var left = document.createElementNS(MATHML_NS, 'mrow'), right = document.createElementNS(MATHML_NS, 'mrow');
        lhs.setAttribute('class', 'universe-stack__lhs');
        rhs.setAttribute('class', 'universe-stack__rhs');
        var at = -1;
        for (var q = 0; q < p.length && at < 0; q++) {
          if (q > 0 && p[q].localName === 'mo' && RELATION_SIGN.test((p[q].textContent || '').trim())) at = q;
        }
        p.forEach(function (k, q) { (at > 0 && q < at ? left : right).appendChild(k); });
        lhs.appendChild(left);
        rhs.appendChild(right);
        tr.appendChild(lhs);
        tr.appendChild(rhs);
        stack.appendChild(tr);
      });
      if (table) table.parentNode.replaceChild(stack, table);
      else { while (math.firstChild) math.removeChild(math.firstChild); math.appendChild(stack); }
      // A table cell's math is laid out from its start, so each left side
      // is set flush right by the space it lacks: the signs share a line.
      var sides = Array.prototype.slice.call(stack.querySelectorAll('.universe-stack__lhs > mrow'));
      var widths = sides.map(function (m) { return m.getBoundingClientRect ? m.getBoundingClientRect().width : 0; });
      var widest = Math.max.apply(null, widths.concat([0]));
      sides.forEach(function (m, j) {
        if (!(widest - widths[j] > 0.5)) return;
        var pad = document.createElementNS(MATHML_NS, 'mspace');
        pad.setAttribute('width', (widest - widths[j]).toFixed(1) + 'px');
        m.parentNode.insertBefore(pad, m);
      });
      el.setAttribute('data-stacked', '1');
      return true;
    }
    /* A displayed formula wider than the panel's measure is first stacked
       where it is a run of relations, then set a little smaller to fit (to
       three quarters of its size at most); one wider still scrolls sideways
       in its own line, never cut, with a fade at the edge it continues past. */
    function fitDisplays(root) {
      if (!root || !root.querySelectorAll) return;
      Array.prototype.forEach.call(root.querySelectorAll('.math-display'), function (el) {
        el.style.fontSize = '';
        var room = el.clientWidth, need = el.scrollWidth;
        if (room > 0 && need > room + 1 && stackRelations(el)) need = el.scrollWidth;
        if (room > 0 && need > room + 1) el.style.fontSize = Math.max(0.75, Math.floor(room / need * 100) / 100) + 'em';
        if (el.classList) el.classList.toggle('is-wide', room > 0 && el.scrollWidth > el.clientWidth + 1);
      });
    }
    function levelOf(i) {
      if (i < 0 || !nodes[i]) return 'overview';
      return nodes[i].kind === 'problem' ? 'problem' : nodes[i].kind === 'paper_statement' ? 'result' : 'object';
    }
    /* The panel's body scrolls. A new card opens at its top; going back to
       the overview returns to where the reader had scrolled it. */
    var shownAt = -1, lastInspectorHtml = null;
    function renderInspector() {
      if (!inspector) return;
      // Leaving a view for a card: remember where the reader was in it (its
      // focus and query) before the card's words replace anything.
      if (selected >= 0 && shownAt < 0) noteReturn();
      var level = levelOf(selected);
      if (panel) {
        panel.classList.toggle('is-reading', selected >= 0);
        if (panel.setAttribute) panel.setAttribute('data-universe-level', level);
      }
      if (!previewBox && hover >= 0 && hover !== selected && selected < 0) {
        // The old placard page (no preview layer): a hover previews in the
        // rail. A pinned card stays put: the pointer crossing other dots on
        // its way to the rail names them on the field and leaves it alone.
        lastInspectorHtml = null;
        inspector.innerHTML = cardHtml(hover, false);
        inspector.classList.add('is-preview');
        return;
      }
      var html = selected >= 0 ? cardHtml(selected, true) : overviewHtml();
      inspector.classList.remove('is-preview');
      // The same words are never set again: a refresh that changes nothing
      // keeps the reader's place, focus and selection of text.
      if (html !== lastInspectorHtml) {
        // A new card arrives (not a card refreshed as its words load).
        var arriving = lastInspectorHtml !== null && selected !== shownAt;
        inspector.innerHTML = html;
        lastInspectorHtml = html;
        fitDisplays(inspector);
        if (arriving) playArrival(inspector, stepping);
      }
      // Each view keeps its own place: a card opens at its top, and going
      // back returns the view the reader left to where they had scrolled it.
      var leaving = shownAt;
      if (scrollBox && selected !== shownAt && shownAt < 0) viewScroll[viewKey()] = scrollBox.scrollTop;
      syncPanelView();
      if (scrollBox && selected !== shownAt) scrollBox.scrollTop = selected < 0 ? (viewScroll[viewKey()] || 0) : 0;
      shownAt = selected;
      if (selected < 0 && leaving >= 0) restoreReturn();
      if (selected < 0 && panelView === 'about') refreshAbout();
      refreshPreview();
    }

    /* What the pointer is on, previewed in a layer over the panel's body
       (5 October 2026). The panel underneath is never redrawn for a hover,
       so its place and its scroll stay exactly where the reader left them,
       and letting go shows it again unchanged. A preview shows at rest, and
       over a chosen problem or paper (the levels a reader chooses from), a
       moment after the pointer settles so crossing the map to the panel
       never flickers; a chosen result is being read and stays put. Hover
       from the panel's own rows only lights the map. */
    var hoverFromMap = false, previewAt = -1, previewTimer = 0, PREVIEW_DWELL = 140;
    function previewTarget() {
      if (!hoverFromMap || hover < 0 || hover === selected) return -1;
      if (selected >= 0 && nodes[selected].kind !== 'problem' && nodes[selected].kind !== 'paper') return -1;
      return hover;
    }
    function showPreview(i) {
      previewAt = i;
      if (i < 0) {
        previewBox.hidden = true;
        previewBox.innerHTML = '';
        if (panel) panel.classList.remove('is-previewing');
        return;
      }
      var opening = previewBox.hidden;
      previewBox.innerHTML = cardHtml(i, false);
      if (scrollBox) previewBox.style.top = scrollBox.offsetTop + 'px';
      previewBox.hidden = false;
      fitDisplays(previewBox);
      if (panel) panel.classList.add('is-previewing');
      // The layer's ground covers the panel at once; its words rise in.
      if (opening) playArrival(previewBox, false, true);
    }
    /* A card's arrival (6 October 2026): a chosen card's parts rise into
       place one after another, a few hundredths of a second apart, so the
       panel reads as turning to the new card rather than flashing; a step
       to the next result in a paper only lifts the card from a faint
       ghost, so walking a paper stays quick. Under reduced motion, or
       without Web Animations, the card is simply there. */
    var stepping = false;
    function playArrival(box, turning, quick) {
      if (!box || reduceMotion || typeof box.animate !== 'function') return;
      if (turning) {
        box.animate([{ opacity: 0.35 }, { opacity: 1 }], { duration: 150, easing: 'ease-out' });
        return;
      }
      var kids = box.children || [];
      for (var k = 0; k < kids.length && k < 12; k++) {
        if (typeof kids[k].animate !== 'function') continue;
        kids[k].animate([{ opacity: 0, transform: 'translateY(' + (quick ? 3 : 7) + 'px)' },
                         { opacity: 1, transform: 'none' }],
          { duration: quick ? 170 : 300, delay: Math.min(k, 6) * (quick ? 14 : 32),
            easing: 'cubic-bezier(0.2, 0.7, 0.2, 1)', fill: 'backwards' });
      }
    }
    function refreshPreview(force) {
      if (!previewBox) return;
      var want = previewTarget();
      if (want === previewAt && !force) return;
      clearTimeout(previewTimer);
      if (want < 0 || previewAt >= 0 || selected < 0) { showPreview(want); return; }
      previewTimer = setTimeout(function () {
        if (previewTarget() === want) showPreview(want);
      }, PREVIEW_DWELL);
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
    /* Speculation rules are an inline script. The landing's policy admits
       only the scripts it serves (script-src 'self'), so there an inline
       rule set is refused and the refusal logged on every pin; where the
       page's policy says so, the paper is prefetched only. */

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
      // Do not prerender the target while the reader is still using the map.
      if (!pageMode) {
        var link = document.createElement('link');
        link.rel = 'prefetch';
        link.href = href;
        warmNodes.push(link);
      }
      warmNodes.forEach(function (node) { document.head.appendChild(node); });
    }

    /* The way the reader came down the map: each pin a click on the map
       made one level below the last (a problem, a paper of it, a result of
       that paper), with the view it replaced when it moved the camera. A
       pin from anywhere else (a card's link, the search, an address)
       starts the trail again. Going back retraces it exactly. */
    var trail = [];
    function viewNow() { return { k: view.k, tx: view.tx, ty: view.ty, fitted: viewIsFitted }; }
    // Whether one object holds another a level down: a problem its sector's
    // papers, claims and results; a paper its results.
    function holds(parent, child) {
      var p = nodes[parent], c = nodes[child];
      if (!p || !c || parent === child) return false;
      if (p.kind === 'problem') return !!c.sector && sectorProblems(c).indexOf(p.sector) !== -1;
      if (p.kind === 'paper') return c.kind === 'paper_statement' && 'paper:' + c.paperId === p.id;
      return false;
    }
    function pin(i, center, keepTrail) {
      if (!keepTrail) trail = i >= 0 ? [{ at: i, before: center ? viewNow() : null }] : [];
      // Focus in the card, or on a row of a view the card covers, follows
      // the reader: to the card's way back, or back to where they were.
      var restoreFocus = (inspector && inspector.contains(document.activeElement)) ||
        (restBox && restBox.contains && restBox.contains(document.activeElement));
      if (i >= 0 && nodes[i] && nodes[i].kind === 'problem') lastProblemAt = i;
      if (i !== selected) { quoteAt = -1; referEl = null; referAt = referShown = -1; referMix = 0; }
      selected = i;
      hover = -1;
      canvas.classList.remove('is-over');
      if (i >= 0) pendingId = null;
      warmPaper(i);
      renderInspector();
      if (restoreFocus) {
        var nextFocus = (i < 0 && returnFocusEl()) || inspector.querySelector('[data-universe-clear]') || searchIn;
        if (nextFocus) nextFocus.focus({ preventScroll: true });
      }
      updateHash();
      if (center && i >= 0) centerOn(i);
      draw();
      // Every selection route brings its reading forward on a phone: a
      // direct URL, search or stepper chooses the same object as a canvas tap.
      if (i >= 0 && explorerRoot) explorerRoot.dispatchEvent(new CustomEvent('explorer:selected', { bubbles: true, detail: { id: nodes[i].id } }));
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

    /* One level back up the way the reader came: a result to the paper or
       the problem it was opened from, a paper to its problem, a problem to
       the whole field, each with its card and the view it had. With nothing
       pinned, a closer view returns to the whole field. */
    function stepBack() {
      var last = trail.length ? trail[trail.length - 1] : null;
      if (last && last.at === selected) {
        trail.pop();
        pin(trail.length ? trail[trail.length - 1].at : -1, false, true);
        if (last.before) restoreView(last.before);
        return;
      }
      trail = [];
      if (selected >= 0) { pin(-1, false, true); return; }
      if (!viewIsFitted) fitAnimated();
    }
    function restoreView(v) {
      if (v.fitted) fitAnimated();
      else cameraTo({ k: v.k, tx: v.tx, ty: v.ty }, false);
    }

    /* Walking a paper keeps the view the reader chose: the camera moves
       only when the next result would leave it, sliding across at the same
       scale, and the step remembers the view it left. */
    function adjacentStatement(n, dir) {
      var seq = paperSequence[n.paperId] || [];
      for (var at = n.seq + dir; at >= 0 && at < seq.length; at += dir) {
        if (visible(nodes[seq[at]])) return seq[at];
      }
      return -1;
    }
    function stepStatement(dir) {
      if (selected < 0 || !nodes[selected]) return;
      var n = nodes[selected];
      var seq = paperSequence[n.paperId];
      if (!seq || n.seq == null) return;
      var next = adjacentStatement(n, dir);
      if (next < 0) return;
      var last = trail.length ? trail[trail.length - 1] : null;
      if (last && last.at === selected) last.at = next;
      else trail = [{ at: next, before: null }];
      stepping = true;
      try { pin(next, false, true); } finally { stepping = false; }
      keepInView(next, trail[trail.length - 1]);
    }
    function keepInView(i, step) {
      var n = nodes[i], w = canvas.clientWidth, h = canvas.clientHeight, inset = 56;
      var x = n.x * view.k + view.tx, y = n.y * view.k + view.ty;
      if (x >= inset && x <= w - inset && y >= inset && y <= h - inset) return;
      if (step && !step.before) step.before = viewNow();
      cameraTo({ k: view.k, tx: w / 2 - n.x * view.k, ty: h / 2 - n.y * view.k }, false);
    }

    function resolvePending() {
      if (!pendingId) return;
      if (byId[pendingId] !== undefined) {
        var at = byId[pendingId], n = nodes[at];
        // An address for a result (the landing's "In the map", a shared
        // link) opens in the explorer as if the reader had come down to it:
        // its problem's sector framed, so it is seen among its paper's
        // results, and Back goes up to the problem, then the whole map.
        if (inExplorer && n.kind === 'paper_statement' && n.sector && problemIndex[n.sector] !== undefined) {
          var up = problemIndex[n.sector];
          trail = [{ at: up, before: viewNow() }, { at: at, before: null }];
          pin(at, false, true);
          centerOn(up);
          return;
        }
        pin(at, true);
        return;
      }
      // A shared link to a full-corpus object must open its card on first visit.
      if (!fullLoaded) loadFull();
    }

    /* ---- Caption (landing teaser) ------------------------------------ */

    /* The caption under the teaser says what the pointer is on in a short
       plain sentence, two lines at most, so it never grows over the drawing:
       "Theorem 6.32 on #257, replayed by Comparator", "#249: The binary
       totient series", "Comparator: 616 of 689 replayed". */
    var CAPTION_EVIDENCE = {
      replayed: 'replayed by Comparator',
      lean: 'exact in Lean, replay not recorded',
      modulo: 'in Lean under named inputs',
      none: 'not yet stated in Lean'
    };
    function captionText(n) {
      var problem = n.sector && problemIndex[n.sector] !== undefined ? nodes[problemIndex[n.sector]].shortLabel : null;
      if (n.kind === 'paper_statement') {
        return clip(splitLabel(n.label).number, 28) + (problem ? ' on ' + problem : '') +
          (CAPTION_EVIDENCE[n.tier] ? ', ' + CAPTION_EVIDENCE[n.tier] : '');
      }
      if (n.kind === 'problem') return n.shortLabel + ': ' + clip(n.label, 44);
      if (n.kind === 'integration_surface') return n.label + (n.sub ? ': ' + n.sub : '');
      return clip(n.label, 52);
    }
    /* ---- Key (landing teaser) -----------------------------------------
       At rest the caption slot under the drawing stood empty, and the
       marks were explained only after a hover. It now holds one quiet line
       of the map's own marks: Comparator's colour for a replayed result,
       the pip of one whose replay is queued, a checked claim, the open ring
       of a result with no Lean statement. Every mark, in that order, each
       kept whole: on a narrow card the line wraps and the drawing yields
       the room (style.css, .home-universe__caption), since a dot the key
       does not name is a dot the reader cannot read. It steps out while the
       caption names what the pointer is on, or the column reads it, and
       comes back a moment after both are done (style.css, .universe-key). */
    var KEY_MARKS = [
      ['replayed', 'Replayed by Comparator'],
      ['lean', 'Replay queued'],
      ['claim', 'Checked claim'],
      ['none', 'No Lean statement']
    ];
    var key = null;
    function buildKey() {
      if (pageMode || key || !caption || !caption.parentNode || typeof document.createElement !== 'function') return;
      var row = caption.parentNode;
      if (!row.classList || !row.classList.contains('home-universe__caption') || typeof row.insertBefore !== 'function') return;
      var slot = document.createElement('div');
      slot.className = 'universe-captionslot';
      row.insertBefore(slot, caption);
      slot.appendChild(caption);
      key = document.createElement('ul');
      key.className = 'universe-key';
      key.setAttribute('aria-label', 'Key to the marks');
      key.innerHTML = KEY_MARKS.map(function (m) {
        return '<li class="universe-key__item"><span class="universe-key__mark universe-key__mark--' + m[0] +
          '" aria-hidden="true"></span>' + escapeHtml(m[1]) + '</li>';
      }).join('');
      slot.appendChild(key);
    }
    function showCaption(i) {
      if (key) key.classList.toggle('is-out', i >= 0);
      if (!caption) return;
      if (i < 0) {
        // The words go with the class: the landing's stylesheet does not
        // hide an unshown caption, and a stale name would linger there.
        caption.classList.remove('is-shown');
        caption.textContent = '';
        return;
      }
      var n = nodes[i];
      var text = captionText(n);
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
        comparator_status: n.comparator_status || null,
        comparator_queued_at: n.comparator_queued_at || null,
        status: n.status || null, statement: n.statement || null,
        side: n.side || null, paperId: n.paperId || null, paperTitle: n.paperTitle || null,
        href: target && !target.external ? target.href : null,
        // The Lean source line on GitHub: the first declaration's, else the
        // object's own.
        github: (decls[0] && decls[0].href) || (n.lean && n.lean.length ? n.lean[0].href : null) ||
          n.source_github || null,
        // The TeX line the paper states it at, on GitHub.
        tex: n.tex && statementMeta && statementMeta.tex_source_base ? statementMeta.tex_source_base + n.tex : null,
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
      syncExpandLinks();
      warmPaper(i);
      draw();
      if (companionApi) {
        stage.dispatchEvent(new CustomEvent('universe:select', { detail: i >= 0 ? companionSummary(i) : null }));
        // Let go under the pointer, the card reads what the pointer is on.
        if (i < 0 && hover >= 0) announce(hover);
      }
    }

    /* The landing's way into the full map (the atlas bar's "Expand map",
       data-universe-expand, and the card's own link where it has one) keeps
       the teaser's selection: expanding opens the explorer on the result
       the reader kept, or on the whole map when nothing is kept. */
    function syncExpandLinks() {
      if (pageMode || !document.querySelectorAll) return;
      var href = route('universe.html' + (selected >= 0 && nodes[selected] ?
        '#o=' + encodeURIComponent(nodes[selected].id) : ''));
      Array.prototype.forEach.call(document.querySelectorAll('a[data-universe-expand], .home-universe__open'), function (a) {
        if (a.getAttribute('href') !== href) a.setAttribute('href', href);
      });
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
      // The column closing lets the field go on its own beat.
      if (i < 0) letGoNow = true;
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
        dataUrl: route(spec.data), tallies: companionTallies(), light: lightProblem, notation: notationHtml,
        restoreSelection: function (id, sector) {
          var i = typeof id === 'string' && Object.prototype.hasOwnProperty.call(byId, id) ? byId[id] : -1;
          var n = typeof i === 'number' && i >= 0 ? nodes[i] : null;
          if (!n || n.sector !== sector || !visible(n) || selected >= 0) return false;
          pinInTeaser(i);
          return true;
        },
        // The column lets a pin go (Escape, leaving the band, another problem).
        release: function () { if (selected >= 0) { selected = -1; letGoNow = true; syncExpandLinks(); draw(); } },
        // The column's own data has arrived: a plate it now reads in full
        // gives only the paper's number, so the plates are set again.
        redraw: function () { pinnedPlate = null; draw(); }
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
          return { name: d[0], file: file, line: d[2] || null,
                   href: statementMeta.lean_source_base + file + (d[2] ? '#L' + d[2] : '') };
        });
      }
      return (n.declarations || []).map(function (d) {
        return { name: d.name, file: d.file || '', href: d.href, line: d.line || null };
      });
    }

    var companionSpec = null;
    function ingest(data) {
      var keepId = selected >= 0 && nodes[selected] ? nodes[selected].id : null;
      var keepView = nodes.length > 0;
      if (data.statements) statementMeta = data.statements;
      // The landing names the counts from this map edition, not symbolic
      // placeholders or a separately maintained census. Missing metadata
      // keeps the plain fallback; a recorded zero is still a real count.
      var census = statementMeta && statementMeta.summary;
      var replayed = census && census.comparator && census.comparator.compared;
      if (replaySummary && census && typeof census.statements === 'number' && typeof replayed === 'number') {
        replaySummary.innerHTML = '<span class="home-universe__specimen">' + fmtCount(replayed) + ' of ' +
          fmtCount(census.statements) + '</span> paper results replayed by Comparator.';
      }
      if (data.companion) companionSpec = data.companion;
      if (data.bands) bands = data.bands;
      if (data.excerpts) {
        excerptRoutes = {};
        data.excerpts.forEach(function (pair) { excerptRoutes[pair[0]] = pair[1]; });
      }
      if (Array.isArray(data.excerpt_batches)) {
        excerptBatchRoutes = {}; excerptBatchIds = {};
        data.excerpt_batches.forEach(function (batch) {
          if (!Array.isArray(batch)) return;
          var pid = batch[0], href = batch[1], ids = batch[2];
          if (typeof pid !== 'string' || !/^[a-z0-9-]+$/.test(pid) || typeof href !== 'string' ||
              href.indexOf('assets/excerpts/' + pid + '--batch-') !== 0 ||
              !/^assets\/excerpts\/[a-z0-9-]+--batch-[a-f0-9]{12}\.json$/.test(href) || !Array.isArray(ids) || !ids.length ||
              !ids.every(function (id) { return typeof id === 'string' && id.indexOf('statement:' + pid + '#') === 0; })) return;
          var expected = {};
          ids.forEach(function (id) { expected[id] = true; excerptBatchRoutes[id] = href; });
          excerptBatchIds[href] = expected;
        });
      }
      if (data.details) {
        detailRoutes = {};
        data.details.forEach(function (pair) { detailRoutes[pair[0]] = pair[1]; });
      }
      visGen++;
      nodes = data.nodes.map(function (n) {
        var row = {
          id: n.id, kind: n.kind, label: plainText(n.label),
          shortLabel: plainText(n.short || n.label),
          status: n.status || null, statement: n.statement || null,
          proof_status: n.proof_status || null, proof_note: n.proof_note || null,
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
          row.subject || '', row.statement || '', row.paperLabel || '', row.side || '',
          row.proof_status === 'ordinary_proof' ? 'ordinary proof' : '',
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
      // The scale round the results ring reads the same sequences.
      buildScale();
      pinnedPlate = null;
      // Link shared formal support across short and long papers. A matching
      // label or name alone does not establish identity or equivalence.
      var twinSlots = {};
      for (i = 0; i < nodes.length; i++) {
        var tn = nodes[i];
        if (tn.kind !== 'paper_statement') continue;
        tn.twins = [];
        var slots = [];
        (tn.decls || []).forEach(function (d) {
          if (d.file && d.name) slots.push(JSON.stringify([tn.sector, d.file, d.name]));
        });
        for (var si = 0; si < slots.length; si++) {
          (twinSlots[slots[si]] = twinSlots[slots[si]] || []).push(i);
        }
      }
      Object.keys(twinSlots).forEach(function (slot) {
        var list = twinSlots[slot];
        if (list.length < 2) return;
        var via = 'a Lean declaration both cite';
        list.forEach(function (a) {
          list.forEach(function (b) {
            if (a === b || !nodes[a].side || !nodes[b].side || nodes[a].side === nodes[b].side) return;
            var have = nodes[a].twins.filter(function (t) { return t.at === b; })[0];
            if (!have) nodes[a].twins.push({ at: b, via: via });
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
      // Every node's fields are in place: visibility is asked afresh.
      visGen++;
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

    /* ---- The panel views (6 October 2026) ----------------------------
       The panel is a guide to the reader's current question, one view at a
       time over the same markup (without scripts every view stands in
       order). Two destinations are peers, the problems and the index; two
       tools open from beside them, the map filters and how to read the map
       with its sources; a kept object reads over whichever view was open,
       and its way back returns there, to the same place, query and focus.
       Every view change pushes where the reader was, so each labelled Back
       retraces the way they came. The explorer carries the view shown as
       data-universe-view (and the index's mode as data-universe-index), so
       CSS decides what stands; the head names the place being read. */
    var V;
    function dom() {
      if (V) return V;
      var find = function (sel) { return pageMode ? document.querySelector(sel) : null; };
      var all = function (sel) {
        return pageMode && document.querySelectorAll ? Array.prototype.slice.call(document.querySelectorAll(sel) || []) : [];
      };
      V = {
        panel: explorerRoot && explorerRoot.querySelector ? explorerRoot.querySelector('.explorer__panel') : null,
        where: find('[data-universe-where]'),
        none: find('[data-universe-none]'),
        searchLabel: find('[data-universe-search-label]'),
        index: find('[data-universe-pane="index"]'),
        indexStatus: find('[data-universe-index-status]'),
        indexScopeOut: find('[data-universe-index-scope]'),
        filtered: find('[data-universe-filtered]'),
        filteredText: find('[data-universe-filtered-text]'),
        badge: find('[data-universe-filter-badge]'),
        captions: find('[data-universe-captions]'),
        evidence: find('[data-universe-evidence]'),
        goButtons: all('[data-universe-view-go]'),
        backButtons: all('[data-universe-view-back]'),
        resets: all('[data-universe-filters-reset]'),
        cats: all('[data-universe-cat]'),
        catNames: {}
      };
      all('[data-universe-index-go]').forEach(function (a) {
        var name = a.querySelector ? a.querySelector('.universe-cats__name') : null;
        V.catNames[a.getAttribute('data-universe-index-go')] = name ? name.textContent : a.getAttribute('data-universe-index-go');
      });
      all('[data-universe-cat-count], [data-universe-cats-count]').forEach(function (el) {
        el.setAttribute('data-default', el.textContent);
      });
      return V;
    }
    var panelEl;
    function viewNames() {
      return {
        problems: { short: 'Problems', long: 'the problems' },
        index: { short: 'Index', long: 'the index' },
        filters: { short: 'Map filters', long: 'the map filters' },
        about: { short: 'How to read', long: 'how to read the map' }
      };
    }
    function viewName(v) {
      if (v === 'index' && indexCat && dom().catNames[indexCat]) {
        return { short: dom().catNames[indexCat], long: 'the index: ' + dom().catNames[indexCat] };
      }
      return viewNames()[v] || viewNames().problems;
    }
    function indexMode() {
      if (indexCat) return 'cat';
      return query.length >= 2 || indexScope ? 'all' : 'cats';
    }
    function viewKey() {
      return panelView === 'index' ? 'index:' + indexCat + ':' + indexScope : panelView;
    }
    function problemShort(pid) {
      var at = problemIndex[pid];
      return at === undefined ? pid : nodes[at].shortLabel;
    }

    // What the head says at depth: the place being read, as a short trail.
    function whereParts(shown) {
      if (shown === 'problems') return [];
      if (shown === 'object') {
        var n = nodes[selected];
        if (!n) return [];
        if (n.kind === 'problem') return [n.shortLabel + ' ' + n.label];
        var up = n.sector && problemIndex[n.sector] !== undefined ? nodes[problemIndex[n.sector]].shortLabel : null;
        if (n.kind === 'paper_statement') return (up ? [up] : []).concat([clip(n.label, 64)]);
        return (up ? [up] : []).concat([capitalFirst(kindLine(n)) + ': ' + clip(n.label, 56)]);
      }
      if (shown === 'index') {
        var parts = ['Index'];
        if (indexCat && dom().catNames[indexCat]) parts.push(dom().catNames[indexCat]);
        if (indexScope) parts.push(problemShort(indexScope));
        return parts;
      }
      if (shown === 'filters') return ['Map filters'];
      if (shown === 'about') return ['How to read the map'];
      return [];
    }
    function backLabel() {
      var s = viewStack.length ? viewStack[viewStack.length - 1] : null;
      if (s && s.at >= 0 && nodes[s.at]) return { short: placeName(s.at), long: placeName(s.at) };
      if (s) {
        var keep = { cat: indexCat };
        indexCat = s.cat || '';
        var name = viewName(s.view);
        indexCat = keep.cat;
        return name;
      }
      if (panelView === 'index' && (indexCat || indexScope)) return { short: 'All categories', long: 'the index' };
      return viewNames().problems;
    }

    function syncPanelView() {
      if (!explorerRoot || !explorerRoot.setAttribute) return;
      var d = dom();
      var shown = selected >= 0 ? 'object' : panelView;
      explorerRoot.setAttribute('data-universe-view', shown);
      explorerRoot.setAttribute('data-universe-index', panelView === 'index' ? indexMode() : '');
      if (explorerRoot.classList) explorerRoot.classList.toggle('is-deep', shown !== 'problems');
      d.goButtons.forEach(function (btn) {
        if (!btn.closest || !btn.closest('[data-universe-nav]')) return;
        btn.setAttribute('aria-pressed', String(selected < 0 && btn.getAttribute('data-universe-view-go') === panelView));
      });
      if (d.where) {
        var parts = whereParts(shown);
        d.where.hidden = !parts.length;
        d.where.innerHTML = parts.map(function (p) {
          return '<span class="universe-where__seg">' + escapeHtml(p) + '</span>';
        }).join('<span class="universe-where__sep" aria-hidden="true">/</span>');
      }
      var back = backLabel();
      d.backButtons.forEach(function (btn) {
        var visibleBack = !(panelView === 'index' && !indexCat && !indexScope && !viewStack.length);
        btn.hidden = !visibleBack;
        btn.innerHTML = '<span aria-hidden="true">←</span> ' + escapeHtml(back.short);
        btn.setAttribute('aria-label', 'Back to ' + back.long + ' (Esc)');
      });
      if (searchIn) {
        var inIndex = panelView === 'index' && selected < 0;
        searchIn.setAttribute('placeholder', inIndex ? 'Find in the index\u2026' : 'Find a theorem or a Lean declaration\u2026');
        if (d.searchLabel) d.searchLabel.textContent = inIndex ? 'Find in the index' : 'Find a theorem, a problem or a Lean declaration on the map';
      }
      renderFilterSummary();
    }

    function focusQuiet(el) {
      if (!el || typeof el.focus !== 'function') return;
      try { el.focus({ preventScroll: true }); } catch (err) { el.focus(); }
    }
    // Open a view. A destination leaves a kept card; opts.push records where
    // the reader was, so the view's Back returns there.
    function setView(v, opts) {
      opts = opts || {};
      if (!viewNames()[v]) return;
      if (opts.push) viewStack.push(opts.push === true ? stateNow() : opts.push);
      if (opts.reset) viewStack = [];
      if (selected >= 0) { trail = []; pin(-1, false, true); }
      if (scrollBox) viewScroll[viewKey()] = scrollBox.scrollTop;
      panelView = v;
      if (v === 'index') { indexCat = opts.cat || ''; indexScope = opts.scope || ''; }
      if (opts.query != null && searchIn && searchIn.value !== opts.query) {
        searchIn.value = opts.query;
        query = normalizeSearchText(opts.query);
        countMatches();
        draw();
      }
      closeResults();
      if (v === 'index') refreshIndex();
      if (v === 'about') refreshAbout();
      renderNone();
      syncPanelView();
      if (scrollBox) scrollBox.scrollTop = opts.restoreScroll ? (viewScroll[viewKey()] || 0) : 0;
      if (opts.at) {
        var target = document.getElementById(opts.at);
        if (target && scrollBox && target.getBoundingClientRect) {
          scrollBox.scrollTop += target.getBoundingClientRect().top - scrollBox.getBoundingClientRect().top - 12;
          if (opts.focus !== false) focusQuiet(target);
          return;
        }
      }
      if (opts.focusSel && returnFocusFrom(opts.focusSel)) return;
      if (opts.focus === 'heading') {
        var pane = d0('[data-universe-pane="' + v + '"]');
        var heading = null;
        if (v === 'index' && indexCat) heading = document.getElementById('universe-cat-' + indexCat + '-title');
        else if (pane && pane.querySelector) heading = pane.querySelector('h2');
        focusQuiet(heading);
      }
    }
    function d0(sel) { return pageMode ? document.querySelector(sel) : null; }
    function stateNow() {
      return { view: panelView, cat: indexCat, scope: indexScope, at: selected, trail: trail.slice(),
               query: searchIn ? searchIn.value : '', focus: focusKey(document.activeElement) };
    }
    function viewBack() {
      var s = viewStack.pop();
      if (!s) {
        if (panelView === 'index' && (indexCat || indexScope)) { setView('index', { restoreScroll: true, focus: 'heading' }); return; }
        setView('problems', { restoreScroll: true });
        return;
      }
      setView(s.view, { cat: s.cat, scope: s.scope, query: s.query, restoreScroll: true, focusSel: s.focus });
      if (s.at >= 0 && nodes[s.at]) {
        trail = s.trail && s.trail.length ? s.trail : [{ at: s.at, before: null }];
        pin(s.at, false, true);
        var back = inspector && inspector.querySelector ? inspector.querySelector('[data-universe-index-scope]') : null;
        focusQuiet(back || (inspector && inspector.querySelector ? inspector.querySelector('[data-universe-clear]') : null));
      }
    }

    // Where focus was, said so it can be found again after a redraw.
    function focusKey(el) {
      if (!el || !el.getAttribute) return null;
      if (el === searchIn) return 'search';
      var node = el.getAttribute('data-universe-node');
      if (node) return '[data-universe-node="' + node.replace(/["\\]/g, '\\$&') + '"]';
      var go = el.getAttribute('data-universe-go');
      if (go && el.classList && el.classList.contains('universe-problem')) return '.universe-problem[data-universe-go="' + go + '"]';
      var cat = el.getAttribute('data-universe-index-go');
      if (cat) return '[data-universe-index-go="' + cat + '"]';
      var to = el.getAttribute('data-universe-view-go');
      if (to) return '[data-universe-nav] [data-universe-view-go="' + to + '"]';
      return null;
    }
    function returnFocusFrom(key) {
      if (!key) return false;
      var el = key === 'search' ? searchIn : d0(key);
      if (!el) return false;
      focusQuiet(el);
      return true;
    }
    function noteReturn() {
      returnState = { query: searchIn ? searchIn.value : '', focus: focusKey(document.activeElement) };
    }
    function returnFocusEl() {
      var key = returnState && returnState.focus;
      if (!key) return null;
      return key === 'search' ? searchIn : d0(key);
    }
    function restoreReturn() {
      if (!returnState || !searchIn || panelView !== 'index') return;
      if (searchIn.value !== returnState.query) {
        searchIn.value = returnState.query;
        query = normalizeSearchText(returnState.query);
        countMatches();
        draw();
      }
      refreshIndex();
    }

    // The index: a category list, one category, or every category filtered
    // by the field or scoped to one problem. Counts say what is shown.
    function rowText(li) {
      if (li._uText == null) li._uText = normalizeSearchText(li.textContent || '');
      return li._uText;
    }
    function refreshIndex() {
      var d = dom();
      if (!d.index) return;
      var mode = indexMode();
      var q = query.length >= 2 ? query : '';
      var words = q ? q.split(' ').filter(Boolean) : [];
      var totalShown = 0, filtered = !!(q || indexScope);
      d.cats.forEach(function (section) {
        var key = section.getAttribute('data-universe-cat');
        var rows = section.querySelectorAll ? Array.prototype.slice.call(section.querySelectorAll('.uidx-list > li')) : [];
        var shown = 0;
        rows.forEach(function (li) {
          var row = li.firstElementChild;
          var problems = row && row.getAttribute ? String(row.getAttribute('data-problems') || '').split(' ') : [];
          var text = words.length ? rowText(li) : '';
          var ok = (!indexScope || problems.indexOf(indexScope) >= 0) &&
            words.every(function (w) { return text.indexOf(w) >= 0; });
          li.hidden = !ok;
          if (ok) shown++;
        });
        totalShown += shown;
        if (section.classList) {
          section.classList.toggle('is-open', mode === 'cat' ? key === indexCat : mode === 'all');
          section.classList.toggle('is-empty', mode === 'all' && !shown);
        }
        var outs = d.index.querySelectorAll('[data-universe-cat-count="' + key + '"], [data-universe-cats-count="' + key + '"]');
        Array.prototype.forEach.call(outs || [], function (out) {
          out.textContent = filtered && rows.length ? fmtCount(shown) + ' of ' + fmtCount(rows.length) : out.getAttribute('data-default');
        });
      });
      if (d.indexScopeOut) {
        d.indexScopeOut.hidden = !indexScope;
        if (indexScope) {
          var at = problemIndex[indexScope];
          d.indexScopeOut.innerHTML = 'Showing what the map places with <b>' + escapeHtml(problemShort(indexScope)) +
            (at !== undefined ? ' ' + escapeHtml(nodes[at].label) : '') + '</b>. ' +
            '<button type="button" class="universe-inline-btn" data-universe-index-unscope>Show every problem</button>';
        }
      }
      if (d.indexStatus) {
        var said = '';
        if (q && mode !== 'cats') {
          said = totalShown ? fmtCount(totalShown) + (totalShown === 1 ? ' entry matches' : ' entries match') + ' \u201c' + escapeHtml(searchIn.value.trim()) + '\u201d.' :
            'Nothing in the index matches \u201c' + escapeHtml(searchIn.value.trim()) + '\u201d' + (indexScope ? ' for ' + escapeHtml(problemShort(indexScope)) : '') + '.';
          if (!fullLoaded) said += ' The index lists ' + escapeHtml(String(d.index.querySelectorAll('[data-universe-cat-list="modules"] > li').length)) +
            ' Lean modules until the complete universe is loaded. <button type="button" class="universe-inline-btn" data-universe-load-proxy>Load it</button>';
        }
        d.indexStatus.innerHTML = said;
        d.indexStatus.hidden = !said;
      }
      if (explorerRoot && explorerRoot.setAttribute && panelView === 'index') explorerRoot.setAttribute('data-universe-index', mode);
    }
    // After the complete universe loads, the index lists every Lean module.
    function fillModuleIndex() {
      var d = dom();
      var list = d.index && d.index.querySelector ? d.index.querySelector('[data-universe-cat-list="modules"]') : null;
      if (!list) return;
      var mods = nodes.filter(function (n) { return n.kind === 'lean_module'; });
      if (explorerRoot && explorerRoot.classList) explorerRoot.classList.add('is-full');
      mods.sort(function (a, b) { return a.label < b.label ? -1 : a.label > b.label ? 1 : 0; });
      list.innerHTML = mods.map(function (n) {
        var label = String(n.label || ''), name = label.split('.').pop();
        var problems = String(n.sector || '').split('+').filter(Boolean).join(' ');
        return '<li><a class="uidx-row uidx-row--module" href="' + escapeHtml(n.source_github || '#') + '" data-link-kind="exogenous" rel="external noopener"' +
          ' data-universe-node="' + escapeHtml(n.id) + '"' + (problems ? ' data-problems="' + escapeHtml(problems) + '"' : '') + '>' +
          '<span class="uidx-title">' + escapeHtml(name) + '</span><code class="uidx-ident">' +
          escapeHtml(label).replace(/\./g, '.<wbr>') + '</code></a></li>';
      }).join('');
      var count = fmtCount(mods.length);
      Array.prototype.forEach.call(d.index.querySelectorAll('[data-universe-cat-count="modules"], [data-universe-cats-count="modules"]') || [], function (out) {
        out.setAttribute('data-default', count);
        out.textContent = count;
      });
      Array.prototype.forEach.call(d.index.querySelectorAll('[data-universe-load-proxy]') || [], function (btn) { btn.hidden = true; });
      var note = d.index.querySelector('[data-universe-modules-note]');
      if (note) note.textContent = 'All ' + count + ' Lean modules, now the complete universe is loaded. Choose one to see where the map places it and what it connects to.';
      refreshIndex();
    }

    // How to read the map: the fans inside the ring and the evidence in
    // full, counted over what the map shows.
    function refreshAbout() {
      var d = dom();
      if (d.captions) d.captions.innerHTML = captionsHtml();
      if (d.evidence) d.evidence.innerHTML = evidenceInFullHtml();
    }

    // The map filters: what is set, said in words wherever the reader is,
    // with a reset that never needs the filters reopened.
    // The kinds the map starts with, taken once, before any choice.
    var lensDefault;
    function lensDefaults() {
      if (!lensDefault) {
        lensDefault = {};
        Object.keys(lensOff).forEach(function (k) { lensDefault[k] = lensOff[k]; });
      }
      return lensDefault;
    }
    function keyText(btn) { return String(btn.textContent || '').replace(/\s+/g, ' ').trim(); }
    function activeFilters() {
      var out = [];
      if (paperScope !== 'all') out.push(paperScope === 'short' ? 'short papers only' : 'long papers only');
      if (sharedOnly) out.push('shared Lean support only');
      if (checking !== 'all' && checkingInput && checkingInput.options) {
        var opt = checkingInput.options[checkingInput.selectedIndex];
        out.push(opt ? opt.text.charAt(0).toLowerCase() + opt.text.slice(1) : checking);
      }
      var hidden = [], shownExtra = [];
      Array.prototype.forEach.call(lensKeys || [], function (btn) {
        if (btn.hidden) return;
        var kinds = String(btn.getAttribute('data-universe-lens') || '').split(' ').filter(Boolean);
        var off = kinds.every(function (k) { return !!lensOff[k]; });
        var was = kinds.every(function (k) { return !!lensDefaults()[k]; });
        if (off && !was) hidden.push(keyText(btn));
        if (!off && was) shownExtra.push(keyText(btn));
      });
      if (hidden.length) out.push(hidden.join(', ') + ' hidden');
      if (shownExtra.length) out.push(shownExtra.join(', ') + ' shown');
      var tiersOff = [];
      if (pageMode && document.querySelectorAll) {
        Array.prototype.forEach.call(document.querySelectorAll('[data-universe-tier]') || [], function (btn) {
          if (tierOff[btn.getAttribute('data-universe-tier')]) tiersOff.push(keyText(btn).toLowerCase());
        });
      }
      if (tiersOff.length) out.push('claims hidden: ' + tiersOff.join(', '));
      return out;
    }
    function renderFilterSummary() {
      if (!explorerRoot) return;
      var d = dom();
      var active = activeFilters();
      if (d.filtered) {
        d.filtered.hidden = !active.length || (panelView === 'filters' && selected < 0);
        if (d.filteredText) d.filteredText.textContent = active.length ? 'Map filtered: ' + active.join('; ') + '.' : '';
      }
      if (d.badge) {
        d.badge.hidden = !active.length;
        d.badge.innerHTML = active.length ? String(active.length) + '<span class="sr-only"> active</span>' : '';
      }
      d.resets.forEach(function (btn) { btn.disabled = !active.length; });
    }
    function resetFilters() {
      paperScope = 'all';
      document.querySelectorAll('[data-universe-scope]').forEach(function (btn) {
        btn.setAttribute('aria-pressed', String(btn.getAttribute('data-universe-scope') === 'all'));
      });
      sharedOnly = false;
      if (overlapInput) overlapInput.checked = false;
      checking = 'all';
      if (checkingInput) checkingInput.value = 'all';
      tierOff = {};
      document.querySelectorAll('[data-universe-tier]').forEach(function (btn) { btn.setAttribute('aria-pressed', 'true'); });
      Object.keys(lensOff).forEach(function (k) { delete lensOff[k]; });
      var base = lensDefaults();
      Object.keys(base).forEach(function (k) { lensOff[k] = base[k]; });
      Array.prototype.forEach.call(lensKeys || [], function (btn) {
        var kinds = String(btn.getAttribute('data-universe-lens') || '').split(' ').filter(Boolean);
        btn.setAttribute('aria-pressed', kinds.every(function (k) { return !lensOff[k]; }) ? 'true' : 'false');
      });
      afterFilterChange();
    }

    // A search that finds nothing says why: the filters, what is not loaded
    // yet, and where every object is listed.
    function renderNone() {
      var d = dom();
      if (!d.none || !searchIn) return;
      var inIndex = explorerRoot && panelView === 'index' && selected < 0;
      var show = !inIndex && overviewReady && query.length >= 2 && !matchList.length;
      d.none.hidden = !show;
      if (!show) { d.none.innerHTML = ''; return; }
      var bits = ['Nothing shown on the map matches \u201c' + escapeHtml(searchIn.value.trim()) + '\u201d.'];
      if (activeFilters().length) {
        bits.push('The map filters hide some objects: <button type="button" class="universe-inline-btn" data-universe-filters-reset>reset them</button>.');
      }
      if (!fullLoaded) {
        bits.push('Lean modules and argument steps are found once the complete universe is loaded: <button type="button" class="universe-inline-btn" data-universe-load-proxy>load it</button>.');
      }
      if (dom().index) bits.push('The <button type="button" class="universe-inline-btn" data-universe-view-go="index">index</button> lists every object.');
      d.none.innerHTML = bits.join(' ');
    }

    if (explorerRoot && dom().panel) {
      panelEl = dom().panel;
      panelEl.addEventListener('click', function (event) {
        var t = event.target;
        if (!t || !t.closest) return;
        var go = t.closest('[data-universe-view-go]');
        if (go) {
          event.preventDefault();
          var to = go.getAttribute('data-universe-view-go');
          var peer = !!go.closest('.universe-tabs');
          if (peer) {
            if (to === 'index' && panelView === 'index' && selected < 0 && !indexCat && !indexScope) return;
            setView(to, { reset: true });
          } else if (to === panelView && selected < 0 && go.closest('[data-universe-nav]')) {
            viewBack();
          } else {
            setView(to, { push: true, focus: 'heading', at: go.getAttribute('data-universe-view-at') === 'evidence' ? 'universe-evidence-title' : null });
          }
          return;
        }
        if (t.closest('[data-universe-view-back]')) { event.preventDefault(); viewBack(); return; }
        if (t.closest('[data-universe-filters-reset]')) {
          event.preventDefault();
          var inSummary = !!t.closest('[data-universe-filtered], [data-universe-none]');
          resetFilters();
          if (inSummary) focusQuiet(d0('[data-universe-nav] [data-universe-view-go="filters"]'));
          return;
        }
        if (t.closest('[data-universe-load-proxy]')) { event.preventDefault(); loadFull(); return; }
        var cat = t.closest('[data-universe-index-go]');
        if (cat) {
          event.preventDefault();
          setView('index', { cat: cat.getAttribute('data-universe-index-go'), scope: indexScope, push: true, focus: 'heading' });
          return;
        }
        if (t.closest('[data-universe-index-unscope]')) {
          event.preventDefault();
          indexScope = '';
          refreshIndex();
          syncPanelView();
          focusQuiet(d0('#universe-index-title'));
          return;
        }
        var scope = t.closest('[data-universe-index-scope]');
        if (scope && selected >= 0) {
          event.preventDefault();
          setView('index', { scope: scope.getAttribute('data-universe-index-scope'), push: stateNow(), focus: 'heading' });
          return;
        }
        // A row of the index whose object is on the map opens its card
        // here; a modified click follows its link as any link does.
        var row = t.closest('[data-universe-node]');
        if (row && restBox && restBox.contains(row) && !(event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)) {
          var at = byId[row.getAttribute('data-universe-node')];
          if (at !== undefined && visible(nodes[at])) {
            event.preventDefault();
            pin(at, true);
          }
        }
      });
      syncPanelView();
      // The body's scrollbar, where the system draws one, as a width the
      // head adds to its right padding, so the search ends where rows end.
      var measureGutter = function () {
        if (!scrollBox || !explorerRoot.style || !explorerRoot.style.setProperty) return;
        var gutter = Math.max(0, (scrollBox.offsetWidth || 0) - (scrollBox.clientWidth || 0));
        explorerRoot.style.setProperty('--u-gutter', gutter + 'px');
      };
      measureGutter();
      explorerRoot.addEventListener('explorer:resize', measureGutter);
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
      // The problems' questions and short papers, for the panel's cards.
      if (pageMode && companionSpec) loadProblemInfo();
      if (opening) startReveal();
      if (teaserOpening) {
        // On the first screen the drawing opens at once. Since the map moved
        // up onto the landing's first screen (5 October 2026) a third of it
        // or less shows there, and a reader who had not scrolled met an empty
        // frame. Reached by scrolling, it still waits until a third shows,
        // so the rings arrive where the reader is looking.
        // At first look "on the first screen" includes a drawing that
        // starts just under its fold: at 1280 by 690 the card's frame showed
        // while its canvas, a few pixels lower, waited closed and the reader
        // met an empty frame (5 October 2026). Within a screen of the
        // viewport it opens at once.
        var firstLook = true;
        var seen = new IntersectionObserver(function (entries) {
          var e = entries[entries.length - 1];
          var box = e.boundingClientRect, port = e.rootBounds;
          var near = firstLook && box && port && box.top < port.bottom + port.height && box.bottom > port.top;
          if ((e.isIntersecting && (firstLook || e.intersectionRatio >= 0.35)) || near) {
            seen.disconnect();
            startReveal();
          }
          firstLook = false;
        }, { threshold: [0, 0.35] });
        seen.observe(canvas);
      }
      if (!pageMode) {
        loadCompanion(data.companion);
        buildKey();
      }
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
        plateBreaks = {};
        pinnedPlate = null;
        // The teaser is fitted to its words, which were measured in the
        // fallback face too.
        // So is the explorer, whose key over the drawing's corner is set in
        // the page's own face.
        chromeCache = null;
        if ((!pageMode || inExplorer) && nodes.length && viewIsFitted) fit();
        if (nodes.length) draw();
      }, function () {});
    }

    /* ---- Pointer ------------------------------------------------------ */

    var panning = false;
    var moved = false;

    // On the page a hover previews in its layer over the panel; without
    // that layer (the old placard page) the rail itself previews.
    function hoverChanged() {
      if (previewBox) refreshPreview(); else renderInspector();
    }
    canvas.addEventListener('pointermove', function (event) {
      if (panning) return;
      var rect = canvas.getBoundingClientRect();
      var i = nodeAt(event.clientX - rect.left, event.clientY - rect.top);
      if (i !== hover || !hoverFromMap) {
        hover = i;
        hoverFromMap = true;
        canvas.classList.toggle('is-over', i >= 0);
        draw();
        if (pageMode) hoverChanged(); else { showCaption(i); announce(i); }
      }
    });
    canvas.addEventListener('pointerleave', function () {
      if (hover === -1) return;
      hover = -1;
      canvas.classList.remove('is-over');
      draw();
      if (pageMode) hoverChanged(); else { showCaption(-1); announce(-1); }
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
        // A click on empty ground steps back: it lets a pin go, and with
        // nothing pinned it returns a closer view to the whole field.
        if (i < 0) { stepBack(); return; }
        // Pinning a problem frames its sector and a paper its results, a
        // level down; a result or a claim pins where it is, under the pointer.
        // A click inside what is pinned goes a level further down its trail.
        var frames = nodes[i].kind === 'problem' || nodes[i].kind === 'paper';
        var last = trail.length ? trail[trail.length - 1] : null;
        if (!last || last.at !== selected || !holds(last.at, i)) trail = [];
        trail.push({ at: i, before: frames ? viewNow() : null });
        pin(i, frames, true);
        // On a phone the explorer shows the panel for what was chosen.
        if (!explorerRoot) revealCard();
        return;
      }
      // Beside the column a dot pins, and empty ground lets a pin go. A
      // second click on the pinned dot opens it at its place in its paper,
      // as on the full map and the system map (Will, 5 October 2026: "if
      // you select and click it" it should take you there). A near miss
      // used to fall through to the full map, throwing the reader off the
      // landing; it still never leaves the page.
      if (companionApi && typeof companionApi.sideBySide === 'function' && companionApi.sideBySide()) {
        if (i >= 0 && i === selected) { openTarget(nodes[i]); return; }
        if (i >= 0 || selected >= 0) pinInTeaser(i >= 0 ? i : -1);
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
        var typing = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (event.target && event.target.isContentEditable);
        // In the panel, with nothing kept, Esc goes back a view (a category
        // to the index, a tool to the view it was opened from).
        if (event.key === 'Escape' && selected < 0 && explorerRoot && panelView !== 'problems' &&
            panelEl && panelEl.contains(document.activeElement)) {
          event.preventDefault();
          viewBack();
          return;
        }
        if (event.key === 'Escape' && (selected >= 0 || (!typing && !viewIsFitted))) { stepBack(); return; }
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
          return;
        }
        // The keyboard's own zoom, as on a map: + and - step, 0 fits. The
        // arrows move the map (Shift for a long step), as on the system
        // map, while nothing in the reading panel holds the keyboard; a
        // kept paper statement keeps left and right for its neighbours.
        if (!typing && explorerRoot && !event.metaKey && !event.ctrlKey && !event.altKey) {
          var arrow = { ArrowLeft: [1, 0], ArrowRight: [-1, 0], ArrowUp: [0, 1], ArrowDown: [0, -1] }[event.key];
          var held = document.activeElement;
          if (arrow && (!held || held === document.body || stage.contains(held))) {
            event.preventDefault();
            var stepPx = event.shiftKey ? 240 : 80;
            cameraTo({ k: view.k, tx: view.tx + arrow[0] * stepPx, ty: view.ty + arrow[1] * stepPx }, false);
            return;
          }
          if (event.key === '+' || event.key === '=') { event.preventDefault(); zoomBy(1.5); }
          else if (event.key === '-' || event.key === '_') { event.preventDefault(); zoomBy(1 / 1.5); }
          else if (event.key === '0') { event.preventDefault(); fitAnimated(); }
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
      /* The explorer's own controls (assets/explorer.js): Fit shows the
         whole map, the zoom steps ease about the centre, and a change in
         the stage's size (the window, full screen, the phone's Map view)
         fits again if the view was fitted, or keeps the same centre. */
      if (explorerRoot) {
        explorerRoot.addEventListener('explorer:fit', function () { fitAnimated(); });
        explorerRoot.addEventListener('explorer:zoom', function (event) {
          zoomBy(event.detail && event.detail.direction < 0 ? 1 / 1.5 : 1.5);
        });
        explorerRoot.addEventListener('explorer:resize', function () {
          chromeCache = null;
          if (nodes.length && followBox()) draw();
        });
      }
    }
    function zoomBy(factor) {
      var w = canvas.clientWidth, h = canvas.clientHeight;
      var k = Math.min(9, Math.max(Math.min(0.3, fittedScale / 2), view.k * factor));
      var f = k / view.k;
      cameraTo({ k: k, tx: w / 2 - (w / 2 - view.tx) * f, ty: h / 2 - (h / 2 - view.ty) * f }, false);
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
          if (isNaN(i) || !nodes[i]) return;
          var last = trail.length ? trail[trail.length - 1] : null;
          // Up to the level the reader came down from: the way back.
          if (last && last.at === selected && trail.length > 1 && trail[trail.length - 2].at === i) { stepBack(); return; }
          // Down into what the card holds (a problem's result, a paper's):
          // the trail goes on, and the view moves only to keep it in sight.
          if (last && last.at === selected && holds(selected, i)) {
            var frames = nodes[i].kind === 'problem' || nodes[i].kind === 'paper';
            trail.push({ at: i, before: frames ? viewNow() : null });
            pin(i, frames, true);
            if (!frames) keepInView(i, trail[trail.length - 1]);
            return;
          }
          pin(i, true);
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
          stepBack();
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

    /* A row in the panel (a problem, a result, a connection) under the
       pointer or in keyboard focus lights its place on the map: the field
       focuses it and its name plate shows, as a hover on the map does, and
       the panel itself is left exactly as it is. */
    function lightFromPanel(event) {
      // A kept result's references name its own relations: they identify
      // them on the figure and leave the focus where it is.
      var ref = event.target && event.target.closest ? event.target.closest('[data-universe-refer]') : null;
      if (ref && !(inspector && inspector.contains(ref))) ref = null;
      var j = ref ? parseInt(ref.getAttribute('data-universe-refer'), 10) : -1;
      if (!relationDrawn(selected, j)) { ref = null; j = -1; }
      if (ref !== referEl) {
        if (referEl && referEl.classList) referEl.classList.remove('is-referred');
        referEl = ref;
        if (ref && ref.classList) ref.classList.add('is-referred');
      }
      setRefer(j);
      if (ref) return;
      var go = event.target && event.target.closest ? event.target.closest('[data-universe-go]') : null;
      var i = go ? parseInt(go.getAttribute('data-universe-go'), 10) : -1;
      // An index row names its object by id; on the map, it lights it too.
      var named = !go && event.target && event.target.closest ? event.target.closest('[data-universe-node]') : null;
      if (named && byId[named.getAttribute('data-universe-node')] !== undefined) i = byId[named.getAttribute('data-universe-node')];
      if (isNaN(i) || !nodes[i] || !visible(nodes[i])) i = -1;
      if (i < 0 && (hoverFromMap || hover < 0)) return;
      if (i === hover && !hoverFromMap) return;
      hoverFromMap = false;
      hover = i;
      draw();
      refreshPreview();
    }
    function unlightFromPanel() {
      if (referEl && referEl.classList) referEl.classList.remove('is-referred');
      referEl = null;
      setRefer(-1);
      if (hoverFromMap || hover < 0) return;
      hover = -1;
      draw();
    }
    if (scrollBox && explorerRoot) {
      scrollBox.addEventListener('pointerover', lightFromPanel);
      scrollBox.addEventListener('pointerleave', unlightFromPanel);
      scrollBox.addEventListener('focusin', lightFromPanel);
      scrollBox.addEventListener('focusout', function (event) {
        if (!event.relatedTarget || !scrollBox.contains(event.relatedTarget)) unlightFromPanel();
      });
    }

    /* ---- Controls ----------------------------------------------------- */

    function afterFilterChange() {
      visGen++;
      frameGraphCache = null;
      pinnedPlate = null;
      if (hover >= 0 && !visible(nodes[hover])) hover = -1;
      if (selected >= 0 && !visible(nodes[selected])) pin(-1, false);
      else renderInspector();
      countMatches();
      renderResults();
      renderFilterSummary();
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
        if (EVIDENCE_ORDER.indexOf(tier) >= 0 && checkingInput) { checking = 'all'; checkingInput.value = 'all'; }
        afterFilterChange();
      });
    });

    document.querySelectorAll('[data-universe-scope]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        paperScope = btn.getAttribute('data-universe-scope');
        document.querySelectorAll('[data-universe-scope]').forEach(function (other) {
          other.setAttribute('aria-pressed', String(other === btn));
        });
        afterFilterChange();
      });
    });
    if (overlapInput) overlapInput.addEventListener('change', function () {
      sharedOnly = overlapInput.checked;
      afterFilterChange();
    });
    if (checkingInput) checkingInput.addEventListener('change', function () {
      checking = checkingInput.value;
      // Choosing a verification view replaces evidence toggles from the key.
      EVIDENCE_ORDER.forEach(function (tier) { delete tierOff[tier]; });
      document.querySelectorAll('[data-universe-tier]').forEach(function (btn) {
        if (EVIDENCE_ORDER.indexOf(btn.getAttribute('data-universe-tier')) >= 0) btn.setAttribute('aria-pressed', 'true');
      });
      afterFilterChange();
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
      renderNone();
      // In the index the field filters the lists in place; no menu opens.
      if (explorerRoot && panelView === 'index' && selected < 0) { closeResults(); refreshIndex(); return; }
      if (!resultsBox || !searchIn) return;
      if (query.length < 2 || !matchList.length || document.activeElement !== searchIn) { closeResults(); return; }
      var top = matchList.slice(0, RESULT_CAP);
      if (activeResult >= top.length) activeResult = top.length - 1;
      resultsBox.innerHTML = top.map(function (idx, at) {
        var n = nodes[idx];
        var mark = n.kind === 'paper_statement' || n.kind === 'public_claim' ? glyphHtml(n.proof_status || n.tier) : dotHtml(n.kind);
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
            proof_status: n.proof_status, proof_note: n.proof_note,
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
        fillModuleIndex();
        renderNone();
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

    function followBox() {
      var w = canvas.clientWidth, h = canvas.clientHeight;
      if (w === viewWidth && h === viewHeight) return false;
      chromeCache = null;
      if (viewIsFitted) fit();
      else {
        // Keep the same object under the centre when rotating a phone or
        // resizing a window; only Reset should discard an explored view.
        view.tx += (w - viewWidth) / 2;
        view.ty += (h - viewHeight) / 2;
        viewWidth = w; viewHeight = h;
      }
      return true;
    }
    var resizeTimer = null;
    window.addEventListener('resize', function () {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        if (followBox()) draw();
      }, 120);
    });
    /* The canvas's own box, observed directly: the drawing follows it when
       the page changes it without a window resize, and learns its exact
       size in device pixels, which the backing store then takes. */
    if (typeof ResizeObserver === 'function') {
      var sizer = new ResizeObserver(function (entries) {
        var entry = entries[entries.length - 1];
        var box = entry && entry.devicePixelContentBoxSize && entry.devicePixelContentBoxSize[0];
        var was = deviceBox;
        deviceBox = box && (window.devicePixelRatio || 1) <= 2 ? [box.inlineSize, box.blockSize] : null;
        var moved = nodes.length ? followBox() : false;
        if (moved || String(was) !== String(deviceBox)) draw();
      });
      try { sizer.observe(canvas, { box: 'device-pixel-content-box' }); }
      catch (err) { sizer.observe(canvas); }
    }
    // Out of view (scrolled past, or slid aside by the landing's atlas) the
    // canvas is not painted; it is painted once when it returns.
    if (typeof IntersectionObserver === 'function') {
      new IntersectionObserver(function (entries) {
        var now = !!entries[entries.length - 1].isIntersecting;
        if (now === onScreen) return;
        onScreen = now;
        if (!now) settleMotion();
        else if (paintPending) draw();
      }, { rootMargin: '120px 0px' }).observe(canvas);
    }
    document.addEventListener('visibilitychange', function () {
      if (document.hidden) settleMotion();
      else if (paintPending) draw();
    });
    function repaint() {
      readPalette();
      draw();
    }
    document.addEventListener('plectis:theme', repaint);
    // The system scheme can change under a page that follows it.
    var schemeQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
    if (schemeQuery && typeof schemeQuery.addEventListener === 'function') {
      schemeQuery.addEventListener('change', repaint);
    } else if (schemeQuery && typeof schemeQuery.addListener === 'function') {
      schemeQuery.addListener(repaint);
    }
    /* The landing's atlas slides this drawing aside for the system map and
       back (plectis:atlas, from landing.js). Leaving, the drawing lets go of
       what it was showing: the hover, a pin, and the column's card, so
       nothing stays lit out of view. Coming back plays nothing: the opening
       has been spent, and the canvas simply paints when it is in view. */
    if (!pageMode) {
      document.addEventListener('plectis:atlas', function (event) {
        var detail = (event && event.detail) || {};
        if (detail.phase !== 'start' || detail.previous !== 'mathematics' || detail.view === 'mathematics') return;
        var had = hover >= 0 || selected >= 0;
        hover = -1;
        canvas.classList.remove('is-over');
        showCaption(-1);
        if (selected >= 0) pinInTeaser(-1);
        else if (companionApi) stage.dispatchEvent(new CustomEvent('universe:select', { detail: null }));
        announce(-1);
        if (had) draw();
      });
    }
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
