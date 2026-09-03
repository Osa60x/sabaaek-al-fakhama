const PUBLIC_API_PATHS = new Set(["/quote", "/history"]);
const PUBLIC_CONFIG_PATHS = new Set(["/public-settings", "/public-adjustments"]);
const SESSION_COOKIE = "sabaaek_stage_session";
const CSRF_COOKIE = "sabaaek_stage_csrf";
const SESSION_TTL_MS = 8 * 60 * 60 * 1000;
const LOGIN_WINDOW_MS = 15 * 60 * 1000;
const LOGIN_LIMIT = 8;
const PBKDF2_ITERATIONS = 100_000;

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

function json(data, status = 200, extraHeaders = {}) {
  return withSecurityHeaders(new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      ...extraHeaders,
    },
  }));
}

function parseJson(value, fallback) {
  try { return JSON.parse(value); } catch { return fallback; }
}

function nowIso() { return new Date().toISOString(); }
function bytesToHex(bytes) { return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join(""); }
function hexToBytes(hex) { return new Uint8Array(hex.match(/.{1,2}/g).map((x) => parseInt(x, 16))); }
function randomHex(size = 32) { const bytes = new Uint8Array(size); crypto.getRandomValues(bytes); return bytesToHex(bytes); }

async function sha256Hex(value) {
  return bytesToHex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)));
}

async function derivePassword(password, saltHex, iterations = PBKDF2_ITERATIONS) {
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(password).buffer, { name: "PBKDF2" }, false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", salt: hexToBytes(saltHex).buffer, iterations, hash: "SHA-256" }, key, 256);
  return bytesToHex(bits);
}

async function hashPassword(password) {
  const salt = randomHex(16);
  const digest = await derivePassword(password, salt);
  return `pbkdf2-sha256$${PBKDF2_ITERATIONS}$${salt}$${digest}`;
}

async function verifyPassword(password, encoded) {
  const parts = String(encoded || "").split("$");
  if (parts.length !== 4 || parts[0] !== "pbkdf2-sha256") return false;
  const iterations = Number(parts[1]);
  if (!Number.isSafeInteger(iterations) || iterations < 100_000 || iterations > 500_000 || !/^[0-9a-f]{32}$/.test(parts[2])) return false;
  const candidate = await derivePassword(password, parts[2], iterations);
  return candidate === parts[3];
}

function cookieValue(request, name) {
  const raw = request.headers.get("Cookie") || "";
  for (const part of raw.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) return decodeURIComponent(rest.join("="));
  }
  return "";
}

function sessionCookie(value, maxAge) {
  return `${SESSION_COOKIE}=${encodeURIComponent(value)}; Max-Age=${maxAge}; Path=/; HttpOnly; Secure; SameSite=Lax`;
}
function csrfCookie(value, maxAge) {
  return `${CSRF_COOKIE}=${encodeURIComponent(value)}; Max-Age=${maxAge}; Path=/; Secure; SameSite=Lax`;
}

function validEmail(email) { return /^\S+@\S+\.\S+$/.test(email) && email.length <= 254; }
function validPassword(password) { return typeof password === "string" && password.length >= 12 && password.length <= 256; }
function validRole(role) { return role === "owner" || role === "manager"; }
function validContactActions(actions) {
  if (!Array.isArray(actions) || actions.length > 6) return false;
  return actions.every((action) => {
    if (!action || !["whatsapp", "phone", "address", "website"].includes(String(action.kind))) return false;
    if (typeof action.label !== "string" || action.label.trim().length < 1 || action.label.length > 80 || /[<>]/.test(action.label)) return false;
    if (typeof action.value !== "string" || action.value.length > 254 || /[<>]/.test(action.value)) return false;
    if (["whatsapp", "phone"].includes(action.kind) && !/^[0-9+ ()-]{7,24}$/.test(action.value)) return false;
    if (action.kind === "website") {
      try { const value = new URL(action.value); if (!["http:", "https:"].includes(value.protocol)) return false; } catch { return false; }
    }
    return true;
  });
}

