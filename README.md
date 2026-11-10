# video-to-hooks

Two ways to turn a talking-head video into Instagram content:

1. **`reel-edit` Claude Code skill (new, free, local)** — edits the raw clip into a finished,
   captioned 1080×1920 Reel *and* writes 10 hooks + the IG caption. See below.
2. **Web app** (`app/`) — upload a video, get hooks + caption (uses the OpenAI Whisper and Anthropic APIs).

Research behind the skill: [docs/claude-reel-editing-research.md](docs/claude-reel-editing-research.md).

## reel-edit skill — setup (2 steps, once)

1. Install ffmpeg and faster-whisper:
   ```bash
   # macOS
   brew install ffmpeg && pip3 install faster-whisper
   # Windows
   winget install ffmpeg && pip install faster-whisper
   # Ubuntu/Debian
   sudo apt install ffmpeg && pip install faster-whisper
   ```
2. Make the skill available everywhere (optional — it already works when Claude Code is opened in this repo):
   ```bash
   cp -r .claude/skills/reel-edit ~/.claude/skills/
   ```

## Use it

Open Claude Code and say:

> Edit ~/Movies/take1.mov into a reel

Claude will transcribe it, cut silences/ums/retakes, write hooks + caption to
`take1_reel/hooks.md`, render `take1_reel.mp4` with the best hook on screen, look at a preview
contact sheet to check captions sit outside Instagram's UI, and fix anything off.

You can also run the script directly:

```bash
python3 .claude/skills/reel-edit/scripts/reel.py auto take1.mov --hook "Most coaches undercharge by half"
```

What you get: 9:16 1080×1920 @30fps, jump cuts with alternating punch-in zoom, word-by-word
yellow-highlight captions placed above the bottom 35% Instagram covers, hook title for the first
3 s, audio normalised to −14 LUFS. No API keys; the first transcription downloads the Whisper
model (~500 MB) once.
