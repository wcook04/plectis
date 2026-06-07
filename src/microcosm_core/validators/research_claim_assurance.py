from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from microcosm_core.receipts import write_json_atomic
from microcosm_core.schemas import read_json_strict


CHECKER_ID = "checker.microcosm.validators.research_claim_assurance"
SCHEMA_VERSION = "microcosm_research_claim_assurance_v1"
STD_MICROCOSM_REL = Path("codex/standards/std_microcosm.json")
CONTRACT_KEY = "research_mechanism_cluster_contract"
EXPECTED_VERDICTS = (
    "allowed",
    "overclaim",
    "underclaim_stale",
    "missing_witness",
    "missing_negative_floor",
    "missing_authority_ceiling",
    "blocked_by_unavailable_validation",
)
EXPECTED_OUTCOMES = (
    "missing_source_locus",
    "missing_standard",
    "missing_paper_module",
    "missing_negative_floor",
    "missing_authority_ceiling",
    "overclaim_public_copy",
    "staged_but_unvalidated",
    "blocked_by_owner_claim",
)
DEFAULT_OUTCOME_BY_VERDICT = {
    "overclaim": "overclaim_public_copy",
    "underclaim_stale": "staged_but_unvalidated",
    "missing_witness": "missing_source_locus",
    "missing_negative_floor": "missing_negative_floor",
    "missing_authority_ceiling": "missing_authority_ceiling",
    "blocked_by_unavailable_validation": "staged_but_unvalidated",
}
REQUIRED_ROW_FIELDS = (
    "cluster_id",
    "organ_id",
    "paper_module",
    "standard",
    "source_loci",
    "positive_claim",
    "required_negative_floor",
    "authority_ceiling",
)
OVERCLAIM_PATTERNS = (
    re.compile(r"\bproduction[- ]ready\b", re.IGNORECASE),
    re.compile(r"\brelease[- ]ready\b", re.IGNORECASE),
    re.compile(r"\brelease authority\b", re.IGNORECASE),
    re.compile(r"\bproof correctness\b", re.IGNORECASE),
    re.compile(r"\binvestment advice\b", re.IGNORECASE),
    re.compile(r"\bprivate[- ]root equivalence\b", re.IGNORECASE),
    re.compile(r"\bsource mutation authority\b", re.IGNORECASE),
    re.compile(r"\bwhole[- ]system correctness\b", re.IGNORECASE),
)
NEGATIVE_FLOOR_MARKERS = (
    "fail",
    "reject",
    "block",
    "refusal",
    "deny",
    "forbidden",
    "inadmissible",
    "negative",
    "wrong",
    "invalid",
    "missing",
)
CEILING_DENIAL_MARKERS = ("not_", "_not_", "not ", "false", "_only", " only")


def _repo_root_for_path(path: str | Path) -> Path:
    """Resolve the ai_workflow repo root anchoring all relative witness refs.

    - Teleology: every standard/source/test ref in the contract is repo-root-relative; this fixes that root from any path inside the tree.
    - Guarantee: returns a directory that contains both `codex/standards/std_microcosm.json` and `microcosm-substrate/`, walking upward from the given path.
    - Fails: never raises; falls back to the resolved input dir (or `Path.cwd()`) when no anchor directory is found.
    - When-needed: inspect when witness paths resolve under the wrong root or the audit silently anchors to cwd.
    - Escalates-to: `STD_MICROCOSM_REL` constant and `audit_research_claim_assurance` callers.
    """
    resolved = Path(path).expanduser().resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if (candidate / STD_MICROCOSM_REL).is_file() and (
            candidate / "microcosm-substrate"
        ).is_dir():
            return candidate
    return resolved if resolved.is_dir() else Path.cwd().resolve(strict=False)


def _display(path: Path, repo_root: Path) -> str:
    """Render a path as a repo-root-relative posix string for stable display.

    - Teleology: receipts and messages should cite portable relative loci, not host-absolute paths.
    - Guarantee: returns the path relative to `repo_root` as posix when it is under the root; otherwise returns the path's own posix form.
    - Fails: never raises; the ValueError from a non-subpath is caught and the absolute posix path is returned instead.
    - When-needed: inspect when a receipt shows an absolute or non-portable path.
    """
    try:
        return path.resolve(strict=False).relative_to(
            repo_root.resolve(strict=False)
        ).as_posix()
    except ValueError:
        return path.as_posix()


