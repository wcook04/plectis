"""Validate that the public site still mirrors the checked-in Plectis source.

This module is the parity guard for the static public shell. It compares a
generated site snapshot from `gh-pages` or a local directory, optionally checks
the deployed URL byte-for-byte against that primary snapshot, and verifies that
public JSON packets, HTML, and text files still match the source registry counts
and authority fields.

Teleology: keep the browsable public site from drifting away from the source
  registries and projection-status hashes it claims to publish.
Guarantee: produces a receipt-shaped dictionary with explicit error rows
  instead of silently accepting missing packets, stale byte hashes, or weakened
  publication authority fields.
Fails: CLI execution converts unexpected parity exceptions into a blocked
  receipt; lower-level helpers propagate filesystem, git, URL, and JSON errors
  unless their contract explicitly returns error rows.
Non-goal: does not build the public site, authorize release, deploy hosting,
  or decide that the source registries themselves are correct.
"""

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
    """An immutable byte snapshot of one public-site source.

    `label` names where the bytes came from, such as a git ref, local directory,
    or URL base. `files` keeps the raw bytes by relative public path so JSON,
    HTML phrase checks, byte hashes, and live-site comparison all inspect the
    same captured content.

    Teleology: carry a named byte capture through every parity check without
      mixing git, directory, and live URL provenance.
    Guarantee: dataclass construction stores the caller-provided `label` and
      `files` mapping and frozen instances reject attribute reassignment.
    Fails: construction raises the normal dataclass `TypeError` when required
      fields are missing; frozen assignment raises `FrozenInstanceError`.
    Reads: constructor arguments only.
    Writes: one immutable `SiteSnapshot` instance.
    Non-goal: does not validate that required paths exist or that file bytes
      match projection-status; reader helpers and `_check_snapshot` do that.
    """

    label: str
    files: dict[str, bytes]


def _read_json(path: Path) -> Any:
    """Read a UTF-8 JSON authority file from the source checkout.

    Teleology: keep source-count derivation on normal JSON parsing instead of
      ad hoc text inspection.
    Guarantee: returns the decoded JSON value exactly as `json.loads` parses
      it.
    Fails: propagates filesystem, encoding, and JSON parse errors to the
      caller; no receipt wrapping happens at this layer.
    Reads: `path`.
    Writes: return value only.
    """

    return json.loads(path.read_text(encoding="utf-8"))


def _source_counts(root: Path) -> dict[str, int]:
    """Derive the source counts that public packets are expected to publish.

    Teleology: make the parity check compare the site against current public
      registries, not against stale constants inside this verifier.
    Guarantee: counts accepted-current organs, public organ families, paper
      module capsules, and the standards registry's declared count.
    Fails: propagates missing or malformed registry files; callers treat that
      as a blocked parity run.
    Reads: `core/organ_registry.json`, `core/organ_families.json`,
      `core/paper_module_capsules.json`, and `core/standards_registry.json`
      under `root`.
    Writes: return value only.
    """

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
    """Return the projection-status hash spelling for a byte payload.

    Teleology: centralize the `sha256:<hex>` format used by
      `projection-status.json` and byte comparison rows.
    Guarantee: deterministic for identical bytes and independent of text
      encoding.
    Fails: never raises for a bytes argument.
    Reads: `data`.
    Writes: return value only.
    """

    return "sha256:" + hashlib.sha256(data).hexdigest()


def _git_ref_exists(root: Path, ref: str) -> bool:
    """Check whether `ref` resolves to a commit in the local checkout.

    Teleology: distinguish a usable local ref from a gh-pages ref that still
      needs a targeted fetch.
    Guarantee: returns True only when `git rev-parse --verify --quiet` accepts
      the ref as a commit.
    Fails: git execution failures are represented as False by the return code;
      no exception is raised for an unresolved ref.
    Reads: the git repository rooted at `root`.
    Writes: return value only.
    """

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
    """Resolve a remote branch spelling into fetch coordinates.

    Teleology: accept both `origin/gh-pages` and
      `refs/remotes/origin/gh-pages` without duplicating parsing at the fetch
      site.
    Guarantee: returns `(remote, branch, target_ref)` only when the remote is
      configured and the ref includes both remote and branch segments.
    Fails: returns None for malformed refs or unknown remotes; git stderr is
      intentionally not surfaced here because the caller owns the user-facing
      failure.
    Reads: git remote configuration under `root`.
    Writes: return value only.
    """

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
    """Make a gh-pages-style ref available before reading files from it.

    Teleology: let the verifier run from a shallow or stale checkout by
      fetching exactly the requested remote branch when possible.
    Guarantee: returns only after `ref` resolves locally, either because it
      already existed or because the targeted fetch succeeded.
    Fails: raises RuntimeError when the ref cannot be parsed, fetched, or
      verified after fetch.
    Reads: git refs and remote configuration under `root`.
    Writes: the local remote-tracking ref targeted by the fetch.
    """

    remote_ref = _remote_branch_ref(root, ref)
    if remote_ref is None:
        if _git_ref_exists(root, ref):
            return
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
            f"+{branch}:{target_ref}",
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
    """Read required public-site files directly from a git ref.

    Teleology: validate the published branch without checking it out or
      touching the working tree.
    Guarantee: returns raw bytes for every requested relative path from
      `ref`, after ensuring the ref is available.
    Fails: raises RuntimeError when the ref is unavailable or any requested
      path cannot be shown from that ref.
    Reads: git objects under `root`.
    Writes: return value only, apart from any fetch performed by
      `_ensure_gh_pages_ref`.
    """

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
    """Capture required public-site files from a generated directory.

    Teleology: support local build verification with the same byte snapshot
      shape used for git and live URL sources.
    Guarantee: returns raw bytes for each required relative path when every
      file exists.
    Fails: raises RuntimeError on the first missing required file.
    Reads: `site_dir` and its requested child files.
    Writes: return value only.
    """

    files: dict[str, bytes] = {}
    for rel in paths:
        path = site_dir / rel
        if not path.is_file():
            raise RuntimeError(f"site dir missing {rel}: {site_dir}")
        files[rel] = path.read_bytes()
    return SiteSnapshot(label=f"dir:{site_dir}", files=files)


