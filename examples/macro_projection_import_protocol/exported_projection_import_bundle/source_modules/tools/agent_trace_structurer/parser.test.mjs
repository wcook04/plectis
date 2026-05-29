import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';

import { buildAttachmentClip, classifyClipboardText, parseAgentTrace } from './parser.mjs';

function utf8Bytes(value) {
  return new TextEncoder().encode(value).length;
}

function restoreSingleJsonClip(clip) {
  return clip.source_segments.map((segment) => segment.text).join('');
}

function sha16(value) {
  return createHash('sha256').update(value).digest('hex').slice(0, 16);
}

test('indexes Claude-style embedded file artifacts without dropping source lines', () => {
  const text = [
    'Ran',
    'Find routes',
    'Bash',
    '$ grep -rn "routes" system/server/ui/src',
    'system/server/ui/src/pages/StationLens.tsx:71:<Route path="/station/routes" />',
    'Created',
    'NavigationFreshnessGateScene.tsx',
    '+266',
    '-0',
    '/Users/example/src/ai_workflow/system/server/ui/src/components/station/NavigationFreshnessGateScene.tsx',
    '// [PURPOSE] Navigation freshness gate scene wrapper for /station/routes.',
    'import React from "react";',
    'type Props = { phaseRef: string | null };',
    'export default function NavigationFreshnessGateScene({ phaseRef }: Props) {',
    '  return <section data-capture-label="route_graph_check">{phaseRef}</section>;',
    '}',
    'Edited',
    'StationLens.tsx',
    '+1',
    '-0',
    '/Users/example/src/ai_workflow/system/',
    'server/ui/src/pages/StationLens.tsx',
    "import NavigationFreshnessGateScene from '../components/station/NavigationFreshnessGateScene';",
    'Updated todos',
  ].join('\n');

  const packet = parseAgentTrace(text, 'claude-sample.txt', '2026-05-08T13:27:27Z');

  assert.equal(packet.source_profile.detected_trace_format, 'claude_tool_trace');
  assert.equal(packet.continuation_view.provider_reading_mode.provider_family, 'claude');
  assert.equal(packet.source.input_lines, packet.source_lines.length);
  assert.equal(packet.source_text, text);
  assert.equal(packet.lossless_source.source_text_complete, true);
  assert.equal(packet.handoff_view.source_integrity.source_lines_complete, true);
  assert.equal(packet.handoff_view.source_integrity.exact_wording_authority, 'source_text');
  assert.equal(packet.handoff_view.source_integrity.line_range_authority, 'source_lines');
  assert.equal(packet.compression_view.source_integrity.source_line_count, packet.source.input_lines);
  assert.equal(packet.summary.artifacts, 2);
  assert.equal(packet.navigation_view.long_clip_strategy.chunks_cover_all_lines, true);
  assert.ok(packet.summary.source_chunks >= 1);
  assert.equal(packet.artifacts[0].kind, 'file_created');
  assert.equal(packet.artifacts[0].language, 'tsx');
  assert.equal(packet.artifacts[0].content_line_range.start, 11);
  assert.equal(packet.artifacts[0].change_stats.additions, 266);
  assert.equal(
    packet.artifacts[1].path,
    '/Users/example/src/ai_workflow/system/server/ui/src/pages/StationLens.tsx',
  );
  assert.equal(packet.query_index.top_artifacts.length, 2);
});

test('keeps Codex-style traces timeline-oriented', () => {
  const text = [
    'Execution mode: direct_local. I am using the repo bootstrap route first.',
    'Explored 3 files',
    'Read AGENTS.override.md',
    'Read CODEX.md',
    'Ran command',
    '$ ./repo-python kernel.py --pulse',
    'KERNEL PULSE',
    '  repo: ai_workflow',
    'Success',
  ].join('\n');

  const packet = parseAgentTrace(text, 'codex-sample.txt', '2026-05-08T13:28:23Z');

  assert.equal(packet.source_profile.detected_trace_format, 'codex_tool_trace');
  assert.equal(packet.continuation_view.provider_reading_mode.provider_family, 'codex');
  assert.equal(packet.handoff_view.detected_shape.provider_specificity.includes('best_effort'), true);
  assert.equal(packet.handoff_view.coverage.timeline_events, packet.summary.events);
  assert.equal(packet.summary.artifacts, 0);
  assert.ok(packet.summary.events >= 4);
  assert.equal(packet.source.input_lines, packet.source_lines.length);
  assert.equal(packet.navigation_view.source_authority.exact_text, 'source_text');
  assert.equal(packet.query_index.top_chunks.length, packet.summary.source_chunks);
});