def _as_rows(value: Any) -> list[dict[str, Any]]:
    """Coerce an untyped JSON value into a clean list of dict rows.

    - Teleology: contract `rows` come from on-disk JSON of unknown shape; downstream code assumes a list of dicts.
    - Guarantee: returns a list containing only the dict members of `value`; non-list input yields `[]`.
    - Fails: never raises; a non-list or list-of-non-dicts degrades to an empty list, not an error.
    - When-needed: inspect when expected cluster rows silently vanish from the receipt.
    """
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _as_string_list(value: Any) -> list[str]:
    """Coerce a scalar-or-list JSON value into a list of non-empty trimmed strings.

    - Teleology: contract fields (witnesses, loci, refs) may be a single string or a list; normalize both to a string list.
    - Guarantee: returns trimmed, non-empty string items; a list is filtered/stripped, a truthy scalar becomes a one-element list, falsy yields `[]`.
    - Fails: never raises; empty/None/whitespace input degrades to an empty list.
    - When-needed: inspect when a present field reads as empty during witness or floor checks.
    """
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if str(value or "").strip():
        return [str(value).strip()]
    return []


def _resolve_ref(repo_root: Path, ref: str) -> Path:
    """Resolve a contract ref to an absolute path under the repo root.

    - Teleology: witness existence checks need an absolute path whether the ref is repo-relative or already absolute.
    - Guarantee: returns the ref unchanged when absolute; otherwise returns `repo_root / ref`.
    - Fails: never raises; does not touch disk, so a non-existent target still returns a Path (existence is checked by callers via `.is_file()`).
    - When-needed: inspect when a witness path is reported missing but the file exists under a different root.
    """
    candidate = Path(ref)
    return candidate if candidate.is_absolute() else repo_root / candidate


def _issue(
    cluster_id: str,
    verdict: str,
    code: str,
    detail: str,
    *,
    outcome: str | None = None,
    refs: list[str] | None = None,
) -> dict[str, Any]:
    """Construct one normalized assurance-issue record with verdict and outcome.

    - Teleology: the single factory for every violation this validator emits, so issue shape stays uniform across all checks.
    - Guarantee: returns a dict carrying cluster_id, verdict, outcome, code, detail, refs; an omitted `outcome` is filled from `DEFAULT_OUTCOME_BY_VERDICT`, defaulting to `staged_but_unvalidated`.
    - Fails: never raises; does not validate that `verdict`/`outcome` are members of the EXPECTED_* tuples — callers supply known values.
    - When-needed: inspect when an issue's outcome or refs look wrong in the receipt's `issues` list.
    """
    resolved_outcome = outcome or DEFAULT_OUTCOME_BY_VERDICT.get(
        verdict, "staged_but_unvalidated"
    )
    return {
        "cluster_id": cluster_id,
        "verdict": verdict,
        "outcome": resolved_outcome,
        "code": code,
        "detail": detail,
        "refs": refs or [],
    }


def _negative_floor_looks_real(value: Any) -> bool:
    """Heuristic: does a negative-floor field actually name failure/refusal cases.

    - Teleology: enforces that a row/standard's negative floor is substantive, not empty boilerplate, by requiring denial vocabulary.
    - Guarantee: returns True only when the joined text is non-empty AND contains at least one `NEGATIVE_FLOOR_MARKERS` token (fail/reject/block/refusal/...).
    - Fails: never raises; empty or marker-free input returns False, which callers turn into a `missing_negative_floor` issue.
    - When-needed: inspect when a populated negative floor is still flagged missing — likely lacks a marker word.
    - Escalates-to: `NEGATIVE_FLOOR_MARKERS` constant.
    """
    text = " ".join(_as_string_list(value)).lower()
    return bool(text) and any(marker in text for marker in NEGATIVE_FLOOR_MARKERS)


