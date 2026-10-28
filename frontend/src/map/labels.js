// The map's inscriptions: one screen-space label planner.
//
// Every label outside the component ring is placed here, in pixels, against
// hard obstacles (chrome, the stage chips, rule glyphs with their obligation
// arcs, flower footprints, active routes, the ring and the bezel) and against
// every label already placed. Candidates are taken by priority, then by id,
// so a settled view always places the same labels in the same places. A
// candidate whose anchors all collide is omitted and the reason recorded:
// there is no collision-blind fallback.
//
// Text footprints are approximated by primitives: a horizontal label is one
// rectangle; radial and curved (arc) text is a row of discs sampled along
// its baseline, each as wide as the text is tall.
//
// The module is pure and deterministic. It has no DOM or canvas dependency;
// measuring text is the caller's job (see `fitText` and a candidate's `fit`).

/** Label priorities (art direction §6): lower is placed first. */
export const PRIORITY = Object.freeze({
  chosen: 1,
  preview: 2,
  traced: 3,
  search: 4,
  family: 5,
  core: 6,
  litRuleId: 7,
  ruleId: 8,
  componentName: 9,
  litAxiomTitle: 10,
  title: 11,
  wedge: 12,
});

/** Levels of detail by local projected pitch (px between neighbouring component columns). */
export const LOD = Object.freeze({ atlas: 0, neighbourhood: 1, reading: 2 });
const LOD_EDGES = [18, 34];
const HYSTERESIS = 0.1; // the band is 10% wide, centred on each edge

/** The local projected pitch p = 360·k·pitch (pitch ≈ 0.0600 rad). */
export function localPitch(k, pitch = 0.06) { return 360 * k * pitch; }

/**
 * The level of detail for pitch p. With a previous level, an edge must be
 * crossed by 5% either side before the level changes (a 10% band), so a view
 * resting near an edge does not flicker between levels.
 */
export function levelOfDetail(p, previous = null) {
  const raw = p >= LOD_EDGES[1] ? LOD.reading : p >= LOD_EDGES[0] ? LOD.neighbourhood : LOD.atlas;
  if (previous === null || previous === undefined || previous === raw) return raw;
  const h = HYSTERESIS / 2;
  if (raw > previous) {
    // Going up: the next edge must be passed by 5%.
    let level = previous;
    while (level < LOD.reading && p >= LOD_EDGES[level] * (1 + h)) level += 1;
    return level;
  }
  let level = previous;
  while (level > LOD.atlas && p < LOD_EDGES[level - 1] * (1 - h)) level -= 1;
  return level;
}

/* ---- Footprints ------------------------------------------------------------ */

/** Discs along a ray: text of height h from `from` px out to `from + length` px. */
export function radialDiscs(cx, cy, angle, from, length, h) {
  const r = h / 2, step = Math.max(1, r);
  const cs = Math.cos(angle), sn = Math.sin(angle);
  const out = [];
  for (let d = r; d - r < length; d += step) {
    const at = from + Math.min(d, Math.max(r, length - r));
    out.push({ t: 'c', x: cx + cs * at, y: cy + sn * at, r });
    if (d >= length - r) break;
  }
  return out;
}

/** Discs along a circle about (cx, cy): text `width` px long centred on angle `mid`. */
export function arcDiscs(cx, cy, radius, mid, width, h) {
  const r = h / 2, step = Math.max(1, r);
  const span = width / Math.max(1, radius);
  const n = Math.max(1, Math.ceil(Math.max(0, width - h) / step));
  const out = [];
  for (let i = 0; i <= n; i += 1) {
    const off = width <= h ? 0 : -width / 2 + r + (width - h) * (i / n);
    const a = mid + off / Math.max(1, radius);
    out.push({ t: 'c', x: cx + Math.cos(a) * radius, y: cy + Math.sin(a) * radius, r });
  }
  out.span = span;
  return out;
}

export const rectShape = (x0, y0, x1, y1) => ({ t: 'r', x0: Math.min(x0, x1), y0: Math.min(y0, y1), x1: Math.max(x0, x1), y1: Math.max(y0, y1) });

/**
 * The longest prefix of `text` (with an ellipsis when cut) that fits in
 * `maxWidth`. `measure(s)` returns a width; `prefix(i)`, when given, returns
 * the width of text.slice(0, i) (a cache). Returns null when fewer than
 * `minChars` characters would stand.
 */
