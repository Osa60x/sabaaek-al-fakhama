from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "workers" / "sabaaek-site-staging" / "public" / "index.html"
WORKER = ROOT / "workers" / "sabaaek-site-staging" / "src" / "index.js"
WRANGLER = ROOT / "workers" / "sabaaek-site-staging" / "wrangler.toml"


def test_staging_frontend_has_no_direct_external_backend_dependencies():
    text = PUBLIC.read_text(encoding="utf-8")
    assert "supabase.co" not in text
    assert "gold-api.com" not in text
    assert "PRIMARY_API" not in text
    assert "ADJUSTMENT_API" not in text
    assert "sabaaek-gold-api.osa60x.workers.dev" not in text
    assert "/public-settings" in text
    assert "/public-adjustments" in text


def test_staging_worker_reads_public_config_from_d1_without_write_routes():
    text = WORKER.read_text(encoding="utf-8")
    config = WRANGLER.read_text(encoding="utf-8")
    assert "public-settings" in text
    assert "public-adjustments" in text
    assert "env.DB" in text
    assert "site_settings" in text
    assert "price_adjustments" in text
    assert "UPSTREAM_PUBLIC_CONFIG_API" not in config
    assert 'request.method !== "GET"' in text
    assert "POST" not in config and "PUT" not in config and "DELETE" not in config


if __name__ == "__main__":
    test_staging_frontend_has_no_direct_external_backend_dependencies()
    test_staging_worker_reads_public_config_from_d1_without_write_routes()
