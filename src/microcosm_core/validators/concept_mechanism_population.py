from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from microcosm_core.schemas import read_json_strict


ALLOWED_RESIDUAL_DISPOSITIONS = {
    "already_valid_projection_consumer",
    "captured_for_later_owner",
    "closed_as_stale_parallel_index",
    "redirected_to_projection_consumer",
}

DEFAULT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENTRY_PACKET = DEFAULT_ROOT / "atlas/entry_packet.json"
DEFAULT_PRESSURE = DEFAULT_ROOT / "core/public_standard_pressure.json"

RESOLVED_TARGET_STATUSES = {
    "declared_receipt_id",
    "declared_receipt_ref",
    "resolved_code_locus",
    "resolved_json_instance",
    "resolved_receipt_ref",
    "resolved_registry_or_atlas_target",
}

PLANNED_TARGET_PREFIXES = (
    "planned_",
)

MECHANISM_POPULATION_BINDING_REQUIRED = (
    "mechanism_role",
    "concept_pair_ref",
    "source_refs",
    "transformation_shape",
    "state_or_proof_effect",
    "omission_receipt",
    "anti_claims",
    "validator_refs",
)

CONCEPT_CLUSTER_FLAG_REQUIRED = (
    "schema_version",
    "cluster_id",
    "kind",
    "concept_id",
    "claim",
    "source_ref",
    "specimen_id",
    "mechanism_count",
    "principle_count",
    "axiom_count",
    "drilldown",
    "authority_boundary",
)


def _load_json(path: Path) -> dict[str, Any]:
    """Strict JSON loader used by every record/route/pressure read in this validator.

    - Teleology: single chokepoint so all reads share strict (reject-trailing-garbage) parse semantics.
    - Guarantee: returns the parsed JSON object for `path` via read_json_strict.
    - Fails: propagates read_json_strict errors (missing file / malformed or non-strict JSON) to the caller.
    - When-needed: tracing where a malformed concept/mechanism/receipt/entry-packet JSON is parsed.
    - Escalates-to: microcosm_core.schemas.read_json_strict.
    """
    return read_json_strict(path)


def _as_dict(value: Any) -> dict[str, Any]:
    """Defensive coercion of an arbitrary JSON value to a dict.

    - Teleology: lets downstream checks treat malformed/absent nested fields as empty instead of crashing.
    - Guarantee: returns `value` unchanged when it is a dict, else a new empty dict.
    - Fails: never raises; non-dict input yields {}.
    - When-needed: reading nested record/route fields that may be absent or wrong-typed in untrusted JSON.
    """
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    """Defensive coercion of an arbitrary JSON value to a list.

    - Teleology: lets iteration over optional array fields proceed without type guards at every call site.
    - Guarantee: returns `value` unchanged when it is a list, else a new empty list.
    - Fails: never raises; non-list input yields [].
    - When-needed: iterating edges/refs/specimens/receipts that may be absent or wrong-typed in untrusted JSON.
    """
    return value if isinstance(value, list) else []


def _add_error(
    errors: list[dict[str, str]], *, path: str, code: str, message: str
) -> None:
    """Append one structured violation onto the shared errors accumulator.

    - Teleology: uniform violation shape so every check contributes machine-readable {path,code,message} rows.
    - Guarantee: mutates `errors` in place by appending exactly one dict with keys path/code/message.
    - Fails: never raises; returns None.
    - When-needed: locating where a specific error `code` is emitted in the validation receipt.
    """
    errors.append({"path": path, "code": code, "message": message})


def _has_text(row: dict[str, Any], key: str) -> bool:
    """Predicate: does `row[key]` hold a non-empty, non-whitespace string.

    - Teleology: shared definition of "field is meaningfully present as text" across all required-field checks.
    - Guarantee: returns True iff row[key] is a str whose stripped value is non-empty, else False.
    - Fails: never raises; missing key or non-str value yields False.
    - When-needed: confirming the text-presence rule behind a missing_*_field violation.
    """
    return isinstance(row.get(key), str) and bool(row[key].strip())


def _has_ref_list(row: dict[str, Any], key: str) -> bool:
    """Predicate: does `row[key]` hold a list with at least one non-empty string ref.

    - Teleology: shared definition of "ref list is meaningfully populated" for source_refs/validator_refs/anti_claims.
    - Guarantee: returns True iff row[key] is a list containing >=1 non-empty stripped str, else False.
    - Fails: never raises; missing key, non-list, or all-blank/non-str entries yield False.
    - When-needed: confirming the rule behind a missing_*_ref_list violation.
    """
    refs = row.get(key)
    return isinstance(refs, list) and any(isinstance(ref, str) and ref.strip() for ref in refs)


def _is_planned_target_status(status: Any) -> bool:
    """Predicate: is an edge target_status an explicitly-planned (deferred) status.

    - Teleology: lets planned targets be tolerated as a distinct class from unresolved targets.
    - Guarantee: returns True iff status is a str starting with a PLANNED_TARGET_PREFIXES prefix ("planned_"), else False.
    - Fails: never raises; non-str status yields False.
    - When-needed: distinguishing edge_target_unresolved_not_planned from a tolerated planned edge.
    """
    return isinstance(status, str) and status.startswith(PLANNED_TARGET_PREFIXES)


def _validator_ref_is_inspectable(ref: str) -> bool:
    """Predicate: does a validator_ref name a runnable command or inspectable test path.

    - Teleology: enforces that at least one cited validator is actually checkable, not prose-only.
    - Guarantee: returns True iff ref starts with "microcosm "/"python "/"./"/"tests/" OR contains "::test_" or "/tests/".
    - Fails: never raises; refs that match none of those shapes yield False.
    - When-needed: confirming the rule behind specimen_validator_not_inspectable / activation_validator_not_inspectable.
    """
    prefixes = ("microcosm ", "python ", "./", "tests/")
    return ref.startswith(prefixes) or "::test_" in ref or "/tests/" in ref


