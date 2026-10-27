// What each returned fact means, in words, in one place.
//
// The API keeps retained verification, index-time hash binding, linked
// tests, saved runs and fresh results as separate fields; this module keeps
// them separate in prose. Nothing here combines facts into a score or a
// "verified" badge. Unknown is neither red nor green (plectis-atlas
// DESIGN.md, "Evidence states stay distinct"): a value this client does not
// recognise is shown as unrecognised, never as success or failure.

// Families in the order the system map draws them, clockwise from the top
// (ai_workflow sites/microcosm/assets/system-map.js), so the two maps rhyme.
export const FAMILY_ORDER = [
  'entry_and_reveal',
  'architecture_and_navigation',
  'agent_reliability_and_safety',
  'research_and_science_replays',
  'import_projection_and_drift',
  'work_landing_and_continuity',
  'formal_math_and_proof',
];
export const FAMILY_NAME = {
  entry_and_reveal: 'Entry & orientation',
  architecture_and_navigation: 'Architecture & navigation',
  agent_reliability_and_safety: 'Agent reliability & safety',
  research_and_science_replays: 'Research & science',
  import_projection_and_drift: 'Import & drift control',
  work_landing_and_continuity: 'Work & continuity',
  formal_math_and_proof: 'Formal math & proof',
};

// How a component is backed: the system map's five marks and their words
// (system-map.js CLASS_OF, CLASS_WORDS, GLYPHS), reused so a reader learns
// one vocabulary for both maps.
export const BACKING_ORDER = ['tool', 'bounded', 'import', 'contract', 'computes'];
export const BACKING_OF = {
  external_subprocess_witness: 'tool',
  bounded_runtime_computation: 'bounded',
  verified_macro_body_import: 'import',
  semantic_validator: 'contract',
  algorithmic_projection: 'computes',
};
export const BACKING_WORDS = {
  tool: 'Runs a real tool',
  bounded: 'Runs a bounded computation',
  import: 'Imports checked source',
  contract: 'Checks a contract',
  computes: 'Computes from its sources',
};
export const BUCKET_WORDS = {
  real_runtime_receipt: 'Saved receipt from a real run',
  real_import_validation: 'Validates imported material',
  source_faithful_refactor: 'Faithful refactor of its source',
  copied_non_secret_macro_body: 'Copied source body',
};
export const DISPOSITION_WORDS = {
  real_substrate_capsule: 'Real source capsule',
};

/** The words for a classification value; an unknown value is named as such. */
export function classWords(facet, value) {
  const table = facet === 'family' ? FAMILY_NAME
    : facet === 'evidence_class' ? Object.fromEntries(Object.entries(BACKING_OF).map(([k, v]) => [k, BACKING_WORDS[v]]))
      : facet === 'truth_accounting_bucket' ? BUCKET_WORDS
        : facet === 'real_substrate_disposition' ? DISPOSITION_WORDS : {};
  return table[value] || unrecognised(value);
}

export function unrecognised(value) {
  return `Unrecognised value: ${value == null ? 'none' : String(value)}`;
}

// One sentence per recorded state. Each says what the fact is and, where a
// reader could over-read it, what it does not establish.
const STATES = {
  formal_contract: {
    partial: ['A selected computation has a modeled contract.', 'This is not a proof of the whole component.'],
    unknown: ['No modeled contract is recorded for this component in the index.', null],
  },
  whole_claim: {
    unknown: ['Whole-claim coverage has not been established.', 'Not zero coverage, no defects, and not a pass.'],
  },
  generated_runtime_binding: {
    recorded_index_binding: ['Generated code and its caller were linked when the index was built.', 'This read did not recheck them.'],
    unrecorded: ['No generated-code binding is recorded.', null],
  },
  host_tests: {
    linked_not_run: ['Tests are linked to this computation.', 'This view does not run them.'],
    unrecorded: ['No linked tests are recorded.', null],
  },
  mutation_controls: {
    recorded_expected_failures: ['Deliberately broken variants failed verification in the retained record.', 'A fresh run is not recorded here.'],
    unrecorded: ['No broken-variant checks are recorded.', null],
  },
  replay: {
    configured_not_run: ['A replay is declared for this component.', 'This view does not run it.'],
  },
  requirements_review: {
    unrecorded: ['No review of whether the specification states the intended behaviour is recorded.', null],
  },
  fresh_prover: {
    not_run_by_index: ['No fresh prover run is recorded in this view.', 'Neither a failure nor a success.'],
    not_recorded_by_index: ['No fresh prover run is recorded in this view.', 'Neither a failure nor a success.'],
  },
  fresh_replay: {
    not_run_by_index: ['No fresh replay is recorded in this view.', 'Neither a failure nor a success.'],
    not_recorded_by_index: ['No fresh replay is recorded in this view.', 'Neither a failure nor a success.'],
  },
  current_backend_binding: {
    not_checked: ['This read did not compare the current source bytes.', 'It does not show that current code matches the retained evidence.'],
  },
  proof_binding: {
    current_hash_binding_pass: ['Proof source and generated files matched their recorded hashes when the index was built.', 'Checked at index generation only.'],
  },
};

/** [sentence, caution|null, recognised] for one facet's status. */
export function stateWords(facet, status) {
  const row = STATES[facet] && STATES[facet][status];
  if (row) return [row[0], row[1], true];
  return [unrecognised(status), null, false];
}

/** A saved run record's availability, never turned into a link when absent. */
export function availabilityWords(record) {
  if (!record) return ['No record.', false];
  if (record.availability === 'available') return ['Listed as available in this snapshot.', true];
  if (record.availability === 'unavailable') {
    return [`Not in this snapshot.${record.reason ? ` The index gives the reason: ${record.reason}.` : ''}`, false];
  }
  return [unrecognised(record.availability), false];
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
/** "27 May 2026" from an ISO timestamp; the text itself when it is not one. */
export function dayWords(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ''));
  if (!m) return String(iso || '');
  return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}`;
}

/** The last saved run, as a dated historical fact. */
export function lastRunWords(lastResult) {
  if (!lastResult) return 'No saved run is recorded.';
  const status = lastResult.recorded_status === 'pass' ? 'recorded a pass'
    : lastResult.recorded_status ? `recorded "${lastResult.recorded_status}"` : 'has no recorded status';
  const when = lastResult.created_at ? ` on ${dayWords(lastResult.created_at)}` : '';
  return `The saved run${when} ${status}. It is a historical record, not checked against the current code.`;
}

/** "OwnershipClassification" -> "Ownership classification". */
export function moduleWords(name) {
  const words = String(name || '').replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/([A-Z])([A-Z][a-z])/g, '$1 $2').split(' ');
  return words.map((w, i) => (i === 0 ? w : /^[A-Z]{2,}$/.test(w) ? w : w.toLowerCase())).join(' ');
}

/** A short label for a proof ID: proof::dafny::mcp_authority -> "MCP authority". */
export function proofShortName(proof) {
  if (proof && proof.module) return moduleWords(proof.module).replace(/^Mcp\b/, 'MCP');
  const tail = String(proof?.proof_id || '').split('::').pop() || '';
  return tail.replace(/_/g, ' ');
}

/** Plural helper: count(3, 'component') -> "3 components". */
export function count(n, noun, plural = `${noun}s`) {
  return `${n.toLocaleString('en-GB')} ${n === 1 ? noun : plural}`;
}
