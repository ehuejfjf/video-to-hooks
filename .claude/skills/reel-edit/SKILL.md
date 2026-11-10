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
5. **Cut redundancy:** sentences that restate the previous point in other words ("So you have
   been thinking you're stuck…" right after explaining it; "beliefs that hold you back" right after
   "limiting beliefs") go. Keep the clearest version once.
6. **Off-camera voices:** keep an interviewer's question only when it is the hook (e.g. a "client
   says" format); drop their follow-ups, chatter and the speaker asking the crew questions.
7. **Never cut mid-thought** so the meaning changes. Re-read the result for flow.

Then run the plan:

```bash
python3 SKILL_DIR/scripts/reel.py plan "VIDEO" --drop "L1,L4-L5,w120-126"
```

`--drop` accepts lines (`L3`, `L3-L6`) and word ranges (`w40-52`); look up exact word indices in
`words.json` when you need partial lines. Pacing knobs: `--max-pause 0.45` (pauses longer than
this are cut; 0.3 = punchier), `--max-shot 3` (zoom change at least every N s; 0 = off), `--zooms 1.0,1.15` (punch-in cycle
applied per shot — hides jump cuts; `1.0` disables), `--keep-fillers`.

Read the generated `edit.txt` (each kept segment with its text and duration) and check that the
story reads cleanly start to finish. Re-run `plan` with a different `--drop` until it does.

Whisper sometimes mishears words ("accompanying" for "occupying"). When the user points one out,
or a word looks wrong in context, fix it before rendering:
`python3 SKILL_DIR/scripts/reel.py fix "VIDEO" w265=occupying` (find the index in `words.json`).

## 3. Write hooks + caption

