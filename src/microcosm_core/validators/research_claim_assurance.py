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
    resolved = Path(path).expanduser().resolve(strict=False)
    start = resolved if resolved.is_dir() else resolved.parent
    for candidate in (start, *start.parents):
        if (candidate / STD_MICROCOSM_REL).is_file() and (
            candidate / "microcosm-substrate"
        ).is_dir():
            return candidate
    return resolved if resolved.is_dir() else Path.cwd().resolve(strict=False)


def _display(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve(strict=False).relative_to(
            repo_root.resolve(strict=False)
        ).as_posix()
    except ValueError:
        return path.as_posix()


def _as_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _as_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if str(value or "").strip():
        return [str(value).strip()]
    return []


def _resolve_ref(repo_root: Path, ref: str) -> Path:
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
    text = " ".join(_as_string_list(value)).lower()
    return bool(text) and any(marker in text for marker in NEGATIVE_FLOOR_MARKERS)


def _authority_ceiling_looks_real(value: Any) -> bool:
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
    return any(pattern.search(text) for pattern in OVERCLAIM_PATTERNS)


def _load_json_object(path: Path) -> dict[str, Any] | None:
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
    if not issues:
        return "allowed"
    priority = {verdict: index for index, verdict in enumerate(EXPECTED_VERDICTS)}
    return min(
        (str(issue.get("verdict") or "missing_witness") for issue in issues),
        key=lambda verdict: priority.get(verdict, len(priority)),
    )


def audit_research_claim_assurance(repo_root: str | Path) -> dict[str, Any]:
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