function originAllowed(request) {
  const origin = request.headers.get("Origin");
  if (!origin) return true;
  return origin === new URL(request.url).origin;
}
function csrfAllowed(request) {
  const cookie = cookieValue(request, CSRF_COOKIE);
  const header = request.headers.get("X-CSRF-Token") || "";
  return Boolean(cookie && header && cookie === header);
}

async function audit(env, actorUserId, action, target = null, details = {}) {
  await env.DB.prepare("INSERT INTO auth_audit_log(actor_user_id, action, target, details_json, created_at) VALUES (?, ?, ?, ?, ?)")
    .bind(actorUserId, action, target, JSON.stringify(details), nowIso()).run();
}

async function currentIdentity(request, env) {
  const raw = cookieValue(request, SESSION_COOKIE);
  if (!raw || !env.DB) return null;
  const idHash = await sha256Hex(raw);
  const row = await env.DB.prepare(
    "SELECT s.id_hash, s.user_id, s.expires_at, u.email, u.role, u.is_active, u.password_change_required FROM auth_sessions s JOIN auth_users u ON u.id = s.user_id WHERE s.id_hash = ? LIMIT 1",
  ).bind(idHash).first();
  if (!row || row.revoked_at || Number(row.expires_at) <= Date.now() || Number(row.is_active) !== 1) return null;
  return { userId: row.user_id, email: row.email, role: row.role, passwordChangeRequired: Number(row.password_change_required) === 1 };
}

async function requireAdmin(request, env, minimumRole = "manager") {
  const identity = await currentIdentity(request, env);
  if (!identity) return { error: json({ error: "unauthorized" }, 401) };
  if (minimumRole === "owner" && identity.role !== "owner") return { error: json({ error: "forbidden" }, 403) };
  return { identity };
}

async function readBody(request) {
  const contentType = request.headers.get("Content-Type") || "";
  if (!contentType.includes("application/json")) return null;
  try { return await request.json(); } catch { return null; }
}

async function login(request, env) {
  const body = await readBody(request);
  const email = String(body?.email || "").trim().toLowerCase();
  const password = body?.password;
  if (!validEmail(email) || !validPassword(password)) return json({ error: "invalid_credentials" }, 401);
  const key = await sha256Hex(`${email}|${request.headers.get("CF-Connecting-IP") || "unknown"}`);
  const attempt = await env.DB.prepare("SELECT window_started_at, attempts, blocked_until FROM auth_login_attempts WHERE key = ? LIMIT 1").bind(key).first();
  const now = Date.now();
  if (attempt && Number(attempt.blocked_until || 0) > now) return json({ error: "too_many_attempts" }, 429, { "Retry-After": String(Math.ceil((Number(attempt.blocked_until) - now) / 1000)) });
  const user = await env.DB.prepare("SELECT id, email, password_hash, role, is_active, password_change_required FROM auth_users WHERE email = ? LIMIT 1").bind(email).first();
  const valid = user && Number(user.is_active) === 1 && await verifyPassword(password, user.password_hash);
  if (!valid) {
    const windowStart = attempt && now - Number(attempt.window_started_at) < LOGIN_WINDOW_MS ? Number(attempt.window_started_at) : now;
    const attempts = (attempt && now - Number(attempt.window_started_at) < LOGIN_WINDOW_MS ? Number(attempt.attempts) : 0) + 1;
    const blockedUntil = attempts >= LOGIN_LIMIT ? now + LOGIN_WINDOW_MS : null;
    await env.DB.prepare("INSERT INTO auth_login_attempts(key, window_started_at, attempts, blocked_until) VALUES (?, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET window_started_at=excluded.window_started_at, attempts=excluded.attempts, blocked_until=excluded.blocked_until")
      .bind(key, windowStart, attempts, blockedUntil).run();
    return json({ error: blockedUntil ? "too_many_attempts" : "invalid_credentials" }, blockedUntil ? 429 : 401);
  }
  await env.DB.prepare("DELETE FROM auth_login_attempts WHERE key = ?").bind(key).run();
  const rawSession = randomHex(32);
  const idHash = await sha256Hex(rawSession);
  const expiresAt = now + SESSION_TTL_MS;
  await env.DB.prepare("INSERT INTO auth_sessions(id_hash, user_id, expires_at, created_at, last_seen_at) VALUES (?, ?, ?, ?, ?)")
    .bind(idHash, user.id, expiresAt, nowIso(), now).run();
  await audit(env, user.id, "login", user.id);
  const response = json({ user: { email: user.email, role: user.role, password_change_required: Number(user.password_change_required) === 1 } }, 200, { "Set-Cookie": sessionCookie(rawSession, SESSION_TTL_MS / 1000) });
  response.headers.append("Set-Cookie", csrfCookie(randomHex(24), SESSION_TTL_MS / 1000));
  return response;
}

