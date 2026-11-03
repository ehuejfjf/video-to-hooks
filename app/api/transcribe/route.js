export const maxDuration = 120;

export async function POST(req) {
  try {
    if (!process.env.OPENAI_API_KEY) {
      return Response.json({ error: "OPENAI_API_KEY is not set on the server." }, { status: 500 });
    }
    const form = await req.formData();
    const file = form.get("file");
    if (!file || typeof file === "string" || file.size === 0) {
      return Response.json({ error: "No audio file received." }, { status: 400 });
    }
    const fd = new FormData();
    fd.append("file", file, "audio.wav");
    fd.append("model", "whisper-1");
    fd.append("response_format", "text");
    const res = await fetch("https://api.openai.com/v1/audio/transcriptions", {
      method: "POST",
      headers: { Authorization: `Bearer ${process.env.OPENAI_API_KEY}` },
      body: fd
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || `Whisper error (${res.status})`);
    }
    const transcript = (await res.text()).trim();
    return Response.json({ transcript });
  } catch (e) {
    return Response.json({ error: e.message }, { status: 500 });
  }
}
