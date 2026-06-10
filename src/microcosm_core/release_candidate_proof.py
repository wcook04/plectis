"""Three-context First Correct Action release-candidate proof.

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
  binding every output by SHA-256 and proving cross-context agreement on the
  selected owner and command; `verify` re-checks digests, re-derives every
  context encounter and the agreement block from on-disk evidence, and never
  reruns the substrate.
- Reads: the source checkout, the throwaway install venv outputs, and the
  throwaway export tree (both work trees are removed after evidence copy
  unless --keep-work).
- Writes: the packet directory only (default .microcosm/release-candidate-proof).
- Non-goal: a passing packet does NOT authorize release, publication, provider
  calls, source mutation, domain correctness, or whole-system correctness; it
  proves the goal-shaped encounter is distribution-true and nothing more.
- Fails: generate exits 1 on a blocked packet; verify exits 1 on any
  digest/derivation/leak failure; subprocess failures are preserved as
  evidence, not hidden.
- Escalates-to: skeptic_flight_recorder (the shared helpers and the
  single-context replay packet) and tests/test_release_candidate_proof.py.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
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


SCHEMA_VERSION = "microcosm_first_action_release_candidate_proof_v1"
ENCOUNTER_SCHEMA_VERSION = "microcosm_release_candidate_context_encounter_v1"
VERIFICATION_SCHEMA_VERSION = "microcosm_release_candidate_proof_verification_v1"
PACKET_FILENAME = "release-candidate-proof.json"
CARD_FILENAME = "release-candidate-proof-card.md"
VERIFICATION_FILENAME = "release-candidate-proof-verification.json"
EXPORT_ARTIFACT_DIR_NAME = "microcosm-substrate"
CONTEXT_IDS = ("source_checkout", "fresh_install", "standalone_export")
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
) -> dict[str, Any]:
    """Run one proof command and persist a digest-bound, packet-relative receipt.

    - Teleology: the release-candidate analogue of the recorder's command
      executor -- same public-argv projection and digest binding, but every
      output ref is PACKET-RELATIVE so the packet stays portable regardless of
      which context root the command ran in.
    - Guarantee: writes raw stdout/stderr under `out_dir`, returns a record
      with public argv (projected against `cwd`), a sha256 of the private
      argv, return code, duration, packet-relative stdout/stderr refs with
      sha256 digests and byte counts, and json_detected; never serializes the
      private argv.
    - Fails: propagates OSError from output writes; runner timeouts arrive as
      return code 124 per default_runner.
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
    stdout_path = out_dir / stdout_rel
    stderr_path = out_dir / stderr_rel
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_bytes(result.stdout)
    stderr_path.write_bytes(result.stderr)
    return {
        "command_id": command_id,
        "argv": display_argv,
        "subprocess_argv_public": _public_subprocess_argv(actual_argv, cwd),
        "subprocess_argv_sha256": sha256_bytes("\0".join(actual_argv).encode("utf-8")),
        "return_code": result.returncode,
        "duration_seconds": result.duration_seconds,
        "stdout_ref": stdout_rel,
        "stderr_ref": stderr_rel,
        "stdout_sha256": sha256_bytes(result.stdout),
        "stderr_sha256": sha256_bytes(result.stderr),
        "stdout_bytes": len(result.stdout),
        "stderr_bytes": len(result.stderr),
        "json_detected": _parse_json_bytes(result.stdout) is not None,
    }


