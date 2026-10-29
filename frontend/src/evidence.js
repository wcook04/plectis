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
// How a component is backed: the system map's five marks
// (system-map.js CLASS_OF, GLYPHS), reused so a reader learns one set of
// shapes for both maps. The words for each class come from the API.
export const BACKING_ORDER = ['tool', 'bounded', 'import', 'contract', 'computes'];
export const BACKING_OF = {
  external_subprocess_witness: 'tool',
  bounded_runtime_computation: 'bounded',
  verified_macro_body_import: 'import',
  semantic_validator: 'contract',
  algorithmic_projection: 'computes',
};
export const CLASS_OF_BACKING = Object.fromEntries(Object.entries(BACKING_OF).map(([k, v]) => [v, k]));

// Labels and descriptions for classification values come from the API
// (metadata component_filters, or the overview's explorer extension), which
// carries the owners' wording. This client keeps no second registry: before
// labels arrive, or for an index that has none, a value is shown as its
// identifier in words; a value missing from a labelled facet is unrecognised.
const LABELS = new Map();
const LABELLED = new Set();
export function setLabels(filters) {
  for (const [facet, values] of Object.entries(filters || {})) {
    for (const v of Array.isArray(values) ? values : []) {
      if (!v || !v.value || !v.label) continue;
      LABELS.set(`${facet}\u0000${v.value}`, { label: v.label, description: v.description || '' });
      LABELLED.add(facet);
    }
  }
}
export function identifierWords(value) {
  const s = String(value ?? '').replace(/_/g, ' ').trim();
  return s ? s[0].toUpperCase() + s.slice(1) : '';
}

/** The words for a classification value; an unknown value is named as such. */
export function classWords(facet, value) {
  if (value === null || value === undefined || value === '') return unrecognised(value);
  const row = LABELS.get(`${facet}\u0000${value}`);
  if (row) return row.label;
  return LABELLED.has(facet) ? unrecognised(value) : identifierWords(value);
}
/** The owner's one-line description of a classification value, or ''. */
export function classDescription(facet, value) {
  return LABELS.get(`${facet}\u0000${value}`)?.description || '';
}
export const familyName = (family) => classWords('family', family);

export function unrecognised(value) {
  return `Unrecognised value: ${value == null ? 'none' : String(value)}`;
}