test('extracts Codex final assistant message before trailing edit review cards', () => {
  const text = [
    'Worked for 8m 41s',
    'Execution mode: direct_local. I am using the repo bootstrap route plus the public-microcosm-evolution-seed skill.',
    '',
    '',
    'Explored 2 files, ran 2 commands',
    'Live HEAD is now 4bda7ed65be6fa8530a9a475b73c4c07e2100e6e, so the prior handle is historical.',
    '',
    '',
    'Ran 5 commands',
    'Context automatically compacted',
    'I am resuming from the committed pattern-ledger import pass.',
    '',
    '',
    'Ran 3 commands',
    'Target chosen: ledger_row_metadata_projection in macro_projection_import_protocol, because it still accepted a real available macro ledger as metadata/source references instead of importing the public body.',
    '',
    'Classification before edit: copied_non_secret_macro_body_with_provenance.',
    '',
    'Changed files:',
    '',
    'projection_protocol.json',
    'import_plan.json',
    'pattern_ledger_rows.jsonl',
    'test_macro_projection_import_protocol.py',
    'Real substrate replacement: copied the full 373-row non-secret macro pattern ledger with exact digest provenance sha256:414fad0ac5f8473503a7852bf6a9a57ae5025d1084577a58e893220e3aabbbf3.',
    '',
    'Validation passed:',
    '',
    './repo-pytest microcosm-substrate/tests/test_macro_projection_import_protocol.py -> 13 passed',
    'py_compile for touched test and relevant Microcosm modules',
    'JSON parsing for touched import/protocol JSON',
    ...Array.from({ length: 34 }, (_, index) => `Validation detail ${index + 1}: retained closeout evidence row for the trace extractor body.`),
    'MIDDLE_REQUIRED_CLOSEOUT_DETAIL: keep this detail in the bounded body instead of hiding it behind a tiny excerpt.',
    'git diff --check',
    'Committed with scoped lane: 3cec6724937105c0c54d2598d5ca15a0aef8ad5f (Import Microcosm pattern ledger body).',
    '',
    'Residual WorkItem/cap id: none for this dent. Unrelated dirt left untouched.',
    '',
    '',
    'Edited 5 files',
    '+154',
    '-30',
    'Undo',
    'Review',
    'microcosm-substrate/examples/macro_projection_import_protocol/exported_projection_import_bundle/projection_protocol.json',
    '',
    '5:25 AM',
  ].join('\n');

  const packet = parseAgentTrace(text, 'codex-ui-final-message-sample.txt', '2026-05-23T05:25:00Z');
  const clip = buildAttachmentClip(packet, { disable_raw_sidecar_fallback: true });
  const finalMessage = packet.continuation_view.final_assistant_message;

  assert.equal(packet.source_profile.detected_trace_format, 'codex_tool_trace');
  assert.equal(finalMessage.status, 'source_claimed');
  assert.equal(finalMessage.source, 'codex_ui_post_activity_message');
  assert.equal(finalMessage.schema_version, 'agent_trace_final_assistant_message_v1');
  assert.equal(finalMessage.body_is_complete, true);
  assert.equal(finalMessage.omitted_char_count, 0);
  assert.ok(finalMessage.body.length > 2000);
  assert.ok(finalMessage.body.length <= finalMessage.body_char_limit);
  assert.ok(finalMessage.body.includes('Target chosen: ledger_row_metadata_projection'));
  assert.ok(finalMessage.body.includes('MIDDLE_REQUIRED_CLOSEOUT_DETAIL'));
  assert.ok(finalMessage.body.includes('Residual WorkItem/cap id: none'));
  assert.equal(finalMessage.body.includes('Edited 5 files'), false);
  assert.equal(finalMessage.body.includes('5:25 AM'), false);
  assert.ok(finalMessage.summary.length <= 700);
  assert.equal(finalMessage.recovery.source_authority, 'source_text/source_lines');
  assert.deepEqual(clip.terminal_state_index.final_assistant_message.line_range, finalMessage.line_range);
  assert.equal(clip.terminal_state_index.final_assistant_message.body.includes('MIDDLE_REQUIRED_CLOSEOUT_DETAIL'), true);
  assert.equal(clip.terminal_state_index.final_closeout_prose.body_ref, 'terminal_state_index.final_assistant_message');
  assert.ok(clip.terminal_state_index.final_closeout_prose.summary.includes('Target chosen'));
  assert.equal(clip.terminal_state_index.final_closeout_prose.summary.includes('Edited 5 files'), false);
});

test('keeps generated trace-paste sessions as tool traces without file artifacts', () => {
  const text = [
    '# codex session fixture turn 3',
    'cwd: /Users/example/src/ai_workflow',
    'started: 2026-05-18T01:41:11.525Z',
    'completed: 2026-05-18T01:48:47.700Z',
    'status: complete',
    '',
    '# prompt_omitted chars=7082 sha16=e587a2bce5b21c8e',
    '',
    'Ran',
    'exec_command (1/2)',
    'Bash',
    "$ sed -n '1,12p' AGENTS.override.md",
    'Chunk ID: 84f5e1',
    'Wall time: 0.0002 seconds',
    'Process exited with code 0',
    'Output:',
    '# AGENTS.override.md - Codex Discovery Seed',
    'importantly this markdown output is evidence, not a standalone source file',
    'Success',
    'Ran',
    'exec_command (2/2)',
    'Bash',
    '$ ./repo-python kernel.py --pulse',
    'KERNEL PULSE',
    '  repo: ai_workflow',
    'Success',
  ].join('\n');

  const packet = parseAgentTrace(text, 'clip-fixture-agent_trace-abcd1234.json', '2026-05-18T01:49:00Z');

  assert.equal(packet.source_profile.detected_trace_format, 'codex_tool_trace');
  assert.notEqual(packet.artifacts[0]?.kind, 'standalone_source_file');
  assert.ok(packet.trace_blocks.some((block) => block.kind === 'command_run'));
  assert.ok(packet.summary.events >= 4);
});

test('recognizes standalone copied source as a navigable artifact', () => {
  const text = [
    '// [PURPOSE] A copied source file, not a thread.',
    'import React from "react";',
    'type Props = { label: string };',
    'export default function Scene({ label }: Props) {',
    '  return <section>{label}</section>;',
    '}',
  ].join('\n');

  const packet = parseAgentTrace(text, 'clipboard-capture.json', '2026-05-08T13:16:54Z');

  assert.equal(packet.source_profile.detected_trace_format, 'standalone_source_file');
  assert.equal(packet.source_profile.primary_content_kind, 'source_file');
  assert.equal(packet.ai_parse_contract.read_order.includes('handoff_view'), true);
  assert.equal(packet.summary.artifacts, 1);
  assert.equal(packet.artifacts[0].kind, 'standalone_source_file');
  assert.equal(packet.artifacts[0].language, 'tsx');
  assert.equal(packet.artifacts[0].content_line_range.start, 1);
  assert.equal(packet.source_text, text);
});

test('preserves raw source text exactly and adds chunk and pattern maps for long mixed captures', () => {
  const repeatedCloseout = [
    'navigation_seed_used: AGENTS.override.md -> CODEX.md -> AGENTS.md -> kernel --pulse',
    'general_artifacts_checked: agent_trace_structurer parser contract',
    'refinement_result: clip compiler refined',
    'plane_home: agent trace structurer',
    'discoverability_refresh: parser.test.mjs',
  ].join('\r\n');
  const sections = Array.from({ length: 18 }, (_, index) => [
    `Seed ${String.fromCharCode(65 + (index % 3))} — specimen ${index + 1}`,
    'This is long operator or agent context that should remain raw, browsable, and non-destructive.',
    repeatedCloseout,
    index % 4 === 0 ? 'Sunday 6:01 AM' : '',
  ].join('\r\n'));
  const text = `${sections.join('\r\n\r\n')}\r\n`;

  const packet = parseAgentTrace(text, 'long-mixed-capture.txt', '2026-05-10T23:09:55Z');

  assert.equal(packet.source_text, text);
  assert.equal(packet.lossless_source.line_breaks.style, 'crlf');
  assert.equal(packet.lossless_source.line_breaks.ends_with_line_break, true);
  assert.equal(packet.lossless_source.source_text_bytes, new TextEncoder().encode(text).length);
  assert.equal(packet.lossless_source.source_lines_are_navigation_projection, true);
  assert.ok(packet.source_chunks.length > 1);
  assert.equal(packet.navigation_view.long_clip_strategy.raw_text_preserved, true);
  assert.equal(packet.navigation_view.long_clip_strategy.chunks_cover_all_lines, true);
  assert.ok(packet.pattern_index.repeated_line_prefixes.some((row) => row.value === 'navigation_seed_used'));
  assert.ok(packet.pattern_index.repeated_line_prefixes.some((row) => row.value === 'refinement_result'));
  assert.ok(packet.pattern_index.time_markers.length > 0);
  assert.ok(packet.query_index.top_chunks.length > 1);
});

