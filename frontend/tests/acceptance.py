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
        page.on("pageerror", lambda e: errors.append(str(e)))

        # 1. A real search with several pages, combined filters and an empty result.
        page.goto(f"{base}/catalogue?q=check", wait_until="load")
        page.wait_for_selector(".rows .row")
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

        # 2. Direct component links.
        page.goto(f"{base}/components/mcp_tool_authority_replay", wait_until="load")
        page.wait_for_selector("#s-contract")
        check("a component with a modeled proof opens directly",
              page.locator("#s-proof").count() == 1 and page.get_by_role("link", name="Read the proof").count() >= 1)
        page.screenshot(path=str(args.out / "component-mcp.png"))
        page.goto(f"{base}/components/pattern_assimilation_step", wait_until="load")
        page.wait_for_selector("#s-records")
        absent = page.locator("#s-records .ref.absent").count()
        linked = page.locator("#s-records ul.ref-list a").count()
        check("unavailable records are named without a link", absent >= 2 and linked == 0, f"{absent} absent, {linked} links")
        page.goto(f"{base}/components/no_such_component", wait_until="load")
        page.wait_for_selector("h1")
        check("an unknown ID is a missing resource", page.locator("h1").inner_text() == "No component with this ID")

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

        page.route("**/api/v1/receipts?*", other_revision)
        page.goto(f"{base}/components/mcp_tool_authority_replay", wait_until="load")
        page.wait_for_selector("h1")
        check("a revision change is an explicit state", page.locator("h1").inner_text() == "The index changed while loading")
        page.unroute("**/api/v1/receipts?*")

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

        # 6. A truncated graph, and the same relations as a list.
        page.goto(f"{base}/graph?type=organ&id=pattern_assimilation_step&depth=2&max_edges=60", wait_until="load")
        page.wait_for_selector(".edge-groups h3")
        listed = page.locator(".edge-groups li").count()
        check("a truncated graph says so and lists its relations", page.locator("text=Truncated at 60 edges").count() == 1 and listed == 60, f"{listed} listed")
        page.screenshot(path=str(args.out / "graph-truncated.png"))

        # 7. Network failure and schema mismatch (controlled).
        page.route("**/api/v1**", lambda route: route.abort())
        page.goto(f"{base}/", wait_until="load")
        page.wait_for_selector("text=The component API is not reachable")
        check("a network failure is its own state", True)
        page.unroute("**/api/v1**")
        page.route("**/api/v1", lambda route: route.fulfill(status=200, content_type="application/json",
                                                             body=json.dumps({"schema_version": "plectis_component_http_v2", "snapshot_revision": "x", "data": {}})))
        page.goto(f"{base}/", wait_until="load")
        page.wait_for_selector("text=contract this explorer does not read")
        check("an incompatible schema is its own state", True)
        page.unroute("**/api/v1")

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

        # 9. Narrow screens read without the drawing.
        phone = browser.new_context(viewport={"width": 390, "height": 844}, color_scheme="light", device_scale_factor=3)
        mobile = phone.new_page()
        mobile.goto(f"{base}/", wait_until="load")
        mobile.wait_for_selector(".explorer__status", state="hidden", timeout=20000)
        mobile.wait_for_timeout(1800)
        mobile.screenshot(path=str(args.out / "phone-map.png"))
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