// One sentence per recorded state. Each says what the fact is and, where a
// reader could over-read it, what it does not establish.
const STATES = {
  formal_contract: {
    partial: ['One computation inside it is proved against written rules.', 'The rest of the component is outside that proof.'],
    unknown: ['No proved computation is recorded for it.', null],
  },
  whole_claim: {
    unknown: ['Nobody has worked out how much of its whole claim is covered.', 'That means unknown, not zero, and not a pass.'],
    not_exhaustively_mapped: ['Nobody has worked out how much of its whole claim is covered.', 'That means unknown, not zero, and not a pass.'],
  },
  generated_runtime_binding: {
    recorded_index_binding: ['Its code is linked to the proved code it calls.', 'The link was recorded when this snapshot was made; this page did not recheck it.'],
    unrecorded: ['No link to proved code is recorded.', null],
  },
  host_tests: {
    linked_not_run: ['Tests are linked to it.', 'This page does not run them.'],
    unrecorded: ['No linked tests are recorded.', null],
  },
  mutation_controls: {
    recorded_expected_failures: ['Deliberately broken versions of its proved computation failed the proof, as they should.', 'From saved results, not a new run.'],
    unrecorded: ['No broken-version checks are recorded.', null],
  },
  replay: {
    configured_not_run: ['A rerun is set up for it.', 'This page does not run it.'],
  },
  requirements_review: {
    unrecorded: ['Nobody has recorded a check that the written rules say the right thing.', null],
  },
  fresh_prover: {
    not_run_by_index: ['The prover has not been run for this page.', 'That is neither a pass nor a failure.'],
    not_recorded_by_index: ['The prover has not been run for this page.', 'That is neither a pass nor a failure.'],
  },
  fresh_replay: {
    not_run_by_index: ['Nothing has been rerun for this page.', 'That is neither a pass nor a failure.'],
    not_recorded_by_index: ['Nothing has been rerun for this page.', 'That is neither a pass nor a failure.'],
  },
  current_backend_binding: {
    not_checked: ['This page did not compare today\'s code with the saved results.', 'So it cannot say the two still match.'],
  },
  proof_binding: {
    current_hash_binding_pass: ['The proof and the code made from it matched their saved fingerprints when this snapshot was made.', 'Checked then, not now.'],
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
  if (record.availability === 'available') return ['Included in this snapshot.', true];
  if (record.availability === 'unavailable') {
    return [`Missing from this snapshot${record.reason ? ` (${record.reason.replace(/_/g, ' ')})` : ''}.`, false];
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
  if (!lastResult) return 'No past run is saved.';
  const status = lastResult.recorded_status === 'pass' ? 'passed'
    : lastResult.recorded_status ? `ended as "${lastResult.recorded_status}"` : 'has no saved outcome';
  const when = lastResult.created_at ? `, on ${dayWords(lastResult.created_at)},` : '';
  return `The last saved run${when} ${status}. It is an old result, not a check of today's code.`;
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

// The map's rings, from the component outward. Each ring is one kind of
// check, named with what does the checking and when; a component's cell is
// filled where the coverage view lists it under that measure
// (component_assurance.py, component_presence). Inks keep their meaning:
// red where a machine checked something and the result was kept, azure where
// something is stated or configured, ember for saved historical runs, and a
// hatch where nothing has been established.
export const TRACKS = [
  {
    id: 'proof', measure: 'retained_proof_metadata', ink: 'ran', short: 'Proved',
    title: 'Proved with Dafny', checker: 'Dafny prover', when: 'saved result',
    words: 'A small computation inside the component is proved to follow its written rules.',
    means: 'Inside the component, one small piece of code makes a decision. Someone wrote down the rules that decision must follow, in a precise language called Dafny, and a program called a prover checked mathematically that the code follows those rules for every possible input, not just for a few test cases.',
    filled: 'The component contains a proved piece like this, and the proof passed when it was last run. That result is saved.',
    empty: 'No part of the component is proved this way. Other rings may still show other checks.',
    not: 'That the whole component is correct. Only that one decision is proved, and only against the rules as written: if the rules are wrong, the proof cannot tell.',
    example: 'In the ownership component, the rule that a live claim on a file always beats a stale one is proved.',
  },
  {
    id: 'variants', measure: 'source_linked_mutation_controls', ink: 'ran', short: 'Broken versions caught',
    title: 'Broken versions caught', checker: 'Dafny prover', when: 'saved result',
    words: 'Copies of that computation with one deliberate mistake were rejected by the prover, so the rules really do constrain the code.',
    means: 'A proof is only useful if the rules are strict enough to catch mistakes. To test that, copies of the proved code were made, each with one deliberate mistake, and the prover was run on them.',
    filled: 'Every broken copy tried was rejected by the prover, as it should be. That result is saved.',
    empty: 'No broken copies were tried for this component.',
    not: 'That the rules would catch every possible mistake, only the ones that were tried.',
    example: 'For the ownership component, one broken copy went back to the old rule of picking the first claim; the prover rejected it.',
  },
  {
    id: 'bound', measure: 'index_time_hash_bindings', ink: 'ran', short: 'Code matches proof',
    title: 'Running code matches the proof', checker: 'SHA-256 fingerprints', when: 'when the snapshot was made',
    words: 'The code that runs is the code the proof was about: their fingerprints matched.',
    means: 'The prover checks Dafny code, but the system runs Python. Dafny turns the proved code into Python automatically. This check compares digital fingerprints (SHA-256 hashes) of the proof and of the Python made from it with the fingerprints saved when the proof passed, to confirm that the code that runs is exactly the code that was proved.',
    filled: 'The fingerprints matched when this snapshot of the project was made.',
    empty: 'There is no proved code in this component, so there is nothing to match.',
    not: 'That the code still matches now. It was checked when the snapshot was made, and an edit made afterwards would not show here.',
    example: 'The ownership component\'s five generated Python files all matched their saved fingerprints.',
  },
  {
    id: 'caller', measure: 'generated_runtime_bindings', ink: 'stated', short: 'Calls proved code',
    title: 'Calls the proved code', checker: 'Link in the source', when: 'declared',
    words: "The component's own code calls the proved computation directly.",
    means: 'Proved code only helps if the component actually uses it. This ring shows that the component\'s own code calls the proved computation, rather than a hand-written copy of the same decision.',
    filled: 'The source code records a direct call from the component to the proved computation.',
    empty: 'No such call is recorded, usually because the component has no proved part.',
    not: 'That the call has been seen happening. It is a link written in the code, not a record of a run.',
    example: 'The ownership component hands every claim to the proved computation and acts on its answer.',
  },
  {
    id: 'lean', measure: 'historical_lean_receipt_observations', ink: 'ran', short: 'Lean run',
    title: 'Lean proof run saved', checker: 'Lean', when: 'past run',
    words: 'A past run saved the Lean proof checker accepting a proof. That is not a proof about the component\'s own code.',
    means: 'Lean is a different proof checker, used for mathematics. A few components exist to run Lean on example proofs and record what happened.',
    filled: 'A saved run shows Lean checking an example proof.',
    empty: 'No Lean run is saved for this component.',
    not: 'That the component\'s own code is proved. It is about the example mathematics.',
    example: 'The Lean and Lake proof witness ran Lean on a small project and saved that a wrong proof was rejected.',
  },
  {
    id: 'replay', measure: 'configured_replay_routes', ink: 'stated', short: 'Rerun set up',
    title: 'Rerun set up', checker: 'Replay checker', when: 'set up, not run here',
    words: 'Everything needed to rerun the component is declared, and the replay checker at the centre would judge the rerun. Nothing has been rerun here.',
    means: 'Any component can be run again from scratch to see whether it still gives the same result. Its inputs, the command and what to compare are written down. A separate proved computation, the replay checker at the centre of the map, decides whether a rerun of everything is accepted.',
    filled: 'A rerun is set up for this component. Every component has one.',
    empty: 'No rerun is set up.',
    not: 'That anything has been rerun. Set up is not the same as passed.',
    example: 'Every spoke on the map is one component\'s rerun, leading to the replay checker.',
  },
  {
    id: 'saved', measure: 'available_authority_artifacts', ink: 'saved', short: 'Past runs',
    title: 'Past runs saved', checker: 'Its own tests', when: 'earlier',
    words: "Results from earlier runs are saved. They are not rerun against today's code.",
    means: 'Each component has its own tests. When they ran in the past, their results were saved, usually with the date.',
    filled: 'At least one past result is saved; most components have four.',
    empty: 'No past result is saved.',
    not: 'That the component passes today. These are results from earlier runs.',
    example: 'The MCP tool authority component has four saved passes, the latest from 27 May 2026.',
  },
  {
    id: 'whole', measure: null, ink: 'unknown', short: 'Whole claim',
    title: 'Whole claim covered?', checker: 'Nobody yet', when: '',
    words: "Nobody has worked out how much of any component's whole claim is covered. That is unknown, not zero.",
    means: 'Each component makes a claim about what it does. Nobody has yet split those claims into parts and matched each part to a check, so how much of each claim the checks cover is not known.',
    filled: '',
    empty: '',
    not: 'That nothing is covered, or that everything passed. Unknown is drawn hatched for every component.',
    example: '',
  },
];
export const TRACK_BY_ID = Object.fromEntries(TRACKS.map((t) => [t.id, t]));

/**
 * A link to exact source at the index's recorded revision, or null. Only a
 * plain repository path gets a link; a file#Symbol reference takes its lines
 * from a bounded excerpt when one is known.
 */
export function sourceHref(source, ref, lines = null) {
  if (!source || !ref) return null;
  const path = String(ref).split('#')[0].split('::')[0];
  if (!/^[A-Za-z0-9_][A-Za-z0-9_./-]*$/.test(path) || path.includes('..') || path.startsWith('state/')) return null;
  const anchor = lines && lines[0] ? `#L${lines[0]}${lines[1] && lines[1] !== lines[0] ? `-L${lines[1]}` : ''}` : '';
  return `${source.repository}/blob/${source.commit}/${path}${anchor}`;
}

/** A saved record in one line: what it recorded, and when, if a date was recorded. */
export function recordWords(rec) {
  if (rec.availability !== 'available') {
    return `Missing from this snapshot${rec.reason ? ` (${rec.reason.replace(/_/g, ' ')})` : ''}.`;
  }
  const status = rec.status === 'pass' ? 'Passed' : rec.status ? `Ended as "${rec.status}"` : 'No saved outcome';
  return `${status}${rec.createdAt ? ` on ${dayWords(rec.createdAt)}` : ', date not saved'}.`;
}

// Files named in words, for readers who do not read paths: the last part of
// a path, without its extension and leading underscore, with a function
// after "#" kept as written.
export function fileWords(ref) {
  const [path, symbol] = String(ref || '').split('#');
  const file = path.split('/').pop().replace(/\.(py|dfy|md|json)$/, '').replace(/^_+/, '');
  const words = file.replace(/_/g, ' ').trim();
  return symbol ? `${words} (${symbol})` : words;
}

/** "src/plectis/repair/_host.py#make_plan" -> { api: "plectis.repair", fn: "make_plan" }. */
export function callerWords(ref) {
  const [path, fn] = String(ref || '').split('#');
  const parts = path.replace(/^src\//, '').replace(/\.py$/, '').split('/').filter((p) => !p.startsWith('_'));
  return { api: parts.join('.'), fn: fn || '' };
}

// The four computations at the centre, named for what they do.
export const CORE_NAMES = {
  replay_admission: ['Replay checker', 'judges reruns of every component'],
  repair: ['Repair planner', 'plans what to rerun after a change'],
  compatibility: ['Compatibility check', 'checks a replacement behaves the same'],
  views: ['Public views', 'makes reports without private data'],
};

/** One plain sentence on what a flower is, for a kernel or a core. */
export function flowerWords(p, usedBy) {
  const n = p.verifiedTasks || 0;
  const m = p.mutants.length;
  return `This flower is one small computation proved correct against written rules. ${usedBy} `
    + `Its ${n} petals are the ${n} proof checks that passed, and its ${m} ${m === 1 ? 'cross is a broken copy' : 'crosses are broken copies'} the prover rejected.`;
}
