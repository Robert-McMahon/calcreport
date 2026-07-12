# calcreport

A workflow for generating presentable engineering calculation reports from notebooks:
unit-aware calculations (pint) with Mathcad-style math display (sympy → MathML
in notebook previews, MathJax in the printed report), paginated to PDF via
HTML and paged.js.

## Starting a new project

```bash
uvx --from "git+https://github.com/Robert-McMahon/calcreport" \
    calcreport-init ~/projects/30040-CLIENT-PROJECT
```

Scaffolds the project directory: pyproject with `calcreport[marimo]` (from
git), a starter marimo report notebook prefilled from the
`jobnum-CLIENT-PROJECT` directory name (override with `--client/--project/
--title`), `images/`, README, .gitignore, a local git repo, and a synced
`.venv`. Then `uv run marimo edit <jobnum>-001.py` and follow the project
README. Create the private remote when ready:
`gh repo create <name> --private --source .`

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

## Writing calculations

State inputs with `displaymath`, then use `equation()` to render a
calculation symbolically from the same expression that computes it — the
formula in the report can never drift from the code:

```python
m_engine = Q_(3448, u.kg)
displaymath(m_engine, comment='Mass of the engine')          # m_engine = 3448 kg

F = equation('F = m_engine * g', to=u.kN,
             comment='Engine weight')                        # F = m_engine · g
                                                             # F = 33.82 kN
d = equation('d = sqrt(4 * A_bolt / pi)', to=u.mm)           # proper radical + π
```

`equation()` evaluates against your variables (pint quantities, sympy,
numbers) and returns the result. Common functions (`sqrt`, `sin`, `log`,
`min`, ...) and constants (`pi`, `e`) are available without imports;
`.to(...)` inside an expression is treated as unit bookkeeping and left out
of the symbolic form. Results display at 4 significant figures by default
(`digits=` to change, `digits=None` for full precision); the returned value
always keeps full precision. `show_result=False` renders the formula only,
`evaluate=False` makes it display-only.

Greek symbols: use real Unicode characters in variable names (`σ_max`,
`Δp`, `θ_x`) — they are valid Python identifiers and render directly. A
VS Code extension that completes `\sigma` → `σ` makes typing painless.
Spelled-out names (`sigma_max`, `SigmaF`) also work, matched on whole name
segments so words like `pitch` are never mangled. Avoid the Unicode
"mathematical alphanumeric" letters (𝑚, 𝐹) and sub/superscript characters
(F₁, Fₐ): Python folds them into plain ASCII identifiers, so visually
distinct names silently collide.

## Cross-references

Give things an id, then reference them anywhere — in markdown or in
equation comments — with `@fig:` / `@eq:` / `@tbl:` / `@sec:`. Numbers are
assigned in document order at export time and render as links:

```python
F = equation('F = m * g', id='weight')                  # numbered: ... (1)
create_results_table(sol, table_id='res', caption='Mount reactions')
Image('images/mesh.png', metadata={'ID': 'mesh', 'caption': 'FE mesh'})
```

```markdown
## Design Loads {#sec:loads}

Per @eq:weight, the reactions in @tbl:res follow from the loads in
@sec:loads; the model is shown in @fig:mesh.
```

renders as "Per Equation (1), the reactions in Table 1 follow from the
loads in Section 1.1; the model is shown in Figure 1." Unresolved
references are left literal with a console warning. The legacy `[id]`
figure syntax still works (and no longer interferes with markdown links).
Note: projects with a customized local `templates/styles.css` need the
`.eq-number` / `.table-block` styles from the bundled stylesheet for
numbers and captions to display nicely.

## Authoring in marimo

Reports can be authored in [marimo](https://marimo.io) instead of Jupyter
(install with the `marimo` extra: `pip install 'calcreport[marimo]'`):

```bash
marimo edit report.py                                        # author
marimo export ipynb --include-outputs report.py -o report.ipynb   # execute + export
notebooktohtml report.ipynb report.html --standalone --pdf        # render
```

`displaymath`/`equation` work unchanged in marimo cells, including multiple
calls per cell. Equations are emitted as MathML with self-contained inline
styling, so they preview identically in the marimo browser editor and in the
VS Code marimo extension's notebook view (no JavaScript or stylesheet needed
in the host; the exporter strips the preview styling, so the report
stylesheet controls print typography). If previews ever look wrong in
VS Code after upgrading calcreport, fully restart VS Code - kernel processes
keep the version of calcreport they imported at launch.

Since marimo has no per-cell metadata, give the cover page and appendices
their metadata as `key: value` lines directly under the heading in the
markdown cell:

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
