from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "workers" / "sabaaek-site-staging" / "wrangler.toml"
WORKER = ROOT / "workers" / "sabaaek-site-staging" / "src" / "index.js"
PUBLIC = ROOT / "workers" / "sabaaek-site-staging" / "public"


def test_staging_files_exist_and_are_not_production_bindings():
    assert CONFIG.exists(), "staging wrangler config is required"
    assert WORKER.exists(), "staging worker entrypoint is required"
    assert (PUBLIC / "index.html").exists(), "staging must contain a public index"

    config = CONFIG.read_text(encoding="utf-8")
    worker = WORKER.read_text(encoding="utf-8")

    assert 'name = "sabaaek-site-staging"' in config
    assert 'compatibility_flags = ["global_fetch_strictly_public"]' in config
    assert 'name = "sabaaek-gold-api"' not in config
    assert "sabaaek_gold" not in config
    assert "9d2acafd-7daf-4f82-b689-50cacfb6f000" not in config
    assert "gold.osa60x.workers.dev" not in config
    assert "rsrtwubjdfdnflkttwwy" not in config
    assert "rsrtwubjdfdnflkttwwy" not in worker


def test_staging_worker_allows_only_read_proxy_methods():
    worker = WORKER.read_text(encoding="utf-8")
    assert "GET" in worker
    assert re.search(r"method\s*!==\s*[\"']GET[\"']", worker)
    config = CONFIG.read_text(encoding="utf-8")
    assert "sabaaek-gold-api.osa60x.workers.dev" in config
    assert "POST" not in worker
    assert "PUT" not in worker
    assert "DELETE" not in worker
    assert "Content-Security-Policy" in worker
    assert "X-Content-Type-Options" in worker
    assert "Referrer-Policy" in worker


if __name__ == "__main__":
    test_staging_files_exist_and_are_not_production_bindings()
    test_staging_worker_allows_only_read_proxy_methods()
