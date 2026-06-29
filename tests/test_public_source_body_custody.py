from __future__ import annotations

import fnmatch
import hashlib
import json
from pathlib import Path, PurePosixPath
import tomllib


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
STANDALONE_ROOT_PREFIX = "microcosm-substrate/"
PUBLIC_ROOT_PREFIXES = {
    "core",
    "examples",
    "fixtures",
    "paper_modules",
    "receipts",
    "src",
    "standards",
}
EXACT_COPY_SOURCE_TO_TARGET_RELATIONS = {
    "exact_copy",
    "exact_copy_macro_body_plus_source_faithful_public_exercise",
    "exact_public_safe_macro_copy",
    "exact_public_safe_source_copy",
    "source_faithful_public_safe_exact_copy",
}
PACKAGE_CODE_PREFIXES = (
    "src/microcosm_core/",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _digest_value(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text.split(":", 1)[1] if text.startswith("sha256:") else text


def _target_refs(row: dict) -> list[str]:
    refs: list[str] = []
    primary = row.get("target_ref") or row.get("path")
    if primary:
        refs.append(str(primary))
    for target_ref in row.get("target_refs") or []:
        if isinstance(target_ref, str) and target_ref not in refs:
            refs.append(target_ref)
    return refs


def _resolve_public_ref(ref: str, *, manifest_path: Path) -> Path | None:
    ref = ref.split("::", 1)[0]
    if ref.startswith(STANDALONE_ROOT_PREFIX):
        ref = ref[len(STANDALONE_ROOT_PREFIX) :]
    ref_path = PurePosixPath(ref)
    if ref_path.is_absolute() or ".." in ref_path.parts:
        return None
    if ref_path.parts[:1] and ref_path.parts[0] in PUBLIC_ROOT_PREFIXES:
        return MICROCOSM_ROOT / Path(ref)
    return manifest_path.parent / Path(ref)


def _packaged_data_patterns() -> list[str]:
    payload = tomllib.loads((MICROCOSM_ROOT / "pyproject.toml").read_text())
    data_files = payload["tool"]["setuptools"]["data-files"]
    return [
        pattern
        for patterns in data_files.values()
        for pattern in patterns
    ]


def _is_shipped_with_package(rel_ref: str, *, data_patterns: list[str]) -> bool:
    if any(rel_ref.startswith(prefix) for prefix in PACKAGE_CODE_PREFIXES):
        return True
    return any(fnmatch.fnmatchcase(rel_ref, pattern) for pattern in data_patterns)


def test_public_source_body_manifest_targets_are_current_and_shipped() -> None:
    data_patterns = _packaged_data_patterns()
    manifest_paths = sorted(
        (MICROCOSM_ROOT / "examples").glob("**/*source_module_manifest*.json")
    )
    assert manifest_paths

    issues: list[str] = []
    copied_body_count = 0
    shipped_target_count = 0

    for manifest_path in manifest_paths:
        manifest_rel = manifest_path.relative_to(MICROCOSM_ROOT).as_posix()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        rows = manifest.get("modules") or []
        if manifest.get("module_count") != len(rows):
            issues.append(
                f"{manifest_rel}: module_count={manifest.get('module_count')} "
                f"but modules has {len(rows)} rows"
            )
        if manifest.get("body_in_receipt") is True:
            issues.append(f"{manifest_rel}: manifest body_in_receipt must be false")
        if manifest.get("body_text_in_receipt") is True:
            issues.append(
                f"{manifest_rel}: manifest body_text_in_receipt must be false"
            )
        if not _is_shipped_with_package(manifest_rel, data_patterns=data_patterns):
            issues.append(f"{manifest_rel}: manifest is not included in package data")

        for row in rows:
            material_id = (
                row.get("module_id")
                or row.get("material_id")
                or row.get("source_ref")
                or "unknown_material"
            )
            if row.get("body_in_receipt") is True:
                issues.append(f"{manifest_rel}:{material_id}: body_in_receipt true")
            if row.get("body_text_in_receipt") is True:
                issues.append(
                    f"{manifest_rel}:{material_id}: body_text_in_receipt true"
                )
            if row.get("body_copied") is not True:
                continue

            copied_body_count += 1
            target_refs = _target_refs(row)
            if not target_refs:
                issues.append(f"{manifest_rel}:{material_id}: no target ref")
                continue

            for index, target_ref in enumerate(target_refs):
                target_path = _resolve_public_ref(
                    target_ref, manifest_path=manifest_path
                )
                if target_path is None:
                    issues.append(
                        f"{manifest_rel}:{material_id}: unresolvable target {target_ref}"
                    )
                    continue
                try:
                    target_rel = target_path.relative_to(MICROCOSM_ROOT).as_posix()
                except ValueError:
                    issues.append(
                        f"{manifest_rel}:{material_id}: target outside public root "
                        f"{target_path}"
                    )
                    continue
                if not target_path.is_file():
                    issues.append(
                        f"{manifest_rel}:{material_id}: missing target {target_rel}"
                    )
                    continue

                if not _is_shipped_with_package(
                    target_rel, data_patterns=data_patterns
                ):
                    issues.append(
                        f"{manifest_rel}:{material_id}: target is not shipped "
                        f"{target_rel}"
                    )
                else:
                    shipped_target_count += 1

                if index != 0:
                    continue

                digest = _sha256(target_path)
                line_count = _line_count(target_path)
                byte_count = target_path.stat().st_size
                for field in ("target_sha256", "sha256"):
                    if field in row and _digest_value(row.get(field)) != digest:
                        issues.append(
                            f"{manifest_rel}:{material_id}: {field} does not "
                            f"match {target_rel}"
                        )
                relation = str(row.get("source_to_target_relation") or "")
                if (
                    relation in EXACT_COPY_SOURCE_TO_TARGET_RELATIONS
                    and row.get("sha256_match") is True
                    and "source_sha256" in row
                    and _digest_value(row.get("source_sha256")) != digest
                ):
                    issues.append(
                        f"{manifest_rel}:{material_id}: exact-copy source_sha256 "
                        f"does not match {target_rel}"
                    )
                if "target_line_count" in row:
                    if row.get("target_line_count") != line_count:
                        issues.append(
                            f"{manifest_rel}:{material_id}: target_line_count "
                            f"does not match {target_rel}"
                        )
                elif "line_count" in row and row.get("line_count") != line_count:
                    issues.append(
                        f"{manifest_rel}:{material_id}: line_count does not "
                        f"match {target_rel}"
                    )
                if "target_byte_count" in row:
                    if row.get("target_byte_count") != byte_count:
                        issues.append(
                            f"{manifest_rel}:{material_id}: target_byte_count "
                            f"does not match {target_rel}"
                        )
                elif "byte_count" in row and row.get("byte_count") != byte_count:
                    issues.append(
                        f"{manifest_rel}:{material_id}: byte_count does not "
                        f"match {target_rel}"
                    )
                text = target_path.read_text(encoding="utf-8")
                missing_anchors = [
                    anchor
                    for anchor in row.get("required_anchors") or []
                    if isinstance(anchor, str) and anchor not in text
                ]
                if missing_anchors:
                    issues.append(
                        f"{manifest_rel}:{material_id}: missing required anchors "
                        f"{missing_anchors!r}"
                    )

    assert copied_body_count > 0
    assert shipped_target_count >= copied_body_count
    assert not issues, "\n".join(issues[:80])


def test_public_source_body_receipts_align_with_authority_map() -> None:
    authority_map = json.loads(
        (MICROCOSM_ROOT / "receipts/runtime_shell/public_authority_map.json").read_text(
            encoding="utf-8"
        )
    )
    ledger = json.loads(
        (MICROCOSM_ROOT / "core/substrate_substitution_ledger.json").read_text(
            encoding="utf-8"
        )
    )

    assert authority_map["status"] == "pass"
    assert authority_map["release_authorized"] is False
    assert authority_map["unsafe_payload_bodies_exported"] is False
    assert authority_map["macro_body_import_floor"]["status"] == "pass"
    assert authority_map["surface_counts"][
        "mixed_public_safe_macro_import_assay_status"
    ] == "pass"
    assert ledger["status"] == "pass"
    assert ledger["validation"]["status"] == "pass"
    assert ledger["summary"]["receipt_body_count"] == 0
    assert authority_map["substrate_substitution"]["status"] == "pass"
    assert authority_map["substrate_substitution"]["accepted_organ_count"] == ledger[
        "summary"
    ]["accepted_organ_count"]
    assert authority_map["substrate_substitution"]["real_body_count"] == ledger[
        "summary"
    ]["real_body_count"]
