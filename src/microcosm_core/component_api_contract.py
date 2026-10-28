"""Public HTTP contract. No index reads, application state or execution imports.

The transport imports these limits; OpenAPI uses the same values. Response
schemas specify the supported client fields and permit additive index fields.
The index owner still validates the complete evidence records at startup.
"""
from __future__ import annotations

CONTRACT_VERSION = "1.5.0"
API_SCHEMA = "plectis_component_http_v1"
API_PREFIX = "/api/v1"
MAX_PAGE_SIZE = 100
MAX_GRAPH_DEPTH = 3
MAX_GRAPH_EDGES = 500
MAX_SEARCH_LENGTH = 160
MAX_OVERVIEW_BYTES = 8 * 1024 * 1024
MAX_GUIDE_BYTES = 256 * 1024
MAX_PLAIN_BYTES = 8 * 1024
MAX_GUIDES_BYTES = 1024 * 1024
CLASSIFICATION_FIELDS = ("family", "evidence_class", "real_substrate_disposition", "truth_accounting_bucket")


def _object(**properties):
    return {"type": "object", "required": list(properties), "properties": properties}


def _ref(name):
    return {"$ref": "#/components/schemas/" + name}


def _array(item):
    return {"type": "array", "items": item}


def _page(item):
    return _object(items=_array(item), total={"type": "integer", "minimum": 0},
                   limit={"type": "integer", "minimum": 1, "maximum": MAX_PAGE_SIZE},
                   next_cursor={"type": ["string", "null"]})