test('builds lossless segmented clips without duplicating raw source text', () => {
  const repeated = Array.from({ length: 360 }, (_, index) => [
    `operator note ${index + 1}: repeated structure should be mined, not pasted wholesale`,
    `navigation_seed_used: rung-${index % 5}`,
    `refinement_result: pattern-${index % 3}`,
  ].join('\n')).join('\n');
  const text = `${repeated}\nFINAL_RAW_SENTINEL_should_be_preserved_once_in_segments`;
  const packet = parseAgentTrace(text, 'long-attachment-capture.txt', '2026-05-10T23:09:55Z');
  const clip = buildAttachmentClip(packet, {
    full_packet_path: '/tmp/full.json',
    raw_source_path: '/tmp/raw.txt',
    clip_store_path: '/tmp/clip.json',
    disable_raw_sidecar_fallback: true,
  });
  const serialized = JSON.stringify(clip);
  const reconstructed = restoreSingleJsonClip(clip);
  const sourceBytes = utf8Bytes(text);
  const clipBytes = utf8Bytes(serialized);

  assert.equal(clip.schema_version, 'agent_trace_lossless_clip_v2');
  assert.equal(clip.carrier_mode, 'single_json');
  assert.equal(clip.clip_contract.schema_version, 'agent_trace_clip_contract_v1');
  assert.equal(clip.clip_contract.standard_ref, 'codex/standards/std_agent_trace_lossless_clip.json');
  assert.equal(clip.clip_contract.source_authority_field, 'source_segments[].text');
  assert.ok(clip.clip_contract.required_fields.includes('reader_index'));
  assert.ok(clip.clip_contract.required_fields.includes('command_ledger'));
  assert.ok(clip.clip_contract.required_fields.includes('terminal_state_index'));
  assert.ok(clip.clip_contract.required_fields.includes('validation_matrix'));
  assert.ok(clip.clip_contract.required_fields.includes('artifact_delta_index'));
  assert.ok(clip.clip_contract.required_fields.includes('long_line_index'));
  assert.equal(clip.reader_index.schema_version, 'agent_trace_clip_reader_index_v1');
  assert.equal(clip.reader_index.compaction_hints.schema_version, 'agent_trace_compaction_hints_v1');
  assert.ok(clip.reader_index.compaction_hints.specimen_vs_target.includes('trace is specimen'));
  assert.ok(clip.reader_index.compaction_hints.section_gate.includes('restart delta'));
  assert.ok(clip.reader_index.compaction_hints.example_guard.includes('specimens'));
  assert.ok(clip.reader_index.compaction_hints.schema_overfit_guard.includes('smallest output shape'));
  assert.equal(clip.command_ledger.schema_version, 'agent_trace_command_ledger_v1');
  assert.equal(clip.terminal_state_index.schema_version, 'agent_trace_terminal_state_index_v1');
  assert.equal(clip.validation_matrix.schema_version, 'agent_trace_validation_matrix_v1');
  assert.equal(clip.artifact_delta_index.schema_version, 'agent_trace_artifact_delta_index_v1');
  assert.equal(clip.long_line_index.schema_version, 'agent_trace_long_line_index_v1');
  assert.equal(clip.reader_index.source_shape.source_line_count, packet.source.input_lines);
  assert.equal(clip.reader_index.source_shape.source_byte_count, sourceBytes);
  assert.ok(clip.reader_index.source_segment_ranges.length > 0);
  assert.ok(clip.navigation_tutorial.read_order.includes('reader_index'));
  assert.ok(clip.navigation_tutorial.read_order.includes('command_ledger'));
  assert.ok(clip.navigation_tutorial.read_order.includes('terminal_state_index'));
  assert.ok(clip.navigation_tutorial.read_order.includes('clip_contract'));
  assert.ok(clip.reader_contract.read_order.includes('reader_index'));
  assert.ok(clip.reader_contract.read_order.includes('validation_matrix'));
  assert.ok(clip.reader_contract.read_order.includes('artifact_delta_index'));
  assert.ok(clip.reader_contract.read_order.includes('clip_contract'));
  assert.ok(clip.reader_contract.continuation_selection_rule.includes('do not expand all source ranges'));
  assert.equal(Object.hasOwn(clip, 'source_text'), false);
  assert.equal(Object.hasOwn(clip, 'source_lines'), false);
  assert.equal(Object.hasOwn(clip, 'source_excerpt'), false);
  assert.equal(reconstructed, text);
  assert.equal(clip.source_integrity.exact_source_text_in_attachment, true);
  assert.equal(clip.source_integrity.source_text_attachment_field, 'source_segments[].text');
  assert.equal(clip.navigation_tutorial.commands.restore_jq.includes("source_segments"), true);
  assert.equal(clip.local_capture.retention_limit, 10);
  assert.equal(clip.local_capture.refs_available.raw_source, true);
  assert.equal(clip.local_capture.refs_available.full_packet, true);
  assert.equal(clip.local_capture.refs_available.private_clip, true);
  assert.equal(clip.local_capture.public_export_contains_local_paths, false);
  assert.equal(Object.hasOwn(clip.local_capture, 'paths'), false);
  assert.equal(clip.source_integrity.source_text_hash, packet.lossless_source.source_text_hash);
  assert.equal(clip.omission_receipt.omitted.source_text, 0);
  assert.equal(clip.omission_receipt.omitted.duplicate_source_text_string, text.length);
  assert.ok(clip.source_segment_index.segment_count > 0);
  assert.ok(clip.source_segments.length > 0);
  assert.ok(clip.source_segments.every((segment) => segment.byte_range_utf8));
  assert.equal(clip.navigation_manifest?.source_line_samples, undefined);
  assert.ok(serialized.length < JSON.stringify(packet).length);
  assert.ok(clipBytes > 0);
  assert.equal(clip.size_policy.raw_source_bytes, sourceBytes);
  assert.equal(clip.size_policy.carrier_decision, 'single_json');
});

