# Engine Room Annex Knowledge Router

Public exercise:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.annex_knowledge_router evaluate-fixtures --input fixtures/first_wave/engine_room_annex_knowledge_router/input --json
```

This capsule is a source-faithful public refactor of
`system/lib/annex_registry.py::route_annexes`. It demonstrates structured
routing-field priority, weaker family/open-first text matches, curated note
matches, domain filtering, and explainable `match_breakdown` output over a
sanitized catalog. It does not ship the private annex corpus or clone upstream
repositories.
