#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE_URL:-https://sabaaek-site-staging.osa60x.workers.dev}"
status=$(curl -sS --max-time 30 -o /tmp/sabaaek-closed-route.body -w '%{http_code}' "$BASE/__security/pbkdf2-benchmark?iterations=100000")
if [[ "$status" != "404" ]]; then
  echo "FAIL closed benchmark route expected=404 actual=$status"
  exit 1
fi
echo "PASS closed benchmark route status=404"
