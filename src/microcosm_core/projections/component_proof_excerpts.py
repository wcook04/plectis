"""Build bounded, hash-bound public Dafny declaration and mutation excerpts.

This module reads only the formal component sources named by retained metadata.
It never runs a prover. Declaration names are not retained verification-task names.
"""
from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path
import re

MAX_SOURCE_BYTES = 128 * 1024
MAX_EXCERPT_BYTES = 24 * 1024
MAX_EXCERPT_LINES = 300
MAX_ENRICHMENT_BYTES = 160 * 1024
MAX_EXCERPTS = 32
MAX_CHANGED_LINES = 64
_ID = re.compile(r"[a-z][a-z0-9_]*\Z")
_DECL = re.compile(r"(?m)^[ \t]*(?:(?:ghost|static|opaque)\s+)*(function|predicate|lemma|method)\s+(?:\{:[^}]*\}\s*)*([A-Za-z_][A-Za-z_0-9]*)\b")


def _bound_read(root: Path, ref: str, digest: str) -> str:
    parts = ref.split('/')
    if (len(parts) not in (4, 5) or parts[:2] != ['formal', 'components']
            or not _ID.fullmatch(parts[2]) or any(p in ('', '.', '..') for p in parts)
            or (len(parts) == 5 and parts[3] != 'negative')
            or not re.fullmatch(r'[A-Za-z][A-Za-z_0-9]*\.dfy', parts[-1])):
        raise ValueError('invalid public Dafny source reference')
    path = root.joinpath(*parts)
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Dafny source must not use symlinks')
    if not path.is_file() or path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError('missing or oversized Dafny source')
    data = path.read_bytes()
    if len(data) > MAX_SOURCE_BYTES or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('stale Dafny source hash')
    return data.decode('utf-8')