def openapi_document():
    """Return a fresh standard OpenAPI 3.1 document suitable for client tools."""
    text = {"type": "string"}
    record = {"type": "object", "additionalProperties": True}
    status = _object(status=text)
    classification = _object(**{key: text for key in CLASSIFICATION_FIELDS})
    evidence = _object(index_state={"const": "retained_generated_snapshot"},
                       current_backend_binding=status, fresh_prover=status, fresh_replay=status)
    card = _object(title=text, summary=text, primary_guide_ref=text,
                   formal_subclaim_ids=_array(text), assurance_facets=record, evidence=record)
    claim = _object(claim_id=text, organ_id=text, claim_ceiling=text, card=card)
    proof = _object(proof=record, modeled_contracts=_array(record), index_state=text,
                    current_backend_binding=status, fresh_prover=status)
    proof["properties"].update(component_ids=_array(text), claim_ids=_array(text))
    core = _object(core_id=text, proof_id=text, statement=text,
        assumptions=_array(text), limits=_array(text), specification_refs=_array(text),
        entry_theorem_refs=_array(text), retained_verification=record,
        current_binding=record, fresh_prover_result=record, generated_refs=_array(text),
        negative_controls=_array(record), public_caller_refs=_array(text))
    artifact = _object(artifact_id=text, ref=text, kind=text,
                       availability={"enum": ["available", "unavailable"]})
    artifact["properties"].update(href=text, reason=text, sha256=text)
    schemas = {
        "SnapshotRevision": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "ComponentSummary": _object(organ_id=text, claim_id=text, title=text, summary=text,
                                     evidence_class=text, formal_subclaim_ids=_array(text),
                                     classification=classification),
        "Claim": claim, "Proof": proof, "Artifact": artifact, "Core": core,
        "Component": _object(component_id=text, claim=_ref("Claim"), guide=record, replay=record,
                              subclaims=_array(record), proofs=_array(_ref("Proof")),
                              artifacts=_array(_ref("Artifact")), evidence_state=evidence,
                              classification=classification),
        "Metadata": _object(index_schema=text, component_count={"type": "integer"},
                             proof_count={"type": "integer"}, receipt_count={"type": "integer"},
                             component_filters=record, graph=record, evidence_state=evidence,
                             limits=record, contract=_object(openapi=text, version=text),
                             execution={"const": "unavailable_over_http"}),
        "Coverage": _object(schema_version={"const": "plectis_component_coverage_v1"},
                             denominator=record, component_presence=record,
                             evidence_class_counts=record, whole_claim_coverage=record,
                             fresh_results=record, notes=_array(text)),
        "Graph": _object(root=_object(type=text, id=text), depth={"type": "integer"},
                          max_edges={"type": "integer"}, direction={"enum": ["in", "out", "both"]},
                          edge_kind={"type": ["string", "null"]}, truncated={"type": "boolean"},
                          nodes=_array(_object(type=text, id=text, record=record)),
                          edges=_array(_object(kind=text, **{"from": text, "from_type": text,
                                                           "to": text, "to_type": text}))),
        "Error": _object(schema_version={"const": API_SCHEMA}, error=_object(code=text, message=text)),
    }
    schemas.update({
        "ArtifactBinding": _object(ref=text, sha256={"type": "string", "pattern": "^[0-9a-f]{64}$"}),
        "SourceExcerpt": _object(ref=text, kind=text, name=text,
            line_start={"type": "integer", "minimum": 1}, line_end={"type": "integer", "minimum": 1},
            text={"type": "string", "maxLength": 24 * 1024}),
        "ChangedLine": _object(line={"type": "integer", "minimum": 1}, original={"type": ["string", "null"]}, mutated={"type": ["string", "null"]}),
        "NegativeControl": _object(source_ref=text, retained_result=record, fresh_result=record),
        "VerificationTask": _object(name=text, kind=text),
        "DoctrineNode": _object(id=text, title=text, plain=text, kind=text, source_ref=text),
        "TypedRelation": _object(from_id=text, to_id=text, kind={"const": "imports_runner"},
            source_ref=text, line={"type": "integer", "minimum": 1}, source_sha256=text),
        "DoctrineEdge": _object(from_id=text, to_id=text, kind=text, source_ref=text),
        "SourceRevision": _object(status={"enum": ["unknown", "recorded"]}, commit={"type": ["string", "null"]},
            dirty={"type": ["boolean", "null"]}, repository={"type": ["string", "null"]},
            exact_source_links={"type": "boolean"}),
        "ReceiptSummary": _object(ref=text, availability={"enum": ["available", "unavailable"]},
            created_at={"type": ["string", "null"]}, date_status={"enum": ["recorded", "unrecorded"]},
            artifact_sha256={"type": ["string", "null"]},
            availability_reason={"type": ["string", "null"]},
            recorded_fields={"type": "object", "additionalProperties": {"type": ["string", "integer", "boolean"]}}),
        "FilterValue": _object(value=text, component_count={"type": "integer", "minimum": 0}),
    })
    schemas["Guide"] = _object(ref=text,
        sha256={"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
        text={"type": ["string", "null"], "maxLength": MAX_GUIDE_BYTES},
        availability={"enum": ["available", "unrecorded"]},
        plain={"type": ["string", "null"], "maxLength": MAX_PLAIN_BYTES},
        plain_availability={"enum": ["available", "unrecorded"]})
    for name in ("Component", "Core", "Proof"):
        schemas[name]["properties"]["guide"] = _ref("Guide")
    schemas["ComponentSummary"]["properties"].update(
        plain={"type": ["string", "null"], "maxLength": MAX_PLAIN_BYTES},
        plain_availability={"enum": ["available", "unrecorded"]})
    schemas["SourceExcerpt"]["properties"].update(source_sha256=_ref("SnapshotRevision"),
        text_sha256=_ref("SnapshotRevision"))
    schemas["SourceExcerpt"]["required"].extend(["source_sha256", "text_sha256"])
    schemas["NegativeControl"]["properties"].update(description=text,
        changed_lines=_array(_ref("ChangedLine")), source_sha256=text,
        description_basis=text, changed_lines_sha256=text)
    schemas["FilterValue"]["properties"].update(label=text, description=text, label_basis=text)
    schemas["Core"]["properties"].update(artifact_bindings=_array(_ref("ArtifactBinding")),
        negative_controls=_array(_ref("NegativeControl")))
    proof_record = {"type": "object", "properties": {
        "component_ids": _array(text), "claim_ids": _array(text),
        "guide": _ref("Guide"),
        "excerpts": _array(_ref("SourceExcerpt")),
        "negative_controls": _array(_ref("NegativeControl")),
        "retained_verification": {"type": "object", "properties": {
            "tasks": _array(_ref("VerificationTask")), "task_names_status": text, "tasks_availability": text, "tasks_reason": text}}}}
    schemas["Proof"]["properties"]["proof"] = proof_record
    schemas["Metadata"]["properties"].update(source_revision=_ref("SourceRevision"),
        component_filters=_object(**{key: _array(_ref("FilterValue")) for key in CLASSIFICATION_FIELDS}))
    schemas["Artifact"]["properties"]["summary"] = _ref("ReceiptSummary")
    schemas["Explorer"] = {"type": "object", "properties": {
        "source_revision": _ref("SourceRevision"),
        "guides": {"type": "object", "maxProperties": 128, "additionalProperties": _ref("Guide")},
        "doctrine": _object(nodes=_array(_ref("DoctrineNode")), edges=_array(_ref("DoctrineEdge"))),
        "cores": _array(_ref("Core")), "ownership_example": record,
        "typed_relations": _object(status=text, edges=_array(_ref("TypedRelation")),
            unavailable_component_ids=_array(text), reason=text),
        "receipt_summaries": _array(_ref("ReceiptSummary"))}}
    schemas["Component"]["properties"].update(
        requirements_reviews=_object(status=text, records=_array(record)),
        claim_clause_coverage=_object(status=text, claim_text_sha256=text,
            clauses=_array(record), mapped_clause_count={"type": ["integer", "null"], "minimum": 0},
            whole_claim_coverage=text))
    schemas["LocalSavedRun"] = _object(component_id=text, run_id=text, recorded_status=text,
        admission=_object(recorded_accepted={"type": "boolean"}, rechecked_accepted={"type": "boolean"},
            basis={"const": "saved_host_observations"}), summary_sha256=_ref("SnapshotRevision"),
        receipt_sha256={"type": ["string", "null"]}, source_identity=_ref("SnapshotRevision"),
        current_policy_binding={"const": "matches_current_registry_policy"},
        indexed_registry_binding={"const": "matches_indexed_registry_bytes"},
        current_source_binding=_object(status={"const": "unknown"}, reason=text),
        input_freshness=_object(status={"const": "unknown"}),
        recorded_time=_object(status={"const": "unrecorded"}),
        fresh_execution=_object(status={"const": "not_run_by_server"}))
    schemas["LocalRuns"] = _object(status={"enum": ["disabled", "loaded"]},
        evidence_kind={"const": "explicit_local_saved_run"},
        runs={"type": "array", "maxItems": 32, "items": _ref("LocalSavedRun")},
        observation_authenticity={"const": "trusted_local_files_not_authenticated"},
        fresh_execution=_object(status={"const": "not_run_by_server"}),
        assessment_time_basis={"const": "server_startup_only"})
    schemas["Metadata"]["properties"]["local_runs"] = {"type": "object", "properties": {
        **{key: value for key, value in schemas["LocalRuns"]["properties"].items() if key != "runs"},
        "run_count": {"type": "integer", "minimum": 0, "maximum": 32}}}
    schemas["OverviewComponent"] = _object(**schemas["ComponentSummary"]["properties"],
        proof_ids=_array(text), receipt_refs=_array(_ref("Artifact")), wires_to=_array(text),
        doctrine_ref_ids=_array(text), route_ids=_array(text))
    schemas["Overview"] = _object(components=_array(_ref("OverviewComponent")),
        kernels=_array(_ref("Proof")), receipts=_array(_ref("Artifact")),
        wiring=_array(record), coverage=_ref("Coverage"), cores=_array(_ref("Core")), explorer=_ref("Explorer"), local_runs=_ref("LocalRuns"))
    schemas["MapReceiptSummary"] = _object(
        created_at={"type": ["string", "null"]}, date_status={"enum": ["recorded", "unrecorded"]},
        availability_reason={"type": ["string", "null"]},
        recorded_fields={"type": "object", "properties": {
            "status": {"type": ["string", "integer", "boolean"]},
            "fixture_id": {"type": ["string", "integer", "boolean"]},
            "case_count": {"type": ["string", "integer", "boolean"]}}})
    schemas["MapReceiptRef"] = _object(artifact_id=text, ref=text, kind=text,
        availability={"enum": ["available", "unavailable"]})
    schemas["MapReceiptRef"]["properties"].update(reason=text, summary=_ref("MapReceiptSummary"))
    schemas["MapOverviewComponent"] = _object(**{
        **schemas["OverviewComponent"]["properties"], "receipt_refs": _array(_ref("MapReceiptRef"))})
    schemas["MapOverview"] = _object(**{
        key: value for key, value in schemas["Overview"]["properties"].items() if key not in {"receipts", "wiring"}})
    schemas["MapOverview"]["properties"]["components"] = _array(_ref("MapOverviewComponent"))
    schemas["MapOverview"]["properties"]["cores"] = {
        **_array(_ref("Core")), "description": "Top-level core records in retained explorer.cores order when present."}
    sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    rule_id = {"type": "string", "pattern": "^(AX|P|AP)-[0-9]{1,3}$"}
    rule_kind = {"enum": ["axiom", "principle", "anti_principle"]}
    texts = _array(text)
    schemas["DoctrineSource"] = _object(ref=text, sha256=sha)
    schemas["AxiomObligation"] = _object(obligation_id=text, predicate=text, required={"type": "boolean"},
        declared_status=text, computed_status=text, witness_component_ids=texts,
        witness_surfaces=texts, negative_case_codes=texts, witness_gaps=texts)
    schemas["AxiomDetail"] = _object(formal_clause=text, lineage=texts, anti_axiom=text,
        routing=_object(basis={"const": "authored_routing_registry"}, source_ref=text, witness_strength=text,
            witness_component_ids=texts, witness_surfaces=texts, negative_case_codes=texts),
        obligations=_array(_ref("AxiomObligation")),
        support=_object(basis={"const": "index_time_computed"}, checker_id=text, verdict=text,
            hand_stamped_witness_strength=text, hand_stamped_strong_not_certifiable={"type": "boolean"},
            strong_blocked_reasons=texts))
    schemas["DoctrineReader"] = _object(basis={"const": "authored_reader_enrichment"}, source_ref=text,
        plain=text, analogy=_object(text=text, maps=_array(_object(doctrine=text, analogy=text)), boundary=text),
        why_it_matters=text, potential_misread=text, governs=text, requires=text, refuses=text,
        example=_object(text=text, component_ids=texts), counterexample=text,
        enforced_in_component_ids=texts, does_not_prove=text)
    schemas["DoctrineNode"]["properties"].update(id=rule_id, kind=rule_kind, reader=_ref("DoctrineReader"),
        statement={"type": "string", "maxLength": 4000}, statement_sha256=sha, axiom=_ref("AxiomDetail"))
    schemas["DoctrineNode"]["required"].extend(["statement", "statement_sha256", "reader"])
    related = {"rests_on": _array(rule_id), "violates": _array(rule_id),
               "principles": _array(rule_id), "failure_modes": _array(rule_id)}
    schemas["DoctrineRule"] = _object(id=rule_id, kind=rule_kind, title=text, plain=text, source_ref=text,
        component_ids=texts, cited_by_count={"type": "integer", "minimum": 0},
        witness_component_ids=texts, **related, support_verdict={"type": ["string", "null"]},
        reader_plain=text, enforced_in_component_ids=texts)
    schemas["DoctrineCitation"] = _object(component_id=text, ref_kind={"enum": ["axiom", "principle"]},
        basis={"const": "authored_atlas_row"}, source_ref=text)
    schemas["Doctrine"] = _object(rules=_array(_ref("DoctrineRule")), edges=_array(_ref("DoctrineEdge")),
        sources=_array(_ref("DoctrineSource")), counts=_object(**{key: {"type": "integer", "minimum": 0}
            for key in ("axiom", "principle", "anti_principle", "citations")}))
    schemas["DoctrineRuleDetail"] = {"allOf": [_ref("DoctrineNode"), _object(component_ids=texts,
        cited_by_count={"type": "integer", "minimum": 0}, citations=_array(_ref("DoctrineCitation")), **related)]}
    schemas["Explorer"]["properties"]["doctrine"] = _object(schema_version={"const": "plectis_explorer_doctrine_v2"},
        sources=_array(_ref("DoctrineSource")), nodes=_array(_ref("DoctrineNode")), edges=_array(_ref("DoctrineEdge")))
    schemas["Metadata"]["properties"]["doctrine_count"] = {"type": "integer", "minimum": 0}
    for name in ("Doctrine", "DoctrineRuleDetail"):
        schemas[name + "Response"] = _object(schema_version={"const": API_SCHEMA},
                                              snapshot_revision=_ref("SnapshotRevision"), data=_ref(name))
    schemas["Error"]["properties"]["snapshot_revision"] = _ref("SnapshotRevision")
    for name in ("ComponentSummary", "Claim", "Proof", "Artifact", "Core"):
        schemas[name + "Page"] = _page(_ref(name))
    for name in ("Metadata", "ComponentSummaryPage", "Component", "ClaimPage", "Claim",
                 "ProofPage", "Proof", "ArtifactPage", "Coverage", "Graph", "Overview", "MapOverview", "CorePage", "Core", "LocalRuns"):
        schemas[name + "Response"] = _object(schema_version={"const": API_SCHEMA},
                                              snapshot_revision=_ref("SnapshotRevision"), data=_ref(name))

    schemas["OverviewSelectionResponse"] = {"anyOf": [_ref("OverviewResponse"), _ref("MapOverviewResponse")]}

    def parameter(name, schema, description="", *, required=False, location="query"):
        return {"name": name, "in": location, "required": required,
                "schema": schema, "description": description}

    pagination = [parameter("limit", {"type": "integer", "minimum": 1, "maximum": MAX_PAGE_SIZE, "default": 25}),
                  parameter("cursor", {"type": "string", "maxLength": 512},
                            "Opaque token. Preserve the query and page size; restart on 409.")]
    conditional = parameter("If-None-Match", text, "Response ETag for conditional GET or HEAD.", location="header")
    filter_parameters = [parameter(name, text, "Select a value advertised by metadata.component_filters.")
                         for name in CLASSIFICATION_FIELDS]
    routes = [
        ("", "metadata", "MetadataResponse", []),
        ("/overview", "overview", "OverviewSelectionResponse", [parameter("view", {"enum": ["map"]},
            "Omit for the complete overview. map removes duplicated collections and limits receipt summaries to map fields.")]),
        ("/components", "listComponents", "ComponentSummaryPageResponse", [
            *filter_parameters, parameter("q", {"type": "string", "minLength": 1, "maxLength": MAX_SEARCH_LENGTH},
                "Trimmed, case-insensitive literal substring of ID, title or summary. No regex or ranking."), *pagination]),
        ("/components/{organ_id}", "getComponent", "ComponentResponse", [
            parameter("organ_id", {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"}, required=True, location="path")]),
        ("/claims", "listClaims", "ClaimPageResponse", pagination),
        ("/claims/{claim_id}", "getClaim", "ClaimResponse", [
            parameter("claim_id", {"type": "string", "pattern": "^claim::[a-z][a-z0-9_]*$"}, required=True, location="path")]),
        ("/proofs", "listProofs", "ProofPageResponse", pagination),
        ("/proofs/{proof_id}", "getProof", "ProofResponse", [
            parameter("proof_id", {"type": "string", "pattern": "^proof::dafny::[a-z][a-z0-9_]*$"}, required=True, location="path")]),
        ("/receipts", "listReceipts", "ArtifactPageResponse", [parameter("component", text), *pagination]),
        ("/local-runs", "localSavedRuns", "LocalRunsResponse", []),
        ("/cores", "listCores", "CorePageResponse", pagination),
        ("/cores/{core_id}", "getCore", "CoreResponse", [
            parameter("core_id", {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"}, required=True, location="path")]),
        ("/coverage", "coverage", "CoverageResponse", []),
        ("/doctrine", "listDoctrine", "DoctrineResponse", []),
        ("/doctrine/{rule_id}", "getDoctrineRule", "DoctrineRuleDetailResponse", [
            parameter("rule_id", {"type": "string", "pattern": "^(AX|P|AP)-[0-9]{1,3}$"}, required=True, location="path")]),
        ("/graph", "graph", "GraphResponse", [
            parameter("type", text, "Use a node type declared in metadata.graph.", required=True),
            parameter("id", {"type": "string", "maxLength": 1000}, required=True),
            parameter("depth", {"type": "integer", "minimum": 1, "maximum": MAX_GRAPH_DEPTH, "default": 1}),
            parameter("max_edges", {"type": "integer", "minimum": 1, "maximum": MAX_GRAPH_EDGES, "default": 100}),
            parameter("direction", {"enum": ["in", "out", "both"], "default": "both"}),
            parameter("edge_kind", text, "Use an edge kind declared in metadata.graph.")]),
        ("/openapi.json", "contract", None, []),
    ]
    paths = {}
    headers = {"ETag": {"schema": text}, "X-Plectis-Snapshot-Revision": {"schema": _ref("SnapshotRevision")}}
    for path, operation, response, parameters in routes:
        schema = _ref(response) if response else _object(openapi={"const": "3.1.0"}, info=record, paths=record)
        success = {"description": "Success. OpenAPI is raw JSON; other routes use the documented envelope.",
                   "headers": headers, "content": {"application/json": {"schema": schema}}}
        errors = {str(code): {"description": description, "content": {"application/json": {"schema": _ref("Error")}}}
                  for code, description in ((400, "Malformed ID, parameters or cursor."),
                      (404, "Unknown route or resource."), (405, "Only GET and HEAD are supported."),
                      (406, "No acceptable response encoding."),
                      (409, "Snapshot changed; restart pagination."), (500, "Bounded internal error."))}
        head_responses = {key: {k: v for k, v in value.items() if k != "content"}
                          for key, value in {"200": success, **errors}.items()}
        unchanged = {"description": "ETag matched; no body.", "headers": headers}
        paths[API_PREFIX + path] = {
            "get": {"operationId": operation, "parameters": [*parameters, conditional],
                    "responses": {"200": success, "304": unchanged, **errors}},
            "head": {"operationId": operation + "Headers", "parameters": [*parameters, conditional],
                     "responses": {**head_responses, "304": unchanged}},
        }
    return {"openapi": "3.1.0", "info": {"title": "Plectis component inspection API", "version": CONTRACT_VERSION,
              "description": "Local read-only snapshot inspection. No execution or fresh verification. "
              "Unknown and repeated query parameters are rejected. Response objects may gain additive fields; "
              "evidence records remain governed by the component index. No CORS or authentication is provided."},
            "servers": [{"url": "/"}], "paths": paths, "components": {"schemas": schemas}}
