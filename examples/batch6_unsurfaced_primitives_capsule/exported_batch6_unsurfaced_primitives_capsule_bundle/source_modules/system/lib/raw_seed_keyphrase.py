"""Corpus-aware keyphrase helpers for raw_seed_registry paragraph hints.

RAKE-style phrase scoring is adapted from Rose et al. (2010), ported from the
reference implementation under annexes/rake-keyphrase/repo/rake.py (Python 3).

`keyword_hints` are **topic-weighted navigation preludes**: terms that appear in
the paragraph and are **well supported across the family corpus** (high DF/CF
among non-filler tokens), plus path/ID salvage. They are **not** authoritative
semantic truth (see std_raw_seed).

Scoring (per candidate term or phrase in paragraph d), after conservative
corpus-first spelling normalization to a canonical unigram t:

- **Local presence** ``L(t,d) = log(1 + tf_{d,t})`` (canonical token counts in d).
- **Global support** ``G(t) = log(1 + df_t) + 0.6 * log(1 + cf_t)`` (corpus-wide).
- **Composite** ``S = w_L * L + w_G * G`` plus small additive boosts for
  section slug tokens, mechanism vocabulary, and path-like salvage.

High document frequency is **not** penalized for content words (topics recur).
Only stoplists, a tiny **ultra-generic** blocklist, and min token length gate noise.

[INTERFACE]
- Exports: load_smart_stopwords, merged_stopwords, build_corpus_token_stats, high_df_omit_unigrams, top_topic_unigrams_for_ledger, build_term_ledger_payload, rake_ranked_phrases, salvage_tokens, merge_distinctive_keyword_hints.
- Reads: raw_seed_smart_stoplist.txt via load_smart_stopwords(); raw paragraph blocks and corpus token counters supplied by raw_seed_registry.
- Outputs: corpus token stats, diagnostic term-ledger payloads, and distinctive keyword-hint lists for raw-seed paragraph routing.

[FLOW]
- raw_seed_registry builds merged stopwords and corpus token stats from family paragraphs.
- Paragraph text is tokenized, canonically normalized, and scored with local/global support plus RAKE/path salvage.
- build_term_ledger_payload emits diagnostics, while merge_distinctive_keyword_hints emits the bounded keyword_hints lane used in raw_seed paragraph records.

[DEPENDENCIES]
- system.lib.raw_seed_spelling: SPELLING_NORMALIZATION_VERSION for term-ledger metadata compatibility.

[CONSTRAINTS]
- Keyword hints are diagnostic navigation aids, not authoritative semantic truth.
- Stopword loading is cached; repeated callers share the same in-memory smart-stoplist snapshot.
- When-needed: Open when raw-seed indexing needs the exact keyword-hint scoring, RAKE salvage, or term-ledger diagnostics instead of only the higher-level registry builder.
- Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_payload; system/lib/raw_seed_spelling.py::build_corpus_hint_normalizer; codex/standards/observe_apply/std_raw_seed.md
- Navigation-group: kernel_lib
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable

from system.lib.raw_seed_spelling import SPELLING_NORMALIZATION_VERSION

# Extra discourse / filler beyond SMART + registry STOP_WORDS (operator voice).
CONVERSATIONAL_STOPWORDS: frozenset[str] = frozenset(
    {
        "okay",
        "ok",
        "yeah",
        "yep",
        "nope",
        "suppose",
        "supposed",
        "basically",
        "literally",
        "actually",
        "definitely",
        "probably",
        "perhaps",
        "maybe",
        "like",
        "great",
        "cool",
        "nice",
        "anyway",
        "btw",
        "imo",
        "tbh",
    }
)

# Legacy constant kept for tests / diagnostics that still call high_df_omit_unigrams.
HIGH_DOCUMENT_FREQUENCY_QUANTILE: float = 0.90

# Narrow blocklist: high-DF *and* low-information glue (not full quantile omission).
ULTRA_GENERIC_UNIGRAMS: frozenset[str] = frozenset(
    {
        "thing",
        "things",
        "stuff",
        "lot",
        "lots",
        "bit",
        "bits",
        "kind",
        "sort",
        "way",
        "ways",
        "part",
        "parts",
        "fact",
        "case",
        "time",
        "times",
    }
)

_WEIGHT_LOCAL: float = 1.15
_WEIGHT_GLOBAL: float = 1.0
_MECHANISM_TOPIC_BONUS: float = 0.25
_RAKE_SCALE: float = 0.38

_SALVAGE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_./:-]{2,}")
_TOKEN_RE = re.compile(r"[a-z][a-z0-9_]{2,}", re.IGNORECASE)
_SENT_SPLIT_RE = re.compile(r'[.!?,;:\t\\"\(\)\'\u2019\u2013]|\s-\s')


@lru_cache(maxsize=1)
def load_smart_stopwords(path: str | None = None) -> frozenset[str]:
    """[ACTION]
    - Teleology: Load the SMART stopword list used as the base stopword substrate for raw-seed hint extraction.
    - Mechanism: Resolve the default or explicit stoplist path, read it once, filter comments/blanks, and cache the normalized frozenset.
    - Guarantee: Returns a lowercase frozenset of stopwords; repeated calls reuse the cached result.
    - Fails: Propagates file-read errors if the stoplist path cannot be read.
    - When-needed: Open when raw-seed hint quality depends on the exact SMART stoplist inputs rather than downstream merged-stopword behavior.
    - Escalates-to: system/lib/raw_seed_keyphrase.py::merged_stopwords; system/lib/raw_seed_registry.py::build_raw_seed_payload
    """
    base = Path(__file__).resolve().parent / "raw_seed_smart_stoplist.txt"
    p = Path(path) if path else base
    raw = p.read_text(encoding="utf-8")
    out: set[str] = set()
    for line in raw.splitlines():
        line = line.strip().lower()
        if not line or line.startswith("#"):
            continue
        out.add(line)
    return frozenset(out)


def merged_stopwords(registry_stop: Iterable[str]) -> frozenset[str]:
    """[ACTION]
    - Teleology: Build the effective stopword set for raw-seed keyphrase extraction.
    - Mechanism: Union the cached SMART stoplist, registry stopwords, and conversational filler into one frozenset.
    - Guarantee: Returns a deduplicated lowercase frozenset suitable for corpus tokenization.
    - Fails: Propagates SMART stoplist load failures from load_smart_stopwords().
    - When-needed: Open when raw-seed indexing needs to know which tokens are suppressed before scoring keyphrases.
    - Escalates-to: system/lib/raw_seed_keyphrase.py::build_corpus_token_stats; system/lib/raw_seed_registry.py::build_raw_seed_payload
    """
    return frozenset(load_smart_stopwords()) | frozenset(w.casefold() for w in registry_stop) | CONVERSATIONAL_STOPWORDS


@dataclass(frozen=True)
class CorpusTokenStats:
    """[ROLE]
    - Teleology: Immutable container for per-corpus unigram and bigram frequency statistics used by raw-seed keyphrase scoring.
    - Ownership: Owns document-frequency counters (df_unigram, df_bigram), collection-frequency counters (cf_unigram, cf_bigram), and per-document term-frequency lists.
    - Mutability: Immutable (frozen dataclass).
    - Concurrency: Safe for concurrent reads; no shared mutable state.
    """
    n_docs: int
    df_unigram: Counter[str]
    df_bigram: Counter[str]
    cf_unigram: Counter[str]
    cf_bigram: Counter[str]
    per_doc_unigram_tf: list[Counter[str]]
    per_doc_bigram_tf: list[Counter[str]]


def _tokenize_for_corpus(text: str, stop_words: frozenset[str]) -> list[str]:
    return [m.group(0).casefold() for m in _TOKEN_RE.finditer(str(text or "")) if m.group(0).casefold() not in stop_words]


def build_corpus_token_stats(plain_texts: list[str], stop_words: frozenset[str]) -> CorpusTokenStats:
    """[ACTION]
    - Teleology: Build unigram and bigram corpus statistics for raw-seed keyword-hint scoring.
    - Mechanism: Tokenize each paragraph with the effective stopwords, accumulate per-document and collection counters, and package them into CorpusTokenStats.
    - Guarantee: Returns a CorpusTokenStats instance covering every supplied paragraph in order.
    - Fails: None.
    - When-needed: Open when the registry pass needs the exact DF/CF and per-document token statistics that drive term-ledger and keyword-hint scoring.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_payload; system/lib/raw_seed_keyphrase.py::build_term_ledger_payload
    """
    n = len(plain_texts)
    df_uni: Counter[str] = Counter()
    df_bi: Counter[str] = Counter()
    cf_uni: Counter[str] = Counter()
    cf_bi: Counter[str] = Counter()
    per_uni: list[Counter[str]] = []
    per_bi: list[Counter[str]] = []
    for text in plain_texts:
        toks = _tokenize_for_corpus(text, stop_words)
        uni_tf = Counter(toks)
        bi_tf: Counter[str] = Counter()
        for i in range(len(toks) - 1):
            pair = f"{toks[i]} {toks[i + 1]}"
            bi_tf[pair] += 1
        per_uni.append(uni_tf)
        per_bi.append(bi_tf)
        for t, c in uni_tf.items():
            df_uni[t] += 1
            cf_uni[t] += c
        for t, c in bi_tf.items():
            df_bi[t] += 1
            cf_bi[t] += c
    return CorpusTokenStats(n, df_uni, df_bi, cf_uni, cf_bi, per_uni, per_bi)


def high_df_omit_unigrams(corpus: CorpusTokenStats, *, quantile: float = HIGH_DOCUMENT_FREQUENCY_QUANTILE) -> frozenset[str]:
    """[ACTION]
    - Teleology: Return the set of unigrams whose document-frequency ratio meets or exceeds the given quantile threshold, for diagnostic and legacy callers.
    - Guarantee: Returns a frozenset of high-DF unigram strings; returns an empty frozenset when the corpus has no documents.
    - Fails: None.
    """
    if corpus.n_docs <= 0:
        return frozenset()
    ratios = sorted((corpus.df_unigram[t] / corpus.n_docs) for t in corpus.df_unigram)
    if not ratios:
        return frozenset()
    idx = min(len(ratios) - 1, int(quantile * (len(ratios) - 1)))
    threshold = ratios[idx]
    return frozenset(t for t, df in corpus.df_unigram.items() if corpus.n_docs and df / corpus.n_docs >= threshold)


def topic_score_unigram(corpus: CorpusTokenStats, canon: str, tf: int) -> float:
    """[ACTION]
    - Teleology: Compute the composite local-plus-global topic score for one canonical unigram token given its term frequency in a document.
    - Guarantee: Returns a non-negative float combining weighted local presence and global corpus support.
    - Fails: None.
    """
    df = corpus.df_unigram.get(canon, 0)
    cf = corpus.cf_unigram.get(canon, 0)
    g = math.log(1.0 + df) + 0.6 * math.log(1.0 + cf)
    ell = math.log(1.0 + max(tf, 0))
    return _WEIGHT_LOCAL * ell + _WEIGHT_GLOBAL * g


def topic_score_bigram(corpus: CorpusTokenStats, pair: str, tf: int) -> float:
    """[ACTION]
    - Teleology: Compute the composite topic score for one canonical bigram pair given its term frequency in a document.
    - Guarantee: Returns a non-negative float combining weighted local presence and global corpus support for the bigram.
    - Fails: None.
    """
    df = corpus.df_bigram.get(pair, 0)
    cf = corpus.cf_bigram.get(pair, 0)
    g = math.log(1.0 + df) + 0.5 * math.log(1.0 + cf)
    ell = math.log(1.0 + max(tf, 0))
    return 0.95 * ell + 1.0 * g


def top_topic_unigrams_for_ledger(
    corpus: CorpusTokenStats,
    stop_words: frozenset[str],
    *,
    top_n: int = 40,
    ultra_generic: frozenset[str] | None = None,
) -> list[dict[str, Any]]:
    """[ACTION]
    - Teleology: Produce the ranked top-N topic unigrams for the term-ledger diagnostic payload, excluding stopwords and ultra-generic tokens.
    - Guarantee: Returns a list of at most `top_n` dicts, each with `term`, `df`, `cf`, and `topic_score` fields, sorted by descending topic score.
    - Fails: None.
    """
    ultra = ultra_generic if ultra_generic is not None else ULTRA_GENERIC_UNIGRAMS
    scored: list[tuple[float, str, int, int]] = []
    for t, cf in corpus.cf_unigram.items():
        if len(t) < 3 or t in stop_words or t in ultra:
            continue
        df = corpus.df_unigram.get(t, 0)
        raw = math.log(1.0 + df) + 0.6 * math.log(1.0 + cf)
        scored.append((raw, t, int(df), int(cf)))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [
        {"term": t, "df": df, "cf": cf, "topic_score": round(s, 4)}
        for s, t, df, cf in scored[:top_n]
    ]


def build_term_ledger_payload(
    corpus: CorpusTokenStats,
    *,
    stop_words: frozenset[str],
    high_df_omit: frozenset[str] | None = None,
    top_n: int = 80,
    topic_top_n: int = 40,
    profile_version: str = "nav_topic_v3",
    spelling_normalization_version: str = SPELLING_NORMALIZATION_VERSION,
    spelling_corrections_applied: int = 0,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Emit the diagnostic term-ledger projection for raw-seed navigation.
    - Mechanism: Summarize corpus DF/CF leaders, omit diagnostics, topic-unigram rankings, and spelling-normalization metadata into one JSON payload.
    - Guarantee: Returns a dict shaped for raw_seed_term_ledger.json; the payload is diagnostic only.
    - Fails: None.
    - When-needed: Open when the raw-seed pipeline needs the exact ledger payload written beside the registry for diagnostics and navigation tuning.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_payload; codex/standards/observe_apply/std_raw_seed.md
    """
    n = corpus.n_docs
    top_cf = [
        {"term": t, "cf": int(c), "df": int(corpus.df_unigram.get(t, 0))}
        for t, c in corpus.cf_unigram.most_common(top_n)
    ]
    top_df = [
        {"term": t, "df": int(d), "cf": int(corpus.cf_unigram.get(t, 0))}
        for t, d in corpus.df_unigram.most_common(top_n)
    ]
    omit = high_df_omit if high_df_omit is not None else frozenset()
    topic_block = top_topic_unigrams_for_ledger(corpus, stop_words, top_n=topic_top_n)
    return {
        "kind": "raw_seed_term_ledger",
        "profile": profile_version,
        "n_paragraphs": n,
        "high_df_omit_unigram_count": len(omit),
        "high_df_quantile": HIGH_DOCUMENT_FREQUENCY_QUANTILE,
        "top_unigrams_by_collection_frequency": top_cf,
        "top_unigrams_by_document_frequency": top_df,
        "top_topic_unigrams": topic_block,
        "spelling_normalization_version": spelling_normalization_version,
        "spelling_corrections_applied": int(spelling_corrections_applied),
    }


