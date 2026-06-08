from __future__ import annotations

from collections.abc import Iterable
import json
from pathlib import Path
from typing import Any

from .schemas import read_json_strict


PASS = "pass"
BLOCKED_PRIVATE = "blocked_private_state"
BLOCKED_PUBLIC_WRITE = "blocked_public_write_attempt"
BLOCKED_CASE_REVIEW = "blocked_case_review_required"
DEFAULT_SCAN_SCOPE = {
    "scope_id": "synthetic_sentinel_policy_default",
    "intended_use": "Detect declared synthetic sentinel tokens and classify explicit macro-import material rows.",
    "not_a_complete_secret_scan": True,
    "does_not_read_binary_or_live_account_state": True,
    "does_not_certify_absence_of_secrets": True,
    "does_not_authorize_source_mutation": True,
    "body_text_exported_in_findings": False,
}

TEXT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".lean",
    ".md",
    ".py",
    ".sh",
    ".toml",
    ".txt",
}
TEXT_FILENAMES = {
    "Dockerfile",
    "LICENSE",
    "Makefile",
    "NOTICE",
}
SCAN_CHUNK_SIZE = 64 * 1024
SYNTHETIC_NEGATIVE_MARKERS = (
    '"expected_negative_case": true',
    '"expected_negative_case_id"',
    '"negative_case_id"',
    '"synthetic_negative_fixture": true',
)

PUBLIC_ROOT_DIR_NAME = "microcosm-substrate"
PUBLIC_ROOT_RELATIVE_PREFIXES = (
    "AGENTS.md",
    "ANTI_PRINCIPLES.md",
    "AXIOMS.md",
    "CONSTITUTION.md",
    "PRINCIPLES.md",
    "README.md",
    "bootstrap.sh",
    "core/",
    "examples/",
    "fixtures/",
    "pyproject.toml",
    "receipts/",
    "src/",
    "tests/",
)


def _looks_like_public_root(path: Path) -> bool:
    """Heuristic test for whether a directory is the public microcosm-substrate root.

    - Teleology: anchors public-relative path rendering so scan findings never leak the operator's absolute filesystem layout.
    - Guarantee: returns True only when pyproject.toml, src/microcosm_core/, and core/private_state_forbidden_classes.json all exist under path; otherwise False.
    - Fails: never raises; a missing/unreadable directory member resolves to False via Path.is_file/is_dir.
    - Reads: path/pyproject.toml, path/src/microcosm_core, path/core/private_state_forbidden_classes.json.
    - Non-goal: does not authorize source-body export, release, or treat the matched root as source-of-truth authority.
    """
    return (
        (path / "pyproject.toml").is_file()
        and (path / "src/microcosm_core").is_dir()
        and (path / "core/private_state_forbidden_classes.json").is_file()
    )