def derive_context_encounter(
    *,
    context_id: str,
    hero_payload: dict[str, Any] | None,
    hero_return_code: int | None,
    assay_payload: dict[str, Any] | None,
    assay_return_code: int | None,
    demo_check_return_code: int | None,
) -> dict[str, Any]:
    """Derive one context's first-action encounter block from its evidence.

    - Teleology: state, per distribution context, whether the hero goal became
      a complete first-action contract -- using the SAME completeness predicate
      the flight recorder uses (first_action_contract_checks), so "complete"
      cannot drift between proof surfaces.
    - Guarantee: pure deterministic projection of payloads + return codes;
      status "pass" only when every check holds; demo_check_return_code=None
      (fresh_install has no committed demo to drift-check) records the check
      as not-applicable rather than failed.
    - Fails: never raises.
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


def derive_cross_context_agreement(
    encounters: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Prove the three contexts selected the SAME owner and command for the hero goal.

    - Teleology: the distribution-truth core -- a contract that resolves
      differently installed than in the checkout is a different product; this
      block makes that divergence a named, mechanical failure instead of a
      latent surprise.
    - Guarantee: pure projection over the per-context encounter blocks;
      status "pass" only when every expected context is present and the owner
      organ_id, the command, and the validator command are each identical —
      and a non-empty string — across all of them (a missing context or empty
      value can never satisfy agreement by vacuity).
    - Fails: never raises.
    """

    def identical_nonempty(values: dict[str, Any]) -> bool:
        distinct = set(values.values())
        return len(distinct) == 1 and all(
            isinstance(value, str) and value for value in distinct
        )

    owner_ids: dict[str, Any] = {}
    commands: dict[str, Any] = {}
    validator_commands: dict[str, Any] = {}
    for context_id in CONTEXT_IDS:
        encounter = encounters.get(context_id)
        row = encounter if isinstance(encounter, dict) else {}
        owner = row.get("owner") if isinstance(row.get("owner"), dict) else {}
        owner_ids[context_id] = owner.get("organ_id")
        commands[context_id] = row.get("command")
        validator_commands[context_id] = row.get("validator_command")
    owner_identical = identical_nonempty(owner_ids)
    command_identical = identical_nonempty(commands)
    validator_identical = identical_nonempty(validator_commands)
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
        "validator_commands": validator_commands,
    }


