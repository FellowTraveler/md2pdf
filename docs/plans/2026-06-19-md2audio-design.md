# Create Audio Narration Design

## Goal

Add a "Create Audio Narration" Finder Quick Action that converts a Markdown file to an MP3 using ElevenLabs TTS (with macOS `say` as a local fallback). The user chooses narration mode and voice via a short dialog before processing begins.

## Architecture

**New files:**
- `md2audio` — Python script (polyglot shebang, runs in `~/.md2pdf-venv`)
- `Create Audio Narration.workflow` — Automator workflow triggering `md2audio`

**TTS providers (priority order):**
1. **ElevenLabs** — if `ELEVENLABS_API_KEY` is set. Chunks text at ~4,500 chars, calls `/v1/text-to-speech/{voice_id}`, concatenates MP3 chunks via ffmpeg.
2. **macOS `say`** — always-available fallback. `say -v <voice> -o output.aiff text`, then `ffmpeg` converts to MP3.

**Output:** `<filename>.mp3` saved next to the source `.md` file.

**Config keys** (in `~/.config/md2pdf/.env`):
- `ELEVENLABS_API_KEY` — existing key
- `ELEVENLABS_VOICE_ID` — default voice ID, set during install (default: David `0hh7H4ZVAtaGpm1VZyEN`)

---

## Install Script UX

After the ElevenLabs API key prompt, a new block appears (only if key is provided):

```
Audio Narration Voice (optional)
Select a default voice for 'Create Audio Narration':

   1) David       Deep, gravelly (Johnny Cash-like)  [default]
   2) Rachel      Calm, professional
   3) Adam        Masculine, American
   4) Antoni      Warm, conversational
   5) Josh        Young, energetic
   6) Bella       Soft, feminine
   7) Custom      Enter a voice ID manually

Select voice [1]:
```

Voice ID saved to `~/.config/md2pdf/.env` as `ELEVENLABS_VOICE_ID`. Skipped if no ElevenLabs key is configured.

---

## Runtime Dialog UX

Triggered by right-click `.md` file → Quick Actions → **Create Audio Narration**.

**Non-.md files:** immediately show `osascript display dialog` error:
> "Create Audio Narration only works with Markdown (.md) files."
Then exit.

**Dialog 1 — Mode** (`osascript choose from list`):
- Exact transcript — narrate the document word for word
- Summary narration — AI condenses to key points first (requires LLM key)

**Dialog 2 — Voice** (`osascript choose from list`):
- David (default) — Deep, gravelly
- Rachel — Calm, professional
- Adam — Masculine, American
- Antoni — Warm, conversational
- Josh — Young, energetic
- Bella — Soft, feminine
- macOS system voice — Local, no API key needed
- Search ElevenLabs… — Find any voice by name

If "Search ElevenLabs…": `display dialog` text input → call `/v1/voices/search` → show results in follow-up `choose from list`.

**Processing:** strip markdown formatting → (if Summary mode) call LLM to condense → chunk text → TTS → concatenate → save `.mp3`.

**Completion:** `osascript display notification "Saved: <filename>.mp3"`.

---

## ElevenLabs Voice IDs (curated list)

| Name   | Voice ID                       | Description              |
|--------|--------------------------------|--------------------------|
| David  | 0hh7H4ZVAtaGpm1VZyEN          | Deep, gravelly (default) |
| Rachel | 21m00Tcm4TlvDq8ikWAM          | Calm, professional       |
| Adam   | pNInz6obpgDQGcFmaJgB          | Masculine, American      |
| Antoni | ErXwobaYiN019PkySvjV          | Warm, conversational     |
| Josh   | TxGEqnHWrfWFTfGW9XjX          | Young, energetic         |
| Bella  | EXAVITQu4vr4xnSDxMaL          | Soft, feminine           |

---

## Error Handling

- No `.md` extension → error dialog, exit
- No `ELEVENLABS_API_KEY` and "Search ElevenLabs…" selected → error dialog
- ElevenLabs API error → fall back to macOS `say` with notification
- `ffmpeg` not found → error dialog with install instructions
- LLM key missing when Summary mode selected → error dialog suggesting Exact mode
- User cancels any dialog → exit silently

---

## Known Limitations

- macOS `say` voice quality is lower than ElevenLabs
- ElevenLabs chunking may produce slight pauses at chunk boundaries
- Summary narration quality depends on which LLM key is configured
- Cannot filter Quick Action to `.md` files only at the macOS level — script handles it at runtime