test('lossless attachment clips preserve CRLF, no-final-newline, and Unicode source', () => {
  const fixtures = [
    'alpha\r\nbeta\r\ngamma\r\n',
    'no final newline\r\nwith crlf',
    'unicode 😀 café\rbare-cr\nmixed',
  ];

  for (const text of fixtures) {
    const packet = parseAgentTrace(text, 'line-ending-fixture.txt', '2026-05-11T02:40:00Z');
    const clip = buildAttachmentClip(packet);
    assert.equal(clip.carrier_mode, 'single_json');
    assert.equal(restoreSingleJsonClip(clip), text);
    assert.equal(clip.source_integrity.source_text_bytes, utf8Bytes(text));
  }
});

test('splits huge single lines into mid-line byte ranges without losing content', () => {
  const text = `${'long_line_'.repeat(9000)}END`;
  const packet = parseAgentTrace(text, 'huge-single-line.txt', '2026-05-11T02:41:00Z');
  const clip = buildAttachmentClip(packet);
  const midLineSegments = clip.source_segment_index.segments.filter(
    (segment) => segment.starts_mid_line || segment.ends_mid_line,
  );

  assert.equal(clip.carrier_mode, 'single_json');
  assert.equal(restoreSingleJsonClip(clip), text);
  assert.ok(clip.source_segments.length > 1);
  assert.ok(midLineSegments.length > 0);
  assert.equal(clip.source_segment_index.segments.at(-1).byte_range_utf8.end, utf8Bytes(text));
  assert.equal(clip.long_line_index.long_line_count, 1);
  assert.equal(clip.long_line_index.rows[0].line, 1);
  assert.ok(clip.long_line_index.rows[0].segment_ids.length > 1);
});

test('hostile JSON-string escaping switches to raw sidecar index instead of breaching size budget', () => {
  const sentinel = 'HOSTILE_RAW_SENTINEL_only_raw_sidecar_should_have_this';
  const line = `{"path":"C:\\\\tmp\\\\quoted","quote":"${'\\"'.repeat(18)}","slash":"${'\\\\'.repeat(28)}"}`;
  const text = `${Array.from({ length: 900 }, (_, index) => `${line},"i":${index}`).join('\n')}\n${sentinel}`;
  const packet = parseAgentTrace(text, 'hostile-json-like.txt', '2026-05-11T02:42:00Z');
  const clip = buildAttachmentClip(packet);
  const serialized = JSON.stringify(clip);

  assert.equal(clip.schema_version, 'agent_trace_lossless_clip_v2');
  assert.equal(clip.carrier_mode, 'raw_sidecar_plus_index');
  assert.equal(clip.clip_contract.schema_version, 'agent_trace_clip_contract_v1');
  assert.equal(clip.clip_contract.source_authority_field, 'raw_sidecar.filename');
  assert.ok(clip.clip_contract.parse_order.includes('raw_sidecar'));
  assert.equal(clip.reader_index.schema_version, 'agent_trace_clip_reader_index_v1');
  assert.equal(clip.command_ledger.schema_version, 'agent_trace_command_ledger_v1');
  assert.equal(clip.terminal_state_index.schema_version, 'agent_trace_terminal_state_index_v1');
  assert.ok(clip.navigation_tutorial.read_order.includes('reader_index'));
  assert.ok(clip.navigation_tutorial.read_order.includes('command_ledger'));
  assert.ok(clip.navigation_tutorial.read_order.includes('clip_contract'));
  assert.ok(clip.reader_contract.read_order.includes('reader_index'));
  assert.ok(clip.reader_contract.read_order.includes('clip_contract'));
  assert.equal(Object.hasOwn(clip, 'source_segments'), false);
  assert.equal(Object.hasOwn(clip, 'source_text'), false);
  assert.equal(Object.hasOwn(clip, 'source_lines'), false);
  assert.equal(Object.hasOwn(clip, 'source_excerpt'), false);
  assert.equal(serialized.includes(sentinel), false);
  assert.equal(clip.raw_sidecar.byte_count_utf8, utf8Bytes(text));
  assert.equal(clip.size_policy.carrier_decision, 'raw_sidecar_plus_index');
  assert.equal(clip.size_policy.reason, 'json_string_escape_overhead_exceeds_ratio_budget');
  assert.ok(clip.size_policy.attempted_single_json_bytes > clip.size_policy.budget_bytes);
  assert.equal(clip.size_policy.export_bytes, utf8Bytes(serialized) + utf8Bytes(text));
  assert.ok(clip.size_policy.export_bytes <= clip.size_policy.budget_bytes);
  assert.equal(clip.source_segment_index.segments.at(-1).byte_range_utf8.end, utf8Bytes(text));
});