Follow `SKILL_DIR/reference/hooks-and-caption.md` (the creator's house prompt) and write the
result to `<video-name>_reel/hooks.md`: 10 text hooks, top 3 with reasoning, and the IG caption.
Base everything on what's actually said in the KEPT transcript.

Pick the on-screen hook. **House style (podcast):** a short, striking *direct quote* from the
speaker, in curly quotes and Title Case, split over two lines with `|` — line 1 renders white,
line 2 gold. Example from the reference reel: `“I Can Only Ask | For Help If I Pay”`.
Aim for 3–5 words per line (it auto-shrinks if long).

## 4. Render

```bash
python3 SKILL_DIR/scripts/reel.py render "VIDEO" --hook "“I Can Only Ask | For Help If I Pay”"
```

The default `--style podcast` was matched to the creator's reference reel (measured pixel by pixel):

- Montserrat Bold (bundled in `fonts/`), sentence-case white captions, 1–3 words, no punctuation,
  soft shadow, centred at y≈1310 just under the face; no word highlight.
- Hook: two black rounded boxes at the top (y≈234), white line + gold (`#F2C14E`) line, ~3.8 s.
- A zoom change at least every ~3 s (set in `plan --max-shot 3`), so a single camera feels like a
  multi-cam podcast edit; pauses up to 0.45 s are kept natural, longer ones cut.
- Audio normalised to −11 LUFS (loud, like the reference).

`--style cards` is the "explainer" look (matched to the Gratias reference): lowercase Poppins
captions (1–2 lines, brands/acronyms keep their case) plus full-screen **grid-paper cards** that
build key phrases word by word as they're spoken, with orange bold-italic emphasis. Captions
hide during text cards. Write a `cards.json` next to the video and pass `--cards cards.json`:

```json
[
 {"at": "w96-110",  "text": ["Not *stuck*", "# Stacked"]},
 {"at": "w139-163", "text": ["# Stacked:", "burdened by", "so many things", "in your *life*", "your *head*", "your *heart*"]},
 {"at": "w60-70",   "image": "ron_kaufman.jpg", "label": "Ron Kaufman"}
]
```

- `at`: the words (or `L<line>`) the card covers; the speaker's audio keeps playing.
- `# ` makes a big orange header line; `*word*` = orange bold-italic emphasis.
- Start each line with a word that is actually spoken so it appears in sync (otherwise lines
  appear evenly). Keep lines ≤ 22 characters.
- Use cards for definitions, numbered points, quotes and punchlines — about one per 10–15 s,
  1.5–8 s each. Photo cards (person/logo/screenshot) need an image from the user; never pull
  photos of people from the web.

`--style bold` gives the alternative Hormozi look (UPPERCASE, yellow word highlight, higher captions, −14 LUFS).

Optional extras (use them when the user provides the info/files):

| flag | what |
|---|---|
| `--lower-title "Podcast with Sha-En Yeo" --lower-sub "Singapore's First Happiness Scientist"` | gold-bar name card, 4–8 s (`--lower-start`, `--lower-duration`) |
| `--broll "w109-115=gym.mp4,L4=seminar.mov@1.5"` | full-screen cutaway while those words are spoken (speaker audio continues); `@1.5` starts 1.5 s into the clip. Pick moments where the words describe something visual ("mentors" → seminar, "too many priorities" → working with kid beside, "numbing your feelings" → ice bath). ~1 cutaway per 10 s, 1.5–3 s each. Make a contact sheet of each clip first and pick the offset where the subject is in frame. **Match the tone:** never put family/kids/pets (love, warmth) under negative lines (burdened, overwhelm, stuck); use solo/work/walking-alone shots there and save family + fun/action clips for positive or resolution moments |
| `--end-heading "Full Episode:" --end-handle "@MasterImplementers" --end-image thumb.jpg --end-text "Episode title" --end-cta 'Comment “SHAEN” for the full video'` | 4.5 s branded end card on a blue gradient (`--end-logo logo.png`, `--end-colors "#1F4FA0,#8A8F99"`) |
| `--caption-y 1200` / `--anchor 0.25` | captions hit the chin / zoom crops the head |
| `--fit pad` / `--fit crop` | landscape source: blurred background (auto default) vs fill-crop |
| `--accent "#00E5FF"` `--font "Name"` `--caption-size 80` | brand tweaks (drop extra .ttf files into `SKILL_DIR/fonts/`) |
| `--hook-duration 3` `--hook ""` `--no-captions` | timing / off-switches |
| `--out path.mp4` | custom output name |

## 5. Check your work visually (required)

```bash
python3 SKILL_DIR/scripts/reel.py preview "VIDEO"
```

Then **Read `<video-name>_reel/preview.jpg`** — a contact sheet of frames just after each cut, with
Instagram's UI zones tinted red. Verify:
- the hook stays outside the red zones; captions sit just under the face without covering the mouth
  (the house style deliberately puts captions at y≈1310, just inside the top of the bottom zone —
  that matches the reference, so don't "fix" it unless they collide with something);
- the punch-in zoom doesn't crop the top of the head (else lower `--anchor` or use `--zooms 1.0,1.08`);
- nothing looks broken (black frames, wrong orientation).

Fix with flags and re-render (render is fast; transcribe is never repeated). Up to 3 passes.

## 6. Deliver

Tell the user: the final file path, length (raw → final), what you cut and why (one line each
for retakes/tangents), and the path to `hooks.md`. Offer variations.

## Variations ("trial reels")

Instagram lets you test a reel on non-followers. Render the same edit with 3 different hooks:

```bash
python3 SKILL_DIR/scripts/reel.py render "VIDEO" --hook "“Quote A | Line Two”" --out "NAME_A.mp4"
python3 SKILL_DIR/scripts/reel.py render "VIDEO" --hook "“Quote B | Line Two”" --out "NAME_B.mp4"
python3 SKILL_DIR/scripts/reel.py render "VIDEO" --hook "HOOK C" --style bold --out "NAME_C.mp4"
```

## One-shot mode

`python3 SKILL_DIR/scripts/reel.py auto "VIDEO" --hook "..."` runs transcribe → plan (fillers +
pauses only, no retake removal) → render → preview. Use it only when the user wants a quick pass.

## Limits

- Claude can't watch video; decisions come from the transcript + preview frames. Retakes are
  detected from repeated words, not from facial expression.
- Whisper sometimes drops fillers silently; the silence detector still trims the gap around them.
- Single-camera talking-head clips work best. B-roll only when the user supplies clips; no music or SFX.
- Real camera-angle switches and guest cutaways need multiple source files (not supported yet).