async function bootstrap(request, env) {
  const supplied = request.headers.get("X-Staging-Bootstrap-Token") || "";
  const configured = env.STAGING_BOOTSTRAP_TOKEN || "";
  if (!configured || supplied.length < 16 || supplied !== configured) return json({ error: "not_found" }, 404);
  const count = await env.DB.prepare("SELECT COUNT(*) AS count FROM auth_users LIMIT 1").first();
  if (Number(count?.count || 0) !== 0) return json({ error: "bootstrap_closed" }, 409);
  const body = await readBody(request);
  const email = String(body?.email || "").trim().toLowerCase();
  const password = body?.password;
  if (!validEmail(email) || !validPassword(password)) return json({ error: "invalid_input" }, 400);
  const id = randomHex(16);
  let hash;
  try {
    hash = await hashPassword(password);
  } catch {
    return json({ error: "bootstrap_hash_failed" }, 500);
  }
  try {
    await env.DB.prepare("INSERT INTO auth_users(id, email, password_hash, role, is_active, password_change_required, created_at, updated_at) VALUES (?, ?, ?, 'owner', 1, 0, ?, ?)")
      .bind(id, email, hash, nowIso(), nowIso()).run();
    await audit(env, id, "bootstrap_owner", id);
  } catch {
    return json({ error: "bootstrap_database_failed" }, 500);
  }
  return json({ created: true }, 201);
}

async function authRoute(request, env, url) {
  if (!env.DB) return json({ error: "staging_database_unavailable" }, 503);
  if (url.pathname === "/auth/login" && request.method === "POST") return login(request, env);
  if (url.pathname === "/auth/bootstrap" && request.method === "POST") return bootstrap(request, env);
  if (url.pathname === "/auth/session" && request.method === "GET") {
    const identity = await currentIdentity(request, env);
    return json({ user: identity ? { email: identity.email, role: identity.role, password_change_required: identity.passwordChangeRequired } : null });
  }
  if (url.pathname === "/auth/logout" && request.method === "POST") {
    const raw = cookieValue(request, SESSION_COOKIE);
    if (raw) await env.DB.prepare("UPDATE auth_sessions SET revoked_at = ? WHERE id_hash = ?").bind(Date.now(), await sha256Hex(raw)).run();
    const response = json({ logged_out: true }, 200, { "Set-Cookie": sessionCookie("", 0) });
    response.headers.append("Set-Cookie", csrfCookie("", 0));
    return response;
  }
  if (url.pathname.startsWith("/auth/")) return json({ error: "method_not_allowed" }, 405, { Allow: "GET, POST" });
  return null;
}