def _split_sentences(text: str) -> list[str]:
    parts = _SENT_SPLIT_RE.split(str(text or ""))
    return [p.strip() for p in parts if p and p.strip()]


def _rake_phrases_from_sentence(sentence: str, stop_words: frozenset[str]) -> list[str]:
    words = re.findall(r"[a-z0-9']+", sentence.casefold())
    phrases: list[str] = []
    cur: list[str] = []
    for w in words:
        if len(w) < 2 or w in stop_words:
            if cur:
                phrases.append(" ".join(cur))
                cur = []
            continue
        cur.append(w)
    if cur:
        phrases.append(" ".join(cur))
    return [p for p in phrases if p and len(p) > 2]


def rake_ranked_phrases(text: str, stop_words: frozenset[str], *, max_phrases: int = 16) -> list[tuple[str, float]]:
    """[ACTION]
    - Teleology: Produce RAKE-style phrase candidates from one paragraph block.
    - Mechanism: Split the text into sentences, build phrase candidates around stopword boundaries, score them, and return the top phrases.
    - Guarantee: Returns at most `max_phrases` `(phrase, score)` tuples ordered by descending score.
    - Fails: None.
    - When-needed: Open when debugging why multiword phrase salvage appeared or disappeared from raw-seed keyword hints.
    - Escalates-to: system/lib/raw_seed_keyphrase.py::merge_distinctive_keyword_hints; system/lib/raw_seed_registry.py::build_raw_seed_payload
    """
    phrase_list: list[str] = []
    for sent in _split_sentences(text):
        phrase_list.extend(_rake_phrases_from_sentence(sent, stop_words))
    if not phrase_list:
        return []
    word_freq: Counter[str] = Counter()
    word_degree: Counter[str] = Counter()
    for phrase in phrase_list:
        words = phrase.split()
        deg = max(len(words) - 1, 0)
        for w in words:
            word_freq[w] += 1
            word_degree[w] += deg
    for w in word_freq:
        word_degree[w] += word_freq[w]
    word_score = {w: word_degree[w] / word_freq[w] for w in word_freq}
    cand: dict[str, float] = {}
    for phrase in phrase_list:
        words = phrase.split()
        if not words:
            continue
        cand[phrase] = cand.get(phrase, 0.0) + sum(word_score.get(w, 0.0) for w in words)
    ranked = sorted(cand.items(), key=lambda x: x[1], reverse=True)
    return ranked[:max_phrases]


