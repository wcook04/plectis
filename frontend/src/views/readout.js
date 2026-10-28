// What the map is showing, in words: for whatever the pointer is on or is
// chosen, one line for each kind of thing the drawing lights, naming its
// ink, where it comes from and how many, then the limit of what the lit
// lines establish. The panel adds wording, not facts (Lean Exposition
// panels/EdgePanel.tsx): every line here is a count or a relation the
// overview already carries, and each corresponds to something map/engine.js
// draws for the same focus (near, haloFocus).
//
// Adapted from the system map's captions and relation sentences
// (ai_workflow sites/microcosm/assets/system-map.js captionParts and
// relationText): one sentence per level, absence stated as a count rather
// than left silent, and a pointed object restated against the chosen one.

import { CITATION_WORDS, TRACKS, count, familyName, obligationWords, proofShortName, ruleKindWords, supportWords, CORE_NAMES, moduleWords } from '../evidence.js';

const list = (ids) => (ids.length <= 4 ? ids.join(', ') : `${ids.slice(0, 3).join(', ')} and ${ids.length - 3} more`);

/** { lines: [{ ink, text }], limit } for one map object (engine objectFor). */
export function readout(model, o) {
  if (!o) return null;
  if (o.type === 'component') return componentReadout(model, o.comp);
  if (o.type === 'rule') return ruleReadout(model, o.rule);
  if (o.type === 'kernel') return kernelReadout(model, o.kernel);
  if (o.type === 'core') return coreReadout(model, o.core);
  return null;
}

// Each line names what is seen first (`mark`), then what it means.
function componentReadout(model, c) {
  const lines = [];
  const kinds = TRACKS.filter((t) => t.ink !== 'unknown');
  const has = kinds.filter((t) => c.checks[t.id]).length;
  lines.push({ ink: 'column', mark: 'Outlined column', text: `${has} of its ${kinds.length} kinds of check are recorded${has < kinds.length ? `; ${kinds.length - has} are not` : ''}.` });
  if (c.kernelId) {
    const k = model.kernelById.get(c.kernelId);
    lines.push({ ink: 'red', mark: 'Red stem', text: `in to ${k ? proofShortName(k) : 'its proved computation'}, a computation proved in Dafny whose generated code it calls.` });
  }
  if (c.replayRoute) lines.push({ ink: 'stated', mark: 'Blue spoke', text: 'its rerun route to the replay checker. Nothing has been rerun here.' });
  const wired = model.wires.filter(([a, b]) => a === c.id || b === c.id).length;
  const imports = c.importsOut.length + c.importsIn.length;
  if (wired || imports) {
    lines.push({ ink: 'stated', mark: 'Blue curves', text: `${count(wired, 'declared connection')}${imports ? ` and ${count(imports, 'code import')}` : ''}, stated in source, not seen in a run.` });
  }
  const rules = (c.ruleIds || []).map((id) => model.ruleById.get(id)).filter(Boolean);
  if (rules.length) {
    const axioms = rules.filter((r) => r.kind === 'axiom');
    const principles = rules.filter((r) => r.kind === 'principle');
    lines.push({ ink: 'doctrine', mark: 'Lines up to the halo', text: `the ${count(rules.length, 'rule')} its record lists: ${count(axioms.length, 'axiom')} (basic ${axioms.length === 1 ? 'assumption' : 'assumptions'}) and ${count(principles.length, 'principle')} (working ${principles.length === 1 ? 'rule' : 'rules'}).` });
    const cited = new Set(rules.map((r) => r.id));
    const basis = [...new Set(principles.flatMap((r) => r.restsOn))].filter((id) => !cited.has(id));
    if (basis.length) lines.push({ ink: 'doctrine-soft', mark: 'Fainter', text: `${list(basis)}, ${basis.length === 1 ? 'an axiom' : 'axioms'} those principles rest on; its record does not list ${basis.length === 1 ? 'it' : 'them'} itself.` });
  } else if (model.rules.length) {
    lines.push({ ink: 'absent', mark: 'Nothing on the halo', text: 'its record lists no rule.' });
  }
  const witnessFor = model.rules.filter((r) => r.witnesses.includes(c.id)).map((r) => r.id);
  if (witnessFor.length) lines.push({ ink: 'doctrine', mark: 'Witness', text: `the routing registry names it, by hand, as a witness for ${list(witnessFor)}.` });
  return { lines, limit: 'None of these lines shows that its whole claim holds; that is unknown for every component.' };
}

