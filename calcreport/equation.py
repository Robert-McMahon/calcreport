"""Render calculations symbolically from the same expression that computes them.

`equation("F = m_engine * g", ...)` parses the expression, renders the
symbolic form (F = m_engine · g) using the shared variable-name formatting,
evaluates the right-hand side against the caller's variables (pint
quantities, sympy objects, plain numbers), optionally renders the result,
and returns it:

    F_gravity = equation('F_gravity = m_engine * g', to=u.kN,
                         comment='Engine weight')

The formula shown in the report can therefore never drift from the
computation - they are the same source text.
"""

import ast
import inspect

import numpy as np
import sympy as sp

from .display import render_content
from .units import u
from .utils import escape_latex, format_var_name


class EquationError(ValueError):
    """Raised when an expression cannot be rendered or evaluated."""


# Operator precedence for deciding when parentheses are needed.
_PREC_ADD = 1      # + -
_PREC_MUL = 2      # * / @
_PREC_UNARY = 3    # -x
_PREC_POW = 4      # **
_PREC_ATOM = 5     # names, numbers, calls, sqrt/frac output

_FUNCTION_NAMES = {
    'sin': '\\sin', 'cos': '\\cos', 'tan': '\\tan',
    'asin': '\\arcsin', 'acos': '\\arccos', 'atan': '\\arctan',
    'arcsin': '\\arcsin', 'arccos': '\\arccos', 'arctan': '\\arctan',
    'sinh': '\\sinh', 'cosh': '\\cosh', 'tanh': '\\tanh',
    'log': '\\ln', 'ln': '\\ln', 'log10': '\\log',
    'exp': '\\exp', 'min': '\\min', 'max': '\\max',
}

# Method calls rendered as binary operators: x.cross(y), x.dot(y)
_METHOD_OPERATORS = {'cross': '\\times', 'dot': '\\cdot'}

# Method calls that are transparent in the symbolic form (unit bookkeeping,
# not mathematics): x.to(u.kN) renders as just x.
_TRANSPARENT_METHODS = {'to', 'to_base_units', 'to_reduced_units', 'm_as'}

# Functions available during evaluation without an import, so expressions
# like 'sqrt(4 * A / pi)' just work. The caller's own names take precedence.
# numpy versions are used because they operate on pint quantities.
_MATH_NAMESPACE = {
    'sqrt': np.sqrt, 'sin': np.sin, 'cos': np.cos, 'tan': np.tan,
    'arcsin': np.arcsin, 'arccos': np.arccos, 'arctan': np.arctan,
    'asin': np.arcsin, 'acos': np.arccos, 'atan': np.arctan,
    'sinh': np.sinh, 'cosh': np.cosh, 'tanh': np.tanh,
    'log': np.log, 'ln': np.log, 'log10': np.log10, 'exp': np.exp,
    'abs': abs, 'min': min, 'max': max, 'pi': np.pi, 'e': np.e,
}


def _number_to_latex(value):
    return sp.latex(sp.sympify(value))


def _parenthesize(latex, needed):
    return f"\\left( {latex} \\right)" if needed else latex


def _call_to_latex(node, parent_prec=0):
    func = node.func
    args = node.args

    # Method call: x.to(...), x.cross(y), ...
    if isinstance(func, ast.Attribute):
        method = func.attr
        receiver = func.value
        if method in _TRANSPARENT_METHODS:
            # The call disappears; the receiver takes its place directly,
            # so it parenthesizes against the original surroundings.
            return _to_latex(receiver, parent_prec), _PREC_ATOM
        if method in _METHOD_OPERATORS and len(args) == 1:
            left = _to_latex(receiver, _PREC_MUL)
            right = _to_latex(args[0], _PREC_MUL + 1)
            return f"{left} {_METHOD_OPERATORS[method]} {right}", _PREC_MUL
        # np.sqrt(x), math.sin(x): use the attribute name as the function
        name = method
    elif isinstance(func, ast.Name):
        name = func.id
    else:
        raise EquationError(f"Cannot render call: {ast.unparse(node)}")

    arg_latex = ', '.join(_to_latex(a, 0) for a in args)
    if name == 'sqrt':
        return f"\\sqrt{{{arg_latex}}}", _PREC_ATOM
    if name == 'abs':
        return f"\\left| {arg_latex} \\right|", _PREC_ATOM
    if name in _FUNCTION_NAMES:
        return f"{_FUNCTION_NAMES[name]}\\left( {arg_latex} \\right)", _PREC_ATOM
    return f"\\operatorname{{{escape_latex(name)}}}\\left( {arg_latex} \\right)", _PREC_ATOM


