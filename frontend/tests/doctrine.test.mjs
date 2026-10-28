// The doctrine joined to the components, its halo, and the words for every
// state it can be in, from a controlled overview.
import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from '../src/data.js';
import { DOCTRINE_KINDS, obligationWords, ruleKindWords, supportWords } from '../src/evidence.js';
import { angleShare, anyCrossing, axiomOrder, KEY_GAP, layout, planRoutes, R, shareAngle, spreadLine } from '../src/map/layout.js';
import { preview, readout, relation } from '../src/views/readout.js';

const component = (id, family, extra = {}) => ({
  organ_id: id, title: `${id} title`, summary: '', claim_id: `claim::${id}`,
  classification: { family, evidence_class: 'semantic_validator', truth_accounting_bucket: 'x' },
  formal_subclaim_ids: [], proof_ids: [], receipt_refs: [], wires_to: [], doctrine_ref_ids: [], route_ids: [], ...extra,
});
const obligation = (id, computed, declared = 'pending_cover_evaluator') => ({ obligation_id: id, predicate: `${id} holds`, required: true, declared_status: declared, computed_status: computed });
const overview = () => ({
  components: [
    component('a', 'formal_math_and_proof', { doctrine_ref_ids: ['AX-1', 'P-1', 'P-2', 'concept.x', 'paper_modules/a.md'] }),
    component('b', 'formal_math_and_proof', { doctrine_ref_ids: ['P-2'] }),
    component('c', 'entry_and_reveal'),
  ],
  kernels: [], cores: [], coverage: { component_presence: {} },
  explorer: {
    doctrine: {
      schema_version: 'plectis_explorer_doctrine_v2',
      nodes: [
        { id: 'AX-1', kind: 'axiom', title: 'Derivation before assertion', plain: 'plain', source_ref: 'AXIOMS.md::AX-1', statement: '## AX-1 Derivation before assertion\n\nBody.', axiom: {
          formal_clause: 'phi', lineage: ['x'], anti_axiom: 'asserted_label_is_truth',
          routing: { basis: 'authored_routing_registry', witness_strength: 'strong', witness_component_ids: ['a', 'c', 'ghost'] },
          obligations: [obligation('AX-1.O1', 'resolved_strength_uncomputable'), obligation('AX-1.O2', 'layer_debt', 'layer_debt'), obligation('AX-1.O3', 'blocked_binding_unresolved')],
          support: { basis: 'index_time_computed', verdict: 'partial_capped_by_layer_debt', hand_stamped_witness_strength: 'strong', hand_stamped_strong_not_certifiable: true, strong_blocked_reasons: [] },
        } },
        { id: 'AX-5', kind: 'axiom', title: 'Fail-closed monotone lattice' },
        { id: 'P-1', kind: 'principle', title: 'Recompute, do not echo' },
        { id: 'P-2', kind: 'principle', title: 'Lower claim strength to checker strength' },
        { id: 'AP-1', kind: 'anti_principle', title: 'Fixture-label echo' },
        { id: 'X-1', kind: 'mystery', title: 'Not a rule' },
      ],
      edges: [
        { from_id: 'P-1', to_id: 'AX-1', kind: 'rests_on' }, { from_id: 'P-2', to_id: 'AX-1', kind: 'rests_on' }, { from_id: 'P-2', to_id: 'AX-5', kind: 'rests_on' },
        { from_id: 'AP-1', to_id: 'AX-1', kind: 'violates' }, { from_id: 'AP-1', to_id: 'AX-5', kind: 'violates' },
        { from_id: 'P-1', to_id: 'P-2', kind: 'rests_on' },
      ],
    },
  },
});
const comp = (m, id) => ({ type: 'component', key: `comp:${id}`, comp: m.byId.get(id) });
const rule = (m, id) => ({ type: 'rule', key: `rule:${id}`, rule: m.ruleById.get(id) });