function ruleReadout(model, r) {
  const lines = [];
  const total = model.totals.components;
  if (r.kind !== 'anti_principle') {
    const n = r.citedBy.length;
    lines.push(n
      ? { ink: 'doctrine', mark: 'Lit columns', text: `the ${n} of ${total} components whose records cite it, each marked at its column. The other ${total - n} are dimmed. ${n > 12 ? 'Point at one to trace its route.' : 'Each has its own route to the rule.'}` }
      : { ink: 'absent', mark: 'No lit columns', text: 'no component lists it.' });
  }
  if (r.kind === 'principle') {
    lines.push(r.restsOn.length
      ? { ink: 'doctrine', mark: 'Lines out', text: `to ${list(r.restsOn)}, the ${r.restsOn.length === 1 ? 'axiom' : 'axioms'} (basic ${r.restsOn.length === 1 ? 'assumption' : 'assumptions'}) it rests on.` }
      : { ink: 'absent', mark: 'No lines out', text: 'it rests on no recorded axiom.' });
  }
  if (r.kind === 'anti_principle') {
    lines.push({ ink: 'threat', mark: 'Dashed lines in', text: `to ${list(r.threatens)}, the ${r.threatens.length === 1 ? 'axiom' : 'axioms'} it would break.` });
    lines.push({ ink: 'absent', mark: 'No lit columns', text: 'components list axioms and principles, never failure modes.' });
  }
  if (r.kind === 'axiom') {
    if (r.witnesses.length) {
      const cites = new Set(r.citedBy);
      const uncited = r.witnesses.filter((id) => !cites.has(id)).length;
      lines.push({ ink: 'doctrine', mark: r.witnesses.length === 1 ? 'Thicker line' : 'Thicker lines', text: `${r.witnesses.length === 1 ? 'the component' : `the ${r.witnesses.length} components`} its routing names by hand as computing part of it${uncited ? `; dashed where that component does not list it (${uncited})` : ''}.` });
    }
    lines.push({ ink: 'doctrine', mark: 'Also lit', text: `${count(r.principles.length, 'principle')} resting on it and ${count(r.failures.length, 'failure mode')} that would break it, each joined by a line.` });
    if (r.obligations.length) {
      const by = (ink) => r.obligations.filter((ob) => obligationWords(ob.computed)[1] === ink).length;
      const parts = [[by('stated'), 'bound to witnesses that exist'], [by('debt'), 'carrying declared layer debt'], [by('blocked'), 'blocked'], [by('unknown'), 'not computed']].filter(([n]) => n);
      lines.push({ ink: 'obligations', mark: 'Arcs round its mark', text: `its ${count(r.obligations.length, 'checkable part')}: ${parts.map(([n, w]) => `${n} ${w}`).join(', ')}.` });
    }
    if (r.support) lines.push({ ink: 'doctrine', mark: 'Support checker', text: `at build time: ${supportWords(r.support.verdict)[2].toLowerCase()}.` });
  }
  const limit = r.kind === 'axiom'
    ? 'No verdict here is a pass: the support checker could not compute how strong any support is.'
    : r.kind === 'anti_principle' ? 'A failure mode names a way to break an axiom; it is not an observed incident.' : CITATION_WORDS;
  return { lines, limit };
}

function kernelReadout(model, k) {
  const comp = k.componentId ? model.byId.get(k.componentId) : null;
  const lines = [];
  if (comp) lines.push({ ink: 'red', mark: 'Red stem', text: `out to ${comp.title}, whose code calls this computation’s generated code.` });
  lines.push({ ink: 'red', mark: 'Ticks', text: `${count(k.verifiedTasks || 0, 'proof check')} Dafny passed, in a saved result: one tick each.` });
  lines.push({ ink: 'ink', mark: 'Crosses', text: `${count(k.mutants.length, 'deliberately broken version')} the prover rejected.` });
  return { lines, limit: 'The proof covers this one computation, not the component around it.' };
}

