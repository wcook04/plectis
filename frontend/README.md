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

Write-ups now come from the API snapshot. Overview component rows carry the
plain-language lead and its availability; component, core and proof detail
responses carry the bounded guide text, source reference, SHA-256 and
availability. The browser requests a full guide only when the reader selects
or opens that record. It neither prefetches every component's write-up nor
reads a guide from the checkout. Older indexes without retained guide text
show that absence explicitly. The `/guides/component/<id>` and
`/guides/core/<id>` development routes remain for compatibility, but the
browser client does not use them.

## Static copy

```sh
python3 frontend/export_static.py --out /path/to/explorer   # or: make explorer-static
```

writes the explorer as plain files for a host with no server, such as GitHub
Pages. It starts the API and `serve.py` from this checkout on free loopback
ports, saves every answer the explorer can request under `api/v1/` (metadata,
the overview and its map view, coverage, every component, proof and core with
its write-up, the doctrine and every rule, the full component list and the
typed graph), and copies `assets/` and `src/`. In the copy, `src/static-api.js` answers the same API URLs from
those files and works out search, filters, paging and graph neighbourhoods
in the browser. The export fails, and writes nothing, unless those answers
equal the server's for every graph node, every filter value, a set of
searches at three page sizes, every doctrine rule, and the error cases.

Each page has its own HTML file with relative paths (`catalogue.html`,
`components/<id>.html`, `proofs/<id>.html`), so the copy works under any
subpath and a direct link opens the right page. `src/base.js` reads the mount
point from its own URL. The snapshot revision on every page is the served
index's digest, unchanged; the map's footer adds that it is a static copy and
the date it was exported. `export.json` records the revision, the commit, the
time and the SHA-256 of every file.

The public copy is at
<https://wcook04.github.io/practical-formal-verification/explorer/>, in the
`explorer/` folder of the `gh-pages` branch. The site deploy adds and updates
files there without deleting others, so the folder stays until it is replaced:
export again into a clone of `gh-pages` and push the `explorer/` change.

## Header

The header starts with the family lockup shared by Will Cook's websites
(`docs/family.md`, "The lockup", in
[wcook04.github.io](https://github.com/wcook04/wcook04.github.io)): the
Plectis plait, which opens the home page <https://wcook04.github.io/>, a short
upright rule, then the proof flower and "Practical Formal Verification", which
open the map. `assets/plectis.svg` is a copy of that repository's
`assets/family/marks/plectis.svg`; the lockup rules in `assets/app.css` are a
copy of its `family.css` block, with the `--fam-*` names mapped in
`assets/tokens.css`.

## What it shows

| Route | Screen |
|---|---|
| `/` | The map, drawn as an instrument whose layers each keep their own territory. Inside the ring: the replay checker and the three workflow cores at the centre, and each of the twelve component kernels as a proof dial (a red ring with one tick per passed proof check, the count written inside when it is large enough, a cross per rejected broken version) on a stem from the component that calls its generated code, along that component's own radius; dials keep a bounded size at every zoom and never overlap. Outside the ring: eight coverage rings, one per kind of check, one cell per component; then one citation tick per component; then the family names; then the doctrine's halo of 20 principles, 12 axioms and 17 failure modes; and a graduated rim. Choosing a rule marks exactly the components whose records cite it and draws a line to each when the lines fit their nested lanes, else traces one citer at a time as you point at it; choosing a component draws its lines up to its rules. A pointer arm swings through the centre to whatever is chosen. Hovering adds a comparison and never replaces the choice or moves the camera. Every label is placed by one planner (`src/map/labels.js`) that keeps text off marks, dials, lines and controls, with more names as you zoom. The panel opens with what the map is and how to read it, and the eight-ring key. A chosen item's card leads with its meaning, its exact count and its limit, and a preview of whatever you point at docks at the bottom of the panel, stating its relation to the choice. Escape dismisses the preview, then the choice, then returns to the overview. Selection is kept in `#o=`; search and filters in the query. |
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
schema. Guide tests cover unavailable older indexes and snapshot conflicts;
route cancellation prevents a late mount from replacing the page the reader
has navigated to. It also checks keyboard use and phone width, and writes screenshots
and `report.json`.

## Source

There is no build step and no dependency. `src/main.js` routes and cancels superseded mounts; `src/api.js`
holds the loading rules (schema check, error kinds, superseded requests,
cursor paging within one revision, parts that must share a revision);
`src/data.js` builds the model from one `/api/v1/overview?view=map` response;
`src/evidence.js` words every state and defines the coverage rings;
`src/markdown.js` loads retained guide bodies from the API and renders them
as text, never as HTML; `src/map/` draws
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
| Plectis system map, `sites/microcosm/assets/system-map.js` at `17c49004bd`: `coreLayout`, `ruleGlyph`, `captionParts`, `relationText` | The doctrine's three marks and its hub order, moved out of the centre into the halo, with its chords opened into ruled lanes (`src/map/layout.js` haloLayout); one sentence per lit thing and a pointed object restated against the chosen one (`src/views/readout.js`) |
| Lean Exposition, `site/src/panels/EdgePanel.tsx` at `6f62294` | The panel adds wording, not facts (`src/views/readout.js`) |

The newcomer introduction adapts the existing `guide__rows` explanation and
`row__go` selection patterns in `src/views/explorer.js`; the compact preview
adapts its existing `peek` card. The full selected-item readout and the map's
visual marks are retained. Both use the existing frame, tokens and fonts.

The layout of the map is new. Inside the ring it follows the paper's chain from
a stated property to the component that runs the proved code; outside it, the
coverage rings read like the tracks of a circular genome plot.

## Performance checks

The map requests `GET /api/v1/overview?view=map`, a compact projection of the
same snapshot. It keeps the fields used by the frontend model, including
retained core order, and omits duplicated proof/core records and unused receipt
fields. The original overview remains available unchanged. Browser acceptance
compares the complete models built from both responses, including Map and Set
iteration order.

The overview carries authored plain introductions; full guide Markdown is loaded
only for a selected detail. Keep hover and idle states free of guide requests.
Routes import their own JavaScript, and the map requests the catalogue only when
its index or a filter is used. Component pages load the overview and detail in
parallel and still refuse mismatched snapshot revisions. In selected map cards,
proof actions and claim limits precede the longer explanation and write-up;
Markdown renders when the write-up is opened.

The API prepares identity and gzip overview representations when admitting its
immutable snapshot. The local server uses HTTP/1.1 so browsers can revalidate
ETag-only API responses; the proxy preserves encoding, ETag and HEAD length.
Static assets use gzip and content ETags, with a bounded in-memory cache (64
entries / 8 MiB). File identity changes invalidate cached bytes immediately,
including edits that preserve size and modification time. Every visit revalidates;
there is no time window that knowingly serves stale code.

The canvas advances all active effects on one animation clock and paints at most
once per display frame. Geometry is invalidated by layout changes, not every
paint. `tests/canvas.test.mjs` checks overlapping animations, settled idle,
geometry changes, reduced motion and disposal; browser acceptance checks that
navigation cancels an unfinished mount and that previews leave the reading panel
clear. Preserve those behaviors when adding visual layers.