test('the doctrine joins its rules to each other and to the components that cite them', () => {
  const m = build(overview(), 'rev');
  assert.deepEqual(m.rules.map((r) => r.id), ['P-1', 'P-2', 'AX-1', 'AX-5', 'AP-1'], 'principles, axioms, failure modes; an unknown kind is left out');
  const r = (id) => m.ruleById.get(id);
  assert.deepEqual(r('P-2').restsOn, ['AX-1', 'AX-5']);
  assert.deepEqual(r('P-1').restsOn, ['AX-1'], 'a principle rests on axioms only');
  assert.deepEqual(r('AX-1').principles, ['P-1', 'P-2']);
  assert.deepEqual(r('AX-1').failures, ['AP-1']);
  assert.deepEqual(r('AP-1').threatens, ['AX-1', 'AX-5']);
  assert.deepEqual(m.byId.get('a').ruleIds, ['AX-1', 'P-1', 'P-2'], 'concepts and paper modules are not rules');
  assert.deepEqual(r('P-2').citedBy, ['a', 'b']);
  assert.deepEqual(r('AX-1').witnesses, ['a', 'c'], 'a witness that is not a component is dropped');
  assert.equal(r('AX-1').statement, 'Body.', 'the card names the rule, so its heading is dropped');
  assert.equal(r('AX-1').support.verdict, 'partial_capped_by_layer_debt');
  assert.equal(r('AX-5').support, null, 'no verdict is recorded for it, so none is invented');
  assert.deepEqual([m.totals.rules, m.totals.axioms, m.totals.principles, m.totals.failures, m.totals.citations], [5, 2, 2, 1, 4]);
  const old = overview();
  delete old.explorer.doctrine;
  const bare = build(old, 'rev');
  assert.equal(bare.rules.length, 0);
  assert.equal(layout(bare).halo, null, 'an index without doctrine draws no halo');
});

test('the halo keeps its orbits, leaves the key wedge open and ties each rule to its axioms', () => {
  const m = build(overview(), 'rev');
  const L = layout(m);
  const orbit = { principle: R.principles, axiom: R.axioms, anti_principle: R.failures };
  for (const mark of L.halo.marks) {
    assert.equal(mark.r, orbit[mark.kind]);
    const s = angleShare(mark.angle);
    assert.ok(s > 0 && s < 1, `${mark.id} stands outside the key wedge`);
  }
  for (const kind of DOCTRINE_KINDS) {
    const on = L.halo.marks.filter((x) => x.kind === kind).sort((p, q) => p.angle - q.angle);
    for (let i = 1; i < on.length; i += 1) assert.ok((on[i].angle - on[i - 1].angle) * on[i].r >= 29.9, `${kind} marks keep apart`);
  }
  const comb = (id) => L.halo.combs.find((c) => c.rule === id);
  assert.deepEqual(comb('P-2').axioms, ['AX-1', 'AX-5']);
  assert.deepEqual(comb('AP-1').axioms, ['AX-1', 'AX-5']);
  for (const c of L.halo.combs) {
    if (c.kind === 'principle') assert.ok(c.laneR > R.principles && c.laneR < R.axioms, 'a principle’s lane runs between its orbit and the axioms');
    else assert.ok(c.laneR > R.axioms && c.laneR < R.failures, 'a failure mode’s lane runs between the axioms and its orbit');
  }
  assert.equal(L.halo.citations.length, 4);
  assert.deepEqual(layout(m).halo.marks, L.halo.marks, 'the same snapshot draws the same halo');
  const p2 = L.halo.marks.find((x) => x.id === 'P-2');
  const plan = planRoutes({ hub: { s: p2.share, r: R.principles - 6, kind: 'glyph' }, k: 1,
    leaves: ['a', 'b'].map((id) => ({ id, s: angleShare(L.comps.find((c) => c.id === id).angle), r: R.cap1 })),
    band: { lo: R.cap1 + 40, hi: R.principles - 8 }, colShare: L.pitch / (2 * Math.PI - KEY_GAP) });
  assert.ok(plan.fits, 'two citations fit');
  assert.deepEqual(plan.routes.map((r) => r.id).sort(), ['a', 'b'], 'one route per citer, and only citers');
  const order = axiomOrder(['A', 'B', 'C', 'D'], [['A', 'D']]);
  assert.equal(Math.abs(order.indexOf('A') - order.indexOf('D')), 1, 'axioms tied by one rule stand side by side');
  const spread = spreadLine([0.5, 0.5, 0.5], 0.1).sort((x, y) => x - y);
  assert.ok(spread[1] - spread[0] >= 0.1 - 1e-6 && spread[2] - spread[1] >= 0.1 - 1e-6);
});

