// Pure helpers for turning decoded audio into WAV files small enough to upload.
// Kept free of browser APIs so they can be unit tested with `node --test`.

export const SAMPLE_RATE = 16000;
const HEADER_BYTES = 44;
const BYTES_PER_SAMPLE = 2; // 16-bit PCM, mono

// Vercel rejects serverless request bodies over 4.5 MB, so each uploaded
// chunk stays comfortably below that (about 1m49s of 16 kHz mono audio).
export const MAX_CHUNK_BYTES = 3.5 * 1024 * 1024;

/** Average any number of Float32 channels into one mono channel. */
export function mixToMono(channels) {
  if (channels.length === 0) return new Float32Array(0);
  const len = channels[0].length;
  const mono = new Float32Array(len);
  for (const ch of channels) {
    for (let i = 0; i < len; i++) mono[i] += ch[i] / channels.length;
  }
  return mono;
}

/** Convert float samples in [-1, 1] to 16-bit signed PCM, clamping out-of-range values. */
export function floatTo16BitPcm(samples) {
  const pcm = new Int16Array(samples.length);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return pcm;
}

/** Wrap 16-bit mono PCM in a complete WAV container. Returns an ArrayBuffer. */
export function encodeWav(pcm, sampleRate = SAMPLE_RATE) {
  const dataBytes = pcm.length * BYTES_PER_SAMPLE;
  const buf = new ArrayBuffer(HEADER_BYTES + dataBytes);
  const v = new DataView(buf);
  const str = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
  str(0, "RIFF"); v.setUint32(4, 36 + dataBytes, true); str(8, "WAVE");
  str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true);
  v.setUint32(24, sampleRate, true); v.setUint32(28, sampleRate * BYTES_PER_SAMPLE, true);
  v.setUint16(32, BYTES_PER_SAMPLE, true); v.setUint16(34, 16, true);
  str(36, "data"); v.setUint32(40, dataBytes, true);
  new Int16Array(buf, HEADER_BYTES).set(pcm);
  return buf;
}

/**
 * Split PCM into several standalone WAV files, each at most maxBytes long
 * including its own header. Slicing one big WAV by bytes (the old approach)
 * left every chunk after the first without a header, so Whisper rejected them.
 */
export function splitIntoWavChunks(pcm, sampleRate = SAMPLE_RATE, maxBytes = MAX_CHUNK_BYTES) {
  const samplesPerChunk = Math.floor((maxBytes - HEADER_BYTES) / BYTES_PER_SAMPLE);
  if (samplesPerChunk <= 0) throw new Error("maxBytes is too small to hold a WAV header");
  const chunks = [];
  for (let start = 0; start < pcm.length; start += samplesPerChunk) {
    chunks.push(encodeWav(pcm.subarray(start, start + samplesPerChunk), sampleRate));
  }
  return chunks;
}
