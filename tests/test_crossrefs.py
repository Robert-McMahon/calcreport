"""Tests for @fig/@eq/@tbl/@sec cross-references and numbering."""

import json

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
    '<div class="math" id="eq-weight"><div class="math-equation">'
    '\\[ F = m \\cdot g \\]'
    '<span class="eq-number" data-eq-id="weight"></span></div>'
    '<div class="math-comment">Engine weight per @fig:lc1</div></div>'
)

TBL_OUTPUT = (
    '<div class="table-block" id="tbl-res"><div class="table-caption">Table '
    '<span class="tbl-number" data-tbl-id="res"></span>: Mount reactions</div>'
    '<table class="results-table"><tr><td>1</td></tr></table></div>'
)


@pytest.fixture
def report_html(tmp_path):
    notebook = {'cells': [
        md_cell('# Cover Page\ntitle: T\nclient: C\nproject: P\n'
                'docid: D\nrevision: 0'),
        md_cell('# Loads {#sec:loads}'),
        md_cell('The mount loads are computed below.'),
        code_cell("Image('images/x.png', metadata={'ID': 'lc1', "
                  "'caption': 'Load case'})"),
        code_cell("F = equation('F = m * g', id='weight')", EQ_OUTPUT),
        code_cell("create_results_table(sol, table_id='res')", TBL_OUTPUT),
        md_cell('# Assessment\n\nPer @eq:weight and @tbl:res in @sec:loads, '
                'see @fig:lc1 and legacy ref [lc1]. '
                'A [lc1](http://example.com) link keeps working. '
                'Unknown @fig:nope stays literal.'),
    ], 'metadata': {}, 'nbformat': 4, 'nbformat_minor': 5}

    path = tmp_path / 'report.ipynb'
    path.write_text(json.dumps(notebook))
    return NotebookToHTML().convert_notebook(str(path))


class TestCrossReferences:
    def test_equation_reference(self, report_html):
        # note: BeautifulSoup serializes attributes alphabetically
        assert '<a class="equation-ref" href="#eq-weight">Equation (1)</a>' \
            in report_html

    def test_equation_number_injected(self, report_html):
        assert '<span class="eq-number" data-eq-id="weight">(1)</span>' \
            in report_html

    def test_table_reference_and_number(self, report_html):
        assert '<a class="table-ref" href="#tbl-res">Table 1</a>' in report_html
        assert '<span class="tbl-number" data-tbl-id="res">1</span>' \
            in report_html

    def test_section_reference(self, report_html):
        assert '<a class="section-ref" href="#s1">Section 1</a>' in report_html

    def test_section_tag_stripped_from_heading(self, report_html):
        assert '{#sec:loads}' not in report_html
        assert '1. Loads' in report_html

    def test_figure_reference_at_syntax(self, report_html):
        assert '<a href="#fig-lc1" class="figure-ref">Figure 1</a>' \
            in report_html

    def test_legacy_bracket_reference_still_works(self, report_html):
        assert 'data-ref="fig-lc1"' in report_html

    def test_markdown_link_not_hijacked(self, report_html):
        assert 'href="http://example.com"' in report_html
        assert '>Figure 1</a>(http://example.com)' not in report_html

    def test_reference_resolved_inside_equation_comment(self, report_html):
        assert 'Engine weight per <a href="#fig-lc1"' in report_html

    def test_unknown_reference_left_literal(self, report_html):
        assert '@fig:nope' in report_html


class TestRuntimeEmission:
    def _capture_display(self, monkeypatch):
        import calcreport.display as display_mod
        captured = []
        monkeypatch.setattr(display_mod, 'display',
                            lambda obj: captured.append(obj.data))
        return captured

    def test_equation_id_emits_anchor_and_placeholder(self, monkeypatch):
        from calcreport import Q_, equation, u
        captured = self._capture_display(monkeypatch)
        m = Q_(2, u.kg)
        equation('F = m * 2', id='weight')
        assert 'id="eq-weight"' in captured[0]
        assert '<span class="eq-number" data-eq-id="weight"></span>' \
            in captured[0]
        # result line is not numbered
        assert 'eq-number' not in captured[1]

    def test_equation_without_id_unchanged(self, monkeypatch):
        from calcreport import Q_, equation, u
        captured = self._capture_display(monkeypatch)
        m = Q_(2, u.kg)
        equation('F = m * 2')
        assert 'eq-number' not in captured[0]
        assert '<div class="math">' in captured[0]

    def test_results_table_id_and_caption(self):
        from calcreport import create_results_table
        html = create_results_table({'A': 1.0}, table_id='res',
                                    caption='Mount reactions').data
        assert 'id="tbl-res"' in html
        assert 'data-tbl-id="res"' in html
        assert ': Mount reactions' in html

    def test_results_table_without_id_unchanged(self):
        from calcreport import create_results_table
        html = create_results_table({'A': 1.0}).data
        assert 'table-block' not in html
