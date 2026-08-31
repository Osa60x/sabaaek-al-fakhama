const PUBLIC_API_PATHS = new Set(["/quote", "/history"]);

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
      if (!PUBLIC_API_PATHS.has(upstreamPath)) {
        return new Response("Not Found", { status: 404 });
      }

      const upstream = new URL(env.UPSTREAM_PUBLIC_API);
      upstream.pathname = upstreamPath;
      upstream.search = url.search;
      const response = await fetch(new Request(upstream, { method: "GET" }));
      const headers = new Headers(response.headers);
      headers.set("Cache-Control", "no-store");
      return new Response(response.body, { status: response.status, headers });
    }

    return env.ASSETS.fetch(request);
  },
};