test('trace density fixture records current fidelity and projection boundaries', () => {
  const providerJsonl = [
    JSON.stringify({
      provider: 'codex',
      session_id: 'fixture-session',
      event: 'raw_provider_event',
      bytes_are_authority: true,
    }),
    JSON.stringify({
      provider: 'codex',
      session_id: 'fixture-session',
      event: 'tool_output',
      payload: { raw_only_sentinel: 'PROVIDER_JSONL_ONLY_SENTINEL' },
    }),
  ].join('\n') + '\n';
  const hostileLine = `{"path":"C:\\\\tmp\\\\quoted","quote":"${'\\"'.repeat(18)}","slash":"${'\\\\'.repeat(28)}"}`;
  const longOutput = Array.from(
    { length: 900 },
    (_, index) => `${hostileLine},"fixture_output_line":${index}`,
  ).join('\n');
  const tracePaste = [
    'Execution mode: direct_local.',
    'Ran',
    'Collect trace density fixture',
    'Bash',
    '$ ./repo-python kernel.py --pulse',
    longOutput,
    'Success',
    'Ran',
    'Validate parser fixture',
    'Bash',
    '$ node --test tools/agent_trace_structurer/parser.test.mjs',
    'tests 1 passed',
    'Success',
    'navigation_seed_used: AGENTS.override.md -> CODEX.md -> AGENTS.md',
    'general_artifacts_checked: std_agent_trace_lossless_clip.json, parser.mjs',
    'refinement_result: trace density fixture refined',
    'plane_home: agent trace structurer',
    'discoverability_refresh: node --test tools/agent_trace_structurer/parser.test.mjs',
  ].join('\n');

  const packet = parseAgentTrace(tracePaste, 'density-fixture.trace-paste.txt', '2026-05-17T05:20:00Z');
  const clip = buildAttachmentClip(packet, {
    full_packet_path: '/tmp/density-full.json',
    raw_source_path: '/tmp/density-trace-paste.txt',
    clip_store_path: '/tmp/density-clip.json',
  });
  const compactV0 = {
    ...Object.fromEntries(Object.entries(clip).filter(([key]) => key !== 'raw_sidecar')),
    schema_version: 'agent_trace_compact_json_v0',
    artifact_kind: 'agent_trace',
    density_tier: 2,
    variant: 'compact_json',
    sliced_from: clip.schema_version,
    standalone: false,
    capabilities: {
      standalone_for: [
        'navigate_copied_source_ranges',
        'inspect_bounded_indexes',
      ],
      requires_for: {
        exact_copied_source_reconstruction: ['agent_trace_lossless_clip_v2.raw_sidecar'],
        exact_provider_jsonl_reconstruction: ['provider_session_jsonl_source_v1'],
      },
    },
    omitted: {
      raw_sidecar: 1,
      reason: 'Current compact_json_v0 strips the raw sidecar from the lossless clip.',
      retrievable_in: 'agent_trace_lossless_clip_v2.raw_sidecar',
    },
  };
  const denoisedV0 = {
    schema_version: 'agent_trace_denoised_packet_v0',
    schema: 'agent_trace_denoised_packet_v0',
    artifact_kind: 'agent_trace',
    density_tier: 3,
    contract_state: 'defined',
    materialization_state: 'ready_for_handoff',
    replay_state: 'blocked_without_lossless_sources',
    promotion_gate: 'handoff_ready_not_replay_ready',
    sliced_from: clip.schema_version,
    slice_variant: 'denoised_v0_operator_summary',
    standalone: true,
    fidelity: {
      raw_source_reconstructable: false,
      model_lossless: false,
      copied_source_reconstructable: false,
      byte_lossless: false,
    },
    capabilities: {
      standalone_for: ['operational_handoff', 'next_move'],
      requires_for: {
        replay: [
          'agent_trace_compact_json_v2',
          'agent_trace_canonical_full_json_v1',
          'provider_session_jsonl_source_v1',
        ],
      },
    },
    not_standalone_for: ['replay', 'byte_reconstruction', 'raw_source_reconstruction'],
    omitted: {
      event_stream: true,
      large_bodies: true,
      retrievable_in: 'agent_trace_lossless_clip_v2 or provider_session_jsonl_source_v1',
    },
    terminal_state: clip.terminal_state_index,
    validation: clip.validation_matrix,
    commands: {
      command_count: clip.command_ledger.command_count,
      role_counts: clip.command_ledger.role_counts,
      status_counts: clip.command_ledger.status_counts,
    },
  };
  const catalogRow = {
    schema_version: 'agent_trace_catalog_row_v1',
    artifact_kind: 'agent_trace',
    density_tier: 4,
    mission_key: 'fixture-mission',
    provider: 'codex',
    session_id: 'fixture-session',
    latest_completed_turn: 1,
    source_sha16: sha16(providerJsonl),
    variants: {
      raw_jsonl: { tier: 0, availability: 'available', bytes: utf8Bytes(providerJsonl) },
      canonical_full: { tier: 1, availability: 'pending', reason: 'canonical core not yet split from reader projection' },
      compact: { tier: 2, availability: 'partial', bytes: utf8Bytes(JSON.stringify(compactV0)) },
      continuation: { tier: 3, availability: 'available', bytes: utf8Bytes(JSON.stringify(denoisedV0)) },
    },
  };
  const commandWithOutput = clip.command_ledger.records.find((row) => row.command === './repo-python kernel.py --pulse');
  const packetBytes = utf8Bytes(JSON.stringify(packet));
  const tracePasteBytes = utf8Bytes(tracePaste);
  const receipt = {
    schema_version: 'agent_trace_density_fixture_receipt_v0',
    source_provider_jsonl_bytes: utf8Bytes(providerJsonl),
    rendered_trace_paste_bytes: tracePasteBytes,
    tier1_canonical_core_bytes: null,
    tier1_reader_projection_bytes_if_any: packetBytes,
    tier2_compact_bytes: utf8Bytes(JSON.stringify(compactV0)),
    tier3_continuation_bytes: utf8Bytes(JSON.stringify(denoisedV0)),
    tier4_catalog_row_bytes: utf8Bytes(JSON.stringify(catalogRow)),
    source_sha16: sha16(providerJsonl),
    variant_sha16s: {
      rendered_trace_paste: sha16(tracePaste),
      current_structured_packet: sha16(JSON.stringify(packet)),
      lossless_clip_v2: sha16(JSON.stringify(clip)),
      compact_json_v0: sha16(JSON.stringify(compactV0)),
      denoised_packet_v0: sha16(JSON.stringify(denoisedV0)),
      catalog_row_v1: sha16(JSON.stringify(catalogRow)),
    },
    copied_source_reconstruction: {
      status: 'pass',
      carrier_mode: clip.carrier_mode,
      copied_source_reconstructable: true,
    },
    provider_jsonl_byte_reconstruction_from_tier1: {
      status: 'fail_expected',
      byte_lossless: false,
      reason: 'Tier 1 candidate is built from rendered trace-paste, not raw provider JSONL line-order bytes.',
    },
    long_blob_dedup_check: {
      status: 'fail_expected',
      reason: 'Current agent_trace_structured_v2 keeps source_text plus reader projections; canonical blob ownership is not split yet.',
    },
    tier2_excerpt_receipts_check: {
      status: commandWithOutput?.output_hash ? 'partial' : 'fail',
      output_hash_present: Boolean(commandWithOutput?.output_hash),
      original_byte_count_present: Object.hasOwn(commandWithOutput || {}, 'original_bytes'),
    },
    sibling_reachback_check: {
      status: 'pass',
      compact_requires_raw_sidecar: compactV0.capabilities.requires_for.exact_copied_source_reconstruction.includes(
        'agent_trace_lossless_clip_v2.raw_sidecar',
      ),
    },
    schema_validation_check: {
      status: 'pass',
      validated_by: 'node --test tools/agent_trace_structurer/parser.test.mjs',
    },
  };

  assert.equal(clip.carrier_mode, 'raw_sidecar_plus_index');
  assert.equal(clip.source_integrity.exact_source_text_in_attachment_bundle, true);
  assert.equal(clip.raw_sidecar.byte_count_utf8, tracePasteBytes);
  assert.equal(packet.source_text, tracePaste);
  assert.equal(receipt.copied_source_reconstruction.status, 'pass');
  assert.equal(receipt.provider_jsonl_byte_reconstruction_from_tier1.status, 'fail_expected');
  assert.equal(receipt.long_blob_dedup_check.status, 'fail_expected');
  assert.equal(receipt.tier2_excerpt_receipts_check.status, 'partial');
  assert.equal(receipt.tier2_excerpt_receipts_check.original_byte_count_present, false);
  assert.equal(receipt.sibling_reachback_check.status, 'pass');
  assert.ok(receipt.tier1_reader_projection_bytes_if_any > receipt.rendered_trace_paste_bytes);
  assert.equal(catalogRow.variants.canonical_full.availability, 'pending');
  assert.equal(clip.clip_contract.status_semantics.missing_required.includes('required'), true);
  assert.equal(
    clip.clip_contract.variant_contracts.denoised_v0_operator_summary.promotion_gate,
    'handoff_ready_not_replay_ready',
  );
  assert.equal(
    clip.clip_contract.variant_contracts.denoised_v0_operator_summary.replay_state,
    'blocked_without_lossless_sources',
  );
  assert.equal(denoisedV0.materialization_state, 'ready_for_handoff');
  assert.equal(denoisedV0.replay_state, 'blocked_without_lossless_sources');
  assert.equal(denoisedV0.capabilities.requires_for.replay.includes('provider_session_jsonl_source_v1'), true);
  assert.equal(denoisedV0.not_standalone_for.includes('replay'), true);
  assert.equal(compactV0.schema_version, 'agent_trace_compact_json_v0');
  assert.equal(compactV0.standalone, false);
});

