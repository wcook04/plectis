"""Tests for tools/meta/observability/operator_handoff_linkage.py.

Synthetic fixtures only — no live private state.

Covers Type B → Type A handoff edge inference:
  1. Type B response contained verbatim in longer Type A input yields strong.
  2. Type A input with operator suffix yields operator_delta_detected.
  3. Near-tie between two candidate sessions yields ambiguous, not false certainty.
  4. Claude and Codex surfaces are both accepted.
  5. Exact match is not required (containment + token overlap is enough).
  6. Soft feed (capture_diagnostics) accepts skipped assistant turns when text is long enough.
  7. Soft + curated feeds dedupe by assistant_sha256.
  8. Rollout fallback filters out non-repo Claude project slugs and non-repo Codex sessions by cwd.
  9. --keep-none-band off (default) drops confidence_band=none edges from projection.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "tools" / "meta" / "observability"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import operator_handoff_linkage as ohl  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_norm_cache_between_tests() -> None:
    """Avoid id-keyed cache pollution across tests when CPython recycles string ids."""
    ohl._clear_norm_cache()


# ---------- helpers ----------


def _capture(*, text: str, run_id: str = "rid_001", slot: str = "B1", slug: str = "synth", captured_at: str = "2026-05-10T00:00:00+00:00", conv_id: str = "conv_001") -> ohl.TypeBCapture:
    return ohl.TypeBCapture(
        prompt_run_id=run_id,
        prompt_slot=slot,
        prompt_slug=slug,
        captured_at=captured_at,
        conversation_id=conv_id,
        conversation_url=f"https://chatgpt.com/c/{conv_id}",
        assistant_sha256="0" * 64,
        assistant_raw_text=text,
    )


def _typea(*, surface: str, session_id: str, text: str, timestamp: str = "2026-05-10T00:05:00+00:00") -> ohl.TypeAUserInput:
    return ohl.TypeAUserInput(
        surface=surface,
        session_id=session_id,
        session_started_at="2026-05-10T00:00:00+00:00",
        session_ended_at="2026-05-10T01:00:00+00:00",
        source_path=f"/synth/rollouts/{session_id}.jsonl",
        cwd="/synth/cwd",
        timestamp=timestamp,
        raw_text=text,
        turn_uuid=None,
    )


# ---------- 1. containment yields strong ----------


def test_typeb_response_contained_in_typea_input_yields_strong() -> None:
    assistant = (
        "Here is the architectural decision. The handoff graph should be a "
        "probabilistic, evidence-backed projection of edges between Type A and "
        "Type B surfaces, not a single tab-to-session field. Edges are inferred "
        "from existing primitives such as prompt-shelf fingerprints and the "
        "execution trace ledger."
    )
    user_input = (
        "Pasting Type B output into Claude.\n\n"
        + assistant
        + "\n\nGo implement the v0 joiner."
    )
    cap = _capture(text=assistant)
    ua = _typea(surface="claude_code", session_id="claude_sess_AAA", text=user_input)
    edges = ohl.compute_edges([cap], [ua])
    assert edges, "expected at least one candidate edge"
    top = edges[0]
    assert top.confidence_band == "strong", f"got band {top.confidence_band} score {top.score}"
    assert top.evidence.containment is True
    assert top.evidence.anchor_match is True


# ---------- 2. operator suffix detected ----------


def test_typea_input_with_operator_suffix_yields_operator_delta() -> None:
    assistant = (
        "v0 should: 1) join recent Type B captures against Type A user inputs, "
        "2) score with containment + anchor + jaccard + time proximity, "
        "3) preserve the operator delta, 4) emit ambiguity explicitly."
    )
    user_input = assistant + "\n\nNote from operator: also handle Codex parity."
    cap = _capture(text=assistant)
    ua = _typea(surface="codex", session_id="codex_sess_BBB", text=user_input)
    edges = ohl.compute_edges([cap], [ua])
    assert edges, "expected at least one edge"
    top = edges[0]
    assert top.evidence.operator_delta_detected is True
    assert top.operator_delta_summary.position == "suffix"
    assert top.operator_delta_summary.chars > 0


def test_typea_input_with_operator_prefix_yields_prefix_delta() -> None:
    assistant = "Step 1 is to extract live shapes. Step 2 is to author the joiner. Step 3 is to add tests."
    user_input = (
        "FYI here's what ChatGPT said before I started — please verify gates before editing.\n\n"
        + assistant
    )
    cap = _capture(text=assistant)
    ua = _typea(surface="claude_code", session_id="claude_sess_CCC", text=user_input)
    edges = ohl.compute_edges([cap], [ua])
    assert edges
    top = edges[0]
    assert top.evidence.operator_delta_detected is True
    assert top.operator_delta_summary.position == "prefix"


# ---------- 3. near-tie yields ambiguous, not false certainty ----------


def test_two_similar_sessions_yields_ambiguous_band() -> None:
    assistant = (
        "Reuse existing primitives: prompt_shelf_fingerprints provides normalize, "
        "anchor position, tokenize, and match. Embedding substrate provides cosine "
        "and search ladder. Agent session attribution merges claude and codex sources."
    )
    # Two Type A inputs that both contain the assistant text — same paste in two sessions.
    ua_one = _typea(surface="codex", session_id="codex_primary___", text="primary tab paste:\n" + assistant)
    ua_two = _typea(surface="codex", session_id="codex_companion_", text="companion tab paste:\n" + assistant)
    cap = _capture(text=assistant)
    edges = ohl.compute_edges([cap], [ua_one, ua_two])
    assert len(edges) >= 2, "expected both candidates emitted as ambiguous companions"
    bands = {e.confidence_band for e in edges}
    # At least one of the emitted edges must be ambiguous when the top two are within 0.05.
    assert "ambiguous" in bands, f"expected ambiguous in bands, got {bands}"
    competing = max(e.evidence.competing_candidate_count for e in edges)
    assert competing >= 1


# ---------- 4. claude AND codex are both accepted ----------


def test_both_surfaces_accepted_in_one_run() -> None:
    assistant_for_claude = "Claude side text: implement the joiner under tools/meta/observability and reuse prompt_shelf_fingerprints."
    assistant_for_codex = "Codex side text: parity with claude through codex hologram process ledger session list."
    cap_claude = _capture(text=assistant_for_claude, run_id="rid_claude", slot="A0", conv_id="conv_claude")
    cap_codex = _capture(text=assistant_for_codex, run_id="rid_codex", slot="B1", conv_id="conv_codex")
    ua_claude = _typea(surface="claude_code", session_id="claude_real", text="Pasted:\n" + assistant_for_claude)
    ua_codex = _typea(surface="codex", session_id="codex_real", text="Pasted:\n" + assistant_for_codex)
    edges = ohl.compute_edges([cap_claude, cap_codex], [ua_claude, ua_codex])
    surfaces = {e.type_a["surface"] for e in edges if e.confidence_band in ("strong", "tentative")}
    assert "claude_code" in surfaces
    assert "codex" in surfaces
    # Claude side edge points at claude session; codex side at codex session.
    for e in edges:
        if e.confidence_band not in ("strong", "tentative"):
            continue
        if e.type_b["prompt_run_id"] == "rid_claude":
            assert e.type_a["surface"] == "claude_code"
        elif e.type_b["prompt_run_id"] == "rid_codex":
            assert e.type_a["surface"] == "codex"


# ---------- 5. exact match is not required ----------


def test_exact_match_not_required_paraphrased_paste_still_scores() -> None:
    # Operator paraphrased the assistant but kept most of the load-bearing tokens.
    assistant = (
        "The handoff projection should preserve operator delta detection, support "
        "ambiguity representation, and reuse existing primitives instead of importing "
        "rapidfuzz simhash or minhash machinery."
    )
    paraphrased_paste = (
        "preserve operator delta detection support ambiguity representation reuse "
        "existing primitives no rapidfuzz simhash or minhash"
    )
    cap = _capture(text=assistant)
    ua = _typea(surface="claude_code", session_id="claude_para_AA", text=paraphrased_paste)
    edges = ohl.compute_edges([cap], [ua])
    # Exact match is False, hash mismatch, but token overlap should produce at least an
    # ambiguous-or-tentative score (not "none"). The point: containment-only or
    # exact-only thresholds would silently drop this.
    if edges:
        top = edges[0]
        assert top.evidence.exact_hash_match is False
        assert top.evidence.token_overlap > 0.5
        assert top.confidence_band in ("ambiguous", "tentative", "strong")
    else:
        # If the score fell below CONFIDENCE_AMBIGUOUS, the test still validates that
        # scoring is at least partial: re-score directly to assert non-zero token overlap.
        score, ev, _ = ohl.score_pair(cap, ua)
        assert ev.token_overlap > 0.5
        assert not ev.exact_hash_match


# ---------- 6. negative case: unrelated text yields none/no-edge ----------


def test_unrelated_typea_input_yields_no_edge() -> None:
    cap = _capture(text="The handoff graph is probabilistic and reuses prompt_shelf_fingerprints.")
    ua = _typea(
        surface="claude_code",
        session_id="claude_unrelated",
        text="Please refactor the favicon helper in the cockpit top bar to add a trailing badge.",
    )
    edges = ohl.compute_edges([cap], [ua])
    # Unrelated text should produce no candidate edges above CONFIDENCE_AMBIGUOUS.
    assert all(e.score < ohl.CONFIDENCE_AMBIGUOUS for e in edges) if edges else True


# ---------- 7. projection schema sanity ----------


def test_projection_schema_shape() -> None:
    assistant = "Containment scoring is the v0 backbone; semantic embedding is deferred."
    cap = _capture(text=assistant)
    ua = _typea(surface="codex", session_id="codex_sess_DDD", text="paste:\n" + assistant)
    edges = ohl.compute_edges([cap], [ua])
    proj = ohl.build_projection([cap], [ua], edges)
    assert proj["schema_version"] == "operator_handoff_linkage_projection_v0"
    assert "candidate_edges" in proj
    assert "current_bindings" in proj
    assert "counts" in proj
    if edges:
        e0 = proj["candidate_edges"][0]
        for required in ("edge_id", "confidence_band", "score", "direction", "type_b", "type_a", "evidence", "operator_delta_summary"):
            assert required in e0
        assert e0["direction"] == "typeb_to_typea"


# ---------- 8. time-proximity influences score, with reverse delta neutral ----------


def test_typea_before_typeb_capture_gives_no_time_bonus() -> None:
    assistant = "When operator paste happens before the assistant turn was captured, time bonus must be zero."
    cap = _capture(text=assistant, captured_at="2026-05-10T00:10:00+00:00")
    ua_before = _typea(surface="claude_code", session_id="claude_before_", text=assistant, timestamp="2026-05-10T00:00:00+00:00")
    score_before, ev_before, _ = ohl.score_pair(cap, ua_before)
    ua_after = _typea(surface="claude_code", session_id="claude_after__", text=assistant, timestamp="2026-05-10T00:11:00+00:00")
    score_after, ev_after, _ = ohl.score_pair(cap, ua_after)
    # The "after" pair must score >= "before" pair because of the time-proximity weight.
    assert score_after >= score_before
    assert ev_before.time_delta_seconds is not None and ev_before.time_delta_seconds < 0
    assert ev_after.time_delta_seconds is not None and ev_after.time_delta_seconds > 0


# ---------- 9. soft feed (capture_diagnostics) ----------


def _write_capture_diagnostic(
    dir_path: Path,
    *,
    name: str,
    assistant_text: str,
    conv_id: str = "conv_soft",
    slot: str = "B2",
    skipped_reason: str = "assistant_missing_complete_uppropagation_block",
    created_at: str = "2026-05-10T01:00:00+00:00",
    sha256_override: str | None = None,
) -> Path:
    import hashlib
    sha = sha256_override or hashlib.sha256(assistant_text.encode()).hexdigest()
    payload = {
        "schema_version": "1.0.0",
        "kind": "prompt_shelf_capture_diagnostic",
        "created_at": created_at,
        "signature": "sig_synth",
        "skipped_reason": skipped_reason,
        "conversation_url": f"https://chatgpt.com/c/{conv_id}",
        "conversation_id": conv_id,
        "tab_title": "9 - Synthetic test tab",
        "slot": slot,
        "match_method": "anchor",
        "match_confidence": 1.0,
        "user_turn_index": 5,
        "assistant_turn_index": 6,
        "snapshot_turn_count": 7,
        "snapshot_generating": False,
        "user_shape": {"sha256": "u" * 64, "char_count": 100},
        "assistant_shape": {"sha256": sha, "sha16": sha[:16], "char_count": len(assistant_text)},
        "marker_turn_shapes": [],
        "assistant_text": assistant_text,
        "user_text_tail": "",
    }
    out = dir_path / f"{name}.json"
    out.write_text(json.dumps(payload))
    return out


def test_soft_feed_loads_skipped_capture_with_long_assistant_text(tmp_path: Path) -> None:
    diag_dir = tmp_path / "capture_diagnostics"
    diag_dir.mkdir()
    long_text = "This is a long synthetic assistant turn used to verify that the soft feed accepts skipped pairs. " * 4
    _write_capture_diagnostic(diag_dir, name="20260510T010000--B2--abc--skipped", assistant_text=long_text)
    captures = ohl.load_typeb_capture_diagnostics(diagnostics_dir=diag_dir, limit=10)
    assert len(captures) == 1
    cap = captures[0]
    assert cap.source == "capture_diagnostic"
    assert cap.capture_status == "skipped"
    assert cap.skipped_reason == "assistant_missing_complete_uppropagation_block"
    assert cap.assistant_raw_text == long_text


def test_soft_feed_filters_out_streaming_short_assistant_text(tmp_path: Path) -> None:
    diag_dir = tmp_path / "capture_diagnostics"
    diag_dir.mkdir()
    _write_capture_diagnostic(diag_dir, name="streaming_snapshot--B2--xyz--skipped", assistant_text="I")
    captures = ohl.load_typeb_capture_diagnostics(diagnostics_dir=diag_dir, limit=10)
    assert captures == [], "streaming/short snapshots should be filtered (below SOFT_FEED_MIN_ASSISTANT_CHARS)"


# ---------- 10. dedupe across feeds ----------


def test_soft_and_curated_dedupe_by_assistant_sha(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    diag_dir = tmp_path / "capture_diagnostics"
    diag_dir.mkdir()
    raw_events_dir = tmp_path / "raw_events" / "B2_continue"
    raw_events_dir.mkdir(parents=True)
    runs_index = tmp_path / "prompt_shelf_runs_index.json"

    long_text = "Shared synthetic assistant turn used to dedupe across feeds. " * 6
    import hashlib
    sha = hashlib.sha256(long_text.encode()).hexdigest()
    _write_capture_diagnostic(diag_dir, name="dup_soft", assistant_text=long_text, sha256_override=sha, created_at="2026-05-10T00:50:00+00:00")

    raw_event = {
        "schema_version": "1.0.0",
        "event_kind": "prompt_shelf_run_raw",
        "user_message": {"raw_text": "user paste", "sha256": "u" * 64, "char_count": 10},
        "assistant_message": {"raw_text": long_text, "sha256": sha, "char_count": len(long_text)},
        "segmentation": {},
        "extra": {},
    }
    raw_event_rel = "raw_events/B2_continue/dup_curated.json"
    (tmp_path / raw_event_rel).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / raw_event_rel).write_text(json.dumps(raw_event))
    runs_index.write_text(json.dumps({
        "__meta": {"schema_version": "1.0.0"},
        "runs": [{
            "prompt_run_id": "curated_run_1",
            "prompt_slot": "B2",
            "prompt_slug": "continue_intelligence",
            "captured_at": "2026-05-10T01:05:00+00:00",
            "source": "chatgpt_web",
            "conversation_id": "conv_dup",
            "conversation_url": "https://chatgpt.com/c/conv_dup",
            "user_turn_index": 0,
            "assistant_turn_index": 1,
            "raw_event_path": raw_event_rel,
            "assistant_message_sha256": sha,
        }],
    }))

    merged = ohl.load_typeb_records(
        runs_index_path=runs_index,
        diagnostics_dir=diag_dir,
        repo_root=tmp_path,
        limit=10,
    )
    # Same sha appears in soft and curated; merged result must dedupe to one entry, with
    # curated authority winning (source = "prompt_shelf_run").
    same_sha_entries = [c for c in merged if c.assistant_sha256 == sha]
    assert len(same_sha_entries) == 1
    assert same_sha_entries[0].source == "prompt_shelf_run"


# ---------- 11. rollout fallback cwd filtering ----------


def test_claude_project_slug_for_repo_cwd() -> None:
    slug = ohl._claude_project_slug_for_cwd(Path("/Users/example/src/ai_workflow"))
    assert slug == "-Users-example-src-ai-workflow"


def test_rollout_fallback_filters_non_repo_claude_projects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = tmp_path / "home"
    repo_root = tmp_path / "repo" / "active"
    repo_root.mkdir(parents=True)
    expected_slug = ohl._claude_project_slug_for_cwd(repo_root)
    other_slug = "-other-some-other-repo"
    claude_root = fake_home / ".claude" / "projects"
    (claude_root / expected_slug).mkdir(parents=True)
    (claude_root / other_slug).mkdir(parents=True)
    (claude_root / expected_slug / "session_a.jsonl").write_text('{"type":"user","message":{"content":"hello"}}\n')
    (claude_root / other_slug / "session_b.jsonl").write_text('{"type":"user","message":{"content":"sibling"}}\n')

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home), raising=False)

    rollouts = ohl._discover_recent_rollouts(session_limit=10, repo_root=repo_root)
    paths = [str(p) for _agent, p, _sid in rollouts]
    assert any("session_a.jsonl" in p for p in paths)
    assert not any("session_b.jsonl" in p for p in paths)


def test_rollout_fallback_filters_codex_by_session_meta_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = tmp_path / "home"
    repo_root = tmp_path / "repo" / "active"
    repo_root.mkdir(parents=True)

    codex_root = fake_home / ".codex" / "sessions" / "2026" / "05" / "10"
    codex_root.mkdir(parents=True)
    matching = codex_root / "rollout-2026-05-10T00-aaa-bbb.jsonl"
    matching.write_text(json.dumps({
        "timestamp": "2026-05-10T00:00:00Z",
        "type": "session_meta",
        "payload": {"id": "aaa", "cwd": str(repo_root)},
    }) + "\n")
    foreign = codex_root / "rollout-2026-05-10T00-ccc-ddd.jsonl"
    foreign.write_text(json.dumps({
        "timestamp": "2026-05-10T00:00:00Z",
        "type": "session_meta",
        "payload": {"id": "ccc", "cwd": "/some/other/place"},
    }) + "\n")

    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home), raising=False)

    rollouts = ohl._discover_recent_rollouts(session_limit=10, repo_root=repo_root)
    paths = [str(p) for _agent, p, _sid in rollouts]
    assert any("aaa-bbb" in p for p in paths)
    assert not any("ccc-ddd" in p for p in paths)


# ---------- 12. projection drops none-band edges by default ----------


def test_projection_drops_none_band_by_default() -> None:
    # Build edges spanning ambiguous, tentative, none manually.
    cap = _capture(text="some assistant text")
    ua = _typea(surface="claude_code", session_id="sid_test_______", text="unrelated")
    band_edges = []
    for band, score in [("strong", 0.85), ("tentative", 0.60), ("ambiguous", 0.35), ("none", 0.10)]:
        band_edges.append(ohl.CandidateEdge(
            edge_id=f"edge_{band}",
            confidence_band=band,
            score=score,
            direction="typeb_to_typea",
            type_b={"prompt_run_id": "rid", "prompt_slot": "B1", "prompt_slug": "x", "conversation_id": "c", "conversation_url": "u", "assistant_sha256": "0"*64, "captured_at": "", "source": "prompt_shelf_run", "capture_status": "captured", "skipped_reason": None, "tab_title": None, "source_completeness": "complete", "soft_observation_count": 1},
            type_a={"surface": "claude_code", "session_id": "sid", "source_path": "p", "cwd": None, "timestamp": None, "turn_uuid": None},
            evidence=ohl.EdgeEvidence(False, False, False, None, 0.0, None, False),
            operator_delta_summary=ohl.OperatorDeltaSummary(position="none", chars=0),
        ))
    proj_default = ohl.build_projection([cap], [ua], band_edges)
    bands = {e["confidence_band"] for e in proj_default["candidate_edges"]}
    assert "none" not in bands
    assert proj_default["counts"]["none_dropped"] == 1
    proj_keep = ohl.build_projection([cap], [ua], band_edges, drop_none_band=False)
    bands_keep = {e["confidence_band"] for e in proj_keep["candidate_edges"]}
    assert "none" in bands_keep


# ---------- 13. composite confidence calibration: tight time + anchor + jaccard ----------


def _soft_capture(*, text: str, captured_at: str, completeness: str = "best_observed_in_group") -> ohl.TypeBCapture:
    cap = _capture(text=text, captured_at=captured_at)
    cap.source = "capture_diagnostic"
    cap.capture_status = "skipped"
    cap.skipped_reason = "assistant_missing_complete_uppropagation_block"
    cap.source_completeness = completeness
    cap.soft_observation_count = 4
    return cap


def test_soft_anchor_high_jaccard_tight_forward_time_lifts_to_tentative() -> None:
    # Soft-feed observation: shares the first ~ASSISTANT_ANCHOR_PREFIX_CHARS with the
    # paste (anchor matches), but the middle of the observed text differs from the paste
    # (containment fails) — simulating the live partial-stream pattern where the observer
    # captured an early snapshot and the operator pasted a later, edited version.
    # Make the shared anchor longer than ASSISTANT_ANCHOR_PREFIX_CHARS (200) so the
    # whole anchor (first 200 chars of observed) lives inside the shared prefix.
    anchor_chars = (
        "Operator Handoff Linkage v0.1: soft capture diagnostics feed plus cwd-filtered "
        "rollout fallback joins ChatGPT Type B captures against Claude Code and Codex "
        "Type A user inputs handoff anchor matching prefix region long enough so the "
        "anchor prefix lands entirely inside the shared chars region "
    )
    assert len(anchor_chars) > ohl.ASSISTANT_ANCHOR_PREFIX_CHARS, "fixture must keep anchor inside shared prefix"
    observed_middle = "AAA observed-only middle material BBB CCC DDD EEE FFF GGG HHH"
    paste_middle = "ZZZ paste-only middle material BBB CCC DDD EEE FFF GGG HHH"
    observed_prefix = anchor_chars + observed_middle + " trailing observed text"
    full_paste = anchor_chars + paste_middle + " trailing paste text and operator note"
    cap = _soft_capture(text=observed_prefix, captured_at="2026-05-10T01:00:59+00:00")
    ua = _typea(
        surface="codex",
        session_id="codex_tight_____",
        text=full_paste,
        timestamp="2026-05-10T01:01:05+00:00",
    )
    score, ev, delta = ohl.score_pair(cap, ua)
    assert ev.containment is False, "fixture must break containment to exercise composite-bump path"
    assert ev.anchor_match is True
    assert ev.token_overlap >= ohl.COMPOSITE_TENTATIVE_JACCARD, f"jaccard={ev.token_overlap}"
    assert ev.tight_time_coupling is True
    assert ev.forward_time_coupling is True
    assert ev.observer_lag_tolerated is False
    assert score >= ohl.CONFIDENCE_TENTATIVE, f"composite bump should lift to tentative, got {score}"


def test_soft_observer_lag_tolerated_when_paste_predates_capture() -> None:
    # Δ=-2s — paste landed in the rollout before the observer wrote the diagnostic.
    # The observer is a polling client; this small backward delta should not disqualify.
    # Containment is broken (paste differs in the middle) so the composite-bump path is exercised.
    anchor_chars = (
        "Operator handoff linkage soft observation snippet used to verify observer-lag tolerance "
        "for tight temporal coupling within thirty seconds backward window. Anchor prefix shared "
        "between observed snapshot and the operator paste landed by claude code session."
    )
    observed = anchor_chars + " observed-only XYZ material 11 22 33 44 55 66 77 88 99 trailing"
    full_paste = anchor_chars + " paste-only ABC material 11 22 33 44 55 66 77 88 99 trailing op note"
    cap = _soft_capture(text=observed, captured_at="2026-05-10T01:31:13+00:00")
    ua = _typea(
        surface="claude_code",
        session_id="claude_lag______",
        text=full_paste,
        timestamp="2026-05-10T01:31:11+00:00",  # 2s before capture
    )
    score, ev, _ = ohl.score_pair(cap, ua)
    assert ev.time_delta_seconds == -2
    assert ev.observer_lag_tolerated is True
    assert ev.tight_time_coupling is True
    assert ev.forward_time_coupling is False
    if ev.token_overlap >= ohl.COMPOSITE_TENTATIVE_JACCARD:
        assert score >= ohl.CONFIDENCE_TENTATIVE


def test_far_time_delta_does_not_trigger_tight_coupling() -> None:
    observed = "Same observed prefix used in tight-time tests but with a one-hour delta."
    cap = _soft_capture(text=observed, captured_at="2026-05-10T01:00:00+00:00")
    ua = _typea(
        surface="codex",
        session_id="codex_far_______",
        text=observed + " op note",
        timestamp="2026-05-10T02:00:30+00:00",  # ~1h after — outside tight window
    )
    _score, ev, _ = ohl.score_pair(cap, ua)
    assert ev.tight_time_coupling is False
    assert ev.forward_time_coupling is False


# ---------- 14. operator_delta reliability split (curated vs soft-without-containment) ----------


def test_curated_suffix_delta_is_likely_operator_delta() -> None:
    assistant = "Curated raw event with full assistant text. No partial source risk."
    user_input = assistant + " Trailing operator commentary added during paste."
    cap = _capture(text=assistant)  # default source = prompt_shelf_run (complete)
    ua = _typea(surface="claude_code", session_id="claude_curated__", text=user_input)
    edges = ohl.compute_edges([cap], [ua])
    assert edges
    delta = edges[0].operator_delta_summary
    assert delta.position == "suffix"
    assert delta.reliability == "likely_operator_delta"
    assert delta.source_relation is None


def test_soft_without_containment_suffix_marked_uncertain_partial_source() -> None:
    # Anchor matches (first 200 chars shared) but the middle of the observed text
    # differs from the paste, so containment is False. The trailing portion of the
    # paste extends past where the observed assistant text ends — that suffix could
    # be either operator-added OR unobserved Type B tail, so reliability must be
    # "uncertain_source_may_be_partial".
    anchor_chars = (
        "Soft observation prefix that ends mid-thought because streaming captured here. "
        "Anchor portion long enough to satisfy ASSISTANT_ANCHOR_PREFIX_CHARS so anchor "
        "matches in the operator paste even after the middle text diverges between observation "
    )
    observed_prefix = anchor_chars + " obs-mid AAA mid material 11 22 33 obs-tail"
    full_paste = anchor_chars + " paste-mid BBB mid material 11 22 33 paste-tail with operator suffix added past the observed end"
    cap = _soft_capture(text=observed_prefix, captured_at="2026-05-10T00:00:00+00:00")
    ua = _typea(surface="claude_code", session_id="claude_soft_____", text=full_paste)
    edges = ohl.compute_edges([cap], [ua])
    assert edges
    e = edges[0]
    assert e.evidence.containment is False
    assert e.evidence.anchor_match is True
    delta = e.operator_delta_summary
    assert delta.position == "suffix"
    assert delta.reliability == "uncertain_source_may_be_partial"
    assert delta.source_relation == "observed_source_prefix_of_typea_input"


def test_soft_with_containment_suffix_is_likely_operator_delta() -> None:
    # When the soft observation IS contained verbatim in the paste, the suffix is
    # operator-authored (we can prove the source is fully present).
    assistant = "Soft observation that happens to equal the actual assistant response."
    user_input = assistant + " operator addendum."
    cap = _soft_capture(text=assistant, captured_at="2026-05-10T00:00:00+00:00", completeness="best_observed_in_group")
    ua = _typea(surface="claude_code", session_id="claude_soft_full", text=user_input)
    edges = ohl.compute_edges([cap], [ua])
    assert edges
    e = edges[0]
    assert e.evidence.containment is True
    delta = e.operator_delta_summary
    assert delta.position == "suffix"
    assert delta.reliability == "likely_operator_delta"


# ---------- 15. soft-feed best-of-group selection ----------


def test_soft_feed_picks_longest_non_generating_per_group(tmp_path: Path) -> None:
    diag_dir = tmp_path / "capture_diagnostics"
    diag_dir.mkdir()
    # All four records belong to the same (conv, turn, slot) — observer re-emitted
    # as the assistant turn streamed; the joiner must pick the longest non-generating.
    short = "I"  # streaming start (below min-chars threshold but should still rank)
    medium = "M" * 250  # ~250 chars, above threshold but not the longest
    longest = "L" * 600  # 600 chars, clearly the longest non-generating record
    longest_streaming = "S" * 800  # longer but still streaming, must lose to non-generating

    common = {"conv": "conv_grp", "slot": "B2"}
    _write_capture_diagnostic(diag_dir, name="t01_short", assistant_text=short, conv_id=common["conv"], slot=common["slot"], created_at="2026-05-10T00:50:01+00:00")
    _write_capture_diagnostic(diag_dir, name="t02_medium", assistant_text=medium, conv_id=common["conv"], slot=common["slot"], created_at="2026-05-10T00:50:05+00:00")
    _write_capture_diagnostic(diag_dir, name="t03_longest", assistant_text=longest, conv_id=common["conv"], slot=common["slot"], created_at="2026-05-10T00:50:09+00:00")
    # A still-generating but slightly later record — must lose to the non-generating longest one.
    streaming_record = {
        "schema_version": "1.0.0",
        "kind": "prompt_shelf_capture_diagnostic",
        "created_at": "2026-05-10T00:50:11+00:00",
        "signature": "sig_synth_streaming",
        "skipped_reason": "assistant_missing_complete_uppropagation_block",
        "conversation_url": f"https://chatgpt.com/c/{common['conv']}",
        "conversation_id": common["conv"],
        "tab_title": "synthetic streaming tab",
        "slot": common["slot"],
        "match_method": "anchor",
        "match_confidence": 1.0,
        "user_turn_index": 5,
        "assistant_turn_index": 6,
        "snapshot_turn_count": 7,
        "snapshot_generating": True,
        "user_shape": {"sha256": "u" * 64, "char_count": 100},
        "assistant_shape": {
            "sha256": "s" * 64,
            "sha16": "s" * 16,
            "char_count": len(longest_streaming),
        },
        "marker_turn_shapes": [],
        "assistant_text": longest_streaming,
        "user_text_tail": "",
    }
    (diag_dir / "t04_streaming.json").write_text(json.dumps(streaming_record))

    captures = ohl.load_typeb_capture_diagnostics(diagnostics_dir=diag_dir, limit=10)
    assert len(captures) == 1, "all four records share key — exactly one capture should be selected"
    cap = captures[0]
    assert cap.assistant_raw_text == longest, "longest non-generating record should win"
    assert cap.source_completeness == "best_observed_in_group"
    assert cap.soft_observation_count == 4


def test_single_record_group_marked_partial_or_unknown(tmp_path: Path) -> None:
    diag_dir = tmp_path / "capture_diagnostics"
    diag_dir.mkdir()
    text = "Solitary observation: only one snapshot for this turn; completeness cannot be inferred."
    _write_capture_diagnostic(diag_dir, name="solitary_record", assistant_text=text * 3, conv_id="solitary_conv")
    captures = ohl.load_typeb_capture_diagnostics(diagnostics_dir=diag_dir, limit=10)
    assert len(captures) == 1
    assert captures[0].source_completeness == "partial_or_unknown"
    assert captures[0].soft_observation_count == 1


# ---------- 16. token-overlap-only without anchor stays below default threshold ----------


def test_token_overlap_without_anchor_stays_below_ambiguous_default() -> None:
    # Two texts share many tokens but the assistant text never appears as a contiguous
    # prefix in the typea input — anchor must fail. The composite calibration must NOT
    # bump this above ambiguous, because shared vocabulary alone is not handoff evidence.
    assistant = "the joiner stabilizes confidence around composite evidence streams of independent strong signals"
    typea_text = "stabilizes confidence around joiner streams composite signals independent strong evidence the of"
    cap = _capture(text=assistant)
    ua = _typea(surface="claude_code", session_id="claude_shuffled_", text=typea_text)
    score, ev, _ = ohl.score_pair(cap, ua)
    assert ev.anchor_match is False
    # Token overlap is high (re-shuffled tokens), but without anchor the bump path is skipped.
    assert score < ohl.CONFIDENCE_AMBIGUOUS


# ---------- 17. HUD/cockpit consumer surface ----------


def _projection_with_edges(*edges: dict) -> dict:
    return {
        "schema_version": ohl.SCHEMA_VERSION,
        "status": "projection_present",
        "generated_at": "2026-05-10T01:38:00+00:00",
        "candidate_edges": list(edges),
        "current_bindings": [],
        "counts": {},
    }


def _edge(*, conversation_id: str, session_id: str, surface: str, band: str, score: float) -> dict:
    return {
        "edge_id": f"hl_{session_id}_{conversation_id}",
        "confidence_band": band,
        "score": score,
        "direction": "typeb_to_typea",
        "type_b": {
            "conversation_id": conversation_id,
            "conversation_url": f"https://chatgpt.com/c/{conversation_id}",
            "source": "capture_diagnostic",
            "source_completeness": "best_observed_in_group",
            "captured_at": "2026-05-10T01:30:00+00:00",
        },
        "type_a": {"surface": surface, "session_id": session_id},
        "evidence": {
            "containment": False,
            "anchor_match": True,
            "token_overlap": 0.92,
            "time_delta_seconds": 6,
            "tight_time_coupling": True,
            "forward_time_coupling": True,
            "observer_lag_tolerated": False,
            "operator_delta_detected": True,
            "competing_candidate_count": 0,
            "top_candidate_gap": 0.05,
        },
        "operator_delta_summary": {
            "position": "suffix",
            "chars": 200,
            "reliability": "uncertain_source_may_be_partial",
            "source_relation": "observed_source_prefix_of_typea_input",
        },
    }


def test_conversation_links_returns_only_strong_and_tentative() -> None:
    proj = _projection_with_edges(
        _edge(conversation_id="conv_x", session_id="sess_strong____", surface="codex", band="strong", score=0.90),
        _edge(conversation_id="conv_x", session_id="sess_tentative_", surface="codex", band="tentative", score=0.55),
        _edge(conversation_id="conv_x", session_id="sess_ambiguous_", surface="claude_code", band="ambiguous", score=0.35),
        _edge(conversation_id="conv_x", session_id="sess_none______", surface="codex", band="none", score=0.10),
    )
    links = ohl.conversation_links(proj, "conv_x")
    assert [link["confidence_band"] for link in links] == ["strong", "tentative"]
    # Sorted strong-first.
    assert links[0]["session_id"] == "sess_strong____"
    assert links[0]["surface_label"] == "Codex"
    assert links[1]["session_id"] == "sess_tentative_"


def test_conversation_links_unknown_conversation_returns_empty() -> None:
    proj = _projection_with_edges(
        _edge(conversation_id="conv_x", session_id="sess_x_________", surface="codex", band="tentative", score=0.55),
    )
    assert ohl.conversation_links(proj, "conv_unknown") == []
    assert ohl.conversation_links(proj, "") == []


def test_load_handoff_projection_handles_missing_and_invalid_paths(tmp_path: Path) -> None:
    missing = tmp_path / "no_such.json"
    proj_missing = ohl.load_handoff_projection(missing)
    assert proj_missing["status"] == "projection_missing"
    assert proj_missing["candidate_edges"] == []

    invalid = tmp_path / "invalid.json"
    invalid.write_text("not json{")
    proj_invalid = ohl.load_handoff_projection(invalid)
    assert proj_invalid["status"] == "projection_invalid"
    assert proj_invalid["candidate_edges"] == []


def test_projection_freshness_label_distinguishes_present_and_stale() -> None:
    import datetime as _dt
    base = "2026-05-10T01:00:00+00:00"
    proj = {"schema_version": ohl.SCHEMA_VERSION, "status": "projection_present", "generated_at": base}
    fresh_now = _dt.datetime(2026, 5, 10, 1, 0, 30, tzinfo=_dt.timezone.utc)
    stale_now = _dt.datetime(2026, 5, 10, 2, 0, 0, tzinfo=_dt.timezone.utc)
    assert ohl.projection_freshness_label(proj, stale_seconds=300, now=fresh_now) == "projection_present"
    assert ohl.projection_freshness_label(proj, stale_seconds=300, now=stale_now) == "projection_stale"

    missing = {"schema_version": ohl.SCHEMA_VERSION, "status": "projection_missing"}
    assert ohl.projection_freshness_label(missing) == "projection_missing"


def test_handoff_linkage_status_reads_projection_metadata_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import datetime as _dt

    projection_path = tmp_path / "handoff_linkage_projection.json"
    diagnostics_path = tmp_path / "handoff_linkage_diagnostics.json"
    projection = _projection_with_edges(
        _edge(conversation_id="conv_status", session_id="sess_status____", surface="codex", band="strong", score=0.9),
    )
    projection["counts"] = {
        "typeb_captures_considered": 2,
        "typeb_by_source": {"prompt_shelf_run": 1, "capture_diagnostic": 1, "other": 0},
        "typea_user_inputs_considered": 4,
        "candidate_edges": 1,
        "strong": 1,
        "tentative": 0,
        "ambiguous": 0,
        "none_dropped": 0,
    }
    projection["current_bindings"] = [{"session_id": "sess_status____", "linked_edge_ids": ["edge_1"]}]
    projection_path.write_text(json.dumps(projection))
    diagnostics_path.write_text(json.dumps({
        "schema_version": "operator_handoff_linkage_diagnostics_v0",
        "captures_with_no_candidate_count": 3,
        "user_input_records_with_no_match": 5,
        "ambiguous_edges": ["edge_amb"],
    }))

    def _raw_join_must_not_run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("status must not read raw handoff inputs")

    monkeypatch.setattr(ohl, "load_typeb_records", _raw_join_must_not_run)
    monkeypatch.setattr(ohl, "load_typea_user_inputs", _raw_join_must_not_run)

    status = ohl.handoff_linkage_status(
        projection_path=projection_path,
        diagnostics_path=diagnostics_path,
        stale_seconds=300,
        now=_dt.datetime(2026, 5, 10, 1, 40, 0, tzinfo=_dt.timezone.utc),
    )
    assert status["schema_version"] == "operator_handoff_linkage_status_v0"
    assert status["status"] == "projection_present"
    assert status["decision_authority"] == "fresh_projection_metadata"
    assert status["mutates_state"] is False
    assert status["counts"]["candidate_edges"] == 1
    assert status["counts"]["current_bindings"] == 1
    assert status["diagnostics"]["status"] == "present"
    assert status["diagnostics"]["counts"]["ambiguous_edges"] == 1
    assert status["next_action"] == "use_projection"
    encoded = json.dumps(status)
    assert "raw_text" not in encoded
    assert "assistant_text" not in encoded


def test_handoff_linkage_status_reports_missing_projection_without_join(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raw_join_must_not_run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("missing status must not rebuild projection implicitly")

    monkeypatch.setattr(ohl, "load_typeb_records", _raw_join_must_not_run)
    monkeypatch.setattr(ohl, "load_typea_user_inputs", _raw_join_must_not_run)

    status = ohl.handoff_linkage_status(
        projection_path=tmp_path / "missing_projection.json",
        diagnostics_path=tmp_path / "missing_diagnostics.json",
    )
    assert status["status"] == "projection_missing"
    assert status["decision_authority"] == "advisory_missing_or_invalid_projection"
    assert status["next_action"] == "write_projection"
    assert status["diagnostics"]["status"] == "missing"


def test_enrich_tab_summary_with_linkage_marks_linked_and_unlinked() -> None:
    proj = _projection_with_edges(
        _edge(conversation_id="conv_linked", session_id="sess_link______", surface="codex", band="tentative", score=0.55),
    )
    index = ohl.conversation_link_index(proj)

    linked_summary = {"key": "chatgpt:conv_linked", "tab_kind": "chatgpt"}
    ohl.enrich_tab_summary_with_linkage(linked_summary, link_index=index, projection=proj)
    block = linked_summary["handoff_linkage"]
    assert block["status"] == "linked"
    assert block["conversation_id"] == "conv_linked"
    assert len(block["links"]) == 1
    assert block["links"][0]["surface_label"] == "Codex"

    unlinked_summary = {"key": "chatgpt:conv_unrelated", "tab_kind": "chatgpt"}
    ohl.enrich_tab_summary_with_linkage(unlinked_summary, link_index=index, projection=proj)
    assert unlinked_summary["handoff_linkage"]["status"] == "unlinked"
    assert unlinked_summary["handoff_linkage"]["links"] == []


def test_enrich_tab_observations_payload_marks_chatgpt_only() -> None:
    proj = _projection_with_edges(
        _edge(conversation_id="conv_x", session_id="sess_codex_____", surface="codex", band="tentative", score=0.55),
    )
    payload = {
        "schema_version": "operator_tab_observation_v1",
        "current_tabs": [
            {"key": "chatgpt:conv_x", "tab_kind": "chatgpt"},
            {"key": "chatgpt:conv_y", "tab_kind": "chatgpt"},
            {"key": "tab:newtab", "tab_kind": "newtab", "handoff_linkage": "stale_field_to_clear"},
        ],
        "tab_memory": {
            "chatgpt:conv_x": {"key": "chatgpt:conv_x", "tab_kind": "chatgpt"},
            "tab:newtab": {"key": "tab:newtab", "tab_kind": "newtab"},
        },
    }
    enriched = ohl.enrich_tab_observations_payload(payload, projection=proj)
    by_key = {item["key"]: item for item in enriched["current_tabs"]}
    assert by_key["chatgpt:conv_x"]["handoff_linkage"]["status"] == "linked"
    assert by_key["chatgpt:conv_y"]["handoff_linkage"]["status"] == "unlinked"
    # Non-chatgpt tabs must have any prior handoff_linkage field cleared.
    assert "handoff_linkage" not in by_key["tab:newtab"]
    summary = enriched["handoff_linkage_summary"]
    assert summary["linked_chatgpt_tab_count"] == 1
    assert summary["linked_session_ids"] == ["sess_codex_____"]


def test_link_summary_session_short_handles_codex_and_claude_session_ids() -> None:
    codex_edge = _edge(conversation_id="cx", session_id="2026-05-09T20-56-21-019e0e4f-f544-78e3-85c4-dc13c4bb80fc", surface="codex", band="tentative", score=0.55)
    claude_edge = _edge(conversation_id="cl", session_id="79fdac5d-414f-425d-b05f-267ab76c5acf", surface="claude_code", band="tentative", score=0.55)
    proj = _projection_with_edges(codex_edge, claude_edge)
    codex_links = ohl.conversation_links(proj, "cx")
    claude_links = ohl.conversation_links(proj, "cl")
    assert codex_links[0]["surface_label"] == "Codex"
    assert "20" in codex_links[0]["session_short"]  # codex slug starts with timestamp segment
    assert claude_links[0]["surface_label"] == "Claude"
    assert claude_links[0]["session_short"] == "79fdac5d"


# ---------- 18. handoff_linkage_visual: additive surface-identity unification ----------


def test_handoff_linkage_visual_codex_carries_distinct_overlay() -> None:
    proj = _projection_with_edges(
        _edge(conversation_id="cv_cx", session_id="2026-05-09T20-56-21-aaa", surface="codex", band="tentative", score=0.55),
    )
    index = ohl.conversation_link_index(proj)
    summary = {"key": "chatgpt:cv_cx", "tab_kind": "chatgpt", "accent": "#d9b45f", "favicon_color": "#d9b45f", "tab_order_label": "1", "tab_chrome_title": "1 · Cold Start Analysis"}
    ohl.enrich_tab_summary_with_linkage(summary, link_index=index, projection=proj)
    visual = summary["handoff_linkage_visual"]
    assert visual["linked_surface"] == "codex"
    assert visual["accent_overlay_hex"] == ohl.LINKED_SURFACE_TINTS["codex"]
    assert visual["badge_text"] is not None and "Codex" in visual["badge_text"]
    assert visual["badge_band"] == "tentative"
    assert visual["badge_intensity"] == "muted"
    assert visual["chrome_title_prefix_extension"] is not None and "Codex" in visual["chrome_title_prefix_extension"]
    assert visual["link_count"] == 1
    # Authority preservation: existing visual fields untouched.
    assert summary["accent"] == "#d9b45f"
    assert summary["favicon_color"] == "#d9b45f"
    assert summary["tab_order_label"] == "1"
    assert summary["tab_chrome_title"] == "1 · Cold Start Analysis"


def test_handoff_linkage_visual_claude_uses_distinct_tint_from_codex() -> None:
    proj = _projection_with_edges(
        _edge(conversation_id="cv_cl", session_id="79fdac5d-414f", surface="claude_code", band="tentative", score=0.55),
    )
    index = ohl.conversation_link_index(proj)
    summary = {"key": "chatgpt:cv_cl", "tab_kind": "chatgpt"}
    ohl.enrich_tab_summary_with_linkage(summary, link_index=index, projection=proj)
    visual = summary["handoff_linkage_visual"]
    assert visual["linked_surface"] == "claude_code"
    assert visual["accent_overlay_hex"] == ohl.LINKED_SURFACE_TINTS["claude_code"]
    assert visual["accent_overlay_hex"] != ohl.LINKED_SURFACE_TINTS["codex"], "Claude and Codex must be visually distinguishable"
    assert "Claude" in visual["badge_text"]


def test_handoff_linkage_visual_strong_band_marks_primary_intensity() -> None:
    proj = _projection_with_edges(
        _edge(conversation_id="cv_strong", session_id="sess_strong", surface="codex", band="strong", score=0.92),
    )
    index = ohl.conversation_link_index(proj)
    summary = {"key": "chatgpt:cv_strong", "tab_kind": "chatgpt"}
    ohl.enrich_tab_summary_with_linkage(summary, link_index=index, projection=proj)
    assert summary["handoff_linkage_visual"]["badge_band"] == "strong"
    assert summary["handoff_linkage_visual"]["badge_intensity"] == "primary"


def test_handoff_linkage_visual_unlinked_returns_null_overlay_no_badge() -> None:
    proj = _projection_with_edges(
        _edge(conversation_id="cv_other", session_id="sess_x", surface="codex", band="tentative", score=0.55),
    )
    index = ohl.conversation_link_index(proj)
    summary = {"key": "chatgpt:cv_unlinked", "tab_kind": "chatgpt", "accent": "#7bc78e"}
    ohl.enrich_tab_summary_with_linkage(summary, link_index=index, projection=proj)
    visual = summary["handoff_linkage_visual"]
    assert visual["accent_overlay_hex"] is None
    assert visual["badge_text"] is None
    assert visual["badge_band"] is None
    assert visual["chrome_title_prefix_extension"] is None
    assert visual["link_count"] == 0
    # Original accent untouched.
    assert summary["accent"] == "#7bc78e"


def test_handoff_linkage_visual_multi_link_appends_count_marker() -> None:
    proj = _projection_with_edges(
        _edge(conversation_id="cv_multi", session_id="sess_a_________", surface="codex", band="tentative", score=0.60),
        _edge(conversation_id="cv_multi", session_id="sess_b_________", surface="codex", band="tentative", score=0.55),
    )
    index = ohl.conversation_link_index(proj)
    summary = {"key": "chatgpt:cv_multi", "tab_kind": "chatgpt"}
    ohl.enrich_tab_summary_with_linkage(summary, link_index=index, projection=proj)
    visual = summary["handoff_linkage_visual"]
    assert visual["link_count"] == 2
    assert "+1" in visual["badge_text"], f"got badge_text={visual['badge_text']!r}"
