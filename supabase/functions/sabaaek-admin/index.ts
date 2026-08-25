import { createClient } from "npm:@supabase/supabase-js@2";

const ALLOWED_ORIGINS = new Set(["https://osa60x.github.io"]);
const OWNER_EMAIL = "osa60x@gmail.com";
const CARATS = new Set(["24", "21", "18"]);
const THEMES = new Set(["emerald_classic", "obsidian_glass", "ivory_luxe"]);
const CONTACT_KINDS = new Set(["whatsapp", "phone", "website", "map", "instagram", "snapchat", "telegram", "email"]);

type Role = "owner" | "manager" | "user";
type Identity = { id: string; email: string; role: Role; isActive: boolean; mustChangePassword: boolean };
type ContactAction = { kind: "whatsapp" | "phone" | "website" | "map" | "instagram" | "snapchat" | "telegram" | "email"; label: string; value: string };
type SiteSettings = { theme: "emerald_classic" | "obsidian_glass" | "ivory_luxe"; contact_actions: ContactAction[]; updated_at?: string };
type SetupToken = { token_hash: string; user_id: string; expires_at: string; used_at: string | null };

function keyFromEnvironment() {
  try {
    const keys = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") ?? "{}");
    if (typeof keys.default === "string" && keys.default) return keys.default;
  } catch { /* legacy fallback below */ }
  return Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
}

const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
const secretKey = keyFromEnvironment();
const admin = createClient(supabaseUrl, secretKey, { auth: { persistSession: false, autoRefreshToken: false } });

function cors(request: Request) {
  const origin = request.headers.get("origin") ?? "";
  return ALLOWED_ORIGINS.has(origin)
    ? { "access-control-allow-origin": origin, "access-control-allow-methods": "GET, POST, PUT, OPTIONS", "access-control-allow-headers": "authorization, content-type", "access-control-max-age": "86400", vary: "Origin" }
    : {};
}

function response(request: Request, body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", ...cors(request) } });
}

function fail(request: Request, status: number, code: string) { return response(request, { code }, status); }

function isStrongPassword(value: string) {
  return value.length >= 12 && /[a-z]/.test(value) && /[A-Z]/.test(value) && /\d/.test(value) && /[^A-Za-z0-9]/.test(value);
}

async function sha256(value: string) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, "0")).join("");
}

async function identityFor(request: Request): Promise<Identity | null> {
  const authorization = request.headers.get("authorization") ?? "";
  const token = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
  if (!token) return null;
  const { data, error } = await admin.auth.getUser(token);
  if (error || !data.user?.id || !data.user.email) return null;
  const { data: profile } = await admin.from("profiles").select("role,is_active,must_change_password").eq("id", data.user.id).maybeSingle();
  if (!profile) return null;
  return { id: data.user.id, email: data.user.email.toLowerCase(), role: profile.role as Role, isActive: Boolean(profile.is_active), mustChangePassword: Boolean(profile.must_change_password) };
}

async function requireAdmin(request: Request, ownerOnly = false, allowPasswordChange = false): Promise<Identity | Response> {
  const identity = await identityFor(request);
  if (!identity || !identity.isActive || (identity.role !== "owner" && identity.role !== "manager")) return fail(request, 403, "forbidden");
  if (ownerOnly && identity.role !== "owner") return fail(request, 403, "owner_required");
  if (!allowPasswordChange && identity.mustChangePassword) return fail(request, 403, "password_change_required");
  return identity;
}

function isError(value: Identity | Response): value is Response { return value instanceof Response; }

function parseUpdates(value: unknown) {
  if (!Array.isArray(value) || value.length !== 3) return null;
  const seen = new Set<string>();
  const normalized: { carat: "24" | "21" | "18"; adjustment_sar: number }[] = [];
  for (const item of value) {
    const carat = String(item?.carat ?? "");
    const adjustment = Number(item?.adjustment_sar);
    if (!CARATS.has(carat) || seen.has(carat) || !Number.isFinite(adjustment) || adjustment < -5000 || adjustment > 5000) return null;
    seen.add(carat);
    normalized.push({ carat: carat as "24" | "21" | "18", adjustment_sar: Math.round(adjustment * 100) / 100 });
  }
  return seen.size === 3 ? normalized : null;
}

