// The map's model, assembled from the existing API routes.
//
// One drawing needs every component, every retained proof, each component's
// saved records and its declared wiring, all from one snapshot. The API has
// no single overview route yet, so this module makes about 190 local
// requests (components, proofs, coverage, then receipts and wiring per
// component, then the detail of each component with a modeled contract) and
// refuses to mix revisions: a mismatch restarts once, then fails as an
// explicit 'revision' error. A single overview route is request 1 in
// frontend/BACKEND_REQUESTS.md.

import { API_ROOT, ApiError, apiPath, getEnvelope, withQuery } from './api.js';
import { BACKING_OF, FAMILY_ORDER } from './evidence.js';

async function inPool(tasks, limit) {
  const results = new Array(tasks.length);
  let next = 0;
  async function worker() {
    while (next < tasks.length) {
      const at = next++;
      results[at] = await tasks[at]();
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, tasks.length) }, worker));
  return results;
}

async function loadOnce({ signal, fetchImpl, onProgress }) {
  const opts = { signal, fetchImpl };
  const meta = await getEnvelope(API_ROOT, opts);
  const revision = meta.revision;
  const take = (envelope) => {
    if (envelope.revision !== revision) {
      throw new ApiError('revision', 'The component index changed while the map was loading.', { revision: envelope.revision });
    }
    return envelope.data;
  };
  const all = async (path, params = {}) => {
    let page = take(await getEnvelope(withQuery(path, { ...params, limit: 100 }), opts));
    const items = [...page.items];
    while (page.next_cursor) {
      page = take(await getEnvelope(withQuery(path, { ...params, limit: 100, cursor: page.next_cursor }), opts));
      items.push(...page.items);
    }
    return { items, total: page.total };
  };

  const [summaries, proofPage, coverage] = await Promise.all([
    all(apiPath('components')),
    all(apiPath('proofs')),
    getEnvelope(apiPath('coverage'), opts).then(take),
  ]);
  const ids = summaries.items.map((c) => c.organ_id);
  let done = 0;
  const step = () => { done += 1; if (onProgress) onProgress(done, ids.length); };

  const perComponent = await inPool(ids.map((id) => async () => {
    const receipts = await all(apiPath('receipts'), { component: id });
    const wiring = take(await getEnvelope(withQuery(apiPath('graph'), {
      type: 'organ', id, edge_kind: 'wires_to', direction: 'out', max_edges: 100,
    }), opts));
    step();
    return {
      id,
      receipts: receipts.items,
      wires: wiring.edges.filter((e) => e.kind === 'wires_to' && e.from === id && e.to_type === 'organ').map((e) => e.to),
      wiringTruncated: !!wiring.truncated,
    };
  }), 6);
  const formalIds = summaries.items.filter((c) => (c.formal_subclaim_ids || []).length).map((c) => c.organ_id);
  const details = await inPool(formalIds.map((id) => async () => take(await getEnvelope(apiPath('components', id), opts))), 6);
  return build({ revision, meta: meta.data, summaries: summaries.items, proofs: proofPage.items, coverage, perComponent, details });
}

/** Load the whole overview, restarting once if the snapshot changes mid-load. */
export async function loadOverview(options = {}) {
  try {
    return await loadOnce(options);
  } catch (error) {
    if (error instanceof ApiError && error.kind === 'revision') return loadOnce(options);
    throw error;
  }
}

/** Join the responses into the map's model. Exported for tests. */
export function build({ revision, meta, summaries, proofs, coverage, perComponent, details }) {
  const extra = new Map(perComponent.map((p) => [p.id, p]));
  const detailOf = new Map(details.map((d) => [d.component_id, d]));
  const kernelOfSubclaim = new Map();
  const kernels = proofs.map((view) => {
    const proof = view.proof || {};
    const contract = (view.modeled_contracts || [])[0] || {};
    const kernel = {
      id: proof.proof_id,
      module: proof.module,
      language: proof.language,
      subclaimId: contract.subclaim_id || null,
      statement: contract.statement || '',
      inputModel: contract.input_model || '',
      assumptions: contract.assumptions || '',
      limits: contract.limits || '',
      requirementsReview: contract.requirements_review?.status || 'unrecorded',
      specificationRefs: contract.specification_refs || [],
      entryTheoremRefs: proof.entry_theorem_refs || contract.entry_theorem_refs || [],
      verifiedTasks: proof.retained_verification?.verified_tasks ?? null,
      dafnyVersion: proof.retained_verification?.dafny_version || '',
      mutants: (proof.negative_controls || []).map((c) => ({
        ref: c.source_ref, retained: c.retained_result || {}, fresh: c.fresh_result || {},
      })),
      generatedRefs: proof.generated_refs || [],
      trustedHostRefs: proof.trusted_host_refs || [],
      adapterRef: proof.adapter_ref || '',
      binding: proof.current_binding?.status || 'unrecorded',
      freshProver: proof.fresh_prover_result?.status || view.fresh_prover?.status || 'not_run_by_index',
      componentId: null,
      consumerRefs: [],
    };
    if (kernel.subclaimId) kernelOfSubclaim.set(kernel.subclaimId, kernel);
    return kernel;
  });

  const components = summaries.map((s) => {
    const more = extra.get(s.organ_id) || { receipts: [], wires: [] };
    const family = s.classification?.family || 'unclassified';
    const evidenceClass = s.classification?.evidence_class || s.evidence_class;
    const kernel = (s.formal_subclaim_ids || []).map((id) => kernelOfSubclaim.get(id)).find(Boolean) || null;
    const component = {
      id: s.organ_id,
      title: s.title || s.organ_id,
      summary: s.summary || '',
      family,
      familyKnown: FAMILY_ORDER.includes(family),
      evidenceClass,
      backing: BACKING_OF[evidenceClass] || 'unknown',
      bucket: s.classification?.truth_accounting_bucket || '',
      claimId: s.claim_id,
      subclaimIds: s.formal_subclaim_ids || [],
      kernelId: kernel ? kernel.id : null,
      receipts: more.receipts.map((r) => ({
        ref: r.ref || r.artifact_id, availability: r.availability, kind: r.kind, reason: r.reason || '',
      })),
      wires: more.wires,
      wiringTruncated: !!more.wiringTruncated,
    };
    if (kernel) {
      kernel.componentId = component.id;
      const facets = detailOf.get(component.id)?.claim?.card?.assurance_facets || {};
      kernel.consumerRefs = facets.generated_runtime_binding?.consumer_refs || [];
      kernel.hostTests = facets.host_tests?.refs || [];
    }
    return component;
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
  const receipts = components.reduce((n, c) => n + c.receipts.length, 0);
  const unavailable = components.reduce((n, c) => n + c.receipts.filter((r) => r.availability !== 'available').length, 0);
  return {
    revision,
    meta,
    coverage,
    components,
    byId,
    kernels,
    kernelById: new Map(kernels.map((k) => [k.id, k])),
    wires,
    totals: {
      components: components.length,
      kernels: kernels.length,
      linkedKernels: kernels.filter((k) => k.componentId).length,
      tasks: kernels.reduce((n, k) => n + (k.verifiedTasks || 0), 0),
      mutants: kernels.reduce((n, k) => n + k.mutants.length, 0),
      receipts,
      unavailable,
      wires: wires.length,
    },
  };
}
