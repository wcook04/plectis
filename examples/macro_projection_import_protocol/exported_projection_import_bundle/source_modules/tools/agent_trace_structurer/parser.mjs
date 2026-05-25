const ID_RE = /\b(?:cap_[a-z0-9_]+|td_[a-f0-9]+|wlr_[a-f0-9]+|wlc_[a-f0-9]+|mtx_[A-Za-z0-9_]+|orch_[A-Za-z0-9T_]+|signoff_[A-Za-z0-9_]+)\b/g;
const HASH_RE = /\b[a-f0-9]{7,40}\b/g;
const PATH_RE = /(?:^|[\s`"'(])((?:\.{1,2}\/|\/Users\/|[A-Za-z0-9_.-]+\/)(?:[^\s`"'<>|]+\/)*[A-Za-z0-9_.()@%+,=-]+(?:\.[A-Za-z0-9][A-Za-z0-9_-]*|\/)?)/g;
const BACKTICK_COMMAND_RE = /`((?:\.\/repo-[^`]+|\.\/checkpoint [^`]+|python3? [^`]+|npm [^`]+|git [^`]+|rg [^`]+|jq [^`]+|curl [^`]+))`/g;
const ANCHORED_COMMAND_RE = /^\s*(?:[-*]\s+|\d+[.)]\s+)?((?:\.\/repo-(?:python|pytest|git|env)\b|\.\/checkpoint\b|node\b|npm\b|npx\b|pnpm\b|yarn\b|python3?\b|pytest\b|git\b|rg\b|grep\b|jq\b|curl\b|swift\b|xcodebuild\b|make\b|uv\b)[^\n]*)$/;
const SCRIPT_COMMAND_RE = /^\s*(?:[-*]\s+|\d+[.)]\s+)?((?:[A-Za-z0-9_./-]+\.py|[A-Za-z0-9_./-]+\.sh)\s+--?[^\n]*)$/;
const TEXT_ENCODER = new TextEncoder();
const ATTACHMENT_READER_SCHEMA_VERSION = 'agent_trace_lossless_clip_v2';
const ATTACHMENT_CLIP_STANDARD_REF = 'codex/standards/std_agent_trace_lossless_clip.json';
const CLIP_SIZE_RATIO_TARGET = 1.25;
const CLIP_TINY_SOURCE_BYTES = 12000;
const CLIP_TINY_FIXED_ALLOWANCE_BYTES = 12000;
const CLIP_NORMAL_FIXED_ALLOWANCE_BYTES = 6144;
const FINAL_MESSAGE_SUMMARY_CHARS = 700;
const FINAL_MESSAGE_BODY_CHARS = 8000;
const TOOL_FILE_ACTIONS = new Set(['Read', 'Edited', 'Created', 'Wrote', 'Deleted']);
const TOOL_BOUNDARY_RE = /^(?:Ran|Read|Edited|Created|Wrote|Deleted|Updated todos|Used ScheduleWakeup|Success|Failed|Failure|Error)$/;
const FILE_EXT_RE = /\.([A-Za-z0-9][A-Za-z0-9_-]*)$/;
const KNOWN_PATH_PREFIX_RE = /^(?:codex|docs|fixtures|obsidian|scripts|state|system|tools|external|runtime|public|src|test|tests|app|components|pages|lib)\//;
const STANDALONE_CODE_RE = /^\s*(?:import\s|export\s|from\s+['"]|const\s+\w+\s*=|let\s+\w+\s*=|var\s+\w+\s*=|function\s+\w+|class\s+\w+|interface\s+\w+|type\s+\w+|\/\/\s*\[PURPOSE\]|#include\s|package\s+\w+)/m;
const B3_PACKET_START = 'PACKET v=3.2';
const B3_PACKET_END = 'END_PACKET';
const B3_HOT_PATH_FIELDS = [
  'terminal_state',
  'produced_artifacts',
  'active_decision_axes',
  'primary_affordance_surfaces',
  'validation_boundary',
  'workspace_boundary',
  'residuals',
];
const B3_TOP_LEVEL_FIELDS = [
  'thread',
  'scope',
  'last_valid_state_per_source',
  'hot_path',
  'state_capsule',
  'produced_artifacts',
  'operator_intent_signals',
  'decision_axes',
  'source_stated_proposals',
  'affordance_surface',
  'surface_topology',
  'change_envelope',
  'behavioral_arcs',
  'proof_boundary',
  'native_compaction_relation',
  'edit_anchors',
  'decided',
  'done_major',
  'validation_matrix',
  'done_inspection',
  'authority_map',
  'workspace_state',
  'stated_open',
  'stated_blocked',
  'stated_risks',
  'stated_contradictions',
  'stated_freshness_or_staleness',
  'stated_postures',
  'verbatim_quotes',
  'facts_added',
  'evidence_pointers',
  'omitted',
];
const PROMPT_DIRECTIVE_RE = /(?:^|\n)\s*(?:please|can you|make sure|improve|fix|implement|write|build|compact|summari[sz]e|extract|use|do not|don't|never|always|carry forward|continue|refactor|debug|review)\b/i;
const PROMPT_ROLE_RE = /(?:^|\n)\s*(?:system|developer|user|assistant|instructions?|objective|goal|task|context|constraints?|requirements?|output|format|deliverables?)\s*:/gi;
const PROMPT_XML_RE = /<\/?(?:system|developer|user|assistant|instructions?|environment_context|task|source)\b/i;
const OPERATOR_THREAD_EXPORT_RE = /^\s*#\s*AIW Thread Export\s*-\s*(?<mode>[^\n]+)\s*$/im;

function looksLikeOperatorThreadExport(text) {
  return OPERATOR_THREAD_EXPORT_RE.test(String(text || ''));
}

function operatorThreadExportMetadata(lines) {
  const source = lines.join('\n');
  const match = OPERATOR_THREAD_EXPORT_RE.exec(source);
  if (!match) return { detected: false };
  const header = {};
  for (const line of lines.slice(0, 32)) {
    const row = /^\s*-\s*([A-Za-z_]+):\s*(.*?)\s*$/.exec(line);
    if (row) header[row[1].toLowerCase()] = row[2];
  }
  return {
    detected: true,
    mode: (match.groups?.mode || '').trim(),
    conversation_id: header.conversation || '',
    thread_label: header.thread || '',
    model_label: header.model || '',
    context_mass: header.context_mass || '',
    prompt_context: header.prompt_context || '',
    up_propagation: header.up_propagation || '',
    copied_at: header.copied_at || '',
    exported_at: header.exported_at || '',
    user_prompt_excerpt_count: lines.filter((line) => /^USER PROMPT EXCERPT:\s*$/.test(line.trim())).length,
    assistant_section_count: lines.filter((line) => /^ASSISTANT:\s*$/.test(line.trim())).length,
  };
}

export function looksLikePromptText(text) {
  const value = String(text || '').trim();
  if (!value || /^PACKET v=/m.test(value) || /^\s*[{[]/.test(value)) return false;
  const lines = value.split(/\r\n?|\n/).filter((line) => line.trim());
  const headingCount = lines.filter((line) =>
    /^(?:#{1,4}\s*)?(?:prompt|task|objective|goal|instructions?|context|constraints?|requirements?|output|format|deliverables?|source|role)\b[:：]?/i.test(line.trim()),
  ).length;
  const roleSignals = (value.match(PROMPT_ROLE_RE) || []).length + (PROMPT_XML_RE.test(value) ? 1 : 0);
  const directive = PROMPT_DIRECTIVE_RE.test(value) || /^\s*you are\b/i.test(value);
  const listOrHeadingShape = /(?:^|\n)\s*(?:[-*]\s+|\d+\.\s+|#{1,4}\s+\S)/.test(value);
  return (
    headingCount >= 2 ||
    (roleSignals >= 2 && directive) ||
    (directive && listOrHeadingShape && value.length >= 180) ||
    (/^\s*(?:can we|could you|please|make sure|improve|fix|build|write|compact|summari[sz]e)\b/i.test(value) && value.length >= 120)
  );
}

function looksLikeFlattenedReview(text) {
  const value = String(text || '');
  const lines = value.split(/\r\n?|\n/).filter((line) => line.trim());
  const diffish = lines.filter((line) => /^\s*[+-](?![+-])/.test(line)).length;
  const pathish = lines.filter((line) => extractPaths(line).length > 0).length;
  const reviewWords = /\b(?:review|diff|patch|files? changed|insertions?\(\+\)|deletions?\(-\)|undo|open)\b/i.test(value);
  return diffish >= 4 && (pathish >= 1 || reviewWords);
}

function looksLikeMixedPaste(text) {
  const value = String(text || '');
  if (!value.trim()) return false;
  const promptish = looksLikePromptText(value) || PROMPT_DIRECTIVE_RE.test(value);
  const clipish = /"schema_version"\s*:\s*"agent_trace_lossless_clip_v2"|clip_contract|source_segments|source_segment_index/.test(value);
  const traceish = /^(?:Ran|Read|Edited|Created|Wrote|Deleted|Bash|Ran \d+ commands?|Explored \d+ files?(?:,.*)?|Success)$/m.test(value);
  return promptish && (clipish || traceish || /^PACKET v=/m.test(value));
}

export function classifyClipboardText(text) {
  const value = String(text || '');
  const traceMarkerCount = (value.match(/^(?:Ran|Read|Edited|Created|Wrote|Deleted|Bash|Ran \d+ commands?|Explored \d+ files?(?:,.*)?|Success)$/gm) || []).length;
  if (looksLikeOperatorThreadExport(value)) return 'operator_thread_export';
  if (looksLikeMixedPaste(value)) return 'mixed_paste';
  if (/^PACKET v=/m.test(value)) return 'packet';
  if (traceMarkerCount < 3 && /^\s*(?:import\s|export\s|const\s+\w+\s*=|function\s+\w+|class\s+\w+|interface\s+\w+|type\s+\w+|\/\/\s*\[PURPOSE\])/m.test(value)) {
    return 'code_file';
  }
  if (traceMarkerCount < 3 && looksLikeFlattenedReview(value)) return 'review_diff';
  if (traceMarkerCount < 3 && looksLikePromptText(value)) return 'prompt';
  if (/\bcap_[a-z0-9_]+\b|\btd_[a-f0-9]+\b|\bwork_landing\b|\bTask Ledger\b|\bWork Ledger\b/.test(value)) return 'agent_trace';
  if (/^(Ran|\$|Edited|Created|Deleted|Committed|Validation|Success|Failed)\b/m.test(value)) return 'command_trace';
  if (/^\s*[{[]/.test(value)) return 'json_like';
  return 'text';
}

function linesOf(text) {
  if (!text) return [];
  return text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
}

function lineBreakProfile(text) {
  const value = String(text || '');
  const crlf = (value.match(/\r\n/g) || []).length;
  const withoutCrlf = value.replace(/\r\n/g, '');
  const cr = (withoutCrlf.match(/\r/g) || []).length;
  const lf = (withoutCrlf.match(/\n/g) || []).length;
  const kinds = [
    crlf ? 'crlf' : null,
    lf ? 'lf' : null,
    cr ? 'cr' : null,
  ].filter(Boolean);
  return {
    style: kinds.length === 0 ? 'none' : kinds.length === 1 ? kinds[0] : 'mixed',
    crlf,
    lf,
    cr,
    ends_with_line_break: /\r\n$|\n$|\r$/.test(value),
  };
}

function stableHash(text) {
  let hash = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, '0');
}

function byteLength(text) {
  return TEXT_ENCODER.encode(String(text || '')).length;
}

function losslessSourceMetadata(text, lines, inputBytes) {
  return {
    schema_version: 'lossless_source_v1',
    source_text_field: 'source_text',
    source_text_complete: true,
    source_text_hash: stableHash(text),
    source_text_chars: text.length,
    source_text_bytes: inputBytes,
    source_line_count: lines.length,
    line_breaks: lineBreakProfile(text),
    source_lines_are_navigation_projection: true,
    source_lines_line_break_policy: 'line endings are normalized to "\\n" for indexing; use source_text for exact byte-level wording and final newline state',
    reconstruction_rule: 'source_text is the exact copied string. source_lines exists for 1-based navigation and line_range evidence pointers.',
  };
}

function uniq(values) {
  return Array.from(new Set(values.filter(Boolean))).sort((a, b) => a.localeCompare(b));
}

function cleanPath(value) {
  return value.replace(/[),.;:]+$/, '').replace(/^["'`]+|["'`]+$/g, '');
}

function isLikelyPath(value) {
  const path = cleanPath(value.trim());
  if (!path || path.includes('://') || path.length < 3) return false;
  if (/^[A-Za-z0-9_-]+\/(?:[0-9]{1,3}|\[[^\]]+\])$/.test(path)) return false;
  if (/^(?:text|bg|border|ring|from|to|via|stroke|fill|divide|outline|decoration|placeholder|accent|shadow|backdrop|hover|focus|active|disabled)-[A-Za-z0-9_-]+\/[0-9]{1,3}$/.test(path)) return false;
  if (/^(?:entry|line|route|control|read|write|copy|paste|drag|find|source|system|agent)\/[A-Za-z0-9_-]+$/.test(path)) return false;
  if (/^(?:\.{1,2}\/|\/Users\/)/.test(path)) return true;
  if (KNOWN_PATH_PREFIX_RE.test(path)) return true;
  if ((path.match(/\//g) || []).length >= 2) return true;
  return FILE_EXT_RE.test(path);
}

function matches(line, regex) {
  const out = [];
  for (const match of line.matchAll(regex)) {
    const value = match[1] || match[0];
    if (value) out.push(value.trim());
  }
  return out;
}

function extractPaths(line) {
  return uniq(
    matches(line, PATH_RE)
      .map(cleanPath)
      .filter(isLikelyPath),
  );
}

function extractCommands(line) {
  const trimmed = line.trim();
  const direct = trimmed.match(/^\$\s+(.+)$/) || trimmed.match(/^Ran\s+(.+)$/);
  const anchored = trimmed.match(ANCHORED_COMMAND_RE) || trimmed.match(SCRIPT_COMMAND_RE);
  return uniq([
    ...(direct && direct[1] ? [direct[1].trim()] : []),
    ...(anchored && anchored[1] ? [anchored[1].trim()] : []),
    ...matches(line, BACKTICK_COMMAND_RE),
  ]);
}

function extractEntities(line) {
  return {
    paths: extractPaths(line),
    commands: extractCommands(line),
    ids: uniq(matches(line, ID_RE)),
    hashes: uniq(matches(line, HASH_RE).filter((hash) => !/^\d+$/.test(hash))),
  };
}

function quoteMask(lines) {
  const mask = [];
  let inQuote = false;
  for (const line of lines) {
    mask.push(inQuote);
    const quoteCount = (line.match(/"""/g) || []).length;
    if (quoteCount % 2 === 1) inQuote = !inQuote;
  }
  return mask;
}

function b3SectionPositions(lines) {
  const positions = {};
  lines.forEach((line, index) => {
    for (const field of B3_TOP_LEVEL_FIELDS) {
      if (positions[field] == null && line.startsWith(`${field}:`)) {
        positions[field] = index;
      }
    }
  });
  return positions;
}

function b3SectionLines(lines, positions, section) {
  const start = positions[section];
  if (start == null) return [];
  const later = Object.entries(positions)
    .filter(([key, index]) => key !== section && index > start)
    .map(([, index]) => index);
  const end = later.length ? Math.min(...later) : lines.length;
  const out = [];
  for (let index = start + 1; index < end; index += 1) out.push([index, lines[index]]);
  return out;
}

function b3Issue(code, index = null, detail = '') {
  const issue = { code };
  if (index != null) issue.line = index + 1;
  if (detail) issue.detail = detail;
  return issue;
}

function packetConformance(text, lines) {
  if (!text.trimStart().startsWith(B3_PACKET_START)) {
    return {
      schema_version: 'agent_trace_structurer_packet_conformance_v0',
      status: 'not_applicable',
      packet_version: 'unknown',
      issue_count: 0,
      issues: [],
    };
  }

  const issues = [];
  const nonempty = lines.map((line, index) => [line, index]).filter(([line]) => String(line).trim());
  const first = nonempty[0]?.[1] ?? 0;
  const last = nonempty[nonempty.length - 1]?.[1] ?? lines.length - 1;
  const starts = lines.map((line, index) => [line.trim(), index]).filter(([line]) => line === B3_PACKET_START).map(([, index]) => index);
  const ends = lines.map((line, index) => [line.trim(), index]).filter(([line]) => line === B3_PACKET_END).map(([, index]) => index);
  if (lines[first]?.trim() !== B3_PACKET_START) issues.push(b3Issue('packet_start_not_v3_2', first, lines[first]?.trim() || ''));
  else if (lines[first] !== B3_PACKET_START) issues.push(b3Issue('packet_start_not_column_1', first, lines[first] || ''));
  if (lines[last]?.trim() !== B3_PACKET_END) issues.push(b3Issue('packet_end_missing', last, lines[last]?.trim() || ''));
  else if (lines[last] !== B3_PACKET_END) issues.push(b3Issue('packet_end_not_column_1', last, lines[last] || ''));
  if (starts.length !== 1) issues.push(b3Issue('packet_start_count_invalid', null, String(starts.length)));
  if (ends.length !== 1) issues.push(b3Issue('packet_end_count_invalid', null, String(ends.length)));
  for (const index of starts) {
    if (index !== first && lines[index] !== B3_PACKET_START) issues.push(b3Issue('packet_start_not_column_1', index, lines[index] || ''));
  }
  for (const index of ends) {
    if (index !== last && lines[index] !== B3_PACKET_END) issues.push(b3Issue('packet_end_not_column_1', index, lines[index] || ''));
  }

  const mask = quoteMask(lines);
  lines.forEach((line, index) => {
    if (mask[index]) return;
    if (/^\s*\* /.test(line)) issues.push(b3Issue('invalid_star_list_marker', index, line.trim().slice(0, 120)));
    if (/\bevidence=\s*(?:$|::|;)/.test(line)) issues.push(b3Issue('empty_evidence_value', index, line.trim().slice(0, 120)));
  });

  const positions = b3SectionPositions(lines);
  for (const field of B3_TOP_LEVEL_FIELDS) {
    if (positions[field] == null) issues.push(b3Issue('required_field_missing', null, field));
  }
  const hotLines = b3SectionLines(lines, positions, 'hot_path');
  const foundHot = new Set();
  for (const [index, line] of hotLines) {
    const unindented = line.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (unindented && B3_HOT_PATH_FIELDS.includes(unindented[1])) {
      issues.push(b3Issue('hot_path_field_unindented', index, unindented[1]));
      continue;
    }
    const indented = line.match(/^\s{2}([A-Za-z0-9_]+):\s*(.*)$/);
    if (indented) foundHot.add(indented[1]);
  }
  for (const field of B3_HOT_PATH_FIELDS) {
    if (!foundHot.has(field)) issues.push(b3Issue('hot_path_field_missing', null, field));
  }

  for (const [index, line] of b3SectionLines(lines, positions, 'operator_intent_signals')) {
    const stripped = line.trim().toLowerCase();
    if (stripped.startsWith('- ') && stripped.includes('signal=none') && stripped.includes('source=not_stated')) {
      issues.push(b3Issue('sentinel_empty_row', index, 'operator_intent_signals.signal'));
    }
  }

  return {
    schema_version: 'agent_trace_structurer_packet_conformance_v0',
    status: issues.length ? 'issues' : 'clean',
    packet_version: B3_PACKET_START,
    issue_count: issues.length,
    issue_codes: Array.from(new Set(issues.map((issue) => issue.code))).sort(),
    issues: issues.slice(0, 50),
  };
}

function titleCaseId(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'section';
}

function sectionTitle(line) {
  const trimmed = line.trim();
  if (/^#{1,6}\s+\S/.test(trimmed)) return trimmed.replace(/^#{1,6}\s+/, '').trim();
  if (/^[A-Za-z][A-Za-z0-9_ -]{2,80}:$/.test(trimmed)) return trimmed.slice(0, -1).trim();
  return null;
}

function classifyLine(line) {
  const trimmed = line.trim();
  if (!trimmed) return null;

  if (/^PACKET v=/.test(trimmed) || trimmed === 'END_PACKET') {
    return { kind: 'packet', title: trimmed, status: 'not_stated', command: null };
  }
  const command = trimmed.match(/^Ran\s+(.+)$/)?.[1] || trimmed.match(/^\$\s+(.+)$/)?.[1] || null;
  if (command) return { kind: 'command', title: command, status: 'not_stated', command };
  if (trimmed === 'Success') return { kind: 'status', title: 'Success', status: 'pass', command: null };
  if (/^(Failed|Failure|Error|Traceback|AssertionError|FAILURES)\b/i.test(trimmed)) {
    return { kind: 'status', title: trimmed.slice(0, 140), status: 'fail', command: null };
  }
  if (/^(Explored|Read|Searched|Opened|Found)\b/.test(trimmed)) {
    return { kind: 'inspection', title: trimmed.slice(0, 140), status: 'not_stated', command: null };
  }
  if (/^(Edited|Applied|Created|Deleted|Wrote|Refreshed|Committed|Pushed)\b/.test(trimmed)) {
    return { kind: 'mutation', title: trimmed.slice(0, 140), status: 'not_stated', command: null };
  }
  if (/^(Tests?|Validation|Focused|Broader|Compile|Task Ledger|Work Ledger)\b/i.test(trimmed)) {
    return { kind: 'validation', title: trimmed.slice(0, 140), status: 'not_stated', command: null };
  }
  if (/^(?:\* )?commit:\s*`?[a-f0-9]{7,40}/i.test(trimmed)) {
    return { kind: 'commit', title: trimmed.slice(0, 140), status: 'not_stated', command: null };
  }
  const heading = sectionTitle(trimmed);
  if (heading) return { kind: 'section', title: heading, status: 'not_stated', command: null };
  if (/^[A-Za-z0-9_. -]{2,50}:\s+\S/.test(trimmed)) {
    return { kind: 'fact', title: trimmed.slice(0, 140), status: 'not_stated', command: null };
  }
  if (/^(Using bootstrap|I.m|I'm|I am|Wave \d|No candidate|What this means|Recommendation)\b/.test(trimmed)) {
    return { kind: 'agent_note', title: trimmed.slice(0, 140), status: 'not_stated', command: null };
  }
  return null;
}

function snippet(block, maxLines = 10, maxChars = 1400) {
  const text = block
    .map((line) => line.trimEnd())
    .filter((line) => line.trim())
    .slice(0, maxLines)
    .join('\n')
    .trim();
  if (text.length <= maxChars) return text;
  return `${text.slice(0, maxChars - 24).trimEnd()}\n[truncated by parser]`;
}

function truncateText(value, maxChars = 500) {
  const text = String(value || '');
  if (text.length <= maxChars) return text;
  return `${text.slice(0, Math.max(0, maxChars - 24)).trimEnd()}\n[truncated]`;
}

function addEntity(map, kind, value, lineNumber) {
  const existing = map.get(value);
  if (existing) {
    existing.count += 1;
    existing.last_line = lineNumber;
    return;
  }
  map.set(value, {
    value,
    kind,
    count: 1,
    first_line: lineNumber,
    last_line: lineNumber,
  });
}

function sorted(map) {
  return Array.from(map.values()).sort(
    (left, right) => right.count - left.count || left.first_line - right.first_line || left.value.localeCompare(right.value),
  );
}

function countBy(rows, keyFn) {
  const counts = {};
  for (const row of rows) {
    const key = keyFn(row) || 'not_stated';
    counts[key] = (counts[key] || 0) + 1;
  }
  return Object.fromEntries(Object.entries(counts).sort((left, right) => left[0].localeCompare(right[0])));
}

function topEntityRows(rows, limit = 16) {
  return rows.slice(0, limit).map((row) => ({
    value: row.value,
    count: row.count,
    first_line: row.first_line,
    last_line: row.last_line,
  }));
}

function buildEntities(lines) {
  const buckets = {
    paths: new Map(),
    commands: new Map(),
    ids: new Map(),
    hashes: new Map(),
  };
  lines.forEach((line, index) => {
    const lineNumber = index + 1;
    const entities = extractEntities(line);
    entities.paths.forEach((value) => addEntity(buckets.paths, 'path', value, lineNumber));
    entities.commands.forEach((value) => addEntity(buckets.commands, 'command', value, lineNumber));
    entities.ids.forEach((value) => addEntity(buckets.ids, 'id', value, lineNumber));
    entities.hashes.forEach((value) => addEntity(buckets.hashes, 'hash', value, lineNumber));
  });
  return {
    paths: sorted(buckets.paths),
    commands: sorted(buckets.commands),
    ids: sorted(buckets.ids),
    hashes: sorted(buckets.hashes),
  };
}

function buildEntitiesForRange(lines, offsetLine = 0) {
  const buckets = {
    paths: new Map(),
    commands: new Map(),
    ids: new Map(),
    hashes: new Map(),
  };
  lines.forEach((line, index) => {
    const lineNumber = offsetLine + index + 1;
    const entities = extractEntities(line);
    entities.paths.forEach((value) => addEntity(buckets.paths, 'path', value, lineNumber));
    entities.commands.forEach((value) => addEntity(buckets.commands, 'command', value, lineNumber));
    entities.ids.forEach((value) => addEntity(buckets.ids, 'id', value, lineNumber));
    entities.hashes.forEach((value) => addEntity(buckets.hashes, 'hash', value, lineNumber));
  });
  return {
    paths: sorted(buckets.paths),
    commands: sorted(buckets.commands),
    ids: sorted(buckets.ids),
    hashes: sorted(buckets.hashes),
  };
}

function buildTimeline(lines) {
  const signals = lines
    .map((line, index) => ({ line, index, signal: classifyLine(line) }))
    .filter((row) => row.signal);

  return signals.map((row, index) => {
    const next = signals[index + 1]?.index || lines.length;
    const block = lines.slice(row.index, Math.max(row.index + 1, next));
    const blockEntities = block.reduce(
      (acc, line) => {
        const entities = extractEntities(line);
        acc.paths.push(...entities.paths);
        acc.commands.push(...entities.commands);
        acc.ids.push(...entities.ids);
        acc.hashes.push(...entities.hashes);
        return acc;
      },
      { paths: [], commands: [], ids: [], hashes: [] },
    );
    return {
      id: `trace_${row.signal.kind}_${String(index + 1).padStart(4, '0')}`,
      kind: row.signal.kind,
      title: row.signal.title,
      line_range: { start: row.index + 1, end: Math.max(row.index + 1, next) },
      status: row.signal.status,
      command: row.signal.command,
      snippet: snippet(block),
      entities: {
        paths: uniq(blockEntities.paths),
        commands: uniq(blockEntities.commands),
        ids: uniq(blockEntities.ids),
        hashes: uniq(blockEntities.hashes),
      },
    };
  });
}

function parseKeyValues(lines) {
  const pairs = {};
  for (const line of lines) {
    const match = line.trim().match(/^([A-Za-z0-9_. -]{2,60}):\s+(.+)$/);
    if (!match) continue;
    const key = titleCaseId(match[1]);
    if (!pairs[key]) pairs[key] = match[2].trim();
  }
  return pairs;
}

function buildSections(lines) {
  const headings = lines
    .map((line, index) => ({ title: sectionTitle(line), index }))
    .filter((row) => row.title);
  return headings.map((row, index) => {
    const next = headings[index + 1]?.index || lines.length;
    const block = lines.slice(row.index, Math.max(row.index + 1, next));
    return {
      id: `section_${String(index + 1).padStart(4, '0')}_${titleCaseId(row.title)}`,
      title: row.title,
      line_range: { start: row.index + 1, end: Math.max(row.index + 1, next) },
      key_values: parseKeyValues(block.slice(1)),
      preview: snippet(block, 8, 900),
    };
  });
}

function languageFromPath(path = '') {
  const ext = (path.match(FILE_EXT_RE)?.[1] || '').toLowerCase();
  const map = {
    cjs: 'javascript',
    css: 'css',
    html: 'html',
    js: 'javascript',
    json: 'json',
    jsx: 'jsx',
    md: 'markdown',
    mjs: 'javascript',
    py: 'python',
    sh: 'shell',
    swift: 'swift',
    ts: 'typescript',
    tsx: 'tsx',
    yaml: 'yaml',
    yml: 'yaml',
  };
  return map[ext] || ext || 'unknown';
}

function languageFromContent(lines) {
  const joined = lines.slice(0, 40).join('\n');
  if (/^\s*[{[]/.test(joined)) return 'json';
  if (/^\s*#\s+\S/m.test(joined)) return 'markdown';
  if (/^\s*import\s.+from\s+['"]|<\w+[\s>]/m.test(joined)) return /\btype\s+\w+|interface\s+\w+|:\s*React\./.test(joined) ? 'tsx' : 'jsx';
  if (/^\s*(?:import|export|const|let|function|class)\s/m.test(joined)) return /\btype\s+\w+|interface\s+\w+/.test(joined) ? 'typescript' : 'javascript';
  if (/^\s*(?:def|class|from|import)\s/m.test(joined)) return 'python';
  if (/^\s*import\s+(?:AppKit|Foundation|SwiftUI)\b/m.test(joined)) return 'swift';
  return 'unknown';
}

function isToolBoundaryLine(line) {
  return TOOL_BOUNDARY_RE.test(line.trim()) || /^(?:Ran|Read) \d+ .+/.test(line.trim());
}

function looksLikeContentStart(line) {
  const trimmed = line.trim();
  if (!trimmed) return false;
  return /^(?:\{|\[|\/\/|\/\*|\*|#|import\s|export\s|const\s|let\s|var\s|function\s|class\s|type\s|interface\s|return\b|if\s*\(|for\s*\(|while\s*\(|<|[-*]\s|\|)/.test(trimmed);
}

function looksLikePathFragment(line) {
  const trimmed = cleanPath(line.trim());
  if (!trimmed || /\s/.test(trimmed)) return false;
  if (isLikelyPath(trimmed)) return true;
  return /^[A-Za-z0-9_.@%+,=-]+\/$/.test(trimmed) || /^[A-Za-z0-9_.@%+,=-]+\.[A-Za-z0-9][A-Za-z0-9_-]*$/.test(trimmed);
}

function joinPathParts(parts) {
  if (!parts.length) return '';
  return parts.reduce((acc, part) => {
    if (!acc) return part;
    if (acc.endsWith('/') || part.startsWith('/')) return `${acc}${part}`;
    return `${acc}/${part}`;
  }, '');
}

function findNextBoundary(lines, startIndex) {
  for (let index = startIndex; index < lines.length; index += 1) {
    if (isToolBoundaryLine(lines[index])) return index;
  }
  return lines.length;
}

function parseFileArtifactAt(lines, startIndex, artifactIndex) {
  const action = lines[startIndex].trim();
  if (!TOOL_FILE_ACTIONS.has(action)) return null;
  let cursor = startIndex + 1;
  while (cursor < lines.length && !lines[cursor].trim()) cursor += 1;
  if (cursor >= lines.length || isToolBoundaryLine(lines[cursor])) return null;

  const displayName = lines[cursor].trim();
  if (!displayName || displayName.length > 220 || looksLikeContentStart(displayName)) return null;
  cursor += 1;

  let additions = null;
  let deletions = null;
  if (/^\+\d+$/.test(lines[cursor]?.trim() || '')) {
    additions = Number(lines[cursor].trim().slice(1));
    cursor += 1;
  }
  if (/^-\d+$/.test(lines[cursor]?.trim() || '')) {
    deletions = Number(lines[cursor].trim().slice(1));
    cursor += 1;
  }

  const pathParts = [];
  while (cursor < lines.length && pathParts.length < 8) {
    const trimmed = lines[cursor].trim();
    if (!trimmed) {
      cursor += 1;
      continue;
    }
    if (isToolBoundaryLine(trimmed) || looksLikeContentStart(trimmed)) break;
    if (!looksLikePathFragment(trimmed)) break;
    pathParts.push(cleanPath(trimmed));
    cursor += 1;
  }

  const displayPath = looksLikePathFragment(displayName) ? cleanPath(displayName) : '';
  const path = joinPathParts(pathParts) || displayPath;
  const contentStart = cursor;
  const endExclusive = findNextBoundary(lines, contentStart);
  const content = lines.slice(contentStart, endExclusive);
  const hasContent = content.some((line) => line.trim());
  if (!path && !FILE_EXT_RE.test(displayName) && !hasContent) return null;

  const language = languageFromPath(path || displayName) || languageFromContent(content);
  const contentText = content.join('\n');
  const kindByAction = {
    Created: 'file_created',
    Edited: 'file_edit',
    Read: 'file_read',
    Wrote: 'file_written',
    Deleted: 'file_deleted',
  };
  const lineStart = startIndex + 1;
  const lineEnd = Math.max(lineStart, endExclusive);
  const contentLineStart = hasContent ? contentStart + 1 : null;
  const contentLineEnd = hasContent ? endExclusive : null;

  return {
    artifact: {
      id: `artifact_${String(artifactIndex).padStart(4, '0')}`,
      kind: kindByAction[action] || 'file_artifact',
      action: action.toLowerCase(),
      title: displayName,
      path: path || null,
      language: language === 'unknown' ? languageFromContent(content) : language,
      line_range: { start: lineStart, end: lineEnd },
      content_line_range: hasContent ? { start: contentLineStart, end: contentLineEnd } : null,
      change_stats: {
        additions,
        deletions,
      },
      content_lines: hasContent ? content.length : 0,
      content_bytes: hasContent ? byteLength(contentText) : 0,
      content_hash: hasContent ? stableHash(contentText) : null,
      preview: hasContent ? snippet(content, 16, 1800) : '',
    },
    endIndex: endExclusive,
  };
}

function parseCommandBlockAt(lines, startIndex, blockIndex) {
  const trimmed = lines[startIndex].trim();
  if (trimmed !== 'Ran') return null;
  const title = lines[startIndex + 1]?.trim() || 'Ran command';
  const shell = lines[startIndex + 2]?.trim() === 'Bash' ? 'bash' : null;
  const commandLineIndex = shell ? startIndex + 3 : startIndex + 2;
  const commandLine = lines[commandLineIndex]?.trim() || '';
  const command = commandLine.startsWith('$ ') ? commandLine.slice(2).trim() : '';
  const endExclusive = findNextBoundary(lines, commandLineIndex + 1);
  return {
    block: {
      id: `block_${String(blockIndex).padStart(4, '0')}`,
      kind: 'command_run',
      title,
      shell,
      command,
      line_range: { start: startIndex + 1, end: Math.max(startIndex + 1, endExclusive) },
      command_line_range: command ? { start: commandLineIndex + 1, end: commandLineIndex + 1 } : null,
      output_line_range: command && endExclusive > commandLineIndex + 1 ? { start: commandLineIndex + 2, end: endExclusive } : null,
      preview: snippet(lines.slice(startIndex, endExclusive), 14, 1600),
    },
    endIndex: endExclusive,
  };
}

function buildArtifactsAndBlocks(lines) {
  const artifacts = [];
  const traceBlocks = [];
  for (let index = 0; index < lines.length; index += 1) {
    const fileBlock = parseFileArtifactAt(lines, index, artifacts.length + 1);
    if (fileBlock) {
      artifacts.push(fileBlock.artifact);
      traceBlocks.push({
        id: `block_${String(traceBlocks.length + 1).padStart(4, '0')}`,
        kind: 'file_artifact',
        artifact_id: fileBlock.artifact.id,
        title: `${fileBlock.artifact.action}: ${fileBlock.artifact.path || fileBlock.artifact.title}`,
        line_range: fileBlock.artifact.line_range,
      });
      index = Math.max(index, fileBlock.endIndex - 1);
      continue;
    }

    const commandBlock = parseCommandBlockAt(lines, index, traceBlocks.length + 1);
    if (commandBlock) {
      traceBlocks.push(commandBlock.block);
      index = Math.max(index, commandBlock.endIndex - 1);
    }
  }
  return { artifacts, traceBlocks };
}

function standaloneSourceArtifact(lines, sourceName) {
  const meaningful = lines.filter((line) => line.trim());
  if (meaningful.length < 4) return null;
  const joined = lines.join('\n');
  if (looksLikeOperatorThreadExport(joined)) return null;
  if (!STANDALONE_CODE_RE.test(joined) && !/^\s*[{[]/.test(joined)) return null;
  const sourceNameLooksGenerated = /^clip-|^clipboard-capture\.json$/i.test(sourceName || '');
  const pathLanguage = sourceNameLooksGenerated ? 'unknown' : languageFromPath(sourceName);
  const language = pathLanguage !== 'unknown' ? pathLanguage : languageFromContent(lines);
  return {
    id: 'artifact_0001',
    kind: 'standalone_source_file',
    action: 'clipboard_source',
    title: sourceName,
    path: null,
    language,
    line_range: { start: 1, end: lines.length },
    content_line_range: { start: 1, end: lines.length },
    change_stats: { additions: null, deletions: null },
    content_lines: lines.length,
    content_bytes: byteLength(joined),
    content_hash: stableHash(joined),
    preview: snippet(lines, 18, 1800),
  };
}

function inferSourceProfile(lines, timeline, artifacts) {
  const exactMarkers = lines.reduce((count, line) => count + (TOOL_BOUNDARY_RE.test(line.trim()) ? 1 : 0), 0);
  const shellCommands = lines.reduce((count, line) => count + (/^\$\s+/.test(line.trim()) ? 1 : 0), 0);
  const codexSignals = lines.reduce(
    (count, line) => count + (/^(?:Explored \d+ files?(?:,.*)?|Ran \d+ commands?|Read [A-Z_a-z0-9./-]+|Execution mode:|KERNEL PULSE|Success)$/.test(line.trim()) ? 1 : 0),
    0,
  );
  const claudeSignals = lines.reduce(
    (count, line) => count + (/^(?:Bash|Ran|Read|Edited|Created|Updated todos|Used ScheduleWakeup)$/.test(line.trim()) ? 1 : 0),
    0,
  );
  const hasStandaloneSource = artifacts.length === 1 && artifacts[0].kind === 'standalone_source_file';
  const operatorThreadExport = operatorThreadExportMetadata(lines);

  if (operatorThreadExport.detected) {
    return {
      detected_trace_format: 'operator_thread_export',
      primary_content_kind: 'operator_thread_export',
      thread_export: operatorThreadExport,
      tool_marker_counts: {
        exact_markers: exactMarkers,
        shell_commands: shellCommands,
        claude_style_markers: claudeSignals,
        codex_style_markers: codexSignals,
      },
      artifact_count: artifacts.length,
      confidence: 0.95,
    };
  }

  let detectedTraceFormat = 'plain_text';
  if (hasStandaloneSource) detectedTraceFormat = 'standalone_source_file';
  else if (artifacts.length && claudeSignals >= Math.max(3, codexSignals * 1.2)) detectedTraceFormat = 'claude_tool_trace';
  else if (codexSignals >= 3 || timeline.some((event) => event.title === 'Success')) detectedTraceFormat = 'codex_tool_trace';
  else if (shellCommands || exactMarkers) detectedTraceFormat = 'generic_tool_trace';

  return {
    detected_trace_format: detectedTraceFormat,
    primary_content_kind: hasStandaloneSource ? 'source_file' : artifacts.length ? 'tool_trace_with_file_artifacts' : 'conversation_trace',
    tool_marker_counts: {
      exact_markers: exactMarkers,
      shell_commands: shellCommands,
      claude_style_markers: claudeSignals,
      codex_style_markers: codexSignals,
    },
    artifact_count: artifacts.length,
    confidence: detectedTraceFormat === 'plain_text' ? 0.35 : 0.82,
  };
}

function evidenceRank(event) {
  if (event.status === 'fail') return 7;
  if (event.kind === 'commit') return 6;
  if (event.kind === 'validation') return 5;
  if (event.kind === 'mutation') return 4;
  if (event.kind === 'command') return 3;
  if (event.kind === 'packet') return 2;
  return 1;
}

const TRACE_ACTIVITY_KINDS = new Set(['command', 'inspection', 'mutation', 'validation', 'commit', 'status', 'packet']);

function lastMeaningfulLine(lines) {
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    if (lines[index].trim()) return index + 1;
  }
  return lines.length;
}

function lineRangeStats(lines, start, end) {
  const boundedStart = Math.max(1, start);
  const boundedEnd = Math.max(boundedStart, Math.min(lines.length, end));
  const selected = lines.slice(boundedStart - 1, boundedEnd);
  return {
    line_range: { start: boundedStart, end: boundedEnd },
    line_count: selected.length,
    byte_count: byteLength(selected.join('\n')),
    preview: snippet(selected, 8, 900),
  };
}

function rangesOverlap(left, right) {
  if (!left || !right) return false;
  return left.start <= right.end && right.start <= left.end;
}

function buildSourceSegments(lines, timeline, traceBlocks) {
  const traceRanges = traceBlocks
    .map((block) => block.line_range)
    .filter((range) => range && typeof range.start === 'number' && typeof range.end === 'number');

  if (!traceRanges.length) {
    traceRanges.push(
      ...timeline
        .filter((event) => TRACE_ACTIVITY_KINDS.has(event.kind))
        .map((event) => event.line_range)
        .filter((range) => range && typeof range.start === 'number' && typeof range.end === 'number'),
    );
  }

  const meaningfulEnd = lastMeaningfulLine(lines);
  if (!traceRanges.length) {
    return {
      mode: 'unsegmented_source',
      first_activity_line: null,
      last_activity_line: null,
      segments: [
        {
          id: 'entire_source',
          role: 'unsegmented_source',
          ...lineRangeStats(lines, 1, meaningfulEnd),
        },
      ],
    };
  }

  const firstActivityLine = Math.min(...traceRanges.map((range) => range.start));
  const lastActivityLine = Math.max(...traceRanges.map((range) => range.end));
  const segments = [];
  if (firstActivityLine > 1) {
    segments.push({
      id: 'initial_context',
      role: 'operator_or_prior_prompt_context_before_first_tool_activity',
      ...lineRangeStats(lines, 1, firstActivityLine - 1),
    });
  }
  segments.push({
    id: 'agent_activity_trace',
    role: 'observed_agent_tool_activity_and_outputs',
    ...lineRangeStats(lines, firstActivityLine, Math.min(lastActivityLine, meaningfulEnd)),
  });
  if (lastActivityLine < meaningfulEnd) {
    segments.push({
      id: 'terminal_tail',
      role: 'post_activity_tail_or_final_assistant_message',
      ...lineRangeStats(lines, lastActivityLine + 1, meaningfulEnd),
    });
  }

  return {
    mode: 'segmented_by_first_tool_activity',
    first_activity_line: firstActivityLine,
    last_activity_line: Math.min(lastActivityLine, meaningfulEnd),
    segments,
  };
}

function segmentRoleForRange(sourceSegments, range) {
  const best = sourceSegments.segments?.find((segment) => rangesOverlap(segment.line_range, range));
  return best?.role || sourceSegments.mode || 'unsegmented_source';
}

function firstMeaningfulTitle(lines, fallback = 'source chunk') {
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const heading = sectionTitle(trimmed);
    return (heading || trimmed).slice(0, 140);
  }
  return fallback;
}

function chunkShouldBreak({ line, index, startIndex, chunkBytes, maxLines, maxBytes, nextBoundaryStarts }) {
  const lineCount = index - startIndex + 1;
  if (lineCount <= 1) return false;
  if (nextBoundaryStarts.has(index + 1) && (lineCount >= 8 || chunkBytes >= Math.floor(maxBytes * 0.45))) return true;
  if (lineCount < maxLines && chunkBytes < maxBytes) return false;
  return !line.trim() || lineCount >= maxLines + 12 || chunkBytes >= maxBytes + 1600;
}

function buildSourceChunks({ lines, timeline, sections, artifacts, traceBlocks, sourceSegments }) {
  const maxLines = 64;
  const maxBytes = 7200;
  const boundaryStarts = new Set([
    0,
    ...sections.map((section) => section.line_range.start - 1),
    ...traceBlocks.map((block) => block.line_range?.start - 1).filter((value) => value >= 0),
    ...timeline
      .filter((event) => evidenceRank(event) >= 4)
      .map((event) => event.line_range.start - 1),
  ]);
  const chunks = [];
  let start = 0;
  let chunkBytes = 0;

  const pushChunk = (endExclusive) => {
    if (endExclusive <= start) return;
    const blockLines = lines.slice(start, endExclusive);
    const range = { start: start + 1, end: endExclusive };
    const localTimeline = timeline.filter((event) => rangesOverlap(event.line_range, range));
    const localArtifacts = artifacts.filter((artifact) => rangesOverlap(artifact.line_range, range));
    const localEntities = buildEntitiesForRange(blockLines, start);
    const text = blockLines.join('\n');
    chunks.push({
      id: `chunk_${String(chunks.length + 1).padStart(4, '0')}`,
      role: segmentRoleForRange(sourceSegments, range),
      title: firstMeaningfulTitle(blockLines, `lines ${range.start}-${range.end}`),
      line_range: range,
      line_count: blockLines.length,
      byte_count: byteLength(text),
      char_count: text.length,
      event_count: localTimeline.length,
      artifact_count: localArtifacts.length,
      kind_counts: countBy(localTimeline, (event) => event.kind),
      entity_counts: {
        paths: localEntities.paths.length,
        commands: localEntities.commands.length,
        ids: localEntities.ids.length,
        hashes: localEntities.hashes.length,
      },
      top_entities: {
        paths: topEntityRows(localEntities.paths, 5),
        commands: topEntityRows(localEntities.commands, 5),
        ids: topEntityRows(localEntities.ids, 5),
        hashes: topEntityRows(localEntities.hashes, 5),
      },
      preview: snippet(blockLines, 10, 1200),
    });
  };

  for (let index = 0; index < lines.length; index += 1) {
    chunkBytes += byteLength(lines[index]) + 1;
    if (
      chunkShouldBreak({
        line: lines[index],
        index,
        startIndex: start,
        chunkBytes,
        maxLines,
        maxBytes,
        nextBoundaryStarts: boundaryStarts,
      })
    ) {
      pushChunk(index + 1);
      start = index + 1;
      chunkBytes = 0;
    }
  }
  pushChunk(lines.length);

  return chunks;
}

function pushPattern(map, key, lineNumber, text) {
  if (!key) return;
  const normalized = String(key).trim().toLowerCase();
  if (!normalized) return;
  const existing = map.get(normalized) || {
    value: String(key).trim(),
    count: 0,
    first_line: lineNumber,
    last_line: lineNumber,
    samples: [],
  };
  existing.count += 1;
  existing.last_line = lineNumber;
  if (existing.samples.length < 4) existing.samples.push({ line: lineNumber, text: text.slice(0, 220) });
  map.set(normalized, existing);
}

function sortedPatterns(map, { repeatedOnly = true, limit = 20 } = {}) {
  return Array.from(map.values())
    .filter((row) => !repeatedOnly || row.count > 1)
    .sort((left, right) => right.count - left.count || left.first_line - right.first_line || left.value.localeCompare(right.value))
    .slice(0, limit);
}

function buildPatternIndex(lines, timeline, sections, sourceChunks) {
  const prefixes = new Map();
  const exactLines = new Map();
  const headings = [];
  const longLines = [];
  const timeMarkers = [];

  lines.forEach((line, index) => {
    const lineNumber = index + 1;
    const trimmed = line.trim();
    if (!trimmed) return;

    const heading = sectionTitle(trimmed);
    if (heading) headings.push({ line: lineNumber, title: heading.slice(0, 180) });

    const prefix = trimmed.match(/^([A-Za-z][A-Za-z0-9_. -]{2,80}):\s*/)?.[1];
    if (prefix) pushPattern(prefixes, prefix, lineNumber, trimmed);

    if (trimmed.length >= 12 && trimmed.length <= 260) pushPattern(exactLines, trimmed, lineNumber, trimmed);
    const bytes = byteLength(line);
    if (bytes >= 1000) longLines.push({ line: lineNumber, bytes, preview: trimmed.slice(0, 220) });

    if (/\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)day\s+\d{1,2}:\d{2}\s*(?:AM|PM)?\b/i.test(trimmed) || /\b\d{4}-\d{2}-\d{2}T\d{2}[:.-]\d{2}/.test(trimmed)) {
      timeMarkers.push({ line: lineNumber, text: trimmed.slice(0, 220) });
    }
  });

  return {
    schema_version: 'trace_pattern_index_v1',
    purpose: 'Deterministic, non-authoritative motifs mined from the copied text so long captures can be browsed before exact source reading.',
    repeated_line_prefixes: sortedPatterns(prefixes, { repeatedOnly: true, limit: 24 }),
    repeated_exact_lines: sortedPatterns(exactLines, { repeatedOnly: true, limit: 16 }),
    section_markers: headings.slice(0, 60),
    time_markers: timeMarkers.slice(0, 40),
    long_lines: longLines.slice(0, 40),
    dense_chunks: sourceChunks
      .slice()
      .sort((left, right) => right.event_count + right.artifact_count - (left.event_count + left.artifact_count) || left.line_range.start - right.line_range.start)
      .slice(0, 16)
      .map((chunk) => ({
        id: chunk.id,
        title: chunk.title,
        line_range: chunk.line_range,
        event_count: chunk.event_count,
        artifact_count: chunk.artifact_count,
        entity_counts: chunk.entity_counts,
      })),
    timeline_kind_counts: countBy(timeline, (event) => event.kind),
    source_chunk_count: sourceChunks.length,
  };
}

function buildNavigationView({ losslessSource, sourceProfile, sourceSegments, sourceChunks, patternIndex }) {
  return {
    schema_version: 'trace_navigation_view_v1',
    purpose: 'Lossless-source navigation map for long or mixed clipboard captures.',
    source_authority: {
      exact_text: losslessSource.source_text_field,
      line_ranges: 'source_lines',
      chunks: 'source_chunks',
      derived_patterns: 'pattern_index',
    },
    long_clip_strategy: {
      raw_text_preserved: losslessSource.source_text_complete,
      raw_text_bytes: losslessSource.source_text_bytes,
      line_count: losslessSource.source_line_count,
      chunk_count: sourceChunks.length,
      chunks_cover_all_lines: sourceChunks.length > 0 && sourceChunks[0].line_range.start === 1 && sourceChunks[sourceChunks.length - 1].line_range.end === losslessSource.source_line_count,
      max_chunk_target_bytes: 7200,
      line_break_policy: losslessSource.source_lines_line_break_policy,
    },
    detected_shape: {
      trace_format: sourceProfile.detected_trace_format,
      primary_content_kind: sourceProfile.primary_content_kind,
      confidence: sourceProfile.confidence,
    },
    source_segments: {
      mode: sourceSegments.mode,
      first_activity_line: sourceSegments.first_activity_line,
      last_activity_line: sourceSegments.last_activity_line,
      segments: sourceSegments.segments.map((segment) => ({
        id: segment.id,
        role: segment.role,
        line_range: segment.line_range,
        line_count: segment.line_count,
        byte_count: segment.byte_count,
        preview: segment.preview,
      })),
    },
    pattern_summary: {
      repeated_line_prefixes: patternIndex.repeated_line_prefixes.length,
      repeated_exact_lines: patternIndex.repeated_exact_lines.length,
      section_markers: patternIndex.section_markers.length,
      time_markers: patternIndex.time_markers.length,
      long_lines: patternIndex.long_lines.length,
    },
    reader_rules: [
      'Start with source_chunks and pattern_index for map-level navigation when source_text is too large to read at once.',
      'Use source_text, not previews, when exact byte-level wording or final newline state matters.',
      'Use source_lines for line_range citations and focused reading; line endings are normalized there by design.',
      'Treat pattern_index as a mining aid only. It is not a semantic summary or contradiction resolver.',
    ],
  };
}

function providerFamily(traceFormat) {
  if (/claude/i.test(traceFormat)) return 'claude';
  if (/codex/i.test(traceFormat)) return 'codex';
  if (/standalone/i.test(traceFormat)) return 'standalone_source';
  if (/tool_trace/i.test(traceFormat)) return 'generic_tool_trace';
  return 'unknown';
}

function providerReadingMode(sourceProfile) {
  const family = providerFamily(sourceProfile.detected_trace_format);
  if (family === 'claude') {
    return {
      provider_family: 'claude',
      primary_signal: 'tool-boundary blocks plus embedded Read/Edited/Created artifacts',
      continuation_bias:
        'Read final tool/status blocks and file artifacts before writing a continuation; Claude exports often contain a long prior prompt before the actual tool trace.',
      caveat: 'Provider label is best effort. Treat source_lines and line ranges as authority.',
    };
  }
  if (family === 'codex') {
    return {
      provider_family: 'codex',
      primary_signal: 'ordered command/timeline receipts and concise status transitions',
      continuation_bias:
        'Read timeline order and command receipts first; Codex traces may carry fewer embedded file artifacts than Claude traces.',
      caveat: 'Provider label is best effort. Treat source_lines and line ranges as authority.',
    };
  }
  return {
    provider_family: family,
    primary_signal: 'source_lines plus generic timeline and artifact indexes',
    continuation_bias: 'Use source_segments to separate copied context from observed activity before deciding the next move.',
    caveat: 'Provider label is best effort. Treat source_lines and line ranges as authority.',
  };
}

function classifyWorkShape(summary) {
  if (summary.mutations > 0 && summary.validations > 0) return 'implementation_validation_wave';
  if (summary.mutations > 0) return 'implementation_wave';
  if (summary.validations > 0) return 'validation_or_triage_wave';
  if (summary.commands > 0) return 'investigation_or_navigation_wave';
  return 'conversation_or_source_capture';
}

function sampleLines(lines, predicate, limit = 8) {
  const rows = [];
  lines.forEach((line, index) => {
    if (rows.length >= limit) return;
    if (predicate(line)) rows.push({ line: index + 1, text: line.trim() });
  });
  return rows;
}

function buildStateCues(lines, timeline, summary, traceBlocks) {
  const validationEvents = timeline.filter((event) => event.kind === 'validation' || event.status !== 'not_stated');
  const validationPasses = validationEvents.filter((event) =>
    /\b(?:passed|passes|clean|exit=0|exit code 0|ok|success)\b/i.test(`${event.title}\n${event.snippet}`),
  );
  const validationFailures = validationEvents.filter((event) =>
    /\b(?:failed|failure|error|exit=1|not found|traceback|assertionerror)\b/i.test(`${event.title}\n${event.snippet}`),
  );
  const allGitStatusLines = sampleLines(lines, (line) => /^(?:[ MADRCU?!]{1,2})\s+\S/.test(line.trim()), Number.MAX_SAFE_INTEGER);
  const sampleGitStatusLines = allGitStatusLines.slice(0, 16);
  const stashRisk =
    lines.some((line) => /\bgit stash\b|\bstash pop\b/i.test(line)) &&
    lines.some((line) => /overwritten by merge|conflict/i.test(line));
  const liveEndpointMismatch =
    lines.some((line) => /\b(?:404|not found)\b/i.test(line)) &&
    lines.some((line) => /\b(?:curl|endpoint|backend|server|api)\b/i.test(line));
  const meaningfulEnd = lastMeaningfulLine(lines);
  const lastTraceEnd = traceBlocks.reduce((max, block) => Math.max(max, block.line_range?.end || 0), 0);

  return {
    mutation_events: summary.mutations,
    validation_events: summary.validations,
    commit_events: summary.commits,
    open_mutation_without_commit: summary.mutations > 0 && summary.commits === 0,
    terminal_trace_without_final_closeout: lastTraceEnd > 0 && lastTraceEnd >= meaningfulEnd - 2,
    validation_cues: {
      pass_event_count: validationPasses.length,
      fail_event_count: validationFailures.length,
      sample_pass_events: validationPasses.slice(0, 6).map((event) => ({
        title: event.title,
        line_range: event.line_range,
      })),
      sample_fail_events: validationFailures.slice(0, 6).map((event) => ({
        title: event.title,
        line_range: event.line_range,
      })),
    },
    git_cues: {
      status_like_line_count: allGitStatusLines.length,
      staged_like_line_count: allGitStatusLines.filter((row) => /^[MADRCU]\s/.test(row.text)).length,
      untracked_line_count: allGitStatusLines.filter((row) => /^\?\?\s/.test(row.text)).length,
      sample_status_lines: sampleGitStatusLines,
    },
    risk_cues: {
      stash_or_merge_conflict_seen: stashRisk,
      live_endpoint_or_runtime_mismatch_seen: liveEndpointMismatch,
    },
    cue_authority:
      'Parser cues are not live state. Re-run repo commands before claiming current git, backend, validation, or deployment status.',
  };
}

function buildContinuationView({ lines, sourceProfile, timeline, artifacts, traceBlocks, sections, summary, sourceSegments }) {
  return {
    purpose:
      'Provider-aware continuation and abstraction surface for downstream AI readers. It helps decide whether the clip asks to continue work, summarize evidence, or improve the clip compiler itself.',
    provider_reading_mode: providerReadingMode(sourceProfile),
    trace_shape: {
      detected_trace_format: sourceProfile.detected_trace_format,
      work_shape: classifyWorkShape(summary),
      primary_content_kind: sourceProfile.primary_content_kind,
      artifact_count: artifacts.length,
      trace_block_count: traceBlocks.length,
      section_count: sections.length,
    },
    source_segments: sourceSegments,
    final_assistant_message: findFinalAssistantMessage(lines),
    state_cues: buildStateCues(lines, timeline, summary, traceBlocks),
    downstream_reader_rules: [
      'Separate initial prompt/context from observed agent activity before drawing conclusions.',
      'If the operator asks for a process or compiler improvement, treat the named work inside the trace as a specimen, not as the target to continue.',
      'Use line_range pointers for exact status, git, validation, and artifact claims; never infer live repo state from a copied trace.',
      'Do not overfit a continuation packet to the specific feature named in one trace; extract the reusable work shape first.',
      'Preserve provider differences: Claude traces are artifact/tool-block heavy; Codex traces are usually command/timeline heavy.',
    ],
    operator_intent_branches: [
      {
        intent: 'continue_captured_work',
        use_when: 'The operator wants the producing Type A agent to finish the in-flight repo/task work.',
        first_reader_move:
          'Verify live worktree/index/runtime state, then use state_cues only as hypotheses for closeout or next action.',
        avoid: 'Do not paste a generic continuation prompt that ignores staged/untracked/validation cues.',
      },
      {
        intent: 'improve_clip_compiler',
        use_when: 'The operator complains about the clip packet, continuation quality, provider differences, or overfitting.',
        first_reader_move:
          'Inspect parser/app tests and improve the reusable packet shape; keep the captured feature as a test specimen only.',
        avoid: 'Do not keep iterating on the feature inside the trace unless the operator explicitly asks for that feature.',
      },
      {
        intent: 'summarize_or_compress_trace',
        use_when: 'The operator wants a compact explanation of what happened.',
        first_reader_move:
          'Summarize from source_segments, artifacts, and validation/git cues with line ranges; mark parser cues as non-authoritative.',
        avoid: 'Do not collapse source_lines into unsupported conclusions or hide failures behind a success narrative.',
      },
    ],
  };
}

function buildHandoffView({ lines, inputBytes, sourceProfile, timeline, artifacts, traceBlocks, entities, sections }) {
  const eventKindCounts = countBy(timeline, (event) => event.kind);
  const structuredSignalCount =
    (eventKindCounts.command || 0) +
    (eventKindCounts.mutation || 0) +
    (eventKindCounts.validation || 0) +
    (eventKindCounts.commit || 0) +
    artifacts.length +
    traceBlocks.length;

  return {
    purpose: 'Compact read-me-first view for a downstream AI that receives this JSON as an attachment.',
    source_integrity: {
      source_lines_complete: true,
      source_text_complete: true,
      source_line_count: lines.length,
      source_bytes: inputBytes,
      derived_indexes_are_lossy_navigation_aids: true,
      exact_wording_authority: 'source_text',
      line_range_authority: 'source_lines',
    },
    detected_shape: {
      trace_format: sourceProfile.detected_trace_format,
      primary_content_kind: sourceProfile.primary_content_kind,
      confidence: sourceProfile.confidence,
      provider_specificity: 'best_effort; downstream readers should rely on source_lines and line ranges, not provider labels alone',
    },
    coverage: {
      timeline_events: timeline.length,
      structured_signal_count: structuredSignalCount,
      artifacts: artifacts.length,
      trace_blocks: traceBlocks.length,
      sections: sections.length,
      unique_paths: entities.paths.length,
      unique_commands: entities.commands.length,
      unique_ids: entities.ids.length,
      unique_hashes: entities.hashes.length,
    },
    recommended_read_order: [
      'handoff_view',
      'navigation_view',
      'continuation_view',
      'summary',
      'query_index',
      'source_chunks',
      'pattern_index',
      'artifacts',
      'trace_blocks',
      'compression_view.selected_evidence',
      'source_lines for focused line-range reading',
      'source_text for exact raw wording',
    ],
    downstream_warning:
      'A small exported file means the copied source was small. A large source is preserved in source_text and source_lines even when the on-screen preview omits middle rows.',
  };
}

export function parseAgentTrace(text, sourceName = 'pasted-agent-trace.txt', generatedAt = new Date().toISOString()) {
  const lines = linesOf(text);
  const inputBytes = byteLength(text);
  const losslessSource = losslessSourceMetadata(text, lines, inputBytes);
  const timeline = buildTimeline(lines);
  const sections = buildSections(lines);
  const entities = buildEntities(lines);
  const built = buildArtifactsAndBlocks(lines);
  const standalone = (built.artifacts.length || built.traceBlocks.length || timeline.length)
    ? null
    : standaloneSourceArtifact(lines, sourceName);
  const artifacts = standalone ? [standalone] : built.artifacts;
  const traceBlocks = standalone
    ? [
        {
          id: 'block_0001',
          kind: 'standalone_source_file',
          artifact_id: standalone.id,
          title: standalone.title,
          line_range: standalone.line_range,
        },
      ]
    : built.traceBlocks;
  const sourceProfile = inferSourceProfile(lines, timeline, artifacts);
  const commands = timeline.filter((event) => event.kind === 'command').length;
  const mutations = timeline.filter((event) => event.kind === 'mutation').length;
  const validations = timeline.filter((event) => event.kind === 'validation' || event.status !== 'not_stated').length;
  const commits = timeline.filter((event) => event.kind === 'commit').length;
  const summary = {
    events: timeline.length,
    commands,
    mutations,
    validations,
    commits,
    artifacts: artifacts.length,
    trace_blocks: traceBlocks.length,
    paths: entities.paths.length,
    ids: entities.ids.length,
    hashes: entities.hashes.length,
    sections: sections.length,
  };
  const sourceSegments = buildSourceSegments(lines, timeline, traceBlocks);
  const sourceChunks = buildSourceChunks({
    lines,
    timeline,
    sections,
    artifacts,
    traceBlocks,
    sourceSegments,
  });
  const patternIndex = buildPatternIndex(lines, timeline, sections, sourceChunks);
  summary.source_chunks = sourceChunks.length;
  summary.patterns = patternIndex.repeated_line_prefixes.length + patternIndex.repeated_exact_lines.length + patternIndex.section_markers.length + patternIndex.time_markers.length;
  const handoffView = buildHandoffView({
    lines,
    inputBytes,
    sourceProfile,
    timeline,
    artifacts,
    traceBlocks,
    entities,
    sections,
  });
  const continuationView = buildContinuationView({
    lines,
    sourceProfile,
    timeline,
    artifacts,
    traceBlocks,
    sections,
    summary,
    sourceSegments,
  });
  const navigationView = buildNavigationView({
    losslessSource,
    sourceProfile,
    sourceSegments,
    sourceChunks,
    patternIndex,
  });
  const packetConformanceView = packetConformance(text, lines);

  return {
    schema_version: 'agent_trace_structured_v2',
    ai_parse_contract: {
      contract_version: '2026-05-06',
      purpose: 'Deterministic pre-structure of a pasted agent trace for later compression, audit, or restart-packet generation.',
      read_order: [
        'ai_parse_contract',
        'source',
        'lossless_source',
        'source_profile',
        'summary',
        'handoff_view',
        'navigation_view',
        'continuation_view',
        'query_index',
        'source_chunks',
        'pattern_index',
        'artifacts',
        'trace_blocks',
        'entities',
        'timeline',
        'sections',
        'compression_view',
        'source_lines',
        'source_text',
      ],
      authority: {
        authoritative_source_text: 'source_text is the exact copied source string. source_lines is the complete normalized line-row projection for line_range navigation.',
        derived_indexes: 'entities, timeline, sections, query_index, source_chunks, pattern_index, navigation_view, and compression_view are deterministic indexes over source_text/source_lines.',
        no_inference: 'This parser extracts observable text patterns only; it does not decide contradictions, infer missing state, or rewrite facts.',
      },
      field_guide: {
        source: 'Original filename, character count, line count, and stable non-cryptographic input hash.',
        lossless_source: 'Integrity metadata for source_text, including line-break profile and the source_text field name.',
        source_profile: 'Best-effort source-shape label distinguishing operator thread exports, Codex traces, Claude tool traces, generic traces, and standalone source files.',
        summary: 'Counts useful for routing and quick size checks.',
        handoff_view: 'Compact read-me-first surface for downstream AI attachment readers; source_text remains the exact-text authority and source_lines carries line-range navigation.',
        navigation_view: 'Read-me-first navigation surface for long captures: chunk strategy, source authority, segment roles, and reader rules.',
        continuation_view:
          'Provider-aware continuation and abstraction surface. Separates copied context from observed tool activity, names parser-only state cues, and offers non-overfit intent branches.',
        packet_conformance:
          'Generated-packet conformance receipt when the source is a parser-coupled packet such as B3 PACKET v=3.2; not a substitute for source_lines.',
        query_index: 'Small top-level lookup surface for event kinds, statuses, and most frequent identifiers.',
        source_chunks: 'Contiguous, line-ranged chunks covering the whole source for long-clip navigation. They carry previews and local entity/event counts.',
        pattern_index: 'Repeated prefixes, repeated exact lines, time markers, section markers, long lines, and dense chunks mined deterministically from source_lines.',
        artifacts: 'Line-ranged file/code artifacts detected inside tool traces or standalone source clipboard payloads. Content remains authoritative in source_lines.',
        trace_blocks: 'Coarse tool-action blocks such as command runs and file artifacts. These are navigation anchors over source_lines.',
        entities: 'Deduplicated paths, commands, ids, and hashes with counts plus first/last source lines.',
        timeline: 'Line-ranged event blocks with kind, status, title, snippet, and entities found inside each block.',
        sections: 'Detected markdown or key-value section blocks with 1-based inclusive line ranges.',
        compression_view: 'Evidence-focused subset for a downstream compression AI; source facts still come from source_lines and line-ranged snippets.',
        source_lines: 'Complete normalized source rows for line-range navigation.',
        source_text: 'Exact raw copied text. Use this when exact wording, line endings, or final newline state matters.',
      },
      downstream_ai_rules: [
        'Use line_range fields as evidence pointers back to source_lines.',
        'Treat status values as parser labels, not proof beyond the cited text.',
        'For very long captures, start with navigation_view, source_chunks, and pattern_index before reading source_text.',
        'Read continuation_view before drafting a continuation or process-refinement response; it separates provider shape, source segments, and non-authoritative state cues.',
        'Prefer compression_view.selected_evidence for compact restart packets, then inspect timeline/source_lines for exact wording.',
        'Do not treat omitted preview rows in the UI as omitted from the exported JSON.',
        'Do not treat source_chunks or pattern_index as destructive compression; they are projections over complete source_text.',
      ],
      annex_pattern_transfer: [
        {
          source: 'euphony annex',
          used_for: 'timeline-first trace inspection and local session JSON thinking',
          code_copied: false,
        },
        {
          source: 'codeflow annex',
          used_for: 'local-only file-to-structured-export workflow',
          code_copied: false,
        },
        {
          source: 'browser-harness annex',
          used_for: 'browser-native operator loop with a small local control surface',
          code_copied: false,
        },
        {
          source: 'make-interfaces-feel-better annex',
          used_for: 'compact numeric stats, stable hit areas, and dense controls',
          code_copied: false,
        },
      ],
    },
    generated_at: generatedAt,
    source: {
      name: sourceName,
      input_chars: text.length,
      input_bytes: inputBytes,
      input_lines: lines.length,
      input_hash: stableHash(text),
      line_breaks: losslessSource.line_breaks,
    },
    lossless_source: losslessSource,
    source_profile: sourceProfile,
    handoff_view: handoffView,
    navigation_view: navigationView,
    continuation_view: continuationView,
    packet_conformance: packetConformanceView,
    summary,
    query_index: {
      event_kind_counts: countBy(timeline, (event) => event.kind),
      status_counts: countBy(timeline, (event) => event.status),
      top_paths: topEntityRows(entities.paths),
      top_commands: topEntityRows(entities.commands, 12),
      top_ids: topEntityRows(entities.ids),
      top_hashes: topEntityRows(entities.hashes, 12),
      top_chunks: sourceChunks.slice(0, 24).map((chunk) => ({
        id: chunk.id,
        role: chunk.role,
        title: chunk.title,
        line_range: chunk.line_range,
        byte_count: chunk.byte_count,
        event_count: chunk.event_count,
        artifact_count: chunk.artifact_count,
        entity_counts: chunk.entity_counts,
      })),
      top_artifacts: artifacts.slice(0, 16).map((artifact) => ({
        id: artifact.id,
        kind: artifact.kind,
        title: artifact.title,
        path: artifact.path,
        language: artifact.language,
        line_range: artifact.line_range,
        content_line_range: artifact.content_line_range,
        content_bytes: artifact.content_bytes,
      })),
    },
    source_chunks: sourceChunks,
    pattern_index: patternIndex,
    artifacts,
    trace_blocks: traceBlocks,
    entities,
    timeline,
    sections,
    compression_view: {
      purpose: 'Source structuring for a later compression model: source profile, artifacts, trace blocks, evidence rows, line ranges, commands, paths, ids, hashes, and section blocks.',
      source_integrity: handoffView.source_integrity,
      coverage: handoffView.coverage,
      source_profile: sourceProfile,
      selected_artifacts: artifacts.slice(0, 80).map((artifact) => ({
        id: artifact.id,
        kind: artifact.kind,
        action: artifact.action,
        title: artifact.title,
        path: artifact.path,
        language: artifact.language,
        line_range: artifact.line_range,
        content_line_range: artifact.content_line_range,
        content_bytes: artifact.content_bytes,
        preview: artifact.preview,
      })),
      selected_evidence: timeline
        .filter((event) => ['command', 'mutation', 'validation', 'commit', 'section', 'packet', 'status'].includes(event.kind))
        .sort((left, right) => evidenceRank(right) - evidenceRank(left) || left.line_range.start - right.line_range.start)
        .slice(0, 120)
        .map((event) => ({
          kind: event.kind,
          title: event.title,
          line_range: event.line_range,
          evidence: event.snippet,
        })),
      source_integrity_note: 'No inference or contradiction resolution is performed by this parser. The JSON preserves observed source text with line ranges.',
    },
    source_lines: lines.map((line, index) => ({
      line: index + 1,
      text: line,
    })),
    source_text: text,
  };
}

function compactLineSamples(lines = [], head = 10, tail = 6) {
  if (!Array.isArray(lines) || lines.length <= head + tail) {
    return {
      mode: 'complete_under_sample_budget',
      omitted_line_count: 0,
      rows: lines.map((row) => ({ line: row.line, text: truncateText(row.text, 180) })),
    };
  }
  return {
    mode: 'head_tail_sample',
    omitted_line_count: lines.length - head - tail,
    rows: [
      ...lines.slice(0, head).map((row) => ({ line: row.line, text: truncateText(row.text, 180) })),
      {
        line: null,
        text: `[attachment clip: ${lines.length - head - tail} source lines omitted; full source is in local raw/full capture refs]`,
      },
      ...lines.slice(-tail).map((row) => ({ line: row.line, text: truncateText(row.text, 180) })),
    ],
  };
}

function compactEventEntities(entities = {}) {
  return {
    paths: (entities.paths || []).slice(0, 3),
    commands: (entities.commands || []).slice(0, 2),
    ids: (entities.ids || []).slice(0, 5),
    hashes: (entities.hashes || []).slice(0, 3),
  };
}

function compactChunks(chunks = [], limit = 80) {
  return chunks.slice(0, limit).map((chunk, index) => ({
    id: chunk.id,
    role: chunk.role,
    title: chunk.title,
    line_range: chunk.line_range,
    line_count: chunk.line_count,
    byte_count: chunk.byte_count,
    char_count: chunk.char_count,
    event_count: chunk.event_count,
    artifact_count: chunk.artifact_count,
    kind_counts: chunk.kind_counts,
    entity_counts: chunk.entity_counts,
    preview: index < 5 ? truncateText(chunk.preview, 140) : '',
    preview_policy: index < 5 ? 'included_for_first_5_chunks' : 'omitted_from_attachment_clip_use_full_packet_or_raw_source',
  }));
}

function compactTimeline(timeline = [], limit = 30) {
  return timeline.slice(0, limit).map((event) => ({
    id: event.id,
    kind: event.kind,
    title: truncateText(event.title, 120),
    line_range: event.line_range,
    status: event.status,
    command: truncateText(event.command, 120),
    snippet: truncateText(event.snippet, 120),
    entities: compactEventEntities(event.entities),
  }));
}

function compactKeyValues(values = {}) {
  return Object.fromEntries(
    Object.entries(values)
      .slice(0, 16)
      .map(([key, value]) => [key, truncateText(value, 140)]),
  );
}

function compactSections(sections = [], limit = 24) {
  return sections.slice(0, limit).map((section) => ({
    id: section.id,
    title: truncateText(section.title, 140),
    line_range: section.line_range,
    key_values: compactKeyValues(section.key_values),
    preview: truncateText(section.preview, 120),
  }));
}

function compactArtifacts(artifacts = [], limit = 80) {
  return artifacts.slice(0, limit).map((artifact) => ({
    id: artifact.id,
    kind: artifact.kind,
    action: artifact.action,
    title: artifact.title,
    path: artifact.path,
    language: artifact.language,
    line_range: artifact.line_range,
    content_line_range: artifact.content_line_range,
    change_stats: artifact.change_stats,
    content_line_count: Array.isArray(artifact.content_lines) ? artifact.content_lines.length : 0,
    content_bytes: artifact.content_bytes,
    content_hash: artifact.content_hash,
    preview: truncateText(artifact.preview, 400),
  }));
}

function compactCompressionView(view = {}) {
  return {
    purpose: view.purpose,
    source_integrity: view.source_integrity,
    coverage: view.coverage,
    source_profile: view.source_profile,
    selected_artifacts: (view.selected_artifacts || []).slice(0, 25).map((artifact) => ({
      ...artifact,
      preview: truncateText(artifact.preview, 260),
    })),
    selected_evidence: (view.selected_evidence || []).slice(0, 16).map((event) => ({
      ...event,
      title: truncateText(event.title, 120),
      evidence: truncateText(event.evidence, 120),
    })),
    source_integrity_note: view.source_integrity_note,
    attachment_clip_policy:
      'This compression view is bounded for upload. Use local_capture_refs.full_packet_path or raw_source_path for complete source text.',
  };
}

function compactQueryRows(rows = [], limit = 24) {
  return rows.slice(0, limit).map((row) => ({
    ...row,
    title: truncateText(row.title, 120),
    preview: truncateText(row.preview, 140),
  }));
}

function compactQueryIndex(index = {}) {
  return {
    event_kind_counts: index.event_kind_counts,
    status_counts: index.status_counts,
    top_paths: compactQueryRows(index.top_paths || [], 12),
    top_commands: compactQueryRows(index.top_commands || [], 10),
    top_ids: compactQueryRows(index.top_ids || [], 12),
    top_hashes: compactQueryRows(index.top_hashes || [], 10),
    top_chunks: compactQueryRows(index.top_chunks || [], 12),
    top_artifacts: compactQueryRows(index.top_artifacts || [], 10),
    omitted_policy: 'attachment clip keeps bounded query rows; full packet keeps complete query indexes',
  };
}

function compactPatternIndex(index = {}) {
  return {
    schema_version: index.schema_version,
    purpose: index.purpose,
    repeated_line_prefixes: compactQueryRows(index.repeated_line_prefixes || [], 40),
    repeated_exact_lines: compactQueryRows(index.repeated_exact_lines || [], 40),
    section_markers: (index.section_markers || []).slice(0, 60).map((row) => ({
      ...row,
      title: truncateText(row.title, 140),
    })),
    time_markers: compactQueryRows(index.time_markers || [], 40),
    long_lines: compactQueryRows(index.long_lines || [], 40),
    dense_chunks: compactQueryRows(index.dense_chunks || [], 30),
    timeline_kind_counts: index.timeline_kind_counts,
    source_chunk_count: index.source_chunk_count,
    omitted_policy: 'attachment clip keeps bounded pattern rows; full packet keeps complete pattern indexes',
  };
}

function compactEntities(entities = {}) {
  return {
    paths: topEntityRows(entities.paths || [], 80),
    commands: topEntityRows(entities.commands || [], 50),
    ids: topEntityRows(entities.ids || [], 80),
    hashes: topEntityRows(entities.hashes || [], 50),
    omitted_policy: 'attachment clip keeps top entities only; full packet keeps complete entity rows',
  };
}

function manifestText(value, maxChars = 120) {
  return truncateText(value, maxChars).replace(/\s+/g, ' ').trim();
}

function manifestChunkOutline(chunks = [], limit = 40) {
  return chunks.slice(0, limit).map((chunk) => ({
    id: chunk.id,
    role: chunk.role,
    title: manifestText(chunk.title, 100),
    line_range: chunk.line_range,
    line_count: chunk.line_count,
    byte_count: chunk.byte_count,
    event_count: chunk.event_count,
    artifact_count: chunk.artifact_count,
    kind_counts: chunk.kind_counts,
    entity_counts: chunk.entity_counts,
  }));
}

function manifestTimelineOutline(timeline = [], limit = 12) {
  return timeline.slice(0, limit).map((event) => ({
    id: event.id,
    kind: event.kind,
    title: manifestText(event.title, 100),
    line_range: event.line_range,
    status: event.status,
  }));
}

function manifestSectionOutline(sections = [], limit = 12) {
  return sections.slice(0, limit).map((section) => ({
    id: section.id,
    title: manifestText(section.title, 110),
    line_range: section.line_range,
    key_count: section.key_values ? Object.keys(section.key_values).length : 0,
  }));
}

function manifestArtifactOutline(artifacts = [], limit = 40) {
  return artifacts.slice(0, limit).map((artifact) => ({
    id: artifact.id,
    kind: artifact.kind,
    action: artifact.action,
    title: manifestText(artifact.title, 100),
    path: artifact.path,
    language: artifact.language,
    line_range: artifact.line_range,
    content_line_range: artifact.content_line_range,
    change_stats: artifact.change_stats,
    content_bytes: artifact.content_bytes,
    content_hash: artifact.content_hash,
  }));
}

function manifestTopEntities(entities = {}, limit = 8) {
  return {
    paths: topEntityRows(entities.paths || [], limit).map((row) => ({
      value: manifestText(row.value, 140),
      count: row.count,
      first_line: row.first_line,
      last_line: row.last_line,
    })),
    commands: topEntityRows(entities.commands || [], 5).map((row) => ({
      value: manifestText(row.value, 140),
      count: row.count,
      first_line: row.first_line,
      last_line: row.last_line,
    })),
    ids: topEntityRows(entities.ids || [], limit).map((row) => row.value),
    hashes: topEntityRows(entities.hashes || [], 5).map((row) => row.value),
  };
}

function packetSectionOutlineFromSourceLines(sourceLines = []) {
  const lines = sourceLines.map((row) => String(row?.text ?? ''));
  if (!lines.length || !lines.some((line) => line.trim() === B3_PACKET_START)) return null;

  const positions = b3SectionPositions(lines);
  const orderedSections = B3_TOP_LEVEL_FIELDS
    .map((section) => ({ section, index: positions[section] }))
    .filter((row) => row.index != null)
    .sort((left, right) => left.index - right.index);
  const sectionRows = orderedSections.map((row, index) => {
    const next = orderedSections[index + 1]?.index ?? lines.length;
    return {
      section: row.section,
      line_range: { start: row.index + 1, end: Math.max(row.index + 1, next) },
    };
  });

  const hotPathFields = [];
  for (const [index, line] of b3SectionLines(lines, positions, 'hot_path')) {
    const match = line.match(/^\s{2}([A-Za-z0-9_]+):\s*(.*)$/);
    if (match && B3_HOT_PATH_FIELDS.includes(match[1])) {
      hotPathFields.push({
        field: match[1],
        line: index + 1,
      });
    }
  }

  return {
    schema_version: 'b3_packet_outline_v1',
    packet_version: B3_PACKET_START,
    status: 'available',
    section_count: sectionRows.length,
    sections: sectionRows,
    hot_path_fields: hotPathFields,
    policy: 'Range-only outline. Read source_segments or raw sidecar for exact packet text.',
  };
}

function evidenceOutlineRows(packet, limit = 12) {
  const sourceRows = Array.isArray(packet.compression_view?.selected_evidence)
    ? packet.compression_view.selected_evidence
    : [];
  const rows = sourceRows.length
    ? sourceRows
    : (packet.timeline || [])
        .filter((event) => ['command', 'mutation', 'validation', 'commit', 'section', 'packet', 'status'].includes(event.kind))
        .sort((left, right) => evidenceRank(right) - evidenceRank(left) || left.line_range.start - right.line_range.start);
  return rows.slice(0, limit).map((row, index) => ({
    id: row.id || `evidence_${String(index + 1).padStart(4, '0')}`,
    kind: row.kind,
    title: manifestText(row.title, 120),
    line_range: row.line_range,
    status: row.status || undefined,
  }));
}

function readerIndexLimitForBudget(budgetProfile = {}, sourceBytes = 0) {
  if (sourceBytes < 12000) return 4;
  if (sourceBytes < 64000) return 8;
  if (sourceBytes < 256000) return 12;
  return Math.max(16, Math.min(24, Number(budgetProfile.timeline || 0) + 8));
}

function buildClipReaderIndex(packet, sourceSegments, budgetProfile = {}) {
  const sourceBytes = packet.lossless_source?.source_text_bytes || packet.source?.input_bytes || 0;
  const limit = readerIndexLimitForBudget(budgetProfile, sourceBytes);
  const packetOutline = packetSectionOutlineFromSourceLines(packet.source_lines || []);
  const conformance = packet.packet_conformance && packet.packet_conformance.status !== 'not_applicable'
    ? {
        status: packet.packet_conformance.status,
        issue_count: packet.packet_conformance.issue_count,
        issue_codes: packet.packet_conformance.issue_codes || [],
      }
    : null;

  return {
    schema_version: 'agent_trace_clip_reader_index_v1',
    purpose: 'Range-only start map; source text stays in source_segments or raw sidecar.',
    read_order: [
      'reader_index',
      packetOutline ? 'reader_index.packet_outline' : null,
      'reader_index.high_value_ranges',
      'terminal_state_index',
      'command_ledger',
      'validation_matrix',
      'source_segment_index',
      'source_segments_or_raw_sidecar',
      'navigation_manifest_when_present',
    ].filter(Boolean),
    source_shape: {
      detected_trace_format: packet.source_profile?.detected_trace_format || 'unknown',
      primary_content_kind: packet.source_profile?.primary_content_kind || 'unknown',
      provider_family: packet.continuation_view?.provider_reading_mode?.provider_family || 'unknown',
      source_line_count: packet.lossless_source?.source_line_count || packet.source?.input_lines || 0,
      source_byte_count: sourceBytes,
    },
    high_value_ranges: evidenceOutlineRows(packet, limit),
    packet_outline: packetOutline || undefined,
    packet_conformance: conformance || undefined,
    compaction_hints: buildCompactionHints(packet, packetOutline),
    source_segment_ranges: sourceSegmentIndexRows(sourceSegments).slice(0, Math.max(12, limit)).map((segment) => ({
      id: segment.id,
      line_range: segment.line_range,
      byte_range_utf8: segment.byte_range_utf8,
      starts_mid_line: segment.starts_mid_line,
      ends_mid_line: segment.ends_mid_line,
    })),
    policy: 'Choose ranges to restore; do not copy index rows as source facts.',
  };
}

function buildCompactionHints(packet, packetOutline = null) {
  const captureKind = packet.capture_context?.capture_kind || packet.source_profile?.primary_content_kind || 'unknown';
  return {
    schema_version: 'agent_trace_compaction_hints_v1',
    capture_kind: captureKind,
    source_partition: 'clip=bulk evidence; user text=salience/control unless SOURCE/facts',
    specimen_vs_target: 'clip/compaction request => trace is specimen, not task to continue',
    density_guard: 'default compact; expand only restart-changing distinctions',
    section_gate: 'optional sections need restart delta; otherwise []',
    example_guard: 'examples/prior answers are specimens unless labeled SOURCE',
    schema_overfit_guard: packetOutline
      ? 'source packet=input evidence, not field-fill template unless requested'
      : 'smallest output shape; no prior-schema copying by default',
  };
}

function boundedExcerptFromLines(lines = [], maxChars = 360) {
  const text = lines.map((line) => String(line || '').trimEnd()).join('\n').trim();
  if (!text) return null;
  if (text.length <= maxChars) return text;
  const head = text.slice(0, Math.floor(maxChars * 0.62)).trimEnd();
  const tail = text.slice(Math.max(0, text.length - Math.floor(maxChars * 0.28))).trimStart();
  return `${head}\n[excerpt omitted: ${text.length - head.length - tail.length} chars]\n${tail}`;
}

function sourceRowsToLines(sourceRows = []) {
  return Array.isArray(sourceRows) ? sourceRows.map((row) => String(row?.text ?? '')) : [];
}

function sliceRange(lines = [], range = null) {
  if (!range || typeof range.start !== 'number' || typeof range.end !== 'number') return [];
  return lines.slice(Math.max(0, range.start - 1), Math.max(0, range.end));
}

function rangeContains(range, line) {
  return range && typeof line === 'number' && range.start <= line && line <= range.end;
}

function commandStatusFromText(text) {
  const value = String(text || '');
  if (/\b(?:exit code|exit=)\s*[1-9]\b/i.test(value) || /\b(?:failed|failure|traceback|assertionerror|syntaxerror)\b/i.test(value)) {
    if (!/\bfail(?:ed|ure)?s?\s*0\b/i.test(value)) return 'fail';
  }
  if (
    /(?:^|\n)\s*✔/m.test(value) ||
    /\b(?:pass(?:ed|es)?|clean|success|ok=true|exit code 0|exit=0|valid_with_warnings)\b/i.test(value) ||
    /\b(?:fail|failed|error)_count\s*=\s*0\b/i.test(value) ||
    /\b(?:fail|failed)\s+0\b/i.test(value)
  ) {
    return 'pass';
  }
  return 'not_detected';
}

const TRACE_VALIDATION_STATUS_SEMANTICS = Object.freeze({
  not_detected: 'Parser did not find a signal in the captured source.',
  not_applicable: 'Signal is not expected for this artifact variant or capture shape.',
  unavailable: 'Signal requires an omitted/lossless source variant or live re-verification.',
  missing_required: 'Signal is required for promotion but absent from the captured evidence.',
});

const DENOISED_V0_VARIANT_CONTRACT = Object.freeze({
  variant_id: 'agent_trace_denoised_packet_v0',
  slice_variant: 'denoised_v0_operator_summary',
  materialization_state: 'ready_for_handoff',
  replay_state: 'blocked_without_lossless_sources',
  promotion_gate: 'handoff_ready_not_replay_ready',
  standalone_for: ['operational_handoff', 'next_move'],
  not_standalone_for: ['replay', 'byte_reconstruction', 'raw_source_reconstruction'],
  requires_for_replay: [
    'agent_trace_compact_json_v2',
    'agent_trace_canonical_full_json_v1',
    'provider_session_jsonl_source_v1',
  ],
  lossiness: {
    raw_source_reconstructable: false,
    model_lossless: false,
    copied_source_reconstructable: false,
    byte_lossless: false,
  },
  omitted: {
    event_stream: true,
    large_bodies: true,
  },
});

function commandExitCode(text) {
  const match = String(text || '').match(/\b(?:exit code|exited with code|exit=)\s*(\d+)\b/i);
  return match ? Number(match[1]) : null;
}

function commandHead(command = '') {
  const firstLine = String(command || '')
    .replace(/^\$\s+/, '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean) || '';
  return firstLine.split(/\s+(?:&&|\|\||;|\|)\s+/, 1)[0].trim();
}

function commandHeadTokens(command = '') {
  const head = commandHead(command);
  if (!head) return [];
  return head
    .match(/"[^"]*"|'[^']*'|\S+/g)
    ?.map((token) => token.replace(/^['"]|['"]$/g, ''))
    .filter((token) => token && !/^(?:>|>>|2>|2>>|2>&1)$/.test(token) && !token.startsWith('>') && !token.startsWith('2>'))
    || [];
}

function commandScriptSurface(command = '') {
  let tokens = commandHeadTokens(command);
  while (tokens.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(tokens[0])) tokens = tokens.slice(1);
  if (tokens[0]?.split('/').at(-1) === 'env') {
    tokens = tokens.slice(1);
    while (tokens.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(tokens[0])) tokens = tokens.slice(1);
  }
  const exe = tokens[0]?.split('/').at(-1) || '';
  if (['repo-python', 'python', 'python3'].includes(exe)) {
    if (tokens[1] === '-m') return { exe, script: tokens[2] || '', args: tokens.slice(3), kind: 'module' };
    return { exe, script: tokens[1] || '', args: tokens.slice(2), kind: 'python_arg' };
  }
  return { exe, script: tokens[0] || '', args: tokens.slice(1), kind: 'exec' };
}

function basename(value = '') {
  return String(value || '').split('/').at(-1) || '';
}

function classifyCommandRole(command = '') {
  const { exe, script, args, kind } = commandScriptSurface(command);
  const scriptBase = basename(script);
  const lowerScript = String(script || '').toLowerCase();
  const lowerArgs = args.map((arg) => String(arg || '').toLowerCase());
  const joinedArgs = lowerArgs.join(' ');
  if (!exe && !script) return 'discovery';
  if (kind === 'python_arg' && ['-', '-c'].includes(script)) return 'diagnostic';

  if (scriptBase === 'closeout_executor.py') return 'governance';
  if (scriptBase === 'mission_transaction_preflight.py') return 'governance';
  if (scriptBase === 'git_state_snapshot.py' && lowerArgs.includes('--closeout-conditions')) return 'governance';
  if (scriptBase === 'run_git.py' && lowerArgs.includes('audit') && lowerArgs.includes('push')) return 'governance';
  if (scriptBase === 'scoped_commit.py' || /(?:^|\/)\.\/checkpoint$/.test(script)) return 'governance';
  if (scriptBase === 'work_ledger.py' && lowerArgs.includes('session-finalize')) return 'governance';
  if (
    scriptBase === 'task_ledger_apply.py' &&
    lowerArgs.some((arg) => ['quick-capture', 'capture', 'note', 'transition', 'sign-off', 'execution-receipt'].includes(arg))
  ) {
    return 'governance';
  }

  if (['pytest', 'repo-pytest'].includes(exe)) return 'validation';
  if (exe === 'node' && lowerArgs.some((arg) => ['--check', '--test'].includes(arg))) return 'validation';
  if (['swiftc', 'swift'].includes(exe) && lowerArgs.some((arg) => ['-parse', 'test', 'build'].includes(arg))) return 'validation';
  if (exe === 'npm' && lowerArgs.some((arg) => ['test', 'build'].includes(arg))) return 'validation';
  if (kind === 'module' && ['py_compile', 'json.tool'].includes(lowerScript)) return 'validation';
  if (scriptBase === 'task_ledger_apply.py' && lowerArgs.includes('validate')) return 'validation';
  if (scriptBase.startsWith('check_') || lowerArgs.includes('--check')) return 'validation';
  if (
    scriptBase.endsWith('_test.py') ||
    scriptBase.startsWith('test_') ||
    ['trace_variant_smoke.py', 'trace_size_smoke.py', 'trace_capsule_unit_test.py'].includes(scriptBase) ||
    lowerScript.includes('pytest')
  ) {
    return 'validation';
  }

  if (scriptBase === 'kernel.py' && /--(?:info|preflight|pulse|phase|entry)\b/.test(joinedArgs)) return 'bootstrap';
  if (scriptBase === 'kernel.py' || /--(?:context-pack|navigation-metabolism|kind-atlas|option-surface|docs-route|paper-module)\b/.test(joinedArgs)) return 'discovery';
  if (['rg', 'grep', 'sed', 'cat', 'ls', 'find', 'jq', 'wc', 'tail', 'head', 'nl'].includes(exe)) return 'search';
  if (['git', 'repo-git'].includes(exe) && lowerArgs.some((arg) => ['status', 'diff', 'log', 'show'].includes(arg))) return 'final_inspection';
  if (/\b(?:apply_patch|--write|--fix|--update|build_|fingerprints\.py\s+--write)\b/.test(commandHead(command).toLowerCase())) return 'edit';
  return 'discovery';
}

function commandOutputLines(lines, outputRange) {
  if (!outputRange) return [];
  return sliceRange(lines, outputRange).filter((line) => String(line).trim());
}

function buildCommandRecord({ id, command, sourceLineRange, commandLineRange, outputLineRange, lines, source }) {
  const outputLines = commandOutputLines(lines, outputLineRange);
  const adjacentStatusLine = sourceLineRange?.end != null ? lines[sourceLineRange.end] || '' : '';
  const outputText = outputLines.join('\n');
  const outputExcerpt = outputLines.length ? boundedExcerptFromLines(outputLines, 1200) : null;
  const statusText = [outputText || boundedExcerptFromLines(sliceRange(lines, sourceLineRange), 500) || '', adjacentStatusLine]
    .filter(Boolean)
    .join('\n');
  return {
    id,
    command: manifestText(command, 260),
    normalized_command: String(command || '').replace(/\s+/g, ' ').trim().slice(0, 260),
    source_line_range: sourceLineRange,
    command_line_range: commandLineRange || sourceLineRange,
    output_line_range: outputLineRange || null,
    role: classifyCommandRole(command),
    status: commandStatusFromText(statusText),
    exit_code: commandExitCode(statusText),
    source,
    output_excerpt: outputExcerpt,
    output_hash: outputLines.length ? stableHash(outputText) : null,
    output_line_count: outputLines.length,
    output_char_count: outputText.length,
    output_excerpt_truncated: Boolean(outputExcerpt && outputText.length > outputExcerpt.length),
  };
}

function detectedInlineCommands(line) {
  const commands = [];
  const direct = line.trim().match(/^\$\s+(.+)$/);
  const anchored = line.trim().match(ANCHORED_COMMAND_RE) || line.trim().match(SCRIPT_COMMAND_RE);
  if (direct?.[1]) commands.push(direct[1].trim());
  if (anchored?.[1]) commands.push(anchored[1].trim());
  for (const match of line.matchAll(BACKTICK_COMMAND_RE)) {
    if (match[1]) commands.push(match[1].trim());
  }
  return uniq(commands);
}

function buildCommandLedger(packet) {
  const lines = sourceRowsToLines(packet.source_lines);
  const records = [];
  const seen = new Set();
  const commandBlocks = (packet.trace_blocks || []).filter((block) => block.kind === 'command_run' && block.command);

  for (const block of commandBlocks) {
    const key = `${block.command_line_range?.start || block.line_range?.start}:${block.command}`;
    seen.add(key);
    records.push(buildCommandRecord({
      id: `cmd_${String(records.length + 1).padStart(4, '0')}`,
      command: block.command,
      sourceLineRange: block.line_range,
      commandLineRange: block.command_line_range || block.line_range,
      outputLineRange: block.output_line_range || null,
      lines,
      source: 'tool_output',
    }));
  }

  lines.forEach((line, index) => {
    const lineNumber = index + 1;
    const commands = detectedInlineCommands(line);
    for (const command of commands) {
      const key = `${lineNumber}:${command}`;
      if (seen.has(key)) continue;
      if (commandBlocks.some((block) => rangeContains(block.line_range, lineNumber) && block.command === command)) continue;
      seen.add(key);
      records.push(buildCommandRecord({
        id: `cmd_${String(records.length + 1).padStart(4, '0')}`,
        command,
        sourceLineRange: { start: lineNumber, end: lineNumber },
        commandLineRange: { start: lineNumber, end: lineNumber },
        outputLineRange: null,
        lines,
        source: /^\s*\$/.test(line) ? 'tool_output' : 'source_claimed',
      }));
    }
  });

  records.sort((left, right) => left.command_line_range.start - right.command_line_range.start || left.command.localeCompare(right.command));
  records.forEach((record, index) => {
    record.id = `cmd_${String(index + 1).padStart(4, '0')}`;
  });

  return {
    schema_version: 'agent_trace_command_ledger_v1',
    purpose: 'All detected shell/tool commands as bounded pointers; output is excerpted and hashed, source text remains authoritative in source_segments or raw sidecar.',
    command_count: records.length,
    role_counts: countBy(records, (record) => record.role),
    status_counts: countBy(records, (record) => record.status),
    records,
    policy: 'Every command detected by the parser is represented once. Read source_line_range/output_line_range for exact wording and output.',
  };
}

function linePointer(row, line) {
  return {
    line,
    text: manifestText(row, 180),
  };
}

function findLinesMatching(lines, predicate, limit = 16) {
  const rows = [];
  lines.forEach((line, index) => {
    if (rows.length >= limit) return;
    if (predicate(line, index + 1)) rows.push(linePointer(line, index + 1));
  });
  return rows;
}

function rangeFromRows(rows) {
  if (!rows.length) return null;
  return { start: rows[0].line, end: rows[rows.length - 1].line };
}

function detectedObject(rows, status, extra = {}) {
  if (!rows || !rows.length) return { status: 'not_detected' };
  return {
    status,
    line_range: rangeFromRows(rows),
    rows,
    ...extra,
  };
}

function isCodexUiTimestamp(line = '') {
  return /^\d{1,2}:\d{2}\s*(?:AM|PM)$/i.test(String(line || '').trim());
}

function isCodexUiActivitySummary(line = '') {
  const trimmed = String(line || '').trim();
  if (!trimmed) return false;
  if (trimmed === 'Context automatically compacted') return true;
  return /^(?:Explored|Read|Searched|Opened|Found|Ran|Edited|Created|Wrote|Deleted)\b.*\b(?:files?|commands?|searches?|lists?|tools?)\b/i.test(trimmed);
}

function previousMeaningfulLine(lines, beforeLine) {
  for (let line = Math.min(lines.length, beforeLine); line >= 1; line -= 1) {
    if (String(lines[line - 1] || '').trim()) return line;
  }
  return 0;
}

function nextMeaningfulLine(lines, afterIndex, endLine) {
  for (let index = Math.max(0, afterIndex); index < Math.min(lines.length, endLine); index += 1) {
    if (String(lines[index] || '').trim()) return index + 1;
  }
  return null;
}

function isUiReviewCardStart(lines, index, effectiveEndLine) {
  const start = String(lines[index] || '').trim();
  if (!/^(?:Edited|Created|Wrote|Deleted)\s+\d+\s+files?$/i.test(start)) return false;
  const tail = lines
    .slice(index, Math.max(index + 1, effectiveEndLine))
    .map((line) => String(line || '').trim())
    .filter(Boolean);
  const hasChangeStats = tail.some((line) => /^\+\d+$/.test(line)) || tail.some((line) => /^-\d+$/.test(line));
  const hasUiChrome = tail.some((line) => /^(?:Undo|Review|Show \d+ more files?)$/i.test(line));
  const hasPath = tail.some((line) => extractPaths(line).length > 0);
  return hasChangeStats && (hasUiChrome || hasPath);
}

function effectiveTerminalMessageEndLine(lines) {
  let endLine = lastMeaningfulLine(lines);
  while (endLine > 0 && isCodexUiTimestamp(lines[endLine - 1])) {
    endLine = previousMeaningfulLine(lines, endLine - 1);
  }
  const scanStart = Math.max(0, endLine - 24);
  for (let index = endLine - 1; index >= scanStart; index -= 1) {
    if (isUiReviewCardStart(lines, index, endLine)) {
      return previousMeaningfulLine(lines, index);
    }
  }
  return endLine;
}

function finalMessageRow(lines, start, end, source) {
  const lineRange = { start, end };
  const block = sliceRange(lines, lineRange);
  const meaningful = block.filter((line) => String(line || '').trim());
  if (!meaningful.length) return { status: 'not_detected' };
  const text = block.map((line) => String(line || '').trimEnd()).join('\n').trim();
  const bodyComplete = text.length <= FINAL_MESSAGE_BODY_CHARS;
  const body = bodyComplete
    ? text
    : boundedExcerptFromLines(block, FINAL_MESSAGE_BODY_CHARS);
  return {
    schema_version: 'agent_trace_final_assistant_message_v1',
    status: 'source_claimed',
    line_range: lineRange,
    line_count: meaningful.length,
    char_count: text.length,
    byte_count: byteLength(text),
    body_char_limit: FINAL_MESSAGE_BODY_CHARS,
    body_is_complete: bodyComplete,
    omitted_char_count: bodyComplete ? 0 : Math.max(0, text.length - String(body || '').length),
    summary: manifestText(boundedExcerptFromLines(block, FINAL_MESSAGE_SUMMARY_CHARS), FINAL_MESSAGE_SUMMARY_CHARS),
    body,
    excerpt: body,
    recovery: {
      source_authority: 'source_text/source_lines',
      line_range: lineRange,
      rule: 'If body_is_complete is false, recover the exact message from the captured source by this line_range; for lossless clips, use source_segments or raw_sidecar per clip_contract.',
    },
    source,
  };
}

function blockIsOnlyUiChrome(lines) {
  const meaningful = lines.map((line) => String(line || '').trim()).filter(Boolean);
  if (!meaningful.length) return true;
  return meaningful.every((line) =>
    /^\+\d+$/.test(line) ||
    /^-\d+$/.test(line) ||
    /^(?:Undo|Review|Show \d+ more files?)$/i.test(line) ||
    isCodexUiTimestamp(line) ||
    extractPaths(line).length > 0
  );
}

function findFinalAssistantMessage(lines) {
  const endLine = effectiveTerminalMessageEndLine(lines);
  if (!endLine) return { status: 'not_detected' };

  for (let index = endLine - 1; index >= 0; index -= 1) {
    if (String(lines[index] || '').trim() !== 'Assistant') continue;
    const start = nextMeaningfulLine(lines, index + 1, endLine);
    if (!start) continue;
    const block = sliceRange(lines, { start, end: endLine });
    if (blockIsOnlyUiChrome(block)) continue;
    return finalMessageRow(lines, start, endLine, 'explicit_assistant_tail');
  }

  for (let index = endLine - 1; index >= 0; index -= 1) {
    if (!isCodexUiActivitySummary(lines[index])) continue;
    if (isUiReviewCardStart(lines, index, endLine)) continue;
    const start = nextMeaningfulLine(lines, index + 1, endLine);
    if (!start) continue;
    const block = sliceRange(lines, { start, end: endLine });
    if (blockIsOnlyUiChrome(block)) continue;
    return finalMessageRow(lines, start, endLine, 'codex_ui_post_activity_message');
  }

  return { status: 'not_detected' };
}

function sourceClaimedValidationResult(event, lines) {
  const result = commandStatusFromText(`${event.title}\n${event.snippet}`);
  if (result !== 'not_detected') return { result };
  return {
    result: 'unavailable',
    result_reason: 'source_claimed_validation_without_machine_result',
    requires: ['captured_source_range', 'lossless_source_variant_or_live_validation'],
  };
}

function postCommitStatusChecks(latestCommit, postCommitCommands) {
  if (postCommitCommands.length) {
    return {
      status: 'tool_output',
      command_ids: postCommitCommands.map((record) => record.id),
      line_range: {
        start: Math.min(...postCommitCommands.map((record) => record.source_line_range.start)),
        end: Math.max(...postCommitCommands.map((record) => record.source_line_range.end)),
      },
    };
  }
  if (latestCommit?.status === 'source_claimed') {
    return {
      status: 'missing_required',
      reason: 'latest_commit_detected_without_post_commit_status_checks',
      latest_commit_hash: latestCommit.hash || null,
      requires: ['final_inspection', 'validation', 'receipt'],
    };
  }
  return {
    status: 'not_applicable',
    reason: 'no_commit_claim_detected',
  };
}

function findFinalCloseout(lines, sourceSegments) {
  const finalAssistantMessage = findFinalAssistantMessage(lines);
  if (finalAssistantMessage.status !== 'not_detected') {
    return {
      schema_version: 'agent_trace_final_closeout_pointer_v1',
      status: finalAssistantMessage.status,
      line_range: finalAssistantMessage.line_range,
      line_count: finalAssistantMessage.line_count,
      char_count: finalAssistantMessage.char_count,
      byte_count: finalAssistantMessage.byte_count,
      summary: finalAssistantMessage.summary,
      body_ref: 'terminal_state_index.final_assistant_message',
      body_is_complete: finalAssistantMessage.body_is_complete,
      omitted_char_count: finalAssistantMessage.omitted_char_count,
      recovery: finalAssistantMessage.recovery,
      source: `${finalAssistantMessage.source}:final_closeout_preferred`,
    };
  }
  const terminalTail = (sourceSegments?.segments || []).find((segment) => segment.id === 'terminal_tail' || segment.role === 'post_activity_tail_or_final_assistant_message');
  if (terminalTail?.line_range) {
    return {
      status: 'source_claimed',
      line_range: terminalTail.line_range,
      summary: manifestText(boundedExcerptFromLines(sliceRange(lines, terminalTail.line_range), 280), 280),
      source: 'source_segment:terminal_tail',
    };
  }
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    if (/(?:navigation_seed_used|general_artifacts_checked|refinement_result|discoverability_refresh|Implemented|Committed|Validation|Final closeout|What changed)/i.test(lines[index])) {
      const start = Math.max(1, index + 1);
      const end = lastMeaningfulLine(lines);
      return {
        status: 'source_claimed',
        line_range: { start, end },
        summary: manifestText(boundedExcerptFromLines(sliceRange(lines, { start, end }), 280), 280),
        source: 'tail_marker',
      };
    }
  }
  return { status: 'not_detected' };
}

function latestCommitCue(lines) {
  const rows = findLinesMatching(
    lines,
    (line) => /\b(?:commit|committed|commit:)\b/i.test(line) && /\b[a-f0-9]{7,40}\b/i.test(line),
    Number.MAX_SAFE_INTEGER,
  );
  const latest = rows.at(-1);
  if (!latest) return { status: 'not_detected' };
  const hash = latest.text.match(/\b[a-f0-9]{7,40}\b/i)?.[0] || null;
  const statRows = findLinesMatching(
    lines.slice(latest.line - 1, Math.min(lines.length, latest.line + 12)),
    (line) => /\b(?:files? changed|insertions?\(\+\)|deletions?\(-\)|\+\d+\s+-\d+)\b/i.test(line),
    4,
  ).map((row) => ({ ...row, line: row.line + latest.line - 1 }));
  return {
    status: 'source_claimed',
    line_range: statRows.length ? { start: latest.line, end: statRows.at(-1).line } : { start: latest.line, end: latest.line },
    hash,
    title: latest.text,
    stat_rows: statRows,
  };
}

function commandEvidenceBucket(record) {
  const role = record?.role || '';
  if (role === 'validation') return 'checks';
  if (role === 'governance' || role === 'receipt' || role === 'commit') return 'governance_receipts';
  if (['bootstrap', 'discovery', 'search', 'final_inspection', 'diagnostic'].includes(role)) return 'diagnostics';
  return null;
}

function evidenceResult(record, bucket) {
  const rawStatus = record?.status || 'not_detected';
  const status = ['pass', 'fail'].includes(rawStatus)
    ? rawStatus
    : record?.exit_code === 0
      ? 'pass'
      : Number(record?.exit_code) > 0
        ? 'fail'
        : rawStatus;
  const output = `${record?.output_excerpt || ''}`.toLowerCase();
  if (
    bucket === 'governance_receipts' &&
    status === 'pass' &&
    (output.includes('"status": "blocked"') || output.includes('"stop_reason":') || output.includes('"direct_push_allowed": false'))
  ) {
    return 'other';
  }
  if (status === 'pass' || status === 'fail') return status;
  return 'other';
}

function resultCountObject(rows) {
  const pass = rows.filter((row) => row.result === 'pass').length;
  const fail = rows.filter((row) => row.result === 'fail').length;
  return {
    pass,
    fail,
    other: Math.max(0, rows.length - pass - fail),
    total: rows.length,
  };
}

function buildValidationMatrix(commandLedger, packet) {
  const lines = sourceRowsToLines(packet.source_lines);
  const commandRows = (commandLedger.records || [])
    .map((record, index) => {
      const bucket = commandEvidenceBucket(record);
      if (!bucket) return null;
      return {
        id: `evidence_${String(index + 1).padStart(4, '0')}`,
        kind: `${bucket.replace(/s$/, '')}_command`,
        bucket,
        evidence_bucket: bucket,
        command_id: record.id,
        command: record.command,
        source_line_range: record.source_line_range,
        output_line_range: record.output_line_range,
        result: evidenceResult(record, bucket),
        result_source: record.source,
        exit_code: record.exit_code,
        output_excerpt: record.output_excerpt,
        output_hash: record.output_hash,
      };
    })
    .filter(Boolean);
  const coveredRanges = commandRows.map((record) => record.source_line_range);
  const sourceClaimed = (packet.timeline || [])
    .filter((event) => event.kind === 'validation' || event.status !== 'not_stated')
    .filter((event) => !coveredRanges.some((range) => rangesOverlap(range, event.line_range)))
    .slice(0, 40)
    .map((event, index) => {
      const validationResult = sourceClaimedValidationResult(event, lines);
      return {
        id: `validation_claim_${String(index + 1).padStart(4, '0')}`,
        kind: 'source_claimed_validation',
        bucket: 'checks',
        evidence_bucket: 'checks',
        title: manifestText(event.title, 180),
        source_line_range: event.line_range,
        result: validationResult.result,
        result_reason: validationResult.result_reason || null,
        requires: validationResult.requires || null,
        result_source: 'source_claimed',
        evidence_excerpt: boundedExcerptFromLines(sliceRange(lines, event.line_range), 260),
      };
    });
  const rows = [...commandRows, ...sourceClaimed];
  const checkRows = rows.filter((row) => row.bucket === 'checks');
  const governanceRows = rows.filter((row) => row.bucket === 'governance_receipts');
  const diagnosticRows = rows.filter((row) => row.bucket === 'diagnostics');
  const matrix = {
    schema_version: 'agent_trace_validation_matrix_v1',
    purpose: 'Typed evidence rows: checks, governance receipts, and diagnostics stay separated.',
    status_semantics: TRACE_VALIDATION_STATUS_SEMANTICS,
    validation_count: checkRows.length,
    command_validation_count: commandRows.filter((row) => row.bucket === 'checks').length,
    source_claimed_validation_count: sourceClaimed.length,
    governance_receipt_count: governanceRows.length,
    diagnostic_count: diagnosticRows.length,
    evidence_count: rows.length,
    result_counts: countBy(checkRows, (row) => row.result),
    rows,
    proof_index: rows.map((row) => ({
      id: row.id,
      proof_kind: row.kind,
      bucket: row.bucket || null,
      source_line_range: row.source_line_range,
      output_line_range: row.output_line_range || null,
      result: row.result,
      establishes: 'source-stated validation/proof only; does not prove live current state',
    })),
    policy: 'Preserve command/result boundaries without mirroring full outputs.',
  };
  if (rows.length > 0) {
    matrix.bucket_counts = {
      checks: resultCountObject(checkRows),
      governance_receipts: resultCountObject(governanceRows),
      diagnostics: resultCountObject(diagnosticRows),
    };
  }
  return matrix;
}

function buildTerminalStateIndex(packet, sourceSegments, commandLedger, validationMatrix) {
  const lines = sourceRowsToLines(packet.source_lines);
  const latestCommit = latestCommitCue(lines);
  const commitLine = latestCommit.line_range?.start || null;
  const postCommitCommands = commitLine
    ? (commandLedger.records || []).filter((record) =>
        record.command_line_range.start >= commitLine &&
        ['final_inspection', 'validation', 'receipt', 'governance', 'commit'].includes(record.role),
      ).slice(0, 16)
    : [];
  const receiptRows = findLinesMatching(
    lines,
    (line) => /\b(?:Task Ledger|task_ledger|receipt|quick-capture|valid_with_warnings|error_count=0)\b/i.test(line),
    16,
  );
  const boundaryRows = findLinesMatching(
    lines,
    (line) => /\b(?:not[-_ ]done|explicit_not_done|blocked|stated_blocked|public_claim_allowed=false|not pushed|left uncommitted|skipped|remaining gaps?)\b/i.test(line),
    16,
  );
  const validationRows = validationMatrix.rows || [];
  const validationRange = validationRows.length
    ? {
        start: Math.min(...validationRows.map((row) => row.source_line_range.start)),
        end: Math.max(...validationRows.map((row) => row.source_line_range.end)),
      }
    : null;

  return {
    schema_version: 'agent_trace_terminal_state_index_v1',
    purpose: 'Pointers to terminal state evidence without deciding live truth beyond captured source text.',
    final_assistant_message: findFinalAssistantMessage(lines),
    final_closeout_prose: findFinalCloseout(lines, sourceSegments),
    latest_commit: latestCommit,
    post_commit_status_checks: postCommitStatusChecks(latestCommit, postCommitCommands),
    validation_summary: validationRows.length
      ? {
          status: validationRows.some((row) => row.result_source === 'tool_output') ? 'tool_output' : 'source_claimed',
          validation_count: validationRows.length,
          result_counts: validationMatrix.result_counts,
          line_range: validationRange,
        }
      : { status: 'not_applicable', reason: 'no_validation_rows_detected' },
    receipt_status: detectedObject(receiptRows, receiptRows.some((row) => /task_ledger_apply|quick-capture/i.test(row.text)) ? 'tool_output' : 'source_claimed'),
    explicit_not_done_or_blocked_boundaries: detectedObject(boundaryRows, 'source_claimed'),
    authority: 'Terminal indexes are captured-source pointers. Re-run live commands before claiming current repo state.',
  };
}

function deltaStateFromText(text = '') {
  const value = String(text || '').toLowerCase();
  if (/\b(?:committed|commit|files? changed|insertions?\(\+\)|deletions?\(-\))\b/.test(value)) return 'committed';
  if (/\b(?:generated|refresh|fingerprints|runs_index|builder)\b/.test(value)) return 'generated';
  if (/\b(?:queued|pending|proposal|proposed|source_stated_proposals)\b/.test(value)) return 'proposed';
  if (/\b(?:edited|created|wrote|patched|modified|changed|deleted)\b/.test(value)) return 'edited';
  if (/\b(?:read|inspected|opened|searched|rg|grep|discovered)\b/.test(value)) return 'discovered';
  return 'discovered';
}

function artifactState(artifact = {}) {
  if (artifact.kind === 'file_created') return 'edited';
  if (artifact.kind === 'file_edit' || artifact.kind === 'file_written' || artifact.kind === 'file_deleted') return 'edited';
  if (artifact.kind === 'file_read') return 'discovered';
  if (artifact.kind === 'standalone_source_file') return 'captured';
  return 'discovered';
}

function extractDeltaStats(lines) {
  return findLinesMatching(
    lines,
    (line) => /\b\d+\s+files? changed\b|\b\d+\s+insertions?\(\+\)|\b\d+\s+deletions?\(-\)|\+\d+\s+-\d+/.test(line),
    12,
  );
}

function buildArtifactDeltaIndex(packet) {
  const lines = sourceRowsToLines(packet.source_lines);
  const artifactRows = (packet.artifacts || []).slice(0, 80).map((artifact, index) => {
    const row = {
      id: `artifact_delta_${String(index + 1).padStart(4, '0')}`,
      source: 'artifact_index',
      artifact_id: artifact.id,
      delta_state: artifactState(artifact),
      kind: artifact.kind,
      action: artifact.action,
      path: artifact.path,
      title: manifestText(artifact.title, 160),
      source_line_range: artifact.line_range,
      content_line_range: artifact.content_line_range,
      change_stats: artifact.change_stats,
      content_bytes: artifact.content_bytes,
      content_hash: artifact.content_hash,
    };
    if (['file_created', 'file_edit', 'file_written', 'file_deleted'].includes(artifact.kind) && artifact.preview) {
      row.content_excerpt = artifact.preview;
    }
    return row;
  });
  const knownPaths = new Set(artifactRows.map((row) => row.path).filter(Boolean));
  const pathRows = (packet.entities?.paths || [])
    .filter((row) => !knownPaths.has(row.value))
    .slice(0, 80)
    .map((row, index) => {
      const firstLine = lines[row.first_line - 1] || '';
      const lastLine = lines[row.last_line - 1] || '';
      const context = `${firstLine}\n${lastLine}`;
      return {
        id: `path_delta_${String(index + 1).padStart(4, '0')}`,
        source: 'path_entity_context',
        delta_state: deltaStateFromText(context),
        path: row.value,
        count: row.count,
        first_line: row.first_line,
        last_line: row.last_line,
        evidence_lines: [
          linePointer(firstLine, row.first_line),
          row.last_line !== row.first_line ? linePointer(lastLine, row.last_line) : null,
        ].filter(Boolean),
      };
    });
  const rows = [...artifactRows, ...pathRows];
  return {
    schema_version: 'agent_trace_artifact_delta_index_v1',
    purpose: 'Artifact and path deltas as source pointers; exact file content remains only in source text or local full packet.',
    artifact_row_count: artifactRows.length,
    path_row_count: pathRows.length,
    state_counts: countBy(rows, (row) => row.delta_state),
    rows,
    delta_stat_rows: extractDeltaStats(lines),
    omitted_policy: 'Rows are bounded to keep the visible clip small. Use source ranges and local full packet for complete path/entity listings.',
  };
}

function sourceLineByteRanges(text = '') {
  const pieces = sourceLinePieces(String(text || ''), Infinity);
  let offset = 0;
  return pieces.map((piece) => {
    const bytes = byteLength(piece.text);
    const row = {
      line: piece.line,
      byte_range_utf8: { start: offset, end: offset + bytes },
      byte_count_with_line_break: bytes,
    };
    offset += bytes;
    return row;
  });
}

function lineRoleHint(line = '') {
  const value = String(line || '').trim();
  if (/^PACKET v=|^END_PACKET$/.test(value)) return 'packet_boundary';
  if (/^\s*[{[]/.test(value)) return 'json_or_jsonl';
  if (/^(?:Ran|Read|Edited|Created|Wrote|Deleted|Success|Failed|Failure|Error)\b/.test(value)) return 'tool_trace';
  if (/^\s*(?:import|export|const|let|function|class|type|interface)\b/.test(value)) return 'source_code';
  if (/^(?:deliverable_type|depth_floor|authority_boundary|integration_target)\b/.test(value)) return 'prompt_or_packet_header';
  return 'long_prose_or_output';
}

function buildLongLineIndex(packet, sourceSegments) {
  const lines = sourceRowsToLines(packet.source_lines);
  const byteRanges = sourceLineByteRanges(packet.source_text || '');
  const segmentRows = sourceSegmentIndexRows(sourceSegments);
  const rows = [];
  lines.forEach((line, index) => {
    const lineNumber = index + 1;
    const lineBytes = byteLength(line);
    if (lineBytes < 1000) return;
    const matchingSegments = segmentRows.filter((segment) => rangeContains(segment.line_range, lineNumber));
    rows.push({
      line: lineNumber,
      byte_count: lineBytes,
      source_line_byte_range_utf8: byteRanges[index]?.byte_range_utf8 || null,
      segment_count: matchingSegments.length,
      segment_ids: matchingSegments.map((segment) => segment.id),
      segment_ranges: matchingSegments.map((segment) => ({
        id: segment.id,
        line_range: segment.line_range,
        byte_range_utf8: segment.byte_range_utf8,
        starts_mid_line: segment.starts_mid_line,
        ends_mid_line: segment.ends_mid_line,
      })),
      role_hint: lineRoleHint(line),
      prefix: manifestText(line, 180),
      suffix: manifestText(String(line).slice(-180), 180),
    });
  });
  return {
    schema_version: 'agent_trace_long_line_index_v1',
    purpose: 'Very long source lines with segment spans so downstream compactors do not rely on line-only navigation.',
    threshold_bytes: 1000,
    long_line_count: rows.length,
    max_line_bytes: rows.reduce((max, row) => Math.max(max, row.byte_count), 0),
    rows: rows.slice(0, 80),
    omitted_long_line_count: Math.max(0, rows.length - 80),
    policy: 'Use segment_ids and byte_range_utf8 to restore exact long-line spans from source_segments or raw sidecar.',
  };
}

function compactCaptureContext(context = {}) {
  if (!context || typeof context !== 'object') return undefined;
  return {
    capture_kind: context.capture_kind || null,
    captured_from: context.captured_from || null,
    captured_at: context.captured_at || null,
    content_kind: context.content_kind || null,
    source_bytes: context.source_bytes || context.input_bytes || null,
    content_bytes: context.content_bytes || context.clipboard_bytes || null,
    file_count: context.file_count || null,
  };
}

function clipBudgetProfile(sourceBytes = 0) {
  const bytes = Number(sourceBytes || 0);
  if (bytes < 12000) {
    return {
      chunks: 0,
      timeline: 0,
      sections: 0,
      artifacts: 2,
      entityLimit: 3,
      patternFamilies: 0,
      patternSamples: 0,
    };
  }
  if (bytes < 64000) {
    return {
      chunks: 0,
      timeline: 0,
      sections: 0,
      artifacts: 0,
      entityLimit: 4,
      patternFamilies: 0,
      patternSamples: 0,
    };
  }
  if (bytes < 256000) {
    return {
      chunks: 8,
      timeline: 5,
      sections: 5,
      artifacts: 8,
      entityLimit: 8,
      patternFamilies: 2,
      patternSamples: 1,
    };
  }
  return {
    chunks: 28,
    timeline: 10,
    sections: 10,
    artifacts: 20,
    entityLimit: 10,
    patternFamilies: 6,
    patternSamples: 2,
  };
}

function manifestPatternValue(value) {
  if (typeof value === 'string') return manifestText(value, 120);
  if (typeof value === 'number' || typeof value === 'boolean' || value == null) return value;
  if (Array.isArray(value)) return value.slice(0, 6).map(manifestPatternValue);
  if (typeof value !== 'object') return String(value);
  const allowed = {};
  for (const [key, nested] of Object.entries(value)) {
    if (['preview', 'snippet', 'evidence', 'text', 'source_text', 'source_lines', 'content_lines'].includes(key)) continue;
    if (typeof nested === 'object' && nested != null && !Array.isArray(nested) && !['line_range', 'entity_counts', 'kind_counts', 'change_stats'].includes(key)) {
      continue;
    }
    allowed[key] = manifestPatternValue(nested);
  }
  return allowed;
}

function manifestPatternCatalog(patternIndex = {}, limitPerFamily = 4, familyLimit = 20) {
  if (familyLimit === 0) {
    const omittedFamilyCount = Object.values(patternIndex || {}).filter(Array.isArray).length;
    return {
      schema_version: 'dynamic_pattern_catalog_manifest_v1',
      source_schema_version: patternIndex?.schema_version || null,
      family_count: 0,
      omitted_family_count: omittedFamilyCount,
      counters: {
        timeline_kind_counts: patternIndex?.timeline_kind_counts || null,
        source_chunk_count: patternIndex?.source_chunk_count || null,
      },
      policy: 'Pattern row samples omitted by size profile; use source_segments plus local full packet for full pattern rows.',
    };
  }
  const families = [];
  const counters = {};
  for (const [family, value] of Object.entries(patternIndex || {})) {
    if (Array.isArray(value)) {
      if (families.length < familyLimit) {
        families.push({
          family,
          row_count: value.length,
          sample_shape: value[0] ? Object.keys(value[0]).filter((key) => !['preview', 'snippet', 'evidence', 'text'].includes(key)).slice(0, 16) : [],
          samples: value.slice(0, limitPerFamily).map(manifestPatternValue),
        });
      }
    } else if (value && typeof value === 'object') {
      counters[family] = manifestPatternValue(value);
    } else if (!['schema_version', 'purpose'].includes(family)) {
      counters[family] = value;
    }
  }
  return {
    schema_version: 'dynamic_pattern_catalog_manifest_v1',
    source_schema_version: patternIndex?.schema_version || null,
    source_purpose: patternIndex?.purpose || null,
    family_count: families.length,
    families,
    counters,
    policy: 'Pattern families are dynamic. This manifest includes counts, row shapes, and bounded samples; the private full packet keeps complete pattern rows.',
  };
}

function splitPieceByByteBudget(piece, maxBytes) {
  const limit = Number(maxBytes || 0);
  if (!Number.isFinite(limit) || limit <= 0 || byteLength(piece.text) <= limit) {
    return [piece];
  }

  const parts = [];
  let current = '';
  let currentBytes = 0;
  for (const char of piece.text) {
    const charBytes = byteLength(char);
    if (current && currentBytes + charBytes > limit) {
      parts.push({
        line: piece.line,
        text: current,
        starts_mid_line: parts.length > 0 || Boolean(piece.starts_mid_line),
        ends_mid_line: true,
      });
      current = '';
      currentBytes = 0;
    }
    current += char;
    currentBytes += charBytes;
  }
  if (current) {
    parts.push({
      line: piece.line,
      text: current,
      starts_mid_line: parts.length > 0 || Boolean(piece.starts_mid_line),
      ends_mid_line: Boolean(piece.ends_mid_line),
    });
  }
  return parts;
}

function sourceLinePieces(text, maxPieceBytes = Infinity) {
  const value = String(text || '');
  if (!value) return [];
  const pieces = [];
  let start = 0;
  let line = 1;
  while (start < value.length) {
    let end = value.length;
    for (let index = start; index < value.length; index += 1) {
      const char = value[index];
      if (char === '\n') {
        end = index + 1;
        break;
      }
      if (char === '\r') {
        end = value[index + 1] === '\n' ? index + 2 : index + 1;
        break;
      }
    }
    pieces.push(...splitPieceByByteBudget({ line, text: value.slice(start, end) }, maxPieceBytes));
    start = end;
    line += 1;
  }
  return pieces;
}

function buildLosslessSourceSegments(packet, refs = {}) {
  const text = typeof packet.source_text === 'string' ? packet.source_text : '';
  const targetBytes = Number(refs.source_segment_target_bytes || 12000);
  const maxLines = Number(refs.source_segment_max_lines || 180);
  const pieces = sourceLinePieces(text, targetBytes);
  const segments = [];
  let current = null;
  let nextByteStart = 0;

  function flush() {
    if (!current || !current.text.length) return;
    const byteCount = byteLength(current.text);
    segments.push({
      id: `seg_${String(segments.length + 1).padStart(4, '0')}`,
      ordinal: segments.length + 1,
      line_range: { start: current.startLine, end: current.endLine },
      byte_range_utf8: { start: nextByteStart, end: nextByteStart + byteCount },
      char_count: current.text.length,
      byte_count: byteCount,
      starts_mid_line: Boolean(current.startsMidLine),
      ends_mid_line: Boolean(current.endsMidLine),
      text: current.text,
    });
    nextByteStart += byteCount;
    current = null;
  }

  for (const piece of pieces) {
    const pieceBytes = byteLength(piece.text);
    const currentBytes = current ? byteLength(current.text) : 0;
    const currentLines = current ? current.endLine - current.startLine + 1 : 0;
    if (
      current
      && (currentBytes + pieceBytes > targetBytes || currentLines >= maxLines)
    ) {
      flush();
    }
    if (!current) {
      current = {
        startLine: piece.line,
        endLine: piece.line,
        startsMidLine: Boolean(piece.starts_mid_line),
        endsMidLine: Boolean(piece.ends_mid_line),
        text: '',
      };
    }
    current.text += piece.text;
    current.endLine = piece.line;
    current.endsMidLine = Boolean(piece.ends_mid_line);
  }
  flush();

  return {
    schema_version: 'lossless_source_segments_v1',
    source_text_complete: true,
    segment_count: segments.length,
    target_segment_bytes: targetBytes,
    max_segment_lines: maxLines,
    total_segment_bytes: segments.reduce((sum, segment) => sum + segment.byte_count, 0),
    reconstruction_rule: 'Concatenate source_segments[].text in ordinal order to recover the exact copied clip content.',
    line_break_policy: 'Segment text preserves the original line endings from the copied source.',
    segments,
  };
}

function sourceSegmentIndexRows(sourceSegments) {
  return sourceSegments.segments.map((segment) => ({
    id: segment.id,
    ordinal: segment.ordinal,
    line_range: segment.line_range,
    byte_range_utf8: segment.byte_range_utf8,
    char_count: segment.char_count,
    byte_count: segment.byte_count,
    starts_mid_line: segment.starts_mid_line,
    ends_mid_line: segment.ends_mid_line,
  }));
}

function rawSidecarFilename(sourceName = 'clip.json') {
  const basename = String(sourceName || 'clip.json').split(/[\\/]/).pop() || 'clip.json';
  const stem = basename.replace(/\.[^.]+$/, '') || basename;
  return `${stem}.raw.txt`;
}

function clipSizeBudget(rawBytes) {
  const sourceBytes = Math.max(0, Number(rawBytes || 0));
  if (sourceBytes < CLIP_TINY_SOURCE_BYTES) {
    return {
      profile: 'tiny_fixed_overhead',
      budget_bytes: sourceBytes + CLIP_TINY_FIXED_ALLOWANCE_BYTES,
      fixed_allowance_bytes: CLIP_TINY_FIXED_ALLOWANCE_BYTES,
      ratio_target: null,
    };
  }
  return {
    profile: 'ratio_plus_fixed_allowance',
    budget_bytes: Math.ceil(sourceBytes * CLIP_SIZE_RATIO_TARGET) + CLIP_NORMAL_FIXED_ALLOWANCE_BYTES,
    fixed_allowance_bytes: CLIP_NORMAL_FIXED_ALLOWANCE_BYTES,
    ratio_target: CLIP_SIZE_RATIO_TARGET,
  };
}

function measuredSizePolicy({
  rawBytes,
  exportBytes,
  attemptedSingleJsonBytes = null,
  carrierDecision,
  reason,
}) {
  const budget = clipSizeBudget(rawBytes);
  return {
    target: 'lossless export, source once, <= source + 25% plus fixed allowance when JSON carrier is feasible',
    raw_source_bytes: rawBytes,
    export_bytes: exportBytes,
    measured_ratio: rawBytes > 0 ? Number((exportBytes / rawBytes).toFixed(4)) : null,
    budget_profile: budget.profile,
    budget_bytes: budget.budget_bytes,
    fixed_allowance_bytes: budget.fixed_allowance_bytes,
    ratio_target: budget.ratio_target,
    carrier_decision: carrierDecision,
    reason,
    attempted_single_json_bytes: attemptedSingleJsonBytes,
    attempted_single_json_ratio: rawBytes > 0 && attemptedSingleJsonBytes != null
      ? Number((attemptedSingleJsonBytes / rawBytes).toFixed(4))
      : null,
  };
}

function withStableSizePolicy(clip, rawBytes, carrierDecision, reason, attemptedSingleJsonBytes = null, externalCarrierBytes = 0) {
  let candidate = {
    ...clip,
    size_policy: measuredSizePolicy({
      rawBytes,
      exportBytes: 0,
      attemptedSingleJsonBytes,
      carrierDecision,
      reason,
    }),
  };
  for (let index = 0; index < 3; index += 1) {
    const exportBytes = byteLength(JSON.stringify(candidate)) + Number(externalCarrierBytes || 0);
    const nextPolicy = measuredSizePolicy({
      rawBytes,
      exportBytes,
      attemptedSingleJsonBytes,
      carrierDecision,
      reason,
    });
    const next = { ...clip, size_policy: nextPolicy };
    if (JSON.stringify(nextPolicy) === JSON.stringify(candidate.size_policy)) {
      return next;
    }
    candidate = next;
  }
  return candidate;
}

function buildNavigationTutorial(sourceSegments, includeOptionalIndexes = true, carrierMode = 'single_json') {
  if (carrierMode === 'raw_sidecar_plus_index') {
    return {
      purpose:
        'Lossless raw-sidecar bundle plus compact JSON index. The raw sidecar is the exact copied source; this JSON teaches how to navigate it.',
      read_order: [
        'clip_contract',
        'source_integrity',
        'reader_index',
        'terminal_state_index',
        'command_ledger',
        'validation_matrix',
        'artifact_delta_index',
        'long_line_index',
        'source_segment_index',
        'navigation_tutorial',
        'size_policy',
        'raw_sidecar',
        ...(includeOptionalIndexes ? ['navigation_manifest'] : []),
      ],
      commands: {
        restore_shell: "cat clip.raw.txt > restored_clip.txt",
        inspect_index: "jq '.source_segment_index.segments[] | {id,line_range,byte_range_utf8,byte_count}' clip.index.json",
        list_commands: "jq '.command_ledger.records[] | {id,role,command,source_line_range,output_line_range,status}' clip.index.json",
        terminal_state: "jq '.terminal_state_index' clip.index.json",
        print_range_python:
          "python3 - <<'PY'\nfrom pathlib import Path\nraw=Path('clip.raw.txt').read_bytes()\nstart,end=0,12000\nPath('segment.txt').write_bytes(raw[start:end])\nPY",
      },
      segment_count: sourceSegments.segment_count,
    };
  }

  const commands = {
    restore_jq: "jq -rj '.source_segments[].text' clip.json > restored_clip.txt",
    restore_python:
      "python3 - <<'PY'\nimport json,sys\np=json.load(open('clip.json'))\nsys.stdout.write(''.join(s['text'] for s in p['source_segments']))\nPY",
    list_ranges: "jq '.source_segment_index.segments[] | {id,line_range,byte_range_utf8,byte_count}' clip.json",
    list_commands: "jq '.command_ledger.records[] | {id,role,command,source_line_range,output_line_range,status}' clip.json",
    terminal_state: "jq '.terminal_state_index' clip.json",
    print_segment: "jq -rj '.source_segments[] | select(.id == \"seg_0001\").text' clip.json",
  };
  if (includeOptionalIndexes) {
    commands.paths = "jq -r '.navigation_manifest.top_entities.paths[].value' clip.json";
  }
  return {
    purpose:
      'Lossless segmented clip plus small indexes. Rebuild or inspect source_segments; indexes are just maps.',
    read_order: [
      'clip_contract',
      'source_integrity',
      'reader_index',
      'terminal_state_index',
      'command_ledger',
      'validation_matrix',
      'artifact_delta_index',
      'long_line_index',
      'source_segment_index',
      'navigation_tutorial',
      'source_segments',
      ...(includeOptionalIndexes ? ['navigation_manifest'] : []),
    ],
    commands,
    segment_count: sourceSegments.segment_count,
  };
}

function buildClipContract(carrierMode = 'single_json') {
  const exactSource = carrierMode === 'raw_sidecar_plus_index'
    ? 'raw_sidecar.filename'
    : 'source_segments[].text';
  const parseOrder = carrierMode === 'raw_sidecar_plus_index'
    ? ['clip_contract', 'source_integrity', 'reader_index', 'terminal_state_index', 'command_ledger', 'validation_matrix', 'artifact_delta_index', 'long_line_index', 'source_segment_index', 'size_policy', 'raw_sidecar']
    : ['clip_contract', 'source_integrity', 'reader_index', 'terminal_state_index', 'command_ledger', 'validation_matrix', 'artifact_delta_index', 'long_line_index', 'source_segment_index', 'source_segments', 'size_policy'];
  return {
    schema_version: 'agent_trace_clip_contract_v1',
    standard_ref: ATTACHMENT_CLIP_STANDARD_REF,
    artifact_class: 'lossless_agent_trace_clip',
    source_authority_field: exactSource,
    parse_order: parseOrder,
    required_fields: [
      'schema_version',
      'carrier_mode',
      'clip_contract',
      'reader_index',
      'terminal_state_index',
      'command_ledger',
      'validation_matrix',
      'artifact_delta_index',
      'long_line_index',
      'source_integrity',
      'source_segment_index',
      'size_policy',
    ],
    compactness_rule: 'The exact copied source appears once. Other fields are bounded maps, range indexes, or local capture refs.',
    reader_index_rule: 'reader_index is mandatory and range-only; never treat it as a semantic summary or source authority.',
    command_ledger_rule: 'command_ledger preserves detected commands as pointers with bounded output excerpts and hashes; full output remains in the source range.',
    terminal_state_rule: 'terminal_state_index points to captured terminal-state evidence and must not override exact source authority or live re-verification.',
    prompt_capture_rule: 'Toolbar prompt captures use capture_context.capture_kind=prompt in the private packet and keep this same clip contract in the visible export.',
    operator_thread_export_rule: 'AIW thread exports use capture_context.capture_kind=operator_thread_export and may carry operator_tab_match metadata that binds copied text to HUD/CDP tab identity without trusting visual tab number alone.',
    status_semantics: TRACE_VALIDATION_STATUS_SEMANTICS,
    variant_contracts: {
      denoised_v0_operator_summary: DENOISED_V0_VARIANT_CONTRACT,
    },
  };
}

export function buildAttachmentClip(packet, refs = {}) {
  const sourceBytes = packet.lossless_source?.source_text_bytes || packet.source?.input_bytes || 0;
  const segmentRefs = {
    ...refs,
    source_segment_target_bytes: refs.source_segment_target_bytes || (sourceBytes < 32000 ? 64000 : 12000),
    source_segment_max_lines: refs.source_segment_max_lines || (sourceBytes < 32000 ? 1000 : 180),
  };
  const sourceSegments = buildLosslessSourceSegments(packet, segmentRefs);
  const budgetProfile = clipBudgetProfile(sourceBytes);
  const commandLedger = buildCommandLedger(packet);
  const validationMatrix = buildValidationMatrix(commandLedger, packet);
  const terminalStateIndex = buildTerminalStateIndex(packet, sourceSegments, commandLedger, validationMatrix);
  const artifactDeltaIndex = buildArtifactDeltaIndex(packet);
  const longLineIndex = buildLongLineIndex(packet, sourceSegments);
  const chunks = manifestChunkOutline(packet.source_chunks || [], budgetProfile.chunks);
  const timeline = manifestTimelineOutline(packet.timeline || [], budgetProfile.timeline);
  const sections = manifestSectionOutline(packet.sections || [], budgetProfile.sections);
  const artifacts = manifestArtifactOutline(packet.artifacts || [], budgetProfile.artifacts);
  const omitted = {
    source_text: 0,
    source_lines: (packet.source_lines || []).length,
    source_chunks: Math.max(0, (packet.source_chunks || []).length - chunks.length),
    timeline: Math.max(0, (packet.timeline || []).length - timeline.length),
    sections: Math.max(0, (packet.sections || []).length - sections.length),
    artifacts: Math.max(0, (packet.artifacts || []).length - artifacts.length),
    duplicate_source_text_string: typeof packet.source_text === 'string' ? packet.source_text.length : 0,
  };
  const includeLocalPaths = refs.include_local_paths === true;
  const localPaths = includeLocalPaths
    ? {
        full_packet_path: refs.full_packet_path || null,
        raw_source_path: refs.raw_source_path || null,
        clip_store_path: refs.clip_store_path || null,
        clip_export_path: refs.clip_export_path || null,
      }
    : undefined;
  const localCapture = {
    storage_scope: refs.storage_scope || 'local_recent_capture_triplet',
    retention_limit: refs.retention_limit || 10,
    input_hash: packet.source?.input_hash || null,
    refs_available: {
      full_packet: Boolean(refs.full_packet_path),
      raw_source: Boolean(refs.raw_source_path),
      private_clip: Boolean(refs.clip_store_path),
      visible_export: Boolean(refs.clip_export_path),
    },
    public_export_contains_local_paths: includeLocalPaths,
    note: 'Attachment has exact source_segments; local stores keep backup/full indexes.',
  };
  if (includeLocalPaths) localCapture.paths = localPaths;
  const captureContext = compactCaptureContext(packet.capture_context);

  const includeOptionalIndexes = sourceBytes >= 32000;
  const optionalIndexes = includeOptionalIndexes
    ? {
        source_profile: {
          detected_trace_format: packet.source_profile?.detected_trace_format,
          primary_content_kind: packet.source_profile?.primary_content_kind,
          provider_family: packet.continuation_view?.provider_reading_mode?.provider_family,
        },
        summary: packet.summary,
        navigation_manifest: {
          source_chunk_count: (packet.source_chunks || []).length,
          included_chunk_count: chunks.length,
          chunks,
          section_count: (packet.sections || []).length,
          included_section_count: sections.length,
          sections,
          timeline_event_count: (packet.timeline || []).length,
          included_timeline_event_count: timeline.length,
          timeline,
          top_entities: manifestTopEntities(packet.entities || {}, budgetProfile.entityLimit),
        },
        pattern_catalog: manifestPatternCatalog(packet.pattern_index || {}, budgetProfile.patternSamples, budgetProfile.patternFamilies),
        artifacts,
      }
    : {
        summary: {
          events: packet.summary?.events || 0,
          artifacts: packet.summary?.artifacts || 0,
          source_chunks: packet.summary?.source_chunks || 0,
          compacted_index_profile: 'tiny_source_clip_content_is_primary',
        },
      };

  const baseClip = {
    schema_version: ATTACHMENT_READER_SCHEMA_VERSION,
    carrier_mode: 'single_json',
    manifest_role: 'lossless_segmented_source_with_bounded_navigation_indexes',
    clip_contract: buildClipContract('single_json'),
    generated_at: packet.generated_at,
    source_integrity: {
      source_text_hash: packet.lossless_source?.source_text_hash,
      source_text_bytes: sourceBytes,
      source_text_chars: packet.lossless_source?.source_text_chars || packet.source?.input_chars || 0,
      source_line_count: packet.lossless_source?.source_line_count || packet.source?.input_lines || 0,
      exact_source_text_in_attachment: true,
      exact_source_text_stored_locally: true,
      source_text_attachment_field: 'source_segments[].text',
      source_lines_reconstructable_from_source_text: true,
      reconstruction_authority: 'Concatenate attachment.source_segments[].text in ordinal order; local backend raw/full capture triplet is backup and full index authority.',
    },
    reader_index: buildClipReaderIndex(packet, sourceSegments, budgetProfile),
    terminal_state_index: terminalStateIndex,
    command_ledger: commandLedger,
    validation_matrix: validationMatrix,
    artifact_delta_index: artifactDeltaIndex,
    long_line_index: longLineIndex,
    source: {
      name: packet.source?.name,
      input_hash: packet.source?.input_hash,
      input_bytes: packet.source?.input_bytes,
      input_chars: packet.source?.input_chars,
      input_lines: packet.source?.input_lines,
      line_breaks: packet.source?.line_breaks,
    },
    ...(captureContext ? { capture_context: captureContext } : {}),
    navigation_tutorial: buildNavigationTutorial(sourceSegments, includeOptionalIndexes, 'single_json'),
    local_capture: localCapture,
    ...optionalIndexes,
    source_segment_index: {
      schema_version: sourceSegments.schema_version,
      source_text_complete: sourceSegments.source_text_complete,
      segment_count: sourceSegments.segment_count,
      target_segment_bytes: sourceSegments.target_segment_bytes,
      max_segment_lines: sourceSegments.max_segment_lines,
      total_segment_bytes: sourceSegments.total_segment_bytes,
      reconstruction_rule: sourceSegments.reconstruction_rule,
      line_break_policy: sourceSegments.line_break_policy,
      segments: sourceSegmentIndexRows(sourceSegments),
    },
    source_segments: sourceSegments.segments,
    reader_contract: {
      read_order: [
        'clip_contract',
        'source_integrity',
        'reader_index',
        'terminal_state_index',
        'command_ledger',
        'validation_matrix',
        'artifact_delta_index',
        'long_line_index',
        'source_segment_index',
        'navigation_tutorial',
        'source_segments',
        'summary',
        ...(includeOptionalIndexes ? ['navigation_manifest', 'pattern_catalog', 'artifacts'] : []),
        'omission_receipt',
      ],
      rule: 'Copied content appears once in ordered source_segments. Other fields are bounded maps.',
      exact_text_request: 'Concatenate source_segments[].text; local full packet keeps duplicate full projections.',
      continuation_selection_rule: 'Use indexes to choose evidence for semantic carryforward or restart state; do not expand all source ranges unless terminal or semantic state remains ambiguous.',
    },
    omission_receipt: {
      reason: 'Lossless clip preserves the copied content exactly once as source_segments and omits duplicate high-volume projections that can be reconstructed or read from the local full packet.',
      omitted,
      full_authority: ['attachment.source_segments', 'backend.raw_source', 'backend.full_packet', 'backend.private_clip'],
    },
  };

  const singleWithPolicy = withStableSizePolicy(
    baseClip,
    sourceBytes,
    'single_json',
    'single_json_carrier_within_measured_budget',
  );
  const singleBytes = byteLength(JSON.stringify(singleWithPolicy));
  if (singleBytes <= clipSizeBudget(sourceBytes).budget_bytes || refs.disable_raw_sidecar_fallback === true) {
    return singleWithPolicy;
  }

  const sidecarClipBase = {
    ...baseClip,
    carrier_mode: 'raw_sidecar_plus_index',
    manifest_role: 'lossless_raw_sidecar_with_bounded_navigation_index',
    clip_contract: buildClipContract('raw_sidecar_plus_index'),
    navigation_tutorial: buildNavigationTutorial(sourceSegments, includeOptionalIndexes, 'raw_sidecar_plus_index'),
    raw_sidecar: {
      role: 'exact_clip_source',
      filename: rawSidecarFilename(packet.source?.name),
      byte_count_utf8: sourceBytes,
      char_count: packet.lossless_source?.source_text_chars || packet.source?.input_chars || 0,
      source_text_hash: packet.lossless_source?.source_text_hash,
      line_breaks: packet.source?.line_breaks,
      reconstruction_rule: 'Use the sibling raw sidecar file as the exact copied source; this JSON only indexes it.',
    },
    source_integrity: {
      ...baseClip.source_integrity,
      exact_source_text_in_json: false,
      exact_source_text_in_attachment_bundle: true,
      source_text_attachment_field: 'raw_sidecar',
      reconstruction_authority: 'Read the sibling raw sidecar file as exact source; source_segment_index provides byte and line ranges.',
    },
    source_segment_index: {
      ...baseClip.source_segment_index,
      reconstruction_rule: 'Use byte_range_utf8 against raw_sidecar to inspect a segment, or read the raw sidecar end to end to recover the exact copied clip.',
    },
    reader_contract: {
      ...baseClip.reader_contract,
      read_order: [
        'clip_contract',
        'source_integrity',
        'reader_index',
        'terminal_state_index',
        'command_ledger',
        'validation_matrix',
        'artifact_delta_index',
        'long_line_index',
        'source_segment_index',
        'navigation_tutorial',
        'size_policy',
        'raw_sidecar',
        'summary',
        ...(includeOptionalIndexes ? ['navigation_manifest', 'pattern_catalog', 'artifacts'] : []),
        'omission_receipt',
      ],
      rule: 'Copied content appears once in the sibling raw sidecar. This JSON contains bounded indexes only.',
      exact_text_request: 'Read raw_sidecar.filename next to this index JSON; local full packet keeps duplicate full projections.',
      continuation_selection_rule: 'Use indexes to choose evidence for semantic carryforward or restart state; do not expand all source ranges unless terminal or semantic state remains ambiguous.',
    },
    omission_receipt: {
      ...baseClip.omission_receipt,
      reason: 'Single JSON would exceed the measured size budget because JSON string escaping bloats the source. The exact clip is stored once in a sibling raw sidecar; this JSON is the bounded index.',
      full_authority: ['attachment.raw_sidecar', 'backend.raw_source', 'backend.full_packet', 'backend.private_clip'],
    },
  };
  delete sidecarClipBase.source_segments;
  return withStableSizePolicy(
    sidecarClipBase,
    sourceBytes,
    'raw_sidecar_plus_index',
    'json_string_escape_overhead_exceeds_ratio_budget',
    singleBytes,
    sourceBytes,
  );
}

export function defaultTraceFilename(now = new Date()) {
  return `clip-${now.toISOString().replace(/[:.]/g, '-')}.json`;
}
