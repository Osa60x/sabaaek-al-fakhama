from __future__ import annotations

import json
import time
from pathlib import Path

from playwright.sync_api import Page, Route, sync_playwright

SITE_URL = "https://osa60x.github.io/sabaaek-al-fakhama/"
ADMIN_URL = "https://osa60x.github.io/sabaaek-al-fakhama/admin.html"
SETTINGS_PATTERN = "**/sabaaek-admin?action=public-settings"
THEMES = ("emerald_classic", "obsidian_glass", "ivory_luxe")


def delayed_settings(theme: str):
    def handler(route: Route) -> None:
        time.sleep(0.25)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps({"settings": {"theme": theme, "contact_actions": []}}),
        )

    return handler


def install_first_frame_probe(page: Page, cached_theme: str | None) -> None:
    cached_assignment = (
        "localStorage.setItem('sabaaek-public-theme', JSON.stringify({"
        f"theme: '{cached_theme}', savedAt: Date.now()}}));"
        if cached_theme
        else "localStorage.removeItem('sabaaek-public-theme');"
    )
    page.add_init_script(
        f"""
        (() => {{
          {cached_assignment}
          window.__firstThemeFrame = null;
          requestAnimationFrame(() => {{
            const body = document.body;
            window.__firstThemeFrame = {{
              at: performance.now(),
              theme: body?.dataset.theme || '',
              pending: document.documentElement.hasAttribute('data-theme-pending'),
              visibility: body ? getComputedStyle(body).visibility : ''
            }};
          }});
        }})();
        """
    )


def test_admin_login_inputs_without_authentication() -> dict:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        page = browser.new_page(viewport={"width": 390, "height": 844})
        sensitive_requests: list[str] = []
        page.on(
            "request",
            lambda request: sensitive_requests.append(request.url)
            if "/auth/v1/token" in request.url or "signInWithPassword" in request.url
            else None,
        )
        page.goto(ADMIN_URL, wait_until="domcontentloaded")
        page.locator("#login-form").wait_for(state="visible")

        input_state = page.evaluate(
            """() => [...document.querySelectorAll('#login-form input')].map(input => ({
              id: input.id,
              type: input.type,
              name: input.name,
              inputMode: input.inputMode,
              autocomplete: input.autocomplete,
              autocapitalize: input.autocapitalize,
              spellcheck: input.spellcheck,
              describedBy: input.getAttribute('aria-describedby'),
              minHeight: parseFloat(getComputedStyle(input).minHeight),
              fontSize: parseFloat(getComputedStyle(input).fontSize)
            }))"""
        )
        by_id = {item["id"]: item for item in input_state}
        assert set(by_id) == {"email", "password"}
        assert by_id["email"]["type"] == "email"
        assert by_id["email"]["name"] == "email"
        assert by_id["email"]["inputMode"] == "email"
        assert by_id["email"]["autocomplete"] == "email"
        assert by_id["email"]["autocapitalize"] == "none"
        assert by_id["email"]["spellcheck"] is False
        assert by_id["email"]["describedBy"] == "email-error"
        assert by_id["password"]["type"] == "password"
        assert by_id["password"]["name"] == "password"
        assert by_id["password"]["autocomplete"] == "current-password"
        assert by_id["password"]["autocapitalize"] == "none"
        assert by_id["password"]["spellcheck"] is False
        assert by_id["password"]["describedBy"] == "password-error"
        assert all(item["minHeight"] >= 44 and item["fontSize"] >= 16 for item in input_state)

        page.locator("#login-button").click()
        page.locator("#login-error-summary").wait_for(state="visible")
        assert page.locator("#login-error-summary").text_content() == "تحقق من الحقول المحددة ثم أعد المحاولة."
        assert page.locator("#email").get_attribute("aria-invalid") == "true"
        assert page.locator("#password").get_attribute("aria-invalid") == "true"
        assert page.evaluate("document.activeElement.id") == "login-error-summary"
        assert not sensitive_requests

        page.locator("#email").fill("bad-email")
        page.locator("#password").fill("TestOnly!123")
        page.locator("#login-button").click()
        assert page.locator("#email").get_attribute("aria-invalid") == "true"
        assert page.locator("#password").get_attribute("aria-invalid") == "false"
        assert not sensitive_requests

        page.locator("#email").fill("valid@example.com")
        assert page.locator("#email").get_attribute("aria-invalid") == "false"
        assert page.locator("#login-error-summary").is_hidden()
        assert not sensitive_requests

        page.locator("#password").fill("")
        page.locator("#login-button").click()
        assert page.locator("#password").get_attribute("aria-invalid") == "true"
        assert page.locator("#password-error").text_content() == "أدخل كلمة المرور."
        page.locator("#password").fill("TestOnly!123")
        assert page.locator("#password").get_attribute("aria-invalid") == "false"
        assert page.locator("#login-error-summary").is_hidden()
        assert not sensitive_requests

        focus_style = page.evaluate(
            """() => { const field = document.querySelector('#email'); field.focus();
            return { outline: getComputedStyle(field).outlineStyle, shadow: getComputedStyle(field).boxShadow }; }"""
        )
        assert focus_style["outline"] != "none" or focus_style["shadow"] != "none"
        metrics = page.evaluate(
            """() => { const nav = performance.getEntriesByType('navigation')[0];
            return { domContentLoaded: Math.round(nav.domContentLoadedEventEnd), load: Math.round(nav.loadEventEnd) }; }"""
        )
        browser.close()
        return {"inputs": input_state, "focus": focus_style, "timing": metrics}


