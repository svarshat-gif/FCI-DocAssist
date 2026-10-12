import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import ts from "typescript";

const source = await readFile(new URL("../functions/api/[[path]].ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } });
const { onRequest } = await import(`data:text/javascript;base64,${Buffer.from(compiled.outputText).toString("base64")}`);
const context = (path = ["v1", "chat"], method = "GET", backend = "https://backend.example") => ({
  params: { path }, env: { API_PROXY_TARGET: backend },
  request: new Request("https://app.example/api/v1/chat?search=leave", {
    method, headers: { Authorization: "Bearer test", Cookie: "private=test", "X-Request-ID": "test-id" },
  }),
});

test("forwards authorized requests only to the configured backend and never caches", async (t) => {
  t.mock.method(globalThis, "fetch", async (url, options) => {
    assert.equal(url.href, "https://backend.example/api/v1/chat?search=leave");
    assert.equal(options.headers.get("authorization"), "Bearer test");
    assert.equal(options.headers.get("cookie"), null);
    assert.equal(options.redirect, "error");
    return Response.json({ ok: true });
  });
  const response = await onRequest(context());
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(await response.json(), { ok: true });
});

test("preserves quota errors without retrying", async (t) => {
  const mock = t.mock.method(globalThis, "fetch", async () => Response.json({ detail: "Usage limit" }, { status: 429, headers: { "Retry-After": "60" } }));
  const response = await onRequest(context());
  assert.equal(response.status, 429);
  assert.equal(response.headers.get("retry-after"), "60");
  assert.equal(mock.mock.callCount(), 1);
});

test("rejects unsafe paths and unsupported methods before reaching the backend", async (t) => {
  const mock = t.mock.method(globalThis, "fetch", () => { throw new Error("Unexpected network request"); });
  for (const path of [["v2", "chat"], ["v1", ".."], ["v1", "a/b"]]) {
    assert.equal((await onRequest(context(path))).status, 404);
  }
  assert.equal((await onRequest(context(["v1", "chat"], "PUT"))).status, 405);
  assert.equal(mock.mock.callCount(), 0);
});

test("fails closed without an HTTPS backend and hides connection failures", async (t) => {
  t.mock.method(globalThis, "fetch", async () => { throw new Error("internal private connection information"); });
  for (const backend of ["", "http://backend.example", "https://user:password@backend.example", "https://backend.example"]) {
    const response = await onRequest(context(["v1", "chat"], "GET", backend));
    assert.equal(response.status, 503);
    assert.equal((await response.text()).includes("private connection"), false);
  }
});
