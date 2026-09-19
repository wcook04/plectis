#!/usr/bin/env python3
"""Refresh this clone's native paper text and indexes using Pandoc.

The companion papers retain their imported bytes and provenance. This command
does not publish a revision, rebuild a PDF, or establish a mathematical claim.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import posixpath
from pathlib import Path

if __package__:
    from . import paper_corpus_renderer as renderer
    from . import build_publication_taxonomy as taxonomy
    from .check_paper_corpus import reading_route_errors
else:
    import paper_corpus_renderer as renderer
    import build_publication_taxonomy as taxonomy
    from check_paper_corpus import reading_route_errors


def safe_path(root: Path, value: str, *, suffix: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix != suffix:
        raise ValueError(f"invalid corpus path: {value}")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink in corpus path: {value}")
    current.resolve().relative_to(root.resolve())
    return current


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def refresh_route(record: dict) -> None:
    route = record.get("first_pass")
    if route is None:
        return
    sections = {section["id"]: section for section in record["sections"]}
    entries = route.get("sections", [])
    if "stated_at" in route:
        entries = [*entries, route["stated_at"]]
    for entry in entries:
        section = sections.get(entry["id"])
        if section is None:
            raise ValueError(f"{record['paper_id']}: reading section {entry['id']} disappeared")
        entry["line"] = section["line"]
        if "title" in entry:
            entry["title"] = section["title"]
        entry.pop("resolved", None)
        entry.pop("reason", None)
    route["unresolved_count"] = 0


def refresh(root: Path, *, write: bool, paper_ids: list[str] | None = None) -> dict:
    root = root.resolve()
    corpus_path = safe_path(root, "docs/papers/corpus.json", suffix=".json")
    original = json.loads(corpus_path.read_text(encoding="utf-8"))
    corpus = copy.deepcopy(original)
    records = corpus["papers"]
    native = {r["paper_id"] for r in records
              if r.get("relation_to_this_repository") == "native"}
    selected = set(paper_ids) if paper_ids else native
    if selected - native:
        raise ValueError(f"unknown or non-native paper selection: {sorted(selected - native)}")
    if not selected:
        raise ValueError("this corpus has no native papers to refresh")
    targets = {}
    for record in records:
        pdf = record.get("local_pdf")
        if pdf:
            safe_path(root, pdf, suffix=".pdf")
            targets[Path(pdf).name] = posixpath.relpath(pdf, "docs/papers/full-text")
    plan: list[tuple[Path, bytes]] = []
    for record in records:
        if record.get("paper_id") not in selected:
            continue
        source = safe_path(root, record["local_source"], suffix=".tex")
        output = safe_path(root, record["local_full_text"], suffix=".md")
        output.relative_to(root / "docs/papers/full-text")
        source_bytes = source.read_bytes()
        converted = renderer._convert(source, output.stem)
        markdown = renderer._rewrite_exported_pdf_links(converted["markdown"], targets)
        if not converted.get("title"):
            raise ValueError(f"{record['paper_id']}: manuscript title is missing")
        source_digest = digest(source_bytes)
        if source_digest != record.get("source_sha256"):
            if record.get("canonical_source_commit"):
                record["previous_published_source"] = {
                    key: record.get(key) for key in
                    ("canonical_source_commit", "canonical_source_url", "source_sha256")
                }
            record["canonical_source_commit"] = None
            record["canonical_source_pin_status"] = "local_unpublished"
            record["canonical_source_url"] = None
            record["canonical_source_raw_url"] = None
        record.update(title=converted["title"], title_source="manuscript",
                      source_sha256=source_digest, sections=converted["sections"],
                      section_count=len(converted["sections"]),
                      citations_rendered=converted["citations_rendered"])
        if converted.get("subtitle"):
            record["subtitle"] = converted["subtitle"]
        else:
            record.pop("subtitle", None)
        fallback = record.get("fallback_title_drift")
        if fallback:
            if fallback["registry_fallback"] == converted["title"]:
                record.pop("fallback_title_drift")
            else:
                fallback["manuscript_title"] = converted["title"]
        if record.get("local_pdf"):
            pdf = safe_path(root, record["local_pdf"], suffix=".pdf").read_bytes()
            record.update(pdf_sha256=digest(pdf), pdf_byte_count=len(pdf))
        refresh_route(record)
        errors = reading_route_errors(record, markdown)
        if errors:
            raise ValueError(f"{record['paper_id']}: {'; '.join(errors)}")
        plan.append((output, markdown.encode()))
    corpus = taxonomy.build(corpus, root)
    records = corpus["papers"]
    plan.extend([
        (corpus_path, (json.dumps(corpus, indent=2) + "\n").encode()),
        (safe_path(root, "docs/papers/README.md", suffix=".md"),
         renderer._readme([r for r in records if r.get("title")],
                          corpus["this_repository"], root).encode()),
    ])
    changed = []
    for path, payload in plan:
        if path.is_file() and path.read_bytes() == payload:
            continue
        changed.append(str(path.relative_to(root)))
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
    return {"status": "written" if write else ("stale" if changed else "current"),
            "native_papers": sorted(selected), "changed": changed,
            "proof_or_pdf_rebuild_performed": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--paper", action="append", help="refresh one existing native paper id")
    args = parser.parse_args()
    try:
        result = refresh(args.root, write=args.write, paper_ids=args.paper)
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        parser.exit(2, f"paper refresh: {error}\n")
    print(json.dumps(result, indent=2))
    return int(args.check and bool(result["changed"]))


if __name__ == "__main__":
    raise SystemExit(main())
