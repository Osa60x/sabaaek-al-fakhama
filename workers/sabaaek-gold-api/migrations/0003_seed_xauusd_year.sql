-- One-time, non-destructive 12-month seed for the public 1y chart.
--
-- Primary source (11 monthly OHLC rows):
-- https://www.myfxbook.com/forex-market/currencies/XAUUSD-historical-data
-- Queried 2026-08-27 with symbol XAUUSD, 1-month timeframe, 2025-08-01 through 2026-08-01.
--
-- March 2026 was absent from that public monthly response. It is retained as a clearly
-- identified average-only reference row from the public World Bank monthly series:
-- https://datahub.io/core/gold-prices/_r/-/data/monthly-processed.csv
-- The row intentionally sets open/high/low/close to the same published monthly average;
-- it does not invent an intramonth range.
--
-- All values are USD per troy ounce. month_ts uses the Riyadh month boundary, matching
-- `monthStart()` in the Sabaaek worker. The current in-progress month is excluded so
-- scheduled gold-api.com collection remains its sole owner.

-- month: 2025-08
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1753995600000, 3289.89, 3453.99, 3281.43, 3448.12, 1, 'myfxbook_xauusd_monthly_ohlc')
ON CONFLICT(month_ts) DO NOTHING;

-- month: 2025-09
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1756674000000, 3444.29, 3871.72, 3437.04, 3863.02, 1, 'myfxbook_xauusd_monthly_ohlc')
ON CONFLICT(month_ts) DO NOTHING;

-- month: 2025-10
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1759266000000, 3863.04, 4381.20, 3819.14, 4001.93, 1, 'myfxbook_xauusd_monthly_ohlc')
ON CONFLICT(month_ts) DO NOTHING;

-- month: 2025-11
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1761944400000, 3983.73, 4245.12, 3928.48, 4222.78, 1, 'myfxbook_xauusd_monthly_ohlc')
ON CONFLICT(month_ts) DO NOTHING;

-- month: 2025-12
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1764536400000, 4229.15, 4549.88, 4163.31, 4311.51, 1, 'myfxbook_xauusd_monthly_ohlc')
ON CONFLICT(month_ts) DO NOTHING;

-- month: 2026-01
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1767214800000, 4328.78, 5598.18, 4309.71, 4882.54, 1, 'myfxbook_xauusd_monthly_ohlc')
ON CONFLICT(month_ts) DO NOTHING;

-- month: 2026-02
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1769893200000, 4781.13, 5280.82, 4402.69, 5279.95, 1, 'myfxbook_xauusd_monthly_ohlc')
ON CONFLICT(month_ts) DO NOTHING;

-- month: 2026-03
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1772312400000, 4856.00, 4856.00, 4856.00, 4856.00, 1, 'world_bank_gold_monthly_average')
ON CONFLICT(month_ts) DO NOTHING;

-- month: 2026-04
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1774990800000, 4681.82, 4889.37, 4510.29, 4621.70, 1, 'myfxbook_xauusd_monthly_ohlc')
ON CONFLICT(month_ts) DO NOTHING;

-- month: 2026-05
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1777582800000, 4628.14, 4773.54, 4366.29, 4539.83, 1, 'myfxbook_xauusd_monthly_ohlc')
ON CONFLICT(month_ts) DO NOTHING;

-- month: 2026-06
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1780261200000, 4522.08, 4546.29, 3942.19, 4007.44, 1, 'myfxbook_xauusd_monthly_ohlc')
ON CONFLICT(month_ts) DO NOTHING;

-- month: 2026-07
INSERT INTO gold_monthly (month_ts, open_price, high_price, low_price, close_price, point_count, source)
VALUES (1782853200000, 4011.95, 4203.10, 3959.23, 4046.24, 1, 'myfxbook_xauusd_monthly_ohlc')
ON CONFLICT(month_ts) DO NOTHING;
