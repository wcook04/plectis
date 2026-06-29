"""
Three-context First Correct Action release-candidate proof.

- Teleology: make the release candidate prove the product FROM THE ARTIFACT,
  not from the development checkout -- the source clone, a fresh package
  install, and the standalone export must all convert the same hero goal into
  the same complete first-action contract, and the proof must survive as a
  digest-bound, public-safe, re-verifiable packet a skeptical reviewer can
  check without trusting prose.
- Guarantee: `generate` runs the first-action encounter (hero contract,
  first-action assay, committed-demo byte-drift check) in three contexts --
  source_checkout, fresh_install (delegated to scripts/package_install_smoke.py),
  standalone_export (a real release_export then the encounter inside the
  exported tree) -- and writes release-candidate-proof.json plus a human card,
  binding every output by SHA-256 and proving both cross-context agreement on
  the selected owner and command AND that the agreed encounter matches the
  committed demonstration (the expectation policy, anchored to a digest-bound
  copy of receipts/code_lens/first_action_demo.json); `verify` re-checks
  digests, re-derives every context encounter, the agreement block, and the
  expectation policy from on-disk evidence, and never reruns the substrate.
- Reads: the source checkout, the throwaway install venv outputs, and the
  throwaway export tree. Both work trees live under a transient work root
  that is allocated OUTSIDE the source root (default: a fresh temp dir;
  --work-root to relocate) and removed after evidence copy unless
  --keep-work; a work root inside the source root is refused outright,
  because it would leak the checkout path into fresh-install evidence and
  ask release_export to write inside the source root.
- Writes: the packet directory (default .microcosm/release-candidate-proof)
  plus the transient out-of-source work root. Captured evidence refers to
  transient work locations only by the symbolic tokens <work-dir>,
  <export-out>, and <work-root> — never by absolute host paths — and the
  recorded digests bind the normalized bytes that are actually published.
- Non-goal: a passing packet does NOT authorize release, publication, provider
  calls, source mutation, domain correctness, or whole-system correctness; it
  proves the goal-shaped encounter is distribution-true and nothing more.
- Fails: generate exits 1 on a blocked packet; verify exits 1 on any
  digest/derivation/leak failure; subprocess failures are preserved as
  evidence, not hidden.
- Escalates-to: skeptic_flight_recorder (the shared helpers and the
  single-context replay packet) and tests/test_release_candidate_proof.py.

[PURPOSE]
- Teleology: Exposes `microcosm_core.release_candidate_proof` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: SCHEMA_VERSION, ENCOUNTER_SCHEMA_VERSION, VERIFICATION_SCHEMA_VERSION, PACKET_FILENAME, CARD_FILENAME, VERIFICATION_FILENAME, EXPORT_ARTIFACT_DIR_NAME, CONTEXT_IDS, COMMITTED_DEMO_RECEIPT_REL, EXPECTATION_EVIDENCE_REF, REVIEW_DOC_REL, WORK_DIR_TOKEN, EXPORT_OUT_TOKEN, WORK_ROOT_TOKEN, EXTERNAL_SIGNATURE_STATUS, PROOF_BOUNDARY, FAILURE_INTERPRETATIONS, INSTALL_EVIDENCE_SOURCES, CONTEXT_EVIDENCE, derive_context_encounter, semantic_action_key, derive_cross_context_agreement, extract_committed_expectation, derive_expectation_policy, ...
- Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results.
- Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: skeptic_flight_recorder
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from .skeptic_flight_recorder import (
    FIRST_ACTION_HERO_GOAL,
    CommandSpec,
    Runner,
    _check_row,
    _packet_payload_sha256,
    _parse_json_bytes,
    _public_subprocess_argv,
    _receipt_status,
    _scan_private_needles,
    _write_json,
    _write_text,
    default_runner,
    first_action_contract_checks,
    first_action_contract_fields,
    sha256_bytes,
    sha256_file,
    source_mutation_check,
    source_snapshot,
    subprocess_env,
    utc_now,
)


SCHEMA_VERSION = "microcosm_first_action_release_candidate_proof_v2"
ENCOUNTER_SCHEMA_VERSION = "microcosm_release_candidate_context_encounter_v1"
VERIFICATION_SCHEMA_VERSION = "microcosm_release_candidate_proof_verification_v1"
PACKET_FILENAME = "release-candidate-proof.json"
CARD_FILENAME = "release-candidate-proof-card.md"
VERIFICATION_FILENAME = "release-candidate-proof-verification.json"
EXPORT_ARTIFACT_DIR_NAME = "plectis"
CONTEXT_IDS = ("source_checkout", "fresh_install", "standalone_export")
# The committed demonstration is the artifact's PROMISE: the expectation policy
# pins the agreed encounter to this receipt, and the reviewer contract
# (RELEASE_REVIEW.md) is generated from the same source.
COMMITTED_DEMO_RECEIPT_REL = "receipts/code_lens/first_action_demo.json"
EXPECTATION_EVIDENCE_REF = "expectation/committed-demo-receipt.json"
REVIEW_DOC_REL = "RELEASE_REVIEW.md"
# Symbolic refs for the transient work locations: published evidence must
# describe WHERE a command worked without serializing the host path it worked
# in. The proof boundary normalizes captured bytes to these tokens before
# digest binding, so the packet is path-stable across hosts and the
# private-path scan stays a real leak detector instead of a TMPDIR lottery.
WORK_DIR_TOKEN = "<work-dir>"
EXPORT_OUT_TOKEN = "<export-out>"
WORK_ROOT_TOKEN = "<work-root>"
# Honest provenance posture: no public release artifact exists yet, so nothing
# here is externally signed or attested. Verification is internal consistency
# with digest-bound evidence, never third-party provenance.
EXTERNAL_SIGNATURE_STATUS = "absent_public_release_not_yet_attested"
PROOF_BOUNDARY = (
    "proves the goal-shaped first-action encounter is distribution-true "
    "across checkout, install, and export; does not authorize release, "
    "publication, provider calls, source mutation, domain correctness, "
    "or whole-system correctness. Verification proves the packet is "
    "internally consistent with its digest-bound evidence; it does not "
    "prove the run happened as recorded — rerun the generator to "
    "re-establish provenance"
)
# The reviewer-facing failure taxonomy: every named way a proof or its
# verification goes red, with what each one does and does not mean. Single
# source for the human card pointer, RELEASE_REVIEW.md, and the gate tests —
# a red result must classify, never read as a bare "bad repo".
FAILURE_INTERPRETATIONS: tuple[dict[str, str], ...] = (
    {
        "code": "context_encounter_blocked",
        "surface": "generate",
        "meaning": (
            "one distribution context did not produce the complete "
            "first-action contract; that context's failed_checks names each "
            "missed obligation and evidence_refs points at the raw bytes"
        ),
        "does_not_mean": (
            "the whole repository is broken — read the named context's "
            "evidence before concluding anything wider"
        ),
    },
    {
        "code": "cross_context_agreement_blocked",
        "surface": "generate",
        "meaning": (
            "the contexts resolved the hero goal to different owners, "
            "commands, or validators — the installed or exported product "
            "differs from the checkout"
        ),
        "does_not_mean": (
            "a tampered packet; agreement failures are honest divergence "
            "evidence, preserved for review"
        ),
    },
    {
        "code": "expectation_policy_blocked",
        "surface": "generate",
        "meaning": (
            "the agreed encounter does not match the committed demonstration "
            "(owner, command, or validator drifted, or the committed demo "
            "receipt is missing from the tree)"
        ),
        "does_not_mean": (
            "cross-context divergence — the contexts can agree with each "
            "other and still differ from what the artifact promised"
        ),
    },
    {
        "code": "private_path_leak",
        "surface": "generate_or_verify",
        "meaning": (
            "a written evidence file carries a private absolute path, so the "
            "packet refuses to present itself as public-safe"
        ),
        "does_not_mean": (
            "a security breach — the usual cause is a subprocess echoing an "
            "absolute workspace path into scanned output"
        ),
    },
    {
        "code": "source_mutation_seen",
        "surface": "generate_or_verify",
        "meaning": (
            "tracked source changed while the proof ran, so the run is not a "
            "clean witness (concurrent edits in a busy tree also trip this)"
        ),
        "does_not_mean": (
            "the proof machinery mutated the tree — rerun in a quiet window "
            "before suspecting the substrate"
        ),
    },
    {
        "code": "packet_stale",
        "surface": "verify",
        "meaning": (
            "the packet is missing, unparseable, schema-mismatched, missing "
            "referenced evidence, or asserting an authority/signature posture "
            "this lane does not grant — regenerate before reviewing"
        ),
        "does_not_mean": (
            "evidence forgery — staleness is the no-packet / wrong-version / "
            "wrong-posture class, not the tampered-bytes class"
        ),
    },
    {
        "code": "digest_mismatch",
        "surface": "verify",
        "meaning": (
            "stored claims diverge from the digest-bound evidence: tampered "
            "bytes, a forged block, or a doctored status"
        ),
        "does_not_mean": (
            "an infrastructure flake — treat the packet as untrusted and "
            "regenerate it"
        ),
    },
    {
        "code": "concurrent_churn_possible",
        "surface": "verify",
        "meaning": (
            "the mutation receipt shows tracked files changed during the "
            "run — most likely a concurrent writer, not the proof itself"
        ),
        "does_not_mean": "deliberate tampering",
    },
    {
        "code": "packet_valid",
        "surface": "verify",
        "meaning": (
            "every digest re-hashed, every derived block re-derived, no "
            "private-path leak: the packet is internally consistent with its "
            "evidence"
        ),
        "does_not_mean": (
            "release authorization, domain correctness, or proof that the "
            "run happened as recorded — rerun the generator to re-establish "
            "provenance"
        ),
    },
)
# Filenames package_install_smoke writes under <work-dir>/outputs/ — the copy
# contract between the smoke and the fresh_install evidence (test-pinned on
# both sides).
INSTALL_EVIDENCE_SOURCES = (
    ("first-action.json", "install/first-action-hero.json"),
    ("first-action-assay.txt", "install/first-action-assay.json"),
)
CONTEXT_EVIDENCE = {
    "source_checkout": {
        "hero": "checkout/first-action-hero.json",
        "assay": "checkout/first-action-assay.json",
        "demo_check": "checkout/demo-check.stdout.txt",
    },
    "fresh_install": {
        "smoke": "install/package-smoke.stdout.txt",
        "hero": "install/first-action-hero.json",
        "assay": "install/first-action-assay.json",
    },
    "standalone_export": {
        "export": "export/release-export-summary.txt",
        "hero": "export/first-action-hero.json",
        "assay": "export/first-action-assay.json",
        "demo_check": "export/demo-check.stdout.txt",
    },
}


def _path_token_redactions(
    pairs: tuple[tuple[Path, str], ...],
) -> list[tuple[str, str]]:
    """
    [ACTION]
    Build the longest-first (needle, token) rows for transient work paths.

    - Teleology: one path can surface in output under several textual
      variants (as passed, fully resolved -- e.g. /var vs /private/var on
      macOS); every variant must normalize to the SAME symbolic token or the
      packet stays host-shaped.
    - Guarantee: deterministic; covers str() and resolved POSIX forms of each
      path; longest needles first so a nested work dir wins over its parent
      work root; never emits an empty or bare-"/" needle.
    - Fails: never raises; non-strict resolve does not require existence.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows: dict[str, str] = {}
    for path, token in pairs:
        for variant in (str(path), path.resolve(strict=False).as_posix()):
            if variant and variant != "/" and variant not in rows:
                rows[variant] = token
    return sorted(rows.items(), key=lambda row: len(row[0]), reverse=True)


