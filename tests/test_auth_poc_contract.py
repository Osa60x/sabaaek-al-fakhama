from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "workers" / "sabaaek-site-staging" / "src" / "index.js"
CONFIG = ROOT / "workers" / "sabaaek-site-staging" / "wrangler.toml"


def test_auth_poc_uses_server_side_session_and_password_hashing():
    text = WORKER.read_text(encoding="utf-8")
    assert "PBKDF2" in text
    assert "HttpOnly" in text and "Secure" in text and "SameSite=Lax" in text
    assert "CSRF_COOKIE" in text and "X-CSRF-Token" in text and "csrf_failed" in text
    assert "auth_sessions" in text and "auth_users" in text
    assert "currentIdentity" in text and "requireAdmin" in text
    assert "localStorage" not in text
    assert "STAGING_BOOTSTRAP_TOKEN" in text


def test_auth_poc_enforces_role_boundaries_and_audit():
    text = WORKER.read_text(encoding="utf-8")
    assert 'minimumRole = "manager"' in text
    assert 'minimumRole === "owner" && identity.role !== "owner"' in text
    assert 'url.pathname === "/admin/site-settings"' in text
    assert 'requireAdmin(request, env, "owner")' in text
    assert 'auth_audit_log' in text
    assert 'auth_login_attempts' in text


def test_auth_poc_has_no_production_auth_binding_or_secret():
    text = WORKER.read_text(encoding="utf-8")
    config = CONFIG.read_text(encoding="utf-8")
    assert "supabase.co" not in text
    assert "SUPABASE" not in text
    assert "STAGING_BOOTSTRAP_TOKEN =" not in config
    assert "password_hash" in text


def test_auth_routes_reject_unsupported_methods_in_source():
    text = WORKER.read_text(encoding="utf-8")
    assert 'url.pathname.startsWith("/auth/")' in text
    assert 'method_not_allowed' in text
    assert 'originAllowed(request)' in text
    assert 'bad_origin' in text