export function fitText(text, maxWidth, measure, { ellipsis = '…', minChars = 4, prefix = null } = {}) {
  const full = prefix ? prefix(text.length) : measure(text);
  if (full <= maxWidth) return { text, width: full, cut: false };
  const ew = measure(ellipsis);
  let lo = 0, hi = text.length;
  const widthAt = (i) => (prefix ? prefix(i) : measure(text.slice(0, i)));
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (widthAt(mid) + ew <= maxWidth) lo = mid; else hi = mid - 1;
  }
  let n = lo;
  while (n > 0 && text.charAt(n - 1) === ' ') n -= 1;
  if (n < minChars) return null;
  const cut = text.slice(0, n) + ellipsis;
  return { text: cut, width: widthAt(n) + ew, cut: true };
}

/* ---- Geometry -------------------------------------------------------------- */

function bboxOf(p) {
  if (p.t === 'c') return [p.x - p.r, p.y - p.r, p.x + p.r, p.y + p.r];
  if (p.t === 'r') return [p.x0, p.y0, p.x1, p.y1];
  if (p.t === 's') return [Math.min(p.ax, p.bx), Math.min(p.ay, p.by), Math.max(p.ax, p.bx), Math.max(p.ay, p.by)];
  return [p.x - p.r1, p.y - p.r1, p.x + p.r1, p.y + p.r1]; // annulus
}
function segDist2(px, py, ax, ay, bx, by) {
  const dx = bx - ax, dy = by - ay;
  const l2 = dx * dx + dy * dy;
  let t = l2 ? ((px - ax) * dx + (py - ay) * dy) / l2 : 0;
  t = t < 0 ? 0 : t > 1 ? 1 : t;
  const qx = ax + dx * t - px, qy = ay + dy * t - py;
  return qx * qx + qy * qy;
}
function rectDist(px, py, r) {
  const dx = Math.max(r.x0 - px, 0, px - r.x1), dy = Math.max(r.y0 - py, 0, py - r.y1);
  return Math.hypot(dx, dy);
}
function segmentsCross(ax, ay, bx, by, cx, cy, dx, dy) {
  const o = (px, py, qx, qy, rx, ry) => Math.sign((qx - px) * (ry - py) - (qy - py) * (rx - px));
  return o(ax, ay, bx, by, cx, cy) !== o(ax, ay, bx, by, dx, dy) && o(cx, cy, dx, dy, ax, ay) !== o(cx, cy, dx, dy, bx, by);
}
function segHitsRect(s, r) {
  const inside = (x, y) => x >= r.x0 && x <= r.x1 && y >= r.y0 && y <= r.y1;
  if (inside(s.ax, s.ay) || inside(s.bx, s.by)) return true;
  const e = [[r.x0, r.y0, r.x1, r.y0], [r.x1, r.y0, r.x1, r.y1], [r.x1, r.y1, r.x0, r.y1], [r.x0, r.y1, r.x0, r.y0]];
  return e.some(([x0, y0, x1, y1]) => segmentsCross(s.ax, s.ay, s.bx, s.by, x0, y0, x1, y1));
}

/** Does label primitive `a` come within `pad` px of obstacle primitive `b`? */
export function collides(a, b, pad = 0) {
  if (b.t === 'c') {
    if (a.t === 'c') return Math.hypot(a.x - b.x, a.y - b.y) < a.r + b.r + pad;
    return rectDist(b.x, b.y, a) < b.r + pad;
  }
  if (b.t === 'r') {
    if (a.t === 'c') return rectDist(a.x, a.y, b) < a.r + pad;
    return a.x0 < b.x1 + pad && a.x1 > b.x0 - pad && a.y0 < b.y1 + pad && a.y1 > b.y0 - pad;
  }
  if (b.t === 's') {
    if (a.t === 'c') return segDist2(a.x, a.y, b.ax, b.ay, b.bx, b.by) < (a.r + pad) ** 2;
    return segHitsRect(b, { x0: a.x0 - pad, y0: a.y0 - pad, x1: a.x1 + pad, y1: a.y1 + pad });
  }
  // Annulus about (x, y) between r0 and r1.
  let lo, hi;
  if (a.t === 'c') { const d = Math.hypot(a.x - b.x, a.y - b.y); lo = d - a.r; hi = d + a.r; } else {
    lo = rectDist(b.x, b.y, a);
    hi = Math.max(...[[a.x0, a.y0], [a.x1, a.y0], [a.x0, a.y1], [a.x1, a.y1]].map(([x, y]) => Math.hypot(x - b.x, y - b.y)));
  }
  return hi > b.r0 - pad && lo < b.r1 + pad;
}

