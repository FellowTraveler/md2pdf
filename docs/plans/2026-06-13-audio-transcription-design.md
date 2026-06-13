# Audio Transcription Quick Action Design

**Date:** 2026-06-13

## Overview

A new Finder right-click Quick Action — "Convert Audio File to Markdown Transcript" — that transcribes one or more selected audio files into `.md` files saved next to the originals.

## Capability Tiers

| Tier | Keys Required | Output |
|------|--------------|--------|
| Basic | None | Raw text (single speaker) or timestamped transcript (Whisper only) |
| Diarized | `HUGGINGFACE_TOKEN` | Per-speaker labeled segments + timestamps |
| Cloud | `ELEVENLABS_API_KEY` | ElevenLabs transcription (overrides local) |

Runtime tier is auto-detected by reading `~/.config/md2pdf/.env`.

## Components

### `Transcribe Audio to MD.workflow`
- New Automator workflow in repo root
- Accepts audio files: `.aac`, `.mp3`, `.m4a`, `.wav`, `.ogg`, `.flac`
- Calls `audio2md "$@"`
- `ShortcutInputClasses`: `WFGenericFileContentItem`
- Menu label: **Convert Audio File to Markdown Transcript**

### `audio2md`
- New Python script installed to `~/bin/`
- Loads `~/.config/md2pdf/.env` for API keys/tokens
- Installs into existing `~/.md2pdf-venv`
- Dependencies: `faster-whisper` (always), `pyannote.audio` (if HF token present)
- For each input file: writes `<basename>.md` next to the audio file

### Install Script Additions
- Installs `faster-whisper` into `~/.md2pdf-venv`
- Prompts for `HUGGINGFACE_TOKEN` (optional, for speaker diarization)
  - Explains: unlocks speaker identification in multi-person recordings
  - Link: https://huggingface.co/settings/tokens (free account required)
  - Also requires accepting pyannote model terms at: https://hf.co/pyannote/speaker-diarization-3.1
- Prompts for `ELEVENLABS_API_KEY` (optional, cloud alternative)
  - Explains: uses ElevenLabs cloud API instead of local models
  - Link: https://elevenlabs.io/app/settings/api-keys
- Appends non-empty values to `~/.config/md2pdf/.env`

## Output Format

### Single speaker detected (or Whisper-only with one speaker)
Pure raw text — no timestamps, no labels. Identical to iMessage voice transcription.

```markdown
# Transcript: signal-2026-06-13-023807.aac

**Date:** 2026-06-13
**Duration:** 4:32
**Transcribed by:** Whisper (large-v3)

---

So what I wanted to talk about today was the upcoming release. I think we need to move the date back by at least a week to give QA enough time.
```

### Multiple speakers detected (with diarization)
Per-speaker labeled segments with timestamps.

```markdown
# Transcript: signal-2026-06-13-023807.aac

**Date:** 2026-06-13
**Duration:** 4:32
**Transcribed by:** Whisper (large-v3) + speaker diarization

---

**[Speaker A]** `00:00:00`

So what I wanted to talk about today was the upcoming release.

**[Speaker B]** `00:00:08`

Right, and I think we need to move the date back.
```

### Timestamped (Whisper-only, multiple speakers but no diarization)
Inline timestamps, no speaker labels.

```markdown
# Transcript: signal-2026-06-13-023807.aac

**Date:** 2026-06-13
**Duration:** 4:32
**Transcribed by:** Whisper (large-v3)

---

`[00:00:00]` So what I wanted to talk about today was the upcoming release.

`[00:00:08]` Right, and I think we need to move the date back.
```

## Error Handling

- Unsupported file format → skip with warning to stderr
- Model download failure (no internet) → clear error message
- Invalid `HUGGINGFACE_TOKEN` → fall back to Whisper-only, note in output markdown
- Invalid `ELEVENLABS_API_KEY` → fall back to local Whisper with warning
- Output `.md` already exists → overwrite (user explicitly re-ran the action)
