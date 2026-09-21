#!/usr/bin/env bash
#
# md2pdf & pdf2md installer
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_BIN="${HOME}/bin"
THEME_DIR="${HOME}/.md2pdf-themes"
# Automator input type of services that take no input (run from any app via hotkey)
NO_INPUT_TYPE="com.apple.Automator.nothing"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BOLD}md2pdf & pdf2md Installer${NC}"
echo ""

# If already installed, uninstall first to avoid conflicts
if [[ -f "$INSTALL_BIN/md2pdf" || -d "${HOME}/Library/Services/Convert MD to PDF.workflow" ]]; then
    echo -e "${YELLOW}Existing installation detected — running uninstall first.${NC}"
    echo ""
    bash "$SCRIPT_DIR/uninstall.sh"
    echo ""
fi

workflow_input_type() {  # workflow_input_type /path/to/Some.workflow
    /usr/libexec/PlistBuddy -c "Print :workflowMetaData:serviceInputTypeIdentifier" \
        "$1/Contents/document.wflow" 2>/dev/null || true
}

# ── Phase 1: Quick Action selection ─────────────────────────────────────────

# Check iCloud/Shortcuts availability upfront
_CAN_SIGN=false
if command -v shortcuts &> /dev/null; then
    _PROBE_TMP=$(mktemp /tmp/probe.XXXXXX.shortcut)
    printf '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict/></plist>\n' \
        | plutil -convert binary1 - -o "$_PROBE_TMP" 2>/dev/null
    _SIGN_ERR=$(shortcuts sign -m anyone -i "$_PROBE_TMP" -o /dev/null 2>&1 || true)
    rm -f "$_PROBE_TMP"
    echo "$_SIGN_ERR" | grep -qi "icloud" || _CAN_SIGN=true
fi

SERVICES_DIR="${HOME}/Library/Services"

echo -e "${BOLD}Quick Actions${NC}"
echo "These appear when you right-click a file or folder in Finder."
echo ""

QA_NAMES=()
QA_PATHS=()
i=1
for workflow in "$SCRIPT_DIR/"*.workflow; do
    [[ -d "$workflow" ]] || continue
    wf_display="$(basename "$workflow" .workflow)"
    already=""
    [[ -d "$SERVICES_DIR/$(basename "$workflow")" ]] && already=" (already installed)"
    [[ "$(workflow_input_type "$workflow")" == "$NO_INPUT_TYPE" ]] && wf_display="$wf_display [any app — hotkey]"
    printf "  %2d) %s%s\n" "$i" "$wf_display" "$already"
    QA_NAMES+=("$(basename "$workflow")")
    QA_PATHS+=("$workflow")
    i=$((i + 1))
done

