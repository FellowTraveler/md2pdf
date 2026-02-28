# md2pdf & pdf2md

Convert between Markdown and PDF. Includes `md2pdf` for themed PDF generation and `pdf2md` for PDF-to-Markdown extraction (with OCR fallback and optional AI cleanup).

## Installation

### Requirements

- **Node.js** (v14 or later) - [nodejs.org](https://nodejs.org/) (for md2pdf)
- **Python 3** with `pymupdf4llm` (for pdf2md)
- **pdfinfo** (optional, for page count) - usually bundled with poppler

**Optional (for image-based PDFs):**
- **tesseract** - OCR engine: `brew install tesseract`
- **pytesseract** and **Pillow** - Python bindings: `pip3 install pytesseract Pillow`
- **anthropic** - AI cleanup of OCR output: `pip3 install anthropic`

### Install

```bash
git clone https://github.com/FellowTraveler/md2pdf.git
cd md2pdf
./install.sh
```

This installs:
- `md2pdf` and `pdf2md` scripts to `~/bin/`
- Theme CSS files to `~/.md2pdf-themes/`
- Finder Quick Actions to `~/Library/Services/` (right-click context menu)

If `~/bin` is not in your PATH, the installer will show you how to add it.

## Usage

```
md2pdf - Convert Markdown to beautiful PDFs

USAGE:
    md2pdf <file.md> [theme]     Convert markdown to PDF
    md2pdf --list                List available themes
    md2pdf --help                Show this help

OUTPUT:
    Creates a PDF file with the same name as the input file.
    Example: README.md -> README.pdf

THEMES:
    academic
    claude
    dark
    executive
    github
    minimal
    modern

EXAMPLES:
    md2pdf README.md             # -> README.pdf (default: executive)
    md2pdf README.md minimal     # -> README.pdf (minimal theme)
    md2pdf docs/guide.md modern  # -> docs/guide.pdf (modern theme)
```

### Output

Creates a PDF with the same name as the input file:
- `README.md` → `README.pdf`
- `docs/guide.md` → `docs/guide.pdf`

### Examples

```bash
md2pdf README.md              # Uses default theme (executive)
md2pdf README.md minimal      # Uses minimal theme
md2pdf docs/guide.md modern   # Convert with modern theme
```

### Commands

```bash
md2pdf --list    # List available themes with descriptions
md2pdf --help    # Show help
```

## Themes

| Theme | Description |
|-------|-------------|
| **executive** | Professional corporate style with navy blue accents. Default. |
| **minimal** | Clean, sparse design with maximum whitespace. |
| **academic** | Traditional serif typography for papers and articles. |
| **modern** | Contemporary tech documentation style. |
| **github** | GitHub's markdown rendering style. |
| **dark** | Dark background with light text. |
| **claude** | Claude Desktop's warm, clean aesthetic. |

Run `md2pdf --list` for detailed theme descriptions.

## Custom Themes

Add your own CSS files to `~/.md2pdf-themes/` and they'll appear in the theme list.

## pdf2md

Convert PDF files to Markdown. Handles both text-based and image-based (scanned) PDFs.

```
pdf2md - Convert PDF files to Markdown

USAGE:
    pdf2md <file.pdf>     Convert PDF to Markdown
    pdf2md --help         Show this help

OUTPUT:
    Creates a Markdown file with the same name as the input file.
    Example: README.pdf -> README.md
```

### How It Works

1. **Text extraction** — Uses `pymupdf4llm` to extract text and formatting directly from the PDF.
2. **OCR fallback** — If no text is found (image-based/scanned PDFs), falls back to `tesseract` OCR.
3. **AI cleanup** (optional) — If `ANTHROPIC_API_KEY` is set, sends OCR output to Claude Haiku to clean up duplicates, fix artifacts, and restore markdown formatting.

### Examples

```bash
pdf2md document.pdf              # -> document.md
pdf2md scanned-doc.pdf           # OCR + optional AI cleanup
```

### AI Cleanup for OCR

OCR output from scanned PDFs is often messy (duplicated content, garbled text, lost formatting). Setting `ANTHROPIC_API_KEY` enables automatic cleanup via Claude Haiku:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
pdf2md scanned-doc.pdf           # OCR output is automatically cleaned up
```

Without the API key, pdf2md still works — you just get the raw OCR output with a tip about enabling cleanup.

## Finder Quick Actions

The installer adds right-click context menu actions for macOS Finder:

- **Convert MD to PDF** — Right-click any `.md` file to convert it to PDF
- **Convert PDF to MD** — Right-click any `.pdf` file to convert it to Markdown

These appear under **Quick Actions** in the Finder right-click menu. A macOS notification confirms when the conversion is complete.

## Author

- Chris Odom - [GitHub](https://github.com/fellowtraveler)
- Contact: [chris@texasfortress.ai](mailto:chris@texasfortress.ai)
- [Become a sponsor for Chris](https://github.com/sponsors/fellowtraveler)
- [![Tip Chris in Crypto](https://tip.md/badge.svg)](https://tip.md/FellowTraveler)

## License

MIT
