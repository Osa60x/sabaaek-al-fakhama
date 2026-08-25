import { createClient } from "npm:@supabase/supabase-js@2";

const ALLOWED_ORIGINS = new Set(["https://osa60x.github.io"]);
const OWNER_EMAIL = "osa60x@gmail.com";

type Role = "owner" | "manager" | "user";
type Identity = { id: string; email: string; role: Role; isActive: boolean };

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

async function identityFor(request: Request): Promise<Identity | null> {
  const authorization = request.headers.get("authorization") ?? "";
  const token = authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
  if (!token) return null;
  const { data, error } = await admin.auth.getUser(token);
  if (error || !data.user?.id || !data.user.email) return null;
  const { data: profile } = await admin.from("profiles").select("role,is_active").eq("id", data.user.id).maybeSingle();
  if (!profile) return null;
  return { id: data.user.id, email: data.user.email.toLowerCase(), role: profile.role as Role, isActive: Boolean(profile.is_active) };
}

async function requireAdmin(request: Request, ownerOnly = false): Promise<Identity | Response> {
  const identity = await identityFor(request);
  if (!identity || !identity.isActive || (identity.role !== "owner" && identity.role !== "manager")) return fail(request, 403, "forbidden");
  if (ownerOnly && identity.role !== "owner") return fail(request, 403, "owner_required");
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
    if ((carat !== "24" && carat !== "21" && carat !== "18") || seen.has(carat) || !Number.isFinite(adjustment) || adjustment < -5000 || adjustment > 5000) return null;
    seen.add(carat);
    normalized.push({ carat: carat as "24" | "21" | "18", adjustment_sar: Math.round(adjustment * 100) / 100 });
  }
  return seen.size === 3 ? normalized : null;
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(request) });
  const url = new URL(request.url);
  const action = url.searchParams.get("action") ?? "";

  if (request.method === "GET" && action === "public-adjustments") {
    const { data, error } = await admin.from("price_adjustments").select("carat,adjustment_sar,updated_at").order("carat", { ascending: false });
    return error ? fail(request, 503, "unavailable") : response(request, { adjustments: data ?? [] });
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

  if (request.method === "PUT" && action === "price-adjustments") {
    const identity = await requireAdmin(request);
    if (isError(identity)) return identity;
    const updates = parseUpdates((await request.json().catch(() => null))?.updates);
    if (!updates) return fail(request, 400, "invalid_adjustments");
    const { data, error } = await admin.rpc("apply_sabaaek_adjustments", { p_updates: updates, p_actor: identity.id });
    return error ? fail(request, 400, "save_failed") : response(request, { adjustments: data ?? [] });
  }

  if (request.method === "POST" && action === "invite-manager") {
    const identity = await requireAdmin(request, true);
    if (isError(identity)) return identity;
    const email = String((await request.json().catch(() => null))?.email ?? "").trim().toLowerCase();
    if (!/^\S+@\S+\.\S+$/.test(email) || email === OWNER_EMAIL) return fail(request, 400, "invalid_email");
    const redirectTo = "https://osa60x.github.io/sabaaek-al-fakhama/admin.html?invite=1";
    const { data: invitation, error: invitationError } = await admin.auth.admin.inviteUserByEmail(email, { redirectTo });
    if (invitationError || !invitation.user?.id) return fail(request, 400, "invite_failed");
    const { error: profileError } = await admin.from("profiles").upsert({ id: invitation.user.id, role: "manager", is_active: true }, { onConflict: "id" });
    if (profileError) return fail(request, 503, "invite_profile_failed");
    const { error: inviteError } = await admin.from("manager_invites").upsert({ email, invited_by: identity.id, is_active: true }, { onConflict: "email" });
    if (inviteError) return fail(request, 503, "invite_record_failed");
    await admin.from("audit_log").insert({ actor_id: identity.id, actor_role: identity.role, action: "manager_invited", entity_type: "manager_invites", detail: { email } });
    return response(request, { ok: true });
  }

  return fail(request, 404, "not_found");
});
