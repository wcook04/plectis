// Where everything on the evidence map stands, in layout units.
//
// Inside the ring the picture follows the paper's chain
// (paper/plectis-public-system.tex, figure "chain"), from the centre outward.
// The replay-admission core stands at the centre: every component's replay
// route runs to it as a hairline spoke. The three other workflow cores
// (repair, compatibility, views) stand round it: they belong to the toolkit,
// not to any one component. Each of the twelve component kernels, a
// specification with one petal for every verified task, grows on its own
// component's radius, on a stem in from the component through its caller and
// its generated code, so the chain reads straight along one spoke; where two
// flowers would touch, the later one stands a bloom further in. The 88
// components stand in their family sectors, as on the system map.
//
// Outside the ring stand the coverage rings (evidence.js TRACKS): one ring
// per kind of check, one cell per component, so reading round a ring shows
// which components have that check and reading outward along a spoke shows
// what one component has. A wedge at the top is kept clear for the rings'
// names. A component without a modeled contract has no thread and empty
// inner cells: the gaps are the honest picture of formal coverage.
//
// Coordinates are deterministic, so the drawing is the same on every visit.

import { BACKING_ORDER, FAMILY_ORDER, TRACKS } from '../evidence.js';

export const R = {
  core: 0,
  cores: 100,
  kernel: 300, // the outermost bloom; crowded flowers step in from here
  bloom: 52, // one step in
  petal: 21,
  component: 360,
  track0: 374,
  trackH: 10,
  trackGap: 2.6,
  labels: 0,
};
R.trackOuter = R.track0 + TRACKS.length * (R.trackH + R.trackGap) - R.trackGap;
R.scale = R.trackOuter + 4;
R.labels = R.scale + 22;
// Beyond the family names, the doctrine's halo: the principles on the inner
// orbit, the axioms they rest on outside them, and the failure modes that
// threaten those axioms outermost, so reading outward along a spoke goes from
// a component, through its checks, to the rules it cites and their basis.
R.principles = R.scale + 104;
R.axioms = R.principles + 36;
R.failures = R.axioms + 34;
R.haloOuter = R.failures + 9;
// Just inside the principles runs the halo's rim: a lit citation travels
// round it from a rule and drops straight down into each citing column.
// At rest a comb hangs from it, one tooth per component, a step per rule.
R.rim = R.principles - 12;
R.tooth = 1.5;
// The register: one quiet tick per component just outside its rings, and,
// for a chosen rule, a cap on each citing column. Routes leave from here.
R.cap0 = R.scale + 4;
R.cap1 = R.scale + 12;

/** Inner and outer radius of a coverage ring. */
export function trackBand(i) {
  const r0 = R.track0 + i * (R.trackH + R.trackGap);
  return [r0, r0 + R.trackH];
}

const SLOT_PAD = 1.1;
const SECTOR_GAP = 0.05;
export const KEY_GAP = 0.24;
const TURN = Math.PI * 2;

/** Sector and slot order: families clockwise after the key wedge, members by backing then title. */
export function arrange(components) {
  const families = FAMILY_ORDER.filter((f) => components.some((c) => c.family === f));
  for (const c of components) if (!families.includes(c.family)) families.push(c.family);
  const groups = families.map((family) => ({
    family,
    members: components.filter((c) => c.family === family).sort((a, b) => {
      const ba = BACKING_ORDER.indexOf(a.backing); const bb = BACKING_ORDER.indexOf(b.backing);
      return (ba < 0 ? 99 : ba) - (bb < 0 ? 99 : bb) || a.title.localeCompare(b.title);
    }),
  }));
  const slots = groups.reduce((n, g) => n + g.members.length + SLOT_PAD, 0);
  const gaps = SECTOR_GAP * Math.max(0, groups.length - 1) + KEY_GAP;
  const pitch = (TURN - gaps) / slots;
  // The ring starts just clockwise of the key wedge, which is centred at the top.
  let at = -Math.PI / 2 + KEY_GAP / 2;
  const angleOf = new Map();
  const sectors = groups.map((g) => {
    const lo = at;
    const hi = lo + (g.members.length + SLOT_PAD) * pitch;
    at = hi + SECTOR_GAP;
    g.members.forEach((c, j) => angleOf.set(c.id, lo + (SLOT_PAD / 2 + j + 0.5) * pitch));
    return { family: g.family, lo, hi, mid: (lo + hi) / 2, members: g.members.map((c) => c.id), count: g.members.length };
  });
  return { sectors, angleOf, pitch };
}

export function shortArc(from, to) {
  let d = (to - from) % TURN;
  if (d > Math.PI) d -= TURN;
  if (d < -Math.PI) d += TURN;
  return d;
}

