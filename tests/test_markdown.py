import pytest

from calcreport import (PortableMarkdown, Q_, equation_markdown,
                        quantity_markdown, table_markdown, u)
from calcreport.equation import EquationError


def test_portable_markdown_exposes_semantic_mime_type():
    output = PortableMarkdown("**result**")
    bundle = output._repr_mimebundle_()

    assert bundle == {"text/markdown": "**result**"}
    assert output._repr_markdown_() == "**result**"
    assert str(output) == "**result**"


def test_quantity_markdown_uses_calcreport_symbol_and_unit_formatting():
    output = quantity_markdown("m_engine", Q_(3448, u.kg), "Engine mass")

    assert "m_{\\text{engine}} = 3448" in output.markdown
    assert "\\mathtt{\\text{kg}}" in output.markdown
    assert "*Engine mass*" in output.markdown


def test_equation_markdown_renders_result_and_quarto_label():
    output = equation_markdown(
        "F_engine = m_engine * g",
        Q_(33818.88, u.N),
        to=u.kN,
        digits=4,
        comment="Static engine weight",
        id="engine-weight",
    )

    assert "F_{\\text{engine}} = m_{\\text{engine}} \\cdot g" in output.markdown
    assert "33.82" in output.markdown
    assert "{#eq-engine-weight}" in output.markdown
    assert "*Static engine weight*" in output.markdown


def test_equation_markdown_can_render_symbolic_expression_only():
    output = equation_markdown("m * g")
    assert output.markdown == "$$\nm \\cdot g\n$$"


def test_equation_markdown_rejects_multiple_assignment():
    with pytest.raises(EquationError):
        equation_markdown("a = b = c")


def test_table_markdown_creates_caption_label_and_alignment():
    output = table_markdown(
        ("Item", "Value"),
        (("Engine mass", "3448 kg"), ("Engine weight", "33.82 kN")),
        align=("left", "right"),
        caption="Calculation summary",
        id="summary",
    )

    assert "|:---|---:|" in output.markdown
    assert "| Engine weight | 33.82 kN |" in output.markdown
    assert ": Calculation summary {#tbl-summary}" in output.markdown


def test_table_markdown_validates_shape_and_alignment():
    with pytest.raises(ValueError, match="one value per header"):
        table_markdown(("A", "B"), ((1,),))
    with pytest.raises(ValueError, match="alignment"):
        table_markdown(("A",), ((1,),), align=("decimal",))
