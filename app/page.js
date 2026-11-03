"use client";
import { useState, useRef } from "react";
import { SAMPLE_RATE, mixToMono, floatTo16BitPcm, splitIntoWavChunks } from "../lib/wav.mjs";
import { readJson } from "../lib/http.mjs";

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

  // Decode the video's audio track and return it as uploadable WAV chunks,
  // each a complete WAV file under the hosting request-size limit.
  async function extractAudio(file) {
    setStatus("Extracting audio from video...");
    const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: SAMPLE_RATE });
    try {
      const audioBuf = await ctx.decodeAudioData(await file.arrayBuffer());
      const channels = [];
      for (let c = 0; c < audioBuf.numberOfChannels; c++) channels.push(audioBuf.getChannelData(c));
      const pcm = floatTo16BitPcm(mixToMono(channels));
      return splitIntoWavChunks(pcm, SAMPLE_RATE).map((buf) => new Blob([buf], { type: "audio/wav" }));
    } catch (e) {
      throw new Error("Could not read audio from this file. " + (e?.message || ""));
    } finally {
      ctx.close();
    }
  }

  async function transcribeAudio(chunks) {
    const parts = [];
    for (let i = 0; i < chunks.length; i++) {
      setStatus(`Transcribing audio${chunks.length > 1 ? ` (part ${i + 1} of ${chunks.length})` : ""}...`);
      const fd = new FormData();
      fd.append("file", chunks[i], "audio.wav");
      const data = await readJson(await fetch("/api/transcribe", { method: "POST", body: fd }));
      if (data.transcript) parts.push(data.transcript);
    }
    return parts.join(" ");
  }

  async function run() {
    if (!videoFile) return;
    setError(""); setOutput(""); setTranscript(""); setLoading(true);
    try {
      const chunks = await extractAudio(videoFile);
      const tx = await transcribeAudio(chunks);
      if (!tx.trim()) throw new Error("No speech was found in this video.");
      setTranscript(tx);
      setStatus("Generating hooks & caption...");
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: tx })
      });
      const data = await readJson(res);
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