def salvage_tokens(raw_block: str, *, max_items: int = 12) -> list[str]:
    """[ACTION]
    - Teleology: Recover path-like or identifier-like tokens that should survive stopword-heavy prose.
    - Mechanism: Regex-scan the raw markdown block, preserve distinctive path/id tokens, dedupe them, and cap the output.
    - Guarantee: Returns a bounded list of distinctive salvage tokens in encounter order.
    - Fails: None.
    - When-needed: Open when raw-seed hints depend on path/ID salvage rather than topical unigram scoring alone.
    - Escalates-to: system/lib/raw_seed_keyphrase.py::merge_distinctive_keyword_hints; system/lib/raw_seed_registry.py::build_raw_seed_payload
    """
    """Paths, identifiers, CamelCase-ish tokens — first-seen order, deduped case-insensitively."""
    ordered: list[str] = []
    seen: set[str] = set()
    for token in _SALVAGE_RE.findall(str(raw_block or "")):
        n = token.casefold()
        if n.startswith("http"):
            continue
        if n in seen:
            continue
        seen.add(n)
        ordered.append(token)
        if len(ordered) >= max_items:
            break
    return ordered


def _is_path_like_salvage(token: str) -> bool:
    t = token.casefold()
    return "/" in t or t.endswith((".py", ".md", ".json", ".ts", ".tsx", ".yaml", ".yml", ".toml"))