def _required_fields(standard: dict[str, Any]) -> list[str]:
    """Extract the declared required-field names from a loaded standard document.

    - Teleology: drives per-record required-field checks off the standard, not a hardcoded list.
    - Guarantee: returns the list of str entries in standard["required_fields"], dropping non-str/absent entries.
    - Fails: never raises; missing or non-list required_fields yields [].
    - When-needed: seeing which fields a concept/mechanism standard demands per record.
    - Escalates-to: standards/std_microcosm_concept.json, standards/std_microcosm_mechanism.json (required_fields).
    """
    return [field for field in _as_list(standard.get("required_fields")) if isinstance(field, str)]


def _receipt_ref_path(root: Path, ref: str) -> Path | None:
    """Resolve a "receipts/..."-shaped ref to an on-disk path under root.

    - Teleology: gate which receipt refs name a real file vs. an opaque declared id, without touching disk.
    - Guarantee: returns root/ref when ref starts with "receipts/", else None (no existence check performed here).
    - Fails: never raises; non-"receipts/" refs yield None.
    - When-needed: understanding how a receipt_ref is mapped onto the filesystem before custody indexing.
    """
    if not ref.startswith("receipts/"):
        return None
    return root / ref


def _record_receipt_index(root: Path, receipt_refs: list[str]) -> dict[str, set[str]]:
    """Build a ref -> {covered record_id} index from on-disk receipt files.

    - Teleology: precompute which records each file-backed receipt actually covers, so custody checks are O(1).
    - Guarantee: returns a dict mapping each existing, parseable "receipts/" ref to the non-empty set of record_id
      strings found under its "record_receipts"; refs with no covered ids are omitted.
    - Fails: never raises; missing files, unreadable/malformed JSON, and non-"receipts/" refs are silently skipped.
    - When-needed: auditing why a record is/ isn't considered receipt-covered (custody index source of truth).
    - Escalates-to: receipts/*.json record_receipts[].record_id under the substrate root.
    """
    indexed: dict[str, set[str]] = {}
    for ref in receipt_refs:
        path = _receipt_ref_path(root, ref)
        if path is None or not path.is_file():
            continue
        try:
            payload = _load_json(path)
        except Exception:
            continue
        ids: set[str] = set()
        for row in _as_list(payload.get("record_receipts")):
            if isinstance(row, dict) and isinstance(row.get("record_id"), str):
                ids.add(row["record_id"])
        if ids:
            indexed[ref] = ids
    return indexed


def _receipt_refs_cover_record(
    *,
    root: Path,
    record_id: str,
    receipt_refs: list[str],
    receipt_index: dict[str, set[str]],
) -> bool:
    """Decide whether any of a record's receipt_refs custody-covers that record.

    - Teleology: custody oracle — a record is bound only if it cites a covering declared or file-backed receipt.
    - Guarantee: returns True if any ref starts with "receipt." (declared id, trusted) OR names an existing
      "receipts/" file that either has no indexed record set or includes record_id; else False.
    - Fails: never raises; returns False when no ref satisfies coverage.
    - When-needed: confirming the rule behind concept_receipt_not_bound / mechanism_receipt_not_bound.
    - Non-goal: does not verify receipt contents/authenticity; a "receipt."-prefixed declared ref is trusted as-is.
    """
    for ref in receipt_refs:
        if ref.startswith("receipt."):
            return True
        path = _receipt_ref_path(root, ref)
        if path is not None and path.is_file() and (
            not receipt_index.get(ref) or record_id in receipt_index.get(ref, set())
        ):
            return True
    return False


def _validate_record_edges(
    *,
    record: dict[str, Any],
    path: Path,
    errors: list[dict[str, str]],
) -> None:
    """Validate every forward relationship edge on a concept/mechanism record.

    - Teleology: enforce that each owned edge carries justification and either resolves or is explicitly planned.
    - Guarantee: appends to `errors` for each non-object edge (edge_not_object), each edge missing
      justification.source_ref/summary (edge_missing_justification), and each edge whose target_status is neither
      in RESOLVED_TARGET_STATUSES nor planned (edge_target_unresolved_not_planned).
    - Fails: never raises; reports violations via the errors accumulator (returns None).
    - When-needed: tracing edge_* violations for a specific record's relationships.edges.
    """
    for index, edge in enumerate(_as_list(_as_dict(record.get("relationships")).get("edges"))):
        edge_path = f"{path.as_posix()}.relationships.edges[{index}]"
        if not isinstance(edge, dict):
            _add_error(
                errors,
                path=edge_path,
                code="edge_not_object",
                message="Relationship edge must be an object.",
            )
            continue
        justification = _as_dict(edge.get("justification"))
        if not _has_text(justification, "source_ref") or not _has_text(
            justification, "summary"
        ):
            _add_error(
                errors,
                path=f"{edge_path}.justification",
                code="edge_missing_justification",
                message="Forward source edge must carry justification.source_ref and justification.summary.",
            )
        status = edge.get("target_status")
        if status not in RESOLVED_TARGET_STATUSES and not _is_planned_target_status(status):
            _add_error(
                errors,
                path=f"{edge_path}.target_status",
                code="edge_target_unresolved_not_planned",
                message="Unresolved concept/mechanism-owned edge targets must resolve or be marked planned.",
            )


