from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "workers" / "sabaaek-gold-api" / "src"


def test_gold_provider_boundary_exists_and_is_used_by_worker():
    provider = (SRC / "providers.js").read_text(encoding="utf-8")
    worker = (SRC / "index.js").read_text(encoding="utf-8")
    assert "GoldProvider" in provider
    assert "createGoldProvider" in provider
    assert "getSpotPrice" in provider
    assert "from \"./providers.js\"" in worker
    assert "fetchPrimary" not in worker


if __name__ == "__main__":
    test_gold_provider_boundary_exists_and_is_used_by_worker()