test('adds provider-aware continuation cues without overfitting a Claude trace specimen', () => {
  const text = [
    'Paste this into Claude:',
    '',
    'Implement Root Navigator from the packet.',
    'Ran',
    'Run targeted tests',
    'Bash',
    '$ npm test',
    'Tests 5 passed',
    'Edited',
    'RootNavigator.tsx',
    '+10',
    '-0',
    '/Users/example/src/ai_workflow/system/server/ui/src/pages/RootNavigator.tsx',
    'export default function RootNavigator() {',
    '  return null;',
    '}',
    'Ran',
    'Check git status',
    'Bash',
    '$ git status --short -- system/server/ui/src/pages/RootNavigator.tsx system/server/ui/src/pages/__tests__/RootNavigator.test.tsx',
    'M  system/server/ui/src/pages/RootNavigator.tsx',
    '?? system/server/ui/src/pages/__tests__/RootNavigator.test.tsx',
  ].join('\n');

  const packet = parseAgentTrace(text, 'claude-root-navigator-specimen.txt', '2026-05-09T02:40:00Z');

  assert.equal(packet.source_profile.detected_trace_format, 'claude_tool_trace');
  assert.equal(packet.ai_parse_contract.read_order.includes('continuation_view'), true);
  assert.equal(packet.handoff_view.recommended_read_order[1], 'navigation_view');
  assert.equal(packet.handoff_view.recommended_read_order[2], 'continuation_view');
  assert.equal(packet.continuation_view.provider_reading_mode.provider_family, 'claude');
  assert.equal(packet.continuation_view.trace_shape.work_shape, 'implementation_validation_wave');
  assert.equal(packet.continuation_view.source_segments.mode, 'segmented_by_first_tool_activity');
  assert.equal(packet.continuation_view.source_segments.segments[0].id, 'initial_context');
  assert.equal(packet.continuation_view.source_segments.segments[0].line_range.end, 3);
  assert.equal(packet.continuation_view.state_cues.open_mutation_without_commit, true);
  assert.equal(packet.continuation_view.state_cues.git_cues.untracked_line_count, 1);
  assert.ok(
    packet.continuation_view.downstream_reader_rules.some((rule) => rule.includes('Do not overfit')),
  );
  assert.ok(
    packet.continuation_view.operator_intent_branches.some((branch) => branch.intent === 'improve_clip_compiler'),
  );
});

test('attaches B3 packet conformance warnings for malformed packet captures', () => {
  const text = [
    'PACKET v=3.2',
    'thread: malformed packet',
    'scope: specimen',
    'last_valid_state_per_source: not_stated',
    '',
    'hot_path:',
    'terminal_state: unindented',
    '  produced_artifacts: not_stated',
    '  active_decision_axes: not_stated',
    '  primary_affordance_surfaces: not_stated',
    '  validation_boundary: not_stated',
    '  workspace_boundary: not_stated',
    '  residuals: not_stated',
    '',
    'state_capsule:',
    '  pushed: not_stated',
    '',
    'produced_artifacts:',
    '* Star bullet',
    '',
    'operator_intent_signals:',
    '  - signal=none :: preserved_as=not_stated :: source=not_stated',
    '',
    'evidence_pointers:',
    '  - claim=bad evidence :: evidence=; source.name=clip',
    '',
    '  END_PACKET',
  ].join('\n');

  const packet = parseAgentTrace(text, 'b3-malformed-packet.txt', '2026-05-10T18:00:00Z');
  const clip = buildAttachmentClip(packet);

  assert.equal(packet.packet_conformance.status, 'issues');
  assert.ok(packet.packet_conformance.issue_codes.includes('invalid_star_list_marker'));
  assert.ok(packet.packet_conformance.issue_codes.includes('empty_evidence_value'));
  assert.ok(packet.packet_conformance.issue_codes.includes('hot_path_field_unindented'));
  assert.ok(packet.packet_conformance.issue_codes.includes('packet_end_not_column_1'));
  assert.ok(packet.packet_conformance.issue_codes.includes('sentinel_empty_row'));
  assert.equal(clip.reader_index.packet_conformance.status, 'issues');
  assert.ok(clip.reader_index.compaction_hints.schema_overfit_guard.includes('input evidence'));
  assert.equal(clip.reader_index.packet_outline.schema_version, 'b3_packet_outline_v1');
  assert.ok(
    clip.reader_index.packet_outline.sections.some((section) => section.section === 'hot_path'),
  );
  assert.ok(
    clip.reader_index.packet_outline.hot_path_fields.some((field) => field.field === 'produced_artifacts'),
  );
});