/* ---- Flowers: one footprint for painting, hit testing, placement, labels -- */
//
// A flower's screen radius is min(cap, 24·k) px: 24 layout units until it
// reaches its cap (46 px, or 62 px for the replay checker at the centre), so
// zooming in never balloons it into its neighbours. Its broken copies stand
// as small crosses on an arc just outside the petal tips, on the side away
// from its stem. Its footprint is the petal radius, plus that ring of
// crosses, plus 6 px of air; below FLOWER.refK every pixel measure shrinks
// with the drawing, so the footprint is bounded in layout units at every zoom
// and the placement below can guarantee that no two footprints meet.
export const FLOWER = {
  world: 24, // petal radius in layout units, until the cap
  cap: 46, replayCap: 62, // px
  refK: 0.6, // below this zoom the pixel measures scale with the drawing
  crossGap: 3, crossArm: 5, crossPitch: 9, // px: gap past the tips, × arm, spacing
  pad: 6, // px of air round the drawn flower
  stemAir: 4, // px a stem keeps clear of another flower's footprint
};
const CROSS_HALF = FLOWER.crossArm / Math.SQRT2; // half the × box for a 5 px arm

/**
 * A flower's measures in screen px at zoom k: petal radius r, the radius of
 * its cross ring's centre line, the ring's depth, the drawn reach (petals and
 * crosses) and the footprint (reach + air). `s` is the scale applied to the
 * fixed pixel measures (1 at or above FLOWER.refK).
 */
export function flowerPx(k, { replay = false, mutants = 0 } = {}) {
  const s = Math.min(1, k / FLOWER.refK);
  const r = Math.min(replay ? FLOWER.replayCap : FLOWER.cap, FLOWER.world * k);
  const half = CROSS_HALF * s;
  const ring = mutants ? FLOWER.crossGap * s + 2 * half : 0;
  const crossR = r + FLOWER.crossGap * s + half;
  const reach = r + ring;
  return { r, s, half, crossR, ring, reach, footprint: reach + FLOWER.pad * s };
}
/**
 * The angular half-span (radians, about the cross direction) of a flower's
 * cross arc at zoom k, with the cross box itself; 0 when it has none.
 */
export function crossSpan(k, mutants) {
  if (!mutants) return 0;
  const f = flowerPx(k, { mutants });
  return (((mutants - 1) / 2) * FLOWER.crossPitch * f.s + f.half) / f.crossR;
}
// The pixel measures and the petals are both proportional to k below refK and
// shrink in layout units above it, so refK is the worst case in layout units.
const worst = (mutants) => flowerPx(FLOWER.refK, { mutants });
/** Least distance in layout units between two flower centres: both reaches and one pad, at the worst zoom. */
export function flowerRoom(mutantsA = 1, mutantsB = 1) {
  return (worst(mutantsA).reach + worst(mutantsB).reach + FLOWER.pad) / FLOWER.refK;
}
/**
 * How far in layout units a stem must keep from a flower's centre in a given
 * direction (radians, world): its footprint plus stem air, counting the cross
 * ring only within the cross arc, where the crosses actually stand.
 */
export function stemClearance(mutants, crossDir, dir) {
  const f = worst(mutants);
  const span = crossSpan(FLOWER.refK, mutants) + 0.35;
  const inCross = mutants && Math.abs(shortArc(crossDir, dir)) <= span;
  return ((inCross ? f.reach : f.r) + (FLOWER.pad + FLOWER.stemAir) * f.s) / FLOWER.refK;
}

export const BLOOM_ROOM = flowerRoom(3, 3);
/** The radial candidates for a kernel flower: outermost first (300, 248, 196). */
export const BLOOM_RADII = [R.kernel, R.kernel - R.bloom, R.kernel - 2 * R.bloom];

/**
 * How many blooms in from the outermost each kernel stands. Each kernel
 * keeps its own component's radius and takes one of the radial candidates;
 * no two flowers, at any depth, and no fixed flower (`fixed`, the toolkit
 * cores as {x, y}) may stand nearer than `room` layout units. The search is
 * a deterministic depth-first walk in angle order, outermost candidates
 * first, so the same input always gives the same placement; if no placement
 * clears every pair, the one with the largest least gap is kept.
 */
export function bloomDepths(angles, radius = R.kernel, step = R.bloom, room = BLOOM_ROOM, fixed = [], depths = 3) {
  const n = angles.length;
  const order = angles.map((a, i) => [a, i]).sort((p, q) => p[0] - q[0] || p[1] - q[1]).map(([, i]) => i);
  const pos = (i, d) => polar(angles[i], radius - d * step);
  const gapTo = (i, d, placed) => {
    const [x, y] = pos(i, d);
    let g = Infinity;
    for (const f of fixed) g = Math.min(g, Math.hypot(f.x - x, f.y - y));
    for (const [j, dj] of placed) { const [u, v] = pos(j, dj); g = Math.min(g, Math.hypot(u - x, v - y)); }
    return g;
  };
  const depth = new Array(n).fill(0);
  const placed = [];
  let budget = 200000;
  const walk = (at) => {
    if (at === n) return true;
    const i = order[at];
    for (let d = 0; d < depths; d += 1) {
      if (budget-- <= 0) return false;
      if (gapTo(i, d, placed) < room) continue;
      placed.push([i, d]); depth[i] = d;
      if (walk(at + 1)) return true;
      placed.pop();
    }
    return false;
  };
  if (walk(0)) return depth;
  // No clear placement: greedily keep the candidate with the widest gap.
  placed.length = 0;
  for (const i of order) {
    let best = 0, bestGap = -1;
    for (let d = 0; d < depths; d += 1) {
      const g = gapTo(i, d, placed);
      if (g >= room) { best = d; bestGap = g; break; }
      if (g > bestGap + 1e-9) { best = d; bestGap = g; }
    }
    placed.push([i, best]); depth[i] = best;
  }
  return depth;
}

