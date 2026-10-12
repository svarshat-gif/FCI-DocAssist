type Context = {
  request: Request;
  params: { path: string | string[] };
  env: { API_PROXY_TARGET?: string };
};

export async function onRequest({ request, params, env }: Context): Promise<Response> {
  const parts = Array.isArray(params.path) ? params.path : [params.path];
  if (parts[0] !== "v1" || parts.some((part) => part === "." || part === ".." || part.includes("/"))) {
    return Response.json({ detail: "Not found." }, { status: 404 });
  }
  if (!["GET", "HEAD", "POST", "DELETE", "OPTIONS"].includes(request.method)) {
    return new Response(null, { status: 405, headers: { Allow: "GET, HEAD, POST, DELETE, OPTIONS" } });
  }
  try {
    if (!env.API_PROXY_TARGET) throw new Error("Missing backend address");
    const target = new URL(env.API_PROXY_TARGET);
    if (target.protocol !== "https:" || target.username || target.password) throw new Error("Invalid backend address");
    const url = new URL(`/api/${parts.map(encodeURIComponent).join("/")}`, target);
    url.search = new URL(request.url).search;
    const headers = new Headers();
    for (const name of ["content-type", "authorization", "x-request-id"]) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }
    const upstream = await fetch(url, {
      method: request.method, headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
      redirect: "error", signal: AbortSignal.timeout(300_000),
    });
    const responseHeaders = new Headers({ "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
    for (const name of ["content-type", "content-disposition", "retry-after"]) {
      const value = upstream.headers.get(name);
      if (value) responseHeaders.set(name, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch {
    return Response.json({ detail: "The assistant is waking up or temporarily unavailable. Please try again shortly." }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}