test('builds command, terminal, validation, and artifact indexes for B3 terminal commits', () => {
  const text = [
    'PACKET v=3.2',
    'thread: agent trace structurer fixture',
    'scope: fixture',
    'last_valid_state_per_source: committed source changes',
    '',
    'hot_path:',
    '  terminal_state: commit abc1234 landed',
    '  produced_artifacts: parser and standard',
    '  active_decision_axes: command ledger',
    '  primary_affordance_surfaces: command_ledger',
    '  validation_boundary: node test passed',
    '  workspace_boundary: scoped commit only',
    '  residuals: none',
    '',
    'Ran',
    'Run parser tests',
    'Bash',
    '$ node --test tools/agent_trace_structurer/parser.test.mjs',
    '✔ parser fixture (12ms)',
    'ℹ fail 0',
    'Success',
    'commit: `abc1234 agent-trace: add command ledger`',
    '1 file changed, 10 insertions(+), 1 deletion(-)',
    'navigation_seed_used: AGENTS.override.md -> CODEX.md -> AGENTS.md',
    'general_artifacts_checked: parser, standard, toolbar',
    'refinement_result: clip command ledger refined',
    'plane_home: agent trace structurer',
    'discoverability_refresh: node --test tools/agent_trace_structurer/parser.test.mjs',
    'END_PACKET',
  ].join('\n');
  const packet = parseAgentTrace(text, 'b3-terminal-commit.txt', '2026-05-13T09:30:00Z');
  const clip = buildAttachmentClip(packet);
  const command = clip.command_ledger.records.find((row) => row.command === 'node --test tools/agent_trace_structurer/parser.test.mjs');

  assert.equal(command.role, 'validation');
  assert.equal(command.status, 'pass');
  assert.equal(command.output_hash.length, 8);
  assert.equal(clip.validation_matrix.command_validation_count, 1);
  assert.equal(clip.terminal_state_index.latest_commit.hash, 'abc1234');
  assert.equal(clip.terminal_state_index.post_commit_status_checks.status, 'missing_required');
  assert.equal(
    clip.terminal_state_index.post_commit_status_checks.reason,
    'latest_commit_detected_without_post_commit_status_checks',
  );
  assert.equal(clip.terminal_state_index.final_closeout_prose.status, 'source_claimed');
  assert.ok(clip.artifact_delta_index.delta_stat_rows.length >= 1);
});

test('indexes non-B3 Codex traces with long output lines and no invented terminal commit', () => {
  const longOutput = `{"row":"${'x'.repeat(7000)}","result":"kept once"}`;
  const text = [
    'Execution mode: direct_local.',
    'Ran',
    'Check JSON standard',
    'Bash',
    '$ ./repo-python -m json.tool codex/standards/std_agent_trace_lossless_clip.json',
    longOutput,
    'Success',
    'Validation passed: ./repo-python -m json.tool codex/standards/std_agent_trace_lossless_clip.json',
    'navigation_seed_used: AGENTS.override.md, CODEX.md, AGENTS.md',
    'general_artifacts_checked: agent trace structurer',
    'refinement_result: command ledger refined',
    'plane_home: agent trace structurer',
    'discoverability_refresh: parser tests',
  ].join('\n');
  const packet = parseAgentTrace(text, 'codex-non-b3-long-line.txt', '2026-05-13T09:31:00Z');
  const clip = buildAttachmentClip(packet);
  const command = clip.command_ledger.records.find((row) => row.command.startsWith('./repo-python -m json.tool'));

  assert.equal(clip.terminal_state_index.latest_commit.status, 'not_detected');
  assert.equal(clip.terminal_state_index.post_commit_status_checks.status, 'not_applicable');
  assert.equal(clip.terminal_state_index.final_closeout_prose.status, 'source_claimed');
  assert.equal(command.role, 'validation');
  assert.equal(command.status, 'pass');
  assert.ok(command.output_excerpt.length < longOutput.length);
  assert.equal(clip.long_line_index.long_line_count, 1);
  assert.ok(clip.long_line_index.rows[0].segment_ids.length >= 1);
});

test('classifies prompt, mixed clip paste, and flattened review captures', () => {
  const prompt = [
    'Task: improve the toolbar capture flow',
    'Instructions: preserve every command as pointers.',
    'Output: concise patch plus validation.',
    '- Do not overfit to one example.',
  ].join('\n');
  const mixed = `${prompt}\n\n{"schema_version":"agent_trace_lossless_clip_v2","clip_contract":{},"source_segments":[]}`;
  const review = [
    'Review',
    'tools/agent_trace_structurer/parser.mjs',
    '+ added command ledger',
    '- old reader-only path',
    '+ terminal_state_index',
    '+ validation_matrix',
  ].join('\n');

  assert.equal(classifyClipboardText(prompt), 'prompt');
  assert.equal(classifyClipboardText(mixed), 'mixed_paste');
  assert.equal(classifyClipboardText(review), 'review_diff');
});

test('classifies AIW thread exports before incidental code or ledger text', () => {
  const text = [
    '# AIW Thread Export - responses only',
    '',
    '- conversation: 6a04e765-1074-8386-b1d6-cb2bb74eadb5',
    '- thread: Research lane',
    '- model: Pro · Extended thinking',
    '- prompt_context: first and last 3 non-empty lines only',
    '- up_propagation: omitted',
    '- copied_at: 2026-05-14T07:16:06.954Z',
    'USER PROMPT EXCERPT:',
    '[full operator prompt omitted]',
    'function incidentalCode() { return "not a code_file"; }',
    'Task Ledger rows appear here as source text.',
    '---',
    '',
    'ASSISTANT:',
    'Done.',
  ].join('\n');

  assert.equal(classifyClipboardText(text), 'operator_thread_export');
  const packet = parseAgentTrace(text, 'clipboard-capture.json', '2026-05-14T07:16:06Z');
  assert.equal(packet.source_profile.detected_trace_format, 'operator_thread_export');
  assert.equal(packet.source_profile.primary_content_kind, 'operator_thread_export');
  assert.equal(packet.source_profile.thread_export.conversation_id, '6a04e765-1074-8386-b1d6-cb2bb74eadb5');
  assert.equal(packet.source_profile.thread_export.thread_label, 'Research lane');
  assert.equal(packet.artifacts.length, 0);
});

