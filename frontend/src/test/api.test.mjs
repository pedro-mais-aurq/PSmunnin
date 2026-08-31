import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { afterEach, mock, test } from "node:test";
import ts from "typescript";

// Use the project's TypeScript compiler so tests also run on the supported Node 20.
const source = await readFile(new URL("../lib/api.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2020, module: ts.ModuleKind.ESNext },
}).outputText;
const { api, isRetryableRequestError } = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString("base64")}`
);
const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;

afterEach(() => {
  mock.restoreAll();
  if (originalApiUrl === undefined) delete process.env.NEXT_PUBLIC_API_URL;
  else process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
});

for (const status of [400, 401, 403, 404, 408, 422, 429, 500, 502, 503, 504]) {
  test(`polling classifies HTTP ${status} without losing the API message`, async () => {
    process.env.NEXT_PUBLIC_API_URL = "http://api.example.test";
    mock.method(globalThis, "fetch", async () => new Response(
      JSON.stringify({ detail: "Mensagem de teste" }), { status },
    ));
    await assert.rejects(api.getSearch("test-search"), (error) => {
      assert.equal(error.message, "Mensagem de teste");
      assert.equal(isRetryableRequestError(error), status === 408 || status === 429 || status >= 500);
      return true;
    });
  });
}

test("network failures are retryable", async () => {
  process.env.NEXT_PUBLIC_API_URL = "http://api.example.test";
  mock.method(globalThis, "fetch", async () => { throw new TypeError("Failed to fetch"); });
  await assert.rejects(api.getSearch("test-search"), (error) => isRetryableRequestError(error));
});

test("missing API configuration is not retryable", async () => {
  delete process.env.NEXT_PUBLIC_API_URL;
  const fetch = mock.method(globalThis, "fetch", async () => { throw new Error("Unexpected network"); });
  await assert.rejects(api.getSearch("test-search"), (error) => {
    assert.equal(isRetryableRequestError(error), false);
    return true;
  });
  assert.equal(fetch.mock.callCount(), 0);
});

test("a TypeError outside the HTTP request must not restart polling", () => {
  assert.equal(isRetryableRequestError(new TypeError("Invalid application data")), false);
});

for (const status of ["done", "failed"]) {
  test(`HTTP 200 with terminal status ${status} preserves the response contract`, async () => {
    process.env.NEXT_PUBLIC_API_URL = "http://api.example.test";
    const detail = { search: { id: "test-search", status, error: status === "failed" ? "Falha controlada" : null }, leads: [] };
    mock.method(globalThis, "fetch", async () => new Response(JSON.stringify(detail)));
    assert.deepEqual(await api.getSearch("test-search"), detail);
  });
}