def _normalize_public_output(
    data: bytes, redactions: list[tuple[str, str]]
) -> tuple[bytes, list[str]]:
    """
    [ACTION]
    Replace transient-work-path variants with symbolic tokens in captured bytes.

    - Teleology: the proof-boundary normalization step -- published evidence
      may say a command worked under <work-dir>, never under which host path.
    - Guarantee: byte-level substring replacement (no decode round-trip, so
      arbitrary subprocess bytes survive untouched); returns the normalized
      bytes plus the sorted tokens actually applied; empty redactions is a
      no-op.
    - Non-goal: does NOT touch source-root or home-directory needles -- a
      product output that echoes the checkout path is a real leak the
      private-path scan must keep catching.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, declared filesystem outputs, subprocess side effects requested by the caller.
    """
    applied: set[str] = set()
    for needle, token in redactions:
        needle_bytes = needle.encode("utf-8")
        if needle_bytes and needle_bytes in data:
            data = data.replace(needle_bytes, token.encode("utf-8"))
            applied.add(token)
    return data, sorted(applied)


def _normalize_public_text(text: str, redactions: list[tuple[str, str]]) -> str:
    """
    [ACTION]
    String-side twin of _normalize_public_output for argv tokens.
    - Teleology: Implements `_normalize_public_text` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, declared filesystem outputs.
    """
    for needle, token in redactions:
        if needle in text:
            text = text.replace(needle, token)
    return text


