#!/usr/bin/env python3
"""Contract for the one-time, sourced XAU/USD monthly history seed."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "workers" / "sabaaek-gold-api" / "migrations" / "0003_seed_xauusd_year.sql"

EXPECTED_MONTHS = (
    "2025-08",
    "2025-09",
    "2025-10",
    "2025-11",
    "2025-12",
    "2026-01",
    "2026-02",
    "2026-03",
    "2026-04",
    "2026-05",
    "2026-06",
    "2026-07",
)


def test_seed_exists_and_is_clearly_sourced() -> None:
    assert MIGRATION.exists(), "Expected the versioned yearly XAU/USD history seed migration"
    sql = MIGRATION.read_text(encoding="utf-8")
    assert "myfxbook.com/forex-market/currencies/XAUUSD-historical-data" in sql
    assert "myfxbook_xauusd_monthly_ohlc" in sql
    assert "world_bank_gold_monthly_average" in sql
    assert "datahub.io/core/gold-prices/_r/-/data/monthly-processed.csv" in sql


def test_seed_covers_exactly_twelve_completed_months() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    months = tuple(re.findall(r"-- month: (\d{4}-\d{2})", sql))
    assert months == EXPECTED_MONTHS, months
    assert "2026-08" not in months, "The live collector owns the current in-progress month"


def test_seed_preserves_realistic_ohlc_relationships() -> None:
    sql = MIGRATION.read_text(encoding="utf-8")
    rows = re.findall(
        r"VALUES \(\s*(\d+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*([\d.]+),\s*(\d+),\s*'(myfxbook_xauusd_monthly_ohlc|world_bank_gold_monthly_average)'\s*\)",
        sql,
    )
    assert len(rows) == 12, f"Expected 12 source rows, found {len(rows)}"
    assert [source for *_, source in rows].count("world_bank_gold_monthly_average") == 1
    for month_ts, open_price, high_price, low_price, close_price, points, source in rows:
        assert int(month_ts) > 0
        open_value, high_value, low_value, close_value = map(float, (open_price, high_price, low_price, close_price))
        assert low_value <= min(open_value, close_value) <= max(open_value, close_value) <= high_value
        assert int(points) == 1, "Each source row represents one published monthly observation"
        if source == "world_bank_gold_monthly_average":
            assert open_value == high_value == low_value == close_value, "Average-only source must not invent an OHLC range"


if __name__ == "__main__":
    test_seed_exists_and_is_clearly_sourced()
    test_seed_covers_exactly_twelve_completed_months()
    test_seed_preserves_realistic_ohlc_relationships()
    print("YEARLY_HISTORY_SEED_TESTS_PASSED")
