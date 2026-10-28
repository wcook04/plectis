"""Static component claim views and explicit current byte checks.

The existing generated CodeLens resource is the sole index. These queries do
not run indexed command strings, import build/proof scripts, invoke a prover,
or promote a model theorem to whole-component correctness.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from microcosm_core import resource_root
from microcosm_core.schemas import read_json_strict, loads_json_strict

INDEX_REF = "receipts/code_lens/code_lens_join_index_v0.json"
SCHEMA = "microcosm_code_lens_join_index_v3"
_ID = re.compile(r"[a-z][a-z0-9_]*\Z")
_SECRET = re.compile(r"sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY")
PUBLIC_TEXT_PATH_RE = re.compile(
    r"(?<![:\w/])/(?!tmp(?:/|[^A-Za-z0-9_.-]|$))[A-Za-z0-9_.-]+(?:/[^\s\"'<>]*)?"
    r"|(?<!\w)[A-Za-z]:[\\/]|\\\\[A-Za-z0-9]|\bfile:", re.IGNORECASE,
)
_BODY_KEYS = {"source_body", "source_text", "docstring", "raw_source", "raw_body", "code_body"}
_SOURCE_FIELDS = {"path", "source_class", "custody_basis", "symbol_count", "real_coverage", "body_specific", "generic_unique", "has_non_goal"}
OWNER_REFS = frozenset({"core/organ_registry.json", "core/organ_atlas.json",
                        "core/paper_module_capsules.json", "core/organ_evidence_classes.json"})
_CONTRACT_FIELDS = {"schema_version", "contract_id", "statement", "input_model", "assumptions", "limits",
                    "specification_refs", "entry_theorem_refs", "component_bindings", "positive_test_ref",
                    "adversarial_test_ref", "mutant_refs", "formal_readme_ref"}
_NODE_FIELDS = {
    "source_file": _SOURCE_FIELDS,
    "claim": {"claim_id", "organ_id", "claim_ceiling", "claim_ceiling_restated", "evidence_class", "evidence_strength_rank", "truth_accounting_bucket", "validator_command", "authority_receipt", "card"},
    "organ": {"organ_id", "evidence_class", "evidence_strength_rank", "truth_accounting_bucket", "real_substrate_disposition", "claim_ceiling", "status", "family", "runner_module", "runner_source_ref", "runner_source_resolved", "runner_custody_basis", "runner_specificity", "validator_command", "receipt_count", "authority_receipt"},
    "route": {"task_class", "route_role", "primary_organ_id", "primary_display_name", "first_command", "stop_condition", "allowed_scope", "organ_count"},
    "family": {"family_id", "organ_count"}, "guide": {"guide_id", "ref"},
    "replay": {"organ_id", "span", "input_mode", "receipt_name", "runner_ref", "configuration_refs", "native_witness_requested", "declared_route", "replay_id", "input_ref", "command", "command_scope", "command_ref", "fresh_receipt_template", "execution_status", "prerequisites_status", "prerequisites_ref", "declared_prerequisites", "guide_example", "primary_execution", "last_result", "last_result_selection"},
    "subclaim": {"subclaim_id", "schema_version", "contract_id", "statement", "input_model", "assumptions", "limits", "specification_refs", "entry_theorem_refs", "component_bindings", "positive_test_ref", "adversarial_test_ref", "mutant_refs", "formal_readme_ref", "descriptor_origin", "contract_sha256", "requirements_review", "scope"},
    "specification": {"specification_id", "source_ref", "symbol_refs"},
    "proof": {"proof_id", "language", "module", "metadata_ref", "entry_theorem_refs", "retained_verification", "current_binding", "fresh_prover_result", "generated_refs", "adapter_ref", "trusted_host_refs", "negative_controls"},
    "artifact": {"artifact_id", "ref", "original_ref", "path", "kind", "availability", "reason", "href", "sha256", "symbol", "symbol_kind", "identity_status"},
}


class UnknownComponent(ValueError):
    """The requested ID is absent from the validated registered universe."""


def _safe(value):
    masked = value.replace("<run>", "RUN").replace("<slug>", "SLUG") if isinstance(value, str) else value
    if isinstance(value, str) and (_SECRET.search(value) or PUBLIC_TEXT_PATH_RE.search(masked)):
        raise ValueError("private text in public component index")
    if isinstance(value, dict):
        if set(value) & _BODY_KEYS:
            raise ValueError("source body field in component index")
        for key, child in value.items():
            _safe(key)
            _safe(child)
    elif isinstance(value, list):
        for child in value:
            _safe(child)


def _path(reference):
    if type(reference) is not str or not reference:
        raise ValueError("invalid index reference")
    path = reference.split("::", 1)[0].split("#", 1)[0]
    pure = PurePosixPath(path)
    if (pure.is_absolute() or str(pure) != path or ".." in pure.parts
            or not path or "\\" in path or ":" in path or any(ord(c) < 32 for c in reference)):
        raise ValueError("escaping index reference")
    return path


def _by(rows, field):
    if type(rows) is not list:
        raise ValueError("missing index node list")
    result = {}
    for row in rows:
        key = row.get(field) if type(row) is dict else None
        if type(key) is not str or not key or key in result:
            raise ValueError("duplicate or invalid index identity")
        result[key] = row
    return result


def _keys(value, fields, label):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError("invalid or unbounded " + label)


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _component_facets(index, organ_id, native_records):
    claim = next(row for row in index["nodes"]["claim"] if row["organ_id"] == organ_id)
    organ = next(row for row in index["nodes"]["organ"] if row["organ_id"] == organ_id)
    replay = next(row for row in index["nodes"]["replay"] if row["organ_id"] == organ_id)
    subclaims = [row for row in index["nodes"]["subclaim"] if row["subclaim_id"] in claim["card"]["formal_subclaim_ids"]]
    proof_ids = {edge["to"] for edge in index["edges"] if edge["from"] in claim["card"]["formal_subclaim_ids"]
                 and edge["kind"] == "has_retained_formal_proof"}
    proofs = [row for row in index["nodes"]["proof"] if row["proof_id"] in proof_ids]
    controls = [copy.deepcopy(control) for proof in proofs for control in proof["negative_controls"]]
    tests = sorted({ref for row in subclaims for binding in row["component_bindings"] for ref in binding["test_refs"]})
    consumers = sorted({ref for row in subclaims for binding in row["component_bindings"] for ref in binding["runtime_refs"]})
    return {
        "classification": {"family": organ["family"], "evidence_class": claim["evidence_class"],
                           "real_substrate_disposition": organ["real_substrate_disposition"],
                           "truth_accounting_bucket": claim["truth_accounting_bucket"],
                           "capability_refs": sorted({edge["to"] for edge in index["edges"] if edge["from"] == organ_id
                                                      and edge["kind"] == "grounded_in_doctrine" and edge.get("ref_kind") == "mechanism"})},
        "formal_contract": {"status": "partial" if subclaims else "unknown", "subclaim_ids": claim["card"]["formal_subclaim_ids"],
                            "proof_ids": sorted(proof_ids), "scope": "selected modeled computations only; whole claim not exhaustively mapped"},
        "whole_claim": {"status": "unknown", "coverage_basis": "not_exhaustively_mapped"},
        "generated_runtime_binding": {"status": "recorded_index_binding" if proofs else "unrecorded",
                                      "generated_refs": sorted({ref for proof in proofs for ref in proof["generated_refs"]}),
                                      "consumer_refs": consumers, "assessment_time_basis": "index_generation_only"},
        "native_verification": {"retained_metadata_proof_ids": sorted(proof_ids),
                                "source_sha256": {proof["proof_id"]: proof["current_binding"]["source_sha256"] for proof in proofs},
                                "model_prover_execution_receipt_refs": [], "model_prover_execution_receipt_status": "unrecorded_in_public_index",
                                "historical_native_records": copy.deepcopy(native_records),
                                "fresh_prover_status": "not_run_by_index"},
        "mutation_controls": {"status": "recorded_expected_failures" if controls else "unrecorded", "controls": controls,
                              "fresh_status": "not_run_by_index"},
        "host_tests": {"status": "linked_not_run" if tests else "unrecorded", "refs": tests},
        "replay": {"status": "configured_not_run", "replay_id": replay["replay_id"],
                   "last_result": copy.deepcopy(replay["last_result"]), "last_result_selection": replay["last_result_selection"],
                   "fresh_status": "not_run_by_index"},
        "requirements_review": {"status": "unrecorded"},
        "model_limits": {"assumptions": [row["assumptions"] for row in subclaims], "limits": [row["limits"] for row in subclaims]},
    }


def _coverage_from_facets(index):
    claims = index["nodes"]["claim"]
    count = len(claims)
    facets = {row["organ_id"]: row["card"]["assurance_facets"] for row in claims}

    def metric(ids, kind, **extra):
        ids = sorted(set(ids))
        return {"numerator": len(ids), "denominator": count, "percentage": round(100 * len(ids) / count, 1),
                "component_ids": ids, "kind": kind, **extra}

    classes = {}
    for row in claims:
        classes[row["evidence_class"]] = classes.get(row["evidence_class"], 0) + 1
    return {"schema_version": "plectis_component_coverage_v1",
            "denominator": {"kind": "registered_component_ids", "count": count,
                            "source_ref": "core/organ_registry.json#implemented_organs"},
            "component_presence": {
                "narrow_domain_contracts": metric([oid for oid, row in facets.items() if row["formal_contract"]["subclaim_ids"]], "selected modeled computation presence, not code/line coverage"),
                "generated_runtime_bindings": metric([oid for oid, row in facets.items() if row["generated_runtime_binding"]["generated_refs"]], "recorded generated-kernel/consumer linkage"),
                "retained_proof_metadata": metric([oid for oid, row in facets.items() if row["native_verification"]["retained_metadata_proof_ids"]], "retained Dafny metadata, not a fresh all-kernel run", proof_record_count=len(index["nodes"]["proof"])),
                "index_time_hash_bindings": metric([oid for oid, row in facets.items() if row["native_verification"]["source_sha256"]], "proof source/generated bytes checked only at index generation"),
                "source_linked_mutation_controls": metric([oid for oid, row in facets.items() if row["mutation_controls"]["controls"]], "source-linked controls with retained expected-failure metadata", record_count=sum(len(row["mutation_controls"]["controls"]) for row in facets.values())),
                "configured_replay_routes": metric(list(facets), "runner/input/output configuration only, not execution or success"),
                "historical_lean_receipt_observations": metric([oid for oid, row in facets.items() if row["native_verification"]["historical_native_records"]], "historical public receipt tool/native-mode observations, not current proof of the Python organ"),
                "available_authority_artifacts": metric([row["organ_id"] for row in claims if row["card"]["evidence"]["authority_availability"] == "available"], "declared saved authority artifact availability, not current mechanism success")},
            "evidence_class_counts": dict(sorted(classes.items())),
            "whole_claim_coverage": {"status": "not_exhaustively_mapped", "numerator": None, "denominator": None, "percentage": None},
            "fresh_results": {"prover": {"status": "not_run_by_index", "recorded_count": 0},
                              "replay": {"status": "not_run_by_index", "recorded_count": 0}},
            "notes": ["Presence categories may overlap; do not add their percentages.",
                      "Whole-claim coverage is unknown, not zero failures among registered components.",
                      "Host-test links, retained metadata, byte binding and fresh verification are distinct facets."]}


def coverage_view(index):
    validate_index(index)
    return copy.deepcopy(_coverage_from_facets(index))


def _nested_schema(index):
    _keys(index, {"schema_version", "export_band", "source_bodies_exported", "generated_from", "nodes", "edges",
                  "graph", "rollup", "authority_ceiling", "non_goals", "assurance"}
          | ({"explorer"} if "explorer" in index else set()), "index fields")
    _keys(index["graph"], {"edge_kinds", "edge_kind_counts", "edge_semantics", "resolved_edge_classes",
                          "deferred_edge_classes", "atlas_plane_present", "route_plane_present", "leak_guard"}, "graph fields")
    if set(index["generated_from"]) - {"python_lens", "organ_registry", "organ_atlas", "agent_task_routes", "claim_assurance", "component_descriptions"}:
        raise ValueError("unknown generated-source fields")
    if any(type(value) is not str for key, value in index["generated_from"].items() if key != "claim_assurance"):
        raise ValueError("generated-source references must be compact strings")
    _keys(index["generated_from"]["claim_assurance"], {"registry", "evidence_classes", "guide_authority",
                                                       "formal_contracts", "replay_configuration"}, "assurance source fields")
    _keys(index["graph"]["leak_guard"], {"values_dropped"}, "leak guard")
    known_edges = {"asserts_claim", "emits_receipt", "grounded_in_doctrine", "implemented_by_runner", "member_of_family",
                   "proven_by", "routes_to", "validated_by", "wires_to", "explained_by_primary_guide", "has_replay_configuration",
                   "has_formal_subclaim", "specified_by", "has_retained_formal_proof", "establishes_model_contract",
                   "invokes_named_runner", "uses_execution_input", "configured_by", "has_historical_receipt",
                   "binds_generated_executable", "relies_on_trusted_host", "consumed_at_runtime_hook", "challenged_by_test"}
    if set(index["graph"]["edge_semantics"]) - known_edges:
        raise ValueError("unknown graph semantic fields")
    if any(type(value) is not str or len(value) > 1600 for value in index["graph"]["edge_semantics"].values()):
        raise ValueError("graph semantics must be compact text")
    for row in index["graph"]["deferred_edge_classes"]:
        if type(row) is not dict or set(row) - {"edge_class", "missing", "missing_source_class", "owner_path", "blocked_on", "would_come_from", "re_entry_command"}:
            raise ValueError("unknown deferred graph fields")
        if any(type(value) is not str or len(value) > 1600 for value in row.values()):
            raise ValueError("deferred graph fields must be compact text")
    if "proof_internal_structure" in index["graph"]["resolved_edge_classes"]:
        raise ValueError("contract descriptors do not extract theorem internals")
    _keys(index["assurance"], {"schema_version", "universe_source", "component_count", "formal_subclaim_count", "owner_refs",
                               "optional_unavailable_assets", "fresh_prover_invoked", "replay_executed", "base_lens_evidence",
                               "component_wide_verification_inferred", "human_fields", "canonical_field_provenance", "coverage"}, "assurance fields")
    provenance = index["assurance"]["canonical_field_provenance"]
    _keys(provenance, {"normative_owner_refs", "ignored_cache_fields", "ignored_atlas_class_rows", "retained_lens_fields"}, "canonical field provenance")
    for row in provenance["ignored_cache_fields"]:
        _keys(row, {"organ_id", "node_type", "fields"}, "ignored cache provenance")
    if set(index["assurance"]["owner_refs"]) != OWNER_REFS or len(index["assurance"]["owner_refs"]) != len(OWNER_REFS):
        raise ValueError("canonical owner references are incomplete")
    allowed_rollups = {"organ_count", "organs_with_resolved_runner_source", "source_file_node_count", "claim_node_count",
                       "route_node_count", "family_node_count", "organs_reachable_from_routes", "route_targets_unknown",
                       "edge_count", "runner_custody_split", "formal_subclaim_count", "proof_node_count", "guide_node_count"}
    _keys(index["rollup"], allowed_rollups, "rollup fields")
    if any(type(value) is not int or value < 0 for key, value in index["rollup"].items() if key != "runner_custody_split"):
        raise ValueError("rollups must be nonnegative integer counts")
    if (type(index["rollup"]["runner_custody_split"]) is not dict
            or set(index["rollup"]["runner_custody_split"]) - {"owned", "directory_coupling_marker", "unknown"}
            or any(type(value) is not int or value < 0 for value in index["rollup"]["runner_custody_split"].values())):
        raise ValueError("invalid custody count fields")
    _keys(index["authority_ceiling"], {"release_authorized", "source_body_export_authorized", "static_analysis_authority",
                                     "whole_system_correctness_authorized"}, "authority fields")
    if any(value is not False for value in index["authority_ceiling"].values()):
        raise ValueError("index cannot authorize release or whole-system correctness")
    for row in index["nodes"]["claim"]:
        _keys(row["card"], {"title", "summary", "primary_guide_id", "primary_guide_ref", "registered_runner_ref", "replay_id",
                            "formal_subclaim_ids", "evidence", "requirements_review", "claim_text_sha256", "assurance_facets"}, "claim card")
        _keys(row["card"]["evidence"], {"evidence_class", "authority_receipt_ref", "authority_availability", "receipt_time_basis",
                                        "historical_receipt_refs", "fresh_run_status"}, "claim evidence")
        text_fields = {"title": row["card"]["title"], "summary": row["card"]["summary"],
                       "claim_ceiling": row.get("claim_ceiling"), "claim_ceiling_restated": row.get("claim_ceiling_restated")}
        if any(value is not None and (type(value) is not str or len(value) > 4000) for value in text_fields.values()):
            raise ValueError("claim text must be bounded strings")
        if row["card"]["claim_text_sha256"] != _digest(text_fields):
            raise ValueError("claim text digest mismatch")
        for key in ("evidence_class", "truth_accounting_bucket"):
            if type(row[key]) is not str or not re.fullmatch(r"[a-z][a-z0-9_]*", row[key]):
                raise ValueError("claim evidence labels must be identifiers")
    for row in index["nodes"]["organ"]:
        if row["runner_specificity"] is not None:
            _keys(row["runner_specificity"], {"real_coverage", "body_specific", "generic_unique"}, "runner lens counts")
            if any(type(value) is not int or value < 0 for value in row["runner_specificity"].values()):
                raise ValueError("runner lens metrics must be counts")
        for key in ("evidence_class", "truth_accounting_bucket", "real_substrate_disposition", "status", "family"):
            if row[key] is not None and (type(row[key]) is not str or not re.fullmatch(r"[a-z][a-z0-9_]*", row[key])):
                raise ValueError("organ labels must be identifiers")
        if row["evidence_strength_rank"] is not None and (type(row["evidence_strength_rank"]) is not int or row["evidence_strength_rank"] < 0):
            raise ValueError("evidence rank must be recorded integer metadata")
        if type(row["runner_source_resolved"]) is not bool or type(row["receipt_count"]) is not int or row["receipt_count"] < 0:
            raise ValueError("invalid recorded runner/receipt metadata")
        for key in ("claim_ceiling", "runner_module", "runner_source_ref", "validator_command", "authority_receipt"):
            if row[key] is not None and (type(row[key]) is not str or len(row[key]) > 4000):
                raise ValueError("organ source fields must be bounded strings")
    for row in index["nodes"]["proof"]:
        _keys(row["retained_verification"], {"basis", "verified_tasks", "dafny_version"}, "retained proof")
        if row["retained_verification"]["basis"] != "recorded_metadata":
            raise ValueError("proof basis must be recorded metadata")
        for control in row["negative_controls"]:
            _keys(control, {"source_ref", "source_sha256", "retained_result", "fresh_result"}, "mutation control")
            _keys(control["retained_result"], {"basis", "verified_tasks", "errors"}, "retained negative metadata")
            if (control["fresh_result"] != {"status": "not_run_by_index"}
                    or control["retained_result"]["basis"] != "recorded_metadata"
                    or type(control["retained_result"]["verified_tasks"]) is not int
                    or type(control["retained_result"]["errors"]) is not int
                    or control["retained_result"]["verified_tasks"] < 0 or control["retained_result"]["errors"] <= 0):
                raise ValueError("invalid retained negative result")
    for row in index["nodes"]["subclaim"]:
        if any(type(row[key]) is not str or not row[key].strip() or len(row[key]) > 2400
               for key in ("statement", "input_model", "assumptions", "limits")):
            raise ValueError("formal contract text must be bounded strings")
        if row["contract_sha256"] != _digest({key: row[key] for key in _CONTRACT_FIELDS}):
            raise ValueError("formal contract text digest mismatch")
        for binding in row["component_bindings"]:
            _keys(binding, {"organ_id", "runtime_refs", "test_refs", "primary_guide_ref"}, "subclaim binding")
    for row in index["nodes"]["replay"]:
        if "declared_route" in row:
            _keys(row["declared_route"], {"example_rel", "input_mode", "runner_ref", "receipt_name"}, "declared replay route")
        _keys(row["guide_example"], {"command", "source_ref", "source_field", "scope", "usage", "writes_retained_receipts", "prerequisites_description",
                                    "expected_result_description"}, "guide example")
        _keys(row["primary_execution"], {"kind", "organ_id", "argv", "scope", "output_policy", "input_override_supported",
                                        "implementation_state", "worker_schema"}, "primary execution request")
        request = row["primary_execution"]
        if (request["kind"] != "fixed_component_replay_api" or request["organ_id"] != row["organ_id"]
                or request["argv"] != ["plectis", "component-replay", row["organ_id"]]
                or request["input_override_supported"] is not False):
            raise ValueError("execution request must be the fixed identifier API")
        _keys(row["guide_example"]["prerequisites_description"], {"status", "see"}, "example prerequisites")
        _keys(row["guide_example"]["expected_result_description"], {"status"}, "example expected result")
        prerequisite_fields = ({"description", "source_ref", "availability_status"}
                               if "description" in row["declared_prerequisites"] else {"status", "source_ref"})
        _keys(row["declared_prerequisites"], prerequisite_fields, "replay prerequisites")


def _validate_header(header, facts):
    _keys(header, {"artifact_ref", "artifact_sha256", "availability", "recorded_status", "created_at", "input_mode",
                   "native_observations", "recorded_source_hashes", "freshness", "source_binding"}, "historical result header")
    if header["artifact_ref"] not in facts or header["freshness"] != "historical_saved_artifact" or header["source_binding"] != "not_checked_against_current_replay":
        raise ValueError("invalid historical result reference or freshness")
    fact = facts[header["artifact_ref"]]
    if header["availability"] != fact["availability"] or header["artifact_sha256"] != fact.get("sha256"):
        raise ValueError("historical header identity differs from artifact")
    for key in ("recorded_status", "created_at", "input_mode"):
        if header[key] is not None and (type(header[key]) is not str or len(header[key]) > 200):
            raise ValueError("historical header fields must be compact text")
    _keys(header["native_observations"], {"lean_available", "lake_available", "execution_witness_mode", "verification_performed"}, "native observations")
    for key in ("lean_available", "lake_available", "verification_performed"):
        if header["native_observations"][key] is not None and type(header["native_observations"][key]) is not bool:
            raise ValueError("native observation flags must be explicit booleans")
    mode = header["native_observations"]["execution_witness_mode"]
    if mode is not None and (type(mode) is not str or len(mode) > 200):
        raise ValueError("native observation mode must be compact text")
    if set(header["recorded_source_hashes"]) - {"source_sha256", "source_digest"} or any(
            type(value) is not str or not re.fullmatch("[0-9a-f]{64}", value) for value in header["recorded_source_hashes"].values()):
        raise ValueError("invalid recorded source hash fields")


def validate_index(index):
    if (type(index) is not dict or index.get("schema_version") != SCHEMA
            or index.get("source_bodies_exported") is not False):
        raise ValueError("unsupported component index")
    from microcosm_core.component_explorer_validation import public_text_view
    _safe(public_text_view(index))
    nodes = index.get("nodes", {})
    if set(nodes) != set(_NODE_FIELDS) or any(
            type(row) is not dict or set(row) - fields
            for kind, fields in _NODE_FIELDS.items() for row in nodes[kind]):
        raise ValueError("unknown component-index node fields")
    for kind, fields in _NODE_FIELDS.items():
        if kind not in {"artifact", "replay"} and any(set(row) != fields for row in nodes[kind]):
            raise ValueError("missing required index node fields")
    _nested_schema(index)
    if any(index.get("assurance", {}).get(key) is not False for key in (
            "fresh_prover_invoked", "replay_executed", "component_wide_verification_inferred")):
        raise ValueError("static index cannot assert current execution or whole-component verification")
    organs = _by(nodes.get("organ"), "organ_id")
    claims = _by(nodes.get("claim"), "organ_id")
    if not organs or set(organs) != set(claims) or any(not _ID.fullmatch(oid) for oid in organs):
        raise ValueError("component index coverage defect")
    for oid, claim in claims.items():
        if claim.get("claim_id") != "claim::" + oid or type(claim.get("card")) is not dict:
            raise ValueError("component claim identity defect")
        if claim["card"].get("requirements_review") != {"status": "unrecorded"}:
            raise ValueError("index cannot infer requirements review")
        if claim["card"].get("evidence", {}).get("fresh_run_status") != "not_run_by_index":
            raise ValueError("index cannot assert fresh execution")
        for field in ("claim_ceiling", "evidence_class", "evidence_strength_rank", "truth_accounting_bucket", "validator_command", "authority_receipt"):
            if organs[oid][field] != claim[field]:
                raise ValueError("organ evidence differs from canonical claim fields")
    for row in nodes.get("source_file", []):
        if type(row) is not dict or set(row) - _SOURCE_FIELDS:
            raise ValueError("source-file index fields exceed counts and references")
        _path(row["path"])
        if any(type(row[key]) is not int or row[key] < 0 for key in (
                "symbol_count", "real_coverage", "body_specific", "generic_unique", "has_non_goal")):
            raise ValueError("source-file metrics must be counts")
        if row["source_class"] is not None and (type(row["source_class"]) is not str or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", row["source_class"])):
            raise ValueError("source classification must be a label")
    facts = _by(nodes.get("artifact"), "artifact_id")
    hashes = {}
    for reference, fact in facts.items():
        path = _path(reference)
        if reference != fact.get("ref") or fact.get("availability") not in {"available", "unavailable"}:
            raise ValueError("invalid artifact identity or availability")
        if fact.get("kind") not in {"file", "directory", "historical_asset"}:
            raise ValueError("unknown artifact kind")
        if fact["availability"] == "unavailable":
            if (set(fact) != {"artifact_id", "ref", "original_ref", "kind", "availability", "reason"}
                    or fact["kind"] != "historical_asset" or fact["original_ref"] != reference
                    or fact.get("reason") != "not included in this checkout"):
                raise ValueError("unavailable artifact cannot have a resolved link")
        elif fact.get("href") != path:
            raise ValueError("artifact link differs from identity")
        elif fact["kind"] == "directory":
            _keys(fact, {"artifact_id", "ref", "path", "kind", "availability", "href"}, "directory artifact")
        elif fact["kind"] == "historical_asset":
            _keys(fact, {"artifact_id", "ref", "path", "kind", "availability", "href", "identity_status"}, "historical artifact")
            if fact["identity_status"] != "not_read_by_index":
                raise ValueError("historical receipt identity cannot be inferred")
        elif set(fact) - {"artifact_id", "ref", "path", "kind", "availability", "href", "sha256", "symbol", "symbol_kind"}:
            raise ValueError("unknown file artifact fields")
        if "symbol" in fact and (type(fact["symbol"]) is not str or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.']*", fact["symbol"])):
            raise ValueError("invalid artifact symbol label")
        if "symbol_kind" in fact and fact["symbol_kind"] not in {"python_function", "python_name", "test_function"}:
            raise ValueError("invalid artifact symbol kind")
        if fact.get("kind") == "file":
            digest = fact.get("sha256")
            if type(digest) is not str or not re.fullmatch("[0-9a-f]{64}", digest):
                raise ValueError("invalid artifact hash")
            if hashes.setdefault(path, digest) != digest:
                raise ValueError("inconsistent artifact byte identities")
    for optional in index["assurance"]["optional_unavailable_assets"]:
        original = facts.get(optional.get("ref"), {})
        if optional != {key: value for key, value in original.items() if key != "artifact_id"} or optional.get("availability") != "unavailable":
            raise ValueError("invalid optional unavailable asset")
    proofs = _by(nodes.get("proof"), "proof_id")
    subclaims = _by(nodes.get("subclaim"), "subclaim_id")
    guides = _by(nodes.get("guide"), "guide_id")
    replays = _by(nodes.get("replay"), "organ_id")
    if set(replays) != set(organs):
        raise ValueError("replay configuration coverage defect")
    for key, proof in proofs.items():
        if (not re.fullmatch(r"proof::dafny::[a-z][a-z0-9_]*", key)
                or proof.get("fresh_prover_result") != {"status": "not_run_by_index"}
                or proof.get("current_binding", {}).get("assessment_time_basis") != "index_generation_only"
                or proof.get("current_binding", {}).get("status") != "current_hash_binding_pass"
                or set(proof.get("current_binding", {})) != {"status", "source_sha256", "generated_python", "assessment_time_basis", "checker_ref"}
                or type(proof.get("retained_verification", {}).get("verified_tasks")) is not int
                or proof["retained_verification"]["verified_tasks"] <= 0):
            raise ValueError("invalid retained proof state")
        slug = key.removeprefix("proof::dafny::")
        source = "formal/components/" + slug + "/" + proof["module"] + ".dfy"
        generated = "src/plectis/components/" + slug + "/_generated/"
        manifest = proof["current_binding"]["generated_python"]
        if (proof["metadata_ref"] != "formal/components/" + slug + "/metadata.json"
                or type(manifest) is not dict or set(manifest) != {proof["module"] + ".py", "module_.py", "__main__.py", "System_/__init__.py", "_dafny/__init__.py"}
                or proof["generated_refs"] != [generated + name for name in sorted(manifest)]
                or source not in facts or facts[source].get("sha256") != proof["current_binding"]["source_sha256"]
                or any(ref not in facts or facts[ref].get("sha256") != manifest[ref.removeprefix(generated)] for ref in proof["generated_refs"])):
            raise ValueError("retained proof hashes disagree with indexed artifacts")
        for control in proof["negative_controls"]:
            if control["source_ref"] not in facts or facts[control["source_ref"]].get("sha256") != control["source_sha256"]:
                raise ValueError("mutation source hash differs from indexed artifact")
    for key, row in subclaims.items():
        if (not re.fullmatch(r"subclaim::[a-z][a-z0-9_]*", key)
                or row.get("requirements_review") != {"status": "unrecorded"}):
            raise ValueError("invalid formal subclaim state")
    for claim in claims.values():
        if set(claim["card"]["formal_subclaim_ids"]) - set(subclaims):
            raise ValueError("dangling formal subclaim")
        card = claim["card"]
        if card.get("primary_guide_id") not in guides or guides[card["primary_guide_id"]]["ref"] != card.get("primary_guide_ref"):
            raise ValueError("dangling primary guide")
        replay = replays[claim["organ_id"]]
        name = replay.get("receipt_name")
        if (type(name) is not str or not name or name in {".", ".."}
                or any(c in name for c in "/\\:#") or any(ord(c) < 32 for c in name)
                or replay.get("fresh_receipt_template") != ".microcosm/component-replays/<run>/" + claim["organ_id"] + "/" + name):
            raise ValueError("escaping replay receipt template")
        _validate_header(replay["last_result"], facts)
        if replay["last_result"]["artifact_ref"] != claim["authority_receipt"]:
            raise ValueError("historical replay result is not the declared authority artifact")
        facet = claim["card"]["assurance_facets"]
        native_records = facet.get("native_verification", {}).get("historical_native_records", [])
        owned_receipts = {edge["to"] for edge in index["edges"] if edge["from"] == claim["organ_id"]
                          and edge["kind"] == "emits_receipt"} | {claim["authority_receipt"]}
        if (len({header.get("artifact_ref") for header in native_records}) != len(native_records)
                or any(header.get("artifact_ref") not in owned_receipts for header in native_records)):
            raise ValueError("historical native records must be distinct component-owned receipts")
        for header in native_records:
            _validate_header(header, facts)
            observations = header["native_observations"]
            if not ((observations["lean_available"] is True and observations["lake_available"] is True)
                    or (observations["execution_witness_mode"] == "live_lean_subprocess_verified"
                        and observations["verification_performed"] is True)):
                raise ValueError("historical native facet has no explicit native observation")
        if facet != _component_facets(index, claim["organ_id"], native_records):
            raise ValueError("assurance facets disagree with source graph")
    for key, subclaim in subclaims.items():
        bindings = _by(subclaim.get("component_bindings"), "organ_id")
        parents = {oid for oid, claim in claims.items() if key in claim["card"]["formal_subclaim_ids"]}
        if not bindings or set(bindings) != parents:
            raise ValueError("formal subclaim component binding defect")
    required_files = set(OWNER_REFS)
    required_directories = set()
    historical_refs = set()
    for claim in claims.values():
        card, replay = claim["card"], replays[claim["organ_id"]]
        required_files.update([card["primary_guide_ref"], card["registered_runner_ref"], replay["runner_ref"],
                               replay["command_ref"], replay["prerequisites_ref"], *replay["configuration_refs"]])
        required_directories.add(replay["input_ref"])
        historical_refs.update([card["evidence"]["authority_receipt_ref"], *card["evidence"]["historical_receipt_refs"]])
        if "declared_route" in replay:
            required_files.add(replay["declared_route"]["runner_ref"])
            required_directories.add(replay["declared_route"]["example_rel"])
    for proof in proofs.values():
        required_files.add("formal/components/" + proof["proof_id"].removeprefix("proof::dafny::") + "/" + proof["module"] + ".dfy")
        required_files.update([proof["metadata_ref"], proof["adapter_ref"], proof["current_binding"]["checker_ref"],
                               *proof["trusted_host_refs"], *proof["generated_refs"]])
    for subclaim in subclaims.values():
        required_files.update([subclaim["formal_readme_ref"], subclaim["positive_test_ref"], subclaim["adversarial_test_ref"],
                               *subclaim["specification_refs"], *subclaim["entry_theorem_refs"], *subclaim["mutant_refs"]])
        for binding in subclaim["component_bindings"]:
            required_files.update(binding["runtime_refs"] + binding["test_refs"])
    for reference in required_files:
        if reference not in facts or facts[reference].get("kind") != "file" or facts[reference].get("availability") != "available":
            raise ValueError("required file role cannot be downgraded or unavailable")
    for reference in required_directories:
        if reference not in facts or facts[reference].get("kind") != "directory" or facts[reference].get("availability") != "available":
            raise ValueError("required input directory unavailable")
    for reference, fact in facts.items():
        if fact["kind"] == "directory" and reference not in required_directories:
            raise ValueError("unexpected directory role")
        if fact["kind"] == "historical_asset" and reference not in historical_refs:
            raise ValueError("unexpected historical asset role")
    identities = {"organ": set(organs), "claim": {row["claim_id"] for row in claims.values()},
                  "route": set(_by(nodes["route"], "task_class")), "family": set(_by(nodes["family"], "family_id")),
                  "source_file": set(_by(nodes["source_file"], "path")), "guide": set(_by(nodes["guide"], "guide_id")),
                  "replay": set(_by(nodes["replay"], "replay_id")), "subclaim": set(subclaims), "proof": set(proofs),
                  "specification": set(_by(nodes["specification"], "specification_id")), "artifact": set(facts),
                  "receipt": set(facts)}
    seen = set()
    edge_counts = {}
    for edge in index.get("edges", []):
        if type(edge) is not dict or set(edge) - {"from_type", "from", "to_type", "to", "kind", "ref_kind", "role"}:
            raise ValueError("unknown graph edge fields")
        for side in ("from", "to"):
            kind = edge[side + "_type"]
            if kind not in {"doctrine_ref", "validator_command"} and edge[side] not in identities.get(kind, set()):
                raise ValueError("dangling graph endpoint")
        identity = tuple(sorted(edge.items()))
        if identity in seen:
            raise ValueError("duplicate graph edge")
        seen.add(identity)
        edge_counts[edge["kind"]] = edge_counts.get(edge["kind"], 0) + 1
    if index["graph"]["edge_kind_counts"] != edge_counts or set(index["graph"]["edge_kinds"]) != set(edge_counts):
        raise ValueError("graph edge counts disagree with records")
    if index["assurance"]["coverage"] != _coverage_from_facets(index):
        raise ValueError("coverage aggregates disagree with component facets")
    from microcosm_core.component_annotations import validate_annotations
    validate_annotations(index)
    return index


def load_index(root=None):
    base = Path(root) if root is not None else resource_root.microcosm_root()
    return validate_index(read_json_strict(base / INDEX_REF))


def _guide_view_validated(index, ref, **extra):
    retained = index.get("explorer", {}).get("guides", {}).get(ref)
    if retained is not None:
        return {**extra, **copy.deepcopy(retained)}
    digest = next((row.get("sha256") for row in index["nodes"]["artifact"] if row["ref"] == ref), None)
    if digest is None:
        digest = next((binding["sha256"] for core in index.get("explorer", {}).get("cores", [])
                       for binding in core["artifact_bindings"] if binding["ref"] == ref), None)
    return {**extra, "ref": ref, "sha256": digest, "text": None, "availability": "unrecorded",
            "plain": None, "plain_availability": "unrecorded"}


def _list_components_validated(index, *, evidence_class=None, family=None):
    organs = _by(index["nodes"]["organ"], "organ_id")
    rows = []
    for row in index["nodes"]["claim"]:
        if evidence_class is not None and row["evidence_class"] != evidence_class:
            continue
        if family is not None and organs[row["organ_id"]].get("family") != family:
            continue
        guide = index.get("explorer", {}).get("guides", {}).get(row["card"]["primary_guide_ref"], {})
        rows.append({"plain": guide.get("plain"), "plain_availability": guide.get("plain_availability", "unrecorded"),
                     "organ_id": row["organ_id"], "claim_id": row["claim_id"],
                     "title": row["card"]["title"], "summary": row["card"]["summary"],
                     "evidence_class": row["evidence_class"], "formal_subclaim_ids": row["card"]["formal_subclaim_ids"]})
    return copy.deepcopy(sorted(rows, key=lambda row: row["organ_id"]))


def _claim_view_validated(index, organ_id):
    if type(organ_id) is not str or not _ID.fullmatch(organ_id):
        raise UnknownComponent("invalid component ID")
    row = next((row for row in index["nodes"]["claim"] if row["organ_id"] == organ_id), None)
    if row is None:
        raise UnknownComponent("unknown component ID: " + organ_id)
    return copy.deepcopy(row)


def _proof_view_validated(index, proof_id):
    row = next((row for row in index["nodes"]["proof"] if row["proof_id"] == proof_id), None)
    if row is None:
        raise ValueError("unknown proof ID")
    subclaim_ids = {edge["from"] for edge in index["edges"]
                    if edge["to"] == proof_id and edge["kind"] == "has_retained_formal_proof"}
    contracts = [{key: copy.deepcopy(contract[key]) for key in (
        "subclaim_id", "statement", "input_model", "assumptions", "limits", "specification_refs",
        "entry_theorem_refs", "descriptor_origin", "contract_sha256", "requirements_review")}
        for contract in index["nodes"]["subclaim"] if contract["subclaim_id"] in subclaim_ids]
    claims = [claim for claim in index["nodes"]["claim"]
              if subclaim_ids.intersection(claim["card"]["formal_subclaim_ids"])]
    component_ids = sorted(claim["organ_id"] for claim in claims)
    claim_ids = sorted(claim["claim_id"] for claim in claims)
    proof = copy.deepcopy(row)
    guide_ref = next(contract["formal_readme_ref"] for contract in index["nodes"]["subclaim"]
                     if contract["subclaim_id"] in subclaim_ids)
    guide = _guide_view_validated(index, guide_ref)
    proof.update(component_ids=component_ids, claim_ids=claim_ids, guide=guide)
    details = index.get("explorer", {}).get("proof_details", {}).get(proof_id, {})
    if details:
        proof["excerpts"] = copy.deepcopy(details["excerpts"])
        proof["retained_verification"].update(copy.deepcopy(details["retained_verification_details"]))
        for control in proof["negative_controls"]:
            control.update(copy.deepcopy(details["negative_control_details"][control["source_ref"]]))
    return {"proof": proof, "guide": copy.deepcopy(guide), "component_ids": component_ids, "claim_ids": claim_ids,
            "index_state": "retained_generated_snapshot",
            "modeled_contracts": contracts,
            "current_backend_binding": {"status": "not_checked"},
            "fresh_prover": {"status": "not_recorded_by_index"}}


def _get_component_validated(index, organ_id):
    from microcosm_core.component_annotations import component_annotation_view
    claim = _claim_view_validated(index, organ_id)
    nodes = index["nodes"]
    subclaims = [row for row in nodes["subclaim"] if row["subclaim_id"] in claim["card"]["formal_subclaim_ids"]]
    proof_ids = {edge["to"] for edge in index["edges"] if edge["from"] in {row["subclaim_id"] for row in subclaims}
                 and edge["kind"] == "has_retained_formal_proof"}
    selected = {claim["claim_id"], claim["card"]["primary_guide_id"], claim["card"]["replay_id"],
                *proof_ids, *claim["card"]["formal_subclaim_ids"]}
    references = {claim["card"]["primary_guide_ref"], claim["card"]["registered_runner_ref"], *OWNER_REFS}
    for contract in subclaims:
        references.update([contract["formal_readme_ref"], contract["positive_test_ref"], contract["adversarial_test_ref"],
                           *contract["specification_refs"], *contract["entry_theorem_refs"], *contract["mutant_refs"]])
        for binding in contract["component_bindings"]:
            references.update(binding["runtime_refs"] + binding["test_refs"])
    for proof in nodes["proof"]:
        if proof["proof_id"] in proof_ids:
            references.update([proof["metadata_ref"], proof["adapter_ref"], proof["current_binding"]["checker_ref"],
                               *proof["generated_refs"], *proof["trusted_host_refs"]])
    for edge in index["edges"]:
        if edge["from"] in selected and edge["to_type"] in {"artifact", "receipt"}:
            references.add(edge["to"])
    artifacts = [copy.deepcopy(row) for row in nodes["artifact"] if row["artifact_id"] in references]
    return {"component_id": organ_id, "claim": claim,
            **copy.deepcopy(component_annotation_view(index, organ_id)),
            "guide": _guide_view_validated(index, claim["card"]["primary_guide_ref"], guide_id=claim["card"]["primary_guide_id"]),
            "replay": copy.deepcopy(next(row for row in nodes["replay"] if row["organ_id"] == organ_id)),
            "subclaims": copy.deepcopy(subclaims), "proofs": [_proof_view_validated(index, key) for key in sorted(proof_ids)],
            "artifacts": artifacts,
            "evidence_state": {"index_state": "retained_generated_snapshot",
                               "current_backend_binding": {"status": "not_checked"},
                               "fresh_prover": {"status": "not_recorded_by_index"},
                               "fresh_replay": {"status": "not_recorded_by_index"}}}


def list_components(index, *, evidence_class=None, family=None):
    validate_index(index)
    return _list_components_validated(index, evidence_class=evidence_class, family=family)


def claim_view(index, organ_id):
    validate_index(index)
    return _claim_view_validated(index, organ_id)


def proof_view(index, proof_id):
    validate_index(index)
    return _proof_view_validated(index, proof_id)


def get_component(index, organ_id):
    validate_index(index)
    return _get_component_validated(index, organ_id)


def compile_views(index):
    """Validate once and return detached serving views; execute nothing."""
    validate_index(index)
    return {"list": _list_components_validated(index),
            "by_component": {row["organ_id"]: _get_component_validated(index, row["organ_id"])
                             for row in index["nodes"]["claim"]},
            "by_proof": {row["proof_id"]: _proof_view_validated(index, row["proof_id"])
                         for row in index["nodes"]["proof"]},
            "coverage": copy.deepcopy(_coverage_from_facets(index)),
            "cores": {row["core_id"]: {**copy.deepcopy(row), "guide": _guide_view_validated(index, row["guide_ref"])}
                      for row in index.get("explorer", {}).get("cores", [])},
            "explorer": copy.deepcopy(index.get("explorer", {}))}


def check_component_bindings(index, root, organ_id):
    """Check indexed file bytes now; perform no proof, replay or adequacy review."""
    view = get_component(index, organ_id)
    root = Path(root).resolve()
    refs = {view["claim"]["card"]["primary_guide_ref"], view["claim"]["card"]["registered_runner_ref"],
            view["replay"]["runner_ref"], view["replay"]["input_ref"]}
    refs.update(index["assurance"]["owner_refs"])
    for subclaim in view["subclaims"]:
        refs.update(subclaim["specification_refs"] + subclaim["entry_theorem_refs"] + subclaim["mutant_refs"] +
                    [subclaim["formal_readme_ref"], subclaim["positive_test_ref"], subclaim["adversarial_test_ref"]])
        for binding in subclaim["component_bindings"]:
            refs.update(binding["runtime_refs"] + binding["test_refs"])
    for result in view["proofs"]:
        proof = result["proof"]
        refs.update([proof["metadata_ref"], proof["adapter_ref"], proof["current_binding"]["checker_ref"],
                     *proof["trusted_host_refs"], *proof["generated_refs"]])
    refs.add(view["replay"]["last_result"]["artifact_ref"])
    refs.update(record["artifact_ref"] for record in view["claim"]["card"]["assurance_facets"]["native_verification"]["historical_native_records"])
    facts = _by(index["nodes"]["artifact"], "artifact_id")
    checked, unchecked, mismatches = [], [], []
    captured = {}
    seen = set()
    for reference in sorted(refs):
        fact = facts.get(reference)
        if fact is None:
            raise ValueError("missing indexed artifact")
        relative = _path(reference)
        if relative in seen:
            continue
        seen.add(relative)
        if fact.get("kind") != "file":
            unchecked.append({"ref": reference, "reason": "no indexed file hash; replay observes inputs separately"})
            continue
        path = root / relative
        reason = None
        if not path.resolve().is_relative_to(root) or any(p.is_symlink() for p in (path, *path.parents) if p != root):
            reason = "linked or escaping current artifact"
        elif not path.is_file() or path.stat().st_size > 4_000_000:
            reason = "missing or oversized current artifact"
        else:
            captured[relative] = path.read_bytes()
            if hashlib.sha256(captured[relative]).hexdigest() != fact["sha256"]:
                reason = "current artifact hash differs from retained index"
        if reason:
            mismatches.append({"ref": reference, "reason": reason})
        else:
            checked.append(relative)
    for result in view["proofs"]:
        proof = result["proof"]
        if proof["metadata_ref"] not in captured:
            continue
        metadata = loads_json_strict(captured[proof["metadata_ref"]].decode("utf-8"), "current proof metadata")
        expected = {"source_sha256": proof["current_binding"]["source_sha256"],
                    "generated_python": proof["current_binding"]["generated_python"],
                    "verified_tasks": proof["retained_verification"]["verified_tasks"],
                    "dafny_version": proof["retained_verification"]["dafny_version"]}
        if any(metadata.get(key) != value for key, value in expected.items()):
            mismatches.append({"ref": proof["metadata_ref"], "reason": "proof fields differ from current metadata"})
    if not checked:
        raise ValueError("no required current file bytes were checked")
    return {"component_id": organ_id, "status": "mismatch" if mismatches else "indexed_file_hashes_match",
            "checked_at": datetime.now(timezone.utc).isoformat(), "checked_refs": checked,
            "unchecked_refs": unchecked, "mismatches": mismatches,
            "index_state": "retained_generated_snapshot", "fresh_prover": {"status": "not_run"},
            "fresh_replay": {"status": "not_run"}, "requirements_review": {"status": "unrecorded"},
            "scope": "current bytes for indexed file hashes only; no whole-component verification"}
