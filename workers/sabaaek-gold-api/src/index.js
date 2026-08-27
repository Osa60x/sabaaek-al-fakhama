const PRIMARY_URL = "https://api.gold-api.com/price/XAU/USD";
const MINUTE = 60 * 1000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const RIYADH_OFFSET = 3 * HOUR;
const RAW_RETENTION_MS = 36 * HOUR;
const DAILY_RETENTION_MS = 400 * DAY;
const memoryCache = { quote: null, until: 0 };
const QUOTE_READ_FRESH_MS = 5 * MINUTE + 30 * 1000;

const HISTORY_RANGES = {
  "24h": {
    title: "24 ساعة",
    resolution: "raw",
    from: (now) => now - DAY,
    gapThresholdMs: 35 * MINUTE,
  },
  "30d": {
    title: "شهر",
    resolution: "daily",
    from: (now) => now - 30 * DAY,
    gapThresholdMs: 38 * HOUR,
  },
  "1y": {
    title: "سنة",
    resolution: "monthly",
    from: (now) => now - 365 * DAY,
    gapThresholdMs: 46 * DAY,
  },
};

function cors(request, env) {
  const origin = request.headers.get("Origin");
  const allowed = new Set([
    "https://osa60x.github.io",
    "https://osa6000.github.io",
    ...String(env.ALLOWED_ORIGIN || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
  ]);
  if (!origin || !allowed.has(origin)) return {};
  return {
    "Access-Control-Allow-Origin": origin,
    Vary: "Origin",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(request, env, body, init = {}) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...cors(request, env),
      ...(init.headers || {}),
    },
  });
}

function edgeCacheKey(request) {
  const url = new URL(request.url);
  url.searchParams.set("__sabaaek_origin", request.headers.get("Origin") || "none");
  return new Request(url.toString(), { method: "GET" });
}

async function cachedEndpoint(request, env, ttlSeconds, createResponse, ctx) {
  const cache = caches.default;
  const key = edgeCacheKey(request);
  const cached = await cache.match(key);
  if (cached) return cached;

  const response = await createResponse();
  if (!response.ok) return response;
  const headers = new Headers(response.headers);
  headers.set("Cache-Control", `public, max-age=${ttlSeconds}, stale-while-revalidate=${ttlSeconds}`);
  const cacheable = new Response(response.body, { status: response.status, statusText: response.statusText, headers });
  ctx.waitUntil(cache.put(key, cacheable.clone()));
  return cacheable;
}

function dayStart(ts) {
  return Math.floor((ts + RIYADH_OFFSET) / DAY) * DAY - RIYADH_OFFSET;
}

function monthStart(ts) {
  const riyadhDate = new Date(ts + RIYADH_OFFSET);
  return Date.UTC(riyadhDate.getUTCFullYear(), riyadhDate.getUTCMonth(), 1) - RIYADH_OFFSET;
}

function validateQuote(raw, previous) {
  const price = Number(raw?.price);
  const symbol = String(raw?.symbol || "").toUpperCase();
  const currency = raw?.currency ? String(raw.currency).toUpperCase() : "USD";
  const sourceUpdatedAt = Date.parse(String(raw?.sourceUpdatedAt ?? raw?.updatedAt ?? ""));
  const fetchedAt = Date.now();

  if (
    symbol !== "XAU" ||
    currency !== "USD" ||
    !Number.isFinite(price) ||
    price < 1000 ||
    price > 10000 ||
    !Number.isFinite(sourceUpdatedAt)
  ) {
    throw new Error("invalid_quote");
  }
  if (fetchedAt - sourceUpdatedAt > 30 * MINUTE) throw new Error("stale_quote");
  if (previous && (sourceUpdatedAt < previous.sourceUpdatedAt || Math.abs(price - previous.price) / previous.price > 0.2)) {
    throw new Error("outlier_quote");
  }

  return {
    price,
    symbol: "XAU",
    currency: "USD",
    source: "gold-api.com",
    sourceUpdatedAt,
    fetchedAt,
    status: "live",
  };
}

async function fetchPrimary(previous) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const response = await fetch(PRIMARY_URL, {
      headers: { Accept: "application/json" },
      signal: controller.signal,
      cf: { cacheTtl: 0 },
    });
    if (!response.ok) throw new Error(`source_${response.status}`);
    return validateQuote(await response.json(), previous);
  } finally {
    clearTimeout(timeout);
  }
}

async function readLatest(env) {
  const snapshot = await env.DB.prepare(
    "SELECT price, source, source_updated_at, fetched_at FROM last_good_quote WHERE id = 1"
  ).first();
  if (!snapshot) return undefined;
  return {
    price: Number(snapshot.price),
    symbol: "XAU",
    currency: "USD",
    source: snapshot.source,
    sourceUpdatedAt: Number(snapshot.source_updated_at),
    fetchedAt: Number(snapshot.fetched_at),
    status: "cached",
  };
}

