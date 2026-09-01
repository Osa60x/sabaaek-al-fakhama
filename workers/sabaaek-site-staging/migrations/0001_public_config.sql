CREATE TABLE IF NOT EXISTS site_settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS price_adjustments (
  carat TEXT PRIMARY KEY CHECK (carat IN ('24', '21', '18')),
  adjustment_sar REAL NOT NULL CHECK (adjustment_sar >= -5000 AND adjustment_sar <= 5000),
  updated_at TEXT NOT NULL
);

INSERT INTO site_settings (key, value_json, updated_at)
VALUES
  ('theme', '"emerald_classic"', '2026-08-26T02:40:44.880202+00:00'),
  ('contact_actions', '[{"kind":"whatsapp","label":"تواصل عبر واتساب","value":"966550441259"},{"kind":"phone","label":"اتصال هاتفي","value":"966550441259"}]', '2026-08-26T02:40:44.880202+00:00')
ON CONFLICT(key) DO UPDATE SET
  value_json = excluded.value_json,
  updated_at = excluded.updated_at;

INSERT INTO price_adjustments (carat, adjustment_sar, updated_at)
VALUES
  ('24', 0, '2026-08-26T14:16:27.236648+00:00'),
  ('21', 0, '2026-08-26T14:16:27.236648+00:00'),
  ('18', 0, '2026-08-26T14:16:27.236648+00:00')
ON CONFLICT(carat) DO UPDATE SET
  adjustment_sar = excluded.adjustment_sar,
  updated_at = excluded.updated_at;