def _mask(text: str) -> str:
    """Hide comments and strings without changing offsets or line numbers."""
    chars = list(text)
    i, depth = 0, 0
    while i < len(text):
        start = i
        if text.startswith('//', i):
            end = text.find('\n', i)
            i = len(text) if end < 0 else end
        elif text.startswith('/*', i):
            depth, i = 1, i + 2
            while i < len(text) and depth:
                if text.startswith('/*', i):
                    depth, i = depth + 1, i + 2
                elif text.startswith('*/', i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            if depth:
                raise ValueError('unterminated Dafny comment')
        elif text[i] == '"':
            i += 1
            while i < len(text):
                if text[i] == '\\':
                    i += 2
                elif text[i] == '"':
                    i += 1
                    break
                else:
                    i += 1
            else:
                raise ValueError('unterminated Dafny string')
        else:
            i += 1
            continue
        for j in range(start, min(i, len(chars))):
            if chars[j] not in '\r\n':
                chars[j] = ' '
    return ''.join(chars)


def _excerpts(source: str, source_ref: str, digest: str, refs: list[str]) -> list[dict]:
    if not refs or len(refs) > MAX_EXCERPTS or len(refs) != len(set(refs)):
        raise ValueError('invalid declaration reference count')
    masked = _mask(source)
    declarations = list(_DECL.finditer(masked))
    lines = source.splitlines(keepends=True)
    result = []
    for ref in refs:
        prefix, separator, name = ref.partition('#')
        matches = [m for m in declarations if m.group(2) == name]
        if prefix != source_ref or separator != '#' or len(matches) != 1:
            raise ValueError('missing or ambiguous Dafny declaration')
        match = matches[0]
        # End at the next declaration (or the module end), then locate the final
        # balanced declaration brace. Earlier braces may be set literals in a
        # requires/ensures clause; their balanced pairs do not end the member.
        next_start = next((m.start() for m in declarations if m.start() > match.start()), len(masked))
        segment = masked[match.end():next_start]
        level, last_end = 0, None
        for offset, char in enumerate(segment):
            if char == '{':
                level += 1
            elif char == '}':
                level -= 1
                if level == 0:
                    last_end = match.end() + offset + 1
                elif level < 0:  # enclosing module's closing brace
                    break
        if last_end is None or level > 0:
            raise ValueError('unbounded Dafny declaration')
        start_line = source.count('\n', 0, match.start()) + 1
        end_line = source.count('\n', 0, last_end) + 1
        text = ''.join(lines[start_line - 1:end_line])
        if end_line - start_line + 1 > MAX_EXCERPT_LINES or len(text.encode()) > MAX_EXCERPT_BYTES:
            raise ValueError('oversized Dafny declaration excerpt')
        result.append({'ref': ref, 'kind': match.group(1), 'name': name,
                       'line_start': start_line, 'line_end': end_line,
                       'text': text, 'source_sha256': digest,
                       'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest()})
    return result


def _changed_lines(original: str, mutated: str) -> list[dict]:
    before, after = original.splitlines(), mutated.splitlines()
    result = []
    for tag, a, b, c, d in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
        if tag == 'equal':
            continue
        for offset in range(max(b - a, d - c)):
            result.append({'line': a + offset + 1,
                           'original': before[a + offset] if a + offset < b else None,
                           'mutated': after[c + offset] if c + offset < d else None})
    if not result or len(result) > MAX_CHANGED_LINES:
        raise ValueError('empty or oversized negative-control diff')
    return result


def build_proof_enrichments(root: Path, metadata: dict) -> dict:
    """Return proof fields and per-source negative-control additions.

    Callers merge ``excerpts`` into the proof, ``retained_verification_details``
    into its retained verification, and ``negative_control_details[source_ref]``
    into each negative control. Limits apply independently of HTTP/page budgets.
    ``tasks_availability=unrecorded`` is deliberate: current retained metadata
    records only task counts, never task identities or their kinds.
    """
    slug = metadata['slug']
    if not isinstance(slug, str) or not _ID.fullmatch(slug):
        raise ValueError('invalid formal component slug')
    source_ref = f"formal/components/{slug}/{metadata['source']}"
    source = _bound_read(Path(root), source_ref, metadata['source_sha256'])
    contract = metadata['contract']
    refs = list(dict.fromkeys([*contract['specification_refs'], *contract['entry_theorem_refs']]))
    excerpts = _excerpts(source, source_ref, metadata['source_sha256'], refs)
    negatives = {}
    names = metadata['negative_sources']
    if not names or len(names) > 16 or len(names) != len(set(names)):
        raise ValueError('invalid negative-control source count')
    if set(names) != set(metadata['negative_sha256']) or set(names) != set(metadata['mutations']):
        raise ValueError('negative-control metadata coverage mismatch')
    for name in names:
        ref = f'formal/components/{slug}/{name}'
        mutated = _bound_read(Path(root), ref, metadata['negative_sha256'][name])
        mutation = metadata['mutations'][name]
        before, after = mutation['before'], mutation['after']
        occurrence = mutation['occurrence']
        if (not before or type(occurrence) is not int or occurrence < 0
                or source.count(before) != mutation['expected_occurrences']
                or occurrence >= source.count(before)):
            raise ValueError('invalid retained mutation recipe')
        start = 0
        for _ in range(occurrence + 1):
            start = source.index(before, start)
            end = start + len(before)
            if _ < occurrence:
                start = end
        if source[:start] + after + source[end:] != mutated:
            raise ValueError('negative-control source differs from retained mutation recipe')
        changes = _changed_lines(source, mutated)
        negatives[ref] = {'changed_lines': changes,
                          'changed_lines_sha256': hashlib.sha256(json.dumps(changes, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest(),
                          'description': f'Replaces {before.strip()!r} with {after.strip()!r}.',
                          'description_basis': 'retained_mutation_recipe'}
    result = {'excerpts': excerpts,
              'retained_verification_details': {
                  'tasks': [], 'tasks_availability': 'unrecorded',
                  'tasks_reason': 'Retained metadata records a verified task count, but no task names or kinds.'},
              'negative_control_details': negatives}
    if len(json.dumps(result, ensure_ascii=False).encode()) > MAX_ENRICHMENT_BYTES:
        raise ValueError('oversized proof enrichment')
    return result
