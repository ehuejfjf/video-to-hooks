import Anthropic from "@anthropic-ai/sdk";

export async function POST(req) {
  try {
    const { audio } = await req.json();
    const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
    const msg = await client.messages.create({
      model: "claude-opus-4-6",
      max_tokens: 4096,
      messages: [{
        role: "user",
        content: [
          { type: "document", source: { type: "base64", media_type: "audio/wav", data: audio } },
          { type: "text", text: "Please transcribe this audio exactly as spoken. Output only the transcript text, nothing else." }
        ]
      }]
    });
    const transcript = msg.content.map(b => b.text || "").join("");
    return Response.json({ transcript });
  } catch (e) {
    return Response.json({ error: e.message }, { status: 500 });
  }
}
