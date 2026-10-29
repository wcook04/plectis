// The evidence map: one canvas, drawn on demand.
//
// Adapted from the Plectis universe map (ai_workflow
// tools/meta/dissemination/maths_site_assets/universe.js). Harvested and
// adapted there: the camera (cameraTo, flightPath after van Wijk and Nuij,
// frameOf, fit), the focus fade (FOCUS_IN/HOLD/OUT), the ember light under
// machine-checked marks on a dark ground, the evidence pulse (a ripple, beads
// with tails, an answering ripple), reticles, leaders, arc lettering
// (arcLetters, drawArcText), device-pixel hairlines, the capped backing store
// and the centre-out opening. The marks for how a component is backed are the
// system map's five glyphs (sites/microcosm/assets/system-map.js GLYPHS).
// What is new is the picture itself (see layout.js): the verified
// computations inside the ring, drawn as proof dials with one tick per
// verified task, and the coverage rings outside it, read like the tracks of a
// circular genome plot, one ring per kind of check. Beyond the family names
// stands the doctrine's halo, moved out from the system map's centre: its
// three marks (system-map.js ruleGlyph), principles on the inner orbit, the
// axioms they rest on, and the failure modes that threaten them outermost,
// each rule tied to its axioms by a ruled lane. Just outside the rings runs
// the register, one tick per component for the rules its record cites; a
// chosen rule caps exactly its citers, and each citation it can show is its
// own nested route (layout.js planRoutes). A hairline alidade points along
// the chosen object's radius.

import { glowSprite, isDark, mixOklab, parseColor, rgbText } from './color.js';
import { angleShare, crossSpan, DIAL, flowerPx, FLOWER, KEY_GAP, layout, planRoutes, polar, R, shortArc, trackBand } from './layout.js';
import { arcDiscs, createPlanner, fitText, levelOfDetail, localPitch, LOD, PRIORITY } from './labels.js';
import {
  CORE_NAMES, TRACKS, classWords, count, familyName, membersOf, moduleWords, obligationWords, proofShortName, ruleKindWords, supportWords,
} from '../evidence.js';

const SERIF = '"Plectis Serif", "Plectis Math", "Plectis Serif Fallback", Georgia, serif';
const SANS = '"Plectis Sans", "Plectis Sans Fallback", -apple-system, "Segoe UI", Arial, sans-serif';
const face = (weight, size, italic, family = SERIF) => `${italic ? 'italic ' : ''}${weight} ${size}px ${family}`;
const TYPE = { title: 14, count: 12.5, rowGap: 16, plate: 13.5, sub: 11.5, anchor: 13.5, kernel: 12, name: 11.5 };

const FOCUS_IN = 180, FOCUS_HOLD = 140, FOCUS_OUT = 220;
const PULSE_WAIT = 110, CHOSEN_RING = 400, PULSE_TRAVEL = 620, PULSE_STAGGER = 70, PULSE_BLOOM = 560;
// The opening runs from the centre out: the cores flower, the replay spokes
// reach the ring, the kernels flower, their threads grow, the components
// appear round the ring, then each coverage ring is read clockwise in turn.
// Last, the halo: its orbits are drawn round clockwise, the axioms kindle,
// the rules join them, their lanes run in, and the citations rise.
const REVEAL = { bezel: 0, bezelDur: 420, core: 0, cores: 110, spokes: 180, spokeDur: 380, kernels: 520, threads: 420, threadDur: 380, pen: 150, penDur: 560, tracks: 480, trackLag: 55, trackDur: 300, words: 760, fade: 240,
  halo: 820, haloDur: 520, axioms: 960, rules: 1060, lanes: 1180, laneDur: 320, fibers: 1280, fiberDur: 300, end: 1650 };
const GROW_MS = 260;
const COMPACT_SCALE = 190;
const HALO_WORDS = 22; // pixels kept beyond the halo for the axioms' names
const TURN = Math.PI * 2;

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);
const clamp01 = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t);

