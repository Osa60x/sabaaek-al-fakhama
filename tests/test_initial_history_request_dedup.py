#!/usr/bin/env python3
"""The initial public view should request its active history range exactly once."""
from __future__ import annotations

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = (Path(__file__).resolve().parents[1] / "index.html").as_uri()
NOW = int(time.time() * 1000)


def main() -> None:
    history_requests = []

    def route_worker(route):
        url = route.request.url
        if "/quote" in url:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"price": 4592.5, "symbol": "XAU", "currency": "USD", "source": "test", "sourceUpdatedAt": NOW, "fetchedAt": NOW, "status": "live"}),
            )
            return
        if "/history" in url:
            history_requests.append(url)
            points = [
                {"ts": NOW - 1800000, "price": 4589.1, "high": 4589.1, "low": 4589.1},
                {"ts": NOW - 900000, "price": 4591.2, "high": 4591.2, "low": 4591.2},
                {"ts": NOW, "price": 4592.5, "high": 4592.5, "low": 4592.5},
            ]
            route.fulfill(status=200, content_type="application/json", body=json.dumps({"range": "24h", "points": points, "gap_threshold_ms": 2100000}))
            return
        route.continue_()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 390, "height": 844})
        page.route("**/sabaaek-gold-api.osa60x.workers.dev/**", route_worker)
        page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_function("document.querySelector('#chart-source')?.textContent.includes('نقاط فعلية')", timeout=30000)
        page.wait_for_timeout(250)
        browser.close()

    assert len(history_requests) == 1, f"Expected one initial history request, observed {len(history_requests)}: {history_requests}"
    print("INITIAL_HISTORY_REQUEST_DEDUP_TEST_PASSED")


if __name__ == "__main__":
    main()
