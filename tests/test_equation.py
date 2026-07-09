"""Tests for the AST-based symbolic equation renderer."""

import pytest

from calcreport import Q_, u
from calcreport.equation import (EquationError, equation, expression_to_latex,
                                 value_to_latex)


class TestExpressionToLatex:
    def test_simple_product(self):
        assert expression_to_latex('m_engine * g') == \
            'm_{\\text{engine}} \\cdot g'

    def test_division_as_fraction(self):
        assert expression_to_latex('F / A_s') == \
            '\\frac{F}{A_{\\text{s}}}'

    def test_power(self):
        assert expression_to_latex('d**2') == 'd^{2}'

    def test_power_of_expression_parenthesized(self):
        assert expression_to_latex('(a + b)**2') == \
            '\\left( a + b \\right)^{2}'

    def test_sum_in_product_parenthesized(self):
        assert expression_to_latex('(a + b) * c') == \
            '\\left( a + b \\right) \\cdot c'

    def test_fraction_operands_not_parenthesized(self):
        assert expression_to_latex('(a + b) / (c - d)') == \
            '\\frac{a + b}{c - d}'

    def test_subtraction_grouping(self):
        assert expression_to_latex('a - (b - c)') == \
            'a - \\left( b - c \\right)'
        assert expression_to_latex('a - b - c') == 'a - b - c'

    def test_sqrt(self):
        assert expression_to_latex('sqrt(a**2 + b**2)') == \
            '\\sqrt{a^{2} + b^{2}}'

    def test_module_function_uses_attribute_name(self):
        assert expression_to_latex('np.sqrt(x)') == '\\sqrt{x}'
        assert expression_to_latex('sp.sin(θ)') == \
            '\\sin\\left( \\theta  \\right)'

    def test_to_is_transparent(self):
        assert expression_to_latex('(m * g).to(u.kN)') == 'm \\cdot g'

    def test_cross_and_dot(self):
        assert expression_to_latex('r_A.cross(F_A)') == \
            'r_{\\text{A}} \\times F_{\\text{A}}'
        assert expression_to_latex('a.dot(b)') == 'a \\cdot b'

    def test_min_max(self):
        assert expression_to_latex('min(a, b)') == \
            '\\min\\left( a, b \\right)'

    def test_unary_minus(self):
        assert expression_to_latex('-a * b') == '-a \\cdot b'

    def test_numeric_subscript(self):
        assert expression_to_latex('F[0]') == 'F_{0}'

    def test_unicode_greek_variables(self):
        assert expression_to_latex('σ_max / FOS') == \
            '\\frac{\\sigma _{\\text{max}}}{FOS}'

    def test_number_constant(self):
        assert expression_to_latex('2 * a') == '2 \\cdot a'

    def test_module_constant(self):
        assert expression_to_latex('np.pi * d**2 / 4') == \
            '\\frac{\\pi  \\cdot d^{2}}{4}'

    def test_unknown_function_operatorname(self):
        assert expression_to_latex('interp(x)') == \
            '\\operatorname{interp}\\left( x \\right)'

    def test_unsupported_syntax_raises(self):
        with pytest.raises(EquationError):
            expression_to_latex('[a for a in b]')
        with pytest.raises(EquationError):
            expression_to_latex('a if b else c')

    def test_invalid_syntax_raises(self):
        with pytest.raises(EquationError):
            expression_to_latex('a +')


class TestValueToLatex:
    def test_scalar_quantity(self):
        assert value_to_latex(Q_(3448, u.kg)) == \
            '3448 \\, \\mathtt{\\text{kg}}'

    def test_float_quantity(self):
        assert '33.8' in value_to_latex(Q_(33.82488, u.kN))

    def test_plain_number(self):
        assert value_to_latex(4) == '4'

    def test_digits_rounds_floats_for_display(self):
        assert value_to_latex(Q_(17.6619276541411, u.mm), digits=4) == \
            '17.66 \\, \\mathtt{\\text{mm}}'
        assert value_to_latex(1.81079725929552, digits=4) == '1.811'

    def test_digits_leaves_integers_exact(self):
        assert value_to_latex(Q_(3448, u.kg), digits=4) == \
            '3448 \\, \\mathtt{\\text{kg}}'


class TestEquation:
    def test_returns_evaluated_result(self, capsys):
        m = Q_(100, u.kg)
        g = Q_(9.81, u.m / u.s**2)
        F = equation('F = m * g', to=u.kN)
        assert F.units == u.kN
        assert abs(F.magnitude - 0.981) < 1e-9

    def test_display_only(self):
        assert equation('F = m * g', evaluate=False) is None

    def test_expression_without_assignment(self):
        x = 3
        assert equation('x * 2') == 6

    def test_math_namespace_available(self):
        A = Q_(245, u.mm**2)
        d = equation('d = sqrt(4 * A / pi)', to=u.mm)
        assert abs(d.magnitude - 17.66) < 0.01

    def test_caller_names_shadow_math_namespace(self):
        pi = 3  # deliberately wrong; caller's binding must win
        assert equation('pi * 2') == 6

    def test_undefined_variable_raises(self):
        with pytest.raises(EquationError, match='Failed to evaluate'):
            equation('nope_zzz * 2')

    def test_multiple_assignment_rejected(self):
        with pytest.raises(EquationError):
            equation('a = b = c * 2')

    def test_symbolic_output_content(self):
        from IPython.display import HTML
        import calcreport.display as display_mod
        captured = []
        original = display_mod.display
        display_mod.display = lambda obj: captured.append(obj.data)
        try:
            m = Q_(100, u.kg)
            g = Q_(9.81, u.m / u.s**2)
            equation('F = m * g', comment='force')
        finally:
            display_mod.display = original
        assert len(captured) == 2  # symbolic line + result line
        assert 'F = m \\cdot g' in captured[0]
        assert 'force' in captured[0]
        assert '981' in captured[1]


class TestCaptureVarName:
    def test_unnamed_expression_raises(self):
        from calcreport import displaymath
        with pytest.raises(ValueError, match='could not determine'):
            displaymath(Q_(1, u.kg) * 2)

    def test_most_recent_name_wins(self):
        import calcreport.display as display_mod
        captured = []
        original = display_mod.render_content
        display_mod.render_content = lambda content, **kw: captured.append(content)
        try:
            from calcreport import displaymath
            aliased_first = 7  # small int, interned
            n_bolts = 7
            displaymath(n_bolts)
        finally:
            display_mod.render_content = original
        assert 'n_{\\text{bolts}}' in captured[0]
