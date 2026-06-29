from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SITE_ROOT_URL = "https://wcook04.github.io/plectis/"
SOURCE_OF_RECORD = "https://github.com/wcook04/plectis"

JSON_PACKET_PATHS = (
    "content-manifest.json",
    "object-map.json",
    "projection-status.json",
    "microcosm-ai-reader-digest.json",
    "microcosm-ai-review-packet.json",
    "microcosm-ai-reader-complete.json",
    "plectis-ai-reader-digest.json",
    "plectis-ai-review-packet.json",
    "plectis-ai-reader-complete.json",
)
HTML_PATHS = ("index.html", "plectis.html")
TEXT_PATHS = ("llms.txt",)
REQUIRED_PATHS = JSON_PACKET_PATHS + HTML_PATHS + TEXT_PATHS
HASHED_PATHS = tuple(
    path
    for path in REQUIRED_PATHS
    if path not in {"projection-status.json", "plectis.html"}
)
PACKET_PATHS = (
    "microcosm-ai-reader-digest.json",
    "microcosm-ai-review-packet.json",
    "microcosm-ai-reader-complete.json",
    "plectis-ai-reader-digest.json",
    "plectis-ai-review-packet.json",
    "plectis-ai-reader-complete.json",
)


@dataclass(frozen=True)
class SiteSnapshot:
    label: str
    files: dict[str, bytes]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _source_counts(root: Path) -> dict[str, int]:
    registry = _read_json(root / "core/organ_registry.json")
    accepted = [
        row
        for row in registry.get("implemented_organs", [])
        if isinstance(row, dict) and row.get("status") == "accepted_current_authority"
    ]
    families = _read_json(root / "core/organ_families.json").get("families", [])
    public_paper_modules = _read_json(root / "core/paper_module_capsules.json").get(
        "paper_modules", []
    )
    standards = _read_json(root / "core/standards_registry.json")
    standard_count = int(standards.get("standard_count") or 0)
    return {
        "component_count": len(accepted),
        "family_count": len(families),
        "paper_module_count": len(public_paper_modules),
        "standard_count": standard_count,
    }


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _git_ref_exists(root: Path, ref: str) -> bool:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "rev-parse",
            "--verify",
            "--quiet",
            f"{ref}^{{commit}}",
        ],
        capture_output=True,
    )
    return result.returncode == 0


def _remote_branch_ref(root: Path, ref: str) -> tuple[str, str, str] | None:
    prefix = "refs/remotes/"
    if ref.startswith(prefix):
        remainder = ref[len(prefix) :]
        remote, separator, branch = remainder.partition("/")
        target_ref = ref
    else:
        remote, separator, branch = ref.partition("/")
        target_ref = f"refs/remotes/{remote}/{branch}"
    if not separator or not remote or not branch:
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", remote],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return remote, branch, target_ref


def _ensure_gh_pages_ref(root: Path, ref: str) -> None:
    if _git_ref_exists(root, ref):
        return
    remote_ref = _remote_branch_ref(root, ref)
    if remote_ref is None:
        raise RuntimeError(
            f"cannot resolve {ref!r}; fetch gh-pages or use --site-dir/--site-url"
        )
    remote, branch, target_ref = remote_ref
    result = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "fetch",
            "--depth=1",
            "--no-tags",
            remote,
            f"{branch}:{target_ref}",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not _git_ref_exists(root, ref):
        detail = result.stderr.strip() or result.stdout.strip()
        suffix = f": {detail}" if detail else ""
        raise RuntimeError(
            f"cannot resolve {ref!r} after fetching {remote}/{branch}{suffix}"
        )


def _read_gh_pages(ref: str, paths: tuple[str, ...], root: Path) -> SiteSnapshot:
    _ensure_gh_pages_ref(root, ref)
    files: dict[str, bytes] = {}
    for rel in paths:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "show", f"{ref}:{rel}"],
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RuntimeError(
                f"cannot read {rel!r} from {ref!r}; fetch gh-pages or use --site-dir/--site-url"
            ) from exc
        files[rel] = result.stdout
    return SiteSnapshot(label=f"git:{ref}", files=files)


def _read_site_dir(site_dir: Path, paths: tuple[str, ...]) -> SiteSnapshot:
    files: dict[str, bytes] = {}
    for rel in paths:
        path = site_dir / rel
        if not path.is_file():
            raise RuntimeError(f"site dir missing {rel}: {site_dir}")
        files[rel] = path.read_bytes()
    return SiteSnapshot(label=f"dir:{site_dir}", files=files)


def _read_site_url(base_url: str, paths: tuple[str, ...], timeout: float) -> SiteSnapshot:
    base = base_url.rstrip("/") + "/"
    files: dict[str, bytes] = {}
    for rel in paths:
        url = base + rel
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status >= 400:
                    raise RuntimeError(f"{url} returned HTTP {response.status}")
                files[rel] = response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"cannot fetch {url}: {exc}") from exc
    return SiteSnapshot(label=base, files=files)


