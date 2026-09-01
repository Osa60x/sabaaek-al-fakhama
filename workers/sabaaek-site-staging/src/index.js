const PUBLIC_API_PATHS = new Set(["/quote", "/history"]);
const PUBLIC_CONFIG_PATHS = new Set(["/public-settings", "/public-adjustments"]);

function withSecurityHeaders(response) {
  const headers = new Headers(response.headers);
  headers.set("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'");
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  headers.set("X-Frame-Options", "DENY");
  headers.set("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload");
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}

function json(data, status = 200) {
  return withSecurityHeaders(new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
    },
  }));
}

function parseJson(value, fallback) {
  try {
    return JSON.parse(value);
  } catch {
    return fallback;
  }
}

async function readPublicSettings(env) {
  if (!env.DB) return json({ error: "staging_database_unavailable" }, 503);
  const result = await env.DB.prepare(
    "SELECT key, value_json, updated_at FROM site_settings WHERE key IN ('theme', 'contact_actions') LIMIT 2",
  ).all();
  const settings = { theme: "emerald_classic", contact_actions: [] };
  let updatedAt = null;
  for (const row of result.results || []) {
    if (row.key === "theme") settings.theme = parseJson(row.value_json, "emerald_classic");
    if (row.key === "contact_actions") settings.contact_actions = parseJson(row.value_json, []);
    if (row.updated_at && (!updatedAt || row.updated_at > updatedAt)) updatedAt = row.updated_at;
  }
  if (updatedAt) settings.updated_at = updatedAt;
  return json({ settings });
}

async function readPublicAdjustments(env) {
  if (!env.DB) return json({ error: "staging_database_unavailable" }, 503);
  const result = await env.DB.prepare(
    "SELECT carat, adjustment_sar, updated_at FROM price_adjustments WHERE carat IN ('24', '21', '18') ORDER BY CASE carat WHEN '24' THEN 1 WHEN '21' THEN 2 WHEN '18' THEN 3 END LIMIT 3",
  ).all();
  return json({ adjustments: result.results || [] });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/admin.html" || url.pathname.startsWith("/admin/")) {
      return withSecurityHeaders(new Response("Not Found", { status: 404 }));
    }

    if (url.pathname.startsWith("/api/")) {
      if (request.method !== "GET") {
        return withSecurityHeaders(new Response("Method Not Allowed", {
          status: 405,
          headers: { Allow: "GET" },
        }));
      }

      const upstreamPath = url.pathname.slice("/api".length);
      if (PUBLIC_CONFIG_PATHS.has(upstreamPath)) {
        try {
          return upstreamPath === "/public-settings"
            ? await readPublicSettings(env)
            : await readPublicAdjustments(env);
        } catch {
          return json({ error: "staging_database_error" }, 503);
        }
      }

      if (!PUBLIC_API_PATHS.has(upstreamPath)) {
        return withSecurityHeaders(new Response("Not Found", { status: 404 }));
      }

      const upstream = new URL(env.UPSTREAM_PUBLIC_API);
      upstream.pathname = upstreamPath;
      upstream.search = url.search;
      const response = await fetch(new Request(upstream, { method: "GET" }));
      const headers = new Headers(response.headers);
      headers.set("Cache-Control", "no-store");
      return withSecurityHeaders(new Response(response.body, { status: response.status, headers }));
    }

    return withSecurityHeaders(await env.ASSETS.fetch(request));
  },
};
