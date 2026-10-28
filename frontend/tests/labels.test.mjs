// The label planner: obstacles, priority order, truncation and determinism.
import test from 'node:test';
import assert from 'node:assert/strict';
import { arcDiscs, collides, createPlanner, fitText, levelOfDetail, localPitch, LOD, PRIORITY, radialDiscs, rectShape } from '../src/map/labels.js';

const measure = (s) => s.length * 6;

test('level of detail follows the local pitch with a 10% hysteresis band', () => {
  assert.equal(levelOfDetail(10), LOD.atlas);
  assert.equal(levelOfDetail(18), LOD.neighbourhood);
  assert.equal(levelOfDetail(34), LOD.reading);
  // Rising from atlas, 18 is not yet enough; 18.9 is.
  assert.equal(levelOfDetail(18.5, LOD.atlas), LOD.atlas);
  assert.equal(levelOfDetail(19, LOD.atlas), LOD.neighbourhood);
  // Falling from neighbourhood, 17.5 holds; 17 drops.
  assert.equal(levelOfDetail(17.5, LOD.neighbourhood), LOD.neighbourhood);
  assert.equal(levelOfDetail(17, LOD.neighbourhood), LOD.atlas);
  // A big jump crosses both edges at once.
  assert.equal(levelOfDetail(60, LOD.atlas), LOD.reading);
  assert.equal(levelOfDetail(5, LOD.reading), LOD.atlas);
  assert.ok(Math.abs(localPitch(1, 0.06) - 21.6) < 1e-9);
});

test('primitive collisions: discs, rects, segments and annuli', () => {
  const disc = { t: 'c', x: 0, y: 0, r: 5 };
  assert.ok(collides(disc, { t: 'c', x: 9, y: 0, r: 5 }));
  assert.ok(!collides(disc, { t: 'c', x: 11, y: 0, r: 5 }));
  assert.ok(collides(disc, { t: 'c', x: 11, y: 0, r: 5 }, 2));
  assert.ok(collides(rectShape(0, 0, 10, 10), { t: 'r', x0: 12, y0: 0, x1: 20, y1: 10 }, 4));
  assert.ok(!collides(rectShape(0, 0, 10, 10), { t: 'r', x0: 12, y0: 0, x1: 20, y1: 10 }));
  const seg = { t: 's', ax: -20, ay: 7, bx: 20, by: 7 };
  assert.ok(!collides(disc, seg));
  assert.ok(collides(disc, seg, 3));
  assert.ok(collides(rectShape(-1, -1, 1, 1), { t: 's', ax: -5, ay: -5, bx: 5, by: 5 }), 'segment through a rect');
  const ring = { t: 'a', x: 0, y: 0, r0: 100, r1: 110 };
  assert.ok(collides({ t: 'c', x: 95, y: 0, r: 6 }, ring));
  assert.ok(!collides({ t: 'c', x: 80, y: 0, r: 6 }, ring));
  assert.ok(collides(rectShape(104, -2, 106, 2), ring));
  assert.ok(!collides(rectShape(-10, -10, 10, 10), ring));
});

test('footprints sample the baseline of radial and arc text', () => {
  const discs = radialDiscs(0, 0, 0, 100, 60, 10);
  assert.ok(discs.length >= 6);
  assert.equal(discs[0].x, 105);
  assert.ok(Math.abs(discs[discs.length - 1].x - 155) < 1e-9, 'last disc ends at the text end');
  const arc = arcDiscs(0, 0, 200, 0, 80, 10);
  for (const d of arc) assert.ok(Math.abs(Math.hypot(d.x, d.y) - 200) < 1e-9);
  assert.ok(Math.abs(arc.span - 0.4) < 1e-9);
});

test('fitText keeps whole text, cuts with an ellipsis, or refuses a stub', () => {
  assert.deepEqual(fitText('abcdef', 100, measure), { text: 'abcdef', width: 36, cut: false });
  const cut = fitText('Check a memory quarantine', 60, measure);
  assert.equal(cut.text, 'Check a m…');
  assert.ok(cut.width <= 60);
  assert.equal(fitText('Check a memory', 20, measure), null);
});

