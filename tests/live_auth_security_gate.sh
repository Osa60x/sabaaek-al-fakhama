#!/usr/bin/env bash
set -euo pipefail
BASE="${BASE_URL:-https://sabaaek-site-staging.osa60x.workers.dev}"
WRANGLER_DIR="$(cd "$(dirname "$0")/../workers/sabaaek-site-staging" && pwd)"
TOKEN="$(head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32)"
OWNER_EMAIL="owner-gate-$(date +%s)@example.invalid"
OWNER_PASSWORD="$(head -c 36 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 20)"
MANAGER_EMAIL="manager-gate-$(date +%s)@example.invalid"
MANAGER_PASSWORD="$(head -c 36 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 20)"
OWNER_COOKIES=/tmp/sabaaek-owner-gate.cookies
MANAGER_COOKIES=/tmp/sabaaek-manager-gate.cookies
cleanup() {
  cd "$WRANGLER_DIR"
  npx -y wrangler@4.127.1 secret delete STAGING_BOOTSTRAP_TOKEN --name sabaaek-site-staging >/tmp/sabaaek-gate-secret-delete.out 2>&1 || true
  npx -y wrangler@4.127.1 d1 execute sabaaek_gold_staging --remote --command="DELETE FROM auth_sessions; DELETE FROM auth_audit_log; DELETE FROM auth_users; DELETE FROM auth_login_attempts; UPDATE price_adjustments SET adjustment_sar=0, updated_at='2026-08-26T14:16:27.236648+00:00' WHERE carat IN ('24','21','18');" >/tmp/sabaaek-gate-db-cleanup.out 2>&1 || true
}
trap cleanup EXIT
assert_status() {
  local expected="$1" actual="$2" label="$3"
  if [[ "$actual" != "$expected" ]]; then echo "FAIL $label expected=$expected actual=$actual"; exit 1; fi
  echo "PASS $label status=$actual"
}
status_body() {
  local out="$1"; curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -o "${out}.body" -w '%{http_code}' "$@" | tail -c 3 > "${out}.status"
}
cd "$WRANGLER_DIR"
printf '%s\n' "$TOKEN" | npx -y wrangler@4.127.1 secret put STAGING_BOOTSTRAP_TOKEN >/tmp/sabaaek-gate-secret-put.out
npx -y wrangler@4.127.1 d1 execute sabaaek_gold_staging --remote --command="DELETE FROM auth_sessions; DELETE FROM auth_audit_log; DELETE FROM auth_users; DELETE FROM auth_login_attempts; UPDATE price_adjustments SET adjustment_sar=0, updated_at='2026-08-26T14:16:27.236648+00:00' WHERE carat IN ('24','21','18');" >/tmp/sabaaek-gate-db-reset.out
printf 'BOOTSTRAP '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -o /tmp/gate-bootstrap.body -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H "X-Staging-Bootstrap-Token: $TOKEN" -d "{\"email\":\"$OWNER_EMAIL\",\"password\":\"$OWNER_PASSWORD\"}" "$BASE/auth/bootstrap" > /tmp/gate-bootstrap.status
assert_status 201 "$(cat /tmp/gate-bootstrap.status)" "owner bootstrap"
printf 'OWNER_LOGIN '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -c "$OWNER_COOKIES" -o /tmp/gate-owner-login.body -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d "{\"email\":\"$OWNER_EMAIL\",\"password\":\"$OWNER_PASSWORD\"}" "$BASE/auth/login" > /tmp/gate-owner-login.status
assert_status 200 "$(cat /tmp/gate-owner-login.status)" "owner login"
OWNER_CSRF="$(awk '$6 == "sabaaek_stage_csrf" {print $7}' "$OWNER_COOKIES")"
if [[ -z "$OWNER_CSRF" ]]; then echo 'FAIL owner csrf cookie missing'; exit 1; fi
printf 'MANAGER_CREATE '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -b "$OWNER_COOKIES" -o /tmp/gate-manager-create.body -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H "X-CSRF-Token: $OWNER_CSRF" -d "{\"email\":\"$MANAGER_EMAIL\",\"password\":\"$MANAGER_PASSWORD\"}" "$BASE/admin/managers" > /tmp/gate-manager-create.status
assert_status 201 "$(cat /tmp/gate-manager-create.status)" "owner creates manager"
MANAGER_ID="$(python3 -c 'import json; print(json.load(open("/tmp/gate-manager-create.body"))["manager"]["id"])')"
printf 'MANAGER_LOGIN '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -c "$MANAGER_COOKIES" -o /tmp/gate-manager-login.body -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d "{\"email\":\"$MANAGER_EMAIL\",\"password\":\"$MANAGER_PASSWORD\"}" "$BASE/auth/login" > /tmp/gate-manager-login.status
assert_status 200 "$(cat /tmp/gate-manager-login.status)" "manager login"
MANAGER_CSRF="$(awk '$6 == "sabaaek_stage_csrf" {print $7}' "$MANAGER_COOKIES")"
printf 'MANAGER_PRICE '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -b "$MANAGER_COOKIES" -o /tmp/gate-manager-price.body -w '%{http_code}' -X PUT -H 'Content-Type: application/json' -H "X-CSRF-Token: $MANAGER_CSRF" -d '{"carat":"24","adjustment_sar":1.25}' "$BASE/admin/price-adjustments" > /tmp/gate-manager-price.status
assert_status 200 "$(cat /tmp/gate-manager-price.status)" "manager price update"
printf 'MANAGER_SETTINGS '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -b "$MANAGER_COOKIES" -o /tmp/gate-manager-settings.body -w '%{http_code}' -X PUT -H 'Content-Type: application/json' -H "X-CSRF-Token: $MANAGER_CSRF" -d '{"theme":"ivory_luxe"}' "$BASE/admin/site-settings" > /tmp/gate-manager-settings.status
assert_status 403 "$(cat /tmp/gate-manager-settings.status)" "manager cannot update settings"
printf 'MANAGER_MANAGERS '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -b "$MANAGER_COOKIES" -o /tmp/gate-manager-managers.body -w '%{http_code}' -X POST -H 'Content-Type: application/json' -H "X-CSRF-Token: $MANAGER_CSRF" -d '{"email":"other@example.invalid","password":"long-enough-password"}' "$BASE/admin/managers" > /tmp/gate-manager-managers.status
assert_status 403 "$(cat /tmp/gate-manager-managers.status)" "manager cannot manage managers"
printf 'MANAGER_AUDIT '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -b "$MANAGER_COOKIES" -o /tmp/gate-manager-audit.body -w '%{http_code}' "$BASE/admin/audit" > /tmp/gate-manager-audit.status
assert_status 403 "$(cat /tmp/gate-manager-audit.status)" "manager cannot read audit"
printf 'CSRF '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -b "$MANAGER_COOKIES" -o /tmp/gate-csrf.body -w '%{http_code}' -X PUT -H 'Content-Type: application/json' -d '{"carat":"21","adjustment_sar":1}' "$BASE/admin/price-adjustments" > /tmp/gate-csrf.status
assert_status 403 "$(cat /tmp/gate-csrf.status)" "missing csrf rejected"
printf 'ORIGIN '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -b "$MANAGER_COOKIES" -o /tmp/gate-origin.body -w '%{http_code}' -X PUT -H 'Origin: https://evil.example' -H 'Content-Type: application/json' -H "X-CSRF-Token: $MANAGER_CSRF" -d '{"carat":"21","adjustment_sar":1}' "$BASE/admin/price-adjustments" > /tmp/gate-origin.status
assert_status 403 "$(cat /tmp/gate-origin.status)" "bad origin rejected"
printf 'INVALID_JSON '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -b "$MANAGER_COOKIES" -o /tmp/gate-json.body -w '%{http_code}' -X PUT -H 'Content-Type: application/json' -H "X-CSRF-Token: $MANAGER_CSRF" -d '{not-json' "$BASE/admin/price-adjustments" > /tmp/gate-json.status
assert_status 400 "$(cat /tmp/gate-json.status)" "invalid json rejected"
printf 'OUT_OF_RANGE '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -b "$MANAGER_COOKIES" -o /tmp/gate-range.body -w '%{http_code}' -X PUT -H 'Content-Type: application/json' -H "X-CSRF-Token: $MANAGER_CSRF" -d '{"carat":"18","adjustment_sar":5001}' "$BASE/admin/price-adjustments" > /tmp/gate-range.status
assert_status 400 "$(cat /tmp/gate-range.status)" "out of range price rejected"
printf 'MALICIOUS_SETTINGS '
curl --retry 1 --retry-delay 0 --retry-all-errors -sS --max-time 10 -b "$OWNER_COOKIES" -o /tmp/gate-xss.body -w '%{http_code}' -X PUT -H 'Content-Type: application/json' -H "X-CSRF-Token: $OWNER_CSRF" -d '{"contact_actions":[{"kind":"whatsapp","label":"<script>alert(1)</script>","value":"javascript:alert(1)"}]}' "$BASE/admin/site-settings" > /tmp/gate-xss.status
assert_status 400 "$(cat /tmp/gate-xss.status)" "unsafe owner settings rejected"
printf 'RATE_LIMIT '
statuses=()
for i in $(seq 1 9); do statuses+=("$(curl --retry 1 --retry-delay 0 --retry-all-errors --connect-timeout 3 -sS --max-time 8 -o /tmp/gate-rate-$i.body -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d "{\"email\":\"$MANAGER_EMAIL\",\"password\":\"wrong-password-$i\"}" "$BASE/auth/login")"); sleep 1; done
printf '%s\n' "${statuses[@]}" | tee /tmp/gate-rate-all.status >/dev/null
assert_status 429 "${statuses[8]}" "brute force rate limit"
printf 'PASS live auth security gate\n'
