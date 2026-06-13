# Audio Transcription Quick Action Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a "Convert Audio File to Markdown Transcript" Finder Quick Action that transcribes audio files to `.md` files saved alongside the originals.

**Architecture:** A new `audio2md` Python script (installed to `~/bin/`) reads `~/.config/md2pdf/.env` to detect which transcription tier is available (ElevenLabs > Whisper+pyannote > Whisper-only), then writes a `.md` file next to each audio file. A new Automator workflow wires it into Finder right-click. The install script adds `faster-whisper` to the existing venv and prompts for optional API keys.

**Tech Stack:** Python 3 / faster-whisper / pyannote.audio (optional) / ElevenLabs SDK (optional) / Automator .workflow / macOS Shortcuts

---

## Task 1: Create the `audio2md` script (Whisper-only tier)

**Files:**
- Create: `audio2md`

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""
audio2md — Transcribe audio files to Markdown.

Tier detection (highest available wins):
  ELEVENLABS_API_KEY  → ElevenLabs cloud (diarization built-in)
  HUGGINGFACE_TOKEN   → Whisper + pyannote speaker diarization
  (neither)           → Whisper only
"""
import os, sys, re, datetime, pathlib

CONFIG_ENV = pathlib.Path.home() / ".config" / "md2pdf" / ".env"
SUPPORTED = {".aac", ".mp3", ".m4a", ".wav", ".ogg", ".flac", ".opus", ".wma"}


def load_env():
    if CONFIG_ENV.exists():
        for line in CONFIG_ENV.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def fmt_duration(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_ts(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def whisper_transcribe(path, model_size="base"):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="auto", compute_type="auto")
    segments, info = model.transcribe(str(path), beam_size=5, word_timestamps=False)
    segs = list(segments)
    return segs, info.duration


def build_markdown_whisper_only(path, segments, duration):
    """Single-tier: no diarization — inline timestamps, or raw text if 1 segment."""
    filename = path.name
    date_str = datetime.date.today().isoformat()
    duration_str = fmt_duration(duration)
    model_size = os.environ.get("WHISPER_MODEL", "base")

    header = f"""# Transcript: {filename}

**Date:** {date_str}
**Duration:** {duration_str}
**Transcribed by:** Whisper ({model_size})

---

"""
    # Merge all text — if very short (single segment), output as raw prose
    lines = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        lines.append(f"`[{fmt_ts(seg.start)}]` {text}")

    return header + "\n\n".join(lines) + "\n"


def build_markdown_diarized(path, speaker_segments, duration, method):
    filename = path.name
    date_str = datetime.date.today().isoformat()
    duration_str = fmt_duration(duration)

    header = f"""# Transcript: {filename}

**Date:** {date_str}
**Duration:** {duration_str}
**Transcribed by:** {method}

---

