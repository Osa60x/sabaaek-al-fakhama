from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE_URL = os.environ.get("LAYOUT_URL", "https://osa60x.github.io/sabaaek-al-fakhama/?locale=ar&theme-preview=obsidian_glass&v=b85d443")
VIEWPORTS = {
    "ipad_landscape": (1024, 768),
    "laptop": (1366, 768),
    "desktop": (1920, 1080),
    "tv_4k": (3840, 2160),
}
OUT_DIR = Path(__file__).resolve().parents[1] / "qa"
QUOTE = {"price": 4592.70, "symbol": "XAU", "currency": "USD", "source": "gold-api.com", "sourceUpdatedAt": 1787772103000, "fetchedAt": 1787772127721, "status": "live"}
HISTORY = {"points": [{"price": 4568.4, "ts": 1787685703000}, {"price": 4584.7, "ts": 1787710903000}, {"price": 4612.1, "ts": 1787736103000}, {"price": 4592.7, "ts": 1787772103000}]}


def route_price_data(route) -> None:
    url = route.request.url
    if "sabaaek-gold-api.osa60x.workers.dev" not in url:
        route.continue_()
        return
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "content-type, authorization",
    }
    if route.request.method == "OPTIONS":
        route.fulfill(status=204, headers=cors_headers, body="")
        return
    payload = HISTORY if "/history" in url else QUOTE
    route.fulfill(
        status=200,
        content_type="application/json",
        headers=cors_headers,
        body=json.dumps(payload),
    )


def audit(page, name: str, width: int, height: int) -> dict:
    page.set_viewport_size({"width": width, "height": height})
    page.goto(SITE_URL, wait_until="domcontentloaded")
    page.wait_for_function("document.body.dataset.theme === 'obsidian_glass'")
    page.wait_for_function("document.querySelector('#ounce')?.textContent.trim() !== '—'", timeout=6000)
    page.wait_for_timeout(250)
    report = page.evaluate(
        """() => {
          const rect = selector => {
            const element = document.querySelector(selector);
            if (!element) return null;
            const r = element.getBoundingClientRect();
            const style = getComputedStyle(element);
            return {x:Math.round(r.x), y:Math.round(r.y), width:Math.round(r.width), height:Math.round(r.height), display:style.display, gridTemplateColumns:style.gridTemplateColumns, gridTemplateRows:style.gridTemplateRows};
          };
          const karats = [...document.querySelectorAll('.karats > *')].map(element => {
            const r = element.getBoundingClientRect();
            return {className:element.className, x:Math.round(r.x), y:Math.round(r.y), width:Math.round(r.width), height:Math.round(r.height), text:element.textContent.trim().slice(0,80)};
          });
          const dashboardChildren = [...document.querySelector('.dashboard').children].map(element => {
            const r = element.getBoundingClientRect();
            return {className:element.className, x:Math.round(r.x), y:Math.round(r.y), width:Math.round(r.width), height:Math.round(r.height)};
          });
          const doc = document.documentElement;
          return {
            viewport:{width:innerWidth,height:innerHeight},
            scroll:{width:doc.scrollWidth,height:doc.scrollHeight,horizontal:doc.scrollWidth>innerWidth,vertical:doc.scrollHeight>innerHeight},
            shell:rect('.shell'), topbar:rect('.topbar'), dashboard:rect('.dashboard'), summary:rect('.summary'), quote:rect('.quote'), karatsContainer:rect('.karats'), chart:rect('.chart-panel'), meta:rect('.meta-bar'), footer:rect('.footer'),
            karats, dashboardChildren,
            price:document.querySelector('#ounce')?.textContent.trim(), chartPoints:document.querySelectorAll('#chart-lines polyline').length,
            qrDisplay:getComputedStyle(document.querySelector('.site-qr')).display
          };
        }"""
    )
    page.screenshot(path=str(OUT_DIR / f"landscape-{name}.png"), full_page=False)
    return report


if __name__ == "__main__":
    OUT_DIR.mkdir(exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path="/usr/bin/chromium")
        context = browser.new_context()
        context.add_init_script("localStorage.setItem('sabaaek-public-theme', JSON.stringify({theme:'obsidian_glass', savedAt:Date.now()}))")
        context.route("**/*", route_price_data)
        page = context.new_page()
        report = {name:audit(page, name, *size) for name,size in VIEWPORTS.items()}
        browser.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    for name, item in report.items():
        assert not item["scroll"]["horizontal"], f"{name}: horizontal overflow"
        assert item["price"] != "—", f"{name}: price did not render"
        assert item["chart"]["height"] > 0, f"{name}: chart panel is missing"
        assert not item["scroll"]["vertical"], f"{name}: content requires vertical scrolling"
        assert item["qrDisplay"] != "none", f"{name}: QR should remain available in landscape"
        assert len(item["karats"]) == 3, f"{name}: karat card count changed"
        ys = {card["y"] for card in item["karats"]}
        assert len(ys) == 1, f"{name}: karat cards are split across rows"
    assert report["tv_4k"]["shell"]["width"] >= int(report["tv_4k"]["viewport"]["width"] * 0.60), "tv_4k: composition is too small for the display"
    print("LANDSCAPE_LAYOUT_AUDIT_PASSED")
