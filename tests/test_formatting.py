"""Tests for variable-name formatting and the symbol layer."""

import pytest

from calcreport.utils import format_var_name, latexify_symbol_segment


class TestLegacyCompatibility:
    """Exact output strings the 30031 report depends on."""

    def test_simple_subscript(self):
        assert format_var_name('m_engine') == 'm_{\\text{engine}}'

    def test_greek_base_with_subscript(self):
        assert format_var_name('sigma_bolt') == '\\sigma _{\\text{bolt}}'

    def test_greek_prefix_before_uppercase(self):
        assert format_var_name('SigmaF') == '\\Sigma F'
        assert format_var_name('SigmaM') == '\\Sigma M'

    def test_multi_underscore_subscript_kept_verbatim(self):
        assert format_var_name('m_engine_assy') == 'm_{\\text{engine_assy}}'

    def test_digit_subscript(self):
        assert format_var_name('LC_2a') == 'LC_{\\text{2a}}'

    def test_plain_name(self):
        assert format_var_name('g') == 'g'
        assert format_var_name('LC') == 'LC'


class TestSubstringMangling:
    """Words containing hidden Greek names must not be rewritten."""

    @pytest.mark.parametrize('name,expected', [
        ('pitch', 'pitch'),                      # 'pi'/'chi' must not fire
        ('annulus', 'annulus'),                  # 'nu' must not fire
        ('Feta', 'Feta'),                        # 'eta' must not fire
        ('chord', 'chord'),                      # 'chi'/'rho' must not fire
        ('A_net', 'A_{\\text{net}}'),
        ('d_pitch', 'd_{\\text{pitch}}'),
        ('A_annulus', 'A_{\\text{annulus}}'),
    ])
    def test_no_mangling(self, name, expected):
        assert format_var_name(name) == expected

    def test_whole_segment_still_matches(self):
        assert format_var_name('pi') == '\\pi '
        assert format_var_name('F_theta') == 'F_{\\text{\\theta }}'

    def test_lambda_names(self):
        # 'lambda' is a Python keyword only as a bare name; segments work
        assert format_var_name('F_lambda') == 'F_{\\text{\\lambda }}'
        assert format_var_name('lamb') == '\\lambda '


class TestUnicodeGreek:
    def test_unicode_base(self):
        assert format_var_name('σ_max') == '\\sigma _{\\text{max}}'

    def test_unicode_mid_name(self):
        assert format_var_name('Δp') == '\\Delta p'

    def test_unicode_subscript(self):
        assert format_var_name('F_σ') == 'F_{\\text{\\sigma }}'

    def test_lookalike_capital(self):
        # Capital Alpha has no LaTeX macro; renders as Latin A
        assert latexify_symbol_segment('Α') == 'A'

    def test_variant_glyphs(self):
        assert latexify_symbol_segment('φ') == '\\varphi '
        assert latexify_symbol_segment('ϕ') == '\\phi '


class TestPrefixBoundary:
    def test_prefix_needs_boundary(self):
        # lowercase continuation is not a boundary
        assert latexify_symbol_segment('pitch') == 'pitch'
        assert latexify_symbol_segment('etaphase') == 'etaphase'

    def test_digit_is_boundary(self):
        assert latexify_symbol_segment('beta1') == '\\beta 1'

    def test_longest_name_wins(self):
        assert latexify_symbol_segment('vartheta') == '\\vartheta '
        assert latexify_symbol_segment('theta') == '\\theta '
        assert latexify_symbol_segment('eta') == '\\eta '