async function activeSetupToken(token: string) {
  if (!token || token.length < 32) return null;
  const hash = await sha256(token);
  const { data } = await admin.from("password_setup_tokens").select("token_hash,user_id,expires_at,used_at").eq("token_hash", hash).maybeSingle<SetupToken>();
  if (!data || data.used_at || new Date(data.expires_at).getTime() < Date.now()) return null;
  return data;
}

async function findUserByEmail(email: string) {
  const { data, error } = await admin.auth.admin.listUsers({ page: 1, perPage: 1000 });
  if (error) return null;
  return (data.users ?? []).find(user => user.email?.toLowerCase() === email) ?? null;
}

function normalizeContactActions(value: unknown): ContactAction[] | null {
  if (!Array.isArray(value) || value.length > 6) return null;
  const seen = new Set<string>();
  const actions: ContactAction[] = [];
  for (const raw of value) {
    const kind = String(raw?.kind ?? "");
    const label = String(raw?.label ?? "").trim().replace(/\s+/g, " ");
    const rawValue = String(raw?.value ?? "").trim();
    if (!CONTACT_KINDS.has(kind) || seen.has(kind) || !label || label.length > 48 || !rawValue || rawValue.length > 300) return null;
    let normalized = rawValue;
    if (kind === "phone" || kind === "whatsapp") {
      normalized = rawValue.replace(/\D/g, "");
      if (normalized.length < 7 || normalized.length > 15) return null;
    } else if (kind === "email") {
      normalized = rawValue.toLowerCase();
      if (!/^\S+@\S+\.\S+$/.test(normalized)) return null;
    } else {
      try {
        const parsed = new URL(rawValue);
        if (parsed.protocol !== "https:") return null;
        normalized = parsed.toString();
      } catch { return null; }
    }
    seen.add(kind);
    actions.push({ kind: kind as ContactAction["kind"], label, value: normalized });
  }
  return actions;
}

function normalizeSiteSettings(value: unknown): SiteSettings | null {
  const theme = String((value as { theme?: unknown } | null)?.theme ?? "");
  const actions = normalizeContactActions((value as { contact_actions?: unknown } | null)?.contact_actions);
  if (!THEMES.has(theme) || !actions) return null;
  return { theme: theme as SiteSettings["theme"], contact_actions: actions };
}

