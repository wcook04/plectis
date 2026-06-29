from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from microcosm_core import cli
from microcosm_core import public_site_parity

ROOT = Path(__file__).resolve().parents[1]


def _source_counts() -> dict[str, int]:
    return public_site_parity._source_counts(ROOT)


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_snapshot(site_dir: Path, *, component_count: int | None = None) -> None:
    counts = _source_counts()
    if component_count is not None:
        counts = {**counts, "component_count": component_count}
    site = {
        "title": "Plectis",
        "source_of_record": public_site_parity.SOURCE_OF_RECORD,
        "runtime_backend": "none",
        "browser_connect_src": "none",
    }
    packet_counts = {
        "component_count": counts["component_count"],
        "family_count": counts["family_count"],
        "paper_module_count": counts["paper_module_count"],
    }
    complete_counts = {
        "component_count": counts["component_count"],
        "paper_module_count": counts["paper_module_count"],
    }
    _write_json(
        site_dir / "content-manifest.json",
        {
            "architecture_graph_scene": {
                "summary": {
                    "area_count": counts["family_count"],
                    "component_count": counts["component_count"],
                }
            }
        },
    )
    _write_json(
        site_dir / "object-map.json",
        {
            "coverage": [
                {"kind": "component", "object_count": counts["component_count"]},
                {"kind": "paper_module", "object_count": counts["paper_module_count"]},
            ]
        },
    )
    for name, payload_counts in (
        ("microcosm-ai-reader-digest.json", packet_counts),
        ("microcosm-ai-review-packet.json", packet_counts),
        ("microcosm-ai-reader-complete.json", complete_counts),
        ("plectis-ai-reader-digest.json", packet_counts),
        ("plectis-ai-review-packet.json", packet_counts),
        ("plectis-ai-reader-complete.json", complete_counts),
    ):
        _write_json(
            site_dir / name,
            {
                "counts": payload_counts,
                "publication_authorized": True,
                "site": site,
            },
        )
    html = (
        '<span data-mc-fact="component_count">'
        f'{counts["component_count"]}</span> '
        f'{public_site_parity.SOURCE_OF_RECORD} no hosted service '
        "plectis-ai-reader-digest.json plectis-ai-review-packet.json llms.txt"
    )
    (site_dir / "index.html").write_text(html, encoding="utf-8")
    (site_dir / "plectis.html").write_text(html, encoding="utf-8")
    (site_dir / "llms.txt").write_text("Plectis public packet\n", encoding="utf-8")

    hashes = {}
    for rel in public_site_parity.HASHED_PATHS:
        data = (site_dir / rel).read_bytes()
        hashes[rel] = {"byte_count": len(data), "sha256": _sha(data)}
    _write_json(
        site_dir / "projection-status.json",
        {
            "artifact_identity": {"exact_byte_sha256_by_path": hashes},
            "ai_orientation_packet": {
                "primary_public_handoff": "plectis-ai-reader-digest.json",
                "advanced_public_handoff": "plectis-ai-review-packet.json",
            },
        },
    )


def test_public_site_parity_accepts_matching_snapshot(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    _write_snapshot(site_dir)

    receipt = public_site_parity.check_public_site_parity(root=ROOT, site_dir=site_dir)

    assert receipt["status"] == "pass"
    assert receipt["error_count"] == 0
    assert receipt["source_counts"]["component_count"] == _source_counts()["component_count"]


def test_public_site_parity_blocks_malformed_download_packet(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    _write_snapshot(site_dir)
    (site_dir / "microcosm-ai-review-packet.json").write_text('{"counts": ', encoding="utf-8")

    receipt = public_site_parity.check_public_site_parity(root=ROOT, site_dir=site_dir)

    assert receipt["status"] == "blocked"
    assert any(error["code"] == "json_parse_failed" for error in receipt["errors"])


def test_public_site_parity_blocks_component_count_drift(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    _write_snapshot(site_dir, component_count=_source_counts()["component_count"] - 1)

    receipt = public_site_parity.check_public_site_parity(root=ROOT, site_dir=site_dir)

    assert receipt["status"] == "blocked"
    assert any(error["code"].endswith("count_mismatch") for error in receipt["errors"])


def test_public_site_parity_blocks_stale_projection_hash(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    _write_snapshot(site_dir)
    (site_dir / "llms.txt").write_text("changed after projection\n", encoding="utf-8")

    receipt = public_site_parity.check_public_site_parity(root=ROOT, site_dir=site_dir)

    assert receipt["status"] == "blocked"
    assert any(
        error["code"] == "projection_hash_mismatch" and error["path"] == "llms.txt"
        for error in receipt["errors"]
    )


def test_public_site_parity_cli_exposes_source_checkout_command(
    tmp_path: Path,
    capsys,
) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    _write_snapshot(site_dir)

    status = cli.main(
        [
            "public-site-parity",
            "--root",
            str(ROOT),
            "--site-dir",
            str(site_dir),
            "--live-url",
            "",
        ]
    )

    output = capsys.readouterr().out
    assert status == 0
    assert "Plectis public site parity: pass" in output