def _authority_ceiling_looks_real(value: Any) -> bool:
    """Heuristic: does an authority-ceiling field actually deny some authority.

    - Teleology: enforces that the ceiling encodes a real denial (a `False` capability flag or denial vocabulary), not a permissive blank.
    - Guarantee: returns True when a dict carries any boolean `False` value, OR when the serialized/scalar text contains a `CEILING_DENIAL_MARKERS` token (not_/false/only/...).
    - Fails: never raises; permissive or marker-free input returns False, which callers turn into a `missing_authority_ceiling` issue.
    - When-needed: inspect when a present ceiling is flagged missing — likely all-True flags or lacks a denial marker.
    - Escalates-to: `CEILING_DENIAL_MARKERS` constant.
    - Non-goal: a True result does not authorize release or whole-system correctness; it only confirms the ceiling field is denial-bearing.
    """
    if isinstance(value, dict):
        bool_values = [
            item for item in value.values() if isinstance(item, bool)
        ]
        if any(item is False for item in bool_values):
            return True
        text = json.dumps(value, sort_keys=True).lower()
    else:
        text = str(value or "").lower()
    return any(marker in text for marker in CEILING_DENIAL_MARKERS)


def _contains_overclaim(text: str) -> bool:
    """Detect banned overclaim phrases in a positive-claim string.

    - Teleology: blocks public-facing claims from asserting forbidden capability (production/release-ready, proof correctness, investment advice, private-root equivalence, ...).
    - Guarantee: returns True iff any `OVERCLAIM_PATTERNS` regex matches `text` (case-insensitive).
    - Fails: never raises; non-matching or empty text returns False.
    - When-needed: inspect when a claim is flagged `overclaim` or when a borderline phrase should be added to the ban list.
    - Escalates-to: `OVERCLAIM_PATTERNS` constant.
    """
    return any(pattern.search(text) for pattern in OVERCLAIM_PATTERNS)


def _load_json_object(path: Path) -> dict[str, Any] | None:
    """Strictly load a JSON file, returning None unless it parses to an object.

    - Teleology: standards and contracts must be JSON objects; this is the guarded loader the row/standard checks depend on.
    - Guarantee: returns the parsed dict when the file exists and decodes to an object; returns None when the file is absent or parses to a non-dict.
    - Fails: a malformed JSON body propagates the underlying `read_json_strict` decode error (this loader does not swallow parse errors); a missing file or non-object returns None.
    - When-needed: inspect when a standard reads as "missing" though the file is present — it may be valid JSON of the wrong top-level type.
    - Escalates-to: `microcosm_core.schemas.read_json_strict`.
    """
    if not path.is_file():
        return None
    payload = read_json_strict(path)
    return payload if isinstance(payload, dict) else None


