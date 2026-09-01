from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "https://sabaaek-site-staging.osa60x.workers.dev/?locale=ar"
VIEWPORTS = {
    "iphone": (390, 844),
    "ipad_portrait": (820, 1180),
    "ipad_landscape": (1180, 820),
    "desktop": (1366, 768),
    "tv": (1920, 1080),
}


def test_staging_live_responsive_layout(tmp_path: Path) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        for name, (width, height) in VIEWPORTS.items():
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            page.goto(URL, wait_until="networkidle", timeout=60_000)
            page.wait_for_selector("#chart-ranges")
            page.screenshot(path=str(tmp_path / f"{name}.png"), full_page=True)
            metrics = page.evaluate(
                """() => ({
                    viewport: [innerWidth, innerHeight],
                    scrollWidth: document.documentElement.scrollWidth,
                    clientWidth: document.documentElement.clientWidth,
                    horizontalOverflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                    visibleAdmin: Boolean(document.querySelector('a[href*="admin"], #admin, [data-admin]')),
                    hasChart: Boolean(document.querySelector('#chart, canvas, svg')),
                    cards: document.querySelectorAll('.karat-price').length
                })"""
            )
            assert metrics["horizontalOverflow"] <= 1, (name, metrics)
            assert not metrics["visibleAdmin"], (name, metrics)
            assert metrics["hasChart"], (name, metrics)
            assert metrics["cards"] >= 3, (name, metrics)
            page.close()
        browser.close()
