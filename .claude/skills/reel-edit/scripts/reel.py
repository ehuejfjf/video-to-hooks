#!/usr/bin/env python3
"""reel.py — turn a raw talking-head clip into a finished 1080x1920 Instagram Reel.

Free and local: ffmpeg + faster-whisper. No API keys.

Subcommands
  transcribe VIDEO            -> <work>/words.json + transcript.txt   (word timestamps)
  plan VIDEO [--drop L3,w40-52] -> <work>/edl.json                    (cut list)
  render VIDEO [--hook "..."] -> <work>/../<name>_reel.mp4            (final reel)
  preview VIDEO               -> <work>/preview.jpg                   (contact sheet w/ safe zones)
  auto VIDEO [--hook "..."]   -> all of the above with defaults

<work> is a folder next to the video called <name>_reel/.
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys

W, H = 1080, 1920
FPS = 30
FILLERS = {"um", "umm", "ummm", "uh", "uhh", "uhm", "er", "erm", "ah", "ahh", "hmm", "hm", "mm", "mmm"}
# Priming prompt nudges Whisper to write fillers down instead of silently dropping them.
FILLER_PROMPT = "Umm, so, uh, I was like, you know, uh... hmm. Okay, um, let me, uh, start again."

# Instagram Reels UI overlays (1080x1920). Bottom ~35% holds caption/username/audio,
# right rail holds like/comment/share, top holds the "Reels" header.
SAFE_TOP = 250
SAFE_BOTTOM = 672
SAFE_RIGHT = 140

# ----------------------------------------------------------------------------- utils


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd, cwd=None, quiet=True):
    if not quiet:
        print("$ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write(p.stderr[-4000:])
        die(f"command failed: {cmd[0]} (exit {p.returncode})")
    return p


def need(binary):
    if not shutil.which(binary):
        die(f"'{binary}' not found. Install it first (see SKILL.md → Setup).")


def workdir(video):
    base = os.path.splitext(os.path.abspath(video))[0]
    d = base + "_reel"
    os.makedirs(d, exist_ok=True)
    return d


def probe(video):
    need("ffprobe")
    p = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", video])
    info = json.loads(p.stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if not a:
        die("video has no audio track — nothing to transcribe")
    dur = float(info["format"].get("duration") or a.get("duration") or 0)
    w = h = 0
    if v:
        w, h = int(v["width"]), int(v["height"])
        rot = 0
        for sd in v.get("side_data_list", []) or []:
            if "rotation" in sd:
                rot = int(sd["rotation"])
        rot = int(v.get("tags", {}).get("rotate", rot) or rot)
        if abs(rot) % 180 == 90:
            w, h = h, w
    return {"duration": dur, "width": w, "height": h, "has_video": v is not None}


def load(path):
    with open(path) as f:
        return json.load(f)


def save(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False)


def norm(word):
    return re.sub(r"[^\w']", "", word.lower())


def fmt_t(t):
    return f"{t:6.2f}"


# ------------------------------------------------------------------------ transcribe


def cmd_transcribe(a):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        die("faster-whisper is not installed. Run:  pip install faster-whisper")
    info = probe(a.video)
    wd = workdir(a.video)
    print(f"Transcribing with faster-whisper '{a.model}' (first run downloads the model once)...")
    try:
        model = WhisperModel(a.model, device="auto", compute_type="auto")
    except Exception as e:  # noqa: BLE001
        die(f"couldn't load/download Whisper model '{a.model}' ({type(e).__name__}: {e}). "
            "The first run needs internet access to huggingface.co; after that it works offline.")
    # Decode with ffmpeg ourselves: faster-whisper's PyAV decoder breaks on some PyAV versions.
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", a.video, "-vn", "-ac", "1",
                          "-ar", "16000", "-f", "f32le", "-"], capture_output=True)
    if pcm.returncode != 0:
        die("ffmpeg could not decode the audio: " + pcm.stderr.decode(errors="ignore")[-500:])
    audio = np.frombuffer(pcm.stdout, dtype=np.float32)
    segs, tinfo = model.transcribe(
        audio,
        language=a.language,
        word_timestamps=True,
        initial_prompt=FILLER_PROMPT if a.keep_fillers_prompt else None,
        vad_filter=False,
        condition_on_previous_text=False,
    )
    words = []
    for seg in segs:
        for w in seg.words or []:
            text = w.word.strip()
            if not text:
                continue
            words.append({"i": len(words), "w": text, "s": round(w.start, 3), "e": round(w.end, 3),
                          "p": round(w.probability, 3)})
        print(f"  {seg.end:6.1f}s / {info['duration']:.1f}s", end="\r")
    print()
    if not words:
        die("no speech found")
    lines = build_lines(words)
    out = {"source": os.path.abspath(a.video), "duration": info["duration"], "width": info["width"],
           "height": info["height"], "language": tinfo.language, "words": words, "lines": lines}
    save(os.path.join(wd, "words.json"), out)
    write_transcript(wd, words, lines)
    print(f"{len(words)} words, {len(lines)} lines → {wd}/transcript.txt")


def build_lines(words):
    """Group words into sentence-ish lines (for retake review)."""
    lines, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        nxt = words[i + 1] if i + 1 < len(words) else None
        end_sentence = w["w"][-1:] in ".?!"
        long_gap = nxt is not None and nxt["s"] - w["e"] > 0.7
        if nxt is None or end_sentence or long_gap or len(cur) >= 25:
            lines.append([cur[0], cur[-1]])
            cur = []
    return lines


def write_transcript(wd, words, lines, path="transcript.txt"):
    with open(os.path.join(wd, path), "w") as f:
        f.write("# L<line> w<first>-<last> [start-end] text      (* = filler, auto-cut)\n")
        for n, (a, b) in enumerate(lines, 1):
            txt = " ".join(("*" + words[i]["w"]) if norm(words[i]["w"]) in FILLERS else words[i]["w"]
                           for i in range(a, b + 1))
            f.write(f"L{n:<3} w{a}-{b} [{fmt_t(words[a]['s'])}-{fmt_t(words[b]['e'])}] {txt}\n")


# ------------------------------------------------------------------------------ plan


def parse_drop(spec, lines, nwords):
    drop = set()
    if not spec:
        return drop
    for tok in re.split(r"[,\s]+", spec.strip()):
        if not tok:
            continue
        m = re.fullmatch(r"[Ll](\d+)(?:-[Ll]?(\d+))?", tok)
        if m:
            l1 = int(m.group(1))
            l2 = int(m.group(2) or l1)
            for ln in range(l1, l2 + 1):
                if not 1 <= ln <= len(lines):
                    die(f"line L{ln} does not exist (have L1-L{len(lines)})")
                a_, b_ = lines[ln - 1]
                drop.update(range(a_, b_ + 1))
            continue
        m = re.fullmatch(r"[Ww]?(\d+)(?:-[Ww]?(\d+))?", tok)
        if m:
            w1 = int(m.group(1))
            w2 = int(m.group(2) or w1)
            if w2 >= nwords:
                die(f"word w{w2} does not exist (have w0-w{nwords - 1})")
            drop.update(range(w1, w2 + 1))
            continue
        die(f"can't parse drop token '{tok}' (use L3, L3-L5, w40, w40-52)")
    return drop


def detect_silences(video, noise_db, min_d):
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-vn", "-af",
                        f"silencedetect=noise={noise_db}dB:d={min_d}", "-f", "null", "-"],
                       capture_output=True, text=True)
    sil, start = [], None
    for line in p.stderr.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            start = max(0.0, float(m.group(1)))
        m = re.search(r"silence_end: ([\d.]+)", line)
        if m and start is not None:
            sil.append((start, float(m.group(1))))
            start = None
    return sil


def cmd_plan(a):
    wd = workdir(a.video)
    wpath = os.path.join(wd, "words.json")
    if not os.path.exists(wpath):
        die("run `transcribe` first")
    data = load(wpath)
    words, lines = data["words"], data["lines"]
    dur = data["duration"]
    drop = parse_drop(a.drop, lines, len(words))
    if not a.keep_fillers:
        drop.update(w["i"] for w in words if norm(w["w"]) in FILLERS)
    keep = [w for w in words if w["i"] not in drop]
    if not keep:
        die("everything was dropped")

    sil = detect_silences(data["source"], a.noise_db, 0.12)

    def in_silence(t):
        for s, e in sil:
            if s <= t <= e:
                return (s, e)
        return None

    # Group kept words into continuous runs. A run breaks at a dropped word or a long pause.
    runs, cur = [], [keep[0]]
    for prev, w in zip(keep, keep[1:]):
        contiguous = w["i"] == prev["i"] + 1
        if contiguous and (w["s"] - prev["e"]) <= a.max_pause:
            cur.append(w)
        else:
            runs.append(cur)
            cur = [w]
    runs.append(cur)

    segs = []
    for r in runs:
        first, last = r[0], r[-1]
        prev_any = words[first["i"] - 1] if first["i"] > 0 else None
        next_any = words[last["i"] + 1] if last["i"] + 1 < len(words) else None
        s = first["s"] - a.pad_in
        e = last["e"] + a.pad_out
        # Whisper often stretches a word's end into the following silence: pull it back.
        z = in_silence(last["e"])
        if z and z[0] + a.pad_out < e:
            e = max(last["s"] + 0.08, z[0] + a.pad_out)
        z = in_silence(first["s"])
        if z and z[1] - a.pad_in > s:
            s = min(first["e"] - 0.08, z[1] - a.pad_in)
        # Never bleed into the neighbouring (possibly dropped) word.
        if prev_any:
            s = max(s, prev_any["e"] + 0.01)
        if next_any:
            e = min(e, next_any["s"] - 0.01)
        s, e = max(0.0, s), min(dur, e)
        if e - s < 0.12:
            continue
        segs.append({"start": round(s, 3), "end": round(e, 3), "words": [first["i"], last["i"]]})

    # merge segments that touch
    merged = []
    for sg in segs:
        if merged and sg["start"] - merged[-1]["end"] < 0.04 and sg["words"][0] == merged[-1]["words"][1] + 1:
            merged[-1]["end"] = sg["end"]
            merged[-1]["words"][1] = sg["words"][1]
        else:
            merged.append(sg)
    segs = merged

    zooms = [float(z) for z in a.zooms.split(",")]
    for k, sg in enumerate(segs):
        sg["zoom"] = zooms[k % len(zooms)]

    out_dur = sum(s["end"] - s["start"] for s in segs)
    edl = {"source": data["source"], "segments": segs, "dropped_words": sorted(drop),
           "settings": {"max_pause": a.max_pause, "pad_in": a.pad_in, "pad_out": a.pad_out}}
    save(os.path.join(wd, "edl.json"), edl)

    # Human-readable result so Claude can sanity-check the story still flows.
    kept_text = []
    for sg in segs:
        kept_text.append(" ".join(words[i]["w"] for i in range(sg["words"][0], sg["words"][1] + 1)
                                  if i not in drop))
    with open(os.path.join(wd, "edit.txt"), "w") as f:
        f.write(f"# {len(segs)} segments, {dur:.1f}s raw → {out_dur:.1f}s reel\n")
        for k, (sg, t) in enumerate(zip(segs, kept_text)):
            f.write(f"S{k + 1:<3} [{fmt_t(sg['start'])}-{fmt_t(sg['end'])}] x{sg['zoom']:.2f} {t}\n")
    print(f"{len(segs)} segments, {dur:.1f}s raw → {out_dur:.1f}s reel. Read {wd}/edit.txt")
    if out_dur > 90:
        print("warning: longer than 90s — Instagram Reels cap; trim more lines.")


# ---------------------------------------------------------------------------- render


def default_font():
    if platform.system() == "Darwin":
        return "Arial Black"
    if platform.system() == "Windows":
        return "Arial Black"
    return "DejaVu Sans"


def ass_color(hex_rgb, alpha=0):
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ass_time(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_escape(s):
    return s.replace("\\", "\\\\").replace("{", "(").replace("}", ")")


def wrap(text, width):
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        out.append(line)
    return "\\N".join(out)


def build_ass(words, edl, a, out_path):
    """Word-by-word highlighted captions on the OUTPUT timeline + optional hook title."""
    drop = set(edl["dropped_words"])
    timed = []  # (text, start, end) in output time
    off = 0.0
    for sg in edl["segments"]:
        for i in range(sg["words"][0], sg["words"][1] + 1):
            if i in drop:
                continue
            w = words[i]
            s = off + max(0.0, w["s"] - sg["start"])
            e = off + min(sg["end"] - sg["start"], w["e"] - sg["start"])
            timed.append([w["w"], s, max(e, s + 0.06)])
        off += sg["end"] - sg["start"]
    total = off

    # chunk into 1-3 word groups
    chunks, cur = [], []
    for k, t in enumerate(timed):
        cur.append(t)
        nxt = timed[k + 1] if k + 1 < len(timed) else None
        chars = sum(len(x[0]) + 1 for x in cur)
        brk = (nxt is None or len(cur) >= a.words_per_caption
               or chars + len(nxt[0]) > a.max_caption_chars
               or t[0][-1:] in ".?!,;:" or (nxt[1] - t[2]) > 0.35)
        if brk:
            chunks.append(cur)
            cur = []
    for k, c in enumerate(chunks):
        nxt_start = chunks[k + 1][0][1] if k + 1 < len(chunks) else total
        end = c[-1][2]
        if nxt_start - end < 0.4:
            end = nxt_start
        c.append(end)  # chunk end marker

    font = a.font or default_font()
    hi = ass_color(a.highlight)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Cap,{font},{a.caption_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
        f"-1,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1",
        f"Style: Hook,{font},{a.hook_size},&H00111111,&H00111111,&H00FFFFFF,&H00FFFFFF,"
        f"-1,0,0,0,100,100,0,0,3,22,0,8,90,90,0,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    y = a.caption_y
    # nudge left of centre so text clears the right-hand like/comment rail
    pos = f"\\an5\\pos({W // 2 - 30},{y})"
    if not a.no_captions:
        for c in chunks:
            end = c[-1]
            ws = c[:-1]
            texts = [ass_escape(x[0].upper() if a.uppercase else x[0]) for x in ws]
            for j, wd in enumerate(ws):
                s = ws[0][1] if j == 0 else wd[1]
                e = ws[j + 1][1] if j + 1 < len(ws) else end
                if e <= s:
                    continue
                parts = []
                for q, txt in enumerate(texts):
                    if q == j:
                        parts.append(f"{{\\c{hi}&\\fscx108\\fscy108}}{txt}{{\\c&H00FFFFFF&\\fscx100\\fscy100}}")
                    else:
                        parts.append(txt)
                pop = "\\fscx92\\fscy92\\t(0,80,\\fscx100\\fscy100)" if j == 0 else ""
                lines.append(f"Dialogue: 1,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{{{pos}{pop}}}" + " ".join(parts))
    if a.hook:
        hd = min(a.hook_duration, total)
        txt = wrap(ass_escape(a.hook), 20)
        lines.append(f"Dialogue: 2,{ass_time(0)},{ass_time(hd)},Hook,,0,0,0,,"
                     f"{{\\an8\\pos({W // 2 - 30},{a.hook_y})\\fad(0,200)}}{txt}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return total


def fit_filter(zoom, mode, anchor):
    if mode == "pad":
        return (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"boxblur=25:2,eq=brightness=-0.08[bg];[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    cw = "min(iw,ih*9/16)"
    return (f"crop=w='trunc({cw}/{zoom}/2)*2':h='trunc({cw}*16/9/{zoom}/2)*2':"
            f"x='(iw-ow)/2':y='(ih-oh)*{anchor}',scale={W}:{H}:flags=lanczos,setsar=1")


def cmd_render(a):
    need("ffmpeg")
    wd = workdir(a.video)
    for f in ("words.json", "edl.json"):
        if not os.path.exists(os.path.join(wd, f)):
            die(f"missing {f} — run transcribe and plan first")
    data = load(os.path.join(wd, "words.json"))
    edl = load(os.path.join(wd, "edl.json"))
    src = edl["source"]
    info = probe(src)
    if not info["has_video"]:
        die("source has no video stream")
    segdir = os.path.join(wd, "segs")
    shutil.rmtree(segdir, ignore_errors=True)
    os.makedirs(segdir)
    mode = a.fit
    if mode == "auto":
        mode = "pad" if info["width"] > info["height"] else "crop"

    listing = []
    n = len(edl["segments"])
    for k, sg in enumerate(edl["segments"]):
        d = sg["end"] - sg["start"]
        out = os.path.join(segdir, f"s{k:04d}.mkv")
        fade = min(0.025, d / 4)
        vf = fit_filter(sg.get("zoom", 1.0) if mode == "crop" else 1.0, mode, a.anchor) + f",fps={FPS},format=yuv420p"
        af = (f"aresample=48000,aformat=channel_layouts=stereo,afade=t=in:d={fade:.3f},"
              f"afade=t=out:st={d - fade:.3f}:d={fade:.3f}")
        run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{sg['start']:.3f}", "-i", src, "-t", f"{d:.3f}",
             "-filter_complex", f"[0:v]{vf}[v];[0:a]{af}[a]", "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-c:a", "pcm_s16le", out])
        listing.append(f"file '{out}'")
        print(f"  segment {k + 1}/{n}", end="\r")
    print()
    with open(os.path.join(segdir, "list.txt"), "w") as f:
        f.write("\n".join(listing) + "\n")
    joined = os.path.join(wd, "joined.mkv")
    run(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", os.path.join(segdir, "list.txt"),
         "-c", "copy", joined])

    build_ass(data["words"], edl, a, os.path.join(wd, "captions.ass"))
    name = os.path.splitext(os.path.basename(src))[0]
    final = a.out or os.path.join(os.path.dirname(wd), f"{name}_reel.mp4")
    vf = "ass=captions.ass"
    fonts = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
    if os.path.isdir(fonts) and any(f.lower().endswith((".ttf", ".otf")) for f in os.listdir(fonts)):
        vf = f"ass=captions.ass:fontsdir={os.path.abspath(fonts)}"
    af = "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000" if not a.no_loudnorm else "anull"
    run(["ffmpeg", "-y", "-hide_banner", "-i", joined, "-vf", vf, "-af", af,
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
         os.path.abspath(final)], cwd=wd)
    if not a.keep_temp:
        shutil.rmtree(segdir, ignore_errors=True)
        os.remove(joined)
    dur = probe(final)["duration"]
    print(f"Done → {final}  ({dur:.1f}s, {W}x{H})")
    save(os.path.join(wd, "last_render.json"), {"final": os.path.abspath(final), "duration": dur})


# --------------------------------------------------------------------------- preview


def cmd_preview(a):
    wd = workdir(a.video)
    lr = os.path.join(wd, "last_render.json")
    if not os.path.exists(lr):
        die("render first")
    final = load(lr)["final"]
    dur = probe(final)["duration"]
    edl = load(os.path.join(wd, "edl.json"))
    # sample: just after every cut (where jumps show) + evenly spaced, max 12 frames
    times, off = [], 0.0
    for sg in edl["segments"]:
        times.append(off + 0.15)
        off += sg["end"] - sg["start"]
    times = [0.5] + [t for t in times[1:] if t < dur - 0.05]
    if len(times) > a.frames:
        step = len(times) / a.frames
        times = [times[int(k * step)] for k in range(a.frames)]
    dedup = []
    for t in sorted(times):
        if not dedup or t - dedup[-1] > 0.4:
            dedup.append(t)
    times = dedup
    fdir = os.path.join(wd, "frames")
    shutil.rmtree(fdir, ignore_errors=True)
    os.makedirs(fdir)
    zone = (f"drawbox=x=0:y=0:w=iw:h={SAFE_TOP}:color=red@0.4:t=fill,"
            f"drawbox=x=0:y={H - SAFE_BOTTOM}:w=iw:h={SAFE_BOTTOM}:color=red@0.4:t=fill,"
            f"drawbox=x={W - SAFE_RIGHT}:y={SAFE_TOP}:w={SAFE_RIGHT}:h={H - SAFE_TOP - SAFE_BOTTOM}:color=red@0.4:t=fill")
    for k, t in enumerate(times):
        run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{t:.2f}", "-i", final, "-frames:v", "1",
             "-vf", f"{zone},scale=360:640", os.path.join(fdir, f"f{k:03d}.png")])
    cols = 4
    rows = (len(times) + cols - 1) // cols
    out = os.path.join(wd, "preview.jpg")
    run(["ffmpeg", "-y", "-hide_banner", "-i", os.path.join(fdir, "f%03d.png"),
         "-vf", f"tile={cols}x{rows}:padding=6:color=white", "-frames:v", "1", "-q:v", "3", out])
    shutil.rmtree(fdir, ignore_errors=True)
    print(f"Contact sheet ({len(times)} frames at {', '.join(f'{t:.1f}s' for t in times)}) → {out}")
    print("Red = Instagram UI overlays. Captions, hook and face should sit outside red.")


# ------------------------------------------------------------------------------ auto


def cmd_auto(a):
    wd = workdir(a.video)
    if not os.path.exists(os.path.join(wd, "words.json")):
        cmd_transcribe(a)
    cmd_plan(a)
    cmd_render(a)
    cmd_preview(a)


# ------------------------------------------------------------------------------- cli


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def t_args(sp):
        sp.add_argument("--model", default="small", help="tiny|base|small|medium|large-v3 (default small)")
        sp.add_argument("--language", default=None, help="force language code, e.g. en")
        sp.add_argument("--no-filler-prompt", dest="keep_fillers_prompt", action="store_false")

    def p_args(sp):
        sp.add_argument("--drop", default="", help="lines/words to cut: L3,L5-L7,w40-52")
        sp.add_argument("--keep-fillers", action="store_true", help="don't auto-cut um/uh")
        sp.add_argument("--max-pause", type=float, default=0.30, help="pauses longer than this get cut (s)")
        sp.add_argument("--pad-in", type=float, default=0.06)
        sp.add_argument("--pad-out", type=float, default=0.10)
        sp.add_argument("--noise-db", type=float, default=-35)
        sp.add_argument("--zooms", default="1.0,1.12", help="zoom cycle per segment (punch-ins hide jump cuts)")

    def r_args(sp):
        sp.add_argument("--hook", default="", help="on-screen hook text for the first seconds")
        sp.add_argument("--hook-duration", type=float, default=3.0)
        sp.add_argument("--hook-y", type=int, default=330)
        sp.add_argument("--hook-size", type=int, default=68)
        sp.add_argument("--caption-y", type=int, default=1130, help="caption centre y (keep < 1248)")
        sp.add_argument("--caption-size", type=int, default=80)
        sp.add_argument("--max-caption-chars", type=int, default=16)
        sp.add_argument("--words-per-caption", type=int, default=3)
        sp.add_argument("--highlight", default="#FFE600", help="active-word colour")
        sp.add_argument("--font", default=None)
        sp.add_argument("--no-uppercase", dest="uppercase", action="store_false")
        sp.add_argument("--no-captions", action="store_true")
        sp.add_argument("--fit", choices=["auto", "crop", "pad"], default="auto",
                        help="crop to 9:16 or blurred-pad (auto: pad landscape, crop vertical)")
        sp.add_argument("--anchor", type=float, default=0.35, help="crop/zoom vertical anchor 0=top 1=bottom")
        sp.add_argument("--no-loudnorm", action="store_true")
        sp.add_argument("--keep-temp", action="store_true")
        sp.add_argument("--out", default=None)

    sp = sub.add_parser("transcribe"); sp.add_argument("video"); t_args(sp)
    sp = sub.add_parser("plan"); sp.add_argument("video"); p_args(sp)
    sp = sub.add_parser("render"); sp.add_argument("video"); r_args(sp)
    sp = sub.add_parser("preview"); sp.add_argument("video"); sp.add_argument("--frames", type=int, default=12)
    sp = sub.add_parser("auto"); sp.add_argument("video"); t_args(sp); p_args(sp); r_args(sp)
    sp.add_argument("--frames", type=int, default=12)

    a = p.parse_args()
    if not os.path.exists(a.video):
        die(f"no such file: {a.video}")
    {"transcribe": cmd_transcribe, "plan": cmd_plan, "render": cmd_render,
     "preview": cmd_preview, "auto": cmd_auto}[a.cmd](a)


if __name__ == "__main__":
    main()