def _run_recorded(
    *,
    command_id: str,
    display_argv: list[str],
    actual_argv: list[str],
    cwd: Path,
    env: dict[str, str],
    out_dir: Path,
    stdout_rel: str,
    timeout_seconds: int,
    runner: Runner,
    redactions: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    Run one proof command and persist a digest-bound, packet-relative receipt.

    - Teleology: the release-candidate analogue of the recorder's command
      executor -- same public-argv projection and digest binding, but every
      output ref is PACKET-RELATIVE so the packet stays portable regardless of
      which context root the command ran in.
    - Guarantee: writes stdout/stderr under `out_dir` after applying the
      transient-work-path `redactions` (so the digests bind the normalized
      bytes that are actually published), returns a record with public argv
      (projected against `cwd`, then normalized with the same redactions), a
      sha256 of the private argv, return code, duration, packet-relative
      stdout/stderr refs with sha256 digests and byte counts, json_detected,
      and -- when redactions are active -- the public_output_normalization
      token list; never serializes the private argv.
    - Fails: propagates OSError from output writes; runner timeouts arrive as
      return code 124 per default_runner.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, declared filesystem outputs, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    stderr_rel = f"{stdout_rel}.stderr.txt"
    spec = CommandSpec(
        command_id,
        display_argv,
        actual_argv,
        stdout_rel,
        stderr_rel,
        timeout_seconds=timeout_seconds,
    )
    result = runner(spec, cwd, env)
    stdout_bytes = result.stdout
    stderr_bytes = result.stderr
    public_argv = _public_subprocess_argv(actual_argv, cwd)
    applied: list[str] = []
    if redactions:
        stdout_bytes, stdout_applied = _normalize_public_output(stdout_bytes, redactions)
        stderr_bytes, stderr_applied = _normalize_public_output(stderr_bytes, redactions)
        argv_applied: set[str] = set()
        normalized_argv: list[str] = []
        for argv_token in public_argv:
            normalized = _normalize_public_text(argv_token, redactions)
            if normalized != argv_token:
                argv_applied.update(
                    token for _, token in redactions if token in normalized
                )
            normalized_argv.append(normalized)
        public_argv = normalized_argv
        applied = sorted({*stdout_applied, *stderr_applied, *argv_applied})
    stdout_path = out_dir / stdout_rel
    stderr_path = out_dir / stderr_rel
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_bytes(stdout_bytes)
    stderr_path.write_bytes(stderr_bytes)
    record = {
        "command_id": command_id,
        "argv": display_argv,
        "subprocess_argv_public": public_argv,
        "subprocess_argv_sha256": sha256_bytes("\0".join(actual_argv).encode("utf-8")),
        "return_code": result.returncode,
        "duration_seconds": result.duration_seconds,
        "stdout_ref": stdout_rel,
        "stderr_ref": stderr_rel,
        "stdout_sha256": sha256_bytes(stdout_bytes),
        "stderr_sha256": sha256_bytes(stderr_bytes),
        "stdout_bytes": len(stdout_bytes),
        "stderr_bytes": len(stderr_bytes),
        "json_detected": _parse_json_bytes(stdout_bytes) is not None,
    }
    if redactions is not None:
        record["public_output_normalization"] = applied
    return record


def derive_context_encounter(
    *,
    context_id: str,
    hero_payload: dict[str, Any] | None,
    hero_return_code: int | None,
    assay_payload: dict[str, Any] | None,
    assay_return_code: int | None,
    demo_check_return_code: int | None,
) -> dict[str, Any]:
    """
    [ACTION]
    Derive one context's first-action encounter block from its evidence.

    - Teleology: state, per distribution context, whether the hero goal became
      a complete first-action contract -- using the SAME completeness predicate
      the flight recorder uses (first_action_contract_checks), so "complete"
      cannot drift between proof surfaces.
    - Guarantee: pure deterministic projection of payloads + return codes;
      status "pass" only when every check holds; demo_check_return_code=None
      (fresh_install has no committed demo to drift-check) records the check
      as not-applicable rather than failed.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    assay = assay_payload if isinstance(assay_payload, dict) else {}
    fields = first_action_contract_fields(hero_payload)
    checks = first_action_contract_checks(hero_payload, hero_return_code)
    checks.update(
        {
            "assay_exit_zero": assay_return_code == 0,
            "assay_source_body_leak_free": assay.get("source_body_leaks") == 0,
            "assay_not_degraded": assay.get("degraded") is not True,
        }
    )
    if demo_check_return_code is not None:
        checks["committed_demo_byte_fresh"] = demo_check_return_code == 0
    return {
        "schema_version": ENCOUNTER_SCHEMA_VERSION,
        "context_id": context_id,
        "status": "pass" if all(checks.values()) else "blocked",
        # Explicitly named so a reviewer diffing checks across contexts sees
        # WHY fresh_install has no committed-demo arm rather than a hole.
        "demo_check_applicable": demo_check_return_code is not None,
        **fields,
        "assay": {
            "return_code": assay_return_code,
            "scenarios": assay.get("scenarios"),
            "source_body_leaks": assay.get("source_body_leaks"),
            "contract_completeness_pct": assay.get("contract_completeness_pct"),
            "degraded": assay.get("degraded"),
        },
        "checks": checks,
        "failed_checks": sorted(key for key, value in checks.items() if not value),
    }


# Invocation prefixes that differ legitimately across distribution contexts: a
# source checkout runs `PYTHONPATH=src python3 -m microcosm_core ...`, while an
# installed wheel runs `plectis ...`. Stripping the prefix lets cross-context
# agreement compare the semantic ACTION (capability + arguments) rather than the
# recipe syntax, so the same action invoked two legitimate ways still agrees.
_INVOCATION_PREFIXES = (
    "PYTHONPATH=src python3 -m microcosm_core",
    "PYTHONPATH=src python -m microcosm_core",
    "python3 -m microcosm_core",
    "python -m microcosm_core",
    "plectis",
    "microcosm",
)


def semantic_action_key(command: Any) -> str | None:
    """
    [ACTION]
    Project a command to its semantic action, independent of how it is invoked.

    - Teleology: distribution truth is about the ACTION the contexts select, not
      the recipe syntax. A checkout legitimately invokes
      ``PYTHONPATH=src python3 -m microcosm_core X ...``; an installed wheel
      invokes ``plectis X ...``. Both name the same action. Stripping the
      invocation prefix lets semantic agreement hold across a syntax difference
      the operator explicitly sanctioned, while a genuinely different capability
      still produces a different key.
    - Guarantee: pure and deterministic; whitespace-normalized; returns None for a
      non-string or blank command; an unrecognized prefix is returned whole
      (conservative — unknown forms compare literally and cannot accidentally
      agree across contexts).
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    if not isinstance(command, str):
        return None
    text = " ".join(command.split())
    if not text:
        return None
    for prefix in _INVOCATION_PREFIXES:
        if text == prefix:
            return ""
        if text.startswith(prefix + " "):
            return text[len(prefix) + 1 :]
    return text


def derive_cross_context_agreement(
    encounters: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """
    [ACTION]
    Prove the three contexts selected the SAME owner and semantic action.

    - Teleology: the distribution-truth core -- a contract that resolves to a
      different product installed than in the checkout is a different product;
      this block makes that divergence a named, mechanical failure instead of a
      latent surprise. It compares the SEMANTIC ACTION (capability + arguments),
      not the literal recipe, so a checkout's source-form command and an installed
      wheel's ``plectis`` command name the same action and agree, while a
      different capability still blocks.
    - Guarantee: pure projection over the per-context encounter blocks;
      status "pass" only when every expected context is present and the owner
      organ_id, the command's semantic action, and the validator command are
      each identical — and a non-empty string — across all of them (a missing
      context or empty value can never satisfy agreement by vacuity).
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """

    def identical_nonempty(values: dict[str, Any]) -> bool:
        """
        [ACTION]
        - Teleology: Implements `derive_cross_context_agreement.identical_nonempty` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        distinct = set(values.values())
        return len(distinct) == 1 and all(
            isinstance(value, str) and value for value in distinct
        )

    owner_ids: dict[str, Any] = {}
    commands: dict[str, Any] = {}
    command_actions: dict[str, Any] = {}
    validator_commands: dict[str, Any] = {}
    validator_actions: dict[str, Any] = {}
    for context_id in CONTEXT_IDS:
        encounter = encounters.get(context_id)
        row = encounter if isinstance(encounter, dict) else {}
        owner = row.get("owner") if isinstance(row.get("owner"), dict) else {}
        owner_ids[context_id] = owner.get("organ_id")
        commands[context_id] = row.get("command")
        command_actions[context_id] = semantic_action_key(row.get("command"))
        validator_commands[context_id] = row.get("validator_command")
        validator_actions[context_id] = semantic_action_key(
            row.get("validator_command")
        )
    owner_identical = identical_nonempty(owner_ids)
    # Distribution truth compares the semantic ACTION across contexts, not the
    # literal recipe: source-form and installed `plectis` forms of the same action
    # (command and validator) must agree, while a different capability still blocks.
    command_identical = identical_nonempty(command_actions)
    validator_identical = identical_nonempty(validator_actions)
    return {
        "status": (
            "pass"
            if owner_identical and command_identical and validator_identical
            else "blocked"
        ),
        "owner_organ_id_identical": owner_identical,
        "command_identical": command_identical,
        "validator_command_identical": validator_identical,
        "owner_organ_ids": owner_ids,
        "commands": commands,
        "command_semantic_actions": command_actions,
        "validator_commands": validator_commands,
        "validator_semantic_actions": validator_actions,
    }


def extract_committed_expectation(
    receipt_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    [ACTION]
    Extract the hero goal's expected encounter from the committed demo receipt.

    - Teleology: the committed demonstration (FIRST_ACTION.md's receipt) is
      what the artifact PROMISES a reviewer; this projection turns its hero row
      into the expectation the proof compares every context against.
    - Guarantee: pure and deterministic; returns the fixed expectation row
      (present flag, hero goal, expected owner organ_id, expected command,
      expected validator command); a missing/malformed receipt degrades to an
      absent expectation, never an exception. The validator preference order
      (validator_command, else runnable_validator) mirrors
      first_action_contract_fields so both sides of the comparison project the
      same field.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    contracts = (
        receipt_payload.get("contracts") if isinstance(receipt_payload, dict) else None
    )
    hero: dict[str, Any] | None = None
    if isinstance(contracts, list):
        for row in contracts:
            if isinstance(row, dict) and row.get("goal") == FIRST_ACTION_HERO_GOAL:
                hero = row
                break
    owner = hero.get("owner") if hero and isinstance(hero.get("owner"), dict) else {}
    action = (
        hero.get("first_action")
        if hero and isinstance(hero.get("first_action"), dict)
        else {}
    )
    proof_path = (
        hero.get("proof_path")
        if hero and isinstance(hero.get("proof_path"), dict)
        else {}
    )
    return {
        "committed_demonstration_present": hero is not None,
        "hero_goal": FIRST_ACTION_HERO_GOAL,
        "expected_owner_organ_id": owner.get("organ_id"),
        "expected_command": action.get("command"),
        "expected_validator_command": proof_path.get("validator_command")
        or proof_path.get("runnable_validator"),
    }


def derive_expectation_policy(
    expectation: dict[str, Any],
    agreement: dict[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    Prove the agreed encounter is the encounter the artifact promised.

    - Teleology: cross-context agreement alone is satisfiable by three contexts
      agreeing on the WRONG product; this block pins the observed owner,
      command, and validator in every context to the committed demonstration,
      so "matches what the artifact sells" is a named mechanical check instead
      of an implicit hope.
    - Guarantee: pure projection over the expectation row plus the agreement
      block's per-context value maps; each *_matches check requires a
      non-empty expected string and every expected context's observed value
      equal to it (a missing context or empty expectation can never satisfy a
      check by vacuity); status "pass" only when the committed demonstration
      was present and every check holds.
    - Fails: never raises.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """

    def all_match(expected: Any, observed: Any) -> bool:
        """
        [ACTION]
        - Teleology: Implements `derive_expectation_policy.all_match` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        rows = observed if isinstance(observed, dict) else {}
        return (
            isinstance(expected, str)
            and bool(expected)
            and set(rows) == set(CONTEXT_IDS)
            and all(value == expected for value in rows.values())
        )

    checks = {
        "committed_demonstration_present": expectation.get(
            "committed_demonstration_present"
        )
        is True,
        "owner_matches_committed_demonstration": all_match(
            expectation.get("expected_owner_organ_id"),
            agreement.get("owner_organ_ids"),
        ),
        "command_matches_committed_demonstration": all_match(
            semantic_action_key(expectation.get("expected_command")),
            agreement.get("command_semantic_actions"),
        ),
        "validator_matches_committed_demonstration": all_match(
            semantic_action_key(expectation.get("expected_validator_command")),
            agreement.get("validator_semantic_actions"),
        ),
    }
    return {
        "status": "pass" if all(checks.values()) else "blocked",
        "source_ref": COMMITTED_DEMO_RECEIPT_REL,
        "evidence_ref": EXPECTATION_EVIDENCE_REF,
        **expectation,
        "checks": checks,
        "failed_checks": sorted(key for key, value in checks.items() if not value),
    }


def _read_json_evidence(out_dir: Path, relpath: str) -> dict[str, Any] | None:
    """
    [ACTION]
    Best-effort load one packet-relative evidence file as a JSON object.
    - Teleology: Implements `_read_json_evidence` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs.
    - Writes: return values.
    """
    try:
        data = (out_dir / relpath).read_bytes()
    except OSError:
        return None
    return _parse_json_bytes(data)


def _context_encounter_from_disk(
    context_id: str,
    records: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    """
    [ACTION]
    Re-derive one context's encounter block from packet-relative evidence.

    Shared by generate (first derivation) and verify (re-derivation), so the
    stored block is provably a projection of the digest-bound files plus the
    recorded return codes.
    - Teleology: Implements `_context_encounter_from_disk` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    by_id = {
        row["command_id"]: row
        for row in records
        if isinstance(row, dict) and isinstance(row.get("command_id"), str)
    }

    def return_code(command_id: str) -> int | None:
        """
        [ACTION]
        - Teleology: Implements `_context_encounter_from_disk.return_code` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        value = by_id.get(command_id, {}).get("return_code")
        return value if isinstance(value, int) else None

    evidence = CONTEXT_EVIDENCE[context_id]
    hero_payload = _read_json_evidence(out_dir, evidence["hero"])
    assay_payload = _read_json_evidence(out_dir, evidence["assay"])
    if context_id == "fresh_install":
        # The install context delegates to package_install_smoke, which runs
        # hero + assay inside the fresh venv and fails the whole smoke on any
        # arm; its single return code governs both.
        smoke_rc = return_code(f"{context_id}.package_smoke")
        hero_rc = smoke_rc
        assay_rc = smoke_rc
        demo_rc: int | None = None
    else:
        hero_rc = return_code(f"{context_id}.first_action_hero")
        assay_rc = return_code(f"{context_id}.first_action_assay")
        demo_rc = return_code(f"{context_id}.demo_check")
    encounter = derive_context_encounter(
        context_id=context_id,
        hero_payload=hero_payload,
        hero_return_code=hero_rc,
        assay_payload=assay_payload,
        assay_return_code=assay_rc,
        demo_check_return_code=demo_rc,
    )
    # Where each claim's bytes live, so a blocked context points the reviewer
    # at its raw evidence instead of leaving only failed booleans.
    encounter["evidence_refs"] = dict(CONTEXT_EVIDENCE[context_id])
    return encounter


def _encounter_argvs(python_executable: str) -> dict[str, list[str]]:
    """
    [ACTION]
    The per-context encounter commands, shared by checkout and export contexts.
    - Teleology: Implements `_encounter_argvs` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    return {
        "hero": [
            python_executable,
            "-m",
            "microcosm_core",
            "comprehend",
            "--first-action",
            FIRST_ACTION_HERO_GOAL,
        ],
        "assay": [
            python_executable,
            "-m",
            "microcosm_core",
            "comprehension-assay",
            "--first-action",
        ],
        "demo_check": [
            python_executable,
            "scripts/build_first_action_demo.py",
            "--check",
        ],
    }


def _run_encounter_context(
    *,
    context_id: str,
    context_root: Path,
    out_dir: Path,
    python_executable: str,
    runner: Runner,
    redactions: list[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    Run hero + assay + demo-check in one context root, recording evidence.
    - Teleology: Implements `_run_encounter_context` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    env, _ = subprocess_env(context_root)
    argvs = _encounter_argvs(python_executable)
    evidence = CONTEXT_EVIDENCE[context_id]
    records = []
    for step, display_head in (
        ("hero", ["plectis", "comprehend", "--first-action", FIRST_ACTION_HERO_GOAL]),
        ("assay", ["plectis", "comprehension-assay", "--first-action"]),
        (
            "demo_check",
            ["python", "scripts/build_first_action_demo.py", "--check"],
        ),
    ):
        if step not in evidence:
            continue
        records.append(
            _run_recorded(
                command_id=f"{context_id}.first_action_{step}"
                if step in ("hero", "assay")
                else f"{context_id}.{step}",
                display_argv=display_head,
                actual_argv=argvs[step],
                cwd=context_root,
                env=env,
                out_dir=out_dir,
                stdout_rel=evidence[step],
                timeout_seconds=300,
                runner=runner,
                redactions=redactions,
            )
        )
    return records


def build_release_candidate_proof(
    *,
    root: Path,
    out_dir: Path,
    python_executable: str = sys.executable,
    runner: Runner = default_runner,
    keep_work: bool = False,
    work_root: Path | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    Run the three-context first-action encounter and write the proof packet + card.

    - Teleology: the release-candidate proof builder -- prove that a cold
      reviewer's hero goal resolves to the SAME complete, graph-backed first
      action in the source checkout, a fresh pip install, and the standalone
      export, with every claim derived from digest-bound evidence.
    - Guarantee: writes release-candidate-proof.json and the human card under
      `out_dir`; packet status is "pass" only when all three context
      encounters pass, cross-context agreement holds, no private path leaks
      into any written file, and the checkout's tracked source is unchanged
      by the run; failures are preserved as evidence with named checks.
    - Writes: `out_dir` (evidence + packet + card) plus a transient work root
      holding the install venv and export tree. The work root defaults to a
      fresh temp dir, must live OUTSIDE the source root, and is removed
      after evidence copy unless keep_work (a caller-supplied work_root keeps
      its shell dir; only the install/export subtrees are removed). Captured
      evidence and recorded argv refer to the work locations only by the
      symbolic tokens <work-dir>, <export-out>, <work-root>.
    - Non-goal: does NOT authorize release/publication/provider calls/source
      mutation, and does not assert domain or whole-system correctness. The
      normalization never covers the source root or home directory -- a
      product output that echoes the checkout path must still block the scan.
    - Fails: raises ValueError when the resolved work root sits inside the
      source root (an in-tree work root would leak the checkout path into
      fresh-install evidence and ask release_export to write inside the
      source root) or when it equals/contains the packet out dir (the scan
      would exclude the whole publishable surface and pass vacuously);
      propagates OSError on packet writes; probe failures land in the
      packet, not as exceptions.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results.
    """
    root = root.expanduser().resolve(strict=False)
    out_dir = out_dir.expanduser()
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    allocated_work_root = work_root is None
    work_base = (
        Path(tempfile.mkdtemp(prefix="microcosm-release-candidate-proof-work-"))
        if work_root is None
        else work_root.expanduser()
    )
    work_base = work_base.resolve(strict=False)
    out_dir_resolved = out_dir.resolve(strict=False)
    refusal: str | None = None
    if work_base == root or root in work_base.parents:
        refusal = (
            "release-candidate proof work root must live outside the source "
            "root: an in-tree work root leaks the checkout path into "
            "fresh-install evidence and asks release_export to write inside "
            "the source root (pass --work-root to relocate it)"
        )
    elif work_base == out_dir_resolved or work_base in out_dir_resolved.parents:
        refusal = (
            "release-candidate proof work root must not equal or contain the "
            "packet out dir: the scan that proves the packet public-safe "
            "excludes the work tree, so this layout would exclude the entire "
            "publishable surface and pass vacuously"
        )
    if refusal is not None:
        if allocated_work_root:
            shutil.rmtree(work_base, ignore_errors=True)
        raise ValueError(refusal)
    work_base.mkdir(parents=True, exist_ok=True)
    # Every evidence file in the packet must belong to THIS run: stale bytes
    # from a prior run would otherwise feed encounters on degraded runs, and a
    # stale receipt would skew the generate-side scan relative to verify.
    for stale_sub in ("checkout", "install", "export", "expectation", "work"):
        shutil.rmtree(out_dir / stale_sub, ignore_errors=True)
    for stale_file in (PACKET_FILENAME, CARD_FILENAME, VERIFICATION_FILENAME):
        (out_dir / stale_file).unlink(missing_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or utc_now()
    before_snapshot = source_snapshot(root)

    records: list[dict[str, Any]] = []
    work_notes: list[str] = []
    copied_evidence: list[dict[str, Any]] = []

    # The expectation snapshot comes FIRST: the committed demonstration is
    # copied into the packet as digest-bound evidence before any context runs,
    # so the promise the encounters are compared against provably predates the
    # encounters themselves.
    committed_demo_payload: dict[str, Any] | None = None
    committed_demo_source = root / COMMITTED_DEMO_RECEIPT_REL
    expectation_target = out_dir / EXPECTATION_EVIDENCE_REF
    if committed_demo_source.is_file():
        expectation_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(committed_demo_source, expectation_target)
        copied_evidence.append(
            {
                "source": COMMITTED_DEMO_RECEIPT_REL,
                "ref": EXPECTATION_EVIDENCE_REF,
                "sha256": sha256_file(expectation_target),
                "bytes": expectation_target.stat().st_size,
            }
        )
        committed_demo_payload = _parse_json_bytes(expectation_target.read_bytes())
    else:
        work_notes.append(
            f"missing committed demonstration: {COMMITTED_DEMO_RECEIPT_REL}"
        )

    # Context 1: the source checkout.
    records.extend(
        _run_encounter_context(
            context_id="source_checkout",
            context_root=root,
            out_dir=out_dir,
            python_executable=python_executable,
            runner=runner,
        )
    )

    # Context 2: fresh install -- delegated to the package smoke, which builds
    # a venv, installs the package, and runs the hero contract + assay from
    # the installed console. Both work trees live under the out-of-source
    # work root; their host paths reach published evidence only as tokens.
    install_work = work_base / "install"
    export_work = work_base / "export"
    work_redactions = _path_token_redactions(
        (
            (install_work, WORK_DIR_TOKEN),
            (export_work, EXPORT_OUT_TOKEN),
            (work_base, WORK_ROOT_TOKEN),
        )
    )
    env, provider_policy = subprocess_env(root)
    # The smoke must prove the INSTALLED copy: a dev-tree PYTHONPATH reaching
    # the venv console would shadow site-packages and hollow out the context.
    smoke_env = dict(env)
    smoke_env.pop("PYTHONPATH", None)
    records.append(
        _run_recorded(
            command_id="fresh_install.package_smoke",
            display_argv=[
                "python",
                "scripts/package_install_smoke.py",
                "--source-root",
                ".",
                "--work-dir",
                "<work-dir>",
            ],
            actual_argv=[
                python_executable,
                "scripts/package_install_smoke.py",
                "--source-root",
                ".",
                "--work-dir",
                str(install_work),
                "--python",
                python_executable,
            ],
            cwd=root,
            env=smoke_env,
            out_dir=out_dir,
            stdout_rel=CONTEXT_EVIDENCE["fresh_install"]["smoke"],
            timeout_seconds=900,
            runner=runner,
            redactions=work_redactions,
        )
    )
    for source_name, target_rel in INSTALL_EVIDENCE_SOURCES:
        source_path = install_work / "outputs" / source_name
        target_path = out_dir / target_rel
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_file():
            shutil.copyfile(source_path, target_path)
            copied_evidence.append(
                {
                    "source": f"outputs/{source_name}",
                    "ref": target_rel,
                    "sha256": sha256_file(target_path),
                    "bytes": target_path.stat().st_size,
                }
            )
        else:
            work_notes.append(f"missing install evidence: outputs/{source_name}")

    # Context 3: the standalone export -- a real release_export, then the
    # encounter inside the exported artifact tree.
    export_env = dict(env)
    # The export builder writes its own receipts inside the new tree; do not
    # carry the probe-side receipt-write suppression into it.
    export_env.pop("MICROCOSM_RUNTIME_RECEIPT_WRITES", None)
    export_env.pop("MICROCOSM_RECEIPT_WRITES", None)
    records.append(
        _run_recorded(
            command_id="standalone_export.release_export",
            display_argv=[
                "python",
                "-m",
                "microcosm_core.release_export",
                "--root",
                ".",
                "--out",
                "<export-out>",
                "--force",
                "--summary",
            ],
            actual_argv=[
                python_executable,
                "-m",
                "microcosm_core.release_export",
                "--root",
                ".",
                "--out",
                str(export_work),
                "--force",
                "--summary",
            ],
            cwd=root,
            env=export_env,
            out_dir=out_dir,
            stdout_rel=CONTEXT_EVIDENCE["standalone_export"]["export"],
            timeout_seconds=900,
            runner=runner,
            redactions=work_redactions,
        )
    )
    exported_root = export_work / EXPORT_ARTIFACT_DIR_NAME
    if exported_root.is_dir():
        records.extend(
            _run_encounter_context(
                context_id="standalone_export",
                context_root=exported_root,
                out_dir=out_dir,
                python_executable=python_executable,
                runner=runner,
                redactions=work_redactions,
            )
        )
    else:
        work_notes.append("export tree missing: standalone_export encounter not run")

    if keep_work:
        # Operator debugging surface only: the kept location goes to stderr,
        # never into the packet, so published evidence stays token-normalized.
        print(
            f"release-candidate proof: kept transient work root: {work_base}",
            file=sys.stderr,
        )
    else:
        shutil.rmtree(install_work, ignore_errors=True)
        shutil.rmtree(export_work, ignore_errors=True)
        if allocated_work_root:
            shutil.rmtree(work_base, ignore_errors=True)

    encounters = {
        context_id: _context_encounter_from_disk(context_id, records, out_dir)
        for context_id in CONTEXT_IDS
    }
    agreement = derive_cross_context_agreement(encounters)
    expectation_policy = derive_expectation_policy(
        extract_committed_expectation(committed_demo_payload), agreement
    )
    after_snapshot = source_snapshot(root)
    mutation = source_mutation_check(before_snapshot, after_snapshot)

    def publishable_paths() -> list[Path]:
        # The work trees (venv, export) are transient workspace, not published
        # evidence — they live outside the source root by contract, and under
        # an explicit --work-root beneath out_dir they would otherwise drag
        # thousands of absolute-path-bearing files (shebangs, pip RECORD)
        # into the scan and block an otherwise-passing packet.
        """
        [ACTION]
        - Teleology: Implements `build_release_candidate_proof.publishable_paths` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
        - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
        - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
        - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
        - Reads: call arguments, module constants, imported helpers.
        - Writes: return values.
        """
        return [
            path
            for path in out_dir.rglob("*")
            if path.is_file()
            and not path.name.endswith(".tmp")
            and work_base not in path.parents
        ]

    private_scan = _scan_private_needles(publishable_paths(), root)

    contexts_pass = all(row["status"] == "pass" for row in encounters.values())
    packet_path = out_dir / PACKET_FILENAME
    card_path = out_dir / CARD_FILENAME
    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": (
            "pass"
            if contexts_pass
            and agreement["status"] == "pass"
            and expectation_policy["status"] == "pass"
            and private_scan["status"] == "pass"
            and mutation["status"] == "pass"
            else "blocked"
        ),
        "generated_at": generated,
        "hero_goal": FIRST_ACTION_HERO_GOAL,
        "packet_ref": PACKET_FILENAME,
        "human_card_ref": CARD_FILENAME,
        "reviewer_contract_ref": REVIEW_DOC_REL,
        "external_signature_status": EXTERNAL_SIGNATURE_STATUS,
        "authority_and_omission_policy": {
            "release_authorized": False,
            "provider_calls_authorized": False,
            "source_mutation_authorized": False,
            "selected_fields_only_in_packet": True,
            "work_trees_removed_after_evidence_copy": not keep_work,
        },
        "contexts": {
            context_id: {
                "status": encounters[context_id]["status"],
                "encounter": encounters[context_id],
            }
            for context_id in CONTEXT_IDS
        },
        "cross_context_agreement": agreement,
        "expectation_policy": expectation_policy,
        "integrity": {
            "source_mutation_check": mutation,
            "private_path_scan": private_scan,
            "provider_env_policy": provider_policy,
            "copied_evidence": copied_evidence,
            "work_notes": work_notes,
            # The hermetic-regeneration contract: transient work never sits
            # inside the source root (enforced fail-closed at allocation) and
            # reaches published evidence only as these symbolic tokens.
            "transient_work_root_policy": {
                "outside_source_root": True,
                "removed_after_evidence_copy": not keep_work,
                "public_tokens": [
                    WORK_DIR_TOKEN,
                    EXPORT_OUT_TOKEN,
                    WORK_ROOT_TOKEN,
                ],
            },
        },
        "commands": records,
        "proof_boundary": PROOF_BOUNDARY,
    }
    _write_json(packet_path, packet)
    card = _human_card(packet)
    _write_text(card_path, card)
    packet["integrity"]["private_path_scan"] = _scan_private_needles(
        publishable_paths(), root
    )
    packet["status"] = (
        "pass"
        if contexts_pass
        and agreement["status"] == "pass"
        and expectation_policy["status"] == "pass"
        and packet["integrity"]["private_path_scan"]["status"] == "pass"
        and mutation["status"] == "pass"
        else "blocked"
    )
    card = _human_card(packet)
    _write_text(card_path, card)
    packet["human_card_sha256"] = sha256_file(card_path)
    packet["packet_payload_sha256"] = _packet_payload_sha256(packet)
    _write_json(packet_path, packet)
    return packet


def _human_card(packet: dict[str, Any]) -> str:
    """
    [ACTION]
    Render the proof packet into the human release-candidate card (a projection, not authority).
    - Teleology: Implements `_human_card` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    agreement = packet["cross_context_agreement"]
    expectation = packet.get("expectation_policy") or {}
    integrity = packet["integrity"]
    expectation_line = f"- Expectation policy: `{expectation.get('status')}`"
    failed_expectation = expectation.get("failed_checks") or []
    if failed_expectation:
        expectation_line += (
            " (failed: " + ", ".join(f"`{name}`" for name in failed_expectation) + ")"
        )
    else:
        expectation_line += (
            f" (matches the committed demonstration `{expectation.get('source_ref')}`)"
        )
    lines = [
        "# Microcosm First Correct Action — Release Candidate Proof",
        "",
        f"- Packet status: `{packet['status']}`",
        f"- Hero goal: `{packet['hero_goal']}`",
        expectation_line,
        (
            "- Cross-context agreement: "
            f"`{agreement['status']}` (owner identical: "
            f"`{agreement['owner_organ_id_identical']}`, command identical: "
            f"`{agreement['command_identical']}`)"
        ),
        (
            "- Source files mutated by this proof run: "
            f"`{integrity['source_mutation_check']['source_files_mutated']}`"
        ),
        (
            "- Private path hits in written evidence: "
            f"`{integrity['private_path_scan']['private_path_hit_count']}`"
        ),
        f"- External signature status: `{packet.get('external_signature_status')}`",
        "",
        "## Claim under review",
        "",
        (
            "This packet claims exactly one thing: in the source checkout, a "
            "fresh package install, and the standalone export, the hero goal "
            "resolved to the complete first-action contract the committed "
            "demonstration promises — same owner, same first command, same "
            "validator. Nothing else is claimed."
        ),
        "",
        f"- Expected owner: `{expectation.get('expected_owner_organ_id')}`",
        f"- Expected command: `{expectation.get('expected_command')}`",
        f"- Expected validator: `{expectation.get('expected_validator_command')}`",
        f"- Promise source: `{expectation.get('source_ref')}` "
        f"(copied into this packet at `{expectation.get('evidence_ref')}`)",
        "",
        "## Contexts",
        "",
    ]
    for context_id in CONTEXT_IDS:
        row = packet["contexts"][context_id]
        encounter = row["encounter"]
        owner = encounter.get("owner") or {}
        failed = encounter.get("failed_checks") or []
        lines += [
            f"### `{context_id}` — `{row['status']}`",
            "",
            f"- Owner: `{owner.get('organ_id')}`",
            f"- Command: `{encounter.get('command')}`",
            f"- Validator: `{encounter.get('validator_command')}`",
            (
                f"- Assay: `{(encounter.get('assay') or {}).get('scenarios')}` scenarios, "
                f"`{(encounter.get('assay') or {}).get('source_body_leaks')}` source-body leaks"
            ),
            (
                "- Failed checks: " + ", ".join(f"`{name}`" for name in failed)
                if failed
                else "- Failed checks: none"
            ),
            "",
        ]
    notes = integrity.get("work_notes") or []
    if notes:
        lines += ["## Notes", ""]
        lines += [f"- {note}" for note in notes]
        lines += [""]
    lines += [
        "## Verify this packet",
        "",
        (
            "- `make release-candidate-proof-verify` (or `PYTHONPATH=src "
            "python3 scripts/release_candidate_proof.py verify <packet-dir> "
            "--root .`) re-derives every claim above from the digest-bound "
            "evidence without rerunning the substrate."
        ),
        (
            "- A reviewer who distrusts this packet should rerun "
            "`make release-candidate-proof` and compare."
        ),
        (
            f"- The full reviewer contract — claim, expectation policy, and "
            f"failure interpretations — is committed as "
            f"`{packet.get('reviewer_contract_ref')}`."
        ),
        "",
        "## Boundary",
        "",
        f"- {packet['proof_boundary']}",
        "",
    ]
    return "\n".join(lines)


def verify_release_candidate_proof(
    *,
    packet_dir: Path,
    root: Path,
    write_receipt: bool = True,
    receipt_path: Path | None = None,
    verified_at: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    Verify an existing release-candidate proof packet WITHOUT rerunning anything.

    - Teleology: let a reviewer trust a previously generated three-context
      proof by re-checking digests, re-deriving every context encounter and
      the agreement block from on-disk evidence, and re-scanning for private
      paths -- the same no-rerun posture as the flight-recorder verifier.
    - Guarantee: returns a receipt whose status is "packet_valid" only when
      the packet parses, its self-digest matches, the card digest matches,
      every referenced output re-hashes to its recorded digest, the stored
      encounters and agreement equal their re-derivations, and no scanned
      file carries a private needle.
    - Fails: never raises on missing/corrupt packets (returns a blocked
      receipt); receipt writes may raise OSError.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Reads: call arguments, module constants, imported helpers, declared filesystem inputs, declared subprocess results.
    - Writes: return values, stdout/stderr or CLI result text, subprocess side effects requested by the caller.
    """
    root = root.expanduser().resolve(strict=False)
    packet_dir = packet_dir.expanduser()
    if not packet_dir.is_absolute():
        packet_dir = root / packet_dir
    packet_dir = packet_dir.resolve(strict=False)
    packet_path = packet_dir / PACKET_FILENAME
    receipt_path = receipt_path or packet_dir / VERIFICATION_FILENAME

    checks: list[dict[str, Any]] = []
    statuses: set[str] = set()
    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        packet = None
    if not isinstance(packet, dict):
        receipt = {
            "schema_version": VERIFICATION_SCHEMA_VERSION,
            "status": "packet_stale",
            "statuses": ["packet_stale"],
            "verified_at": verified_at or utc_now(),
            "no_substrate_rerun": True,
            "checks": [
                _check_row("packet_json", "blocked", reason="packet missing or unreadable")
            ],
        }
        if write_receipt:
            _write_json(receipt_path, receipt)
        return receipt

    if packet.get("schema_version") == SCHEMA_VERSION:
        checks.append(_check_row("packet_schema", "pass"))
    else:
        statuses.add("packet_stale")
        checks.append(
            _check_row(
                "packet_schema",
                "blocked",
                observed_schema_version=packet.get("schema_version"),
            )
        )

    expected_digest = packet.get("packet_payload_sha256")
    actual_digest = _packet_payload_sha256(packet)
    if isinstance(expected_digest, str) and expected_digest == actual_digest:
        checks.append(_check_row("packet_payload_sha256", "pass"))
    else:
        statuses.add("digest_mismatch" if isinstance(expected_digest, str) else "packet_stale")
        checks.append(_check_row("packet_payload_sha256", "blocked"))

    card_path = packet_dir / str(packet.get("human_card_ref") or CARD_FILENAME)
    expected_card = packet.get("human_card_sha256")
    if not isinstance(expected_card, str) or not card_path.is_file():
        statuses.add("packet_stale")
        checks.append(
            _check_row(
                "human_card_sha256",
                "blocked",
                reason="card_missing_or_digest_absent",
            )
        )
    elif sha256_file(card_path) != expected_card:
        statuses.add("digest_mismatch")
        checks.append(_check_row("human_card_sha256", "blocked"))
    else:
        checks.append(_check_row("human_card_sha256", "pass"))

    records = packet.get("commands")
    records = [row for row in records if isinstance(row, dict)] if isinstance(records, list) else []
    evidence_paths: list[Path] = []
    digest_mismatches = 0
    missing_outputs = 0
    for record in records:
        for stream in ("stdout", "stderr"):
            ref = record.get(f"{stream}_ref")
            digest = record.get(f"{stream}_sha256")
            if not isinstance(ref, str) or not isinstance(digest, str):
                statuses.add("packet_stale")
                missing_outputs += 1
                continue
            path = packet_dir / ref
            if not path.is_file():
                statuses.add("packet_stale")
                missing_outputs += 1
                continue
            evidence_paths.append(path)
            if sha256_file(path) != digest:
                statuses.add("digest_mismatch")
                digest_mismatches += 1
    checks.append(
        _check_row(
            "command_output_sha256",
            "pass" if not digest_mismatches and not missing_outputs else "blocked",
            raw_output_count=len(evidence_paths),
            digest_mismatch_count=digest_mismatches,
            missing_output_count=missing_outputs,
        )
    )

    # Copied install evidence is not command stdout, so it carries its own
    # digest rows — re-hash them or the fresh_install re-derivation would
    # trust unverified bytes.
    integrity_block = packet.get("integrity")
    integrity_block = integrity_block if isinstance(integrity_block, dict) else {}
    copied_rows = integrity_block.get("copied_evidence")
    copied_rows = copied_rows if isinstance(copied_rows, list) else []
    copied_mismatches = 0
    copied_missing = 0
    for row in copied_rows:
        if not isinstance(row, dict):
            copied_missing += 1
            continue
        ref = row.get("ref")
        digest = row.get("sha256")
        if not isinstance(ref, str) or not isinstance(digest, str):
            copied_missing += 1
            continue
        path = packet_dir / ref
        if not path.is_file():
            copied_missing += 1
            continue
        evidence_paths.append(path)
        if sha256_file(path) != digest:
            copied_mismatches += 1
    if copied_missing:
        statuses.add("packet_stale")
    if copied_mismatches:
        statuses.add("digest_mismatch")
    checks.append(
        _check_row(
            "copied_evidence_sha256",
            "pass" if not copied_mismatches and not copied_missing else "blocked",
            copied_evidence_count=len(copied_rows),
            digest_mismatch_count=copied_mismatches,
            missing_count=copied_missing,
        )
    )

    contexts = packet.get("contexts")
    contexts = contexts if isinstance(contexts, dict) else {}
    rederived: dict[str, dict[str, Any]] = {}
    encounter_divergences: list[str] = []
    for context_id in CONTEXT_IDS:
        derived = _context_encounter_from_disk(context_id, records, packet_dir)
        rederived[context_id] = derived
        stored_row = contexts.get(context_id)
        stored = (
            stored_row.get("encounter")
            if isinstance(stored_row, dict) and isinstance(stored_row.get("encounter"), dict)
            else None
        )
        if stored != derived:
            encounter_divergences.append(context_id)
    if encounter_divergences:
        statuses.add("digest_mismatch")
        checks.append(
            _check_row(
                "context_encounters_rederived",
                "blocked",
                divergent_contexts=encounter_divergences,
            )
        )
    else:
        checks.append(_check_row("context_encounters_rederived", "pass"))

    derived_agreement = derive_cross_context_agreement(rederived)
    if packet.get("cross_context_agreement") != derived_agreement:
        statuses.add("digest_mismatch")
        checks.append(_check_row("cross_context_agreement_rederived", "blocked"))
    else:
        checks.append(_check_row("cross_context_agreement_rederived", "pass"))

    # The expectation policy must be a projection of the digest-bound copy of
    # the committed demonstration plus the re-derived agreement — a forged
    # "matches the promise" claim is refused even with a recomputed self-digest.
    derived_expectation = derive_expectation_policy(
        extract_committed_expectation(
            _read_json_evidence(packet_dir, EXPECTATION_EVIDENCE_REF)
        ),
        derived_agreement,
    )
    if packet.get("expectation_policy") != derived_expectation:
        statuses.add("digest_mismatch")
        checks.append(_check_row("expectation_policy_rederived", "blocked"))
    else:
        checks.append(_check_row("expectation_policy_rederived", "pass"))

    scan_paths = [packet_path, *([card_path] if card_path.is_file() else []), *evidence_paths]
    private_scan = _scan_private_needles(scan_paths, root)
    if private_scan["status"] != "pass":
        statuses.add("private_path_leak")
    checks.append(
        _check_row(
            "private_path_leakage",
            private_scan["status"],
            private_path_hit_count=private_scan["private_path_hit_count"],
        )
    )

    # The stored no-mutation custody claim must be present and clean — the
    # same posture as the flight-recorder verifier.
    mutation = integrity_block.get("source_mutation_check")
    mutation = mutation if isinstance(mutation, dict) else {}
    mutation_clean = (
        mutation.get("status") == "pass"
        and mutation.get("source_files_mutated") is False
    )
    if mutation_clean:
        checks.append(_check_row("source_mutation_receipt", "pass"))
    else:
        statuses.add("source_mutation_seen" if mutation else "packet_stale")
        if any(
            mutation.get(key, 0)
            for key in ("changed_count", "added_count", "removed_count")
        ):
            statuses.add("concurrent_churn_possible")
        checks.append(
            _check_row(
                "source_mutation_receipt",
                "blocked",
                mutation_status=mutation.get("status"),
                source_files_mutated=mutation.get("source_files_mutated"),
            )
        )

    # The packet must not have silently gained authority.
    policy = packet.get("authority_and_omission_policy")
    policy = policy if isinstance(policy, dict) else {}
    provider_policy = integrity_block.get("provider_env_policy")
    provider_policy = provider_policy if isinstance(provider_policy, dict) else {}
    policy_ok = (
        all(
            policy.get(key) is False
            for key in (
                "release_authorized",
                "provider_calls_authorized",
                "source_mutation_authorized",
            )
        )
        and (
            provider_policy.get("provider_credential_env_keys_available_to_subprocess")
            is False
        )
        # A packet asserting any other signature posture is claiming external
        # provenance this lane does not have.
        and packet.get("external_signature_status") == EXTERNAL_SIGNATURE_STATUS
    )
    if policy_ok:
        checks.append(_check_row("authority_policy_preserved", "pass"))
    else:
        statuses.add("packet_stale")
        checks.append(_check_row("authority_policy_preserved", "blocked"))

    # Top-level status must be a projection of the parts, not an assertion: a
    # doctored "pass" over blocked components is refused even with a
    # recomputed self-digest.
    expected_status = (
        "pass"
        if all(row["status"] == "pass" for row in rederived.values())
        and derived_agreement["status"] == "pass"
        and derived_expectation["status"] == "pass"
        and private_scan["status"] == "pass"
        and mutation_clean
        and not copied_missing
        and not copied_mismatches
        else "blocked"
    )
    if packet.get("status") == expected_status:
        checks.append(
            _check_row("packet_status_rederived", "pass", packet_status=expected_status)
        )
    else:
        statuses.add("digest_mismatch")
        checks.append(
            _check_row(
                "packet_status_rederived",
                "blocked",
                stored_status=packet.get("status"),
                expected_status=expected_status,
            )
        )

    receipt: dict[str, Any] = {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": _receipt_status(statuses),
        "statuses": sorted(statuses) if statuses else ["packet_valid"],
        "verified_at": verified_at or utc_now(),
        "no_substrate_rerun": True,
        "provider_calls_authorized": False,
        "packet_status": packet.get("status"),
        "cross_context_agreement_status": derived_agreement["status"],
        "expectation_policy_status": derived_expectation["status"],
        "private_path_scan": private_scan,
        "checks": checks,
    }
    if write_receipt:
        _write_json(receipt_path, receipt)
        final_scan = _scan_private_needles([*scan_paths, receipt_path], root)
        if final_scan["status"] != "pass":
            statuses.add("private_path_leak")
            receipt["status"] = _receipt_status(statuses)
            receipt["statuses"] = sorted(statuses)
        receipt["verifier_integrity"] = {
            "receipt_written": True,
            "final_private_path_scan": final_scan,
        }
        _write_json(receipt_path, receipt)
    else:
        receipt["verifier_integrity"] = {"receipt_written": False}
    return receipt


def _generate_main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI handler for `generate`: build the three-context proof and print a summary.
    - Teleology: Implements `_generate_main` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Prove the First Correct Action product is distribution-true: the "
            "same hero goal must resolve to the same complete contract in the "
            "source checkout, a fresh package install, and the standalone export."
        ),
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--out", default=".microcosm/release-candidate-proof")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--work-root",
        default=None,
        help=(
            "transient work root for the install venv and export tree "
            "(default: a fresh temporary directory; must live outside the "
            "source root -- an in-tree work root is refused)"
        ),
    )
    parser.add_argument(
        "--keep-work",
        action="store_true",
        help="keep the install venv and export tree instead of removing them after evidence copy",
    )
    args = parser.parse_args(argv)
    try:
        packet = build_release_candidate_proof(
            root=Path(args.root),
            out_dir=Path(args.out),
            python_executable=args.python,
            keep_work=args.keep_work,
            work_root=Path(args.work_root) if args.work_root else None,
        )
    except ValueError as exc:
        parser.error(str(exc))
    # The generate-side failure codes from FAILURE_INTERPRETATIONS, so a red
    # run is greppable against the reviewer contract's taxonomy table.
    blocked_codes = []
    if any(row["status"] != "pass" for row in packet["contexts"].values()):
        blocked_codes.append("context_encounter_blocked")
    if packet["cross_context_agreement"]["status"] != "pass":
        blocked_codes.append("cross_context_agreement_blocked")
    if packet["expectation_policy"]["status"] != "pass":
        blocked_codes.append("expectation_policy_blocked")
    if packet["integrity"]["private_path_scan"]["status"] != "pass":
        blocked_codes.append("private_path_leak")
    if packet["integrity"]["source_mutation_check"]["status"] != "pass":
        blocked_codes.append("source_mutation_seen")
    summary = {
        "status": packet["status"],
        "blocked_codes": blocked_codes,
        "cross_context_agreement": packet["cross_context_agreement"]["status"],
        "expectation_policy": packet["expectation_policy"]["status"],
        "contexts": {
            context_id: packet["contexts"][context_id]["status"]
            for context_id in CONTEXT_IDS
        },
        "private_path_hit_count": packet["integrity"]["private_path_scan"][
            "private_path_hit_count"
        ],
        "source_files_mutated": packet["integrity"]["source_mutation_check"][
            "source_files_mutated"
        ],
        "packet_ref": packet["packet_ref"],
        "human_card_ref": packet["human_card_ref"],
        "release_authorized": False,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if packet["status"] == "pass" else 1


def _verify_main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI handler for `verify`: re-check an existing proof packet without rerunning.
    - Teleology: Implements `_verify_main` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Verify an existing Microcosm release-candidate proof packet "
            "without rerunning the substrate."
        ),
    )
    parser.add_argument("packet_dir")
    parser.add_argument("--root", default=".")
    parser.add_argument(
        "--no-write-receipt",
        action="store_true",
        help="only print the verification summary; do not write a receipt file",
    )
    args = parser.parse_args(argv)
    receipt = verify_release_candidate_proof(
        packet_dir=Path(args.packet_dir),
        root=Path(args.root),
        write_receipt=not args.no_write_receipt,
    )
    summary = {
        "status": receipt["status"],
        "statuses": receipt["statuses"],
        "packet_status": receipt.get("packet_status"),
        "cross_context_agreement_status": receipt.get("cross_context_agreement_status"),
        "no_substrate_rerun": receipt["no_substrate_rerun"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "packet_valid" else 1


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    CLI entry: dispatch the release-candidate proof generate/verify subcommands.
    - Teleology: Implements `main` for `microcosm_core.release_candidate_proof` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "verify":
        return _verify_main(args[1:])
    if args and args[0] == "generate":
        return _generate_main(args[1:])
    return _generate_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
