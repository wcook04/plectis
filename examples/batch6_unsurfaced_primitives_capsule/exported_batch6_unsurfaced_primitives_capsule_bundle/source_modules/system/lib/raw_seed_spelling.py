"""Conservative, corpus-first spelling normalization for raw_seed keyword_hints only.

Never mutates paragraph body text — canonicalization applies to hint candidates at merge time.

[INTERFACE]
- Exports: CorpusLexicon, build_corpus_lexicon, build_corpus_hint_normalizer, SPELLING_NORMALIZATION_VERSION.
- Inputs: corpus unigram frequency maps, effective stopwords, and mechanism vocabulary from the raw-seed keyphrase/registry pipeline.
- Outputs: a corpus lexicon plus a callable unigram normalizer used during keyword-hint merge.

[FLOW]
- raw_seed_registry / raw_seed_keyphrase build a corpus lexicon from attested content terms.
- build_corpus_hint_normalizer closes over trust thresholds and one-edit candidates.
- Paragraph hint generation calls the returned normalizer to canonically normalize candidate tokens without touching paragraph text.

[DEPENDENCIES]
- None (stdlib only).

[CONSTRAINTS]
- Normalization is corpus-first and conservative: paragraph body text is never mutated, only hint candidates are canonicalized.
- Mechanism vocabulary and strongly attested tokens bypass correction.
- When-needed: Open when raw-seed keyword hints need the exact spelling-normalization policy, trust thresholds, or correction rules instead of the higher-level registry wrapper.
- Escalates-to: system/lib/raw_seed_keyphrase.py::merge_distinctive_keyword_hints; system/lib/raw_seed_registry.py::build_raw_seed_payload; codex/standards/observe_apply/std_raw_seed.md
- Navigation-group: kernel_lib
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

# Bumped when edit rules / thresholds change (written into raw_seed_term_ledger.json).
SPELLING_NORMALIZATION_VERSION = "corpus_edit1_v1"

# Trust token as-is when strongly attested: high CF vs corpus max and usually df>=2
# (single-paragraph repeated typos must not satisfy trust).
_MIN_CF_RATIO_TRUST = 0.012
_MIN_DF_TRUST = 2
_MIN_CF_TRUST_ABSOLUTE = 6
# Correction target must beat source cf by this factor when source is already in-lexicon.
_MIN_CORRECTION_CF_RATIO = 2.0
# Minimum cf for a correction target to be considered (noise floor).
_MIN_CORRECTION_TARGET_CF = 2


def _edits1(word: str) -> set[str]:
    """All strings at Levenshtein distance 1 from word (lowercase a-z)."""
    letters = "abcdefghijklmnopqrstuvwxyz"
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = {a + b[1:] for a, b in splits if b}
    transposes = {a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1}
    replaces = {a + c + b[1:] for a, b in splits if b for c in letters}
    inserts = {a + c + b for a, b in splits for c in letters}
    return deletes | transposes | replaces | inserts


@dataclass(frozen=True)
class CorpusLexicon:
    """[ROLE]
    - Teleology: Carry the content-word frequency tables that spelling normalization trusts and corrects toward.
    - Ownership: Owns the cf (collection frequency) and df (document frequency) dicts plus the corpus max_cf scalar.
    - Mutability: Immutable — frozen dataclass; callers may not modify fields after construction.
    - Concurrency: Safe for concurrent reads; no mutable state.
    """

    cf: dict[str, int]
    df: dict[str, int]
    max_cf: int


def build_corpus_lexicon(
    cf_unigram: dict[str, int],
    df_unigram: dict[str, int],
    stop_words: frozenset[str],
    mechanism_vocab: frozenset[str],
) -> CorpusLexicon:
    """[ACTION]
    - Teleology: Build the content-word lexicon that spelling normalization is allowed to trust or correct toward.
    - Mechanism: Filter corpus unigram counters by stopwords and token length, inject mechanism vocabulary with minimum support, and compute max collection frequency.
    - Guarantee: Returns a CorpusLexicon containing attested content tokens plus mechanism vocabulary.
    - Fails: None.
    - When-needed: Open when hint normalization depends on exactly which tokens are considered canonical targets in the corpus.
    - Escalates-to: system/lib/raw_seed_spelling.py::build_corpus_hint_normalizer; system/lib/raw_seed_registry.py::build_raw_seed_payload
    """
    cf: dict[str, int] = {}
    df: dict[str, int] = {}
    for t, c in cf_unigram.items():
        if len(t) < 3 or t in stop_words:
            continue
        cf[t] = int(c)
        df[t] = int(df_unigram.get(t, 0))
    for t in mechanism_vocab:
        if len(t) >= 3 and t not in stop_words:
            cf.setdefault(t, max(cf.get(t, 0), 1))
            df.setdefault(t, max(df.get(t, 0), 1))
    max_cf = max(cf.values(), default=1)
    return CorpusLexicon(cf=cf, df=df, max_cf=max(max_cf, 1))


def build_corpus_hint_normalizer(
    lex: CorpusLexicon,
    stop_words: frozenset[str],
    mechanism_vocab: frozenset[str],
) -> Callable[[str], tuple[str, bool]]:
    """[ACTION]
    - Teleology: Build the conservative unigram normalizer used during raw-seed hint extraction.
    - Mechanism: Close over corpus trust thresholds, edit-distance-1 candidates, and correction acceptance rules, then return `normalize(lower_token)`.
    - Guarantee: Returns a callable that yields `(canonical_lower, was_corrected)` for one lowercased token.
    - Fails: None.
    - When-needed: Open when a caller needs the exact correction-vs-trust decision rules for raw-seed keyword-hint normalization.
    - Escalates-to: system/lib/raw_seed_keyphrase.py::merge_distinctive_keyword_hints; system/lib/raw_seed_registry.py::build_raw_seed_payload
    - Navigation-group: kernel_lib
    """

    lexicon_set = frozenset(lex.cf.keys())
    trust_cf_floor = max(_MIN_CF_TRUST_ABSOLUTE, int(math.ceil(_MIN_CF_RATIO_TRUST * lex.max_cf)))

    def normalize(token_lower: str) -> tuple[str, bool]:
        t = token_lower.strip().casefold()
        if not t or t in stop_words:
            return t, False
        if t in mechanism_vocab:
            return t, False
        src_cf = lex.cf.get(t, 0)
        src_df = lex.df.get(t, 0)
        if src_cf >= trust_cf_floor and src_df >= _MIN_DF_TRUST:
            return t, False
        if src_cf >= max(trust_cf_floor * 2, int(0.05 * lex.max_cf)):
            return t, False

        best: tuple[str, int] | None = None
        for cand in _edits1(t):
            if cand not in lexicon_set:
                continue
            ccf = lex.cf.get(cand, 0)
            if ccf < _MIN_CORRECTION_TARGET_CF:
                continue
            if src_cf > 0 and ccf < src_cf * _MIN_CORRECTION_CF_RATIO:
                continue
            if best is None or ccf > best[1] or (ccf == best[1] and cand < best[0]):
                best = (cand, ccf)

        if best is not None:
            return best[0], True
        return t, False

    return normalize
