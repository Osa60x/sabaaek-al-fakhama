from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import Route, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SITE_URL = (ROOT / "index.html").as_uri() + "?locale=ar"
INDEX = ROOT / "index.html"
WORKER_SOURCE = ROOT / "workers" / "sabaaek-gold-api" / "src" / "index.js"
WORKER_HOST = "**/sabaaek-gold-api.osa60x.workers.dev/**"
SETTINGS_HOST = "**/sabaaek-admin?action=public-settings"
ADJUSTMENTS_HOST = "**/sabaaek-admin?action=public-adjustments"

NOW = 1787787600000
RAW_POINTS = [
    {"ts": NOW - 60 * 60 * 1000, "price": 4600.0},
    {"ts": NOW - 50 * 60 * 1000, "price": 4612.0},
    {"ts": NOW - 40 * 60 * 1000, "price": 4608.0},
    {"ts": NOW - 20 * 60 * 1000, "price": 4616.0},
    {"ts": NOW, "price": 4620.0},
]
DAILY_POINTS = [
    {"ts": NOW - 4 * 24 * 60 * 60 * 1000, "price": 4590.0, "high": 4615.0, "low": 4572.0},
    {"ts": NOW - 3 * 24 * 60 * 60 * 1000, "price": 4611.0, "high": 4622.0, "low": 4581.0},
    {"ts": NOW - 2 * 24 * 60 * 60 * 1000, "price": 4605.0, "high": 4630.0, "low": 4598.0},
    {"ts": NOW - 24 * 60 * 60 * 1000, "price": 4628.0, "high": 4638.0, "low": 4602.0},
    {"ts": NOW, "price": 4620.0, "high": 4631.0, "low": 4610.0},
]
MONTHLY_POINTS = [
    {"ts": NOW - 120 * 24 * 60 * 60 * 1000, "price": 4400.0, "high": 4450.0, "low": 4310.0},
    {"ts": NOW - 90 * 24 * 60 * 60 * 1000, "price": 4510.0, "high": 4555.0, "low": 4380.0},
    {"ts": NOW - 60 * 24 * 60 * 60 * 1000, "price": 4560.0, "high": 4600.0, "low": 4480.0},
    {"ts": NOW - 30 * 24 * 60 * 60 * 1000, "price": 4595.0, "high": 4650.0, "low": 4540.0},
    {"ts": NOW, "price": 4620.0, "high": 4670.0, "low": 4570.0},
]


def fulfill_json(route: Route, payload: dict) -> None:
    route.fulfill(status=200, content_type="application/json", body=json.dumps(payload))


def install_api_mocks(page, requested_ranges: list[str]) -> None:
    def worker(route: Route) -> None:
        parsed = urlparse(route.request.url)
        if parsed.path.endswith("/quote"):
            fulfill_json(
                route,
                {
                    "price": 4620.0,
                    "symbol": "XAU",
                    "currency": "USD",
                    "source": "test",
                    "sourceUpdatedAt": NOW,
                    "fetchedAt": NOW,
                    "status": "live",
                },
            )
            return
        selected = parse_qs(parsed.query).get("range", [""])[0]
        requested_ranges.append(selected)
        points = {"24h": RAW_POINTS, "30d": DAILY_POINTS, "1y": MONTHLY_POINTS}.get(selected, [])
        fulfill_json(
            route,
            {
                "range": selected,
                "resolution": {"24h": "raw", "30d": "daily", "1y": "monthly"}.get(selected),
                "points": points,
                "high": max(point.get("high", point["price"]) for point in points) if points else None,
                "low": min(point.get("low", point["price"]) for point in points) if points else None,
            },
        )

    page.route(WORKER_HOST, worker)
    page.route(SETTINGS_HOST, lambda route: fulfill_json(route, {"settings": {"theme": "obsidian_glass", "contact_actions": []}}))
    page.route(ADJUSTMENTS_HOST, lambda route: fulfill_json(route, {"adjustments": []}))


def test_range_controls_render_and_request_aggregate_ranges() -> None:
    requested_ranges: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        page = browser.new_page(viewport={"width": 1024, "height": 768})
        install_api_mocks(page, requested_ranges)
        page.add_init_script("localStorage.setItem('sabaaek-public-theme', JSON.stringify({theme:'obsidian_glass', savedAt:Date.now()}));")
        page.goto(SITE_URL, wait_until="domcontentloaded")

        controls = page.locator("#chart-ranges button")
        assert controls.count() == 3
        page.wait_for_function("document.querySelectorAll('#chart-lines polyline').length > 0")
        assert [controls.nth(i).get_attribute("data-range") for i in range(3)] == ["24h", "30d", "1y"]
        assert page.locator("#chart-ranges button[aria-pressed='true']").get_attribute("data-range") == "24h"
        initial_request_count = len(requested_ranges)

        page.locator("#chart-ranges button[data-range='30d']").click()
        page.wait_for_function("document.querySelector('#chart-title').textContent.includes('شهر')")
        assert page.locator("#chart-ranges button[aria-pressed='true']").get_attribute("data-range") == "30d"
        assert page.locator("#chart-lines polyline").count() == 1

        page.locator("#chart-ranges button[data-range='1y']").click()
        page.wait_for_function("document.querySelector('#chart-title').textContent.includes('سنة')")
        assert page.locator("#chart-ranges button[aria-pressed='true']").get_attribute("data-range") == "1y"
        assert page.locator("#chart-lines polyline").count() == 1
        assert requested_ranges[initial_request_count:] == ["30d", "1y"]
        browser.close()


def test_history_worker_contract_supports_raw_daily_and_monthly_storage() -> None:
    source = WORKER_SOURCE.read_text(encoding="utf-8")
    for token in (
        "gold_daily",
        "gold_monthly",
        '"24h": {',
        '"30d": {',
        '"1y": {',
        "resolution",
        "last_good_quote",
        "DELETE FROM gold_points WHERE ts < ?",
    ):
        assert token in source, f"missing worker history contract: {token}"


if __name__ == "__main__":
    test_range_controls_render_and_request_aggregate_ranges()
    test_history_worker_contract_supports_raw_daily_and_monthly_storage()
    print("CHART_HISTORY_RANGE_TESTS_PASSED")