def _validate_mechanism_population_binding(
    *,
    record: dict[str, Any],
    path: Path,
    errors: list[dict[str, str]],
) -> None:
    """Validate a mechanism record's mechanism_payload.population_binding completeness.

    - Teleology: ensure every mechanism declares the full population binding (role, concept pair, source refs,
      transformation, state/proof effect, omission receipt, anti-claims, validator refs).
    - Guarantee: for each key in MECHANISM_POPULATION_BINDING_REQUIRED, appends to `errors` when missing —
      ref-list keys (source_refs/anti_claims/validator_refs) -> missing_mechanism_population_binding_ref_list,
      omission_receipt without .drilldown -> missing_mechanism_population_binding_omission,
      any other text key blank -> missing_mechanism_population_binding_field.
    - Fails: never raises; reports violations via the errors accumulator (returns None).
    - When-needed: tracing missing_mechanism_population_binding_* violations for a mechanism record.
    """
    binding = _as_dict(_as_dict(record.get("mechanism_payload")).get("population_binding"))
    for key in MECHANISM_POPULATION_BINDING_REQUIRED:
        if key in {"source_refs", "anti_claims", "validator_refs"}:
            if not _has_ref_list(binding, key):
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.mechanism_payload.population_binding.{key}",
                    code="missing_mechanism_population_binding_ref_list",
                    message=f"Mechanism population binding must carry non-empty {key}.",
                )
        elif key == "omission_receipt":
            if not _has_text(_as_dict(binding.get(key)), "drilldown"):
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.mechanism_payload.population_binding.omission_receipt",
                    code="missing_mechanism_population_binding_omission",
                    message="Mechanism population binding must carry omission_receipt.drilldown.",
                )
        elif not _has_text(binding, key):
            _add_error(
                errors,
                path=f"{path.as_posix()}.mechanism_payload.population_binding.{key}",
                code="missing_mechanism_population_binding_field",
                message="Mechanism population binding must name role, concept pair, transformation shape, and state/proof effect.",
            )


def _validate_concept_cluster_flag(
    *,
    record: dict[str, Any],
    path: Path,
    errors: list[dict[str, str]],
) -> bool:
    """Validate a concept record's cluster_flag projection row against its relationships.

    - Teleology: ensure the at-a-glance cluster_flag is source-backed, self-consistent, and not source-authority.
    - Guarantee: appends to `errors` for a missing flag (concept_cluster_flag_missing), each missing required field
      (concept_cluster_flag_missing_field), kind!="concept", concept_id!=record id, specimen_id mismatch,
      each mechanism/principle/axiom count that disagrees with relationships refs, a drilldown not under
      "concepts/", and an authority_boundary lacking "not_source_authority"; returns True iff a flag was present
      (even if it has field-level violations), False when the flag is absent.
    - Fails: never raises; reports violations via the errors accumulator and signals presence via the bool return.
    - When-needed: tracing concept_cluster_flag_* violations, or whether a concept contributed to cluster_flag_count.
    - Non-goal: a present, consistent cluster_flag is a projection row only; it does not make the flag source authority.
    """
    flag = _as_dict(record.get("cluster_flag"))
    flag_path = f"{path.as_posix()}.cluster_flag"
    if not flag:
        _add_error(
            errors,
            path=flag_path,
            code="concept_cluster_flag_missing",
            message="Concept records must expose a source-backed cluster_flag row.",
        )
        return False
    for key in CONCEPT_CLUSTER_FLAG_REQUIRED:
        if flag.get(key) in (None, "", []):
            _add_error(
                errors,
                path=f"{flag_path}.{key}",
                code="concept_cluster_flag_missing_field",
                message=f"Concept cluster_flag is missing required field {key}.",
            )
    relationships = _as_dict(record.get("relationships"))
    count_expectations = {
        "mechanism_count": len(_as_list(relationships.get("mechanism_refs"))),
        "principle_count": len(_as_list(relationships.get("principle_refs"))),
        "axiom_count": len(_as_list(relationships.get("axiom_refs"))),
    }
    if flag.get("kind") != "concept":
        _add_error(
            errors,
            path=f"{flag_path}.kind",
            code="concept_cluster_flag_kind_mismatch",
            message="Concept cluster_flag.kind must be concept.",
        )
    if flag.get("concept_id") != record.get("id"):
        _add_error(
            errors,
            path=f"{flag_path}.concept_id",
            code="concept_cluster_flag_id_mismatch",
            message="Concept cluster_flag.concept_id must match the record id.",
        )
    if flag.get("specimen_id") != relationships.get("specimen_id"):
        _add_error(
            errors,
            path=f"{flag_path}.specimen_id",
            code="concept_cluster_flag_specimen_mismatch",
            message="Concept cluster_flag.specimen_id must match relationships.specimen_id.",
        )
    for key, expected in count_expectations.items():
        if flag.get(key) != expected:
            _add_error(
                errors,
                path=f"{flag_path}.{key}",
                code="concept_cluster_flag_count_mismatch",
                message=f"Concept cluster_flag.{key} must match relationships refs.",
            )
    if not str(flag.get("drilldown", "")).startswith("concepts/"):
        _add_error(
            errors,
            path=f"{flag_path}.drilldown",
            code="concept_cluster_flag_drilldown_not_local",
            message="Concept cluster_flag.drilldown must point at the local concept record.",
        )
    if "not_source_authority" not in str(flag.get("authority_boundary", "")):
        _add_error(
            errors,
            path=f"{flag_path}.authority_boundary",
            code="concept_cluster_flag_authority_boundary_missing",
            message="Concept cluster_flag must state that it is not source authority.",
        )
    return True


