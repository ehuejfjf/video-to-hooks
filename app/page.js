"use client";
import { useState, useRef } from "react";

const CHUNK_MB = 20 * 1024 * 1024;

export default function Home() {
  const [videoFile, setVideoFile] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [output, setOutput] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showTranscript, setShowTranscript] = useState(false);
  const [copied, setCopied] = useState(false);
  const fileRef = useRef();

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (f) { setVideoFile(f); setTranscript(""); setOutput(""); setError(""); setStatus(""); }
  };

  async function extractAudio(file) {
    setStatus("Extracting audio from video...");
    const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    const buf = await file.arrayBuffer();
    const audioBuf = await ctx.decodeAudioData(buf);
    const len = audioBuf.length;
    const numCh = audioBuf.numberOfChannels;
    const mono = new Float32Array(len);
    for (let c = 0; c < numCh; c++) {
      const ch = audioBuf.getChannelData(c);
      for (let i = 0; i < len; i++) mono[i] += ch[i] / numCh;
    }
    const pcm = new Int16Array(len);
    for (let i = 0; i < len; i++) {
      const s = Math.max(-1, Math.min(1, mono[i]));
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    const wavBuf = new ArrayBuffer(44 + pcm.byteLength);
    const v = new DataView(wavBuf);
    const w = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    w(0,"RIFF"); v.setUint32(4, 36 + pcm.byteLength, true); w(8,"WAVE");
    w(12,"fmt "); v.setUint32(16,16,true); v.setUint16(20,1,true); v.setUint16(22,1,true);
    v.setUint32(24,16000,true); v.setUint32(28,32000,true); v.setUint16(32,2,true); v.setUint16(34,16,true);
    w(36,"data"); v.setUint32(40, pcm.byteLength, true);
    new Int16Array(wavBuf, 44).set(pcm);
    await ctx.close();
    return new Blob([wavBuf], { type: "audio/wav" });
  }

  function blobToBase64(blob) {
    return new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(r.result.split(",")[1]);
      r.onerror = rej;
      r.readAsDataURL(blob);
    });
  }

  async function transcribeAudio(wav) {
    const totalSize = wav.size;
    const numChunks = Math.ceil(totalSize / CHUNK_MB);
    const parts = [];
    for (let i = 0; i < numChunks; i++) {
      setStatus(`Transcribing audio${numChunks > 1 ? ` (part ${i+1} of ${numChunks})` : ""}...`);
      const chunk = wav.slice(i * CHUNK_MB, Math.min((i+1) * CHUNK_MB, totalSize), "audio/wav");
      const b64 = await blobToBase64(chunk);
      const res = await fetch("/api/transcribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio: b64 })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      parts.push(data.transcript);
    }
    return parts.join(" ");
  }

  async function run() {
    if (!videoFile) return;
    setError(""); setOutput(""); setTranscript(""); setLoading(true);
    try {
      const wav = await extractAudio(videoFile);
      setStatus(`Audio ready (${(wav.size/1024/1024).toFixed(1)} MB). Transcribing...`);
      const tx = await transcribeAudio(wav);
      setTranscript(tx);
      setStatus("Generating hooks & caption...");
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: tx })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setOutput(data.result);
      setStatus("");
    } catch(e) {
      setError("Error: " + e.message);
      setStatus("");
    }
    setLoading(false);
  }

  const copy = () => { navigator.clipboard.writeText(output); setCopied(true); setTimeout(() => setCopied(false), 2000); };
  const reset = () => { setVideoFile(null); setTranscript(""); setOutput(""); setError(""); setStatus(""); if (fileRef.current) fileRef.current.value = ""; };

  return (
    <main style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", background: "#f5f5f5", minHeight: "100vh", padding: "2rem 1rem" }}>
      <div style={{ maxWidth: 740, margin: "0 auto", background: "#fff", borderRadius: 14, padding: "2rem", boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>Video → Hooks & Caption</h1>
        <p style={{ fontSize: 14, color: "#666", marginBottom: "1.75rem" }}>Upload any video — transcript, hooks, and caption generated automatically.</p>

        <label style={{ fontSize: 13, fontWeight: 500, color: "#555", display: "block", marginBottom: 6 }}>
          Upload video <span style={{ fontWeight: 400, color: "#aaa" }}>(mp4, mov, m4a — up to 1GB)</span>
        </label>
        <input ref={fileRef} type="file" accept="video/*,audio/*" onChange={handleFile} style={{ display: "none" }} />
        <div onClick={() => !loading && fileRef.current?.click()} style={{ border: "1.5px dashed #ccc", borderRadius: 12, padding: "2rem 1rem", textAlign: "center", cursor: "pointer", background: "#fafafa", marginBottom: "1.25rem" }}>
          {videoFile ? (
            <>
              <p style={{ fontWeight: 500, fontSize: 14, color: "#111", marginBottom: 4 }}>{videoFile.name}</p>
              <small style={{ color: "#888" }}>{(videoFile.size/1024/1024).toFixed(1)} MB</small>
            </>
          ) : (
            <>
              <p style={{ fontSize: 15, color: "#666", marginBottom: 4 }}>Click to upload your video</p>
              <small style={{ color: "#aaa" }}>mp4, mov, m4a · up to 1GB</small>
            </>
          )}
        </div>

        {error && <p style={{ fontSize: 13, color: "#c0392b", marginBottom: 8 }}>{error}</p>}

        <button onClick={run} disabled={!videoFile || loading} style={{ width: "100%", padding: 12, borderRadius: 10, border: "none", background: "#533AB7", color: "#fff", fontSize: 15, fontWeight: 500, cursor: !videoFile || loading ? "not-allowed" : "pointer", opacity: !videoFile || loading ? 0.5 : 1 }}>
          {loading ? "Processing..." : "Generate transcript + hooks + caption"}
        </button>

        {status && <p style={{ fontSize: 13, color: "#666", textAlign: "center", marginTop: 10 }}>{status}</p>}

        {output && (
          <>
            <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: "1.75rem", marginBottom: 6 }}>
              <span style={{ flex: 1, fontSize: 13, fontWeight: 500, color: "#666" }}>Output</span>
              <button onClick={() => setShowTranscript(v => !v)} style={{ padding: "7px 14px", borderRadius: 8, border: "1px solid #ddd", background: "transparent", color: "#555", cursor: "pointer", fontSize: 13 }}>{showTranscript ? "hide transcript" : "view transcript"}</button>
              <button onClick={copy} style={{ padding: "7px 14px", borderRadius: 8, border: "1px solid #ddd", background: "transparent", color: "#555", cursor: "pointer", fontSize: 13 }}>{copied ? "copied!" : "copy all"}</button>
              <button onClick={reset} style={{ padding: "7px 14px", borderRadius: 8, border: "1px solid #ddd", background: "transparent", color: "#555", cursor: "pointer", fontSize: 13 }}>new video</button>
            </div>
            {showTranscript && (
              <div style={{ background: "#f9f9f9", border: "1px solid #eee", borderRadius: 12, padding: "1.25rem", fontSize: 13, color: "#666", whiteSpace: "pre-wrap", maxHeight: 150, overflowY: "auto", marginBottom: 8 }}>
                <span style={{ display: "inline-block", fontSize: 12, padding: "3px 10px", borderRadius: 20, background: "#EEEDFE", color: "#533AB7", border: "1px solid #AFA9EC", marginBottom: 8 }}>transcript</span>
                <br />{transcript}
              </div>
            )}
            <div style={{ background: "#f9f9f9", border: "1px solid #eee", borderRadius: 12, padding: "1.25rem", fontSize: 13.5, lineHeight: 1.85, color: "#111", whiteSpace: "pre-wrap", maxHeight: 520, overflowY: "auto" }}>
              <span style={{ display: "inline-block", fontSize: 12, padding: "3px 10px", borderRadius: 20, background: "#EEEDFE", color: "#533AB7", border: "1px solid #AFA9EC", marginBottom: 8 }}>hooks & caption</span>
              <br />{output}
            </div>
          </>
        )}
      </div>
    </main>
  );
}
