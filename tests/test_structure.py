"""Tests for document-structure extraction and section rendering.

Regression tests for defects found while producing report 30038-001:
- the Executive Summary bypassed cross-reference resolution;
- only the first heading of a markdown cell was registered, so an h2
  sharing a cell with its h1 vanished from the TOC and kept its literal
  '{#sec:...}' anchor in the rendered heading.
"""

import json
import re

import pytest

from calcreport.export.notebooktohtml import NotebookToHTML


def md_cell(source):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': [source]}


def code_cell(source, html_output=None):
    outputs = []
    if html_output:
        outputs.append({'output_type': 'display_data',
                        'data': {'text/html': [html_output]}})
    return {'cell_type': 'code', 'metadata': {},
            'source': [source], 'outputs': outputs}


EQ_OUTPUT = (
    '<div class="math" id="eq-cap"><div class="math-equation">'
    '\\[ F = m \\cdot g \\]'
    '<span class="eq-number" data-eq-id="cap"></span></div></div>'
)


def render(cells, tmp_path):
    notebook = {'cells': cells, 'metadata': {},
                'nbformat': 4, 'nbformat_minor': 5}
    path = tmp_path / 'report.ipynb'
    path.write_text(json.dumps(notebook))
    return NotebookToHTML().convert_notebook(str(path))


COVER = md_cell('# Cover Page\ntitle: T\nclient: C\nproject: P\n'
                'docid: D\nrevision: 0')


class TestExecutiveSummaryReferences:
    def test_references_resolve_in_executive_summary(self, tmp_path):
        html = render([
            COVER,
            md_cell('# Executive Summary\n\n'
                    'The capacity per @eq:cap governs.'),
            md_cell('# Analysis'),
            code_cell("F = equation('F = m * g', id='cap')", EQ_OUTPUT),
        ], tmp_path)

        assert '@eq:cap' not in html
        summary = html.split('id="executive-summary"')[1]
        assert 'href="#eq-cap"' in summary
        assert 'Equation (1)' in summary


class TestMultiHeadingCells:
    """Every heading in a markdown cell is numbered and reaches the TOC."""

    @pytest.fixture
    def report_html(self, tmp_path):
        return render([
            COVER,
            md_cell('# Analysis\n\n## Kerf Geometry {#sec:kerf}\n\n'
                    'The kerf drives power demand.'),
            md_cell('Prose between sections.\n\n## Spindle Speed'),
            md_cell('See @sec:kerf for the kerf.'),
        ], tmp_path)

    def test_first_heading_numbered(self, report_html):
        assert '1. Analysis' in report_html

    def test_second_heading_in_same_cell_numbered(self, report_html):
        assert '1.1. Kerf Geometry' in report_html

    def test_following_cells_continue_numbering(self, report_html):
        assert '1.2. Spindle Speed' in report_html

    def test_anchor_tag_stripped_from_mid_cell_heading(self, report_html):
        assert '{#sec:kerf}' not in report_html

    def test_mid_cell_heading_referenceable(self, report_html):
        assert ('<a class="section-ref" href="#s1s1">Section 1.1</a>'
                in report_html)

    def test_all_headings_reach_the_toc(self, report_html):
        toc = report_html.split('</nav>')[0]
        assert '1.1. Kerf Geometry' in toc
        assert '1.2. Spindle Speed' in toc


class TestEquationBlocksStayWhole:
    """Each equation block carries an inline break-inside: avoid.

    paged.js disables stylesheet break-inside rules during layout and
    mishandles a flex block fragmented across the page boundary (it was left
    in the hidden overflow column and dropped from report 30038-001-calc).
    Inline styles survive, so the browser keeps the block whole.
    """

    def test_inline_break_inside_on_math_blocks(self, tmp_path):
        html = render([
            COVER,
            md_cell('# Analysis'),
            code_cell("F = equation('F = m * g', id='cap')", EQ_OUTPUT),
        ], tmp_path)
        tag = re.search(r'<div[^>]*id="eq-cap"[^>]*>', html).group(0)
        assert 'class="math"' in tag
        assert 'break-inside: avoid' in tag

    def test_preview_styling_still_stripped(self, tmp_path):
        preview = EQ_OUTPUT.replace('<div class="math" id="eq-cap">',
                                    '<div class="math" id="eq-cap" data-preview="1" style="display:flex">')
        html = render([
            COVER,
            md_cell('# Analysis'),
            code_cell("F = equation('F = m * g', id='cap')", preview),
        ], tmp_path)
        assert 'data-preview' not in html
        assert 'display:flex' not in html
        assert 'break-inside: avoid' in html
