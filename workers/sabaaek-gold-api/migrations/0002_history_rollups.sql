CREATE TABLE IF NOT EXISTS last_good_quote (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  price REAL NOT NULL,
  source TEXT NOT NULL,
  source_updated_at INTEGER NOT NULL,
  fetched_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS gold_daily (
  day_ts INTEGER PRIMARY KEY,
  open_price REAL NOT NULL,
  high_price REAL NOT NULL,
  low_price REAL NOT NULL,
  close_price REAL NOT NULL,
  point_count INTEGER NOT NULL,
  source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gold_monthly (
  month_ts INTEGER PRIMARY KEY,
  open_price REAL NOT NULL,
  high_price REAL NOT NULL,
  low_price REAL NOT NULL,
  close_price REAL NOT NULL,
  point_count INTEGER NOT NULL,
  source TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gold_points_ts ON gold_points(ts);
CREATE INDEX IF NOT EXISTS idx_gold_daily_day_ts ON gold_daily(day_ts);
CREATE INDEX IF NOT EXISTS idx_gold_monthly_month_ts ON gold_monthly(month_ts);

INSERT INTO last_good_quote(id, price, source, source_updated_at, fetched_at)
SELECT 1, price, source, source_updated_at, fetched_at
FROM gold_points
ORDER BY ts DESC
LIMIT 1
ON CONFLICT(id) DO UPDATE SET
  price = excluded.price,
  source = excluded.source,
  source_updated_at = excluded.source_updated_at,
  fetched_at = excluded.fetched_at;

INSERT INTO gold_daily(day_ts, open_price, high_price, low_price, close_price, point_count, source)
SELECT
  day_ts,
  (
    SELECT first_point.price FROM gold_points AS first_point
    WHERE CAST((first_point.ts + 10800000) / 86400000 AS INTEGER) * 86400000 - 10800000 = day_ts
    ORDER BY first_point.ts ASC LIMIT 1
  ),
  MAX(price),
  MIN(price),
  (
    SELECT last_point.price FROM gold_points AS last_point
    WHERE CAST((last_point.ts + 10800000) / 86400000 AS INTEGER) * 86400000 - 10800000 = day_ts
    ORDER BY last_point.ts DESC LIMIT 1
  ),
  COUNT(*),
  MIN(source)
FROM (
  SELECT *, CAST((ts + 10800000) / 86400000 AS INTEGER) * 86400000 - 10800000 AS day_ts
  FROM gold_points
)
GROUP BY day_ts
ON CONFLICT(day_ts) DO NOTHING;

INSERT INTO gold_monthly(month_ts, open_price, high_price, low_price, close_price, point_count, source)
SELECT
  month_ts,
  (
    SELECT first_day.open_price FROM gold_daily AS first_day
    WHERE CAST(strftime('%Y%m', datetime(first_day.day_ts / 1000, 'unixepoch', '+3 hours')) AS INTEGER) = month_key
    ORDER BY first_day.day_ts ASC LIMIT 1
  ),
  MAX(high_price),
  MIN(low_price),
  (
    SELECT last_day.close_price FROM gold_daily AS last_day
    WHERE CAST(strftime('%Y%m', datetime(last_day.day_ts / 1000, 'unixepoch', '+3 hours')) AS INTEGER) = month_key
    ORDER BY last_day.day_ts DESC LIMIT 1
  ),
  SUM(point_count),
  MIN(source)
FROM (
  SELECT *,
    CAST(strftime('%Y%m', datetime(day_ts / 1000, 'unixepoch', '+3 hours')) AS INTEGER) AS month_key,
    (strftime('%s', date(datetime(day_ts / 1000, 'unixepoch', '+3 hours'), 'start of month')) * 1000) - 10800000 AS month_ts
  FROM gold_daily
)
GROUP BY month_key, month_ts
ON CONFLICT(month_ts) DO NOTHING;
