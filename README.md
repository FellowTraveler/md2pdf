# md2pdf

Convert Markdown to beautiful PDFs with customizable themes.

## Installation

### Requirements

- **Node.js** (v14 or later) - [nodejs.org](https://nodejs.org/)
- **pdfinfo** (optional, for page count) - usually bundled with poppler

### Install

```bash
git clone https://github.com/FellowTraveler/md2pdf.git
cd md2pdf
./install.sh
```

This installs:
- `md2pdf` script to `~/bin/`
- Theme CSS files to `~/.md2pdf-themes/`

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

## License

MIT