def _json_from_snapshot(snapshot: SiteSnapshot) -> tuple[dict[str, Any], list[dict[str, str]]]:
    payloads: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    for rel in JSON_PACKET_PATHS:
        try:
            payloads[rel] = json.loads(snapshot.files[rel].decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - report the parser failure, do not hide it.
            errors.append(
                {
                    "code": "json_parse_failed",
                    "path": rel,
                    "message": str(exc),
                }
            )
    return payloads, errors


def _coverage_count(payload: dict[str, Any], kind: str) -> int | None:
    for row in payload.get("coverage", []):
        if isinstance(row, dict) and row.get("kind") == kind:
            value = row.get("object_count")
            return int(value) if isinstance(value, int) else None
    return None


def _site_field(payload: dict[str, Any], key: str) -> Any:
    site = payload.get("site")
    if isinstance(site, dict):
        return site.get(key)
    return None


def _packet_authority_errors(payload: dict[str, Any], rel: str) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if "public_source_slice_distribution_authorized" in payload:
        if payload.get("public_source_slice_distribution_authorized") is not True:
            errors.append(
                {
                    "code": "packet_distribution_authority_mismatch",
                    "path": rel,
                    "field": "public_source_slice_distribution_authorized",
                    "expected": True,
                    "actual": payload.get("public_source_slice_distribution_authorized"),
                }
            )
    elif payload.get("publication_authorized") is not True:
        errors.append(
            {
                "code": "packet_publication_state_mismatch",
                "path": rel,
                "expected": True,
                "actual": payload.get("publication_authorized"),
            }
        )
    if (
        "release_authority_granted" in payload
        and payload.get("release_authority_granted") is not False
    ):
        errors.append(
            {
                "code": "packet_release_authority_mismatch",
                "path": rel,
                "field": "release_authority_granted",
                "expected": False,
                "actual": payload.get("release_authority_granted"),
            }
        )
    return errors


def _check_snapshot(
    snapshot: SiteSnapshot,
    *,
    source_counts: dict[str, int],
    compare_to: SiteSnapshot | None = None,
) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    payloads, json_errors = _json_from_snapshot(snapshot)
    errors.extend(json_errors)
    if json_errors:
        return {
            "label": snapshot.label,
            "status": "blocked",
            "errors": errors,
            "parsed_json_count": len(payloads),
        }

    projection = payloads["projection-status.json"]
    hashes = (
        projection.get("artifact_identity", {})
        .get("exact_byte_sha256_by_path", {})
    )
    for rel in HASHED_PATHS:
        row = hashes.get(rel)
        if not isinstance(row, dict):
            errors.append({"code": "missing_projection_hash", "path": rel})
            continue
        expected_hash = row.get("sha256")
        expected_bytes = row.get("byte_count")
        actual = snapshot.files[rel]
        actual_hash = _sha256(actual)
        if expected_hash != actual_hash:
            errors.append(
                {
                    "code": "projection_hash_mismatch",
                    "path": rel,
                    "expected": expected_hash,
                    "actual": actual_hash,
                }
            )
        if expected_bytes != len(actual):
            errors.append(
                {
                    "code": "projection_byte_count_mismatch",
                    "path": rel,
                    "expected": expected_bytes,
                    "actual": len(actual),
                }
            )

    if compare_to is not None:
        for rel in REQUIRED_PATHS:
            actual_hash = _sha256(snapshot.files[rel])
            other_hash = _sha256(compare_to.files[rel])
            if actual_hash != other_hash:
                errors.append(
                    {
                        "code": "live_branch_byte_mismatch",
                        "path": rel,
                        "expected": actual_hash,
                        "actual": other_hash,
                        "other": compare_to.label,
                    }
                )

    for rel in PACKET_PATHS:
        payload = payloads[rel]
        counts = payload.get("counts", {})
        for key in ("component_count", "paper_module_count"):
            if counts.get(key) != source_counts[key]:
                errors.append(
                    {
                        "code": "packet_count_mismatch",
                        "path": rel,
                        "field": f"counts.{key}",
                        "expected": source_counts[key],
                        "actual": counts.get(key),
                    }
                )
        if rel not in {
            "microcosm-ai-reader-complete.json",
            "plectis-ai-reader-complete.json",
        }:
            if counts.get("family_count") != source_counts["family_count"]:
                errors.append(
                    {
                        "code": "packet_count_mismatch",
                        "path": rel,
                        "field": "counts.family_count",
                        "expected": source_counts["family_count"],
                        "actual": counts.get("family_count"),
                    }
                )
        for key, expected in (
            ("source_of_record", SOURCE_OF_RECORD),
            ("runtime_backend", "none"),
            ("browser_connect_src", "none"),
        ):
            actual = _site_field(payload, key)
            if actual != expected:
                errors.append(
                    {
                        "code": "packet_site_field_mismatch",
                        "path": rel,
                        "field": f"site.{key}",
                        "expected": expected,
                        "actual": actual,
                    }
                )
        errors.extend(_packet_authority_errors(payload, rel))

    content_manifest = payloads["content-manifest.json"]
    arch_summary = (
        content_manifest.get("architecture_graph_scene", {}).get("summary", {})
    )
    for field, expected_key in (
        ("component_count", "component_count"),
        ("area_count", "family_count"),
    ):
        actual = arch_summary.get(field)
        expected = source_counts[expected_key]
        if actual != expected:
            errors.append(
                {
                    "code": "content_manifest_count_mismatch",
                    "field": f"architecture_graph_scene.summary.{field}",
                    "expected": expected,
                    "actual": actual,
                }
            )
    object_map = payloads["object-map.json"]
    if _coverage_count(object_map, "component") != source_counts["component_count"]:
        errors.append(
            {
                "code": "object_map_component_count_mismatch",
                "expected": source_counts["component_count"],
                "actual": _coverage_count(object_map, "component"),
            }
        )
    if _coverage_count(object_map, "paper_module") != source_counts["paper_module_count"]:
        errors.append(
            {
                "code": "object_map_paper_module_count_mismatch",
                "expected": source_counts["paper_module_count"],
                "actual": _coverage_count(object_map, "paper_module"),
            }
        )

    required_html_phrases = (
        f'data-mc-fact="component_count">{source_counts["component_count"]}',
        SOURCE_OF_RECORD,
        "no hosted service",
        "plectis-ai-reader-digest.json",
        "plectis-ai-review-packet.json",
        "llms.txt",
    )
    for rel in HTML_PATHS:
        text = snapshot.files[rel].decode("utf-8", errors="replace")
        for phrase in required_html_phrases:
            if phrase not in text:
                errors.append(
                    {
                        "code": "html_required_phrase_missing",
                        "path": rel,
                        "phrase": phrase,
                    }
                )

    return {
        "label": snapshot.label,
        "status": "blocked" if errors else "pass",
        "errors": errors,
        "source_counts": source_counts,
        "checked_paths": list(REQUIRED_PATHS),
        "hash_checked_paths": list(HASHED_PATHS),
    }


def check_public_site_parity(
    *,
    root: Path,
    gh_pages_ref: str | None = None,
    site_dir: Path | None = None,
    site_url: str | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    sources = [bool(gh_pages_ref), bool(site_dir)]
    if sum(sources) != 1:
        raise ValueError("provide exactly one of gh_pages_ref or site_dir")
    counts = _source_counts(root)
    if site_dir is not None:
        primary = _read_site_dir(site_dir, REQUIRED_PATHS)
    else:
        assert gh_pages_ref is not None
        primary = _read_gh_pages(gh_pages_ref, REQUIRED_PATHS, root)
    live = _read_site_url(site_url, REQUIRED_PATHS, timeout) if site_url else None
    primary_receipt = _check_snapshot(primary, source_counts=counts, compare_to=live)
    receipts = [primary_receipt]
    if live is not None:
        receipts.append(_check_snapshot(live, source_counts=counts))
    errors = [err for receipt in receipts for err in receipt["errors"]]
    return {
        "schema_version": "plectis_public_site_parity_receipt_v1",
        "status": "blocked" if errors else "pass",
        "source_counts": counts,
        "primary": primary.label,
        "live": live.label if live else None,
        "receipts": receipts,
        "error_count": len(errors),
        "errors": errors,
    }


def _format(receipt: dict[str, Any]) -> str:
    lines = [
        f"Plectis public site parity: {receipt.get('status', 'unknown')}",
        f"primary: {receipt.get('primary') or 'unavailable'}",
    ]
    if receipt.get("live"):
        lines.append(f"live: {receipt['live']}")
    counts = receipt.get("source_counts")
    if isinstance(counts, dict):
        lines.append(
            "source counts: "
            f"components={counts.get('component_count')} "
            f"families={counts.get('family_count')} "
            f"paper_modules={counts.get('paper_module_count')}"
        )
    errors = receipt.get("errors") or []
    if errors:
        lines.append("errors:")
        for err in errors[:20]:
            lines.append("  - " + json.dumps(err, sort_keys=True))
        if len(errors) > 20:
            lines.append(f"  ... {len(errors) - 20} more")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate that the gh-pages/deployed Plectis public packets agree "
            "with the source registry counts, boundary fields, and projection hashes."
        )
    )
    parser.add_argument("--root", default=".", help="Plectis source root")
    parser.add_argument(
        "--gh-pages-ref",
        default="origin/gh-pages",
        help="git ref containing the generated public site",
    )
    parser.add_argument("--site-dir", help="local generated site directory")
    parser.add_argument(
        "--live-url",
        default=None,
        help="optional deployed site URL to byte-compare against the primary source",
    )
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        receipt = check_public_site_parity(
            root=Path(args.root).resolve(),
            gh_pages_ref=None if args.site_dir else args.gh_pages_ref,
            site_dir=Path(args.site_dir).resolve() if args.site_dir else None,
            site_url=args.live_url,
            timeout=args.timeout,
        )
    except Exception as exc:  # noqa: BLE001 - CLI should return a receipt-shaped failure.
        receipt = {
            "schema_version": "plectis_public_site_parity_receipt_v1",
            "status": "blocked",
            "error_count": 1,
            "errors": [{"code": "public_site_parity_exception", "message": str(exc)}],
        }

    print(json.dumps(receipt, indent=2, sort_keys=True) if args.json else _format(receipt))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
