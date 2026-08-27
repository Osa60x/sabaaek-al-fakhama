#!/usr/bin/env python3
"""Read-latency contract for the public Sabaaek price worker."""
from pathlib import Path

WORKER = Path(__file__).resolve().parents[1] / "workers" / "sabaaek-gold-api" / "src" / "index.js"


def main() -> None:
    source = WORKER.read_text(encoding="utf-8")
    assert "const QUOTE_READ_FRESH_MS" in source, "Expected a bounded fresh-read window for scheduled quotes"
    assert "previous && Date.now() - previous.fetchedAt <= QUOTE_READ_FRESH_MS" in source, "Public quote must reuse the latest scheduled quote before calling the source"
    assert "async function cachedEndpoint" in source, "Expected an edge-cache wrapper for public read endpoints"
    assert "caches.default" in source, "Expected Cloudflare Cache API use for bounded public reads"
    assert "edgeCacheKey" in source and "request.headers.get(\"Origin\")" in source, "Cache must isolate CORS variants by request origin"
    assert "cachedEndpoint(request, env, 12" in source, "Quote cache must be short-lived"
    assert "cachedEndpoint(request, env, 20" in source, "History cache must be short-lived"
    print("WORKER_READ_LATENCY_CONTRACT_PASSED")


if __name__ == "__main__":
    main()
