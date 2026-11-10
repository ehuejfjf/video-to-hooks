# Claude video-editing skills for Instagram Reels — research (Nov 2026)

Goal: find the best Claude workflow for editing talking-head Instagram Reels that is **free**
(no paid APIs beyond a Claude plan), **easy to set up** (few steps), and has **few external
dependencies**.

## How they all work

Claude can't watch video. Every serious skill uses the same loop:

1. **Transcribe with word timestamps** (Whisper / faster-whisper / whisper.cpp / ElevenLabs Scribe / Groq).
2. **Claude edits the transcript** — removes silences, fillers, retakes, tangents — producing a cut list.
3. **ffmpeg renders** the cuts, 9:16 crop, captions, loudness.
4. **Claude checks frames** (contact sheets / timeline images) and iterates.

The differences come down to transcription cost, render engine (plain ffmpeg vs HyperFrames vs
Remotion, which need Node + headless Chrome) and how much motion-graphics polish they add.

## What's out there

| Skill | Reels focus | Paid key? | Extra deps beyond ffmpeg | Setup | Notes |
|---|---|---|---|---|---|
| [browser-use/video-use](https://github.com/browser-use/video-use) (~30k★, MIT) | general | **ElevenLabs (paid)** | Python env, optional HyperFrames/Remotion/Manim | ~4 steps | Best-known. Excellent cut rules (cut at ≥400 ms pauses, 30 ms audio fades, timeline PNG self-checks). Paid transcription is a deal-breaker for "free". |
| [tenfoldmarc/video-edit-skill](https://github.com/tenfoldmarc/video-edit-skill) | **IG reels** | no | Node 22, Python, matting model | ~3 | Best-take picking, text behind head, 3 looks, explicit IG safe zone (top 220 / bottom 450). No license file. |
| [artemnovitckii/claude-editing-skills](https://github.com/artemnovitckii/claude-editing-skills) | **IG reels** | Groq key (free tier) | Node 22, HyperFrames, RobustVideoMatting (GPL) | ~4 | 6 reel formats incl. `/trial-reels` (3 variants). macOS/Linux. |
| [yerinsabraham/video-edit-skill](https://github.com/yerinsabraham/video-edit-skill) | reels | no | whisper.cpp, Node 22, HyperFrames, MediaPipe | 2 (plugin) | Most polished QA (face clearance, safe zones). Heavy first-run install. |
| [Melvynx/video-agent-skills](https://github.com/Melvynx/video-agent-skills) | reels/shorts | no | Node, yt-dlp, Chrome, whisper.cpp, 0.6 GB engine | ~3 + 15 min setup | Full script→edit→publish pack; tied to a paid course. |
| [josemdasilvag-blip/reels-editor-skill](https://github.com/josemdasilvag-blip/reels-editor-skill) | reels | no | Node 20, HyperFrames 0.6.63 | ~5 | Spanish. Concrete numbers: pauses ≥0.55 s → 0.30 s, 1-word captions, safe zones top 250 / bottom 420. |
| [social-media-skills/video-editing-skill](https://github.com/social-media-skills/video-editing-skill) | YouTube-first | no | Python, Pillow, faster-whisper | ~3 | Punch-in 1.10–1.15×, −14 LUFS. Tied to WoopSocial. |
| [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) (~4.9k★) | generic + reels template | no | Python stdlib | ~3 | 42-tool ffmpeg toolbox / MCP server; you still assemble the workflow yourself. |
| [6missedcalls/video-editing-skill](https://github.com/6missedcalls/video-editing-skill) | generic | no | openai-whisper | ~3 | Bash; jump cut −30 dB / 0.5 s defaults; Hormozi caption style. No retakes, no safe zones. |
| [blazerior/videoediting-claude-skill](https://github.com/blazerior/videoediting-claude-skill) | vertical | no | faster-whisper, Chrome, ~4 GB | ~3 | Grading + HTML info cards. |
| [AgriciDaniel/claude-shorts](https://github.com/agricidaniel/claude-shorts) | long→short clips | no | Remotion | — | Clipping long videos, not editing a single take. |
| [digitalsamba/claude-code-video-toolkit](https://github.com/digitalsamba/claude-code-video-toolkit) | explainers | optional ElevenLabs | Remotion, Node | — | Generated videos, not talking-head editing. |
| [Remotion agent skills](https://remotion.dev/docs/ai/claude-code-plugin), [HeyGen HyperFrames](https://www.claudepluginhub.com/plugins/adam-s-tech-hyperframes) | motion graphics | no | Node 22, Chrome | — | Render engines other skills build on. |
| [video-db/skills](https://github.com/video-db/skills) | server-side | VideoDB account | — | — | Cloud processing. |
| DaVinci Resolve MCP servers ([example](https://github.com/samuelgursky/davinci-resolve-mcp)) | NLE control | no | Resolve running | config edit | Powerful but needs Resolve open and a project. |
| Others in [awesome-claude-video-skills](https://github.com/zhuyansen/awesome-claude-video-skills) (~180 repos): SeeCut, ghost-editor, cut-video, claude-youtube-editor, video-editor-agent (ElevenLabs)… | various | mostly no | mostly HyperFrames/Remotion | — | Same pattern; none independently benchmarked for reels quality. |

## Consensus best practices found

- **Cuts:** remove pauses > ~0.3 s (punchy) to 0.5 s (calm); pad 50–100 ms before / ~100 ms after words; 20–30 ms audio fades at every cut to avoid clicks; snap to word boundaries, never mid-word; Whisper word ends drift into silence → verify with an energy/silence detector.
- **Retakes:** keep the *last* clean take of a repeated line.
- **Jump cuts:** alternate punch-in zoom (1.0× ↔ 1.1–1.2×) per cut so cuts feel intentional.
- **Captions:** 1–3 words, bold, white with heavy outline, active word highlighted (yellow is the default everywhere), uppercase optional.
- **Safe zones (1080×1920):** IG overlays the bottom ~35 % (caption, username, audio), the top ~250 px and a right rail of ~120–140 px. Keep captions around y≈1000–1200, hook text around y≈300–500.
- **Hook:** on-screen text in the first 0.5–3 s that opens a loop; 15–30 s length is the safe default; Reels cap at 90 s.
- **Audio:** normalise to −14 LUFS, true peak −1.5 dB.
- **Self-check:** render a contact sheet with safe zones marked and have Claude look at it.

## Verdict: build our own lean skill

None of the published options hit all three constraints at once:

- the best-known one (video-use) needs a **paid** ElevenLabs key;
- the reel-specific ones (tenfoldmarc, artemnovitckii, yerinsabraham, Melvynx) pull in **Node 22 + HyperFrames/Remotion + headless Chrome + matting models**, which is the "lots of external stuff" we want to avoid;
- the lightweight ones (6missedcalls, kajisho5) lack retake removal, safe zones and the self-check loop.

So this repo ships **`.claude/skills/reel-edit/`**: one Python file + one SKILL.md that takes the
best-practice rules above and needs only **ffmpeg + `pip install faster-whisper`**. No API keys,
no Node, no browser, nothing to pay for beyond your Claude plan. It also reuses the existing
hooks-and-caption prompt from this app, so Claude writes 10 hooks + the IG caption for free
inside Claude Code instead of via the paid API.

What we deliberately skipped (possible later add-ons): text-behind-head (needs a matting model),
b-roll, music, animated motion graphics (HyperFrames/Remotion).

Caveat: star counts and details come from READMEs and aggregator pages fetched in Nov 2026; several
blog roundups (kapwing, sprites.ai, heyperai, dariusreed, novitckii.com) could not be fetched from
the research sandbox.