export const polar = (angle, r) => [Math.cos(angle) * r, Math.sin(angle) * r];

// The workflow cores round the replay-admission core: either side and below,
// so each can name itself on its outer side.
const CORE_ANGLES = { repair: Math.PI, compatibility: 0, views: Math.PI / 2 };

// A polar polyline, sampled every few layout units: radial runs and arcs.
function stemPts(legs) {
  const pts = [];
  for (const leg of legs) {
    const seg = [];
    if (leg.arc) {
      const [a0, a1, r] = leg.arc;
      const n = Math.max(2, Math.ceil(Math.abs(a1 - a0) * r / 3));
      for (let i = 0; i <= n; i += 1) seg.push(polar(a0 + (a1 - a0) * (i / n), r));
    } else {
      const [a, r0, r1] = leg.radial;
      const n = Math.max(2, Math.ceil(Math.abs(r1 - r0) / 3));
      for (let i = 0; i <= n; i += 1) seg.push(polar(a, r0 + (r1 - r0) * (i / n)));
    }
    pts.push(...(pts.length ? seg.slice(1) : seg));
  }
  return pts;
}
/** The point at fraction t of a polyline's arc length, measured after its first `skip` units. */
export function pointAlong(pts, t, skip = 0) {
  let total = 0;
  const seg = [];
  for (let i = 1; i < pts.length; i += 1) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); seg.push(d); total += d; }
  let left = skip + t * Math.max(0, total - skip);
  for (let i = 0; i < seg.length; i += 1) {
    if (left <= seg[i] || i === seg.length - 1) {
      const f = seg[i] ? Math.min(1, left / seg[i]) : 0;
      return [pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f];
    }
    left -= seg[i];
  }
  return pts[pts.length - 1];
}
// The least margin (layout units; negative inside) a stem keeps from any flower.
function stemMargin(pts, skip, flowers) {
  let least = Infinity;
  let walked = 0;
  for (let i = 0; i < pts.length; i += 1) {
    if (i) walked += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    if (walked < skip) continue;
    const [x, y] = pts[i];
    for (const f of flowers) {
      const d = Math.hypot(x - f.x, y - f.y);
      least = Math.min(least, d - stemClearance(f.mutants, f.crossDir, Math.atan2(y - f.y, x - f.x)));
    }
  }
  return least;
}
/**
 * A kernel's stem, from its flower out to its component's mark. Straight
 * along the component's radius when that keeps clear of every other flower's
 * footprint plus stem air; otherwise it doglegs one, then two, component
 * pitches to either side, inside the family sector: out of the flower, round
 * an arc, out past the obstacle, and back to the mark round an arc just
 * inside the ring. The generated code stands at 40% and the caller at 70% of
 * the stem's arc length, measured from the flower's petal tips.
 */
export function stemFor(k, sector, pitch, flowers) {
  const end = R.component;
  const skip = FLOWER.world; // the stem leaves the flower at its petal tips
  const t1 = k.r + FLOWER.world + 4, t2 = R.component - 16;
  const options = [{ dogleg: 0, legs: [{ radial: [k.angle, k.r, end] }] }];
  for (const steps of [1, 2]) {
    for (const sign of [1, -1]) {
      const b = k.angle + sign * steps * pitch;
      if (sector && (b < sector.lo + pitch * 0.5 || b > sector.hi - pitch * 0.5)) continue;
      options.push({ dogleg: sign * steps, legs: [
        { radial: [k.angle, k.r, t1] }, { arc: [k.angle, b, t1] }, { radial: [b, t1, t2] }, { arc: [b, k.angle, t2] }, { radial: [k.angle, t2, end] }] });
    }
  }
  let best = null;
  for (const o of options) {
    const pts = stemPts(o.legs);
    const cand = { stem: pts, dogleg: o.dogleg, clearance: stemMargin(pts, skip, flowers) };
    if (cand.clearance >= 0) { best = cand; break; }
    if (!best || cand.clearance > best.clearance + 1e-9) best = cand;
  }
  const generated = pointAlong(best.stem, 0.4, skip);
  const caller = pointAlong(best.stem, 0.7, skip);
  return { ...best, generated, caller, generatedR: Math.hypot(...generated), callerR: Math.hypot(...caller) };
}