def _display_form(raw_block: str, term_lower: str) -> str:
    if not term_lower:
        return ""
    if " " in term_lower:
        pattern = re.escape(term_lower).replace(r"\ ", r"\s+")
        m = re.search(pattern, str(raw_block or ""), flags=re.IGNORECASE)
        return m.group(0).strip() if m else term_lower
    m = re.search(r"(?<![A-Za-z0-9])" + re.escape(term_lower) + r"(?![A-Za-z0-9])", str(raw_block or ""), flags=re.IGNORECASE)
    return m.group(0) if m else term_lower


def _display_form_map(raw_block: str) -> dict[str, str]:
    display: dict[str, str] = {}
    for match in _TOKEN_RE.finditer(str(raw_block or "")):
        token = match.group(0)
        key = token.casefold()
        if key not in display:
            display[key] = token
    return display


def _display_form_fast(raw_block: str, raw_lower: str, term_lower: str, display_map: dict[str, str]) -> str:
    term = str(term_lower or "").strip()
    if not term:
        return ""
    if " " not in term:
        return display_map.get(term.casefold(), term)

    raw = str(raw_block or "")
    parts = [part for part in term.casefold().split() if part]
    if not parts:
        return term
    first = parts[0]
    start = raw_lower.find(first)
    while start >= 0:
        pos = start + len(first)
        ok = True
        for part in parts[1:]:
            while pos < len(raw_lower) and raw_lower[pos].isspace():
                pos += 1
            if not raw_lower.startswith(part, pos):
                ok = False
                break
            pos += len(part)
        if ok:
            return raw[start:pos].strip()
        start = raw_lower.find(first, start + 1)
    return term