def _standard_issues(
    repo_root: Path,
    cluster_id: str,
    standard_ref: str,
    cluster_positive_claim: str,
) -> list[dict[str, Any]]:
    """Audit one organ standard for its research-bet contract and ceiling discipline.

    - Teleology: confirms the cited Microcosm-side standard backs the cluster's claim — research_bet_contract routed through mech_036, real witnesses, negative floor, denied authority, anti-claim, validator contract, and no overclaim.
    - Guarantee: returns a list of `_issue` records (empty when the standard satisfies every check); checks include STANDARD_FILE_MISSING, RESEARCH_BET_CONTRACT_MISSING, GOVERNING_MECHANISM_STALE, REQUIRED_WITNESSES_MISSING, NEGATIVE_FLOOR_MISSING, DENIED_AUTHORITY_MISSING, POSITIVE_CLAIM_OVERCLAIM, POSITIVE_CLAIM_DIVERGES, AUTHORITY_CEILING_MISSING, ANTI_CLAIM_MISSING, VALIDATOR_CONTRACT_MISSING.
    - Fails: does not raise on data defects (they become issue records); a malformed standard JSON propagates the `read_json_strict` decode error via `_load_json_object`.
    - When-needed: inspect when a row is `missing_witness`/`overclaim`/`missing_authority_ceiling` and the cause traces to the organ standard rather than the row.
    - Escalates-to: `codex/standards/std_microcosm.json` rows' `standard` ref and the cited per-organ standard file.
    - Non-goal: passing does not authorize release or prove the organ correct; it only checks the standard's claim-accounting fields exist and are denial-bearing.
    """
    standard_path = _resolve_ref(repo_root, standard_ref)
    standard = _load_json_object(standard_path)
    if standard is None:
        return [
            _issue(
                cluster_id,
                "missing_witness",
                "STANDARD_FILE_MISSING",
                "The row's Microcosm-side standard does not resolve on disk.",
                outcome="missing_standard",
                refs=[standard_ref],
            )
        ]

    issues: list[dict[str, Any]] = []
    research_bet = standard.get("research_bet_contract")
    if not isinstance(research_bet, dict):
        issues.append(
            _issue(
                cluster_id,
                "missing_witness",
                "STANDARD_RESEARCH_BET_CONTRACT_MISSING",
                "The organ standard must carry a research_bet_contract.",
                outcome="staged_but_unvalidated",
                refs=[standard_ref],
            )
        )
    else:
        if research_bet.get("governing_mechanism") != "mech_036":
            issues.append(
                _issue(
                    cluster_id,
                    "underclaim_stale",
                    "STANDARD_GOVERNING_MECHANISM_STALE",
                    "The organ standard does not route its research bet through mech_036.",
                    outcome="staged_but_unvalidated",
                    refs=[standard_ref],
                )
            )
        if not _as_string_list(research_bet.get("required_witnesses")):
            issues.append(
                _issue(
                    cluster_id,
                    "missing_witness",
                    "STANDARD_REQUIRED_WITNESSES_MISSING",
                    "The organ standard does not name required witnesses.",
                    outcome="staged_but_unvalidated",
                    refs=[standard_ref],
                )
            )
        if not _negative_floor_looks_real(research_bet.get("negative_floor")):
            issues.append(
                _issue(
                    cluster_id,
                    "missing_negative_floor",
                    "STANDARD_NEGATIVE_FLOOR_MISSING",
                    "The organ standard does not name negative or refusal cases.",
                    outcome="missing_negative_floor",
                    refs=[standard_ref],
                )
            )
        if not _as_string_list(research_bet.get("denied_authority")):
            issues.append(
                _issue(
                    cluster_id,
                    "missing_authority_ceiling",
                    "STANDARD_DENIED_AUTHORITY_MISSING",
                    "The organ standard does not name denied authority classes.",
                    outcome="missing_authority_ceiling",
                    refs=[standard_ref],
                )
            )
        standard_claim = str(research_bet.get("positive_claim") or "")
        if _contains_overclaim(standard_claim):
            issues.append(
                _issue(
                    cluster_id,
                    "overclaim",
                    "STANDARD_POSITIVE_CLAIM_OVERCLAIM",
                    "The organ standard's positive claim contains an overclaim phrase.",
                    outcome="overclaim_public_copy",
                    refs=[standard_ref],
                )
            )
        elif standard_claim and cluster_positive_claim:
            cluster_terms = {
                token
                for token in re.findall(r"[a-z0-9_]+", cluster_positive_claim.lower())
                if len(token) >= 8
            }
            standard_terms = set(
                re.findall(r"[a-z0-9_]+", standard_claim.lower())
            )
            if cluster_terms and not cluster_terms.intersection(standard_terms):
                issues.append(
                    _issue(
                        cluster_id,
                        "underclaim_stale",
                        "STANDARD_POSITIVE_CLAIM_DIVERGES",
                        "The cluster claim and organ-standard claim no longer share a material term.",
                        outcome="staged_but_unvalidated",
                        refs=[standard_ref],
                    )
                )

    if not _authority_ceiling_looks_real(standard.get("authority_ceiling")):
        issues.append(
            _issue(
                cluster_id,
                "missing_authority_ceiling",
                "STANDARD_AUTHORITY_CEILING_MISSING",
                "The organ standard lacks a denial-bearing authority ceiling.",
                outcome="missing_authority_ceiling",
                refs=[standard_ref],
            )
        )
    if "not" not in str(standard.get("anti_claim") or "").lower():
        issues.append(
            _issue(
                cluster_id,
                "missing_authority_ceiling",
                "STANDARD_ANTI_CLAIM_MISSING",
                "The organ standard lacks a negative anti-claim sentence.",
                outcome="missing_authority_ceiling",
                refs=[standard_ref],
            )
        )
    if not isinstance(standard.get("validator_contract"), dict):
        issues.append(
            _issue(
                cluster_id,
                "blocked_by_unavailable_validation",
                "STANDARD_VALIDATOR_CONTRACT_MISSING",
                "The organ standard does not name its validator contract.",
                outcome="staged_but_unvalidated",
                refs=[standard_ref],
            )
        )
    return issues


