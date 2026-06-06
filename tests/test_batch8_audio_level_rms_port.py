from __future__ import annotations

import hashlib
import json
import shutil
import struct
import wave
from pathlib import Path
from typing import Any

import pytest

from microcosm_core.organs.batch8_audio_level_rms_port import (
    AUTHORITY_CEILING,
    EXPECTED_CASES,
    EXPECTED_NEGATIVE_CASES,
    _evaluate_reference_cases,
    main,
    normalized_level,
    result_card,
    run,
    run_batch8_audio_level_rms_bundle,
)


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = MICROCOSM_ROOT.parent
ORGAN_ID = "batch8_audio_level_rms_port"
FIXTURE_INPUT = MICROCOSM_ROOT / f"fixtures/first_wave/{ORGAN_ID}/input"
EXPORTED_BUNDLE = MICROCOSM_ROOT / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"
SOURCE_MODULE_MANIFEST = EXPORTED_BUNDLE / "source_module_manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_int16_wav(path: Path, samples: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16_000)
        handle.writeframes(struct.pack(f"<{len(samples)}h", *samples))


def _probe_manifest(fixture: Path) -> dict[str, Any]:
    return json.loads(
        (fixture / "batch8_audio_level_rms_port_probe_manifest.json").read_text(
            encoding="utf-8",
        )
    )


def _write_probe_manifest(fixture: Path, payload: dict[str, Any]) -> None:
    (fixture / "batch8_audio_level_rms_port_probe_manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _add_byte_reference_case(
    fixture: Path,
    *,
    case_id: str,
    audio_ref: str,
    samples: list[int],
    expected_samples: list[int] | None = None,
    append: bool = False,
) -> Path:
    audio_path = fixture / audio_ref
    _write_int16_wav(audio_path, samples)
    probe = _probe_manifest(fixture)
    byte_cases = probe.get("byte_reference_cases")
    if not append or not isinstance(byte_cases, list):
        byte_cases = []
    byte_cases.append(
        {
            "audio_ref": audio_ref,
            "body_in_receipt": False,
            "case_id": case_id,
            "container": "wav",
            "expected_level": normalized_level(expected_samples or samples, "int16"),
            "sample_format": "int16",
            "tolerance": 1e-6,
        }
    )
    probe["byte_reference_cases"] = byte_cases
    _write_probe_manifest(fixture, probe)
    return audio_path


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


def _copy_public_fixture(tmp_path: Path) -> Path:
    public_root = tmp_path / "microcosm-substrate"
    shutil.copytree(MICROCOSM_ROOT / "core", public_root / "core")
    shutil.copytree(
        MICROCOSM_ROOT / f"examples/{ORGAN_ID}",
        public_root / f"examples/{ORGAN_ID}",
    )
    shutil.copytree(
        MICROCOSM_ROOT / f"fixtures/first_wave/{ORGAN_ID}",
        public_root / f"fixtures/first_wave/{ORGAN_ID}",
    )
    return public_root / f"fixtures/first_wave/{ORGAN_ID}/input"


def test_normalized_level_port_math_matches_swift_formula() -> None:
    assert normalized_level([], "float32") == 0
    assert normalized_level([1.0, -1.0, 0.5], "float32") == 1
    assert normalized_level([0, 1638, -1638, 3277], "int16") == pytest.approx(
        0.48989296997474613,
        abs=1e-6,
    )
    with pytest.raises(ValueError):
        normalized_level([1, 2, 3], "pcm24")


