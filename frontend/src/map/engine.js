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
// computations inside the ring, drawn as flowers with one petal per verified
// task, and the coverage rings outside it, read like the tracks of a
// circular genome plot, one ring per kind of check.

import { glowSprite, isDark, mixOklab, parseColor, rgbText } from './color.js';
import { KEY_GAP, layout, polar, R, shortArc, threadAngle, trackBand } from './layout.js';
import { CORE_NAMES, TRACKS, classWords, count, familyName, moduleWords, proofShortName } from '../evidence.js';

const SERIF = '"Plectis Serif", "Plectis Math", "Plectis Serif Fallback", Georgia, serif';
const SANS = '"Plectis Sans", "Plectis Sans Fallback", -apple-system, "Segoe UI", Arial, sans-serif';
const face = (weight, size, italic, family = SERIF) => `${italic ? 'italic ' : ''}${weight} ${size}px ${family}`;
const TYPE = { title: 14, count: 12.5, rowGap: 16, plate: 13.5, sub: 11.5, anchor: 13.5, kernel: 12, name: 11.5 };

const FOCUS_IN = 180, FOCUS_HOLD = 140, FOCUS_OUT = 220;
const PULSE_WAIT = 110, PULSE_RIPPLE = 720, PULSE_TRAVEL = 620, PULSE_STAGGER = 70, PULSE_BLOOM = 560;
// The opening runs from the centre out: the cores flower, the replay spokes
// reach the ring, the kernels flower, their threads grow, the components
// appear round the ring, then each coverage ring is read clockwise in turn.
const REVEAL = { core: 0, cores: 140, spokes: 260, spokeDur: 520, kernels: 380, threads: 560, threadDur: 520, pen: 640, penDur: 900, tracks: 900, trackLag: 110, trackDur: 760, words: 1500, fade: 380, end: 2500 };
const GROW_MS = 260;
const COMPACT_SCALE = 190;
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
    const thread = [];
    if (k.to !== null) {
      for (let s = 0; s <= 28; s += 1) {
        const r = R.kernel + (R.component - R.kernel) * (s / 28);
        thread.push(polar(threadAngle(k.angle, k.to, r), r));
      }
    }
    kernelObj.set(k.id, add({ key: `kernel:${k.id}`, type: 'kernel', id: k.id, kernel, x: k.x, y: k.y, angle: k.angle, r: 8,
      componentId: k.componentId, thread, generated: k.generated, caller: k.caller,
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

  /* ---- State -------------------------------------------------------------- */
  const view = { k: 1, tx: 0, ty: 0 };
  let fittedK = 1, viewIsFitted = true;
  let hover = null, selected = null, hoverTrack = -1;
  let matches = null; // Set of component ids, or null for "all"
  let emphasis = null; // a track id lit from the panel, or null
  let allWiring = false;
  let palette = {};
  let darkGround = false;
  let hatch = null;
  let labelBoxes = [];
  let hairPx = 0.5;
  let frame = 0;
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
  const size = () => [canvas.clientWidth, canvas.clientHeight];
  function chromeBoxes() {
    if (!stage || !canvas.getBoundingClientRect) return [];
    const base = canvas.getBoundingClientRect();
    return Array.from(stage.querySelectorAll('.explorer__tools, .explorer__legend > *, .explorer__rings')).map((el) => {
      const r = el.getBoundingClientRect();
      return { x0: r.left - base.left, x1: r.right - base.left, y0: r.top - base.top, y1: r.bottom - base.top };
    }).filter((b) => b.x1 > b.x0 && b.y1 > b.y0);
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
  let cameraFrame = 0;
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
  function cameraTo(target, fitted, delay = 0) {
    const [w, h] = size();
    if (cameraFrame) cancelAnimationFrame(cameraFrame);
    cameraFrame = 0;
    const finish = () => { Object.assign(view, { k: target.k, tx: target.tx, ty: target.ty }); viewIsFitted = !!fitted; request(); };
    if (reduceMotion || !w || document.hidden) { finish(); return; }
    const from = { k: view.k, cx: (w / 2 - view.tx) / view.k, cy: (h / 2 - view.ty) / view.k };
    const to = { k: target.k, cx: (w / 2 - target.tx) / target.k, cy: (h / 2 - target.ty) / target.k };
    let duration = Math.min(650, 300 + 120 * Math.abs(Math.log(to.k / from.k) / Math.LN2));
    const flight = flightPath(from, to, Math.max(w, h));
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
      paintNow();
      if (t < 1) cameraFrame = requestAnimationFrame(step);
      else { cameraFrame = 0; finish(); }
    };
    cameraFrame = requestAnimationFrame(step);
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
  function centerOn(o) {
    if (!o) return;
    const pts = [];
    if (o.type === 'core') {
      if (o.centre) { cameraTo(fitTarget(), true); return; }
      for (let a = 0; a < TURN; a += TURN / 8) pts.push(polar(a, R.cores + 70));
      cameraTo(frameOf(pts, 2.4), false, 90);
      return;
    }
    if (o.type === 'component') {
      const s = o.sector;
      for (let a = s.lo; a <= s.hi; a += (s.hi - s.lo) / 6) {
        pts.push(polar(a, R.component - 30), polar(a, R.scale + 34));
      }
      if (o.formal) {
        const k = kernelObj.get(o.comp.kernelId);
        if (k) pts.push([k.x, k.y]);
      }
      cameraTo(frameOf(pts, 3.2), false, 90);
      return;
    }
    if (o.type === 'kernel') {
      // A kernel frames its whole chain: the kernel, the thread, the component
      // it reaches and that component's coverage rings.
      pts.push([o.x, o.y], polar(o.angle, R.kernel - 60));
      const c = o.componentId && compObj.get(o.componentId);
      if (c) pts.push([c.x, c.y], polar(c.angle, R.scale + 20));
      cameraTo(frameOf(pts, 2.6), false, 90);
    }
  }

  /* ---- Focus fade, as on the universe map -------------------------------- */
  let focusMix = 1, focusWas = null, focusHeld = null, focusFade = null, focusFrame = 0;
  function fadeFocus(to, dur, delay) {
    if (reduceMotion) { focusMix = to; focusFade = null; if (to === 0) focusHeld = null; return; }
    focusFade = { from: focusMix, to, dur: Math.max(1, dur), delay, start: null };
    if (!focusFrame) focusFrame = requestAnimationFrame(stepFocus);
  }
  function stepFocus(now) {
    focusFrame = 0;
    const f = focusFade;
    if (!f) return;
    if (f.start === null) f.start = now;
    const t = clamp01((now - f.start - f.delay) / f.dur);
    focusMix = f.from + (f.to - f.from) * (1 - (1 - t) * (1 - t));
    if (t < 1) focusFrame = requestAnimationFrame(stepFocus);
    else { focusFade = null; if (f.to === 0) focusHeld = null; }
    paintNow();
  }
  function trackFocus(focus) {
    if (focus && !focusWas) {
      if (!focusFade) focusMix = 0;
      focusHeld = null;
      fadeFocus(1, FOCUS_IN * (1 - focusMix), 0);
    } else if (!focus && focusWas) {
      focusHeld = focusWas;
      fadeFocus(0, FOCUS_OUT, FOCUS_HOLD);
    }
    if (focus !== focusWas) {
      startGrowth();
      if (focus && focus === selected && focus !== pulsedSelection) { startPulse(focus); pulsedSelection = focus; }
    }
    focusWas = focus;
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
    const pen = (revealMs - REVEAL.tracks - i * REVEAL.trackLag) / REVEAL.trackDur;
    const t = (pen - share(angle)) / 0.05;
    return t <= 0 ? 0 : t >= 1 ? 1 : 1 - (1 - t) ** 2;
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
      paintNow();
      if (reveal < 1) revealFrame = requestAnimationFrame(step);
    };
    revealFrame = requestAnimationFrame(step);
  }

  /* ---- Lit lines grow out from the focus ----------------------------------- */
  let growth = 1, growthFrame = 0;
  function startGrowth() {
    if (reduceMotion) { growth = 1; return; }
    growth = 0;
    let start = null;
    if (growthFrame) cancelAnimationFrame(growthFrame);
    const step = (now) => {
      growthFrame = 0;
      if (start === null) start = now;
      growth = ease(clamp01((now - start) / GROW_MS));
      paintNow();
      if (growth < 1) growthFrame = requestAnimationFrame(step);
    };
    growthFrame = requestAnimationFrame(step);
  }

  /* ---- The evidence pulse ------------------------------------------------- */
  // A chosen component sends beads where its checks run: inward along its
  // thread to its kernel, which answers, and along its replay spoke to the
  // admission core. A chosen kernel sends beads out along its thread to the
  // component that calls it. The admission core sends a bead down every spoke.
  const pulse = { key: null, ms: 1e9, frame: 0, legs: [], blooms: [], end: 0 };
  const spokeOf = (c) => [polar(c.angle, R.component - 10), polar(c.angle, 22)];
  function startPulse(key) {
    if (pulse.frame) cancelAnimationFrame(pulse.frame);
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
    pulse.end = Math.max(PULSE_WAIT + PULSE_RIPPLE, ...legs.map((l) => l.delay + l.dur), ...blooms.map((b) => b.at + PULSE_BLOOM));
    pulse.ms = 0;
    let start = null;
    const step = (now) => {
      if (start === null) start = now;
      pulse.ms = now - start;
      pulse.frame = pulse.ms < pulse.end ? requestAnimationFrame(step) : 0;
      paintNow();
    };
    pulse.frame = requestAnimationFrame(step);
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
  // A verified computation as a flower: one thin petal per verified task in
  // the retained record, its specification as an azure ring round a red
  // point, and a cross outside for each broken variant the verifier rejected.
  function drawFlower(o, x, y, len, alpha, bloomAt) {
    const n = o.tasks;
    const base = o.angle + Math.PI;
    const thin = n > 24 ? 0.085 : n > 14 ? 0.11 : 0.14;
    ctx.lineWidth = Math.max(hairPx, Math.min(1.05, len / 24));
    ctx.strokeStyle = palette.red;
    ctx.fillStyle = palette.red;
    for (let i = 0; i < n; i += 1) {
      const unfold = reveal >= 1 ? 1 : clamp01((revealMs - bloomAt - i * 14) / 260);
      if (unfold <= 0) continue;
      const l = len * (0.5 + 0.5 * unfold);
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(base + (i / n) * TURN);
      ctx.beginPath();
      ctx.ellipse(l * 0.5 + len * 0.06, 0, l * 0.5, Math.max(0.7, l * thin), 0, 0, TURN);
      ctx.globalAlpha = alpha * (darkGround ? 0.1 : 0.07) * unfold;
      ctx.fill();
      ctx.globalAlpha = alpha * (darkGround ? 0.7 : 0.62) * unfold;
      ctx.stroke();
      ctx.restore();
    }
    const ring = Math.max(3, len * 0.3);
    ctx.globalAlpha = alpha;
    ctx.beginPath(); ctx.arc(x, y, ring, 0, TURN);
    ctx.fillStyle = palette.ground; ctx.fill();
    ctx.lineWidth = Math.max(1.1, len * 0.075);
    ctx.strokeStyle = palette.stated; ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y, Math.max(1.5, ring * 0.42), 0, TURN);
    ctx.fillStyle = palette.red; ctx.fill();
    const m = o.mutants;
    if (m) {
      const out = Math.hypot(o.x, o.y) > 1 ? Math.atan2(o.y, o.x) : -Math.PI / 2;
      const arm = Math.max(1.7, len * 0.11);
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = 1;
      ctx.globalAlpha = alpha * 0.8 * (reveal >= 1 ? 1 : clamp01((revealMs - bloomAt - n * 14) / 260));
      for (let i = 0; i < m; i += 1) {
        const ang = out + (i - (m - 1) / 2) * 0.42;
        const mx = x + Math.cos(ang) * (len + arm + 4), my = y + Math.sin(ang) * (len + arm + 4);
        ctx.beginPath();
        ctx.moveTo(mx - arm, my - arm); ctx.lineTo(mx + arm, my + arm);
        ctx.moveTo(mx + arm, my - arm); ctx.lineTo(mx - arm, my + arm);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }
  const petalPx = (o, rs) => R.petal * (o.type === 'core' ? (o.centre ? 1.45 : 1.08) : 1) * view.k * Math.max(1, rs * 0.9);
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
  function drawArcText(text, font, color, alpha, radius, mid, lower, halo = true) {
    ctx.font = font;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = 3;
    ctx.lineJoin = 'round';
    const dir = lower ? -1 : 1;
    const run = arcLetters(text);
    const at = mid - dir * (run.width / radius) / 2;
    for (let pass = halo ? 0 : 1; pass < 2; pass += 1) {
      for (const [ch, offset] of run.letters) {
        const angle = at + dir * offset / radius;
        ctx.save();
        ctx.translate(view.tx + radius * Math.cos(angle), view.ty + radius * Math.sin(angle));
        ctx.rotate(angle + (lower ? -Math.PI / 2 : Math.PI / 2));
        ctx.globalAlpha = alpha;
        if (pass === 0) { ctx.strokeStyle = palette.ground; ctx.strokeText(ch, 0, 0); } else { ctx.fillStyle = color; ctx.fillText(ch, 0, 0); }
        ctx.restore();
      }
    }
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
  function request() {
    if (frame || destroyed) return;
    frame = requestAnimationFrame(() => { frame = 0; paintNow(); });
  }
  function paintNow() {
    if (destroyed) return;
    if (!onScreen || document.hidden) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const [w, h] = size();
    const bw = Math.round(w * dpr), bh = Math.round(h * dpr);
    if (canvas.width !== bw || canvas.height !== bh) { canvas.width = bw; canvas.height = bh; }
    ctx.setTransform(bw / (w || 1), 0, 0, bh / (h || 1), 0, 0);
    hairPx = 1 / dpr;
    ctx.clearRect(0, 0, w, h);
    if ('fontKerning' in ctx) ctx.fontKerning = 'normal';
    labelBoxes = chromeBoxes().map((b) => ({ x0: b.x0 - 4, x1: b.x1 + 4, y0: b.y0 - 4, y1: b.y1 + 4 }));
    stage?.classList.toggle('is-explored', !viewIsFitted);

    const focus = trackFocus(hover || selected);
    const lit = near(focus);
    const rs = rScale();
    const shown = (c) => !matches || matches.has(c.id);
    const fade = (key) => (focus && !lit.has(key) ? dimmed(0.22) : 1);

    drawDepth(w, h);
    drawOrbits();
    drawSpokes(focus, lit, shown);
    drawWiring(focus, shown);
    drawThreads(focus, lit, shown, rs);
    if (darkGround) drawEmbers(focus, lit, rs, shown);
    drawTracks(focus, shown);
    drawTrackKey(focus);
    drawFamilyWords(focus);
    drawKernels(focus, lit, rs, shown, fade);
    drawCores(focus, lit, rs, fade);
    drawComponents(focus, lit, rs, shown, fade);
    drawAnchorWords(focus, lit, rs);
    drawComponentNames(focus, lit, shown);
    drawPulse(rs);
    drawPlatesFor(focus, rs, w, h);
    drawReticles(rs);
    ctx.globalAlpha = 1;
  }

  // A faint light at the centre, so the drawing has depth without a frame.
  function drawDepth() {
    const r = R.component * view.k;
    if (r < 40) return;
    const g = ctx.createRadialGradient(view.tx, view.ty, 0, view.tx, view.ty, r * 1.05);
    const tone = parseColor(palette.ink) || [1, 1, 1, 1];
    const rgb = `${Math.round(tone[0] * 255)},${Math.round(tone[1] * 255)},${Math.round(tone[2] * 255)}`;
    g.addColorStop(0, `rgba(${rgb},${darkGround ? 0.05 : 0.035})`);
    g.addColorStop(0.55, `rgba(${rgb},${darkGround ? 0.022 : 0.015})`);
    g.addColorStop(1, `rgba(${rgb},0)`);
    ctx.globalAlpha = revealAlpha(REVEAL.core);
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(view.tx, view.ty, r * 1.05, 0, TURN); ctx.fill();
    ctx.globalAlpha = 1;
  }

  // The kernels' orbit and the cores' orbit as hairlines, so the inner rings
  // read as structure.
  function drawOrbits() {
    ctx.strokeStyle = palette.edge;
    ctx.lineWidth = hairPx;
    ctx.globalAlpha = 0.9 * revealAlpha(REVEAL.kernels);
    ctx.beginPath(); ctx.arc(view.tx, view.ty, R.kernel * view.k, 0, TURN); ctx.stroke();
    ctx.globalAlpha = 0.6 * revealAlpha(REVEAL.cores);
    ctx.setLineDash([2, 3]);
    ctx.beginPath(); ctx.arc(view.tx, view.ty, R.cores * view.k, 0, TURN); ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;
  }

  // Every component's configured replay route, as a hairline spoke to the
  // admission core at the centre. Azure: configured, not run here.
  function drawSpokes(focus, lit, shown) {
    if (!replayCore) return;
    const reach = spokeReach();
    if (reach <= 0) return;
    const fo = focus ? byKey.get(focus) : null;
    const all = fo === replayCore;
    const emph = emphasis === 'replay';
    ctx.strokeStyle = palette.stated;
    for (const c of compObj.values()) {
      if (!routed.has(c.id)) continue;
      const on = all || (fo && fo.type === 'component' && fo === c);
      let alpha = on ? 0.62 : emph ? 0.32 : darkGround ? 0.085 : 0.11;
      if (fo && !on) alpha *= dimmed(0.5);
      if (!shown(c.comp)) alpha *= 0.3;
      ctx.lineWidth = on ? 1.05 : hairPx;
      ctx.globalAlpha = alpha;
      const [a, b] = spokeOf(c);
      // The spoke grows out from the centre in the opening.
      strokePath([b, a], reach * (on ? growth : 1));
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
  function drawWiring(focus, shown) {
    const fo = focus ? byKey.get(focus) : null;
    const component = fo && fo.type === 'component' ? fo : null;
    if (allWiring) {
      ctx.strokeStyle = palette.stated;
      ctx.lineWidth = hairPx * 1.4;
      for (const [x, y] of model.wires) {
        const a = compObj.get(x), b = compObj.get(y);
        const on = component && (component === a || component === b);
        if (on) continue;
        ctx.globalAlpha = (darkGround ? 0.3 : 0.34) * (component ? dimmed(0.4) : 1) * (shown(a.comp) || shown(b.comp) ? 1 : 0.25);
        strokePath(wirePath(a, b));
      }
    }
    if (!component) return;
    ctx.strokeStyle = palette.stated;
    ctx.lineWidth = 1.1;
    for (const id of wiresOf.get(component.id) || []) {
      const o = compObj.get(id);
      if (!o) continue;
      ctx.globalAlpha = 0.85 * focusMix;
      strokePath(wirePath(component, o), growth);
    }
    ctx.lineWidth = 1.7;
    for (const e of model.imports) {
      if (e.from !== component.id && e.to !== component.id) continue;
      const a = compObj.get(e.from), b = compObj.get(e.to);
      if (!a || !b) continue;
      ctx.globalAlpha = 0.95 * focusMix;
      strokePath(wirePath(a, b), growth);
    }
    ctx.globalAlpha = 1;
  }

  // Each kernel's thread out to its component, through its generated code
  // and its caller: the paper's chain, drawn radially.
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
      ctx.strokeStyle = palette.red;
      ctx.lineWidth = on ? 1.7 : 1.05;
      ctx.globalAlpha = (on ? 0.95 : off ? dimmed(0.5) * 0.6 : 0.62) * matchFade;
      strokePath(k.thread, reach * (on ? growth : 1));
      if (!on && !close) continue;
      // Generated code: a small square; the caller: a diamond.
      const rr = (on ? 3.4 : 2.8) * Math.min(1.3, rs);
      const at = (r0) => reach >= (r0 - R.kernel) / (R.component - R.kernel);
      if (k.generated && at(R.generated)) {
        const x = sx(k.generated[0]), y = sy(k.generated[1]);
        ctx.globalAlpha = (on ? 1 : 0.8) * matchFade;
        ctx.fillStyle = palette.ground;
        ctx.fillRect(x - rr, y - rr, rr * 2, rr * 2);
        ctx.lineWidth = 1.1;
        ctx.strokeRect(x - rr, y - rr, rr * 2, rr * 2);
      }
      if (k.caller && at(R.caller)) {
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
      const len = petalPx(o, rs);
      drawGlow(sx(o.x), sy(o.y), len * 1.5, palette.red, (on ? 0.3 : 0.16) * (focus && !on ? 1 - focusMix : 1) * revealAlpha(o.type === 'core' ? REVEAL.core : REVEAL.kernels));
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
  }

  // The coverage rings: one cell per component per kind of check. Red where a
  // machine checked and the result was kept, azure where it is stated or
  // configured, ember for saved runs, a hatch where nothing is established,
  // and an empty cell where the index lists no such check.
  function cellInk(track, c) {
    if (track.ink === 'unknown') return 'unknown';
    if (!c.comp.checks[track.id]) return 'empty';
    return track.ink;
  }
  function drawTracks(focus, shown) {
    const fo = focus ? byKey.get(focus) : null;
    const column = fo && fo.type === 'component' ? fo : fo && fo.type === 'kernel' ? compObj.get(fo.componentId) : null;
    const k = view.k;
    const close = k >= fittedK * 1.3;
    const halfCell = L.pitch / 2;
    TRACKS.forEach((track, i) => {
      const [r0, r1] = trackBand(i);
      const emph = !emphasis || emphasis === track.id;
      for (const c of compObj.values()) {
        const p = trackPen(c.angle, i);
        if (p <= 0) continue;
        const ink = cellInk(track, c);
        const inColumn = column === c;
        let alpha = p * (shown(c.comp) ? 1 : 0.16) * (emph ? 1 : 0.28);
        if (column && !inColumn) alpha *= dimmed(0.45);
        cellPath(c.angle, halfCell, 0.75, r0, r1);
        if (ink === 'empty') {
          ctx.globalAlpha = alpha * (darkGround ? 0.9 : 1);
          ctx.fillStyle = palette.empty;
          ctx.fill();
        } else if (ink === 'unknown') {
          ctx.globalAlpha = alpha * 0.85;
          ctx.fillStyle = hatch || palette.empty;
          ctx.fill();
        } else {
          ctx.globalAlpha = alpha * 0.95;
          ctx.fillStyle = palette.ring[track.id];
          ctx.fill();
          if (ink === 'saved' && close) {
            // One notch per saved record; an absent one as a hollow notch.
            const recs = c.comp.receipts;
            const n = recs.length;
            const rm = (r0 + r1) / 2;
            const span = 2 * (halfCell - 0.75 / rm);
            recs.forEach((rec, j) => {
              const a = c.angle + ((j + 0.5) / n - 0.5) * span * 0.86;
              const x = view.tx + Math.cos(a) * rm * k, y = view.ty + Math.sin(a) * rm * k;
              const dot = Math.max(0.8, Math.min(2.2, (span * rm * k) / (n * 2.6)));
              ctx.globalAlpha = alpha;
              ctx.beginPath(); ctx.arc(x, y, dot, 0, TURN);
              if (rec.availability === 'available' && rec.status !== 'blocked') { ctx.fillStyle = palette.ground; ctx.fill(); }
              else { ctx.strokeStyle = palette.ground; ctx.lineWidth = 1; ctx.stroke(); }
            });
          }
        }
      }
    });
    if (column) {
      // The chosen component's column, outlined from its mark to the last ring.
      const [, rOut] = trackBand(TRACKS.length - 1);
      ctx.globalAlpha = 0.9;
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = Math.max(1, hairPx * 2.2);
      cellPath(column.angle, halfCell, -0.9, R.track0 - 2.2, rOut + 2.2);
      ctx.stroke();
      if (hoverTrack >= 0 && hover === column.key) {
        const [a0, a1] = trackBand(hoverTrack);
        cellPath(column.angle, halfCell, -0.4, a0 - 1.3, a1 + 1.3);
        ctx.lineWidth = Math.max(1.4, hairPx * 3);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  // The rings' names, in the wedge kept clear at the top: each name in its
  // ring's own ink, so the wedge is also the key.
  function drawTrackKey(focus) {
    const a = revealAlpha(REVEAL.words);
    if (a <= 0.01) return;
    const k = view.k;
    const pitchPx = (R.trackH + R.trackGap) * k;
    const size = Math.min(10.5, pitchPx * 0.8);
    if (size < 8.4) return;
    const fo = focus ? byKey.get(focus) : null;
    TRACKS.forEach((track, i) => {
      const [r0, r1] = trackBand(i);
      const rm = ((r0 + r1) / 2) * k;
      const room = (KEY_GAP * r0 * k) - 10;
      let px = size;
      ctx.font = face(600, px, false, SANS);
      const w = ctx.measureText(track.short).width;
      if (w > room) px = size * room / w;
      if (px < 6.2) return;
      const color = track.ink === 'unknown' ? palette.muted : palette.ring[track.id];
      const on = !emphasis || emphasis === track.id;
      const alpha = a * (on ? 1 : 0.4) * (fo && fo.type === 'component' ? dimmed(0.7) : 1);
      drawArcText(track.short, face(600, px, false, SANS), color, alpha, rm, -Math.PI / 2, false, false);
    });
    // "Checks" just inside the first ring names the rings as one key.
    if (size >= 7.4) {
      drawArcText('CHECKS', face(700, Math.min(9, size * 0.88), false, SANS), palette.muted, a * 0.85, (R.track0 - 9) * k, -Math.PI / 2, false, false);
    }
    ctx.globalAlpha = 1;
  }

  // The family names round the outside, two lines each: the family, then
  // what it holds. A name that would run into a neighbour's steps out a band.
  function drawFamilyWords(focus) {
    const a = revealAlpha(REVEAL.words);
    if (a <= 0.01 || R.scale * view.k < 90 || namesShown()) return;
    const fo = focus ? byKey.get(focus) : null;
    const base = R.scale * view.k + 16;
    const compact = R.scale * view.k < COMPACT_SCALE;
    const band = compact ? TYPE.rowGap + 4 : TYPE.rowGap * 2 + 6;
    const plans = L.sectors.map((s) => {
      const lower = Math.sin(s.mid) > 0.08;
      const formal = s.members.filter((id) => compObj.get(id).formal).length;
      const name = familyName(s.family);
      const tally = `${count(s.count, 'component')}${formal ? `, ${formal} with a proved part` : ''}`;
      ctx.font = face(600, TYPE.title);
      const nameW = ctx.measureText(name).width;
      ctx.font = face(400, TYPE.count, true);
      const tallyW = ctx.measureText(tally).width;
      return { s, lower, name, tally, half: ((compact ? nameW : Math.max(nameW, tallyW)) / 2 + 10) / base, nameHalf: (nameW / 2 + 10) / base, shift: 0 };
    });
    const order = [...plans].sort((p, q) => q.s.count - p.s.count);
    const placed = [];
    const clashes = (p, shift) => placed.some((q) => q.shift === shift && Math.abs(shortArc(q.s.mid, p.s.mid)) < q.half + p.half);
    for (const p of order) {
      // A name that would run into a neighbour first drops its tally line,
      // then steps out a band.
      if (!compact && clashes(p, 0)) { p.nameOnly = true; p.half = p.nameHalf; }
      for (let shift = 0; shift < 3; shift += 1) {
        if (!clashes(p, shift)) { p.shift = shift; break; }
        p.shift = shift + 1;
      }
      placed.push(p);
    }
    for (const p of plans) {
      const on = !fo || (fo.type === 'component' && fo.sector === p.s);
      const alpha = (on ? 0.95 : dimmed(0.55)) * a;
      const r0 = base + p.shift * band;
      const rows = compact || p.nameOnly
        ? [[p.name, face(600, compact ? TYPE.title - 1.5 : TYPE.title), r0 + TYPE.title * 0.5]]
        : p.lower
          ? [[p.name, face(600, TYPE.title), r0 + TYPE.title * 0.55], [p.tally, face(400, TYPE.count, true), r0 + TYPE.title * 0.55 + TYPE.rowGap]]
          : [[p.tally, face(400, TYPE.count, true), r0 + TYPE.count * 0.5], [p.name, face(600, TYPE.title), r0 + TYPE.count * 0.5 + TYPE.rowGap]];
      for (const [text, font, radius] of rows) {
        drawArcText(text, font, font.includes('italic') ? palette.muted : palette.ink, alpha, radius, p.s.mid, p.lower);
      }
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
    for (const c of compObj.values()) {
      const p = penAt(c.angle);
      if (p <= 0) continue;
      let alpha = p * fade(c.key);
      if (matches && !shown(c.comp)) alpha *= 0.13;
      const x = sx(c.x), y = sy(c.y);
      let r = c.r * rs * (1 + 0.35 * (1 - p));
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
  function drawAnchorWords(focus, lit, rs) {
    const a = revealAlpha(REVEAL.words);
    if (a <= 0.01) return;
    const marks = [...coreObj.values(), ...kernelObj.values()];
    const markBox = (o) => {
      const reach = petalPx(o, rs) + 5;
      labelBoxes.push({ x0: sx(o.x) - reach, x1: sx(o.x) + reach, y0: sy(o.y) - reach, y1: sy(o.y) + reach });
    };
    // The centre's own flower is room taken only after the cores round it
    // have named themselves just beyond its petals.
    for (const o of marks) if (o !== replayCore) markBox(o);
    // Each core names itself under its flower, or above it when it stands
    // below the centre; on a small drawing the plate names it instead.
    const roomy = petalPx(replayCore || marks[0] || { type: 'kernel' }, rs) >= 15;
    // The centre names itself first, so the cores round it step around its name.
    const coresInOrder = [...coreObj.values()].sort((a, b) => (b.centre ? 1 : 0) - (a.centre ? 1 : 0));
    for (const o of coresInOrder) {
      const len = petalPx(o, rs);
      const side = 0;
      const name = coreName(o.core);
      const sub = roomy ? coreSub(o.core) : '';
      const nameFont = face(600, o.centre ? TYPE.anchor : TYPE.kernel);
      ctx.font = nameFont;
      let wdt = ctx.measureText(name).width;
      ctx.font = face(400, TYPE.sub, true);
      if (sub) wdt = Math.max(wdt, ctx.measureText(sub).width);
      const lines = sub ? 2 : 1;
      // The centre core names itself above its flower; another core under
      // its own, or above it when that is taken, running away from the centre
      // when it stands to one side.
      let x = sx(o.x), align = 'center';
      if (side) { x += side * (len + 8); align = side > 0 ? 'left' : 'right'; }
      const x0 = align === 'left' ? x : align === 'right' ? x - wdt : x - wdt / 2;
      const places = o.centre ? [sy(o.y) - len - 12 - (lines - 1) * 14] : [sy(o.y) + len + 14, sy(o.y) - len - 12 - (lines - 1) * 14];
      let y = null, box = null;
      for (const at of places) {
        const b = { x0: x0 - 3, x1: x0 + wdt + 3, y0: at - 9, y1: at + 9 + (lines - 1) * 14 };
        if (o.centre || !boxHit(b)) { y = at; box = b; break; }
      }
      if (y === null) continue;
      const alpha = a * (focus && !lit.has(o.key) ? dimmed(0.4) : 1);
      textWithHalo(name, x, y, nameFont, palette.ink, alpha, align);
      if (sub) textWithHalo(sub, x, y + 14, face(400, TYPE.sub, true), palette.muted, alpha, align);
      labelBoxes.push(box);
    }
    if (replayCore) markBox(replayCore);
    // Kernel names stand beside their petals, trying places from the side
    // away from the centre round to the side toward it, and step aside from
    // any name or mark already standing; one with no room waits for a closer
    // view or the pointer.
    const font = face(600, TYPE.kernel);
    ctx.font = font;
    for (const k of kernelObj.values()) {
      const name = proofShortName(k.kernel);
      const wdt = ctx.measureText(name).width;
      const reach = petalPx(k, rs) + 6;
      const x = sx(k.x), y = sy(k.y);
      const out = Math.atan2(k.y, k.x);
      const tries = [];
      for (const extra of [0, 12]) for (const d of [0, 0.6, -0.6, 1.2, -1.2, 1.9, -1.9, Math.PI]) tries.push([out + d, extra]);
      let placed = null;
      for (const [ang, extra] of tries) {
        const cx = Math.cos(ang), cy = Math.sin(ang);
        const lx = x + cx * (reach + extra), ly = y + cy * (reach + extra + 2);
        const align = cx > 0.35 ? 'left' : cx < -0.35 ? 'right' : 'center';
        const x0 = align === 'left' ? lx : align === 'right' ? lx - wdt : lx - wdt / 2;
        const yc = Math.abs(cx) <= 0.35 ? ly + (cy > 0 ? 8 : -8) : ly;
        const box = { x0: x0 - 3, x1: x0 + wdt + 3, y0: yc - 9, y1: yc + 9 };
        if (!boxHit(box) && insideRing(box)) { placed = { lx, ly: yc, align, box }; break; }
      }
      const hot = k.key === hover || k.key === selected;
      if (!placed || hot) continue;
      labelBoxes.push(placed.box);
      const alpha = a * (focus && !lit.has(k.key) ? dimmed(0.35) : 1);
      textWithHalo(name, placed.lx, placed.ly, font, palette.ink, alpha, placed.align);
    }
    ctx.globalAlpha = 1;
  }

  // Zoomed in, each component names itself along its radius, outside its
  // coverage rings, wherever the name has room.
  function namesShown() { return view.k >= fittedK * 1.55; }
  function drawComponentNames(focus, lit, shown) {
    if (!namesShown()) return;
    const font = face(500, TYPE.name);
    ctx.font = font;
    const r0 = (R.scale + 8) * view.k;
    const [w, h] = size();
    for (const c of compObj.values()) {
      if (matches && !shown(c.comp)) continue;
      const cs = Math.cos(c.angle), sn = Math.sin(c.angle);
      const x = view.tx + cs * r0, y = view.ty + sn * r0;
      if (x < -200 || y < -200 || x > w + 200 || y > h + 200) continue;
      const flip = cs < 0;
      const text = c.comp.title.length > 44 ? `${c.comp.title.slice(0, 43)}…` : c.comp.title;
      const alpha = focus && !lit.has(c.key) ? dimmed(0.3) : 0.92;
      ctx.save();
      ctx.translate(x, y);
      ctx.rotate(flip ? c.angle + Math.PI : c.angle);
      ctx.font = font;
      ctx.textBaseline = 'middle';
      ctx.textAlign = flip ? 'right' : 'left';
      ctx.lineWidth = 3;
      ctx.lineJoin = 'round';
      ctx.globalAlpha = alpha;
      ctx.strokeStyle = palette.ground;
      ctx.strokeText(text, 0, 0);
      ctx.fillStyle = c.formal ? palette.red : palette.ink;
      ctx.fillText(text, 0, 0);
      ctx.restore();
    }
    ctx.globalAlpha = 1;
  }

  function drawPulse(rs) {
    if (!pulse.key || pulse.ms >= pulse.end) return;
    const o = byKey.get(pulse.key);
    if (!o) return;
    const phase = (delay, length) => clamp01((pulse.ms - delay) / length);
    const t = phase(PULSE_WAIT, PULSE_RIPPLE);
    const x = sx(o.x), y = sy(o.y), r = (o.type === 'component' ? o.r * rs : petalPx(o, rs) * 0.5) + 1.5;
    const inkOf = (name) => (name === 'stated' ? palette.stated : palette.red);
    if (t > 0 && t < 1) {
      const e = 1 - (1 - t) ** 3;
      ctx.globalAlpha = 0.6 * (1 - e);
      ctx.lineWidth = 1.3;
      ctx.strokeStyle = o.type === 'component' && !o.formal ? palette.ink : palette.red;
      ctx.beginPath(); ctx.arc(x, y, r + 3 + e * Math.max(16, r * 1.6), 0, TURN); ctx.stroke();
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
      const mr = m.type === 'component' ? m.r * rs : petalPx(m, rs) * 0.6;
      ctx.globalAlpha = 0.7 * (1 - e);
      ctx.lineWidth = 1.3;
      ctx.strokeStyle = inkOf(b.ink);
      ctx.beginPath(); ctx.arc(sx(m.x), sy(m.y), mr + 2 + e * Math.max(12, mr * 1.1), 0, TURN); ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  // A plate names what the pointer is on, or what is kept, on a hairline
  // leader; the pinned plate is placed first.
  function cellWords(track, c) {
    const comp = c.comp;
    if (track.id === 'saved') {
      const kept = comp.receipts.filter((r) => r.availability === 'available').length;
      const gone = comp.receipts.length - kept;
      return gone ? `${count(kept, 'past run')}; ${gone} missing from this snapshot` : `${count(kept, 'past run')} saved`;
    }
    if (track.id === 'whole') return 'Unknown, for every component';
    if (track.id === 'replay') return comp.checks.replay ? 'Set up; nothing rerun here' : 'No rerun set up';
    if (!comp.checks[track.id]) return 'Not checked this way';
    if (track.id === 'proof') {
      const k = model.kernelById.get(comp.kernelId);
      return k ? `${proofShortName(k)}: ${count(k.verifiedTasks || 0, 'proof check')} passed` : 'Proof saved';
    }
    if (track.id === 'variants') {
      const k = model.kernelById.get(comp.kernelId);
      return k ? `${count(k.mutants.length, 'broken version')} rejected` : 'Broken versions rejected';
    }
    return `${track.checker}, ${track.when}`;
  }
  function plateLines(o) {
    if (o.type === 'component') {
      const c = o.comp;
      if (o.key === hover && hoverTrack >= 0) {
        const track = TRACKS[hoverTrack];
        return [c.title, `${track.title} · ${track.checker}`, cellWords(track, o)];
      }
      const checked = TRACKS.filter((t) => t.ink === 'ran' && c.checks[t.id]).map((t) => t.short.toLowerCase());
      const lines = [c.title, classWords('evidence_class', c.evidenceClass)];
      lines.push(checked.length ? `Checked by tools: ${checked.join(', ')}` : 'No tool checks beyond its past runs');
      lines.push(cellWords(TRACKS.find((t) => t.id === 'saved'), o));
      return lines;
    }
    if (o.type === 'kernel') {
      const k = o.kernel;
      return [proofShortName(k), `${count(k.verifiedTasks || 0, 'proof check')} passed`,
        `${count(k.mutants.length, 'broken version')} rejected`, k.componentId ? `Used by: ${model.byId.get(k.componentId)?.title}` : 'Not used by a component'];
    }
    if (o.type === 'core') {
      const c = o.core;
      return [coreName(c), `${count(c.verifiedTasks || 0, 'proof check')} passed, ${count(c.mutants.length, 'broken version')} rejected`, coreSub(c)];
    }
    return [];
  }
  function drawPlatesFor(focus, rs, w, h) {
    const keys = [];
    if (selected) keys.push(selected);
    if (hover && hover !== selected) keys.push(hover);
    if (hover && hover === selected && hoverTrack >= 0) keys.splice(0, 1, hover);
    for (const key of keys) {
      const o = byKey.get(key);
      if (!o) continue;
      const lines = plateLines(o);
      if (!lines.length) continue;
      const x = sx(o.x), y = sy(o.y);
      if (x < -40 || y < -40 || x > w + 40 || y > h + 40) continue;
      const fonts = [face(600, TYPE.plate), ...lines.slice(1).map(() => face(400, TYPE.sub, false, SANS))];
      let wd = 0;
      lines.forEach((line, i) => { ctx.font = fonts[i]; wd = Math.max(wd, ctx.measureText(line).width); });
      const pw = wd + 20, ph = 12 + 18 + (lines.length - 1) * 16;
      const out = Math.atan2(o.y, o.x);
      const reach = (o.type === 'component' ? o.r * rs : petalPx(o, rs)) + 22;
      // A kernel's thread leaves it outward and a component's rings stand
      // outside it, so their plates stand to the side or inward first.
      const sideFirst = o.type !== 'core';
      const tries = sideFirst
        ? [out + Math.PI, out + Math.PI / 2, out - Math.PI / 2, out + Math.PI - 0.5, out + Math.PI + 0.5, out]
        : [out + Math.PI / 2, out - Math.PI / 2, out, out + Math.PI];
      let best = null;
      for (const ang of tries) {
        const ax = x + Math.cos(ang) * reach, ay = y + Math.sin(ang) * reach;
        const bx = Math.cos(ang) >= 0 ? ax : ax - pw;
        const by = Math.sin(ang) >= 0 ? ay : ay - ph;
        const cx = Math.max(6, Math.min(w - pw - 6, bx)), cy = Math.max(6, Math.min(h - ph - 6, by));
        const box = { x0: cx, x1: cx + pw, y0: cy, y1: cy + ph };
        if (!boxHit(box)) { best = { box, ang }; break; }
        if (!best) best = { box, ang };
      }
      const { box } = best;
      labelBoxes.push(box);
      // Leader from the mark's edge to the nearest point of the plate.
      const lx = Math.max(box.x0, Math.min(box.x1, x)), ly = Math.max(box.y0, Math.min(box.y1, y));
      const d = Math.hypot(lx - x, ly - y);
      const edge = o.type === 'component' ? o.r * rs : petalPx(o, rs) * 0.4;
      if (d > edge + 4) {
        ctx.globalAlpha = 0.6;
        ctx.strokeStyle = palette.ink;
        ctx.lineWidth = hairPx;
        ctx.beginPath();
        ctx.moveTo(x + (lx - x) / d * (edge + 3), y + (ly - y) / d * (edge + 3));
        ctx.lineTo(lx, ly);
        ctx.stroke();
      }
      ctx.globalAlpha = key === selected ? 0.97 : 0.93;
      ctx.fillStyle = palette.ground;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(box.x0, box.y0, pw, ph, 6); else ctx.rect(box.x0, box.y0, pw, ph);
      ctx.fill();
      ctx.strokeStyle = key === selected ? palette.ink : palette.muted;
      ctx.lineWidth = hairPx * (key === selected ? 2 : 1);
      ctx.stroke();
      ctx.globalAlpha = 1;
      const trackLine = o.type === 'component' && o.key === hover && hoverTrack >= 0 ? TRACKS[hoverTrack] : null;
      lines.forEach((line, i) => {
        ctx.font = fonts[i];
        ctx.textAlign = 'left';
        ctx.textBaseline = 'alphabetic';
        let color = i === 0 ? palette.ink : palette.muted;
        if (trackLine && i === 1) color = trackLine.ink === 'unknown' ? palette.muted : palette.ring[trackLine.id];
        else if (!trackLine && o.type === 'component' && i === 2 && o.formal) color = palette.red;
        else if (o.type !== 'component' && i === 1) color = palette.red;
        ctx.fillStyle = color;
        ctx.fillText(line, box.x0 + 10, box.y0 + 22 + i * 16);
      });
    }
  }

  // Four corner ticks round what the pointer is on and what is kept.
  function drawReticles(rs) {
    for (const key of [selected, hover]) {
      if (!key) continue;
      const o = byKey.get(key);
      if (!o) continue;
      const s = o.type === 'component' ? o.r * rs + 5 : petalPx(o, rs) * 0.55 + 6;
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
    // Within the rings, the pointer is on a component's column.
    if (rr >= R.component - 8 && rr <= R.scale + 2) {
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
      const reach = Math.max(12, petalPx(o, rs) * 0.85);
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
  function select(key, { camera = true, emit = true } = {}) {
    const o = key ? byKey.get(key) : null;
    selected = o ? o.key : null;
    pulsedSelection = null;
    if (o && camera) centerOn(o);
    if (!o && camera && !viewIsFitted) cameraTo(fitTarget(), true);
    if (emit && hooks.onSelect) hooks.onSelect(o);
    request();
  }
  function setHover(o, track = -1) {
    const key = o ? o.key : null;
    if (key === hover && track === hoverTrack) return;
    const changed = key !== hover;
    hover = key;
    hoverTrack = key ? track : -1;
    canvas.style.cursor = key ? 'pointer' : '';
    if (changed && hooks.onHover) hooks.onHover(o);
    request();
  }
  function zoomAt(px, py, factor) {
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
      zoomAt(pinch.cx, pinch.cy, (pinch.k * d / pinch.d) / view.k);
      moved = true;
      return;
    }
    if (drag && (Math.abs(e.offsetX - drag.x) > 4 || Math.abs(e.offsetY - drag.y) > 4 || moved)) {
      moved = true;
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
    e.preventDefault();
    const factor = Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0016));
    zoomAt(e.offsetX, e.offsetY, factor);
  }, { passive: false });
  // Keys: arrows walk the ring, Enter opens, Escape lets go, +/- zoom, 0 fits.
  const ring = L.sectors.flatMap((s) => s.members);
  canvas.addEventListener('keydown', (e) => {
    const cur = selected && byKey.get(selected);
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft' || e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const step = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : -1;
      let at = cur && cur.type === 'component' ? ring.indexOf(cur.id) : -1;
      at = at < 0 ? (step > 0 ? 0 : ring.length - 1) : (at + step + ring.length) % ring.length;
      select(`comp:${ring[at]}`);
    } else if (e.key === 'Enter' && cur && hooks.onOpen) {
      hooks.onOpen(cur);
    } else if (e.key === 'Escape' && selected) {
      // The page's own Escape handler lets go too; this one only stops the
      // key reaching it twice.
      e.preventDefault();
      select(null);
    } else if (e.key === '+' || e.key === '=') {
      zoomAt(canvas.clientWidth / 2, canvas.clientHeight / 2, 1.35);
    } else if (e.key === '-' || e.key === '_') {
      zoomAt(canvas.clientWidth / 2, canvas.clientHeight / 2, 1 / 1.35);
    } else if (e.key === '0') {
      cameraTo(fitTarget(), true);
    }
  });

  /* ---- Lifecycle ------------------------------------------------------------ */
  const onTheme = () => { readPalette(); request(); };
  const schemeQuery = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  schemeQuery?.addEventListener?.('change', onTheme);
  document.addEventListener('plectis:theme', onTheme);
  reduceQuery?.addEventListener?.('change', () => {
    reduceMotion = !!reduceQuery.matches;
    if (reduceMotion) { reveal = 1; pulse.ms = 1e9; growth = 1; focusMix = 1; focusFade = null; request(); }
  });
  const resize = () => {
    const keepCentre = !viewIsFitted ? [(canvas.clientWidth / 2 - view.tx) / view.k, (canvas.clientHeight / 2 - view.ty) / view.k] : null;
    if (viewIsFitted) fit();
    else if (keepCentre) {
      fittedK = fitTarget().k;
      view.tx = canvas.clientWidth / 2 - keepCentre[0] * view.k;
      view.ty = canvas.clientHeight / 2 - keepCentre[1] * view.k;
    }
    paintNow();
  };
  const observer = 'ResizeObserver' in window ? new ResizeObserver(() => resize()) : null;
  observer?.observe(canvas);
  const visibility = () => { if (!document.hidden) request(); };
  document.addEventListener('visibilitychange', visibility);
  document.fonts?.ready?.then(() => { arcCache.clear(); request(); });

  readPalette();
  fit();
  if (hooks.skipReveal) reveal = 1; else startReveal();
  request();

  return {
    select,
    selectedKey: () => selected,
    hoverKey: (key) => { hover = key; hoverTrack = -1; request(); },
    setMatches(set) { matches = set; request(); },
    emphasise(trackId) { emphasis = trackId || null; request(); },
    showWiring(on) { allWiring = !!on; request(); return allWiring; },
    fit: () => cameraTo(fitTarget(), true),
    zoomBy: (f) => zoomAt(canvas.clientWidth / 2, canvas.clientHeight / 2, f),
    resize,
    refreshPalette: onTheme,
    objectFor: (key) => byKey.get(key) || null,
    destroy() {
      destroyed = true;
      observer?.disconnect();
      document.removeEventListener('plectis:theme', onTheme);
      document.removeEventListener('visibilitychange', visibility);
      schemeQuery?.removeEventListener?.('change', onTheme);
      for (const f of [frame, cameraFrame, focusFrame, revealFrame, growthFrame, pulse.frame]) if (f) cancelAnimationFrame(f);
    },
  };
}