def _validate_record_corpus(root: Path, errors: list[dict[str, str]]) -> dict[str, Any]:
    """Validate the whole on-disk concept/mechanism record corpus and return a count summary.

    - Teleology: corpus-level gate — every concept/ and mechanism/ record must be active, required-field complete,
      receipt-covered, validator-cited, edge-clean, and mutually back-referenced.
    - Guarantee: loads the two standards, every concepts/*.json and mechanisms/*.json, builds a receipt index, then
      appends to `errors` for: draft/seed status (concept_not_active/mechanism_not_active), missing required fields,
      uncovered receipts, absent validator_refs, bad cluster_flags, edge violations, and unresolved or
      non-back-referenced concept<->mechanism refs; returns a dict of counts (concept/mechanism, draft_or_seed,
      empty_receipt, planned/unresolved target, receipt_ref, cluster_flag).
    - Fails: raises (via _load_json) if a standard or any record/receipt JSON is missing or malformed; otherwise
      reports all record-level problems through the errors accumulator.
    - When-needed: diagnosing any record-corpus violation or interpreting record_validation counts in the receipt.
    - Escalates-to: standards/std_microcosm_concept.json, standards/std_microcosm_mechanism.json, concepts/*.json,
      mechanisms/*.json under the substrate root.
    - Non-goal: validates record shape and cross-references only; does not authorize release or assert proof correctness.
    """
    concept_standard = _load_json(root / "standards/std_microcosm_concept.json")
    mechanism_standard = _load_json(root / "standards/std_microcosm_mechanism.json")
    concept_required = _required_fields(concept_standard)
    mechanism_required = _required_fields(mechanism_standard)
    concept_paths = sorted((root / "concepts").glob("*.json"))
    mechanism_paths = sorted((root / "mechanisms").glob("*.json"))
    concepts = {path: _load_json(path) for path in concept_paths}
    mechanisms = {path: _load_json(path) for path in mechanism_paths}
    concept_ids = {row.get("id") for row in concepts.values()}
    mechanism_ids = {row.get("id") for row in mechanisms.values()}
    receipt_refs = sorted(
        {
            ref
            for row in [*concepts.values(), *mechanisms.values()]
            for ref in _as_list(row.get("receipt_refs"))
            if isinstance(ref, str) and ref.strip()
        }
    )
    receipt_index = _record_receipt_index(root, receipt_refs)

    draft_or_seed_count = 0
    empty_receipt_count = 0
    planned_target_count = 0
    unresolved_target_count = 0
    cluster_flag_count = 0

    for path, record in concepts.items():
        record_id = str(record.get("id") or path.stem)
        status = str(record.get("status") or "")
        if status in {"draft", "seed"}:
            draft_or_seed_count += 1
            _add_error(
                errors,
                path=f"{path.as_posix()}.status",
                code="concept_not_active",
                message="Concept records must be active, not draft or seed.",
            )
        for key in concept_required:
            if record.get(key) in (None, "", []):
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.{key}",
                    code="concept_missing_required_field",
                    message=f"Concept record is missing required field {key}.",
                )
        refs = [ref for ref in _as_list(record.get("receipt_refs")) if isinstance(ref, str)]
        if not refs:
            empty_receipt_count += 1
        if not _receipt_refs_cover_record(
            root=root, record_id=record_id, receipt_refs=refs, receipt_index=receipt_index
        ):
            _add_error(
                errors,
                path=f"{path.as_posix()}.receipt_refs",
                code="concept_receipt_not_bound",
                message="Concept record must point to a declared or local receipt that covers this record.",
            )
        if not _has_ref_list(record, "validator_refs"):
            _add_error(
                errors,
                path=f"{path.as_posix()}.validator_refs",
                code="concept_validator_refs_missing",
                message="Concept record must carry validator_refs.",
            )
        if _validate_concept_cluster_flag(record=record, path=path, errors=errors):
            cluster_flag_count += 1
        _validate_record_edges(record=record, path=path, errors=errors)
        for mechanism_id in _as_list(_as_dict(record.get("relationships")).get("mechanism_refs")):
            if mechanism_id not in mechanism_ids:
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.relationships.mechanism_refs",
                    code="concept_mechanism_ref_unresolved",
                    message=f"Concept mechanism ref {mechanism_id} must resolve to a mechanism record.",
                )

    concept_mechanism_refs = {
        str(record.get("id")): set(_as_list(_as_dict(record.get("relationships")).get("mechanism_refs")))
        for record in concepts.values()
    }
    for path, record in mechanisms.items():
        record_id = str(record.get("id") or path.stem)
        status = str(record.get("status") or "")
        if status in {"draft", "seed"}:
            draft_or_seed_count += 1
            _add_error(
                errors,
                path=f"{path.as_posix()}.status",
                code="mechanism_not_active",
                message="Mechanism records must be active, not draft or seed.",
            )
        for key in mechanism_required:
            if record.get(key) in (None, "", []):
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.{key}",
                    code="mechanism_missing_required_field",
                    message=f"Mechanism record is missing required field {key}.",
                )
        refs = [ref for ref in _as_list(record.get("receipt_refs")) if isinstance(ref, str)]
        if not refs:
            empty_receipt_count += 1
        if not _receipt_refs_cover_record(
            root=root, record_id=record_id, receipt_refs=refs, receipt_index=receipt_index
        ):
            _add_error(
                errors,
                path=f"{path.as_posix()}.receipt_refs",
                code="mechanism_receipt_not_bound",
                message="Mechanism record must point to a declared or local receipt that covers this record.",
            )
        if not _has_ref_list(record, "validator_refs"):
            _add_error(
                errors,
                path=f"{path.as_posix()}.validator_refs",
                code="mechanism_validator_refs_missing",
                message="Mechanism record must carry validator_refs.",
            )
        _validate_mechanism_population_binding(record=record, path=path, errors=errors)
        _validate_record_edges(record=record, path=path, errors=errors)
        for edge in _as_list(_as_dict(record.get("relationships")).get("edges")):
            if isinstance(edge, dict):
                status = edge.get("target_status")
                if _is_planned_target_status(status):
                    planned_target_count += 1
                elif status not in RESOLVED_TARGET_STATUSES:
                    unresolved_target_count += 1
        for concept_id in _as_list(_as_dict(record.get("relationships")).get("concept_refs")):
            if concept_id not in concept_ids:
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.relationships.concept_refs",
                    code="mechanism_concept_ref_unresolved",
                    message=f"Mechanism concept ref {concept_id} must resolve to a concept record.",
                )
            elif record_id not in concept_mechanism_refs.get(concept_id, set()):
                _add_error(
                    errors,
                    path=f"{path.as_posix()}.relationships.concept_refs",
                    code="concept_missing_mechanism_backref",
                    message=f"Concept {concept_id} must list mechanism {record_id} back.",
                )

    return {
        "concept_count": len(concept_paths),
        "mechanism_count": len(mechanism_paths),
        "draft_or_seed_status_count": draft_or_seed_count,
        "empty_receipt_ref_count": empty_receipt_count,
        "planned_target_count": planned_target_count,
        "unresolved_target_count": unresolved_target_count,
        "receipt_ref_count": len(receipt_refs),
        "cluster_flag_count": cluster_flag_count,
    }


