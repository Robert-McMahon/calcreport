# Quarto + marimo + Typst pilot

This pilot keeps the calculation in a `.qmd` file, executes its marimo cells in
the existing `calcreport` environment, and uses Quarto's Typst backend to create
an A4 PDF.

## Render

The installed `quarto-marimo` extension requires Quarto 1.9.20 or newer. With a
compatible Quarto executable on `PATH`, run from this directory:

```sh
quarto render pilot.qmd
```

The PDF is written to `_output/pilot.pdf`.

`external-env: true` is deliberately present in the document front matter. It
causes the extension to use the active Python environment rather than asking
`uv` to construct another one. Activate the repository virtual environment, or
otherwise ensure that `marimo` and `calcreport` are importable before rendering.

## Portable Markdown adapter

The reusable `PortableMarkdown`, `quantity_markdown`, `equation_markdown`, and
`table_markdown` APIs now live in `calcreport`. They provide Quarto with semantic
Markdown for equations and tables while remaining valid marimo outputs. The
vendored `quarto-marimo` v0.4.5 extension has one compatibility change in
`extract.py`: prefer `text/markdown` when extracting a marimo MIME bundle.

This enables native equation and table labels, cross-references, and Typst
typesetting without giving up unit-aware Python calculations. These semantic
outputs are shared by future reports rather than repeated in each `.qmd` file.

## Current limitations found by the pilot

- The extension currently needs a newer Quarto than the system installation
  that was present when this pilot was made.
- HTML rendering uses reactive marimo islands, so Quarto does not resolve labels
  emitted by cells in the same way as the static Typst path. Typst is therefore
  the default format for this pilot.
- The extension disables Quarto execution freezing, and a multi-format render
  executes the calculation once per format.
- A fully self-contained HTML render conflicts with the extension's external
  island assets; this does not affect the Typst PDF.

These are extension-integration issues, not limitations of the underlying
calculation model.