test('every doctrine state has its own words, and none of them is worded as a pass', () => {
  const verdicts = ['bound_resolved_strength_uncomputable', 'partial_capped_by_layer_debt', 'blocked', 'blocked_conflict_detected', 'unknown'];
  const seen = new Set();
  for (const v of verdicts) {
    const [sentence, , short, known] = supportWords(v);
    assert.equal(known, true, v);
    assert.doesNotMatch(short, /\bpass(es|ed)?\b/i, v);
    assert.doesNotMatch(sentence, /\b(passes|passed|verified|proved)\b/i, v);
    seen.add(short);
  }
  assert.equal(seen.size, 4, 'each verdict reads differently, the two blocked ones alike');
  assert.equal(supportWords('certified_strong')[3], false);
  assert.match(supportWords('certified_strong')[0], /Unrecognised/);
  assert.equal(supportWords(null)[2], 'Not recorded');
  assert.deepEqual(['resolved_strength_uncomputable', 'layer_debt', 'blocked_binding_unresolved', 'pending'].map((s) => obligationWords(s)[1]), ['stated', 'debt', 'blocked', 'unknown']);
  assert.match(obligationWords('pending')[0], /Unrecognised/);
  assert.deepEqual(DOCTRINE_KINDS.map((k) => ruleKindWords(k)), ['Principle', 'Axiom', 'Failure mode']);
  assert.deepEqual(DOCTRINE_KINDS.map((k) => ruleKindWords(k, { glyph: true })), ['principle', 'axiom', 'failure']);
});

test('the readout names each lit thing and its limit, and a pointed object is said against the chosen one', () => {
  const m = build(overview(), 'rev');
  const marks = (o) => readout(m, o).lines.map((l) => l.mark);
  const text = (o) => readout(m, o).lines.map((l) => `${l.mark}: ${l.text}`).join('\n');
  assert.ok(marks(comp(m, 'a')).includes('Lines up to the halo'));
  assert.match(text(comp(m, 'a')), /3 rules its record lists: 1 axiom \(basic assumption\) and 2 principles \(working rules\)/);
  assert.match(text(comp(m, 'a')), /Fainter: AX-5/, 'an axiom its principles rest on, which it does not cite');
  assert.match(text(comp(m, 'a')), /witness for AX-1/);
  assert.ok(marks(comp(m, 'c')).includes('Nothing on the halo'));
  assert.match(text(rule(m, 'P-2')), /Lit columns: the 2 of 3 components whose records cite it, each marked at its column\. The other 1 are dimmed/);
  assert.doesNotMatch(text(rule(m, 'P-2')), /round the edge|sweep/);
  assert.match(text(rule(m, 'P-2')), /Lines out: to AX-1, AX-5, the axioms \(basic assumptions\) it rests on/);
  const ax = text(rule(m, 'AX-1'));
  assert.match(ax, /Thicker lines: the 2 components its routing names by hand as computing part of it; dashed where that component does not list it \(1\)/);
  assert.match(ax, /3 checkable parts: 1 bound to witnesses that exist, 1 carrying declared layer debt, 1 blocked/);
  assert.match(ax, /Support checker: at build time: partial: layer debt/);
  assert.match(text(rule(m, 'AP-1')), /No lit columns: components list axioms and principles, never failure modes/);
  for (const o of [comp(m, 'a'), comp(m, 'b'), comp(m, 'c'), ...m.rules.map((r) => rule(m, r.id))]) {
    const r = readout(m, o);
    assert.ok(r.lines.length && r.lines.every((l) => l.mark && l.text), o.key);
    assert.ok(r.limit && r.limit.length > 20, `${o.key} states its limit`);
  }
  assert.equal(relation(m, comp(m, 'b'), rule(m, 'P-1')), 'Its record does not cite P-1.');
  assert.equal(relation(m, rule(m, 'P-2'), comp(m, 'a')), 'The chosen component’s record cites P-2.');
  assert.match(relation(m, rule(m, 'AX-1'), comp(m, 'a')), /cites AX-1\. The routing registry also names it as a witness\./);
  assert.match(relation(m, comp(m, 'a'), rule(m, 'AP-1')), /cannot cite AP-1/);
  assert.equal(relation(m, rule(m, 'P-2'), rule(m, 'AX-5')), 'P-2 rests on AX-5.');
  assert.match(relation(m, comp(m, 'a'), comp(m, 'b')), /cite 1 rule|both cite 1 rule/);
  assert.equal(relation(m, comp(m, 'a'), comp(m, 'a')), null);
  // Two rules with no direct tie: the shared citers, and that sharing is not a link.
  const shared = m.rules.filter((r) => r.kind !== 'anti_principle');
  for (const a of shared) for (const b of shared) {
    if (a === b || a.restsOn.includes(b.id) || b.restsOn.includes(a.id)) continue;
    const n = a.citedBy.filter((id) => b.citedBy.includes(id)).length;
    assert.equal(relation(m, rule(m, a.id), rule(m, b.id)), n ? `${n} component${n === 1 ? '' : 's'} ${n === 1 ? 'cites' : 'cite'} both ${a.id} and ${b.id}. Shared citations do not link the rules.` : `No component cites both ${a.id} and ${b.id}.`);
  }
  assert.match(relation(m, rule(m, 'P-1'), rule(m, 'P-2'), { relation: { kind: 'shared', count: 7 } }) || '', /^(7 components cite both|P-\d (rests on|threatens))/);
  // The dock reads identity, relation, purpose, counts and limit in that order.
  const p = preview(m, comp(m, 'b'), rule(m, 'P-1'));
  assert.equal(p.relation, 'Its record does not cite P-1.');
  assert.ok(p.kind.startsWith('Component') && p.name && p.counts.length && p.limit);
  assert.doesNotMatch(p.counts.join(' '), /\b\d+ of \d+ (kinds|rings)\b/, 'no progress fractions');
  const rp = preview(m, rule(m, 'P-2'), null);
  assert.equal(rp.relation, null);
  assert.match(rp.counts[0], /^2 of 3 components cite it$/);
  assert.equal(preview(m, null), null);
});