function coreReadout(model, c) {
  const lines = [];
  if (c.id === 'replay_admission') {
    lines.push({ ink: 'stated', mark: 'Blue spokes', text: `to all ${count(c.admitted.length, 'component')} with a rerun route it would judge. Nothing has been rerun here.` });
  } else {
    lines.push({ ink: 'ink', mark: 'At the centre', text: `part of the toolkit itself: it ${CORE_NAMES[c.id]?.[1] || moduleWords(c.id)}.` });
  }
  lines.push({ ink: 'red', mark: 'Ticks', text: `${count(c.verifiedTasks || 0, 'proof check')} Dafny passed, in a saved result: one tick each.` });
  lines.push({ ink: 'ink', mark: 'Crosses', text: `${count(c.mutants.length, 'deliberately broken version')} the prover rejected.` });
  return { lines, limit: 'Its proof covers the modelled computation; the code around it is tested, not proved.' };
}

/**
 * The previewed object said against the chosen one, as one plain sentence,
 * or null when they are the same object or nothing is chosen. `info` is the
 * engine's optional hover detail ({ relation: { kind, count } }); the count
 * it carries is preferred, the wording is always this module's.
 */
export function relation(model, hovered, chosen, info) {
  if (!hovered || !chosen || hovered.key === chosen.key) return null;
  const rule = hovered.type === 'rule' ? hovered.rule : chosen.type === 'rule' ? chosen.rule : null;
  const comp = hovered.type === 'component' ? hovered.comp : chosen.type === 'component' ? chosen.comp : null;
  if (rule && comp) {
    const subject = hovered.type === 'component' ? 'Its record' : 'The chosen component’s record';
    if (rule.kind === 'anti_principle') return `${subject} cannot cite ${rule.id}: records cite axioms and principles, never failure modes.`;
    const cites = (comp.ruleIds || []).includes(rule.id);
    const head = `${subject} ${cites ? 'cites' : 'does not cite'} ${rule.id}.`;
    return rule.witnesses.includes(comp.id) ? `${head} The routing registry also names it as a witness.` : head;
  }
  if (hovered.type === 'rule' && chosen.type === 'rule') {
    const a = hovered.rule, b = chosen.rule;
    for (const [p, q] of [[a, b], [b, a]]) {
      if (p.restsOn.includes(q.id)) return `${p.id} rests on ${q.id}.`;
      if (p.threatens.includes(q.id)) return `${p.id} threatens ${q.id}.`;
    }
    const computed = a.citedBy.filter((id) => b.citedBy.includes(id)).length;
    const shared = Number.isFinite(info?.relation?.count) && info.relation.kind === 'shared' ? info.relation.count : computed;
    if (!shared) return `No component cites both ${a.id} and ${b.id}.`;
    return `${count(shared, 'component')} ${shared === 1 ? 'cites' : 'cite'} both ${a.id} and ${b.id}. Shared citations do not link the rules.`;
  }
  if (hovered.type === 'component' && chosen.type === 'component') {
    const a = hovered.comp, b = chosen.comp;
    const wired = model.wires.some(([x, y]) => (x === a.id && y === b.id) || (x === b.id && y === a.id));
    const shared = (a.ruleIds || []).filter((id) => (b.ruleIds || []).includes(id)).length;
    const parts = [wired ? 'A connection between the two is declared in source.' : 'No connection between the two is declared.'];
    if (model.rules.length) parts.push(shared ? `Their records both cite ${count(shared, 'rule')}.` : 'Their records cite no rule in common.');
    return parts.join(' ');
  }
  const kernelOf = (o) => (o.type === 'kernel' ? o.kernel : null);
  const k = kernelOf(hovered) || kernelOf(chosen);
  const c = hovered.type === 'component' ? hovered.comp : chosen.type === 'component' ? chosen.comp : null;
  if (k && c) {
    const owns = c.kernelId === k.id;
    if (hovered.type === 'kernel') return owns ? 'The proved computation inside the chosen component.' : 'Not part of the chosen component.';
    return owns ? 'The component this proved computation sits inside.' : 'This component does not contain the chosen computation.';
  }
  return null;
}

/**
 * What the preview dock says about a previewed object, in reading order:
 * { kind, name, relation, purpose, counts: [text], limit }.
 */