def _to_latex(node, parent_prec=0):
    """Convert an AST expression node to LaTeX.

    parent_prec is the binding strength of the surrounding context; the
    result is parenthesized when this node binds more loosely.
    """
    if isinstance(node, ast.Name):
        return format_var_name(node.id)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return _number_to_latex(node.value)
        raise EquationError(f"Cannot render constant: {node.value!r}")

    if isinstance(node, ast.BinOp):
        op = type(node.op)
        if op is ast.Div:
            top = _to_latex(node.left, 0)
            bottom = _to_latex(node.right, 0)
            return f"\\frac{{{top}}}{{{bottom}}}"
        if op is ast.Pow:
            base = _to_latex(node.left, _PREC_POW + 1)
            exponent = _to_latex(node.right, 0)
            return f"{base}^{{{exponent}}}"
        if op in (ast.Add, ast.Sub):
            symbol = '+' if op is ast.Add else '-'
            left = _to_latex(node.left, _PREC_ADD)
            # a - (b + c) and a - (b - c) both need parentheses
            right = _to_latex(node.right, _PREC_ADD + (op is ast.Sub))
            return _parenthesize(f"{left} {symbol} {right}",
                                 parent_prec > _PREC_ADD)
        if op in (ast.Mult, ast.MatMult):
            left = _to_latex(node.left, _PREC_MUL)
            right = _to_latex(node.right, _PREC_MUL)
            return _parenthesize(f"{left} \\cdot {right}",
                                 parent_prec > _PREC_MUL)
        raise EquationError(f"Unsupported operator: {ast.unparse(node)}")

    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.USub):
            operand = _to_latex(node.operand, _PREC_UNARY)
            return _parenthesize(f"-{operand}", parent_prec > _PREC_UNARY)
        raise EquationError(f"Unsupported operator: {ast.unparse(node)}")

    if isinstance(node, ast.Call):
        latex, prec = _call_to_latex(node, parent_prec)
        return _parenthesize(latex, parent_prec > prec)

    if isinstance(node, ast.Attribute):
        # Module-qualified constants: np.pi, math.e - render the attribute
        # name through the symbol layer ('pi' -> \pi).
        return format_var_name(node.attr)

    if isinstance(node, ast.Subscript):
        base = _to_latex(node.value, _PREC_ATOM)
        if isinstance(node.slice, ast.Constant):
            return f"{base}_{{{node.slice.value}}}"
        raise EquationError(f"Cannot render subscript: {ast.unparse(node)}")

    raise EquationError(
        f"Cannot render '{ast.unparse(node)}' symbolically "
        f"({type(node).__name__} is not supported)")


def expression_to_latex(source: str) -> str:
    """Render a Python expression string as LaTeX (symbolic form only)."""
    try:
        tree = ast.parse(source, mode='eval')
    except SyntaxError as e:
        raise EquationError(f"Invalid expression {source!r}: {e.msg}") from e
    return _to_latex(tree.body)


def _round_for_display(sympified, digits):
    """Limit floats to `digits` significant figures; leave exact values alone."""
    if digits is None:
        return sympified
    if isinstance(sympified, sp.MatrixBase):
        return sympified.applyfunc(lambda x: _round_for_display(x, digits))
    if isinstance(sympified, sp.Float):
        return sp.Float(sympified, digits)
    return sympified