def _validate_concept_binding(
    *,
    binding: dict[str, Any],
    path: str,
    errors: list[dict[str, str]],
    require_pair_ref: bool,
) -> None:
    """Validate a concept_binding block (in a specimen or activation receipt).

    - Teleology: ensure a concept is populated as a role/relation/payload binding that explicitly rejects glossary-only.
    - Guarantee: appends to `errors` a missing_concept_binding_field for each blank required text field
      (concept_role, relationship_shape, payload_shape_ref, anti_glossary_rule, plus mechanism_pair_ref when
      require_pair_ref is True), and concept_binding_not_anti_glossary when anti_glossary_rule lacks "glossary".
    - Fails: never raises; reports violations via the errors accumulator (returns None).
    - When-needed: tracing missing_concept_binding_field / concept_binding_not_anti_glossary violations.
    """
    required = ["concept_role", "relationship_shape", "payload_shape_ref", "anti_glossary_rule"]
    if require_pair_ref:
        required.append("mechanism_pair_ref")
    for key in required:
        if not _has_text(binding, key):
            _add_error(
                errors,
                path=f"{path}.{key}",
                code="missing_concept_binding_field",
                message="Concept binding must carry role, relation, payload, anti-glossary rule, and mechanism pair when it is an activation receipt.",
            )
    if "glossary" not in str(binding.get("anti_glossary_rule", "")).lower():
        _add_error(
            errors,
            path=f"{path}.anti_glossary_rule",
            code="concept_binding_not_anti_glossary",
            message="Concept binding must explicitly reject glossary-only population.",
        )


def _validate_mechanism_binding(
    *,
    binding: dict[str, Any],
    expected_pair_ref: str,
    path: str,
    errors: list[dict[str, str]],
) -> None:
    """Validate a mechanism_binding block and its back-pointer to the paired concept binding.

    - Teleology: ensure a mechanism is populated as a transformation/proof-effect binding that rejects feature-prose
      and points back at its concept pair.
    - Guarantee: appends to `errors` a missing_mechanism_binding_field for each blank required text field
      (mechanism_role, concept_pair_ref, transformation_shape, state_or_proof_effect, anti_feature_prose_rule),
      mechanism_pair_ref_mismatch when concept_pair_ref != expected_pair_ref, and
      mechanism_binding_not_anti_feature_prose when anti_feature_prose_rule lacks "feature prose".
    - Fails: never raises; reports violations via the errors accumulator (returns None).
    - When-needed: tracing missing_mechanism_binding_field / mechanism_pair_ref_mismatch /
      mechanism_binding_not_anti_feature_prose violations.
    """
    required = [
        "mechanism_role",
        "concept_pair_ref",
        "transformation_shape",
        "state_or_proof_effect",
        "anti_feature_prose_rule",
    ]
    for key in required:
        if not _has_text(binding, key):
            _add_error(
                errors,
                path=f"{path}.{key}",
                code="missing_mechanism_binding_field",
                message="Mechanism binding must carry role, concept pair, transformation, proof effect, and anti-feature-prose rule.",
            )
    if binding.get("concept_pair_ref") != expected_pair_ref:
        _add_error(
            errors,
            path=f"{path}.concept_pair_ref",
            code="mechanism_pair_ref_mismatch",
            message=f"Mechanism binding must point back to {expected_pair_ref}.",
        )
    if "feature prose" not in str(binding.get("anti_feature_prose_rule", "")).lower():
        _add_error(
            errors,
            path=f"{path}.anti_feature_prose_rule",
            code="mechanism_binding_not_anti_feature_prose",
            message="Mechanism binding must explicitly reject feature-prose population.",
        )


