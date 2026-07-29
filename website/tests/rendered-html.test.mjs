import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function render(pathname = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${pathname}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request(`https://develoop.example${pathname}`, {
      headers: { accept: "text/html" },
    }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("renders Develoop and the four installation paths", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /<title>Develoop — Close the loop on GitHub work<\/title>/i);
  assert.match(html, /Close the loop/);
  assert.match(html, /gh-create-issue/);
  assert.match(html, /gh-implement-issue/);
  assert.match(html, /gh-autoreview-resolve/);
  assert.match(
    html,
    /https:\/\/chatgpt\.com\/plugins\/plugins_6a69ee33e3048191ab7da89ec70dbbe2/,
  );
  assert.match(html, /OpenAI Curated Directory/);
  assert.doesNotMatch(html, /codex plugin marketplace add/);
  assert.match(html, /claude plugin install develoop@develoop/);
  assert.match(html, /agy plugins install https:\/\/github\.com\/comfuture\/agent-skills/);
  assert.match(html, /npx skills add comfuture\/agent-skills/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/);
});

for (const [pathname, heading] of [
  ["/privacy", "Privacy Policy"],
  ["/terms", "Terms of Use"],
  ["/support", "Support"],
  ["/releases", "Release Notes"],
]) {
  test(`renders ${pathname}`, async () => {
    const response = await render(pathname);
    assert.equal(response.status, 200);
    const html = await response.text();
    assert.match(html, new RegExp(`<h1[^>]*>${heading}<\\/h1>`, "i"));
    assert.match(html, /comfuture@gmail\.com/);
  });
}

test("privacy policy explains GitHub processing and no developer backend", async () => {
  const response = await render("/privacy");
  const html = await response.text();
  assert.match(html, /does not receive your GitHub token/);
  assert.match(html, /does not use forms, advertising, behavioral analytics/);
  assert.match(html, /State-changing actions/);
});

test("removes the temporary starter surface", async () => {
  await assert.rejects(access(new URL("app/_sites-preview", root)));
  const packageJson = await readFile(new URL("package.json", root), "utf8");
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
});