async function readSiteSettings() {
  const { data, error } = await admin.from("site_settings").select("theme,contact_actions,updated_at").eq("singleton", true).maybeSingle();
  if (error || !data) return null;
  const settings = normalizeSiteSettings(data);
  return settings ? { ...settings, updated_at: data.updated_at } : null;
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(request) });
  const url = new URL(request.url);
  const action = url.searchParams.get("action") ?? "";

  if (request.method === "GET" && action === "public-adjustments") {
    const { data, error } = await admin.from("price_adjustments").select("carat,adjustment_sar,updated_at").order("carat", { ascending: false });
    return error ? fail(request, 503, "unavailable") : response(request, { adjustments: data ?? [] });
  }

  if (request.method === "GET" && action === "public-settings") {
    const settings = await readSiteSettings();
    return settings ? response(request, { settings }) : fail(request, 503, "unavailable");
  }

  if (request.method === "GET" && action === "owner-setup") {
    const setup = await activeSetupToken(url.searchParams.get("token") ?? "");
    if (!setup) return fail(request, 403, "invalid_setup");
    const { data: profile } = await admin.from("profiles").select("role,is_active").eq("id", setup.user_id).maybeSingle();
    if (!profile || profile.role !== "owner" || !profile.is_active) return fail(request, 403, "invalid_setup");
    return response(request, { ok: true, email: OWNER_EMAIL });
  }

  if (request.method === "POST" && action === "owner-setup") {
    const payload = await request.json().catch(() => null);
    const setup = await activeSetupToken(String(payload?.token ?? ""));
    const password = String(payload?.password ?? "");
    if (!setup) return fail(request, 403, "invalid_setup");
    if (!isStrongPassword(password)) return fail(request, 400, "weak_password");
    const { data: profile } = await admin.from("profiles").select("role,is_active").eq("id", setup.user_id).maybeSingle();
    if (!profile || profile.role !== "owner" || !profile.is_active) return fail(request, 403, "invalid_setup");
    const { error: authError } = await admin.auth.admin.updateUserById(setup.user_id, { password, email_confirm: true });
    if (authError) return fail(request, 503, "password_setup_failed");
    await admin.from("profiles").update({ must_change_password: false }).eq("id", setup.user_id);
    await admin.from("password_setup_tokens").update({ used_at: new Date().toISOString() }).eq("token_hash", setup.token_hash);
    await admin.from("audit_log").insert({ actor_id: setup.user_id, actor_role: "owner", action: "owner_password_configured", entity_type: "profiles", detail: {} });
    return response(request, { ok: true });
  }

  if (request.method === "GET" && action === "me") {
    const identity = await identityFor(request);
    return identity ? response(request, { identity }) : fail(request, 401, "unauthenticated");
  }

  if (request.method === "GET" && action === "audit") {
    const identity = await requireAdmin(request, true);
    if (isError(identity)) return identity;
    const { data, error } = await admin.from("audit_log").select("action,entity_type,actor_role,created_at").order("created_at", { ascending: false }).limit(20);
    return error ? fail(request, 503, "unavailable") : response(request, { logs: data ?? [] });
  }

  if (request.method === "GET" && action === "site-settings") {
    const identity = await requireAdmin(request, true);
    if (isError(identity)) return identity;
    const settings = await readSiteSettings();
    return settings ? response(request, { settings }) : fail(request, 503, "unavailable");
  }

  if (request.method === "PUT" && action === "site-settings") {
    const identity = await requireAdmin(request, true);
    if (isError(identity)) return identity;
    const payload = await request.json().catch(() => null);
    const settings = normalizeSiteSettings(payload);
    if (!settings) return fail(request, 400, "invalid_site_settings");
    const { data, error } = await admin.from("site_settings")
      .upsert({ singleton: true, theme: settings.theme, contact_actions: settings.contact_actions, updated_by: identity.id }, { onConflict: "singleton" })
      .select("theme,contact_actions,updated_at").single();
    const saved = !error ? normalizeSiteSettings(data) : null;
    if (!saved) return fail(request, 503, "settings_save_failed");
    await admin.from("audit_log").insert({ actor_id: identity.id, actor_role: identity.role, action: "site_settings_updated", entity_type: "site_settings", detail: { theme: saved.theme, contacts: saved.contact_actions.map(action => action.kind) } });
    return response(request, { settings: { ...saved, updated_at: data.updated_at } });
  }

  if (request.method === "GET" && action === "managers") {
    const identity = await requireAdmin(request, true);
    if (isError(identity)) return identity;
    const { data, error } = await admin.from("manager_invites").select("email,is_active,created_at,updated_at").order("created_at", { ascending: false }).limit(50);
    return error ? fail(request, 503, "unavailable") : response(request, { managers: data ?? [] });
  }

  if (request.method === "PUT" && action === "price-adjustments") {
    const identity = await requireAdmin(request);
    if (isError(identity)) return identity;
    const updates = parseUpdates((await request.json().catch(() => null))?.updates);
    if (!updates) return fail(request, 400, "invalid_adjustments");
    const { data, error } = await admin.rpc("apply_sabaaek_adjustments", { p_updates: updates, p_actor: identity.id });
    return error ? fail(request, 400, "save_failed") : response(request, { adjustments: data ?? [] });
  }

  if (request.method === "POST" && action === "change-password") {
    const identity = await requireAdmin(request, false, true);
    if (isError(identity)) return identity;
    const payload = await request.json().catch(() => null);
    const currentPassword = String(payload?.currentPassword ?? "");
    const password = String(payload?.password ?? "");
    if (!isStrongPassword(password)) return fail(request, 400, "weak_password");
    // Do not sign in through the service client: a user session there would replace
    // its service credentials and make the following profile update subject to RLS.
    const verifier = createClient(supabaseUrl, secretKey, { auth: { persistSession: false, autoRefreshToken: false } });
    const { error: checkError } = await verifier.auth.signInWithPassword({ email: identity.email, password: currentPassword });
    if (checkError) return fail(request, 400, "current_password_incorrect");
    const { error: updateError } = await admin.auth.admin.updateUserById(identity.id, { password });
    if (updateError) return fail(request, 503, "password_update_failed");
    const { error: profileUpdateError } = await admin.from("profiles").update({ must_change_password: false }).eq("id", identity.id);
    if (profileUpdateError) return fail(request, 503, "password_state_update_failed");
    await admin.from("audit_log").insert({ actor_id: identity.id, actor_role: identity.role, action: "password_changed", entity_type: "profiles", detail: {} });
    return response(request, { ok: true });
  }

  if (request.method === "POST" && action === "create-manager") {
    const identity = await requireAdmin(request, true);
    if (isError(identity)) return identity;
    const payload = await request.json().catch(() => null);
    const email = String(payload?.email ?? "").trim().toLowerCase();
    const password = String(payload?.password ?? "");
    if (!/^\S+@\S+\.\S+$/.test(email) || email === OWNER_EMAIL) return fail(request, 400, "invalid_email");
    if (!isStrongPassword(password)) return fail(request, 400, "weak_password");
    const existingUser = await findUserByEmail(email);
    let userId = existingUser?.id ?? "";
    if (existingUser) {
      const { data: existingProfile } = await admin.from("profiles").select("role").eq("id", existingUser.id).maybeSingle();
      if (!existingProfile || existingProfile.role !== "manager") return fail(request, 409, "email_unavailable");
      const { error } = await admin.auth.admin.updateUserById(existingUser.id, { password, email_confirm: true });
      if (error) return fail(request, 503, "manager_setup_failed");
    } else {
      const { data, error } = await admin.auth.admin.createUser({ email, password, email_confirm: true });
      if (error || !data.user?.id) return fail(request, 503, "manager_setup_failed");
      userId = data.user.id;
    }
    const { error: profileError } = await admin.from("profiles").upsert({ id: userId, role: "manager", is_active: true, must_change_password: true }, { onConflict: "id" });
    if (profileError) return fail(request, 503, "manager_profile_failed");
    const { error: inviteError } = await admin.from("manager_invites").upsert({ email, invited_by: identity.id, is_active: true }, { onConflict: "email" });
    if (inviteError) return fail(request, 503, "manager_record_failed");
    await admin.from("audit_log").insert({ actor_id: identity.id, actor_role: identity.role, action: "manager_created", entity_type: "manager_invites", detail: { email } });
    return response(request, { ok: true });
  }

  if (request.method === "POST" && action === "deactivate-manager") {
    const identity = await requireAdmin(request, true);
    if (isError(identity)) return identity;
    const email = String((await request.json().catch(() => null))?.email ?? "").trim().toLowerCase();
    const manager = await findUserByEmail(email);
    if (!manager) return fail(request, 404, "manager_not_found");
    const { data: profile } = await admin.from("profiles").select("role").eq("id", manager.id).maybeSingle();
    if (!profile || profile.role !== "manager") return fail(request, 404, "manager_not_found");
    await admin.from("profiles").update({ is_active: false }).eq("id", manager.id);
    await admin.from("manager_invites").update({ is_active: false }).eq("email", email);
    await admin.from("audit_log").insert({ actor_id: identity.id, actor_role: identity.role, action: "manager_deactivated", entity_type: "manager_invites", detail: { email } });
    return response(request, { ok: true });
  }

  return fail(request, 404, "not_found");
});