async function adminRoute(request, env, url) {
  if (!env.DB) return json({ error: "staging_database_unavailable" }, 503);
  if (!originAllowed(request)) return json({ error: "bad_origin" }, 403);
  if (["POST", "PUT", "PATCH", "DELETE"].includes(request.method) && !csrfAllowed(request)) return json({ error: "csrf_failed" }, 403);
  if (url.pathname === "/admin/managers" && request.method === "POST") {
    const auth = await requireAdmin(request, env, "owner");
    if (auth.error) return auth.error;
    const body = await readBody(request);
    const email = String(body?.email || "").trim().toLowerCase();
    const password = body?.password;
    if (!validEmail(email) || !validPassword(password)) return json({ error: "invalid_input" }, 400);
    const id = randomHex(16);
    const hash = await hashPassword(password);
    try {
      await env.DB.prepare("INSERT INTO auth_users(id, email, password_hash, role, is_active, password_change_required, created_at, updated_at) VALUES (?, ?, ?, 'manager', 1, 1, ?, ?)")
        .bind(id, email, hash, nowIso(), nowIso()).run();
    } catch {
      return json({ error: "manager_already_exists" }, 409);
    }
    await audit(env, auth.identity.userId, "manager_create", id, { email });
    return json({ manager: { id, email, role: "manager", is_active: true, password_change_required: true } }, 201);
  }
  if (url.pathname.startsWith("/admin/managers/") && request.method === "PATCH") {
    const auth = await requireAdmin(request, env, "owner");
    if (auth.error) return auth.error;
    const id = url.pathname.slice("/admin/managers/".length);
    const body = await readBody(request);
    if (!id || typeof body?.is_active !== "boolean") return json({ error: "invalid_input" }, 400);
    const result = await env.DB.prepare("UPDATE auth_users SET is_active = ?, updated_at = ? WHERE id = ? AND role = 'manager'")
      .bind(body.is_active ? 1 : 0, nowIso(), id).run();
    if (!result.meta?.changes) return json({ error: "manager_not_found" }, 404);
    await audit(env, auth.identity.userId, body.is_active ? "manager_activate" : "manager_disable", id);
    return json({ updated: true, id, is_active: body.is_active });
  }
  if (url.pathname === "/admin/managers" && request.method === "GET") {
    const auth = await requireAdmin(request, env, "owner");
    if (auth.error) return auth.error;
    const result = await env.DB.prepare("SELECT id, email, role, is_active, password_change_required, created_at, updated_at FROM auth_users WHERE role = 'manager' ORDER BY email LIMIT 100").all();
    return json({ managers: result.results || [] });
  }
  if (url.pathname === "/admin/price-adjustments" && request.method === "GET") {
    const auth = await requireAdmin(request, env);
    if (auth.error) return auth.error;
    const result = await env.DB.prepare("SELECT carat, adjustment_sar, updated_at FROM price_adjustments WHERE carat IN ('24','21','18') ORDER BY carat LIMIT 3").all();
    return json({ adjustments: result.results || [] });
  }
  if (url.pathname === "/admin/price-adjustments" && request.method === "PUT") {
    const auth = await requireAdmin(request, env);
    if (auth.error) return auth.error;
    const body = await readBody(request);
    const carat = String(body?.carat || "");
    const value = Number(body?.adjustment_sar);
    if (!["24", "21", "18"].includes(carat) || !Number.isFinite(value) || value < -5000 || value > 5000) return json({ error: "invalid_adjustment" }, 400);
    const updatedAt = nowIso();
    await env.DB.prepare("UPDATE price_adjustments SET adjustment_sar = ?, updated_at = ? WHERE carat = ?").bind(value, updatedAt, carat).run();
    await audit(env, auth.identity.userId, "price_adjustment_update", carat, { value });
    return json({ updated: true, carat, adjustment_sar: value, updated_at: updatedAt });
  }
  if (url.pathname === "/admin/site-settings" && request.method === "PUT") {
    const auth = await requireAdmin(request, env, "owner");
    if (auth.error) return auth.error;
    const body = await readBody(request);
    if (!body || !["theme", "contact_actions"].some((key) => key in body)) return json({ error: "invalid_settings" }, 400);
    const allowedThemes = new Set(["emerald_classic", "obsidian_glass", "ivory_luxe"]);
    if (body.theme !== undefined && !allowedThemes.has(String(body.theme))) return json({ error: "invalid_theme" }, 400);
    if (body.contact_actions !== undefined && !validContactActions(body.contact_actions)) return json({ error: "invalid_contact_actions" }, 400);
    const updatedAt = nowIso();
    const statements = [];
    if (body.theme !== undefined) statements.push(env.DB.prepare("UPDATE site_settings SET value_json = ?, updated_at = ? WHERE key = 'theme'").bind(JSON.stringify(body.theme), updatedAt));
    if (body.contact_actions !== undefined) statements.push(env.DB.prepare("UPDATE site_settings SET value_json = ?, updated_at = ? WHERE key = 'contact_actions'").bind(JSON.stringify(body.contact_actions), updatedAt));
    await env.DB.batch(statements);
    await audit(env, auth.identity.userId, "site_settings_update", "site_settings");
    return json({ updated: true });
  }
  if (url.pathname === "/admin/audit" && request.method === "GET") {
    const auth = await requireAdmin(request, env, "owner");
    if (auth.error) return auth.error;
    const result = await env.DB.prepare("SELECT id, actor_user_id, action, target, details_json, created_at FROM auth_audit_log ORDER BY id DESC LIMIT 100").all();
    return json({ audit: result.results || [] });
  }
  return null;
}

