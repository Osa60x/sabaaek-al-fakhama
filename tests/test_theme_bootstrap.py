from __future__ import annotations

import time
from pathlib import Path

from playwright.sync_api import Route, sync_playwright

PAGE_URL = (Path(__file__).resolve().parents[1] / "index.html").as_uri()
THEMES = ("emerald_classic", "obsidian_glass", "ivory_luxe")


def settings_route(theme: str):
    def fulfill(route: Route) -> None:
        time.sleep(0.25)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=f'{{"settings":{{"theme":"{theme}","contact_actions":[]}}}}',
        )

    return fulfill


def record_first_frame(page) -> None:
    page.add_init_script(
        """
        (() => {
          window.__themeBootstrapFirstFrame = null;
          requestAnimationFrame(() => {
            window.__themeBootstrapFirstFrame = {
              theme: document.body?.dataset.theme || '',
              pending: document.documentElement.hasAttribute('data-theme-pending')
            };
          });
        })();
        """
    )


def test_cached_theme_is_present_before_first_frame_for_every_theme() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        for theme in THEMES:
            page = browser.new_page()
            page.route("**/sabaaek-admin?action=public-settings", settings_route(theme))
            page.add_init_script(f"localStorage.setItem('sabaaek-public-theme', JSON.stringify({{theme:'{theme}',savedAt:Date.now()}}))")
            record_first_frame(page)
            page.goto(PAGE_URL, wait_until="domcontentloaded")
            page.wait_for_function("window.__themeBootstrapFirstFrame !== null")
            first_frame = page.evaluate("window.__themeBootstrapFirstFrame")
            assert first_frame == {"theme": theme, "pending": False}
            page.wait_for_function(
                "([ 'emerald_classic', 'obsidian_glass', 'ivory_luxe' ].includes(document.body.dataset.theme) && !document.documentElement.hasAttribute('data-theme-pending'))"
            )
            assert page.evaluate("document.body.dataset.theme") == theme
            page.close()
        browser.close()


def test_cold_start_stays_gated_until_remote_theme_arrives_for_every_theme() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        for theme in THEMES:
            page = browser.new_page()
            page.route("**/sabaaek-admin?action=public-settings", settings_route(theme))
            record_first_frame(page)
            page.goto(PAGE_URL, wait_until="domcontentloaded")
            page.wait_for_function("window.__themeBootstrapFirstFrame !== null")
            assert page.evaluate("window.__themeBootstrapFirstFrame") == {"theme": "", "pending": True}
            page.wait_for_function(
                f"document.body.dataset.theme === '{theme}' && !document.documentElement.hasAttribute('data-theme-pending')"
            )
            page.close()
        browser.close()


def test_legacy_theme_cache_is_gated_when_remote_theme_differs() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        page = browser.new_page()
        page.route("**/sabaaek-admin?action=public-settings", settings_route("obsidian_glass"))
        page.add_init_script("localStorage.setItem('sabaaek-public-theme', 'emerald_classic')")
        record_first_frame(page)
        page.goto(PAGE_URL, wait_until="domcontentloaded")
        page.wait_for_function("window.__themeBootstrapFirstFrame !== null")
        assert page.evaluate("window.__themeBootstrapFirstFrame") == {"theme": "", "pending": True}
        page.wait_for_function("document.body.dataset.theme === 'obsidian_glass' && !document.documentElement.hasAttribute('data-theme-pending')")
        browser.close()


if __name__ == "__main__":
    test_cached_theme_is_present_before_first_frame_for_every_theme()
    test_cold_start_stays_gated_until_remote_theme_arrives_for_every_theme()
    test_legacy_theme_cache_is_gated_when_remote_theme_differs()
    print("THEME_BOOTSTRAP_TESTS_PASSED")
