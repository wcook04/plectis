// The map's model, from one overview response.
//
// GET /api/v1/overview?view=map carries the fields used by this model in
// one revision-bound envelope: components, proofs, workflow cores, coverage,
// labels, doctrine, typed imports and compact saved-record summaries. Full
// guides and record detail load only when a reader asks to see them. Older
// indexes may have no cores or explorer extension; those parts stay empty.

import { ApiError, apiPath, getEnvelope } from './api.js';
import { BACKING_OF, DOCTRINE_KINDS, FAMILY_ORDER, TRACKS } from './evidence.js';

/** Load the overview. One request, so no revision can be mixed. */
export async function loadOverview({ signal, fetchImpl } = {}) {
  const envelope = await getEnvelope(`${apiPath('overview')}?view=map`, { signal, fetchImpl });
  if (!envelope.data || !Array.isArray(envelope.data.components)) {
    throw new ApiError('schema', 'The overview response has no component list.');
  }
  return build(envelope.data, envelope.revision);
}

// One model per session, shared by the map and the proof pages. A later
// visit checks the snapshot revision first and reloads only when it moved.
let cached = null;
export async function getModel(options = {}) {
  if (cached) {
    const meta = await getEnvelope(apiPath(), options);
    if (meta.revision === cached.revision) return cached;
  }
  cached = await loadOverview(options);
  return cached;
}


const list = (v) => (Array.isArray(v) ? v : v ? [v] : []);
const text = (v) => (Array.isArray(v) ? v.filter(Boolean).join(' ') : v || '');

function mutantsOf(controls) {
  return list(controls).map((c) => ({
    ref: c.source_ref,
    errors: c.retained_result?.errors ?? null,
    verifiedTasks: c.retained_result?.verified_tasks ?? null,
    fresh: c.fresh_result?.status || 'not_run_by_index',
    description: c.description || '',
    changedLines: list(c.changed_lines).map((l) => ({ line: l.line, original: l.original, mutated: l.mutated })),
  }));
}

function excerptsOf(rows) {
  return list(rows).map((e) => ({
    ref: e.ref, kind: e.kind, name: e.name, lineStart: e.line_start, lineEnd: e.line_end, text: e.text || '',
  }));
}

function recordOf(r) {
  const s = r.summary || {};
  const fields = s.recorded_fields || {};
  return {
    ref: r.ref || r.artifact_id,
    availability: r.availability,
    kind: r.kind,
    reason: r.reason || s.availability_reason || '',
    status: fields.status || null,
    fixtureId: fields.fixture_id || null,
    cases: fields.case_count ?? null,
    createdAt: s.created_at || null,
    dated: s.date_status === 'recorded',
  };
}