def _canonical_token_sequence(
    plain_text: str,
    stop_words: frozenset[str],
    ultra_generic: frozenset[str],
    normalize_unigram: Callable[[str], tuple[str, bool]],
    correction_counter: list[int],
) -> tuple[list[str], Counter[str]]:
    seq: list[str] = []
    for m in _TOKEN_RE.finditer(str(plain_text or "")):
        w = m.group(0).casefold()
        if len(w) < 3 or w in stop_words or w in ultra_generic:
            continue
        canon, corrected = normalize_unigram(w)
        if corrected:
            correction_counter[0] += 1
        if len(canon) < 3 or canon in ultra_generic:
            continue
        seq.append(canon)
    return seq, Counter(seq)


def merge_distinctive_keyword_hints(
    raw_block: str,
    plain_text: str,
    doc_index: int,
    corpus: CorpusTokenStats,
    stop_words: frozenset[str],
    section_boost_tokens: frozenset[str],
    mechanism_vocab_unigrams: frozenset[str],
    normalize_unigram: Callable[[str], tuple[str, bool]],
    correction_counter: list[int],
    *,
    ultra_generic: frozenset[str] | None = None,
    max_items: int = 8,
    min_tokens_for_rake: int = 5,
) -> list[str]:
    """[ACTION]
    - Teleology: Derive the bounded `keyword_hints` lane for one raw-seed paragraph.
    - Mechanism: Merge salvage identifiers, topic-scored unigrams/bigrams, RAKE phrases, and section/mechanism boosts into one deduped ranked hint list.
    - Guarantee: Returns at most `max_items` display-form hints for the paragraph; out-of-range doc indexes return an empty list.
    - Fails: None.
    - When-needed: Open when paragraph-level keyword hints need to be explained, tuned, or debugged from the registry pipeline.
    - Escalates-to: system/lib/raw_seed_registry.py::build_raw_seed_payload; system/lib/raw_seed_spelling.py::build_corpus_hint_normalizer
    - Navigation-group: kernel_lib
    """
    ultra = ultra_generic if ultra_generic is not None else ULTRA_GENERIC_UNIGRAMS
    if doc_index < 0 or doc_index >= corpus.n_docs:
        return []

    raw_block_text = str(raw_block or "")
    raw_lower = raw_block_text.casefold()
    display_map = _display_form_map(raw_block_text)
    toks = _tokenize_for_corpus(plain_text, stop_words)
    seq, canon_tf = _canonical_token_sequence(
        plain_text, stop_words, ultra, normalize_unigram, correction_counter
    )

    candidates: list[tuple[str, float, str]] = []

    for st in salvage_tokens(raw_block, max_items=max_items + 8):
        k = st.casefold()
        if k in stop_words:
            continue
        if _is_path_like_salvage(st):
            candidates.append((st, 4.85, "salvage_path"))
            continue
        if k in ultra:
            continue
        canon, _cor = normalize_unigram(k)
        if len(canon) < 3 or canon in ultra:
            continue
        tf = max(canon_tf.get(canon, 0), 1)
        s = 0.55 * topic_score_unigram(corpus, canon, tf) + 0.4
        if canon in section_boost_tokens:
            s += 0.35
        if canon in mechanism_vocab_unigrams:
            s += _MECHANISM_TOPIC_BONUS
        disp = _display_form_fast(raw_block_text, raw_lower, canon, display_map)
        candidates.append((disp, s, "salvage_ident"))

    for canon, tf in canon_tf.items():
        if canon in ultra:
            continue
        s = topic_score_unigram(corpus, canon, tf)
        if canon in section_boost_tokens:
            s += 0.35
        if canon in mechanism_vocab_unigrams:
            s += _MECHANISM_TOPIC_BONUS
        disp = _display_form_fast(raw_block_text, raw_lower, canon, display_map)
        candidates.append((disp, s, "topic_unigram"))

    pair_tf: Counter[str] = Counter()
    for i in range(len(seq) - 1):
        a, b = seq[i], seq[i + 1]
        if a in ultra or b in ultra:
            continue
        pair_tf[f"{a} {b}"] += 1

    for pair, tf in pair_tf.items():
        if tf <= 0:
            continue
        parts = pair.split()
        if len(parts) != 2 or parts[0] in ultra or parts[1] in ultra:
            continue
        s = topic_score_bigram(corpus, pair, tf)
        if any(p in section_boost_tokens for p in parts):
            s += 0.35
        disp = _display_form_fast(raw_block_text, raw_lower, pair, display_map)
        candidates.append((disp, s, "topic_bigram"))

    rake_n = 14 if len(toks) < min_tokens_for_rake else 10
    rake_list = rake_ranked_phrases(plain_text, stop_words, max_phrases=rake_n)
    max_rake = max((s for _, s in rake_list), default=1.0)
    for phrase, rsc in rake_list:
        parts = phrase.split()
        norm_parts: list[str] = []
        skip = False
        for w in parts:
            if len(w) < 3 or w in ultra:
                skip = True
                break
            c, _cor = normalize_unigram(w)
            if len(c) < 3 or c in ultra:
                skip = True
                break
            norm_parts.append(c)
        if skip or not norm_parts:
            continue
        canon_phrase = " ".join(norm_parts)
        rake_norm = (rsc / max(max_rake, 1e-9)) * 3.2
        avg_g = sum(math.log(1 + corpus.df_unigram.get(x, 0)) for x in norm_parts) / max(len(norm_parts), 1)
        s = _RAKE_SCALE * rake_norm + 0.22 * avg_g
        disp = _display_form_fast(raw_block_text, raw_lower, canon_phrase, display_map)
        candidates.append((disp, s, "rake"))

    candidates.sort(key=lambda x: x[1], reverse=True)

    out: list[str] = []
    seen: set[str] = set()

    for disp, _sc, _src in candidates:
        d = disp.strip()
        if not d:
            continue
        k = d.casefold()
        if k in stop_words or k in seen:
            continue
        if " " in k:
            parts = k.split()
            if len(parts) >= 2 and all(p in seen for p in parts):
                continue
        seen.add(k)
        out.append(d)
        if len(out) >= max_items:
            break

    return out