// The route planner (layout.js planRoutes), shared with the painter.
const SPAN = 2 * Math.PI - KEY_GAP;
const rad = ([x, y]) => Math.hypot(x, y);
const shareAt = (p) => angleShare(Math.atan2(p[1], p[0]));
const fan = (n, { k = 1, hubS = 0.5, spread = 0.3, blocked = [], kind = 'cap' } = {}) => {
  const leaves = Array.from({ length: n }, (_, i) => ({ id: `t${i}`, s: hubS + ((i + 0.5) / n - 0.5) * 2 * spread, r: kind === 'cap' ? R.principles - 6 : R.cap1 + 1 }));
  return planRoutes({ hub: { s: hubS, r: kind === 'cap' ? R.cap1 + 1 : R.principles - 6, kind }, leaves, k,
    band: { lo: R.cap1 + 45, hi: R.principles - 8 }, corridor: { lo: R.cap1 + 2, hi: R.cap1 + 8 }, blocked, colShare: 0.06 / SPAN });
};
const lanesOf = (plan, side) => plan.routes.filter((r) => r.side === side).sort((p, q) => p.lane - q.lane);
const laneR = (r) => r.waypoints[r.waypoints.length - 2][1];

test('a fan of routes is nested: no two cross, the nearer target takes the lane nearest the orbit', () => {
  for (const kind of ['cap', 'glyph']) {
    const plan = fan(12, { kind, k: 1 });
    assert.ok(plan.fits, `${kind}: twelve routes fit a 70 px band`);
    assert.equal(anyCrossing(plan.routes.map((r) => r.pts)), false, `${kind}: no crossings`);
    for (const side of ['cw', 'ccw']) {
      const rs = lanesOf(plan, side);
      const dist = (r) => Math.abs(r.waypoints[r.waypoints.length - 1][0] - 0.5);
      for (let i = 1; i < rs.length; i += 1) {
        assert.ok(dist(rs[i]) >= dist(rs[i - 1]), `${kind}: lanes are dealt nearest first`);
        const h0 = kind === 'cap' ? laneR(rs[i - 1]) : rs[i - 1].waypoints[1][1];
        const h1 = kind === 'cap' ? laneR(rs[i]) : rs[i].waypoints[1][1];
        if (kind === 'cap') assert.ok(h0 - h1 >= 3 - 1e-9, 'from a cap, a nearer target takes a higher lane, at least 3 px apart');
        else assert.ok(h1 - h0 >= 3 - 1e-9, 'from a rule, a nearer target takes a lower lane, at least 3 px apart');
      }
    }
    for (const r of plan.routes) {
      const first = r.pts[0], last = r.pts[r.pts.length - 1];
      assert.ok(Math.abs(rad(first) - (kind === 'cap' ? R.cap1 + 1 : R.principles - 6)) < 1e-6, 'it leaves the hub');
      const leaf = r.waypoints[r.waypoints.length - 1];
      assert.ok(Math.abs(rad(last) - leaf[1]) < 1e-6 && Math.abs(shareAt(last) - leaf[0]) < 1e-9, 'it lands on its own leaf');
      for (const p of r.pts) { const s = shareAt(p); assert.ok(s > 0 && s < 1, 'a fan inside the ring stays clear of the key wedge'); }
      // Filleted: no sharp corner anywhere along it.
      for (let i = 2; i < r.pts.length; i += 1) {
        const a = Math.atan2(r.pts[i - 1][1] - r.pts[i - 2][1], r.pts[i - 1][0] - r.pts[i - 2][0]);
        const b = Math.atan2(r.pts[i][1] - r.pts[i - 1][1], r.pts[i][0] - r.pts[i - 1][0]);
        let d = Math.abs(b - a); if (d > Math.PI) d = 2 * Math.PI - d;
        assert.ok(d < 0.6, 'corners are rounded');
      }
    }
  }
});