export function preview(model, o, chosen = null, info = undefined) {
  if (!o) return null;
  const rel = relation(model, o, chosen, info);
  const total = model.totals.components;
  if (o.type === 'component') {
    const c = o.comp;
    const cites = (c.ruleIds || []).length;
    const k = c.kernelId ? model.kernelById.get(c.kernelId) : null;
    const counts = [];
    if (model.rules.length) counts.push(cites ? `Its record cites ${count(cites, 'rule')}` : 'Its record cites no rule');
    counts.push(k ? `Contains a proved computation: ${proofShortName(k)}` : 'No proved computation inside it');
    return { kind: `Component · ${familyName(c.family)}`, name: c.title, relation: rel, purpose: c.summary || c.plain || '', counts,
      limit: 'How much of its whole claim the checks cover is unknown.' };
  }
  if (o.type === 'rule') {
    const r = o.rule;
    const n = r.citedBy.length;
    const counts = r.kind === 'anti_principle'
      ? [`Threatens ${r.threatens.join(', ') || 'no recorded axiom'}`, 'Components do not cite failure modes']
      : [`${n} of ${total} components cite it`];
    if (r.kind === 'principle' && r.restsOn.length) counts.push(`Rests on ${r.restsOn.join(', ')}`);
    if (r.kind === 'axiom') counts.push(`${count(r.principles.length, 'principle')} rest on it`);
    return { kind: `${ruleKindWords(r.kind)} · ${r.id}`, name: r.title, relation: rel, purpose: r.reader?.plain || r.plain || '', counts,
      limit: r.kind === 'anti_principle' ? 'A failure mode names a way to break an axiom; it is not an observed incident.' : 'A citation is the component’s own record listing the rule; it is not a check.' };
  }
  const p = o.type === 'kernel' ? o.kernel : o.core;
  const comp = o.type === 'kernel' && o.componentId ? model.byId.get(o.componentId) : null;
  const name = o.type === 'kernel' ? proofShortName(p) : CORE_NAMES[p.id]?.[0] || moduleWords(p.id);
  const purpose = o.type === 'kernel' ? (comp ? `It makes one decision inside “${comp.title}”.` : 'It is used by no component.') : `It ${CORE_NAMES[p.id]?.[1] || 'is part of the toolkit'}.`;
  return { kind: o.type === 'kernel' ? 'Proved computation' : 'Proved computation in the toolkit', name, relation: rel, purpose,
    counts: [`${count(p.verifiedTasks || 0, 'proof check')} passed · ${count(p.mutants.length, 'broken copy', 'broken copies')} rejected`],
    limit: o.type === 'kernel' ? 'The proof covers this one computation, not the component around it.' : 'The proof covers the modelled computation; the code around it is tested, not proved.' };
}

/** A short identity line for a map object: kind and, for a rule, its number. */
export function kindLine(model, o) {
  if (o.type === 'rule') return `${ruleKindWords(o.rule.kind)} · ${o.rule.id}`;
  if (o.type === 'component') return familyName(o.comp.family);
  if (o.type === 'kernel') return 'Proved computation inside a component';
  return 'Proved computation in the toolkit';
}

/**
 * Why an object sits where it does on the map, in one sentence (the
 * universe map's placementHtml: every placed object carries its reason).
 */
export function placement(model, o) {
  const and = (ids) => (ids.length === 1 ? ids[0] : `${ids.slice(0, -1).join(', ')} and ${ids[ids.length - 1]}`);
  if (o.type === 'component') {
    return `In the ${familyName(o.comp.family)} sector, grouped with the components backed the same way.`;
  }
  if (o.type === 'kernel') {
    const comp = o.componentId ? model.byId.get(o.componentId) : null;
    if (!comp) return 'It is used by no component, so it waits under the centre.';
    return `On ${comp.title}’s own radius${o.depth ? `, ${o.depth === 1 ? 'one step' : `${o.depth} steps`} further in so it does not touch a neighbour’s dial` : ''}.`;
  }
  if (o.type === 'core') {
    return o.core.id === 'replay_admission'
      ? 'At the centre, where every component’s rerun route leads.'
      : 'Round the centre with the toolkit’s other proved computations; none of them belongs to one component.';
  }
  if (o.type === 'rule') {
    const r = o.rule;
    if (r.kind === 'axiom') return 'On the middle orbit. The axioms are ordered so that rules tied to several of them sit close together, then the ring is turned toward the components that list them.';
    const ties = r.kind === 'principle' ? r.restsOn : r.threatens;
    const orbit = r.kind === 'principle' ? 'On the inner orbit' : 'On the outer orbit';
    if (!ties.length) return `${orbit}, near the components that list it.`;
    const where = ties.length === 1 ? (r.kind === 'principle' ? 'just inside' : 'just outside') : 'between';
    return `${orbit}, ${where} ${and(ties)}, the ${ties.length === 1 ? 'axiom' : 'axioms'} it ${r.kind === 'principle' ? 'rests on' : 'would break'}.`;
  }
  return '';
}