echo ""
QA_SELECTED=()
if [ -t 0 ]; then
    echo "Enter numbers to install (e.g., 1 3 7), 'all', or 'none' to skip:"
    read -p "> " qa_selection
    case "$qa_selection" in
        none|"") ;;
        all)     QA_SELECTED=($(seq 1 ${#QA_NAMES[@]})) ;;
        *)       QA_SELECTED=($qa_selection) ;;
    esac
fi

# Determine which AI features the selected workflows require
_need_llm=false
_need_elevenlabs=false
_need_huggingface=false
_need_voice=false
_need_qr=false

for num in "${QA_SELECTED[@]}"; do
    idx=$((num - 1))
    [[ $idx -lt 0 || $idx -ge ${#QA_NAMES[@]} ]] && continue
    case "${QA_NAMES[$idx]}" in
        "Convert PDF to MD.workflow")
            _need_llm=true ;;
        "Create Audio Narration.workflow")
            _need_llm=true; _need_elevenlabs=true; _need_voice=true ;;
        "Transcribe Audio to MD.workflow")
            _need_elevenlabs=true; _need_huggingface=true ;;
        "Decode QR Code On Screen.workflow")
            _need_qr=true ;;
    esac
done

# ── Phase 2: API key prompts (only for needed features) ──────────────────────

_LLM_PROVIDER=""
_LLM_KEY=""
_HF_TOKEN=""
_EL_KEY=""
_VOICE_ID=""

mkdir -p "$HOME/.config/md2pdf"
touch "$HOME/.config/md2pdf/.env"

save_key() {  # save_key KEY value
    sed -i '' "/^${1}=/d" "$HOME/.config/md2pdf/.env" 2>/dev/null || true
    echo "${1}=${2}" >> "$HOME/.config/md2pdf/.env"
    echo -e "${GREEN}Saved:${NC} ${1} -> ~/.config/md2pdf/.env"
}

if [ -t 0 ]; then

    # LLM provider — used by pdf2md (OCR enhancement) and md2audio (text preprocessing)
    if [[ "$_need_llm" == "true" ]]; then
        echo ""
        echo -e "${BOLD}AI Language Model (optional)${NC}"
        echo "Enhances PDF text recovery and audio narration preprocessing."
        echo ""
        echo "  1) Anthropic (Claude)  https://console.anthropic.com/settings/keys"
        echo "  2) OpenAI (GPT-4o)    https://platform.openai.com/api-keys"
        echo "  3) Skip"
        echo ""
        read -p "  Choose provider [3]: " _LLM_CHOICE
        _LLM_CHOICE="${_LLM_CHOICE:-3}"
        case "$_LLM_CHOICE" in
            1)
                _LLM_PROVIDER="anthropic"
                read -p "  Anthropic API key: " _LLM_KEY
                [[ -n "$_LLM_KEY" ]] && save_key ANTHROPIC_API_KEY "$_LLM_KEY"
                ;;
            2)
                _LLM_PROVIDER="openai"
                read -p "  OpenAI API key: " _LLM_KEY
                [[ -n "$_LLM_KEY" ]] && save_key OPENAI_API_KEY "$_LLM_KEY"
                ;;
        esac
        echo ""
    fi

    if [[ "$_need_huggingface" == "true" ]]; then
        echo -e "\n${BOLD}Speaker Identification (optional)${NC}"
        echo "Identifies who is speaking. Free account at https://huggingface.co — get a token"
        echo "at /settings/tokens and accept terms at /pyannote/speaker-diarization-3.1"
        read -p "  HuggingFace token (press Enter to skip): " _HF_TOKEN
        [[ -n "$_HF_TOKEN" ]] && save_key HUGGINGFACE_TOKEN "$_HF_TOKEN"
        echo ""
    fi

    if [[ "$_need_elevenlabs" == "true" ]]; then
        [[ "$_need_voice" == "true" ]] \
            && echo -e "\n${BOLD}ElevenLabs (required for audio narration)${NC}" \
            || echo -e "\n${BOLD}ElevenLabs (optional — enables cloud transcription)${NC}"
        read -p "  Key from https://elevenlabs.io/app/settings/api-keys (Enter to skip): " _EL_KEY
        [[ -n "$_EL_KEY" ]] && save_key ELEVENLABS_API_KEY "$_EL_KEY"
        echo ""
    fi

    _EL_KEY_ACTIVE="${_EL_KEY:-$(grep '^ELEVENLABS_API_KEY=' "$HOME/.config/md2pdf/.env" 2>/dev/null | cut -d= -f2-)}"
    if [[ "$_need_voice" == "true" && -n "$_EL_KEY_ACTIVE" ]]; then
        echo -e "${BOLD}Audio Narration Voice${NC}"
        echo "  1) David (default)  2) Rachel  3) Adam  4) Antoni  5) Josh  6) Bella  7) Custom"
        read -p "  Select voice [1]: " _VOICE_CHOICE
        case "${_VOICE_CHOICE:-1}" in
            1) _VOICE_ID="0hh7H4ZVAtaGpm1VZyEN" ;;
            2) _VOICE_ID="21m00Tcm4TlvDq8ikWAM" ;;
            3) _VOICE_ID="pNInz6obpgDQGcFmaJgB" ;;
            4) _VOICE_ID="ErXwobaYiN019PkySvjV" ;;
            5) _VOICE_ID="TxGEqnHWrfWFTfGW9XjX" ;;
            6) _VOICE_ID="EXAVITQu4vr4xnSDxMaL" ;;
            7) read -p "  Voice ID: " _VOICE_ID ;;
            *) _VOICE_ID="0hh7H4ZVAtaGpm1VZyEN" ;;
        esac
        [[ -n "$_VOICE_ID" ]] && save_key ELEVENLABS_VOICE_ID "$_VOICE_ID"
        echo ""
    fi

else
    [[ "$_need_llm" == "true" ]]          && echo -e "${YELLOW}Note:${NC} Add ANTHROPIC_API_KEY or OPENAI_API_KEY to ~/.config/md2pdf/.env"
    [[ "$_need_huggingface" == "true" ]]  && echo -e "${YELLOW}Note:${NC} Add HUGGINGFACE_TOKEN to ~/.config/md2pdf/.env for speaker identification"
    [[ "$_need_elevenlabs" == "true" ]]   && echo -e "${YELLOW}Note:${NC} Add ELEVENLABS_API_KEY to ~/.config/md2pdf/.env for transcription/narration"