/** The whole layout for a model from data.js. */
export function layout(model) {
  const { sectors, angleOf, pitch } = arrange(model.components);
  const comps = model.components.map((c) => {
    const angle = angleOf.get(c.id);
    const [x, y] = polar(angle, R.component);
    return { id: c.id, angle, x, y };
  });
  const others = model.cores.filter((c) => c.id !== 'replay_admission');
  const cores = model.cores.map((c) => {
    if (c.id === 'replay_admission') return { id: c.id, x: 0, y: 0, angle: 0 };
    const angle = CORE_ANGLES[c.id] ?? (-Math.PI / 2 + (others.indexOf(c) / Math.max(1, others.length)) * TURN);
    const [x, y] = polar(angle, R.cores);
    return { id: c.id, x, y, angle };
  });
  const linked = model.kernels.filter((k) => k.componentId && angleOf.has(k.componentId));
  const depths = bloomDepths(linked.map((k) => angleOf.get(k.componentId)), R.kernel, R.bloom, BLOOM_ROOM, cores);
  const sectorOf = new Map();
  for (const sct of sectors) for (const id of sct.members) sectorOf.set(id, sct);
  const kernels = linked.map((k, i) => {
    const angle = angleOf.get(k.componentId);
    const r = R.kernel - depths[i] * R.bloom;
    const [x, y] = polar(angle, r);
    return { id: k.id, componentId: k.componentId, angle, x, y, r, depth: depths[i], mutants: (k.mutants || []).length, to: angle };
  });
  // Every flower a stem must keep clear of: the other kernels and the cores.
  const flowers = [
    ...kernels.map((k) => ({ id: k.id, x: k.x, y: k.y, mutants: k.mutants, crossDir: k.angle + Math.PI })),
    ...cores.map((c) => {
      const core = model.cores.find((m) => m.id === c.id);
      const crossDir = c.id === 'replay_admission' ? -Math.PI / 2 : c.angle;
      return { id: c.id, x: c.x, y: c.y, mutants: (core?.mutants || []).length, crossDir };
    }),
  ];
  for (const k of kernels) {
    const sector = sectorOf.get(k.componentId);
    Object.assign(k, stemFor(k, sector, pitch, flowers.filter((f) => f.id !== k.id)));
  }
  // Unlinked kernels (none today) wait on a small arc under the cores.
  model.kernels.filter((k) => !linked.includes(k)).forEach((k, i) => {
    const angle = Math.PI / 2 + (i - 0.5) * 0.3;
    const r = R.cores + 90;
    const [x, y] = polar(angle, r);
    kernels.push({ id: k.id, componentId: null, angle, x, y, r, depth: 0, mutants: (k.mutants || []).length,
      stem: [], dogleg: 0, clearance: Infinity, generated: null, caller: null, generatedR: null, callerR: null, to: null });
  });
  const halo = model.rules && model.rules.length ? haloLayout(model, angleOf) : null;
  return { sectors, pitch, comps, kernels, cores, halo, radius: halo ? R.haloOuter : R.labels + 44 };
}

/* ---- The doctrine halo ----------------------------------------------------- */
//
// Adapted from the system map's doctrine necklace (ai_workflow
// sites/microcosm/assets/system-map.js coreLayout at 17c49004bd): the hub
// order chosen so the rules tied to several axioms span as few of them as
// can be managed, then turned toward the components that cite them; and
// every line to a hub leaves and lands along the radius. Here the necklace
// is moved outside the ring and opened into three orbits, and its U-shaped
// chords become ruled lanes (system-map.js chordShape 'lane'): out of a rule
// along its radius, round a lane, and into each of its axioms.

const ORBIT_OF = { principle: 'principles', axiom: 'axioms', anti_principle: 'failures' };
// Usable arc: the same wedge as the components' is kept clear at the top.
export const shareAngle = (s) => -Math.PI / 2 + KEY_GAP / 2 + s * (TURN - KEY_GAP);
export const angleShare = (a) => ((((a + Math.PI / 2 - KEY_GAP / 2) % TURN) + TURN) % TURN) / (TURN - KEY_GAP);
const HALO_GAP = 30; // least layout units between two marks on one orbit
const LANE_PAD = 8; // a lane's distance from the orbit glyphs it serves
const ALIGN = 1.2; // pull of the citing components on the axioms' order

/** The axioms' order round the halo: fewest spanned hubs, then nearest their citers. */
export function axiomOrder(axioms, groups, pref = new Map()) {
  const n = axioms.length;
  const cost = (order) => {
    const at = new Map(order.map((id, i) => [id, i]));
    let c = 0;
    for (const g of groups) {
      let lo = Infinity, hi = -Infinity;
      for (const id of g) { const p = at.get(id); if (p === undefined) continue; lo = Math.min(lo, p); hi = Math.max(hi, p); }
      if (hi > lo) c += hi - lo;
    }
    for (const [id, p] of at) if (pref.has(id)) c += ALIGN * Math.abs((p + 0.5) / n - pref.get(id));
    return c;
  };
  let order = [...axioms];
  let best = cost(order);
  // Swaps and reversals until neither helps: deterministic, and quick for twelve.
  for (let round = 0, better = true; better && round < 60; round += 1) {
    better = false;
    for (let i = 0; i < n - 1; i += 1) {
      for (let j = i + 1; j < n; j += 1) {
        const swap = [...order]; [swap[i], swap[j]] = [swap[j], swap[i]];
        const turn = [...order.slice(0, i), ...order.slice(i, j + 1).reverse(), ...order.slice(j + 1)];
        for (const cand of [swap, turn]) {
          const c = cost(cand);
          if (c < best - 1e-9) { order = cand; best = c; better = true; }
        }
      }
    }
  }
  return order;
}

