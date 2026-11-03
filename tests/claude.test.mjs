import { test } from "node:test";
import assert from "node:assert/strict";
import { resultFromMessage } from "../lib/claude.mjs";

test("keeps only text blocks, skipping thinking and fallback blocks", () => {
  const msg = {
    stop_reason: "end_turn",
    content: [
      { type: "thinking", thinking: "" },
      { type: "fallback", from: { model: "a" }, to: { model: "b" } },
      { type: "text", text: "# Topic" },
      { type: "text", text: "\nhooks" }
    ]
  };
  assert.deepEqual(resultFromMessage(msg), { result: "# Topic\nhooks" });
});

test("flags output that hit max_tokens", () => {
  const out = resultFromMessage({ stop_reason: "max_tokens", content: [{ type: "text", text: "partial" }] });
  assert.match(out.result, /^partial/);
  assert.match(out.result, /cut off/);
});

test("reports a refusal as an error", () => {
  const out = resultFromMessage({ stop_reason: "refusal", content: [] });
  assert.ok(out.error);
});

test("reports an empty answer as an error", () => {
  const out = resultFromMessage({ stop_reason: "end_turn", content: [{ type: "text", text: "  " }] });
  assert.ok(out.error);
});