def _read_site_url(base_url: str, paths: tuple[str, ...], timeout: float) -> SiteSnapshot:
    """Fetch required public-site files from a deployed URL base.

    Teleology: make deployment drift visible by comparing the hosted bytes
      against the primary git or directory snapshot.
    Guarantee: returns raw response bodies for every requested path when all
      fetches complete below HTTP 400.
    Fails: raises RuntimeError on URL, timeout, or HTTP error responses.
    Reads: network responses below `base_url`.
    Writes: return value only.
    """

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
    """Parse every JSON packet from a captured site snapshot.

    Teleology: gather JSON parsing failures into receipt rows so a broken
      packet blocks parity with a concrete path and message.
    Guarantee: returns successfully parsed payloads plus one
      `json_parse_failed` row for each packet that cannot be decoded as UTF-8
      JSON.
    Fails: does not raise for packet parse failures; missing snapshot paths or
      other unexpected access failures are converted into error rows by the
      broad parser guard.
    Reads: `snapshot.files` for `JSON_PACKET_PATHS`.
    Writes: return value only.
    """

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
    """Return the object-map coverage count for one object kind.

    Teleology: keep object-map count checks focused on the `coverage` row
      schema instead of assuming positional layout.
    Guarantee: returns an integer `object_count` for the first matching kind,
      otherwise None.
    Fails: never raises for dictionary payloads with absent coverage or
      non-dict coverage rows.
    Reads: `payload["coverage"]`.
    Writes: return value only.
    """

    for row in payload.get("coverage", []):
        if isinstance(row, dict) and row.get("kind") == kind:
            value = row.get("object_count")
            return int(value) if isinstance(value, int) else None
    return None


def _site_field(payload: dict[str, Any], key: str) -> Any:
    """Read one field from a packet's `site` metadata block.

    Teleology: make source-of-record and no-runtime-backend checks tolerant of
      missing or malformed `site` blocks while still reporting mismatches.
    Guarantee: returns the requested value only when `site` is a dictionary.
    Fails: never raises for absent or non-dict `site` values.
    Reads: `payload["site"]`.
    Writes: return value only.
    """

    site = payload.get("site")
    if isinstance(site, dict):
        return site.get(key)
    return None


def _packet_authority_errors(payload: dict[str, Any], rel: str) -> list[dict[str, Any]]:
    """Check one AI-reader packet for publication and release boundary fields.

    Teleology: prevent public packets from quietly flipping from source-slice
      distribution to release authority.
    Guarantee: returns explicit mismatch rows when publication/distribution is
      not true or when `release_authority_granted` is present and not false.
    Fails: never raises for missing authority fields; absence is interpreted
      by the compatibility rules encoded here.
    Reads: authority fields in `payload`.
    Writes: return value only.
    """

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
    """Validate one captured site snapshot against source and projection truth.

    Teleology: collapse the public-shell parity contract into one receipt for
      the primary snapshot or the live snapshot.
    Guarantee: checks JSON parseability, projection-status byte hashes and
      counts, optional byte equality with another snapshot, AI-reader packet
      counts and authority fields, content-manifest and object-map counts, and
      required public HTML phrases.
    Fails: returns a `blocked` receipt with error rows for contract failures;
      malformed JSON blocks deeper packet checks because later checks require
      parsed payloads.
    Reads: `snapshot.files`, `source_counts`, and optionally `compare_to`.
    Writes: return value only.
    """

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
    """Build the public-site parity receipt for one primary site source.

    Teleology: give release and deployment checks one callable that can verify
      either a `gh-pages` ref or a local generated site directory, with optional
      deployed-site comparison.
    Guarantee: accepts exactly one primary source, derives current source
      counts from `root`, validates the primary snapshot, validates the live URL
      snapshot when supplied, and returns a receipt with aggregate errors.
    Fails: raises ValueError when source selection is ambiguous; filesystem,
      git, URL, and malformed-registry errors propagate to the CLI wrapper or
      test caller.
    Reads: source registries, the selected public-site source, and optionally
      the deployed URL.
    Writes: return value only, apart from any targeted gh-pages fetch needed
      to read the selected ref.
    Non-goal: does not build, publish, or authorize the public site.
    """

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
    """Render a parity receipt as compact terminal text.

    Teleology: keep the non-JSON CLI output readable while preserving the
      exact structured error rows operators need to debug drift.
    Guarantee: includes status, primary source, optional live source, source
      counts, and at most the first twenty errors.
    Fails: never raises for ordinary receipt dictionaries with missing fields;
      absent values are printed as unavailable or omitted.
    Reads: `receipt`.
    Writes: return value only.
    """

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
    """CLI entry point for the public-site parity guard.

    Teleology: expose the parity receipt to shell workflows that check
      gh-pages, a local site directory, or an optional live deployment.
    Guarantee: prints JSON when `--json` is present, otherwise prints the
      compact text format; returns 0 only for a passing receipt.
    Fails: catches unexpected validation exceptions and converts them into a
      blocked receipt so automation receives a stable failure shape.
    Reads: command-line arguments, source registries, selected site files, git
      refs, and optionally live HTTP responses.
    Writes: stdout and any targeted gh-pages fetch needed by the selected
      primary source.
    Non-goal: does not mutate source files, generate site artifacts, deploy
      pages, or grant release authority.
    """

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