/** Push marks apart along one orbit (shares 0..1), then draw each back toward its target. */
export function spreadLine(targets, gap) {
  const order = targets.map((t, i) => [t, i]).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const pos = order.map(([t]) => Math.min(1 - gap / 2, Math.max(gap / 2, t)));
  const push = () => {
    for (let i = 0; i < pos.length - 1; i += 1) {
      const d = pos[i + 1] - pos[i];
      if (d < gap) { const p = (gap - d) / 2; pos[i] -= p; pos[i + 1] += p; }
    }
  };
  for (let pass = 0; pass < 400; pass += 1) {
    for (let i = 0; i < pos.length; i += 1) {
      pos[i] += (order[i][0] - pos[i]) * 0.02;
      pos[i] = Math.min(1 - gap / 2, Math.max(gap / 2, pos[i]));
    }
    push();
  }
  // The pull back toward each target ends before the last pushes, so no two
  // marks are left nearer than the gap.
  for (let pass = 0; pass < 60; pass += 1) push();
  const out = new Array(pos.length);
  order.forEach(([, original], k) => { out[original] = pos[k]; });
  return out;
}

// A polar polyline in layout units: radial from (a, r0) to r1.
const radial = (a, r0, r1) => [polar(a, r0), polar(a, r1)];
function arcPts(a0, a1, r) {
  const n = Math.max(2, Math.ceil(Math.abs(a1 - a0) * r / 5));
  const pts = [];
  for (let i = 0; i <= n; i += 1) pts.push(polar(a0 + (a1 - a0) * (i / n), r));
  return pts;
}

/* ---- Route planner ---------------------------------------------------------- */
//
// One relation, one line. A route joins a component's cap to a rule glyph:
// it rises radially beside the column, runs round a lane just inside the
// rule's orbit, and steps up to the glyph. Routes from one hub (a chosen
// component, or a chosen rule) are nested so that none crosses another, the
// pitch between neighbours is at least `pitchPx` on screen, and corners are
// filleted. Where a cap stands under a family label, the route runs along
// the thin corridor just above the caps to the label's nearest edge first.
// Positions round the ring are shares (0..1 clockwise from the key wedge),
// so no route ever crosses the wedge. Radii are layout units; `k` is pixels
// per layout unit at the current zoom. Pure: painter and tests share it.

const SPAN = TURN - KEY_GAP;

/**
 * Plan the routes from one hub to its leaves.
 *
 * hub:    { s, r, kind: 'cap' | 'glyph' } — share, the radius the routes leave
 *         from (a cap's top, or just under a glyph), and which end it is.
 * leaves: [{ id, s, r, avoid?, jogR? }] — the other ends (glyph bottoms for a
 *         cap hub, cap tops for a glyph hub). A glyph leaf whose step up would
 *         pass behind another glyph (an axiom over a principle) names those
 *         shares in `avoid` and steps up beside it, jogging in at `jogR`;
 *         with no room for the jog it enters from the side, at `orbit`,
 *         stopping `half` (a share) short of the glyph's centre.
 * band:   { lo, hi } — the lane band, in layout units.
 * corridor: { lo, hi } | null — the corridor above the caps, under the labels.
 * blocked: [[s0, s1]] — shares where the family band carries a label.
 * colShare: one component's pitch, as a share.
 *
 * Returns { fits, reason, sides, routes }: `fits` is false when a side needs
 * more lanes (or corridor tracks) than the band holds at this zoom, or the
 * plan would cross; `routes` is always computed (one per leaf), each
 * { id, side, lane, waypoints: [[s, r]...], pts: [[x, y]...] } running from
 * the hub to the leaf.
 */