/** Join the overview into the map's model. Exported for tests. */
export function build(data, revision) {
  const explorer = data.explorer || {};
  const details = explorer.proof_details || {};
  const cov = data.coverage || {};
  const presence = new Map();
  for (const [measure, row] of Object.entries(cov.component_presence || {})) {
    presence.set(measure, new Set(list(row.component_ids)));
  }

  const labels = {};
  for (const [facet, values] of Object.entries(explorer.component_filters || {})) {
    labels[facet] = new Map(list(values).map((v) => [v.value, { label: v.label, description: v.description || '', count: v.component_count }]));
  }

  const kernels = list(data.kernels).map((view) => {
    const proof = view.proof || {};
    const contract = list(view.modeled_contracts)[0] || {};
    const extra = details[proof.proof_id] || {};
    const retained = proof.retained_verification || {};
    const variantDetail = extra.negative_control_details || {};
    const controls = list(proof.negative_controls).map((c) => ({ ...variantDetail[c.source_ref], ...c }));
    return {
      id: proof.proof_id,
      module: proof.module,
      language: proof.language,
      componentIds: list(view.component_ids || proof.component_ids),
      claimIds: list(view.claim_ids || proof.claim_ids),
      subclaimId: contract.subclaim_id || null,
      statement: contract.statement || '',
      inputModel: contract.input_model || '',
      assumptions: text(contract.assumptions),
      limits: text(contract.limits),
      requirementsReview: contract.requirements_review?.status || 'unrecorded',
      specificationRefs: list(contract.specification_refs),
      entryTheoremRefs: list(proof.entry_theorem_refs || contract.entry_theorem_refs),
      verifiedTasks: retained.verified_tasks ?? null,
      tasksAvailability: retained.tasks_availability || extra.retained_verification_details?.tasks_availability || 'unrecorded',
      dafnyVersion: retained.dafny_version || '',
      mutants: mutantsOf(controls),
      excerpts: excerptsOf(proof.excerpts || extra.excerpts),
      generatedRefs: list(proof.generated_refs),
      trustedHostRefs: list(proof.trusted_host_refs),
      adapterRef: proof.adapter_ref || '',
      checkerRef: proof.current_binding?.checker_ref || '',
      binding: proof.current_binding?.status || 'unrecorded',
      freshProver: proof.fresh_prover_result?.status || view.fresh_prover?.status || 'not_run_by_index',
      componentId: null,
    };
  });
  const kernelById = new Map(kernels.map((k) => [k.id, k]));

  const coreRows = list(explorer.cores).length ? list(explorer.cores) : list(data.cores);
  const cores = coreRows.map((c) => ({
    id: c.core_id,
    proofId: c.proof_id,
    module: c.module,
    statement: c.statement || '',
    assumptions: text(c.assumptions),
    limits: text(c.limits),
    verifiedTasks: c.retained_verification?.verified_tasks ?? null,
    dafnyVersion: c.retained_verification?.dafny_version || '',
    mutants: mutantsOf(c.negative_controls),
    excerpts: excerptsOf(c.excerpts),
    generatedRefs: list(c.generated_refs),
    specificationRefs: list(c.specification_refs),
    entryTheoremRefs: list(c.entry_theorem_refs),
    callers: list(c.public_caller_refs),
    guideRef: c.guide_ref || '',
    checkerRef: c.current_binding?.checker_ref || '',
    binding: c.current_binding?.status || 'unrecorded',
    freshProver: c.fresh_prover_result?.status || 'not_run_by_index',
    requirementsReview: c.requirements_review?.status || 'unrecorded',
    admitted: list(c.admitted_replay_routes).map((r) => ({ componentId: r.component_id, route: r.route })),
  }));
  const coreById = new Map(cores.map((c) => [c.id, c]));

  const imports = list(explorer.typed_relations?.edges).map((e) => ({
    from: e.from_id, to: e.to_id, kind: e.kind, ref: e.source_ref, line: e.line,
  }));
  const routeOf = new Map();
  for (const core of cores) for (const r of core.admitted) routeOf.set(r.componentId, r.route);

  const components = list(data.components).map((s) => {
    const family = s.classification?.family || 'unclassified';
    const evidenceClass = s.classification?.evidence_class || s.evidence_class;
    const proofIds = list(s.proof_ids);
    const kernel = proofIds.map((id) => kernelById.get(id)).find(Boolean)
      || kernels.find((k) => k.componentIds.includes(s.organ_id)) || null;
    const c = {
      id: s.organ_id,
      title: s.title || s.organ_id,
      summary: s.summary || '',
      plain: s.plain_availability === 'available' && typeof s.plain === 'string' ? s.plain : null,
      plainAvailability: s.plain_availability || 'unrecorded',
      family,
      familyKnown: FAMILY_ORDER.includes(family),
      evidenceClass,
      backing: BACKING_OF[evidenceClass] || 'unknown',
      bucket: s.classification?.truth_accounting_bucket || '',
      claimId: s.claim_id,
      subclaimIds: list(s.formal_subclaim_ids),
      proofIds,
      kernelId: kernel ? kernel.id : null,
      receipts: list(s.receipt_refs).map(recordOf),
      wires: list(s.wires_to),
      doctrineIds: list(s.doctrine_ref_ids),
      routeIds: list(s.route_ids),
      replayRoute: routeOf.get(s.organ_id) || null,
      importsOut: imports.filter((e) => e.from === s.organ_id),
      importsIn: imports.filter((e) => e.to === s.organ_id),
    };
    c.checks = {};
    for (const t of TRACKS) c.checks[t.id] = t.measure && presence.has(t.measure) ? presence.get(t.measure).has(c.id) : null; // a measure the snapshot does not carry stays unknown, never false
    if (kernel && !kernel.componentId) kernel.componentId = c.id;
    return c;
  });
  const byId = new Map(components.map((c) => [c.id, c]));

  // Wiring is declared from one side; keep each pair once, between known ends.
  const wires = [];
  const seen = new Set();
  for (const c of components) {
    for (const to of c.wires) {
      if (!byId.has(to)) continue;
      const key = c.id < to ? `${c.id}|${to}` : `${to}|${c.id}`;
      if (seen.has(key)) continue;
      seen.add(key);
      wires.push([c.id, to]);
    }
  }

  const doctrine = new Map(list(explorer.doctrine?.nodes).map((n) => [n.id, n]));
  const doctrineEdges = list(explorer.doctrine?.edges);
  const { rules, ruleById } = rulesOf(doctrine, doctrineEdges, components, byId);
  const source = explorer.source_revision || null;
  const records = components.flatMap((c) => c.receipts);
  const dated = records.filter((r) => r.createdAt).map((r) => r.createdAt).sort();

  // What a write-up's links can open inside the explorer.
  const proofIdOfDir = new Map(kernels.map((k) => [String(k.id).split('::').pop(), k.id]));
  for (const c of cores) {
    const dir = /^formal\/([\w-]+)\/README\.md$/.exec(c.guideRef || '');
    if (dir) proofIdOfDir.set(dir[1], c.proofId);
  }
  const sourceRevision = source && source.status === 'recorded' && source.exact_source_links && /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/.test(source.repository || '')
    && /^[0-9a-f]{40}$/.test(source.commit || '') ? { repository: source.repository, commit: source.commit } : null;

  return {
    revision,
    labels,
    filters: explorer.component_filters || null,
    coverage: cov,
    presence,
    components,
    byId,
    kernels,
    kernelById,
    cores,
    coreById,
    imports,
    wires,
    doctrine,
    doctrineEdges,
    rules,
    ruleById,
    doctrineSources: list(explorer.doctrine?.sources),
    ownership: explorer.ownership_example || null,
    reviews: list(explorer.requirements_reviews),
    clauses: list(explorer.claim_clause_coverage),
    localRuns: data.local_runs || null,
    source: sourceRevision,
    links: { componentIds: new Set(byId.keys()), proofIdOfDir, source: sourceRevision, revision, guides: explorer.guides ?? null },
    totals: {
      components: components.length,
      kernels: kernels.length,
      linkedKernels: kernels.filter((k) => k.componentId).length,
      cores: cores.length,
      tasks: kernels.reduce((n, k) => n + (k.verifiedTasks || 0), 0),
      coreTasks: cores.reduce((n, k) => n + (k.verifiedTasks || 0), 0),
      mutants: kernels.reduce((n, k) => n + k.mutants.length, 0) + cores.reduce((n, k) => n + k.mutants.length, 0),
      receipts: records.length,
      unavailable: records.filter((r) => r.availability !== 'available').length,
      wires: wires.length,
      imports: imports.length,
      firstRecord: dated[0] || null,
      lastRecord: dated[dated.length - 1] || null,
      excerpts: kernels.reduce((n, k) => n + k.excerpts.length, 0),
      rules: rules.length,
      axioms: rules.filter((r) => r.kind === 'axiom').length,
      principles: rules.filter((r) => r.kind === 'principle').length,
      failures: rules.filter((r) => r.kind === 'anti_principle').length,
      citations: rules.reduce((n, r) => n + r.citedBy.length, 0),
    },
  };
}

