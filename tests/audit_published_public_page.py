from __future__ import annotations

import json
from typing import Any

from playwright.sync_api import sync_playwright

SITE_URL = "https://osa60x.github.io/sabaaek-al-fakhama/?locale=ar&theme-preview=obsidian_glass&v=ea1f34c"


def inspect_viewport(playwright, width: int, height: int) -> dict[str, Any]:
    browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
    context = browser.new_context(viewport={"width": width, "height": height})
    context.add_init_script(
        """
        localStorage.setItem('sabaaek-public-theme','obsidian_glass');
        window.__startupAudit = {firstFrame: null, lcp: null};
        new PerformanceObserver(list => {
          const entries = list.getEntries();
          const entry = entries.at(-1);
          if (entry) window.__startupAudit.lcp = {
            startTime: Math.round(entry.startTime),
            size: entry.size,
            tag: entry.element?.tagName || '',
            id: entry.element?.id || '',
            className: entry.element?.className || ''
          };
        }).observe({type:'largest-contentful-paint', buffered:true});
        requestAnimationFrame(() => {
          window.__startupAudit.firstFrame = {
            theme: document.body?.dataset.theme || '',
            pending: document.documentElement.hasAttribute('data-theme-pending'),
            visibility: document.body ? getComputedStyle(document.body).visibility : ''
          };
        });
        """
    )
    page = context.new_page()
    cdp = context.new_cdp_session(page)
    requests: list[dict[str, Any]] = []
    cdp.send("Network.enable")
    cdp.on(
        "Network.requestWillBeSent",
        lambda event: requests.append(
            {
                "url": event["request"]["url"],
                "priority": event["request"].get("initialPriority", ""),
                "type": event.get("type", ""),
            }
        ),
    )
    page.goto(SITE_URL, wait_until="domcontentloaded")
    page.wait_for_function("window.__startupAudit.firstFrame !== null")
    page.wait_for_function("document.body.dataset.theme === 'obsidian_glass'")
    page.wait_for_timeout(1200)
    result = page.evaluate(
        """() => {
          const logo = document.querySelector('.brand-logo-user');
          const qr = document.querySelector('.site-qr');
          const nav = performance.getEntriesByType('navigation')[0];
          const paints = Object.fromEntries(performance.getEntriesByType('paint').map(e => [e.name, Math.round(e.startTime)]));
          const resources = performance.getEntriesByType('resource').map(e => ({name:e.name,duration:Math.round(e.duration),transferSize:e.transferSize}));
          const rect = logo.getBoundingClientRect();
          return {
            startup: window.__startupAudit,
            nav: {domContentLoaded:Math.round(nav.domContentLoadedEventEnd),load:Math.round(nav.loadEventEnd)},
            paints,
            logo: {width:Math.round(rect.width),height:Math.round(rect.height),filter:getComputedStyle(logo).filter},
            qrDisplay:getComputedStyle(qr).display,
            horizontalOverflow:document.documentElement.scrollWidth > window.innerWidth,
            price:document.querySelector('#ounce')?.textContent?.trim(),
            resourceCount:resources.length,
            logoResource:resources.find(r => r.name.includes('sabaaek-logo-user.png')) || null
          };
        }"""
    )
    result["logoRequest"] = next((r for r in requests if "sabaaek-logo-user.png" in r["url"]), None)
    browser.close()
    return result


if __name__ == "__main__":
    with sync_playwright() as playwright:
        report = {
            "mobile": inspect_viewport(playwright, 390, 844),
            "desktop": inspect_viewport(playwright, 1366, 768),
        }
    assert report["mobile"]["startup"]["firstFrame"] == {"theme": "obsidian_glass", "pending": False, "visibility": "visible"}
    assert report["desktop"]["startup"]["firstFrame"] == {"theme": "obsidian_glass", "pending": False, "visibility": "visible"}
    assert not report["mobile"]["horizontalOverflow"]
    assert not report["desktop"]["horizontalOverflow"]
    assert report["mobile"]["qrDisplay"] == "none"
    assert report["desktop"]["qrDisplay"] != "none"
    assert report["mobile"]["logo"]["width"] > 0 and report["desktop"]["logo"]["width"] > 0
    assert report["mobile"]["startup"]["lcp"]["className"] == "brand-logo-user"
    assert report["mobile"]["logoRequest"]["priority"] == "High"
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("PUBLISHED_PUBLIC_AUDIT_PASSED")