async function persistQuote(env, quote) {
  const dayTs = dayStart(quote.fetchedAt);
  const monthTs = monthStart(quote.fetchedAt);
  await env.DB.batch([
    env.DB.prepare(
      "INSERT INTO gold_points(ts, price, source, source_updated_at, fetched_at) VALUES (?, ?, ?, ?, ?)"
    ).bind(quote.fetchedAt, quote.price, quote.source, quote.sourceUpdatedAt, quote.fetchedAt),
    env.DB.prepare(
      "INSERT INTO last_good_quote(id, price, source, source_updated_at, fetched_at) VALUES (1, ?, ?, ?, ?) " +
        "ON CONFLICT(id) DO UPDATE SET price = excluded.price, source = excluded.source, source_updated_at = excluded.source_updated_at, fetched_at = excluded.fetched_at"
    ).bind(quote.price, quote.source, quote.sourceUpdatedAt, quote.fetchedAt),
    env.DB.prepare(
      "INSERT INTO gold_daily(day_ts, open_price, high_price, low_price, close_price, point_count, source) VALUES (?, ?, ?, ?, ?, 1, ?) " +
        "ON CONFLICT(day_ts) DO UPDATE SET high_price = MAX(gold_daily.high_price, excluded.high_price), low_price = MIN(gold_daily.low_price, excluded.low_price), close_price = excluded.close_price, point_count = gold_daily.point_count + 1, source = excluded.source"
    ).bind(dayTs, quote.price, quote.price, quote.price, quote.price, quote.source),
    env.DB.prepare(
      "INSERT INTO gold_monthly(month_ts, open_price, high_price, low_price, close_price, point_count, source) VALUES (?, ?, ?, ?, ?, 1, ?) " +
        "ON CONFLICT(month_ts) DO UPDATE SET high_price = MAX(gold_monthly.high_price, excluded.high_price), low_price = MIN(gold_monthly.low_price, excluded.low_price), close_price = excluded.close_price, point_count = gold_monthly.point_count + 1, source = excluded.source"
    ).bind(monthTs, quote.price, quote.price, quote.price, quote.price, quote.source),
    env.DB.prepare("DELETE FROM gold_points WHERE ts < ?").bind(quote.fetchedAt - RAW_RETENTION_MS),
    env.DB.prepare("DELETE FROM gold_daily WHERE day_ts < ?").bind(quote.fetchedAt - DAILY_RETENTION_MS),
  ]);
}

async function recordQuote(env, previous) {
  const quote = await fetchPrimary(previous);
  await persistQuote(env, quote);
  return quote;
}

async function quote(env) {
  if (memoryCache.quote && memoryCache.until > Date.now()) {
    return { ...memoryCache.quote, status: "cached" };
  }
  const previous = await readLatest(env);
  if (previous && Date.now() - previous.fetchedAt <= QUOTE_READ_FRESH_MS) {
    memoryCache.quote = previous;
    memoryCache.until = Date.now() + 25 * 1000;
    return previous;
  }
  try {
    const fresh = await recordQuote(env, previous);
    memoryCache.quote = fresh;
    memoryCache.until = Date.now() + 25 * 1000;
    return fresh;
  } catch (error) {
    if (previous) return previous;
    throw error;
  }
}

function selectHistoryQuery(range, now) {
  const config = HISTORY_RANGES[range];
  if (range === "24h") {
    return envQuery(
      "SELECT ts, price, price AS high, price AS low, source FROM gold_points WHERE ts >= ? ORDER BY ts ASC",
      [config.from(now)]
    );
  }
  if (range === "30d") {
    return envQuery(
      "SELECT day_ts AS ts, close_price AS price, high_price AS high, low_price AS low, source FROM gold_daily WHERE day_ts >= ? ORDER BY day_ts ASC",
      [config.from(now)]
    );
  }
  return envQuery(
    "SELECT month_ts AS ts, close_price AS price, high_price AS high, low_price AS low, source FROM gold_monthly WHERE month_ts >= ? ORDER BY month_ts ASC",
    [config.from(now)]
  );
}

function envQuery(sql, values) {
  return { sql, values };
}

async function history(env, requestedRange) {
  const range = Object.hasOwn(HISTORY_RANGES, requestedRange) ? requestedRange : "24h";
  const config = HISTORY_RANGES[range];
  const query = selectHistoryQuery(range, Date.now());
  const result = await env.DB.prepare(query.sql).bind(...query.values).all();
  const points = (result.results || []).map((row) => ({
    ts: Number(row.ts),
    price: Number(row.price),
    high: Number(row.high),
    low: Number(row.low),
    source: row.source,
  }));
  const highs = points.map((point) => point.high);
  const lows = points.map((point) => point.low);
  return {
    range,
    title: config.title,
    resolution: config.resolution,
    gap_threshold_ms: config.gapThresholdMs,
    points,
    high: highs.length ? Math.max(...highs) : null,
    low: lows.length ? Math.min(...lows) : null,
    first: points[0]?.price ?? null,
    last: points.at(-1)?.price ?? null,
    lastPointAt: points.at(-1)?.ts ?? null,
    count: points.length,
  };
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") return new Response(null, { headers: cors(request, env) });
    const url = new URL(request.url);
    try {
      if (url.pathname === "/quote") return cachedEndpoint(request, env, 12, () => quote(env).then((value) => json(request, env, value)), ctx);
      if (url.pathname === "/history") return cachedEndpoint(request, env, 20, () => history(env, url.searchParams.get("range") || "24h").then((value) => json(request, env, value)), ctx);
      return json(request, env, { error: "not_found" }, { status: 404 });
    } catch {
      const cached = await readLatest(env);
      if (url.pathname === "/quote" && cached) return json(request, env, cached);
      return json(request, env, { error: "unavailable" }, { status: 503 });
    }
  },

  async scheduled(_event, env, ctx) {
    ctx.waitUntil(
      readLatest(env)
        .then((previous) => recordQuote(env, previous))
        .catch(() => undefined)
    );
  },
};