/* ---- The planner ----------------------------------------------------------- */

function normaliseObstacle(ob) {
  const pad = ob.pad || 0;
  const tag = ob.tag || ob.kind;
  switch (ob.kind) {
    case 'rect': return [{ ...rectShape(ob.x0, ob.y0, ob.x1, ob.y1), pad, tag }];
    case 'circle': return [{ t: 'c', x: ob.x, y: ob.y, r: ob.r, pad, tag }];
    case 'annulus': return [{ t: 'a', x: ob.x, y: ob.y, r0: ob.r0, r1: ob.r1, pad, tag }];
    case 'polyline': {
      const pts = ob.points || [];
      const out = [];
      for (let i = 1; i < pts.length; i += 1) {
        const [ax, ay] = pts[i - 1], [bx, by] = pts[i];
        out.push({ t: 's', ax, ay, bx, by, pad, tag });
      }
      if (pts.length === 1) out.push({ t: 'c', x: pts[0][0], y: pts[0][1], r: 0, pad, tag });
      return out;
    }
    case 'shape': return (ob.shape || []).map((p) => ({ ...p, pad, tag }));
    default: throw new Error(`labels: unknown obstacle kind ${ob.kind}`);
  }
}

/**
 * A planner for one paint.
 *   bounds: {x0, y0, x1, y1} every label must lie inside (optional)
 *   gap:    px kept between two placed labels (default 4)
 *
 * planner.block(obstacle) adds a hard obstacle (chainable):
 *   {kind:'rect', x0, y0, x1, y1, pad?, tag?}
 *   {kind:'circle', x, y, r, pad?, tag?}
 *   {kind:'annulus', x, y, r0, r1, pad?, tag?}
 *   {kind:'polyline', points:[[x, y], ...], pad?, tag?}
 *   {kind:'shape', shape:[primitive...], pad?, tag?}
 * planner.place(candidate) places one candidate now (greedy) or returns null.
 * planner.plan(candidates) places a batch by priority, then id.
 *
 * A candidate: {id, priority, anchors:[anchor...], ignore?:[tag...], fit?(px)}
 *   anchor {kind:'rect', x0, y0, x1, y1, ...}
 *   anchor {kind:'arc', cx, cy, radius, mid, width, height, ...}
 *   anchor {kind:'radial', cx, cy, angle, from, length, height, ...}: the
 *     free run along the ray is measured to the first obstacle, then
 *     candidate.fit(freePx) returns {text, width} (or null to reject) and
 *     only that width is claimed.
 *   anchor {kind:'shape', shape:[primitive...], ...}: a precomputed footprint.
 * Extra anchor fields are returned untouched on the placement.
 */
