// One component, read from its claim outward. The brief's order: the claim
// and its limit first, then the guide, the declared replay, modeled
// subclaims, retained proofs and saved records. Each section lights its step
// in the chain figure beside it. The detail and its receipts load together
// and are shown only when both come from one snapshot revision.

import { apiPath, loadTogether, withQuery } from '../api.js';
import { backingGlyph, copyButton, h, keyGlyph } from '../dom.js';
import {
  BACKING_OF, BACKING_WORDS, FAMILY_NAME, availabilityWords, classWords, count, dayWords, lastRunWords, moduleWords, stateWords,
} from '../evidence.js';
import { chainFigure, followSections } from './chain.js';

export async function mountComponent(root, { id }) {
  const page = h('div', { class: 'page' }, h('p', { class: 'muted', role: 'status' }, 'Loading the component…'));
  root.append(page);
  let detail, receipts, revision;
  try {
    ({ revision, parts: [detail, receipts] } = await loadTogether([
      apiPath('components', id),
      withQuery(apiPath('receipts'), { component: id, limit: 100 }),
    ]));
  } catch (error) {
    page.replaceChildren(failure(error, id));
    return () => {};
  }
  document.title = `${detail.claim?.card?.title || id} · Plectis components`;
  const claim = detail.claim || {};
  const card = claim.card || {};
  const facets = card.assurance_facets || {};
  const cls = detail.classification || {};
  const backing = BACKING_OF[cls.evidence_class] || 'unknown';
  const formal = (detail.proofs || []).length > 0;
  const sections = [];
  const section = (sid, title, ...content) => {
    const el = h('section', { id: `s-${sid}`, 'aria-labelledby': `h-${sid}` }, h('h2', { id: `h-${sid}` }, title), ...content);
    sections.push({ id: sid, el });
    return el;
  };
  const factItem = (facet, status, glyph) => {
    const [text, caution, known] = stateWords(facet, status);
    return h('li', { class: `fact${known ? '' : ' fact--unknown'}` }, glyph,
      h('span', {}, h('span', { class: 'fact__text' }, text), caution ? h('span', { class: 'fact__caution' }, caution) : null));
  };

  const available = (receipts.items || []).filter((r) => r.availability === 'available').length;
  const absent = (receipts.items || []).length - available;
  const steps = [
    { id: 'claim', title: 'Claim', note: 'stated by the registry, with its limit', state: 'stated', ink: 'azure' },
    formal
      ? { id: 'contract', title: 'Modeled contract', note: `${count(detail.subclaims.length, 'selected computation')}`, state: 'stated', ink: 'azure', shape: 'kernel' }
      : { id: 'contract', title: 'No modeled contract', note: 'none recorded for this component', state: 'absent', ink: 'faint' },
  ];
  if (formal) {
    const p = detail.proofs[0].proof || {};
    steps.push(
      { id: 'proof', title: 'Retained proof', note: `${count(p.retained_verification?.verified_tasks || 0, 'task')} verified by Dafny`, state: 'recorded', ink: 'red' },
      { id: 'generated', title: 'Generated code', note: 'hash-bound when the index was built', state: 'recorded', ink: 'red', shape: 'square' },
      { id: 'caller', title: 'Application caller', note: 'linked; not run by this view', state: 'stated', ink: 'ink', shape: 'diamond' },
    );
  }
  steps.push(
    { id: 'replay', title: 'Declared replay', note: 'configured; this view runs nothing', state: 'configured', ink: 'ink' },
    { id: 'records', title: 'Saved records', note: absent ? `${available} listed, ${absent} not in this snapshot` : `${available} listed`, state: 'recorded', ink: 'ink', shape: 'records' },
    { id: 'open', title: 'Whole claim', note: 'coverage unknown', state: 'unknown', ink: 'faint' },
  );
  const figure = chainFigure(steps, { label: `The evidence chain for ${card.title || id}` });

  const steps$ = h('div', { class: 'reader__steps' });
  steps$.append(section('claim', 'What it claims, and where it stops',
    h('div', { class: 'limit prose' }, h('span', { class: 'limit__label' }, 'Where its claim stops'), claim.claim_ceiling_restated || claim.claim_ceiling || 'No limit is recorded.'),
    claim.claim_ceiling && claim.claim_ceiling_restated ? h('p', { class: 'note prose' }, `The registry's own wording: “${claim.claim_ceiling}”`) : null,
    h('h3', {}, 'How it is backed'),
    h('ul', { class: 'facts prose' },
      h('li', { class: 'fact' }, backingGlyph(backing, formal ? 'mark--proved' : 'mark'), h('span', {}, BACKING_WORDS[backing] || classWords('evidence_class', cls.evidence_class),
        h('span', { class: 'fact__caution' }, 'Evidence class ', h('code', {}, cls.evidence_class)))),
      h('li', { class: 'fact' }, keyGlyph('record'), h('span', {}, classWords('truth_accounting_bucket', cls.truth_accounting_bucket),
        h('span', { class: 'fact__caution' }, 'Saved-evidence bucket ', h('code', {}, cls.truth_accounting_bucket)))))));

  const guideRef = detail.guide?.ref;
  const contract = section('contract', formal ? 'The modeled contract' : 'No modeled contract');
  if (formal) {
    for (const sub of detail.subclaims) {
      contract.append(
        h('p', { class: 'statement prose' }, sub.statement),
        h('div', { class: 'split prose' },
          h('div', {}, h('h3', {}, 'Input model'), h('p', { class: 'small' }, sub.input_model)),
          h('div', {}, h('h3', {}, 'Assumptions'), h('p', { class: 'small' }, sub.assumptions))),
        h('div', { class: 'limit prose' }, h('span', { class: 'limit__label' }, 'What the model leaves out'), sub.limits),
        h('h3', {}, 'Specification and entry theorems'),
        refList([...(sub.specification_refs || []), ...(sub.entry_theorem_refs || [])]),
        h('h3', {}, 'Tests through the caller'),
        refList([sub.positive_test_ref, sub.adversarial_test_ref].filter(Boolean)),
        h('ul', { class: 'facts prose' },
          factItem('requirements_review', sub.requirements_review?.status, keyGlyph('absent')),
          factItem('host_tests', facets.host_tests?.status, keyGlyph('caller'))),
        h('p', { class: 'note prose' }, 'The contract covers this selected computation only. ', stateWords('formal_contract', facets.formal_contract?.status)[1] || ''));
    }
  } else {
    contract.append(h('p', { class: 'prose' }, stateWords('formal_contract', facets.formal_contract?.status)[0], ' Its evidence is the declared replay and the saved records below.'));
  }
  steps$.append(contract);

  if (formal) {
    for (const view of detail.proofs) {
      const p = view.proof || {};
      steps$.append(section('proof', `Retained proof: ${moduleWords(p.module)}`,
        h('ul', { class: 'facts prose' },
          h('li', { class: 'fact' }, keyGlyph('task'), h('span', {}, `Dafny ${String(p.retained_verification?.dafny_version || '').split('+')[0]} verified ${count(p.retained_verification?.verified_tasks || 0, 'task')} in the retained record.`,
            h('span', { class: 'fact__caution' }, 'A recorded result, not a prover run during this view.'))),
          h('li', { class: 'fact' }, keyGlyph('variant'), h('span', {}, `${count((p.negative_controls || []).length, 'deliberately broken variant')} failed verification in the retained record.`)),
          factItem('fresh_prover', p.fresh_prover_result?.status, keyGlyph('absent'))),
        h('div', { class: 'actions' }, h('a', { class: 'btn btn--ink', href: `/proofs/${encodeURIComponent(p.proof_id)}`, 'data-route': '' }, 'Read the proof'))));
      steps$.append(section('generated', 'Generated code',
        h('p', { class: 'prose small' }, 'The Python that the application calls was compiled from the verified Dafny. These files matched their recorded hashes when the index was built.'),
        refList(p.generated_refs || []),
        h('ul', { class: 'facts prose' }, factItem('proof_binding', p.current_binding?.status, keyGlyph('generated')),
          factItem('current_backend_binding', view.current_backend_binding?.status, keyGlyph('absent')))));
      steps$.append(section('caller', 'The application caller',
        h('p', { class: 'prose small' }, 'The component\'s own code normalizes its inputs into the model and calls the generated computation. The adapter, worker and host remain trusted; they are outside the proof.'),
        h('h3', {}, 'Callers'), refList(facets.generated_runtime_binding?.consumer_refs || []),
        h('h3', {}, 'Adapter and trusted host'), refList([p.adapter_ref, ...(p.trusted_host_refs || [])].filter(Boolean))));
    }
  }

  const replay = detail.replay || {};
  const argv = replay.primary_execution?.argv;
  const replayCmd = Array.isArray(argv) ? argv.join(' ') : '';
  steps$.append(section('replay', 'The declared replay',
    h('p', { class: 'prose' }, stateWords('replay', facets.replay?.status)[0], ' ', stateWords('replay', facets.replay?.status)[1] || ''),
    replayCmd ? h('div', { class: 'prose' }, h('h3', {}, 'Replay this component'), h('code', { class: 'cmd' }, replayCmd), copyButton(replayCmd)) : null,
    replay.guide_example?.command ? h('div', { class: 'prose' }, h('h3', {}, 'The guide\'s historical example'),
      h('p', { class: 'note' }, 'Quoted from the component atlas; it may write to retained receipt paths.'),
      h('code', { class: 'cmd' }, replay.guide_example.command), copyButton(replay.guide_example.command)) : null,
    h('div', { class: 'split prose' },
      h('div', {}, h('h3', {}, 'Input'), refList([replay.input_ref].filter(Boolean))),
      h('div', {}, h('h3', {}, 'Runner'), refList([replay.runner_ref].filter(Boolean)))),
    h('h3', {}, 'The last saved run'),
    h('p', { class: 'prose' }, lastRunWords(replay.last_result)),
    guideRef ? h('div', { class: 'prose' }, h('h3', {}, 'Reading guide'), refList([guideRef])) : null));

  const recordList = h('ul', { class: 'ref-list prose' });
  for (const r of receipts.items || []) {
    const [words, ok] = availabilityWords(r);
    recordList.append(h('li', {}, h('span', { class: ok ? 'ref' : 'ref absent' }, r.ref || r.artifact_id), h('br'),
      h('span', { class: 'muted' }, words, r.identity_status === 'not_read_by_index' ? ' The index did not read its contents.' : '')));
  }
  steps$.append(section('records', `Saved records (${(receipts.items || []).length})`,
    h('p', { class: 'prose small' }, 'Records the index lists for this component. An available record shows that the file is in this snapshot, not that its contents prove the claim or are current. An unavailable one is named without a link.'),
    recordList,
    receipts.next_cursor ? h('p', { class: 'note' }, `The API holds ${receipts.total} records; the first ${receipts.items.length} are shown.`) : null,
    h('details', { class: 'prose' }, h('summary', {}, `All ${count((detail.artifacts || []).length, 'indexed artifact')}`),
      refList((detail.artifacts || []).map((a) => a.ref || a.artifact_id), (detail.artifacts || []).map((a) => a.availability !== 'available')))));

  steps$.append(section('open', 'What this page does not establish',
    h('ul', { class: 'facts prose' },
      factItem('whole_claim', facets.whole_claim?.status, keyGlyph('absent')),
      factItem('requirements_review', facets.requirements_review?.status, keyGlyph('absent')),
      factItem('fresh_replay', detail.evidence_state?.fresh_replay?.status, keyGlyph('absent')),
      factItem('current_backend_binding', detail.evidence_state?.current_backend_binding?.status, keyGlyph('absent'))),
    h('div', { class: 'actions' },
      h('a', { class: 'btn', href: withQuery('/graph', { type: 'organ', id }), 'data-route': '' }, 'Related records'),
      h('a', { class: 'btn', href: `/#o=${encodeURIComponent(`comp:${id}`)}`, 'data-route': '' }, 'Show it on the map'))));

  page.replaceChildren(
    h('nav', { class: 'trail', 'aria-label': 'Breadcrumb' },
      h('a', { href: '/', 'data-route': '' }, 'Evidence map'), h('span', { 'aria-hidden': 'true' }, '/'),
      h('a', { href: withQuery('/catalogue', { family: cls.family }), 'data-route': '' }, FAMILY_NAME[cls.family] || cls.family), h('span', { 'aria-hidden': 'true' }, '/'),
      h('span', {}, detail.component_id)),
    h('h1', { class: 'page-title' }, card.title || id),
    h('p', { class: 'page-lede' }, card.summary || ''),
    h('p', { class: 'note figures' }, `Snapshot ${revision.slice(0, 12)} of the component index. A digest, not a Git commit or a proof.`),
    h('div', { class: 'reader' }, steps$, h('div', { class: 'reader__figure' }, figure.el)));

  figure.onPick((sid) => {
    const target = document.getElementById(`s-${sid}`);
    if (target) target.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  });
  const stop = followSections(sections, (sid) => figure.setCurrent(sid));
  return () => stop();
}

