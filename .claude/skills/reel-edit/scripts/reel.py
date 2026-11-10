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

    # Long continuous takes get split into ~max_shot pieces at the quietest word gap, with the
    # zoom alternating, so the reel "changes camera" every few seconds like a multi-cam edit.
    if a.max_shot and a.max_shot > 0:
        split = []
        for sg in segs:
            pieces = [sg]
            while pieces[-1]["end"] - pieces[-1]["start"] > a.max_shot * 1.25:
                cur_sg = pieces.pop()
                target = cur_sg["start"] + a.max_shot
                best = None
                for i in range(cur_sg["words"][0], cur_sg["words"][1]):
                    if i in drop or (i + 1) in drop:
                        continue
                    t = (words[i]["e"] + words[i + 1]["s"]) / 2
                    if t - cur_sg["start"] < 1.2 or cur_sg["end"] - t < 1.2:
                        continue
                    score = abs(t - target) - 2.0 * (words[i + 1]["s"] - words[i]["e"])
                    if words[i]["w"][-1:] in ".?!,":
                        score -= 0.6
                    if best is None or score < best[0]:
                        best = (score, i, t)
                if best is None:
                    pieces.append(cur_sg)
                    break
                _, i, t = best
                t = round(t, 3)
                pieces.append({"start": cur_sg["start"], "end": t, "words": [cur_sg["words"][0], i],
                               **({"join_prev": True} if cur_sg.get("join_prev") else {})})
                pieces.append({"start": t, "end": cur_sg["end"], "words": [i + 1, cur_sg["words"][1]],
                               "join_prev": True})
            split.extend(pieces)
        segs = split

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
        f.write(f"# {len(segs)} shots, {dur:.1f}s raw → {out_dur:.1f}s reel   (~ = same take, just a zoom change)\n")
        for k, (sg, t) in enumerate(zip(segs, kept_text)):
            j = "~" if sg.get("join_prev") else " "
            f.write(f"S{k + 1:<3}{j}[{fmt_t(sg['start'])}-{fmt_t(sg['end'])}] x{sg['zoom']:.2f} {t}\n")
    print(f"{len(segs)} segments, {dur:.1f}s raw → {out_dur:.1f}s reel. Read {wd}/edit.txt")
    if out_dur > 90:
        print("warning: longer than 90s — Instagram Reels cap; trim more lines.")


# ---------------------------------------------------------------------------- render

FONTS_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts"))

# Style presets. "podcast" was matched to the creator's reference reel (Nov 2026):
# sentence-case Montserrat captions under the face, boxed 2-line quote hook (white / gold),
# gold-bar lower third, -11 LUFS. "bold" is the classic Hormozi look.
STYLES = {
    "podcast": dict(font="Montserrat", caption_size=86, caption_y=1310, uppercase=False, highlight="none",
                    words_per_caption=3, max_caption_chars=18, strip_punct=True, caption_box=False,
                    hook_size=108, hook_y=234, hook_duration=3.8, hook_style="boxed", lufs=-11.0,
                    accent="#F2C14E"),
    "bold": dict(font=None, caption_size=80, caption_y=1130, uppercase=True, highlight="#FFE600",
                 words_per_caption=3, max_caption_chars=16, strip_punct=False, caption_box=False,
                 hook_size=68, hook_y=330, hook_duration=3.0, hook_style="card", lufs=-14.0,
                 accent="#FFE600"),
}


def apply_style(a):
    st = STYLES[a.style]
    for k, v in st.items():
        if getattr(a, k, None) is None:
            setattr(a, k, v)
    if not a.font:
        a.font = default_font()


def default_font():
    if any(f.startswith("Montserrat") for f in os.listdir(FONTS_DIR)) if os.path.isdir(FONTS_DIR) else False:
        return "Montserrat"
    if platform.system() in ("Darwin", "Windows"):
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
    return out


_MEASURE_CACHE = {}