def _validate_specimens(route: dict[str, Any], errors: list[dict[str, str]]) -> set[str]:
    """Validate the entry route's population_specimens and return the set of valid specimen ids.

    - Teleology: every population specimen must be a complete, distinct, source-and-validator-backed concept/mechanism pair.
    - Guarantee: appends to `errors` for an empty specimen list (missing_population_specimens), each missing
      specimen_id, each invalid concept/mechanism binding (delegated), collapsed concept==mechanism roles
      (concept_mechanism_roles_collapsed), missing source/validator/anti-claim ref lists (missing_specimen_ref_list),
      no inspectable validator (specimen_validator_not_inspectable), and a missing omission drilldown; returns the
      set of specimen_id strings that carried a stable id.
    - Fails: never raises; reports violations via the errors accumulator and returns the collected id set (empty on no specimens).
    - When-needed: tracing specimen-level violations or learning which specimen ids exist for activation cross-checks.
    """
    specimens = _as_list(route.get("population_specimens"))
    specimen_ids: set[str] = set()
    if not specimens:
        _add_error(
            errors,
            path="concept_mechanism_entry_route.population_specimens",
            code="missing_population_specimens",
            message="Population route must carry at least one specimen.",
        )
        return specimen_ids

    for index, specimen_value in enumerate(specimens):
        specimen = _as_dict(specimen_value)
        specimen_id = str(specimen.get("specimen_id") or f"index_{index}")
        specimen_path = f"population_specimens[{specimen_id}]"
        if not _has_text(specimen, "specimen_id"):
            _add_error(
                errors,
                path=f"{specimen_path}.specimen_id",
                code="missing_specimen_id",
                message="Specimen must carry a stable specimen_id.",
            )
        else:
            specimen_ids.add(specimen["specimen_id"])

        concept_binding = _as_dict(specimen.get("concept_binding"))
        mechanism_binding = _as_dict(specimen.get("mechanism_binding"))
        _validate_concept_binding(
            binding=concept_binding,
            path=f"{specimen_path}.concept_binding",
            errors=errors,
            require_pair_ref=False,
        )
        _validate_mechanism_binding(
            binding=mechanism_binding,
            expected_pair_ref=f"{specimen_id}.concept_binding",
            path=f"{specimen_path}.mechanism_binding",
            errors=errors,
        )
        if concept_binding.get("concept_role") == mechanism_binding.get("mechanism_role"):
            _add_error(
                errors,
                path=specimen_path,
                code="concept_mechanism_roles_collapsed",
                message="Concept and mechanism roles must remain distinct.",
            )
        for key in ("source_refs", "validator_refs", "anti_claims"):
            if not _has_ref_list(specimen, key):
                _add_error(
                    errors,
                    path=f"{specimen_path}.{key}",
                    code="missing_specimen_ref_list",
                    message=f"Specimen must carry non-empty {key}.",
                )
        if not any(
            _validator_ref_is_inspectable(ref)
            for ref in _as_list(specimen.get("validator_refs"))
            if isinstance(ref, str)
        ):
            _add_error(
                errors,
                path=f"{specimen_path}.validator_refs",
                code="specimen_validator_not_inspectable",
                message="Specimen needs at least one runnable or inspectable validator ref.",
            )
        if not _has_text(_as_dict(specimen.get("omission_receipt")), "drilldown"):
            _add_error(
                errors,
                path=f"{specimen_path}.omission_receipt",
                code="missing_omission_drilldown",
                message="Specimen omission receipt must point to a drilldown.",
            )
    return specimen_ids