fi

# ── System setup ─────────────────────────────────────────────────────────────

if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Warning: Node.js not found. md2pdf requires Node.js (https://nodejs.org/)${NC}"
else
    # Fresh install every time (uninstall removes it), so re-running install.sh pulls
    # the latest patched versions of these tools AND their dependencies. `npx --yes`
    # reused its first download forever, leaving users on vulnerable transitive deps.
    echo -e "${BLUE}Setting up:${NC} md-to-pdf and mermaid-cli at ~/.md2pdf-node"
    rm -rf "$HOME/.md2pdf-node"
    npm install --prefix "$HOME/.md2pdf-node" --loglevel=error --no-fund \
        md-to-pdf@latest @mermaid-js/mermaid-cli@latest
fi

source "$SCRIPT_DIR/python_select.sh"
VENV_PYTHON="$(find_venv_python || true)"
if [[ -z "$VENV_PYTHON" ]] && command -v brew &> /dev/null; then
    _PREFERRED_PYTHON="${PYTHON_VERSIONS%% *}"
    echo -e "${BLUE}Installing:${NC} python@$_PREFERRED_PYTHON (Homebrew) for the Python tools"
    brew install "python@$_PREFERRED_PYTHON"
    VENV_PYTHON="$(find_venv_python || true)"
fi

if [[ -n "$VENV_PYTHON" ]]; then
    for pkg in pymupdf4llm pymupdf-layout pytesseract Pillow anthropic openai faster-whisper pyannote.audio elevenlabs; do
        if pip3 show "$pkg" &>/dev/null 2>&1; then
            echo -e "${YELLOW}Cleaning up:${NC} removing $pkg from system Python"
            pip3 uninstall --break-system-packages -y "$pkg" 2>/dev/null || true
        fi
    done

    echo -e "${BLUE}Setting up:${NC} Python venv at ~/.md2pdf-venv ($("$VENV_PYTHON" --version))"
    "$VENV_PYTHON" -m venv --clear "$HOME/.md2pdf-venv"

    source "$SCRIPT_DIR/venv_packages.sh"
    _PKGS="$(venv_packages "$HOME/.config/md2pdf/.env")"

    "$HOME/.md2pdf-venv/bin/pip" install --quiet --upgrade $_PKGS
    echo ""

    # llm_helper — always installed; gracefully returns None when no key is set
    cp "$SCRIPT_DIR/llm_helper.py" "$HOME/.config/md2pdf/llm_helper.py"

else
    echo -e "${YELLOW}Warning: no supported Python ($PYTHON_VERSIONS) found. pdf2md and audio tools require one (brew install python@${PYTHON_VERSIONS%% *}).${NC}"
    echo ""
fi

# Check for ffmpeg (required for audio/video transcription)
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}Warning: ffmpeg not found. Audio/video transcription requires ffmpeg.${NC}"
    echo "Install with: brew install ffmpeg"
    echo ""
fi

# Check for tesseract (required for OCR of image-based PDFs)
if ! command -v tesseract &> /dev/null; then
    echo -e "${YELLOW}Installing tesseract (OCR for image-based PDFs)...${NC}"
    if command -v brew &> /dev/null; then
        brew install tesseract
    else
        echo -e "${YELLOW}Warning: tesseract not found and Homebrew not available.${NC}"
        echo "Install tesseract manually: https://github.com/tesseract-ocr/tesseract"
    fi
    echo ""
fi

# ── Phase 4: Install scripts and themes ─────────────────────────────────────

if [[ ! -d "$INSTALL_BIN" ]]; then
    echo -e "${BLUE}Creating:${NC} $INSTALL_BIN"
    mkdir -p "$INSTALL_BIN"
fi

for script in md2pdf pdf2md audio2md md2audio qr2clip; do
    echo -e "${BLUE}Installing:${NC} $script -> $INSTALL_BIN/$script"
    cp "$SCRIPT_DIR/$script" "$INSTALL_BIN/$script"
    chmod +x "$INSTALL_BIN/$script"
done

echo -e "${BLUE}Installing:${NC} themes -> $THEME_DIR/"
mkdir -p "$THEME_DIR"
cp "$SCRIPT_DIR/themes/"*.css "$THEME_DIR/"

