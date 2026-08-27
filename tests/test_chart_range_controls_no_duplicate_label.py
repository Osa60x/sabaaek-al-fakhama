#!/usr/bin/env python3
"""The selected range button is the label; a duplicated range badge wastes chart header space."""
from __future__ import annotations

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = (Path(__file__).resolve().parents[1] / 'index.html').as_uri()
NOW = int(time.time() * 1000)


def main() -> None:
    def route(route):
        url = route.request.url
        if '/quote' in url:
            payload = {'price':4592.5,'symbol':'XAU','currency':'USD','source':'test','sourceUpdatedAt':NOW,'fetchedAt':NOW,'status':'live'}
        elif '/history' in url:
            payload = {'range':'24h','gap_threshold_ms':2100000,'points':[{'ts':NOW-1800000,'price':4588.0,'high':4588.0,'low':4588.0},{'ts':NOW,'price':4592.5,'high':4592.5,'low':4592.5}]}
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
        page = browser.new_page(viewport={'width':1366,'height':768})
        page.route('**/*', route)
        page.goto(URL, wait_until='domcontentloaded')
        page.wait_for_function("document.querySelectorAll('#chart-ranges button').length === 3")
        assert page.locator('#range-label').evaluate("el => getComputedStyle(el).display") == 'none'
        assert page.locator('#chart-ranges button').count() == 3
        browser.close()
    print('CHART_RANGE_CONTROLS_NO_DUPLICATE_LABEL_TEST_PASSED')


if __name__ == '__main__':
    main()
