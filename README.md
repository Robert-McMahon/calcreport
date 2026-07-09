# calcreport

A workflow for generating presentable engineering calculation reports from notebooks:
unit-aware calculations (pint) with Mathcad-style TeX output (sympy + MathJax),
paginated to PDF via HTML and paged.js.

## Pipeline

```
notebook (.ipynb) --> notebooktohtml --> report HTML --> headless Chromium --> PDF
```

```bash
notebooktohtml report.ipynb report.html            # HTML (serve over http to view)
notebooktohtml report.ipynb report.html --pdf      # ... plus PDF via headless Chromium
notebooktohtml report.ipynb report.html --standalone   # single self-contained file,
                                                       # opens directly from file://
```

`--pdf` needs a one-time `playwright install chromium`. A project-local
`templates/report_template.html` overrides the bundled template.

## Authoring in marimo

Reports can be authored in [marimo](https://marimo.io) instead of Jupyter
(install with the `marimo` extra: `pip install 'calcreport[marimo]'`):

```bash
marimo edit report.py                                        # author
marimo export ipynb --include-outputs report.py -o report.ipynb   # execute + export
notebooktohtml report.ipynb report.html --standalone --pdf        # render
```

`displaymath` works unchanged in marimo cells (equations preview live via
MathJax), including multiple calls per cell. Since marimo has no per-cell
metadata, give the cover page and appendices their metadata as `key: value`
lines directly under the heading in the markdown cell:

```markdown
# Cover Page
title: Structural Analysis Report
client: ACME Pty Ltd
project: 99001
docid: 99001-001
revision: A

| Revision | Date | Description |
|----------|------|-------------|
| A | 2026-07-09 | Issued for review |
```

Recognised keys: title, client, project, docid, revision, filename, date,
author. In Jupyter notebooks the existing cell-metadata mechanism still works
and takes precedence.

Migrating an existing notebook: `marimo convert report.ipynb -o report.py`,
then fix the imports cell (no `import *` or `from __future__` in marimo cells)
and add the metadata lines above.
