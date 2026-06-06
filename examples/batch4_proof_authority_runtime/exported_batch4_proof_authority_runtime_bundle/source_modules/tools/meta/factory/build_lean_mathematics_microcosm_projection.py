#!/usr/bin/env python3
"""Build the dynamic Lean mathematics microcosm projection.

This projection is a live read model over the repo's formal-math lane. It
discovers current Lean projects, formal-math operation receipts, generated
docs, and verification tests, then emits a compact microcosm card for agents.

It does not run Lean, call providers, import external registries, or claim that
any mathematical theorem is solved. Proof authority remains with Lean/Lake,
statement reconciliation, literature review, and the owner receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]

OWNER_ID = "lean_mathematics_microcosm_projection"
BUILDER_REL = "tools/meta/factory/build_lean_mathematics_microcosm_projection.py"
OUTPUT_REL = "state/system_atlas/lean_mathematics_microcosm.json"
RECEIPT_REL = "state/system_atlas/lean_mathematics_microcosm_receipt.json"
DOC_REL = "docs/system_atlas/lean_mathematics_microcosm.generated.md"
FULL_FIDELITY_PACKET_REL = "state/system_atlas/lean_full_fidelity_evidence_packet.json"
FULL_FIDELITY_PACKET_RECEIPT_REL = "state/system_atlas/lean_full_fidelity_evidence_packet_receipt.json"
FULL_FIDELITY_PACKET_DOC_REL = "docs/system_atlas/lean_full_fidelity_evidence_packet.generated.md"
FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL = (
    "state/system_atlas/lean_full_fidelity_evidence_packet_verification_receipt.json"
)
FULL_FIDELITY_PACKET_VERIFICATION_DOC_REL = (
    "docs/system_atlas/lean_full_fidelity_evidence_packet_verification.generated.md"
)
FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL = (
    "state/system_atlas/lean_full_fidelity_evidence_packet_replay_receipt.json"
)
FULL_FIDELITY_PACKET_REPLAY_DOC_REL = (
    "docs/system_atlas/lean_full_fidelity_evidence_packet_replay.generated.md"
)
FULL_FIDELITY_CAPSULE_MANIFEST_REL = (
    "state/system_atlas/lean_full_fidelity_cold_reviewer_capsule_manifest.json"
)
FULL_FIDELITY_CAPSULE_RECEIPT_REL = (
    "state/system_atlas/lean_full_fidelity_cold_reviewer_capsule_receipt.json"
)
FULL_FIDELITY_CAPSULE_DOC_REL = (
    "docs/system_atlas/lean_full_fidelity_cold_reviewer_capsule.generated.md"
)
FULL_FIDELITY_REVIEWER_HANDOFF_ENVELOPE_REL = (
    "state/system_atlas/lean_full_fidelity_reviewer_handoff_envelope.json"
)
FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_REL = (
    "state/system_atlas/lean_full_fidelity_reviewer_handoff_receipt.json"
)
FULL_FIDELITY_REVIEWER_HANDOFF_DOC_REL = (
    "docs/system_atlas/lean_full_fidelity_reviewer_handoff.generated.md"
)
SCHEMA_VERSION = "lean_mathematics_microcosm_projection_v0"
RECEIPT_SCHEMA_VERSION = "lean_mathematics_microcosm_projection_receipt_v0"
CHECK_SCHEMA_VERSION = "lean_mathematics_microcosm_projection_check_v0"
FULL_FIDELITY_PACKET_SCHEMA_VERSION = "lean_full_fidelity_evidence_packet_v0"
FULL_FIDELITY_PACKET_RECEIPT_SCHEMA_VERSION = "lean_full_fidelity_evidence_packet_receipt_v0"
FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_SCHEMA_VERSION = (
    "lean_full_fidelity_evidence_packet_verification_receipt_v0"
)
FULL_FIDELITY_PACKET_REPLAY_RECEIPT_SCHEMA_VERSION = (
    "lean_full_fidelity_evidence_packet_replay_receipt_v0"
)
FULL_FIDELITY_CAPSULE_SCHEMA_VERSION = "lean_full_fidelity_cold_reviewer_capsule_manifest_v0"
FULL_FIDELITY_CAPSULE_RECEIPT_SCHEMA_VERSION = "lean_full_fidelity_cold_reviewer_capsule_receipt_v0"
FULL_FIDELITY_REVIEWER_HANDOFF_SCHEMA_VERSION = "lean_full_fidelity_reviewer_handoff_envelope_v0"
FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_SCHEMA_VERSION = "lean_full_fidelity_reviewer_handoff_receipt_v0"
MICROCOSM_ID = "lean_mathematics_dynamic_microcosm"
FULL_FIDELITY_PACKET_ID = "operator_authorized_lean_full_fidelity_evidence_packet"
FULL_FIDELITY_PACKET_VERIFIER_ID = "lean_full_fidelity_evidence_packet_verifier"
FULL_FIDELITY_PACKET_REPLAY_ID = "lean_full_fidelity_packet_cold_reviewer_replay"
FULL_FIDELITY_CAPSULE_ID = "lean_full_fidelity_cold_reviewer_capsule"
FULL_FIDELITY_REVIEWER_HANDOFF_ID = "lean_full_fidelity_reviewer_handoff"
AUTHORITY_INVARIANT = "Wider disclosure increases inspectability; only verifier-backed receipts increase claim authority."

RELEASE_GATE_REFS: tuple[tuple[str, str], ...] = (
    ("docs/dissemination/public_toggle_readiness_gate_v0.json", "public_toggle_readiness_gate"),
    ("docs/dissemination/release_operator_decision_packet_v0.json", "release_operator_decision_packet"),
    ("docs/dissemination/release_decision_register_v0.json", "release_decision_register"),
    ("docs/dissemination/release_claim_language_gate_v0.json", "release_claim_language_gate"),
    ("docs/dissemination/release_public_toggle_closure_map_v0.json", "release_public_toggle_closure_map"),
)

SOURCE_ROOTS = (
    "formal_math",
    "state/formal_math_research_operations",
    "state/lean_diagnostics",
    "docs/formal_math",
    "system/server/tests",
    "tools/meta/factory",
)

GRAPH_VIEW_KEYS = (
    "dependency_layers",
    "semantic_families",
    "final_theorem_routes",
    "high_degree_nodes",
    "terminal_claims",
    "external_dependencies",
)
GRAPH_VIEW_SCHEMA_VERSION = "lean_mathematics_graph_views_v2"
GRAPH_VIEW_LEGACY_SCHEMA_VERSION = "lean_mathematics_graph_views_v1"
GRAPH_VIEW_REGISTRY = (
    {
        "view_id": "proof_spine_bundle",
        "label": "Proof Spine",
        "layout_policy": "layered_spine_with_branch_bundles",
        "default": True,
        "supports_expand": ["route_step", "layer", "semantic_family", "edge_bundle"],
    },
    {
        "view_id": "semantic_family_map",
        "label": "Semantic Families",
        "layout_policy": "family_clusters_with_route_overlay",
        "default": False,
        "supports_expand": ["semantic_family"],
    },
    {
        "view_id": "condensed_dag",
        "label": "Condensed DAG",
        "layout_policy": "transitive_reduced_layered_dag",
        "default": False,
        "supports_expand": ["edge_bundle", "semantic_family"],
    },
    {
        "view_id": "full_debug_dag",
        "label": "Full DAG",
        "layout_policy": "dense_debug",
        "default": False,
        "supports_expand": [],
    },
)

DIAGNOSTIC_OBSERVATION_ONLY_STATUSES = frozenset({"ENVIRONMENT_BLOCKED"})
DIAGNOSTIC_SOURCE_BOUNDARY_FILTER = {
    "filter_id": "lean_diagnostics_environment_block_observation_filter",
    "excluded_statuses": sorted(DIAGNOSTIC_OBSERVATION_ONLY_STATUSES),
    "projection_participation": "excluded_from_source_fingerprint",
    "reason": (
        "Read-only diagnostics reviews can emit ENVIRONMENT_BLOCKED rows when the Lean/Lake "
        "environment is unavailable. Those rows are useful observation receipts, but they are "
        "not proof-relevant replay/profile receipts and must not stale the Lean microcosm projection."
    ),
}

CERTIFICATE_OBJECT_ROLE_BY_FAMILY = {
    "period_noncollapse_endpoint": (
        "human-facing theorem endpoint: the declaration whose route is being inspected"
    ),
    "local_layer_certificate": (
        "local-layer witness/decomposition family that packages the certificate route toward noncollapse"
    ),
    "canonical_witness_row": "canonical witness rows or case records used as certificate objects",
    "finite_fixture": "generated finite rows and concrete fixture declarations behind the route",
    "component_term_residue": "component-term and residue arithmetic carried by the certificate machinery",
    "orderof_modeq": "orderOf and modular-equivalence facts used to move from certificate data to period facts",
    "valuation_core": "prime-drop, valuation, and factorization core declarations",
    "certificate_structure": "structural witness/certificate objects used by the Lean declarations",
    "other": "supporting declarations not classified into a specific certificate family",
}

ANTI_CLAIMS = (
    "not a proof that every Lean file in the repo compiles",
    "not a claim that any Erdos problem or external conjecture is solved",
    "not a replacement for Lean/Lake, statement reconciliation, or literature review",
    "not release permission or public mathematical authority",
    "not a claim that wider source disclosure upgrades proof authority",
    "not a static registry mirror; rebuild from local source surfaces as they evolve",
)

# ---------------------------------------------------------------------------
# Proof Architecture Atlas + Proof Trace Flight Recorder (wave: proof_atlas_v1)
#
# These surfaces turn the Lean microcosm from "a page about Lean" into a
# navigable proof instrument: the real logical tower of the kernel, plus the
# real per-declaration execution cost mapped from existing Lean `--profile`
# diagnostics. Everything here is generated-projection inspection data, NOT
# proof authority. Conceptual-layer titles and plain-math glosses are
# human-authored descriptive annotations (clearly labelled), never proof claims,
# never statement-reconciliation claims, and never a public-release signal.
# ---------------------------------------------------------------------------

PROOF_ARCHITECTURE_ANNOTATION_AUTHORITY = (
    "human_authored_mathematical_gloss_not_machine_derived; descriptive inspection aid only; "
    "not proof authority, not statement reconciliation, not public-release authorization"
)

# Significance vocabulary for the curated mathematical annotations.
PROOF_ARCHITECTURE_SIGNIFICANCE = (
    "centerpiece",
    "summit",
    "bridge",
    "engine",
    "spine_definition",
    "primitive",
    "edge_case",
    "concrete_endpoint",
)

# Conceptual layer bands, keyed by Lean file basename. A declaration's conceptual
# layer is the last band whose ``line_band_start`` <= its ``line_start``. Keyed by
# basename so the overlay only lights up for files whose architecture has been read
# and curated; every other file falls back to the machine-derived topological
# ``dependency_layers``. ``assignment_method`` is recorded as a heuristic source-line
# band so the projection never over-states how layer membership was derived.
PROOF_ARCHITECTURE_LAYER_BANDS_BY_BASENAME: dict[str, tuple[dict[str, Any], ...]] = {
    "CertificateKernel.lean": (
        {
            "layer_id": "valuation_primitives",
            "ordinal": 0,
            "title": "Valuation & divisibility primitives",
            "line_band_start": 1,
            "summary": (
                "p-adic valuation and divisibility leaf lemmas the whole tower stands on — "
                "e.g. a valuation deficit blocks divisibility."
            ),
            "role": "leaf_primitives",
        },
        {
            "layer_id": "no_prime_drop",
            "ordinal": 1,
            "title": "No-prime-drop from valuation witnesses",
            "line_band_start": 61,
            "summary": "Glues the valuation primitives into the prime-drop criterion that blocks order collapse.",
            "role": "criterion",
        },
        {
            "layer_id": "orderof_bridge",
            "ordinal": 2,
            "title": "order(b mod q) ⇄ modEq ⇄ divisibility bridge",
            "line_band_start": 208,
            "summary": "Moves between the group-theoretic order of b in (ZMod Q)ˣ and elementary q ∣ bⁿ−1 arithmetic.",
            "role": "bridge",
        },
        {
            "layer_id": "lte_valuation_engine",
            "ordinal": 3,
            "title": "Lifting-the-Exponent valuation engine",
            "line_band_start": 317,
            "summary": "The odd-prime LTE machinery: v_q(b^{dk}−1) = v_q(b^d−1) + v_q(k) and its normalized corollaries.",
            "role": "engine",
        },
        {
            "layer_id": "binomial_first_order",
            "ordinal": 4,
            "title": "Explicit binomial first-order expansion",
            "line_band_start": 547,
            "summary": "Constructs the exact first-order q-adic expansion by hand from the binomial theorem (not a black-box LTE).",
            "role": "engine",
        },
        {
            "layer_id": "residue_formula",
            "ordinal": 5,
            "title": "The residue formula (mathematical centerpiece)",
            "line_band_start": 809,
            "summary": (
                "The cross-multiplication identity: the normalized component quotients sum to a q-adic unit. "
                "This is what lets a multi-row certificate prove non-collapse when no single row suffices."
            ),
            "role": "centerpiece",
        },
        {
            "layer_id": "local_layer_certificate",
            "ordinal": 6,
            "title": "Local-layer certificate & per-prime witness",
            "line_band_start": 1126,
            "summary": "The PrimeComponentWitness / LocalLayerCertificate abstraction and the per-prime witness summits.",
            "role": "abstraction",
        },
        {
            "layer_id": "canonical_dispatch_summits",
            "ordinal": 7,
            "title": "Canonical dispatch, 2-adic exception, finite tables, summits",
            "line_band_start": 1708,
            "summary": (
                "Canonical case dispatch, the q=2 (Zsigmondy) exception, the machine-emittable certificate table, "
                "the top family entrypoints, and the concrete worked fixtures."
            ),
            "role": "dispatch_and_summits",
        },
    ),
}

# Conceptual layers assigned by file role rather than line band (generated/concrete files).
PROOF_ARCHITECTURE_FILE_ROLE_LAYERS: tuple[dict[str, Any], ...] = (
    {
        "layer_id": "concrete_instantiation",
        "ordinal": 9,
        "title": "Concrete instantiation",
        "summary": "Machine-generated concrete certificate that instantiates the kernel for a specific (base, period, residue).",
        "role": "concrete_instantiation",
        "match": "path_contains:/GeneratedCertificates/",
    },
    {
        "layer_id": "generated_certificate_tables",
        "ordinal": 8,
        "title": "Generated certificate tables",
        "summary": "Aggregate of machine-emitted finite certificate rows verified against the kernel.",
        "role": "generated_tables",
        "match": "basename:GeneratedCertificates.lean",
    },
    {
        "layer_id": "root_module",
        "ordinal": 10,
        "title": "Root module",
        "summary": "Lake root module that imports the kernel and generated certificates.",
        "role": "root_module",
        "match": "basename:Erdos257PeriodNoncollapse.lean",
    },
)

# Curated plain-math annotations, keyed by Lean declaration name. These light up
# wherever the real declaration names appear. Glosses are human-authored
# descriptions for inspection only (see PROOF_ARCHITECTURE_ANNOTATION_AUTHORITY).
MATHEMATICAL_ANNOTATIONS: dict[str, dict[str, str]] = {
    "primeComponentQuotient": {
        "significance": "spine_definition",
        "conceptual_layer_id": "local_layer_certificate",
        "plain_math": (
            "The per-prime component quotient: b^L−1 with the contribution of prime p normalized out. "
            "The highest-fan-in definition — the upper tower hangs off it."
        ),
    },
    "PrimeComponentWitness": {
        "significance": "spine_definition",
        "conceptual_layer_id": "local_layer_certificate",
        "plain_math": (
            "The per-prime witness predicate: a certificate that prime p does not drop the multiplicative order of b."
        ),
    },
    "valuation_deficit_blocks_dvd": {
        "significance": "primitive",
        "conceptual_layer_id": "valuation_primitives",
        "plain_math": "If the q-adic valuation of M exceeds that of A, then M ∤ A — the highest-reuse leaf lemma.",
    },
    "orderOf_dvd_iff_q_dvd_pow_sub_one": {
        "significance": "bridge",
        "conceptual_layer_id": "orderof_bridge",
        "plain_math": "order(b mod q) ∣ n ⟺ q ∣ bⁿ−1 — the bridge from the group order to elementary divisibility.",
    },
    "odd_prime_order_factorization_pow_sub_one": {
        "significance": "engine",
        "conceptual_layer_id": "lte_valuation_engine",
        "plain_math": (
            "Lifting-the-Exponent: for an odd prime q with d = order(b mod q), "
            "v_q(b^{dk}−1) = v_q(b^d−1) + v_q(k)."
        ),
    },
    "odd_prime_order_pow_sub_one_eq_mul_add_pow_succ": {
        "significance": "engine",
        "conceptual_layer_id": "binomial_first_order",
        "plain_math": (
            "An exact first-order q-adic expansion b^{dk}−1 = q^{m+s}·(unit) + q^{m+s+1}·C, "
            "built by hand from the binomial theorem."
        ),
    },
    "odd_prime_order_residue_formula": {
        "significance": "centerpiece",
        "conceptual_layer_id": "residue_formula",
        "plain_math": (
            "The cross-multiplication residue identity at the heart of the certificate: the normalized "
            "component quotients combine to a fixed residue mod q."
        ),
    },
    "odd_prime_order_residue_formula_not_dvd_sum": {
        "significance": "centerpiece",
        "conceptual_layer_id": "residue_formula",
        "plain_math": (
            "Therefore q does not divide the sum of normalized component quotients — the actual "
            "non-collapse output of the residue engine."
        ),
    },
    "witness_certificate_implies_period_noncollapse": {
        "significance": "summit",
        "conceptual_layer_id": "local_layer_certificate",
        "plain_math": (
            "Given a per-prime valuation-deficit witness for every prime dividing L, the multiplicative "
            "order of b mod Q equals L."
        ),
    },
    "witness_existence_implies_period_noncollapse": {
        "significance": "summit",
        "conceptual_layer_id": "local_layer_certificate",
        "plain_math": (
            "Root summit: if for every prime p ∣ L some PrimeComponentWitness exists, the order equals L "
            "(minimal-prime selection via Nat.find)."
        ),
    },
    "LocalLayerCertificate": {
        "significance": "spine_definition",
        "conceptual_layer_id": "local_layer_certificate",
        "plain_math": "A local-layer certificate object: the structured per-prime decomposition data the kernel verifies.",
    },
    "local_layer_witness_family_implies_period_noncollapse": {
        "significance": "summit",
        "conceptual_layer_id": "canonical_dispatch_summits",
        "plain_math": "Top family entrypoint: a family of local-layer witnesses implies period noncollapse (order = L).",
    },
    "finite_period_noncollapse_from_emitted_certificate_table": {
        "significance": "summit",
        "conceptual_layer_id": "canonical_dispatch_summits",
        "plain_math": (
            "Period noncollapse from a machine-emitted finite certificate table — the entrypoint the "
            "generated certificates target."
        ),
    },
    "finite_period_noncollapse_from_generated_finite_rows": {
        "significance": "summit",
        "conceptual_layer_id": "canonical_dispatch_summits",
        "plain_math": "Period noncollapse from generated finite witness rows.",
    },
    "EmittedCertificateTable": {
        "significance": "spine_definition",
        "conceptual_layer_id": "canonical_dispatch_summits",
        "plain_math": (
            "The machine-emittable finite certificate: per-prime rows a generator emits and the kernel "
            "checks — a certificate-as-data design."
        ),
    },
    "two_adic_pow_sub_one_factorization_odd": {
        "significance": "edge_case",
        "conceptual_layer_id": "canonical_dispatch_summits",
        "plain_math": (
            "2-adic Lifting-the-Exponent for odd base — the q=2 (Zsigmondy) exception the odd-prime "
            "argument cannot cover."
        ),
    },
    "orderOf_b10_mod90909_eq_6_from_emittedCertificate_denNorm": {
        "significance": "concrete_endpoint",
        "conceptual_layer_id": "concrete_instantiation",
        "plain_math": (
            "Concrete instance: the multiplicative order of 10 modulo 90909 is exactly 6, discharged "
            "through the emitted certificate table."
        ),
    },
}

# Declarations that act as proof summits (the family of period-noncollapse endpoints).
PROOF_ARCHITECTURE_SUMMIT_NAMES = tuple(
    name for name, row in MATHEMATICAL_ANNOTATIONS.items() if row["significance"] in {"summit", "concrete_endpoint"}
)

DISCLOSURE_POSTURES: tuple[dict[str, Any], ...] = (
    {
        "posture_id": "public_safe_fixture",
        "label": "Public-safe fixture",
        "disclosure_scope": "Tiny synthetic Lean/Lake witness and public metadata index.",
        "carries": [
            "redacted reproducible fixture",
            "Mathlib-free witness lane",
            "public premise metadata",
            "narrow authority ceiling",
        ],
        "excludes": [
            "private proof bodies",
            "local Mathlib-dependent package substrate",
            "credentials or unrelated private data",
        ],
        "proof_authority_effect": "none; fixture compiles only its scoped public witness",
        "operator_authorization_required": False,
        "source_refs": [
            "microcosm-substrate formal_math_lean_proof_witness",
            "microcosm-substrate lean_std_premise_index",
        ],
    },
    {
        "posture_id": "operator_authorized_full_fidelity",
        "label": "Operator-authorized full fidelity",
        "disclosure_scope": "Real local Lean/Formal-Math substrate when the operator authorizes review.",
        "carries": [
            "Lake root, lean-toolchain, lakefile, and manifest",
            "relevant Lean modules and proof bodies when authorized",
            "target-runner receipts",
            "evidence cells, diagnostics, profile rows, and statement boundary",
            "non-claims and validation receipts",
        ],
        "excludes": [
            "credentials, tokens, secrets, and unrelated private payloads",
            "third-party-confidential material without separate authority",
        ],
        "proof_authority_effect": "none by itself; wider disclosure is evidence, not a stronger claim",
        "operator_authorization_required": True,
        "source_refs": [
            "formal_math/erdos257_period_noncollapse",
            "state/formal_math_research_operations",
            "state/lean_diagnostics",
        ],
    },
    {
        "posture_id": "proof_authority",
        "label": "Proof authority",
        "disclosure_scope": "Claim boundary and validation authority, not an export redaction mode.",
        "carries": [
            "Lean/Lake typechecking",
            "target-runner receipts",
            "axiom/sorry/admit checks",
            "formal evidence cells",
            "statement reconciliation and owner receipts",
        ],
        "excludes": [
            "generated projection prose as proof",
            "static scans as proof authority",
            "operator disclosure permission as proof success",
        ],
        "proof_authority_effect": "sole lane that can upgrade what is claimed, and only through owner checks",
        "operator_authorization_required": False,
        "source_refs": [
            "tools/meta/factory/run_formal_math_erdos257_lean_target_runner.py",
            "state/formal_math_research_operations/formal_evidence_cell_registry.json",
        ],
    },
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_path(path: str | Path, *, repo_root: Path = REPO_ROOT) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _rel(path: str | Path, *, repo_root: Path = REPO_ROOT) -> str:
    candidate = Path(path)
    try:
        return candidate.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _write_json(path: str | Path, payload: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> None:
    target = _repo_path(path, repo_root=repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(payload), ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: str | Path, payload: str, *, repo_root: Path = REPO_ROOT) -> None:
    target = _repo_path(path, repo_root=repo_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")


def _read_json_if_exists(path: str | Path, *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    target = _repo_path(path, repo_root=repo_root)
    if not target.exists():
        return {}
    payload = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {target}")
    return payload


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256(value: Any) -> str:
    text = value if isinstance(value, str) else _canonical_json(value)
    return _sha256_text(text)


def _file_sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _iter_existing_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*") if path.is_file())


def _is_lake_build_path(path: Path) -> bool:
    return ".lake" in path.parts


def _lean_declarations(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern = re.compile(r"^\s*(theorem|lemma|def|structure|class|abbrev|inductive)\s+([A-Za-z0-9_'.]+)")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            header_lines = [line.strip()]
            end_index = index
            for next_index in range(index + 1, min(index + 12, len(lines))):
                next_line = lines[next_index]
                if pattern.match(next_line):
                    break
                if not next_line.strip():
                    break
                header_lines.append(next_line.strip())
                end_index = next_index
                if ":=" in next_line or " where" in next_line:
                    break
            signature_excerpt = " ".join(header_lines)
            if len(signature_excerpt) > 240:
                signature_excerpt = signature_excerpt[:237].rstrip() + "..."
            rows.append(
                {
                    "kind": match.group(1),
                    "name": match.group(2),
                    "line_start": index + 1,
                    "line_end": end_index + 1,
                    "signature_excerpt": signature_excerpt,
                }
            )
    return rows


def _count_token(text: str, token: str) -> int:
    return len(re.findall(rf"\b{re.escape(token)}\b", text))


def _lake_dependencies(manifest_path: Path) -> list[dict[str, str]]:
    if not manifest_path.exists():
        return []
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    packages = payload.get("packages") if isinstance(payload, dict) else None
    if not isinstance(packages, list):
        return []
    rows: list[dict[str, str]] = []
    for package in packages:
        if not isinstance(package, dict):
            continue
        rows.append(
            {
                "name": str(package.get("name") or ""),
                "scope": str(package.get("scope") or ""),
                "url": str(package.get("url") or ""),
                "rev": str(package.get("rev") or package.get("inputRev") or ""),
            }
        )
    return rows


def _module_id_for_lean_file(project_root: Path, lean_file: Path) -> str:
    rel = lean_file.relative_to(project_root).with_suffix("")
    return ".".join(rel.parts)


def _declaration_node_id(project_id: str, module_id: str, name: str) -> str:
    return "d_" + hashlib.sha1(f"{project_id}:{module_id}:{name}".encode("utf-8")).hexdigest()[:12]


def _discover_lean_projects(*, repo_root: Path) -> list[dict[str, Any]]:
    formal_root = _repo_path("formal_math", repo_root=repo_root)
    if not formal_root.exists():
        return []
    lakefiles = [
        path
        for pattern in ("lakefile.toml", "lakefile.lean")
        for path in formal_root.rglob(pattern)
        if not _is_lake_build_path(path)
    ]
    project_roots = sorted({path.parent for path in lakefiles})
    rows: list[dict[str, Any]] = []
    for root in project_roots:
        project_id = root.name
        lean_files = sorted(path for path in root.rglob("*.lean") if not _is_lake_build_path(path))
        declaration_rows: list[dict[str, Any]] = []
        declaration_counts: Counter[str] = Counter()
        sorry_count = 0
        admit_count = 0
        axiom_count = 0
        for lean_file in lean_files:
            text = lean_file.read_text(encoding="utf-8")
            declarations = _lean_declarations(text)
            for declaration in declarations:
                module_id = _module_id_for_lean_file(root, lean_file)
                declaration_rows.append(
                    {
                        "file": _rel(lean_file, repo_root=repo_root),
                        "module_id": module_id,
                        "kind": declaration["kind"],
                        "name": declaration["name"],
                        "node_id": _declaration_node_id(project_id, module_id, declaration["name"]),
                        "line_start": declaration["line_start"],
                        "line_end": declaration["line_end"],
                        "signature_excerpt": declaration["signature_excerpt"],
                    }
                )
                declaration_counts[declaration["kind"]] += 1
            sorry_count += _count_token(text, "sorry")
            admit_count += _count_token(text, "admit")
            axiom_count += _count_token(text, "axiom")

        _attach_proof_layers(declaration_rows)
        _attach_execution_profiles(declaration_rows, repo_root=repo_root)

        toolchain_path = root / "lean-toolchain"
        manifest_path = root / "lake-manifest.json"
        lakefile_path = next((path for path in sorted(root.glob("lakefile.*")) if path.name in {"lakefile.toml", "lakefile.lean"}), None)
        dependencies = _lake_dependencies(manifest_path)
        mathlib_dependency = next((item for item in dependencies if item.get("name") == "mathlib"), None)
        rows.append(
            {
                "project_id": project_id,
                "root": _rel(root, repo_root=repo_root),
                "lakefile": _rel(lakefile_path, repo_root=repo_root) if lakefile_path else None,
                "lean_toolchain": toolchain_path.read_text(encoding="utf-8").strip() if toolchain_path.exists() else None,
                "lean_toolchain_path": _rel(toolchain_path, repo_root=repo_root) if toolchain_path.exists() else None,
                "lake_manifest": _rel(manifest_path, repo_root=repo_root) if manifest_path.exists() else None,
                "dependency_count": len(dependencies),
                "dependencies": dependencies[:12],
                "lean_file_count": len(lean_files),
                "lean_files": [_rel(path, repo_root=repo_root) for path in lean_files],
                "declaration_count": len(declaration_rows),
                "declaration_counts": dict(sorted(declaration_counts.items())),
                "declarations": [
                    {
                        **declaration,
                        "project_id": project_id,
                    }
                    for declaration in declaration_rows
                ],
                "sample_declarations": declaration_rows[:30],
                "build_provenance": {
                    "lean_toolchain": toolchain_path.read_text(encoding="utf-8").strip() if toolchain_path.exists() else None,
                    "lean_toolchain_path": _rel(toolchain_path, repo_root=repo_root) if toolchain_path.exists() else None,
                    "lake_manifest": _rel(manifest_path, repo_root=repo_root) if manifest_path.exists() else None,
                    "lake_manifest_sha256": _file_sha(manifest_path) if manifest_path.exists() else None,
                    "mathlib_rev": mathlib_dependency.get("rev") if mathlib_dependency else None,
                    "dependency_count": len(dependencies),
                },
                "static_risk_scan": {
                    "sorry_count": sorry_count,
                    "admit_count": admit_count,
                    "axiom_count": axiom_count,
                    "claim_boundary": "static token scan only; Lean/Lake owner checks remain proof authority",
                },
            }
        )
    return rows


def _receipt_status(path: Path) -> str:
    payload = _read_json_if_exists(path)
    status = payload.get("status") or payload.get("validation_status") or payload.get("route_status")
    if isinstance(status, str):
        return status
    if payload:
        return "present"
    return "missing"


def _thread_status(receipts: Sequence[Path]) -> str:
    statuses = [_receipt_status(path).upper() for path in receipts]
    if any(status in {"FAIL", "FAILED", "RED"} for status in statuses):
        return "attention_receipt_failed"
    if any(status in {"PASS", "GREEN", "OK"} for status in statuses):
        return "active_with_pass_receipts"
    if receipts:
        return "receipts_present_status_unclear"
    return "state_present_without_receipts"


def _docs_for_pilot(pilot_id: str, *, repo_root: Path) -> list[str]:
    docs_root = _repo_path("docs/formal_math", repo_root=repo_root)
    if not docs_root.exists():
        return []
    tokens = {pilot_id.lower()}
    if "erdos" in pilot_id.lower():
        tokens.add("erdos257")
    rows = []
    for path in sorted(docs_root.glob("*.md")):
        name = path.name.lower()
        if any(token in name for token in tokens):
            rows.append(_rel(path, repo_root=repo_root))
    return rows


def _discover_formal_threads(lean_projects: Sequence[Mapping[str, Any]], *, repo_root: Path) -> list[dict[str, Any]]:
    pilots_root = _repo_path("state/formal_math_research_operations/pilots", repo_root=repo_root)
    rows: list[dict[str, Any]] = []
    if not pilots_root.exists():
        return rows
    for pilot_dir in sorted(path for path in pilots_root.iterdir() if path.is_dir()):
        artifacts = sorted(path for path in pilot_dir.glob("*.json") if path.is_file())
        receipts = [path for path in artifacts if path.stem.endswith("_receipt")]
        state_artifacts = [path for path in artifacts if not path.stem.endswith("_receipt")]
        project_refs = [
            str(project["root"])
            for project in lean_projects
            if pilot_dir.name.split("_")[0].lower() in str(project.get("root", "")).lower()
        ]
        claim_boundaries = []
        for path in state_artifacts + receipts:
            payload = _read_json_if_exists(path, repo_root=repo_root)
            boundary = payload.get("claim_boundary")
            if isinstance(boundary, str) and boundary not in claim_boundaries:
                claim_boundaries.append(boundary)
        rows.append(
            {
                "thread_id": pilot_dir.name,
                "thread_root": _rel(pilot_dir, repo_root=repo_root),
                "status": _thread_status(receipts),
                "state_artifacts": [_rel(path, repo_root=repo_root) for path in state_artifacts],
                "receipt_artifacts": [
                    {
                        "path": _rel(path, repo_root=repo_root),
                        "status": _receipt_status(path),
                    }
                    for path in receipts
                ],
                "doc_refs": _docs_for_pilot(pilot_dir.name, repo_root=repo_root),
                "lean_project_refs": project_refs,
                "claim_boundaries": claim_boundaries,
            }
        )
    return rows


def _formal_tests(*, repo_root: Path) -> list[str]:
    tests_root = _repo_path("system/server/tests", repo_root=repo_root)
    if not tests_root.exists():
        return []
    return [_rel(path, repo_root=repo_root) for path in sorted(tests_root.glob("test_formal_math*.py"))]


def _source_manifest(*, repo_root: Path) -> list[dict[str, Any]]:
    generated_outputs = {
        OUTPUT_REL,
        RECEIPT_REL,
        DOC_REL,
        FULL_FIDELITY_PACKET_REL,
        FULL_FIDELITY_PACKET_RECEIPT_REL,
        FULL_FIDELITY_PACKET_DOC_REL,
        FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL,
        FULL_FIDELITY_PACKET_VERIFICATION_DOC_REL,
        FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
        FULL_FIDELITY_PACKET_REPLAY_DOC_REL,
        FULL_FIDELITY_CAPSULE_MANIFEST_REL,
        FULL_FIDELITY_CAPSULE_RECEIPT_REL,
        FULL_FIDELITY_CAPSULE_DOC_REL,
        FULL_FIDELITY_REVIEWER_HANDOFF_ENVELOPE_REL,
        FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_REL,
        FULL_FIDELITY_REVIEWER_HANDOFF_DOC_REL,
    }

    def in_projection_scope(path: Path) -> bool:
        rel = _rel(path, repo_root=repo_root)
        name = path.name
        if rel.startswith("tools/meta/factory/"):
            return "formal_math" in name or name == "build_lean_mathematics_microcosm_projection.py"
        if rel.startswith("system/server/tests/"):
            return name.startswith("test_formal_math") or name.startswith("test_lean_mathematics")
        if rel.startswith("state/lean_diagnostics/"):
            return _is_projection_relevant_lean_diagnostic(path, repo_root=repo_root)
        return True

    rows: list[dict[str, Any]] = []
    for rel_root in SOURCE_ROOTS:
        root = _repo_path(rel_root, repo_root=repo_root)
        files = [
            path
            for path in _iter_existing_files(root)
            if not _is_lake_build_path(path)
            and path.suffix in {".py", ".json", ".md", ".lean", ".toml"}
            and in_projection_scope(path)
            and _rel(path, repo_root=repo_root) not in generated_outputs
        ]
        rows.append(
            {
                "root": rel_root,
                "exists": root.exists(),
                "file_count": len(files),
                "fingerprint": _sha256(
                    [
                        {
                            "path": _rel(path, repo_root=repo_root),
                            "sha256": _file_sha(path),
                        }
                        for path in files
                    ]
                )
                if files
                else None,
            }
        )
    return rows


def _source_fingerprint(source_manifest: Sequence[Mapping[str, Any]]) -> str:
    return _sha256(list(source_manifest))


def _capability_snapshot(*, repo_root: Path) -> dict[str, Any]:
    capability_map = _read_json_if_exists("state/formal_math_research_operations/capability_map.json", repo_root=repo_root)
    rows = capability_map.get("capability_rows") if isinstance(capability_map, Mapping) else None
    capability_rows = rows if isinstance(rows, list) else []
    return {
        "capability_map_ref": "state/formal_math_research_operations/capability_map.json",
        "capability_count": len(capability_rows),
        "capability_ids": [
            str(row.get("capability_id"))
            for row in capability_rows
            if isinstance(row, Mapping) and row.get("capability_id")
        ],
        "authority_boundary": capability_map.get("authority_boundary") or {},
    }


def _line_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _file_entry(
    path: str | Path,
    *,
    repo_root: Path,
    role: str,
    material_class: str,
    body_access: str = "operator_authorized_local_source_ref",
) -> dict[str, Any] | None:
    target = _repo_path(path, repo_root=repo_root)
    if not target.is_file():
        return None
    rel = _rel(target, repo_root=repo_root)
    row: dict[str, Any] = {
        "source_ref": rel,
        "role": role,
        "material_class": material_class,
        "sha256": _file_sha(target),
        "line_count": _line_count(target) if target.suffix in {".lean", ".toml", ".json", ".md", ".txt"} else None,
        "byte_count": target.stat().st_size,
        "body_access": body_access,
        "body_text_in_packet_json": False,
        "body_text_in_receipts": False,
    }
    if target.suffix == ".lean":
        text = target.read_text(encoding="utf-8")
        row["imports"] = sorted(
            part
            for match in re.findall(r"^\s*import\s+(.+?)\s*$", text, flags=re.M)
            for part in match.split()
            if part
        )
        declarations = _lean_declarations(text)
        row["declaration_count"] = len(declarations)
        row["sample_declarations"] = [
            {
                "kind": item["kind"],
                "name": item["name"],
                "line_start": item["line_start"],
                "signature_excerpt": item["signature_excerpt"],
            }
            for item in declarations[:16]
        ]
    return row


def _latest_file(root: Path, pattern: str) -> Path | None:
    if not root.exists():
        return None
    matches = sorted(path for path in root.glob(pattern) if path.is_file())
    return matches[-1] if matches else None


def _diagnostic_status_tokens(payload: Mapping[str, Any]) -> set[str]:
    execution_context = payload.get("execution_context") if isinstance(payload.get("execution_context"), Mapping) else {}
    tokens = {
        payload.get("status"),
        payload.get("environment_status"),
        execution_context.get("environment_status"),
    }
    return {str(token) for token in tokens if token}


def _is_observation_only_lean_diagnostic(payload: Mapping[str, Any]) -> bool:
    return bool(_diagnostic_status_tokens(payload) & DIAGNOSTIC_OBSERVATION_ONLY_STATUSES)


def _is_projection_relevant_lean_diagnostic(path: Path, *, repo_root: Path) -> bool:
    if path.suffix != ".json":
        return True
    payload = _read_json_if_exists(path, repo_root=repo_root)
    if not payload:
        return True
    return not _is_observation_only_lean_diagnostic(payload)


def _lean_diagnostic_run_rows(*, repo_root: Path) -> list[dict[str, Any]]:
    root = _repo_path("state/lean_diagnostics/runs", repo_root=repo_root)
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(candidate for candidate in root.glob("*.json") if candidate.is_file()):
        payload = _read_json_if_exists(path, repo_root=repo_root)
        projection_relevant = bool(payload) and not _is_observation_only_lean_diagnostic(payload)
        rows.append(
            {
                "path": path,
                "payload": payload,
                "status_tokens": sorted(_diagnostic_status_tokens(payload)),
                "projection_relevant": projection_relevant,
                "projection_participation": "source_fingerprint_input"
                if projection_relevant
                else "observation_only_excluded_from_source_fingerprint",
            }
        )
    return rows


def _latest_lean_diagnostic(*, repo_root: Path) -> dict[str, Any]:
    rows = _lean_diagnostic_run_rows(repo_root=repo_root)
    latest_relevant = next((row for row in reversed(rows) if row["projection_relevant"]), None)
    if latest_relevant is None:
        return {
            "available": False,
            "status": "missing",
            "diagnostic_ref": None,
            "environment_status": "unknown",
            "source_boundary_filter": dict(DIAGNOSTIC_SOURCE_BOUNDARY_FILTER),
            "claim_boundary": "no diagnostic receipt found; absence is not proof success or proof failure",
        }
    path = latest_relevant["path"]
    payload = _read_json_if_exists(path, repo_root=repo_root)
    execution_context = payload.get("execution_context") if isinstance(payload.get("execution_context"), Mapping) else {}
    profile = payload.get("profile") if isinstance(payload.get("profile"), Mapping) else {}
    row = {
        "available": bool(payload),
        "diagnostic_ref": _rel(path, repo_root=repo_root),
        "sha256": _file_sha(path),
        "status": payload.get("status") or "present",
        "environment_status": payload.get("environment_status")
        or execution_context.get("environment_status")
        or "unknown",
        "dependency_cache_status": payload.get("dependency_cache_status")
        or execution_context.get("dependency_cache_status"),
        "command": payload.get("command"),
        "command_form": execution_context.get("command_form"),
        "cwd": execution_context.get("cwd"),
        "lake_root": execution_context.get("lake_root"),
        "lakefile": execution_context.get("lakefile"),
        "lean_toolchain": execution_context.get("lean_toolchain"),
        "target_file": execution_context.get("target_file") or payload.get("source_path"),
        "target_module": execution_context.get("target_module"),
        "returncode": payload.get("returncode"),
        "started_at": payload.get("started_at"),
        "ended_at": payload.get("ended_at"),
        "recommended_dependency_commands": execution_context.get("recommended_dependency_commands") or [],
        "diagnostic_lines": payload.get("diagnostic_lines") or [],
        "profile_event_count": profile.get("event_count"),
        "profile_cumulative_count": profile.get("cumulative_count"),
        "source_boundary_filter": dict(DIAGNOSTIC_SOURCE_BOUNDARY_FILTER),
        "projection_participation": "source_fingerprint_input",
        "claim_boundary": "diagnostic environment status only; Lean/Lake target-runner receipts remain proof authority",
    }
    return row


def _lean_imports_for_target(target_file: str | None, *, repo_root: Path) -> list[str]:
    if not target_file:
        return []
    path = _repo_path(target_file, repo_root=repo_root)
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    return sorted(
        part
        for match in re.findall(r"^\s*import\s+(.+?)\s*$", text, flags=re.M)
        for part in match.split()
        if part
    )


def _primary_lake_project(
    source_layer: Mapping[str, Any],
    latest_diagnostic: Mapping[str, Any],
) -> Mapping[str, Any]:
    projects = [
        project
        for project in source_layer.get("projects") or []
        if isinstance(project, Mapping)
    ]
    lake_root = latest_diagnostic.get("lake_root")
    if isinstance(lake_root, str) and lake_root:
        for project in projects:
            if project.get("root") == lake_root:
                return project
    return projects[0] if projects else {}


def _package_from_manifest(manifest_path: Path, package_name: str) -> dict[str, Any] | None:
    if not manifest_path.is_file():
        return None
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    packages = payload.get("packages") if isinstance(payload, Mapping) else None
    if not isinstance(packages, list):
        return None
    for package in packages:
        if isinstance(package, Mapping) and package.get("name") == package_name:
            return dict(package)
    return None


def _lake_workspace_status(
    source_layer: Mapping[str, Any],
    latest_diagnostic: Mapping[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    project = _primary_lake_project(source_layer, latest_diagnostic)
    lake_root = str(latest_diagnostic.get("lake_root") or project.get("root") or "")
    lake_root_path = _repo_path(lake_root, repo_root=repo_root) if lake_root else repo_root
    target_file = latest_diagnostic.get("target_file")
    if not isinstance(target_file, str) or not target_file:
        lean_files = [
            str(row.get("source_ref"))
            for row in project.get("source_files") or []
            if isinstance(row, Mapping)
            and row.get("material_class") == "lean_source_or_proof_body"
            and isinstance(row.get("source_ref"), str)
        ]
        target_file = lean_files[0] if lean_files else None
    lakefile = str(latest_diagnostic.get("lakefile") or project.get("lakefile") or "")
    if not lakefile and lake_root:
        for candidate in ("lakefile.toml", "lakefile.lean"):
            candidate_path = lake_root_path / candidate
            if candidate_path.is_file():
                lakefile = _rel(candidate_path, repo_root=repo_root)
                break
    manifest_ref = str(project.get("lake_manifest") or (f"{lake_root}/lake-manifest.json" if lake_root else ""))
    toolchain_ref = str(project.get("lean_toolchain_path") or (f"{lake_root}/lean-toolchain" if lake_root else ""))
    manifest_path = _repo_path(manifest_ref, repo_root=repo_root) if manifest_ref else repo_root / "__missing__"
    toolchain_path = _repo_path(toolchain_ref, repo_root=repo_root) if toolchain_ref else repo_root / "__missing__"
    lakefile_path = _repo_path(lakefile, repo_root=repo_root) if lakefile else repo_root / "__missing__"
    mathlib_package = _package_from_manifest(manifest_path, "mathlib") or {}
    imports = _lean_imports_for_target(target_file, repo_root=repo_root)
    expected_import_artifacts: list[dict[str, Any]] = []
    mathlib_artifact_roots = [
        lake_root_path / ".lake/build/lib/lean",
        lake_root_path / ".lake/packages/mathlib/.lake/build/lib/lean",
    ]
    for module in imports:
        if not module.startswith("Mathlib."):
            continue
        rel_olean = Path(*module.split(".")).with_suffix(".olean")
        artifact_candidates = [root / rel_olean for root in mathlib_artifact_roots]
        artifact_path = next((path for path in artifact_candidates if path.is_file()), artifact_candidates[0])
        expected_import_artifacts.append(
            {
                "module": module,
                "artifact_ref": _rel(artifact_path, repo_root=repo_root),
                "exists": artifact_path.is_file(),
                "candidate_refs": [_rel(path, repo_root=repo_root) for path in artifact_candidates],
            }
        )
    missing_import_artifacts = [
        row["module"] for row in expected_import_artifacts if not row.get("exists")
    ]
    mathlib_source_root = lake_root_path / ".lake/packages/mathlib/Mathlib"
    mathlib_build_roots = [root / "Mathlib" for root in mathlib_artifact_roots]
    mathlib_build_root = next((path for path in mathlib_build_roots if path.is_dir()), mathlib_build_roots[0])
    package_status = (
        "present" if mathlib_source_root.is_dir() else "missing"
    )
    artifact_status = (
        "not_required"
        if not expected_import_artifacts
        else ("present" if not missing_import_artifacts else "missing")
    )
    status = "PASS"
    if not lake_root or not lake_root_path.is_dir() or not manifest_path.is_file() or not toolchain_path.is_file():
        status = "BLOCKED"
    elif package_status == "missing" or artifact_status == "missing":
        status = "BLOCKED"
    return {
        "status": status,
        "lake_root": lake_root or None,
        "lake_root_exists": lake_root_path.is_dir() if lake_root else False,
        "package_id": project.get("project_id") or latest_diagnostic.get("package_id"),
        "target_file": target_file,
        "target_module": latest_diagnostic.get("target_module"),
        "lean_toolchain": latest_diagnostic.get("lean_toolchain") or project.get("lean_toolchain"),
        "lean_toolchain_ref": toolchain_ref or None,
        "lean_toolchain_sha256": _file_sha(toolchain_path) if toolchain_path.is_file() else None,
        "lakefile_ref": lakefile or None,
        "lakefile_sha256": _file_sha(lakefile_path) if lakefile_path.is_file() else None,
        "lake_manifest_ref": manifest_ref or None,
        "lake_manifest_sha256": _file_sha(manifest_path) if manifest_path.is_file() else None,
        "mathlib_package_status": package_status,
        "mathlib_package_ref": _rel(mathlib_source_root, repo_root=repo_root),
        "mathlib_rev": mathlib_package.get("rev") or mathlib_package.get("inputRev"),
        "build_artifact_root_ref": _rel(mathlib_build_root, repo_root=repo_root),
        "build_artifact_root_exists": mathlib_build_root.is_dir(),
        "build_artifact_root_candidates": [_rel(path, repo_root=repo_root) for path in mathlib_build_roots],
        "expected_import_artifact_status": artifact_status,
        "expected_import_artifacts": expected_import_artifacts,
        "missing_import_artifacts": missing_import_artifacts,
        "claim_boundary": "Lake workspace status classifies replay environment only; it is not proof authority.",
    }


def _replay_context_fingerprint(
    packet: Mapping[str, Any],
    latest_diagnostic: Mapping[str, Any],
    lake_workspace_status: Mapping[str, Any],
) -> str:
    return _sha256(
        {
            "lake_root": lake_workspace_status.get("lake_root"),
            "target_file": lake_workspace_status.get("target_file"),
            "lake_manifest_sha256": lake_workspace_status.get("lake_manifest_sha256"),
            "lean_toolchain_sha256": lake_workspace_status.get("lean_toolchain_sha256"),
        }
    )


def _preserved_replay_attempts(
    previous_receipt: Mapping[str, Any],
    *,
    replay_context_fingerprint: str,
) -> dict[str, Any]:
    if previous_receipt.get("replay_context_fingerprint") != replay_context_fingerprint:
        return {}
    preserved: dict[str, Any] = {}
    for key in ("hydration_attempt", "target_attempt", "attempted_at"):
        value = previous_receipt.get(key)
        if value:
            preserved[key] = value
    return preserved


def _attempt_status(attempt: Mapping[str, Any] | None) -> str | None:
    if not isinstance(attempt, Mapping) or not attempt:
        return None
    if attempt.get("timed_out") is True:
        return "TIMEOUT"
    returncode = attempt.get("returncode")
    if returncode == 0:
        return "PASS"
    if isinstance(returncode, int):
        return "FAIL"
    return None


def _dependency_hydration_status(
    lake_workspace_status: Mapping[str, Any],
    latest_diagnostic: Mapping[str, Any],
    hydration_attempt: Mapping[str, Any] | None,
) -> str:
    attempt_status = _attempt_status(hydration_attempt)
    if attempt_status == "PASS":
        return "PASS"
    if attempt_status == "TIMEOUT":
        return "BLOCKED"
    if attempt_status == "FAIL":
        return "FAIL"
    if lake_workspace_status.get("expected_import_artifact_status") in {"present", "not_required"} and (
        lake_workspace_status.get("mathlib_package_status") == "present"
        or lake_workspace_status.get("expected_import_artifact_status") == "not_required"
    ):
        return "PASS"
    environment_status = str(latest_diagnostic.get("environment_status") or "").lower()
    if environment_status in {"dependency_cache_missing", "lake_cache_missing", "environment_blocked"}:
        return "BLOCKED"
    return "NOT_ATTEMPTED"


def _target_replay_status(
    latest_diagnostic: Mapping[str, Any],
    target_attempt: Mapping[str, Any] | None,
    *,
    dependency_hydration_status: str,
) -> str:
    attempt_status = _attempt_status(target_attempt)
    if attempt_status == "PASS":
        return "PASS"
    if attempt_status == "TIMEOUT":
        return "TIMEOUT"
    if attempt_status == "FAIL":
        return "LEAN_FAIL"
    diagnostic_status = _lake_replay_status(latest_diagnostic)
    if diagnostic_status == "PASS":
        return "PASS"
    if diagnostic_status == "ENVIRONMENT_BLOCKED":
        return "ENVIRONMENT_BLOCKED"
    if diagnostic_status == "FAIL":
        return "LEAN_FAIL" if dependency_hydration_status == "PASS" else "ENVIRONMENT_BLOCKED"
    return "NOT_RUN"


def _reviewer_acceptance_from_replay(target_replay_status: str) -> str:
    if target_replay_status == "PASS":
        return "REVIEWABLE_REPLAYED"
    if target_replay_status == "LEAN_FAIL":
        return "REJECTED_OR_REQUIRES_REPAIR"
    if target_replay_status in {"ENVIRONMENT_BLOCKED", "TIMEOUT"}:
        return "REVIEWABLE_WITH_ENVIRONMENT_BLOCK"
    return "PACKET_ONLY"


def _packet_source_disclosure_layer(
    lean_projects: Sequence[Mapping[str, Any]],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    projects: list[dict[str, Any]] = []
    source_files: list[dict[str, Any]] = []
    for project in lean_projects:
        project_files: list[dict[str, Any]] = []
        for key, role, material_class in (
            ("lean_toolchain_path", "Lean toolchain pin", "lean_toolchain"),
            ("lakefile", "Lake package configuration", "lake_package_config"),
            ("lake_manifest", "Lake dependency manifest", "lake_dependency_manifest"),
        ):
            ref = project.get(key)
            if isinstance(ref, str) and ref:
                entry = _file_entry(
                    ref,
                    repo_root=repo_root,
                    role=role,
                    material_class=material_class,
                    body_access="operator_authorized_local_source_ref",
                )
                if entry:
                    project_files.append(entry)
        for ref in project.get("lean_files") or []:
            if isinstance(ref, str) and ref:
                entry = _file_entry(
                    ref,
                    repo_root=repo_root,
                    role="Lean module or proof body source",
                    material_class="lean_source_or_proof_body",
                    body_access="operator_authorized_local_source_ref",
                )
                if entry:
                    project_files.append(entry)
        source_files.extend(project_files)
        projects.append(
            {
                "project_id": project.get("project_id"),
                "root": project.get("root"),
                "lakefile": project.get("lakefile"),
                "lean_toolchain": project.get("lean_toolchain"),
                "lean_toolchain_path": project.get("lean_toolchain_path"),
                "lake_manifest": project.get("lake_manifest"),
                "dependency_count": project.get("dependency_count"),
                "mathlib_rev": (project.get("build_provenance") or {}).get("mathlib_rev")
                if isinstance(project.get("build_provenance"), Mapping)
                else None,
                "source_file_count": len(project_files),
                "source_files": project_files,
                "static_risk_scan": project.get("static_risk_scan") or {},
            }
        )
    return {
        "layer_id": "source_disclosure",
        "answers": "what can be shown",
        "posture_id": "operator_authorized_full_fidelity",
        "body_storage_policy": (
            "Proof bodies and Mathlib-dependent Lean modules remain in local source files; "
            "this packet carries refs, hashes, metadata, and receipts rather than duplicating full bodies into JSON."
        ),
        "body_visibility": "operator_authorized_local_source_refs",
        "body_text_in_packet_json": False,
        "body_text_in_receipts": False,
        "lake_project_count": len(projects),
        "source_file_count": len(source_files),
        "source_files_sha256": _sha256(
            [{"source_ref": row["source_ref"], "sha256": row["sha256"]} for row in source_files]
        ),
        "projects": projects,
    }


def _evidence_cell_refs(formal_math_threads: Sequence[Mapping[str, Any]], *, repo_root: Path) -> list[dict[str, Any]]:
    refs = [
        "state/formal_math_research_operations/formal_evidence_cell_registry.json",
        "state/formal_math_research_operations/formal_evidence_cell_registry_receipt.json",
    ]
    for thread in formal_math_threads:
        thread_root = str(thread.get("thread_root") or "")
        if thread_root:
            refs.extend(
                [
                    f"{thread_root}/formal_evidence_cells.json",
                    f"{thread_root}/formal_evidence_cells_receipt.json",
                ]
            )
    rows: list[dict[str, Any]] = []
    for ref in dict.fromkeys(refs):
        path = _repo_path(ref, repo_root=repo_root)
        if not path.is_file():
            continue
        payload = _read_json_if_exists(path, repo_root=repo_root)
        cell_count = payload.get("cell_count")
        if cell_count is None and isinstance(payload.get("cells"), list):
            cell_count = len(payload["cells"])
        rows.append(
            {
                "ref": ref,
                "sha256": _file_sha(path),
                "status": payload.get("status") or "present",
                "cell_count": cell_count,
                "authority_posture": payload.get("authority_posture"),
                "claim_boundary": payload.get("claim_boundary"),
            }
        )
    return rows


def _target_runner_refs(formal_math_threads: Sequence[Mapping[str, Any]], *, repo_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for thread in formal_math_threads:
        thread_root = str(thread.get("thread_root") or "")
        if not thread_root:
            continue
        for path in sorted(_repo_path(thread_root, repo_root=repo_root).glob("*target_runner*receipt*.json")):
            payload = _read_json_if_exists(path, repo_root=repo_root)
            rows.append(
                {
                    "ref": _rel(path, repo_root=repo_root),
                    "sha256": _file_sha(path),
                    "status": payload.get("status") or "present",
                    "target_check_status": payload.get("target_check_status"),
                    "print_axioms_status": payload.get("print_axioms_status"),
                    "axiom_dependency_class": payload.get("axiom_dependency_class"),
                    "claim_boundary": payload.get("claim_boundary"),
                    "target_count": payload.get("target_count"),
                    "target_theorem": payload.get("target_theorem"),
                    "non_claims": payload.get("non_claims") or [],
                }
            )
    return rows


def _packet_receipt_reproduction_layer(
    formal_math_threads: Sequence[Mapping[str, Any]],
    validation_surfaces: Mapping[str, Any],
    *,
    repo_root: Path,
) -> dict[str, Any]:
    evidence_cells = _evidence_cell_refs(formal_math_threads, repo_root=repo_root)
    target_runner_receipts = _target_runner_refs(formal_math_threads, repo_root=repo_root)
    thread_receipts: list[dict[str, Any]] = []
    for thread in formal_math_threads:
        for receipt in thread.get("receipt_artifacts") or []:
            if not isinstance(receipt, Mapping):
                continue
            ref = str(receipt.get("path") or "")
            if not ref:
                continue
            path = _repo_path(ref, repo_root=repo_root)
            thread_receipts.append(
                {
                    "ref": ref,
                    "status": receipt.get("status") or _receipt_status(path),
                    "sha256": _file_sha(path) if path.is_file() else None,
                }
            )
    latest_diagnostic = _latest_lean_diagnostic(repo_root=repo_root)
    return {
        "layer_id": "receipt_and_reproduction",
        "answers": "what was checked, by which lane, under what context",
        "generated_projection": {
            "projection_ref": OUTPUT_REL,
            "receipt_ref": RECEIPT_REL,
            "markdown_ref": DOC_REL,
        },
        "full_fidelity_packet": {
            "packet_ref": FULL_FIDELITY_PACKET_REL,
            "receipt_ref": FULL_FIDELITY_PACKET_RECEIPT_REL,
            "markdown_ref": FULL_FIDELITY_PACKET_DOC_REL,
        },
        "evidence_cells": evidence_cells,
        "target_runner_receipts": target_runner_receipts,
        "thread_receipts": thread_receipts,
        "latest_diagnostic": latest_diagnostic,
        "validation_commands": list(validation_surfaces.get("recommended_checks") or []),
        "claim_boundary": (
            "Reproduction refs are evidence handles; proof authority remains with their owner tools and Lean/Lake execution."
        ),
    }


def _packet_claim_boundary_layer(
    formal_math_threads: Sequence[Mapping[str, Any]],
    lean_projects: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    claim_boundaries: list[str] = []
    for thread in formal_math_threads:
        for boundary in thread.get("claim_boundaries") or []:
            if isinstance(boundary, str) and boundary not in claim_boundaries:
                claim_boundaries.append(boundary)
    static_risk_scans = [
        {
            "project_id": project.get("project_id"),
            "root": project.get("root"),
            "static_risk_scan": project.get("static_risk_scan") or {},
        }
        for project in lean_projects
    ]
    return {
        "layer_id": "claim_boundary",
        "answers": "what may be claimed",
        "authority_invariant": AUTHORITY_INVARIANT,
        "anti_claims": list(ANTI_CLAIMS),
        "thread_claim_boundaries": claim_boundaries,
        "claim_boundary_count": len(claim_boundaries),
        "static_risk_scans": static_risk_scans,
        "statement_reconciliation_status": (
            "projection carries formal-math thread claim boundaries and obligation DAG refs; "
            "statement reconciliation authority remains with owner receipts when present"
        ),
        "proof_body_visibility_caveat": (
            "Visible Lean source is inspection evidence. It is not proof authority unless the named Lean/Lake "
            "target-runner, axiom/sorry/admit audit, and statement-boundary receipts verify the exact claim."
        ),
        "release_boundary": "operator-authorized review packet, not public release permission",
    }


def _secret_exclusion_scan(
    paths: Sequence[str],
    *,
    repo_root: Path,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy_ref = "microcosm-substrate/core/private_state_forbidden_classes.json"
    policy_path = _repo_path(policy_ref, repo_root=repo_root)
    if not policy_path.is_file():
        return {
            "status": "policy_missing",
            "policy_ref": policy_ref,
            "blocking_hit_count": None,
            "scanned_path_count": 0,
            "body_redacted": True,
            "hits_exported": False,
            "claim_boundary": "secret-exclusion policy missing in this checkout; not a release clearance",
        }
    for src in (
        _repo_path("microcosm-substrate/src", repo_root=repo_root),
        REPO_ROOT / "microcosm-substrate/src",
    ):
        if src.exists() and str(src) not in sys.path:
            sys.path.insert(0, str(src))
    try:
        from microcosm_core.private_state_scan import (  # type: ignore
            load_forbidden_classes,
            scan_json_payload,
            scan_paths,
        )
    except Exception as exc:  # pragma: no cover - defensive degradation
        return {
            "status": "scanner_unavailable",
            "policy_ref": policy_ref,
            "blocking_hit_count": None,
            "scanned_path_count": 0,
            "body_redacted": True,
            "hits_exported": False,
            "error": str(exc),
            "claim_boundary": "secret-exclusion scanner unavailable; not a release clearance",
        }
    policy = load_forbidden_classes(policy_path)
    resolved_paths = [_repo_path(path, repo_root=repo_root) for path in paths]
    path_scan = scan_paths(resolved_paths, forbidden_classes=policy, display_root=repo_root)
    payload_scan = (
        scan_json_payload(
            dict(payload),
            path=FULL_FIDELITY_PACKET_REL,
            forbidden_classes=policy,
        )
        if payload is not None
        else {"status": "pass", "hits": [], "blocking_hit_count": 0}
    )
    path_hits = [
        hit for hit in path_scan.get("hits", []) if isinstance(hit, Mapping) and not hit.get("expected_negative_case")
    ]
    payload_hits = [
        hit for hit in payload_scan.get("hits", []) if isinstance(hit, Mapping) and not hit.get("expected_negative_case")
    ]
    blocking_hit_count = len(path_hits) + len(payload_hits)
    return {
        "status": "pass" if blocking_hit_count == 0 else "blocked_private_state",
        "policy_ref": policy_ref,
        "scanner": "microcosm_core.private_state_scan",
        "blocking_hit_count": blocking_hit_count,
        "path_blocking_hit_count": len(path_hits),
        "payload_blocking_hit_count": len(payload_hits),
        "scanned_path_count": path_scan.get("scanned_path_count", 0),
        "body_redacted": True,
        "hits_exported": False,
        "scan_scope": path_scan.get("scan_scope"),
        "anti_claim": path_scan.get("anti_claim"),
        "claim_boundary": "secret-exclusion scan is sentinel/policy evidence, not complete DLP or public release clearance",
    }


def _surface_payload(surface_id: str, *, available: bool, issues: Sequence[str] = (), **payload: Any) -> dict[str, Any]:
    return {
        "surface_id": surface_id,
        "available": available,
        **payload,
        "omission_receipt": {
            "status": "complete" if available and not issues else "degraded",
            "issues": list(issues),
            "reason": "visual surface is projection transport only; source artifacts remain authority",
        },
    }


def _declaration_catalog(lean_projects: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    declarations: list[dict[str, Any]] = []
    for project in lean_projects:
        project_declarations = project.get("declarations")
        if isinstance(project_declarations, list):
            declarations.extend(item for item in project_declarations if isinstance(item, dict))
    declarations.sort(key=lambda item: (str(item.get("file")), int(item.get("line_start") or 0), str(item.get("name"))))
    kind_counts = Counter(str(item.get("kind") or "unknown") for item in declarations)
    return _surface_payload(
        "declaration_catalog",
        available=True,
        declarations=declarations,
        declaration_count=len(declarations),
        kind_counts=dict(sorted(kind_counts.items())),
        ordering="file,line_start,name",
    )


def _declaration_graph(lean_projects: Sequence[Mapping[str, Any]], *, repo_root: Path) -> dict[str, Any]:
    declarations = _declaration_catalog(lean_projects)["declarations"]
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    declaration_by_file: dict[str, list[dict[str, Any]]] = {}
    for declaration in declarations:
        node_id = str(declaration.get("node_id") or "")
        node: dict[str, Any] = {
            "node_id": node_id,
            "node_kind": "declaration",
            "label": declaration.get("name"),
            "declaration_kind": declaration.get("kind"),
            "cluster_id": declaration.get("module_id"),
        }
        proof_layer = declaration.get("proof_layer")
        if isinstance(proof_layer, Mapping):
            if proof_layer.get("layer_id"):
                node["proof_layer_id"] = proof_layer.get("layer_id")
            if proof_layer.get("significance"):
                node["proof_significance"] = proof_layer.get("significance")
        execution_profile = declaration.get("execution_profile")
        if isinstance(execution_profile, Mapping) and execution_profile.get("available"):
            node["execution_duration_ms"] = execution_profile.get("total_duration_ms")
            node["execution_dominant_phase"] = execution_profile.get("dominant_phase")
            node["execution_profile_freshness"] = execution_profile.get("profile_freshness")
        nodes.append(node)
        declaration_by_file.setdefault(str(declaration.get("file")), []).append({**declaration, "node_id": node_id})

    name_to_nodes = {
        str(item.get("name")): str(item.get("node_id") or "")
        for item in declarations
        if item.get("name") and item.get("node_id")
    }
    name_token_chars = r"A-Za-z0-9_'."
    declaration_name_pattern = (
        re.compile(
            rf"(?<![{name_token_chars}])("
            + "|".join(
                re.escape(name)
                for name in sorted(name_to_nodes, key=len, reverse=True)
            )
            + rf")(?![{name_token_chars}])"
        )
        if name_to_nodes
        else None
    )
    edge_index = 0
    for rel_file, file_declarations in declaration_by_file.items():
        path = _repo_path(rel_file, repo_root=repo_root)
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        ordered = sorted(file_declarations, key=lambda item: int(item.get("line_start") or 0))
        for index, declaration in enumerate(ordered):
            start = int(declaration.get("line_start") or 1)
            next_start = (
                int(ordered[index + 1].get("line_start") or len(lines) + 1)
                if index + 1 < len(ordered)
                else len(lines) + 1
            )
            body = "\n".join(lines[start: max(start, next_start - 1)])
            target_ids = {
                name_to_nodes[match.group(1)]
                for match in declaration_name_pattern.finditer(body)
            } if declaration_name_pattern else set()
            for target_id in sorted(target_ids):
                if target_id == declaration["node_id"]:
                    continue
                edge_index += 1
                edges.append(
                    {
                        "edge_id": f"e{edge_index}",
                        "from_node_id": declaration["node_id"],
                        "to_node_id": target_id,
                        "edge_kind": "calls",
                        "confidence": "lexical_reference",
                    }
                )
        if any(line.startswith("import Mathlib") for line in lines):
            mathlib_node_id = "external:mathlib"
            if not any(node["node_id"] == mathlib_node_id for node in nodes):
                nodes.append(
                    {
                        "node_id": mathlib_node_id,
                        "node_kind": "external_package",
                        "label": "mathlib",
                        "cluster_id": "external",
                    }
                )
            first = ordered[0] if ordered else None
            if first:
                edge_index += 1
                edges.append(
                    {
                        "edge_id": f"e{edge_index}",
                        "from_node_id": first["node_id"],
                        "to_node_id": mathlib_node_id,
                        "edge_kind": "mathlib_dep",
                        "confidence": "import_statement",
                    }
                )

    edge_counts = Counter(str(edge["edge_kind"]) for edge in edges)
    cluster_counts = Counter(str(node.get("cluster_id") or "unclustered") for node in nodes)
    return _surface_payload(
        "declaration_graph",
        available=True,
        nodes=nodes,
        edges=edges,
        clusters=[
            {"cluster_id": cluster_id, "node_count": count}
            for cluster_id, count in sorted(cluster_counts.items())
        ],
        edge_kind_counts=dict(sorted(edge_counts.items())),
        edge_taxonomy=[
            "calls",
            "unfolds_into",
            "case_of",
            "mathlib_dep",
            "tactic_uses",
            "hypothesis_of",
        ],
    )


def _graph_node_label(node: Mapping[str, Any]) -> str:
    return str(node.get("label") or node.get("node_id") or "")


def _semantic_family_for_node(node: Mapping[str, Any]) -> tuple[str, str, str]:
    label = _graph_node_label(node)
    lower = label.lower()
    declaration_kind = str(node.get("declaration_kind") or "")
    if "period_noncollapse" in lower and not lower.startswith(
        ("local_layer", "minimal_layer", "residue_formula", "component", "odd_component")
    ):
        return (
            "period_noncollapse_endpoint",
            "Period Noncollapse Endpoint",
            "declarations whose names close or route toward period noncollapse endpoints",
        )
    if lower.startswith("b2_f") or "fixture" in lower or "generated_finite" in lower or "generatedfinite" in lower:
        return (
            "finite_fixture",
            "Finite Generated Rows / Fixtures",
            "generated finite rows, fixture declarations, and concrete witness rows",
        )
    if "canonical" in lower and ("witness" in lower or "row" in lower or "case" in lower):
        return (
            "canonical_witness_row",
            "Canonical Witness Rows",
            "canonical witness rows and case constructors inferred from declaration names",
        )
    if "local_layer" in lower or "layer_certificate" in lower:
        return (
            "local_layer_certificate",
            "Local Layer Certificates",
            "local-layer certificates and decomposition lemmas inferred from declaration names",
        )
    if "component" in lower or "residue" in lower or "term" in lower:
        return (
            "component_term_residue",
            "Component Term / Residue Formulas",
            "component-term and residue formula machinery inferred from declaration names",
        )
    if "orderof" in lower or "modeq" in lower or "mod_eq" in lower:
        return (
            "orderof_modeq",
            "orderOf / modEq Machinery",
            "orderOf and modular-equivalence machinery inferred from declaration names",
        )
    if "valuation" in lower or ("prime" in lower and "drop" in lower) or "factorization" in lower:
        return (
            "valuation_core",
            "Prime Drop / Valuation Core",
            "prime-drop, valuation, and factorization core declarations inferred from names",
        )
    if declaration_kind in {"structure", "class", "inductive"} or "witness" in lower or "certificate" in lower:
        return (
            "certificate_structure",
            "Certificate Structures",
            "structural witness and certificate declarations inferred from kind/name",
        )
    return (
        "other",
        "Other Declarations",
        "declarations not matched by the current name-based semantic family rules",
    )


def _safe_token(value: Any) -> str:
    token = re.sub(r"[^A-Za-z0-9_:.=-]+", "_", str(value or "").strip())
    return token.strip("_") or "unknown"


def _edge_id_sort_key(edge_id: Any) -> tuple[int, str]:
    token = str(edge_id or "")
    match = re.match(r"e(\d+)$", token)
    return (int(match.group(1)) if match else 10**9, token)


def _first_family_id(family_ids: Sequence[str] | None) -> str:
    if not family_ids:
        return "unclassified"
    return str(family_ids[0] or "unclassified")


def _reachable_nodes(
    start: str,
    adjacency: Mapping[str, set[str]],
    cache: dict[str, set[str]],
    stack: frozenset[str] = frozenset(),
) -> set[str]:
    if start in cache:
        return set(cache[start])
    if start in stack:
        return set()
    out: set[str] = set()
    next_stack = stack | {start}
    for nxt in adjacency.get(start, set()):
        out.add(nxt)
        out.update(_reachable_nodes(nxt, adjacency, cache, next_stack))
    cache[start] = set(out)
    return out


def _multi_source_distances(source_ids: Sequence[str], adjacency: Mapping[str, set[str]]) -> dict[str, int]:
    distances: dict[str, int] = {}
    frontier = list(dict.fromkeys(str(item) for item in source_ids if str(item or "").strip()))
    for node_id in frontier:
        distances[node_id] = 0
    index = 0
    while index < len(frontier):
        current = frontier[index]
        index += 1
        for nxt in sorted(adjacency.get(current, set())):
            if nxt in distances:
                continue
            distances[nxt] = distances[current] + 1
            frontier.append(nxt)
    return distances


def _alternative_path_exists(
    *,
    start: str,
    target: str,
    adjacency_with_edges: Mapping[str, Sequence[tuple[str, str]]],
    skip_edge_id: str,
) -> bool:
    stack = [start]
    seen = {start}
    while stack:
        current = stack.pop()
        for nxt, edge_id in adjacency_with_edges.get(current, ()):
            if edge_id == skip_edge_id:
                continue
            if nxt == target:
                return True
            if nxt in seen:
                continue
            seen.add(nxt)
            stack.append(nxt)
    return False


def _transitive_reduction_edge_ids(declaration_edges: Sequence[Mapping[str, Any]]) -> list[str]:
    adjacency_with_edges: dict[str, list[tuple[str, str]]] = {}
    for edge in declaration_edges:
        edge_id = str(edge.get("edge_id") or "")
        from_id = str(edge.get("from_node_id") or "")
        to_id = str(edge.get("to_node_id") or "")
        if not edge_id or not from_id or not to_id:
            continue
        adjacency_with_edges.setdefault(from_id, []).append((to_id, edge_id))

    reduced: list[str] = []
    for edge in sorted(declaration_edges, key=lambda item: _edge_id_sort_key(item.get("edge_id"))):
        edge_id = str(edge.get("edge_id") or "")
        from_id = str(edge.get("from_node_id") or "")
        to_id = str(edge.get("to_node_id") or "")
        if not edge_id or not from_id or not to_id:
            continue
        if not _alternative_path_exists(
            start=from_id,
            target=to_id,
            adjacency_with_edges=adjacency_with_edges,
            skip_edge_id=edge_id,
        ):
            reduced.append(edge_id)
    return reduced


def _declaration_graph_views(
    declaration_graph: Mapping[str, Any],
    *,
    currentness: Mapping[str, Any],
) -> dict[str, Any]:
    nodes = [
        dict(node)
        for node in declaration_graph.get("nodes") or []
        if isinstance(node, Mapping)
    ]
    edges = [
        dict(edge)
        for edge in declaration_graph.get("edges") or []
        if isinstance(edge, Mapping)
    ]
    node_by_id = {str(node.get("node_id")): node for node in nodes if node.get("node_id")}
    declaration_node_ids = {
        node_id
        for node_id, node in node_by_id.items()
        if node.get("node_kind") == "declaration"
    }
    declaration_edges = [
        edge
        for edge in edges
        if str(edge.get("from_node_id")) in declaration_node_ids
        and str(edge.get("to_node_id")) in declaration_node_ids
    ]
    deps_by_node: dict[str, set[str]] = {node_id: set() for node_id in declaration_node_ids}
    callers_by_node: dict[str, set[str]] = {node_id: set() for node_id in declaration_node_ids}
    for edge in declaration_edges:
        from_id = str(edge.get("from_node_id") or "")
        to_id = str(edge.get("to_node_id") or "")
        if from_id and to_id:
            deps_by_node.setdefault(from_id, set()).add(to_id)
            callers_by_node.setdefault(to_id, set()).add(from_id)

    def node_sort_key(node_id: str) -> tuple[str, int, str]:
        node = node_by_id.get(node_id, {})
        return (
            str(node.get("cluster_id") or ""),
            int(node.get("line_start") or 0),
            _graph_node_label(node),
        )

    dependency_layers: list[dict[str, Any]] = []
    assigned: set[str] = set()
    remaining = set(declaration_node_ids)
    while remaining:
        ready = sorted(
            (node_id for node_id in remaining if deps_by_node.get(node_id, set()) <= assigned),
            key=node_sort_key,
        )
        cycle_break = False
        if not ready:
            cycle_break = True
            ready = [
                min(
                    remaining,
                    key=lambda node_id: (
                        len(deps_by_node.get(node_id, set()) - assigned),
                        node_sort_key(node_id),
                    ),
                )
            ]
        dependency_layers.append(
            {
                "layer_index": len(dependency_layers),
                "node_ids": ready,
                "node_count": len(ready),
                "sample_labels": [_graph_node_label(node_by_id[node_id]) for node_id in ready[:8]],
                "cycle_break": cycle_break,
            }
        )
        assigned.update(ready)
        remaining.difference_update(ready)

    family_order = [
        "period_noncollapse_endpoint",
        "finite_fixture",
        "canonical_witness_row",
        "local_layer_certificate",
        "component_term_residue",
        "orderof_modeq",
        "valuation_core",
        "certificate_structure",
        "other",
    ]
    families: dict[str, dict[str, Any]] = {}
    for node_id in sorted(declaration_node_ids, key=node_sort_key):
        family_id, label, summary = _semantic_family_for_node(node_by_id[node_id])
        family = families.setdefault(
            family_id,
            {
                "family_id": family_id,
                "label": label,
                "node_ids": [],
                "summary": summary,
                "color_token": f"lean_family_{family_id}",
                "inference": "name_kind_edge_signature_v1",
                "sample_labels": [],
            },
        )
        family["node_ids"].append(node_id)
        if len(family["sample_labels"]) < 8:
            family["sample_labels"].append(_graph_node_label(node_by_id[node_id]))
    semantic_families = [
        {**families[family_id], "node_count": len(families[family_id]["node_ids"])}
        for family_id in family_order
        if family_id in families
    ]

    def longest_dependency_path(node_id: str, seen: frozenset[str] = frozenset()) -> list[str]:
        if node_id in seen:
            return [node_id]
        deps = sorted(deps_by_node.get(node_id, set()), key=node_sort_key)
        if not deps:
            return [node_id]
        next_seen = seen | {node_id}
        best_tail = max(
            (longest_dependency_path(dep, next_seen) for dep in deps),
            key=lambda path: (len(path), [_graph_node_label(node_by_id.get(item, {})) for item in path]),
        )
        return [node_id, *best_tail]

    terminal_candidates = [
        node_id
        for node_id in declaration_node_ids
        if node_by_id[node_id].get("declaration_kind") in {"theorem", "lemma"}
        and not callers_by_node.get(node_id)
    ]
    if not terminal_candidates:
        terminal_candidates = [
            node_id
            for node_id in declaration_node_ids
            if node_by_id[node_id].get("declaration_kind") in {"theorem", "lemma"}
            and not deps_by_node.get(node_id)
        ]
    terminal_candidates = sorted(
        terminal_candidates,
        key=lambda node_id: (
            "period_noncollapse" not in _graph_node_label(node_by_id[node_id]).lower(),
            -len(deps_by_node.get(node_id, set())),
            node_sort_key(node_id),
        ),
    )

    final_theorem_routes: list[dict[str, Any]] = []
    terminal_claims: list[dict[str, Any]] = []
    for rank, node_id in enumerate(terminal_candidates[:20], start=1):
        node = node_by_id[node_id]
        route_node_ids = longest_dependency_path(node_id)
        leaf_node_ids = sorted(
            (
                reachable
                for reachable in route_node_ids
                if not deps_by_node.get(reachable)
            ),
            key=node_sort_key,
        )
        if rank <= 12:
            final_theorem_routes.append(
                {
                    "route_id": f"final_route_{rank}",
                    "final_node_id": node_id,
                    "final_label": _graph_node_label(node),
                    "chains": [route_node_ids],
                    "route_node_ids": route_node_ids,
                    "route_labels": [_graph_node_label(node_by_id[item]) for item in route_node_ids if item in node_by_id],
                    "depth": max(0, len(route_node_ids) - 1),
                    "leaf_node_ids": leaf_node_ids,
                }
            )
        terminal_claims.append(
            {
                "node_id": node_id,
                "label": _graph_node_label(node),
                "declaration_kind": node.get("declaration_kind"),
                "terminal_reason": "final_theorem_candidate_no_declaration_callers"
                if not callers_by_node.get(node_id)
                else "leaf_theorem_candidate_no_declaration_dependencies",
                "inbound_declaration_edge_count": len(callers_by_node.get(node_id, set())),
                "outbound_declaration_edge_count": len(deps_by_node.get(node_id, set())),
                "rank": rank,
            }
        )

    high_degree_nodes = []
    for rank, node_id in enumerate(
        sorted(
            declaration_node_ids,
            key=lambda item: (
                -(len(callers_by_node.get(item, set())) + len(deps_by_node.get(item, set()))),
                node_sort_key(item),
            ),
        )[:16],
        start=1,
    ):
        node = node_by_id[node_id]
        inbound = len(callers_by_node.get(node_id, set()))
        outbound = len(deps_by_node.get(node_id, set()))
        high_degree_nodes.append(
            {
                "node_id": node_id,
                "label": _graph_node_label(node),
                "declaration_kind": node.get("declaration_kind"),
                "in_degree": inbound,
                "out_degree": outbound,
                "total_degree": inbound + outbound,
                "rank": rank,
            }
        )

    external_dependencies = []
    for node_id, node in sorted(node_by_id.items(), key=lambda item: _graph_node_label(item[1])):
        if node.get("node_kind") != "external_package" and node.get("cluster_id") != "external":
            continue
        dependent_node_ids = sorted(
            {
                str(edge.get("from_node_id"))
                for edge in edges
                if str(edge.get("to_node_id")) == node_id
                and str(edge.get("from_node_id")) in declaration_node_ids
            },
            key=node_sort_key,
        )
        external_dependencies.append(
            {
                "external_node_id": node_id,
                "label": _graph_node_label(node),
                "dependent_node_ids": dependent_node_ids,
                "dependent_labels": [_graph_node_label(node_by_id[item]) for item in dependent_node_ids[:12]],
                "dependent_count": len(dependent_node_ids),
            }
        )

    layer_by_node: dict[str, int] = {}
    layer_order_by_node: dict[str, int] = {}
    for layer in dependency_layers:
        idx = int(layer.get("layer_index") or 0)
        for order, node_id in enumerate(layer.get("node_ids") or []):
            node_id = str(node_id)
            layer_by_node[node_id] = idx
            layer_order_by_node[node_id] = order

    family_by_node: dict[str, list[str]] = {node_id: [] for node_id in declaration_node_ids}
    family_label_by_id: dict[str, str] = {}
    family_color_by_id: dict[str, str] = {}
    for family in semantic_families:
        family_id = str(family.get("family_id") or "unknown")
        family_label_by_id[family_id] = str(family.get("label") or family_id)
        family_color_by_id[family_id] = str(family.get("color_token") or f"lean_family_{family_id}")
        for node_id in family.get("node_ids") or []:
            if str(node_id) in declaration_node_ids:
                family_by_node.setdefault(str(node_id), []).append(family_id)

    primary_route = final_theorem_routes[0] if final_theorem_routes else {}
    primary_route_id = str(primary_route.get("route_id") or "final_route_1")
    primary_route_node_ids = [
        str(node_id)
        for node_id in primary_route.get("route_node_ids") or []
        if str(node_id) in node_by_id
    ]
    primary_route_set = set(primary_route_node_ids)

    edge_by_pair: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    edge_by_id: dict[str, Mapping[str, Any]] = {}
    for edge in edges:
        edge_id = str(edge.get("edge_id") or "")
        from_id = str(edge.get("from_node_id") or "")
        to_id = str(edge.get("to_node_id") or "")
        if edge_id:
            edge_by_id[edge_id] = edge
        if from_id and to_id:
            edge_by_pair.setdefault((from_id, to_id), []).append(edge)
    for pair in list(edge_by_pair):
        edge_by_pair[pair] = sorted(edge_by_pair[pair], key=lambda item: _edge_id_sort_key(item.get("edge_id")))

    proof_spine_edge_ids: list[str] = []
    for from_id, to_id in zip(primary_route_node_ids, primary_route_node_ids[1:]):
        direct = edge_by_pair.get((from_id, to_id)) or []
        if direct:
            proof_spine_edge_ids.append(str(direct[0].get("edge_id")))

    declaration_undirected: dict[str, set[str]] = {node_id: set() for node_id in declaration_node_ids}
    all_undirected: dict[str, set[str]] = {node_id: set() for node_id in node_by_id}
    for edge in edges:
        from_id = str(edge.get("from_node_id") or "")
        to_id = str(edge.get("to_node_id") or "")
        if not from_id or not to_id:
            continue
        all_undirected.setdefault(from_id, set()).add(to_id)
        all_undirected.setdefault(to_id, set()).add(from_id)
        if from_id in declaration_node_ids and to_id in declaration_node_ids:
            declaration_undirected.setdefault(from_id, set()).add(to_id)
            declaration_undirected.setdefault(to_id, set()).add(from_id)

    terminal_node_ids = {str(row.get("node_id")) for row in terminal_claims if row.get("node_id")}
    external_node_ids = {
        str(row.get("external_node_id"))
        for row in external_dependencies
        if row.get("external_node_id")
    }
    route_distances = _multi_source_distances(primary_route_node_ids, all_undirected)
    terminal_distances = _multi_source_distances(sorted(terminal_node_ids), all_undirected)
    external_distances = _multi_source_distances(sorted(external_node_ids), all_undirected)
    descendant_cache: dict[str, set[str]] = {}
    ancestor_cache: dict[str, set[str]] = {}

    raw_importance: dict[str, float] = {}
    for node_id, node in node_by_id.items():
        in_degree = len(callers_by_node.get(node_id, set()))
        out_degree = len(deps_by_node.get(node_id, set()))
        descendant_count = len(_reachable_nodes(node_id, deps_by_node, descendant_cache)) if node_id in declaration_node_ids else 0
        terminal_distance = terminal_distances.get(node_id)
        external_distance = external_distances.get(node_id)
        raw_importance[node_id] = (
            (3.0 if node_id in primary_route_set else 0.0)
            + min(1.35, math.log1p(in_degree + out_degree) * 0.35)
            + min(1.0, math.log1p(descendant_count) * 0.22)
            + (0.75 / (terminal_distance + 1) if terminal_distance is not None else 0.0)
            + (0.35 / (external_distance + 1) if external_distance is not None else 0.0)
            + (0.45 if node_id in terminal_node_ids else 0.0)
            + (0.45 if node_id in external_node_ids else 0.0)
            + (0.18 if node.get("declaration_kind") in {"theorem", "lemma"} else 0.0)
        )
    max_importance = max(raw_importance.values(), default=1.0) or 1.0

    family_anchor_by_family_id: dict[str, str] = {}
    for family in semantic_families:
        family_id = str(family.get("family_id") or "unknown")
        candidates = [str(node_id) for node_id in family.get("node_ids") or [] if str(node_id) in declaration_node_ids]
        if not candidates:
            continue
        family_anchor_by_family_id[family_id] = min(
            candidates,
            key=lambda node_id: (-raw_importance.get(node_id, 0.0), node_sort_key(node_id)),
        )

    high_degree_node_ids = {str(row.get("node_id")) for row in high_degree_nodes if row.get("node_id")}
    family_anchor_node_ids = set(family_anchor_by_family_id.values())
    node_salience: dict[str, dict[str, Any]] = {}
    for node_id in sorted(node_by_id, key=node_sort_key):
        in_degree = len(callers_by_node.get(node_id, set()))
        out_degree = len(deps_by_node.get(node_id, set()))
        descendant_count = len(_reachable_nodes(node_id, deps_by_node, descendant_cache)) if node_id in declaration_node_ids else 0
        ancestor_count = len(_reachable_nodes(node_id, callers_by_node, ancestor_cache)) if node_id in declaration_node_ids else 0
        if node_id in external_node_ids:
            visual_role = "external_dependency"
        elif node_id in primary_route_set:
            visual_role = "primary_route"
        elif node_id in terminal_node_ids:
            visual_role = "terminal_claim"
        elif node_id in high_degree_node_ids:
            visual_role = "high_degree_anchor"
        elif node_id in family_anchor_node_ids:
            visual_role = "family_anchor"
        elif node_id in declaration_node_ids:
            visual_role = "sibling"
        else:
            visual_role = "other"
        node_salience[node_id] = {
            "node_id": node_id,
            "on_primary_route": node_id in primary_route_set,
            "route_distance": route_distances.get(node_id),
            "layer_index": layer_by_node.get(node_id),
            "semantic_family_ids": list(family_by_node.get(node_id, [])),
            "in_degree": in_degree,
            "out_degree": out_degree,
            "descendant_count": descendant_count,
            "ancestor_count": ancestor_count,
            "terminal_claim_distance": terminal_distances.get(node_id),
            "external_dependency_distance": external_distances.get(node_id),
            "importance_score": round(raw_importance.get(node_id, 0.0) / max_importance, 4),
            "visual_role": visual_role,
        }

    expansion_handles: dict[str, dict[str, Any]] = {}
    branch_bundles: list[dict[str, Any]] = []
    branch_bundle_count_by_anchor: Counter[str] = Counter()
    for anchor_id in primary_route_node_ids:
        layer_index = layer_by_node.get(anchor_id)
        if layer_index is None:
            continue
        layer = next((row for row in dependency_layers if int(row.get("layer_index") or 0) == layer_index), None)
        layer_ids = [str(node_id) for node_id in (layer or {}).get("node_ids") or []]
        sibling_ids = [
            node_id
            for node_id in layer_ids
            if node_id != anchor_id and node_id in declaration_node_ids
        ]
        sibling_ids.sort(key=node_sort_key)
        if not sibling_ids:
            continue
        member_ids = set(sibling_ids) | {anchor_id}
        local_edges = [
            edge
            for edge in declaration_edges
            if str(edge.get("from_node_id")) in member_ids
            and str(edge.get("to_node_id")) in member_ids
            and (
                str(edge.get("from_node_id")) in sibling_ids
                or str(edge.get("to_node_id")) in sibling_ids
            )
        ]
        edge_ids = [str(edge.get("edge_id")) for edge in sorted(local_edges, key=lambda item: _edge_id_sort_key(item.get("edge_id")))]
        edge_kind_counts = Counter(str(edge.get("edge_kind") or "unknown") for edge in local_edges)
        dominant_edge_kind = edge_kind_counts.most_common(1)[0][0] if edge_kind_counts else "none"
        handle_key = f"layer:{layer_index}:anchor:{anchor_id}"
        expansion_handles[handle_key] = {
            "handle_key": handle_key,
            "kind": "layer_branch_bundle",
            "node_ids": sibling_ids,
            "edge_ids": edge_ids,
            "summary": f"Layer {layer_index} siblings around {_graph_node_label(node_by_id.get(anchor_id, {}))}",
            "default_limit": min(12, max(1, len(sibling_ids))),
        }
        branch_bundle_count_by_anchor[anchor_id] += 1
        branch_bundles.append(
            {
                "bundle_id": f"layer_{layer_index}_branches_to_{_safe_token(anchor_id)}",
                "anchor_node_id": anchor_id,
                "layer_index": layer_index,
                "node_count": len(sibling_ids),
                "edge_count": len(edge_ids),
                "dominant_edge_kind": dominant_edge_kind,
                "sample_labels": [_graph_node_label(node_by_id[node_id]) for node_id in sibling_ids[:8]],
                "node_ids": sibling_ids,
                "edge_ids": edge_ids,
                "expansion_handle": {"kind": "layer_branch_bundle", "key": handle_key},
            }
        )

    route_steps: list[dict[str, Any]] = []
    for route_index, node_id in enumerate(primary_route_node_ids):
        node = node_by_id.get(node_id, {})
        layer_index = layer_by_node.get(node_id)
        hidden_sibling_count = 0
        if layer_index is not None:
            layer = next((row for row in dependency_layers if int(row.get("layer_index") or 0) == layer_index), None)
            hidden_sibling_count = max(0, int((layer or {}).get("node_count") or 0) - 1)
        route_steps.append(
            {
                "node_id": node_id,
                "label": _graph_node_label(node),
                "layer_index": layer_index,
                "route_index": route_index,
                "family_ids": list(family_by_node.get(node_id, [])),
                "hidden_sibling_count": hidden_sibling_count,
                "branch_bundle_count": int(branch_bundle_count_by_anchor.get(node_id, 0)),
                "importance_score": node_salience.get(node_id, {}).get("importance_score", 0.0),
            }
        )

    family_overlays: list[dict[str, Any]] = []
    for family in semantic_families:
        family_id = str(family.get("family_id") or "unknown")
        route_node_ids = [node_id for node_id in family.get("node_ids") or [] if str(node_id) in primary_route_set]
        if not route_node_ids:
            continue
        family_overlays.append(
            {
                "family_id": family_id,
                "label": family_label_by_id.get(family_id, family_id),
                "color_token": family_color_by_id.get(family_id, f"lean_family_{family_id}"),
                "route_node_ids": [str(node_id) for node_id in route_node_ids],
                "node_count": int(family.get("node_count") or len(family.get("node_ids") or [])),
                "anchor_node_id": family_anchor_by_family_id.get(family_id),
            }
        )

    external_dependency_chips: list[dict[str, Any]] = []
    for external in external_dependencies:
        route_touch = [
            str(node_id)
            for node_id in external.get("dependent_node_ids") or []
            if str(node_id) in primary_route_set
        ]
        if not route_touch:
            continue
        external_dependency_chips.append(
            {
                "external_node_id": external.get("external_node_id"),
                "label": external.get("label"),
                "route_node_ids": route_touch,
                "dependent_count": external.get("dependent_count", len(route_touch)),
            }
        )

    route_neighborhood = set(primary_route_node_ids)
    for node_id in primary_route_node_ids:
        route_neighborhood.update(declaration_undirected.get(node_id, set()))
    terminal_claim_chips = [
        {
            "node_id": row.get("node_id"),
            "label": row.get("label"),
            "declaration_kind": row.get("declaration_kind"),
            "terminal_reason": row.get("terminal_reason"),
            "rank": row.get("rank"),
        }
        for row in terminal_claims
        if str(row.get("node_id")) in route_neighborhood
    ]

    rank_by_node_id = {node_id: layer_by_node[node_id] for node_id in sorted(layer_by_node, key=node_sort_key)}
    lane_by_node_id = {
        node_id: layer_order_by_node[node_id]
        for node_id in sorted(layer_order_by_node, key=node_sort_key)
    }
    for route_index, node_id in enumerate(primary_route_node_ids):
        lane_by_node_id[node_id] = route_index
    family_lane_by_family_id = {
        str(family.get("family_id")): index
        for index, family in enumerate(semantic_families)
        if family.get("family_id")
    }
    layout_hints = {
        "rank_by_node_id": rank_by_node_id,
        "lane_by_node_id": lane_by_node_id,
        "family_lane_by_family_id": family_lane_by_family_id,
        "route_step_order": list(primary_route_node_ids),
    }

    transitive_reduction_edge_ids = _transitive_reduction_edge_ids(declaration_edges)
    bundle_groups: dict[tuple[int, int, str, str], list[Mapping[str, Any]]] = {}
    for edge in declaration_edges:
        from_id = str(edge.get("from_node_id") or "")
        to_id = str(edge.get("to_node_id") or "")
        from_layer = layer_by_node.get(from_id)
        to_layer = layer_by_node.get(to_id)
        if from_layer is None or to_layer is None or from_layer == to_layer:
            continue
        from_family = _first_family_id(family_by_node.get(from_id))
        to_family = _first_family_id(family_by_node.get(to_id))
        bundle_groups.setdefault((from_layer, to_layer, from_family, to_family), []).append(edge)

    bundle_edges: list[dict[str, Any]] = []
    for (from_layer, to_layer, from_family, to_family), grouped_edges in sorted(
        bundle_groups.items(),
        key=lambda item: (item[0][0], item[0][1], item[0][2], item[0][3]),
    ):
        node_ids = sorted(
            {
                str(edge.get("from_node_id"))
                for edge in grouped_edges
                if edge.get("from_node_id")
            }
            | {
                str(edge.get("to_node_id"))
                for edge in grouped_edges
                if edge.get("to_node_id")
            },
            key=node_sort_key,
        )
        sorted_edges = sorted(
            grouped_edges,
            key=lambda edge: (
                -int(str(edge.get("from_node_id")) in primary_route_set or str(edge.get("to_node_id")) in primary_route_set),
                -(
                    float(node_salience.get(str(edge.get("from_node_id")), {}).get("importance_score") or 0.0)
                    + float(node_salience.get(str(edge.get("to_node_id")), {}).get("importance_score") or 0.0)
                ),
                _edge_id_sort_key(edge.get("edge_id")),
            ),
        )
        edge_ids = [str(edge.get("edge_id")) for edge in sorted(grouped_edges, key=lambda item: _edge_id_sort_key(item.get("edge_id")))]
        bundle_id = (
            f"bundle:from:{from_layer}:{_safe_token(from_family)}:"
            f"to:{to_layer}:{_safe_token(to_family)}"
        )
        handle_key = bundle_id
        expansion_handles[handle_key] = {
            "handle_key": handle_key,
            "kind": "edge_bundle",
            "node_ids": node_ids,
            "edge_ids": edge_ids,
            "summary": (
                f"{family_label_by_id.get(from_family, from_family)} layer {from_layer} "
                f"to {family_label_by_id.get(to_family, to_family)} layer {to_layer}"
            ),
            "default_limit": min(12, max(1, len(node_ids))),
        }
        bundle_edges.append(
            {
                "bundle_id": bundle_id,
                "from_layer": from_layer,
                "to_layer": to_layer,
                "from_family": from_family,
                "to_family": to_family,
                "edge_kind_counts": dict(sorted(Counter(str(edge.get("edge_kind") or "unknown") for edge in grouped_edges).items())),
                "node_count": len(node_ids),
                "edge_count": len(edge_ids),
                "representative_edge_ids": [str(edge.get("edge_id")) for edge in sorted_edges[:4]],
                "expansion_handle": {"kind": "edge_bundle", "key": handle_key},
            }
        )

    condensed_node_ids: list[str] = []
    seen_condensed: set[str] = set()

    def add_condensed(node_id: Any) -> None:
        token = str(node_id or "")
        if not token or token in seen_condensed or token not in declaration_node_ids:
            return
        seen_condensed.add(token)
        condensed_node_ids.append(token)

    for node_id in primary_route_node_ids:
        add_condensed(node_id)
    for node_id in family_anchor_by_family_id.values():
        add_condensed(node_id)
    for row in high_degree_nodes:
        add_condensed(row.get("node_id"))
    for row in terminal_claims:
        add_condensed(row.get("node_id"))
    condensed_edge_ids = [
        edge_id
        for edge_id in transitive_reduction_edge_ids
        if str(edge_by_id.get(edge_id, {}).get("from_node_id")) in seen_condensed
        and str(edge_by_id.get(edge_id, {}).get("to_node_id")) in seen_condensed
    ]

    proof_spine_bundle = {
        "primary_route_id": primary_route_id,
        "final_label": primary_route.get("final_label"),
        "route_steps": route_steps,
        "route_edges": proof_spine_edge_ids,
        "branch_bundles": branch_bundles,
        "family_overlays": family_overlays,
        "external_dependency_chips": external_dependency_chips,
        "terminal_claim_chips": terminal_claim_chips,
    }
    edge_views = {
        "full_edges": [str(edge.get("edge_id")) for edge in sorted(edges, key=lambda item: _edge_id_sort_key(item.get("edge_id")))],
        "transitive_reduction_edges": transitive_reduction_edge_ids,
        "proof_spine_edges": list(proof_spine_edge_ids),
        "bundle_edges": bundle_edges,
    }
    condensed_dag = {
        "nodes": condensed_node_ids,
        "edges": condensed_edge_ids,
        "family_anchor_node_ids": dict(family_anchor_by_family_id),
        "layout_hints": {
            "rank_by_node_id": {node_id: rank_by_node_id[node_id] for node_id in condensed_node_ids if node_id in rank_by_node_id},
            "lane_by_node_id": {node_id: lane_by_node_id[node_id] for node_id in condensed_node_ids if node_id in lane_by_node_id},
            "lane_by_family": dict(family_lane_by_family_id),
        },
    }

    values_by_key = {
        "dependency_layers": dependency_layers,
        "semantic_families": semantic_families,
        "final_theorem_routes": final_theorem_routes,
        "high_degree_nodes": high_degree_nodes,
        "terminal_claims": terminal_claims,
        "external_dependencies": external_dependencies,
    }
    empty_keys = [key for key, value in values_by_key.items() if not value]
    return {
        "schema_version": GRAPH_VIEW_SCHEMA_VERSION,
        "legacy_schema_version": GRAPH_VIEW_LEGACY_SCHEMA_VERSION,
        "available": bool(declaration_node_ids),
        "source_ref": "visual_surfaces.declaration_graph",
        "source_fingerprint": currentness.get("source_fingerprint"),
        "inference": {
            "mode": "static_projection_name_edge_inference",
            "proof_authority": "none; graph views are projection-only and do not run Lean",
            "edge_direction": "from declaration to declaration it lexically references",
            "importance_score_formula": (
                "normalized deterministic weighted sum: primary-route flag, log(degree), "
                "log(descendant_count), terminal/external proximity, terminal/external roles, theorem-kind bonus"
            ),
            "layout_contract": "backend supplies semantic view registry, ordering hints, bundles, and handles; frontend computes pixels",
        },
        "view_keys": list(GRAPH_VIEW_KEYS),
        "view_registry": [dict(row) for row in GRAPH_VIEW_REGISTRY],
        "capabilities": {
            "has_view_registry": True,
            "has_proof_spine_bundle": bool(route_steps),
            "has_layout_hints": bool(layout_hints["route_step_order"]),
            "has_expansion_handles": bool(expansion_handles),
            "has_edge_views": bool(edge_views["full_edges"]),
            "has_salience": bool(node_salience),
            "has_condensed_dag": bool(condensed_node_ids),
        },
        **values_by_key,
        "proof_spine_bundle": proof_spine_bundle,
        "layout_hints": layout_hints,
        "expansion_handles": expansion_handles,
        "node_salience": node_salience,
        "edge_views": edge_views,
        "condensed_dag": condensed_dag,
        "omission_receipt": {
            "status": "complete" if declaration_node_ids else "degraded",
            "issues": [f"empty:{key}" for key in empty_keys],
            "derived_fields": [
                "dependency_layers",
                "semantic_families",
                "final_theorem_routes",
                "node_salience",
                "proof_spine_bundle",
                "edge_views",
                "condensed_dag",
            ],
            "reason": "graph_views are derived from declaration_graph nodes/edges plus name-based semantic families; source artifacts remain authority",
        },
    }


def _declarations_by_node_id(visual_surfaces: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    catalog = visual_surfaces.get("declaration_catalog")
    declarations = catalog.get("declarations") if isinstance(catalog, Mapping) else []
    return {
        str(row.get("node_id")): row
        for row in declarations or []
        if isinstance(row, Mapping) and row.get("node_id")
    }


def _declarations_by_name(visual_surfaces: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    catalog = visual_surfaces.get("declaration_catalog")
    declarations = catalog.get("declarations") if isinstance(catalog, Mapping) else []
    rows: dict[str, Mapping[str, Any]] = {}
    for row in declarations or []:
        if not isinstance(row, Mapping):
            continue
        name = str(row.get("name") or "")
        if not name:
            continue
        rows.setdefault(name, row)
        rows.setdefault(name.split(".")[-1], row)
    return rows


def _declaration_by_lean_name(
    declaration_by_name: Mapping[str, Mapping[str, Any]],
    name: Any,
) -> Mapping[str, Any]:
    target = str(name or "")
    if not target:
        return {}
    candidates = [target, target.split(".")[-1]]
    for candidate in candidates:
        if candidate in declaration_by_name:
            return declaration_by_name[candidate]
    suffix = "." + target.split(".")[-1]
    return next((row for key, row in declaration_by_name.items() if key.endswith(suffix)), {})


def _source_span_for_declaration(declaration: Mapping[str, Any] | None) -> dict[str, Any]:
    if not declaration:
        return {}
    return {
        "source_ref": declaration.get("file"),
        "line_start": declaration.get("line_start"),
        "line_end": declaration.get("line_end"),
        "module_id": declaration.get("module_id"),
    }


def _lean_static_risk_summary(lean_projects: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    totals = Counter()
    project_rows: list[dict[str, Any]] = []
    for project in lean_projects:
        scan = project.get("static_risk_scan") if isinstance(project.get("static_risk_scan"), Mapping) else {}
        row = {
            "project_id": project.get("project_id"),
            "project_root": project.get("project_root"),
            "sorry_count": int(scan.get("sorry_count") or 0),
            "admit_count": int(scan.get("admit_count") or 0),
            "axiom_count": int(scan.get("axiom_count") or 0),
        }
        totals.update(
            {
                "sorry_count": row["sorry_count"],
                "admit_count": row["admit_count"],
                "axiom_count": row["axiom_count"],
            }
        )
        project_rows.append(row)
    blocking_count = totals["sorry_count"] + totals["admit_count"] + totals["axiom_count"]
    return {
        "status": "PASS" if blocking_count == 0 else "REVIEW",
        "sorry_count": totals["sorry_count"],
        "admit_count": totals["admit_count"],
        "axiom_count": totals["axiom_count"],
        "project_rows": project_rows,
        "claim_boundary": "static token scan is a risk audit, not proof authority or a replacement for Lean #print axioms",
    }


def _receipt_chain_from_threads(formal_math_threads: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for thread in formal_math_threads:
        thread_id = str(thread.get("thread_id") or "unknown")
        for index, receipt in enumerate(thread.get("receipt_artifacts") or [], start=1):
            if not isinstance(receipt, Mapping):
                continue
            path = str(receipt.get("path") or "")
            if not path:
                continue
            rows.append(
                {
                    "receipt_id": f"{thread_id}:{index}:{Path(path).stem}",
                    "thread_id": thread_id,
                    "status": receipt.get("status"),
                    "artifact_ref": path,
                }
            )
    return rows


def _certificate_object_rows(
    graph_views: Mapping[str, Any],
    declaration_by_node_id: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    proof_spine = graph_views.get("proof_spine_bundle") if isinstance(graph_views.get("proof_spine_bundle"), Mapping) else {}
    family_by_id = {
        str(family.get("family_id")): family
        for family in graph_views.get("semantic_families") or []
        if isinstance(family, Mapping) and family.get("family_id")
    }
    family_overlays = proof_spine.get("family_overlays") if isinstance(proof_spine.get("family_overlays"), list) else []
    rows: list[dict[str, Any]] = []
    for overlay in family_overlays:
        if not isinstance(overlay, Mapping):
            continue
        family_id = str(overlay.get("family_id") or "other")
        family = family_by_id.get(family_id, {})
        route_node_ids = [str(node_id) for node_id in overlay.get("route_node_ids") or [] if str(node_id)]
        route_declarations = []
        for node_id in route_node_ids:
            declaration = declaration_by_node_id.get(node_id)
            if not declaration:
                continue
            route_declarations.append(
                {
                    "node_id": node_id,
                    "name": declaration.get("name"),
                    "kind": declaration.get("kind"),
                    **_source_span_for_declaration(declaration),
                }
            )
        rows.append(
            {
                "object_id": f"semantic_family:{family_id}",
                "family_id": family_id,
                "label": overlay.get("label") or family.get("label") or family_id,
                "role": CERTIFICATE_OBJECT_ROLE_BY_FAMILY.get(
                    family_id,
                    CERTIFICATE_OBJECT_ROLE_BY_FAMILY["other"],
                ),
                "route_node_ids": route_node_ids,
                "route_declarations": route_declarations,
                "node_count": overlay.get("node_count") or family.get("node_count") or len(route_node_ids),
                "anchor_node_id": overlay.get("anchor_node_id") or family.get("anchor_node_id"),
                "sample_labels": list(family.get("sample_labels") or [])[:8],
                "authority_boundary": (
                    "certificate-object semantics are projected from declaration names, graph route membership, "
                    "and semantic families; Lean source and receipts remain authority"
                ),
            }
        )
    return rows


def _lean_declaration_regions(text: str) -> dict[str, dict[str, Any]]:
    declaration_pattern = re.compile(
        r"^\s*(theorem|lemma|def|structure|class|abbrev|inductive)\s+([A-Za-z0-9_'.]+)"
    )
    lines = text.splitlines()
    starts: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        match = declaration_pattern.match(line)
        if match:
            starts.append((index, match.group(1), match.group(2)))

    regions: dict[str, dict[str, Any]] = {}
    for position, (start_index, kind, name) in enumerate(starts):
        end_exclusive = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        regions[name] = {
            "kind": kind,
            "name": name,
            "line_start": start_index + 1,
            "line_end": end_exclusive,
            "body": "\n".join(lines[start_index:end_exclusive]),
        }
    return regions


def _lean_region_for_name(regions: Mapping[str, Mapping[str, Any]], name: Any) -> Mapping[str, Any]:
    target = str(name or "")
    if not target:
        return {}
    return regions.get(target) or regions.get(target.split(".")[-1]) or {}


def _int_or_none(value: Any) -> int | None:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _source_ref_for_named_declaration(
    *,
    name: str,
    declaration_by_name: Mapping[str, Mapping[str, Any]],
    fallback_source_ref: str,
    fallback_regions: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    declaration = _declaration_by_lean_name(declaration_by_name, name)
    if declaration:
        return {
            "name": declaration.get("name") or name,
            **_source_span_for_declaration(declaration),
        }
    region = _lean_region_for_name(fallback_regions, name)
    return {
        "name": name,
        "source_ref": fallback_source_ref,
        "line_start": region.get("line_start"),
        "line_end": region.get("line_end"),
        "module_id": None,
    }


def _build_certificate_microscope(
    *,
    repo_root: Path,
    visual_surfaces: Mapping[str, Any],
    target_runner: Mapping[str, Any],
) -> dict[str, Any]:
    authority_boundary = (
        "Parsed certificate microscope data is an inspectability projection from generated Lean source; "
        "Lean target-runner receipts and axiom audits remain proof authority."
    )
    target_theorem = str(target_runner.get("target_theorem") or "")
    base_receipt = {
        "parser": "regex_over_generated_lean_source",
        "status": "MISSING_TARGET_RUNNER",
        "issues": [],
    }
    if not target_theorem:
        return {
            "schema_version": "lean_certificate_microscope_v0",
            "available": False,
            "target_theorem": None,
            "row_cases": [],
            "table_route": [],
            "parse_receipt": base_receipt,
            "authority_boundary": authority_boundary,
        }

    issues: list[str] = []
    declaration_by_name = _declarations_by_name(visual_surfaces)
    target_declaration = _declaration_by_lean_name(declaration_by_name, target_theorem)
    target_source_ref = str(target_declaration.get("file") or "")
    if not target_source_ref:
        issues.append("target_theorem_declaration_not_resolved")
        return {
            "schema_version": "lean_certificate_microscope_v0",
            "available": False,
            "target_theorem": target_theorem,
            "target_source_ref": None,
            "row_cases": [],
            "table_route": [],
            "parse_receipt": {**base_receipt, "status": "DEGRADED", "issues": issues},
            "authority_boundary": authority_boundary,
        }

    target_path = _repo_path(target_source_ref, repo_root=repo_root)
    if not target_path.is_file():
        issues.append("target_theorem_source_missing")
        return {
            "schema_version": "lean_certificate_microscope_v0",
            "available": False,
            "target_theorem": target_theorem,
            "target_source_ref": target_source_ref,
            "row_cases": [],
            "table_route": [],
            "parse_receipt": {**base_receipt, "status": "DEGRADED", "issues": issues},
            "authority_boundary": authority_boundary,
        }

    target_text = target_path.read_text(encoding="utf-8")
    target_regions = _lean_declaration_regions(target_text)
    target_region = _lean_region_for_name(target_regions, target_declaration.get("name") or target_theorem)
    target_body = str(target_region.get("body") or target_text)
    target_parameters: dict[str, Any] = {}
    call_match = re.search(
        r"finite_period_noncollapse_from_emitted_certificate_table\s+"
        r"([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)",
        target_body,
        re.S,
    )
    if call_match:
        L, A, B, Q, b = (int(item) for item in call_match.groups())
        target_parameters = {
            "L": L,
            "A": A,
            "B": B,
            "Q": Q,
            "b": b,
            "denominator_norm": Q,
        }
    else:
        issues.append("target_runner_call_parameters_not_resolved")

    certificate_name_match = re.search(r"\b(emittedCertificate_[A-Za-z0-9_']+)\b", target_body)
    certificate_name = certificate_name_match.group(1) if certificate_name_match else ""
    certificate_declaration = _declaration_by_lean_name(declaration_by_name, certificate_name)
    certificate_source_ref = str(certificate_declaration.get("file") or target_source_ref)
    certificate_path = _repo_path(certificate_source_ref, repo_root=repo_root)
    certificate_text = certificate_path.read_text(encoding="utf-8") if certificate_path.is_file() else target_text
    certificate_regions = _lean_declaration_regions(certificate_text)

    if not certificate_name:
        for match in re.finditer(
            r"\bdef\s+(emittedCertificate_[A-Za-z0-9_']+)\s*:\s*"
            r"EmittedCertificateTable\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)",
            certificate_text,
            re.S,
        ):
            if not target_parameters or (
                int(match.group(2)) == target_parameters.get("L")
                and int(match.group(3)) == target_parameters.get("A")
                and int(match.group(4)) == target_parameters.get("b")
            ):
                certificate_name = match.group(1)
                certificate_declaration = _declaration_by_lean_name(declaration_by_name, certificate_name)
                certificate_source_ref = str(certificate_declaration.get("file") or certificate_source_ref)
                break
    if not certificate_name:
        issues.append("emitted_certificate_name_not_resolved")

    certificate_region = _lean_region_for_name(certificate_regions, certificate_name)
    certificate_body = str(certificate_region.get("body") or "")
    certificate_parameters: dict[str, Any] = {}
    certificate_type_match = (
        re.search(
            rf"\bdef\s+{re.escape(certificate_name)}\s*:\s*"
            r"EmittedCertificateTable\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)",
            certificate_text,
            re.S,
        )
        if certificate_name
        else None
    )
    if certificate_type_match:
        certificate_parameters = {
            "L": int(certificate_type_match.group(1)),
            "A": int(certificate_type_match.group(2)),
            "b": int(certificate_type_match.group(3)),
        }
    elif certificate_name:
        issues.append("emitted_certificate_type_parameters_not_resolved")
    if certificate_parameters:
        target_parameters = {**certificate_parameters, **target_parameters}

    rows_match = re.search(r"rows\s*:=\s*\(\{([^}]*)\}\s*:\s*Finset\s+Nat\)", certificate_body)
    rows = [int(item) for item in re.findall(r"[0-9]+", rows_match.group(1) if rows_match else "")]
    if certificate_name and not rows:
        issues.append("emitted_certificate_rows_not_resolved")

    L = target_parameters.get("L")
    A = target_parameters.get("A")
    b = target_parameters.get("b")
    row_kind_by_p = {
        int(match.group(1)): str(match.group(2))
        for match in re.finditer(
            r"CanonicalWitnessRowCase\s+[0-9]+\s+[0-9]+\s+[0-9]+\s+([0-9]+).*?"
            r"EmittedGeneratedRowCase\.([A-Za-z0-9_'.]+)",
            certificate_body,
            re.S,
        )
    }
    row_cases: list[dict[str, Any]] = []
    for p in rows:
        row_issues: list[str] = []
        witness_match = (
            re.search(
                rf"\btheorem\s+([A-Za-z0-9_'.]+)\s*:\s*"
                rf"PrimeComponentWitness\s+{L}\s+{A}\s+{b}\s+{p}\s+([0-9]+)"
                r"\s*:=\s*by(?P<body>.*?)(?=^\s*(?:theorem|lemma|def|structure|class|abbrev|inductive)\s+|\Z)",
                certificate_text,
                re.S | re.M,
            )
            if L is not None and A is not None and b is not None
            else None
        )
        case_match = (
            re.search(
                rf"\btheorem\s+([A-Za-z0-9_'.]+)\s*:\s*"
                rf"CanonicalWitnessRowCase\s+{L}\s+{A}\s+{b}\s+{p}"
                r"\s*:=\s*by(?P<body>.*?)(?=^\s*(?:theorem|lemma|def|structure|class|abbrev|inductive)\s+|\Z)",
                certificate_text,
                re.S | re.M,
            )
            if L is not None and A is not None and b is not None
            else None
        )
        witness_name = witness_match.group(1) if witness_match else ""
        witness_q = _int_or_none(witness_match.group(2) if witness_match else None)
        witness_body = witness_match.group("body") if witness_match else ""
        quotient_match = (
            re.search(rf"primeComponentQuotient\s+{b}\s+{L}\s+{p}\s*=\s*([0-9]+)", witness_body)
            if L is not None and b is not None
            else None
        )
        quotient = _int_or_none(quotient_match.group(1) if quotient_match else None)
        quotient_exponent = None
        A_exponent = None
        if witness_q is not None:
            quotient_factor_match = re.search(
                rf"\(([0-9]+)\s*:\s*Nat\)\.factorization\s+{witness_q}\s*=\s*([0-9]+)",
                witness_body,
            )
            if quotient_factor_match:
                quotient = quotient or _int_or_none(quotient_factor_match.group(1))
                quotient_exponent = _int_or_none(quotient_factor_match.group(2))
            if A is not None:
                A_factor_match = re.search(
                    rf"\({A}\s*:\s*Nat\)\.factorization\s+{witness_q}\s*=\s*([0-9]+)",
                    witness_body,
                )
                A_exponent = _int_or_none(A_factor_match.group(1) if A_factor_match else None)
        row_case_name = case_match.group(1) if case_match else ""
        row_kind = row_kind_by_p.get(p)
        if not row_kind and case_match and "Or.inr (Or.inr" in case_match.group("body"):
            row_kind = "prime_witness"
        if not row_kind:
            row_kind = "unknown"
            row_issues.append("row_kind_not_resolved")
        if not witness_name:
            row_issues.append("prime_component_witness_theorem_not_resolved")
        if witness_q is None:
            row_issues.append("witness_prime_not_resolved")
        if quotient is None:
            row_issues.append("prime_component_quotient_not_resolved")
        if quotient_exponent is None:
            row_issues.append("quotient_factorization_exponent_not_resolved")
        if A_exponent is None:
            row_issues.append("A_factorization_exponent_not_resolved")
        if not row_case_name:
            row_issues.append("canonical_witness_row_case_not_resolved")
        row_cases.append(
            {
                "row_id": f"{certificate_name or 'emitted_certificate'}:p{p}",
                "p": p,
                "row_kind": row_kind,
                "witness_prime_q": witness_q,
                "prime_component_quotient": quotient,
                "quotient_factorization_exponent": quotient_exponent,
                "A_factorization_exponent": A_exponent,
                "witness_theorem": _source_ref_for_named_declaration(
                    name=witness_name,
                    declaration_by_name=declaration_by_name,
                    fallback_source_ref=certificate_source_ref,
                    fallback_regions=certificate_regions,
                )
                if witness_name
                else {},
                "row_case_theorem": _source_ref_for_named_declaration(
                    name=row_case_name,
                    declaration_by_name=declaration_by_name,
                    fallback_source_ref=certificate_source_ref,
                    fallback_regions=certificate_regions,
                )
                if row_case_name
                else {},
                "semantic_claim": (
                    f"row p={p} is discharged by witness prime q={witness_q}; "
                    f"primeComponentQuotient {b} {L} {p} has q-exponent {quotient_exponent}, "
                    f"while A={A} has q-exponent {A_exponent}"
                ),
                "issues": row_issues,
                "authority_boundary": authority_boundary,
            }
        )
        issues.extend(f"row_p{p}:{issue}" for issue in row_issues)

    certificate_def = (
        {
            **_source_ref_for_named_declaration(
                name=certificate_name,
                declaration_by_name=declaration_by_name,
                fallback_source_ref=certificate_source_ref,
                fallback_regions=certificate_regions,
            ),
            "type": "EmittedCertificateTable",
            "parameters": certificate_parameters,
            "rows": rows,
        }
        if certificate_name
        else {}
    )
    target_source = {
        **_source_ref_for_named_declaration(
            name=str(target_declaration.get("name") or target_theorem),
            declaration_by_name=declaration_by_name,
            fallback_source_ref=target_source_ref,
            fallback_regions=target_regions,
        ),
        "target_runner_ref": target_runner.get("ref"),
        "target_runner_status": target_runner.get("status"),
    }
    table_route = [
        {
            "step_id": "emitted_certificate_rows",
            "label": "EmittedCertificateTable.rows",
            "source_ref": certificate_def.get("source_ref"),
            "claim": "the generated table enumerates the p-rows covering L.factorization.support",
        },
        {
            "step_id": "covers_factor_support",
            "label": "covers_factor_support",
            "source_ref": certificate_def.get("source_ref"),
            "claim": "each prime factor of L is routed into an emitted certificate row",
        },
        {
            "step_id": "row_sound",
            "label": "row_sound",
            "source_ref": certificate_def.get("source_ref"),
            "claim": "each emitted row supplies an EmittedGeneratedRowCase",
        },
        {
            "step_id": "finite_period_noncollapse_from_emitted_certificate_table",
            "label": "finite_period_noncollapse_from_emitted_certificate_table",
            "source_ref": target_source.get("source_ref"),
            "claim": "the emitted table is consumed by the period noncollapse kernel",
        },
        {
            "step_id": "target_runner_theorem",
            "label": target_theorem,
            "source_ref": target_source.get("source_ref"),
            "claim": "the target runner checked this generated endpoint under its receipt boundary",
        },
    ]
    if rows and len(row_cases) != len(rows):
        issues.append("row_case_count_mismatch")

    return {
        "schema_version": "lean_certificate_microscope_v0",
        "available": bool(certificate_def and rows and row_cases),
        "target_theorem": target_theorem,
        "target_source": target_source,
        "target_parameters": target_parameters,
        "certificate_def": certificate_def,
        "row_cases": row_cases,
        "table_route": table_route,
        "parse_receipt": {
            "parser": "regex_over_generated_lean_source",
            "status": "PASS" if not issues else "DEGRADED",
            "issues": issues,
            "source_ref": certificate_source_ref,
            "source_sha256": _file_sha(certificate_path) if certificate_path.is_file() else _file_sha(target_path),
            "target_source_sha256": _file_sha(target_path),
        },
        "authority_boundary": authority_boundary,
    }


def _basename(rel_file: Any) -> str:
    return str(rel_file or "").rsplit("/", 1)[-1]


def _conceptual_layer_for(rel_file: Any, line_start: Any) -> dict[str, Any] | None:
    """Resolve a declaration's curated conceptual layer.

    Returns ``None`` when the file has no curated band map and no file-role match,
    so the consumer falls back to the machine-derived topological dependency_layers.
    """
    rel = str(rel_file or "")
    basename = _basename(rel)
    line = int(line_start or 0)
    bands = PROOF_ARCHITECTURE_LAYER_BANDS_BY_BASENAME.get(basename)
    if bands:
        chosen: Mapping[str, Any] | None = None
        for band in bands:  # bands are ordered ascending by line_band_start
            if line >= int(band["line_band_start"]):
                chosen = band
            else:
                break
        if chosen is not None:
            return {
                "layer_id": chosen["layer_id"],
                "ordinal": chosen["ordinal"],
                "title": chosen["title"],
                "assignment_method": "heuristic_source_line_band",
            }
    for role_layer in PROOF_ARCHITECTURE_FILE_ROLE_LAYERS:
        kind, _, value = str(role_layer["match"]).partition(":")
        if (kind == "path_contains" and value in rel) or (kind == "basename" and basename == value):
            return {
                "layer_id": role_layer["layer_id"],
                "ordinal": role_layer["ordinal"],
                "title": role_layer["title"],
                "assignment_method": "file_role",
            }
    return None


def _mathematical_annotation_for(name: Any) -> dict[str, str] | None:
    target = str(name or "")
    if not target:
        return None
    if target in MATHEMATICAL_ANNOTATIONS:
        return MATHEMATICAL_ANNOTATIONS[target]
    return MATHEMATICAL_ANNOTATIONS.get(target.split(".")[-1])


def _proof_layer_for_declaration(declaration: Mapping[str, Any]) -> dict[str, Any]:
    conceptual = _conceptual_layer_for(declaration.get("file"), declaration.get("line_start"))
    annotation = _mathematical_annotation_for(declaration.get("name"))
    layer: dict[str, Any] = {}
    if conceptual:
        layer.update(conceptual)
    elif annotation and annotation.get("conceptual_layer_id"):
        layer.update(
            {
                "layer_id": annotation["conceptual_layer_id"],
                "assignment_method": "curated_annotation_anchor",
            }
        )
    if annotation:
        layer["significance"] = annotation["significance"]
        layer["plain_math"] = annotation["plain_math"]
        layer["annotation_authority"] = PROOF_ARCHITECTURE_ANNOTATION_AUTHORITY
    return layer


def _attach_proof_layers(declaration_rows: list[dict[str, Any]]) -> None:
    for row in declaration_rows:
        layer = _proof_layer_for_declaration(row)
        if layer:
            row["proof_layer"] = layer


_FILE_OVERHEAD_PROFILE_PHASES = frozenset({"import"})


def _profile_events(run: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    profile = run.get("profile") if isinstance(run.get("profile"), Mapping) else {}
    events = profile.get("events")
    return [event for event in events if isinstance(event, Mapping)] if isinstance(events, list) else []


def _profiled_run_source_rel(run: Mapping[str, Any]) -> str | None:
    execution_context = run.get("execution_context") if isinstance(run.get("execution_context"), Mapping) else {}
    for candidate in (execution_context.get("target_file"), run.get("source_path")):
        if isinstance(candidate, str) and candidate.startswith("formal_math"):
            return candidate
    cwd = execution_context.get("cwd")
    args = run.get("args") if isinstance(run.get("args"), list) else []
    profile_arg = next((arg for arg in reversed(args) if isinstance(arg, str) and arg.endswith(".lean")), None)
    if isinstance(cwd, str) and profile_arg:
        return f"{cwd.rstrip('/')}/{profile_arg}"
    candidate = execution_context.get("target_file") or run.get("source_path")
    return candidate if isinstance(candidate, str) else None


def _select_profiled_runs_by_file(*, repo_root: Path) -> dict[str, dict[str, Any]]:
    """Latest projection-relevant PASS profile run per profiled Lean file.

    Diagnostic rows are sorted ascending by path, so later (newer) runs overwrite
    earlier ones and the most recent PASS profile wins. ENVIRONMENT_BLOCKED rows are
    already excluded as observation-only by ``_lean_diagnostic_run_rows``.
    """
    chosen: dict[str, dict[str, Any]] = {}
    for row in _lean_diagnostic_run_rows(repo_root=repo_root):
        if not row.get("projection_relevant"):
            continue
        payload = row.get("payload") or {}
        if str(payload.get("status") or "").upper() != "PASS":
            continue
        source_rel = _profiled_run_source_rel(payload)
        if not source_rel:
            continue
        chosen[source_rel] = {"path": row["path"], "payload": payload}
    return chosen


def _declaration_spans(
    file_rows: Sequence[Mapping[str, Any]], total_lines: int
) -> list[tuple[int, int, Mapping[str, Any]]]:
    """Full-body line span [start, end] per declaration, mirroring the edge-scan logic."""
    ordered = sorted(file_rows, key=lambda row: int(row.get("line_start") or 0))
    spans: list[tuple[int, int, Mapping[str, Any]]] = []
    for index, row in enumerate(ordered):
        start = int(row.get("line_start") or 1)
        if index + 1 < len(ordered):
            next_start = int(ordered[index + 1].get("line_start") or (total_lines + 1))
        else:
            next_start = total_lines + 1
        spans.append((start, max(start, next_start - 1), row))
    return spans


def _map_profile_events_to_declarations(
    events: Sequence[Mapping[str, Any]],
    spans: Sequence[tuple[int, int, Mapping[str, Any]]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    per_node: dict[str, dict[str, Any]] = {}
    overhead_ms = 0.0
    overhead_events = 0
    for event in events:
        duration = float(event.get("duration_ms") or 0.0)
        phase = str(event.get("phase") or "")
        line = event.get("line")
        owner: Mapping[str, Any] | None = None
        if phase not in _FILE_OVERHEAD_PROFILE_PHASES and isinstance(line, int):
            for start, end, row in spans:
                if start <= line <= end:
                    owner = row
                    break
        if owner is None:
            overhead_ms += duration
            overhead_events += 1
            continue
        node_id = str(owner.get("node_id") or "")
        acc = per_node.setdefault(
            node_id,
            {"row": owner, "total_duration_ms": 0.0, "event_count": 0, "phase_totals": {}},
        )
        acc["total_duration_ms"] += duration
        acc["event_count"] += 1
        acc["phase_totals"][phase] = acc["phase_totals"].get(phase, 0.0) + duration
    return per_node, {
        "file_overhead_duration_ms": round(overhead_ms, 3),
        "file_overhead_event_count": overhead_events,
    }


def _execution_profile_payload(
    acc: Mapping[str, Any],
    *,
    file_total_ms: float,
    profiled_ref: str | None,
    profiled_sha: str | None,
    current_sha: str | None,
    freshness: str,
) -> dict[str, Any]:
    phase_totals = acc["phase_totals"]
    total = round(float(acc["total_duration_ms"]), 3)
    breakdown = sorted(
        ({"phase": phase, "duration_ms": round(ms, 3)} for phase, ms in phase_totals.items()),
        key=lambda row: (-row["duration_ms"], row["phase"]),
    )
    dominant = breakdown[0]["phase"] if breakdown else None
    return {
        "available": True,
        "total_duration_ms": total,
        "event_count": int(acc["event_count"]),
        "dominant_phase": dominant,
        "phase_breakdown": breakdown,
        "pct_of_profiled_file": round(100.0 * total / file_total_ms, 2) if file_total_ms else None,
        "profiled_run_ref": profiled_ref,
        "profiled_source_sha256": profiled_sha,
        "current_source_sha256": current_sha,
        "profile_freshness": freshness,
        "claim_boundary": (
            "Lean --profile timing for this declaration's source span; diagnostic evidence, not proof authority"
        ),
    }


def _profile_freshness(profiled_sha: str | None, current_sha: str | None) -> str:
    if not profiled_sha:
        return "unknown"
    return "current" if current_sha == profiled_sha else "stale"


def _attach_execution_profiles(declaration_rows: list[dict[str, Any]], *, repo_root: Path) -> None:
    chosen = _select_profiled_runs_by_file(repo_root=repo_root)
    if not chosen:
        return
    by_file: dict[str, list[dict[str, Any]]] = {}
    for row in declaration_rows:
        by_file.setdefault(str(row.get("file") or ""), []).append(row)
    for rel_file, run_info in chosen.items():
        file_rows = by_file.get(rel_file)
        if not file_rows:
            continue
        path = _repo_path(rel_file, repo_root=repo_root)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        total_lines = len(text.splitlines())
        current_sha = _file_sha(path)
        run = run_info["payload"]
        profiled_sha = run.get("source_sha256")
        freshness = _profile_freshness(profiled_sha, current_sha)
        file_total_ms = float(run.get("duration_ms") or 0.0)
        profiled_ref = _rel(run_info["path"], repo_root=repo_root)
        spans = _declaration_spans(file_rows, total_lines)
        per_node, _overhead = _map_profile_events_to_declarations(_profile_events(run), spans)
        for acc in per_node.values():
            acc["row"]["execution_profile"] = _execution_profile_payload(
                acc,
                file_total_ms=file_total_ms,
                profiled_ref=profiled_ref,
                profiled_sha=profiled_sha,
                current_sha=current_sha,
                freshness=freshness,
            )


def _build_proof_trace_flight_recorder(
    *,
    repo_root: Path,
    visual_surfaces: Mapping[str, Any],
    route_steps: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    catalog = visual_surfaces.get("declaration_catalog") if isinstance(visual_surfaces.get("declaration_catalog"), Mapping) else {}
    declarations = [row for row in (catalog.get("declarations") or []) if isinstance(row, Mapping)]
    declaration_by_node_id = _declarations_by_node_id(visual_surfaces)
    by_file: dict[str, list[Mapping[str, Any]]] = {}
    for row in declarations:
        by_file.setdefault(str(row.get("file") or ""), []).append(row)
    chosen = _select_profiled_runs_by_file(repo_root=repo_root)
    profiled_files: list[dict[str, Any]] = []
    for rel_file in sorted(chosen):
        run_info = chosen[rel_file]
        run = run_info["payload"]
        rows = by_file.get(rel_file, [])
        path = _repo_path(rel_file, repo_root=repo_root)
        current_sha = _file_sha(path) if path.exists() else None
        profiled_sha = run.get("source_sha256")
        events = _profile_events(run)
        phase_totals: dict[str, float] = {}
        for event in events:
            phase = str(event.get("phase") or "")
            phase_totals[phase] = phase_totals.get(phase, 0.0) + float(event.get("duration_ms") or 0.0)
        phase_breakdown = sorted(
            ({"phase": phase, "duration_ms": round(ms, 3)} for phase, ms in phase_totals.items()),
            key=lambda row: (-row["duration_ms"], row["phase"]),
        )
        attributed = [
            {
                "node_id": str(row.get("node_id") or ""),
                "name": row.get("name"),
                "total_duration_ms": (row.get("execution_profile") or {}).get("total_duration_ms"),
                "dominant_phase": (row.get("execution_profile") or {}).get("dominant_phase"),
                "event_count": (row.get("execution_profile") or {}).get("event_count"),
                "proof_layer_id": (row.get("proof_layer") or {}).get("layer_id"),
            }
            for row in rows
            if isinstance(row.get("execution_profile"), Mapping) and row["execution_profile"].get("available")
        ]
        attributed.sort(key=lambda row: (-(row["total_duration_ms"] or 0.0), str(row.get("name"))))
        profiled_files.append(
            {
                "file": rel_file,
                "module_id": rows[0].get("module_id") if rows else None,
                "status": run.get("status"),
                "diagnostic_ref": _rel(run_info["path"], repo_root=repo_root),
                "total_duration_ms": run.get("duration_ms"),
                "profiled_event_count": len(events),
                "declaration_count": len(rows),
                "attributed_declaration_count": len(attributed),
                "profiled_source_sha256": profiled_sha,
                "current_source_sha256": current_sha,
                "profile_freshness": _profile_freshness(profiled_sha, current_sha),
                "phase_breakdown": phase_breakdown,
                "top_cost_declarations": attributed[:8],
                "started_at": run.get("started_at"),
                "ended_at": run.get("ended_at"),
            }
        )
    unprofiled_files = sorted(rel_file for rel_file in by_file if rel_file not in chosen)
    route_step_profiles: list[dict[str, Any]] = []
    for step in route_steps:
        node_id = str(step.get("node_id") or "")
        declaration = declaration_by_node_id.get(node_id, {})
        execution_profile = declaration.get("execution_profile") if isinstance(declaration, Mapping) else None
        has_profile = isinstance(execution_profile, Mapping) and bool(execution_profile.get("available"))
        route_step_profiles.append(
            {
                "node_id": node_id,
                "name": (declaration.get("name") if isinstance(declaration, Mapping) else None) or step.get("label"),
                "available": has_profile,
                "total_duration_ms": execution_profile.get("total_duration_ms") if has_profile else None,
                "dominant_phase": execution_profile.get("dominant_phase") if has_profile else None,
                "profile_freshness": execution_profile.get("profile_freshness") if has_profile else None,
            }
        )
    any_stale = any(entry["profile_freshness"] == "stale" for entry in profiled_files)
    return {
        "schema_version": "lean_proof_trace_flight_recorder_v0",
        "available": bool(profiled_files),
        "coverage": {
            "profiled_file_count": len(profiled_files),
            "unprofiled_file_count": len(unprofiled_files),
            "unprofiled_files": unprofiled_files,
            "note": (
                "Per-declaration cost is mapped from existing Lean `--profile` diagnostics by source line. "
                "Only files with a projection-relevant PASS profile run carry attributed cost; the rest are unprofiled."
            ),
        },
        "profiled_files": profiled_files,
        "route_step_profiles": route_step_profiles,
        "freshness_warning": (
            "At least one profile was recorded against a different source revision than the current file "
            "(profile_freshness=stale); rerun the Lean diagnostics to refresh."
            if any_stale
            else None
        ),
        "source_boundary_filter": dict(DIAGNOSTIC_SOURCE_BOUNDARY_FILTER),
        "claim_boundary": (
            "Lean `--profile` timing is diagnostic/performance evidence with explicit coverage and freshness; "
            "it is not proof authority. Target-runner and replay receipts remain the proof surfaces."
        ),
        "authority_boundary": (
            "Flight-recorder cost describes where elaboration time was spent, not whether a theorem is true. "
            "Profiler coverage can be partial: only events above the Lean profiler threshold are recorded."
        ),
    }


def _build_proof_architecture(
    *,
    visual_surfaces: Mapping[str, Any],
    graph_views: Mapping[str, Any],
    static_risk_scan: Mapping[str, Any],
) -> dict[str, Any]:
    catalog = visual_surfaces.get("declaration_catalog") if isinstance(visual_surfaces.get("declaration_catalog"), Mapping) else {}
    declarations = [row for row in (catalog.get("declarations") or []) if isinstance(row, Mapping)]
    layer_acc: dict[str, dict[str, Any]] = {}
    centerpieces: list[dict[str, Any]] = []
    summits: list[dict[str, Any]] = []
    for row in declarations:
        layer = row.get("proof_layer") if isinstance(row.get("proof_layer"), Mapping) else {}
        layer_id = layer.get("layer_id")
        execution_profile = row.get("execution_profile") if isinstance(row.get("execution_profile"), Mapping) else {}
        has_cost = bool(execution_profile.get("available"))
        cost = float(execution_profile.get("total_duration_ms") or 0.0) if has_cost else 0.0
        if layer_id:
            acc = layer_acc.setdefault(
                layer_id,
                {"declaration_count": 0, "profiled_declaration_count": 0, "total_duration_ms": 0.0},
            )
            acc["declaration_count"] += 1
            if has_cost:
                acc["profiled_declaration_count"] += 1
                acc["total_duration_ms"] += cost
        significance = layer.get("significance")
        if significance:
            entry = {
                "name": row.get("name"),
                "significance": significance,
                "conceptual_layer_id": layer_id,
                "plain_math": layer.get("plain_math"),
                "source_ref": row.get("file"),
                "line_start": row.get("line_start"),
                "line_end": row.get("line_end"),
                "execution_duration_ms": execution_profile.get("total_duration_ms") if has_cost else None,
            }
            if significance in {"summit", "concrete_endpoint"}:
                summits.append(entry)
            centerpieces.append(entry)
    layer_meta: list[Mapping[str, Any]] = []
    for bands in PROOF_ARCHITECTURE_LAYER_BANDS_BY_BASENAME.values():
        layer_meta.extend(bands)
    layer_meta.extend(PROOF_ARCHITECTURE_FILE_ROLE_LAYERS)
    layers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for meta in sorted(layer_meta, key=lambda item: int(item.get("ordinal") or 0)):
        layer_id = str(meta.get("layer_id"))
        if layer_id in seen or layer_id not in layer_acc:
            continue
        seen.add(layer_id)
        acc = layer_acc[layer_id]
        layers.append(
            {
                "layer_id": layer_id,
                "ordinal": meta.get("ordinal"),
                "title": meta.get("title"),
                "summary": meta.get("summary"),
                "role": meta.get("role"),
                "declaration_count": acc["declaration_count"],
                "profiled_declaration_count": acc["profiled_declaration_count"],
                "total_duration_ms": round(acc["total_duration_ms"], 3) if acc["total_duration_ms"] else None,
            }
        )
    centerpieces.sort(key=lambda row: (str(row.get("source_ref")), int(row.get("line_start") or 0)))
    summits.sort(key=lambda row: (str(row.get("source_ref")), int(row.get("line_start") or 0)))
    topological_layers = graph_views.get("dependency_layers") if isinstance(graph_views.get("dependency_layers"), list) else []
    return {
        "schema_version": "lean_proof_architecture_v0",
        "available": bool(layers),
        "annotation_authority": PROOF_ARCHITECTURE_ANNOTATION_AUTHORITY,
        "structural_backbone": "graph_views.dependency_layers (machine-derived topological layering)",
        "topological_layer_count": len(topological_layers),
        "conceptual_layers": layers,
        "summits": summits,
        "centerpieces": centerpieces,
        "trust_summary": {
            "sorry_count": static_risk_scan.get("sorry_count"),
            "admit_count": static_risk_scan.get("admit_count"),
            "axiom_count": static_risk_scan.get("axiom_count"),
            "status": static_risk_scan.get("status"),
            "scan_claim_boundary": static_risk_scan.get("claim_boundary"),
            "annotation": (
                "Token-scan counts are exact for the owned Lean source. The abstract proof engine is written "
                "without sorry/admit/axiom; concrete fixtures use kernel-checked `decide` (not native_decide)."
            ),
            "annotation_authority": PROOF_ARCHITECTURE_ANNOTATION_AUTHORITY,
        },
        "claim_boundary": (
            "The proof architecture is an inspection map over generated projection data with human-authored "
            "layer/gloss annotations. It is not proof authority, statement reconciliation, or a solved-conjecture claim."
        ),
    }


def _build_theorem_observatory(
    *,
    repo_root: Path,
    lean_projects: Sequence[Mapping[str, Any]],
    formal_math_threads: Sequence[Mapping[str, Any]],
    graph_views: Mapping[str, Any],
    visual_surfaces: Mapping[str, Any],
    currentness: Mapping[str, Any],
    anti_claims: Sequence[str],
) -> dict[str, Any]:
    proof_spine = graph_views.get("proof_spine_bundle") if isinstance(graph_views.get("proof_spine_bundle"), Mapping) else {}
    route_steps = [row for row in proof_spine.get("route_steps") or [] if isinstance(row, Mapping)]
    declaration_by_node_id = _declarations_by_node_id(visual_surfaces)
    primary_step = route_steps[0] if route_steps else {}
    primary_node_id = str(primary_step.get("node_id") or "")
    canonical_declaration = declaration_by_node_id.get(primary_node_id, {})
    target_runner_receipts = _target_runner_refs(formal_math_threads, repo_root=repo_root)
    target_runner = next(
        (row for row in target_runner_receipts if str(row.get("status") or "").upper() == "PASS"),
        target_runner_receipts[0] if target_runner_receipts else {},
    )
    static_risk_scan = _lean_static_risk_summary(lean_projects)
    latest_diagnostic = _latest_lean_diagnostic(repo_root=repo_root)
    certificate_objects = _certificate_object_rows(graph_views, declaration_by_node_id)
    certificate_microscope = _build_certificate_microscope(
        repo_root=repo_root,
        visual_surfaces=visual_surfaces,
        target_runner=target_runner,
    )
    route_declarations = []
    for step in route_steps:
        node_id = str(step.get("node_id") or "")
        declaration = declaration_by_node_id.get(node_id, {})
        route_declarations.append(
            {
                **dict(step),
                "declaration": {
                    "name": declaration.get("name") or step.get("label"),
                    "kind": declaration.get("kind"),
                    "formal_statement_excerpt": declaration.get("signature_excerpt"),
                    **_source_span_for_declaration(declaration),
                },
            }
        )
    target_theorem = target_runner.get("target_theorem")
    canonical_label = canonical_declaration.get("name") or primary_step.get("label")
    authority_chain = [
        {
            "authority_id": "lean_declaration_source",
            "label": "Lean declaration source",
            "status": "present" if canonical_declaration else "missing",
            "source_ref": canonical_declaration.get("file"),
            "line_start": canonical_declaration.get("line_start"),
            "line_end": canonical_declaration.get("line_end"),
            "claim_boundary": "source anchor for the theorem route; not an execution receipt",
        },
        {
            "authority_id": "target_runner_receipt",
            "label": "Target runner receipt",
            "status": target_runner.get("status") or "missing",
            "receipt_ref": target_runner.get("ref"),
            "target_theorem": target_theorem,
            "target_check_status": target_runner.get("target_check_status"),
            "print_axioms_status": target_runner.get("print_axioms_status"),
            "axiom_dependency_class": target_runner.get("axiom_dependency_class"),
            "claim_boundary": target_runner.get("claim_boundary")
            or "target-runner receipt missing; projection cannot upgrade proof authority",
        },
        {
            "authority_id": "static_risk_scan",
            "label": "sorry/admit/axiom audit",
            "status": static_risk_scan["status"],
            "sorry_count": static_risk_scan["sorry_count"],
            "admit_count": static_risk_scan["admit_count"],
            "axiom_count": static_risk_scan["axiom_count"],
            "claim_boundary": static_risk_scan["claim_boundary"],
        },
        {
            "authority_id": "projection_currentness",
            "label": "Generated projection currentness",
            "status": currentness.get("last_check_status") or currentness.get("status"),
            "source_fingerprint": currentness.get("source_fingerprint"),
            "safe_to_treat_as_proof_authority": currentness.get("safe_to_treat_as_proof_authority"),
            "claim_boundary": "content-addressed projection freshness only; no proof authority delta",
        },
    ]
    performance_boundary = {
        "latest_diagnostic": latest_diagnostic,
        "source_boundary_filter": dict(DIAGNOSTIC_SOURCE_BOUNDARY_FILTER),
        "profile_claim_boundary": (
            "profile and environment diagnostics describe replay/performance context; they are not proof authority"
        ),
    }
    flight_recorder = _build_proof_trace_flight_recorder(
        repo_root=repo_root,
        visual_surfaces=visual_surfaces,
        route_steps=route_steps,
    )
    proof_architecture = _build_proof_architecture(
        visual_surfaces=visual_surfaces,
        graph_views=graph_views,
        static_risk_scan=static_risk_scan,
    )
    return {
        "schema_version": "lean_theorem_observatory_v0",
        "observatory_id": "proof_observatory_v0_canonical_route",
        "available": bool(route_steps),
        "route": {
            "route_id": proof_spine.get("primary_route_id"),
            "final_label": proof_spine.get("final_label"),
            "route_step_count": len(route_steps),
            "branch_bundle_count": len(proof_spine.get("branch_bundles") or []),
            "terminal_claim_chips": list(proof_spine.get("terminal_claim_chips") or []),
            "external_dependency_chips": list(proof_spine.get("external_dependency_chips") or []),
            "condensed_dag_node_count": len((graph_views.get("condensed_dag") or {}).get("nodes") or []),
            "condensed_dag_edge_count": len((graph_views.get("condensed_dag") or {}).get("edges") or []),
            "condensed_dag_status": "available"
            if (graph_views.get("condensed_dag") or {}).get("nodes")
            else "not_computed_or_unavailable",
        },
        "canonical_theorem": {
            "label": canonical_label,
            "lean_declaration": canonical_declaration.get("name"),
            "declaration_kind": canonical_declaration.get("kind"),
            "formal_statement_excerpt": canonical_declaration.get("signature_excerpt"),
            **_source_span_for_declaration(canonical_declaration),
        },
        "route_steps": route_declarations,
        "certificate_objects": certificate_objects,
        "certificate_microscope": certificate_microscope,
        "authority_chain": authority_chain,
        "receipt_chain": _receipt_chain_from_threads(formal_math_threads),
        "performance_boundary": performance_boundary,
        "proof_trace_flight_recorder": flight_recorder,
        "proof_architecture": proof_architecture,
        "target_runner_receipts": target_runner_receipts,
        "anti_claims": list(anti_claims),
        "reviewer_questions": [
            {
                "question": "What exactly is claimed?",
                "answer_ref": "canonical_theorem.formal_statement_excerpt",
                "answer": canonical_declaration.get("signature_excerpt")
                or "No canonical theorem declaration was resolved from the proof spine.",
            },
            {
                "question": "Which Lean declarations support it?",
                "answer_ref": "route_steps",
                "answer": "Follow route_steps from the theorem endpoint through its dependency spine.",
            },
            {
                "question": "What certificate objects are involved?",
                "answer_ref": "certificate_objects",
                "answer": (
                    "Certificate objects are semantic-family projections over route declarations; "
                    "they expose mathematical object roles without promoting the projection to proof authority."
                ),
            },
            {
                "question": "Which generated certificate rows are inside the checked endpoint?",
                "answer_ref": "certificate_microscope.row_cases",
                "answer": (
                    f"{len(certificate_microscope.get('row_cases') or [])} emitted certificate rows resolved from "
                    f"{(certificate_microscope.get('certificate_def') or {}).get('name') or 'no generated table'}."
                ),
            },
            {
                "question": "What was replayed or checked?",
                "answer_ref": "authority_chain.target_runner_receipt",
                "answer": target_runner.get("claim_boundary")
                or "No target-runner receipt was resolved for this route.",
            },
            {
                "question": "What is not being claimed?",
                "answer_ref": "anti_claims",
                "answer": "The projection is not a conjecture solution, public release authorization, or proof authority transport.",
            },
        ],
        "authority_boundary": (
            "The observatory is an inspectability route over generated projection data. Lean/Lake execution, "
            "target-runner receipts, and axiom audits remain the mathematical authority surfaces."
        ),
    }


def _theorem_observatory_surface(observatory: Mapping[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    if not observatory.get("available"):
        issues.append("missing_canonical_route")
    if not observatory.get("certificate_objects"):
        issues.append("missing_certificate_object_semantics")
    return _surface_payload(
        "theorem_observatory",
        available=bool(observatory.get("available")) and not issues,
        issues=issues,
        observatory_id=observatory.get("observatory_id"),
        route=observatory.get("route") or {},
        canonical_theorem=observatory.get("canonical_theorem") or {},
        route_steps=list(observatory.get("route_steps") or []),
        certificate_objects=list(observatory.get("certificate_objects") or []),
        certificate_microscope=observatory.get("certificate_microscope") or {},
        authority_chain=list(observatory.get("authority_chain") or []),
        receipt_chain=list(observatory.get("receipt_chain") or []),
        performance_boundary=observatory.get("performance_boundary") or {},
        proof_trace_flight_recorder=observatory.get("proof_trace_flight_recorder") or {},
        proof_architecture=observatory.get("proof_architecture") or {},
        target_runner_receipts=list(observatory.get("target_runner_receipts") or []),
        anti_claims=list(observatory.get("anti_claims") or []),
        reviewer_questions=list(observatory.get("reviewer_questions") or []),
        authority_boundary=observatory.get("authority_boundary"),
    )


def _install_theorem_observatory_surface(payload: dict[str, Any]) -> None:
    observatory = payload.get("theorem_observatory")
    visual = payload.get("visual_surfaces")
    if not isinstance(observatory, Mapping) or not isinstance(visual, dict):
        return
    keys = [str(key) for key in visual.get("surface_keys") or []]
    if "theorem_observatory" not in keys:
        insert_at = keys.index("declaration_catalog") if "declaration_catalog" in keys else len(keys)
        keys.insert(insert_at, "theorem_observatory")
    visual["surface_keys"] = keys
    visual["theorem_observatory"] = _theorem_observatory_surface(observatory)


def _receipt_timeline(formal_math_threads: Sequence[Mapping[str, Any]], *, repo_root: Path) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    for thread in formal_math_threads:
        thread_id = str(thread.get("thread_id") or "unknown")
        receipts = thread.get("receipt_artifacts")
        if not isinstance(receipts, list):
            continue
        for index, receipt_ref in enumerate(receipts, start=1):
            if not isinstance(receipt_ref, Mapping):
                continue
            path = str(receipt_ref.get("path") or "")
            payload = _read_json_if_exists(path, repo_root=repo_root) if path else {}
            status = str(payload.get("status") or receipt_ref.get("status") or "present")
            steps.append(
                {
                    "step_id": f"{thread_id}:{Path(path).stem or index}",
                    "thread_id": thread_id,
                    "status": status,
                    "artifact_ref": path,
                    "check_id": Path(path).stem,
                    "claim_boundary": payload.get("claim_boundary"),
                    "started_at": payload.get("started_at") or payload.get("generated_at"),
                    "finished_at": payload.get("finished_at") or payload.get("generated_at"),
                    "elapsed_ms": payload.get("elapsed_ms"),
                    "ordinal": index,
                }
            )
    return _surface_payload(
        "receipt_timeline",
        available=bool(steps),
        issues=[] if steps else ["no_receipt_steps_discovered"],
        steps=steps,
        step_count=len(steps),
    )


def _obligation_graph(formal_math_threads: Sequence[Mapping[str, Any]], *, repo_root: Path) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    issues: list[str] = []
    for thread in formal_math_threads:
        thread_id = str(thread.get("thread_id") or "unknown")
        thread_root = str(thread.get("thread_root") or "")
        dag_path = f"{thread_root}/obligation_dag.json" if thread_root else ""
        payload = _read_json_if_exists(dag_path, repo_root=repo_root) if dag_path else {}
        if not payload:
            issues.append(f"missing:{dag_path}")
            continue
        for node in payload.get("nodes") or []:
            if isinstance(node, Mapping):
                nodes.append(
                    {
                        "node_id": str(node.get("node_id") or ""),
                        "thread_id": thread_id,
                        "label": node.get("claim_text_or_summary") or node.get("node_id"),
                        "status": node.get("status"),
                        "claim_type": node.get("claim_type"),
                        "evidence_kind": node.get("evidence_kind"),
                        "source_ref": node.get("source_ref"),
                        "claim_boundary": payload.get("claim_boundary"),
                    }
                )
        for edge in payload.get("edges") or []:
            if isinstance(edge, Mapping):
                edges.append(
                    {
                        "edge_id": f"{thread_id}:{edge.get('from')}->{edge.get('to')}",
                        "thread_id": thread_id,
                        "from_node_id": edge.get("from"),
                        "to_node_id": edge.get("to"),
                        "edge_kind": edge.get("edge_kind") or "depends_on",
                    }
                )
    return _surface_payload(
        "obligation_graph",
        available=bool(nodes),
        issues=issues,
        nodes=nodes,
        edges=edges,
        node_count=len(nodes),
        edge_count=len(edges),
    )


def _capability_cards(*, repo_root: Path) -> dict[str, Any]:
    capability_map = _read_json_if_exists("state/formal_math_research_operations/capability_map.json", repo_root=repo_root)
    rows = capability_map.get("capability_rows") if isinstance(capability_map, Mapping) else []
    cards = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            cards.append(
                {
                    "capability_id": row.get("capability_id"),
                    "family": row.get("family"),
                    "role": row.get("role"),
                    "maturity": row.get("maturity"),
                    "owner_surface": row.get("owner_surface"),
                    "risk_boundary": row.get("risk_boundary"),
                    "next_action": row.get("next_action"),
                    "source_refs": row.get("source_refs") or [],
                    "validation_commands": row.get("validation_commands") or [],
                }
            )
    return _surface_payload(
        "capability_cards",
        available=bool(cards),
        issues=[] if cards else ["missing_or_empty:state/formal_math_research_operations/capability_map.json"],
        cards=cards,
        card_count=len(cards),
    )


def _validation_cards(validation_surfaces: Mapping[str, Any], receipt: Mapping[str, Any] | None = None) -> dict[str, Any]:
    receipt = receipt or {}
    commands = validation_surfaces.get("recommended_checks")
    cards = []
    if isinstance(commands, list):
        for command in commands:
            command_text = str(command)
            if "build_lean_mathematics_microcosm_projection.py" in command_text:
                status = str(receipt.get("status") or "unknown")
                source_fingerprint = receipt.get("source_fingerprint")
            else:
                status = "unknown"
                source_fingerprint = None
            cards.append(
                {
                    "check_id": re.sub(r"[^a-z0-9]+", "_", command_text.lower()).strip("_")[:80],
                    "command": command_text,
                    "authority": "owner_check_command",
                    "latest_known_status": status,
                    "source_fingerprint": source_fingerprint,
                }
            )
    return _surface_payload("validation_cards", available=bool(cards), cards=cards, card_count=len(cards))


def _boundary_cards() -> dict[str, Any]:
    boundary_kinds = [
        "proof_authority",
        "public_claim",
        "proof_replacement",
        "release_authority",
        "disclosure_authority",
        "registry_authority",
    ]
    cards = [
        {
            "boundary_id": f"anti_claim_{index}",
            "claim_text": claim,
            "boundary_kind": boundary_kinds[index - 1] if index - 1 < len(boundary_kinds) else "claim_boundary",
            "proof_authority": "Lean/Lake plus statement reconciliation and literature review",
            "originating_doc": DOC_REL,
            "originating_anchor": "anti-claims",
        }
        for index, claim in enumerate(ANTI_CLAIMS, start=1)
    ]
    return _surface_payload("boundary_cards", available=True, cards=cards, card_count=len(cards))


def _disclosure_posture_cards() -> dict[str, Any]:
    cards = [dict(posture) for posture in DISCLOSURE_POSTURES]
    return _surface_payload(
        "disclosure_posture_cards",
        available=True,
        cards=cards,
        card_count=len(cards),
        invariant="Disclosure scope controls what can be shown; proof authority controls what can be claimed.",
    )


def _full_fidelity_packet_card(packet: Mapping[str, Any], packet_receipt: Mapping[str, Any]) -> dict[str, Any]:
    source_layer = packet.get("source_disclosure_layer") if isinstance(packet.get("source_disclosure_layer"), Mapping) else {}
    receipt_layer = packet.get("receipt_reproduction_layer") if isinstance(packet.get("receipt_reproduction_layer"), Mapping) else {}
    claim_layer = packet.get("claim_boundary_layer") if isinstance(packet.get("claim_boundary_layer"), Mapping) else {}
    secret_scan = packet.get("secret_exclusion_scan") if isinstance(packet.get("secret_exclusion_scan"), Mapping) else {}
    latest_diagnostic = receipt_layer.get("latest_diagnostic") if isinstance(receipt_layer.get("latest_diagnostic"), Mapping) else {}
    return _surface_payload(
        "full_fidelity_packet_card",
        available=packet_receipt.get("status") == "PASS",
        issues=[] if packet_receipt.get("status") == "PASS" else ["full_fidelity_packet_receipt_not_pass"],
        packet_id=packet.get("packet_id"),
        disclosure_posture_id=packet.get("disclosure_posture_id"),
        packet_ref=FULL_FIDELITY_PACKET_REL,
        receipt_ref=FULL_FIDELITY_PACKET_RECEIPT_REL,
        markdown_ref=FULL_FIDELITY_PACKET_DOC_REL,
        status=packet_receipt.get("status"),
        packet_sha256=packet_receipt.get("packet_sha256"),
        source_file_count=source_layer.get("source_file_count", 0),
        receipt_ref_count=packet_receipt.get("receipt_ref_count", 0),
        claim_boundary_count=claim_layer.get("claim_boundary_count", 0),
        secret_exclusion_status=secret_scan.get("status"),
        secret_exclusion_blocking_hit_count=secret_scan.get("blocking_hit_count"),
        latest_diagnostic_status=latest_diagnostic.get("status"),
        latest_diagnostic_environment_status=latest_diagnostic.get("environment_status"),
        body_text_policy=source_layer.get("body_storage_policy"),
        authority_invariant=claim_layer.get("authority_invariant"),
    )


def _provenance_card(lean_projects: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    projects = []
    for project in lean_projects:
        projects.append(
            {
                "project_id": project.get("project_id"),
                "root": project.get("root"),
                "lean_toolchain": project.get("lean_toolchain"),
                "lake_manifest": project.get("lake_manifest"),
                "dependency_count": project.get("dependency_count"),
                "build_provenance": project.get("build_provenance") or {},
                "static_risk_scan": project.get("static_risk_scan") or {},
            }
        )
    return _surface_payload("provenance_card", available=bool(projects), projects=projects, project_count=len(projects))


def _doc_section_index(*, repo_root: Path) -> dict[str, Any]:
    # The markdown body includes the receipt projection hash, which is derived
    # from this JSON projection. The API loader computes the live section index
    # after reading the already-written markdown to avoid circular projection
    # hashes inside the generated owner artifact.
    return _surface_payload(
        "doc_section_index",
        available=False,
        issues=["computed_by_api_loader"],
        sections=[],
        section_count=0,
        markdown_ref=DOC_REL,
    )


def _build_visual_surfaces(
    *,
    repo_root: Path,
    lean_projects: Sequence[Mapping[str, Any]],
    proof_threads: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    currentness: Mapping[str, Any],
    validation_surfaces: Mapping[str, Any],
    receipt: Mapping[str, Any] | None = None,
    full_fidelity_packet: Mapping[str, Any] | None = None,
    full_fidelity_packet_receipt: Mapping[str, Any] | None = None,
    full_fidelity_packet_verification_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_fingerprint = str(currentness.get("source_fingerprint") or "")
    generated_at = str(currentness.get("generated_at") or "")
    consistency_token = hashlib.sha256(f"{source_fingerprint}:{generated_at}".encode("utf-8")).hexdigest()[:16]
    return {
        "schema_version": "lean_mathematics_visual_surfaces_v1",
        "surface_keys": [
            "overview",
            "declaration_catalog",
            "declaration_graph",
            "obligation_graph",
            "receipt_timeline",
            "capability_cards",
            "validation_cards",
            "full_fidelity_packet_card",
            "full_fidelity_packet_verifier_card",
            "disclosure_posture_cards",
            "boundary_cards",
            "provenance_card",
            "doc_section_index",
        ],
        "consistency_token": consistency_token,
        "carve_out_thresholds": {
            "payload_bytes": 100000,
            "declarations": 2000,
            "edges": 5000,
            "timeline_steps": 1000,
        },
        "overview": _surface_payload(
            "overview",
            available=True,
            summary=dict(summary),
            currentness=dict(currentness),
        ),
        "declaration_catalog": _declaration_catalog(lean_projects),
        "declaration_graph": _declaration_graph(lean_projects, repo_root=repo_root),
        "obligation_graph": _obligation_graph(proof_threads, repo_root=repo_root),
        "receipt_timeline": _receipt_timeline(proof_threads, repo_root=repo_root),
        "capability_cards": _capability_cards(repo_root=repo_root),
        "validation_cards": _validation_cards(validation_surfaces, receipt),
        "full_fidelity_packet_card": _full_fidelity_packet_card(full_fidelity_packet, full_fidelity_packet_receipt)
        if full_fidelity_packet is not None and full_fidelity_packet_receipt is not None
        else _surface_payload(
            "full_fidelity_packet_card",
            available=False,
            issues=["computed_after_packet_build"],
            packet_ref=FULL_FIDELITY_PACKET_REL,
            receipt_ref=FULL_FIDELITY_PACKET_RECEIPT_REL,
            markdown_ref=FULL_FIDELITY_PACKET_DOC_REL,
        ),
        "full_fidelity_packet_verifier_card": _full_fidelity_packet_verifier_card(
            full_fidelity_packet_verification_receipt
        )
        if full_fidelity_packet_verification_receipt is not None
        else _surface_payload(
            "full_fidelity_packet_verifier_card",
            available=False,
            issues=["computed_after_packet_verification"],
            verification_receipt_ref=FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL,
            verification_markdown_ref=FULL_FIDELITY_PACKET_VERIFICATION_DOC_REL,
            packet_ref=FULL_FIDELITY_PACKET_REL,
            packet_receipt_ref=FULL_FIDELITY_PACKET_RECEIPT_REL,
        ),
        "disclosure_posture_cards": _disclosure_posture_cards(),
        "boundary_cards": _boundary_cards(),
        "provenance_card": _provenance_card(lean_projects),
        "doc_section_index": _doc_section_index(repo_root=repo_root),
    }


def build_lean_mathematics_microcosm(
    *,
    repo_root: Path = REPO_ROOT,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or _utc_now()
    lean_projects = _discover_lean_projects(repo_root=repo_root)
    proof_threads = _discover_formal_threads(lean_projects, repo_root=repo_root)
    tests = _formal_tests(repo_root=repo_root)
    source_manifest = _source_manifest(repo_root=repo_root)
    source_fingerprint = _source_fingerprint(source_manifest)
    thread_status_counts = Counter(row["status"] for row in proof_threads)
    summary = {
        "lean_project_count": len(lean_projects),
        "lean_file_count": sum(int(project["lean_file_count"]) for project in lean_projects),
        "proof_thread_count": len(proof_threads),
        "formal_math_test_count": len(tests),
        "thread_status_counts": dict(sorted(thread_status_counts.items())),
        "anti_claim_count": len(ANTI_CLAIMS),
        "disclosure_posture_count": len(DISCLOSURE_POSTURES),
    }
    currentness = {
        "status": "content_addressed_current_when_check_passes",
        "source_coupling_status": "derived_from_source_fingerprint",
        "source_fingerprint": source_fingerprint,
        "source_fingerprint_short": source_fingerprint.removeprefix("sha256:")[:8],
        "generated_at": generated_at,
        "last_check_at": generated_at,
        "last_check_status": "generated",
        "last_check_actor": BUILDER_REL,
        "safe_to_treat_as_proof_authority": False,
        "freshness_command": f"./repo-python {BUILDER_REL} --check --compact",
        "rebuild_command": f"./repo-python {BUILDER_REL} --write --compact",
    }
    validation_surfaces = {
        "formal_math_tests": tests,
        "recommended_checks": [
            "./repo-python tools/meta/factory/build_formal_math_research_operations_map.py --check",
            "./repo-python tools/meta/factory/build_formal_math_erdos257_issue217_pilot_dossier.py --check",
            "./repo-python tools/meta/factory/build_formal_math_erdos257_issue217_obligation_dag.py --check",
            "./repo-python tools/meta/factory/run_formal_math_erdos257_period_noncollapse_strike.py --check",
            f"./repo-python {BUILDER_REL} --check --compact",
        ],
    }
    declaration_graph = _declaration_graph(lean_projects, repo_root=repo_root)
    graph_views = _declaration_graph_views(declaration_graph, currentness=currentness)
    visual_surfaces = _build_visual_surfaces(
        repo_root=repo_root,
        lean_projects=lean_projects,
        proof_threads=proof_threads,
        summary=summary,
        currentness=currentness,
        validation_surfaces=validation_surfaces,
    )
    theorem_observatory = _build_theorem_observatory(
        repo_root=repo_root,
        lean_projects=lean_projects,
        formal_math_threads=proof_threads,
        graph_views=graph_views,
        visual_surfaces=visual_surfaces,
        currentness=currentness,
        anti_claims=ANTI_CLAIMS,
    )
    public_lean_projects = [
        {key: value for key, value in project.items() if key != "declarations"}
        for project in lean_projects
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "kind": "lean_mathematics_microcosm_projection",
        "microcosm_id": MICROCOSM_ID,
        "generated_at": generated_at,
        "authority_posture": "generated_dynamic_projection_not_proof_authority",
        "owner": {
            "owner_id": OWNER_ID,
            "builder": BUILDER_REL,
            "check_command": f"./repo-python {BUILDER_REL} --check --compact",
            "rebuild_command": f"./repo-python {BUILDER_REL} --write --compact",
        },
        "purpose": (
            "Project the moving Lean/formal-math lane as a microcosm that shows current projects, "
            "proof threads, receipts, validation surfaces, and claim boundaries without freezing the lane."
        ),
        "evolution_model": {
            "mode": "discover_from_current_sources",
            "source_roots": list(SOURCE_ROOTS),
            "source_fingerprint": source_fingerprint,
            "source_boundary_filters": {
                "state/lean_diagnostics": dict(DIAGNOSTIC_SOURCE_BOUNDARY_FILTER),
            },
            "rule": "Add Lean projects, formal-math state, docs, or tests under the source roots; rerun the builder to update the microcosm.",
            "staleness_signal": "builder --check compares this content-addressed projection with live source roots",
        },
        "currentness": currentness,
        "summary": summary,
        "lean_projects": public_lean_projects,
        "formal_math_threads": proof_threads,
        "capability_snapshot": _capability_snapshot(repo_root=repo_root),
        "graph_views": graph_views,
        "theorem_observatory": theorem_observatory,
        "validation_surfaces": validation_surfaces,
        "route_cards": [
            {
                "route_card_id": "lean_math.what_exists_now",
                "question": "What Lean/formal-math work exists right now?",
                "answer_surface": OUTPUT_REL,
                "drilldown": "lean_projects + formal_math_threads",
            },
            {
                "route_card_id": "lean_math.what_changed",
                "question": "Did the Lean/math microcosm drift after source changes?",
                "answer_surface": "currentness.source_fingerprint",
                "drilldown": f"./repo-python {BUILDER_REL} --check --compact",
            },
            {
                "route_card_id": "lean_math.what_is_proof_authority",
                "question": "What can be trusted as proof?",
                "answer_surface": "formal owner receipts and Lean/Lake checks, not this projection",
                "drilldown": "validation_surfaces.recommended_checks",
            },
            {
                "route_card_id": "lean_math.what_can_be_shown",
                "question": "Which disclosure posture governs this export or review?",
                "answer_surface": "disclosure_postures + visual_surfaces.disclosure_posture_cards",
                "drilldown": "public_safe_fixture / operator_authorized_full_fidelity / proof_authority",
            },
        ],
        "anti_claims": list(ANTI_CLAIMS),
        "disclosure_postures": [dict(posture) for posture in DISCLOSURE_POSTURES],
        "visual_surfaces": visual_surfaces,
        "source_manifest": source_manifest,
    }
    _install_theorem_observatory_surface(payload)
    return payload


def build_full_fidelity_evidence_packet(
    payload: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    lean_projects = [
        row for row in payload.get("lean_projects") or [] if isinstance(row, Mapping)
    ]
    formal_math_threads = [
        row for row in payload.get("formal_math_threads") or [] if isinstance(row, Mapping)
    ]
    validation_surfaces = payload.get("validation_surfaces") if isinstance(payload.get("validation_surfaces"), Mapping) else {}
    source_layer = _packet_source_disclosure_layer(lean_projects, repo_root=repo_root)
    receipt_layer = _packet_receipt_reproduction_layer(
        formal_math_threads,
        validation_surfaces,
        repo_root=repo_root,
    )
    claim_layer = _packet_claim_boundary_layer(formal_math_threads, lean_projects)
    scan_paths = [
        row["source_ref"]
        for project in source_layer.get("projects") or []
        if isinstance(project, Mapping)
        for row in project.get("source_files") or []
        if isinstance(row, Mapping) and row.get("source_ref")
    ]
    scan_paths.extend(
        str(row.get("ref"))
        for row in receipt_layer.get("evidence_cells") or []
        if isinstance(row, Mapping) and row.get("ref")
    )
    scan_paths.extend(
        str(row.get("ref"))
        for row in receipt_layer.get("target_runner_receipts") or []
        if isinstance(row, Mapping) and row.get("ref")
    )
    latest = receipt_layer.get("latest_diagnostic")
    if isinstance(latest, Mapping) and latest.get("diagnostic_ref"):
        scan_paths.append(str(latest["diagnostic_ref"]))
    generated_at = str(payload.get("generated_at") or _utc_now())
    packet: dict[str, Any] = {
        "schema_version": FULL_FIDELITY_PACKET_SCHEMA_VERSION,
        "kind": "lean_full_fidelity_evidence_packet",
        "packet_id": FULL_FIDELITY_PACKET_ID,
        "generated_at": generated_at,
        "operator_authorization": {
            "posture_id": "operator_authorized_full_fidelity",
            "authorized_scope": "Lean/Formal-Math review substrate only",
            "public_release_authorized": False,
            "credentials_or_unrelated_private_payloads_authorized": False,
        },
        "disclosure_posture_id": "operator_authorized_full_fidelity",
        "authority_posture": "inspection_authority_only_not_proof_authority",
        "authority_invariant": AUTHORITY_INVARIANT,
        "source_projection": {
            "projection_ref": OUTPUT_REL,
            "receipt_ref": RECEIPT_REL,
            "markdown_ref": DOC_REL,
            "source_fingerprint": (payload.get("currentness") or {}).get("source_fingerprint")
            if isinstance(payload.get("currentness"), Mapping)
            else None,
        },
        "source_disclosure_layer": source_layer,
        "receipt_reproduction_layer": receipt_layer,
        "claim_boundary_layer": claim_layer,
        "non_claims": list(ANTI_CLAIMS),
    }
    packet["secret_exclusion_scan"] = _secret_exclusion_scan(
        list(dict.fromkeys(scan_paths)),
        repo_root=repo_root,
        payload=packet,
    )
    return packet


def build_full_fidelity_evidence_packet_receipt(packet: Mapping[str, Any]) -> dict[str, Any]:
    source_layer = packet.get("source_disclosure_layer") if isinstance(packet.get("source_disclosure_layer"), Mapping) else {}
    receipt_layer = packet.get("receipt_reproduction_layer") if isinstance(packet.get("receipt_reproduction_layer"), Mapping) else {}
    claim_layer = packet.get("claim_boundary_layer") if isinstance(packet.get("claim_boundary_layer"), Mapping) else {}
    secret_scan = packet.get("secret_exclusion_scan") if isinstance(packet.get("secret_exclusion_scan"), Mapping) else {}
    evidence_cells = receipt_layer.get("evidence_cells") if isinstance(receipt_layer.get("evidence_cells"), list) else []
    target_runner_receipts = (
        receipt_layer.get("target_runner_receipts")
        if isinstance(receipt_layer.get("target_runner_receipts"), list)
        else []
    )
    thread_receipts = receipt_layer.get("thread_receipts") if isinstance(receipt_layer.get("thread_receipts"), list) else []
    blocking_hits = secret_scan.get("blocking_hit_count")
    secret_pass = blocking_hits == 0 or secret_scan.get("status") == "pass"
    return {
        "schema_version": FULL_FIDELITY_PACKET_RECEIPT_SCHEMA_VERSION,
        "status": "PASS" if secret_pass else "FAIL",
        "packet_ref": FULL_FIDELITY_PACKET_REL,
        "packet_receipt_ref": FULL_FIDELITY_PACKET_RECEIPT_REL,
        "packet_markdown_ref": FULL_FIDELITY_PACKET_DOC_REL,
        "packet_sha256": _sha256(packet),
        "source_file_count": source_layer.get("source_file_count", 0),
        "receipt_ref_count": len(evidence_cells) + len(target_runner_receipts) + len(thread_receipts),
        "evidence_cell_ref_count": len(evidence_cells),
        "target_runner_receipt_count": len(target_runner_receipts),
        "thread_receipt_count": len(thread_receipts),
        "claim_boundary_count": claim_layer.get("claim_boundary_count", 0),
        "secret_exclusion_status": secret_scan.get("status"),
        "secret_exclusion_blocking_hit_count": secret_scan.get("blocking_hit_count"),
        "latest_diagnostic_status": (
            (receipt_layer.get("latest_diagnostic") or {}).get("status")
            if isinstance(receipt_layer.get("latest_diagnostic"), Mapping)
            else None
        ),
        "latest_diagnostic_environment_status": (
            (receipt_layer.get("latest_diagnostic") or {}).get("environment_status")
            if isinstance(receipt_layer.get("latest_diagnostic"), Mapping)
            else None
        ),
        "authority_invariant": packet.get("authority_invariant"),
    }


def _verify_hashed_file_ref(row: Mapping[str, Any], *, ref_key: str, repo_root: Path) -> list[str]:
    ref = row.get(ref_key)
    expected_sha = row.get("sha256")
    if not isinstance(ref, str) or not ref:
        return [f"missing_ref:{ref_key}"]
    path = _repo_path(ref, repo_root=repo_root)
    if not path.is_file():
        return [f"missing_file:{ref}"]
    if not isinstance(expected_sha, str) or not expected_sha:
        return [f"missing_sha256:{ref}"]
    actual_sha = _file_sha(path)
    if actual_sha != expected_sha:
        return [f"sha256_mismatch:{ref}"]
    return []


def _lake_replay_status(latest_diagnostic: Mapping[str, Any]) -> str:
    if not latest_diagnostic or latest_diagnostic.get("available") is False:
        return "NOT_RUN"
    status = str(latest_diagnostic.get("status") or "").upper()
    environment_status = str(latest_diagnostic.get("environment_status") or "").lower()
    returncode = latest_diagnostic.get("returncode")
    if status == "PASS" or environment_status == "lake_project_ok":
        return "PASS"
    if status == "ENVIRONMENT_BLOCKED" or environment_status in {
        "dependency_cache_missing",
        "environment_blocked",
        "lake_cache_missing",
        "toolchain_missing",
    }:
        return "ENVIRONMENT_BLOCKED"
    if status in {"FAIL", "ERROR"} or (isinstance(returncode, int) and returncode != 0):
        return "FAIL"
    return "NOT_RUN"


def _reviewer_acceptance_status(
    *,
    packet_integrity: str,
    disclosure_boundary: str,
    secret_exclusion: str,
    source_ref_integrity: str,
    receipt_ref_integrity: str,
    claim_boundary_integrity: str,
    lake_replay_status: str,
) -> str:
    hard_statuses = {
        packet_integrity,
        secret_exclusion,
        source_ref_integrity,
        receipt_ref_integrity,
        claim_boundary_integrity,
    }
    if "FAIL" in hard_statuses:
        return "REJECTED"
    if disclosure_boundary == "FAIL":
        return "REJECTED"
    if lake_replay_status == "FAIL":
        return "REJECTED_OR_REQUIRES_REPAIR"
    if lake_replay_status == "ENVIRONMENT_BLOCKED":
        return "REVIEWABLE_WITH_ENVIRONMENT_BLOCK"
    if lake_replay_status == "PASS":
        return "REVIEWABLE_REPLAYED"
    return "REVIEWABLE_PACKET_ONLY"


def build_full_fidelity_evidence_packet_replay_receipt(
    packet: Mapping[str, Any],
    packet_receipt: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    previous_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_layer = packet.get("source_disclosure_layer") if isinstance(packet.get("source_disclosure_layer"), Mapping) else {}
    receipt_layer = packet.get("receipt_reproduction_layer") if isinstance(packet.get("receipt_reproduction_layer"), Mapping) else {}
    latest_diagnostic = receipt_layer.get("latest_diagnostic") if isinstance(receipt_layer.get("latest_diagnostic"), Mapping) else {}
    lake_workspace_status = _lake_workspace_status(source_layer, latest_diagnostic, repo_root=repo_root)
    replay_context_fingerprint = _replay_context_fingerprint(packet, latest_diagnostic, lake_workspace_status)
    preserved = _preserved_replay_attempts(
        previous_receipt or {},
        replay_context_fingerprint=replay_context_fingerprint,
    )
    hydration_attempt = preserved.get("hydration_attempt") if isinstance(preserved.get("hydration_attempt"), Mapping) else None
    target_attempt = preserved.get("target_attempt") if isinstance(preserved.get("target_attempt"), Mapping) else None
    dependency_hydration_status = _dependency_hydration_status(
        lake_workspace_status,
        latest_diagnostic,
        hydration_attempt,
    )
    dependency_hydration_mode = (
        str(hydration_attempt.get("mode"))
        if isinstance(hydration_attempt, Mapping) and hydration_attempt.get("mode")
        else "existing_workspace"
    )
    target_replay_status = _target_replay_status(
        latest_diagnostic,
        target_attempt,
        dependency_hydration_status=dependency_hydration_status,
    )
    reviewer_acceptance_status = _reviewer_acceptance_from_replay(target_replay_status)
    packet_verifier_status = (
        "PASS" if packet_receipt.get("status") == "PASS" else "PACKET_RECEIPT_NOT_PASS"
    )
    recommended_commands = (
        latest_diagnostic.get("recommended_dependency_commands")
        if isinstance(latest_diagnostic, Mapping)
        else []
    ) or []
    if not recommended_commands and lake_workspace_status.get("lake_root"):
        lake_root = str(lake_workspace_status["lake_root"])
        recommended_commands = [
            f"cd {lake_root} && lake exe cache get",
            f"cd {lake_root} && lake build",
        ]
    return {
        "schema_version": FULL_FIDELITY_PACKET_REPLAY_RECEIPT_SCHEMA_VERSION,
        "kind": "lean_full_fidelity_evidence_packet_replay_receipt",
        "status": "PASS" if reviewer_acceptance_status.startswith("REVIEWABLE") else "BLOCKED",
        "replay_id": FULL_FIDELITY_PACKET_REPLAY_ID,
        "replay_receipt_ref": FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
        "replay_markdown_ref": FULL_FIDELITY_PACKET_REPLAY_DOC_REL,
        "packet_ref": FULL_FIDELITY_PACKET_REL,
        "packet_receipt_ref": FULL_FIDELITY_PACKET_RECEIPT_REL,
        "packet_sha256": _sha256(packet),
        "packet_receipt_sha256": _sha256(packet_receipt),
        "packet_verifier_status": packet_verifier_status,
        "replay_context_fingerprint": replay_context_fingerprint,
        "dependency_hydration_status": dependency_hydration_status,
        "dependency_hydration_mode": dependency_hydration_mode,
        "lake_workspace_status": lake_workspace_status,
        "target_replay_status": target_replay_status,
        "target_runner_status": packet_receipt.get("target_runner_status"),
        "reviewer_acceptance_status": reviewer_acceptance_status,
        "proof_authority_delta": "none",
        "latest_diagnostic_ref": latest_diagnostic.get("diagnostic_ref") if isinstance(latest_diagnostic, Mapping) else None,
        "latest_diagnostic_status": latest_diagnostic.get("status") if isinstance(latest_diagnostic, Mapping) else None,
        "latest_diagnostic_environment_status": (
            latest_diagnostic.get("environment_status") if isinstance(latest_diagnostic, Mapping) else None
        ),
        "latest_diagnostic_dependency_cache_status": (
            latest_diagnostic.get("dependency_cache_status") if isinstance(latest_diagnostic, Mapping) else None
        ),
        "recommended_dependency_commands": recommended_commands,
        "hydration_attempt": hydration_attempt,
        "target_attempt": target_attempt,
        "attempted_at": preserved.get("attempted_at"),
        "authority_invariant": AUTHORITY_INVARIANT,
        "claim_boundary": (
            "Replay receipts classify dependency hydration and target replay. They do not upgrade proof authority; "
            "Lean/Lake target checks, evidence cells, and owner receipts carry claim authority."
        ),
    }


def _lake_status_from_replay(replay_receipt: Mapping[str, Any], latest_diagnostic: Mapping[str, Any]) -> str:
    target_status = str(replay_receipt.get("target_replay_status") or "")
    if target_status == "PASS":
        return "PASS"
    if target_status == "LEAN_FAIL":
        return "FAIL"
    if target_status in {"ENVIRONMENT_BLOCKED", "TIMEOUT"}:
        return "ENVIRONMENT_BLOCKED"
    return _lake_replay_status(latest_diagnostic)


def build_full_fidelity_evidence_packet_verification_receipt(
    packet: Mapping[str, Any],
    packet_receipt: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    replay_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_layer = packet.get("source_disclosure_layer") if isinstance(packet.get("source_disclosure_layer"), Mapping) else {}
    receipt_layer = packet.get("receipt_reproduction_layer") if isinstance(packet.get("receipt_reproduction_layer"), Mapping) else {}
    claim_layer = packet.get("claim_boundary_layer") if isinstance(packet.get("claim_boundary_layer"), Mapping) else {}
    secret_scan = packet.get("secret_exclusion_scan") if isinstance(packet.get("secret_exclusion_scan"), Mapping) else {}

    packet_integrity_issues: list[str] = []
    expected_packet_sha = _sha256(packet)
    if packet.get("schema_version") != FULL_FIDELITY_PACKET_SCHEMA_VERSION:
        packet_integrity_issues.append("packet_schema_version_mismatch")
    if packet.get("packet_id") != FULL_FIDELITY_PACKET_ID:
        packet_integrity_issues.append("packet_id_mismatch")
    if packet.get("disclosure_posture_id") != "operator_authorized_full_fidelity":
        packet_integrity_issues.append("disclosure_posture_mismatch")
    if packet.get("authority_invariant") != AUTHORITY_INVARIANT:
        packet_integrity_issues.append("authority_invariant_mismatch")
    if packet_receipt.get("packet_sha256") != expected_packet_sha:
        packet_integrity_issues.append("packet_sha256_mismatch")
    if packet_receipt.get("status") != "PASS":
        packet_integrity_issues.append("packet_receipt_not_pass")

    source_files = [
        row
        for project in source_layer.get("projects") or []
        if isinstance(project, Mapping)
        for row in project.get("source_files") or []
        if isinstance(row, Mapping)
    ]
    source_ref_issues: list[str] = []
    for row in source_files:
        source_ref_issues.extend(_verify_hashed_file_ref(row, ref_key="source_ref", repo_root=repo_root))
    if source_layer.get("source_file_count") != len(source_files):
        source_ref_issues.append("source_file_count_mismatch")
    if packet_receipt.get("source_file_count") != len(source_files):
        source_ref_issues.append("receipt_source_file_count_mismatch")
    source_fingerprint = _sha256(
        [{"source_ref": row.get("source_ref"), "sha256": row.get("sha256")} for row in source_files]
    )
    if source_layer.get("source_files_sha256") != source_fingerprint:
        source_ref_issues.append("source_files_sha256_mismatch")

    evidence_cells = receipt_layer.get("evidence_cells") if isinstance(receipt_layer.get("evidence_cells"), list) else []
    target_runner_receipts = (
        receipt_layer.get("target_runner_receipts")
        if isinstance(receipt_layer.get("target_runner_receipts"), list)
        else []
    )
    thread_receipts = receipt_layer.get("thread_receipts") if isinstance(receipt_layer.get("thread_receipts"), list) else []
    latest_diagnostic = receipt_layer.get("latest_diagnostic") if isinstance(receipt_layer.get("latest_diagnostic"), Mapping) else {}
    receipt_ref_rows: list[Mapping[str, Any]] = [
        row
        for row in [*evidence_cells, *target_runner_receipts, *thread_receipts]
        if isinstance(row, Mapping)
    ]
    if isinstance(latest_diagnostic, Mapping) and latest_diagnostic.get("diagnostic_ref"):
        receipt_ref_rows.append(
            {
                "ref": latest_diagnostic.get("diagnostic_ref"),
                "sha256": latest_diagnostic.get("sha256"),
            }
        )
    receipt_ref_issues: list[str] = []
    for row in receipt_ref_rows:
        receipt_ref_issues.extend(_verify_hashed_file_ref(row, ref_key="ref", repo_root=repo_root))
    receipt_ref_count = len(evidence_cells) + len(target_runner_receipts) + len(thread_receipts)
    if packet_receipt.get("receipt_ref_count") != receipt_ref_count:
        receipt_ref_issues.append("receipt_ref_count_mismatch")
    if packet_receipt.get("evidence_cell_ref_count") != len(evidence_cells):
        receipt_ref_issues.append("evidence_cell_ref_count_mismatch")
    if packet_receipt.get("target_runner_receipt_count") != len(target_runner_receipts):
        receipt_ref_issues.append("target_runner_receipt_count_mismatch")
    if packet_receipt.get("thread_receipt_count") != len(thread_receipts):
        receipt_ref_issues.append("thread_receipt_count_mismatch")

    authorization = packet.get("operator_authorization") if isinstance(packet.get("operator_authorization"), Mapping) else {}
    disclosure_issues: list[str] = []
    disclosure_warnings: list[str] = []
    if authorization.get("posture_id") != "operator_authorized_full_fidelity":
        disclosure_issues.append("operator_authorization_posture_mismatch")
    if authorization.get("public_release_authorized") is not False:
        disclosure_issues.append("public_release_boundary_not_false")
    if authorization.get("credentials_or_unrelated_private_payloads_authorized") is not False:
        disclosure_issues.append("credential_boundary_not_false")
    if source_layer.get("body_text_in_packet_json") is not False:
        disclosure_warnings.append("proof_body_text_embedded_in_packet_json")

    scan_paths = [
        str(row.get("source_ref"))
        for row in source_files
        if isinstance(row.get("source_ref"), str) and row.get("source_ref")
    ]
    scan_paths.extend(
        str(row.get("ref"))
        for row in [*evidence_cells, *target_runner_receipts, *thread_receipts]
        if isinstance(row, Mapping) and isinstance(row.get("ref"), str) and row.get("ref")
    )
    if isinstance(latest_diagnostic, Mapping) and latest_diagnostic.get("diagnostic_ref"):
        scan_paths.append(str(latest_diagnostic["diagnostic_ref"]))
    verifier_secret_scan = _secret_exclusion_scan(
        list(dict.fromkeys(scan_paths)),
        repo_root=repo_root,
        payload=packet,
    )
    secret_issues: list[str] = []
    if secret_scan.get("status") != "pass" or secret_scan.get("blocking_hit_count") != 0:
        secret_issues.append("packet_secret_exclusion_not_pass")
    if verifier_secret_scan.get("status") != "pass" or verifier_secret_scan.get("blocking_hit_count") != 0:
        secret_issues.append("verifier_secret_exclusion_not_pass")

    claim_issues: list[str] = []
    proof_body_caveat = str(claim_layer.get("proof_body_visibility_caveat") or "")
    if claim_layer.get("authority_invariant") != AUTHORITY_INVARIANT:
        claim_issues.append("claim_layer_authority_invariant_mismatch")
    if claim_layer.get("anti_claims") != list(ANTI_CLAIMS):
        claim_issues.append("anti_claims_mismatch")
    if not claim_layer.get("release_boundary"):
        claim_issues.append("release_boundary_missing")
    if "not proof authority" not in proof_body_caveat:
        claim_issues.append("proof_body_visibility_caveat_missing")
    if not claim_layer.get("statement_reconciliation_status"):
        claim_issues.append("statement_reconciliation_status_missing")
    if packet_receipt.get("claim_boundary_count") != claim_layer.get("claim_boundary_count"):
        claim_issues.append("claim_boundary_count_mismatch")
    if not evidence_cells:
        claim_issues.append("evidence_cell_refs_missing")
    if not target_runner_receipts:
        claim_issues.append("target_runner_refs_missing")

    packet_integrity = "PASS" if not packet_integrity_issues else "FAIL"
    source_ref_integrity = "PASS" if not source_ref_issues else "FAIL"
    receipt_ref_integrity = "PASS" if not receipt_ref_issues else "FAIL"
    disclosure_boundary = "FAIL" if disclosure_issues else ("WARN" if disclosure_warnings else "PASS")
    secret_exclusion = "PASS" if not secret_issues else "FAIL"
    claim_boundary_integrity = "PASS" if not claim_issues else "FAIL"
    replay_receipt = replay_receipt or {}
    lake_status = _lake_status_from_replay(replay_receipt, latest_diagnostic)
    replay_target_status = replay_receipt.get("target_replay_status") or (
        "PASS" if lake_status == "PASS" else ("ENVIRONMENT_BLOCKED" if lake_status == "ENVIRONMENT_BLOCKED" else "NOT_RUN")
    )
    reviewer_acceptance = _reviewer_acceptance_status(
        packet_integrity=packet_integrity,
        disclosure_boundary=disclosure_boundary,
        secret_exclusion=secret_exclusion,
        source_ref_integrity=source_ref_integrity,
        receipt_ref_integrity=receipt_ref_integrity,
        claim_boundary_integrity=claim_boundary_integrity,
        lake_replay_status=lake_status,
    )
    overall_status = "PASS" if reviewer_acceptance.startswith("REVIEWABLE") else "FAIL"
    return {
        "schema_version": FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_SCHEMA_VERSION,
        "kind": "lean_full_fidelity_evidence_packet_verification_receipt",
        "status": overall_status,
        "verifier_id": FULL_FIDELITY_PACKET_VERIFIER_ID,
        "verification_receipt_ref": FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL,
        "verification_markdown_ref": FULL_FIDELITY_PACKET_VERIFICATION_DOC_REL,
        "packet_ref": FULL_FIDELITY_PACKET_REL,
        "packet_receipt_ref": FULL_FIDELITY_PACKET_RECEIPT_REL,
        "packet_markdown_ref": FULL_FIDELITY_PACKET_DOC_REL,
        "replay_receipt_ref": FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
        "replay_markdown_ref": FULL_FIDELITY_PACKET_REPLAY_DOC_REL,
        "packet_sha256": expected_packet_sha,
        "packet_receipt_sha256": _sha256(packet_receipt),
        "replay_receipt_sha256": _sha256(replay_receipt) if replay_receipt else None,
        "packet_integrity": packet_integrity,
        "disclosure_boundary": disclosure_boundary,
        "secret_exclusion": secret_exclusion,
        "source_ref_integrity": source_ref_integrity,
        "receipt_ref_integrity": receipt_ref_integrity,
        "claim_boundary_integrity": claim_boundary_integrity,
        "station_render_surface": "NOT_RUN",
        "station_render_surface_reason": (
            "Render smoke is an external validation receipt; this deterministic verifier confirms the Station card surface contract."
        ),
        "lake_replay_status": lake_status,
        "dependency_hydration_status": replay_receipt.get("dependency_hydration_status"),
        "dependency_hydration_mode": replay_receipt.get("dependency_hydration_mode"),
        "lake_workspace_status": replay_receipt.get("lake_workspace_status") or {},
        "target_replay_status": replay_target_status,
        "target_runner_status": replay_receipt.get("target_runner_status") or packet_receipt.get("target_runner_status"),
        "latest_diagnostic_status": latest_diagnostic.get("status") if isinstance(latest_diagnostic, Mapping) else None,
        "latest_diagnostic_environment_status": (
            latest_diagnostic.get("environment_status") if isinstance(latest_diagnostic, Mapping) else None
        ),
        "latest_diagnostic_ref": latest_diagnostic.get("diagnostic_ref") if isinstance(latest_diagnostic, Mapping) else None,
        "recommended_dependency_commands": (
            latest_diagnostic.get("recommended_dependency_commands")
            if isinstance(latest_diagnostic, Mapping)
            else []
        )
        or [],
        "proof_authority_delta": "none",
        "reviewer_acceptance_status": reviewer_acceptance,
        "authority_invariant": AUTHORITY_INVARIANT,
        "source_ref_count": len(source_files),
        "receipt_ref_count": receipt_ref_count,
        "expanded_receipt_ref_count": len(receipt_ref_rows),
        "evidence_cell_ref_count": len(evidence_cells),
        "target_runner_receipt_count": len(target_runner_receipts),
        "thread_receipt_count": len(thread_receipts),
        "claim_boundary_count": claim_layer.get("claim_boundary_count", 0),
        "secret_exclusion_blocking_hit_count": verifier_secret_scan.get("blocking_hit_count"),
        "verification_checks": {
            "packet_integrity": {"status": packet_integrity, "issues": packet_integrity_issues},
            "disclosure_boundary": {
                "status": disclosure_boundary,
                "issues": disclosure_issues,
                "warnings": disclosure_warnings,
            },
            "secret_exclusion": {
                "status": secret_exclusion,
                "issues": secret_issues,
                "packet_scan": secret_scan,
                "verifier_scan": verifier_secret_scan,
            },
            "source_ref_integrity": {"status": source_ref_integrity, "issues": source_ref_issues},
            "receipt_ref_integrity": {"status": receipt_ref_integrity, "issues": receipt_ref_issues},
            "claim_boundary_integrity": {"status": claim_boundary_integrity, "issues": claim_issues},
            "lake_replay": {
                "status": lake_status,
                "replay_receipt_ref": FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL if replay_receipt else None,
                "dependency_hydration_status": replay_receipt.get("dependency_hydration_status"),
                "target_replay_status": replay_target_status,
                "diagnostic_ref": latest_diagnostic.get("diagnostic_ref") if isinstance(latest_diagnostic, Mapping) else None,
                "environment_status": latest_diagnostic.get("environment_status") if isinstance(latest_diagnostic, Mapping) else None,
                "dependency_cache_status": latest_diagnostic.get("dependency_cache_status")
                if isinstance(latest_diagnostic, Mapping)
                else None,
                "claim_boundary": "Replay status is separate from packet integrity and from proof authority.",
            },
        },
        "reviewer_instruction": (
            "Treat a verified packet as reviewer-acceptable inspection evidence. It is not proof authority unless "
            "the Lean/Lake and formal receipt lanes verify the exact claim."
        ),
    }


def _packet_source_file_rows(packet: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    source_layer = packet.get("source_disclosure_layer") if isinstance(packet.get("source_disclosure_layer"), Mapping) else {}
    return [
        row
        for project in source_layer.get("projects") or []
        if isinstance(project, Mapping)
        for row in project.get("source_files") or []
        if isinstance(row, Mapping)
    ]


def _capsule_ref_row(ref: str, payload: Mapping[str, Any], *, role: str) -> dict[str, Any]:
    return {
        "ref": ref,
        "role": role,
        "sha256": _sha256(payload),
        "hash_source": "generated_payload",
    }


def build_full_fidelity_cold_reviewer_capsule_manifest(
    packet: Mapping[str, Any],
    packet_receipt: Mapping[str, Any],
    replay_receipt: Mapping[str, Any],
    verification_receipt: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    source_files = [
        {
            "ref": str(row.get("source_ref")),
            "sha256": row.get("sha256"),
            "material_class": row.get("material_class"),
            "role": row.get("role"),
            "body_access": row.get("body_access"),
            "body_text_in_capsule_manifest": False,
        }
        for row in _packet_source_file_rows(packet)
        if isinstance(row.get("source_ref"), str) and row.get("source_ref")
    ]
    lake_workspace = (
        replay_receipt.get("lake_workspace_status")
        if isinstance(replay_receipt.get("lake_workspace_status"), Mapping)
        else {}
    )
    target_file = str(lake_workspace.get("target_file") or "")
    lake_root = str(lake_workspace.get("lake_root") or "")
    target_rel = target_file
    if target_file and lake_root:
        target_rel = _rel(_repo_path(target_file, repo_root=repo_root).resolve(), repo_root=_repo_path(lake_root, repo_root=repo_root))
    receipt_refs = [
        _capsule_ref_row(FULL_FIDELITY_PACKET_REL, packet, role="full_fidelity_packet"),
        _capsule_ref_row(FULL_FIDELITY_PACKET_RECEIPT_REL, packet_receipt, role="packet_receipt"),
        _capsule_ref_row(FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL, replay_receipt, role="local_replay_receipt"),
        _capsule_ref_row(FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL, verification_receipt, role="packet_verifier_receipt"),
        _capsule_ref_row(OUTPUT_REL, payload, role="lean_microcosm_projection"),
    ]
    return {
        "schema_version": FULL_FIDELITY_CAPSULE_SCHEMA_VERSION,
        "kind": "lean_full_fidelity_cold_reviewer_capsule_manifest",
        "capsule_id": FULL_FIDELITY_CAPSULE_ID,
        "capsule_manifest_ref": FULL_FIDELITY_CAPSULE_MANIFEST_REL,
        "capsule_receipt_ref": FULL_FIDELITY_CAPSULE_RECEIPT_REL,
        "capsule_markdown_ref": FULL_FIDELITY_CAPSULE_DOC_REL,
        "generated_at": str(payload.get("generated_at") or _utc_now()),
        "disclosure_posture_id": "operator_authorized_full_fidelity",
        "authority_posture": "review_transport_only_not_proof_authority",
        "authority_invariant": AUTHORITY_INVARIANT,
        "operator_authorization": {
            "posture_id": "operator_authorized_full_fidelity",
            "authorized_scope": "bounded Lean/Formal-Math reviewer capsule",
            "public_release_authorized": False,
            "credentials_or_unrelated_private_payloads_authorized": False,
        },
        "source_refs": source_files,
        "source_ref_count": len(source_files),
        "receipt_refs": receipt_refs,
        "receipt_ref_count": len(receipt_refs),
        "local_replay": {
            "receipt_ref": FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
            "dependency_hydration_status": replay_receipt.get("dependency_hydration_status"),
            "target_replay_status": replay_receipt.get("target_replay_status"),
            "reviewer_acceptance_status": replay_receipt.get("reviewer_acceptance_status"),
            "proof_authority_delta": replay_receipt.get("proof_authority_delta"),
        },
        "reviewer_workspace_plan": {
            "mode": "copy_declared_source_refs_to_isolated_workspace",
            "lake_root": lake_root,
            "lean_toolchain": lake_workspace.get("lean_toolchain"),
            "lakefile_ref": lake_workspace.get("lakefile_ref"),
            "lake_manifest_ref": lake_workspace.get("lake_manifest_ref"),
            "target_file": target_file,
            "target_rel_to_lake_root": target_rel,
            "hydration_command": "lake exe cache get",
            "target_replay_command": f"lake env lean --profile {target_rel}" if target_rel else None,
            "proof_authority_delta": "none",
        },
        "reviewer_instruction": (
            "Use this capsule as a deterministic inspection/replay transport. It can make local replay portability "
            "explicit, but proof authority still comes only from Lean/Lake owner receipts and formal evidence cells."
        ),
        "non_claims": [
            "not public release permission",
            "not a proof-authority upgrade",
            "not a claim that a reviewer has all third-party/legal disclosure rights",
            "not a claim of cold portability until capsule_replay_status is PASS",
        ],
    }


def _capsule_context_fingerprint(manifest: Mapping[str, Any]) -> str:
    return _sha256(
        {
            "capsule_id": manifest.get("capsule_id"),
            "source_refs": [
                {"ref": row.get("ref"), "sha256": row.get("sha256")}
                for row in manifest.get("source_refs") or []
                if isinstance(row, Mapping)
            ],
            "local_replay": manifest.get("local_replay"),
            "receipt_refs": [
                {"role": row.get("role"), "ref": row.get("ref")}
                for row in manifest.get("receipt_refs") or []
                if isinstance(row, Mapping)
            ],
            "reviewer_workspace_plan": manifest.get("reviewer_workspace_plan"),
        }
    )


def _preserved_capsule_attempt(
    previous_receipt: Mapping[str, Any],
    *,
    capsule_context_fingerprint: str,
) -> Mapping[str, Any] | None:
    if previous_receipt.get("capsule_context_fingerprint") != capsule_context_fingerprint:
        return None
    attempt = previous_receipt.get("capsule_replay_attempt")
    return attempt if isinstance(attempt, Mapping) else None


def _capsule_replay_status(attempt: Mapping[str, Any] | None) -> str:
    if not attempt:
        return "NOT_RUN"
    if attempt.get("timed_out") is True:
        return "TIMEOUT"
    if attempt.get("status") in {"ENVIRONMENT_BLOCKED", "BLOCKED"}:
        return "ENVIRONMENT_BLOCKED"
    if attempt.get("returncode") == 0 or attempt.get("target_returncode") == 0:
        return "PASS"
    if isinstance(attempt.get("returncode"), int) or isinstance(attempt.get("target_returncode"), int):
        return "FAIL"
    return str(attempt.get("status") or "NOT_RUN")


def _capsule_portability_status(
    *,
    capsule_integrity_status: str,
    capsule_secret_exclusion: str,
    local_replay_status: str,
    capsule_replay_status: str,
) -> str:
    if capsule_integrity_status != "PASS" or capsule_secret_exclusion != "PASS":
        return "REJECTED"
    if local_replay_status not in {"PASS", "REVIEWABLE_REPLAYED"}:
        return "PACKET_ONLY"
    if capsule_replay_status == "PASS":
        return "PORTABLE_REPLAYED"
    if capsule_replay_status in {"ENVIRONMENT_BLOCKED", "TIMEOUT"}:
        return "PORTABLE_WITH_ENVIRONMENT_BLOCK"
    if capsule_replay_status == "FAIL":
        return "REJECTED"
    return "LOCAL_ONLY_REPLAYED"


def build_full_fidelity_cold_reviewer_capsule_receipt(
    manifest: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    previous_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source_ref_issues: list[str] = []
    for row in manifest.get("source_refs") or []:
        if isinstance(row, Mapping):
            source_ref_issues.extend(_verify_hashed_file_ref(row, ref_key="ref", repo_root=repo_root))
    receipt_ref_issues = [
        f"missing_generated_hash:{row.get('ref')}"
        for row in manifest.get("receipt_refs") or []
        if isinstance(row, Mapping) and not row.get("sha256")
    ]
    capsule_integrity_status = "PASS" if not source_ref_issues and not receipt_ref_issues else "FAIL"
    scan_paths = [
        str(row.get("ref"))
        for row in manifest.get("source_refs") or []
        if isinstance(row, Mapping) and isinstance(row.get("ref"), str) and row.get("ref")
    ]
    secret_scan = _secret_exclusion_scan(
        list(dict.fromkeys(scan_paths)),
        repo_root=repo_root,
        payload=manifest,
    )
    capsule_secret_exclusion = (
        "PASS" if secret_scan.get("status") == "pass" and secret_scan.get("blocking_hit_count") == 0 else "FAIL"
    )
    local_replay = manifest.get("local_replay") if isinstance(manifest.get("local_replay"), Mapping) else {}
    local_replay_status = str(local_replay.get("target_replay_status") or "NOT_RUN")
    capsule_context_fingerprint = _capsule_context_fingerprint(manifest)
    attempt = _preserved_capsule_attempt(
        previous_receipt or {},
        capsule_context_fingerprint=capsule_context_fingerprint,
    )
    capsule_replay_status = _capsule_replay_status(attempt)
    capsule_portability_status = _capsule_portability_status(
        capsule_integrity_status=capsule_integrity_status,
        capsule_secret_exclusion=capsule_secret_exclusion,
        local_replay_status=local_replay_status,
        capsule_replay_status=capsule_replay_status,
    )
    return {
        "schema_version": FULL_FIDELITY_CAPSULE_RECEIPT_SCHEMA_VERSION,
        "kind": "lean_full_fidelity_cold_reviewer_capsule_receipt",
        "status": "PASS" if capsule_portability_status in {"PORTABLE_REPLAYED", "LOCAL_ONLY_REPLAYED"} else "BLOCKED",
        "capsule_id": manifest.get("capsule_id"),
        "capsule_manifest_ref": FULL_FIDELITY_CAPSULE_MANIFEST_REL,
        "capsule_receipt_ref": FULL_FIDELITY_CAPSULE_RECEIPT_REL,
        "capsule_markdown_ref": FULL_FIDELITY_CAPSULE_DOC_REL,
        "capsule_manifest_sha256": _sha256(manifest),
        "capsule_context_fingerprint": capsule_context_fingerprint,
        "packet_verifier_status": "PASS",
        "local_replay_status": local_replay_status,
        "local_reviewer_acceptance_status": local_replay.get("reviewer_acceptance_status"),
        "capsule_integrity_status": capsule_integrity_status,
        "capsule_secret_exclusion": capsule_secret_exclusion,
        "capsule_replay_status": capsule_replay_status,
        "capsule_portability_status": capsule_portability_status,
        "capsule_replay_attempt": attempt,
        "source_ref_count": manifest.get("source_ref_count"),
        "receipt_ref_count": manifest.get("receipt_ref_count"),
        "source_ref_issues": source_ref_issues,
        "receipt_ref_issues": receipt_ref_issues,
        "secret_exclusion_scan": secret_scan,
        "proof_authority_delta": "none",
        "authority_invariant": AUTHORITY_INVARIANT,
        "claim_boundary": (
            "Capsule verification is reviewer transport evidence. It does not upgrade proof authority; "
            "Lean/Lake target checks and formal owner receipts remain the authority lane."
        ),
    }


def _file_ref_row(ref: str, *, repo_root: Path, role: str) -> dict[str, Any]:
    path = _repo_path(ref, repo_root=repo_root)
    payload = _read_json_if_exists(path, repo_root=repo_root) if path.suffix == ".json" else {}
    return {
        "ref": ref,
        "role": role,
        "exists": path.is_file(),
        "sha256": _file_sha(path) if path.is_file() else None,
        "status": payload.get("status") if isinstance(payload, Mapping) else None,
        "public_toggle": payload.get("public_toggle") if isinstance(payload, Mapping) else None,
        "release_action": payload.get("release_action") if isinstance(payload, Mapping) else None,
        "hash_source": "file",
    }


def _release_authority_summary(*, repo_root: Path) -> dict[str, Any]:
    refs = [_file_ref_row(ref, repo_root=repo_root, role=role) for ref, role in RELEASE_GATE_REFS]
    readiness = _read_json_if_exists(RELEASE_GATE_REFS[0][0], repo_root=repo_root)
    decision_packet = _read_json_if_exists(RELEASE_GATE_REFS[1][0], repo_root=repo_root)
    decision_register = _read_json_if_exists(RELEASE_GATE_REFS[2][0], repo_root=repo_root)
    claim_gate = _read_json_if_exists(RELEASE_GATE_REFS[3][0], repo_root=repo_root)
    public_toggle = (
        readiness.get("public_toggle")
        or decision_register.get("public_toggle")
        or decision_packet.get("public_toggle")
        or "unknown"
    )
    release_action = (
        readiness.get("release_action")
        or decision_register.get("release_action")
        or decision_packet.get("release_action")
        or "none"
    )
    public_release_authority = (
        "granted"
        if public_toggle == "green" and isinstance(release_action, str) and release_action not in {"", "none"}
        else "none"
    )
    return {
        "source_refs": refs,
        "source_ref_count": len(refs),
        "status": readiness.get("status") or "unknown",
        "operator_decision_packet_status": decision_packet.get("status") or "unknown",
        "release_decision_register_status": decision_register.get("status") or "unknown",
        "claim_language_gate_status": claim_gate.get("status") or "unknown",
        "public_toggle": public_toggle,
        "release_action": release_action,
        "public_release_authority": public_release_authority,
        "allowed_current_wording": (
            (claim_gate.get("claim_guard") or {}).get("allowed_current_wording")
            if isinstance(claim_gate.get("claim_guard"), Mapping)
            else []
        ),
        "forbidden_current_wording": (
            (claim_gate.get("claim_guard") or {}).get("forbidden_current_wording")
            if isinstance(claim_gate.get("claim_guard"), Mapping)
            else []
        ),
        "claim_boundary": (
            "Release gates decide public/send authority. The Lean handoff envelope only cites their current "
            "fail-closed state and does not grant public release."
        ),
    }


def _handoff_payload_ref_rows(
    *,
    payload: Mapping[str, Any],
    packet: Mapping[str, Any],
    packet_receipt: Mapping[str, Any],
    replay_receipt: Mapping[str, Any],
    verification_receipt: Mapping[str, Any],
    capsule_manifest: Mapping[str, Any],
    capsule_receipt: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        _capsule_ref_row(FULL_FIDELITY_CAPSULE_MANIFEST_REL, capsule_manifest, role="cold_reviewer_capsule_manifest"),
        _capsule_ref_row(FULL_FIDELITY_CAPSULE_RECEIPT_REL, capsule_receipt, role="cold_reviewer_capsule_receipt"),
        _capsule_ref_row(FULL_FIDELITY_PACKET_REL, packet, role="full_fidelity_packet"),
        _capsule_ref_row(FULL_FIDELITY_PACKET_RECEIPT_REL, packet_receipt, role="packet_receipt"),
        _capsule_ref_row(FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL, replay_receipt, role="local_replay_receipt"),
        _capsule_ref_row(FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL, verification_receipt, role="packet_verifier_receipt"),
        _capsule_ref_row(OUTPUT_REL, payload, role="lean_microcosm_projection"),
    ]


def _handoff_reviewer_acceptance_status(
    *,
    handoff_authority_status: str,
    recipient_binding_status: str,
    handoff_delivery_status: str,
    external_reviewer_replay_status: str,
) -> str:
    if external_reviewer_replay_status == "PASS":
        return "REVIEWER_REPLAYED"
    if external_reviewer_replay_status in {"ENVIRONMENT_BLOCKED", "TIMEOUT"}:
        return "REVIEWER_BLOCKED"
    if external_reviewer_replay_status == "FAIL":
        return "REVIEW_REJECTED_OR_REQUIRES_REPAIR"
    if handoff_delivery_status == "ACKED":
        return "REVIEWER_ACKED"
    if recipient_binding_status == "RECIPIENT_BOUND":
        return "RECIPIENT_BOUND_DELIVERABLE_READY"
    if handoff_authority_status == "OPERATOR_AUTHORIZED":
        return "HANDOFF_READY_RECIPIENT_UNBOUND"
    return "PORTABLE_REPLAYED_NOT_HANDED_OFF"


def build_full_fidelity_reviewer_handoff_envelope(
    payload: Mapping[str, Any],
    packet: Mapping[str, Any],
    packet_receipt: Mapping[str, Any],
    replay_receipt: Mapping[str, Any],
    verification_receipt: Mapping[str, Any],
    capsule_manifest: Mapping[str, Any],
    capsule_receipt: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    release_authority = _release_authority_summary(repo_root=repo_root)
    handoff_authority_status = "OPERATOR_AUTHORIZED"
    recipient_binding_status = "RECIPIENT_UNBOUND"
    handoff_delivery_status = "NOT_DELIVERED"
    external_reviewer_replay_status = "NOT_RUN"
    reviewer_acceptance_status = _handoff_reviewer_acceptance_status(
        handoff_authority_status=handoff_authority_status,
        recipient_binding_status=recipient_binding_status,
        handoff_delivery_status=handoff_delivery_status,
        external_reviewer_replay_status=external_reviewer_replay_status,
    )
    source_refs = [
        {
            "ref": str(row.get("ref")),
            "sha256": row.get("sha256"),
            "material_class": row.get("material_class"),
            "role": row.get("role"),
            "body_access": row.get("body_access"),
            "body_text_in_handoff_envelope": False,
        }
        for row in capsule_manifest.get("source_refs") or []
        if isinstance(row, Mapping) and isinstance(row.get("ref"), str) and row.get("ref")
    ]
    return {
        "schema_version": FULL_FIDELITY_REVIEWER_HANDOFF_SCHEMA_VERSION,
        "kind": "lean_full_fidelity_reviewer_handoff_envelope",
        "handoff_id": FULL_FIDELITY_REVIEWER_HANDOFF_ID,
        "handoff_envelope_ref": FULL_FIDELITY_REVIEWER_HANDOFF_ENVELOPE_REL,
        "handoff_receipt_ref": FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_REL,
        "handoff_markdown_ref": FULL_FIDELITY_REVIEWER_HANDOFF_DOC_REL,
        "generated_at": str(payload.get("generated_at") or _utc_now()),
        "authority_posture": "recipient_handoff_transport_only_not_proof_authority",
        "disclosure_posture_id": "operator_authorized_full_fidelity",
        "handoff_authority_status": handoff_authority_status,
        "recipient_binding_status": recipient_binding_status,
        "recipient_class": "authorized_lean_full_fidelity_reviewer",
        "recipient_handle": None,
        "handoff_delivery_status": handoff_delivery_status,
        "external_reviewer_replay_status": external_reviewer_replay_status,
        "public_release_authority": release_authority["public_release_authority"],
        "release_action": release_authority["release_action"],
        "reviewer_acceptance_status": reviewer_acceptance_status,
        "proof_authority_delta": "none",
        "capsule_portability_status": capsule_receipt.get("capsule_portability_status"),
        "capsule_replay_status": capsule_receipt.get("capsule_replay_status"),
        "payload_refs": _handoff_payload_ref_rows(
            payload=payload,
            packet=packet,
            packet_receipt=packet_receipt,
            replay_receipt=replay_receipt,
            verification_receipt=verification_receipt,
            capsule_manifest=capsule_manifest,
            capsule_receipt=capsule_receipt,
        ),
        "source_refs": source_refs,
        "source_ref_count": len(source_refs),
        "release_authority": release_authority,
        "allowed_materials": [
            "cold capsule manifest and receipt refs",
            "full-fidelity packet, verifier, replay, and projection refs",
            "authorized Lean source refs and hashes",
            "reviewer replay commands from the capsule workspace plan",
            "non-claims, claim boundaries, and public-toggle no-release state",
        ],
        "withheld_boundary": [
            "credentials, tokens, preview credentials, and account/session secrets",
            "unrelated private root payloads",
            "raw seed or private ledgers unless separately authorized",
            "public-send or public-release permission",
        ],
        "receiver_synthesis_prompt": {
            "required_before_acceptance": True,
            "recipient_must_state_back": [
                "packet class",
                "chosen route or command",
                "inspectable scope",
                "withheld boundary",
                "confidence-changing proof or blocker",
            ],
            "response_intake_rule": (
                "Recipient responses are evidence inputs; they do not grant proof, release, send, or access authority."
            ),
        },
        "external_replay_entrypoint": {
            "runner": "tools/meta/factory/run_lean_full_fidelity_cold_reviewer_capsule.py",
            "command": (
                "./repo-python tools/meta/factory/run_lean_full_fidelity_cold_reviewer_capsule.py "
                "--attempt-replay --timeout-seconds 300 --write --compact"
            ),
            "status": external_reviewer_replay_status,
        },
        "revalidation_condition": (
            "Revalidate when the capsule source refs, receipt refs, release gates, recipient binding, or "
            "external replay receipt changes."
        ),
        "next_reentry_condition": "recipient/thread/outbox row supplied or release authority granted",
        "authority_invariant": AUTHORITY_INVARIANT,
        "non_claims": [
            "not public release permission",
            "not send authority",
            "not proof authority",
            "not evidence that an external reviewer has received, acknowledged, or replayed the capsule",
            "not authorization to disclose credentials, unrelated private state, or third-party-confidential material",
        ],
    }


def build_full_fidelity_reviewer_handoff_receipt(
    envelope: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    payload_ref_issues = [
        f"missing_generated_hash:{row.get('ref')}"
        for row in envelope.get("payload_refs") or []
        if isinstance(row, Mapping) and not row.get("sha256")
    ]
    source_ref_issues: list[str] = []
    for row in envelope.get("source_refs") or []:
        if isinstance(row, Mapping):
            source_ref_issues.extend(_verify_hashed_file_ref(row, ref_key="ref", repo_root=repo_root))
    release_ref_issues: list[str] = []
    release_authority = (
        envelope.get("release_authority")
        if isinstance(envelope.get("release_authority"), Mapping)
        else {}
    )
    for row in release_authority.get("source_refs") or []:
        if isinstance(row, Mapping) and row.get("exists") is not True:
            release_ref_issues.append(f"missing_release_authority_ref:{row.get('ref')}")
    handoff_integrity_status = (
        "PASS" if not payload_ref_issues and not source_ref_issues and not release_ref_issues else "FAIL"
    )
    scan_paths = [
        str(row.get("ref"))
        for row in envelope.get("source_refs") or []
        if isinstance(row, Mapping) and isinstance(row.get("ref"), str) and row.get("ref")
    ]
    secret_scan = _secret_exclusion_scan(
        list(dict.fromkeys(scan_paths)),
        repo_root=repo_root,
        payload=envelope,
    )
    handoff_secret_exclusion = (
        "PASS" if secret_scan.get("status") == "pass" and secret_scan.get("blocking_hit_count") == 0 else "FAIL"
    )
    disclosure_authority_status = (
        "PASS"
        if envelope.get("handoff_authority_status") == "OPERATOR_AUTHORIZED"
        and envelope.get("disclosure_posture_id") == "operator_authorized_full_fidelity"
        and envelope.get("public_release_authority") == "none"
        and envelope.get("proof_authority_delta") == "none"
        else "FAIL"
    )
    handoff_delivery_status = str(envelope.get("handoff_delivery_status") or "NOT_DELIVERED")
    external_reviewer_replay_status = str(envelope.get("external_reviewer_replay_status") or "NOT_RUN")
    recipient_binding_status = str(envelope.get("recipient_binding_status") or "RECIPIENT_UNBOUND")
    handoff_authority_status = str(envelope.get("handoff_authority_status") or "NOT_AUTHORIZED")
    reviewer_acceptance_status = _handoff_reviewer_acceptance_status(
        handoff_authority_status=handoff_authority_status,
        recipient_binding_status=recipient_binding_status,
        handoff_delivery_status=handoff_delivery_status,
        external_reviewer_replay_status=external_reviewer_replay_status,
    )
    status = (
        "PASS"
        if handoff_integrity_status == "PASS"
        and handoff_secret_exclusion == "PASS"
        and disclosure_authority_status == "PASS"
        else "BLOCKED"
    )
    return {
        "schema_version": FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_SCHEMA_VERSION,
        "kind": "lean_full_fidelity_reviewer_handoff_receipt",
        "status": status,
        "handoff_id": envelope.get("handoff_id"),
        "handoff_envelope_ref": FULL_FIDELITY_REVIEWER_HANDOFF_ENVELOPE_REL,
        "handoff_receipt_ref": FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_REL,
        "handoff_markdown_ref": FULL_FIDELITY_REVIEWER_HANDOFF_DOC_REL,
        "handoff_envelope_sha256": _sha256(envelope),
        "handoff_integrity_status": handoff_integrity_status,
        "handoff_secret_exclusion": handoff_secret_exclusion,
        "disclosure_authority_status": disclosure_authority_status,
        "handoff_authority_status": handoff_authority_status,
        "recipient_binding_status": recipient_binding_status,
        "handoff_delivery_status": handoff_delivery_status,
        "external_reviewer_replay_status": external_reviewer_replay_status,
        "public_release_authority": envelope.get("public_release_authority"),
        "release_action": envelope.get("release_action"),
        "reviewer_acceptance_status": reviewer_acceptance_status,
        "proof_authority_delta": envelope.get("proof_authority_delta"),
        "capsule_portability_status": envelope.get("capsule_portability_status"),
        "capsule_replay_status": envelope.get("capsule_replay_status"),
        "payload_ref_count": len(envelope.get("payload_refs") or []),
        "source_ref_count": envelope.get("source_ref_count"),
        "payload_ref_issues": payload_ref_issues,
        "source_ref_issues": source_ref_issues,
        "release_ref_issues": release_ref_issues,
        "secret_exclusion_scan": secret_scan,
        "authority_invariant": AUTHORITY_INVARIANT,
        "next_reentry_condition": envelope.get("next_reentry_condition"),
        "claim_boundary": (
            "The handoff receipt controls reviewer-use transport and disclosure posture only. It does not "
            "prove Lean claims, authorize public release, or record external reviewer acceptance."
        ),
    }


def _full_fidelity_packet_verifier_card(
    verification_receipt: Mapping[str, Any],
    capsule_receipt: Mapping[str, Any] | None = None,
    handoff_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    status = verification_receipt.get("status")
    capsule_receipt = capsule_receipt or {}
    handoff_receipt = handoff_receipt or {}
    return _surface_payload(
        "full_fidelity_packet_verifier_card",
        available=status == "PASS",
        issues=[] if status == "PASS" else ["full_fidelity_packet_verification_not_pass"],
        verifier_id=verification_receipt.get("verifier_id"),
        verification_receipt_ref=FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL,
        verification_markdown_ref=FULL_FIDELITY_PACKET_VERIFICATION_DOC_REL,
        replay_receipt_ref=verification_receipt.get("replay_receipt_ref") or FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
        replay_markdown_ref=verification_receipt.get("replay_markdown_ref") or FULL_FIDELITY_PACKET_REPLAY_DOC_REL,
        capsule_manifest_ref=FULL_FIDELITY_CAPSULE_MANIFEST_REL,
        capsule_receipt_ref=FULL_FIDELITY_CAPSULE_RECEIPT_REL,
        capsule_markdown_ref=FULL_FIDELITY_CAPSULE_DOC_REL,
        handoff_envelope_ref=FULL_FIDELITY_REVIEWER_HANDOFF_ENVELOPE_REL,
        handoff_receipt_ref=FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_REL,
        handoff_markdown_ref=FULL_FIDELITY_REVIEWER_HANDOFF_DOC_REL,
        packet_ref=verification_receipt.get("packet_ref") or FULL_FIDELITY_PACKET_REL,
        packet_receipt_ref=verification_receipt.get("packet_receipt_ref") or FULL_FIDELITY_PACKET_RECEIPT_REL,
        status=status,
        verification_receipt_sha256=_sha256(verification_receipt),
        replay_receipt_sha256=verification_receipt.get("replay_receipt_sha256"),
        capsule_receipt_sha256=_sha256(capsule_receipt) if capsule_receipt else None,
        handoff_receipt_sha256=_sha256(handoff_receipt) if handoff_receipt else None,
        packet_integrity=verification_receipt.get("packet_integrity"),
        disclosure_boundary=verification_receipt.get("disclosure_boundary"),
        secret_exclusion=verification_receipt.get("secret_exclusion"),
        source_ref_integrity=verification_receipt.get("source_ref_integrity"),
        receipt_ref_integrity=verification_receipt.get("receipt_ref_integrity"),
        claim_boundary_integrity=verification_receipt.get("claim_boundary_integrity"),
        station_render_surface=verification_receipt.get("station_render_surface"),
        lake_replay_status=verification_receipt.get("lake_replay_status"),
        dependency_hydration_status=verification_receipt.get("dependency_hydration_status"),
        dependency_hydration_mode=verification_receipt.get("dependency_hydration_mode"),
        target_replay_status=verification_receipt.get("target_replay_status"),
        target_runner_status=verification_receipt.get("target_runner_status"),
        lake_workspace_status=verification_receipt.get("lake_workspace_status") or {},
        latest_diagnostic_environment_status=verification_receipt.get("latest_diagnostic_environment_status"),
        latest_diagnostic_ref=verification_receipt.get("latest_diagnostic_ref"),
        reviewer_acceptance_status=verification_receipt.get("reviewer_acceptance_status"),
        capsule_integrity_status=capsule_receipt.get("capsule_integrity_status"),
        capsule_secret_exclusion=capsule_receipt.get("capsule_secret_exclusion"),
        capsule_replay_status=capsule_receipt.get("capsule_replay_status"),
        capsule_portability_status=capsule_receipt.get("capsule_portability_status"),
        handoff_integrity_status=handoff_receipt.get("handoff_integrity_status"),
        handoff_secret_exclusion=handoff_receipt.get("handoff_secret_exclusion"),
        disclosure_authority_status=handoff_receipt.get("disclosure_authority_status"),
        handoff_authority_status=handoff_receipt.get("handoff_authority_status"),
        recipient_binding_status=handoff_receipt.get("recipient_binding_status"),
        handoff_delivery_status=handoff_receipt.get("handoff_delivery_status"),
        external_reviewer_replay_status=handoff_receipt.get("external_reviewer_replay_status"),
        public_release_authority=handoff_receipt.get("public_release_authority"),
        handoff_reviewer_acceptance_status=handoff_receipt.get("reviewer_acceptance_status"),
        proof_authority_delta=verification_receipt.get("proof_authority_delta"),
        authority_invariant=verification_receipt.get("authority_invariant"),
    )


def attach_full_fidelity_packet_summary(
    payload: dict[str, Any],
    packet: Mapping[str, Any],
    packet_receipt: Mapping[str, Any],
    replay_receipt: Mapping[str, Any],
    verification_receipt: Mapping[str, Any],
    capsule_manifest: Mapping[str, Any] | None = None,
    capsule_receipt: Mapping[str, Any] | None = None,
    handoff_envelope: Mapping[str, Any] | None = None,
    handoff_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    card = _full_fidelity_packet_card(packet, packet_receipt)
    verifier_card = _full_fidelity_packet_verifier_card(
        verification_receipt,
        capsule_receipt,
        handoff_receipt,
    )
    payload["full_fidelity_packet"] = {
        "packet_id": packet.get("packet_id"),
        "packet_ref": FULL_FIDELITY_PACKET_REL,
        "receipt_ref": FULL_FIDELITY_PACKET_RECEIPT_REL,
        "markdown_ref": FULL_FIDELITY_PACKET_DOC_REL,
        "status": packet_receipt.get("status"),
        "source_file_count": packet_receipt.get("source_file_count", 0),
        "receipt_ref_count": packet_receipt.get("receipt_ref_count", 0),
        "secret_exclusion_status": packet_receipt.get("secret_exclusion_status"),
        "secret_exclusion_blocking_hit_count": packet_receipt.get("secret_exclusion_blocking_hit_count"),
        "authority_invariant": packet.get("authority_invariant"),
    }
    payload["full_fidelity_packet_verification"] = {
        "verifier_id": verification_receipt.get("verifier_id"),
        "verification_receipt_ref": FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL,
        "verification_markdown_ref": FULL_FIDELITY_PACKET_VERIFICATION_DOC_REL,
        "replay_receipt_ref": FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
        "replay_markdown_ref": FULL_FIDELITY_PACKET_REPLAY_DOC_REL,
        "status": verification_receipt.get("status"),
        "reviewer_acceptance_status": verification_receipt.get("reviewer_acceptance_status"),
        "lake_replay_status": verification_receipt.get("lake_replay_status"),
        "dependency_hydration_status": verification_receipt.get("dependency_hydration_status"),
        "target_replay_status": verification_receipt.get("target_replay_status"),
        "proof_authority_delta": verification_receipt.get("proof_authority_delta"),
        "authority_invariant": verification_receipt.get("authority_invariant"),
    }
    payload["full_fidelity_packet_replay"] = {
        "replay_id": replay_receipt.get("replay_id"),
        "replay_receipt_ref": FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
        "replay_markdown_ref": FULL_FIDELITY_PACKET_REPLAY_DOC_REL,
        "status": replay_receipt.get("status"),
        "dependency_hydration_status": replay_receipt.get("dependency_hydration_status"),
        "dependency_hydration_mode": replay_receipt.get("dependency_hydration_mode"),
        "target_replay_status": replay_receipt.get("target_replay_status"),
        "reviewer_acceptance_status": replay_receipt.get("reviewer_acceptance_status"),
        "proof_authority_delta": replay_receipt.get("proof_authority_delta"),
        "authority_invariant": replay_receipt.get("authority_invariant"),
    }
    payload["full_fidelity_cold_reviewer_capsule"] = {
        "capsule_id": (capsule_manifest or {}).get("capsule_id"),
        "capsule_manifest_ref": FULL_FIDELITY_CAPSULE_MANIFEST_REL,
        "capsule_receipt_ref": FULL_FIDELITY_CAPSULE_RECEIPT_REL,
        "capsule_markdown_ref": FULL_FIDELITY_CAPSULE_DOC_REL,
        "status": (capsule_receipt or {}).get("status"),
        "capsule_integrity_status": (capsule_receipt or {}).get("capsule_integrity_status"),
        "capsule_secret_exclusion": (capsule_receipt or {}).get("capsule_secret_exclusion"),
        "capsule_replay_status": (capsule_receipt or {}).get("capsule_replay_status"),
        "capsule_portability_status": (capsule_receipt or {}).get("capsule_portability_status"),
        "proof_authority_delta": (capsule_receipt or {}).get("proof_authority_delta"),
        "authority_invariant": (capsule_receipt or {}).get("authority_invariant"),
    }
    payload["full_fidelity_reviewer_handoff"] = {
        "handoff_id": (handoff_envelope or {}).get("handoff_id"),
        "handoff_envelope_ref": FULL_FIDELITY_REVIEWER_HANDOFF_ENVELOPE_REL,
        "handoff_receipt_ref": FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_REL,
        "handoff_markdown_ref": FULL_FIDELITY_REVIEWER_HANDOFF_DOC_REL,
        "status": (handoff_receipt or {}).get("status"),
        "handoff_authority_status": (handoff_receipt or {}).get("handoff_authority_status"),
        "recipient_binding_status": (handoff_receipt or {}).get("recipient_binding_status"),
        "handoff_delivery_status": (handoff_receipt or {}).get("handoff_delivery_status"),
        "external_reviewer_replay_status": (handoff_receipt or {}).get("external_reviewer_replay_status"),
        "public_release_authority": (handoff_receipt or {}).get("public_release_authority"),
        "reviewer_acceptance_status": (handoff_receipt or {}).get("reviewer_acceptance_status"),
        "proof_authority_delta": (handoff_receipt or {}).get("proof_authority_delta"),
        "authority_invariant": (handoff_receipt or {}).get("authority_invariant"),
    }
    visual = payload.get("visual_surfaces")
    if isinstance(visual, dict):
        keys = list(visual.get("surface_keys") or [])
        if "full_fidelity_packet_card" not in keys:
            insert_at = keys.index("disclosure_posture_cards") if "disclosure_posture_cards" in keys else len(keys)
            keys.insert(insert_at, "full_fidelity_packet_card")
        if "full_fidelity_packet_verifier_card" not in keys:
            insert_at = (
                keys.index("disclosure_posture_cards")
                if "disclosure_posture_cards" in keys
                else len(keys)
            )
            keys.insert(insert_at, "full_fidelity_packet_verifier_card")
        visual["surface_keys"] = keys
        visual["full_fidelity_packet_card"] = card
        visual["full_fidelity_packet_verifier_card"] = verifier_card
    observatory = payload.get("theorem_observatory")
    if isinstance(observatory, dict):
        authority_chain = [
            row
            for row in observatory.get("authority_chain") or []
            if not (isinstance(row, Mapping) and row.get("authority_id") == "full_fidelity_replay_verifier")
        ]
        authority_chain.append(
            {
                "authority_id": "full_fidelity_replay_verifier",
                "label": "Full-fidelity replay/verifier receipt",
                "status": verification_receipt.get("status"),
                "verification_receipt_ref": FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL,
                "replay_receipt_ref": FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
                "lake_replay_status": verification_receipt.get("lake_replay_status"),
                "dependency_hydration_status": verification_receipt.get("dependency_hydration_status"),
                "target_replay_status": verification_receipt.get("target_replay_status"),
                "proof_authority_delta": verification_receipt.get("proof_authority_delta"),
                "claim_boundary": verification_receipt.get("authority_invariant") or AUTHORITY_INVARIANT,
            }
        )
        observatory["authority_chain"] = authority_chain
        performance_boundary = observatory.get("performance_boundary")
        if not isinstance(performance_boundary, dict):
            performance_boundary = {}
        performance_boundary["full_fidelity_replay"] = {
            "verification_receipt_ref": FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL,
            "replay_receipt_ref": FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
            "lake_replay_status": verification_receipt.get("lake_replay_status"),
            "target_replay_status": verification_receipt.get("target_replay_status"),
            "dependency_hydration_status": verification_receipt.get("dependency_hydration_status"),
            "proof_authority_delta": verification_receipt.get("proof_authority_delta"),
            "claim_boundary": "replay/verifier receipts bound reproducibility and reviewability; proof authority delta remains explicit",
        }
        observatory["performance_boundary"] = performance_boundary
        _install_theorem_observatory_surface(payload)
    return payload


def build_projection_and_packet(
    *,
    repo_root: Path = REPO_ROOT,
    generated_at: str | None = None,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    payload = build_lean_mathematics_microcosm(repo_root=repo_root, generated_at=generated_at)
    packet = build_full_fidelity_evidence_packet(payload, repo_root=repo_root)
    packet_receipt = build_full_fidelity_evidence_packet_receipt(packet)
    previous_replay_receipt = _read_json_if_exists(FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL, repo_root=repo_root)
    replay_receipt = build_full_fidelity_evidence_packet_replay_receipt(
        packet,
        packet_receipt,
        repo_root=repo_root,
        previous_receipt=previous_replay_receipt,
    )
    verification_receipt = build_full_fidelity_evidence_packet_verification_receipt(
        packet,
        packet_receipt,
        repo_root=repo_root,
        replay_receipt=replay_receipt,
    )
    capsule_manifest = build_full_fidelity_cold_reviewer_capsule_manifest(
        packet,
        packet_receipt,
        replay_receipt,
        verification_receipt,
        payload,
        repo_root=repo_root,
    )
    previous_capsule_receipt = _read_json_if_exists(FULL_FIDELITY_CAPSULE_RECEIPT_REL, repo_root=repo_root)
    capsule_receipt = build_full_fidelity_cold_reviewer_capsule_receipt(
        capsule_manifest,
        repo_root=repo_root,
        previous_receipt=previous_capsule_receipt,
    )
    handoff_envelope = build_full_fidelity_reviewer_handoff_envelope(
        payload,
        packet,
        packet_receipt,
        replay_receipt,
        verification_receipt,
        capsule_manifest,
        capsule_receipt,
        repo_root=repo_root,
    )
    handoff_receipt = build_full_fidelity_reviewer_handoff_receipt(
        handoff_envelope,
        repo_root=repo_root,
    )
    attach_full_fidelity_packet_summary(
        payload,
        packet,
        packet_receipt,
        replay_receipt,
        verification_receipt,
        capsule_manifest,
        capsule_receipt,
        handoff_envelope,
        handoff_receipt,
    )
    return (
        payload,
        packet,
        packet_receipt,
        replay_receipt,
        verification_receipt,
        capsule_manifest,
        capsule_receipt,
        handoff_envelope,
        handoff_receipt,
    )


def build_receipt(
    payload: Mapping[str, Any],
    packet: Mapping[str, Any] | None = None,
    packet_receipt: Mapping[str, Any] | None = None,
    replay_receipt: Mapping[str, Any] | None = None,
    verification_receipt: Mapping[str, Any] | None = None,
    capsule_manifest: Mapping[str, Any] | None = None,
    capsule_receipt: Mapping[str, Any] | None = None,
    handoff_envelope: Mapping[str, Any] | None = None,
    handoff_receipt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    graph_views = payload.get("graph_views") if isinstance(payload.get("graph_views"), Mapping) else {}
    return {
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "status": "PASS",
        "projection_ref": OUTPUT_REL,
        "markdown_ref": DOC_REL,
        "full_fidelity_packet_ref": FULL_FIDELITY_PACKET_REL,
        "full_fidelity_packet_receipt_ref": FULL_FIDELITY_PACKET_RECEIPT_REL,
        "full_fidelity_packet_markdown_ref": FULL_FIDELITY_PACKET_DOC_REL,
        "full_fidelity_packet_verification_receipt_ref": FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL,
        "full_fidelity_packet_verification_markdown_ref": FULL_FIDELITY_PACKET_VERIFICATION_DOC_REL,
        "full_fidelity_packet_replay_receipt_ref": FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
        "full_fidelity_packet_replay_markdown_ref": FULL_FIDELITY_PACKET_REPLAY_DOC_REL,
        "full_fidelity_cold_reviewer_capsule_manifest_ref": FULL_FIDELITY_CAPSULE_MANIFEST_REL,
        "full_fidelity_cold_reviewer_capsule_receipt_ref": FULL_FIDELITY_CAPSULE_RECEIPT_REL,
        "full_fidelity_cold_reviewer_capsule_markdown_ref": FULL_FIDELITY_CAPSULE_DOC_REL,
        "full_fidelity_reviewer_handoff_envelope_ref": FULL_FIDELITY_REVIEWER_HANDOFF_ENVELOPE_REL,
        "full_fidelity_reviewer_handoff_receipt_ref": FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_REL,
        "full_fidelity_reviewer_handoff_markdown_ref": FULL_FIDELITY_REVIEWER_HANDOFF_DOC_REL,
        "projection_sha256": _sha256(payload),
        "full_fidelity_packet_sha256": _sha256(packet) if packet is not None else None,
        "full_fidelity_packet_receipt_sha256": _sha256(packet_receipt) if packet_receipt is not None else None,
        "full_fidelity_packet_replay_receipt_sha256": _sha256(replay_receipt)
        if replay_receipt is not None
        else None,
        "full_fidelity_packet_verification_receipt_sha256": _sha256(verification_receipt)
        if verification_receipt is not None
        else None,
        "full_fidelity_cold_reviewer_capsule_manifest_sha256": _sha256(capsule_manifest)
        if capsule_manifest is not None
        else None,
        "full_fidelity_cold_reviewer_capsule_receipt_sha256": _sha256(capsule_receipt)
        if capsule_receipt is not None
        else None,
        "full_fidelity_reviewer_handoff_envelope_sha256": _sha256(handoff_envelope)
        if handoff_envelope is not None
        else None,
        "full_fidelity_reviewer_handoff_receipt_sha256": _sha256(handoff_receipt)
        if handoff_receipt is not None
        else None,
        "full_fidelity_packet_status": packet_receipt.get("status") if isinstance(packet_receipt, Mapping) else None,
        "full_fidelity_packet_verification_status": verification_receipt.get("status")
        if isinstance(verification_receipt, Mapping)
        else None,
        "full_fidelity_packet_reviewer_acceptance_status": verification_receipt.get("reviewer_acceptance_status")
        if isinstance(verification_receipt, Mapping)
        else None,
        "full_fidelity_packet_lake_replay_status": verification_receipt.get("lake_replay_status")
        if isinstance(verification_receipt, Mapping)
        else None,
        "full_fidelity_packet_dependency_hydration_status": replay_receipt.get("dependency_hydration_status")
        if isinstance(replay_receipt, Mapping)
        else None,
        "full_fidelity_packet_target_replay_status": replay_receipt.get("target_replay_status")
        if isinstance(replay_receipt, Mapping)
        else None,
        "full_fidelity_cold_reviewer_capsule_portability_status": capsule_receipt.get("capsule_portability_status")
        if isinstance(capsule_receipt, Mapping)
        else None,
        "full_fidelity_cold_reviewer_capsule_replay_status": capsule_receipt.get("capsule_replay_status")
        if isinstance(capsule_receipt, Mapping)
        else None,
        "full_fidelity_reviewer_handoff_status": handoff_receipt.get("status")
        if isinstance(handoff_receipt, Mapping)
        else None,
        "full_fidelity_reviewer_handoff_authority_status": handoff_receipt.get("handoff_authority_status")
        if isinstance(handoff_receipt, Mapping)
        else None,
        "full_fidelity_reviewer_handoff_recipient_binding_status": handoff_receipt.get("recipient_binding_status")
        if isinstance(handoff_receipt, Mapping)
        else None,
        "full_fidelity_reviewer_handoff_delivery_status": handoff_receipt.get("handoff_delivery_status")
        if isinstance(handoff_receipt, Mapping)
        else None,
        "full_fidelity_reviewer_handoff_external_replay_status": handoff_receipt.get("external_reviewer_replay_status")
        if isinstance(handoff_receipt, Mapping)
        else None,
        "full_fidelity_reviewer_handoff_public_release_authority": handoff_receipt.get("public_release_authority")
        if isinstance(handoff_receipt, Mapping)
        else None,
        "full_fidelity_reviewer_handoff_acceptance_status": handoff_receipt.get("reviewer_acceptance_status")
        if isinstance(handoff_receipt, Mapping)
        else None,
        "source_fingerprint": payload["currentness"]["source_fingerprint"],
        "lean_project_count": payload["summary"]["lean_project_count"],
        "proof_thread_count": payload["summary"]["proof_thread_count"],
        "formal_math_test_count": payload["summary"]["formal_math_test_count"],
        "graph_views_fingerprint": _sha256(graph_views) if graph_views else None,
        "graph_views_keys": list(GRAPH_VIEW_KEYS),
        "graph_views_schema_version": graph_views.get("schema_version"),
        "graph_view_registry_ids": [
            str(row.get("view_id"))
            for row in graph_views.get("view_registry") or []
            if isinstance(row, Mapping) and row.get("view_id")
        ],
        "proof_spine_bundle_fingerprint": _sha256(graph_views.get("proof_spine_bundle") or {})
        if graph_views
        else None,
        "expansion_handles_fingerprint": _sha256(graph_views.get("expansion_handles") or {})
        if graph_views
        else None,
        "anti_claims": list(ANTI_CLAIMS),
        "disclosure_posture_ids": [
            str(row.get("posture_id"))
            for row in payload.get("disclosure_postures") or []
            if isinstance(row, Mapping) and row.get("posture_id")
        ],
    }


def _markdown_cell(value: Any, default: str = "not surfaced") -> str:
    if value is None or value == "":
        return default
    return str(value).replace("\n", " ").replace("|", "\\|")


def _markdown_duration_ms(value: Any) -> str:
    if value is None or value == "":
        return "not profiled"
    try:
        duration_ms = float(value)
    except (TypeError, ValueError):
        return str(value)
    if duration_ms >= 1000:
        return f"{duration_ms / 1000:.2f}s"
    return f"{duration_ms:.1f}ms"


def render_markdown(payload: Mapping[str, Any], receipt: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Lean Mathematics Microcosm")
    lines.append("")
    lines.append("_Generated by `tools/meta/factory/build_lean_mathematics_microcosm_projection.py`; dynamic projection, not proof authority._")
    lines.append("")
    lines.append("## Current Shape")
    lines.append("")
    summary = payload["summary"]
    lines.append(f"- Lean projects: `{summary['lean_project_count']}`")
    lines.append(f"- Lean files: `{summary['lean_file_count']}`")
    lines.append(f"- Formal-math proof threads: `{summary['proof_thread_count']}`")
    lines.append(f"- Formal-math tests: `{summary['formal_math_test_count']}`")
    lines.append(f"- Source fingerprint: `{payload['currentness']['source_fingerprint']}`")
    graph_views = payload.get("graph_views") if isinstance(payload.get("graph_views"), Mapping) else {}
    lines.append(f"- Graph-view keys: `{len(graph_views.get('view_keys') or [])}`")
    packet = payload.get("full_fidelity_packet") if isinstance(payload.get("full_fidelity_packet"), Mapping) else {}
    if packet:
        lines.append(f"- Full-fidelity packet: `{packet.get('packet_ref')}` (`{packet.get('status')}`)")
    replay = (
        payload.get("full_fidelity_packet_replay")
        if isinstance(payload.get("full_fidelity_packet_replay"), Mapping)
        else {}
    )
    if replay:
        lines.append(
            "- Full-fidelity packet replay: `{}` (`{}` / `{}`)".format(
                replay.get("replay_receipt_ref"),
                replay.get("dependency_hydration_status"),
                replay.get("target_replay_status"),
            )
        )
    verifier = (
        payload.get("full_fidelity_packet_verification")
        if isinstance(payload.get("full_fidelity_packet_verification"), Mapping)
        else {}
    )
    if verifier:
        lines.append(
            "- Full-fidelity packet verifier: `{}` (`{}` / `{}`)".format(
                verifier.get("verification_receipt_ref"),
                verifier.get("status"),
                verifier.get("reviewer_acceptance_status"),
            )
        )
    handoff = (
        payload.get("full_fidelity_reviewer_handoff")
        if isinstance(payload.get("full_fidelity_reviewer_handoff"), Mapping)
        else {}
    )
    if handoff:
        lines.append(
            "- Reviewer handoff: `{}` (`{}` / `{}` / `{}`)".format(
                handoff.get("handoff_receipt_ref"),
                handoff.get("handoff_authority_status"),
                handoff.get("recipient_binding_status"),
                handoff.get("reviewer_acceptance_status"),
            )
        )
    lines.append("")
    lines.append("## Disclosure Postures")
    lines.append("")
    lines.append("Disclosure scope controls what can be shown; proof authority controls what can be claimed.")
    lines.append("")
    lines.append("| Posture | Scope | Proof authority effect |")
    lines.append("|---|---|---|")
    for posture in payload.get("disclosure_postures") or []:
        if not isinstance(posture, Mapping):
            continue
        lines.append(
            "| `{}` | {} | {} |".format(
                posture.get("posture_id"),
                posture.get("disclosure_scope"),
                posture.get("proof_authority_effect"),
            )
        )
    lines.append("")
    lines.append("## Lean Projects")
    lines.append("")
    lines.append("| Project | Files | Toolchain | Static risk scan |")
    lines.append("|---|---:|---|---|")
    for project in payload["lean_projects"]:
        risk = project["static_risk_scan"]
        lines.append(
            "| `{}` | `{}` | `{}` | sorry `{}`, admit `{}`, axiom `{}` |".format(
                project["project_id"],
                project["lean_file_count"],
                project.get("lean_toolchain") or "unknown",
                risk["sorry_count"],
                risk["admit_count"],
                risk["axiom_count"],
            )
        )
    lines.append("")
    lines.append("## Formal-Math Threads")
    lines.append("")
    lines.append("| Thread | Status | Receipts | Lean project refs |")
    lines.append("|---|---|---:|---|")
    for thread in payload["formal_math_threads"]:
        lines.append(
            "| `{}` | `{}` | `{}` | {} |".format(
                thread["thread_id"],
                thread["status"],
                len(thread["receipt_artifacts"]),
                ", ".join(f"`{item}`" for item in thread["lean_project_refs"]) or "`none`",
            )
        )
    lines.append("")
    observatory = (
        payload.get("theorem_observatory")
        if isinstance(payload.get("theorem_observatory"), Mapping)
        else {}
    )
    lines.append("## Theorem Observatory")
    lines.append("")
    if observatory:
        route = observatory.get("route") if isinstance(observatory.get("route"), Mapping) else {}
        canonical = (
            observatory.get("canonical_theorem")
            if isinstance(observatory.get("canonical_theorem"), Mapping)
            else {}
        )
        performance = (
            observatory.get("performance_boundary")
            if isinstance(observatory.get("performance_boundary"), Mapping)
            else {}
        )
        latest_diagnostic = (
            performance.get("latest_diagnostic")
            if isinstance(performance.get("latest_diagnostic"), Mapping)
            else {}
        )
        microscope = (
            observatory.get("certificate_microscope")
            if isinstance(observatory.get("certificate_microscope"), Mapping)
            else {}
        )
        certificate_def = (
            microscope.get("certificate_def")
            if isinstance(microscope.get("certificate_def"), Mapping)
            else {}
        )
        target_parameters = (
            microscope.get("target_parameters")
            if isinstance(microscope.get("target_parameters"), Mapping)
            else {}
        )
        row_cases = microscope.get("row_cases") if isinstance(microscope.get("row_cases"), list) else []
        lines.append(f"- Observatory: `{observatory.get('observatory_id')}`")
        lines.append(f"- Canonical theorem: `{canonical.get('lean_declaration') or canonical.get('label')}`")
        lines.append(f"- Source: `{canonical.get('source_ref')}` lines `{canonical.get('line_start')}`-`{canonical.get('line_end')}`")
        lines.append(f"- Route steps: `{route.get('route_step_count')}`")
        lines.append(f"- Branch bundles: `{route.get('branch_bundle_count')}`")
        lines.append(
            "- Condensed DAG: `{}` nodes / `{}` edges (`{}`)".format(
                route.get("condensed_dag_node_count"),
                route.get("condensed_dag_edge_count"),
                route.get("condensed_dag_status"),
            )
        )
        lines.append(f"- Certificate objects: `{len(observatory.get('certificate_objects') or [])}`")
        lines.append(
            "- Certificate microscope: `{}` rows from `{}` (`L={}, A={}, b={}, B={}, Q={}`)".format(
                len(row_cases),
                certificate_def.get("name") or "missing",
                target_parameters.get("L"),
                target_parameters.get("A"),
                target_parameters.get("b"),
                target_parameters.get("B"),
                target_parameters.get("Q"),
            )
        )
        for row in row_cases[:4]:
            if not isinstance(row, Mapping):
                continue
            lines.append(
                "  - row `p={}` -> witness `q={}`, quotient `{}`, exponents quotient/A `{}`/`{}`".format(
                    row.get("p"),
                    row.get("witness_prime_q"),
                    row.get("prime_component_quotient"),
                    row.get("quotient_factorization_exponent"),
                    row.get("A_factorization_exponent"),
                )
            )
        lines.append(f"- Authority chain entries: `{len(observatory.get('authority_chain') or [])}`")
        lines.append(f"- Latest diagnostic: `{latest_diagnostic.get('diagnostic_ref')}` (`{latest_diagnostic.get('environment_status')}`)")
        lines.append(
            "- Diagnostic source boundary: `{}`".format(
                latest_diagnostic.get("latest_observation_projection_participation")
                or latest_diagnostic.get("projection_participation")
                or "not surfaced"
            )
        )
        lines.append(f"- Authority boundary: {observatory.get('authority_boundary')}")
    else:
        lines.append("- `theorem_observatory` missing from projection.")
    lines.append("")
    architecture = (
        observatory.get("proof_architecture")
        if isinstance(observatory.get("proof_architecture"), Mapping)
        else {}
    )
    lines.append("## Proof Architecture")
    lines.append("")
    if architecture:
        trust_summary = (
            architecture.get("trust_summary")
            if isinstance(architecture.get("trust_summary"), Mapping)
            else {}
        )
        lines.append(f"- Schema: `{architecture.get('schema_version')}`")
        lines.append(f"- Available: `{architecture.get('available')}`")
        lines.append(f"- Annotation authority: {architecture.get('annotation_authority')}")
        lines.append(f"- Claim boundary: {architecture.get('claim_boundary')}")
        lines.append(f"- Topological layers: `{architecture.get('topological_layer_count')}`")
        lines.append(
            "- Trust summary: status `{}`; sorry `{}`, admit `{}`, axiom `{}`".format(
                trust_summary.get("status"),
                trust_summary.get("sorry_count"),
                trust_summary.get("admit_count"),
                trust_summary.get("axiom_count"),
            )
        )
        lines.append("")
        lines.append("| Conceptual layer | Role | Declarations | Profiled | Cost |")
        lines.append("|---|---|---:|---:|---:|")
        conceptual_layers = (
            architecture.get("conceptual_layers")
            if isinstance(architecture.get("conceptual_layers"), list)
            else []
        )
        for layer in conceptual_layers[:16]:
            if not isinstance(layer, Mapping):
                continue
            lines.append(
                "| `{}` | {} | `{}` | `{}` | `{}` |".format(
                    _markdown_cell(layer.get("title") or layer.get("layer_id")),
                    _markdown_cell(layer.get("role")),
                    layer.get("declaration_count"),
                    layer.get("profiled_declaration_count"),
                    _markdown_duration_ms(layer.get("total_duration_ms")),
                )
            )
        centerpieces = (
            architecture.get("centerpieces")
            if isinstance(architecture.get("centerpieces"), list)
            else []
        )
        if centerpieces:
            lines.append("")
            lines.append("| Centerpiece | Layer | Source | Plain-math gloss |")
            lines.append("|---|---|---|---|")
            for item in centerpieces[:8]:
                if not isinstance(item, Mapping):
                    continue
                lines.append(
                    "| `{}` | `{}` | `{}` line `{}` | {} |".format(
                        _markdown_cell(item.get("name")),
                        _markdown_cell(item.get("conceptual_layer_id")),
                        _markdown_cell(item.get("source_ref")),
                        item.get("line_start"),
                        _markdown_cell(item.get("plain_math")),
                    )
                )
        summits = architecture.get("summits") if isinstance(architecture.get("summits"), list) else []
        if summits:
            lines.append("")
            lines.append("| Summit | Significance | Source |")
            lines.append("|---|---|---|")
            for item in summits[:8]:
                if not isinstance(item, Mapping):
                    continue
                lines.append(
                    "| `{}` | `{}` | `{}` line `{}` |".format(
                        _markdown_cell(item.get("name")),
                        _markdown_cell(item.get("significance")),
                        _markdown_cell(item.get("source_ref")),
                        item.get("line_start"),
                    )
                )
    else:
        lines.append("- `proof_architecture` missing from theorem observatory projection.")
    lines.append("")
    flight_recorder = (
        observatory.get("proof_trace_flight_recorder")
        if isinstance(observatory.get("proof_trace_flight_recorder"), Mapping)
        else {}
    )
    lines.append("## Proof Trace Flight Recorder")
    lines.append("")
    if flight_recorder:
        coverage = (
            flight_recorder.get("coverage")
            if isinstance(flight_recorder.get("coverage"), Mapping)
            else {}
        )
        lines.append(f"- Schema: `{flight_recorder.get('schema_version')}`")
        lines.append(f"- Available: `{flight_recorder.get('available')}`")
        lines.append(f"- Authority boundary: {flight_recorder.get('authority_boundary')}")
        lines.append(f"- Freshness warning: {flight_recorder.get('freshness_warning') or 'none'}")
        lines.append(
            "- Coverage: `{}` profiled files / `{}` unprofiled files".format(
                coverage.get("profiled_file_count"),
                coverage.get("unprofiled_file_count"),
            )
        )
        profiled_files = (
            flight_recorder.get("profiled_files")
            if isinstance(flight_recorder.get("profiled_files"), list)
            else []
        )
        if profiled_files:
            lines.append("")
            lines.append("| Profiled file | Freshness | Duration | Attributed declarations | Lean declarations |")
            lines.append("|---|---|---:|---:|---:|")
            for item in profiled_files:
                if not isinstance(item, Mapping):
                    continue
                lines.append(
                    "| `{}` | `{}` | `{}` | `{}` | `{}` |".format(
                        _markdown_cell(Path(str(item.get("file") or "")).name),
                        _markdown_cell(item.get("profile_freshness")),
                        _markdown_duration_ms(item.get("total_duration_ms")),
                        item.get("attributed_declaration_count"),
                        item.get("declaration_count"),
                    )
                )
        top_cost_rows: list[Mapping[str, Any]] = []
        for item in profiled_files:
            if not isinstance(item, Mapping):
                continue
            for row in item.get("top_cost_declarations") or []:
                if isinstance(row, Mapping):
                    top_cost_rows.append(row)
        top_cost_rows.sort(key=lambda row: (-(float(row.get("total_duration_ms") or 0.0)), str(row.get("name"))))
        if top_cost_rows:
            lines.append("")
            lines.append("| Top-cost declaration | Duration | Dominant phase |")
            lines.append("|---|---:|---|")
            for row in top_cost_rows[:8]:
                lines.append(
                    "| `{}` | `{}` | `{}` |".format(
                        _markdown_cell(row.get("name")),
                        _markdown_duration_ms(row.get("total_duration_ms")),
                        _markdown_cell(row.get("dominant_phase")),
                    )
                )
        route_step_profiles = (
            flight_recorder.get("route_step_profiles")
            if isinstance(flight_recorder.get("route_step_profiles"), list)
            else []
        )
        if route_step_profiles:
            lines.append("")
            lines.append("| Route step profile | Status | Duration |")
            lines.append("|---|---|---:|")
            for row in route_step_profiles[:8]:
                if not isinstance(row, Mapping):
                    continue
                lines.append(
                    "| `{}` | `{}` | `{}` |".format(
                        _markdown_cell(row.get("name") or row.get("node_id")),
                        "available" if row.get("available") else "missing",
                        _markdown_duration_ms(row.get("total_duration_ms")),
                    )
                )
    else:
        lines.append("- `proof_trace_flight_recorder` missing from theorem observatory projection.")
    lines.append("")
    lines.append("## Graph Views")
    lines.append("")
    if graph_views:
        lines.append(f"- Source: `{graph_views.get('source_ref')}`")
        lines.append(f"- Source fingerprint: `{graph_views.get('source_fingerprint')}`")
        lines.append(f"- Dependency layers: `{len(graph_views.get('dependency_layers') or [])}`")
        lines.append(f"- Semantic families: `{len(graph_views.get('semantic_families') or [])}`")
        lines.append(f"- Final theorem routes: `{len(graph_views.get('final_theorem_routes') or [])}`")
        lines.append(f"- High-degree nodes: `{len(graph_views.get('high_degree_nodes') or [])}`")
        lines.append(f"- Terminal claims: `{len(graph_views.get('terminal_claims') or [])}`")
        lines.append(f"- External dependencies: `{len(graph_views.get('external_dependencies') or [])}`")
        proof_spine = graph_views.get("proof_spine_bundle") if isinstance(graph_views.get("proof_spine_bundle"), Mapping) else {}
        edge_views = graph_views.get("edge_views") if isinstance(graph_views.get("edge_views"), Mapping) else {}
        lines.append(f"- View registry: `{len(graph_views.get('view_registry') or [])}`")
        lines.append(f"- Proof-spine route steps: `{len(proof_spine.get('route_steps') or [])}`")
        lines.append(f"- Branch bundles: `{len(proof_spine.get('branch_bundles') or [])}`")
        lines.append(f"- Expansion handles: `{len(graph_views.get('expansion_handles') or {})}`")
        lines.append(f"- Transitive-reduction edges: `{len(edge_views.get('transitive_reduction_edges') or [])}`")
    else:
        lines.append("- `graph_views` missing from projection.")
    lines.append("")
    lines.append("## Evolution Guard")
    lines.append("")
    lines.append(f"- Check: `{payload['owner']['check_command']}`")
    lines.append(f"- Rebuild: `{payload['owner']['rebuild_command']}`")
    lines.append("- Rule: add sources under the declared roots, then rebuild; do not hand-maintain this projection.")
    lines.append("")
    lines.append("## Full-Fidelity Packet")
    lines.append("")
    if packet:
        lines.append(f"- Packet: `{packet.get('packet_ref')}`")
        lines.append(f"- Receipt: `{packet.get('receipt_ref')}`")
        lines.append(f"- Markdown: `{packet.get('markdown_ref')}`")
        lines.append(f"- Source files: `{packet.get('source_file_count')}`")
        lines.append(f"- Receipt refs: `{packet.get('receipt_ref_count')}`")
        lines.append(f"- Secret-exclusion status: `{packet.get('secret_exclusion_status')}`")
        lines.append(f"- Secret-exclusion blocking hits: `{packet.get('secret_exclusion_blocking_hit_count')}`")
        lines.append(f"- Authority invariant: {packet.get('authority_invariant')}")
    else:
        lines.append("- Full-fidelity packet summary missing from projection.")
    lines.append("")
    lines.append("## Full-Fidelity Packet Verifier")
    lines.append("")
    if verifier:
        lines.append(f"- Verification receipt: `{verifier.get('verification_receipt_ref')}`")
        lines.append(f"- Verification markdown: `{verifier.get('verification_markdown_ref')}`")
        lines.append(f"- Replay receipt: `{verifier.get('replay_receipt_ref')}`")
        lines.append(f"- Replay markdown: `{verifier.get('replay_markdown_ref')}`")
        lines.append(f"- Status: `{verifier.get('status')}`")
        lines.append(f"- Reviewer acceptance: `{verifier.get('reviewer_acceptance_status')}`")
        lines.append(f"- Lake replay: `{verifier.get('lake_replay_status')}`")
        lines.append(f"- Dependency hydration: `{verifier.get('dependency_hydration_status')}`")
        lines.append(f"- Target replay: `{verifier.get('target_replay_status')}`")
        lines.append(f"- Proof authority delta: `{verifier.get('proof_authority_delta')}`")
        lines.append(f"- Authority invariant: {verifier.get('authority_invariant')}")
    else:
        lines.append("- Full-fidelity packet verifier summary missing from projection.")
    lines.append("")
    lines.append("## Reviewer Handoff")
    lines.append("")
    if handoff:
        lines.append(f"- Handoff envelope: `{handoff.get('handoff_envelope_ref')}`")
        lines.append(f"- Handoff receipt: `{handoff.get('handoff_receipt_ref')}`")
        lines.append(f"- Handoff markdown: `{handoff.get('handoff_markdown_ref')}`")
        lines.append(f"- Authority: `{handoff.get('handoff_authority_status')}`")
        lines.append(f"- Recipient binding: `{handoff.get('recipient_binding_status')}`")
        lines.append(f"- Delivery: `{handoff.get('handoff_delivery_status')}`")
        lines.append(f"- External reviewer replay: `{handoff.get('external_reviewer_replay_status')}`")
        lines.append(f"- Public release authority: `{handoff.get('public_release_authority')}`")
        lines.append(f"- Reviewer acceptance: `{handoff.get('reviewer_acceptance_status')}`")
        lines.append(f"- Proof authority delta: `{handoff.get('proof_authority_delta')}`")
        lines.append(f"- Authority invariant: {handoff.get('authority_invariant')}")
    else:
        lines.append("- Reviewer handoff summary missing from projection.")
    lines.append("")
    lines.append("## Route Cards")
    lines.append("")
    for card in payload["route_cards"]:
        lines.append(f"- `{card['route_card_id']}`: {card['question']} -> `{card['answer_surface']}`")
    lines.append("")
    lines.append("## Anti-Claims")
    lines.append("")
    for item in payload["anti_claims"]:
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Receipt")
    lines.append("")
    lines.append(f"- Projection: `{receipt['projection_ref']}`")
    lines.append(f"- Projection SHA256: `{receipt['projection_sha256']}`")
    lines.append(f"- Source fingerprint: `{receipt['source_fingerprint']}`")
    lines.append("")
    return "\n".join(lines)


def render_full_fidelity_packet_markdown(packet: Mapping[str, Any], packet_receipt: Mapping[str, Any]) -> str:
    source_layer = packet.get("source_disclosure_layer") if isinstance(packet.get("source_disclosure_layer"), Mapping) else {}
    receipt_layer = packet.get("receipt_reproduction_layer") if isinstance(packet.get("receipt_reproduction_layer"), Mapping) else {}
    claim_layer = packet.get("claim_boundary_layer") if isinstance(packet.get("claim_boundary_layer"), Mapping) else {}
    secret_scan = packet.get("secret_exclusion_scan") if isinstance(packet.get("secret_exclusion_scan"), Mapping) else {}
    latest_diagnostic = receipt_layer.get("latest_diagnostic") if isinstance(receipt_layer.get("latest_diagnostic"), Mapping) else {}
    lines: list[str] = []
    lines.append("# Lean Full-Fidelity Evidence Packet")
    lines.append("")
    lines.append("_Operator-authorized inspection packet. It is not proof authority and not public release permission._")
    lines.append("")
    lines.append("## Authority")
    lines.append("")
    lines.append(f"- Packet id: `{packet.get('packet_id')}`")
    lines.append(f"- Disclosure posture: `{packet.get('disclosure_posture_id')}`")
    lines.append(f"- Receipt status: `{packet_receipt.get('status')}`")
    lines.append(f"- Authority invariant: {packet.get('authority_invariant')}")
    lines.append("")
    lines.append("## Source Disclosure")
    lines.append("")
    lines.append(f"- Lake projects: `{source_layer.get('lake_project_count', 0)}`")
    lines.append(f"- Source files: `{source_layer.get('source_file_count', 0)}`")
    lines.append(f"- Body storage policy: {source_layer.get('body_storage_policy')}")
    lines.append("")
    lines.append("| Project | Root | Source files | Toolchain |")
    lines.append("|---|---|---:|---|")
    for project in source_layer.get("projects") or []:
        if not isinstance(project, Mapping):
            continue
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` |".format(
                project.get("project_id"),
                project.get("root"),
                project.get("source_file_count"),
                project.get("lean_toolchain") or "unknown",
            )
        )
    lines.append("")
    lines.append("## Receipts And Reproduction")
    lines.append("")
    lines.append(f"- Evidence-cell refs: `{len(receipt_layer.get('evidence_cells') or [])}`")
    lines.append(f"- Target-runner receipts: `{len(receipt_layer.get('target_runner_receipts') or [])}`")
    lines.append(f"- Thread receipts: `{len(receipt_layer.get('thread_receipts') or [])}`")
    lines.append(f"- Latest diagnostic: `{latest_diagnostic.get('diagnostic_ref')}`")
    lines.append(f"- Latest diagnostic status: `{latest_diagnostic.get('status')}`")
    lines.append(f"- Latest diagnostic environment: `{latest_diagnostic.get('environment_status')}`")
    lines.append("")
    lines.append("## Secret Exclusion")
    lines.append("")
    lines.append(f"- Status: `{secret_scan.get('status')}`")
    lines.append(f"- Blocking hits: `{secret_scan.get('blocking_hit_count')}`")
    lines.append(f"- Scanner: `{secret_scan.get('scanner')}`")
    lines.append(f"- Boundary: {secret_scan.get('claim_boundary')}")
    lines.append("")
    lines.append("## Claim Boundary")
    lines.append("")
    lines.append(f"- Claim boundaries: `{claim_layer.get('claim_boundary_count', 0)}`")
    lines.append(f"- Release boundary: {claim_layer.get('release_boundary')}")
    lines.append(f"- Proof-body caveat: {claim_layer.get('proof_body_visibility_caveat')}")
    lines.append("")
    lines.append("## Anti-Claims")
    lines.append("")
    for claim in packet.get("non_claims") or []:
        lines.append(f"- {claim}")
    lines.append("")
    lines.append("## Receipt")
    lines.append("")
    lines.append(f"- Packet SHA256: `{packet_receipt.get('packet_sha256')}`")
    lines.append(f"- Source files: `{packet_receipt.get('source_file_count')}`")
    lines.append(f"- Receipt refs: `{packet_receipt.get('receipt_ref_count')}`")
    lines.append("")
    return "\n".join(lines)


def render_full_fidelity_packet_replay_markdown(replay_receipt: Mapping[str, Any]) -> str:
    workspace = (
        replay_receipt.get("lake_workspace_status")
        if isinstance(replay_receipt.get("lake_workspace_status"), Mapping)
        else {}
    )
    lines: list[str] = []
    lines.append("# Lean Full-Fidelity Evidence Packet Replay")
    lines.append("")
    lines.append("_Dependency hydration and target replay receipt. It classifies reviewer replay; it is not proof authority._")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Replay id: `{replay_receipt.get('replay_id')}`")
    lines.append(f"- Status: `{replay_receipt.get('status')}`")
    lines.append(f"- Dependency hydration: `{replay_receipt.get('dependency_hydration_status')}`")
    lines.append(f"- Hydration mode: `{replay_receipt.get('dependency_hydration_mode')}`")
    lines.append(f"- Target replay: `{replay_receipt.get('target_replay_status')}`")
    lines.append(f"- Reviewer acceptance: `{replay_receipt.get('reviewer_acceptance_status')}`")
    lines.append(f"- Proof authority delta: `{replay_receipt.get('proof_authority_delta')}`")
    lines.append("")
    lines.append("## Lake Workspace")
    lines.append("")
    lines.append(f"- Lake root: `{workspace.get('lake_root')}`")
    lines.append(f"- Toolchain: `{workspace.get('lean_toolchain')}`")
    lines.append(f"- Lakefile: `{workspace.get('lakefile_ref')}`")
    lines.append(f"- Manifest: `{workspace.get('lake_manifest_ref')}`")
    lines.append(f"- Mathlib rev: `{workspace.get('mathlib_rev')}`")
    lines.append(f"- Mathlib package: `{workspace.get('mathlib_package_status')}`")
    lines.append(f"- Expected import artifacts: `{workspace.get('expected_import_artifact_status')}`")
    missing = workspace.get("missing_import_artifacts")
    if isinstance(missing, list) and missing:
        lines.append("- Missing import artifacts:")
        for module in missing:
            lines.append(f"  - `{module}`")
    lines.append("")
    lines.append("## Attempts")
    lines.append("")
    lines.append(f"- Attempted at: `{replay_receipt.get('attempted_at')}`")
    hydration_attempt = replay_receipt.get("hydration_attempt")
    if isinstance(hydration_attempt, Mapping):
        lines.append(
            f"- Hydration command: `{hydration_attempt.get('command')}` "
            f"-> `{hydration_attempt.get('returncode')}`"
        )
    else:
        lines.append("- Hydration command: `not_attempted`")
    target_attempt = replay_receipt.get("target_attempt")
    if isinstance(target_attempt, Mapping):
        lines.append(
            f"- Target command: `{target_attempt.get('command')}` "
            f"-> `{target_attempt.get('returncode')}`"
        )
    else:
        lines.append("- Target command: `not_attempted`")
    commands = replay_receipt.get("recommended_dependency_commands")
    if isinstance(commands, list) and commands:
        lines.append("- Recommended dependency commands:")
        for command in commands:
            lines.append(f"  - `{command}`")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append(replay_receipt.get("claim_boundary") or "")
    lines.append("")
    return "\n".join(lines)


def render_full_fidelity_packet_verification_markdown(verification_receipt: Mapping[str, Any]) -> str:
    checks = (
        verification_receipt.get("verification_checks")
        if isinstance(verification_receipt.get("verification_checks"), Mapping)
        else {}
    )
    lines: list[str] = []
    lines.append("# Lean Full-Fidelity Evidence Packet Verification")
    lines.append("")
    lines.append("_Reviewer acceptance receipt. It verifies inspection transport; it is not proof authority._")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Verifier id: `{verification_receipt.get('verifier_id')}`")
    lines.append(f"- Status: `{verification_receipt.get('status')}`")
    lines.append(f"- Reviewer acceptance: `{verification_receipt.get('reviewer_acceptance_status')}`")
    lines.append(f"- Lake replay: `{verification_receipt.get('lake_replay_status')}`")
    lines.append(f"- Dependency hydration: `{verification_receipt.get('dependency_hydration_status')}`")
    lines.append(f"- Target replay: `{verification_receipt.get('target_replay_status')}`")
    lines.append(f"- Proof authority delta: `{verification_receipt.get('proof_authority_delta')}`")
    lines.append(f"- Authority invariant: {verification_receipt.get('authority_invariant')}")
    lines.append("")
    lines.append("## Integrity Checks")
    lines.append("")
    lines.append("| Check | Status | Issues |")
    lines.append("|---|---|---|")
    for key in (
        "packet_integrity",
        "source_ref_integrity",
        "receipt_ref_integrity",
        "disclosure_boundary",
        "secret_exclusion",
        "claim_boundary_integrity",
        "lake_replay",
    ):
        check = checks.get(key) if isinstance(checks.get(key), Mapping) else {}
        issues = check.get("issues") if isinstance(check.get("issues"), list) else []
        lines.append(
            "| `{}` | `{}` | {} |".format(
                key,
                check.get("status") or verification_receipt.get(key),
                ", ".join(f"`{issue}`" for issue in issues) if issues else "`none`",
            )
        )
    lines.append("")
    lines.append("## Replay Classification")
    lines.append("")
    lines.append(f"- Replay receipt: `{verification_receipt.get('replay_receipt_ref')}`")
    lines.append(f"- Latest diagnostic: `{verification_receipt.get('latest_diagnostic_ref')}`")
    lines.append(f"- Diagnostic status: `{verification_receipt.get('latest_diagnostic_status')}`")
    lines.append(f"- Environment status: `{verification_receipt.get('latest_diagnostic_environment_status')}`")
    commands = verification_receipt.get("recommended_dependency_commands")
    if isinstance(commands, list) and commands:
        lines.append("- Recommended dependency commands:")
        for command in commands:
            lines.append(f"  - `{command}`")
    else:
        lines.append("- Recommended dependency commands: `none`")
    lines.append("")
    lines.append("## Source And Receipt Counts")
    lines.append("")
    lines.append(f"- Source refs checked: `{verification_receipt.get('source_ref_count')}`")
    lines.append(f"- Receipt refs checked: `{verification_receipt.get('expanded_receipt_ref_count')}`")
    lines.append(f"- Evidence-cell refs: `{verification_receipt.get('evidence_cell_ref_count')}`")
    lines.append(f"- Target-runner refs: `{verification_receipt.get('target_runner_receipt_count')}`")
    lines.append(f"- Secret blocking hits: `{verification_receipt.get('secret_exclusion_blocking_hit_count')}`")
    lines.append("")
    lines.append("## Receipt")
    lines.append("")
    lines.append(f"- Packet: `{verification_receipt.get('packet_ref')}`")
    lines.append(f"- Packet receipt: `{verification_receipt.get('packet_receipt_ref')}`")
    lines.append(f"- Packet SHA256: `{verification_receipt.get('packet_sha256')}`")
    lines.append("")
    lines.append(verification_receipt.get("reviewer_instruction") or "")
    lines.append("")
    return "\n".join(lines)


def render_full_fidelity_cold_reviewer_capsule_markdown(
    manifest: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> str:
    plan = manifest.get("reviewer_workspace_plan") if isinstance(manifest.get("reviewer_workspace_plan"), Mapping) else {}
    lines: list[str] = []
    lines.append("# Lean Full-Fidelity Cold Reviewer Capsule")
    lines.append("")
    lines.append("_Authorized reviewer transport. It is not public release permission or proof authority._")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Capsule id: `{manifest.get('capsule_id')}`")
    lines.append(f"- Capsule integrity: `{receipt.get('capsule_integrity_status')}`")
    lines.append(f"- Capsule secret exclusion: `{receipt.get('capsule_secret_exclusion')}`")
    lines.append(f"- Local replay status: `{receipt.get('local_replay_status')}`")
    lines.append(f"- Capsule replay status: `{receipt.get('capsule_replay_status')}`")
    lines.append(f"- Capsule portability: `{receipt.get('capsule_portability_status')}`")
    lines.append(f"- Proof authority delta: `{receipt.get('proof_authority_delta')}`")
    lines.append(f"- Authority invariant: {receipt.get('authority_invariant')}")
    lines.append("")
    lines.append("## Reviewer Workspace Plan")
    lines.append("")
    lines.append(f"- Mode: `{plan.get('mode')}`")
    lines.append(f"- Lake root: `{plan.get('lake_root')}`")
    lines.append(f"- Toolchain: `{plan.get('lean_toolchain')}`")
    lines.append(f"- Hydration command: `{plan.get('hydration_command')}`")
    lines.append(f"- Target replay command: `{plan.get('target_replay_command')}`")
    lines.append("")
    lines.append("## Refs")
    lines.append("")
    lines.append(f"- Source refs: `{manifest.get('source_ref_count')}`")
    lines.append(f"- Receipt refs: `{manifest.get('receipt_ref_count')}`")
    lines.append(f"- Manifest hash: `{receipt.get('capsule_manifest_sha256')}`")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append(receipt.get("claim_boundary") or "")
    lines.append("")
    return "\n".join(lines)


def render_full_fidelity_reviewer_handoff_markdown(
    envelope: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> str:
    release_authority = (
        envelope.get("release_authority")
        if isinstance(envelope.get("release_authority"), Mapping)
        else {}
    )
    lines: list[str] = []
    lines.append("# Lean Full-Fidelity Reviewer Handoff")
    lines.append("")
    lines.append("_Recipient-bound handoff envelope. It is not public release permission or proof authority._")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Handoff id: `{envelope.get('handoff_id')}`")
    lines.append(f"- Receipt status: `{receipt.get('status')}`")
    lines.append(f"- Handoff authority: `{receipt.get('handoff_authority_status')}`")
    lines.append(f"- Recipient binding: `{receipt.get('recipient_binding_status')}`")
    lines.append(f"- Delivery: `{receipt.get('handoff_delivery_status')}`")
    lines.append(f"- External reviewer replay: `{receipt.get('external_reviewer_replay_status')}`")
    lines.append(f"- Public release authority: `{receipt.get('public_release_authority')}`")
    lines.append(f"- Reviewer acceptance: `{receipt.get('reviewer_acceptance_status')}`")
    lines.append(f"- Proof authority delta: `{receipt.get('proof_authority_delta')}`")
    lines.append(f"- Authority invariant: {receipt.get('authority_invariant')}")
    lines.append("")
    lines.append("## Payload")
    lines.append("")
    lines.append(f"- Payload refs: `{receipt.get('payload_ref_count')}`")
    lines.append(f"- Source refs: `{receipt.get('source_ref_count')}`")
    lines.append(f"- Secret exclusion: `{receipt.get('handoff_secret_exclusion')}`")
    lines.append(f"- Disclosure authority: `{receipt.get('disclosure_authority_status')}`")
    lines.append(f"- Envelope SHA256: `{receipt.get('handoff_envelope_sha256')}`")
    lines.append("")
    lines.append("## Release Gate")
    lines.append("")
    lines.append(f"- Public release authority: `{release_authority.get('public_release_authority')}`")
    lines.append(f"- Release action: `{release_authority.get('release_action')}`")
    lines.append(f"- Gate statuses: `{release_authority.get('gate_statuses')}`")
    lines.append(f"- Public toggles: `{release_authority.get('public_toggles')}`")
    lines.append("")
    lines.append("## Receiver Synthesis")
    lines.append("")
    receiver = (
        envelope.get("receiver_synthesis_prompt")
        if isinstance(envelope.get("receiver_synthesis_prompt"), Mapping)
        else {}
    )
    lines.append(f"- Required before acceptance: `{receiver.get('required_before_acceptance')}`")
    for item in receiver.get("recipient_must_state_back") or []:
        lines.append(f"- Recipient must state back: `{item}`")
    lines.append("")
    lines.append("## Non-Claims")
    lines.append("")
    for claim in envelope.get("non_claims") or []:
        lines.append(f"- {claim}")
    lines.append("")
    lines.append("## Re-entry")
    lines.append("")
    lines.append(f"- Next condition: `{receipt.get('next_reentry_condition')}`")
    lines.append(f"- Claim boundary: {receipt.get('claim_boundary')}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(*, repo_root: Path = REPO_ROOT, generated_at: str | None = None) -> dict[str, Any]:
    (
        payload,
        packet,
        packet_receipt,
        replay_receipt,
        verification_receipt,
        capsule_manifest,
        capsule_receipt,
        handoff_envelope,
        handoff_receipt,
    ) = build_projection_and_packet(
        repo_root=repo_root,
        generated_at=generated_at,
    )
    receipt = build_receipt(
        payload,
        packet=packet,
        packet_receipt=packet_receipt,
        replay_receipt=replay_receipt,
        verification_receipt=verification_receipt,
        capsule_manifest=capsule_manifest,
        capsule_receipt=capsule_receipt,
        handoff_envelope=handoff_envelope,
        handoff_receipt=handoff_receipt,
    )
    markdown = render_markdown(payload, receipt)
    packet_markdown = render_full_fidelity_packet_markdown(packet, packet_receipt)
    replay_markdown = render_full_fidelity_packet_replay_markdown(replay_receipt)
    verification_markdown = render_full_fidelity_packet_verification_markdown(verification_receipt)
    capsule_markdown = render_full_fidelity_cold_reviewer_capsule_markdown(capsule_manifest, capsule_receipt)
    handoff_markdown = render_full_fidelity_reviewer_handoff_markdown(handoff_envelope, handoff_receipt)
    _write_json(OUTPUT_REL, payload, repo_root=repo_root)
    _write_json(RECEIPT_REL, receipt, repo_root=repo_root)
    _write_text(DOC_REL, markdown, repo_root=repo_root)
    _write_json(FULL_FIDELITY_PACKET_REL, packet, repo_root=repo_root)
    _write_json(FULL_FIDELITY_PACKET_RECEIPT_REL, packet_receipt, repo_root=repo_root)
    _write_text(FULL_FIDELITY_PACKET_DOC_REL, packet_markdown, repo_root=repo_root)
    _write_json(FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL, replay_receipt, repo_root=repo_root)
    _write_text(FULL_FIDELITY_PACKET_REPLAY_DOC_REL, replay_markdown, repo_root=repo_root)
    _write_json(FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL, verification_receipt, repo_root=repo_root)
    _write_text(FULL_FIDELITY_PACKET_VERIFICATION_DOC_REL, verification_markdown, repo_root=repo_root)
    _write_json(FULL_FIDELITY_CAPSULE_MANIFEST_REL, capsule_manifest, repo_root=repo_root)
    _write_json(FULL_FIDELITY_CAPSULE_RECEIPT_REL, capsule_receipt, repo_root=repo_root)
    _write_text(FULL_FIDELITY_CAPSULE_DOC_REL, capsule_markdown, repo_root=repo_root)
    _write_json(FULL_FIDELITY_REVIEWER_HANDOFF_ENVELOPE_REL, handoff_envelope, repo_root=repo_root)
    _write_json(FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_REL, handoff_receipt, repo_root=repo_root)
    _write_text(FULL_FIDELITY_REVIEWER_HANDOFF_DOC_REL, handoff_markdown, repo_root=repo_root)
    return receipt


def check_outputs(*, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    actual = _read_json_if_exists(OUTPUT_REL, repo_root=repo_root)
    generated_at = actual.get("generated_at") if isinstance(actual.get("generated_at"), str) else None
    (
        expected,
        expected_packet,
        expected_packet_receipt,
        expected_replay_receipt,
        expected_verification_receipt,
        expected_capsule_manifest,
        expected_capsule_receipt,
        expected_handoff_envelope,
        expected_handoff_receipt,
    ) = build_projection_and_packet(
        repo_root=repo_root,
        generated_at=generated_at,
    )
    expected_receipt = build_receipt(
        expected,
        packet=expected_packet,
        packet_receipt=expected_packet_receipt,
        replay_receipt=expected_replay_receipt,
        verification_receipt=expected_verification_receipt,
        capsule_manifest=expected_capsule_manifest,
        capsule_receipt=expected_capsule_receipt,
        handoff_envelope=expected_handoff_envelope,
        handoff_receipt=expected_handoff_receipt,
    )
    expected_markdown = render_markdown(expected, expected_receipt)
    expected_packet_markdown = render_full_fidelity_packet_markdown(expected_packet, expected_packet_receipt)
    expected_replay_markdown = render_full_fidelity_packet_replay_markdown(expected_replay_receipt)
    expected_verification_markdown = render_full_fidelity_packet_verification_markdown(expected_verification_receipt)
    expected_capsule_markdown = render_full_fidelity_cold_reviewer_capsule_markdown(
        expected_capsule_manifest,
        expected_capsule_receipt,
    )
    expected_handoff_markdown = render_full_fidelity_reviewer_handoff_markdown(
        expected_handoff_envelope,
        expected_handoff_receipt,
    )
    actual_receipt = _read_json_if_exists(RECEIPT_REL, repo_root=repo_root)
    actual_packet = _read_json_if_exists(FULL_FIDELITY_PACKET_REL, repo_root=repo_root)
    actual_packet_receipt = _read_json_if_exists(FULL_FIDELITY_PACKET_RECEIPT_REL, repo_root=repo_root)
    actual_replay_receipt = _read_json_if_exists(FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL, repo_root=repo_root)
    actual_verification_receipt = _read_json_if_exists(FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL, repo_root=repo_root)
    actual_capsule_manifest = _read_json_if_exists(FULL_FIDELITY_CAPSULE_MANIFEST_REL, repo_root=repo_root)
    actual_capsule_receipt = _read_json_if_exists(FULL_FIDELITY_CAPSULE_RECEIPT_REL, repo_root=repo_root)
    actual_handoff_envelope = _read_json_if_exists(FULL_FIDELITY_REVIEWER_HANDOFF_ENVELOPE_REL, repo_root=repo_root)
    actual_handoff_receipt = _read_json_if_exists(FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_REL, repo_root=repo_root)
    doc_path = _repo_path(DOC_REL, repo_root=repo_root)
    packet_doc_path = _repo_path(FULL_FIDELITY_PACKET_DOC_REL, repo_root=repo_root)
    replay_doc_path = _repo_path(FULL_FIDELITY_PACKET_REPLAY_DOC_REL, repo_root=repo_root)
    verification_doc_path = _repo_path(FULL_FIDELITY_PACKET_VERIFICATION_DOC_REL, repo_root=repo_root)
    capsule_doc_path = _repo_path(FULL_FIDELITY_CAPSULE_DOC_REL, repo_root=repo_root)
    handoff_doc_path = _repo_path(FULL_FIDELITY_REVIEWER_HANDOFF_DOC_REL, repo_root=repo_root)
    actual_markdown = doc_path.read_text(encoding="utf-8") if doc_path.exists() else ""
    actual_packet_markdown = packet_doc_path.read_text(encoding="utf-8") if packet_doc_path.exists() else ""
    actual_replay_markdown = replay_doc_path.read_text(encoding="utf-8") if replay_doc_path.exists() else ""
    actual_verification_markdown = verification_doc_path.read_text(encoding="utf-8") if verification_doc_path.exists() else ""
    actual_capsule_markdown = capsule_doc_path.read_text(encoding="utf-8") if capsule_doc_path.exists() else ""
    actual_handoff_markdown = handoff_doc_path.read_text(encoding="utf-8") if handoff_doc_path.exists() else ""
    issues: list[str] = []
    if actual != expected:
        issues.append(f"stale_or_missing:{OUTPUT_REL}")
    if actual_receipt != expected_receipt:
        issues.append(f"stale_or_missing:{RECEIPT_REL}")
    if actual_markdown != expected_markdown:
        issues.append(f"stale_or_missing:{DOC_REL}")
    if actual_packet != expected_packet:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_PACKET_REL}")
    if actual_packet_receipt != expected_packet_receipt:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_PACKET_RECEIPT_REL}")
    if actual_packet_markdown != expected_packet_markdown:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_PACKET_DOC_REL}")
    if actual_replay_receipt != expected_replay_receipt:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL}")
    if actual_replay_markdown != expected_replay_markdown:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_PACKET_REPLAY_DOC_REL}")
    if actual_verification_receipt != expected_verification_receipt:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL}")
    if actual_verification_markdown != expected_verification_markdown:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_PACKET_VERIFICATION_DOC_REL}")
    if actual_capsule_manifest != expected_capsule_manifest:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_CAPSULE_MANIFEST_REL}")
    if actual_capsule_receipt != expected_capsule_receipt:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_CAPSULE_RECEIPT_REL}")
    if actual_capsule_markdown != expected_capsule_markdown:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_CAPSULE_DOC_REL}")
    if actual_handoff_envelope != expected_handoff_envelope:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_REVIEWER_HANDOFF_ENVELOPE_REL}")
    if actual_handoff_receipt != expected_handoff_receipt:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_REL}")
    if actual_handoff_markdown != expected_handoff_markdown:
        issues.append(f"stale_or_missing:{FULL_FIDELITY_REVIEWER_HANDOFF_DOC_REL}")
    return {
        "schema_version": CHECK_SCHEMA_VERSION,
        "status": "PASS" if not issues else "FAIL",
        "issues": issues,
        "projection_ref": OUTPUT_REL,
        "receipt_ref": RECEIPT_REL,
        "markdown_ref": DOC_REL,
        "full_fidelity_packet_ref": FULL_FIDELITY_PACKET_REL,
        "full_fidelity_packet_receipt_ref": FULL_FIDELITY_PACKET_RECEIPT_REL,
        "full_fidelity_packet_markdown_ref": FULL_FIDELITY_PACKET_DOC_REL,
        "full_fidelity_packet_verification_receipt_ref": FULL_FIDELITY_PACKET_VERIFICATION_RECEIPT_REL,
        "full_fidelity_packet_verification_markdown_ref": FULL_FIDELITY_PACKET_VERIFICATION_DOC_REL,
        "full_fidelity_packet_replay_receipt_ref": FULL_FIDELITY_PACKET_REPLAY_RECEIPT_REL,
        "full_fidelity_packet_replay_markdown_ref": FULL_FIDELITY_PACKET_REPLAY_DOC_REL,
        "full_fidelity_cold_reviewer_capsule_manifest_ref": FULL_FIDELITY_CAPSULE_MANIFEST_REL,
        "full_fidelity_cold_reviewer_capsule_receipt_ref": FULL_FIDELITY_CAPSULE_RECEIPT_REL,
        "full_fidelity_cold_reviewer_capsule_markdown_ref": FULL_FIDELITY_CAPSULE_DOC_REL,
        "full_fidelity_reviewer_handoff_envelope_ref": FULL_FIDELITY_REVIEWER_HANDOFF_ENVELOPE_REL,
        "full_fidelity_reviewer_handoff_receipt_ref": FULL_FIDELITY_REVIEWER_HANDOFF_RECEIPT_REL,
        "full_fidelity_reviewer_handoff_markdown_ref": FULL_FIDELITY_REVIEWER_HANDOFF_DOC_REL,
        "lean_project_count": expected["summary"]["lean_project_count"],
        "proof_thread_count": expected["summary"]["proof_thread_count"],
        "full_fidelity_packet_status": expected_packet_receipt["status"],
        "full_fidelity_packet_verification_status": expected_verification_receipt["status"],
        "full_fidelity_packet_reviewer_acceptance_status": expected_verification_receipt["reviewer_acceptance_status"],
        "full_fidelity_packet_lake_replay_status": expected_verification_receipt["lake_replay_status"],
        "full_fidelity_packet_dependency_hydration_status": expected_replay_receipt["dependency_hydration_status"],
        "full_fidelity_packet_target_replay_status": expected_replay_receipt["target_replay_status"],
        "full_fidelity_cold_reviewer_capsule_portability_status": expected_capsule_receipt[
            "capsule_portability_status"
        ],
        "full_fidelity_cold_reviewer_capsule_replay_status": expected_capsule_receipt["capsule_replay_status"],
        "full_fidelity_reviewer_handoff_status": expected_handoff_receipt["status"],
        "full_fidelity_reviewer_handoff_authority_status": expected_handoff_receipt["handoff_authority_status"],
        "full_fidelity_reviewer_handoff_recipient_binding_status": expected_handoff_receipt[
            "recipient_binding_status"
        ],
        "full_fidelity_reviewer_handoff_delivery_status": expected_handoff_receipt["handoff_delivery_status"],
        "full_fidelity_reviewer_handoff_external_replay_status": expected_handoff_receipt[
            "external_reviewer_replay_status"
        ],
        "full_fidelity_reviewer_handoff_public_release_authority": expected_handoff_receipt[
            "public_release_authority"
        ],
        "full_fidelity_reviewer_handoff_acceptance_status": expected_handoff_receipt["reviewer_acceptance_status"],
        "source_fingerprint": expected["currentness"]["source_fingerprint"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write the generated microcosm projection.")
    parser.add_argument("--check", action="store_true", help="Check the generated projection for freshness.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON summary.")
    args = parser.parse_args(argv)
    if args.check:
        result = check_outputs()
        print(json.dumps(result, ensure_ascii=True, indent=None if args.compact else 2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    receipt = write_outputs()
    print(json.dumps(receipt, ensure_ascii=True, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
