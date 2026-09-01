const PUBLIC_API_PATHS = new Set(["/quote", "/history"]);
const PUBLIC_CONFIG_PATHS = new Map([
  ["/public-settings", "public-settings"],
  ["/public-adjustments", "public-adjustments"],
]);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/admin.html" || url.pathname.startsWith("/admin/")) {
      return new Response("Not Found", { status: 404 });
    }

    if (url.pathname.startsWith("/api/")) {
      if (request.method !== "GET") {
        return new Response("Method Not Allowed", {
          status: 405,
          headers: { Allow: "GET" },
        });
      }

      const upstreamPath = url.pathname.slice("/api".length);
      const configAction = PUBLIC_CONFIG_PATHS.get(upstreamPath);
      if (!PUBLIC_API_PATHS.has(upstreamPath) && !configAction) {
        return new Response("Not Found", { status: 404 });
      }

      const upstream = new URL(configAction ? env.UPSTREAM_PUBLIC_CONFIG_API : env.UPSTREAM_PUBLIC_API);
      upstream.pathname = configAction ? upstream.pathname : upstreamPath;
      upstream.search = configAction ? `?action=${encodeURIComponent(configAction)}` : url.search;
      const response = await fetch(new Request(upstream, { method: "GET" }));
      const headers = new Headers(response.headers);
      headers.set("Cache-Control", "no-store");
      return new Response(response.body, { status: response.status, headers });
    }

    return env.ASSETS.fetch(request);
  },
};