test('preserves all detected commands as pointers while keeping huge outputs bounded', () => {
  const hugeOutput = `OUTPUT:${'0123456789'.repeat(800)}`;
  const text = [
    'Ran',
    'Bootstrap',
    'Bash',
    '$ ./repo-python kernel.py --pulse',
    'KERNEL PULSE',
    'Success',
    'Ran',
    'Parser tests',
    'Bash',
    '$ node --test tools/agent_trace_structurer/parser.test.mjs',
    hugeOutput,
    'ℹ fail 0',
    'Success',
    '- ./repo-git status --short',
  ].join('\n');
  const packet = parseAgentTrace(text, 'huge-command-output.txt', '2026-05-13T09:32:00Z');
  const clip = buildAttachmentClip(packet);
  const commands = clip.command_ledger.records.map((row) => row.command);
  const validation = clip.command_ledger.records.find((row) => row.command.startsWith('node --test'));

  assert.deepEqual(commands, [
    './repo-python kernel.py --pulse',
    'node --test tools/agent_trace_structurer/parser.test.mjs',
    './repo-git status --short',
  ]);
  assert.equal(validation.role, 'validation');
  assert.equal(validation.status, 'pass');
  assert.ok(validation.output_excerpt.length < hugeOutput.length);
  assert.equal(Boolean(validation.output_hash), true);
  if (clip.carrier_mode === 'single_json') {
    assert.equal(JSON.stringify(clip).includes(hugeOutput), true);
  } else {
    assert.equal(clip.raw_sidecar.byte_count_utf8, utf8Bytes(text));
  }
  assert.ok(JSON.stringify(clip.command_ledger).length < hugeOutput.length);
});

test('separates checks, governance receipts, and diagnostics by executed command head', () => {
  const text = [
    'Ran',
    'Inspect fixture text',
    'Bash',
    "$ ./repo-python - <<'PY'",
    'fixture = "tools/meta/control/closeout_executor.py should not classify this heredoc"',
    'print(fixture)',
    'PY',
    'tools/meta/control/closeout_executor.py should not classify this heredoc',
    'Process exited with code 0',
    'Ran',
    'Run failing capsule unit test',
    'Bash',
    '$ ./repo-python tools/agent_trace_structurer/trace_capsule_unit_test.py',
    'AssertionError: expected failing fixture',
    'Process exited with code 1',
    'Ran',
    'Run closeout executor',
    'Bash',
    '$ ./repo-python tools/meta/control/closeout_executor.py run-burst --json',
    '{"status": "blocked", "stop_reason": "UnsupportedLane"}',
    'Process exited with code 0',
    'Ran',
    'Commit scoped paths',
    'Bash',
    '$ ./repo-python tools/meta/control/scoped_commit.py full-paths --path tools/example.py --message ok',
    '{"new_commit": "abc1234def5678"}',
    'Process exited with code 0',
  ].join('\n');

  const packet = parseAgentTrace(text, 'typed-evidence-fixture.txt', '2026-05-23T06:00:00Z');
  const clip = buildAttachmentClip(packet);
  const heredoc = clip.command_ledger.records.find((row) => row.command.startsWith("./repo-python - <<'PY'"));
  const directTest = clip.command_ledger.records.find((row) => row.command.includes('trace_capsule_unit_test.py'));
  const closeout = clip.command_ledger.records.find((row) => row.command.includes('closeout_executor.py run-burst'));
  const scopedCommit = clip.command_ledger.records.find((row) => row.command.includes('scoped_commit.py full-paths'));
  const matrix = clip.validation_matrix;

  assert.equal(heredoc.role, 'diagnostic');
  assert.equal(directTest.role, 'validation');
  assert.equal(directTest.status, 'fail');
  assert.equal(closeout.role, 'governance');
  assert.equal(scopedCommit.role, 'governance');
  assert.equal(matrix.validation_count, 1);
  assert.equal(matrix.governance_receipt_count, 2);
  assert.equal(matrix.bucket_counts.checks.fail, 1);
  assert.equal(matrix.bucket_counts.checks.total, 1);
  assert.equal(matrix.bucket_counts.governance_receipts.pass, 1);
  assert.equal(matrix.bucket_counts.governance_receipts.other, 1);
  assert.equal(matrix.bucket_counts.governance_receipts.total, 2);
  assert.equal(matrix.bucket_counts.diagnostics.total, 1);
  assert.equal(
    matrix.rows.some((row) => row.command_id === heredoc.id && row.bucket === 'governance_receipts'),
    false,
  );
});

test('indexes apply_patch traces as command output plus per-file delta excerpts', () => {
  const text = [
    '# codex session fixture turn 4',
    'Ran',
    'apply_patch (1/1)',
    'Bash',
    '$ apply_patch',
    'Success. Updated the following files:',
    'M tools/agent_trace_structurer/app.mjs',
    'Process exited with code 0',
    'Success',
    '',
    'Edited',
    'tools/agent_trace_structurer/app.mjs',
    '+2',
    '-1',
    '*** Update File: tools/agent_trace_structurer/app.mjs',
    '@@',
    '-  copySelectedMissionArtifact("compressed", "compact_json");',
    '+  copySelectedMissionArtifact("compressed", "denoised");',
    '+  // compact sidecar stays explicit.',
    '*** End Patch',
  ].join('\n');
  const packet = parseAgentTrace(text, 'apply-patch-trace.txt', '2026-05-18T03:02:00Z');
  const clip = buildAttachmentClip(packet);
  const command = clip.command_ledger.records.find((row) => row.command === 'apply_patch');
  const delta = clip.artifact_delta_index.rows.find((row) => row.path === 'tools/agent_trace_structurer/app.mjs');

  assert.equal(command.role, 'edit');
  assert.equal(command.status, 'pass');
  assert.equal(command.exit_code, 0);
  assert.match(command.output_excerpt, /Updated the following files/);
  assert.equal(delta.delta_state, 'edited');
  assert.equal(delta.change_stats.additions, 2);
  assert.equal(delta.change_stats.deletions, 1);
  assert.match(delta.content_excerpt, /compact sidecar stays explicit/);
});
