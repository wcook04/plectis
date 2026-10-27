# Practical formal verification: the component explorer

A local browser client for the [component API](../docs/reference/component-http-api.md),
built to the [frontend brief](../docs/guides/frontend-implementation.md). It
shows which computations in Plectis are proved with Dafny, how the proved code
reaches the components that call it, and every other check each component has,
with each component's write-up in plain words. It runs nothing: the API has no
execution route, and declared commands are folded away as text to copy.

## Start it

From the repository root, with Python 3.11 or newer and no installation:

```sh
python3 frontend/serve.py --start-backend
```

Then open <http://127.0.0.1:8767/>. `make explorer` does the same. Without
`--start-backend`, the explorer expects `plectis serve-components` already
listening on `127.0.0.1:8766`.

`serve.py` is the development server and the proxy configuration. It serves the
files in this directory, answers client routes with `index.html`, and forwards
every `/api/v1` request to the API unchanged: path, query, status, body and the
`ETag`, `Cache-Control` and `X-Plectis-Snapshot-Revision` headers, including
`304` responses. The page and the API share one origin, so no CORS is needed.
It accepts only `GET` and `HEAD`, listens on loopback only, and answers `502`
in plain text when the API is down. `--backend` and `--port` change the
addresses.

Its one route of its own, `/guides/component/<id>` and `/guides/core/<id>`,
serves the write-up the snapshot names for a component or a core
(`paper_modules/*.md`, or a core's formal README). It reads the file from this
checkout only after asking the API for the write-up's recorded SHA-256, and
answers `409 stale_guide` when the bytes no longer match, so a write-up is
never newer than the snapshot it is shown with. Each write-up opens with a
five-sentence block quote, "In plain terms", which the map shows on hover.

## What it shows

| Route | Screen |
|---|---|
| `/` | The map. Inside the ring: the replay checker and the three workflow cores at the centre, the twelve component kernels as flowers (one petal per proof check, a cross per rejected broken version), and a thread from each kernel to the component that calls its generated code. Outside the ring: eight coverage rings, one per kind of check, one cell per component. Hovering a component shows its plain description in the panel; choosing it opens its card. Escape or a click on empty space lets go. Selection is kept in `#o=`; search and filters in the query. |
| `/catalogue` | Search and combined filters, the matching total and further pages, all kept in the URL. |
| `/components/<organ_id>` | One component: its plain description, its limit, its proved part, the rendered write-up, past runs as dated marks, the principles it cites and its connections, beside its column of checks. |
| `/proofs/<proof_id>` | One proved computation (a component kernel or a workflow core): what it promises, the ownership repair played through where it applies, the Dafny rules as retained text, the broken versions as changed lines, the compiled code and who calls it, and what is not checked. |
| `/coverage` | The map's rings laid flat: one row of squares per kind of check, grouped by family. |
| `/graph?type=&id=` | Related records within a bounded neighbourhood, drawn and listed, with truncation stated. |

Every page shows its snapshot revision as a digest of the index, never as a
commit or a proof. Facts the API keeps apart stay apart: there is no score and
no "verified component" mark.

## Tests

```sh
node --test frontend/tests/*.test.mjs                       # loading rules and model, Node 20+
PYTHONPATH=src python3 -m pytest tests/test_frontend_server.py   # proxy and static serving
python3 frontend/tests/acceptance.py --out /tmp/explorer-acceptance   # browser run, needs Playwright
```

The acceptance run needs the explorer running (above) and Playwright for
Python. It uses real responses for search, paging, combined filters, empty
results, direct links, unavailable records, unknown IDs and truncated graphs,
and controlled responses for a stale cursor, a revision change between parts
of a page, a slow superseded search, network failure and an incompatible
schema. It also checks keyboard use and phone width, and writes screenshots
and `report.json`.

## Source

There is no build step and no dependency. `src/main.js` routes; `src/api.js`
holds the loading rules (schema check, error kinds, superseded requests,
cursor paging within one revision, parts that must share a revision);
`src/data.js` builds the model from one `/api/v1/overview` response;
`src/evidence.js` words every state and defines the coverage rings;
`src/markdown.js` renders write-ups as text, never as HTML; `src/map/` draws
the map; `src/views/` holds the pages.

`BACKEND_REQUESTS.md` lists what this pass needed from the API and could not
get.

## Where the visuals come from

The map and pages adapt existing Plectis front ends rather than new drawings:

| Adapted from | Used for |
|---|---|
| Plectis universe map, `ai_workflow` `tools/meta/dissemination/maths_site_assets/universe.js` at `5d5a287058` | Camera, smooth zoom flight, focus fade, ember light, evidence pulse, reticles, arc lettering, Oklab colour mixing, capped canvas backing store, centre-out opening (`src/map/engine.js`, `src/map/color.js`) |
| Plectis system map, `sites/microcosm/assets/system-map.js` at `17c49004bd` | The five marks for how a component is backed, their words, and the family order (`src/evidence.js`, `src/dom.js`) |
| Plectis explorer frame, `sites/microcosm/assets/explorer.js` at `1f6c2e3d00`, and `style.css` at `da3ea006da` | Full screen, fit and zoom, folding panel, narrow layout; tokens, header and explorer layout (`src/frame.js`, `assets/`) |
| Plectis web fonts, `sites/microcosm/assets/fonts` at `4aff507d35` | STIX Two Text and Source Sans 3 subsets, under the SIL Open Font Licence (`assets/fonts/`) |
| Lean Exposition, `site/src/checks/CheckMap.tsx` and `site/src/reader/ReaderPage.tsx` at `6f62294` | One square per item for coverage; the figure that follows the reading position (`src/views/coverage.js`, `src/views/chain.js`) |
| Plectis Atlas, `DESIGN.md` "Evidence states stay distinct" at `3f0f093a` | Unknown is neither red nor green; an unrecognised value is named, not coloured (`src/evidence.js`) |

The layout of the map is new. Inside the ring it follows the paper's chain from
a stated property to the component that runs the proved code; outside it, the
coverage rings read like the tracks of a circular genome plot.