def _row_issues(
    repo_root: Path,
    row: dict[str, Any],
    validation_probe_present: bool,
) -> list[dict[str, Any]]:
    """Audit one cluster contract row's claim accounting and witness resolution.

    - Teleology: the per-row gate of the assurance matrix — required fields present, no overclaim, real negative floor and authority ceiling, every paper/standard/source/test witness resolves on disk, a focused test is cited, and validation is not blocked.
    - Guarantee: returns a list of `_issue` records (empty when the row is fully clean); emits codes including ROW_REQUIRED_FIELDS_MISSING, ROW_POSITIVE_CLAIM_OVERCLAIM, ROW_NEGATIVE_FLOOR_MISSING, ROW_AUTHORITY_CEILING_MISSING, ROW_WITNESS_PATH_MISSING, ROW_FOCUSED_TEST_WITNESS_MISSING, CLUSTER_VALIDATION_PROBE_MISSING, ROW_OWNER_CLAIM_BLOCKS_VALIDATION, plus any from `_standard_issues`.
    - Fails: does not raise on a defective row (defects become issue records); a malformed cited standard JSON propagates the decode error via `_standard_issues`.
    - When-needed: inspect when a specific cluster's verdict is non-`allowed` and you need the exact failing field or unresolved witness.
    - Escalates-to: the `research_mechanism_cluster_contract.rows` entry in `codex/standards/std_microcosm.json` and `_standard_issues`.
    - Non-goal: passing does not authorize release or rerun the organ's own validator; it audits the row's claim-accounting and path witnesses only.
    """
    cluster_id = str(row.get("cluster_id") or "<missing_cluster_id>")
    issues: list[dict[str, Any]] = []

    missing_field_outcomes = {
        "paper_module": "missing_paper_module",
        "standard": "missing_standard",
        "source_loci": "missing_source_locus",
        "required_negative_floor": "missing_negative_floor",
        "authority_ceiling": "missing_authority_ceiling",
    }
    for field in [field for field in REQUIRED_ROW_FIELDS if field not in row]:
        issues.append(
            _issue(
                cluster_id,
                "missing_witness",
                "ROW_REQUIRED_FIELDS_MISSING",
                "The cluster row is missing required assurance fields.",
                outcome=missing_field_outcomes.get(field, "staged_but_unvalidated"),
                refs=[field],
            )
        )

    positive_claim = str(row.get("positive_claim") or "")
    if _contains_overclaim(positive_claim):
        issues.append(
            _issue(
                cluster_id,
                "overclaim",
                "ROW_POSITIVE_CLAIM_OVERCLAIM",
                "The row's positive claim contains an overclaim phrase.",
                outcome="overclaim_public_copy",
            )
        )

    if not _negative_floor_looks_real(row.get("required_negative_floor")):
        issues.append(
            _issue(
                cluster_id,
                "missing_negative_floor",
                "ROW_NEGATIVE_FLOOR_MISSING",
                "The row does not carry a denial/refusal-bearing negative floor.",
                outcome="missing_negative_floor",
            )
        )

    if not _authority_ceiling_looks_real(row.get("authority_ceiling")):
        issues.append(
            _issue(
                cluster_id,
                "missing_authority_ceiling",
                "ROW_AUTHORITY_CEILING_MISSING",
                "The row does not carry a denial-bearing authority ceiling.",
                outcome="missing_authority_ceiling",
            )
        )

    paper_ref = str(row.get("paper_module") or "")
    if paper_ref and not _resolve_ref(repo_root, paper_ref).is_file():
        issues.append(
            _issue(
                cluster_id,
                "missing_witness",
                "ROW_WITNESS_PATH_MISSING",
                "The cited paper module does not resolve.",
                outcome="missing_paper_module",
                refs=[paper_ref],
            )
        )

    standard_refs = [
        str(row.get("standard") or ""),
        str(row.get("sibling_standard") or ""),
        *_as_string_list(row.get("supporting_standards")),
    ]
    standard_missing = [
        ref
        for ref in standard_refs
        if ref and not _resolve_ref(repo_root, ref).is_file()
    ]
    if standard_missing:
        issues.append(
            _issue(
                cluster_id,
                "missing_witness",
                "ROW_WITNESS_PATH_MISSING",
                "One or more cited standard loci do not resolve.",
                outcome="missing_standard",
                refs=standard_missing,
            )
        )

    source_loci = _as_string_list(row.get("source_loci"))
    missing_source_loci = [
        ref for ref in source_loci if not _resolve_ref(repo_root, ref).is_file()
    ]
    if missing_source_loci:
        issues.append(
            _issue(
                cluster_id,
                "missing_witness",
                "ROW_WITNESS_PATH_MISSING",
                "One or more cited source or focused test loci do not resolve.",
                outcome="missing_source_locus",
                refs=missing_source_loci,
            )
        )

    if not any("/tests/" in ref or ref.startswith("microcosm-substrate/tests/") for ref in source_loci):
        issues.append(
            _issue(
                cluster_id,
                "missing_witness",
                "ROW_FOCUSED_TEST_WITNESS_MISSING",
                "The row does not cite a focused test locus.",
                outcome="missing_source_locus",
                refs=source_loci,
            )
        )

    standard_ref = str(row.get("standard") or "")
    if standard_ref:
        issues.extend(
            _standard_issues(repo_root, cluster_id, standard_ref, positive_claim)
        )

    if not validation_probe_present:
        issues.append(
            _issue(
                cluster_id,
                "blocked_by_unavailable_validation",
                "CLUSTER_VALIDATION_PROBE_MISSING",
                "The cluster contract does not expose a validation_probe command list.",
                outcome="staged_but_unvalidated",
            )
        )
    owner_claim_state = str(row.get("owner_claim_state") or "").lower()
    if row.get("blocked_by_owner_claim") is True or owner_claim_state in {
        "blocked",
        "owned_live",
        "owned_stale",
    }:
        issues.append(
            _issue(
                cluster_id,
                "blocked_by_unavailable_validation",
                "ROW_OWNER_CLAIM_BLOCKS_VALIDATION",
                "The row declares that an owner claim currently blocks validation.",
                outcome="blocked_by_owner_claim",
            )
        )
    return issues


