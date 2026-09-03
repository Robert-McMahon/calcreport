"""Tests for document styles: the default engineering report and the
short calculation sheet (title block + revision history, running header,
continuous numbered sections, no TOC)."""

import json
from importlib import resources

import pytest

from calcreport.export.notebooktohtml import NotebookToHTML, STYLE_TEMPLATES


def md_cell(source):
    return {'cell_type': 'markdown', 'metadata': {}, 'source': [source]}


def render(cells, tmp_path, **kwargs):
    notebook = {'cells': cells, 'metadata': {},
                'nbformat': 4, 'nbformat_minor': 5}
    path = tmp_path / 'report.ipynb'
    path.write_text(json.dumps(notebook))
    converter = NotebookToHTML(**kwargs)
    return converter, converter.convert_notebook(str(path))


COVER = md_cell('# Cover Page\ntitle: T\nclient: C\nproject: P\n'
                'docid: D\nrevision: 0')
TITLE_BLOCK = md_cell(
    '# Title Block\ntitle: Torque Check\nclient: Acme\nproject: Reeler\n'
    'docid: 30040-001\nrevision: A\ndate: 2026-09-03\nauthor: R. McMahon\n\n'
    '| Rev | Date | Description | Calc | Chk | App |\n'
    '|-----|------|-------------|------|-----|-----|\n'
    '| A | 2026-09-03 | Issued for use | RMC | | |')
BODY = [
    md_cell('# References\n\n| ID | Reference |\n|----|-----------|\n| [1] | Spec |'),
    md_cell('# Objective\n\nDetermine the torque.'),
    md_cell('# Conclusions\n\nThe torque is fine.'),
]


class TestBundledTemplates:
    @pytest.mark.parametrize('style', sorted(STYLE_TEMPLATES))
    def test_template_and_stylesheet_are_packaged(self, style):
        templates = resources.files('calcreport.export').joinpath('templates')
        template = templates.joinpath(STYLE_TEMPLATES[style])
        assert template.is_file()
        stylesheet = 'calculation.css' if style == 'calculation' else 'styles.css'
        assert f'templates/{stylesheet}' in template.read_text(encoding='utf-8')
        assert templates.joinpath(stylesheet).is_file()


class TestStyleSelection:
    def test_default_is_report(self, tmp_path):
        converter, html = render([COVER, *BODY], tmp_path)
        assert converter.style == 'report'
        assert 'class="cover-page"' in html
        assert 'class="toc"' in html
        assert 'title-block' not in html

    def test_title_block_cell_selects_calculation(self, tmp_path):
        converter, html = render([TITLE_BLOCK, *BODY], tmp_path)
        assert converter.style == 'calculation'
        assert 'id="title-block"' in html

    def test_style_metadata_line_selects_calculation(self, tmp_path):
        cover = md_cell('# Cover Page\ntitle: T\nclient: C\nproject: P\n'
                        'docid: D\nrevision: 0\nstyle: calculation')
        converter, html = render([cover, *BODY], tmp_path)
        assert converter.style == 'calculation'
        assert 'class="cover-page"' not in html
        # the style line is metadata, not content
        assert 'style: calculation' not in html

    def test_command_line_override_wins(self, tmp_path):
        converter, html = render([TITLE_BLOCK, *BODY], tmp_path, style='report')
        assert converter.style == 'report'
        assert 'class="cover-page"' in html
        assert 'class="toc"' in html

    def test_unknown_style_rejected(self, tmp_path):
        with pytest.raises(ValueError, match='memo'):
            render([COVER, *BODY], tmp_path, style='memo')


class TestCalculationLayout:
    @pytest.fixture
    def html(self, tmp_path):
        return render([TITLE_BLOCK, *BODY], tmp_path)[1]

    def test_no_report_front_matter(self, html):
        assert 'class="cover-page"' not in html
        assert 'class="toc"' not in html
        assert 'executive-summary' not in html

    def test_title_block_carries_identity_and_revisions(self, html):
        block = html.split('id="title-block"')[1].split('<h1')[0]
        assert 'Torque Check' in block
        assert '30040-001' in block
        assert 'R. McMahon' in block
        assert 'Revision History' in block
        assert 'Issued for use' in block

    def test_running_header_carries_document_identity(self, html):
        header = html.split('class="running-header"')[1].split('running-footer')[0]
        assert 'Document #: 30040-001' in header
        assert 'Rev: A' in header
        assert 'Client: Acme' in header
        assert 'Project: Reeler' in header
        assert 'Calculation: Torque Check' in header
        assert 'page-number' in html.split('running-footer')[1]

    def test_sections_numbered_from_one(self, html):
        assert '1. References' in html
        assert '2. Objective' in html
        assert '3. Conclusions' in html
        assert 'Title Block' not in html.split('id="title-block"')[1]

    def test_calculation_stylesheet_used(self, html):
        assert 'templates/calculation.css' in html
        assert 'templates/styles.css' not in html
