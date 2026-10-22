# Python CLI

This repository now includes a Python-only CLI implementation for splitting PDFs
without GUI or OCR.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

Mode definitions:

- `content` (default): Split by document structure. The CLI uses the PDF outline
  (table of contents/bookmarks) up to `--depth` first. If no outline is present,
  it falls back to heading detection from text layout.
- `length`: Split into equally sized parts based only on page count. Use
  `--parts` to control how many output files are created.

Default behavior:

- If `--mode` is omitted, `pdf-splitter` runs in `content` mode.
- In content mode, `--depth` defaults to `1`.
- In length mode, `--parts` defaults to `4`.
- If `--output-dir` is omitted, output is written to a sibling folder named
  after the input PDF file.

Split by content (outline first, heading detection fallback):

```bash
pdf-splitter input.pdf --mode content --depth 2
```

Split by equal length:

```bash
pdf-splitter input.pdf --mode length --parts 6
```

Choose output folder:

```bash
pdf-splitter input.pdf --output-dir ./out
```

## Notes

- `--mode` defaults to `content`.
- OCR is intentionally not part of this Python CLI.
