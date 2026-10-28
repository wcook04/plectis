"""Browser acceptance run for the component explorer (docs/guides/frontend-implementation.md).

Needs Playwright for Python and a running explorer with its backend:

    python3 frontend/serve.py --start-backend          # in one terminal
    python3 frontend/tests/acceptance.py --base http://127.0.0.1:8767 --out /tmp/explorer-acceptance

Real responses are used wherever the API can produce the state; stale cursors,
revision changes, slow searches, network failure and schema mismatch use
controlled responses through request interception. Each check prints PASS or
FAIL and the run writes report.json and screenshots to --out.
"""

import argparse
import json
from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

SCHEMA = "plectis_component_http_v1"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:8767")
    parser.add_argument("--out", type=Path, default=Path("explorer-acceptance"))
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    base = args.base.rstrip("/")
    results = []

    def check(name, ok, detail=""):
        results.append({"check": name, "ok": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + (f": {detail}" if detail else ""), flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 790}, color_scheme="dark")
        page = ctx.new_page()
        errors = []
        initial_requests = []
        page.on("request", lambda request: initial_requests.append(request.url))
        page.on("pageerror", lambda e: errors.append(str(e)))

        # 1. A real search with several pages, combined filters and an empty result.
        page.goto(f"{base}/catalogue?q=check", wait_until="load")
        page.wait_for_selector(".rows .row")
        check("a catalogue visit loads no map code or overview",
              not any("/src/map/" in url or "/src/views/explorer.js" in url or "/api/v1/overview" in url for url in initial_requests))
        # Compact transport must preserve every model field and ordering.
        parity = page.evaluate("""async () => {
          const { build } = await import('/src/data.js');
          const [full, compact] = await Promise.all(['overview', 'overview?view=map']
            .map(path => fetch('/api/v1/' + path).then(response => response.json())));
          const canonical = value => value instanceof Map ? [...value].map(([key, item]) => [key, canonical(item)])
            : value instanceof Set ? [...value].map(canonical)
            : Array.isArray(value) ? value.map(canonical)
            : value && typeof value === 'object' ? Object.fromEntries(Object.entries(value).map(([key, item]) => [key, canonical(item)]))
            : value;
          return full.snapshot_revision === compact.snapshot_revision &&
            JSON.stringify(canonical(build(full.data, full.snapshot_revision))) ===
            JSON.stringify(canonical(build(compact.data, compact.snapshot_revision)));
        }""")
        check("compact transport preserves the entire map model and ordering", parity)
        cache_probe = page.evaluate("""async () => {
          const url = '/api/v1/overview?view=map';
          const first = await fetch(url).then(response => response.text());
          const second = await fetch(url).then(response => response.text());
          const last = performance.getEntriesByName(new URL(url, location.href).href).at(-1);
          return { same: first === second, transfer: last.transferSize, decoded: last.decodedBodySize };
        }""")
        check("unchanged API responses revalidate without downloading the body",
              cache_probe["same"] and cache_probe["transfer"] <= 1000
              and cache_probe["decoded"] > cache_probe["transfer"], str(cache_probe))
        status = page.locator('[role="status"]').first.inner_text()
        first = page.locator(".rows .row").count()
        page.get_by_role("button", name="more").first.click()
        page.wait_for_function("document.querySelectorAll('.rows .row').length > 25")
        second = page.locator(".rows .row").count()
        check("search pages append within one revision", first == 25 and second > first, f"{status!r}; {first} then {second} rows")
        page.goto(f"{base}/catalogue?q=check&family=agent_reliability_and_safety&evidence_class=algorithmic_projection", wait_until="load")
        page.wait_for_selector(".rows .row")
        combined = page.locator('[role="status"]').first.inner_text()
        page.reload(wait_until="load")
        page.wait_for_selector(".rows .row")
        check("combined filters survive reload", "match" in combined and page.locator('.chip[aria-pressed="true"]').count() == 2, combined)
        page.goto(f"{base}/catalogue?q=no-such-words-anywhere", wait_until="load")
        page.wait_for_selector("text=No component matches.")
        check("an unmatched search is an empty page, not an error", page.locator(".state--error").count() == 0)
        page.screenshot(path=str(args.out / "catalogue-empty.png"))

        # Late labels update already-visible content without a second list read.
        labels = ctx.new_page()
        held_labels, label_requests = [], []
        labels.route(f"{base}/api/v1", lambda route: held_labels.append(route))
        labels.on("request", lambda request: label_requests.append(request.url))
        labels.goto(f"{base}/catalogue?family=agent_reliability_and_safety", wait_until="load")
        labels.wait_for_selector(".rows .row")
        metadata = ctx.request.get(f"{base}/api/v1").json()
        for family in metadata["data"]["component_filters"]["family"]:
            if family["value"] == "agent_reliability_and_safety":
                family["label"] = "Readable family from the API"
        held_labels[0].fulfill(status=200, content_type="application/json", body=json.dumps(metadata))
        labels.wait_for_function("document.querySelector('.row__sub')?.textContent.includes('Readable family from the API')")
        check("late metadata refreshes visible catalogue labels without refetching",
              "Readable family from the API" in labels.locator('.graph-layout > div > p[aria-live]').inner_text()
              and sum("/api/v1/components?" in url for url in label_requests) == 1)
        labels.unroute(f"{base}/api/v1")
        compact = ctx.request.get(f"{base}/api/v1/overview?view=map").json()
        for family in compact["data"]["explorer"]["component_filters"]["family"]:
            if family["value"] == "agent_reliability_and_safety":
                family["label"] = "Readable family from the API"
        labels.route("**/api/v1/overview*", lambda route: route.fulfill(
            status=200, content_type="application/json", body=json.dumps(compact)))
        labels.goto(f"{base}/?family=agent_reliability_and_safety", wait_until="load")
        labels.wait_for_selector("[data-start-example]")
        check("the map refreshes its filter sentence from snapshot labels",
              "Readable family from the API" in labels.locator('.filtered').inner_text())
        labels.close()

        # A cold component detail starts while the overview is still in flight.
        parallel = ctx.new_page()
        parallel.add_init_script("""(() => {
          const original = window.fetch;
          let release;
          window.detailWhileOverviewPending = false;
          window.fetch = (url, options) => {
            if (String(url).includes('/overview')) return new Promise(resolve => {
              release = () => { release = null; resolve(original(url, options)); };
              setTimeout(() => release?.(), 750);
            });
            if (String(url).includes('/components/mcp_tool_authority_replay')) {
              window.detailWhileOverviewPending = !!release;
              release?.();
            }
            return original(url, options);
          };
        })()""")
        parallel.goto(f"{base}/components/mcp_tool_authority_replay", wait_until="load")
        parallel.wait_for_selector("#s-contract")
        check("cold component details and overview load concurrently",
              parallel.evaluate("window.detailWhileOverviewPending"))
        parallel.close()

        # 2. Direct component links.
        page.goto(f"{base}/components/mcp_tool_authority_replay", wait_until="load")
        page.wait_for_selector("#s-contract")
        page.wait_for_selector("#s-writeup .writeup")
        check("a component with a proved part opens directly, with its write-up",
              page.get_by_role("link", name="Open the proof page").count() >= 1 and page.locator(".page-plain").inner_text().startswith("Changes an automated assistant"))
        writeup = page.locator("#s-writeup").inner_text()
        check("the write-up shows no file path or command", "src/" not in writeup and "PYTHONPATH" not in writeup and "--input" not in writeup)
        page.screenshot(path=str(args.out / "component-mcp.png"))
        page.goto(f"{base}/components/pattern_assimilation_step", wait_until="load")
        page.wait_for_selector("#s-records .run")
        absent = page.locator("#s-records .run.is-absent").count()
        linked = page.locator("#s-records .run.is-absent a").count()
        check("missing records are shown without a link", absent >= 2 and linked == 0, f"{absent} missing, {linked} links")
        page.goto(f"{base}/components/no_such_component", wait_until="load")
        page.wait_for_selector("h1")
        check("an unknown ID is a missing resource", page.locator("h1").inner_text() == "No component with this ID")

        # The workflow cores and component kernels use different detail routes.
        for proof_id, title in (("proof::dafny::mcp_authority", "MCP authority"), ("repair", "Repair")):
            page.goto(f"{base}/proofs/{proof_id}", wait_until="load")
            page.wait_for_selector("#s-writeup .writeup")
            check(f"{title} proof page reads its retained guide",
                  len(page.locator("#s-writeup .writeup").inner_text()) > 100)

        # 3. A stale cursor restarts the list once (controlled 409).
        stale = {"done": False}

        def stale_cursor(route):
            if "cursor=" in route.request.url and not stale["done"]:
                stale["done"] = True
                route.fulfill(status=409, content_type="application/json",
                              body=json.dumps({"schema_version": SCHEMA, "snapshot_revision": "changed",
                                               "error": {"code": "stale_cursor", "message": "snapshot changed; restart pagination"}}))
            else:
                route.continue_()

        page.route("**/api/v1/components?*", stale_cursor)
        page.goto(f"{base}/catalogue?q=check", wait_until="load")
        page.wait_for_selector(".rows .row")
        page.get_by_role("button", name="more").first.click()
        page.wait_for_selector("text=started again from the first page")
        check("a stale cursor restarts pagination once", page.locator(".rows .row").count() == 25)
        page.unroute("**/api/v1/components?*")

        # 4. Parts of a page from two snapshots are never combined (controlled revision).
        def other_revision(route):
            response = route.fetch()
            body = response.json()
            body["snapshot_revision"] = "0" * 64
            route.fulfill(response=response, body=json.dumps(body))

        page.route("**/api/v1/components/mcp_tool_authority_replay", other_revision)
        page.goto(f"{base}/components/mcp_tool_authority_replay", wait_until="load")
        page.wait_for_selector("h1")
        check("a revision change is an explicit state", page.locator("h1").inner_text() == "The index changed while loading")
        page.goto(f"{base}/#o=comp%3Amcp_tool_authority_replay", wait_until="load")
        page.wait_for_function("document.querySelector('[data-limit]')?.textContent.includes('Reload the map')")
        check("a map card refuses details from another revision",
              "The index changed" in page.locator('[data-limit]').inner_text())
        page.unroute("**/api/v1/components/mcp_tool_authority_replay")

        # Old index details cannot silently read a newer guide from disk.
        def absent_guide(route):
            response = route.fetch()
            body = response.json()
            body["data"]["guide"] = {"ref": "paper_modules/mcp_tool_authority_replay.md", "availability": "unrecorded", "text": None}
            route.fulfill(response=response, body=json.dumps(body))

        page.route("**/api/v1/components/mcp_tool_authority_replay", absent_guide)
        page.goto(f"{base}/components/mcp_tool_authority_replay", wait_until="load")
        page.wait_for_selector("text=The write-up text is not retained in this snapshot")
        check("an old snapshot's missing guide stays explicitly absent",
              page.locator('#s-writeup .writeup').count() == 0)
        page.screenshot(path=str(args.out / "guide-unrecorded.png"))
        page.unroute("**/api/v1/components/mcp_tool_authority_replay")

        # 5. A slow earlier search cannot overwrite a later one (controlled delay).
        def slow(route):
            if "q=slow" in route.request.url:
                page.wait_for_timeout(1500)
            route.continue_()

        page.route("**/api/v1/components?*", slow)
        page.goto(f"{base}/catalogue", wait_until="load")
        page.wait_for_selector(".rows .row")
        box = page.locator("#cat-find")
        box.fill("slow")
        page.wait_for_timeout(300)
        box.fill("ownership")
        page.wait_for_timeout(2200)
        titles = page.locator(".rows .row__title").all_inner_texts()
        check("a superseded slow search is discarded", page.url.endswith("q=ownership") and len(titles) >= 1 and not any("slow" in t.lower() for t in titles),
              f"{len(titles)} rows for 'ownership'")
        page.unroute("**/api/v1/components?*")

        # 5b. Map match requests must be superseded even by an empty reset.
        match_probes = page.evaluate("""async () => {
          const { createCatalogue } = await import('/src/views/catalogue-core.js');
          const originalFetch = globalThis.fetch;
          const results = [];
          try {
            for (const scenario of ['text-reset', 'facet-reset', 'new-query', 'revision']) {
              let release;
              const observed = [];
              globalThis.fetch = async (url) => {
                const u = new URL(url, location.href);
                const old = u.searchParams.get('q') === 'old' || u.searchParams.has('family');
                const reply = () => new Response(JSON.stringify({
                  schema_version: 'plectis_component_http_v1',
                  snapshot_revision: scenario === 'revision' ? 'other' : 'held',
                  data: { items: [{ organ_id: old ? 'old-match' : 'new-match' }], total: 1, next_cursor: null }
                }), { headers: { 'Content-Type': 'application/json' } });
                if (old && u.searchParams.get('limit') === '100') {
                  return new Promise((resolve) => { release = () => resolve(reply()); });
                }
                return reply();
              };
              const host = document.createElement('div');
              const catalogue = createCatalogue(host, {
                row: () => document.createElement('li'), expectedRevision: () => 'held',
                onMatches: (ids, error) => observed.push({ ids: ids === null ? null : [...ids], error: error?.kind || null })
              });
              const first = scenario === 'facet-reset' ? { family: 'example' } : { q: scenario === 'revision' ? 'new' : 'old' };
              await catalogue.load(first);
              if (scenario !== 'revision') {
                await catalogue.load({ q: scenario === 'new-query' ? 'new' : '' });
                release();
              }
              await new Promise((resolve) => setTimeout(resolve, 0));
              results.push({ scenario, observed });
              catalogue.destroy();
            }
          } finally { globalThis.fetch = originalFetch; }
          return results;
        }""")
        for probe in match_probes:
            expected = [{"ids": None, "error": None}]
            if probe["scenario"] == "new-query":
                expected = [{"ids": ["new-match"], "error": None}]
            elif probe["scenario"] == "revision":
                expected = [{"ids": None, "error": "revision"}]
            check(f"map matches: {probe['scenario']}", probe["observed"] == expected, str(probe["observed"]))

        disposed = page.evaluate("""async () => {
          const { createCatalogue } = await import('/src/views/catalogue-core.js');
          const original = globalThis.fetch, pending = [], matches = [];
          const host = document.createElement('div');
          let catalogue;
          try {
            globalThis.fetch = (url, options) => new Promise(resolve => pending.push({ resolve, signal: options.signal }));
            catalogue = createCatalogue(host, {
              row: () => document.createElement('li'), onMatches: value => matches.push(value)
            });
            const loaded = catalogue.load({ q: 'held' });
            catalogue.destroy();
            for (const request of pending) request.resolve(new Response(JSON.stringify({
              schema_version: 'plectis_component_http_v1', snapshot_revision: 'held',
              data: { items: [{ organ_id: 'old' }], total: 1, next_cursor: null }
            })));
            await loaded;
            await new Promise(resolve => setTimeout(resolve, 0));
            return { requests: pending.length, aborted: pending.filter(request => request.signal.aborted).length,
              matches: matches.length, children: host.childElementCount };
          } finally { catalogue?.destroy(); globalThis.fetch = original; }
        }""")
        check("disposing a catalogue cancels both readers and withholds late results",
              disposed == {"requests": 2, "aborted": 2, "matches": 0, "children": 0}, str(disposed))

        # 6. A truncated graph, and the same relations as a list.
        page.goto(f"{base}/graph?type=organ&id=pattern_assimilation_step&depth=2&max_edges=60", wait_until="load")
        page.wait_for_selector(".edge-groups h3")
        listed = page.locator(".edge-groups li").count()
        check("a truncated graph says so and lists its relations", page.locator("text=Truncated at 60 edges").count() == 1 and listed == 60, f"{listed} listed")
        page.screenshot(path=str(args.out / "graph-truncated.png"))

        # 7. Network failure and schema mismatch (controlled).
        page.route("**/api/v1**", lambda route: route.abort())
        page.goto(f"{base}/", wait_until="load")
        page.wait_for_selector("text=The data server is not running")
        check("a network failure is its own state", True)
        page.unroute("**/api/v1**")
        page.route("**/api/v1/overview*", lambda route: route.fulfill(status=200, content_type="application/json",
                                                                      body=json.dumps({"schema_version": "plectis_component_http_v2", "snapshot_revision": "x", "data": {}})))
        page.goto(f"{base}/", wait_until="load")
        page.wait_for_selector("text=contract this explorer does not read")
        check("an incompatible schema is its own state", True)
        page.unroute("**/api/v1/overview*")

        # 8. Keyboard: skip link first, the map walks by arrow and lets go on Escape.
        page.goto(f"{base}/", wait_until="load")
        page.wait_for_selector(".explorer__status", state="hidden", timeout=20000)
        page.keyboard.press("Tab")
        check("the skip link is the first tab stop", page.evaluate("document.activeElement.className") == "skip-link")
        page.locator("canvas").focus()
        page.keyboard.press("ArrowRight")
        page.wait_for_selector(".card-title")
        picked = page.locator(".card-title").inner_text()
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        check("arrows choose a component and Escape lets it go", bool(picked) and page.locator(".card-title").count() == 0, picked)
        page.goto(f"{base}/#o=comp%3Amcp_tool_authority_replay", wait_until="load")
        page.wait_for_selector(".card-title", timeout=20000)
        page.wait_for_timeout(1400)
        page.screenshot(path=str(args.out / "map-selected.png"))
        check("a map selection is addressable", page.locator(".card-title").inner_text() == "MCP Tool Authority Replay")
        page.wait_for_selector(".component-summary")
        check("the card puts its proof action before map mechanics",
              page.locator(".component-summary").inner_text() != ""
              and page.evaluate("document.querySelector('.component-proof').compareDocumentPosition(document.querySelector('.readout')) & Node.DOCUMENT_POSITION_FOLLOWING")
              and page.locator(".component-card > details.fullwriteup").last.evaluate("(el) => !el.open"))
        page.locator(".plain-explanation > summary").click()
        check("the complete authored plain explanation stays available",
              page.locator("[data-plain]").inner_text().startswith("Changes an automated assistant")
              and "not for being genuine" in page.locator("[data-plain]").inner_text())
        page.locator(".plain-explanation > summary").click()
        page.locator(".explorer__body").click(position={"x": 8, "y": 8})
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        check("Escape lets go even when the panel has focus", page.locator(".card-title").count() == 0)

        # 8b. A real starting point and a compact preview with no guide prefetch.
        map_requests = []
        record_request = lambda request: map_requests.append(request.url)
        page.on("request", record_request)
        page.goto(f"{base}/", wait_until="load")
        page.wait_for_selector(".explorer__status", state="hidden", timeout=20000)
        page.wait_for_selector(".overview .guide__name")
        check("the overview states the page's purpose once, then reads the map from the centre out",
              page.locator(".overview h1").is_visible()
              and page.locator(".guide__name").all_text_contents() == ["Proof dials", "Components", "Eight rings", "Citations", "Doctrine"]
              and page.locator(".ring-key .ring-row").count() == 8)
        check("the unfiltered map does not request a hidden catalogue",
              not any("/api/v1/components?" in url for url in map_requests))
        page.locator("[data-start-example]").click()
        page.wait_for_selector(".card-title")
        check("a card has no permanent page title above it",
              page.locator(".explorer__title").count() == 0 and page.locator(".explorer__panel h1").count() == 1
              and page.locator(".explorer__panel h1.sr-only").count() == 1)
        check("a component card leads with identity, purpose, its limit and eight evidence rows",
              page.evaluate("""() => {
                const card = document.querySelector('.component-card');
                const order = ['.card-title', '.component-summary', '[data-limit]', '.evidence'].map((s) => card.querySelector(s));
                const rows = [...card.querySelectorAll('.evidence__row:not(.evidence__row--extra) .evidence__no')].map((e) => e.textContent);
                return order.every(Boolean) && order.every((el, i) => !i || order[i - 1].compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING)
                  && rows.join() === '01,02,03,04,05,06,07,08' && !/\\d+ of \\d+/.test(card.querySelector('.evidence').textContent);
              }"""))
        check("the newcomer example selects a real component",
              page.locator(".card-title").inner_text() == "MCP Tool Authority Replay"
              and "comp%3Amcp_tool_authority_replay" in page.url)
        page.keyboard.press("Escape")
        page.wait_for_selector("[data-start-example]")
        map_requests.clear()
        page.wait_for_timeout(2600)
        box = page.locator("canvas").bounding_box()
        cx, cy, base_r = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, min(box["width"], box["height"]) / 2
        shown = False
        for f in [x / 100 for x in range(40, 80)]:
            page.mouse.move(cx + base_r * f, cy + 1)
            page.wait_for_timeout(110)
            if page.locator(".dock.is-on").count():
                shown = True
                break
        page.wait_for_timeout(500)
        check("hovering a component shows its name, purpose, counts and limit in the dock",
              shown and page.locator(".dock__name").inner_text() != "" and len(page.locator(".dock__purpose").inner_text()) > 30
              and page.locator(".dock__counts li").count() >= 1 and page.locator(".dock__limit").inner_text() != "")
        panel_box = page.locator(".explorer__panel").bounding_box()
        preview_box = page.locator(".dock").bounding_box()
        check("the preview dock sits in the panel, never over the map, and is readable by assistive tech",
              shown and preview_box["x"] + preview_box["width"] <= panel_box["x"] + panel_box["width"] + 1
              and preview_box["height"] <= panel_box["height"] * 0.42 + 2
              and page.locator(".dock").get_attribute("aria-hidden") is None
              and page.locator(".explorer__stage .peek").count() == 0)
        page.mouse.move(cx, cy - base_r * 2)
        page.wait_for_timeout(120)
        lingered = page.locator(".dock.is-on").count() == 1
        page.wait_for_timeout(500)
        check("the last preview stays briefly after the pointer leaves, then goes",
              lingered and page.locator(".dock.is-on").count() == 0)
        check("resting and hovering never prefetch guide bodies",
              not any("/guides/" in url or "/api/v1/components/" in url or "/api/v1/cores/" in url or "/api/v1/proofs/" in url for url in map_requests))
        page.remove_listener("request", record_request)
        check("the ring key names all eight rings, numbered from the component, and stays on the stage with the panel open",
              page.locator(".explorer__rings .ringkey__row").count() == 8
              and sorted(page.locator(".explorer__rings .ringkey__no").all_text_contents()) == [f"0{i}" for i in range(1, 9)]
              and page.locator(".explorer__rings").is_visible())
        # Escape order: a preview first, then the choice, then the overview.
        page.evaluate("document.querySelector('[data-start-example]').click()")
        page.wait_for_selector(".card-title")
        page.wait_for_timeout(600)
        found = False
        for f in [x / 100 for x in range(40, 80)]:
            page.mouse.move(cx - base_r * f, cy + 3)
            page.wait_for_timeout(90)
            if page.locator(".dock.is-on").count():
                found = True
                break
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        first = (page.locator(".dock.is-on").count() == 0, page.locator(".card-title").count() == 1)
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        check("Escape dismisses the preview, then the choice, and the overview returns",
              found and first == (True, True) and page.locator(".card-title").count() == 0 and page.locator(".overview h1").is_visible(),
              f"preview found {found}; after first Escape {first}")
        page.mouse.move(2, 2)
        page.get_by_role("button", name="What do these mean?").first.click()
        page.wait_for_selector("dialog.explain[open]")
        rings = page.locator("dialog.explain .explain__ring").count()
        page.keyboard.press("Escape")
        page.wait_for_timeout(250)
        check("the key opens as a window that explains every ring and closes on Escape",
              rings == 8 and page.locator("dialog.explain[open]").count() == 0, f"{rings} rings explained")
        page.goto(f"{base}/coverage", wait_until="load")
        page.wait_for_selector(".measure")
        check("the coverage page lays the eight rings flat", page.locator(".measure").count() == 8 and page.locator(".measure .sq").count() == 8 * 88)

        # A superseded mount cannot install a hidden map or replace the new page.
        navigation = page.evaluate("""async () => {
          const { navigate } = await import('/src/main.js');
          const originalFetch = globalThis.fetch;
          let release, pendingSignal, began;
          const started = new Promise((resolve) => { began = resolve; });
          globalThis.fetch = (url, init) => {
            if (url === '/api/v1' && !release) {
              pendingSignal = init?.signal;
              began();
              return new Promise((resolve, reject) => {
                release = async () => {
                  try { resolve(await originalFetch(url, { ...init, signal: undefined })); }
                  catch (error) { reject(error); }
                };
              });
            }
            return originalFetch(url, init);
          };
          try {
            navigate('/');
            await started;
            await navigate('/catalogue');
            const aborted = pendingSignal?.aborted;
            await release();
            await new Promise((resolve) => setTimeout(resolve, 0));
            return { aborted, title: document.querySelector('h1')?.textContent,
                     maps: document.querySelectorAll('.explorer').length,
                     explorerMode: document.documentElement.classList.contains('is-explorer') };
          } finally { globalThis.fetch = originalFetch; }
        }""")
        check("navigation aborts a pending map mount and keeps the new route",
              navigation == {"aborted": True, "title": "Components", "maps": 0, "explorerMode": False}, str(navigation))

        # A route module may arrive after navigation. It must never mount then.
        import_context = browser.new_context(viewport={"width": 1440, "height": 790})
        delayed = import_context.new_page()
        held_imports = []
        delayed.route("**/src/views/explorer.js", lambda route: held_imports.append(route))
        with delayed.expect_request("**/src/views/explorer.js"):
            delayed.goto(f"{base}/", wait_until="domcontentloaded")
        delayed.locator('[data-nav="catalogue"]').click()
        delayed.wait_for_selector(".rows .row")
        for held in held_imports:
            held.continue_()
        after_import = delayed.evaluate("""async () => {
          await import('/src/views/explorer.js');
          await new Promise((resolve) => setTimeout(resolve, 0));
          return { title: document.querySelector('h1')?.textContent,
                   maps: document.querySelectorAll('.explorer').length,
                   path: location.pathname };
        }""")
        check("a delayed route import cannot mount after navigation",
              after_import == {"title": "Components", "maps": 0, "path": "/catalogue"}, str(after_import))
        import_context.close()

        # 9. Narrow screens read without the drawing.
        phone = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="light", device_scale_factor=3)
        mobile = phone.new_page()
        mobile.goto(f"{base}/", wait_until="load")
        mobile.wait_for_selector(".explorer__status", state="hidden", timeout=20000)
        mobile.wait_for_timeout(1800)
        mobile.screenshot(path=str(args.out / "phone-map.png"))
        mobile.evaluate("document.querySelector('[data-explorer-view=\"details\"]').click()")
        mobile.wait_for_timeout(200)
        mobile.locator("[data-start-example]").click()
        mobile.wait_for_selector(".card-title")
        mobile.wait_for_timeout(400)
        mobile.locator("[data-explorer-view=map]").click()
        mobile.wait_for_timeout(200)
        mobile.evaluate("document.querySelector('canvas').focus()")
        mobile.keyboard.press("ArrowRight")
        mobile.wait_for_timeout(600)
        sheet = mobile.evaluate("({ shown: document.querySelector('.explorer').dataset.explorerShown, sheet: document.querySelector('.explorer').dataset.explorerSheet, h: document.querySelector('.explorer__panel').getBoundingClientRect().height })")
        mobile.screenshot(path=str(args.out / "phone-sheet.png"))
        check("a phone choice keeps the map and opens a short sheet over it",
              sheet["shown"] == "map" and sheet["sheet"] == "peek" and sheet["h"] <= 240, str(sheet))
        mobile.keyboard.press("Escape")
        mobile.wait_for_timeout(300)
        mobile.get_by_role("button", name="Details").click()
        mobile.wait_for_timeout(300)
        mobile.screenshot(path=str(args.out / "phone-details.png"))
        wide = mobile.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        check("a phone switches between map and details without sideways scroll", not wide)
        mobile.goto(f"{base}/components/pattern_assimilation_step", wait_until="load")
        mobile.wait_for_selector("#s-records")
        check("a component page reflows at phone width", not mobile.evaluate("document.documentElement.scrollWidth > window.innerWidth"))
        mobile.screenshot(path=str(args.out / "phone-component.png"))
        phone.close()

        check("no script errors on any page", not errors, "; ".join(errors[:3]))
        browser.close()

    (args.out / "report.json").write_text(json.dumps(results, indent=2))
    failed = [r for r in results if not r["ok"]]
    print(f"{len(results) - len(failed)} of {len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