export function planRoutes({ hub, leaves: given, k, band, corridor = null, blocked = [], colShare = 0.01, pitchPx = 3, portPx = 3, filletPx = 4, maxPitchPx = 6, wrap = true, check = true }) {
  const pW = pitchPx / k;
  const shareOfPx = (px, r) => px / (Math.max(1, r) * k * SPAN);
  // A whole turn in shares. With `wrap`, a leaf more than half a turn away
  // is reached the short way, across the key wedge.
  const P = TURN / SPAN;
  const leaves = given.map((l) => {
    if (!wrap) return l;
    let s = l.s;
    while (s - hub.s > P / 2) s -= P;
    while (hub.s - s > P / 2) s += P;
    return s === l.s ? l : { ...l, s };
  });
  const blockOf = (s) => {
    for (const off of [0, -P, P]) {
      const b = blocked.find(([a, z]) => s >= a + off && s <= z + off);
      if (b) return [b[0] + off, b[1] + off];
    }
    return null;
  };
  const slots = Math.max(0, Math.floor((band.hi - band.lo) / pW + 1e-9));
  const cSlots = corridor ? Math.max(0, Math.floor((corridor.hi - corridor.lo) / pW + 1e-9) + 1) : 0;
  const sides = { cw: { need: 0, slots, corridorNeed: 0, corridorSlots: cSlots }, ccw: { need: 0, slots, corridorNeed: 0, corridorSlots: cSlots } };
  // The reason reported is the most basic one: lanes, then corridor, label, crossing.
  const ORDER = ['lanes', 'corridor', 'label', 'crossing'];
  let reason = null;
  const fail = (why) => { if (!reason || ORDER.indexOf(why) < ORDER.indexOf(reason)) reason = why; };
  const routes = [];
  const sorted = [...leaves].sort((p, q) => Math.abs(p.s - hub.s) - Math.abs(q.s - hub.s) || (p.id < q.id ? -1 : p.id > q.id ? 1 : 0));

  // The last move up into a glyph: straight, or beside a glyph in the way.
  const stepUp = (leaf, h, sign) => {
    let clash = null;
    if (leaf.jogR) for (const off of [0, -P, P]) for (const [a, z] of leaf.avoid || []) if (!clash && leaf.s > a + off && leaf.s < z + off) clash = [a + off, z + off];
    if (!clash) return [[leaf.s, h], [leaf.s, leaf.r]];
    if (leaf.jogR < leaf.r) {
      const e = sign > 0 ? clash[0] : clash[1]; // the edge the lane arrives at
      return [[e, h], [e, leaf.jogR], [leaf.s, leaf.jogR], [leaf.s, leaf.r]];
    }
    // No room under the glyph: rise beside both and enter it from the side.
    const half = leaf.half || 0;
    const e = sign > 0 ? Math.min(clash[0], leaf.s - half * 1.25) : Math.max(clash[1], leaf.s + half * 1.25);
    return [[e, h], [e, leaf.orbit], [leaf.s - sign * half, leaf.orbit]];
  };
  if (hub.kind === 'cap') {
    const hb = blockOf(hub.s);
    for (const [name, sign] of [['cw', 1], ['ccw', -1]]) {
      const list = sorted.filter((l) => (sign > 0 ? l.s >= hub.s : l.s < hub.s));
      const n = list.length;
      if (!n) continue;
      sides[name].need = n;
      if (n > slots) fail('lanes');
      const lp = Math.max(pW, Math.min(maxPitchPx / k, (band.hi - band.lo) / n));
      const dS = shareOfPx(portPx, hub.r);
      if (hb) {
        sides[name].corridorNeed = n;
        if (n > cSlots) fail('corridor');
      }
      list.forEach((leaf, j) => {
        const h = band.hi - (j + 0.5) * lp; // the nearest target takes the lane nearest the orbit
        const wp = [];
        if (hb && corridor) {
          const u = hub.s + sign * (j + 0.5) * Math.min(dS, (colShare * 0.33) / n);
          const c = corridor.hi - j * pW;
          const edge = sign > 0 ? hb[1] : hb[0];
          const x = edge + sign * (j + 0.5) * shareOfPx(portPx, corridor.lo);
          wp.push([u, hub.r], [u, c], [x, c], [x, h], ...stepUp(leaf, h, sign));
        } else {
          let x = hub.s + sign * (colShare * 0.2 + j * dS);
          if (sign * (leaf.s - x) <= 0) wp.push([leaf.s, hub.r], [leaf.s, leaf.r]); // the target stands over the column
          else wp.push([x, hub.r], [x, h], ...stepUp(leaf, h, sign));
          if (blockOf(x)) fail('label');
        }
        routes.push({ id: leaf.id, side: name, lane: j, waypoints: wp });
      });
    }
  } else {
    // From a rule: each leaf's entry angle is its own, or, under a label,
    // just outside the label's edge nearer the rule.
    const plans = sorted.map((leaf) => {
      const lb = blockOf(leaf.s);
      if (!lb) return { leaf, edge: null, block: null, side: leaf.s >= hub.s ? 'cw' : 'ccw' };
      const edge = Math.abs(lb[0] - hub.s) <= Math.abs(lb[1] - hub.s) ? 0 : 1;
      return { leaf, block: lb, edge, side: lb[edge] >= hub.s ? 'cw' : 'ccw' };
    });
    // Rank within each label, nearest target first.
    const groups = new Map();
    for (const p of plans) if (p.block) {
      const key = `${p.block[0]}|${p.edge}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(p);
    }
    for (const g of groups.values()) {
      g.forEach((p, rank) => {
        const out = p.edge === 0 ? -1 : 1;
        const dS = shareOfPx(portPx, corridor ? corridor.lo : hub.r);
        p.entry = p.block[p.edge] + out * (g.length - 1 - rank + 0.5) * dS;
        p.rank = rank;
        p.c = corridor ? corridor.lo + rank * pW : null;
      });
      sides[g[0].side].corridorNeed = Math.max(sides[g[0].side].corridorNeed, g.length);
      if (!corridor || g.length > cSlots) fail('corridor');
    }
    for (const p of plans) if (!p.block) p.entry = p.leaf.s;
    for (const [name, sign] of [['cw', 1], ['ccw', -1]]) {
      const list = plans.filter((p) => p.side === name).sort((p, q) => Math.abs(p.entry - hub.s) - Math.abs(q.entry - hub.s) || (p.leaf.id < q.leaf.id ? -1 : 1));
      const n = list.length;
      if (!n) continue;
      sides[name].need = n;
      if (n > slots) fail('lanes');
      const lp = Math.max(pW, Math.min(maxPitchPx / k, (band.hi - band.lo) / n));
      const dS = shareOfPx(portPx, band.lo);
      list.forEach((p, j) => {
        const h = band.hi - (n - j - 0.5) * lp; // the nearest target takes the lane furthest from the orbit
        let d = hub.s + sign * (j + 0.5) * dS;
        if (sign * (p.entry - d) < 0) d = p.entry;
        const wp = [[d, hub.r], [d, h], [p.entry, h]];
        if (p.block && corridor) wp.push([p.entry, p.c], [p.leaf.s, p.c]);
        wp.push([p.leaf.s, p.leaf.r]);
        routes.push({ id: p.leaf.id, side: name, lane: j, waypoints: wp });
      });
    }
  }
  const fillet = filletPx / k;
  for (const r of routes) r.pts = tracePolar(r.waypoints, fillet, 5 / k);
  if (check && !reason && routes.length > 1 && anyCrossing(routes.map((r) => r.pts))) fail('crossing');
  return { fits: !reason, reason, sides, routes };
}

// Points along a polar path whose waypoints alternate radial and round
// moves, with each corner rounded by `fillet` layout units.
export function tracePolar(waypoints, fillet, step) {
  const wp = [];
  for (const p of waypoints) {
    const last = wp[wp.length - 1];
    if (last && Math.abs(last[0] - p[0]) < 1e-12 && Math.abs(last[1] - p[1]) < 1e-9) continue;
    wp.push(p);
  }
  // Merge consecutive moves of the same kind.
  for (let i = 1; i < wp.length - 1;) {
    const a = wp[i - 1], b = wp[i], c = wp[i + 1];
    const radial = (p, q) => Math.abs(p[0] - q[0]) < 1e-12;
    if ((radial(a, b) && radial(b, c)) || (Math.abs(a[1] - b[1]) < 1e-9 && Math.abs(b[1] - c[1]) < 1e-9)) wp.splice(i, 1);
    else i += 1;
  }
  const at = ([s, r]) => polar(shareAngle(s), r);
  const segLen = (p, q) => (Math.abs(p[0] - q[0]) < 1e-12 ? Math.abs(q[1] - p[1]) : Math.abs(q[0] - p[0]) * SPAN * p[1]);
  // A point `d` layout units along the move p->q.
  const along = (p, q, d) => {
    const L = segLen(p, q) || 1;
    const t = Math.min(1, d / L);
    return [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t];
  };
  const out = [];
  const sample = (p, q) => {
    const L = segLen(p, q);
    const n = Math.abs(p[0] - q[0]) < 1e-12 ? 1 : Math.max(1, Math.ceil(L / step));
    for (let i = out.length ? 1 : 0; i <= n; i += 1) out.push(at([p[0] + (q[0] - p[0]) * (i / n), p[1] + (q[1] - p[1]) * (i / n)]));
  };
  let cur = wp[0];
  for (let i = 1; i < wp.length; i += 1) {
    const p = wp[i - 1], q = wp[i], nxt = wp[i + 1];
    if (!nxt) { sample(cur, q); break; }
    const f = Math.min(fillet, segLen(p, q) * 0.45, segLen(q, nxt) * 0.45);
    const inP = along(q, p, f), outP = along(q, nxt, f);
    sample(cur, inP);
    const A = at(inP), C = at(q), B = at(outP);
    for (let t = 1; t <= 6; t += 1) {
      const u = t / 6;
      out.push([(1 - u) * (1 - u) * A[0] + 2 * u * (1 - u) * C[0] + u * u * B[0], (1 - u) * (1 - u) * A[1] + 2 * u * (1 - u) * C[1] + u * u * B[1]]);
    }
    cur = outP;
  }
  if (wp.length === 1) out.push(at(wp[0]));
  return out;
}

function segmentsCross(a, b, c, d) {
  const o = (p, q, r) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);
  const d1 = o(c, d, a), d2 = o(c, d, b), d3 = o(a, b, c), d4 = o(a, b, d);
  return ((d1 > 0 && d2 < 0) || (d1 < 0 && d2 > 0)) && ((d3 > 0 && d4 < 0) || (d3 < 0 && d4 > 0));
}
/** True when any two of the polylines cross. */
export function anyCrossing(lines) {
  const boxes = lines.map((pts) => {
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (const [x, y] of pts) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    return [x0, x1, y0, y1];
  });
  for (let i = 0; i < lines.length; i += 1) {
    for (let j = i + 1; j < lines.length; j += 1) {
      const A = boxes[i], B = boxes[j];
      if (A[1] < B[0] || B[1] < A[0] || A[3] < B[2] || B[3] < A[2]) continue;
      const P = lines[i], Q = lines[j];
      for (let a = 1; a < P.length; a += 1) {
        const ax0 = Math.min(P[a - 1][0], P[a][0]), ax1 = Math.max(P[a - 1][0], P[a][0]);
        const ay0 = Math.min(P[a - 1][1], P[a][1]), ay1 = Math.max(P[a - 1][1], P[a][1]);
        if (ax1 < B[0] || ax0 > B[1] || ay1 < B[2] || ay0 > B[3]) continue;
        for (let b = 1; b < Q.length; b += 1) {
          if (Math.max(Q[b - 1][0], Q[b][0]) < ax0 || Math.min(Q[b - 1][0], Q[b][0]) > ax1) continue;
          if (Math.max(Q[b - 1][1], Q[b][1]) < ay0 || Math.min(Q[b - 1][1], Q[b][1]) > ay1) continue;
          if (segmentsCross(P[a - 1], P[a], Q[b - 1], Q[b])) return true;
        }
      }
    }
  }
  return false;
}

function haloLayout(model, angleOf) {
  const rules = model.rules;
  const axioms = rules.filter((r) => r.kind === 'axiom');
  const shareOf = (id) => angleShare(angleOf.get(id));
  const meanShare = (ids) => {
    const s = ids.filter((id) => angleOf.has(id)).map(shareOf);
    return s.length ? s.reduce((a, b) => a + b, 0) / s.length : null;
  };
  // A rule tied to several axioms wants them side by side; its citers pull lightly.
  const groups = rules.map((r) => (r.kind === 'principle' ? r.restsOn : r.kind === 'anti_principle' ? r.threatens : [])).filter((g) => g.length > 1);
  const pref = new Map();
  for (const a of axioms) { const m = meanShare(a.citedBy); if (m !== null) pref.set(a.id, m); }
  const order = axiomOrder(axioms.map((a) => a.id), groups, pref);
  // Each axiom takes room for the rules it holds, so a crowded hub has space.
  const load = new Map(order.map((id) => [id, 0]));
  for (const r of rules) for (const id of [...r.restsOn, ...r.threatens]) if (load.has(id)) load.set(id, load.get(id) + 1 / Math.max(1, r.restsOn.length + r.threatens.length));
  const weights = order.map((id) => 2.2 + load.get(id));
  const total = weights.reduce((a, b) => a + b, 0);
  const share = new Map();
  let acc = 0;
  order.forEach((id, i) => { share.set(id, (acc + weights[i] / 2) / total); acc += weights[i]; });

  const place = new Map();
  for (const id of order) place.set(id, { id, kind: 'axiom', share: share.get(id), r: R.axioms });
  for (const kind of ['principle', 'anti_principle']) {
    const members = rules.filter((r) => r.kind === kind);
    const radius = R[ORBIT_OF[kind]];
    const targets = members.map((r) => {
      const hubs = (kind === 'principle' ? r.restsOn : r.threatens).filter((id) => share.has(id));
      if (hubs.length) return hubs.reduce((a, id) => a + share.get(id), 0) / hubs.length;
      return meanShare(r.citedBy) ?? 0.5;
    });
    const gap = HALO_GAP / (radius * (TURN - KEY_GAP));
    spreadLine(targets, gap).forEach((s, i) => place.set(members[i].id, { id: members[i].id, kind, share: s, r: radius }));
  }
  const marks = rules.map((r) => {
    const p = place.get(r.id);
    const angle = shareAngle(p.share);
    const [x, y] = polar(angle, p.r);
    return { id: r.id, kind: r.kind, share: p.share, angle, r: p.r, x, y };
  });
  const markOf = new Map(marks.map((m) => [m.id, m]));

  // Each rule's lines to its axioms run as one comb: a stem out of the rule,
  // a lane round to its farthest axiom on either side, and a drop into each.
  // Lanes are dealt shortest first, nearest the rule's own orbit.
  const combs = [];
  for (const kind of ['principle', 'anti_principle']) {
    const inner = kind === 'principle';
    const lo = inner ? R.principles + LANE_PAD : R.axioms + LANE_PAD;
    const hi = inner ? R.axioms - LANE_PAD : R.failures - LANE_PAD;
    const rows = rules.filter((r) => r.kind === kind).map((r) => {
      const m = markOf.get(r.id);
      const hubs = (inner ? r.restsOn : r.threatens).map((id) => markOf.get(id)).filter(Boolean);
      const angles = [m.angle, ...hubs.map((h) => h.angle)];
      return { rule: r.id, kind, m, hubs, a0: Math.min(...angles), a1: Math.max(...angles) };
    }).filter((c) => c.hubs.length);
    const lanes = [];
    for (const c of [...rows].sort((p, q) => (p.a1 - p.a0) - (q.a1 - q.a0) || p.a0 - q.a0)) {
      const margin = 9 / R.axioms;
      let lane = lanes.findIndex((used) => used.every(([u0, u1]) => c.a1 + margin < u0 || c.a0 - margin > u1));
      if (lane < 0) { lane = lanes.length; lanes.push([]); }
      lanes[lane].push([c.a0, c.a1]);
      c.lane = lane;
    }
    const pitch = Math.min(4.2, (hi - lo) / Math.max(1, lanes.length));
    for (const c of rows) {
      const lr = inner ? lo + (c.lane + 0.5) * pitch : hi - (c.lane + 0.5) * pitch;
      const edge = inner ? 1 : -1;
      const parts = [];
      // A rule standing straight over its one axiom needs no lane.
      if (c.hubs.length === 1 && Math.abs(c.hubs[0].angle - c.m.angle) * lr < 2.5) {
        parts.push(radial(c.m.angle, c.m.r + edge * 6, c.hubs[0].r - edge * 8));
      } else {
        parts.push(radial(c.m.angle, c.m.r + edge * 6, lr));
        if (c.a1 > c.a0) parts.push(arcPts(c.a0, c.a1, lr));
        for (const hub of c.hubs) parts.push(radial(hub.angle, lr, hub.r - edge * 8));
      }
      combs.push({ rule: c.rule, kind, axioms: c.hubs.map((h) => h.id), lane: c.lane, laneR: lr, parts, joints: c.hubs.map((h) => polar(h.angle, lr)) });
    }
  }

  // Each citation, between a component on the ring and a rule on the halo.
  const citations = [];
  for (const r of rules) for (const id of r.citedBy) if (angleOf.has(id)) citations.push({ comp: id, rule: r.id });
  return { marks, combs, citations, order, orbits: { principle: R.principles, axiom: R.axioms, anti_principle: R.failures } };
}