export function createPlanner({ bounds = null, gap = 4, cell = 48 } = {}) {
  const grid = new Map();
  const wide = [];
  const all = [];
  let stamp = 0;
  const placed = [];
  const rejected = [];
  const keyOf = (i, j) => i * 100003 + j;
  function insert(p) {
    p.stamp = 0;
    all.push(p);
    const [x0, y0, x1, y1] = bboxOf(p);
    const pad = p.pad || 0;
    const i0 = Math.floor((x0 - pad) / cell), i1 = Math.floor((x1 + pad) / cell);
    const j0 = Math.floor((y0 - pad) / cell), j1 = Math.floor((y1 + pad) / cell);
    if (p.t === 'a' || (i1 - i0 + 1) * (j1 - j0 + 1) > 64) { wide.push(p); return; }
    for (let i = i0; i <= i1; i += 1) for (let j = j0; j <= j1; j += 1) {
      const key = keyOf(i, j);
      let list = grid.get(key);
      if (!list) grid.set(key, (list = []));
      list.push(p);
    }
  }
  function hitOf(prim, ignore, extraPad = 0) {
    if (bounds) {
      const [x0, y0, x1, y1] = bboxOf(prim);
      if (x0 < bounds.x0 || y0 < bounds.y0 || x1 > bounds.x1 || y1 > bounds.y1) return 'bounds';
    }
    stamp += 1;
    const check = (p) => {
      if (p.stamp === stamp) return false;
      p.stamp = stamp;
      if (ignore && ignore.includes(p.tag)) return false;
      return collides(prim, p, (p.pad || 0) + extraPad);
    };
    for (const p of wide) if (check(p)) return p.tag || 'obstacle';
    const [x0, y0, x1, y1] = bboxOf(prim);

    // Obstacles are filed under their box grown by their pad, so the
    // candidate's own box finds every one it could touch.
    const i0 = Math.floor(x0 / cell), i1 = Math.floor(x1 / cell);
    const j0 = Math.floor(y0 / cell), j1 = Math.floor(y1 / cell);
    for (let i = i0; i <= i1; i += 1) for (let j = j0; j <= j1; j += 1) {
      const list = grid.get(keyOf(i, j));
      if (!list) continue;
      for (const p of list) if (check(p)) return p.tag || 'obstacle';
    }
    return null;
  }
  function testShape(shape, ignore) {
    for (const prim of shape) { const hit = hitOf(prim, ignore); if (hit) return hit; }
    return null;
  }
  function claim(shape, id) {
    for (const prim of shape) insert({ ...prim, pad: gap, tag: 'label', owner: id });
  }
  function tryAnchor(c, anchor) {
    const ignore = c.ignore || null;
    if (anchor.kind === 'radial') {
      const h = anchor.height;
      const discs = radialDiscs(anchor.cx, anchor.cy, anchor.angle, anchor.from, anchor.length, h);
      let free = 0, reason = null;
      for (const d of discs) {
        const hit = hitOf(d, ignore);
        if (hit) { reason = hit; break; }
        free = Math.min(anchor.length, Math.hypot(d.x - anchor.cx, d.y - anchor.cy) - anchor.from + d.r);
      }
      const fit = anchor.fit || c.fit;
      const fitted = fit ? fit(free) : (free >= (anchor.minLength || 0) ? { width: free } : null);
      if (!fitted || fitted.width <= 0) return { reason: reason ? `short:${reason}` : 'short' };
      const shape = radialDiscs(anchor.cx, anchor.cy, anchor.angle, anchor.from, fitted.width, h);
      return { shape, fitted, length: fitted.width, stoppedBy: fitted.cut ? reason : null };
    }
    let shape;
    if (anchor.kind === 'rect') shape = [rectShape(anchor.x0, anchor.y0, anchor.x1, anchor.y1)];
    else if (anchor.kind === 'arc') shape = arcDiscs(anchor.cx, anchor.cy, anchor.radius, anchor.mid, anchor.width, anchor.height);
    else if (anchor.kind === 'shape') shape = anchor.shape;
    else throw new Error(`labels: unknown anchor kind ${anchor.kind}`);
    const hit = testShape(shape, ignore);
    if (hit) return { reason: hit };
    const fit = anchor.fit || c.fit;
    return { shape, fitted: fit ? fit(Infinity) : null };
  }
  const api = {
    block(ob) { for (const p of normaliseObstacle(ob)) insert(p); return api; },
    /** The first obstacle tag a footprint would hit, or null. */
    test(shape, ignore = null) { return testShape(shape, ignore); },
    place(c) {
      const reasons = [];
      for (let i = 0; i < (c.anchors || []).length; i += 1) {
        const anchor = c.anchors[i];
        const got = tryAnchor(c, anchor);
        if (got.reason) { reasons.push(got.reason); continue; }
        claim(got.shape, c.id);
        const placement = { id: c.id, priority: c.priority, anchor, index: i, shape: got.shape, fitted: got.fitted || null, length: got.length, stoppedBy: got.stoppedBy || null, data: c.data };
        placed.push(placement);
        return placement;
      }
      rejected.push({ id: c.id, priority: c.priority, reason: reasons.length ? reasons.join(',') : 'no-anchor', data: c.data });
      return null;
    },
    plan(candidates) {
      const order = [...candidates].sort((a, b) => a.priority - b.priority || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
      const out = new Map();
      for (const c of order) { const p = api.place(c); if (p) out.set(c.id, p); }
      return out;
    },
    placed,
    rejected,
    obstacles: () => all.length,
    /** Bounding rectangles of every placed label primitive, for legacy box tests. */
    boxes() {
      const out = [];
      for (const p of placed) for (const prim of p.shape) {
        const [x0, y0, x1, y1] = bboxOf(prim);
        out.push({ x0, y0, x1, y1 });
      }
      return out;
    },
  };
  return api;
}
