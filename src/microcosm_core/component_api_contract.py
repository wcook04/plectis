"""Public HTTP contract. No index reads, application state or execution imports.

The transport imports these limits; OpenAPI uses the same values. Response
schemas specify the supported client fields and permit additive index fields.
The index owner still validates the complete evidence records at startup.
"""
from __future__ import annotations

CONTRACT_VERSION = "1.1.0"
API_SCHEMA = "plectis_component_http_v1"
API_PREFIX = "/api/v1"
MAX_PAGE_SIZE = 100
MAX_GRAPH_DEPTH = 3
MAX_GRAPH_EDGES = 500
MAX_SEARCH_LENGTH = 160
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
    artifact = _object(artifact_id=text, ref=text, kind=text,
                       availability={"enum": ["available", "unavailable"]})
    artifact["properties"].update(href=text, reason=text, sha256=text)
    schemas = {
        "SnapshotRevision": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "ComponentSummary": _object(organ_id=text, claim_id=text, title=text, summary=text,
                                     evidence_class=text, formal_subclaim_ids=_array(text),
                                     classification=classification),
        "Claim": claim, "Proof": proof, "Artifact": artifact,
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
    schemas["Error"]["properties"]["snapshot_revision"] = _ref("SnapshotRevision")
    for name in ("ComponentSummary", "Claim", "Proof", "Artifact"):
        schemas[name + "Page"] = _page(_ref(name))
    for name in ("Metadata", "ComponentSummaryPage", "Component", "ClaimPage", "Claim",
                 "ProofPage", "Proof", "ArtifactPage", "Coverage", "Graph"):
        schemas[name + "Response"] = _object(schema_version={"const": API_SCHEMA},
                                              snapshot_revision=_ref("SnapshotRevision"), data=_ref(name))

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
        ("/coverage", "coverage", "CoverageResponse", []),
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