def test_batch8_audio_level_reference_cases_reject_boolean_expected_level() -> None:
    probe = {
        "cases": [
            {
                "case_id": "float32_reference_buffer",
                "sample_format": "float32",
                "samples": [1.0, -1.0, 0.5],
                "expected_level": True,
                "tolerance": 1e-6,
            },
            {
                "case_id": "int16_reference_buffer",
                "sample_format": "int16",
                "samples": [0, 1638, -1638, 3277],
                "expected_level": 0.48989296997474613,
                "tolerance": 1e-6,
            },
            {
                "case_id": "clamp_over_one_buffer",
                "sample_format": "float32",
                "samples": [1.0, -1.0, 0.5],
                "expected_level": 1.0,
                "tolerance": 1e-6,
            },
        ]
    }

    case_results, findings = _evaluate_reference_cases(probe)

    assert "float32_reference_buffer" not in {row["case_id"] for row in case_results}
    assert {
        (row["error_code"], row.get("case_id"))
        for row in findings
    } >= {
        ("BATCH8_AUDIO_LEVEL_CASE_INVALID", "float32_reference_buffer"),
        ("BATCH8_AUDIO_LEVEL_REFERENCE_CASE_MISSING", "float32_reference_buffer"),
    }


def test_batch8_audio_level_reference_case_sample_perturbation_blocks(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    probe = _probe_manifest(fixture)
    target_case = next(
        row for row in probe["cases"] if row["case_id"] == "float32_reference_buffer"
    )
    target_case["samples"] = [0.0, 0.2, -0.05, 0.1]
    _write_probe_manifest(fixture, probe)

    result = run(
        fixture,
        tmp_path / f"microcosm-substrate/receipts/first_wave/{ORGAN_ID}",
    )

    assert result["status"] == "blocked"
    mismatch = next(
        row
        for row in result["exercise"]["reference_cases"]
        if row["case_id"] == "float32_reference_buffer"
    )
    assert mismatch["status"] == "blocked"
    assert mismatch["expected_level"] == pytest.approx(
        0.48989794855663565,
        abs=1e-9,
    )
    assert mismatch["observed_level"] == pytest.approx(
        0.9165151389911681,
        abs=1e-9,
    )
    assert mismatch["observed_level"] != mismatch["expected_level"]
    assert mismatch["delta"] > mismatch["tolerance"]
    assert {
        (row["error_code"], row.get("case_id"))
        for row in result["findings"]
    } >= {("BATCH8_AUDIO_LEVEL_PARITY_MISMATCH", "float32_reference_buffer")}


def test_batch8_audio_level_expected_level_perturbation_blocks(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    probe = _probe_manifest(fixture)
    target_case = next(
        row for row in probe["cases"] if row["case_id"] == "int16_reference_buffer"
    )
    target_case["expected_level"] = 0.99999
    _write_probe_manifest(fixture, probe)

    result = run(
        fixture,
        tmp_path / f"microcosm-substrate/receipts/first_wave/{ORGAN_ID}",
    )

    assert result["status"] == "blocked"
    assert result["exercise"]["passed_reference_case_count"] == len(EXPECTED_CASES) - 1
    mismatch = next(
        row
        for row in result["exercise"]["reference_cases"]
        if row["case_id"] == "int16_reference_buffer"
    )
    assert mismatch["status"] == "blocked"
    assert mismatch["observed_level"] == pytest.approx(0.48989296997474613, abs=1e-6)
    assert "BATCH8_AUDIO_LEVEL_PARITY_MISMATCH" in result["error_codes"]


def test_batch8_audio_level_recomputes_from_generated_wav_bytes(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    samples = [0, 1638, -1638, 3277]
    audio_path = _add_byte_reference_case(
        fixture,
        case_id="generated_int16_wav_reference",
        audio_ref="audio/generated_int16_reference.wav",
        samples=samples,
    )

    result = run(
        fixture,
        tmp_path / f"microcosm-substrate/receipts/first_wave/{ORGAN_ID}",
    )

    assert result["status"] == "pass"
    assert result["exercise"]["byte_reference_case_count"] == 1
    assert result["exercise"]["passed_byte_reference_case_count"] == 1
    byte_case = result["exercise"]["byte_reference_cases"][0]
    assert byte_case["case_id"] == "generated_int16_wav_reference"
    assert byte_case["container"] == "wav"
    assert byte_case["sample_format"] == "int16"
    assert byte_case["frame_count"] == len(samples)
    assert byte_case["decoded_sample_count"] == len(samples)
    assert byte_case["byte_sha256"] == _sha256(audio_path)
    assert byte_case["observed_level"] == pytest.approx(
        normalized_level(samples, "int16"),
        abs=1e-9,
    )
    assert byte_case["observed_level"] == pytest.approx(
        0.48989296997474613,
        abs=1e-6,
    )
    assert byte_case["body_in_receipt"] is False


def test_batch8_audio_level_mutated_wav_bytes_change_verdict(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    expected_samples = [0, 1638, -1638, 3277]
    mutated_samples = [0, 6000, -1638, 3277]
    _add_byte_reference_case(
        fixture,
        case_id="mutated_int16_wav_reference",
        audio_ref="audio/mutated_int16_reference.wav",
        samples=mutated_samples,
        expected_samples=expected_samples,
    )

    result = run(
        fixture,
        tmp_path / f"microcosm-substrate/receipts/first_wave/{ORGAN_ID}",
    )

    assert result["status"] == "blocked"
    byte_case = result["exercise"]["byte_reference_cases"][0]
    assert byte_case["status"] == "blocked"
    assert byte_case["observed_level"] == pytest.approx(
        normalized_level(mutated_samples, "int16"),
        abs=1e-9,
    )
    assert byte_case["observed_level"] == pytest.approx(
        0.8581880661353443,
        abs=1e-9,
    )
    assert byte_case["expected_level"] == pytest.approx(
        normalized_level(expected_samples, "int16"),
        abs=1e-9,
    )
    assert byte_case["expected_level"] == pytest.approx(
        0.48989296997474613,
        abs=1e-9,
    )
    assert byte_case["delta"] > byte_case["tolerance"]
    assert {
        (row["error_code"], row.get("case_id"))
        for row in result["findings"]
    } >= {("BATCH8_AUDIO_LEVEL_PARITY_MISMATCH", "mutated_int16_wav_reference")}


def test_batch8_audio_level_paired_wav_artifacts_follow_amplitude_not_expected_field(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    expected_samples = [0, 1638, -1638, 3277]
    mutated_samples = [0, 6000, -1638, 3277]
    _add_byte_reference_case(
        fixture,
        case_id="paired_good_int16_wav_reference",
        audio_ref="audio/paired_good_int16_reference.wav",
        samples=expected_samples,
    )
    _add_byte_reference_case(
        fixture,
        case_id="paired_bad_int16_wav_reference",
        audio_ref="audio/paired_bad_int16_reference.wav",
        samples=mutated_samples,
        expected_samples=expected_samples,
        append=True,
    )

    result = run(
        fixture,
        tmp_path / f"microcosm-substrate/receipts/first_wave/{ORGAN_ID}",
    )

    assert result["status"] == "blocked"
    assert result["exercise"]["byte_reference_case_count"] == 2
    assert result["exercise"]["passed_byte_reference_case_count"] == 1
    byte_cases = {
        row["case_id"]: row for row in result["exercise"]["byte_reference_cases"]
    }
    good = byte_cases["paired_good_int16_wav_reference"]
    bad = byte_cases["paired_bad_int16_wav_reference"]
    assert good["status"] == "pass"
    assert bad["status"] == "blocked"
    assert good["observed_level"] == pytest.approx(0.48989296997474613, abs=1e-9)
    assert good["observed_level"] == pytest.approx(good["expected_level"], abs=1e-9)
    assert bad["expected_level"] == pytest.approx(good["expected_level"], abs=1e-9)
    assert bad["observed_level"] == pytest.approx(0.8581880661353443, abs=1e-9)
    assert bad["observed_level"] == pytest.approx(
        normalized_level(mutated_samples, "int16"),
        abs=1e-9,
    )
    assert bad["observed_level"] != pytest.approx(good["observed_level"], abs=1e-9)
    assert bad["delta"] == pytest.approx(
        abs(bad["observed_level"] - bad["expected_level"]),
        abs=1e-12,
    )
    assert bad["delta"] > bad["tolerance"]
    assert {
        (row["error_code"], row.get("case_id"))
        for row in result["findings"]
    } >= {("BATCH8_AUDIO_LEVEL_PARITY_MISMATCH", "paired_bad_int16_wav_reference")}


def test_batch8_audio_level_rms_port_runs_public_parity_fixtures(tmp_path: Path) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        acceptance_out=tmp_path
        / f"receipts/acceptance/first_wave/{ORGAN_ID}_fixture_acceptance.json",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["real_substrate_disposition"] == "real_substrate_capsule"
    assert result["authority_ceiling"] == AUTHORITY_CEILING
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["source_module_manifest"]["all_required_anchors_present"] is True
    assert result["semantic_negative_case_evaluator_used"] is True

    exercise = result["exercise"]
    assert exercise["reference_case_count"] == len(EXPECTED_CASES)
    assert exercise["passed_reference_case_count"] == len(EXPECTED_CASES)
    assert exercise["negative_exercises"]["empty_buffer_level"] == 0
    assert exercise["negative_exercises"]["clamp_over_one_level"] == 1
    assert exercise["negative_exercises"]["unknown_format_refused"] is True
    assert result["body_in_receipt"] is False


def test_batch8_audio_level_rms_bundle_validates_runtime_shape(tmp_path: Path) -> None:
    result = run_batch8_audio_level_rms_bundle(
        EXPORTED_BUNDLE,
        tmp_path / f"receipts/runtime_shell/demo_project/organs/{ORGAN_ID}",
        command="pytest",
    )

    assert result["status"] == "pass"
    assert result["input_mode"] == f"exported_{ORGAN_ID}_bundle"
    assert result["source_module_manifest"]["module_count"] == 1
    assert result["exercise"]["copied_macro_source_module_count"] == 1
    assert result["secret_exclusion_scan"]["blocking_hit_count"] == 0
    assert result["receipt_body_scan"]["status"] == "pass"


def test_batch8_audio_source_module_is_exact_swift_source_ref() -> None:
    manifest = json.loads(SOURCE_MODULE_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["source_import_class"] == "copied_non_secret_macro_body"
    assert manifest["source_port_class"] == "python_port_from_swift_math"
    assert manifest["body_in_receipt"] is False
    assert manifest["module_count"] == 1

    for row in manifest["modules"]:
        source = SOURCE_ROOT / row["source_ref"]
        target = EXPORTED_BUNDLE / row["path"]
        assert source.is_file(), row["source_ref"]
        assert target.is_file(), row["path"]
        assert source.read_bytes() == target.read_bytes(), row["source_ref"]
        assert row["sha256"] == _sha256(source)
        text = target.read_text(encoding="utf-8")
        assert all(anchor in text for anchor in row["required_anchors"])


def test_batch8_audio_source_manifest_digest_swap_is_rejected(tmp_path: Path) -> None:
    fixture = _copy_public_fixture(tmp_path)
    bundle = (
        fixture.parents[3]
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"
    )
    manifest_path = bundle / "source_module_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["modules"][0]["sha256"] = "0" * 64
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = run_batch8_audio_level_rms_bundle(
        bundle,
        tmp_path / f"microcosm-substrate/receipts/runtime_shell/demo_project/organs/{ORGAN_ID}",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]


def test_batch8_audio_copied_source_body_mutation_is_rejected(tmp_path: Path) -> None:
    fixture = _copy_public_fixture(tmp_path)
    bundle = (
        fixture.parents[3]
        / f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle"
    )
    source_module = next((bundle / "source_modules").rglob("AudioLevelMonitor.swift"))
    source_module.write_text(
        source_module.read_text(encoding="utf-8").replace(
            "return min(max(rms * 8, 0), 1)",
            "return min(max(rms * 4, 0), 1)",
        ),
        encoding="utf-8",
    )

    result = run_batch8_audio_level_rms_bundle(
        bundle,
        tmp_path / f"microcosm-substrate/receipts/runtime_shell/demo_project/organs/{ORGAN_ID}",
    )

    assert result["status"] == "blocked"
    assert result["source_module_manifest"]["status"] == "blocked"
    assert result["source_module_manifest"]["all_expected_digests_matched"] is False
    assert result["source_module_manifest"]["all_required_anchors_present"] is False
    assert "CROWN_JEWEL_SOURCE_DIGEST_MISMATCH" in result["error_codes"]
    assert "CROWN_JEWEL_SOURCE_LINE_COUNT_MISMATCH" not in result["error_codes"]
    assert "CROWN_JEWEL_SOURCE_ANCHOR_MISSING" in result["error_codes"]


def test_batch8_audio_level_card_omits_private_bodies(
    tmp_path: Path,
    capsys,
) -> None:
    result = run(
        FIXTURE_INPUT,
        tmp_path / f"receipts/first_wave/{ORGAN_ID}",
        command="pytest",
    )
    card = result_card(result)

    assert card["status"] == "pass"
    assert card["source_module_count"] == 1
    assert card["observed_negative_case_count"] == len(EXPECTED_NEGATIVE_CASES)
    assert card["authority_floor"] == {
        "authority_ceiling": AUTHORITY_CEILING["authority_ceiling"],
        "real_substrate_disposition": "real_substrate_capsule",
        "python_port": True,
        "microphone_permission_required": False,
        "audio_session_started": False,
        "device_capture_authorized": False,
        "provider_dispatch": False,
        "repo_mutation_authorized": False,
        "source_mutation_authorized": False,
        "publication_authorized": False,
        "release_authorized": False,
    }
    assert card["body_floor"] == {
        "body_in_receipt": False,
        "source_module_body_in_receipt": False,
        "receipt_body_scan_status": "pass",
        "source_bodies_in_card": False,
        "secret_scan_scope_in_card": False,
    }
    serialized = json.dumps(result, sort_keys=True)
    assert "/Users/" not in serialized
    assert "src/ai_workflow" not in serialized
    assert "source_body" not in _walk_keys(result)
    assert "body" not in _walk_keys(result)

    assert (
        main(
            [
                "run",
                "--input",
                str(FIXTURE_INPUT),
                "--out",
                str(tmp_path / "cli_card"),
                "--card",
            ]
        )
        == 0
    )
    cli_card = json.loads(capsys.readouterr().out)
    assert cli_card["authority_floor"] == card["authority_floor"]
    assert cli_card["body_floor"] == card["body_floor"]


def test_batch8_audio_level_negative_cases_are_stable() -> None:
    for case_id, expected_codes in EXPECTED_NEGATIVE_CASES.items():
        payload = json.loads((FIXTURE_INPUT / f"{case_id}.json").read_text(encoding="utf-8"))
        assert payload["error_codes"] == list(expected_codes)
        assert payload["body_in_receipt"] is False


def test_batch8_audio_level_negative_cases_are_semantic_not_declared_labels(
    tmp_path: Path,
) -> None:
    fixture = _copy_public_fixture(tmp_path)
    for case_id in EXPECTED_NEGATIVE_CASES:
        path = fixture / f"{case_id}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["error_codes"] = ["BOGUS_DECLARED_ERROR"]
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    result = run(
        fixture,
        tmp_path / f"microcosm-substrate/receipts/first_wave/{ORGAN_ID}",
    )

    assert result["status"] == "pass"
    assert set(result["observed_negative_cases"]) == set(EXPECTED_NEGATIVE_CASES)
    assert result["missing_negative_cases"] == []
    assert result["semantic_negative_case_evaluator_used"] is True
    assert all(row["semantic_evaluator_used"] for row in result["negative_case_semantics"])
    assert "BOGUS_DECLARED_ERROR" not in result["error_codes"]
    assert "BATCH8_AUDIO_LEVEL_EMPTY_BUFFER_ZERO" in result["error_codes"]
    assert "BATCH8_AUDIO_LEVEL_UNKNOWN_FORMAT_REFUSED" in result["error_codes"]
    assert "BATCH8_AUDIO_LEVEL_CLAMP_REQUIRED" in result["error_codes"]
