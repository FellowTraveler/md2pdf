# Decides which pip packages ~/.md2pdf-venv needs. Sourced by install.sh.
#
# An optional feature's package is installed when its Quick Action was selected
# (the _need_* flags) AND its key is saved in the env file — whether typed during
# this run or saved by an earlier install. Gating on "typed this run" dropped
# pyannote/elevenlabs for anyone who pressed Enter to keep their saved keys.

has_saved_key() {  # has_saved_key NAME ENV_FILE — true if NAME has a non-empty value
    grep -q "^${1}=." "$2" 2>/dev/null
}

venv_packages() {  # venv_packages ENV_FILE — prints the package list
    local env_file="$1"
    # av<19: faster-whisper 1.2.1 passes metadata_errors to av.open(), removed in av 19
    # (fixed on faster-whisper master, unreleased). Drop the cap after its next release.
    local packages="pymupdf4llm pytesseract Pillow faster-whisper av<19"
    if [[ "$_need_llm" == "true" ]]; then
        has_saved_key ANTHROPIC_API_KEY "$env_file" && packages="$packages anthropic"
        has_saved_key OPENAI_API_KEY "$env_file" && packages="$packages openai"
    fi
    if [[ "$_need_huggingface" == "true" ]] && has_saved_key HUGGINGFACE_TOKEN "$env_file"; then
        packages="$packages pyannote.audio"
    fi
    if [[ "$_need_elevenlabs" == "true" ]] && has_saved_key ELEVENLABS_API_KEY "$env_file"; then
        packages="$packages elevenlabs"
    fi
    echo "$packages"
}
