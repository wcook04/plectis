from __future__ import annotations

import json
import shutil
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

import microcosm_core.organs.formal_math_premise_retrieval as premise_module
from microcosm_core.organs.formal_math_premise_retrieval import (
    EXPECTED_NEGATIVE_CASES,
    run,
    run_retrieval_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_INPUT = MICROCOSM_ROOT / "fixtures/first_wave/formal_math_premise_retrieval/input"
BUNDLE_INPUT = (
    MICROCOSM_ROOT
    / "examples/formal_math_premise_retrieval/exported_premise_retrieval_bundle"
)


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


def test_formal_math_premise_retrieval_observes_negative_cases(
    tmp_path: Path,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / "receipts/first_wave/formal_math_premise_retrieval",
        command="pytest",
        acceptance_out=tmp_path
        / "receipts/acceptance/first_wave/formal_math_premise_retrieval_fixture_acceptance.json",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["premise_count"] == 11
    assert result["query_count"] == 4
    assert result["recipe_count"] == 3
    assert result["strategy_case_count"] == 4
    assert result["mean_public_retrieval_recall"] == 1.0
    assert result["body_copied_material_count"] == 6
    assert result["authority_ceiling"]["lean_lake_execution_authorized"] is False
    assert result["authority_ceiling"]["proof_bodies_allowed"] is False
    for codes in EXPECTED_NEGATIVE_CASES.values():
        for code in codes:
            assert code in result["error_codes"]


def test_formal_math_premise_retrieval_receipts_are_public_relative_and_secret_scanned(
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / "fixtures/first_wave/formal_math_premise_retrieval",
        public_root / "fixtures/first_wave/formal_math_premise_retrieval",
    )

    result = run(
        public_root / "fixtures/first_wave/formal_math_premise_retrieval/input",
        public_root / "receipts/first_wave/formal_math_premise_retrieval",
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
        assert "synthetic forbidden proof payload" not in text
        assert '"proof_body":' not in text
        payload = json.loads(text)
        assert payload["status"] == "pass"
        assert payload["secret_exclusion_scan"]["blocking_hit_count"] == 0
        assert payload["secret_exclusion_scan"]["body_material_status"] == (
            "secret_exclusion_scan_no_payload_body_export"
        )
        assert payload["body_material_status"] == (
            "copied_non_secret_macro_body_with_provenance"
        )
        assert "body_redacted" not in _walk_keys(payload)
        assert "private_state_scan" not in payload
        assert "proof_body" not in _walk_keys(payload)


def test_formal_math_premise_retrieval_exported_bundle_validates_runtime_shape(
    tmp_path: Path,
) -> None:
    result = run_retrieval_bundle(
        BUNDLE_INPUT,
        tmp_path / "receipts/runtime_shell/demo_project/organs/formal_math_premise_retrieval",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == "exported_premise_retrieval_bundle"
    assert result["bundle_id"] == "formal_math_premise_retrieval_runtime_example"
    assert result["expected_negative_cases"] == []
    assert result["missing_negative_cases"] == []
    assert result["error_codes"] == []
    assert result["premise_count"] == 11
    assert result["query_count"] == 4
    assert result["mean_public_retrieval_recall"] == 1.0
    assert result["body_copied_material_count"] == 6
    assert result["premise_retrieval_board"]["formal_proof_authority"] is False
    assert result["secret_exclusion_scan"]["scanned_path_count"] == 11


def test_formal_math_premise_retrieval_cli_card_compacts_exported_bundle(
    tmp_path: Path,
    capsys: Any,
) -> None:
    status = premise_module.main(
        [
            "run-retrieval-bundle",
            "--input",
            str(BUNDLE_INPUT),
            "--out",
            str(tmp_path / "receipts/runtime_shell/demo_project/organs/formal_math_premise_retrieval"),
            "--card",
        ]
    )

    output = capsys.readouterr().out
    payload = json.loads(output)

    assert status == 0
    assert len(output.encode("utf-8")) < 3600
    assert payload["schema_version"] == "formal_math_premise_retrieval_card_v1"
    assert payload["status"] == "pass"
    assert payload["card_id"] == "formal_math_premise_retrieval_bundle_card"
    assert payload["output_profile"] == "compact_card_no_retrieval_rows"
    assert payload["input_mode"] == "exported_premise_retrieval_bundle"
    assert payload["receipt_paths"]
    assert payload["receipt_reused"] is False
    assert payload["freshness_status"] == "current"
    assert payload["freshness_digest"].startswith("sha256:")
    assert payload["secret_exclusion_scan_summary"]["scanned_path_count"] == 11
    assert payload["secret_exclusion_scan_summary"]["blocking_hit_count"] == 0
    assert payload["secret_exclusion_scan_summary"]["body_text_exported"] is False
    assert payload["premise_count"] == 11
    assert payload["query_count"] == 4
    assert payload["mean_public_retrieval_recall"] == 1.0
    assert payload["retrieval_rows_omitted"] is True
    assert payload["source_refs_exported"] is False
    assert payload["proof_bodies_exported"] is False
    assert "retrievals" not in payload
    assert "copied_material" not in payload
    assert "source_refs" not in payload
    assert "retrievals" in payload["omitted_full_payload_keys"]
    assert "freshness_basis" in payload["omitted_full_payload_keys"]


def test_formal_math_premise_retrieval_bundle_card_reuses_fresh_receipt(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    out_dir = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/formal_math_premise_retrieval"
    )

    result = run_retrieval_bundle(
        BUNDLE_INPUT,
        out_dir,
        command="pytest --card",
        reuse_fresh_receipt=True,
    )
    card = premise_module._result_card(result)

    assert result["status"] == "pass"
    assert result["receipt_reused"] is False
    assert result["card_schema_version"] == "formal_math_premise_retrieval_card_v1"
    assert result["freshness_digest"].startswith("sha256:")
    assert card["receipt_reused"] is False
    assert card["freshness_digest"] == result["freshness_digest"]
    assert card["premise_count"] == 11
    assert card["query_count"] == 4
    assert card["secret_exclusion_scan_summary"]["scanned_path_count"] == 11
    assert "retrievals" in card["omitted_full_payload_keys"]
    assert "freshness_basis" in card["omitted_full_payload_keys"]
    assert "retrievals" not in card
    assert "secret_exclusion_scan" not in card
    assert str(tmp_path) not in json.dumps(card, sort_keys=True)

    def fail_if_rebuilt(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise AssertionError("fresh card path should reuse the premise retrieval receipt")

    monkeypatch.setattr(premise_module, "_build_result", fail_if_rebuilt)

    cached = run_retrieval_bundle(
        BUNDLE_INPUT,
        out_dir,
        command="pytest --card",
        reuse_fresh_receipt=True,
    )
    cached_card = premise_module._result_card(cached)

    assert cached["status"] == "pass"
    assert cached["receipt_reused"] is True
    assert cached["freshness_digest"] == result["freshness_digest"]
    assert cached_card["receipt_reused"] is True
    assert cached_card["premise_count"] == 11


def test_formal_math_premise_retrieval_fresh_receipt_rejects_duplicate_json_keys(
    tmp_path: Path,
) -> None:
    out_dir = (
        tmp_path
        / "receipts/runtime_shell/demo_project/organs/formal_math_premise_retrieval"
    )
    out_dir.mkdir(parents=True)
    freshness_digest = "sha256:duplicate-key-cache"
    (out_dir / premise_module.BUNDLE_RESULT_NAME).write_text(
        (
            '{"card_schema_version":"poisoned",'
            f'"card_schema_version":"{premise_module.CARD_SCHEMA_VERSION}",'
            f'"organ_id":"{premise_module.ORGAN_ID}",'
            '"input_mode":"exported_premise_retrieval_bundle",'
            f'"freshness_digest":"{freshness_digest}"'
            "}"
        ),
        encoding="utf-8",
    )

    assert (
        premise_module._fresh_retrieval_bundle_receipt(
            out_dir,
            freshness_digest=freshness_digest,
        )
        is None
    )


def test_formal_math_premise_retrieval_source_module_scan_streams_without_path_rglob(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    input_dir = tmp_path / "input"
    source_modules = input_dir / "source_modules"
    nested = source_modules / "system/lib"
    nested.mkdir(parents=True)
    for name in premise_module.INPUT_NAMES:
        (input_dir / name).write_text("{}", encoding="utf-8")
    (input_dir / "bundle_manifest.json").write_text("{}", encoding="utf-8")
    module_file = nested / "premise_runtime.py"
    module_file.write_text("VALUE = 1\n", encoding="utf-8")
    (nested / "notes.md").write_text("public note\n", encoding="utf-8")
    original_rglob = Path.rglob

    def guarded_rglob(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == source_modules:
            raise AssertionError("source module scan should not call Path.rglob")
        return original_rglob(self, *args, **kwargs)

    monkeypatch.setattr(Path, "rglob", guarded_rglob)

    assert [
        path.relative_to(input_dir).as_posix()
        for path in premise_module._scan_input_paths(input_dir, include_negative=False)
    ] == [
        "projection_protocol.json",
        "premise_index.json",
        "retrieval_queries.json",
        "context_recipes.json",
        "strategy_cases.json",
        "bundle_manifest.json",
        "source_modules/system/lib/notes.md",
        "source_modules/system/lib/premise_runtime.py",
    ]


def test_formal_math_premise_retrieval_source_module_scan_recurses_before_root_sibling(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    source_modules = tmp_path / "source_modules"
    nested_opened = {"value": False}

    class FakeEntry:
        def __init__(self, name: str, *, is_dir: bool = False, is_file: bool = False) -> None:
            self.name = name
            self._is_dir = is_dir
            self._is_file = is_file

        def is_dir(self, *, follow_symlinks: bool = True) -> bool:
            return self._is_dir

        def is_file(self, *, follow_symlinks: bool = True) -> bool:
            return self._is_file

    class FakeScandir:
        def __init__(self, path: Path, entries: list[FakeEntry]) -> None:
            self.path = path
            self.entries = entries

        def __enter__(self) -> "FakeScandir":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def __iter__(self) -> Any:
            for index, entry in enumerate(self.entries):
                if self.path == source_modules and index == 1 and not nested_opened["value"]:
                    raise AssertionError("source module scan should recurse before root siblings")
                yield entry

    def fake_scandir(path: Path) -> FakeScandir:
        path = Path(path)
        if path == source_modules:
            return FakeScandir(
                path,
                [
                    FakeEntry("system", is_dir=True),
                    FakeEntry("bundle_manifest.json", is_file=True),
                ],
            )
        if path == source_modules / "system":
            nested_opened["value"] = True
            return FakeScandir(path, [FakeEntry("premise_runtime.py", is_file=True)])
        raise AssertionError(f"unexpected scandir path: {path}")

    class FakeOs:
        scandir = staticmethod(fake_scandir)

    monkeypatch.setattr(premise_module, "os", FakeOs)

    refs = [
        path.relative_to(source_modules).as_posix()
        for path in premise_module._iter_source_module_files(source_modules)
    ]

    assert refs == ["system/premise_runtime.py", "bundle_manifest.json"]


def test_formal_math_premise_retrieval_source_module_scan_skips_symlinked_files(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    source_modules = input_dir / "source_modules"
    nested = source_modules / "system/lib"
    nested.mkdir(parents=True)
    for name in premise_module.INPUT_NAMES:
        (input_dir / name).write_text("{}", encoding="utf-8")
    direct = nested / "premise_runtime.py"
    direct.write_text("VALUE = 1\n", encoding="utf-8")
    outside = tmp_path / "outside_runtime.py"
    outside.write_text("SECRET = False\n", encoding="utf-8")
    symlink = nested / "linked_runtime.py"
    try:
        symlink.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    refs = [
        path.relative_to(input_dir).as_posix()
        for path in premise_module._scan_input_paths(input_dir, include_negative=False)
    ]

    assert "source_modules/system/lib/premise_runtime.py" in refs
    assert "source_modules/system/lib/linked_runtime.py" not in refs


def test_formal_math_premise_retrieval_imports_real_macro_premise_index() -> None:
    premise_index = json.loads(
        (FIXTURE_INPUT / "premise_index.json").read_text(encoding="utf-8")
    )
    protocol = json.loads(
        (FIXTURE_INPUT / "projection_protocol.json").read_text(encoding="utf-8")
    )

    assert premise_index["index_id"] == "lean_std_toolchain_premise_index_v0_public_import"
    assert premise_index["source_ref"] == (
        "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/"
        "premise_index.json"
    )
    assert premise_index["source_sha256"] == (
        "sha256:c78b176388a5e81bd8a785950e7db0c9a65fd38e556515134146163b48604df1"
    )
    assert premise_index["premise_count"] == 11
    assert all(row["body_copied"] is True for row in premise_index["premises"])
    assert all("/Users/" not in row["source_ref"] for row in premise_index["premises"])
    assert {row["premise_id"] for row in premise_index["premises"]} >= {
        "premise_nat_add_comm",
        "premise_bool_not_not",
        "premise_list_length_append",
        "premise_iff_intro",
    }
    copied = protocol["copied_material"][0]
    assert copied["classification"] == "copied_non_secret_macro_body_with_provenance"
    assert copied["body_copied"] is True
    assert copied["source_sha256"] == premise_index["source_sha256"]


def test_formal_math_premise_retrieval_source_open_manifest_counts_body_floor() -> None:
    premise_source_path = (
        MICROCOSM_ROOT.parent
        / "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/premise_index.json"
    )
    problem_source_path = (
        MICROCOSM_ROOT.parent
        / "state/runs/PROVER_BENCHMARK_RING2_20260510_premise_retrieval_v0/problem_source_manifest.json"
    )
    source_module_manifest = json.loads(
        (BUNDLE_INPUT / "source_module_manifest.json").read_text()
    )
    bundle_manifest = json.loads((BUNDLE_INPUT / "bundle_manifest.json").read_text())
    fixture_manifest = json.loads(
        (
            MICROCOSM_ROOT
            / "core/fixture_manifests/formal_math_premise_retrieval.fixture_manifest.json"
        ).read_text()
    )
    premise_source = json.loads(premise_source_path.read_text())
    problem_source = json.loads(problem_source_path.read_text())
    public_premise_index = json.loads((BUNDLE_INPUT / "premise_index.json").read_text())
    public_queries = json.loads((BUNDLE_INPUT / "retrieval_queries.json").read_text())

    exact_modules = {row["module_id"]: row for row in source_module_manifest["modules"]}
    faithful_modules = {
        row["module_id"]: row for row in source_module_manifest["source_faithful_modules"]
    }
    body_floor = fixture_manifest["source_open_body_imports"]
    bundle_exact_artifacts = {
        row["module_id"]: row for row in bundle_manifest["copied_macro_body_artifacts"]
    }

    assert source_module_manifest["module_count"] == 4
    assert set(exact_modules) == {
        "premise_retrieval_aggregate_report_body_import",
        "premise_retrieval_cost_metrics_body_import",
        "premise_retrieval_graph_update_candidates_body_import",
        "premise_retrieval_graph_variant_body_import",
    }
    assert set(faithful_modules) == {
        "lean_std_toolchain_premise_index_body_import",
        "formal_math_public_retrieval_query_slice_body_import",
    }
    assert body_floor["body_material_count"] == 6
    assert body_floor["body_material_ids"] == [
        *exact_modules.keys(),
        *faithful_modules.keys(),
    ]

    for module_id, module in exact_modules.items():
        copied_path = BUNDLE_INPUT / module["path"]
        assert copied_path.is_file()
        assert module["sha256"] == sha256(copied_path.read_bytes()).hexdigest()
        assert bundle_exact_artifacts[module_id]["sha256"] == f"sha256:{module['sha256']}"
        copied_text = copied_path.read_text(encoding="utf-8")
        assert "/Users/" not in copied_text
        assert '"provider_calls": 0' in copied_text or module_id.endswith(
            ("graph_update_candidates_body_import", "graph_variant_body_import")
        )

    premise_module = faithful_modules["lean_std_toolchain_premise_index_body_import"]
    query_module = faithful_modules["formal_math_public_retrieval_query_slice_body_import"]
    assert premise_module["source_sha256"] == (
        "sha256:" + sha256(premise_source_path.read_bytes()).hexdigest()
    )
    assert premise_module["target_sha256"] == (
        "sha256:" + sha256((BUNDLE_INPUT / "premise_index.json").read_bytes()).hexdigest()
    )
    assert query_module["source_sha256"] == (
        "sha256:" + sha256(problem_source_path.read_bytes()).hexdigest()
    )
    assert query_module["target_sha256"] == (
        "sha256:" + sha256((BUNDLE_INPUT / "retrieval_queries.json").read_bytes()).hexdigest()
    )

    for source_row, public_row in zip(premise_source["premises"], public_premise_index["premises"]):
        assert public_row["premise_id"] == source_row["premise_id"]
        assert public_row["theorem_or_def_name"] == source_row["theorem_or_def_name"]
        assert public_row["namespace"] == source_row["namespace"]
        assert public_row["retrieval_terms"] == source_row["retrieval_terms"]
        assert public_row["allowed_for_split"] == source_row["allowed_for_split"]
        assert public_row["statement_excerpt"] == source_row["statement_excerpt"]
        assert public_row["source_ref"].startswith("lean-toolchain://")
        assert public_row["body_copied"] is True
        assert "proof_body" not in public_row
        assert "oracle_needed_premise_ids" not in public_row

    source_problems = {row["problem_id"]: row for row in problem_source["problems"]}
    for query in public_queries["queries"]:
        source_problem = source_problems[query["source_problem_id"]]
        assert query["split"] == source_problem["split"]
        assert set(source_problem["retrieval_query_terms"]).issubset(query["query_terms"])
        assert source_problem["theorem_name"].removeprefix("ring2_") in query["query_id"]
        assert "oracle_needed_premise_ids" not in query
        assert "proof_body" not in query
