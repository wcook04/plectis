"""Public-safe reference normalization for standalone Plectis builders.

The public repository must be able to refresh its own source-module manifests
without importing the private macro checkout. This module carries the bounded
path/reference transformations needed by that custody lane. It deliberately
blocks credential-shaped material instead of trying to redact it into a pass.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable


POLICY_ID = "plectis_public_reference_sanitizer_v1"
MACRO_ROOT_NAME = "self-indexing-" + "cognitive-substrate"
PUBLIC_SAFE_PATH_NORMALIZED_RELATION = (
    "source_faithful_public_safe_path_normalized_copy"
)
PUBLIC_SAFE_PATH_NORMALIZED_MODE = "verified_public_macro_body_light_edit"

_RAW_SEED_ROOT_RE = re.compile(
    re.escape("obsidian/" + "okay lets do this") + r"(?:/[^\s\"']*)?",
    re.IGNORECASE,
)
_OBSIDIAN_CONFIG_RE = re.compile(r"\.obsidian/", re.IGNORECASE)
_OBSIDIAN_ROOT_RE = re.compile(r"(?<![A-Za-z0-9_.-])obsidian/", re.IGNORECASE)
_MACRO_ROOT_RE = re.compile(re.escape(MACRO_ROOT_NAME) + r"/?")
_PRIVATE_REPO_HOME_RE = re.compile(
    r"/Users/(?!(?:example|operator)(?:/|$))[^/\s\"']+/src/ai_workflow"
    r"(?P<suffix>[A-Za-z0-9._/\-]*)",
    re.IGNORECASE,
)
_PRIVATE_HOME_RE = re.compile(
    r"/Users/(?!(?:example|operator)(?:/|$))[^/\s\"']+"
    r"(?P<suffix>[A-Za-z0-9._/\-]*)",
    re.IGNORECASE,
)
_PRIVATE_TMP_RE = re.compile(
    r"(?<![A-Za-z0-9_.>/-])(?:/private)?/tmp"
    r"(?P<suffix>(?:/[A-Za-z0-9._/\-]*)?)",
    re.IGNORECASE,
)
_REPO_FRAGMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_.>/-])src/ai_workflow"
    r"(?P<suffix>[A-Za-z0-9._/\-]*)",
    re.IGNORECASE,
)
_BROWSER_TRANSPORT_RE = re.compile(
    r"\b(?:claude_app_injector|chatgpt_app_injector|operator_chrome_hud|"
    r"browser_provider_transport)\b",
    re.IGNORECASE,
)
_BROWSER_DEBUG_PORT_RE = re.compile(
    r"(?i)(?:--remote-debugging-port(?:=|\s+)|localhost:)(?:9222|9223|9224)\b"
)
_SECRET_PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH |)PRIVATE KEY-----")),
    (
        "credential_assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|secret[_-]?key)"
            r"\s*=\s*['\"][^'\"]{12,}['\"]"
        ),
    ),
)

_TRANSFORM_REASONS = {
    "repo_root_private_home_path_transform": (
        "private macro-repository home path replaced with a repo-root boundary"
    ),
    "private_home_path_transform": (
        "non-portable private home path replaced with a private-home boundary"
    ),
    "host_temp_path_transform": (
        "host temporary path replaced with a host-temp boundary"
    ),
    "repo_root_fragment_transform": (
        "macro repository fragment replaced with a repo-root boundary"
    ),
    "private_raw_seed_root_transform": (
        "private raw-seed root replaced with a private-raw-seed boundary"
    ),
    "private_obsidian_tree_transform": (
        "private Obsidian tree path replaced with a bounded public token"
    ),
    "private_macro_source_ref_transform": (
        "private macro source root replaced with non-grant provenance"
    ),
    "browser_provider_symbol_transform": (
        "host-bound browser/provider symbol replaced with a public boundary token"
    ),
    "browser_debug_port_transform": (
        "host-bound browser debug port replaced with a public boundary token"
    ),
}


@dataclass(frozen=True)
class PublicReferenceReplacement:
    original_sha256: str
    replacement: str
    treatment_class: str
    reason: str

    def to_json(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class PublicReferenceBlocker:
    token_sha256: str
    category: str
    kind: str
    treatment_class: str
    reason: str
    release_impact: str
    line: int | None
    source: str

    def to_json(self) -> dict[str, str | int | None]:
        return asdict(self)


@dataclass(frozen=True)
class PublicReferenceSanitization:
    status: str
    text: str
    replacements: tuple[PublicReferenceReplacement, ...]
    blockers: tuple[PublicReferenceBlocker, ...]
    policy_id: str = POLICY_ID

    @property
    def public_safe(self) -> bool:
        return self.status in {"pass", "transformed"} and not self.blockers


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _replacement(
    *,
    original: str,
    replacement: str,
    treatment_class: str,
) -> PublicReferenceReplacement:
    return PublicReferenceReplacement(
        original_sha256=_sha256(original),
        replacement=replacement,
        treatment_class=treatment_class,
        reason=_TRANSFORM_REASONS[treatment_class],
    )


def _substitute(
    pattern: re.Pattern[str],
    text: str,
    *,
    replacement_for: Callable[[re.Match[str]], str],
    treatment_class: str,
) -> tuple[str, list[PublicReferenceReplacement]]:
    receipts: list[PublicReferenceReplacement] = []

    def replace(match: re.Match[str]) -> str:
        replacement = str(replacement_for(match))
        receipts.append(
            _replacement(
                original=match.group(0),
                replacement=replacement,
                treatment_class=treatment_class,
            )
        )
        return replacement

    return pattern.sub(replace, text), receipts


def sanitize_public_reference_text(
    text: str,
    *,
    path: str | Path | None = None,
) -> PublicReferenceSanitization:
    """Normalize non-portable references and retain hard blockers as hashes."""

    current = text
    replacements: list[PublicReferenceReplacement] = []
    transforms = (
        (
            _PRIVATE_REPO_HOME_RE,
            lambda match: f"<repo-root>{match.group('suffix') or ''}",
            "repo_root_private_home_path_transform",
        ),
        (
            _PRIVATE_HOME_RE,
            lambda _match: "<private-home-path>",
            "private_home_path_transform",
        ),
        (
            _PRIVATE_TMP_RE,
            lambda match: f"<host-temp>{match.group('suffix') or ''}",
            "host_temp_path_transform",
        ),
        (
            _REPO_FRAGMENT_RE,
            lambda match: f"<repo-root>{match.group('suffix') or ''}",
            "repo_root_fragment_transform",
        ),
        (
            _RAW_SEED_ROOT_RE,
            lambda _match: "<private-raw-seed-root>",
            "private_raw_seed_root_transform",
        ),
        (
            _OBSIDIAN_CONFIG_RE,
            lambda _match: "<private-obsidian-config>/",
            "private_obsidian_tree_transform",
        ),
        (
            _OBSIDIAN_ROOT_RE,
            lambda _match: "<private-obsidian-root>/",
            "private_obsidian_tree_transform",
        ),
        (
            _MACRO_ROOT_RE,
            lambda match: (
                "private-macro-source/" if match.group(0).endswith("/") else "private-macro-source"
            ),
            "private_macro_source_ref_transform",
        ),
        (
            _BROWSER_TRANSPORT_RE,
            lambda _match: "<private-browser-transport-symbol>",
            "browser_provider_symbol_transform",
        ),
        (
            _BROWSER_DEBUG_PORT_RE,
            lambda _match: "<private-browser-debug-port>",
            "browser_debug_port_transform",
        ),
    )
    for pattern, replacement_for, treatment_class in transforms:
        current, rows = _substitute(
            pattern,
            current,
            replacement_for=replacement_for,
            treatment_class=treatment_class,
        )
        replacements.extend(rows)

    blockers: list[PublicReferenceBlocker] = []
    for line_number, line in enumerate(current.splitlines(), start=1):
        for kind, pattern in _SECRET_PATTERNS:
            for match in pattern.finditer(line):
                blockers.append(
                    PublicReferenceBlocker(
                        token_sha256=_sha256(match.group(0)),
                        category="secret",
                        kind=kind,
                        treatment_class="real_credential_or_secret_shape",
                        reason="credential-shaped material must be removed, not normalized",
                        release_impact="block",
                        line=line_number,
                        source="content",
                    )
                )

    status = "blocked" if blockers else "transformed" if replacements else "pass"
    return PublicReferenceSanitization(
        status=status,
        text=current,
        replacements=tuple(replacements),
        blockers=tuple(blockers),
    )


def public_safe_transform_receipt(
    result: PublicReferenceSanitization,
) -> dict[str, object]:
    """Return transformation evidence without repeating the transformed body."""

    return {
        "policy_id": result.policy_id,
        "status": result.status,
        "public_safe": result.public_safe,
        "replacement_count": len(result.replacements),
        "blocker_count": len(result.blockers),
        "transform_classes": sorted(
            {row.treatment_class for row in result.replacements}
        ),
        "replacements": [row.to_json() for row in result.replacements],
        "blockers": [row.to_json() for row in result.blockers],
        "body_text_boundary": (
            "Transform receipts record hashed originals, replacements, classes, "
            "and reasons only; body text remains in the source-module target."
        ),
    }
