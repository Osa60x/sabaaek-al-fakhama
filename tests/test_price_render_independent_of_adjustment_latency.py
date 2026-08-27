#!/usr/bin/env python3
"""A slow public-adjustments read must not block the first valid quote render."""
from __future__ import annotations

from pathlib import Path
from playwright.sync_api import sync_playwright

URL = (Path(__file__).resolve().parents[1] / "index.html").as_uri()
INIT_SCRIPT = r"""
(() => {
  const now = Date.now();
  const quote = {price:4592.5,symbol:'XAU',currency:'USD',source:'test',sourceUpdatedAt:now,fetchedAt:now,status:'live'};
  const points = {range:'24h',gap_threshold_ms:2100000,points:[
    {ts:now-1800000,price:4588.4,high:4588.4,low:4588.4},
    {ts:now-900000,price:4590.3,high:4590.3,low:4590.3},
    {ts:now,price:4592.5,high:4592.5,low:4592.5}
  ]};
  const json = payload => Promise.resolve(new Response(JSON.stringify(payload), {status:200,headers:{'Content-Type':'application/json'}}));
  window.fetch = input => {
    const url = String(input);
    if (url.includes('sabaaek-gold-api.osa60x.workers.dev/quote')) return json(quote);
    if (url.includes('sabaaek-gold-api.osa60x.workers.dev/history')) return json(points);
    if (url.includes('action=public-adjustments')) return new Promise(resolve => setTimeout(() => resolve(new Response(JSON.stringify({adjustments:[]}), {status:200,headers:{'Content-Type':'application/json'}})), 1200));
    if (url.includes('action=public-settings')) return json({settings:{theme:'obsidian_glass',contact_actions:[]}});
    return json({});
  };
})();
"""


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 390, "height": 844})
        context.add_init_script(INIT_SCRIPT)
        page = context.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_function("document.querySelector('#ounce')?.textContent.trim() !== '—'", timeout=500)
        assert page.locator('#ounce').text_content().strip() == '4,592.50'
        browser.close()
    print('PRICE_RENDER_NOT_BLOCKED_BY_ADJUSTMENTS_TEST_PASSED')


if __name__ == '__main__':
    main()