test('capacity is per side at the current zoom, and an overfull set says so instead of dropping routes', () => {
  const wide = fan(40, { kind: 'glyph', k: 1 });
  assert.equal(wide.fits, false);
  assert.equal(wide.reason, 'lanes');
  assert.equal(wide.routes.length, 40, 'every route is still planned, for trace-on-preview');
  assert.ok(wide.sides.cw.need > wide.sides.cw.slots);
  const zoomed = fan(40, { kind: 'glyph', k: 2.5 });
  assert.ok(zoomed.sides.cw.slots > wide.sides.cw.slots, 'zooming in adds lanes');
  const one = fan(1, { kind: 'glyph', k: 0.4 });
  assert.ok(one.fits, 'a single traced route fits even far out');
});

test('a route to a cap under a family label enters along the corridor, never through the label', () => {
  const label = [0.43, 0.47];
  const leaves = [{ id: 'under', s: 0.45, r: R.cap1 + 1 }, { id: 'clear', s: 0.4, r: R.cap1 + 1 }];
  const plan = planRoutes({ hub: { s: 0.3, r: R.principles - 6, kind: 'glyph' }, leaves, k: 1,
    band: { lo: R.cap1 + 45, hi: R.principles - 8 }, corridor: { lo: R.cap1 + 2, hi: R.cap1 + 8 }, blocked: [label], colShare: 0.06 / SPAN });
  assert.ok(plan.fits);
  for (const r of plan.routes) {
    for (const p of r.pts) {
      const s = shareAt(p), radius = rad(p);
      assert.ok(!(s > label[0] && s < label[1] && radius > R.cap1 + 9 && radius < R.cap1 + 44), `${r.id} stays out of the label box`);
    }
  }
  const under = plan.routes.find((r) => r.id === 'under');
  assert.ok(under.pts.some((p) => Math.abs(rad(p) - (R.cap1 + 2)) < 0.5 && shareAt(p) > label[0]), 'it runs the corridor above the caps');
  const fromUnder = planRoutes({ hub: { s: 0.45, r: R.cap1 + 1, kind: 'cap' }, leaves: [{ id: 'x', s: 0.6, r: R.principles - 6 }, { id: 'y', s: 0.3, r: R.principles - 6 }], k: 1,
    band: { lo: R.cap1 + 45, hi: R.principles - 8 }, corridor: { lo: R.cap1 + 2, hi: R.cap1 + 8 }, blocked: [label], colShare: 0.06 / SPAN });
  assert.ok(fromUnder.fits);
  for (const r of fromUnder.routes) for (const p of r.pts) {
    assert.ok(!(shareAt(p) > label[0] && shareAt(p) < label[1] && rad(p) > R.cap1 + 9 && rad(p) < R.cap1 + 44), 'a fan from under a label leaves round it');
  }
  // A leaf more than half a turn away is reached the short way round.
  const across = planRoutes({ hub: { s: 0.03, r: R.cap1 + 1, kind: 'cap' }, leaves: [{ id: 'far', s: 0.97, r: R.principles - 6 }], k: 1,
    band: { lo: R.cap1 + 45, hi: R.principles - 8 }, colShare: 0.06 / SPAN });
  const swept = across.routes[0].pts.reduce((m, p, i, a) => (i ? m + Math.abs(Math.atan2(a[i - 1][0] * p[1] - a[i - 1][1] * p[0], a[i - 1][0] * p[0] + a[i - 1][1] * p[1])) : 0), 0);
  assert.ok(swept < Math.PI / 2, 'across the wedge, not three quarters of the way round');
  assert.ok(Math.abs(shareAngle(0.25) - (-Math.PI / 2 + KEY_GAP / 2 + 0.25 * SPAN)) < 1e-12);
});
