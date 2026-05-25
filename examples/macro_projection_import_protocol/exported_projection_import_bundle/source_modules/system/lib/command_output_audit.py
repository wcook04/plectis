"""
Command-output projection audit.

[PURPOSE]
- Teleology: Report which kernel commands emit the canonical projection envelope governed by std_command_output_projection.json, and which are still monolithic.
- Mechanism: Walk a registry of retrofitted commands, invoke each in projected mode (in-process, not via subprocess), validate envelope required fields, and emit a structured audit row per command.
- When-needed: Open when running `./repo-python kernel.py --command-output-projection-audit` or when verifying that a retrofit added all required envelope fields.
- Escalates-to: codex/standards/std_command_output_projection.json; system/lib/command_output_projection.py (envelope contract); per-command emitters in system/lib/kernel/commands/navigate.py.
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from system.lib.command_output_projection import (
    ENVELOPE_KIND,
    STANDARD_REF,
    envelope_field_present,
    envelope_required_fields,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_size_bytes(value: Any) -> int:
    """Return the compact JSON byte size for an audit sample."""
    try:
        text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except TypeError:
        text = json.dumps(str(value), ensure_ascii=False)
    return len(text.encode("utf-8"))


def _walk_repeated_atoms(
    value: Any,
    *,
    string_counts: Counter[str],
    subtree_counts: Counter[str],
    min_string_len: int,
    min_subtree_len: int,
) -> None:
    """Collect repeated semantic atoms without treating every short enum as waste."""
    if isinstance(value, str):
        text = value.strip()
        if len(text) >= min_string_len:
            string_counts[text] += 1
        return
    if isinstance(value, Mapping):
        try:
            encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except TypeError:
            encoded = ""
        if len(encoded) >= min_subtree_len:
            subtree_counts[encoded] += 1
        for child in value.values():
            _walk_repeated_atoms(
                child,
                string_counts=string_counts,
                subtree_counts=subtree_counts,
                min_string_len=min_string_len,
                min_subtree_len=min_subtree_len,
            )
        return
    if isinstance(value, list):
        try:
            encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except TypeError:
            encoded = ""
        if len(encoded) >= min_subtree_len:
            subtree_counts[encoded] += 1
        for child in value:
            _walk_repeated_atoms(
                child,
                string_counts=string_counts,
                subtree_counts=subtree_counts,
                min_string_len=min_string_len,
                min_subtree_len=min_subtree_len,
            )


def _repeat_rows(counter: Counter[str], *, limit: int, value_key: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for value, count in counter.most_common():
        if count <= 1:
            continue
        sample = value
        if len(sample) > 240:
            sample = sample[:237] + "..."
        rows.append(
            {
                value_key: sample,
                "count": count,
                "length": len(value),
                "estimated_repeated_bytes": (count - 1) * len(value),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _semantic_duplication_profile(
    value: Any,
    *,
    min_string_len: int = 24,
    min_subtree_len: int = 120,
    limit: int = 12,
) -> dict[str, Any]:
    string_counts: Counter[str] = Counter()
    subtree_counts: Counter[str] = Counter()
    _walk_repeated_atoms(
        value,
        string_counts=string_counts,
        subtree_counts=subtree_counts,
        min_string_len=min_string_len,
        min_subtree_len=min_subtree_len,
    )
    repeated_strings = _repeat_rows(string_counts, limit=limit, value_key="value")
    repeated_subtrees = _repeat_rows(subtree_counts, limit=limit, value_key="canonical_json")
    estimated_savings = sum(row["estimated_repeated_bytes"] for row in repeated_strings)
    estimated_savings += sum(row["estimated_repeated_bytes"] for row in repeated_subtrees)
    return {
        "repeated_string_count": len(repeated_strings),
        "repeated_subtree_count": len(repeated_subtrees),
        "estimated_factoring_savings_bytes": estimated_savings,
        "top_repeated_strings": repeated_strings,
        "top_repeated_subtrees": repeated_subtrees,
        "notes": [
            "Report-only estimate: counts repeated long string values and repeated JSON subtrees.",
            "Short enums and normal JSON key names are intentionally ignored; this audits repeated semantic objects, not minification.",
        ],
    }


def _safe_sample(label: str, fn: Callable[[], Any]) -> tuple[Any | None, str | None]:
    try:
        return fn(), None
    except Exception as exc:  # noqa: BLE001 - audit must not crash on one sample
        return None, f"{label} sample failed: {type(exc).__name__}: {exc}"


def _phase_default_summary_packet() -> Mapping[str, Any]:
    from system.lib.kernel.commands import navigate as _navigate

    navigator = _navigate.KernelNavigation(_navigate.state.REPO_ROOT)
    result = navigator.build_phase(None)
    return _navigate._phase_output_mode_packet(result, output_mode="summary")


def build_command_output_duplication_audit() -> dict[str, Any]:
    """Report repeated semantic objects in projected command packets.

    The audit is intentionally read-only. It measures packet shapes and repeated
    values so packet factoring can be justified before changing an emitter.
    """
    from system.lib.kernel.commands import navigate as _navigate

    samples: list[dict[str, Any]] = [
        {
            "command": "--phase",
            "band": "card",
            "projected": lambda: _navigate.build_phase_projection_envelope(band="card"),
            "default": _phase_default_summary_packet,
            "proof_case": True,
        },
        {
            "command": "--pulse",
            "band": "card",
            "projected": lambda: _navigate.build_pulse_projection_envelope(band="card"),
            "default": lambda: _navigate._pulse_snapshot(),
            "proof_case": False,
        },
        {
            "command": "--docs-route",
            "band": "card",
            "projected": lambda: _navigate.build_docs_route_projection_envelope(
                band="card",
                request="compression redundant keys",
            ),
            "default": lambda: _navigate.KernelNavigation(_navigate.state.REPO_ROOT)
            .build_docs_route("compression redundant keys")
            .to_dict(_navigate.state.KERNEL_VERSION, full=False),
            "proof_case": False,
        },
    ]

    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for sample in samples:
        projected, projected_error = _safe_sample(
            f"{sample['command']} projected",
            sample["projected"],
        )
        default, default_error = _safe_sample(
            f"{sample['command']} default",
            sample["default"],
        )
        if projected_error:
            errors.append(projected_error)
        if default_error:
            errors.append(default_error)
        projected_size = _json_size_bytes(projected) if projected is not None else None
        default_size = _json_size_bytes(default) if default is not None else None
        profile = (
            _semantic_duplication_profile(projected)
            if projected is not None
            else {
                "repeated_string_count": 0,
                "repeated_subtree_count": 0,
                "estimated_factoring_savings_bytes": 0,
                "top_repeated_strings": [],
                "top_repeated_subtrees": [],
            }
        )
        delta = (
            int(projected_size) - int(default_size)
            if projected_size is not None and default_size is not None
            else None
        )
        rows.append(
            {
                "command": sample["command"],
                "band": sample["band"],
                "proof_case": bool(sample.get("proof_case")),
                "projected_size_bytes": projected_size,
                "default_size_bytes": default_size,
                "projected_minus_default_bytes": delta,
                "payload_economy_status": (
                    "projected_smaller"
                    if delta is not None and delta < 0
                    else "projected_not_smaller"
                    if delta is not None and delta >= 0
                    else "comparison_unavailable"
                ),
                "duplication_profile": profile,
            }
        )

    projected_not_smaller = sum(
        1 for row in rows if row.get("payload_economy_status") == "projected_not_smaller"
    )
    estimated_savings = sum(
        int((row.get("duplication_profile") or {}).get("estimated_factoring_savings_bytes") or 0)
        for row in rows
    )
    return {
        "kind": "command_output_duplication_audit",
        "schema_version": "command_output_duplication_audit_v0",
        "generated_at": _utc_now(),
        "governing_standard": STANDARD_REF,
        "principle": "payload_economy_via_packet_level_semantic_factoring",
        "summary": {
            "sample_count": len(rows),
            "projected_not_smaller_count": projected_not_smaller,
            "estimated_factoring_savings_bytes": estimated_savings,
            "error_count": len(errors),
        },
        "rows": rows,
        "errors": errors,
        "next": [
            {
                "command": "./repo-python kernel.py --phase --output-band card",
                "reason": "Inspect the proof-case packet after any factoring change.",
            },
            {
                "command": "./repo-python kernel.py --command-output-projection-audit",
                "reason": "Verify canonical envelope coverage remains clean after factoring.",
            },
        ],
        "notes": [
            "This is report-only: it does not mutate command emitters.",
            "It audits repeated semantic objects and projected-vs-default byte posture, not key minification.",
            "Allowed duplication remains row-local identity, safety-critical currentness, and copy-out affordances.",
        ],
    }


def _audit_one_command(
    *,
    command: str,
    bands: list[str],
    project_fn: Callable[..., Mapping[str, Any]],
    monolithic_default: bool,
    band_kwargs: Mapping[str, Mapping[str, Any]] | None = None,
    notes: str = "",
) -> dict[str, Any]:
    """Audit one retrofitted command across its declared bands.

    project_fn(band, **kwargs) must return the in-process projection envelope dict
    for the given band (e.g. invoke the same code path the command handler uses
    when --output-band <band> is supplied). band_kwargs maps a band to extra
    kwargs needed by that band's projector (e.g. paper-module:card needs slug).
    """
    required = envelope_required_fields()
    band_results: list[dict[str, Any]] = []
    band_kwargs = band_kwargs or {}
    for band in bands:
        band_row: dict[str, Any] = {"band": band, "ok": True, "missing_fields": []}
        kwargs = dict(band_kwargs.get(band, {}))
        try:
            envelope = project_fn(band, **kwargs)
        except Exception as exc:  # noqa: BLE001 - audit must not crash on emitter error
            band_row.update(
                {
                    "ok": False,
                    "error": f"emitter raised: {type(exc).__name__}: {exc}",
                }
            )
            band_results.append(band_row)
            continue
        if not isinstance(envelope, Mapping):
            band_row.update({"ok": False, "error": "emitter returned non-mapping"})
            band_results.append(band_row)
            continue
        kind_value = str(envelope.get("kind") or "")
        if kind_value != ENVELOPE_KIND:
            band_row.update(
                {
                    "ok": False,
                    "error": f"envelope.kind={kind_value!r} expected {ENVELOPE_KIND!r}",
                }
            )
        missing = [field for field in required if not envelope_field_present(envelope, field)]
        if missing:
            band_row["ok"] = False
            band_row["missing_fields"] = missing
        band_row["row_id"] = str(envelope.get("row_id") or "")
        band_results.append(band_row)

    all_ok = all(row["ok"] for row in band_results) and bool(band_results)
    return {
        "command": command,
        "status": "projected" if all_ok else "projected_with_drift" if band_results else "monolithic",
        "bands_declared": list(bands),
        "band_results": band_results,
        "default_behavior": "monolithic" if monolithic_default else "projected",
        "back_compat_preserved": bool(monolithic_default),
        "notes": notes,
    }


def build_command_output_projection_audit() -> dict[str, Any]:
    """Build the command-output projection audit packet.

    Imports per-command projector callables lazily to avoid circular imports
    between this audit module and the navigate command module that imports the
    projection helper.
    """
    rows: list[dict[str, Any]] = []
    monolithic_commands: list[dict[str, Any]] = []

    try:
        from system.lib.kernel.commands import navigate as _navigate
    except Exception as exc:  # noqa: BLE001
        return {
            "kind": "command_output_projection_audit",
            "schema_version": "command_output_projection_audit_v0",
            "generated_at": _utc_now(),
            "governing_standard": STANDARD_REF,
            "summary": {
                "projected_commands": 0,
                "monolithic_commands": 0,
                "missing_required_fields": 0,
                "back_compat_preserved": True,
                "audit_load_error": f"{type(exc).__name__}: {exc}",
            },
            "rows": [],
            "monolithic": [],
            "notes": [
                "Audit could not import system.lib.kernel.commands.navigate; the",
                "command-output projection retrofit may not be loaded.",
            ],
        }

    # Registry of retrofitted commands. Each entry names the projector callable on
    # the navigate module (as a string) and the bands it supports. The projector
    # must be a zero-arg-or-band-only function returning the in-process envelope.
    registry: list[dict[str, Any]] = [
        {
            "command": "--phase",
            "projector_attr": "build_phase_projection_envelope",
            "bands": ["card", "full"],
            "monolithic_default": True,
            "notes": "Default --phase emission unchanged; --output-band <band> opts in.",
        },
        {
            "command": "--paper-module",
            "projector_attr": "build_paper_module_projection_envelope",
            "bands": ["flag", "card"],
            "monolithic_default": True,
            "band_kwargs": {"card": {"slug": "raw_seed_substrate"}},
            "notes": (
                "Default --paper-module emission (full evidence/markdown) unchanged; "
                "--output-band <band> opts in. Audit uses raw_seed_substrate as a stable "
                "sample slug for the card-band probe."
            ),
        },
        {
            "command": "--info",
            "projector_attr": "build_info_projection_envelope",
            "bands": ["flag", "card"],
            "monolithic_default": True,
            "notes": "Default --info emission unchanged; --output-band <band> opts in.",
        },
        {
            "command": "--frontier",
            "projector_attr": "build_frontier_projection_envelope",
            "bands": ["flag", "card"],
            "monolithic_default": True,
            "notes": "Default --frontier emission unchanged; --output-band <band> opts in.",
        },
        {
            "command": "--docs-route",
            "projector_attr": "build_docs_route_projection_envelope",
            "bands": ["card"],
            "monolithic_default": True,
            "notes": "Default --docs-route emission unchanged; --output-band card opts in.",
        },
        {
            "command": "--pulse",
            "projector_attr": "build_pulse_projection_envelope",
            "bands": ["flag", "card"],
            "monolithic_default": True,
            "notes": "Tranche 2: default --pulse emission unchanged; --output-band <band> opts in, and --pulse --json is a card-band machine-readable alias.",
        },
        {
            "command": "--working-set",
            "projector_attr": "build_working_set_projection_envelope",
            "bands": ["flag", "card"],
            "monolithic_default": True,
            "notes": "Tranche 2: default --working-set emission unchanged; --output-band <band> opts in.",
        },
        {
            "command": "--system-map",
            "projector_attr": "build_system_map_projection_envelope",
            "bands": ["flag", "card"],
            "monolithic_default": True,
            "notes": "Tranche 2: default --system-map emission unchanged; --output-band <band> opts in. Generator-mode flags (--system-map-print/--dry-run/--bridge-only) bypass projection.",
        },
        {
            "command": "--session-diagnostics",
            "projector_attr": "build_session_diagnostics_projection_envelope",
            "bands": ["flag", "card"],
            "monolithic_default": True,
            "notes": "Tranche 2: default --session-diagnostics emission unchanged; --output-band <band> opts in.",
        },
    ]

    for entry in registry:
        attr = entry["projector_attr"]
        projector = getattr(_navigate, attr, None)
        if projector is None:
            monolithic_commands.append(
                {
                    "command": entry["command"],
                    "status": "monolithic",
                    "reason": f"projector {attr!r} not found on navigate module",
                }
            )
            continue

        def make_caller(fn: Callable[..., Any], cmd_label: str) -> Callable[..., Mapping[str, Any]]:
            def _call(band: str, **kwargs: Any) -> Mapping[str, Any]:
                try:
                    result = fn(band=band, **kwargs)
                except TypeError:
                    # Projector may take no arguments or only positional band.
                    try:
                        result = fn(band, **kwargs)
                    except TypeError:
                        result = fn()
                return result if isinstance(result, Mapping) else {}
            _call.__name__ = f"projector_{cmd_label}"
            return _call

        rows.append(
            _audit_one_command(
                command=entry["command"],
                bands=entry["bands"],
                project_fn=make_caller(projector, entry["command"]),
                monolithic_default=entry["monolithic_default"],
                band_kwargs=entry.get("band_kwargs"),
                notes=entry.get("notes", ""),
            )
        )

    projected_count = sum(1 for row in rows if row["status"] == "projected")
    drift_count = sum(1 for row in rows if row["status"] == "projected_with_drift")
    missing_required_total = sum(
        len(br.get("missing_fields", []))
        for row in rows
        for br in row.get("band_results", [])
    )
    back_compat_preserved = all(row.get("back_compat_preserved", False) for row in rows)

    return {
        "kind": "command_output_projection_audit",
        "schema_version": "command_output_projection_audit_v0",
        "generated_at": _utc_now(),
        "governing_standard": STANDARD_REF,
        "summary": {
            "registered_commands": len(registry),
            "projected_commands": projected_count,
            "projected_with_drift": drift_count,
            "monolithic_commands": len(monolithic_commands),
            "missing_required_fields": missing_required_total,
            "back_compat_preserved": back_compat_preserved,
        },
        "rows": rows,
        "monolithic": monolithic_commands,
        "next": [
            {
                "command": "./repo-python kernel.py --kind-band-contract-audit",
                "reason": "Cross-check that retrofitted command bands are consistent with kind-native bands.",
            },
            {
                "command": "./repo-python kernel.py --row paper_modules:<slug> --band card",
                "reason": "Verify the generic --row adapter delegates to option-surface for at least one kind.",
            },
        ],
        "notes": [
            "v0 audit: in-process projector invocation; no subprocess.",
            "Default emission for every retrofitted command remains unchanged. Projection is opt-in via --output-band.",
            "Adding a new retrofitted command: append a registry row above and add a build_<cmd>_projection_envelope on system/lib/kernel/commands/navigate.py.",
        ],
    }