def load_forbidden_classes(path: str | Path) -> dict[str, Any]:
    """Strictly load the forbidden-class policy that drives every private-state scan.

    - Teleology: the single entry that turns the on-disk forbidden-class policy file into the dict every scanner consumes.
    - Guarantee: returns the policy as a dict after strict JSON parse; the returned object is the verbatim policy mapping.
    - Fails: malformed JSON -> read_json_strict raises; a non-object top-level payload -> raises ValueError "forbidden class policy must be a JSON object".
    - When-needed: inspect when a scan misclassifies because the policy file shape (classes/terms/risk_routing) is wrong.
    - Reads: the forbidden-class policy file at `path` (canonically core/private_state_forbidden_classes.json).
    - Escalates-to: microcosm_core.schemas.read_json_strict and core/private_state_forbidden_classes.json for the authoritative policy shape.
    - Non-goal: does not validate term correctness, authorize source export, or certify the policy is a complete secret list.
    """
    payload = read_json_strict(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: forbidden class policy must be a JSON object")
    return payload


def _resolved(path: Path) -> Path:
    """Normalize a path for root-relative comparison without requiring it to exist.

    - Teleology: gives every path comparison a stable canonical form so public-root inference is symlink/`~`-robust.
    - Guarantee: returns the expanduser+resolve(strict=False) form of path; non-existent paths resolve without error.
    - Fails: never raises; strict=False means missing components do not raise.
    - Reads: only the supplied path (and the filesystem for symlink resolution); reads no policy or source body.
    """
    return path.expanduser().resolve(strict=False)


def _public_root_for_path(path: str | Path) -> Path | None:
    """Infer the public root that a given path should be rendered relative to.

    - Teleology: locates the public-safe root so absolute operator paths are stripped before they appear in scan findings.
    - Guarantee: returns the nearest ancestor named microcosm-substrate or matching `_looks_like_public_root`, else the cwd when path lies under it, else None.
    - Fails: never raises; an unrelated absolute path that is not under cwd returns None.
    - Reads: path's resolved ancestors and Path.cwd(); reads no policy or source body.
    - Non-goal: does not authorize export or certify the inferred root as authority — it only governs display-path stripping.
    """
    raw_path = Path(path)
    resolved = _resolved(raw_path)
    start = resolved if raw_path.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if candidate.name == PUBLIC_ROOT_DIR_NAME or _looks_like_public_root(candidate):
            return candidate

    cwd = Path.cwd().resolve(strict=False)
    try:
        resolved.relative_to(cwd)
    except ValueError:
        return None
    return cwd


def public_relative_path(path: str | Path, *, display_root: str | Path | None = None) -> str:
    """Render a scan path as a public-safe relative string, never an operator-absolute path.

    - Teleology: the source-ref normalizer that keeps every emitted scan path public-safe (no operator home, no absolute root).
    - Guarantee: returns a POSIX path relative to display_root (when supplied and containing path) or the inferred public root; an already-relative input is returned as-is; only falls back to the absolute resolved string when no root contains the path.
    - Fails: never raises; a path outside every candidate root degrades to its resolved absolute POSIX form rather than erroring.
    - When-needed: inspect when a finding's `path` field leaks an absolute or operator-home prefix.
    - Reads: only the supplied path and display_root; reads no policy or source body.
    - Non-goal: does not guarantee absence of all private substrings — only strips the leading root; does not authorize export.
    """
    raw_path = Path(path)
    if not raw_path.is_absolute():
        return raw_path.as_posix()

    resolved = _resolved(raw_path)
    if display_root is not None:
        root = _resolved(Path(display_root))
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            pass

    inferred_root = _public_root_for_path(raw_path)
    if inferred_root is not None:
        try:
            return resolved.relative_to(inferred_root).as_posix()
        except ValueError:
            pass
    return resolved.as_posix()


def _infer_display_root(paths: Iterable[Path]) -> Path | None:
    """Pick a shared public display root from the first inferable path in a batch.

    - Teleology: lets a multi-path scan agree on one public root so every finding's path is stripped consistently.
    - Guarantee: returns the public root of the first path for which one can be inferred; None when no path yields a root.
    - Fails: never raises; an empty or all-unrooted iterable returns None.
    - Reads: only the supplied paths (via `_public_root_for_path`); reads no policy or source body.
    """
    for path in paths:
        root = _public_root_for_path(path)
        if root is not None:
            return root
    return None


def _terms(forbidden_classes: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten the forbidden-class policy into the token rows the scanner matches against.

    - Teleology: turns the nested classes/terms policy into the flat (class, term_id, token, remediation) rows scanning iterates over.
    - Guarantee: returns one row per term carrying a non-empty token; class_id, term_id, and remediation default to stable fallbacks when absent; non-dict classes/terms are skipped.
    - Fails: never raises; malformed (non-dict) class or term entries and blank tokens are silently dropped.
    - Reads: forbidden_classes["classes"][*]["terms"][*] (class_id, remediation, token, term_id) only.
    - Non-goal: does not validate that the token set is a complete secret list, nor authorize export.
    """
    rows: list[dict[str, str]] = []
    for cls in forbidden_classes.get("classes", []):
        if not isinstance(cls, dict):
            continue
        class_id = str(cls.get("class_id") or "forbidden_content_body")
        remediation = str(
            cls.get("remediation") or "exclude credential/account-bound material"
        )
        for term in cls.get("terms", []):
            if not isinstance(term, dict):
                continue
            token = str(term.get("token") or "").strip()
            term_id = str(term.get("term_id") or token).strip()
            if token:
                rows.append(
                    {
                        "forbidden_class": class_id,
                        "term_id": term_id,
                        "token": token,
                        "remediation": remediation,
                    }
                )
    return rows


def _import_policy(forbidden_classes: dict[str, Any]) -> dict[str, Any]:
    """Extract the public-safe macro-import sub-policy from the forbidden-class policy.

    - Teleology: isolates the import-routing block (risk routing, allowed modes, required provenance fields) for the import classifier.
    - Guarantee: returns forbidden_classes["public_safe_macro_import"] when it is a dict, else an empty dict.
    - Fails: never raises; an absent or non-dict block returns {} so the caller treats the policy as maximally restrictive.
    - Reads: forbidden_classes["public_safe_macro_import"] only.
    - Non-goal: does not validate the sub-policy contents or authorize any import on its own.
    """
    policy = forbidden_classes.get("public_safe_macro_import", {})
    return policy if isinstance(policy, dict) else {}


def _scan_scope(forbidden_classes: dict[str, Any]) -> dict[str, Any]:
    """Resolve the scope-disclaimer block stamped onto every scan result.

    - Teleology: carries the honest "what this scan is NOT" boundary (not a complete secret scan, no binary/live-state read) into each result envelope.
    - Guarantee: returns DEFAULT_SCAN_SCOPE overlaid with any dict at forbidden_classes["scan_scope"]; a copy is returned so callers cannot mutate the module default.
    - Fails: never raises; an absent or non-dict scan_scope returns a copy of DEFAULT_SCAN_SCOPE.
    - Reads: forbidden_classes["scan_scope"] and the DEFAULT_SCAN_SCOPE constant.
    - Non-goal: the scope is a disclaimer, not an authorization — it never certifies absence of secrets or authorizes export.
    """
    scope = forbidden_classes.get("scan_scope")
    if not isinstance(scope, dict):
        return dict(DEFAULT_SCAN_SCOPE)
    merged = dict(DEFAULT_SCAN_SCOPE)
    merged.update(scope)
    return merged


def _anti_claim(forbidden_classes: dict[str, Any]) -> str:
    """Resolve the ceiling-defense sentence stamped onto every scan result.

    - Teleology: binds the explicit overclaim guard ("bounded evidence, not complete secret-audit authority") into each result so consumers cannot read a PASS as a release certificate.
    - Guarantee: returns forbidden_classes["anti_claim"] as a string when present, else the default bounded-evidence anti-claim sentence.
    - Fails: never raises; an absent key yields the default string.
    - Reads: forbidden_classes["anti_claim"] only.
    - Non-goal: the anti-claim is documentation of the ceiling, not enforcement; it does not authorize export or release.
    """
    return str(
        forbidden_classes.get("anti_claim")
        or "Scanner output is bounded sentinel/import-policy evidence, not complete secret-audit authority."
    )


def _string_list(value: object) -> list[str]:
    """Coerce a policy field into a clean list of non-empty trimmed strings.

    - Teleology: the defensive normalizer that lets policy list-fields (allowed modes, required fields, forbidden classes) be consumed safely.
    - Guarantee: returns a list of stripped string items, dropping blanks; a non-list input returns [].
    - Fails: never raises; non-list and empty inputs return [].
    - Reads: only the supplied value.
    """
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def is_text_scan_candidate(path: str | Path) -> bool:
    """Decide whether a path is a text file the token scanner should open.

    - Teleology: the allow-list gate that keeps the scanner on text it can decode, never opening binary or live-account artifacts.
    - Guarantee: returns True iff the path's suffix is in TEXT_SUFFIXES or its filename is in TEXT_FILENAMES; otherwise False.
    - Fails: never raises (extension/name membership test only).
    - When-needed: inspect when a file that should (or should not) be scanned is being skipped or read.
    - Reads: the TEXT_SUFFIXES and TEXT_FILENAMES constants and the path's suffix/name; opens no file.
    - Non-goal: a candidacy filter, not a guarantee the file is secret-free; does not authorize export.
    """
    candidate = Path(path)
    return candidate.suffix in TEXT_SUFFIXES or candidate.name in TEXT_FILENAMES


def _bool_from_row(row: dict[str, Any], key: str) -> bool:
    """Read a strict-True flag from an import row, falling back to its authority_ceiling block.

    - Teleology: lets the import classifier read an overclaim flag whether it sits at the row top level or nested under authority_ceiling.
    - Guarantee: returns True only when row[key] is exactly True, or (when key absent at top level) when row["authority_ceiling"][key] is exactly True; every other value -> False.
    - Fails: never raises; missing keys or a non-dict authority_ceiling resolve to False.
    - Reads: row[key] and row["authority_ceiling"][key] only.
    """
    if key in row:
        return row.get(key) is True
    ceiling = row.get("authority_ceiling")
    if isinstance(ceiling, dict):
        return ceiling.get(key) is True
    return False


def classify_public_safe_macro_import(
    row: dict[str, Any],
    *,
    forbidden_classes: dict[str, Any],
) -> dict[str, Any]:
    """Classify one requested macro import without exposing credential-bound bodies.

    - Teleology: the import/export custody gate that decides whether one requested macro body may enter verified public import, citing redacted findings only.
    - Guarantee: returns a dict with status PASS only when no findings accumulate; status BLOCKED_CASE_REVIEW when the sole/route reason is case_review, else BLOCKED_PRIVATE; always sets route, material_class, credential_exposure_risk, public_safe_mode, flow_allowed (== PASS), findings (each body_redacted), body_redacted True, scan_scope, and anti_claim.
    - Fails: never raises; policy/account-bound violations surface as error-coded findings (PUBLIC_SAFE_IMPORT_TRUE_FORBIDDEN_CLASS / UNKNOWN_BODY_CLASS / CASE_REVIEW_REQUIRED / SYNTHETIC_ONLY / MODE_UNSUPPORTED / PROVENANCE_MISSING / AUTHORITY_OVERCLAIM) with status != PASS, never as exceptions or exported bodies.
    - When-needed: inspect before importing any macro body, or when a body import is unexpectedly blocked or passed.
    - Reads: the row's material_class/credential_exposure_risk/public_safe_mode/provenance fields and the public_safe_macro_import sub-policy (risk_routing, true_forbidden/public_safe classes, required fields, allowed modes, forbidden flags).
    - Escalates-to: core/private_state_forbidden_classes.json::public_safe_macro_import and the import classifier tests for the authoritative routing/error-code contract.
    - Non-goal: never emits the body text, and does not authorize hosted publication, account/root mirror, or whole-system authority even on PASS.
    """

    policy = _import_policy(forbidden_classes)
    material_class = str(row.get("material_class") or "").strip()
    private_state_risk = str(
        row.get("credential_exposure_risk")
        or row.get("private_state_risk")
        or ""
    ).strip().lower()
    risk_routing = policy.get("risk_routing", {})
    if not isinstance(risk_routing, dict):
        risk_routing = {}
    route = str(risk_routing.get(private_state_risk) or "case_review")

    true_forbidden = set(_string_list(policy.get("true_forbidden_material_classes")))
    public_safe_classes = set(_string_list(policy.get("public_safe_body_material_classes")))
    required_fields = _string_list(policy.get("required_public_body_fields"))
    allowed_modes = set(_string_list(policy.get("allowed_public_safe_modes")))
    forbidden_flags = _string_list(policy.get("claim_ceiling_forbidden_flags"))

    findings: list[dict[str, Any]] = []
    if material_class in true_forbidden:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_TRUE_FORBIDDEN_CLASS",
                "message": "Credential-bound, operator, provider, or raw-seed material classes cannot enter verified macro import.",
                "material_class": material_class,
                "body_redacted": True,
            }
        )
    elif material_class not in public_safe_classes:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_UNKNOWN_BODY_CLASS",
                "message": "Body-bearing material must declare a verified public macro body class.",
                "material_class": material_class,
                "body_redacted": True,
            }
        )

    if route in {"case_review", "case_review_for_secret_risk"}:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_CASE_REVIEW_REQUIRED",
                "message": "Medium or unclassified secret/account-bound risk requires case review before body import.",
                "material_class": material_class,
                "body_redacted": True,
            }
        )
    elif route in {"synthetic_only", "credential_or_account_bound_exclusion"}:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_SYNTHETIC_ONLY",
                "message": "High credential/account-bound risk is excluded from real macro import.",
                "material_class": material_class,
                "body_redacted": True,
            }
        )

    public_safe_mode = str(row.get("public_safe_mode") or "").strip()
    if public_safe_mode not in allowed_modes:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_MODE_UNSUPPORTED",
                "message": "Verified macro body import must use an allowed real-substrate mode.",
                "material_class": material_class,
                "body_redacted": True,
            }
        )

    missing_fields: list[str] = []
    for field in required_fields:
        value = row.get(field)
        if isinstance(value, list):
            if not _string_list(value):
                missing_fields.append(field)
        elif value in (None, "", False):
            missing_fields.append(field)
    if missing_fields:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_PROVENANCE_MISSING",
                "message": "Verified macro body import requires source, provenance, validation, risk, mode, claim floor, and body verification fields.",
                "missing_fields": missing_fields,
                "material_class": material_class,
                "body_redacted": True,
            }
        )

    forbidden_claim_flags = [flag for flag in forbidden_flags if _bool_from_row(row, flag)]
    if row.get("claims_source_authority") is True:
        forbidden_claim_flags.append("claims_source_authority")
    if forbidden_claim_flags:
        findings.append(
            {
                "error_code": "PUBLIC_SAFE_IMPORT_AUTHORITY_OVERCLAIM",
                "message": "Verified macro body import cannot upgrade itself into hosted publication, account/root mirror, or whole-system authority.",
                "forbidden_flags": sorted(set(forbidden_claim_flags)),
                "material_class": material_class,
                "body_redacted": True,
            }
        )

    if findings:
        status = BLOCKED_CASE_REVIEW if route == "case_review" else BLOCKED_PRIVATE
    else:
        status = PASS

    return {
        "status": status,
        "route": route,
        "material_class": material_class,
        "credential_exposure_risk": private_state_risk,
        "public_safe_mode": public_safe_mode,
        "flow_allowed": status == PASS,
        "findings": findings,
        "body_redacted": True,
        "scan_scope": _scan_scope(forbidden_classes),
        "anti_claim": _anti_claim(forbidden_classes),
    }


def _is_expected_negative_fixture_path(path: str) -> bool:
    """Decide whether a path is a sanctioned home for synthetic forbidden-token fixtures.

    - Teleology: lets the scanner treat the policy files, tests, and pattern-binding inputs as places where forbidden tokens are EXPECTED, so deliberate negative fixtures do not block.
    - Guarantee: returns True for the forbidden-classes/forbidden-terms policy files, any tests/ path, and pattern_binding_contract/input paths; False otherwise.
    - Fails: never raises (lowercase path-suffix/prefix matching only).
    - Reads: only the supplied public-relative path string.
    - Non-goal: marks a path eligible for negative-case tolerance only; does not itself authorize a token or grant export.
    """
    lowered = path.lower()
    if lowered.endswith("core/private_state_forbidden_classes.json"):
        return True
    if lowered.endswith("private_state_forbidden_terms.json"):
        return True
    if lowered.startswith("tests/") or "/tests/" in lowered:
        return True
    if "pattern_binding_contract/input" not in lowered:
        return False
    return True


def _allowed_synthetic_negative(path: str, text: str) -> bool:
    """Decide whether a forbidden-token hit at this path+text is a sanctioned negative case.

    - Teleology: distinguishes a deliberate synthetic negative fixture (non-blocking) from a real private-state leak, so honest test corpora do not fail the scan.
    - Guarantee: returns True only for an expected-negative path AND (a policy file / a tests path / text carrying a SYNTHETIC_NEGATIVE_MARKER); any non-fixture path returns False.
    - Fails: never raises (path classification plus substring membership only).
    - Reads: the public-relative path, the scanned text, and the SYNTHETIC_NEGATIVE_MARKERS constant; reads no policy file from disk.
    - Non-goal: does not authorize export — a sanctioned negative is still reported as a hit, only flagged expected_negative_case.
    """
    if not _is_expected_negative_fixture_path(path):
        return False
    lowered = path.lower()
    if lowered.endswith("core/private_state_forbidden_classes.json"):
        return True
    if lowered.endswith("private_state_forbidden_terms.json"):
        return True
    if lowered.startswith("tests/") or "/tests/" in lowered:
        return True
    return any(marker in text for marker in SYNTHETIC_NEGATIVE_MARKERS)


def _path_hit(path: str, source_context: str) -> dict[str, Any] | None:
    """Detect the structural violation of treating a public-root path as a source authority.

    - Teleology: enforces the target-only-not-source custody boundary so the public microcosm-substrate tree is never written/exported as if it were the macro source of truth.
    - Guarantee: returns None when source_context == "target"; otherwise returns a redacted hit (forbidden_class target_only_not_source, term_id microcosm_substrate_as_source_authority) when the path is a public-root path, else None.
    - Fails: never raises; a non-public-root path in a non-target context returns None.
    - Reads: the path string, the source_context flag, and the PUBLIC_ROOT_RELATIVE_PREFIXES constant.
    - Non-goal: does not read or export the file body; the hit is a path-shape custody violation, not a token leak.
    """
    if source_context == "target":
        return None
    normalized = path.replace("\\", "/")
    is_public_root_path = "microcosm-substrate" in normalized or any(
        normalized == prefix.rstrip("/") or normalized.startswith(prefix)
        for prefix in PUBLIC_ROOT_RELATIVE_PREFIXES
    )
    if is_public_root_path:
        return {
            "path": path,
            "forbidden_class": "target_only_not_source",
            "term_id": "microcosm_substrate_as_source_authority",
            "body_redacted": True,
            "remediation": "treat public root paths as target paths, not source authority",
        }
    return None


def _scan_text_with_terms(
    text: str,
    *,
    path: str,
    forbidden_classes: dict[str, Any],
    terms: list[dict[str, str]],
    source_context: str = "target",
) -> dict[str, Any]:
    """Scan one in-memory text blob against pre-flattened forbidden-token rows.

    - Teleology: the substitution-ledger core that turns a text body + term rows into a redacted hit list and a pass/blocked status, never exporting the matched excerpt.
    - Guarantee: returns status PASS when no blocking hit; BLOCKED_PUBLIC_WRITE when a target_only_not_source path hit blocks; else BLOCKED_PRIVATE; emits hits (each body_redacted, sanctioned negatives flagged expected_negative_case), forbidden_output_fields ["matched_excerpt","body"], body_redacted True, scan_scope, and anti_claim.
    - Fails: never raises; a forbidden token simply appends a redacted hit and flips status; it does not throw.
    - Reads: the supplied text, path, the term rows, and (via helpers) the scan_scope/anti_claim policy fields; opens no file.
    - Non-goal: never returns the matched excerpt or body, and PASS does not certify the text is secret-free or authorize export.
    """
    hits: list[dict[str, Any]] = []
    path_based = _path_hit(path, source_context)
    if path_based is not None:
        hits.append(path_based)

    allowed_negative = _allowed_synthetic_negative(path, text)
    for term in terms:
        if term["token"] not in text:
            continue
        hit = {
            "path": path,
            "forbidden_class": term["forbidden_class"],
            "term_id": term["term_id"],
            "body_redacted": True,
            "remediation": term["remediation"],
        }
        if allowed_negative:
            hit["expected_negative_case"] = True
        hits.append(hit)

    blocking_hits = [hit for hit in hits if not hit.get("expected_negative_case")]
    if any(hit.get("forbidden_class") == "target_only_not_source" for hit in blocking_hits):
        status = BLOCKED_PUBLIC_WRITE
    elif blocking_hits:
        status = BLOCKED_PRIVATE
    else:
        status = PASS
    return {
        "status": status,
        "hits": hits,
        "forbidden_output_fields": ["matched_excerpt", "body"],
        "body_redacted": True,
        "scan_scope": _scan_scope(forbidden_classes),
        "anti_claim": _anti_claim(forbidden_classes),
    }


def scan_text(
    text: str,
    *,
    path: str,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
) -> dict[str, Any]:
    """Public entrypoint: scan one text blob against a forbidden-class policy.

    - Teleology: the public one-shot text scanner that flattens the policy and delegates to the term-matching core for callers holding text in memory.
    - Guarantee: returns the `_scan_text_with_terms` envelope (status PASS / BLOCKED_PUBLIC_WRITE / BLOCKED_PRIVATE, redacted hits, scan_scope, anti_claim) computed against `_terms(forbidden_classes)`.
    - Fails: never raises on content; a forbidden token yields a blocked status with redacted hits, not an exception.
    - When-needed: inspect when scanning a string (not a file path) for declared forbidden tokens before public emission.
    - Reads: the supplied text, path, and forbidden_classes policy (classes/terms, scan_scope, anti_claim); opens no file.
    - Non-goal: a bounded declared-token scan, not a complete secret audit; never exports the body and PASS does not authorize release.
    """
    return _scan_text_with_terms(
        text,
        path=path,
        forbidden_classes=forbidden_classes,
        terms=_terms(forbidden_classes),
        source_context=source_context,
    )


def _merge_scan_hits(
    hits: list[dict[str, Any]], forbidden_classes: dict[str, Any]
) -> dict[str, Any]:
    """Fold many redacted hit rows into one aggregate scan-result envelope.

    - Teleology: the reducer that combines per-file/per-term hits into a single status + count envelope for multi-source scans.
    - Guarantee: returns status BLOCKED_PUBLIC_WRITE when any non-negative hit is target_only_not_source, else BLOCKED_PRIVATE when any blocking hit remains, else PASS; reports hit_count and blocking_hit_count (negatives excluded) plus body_redacted, scan_scope, and anti_claim.
    - Fails: never raises (list filtering and counting only).
    - Reads: the supplied hit rows and the scan_scope/anti_claim policy fields; opens no file.
    - Non-goal: never reconstructs a body from hits; an aggregate PASS does not authorize export or certify a complete audit.
    """
    blocking_hits = [hit for hit in hits if not hit.get("expected_negative_case")]
    if any(hit.get("forbidden_class") == "target_only_not_source" for hit in blocking_hits):
        status = BLOCKED_PUBLIC_WRITE
    elif blocking_hits:
        status = BLOCKED_PRIVATE
    else:
        status = PASS
    return {
        "status": status,
        "hits": hits,
        "hit_count": len(hits),
        "blocking_hit_count": len(blocking_hits),
        "forbidden_output_fields": ["matched_excerpt", "body"],
        "body_redacted": True,
        "scan_scope": _scan_scope(forbidden_classes),
        "anti_claim": _anti_claim(forbidden_classes),
    }


def _merge_scan_results(
    results: list[dict[str, Any]], forbidden_classes: dict[str, Any]
) -> dict[str, Any]:
    """Merge several per-source scan-result envelopes into one aggregate envelope.

    - Teleology: lets a caller combine independently produced scan results (e.g. text + json) into a single status.
    - Guarantee: concatenates every result's "hits" list and returns the `_merge_scan_hits` aggregate (status, counts, scan_scope, anti_claim).
    - Fails: never raises; a result missing "hits" contributes nothing.
    - Reads: each result's "hits" field and the forbidden_classes policy (scan_scope/anti_claim); opens no file.
    - Non-goal: a status reducer, not a re-scan; does not export bodies or authorize release.
    """
    hits: list[dict[str, Any]] = []
    for result in results:
        hits.extend(result.get("hits", []))
    return _merge_scan_hits(hits, forbidden_classes)


def _unreadable_text_result(
    *,
    path: str,
    error: OSError | UnicodeDecodeError,
    forbidden_classes: dict[str, Any],
) -> dict[str, Any]:
    """Build the blocked envelope for a text candidate that could not be read or decoded.

    - Teleology: converts an I/O or UTF-8 failure into an explicit blocked finding, so an unreadable file fails closed rather than silently passing.
    - Guarantee: returns status BLOCKED_PRIVATE with one redacted hit (forbidden_class unreadable_text_candidate; term_id text_read_failed for OSError, else utf8_decode_failed) carrying the error class and remediation, plus scan_scope and anti_claim.
    - Fails: never raises; it is the failure-handling path itself and only constructs a dict.
    - Reads: the public path, the raised error object, and the forbidden_classes scan_scope/anti_claim fields; reads no file body.
    - Non-goal: never exports the unread body; fail-closed is a safety posture, not an authorization of anything.
    """
    term_id = "utf8_decode_failed"
    remediation = "re-encode or exclude the text candidate before public scan"
    if isinstance(error, OSError):
        term_id = "text_read_failed"
        remediation = "make the text candidate readable or exclude it before public scan"
    return {
        "status": BLOCKED_PRIVATE,
        "hits": [
            {
                "path": path,
                "forbidden_class": "unreadable_text_candidate",
                "term_id": term_id,
                "error_class": error.__class__.__name__,
                "body_redacted": True,
                "remediation": remediation,
            }
        ],
        "forbidden_output_fields": ["matched_excerpt", "body"],
        "body_redacted": True,
        "scan_scope": _scan_scope(forbidden_classes),
        "anti_claim": _anti_claim(forbidden_classes),
    }


def _scan_path_with_terms(
    path: Path,
    *,
    public_path: str,
    forbidden_classes: dict[str, Any],
    terms: list[dict[str, str]],
    source_context: str,
) -> dict[str, Any]:
    """Stream one file in chunks and scan it for forbidden tokens without buffering the whole body.

    - Teleology: the bounded-memory file scanner that detects declared forbidden tokens (and negative-fixture markers) across chunk boundaries while never holding or exporting the body.
    - Guarantee: returns status PASS / BLOCKED_PUBLIC_WRITE (target_only_not_source path hit) / BLOCKED_PRIVATE with redacted hits; an overlap tail preserves cross-chunk token matches; sanctioned-negative paths/markers flag expected_negative_case; emits forbidden_output_fields, body_redacted, scan_scope, anti_claim.
    - Fails: never raises to the caller; a UnicodeDecodeError or OSError is caught and converted to the `_unreadable_text_result` blocked envelope.
    - Reads: the file at `path` in SCAN_CHUNK_SIZE chunks, the term tokens, the public_path string, and the scan_scope/anti_claim policy fields.
    - Non-goal: never returns the matched excerpt or body; only the declared tokens are matched, so PASS is not a complete secret audit or an export authorization.
    """
    matched_term_indexes: set[int] = set()
    marker_seen = False
    public_path_lower = public_path.lower()
    negative_path = _is_expected_negative_fixture_path(public_path)
    markers = (
        SYNTHETIC_NEGATIVE_MARKERS
        if negative_path
        and not public_path_lower.endswith("core/private_state_forbidden_classes.json")
        and not public_path_lower.endswith("private_state_forbidden_terms.json")
        and not public_path_lower.startswith("tests/")
        and "/tests/" not in public_path_lower
        else ()
    )
    needles = [term["token"] for term in terms] + list(markers)
    overlap = max((len(needle) for needle in needles), default=1) - 1
    chunk_size = max(1, int(SCAN_CHUNK_SIZE))
    tail = ""
    try:
        with path.open("r", encoding="utf-8") as handle:
            while True:
                chunk = handle.read(chunk_size)
                if not chunk:
                    break
                window = f"{tail}{chunk}"
                for index, term in enumerate(terms):
                    if index not in matched_term_indexes and term["token"] in window:
                        matched_term_indexes.add(index)
                if not marker_seen:
                    marker_seen = any(marker in window for marker in markers)
                tail = window[-overlap:] if overlap > 0 else ""
    except (UnicodeDecodeError, OSError) as error:
        return _unreadable_text_result(
            path=public_path,
            error=error,
            forbidden_classes=forbidden_classes,
        )

    path_based = _path_hit(public_path, source_context)
    hits: list[dict[str, Any]] = []
    if path_based is not None:
        hits.append(path_based)

    allowed_negative = negative_path and (
        public_path_lower.endswith("core/private_state_forbidden_classes.json")
        or public_path_lower.endswith("private_state_forbidden_terms.json")
        or public_path_lower.startswith("tests/")
        or "/tests/" in public_path_lower
        or marker_seen
    )
    for index, term in enumerate(terms):
        if index not in matched_term_indexes:
            continue
        hit = {
            "path": public_path,
            "forbidden_class": term["forbidden_class"],
            "term_id": term["term_id"],
            "body_redacted": True,
            "remediation": term["remediation"],
        }
        if allowed_negative:
            hit["expected_negative_case"] = True
        hits.append(hit)

    blocking_hits = [hit for hit in hits if not hit.get("expected_negative_case")]
    if any(hit.get("forbidden_class") == "target_only_not_source" for hit in blocking_hits):
        status = BLOCKED_PUBLIC_WRITE
    elif blocking_hits:
        status = BLOCKED_PRIVATE
    else:
        status = PASS
    return {
        "status": status,
        "hits": hits,
        "forbidden_output_fields": ["matched_excerpt", "body"],
        "body_redacted": True,
        "scan_scope": _scan_scope(forbidden_classes),
        "anti_claim": _anti_claim(forbidden_classes),
    }


def scan_paths(
    paths: Iterable[str | Path],
    *,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
    display_root: str | Path | None = None,
) -> dict[str, Any]:
    """Public entrypoint: scan a set of file paths for forbidden tokens, paths rendered public-safe.

    - Teleology: the import/export custody surface that walks a path set, scans each text candidate, and folds results into one redacted aggregate before public emission.
    - Guarantee: returns the `_merge_scan_hits` aggregate (status PASS / BLOCKED_PUBLIC_WRITE / BLOCKED_PRIVATE, redacted hits, scan_scope, anti_claim) plus scanned_path_count; skips symlinks, non-files, and non-text candidates; every hit path is rendered relative to the inferred/declared display_root.
    - Fails: never raises on content; an unreadable/undecodable file yields a BLOCKED_PRIVATE unreadable_text_candidate hit, not an exception.
    - When-needed: inspect before publishing or exporting a file set, to confirm no declared forbidden token or source-as-authority path violation is present.
    - Reads: each candidate file body (streamed), the forbidden_classes policy (terms, scan_scope, anti_claim), and the display_root for path normalization.
    - Escalates-to: core/private_state_forbidden_classes.json for the token policy and the private_state_scan tests for the aggregate-status contract.
    - Non-goal: a bounded declared-token scan, never a complete secret-absence certificate; never exports file bodies and PASS does not authorize release.
    """
    hits: list[dict[str, Any]] = []
    scanned = 0
    candidate_paths = (Path(raw_path) for raw_path in paths)
    if display_root is not None:
        root = Path(display_root).resolve(strict=False)
        paths_to_scan = candidate_paths
    else:
        paths_to_scan = list(candidate_paths)
        root = _infer_display_root(paths_to_scan)
    terms = _terms(forbidden_classes)
    for path in paths_to_scan:
        if path.is_symlink() or not path.is_file() or not is_text_scan_candidate(path):
            continue
        scanned += 1
        public_path = public_relative_path(path, display_root=root)
        scan_result = _scan_path_with_terms(
            path,
            public_path=public_path,
            forbidden_classes=forbidden_classes,
            terms=terms,
            source_context=source_context,
        )
        hits.extend(scan_result.get("hits", []))
    merged = _merge_scan_hits(hits, forbidden_classes)
    merged["scanned_path_count"] = scanned
    return merged


def scan_json_payload(
    payload: object,
    *,
    path: str,
    forbidden_classes: dict[str, Any],
    source_context: str = "target",
) -> dict[str, Any]:
    """Public entrypoint: serialize a JSON-able payload deterministically and scan it for forbidden tokens.

    - Teleology: lets an in-memory structure be checked for declared forbidden tokens before it is written or published, using a stable canonical serialization.
    - Guarantee: returns the `scan_text` envelope (status PASS / BLOCKED_PUBLIC_WRITE / BLOCKED_PRIVATE, redacted hits, scan_scope, anti_claim) computed over json.dumps(payload, ensure_ascii=True, sort_keys=True).
    - Fails: a non-JSON-serializable payload -> json.dumps raises TypeError; content with a forbidden token yields a blocked status, not an exception.
    - When-needed: inspect before emitting a built JSON artifact publicly, to confirm no declared forbidden token leaked into the structure.
    - Reads: the supplied payload and the forbidden_classes policy (terms, scan_scope, anti_claim); opens no file.
    - Non-goal: a bounded declared-token scan over the serialized form, never a complete secret audit; never exports the body and PASS does not authorize release.
    """
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    return scan_text(
        text,
        path=path,
        forbidden_classes=forbidden_classes,
        source_context=source_context,
    )
