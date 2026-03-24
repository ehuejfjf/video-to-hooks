export async function POST(req) {
  try {
    const { audio } = await req.json();
    const binary = Buffer.from(audio, "base64");
    const blob = new Blob([binary], { type: "audio/wav" });
    const fd = new FormData();
    fd.append("file", blob, "audio.wav");
    fd.append("model", "whisper-1");
    fd.append("response_format", "text");
    const res = await fetch("https://api.openai.com/v1/audio/transcriptions", {
      method: "POST",
      headers: { Authorization: `Bearer ${process.env.OPENAI_API_KEY}` },
      body: fd
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || "Whisper error");
    }
    const transcript = await res.text();
    return Response.json({ transcript });
  } catch (e) {
    return Response.json({ error: e.message }, { status: 500 });
  }
}