# ── Phase 5: Install Quick Actions ──────────────────────────────────────────

_install_services=false
_install_shortcuts=false

if [[ ${#QA_SELECTED[@]} -gt 0 ]]; then
    echo ""
    echo -e "${BOLD}Install Method${NC}"
    echo ""
    echo "  Finder Services  Works immediately, no account needed."
    echo "                   Location: right-click → Services → [action name]"
    echo ""
    echo "  Shortcuts App    More prominently placed in Finder's Quick Actions menu."
    echo "                   Requires iCloud sign-in and the Shortcuts app."
    echo "                   Location: right-click → Quick Actions → [action name]"
    echo ""
    if [[ "$_CAN_SIGN" == "true" ]]; then
        echo "Install selected actions as:"
        echo "  [s] Finder Services only  (right-click → Services)"
        echo "  [q] Shortcuts App only    (right-click → Quick Actions)"
        echo "  [b] Both                  (default)"
        read -p "> " _install_type
        _install_type="${_install_type:-b}"
        [[ "$_install_type" == "s" || "$_install_type" == "b" ]] && _install_services=true
        [[ "$_install_type" == "q" || "$_install_type" == "b" ]] && _install_shortcuts=true
    else
        echo -e "${YELLOW}Note:${NC} Shortcuts App requires iCloud sign-in — installing as Finder Services only."
        echo "To also install as Shortcuts later, sign in to iCloud and re-run ./install.sh"
        _install_services=true
    fi
    echo ""
fi

# --- Install as Finder Services ---
# No-input services cannot be Shortcuts, so they install here even in Shortcuts-only mode.
if [[ "$_install_services" == "true" || "$_need_qr" == "true" ]]; then
    mkdir -p "$SERVICES_DIR"
    _need_finder_restart=false
    for num in "${QA_SELECTED[@]}"; do
        idx=$((num - 1))
        [[ $idx -lt 0 || $idx -ge ${#QA_NAMES[@]} ]] && continue
        name="${QA_NAMES[$idx]}"
        workflow="${QA_PATHS[$idx]}"
        input_type="$(workflow_input_type "$workflow")"
        [[ "$_install_services" != "true" && "$input_type" != "$NO_INPUT_TYPE" ]] && continue
        echo -e "${BLUE}Installing:${NC} Finder Service -> $SERVICES_DIR/$name"
        rm -rf "$SERVICES_DIR/$name"
        cp -R "$workflow" "$SERVICES_DIR/$name"
        service_name=$(/usr/libexec/PlistBuddy -c "Print :NSServices:0:NSMenuItem:default" "$SERVICES_DIR/$name/Contents/Info.plist" 2>/dev/null)
        # macOS keeps a service's hotkey (key_equivalent) in this same pbs entry, and
        # -dict-add replaces the whole entry. No-input services don't need the
        # context-menu flags, so leave their entry alone to preserve the hotkey.
        if [[ -n "$service_name" && "$input_type" != "$NO_INPUT_TYPE" ]]; then
            pbs_key="(null) - ${service_name} - runWorkflowAsService"
            defaults write pbs NSServicesStatus -dict-add \
                "\"$pbs_key\"" \
                '{ "presentation_modes" = { ContextMenu = 1; FinderPreview = 1; ServicesMenu = 1; TouchBar = 1; }; }'
        fi
        _need_finder_restart=true
    done
    if [[ "$_need_finder_restart" == "true" ]]; then
        killall pbs 2>/dev/null || true
        sleep 1
        killall Finder 2>/dev/null || true
    fi
    echo ""
fi

# --- Install as Shortcuts App ---
if [[ "$_install_shortcuts" == "true" ]]; then
    SHORTCUTS_TMP=$(mktemp -d)
    for num in "${QA_SELECTED[@]}"; do
        idx=$((num - 1))
        [[ $idx -lt 0 || $idx -ge ${#QA_NAMES[@]} ]] && continue
        workflow="${QA_PATHS[$idx]}"
        wf_name="${QA_NAMES[$idx]%.workflow}"

        cmd=$(/usr/libexec/PlistBuddy -c "Print :actions:0:action:ActionParameters:COMMAND_STRING" \
            "$workflow/Contents/document.wflow" 2>/dev/null)
        input_type="$(workflow_input_type "$workflow")"
        [[ -z "$cmd" ]] && continue
        if [[ "$input_type" == "$NO_INPUT_TYPE" ]]; then
            echo -e "${YELLOW}Note:${NC} '$wf_name' takes no input — installed as a Service only."
            continue
        fi

        input_xml=""
        i=0
        while true; do
            cls=$(/usr/libexec/PlistBuddy -c "Print :ShortcutInputClasses:$i" \
                "$workflow/Contents/Info.plist" 2>/dev/null) || break
            input_xml="${input_xml}<string>${cls}</string>
		"
            i=$((i + 1))
        done
        if [[ -z "$input_xml" ]]; then
            case "$input_type" in
                *folder*) input_xml='<string>WFFolderContentItem</string>' ;;
                *item*)   input_xml='<string>WFGenericFileContentItem</string>' ;;
                *)        input_xml='<string>WFGenericFileContentItem</string>
		<string>WFFolderContentItem</string>' ;;
            esac
        fi

        # Shortcuts run shell scripts in a sandboxed subprocess that cannot open files
        # in protected directories (Downloads, Documents, Desktop) even when Finder
        # passes them via Quick Actions. "Copy File Contents" must use stdin mode so
        # shortcuts.app reads the file itself (using its Finder-granted permission)
        # and pipes the content to the script, bypassing the sandbox restriction.
        if [[ "$wf_name" == "Copy File Contents" ]]; then
            shortcut_script="cat | pbcopy"
            shortcut_input_mode="to stdin"
        else
            shortcut_script=$(printf '%s' "$cmd" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')
            shortcut_input_mode="as arguments"
        fi
        cat > "$SHORTCUTS_TMP/shortcut.plist" << SHORTCUT_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>WFWorkflowMinimumClientVersionString</key>
	<string>900</string>
	<key>WFWorkflowTypes</key>
	<array>
		<string>QuickActions</string>
	</array>
	<key>WFWorkflowInputContentItemClasses</key>
	<array>
		${input_xml}
	</array>
	<key>WFWorkflowIcon</key>
	<dict>
		<key>WFWorkflowIconGlyphNumber</key>
		<integer>59511</integer>
		<key>WFWorkflowIconStartColor</key>
		<integer>4282601983</integer>
	</dict>
	<key>WFWorkflowActions</key>
	<array>
		<dict>
			<key>WFWorkflowActionIdentifier</key>
			<string>is.workflow.actions.runshellscript</string>
			<key>WFWorkflowActionParameters</key>
			<dict>
				<key>Script</key>
				<string>${shortcut_script}</string>
				<key>Shell</key>
				<string>/bin/bash</string>
				<key>InputMode</key>
				<string>${shortcut_input_mode}</string>
			</dict>
		</dict>
	</array>
</dict>
</plist>
SHORTCUT_EOF

        plutil -convert binary1 "$SHORTCUTS_TMP/shortcut.plist" \
            -o "$SHORTCUTS_TMP/unsigned.shortcut"
        if shortcuts sign -m anyone \
            -i "$SHORTCUTS_TMP/unsigned.shortcut" \
            -o "$SHORTCUTS_TMP/$wf_name.shortcut" 2>/dev/null; then
            echo -e "${BLUE}Installing:${NC} Shortcut -> $wf_name"
            open "$SHORTCUTS_TMP/$wf_name.shortcut"
            sleep 3
        else
            echo -e "${YELLOW}Warning:${NC} Failed to sign shortcut: $wf_name"
        fi
    done
    echo ""
    echo -e "${YELLOW}Note:${NC} Click 'Add Shortcut' for each dialog in the Shortcuts app."
    echo ""
    echo "Next steps after adding all shortcuts:"
    echo "  1. Shortcuts app -> Settings (Cmd+,) -> Advanced -> check 'Allow Running Scripts'"
    echo "  2. Restart your Mac (required for shortcuts to appear in Finder)"
    echo "  3. Right-click any file -> Quick Actions -> Customize... -> toggle on what you want"
    echo "     (macOS shows only relevant actions per file type, so enabling all is fine)"
    sleep 5
    rm -rf "$SHORTCUTS_TMP"
fi

if [[ "$_need_qr" == "true" ]]; then
    echo ""
    echo -e "${BOLD}Decode QR Code On Screen${NC}"
    echo "  1. Bind a hotkey: System Settings -> Keyboard -> Keyboard Shortcuts -> Services -> General"
    echo "     (an existing hotkey for this service is preserved across reinstalls)"
    echo "  2. On first use, grant Screen Recording permission when System Settings opens."
fi

echo ""
echo "Run 'md2pdf --help' or 'pdf2md --help' to get started."