def test_safe_internal_input_controls_without_save() -> dict:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        page = browser.new_page(viewport={"width": 390, "height": 844})
        protected_requests: list[str] = []
        page.on(
            "request",
            lambda request: protected_requests.append(request.url)
            if "sabaaek-admin?action=" in request.url and not request.url.endswith("public-adjustments")
            else None,
        )
        page.goto(ADMIN_URL, wait_until="domcontentloaded")
        page.evaluate(
            """() => ['owner-setup','password-change','dashboard','owner-tools'].forEach(id =>
              document.querySelector(`#${id}`).classList.remove('hidden'))"""
        )

        all_controls = page.evaluate(
            """() => [...document.querySelectorAll('input, select')].map(control => ({
              id: control.id || '', type: control.type || '', required: control.required,
              min: control.min || '', max: control.max || '', step: control.step || '',
              minHeight: parseFloat(getComputedStyle(control).minHeight),
              fontSize: parseFloat(getComputedStyle(control).fontSize)
            }))"""
        )
        assert all(item["minHeight"] >= 44 and item["fontSize"] >= 16 for item in all_controls)

        page.locator('[data-carat="24"]').fill("0")
        page.get_by_role("button", name="زيادة تعديل عيار 24").click()
        assert page.locator('[data-carat="24"]').input_value() == "0.5"
        page.get_by_role("button", name="إنقاص تعديل عيار 24").click()
        assert page.locator('[data-carat="24"]').input_value() == "0"
        page.locator('[data-carat="24"]').fill("5001")
        page.locator('#save-prices').click()
        assert "تحقق من القيم المسموح بها" in page.locator('#price-status').text_content()

        page.locator('#current-password').fill("TestOnly!123")
        page.locator('#new-password').fill("ValidPass!123")
        page.locator('#new-password-confirm').fill("DifferentPass!456")
        page.locator('#password-change-form button[type="submit"]').click()
        assert "غير متطابقتين" in page.locator('#password-change-status').text_content()

        page.locator('#owner-password').fill("ValidPass!123")
        page.locator('#owner-password-confirm').fill("DifferentPass!456")
        page.locator('#owner-setup-form button[type="submit"]').click()
        assert "غير متطابقتين" in page.locator('#owner-setup-status').text_content()

        page.locator('#manager-email').fill("manager@example.com")
        page.locator('#manager-password').fill("weak")
        page.locator('#create-manager').click()
        assert "لا تحقق متطلبات الأمان" in page.locator('#manager-status').text_content()

        page.locator('input[name="site-theme"][value="obsidian_glass"]').check(force=True)
        assert page.locator('input[name="site-theme"]:checked').get_attribute('value') == "obsidian_glass"
        page.locator('#add-contact').click()
        row = page.locator('#contact-editor .contact-row')
        row.wait_for(state="visible")
        row.locator('input').nth(0).fill("تواصل تجريبي")
        row.locator('input').nth(1).fill("966500000000")
        assert row.locator('input').nth(0).input_value() == "تواصل تجريبي"
        assert row.locator('input').nth(1).input_value() == "966500000000"
        row.get_by_role('button', name='حذف').click()
        assert page.locator('#contact-editor .contact-row').count() == 0
        assert not protected_requests
        browser.close()
        return {"controls": len(all_controls), "protected_requests": len(protected_requests)}


def test_black_theme_starts_without_green_flash() -> list[dict]:
    results: list[dict] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        for theme in THEMES:
            page = browser.new_page(viewport={"width": 390, "height": 844})
            page.route(SETTINGS_PATTERN, delayed_settings(theme))
            install_first_frame_probe(page, theme)
            page.goto(SITE_URL, wait_until="domcontentloaded")
            page.wait_for_function("window.__firstThemeFrame !== null")
            first = page.evaluate("window.__firstThemeFrame")
            assert first == {"at": first["at"], "theme": theme, "pending": False, "visibility": "visible"}
            page.wait_for_function(
                f"document.body.dataset.theme === '{theme}' && !document.documentElement.hasAttribute('data-theme-pending')"
            )
            results.append({"mode": "cached", "theme": theme, **first})
            page.close()

        cold = browser.new_page(viewport={"width": 390, "height": 844})
        cold.route(SETTINGS_PATTERN, delayed_settings("obsidian_glass"))
        install_first_frame_probe(cold, None)
        cold.goto(SITE_URL, wait_until="domcontentloaded")
        cold.wait_for_function("window.__firstThemeFrame !== null")
        first = cold.evaluate("window.__firstThemeFrame")
        assert first == {"at": first["at"], "theme": "", "pending": True, "visibility": "hidden"}
        cold.wait_for_function(
            "document.body.dataset.theme === 'obsidian_glass' && !document.documentElement.hasAttribute('data-theme-pending')"
        )
        results.append({"mode": "cold", "theme": "obsidian_glass", **first})
        cold.close()
        browser.close()
    return results


if __name__ == "__main__":
    report = {
        "admin": test_admin_login_inputs_without_authentication(),
        "safe_internal_controls": test_safe_internal_input_controls_without_save(),
        "theme_startup": test_black_theme_starts_without_green_flash(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("ADMIN_UX_AND_THEME_STARTUP_TESTS_PASSED")
