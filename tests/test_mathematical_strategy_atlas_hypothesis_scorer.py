from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from microcosm_core.organs.mathematical_strategy_atlas_hypothesis_scorer import (
    CARD_SCHEMA_VERSION,
    EXPECTED_NEGATIVE_CASES,
    PUBLIC_SAFE_BODY_CLASSES,
    SOURCE_STRATEGY_CARDS_REF,
    SOURCE_STRATEGY_HYPOTHESIS_SET_REF,
    SOURCE_PATTERN_IDS,
    SOURCE_REFS,
    _line_count,
    _sha256,
    main,
    run,
    run_strategy_bundle,
    validate_source_module_imports,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = (
    MICROCOSM_ROOT
    / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input"
)
EXPORTED_BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/mathematical_strategy_atlas_hypothesis_scorer/exported_mathematical_strategy_atlas_bundle"
)
SOURCE_ARTIFACT_REFS = SOURCE_REFS


def _walk_keys(payload: Any) -> list[str]:
    if isinstance(payload, dict):
        keys = list(payload)
        for value in payload.values():
            keys.extend(_walk_keys(value))
        return keys
    if isinstance(payload, list):
        keys: list[str] = []
        for item in payload:
            keys.extend(_walk_keys(item))
        return keys
    return []


def test_mathematical_strategy_line_count_streams_without_full_text_read(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source = tmp_path / "strategy_source.py"
    empty_source = tmp_path / "empty_strategy_source.py"
    source.write_text("one\n\ntwo\n", encoding="utf-8")
    empty_source.write_text("", encoding="utf-8")
    guarded_paths = {source, empty_source}
    original_read_text = Path.read_text

    def guarded_read_text(self: Path, *args: Any, **kwargs: Any) -> str:
        if self in guarded_paths:
            raise AssertionError("line count should stream source-module input")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert _line_count(source) == 3
    assert _line_count(empty_source) == 1


def test_mathematical_strategy_source_module_metadata_streams_without_read_bytes(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    input_dir = tmp_path / "bundle"
    target = input_dir / "source_artifacts/example.py"
    target.parent.mkdir(parents=True)
    body = b"def strategy_anchor():\n    return 'public'\n"
    target.write_bytes(body)
    expected_digest = "sha256:" + hashlib.sha256(body).hexdigest()
    (input_dir / "source_module_manifest.json").write_text(
        json.dumps(
            {
                "source_import_class": "copied_non_secret_macro_body",
                "body_in_receipt": False,
                "modules": [
                    {
                        "module_id": "example_strategy_source",
                        "path": "source_artifacts/example.py",
                        "source_ref": "tools/meta/factory/example.py",
                        "source_import_class": "copied_non_secret_macro_body",
                        "material_class": sorted(PUBLIC_SAFE_BODY_CLASSES)[0],
                        "sha256": expected_digest,
                        "byte_count": len(body),
                        "line_count": 2,
                        "required_anchors": ["strategy_anchor"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    guarded_paths = {target}
    original_read_bytes = Path.read_bytes

    def fail_read_bytes(self: Path, *args: Any, **kwargs: Any) -> bytes:
        if self in guarded_paths:
            raise AssertionError("source-module metadata should stream bytes")
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", fail_read_bytes)

    result = validate_source_module_imports(
        input_dir,
        required=True,
        public_root=tmp_path,
    )

    assert _sha256(target) == expected_digest
    assert result["source_modules_pass"] is True
    assert result["source_module_import_count"] == 1
    import_row = result["source_module_imports"][0]
    assert import_row["target_sha256"] == expected_digest
    assert import_row["target_byte_count"] == len(body)
    assert import_row["missing_required_anchors"] == []


def test_mathematical_strategy_atlas_scorer_covers_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts",
        command="pytest",
        acceptance_out=tmp_path / "acceptance.json",
    )

    assert result["status"] == "pass"
    assert result["source_pattern_ids"] == SOURCE_PATTERN_IDS
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["strategy_count"] == 7
    assert result["problem_count"] == 5
    assert result["hypothesis_case_count"] == 5
    assert result["selected_strategy_ids"] == [
        "iff_split",
        "recursive_data_induction",
        "symmetry_or_orientation",
        "unknown",
    ]
    scored_by_id = {row["case_id"]: row for row in result["scored_cases"]}
    orientation = scored_by_id["prefer_orientation_over_superficial_overlap"]
    assert orientation["selected_strategy_id"] == "symmetry_or_orientation"
    assert orientation["score"] == 14
    assert orientation["feature_overlap_count"] == 3
    equality_candidate = next(
        row
        for row in orientation["candidate_scores"]
        if row["strategy_id"] == "equality_normal_form"
    )
    assert equality_candidate["score"] == 10
    assert equality_candidate["feature_overlap_count"] == 4
    assert equality_candidate["negative_trigger_hits"] == ["reversed_orientation"]

    retrieval_ceiling = scored_by_id["cap_retrieval_bonus_under_trigger_match"]
    assert retrieval_ceiling["selected_strategy_id"] == "iff_split"
    sponge_candidate = next(
        row
        for row in retrieval_ceiling["candidate_scores"]
        if row["strategy_id"] == "retrieval_keyword_sponge"
    )
    assert sponge_candidate["retrieval_bonus"] == 2
    assert len(sponge_candidate["retrieval_term_hits"]) > 2
    assert sponge_candidate["score"] == 2
    assert retrieval_ceiling["score"] == 14

    unknown_case = scored_by_id["typed_unknown_strategy_miss"]
    assert unknown_case["selected_strategy_id"] == "unknown"
    assert unknown_case["score"] == 0
    assert result["strategy_selection_miss_case_ids"] == ["typed_unknown_strategy_miss"]
    assert result["all_expectations_met"] is True
    assert result["strategy_board"]["public_contract"]["strategy_selected_pre_oracle"] is True
    assert result["strategy_board"]["public_contract"]["weighted_trigger_scoring"] is True
    assert result["strategy_board"]["public_contract"]["negative_triggers_penalized"] is True
    assert result["strategy_board"]["public_contract"]["retrieval_bonus_capped"] is True
    assert (
        result["strategy_board"]["public_contract"]["drilldown_regression_not_product_organ"]
        is True
    )
    assert result["source_module_import_count"] == len(SOURCE_ARTIFACT_REFS)
    assert result["copied_source_artifact_count"] == len(SOURCE_ARTIFACT_REFS)
    assert result["source_modules_pass"] is True
    assert result["source_artifact_consistency_pass"] is True
    assert result["source_strategy_card_count"] == 8
    assert result["source_strategy_hypothesis_count"] == 3
    assert result["source_skill_cell_count"] == 4
    assert result["selected_source_hypothesis_id"] == "constructor_injectivity"
    assert result["overlapping_source_strategy_ids"] == [
        "equality_normal_form",
        "iff_split",
        "recursive_data_induction",
        "symmetry_or_orientation",
    ]
    assert result["strategy_board"]["source_body_import_projection"][
        "copied_source_artifact_count"
    ] == len(SOURCE_ARTIFACT_REFS)
    assert result["strategy_board"]["source_artifact_consistency_projection"][
        "source_artifact_consistency_pass"
    ] is True
    assert result["authority_ceiling"]["oracle_label_visibility_authorized"] is False
    assert result["scoring_derivation"] == {
        "status": "recomputed_from_problem_and_strategy_evidence",
        "authoritative_input_fields": [
            "problem_features.problems[].feature_tags",
            "problem_features.problems[].retrieval_query_terms",
            "hypothesis_cases.cases[].candidate_strategy_ids",
            "hypothesis_cases.cases[].retrieval_query_terms",
            "strategy_atlas.strategies[].trigger_features",
            "strategy_atlas.strategies[].negative_triggers",
            "strategy_atlas.strategies[].retrieval_expansion_terms",
        ],
        "input_strategy_card_validation_pass": True,
        "declared_outcome_checked_fields": [],
        "declared_case_count": 0,
        "declared_outcome_mismatch_count": 0,
        "declared_outcome_verification_pass": True,
    }
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_mathematical_strategy_atlas_recomputes_when_problem_features_change_and_rejects_stale_declared_verdict(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    problem_features_path = input_dir / "problem_features.json"
    problem_features = json.loads(problem_features_path.read_text(encoding="utf-8"))
    for problem in problem_features["problems"]:
        if problem["problem_id"] == "toy_reversed_length_append":
            problem["feature_tags"] = [
                "equality_target",
                "nat_add",
                "length_append",
                "direct_orientation",
            ]
            break
    else:
        raise AssertionError("toy_reversed_length_append fixture problem missing")
    problem_features_path.write_text(
        json.dumps(problem_features, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    cases_path = input_dir / "hypothesis_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    for case in cases["cases"]:
        if case["case_id"] == "prefer_orientation_over_superficial_overlap":
            case["selected_strategy_id"] = "symmetry_or_orientation"
            case["score"] = 14
            case["classifier"] = "matched_strategy"
            case["candidate_scores"] = [
                {"strategy_id": "symmetry_or_orientation", "score": 14},
                {"strategy_id": "equality_normal_form", "score": 10},
                {"strategy_id": "arithmetic_normalization", "score": 0},
            ]
            break
    else:
        raise AssertionError("prefer_orientation_over_superficial_overlap missing")
    cases_path.write_text(
        json.dumps(cases, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(input_dir, public_root / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert result["all_expectations_met"] is False
    assert result["scoring_derivation"]["declared_case_count"] == 1
    assert result["scoring_derivation"]["declared_outcome_verification_pass"] is False
    assert result["scoring_derivation"]["declared_outcome_mismatch_count"] == 3
    assert result["scoring_derivation"]["declared_outcome_checked_fields"] == [
        "candidate_scores",
        "classifier",
        "score",
        "selected_strategy_id",
    ]
    assert {
        "MATH_STRATEGY_DECLARED_SELECTION_STALE",
        "MATH_STRATEGY_DECLARED_SCORE_STALE",
        "MATH_STRATEGY_DECLARED_RANKING_STALE",
    } <= set(result["error_codes"])
    scored_by_id = {row["case_id"]: row for row in result["scored_cases"]}
    mutated_case = scored_by_id["prefer_orientation_over_superficial_overlap"]
    assert mutated_case["expected_strategy_id"] == "symmetry_or_orientation"
    assert mutated_case["selected_strategy_id"] == "equality_normal_form"
    assert mutated_case["score"] == 13
    assert mutated_case["declared_outcome_status"] == (
        "declared_outcomes_contradict_recomputed_evidence"
    )
    assert {row["field"] for row in mutated_case["declared_outcome_mismatches"]} == {
        "candidate_scores",
        "score",
        "selected_strategy_id",
    }
    candidate_scores = {
        row["strategy_id"]: row for row in mutated_case["candidate_scores"]
    }
    assert candidate_scores["equality_normal_form"]["trigger_feature_hits"] == [
        "equality_target",
        "length_append",
        "nat_add",
    ]
    assert candidate_scores["equality_normal_form"]["negative_trigger_hits"] == []
    assert candidate_scores["symmetry_or_orientation"]["score"] == 3
    assert candidate_scores["symmetry_or_orientation"]["negative_trigger_hits"] == [
        "direct_orientation"
    ]


def test_mathematical_strategy_atlas_recomputes_when_strategy_evidence_changes(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    strategy_atlas_path = input_dir / "strategy_atlas.json"
    strategy_atlas = json.loads(strategy_atlas_path.read_text(encoding="utf-8"))
    for strategy in strategy_atlas["strategies"]:
        if strategy["strategy_id"] == "symmetry_or_orientation":
            strategy["trigger_features"] = ["symmetry_needed"]
            break
    else:
        raise AssertionError("symmetry_or_orientation strategy missing")
    strategy_atlas_path.write_text(
        json.dumps(strategy_atlas, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(input_dir, public_root / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert result["all_expectations_met"] is False
    assert result["scoring_derivation"]["declared_outcome_verification_pass"] is True
    scored_by_id = {row["case_id"]: row for row in result["scored_cases"]}
    mutated_case = scored_by_id["prefer_orientation_over_superficial_overlap"]
    assert mutated_case["expected_strategy_id"] == "symmetry_or_orientation"
    assert mutated_case["selected_strategy_id"] == "equality_normal_form"
    assert mutated_case["score"] == 10
    assert [
        row["strategy_id"] for row in mutated_case["candidate_scores"]
    ] == [
        "equality_normal_form",
        "symmetry_or_orientation",
        "arithmetic_normalization",
    ]
    assert mutated_case["candidate_scores"][1]["score"] == 6
    assert mutated_case["declared_outcome_status"] == "no_declared_outcomes_present"


def test_mathematical_strategy_atlas_rejects_label_only_strategy_card_input(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    strategy_atlas_path = input_dir / "strategy_atlas.json"
    strategy_atlas = json.loads(strategy_atlas_path.read_text(encoding="utf-8"))
    for strategy in strategy_atlas["strategies"]:
        if strategy["strategy_id"] == "symmetry_or_orientation":
            strategy.clear()
            strategy.update(
                {
                    "strategy_id": "symmetry_or_orientation",
                    "title": "Symmetry or orientation",
                    "body_redacted": True,
                    "authority_boundary": "pre_oracle_strategy_hypothesis_only",
                }
            )
            break
    else:
        raise AssertionError("symmetry_or_orientation strategy missing")
    strategy_atlas_path.write_text(
        json.dumps(strategy_atlas, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(input_dir, public_root / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert result["scoring_derivation"]["input_strategy_card_validation_pass"] is False
    assert "MATH_STRATEGY_RICH_CARD_FIELDS_REQUIRED" in result["error_codes"]


def test_mathematical_strategy_atlas_rejects_label_only_declared_selection(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    cases_path = input_dir / "hypothesis_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    for case in cases["cases"]:
        if case["case_id"] == "prefer_orientation_over_superficial_overlap":
            case["selected_strategy_id"] = "symmetry_or_orientation"
            break
    else:
        raise AssertionError("prefer_orientation_over_superficial_overlap missing")
    cases_path.write_text(
        json.dumps(cases, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(input_dir, public_root / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert result["scoring_derivation"]["declared_case_count"] == 1
    assert result["scoring_derivation"]["declared_outcome_verification_pass"] is False
    assert result["scoring_derivation"]["declared_outcome_mismatch_count"] == 0
    assert result["scoring_derivation"]["declared_outcome_checked_fields"] == [
        "selected_strategy_id"
    ]
    assert (
        "MATH_STRATEGY_DECLARED_SELECTION_LABEL_ONLY_FORBIDDEN"
        in result["error_codes"]
    )
    scored_by_id = {row["case_id"]: row for row in result["scored_cases"]}
    stale_case = scored_by_id["prefer_orientation_over_superficial_overlap"]
    assert stale_case["declared_outcome_status"] == (
        "declared_selection_label_only_forbidden"
    )
    assert stale_case["declared_selection_label_only"] is True
    assert stale_case["declared_outcome_mismatches"] == []


def test_mathematical_strategy_atlas_rejects_stale_declared_outcomes(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    input_dir = (
        public_root
        / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input"
    )
    shutil.copytree(FIXTURE_INPUT, input_dir)
    cases_path = input_dir / "hypothesis_cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    for case in cases["cases"]:
        if case["case_id"] == "prefer_orientation_over_superficial_overlap":
            case["selected_strategy_id"] = "equality_normal_form"
            case["score"] = 10
            case["classifier"] = "STRATEGY_SELECTION_MISS"
            case["candidate_scores"] = [
                {"strategy_id": "equality_normal_form", "score": 10},
                {"strategy_id": "symmetry_or_orientation", "score": 14},
                {"strategy_id": "arithmetic_normalization", "score": 0},
            ]
            break
    else:
        raise AssertionError("prefer_orientation_over_superficial_overlap missing")
    cases_path.write_text(
        json.dumps(cases, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run(input_dir, public_root / "receipts", command="pytest")

    assert result["status"] == "blocked"
    assert result["scoring_derivation"]["declared_case_count"] == 1
    assert result["scoring_derivation"]["declared_outcome_verification_pass"] is False
    assert result["scoring_derivation"]["declared_outcome_mismatch_count"] == 4
    assert result["scoring_derivation"]["declared_outcome_checked_fields"] == [
        "candidate_scores",
        "classifier",
        "score",
        "selected_strategy_id",
    ]
    assert {
        "MATH_STRATEGY_DECLARED_SELECTION_STALE",
        "MATH_STRATEGY_DECLARED_SCORE_STALE",
        "MATH_STRATEGY_DECLARED_VERDICT_STALE",
        "MATH_STRATEGY_DECLARED_RANKING_STALE",
    } <= set(result["error_codes"])
    scored_by_id = {row["case_id"]: row for row in result["scored_cases"]}
    stale_case = scored_by_id["prefer_orientation_over_superficial_overlap"]
    assert stale_case["declared_outcome_status"] == (
        "declared_outcomes_contradict_recomputed_evidence"
    )
    assert stale_case["declared_outcome_fields_present"] == [
        "selected_strategy_id",
        "score",
        "classifier",
        "candidate_scores",
    ]
    assert {row["field"] for row in stale_case["declared_outcome_mismatches"]} == {
        "candidate_scores",
        "classifier",
        "score",
        "selected_strategy_id",
    }


def test_mathematical_strategy_atlas_scorer_accepts_exported_bundle(
    tmp_path: Path,
) -> None:
    result = run_strategy_bundle(
        EXPORTED_BUNDLE_INPUT,
        tmp_path / "receipts",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_mathematical_strategy_atlas_bundle"
    assert result["bundle_id"] == "mathematical_strategy_atlas_runtime_example"
    assert result["observed_negative_cases"] == {}
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["strategy_selection_miss_case_ids"] == ["typed_unknown_strategy_miss"]
    assert result["body_material_status"] == (
        "copied_non_secret_macro_strategy_atlas_body_floor_with_provenance"
    )
    assert (
        result["source_module_import_status"]
        == "copied_strategy_atlas_macro_body_floor_verified"
    )
    assert result["source_module_import_count"] == len(SOURCE_ARTIFACT_REFS)
    assert result["copied_source_artifact_count"] == len(SOURCE_ARTIFACT_REFS)
    assert result["source_modules_pass"] is True
    assert result["source_artifact_consistency_pass"] is True
    assert result["source_strategy_card_count"] == 8
    assert result["source_strategy_hypothesis_count"] == 3
    assert result["source_skill_cell_count"] == 4
    assert all(row["exists"] is True for row in result["source_module_imports"])
    assert all(row["digest_match"] is True for row in result["source_module_imports"])
    assert all(
        row["missing_required_anchors"] == []
        for row in result["source_module_imports"]
    )
    assert result["strategy_board"]["source_body_import_projection"][
        "copied_source_artifact_count"
    ] == len(SOURCE_ARTIFACT_REFS)
    assert result["receipt_paths"] == [
        "receipts/exported_mathematical_strategy_atlas_bundle_validation_result.json"
    ]


def test_mathematical_strategy_atlas_rejects_source_module_digest_mismatch(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/mathematical_strategy_atlas_hypothesis_scorer/"
        "exported_mathematical_strategy_atlas_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE_INPUT, bundle)
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mutated_module_id = manifest["modules"][0]["module_id"]
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_strategy_bundle(
        bundle,
        public_root / "receipts/mathematical_strategy_atlas_hypothesis_scorer",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_modules_pass"] is False
    assert "MATH_STRATEGY_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    mismatches = [
        row for row in result["source_module_imports"] if row["digest_match"] is False
    ]
    assert [row["module_id"] for row in mismatches] == [mutated_module_id]
    assert result["copied_source_artifact_count"] == len(SOURCE_ARTIFACT_REFS) - 1
    assert result["private_state_scan"]["blocking_hit_count"] == 0


def _bundle_copy_with_core(tmp_path: Path) -> tuple[Path, Path]:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    bundle = (
        public_root
        / "examples/mathematical_strategy_atlas_hypothesis_scorer/"
        "exported_mathematical_strategy_atlas_bundle"
    )
    shutil.copytree(EXPORTED_BUNDLE_INPUT, bundle)
    return public_root, bundle


def _source_artifact_path(bundle: Path, source_ref: str) -> Path:
    manifest = json.loads(
        (bundle / "source_module_manifest.json").read_text(encoding="utf-8")
    )
    row = next(row for row in manifest["modules"] if row["source_ref"] == source_ref)
    return bundle / row["path"]


def test_mathematical_strategy_atlas_rejects_disconnected_source_card(
    tmp_path: Path,
) -> None:
    public_root, bundle = _bundle_copy_with_core(tmp_path)
    cards_path = _source_artifact_path(bundle, SOURCE_STRATEGY_CARDS_REF)
    cards = json.loads(cards_path.read_text(encoding="utf-8"))
    for card in cards["cards"]:
        if card["strategy_id"] == "symmetry_or_orientation":
            card["mathematical_lens"] = "Decorative disconnected label."
            card["retrieval_expansion_terms"] = ["decorative-disconnected-token"]
            card["lean_tactic_affordances"] = ["decorative-placeholder"]
    cards_path.write_text(
        json.dumps(cards, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_strategy_bundle(
        bundle,
        public_root / "receipts/mathematical_strategy_atlas_hypothesis_scorer",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_artifact_consistency_pass"] is False
    assert "MATH_STRATEGY_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert "MATH_STRATEGY_SOURCE_CARD_ATLAS_DISCONNECTED" in result["error_codes"]
    disconnected = [
        finding
        for finding in result["findings"]
        if finding["error_code"] == "MATH_STRATEGY_SOURCE_CARD_ATLAS_DISCONNECTED"
    ]
    assert disconnected[0]["subject_id"] == "symmetry_or_orientation"


def test_mathematical_strategy_atlas_rejects_inconsistent_source_hypothesis_set(
    tmp_path: Path,
) -> None:
    public_root, bundle = _bundle_copy_with_core(tmp_path)
    hypothesis_path = _source_artifact_path(bundle, SOURCE_STRATEGY_HYPOTHESIS_SET_REF)
    hypothesis = json.loads(hypothesis_path.read_text(encoding="utf-8"))
    hypothesis["selected_strategy_id"] = "decorative_missing_strategy"
    hypothesis_path.write_text(
        json.dumps(hypothesis, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_strategy_bundle(
        bundle,
        public_root / "receipts/mathematical_strategy_atlas_hypothesis_scorer",
        command="pytest",
    )

    assert result["status"] == "blocked"
    assert result["source_artifact_consistency_pass"] is False
    assert "MATH_STRATEGY_SOURCE_MODULE_DIGEST_MISMATCH" in result["error_codes"]
    assert (
        "MATH_STRATEGY_SOURCE_HYPOTHESIS_SELECTED_ID_NOT_IN_SET"
        in result["error_codes"]
    )


def test_mathematical_strategy_atlas_bundle_card_is_compact(
    tmp_path: Path,
    capsys,
) -> None:
    exit_code = main(
        [
            "run-strategy-bundle",
            "--input",
            str(EXPORTED_BUNDLE_INPUT),
            "--out",
            str(tmp_path / "receipts"),
            "--card",
        ]
    )

    assert exit_code == 0
    stdout = capsys.readouterr().out
    assert len(stdout.encode("utf-8")) < 6000
    payload = json.loads(stdout)
    assert payload["schema_version"] == CARD_SCHEMA_VERSION
    assert payload["status"] == "pass"
    assert payload["organ_id"] == "mathematical_strategy_atlas_hypothesis_scorer"
    assert payload["counts"]["strategy_count"] == 7
    assert payload["counts"]["hypothesis_case_count"] == 5
    assert payload["counts"]["source_module_import_count"] == len(
        SOURCE_ARTIFACT_REFS
    )
    assert payload["strategy_projection"]["selected_strategy_ids"] == [
        "iff_split",
        "recursive_data_induction",
        "symmetry_or_orientation",
        "unknown",
    ]
    assert payload["strategy_projection"]["scoring_model"] == {
        "model_id": "weighted_trigger_negative_retrieval_v1",
        "trigger_feature_weight": 4,
        "negative_trigger_penalty": 3,
        "retrieval_term_bonus": 1,
        "retrieval_bonus_cap": 2,
        "feature_overlap_is_diagnostic_only": True,
    }
    assert payload["strategy_projection"]["strategy_selection_miss_case_ids"] == [
        "typed_unknown_strategy_miss"
    ]
    assert payload["scoring_derivation"] == {
        "status": "recomputed_from_problem_and_strategy_evidence",
        "authoritative_input_field_count": 7,
        "input_strategy_card_validation_pass": True,
        "declared_case_count": 0,
        "declared_checked_field_count": 0,
        "declared_outcome_mismatch_count": 0,
        "declared_outcome_verification_pass": True,
    }
    assert payload["source_module_import"]["source_modules_pass"] is True
    assert payload["source_module_import"]["digest_match_count"] == len(
        SOURCE_ARTIFACT_REFS
    )
    assert payload["source_artifact_consistency"]["pass"] is True
    assert payload["source_artifact_consistency"]["source_strategy_card_count"] == 8
    assert payload["source_artifact_consistency"]["overlap_count"] == 4
    assert payload["private_state_scan"]["blocking_hit_count"] == 0
    assert payload["authority_ceiling"]["provider_calls_authorized"] is False
    assert payload["output_economy"]["stdout_mode"] == "card"
    assert payload["output_economy"]["full_receipt_written"] is True
    assert "scored_cases" not in payload
    assert "strategy_board" not in payload
    assert "source_module_imports" not in payload
    assert "scan_scope" not in payload["private_state_scan"]


def _assert_source_manifest_exact_copies(input_dir: Path) -> None:
    manifest = json.loads(
        (input_dir / "source_module_manifest.json").read_text(encoding="utf-8")
    )
    modules = {row["source_ref"]: row for row in manifest["modules"]}
    assert sorted(modules) == sorted(SOURCE_ARTIFACT_REFS)
    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["body_in_receipt"] is False

    for source_ref in SOURCE_ARTIFACT_REFS:
        source = MICROCOSM_ROOT.parent / source_ref
        target = input_dir / "source_artifacts" / source_ref
        assert target.is_file()
        source_bytes = source.read_bytes()
        target_bytes = target.read_bytes()
        digest = "sha256:" + hashlib.sha256(source_bytes).hexdigest()
        assert source_bytes == target_bytes
        assert modules[source_ref]["sha256"] == digest
        assert modules[source_ref]["byte_count"] == len(source_bytes)
        assert modules[source_ref]["line_count"] == len(
            source.read_text(encoding="utf-8").splitlines()
        )
        assert modules[source_ref]["body_in_receipt"] is False
        assert modules[source_ref]["required_anchors"]
        assert all(
            anchor in target.read_text(encoding="utf-8")
            for anchor in modules[source_ref]["required_anchors"]
        )


def test_mathematical_strategy_atlas_exported_source_modules_are_exact_copies() -> None:
    _assert_source_manifest_exact_copies(EXPORTED_BUNDLE_INPUT)

    bundle_manifest = json.loads(
        (EXPORTED_BUNDLE_INPUT / "bundle_manifest.json").read_text(encoding="utf-8")
    )
    assert bundle_manifest["source_module_manifest_ref"] == "source_module_manifest.json"
    assert len(bundle_manifest["copied_macro_body_artifacts"]) == len(
        SOURCE_ARTIFACT_REFS
    )


def test_mathematical_strategy_atlas_fixture_source_modules_are_exact_copies() -> None:
    _assert_source_manifest_exact_copies(FIXTURE_INPUT)


def test_mathematical_strategy_atlas_exported_bundle_receipt_omits_source_bodies(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "examples/mathematical_strategy_atlas_hypothesis_scorer",
        public_root / "examples/mathematical_strategy_atlas_hypothesis_scorer",
    )

    result = run_strategy_bundle(
        public_root
        / "examples/mathematical_strategy_atlas_hypothesis_scorer/exported_mathematical_strategy_atlas_bundle",
        public_root / "receipts/mathematical_strategy_atlas_hypothesis_scorer",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "def _strategy_cards" not in text
        assert "def _provider_value" not in text
        assert "test_strategy_classification_reducer_accepts_valid_advisory" not in text
        assert "prover_skill_foundry_candidate_atlas_v0" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["source_module_import_count"] == len(SOURCE_ARTIFACT_REFS)
        assert payload["copied_source_artifact_count"] == len(SOURCE_ARTIFACT_REFS)
        assert payload["source_modules_pass"] is True
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)


def test_mathematical_strategy_atlas_receipts_are_redacted_and_public_relative(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer",
        public_root / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer",
    )

    result = run(
        public_root / "fixtures/first_wave/mathematical_strategy_atlas_hypothesis_scorer/input",
        public_root / "receipts/first_wave/mathematical_strategy_atlas_hypothesis_scorer",
        command="pytest",
    )

    assert result["status"] == "pass"
    for receipt_ref in result["receipt_paths"]:
        receipt_file = public_root / receipt_ref
        assert receipt_file.is_file()
        text = receipt_file.read_text(encoding="utf-8")
        assert str(public_root) not in text
        assert "/Users/" not in text
        assert "src/ai_workflow" not in text
        assert "matched_excerpt" not in text
        assert "synthetic forbidden proof material" not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["private_state_scan"]["body_redacted"] is True
        assert payload["authority_ceiling"]["oracle_label_visibility_authorized"] is False
        assert "matched_excerpt" not in _walk_keys(payload)
        assert "body" not in _walk_keys(payload)
