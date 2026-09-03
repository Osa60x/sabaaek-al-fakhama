from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"


def test_public_site_origin_is_not_hardcoded_in_qr_copy():
    text = INDEX.read_text(encoding="utf-8")
    assert "osa60x.github.io" not in text
    assert 'id="site-origin-label"' in text
    assert "location.origin" in text


if __name__ == "__main__":
    test_public_site_origin_is_not_hardcoded_in_qr_copy()
