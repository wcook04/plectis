// Where everything on the evidence map stands, in layout units.
//
// The picture follows the paper's chain (paper/plectis-public-system.tex,
// figure "chain"): a stated property is specified, verified and compiled,
// and an application caller runs the generated code and saves a record. On
// the map that chain runs from the centre outward. The core is the retained
// Dafny verification; the twelve kernels stand on an inner ring, each a
// specification with one dot for every verified task; a thread leaves each
// kernel, passes its generated code and its caller, and reaches its component
// on the outer ring. The 88 components stand in their seven family sectors,
// as on the system map, each with its saved records stacked outward. A
// component without a modeled contract has no thread: the gap toward the
// centre is the honest picture of formal coverage.
//
// Coordinates are deterministic, so the drawing is the same on every visit.

import { BACKING_ORDER, FAMILY_ORDER } from '../evidence.js';

export const R = {
  core: 0,
  kernel: 282,
  petal: 19,
  generated: 324,
  caller: 362,
  component: 400,
  record0: 416,
  recordStep: 6.6,
  scale: 478,
  labels: 502,
};
const SLOT_PAD = 1.1;
const SECTOR_GAP = 0.05;
const KERNEL_SPACING = 104;
const EVEN_PULL = 0.5;

/** Sector and slot order: families clockwise from the top, members by backing then title. */
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
  const pitch = (Math.PI * 2 - SECTOR_GAP * groups.length) / slots;
  let at = 0;
  const sectors = groups.map((g) => {
    const lo = at;
    const hi = lo + (g.members.length + SLOT_PAD) * pitch;
    at = hi + SECTOR_GAP;
    return { family: g.family, lo, hi, members: g.members.map((c) => c.id), count: g.members.length };
  });
  // Turn the ring so the first family's middle stands at the top.
  const turn = -Math.PI / 2 - (sectors[0].lo + sectors[0].hi) / 2;
  const angleOf = new Map();
  for (const s of sectors) {
    s.lo += turn; s.hi += turn;
    s.members.forEach((id, j) => angleOf.set(id, s.lo + (SLOT_PAD / 2 + j + 0.5) * pitch));
    s.mid = (s.lo + s.hi) / 2;
  }
  return { sectors, angleOf, pitch };
}

const TURN = Math.PI * 2;
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
  // Unlinked kernels (none today) wait on a small arc under the core.
  model.kernels.filter((k) => !linked.includes(k)).forEach((k, i) => {
    const angle = Math.PI / 2 + (i - 0.5) * 0.3;
    const [x, y] = polar(angle, R.kernel);
    kernels.push({ id: k.id, componentId: null, angle, x, y, generated: null, caller: null, to: null });
  });
  // The two satellites stand under the core, as Comparator and Palomar
  // stand under the universe map's core.
  const satellites = [
    { id: 'retained', x: -112, y: 72 },
    { id: 'fresh', x: 112, y: 72 },
  ];
  return { sectors, pitch, comps, kernels, satellites, radius: R.labels + 40 };
}
