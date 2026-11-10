---
name: reel-edit
description: Edit a raw talking-head clip into a finished, captioned 1080x1920 Instagram Reel — cuts silences, ums and retakes, adds punch-in zooms, word-by-word highlighted captions, an on-screen hook, loudness normalisation, plus 10 hooks and an IG caption. Free and local (ffmpeg + faster-whisper, no API keys). Use when the user asks to edit / cut / caption a reel, short, TikTok or talking-head video, or drops a video file and says "make this a reel".
---

# Reel Edit

Turns a phone-shot talking-head clip into a post-ready Instagram Reel. You (Claude) make the
editorial decisions; `scripts/reel.py` does the mechanical work with ffmpeg.

Script path (use it verbatim): `SKILL_DIR/scripts/reel.py` where `SKILL_DIR` is the folder
containing this file. Everything it produces goes into `<video-name>_reel/` next to the video,
and the final file is `<video-name>_reel.mp4`.
On Windows use `python` instead of `python3`.

## 0. Setup check (first time only)

```bash
ffmpeg -version | head -1 && python3 -c "import faster_whisper" && echo OK
```

If something is missing, tell the user the one command they need:
- ffmpeg — macOS `brew install ffmpeg` · Windows `winget install ffmpeg` · Linux `sudo apt install ffmpeg`
- faster-whisper — `pip install faster-whisper` (first transcription downloads a ~500 MB model once, then runs offline)

## 1. Transcribe

```bash
python3 SKILL_DIR/scripts/reel.py transcribe "VIDEO"
```

Options: `--model small` (default; `medium` is more accurate but slower, `base` is faster),
`--language en` to skip detection. Produces `words.json` (word timestamps) and
`transcript.txt`, numbered by line and word:

```
L3   w40-58 [ 12.10- 17.80] Most coaches charge too little because they...
```
Words marked `*` are fillers (um/uh) and are cut automatically.

## 2. Decide the cut (this is the editing — do it carefully)

Read `transcript.txt` and choose what to remove. Rules a good short-form editor follows:

1. **Retakes:** when a sentence is said more than once, keep the LAST complete, clean take and
   drop the earlier ones (people restart because they flubbed it). Watch for partial restarts
   inside a line (e.g. "the thing is— the thing is") and drop the broken words with `w` ranges.
2. **Dead intro/outro:** drop "okay is it recording", "let me start again", throat clears,
   "yeah so...", trailing "...and yeah", "cool, cut".
3. **Start strong:** the first spoken line should be the most gripping claim. If the best hook
   line is buried later, that's fine — the on-screen hook (step 4) carries the first 3 s — but
   cut any warm-up before the first real sentence.
4. **One idea per reel.** Tangents that don't serve the main point go. Target 15–45 s; hard cap 90 s.
5. **Never cut mid-thought** so the meaning changes. Re-read the result for flow.

Then run the plan:

```bash
python3 SKILL_DIR/scripts/reel.py plan "VIDEO" --drop "L1,L4-L5,w120-126"
```

`--drop` accepts lines (`L3`, `L3-L6`) and word ranges (`w40-52`); look up exact word indices in
`words.json` when you need partial lines. Pacing knobs: `--max-pause 0.30` (pauses longer than
this are cut; use 0.2 for very punchy, 0.45 for calmer), `--zooms 1.0,1.12` (punch-in cycle
applied per cut — hides jump cuts; `1.0` disables), `--keep-fillers`.

Read the generated `edit.txt` (each kept segment with its text and duration) and check that the
story reads cleanly start to finish. Re-run `plan` with a different `--drop` until it does.

## 3. Write hooks + caption

Follow `SKILL_DIR/reference/hooks-and-caption.md` (the creator's house prompt) and write the
result to `<video-name>_reel/hooks.md`: 10 text hooks, top 3 with reasoning, and the IG caption.
Base everything on what's actually said in the KEPT transcript.

Pick the strongest hook for the on-screen title: ≤ 10 words, readable in under 2 seconds.

## 4. Render

```bash
python3 SKILL_DIR/scripts/reel.py render "VIDEO" --hook "Your best hook here"
```

Defaults are tuned for Instagram: 1080x1920 @30fps, H.264 + AAC, −14 LUFS, captions centred at
y=1130 (above the bottom 35% IG covers with UI), hook title at the top for 3 s, word-by-word
yellow highlight, 1–3 words per caption, uppercase. Useful flags:

| flag | when |
|---|---|
| `--caption-y 1000` | captions collide with chin/hands — move up (keep < 1248) |
| `--anchor 0.25` | face is high in frame, crop/zoom keeps cutting the head (0 = top, 1 = bottom) |
| `--fit pad` / `--fit crop` | landscape source: blurred background (auto default) vs fill-crop |
| `--highlight "#00E5FF"` `--font "Montserrat"` | brand colours / font (drop .ttf files into `SKILL_DIR/fonts/`) |
| `--words-per-caption 2` `--caption-size 90` | punchier/larger captions |
| `--no-uppercase` `--no-captions` `--hook ""` | style off-switches |
| `--hook-duration 2.5` | hook on screen shorter/longer |
| `--out path.mp4` | custom output name |

## 5. Check your work visually (required)

```bash
python3 SKILL_DIR/scripts/reel.py preview "VIDEO"
```

Then **Read `<video-name>_reel/preview.jpg`** — a contact sheet of frames just after each cut, with
Instagram's UI zones tinted red. Verify:
- captions and the hook sit outside the red zones and don't cover the mouth/eyes;
- the punch-in zoom doesn't crop the top of the head (else lower `--anchor` or use `--zooms 1.0,1.08`);
- nothing looks broken (black frames, wrong orientation).

Fix with flags and re-render (render is fast; transcribe is never repeated). Up to 3 passes.

## 6. Deliver

Tell the user: the final file path, length (raw → final), what you cut and why (one line each
for retakes/tangents), and the path to `hooks.md`. Offer variations.

## Variations ("trial reels")

Instagram lets you test a reel on non-followers. Render the same edit with 3 different hooks:

```bash
python3 SKILL_DIR/scripts/reel.py render "VIDEO" --hook "Hook A" --out "NAME_A.mp4"
python3 SKILL_DIR/scripts/reel.py render "VIDEO" --hook "Hook B" --highlight "#00E5FF" --out "NAME_B.mp4"
python3 SKILL_DIR/scripts/reel.py render "VIDEO" --hook "Hook C" --words-per-caption 1 --out "NAME_C.mp4"
```

## One-shot mode

`python3 SKILL_DIR/scripts/reel.py auto "VIDEO" --hook "..."` runs transcribe → plan (fillers +
pauses only, no retake removal) → render → preview. Use it only when the user wants a quick pass.

## Limits

- Claude can't watch video; decisions come from the transcript + preview frames. Retakes are
  detected from repeated words, not from facial expression.
- Whisper sometimes drops fillers silently; the silence detector still trims the gap around them.
- Single-speaker talking-head clips work best. No b-roll, music or sound effects are added.
