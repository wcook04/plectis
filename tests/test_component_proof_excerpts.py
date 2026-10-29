"""Retained Dafny excerpt export exercises real source bindings, without a prover."""
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from microcosm_core.projections import component_proof_excerpts as excerpts

ROOT = Path(__file__).resolve().parents[1]
METADATA = sorted((ROOT / 'formal/components').glob('*/metadata.json'))


def _copied(tmp_path, slug='premise_ranking'):
    relative = Path('formal/components') / slug
    shutil.copytree(ROOT / relative, tmp_path / relative)
    return json.loads((tmp_path / relative / 'metadata.json').read_text())


@pytest.mark.parametrize('metadata_path', METADATA, ids=lambda p: p.parent.name)
def test_actual_sources_export_exact_hash_bound_declarations_and_mutations(metadata_path):
    metadata = json.loads(metadata_path.read_text())
    result = excerpts.build_proof_enrichments(ROOT, metadata)
    refs = set(metadata['contract']['specification_refs'] + metadata['contract']['entry_theorem_refs'])
    assert {row['ref'] for row in result['excerpts']} == refs
    source_lines = (metadata_path.parent / metadata['source']).read_text().splitlines(keepends=True)
    for row in result['excerpts']:
        assert row['text'] == ''.join(source_lines[row['line_start'] - 1:row['line_end']])
        assert row['source_sha256'] == metadata['source_sha256']
        assert row['kind'] in {'function', 'predicate', 'lemma', 'method'}
    for name in metadata['negative_sources']:
        row = result['negative_control_details'][f"formal/components/{metadata['slug']}/{name}"]
        assert row['changed_lines']
        assert row['description_basis'] == 'retained_mutation_recipe'
        assert metadata['mutations'][name]['before'].strip() in row['description'] or '\\n' in row['description']
        for change in row['changed_lines']:
            if change['original'] is not None:
                assert change['original'] == source_lines[change['line'] - 1].rstrip('\r\n')
    retained = result['retained_verification_details']
    assert retained['tasks'] == []
    assert retained['tasks_availability'] == 'unrecorded'
    assert 'no task names' in retained['tasks_reason']


@pytest.mark.parametrize('target', ['source', 'negative'])
def test_tampered_source_or_mutant_fails_binding(tmp_path, target):
    metadata = _copied(tmp_path)
    name = metadata['source'] if target == 'source' else metadata['negative_sources'][0]
    path = tmp_path / 'formal/components/premise_ranking' / name
    path.write_bytes(path.read_bytes() + b'\n// drift\n')
    with pytest.raises(ValueError, match='stale Dafny source hash'):
        excerpts.build_proof_enrichments(tmp_path, metadata)


def test_mutant_hash_alone_cannot_authorize_different_mutation(tmp_path):
    metadata = _copied(tmp_path)
    name = metadata['negative_sources'][0]
    path = tmp_path / 'formal/components/premise_ranking' / name
    path.write_bytes(path.read_bytes() + b'\n// another change\n')
    metadata['negative_sha256'][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='differs from retained mutation recipe'):
        excerpts.build_proof_enrichments(tmp_path, metadata)


def test_references_cannot_escape_or_select_other_source(tmp_path):
    metadata = _copied(tmp_path)
    metadata['source'] = '../../outside.dfy'
    with pytest.raises(ValueError, match='invalid public Dafny source reference'):
        excerpts.build_proof_enrichments(tmp_path, metadata)
    metadata = _copied(tmp_path / 'second')
    metadata['contract']['specification_refs'][0] = 'formal/components/premise_ranking/Other.dfy#OverlapSpec'
    with pytest.raises(ValueError, match='missing or ambiguous'):
        excerpts.build_proof_enrichments(tmp_path / 'second', metadata)


def test_symlink_source_rejected_even_with_matching_hash(tmp_path):
    metadata = _copied(tmp_path)
    path = tmp_path / 'formal/components/premise_ranking' / metadata['source']
    original = path.read_bytes()
    path.unlink()
    outside = tmp_path / 'outside.dfy'
    outside.write_bytes(original)
    path.symlink_to(outside)
    with pytest.raises(ValueError, match='symlinks'):
        excerpts.build_proof_enrichments(tmp_path, metadata)


@pytest.mark.parametrize('limit', ['MAX_SOURCE_BYTES', 'MAX_EXCERPT_BYTES', 'MAX_EXCERPT_LINES', 'MAX_ENRICHMENT_BYTES', 'MAX_CHANGED_LINES', 'MAX_EXCERPTS'])
def test_explicit_export_limits_fail_closed(monkeypatch, limit):
    metadata = json.loads(METADATA[0].read_text())
    monkeypatch.setattr(excerpts, limit, 0 if limit == 'MAX_CHANGED_LINES' else 1)
    with pytest.raises(ValueError):
        excerpts.build_proof_enrichments(ROOT, metadata)


def test_comments_strings_attributes_and_division_preserve_source_lines():
    source = '''module Public {
  // method Fake() { }
  lemma {:fuel 5} Real()
    ensures |{}| == 0
  {
    var text := "} // /*";
    /* nested { /* } */ still } */
    assert 4 / 2 == 2; // }
  }
}
'''
    ref = 'formal/components/example/Public.dfy#Real'
    result = excerpts._excerpts(source, ref.split('#')[0], 'a' * 64, [ref])
    assert len(result) == 1
    assert result[0]['line_start'] == 3
    assert result[0]['line_end'] == 9
    assert '4 / 2' in result[0]['text']
    assert 'method Fake' not in result[0]['text']


def test_missing_ambiguous_and_unclosed_declarations_fail():
    ref = 'formal/components/example/Public.dfy#Real'
    for source in ['module M {\n method Other() {}\n}',
                   'module M {\n method Real() {}\n method Real() {}\n}',
                   'module M {\n method Real() {\n']:
        with pytest.raises(ValueError):
            excerpts._excerpts(source, ref.split('#')[0], 'a' * 64, [ref])


def test_insertions_and_deletions_remain_explicit():
    assert excerpts._changed_lines('a\nb\n', 'a\nx\nb\n') == [
        {'line': 2, 'original': None, 'mutated': 'x'}]
    assert excerpts._changed_lines('a\nx\nb\n', 'a\nb\n') == [
        {'line': 2, 'original': 'x', 'mutated': None}]