def _validate_activation_receipts(
    route: dict[str, Any], specimen_ids: set[str], errors: list[dict[str, str]]
) -> list[str]:
    """Validate the entry route's activation_receipts and return the list of valid receipt ids.

    - Teleology: every activation receipt must bind a real pressure to an existing specimen with an allowed residual
      disposition and a self-consistent concept<->mechanism binding, never standing up a parallel concept index.
    - Guarantee: appends to `errors` for an empty receipt list (missing_activation_receipts), each missing
      receipt_id/required field, a selected_specimen_id not in `specimen_ids` (activation_receipt_unknown_specimen),
      a residual_disposition outside ALLOWED_RESIDUAL_DISPOSITIONS (activation_receipt_bad_disposition), a
      concept-index pressure whose authority_boundary fails to reject parallel concept-index authority, invalid
      concept/mechanism bindings (delegated), a mismatched concept->mechanism pair ref, missing validator/anti-claim
      ref lists, no inspectable validator, and a missing omission drilldown; returns the list of receipt_id strings.
    - Fails: never raises; reports violations via the errors accumulator and returns the collected id list.
    - When-needed: tracing activation_receipt_* violations or learning which activation receipt ids were accepted.
    - Non-goal: passing does not authorize a parallel concept index, release readiness, or provider calls — it only
      checks receipt shape and specimen linkage.
    """
    receipts = _as_list(route.get("activation_receipts"))
    receipt_ids: list[str] = []
    if not receipts:
        _add_error(
            errors,
            path="concept_mechanism_entry_route.activation_receipts",
            code="missing_activation_receipts",
            message="Activated population route must record at least one pressure receipt.",
        )
        return receipt_ids

    for index, receipt_value in enumerate(receipts):
        receipt = _as_dict(receipt_value)
        receipt_id = str(receipt.get("receipt_id") or f"index_{index}")
        receipt_path = f"activation_receipts[{receipt_id}]"
        if not _has_text(receipt, "receipt_id"):
            _add_error(
                errors,
                path=f"{receipt_path}.receipt_id",
                code="missing_activation_receipt_id",
                message="Activation receipt must carry a stable receipt_id.",
            )
        else:
            receipt_ids.append(receipt["receipt_id"])
        for key in (
            "pressure_id",
            "classification",
            "selected_specimen_id",
            "source_ref",
            "residual_disposition",
            "reentry_condition",
            "receipt_ref",
            "authority_boundary",
        ):
            if not _has_text(receipt, key):
                _add_error(
                    errors,
                    path=f"{receipt_path}.{key}",
                    code="missing_activation_receipt_field",
                    message="Activation receipt must bind pressure, specimen, source, disposition, reentry, receipt, and authority fields.",
                )
        if receipt.get("selected_specimen_id") not in specimen_ids:
            _add_error(
                errors,
                path=f"{receipt_path}.selected_specimen_id",
                code="activation_receipt_unknown_specimen",
                message="Activation receipt must choose an existing population specimen.",
            )
        if receipt.get("residual_disposition") not in ALLOWED_RESIDUAL_DISPOSITIONS:
            _add_error(
                errors,
                path=f"{receipt_path}.residual_disposition",
                code="activation_receipt_bad_disposition",
                message="Residual disposition must be an allowed projection/retirement/capture state, never a new parallel index.",
            )
        boundary_text = str(receipt.get("authority_boundary", "")).lower().replace("_", " ")
        if "parallel concept index" not in boundary_text and (
            "concept_index" in str(receipt.get("pressure_id", "")).lower()
            or "concept index" in str(receipt.get("pressure_label", "")).lower()
        ):
            _add_error(
                errors,
                path=f"{receipt_path}.authority_boundary",
                code="concept_index_pressure_boundary_missing",
                message="Concept-index pressure receipts must explicitly reject parallel concept-index authority.",
            )
        concept_binding = _as_dict(receipt.get("concept_binding"))
        mechanism_binding = _as_dict(receipt.get("mechanism_binding"))
        _validate_concept_binding(
            binding=concept_binding,
            path=f"{receipt_path}.concept_binding",
            errors=errors,
            require_pair_ref=True,
        )
        _validate_mechanism_binding(
            binding=mechanism_binding,
            expected_pair_ref=f"{receipt_id}.concept_binding",
            path=f"{receipt_path}.mechanism_binding",
            errors=errors,
        )
        if concept_binding.get("mechanism_pair_ref") != f"{receipt_id}.mechanism_binding":
            _add_error(
                errors,
                path=f"{receipt_path}.concept_binding.mechanism_pair_ref",
                code="concept_pair_ref_mismatch",
                message="Activation concept binding must point to the same receipt's mechanism binding.",
            )
        for key in ("validator_refs", "anti_claims"):
            if not _has_ref_list(receipt, key):
                _add_error(
                    errors,
                    path=f"{receipt_path}.{key}",
                    code="missing_activation_ref_list",
                    message=f"Activation receipt must carry non-empty {key}.",
                )
        if not any(
            _validator_ref_is_inspectable(ref)
            for ref in _as_list(receipt.get("validator_refs"))
            if isinstance(ref, str)
        ):
            _add_error(
                errors,
                path=f"{receipt_path}.validator_refs",
                code="activation_validator_not_inspectable",
                message="Activation receipt needs at least one runnable or inspectable validator ref.",
            )
        if not _has_text(_as_dict(receipt.get("omission_receipt")), "drilldown"):
            _add_error(
                errors,
                path=f"{receipt_path}.omission_receipt",
                code="missing_activation_omission_drilldown",
                message="Activation receipt omission receipt must point to a drilldown.",
            )
    return receipt_ids


def _validate_pressure(
    pressure_payload: dict[str, Any] | None, errors: list[dict[str, str]]
) -> bool:
    """Validate that public standard pressure exposes the activation-receipt-loop row and its route refs.

    - Teleology: confirm the public pressure surface actually advertises this validator's activation loop, so the
      requirement is discoverable, not just enforced.
    - Guarantee: when pressure_payload is provided, appends missing_activation_pressure_row if the
      concept_mechanism_requires_activation_receipt_loop row is absent, and activation_pressure_route_ref_missing for
      each required route_ref (the entry-packet activation route + the validator module) not present; returns True iff
      the required pressure row was found, False otherwise.
    - Fails: never raises; returns False when pressure_payload is None or the required row is missing.
    - When-needed: tracing missing_activation_pressure_row / activation_pressure_route_ref_missing, or why
      pressure_checked is False in the receipt.
    - Escalates-to: core/public_standard_pressure.json (concept_mechanism_requires_activation_receipt_loop.route_refs).
    """
    if pressure_payload is None:
        return False
    rows = _as_list(pressure_payload.get("rows"))
    row_by_id = {
        row.get("standard_id"): row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("standard_id"), str)
    }
    row = row_by_id.get("concept_mechanism_requires_activation_receipt_loop")
    if not isinstance(row, dict):
        _add_error(
            errors,
            path="core/public_standard_pressure.rows",
            code="missing_activation_pressure_row",
            message="Public pressure must expose the activation receipt loop.",
        )
        return False
    route_refs = _as_list(row.get("route_refs"))
    required_refs = [
        "atlas/entry_packet.json::concept_mechanism_entry_route.activation_receipts",
        "python -m microcosm_core.validators.concept_mechanism_population",
    ]
    for required_ref in required_refs:
        if required_ref not in route_refs:
            _add_error(
                errors,
                path="core/public_standard_pressure.concept_mechanism_requires_activation_receipt_loop.route_refs",
                code="activation_pressure_route_ref_missing",
                message=f"Activation pressure row must include {required_ref}.",
            )
    return True


