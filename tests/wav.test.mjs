import { test } from "node:test";
import assert from "node:assert/strict";
import { mixToMono, floatTo16BitPcm, encodeWav, splitIntoWavChunks, MAX_CHUNK_BYTES } from "../lib/wav.mjs";

const ascii = (buf, off, len) => String.fromCharCode(...new Uint8Array(buf, off, len));

function assertValidWav(buf, expectedSamples) {
  const v = new DataView(buf);
  assert.equal(ascii(buf, 0, 4), "RIFF");
  assert.equal(ascii(buf, 8, 4), "WAVE");
  assert.equal(ascii(buf, 36, 4), "data");
  assert.equal(v.getUint32(4, true), buf.byteLength - 8);
  assert.equal(v.getUint32(40, true), expectedSamples * 2);
  assert.equal(v.getUint16(22, true), 1, "mono");
  assert.equal(v.getUint32(24, true), 16000, "sample rate");
}

test("mixToMono averages channels", () => {
  const mono = mixToMono([new Float32Array([1, 0, -1]), new Float32Array([0, 0, -1])]);
  assert.deepEqual([...mono], [0.5, 0, -1]);
});

test("mixToMono handles no channels", () => {
  assert.equal(mixToMono([]).length, 0);
});

test("floatTo16BitPcm clamps and scales", () => {
  const pcm = floatTo16BitPcm(new Float32Array([2, 1, 0, -1, -2]));
  assert.deepEqual([...pcm], [32767, 32767, 0, -32768, -32768]);
});

test("encodeWav writes a correct header and the samples", () => {
  const pcm = new Int16Array([1, -1, 300]);
  const buf = encodeWav(pcm);
  assert.equal(buf.byteLength, 44 + 6);
  assertValidWav(buf, 3);
  assert.deepEqual([...new Int16Array(buf, 44)], [1, -1, 300]);
});

test("splitIntoWavChunks gives every chunk its own valid header", () => {
  const pcm = new Int16Array(25).map((_, i) => i);
  const maxBytes = 44 + 10 * 2; // 10 samples per chunk
  const chunks = splitIntoWavChunks(pcm, 16000, maxBytes);
  assert.equal(chunks.length, 3);
  const sizes = [10, 10, 5];
  chunks.forEach((c, i) => {
    assert.ok(c.byteLength <= maxBytes);
    assertValidWav(c, sizes[i]);
  });
  const joined = chunks.flatMap((c) => [...new Int16Array(c, 44)]);
  assert.deepEqual(joined, [...pcm], "no samples lost or duplicated");
});

test("splitIntoWavChunks returns one chunk for short audio and none for empty", () => {
  assert.equal(splitIntoWavChunks(new Int16Array(100)).length, 1);
  assert.equal(splitIntoWavChunks(new Int16Array(0)).length, 0);
});

test("default chunk size stays under Vercel's 4.5 MB body limit", () => {
  assert.ok(MAX_CHUNK_BYTES < 4.5 * 1024 * 1024);
});

test("splitIntoWavChunks rejects a size too small for a header", () => {
  assert.throws(() => splitIntoWavChunks(new Int16Array(10), 16000, 44));
});
