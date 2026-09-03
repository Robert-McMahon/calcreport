"""Tests for the calcreport-init project scaffolder."""

import ast

from calcreport.newproject import create_project, parse_project_name


class TestParseProjectName:
    def test_full_convention(self):
        assert parse_project_name('30040-GENESISWEST-STRIKELUBE') == \
            ('30040', 'GENESISWEST', 'STRIKELUBE')

    def test_multiword_project(self):
        assert parse_project_name('30050-ACME-ENGINE-SKID') == \
            ('30050', 'ACME', 'ENGINE-SKID')

    def test_number_only(self):
        jobnum, client, project = parse_project_name('30060')
        assert jobnum == '30060'

    def test_no_convention(self):
        jobnum, client, project = parse_project_name('scratch')
        assert project == 'scratch'


class TestCreateProject:
    def test_scaffold(self, tmp_path):
        directory = create_project(tmp_path / '30040-GENESISWEST-STRIKELUBE',
                                   sync=False, git=False)
        assert (directory / 'pyproject.toml').exists()
        assert (directory / 'README.md').exists()
        assert (directory / '.gitignore').exists()
        assert (directory / 'images').is_dir()

        notebook = directory / '30040-001.py'
        assert notebook.exists()
        source = notebook.read_text()
        # valid python, marimo skeleton, metadata prefilled, no leftovers
        ast.parse(source)
        assert 'app = marimo.App()' in source
        assert 'client: GENESISWEST' in source
        assert 'docid: 30040-001' in source
        assert '{{' not in source

        pyproject = (directory / 'pyproject.toml').read_text()
        assert 'calcreport[marimo]' in pyproject
        assert '{{' not in pyproject

    def test_client_override(self, tmp_path):
        directory = create_project(tmp_path / '30041-FOO-BAR',
                                   client='Foo Industries Pty Ltd',
                                   sync=False, git=False)
        assert 'client: Foo Industries Pty Ltd' in \
            (directory / '30041-001.py').read_text()

    def test_default_style_is_report(self, tmp_path):
        directory = create_project(tmp_path / '30043-FOO-BAR', sync=False, git=False)
        source = (directory / '30043-001.py').read_text()
        assert '# Cover Page' in source
        assert '# Executive Summary' in source

    def test_calculation_style(self, tmp_path):
        directory = create_project(tmp_path / '30044-FOO-BAR', style='calculation',
                                   sync=False, git=False)
        source = (directory / '30044-001.py').read_text()
        ast.parse(source)
        assert '# Title Block' in source
        assert 'docid: 30044-001' in source
        for heading in ('# References', '# Objective', '# Inputs to Calculations',
                        '# Calculations', '# Conclusions'):
            assert heading in source
        assert '# Cover Page' not in source
        assert '{{' not in source

    def test_unknown_style_rejected(self, tmp_path):
        import pytest
        with pytest.raises(ValueError):
            create_project(tmp_path / '30045-FOO-BAR', style='memo',
                           sync=False, git=False)

    def test_refuses_non_empty_directory(self, tmp_path):
        target = tmp_path / '30042-X-Y'
        target.mkdir()
        (target / 'existing.txt').write_text('data')
        import pytest
        with pytest.raises(SystemExit):
            create_project(target, sync=False, git=False)
