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
// What is new is the picture itself: the chain from a specification to a
// saved run, drawn from the centre outward (see layout.js).

import { glowSprite, isDark, mixOklab, parseColor, rgbText } from './color.js';
import { layout, polar, R, shortArc, threadAngle } from './layout.js';
import { BACKING_WORDS, FAMILY_NAME, count, proofShortName } from '../evidence.js';

const SERIF = '"Plectis Serif", "Plectis Math", "Plectis Serif Fallback", Georgia, serif';
const SANS = '"Plectis Sans", "Plectis Sans Fallback", -apple-system, "Segoe UI", Arial, sans-serif';
const face = (weight, size, italic, family = SERIF) => `${italic ? 'italic ' : ''}${weight} ${size}px ${family}`;
const TYPE = { title: 14, count: 12.5, rowGap: 16, plate: 13.5, sub: 11.5, anchor: 14.5, kernel: 12, name: 11.5 };

const FOCUS_IN = 180, FOCUS_HOLD = 140, FOCUS_OUT = 220;
const PULSE_WAIT = 110, PULSE_RIPPLE = 720, PULSE_TRAVEL = 620, PULSE_STAGGER = 70, PULSE_BLOOM = 560;
const REVEAL = { core: 0, kernels: 160, threads: 360, threadDur: 520, pen: 520, penDur: 900, records: 700, words: 1150, fade: 360, end: 1750 };
const GROW_MS = 260;
const COMPACT_SCALE = 190;
const EMBER_REST = 0.26, EMBER_LIT = 0.42;
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
  add({ key: 'core', type: 'core', x: 0, y: 0, r: 13 });
  for (const s of L.satellites) add({ key: `sat:${s.id}`, type: 'satellite', id: s.id, x: s.x, y: s.y, r: 7.5 });
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
    const o = add({ key: `kernel:${k.id}`, type: 'kernel', id: k.id, kernel, x: k.x, y: k.y, angle: k.angle, r: 8.5,
      componentId: k.componentId, thread, generated: k.generated, caller: k.caller });
    kernelObj.set(k.id, o);
  }
  const sectorOf = new Map();
  for (const s of L.sectors) for (const id of s.members) sectorOf.set(id, s);
  const compObj = new Map();
  for (const p of L.comps) {
    const c = model.byId.get(p.id);
    const o = add({ key: `comp:${c.id}`, type: 'component', id: c.id, comp: c, x: p.x, y: p.y, angle: p.angle,
      r: c.kernelId ? 6 : 5.2, formal: !!c.kernelId, sector: sectorOf.get(c.id) });
    compObj.set(c.id, o);
  }
  const wiresOf = new Map();
  for (const [a, b] of model.wires) {
    if (!wiresOf.has(a)) wiresOf.set(a, []);
    if (!wiresOf.has(b)) wiresOf.set(b, []);
    wiresOf.get(a).push(b);
    wiresOf.get(b).push(a);
  }

  /* ---- State -------------------------------------------------------------- */
  const view = { k: 1, tx: 0, ty: 0 };
  let fittedK = 1, viewIsFitted = true;
  let hover = null, selected = null;
  let matches = null; // Set of component ids, or null for "all"
  let palette = {};
  let darkGround = false;
  let labelBoxes = [];
  let hairPx = 0.5;
  let frame = 0;
  let destroyed = false;
  let onScreen = true;

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
      edgeHot: cssColor(styles, '--m-edge-hot', 'rgba(151,193,223,0.7)'),
      halo: cssColor(styles, '--m-halo', 'rgba(242,230,212,0.12)'),
    };
    darkGround = isDark(palette.ground);
    // Red is drawn at its glow step on the dark ground, where the base step
    // reads muddy at mark size, and at its base step on paper.
    palette.red = darkGround ? palette.provedGlow : palette.proved;
    const ground = parseColor(palette.ground) || [0, 0, 0, 1];
    palette.tone = mixOklab(palette.ink, rgbText(ground), 0.84, ground) || palette.faint;
    palette.record = mixOklab(palette.ink, rgbText(ground), 0.55, ground) || palette.faint;
  }

  /* ---- Camera ------------------------------------------------------------- */
  const size = () => [canvas.clientWidth, canvas.clientHeight];
  function chromeBoxes() {
    if (!stage || !canvas.getBoundingClientRect) return [];
    const base = canvas.getBoundingClientRect();
    return Array.from(stage.querySelectorAll('.explorer__tools, .explorer__legend > *')).map((el) => {
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
    // The family titles stand a fixed number of pixels beyond the scale, so
    // the fit holds the scale's radius plus their reach, not a layout radius.
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
    if (o.type === 'core' || o.type === 'satellite') { cameraTo(fitTarget(), true); return; }
    const pts = [];
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
      // A kernel frames its whole chain: the core, the kernel, the thread and
      // the component it reaches.
      pts.push([0, 0], [o.x, o.y], polar(o.angle, R.kernel + 40));
      const c = o.componentId && compObj.get(o.componentId);
      if (c) pts.push([c.x, c.y], polar(c.angle, R.scale + 20));
      cameraTo(frameOf(pts, 2.4), false, 90);
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
      if (o.formal) { set.add(`kernel:${o.comp.kernelId}`); set.add('core'); set.add('sat:retained'); }
    } else if (o.type === 'kernel') {
      if (o.componentId) set.add(`comp:${o.componentId}`);
      set.add('core'); set.add('sat:retained');
    } else if (o.type === 'core' || o.id === 'retained') {
      for (const k of kernelObj.values()) { set.add(k.key); if (k.componentId) set.add(`comp:${k.componentId}`); }
      set.add('core'); set.add('sat:retained'); set.add('sat:fresh');
    } else if (o.id === 'fresh') {
      set.add('core');
    }
    return set;
  }

  /* ---- Opening: the core, the kernels, the threads, then the ring -------- */
  let reveal = 1, revealMs = 1e9, revealFrame = 0;
  const revealAlpha = (delay) => (reveal >= 1 ? 1 : 1 - 2 ** (-10 * clamp01((revealMs - delay) / REVEAL.fade)));
  const threadReach = () => (reveal >= 1 ? 1 : ease(clamp01((revealMs - REVEAL.threads) / REVEAL.threadDur)));
  function penAt(angle, lag = 0) {
    if (reveal >= 1) return 1;
    const share = (((angle + Math.PI / 2) % TURN) + TURN) % TURN / TURN;
    const pen = (revealMs - REVEAL.pen - lag) / REVEAL.penDur;
    const t = (pen - share) / 0.08;
    return t <= 0 ? 0 : t >= 1 ? 1 : 1 - (1 - t) ** 3;
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

  /* ---- Lit threads grow out from the focus -------------------------------- */
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
  // A chosen component sends a ripple and beads along where its evidence
  // goes: inward along its chain to its kernel and the retained verification,
  // which answers; or, with no modeled contract, outward to its saved records,
  // and nothing at the centre answers.
  const pulse = { key: null, ms: 1e9, frame: 0, legs: [], blooms: [], end: 0 };
  function startPulse(key) {
    if (pulse.frame) cancelAnimationFrame(pulse.frame);
    pulse.frame = 0; pulse.key = key; pulse.ms = 1e9;
    if (!key || reduceMotion || document.hidden) return;
    const o = byKey.get(key);
    const legs = [];
    const blooms = [];
    const toCore = (k) => [[k.x, k.y], [k.x * 0.5, k.y * 0.5], [0, 0]];
    if (o.type === 'component' && o.formal) {
      const k = kernelObj.get(o.comp.kernelId);
      legs.push({ pts: [...k.thread].reverse(), delay: PULSE_WAIT, dur: PULSE_TRAVEL });
      blooms.push({ key: k.key, at: PULSE_WAIT + PULSE_TRAVEL });
      legs.push({ pts: toCore(k), delay: PULSE_WAIT + PULSE_TRAVEL + 60, dur: PULSE_TRAVEL * 0.6 });
      blooms.push({ key: 'sat:retained', at: PULSE_WAIT + PULSE_TRAVEL * 1.6 + 60 });
    } else if (o.type === 'component') {
      const n = Math.max(1, o.comp.receipts.length);
      legs.push({ pts: [polar(o.angle, R.component), polar(o.angle, R.record0 + (n - 1) * R.recordStep)], delay: PULSE_WAIT, dur: PULSE_TRAVEL * 0.7 });
    } else if (o.type === 'kernel') {
      if (o.thread.length) legs.push({ pts: o.thread, delay: PULSE_WAIT, dur: PULSE_TRAVEL });
      legs.push({ pts: toCore(o), delay: PULSE_WAIT + PULSE_STAGGER, dur: PULSE_TRAVEL * 0.6 });
      blooms.push({ key: 'sat:retained', at: PULSE_WAIT + PULSE_STAGGER + PULSE_TRAVEL * 0.6 });
    } else if (o.type === 'core' || o.id === 'retained') {
      let i = 0;
      for (const k of kernelObj.values()) {
        legs.push({ pts: [[0, 0], [k.x * 0.5, k.y * 0.5], [k.x, k.y]], delay: PULSE_WAIT + (i % 4) * PULSE_STAGGER, dur: PULSE_TRAVEL * 0.7 });
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
  function drawArcText(text, font, color, alpha, radius, mid, lower) {
    ctx.font = font;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = 3;
    ctx.lineJoin = 'round';
    const dir = lower ? -1 : 1;
    const run = arcLetters(text);
    const at = mid - dir * (run.width / radius) / 2;
    for (let pass = 0; pass < 2; pass += 1) {
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
    const searching = !!matches;
    const shown = (c) => !matches || matches.has(c.id);
    const fade = (key) => (focus && !lit.has(key) ? dimmed(0.22) : 1);

    drawPlates(focus, lit);
    drawScale(focus, rs, w, h);
    drawSpokes(focus, lit);
    drawThreads(focus, lit, shown);
    drawWiring(focus, rs);
    if (darkGround) drawEmbers(focus, lit, rs, shown);
    drawFamilyWords(focus, lit);
    drawRecords(focus, lit, rs, shown, fade);
    drawKernels(focus, lit, rs, shown, fade);
    drawCore(focus, lit, rs, fade);
    drawComponents(focus, lit, rs, shown, fade, searching);
    drawAnchorWords(focus, lit, rs);
    drawComponentNames(focus, lit, rs, shown);
    drawPulse(rs);
    drawPlatesFor(focus, rs, w, h);
    drawReticles(rs);
    ctx.globalAlpha = 1;
  }

  // The family sectors as faint plates, a lit sector as one wash.
  function drawPlates(focus, lit) {
    const k = view.k;
    const fo = focus ? byKey.get(focus) : null;
    const top = R.record0 + 9 * R.recordStep;
    for (const s of L.sectors) {
      const on = fo && fo.type === 'component' && fo.sector === s;
      const a = revealAlpha(REVEAL.records);
      ctx.globalAlpha = (on ? 0.9 * focusMix + 1 * (1 - focusMix) : 1) * a;
      ctx.fillStyle = on ? palette.halo : palette.plate;
      ctx.beginPath();
      ctx.arc(view.tx, view.ty, (top + 8) * k, s.lo + 0.01, s.hi - 0.01);
      ctx.arc(view.tx, view.ty, (R.component - 16) * k, s.hi - 0.01, s.lo + 0.01, true);
      ctx.closePath();
      ctx.fill();
      ctx.globalAlpha = (on ? 0.5 : 0.85) * a;
      ctx.strokeStyle = on ? palette.muted : palette.edge;
      ctx.lineWidth = hairPx;
      ctx.stroke();
    }
    // The kernels' orbit: one hairline, so the inner ring reads as a structure.
    ctx.globalAlpha = 0.9 * revealAlpha(REVEAL.kernels);
    ctx.strokeStyle = palette.edge;
    ctx.lineWidth = hairPx;
    ctx.beginPath();
    ctx.arc(view.tx, view.ty, R.kernel * k, 0, TURN);
    ctx.stroke();
    ctx.globalAlpha = 1;
  }

  // One tick per component round the ring, every fifth longer, and the
  // boundaries between families as its strongest marks. A cursor bar stands
  // on the selected component's tick.
  function drawScale(focus, rs, w, h) {
    const Rpx = R.scale * view.k;
    if (Rpx < 60) return;
    const a = revealAlpha(REVEAL.words);
    ctx.strokeStyle = palette.ink;
    ctx.lineWidth = hairPx;
    for (const s of L.sectors) {
      s.members.forEach((id, j) => {
        const o = compObj.get(id);
        const len = (j + 1) % 5 === 0 ? 4.5 : 2.6;
        const c = Math.cos(o.angle), sn = Math.sin(o.angle);
        ctx.globalAlpha = (j + 1) % 5 === 0 ? 0.42 * a : 0.26 * a;
        ctx.beginPath();
        ctx.moveTo(view.tx + c * Rpx, view.ty + sn * Rpx);
        ctx.lineTo(view.tx + c * (Rpx + len), view.ty + sn * (Rpx + len));
        ctx.stroke();
      });
    }
    ctx.globalAlpha = 0.7 * a;
    ctx.lineWidth = hairPx * 2;
    for (let i = 0; i < L.sectors.length; i += 1) {
      const cur = L.sectors[i], next = L.sectors[(i + 1) % L.sectors.length];
      const mid = cur.hi + ((((next.lo - cur.hi) % TURN) + TURN) % TURN) / 2;
      const c = Math.cos(mid), sn = Math.sin(mid);
      ctx.beginPath();
      ctx.moveTo(view.tx + c * (Rpx - 2), view.ty + sn * (Rpx - 2));
      ctx.lineTo(view.tx + c * (Rpx + 8), view.ty + sn * (Rpx + 8));
      ctx.stroke();
    }
    const sel = selected && byKey.get(selected);
    if (sel && sel.type === 'component') {
      const c = Math.cos(sel.angle), sn = Math.sin(sel.angle);
      ctx.globalAlpha = 1;
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = hairPx * 2.4;
      ctx.beginPath();
      ctx.moveTo(view.tx + c * (Rpx - 4), view.ty + sn * (Rpx - 4));
      ctx.lineTo(view.tx + c * (Rpx + 9), view.ty + sn * (Rpx + 9));
      ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  // From the core to each kernel: the retained verification each kernel stands on.
  function drawSpokes(focus, lit) {
    const a = revealAlpha(REVEAL.kernels);
    const fo = focus ? byKey.get(focus) : null;
    const allLit = fo && (fo.type === 'core' || fo.id === 'retained');
    for (const k of kernelObj.values()) {
      const on = allLit || (fo && lit.has(k.key) && (fo.type === 'kernel' || fo.type === 'component'));
      ctx.strokeStyle = on ? palette.red : palette.edge;
      ctx.lineWidth = on ? 1.1 : hairPx;
      ctx.globalAlpha = (on ? 0.85 : (focus ? dimmed(0.6) : 0.9)) * a;
      const inner = 14 / view.k, outer = k.r * 1.6 / view.k;
      const d = Math.hypot(k.x, k.y);
      const ux = k.x / d, uy = k.y / d;
      const upto = on ? growth : 1;
      strokePath([[ux * inner, uy * inner], [ux * (inner + (d - outer - inner) * upto), uy * (inner + (d - outer - inner) * upto)]]);
    }
    ctx.globalAlpha = 1;
  }

  // Each kernel's thread out to its component, through its generated code
  // and its caller: the paper's chain, drawn radially.
  function drawThreads(focus, lit, shown) {
    const reach = threadReach();
    if (reach <= 0) return;
    for (const k of kernelObj.values()) {
      if (!k.thread.length) continue;
      const comp = compObj.get(k.componentId);
      const on = focus && lit.has(k.key) && comp && lit.has(comp.key);
      const off = focus && !on;
      const matchFade = comp && !shown(comp.comp) ? 0.25 : 1;
      ctx.strokeStyle = palette.red;
      ctx.lineWidth = on ? 1.6 : 1;
      ctx.globalAlpha = (on ? 0.95 : off ? dimmed(0.5) * 0.55 : 0.55) * matchFade;
      strokePath(k.thread, reach * (on ? growth : 1));
      // Generated code: a small square; the caller: a diamond.
      const at = (pt, r0) => (reach >= (r0 - R.kernel) / (R.component - R.kernel));
      const rr = on ? 3.6 : 3;
      if (k.generated && at(k.generated, R.generated)) {
        const x = sx(k.generated[0]), y = sy(k.generated[1]);
        ctx.globalAlpha = (on ? 1 : off ? dimmed(0.4) : 0.85) * matchFade;
        ctx.fillStyle = palette.ground;
        ctx.fillRect(x - rr, y - rr, rr * 2, rr * 2);
        ctx.lineWidth = 1.1;
        ctx.strokeRect(x - rr, y - rr, rr * 2, rr * 2);
      }
      if (k.caller && at(k.caller, R.caller)) {
        const x = sx(k.caller[0]), y = sy(k.caller[1]);
        ctx.globalAlpha = (on ? 1 : off ? dimmed(0.4) : 0.85) * matchFade;
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

  // Declared wiring of the component in focus: azure, because it is stated
  // in source, not observed in a run, and untyped (component_index.py).
  function drawWiring(focus) {
    const fo = focus ? byKey.get(focus) : null;
    if (!fo || fo.type !== 'component') return;
    const others = wiresOf.get(fo.id) || [];
    if (!others.length) return;
    ctx.strokeStyle = palette.stated;
    ctx.lineWidth = 1.05;
    for (const id of others) {
      const o = compObj.get(id);
      if (!o) continue;
      const d = Math.abs(shortArc(fo.angle, o.angle));
      const mid = fo.angle + shortArc(fo.angle, o.angle) / 2;
      const cr = R.component * (0.96 - 0.5 * (d / Math.PI));
      const c = polar(mid, cr);
      const pts = [];
      for (let i = 0; i <= 20; i += 1) {
        const t = i / 20, u = 1 - t;
        pts.push([u * u * fo.x * 0.985 + 2 * u * t * c[0] + t * t * o.x * 0.985, u * u * fo.y * 0.985 + 2 * u * t * c[1] + t * t * o.y * 0.985]);
      }
      ctx.globalAlpha = 0.78 * focusMix;
      strokePath(pts, growth);
    }
    ctx.globalAlpha = 1;
  }

  // Light belongs to machine-checked evidence: on the dark ground the twelve
  // components with a retained proof and their kernels glow faintly, an
  // ember each, and nothing else does.
  function drawEmbers(focus, lit, rs, shown) {
    ctx.globalCompositeOperation = 'lighter';
    for (const c of compObj.values()) {
      if (!c.formal || !shown(c.comp)) continue;
      const on = focus && lit.has(c.key);
      const a = (on ? EMBER_LIT : EMBER_REST) * (focus && !on ? 1 - focusMix : 1) * penAt(c.angle);
      drawGlow(sx(c.x), sy(c.y), c.r * rs * 2.9, palette.red, a);
    }
    for (const k of kernelObj.values()) {
      const on = focus && lit.has(k.key);
      drawGlow(sx(k.x), sy(k.y), k.r * rs * 2.4, palette.red, (on ? 0.34 : 0.2) * (focus && !on ? 1 - focusMix : 1) * revealAlpha(REVEAL.kernels));
    }
    const sat = byKey.get('sat:retained');
    drawGlow(sx(sat.x), sy(sat.y), sat.r * rs * 3, palette.red, 0.3 * revealAlpha(REVEAL.core));
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
  }

  // The family names round the outside, two lines each: the family, then
  // what it holds. A name that would run into a neighbour's steps out a band.
  function drawFamilyWords(focus) {
    const a = revealAlpha(REVEAL.words);
    // Close enough for the components to name themselves, the panel names
    // the family instead, so the two never run across each other.
    if (a <= 0.01 || R.scale * view.k < 90 || namesShown()) return;
    const fo = focus ? byKey.get(focus) : null;
    const base = R.scale * view.k + 16;
    const compact = R.scale * view.k < COMPACT_SCALE;
    const band = compact ? TYPE.rowGap + 4 : TYPE.rowGap * 2 + 6;
    const plans = L.sectors.map((s) => {
      const lower = Math.sin(s.mid) > 0.08;
      const formal = s.members.filter((id) => compObj.get(id).formal).length;
      const name = FAMILY_NAME[s.family] || s.family;
      const tally = `${count(s.count, 'component')}${formal ? `, ${formal} with a verified kernel` : ''}`;
      ctx.font = face(600, TYPE.title);
      const nameW = ctx.measureText(name).width;
      ctx.font = face(400, TYPE.count, true);
      const tallyW = ctx.measureText(tally).width;
      return { s, lower, name, tally, half: ((compact ? nameW : Math.max(nameW, tallyW)) / 2 + 10) / base, shift: 0 };
    });
    const order = [...plans].sort((p, q) => q.s.count - p.s.count);
    const placed = [];
    for (const p of order) {
      for (let shift = 0; shift < 3; shift += 1) {
        const clash = placed.some((q) => q.shift === shift && Math.abs(shortArc(q.s.mid, p.s.mid)) < q.half + p.half);
        if (!clash) { p.shift = shift; break; }
        p.shift = shift + 1;
      }
      placed.push(p);
    }
    for (const p of plans) {
      const on = !fo || (fo.type === 'component' && fo.sector === p.s);
      const alpha = (on ? 0.95 : dimmed(0.55)) * a;
      const r0 = base + p.shift * band;
      const rows = compact
        ? [[p.name, face(600, TYPE.title - 1.5), r0 + TYPE.title * 0.5]]
        : p.lower
          ? [[p.name, face(600, TYPE.title), r0 + TYPE.title * 0.55], [p.tally, face(400, TYPE.count, true), r0 + TYPE.title * 0.55 + TYPE.rowGap]]
          : [[p.tally, face(400, TYPE.count, true), r0 + TYPE.count * 0.5], [p.name, face(600, TYPE.title), r0 + TYPE.count * 0.5 + TYPE.rowGap]];
      for (const [text, font, radius] of rows) {
        drawArcText(text, font, font.includes('italic') ? palette.muted : palette.ink, alpha, radius, p.s.mid, p.lower);
      }
    }
    ctx.globalAlpha = 1;
  }

  // Saved records stacked outward from each component: a filled dot for one
  // listed as available, a broken ring for one this snapshot does not include.
  function drawRecords(focus, lit, rs, shown, fade) {
    const k = view.k;
    const dot = Math.max(1.1, 1.55 * rs);
    for (const c of compObj.values()) {
      const p = penAt(c.angle, REVEAL.records - REVEAL.pen);
      if (p <= 0) continue;
      const alphaBase = (shown(c.comp) ? 1 : 0.14) * fade(c.key) * p;
      const cs = Math.cos(c.angle), sn = Math.sin(c.angle);
      c.comp.receipts.forEach((rec, i) => {
        const r = (R.record0 + i * R.recordStep) * k;
        const x = view.tx + cs * r, y = view.ty + sn * r;
        ctx.globalAlpha = alphaBase * (i === 0 ? 0.95 : 0.8);
        if (rec.availability === 'available') {
          ctx.fillStyle = i === 0 ? palette.ink : palette.record;
          ctx.beginPath();
          ctx.arc(x, y, i === 0 ? dot * 1.25 : dot, 0, TURN);
          ctx.fill();
        } else {
          ctx.strokeStyle = palette.muted;
          ctx.lineWidth = 1;
          ctx.setLineDash([1.2, 1.4]);
          ctx.beginPath();
          ctx.arc(x, y, dot * 1.35, 0, TURN);
          ctx.stroke();
          ctx.setLineDash([]);
        }
      });
    }
    ctx.globalAlpha = 1;
  }

  // A kernel: its specification is a ring in the stated ink round a point in
  // the machine ink, and one petal per retained verified task round it; the
  // deliberately broken variants the verifier rejected stand outside as
  // small crosses.
  function drawKernels(focus, lit, rs, shown, fade) {
    const a = revealAlpha(REVEAL.kernels);
    for (const k of kernelObj.values()) {
      const comp = k.componentId ? compObj.get(k.componentId) : null;
      const alpha = a * fade(k.key) * (comp && !shown(comp.comp) ? 0.3 : 1);
      const x = sx(k.x), y = sy(k.y);
      const r = k.r * rs;
      const tasks = k.kernel?.verifiedTasks || 0;
      const pr = (R.petal * view.k) * Math.max(1, rs * 0.9);
      ctx.fillStyle = palette.red;
      for (let i = 0; i < tasks; i += 1) {
        const ang = k.angle + Math.PI + (i / tasks) * TURN;
        const unfold = reveal >= 1 ? 1 : clamp01((revealMs - REVEAL.kernels - i * 18) / 260);
        if (unfold <= 0) continue;
        ctx.globalAlpha = alpha * 0.9 * unfold;
        ctx.beginPath();
        ctx.arc(x + Math.cos(ang) * pr * (0.6 + 0.4 * unfold), y + Math.sin(ang) * pr * (0.6 + 0.4 * unfold), Math.max(0.9, 1.25 * rs), 0, TURN);
        ctx.fill();
      }
      const mutants = k.kernel?.mutants || [];
      ctx.strokeStyle = palette.ink;
      ctx.lineWidth = 1;
      mutants.forEach((_, i) => {
        const ang = k.angle + (i - (mutants.length - 1) / 2) * 0.42;
        const mx = x + Math.cos(ang) * (pr + 9 * rs), my = y + Math.sin(ang) * (pr + 9 * rs);
        const m = 2.4 * rs;
        ctx.globalAlpha = alpha * 0.75;
        ctx.beginPath();
        ctx.moveTo(mx - m, my - m); ctx.lineTo(mx + m, my + m);
        ctx.moveTo(mx + m, my - m); ctx.lineTo(mx - m, my + m);
        ctx.stroke();
      });
      ctx.globalAlpha = alpha;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, TURN);
      ctx.fillStyle = palette.ground;
      ctx.fill();
      ctx.lineWidth = 1.6;
      ctx.strokeStyle = palette.stated;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(x, y, Math.max(1.6, r * 0.36), 0, TURN);
      ctx.fillStyle = palette.red;
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // The core, a ring round a point in ink, and its two satellites: the
  // retained verification, filled, and a fresh prover run, a hollow ring,
  // because this view records none.
  function drawCore(focus, lit, rs, fade) {
    const a = revealAlpha(REVEAL.core);
    const core = byKey.get('core');
    const x = sx(0), y = sy(0), r = core.r * rs;
    ctx.globalAlpha = a * fade('core');
    ctx.beginPath(); ctx.arc(x, y, r, 0, TURN);
    ctx.fillStyle = palette.ground; ctx.fill();
    ctx.lineWidth = 1.8; ctx.strokeStyle = palette.ink; ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y, r * 0.3, 0, TURN); ctx.fillStyle = palette.ink; ctx.fill();
    ctx.globalAlpha = a * fade('core') * 0.35;
    ctx.lineWidth = hairPx;
    ctx.beginPath(); ctx.arc(x, y, r + 5, 0, TURN); ctx.stroke();
    const ret = byKey.get('sat:retained'), fresh = byKey.get('sat:fresh');
    ctx.globalAlpha = a * fade(ret.key);
    ctx.beginPath(); ctx.arc(sx(ret.x), sy(ret.y), ret.r * rs, 0, TURN);
    ctx.fillStyle = palette.red; ctx.fill();
    ctx.globalAlpha = a * fade(fresh.key);
    ctx.beginPath(); ctx.arc(sx(fresh.x), sy(fresh.y), fresh.r * rs, 0, TURN);
    ctx.lineWidth = 1.6; ctx.strokeStyle = palette.red; ctx.stroke();
    ctx.globalAlpha = 1;
  }

  function drawComponents(focus, lit, rs, shown, fade, searching) {
    for (const c of compObj.values()) {
      const p = penAt(c.angle);
      if (p <= 0) continue;
      let alpha = p * fade(c.key);
      if (searching && !shown(c.comp)) alpha *= 0.13;
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

  // Where each satellite's name goes in this frame, or nothing for no room.
  let satNames = {};
  function satellitePlacement(rows) {
    const rs = rScale();
    const width = (name, sub, sizePx) => {
      ctx.font = face(600, sizePx); const a = ctx.measureText(name).width;
      ctx.font = face(400, TYPE.sub, true); return Math.max(a, ctx.measureText(sub).width) + 4;
    };
    const [[left, ln, lsub, lsize], [right, rn, rsub, rsize]] = rows;
    const lw = width(ln, lsub, lsize), rw = width(rn, rsub, rsize);
    const lx = sx(left.x), rx = sx(right.x), sep = rx - lx;
    if (sep >= (lw + rw) / 2 + 12) return { retained: { x: lx, align: 'center' }, fresh: { x: rx, align: 'center' } };
    const inner = (R.kernel - R.petal - 8) * view.k;
    const reach = Math.max(Math.abs(lx - view.tx) + lw, Math.abs(rx - view.tx) + rw);
    if (reach < inner && rs > 0) return { retained: { x: lx + 6, align: 'right' }, fresh: { x: rx - 6, align: 'left' } };
    return {};
  }

  // Names that stand at rest: the core, the satellites and the kernels.
  // Every mark near the centre is room taken first, so no name covers one.
  function drawAnchorWords(focus, lit, rs) {
    const a = revealAlpha(REVEAL.words);
    if (a <= 0.01) return;
    const t = model.totals;
    const marks = [byKey.get('core'), byKey.get('sat:retained'), byKey.get('sat:fresh'), ...kernelObj.values()];
    for (const o of marks) {
      const reach = o.type === 'kernel' ? R.petal * view.k * Math.max(1, rs * 0.9) + 5 : o.r * rs + 4;
      labelBoxes.push({ x0: sx(o.x) - reach, x1: sx(o.x) + reach, y0: sy(o.y) - reach, y1: sy(o.y) + reach });
    }
    // The core names itself above its mark; each satellite under its own.
    const words = [
      [byKey.get('core'), 'Formal contracts', `${count(t.kernels, 'specification')} in Dafny`, TYPE.anchor, true],
      [byKey.get('sat:retained'), 'Retained proofs', `${t.tasks} tasks verified`, TYPE.anchor - 1.5, false],
      [byKey.get('sat:fresh'), 'Fresh prover run', 'not recorded here', TYPE.anchor - 1.5, false],
    ];
    // The satellites' names stand centred under them where there is room,
    // turn outward where there is less, and give way on a small drawing, where
    // each mark names itself on a plate instead.
    satNames = satellitePlacement(words.slice(1));
    for (const [o, name, sub, sizePx, above] of words) {
      let x = sx(o.x), align = 'center';
      if (o.type === 'satellite') {
        const place = satNames[o.id];
        if (!place) continue;
        ({ x, align } = place);
      }
      const y = above ? sy(o.y) - o.r * rs - 30 : sy(o.y) + o.r * rs + 13;
      const alpha = a * (focus && !lit.has(o.key) ? dimmed(0.4) : 1);
      textWithHalo(name, x, y, face(600, sizePx), palette.ink, alpha, align);
      textWithHalo(sub, x, y + 15, face(400, TYPE.sub, true), palette.muted, alpha, align);
      ctx.font = face(600, sizePx);
      const wdt = Math.max(ctx.measureText(name).width, ctx.measureText(sub).width) + 4;
      const x0 = align === 'center' ? x - wdt / 2 : align === 'right' ? x - wdt : x;
      labelBoxes.push({ x0, x1: x0 + wdt, y0: y - 9, y1: y + 23 });
    }
    // Kernel names stand beside their petals, trying eight places from the
    // side away from the centre round to the side toward it, and step aside
    // from any name or mark already standing; one with no room waits for a
    // closer view or the pointer.
    const font = face(600, TYPE.kernel);
    ctx.font = font;
    const kernels = [...kernelObj.values()];
    for (const k of kernels) {
      const name = proofShortName(k.kernel);
      const wdt = ctx.measureText(name).width;
      const reach = R.petal * view.k * Math.max(1, rs * 0.9) + 6;
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
  // saved records, wherever the name has room.
  function namesShown() { return view.k >= fittedK * 1.55; }
  function drawComponentNames(focus, lit, rs, shown) {
    if (!namesShown()) return;
    const font = face(500, TYPE.name);
    ctx.font = font;
    const r0 = (R.record0 + 9 * R.recordStep + 10) * view.k;
    for (const c of compObj.values()) {
      if (matches && !shown(c.comp)) continue;
      const cs = Math.cos(c.angle), sn = Math.sin(c.angle);
      const x = view.tx + cs * r0, y = view.ty + sn * r0;
      const [w, h] = size();
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
    const x = sx(o.x), y = sy(o.y), r = (o.r || 6) * rs + 1.5;
    const color = o.type === 'component' && !o.formal ? palette.ink : palette.red;
    if (t > 0 && t < 1) {
      const e = 1 - (1 - t) ** 3;
      ctx.globalAlpha = 0.6 * (1 - e);
      ctx.lineWidth = 1.3;
      ctx.strokeStyle = color;
      ctx.beginPath(); ctx.arc(x, y, r + 3 + e * Math.max(16, r * 1.6), 0, TURN); ctx.stroke();
    }
    const size = Math.max(0.8, rs);
    for (const leg of pulse.legs) {
      const p = phase(leg.delay, leg.dur);
      if (p <= 0 || p >= 1) continue;
      const fade = Math.min(1, p * 6, (1 - p) * 6);
      ctx.fillStyle = color;
      for (let d = 3; d >= 1; d -= 1) {
        const tail = alongPath(leg.pts, ease(Math.max(0, p - d * 0.035)));
        ctx.globalAlpha = fade * (0.56 - d * 0.14);
        ctx.beginPath(); ctx.arc(sx(tail[0]), sy(tail[1]), Math.max(0.7, (2.2 - d * 0.4) * size), 0, TURN); ctx.fill();
      }
      const bead = alongPath(leg.pts, ease(p));
      ctx.globalAlpha = fade;
      ctx.fillStyle = darkGround ? palette.ink : color;
      ctx.beginPath(); ctx.arc(sx(bead[0]), sy(bead[1]), 2.2 * size, 0, TURN); ctx.fill();
    }
    for (const b of pulse.blooms) {
      const m = byKey.get(b.key);
      const p = phase(b.at, PULSE_BLOOM);
      if (!m || p <= 0 || p >= 1) continue;
      const e = 1 - (1 - p) ** 3, mr = (m.r || 6) * rs;
      ctx.globalAlpha = 0.7 * (1 - e);
      ctx.lineWidth = 1.3;
      ctx.strokeStyle = palette.red;
      ctx.beginPath(); ctx.arc(sx(m.x), sy(m.y), mr + 2 + e * Math.max(12, mr * 1.1), 0, TURN); ctx.stroke();
    }
    ctx.globalAlpha = 1;
  }

  // A plate names what the pointer is on, or what is kept, on a hairline
  // leader; the pinned plate is placed first.
  function plateLines(o) {
    if (o.type === 'component') {
      const c = o.comp;
      const lines = [c.title, BACKING_WORDS[c.backing] || 'How it is backed is not recognised'];
      const kept = c.receipts.filter((r) => r.availability === 'available').length;
      const gone = c.receipts.length - kept;
      lines.push(gone ? `${count(kept, 'saved record')} listed; ${gone} not in this snapshot` : `${count(kept, 'saved record')} listed`);
      if (o.formal) lines.push(`Modeled contract: ${proofShortName(model.kernelById.get(c.kernelId))}`);
      return lines;
    }
    if (o.type === 'kernel') {
      const k = o.kernel;
      return [proofShortName(k), `${count(k.verifiedTasks || 0, 'task')} verified in the retained record`,
        `${count(k.mutants.length, 'broken variant')} rejected`, k.componentId ? `In: ${model.byId.get(k.componentId)?.title}` : 'No component linked'];
    }
    if (o.type === 'core') return ['Formal contracts', 'Select to light every kernel and its thread'];
    if (o.id === 'retained') return ['Retained proofs', `Dafny ${(model.kernels[0]?.dafnyVersion || '').split('+')[0]}`, 'Recorded results, not a run in this view'];
    return ['Fresh prover run', 'This view runs nothing and records none'];
  }
  function drawPlatesFor(focus, rs, w, h) {
    const keys = [];
    if (selected) keys.push(selected);
    if (hover && hover !== selected) keys.push(hover);
    for (const key of keys) {
      const o = byKey.get(key);
      if (!o || o.type === 'core' || (o.type === 'satellite' && satNames[o.id])) continue;
      const lines = plateLines(o);
      const x = sx(o.x), y = sy(o.y);
      if (x < -40 || y < -40 || x > w + 40 || y > h + 40) continue;
      const fonts = [face(600, TYPE.plate), ...lines.slice(1).map(() => face(400, TYPE.sub, false, SANS))];
      let wd = 0;
      lines.forEach((line, i) => { ctx.font = fonts[i]; wd = Math.max(wd, ctx.measureText(line).width); });
      const pw = wd + 20, ph = 12 + 18 + (lines.length - 1) * 16;
      const out = Math.atan2(o.y, o.x);
      const reach = (o.r * rs) + 22;
      // A kernel's thread leaves it outward, and a zoomed component's name
      // runs outward, so their plates stand to the side first.
      const sideFirst = o.type === 'kernel' || namesShown();
      const tries = sideFirst
        ? [out + Math.PI / 2, out - Math.PI / 2, out + Math.PI, out + 0.5, out - 0.5, out]
        : [out, out + 0.5, out - 0.5, out + Math.PI / 2, out - Math.PI / 2, out + Math.PI];
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
      if (d > o.r * rs + 4) {
        ctx.globalAlpha = 0.6;
        ctx.strokeStyle = palette.ink;
        ctx.lineWidth = hairPx;
        ctx.beginPath();
        ctx.moveTo(x + (lx - x) / d * (o.r * rs + 3), y + (ly - y) / d * (o.r * rs + 3));
        ctx.lineTo(lx, ly);
        ctx.stroke();
      }
      ctx.globalAlpha = key === selected ? 0.97 : 0.92;
      ctx.fillStyle = palette.ground;
      ctx.beginPath();
      if (ctx.roundRect) ctx.roundRect(box.x0, box.y0, pw, ph, 6); else ctx.rect(box.x0, box.y0, pw, ph);
      ctx.fill();
      ctx.strokeStyle = key === selected ? palette.ink : palette.muted;
      ctx.lineWidth = hairPx * (key === selected ? 2 : 1);
      ctx.stroke();
      ctx.globalAlpha = 1;
      lines.forEach((line, i) => {
        ctx.font = fonts[i];
        ctx.textAlign = 'left';
        ctx.textBaseline = 'alphabetic';
        ctx.fillStyle = i === 0 ? palette.ink : (o.formal || o.type === 'kernel') && i === lines.length - 1 && i > 1 ? palette.red : palette.muted;
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
      const s = (o.r || 6) * rs + (o.type === 'kernel' ? 8 : 5);
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
  function hit(px, py) {
    const rs = rScale();
    let best = null, bestD = Infinity;
    for (const o of objects) {
      let x = sx(o.x), y = sy(o.y);
      let reach = Math.max(12, (o.r || 6) * rs + 6);
      if (o.type === 'component') {
        // A component's saved records answer for it too.
        const cs = Math.cos(o.angle), sn = Math.sin(o.angle);
        const r1 = R.component * view.k, r2 = (R.record0 + Math.max(0, o.comp.receipts.length - 1) * R.recordStep) * view.k;
        const along = (px - view.tx) * cs + (py - view.ty) * sn;
        const t = Math.max(r1, Math.min(r2, along));
        x = view.tx + cs * t; y = view.ty + sn * t;
        reach = Math.max(10, Math.min(reach, (L.pitch * R.component * view.k) / 2 + 1));
      }
      if (o.type === 'kernel') reach = Math.max(reach, R.petal * view.k * 0.8);
      const d = Math.hypot(px - x, py - y);
      if (d <= reach && d < bestD) { best = o; bestD = d; }
    }
    if (!best) {
      // The chain's markers belong to their kernel.
      for (const k of kernelObj.values()) {
        for (const pt of [k.generated, k.caller]) {
          if (pt && Math.hypot(px - sx(pt[0]), py - sy(pt[1])) < 10) return k;
        }
      }
    }
    return best;
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
  function setHover(o) {
    const key = o ? o.key : null;
    if (key === hover) return;
    hover = key;
    canvas.style.cursor = key ? 'pointer' : '';
    if (hooks.onHover) hooks.onHover(o);
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
    if (!pointers.size) setHover(hit(e.offsetX, e.offsetY));
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
    const o = hit(e.offsetX, e.offsetY);
    if (o) select(o.key);
    else if (selected) select(null);
  });
  canvas.addEventListener('pointercancel', release);
  canvas.addEventListener('pointerleave', () => { if (!pointers.size) setHover(null); });
  canvas.addEventListener('dblclick', (e) => {
    const o = hit(e.offsetX, e.offsetY);
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
    hoverKey: (key) => { hover = key; request(); },
    setMatches(set) { matches = set; request(); },
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
