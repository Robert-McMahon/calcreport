"""Portable semantic Markdown outputs for Quarto and notebook frontends.

The objects in this module expose the standard ``text/markdown`` MIME type so
notebook frontends can render them and document engines can retain their
equation, table, caption, and cross-reference semantics.
"""

import ast
import re
from collections.abc import Iterable, Sequence

from .equation import EquationError, expression_to_latex, value_to_latex
from .utils import format_var_name


_MISSING = object()
_LABEL_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")


class PortableMarkdown:
    """Markdown content that notebook and document engines can consume."""

    def __init__(self, markdown: str):
        if not isinstance(markdown, str):
            raise TypeError("markdown must be a string")
        self.markdown = markdown

    def _repr_mimebundle_(self, include=None, exclude=None):
        """Return the semantic Markdown MIME representation."""
        return {"text/markdown": self.markdown}

    def _repr_markdown_(self):
        return self.markdown

    def __str__(self):
        return self.markdown


def _label(kind: str, identifier: str | None) -> str:
    if identifier is None:
        return ""
    prefix = f"{kind}-"
    label = identifier if identifier.startswith(prefix) else prefix + identifier
    if not _LABEL_RE.fullmatch(label):
        raise ValueError(
            "Markdown labels must begin with a letter and contain only letters, "
            "numbers, underscores, hyphens, periods, or colons"
        )
    return f" {{#{label}}}"


def quantity_markdown(symbol: str, value, comment: str = "",
                      digits: int | None = 4) -> PortableMarkdown:
    """Render a named value as portable display math.

    ``symbol`` is a Python-style variable name such as ``m_engine``; it uses
    the same subscript and Greek-letter formatting as :func:`equation`.
    """
    equation_latex = (
        f"{format_var_name(symbol)} = {value_to_latex(value, digits=digits)}"
    )
    markdown = f"$$\n{equation_latex}\n$$"
    if comment:
        markdown += f"\n\n*{comment}*"
    return PortableMarkdown(markdown)


def _symbolic_equation(expr: str) -> str:
    try:
        parsed = ast.parse(expr.strip(), mode="exec").body
    except SyntaxError as error:
        raise EquationError(f"Invalid expression {expr!r}: {error.msg}") from error

    if len(parsed) != 1:
        raise EquationError(
            f"equation_markdown() expects one expression or assignment, got {expr!r}"
        )
    statement = parsed[0]
    if isinstance(statement, ast.Assign):
        if (len(statement.targets) != 1
                or not isinstance(statement.targets[0], ast.Name)):
            raise EquationError(
                "equation_markdown() supports a single 'name = expression' "
                f"assignment, got {expr!r}"
            )
        name = statement.targets[0].id
        rhs = ast.unparse(statement.value)
        return f"{format_var_name(name)} = {expression_to_latex(rhs)}"
    if isinstance(statement, ast.Expr):
        return expression_to_latex(ast.unparse(statement.value))
    raise EquationError(
        f"equation_markdown() expects an expression or assignment, got {expr!r}"
    )


def equation_markdown(expr: str, result=_MISSING, *, comment: str = "",
                      id: str | None = None, digits: int | None = 4,
                      to=None) -> PortableMarkdown:
    """Render symbolic calculation source and its result as a Quarto equation.

    The expression syntax matches :func:`equation`. If ``result`` is supplied,
    it is appended to the symbolic line and may optionally be converted with
    ``to``. Supplying ``id='weight'`` creates Quarto label ``eq-weight``.
    """
    symbolic = _symbolic_equation(expr)
    if result is not _MISSING:
        if to is not None:
            result = result.to(to)
        symbolic += f" = {value_to_latex(result, digits=digits)}"
    markdown = f"$$\n{symbolic}\n$$" + _label("eq", id)
    if comment:
        markdown += f"\n\n*{comment}*"
    return PortableMarkdown(markdown)


def _table_cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _alignment_marker(alignment: str) -> str:
    markers = {
        "left": ":---",
        "center": ":---:",
        "right": "---:",
    }
    try:
        return markers[alignment]
    except KeyError as error:
        raise ValueError("alignment must be 'left', 'center', or 'right'") from error


def table_markdown(headers: Sequence, rows: Iterable[Sequence], *,
                   caption: str = "", id: str | None = None,
                   align: Sequence[str] | None = None) -> PortableMarkdown:
    """Create a semantic Markdown table with an optional Quarto caption/id."""
    headers = tuple(headers)
    if not headers:
        raise ValueError("headers must not be empty")
    if align is None:
        align = ("left",) * len(headers)
    else:
        align = tuple(align)
    if len(align) != len(headers):
        raise ValueError("align must contain one value per header")

    lines = [
        "| " + " | ".join(_table_cell(value) for value in headers) + " |",
        "|" + "|".join(_alignment_marker(value) for value in align) + "|",
    ]
    for row in rows:
        row = tuple(row)
        if len(row) != len(headers):
            raise ValueError("each row must contain one value per header")
        lines.append("| " + " | ".join(_table_cell(value) for value in row) + " |")

    if caption or id:
        lines.extend(("", f": {caption}{_label('tbl', id)}"))
    return PortableMarkdown("\n".join(lines))