test('greedy placement honours priority then id, obstacles and the label gap', () => {
  const planner = createPlanner({ bounds: { x0: 0, y0: 0, x1: 400, y1: 300 } });
  planner.block({ kind: 'rect', x0: 300, y0: 0, x1: 400, y1: 40, pad: 4, tag: 'chrome' });
  const box = (id, priority, x0, y0, x1, y1, more = []) => ({ id, priority, anchors: [{ kind: 'rect', x0, y0, x1, y1 }, ...more] });
  const out = planner.plan([
    box('b-name', PRIORITY.componentName, 10, 10, 60, 22),
    box('a-name', PRIORITY.componentName, 20, 12, 70, 24, [{ kind: 'rect', x0: 20, y0: 40, x1: 70, y1: 52 }]),
    box('family', PRIORITY.family, 0, 8, 80, 24),
    box('chromed', PRIORITY.chosen, 310, 10, 360, 22),
    box('outside', PRIORITY.chosen, 390, 280, 420, 290),
  ]);
  assert.ok(out.has('family'), 'family (5) goes before names (9)');
  assert.equal(out.get('a-name').index, 1, 'a-name takes its second anchor');
  assert.ok(!out.has('b-name'), 'b-name has no free anchor and is omitted');
  const reasons = Object.fromEntries(planner.rejected.map((r) => [r.id, r.reason]));
  assert.equal(reasons['b-name'], 'label');
  assert.equal(reasons.chromed, 'chrome');
  assert.equal(reasons.outside, 'bounds');
  // The gap: a box 3 px from a placed label collides, 5 px does not.
  assert.equal(planner.test([rectShape(0, 27, 10, 30)]), 'label');
  assert.equal(planner.test([rectShape(0, 29, 10, 32)]), null);
});

test('a radial name is truncated before the first rule glyph and never crosses it', () => {
  const planner = createPlanner();
  // A glyph (with its obligation arcs) on the ray 140 px out.
  planner.block({ kind: 'circle', x: 140, y: 0, r: 12, pad: 3, tag: 'glyph' });
  const title = 'Check a memory quarantine and rollback record';
  const fit = (px) => fitText(title, px, measure);
  const p = planner.place({ id: 'comp:x', priority: PRIORITY.componentName, fit,
    anchors: [{ kind: 'radial', cx: 0, cy: 0, angle: 0, from: 40, length: 400, height: 11 }] });
  assert.ok(p, 'placed');
  assert.ok(p.fitted.cut, 'shortened with an ellipsis');
  assert.ok(p.fitted.text.endsWith('…'));
  assert.equal(p.stoppedBy, 'glyph');
  // Its footprint stays clear of the glyph.
  for (const d of p.shape) assert.ok(!collides(d, { t: 'c', x: 140, y: 0, r: 12 }, 3));
  assert.ok(40 + p.length <= 140 - 12 - 3 + 1e-9);
  // A ray that starts on the glyph has no room at all.
  const q = planner.place({ id: 'comp:y', priority: PRIORITY.componentName, fit,
    anchors: [{ kind: 'radial', cx: 0, cy: 0, angle: 0, from: 128, length: 300, height: 11 }] });
  assert.equal(q, null);
  assert.match(planner.rejected.at(-1).reason, /^short/);
});

test('polylines block like routes; ignore lets territory labels skip a tag', () => {
  const planner = createPlanner();
  planner.block({ kind: 'polyline', points: [[0, 50], [200, 50]], pad: 6, tag: 'route' });
  planner.block({ kind: 'circle', x: 0, y: 0, r: 30, tag: 'ring' });
  assert.equal(planner.test([rectShape(10, 40, 50, 46)]), 'route');
  assert.equal(planner.test([rectShape(10, 30, 50, 38)]), null);
  assert.equal(planner.test([rectShape(-5, -5, 5, 5)]), 'ring');
  const p = planner.place({ id: 'wedge', priority: PRIORITY.wedge, ignore: ['ring'], anchors: [{ kind: 'rect', x0: -5, y0: -5, x1: 5, y1: 5 }] });
  assert.ok(p);
});

test('plans are deterministic regardless of input order', () => {
  const make = () => Array.from({ length: 40 }, (_, i) => ({
    id: `c${String(i).padStart(2, '0')}`, priority: i % 3 ? PRIORITY.componentName : PRIORITY.ruleId,
    fit: (px) => fitText(`component number ${i} with a long name`, px, measure),
    anchors: [{ kind: 'radial', cx: 0, cy: 0, angle: (i / 40) * Math.PI * 2, from: 60, length: 220, height: 11 }],
  }));
  const run = (cands) => {
    const planner = createPlanner({ bounds: { x0: -300, y0: -300, x1: 300, y1: 300 } });
    planner.block({ kind: 'circle', x: 150, y: 20, r: 14, tag: 'glyph' });
    const out = planner.plan(cands);
    return [...out.values()].map((p) => `${p.id}:${p.fitted.text}`).sort().join('|');
  };
  const a = run(make());
  const b = run(make().reverse());
  assert.equal(a, b);
  assert.ok(a.length > 0);
});