function readerOf(r, byId) {
  if (!r) return null;
  const known = (ids) => list(ids).filter((id) => byId.has(id));
  return {
    plain: r.plain || '',
    analogy: r.analogy?.text || '',
    analogyMaps: list(r.analogy?.maps).map((m) => ({ doctrine: m.doctrine || '', analogy: m.analogy || '' })),
    analogyBoundary: r.analogy?.boundary || '',
    whyItMatters: r.why_it_matters || '',
    misread: r.potential_misread || '',
    governs: r.governs || '',
    requires: r.requires || '',
    refuses: r.refuses || '',
    example: r.example?.text || '',
    exampleIds: known(r.example?.component_ids),
    counterexample: typeof r.counterexample === 'string' ? r.counterexample : r.counterexample?.text || '',
    enforcedIn: known(r.enforced_in_component_ids),
    doesNotProve: r.does_not_prove || '',
  };
}

// The doctrine as rules joined to the components. A principle rests on its
// axioms and a failure mode threatens its axioms (explorer.doctrine edges,
// rests_on and violates, as authored). A component cites a rule when its
// atlas row lists it (doctrine_ref_ids); the axiom's routing row names its
// witnesses, and the support checker's verdict and each obligation's
// computed status come from the index build (doctrine v2). An older index
// has none of the v2 parts and the rule keeps them empty.
function rulesOf(doctrine, edges, components, byId) {
  const rules = [];
  const ruleById = new Map();
  for (const n of doctrine.values()) {
    if (!n || !n.id || !DOCTRINE_KINDS.includes(n.kind)) continue;
    const ax = n.axiom || null;
    const rule = {
      id: n.id,
      kind: n.kind,
      title: n.title || n.id,
      plain: n.plain || '',
      sourceRef: n.source_ref || '',
      // The card names the rule, so the section's own heading is dropped.
      statement: String(n.statement || '').replace(/^#{1,4} [^\n]*\n+/, '').trim(),
      restsOn: [],
      threatens: [],
      principles: [],
      failures: [],
      citedBy: [],
      witnesses: list(ax?.routing?.witness_component_ids).filter((id) => byId.has(id)),
      // The hand-written reader content (core/doctrine_enrichment.json):
      // reader words, never support evidence; empty for an older index.
      reader: readerOf(n.reader, byId),
      formalClause: ax?.formal_clause || '',
      lineage: list(ax?.lineage),
      antiAxiom: ax?.anti_axiom || '',
      routedStrength: ax?.routing?.witness_strength || null,
      obligations: list(ax?.obligations).map((o) => ({
        id: o.obligation_id, predicate: o.predicate || '', required: !!o.required,
        declared: o.declared_status || null, computed: o.computed_status || null,
        witnesses: list(o.witness_component_ids).filter((id) => byId.has(id)),
        surfaces: list(o.witness_surfaces), negativeCases: list(o.negative_case_codes), gaps: list(o.witness_gaps),
      })),
      support: ax?.support ? {
        verdict: ax.support.verdict || null,
        notCertifiable: !!ax.support.hand_stamped_strong_not_certifiable,
        blockedReasons: list(ax.support.strong_blocked_reasons),
        checker: ax.support.checker_id || '',
      } : null,
    };
    rules.push(rule);
    ruleById.set(rule.id, rule);
  }
  // Numbered order within each kind: AX-2 before AX-10.
  const num = (id) => Number(/(\d+)$/.exec(id)?.[1] ?? 1e9);
  rules.sort((a, b) => DOCTRINE_KINDS.indexOf(a.kind) - DOCTRINE_KINDS.indexOf(b.kind) || num(a.id) - num(b.id) || a.id.localeCompare(b.id));
  for (const e of edges) {
    const from = ruleById.get(e.from_id), to = ruleById.get(e.to_id);
    if (!from || !to || to.kind !== 'axiom') continue;
    if (e.kind === 'rests_on' && from.kind === 'principle') { from.restsOn.push(to.id); to.principles.push(from.id); }
    if (e.kind === 'violates' && from.kind === 'anti_principle') { from.threatens.push(to.id); to.failures.push(from.id); }
  }
  for (const c of components) {
    c.ruleIds = c.doctrineIds.filter((id) => ruleById.has(id));
    for (const id of c.ruleIds) ruleById.get(id).citedBy.push(c.id);
  }
  return { rules, ruleById };
}
