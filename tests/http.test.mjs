import { test } from "node:test";
import assert from "node:assert/strict";
import { readJson } from "../lib/http.mjs";

test("readJson returns parsed JSON on success", async () => {
  assert.deepEqual(await readJson(new Response('{"transcript":"hi"}')), { transcript: "hi" });
});

test("readJson surfaces the server's error field", async () => {
  const res = new Response('{"error":"Whisper error"}', { status: 500 });
  await assert.rejects(readJson(res), /Whisper error/);
});

test("readJson explains non-JSON error pages instead of a parse error", async () => {
  const res = new Response("Request Entity Too Large", { status: 413 });
  await assert.rejects(readJson(res), /413: Request Entity Too Large/);
});

test("readJson rejects a non-OK status even without an error field", async () => {
  await assert.rejects(readJson(new Response("{}", { status: 502 })), /502/);
});