function refList(refs, absentFlags = []) {
  const list = h('ul', { class: 'ref-list' });
  refs.forEach((ref, i) => list.append(h('li', {}, h('span', { class: absentFlags[i] ? 'ref absent' : 'ref' }, ref), absentFlags[i] ? h('span', { class: 'muted' }, ' (not in this snapshot)') : null)));
  if (!refs.length) list.append(h('li', { class: 'muted' }, 'None recorded.'));
  return list;
}

export function failure(error, id) {
  const wrap = h('div', {});
  if (error.kind === 'not_found') {
    wrap.append(h('h1', { class: 'page-title' }, 'No component with this ID'),
      h('p', { class: 'page-lede' }, `The index has no component “${id}”. IDs come from the component registry; they are not derived from titles.`));
  } else if (error.kind === 'network') {
    wrap.append(h('h1', { class: 'page-title' }, 'The component API is not reachable'),
      h('p', { class: 'page-lede' }, 'Start it with ', h('code', {}, 'PYTHONPATH=src python3 -m plectis serve-components'), ', then reload this page.'));
  } else if (error.kind === 'schema') {
    wrap.append(h('h1', { class: 'page-title' }, 'An API this explorer cannot read'), h('p', { class: 'page-lede' }, error.message));
  } else if (error.kind === 'revision') {
    wrap.append(h('h1', { class: 'page-title' }, 'The index changed while loading'),
      h('p', { class: 'page-lede' }, 'The parts of this page came from different snapshots twice, so none of them is shown. ', h('a', { href: window.location.href, 'data-route': '' }, 'Load it again'), '.'));
  } else {
    wrap.append(h('h1', { class: 'page-title' }, 'This page could not be loaded'), h('p', { class: 'page-lede' }, error.message));
  }
  wrap.append(h('div', { class: 'actions' }, h('a', { class: 'btn', href: '/', 'data-route': '' }, 'Open the evidence map'), h('a', { class: 'btn', href: '/catalogue', 'data-route': '' }, 'Search the catalogue')));
  return wrap;
}

export { dayWords };
