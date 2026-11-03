# video-to-hooks

Upload a video and get a transcript, 10 short-form text hooks, a top-3 pick with reasoning, and a ready-to-post caption.

## How it works

1. The browser decodes the video's audio, mixes it to 16 kHz mono, and splits it into WAV chunks of at most 3.5 MB (about 1m49s each), so every upload stays under Vercel's 4.5 MB request limit.
2. `/api/transcribe` sends each chunk to OpenAI Whisper.
3. `/api/generate` sends the joined transcript to Claude (`claude-sonnet-5-5`) with the hooks and caption prompt.

## Setup

```bash
npm install
cp .env.example .env.local   # then fill in both keys
npm run dev
```

Environment variables:

| Name | Used for |
| --- | --- |
| `ANTHROPIC_API_KEY` | Writing hooks and captions |
| `OPENAI_API_KEY` | Whisper transcription |

## Tests

```bash
npm test
```

The tests cover WAV encoding and chunking, server error handling, and reading Claude's response. They need no API keys.
