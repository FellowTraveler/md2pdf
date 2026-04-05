# Mermaid Diagram Support Design

Date: 2026-04-05

## Overview

Two features:
1. **MD→PDF**: Render embedded mermaid diagrams when converting markdown to PDF
2. **PDF→MD**: Detect diagrams in PDFs and convert them to mermaid blocks when converting to markdown

---

## Feature 1: MD→PDF Mermaid Rendering

### Approach

Pre-render mermaid blocks to SVG before passing to `md-to-pdf`, using the offline
`@mermaid-js/mermaid-cli` package (via `npx`).

### Flow

1. Scan input markdown for ` ```mermaid ` blocks
2. If none found, pass through unchanged (zero overhead)
3. For each mermaid block:
   - Write diagram source to a temp `.mmd` file
   - Run `npx --yes @mermaid-js/mermaid-cli mmdc -i diagram.mmd -o diagram.svg`
   - Replace the ` ```mermaid ``` ` block in a temp copy of the markdown with `![diagram](diagram.svg)`
4. Pass the modified temp markdown to `md-to-pdf` as usual
5. Clean up all temp files after conversion

### Notes

- Works fully offline after first `npx` cache warms up
- No timing/JS execution issues in headless browser
- SVGs scale cleanly to any PDF page size

---

## Feature 2: PDF→MD Diagram Detection and Mermaid Conversion

### Approach

After text extraction, extract all embedded images from the PDF using `pymupdf`.
Classify each image with Claude vision. Diagrams get converted to mermaid; non-diagrams
are saved as image files. Both types are saved to disk and referenced in the markdown.

### Flow

1. Extract text as before with `pymupdf4llm` (unchanged)
2. Use `pymupdf` (already a transitive dependency) to extract all embedded images, grouped by page number
3. For each image:
   - **Step A — Classify**: Call Claude vision: "Is this a technical diagram (flowchart, sequence diagram, architecture chart, etc.) that could be expressed as Mermaid? Answer Yes or No."
   - **Step B (diagrams only) — Convert**: Call Claude vision: "Convert this diagram to Mermaid syntax. Output only the mermaid code block, no explanation."
4. Save all images to disk as `<basename>_p<page>_img<n>.png` (both diagrams and non-diagrams)
5. Insert into markdown at the appropriate page position:
   - **Diagram**: insert saved image reference `![](...)` AND a ` ```mermaid ``` ` block with the generated source
   - **Non-diagram**: insert saved image reference `![](...)` only
6. Existing LLM cleanup pass normalizes the combined output

### Image Naming

Images saved adjacent to the output `.md` file:
```
report.pdf  →  report.md
               report_p1_img1.png
               report_p1_img2.png
               report_p2_img1.png
               ...
```

### API Usage

- Uses `claude-sonnet-4-6` (or configured model) via the `anthropic` Python package
- Requires `ANTHROPIC_API_KEY` (same as existing LLM cleanup)
- If no API key, diagram detection is skipped and images are saved as plain image references

---

## Dependencies

### New (MD→PDF)
- `@mermaid-js/mermaid-cli` — via `npx`, no explicit install required

### New (PDF→MD)
- No new Python packages — `pymupdf` is already available as a dep of `pymupdf4llm`

### Already Present
- `anthropic` Python package (already installed by `install.sh`)
- `pymupdf` (transitive dep of `pymupdf4llm`)