def measure_text(text, font, size, bold=True):
    """Pixel width/height of text as libass will render it (one tiny ffmpeg call, cached)."""
    key = (text, font, size, bold)
    if key in _MEASURE_CACHE:
        return _MEASURE_CACHE[key]
    import tempfile
    import numpy as np
    style = (f"Style: A,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,{-1 if bold else 0},"
             f"0,0,0,100,100,0,0,1,0,0,5,0,0,0,1")
    MW = 4000  # wide canvas so text wider than the frame is measured, not clipped
    body = "\n".join(ass_header([style], MW) + [
        f"Dialogue: 0,0:00:00.00,0:00:01.00,A,,0,0,0,,{{\\an5\\pos({MW // 2},{H // 2})\\q2}}{ass_escape(text)}"])
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "m.ass"), "w", encoding="utf-8") as f:
            f.write(body + "\n")
        fonts = f":fontsdir={FONTS_DIR}" if os.path.isdir(FONTS_DIR) else ""
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i", f"color=black:s={MW}x{H}:d=0.1",
                              "-vf", f"ass=m.ass{fonts}", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True, cwd=td).stdout
    try:
        img = np.frombuffer(raw, np.uint8).reshape(H, MW)
        xs = np.where(img.max(0) > 100)[0]
        ys = np.where(img.max(1) > 100)[0]
        res = (int(xs[-1] - xs[0]), int(ys[-1] - ys[0]))
    except Exception:  # noqa: BLE001  fall back to a char-count estimate
        res = (int(len(text) * size * 0.34), int(size * 0.7))
    _MEASURE_CACHE[key] = res
    return res