async function readPublicSettings(env) {
  if (!env.DB) return json({ error: "staging_database_unavailable" }, 503);
  const result = await env.DB.prepare("SELECT key, value_json, updated_at FROM site_settings WHERE key IN ('theme', 'contact_actions') LIMIT 2").all();
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
  const result = await env.DB.prepare("SELECT carat, adjustment_sar, updated_at FROM price_adjustments WHERE carat IN ('24', '21', '18') ORDER BY CASE carat WHEN '24' THEN 1 WHEN '21' THEN 2 WHEN '18' THEN 3 END LIMIT 3").all();
  return json({ adjustments: result.results || [] });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    try {
      if (url.pathname.startsWith("/__security/")) return json({ error: "not_found" }, 404);
      const authResponse = await authRoute(request, env, url);
      if (authResponse) return withSecurityHeaders(authResponse);
      if (url.pathname.startsWith("/admin/")) {
        const adminResponse = await adminRoute(request, env, url);
        if (adminResponse) return withSecurityHeaders(adminResponse);
      }
      if (url.pathname === "/admin.html" || url.pathname.startsWith("/admin/")) return withSecurityHeaders(new Response("Not Found", { status: 404 }));
      if (url.pathname.startsWith("/api/")) {
        if (request.method !== "GET") return withSecurityHeaders(new Response("Method Not Allowed", { status: 405, headers: { Allow: "GET" } }));
        const upstreamPath = url.pathname.slice("/api".length);
        if (PUBLIC_CONFIG_PATHS.has(upstreamPath)) return upstreamPath === "/public-settings" ? await readPublicSettings(env) : await readPublicAdjustments(env);
        if (!PUBLIC_API_PATHS.has(upstreamPath)) return withSecurityHeaders(new Response("Not Found", { status: 404 }));
        const upstream = new URL(env.UPSTREAM_PUBLIC_API);
        upstream.pathname = upstreamPath;
        upstream.search = url.search;
        const response = await fetch(new Request(upstream, { method: "GET" }));
        const headers = new Headers(response.headers);
        headers.set("Cache-Control", "no-store");
        return withSecurityHeaders(new Response(response.body, { status: response.status, headers }));
      }
      return withSecurityHeaders(await env.ASSETS.fetch(request));
    } catch {
      return json({ error: "internal_error" }, 500);
    }
  },
};