def _read_json_evidence(out_dir: Path, relpath: str) -> dict[str, Any] | None:
    """Best-effort load one packet-relative evidence file as a JSON object."""
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
    """Re-derive one context's encounter block from packet-relative evidence.

    Shared by generate (first derivation) and verify (re-derivation), so the
    stored block is provably a projection of the digest-bound files plus the
    recorded return codes.
    """
    by_id = {
        row["command_id"]: row
        for row in records
        if isinstance(row, dict) and isinstance(row.get("command_id"), str)
    }

    def return_code(command_id: str) -> int | None:
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
    """The per-context encounter commands, shared by checkout and export contexts."""
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
) -> list[dict[str, Any]]:
    """Run hero + assay + demo-check in one context root, recording evidence."""
    env, _ = subprocess_env(context_root)
    argvs = _encounter_argvs(python_executable)
    evidence = CONTEXT_EVIDENCE[context_id]
    records = []
    for step, display_head in (
        ("hero", ["microcosm", "comprehend", "--first-action", FIRST_ACTION_HERO_GOAL]),
        ("assay", ["microcosm", "comprehension-assay", "--first-action"]),
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
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Run the three-context first-action encounter and write the proof packet + card.

    - Teleology: the release-candidate proof builder -- prove that a cold
      reviewer's hero goal resolves to the SAME complete, graph-backed first
      action in the source checkout, a fresh pip install, and the standalone
      export, with every claim derived from digest-bound evidence.
    - Guarantee: writes release-candidate-proof.json and the human card under
      `out_dir`; packet status is "pass" only when all three context
      encounters pass, cross-context agreement holds, no private path leaks
      into any written file, and the checkout's tracked source is unchanged
      by the run; failures are preserved as evidence with named checks.
    - Writes: `out_dir` (evidence + packet + card); transient install/export
      work trees under `out_dir` are removed after evidence copy unless
      keep_work.
    - Non-goal: does NOT authorize release/publication/provider calls/source
      mutation, and does not assert domain or whole-system correctness.
    - Fails: propagates OSError on packet writes; probe failures land in the
      packet, not as exceptions.
    """
    root = root.expanduser().resolve(strict=False)
    out_dir = out_dir.expanduser()
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    # Every evidence file in the packet must belong to THIS run: stale bytes
    # from a prior run would otherwise feed encounters on degraded runs, and a
    # stale receipt would skew the generate-side scan relative to verify.
    for stale_sub in ("checkout", "install", "export", "work"):
        shutil.rmtree(out_dir / stale_sub, ignore_errors=True)
    for stale_file in (PACKET_FILENAME, CARD_FILENAME, VERIFICATION_FILENAME):
        (out_dir / stale_file).unlink(missing_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = generated_at or utc_now()
    before_snapshot = source_snapshot(root)

    records: list[dict[str, Any]] = []
    work_notes: list[str] = []
    copied_evidence: list[dict[str, Any]] = []

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
    # the installed console.
    install_work = out_dir / "work/install"
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
    export_work = out_dir / "work/export"
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
            )
        )
    else:
        work_notes.append("export tree missing: standalone_export encounter not run")

    if not keep_work:
        shutil.rmtree(out_dir / "work", ignore_errors=True)

    encounters = {
        context_id: _context_encounter_from_disk(context_id, records, out_dir)
        for context_id in CONTEXT_IDS
    }
    agreement = derive_cross_context_agreement(encounters)
    after_snapshot = source_snapshot(root)
    mutation = source_mutation_check(before_snapshot, after_snapshot)

    def publishable_paths() -> list[Path]:
        # The work trees (venv, export) are transient workspace, not published
        # evidence — under --keep-work they would otherwise drag thousands of
        # absolute-path-bearing files (shebangs, pip RECORD) into the scan and
        # block an otherwise-passing packet.
        work_root = out_dir / "work"
        return [
            path
            for path in out_dir.rglob("*")
            if path.is_file()
            and not path.name.endswith(".tmp")
            and work_root not in path.parents
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
            and private_scan["status"] == "pass"
            and mutation["status"] == "pass"
            else "blocked"
        ),
        "generated_at": generated,
        "hero_goal": FIRST_ACTION_HERO_GOAL,
        "packet_ref": PACKET_FILENAME,
        "human_card_ref": CARD_FILENAME,
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
        "integrity": {
            "source_mutation_check": mutation,
            "private_path_scan": private_scan,
            "provider_env_policy": provider_policy,
            "copied_evidence": copied_evidence,
            "work_notes": work_notes,
        },
        "commands": records,
        "proof_boundary": (
            "proves the goal-shaped first-action encounter is distribution-true "
            "across checkout, install, and export; does not authorize release, "
            "publication, provider calls, source mutation, domain correctness, "
            "or whole-system correctness. Verification proves the packet is "
            "internally consistent with its digest-bound evidence; it does not "
            "prove the run happened as recorded — rerun the generator to "
            "re-establish provenance"
        ),
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
    """Render the proof packet into the human release-candidate card (a projection, not authority)."""
    agreement = packet["cross_context_agreement"]
    integrity = packet["integrity"]
    lines = [
        "# Microcosm First Correct Action — Release Candidate Proof",
        "",
        f"- Packet status: `{packet['status']}`",
        f"- Hero goal: `{packet['hero_goal']}`",
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
    """Verify an existing release-candidate proof packet WITHOUT rerunning anything.

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
    policy_ok = all(
        policy.get(key) is False
        for key in (
            "release_authorized",
            "provider_calls_authorized",
            "source_mutation_authorized",
        )
    ) and (
        provider_policy.get("provider_credential_env_keys_available_to_subprocess")
        is False
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
    """CLI handler for `generate`: build the three-context proof and print a summary."""
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
        "--keep-work",
        action="store_true",
        help="keep the install venv and export tree instead of removing them after evidence copy",
    )
    args = parser.parse_args(argv)
    packet = build_release_candidate_proof(
        root=Path(args.root),
        out_dir=Path(args.out),
        python_executable=args.python,
        keep_work=args.keep_work,
    )
    summary = {
        "status": packet["status"],
        "cross_context_agreement": packet["cross_context_agreement"]["status"],
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
    """CLI handler for `verify`: re-check an existing proof packet without rerunning."""
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
    """CLI entry: dispatch the release-candidate proof generate/verify subcommands."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "verify":
        return _verify_main(args[1:])
    if args and args[0] == "generate":
        return _generate_main(args[1:])
    return _generate_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