def validate_concept_mechanism_population(
    *,
    entry_packet: dict[str, Any],
    pressure_payload: dict[str, Any] | None = None,
    root: Path | None = None,
    command: str = "concept-mechanism-population-validator",
) -> dict[str, Any]:
    """Top-level in-memory validator: route + specimens + activation receipts + pressure (+ optional corpus).

    - Teleology: single public entry that assembles the full concept/mechanism population validation receipt.
    - Guarantee: returns a receipt dict with schema microcosm_concept_mechanism_population_validation_v0,
      status "pass" iff zero errors were accumulated else "blocked", specimen/activation counts and ids,
      pressure_checked, record_validation (only when `root` is given), a constant parallel_index_authorized=False,
      an anti_claim string, and the full errors list; runs corpus validation only when `root` is not None.
    - Fails: never raises for shape violations (they become errors with status "blocked"); propagates _load_json /
      filesystem errors only when corpus validation is triggered with a malformed root.
    - When-needed: the canonical programmatic check of concept/mechanism population; inspect first for status logic.
    - Escalates-to: tests for this module under tests/, and atlas/entry_packet.json::concept_mechanism_entry_route.
    - Non-goal: a "pass" validates route/specimen/receipt/corpus shape only; it does NOT authorize a parallel concept
      index, release readiness, provider calls, or private-data equivalence (see the receipt's anti_claim).
    """
    errors: list[dict[str, str]] = []
    route = _as_dict(entry_packet.get("concept_mechanism_entry_route"))
    if not route:
        _add_error(
            errors,
            path="concept_mechanism_entry_route",
            code="missing_route",
            message="Entry packet must carry concept_mechanism_entry_route.",
        )
    specimen_ids = _validate_specimens(route, errors)
    receipt_ids = _validate_activation_receipts(route, specimen_ids, errors)
    pressure_checked = _validate_pressure(pressure_payload, errors)
    validation_commands = _as_list(route.get("validation_commands"))
    validator_command_present = any(
        isinstance(command_ref, str)
        and "microcosm_core.validators.concept_mechanism_population" in command_ref
        for command_ref in validation_commands
    )
    if not validator_command_present:
        _add_error(
            errors,
            path="concept_mechanism_entry_route.validation_commands",
            code="activation_validator_command_missing",
            message="Validation commands must expose the activation population validator.",
        )
    record_validation = None
    if root is not None:
        record_validation = _validate_record_corpus(root, errors)

    return {
        "schema": "microcosm_concept_mechanism_population_validation_v0",
        "status": "pass" if not errors else "blocked",
        "command": command,
        "specimen_count": len(specimen_ids),
        "activation_receipt_count": len(receipt_ids),
        "activation_receipt_ids": receipt_ids,
        "pressure_checked": pressure_checked,
        "record_validation": record_validation,
        "parallel_index_authorized": False,
        "anti_claim": (
            "This validator checks specimen/activation route shape only; it does not "
            "authorize a parallel concept index, release readiness, provider calls, or "
            "private-data equivalence."
        ),
        "errors": errors,
    }


def validate_paths(
    *,
    entry_packet_path: Path,
    pressure_path: Path | None,
    out: Path | None,
    root: Path | None = None,
    command: str,
) -> dict[str, Any]:
    """Filesystem wrapper: load the entry packet (and optional pressure), validate, optionally write the receipt.

    - Teleology: disk-facing adapter over validate_concept_mechanism_population for CLI and file-based callers.
    - Guarantee: loads entry_packet_path and (if given) pressure_path, returns the validation receipt; when `out` is
      provided, also creates `out` and writes the receipt to out/concept_mechanism_population_validation.json
      (indent=2, sort_keys=True, trailing newline).
    - Fails: raises (via _load_json) if the entry packet or pressure JSON is missing/malformed; raises on filesystem
      errors creating `out` or writing the receipt.
    - When-needed: running the validator against on-disk inputs or persisting a receipt artifact.
    - Escalates-to: the written out/concept_mechanism_population_validation.json receipt; the entry packet at entry_packet_path.
    """
    pressure_payload = _load_json(pressure_path) if pressure_path else None
    receipt = validate_concept_mechanism_population(
        entry_packet=_load_json(entry_packet_path),
        pressure_payload=pressure_payload,
        root=root,
        command=command,
    )
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / "concept_mechanism_population_validation.json").write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return receipt


def main(argv: list[str] | None = None) -> int:
    """CLI entry: parse --root/--entry-packet/--pressure/--out, validate, print receipt, return exit code.

    - Teleology: command-line front door (`python -m microcosm_core.validators.concept_mechanism_population`).
    - Guarantee: resolves defaults (root, root/atlas/entry_packet.json, root/core/public_standard_pressure.json when
      present), runs validate_paths, prints the receipt JSON to stdout, and returns 0 iff receipt["status"]=="pass"
      else 1.
    - Fails: returns 1 on a "blocked" receipt; argparse exits the process on bad args; propagates load/write errors
      from validate_paths (missing/malformed inputs, unwritable --out).
    - When-needed: invoking or scripting this validator from the shell, or interpreting its process exit code.
    - Escalates-to: validate_paths and validate_concept_mechanism_population in this module.
    """
    parser = argparse.ArgumentParser(
        description="Validate Microcosm concept/mechanism population specimens and activation receipts."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--entry-packet", type=Path)
    parser.add_argument("--pressure", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    entry_packet_path = args.entry_packet or root / "atlas/entry_packet.json"
    pressure_path = args.pressure
    if pressure_path is None and (root / "core/public_standard_pressure.json").is_file():
        pressure_path = root / "core/public_standard_pressure.json"
    command = (
        "python -m microcosm_core.validators.concept_mechanism_population "
        f"--root {root} --entry-packet {entry_packet_path}"
        + (f" --pressure {pressure_path}" if pressure_path else "")
        + (f" --out {args.out}" if args.out else "")
    )
    receipt = validate_paths(
        entry_packet_path=entry_packet_path,
        pressure_path=pressure_path,
        out=args.out,
        root=root,
        command=command,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