def _verdict_for(issues: list[dict[str, Any]]) -> str:
    """Collapse a row's issue list into a single highest-priority verdict.

    - Teleology: a row carries many issues but reports one verdict; this picks the most severe by `EXPECTED_VERDICTS` order.
    - Guarantee: returns `"allowed"` for an empty list; otherwise returns the issue verdict ranked earliest in `EXPECTED_VERDICTS` (unknown verdicts sort last), defaulting a missing verdict field to `missing_witness`.
    - Fails: never raises; tolerates issues with absent/unknown verdict fields.
    - When-needed: inspect when a row's rolled-up verdict seems milder/harsher than its underlying issues.
    - Escalates-to: `EXPECTED_VERDICTS` constant.
    """
    if not issues:
        return "allowed"
    priority = {verdict: index for index, verdict in enumerate(EXPECTED_VERDICTS)}
    return min(
        (str(issue.get("verdict") or "missing_witness") for issue in issues),
        key=lambda verdict: priority.get(verdict, len(priority)),
    )


def audit_research_claim_assurance(repo_root: str | Path) -> dict[str, Any]:
    """Module entrypoint: audit the whole research-claim-assurance cluster matrix.

    - Teleology: the public claim-assurance oracle — reads `research_mechanism_cluster_contract` from std_microcosm.json and rolls every cluster row's claim accounting and witnesses into one stable receipt.
    - Guarantee: returns a receipt dict with `status` `"pass"` (zero issues) or `"blocked"`, plus schema_version/checker_id, per-row receipts, verdict/outcome/code counts, the sorted issue list, and the `authority_boundary`/`anti_claim` strings.
    - Fails: raises ValueError when std_microcosm.json is missing/non-object or lacks `research_mechanism_cluster_contract`; a malformed standard JSON propagates the `read_json_strict` decode error. All row/standard data defects are reported as issues, not exceptions.
    - When-needed: inspect for the authoritative pass/blocked verdict on the research claim matrix, or to enumerate every outstanding assurance issue.
    - Escalates-to: `codex/standards/std_microcosm.json::research_mechanism_cluster_contract` and `microcosm-substrate/tests/` focused tests for this checker.
    - Non-goal: a `pass` does NOT authorize release, rerun each organ's validator, prove mathematical correctness, give investment advice, or mutate source — see the receipt's `anti_claim`.
    """
    root = _repo_root_for_path(repo_root)
    standard = _load_json_object(root / STD_MICROCOSM_REL)
    if standard is None:
        raise ValueError(f"{STD_MICROCOSM_REL}: missing or non-object standard")
    contract = standard.get(CONTRACT_KEY)
    if not isinstance(contract, dict):
        raise ValueError(f"{STD_MICROCOSM_REL}: missing {CONTRACT_KEY}")

    rows = _as_rows(contract.get("rows"))
    validation_probe_present = bool(_as_string_list(contract.get("validation_probe")))
    row_receipts: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    for row in rows:
        row_issues = _row_issues(root, row, validation_probe_present)
        row_outcomes = sorted(
            {
                str(issue.get("outcome") or "staged_but_unvalidated")
                for issue in row_issues
            }
        )
        issues.extend(row_issues)
        row_receipts.append(
            {
                "cluster_id": row.get("cluster_id"),
                "organ_id": row.get("organ_id"),
                "verdict": _verdict_for(row_issues),
                "issue_count": len(row_issues),
                "issue_codes": sorted(str(issue["code"]) for issue in row_issues),
                "outcomes": row_outcomes,
                "paper_module": row.get("paper_module"),
                "standard": row.get("standard"),
                "source_loci": _as_string_list(row.get("source_loci")),
                "required_negative_floor": row.get("required_negative_floor"),
                "authority_ceiling": row.get("authority_ceiling"),
            }
        )

    verdict_counts: dict[str, int] = {verdict: 0 for verdict in EXPECTED_VERDICTS}
    for row in row_receipts:
        verdict = str(row["verdict"])
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
    outcome_counts: dict[str, int] = {outcome: 0 for outcome in EXPECTED_OUTCOMES}
    issue_counts: dict[str, int] = {}
    for issue in issues:
        code = str(issue["code"])
        issue_counts[code] = issue_counts.get(code, 0) + 1
        outcome = str(issue.get("outcome") or "staged_but_unvalidated")
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    status = "pass" if not issues else "blocked"
    return {
        "schema_version": SCHEMA_VERSION,
        "checker_id": CHECKER_ID,
        "status": status,
        "contract_ref": f"{STD_MICROCOSM_REL.as_posix()}::{CONTRACT_KEY}",
        "governing_mechanism": contract.get("governing_mechanism"),
        "expected_verdicts": list(EXPECTED_VERDICTS),
        "expected_outcomes": list(EXPECTED_OUTCOMES),
        "row_count": len(row_receipts),
        "issue_count": len(issues),
        "verdict_counts": dict(sorted(verdict_counts.items())),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "issue_counts_by_code": dict(sorted(issue_counts.items())),
        "rows": row_receipts,
        "issues": sorted(
            issues,
            key=lambda issue: (
                str(issue["verdict"]),
                str(issue["cluster_id"]),
                str(issue["code"]),
            ),
        ),
        "authority_boundary": (
            "read_only_research_claim_assurance_not_organ_validation_release_"
            "authority_proof_correctness_investment_advice_or_source_mutation"
        ),
        "anti_claim": (
            "This validator audits the cluster claim-accounting matrix and path/standard "
            "witnesses. It does not rerun each organ, prove mathematical correctness, "
            "authorize release, provide investment advice, or mutate source."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI wrapper: run the assurance audit, optionally write a receipt, set exit code.

    - Teleology: the command-line entry exposing `audit_research_claim_assurance` to scripts and CI with `--repo-root`, `--out`, `--json` flags.
    - Guarantee: runs the audit; writes the receipt atomically to `--out` when given; prints JSON when `--json` or no `--out`; returns 0 iff `status == "pass"`, else 1.
    - Fails: propagates ValueError from the audit (missing standard or contract) and argparse SystemExit on bad arguments; does not catch them.
    - When-needed: inspect when wiring this checker into a CI gate or reproducing a receipt from the shell.
    - Escalates-to: `audit_research_claim_assurance` and `microcosm_core.receipts.write_json_atomic`.
    """
    parser = argparse.ArgumentParser(description="Audit Microcosm research claim assurance.")
    parser.add_argument(
        "--repo-root",
        "--root",
        dest="repo_root",
        default=".",
        help="Path inside the ai_workflow repository root.",
    )
    parser.add_argument("--out", help="Optional JSON receipt path.")
    parser.add_argument("--json", action="store_true", help="Print JSON receipt.")
    args = parser.parse_args(argv)

    receipt = audit_research_claim_assurance(args.repo_root)
    if args.out:
        write_json_atomic(args.out, receipt)
    if args.json or not args.out:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