"""
    speakers = {s for s, _, _, _ in speaker_segments}
    if len(speakers) <= 1:
        # Single speaker — pure raw text, no timestamps, no labels
        text = " ".join(t for _, _, _, t in speaker_segments if t.strip())
        return header + text + "\n"

    # Multiple speakers
    lines = []
    for speaker, start, end, text in speaker_segments:
        text = text.strip()
        if not text:
            continue
        lines.append(f"**[{speaker}]** `{fmt_ts(start)}`\n\n{text}")

    return header + "\n\n".join(lines) + "\n"


def transcribe_elevenlabs(path):
    from elevenlabs.client import ElevenLabs
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    client = ElevenLabs(api_key=api_key)
    with open(path, "rb") as f:
        result = client.speech_to_text.convert(
            file=f,
            model_id="scribe_v1",
            diarize=True,
            timestamps_granularity="segment",
        )
    # Build (speaker, start, end, text) tuples from result.words
    segments = []
    current_speaker, current_start, current_end, current_text = None, 0, 0, ""
    for word in result.words:
        spk = getattr(word, "speaker_id", None) or "Speaker A"
        if spk != current_speaker:
            if current_text.strip():
                segments.append((current_speaker, current_start, current_end, current_text.strip()))
            current_speaker, current_start, current_end, current_text = spk, word.start, word.end, word.text
        else:
            current_end = word.end
            current_text += " " + word.text
    if current_text.strip():
        segments.append((current_speaker, current_start, current_end, current_text.strip()))
    duration = result.words[-1].end if result.words else 0
    return segments, duration


def transcribe_whisper_pyannote(path):
    import torch
    from faster_whisper import WhisperModel
    from pyannote.audio import Pipeline

    hf_token = os.environ.get("HUGGINGFACE_TOKEN")
    model_size = os.environ.get("WHISPER_MODEL", "base")

    model = WhisperModel(model_size, device="auto", compute_type="auto")
    whisper_segs, duration = model.transcribe(str(path), beam_size=5, word_timestamps=True)
    whisper_segs = list(whisper_segs)

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )
    diarization = pipeline(str(path))

    # Map each Whisper word to a speaker via diarization timeline
    def speaker_at(t):
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            if turn.start <= t <= turn.end:
                return speaker
        return "Speaker A"

    # Group words into speaker-contiguous segments
    segments = []
    cur_spk, cur_start, cur_end, cur_text = None, 0, 0, ""
    for seg in whisper_segs:
        for word in (seg.words or []):
            mid = (word.start + word.end) / 2
            spk = speaker_at(mid)
            if spk != cur_spk:
                if cur_text.strip():
                    segments.append((cur_spk, cur_start, cur_end, cur_text.strip()))
                cur_spk, cur_start, cur_end, cur_text = spk, word.start, word.end, word.text
            else:
                cur_end = word.end
                cur_text += " " + word.text
    if cur_text.strip():
        segments.append((cur_spk, cur_start, cur_end, cur_text.strip()))

    return segments, duration


def process_file(path):
    path = pathlib.Path(path)
    if path.suffix.lower() not in SUPPORTED:
        print(f"Skipping (unsupported format): {path.name}", file=sys.stderr)
        return

    out_path = path.with_suffix(".md")
    print(f"Transcribing: {path.name} -> {out_path.name}", file=sys.stderr)

    el_key = os.environ.get("ELEVENLABS_API_KEY")
    hf_token = os.environ.get("HUGGINGFACE_TOKEN")

    try:
        if el_key:
            segments, duration = transcribe_elevenlabs(path)
            md = build_markdown_diarized(path, segments, duration, "ElevenLabs (scribe_v1)")
        elif hf_token:
            try:
                segments, duration = transcribe_whisper_pyannote(path)
                model_size = os.environ.get("WHISPER_MODEL", "base")
                md = build_markdown_diarized(path, segments, duration,
                                             f"Whisper ({model_size}) + speaker diarization")
            except Exception as e:
                print(f"Warning: diarization failed ({e}), falling back to Whisper-only", file=sys.stderr)
                segs, duration = whisper_transcribe(path)
                md = build_markdown_whisper_only(path, segs, duration)
        else:
            segs, duration = whisper_transcribe(path)
            md = build_markdown_whisper_only(path, segs, duration)
    except Exception as e:
        print(f"Error transcribing {path.name}: {e}", file=sys.stderr)
        sys.exit(1)

    out_path.write_text(md, encoding="utf-8")
    print(f"Saved: {out_path}", file=sys.stderr)


def main():
    if len(sys.argv) < 2:
        print("Usage: audio2md <file1> [file2 ...]", file=sys.stderr)
        sys.exit(1)
    load_env()
    for arg in sys.argv[1:]:
        process_file(arg)


if __name__ == "__main__":
    main()
```

**Step 2: Make executable and install**

```bash
chmod +x audio2md
cp audio2md ~/bin/audio2md
```

**Step 3: Manual smoke test (Whisper-only)**

```bash
~/bin/audio2md /Users/au/src/Tranquilo/records/signal-2026-06-13-013859.aac
```

Expected: A `.md` file appears next to the `.aac` file. It should contain a header with filename/date/duration and timestamped transcript lines.

**Step 4: Commit**

```bash
git add audio2md
git commit -m "Add audio2md transcription script (Whisper-only tier)"
```

---

## Task 2: Create the Automator workflow

The workflow is a directory with two files. Model it exactly on `Convert MD to PDF.workflow`.

**Files:**
- Create: `Transcribe Audio to MD.workflow/Contents/document.wflow`
- Create: `Transcribe Audio to MD.workflow/Contents/Info.plist`

**Step 1: Create the directory structure**

```bash
mkdir -p "Transcribe Audio to MD.workflow/Contents"
```

**Step 2: Create `Info.plist`**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleIdentifier</key>
	<string>com.apple.automator.transcribe-audio-to-md</string>
	<key>CFBundleName</key>
	<string>Convert Audio File to Markdown Transcript</string>
	<key>CFBundleVersion</key>
	<string>1</string>
	<key>NSServices</key>
	<array>
		<dict>
			<key>NSMenuItem</key>
			<dict>
				<key>default</key>
				<string>Convert Audio File to Markdown Transcript</string>
			</dict>
			<key>NSMessage</key>
			<string>runWorkflowAsService</string>
			<key>NSPortName</key>
			<string>Convert Audio File to Markdown Transcript</string>
			<key>NSRequiredContext</key>
			<dict>
				<key>NSApplicationIdentifier</key>
				<string>com.apple.finder</string>
			</dict>
			<key>NSSendTypes</key>
			<array>
				<string>NSFilenamesPboardType</string>
			</array>
		</dict>
	</array>
	<key>ShortcutInputClasses</key>
	<array>
		<string>WFGenericFileContentItem</string>
	</array>
</dict>
</plist>
```

**Step 3: Create `document.wflow`**

Copy `Convert MD to PDF.workflow/Contents/document.wflow` as a base:

```bash
cp "Convert MD to PDF.workflow/Contents/document.wflow" \
   "Transcribe Audio to MD.workflow/Contents/document.wflow"
```

Then open it and replace the `COMMAND_STRING` value with:

```
export PATH="$HOME/bin:/opt/homebrew/bin:$PATH"
audio2md "$@"
```

Use PlistBuddy to set it (avoids XML editing mistakes):

```bash
/usr/libexec/PlistBuddy -c \
  'Set :actions:0:action:ActionParameters:COMMAND_STRING export PATH="$HOME/bin:/opt/homebrew/bin:$PATH"\naudio2md "$@"' \
  "Transcribe Audio to MD.workflow/Contents/document.wflow"
```

Also update the bundle name in `document.wflow` to avoid collision with the MD-to-PDF workflow. Use PlistBuddy to set `:workflowMetaData:serviceInputTypeIdentifier` to `com.apple.automator.fileSystemObject.item` (accepts files).

**Step 4: Install and test in Finder**

```bash
cp -R "Transcribe Audio to MD.workflow" \
      ~/Library/Services/"Transcribe Audio to MD.workflow"
```

Restart Finder:
```bash
killall pbs 2>/dev/null || true; sleep 1; killall Finder
```

Right-click one of the `.aac` files in Finder and verify "Convert Audio File to Markdown Transcript" appears in Quick Actions (or Services submenu).

**Step 5: Commit**

```bash
git add "Transcribe Audio to MD.workflow/"
git commit -m "Add Transcribe Audio to MD Automator workflow"
```

---

## Task 3: Update `install.sh`

**Files:**
- Modify: `install.sh`

Make three additions to `install.sh`:

**Step 1: Add `faster-whisper` to venv pip install line (~line 46)**

Change:
```bash
    "$HOME/.md2pdf-venv/bin/pip" install --quiet --upgrade \
        pymupdf4llm pytesseract Pillow anthropic openai
```

To:
```bash
    "$HOME/.md2pdf-venv/bin/pip" install --quiet --upgrade \
        pymupdf4llm pytesseract Pillow anthropic openai faster-whisper
```

**Step 2: Add `audio2md` install after the `pdf2md` install block**

Find where `pdf2md` is installed (look for `cp "$SCRIPT_DIR/pdf2md"`). After that block, add:

```bash
# Install audio2md
echo -e "${BLUE}Installing:${NC} audio2md -> $INSTALL_BIN/audio2md"
cp "$SCRIPT_DIR/audio2md" "$INSTALL_BIN/audio2md"
chmod +x "$INSTALL_BIN/audio2md"
```

**Step 3: Add API key prompts after the venv setup block (~line 48)**

After the `echo ""` that follows the pip install, add:

```bash
    # --- Audio transcription keys (optional) ---
    echo -e "${BOLD}Audio Transcription (optional — for 'Convert Audio File to Markdown Transcript')${NC}"
    echo ""
    echo "  Without any keys: transcription runs locally via Whisper (raw timestamped text)."
    echo ""
    echo "  HUGGINGFACE_TOKEN — unlocks speaker identification (who said what)."
    echo "    Get a free token at: https://huggingface.co/settings/tokens"
    echo "    Then accept model terms at: https://huggingface.co/pyannote/speaker-diarization-3.1"
    echo "    (Requires accepting terms while logged in to HuggingFace)"
    echo ""
    read -p "  HuggingFace token (press Enter to skip): " _HF_TOKEN
    echo ""
    echo "  ELEVENLABS_API_KEY — use ElevenLabs cloud instead of local models."
    echo "    (Optional; costs per minute of audio. Get a key at: https://elevenlabs.io/app/settings/api-keys)"
    echo ""
    read -p "  ElevenLabs API key (press Enter to skip): " _EL_KEY
    echo ""

    # Write non-empty keys to ~/.config/md2pdf/.env
    mkdir -p "$HOME/.config/md2pdf"
    touch "$HOME/.config/md2pdf/.env"
    if [[ -n "$_HF_TOKEN" ]]; then
        # Remove existing line if present, then append
        sed -i '' '/^HUGGINGFACE_TOKEN=/d' "$HOME/.config/md2pdf/.env" 2>/dev/null || true
        echo "HUGGINGFACE_TOKEN=${_HF_TOKEN}" >> "$HOME/.config/md2pdf/.env"
        echo -e "${GREEN}Saved:${NC} HUGGINGFACE_TOKEN"
        # Install pyannote for diarization
        echo -e "${BLUE}Installing:${NC} pyannote.audio (speaker diarization)"
        "$HOME/.md2pdf-venv/bin/pip" install --quiet pyannote.audio
        echo ""
    fi
    if [[ -n "$_EL_KEY" ]]; then
        sed -i '' '/^ELEVENLABS_API_KEY=/d' "$HOME/.config/md2pdf/.env" 2>/dev/null || true
        echo "ELEVENLABS_API_KEY=${_EL_KEY}" >> "$HOME/.config/md2pdf/.env"
        echo -e "${GREEN}Saved:${NC} ELEVENLABS_API_KEY"
        "$HOME/.md2pdf-venv/bin/pip" install --quiet elevenlabs
        echo ""
    fi
    echo ""
```

**Step 4: Verify the install script runs without error (dry-run the relevant section)**

```bash
bash -n install.sh
```

Expected: no syntax errors.

**Step 5: Commit**

```bash
git add install.sh
git commit -m "Update install.sh: add audio2md install and API key prompts"
```

---

## Task 4: Fix the `audio2md` shebang to use the venv Python

The script must use `~/.md2pdf-venv/bin/python3` (where `faster-whisper` is installed), not the system Python. Since `~/bin/audio2md` is called from Automator (no shell profile loaded), the shebang must be an absolute path.

**Files:**
- Modify: `audio2md` (line 1)

**Step 1: Update shebang**

Change line 1 from:
```python
#!/usr/bin/env python3
```
To:
```python
#!/bin/bash
# -*- mode: python -*-
''':'
exec "$HOME/.md2pdf-venv/bin/python3" "$0" "$@"
'''
```

This bash/python polyglot trick works reliably from Automator: bash executes the `exec` which re-invokes the same file under the venv Python.

**Step 2: Re-install**

```bash
cp audio2md ~/bin/audio2md && chmod +x ~/bin/audio2md
```

**Step 3: Verify it runs without `faster-whisper` import errors**

```bash
~/bin/audio2md /Users/au/src/Tranquilo/records/signal-2026-06-13-013859.aac
```

Expected: transcription runs (may take 30-120s on first run while model downloads), `.md` file created next to audio file.

**Step 4: Commit**

```bash
git add audio2md
git commit -m "Fix audio2md shebang to use venv Python (required for Automator)"
```

---

## Task 5: Transcribe the four test audio files

**Step 1: Run on all four files**

```bash
~/bin/audio2md \
  /Users/au/src/Tranquilo/records/signal-2026-06-13-023807.aac \
  /Users/au/src/Tranquilo/records/signal-2026-06-13-014105.aac \
  /Users/au/src/Tranquilo/records/signal-2026-06-13-013955.aac \
  /Users/au/src/Tranquilo/records/signal-2026-06-13-013859.aac
```

**Step 2: Inspect the output**

```bash
cat /Users/au/src/Tranquilo/records/signal-2026-06-13-013859.md
```

Verify: header present, transcript text populated, timestamps formatted correctly.

**Step 3: No commit needed** — these output `.md` files are not tracked in the md2pdf repo.

---

## Task 6: Update `README.md`

**Files:**
- Modify: `README.md`

Add a new section describing the audio transcription Quick Action. It should cover:

1. What the action does
2. The three tiers (no keys / HuggingFace / ElevenLabs) with what each unlocks
3. How to get a HuggingFace token and accept pyannote model terms
4. How to get an ElevenLabs API key
5. How to set keys after install: `~/.config/md2pdf/.env`
6. Supported audio formats

Add the section after the existing "Convert PDF to Markdown" section, before "Installation".

**Step 1: Add the section**

Find the README location to insert after (e.g., after the pdf2md section header), then insert:

```markdown
## Convert Audio File to Markdown Transcript

Right-click any audio file in Finder → Quick Actions → **Convert Audio File to Markdown Transcript**

Transcribes the audio and saves a `.md` file with the same name next to the original. Select multiple files to batch-transcribe.

### Output quality tiers

| What you have | Output |
|---|---|
| Nothing (default) | Timestamped raw transcript via local Whisper |
| `HUGGINGFACE_TOKEN` | Per-speaker labeled transcript (who said what) |
| `ELEVENLABS_API_KEY` | Cloud transcription via ElevenLabs (overrides local) |

Single-speaker recordings always produce clean raw text with no timestamps or labels.

### Supported formats

`.aac`, `.mp3`, `.m4a`, `.wav`, `.ogg`, `.flac`, `.opus`, `.wma`

### Setting up speaker identification (optional)

1. Create a free account at [huggingface.co](https://huggingface.co)
2. Generate a token at <https://huggingface.co/settings/tokens>
3. Accept the model terms at <https://huggingface.co/pyannote/speaker-diarization-3.1> (while signed in)
4. Add to `~/.config/md2pdf/.env`:
   ```
   HUGGINGFACE_TOKEN=hf_your_token_here
   ```

### Setting up ElevenLabs cloud transcription (optional)

1. Create an account at [elevenlabs.io](https://elevenlabs.io)
2. Get your API key at <https://elevenlabs.io/app/settings/api-keys>
3. Add to `~/.config/md2pdf/.env`:
   ```
   ELEVENLABS_API_KEY=sk_your_key_here
   ```

When `ELEVENLABS_API_KEY` is set, it takes priority over local Whisper for all transcriptions.
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "Update README: document audio transcription Quick Action"
```

---

## Task 7: Final verification

**Step 1: Test the Finder Quick Action end-to-end**

1. Open Finder and navigate to `/Users/au/src/Tranquilo/records/`
2. Right-click `signal-2026-06-13-013859.aac`
3. Hover "Quick Actions" — verify "Convert Audio File to Markdown Transcript" appears
4. Click it
5. Verify `signal-2026-06-13-013859.md` is created/updated next to the file

**Step 2: Verify the output reads correctly**

```bash
cat /Users/au/src/Tranquilo/records/signal-2026-06-13-013859.md
```

**Step 3: Confirm `install.sh` syntax is clean**

```bash
bash -n install.sh && echo "OK"
```
