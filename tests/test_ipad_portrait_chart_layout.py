#!/usr/bin/env python3
"""Regression test: iPad portrait must use the stacked layout without horizontal overflow."""
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = (Path(__file__).resolve().parents[1] / "index.html").as_uri()


def history_response(route):
    points = [
        {"ts": 1787800000000, "price": 4588.10, "source": "test"},
        {"ts": 1787818000000, "price": 4594.30, "source": "test"},
        {"ts": 1787836000000, "price": 4579.70, "source": "test"},
        {"ts": 1787854000000, "price": 4592.80, "source": "test"},
    ]
    route.fulfill(status=200, content_type="application/json", body='{"range":"24h","count":4,"points":' + __import__("json").dumps(points) + "}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 820, "height": 1180}, device_scale_factor=1)
        page.route("**/history**", history_response)
        page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_function("document.querySelectorAll('.chart-price-tick').length >= 4", timeout=45000)
        metrics = page.evaluate(
            """() => {
              const dashboard = document.querySelector('.dashboard').getBoundingClientRect();
              const chart = document.querySelector('.chart-panel').getBoundingClientRect();
              return {
                viewport: window.innerWidth,
                scrollWidth: document.documentElement.scrollWidth,
                grid: getComputedStyle(document.querySelector('.dashboard')).gridTemplateColumns,
                dashboardWidth: dashboard.width,
                chartWidth: chart.width,
                svgWidth: document.querySelector('#chart').getBoundingClientRect().width,
              };
            }"""
        )
        browser.close()
    print(metrics)
    assert metrics["scrollWidth"] <= metrics["viewport"], metrics
    assert metrics["dashboardWidth"] <= metrics["viewport"], metrics
    assert len(metrics["grid"].split()) == 1, f"iPad portrait must use a single dashboard column: {metrics}"
    assert metrics["chartWidth"] <= metrics["viewport"], metrics
    assert metrics["svgWidth"] > 0, metrics
    print("IPAD_PORTRAIT_CHART_LAYOUT_TEST_PASSED")


if __name__ == "__main__":
    main()
