from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN = ROOT / "supabase" / "functions" / "sabaaek-admin" / "index.ts"
PUBLIC = ROOT / "index.html"


def test_admin_authorization_is_server_side_and_owner_paths_are_protected():
    text = ADMIN.read_text(encoding="utf-8")
    assert "function identityFor" in text
    assert "admin.auth.getUser(token)" in text
    assert "identity.isActive" in text
    assert "ownerOnly && identity.role !== \"owner\"" in text
    assert "action === \"audit\"" in text and "requireAdmin(request, true)" in text
    assert "action === \"site-settings\"" in text and "requireAdmin(request, true)" in text
    assert "action === \"managers\"" in text and "requireAdmin(request, true)" in text
    assert "action === \"price-adjustments\"" in text and "requireAdmin(request)" in text
    assert 'const ALLOWED_ORIGINS = new Set(["https://osa60x.github.io"])' in text
    assert '"access-control-allow-origin": "*"' not in text
    assert 'ALLOWED_ORIGINS = new Set(["*"])' not in text


def test_service_credentials_are_not_exposed_to_public_frontend():
    text = PUBLIC.read_text(encoding="utf-8")
    assert "SUPABASE_SERVICE_ROLE_KEY" not in text
    assert "SUPABASE_SECRET_KEYS" not in text


if __name__ == "__main__":
    test_admin_authorization_is_server_side_and_owner_paths_are_protected()
    test_service_credentials_are_not_exposed_to_public_frontend()
