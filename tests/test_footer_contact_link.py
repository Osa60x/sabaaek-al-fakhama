from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_footer_uses_verified_whatsapp_number():
    for path in [ROOT / "index.html", ROOT / "workers/sabaaek-site-staging/public/index.html"]:
        text = path.read_text(encoding="utf-8")
        assert "wa.me/Osa60x" not in text
        assert "wa.me/966550441259" in text
        assert "@Osa60x" in text


if __name__ == "__main__":
    test_footer_uses_verified_whatsapp_number()