export function createMap(canvas, model, hooks = {}) {
  const ctx = canvas.getContext('2d');
  const stage = canvas.parentElement;
  const L = layout(model);
  const reduceQuery = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  let reduceMotion = !!(reduceQuery && reduceQuery.matches);

  /* ---- Objects ----------------------------------------------------------- */
  const objects = [];
  const byKey = new Map();
  const add = (o) => { o.index = objects.length; objects.push(o); byKey.set(o.key, o); return o; };
  const coreObj = new Map();
  for (const p of L.cores) {
    const core = model.coreById.get(p.id);
    const centre = p.id === 'replay_admission';
    coreObj.set(p.id, add({ key: `core:${p.id}`, type: 'core', id: p.id, core, x: p.x, y: p.y, angle: p.angle, r: centre ? 11 : 8, centre,
      tasks: core.verifiedTasks || 0, mutants: core.mutants.length }));
  }
  const replayCore = coreObj.get('replay_admission') || null;
  const kernelObj = new Map();
  for (const k of L.kernels) {
    const kernel = model.kernelById.get(k.id);
    // Its stem out to its component (layout.js stemFor): straight along the
    // component's radius, or doglegged round a neighbouring flower.
    const thread = k.to !== null ? k.stem : [];
    kernelObj.set(k.id, add({ key: `kernel:${k.id}`, type: 'kernel', id: k.id, kernel, x: k.x, y: k.y, angle: k.angle, r: 8, orbit: k.r, depth: k.depth,
      componentId: k.componentId, thread, dogleg: k.dogleg, generated: k.generated, caller: k.caller, generatedR: k.generatedR, callerR: k.callerR,
      tasks: kernel.verifiedTasks || 0, mutants: kernel.mutants.length }));
  }
  const sectorOf = new Map();
  for (const s of L.sectors) for (const id of s.members) sectorOf.set(id, s);
  const compObj = new Map();
  for (const p of L.comps) {
    const c = model.byId.get(p.id);
    compObj.set(c.id, add({ key: `comp:${c.id}`, type: 'component', id: c.id, comp: c, x: p.x, y: p.y, angle: p.angle,
      r: c.kernelId ? 5.6 : 4.9, formal: !!c.kernelId, sector: sectorOf.get(c.id) }));
  }
  const routed = new Set(replayCore ? replayCore.core.admitted.map((a) => a.componentId) : []);
  const wiresOf = new Map();
  for (const [a, b] of model.wires) {
    if (!wiresOf.has(a)) wiresOf.set(a, []);
    if (!wiresOf.has(b)) wiresOf.set(b, []);
    wiresOf.get(a).push(b);
    wiresOf.get(b).push(a);
  }
  const importsOf = new Map();
  for (const e of model.imports) {
    for (const [x, y] of [[e.from, e.to], [e.to, e.from]]) {
      if (!importsOf.has(x)) importsOf.set(x, []);
      importsOf.get(x).push(y);
    }
  }
  // The halo's rules, their lanes and the citation fibres (layout.js).
  const halo = L.halo;
  const ruleObj = new Map();
  for (const m of halo?.marks || []) {
    const rule = model.ruleById.get(m.id);
    ruleObj.set(m.id, add({ key: `rule:${m.id}`, type: 'rule', id: m.id, rule, kind: m.kind, x: m.x, y: m.y, angle: m.angle, orbit: m.r, share: m.share }));
  }
  // Each component's tooth: a step for every rule its record cites, the
  // axioms nearest the rim, then the principles.
  const maxCited = Math.max(1, ...[...ruleObj.values()].map((o) => o.rule.citedBy.length));
  const teethOf = new Map();
  for (const c of compObj.values()) {
    const ids = (c.comp.ruleIds || []).filter((id) => ruleObj.has(id));
    teethOf.set(c.id, [...ids.filter((id) => ruleObj.get(id).kind === 'axiom'), ...ids.filter((id) => ruleObj.get(id).kind !== 'axiom')]);
  }

  /* ---- State -------------------------------------------------------------- */
  const view = { k: 1, tx: 0, ty: 0 };
  let fittedK = 1, viewIsFitted = true;
  let hover = null, selected = null, hoverTrack = -1;
  let matches = null; // Set of component ids, or null for "all"
  let matchesGen = 0, paletteGen = 0, fontGen = 0; // label-plan cache keys
  let emphasis = null; // a track id lit from the panel, or null
  let allWiring = false;
  let palette = {};
  let darkGround = false;
  let hatch = null;
  let labelBoxes = [];
  // This paint's inscriptions (planInscriptions) and the level of detail,
  // kept between paints for its hysteresis.
  let ins = null;
  let lodLevel = null;
  let panelHidden = false;
  let hairPx = 0.5;
  let frame = 0, advancing = false, paintRequested = false;
  let nextAnimation = 1;
  const animations = new Map();
  let destroyed = false;
  const onScreen = true;

  /* ---- Palette ------------------------------------------------------------ */
  function cssColor(styles, name, fallback) {
    const v = styles.getPropertyValue(name).trim();
    return v || fallback;
  }
  function readPalette() {
    const styles = getComputedStyle(document.documentElement);
    palette = {
      ground: cssColor(styles, '--m-ground', '#1c1526'),
      ink: cssColor(styles, '--ink', '#f2e6d4'),
      muted: cssColor(styles, '--muted', '#bcb8c6'),
      faint: cssColor(styles, '--m-faint', '#85818e'),
      proved: cssColor(styles, '--m-proved', '#b84e45'),
      provedGlow: cssColor(styles, '--weave-red-glow', '#e67b6d'),
      stated: cssColor(styles, '--m-stated', '#93c5e6'),
      plate: cssColor(styles, '--m-plate', 'rgba(242,230,212,0.05)'),
      edge: cssColor(styles, '--m-edge', 'rgba(242,230,212,0.14)'),
      halo: cssColor(styles, '--m-halo', 'rgba(242,230,212,0.12)'),
      ember: cssColor(styles, '--m-ember', '#d9a48d'),
    };
    darkGround = isDark(palette.ground);
    // Red is drawn at its glow step on the dark ground, where the base step
    // reads muddy at mark size, and at its base step on paper.
    palette.red = darkGround ? palette.provedGlow : palette.proved;
    const ground = parseColor(palette.ground) || [0, 0, 0, 1];
    palette.groundText = rgbText(ground);
    palette.tone = mixOklab(palette.ink, palette.groundText, 0.84, ground) || palette.faint;
    palette.empty = mixOklab(palette.ink, palette.groundText, darkGround ? 0.9 : 0.92, ground) || palette.plate;
    palette.redSoft = mixOklab(palette.red, palette.groundText, 0.55, ground) || palette.red;
    palette.statedSoft = mixOklab(palette.stated, palette.groundText, darkGround ? 0.42 : 0.5, ground) || palette.stated;
    hatch = makeHatch(mixOklab(palette.ink, palette.groundText, 0.62, ground) || palette.faint);
    palette.doctrine = cssColor(styles, '--m-doctrine', palette.stated);
    palette.threat = cssColor(styles, '--m-threat', palette.muted);
    palette.doctrineSoft = mixOklab(palette.doctrine, palette.groundText, darkGround ? 0.55 : 0.6, ground) || palette.doctrine;
    // Each coverage ring has its own colour (tokens.css --ring-*).
    palette.ring = {};
    for (const t of TRACKS) palette.ring[t.id] = cssColor(styles, `--ring-${t.id}`, t.ink === 'stated' ? palette.stated : t.ink === 'saved' ? palette.ember : palette.red);
  }
  function makeHatch(color) {
    const tile = document.createElement('canvas');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const n = Math.round(5 * dpr);
    tile.width = tile.height = n;
    const g = tile.getContext('2d');
    if (!g) return null;
    g.strokeStyle = color;
    g.lineWidth = Math.max(1, dpr * 0.8);
    g.beginPath();
    g.moveTo(-1, n + 1); g.lineTo(n + 1, -1);
    g.moveTo(-1, 1); g.lineTo(1, -1);
    g.moveTo(n - 1, n + 1); g.lineTo(n + 1, n - 1);
    g.stroke();
    const pattern = ctx.createPattern(tile, 'repeat');
    if (pattern && pattern.setTransform && window.DOMMatrix) pattern.setTransform(new DOMMatrix().scale(1 / dpr));
    return pattern;
  }

  /* ---- Camera ------------------------------------------------------------- */
  // Layout reads are shared by fitting, hit testing and painting. Animation
  // frames reuse them until the surrounding DOM or viewport actually changes.
  let dimensions = null, chrome = null;
  const chromeSelector = '.explorer__tools, .explorer__legend > *, .explorer__rings';
  const observedChrome = new Set();
  let observer = null;
  const size = () => dimensions || (dimensions = [canvas.clientWidth, canvas.clientHeight]);
  function invalidateGeometry() { dimensions = null; chrome = null; }
  function chromeBoxes() {
    if (chrome) return chrome;
    if (!stage || !canvas.getBoundingClientRect) return (chrome = []);
    const base = canvas.getBoundingClientRect();
    const elements = Array.from(stage.querySelectorAll(chromeSelector));
    for (const el of observedChrome) if (!elements.includes(el)) { observer?.unobserve(el); observedChrome.delete(el); }
    for (const el of elements) if (!observedChrome.has(el)) { observer?.observe(el); observedChrome.add(el); }
    // Whether the reading panel is out of the way, so the selection chip
    // may stand on the stage (read with the rest of the layout, once).
    const root = stage.closest ? stage.closest('.explorer') : null;
    const panel = root && root.querySelector ? root.querySelector('.explorer__panel') : null;
    panelHidden = false;
    if (root && root.classList && root.classList.contains('is-panel-collapsed')) panelHidden = true;
    else if (panel && panel.getBoundingClientRect) {
      const pr = panel.getBoundingClientRect();
      panelHidden = pr.width < 2 || pr.height < 2;
    }
    const roleOf = (el) => (el.closest && el.closest('.explorer__legend') ? 'legend' : el.matches && el.matches('.explorer__rings') ? 'rings' : 'tools');
    return (chrome = elements.map((el) => {
      const r = el.getBoundingClientRect();
      return { x0: r.left - base.left, x1: r.right - base.left, y0: r.top - base.top, y1: r.bottom - base.top, role: roleOf(el) };
    }).filter((b) => b.x1 > b.x0 && b.y1 > b.y0));
  }
  function fitTarget() {
    const [w, h] = size();
    const reach = L.radius;
    let limit = Math.min(w, h) / 2 - 12;
    const cx = w / 2, cy = h / 2;
    for (const b of chromeBoxes()) {
      const dx = Math.max(b.x0 - cx, 0, cx - b.x1), dy = Math.max(b.y0 - cy, 0, cy - b.y1);
      limit = Math.min(limit, Math.max(Math.min(w, h) * 0.36, Math.sqrt(dx * dx + dy * dy) - 6));
    }
    // The halo is outermost, with room beyond it for the axioms' names.
    if (halo) return { k: Math.max(0.05, (limit - HALO_WORDS) / R.haloOuter), tx: cx, ty: cy };
    // The family titles stand a fixed number of pixels beyond the rings, so
    // the fit holds the rings' radius plus their reach, not a layout radius.
    const full = 16 + TYPE.rowGap * 2 + 12;
    let k = Math.max(0.05, Math.min(limit / reach, (limit - full) / R.scale));
    // A small drawing names each family on one line, so it keeps its size.
    if (R.scale * k < COMPACT_SCALE) k = Math.max(0.05, (limit - 16 - TYPE.rowGap - 10) / R.scale);
    return { k, tx: cx, ty: cy };
  }
  function fit() {
    const t = fitTarget();
    fittedK = t.k;
    Object.assign(view, t);
    viewIsFitted = true;
  }
  let cameraFrame = 0, cameraFinish = null;
  function flightPath(from, to, span) {
    const RHO = 1.4;
    const w0 = span / from.k, w1 = span / to.k;
    const dx = to.cx - from.cx, dy = to.cy - from.cy, d2 = dx * dx + dy * dy, u1 = Math.sqrt(d2);
    if (!(u1 > Math.min(w0, w1) * 0.9) || from.k <= fittedK * 1.25 || to.k <= fittedK * 1.25) return null;
    const rho2 = RHO * RHO, rho4 = rho2 * rho2;
    const b0 = (w1 * w1 - w0 * w0 + rho4 * d2) / (2 * w0 * rho2 * u1);
    const b1 = (w1 * w1 - w0 * w0 - rho4 * d2) / (2 * w1 * rho2 * u1);
    const r0 = Math.log(Math.sqrt(b0 * b0 + 1) - b0), r1 = Math.log(Math.sqrt(b1 * b1 + 1) - b1);
    const S = (r1 - r0) / RHO;
    if (!Number.isFinite(S) || S <= 0) return null;
    const c0 = Math.cosh(r0);
    return {
      ms: S * 1000 * RHO / Math.SQRT2 * 0.62,
      at(t) {
        if (t >= 1) return [to.cx, to.cy, to.k];
        const s = t * S;
        const u = w0 / rho2 * (c0 * Math.tanh(RHO * s + r0) - Math.sinh(r0));
        const wide = w0 * c0 / Math.cosh(RHO * s + r0);
        return [from.cx + u * dx / u1, from.cy + u * dy / u1, span / wide];
      },
    };
  }
  function cameraTo(target, fitted, delay = 0, fixedMs = 0) {
    const [w, h] = size();
    if (cameraFrame) cancelAnimation(cameraFrame);
    cameraFrame = 0;
const finish = () => { cameraFinish = null; Object.assign(view, { k: target.k, tx: target.tx, ty: target.ty }); viewIsFitted = !!fitted; request(); };
    cameraFinish = finish;
    if (reduceMotion || !w || document.hidden) { finish(); return; }
    const from = { k: view.k, cx: (w / 2 - view.tx) / view.k, cy: (h / 2 - view.ty) / view.k };
    const to = { k: target.k, cx: (w / 2 - target.tx) / target.k, cy: (h / 2 - target.ty) / target.k };
    let duration = fixedMs || Math.min(650, 300 + 120 * Math.abs(Math.log(to.k / from.k) / Math.LN2));
    const flight = fixedMs ? null : flightPath(from, to, Math.max(w, h));
    if (flight) duration = Math.max(duration, Math.min(900, flight.ms));
viewIsFitted = false;
    let start = null;
    const step = (now) => {
      if (start === null) start = now + delay;
      const t = clamp01((now - start) / duration);
      const e = ease(t);
      let k, cx, cy;
      if (flight) [cx, cy, k] = flight.at(e);
      else {
        k = from.k * (to.k / from.k) ** e;
        cx = from.cx + (to.cx - from.cx) * e;
        cy = from.cy + (to.cy - from.cy) * e;
      }
      view.k = k; view.tx = w / 2 - cx * k; view.ty = h / 2 - cy * k;
      request();
      if (t < 1) cameraFrame = animate(step);
      else { cameraFrame = 0; finish(); }
    };
    cameraFrame = animate(step);
  }
  // maxK is a multiple of the fitted scale, so a frame keeps the same
  // context on a laptop and a monitor.
  function frameOf(points, maxK) {
    const [w, h] = size();
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const [x, y] of points) {
      minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
    }
    const pad = 70;
    let k = Math.min((w - pad * 2) / Math.max(1, maxX - minX), (h - pad * 2) / Math.max(1, maxY - minY));
    k = Math.max(fittedK, Math.min(fittedK * maxK, k));
    return { k, tx: w / 2 - k * (minX + maxX) / 2, ty: h / 2 - k * (minY + maxY) / 2 };
  }
  // Choosing never zooms: the camera pans the least distance that brings the
  // chosen object inside the safe rectangle, and only when it is outside.
  function safeRect() {
    const [w, h] = size();
    const r = { x0: 48, x1: w - 48, y0: 48, y1: h - 48 };
    for (const b of chromeBoxes()) {
      if (b.y0 < 64 && b.y1 < h * 0.3) r.y0 = Math.max(r.y0, b.y1 + 12);
      else if (b.y1 > h - 64 && b.y0 > h * 0.7) r.y1 = Math.min(r.y1, b.y0 - 12);
    }
    if (r.y1 - r.y0 < 80) { r.y0 = 48; r.y1 = h - 48; }
    return r;
  }
  function ensureVisible(o) {
    const [w] = size();
    if (!w || !o) return;
    const r = safeRect();
    const x = sx(o.x), y = sy(o.y);
    const dx = x < r.x0 ? r.x0 - x : x > r.x1 ? r.x1 - x : 0;
    const dy = y < r.y0 ? r.y0 - y : y > r.y1 ? r.y1 - y : 0;
    if (!dx && !dy) return;
    cameraTo({ k: view.k, tx: view.tx + dx, ty: view.ty + dy }, false, 0, 320);
  }
  // Focus frames an object's neighbourhood: a component's column with its
  // kernel and name band, a kernel's chain, a rule's glyph with its nearest
  // citers (or the whole map when they stand all round it).
  function focusOn(key) {
    const o = key ? byKey.get(key) : null;
    if (!o) return;
    const pts = [];
    if (o.type === 'core') {
      if (o.centre) { cameraTo(fitTarget(), true, 0, 320); return; }
      for (let a = 0; a < TURN; a += TURN / 8) pts.push(polar(a, R.cores + 70));
      cameraTo(frameOf(pts, 2.4), false, 0, 320);
      return;
    }
    if (o.type === 'component') {
      for (const a of [o.angle - 3 * L.pitch, o.angle, o.angle + 3 * L.pitch]) pts.push(polar(a, R.component - 24), polar(a, R.cap1 + 110));
      if (o.formal) { const kk = kernelObj.get(o.comp.kernelId); if (kk) pts.push([kk.x, kk.y]); }
      cameraTo(frameOf(pts, 3.2), false, 0, 320);
      return;
    }
    if (o.type === 'kernel') {
      pts.push([o.x, o.y], polar(o.angle, o.orbit - 50));
      const c = o.componentId && compObj.get(o.componentId);
      if (c) pts.push([c.x, c.y], polar(c.angle, R.cap1 + 24));
      cameraTo(frameOf(pts, 2.6), false, 0, 320);
      return;
    }
    if (o.type === 'rule') {
      const near5 = o.rule.citedBy.map((id) => compObj.get(id)).filter(Boolean)
        .sort((p, q) => Math.abs(shortArc(o.angle, p.angle)) - Math.abs(shortArc(o.angle, q.angle))).slice(0, 5);
      const spread = Math.max(0, ...near5.map((c) => Math.abs(shortArc(o.angle, c.angle))));
      if (!near5.length || spread > 0.9) { cameraTo(fitTarget(), true, 0, 320); return; }
      pts.push(polar(o.angle, o.orbit + 16), ...near5.map((c) => polar(c.angle, R.cap0)));
      cameraTo(frameOf(pts, 2.6), false, 0, 320);
    }
  }
  /* ---- Focus fade, as on the universe map -------------------------------- */
  let focusMix = 1, focusWas = null, focusHeld = null, focusFade = null, focusFrame = 0;
  function fadeFocus(to, dur, delay) {
    if (reduceMotion) { focusMix = to; focusFade = null; if (to === 0) focusHeld = null; return; }
    focusFade = { from: focusMix, to, dur: Math.max(1, dur), delay, start: null };
    if (!focusFrame) focusFrame = animate(stepFocus);
  }
  function stepFocus(now) {
    focusFrame = 0;
    const f = focusFade;
    if (!f) return;
    if (f.start === null) f.start = now;
    const t = clamp01((now - f.start - f.delay) / f.dur);
    focusMix = f.from + (f.to - f.from) * (1 - (1 - t) * (1 - t));
    if (t < 1) focusFrame = animate(stepFocus);
    else { focusFade = null; if (f.to === 0) focusHeld = null; }
    request();
  }
  // The focus is the chosen object; with nothing chosen, a preview lights
  // its own neighbourhood, softer. A preview over a choice never moves the
  // focus, so it never restarts the chosen object's animations.
  const PREVIEW_MIX = 0.62;
  let focusSoft = false;
  function trackFocus(chosen, preview) {
    const focus = chosen || preview || null;
    const soft = !chosen && !!preview;
    const target = soft ? PREVIEW_MIX : 1;
    if (focus && !focusWas) {
      if (!focusFade) focusMix = 0;
      focusHeld = null;
      fadeFocus(target, FOCUS_IN * Math.max(0.2, 1 - focusMix), 0);
    } else if (!focus && focusWas) {
      focusHeld = focusWas;
      fadeFocus(0, FOCUS_OUT, FOCUS_HOLD);
    } else if (focus && soft !== focusSoft) {
      fadeFocus(target, FOCUS_IN, 0);
    }
    if (focus !== focusWas) {
      startGrowth();
      if (focus) startIgnition(focus);
    }
    if (focus && focus === chosen && focus !== pulsedSelection) { startPulse(focus); pulsedSelection = focus; }
    focusWas = focus;
    focusSoft = soft;
    return focus || focusHeld;
  }
  let pulsedSelection = null;
  const dimmed = (base) => 1 - (1 - base) * focusMix;

  /* ---- Neighbourhoods ----------------------------------------------------- */
  function near(key) {
    const set = new Set();
    if (!key) return set;
    const o = byKey.get(key);
    if (!o) return set;
    set.add(key);
    if (o.type === 'component') {
      for (const w of wiresOf.get(o.id) || []) set.add(`comp:${w}`);
      for (const w of importsOf.get(o.id) || []) set.add(`comp:${w}`);
      if (o.formal) set.add(`kernel:${o.comp.kernelId}`);
      if (replayCore && routed.has(o.id)) set.add(replayCore.key);
      for (const id of o.comp.ruleIds || []) if (ruleObj.has(id)) set.add(`rule:${id}`);
    } else if (o.type === 'rule') {
      // A rule lights exactly the components whose records cite it (for a
      // failure mode, those exposed through the axioms it would break), and
      // the rules it is tied to. Witnesses are a separate relation, never members.
      const r = o.rule;
      for (const id of membersOf(r)) set.add(`comp:${id}`);
      for (const id of [...r.restsOn, ...r.threatens, ...r.principles, ...r.failures]) set.add(`rule:${id}`);
    } else if (o.type === 'kernel') {
      if (o.componentId) set.add(`comp:${o.componentId}`);
    } else if (o.type === 'core' && o.centre) {
      for (const c of compObj.values()) if (routed.has(c.id)) set.add(c.key);
    }
    return set;
  }

  /* ---- Opening ------------------------------------------------------------- */
  let reveal = 1, revealMs = 1e9, revealFrame = 0;
  const revealAlpha = (delay) => (reveal >= 1 ? 1 : 1 - 2 ** (-10 * clamp01((revealMs - delay) / REVEAL.fade)));
  const threadReach = () => (reveal >= 1 ? 1 : ease(clamp01((revealMs - REVEAL.threads) / REVEAL.threadDur)));
  const spokeReach = () => (reveal >= 1 ? 1 : ease(clamp01((revealMs - REVEAL.spokes) / REVEAL.spokeDur)));
  // Share of the way round the ring, clockwise from the key wedge.
  const share = (angle) => ((((angle + Math.PI / 2 - KEY_GAP / 2) % TURN) + TURN) % TURN) / (TURN - KEY_GAP);
  function penAt(angle, lag = 0) {
    if (reveal >= 1) return 1;
    const pen = (revealMs - REVEAL.pen - lag) / REVEAL.penDur;
    const t = (pen - share(angle)) / 0.08;
    return t <= 0 ? 0 : t >= 1 ? 1 : 1 - (1 - t) ** 3;
  }
  function trackPen(angle, i) {
    if (reveal >= 1) return 1;
    const t = (revealMs - REVEAL.tracks - i * REVEAL.trackLag) / REVEAL.trackDur;
    return t <= 0 ? 0 : t >= 1 ? 1 : 1 - (1 - t) ** 2;
  }
  function settleReveal() {
    if (reveal >= 1) return;
    reveal = 1;
    requestFull();
  }
  function startReveal() {
    if (reduceMotion || document.hidden) { reveal = 1; request(); return; }
    reveal = 0; revealMs = 0;
    let start = null;
    const step = (now) => {
      revealFrame = 0;
      if (start === null) start = now;
      revealMs = now - start;
      if (revealMs >= REVEAL.end) reveal = 1;
      request();
      if (reveal < 1) revealFrame = animate(step);
    };
    revealFrame = animate(step);
  }

  /* ---- Lit lines grow out from the focus ----------------------------------- */
  let growth = 1, growthFrame = 0;
  function startGrowth() {
    if (reduceMotion) { growth = 1; return; }
    growth = 0;
    let start = null;
    if (growthFrame) cancelAnimation(growthFrame);
    const step = (now) => {
      growthFrame = 0;
      if (start === null) start = now;
      growth = ease(clamp01((now - start) / GROW_MS));
      request();
      if (growth < 1) growthFrame = animate(step);
    };
    growthFrame = animate(step);
  }

  /* ---- Tweens: short, finite effects that settle exactly -------------------- */
  // Each named tween runs for its duration; once it has run, `elapsed` reads
  // Infinity, so every effect computed from it lands on its final value.
  const tweens = new Map();
  let tweenFrame = 0, clock = 0;
  function kick(name, dur) {
    if (reduceMotion || document.hidden) { tweens.delete(name); return; }
    tweens.set(name, { start: null, dur });
    if (!tweenFrame) tweenFrame = animate(stepTweens);
  }
  function stepTweens(now) {
    tweenFrame = 0;
    clock = now;
    for (const [name, t] of [...tweens]) {
      if (t.start === null) t.start = now;
      else if (now - t.start >= t.dur) tweens.delete(name);
    }
    request();
    if (tweens.size) tweenFrame = animate(stepTweens);
  }
  const elapsed = (name) => { const t = tweens.get(name); return !t ? Infinity : t.start === null ? 0 : clock - t.start; };

  /* ---- Cap ignition ---------------------------------------------------------- */
  // A chosen rule's caps light in order of angular distance from its glyph:
  // up to 220 ms of stagger, each over 140 ms with a 1.25x flash that settles.
  // `sweepMs` keeps the rule glyph's flare in step.
  const IGNITE_STAGGER = 220, IGNITE_FADE = 140, ROUTE_DRAW = 220, ALIDADE_SWING = 380, ALIDADE_FADE = 160;
  const SWEEP_MS = IGNITE_STAGGER, RIPPLE_MS = IGNITE_FADE + 160;
  let sweepMs = 1e9;
  function startIgnition() { kick('ignite', IGNITE_STAGGER + IGNITE_FADE * 1.6); }
  // 0..1.25..1 for one cap whose turn comes `delay` ms in; exactly 1 once done.
  function ignition(delay) {
    const e = elapsed('ignite');
    if (e === Infinity) return 1;
    const t = (e - delay) / IGNITE_FADE;
    if (t <= 0) return 0;
    if (t >= 1) return 1;
    return t < 0.55 ? 1.25 * (t / 0.55) : 1.25 - 0.25 * ((t - 0.55) / 0.45);
  }
  /* ---- The evidence pulse ------------------------------------------------- */
  // A chosen component sends beads where its checks run: inward along its
  // thread to its kernel, which answers, and along its replay spoke to the
  // admission core. A chosen kernel sends beads out along its thread to the
  // component that calls it. The admission core sends a bead down every spoke.
  const pulse = { key: null, ms: 1e9, frame: 0, legs: [], blooms: [], end: 0 };
  const spokeOf = (c) => [polar(c.angle, R.component - 10), polar(c.angle, 22)];
  function startPulse(key) {
    if (pulse.frame) cancelAnimation(pulse.frame);
    pulse.frame = 0; pulse.key = key; pulse.ms = 1e9;
    if (!key || reduceMotion || document.hidden) return;
    const o = byKey.get(key);
    const legs = [];
    const blooms = [];
    if (o.type === 'component') {
      if (o.formal) {
        const k = kernelObj.get(o.comp.kernelId);
        legs.push({ pts: [...k.thread].reverse(), delay: PULSE_WAIT, dur: PULSE_TRAVEL, ink: 'red' });
        blooms.push({ key: k.key, at: PULSE_WAIT + PULSE_TRAVEL });
      }
      if (replayCore && routed.has(o.id)) {
        legs.push({ pts: spokeOf(o), delay: PULSE_WAIT + PULSE_STAGGER, dur: PULSE_TRAVEL * 1.1, ink: 'stated' });
        blooms.push({ key: replayCore.key, at: PULSE_WAIT + PULSE_STAGGER + PULSE_TRAVEL * 1.1, ink: 'stated' });
      }
    } else if (o.type === 'kernel') {
      if (o.thread.length) {
        legs.push({ pts: o.thread, delay: PULSE_WAIT, dur: PULSE_TRAVEL, ink: 'red' });
        blooms.push({ key: `comp:${o.componentId}`, at: PULSE_WAIT + PULSE_TRAVEL });
      }
    } else if (o.type === 'core' && o.centre) {
      let i = 0;
      for (const c of compObj.values()) {
        if (!routed.has(c.id)) continue;
        legs.push({ pts: [...spokeOf(c)].reverse(), delay: PULSE_WAIT + (i % 6) * PULSE_STAGGER, dur: PULSE_TRAVEL * 1.1, ink: 'stated' });
        i += 1;
      }
    }
    pulse.legs = legs;
    pulse.blooms = blooms;
    pulse.end = Math.max(CHOSEN_RING, ...legs.map((l) => l.delay + l.dur), ...blooms.map((b) => b.at + PULSE_BLOOM));
    pulse.ms = 0;
    let start = null;
    const step = (now) => {
      if (start === null) start = now;
      pulse.ms = now - start;
      pulse.frame = pulse.ms < pulse.end ? animate(step) : 0;
      request();
    };
    pulse.frame = animate(step);
  }

  /* ---- Drawing helpers ----------------------------------------------------- */
  const sx = (x) => x * view.k + view.tx;
  const sy = (y) => y * view.k + view.ty;
  function rScale() {
    const [w, h] = size();
    const small = Math.min(w, h) < 520 ? 0.78 : 1;
    return small * Math.min(2.2, Math.max(0.85, Math.sqrt(view.k / fittedK)));
  }
  function alongPath(pts, t) {
    if (pts.length < 2) return pts[0] || [0, 0];
    let total = 0;
    const segs = [];
    for (let i = 1; i < pts.length; i += 1) {
      const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      segs.push(d); total += d;
    }
    let left = t * total;
    for (let i = 0; i < segs.length; i += 1) {
      if (left <= segs[i] || i === segs.length - 1) {
        const f = segs[i] ? Math.min(1, left / segs[i]) : 0;
        return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f];
      }
      left -= segs[i];
    }
    return pts[pts.length - 1];
  }
  // A polyline through world points with each corner turned on a radius of
  // up to `px` screen pixels (never more than half of either leg).
  function strokeRounded(pts, px) {
    if (pts.length < 2) return;
    const q = pts.map(([x, y]) => [sx(x), sy(y)]);
    ctx.beginPath();
    ctx.moveTo(q[0][0], q[0][1]);
    for (let i = 1; i < q.length - 1; i += 1) {
      const [ax, ay] = q[i - 1], [bx, by] = q[i], [cx2, cy2] = q[i + 1];
      const r = Math.min(px, Math.hypot(bx - ax, by - ay) / 2, Math.hypot(cx2 - bx, cy2 - by) / 2);
      if (r > 0.5) ctx.arcTo(bx, by, cx2, cy2, r); else ctx.lineTo(bx, by);
    }
    ctx.lineTo(q[q.length - 1][0], q[q.length - 1][1]);
    ctx.stroke();
  }
  function strokePath(pts, upto = 1) {
    if (pts.length < 2) return;
    ctx.beginPath();
    ctx.moveTo(sx(pts[0][0]), sy(pts[0][1]));
    if (upto >= 1) {
      for (let i = 1; i < pts.length; i += 1) ctx.lineTo(sx(pts[i][0]), sy(pts[i][1]));
    } else {
      const n = 24;
      for (let i = 1; i <= n; i += 1) {
        const p = alongPath(pts, (i / n) * upto);
        ctx.lineTo(sx(p[0]), sy(p[1]));
      }
    }
    ctx.stroke();
  }
  function drawGlow(x, y, radius, color, alpha) {
    if (alpha <= 0.002 || radius <= 0) return;
    const sprite = glowSprite(color);
    if (!sprite) return;
    ctx.globalAlpha = Math.min(1, alpha);
    ctx.drawImage(sprite, x - radius, y - radius, radius * 2, radius * 2);
  }
  // The system map's five marks (system-map.js GLYPHS), drawn at radius r.
  function drawBacking(x, y, r, backing, color) {
    ctx.fillStyle = color;
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(1.1, r * 0.32);
    ctx.beginPath();
    switch (backing) {
      case 'tool':
        ctx.arc(x, y, r, 0, TURN); ctx.fill(); break;
      case 'bounded':
        ctx.arc(x, y, r * 0.87, 0, TURN); ctx.stroke();
        ctx.beginPath(); ctx.arc(x, y, r * 0.87, -Math.PI / 2, Math.PI / 2); ctx.closePath(); ctx.fill(); break;
      case 'import': {
        const s = r * 0.9;
        if (ctx.roundRect) ctx.roundRect(x - s, y - s, s * 2, s * 2, r * 0.24); else ctx.rect(x - s, y - s, s * 2, s * 2);
        ctx.fill(); break;
      }
      case 'contract':
        ctx.arc(x, y, r * 0.87, 0, TURN); ctx.stroke();
        ctx.beginPath(); ctx.arc(x, y, r * 0.38, 0, TURN); ctx.fill(); break;
      case 'computes':
        ctx.arc(x, y, r * 0.87, 0, TURN); ctx.stroke(); break;
      default:
        ctx.arc(x, y, r * 0.45, 0, TURN); ctx.fill();
    }
  }
  // A verified computation as a proof dial, engraved like an instrument
  // scale: a red ring (the proved computation) graduated with one fine tick
  // per passed proof check (the exact count), round a blue ring (its written
  // rules) and a red centre dot (the checked code). Large enough, the count is
  // written as a numeral in the centre, in the code's red. Each deliberately
  // broken copy the prover rejected is a small cross on an arc just outside
  // the ring, away from the stem; more than DIAL.maxCrosses are written ×M.
  // Too fine for distinct ticks, the graduation is a faint band (the count is
  // in the panel). The dial opens as a whole: nothing accumulates tick by tick.
  const flowerOf = (o) => flowerPx(view.k, { replay: o.type === 'core' && !!o.centre, mutants: o.mutants });
  // Crosses stand opposite the stem: inward for a kernel (its stem runs out),
  // outward for a toolkit core, upward for the centre.
  const crossDirOf = (o) => (o.type === 'kernel' ? o.angle + Math.PI : o.centre ? -Math.PI / 2 : o.angle);
  function drawFlower(o, x, y, len, alpha, bloomAt) {
    if (alpha <= 0.002 || len <= 0) return;
    const unfold = reveal >= 1 ? 1 : ease(clamp01((revealMs - bloomAt) / 420));
    if (unfold <= 0) return;
    const f = flowerOf(o);
    const n = o.tasks;
    const r = len * (0.7 + 0.3 * unfold);
    const a = alpha * unfold;
    const glow = darkGround;
    const ringW = Math.max(0.9, Math.min(1.6, r * 0.085));
    // The face: ground inside the ring, so spokes and stems stop at its edge.
    ctx.globalAlpha = a;
    ctx.fillStyle = palette.ground;
    ctx.beginPath(); ctx.arc(x, y, r, 0, TURN); ctx.fill();
    if (glow) {
      ctx.globalCompositeOperation = 'lighter';
      drawGlow(x, y, r * 1.05, palette.red, a * 0.22);
      ctx.globalCompositeOperation = 'source-over';
    }
    // The graduation: N ticks inward from the ring, one per passed check,
    // the first at 12 o'clock.
    const tickIn = Math.max(1.4, r * 0.26);
    const lit = o.key === selected || o.key === hover;
    if (n > 0) {
      ctx.strokeStyle = palette.red;
      if ((TURN * (r - tickIn / 2)) / n >= 1.7) {
        const fine = Math.max(hairPx, Math.min(0.9, r * 0.05));
        ctx.lineWidth = fine;
        ctx.globalAlpha = a * (lit ? 1 : 0.85);
        ctx.beginPath();
        for (let i = 0; i < n; i += 1) {
          if (i % 5 === 0 && n > 5) continue;
          const t = -Math.PI / 2 + (i / n) * TURN, c = Math.cos(t), sn = Math.sin(t);
          ctx.moveTo(x + c * (r - tickIn), y + sn * (r - tickIn)); ctx.lineTo(x + c * r, y + sn * r);
        }
        ctx.stroke();
        if (n > 5) {
          // Every fifth check, a longer, firmer tick: 41 reads as eight
          // fives and one.
          ctx.lineWidth = fine * 1.7;
          ctx.beginPath();
          for (let i = 0; i < n; i += 5) {
            const t = -Math.PI / 2 + (i / n) * TURN, c = Math.cos(t), sn = Math.sin(t);
            ctx.moveTo(x + c * (r - tickIn * 1.55), y + sn * (r - tickIn * 1.55)); ctx.lineTo(x + c * r, y + sn * r);
          }
          ctx.stroke();
        }
        if (r >= 9) {
          // The graduation's inner track, a hair inside the ticks.
          ctx.lineWidth = hairPx;
          ctx.globalAlpha = a * 0.3;
          ctx.beginPath(); ctx.arc(x, y, r - tickIn - 0.8, 0, TURN); ctx.stroke();
        }
      } else {
        ctx.lineWidth = tickIn;
        ctx.globalAlpha = a * 0.32;
        ctx.beginPath(); ctx.arc(x, y, r - tickIn / 2, 0, TURN); ctx.stroke();
      }
    }
    ctx.strokeStyle = palette.red;
    ctx.lineWidth = ringW;
    ctx.globalAlpha = a * 0.95;
    ctx.beginPath(); ctx.arc(x, y, r, 0, TURN); ctx.stroke();
    if (r >= 6) {
      // An engraved second rim just outside, as on a gauge's bezel; firmer
      // on the dial pointed at or chosen.
      ctx.lineWidth = hairPx * (lit ? 1.6 : 1);
      ctx.globalAlpha = a * (lit ? 0.75 : 0.32);
      ctx.beginPath(); ctx.arc(x, y, r + Math.max(1.5, r * 0.13), 0, TURN); ctx.stroke();
    }
    // The written rules (blue ring) round the code (red dot, or the count).
    const numeral = r >= DIAL.numeral && n > 0;
    const inner = numeral ? r * 0.58 : Math.max(1.6, r * 0.46);
    ctx.lineWidth = Math.max(0.8, Math.min(1.3, r * 0.07));
    ctx.strokeStyle = palette.stated;
    ctx.globalAlpha = a;
    ctx.beginPath(); ctx.arc(x, y, inner, 0, TURN); ctx.stroke();
    if (numeral) {
      const text = String(n);
      let px = Math.min(11.5, inner * 1.15);
      ctx.font = face(700, px, false, SANS);
      const wd = ctx.measureText(text).width;
      if (wd > inner * 1.55) { px *= (inner * 1.55) / wd; ctx.font = face(700, px, false, SANS); }
      ctx.fillStyle = palette.red;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(text, x, y + px * 0.04);
    } else {
      ctx.beginPath(); ctx.arc(x, y, Math.max(1.1, inner * 0.42), 0, TURN);
      ctx.fillStyle = palette.red; ctx.fill();
    }
    const m = o.mutants;
    if (m) {
      const cr = f.crossR - f.r + r, half = f.half;
      const dir = crossDirOf(o);
      ctx.strokeStyle = palette.ink;
      ctx.fillStyle = palette.ink;
      ctx.lineWidth = Math.max(0.8, 0.9 * f.s);
      ctx.lineCap = 'round';
      ctx.globalAlpha = alpha * 0.85 * unfold;
      if (m > DIAL.maxCrosses) {
        // ×M on the cross side, level type.
        const px = Math.max(6.5, 9 * f.s);
        ctx.font = face(600, px, false, SANS);
        const text = `×${m}`;
        const wd = ctx.measureText(text).width;
        const c = Math.cos(dir), sn = Math.sin(dir);
        // Push the box's centre out until its near edge clears the ring.
        const reachBox = Math.abs(c) * wd / 2 + Math.abs(sn) * px / 2;
        const d = r + DIAL.crossGap * f.s + reachBox;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, x + c * d, y + sn * d);
      } else {
        const step = (DIAL.crossPitch * f.s) / cr;
        ctx.beginPath();
        for (let i = 0; i < m; i += 1) {
          const ang = dir + (i - (m - 1) / 2) * step;
          const mx = x + Math.cos(ang) * cr, my = y + Math.sin(ang) * cr;
          ctx.moveTo(mx - half, my - half); ctx.lineTo(mx + half, my + half);
          ctx.moveTo(mx + half, my - half); ctx.lineTo(mx - half, my + half);
        }
        ctx.stroke();
      }
    }
    ctx.lineCap = 'butt';
    ctx.globalAlpha = 1;
  }
  // Dial radius in px: min(cap, 12·k); zoom never inflates it further. The
  // second argument is ignored (kept for callers that pass rScale()).
  const petalPx = (o) => flowerOf(o).r;
  /**
   * Every flower's footprint in screen px, for the current view: petal
   * radius + cross ring + 6 px of air (layout.js flowerPx). The same measure
   * spaces the flowers (bloomDepths), sizes their hit targets and keeps the
   * kernel and core names off them; the label planner reads it here too.
   * Returns [{ key, x, y, r, reach, crossDir, crossSpan }], where reach is the
   * drawn extent (petals and crosses) and crossDir/crossSpan say where the
   * crosses stand (radians).
   */
  function flowerFootprints() {
    const out = [];
    for (const o of [...coreObj.values(), ...kernelObj.values()]) {
      const f = flowerOf(o);
      out.push({ key: o.key, x: sx(o.x), y: sy(o.y), r: f.footprint, reach: f.reach, petal: f.r,
        crossDir: crossDirOf(o), crossSpan: crossSpan(view.k, o.mutants) });
    }
    return out;
  }
  // A kernel's name stays inside the component band, never over its marks.
  function insideRing(box) {
    const limit = (R.component - 22) * view.k;
    for (const [x, y] of [[box.x0, box.y0], [box.x1, box.y0], [box.x0, box.y1], [box.x1, box.y1]]) {
      if (Math.hypot(x - view.tx, y - view.ty) > limit) return false;
    }
    return true;
  }
  function boxHit(box) {
    for (const p of labelBoxes) {
      if (box.x0 < p.x1 - 2 && box.x1 > p.x0 + 2 && box.y0 < p.y1 - 2 && box.y1 > p.y0 + 2) return true;
    }
    return false;
  }
  function textWithHalo(text, x, y, font, color, alpha, align = 'center', baseline = 'middle') {
    ctx.font = font;
    ctx.textAlign = align;
    ctx.textBaseline = baseline;
    ctx.lineJoin = 'round';
    ctx.lineWidth = 3.2;
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = palette.ground;
    ctx.strokeText(text, x, y);
    ctx.fillStyle = color;
    ctx.fillText(text, x, y);
  }
  const arcCache = new Map();
  function arcLetters(text) {
    const key = `${ctx.font}|${text}`;
    if (arcCache.has(key)) return arcCache.get(key);
    const out = { width: ctx.measureText(text).width, letters: [] };
    for (let i = 0; i < text.length; i += 1) {
      const ch = text.charAt(i);
      if (ch === ' ') continue;
      out.letters.push([ch, ctx.measureText(text.slice(0, i)).width + ctx.measureText(ch).width / 2]);
    }
    arcCache.set(key, out);
    return out;
  }
  // Upright text along a circle about the centre: the upper half reads
  // clockwise, the lower half anticlockwise, so neither runs upside down.
  // `register` (default true) files its footprint in labelBoxes; text placed
  // by the planner passes false, since the planner files it.
  function drawArcText(text, font, color, alpha, radius, mid, lower, halo = true, register = true) {
    ctx.font = font;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = 3;
    ctx.lineJoin = 'round';
    const dir = lower ? -1 : 1;
    const run = arcLetters(text);
    const at = mid - dir * (run.width / radius) / 2;
    // Each letter is placed with one setTransform composed onto the current
    // matrix (no save/restore per letter); style and alpha are set per pass.
    const m = ctx.getTransform ? ctx.getTransform() : null;
    const turn = lower ? -Math.PI / 2 : Math.PI / 2;
    const was = [ctx.globalAlpha, ctx.strokeStyle, ctx.fillStyle];
    ctx.globalAlpha = alpha;
    for (let pass = halo ? 0 : 1; pass < 2; pass += 1) {
      if (pass === 0) ctx.strokeStyle = palette.ground; else ctx.fillStyle = color;
      for (const [ch, offset] of run.letters) {
        const angle = at + dir * offset / radius;
        const x = view.tx + radius * Math.cos(angle), y = view.ty + radius * Math.sin(angle);
        if (m) {
          const cs = Math.cos(angle + turn), sn = Math.sin(angle + turn);
          ctx.setTransform(m.a * cs + m.c * sn, m.b * cs + m.d * sn, m.c * cs - m.a * sn, m.d * cs - m.b * sn, m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f);
          if (pass === 0) ctx.strokeText(ch, 0, 0); else ctx.fillText(ch, 0, 0);
        } else {
          ctx.save();
          ctx.translate(x, y);
          ctx.rotate(angle + turn);
          if (pass === 0) ctx.strokeText(ch, 0, 0); else ctx.fillText(ch, 0, 0);
          ctx.restore();
        }
      }
    }
    if (m) ctx.setTransform(m);
    [ctx.globalAlpha, ctx.strokeStyle, ctx.fillStyle] = was;
    if (!register) return;
    const span = run.width / radius;
    const steps = Math.max(1, Math.ceil(span * radius / 10));
    for (let e = 0; e <= steps; e += 1) {
      const a = mid - span / 2 + span * e / steps;
      const ex = view.tx + radius * Math.cos(a), ey = view.ty + radius * Math.sin(a);
      labelBoxes.push({ x0: ex - 9, x1: ex + 9, y0: ey - 9, y1: ey + 9 });
    }
  }
  // One cell: an annular sector of the component's slot, less a fixed gap.
  function cellPath(angle, halfAngle, gap, r0, r1) {
    const k = view.k;
    const h1 = halfAngle - gap / r1, h0 = halfAngle - gap / r0;
    ctx.beginPath();
    ctx.arc(view.tx, view.ty, r1 * k, angle - h1, angle + h1);
    ctx.arc(view.tx, view.ty, r0 * k, angle + h0, angle - h0, true);
    ctx.closePath();
  }

  /* ---- Paint ------------------------------------------------------------- */
  // Advance every active effect before a single canvas paint. A callback
  // queued while advancing belongs to the next display frame, just like RAF.
  function animate(callback) {
    if (destroyed) return 0;
    const id = nextAnimation++;
    animations.set(id, callback);
    request();
    return id;
  }
  function cancelAnimation(id) { animations.delete(id); }
  function request() {
    if (destroyed) return;
    paintRequested = true;
    if (!frame && !advancing) frame = requestAnimationFrame(drawFrame);
  }
  function drawFrame(now) {
    frame = 0;
    if (destroyed) return;
    advancing = true;
    try {
      for (const [id, callback] of [...animations]) {
        if (!animations.delete(id)) continue;
        callback(now);
      }
      paintRequested = false;
      paintNow();
    } finally {
      advancing = false;
      if (paintRequested || animations.size) request();
    }
  }
  /* ---- Interaction bitmap cache ------------------------------------------ */
  // While the user drags, pinches or wheels (and while a camera flight runs
  // with no other effect in play), a frame is the last crisp full frame from
  // an offscreen copy, moved and scaled by the camera delta: one drawImage.
  // The ground shows through where the copy does not reach (the canvas is
  // transparent over the stage's own ground). A crisp full paint runs
  // SETTLE_MS after the last input, mid-gesture whenever the copy has been
  // scaled outside [SNAP_MIN, SNAP_MAX] or leaves too wide a strip uncovered,
  // and always after a change of choice, preview, focus, matches, emphasis,
  // wiring, palette or fonts (requestFull). Hit testing reads the camera, not
  // the bitmap, so hover keeps working throughout.
  const SETTLE_MS = 120, SNAP_MIN = 0.6, SNAP_MAX = 1.7, SNAP_EDGE = 0.16;
  const snap = { canvas: null, ctx: null, valid: false, k: 1, tx: 0, ty: 0, bw: 0, bh: 0 };
  const painted = { k: 1, tx: 0, ty: 0, bw: 0, bh: 0, full: false };
  const stats = { full: 0, blit: 0, last: 'none' };
  let gesturing = false, settleTimer = 0, needFull = true;
  function requestFull() { needFull = true; request(); }
  function markGesture() {
    if (destroyed) return;
    gesturing = true;
    if (settleTimer) clearTimeout(settleTimer);
    settleTimer = setTimeout(endGesture, SETTLE_MS);
  }
  function endGesture() {
    settleTimer = 0;
    gesturing = false;
    if (destroyed) return;
    requestFull();
  }
  // Effects that change the picture itself, not just the camera.
  const effectsActive = () => !!focusFade || growth < 1 || tweens.size > 0 || pulse.ms < pulse.end || reveal < 1;
  function takeSnap() {
    if (!painted.full) return false;
    if (!snap.canvas) {
      snap.canvas = typeof document !== 'undefined' && document.createElement ? document.createElement('canvas') : null;
      snap.ctx = snap.canvas && snap.canvas.getContext ? snap.canvas.getContext('2d') : null;
      if (!snap.ctx) { snap.canvas = null; return false; }
    }
    if (snap.canvas.width !== painted.bw || snap.canvas.height !== painted.bh) { snap.canvas.width = painted.bw; snap.canvas.height = painted.bh; }
    const g = snap.ctx;
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.globalAlpha = 1;
    g.globalCompositeOperation = 'copy';
    g.drawImage(canvas, 0, 0);
    g.globalCompositeOperation = 'source-over';
    Object.assign(snap, { valid: true, k: painted.k, tx: painted.tx, ty: painted.ty, bw: painted.bw, bh: painted.bh });
    return true;
  }
  // One cached frame, or false when only a full paint will do.
  function blitNow(w, h, bw, bh) {
    if (canvas.width !== bw || canvas.height !== bh) return false;
    if (!snap.valid && !takeSnap()) return false;
    if (snap.bw !== bw || snap.bh !== bh) return false;
    const s = view.k / snap.k;
    if (!(s >= SNAP_MIN && s <= SNAP_MAX)) return false;
    const dx = view.tx - snap.tx * s, dy = view.ty - snap.ty * s;
    const edge = SNAP_EDGE * Math.min(w, h);
    if (dx > edge || dy > edge || w - (dx + w * s) > edge || h - (dy + h * s) > edge) return false;
    ctx.setTransform(bw / (w || 1), 0, 0, bh / (h || 1), 0, 0);
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
    ctx.clearRect(0, 0, w, h);
    ctx.drawImage(snap.canvas, 0, 0, snap.bw, snap.bh, dx, dy, w * s, h * s);
    painted.full = false;
    stats.blit += 1; stats.last = 'blit';
    return true;
  }
  function paintNow() {
    if (destroyed) return;
    if (!onScreen || document.hidden) return;
    const explored = !viewIsFitted;
    if (stage && stage.classList.contains('is-explored') !== explored) {
      stage.classList.toggle('is-explored', explored);
      invalidateGeometry();
    }
    if (!needFull && (gesturing || (cameraFrame && !effectsActive()))) {
      const dprB = Math.min(window.devicePixelRatio || 1, 2);
      const [wB, hB] = size();
      if (blitNow(wB, hB, Math.round(wB * dprB), Math.round(hB * dprB))) return;
    }
    needFull = false;
    paintFull();
    snap.valid = false;
    stats.full += 1; stats.last = 'full';
  }
  function paintFull() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const [w, h] = size();
    const bw = Math.round(w * dpr), bh = Math.round(h * dpr);
    if (canvas.width !== bw || canvas.height !== bh) { canvas.width = bw; canvas.height = bh; }
    ctx.setTransform(bw / (w || 1), 0, 0, bh / (h || 1), 0, 0);
    hairPx = 1 / dpr;
    ctx.clearRect(0, 0, w, h);
    if ('fontKerning' in ctx) ctx.fontKerning = 'normal';
    labelBoxes = chromeBoxes().map((b) => ({ x0: b.x0 - 4, x1: b.x1 + 4, y0: b.y0 - 4, y1: b.y1 + 4 }));
    sweepMs = Math.min(1e9, elapsed('ignite'));

    // Chosen owns the lit set; a preview only adds a comparison (or, with
    // nothing chosen, lights its own neighbourhood, softer).
    const chosen = selected && byKey.has(selected) ? selected : null;
    const preview = hover && hover !== chosen && byKey.has(hover) ? hover : null;
    const focus = trackFocus(chosen, preview);
    const lit = near(focus);
    const previewLit = chosen ? near(preview) : new Set();
    const rs = rScale();
    const fo = focus ? byKey.get(focus) : null;
    const cmp = chosen && preview ? byKey.get(preview) : null; // the comparison
    planRoutesFor(fo, cmp, rs);
    ins = cachedInscriptions(focus, rs, w, h);
    const shown = (c) => !matches || matches.has(c.id);
    const fade = (key) => (focus && !lit.has(key) ? dimmed(0.22) : 1);
    const members = fo && fo.type === 'rule' ? new Set(membersOf(fo.rule)) : null;
    Object.assign(shared, { chosen, preview, focus, lit, previewLit, members, relation: relationOf(chosen ? byKey.get(chosen) : null, cmp) });

    drawDepth(w, h);
    drawBezel();
    drawOrbits();
    drawAlidade(chosen, preview);
    drawSpokes(focus, lit, shown, cmp);
    drawWiring(focus, shown, cmp);
    drawThreads(focus, lit, shown, rs);
    if (darkGround) drawEmbers(focus, lit, rs, shown);
    drawTracks(focus, shown, lit, fade, members);
    drawHaloField();
    drawRegister(fo, cmp, shown);
    drawLanes(focus, cmp);
    drawRoutes(fo, cmp, shown, rs);
    drawWedge(focus);
    drawFamilyWords();
    drawRules(focus, rs);
    drawKernels(focus, lit, rs, shown, fade);
    drawCores(focus, lit, rs, fade);
    drawComponents(focus, lit, rs, shown, fade);
    drawAnchorWords(focus, lit, rs);
    drawComponentNames(focus, lit, shown);
    drawPulse(rs);
    drawReticles(rs);
    drawStageChips();
    ctx.globalAlpha = 1;
    Object.assign(painted, { k: view.k, tx: view.tx, ty: view.ty, bw, bh, full: true });
  }

  // What a preview says against the chosen object: a short typed descriptor
  // the panel words (relation.kind is 'cites' | 'not-cites' | 'shared' |
  // 'wired' | 'not-wired' | 'owner' | 'replay-route' | 'no-replay-route' | 'other').
  function relationOf(c, p) {
    if (!c || !p || c === p) return null;
    const rulesOf = (o) => o.comp.ruleIds || [];
    const exposure = (rule, comp) => {
      const through = rule.rule.exposed.get(comp.id) || [];
      return { kind: through.length ? 'exposed' : 'not-exposed', rule: rule.id, component: comp.id, through, axioms: [...rule.rule.threatens] };
    };
    if (c.type === 'rule' && p.type === 'component') return c.rule.kind === 'anti_principle' ? exposure(c, p) : { kind: c.rule.citedBy.includes(p.id) ? 'cites' : 'not-cites', rule: c.id, component: p.id };
    if (c.type === 'component' && p.type === 'rule') return p.rule.kind === 'anti_principle' ? exposure(p, c) : { kind: rulesOf(c).includes(p.id) ? 'cites' : 'not-cites', rule: p.id, component: c.id };
    if (c.type === 'rule' && p.type === 'rule') {
      const pm = new Set(membersOf(p.rule));
      const count = membersOf(c.rule).filter((id) => pm.has(id)).length;
      const direct = c.rule.restsOn.includes(p.id) || p.rule.restsOn.includes(c.id) ? 'rests-on'
        : c.rule.threatens.includes(p.id) || p.rule.threatens.includes(c.id) ? 'threatens' : null;
      return { kind: 'shared', count, direct, rules: [c.id, p.id] };
    }
    if (c.type === 'component' && p.type === 'component') {
      const wired = (wiresOf.get(c.id) || []).includes(p.id);
      const imports = (importsOf.get(c.id) || []).includes(p.id);
      const count = rulesOf(c).filter((id) => rulesOf(p).includes(id)).length;
      return { kind: wired || imports ? 'wired' : 'not-wired', imports, count };
    }
    if (c.type === 'kernel' && p.type === 'component') return { kind: c.componentId === p.id ? 'owner' : 'other' };
    if (c.type === 'core' && c.centre && p.type === 'component') return { kind: routed.has(p.id) ? 'replay-route' : 'no-replay-route' };
    return { kind: 'other' };
  }

  /* ---- The alidade --------------------------------------------------------- */
  // A hairline pointer arm across the whole instrument, aimed at the chosen
  // object's angle, with an index notch at the bezel and a counterweight tick
  // opposite. It swings by the shortest rotation; the centre core has no
  // angle, so the arm fades. A preview shows a ghost arm.
  const alid = { key: null, on: false, from: 0, to: 0 };
  function angleFor(o) {
    if (!o) return null;
    if (o.type === 'component' || o.type === 'rule') return o.angle;
    if (o.type === 'kernel' && o.componentId && compObj.has(o.componentId)) return compObj.get(o.componentId).angle;
    return null;
  }
  const alidadeAngle = () => {
    const e = elapsed('alidade');
    const t = e === Infinity ? 1 : clamp01(e / ALIDADE_SWING);
    return alid.from + (alid.to - alid.from) * ease(t);
  };
  function aimAlidade(key) {
    const a = angleFor(key ? byKey.get(key) : null);
    if (a === null) { if (alid.on) { alid.on = false; kick('alidade-fade', ALIDADE_FADE); } return; }
    if (!alid.on) {
      const wasShowing = elapsed('alidade-fade') !== Infinity;
      alid.on = true;
      kick('alidade-fade', ALIDADE_FADE);
      if (!wasShowing) { alid.from = alid.to = a; tweens.delete('alidade'); return; }
    }
    const now = alidadeAngle();
    alid.from = now;
    alid.to = now + shortArc(now, a);
    kick('alidade', ALIDADE_SWING);
  }
  function drawAlidade(chosen, preview) {
    if (chosen !== alid.key) { alid.key = chosen; aimAlidade(chosen); }
    const show = revealAlpha(REVEAL.halo);
    if (show <= 0.01) return;
    const k = view.k;
    const outer = halo ? R.haloOuter : R.labels;
    const rIn = (outer + 6) * k, rOut = (outer + 14) * k;
    const line = (cs, sn) => {
      ctx.beginPath();
      ctx.moveTo(view.tx - cs * rOut, view.ty - sn * rOut);
      ctx.lineTo(view.tx + cs * rOut, view.ty + sn * rOut);
      ctx.stroke();
    };
    const arm = (ang, alpha, ghost) => {
      if (alpha <= 0.005) return;
      const cs = Math.cos(ang), sn = Math.sin(ang);
      const nx = -sn, ny = cs;
      ctx.save();
      if (darkGround) {
        // The glow is two wide, faint under-strokes added in light (no
        // shadow blur: a blur re-rasterises the whole arm every frame).
        ctx.globalCompositeOperation = 'lighter';
        ctx.strokeStyle = palette.doctrine;
        ctx.fillStyle = palette.doctrine;
        ctx.lineCap = 'round';
        ctx.globalAlpha = alpha * 0.06; ctx.lineWidth = 6; line(cs, sn);
        ctx.globalAlpha = alpha * 0.11; ctx.lineWidth = 2.6; line(cs, sn);
        ctx.lineCap = 'butt';
        ctx.globalAlpha = alpha * 0.42;
      } else {
        ctx.strokeStyle = palette.ink;
        ctx.fillStyle = palette.ink;
        ctx.globalAlpha = alpha * 0.26;
      }
      ctx.lineWidth = darkGround ? 0.9 : Math.max(hairPx, 0.6);
      line(cs, sn);
      // Index notch: a fine wedge at the bezel, pointing in.
      if (darkGround) drawGlow(view.tx + cs * rOut, view.ty + sn * rOut, 11, palette.doctrine, alpha * (ghost ? 0.25 : 0.55));
      ctx.globalAlpha = alpha * (darkGround ? 0.85 : 0.75) * (ghost ? 0.6 : 1);
      ctx.beginPath();
      ctx.moveTo(view.tx + cs * (rIn - 3), view.ty + sn * (rIn - 3));
      ctx.lineTo(view.tx + cs * rOut + nx * 3.4, view.ty + sn * rOut + ny * 3.4);
      ctx.lineTo(view.tx + cs * rOut - nx * 3.4, view.ty + sn * rOut - ny * 3.4);
      ctx.closePath();
      ctx.fill();
      // Counterweight: a short bar across the arm on the far side.
      const rc = (rIn + rOut) / 2;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(view.tx - cs * rc + nx * 4, view.ty - sn * rc + ny * 4);
      ctx.lineTo(view.tx - cs * rc - nx * 4, view.ty - sn * rc - ny * 4);
      ctx.stroke();
      ctx.restore();
    };
    const f = elapsed('alidade-fade');
    const t = f === Infinity ? 1 : clamp01(f / ALIDADE_FADE);
    const alpha = alid.on ? t : 1 - t;
    if (alpha > 0) {
      const ang = alidadeAngle();
      // While it swings, a faint motion trail: a sweep along the bezel from
      // where the arm was a moment ago, and two ghost arms behind it, all
      // gone by the end of the swing.
      const e = elapsed('alidade');
      if (e !== Infinity && alid.to !== alid.from) {
        const st = clamp01(e / ALIDADE_SWING);
        const fadeOut = (1 - st) ** 1.4;
        const at = (lag) => alid.from + (alid.to - alid.from) * ease(clamp01(st - lag));
        ctx.save();
        if (darkGround) ctx.globalCompositeOperation = 'lighter';
        ctx.strokeStyle = darkGround ? palette.doctrine : palette.ink;
        ctx.lineCap = 'butt';
        const rc = (rIn + rOut) / 2;
        const seg = 6;
        for (let i = 0; i < seg; i += 1) {
          const a0 = at(0.22 * (1 - i / seg)), a1 = at(0.22 * (1 - (i + 1) / seg));
          if (Math.abs(a1 - a0) < 1e-4) continue;
          ctx.globalAlpha = alpha * show * fadeOut * (darkGround ? 0.5 : 0.32) * ((i + 1) / seg);
          ctx.lineWidth = rOut - rIn;
          ctx.beginPath(); ctx.arc(view.tx, view.ty, rc, Math.min(a0, a1), Math.max(a0, a1)); ctx.stroke();
        }
        ctx.lineWidth = darkGround ? 0.8 : Math.max(hairPx, 0.5);
        for (const [lag, g] of [[0.12, 0.16], [0.06, 0.26]]) {
          const ga = at(lag);
          ctx.globalAlpha = alpha * show * fadeOut * g * (darkGround ? 1 : 0.7);
          line(Math.cos(ga), Math.sin(ga));
        }
        ctx.restore();
      }
      arm(ang, alpha * show, false);
    }
    const pa = preview && preview !== chosen ? angleFor(byKey.get(preview)) : null;
    if (pa !== null) arm(pa, 0.25 * show, true);
    ctx.globalAlpha = 1;
  }
  // Smooth radial lights (the centre's depth, the halo's cold light) are
  // painted once per palette into a small sprite and scaled into place: a
  // linear ramp upsampled bilinearly is indistinguishable from the gradient,
  // and one textured quad is far cheaper than shading the gradient over the
  // whole retina backing store every frame.
  const lightSprites = new Map();
  function lightSprite(name, size, stops, inner = 0) {
    const key = `${name}|${palette.ground}|${palette.ink}|${palette.doctrine}`;
    if (lightSprites.has(key)) return lightSprites.get(key);
    if (lightSprites.size > 12) lightSprites.clear();
    let sprite = typeof document !== 'undefined' && document.createElement ? document.createElement('canvas') : null;
    const g = sprite && sprite.getContext ? sprite.getContext('2d') : null;
    if (g && g.createRadialGradient) {
      sprite.width = sprite.height = size;
      const c = size / 2;
      const grad = g.createRadialGradient(c, c, inner * c, c, c, c);
      for (const [at, color] of stops) grad.addColorStop(at, color);
      g.fillStyle = grad;
      g.beginPath(); g.arc(c, c, c, 0, TURN); g.fill();
    } else sprite = null;
    lightSprites.set(key, sprite);
    return sprite;
  }
  function drawLight(sprite, r, alpha) {
    if (!sprite || alpha <= 0.002) return;
    ctx.globalAlpha = alpha;
    ctx.drawImage(sprite, view.tx - r, view.ty - r, r * 2, r * 2);
  }
  // A faint light at the centre, so the drawing has depth without a frame.
  function drawDepth() {
    const r = R.component * view.k;
    if (r < 40) return;
    const tone = parseColor(palette.ink) || [1, 1, 1, 1];
    const rgb = `${Math.round(tone[0] * 255)},${Math.round(tone[1] * 255)},${Math.round(tone[2] * 255)}`;
    const sprite = lightSprite('depth', 256, [[0, `rgba(${rgb},${darkGround ? 0.05 : 0.035})`], [0.55, `rgba(${rgb},${darkGround ? 0.022 : 0.015})`], [1, `rgba(${rgb},0)`]]);
    drawLight(sprite, r * 1.05, revealAlpha(REVEAL.core));
    ctx.globalAlpha = 1;
  }

  // The cores' orbit as a hairline, so the toolkit at the centre reads as
  // one group, apart from the components' own flowers on their stems.
  function drawOrbits() {
    ctx.strokeStyle = palette.edge;
    ctx.lineWidth = hairPx;
    ctx.globalAlpha = 0.6 * revealAlpha(REVEAL.cores);
    ctx.setLineDash([2, 3]);
    ctx.beginPath(); ctx.arc(view.tx, view.ty, R.cores * view.k, 0, TURN); ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
  }

  // Every component's configured replay route, as a hairline spoke to the
  // admission core at the centre. Azure: configured, not run here. With the
  // admission core chosen, every spoke stays faint and the previewed
  // component's spoke is bright.
  function drawSpokes(focus, lit, shown, cmp) {
    if (!replayCore) return;
    const reach = spokeReach();
    if (reach <= 0) return;
    const fo = focus ? byKey.get(focus) : null;
    const all = fo === replayCore;
    const bright = all && cmp && cmp.type === 'component' ? cmp : null;
    const emph = emphasis === 'replay';
    ctx.strokeStyle = palette.stated;
    for (const c of compObj.values()) {
      if (!routed.has(c.id)) continue;
      const own = fo && fo.type === 'component' && fo === c;
      const on = own || bright === c;
      let alpha = on ? 0.78 : all ? 0.26 * focusMix + 0.1 : emph ? 0.32 : darkGround ? 0.085 : 0.11;
      if (fo && !on && !all) alpha *= dimmed(0.5);
      if (!shown(c.comp)) alpha *= 0.3;
      ctx.lineWidth = on ? 1.3 : all ? Math.max(hairPx, 0.7) : hairPx;
      ctx.globalAlpha = alpha;
      const [a, b] = spokeOf(c);
      // The spoke grows out from the centre in the opening.
      strokePath([b, a], reach * (own ? growth : 1));
    }
    ctx.globalAlpha = 1;
  }

  // Declared wiring, bundled round inside the ring: azure, because it is
  // stated in source, not observed in a run, and untyped. Lexical imports
  // between runner modules are drawn solid on top.
  const wirePaths = new Map();
  function wirePath(a, b) {
    const key = `${a.id}|${b.id}`;
    if (wirePaths.has(key)) return wirePaths.get(key);
    const d = shortArc(a.angle, b.angle);
    const depth = Math.min(150, 26 + 150 * Math.abs(d) / Math.PI);
    const r0 = R.component - 9;
    const pts = [];
    for (let i = 0; i <= 28; i += 1) {
      const t = i / 28;
      const r = r0 - depth * (4 * t * (1 - t)) ** 0.8;
      pts.push(polar(a.angle + d * t, r));
    }
    wirePaths.set(key, pts);
    return pts;
  }
  // A chosen component shows its own wiring clearly; every other curve is
  // hidden unless the Wiring toggle is on, when they are a faint aggregate.
  // A previewed component that is wired to the chosen one has its curve
  // drawn heavier.
  function drawWiring(focus, shown, cmp) {
    const fo = focus ? byKey.get(focus) : null;
    const component = fo && fo.type === 'component' ? fo : null;
    const other = component && cmp && cmp.type === 'component' ? cmp : null;
    if (allWiring) {
      ctx.strokeStyle = palette.stated;
      ctx.lineWidth = hairPx * 1.4;
      for (const [x, y] of model.wires) {
        const a = compObj.get(x), b = compObj.get(y);
        if (!a || !b) continue;
        const on = component && (component === a || component === b);
        if (on) continue;
        ctx.globalAlpha = (darkGround ? 0.26 : 0.3) * (component ? dimmed(0.4) : 1) * (shown(a.comp) || shown(b.comp) ? 1 : 0.25);
        strokePath(wirePath(a, b));
      }
    }
    if (!component) return;
    ctx.strokeStyle = palette.stated;
    for (const id of wiresOf.get(component.id) || []) {
      const o = compObj.get(id);
      if (!o) continue;
      const hot = other === o;
      ctx.lineWidth = hot ? 2 : 1.1;
      ctx.globalAlpha = (hot ? 1 : other ? 0.55 : 0.85) * focusMix;
      strokePath(wirePath(component, o), hot ? 1 : growth);
    }
    for (const e of model.imports) {
      if (e.from !== component.id && e.to !== component.id) continue;
      const a = compObj.get(e.from), b = compObj.get(e.to);
      if (!a || !b) continue;
      const hot = other && (other === a || other === b);
      ctx.lineWidth = hot ? 2.2 : 1.7;
      ctx.globalAlpha = 0.95 * focusMix;
      strokePath(wirePath(a, b), hot ? 1 : growth);
    }
    ctx.globalAlpha = 1;
  }
  // Each kernel's stem out to its component, through its generated code
  // (a square at 40% of its length) and its caller (a diamond at 70%): the
  // paper's chain. It leaves the dial at its drawn ring, so it never
  // runs under the dial, and doglegs round a neighbour (layout.js stemFor).
  function subPath(pts, from, to) {
    const out = [];
    let walked = 0;
    for (let i = 1; i < pts.length; i += 1) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
      const d = Math.hypot(x1 - x0, y1 - y0);
      const a = walked, b = walked + d;
      walked = b;
      if (b < from || a > to || !d) continue;
      const t0 = Math.max(0, (from - a) / d), t1 = Math.min(1, (to - a) / d);
      if (!out.length) out.push([x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0]);
      out.push([x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1]);
    }
    return out;
  }
  const pathLength = (pts) => { let t = 0; for (let i = 1; i < pts.length; i += 1) t += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); return t; };
  function drawThreads(focus, lit, shown, rs) {
    const reach = threadReach();
    if (reach <= 0) return;
    const close = view.k >= fittedK * 1.6;
    for (const k of kernelObj.values()) {
      if (!k.thread.length) continue;
      const comp = compObj.get(k.componentId);
      const on = focus && lit.has(k.key) && comp && lit.has(comp.key);
      const off = focus && !on;
      const matchFade = comp && !shown(comp.comp) ? 0.25 : 1;
      const total = k.stemLength ?? (k.stemLength = pathLength(k.thread));
      const skip = (petalPx(k) + 1.5) / view.k;
      const grown = reach * (on ? growth : 1);
      const end = (comp ? total - (comp.r * rs + 1) / view.k : total);
      const pts = subPath(k.thread, skip, skip + (end - skip) * grown);
      ctx.strokeStyle = palette.red;
      ctx.lineWidth = on ? 1.7 : 1.05;
      ctx.lineJoin = 'round';
      ctx.globalAlpha = (on ? 0.95 : off ? dimmed(0.5) * 0.6 : 0.62) * matchFade;
      strokeRounded(pts, 9);
      if (!on && !close) continue;
      const rr = (on ? 3.4 : 2.8) * Math.min(1.3, rs);
      if (k.generated && grown >= 0.4) {
        const x = sx(k.generated[0]), y = sy(k.generated[1]);
        ctx.globalAlpha = (on ? 1 : 0.8) * matchFade;
        ctx.fillStyle = palette.ground;
        ctx.fillRect(x - rr, y - rr, rr * 2, rr * 2);
        ctx.lineWidth = 1.1;
        ctx.strokeRect(x - rr, y - rr, rr * 2, rr * 2);
      }
      if (k.caller && grown >= 0.7) {
        const x = sx(k.caller[0]), y = sy(k.caller[1]);
        ctx.globalAlpha = (on ? 1 : 0.8) * matchFade;
        ctx.beginPath();
        ctx.moveTo(x, y - rr * 1.25); ctx.lineTo(x + rr * 1.25, y); ctx.lineTo(x, y + rr * 1.25); ctx.lineTo(x - rr * 1.25, y);
        ctx.closePath();
        ctx.fillStyle = palette.ground;
        ctx.fill();
        ctx.strokeStyle = palette.ink;
        ctx.lineWidth = 1.1;
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  // Light belongs to machine-checked evidence: on the dark ground the
  // verified computations and the components that call them glow faintly.
  function drawEmbers(focus, lit, rs, shown) {
    ctx.globalCompositeOperation = 'lighter';
    for (const c of compObj.values()) {
      if (!c.formal || !shown(c.comp)) continue;
      const on = focus && lit.has(c.key);
      drawGlow(sx(c.x), sy(c.y), c.r * rs * 3, palette.red, (on ? 0.42 : 0.24) * (focus && !on ? 1 - focusMix : 1) * penAt(c.angle));
    }
    for (const o of [...kernelObj.values(), ...coreObj.values()]) {
      const on = focus && lit.has(o.key);
      const len = petalPx(o);
      drawGlow(sx(o.x), sy(o.y), len * 1.5, palette.red, (on ? 0.3 : 0.16) * (focus && !on ? 1 - focusMix : 1) * revealAlpha(o.type === 'core' ? REVEAL.core : REVEAL.kernels));
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
  }

  // The coverage rings, read like the tracks of a circular genome plot: one
  // ring per kind of evidence, one cell per component. A recorded cell takes
  // its ring's colour; the two rings recorded for every component (rerun set
  // up, past runs) are lighter tints at rest so the sparse proof evidence
  // stands out; a cell the snapshot does not record is a neutral outline
  // (not a failure), and an unknown one is hatched.
  function cellInk(track, c) {
    if (track.ink === 'unknown') return 'unknown';
    const v = c.comp.checks[track.id];
    if (v === null || v === undefined) return 'unknown';
    return v ? track.ink : 'empty';
  }
  const ubiquitous = new Set(TRACKS.filter((t) => {
    if (t.ink === 'unknown' || !compObj.size) return false;
    let n = 0;
    for (const c of compObj.values()) if (c.comp.checks[t.id] === true) n += 1;
    return n >= compObj.size * 0.9;
  }).map((t) => t.id));
  let trackInks = null, trackInksFor = null;
  function inksFor() {
    if (trackInksFor === palette) return trackInks;
    const ground = parseColor(palette.ground) || [0, 0, 0, 1];
    const mix = (a, b, t) => mixOklab(a, b, t, ground) || a;
    trackInks = { tint: {}, dot: {}, line: mix(palette.ink, palette.groundText, darkGround ? 0.66 : 0.7) };
    for (const t of TRACKS) {
      const base = palette.ring[t.id];
      trackInks.tint[t.id] = mix(base, palette.groundText, darkGround ? 0.5 : 0.56);
      trackInks.dot[t.id] = mix(base, palette.ink, darkGround ? 0.1 : 0.45);
    }
    trackInksFor = palette;
    return trackInks;
  }
  const columnOf = (key) => {
    const o = key ? byKey.get(key) : null;
    return o && o.type === 'component' ? o : o && o.type === 'kernel' && o.componentId ? compObj.get(o.componentId) : null;
  };
  function drawTracks(focus, shown, lit) {
    const inks = inksFor();
    const fo = focus ? byKey.get(focus) : null;
    const column = fo && (fo.type === 'component' || fo.type === 'kernel') ? columnOf(focus) : null;
    const chosen = columnOf(selected);
    const preview = columnOf(hover);
    // A lit rule keeps its citers' columns at full colour; the others dim to
    // about half. Membership is the rule's own citers (or the lit set when
    // the caller passes one), never its witnesses.
    let citing = null;
    if (fo && fo.type === 'rule') {
      citing = new Set();
      if (lit && lit.size) { for (const c of compObj.values()) if (lit.has(c.key)) citing.add(c.id); } else for (const id of fo.rule.citedBy) citing.add(id);
    }
    const k = view.k;
    const close = k >= fittedK * 1.3;
    const halfCell = L.pitch / 2;
    TRACKS.forEach((track, i) => {
      const [r0, r1] = trackBand(i);
      const emph = !emphasis || emphasis === track.id;
      const tinted = ubiquitous.has(track.id);
      for (const c of compObj.values()) {
        const p = trackPen(c.angle, i);
        if (p <= 0) continue;
        const ink = cellInk(track, c);
        const full = c === chosen || c === preview || (column === c);
        let alpha = p * (shown(c.comp) ? 1 : 0.16) * (emph ? 1 : 0.28);
        if (column && column !== c) alpha *= dimmed(0.45);
        if (citing && !citing.has(c.id)) alpha *= 1 - 0.5 * focusMix;
        cellPath(c.angle, halfCell, 0.75, r0, r1);
        if (ink === 'empty') {
          ctx.globalAlpha = alpha * (lodLevel === LOD.reading ? 0.9 : lodLevel === LOD.neighbourhood ? 0.7 : 0.45);
          ctx.strokeStyle = inks.line;
          ctx.lineWidth = Math.max(hairPx, Math.min(0.8, k * 1.1));
          ctx.stroke();
        } else if (ink === 'unknown') {
          ctx.globalAlpha = alpha * 0.85;
          ctx.fillStyle = hatch || palette.empty;
          ctx.fill();
        } else {
          ctx.globalAlpha = alpha * 0.95;
          ctx.fillStyle = tinted && !full ? inks.tint[track.id] : palette.ring[track.id];
          ctx.fill();
          if (ink === 'saved' && close) {
            // One dot per past-run record: filled when available, slashed
            // when available but blocked, hollow when missing from the snapshot.
            const recs = c.comp.receipts;
            const n = recs.length;
            const rm = (r0 + r1) / 2;
            const span = 2 * (halfCell - 0.75 / rm);
            const dot = Math.max(0.8, Math.min(2.2, (span * rm * k) / (n * 2.8)));
            const dotInk = tinted && !full ? inks.dot[track.id] : palette.ground;
            ctx.strokeStyle = dotInk;
            ctx.fillStyle = dotInk;
            ctx.lineWidth = Math.max(0.6, Math.min(1, dot * 0.5));
            recs.forEach((rec, j) => {
              const a = c.angle + ((j + 0.5) / n - 0.5) * span * 0.86;
              const x = view.tx + Math.cos(a) * rm * k, y = view.ty + Math.sin(a) * rm * k;
              ctx.globalAlpha = alpha;
              ctx.beginPath(); ctx.arc(x, y, dot, 0, TURN);
              const available = rec.availability === 'available';
              if (available && rec.status !== 'blocked') { ctx.fill(); return; }
              ctx.stroke();
              if (available) {
                const e = dot * 1.35;
                ctx.beginPath(); ctx.moveTo(x - e * 0.7, y + e * 0.7); ctx.lineTo(x + e * 0.7, y - e * 0.7); ctx.stroke();
              }
            });
          }
        }
      }
    });
    const [rIn] = trackBand(0);
    const [, rOut] = trackBand(TRACKS.length - 1);
    if (chosen) {
      // The chosen column: a crisp ink outline from the first ring to the
      // last, numbered 01-08 from the component outward when there is room.
      ctx.globalAlpha = 0.95;
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = 1.5;
      ctx.lineJoin = 'miter';
      cellPath(chosen.angle, halfCell, -0.9, rIn - 2.2, rOut + 2.2);
      ctx.stroke();
      const pitchPx = R.component * k * L.pitch;
      if (pitchPx >= 34) {
        const font = face(600, 9.5, false, SANS);
        TRACKS.forEach((t, i) => {
          const [a0, a1] = trackBand(i);
          const rm = ((a0 + a1) / 2) * k;
          const edge = chosen.angle + halfCell + 0.9 / ((a0 + a1) / 2);
          const ex = view.tx + Math.cos(edge) * rm, ey = view.ty + Math.sin(edge) * rm;
          const tx = -Math.sin(edge), ty = Math.cos(edge); // clockwise tangent
          ctx.globalAlpha = 0.9;
          ctx.strokeStyle = palette.ink;
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(ex, ey); ctx.lineTo(ex + tx * 4, ey + ty * 4); ctx.stroke();
          const lx = ex + tx * 13, ly = ey + ty * 13;
          textWithHalo(String(i + 1).padStart(2, '0'), lx, ly, font, palette.ink, 0.95, 'center', 'middle');
        });
      }
      if (hoverTrack >= 0 && hover === chosen.key) {
        const [a0, a1] = trackBand(hoverTrack);
        cellPath(chosen.angle, halfCell, -0.4, a0 - 1.3, a1 + 1.3);
        ctx.lineWidth = Math.max(1.4, hairPx * 3);
        ctx.stroke();
      }
    }
    if (preview && preview !== chosen) {
      // The previewed column: open-corner brackets, not a full outline.
      const h0 = halfCell + 0.9 / (rIn - 2.2), h1 = halfCell + 0.9 / (rOut + 2.2);
      const ri = (rIn - 2.2) * k, ro = (rOut + 2.2) * k;
      const arm = 6;
      ctx.globalAlpha = 0.9;
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      for (const [rad, h, dirR] of [[ri, h0, 1], [ro, h1, -1]]) {
        for (const side of [-1, 1]) {
          const ang = preview.angle + side * h;
          const da = (arm / rad) * -side;
          ctx.moveTo(view.tx + Math.cos(ang + da) * rad, view.ty + Math.sin(ang + da) * rad);
          ctx.arc(view.tx, view.ty, rad, ang + da, ang, side > 0 ? false : true);
          ctx.lineTo(view.tx + Math.cos(ang) * (rad + dirR * arm), view.ty + Math.sin(ang) * (rad + dirR * arm));
        }
      }
      ctx.stroke();
      if (hoverTrack >= 0) {
        const [a0, a1] = trackBand(hoverTrack);
        cellPath(preview.angle, halfCell, -0.4, a0 - 1.3, a1 + 1.3);
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  // The layer scale in the key wedge at 12 o'clock, top to bottom: the
  // three orbits, the citation band, the eight rings (each name at its own
  // ring's radius, in its ring's colour), the components and the proved
  // computations in the dial field. Every name is planned by the label
  // planner (wedgeCandidates, in planInscriptions) and drawn here (drawWedge).
  // It is also a live readout: a chosen rule lights its orbit's name and
  // CITATIONS; a chosen component turns the ring names into its own readout
  // (ring colour and a filled dot = recorded; muted and a hollow dot = not
  // recorded; italic and a dashed dot = unknown) and lights COMPONENTS (and
  // PROVED COMPUTATIONS when it has one); a hovered ring cell lights its
  // ring's name, with one faint guide arc along the ring to the cell.
  const luminance = (c) => {
    const lin = (v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
    return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
  };
  const contrastOf = (a, b) => { const la = luminance(a), lb = luminance(b); return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05); };
  const legibleCache = new Map();
  /** The colour itself, or the nearest step towards the ink that reads at 4.5:1 on the ground. */
  function legible(color) {
    const key = `${palette.ground}|${palette.ink}|${color}`;
    if (legibleCache.has(key)) return legibleCache.get(key);
    const ground = parseColor(palette.ground) || [0, 0, 0, 1];
    let out = color;
    for (let t = 0; t <= 1.0001; t += 0.05) {
      const c = t ? mixOklab(color, palette.ink, t, ground) : color;
      const pc = c && parseColor(c);
      if (!pc) break;
      const flat = pc[3] < 1 ? [pc[0] * pc[3] + ground[0] * (1 - pc[3]), pc[1] * pc[3] + ground[1] * (1 - pc[3]), pc[2] * pc[3] + ground[2] * (1 - pc[3])] : pc;
      out = c;
      if (contrastOf(flat, ground) >= 4.6) break;
    }
    legibleCache.set(key, out);
    return out;
  }
  const WEDGE_SPARE = 4; // px kept clear at each end of a name's chord
  function wedgeState(fo) {
    const comp = fo && fo.type === 'component' ? fo : fo && fo.type === 'kernel' && fo.componentId ? compObj.get(fo.componentId) : null;
    const rule = fo && fo.type === 'rule' ? fo : null;
    const dialed = fo && (fo.type === 'kernel' || fo.type === 'core' || (comp && [...kernelObj.values()].some((x) => x.componentId === comp.id)));
    const cell = hoverTrack >= 0 && hover ? byKey.get(hover) : null;
    return { comp, rule, dialed: !!dialed, cell: cell && cell.type === 'component' ? cell : null, track: hoverTrack };
  }
  function wedgeCandidates(fo, cx, cy) {
    const k = view.k;
    const st = wedgeState(fo);
    const out = [];
    const capsPx = Math.min(10, Math.max(8.5, k * 15));
    const caps = face(700, capsPx, false, SANS);
    const add = (id, text, font, px, radius, color, extra = {}) => {
      const W = textWidth(font, text) + (extra.dotW || 0);
      const room = KEY_GAP * radius - 2 * WEDGE_SPARE;
      if (!extra.free && W > room) return;
      const anchors = (extra.radii || [radius]).map((r) => ({ kind: 'arc', cx, cy, radius: r, mid: -Math.PI / 2, width: W, height: extra.height || px + 2 }));
      out.push({ id: `wedge:${id}`, priority: PRIORITY.wedge, ignore: extra.inside ? ['ring'] : undefined, anchors,
        data: { text, font, px, color, W, lit: !!extra.lit, dim: !!extra.dim, dotW: extra.dotW || 0, state: extra.state || null, track: extra.track ?? -1, lines: extra.lines || null } });
    };
    const anyLit = !!(st.rule || st.comp || (fo && (fo.type === 'kernel' || fo.type === 'core')) || st.track >= 0);
    if (halo) {
      const orbitLit = (kind) => !!(st.rule && st.rule.kind === kind);
      for (const [id, text, r, color, kind] of [['failures', 'FAILURE MODES', R.failures, palette.threat, 'anti_principle'], ['axioms', 'AXIOMS', R.axioms, palette.doctrine, 'axiom'], ['principles', 'PRINCIPLES', R.principles, palette.doctrine, 'principle']]) {
        add(id, text, caps, capsPx, r * k, legible(color), { lit: orbitLit(kind), dim: anyLit && !orbitLit(kind) });
      }
      add('citations', 'CITATIONS', caps, capsPx, (R.cap1 ?? R.scale + 12) * k + 9, legible(palette.muted), { lit: !!st.rule, dim: anyLit && !st.rule });
    }
    // The ring names, each at its own ring's centre line.
    const pitchPx = (R.trackH + R.trackGap) * k;
    const ringPx = Math.min(10, pitchPx * 0.8);
    if (ringPx >= 7) {
      const font = face(600, ringPx, false, SANS);
      const dotW = ringPx * 0.95;
      TRACKS.forEach((track, i) => {
        const [r0, r1] = trackBand(i);
        let state = null;
        if (st.comp) state = cellInk(track, st.comp);
        const lit = st.track === i;
        const color = legible(track.ink === 'unknown' ? palette.muted : palette.ring[track.id]);
        const text = track.wedge || track.short;
        const f = state === 'unknown' ? face(600, ringPx, true, SANS) : state && state !== 'empty' ? face(700, ringPx, false, SANS) : font;
        add(`ring:${track.id}`, text, f, ringPx, ((r0 + r1) / 2) * k, state === 'empty' || state === 'unknown' ? legible(palette.muted) : color,
          { inside: true, dotW, state, track: i, lit, dim: !st.comp && anyLit && !lit && !(emphasis === track.id),
            // Each name keeps to its own ring's band, so neighbours never meet.
            height: Math.min(ringPx + 2, pitchPx - 4.5) });
      });
    }
    add('components', 'COMPONENTS', caps, capsPx, R.component * k, legible(palette.ink), { inside: true, lit: !!st.comp, dim: anyLit && !st.comp });
    // The dial field: under the components, on one line where the field
    // allows it, else on two; wider than the wedge, since nothing but dials
    // and stems stands inside the ring (the planner keeps it off both).
    // It is shown with the ring names, as one scale, or not at all.
    if (ringPx >= 7) {
      const lit = st.dialed;
      const dim = anyLit && !lit;
      const color = legible(palette.red);
      const one = 'PROVED COMPUTATIONS';
      const W1 = textWidth(caps, one);
      const radii = [];
      for (let r = R.component * k - capsPx - 10; r >= (R.cores * k) + 18; r -= 6) radii.push(r);
      const lh = capsPx + 3;
      const wA = textWidth(caps, 'PROVED'), wB = textWidth(caps, 'COMPUTATIONS');
      // Nearest the components first: one line, else two, at each radius.
      const anchors = [];
      for (const r of radii) {
        anchors.push({ kind: 'arc', cx, cy, radius: r, mid: -Math.PI / 2, width: W1, height: capsPx + 2, lines: null });
        if (r - lh < R.cores * k + 18) continue;
        const shape = [...arcDiscs(cx, cy, r, -Math.PI / 2, wA, capsPx + 2), ...arcDiscs(cx, cy, r - lh, -Math.PI / 2, wB, capsPx + 2)];
        anchors.push({ kind: 'shape', shape, radius: r, lines: [['PROVED', r], ['COMPUTATIONS', r - lh]] });
      }
      out.push({ id: 'wedge:dials', priority: PRIORITY.wedge, ignore: ['ring'], anchors,
        data: { text: one, font: caps, px: capsPx, color, W: W1, lit, dim, dotW: 0, state: null, track: -1 } });
    }
    return out;
  }
  function drawWedge(focus) {
    if (!ins || !ins.wedge.length) return;
    const a = revealAlpha(REVEAL.words);
    if (a <= 0.01) return;
    const k = view.k;
    const top = -Math.PI / 2;
    for (const p of ins.wedge) {
      const d = p.data || {};
      const an = p.anchor;
      const alpha = a * (d.dim ? 0.5 : 1);
      const font = d.lit ? d.font.replace(/^(italic )?\d+/, (m, it) => `${it || ''}800`) : d.font;
      const radius = an.radius;
      if (an.lines) {
        for (const [text, r] of an.lines) drawArcText(text, font, d.color, alpha, r, top, false, true, false);
        if (d.lit) for (const [text, r] of an.lines) wedgeRule(text, font, d.color, alpha, r, d.px);
        continue;
      }
      // The readout dot (or nothing at rest) stands before the name.
      const textW = d.W - d.dotW;
      const shift = d.state ? d.dotW / 2 : 0; // the name moves right of its dot
      const mid = top + shift / radius;
      drawArcText(d.text, font, d.color, alpha, radius, mid, false, true, false);
      if (d.state) {
        const ang = top - (textW / 2 + d.dotW / 2 - shift) / radius - (d.dotW * 0.1) / radius;
        const x = view.tx + Math.cos(ang) * radius, y = view.ty + Math.sin(ang) * radius;
        const rr = Math.max(1.8, d.px * 0.27);
        ctx.globalAlpha = alpha;
        ctx.beginPath(); ctx.arc(x, y, rr, 0, TURN);
        if (d.state === 'empty' || d.state === 'unknown') {
          ctx.fillStyle = palette.ground; ctx.fill();
          ctx.strokeStyle = d.color; ctx.lineWidth = 1;
          if (d.state === 'unknown') ctx.setLineDash([1.2, 1.2]);
          ctx.stroke(); ctx.setLineDash([]);
        } else { ctx.fillStyle = d.color; ctx.fill(); }
      }
      if (d.lit && d.track < 0) wedgeRule(d.text, font, d.color, alpha, radius, d.px, mid);
      // A hovered ring cell: one faint guide arc along its ring from the
      // name to the cell, round the side the cell is on.
      if (d.track >= 0 && d.track === hoverTrack && hover && byKey.get(hover)?.type === 'component') {
        const c = byKey.get(hover);
        const half = (d.W / 2 + 3) / radius;
        const clockwise = share(c.angle) < 0.5;
        const from = clockwise ? top + half : top - half;
        let to = c.angle;
        if (clockwise) { while (to < from) to += TURN; } else { while (to > from) to -= TURN; }
        const end = to - (clockwise ? 1 : -1) * (L.pitch * 0.5);
        ctx.strokeStyle = d.color;
        ctx.lineWidth = 1;
        ctx.globalAlpha = a * 0.5;
        ctx.setLineDash([2, 3]);
        ctx.beginPath(); ctx.arc(view.tx, view.ty, radius, Math.min(from, end), Math.max(from, end)); ctx.stroke();
        ctx.setLineDash([]);
      }
    }
    ctx.globalAlpha = 1;
  }
  // A lit name gets a fine rule under it, its own width.
  function wedgeRule(text, font, color, alpha, radius, px, mid = -Math.PI / 2) {
    ctx.font = font;
    const w = ctx.measureText(text).width;
    const r = radius - px * 0.62;
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.globalAlpha = alpha * 0.9;
    ctx.beginPath(); ctx.arc(view.tx, view.ty, r, mid - w / 2 / r, mid + w / 2 / r); ctx.stroke();
  }

  /* ---- The doctrine halo ---------------------------------------------------- */
  // A rule's mark in pixels: an axiom larger than a principle or a failure mode.
  function rulePx(o, rs) {
    return (o.kind === 'axiom' ? 13 : 10) * Math.min(1.6, Math.max(0.8, rs));
  }
  const rgbOf = (color) => {
    const c = parseColor(color) || [0.6, 0.8, 0.9, 1];
    return `${Math.round(c[0] * 255)},${Math.round(c[1] * 255)},${Math.round(c[2] * 255)}`;
  };
  // What a focus lights on the halo: the rules it names directly, and those
  // one step further (a cited principle's axioms, a rule's ties), fainter.
  function haloFocus(fo) {
    const direct = new Set(), soft = new Set();
    if (fo && fo.type === 'component') {
      for (const id of fo.comp.ruleIds || []) if (ruleObj.has(id)) direct.add(id);
      for (const id of direct) for (const a of model.ruleById.get(id).restsOn) if (!direct.has(a)) soft.add(a);
      return { direct, soft, comp: fo, rule: null };
    }
    if (fo && fo.type === 'rule') {
      const r = fo.rule;
      direct.add(r.id);
      for (const id of [...r.restsOn, ...r.threatens, ...r.principles, ...r.failures]) soft.add(id);
      return { direct, soft, comp: null, rule: fo };
    }
    return { direct, soft, comp: null, rule: null };
  }

  // The halo's ground: a cold light along the axioms' orbit on the dark
  // ground, the three orbits drawn round clockwise from the key wedge, and a
  // graduation on the axioms' orbit at every component's angle, so the halo
  // is read against the ring beneath it.
  function drawBezel() {
    if (!halo) return;
    const a = revealAlpha(REVEAL.bezel);
    if (a <= 0.01) return;
    const pen = reveal >= 1 ? 1 : ease(clamp01((revealMs - REVEAL.bezel) / REVEAL.bezelDur));
    const edges = [];
    L.sectors.forEach((s, i) => { if (i) edges.push((L.sectors[i - 1].hi + s.lo) / 2); });
    edges.push(L.sectors[0].lo, L.sectors[L.sectors.length - 1].hi);
    // One fine tick per component just outside the halo, longer at each
    // family's edge, so the outer rim reads as a graduated scale.
    const bz = bezel();
    ctx.strokeStyle = palette.muted;
    ctx.lineWidth = hairPx;
    ctx.globalAlpha = 0.7 * a;
    ctx.beginPath();
    for (const c of compObj.values()) {
      if (share(c.angle) > pen) continue;
      const cs = Math.cos(c.angle), sn = Math.sin(c.angle);
      ctx.moveTo(view.tx + cs * bz.r0, view.ty + sn * bz.r0);
      ctx.lineTo(view.tx + cs * (bz.r0 + bz.tick), view.ty + sn * (bz.r0 + bz.tick));
    }
    ctx.stroke();
    ctx.lineWidth = Math.max(hairPx, 1);
    ctx.globalAlpha = 0.9 * a;
    ctx.beginPath();
    for (const ang of edges) {
      if (share(ang) > pen + 0.01) continue;
      const cs = Math.cos(ang), sn = Math.sin(ang);
      ctx.moveTo(view.tx + cs * bz.r0, view.ty + sn * bz.r0);
      ctx.lineTo(view.tx + cs * bz.r1, view.ty + sn * bz.r1);
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
  function drawHaloField() {
    if (!halo) return;
    const a = revealAlpha(REVEAL.halo);
    if (a <= 0.01) return;
    const k = view.k;
    const lo = -Math.PI / 2 + KEY_GAP / 2, span = TURN - KEY_GAP;
    const pen = reveal >= 1 ? 1 : ease(clamp01((revealMs - REVEAL.halo) / REVEAL.haloDur));
    if (darkGround) {
      // The ring of cold light along the axioms' orbit; its proportions do
      // not depend on the zoom, so one sprite serves every camera.
      const r0 = R.principles - 18, r1 = R.failures + 16;
      const rgb = rgbOf(palette.doctrine);
      const sprite = lightSprite('halo', 768, [[0, `rgba(${rgb},0)`], [(R.axioms - r0) / (r1 - r0), `rgba(${rgb},0.05)`], [1, `rgba(${rgb},0)`]], r0 / r1);
      drawLight(sprite, r1 * k, a * pen);
    }
    ctx.strokeStyle = palette.doctrineSoft;
    ctx.lineWidth = hairPx;
    for (const [r, alpha, dash] of [[R.principles, 0.55, []], [R.axioms, 0.95, []], [R.failures, 0.5, [1.5, 3]]]) {
      ctx.globalAlpha = alpha * a;
      ctx.setLineDash(dash);
      ctx.beginPath(); ctx.arc(view.tx, view.ty, r * k, lo, lo + span * pen); ctx.stroke();
    }
    ctx.setLineDash([]);
    if (R.axioms * k * L.pitch > 2.4) {
      const r0 = (R.axioms - 2.6) * k, r1 = (R.axioms + 2.6) * k;
      ctx.globalAlpha = 0.5 * a;
      ctx.beginPath();
      for (const c of compObj.values()) {
        if (share(c.angle) > pen) continue;
        const cs = Math.cos(c.angle), sn = Math.sin(c.angle);
        ctx.moveTo(view.tx + cs * r0, view.ty + sn * r0); ctx.lineTo(view.tx + cs * r1, view.ty + sn * r1);
      }
      ctx.stroke();
    }
    // A ray at each family's edge, from the rings out to the rim, so the
    // halo is read against the families beneath it.
    const edges = [];
    L.sectors.forEach((s, i) => { if (i) edges.push((L.sectors[i - 1].hi + s.lo) / 2); });
    edges.push(L.sectors[0].lo, L.sectors[L.sectors.length - 1].hi);
    ctx.strokeStyle = palette.doctrineSoft;
    ctx.lineWidth = hairPx;
    ctx.globalAlpha = 0.5 * a * pen;
    ctx.setLineDash([1, 3]);
    ctx.beginPath();
    for (const ang of edges) {
      const cs = Math.cos(ang), sn = Math.sin(ang);
      ctx.moveTo(view.tx + cs * (R.scale + 6) * k, view.ty + sn * (R.scale + 6) * k);
      ctx.lineTo(view.tx + cs * (R.rim - 2) * k, view.ty + sn * (R.rim - 2) * k);
    }
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
  }

  // The register: one quiet tick per component just outside its rings, its
  // length the number of rules its record cites. A chosen rule turns each
  // citer's tick into a luminous cap (in order of angular distance from the
  // rule) and fades every other tick to 15%; a previewed second rule's citers
  // get hollow caps beside them. A chosen component shows its own cap, where
  // its routes leave. A previewed component gets open-corner brackets.
  let maxRules = 1;
  for (const ids of teethOf.values()) maxRules = Math.max(maxRules, ids.length);
  const CAP_MID = (R.cap0 + R.cap1) / 2;
  function capArc(c, r, half, width) {
    ctx.lineWidth = width;
    ctx.beginPath(); ctx.arc(view.tx, view.ty, r, c.angle - half, c.angle + half); ctx.stroke();
  }
  function drawRegister(fo, cmp, shown) {
    if (!halo) return;
    const pen = reveal >= 1 ? 1 : (revealMs - REVEAL.fibers) / REVEAL.fiberDur;
    if (pen <= 0) return;
    const k = view.k;
    const rule = fo && fo.type === 'rule' ? fo : null;
    const comp = fo && fo.type === 'component' ? fo : fo && fo.type === 'kernel' && fo.componentId ? compObj.get(fo.componentId) : null;
    const members = rule ? new Set(membersOf(rule.rule)) : null;
    const second = rule && cmp && cmp.type === 'rule' ? new Set(membersOf(cmp.rule)) : null;
    // A failure mode's members are exposed, not citing: their caps are
    // dashed, in the threat ink, so the indirect relation never reads as a
    // citation.
    const exposing = !!rule && rule.rule.kind === 'anti_principle';
    const capInk = exposing ? palette.threat : palette.doctrine;
    const half = L.pitch * 0.35;
    const colPx = L.pitch * R.cap0 * k;
    ctx.lineCap = 'butt';
    ctx.strokeStyle = palette.doctrineSoft;
    ctx.lineWidth = Math.max(hairPx, Math.min(1.3, colPx * 0.085));
    for (const c of compObj.values()) {
      const n = teethOf.get(c.id).length;
      if (!n) continue;
      const tooth = reveal >= 1 ? 1 : clamp01((pen - share(c.angle)) / 0.12);
      if (tooth <= 0) continue;
      if (members && members.has(c.id) && focusMix >= 0.999) continue; // its cap stands in for it
      let alpha = (darkGround ? 0.55 : 0.62) * tooth * (shown(c.comp) ? 1 : 0.25);
      if (members) alpha *= 1 - 0.85 * focusMix;
      else if (comp && comp !== c) alpha *= dimmed(0.6);
      ctx.globalAlpha = alpha;
      const len = (8 * n) / maxRules;
      const cs = Math.cos(c.angle), sn = Math.sin(c.angle);
      ctx.beginPath();
      ctx.moveTo(view.tx + cs * R.cap0 * k, view.ty + sn * R.cap0 * k);
      ctx.lineTo(view.tx + cs * (R.cap0 + len) * k, view.ty + sn * (R.cap0 + len) * k);
      ctx.stroke();
    }
    // Caps, in order of angular distance from the rule's glyph.
    const caps = members ? [...members].map((id) => compObj.get(id)).filter(Boolean) : comp ? [comp] : [];
    const far = rule ? Math.max(1e-6, ...caps.map((c) => Math.abs(shortArc(rule.angle, c.angle)))) : 1;
    const rc = CAP_MID * k;
    // On the dark ground each cap glows: two wide, faint under-strokes in
    // added light stand in for a shadow blur at a fraction of its cost.
    for (const glow of darkGround ? [2, 1, 0] : [0]) {
      ctx.save();
      if (glow) ctx.globalCompositeOperation = 'lighter';
      ctx.strokeStyle = capInk;
      if (exposing && !glow) ctx.setLineDash([2.4, 1.6]);
      for (const c of caps) {
        const v = ignition(rule ? IGNITE_STAGGER * Math.abs(shortArc(rule.angle, c.angle)) / far : 0);
        if (v <= 0) continue;
        const alpha = Math.min(1, v) * focusMix * (shown(c.comp) ? 1 : 0.35) * (glow === 2 ? 0.1 : glow === 1 ? 0.2 : 1);
        ctx.globalAlpha = alpha;
        const width = 2 * Math.max(1, v);
        capArc(c, rc, half * (v > 1 ? 1 + (v - 1) * 0.6 : 1) + (glow ? glow * 1.4 / rc : 0), width + (glow === 2 ? 7 : glow === 1 ? 3 : 0));
      }
      ctx.restore();
    }
    if (second) {
      // Hollow caps for the previewed rule's members, just outside the solid ones.
      ctx.strokeStyle = cmp.rule.kind === 'anti_principle' ? palette.threat : palette.doctrine;
      ctx.lineWidth = 1;
      ctx.globalAlpha = 0.95;
      const r0 = rc + 2.2, r1 = rc + 5;
      for (const id of second) {
        const c = compObj.get(id);
        if (!c) continue;
        const h0 = half;
        ctx.beginPath();
        ctx.arc(view.tx, view.ty, r1, c.angle - h0, c.angle + h0);
        ctx.arc(view.tx, view.ty, r0, c.angle + h0, c.angle - h0, true);
        ctx.closePath();
        ctx.stroke();
      }
    }
    if (cmp && cmp.type === 'component') drawBrackets(cmp);
    ctx.globalAlpha = 1;
  }
  // Open-corner brackets round a previewed component's column, from its mark
  // out to the register.
  function drawBrackets(c) {
    const k = view.k;
    const r0 = (R.track0 - 3) * k, r1 = (R.cap1 + 2) * k;
    const h = L.pitch * 0.56;
    const arm = 5;
    ctx.strokeStyle = palette.ink;
    ctx.lineWidth = 1.2;
    ctx.globalAlpha = 0.85;
    ctx.beginPath();
    for (const [r, inward] of [[r0, 1], [r1, -1]]) {
      for (const side of [-1, 1]) {
        const a = c.angle + side * h;
        const da = (arm / r) * -side;
        const cs = Math.cos(a), sn = Math.sin(a);
        ctx.moveTo(view.tx + Math.cos(a + da) * r, view.ty + Math.sin(a + da) * r);
        ctx.arc(view.tx, view.ty, r, a + da, a, side > 0 ? false : true);
        ctx.lineTo(view.tx + cs * (r + inward * arm), view.ty + sn * (r + inward * arm));
      }
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  /* ---- Routes ------------------------------------------------------------- */
  // A route is one citation, drawn between a cap and a rule glyph by the
  // planner in layout.js. A chosen rule draws all its routes when they fit
  // the lane capacity at this zoom, else none until one citer is previewed,
  // then exactly that one. A chosen component fans to its rules on the same
  // terms. A new route draws on from its source over 220 ms.
  const shared = {
    // Lane 2 may set `familyArcs` (an array, or a function returning one) of
    // the family labels' measured extents: { a0, a1 } in radians clockwise
    // and { r0, r1 } in screen pixels from the centre. Routes enter the caps
    // round them. Without it the planner estimates them from §3.
    familyArcs: null,
    activeRoutePolylines: () => routeLines,
    routeState: () => routeInfo,
  };
  let routeLines = [];
  let routeInfo = { mode: 'none', hub: null, total: 0, drawn: 0, reason: null, tracing: null };
  const routeShown = new Set();
  const planCache = new Map();
  function familyArcs(fo) {
    const supplied = typeof shared.familyArcs === 'function' ? shared.familyArcs() : shared.familyArcs;
    if (Array.isArray(supplied)) return supplied;
    const k = view.k;
    if (R.scale * k < 90) return [];
    const base = R.cap1 * k + 15;
    ctx.font = face(600, TYPE.title);
    // One line per family (§3): the name, serif 14 px, on its baseline.
    return L.sectors.map((s) => {
      const half = (ctx.measureText(familyName(s.family)).width / 2 + 8) / base;
      return { a0: s.mid - half, a1: s.mid + half, r0: base - 7, r1: base + 7 };
    });
  }
  function routePlan(fo, leafIds, rs) {
    const k = view.k;
    const arcs = familyArcs(fo);
    const ruleBottom = (o) => o.orbit - (rulePx(o, rs) / 2 + (o.kind === 'axiom' ? 5 : 2.5)) / k;
    const capTop = CAP_MID + 1.2 / k;
    const outer = arcs.length ? Math.max(...arcs.map((a) => a.r1)) : R.cap1 * k + 24;
    const inner = arcs.length ? Math.min(...arcs.map((a) => a.r0)) : R.cap1 * k + 24;
    const band = { lo: (outer + 3) / k, hi: R.principles - (rulePx({ kind: 'principle' }, rs) / 2 + 3) / k };
    const corridor = { lo: R.cap1 + 2 / k, hi: Math.max(R.cap1 + 2 / k, (inner - 1.5) / k) };
    const blocked = arcs.map((a) => [angleShare(a.a0), angleShare(a.a1)]).filter(([x, y]) => y > x);
    const key = `${fo.key}|${leafIds.join(',')}|${k.toFixed(5)}|${rs.toFixed(3)}|${band.lo.toFixed(2)}|${corridor.hi.toFixed(2)}|${blocked.map((b) => `${b[0].toFixed(4)}:${b[1].toFixed(4)}`).join(',')}`;
    if (planCache.has(key)) return planCache.get(key);
    const hub = fo.type === 'rule' ? { s: fo.share, r: ruleBottom(fo), kind: 'glyph' } : { s: angleShare(fo.angle), r: capTop, kind: 'cap' };
    // An axiom's step up passes the principles' orbit: beside any principle
    // glyph standing in the way, so no route seems to end at the wrong rule.
    const pHalf = rulePx({ kind: 'principle' }, rs) / 2 + 3;
    const avoid = [...ruleObj.values()].filter((o) => o.kind === 'principle')
      .map((o) => { const w = pHalf / (R.principles * k * (TURN - KEY_GAP)); return [o.share - w, o.share + w]; });
    const jogR = R.principles + (pHalf + 1.5) / k;
    const leaves = leafIds.map((id) => {
      if (fo.type === 'rule') return { id, s: angleShare(compObj.get(id).angle), r: capTop };
      const o = ruleObj.get(id);
      const half = (rulePx(o, rs) / 2 + 5) / (o.orbit * k * (TURN - KEY_GAP));
      return o.kind === 'axiom' ? { id, s: o.share, r: ruleBottom(o), avoid, jogR, orbit: o.orbit, half } : { id, s: o.share, r: ruleBottom(o) };
    });
    const plan = planRoutes({ hub, leaves, k, band, corridor, blocked, colShare: L.pitch / (TURN - KEY_GAP) });
    if (planCache.size > 48) planCache.clear();
    planCache.set(key, plan);
    return plan;
  }
  function strokeUpto(pts, upto) {
    if (pts.length < 2) return null;
    let total = 0;
    for (let i = 1; i < pts.length; i += 1) total += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    let left = total * upto;
    let end = pts[pts.length - 1];
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i += 1) {
      const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
      if (d >= left) {
        const f = d ? left / d : 0;
        end = [pts[i - 1][0] + (pts[i][0] - pts[i - 1][0]) * f, pts[i - 1][1] + (pts[i][1] - pts[i - 1][1]) * f];
        ctx.lineTo(end[0], end[1]);
        break;
      }
      ctx.lineTo(pts[i][0], pts[i][1]);
      left -= d;
    }
    ctx.stroke();
    return end;
  }
  // Which routes show this frame, decided before anything is painted: the
  // label planner treats their full polylines as obstacles.
  let routeShow = [], routePick = null, routeHub = null;
  function planRoutesFor(fo, cmp, rs) {
    routeLines = [];
    const info = { mode: 'none', hub: fo ? fo.key : null, total: 0, drawn: 0, reason: null, tracing: null };
    let show = [];
    let pick = null;
    if (halo && fo && fo.type === 'rule' && fo.rule.kind === 'anti_principle' && reveal >= 1) {
      // A failure mode has no lines of its own: nothing cites it. Pointing at
      // an exposed component traces the citation leg of its path, from the
      // axiom it runs through (the threat lane to that axiom stays lit).
      info.total = fo.rule.exposed.size;
      info.mode = 'point';
      const through = cmp && cmp.type === 'component' ? fo.rule.exposed.get(cmp.id) : null;
      const axiom = through ? ruleObj.get(through[0]) : null;
      if (axiom) {
        show = routePlan(axiom, [cmp.id], rs).routes;
        pick = cmp.id;
        info.mode = 'trace';
        info.tracing = pick;
        info.through = axiom.id;
      }
    } else if (halo && fo && (fo.type === 'rule' || fo.type === 'component') && reveal >= 1) {
      const leaves = fo.type === 'rule' ? fo.rule.citedBy.filter((id) => compObj.has(id)) : (teethOf.get(fo.id) || []);
      info.total = leaves.length;
      if (leaves.length) {
        if (cmp) pick = fo.type === 'rule' ? (cmp.type === 'component' && leaves.includes(cmp.id) ? cmp.id : null) : (cmp.type === 'rule' && leaves.includes(cmp.id) ? cmp.id : null);
        const plan = routePlan(fo, leaves, rs);
        info.reason = plan.reason;
        if (plan.fits) { show = plan.routes; info.mode = 'all'; }
        else if (pick) { show = routePlan(fo, [pick], rs).routes; info.mode = 'trace'; }
        else info.mode = 'point';
        info.tracing = pick;
      }
    }
    const ids = new Set(show.map((r) => `${fo.key}>${r.id}`));
    for (const id of ids) if (!routeShown.has(id)) kick(`route:${id}`, ROUTE_DRAW);
    routeShown.clear();
    for (const id of ids) routeShown.add(id);
    info.drawn = show.length;
    routeInfo = info;
    routeShow = show; routePick = pick; routeHub = fo;
    for (const r of show) routeLines.push({ id: r.id, pts: r.pts.map(([x, y]) => [sx(x), sy(y)]), width: r.id === pick ? 2 : 1.5 });
  }
  function drawRoutes(fo, cmp, shown) {
    const show = routeShow, pick = routePick;
    if (!show.length || fo !== routeHub) return;
    const screen = show.map((r) => ({ r, pts: r.pts.map(([x, y]) => [sx(x), sy(y)]) }));
    const tips = [];
    // On the dark ground a route glows: two wide, faint under-strokes in
    // added light (pass 2, then 1) under the crisp line (pass 0).
    for (const glow of darkGround ? [2, 1, 0] : [0]) {
      ctx.save();
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.strokeStyle = palette.doctrine;
      ctx.fillStyle = palette.doctrine;
      if (glow) ctx.globalCompositeOperation = 'lighter';
      for (const { r, pts } of screen) {
        const e = elapsed(`route:${fo.key}>${r.id}`);
        const t = e === Infinity ? 1 : clamp01(e / ROUTE_DRAW);
        const p = 1 - (1 - t) ** 3;
        const c = fo.type === 'rule' ? compObj.get(r.id) : fo;
        const hot = r.id === pick;
        const width = hot ? 2 : 1.5;
        const base = focusMix * (c && !shown(c.comp) ? 0.35 : 1) * (pick && !hot ? 0.45 : 0.95);
        ctx.globalAlpha = base * (glow === 2 ? 0.09 : glow === 1 ? 0.2 : 1);
        ctx.lineWidth = width + (glow === 2 ? 6 : glow === 1 ? 2.6 : 0);
        const end = strokeUpto(pts, p);
        if (!glow) {
          if (p >= 1) {
            const [x, y] = pts[pts.length - 1];
            ctx.beginPath(); ctx.arc(x, y, hot ? 2 : 1.5, 0, TURN); ctx.fill();
          } else if (end) tips.push([end[0], end[1], base * (1 - clamp01((t - 0.7) / 0.3)), width]);
        }
      }
      ctx.restore();
    }
    // The pen: a bright point at the drawing front of each route while it
    // draws on, gone as the route completes (it never travels on its own).
    for (const [x, y, alpha, width] of tips) {
      if (alpha <= 0.01) continue;
      if (darkGround) {
        ctx.globalCompositeOperation = 'lighter';
        drawGlow(x, y, 9 + width * 2, palette.doctrine, alpha * 0.9);
        ctx.globalCompositeOperation = 'source-over';
        ctx.fillStyle = palette.ink;
      } else ctx.fillStyle = palette.doctrine;
      ctx.globalAlpha = alpha;
      ctx.beginPath(); ctx.arc(x, y, width * (darkGround ? 0.95 : 1.25), 0, TURN); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // Each rule's ruled lane to its axioms: out of the rule along its radius,
  // round the lane, and into each axiom; a failure mode's dashed, as a threat.
  // The chosen rule's lanes light; a previewed rule tied directly to it
  // (rests on, threatens) lights the lane between them.
  function drawLanes(focus, cmp) {
    if (!halo) return;
    const grow = reveal >= 1 ? 1 : ease(clamp01((revealMs - REVEAL.lanes) / REVEAL.laneDur));
    if (grow <= 0) return;
    const fo = focus ? byKey.get(focus) : null;
    const hf = haloFocus(fo);
    const close = view.k >= fittedK * 1.6;
    const tie = hf.rule && cmp && cmp.type === 'rule' ? [hf.rule.id, cmp.id] : null;
    for (const c of halo.combs) {
      let on = !!hf.rule && (hf.direct.has(c.rule) || (hf.rule.kind === 'axiom' && c.axioms.includes(hf.rule.id)));
      if (tie && ((c.rule === tie[0] && c.axioms.includes(tie[1])) || (c.rule === tie[1] && c.axioms.includes(tie[0])))) on = true;
      const failure = c.kind === 'anti_principle';
      ctx.strokeStyle = failure ? palette.threat : palette.doctrine;
      ctx.lineWidth = on ? 1.3 : Math.max(hairPx, 0.75);
      ctx.globalAlpha = (on ? 0.95 : darkGround ? 0.5 : 0.55) * (fo && !on ? dimmed(0.35) : 1) * (namesShown() && !on ? 0.4 : 1);
      ctx.setLineDash(failure ? [2.6, 2.2] : []);
      for (const part of c.parts) strokePath(part, grow);
      ctx.setLineDash([]);
      if ((on || close) && grow >= 1) {
        // A joint where a lane meets a drop, as on a circuit board.
        ctx.fillStyle = ctx.strokeStyle;
        for (const [x, y] of c.joints) { ctx.beginPath(); ctx.arc(sx(x), sy(y), on ? 1.7 : 1.2, 0, TURN); ctx.fill(); }
      }
    }
    ctx.globalAlpha = 1;
  }
  // The system map's rule marks (system-map.js ruleGlyph), drawn at z px.
  function drawRuleGlyph(kind, x, y, z, color) {
    ctx.strokeStyle = color;
    ctx.fillStyle = color;
    if (kind === 'axiom') {
      ctx.lineWidth = Math.max(1.3, z * 0.12);
      ctx.beginPath(); ctx.arc(x, y, z / 2 - 0.8, 0, TURN); ctx.stroke();
      ctx.beginPath(); ctx.arc(x, y, Math.max(1.7, z * 0.17), 0, TURN); ctx.fill();
    } else if (kind === 'principle') {
      const q = z / 2 - 0.5;
      ctx.lineWidth = Math.max(1.3, z * 0.13);
      ctx.beginPath(); ctx.moveTo(x, y - q); ctx.lineTo(x + q, y); ctx.lineTo(x, y + q); ctx.lineTo(x - q, y); ctx.closePath(); ctx.stroke();
    } else {
      const e = z * 0.37;
      ctx.lineWidth = Math.max(1.4, z * 0.15);
      ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(x - e, y - e); ctx.lineTo(x + e, y + e); ctx.moveTo(x + e, y - e); ctx.lineTo(x - e, y + e); ctx.stroke();
      ctx.lineCap = 'butt';
    }
  }
  // An axiom's obligations as arcs round its mark, one per obligation, in the
  // ink of its computed status: azure where its witnesses resolve, mauve for
  // declared layer debt, dotted where it is blocked or was not computed.
  function drawObligations(o, x, y, z, alpha) {
    const obs = o.rule.obligations;
    if (!obs.length || z < 11) return;
    const n = obs.length, rr = z / 2 + 3.6, gap = Math.min(0.5, TURN / n * 0.3);
    obs.forEach((ob, i) => {
      const ink = obligationWords(ob.computed)[1];
      const a0 = o.angle - Math.PI / 2 + (i / n) * TURN + gap / 2;
      ctx.globalAlpha = alpha * (ink === 'unknown' ? 0.55 : 0.95);
      ctx.strokeStyle = ink === 'stated' ? palette.doctrine : ink === 'debt' ? palette.threat : palette.muted;
      ctx.lineWidth = 1.5;
      ctx.setLineDash(ink === 'blocked' || ink === 'unknown' ? [1.2, 1.7] : []);
      ctx.beginPath(); ctx.arc(x, y, rr, a0, a0 + TURN / n - gap); ctx.stroke();
    });
    ctx.setLineDash([]);
  }

  function drawRules(focus, rs) {
    if (!halo) return;
    const fo = focus ? byKey.get(focus) : null;
    const hf = haloFocus(fo);
    for (const o of ruleObj.values()) {
      const at = (o.kind === 'axiom' ? REVEAL.axioms : REVEAL.rules) + o.share * 320;
      const pop = reveal >= 1 ? 1 : clamp01((revealMs - at) / 320);
      if (pop <= 0) continue;
      const on = hf.direct.has(o.id), near = hf.soft.has(o.id);
      let alpha = pop * (fo ? (on ? 1 : near ? 0.85 : dimmed(0.3)) : 1);
      if (matches && !on && !o.rule.citedBy.some((id) => matches.has(id))) alpha *= 0.4;
      const x = sx(o.x), y = sy(o.y);
      const z = rulePx(o, rs) * (1 + 0.5 * (1 - pop)) + (o.key === hover || o.key === selected ? 1.6 : 0);
      const ink = o.kind === 'anti_principle' ? palette.threat : palette.doctrine;
      // A rule glows by how many components cite it, so the halo is
      // brightest where the doctrine is most invoked; a lit rule flares as
      // the light reaches it.
      const weight = o.rule.citedBy.length / maxCited;
      const flare = on && hf.comp ? 0.35 * (1 - clamp01(sweepMs / (SWEEP_MS + RIPPLE_MS))) : 0;
      if (darkGround && (weight > 0 || on)) {
        ctx.globalCompositeOperation = 'lighter';
        drawGlow(x, y, z * (on ? 2.6 : 1.5 + 1.4 * weight), ink, alpha * (on ? 0.5 + flare : 0.06 + 0.34 * weight));
        ctx.globalCompositeOperation = 'source-over';
      }
      ctx.globalAlpha = alpha;
      ctx.fillStyle = palette.ground;
      ctx.beginPath(); ctx.arc(x, y, z / 2 + 1.8, 0, TURN); ctx.fill();
      drawRuleGlyph(o.kind, x, y, z, ink);
      if (o.kind === 'axiom') drawObligations(o, x, y, z, alpha);
      labelBoxes.push({ x0: x - z / 2 - 3, x1: x + z / 2 + 3, y0: y - z / 2 - 3, y1: y + z / 2 + 3 });
    }
    ctx.globalAlpha = 1;
    drawRuleWords(hf);
  }

  // The rule words, as planned: the chosen (and previewed) rule's full title,
  // the rule numbers beside their marks, and the axioms' and lit principles'
  // titles round the outside of the bezel. Each stands at full ink with a
  // ground knockout; under a focus, what is not lit steps back to context.
  function drawRuleWords(hf) {
    const a = revealAlpha(REVEAL.rules + 500);
    if (a <= 0.01 || !ins) return;
    const focused = hf && (hf.comp || hf.rule);
    const inkOf = (o) => (o.kind === 'anti_principle' ? palette.threat : palette.doctrine);
    const lit = (o) => !focused || hf.direct.has(o.id) || hf.soft.has(o.id);
    for (const p of ins.titles) {
      const d = p.anchor, o = p.data.o;
      const alpha = a * (p.priority <= PRIORITY.preview || lit(o) ? 1 : 0.55);
      if (d.kind === 'rect') textWithHalo(d.text, (d.x0 + d.x1) / 2, (d.y0 + d.y1) / 2, d.font, inkOf(o), alpha, 'center');
      else drawArcText(d.text, d.font, inkOf(o), alpha, d.radius, d.mid, d.lower, true, false);
    }
    for (const p of ins.ids.values()) {
      const d = p.anchor, o = p.data.o;
      textWithHalo(o.id, (d.x0 + d.x1) / 2, (d.y0 + d.y1) / 2 + 0.5, FONT.id, inkOf(o), a * (lit(o) ? 1 : 0.55), 'center');
    }
    ctx.globalAlpha = 1;
  }

  // The family names in their band just outside the caps: one line each,
  // name and count, and under a chosen rule how many of the family cite it.
  // They never leave at zoom: a family whose name is off screen is named by
  // the scope chip instead.
  function drawFamilyWords() {
    const a = revealAlpha(REVEAL.words);
    if (a <= 0.01 || !ins) return;
    for (const p of ins.family.values()) {
      const d = p.anchor;
      if (d.flat) {
        const y = d.y0 + 8;
        textWithHalo(d.name, d.x0, y, d.nameFont, palette.ink, a, 'left');
        textWithHalo(d.num, d.x0 + d.nameW + d.gapW, y, d.numFont, d.citeInline ? ins.citeInk || palette.doctrine : palette.muted, a, 'left');
        if (d.cite) textWithHalo(d.cite, d.x0, y + 14, FONT.cite, palette.doctrine, a, 'left');
        continue;
      }
      const r = d.radius;
      const dir = d.lower ? -1 : 1;
      const nameMid = d.mid - dir * (d.W / 2 - d.nameW / 2) / r;
      const numMid = d.mid + dir * (d.W / 2 - d.numW / 2) / r;
      drawArcText(d.name, d.nameFont, palette.ink, a, r, nameMid, d.lower, true, false);
      drawArcText(d.num, d.numFont, d.citeInline ? ins.citeInk || palette.doctrine : palette.muted, a, r, numMid, d.lower, true, false);
      if (d.cite) drawArcText(d.cite, FONT.cite, palette.doctrine, a, r + CITE_STEP, d.mid, d.lower, true, false);
    }
    ctx.globalAlpha = 1;
  }

  function drawKernels(focus, lit, rs, shown, fade) {
    const a = revealAlpha(REVEAL.kernels);
    for (const k of kernelObj.values()) {
      const comp = k.componentId ? compObj.get(k.componentId) : null;
      const alpha = a * fade(k.key) * (comp && !shown(comp.comp) ? 0.3 : 1);
      drawFlower(k, sx(k.x), sy(k.y), petalPx(k, rs), alpha, REVEAL.kernels);
    }
  }

  function drawCores(focus, lit, rs, fade) {
    for (const o of coreObj.values()) {
      const at = o.centre ? REVEAL.core : REVEAL.cores;
      const a = revealAlpha(at);
      drawFlower(o, sx(o.x), sy(o.y), petalPx(o, rs), a * fade(o.key), at);
    }
  }

  function drawComponents(focus, lit, rs, shown, fade) {
    const pitchPx = localPitch(view.k, L.pitch, R.component);
    const markScale = pitchPx >= 11 ? 1 : Math.max(0.55, pitchPx / 11);
    for (const c of compObj.values()) {
      const p = penAt(c.angle);
      if (p <= 0) continue;
      let alpha = p * fade(c.key);
      if (matches && !shown(c.comp)) alpha *= 0.13;
      const x = sx(c.x), y = sy(c.y);
      let r = c.r * rs * (1 + 0.35 * (1 - p)) * markScale;
      if (c.key === hover || c.key === selected) r += 1.2;
      ctx.globalAlpha = alpha;
      // A ground disc under each mark keeps lines beneath from reading as
      // part of it.
      ctx.fillStyle = palette.ground;
      ctx.beginPath(); ctx.arc(x, y, r + 1.4, 0, TURN); ctx.fill();
      drawBacking(x, y, r, c.comp.backing, c.formal ? palette.red : palette.ink);
    }
    ctx.globalAlpha = 1;
  }

  // Names that stand at rest: the cores and the kernels. Every mark near the
  // centre is room taken first, so no name covers one.
  const coreName = (core) => CORE_NAMES[core.id]?.[0] || moduleWords(core.id);
  const coreSub = (core) => {
    if (CORE_NAMES[core.id]) return CORE_NAMES[core.id][1];
    const caller = core.callers[0] ? String(core.callers[0]).split('#')[0].replace(/^src\//, '').replace(/\/_[a-z]+\.py$/, '').replace(/\//g, '.') : '';
    return caller ? `used by ${caller}` : 'part of the toolkit';
  };
  // Names inside the ring: the four cores and the kernels, horizontal, sans
  // 12.5 px, beside their own flower (below, above, right, then left: the
  // first place clear of every dial, cross, stem and placed name). A name
  // pushed further out than 6 px keeps a hairline leader to its flower. The
  // core names are placed first and are never omitted.
  const segHitsBox = (x0, y0, x1, y1, b) => {
    // Liang-Barsky clip of a segment against a box.
    let t0 = 0, t1 = 1;
    const dx = x1 - x0, dy = y1 - y0;
    for (const [p, q] of [[-dx, x0 - b.x0], [dx, b.x1 - x0], [-dy, y0 - b.y0], [dy, b.y1 - y0]]) {
      if (p === 0) { if (q < 0) return false; continue; }
      const r = q / p;
      if (p < 0) { if (r > t1) return false; if (r > t0) t0 = r; } else { if (r < t0) return false; if (r < t1) t1 = r; }
    }
    return true;
  };
  const circleHitsBox = (cx, cy, r, b) => {
    const nx = Math.max(b.x0, Math.min(b.x1, cx)), ny = Math.max(b.y0, Math.min(b.y1, cy));
    return Math.hypot(nx - cx, ny - cy) < r;
  };
  function drawAnchorWords(focus, lit, rs) {
    const a = revealAlpha(REVEAL.words);
    const k = view.k;
    const prints = flowerFootprints();
    // Every dial and every cross is room taken; so is every stem.
    const discs = [];
    for (const fp of prints) {
      const o = byKey.get(fp.key);
      discs.push([fp.x, fp.y, fp.petal + 2.5]);
      const f = flowerOf(o);
      if (o.mutants > DIAL.maxCrosses) {
        // The ×M inscription, a little wider than one cross.
        discs.push([fp.x + Math.cos(fp.crossDir) * (f.crossR + 2), fp.y + Math.sin(fp.crossDir) * (f.crossR + 2), Math.max(9, 9 * f.s)]);
      } else if (o.mutants) {
        const cr = f.crossR, step = (DIAL.crossPitch * f.s) / cr;
        for (let i = 0; i < o.mutants; i += 1) {
          const ang = fp.crossDir + (i - (o.mutants - 1) / 2) * step;
          discs.push([fp.x + Math.cos(ang) * cr, fp.y + Math.sin(ang) * cr, f.half * 1.45 + 2]);
        }
      }
    }
    const segs = [];
    for (const kk of kernelObj.values()) {
      const pts = kk.thread;
      for (let i = 1; i < pts.length; i += 1) segs.push([sx(pts[i - 1][0]), sy(pts[i - 1][1]), sx(pts[i][0]), sy(pts[i][1])]);
    }
    // Inside the ring of component marks (their inner edge, less a little air).
    const ringLimit = R.component * k - 5.6 * rs - 5;
    const inside = (b) => [[b.x0, b.y0], [b.x1, b.y0], [b.x0, b.y1], [b.x1, b.y1]].every(([x, y]) => Math.hypot(x - view.tx, y - view.ty) <= ringLimit);
    const free = (box) => {
      if (boxHit(box) || !inside(box)) return false;
      for (const [x, y, r] of discs) if (circleHitsBox(x, y, r, box)) return false;
      for (const [x0, y0, x1, y1] of segs) if (segHitsBox(x0, y0, x1, y1, box)) return false;
      return true;
    };
    const reading = R.component * k * L.pitch >= 34;
    const nameFont = face(600, 12.5, false, SANS);
    const subFont = face(400, 11, true, SANS);
    const place = (o, name, sub, must, fixed = false) => {
      const fp = prints.find((p) => p.key === o.key);
      const f = flowerOf(o);
      ctx.font = nameFont;
      let wdt = ctx.measureText(name).width;
      if (sub) { ctx.font = subFont; wdt = Math.max(wdt, ctx.measureText(sub).width); }
      const ht = sub ? 30 : 16;
      // The near edge of the flower in a direction: its petals, or its
      // crosses where they stand.
      const edge = (dir) => (o.mutants && Math.abs(shortArc(fp.crossDir, dir)) <= fp.crossSpan + 0.45 ? f.reach : f.r) + 4;
      // Below, above, right, left; then the diagonals, as a fallback.
      const q = Math.PI / 4;
      const dirs = [Math.PI / 2, -Math.PI / 2, 0, Math.PI, 3 * q, q, -3 * q, -q];
      const boxAt = (dir, extra) => {
        // The box's nearest side (or corner) stands `d` out along `dir`.
        const c = Math.cos(dir), sn = Math.sin(dir);
        const d = edge(dir) + extra;
        const px = fp.x + c * d, py = fp.y + sn * d;
        const ux = Math.abs(c) < 1e-6 ? 0 : Math.sign(c), uy = Math.abs(sn) < 1e-6 ? 0 : Math.sign(sn);
        const x0 = px - wdt / 2 + ux * wdt / 2, y0 = py - ht / 2 + uy * ht / 2;
        return { x0, x1: x0 + wdt, y0, y1: y0 + ht };
      };
      let chosenBox = null, moved = 0, dirOf = 0;
      // A name stays beside its own flower: pushed out a little at most (a
      // core further, since its name is never omitted); one with no room
      // waits for a closer view and stays in the panel.
      const extras = must ? [0, 8, 16, 26, 38] : [0, 8, 16];
      // A core name that finds no clear place beside its flower (a very
      // small drawing) may stand further out, over the drawing but never
      // over another name or its own flower.
      const own = discs.filter(([x, y]) => Math.hypot(x - fp.x, y - fp.y) <= f.reach + 1);
      const loose = (b) => !boxHit(b) && !own.some(([x, y, r]) => circleHitsBox(x, y, r, b));
      const passes = fixed ? [[[0, 4, 9], free]] : must ? [[extras, free], [[0, 8, 16, 26, 38, 52, 70, 90], loose]] : [[extras, free]];
      outer: for (const [list, test] of passes) {
        for (const extra of list) {
          // Diagonals only right beside the flower, and never on its cross side.
          const tryDirs = fixed ? [dirs[0]] : extra ? dirs.slice(0, 4) : dirs.filter((d, i) => i < 4 || !o.mutants || Math.abs(shortArc(fp.crossDir, d)) > fp.crossSpan + 0.6);
          for (const dir of tryDirs) {
            const b = boxAt(dir, extra);
            const padded = { x0: b.x0 - 2, x1: b.x1 + 2, y0: b.y0 - 1, y1: b.y1 + 1 };
            if (test(padded)) { chosenBox = b; moved = extra; dirOf = dir; break outer; }
          }
        }
      }
      if (!chosenBox) {
        if (!must) return;
        chosenBox = boxAt(dirs[0], 0); moved = 0; dirOf = dirs[0];
      }
      const alpha = a * (focus && !lit.has(o.key) ? dimmed(0.4) : 1);
      if (moved > 6 && !fixed) {
        // A hairline leader from the flower's edge to the name.
        const bx = Math.max(chosenBox.x0, Math.min(chosenBox.x1, fp.x)), by = Math.max(chosenBox.y0, Math.min(chosenBox.y1, fp.y));
        const d = Math.hypot(bx - fp.x, by - fp.y) || 1;
        const e = edge(dirOf) - 2;
        ctx.globalAlpha = alpha * 0.75;
        ctx.strokeStyle = palette.muted;
        ctx.lineWidth = 0.8;
        ctx.beginPath(); ctx.moveTo(fp.x + (bx - fp.x) / d * e, fp.y + (by - fp.y) / d * e); ctx.lineTo(bx, by); ctx.stroke();
      }
      const cx = (chosenBox.x0 + chosenBox.x1) / 2;
      textWithHalo(name, cx, chosenBox.y0 + 8, nameFont, palette.ink, alpha, 'center', 'middle');
      if (sub) textWithHalo(sub, cx, chosenBox.y0 + 23, subFont, palette.muted, alpha, 'center', 'middle');
      labelBoxes.push({ x0: chosenBox.x0 - 2, x1: chosenBox.x1 + 2, y0: chosenBox.y0 - 1, y1: chosenBox.y1 + 1 });
    };
    if (a > 0.01) {
      // The words live in the panel, in one place. On the map a dial is
      // named only while it is pointed at or chosen, and always the same
      // way: centred under it, its role beneath for the toolkit's own.
      const named = new Set();
      for (const key of [selected, hover]) {
        const o = key ? byKey.get(key) : null;
        if (!o || named.has(o.key) || (o.type !== 'core' && o.type !== 'kernel')) continue;
        named.add(o.key);
        place(o, o.type === 'core' ? coreName(o.core) : proofShortName(o.kernel), o.type === 'core' ? coreSub(o.core) : '', true, true);
      }
    }
    // The flowers are room taken for every label placed after these.
    for (const fp of prints) labelBoxes.push({ x0: fp.x - fp.reach, x1: fp.x + fp.reach, y0: fp.y - fp.reach, y1: fp.y + fp.reach });
    ctx.globalAlpha = 1;
  }

  /* ---- Inscriptions (labels.js) ------------------------------------------- */
  //
  // Every label outside the ring is planned once per paint, before anything
  // is drawn, by one screen-space planner: chrome, the stage chips, the ring,
  // the bezel, rule glyphs (with their obligation arcs) and flower
  // footprints are hard obstacles, and labels are taken in the art
  // direction's priority order (labels.js PRIORITY), ties by id. The draw
  // functions then paint only what was placed. Placed footprints are also
  // filed in labelBoxes, so older box tests (kernel names, plates) step
  // around them.
  //
  // Hooks for the other lanes: push a function onto `obstacleSources` that
  // returns obstacles in screen pixels for this paint, e.g.
  //   obstacleSources.push(() => routes.map((points) => ({ kind: 'polyline', points, pad: 6, tag: 'route' })));
  //   obstacleSources.push(() => flowers.map((f) => ({ kind: 'circle', x: f.x, y: f.y, r: f.footprint, tag: 'flower' })));
  // and push a function onto `candidateSources` that returns label
  // candidates (labels.js createPlanner) to be placed with these, e.g. traced
  // endpoints at PRIORITY.traced; their placements come back in ins.extra.
  const obstacleSources = [];
  const candidateSources = [];
  const CITE_STEP = 15; // the family band's second line, outward
  function familyBand() {
    const k = view.k;
    if (!halo || R.scale * k < 90) return [];
    const famR = (R.cap1 ?? R.scale + 12) * k + 15;
    const chosen = selected ? byKey.get(selected) : null;
    const citers = chosen && chosen.type === 'rule' ? new Set(membersOf(chosen.rule)) : null;
    return L.sectors.map((s) => {
      const num = citers ? `${s.members.filter((id) => citers.has(id)).length} of ${s.count}` : String(s.count);
      const W = textWidth(FONT.family, familyName(s.family)) + textWidth(FONT.family, '  ') + textWidth(citers ? FONT.cite : FONT.familyCount, num);
      const half = (W / 2 + 8) / famR;
      return { a0: s.mid - half, a1: s.mid + half, r0: famR - 9, r1: famR + 9 };
    });
  }
  shared.familyArcs = familyBand;
  const FONT = {
    name: face(500, 12, false, SANS),
    ident: face(600, 12.5, false, SANS),
    id: face(650, 10, false, SANS),
    title: face(500, 11.5, true),
    chosen: face(650, 13.5),
    family: face(600, 14),
    familyCount: face(400, 12.5, true),
    familySmall: face(600, 12.5),
    familyCountSmall: face(400, 11.5, true),
    cite: face(600, 11, false, SANS),
    chipKind: face(700, 10.5, false, SANS),
    chipName: face(600, 13),
    chipFact: face(400, 12, false, SANS),
  };
  const widthCache = new Map();
  function textWidth(font, text) {
    const key = `${font}|${text}`;
    let wd = widthCache.get(key);
    if (wd === undefined) {
      ctx.font = font;
      wd = Number(ctx.measureText(text).width) || 0;
      widthCache.set(key, wd);
    }
    return wd;
  }
  const prefixCache = new Map();
  function prefixWidths(font, text) {
    const key = `${font}|${text}`;
    let arr = prefixCache.get(key);
    if (!arr) {
      ctx.font = font;
      arr = new Float64Array(text.length + 1);
      for (let i = 1; i <= text.length; i += 1) arr[i] = Number(ctx.measureText(text.slice(0, i)).width) || 0;
      prefixCache.set(key, arr);
    }
    return (i) => arr[i];
  }
  const measurer = (font) => (t) => textWidth(font, t);
  // The bezel just outside the halo, in pixels from the centre.
  function bezel() {
    const k = view.k;
    const r0 = (R.haloOuter + 6) * k;
    return { r0, tick: Math.max(2.5, 4 * k), r1: r0 + Math.max(5, 8 * k) };
  }
  // A flower's footprint for the planner until lane 3 supplies its own.

  /** The level of detail now (labels.js LOD), from the local pitch with hysteresis. */
  function currentLod() { return lodLevel ?? levelOfDetail(localPitch(view.k, L.pitch, R.component)); }
  // Kept for callers elsewhere in the engine: true once names are in view.
  function namesShown() { return currentLod() >= LOD.neighbourhood; }

  function chipLines(o) {
    if (o.type === 'component') {
      const n = (o.comp.ruleIds || []).filter((id) => ruleObj.has(id)).length;
      return ['Component', o.comp.title, `${familyName(o.comp.family)} · its record cites ${count(n, 'rule')}`];
    }
    if (o.type === 'rule') {
      return [ruleKindWords(o.kind), `${o.id}  ${o.rule.title}`, o.rule.kind === 'anti_principle'
        ? `${o.rule.exposed.size} of ${compObj.size} components exposed through its axioms`
        : `${o.rule.citedBy.length} of ${compObj.size} components cite it`];
    }
    if (o.type === 'kernel') {
      return ['Proved computation', proofShortName(o.kernel), `${count(o.tasks, 'proof check')} passed · ${count(o.mutants, 'broken copy', 'broken copies')} rejected`];
    }
    if (o.type === 'core') {
      return ['Toolkit computation', coreName(o.core), `${count(o.tasks, 'proof check')} passed · ${count(o.mutants, 'broken copy', 'broken copies')} rejected`];
    }
    return null;
  }
  // The selection chip: kind, name and one fact, in a slot kept above the
  // bottom legend, only while the reading panel is hidden.
  function selectionChip(o, boxes, w, h) {
    const lines = chipLines(o);
    if (!lines) return null;
    const [kindWords, name, fact] = lines;
    const kind = String(kindWords).toUpperCase();
    const legend = boxes.filter((b) => b.role === 'legend');
    const top = legend.length ? Math.min(...legend.map((b) => b.y0)) : h - 12;
    const maxW = Math.min(460, w - 32);
    const kindW = textWidth(FONT.chipKind, kind);
    const nameFit = fitText(name, maxW - 24 - kindW - 8, measurer(FONT.chipName), { minChars: 1 }) || { text: '', width: 0 };
    const factFit = fitText(fact, maxW - 24, measurer(FONT.chipFact), { minChars: 1 }) || { text: '', width: 0 };
    const wd = Math.max(kindW + 8 + nameFit.width, factFit.width) + 24;
    const ht = 46;
    const x0 = w < 520 ? 12 : 18;
    const y1 = top - 8;
    return { box: { x0, y0: y1 - ht, x1: x0 + wd, y1 }, kind, kindW, name: nameFit.text, fact: factFit.text, type: o.type, ruleKind: o.kind };
  }
  // The scope chip, top left: the families in view whose names are off
  // screen. Its slot is the first free one beside or below the corner chrome.
  function scopeChip(planner, missing, boxes, w) {
    const kind = 'IN VIEW';
    const kindW = textWidth(FONT.chipKind, kind);
    const names = missing.map((s) => familyName(s.family));
    const full = names.length <= 2 ? names.join(' · ') : `${names[0]} · ${names[1]} · +${names.length - 2} more`;
    const maxW = Math.min(420, w - 32);
    const fitted = fitText(full, maxW - 24 - kindW - 8, measurer(FONT.chipName), { minChars: 3 });
    if (!fitted) return null;
    const wd = kindW + 8 + fitted.width + 24, ht = 28;
    const left = w < 520 ? 12 : 18;
    const corner = boxes.filter((b) => b.role !== 'legend' && b.y0 < 80 && b.x0 < w / 2);
    const slots = [[left, 14], ...corner.map((b) => [b.x1 + 10, 14]), [left, Math.max(14, ...corner.map((b) => b.y1 + 10))]];
    for (const [x0, y0] of slots) {
      const box = { x0, y0, x1: x0 + wd, y1: y0 + ht };
      if (planner.test([{ t: 'r', ...box }])) continue;
      planner.block({ kind: 'rect', ...box, pad: 4, tag: 'chip' });
      return { box, kind, kindW, text: fitted.text };
    }
    return null;
  }

  // The label plan is a pure function of the camera, the size and chrome,
  // what is chosen, previewed and in focus, the search matches, the routes
  // shown, the level of detail and the fonts and palette. Animation frames
  // with a still camera (focus fades, ignition, route draw-on, the pulse)
  // reuse the last plan and re-file its boxes instead of re-planning.
  let planKey = '', planBoxes = [], planChrome = null;
  function cachedInscriptions(focus, rs, w, h) {
    const chromeNow = chromeBoxes();
    const routes = routeLines.map((l) => `${l.id}:${l.width}`).join(',');
    const key = reveal < 1 ? '' : [view.k, view.tx, view.ty, w, h, fittedK, rs, selected, hover, focus, matchesGen, emphasis, lodLevel,
      fontGen, paletteGen, panelHidden, routeInfo.mode, routes, obstacleSources.length, candidateSources.length].join('|');
    if (key && key === planKey && chromeNow === planChrome && ins) {
      for (const b of planBoxes) labelBoxes.push(b);
      return ins;
    }
    const before = labelBoxes.length;
    const out = planInscriptions(focus, rs, w, h);
    planBoxes = labelBoxes.slice(before);
    planKey = key; planChrome = chromeNow;
    return out;
  }
  function planInscriptions(focus, rs, w, h) {
    const k = view.k, cx = view.tx, cy = view.ty;
    lodLevel = levelOfDetail(localPitch(k, L.pitch, R.component), lodLevel);
    const lod = lodLevel;
    const planner = createPlanner({ bounds: { x0: 2, y0: 2, x1: w - 2, y1: h - 2 }, gap: 4 });
    const boxes = chromeBoxes();
    for (const b of boxes) planner.block({ kind: 'rect', x0: b.x0, y0: b.y0, x1: b.x1, y1: b.y1, pad: 4, tag: 'chrome' });
    const chosen = selected ? byKey.get(selected) : null;
    const preview = hover && hover !== selected ? byKey.get(hover) : null;
    const ruleChosen = chosen && chosen.type === 'rule' ? chosen : null;
    const cap1 = (R.cap1 ?? R.scale + 12) * k;
    const famR = cap1 + 15;
    // The name band starts 10 px past the family line's baseline (its
    // letters stand on famR + 3 or so), clear of the family words.
    const nameFrom = famR + 13;
    const bz = bezel();
    const titleR = bz.r1 + 10;
    const out = { lod, planner, famR, nameFrom, family: new Map(), names: new Map(), ids: new Map(), titles: [], wedge: [], extra: [], scope: null, chip: null };
    if (panelHidden && chosen) {
      const chip = selectionChip(chosen, boxes, w, h);
      if (chip) { out.chip = chip; planner.block({ kind: 'rect', ...chip.box, pad: 4, tag: 'chip' }); }
    }
    // The territories: nothing outside the ring enters it or the caps band,
    // and nothing writes over the bezel.
    planner.block({ kind: 'circle', x: cx, y: cy, r: cap1 + 1, tag: 'ring' });
    if (halo) planner.block({ kind: 'annulus', x: cx, y: cy, r0: bz.r0 - 1, r1: bz.r1 + 1, tag: 'bezel' });
    const glyphR = (o) => rulePx(o, rs) / 2 + (o.kind === 'axiom' && o.rule.obligations.length && rulePx(o, rs) >= 11 ? 5.1 : 1.8);
    for (const o of ruleObj.values()) planner.block({ kind: 'circle', x: sx(o.x), y: sy(o.y), r: glyphR(o), pad: 3, tag: 'glyph' });
    for (const fp of flowerFootprints()) planner.block({ kind: 'circle', x: fp.x, y: fp.y, r: fp.r, tag: 'flower' });
    for (const kk of kernelObj.values()) if (kk.thread && kk.thread.length > 1) planner.block({ kind: 'polyline', points: kk.thread.map(([x, y]) => [sx(x), sy(y)]), pad: 3, tag: 'stem' });
    for (const line of routeLines) planner.block({ kind: 'polyline', points: line.pts, pad: 6, tag: 'route' });
    for (const source of obstacleSources) for (const ob of source({ k, cx, cy, w, h }) || []) planner.block(ob);

    const onScreenAt = (angle, r) => {
      const x = cx + Math.cos(angle) * r, y = cy + Math.sin(angle) * r;
      return x > -2 && y > -2 && x < w + 2 && y < h + 2;
    };
    const fo = focus ? byKey.get(focus) : null;
    const hf = haloFocus(fo);
    const isLit = (id) => hf.direct.has(id) || hf.soft.has(id);
    const lowerAt = (a) => Math.sin(a) > 0.08;

    const nameCand = (c, priority) => {
      const title = c.comp.title;
      const prefix = prefixWidths(FONT.name, title);
      return { id: `name:${c.id}`, priority, data: { c },
        fit: (px) => fitText(title, px, measurer(FONT.name), { prefix, minChars: 4 }),
        anchors: [{ kind: 'radial', cx, cy, angle: c.angle, from: nameFrom, length: prefix(title.length) + 1, height: 11 }] };
    };
    // A chosen or previewed component keeps its whole name: on its own
    // radius when that is free, else level type beside it on a short leader,
    // and only as a last resort cut short on its radius.
    const identityCand = (c, priority) => {
      const title = c.comp.title;
      const prefix = prefixWidths(FONT.name, title);
      const full = prefix(title.length);
      const whole = (px) => (px >= full ? { text: title, width: full } : null);
      const cut = (px) => fitText(title, px, measurer(FONT.name), { prefix, minChars: 4 });
      const anchors = [{ kind: 'radial', cx, cy, angle: c.angle, from: nameFrom, length: full + 1, height: 11, fit: whole }];
      const cs = Math.cos(c.angle), sn = Math.sin(c.angle);
      const W = textWidth(FONT.ident, title) + 10, H = 18;
      for (const d of [nameFrom + 4, nameFrom + 26, bz.r1 + 12, bz.r1 + 36]) {
        const px = cx + cs * d, py = cy + sn * d;
        const x0 = cs > 0.25 ? px : cs < -0.25 ? px - W : px - W / 2;
        const y0 = sn > 0.25 ? py : sn < -0.25 ? py - H : py - H / 2;
        anchors.push({ kind: 'rect', x0, y0, x1: x0 + W, y1: y0 + H, level: true, foot: [cx + cs * nameFrom, cy + sn * nameFrom], fit: () => ({ text: title, width: W }) });
      }
      anchors.push({ kind: 'radial', cx, cy, angle: c.angle, from: nameFrom, length: full + 1, height: 11, fit: cut });
      return { id: `name:${c.id}`, priority, data: { c }, anchors };
    };
    // Along the rule's own orbit, starting just past its mark (and past its
    // number), on either side.
    const orbitAnchors = (o, text, font, W, height) => {
      const ro = o.orbit * k;
      const g = glyphR(o) + 5;
      const idW = textWidth(FONT.id, o.id) + 10;
      const out = [];
      for (const extra of [0, idW]) for (const side of [1, -1]) {
        const mid = o.angle + side * (g + extra + W / 2) / ro;
        out.push({ kind: 'arc', cx, cy, radius: ro, mid, width: W, height, text, font, lower: lowerAt(mid) });
      }
      return out;
    };
    const ruleTitleCand = (o, priority) => {
      const text = `${o.id}  ${o.rule.title}`;
      const W = textWidth(FONT.chosen, text);
      const anchors = [];
      const half = W / 2 / titleR;
      for (const t of [0, 0.5, -0.5, 1, -1, 1.5, -1.5]) {
        const mid = o.angle + t * half;
        anchors.push({ kind: 'arc', cx, cy, radius: titleR, mid, width: W, height: 15, text, font: FONT.chosen, lower: lowerAt(mid) });
      }
      anchors.push(...orbitAnchors(o, text, FONT.chosen, W, 15));
      // Under the principles' orbit, clear of the names it outranks.
      const innerR = R.principles * k - rulePx(o, rs) - 14;
      for (const t of [0, 0.6, -0.6]) {
        const mid = o.angle + t * W / 2 / innerR;
        anchors.push({ kind: 'arc', cx, cy, radius: innerR, mid, width: W, height: 15, text, font: FONT.chosen, lower: lowerAt(mid) });
      }
      const x = sx(o.x), y = sy(o.y), z = glyphR(o) + 8, ht = 17;
      for (const [dx, dy] of [[0, -1], [0, 1], [1, 0], [-1, 0]]) {
        const bx = dx > 0 ? x + z : dx < 0 ? x - z - W : x - W / 2;
        const by = dy > 0 ? y + z : dy < 0 ? y - z - ht : y - ht / 2;
        anchors.push({ kind: 'rect', x0: bx, y0: by, x1: bx + W, y1: by + ht, text, font: FONT.chosen });
      }
      return { id: `title:${o.id}`, priority, anchors, data: { o } };
    };
    const idCand = (o, priority) => {
      const wd = textWidth(FONT.id, o.id) + 2, ht = 12;
      const z = glyphR(o) + 3 + 1.5;
      const x = sx(o.x), y = sy(o.y);
      const anchors = [];
      // Beside the mark along its orbit (clockwise first), else out, else in.
      for (const t of [o.angle + Math.PI / 2, o.angle - Math.PI / 2, o.angle, o.angle + Math.PI]) {
        const ax = Math.cos(t), ay = Math.sin(t);
        const lx = x + ax * z, ly = y + ay * z;
        const x0 = ax > 0.3 ? lx : ax < -0.3 ? lx - wd : lx - wd / 2;
        const y0 = ay > 0.3 ? ly : ay < -0.3 ? ly - ht : ly - ht / 2;
        anchors.push({ kind: 'rect', x0, y0, x1: x0 + wd, y1: y0 + ht });
      }
      return { id: `id:${o.id}`, priority, anchors, data: { o } };
    };
    const titleCand = (o, priority) => {
      const text = o.rule.title;
      const W = textWidth(FONT.title, text);
      const half = W / 2 / titleR;
      const anchors = orbitAnchors(o, text, FONT.title, W, 13);
      for (const t of [0, 0.4, -0.4]) {
        const mid = o.angle + t * half;
        anchors.push({ kind: 'arc', cx, cy, radius: titleR, mid, width: W, height: 13, text, font: FONT.title, lower: lowerAt(mid) });
      }
      return { id: `title:${o.id}`, priority, anchors, data: { o } };
    };

    // First the identities and the families.
    const first = [];
    const named = new Set();
    const titled = new Set();
    for (const [o, priority] of [[chosen, PRIORITY.chosen], [preview, PRIORITY.preview]]) {
      if (!o) continue;
      if (o.type === 'rule' && halo) { first.push(ruleTitleCand(o, priority)); titled.add(o.id); }
      if (o.type === 'component') { first.push(identityCand(o, priority)); named.add(o.id); }
    }
    if (matches && matches.size <= 24) {
      for (const id of matches) {
        const c = compObj.get(id);
        if (!c || named.has(id) || !onScreenAt(c.angle, nameFrom)) continue;
        first.push(nameCand(c, PRIORITY.search)); named.add(id);
      }
    }
    const citers = ruleChosen ? new Set(membersOf(ruleChosen.rule)) : null;
    out.citeInk = ruleChosen && ruleChosen.rule.kind === 'anti_principle' ? palette.threat : palette.doctrine;
    for (const s of L.sectors) {
      const name = familyName(s.family);
      const num = citers ? `${s.members.filter((id) => citers.has(id)).length} of ${s.count}` : String(s.count);
      const cite = null, citeInline = !!citers;
      const citeW = 0;
      const halfSector = (s.hi - s.lo) / 2;
      const anchors = [];
      const slides = [0, 0.125, -0.125, 0.25, -0.25, 0.375, -0.375, 0.5, -0.5, 0.625, -0.625, 0.75, -0.75, 0.875, -0.875, 1, -1];
      // In the family band; on a drawing too small for the band under the
      // halo, outside the bezel instead, on the family's own radius, at the
      // full size, then smaller, then a step further out.
      const tiers = [[famR, FONT.family, FONT.familyCount, 15]];
      if (halo) tiers.push([titleR + 2, FONT.family, FONT.familyCount, 15], [titleR, FONT.familySmall, FONT.familyCountSmall, 13], [titleR + 17, FONT.familySmall, FONT.familyCountSmall, 13]);
      for (const [radius, nameFont, numFont0, height] of tiers) {
        const numFont = citeInline ? FONT.cite : numFont0;
        const nameW = textWidth(nameFont, name), numW = textWidth(numFont, num);
        const W = nameW + textWidth(nameFont, '  ') + numW;
        const half = Math.max(W, citeW) / 2 / radius;
        const span = Math.max(halfSector - half, halfSector * 0.5);
        for (const t of slides) {
          const mid = s.mid + t * span;
          const shape = arcDiscs(cx, cy, radius, mid, W, height);
          if (cite) shape.push(...arcDiscs(cx, cy, radius + CITE_STEP, mid, citeW, 12));
          anchors.push({ kind: 'shape', shape, mid, radius, lower: lowerAt(mid), W, nameW, numW, name, num, cite, citeInline, nameFont, numFont });
        }
      }
      // Last, level type beyond the bezel on the family's own bearing (a
      // small drawing has room above and below the halo, not round it).
      if (halo) {
        const flatNum = citeInline ? FONT.cite : FONT.familyCountSmall;
        const nameW = textWidth(FONT.familySmall, name), numW = textWidth(flatNum, num);
        const gapW = textWidth(FONT.familySmall, '  ');
        const W = Math.max(nameW + gapW + numW, citeW), ht = cite ? 30 : 16;
        for (const out of [6, 24, 42]) for (const t of [0, 0.5, -0.5, 1, -1]) {
          const mid = s.mid + t * halfSector;
          const ax = Math.cos(mid), ay = Math.sin(mid);
          const px = cx + ax * (bz.r1 + out), py = cy + ay * (bz.r1 + out);
          const x0 = ax > 0.3 ? px : ax < -0.3 ? px - W : px - W / 2;
          const y0 = ay > 0.3 ? py : ay < -0.3 ? py - ht : py - ht / 2;
          anchors.push({ kind: 'rect', flat: true, x0, y0, x1: x0 + W, y1: y0 + ht, name, num, cite, citeInline, nameW, gapW, numW, nameFont: FONT.familySmall, numFont: flatNum });
        }
      }
      first.push({ id: `family:${s.family}`, priority: PRIORITY.family, anchors, data: { s }, ignore: ['route'] });
    }
    for (const source of candidateSources) for (const c of source({ k, cx, cy, w, h, lod }) || []) first.push(c);
    const placedFirst = planner.plan(first);

    // The scope chip, when a family in view has its name off screen (or, on
    // a drawing too small for every name, nowhere to stand): family names
    // never simply disappear.
    {
      const missing = L.sectors.filter((s) => !placedFirst.has(`family:${s.family}`) && s.members.some((id) => {
        const c = compObj.get(id);
        return onScreenAt(c.angle, nameFrom) || onScreenAt(c.angle, R.component * k);
      }));
      if (missing.length) out.scope = scopeChip(planner, missing, boxes, w);
    }

    // Then the doctrine's numbers, the components' names, titles and the wedge.
    const rest = [];
    if (halo) {
      for (const o of ruleObj.values()) {
        if (titled.has(o.id)) continue;
        if (!onScreenAt(o.angle, Math.hypot(o.x, o.y) * k) && !(sx(o.x) > -20 && sx(o.x) < w + 20 && sy(o.y) > -20 && sy(o.y) < h + 20)) continue;
        if (isLit(o.id)) rest.push(idCand(o, PRIORITY.litRuleId));
        else if (lod >= LOD.neighbourhood) rest.push(idCand(o, PRIORITY.ruleId));
      }
    }
    if (lod >= LOD.neighbourhood) {
      for (const c of compObj.values()) {
        if (named.has(c.id) || (matches && !matches.has(c.id)) || !onScreenAt(c.angle, nameFrom)) continue;
        rest.push(nameCand(c, PRIORITY.componentName));
      }
    }
    if (halo && lod >= LOD.neighbourhood) {
      for (const o of ruleObj.values()) {
        if (titled.has(o.id)) continue;
        const lit = isLit(o.id);
        // Reading close in, an axiom's title on its own orbit belongs to its
        // mark (a glyph's label, which names never cross), so it is placed
        // just after the rule numbers, before the names it would otherwise
        // lose to; lit axioms further out keep their own priority.
        if (o.kind === 'axiom' && lod >= LOD.reading) rest.push(titleCand(o, PRIORITY.ruleId + 0.5));
        else if (o.kind === 'axiom' && lit) rest.push(titleCand(o, PRIORITY.litAxiomTitle));
        else if (lod >= LOD.reading && (o.kind === 'axiom' || (o.kind === 'principle' && lit))) rest.push(titleCand(o, PRIORITY.title));
      }
    }
    for (const c of wedgeCandidates(fo, cx, cy)) rest.push(c);
    const placedRest = planner.plan(rest);

    for (const [id, p] of [...placedFirst, ...placedRest]) {
      if (id.startsWith('family:')) out.family.set(id, p);
      else if (id.startsWith('name:')) out.names.set(id, p);
      else if (id.startsWith('id:')) out.ids.set(id, p);
      else if (id.startsWith('title:')) out.titles.push(p);
      else if (id.startsWith('wedge:')) out.wedge.push(p);
      else out.extra.push(p);
    }
    for (const b of planner.boxes()) labelBoxes.push(b);
    for (const chip of [out.chip, out.scope]) if (chip) labelBoxes.push({ x0: chip.box.x0 - 4, x1: chip.box.x1 + 4, y0: chip.box.y0 - 4, y1: chip.box.y1 + 4 });
    return out;
  }

  // Component names along their radii in the name band, as planned:
  // measured, cut with an ellipsis at the first obstacle, never across one.
  function drawComponentNames(focus, lit) {
    if (!ins || !ins.names.size) return;
    const a = revealAlpha(REVEAL.words);
    if (a <= 0.01) return;
    const r0 = ins.nameFrom;
    const m = ctx.getTransform ? ctx.getTransform() : null;
    ctx.font = FONT.name;
    ctx.textBaseline = 'middle';
    ctx.lineWidth = 3;
    ctx.lineJoin = 'round';
    for (const p of ins.names.values()) {
      const c = p.data.c;
      const text = p.fitted.text;
      if (p.anchor.level) {
        if (m) ctx.setTransform(m);
        const { x0, y0, x1, y1, foot } = p.anchor;
        const lx = Math.max(x0, Math.min(x1, foot[0])), ly = Math.max(y0, Math.min(y1, foot[1]));
        ctx.save();
        ctx.globalAlpha = a * 0.7;
        ctx.strokeStyle = palette.muted;
        ctx.lineWidth = hairPx * 1.4;
        ctx.beginPath(); ctx.moveTo(foot[0], foot[1]); ctx.lineTo(lx, ly); ctx.stroke();
        ctx.globalAlpha = a;
        ctx.font = FONT.ident;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'middle';
        ctx.lineWidth = 3;
        ctx.strokeStyle = palette.ground;
        ctx.strokeText(text, x0 + 5, (y0 + y1) / 2);
        ctx.fillStyle = c.formal ? palette.red : palette.ink;
        ctx.fillText(text, x0 + 5, (y0 + y1) / 2);
        ctx.restore();
        ctx.font = FONT.name;
        ctx.textBaseline = 'middle';
        continue;
      }
      const cs = Math.cos(c.angle), sn = Math.sin(c.angle);
      const flip = cs < 0;
      const context = focus && !lit.has(c.key) && p.priority > PRIORITY.preview;
      const x = view.tx + cs * r0, y = view.ty + sn * r0;
      const rc = flip ? -cs : cs, rsn = flip ? -sn : sn; // the rotation's cos and sin
      if (m) ctx.setTransform(m.a * rc + m.c * rsn, m.b * rc + m.d * rsn, m.c * rc - m.a * rsn, m.d * rc - m.b * rsn, m.a * x + m.c * y + m.e, m.b * x + m.d * y + m.f);
      else { ctx.save(); ctx.translate(x, y); ctx.rotate(flip ? c.angle + Math.PI : c.angle); }
      ctx.textAlign = flip ? 'right' : 'left';
      ctx.globalAlpha = a * (context ? 0.5 : 1);
      ctx.strokeStyle = palette.ground;
      ctx.strokeText(text, 0, 0);
      ctx.fillStyle = c.formal ? palette.red : palette.ink;
      ctx.fillText(text, 0, 0);
      if (!m) ctx.restore();
    }
    if (m) ctx.setTransform(m);
    ctx.globalAlpha = 1;
  }

  // The two stage chips, drawn last, over the map: the scope chip and the
  // selection chip.
  function chipFrame(box) {
    ctx.globalAlpha = 0.95;
    ctx.fillStyle = palette.ground;
    ctx.beginPath();
    const wd = box.x1 - box.x0, ht = box.y1 - box.y0;
    if (ctx.roundRect) ctx.roundRect(box.x0, box.y0, wd, ht, 7); else ctx.rect(box.x0, box.y0, wd, ht);
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.strokeStyle = palette.muted;
    ctx.lineWidth = hairPx * 1.5;
    ctx.stroke();
  }
  function drawStageChips() {
    if (!ins) return;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    const sc = ins.scope;
    if (sc) {
      chipFrame(sc.box);
      const y = (sc.box.y0 + sc.box.y1) / 2;
      ctx.font = FONT.chipKind; ctx.fillStyle = palette.muted; ctx.fillText(sc.kind, sc.box.x0 + 12, y + 0.5);
      ctx.font = FONT.chipName; ctx.fillStyle = palette.ink; ctx.fillText(sc.text, sc.box.x0 + 12 + sc.kindW + 8, y);
    }
    const ch = ins.chip;
    if (ch) {
      chipFrame(ch.box);
      const y1 = ch.box.y0 + 16, y2 = ch.box.y0 + 33;
      ctx.font = FONT.chipKind;
      ctx.fillStyle = ch.type === 'rule' ? (ch.ruleKind === 'anti_principle' ? palette.threat : palette.doctrine) : ch.type === 'component' ? palette.muted : palette.red;
      ctx.fillText(ch.kind, ch.box.x0 + 12, y1 + 0.5);
      ctx.font = FONT.chipName; ctx.fillStyle = palette.ink; ctx.fillText(ch.name, ch.box.x0 + 12 + ch.kindW + 8, y1);
      ctx.font = FONT.chipFact; ctx.fillStyle = palette.muted; ctx.fillText(ch.fact, ch.box.x0 + 12, y2);
    }
    ctx.globalAlpha = 1;
  }

  function drawPulse(rs) {
    if (!pulse.key || pulse.ms >= pulse.end) return;
    const o = byKey.get(pulse.key);
    if (!o) return;
    const phase = (delay, length) => clamp01((pulse.ms - delay) / length);
    const t = phase(0, CHOSEN_RING);
    const x = sx(o.x), y = sy(o.y), r = (o.type === 'component' ? o.r * rs : o.type === 'rule' ? rulePx(o, rs) / 2 : petalPx(o, rs) * 0.5) + 1.5;
    const inkOf = (name) => (name === 'stated' ? palette.stated : name === 'doctrine' ? palette.doctrine : palette.red);
    if (t > 0 && t < 1) {
      // "This was chosen": one soft ring leaves the mark at once and expands
      // as it fades, a wide faint band under a fine bright edge.
      const e = 1 - (1 - t) ** 3;
      const rr = r + 2 + e * Math.max(18, r * 1.8);
      const fadeOut = (1 - t) ** 1.6;
      ctx.strokeStyle = o.type === 'rule' ? palette.doctrine : o.type === 'component' && !o.formal ? (darkGround ? palette.stated : palette.ink) : palette.red;
      if (darkGround) ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = (darkGround ? 0.2 : 0.12) * fadeOut;
      ctx.lineWidth = 3 + 6 * e;
      ctx.beginPath(); ctx.arc(x, y, rr, 0, TURN); ctx.stroke();
      ctx.globalAlpha = (darkGround ? 0.85 : 0.7) * fadeOut;
      ctx.lineWidth = 1.3;
      ctx.beginPath(); ctx.arc(x, y, rr, 0, TURN); ctx.stroke();
      ctx.globalCompositeOperation = 'source-over';
    }
    const sizePx = Math.max(0.8, rs);
    for (const leg of pulse.legs) {
      const p = phase(leg.delay, leg.dur);
      if (p <= 0 || p >= 1) continue;
      const fadeIn = Math.min(1, p * 6, (1 - p) * 6);
      const color = inkOf(leg.ink);
      ctx.fillStyle = color;
      for (let d = 3; d >= 1; d -= 1) {
        const tail = alongPath(leg.pts, ease(Math.max(0, p - d * 0.035)));
        ctx.globalAlpha = fadeIn * (0.56 - d * 0.14);
        ctx.beginPath(); ctx.arc(sx(tail[0]), sy(tail[1]), Math.max(0.7, (2.2 - d * 0.4) * sizePx), 0, TURN); ctx.fill();
      }
      const bead = alongPath(leg.pts, ease(p));
      ctx.globalAlpha = fadeIn;
      ctx.fillStyle = darkGround ? palette.ink : color;
      ctx.beginPath(); ctx.arc(sx(bead[0]), sy(bead[1]), 2.1 * sizePx, 0, TURN); ctx.fill();
    }
    for (const b of pulse.blooms) {
      const m = byKey.get(b.key);
      const p = phase(b.at, PULSE_BLOOM);
      if (!m || p <= 0 || p >= 1) continue;
      const e = 1 - (1 - p) ** 3;
      const mr = m.type === 'component' ? m.r * rs : m.type === 'rule' ? rulePx(m, rs) / 2 : petalPx(m, rs) * 0.6;
      ctx.globalAlpha = 0.7 * (1 - e);
      ctx.lineWidth = 1.3;
      ctx.strokeStyle = inkOf(b.ink);
      ctx.beginPath(); ctx.arc(sx(m.x), sy(m.y), mr + 2 + e * Math.max(12, mr * 1.1), 0, TURN); ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  // (No canvas fact plates: the panel explains what is chosen or previewed;
  // lane 2 adds a compact selection chip when the panel is hidden.)

  // Four corner ticks round what the pointer is on and what is kept.
  function drawReticles(rs) {
    for (const key of [selected, hover]) {
      if (!key) continue;
      const o = byKey.get(key);
      if (!o) continue;
      const s = o.type === 'component' ? o.r * rs + 5 : o.type === 'rule' ? rulePx(o, rs) / 2 + (o.kind === 'axiom' ? 8 : 5) : petalPx(o) + 3;
      const x = sx(o.x), y = sy(o.y);
      const arm = Math.max(3, Math.min(7, s * 0.35));
      ctx.globalAlpha = key === selected ? 0.92 : 0.7;
      ctx.fillStyle = palette.ink;
      for (const [cx, cy, dx, dy] of [[x - s, y - s, 1, 1], [x + s, y - s, -1, 1], [x - s, y + s, 1, -1], [x + s, y + s, -1, -1]]) {
        ctx.fillRect(dx > 0 ? cx : cx - arm, dy > 0 ? cy : cy - hairPx, arm, hairPx * 1.4);
        ctx.fillRect(dx > 0 ? cx : cx - hairPx, dy > 0 ? cy : cy - arm, hairPx * 1.4, arm);
      }
    }
    ctx.globalAlpha = 1;
  }

  /* ---- Hit testing --------------------------------------------------------- */
  // Returns [object, track index or -1].
  function hit(px, py) {
    const rs = rScale();
    const k = view.k;
    const dx = px - view.tx, dy = py - view.ty;
    const rr = Math.hypot(dx, dy) / k;
    // Within the rings and the register, the pointer is on a component's column.
    if (rr >= R.component - 8 && rr <= R.cap1 + 3) {
      const ang = Math.atan2(dy, dx);
      let best = null, bestD = Infinity;
      for (const c of compObj.values()) {
        const d = Math.abs(shortArc(c.angle, ang));
        if (d < bestD) { best = c; bestD = d; }
      }
      if (best && bestD <= L.pitch * 0.62) {
        let track = -1;
        TRACKS.forEach((t, i) => { const [r0, r1] = trackBand(i); if (rr >= r0 - 1.3 && rr <= r1 + 1.3) track = i; });
        return [best, track];
      }
    }
    let best = null, bestD = Infinity;
    for (const o of objects) {
      if (o.type === 'component') continue;
      const x = sx(o.x), y = sy(o.y);
      const reach = o.type === 'rule' ? Math.max(10, rulePx(o, rs) / 2 + 5) : Math.max(12, flowerOf(o).reach);
      const d = Math.hypot(px - x, py - y);
      if (d <= reach && d < bestD) { best = o; bestD = d; }
    }
    if (!best) {
      // The chain's markers belong to their kernel.
      for (const kk of kernelObj.values()) {
        for (const pt of [kk.generated, kk.caller]) {
          if (pt && Math.hypot(px - sx(pt[0]), py - sy(pt[1])) < 10) return [kk, -1];
        }
      }
    }
    return [best, -1];
  }

  /* ---- Public operations --------------------------------------------------- */
  // Choosing pins an object: it owns the lit set, the alidade and the card.
  // It never zooms; the camera pans only if the object is off screen.
  function select(key, { camera = true, emit = true } = {}) {
    const o = key ? byKey.get(key) : null;
    selected = o ? o.key : null;
    pulsedSelection = null;
    if (o && camera) ensureVisible(o);
    if (emit && hooks.onSelect) hooks.onSelect(o);
    requestFull();
  }
  // A preview (pointer, or a panel row) only adds a comparison. Every change
  // of object or ring is told, with the ring and the relation to the chosen
  // object: hooks.onHover(o, { track, relation, source }).
  function setHover(o, track = -1, source = 'pointer') {
    const key = o ? o.key : null;
    const t = key ? track : -1;
    if (key === hover && t === hoverTrack) return;
    hover = key;
    hoverTrack = t;
    if (source === 'pointer') canvas.style.cursor = key ? 'pointer' : '';
    if (hooks.onHover) hooks.onHover(o, { track: t, relation: relationOf(selected ? byKey.get(selected) : null, o), source });
    requestFull();
  }  function zoomAt(px, py, factor) {
    const k = Math.max(fittedK * 0.8, Math.min(fittedK * 9, view.k * factor));
    const f = k / view.k;
    view.tx = px - (px - view.tx) * f;
    view.ty = py - (py - view.ty) * f;
    view.k = k;
    viewIsFitted = false;
    request();
  }

  /* ---- Input ---------------------------------------------------------------- */
  const pointers = new Map();
  let drag = null, pinch = null, moved = false;
  canvas.addEventListener('pointerdown', (e) => {
    settleReveal();
    canvas.setPointerCapture?.(e.pointerId);
    pointers.set(e.pointerId, [e.offsetX, e.offsetY]);
    moved = false;
    if (pointers.size === 1) drag = { x: e.offsetX, y: e.offsetY, tx: view.tx, ty: view.ty };
    if (pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), k: view.k, cx: (a[0] + b[0]) / 2, cy: (a[1] + b[1]) / 2 };
      drag = null;
    }
  });
  canvas.addEventListener('pointermove', (e) => {
    if (pointers.has(e.pointerId)) pointers.set(e.pointerId, [e.offsetX, e.offsetY]);
    if (pinch && pointers.size === 2) {
      const [a, b] = [...pointers.values()];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      markGesture();
      zoomAt(pinch.cx, pinch.cy, (pinch.k * d / pinch.d) / view.k);
      moved = true;
      return;
    }
    if (drag && (Math.abs(e.offsetX - drag.x) > 4 || Math.abs(e.offsetY - drag.y) > 4 || moved)) {
      moved = true;
      markGesture();
      view.tx = drag.tx + e.offsetX - drag.x;
      view.ty = drag.ty + e.offsetY - drag.y;
      viewIsFitted = false;
      setHover(null);
      request();
      return;
    }
    if (!pointers.size) setHover(...hit(e.offsetX, e.offsetY));
  });
  const release = (e) => {
    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinch = null;
    if (!pointers.size) drag = null;
  };
  canvas.addEventListener('pointerup', (e) => {
    const wasMoved = moved;
    release(e);
    if (wasMoved) return;
    const [o] = hit(e.offsetX, e.offsetY);
    if (o) select(o.key);
    else if (selected) select(null);
  });
  canvas.addEventListener('pointercancel', release);
  canvas.addEventListener('pointerleave', () => { if (!pointers.size) setHover(null); });
  canvas.addEventListener('dblclick', (e) => {
    const [o] = hit(e.offsetX, e.offsetY);
    if (o && hooks.onOpen) hooks.onOpen(o);
  });
  canvas.addEventListener('wheel', (e) => {
    settleReveal();
    e.preventDefault();
    const factor = Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0016));
    markGesture();
    zoomAt(e.offsetX, e.offsetY, factor);
  }, { passive: false });
  // Keys: arrows walk the ring, Enter opens, Escape lets go, +/- zoom, 0 fits.
  const ring = L.sectors.flatMap((s) => s.members);
  canvas.addEventListener('keydown', (e) => {
    settleReveal();
    const cur = selected && byKey.get(selected);
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft' || e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const step = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : -1;
      let at = cur && cur.type === 'component' ? ring.indexOf(cur.id) : -1;
      at = at < 0 ? (step > 0 ? 0 : ring.length - 1) : (at + step + ring.length) % ring.length;
      select(`comp:${ring[at]}`);
    } else if (e.key === 'Enter' && cur && hooks.onOpen) {
      hooks.onOpen(cur);
    } else if (e.key === 'Escape' && (hover || selected)) {
      // First the preview goes, then the choice. The page's own Escape
      // handler skips a key already handled here.
      e.preventDefault();
      if (hover && hover !== selected) setHover(null);
      else { setHover(null); select(null); }    } else if (e.key === '+' || e.key === '=') {
      zoomAt(canvas.clientWidth / 2, canvas.clientHeight / 2, 1.35);
    } else if (e.key === '-' || e.key === '_') {
      zoomAt(canvas.clientWidth / 2, canvas.clientHeight / 2, 1 / 1.35);
    } else if (e.key === '0') {
      cameraTo(fitTarget(), true);
    }
  });

  /* ---- Lifecycle ------------------------------------------------------------ */
  const onTheme = () => { if (destroyed) return; readPalette(); paletteGen += 1; invalidateGeometry(); requestFull(); };
  const schemeQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  schemeQuery?.addEventListener?.('change', onTheme);
  document.addEventListener('plectis:theme', onTheme);
  const onReducedMotion = () => {
    reduceMotion = !!reduceQuery.matches;
    if (!reduceMotion || destroyed) return;
    for (const id of [cameraFrame, focusFrame, revealFrame, growthFrame, tweenFrame, pulse.frame]) cancelAnimation(id);
    cameraFrame = focusFrame = revealFrame = growthFrame = tweenFrame = pulse.frame = 0;
    tweens.clear();
    cameraFinish?.();
    reveal = 1; pulse.ms = 1e9; growth = 1; sweepMs = 1e9;
    focusMix = hover || selected ? 1 : 0; focusHeld = null; focusFade = null;
    request();
  };
  reduceQuery?.addEventListener?.('change', onReducedMotion);
  const resize = () => {
    if (destroyed) return;
    const [oldW, oldH] = size();
    const keepCentre = !viewIsFitted ? [(oldW / 2 - view.tx) / view.k, (oldH / 2 - view.ty) / view.k] : null;
    invalidateGeometry();
    needFull = true;
    if (viewIsFitted) fit();
    else if (keepCentre) {
      fittedK = fitTarget().k;
      const [w, h] = size();
      view.tx = w / 2 - keepCentre[0] * view.k;
      view.ty = h / 2 - keepCentre[1] * view.k;
    }
    request();
  };
  observer = 'ResizeObserver' in window ? new ResizeObserver(resize) : null;
  observer?.observe(canvas);
  // Chrome can move without changing canvas size (panel visibility, zoom
  // classes, replaced legend text), so dimensions alone are not sufficient.
  const mutations = 'MutationObserver' in window ? new MutationObserver((records) => {
    if (records.some((record) => record.target !== canvas)) resize();
  }) : null;
  if (stage) mutations?.observe(stage, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['class', 'style', 'hidden'] });
  for (let el = stage?.parentElement; el; el = el.parentElement) {
    mutations?.observe(el, { attributes: true, attributeFilter: ['class', 'style', 'hidden', 'data-explorer-shown', 'data-theme'] });
  }
  window.addEventListener('resize', resize);
  const visibility = () => { if (!document.hidden) resize(); };
  document.addEventListener('visibilitychange', visibility);
  const fontsReady = () => { if (destroyed) return; arcCache.clear(); widthCache.clear(); prefixCache.clear(); fontGen += 1; needFull = true; resize(); };
  document.fonts?.ready?.then(fontsReady);
  document.fonts?.addEventListener?.('loadingdone', fontsReady);

  readPalette();
  fit();
  if (hooks.skipReveal) reveal = 1; else startReveal();
  request();

  return {
    select,
    selectedKey: () => selected,
    // A panel row's hover goes through the same preview path as the pointer.
    hoverKey: (key) => setHover(key ? byKey.get(key) || null : null, -1, 'panel'),
    previewKey: () => hover,
    view: () => ({ ...view }),
    focus: focusOn,
    routeState: () => ({ ...routeInfo }),
    relation: () => relationOf(selected ? byKey.get(selected) : null, hover ? byKey.get(hover) : null),
    activeRoutePolylines: () => routeLines,
    shared,

    setMatches(set) { matches = set; matchesGen += 1; requestFull(); },
    emphasise(trackId) { emphasis = trackId || null; requestFull(); },
    showWiring(on) { allWiring = !!on; requestFull(); return allWiring; },
    // How the last frames were made: full paints and cached (blit) frames.
    paintStats: () => ({ ...stats, gesturing }),
    hasHalo: !!halo,
    fit: () => cameraTo(fitTarget(), true),
    zoomBy: (f) => zoomAt(canvas.clientWidth / 2, canvas.clientHeight / 2, f),
    resize,
    refreshPalette: onTheme,
    objectFor: (key) => byKey.get(key) || null,
    flowerFootprints,
    destroy() {
      destroyed = true;
      observer?.disconnect();
      mutations?.disconnect();
      window.removeEventListener('resize', resize);
      reduceQuery?.removeEventListener?.('change', onReducedMotion);
      document.fonts?.removeEventListener?.('loadingdone', fontsReady);
      document.removeEventListener('plectis:theme', onTheme);
      document.removeEventListener('visibilitychange', visibility);
      schemeQuery?.removeEventListener?.('change', onTheme);
      if (frame) cancelAnimationFrame(frame);
      if (settleTimer) clearTimeout(settleTimer);
      settleTimer = 0;
      animations.clear();
    },
  };
}