def value_to_latex(value, digits=None):
    """Render an evaluated result (pint/sympy/number) as LaTeX.

    digits limits floats to that many significant figures for display
    (None = full precision). Integers and exact values are untouched.
    """
    if isinstance(value, u.Quantity):
        magnitude = value.magnitude
        if isinstance(magnitude, np.ndarray):
            magnitude_sym = sp.Matrix(magnitude)
        else:
            magnitude_sym = sp.sympify(magnitude)
        magnitude_latex = sp.latex(_round_for_display(magnitude_sym, digits))
        return f"{magnitude_latex} \\, {sp.latex(value.units)}"
    if isinstance(value, (sp.Basic, sp.MatrixBase)):
        return sp.latex(_round_for_display(value, digits))
    if isinstance(value, np.ndarray):
        return sp.latex(_round_for_display(sp.Matrix(value), digits))
    if isinstance(value, (int, float)):
        return sp.latex(_round_for_display(sp.sympify(value), digits))
    return escape_latex(str(value))


def equation(expr: str, comment: str = '', to=None, show_result: bool = True,
             evaluate: bool = True, digits: int = 4, **style):
    """Render a calculation symbolically, evaluate it, and return the result.

    Args:
        expr: The calculation as Python source, e.g. 'F = m_engine * g'.
            With a 'name =' left-hand side the equation renders as
            'F = m_engine · g'; without one, only the right-hand side is
            rendered and shown.
        comment: Comment displayed beside the symbolic equation.
        to: Optional pint unit to convert the result to, e.g. u.kN.
        show_result: Also render 'F = <value>' below the symbolic form.
        evaluate: Evaluate the expression against the caller's variables.
            With evaluate=False the equation is display-only (returns None).
        digits: Significant figures for the displayed result (display only -
            the returned value keeps full precision). None = full precision.
        **style: Passed through to render_content (equation_size etc.).

    Returns:
        The evaluated result, so the caller can assign it:
        F = equation('F = m_engine * g', to=u.kN)
    """
    frame = inspect.currentframe().f_back
    try:
        name = None
        rhs_source = expr.strip()
        try:
            parsed = ast.parse(rhs_source, mode='exec').body
        except SyntaxError as e:
            raise EquationError(f"Invalid expression {expr!r}: {e.msg}") from e
        if len(parsed) == 1 and isinstance(parsed[0], ast.Assign):
            targets = parsed[0].targets
            if len(targets) != 1 or not isinstance(targets[0], ast.Name):
                raise EquationError(
                    f"equation() supports a single 'name = expression' "
                    f"assignment, got {expr!r}")
            name = targets[0].id
            rhs_node = parsed[0].value
            rhs_source = ast.unparse(rhs_node)
        elif len(parsed) == 1 and isinstance(parsed[0], ast.Expr):
            rhs_node = parsed[0].value
        else:
            raise EquationError(
                f"equation() expects an expression or a single assignment, "
                f"got {expr!r}")

        rhs_latex = _to_latex(rhs_node)
        lhs_latex = format_var_name(name) if name else None
        symbolic = f"{lhs_latex} = {rhs_latex}" if name else rhs_latex
        render_content(symbolic, comment=comment, **style)

        if not evaluate:
            return None

        code = compile(ast.Expression(body=rhs_node), '<equation>', 'eval')
        eval_globals = {**_MATH_NAMESPACE, **frame.f_globals}
        try:
            result = eval(code, eval_globals, frame.f_locals)
        except Exception as e:
            raise EquationError(
                f"Failed to evaluate {rhs_source!r}: {e}") from e
        if to is not None:
            result = result.to(to)
        if show_result:
            result_latex = value_to_latex(result, digits=digits)
            result_line = (f"{lhs_latex} = {result_latex}"
                           if name else result_latex)
            render_content(result_line, **style)
        return result
    finally:
        del frame
