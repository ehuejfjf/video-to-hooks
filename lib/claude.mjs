/**
 * Pull the visible answer out of a Messages API response and decide whether
 * it is usable. Thinking and fallback blocks carry no answer text, so only
 * text blocks are kept.
 */
export function resultFromMessage(msg) {
  const text = (msg.content || [])
    .filter((b) => b.type === "text")
    .map((b) => b.text)
    .join("");

  if (msg.stop_reason === "refusal") {
    return { error: "Claude declined to write hooks for this transcript. Try a different video." };
  }
  if (!text.trim()) {
    return { error: "Claude returned an empty response. Please try again." };
  }
  if (msg.stop_reason === "max_tokens") {
    return { result: text + "\n\n[Output was cut off before it finished. Please run it again.]" };
  }
  return { result: text };
}
