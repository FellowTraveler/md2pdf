#!/usr/bin/env bash
#
# md2pdf & pdf2md installer
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_BIN="${HOME}/bin"
THEME_DIR="${HOME}/.md2pdf-themes"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BOLD}md2pdf & pdf2md Installer${NC}"
echo ""

# Check for Node.js (required for md-to-pdf)
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Warning: Node.js not found. md2pdf requires Node.js to run.${NC}"
    echo "Install Node.js from https://nodejs.org/"
    echo ""
fi

# Check for Python 3 and pymupdf4llm (required for pdf2md)
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Warning: Python 3 not found. pdf2md requires Python 3 to run.${NC}"
    echo ""
elif ! python3 -c "import pymupdf4llm" 2>/dev/null; then
    echo -e "${YELLOW}Warning: pymupdf4llm not found. Installing...${NC}"
    pip3 install pymupdf4llm
    echo ""
fi

# Check for anthropic package (optional, for AI cleanup of OCR output)
if command -v python3 &> /dev/null; then
    if ! python3 -c "import anthropic" 2>/dev/null; then
        echo -e "${YELLOW}Installing anthropic (for AI cleanup of OCR output)...${NC}"
        pip3 install anthropic
        echo ""
    fi
fi

# Create bin directory if needed
if [[ ! -d "$INSTALL_BIN" ]]; then
    echo -e "${BLUE}Creating:${NC} $INSTALL_BIN"
    mkdir -p "$INSTALL_BIN"
fi

# Install scripts
echo -e "${BLUE}Installing:${NC} md2pdf -> $INSTALL_BIN/md2pdf"
cp "$SCRIPT_DIR/md2pdf" "$INSTALL_BIN/md2pdf"
chmod +x "$INSTALL_BIN/md2pdf"

echo -e "${BLUE}Installing:${NC} pdf2md -> $INSTALL_BIN/pdf2md"
cp "$SCRIPT_DIR/pdf2md" "$INSTALL_BIN/pdf2md"
chmod +x "$INSTALL_BIN/pdf2md"

# Install themes
echo -e "${BLUE}Installing:${NC} themes -> $THEME_DIR/"
mkdir -p "$THEME_DIR"
cp "$SCRIPT_DIR/themes/"*.css "$THEME_DIR/"

# Install Finder Quick Actions
SERVICES_DIR="${HOME}/Library/Services"
mkdir -p "$SERVICES_DIR"
for workflow in "$SCRIPT_DIR/"*.workflow; do
    if [[ -d "$workflow" ]]; then
        name="$(basename "$workflow")"
        echo -e "${BLUE}Installing:${NC} Quick Action -> $SERVICES_DIR/$name"
        rm -rf "$SERVICES_DIR/$name"
        cp -R "$workflow" "$SERVICES_DIR/$name"

        # Register as Quick Action in pbs (pasteboard server) so it appears in Finder context menu
        service_name=$(/usr/libexec/PlistBuddy -c "Print :NSServices:0:NSMenuItem:default" "$SERVICES_DIR/$name/Contents/Info.plist" 2>/dev/null)
        if [[ -n "$service_name" ]]; then
            pbs_key="(null) - ${service_name} - runWorkflowAsService"
            defaults write pbs NSServicesStatus -dict-add \
                "\"$pbs_key\"" \
                '{ "presentation_modes" = { ContextMenu = 1; FinderPreview = 1; ServicesMenu = 1; TouchBar = 1; }; }'
        fi
    fi
done

# Restart pasteboard server and Finder so Quick Actions appear immediately
killall pbs 2>/dev/null || true
sleep 1
killall Finder 2>/dev/null || true

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""

# Check if ~/bin is in PATH
if [[ ":$PATH:" != *":$HOME/bin:"* ]]; then
    echo -e "${YELLOW}Note:${NC} Add ~/bin to your PATH to run md2pdf from anywhere:"
    echo ""
    echo "  echo 'export PATH=\"\$HOME/bin:\$PATH\"' >> ~/.zshrc"
    echo "  source ~/.zshrc"
    echo ""
fi

# Install Shortcuts for Finder Quick Actions (modern macOS)
if command -v shortcuts &> /dev/null; then
    echo -e "${BOLD}Finder Quick Actions (Shortcuts)${NC}"
    echo "On modern macOS, Shortcuts appear in Finder's right-click Quick Actions menu."
    echo "Each shortcut requires a one-time confirmation in the Shortcuts app."
    echo ""

    # Build numbered list of available workflows
    WF_NAMES=()
    WF_PATHS=()
    i=1
    for workflow in "$SCRIPT_DIR/"*.workflow; do
        [[ -d "$workflow" ]] || continue
        WF_NAMES+=("$(basename "$workflow" .workflow)")
        WF_PATHS+=("$workflow")
        printf "  %2d) %s\n" "$i" "$(basename "$workflow" .workflow)"
        i=$((i + 1))
    done

    echo ""
    echo "Enter numbers to install (e.g., 1 3 7), 'all', or 'none' to skip:"
    read -p "> " selection

    SELECTED=()
    case "$selection" in
        none|"") ;;
        all)     SELECTED=($(seq 1 ${#WF_NAMES[@]})) ;;
        *)       SELECTED=($selection) ;;
    esac

    if [[ ${#SELECTED[@]} -gt 0 ]]; then
        SHORTCUTS_TMP=$(mktemp -d)
        echo ""

        for num in "${SELECTED[@]}"; do
            idx=$((num - 1))
            [[ $idx -lt 0 || $idx -ge ${#WF_NAMES[@]} ]] && continue

            workflow="${WF_PATHS[$idx]}"
            wf_name="${WF_NAMES[$idx]}"

            # Extract shell command and input type from Automator workflow
            cmd=$(/usr/libexec/PlistBuddy -c "Print :actions:0:action:ActionParameters:COMMAND_STRING" \
                "$workflow/Contents/document.wflow" 2>/dev/null)
            input_type=$(/usr/libexec/PlistBuddy -c "Print :workflowMetaData:serviceInputTypeIdentifier" \
                "$workflow/Contents/document.wflow" 2>/dev/null)
            [[ -z "$cmd" ]] && continue

            # Map Automator input type to Shortcuts content item classes
            case "$input_type" in
                *folder*) input_xml='<string>WFFolderContentItem</string>' ;;
                *item*)   input_xml='<string>WFGenericFileContentItem</string>' ;;
                *)        input_xml='<string>WFGenericFileContentItem</string>
		<string>WFFolderContentItem</string>' ;;
            esac

            # XML-escape the shell command
            escaped_cmd=$(printf '%s' "$cmd" | sed 's/&/\&amp;/g; s/</\&lt;/g; s/>/\&gt;/g')

            # Generate shortcut plist
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
				<key>WFShellScriptActionInputMode</key>
				<string>as arguments</string>
				<key>COMMAND_STRING</key>
				<string>${escaped_cmd}</string>
			</dict>
		</dict>
	</array>
</dict>
</plist>
SHORTCUT_EOF

            # Convert to binary plist and sign
            plutil -convert binary1 "$SHORTCUTS_TMP/shortcut.plist" -o "$SHORTCUTS_TMP/unsigned.shortcut"
            if shortcuts sign -m anyone -i "$SHORTCUTS_TMP/unsigned.shortcut" \
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
        sleep 5
        rm -rf "$SHORTCUTS_TMP"
    fi
fi

echo ""
echo "Run 'md2pdf --help' or 'pdf2md --help' to get started."