def rounded_rect(w, h, r):
    r = max(0, min(r, w // 2, h // 2))
    return (f"m {r} 0 l {w - r} 0 b {w} 0 {w} 0 {w} {r} l {w} {h - r} b {w} {h} {w} {h} {w - r} {h} "
            f"l {r} {h} b 0 {h} 0 {h} 0 {h - r} l 0 {r} b 0 0 0 0 {r} 0")


def split_two(text):
    """Split a hook into two balanced lines (or at a user '|')."""
    if "|" in text:
        return [x.strip() for x in text.split("|") if x.strip()][:3]
    ws = text.split()
    if len(ws) < 4:
        return [text]
    best = min(range(1, len(ws)), key=lambda k: abs(len(" ".join(ws[:k])) - len(" ".join(ws[k:]))))
    return [" ".join(ws[:best]), " ".join(ws[best:])]


def ass_header(styles, play_w=None):
    return [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {play_w or W}", f"PlayResY: {H}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        *styles, "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]


def timed_words(words, edl):
    """Kept words placed on the OUTPUT timeline."""
    drop = set(edl["dropped_words"])
    timed, off = [], 0.0
    for sg in edl["segments"]:
        for i in range(sg["words"][0], sg["words"][1] + 1):
            if i in drop:
                continue
            w = words[i]
            s = off + max(0.0, w["s"] - sg["start"])
            e = off + min(sg["end"] - sg["start"], w["e"] - sg["start"])
            if timed and w["w"].startswith("-") and len(w["w"]) > 1:
                timed[-1]["w"] += w["w"]
                timed[-1]["e"] = max(timed[-1]["e"], e)
                continue
            timed.append({"i": i, "w": w["w"], "s": s, "e": max(e, s + 0.06)})
        off += sg["end"] - sg["start"]
    return timed, off


def build_ass(timed, total, a, out_path):
    chunks, cur = [], []
    for k, t in enumerate(timed):
        cur.append(t)
        nxt = timed[k + 1] if k + 1 < len(timed) else None
        chars = sum(len(x["w"]) + 1 for x in cur)
        brk = (nxt is None or len(cur) >= a.words_per_caption
               or chars + len(nxt["w"]) > a.max_caption_chars
               or t["w"][-1:] in ".?!,;:" or (nxt["s"] - t["e"]) > 0.35)
        if brk:
            chunks.append(cur)
            cur = []
    ends = []
    for k, c in enumerate(chunks):
        nxt_start = chunks[k + 1][0]["s"] if k + 1 < len(chunks) else total
        end = c[-1]["e"]
        ends.append(nxt_start if nxt_start - end < 0.4 else end)

    font = a.font
    accent = ass_color(a.accent)
    styles = []
    if a.style == "podcast":
        styles.append(f"Style: Cap,{font},{a.caption_size},&H00FFFFFF,&H00FFFFFF,&H90000000,&H00000000,"
                      f"-1,0,0,0,100,100,0,0,1,3,0,5,60,60,0,1")
    else:
        styles.append(f"Style: Cap,{font},{a.caption_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,"
                      f"-1,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1")
    # boxed hook: each line its own opaque black box
    styles.append(f"Style: HookBox,{font},{a.hook_size},&H00FFFFFF,&H00FFFFFF,&H10141414,&H00000000,"
                  f"-1,0,0,0,100,100,0,0,3,16,0,8,60,60,0,1")
    styles.append(f"Style: Hook,{font},{a.hook_size},&H00111111,&H00111111,&H00FFFFFF,&H00FFFFFF,"
                  f"-1,0,0,0,100,100,0,0,3,22,0,8,90,90,0,1")
    styles.append(f"Style: LT1,{font},70,{accent},{accent},&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,4,0,0,0,1")
    styles.append(f"Style: LT2,{font},50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,4,0,0,0,1")
    styles.append("Style: Box,Arial,10,&H40000000,&H40000000,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1")
    lines = ass_header(styles)

    cx = W // 2 - 20  # a touch left of centre to clear the right-hand button rail
    if not a.no_captions:
        hl = None if (a.highlight or "none").lower() == "none" else ass_color(a.highlight)
        for c, end in zip(chunks, ends):
            texts = []
            for x in c:
                t = x["w"]
                if a.strip_punct:
                    t = re.sub(r"[.,!?;:\"“”…]+", "", t)
                if a.uppercase:
                    t = t.upper()
                texts.append(ass_escape(t))
            pos = f"\\an5\\pos({cx},{a.caption_y})"
            if a.style == "podcast":
                lines.append(f"Dialogue: 1,{ass_time(c[0]['s'])},{ass_time(end)},Cap,,0,0,0,,"
                             f"{{{pos}\\blur3}}" + " ".join(texts))
                continue
            for j in range(len(c)):
                s = c[0]["s"] if j == 0 else c[j]["s"]
                e = c[j + 1]["s"] if j + 1 < len(c) else end
                if e <= s:
                    continue
                parts = [(f"{{\\c{hl}&\\fscx108\\fscy108}}{txt}{{\\c&H00FFFFFF&\\fscx100\\fscy100}}"
                          if (q == j and hl) else txt) for q, txt in enumerate(texts)]
                pop = "\\fscx92\\fscy92\\t(0,80,\\fscx100\\fscy100)" if j == 0 else ""
                lines.append(f"Dialogue: 1,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{{{pos}{pop}}}" + " ".join(parts))

    if a.hook:
        hd = min(a.hook_duration, total)
        if a.hook_style == "boxed":
            hook_lines = split_two(a.hook)
            size = a.hook_size
            widest = max(measure_text(ln, font, size)[0] for ln in hook_lines)
            if widest > W - 180:  # long hook: shrink to fit
                size = int(size * (W - 180) / widest)
            box_h = int(size * 0.74)
            pitch = box_h + 4
            for n, ln in enumerate(hook_lines):
                tw, _ = measure_text(ln, font, size)
                bw = tw + int(size * 0.5)
                top = a.hook_y + n * pitch
                col = "\\c&HFFFFFF&" if n % 2 == 0 else f"\\c{accent}&"
                lines.append(f"Dialogue: 2,{ass_time(0)},{ass_time(hd)},Box,,0,0,0,,"
                             f"{{\\an7\\pos({cx - bw // 2},{top})\\p1\\1c&H141414&\\1a&H10&\\fad(0,150)}}"
                             f"{rounded_rect(bw, box_h, int(size * 0.1))}{{\\p0}}")
                lines.append(f"Dialogue: 3,{ass_time(0)},{ass_time(hd)},Cap,,0,0,0,,"
                             f"{{\\an5\\pos({cx},{top + box_h // 2 + int(size * 0.03)})\\fs{size}\\bord0\\shad0"
                             f"{col}\\fad(0,150)}}{ass_escape(ln)}")
        else:
            txt = "\\N".join(wrap(ass_escape(a.hook), 20))
            lines.append(f"Dialogue: 2,{ass_time(0)},{ass_time(hd)},Hook,,0,0,0,,"
                         f"{{\\an8\\pos({cx},{a.hook_y})\\fad(0,200)}}{txt}")

    if a.lower_title:
        s0 = min(a.lower_start, max(0.0, total - 1))
        s1 = min(total, s0 + a.lower_duration)
        y0 = a.lower_y
        tw = measure_text(a.lower_title, font, 70)[0]
        sw = measure_text(a.lower_sub, font, 50, bold=False)[0] if a.lower_sub else 0
        bw = min(max(tw, sw) + 38 + 34, W - 120)
        bh = 150 if a.lower_sub else 96
        fad = "\\fad(200,200)"
        lines.append(f"Dialogue: 3,{ass_time(s0)},{ass_time(s1)},Box,,0,0,0,,"
                     f"{{\\an7\\pos(80,{y0})\\p1\\1c&H000000&\\1a&H30&{fad}}}m 0 0 l {bw} 0 {bw} {bh} 0 {bh}{{\\p0}}")
        lines.append(f"Dialogue: 4,{ass_time(s0)},{ass_time(s1)},Box,,0,0,0,,"
                     f"{{\\an7\\pos(80,{y0})\\p1\\1c{accent}&\\1a&H00&{fad}}}m 0 0 l 12 0 12 {bh} 0 {bh}{{\\p0}}")
        ty = y0 + (48 if a.lower_sub else bh // 2)
        lines.append(f"Dialogue: 5,{ass_time(s0)},{ass_time(s1)},LT1,,0,0,0,,"
                     f"{{\\an4\\pos(118,{ty}){fad}}}{ass_escape(a.lower_title)}")
        if a.lower_sub:
            lines.append(f"Dialogue: 5,{ass_time(s0)},{ass_time(s1)},LT2,,0,0,0,,"
                         f"{{\\an4\\pos(118,{y0 + 106}){fad}}}{ass_escape(a.lower_sub)}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def fit_filter(zoom, mode, anchor):
    if mode == "pad":
        return (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                f"boxblur=25:2,eq=brightness=-0.08[bg];[b]scale={W}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    cw = "min(iw,ih*9/16)"
    return (f"crop=w='trunc({cw}/{zoom}/2)*2':h='trunc({cw}*16/9/{zoom}/2)*2':"
            f"x='(iw-ow)/2':y='(ih-oh)*{anchor}',scale={W}:{H}:flags=lanczos,setsar=1")


def snap(t):
    return round(round(t * FPS) / FPS, 6)


def make_endcard(a, wd, out):
    """Branded end card: gradient, optional logo + thumbnail, heading/handle/title/CTA text."""
    d = a.end_duration
    bg = os.path.join(wd, "end_bg.png")
    c0, c1 = [c.strip().lstrip("#") for c in a.end_colors.split(",")[:2]]
    ch = [(int(c0[i:i + 2], 16), int(c1[i:i + 2], 16)) for i in (0, 2, 4)]
    geq = ":".join(f"{n}='{x}+({y}-{x})*Y/H'" for n, (x, y) in zip("rgb", ch))
    run(["ffmpeg", "-y", "-hide_banner", "-f", "lavfi", "-i", f"color=black:s={W}x{H}", "-vf",
         f"format=rgb24,geq={geq}",
         "-frames:v", "1", bg])
    font = a.font
    styles = [f"Style: H,{font},116,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,8,60,60,0,1",
              f"Style: S,{font},84,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,8,60,60,0,1",
              f"Style: T,{font},74,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,8,90,90,0,1"]
    ev = ass_header(styles)
    t1 = ass_time(d)
    y = 400  # same layout with or without a logo
    if a.end_heading:
        ev.append(f"Dialogue: 0,0:00:00.00,{t1},H,,0,0,0,,{{\\an8\\pos({W // 2},{y})}}{ass_escape(a.end_heading)}")
    if a.end_handle:
        ev.append(f"Dialogue: 0,0:00:00.00,{t1},S,,0,0,0,,{{\\an8\\pos({W // 2},{y + 118})}}{ass_escape(a.end_handle)}")
    img_top, img_h = y + 225, 0
    if a.end_image:
        img_h = 440
    ty = img_top + img_h + 60
    for n, part in enumerate([a.end_text, a.end_cta]):
        if not part:
            continue
        txt = "\\N".join(wrap(ass_escape(part), 24))
        ev.append(f"Dialogue: 0,0:00:00.00,{t1},T,,0,0,0,,{{\\an8\\pos({W // 2},{ty})}}{txt}")
        ty += 92 * len(wrap(part, 24)) + 80
    with open(os.path.join(wd, "endcard.ass"), "w", encoding="utf-8") as f:
        f.write("\n".join(ev) + "\n")
    inputs = ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", bg]
    fc, last, idx = [], "[0:v]", 1
    if a.end_logo:
        inputs += ["-i", a.end_logo]
        fc.append(f"[{idx}:v]scale=620:-1[lg];{last}[lg]overlay=(W-w)/2:{y - 190}[v{idx}]")
        last, idx = f"[v{idx}]", idx + 1
    if a.end_image:
        inputs += ["-i", a.end_image]
        fc.append(f"[{idx}:v]scale=780:{img_h}:force_original_aspect_ratio=increase,crop=780:{img_h},"
                  f"pad=792:{img_h + 12}:6:6:color=0x222222[im];{last}[im]overlay=(W-w)/2:{img_top}[v{idx}]")
        last, idx = f"[v{idx}]", idx + 1
    fonts = f":fontsdir={FONTS_DIR}" if os.path.isdir(FONTS_DIR) else ""
    fc.append(f"{last}ass=endcard.ass{fonts},fps={FPS},format=yuv420p[v]")
    inputs += ["-f", "lavfi", "-t", f"{d:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
    run(["ffmpeg", "-y", "-hide_banner", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]",
         "-map", f"{idx}:a", "-t", f"{d:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
         "-c:a", "pcm_s16le", out], cwd=wd)


def parse_broll(spec, timed, lines):
    """'w60-65=gym.mp4,L4=seminar.mov' -> [(out_start, out_end, path)]"""
    out = []
    if not spec:
        return out
    by_i = {t["i"]: t for t in timed}
    for item in spec.split(","):
        if "=" not in item:
            die(f"b-roll item '{item}' needs RANGE=FILE")
        rng, path = item.split("=", 1)
        rng, path = rng.strip(), os.path.expanduser(path.strip())
        if not os.path.exists(path):
            die(f"b-roll file not found: {path}")
        m = re.fullmatch(r"[Ll](\d+)", rng)
        if m:
            w1, w2 = lines[int(m.group(1)) - 1]
        else:
            m = re.fullmatch(r"[Ww]?(\d+)-[Ww]?(\d+)", rng) or re.fullmatch(r"[Ww]?(\d+)", rng)
            if not m:
                die(f"can't parse b-roll range '{rng}'")
            w1 = int(m.group(1))
            w2 = int(m.group(2)) if m.lastindex and m.lastindex > 1 else w1
        kept = [by_i[i] for i in range(w1, w2 + 1) if i in by_i]
        if not kept:
            die(f"b-roll range {rng} covers no kept words")
        out.append((kept[0]["s"], kept[-1]["e"], os.path.abspath(path)))
    return out


def cmd_render(a):
    need("ffmpeg")
    apply_style(a)
    for k in ("end_image", "end_logo"):
        v = getattr(a, k)
        if v:
            v = os.path.abspath(os.path.expanduser(v))
            if not os.path.exists(v):
                die(f"--{k.replace('_', '-')} file not found: {v}")
            setattr(a, k, v)
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
    # Snap every cut to the frame grid so audio and video stay in sync across many cuts.
    for sg in edl["segments"]:
        sg["start"], sg["end"] = snap(sg["start"]), snap(sg["end"])
    edl["segments"] = [sg for sg in edl["segments"] if sg["end"] - sg["start"] >= 2 / FPS]
    segdir = os.path.join(wd, "segs")
    shutil.rmtree(segdir, ignore_errors=True)
    os.makedirs(segdir)
    mode = a.fit
    if mode == "auto":
        mode = "pad" if info["width"] > info["height"] else "crop"

    listing = []
    segs = edl["segments"]
    n = len(segs)
    for k, sg in enumerate(segs):
        d = sg["end"] - sg["start"]
        out = os.path.join(segdir, f"s{k:04d}.mkv")
        fade = min(0.025, d / 4)
        fades = []
        if not sg.get("join_prev"):
            fades.append(f"afade=t=in:d={fade:.3f}")
        if not (k + 1 < n and segs[k + 1].get("join_prev")):
            fades.append(f"afade=t=out:st={d - fade:.3f}:d={fade:.3f}")
        vf = fit_filter(sg.get("zoom", 1.0) if mode == "crop" else 1.0, mode, a.anchor) + f",fps={FPS},format=yuv420p"
        af = ",".join(["aresample=48000", "aformat=channel_layouts=stereo", *fades])
        run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{sg['start']:.4f}", "-i", src, "-t", f"{d:.4f}",
             "-filter_complex", f"[0:v]{vf}[v];[0:a]{af}[a]", "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-c:a", "pcm_s16le", out])
        listing.append(f"file '{out}'")
        print(f"  shot {k + 1}/{n}", end="\r")
    print()
    timed, total = timed_words(data["words"], edl)
    if a.end_heading or a.end_cta or a.end_image:
        endc = os.path.join(segdir, "endcard.mkv")
        make_endcard(a, wd, endc)
        listing.append(f"file '{endc}'")
    with open(os.path.join(segdir, "list.txt"), "w") as f:
        f.write("\n".join(listing) + "\n")
    joined = os.path.join(wd, "joined.mkv")
    run(["ffmpeg", "-y", "-hide_banner", "-f", "concat", "-safe", "0", "-i", os.path.join(segdir, "list.txt"),
         "-c", "copy", joined])

    build_ass(timed, total, a, os.path.join(wd, "captions.ass"))
    name = os.path.splitext(os.path.basename(src))[0]
    final = a.out or os.path.join(os.path.dirname(wd), f"{name}_reel.mp4")
    fonts = f":fontsdir={FONTS_DIR}" if os.path.isdir(FONTS_DIR) else ""

    # b-roll: full-frame cutaways over chosen words; speaker audio continues underneath.
    inputs, fc, last = ["-i", joined], [], "[0:v]"
    for k, (s0, s1, path) in enumerate(parse_broll(a.broll, timed, data["lines"])):
        inputs += ["-i", path]
        dur_b = s1 - s0 + 0.1
        fc.append(f"[{k + 1}:v]trim=0:{dur_b:.3f},setpts=PTS-STARTPTS+{s0:.3f}/TB,"
                  f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}[b{k}]")
        fc.append(f"{last}[b{k}]overlay=eof_action=pass:enable='between(t,{s0:.3f},{s1 + 0.05:.3f})'[o{k}]")
        last = f"[o{k}]"
    fc.append(f"{last}ass=captions.ass{fonts}[v]")
    af = f"loudnorm=I={a.lufs}:TP=-1.0:LRA=11,aresample=48000" if not a.no_loudnorm else "anull"
    fc.append(f"[0:a]{af}[a]")
    run(["ffmpeg", "-y", "-hide_banner", *inputs, "-filter_complex", ";".join(fc), "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-profile:v", "high", "-pix_fmt", "yuv420p",
         "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
         os.path.abspath(final)], cwd=wd)
    if not a.keep_temp:
        shutil.rmtree(segdir, ignore_errors=True)
        os.remove(joined)
    dur = probe(final)["duration"]
    print(f"Done → {final}  ({dur:.1f}s, {W}x{H}, style={a.style})")
    save(os.path.join(wd, "last_render.json"), {"final": os.path.abspath(final), "duration": dur})
    save(os.path.join(wd, "render_edl.json"), edl)


# --------------------------------------------------------------------------- preview


def cmd_preview(a):
    wd = workdir(a.video)
    lr = os.path.join(wd, "last_render.json")
    if not os.path.exists(lr):
        die("render first")
    final = load(lr)["final"]
    dur = probe(final)["duration"]
    edl = load(os.path.join(wd, "render_edl.json") if os.path.exists(os.path.join(wd, "render_edl.json"))
               else os.path.join(wd, "edl.json"))
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
        sp.add_argument("--max-pause", type=float, default=0.45, help="pauses longer than this get cut (s)")
        sp.add_argument("--pad-in", type=float, default=0.08)
        sp.add_argument("--pad-out", type=float, default=0.12)
        sp.add_argument("--noise-db", type=float, default=-35)
        sp.add_argument("--zooms", default="1.0,1.15", help="zoom cycle per shot (punch-ins hide jump cuts)")
        sp.add_argument("--max-shot", type=float, default=3.0,
                        help="switch zoom at least every N seconds within long takes (0 = off)")

    def r_args(sp):
        sp.add_argument("--style", choices=sorted(STYLES), default="podcast",
                        help="podcast (default, matches the reference reel) or bold (Hormozi)")
        sp.add_argument("--hook", default="", help="on-screen hook; use | to choose the line break")
        sp.add_argument("--hook-duration", type=float, default=None)
        sp.add_argument("--hook-y", type=int, default=None)
        sp.add_argument("--hook-size", type=int, default=None)
        sp.add_argument("--caption-y", type=int, default=None, help="caption centre y")
        sp.add_argument("--caption-size", type=int, default=None)
        sp.add_argument("--max-caption-chars", type=int, default=None)
        sp.add_argument("--words-per-caption", type=int, default=None)
        sp.add_argument("--highlight", default=None, help="active-word colour, or none")
        sp.add_argument("--accent", default=None, help="accent colour (hook line 2, lower-third)")
        sp.add_argument("--font", default=None)
        sp.add_argument("--uppercase", dest="uppercase", action="store_true", default=None)
        sp.add_argument("--no-uppercase", dest="uppercase", action="store_false")
        sp.add_argument("--no-captions", action="store_true")
        sp.add_argument("--lower-title", default="", help='lower-third title, e.g. "Podcast with Sha-En Yeo"')
        sp.add_argument("--lower-sub", default="", help="lower-third subtitle")
        sp.add_argument("--lower-start", type=float, default=4.0)
        sp.add_argument("--lower-duration", type=float, default=4.0)
        sp.add_argument("--lower-y", type=int, default=1335)
        sp.add_argument("--broll", default="", help="cutaways: w60-65=gym.mp4,L4=seminar.mov")
        sp.add_argument("--end-heading", default="", help='end card heading, e.g. "Full Episode:"')
        sp.add_argument("--end-handle", default="")
        sp.add_argument("--end-text", default="", help="end card title text")
        sp.add_argument("--end-cta", default="", help='e.g. Comment "SHAEN" for the full video')
        sp.add_argument("--end-image", default="", help="thumbnail image for the end card")
        sp.add_argument("--end-logo", default="", help="logo image (PNG with transparency)")
        sp.add_argument("--end-duration", type=float, default=4.5)
        sp.add_argument("--end-colors", default="#1F4FA0,#8A8F99", help="gradient top,bottom")
        sp.add_argument("--fit", choices=["auto", "crop", "pad"], default="auto",
                        help="crop to 9:16 or blurred-pad (auto: pad landscape, crop vertical)")
        sp.add_argument("--anchor", type=float, default=0.35, help="crop/zoom vertical anchor 0=top 1=bottom")
        sp.add_argument("--lufs", type=float, default=None)
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
