# Component explorer

A local browser client for the [component API](../docs/reference/component-http-api.md),
built to the [frontend brief](../docs/guides/frontend-implementation.md). It
reads the validated component index and shows what each piece of evidence
establishes, and where it stops. It runs nothing: the API has no execution
route, and declared commands are shown as text to copy.

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

## What it shows

| Route | Screen |
|---|---|
| `/` | The evidence map: every component in its family, the twelve Dafny-verified kernels at the centre, the thread from each kernel to the component that calls its generated code, and each component's saved records. Selection is kept in `#o=`; search and filters in the query. |
| `/catalogue` | Search and combined filters, the matching total and further pages, all kept in the URL. |
| `/components/<organ_id>` | One component: its claim and limit first, then its modeled contract, retained proof, generated code, caller, declared replay and saved records, beside a chain figure that follows the reading position. |
| `/proofs/<proof_id>` | One retained proof: statement, assumptions and limits, retained verification, broken variants, generated code and fresh-check state. |
| `/coverage` | Each presence measure with its denominator and the API's own meaning; whole-claim coverage shown as unknown. |
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
`src/data.js` assembles the map's model; `src/evidence.js` words every state;
`src/map/` draws the map; `src/views/` holds the pages.

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

The layout of the evidence map is new: it follows the paper's chain from a
stated property to a saved run, from the centre outward.
