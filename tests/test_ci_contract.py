from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "pull-request-checks.yml"


def test_pull_request_checks_are_present_and_non_deploying():
    text = CI.read_text(encoding="utf-8")
    assert "pull_request:" in text
    assert "node --check" in text
    assert "tests/test_staging_isolation_contract.py" in text
    assert "tests/test_frontend_dependency_boundary.py" in text
    assert "wrangler deploy" not in text
    assert "deploy-pages" not in text


if __name__ == "__main__":
    test_pull_request_checks_are_present_and_non_deploying()
