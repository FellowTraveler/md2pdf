#!/usr/bin/env bash
#
# md2pdf installer
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

echo -e "${BOLD}md2pdf Installer${NC}"
echo ""

# Check for Node.js (required for md-to-pdf)
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}Warning: Node.js not found. md2pdf requires Node.js to run.${NC}"
    echo "Install Node.js from https://nodejs.org/"
    echo ""
fi

# Create bin directory if needed
if [[ ! -d "$INSTALL_BIN" ]]; then
    echo -e "${BLUE}Creating:${NC} $INSTALL_BIN"
    mkdir -p "$INSTALL_BIN"
fi

# Install script
echo -e "${BLUE}Installing:${NC} md2pdf -> $INSTALL_BIN/md2pdf"
cp "$SCRIPT_DIR/md2pdf" "$INSTALL_BIN/md2pdf"
chmod +x "$INSTALL_BIN/md2pdf"

# Install themes
echo -e "${BLUE}Installing:${NC} themes -> $THEME_DIR/"
mkdir -p "$THEME_DIR"
cp "$SCRIPT_DIR/themes/"*.css "$THEME_DIR/"

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

echo "Run 'md2pdf --help' to get started."
