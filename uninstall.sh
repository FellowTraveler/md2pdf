#!/usr/bin/env bash
#
# md2pdf & pdf2md uninstaller
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_BIN="${HOME}/bin"
THEME_DIR="${HOME}/.md2pdf-themes"
SERVICES_DIR="${HOME}/Library/Services"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BOLD}md2pdf & pdf2md Uninstaller${NC}"
echo ""

# Remove scripts
for script in md2pdf pdf2md; do
    if [[ -f "$INSTALL_BIN/$script" ]]; then
        echo -e "${BLUE}Removing:${NC} $INSTALL_BIN/$script"
        rm -f "$INSTALL_BIN/$script"
    fi
done

# Remove themes
if [[ -d "$THEME_DIR" ]]; then
    echo -e "${BLUE}Removing:${NC} $THEME_DIR/"
    rm -rf "$THEME_DIR"
fi

# Remove Python venv
if [[ -d "$HOME/.md2pdf-venv" ]]; then
    echo -e "${BLUE}Removing:${NC} ~/.md2pdf-venv"
    rm -rf "$HOME/.md2pdf-venv"
fi

# Remove Automator workflows from Services
for workflow in "$SCRIPT_DIR/"*.workflow; do
    [[ -d "$workflow" ]] || continue
    name="$(basename "$workflow")"
    if [[ -d "$SERVICES_DIR/$name" ]]; then
        echo -e "${BLUE}Removing:${NC} $SERVICES_DIR/$name"
        rm -rf "$SERVICES_DIR/$name"
    fi
done

# Restart pbs and Finder to clear stale entries
killall pbs 2>/dev/null || true
sleep 1
killall Finder 2>/dev/null || true

echo ""
echo -e "${GREEN}Uninstall complete!${NC}"
echo ""

# Warn about Shortcuts that must be removed manually
if command -v shortcuts &> /dev/null; then
    remaining=""
    while IFS= read -r sc; do
        for workflow in "$SCRIPT_DIR/"*.workflow; do
            [[ -d "$workflow" ]] || continue
            wf_name="$(basename "$workflow" .workflow)"
            if [[ "$sc" == "$wf_name" ]]; then
                remaining="${remaining}  - ${sc}\n"
            fi
        done
    done < <(shortcuts list 2>/dev/null)

    if [[ -n "$remaining" ]]; then
        echo -e "${YELLOW}Note:${NC} macOS does not allow removing Shortcuts from the command line."
        echo "Please delete these manually in the Shortcuts app (Cmd+click to select, then Delete):"
        echo -e "$remaining"
    fi
fi
