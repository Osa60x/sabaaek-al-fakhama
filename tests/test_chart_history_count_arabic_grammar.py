#!/usr/bin/env python3
"""History source counters must use readable Arabic count grammar for 11+ records."""
from __future__ import annotations

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = (Path(__file__).resolve().parents[1] / 'index.html').as_uri()
NOW = int(time.time() * 1000)


def points(count: int, interval: int) -> list[dict]:
    return [{'ts': NOW - (count - item) * interval, 'price': 4500 + item, 'high': 4501 + item, 'low': 4499 + item} for item in range(count)]


def main() -> None:
    def route(route):
        url = route.request.url
        if '/quote' in url:
            payload = {'price':4592.5,'symbol':'XAU','currency':'USD','source':'test','sourceUpdatedAt':NOW,'fetchedAt':NOW,'status':'live'}
        elif 'range=1y' in url:
            payload = {'range':'1y','gap_threshold_ms':4000000000,'points':points(12, 2500000000)}
        elif '/history' in url:
            payload = {'range':'24h','gap_threshold_ms':2100000,'points':points(12, 300000)}
        elif 'public-settings' in url:
            payload = {'settings':{'theme':'obsidian_glass','contact_actions':[]}}
        elif 'public-adjustments' in url:
            payload = {'adjustments':[]}
        else:
            route.continue_()
            return
        route.fulfill(status=200, content_type='application/json', body=json.dumps(payload))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':390,'height':844})
        page.route('**/*', route)
        page.goto(URL, wait_until='domcontentloaded')
        page.locator("button[data-range='1y']").click()
        page.wait_for_function("(document.querySelector('#chart-source')?.textContent || '').includes('12')")
        assert page.locator('#chart-source').text_content().strip() == '12 ملخصاً شهرياً محفوظاً'
        browser.close()
    print('CHART_HISTORY_COUNT_ARABIC_GRAMMAR_TEST_PASSED')


if __name__ == '__main__':
    main()
