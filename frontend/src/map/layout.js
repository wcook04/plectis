// Where everything on the evidence map stands, in layout units.
//
// Inside the ring the picture follows the paper's chain
// (paper/plectis-public-system.tex, figure "chain"), from the centre outward.
// The replay-admission core stands at the centre: every component's replay
// route runs to it as a hairline spoke. The three other workflow cores
// (repair, compatibility, views) stand round it. The twelve component kernels
// stand on an inner ring, each a specification with one petal for every
// verified task; a thread leaves each kernel, passes its generated code and
// its caller, and reaches its component. The 88 components stand in their
// family sectors, as on the system map.
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
  kernel: 258,
  petal: 21,
  generated: 292,
  caller: 326,
  component: 360,
  track0: 374,
  trackH: 10,
  trackGap: 2.6,
  labels: 0,
};
R.trackOuter = R.track0 + TRACKS.length * (R.trackH + R.trackGap) - R.trackGap;
R.scale = R.trackOuter + 4;
R.labels = R.scale + 22;

/** Inner and outer radius of a coverage ring. */
export function trackBand(i) {
  const r0 = R.track0 + i * (R.trackH + R.trackGap);
  return [r0, r0 + R.trackH];
}

const SLOT_PAD = 1.1;
const SECTOR_GAP = 0.05;
export const KEY_GAP = 0.24;
const KERNEL_SPACING = 100;
const EVEN_PULL = 0.5;
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

/**
 * Kernels stand at their component's angle, pushed apart round the ring until
 * no two flowers touch, then drawn back toward their components.
 */
export function spreadKernels(targets, radius = R.kernel, spacing = KERNEL_SPACING) {
  const n = targets.length;
  if (!n) return [];
  const order = targets.map((t, i) => [t, i]).sort((a, b) => a[0] - b[0]);
  // Drawn part way toward an even spacing in the same order, so a family
  // with several kernels does not crowd one side of the ring.
  const step = TURN / n;
  let offset = 0;
  for (let i = 0; i < n; i += 1) offset += shortArc(i * step, order[i][0]);
  offset /= n;
  const angles = order.map(([t], i) => t + shortArc(t, offset + i * step) * EVEN_PULL);
  const need = Math.min(spacing / radius, (TURN / n) * 0.96);
  for (let pass = 0; pass < 400; pass += 1) {
    for (let i = 0; i < n && n > 1; i += 1) {
      const j = (i + 1) % n;
      const gap = j === 0 ? angles[0] + TURN - angles[i] : angles[j] - angles[i];
      if (gap < need) {
        const push = (need - gap) / 2;
        angles[i] -= push;
        angles[j] += push;
      }
    }
    for (let i = 0; i < n; i += 1) angles[i] += shortArc(angles[i], order[i][0]) * 0.02;
  }
  const out = new Array(n);
  order.forEach(([, original], k) => { out[original] = angles[k]; });
  return out;
}

/** A thread's angle at a radius: it leaves the kernel straight and bends to its component. */
export function threadAngle(from, to, r) {
  const t = Math.max(0, Math.min(1, (r - R.kernel) / (R.component - R.kernel)));
  const s = t * t * (3 - 2 * t);
  return from + shortArc(from, to) * s;
}

export const polar = (angle, r) => [Math.cos(angle) * r, Math.sin(angle) * r];

// The workflow cores round the replay-admission core: either side and below,
// so each can name itself on its outer side.
const CORE_ANGLES = { repair: Math.PI, compatibility: 0, views: Math.PI / 2 };

/** The whole layout for a model from data.js. */
export function layout(model) {
  const { sectors, angleOf, pitch } = arrange(model.components);
  const comps = model.components.map((c) => {
    const angle = angleOf.get(c.id);
    const [x, y] = polar(angle, R.component);
    return { id: c.id, angle, x, y };
  });
  const linked = model.kernels.filter((k) => k.componentId && angleOf.has(k.componentId));
  const spread = spreadKernels(linked.map((k) => angleOf.get(k.componentId)));
  const kernels = linked.map((k, i) => {
    const angle = spread[i];
    const [x, y] = polar(angle, R.kernel);
    const to = angleOf.get(k.componentId);
    const [gx, gy] = polar(threadAngle(angle, to, R.generated), R.generated);
    const [cx, cy] = polar(threadAngle(angle, to, R.caller), R.caller);
    return { id: k.id, componentId: k.componentId, angle, x, y, generated: [gx, gy], caller: [cx, cy], to };
  });
  // Unlinked kernels (none today) wait on a small arc under the cores.
  model.kernels.filter((k) => !linked.includes(k)).forEach((k, i) => {
    const angle = Math.PI / 2 + (i - 0.5) * 0.3;
    const [x, y] = polar(angle, R.kernel);
    kernels.push({ id: k.id, componentId: null, angle, x, y, generated: null, caller: null, to: null });
  });
  const others = model.cores.filter((c) => c.id !== 'replay_admission');
  const cores = model.cores.map((c) => {
    if (c.id === 'replay_admission') return { id: c.id, x: 0, y: 0, angle: 0 };
    const angle = CORE_ANGLES[c.id] ?? (-Math.PI / 2 + (others.indexOf(c) / Math.max(1, others.length)) * TURN);
    const [x, y] = polar(angle, R.cores);
    return { id: c.id, x, y, angle };
  });
  return { sectors, pitch, comps, kernels, cores, radius: R.labels + 44 };
}
