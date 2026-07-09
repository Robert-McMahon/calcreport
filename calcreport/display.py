import html as html_module
import re
import sympy as sp
import inspect
import numpy as np
import pandas as pd
from sympy import Matrix, latex
from IPython.display import display, HTML
from .utils import escape_latex, replace_greek_letters, format_var_name
from .units import u, Q_

DEBUG_MODE = False  

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        print("DEBUG:", *args, **kwargs)

def capture_var_name(func):
    #Capture the variable name of the first argument passed to the function
    def wrapper(*args, **kwargs):
        frame = inspect.currentframe().f_back
        try:
            matches = [name for name, val in frame.f_locals.items() if val is args[0]]
        finally:
            del frame  # avoid reference cycle via the caller's frame
        if not matches:
            raise ValueError(
                f"{func.__name__} could not determine a variable name for its "
                f"argument (type {type(args[0]).__name__}) - assign the value "
                f"to a variable first, e.g. 'F = m * g' then displaymath(F)."
            )
        # On multiple identity matches (e.g. two variables holding the same
        # interned int) prefer the most recently defined one, which is the
        # variable the caller most likely just assigned.
        var_name = matches[-1]
        debug_print(f"Captured variable name: {var_name}")
        return func(var_name, *args, **kwargs)
    return wrapper

@capture_var_name
def displaymath(var_name, expr, comment='', comment_size="small", equation_size="small", line_height="1.2", comment_width="50%"):
    #Generate LaTeX code for the expression and display it
    debug_print(f"Input expression: {expr}")
    debug_print(f"Type of expression: {type(expr)}")
    debug_print(f"Variable name: {var_name}")
    
    formatted_var_name = format_var_name(var_name)
    debug_print(f"Formatted variable name: {formatted_var_name}")
    # Check if expr is a SymPy expression
    if isinstance(expr, sp.Basic):
        debug_print("Expression is a SymPy Basic type.")
   
        if isinstance(expr, sp.Matrix):
            debug_print("Expression is a SymPy Matrix.")
            # If it's a SymPy matrix, format it as an equation
            expr = replace_greek_letters(expr)
            equation_latex = f"{formatted_var_name} = {sp.latex(expr)}"
    
        elif isinstance(expr, sp.core.relational.Equality):
            debug_print("Expression is a SymPy Equality.")
            # If it's a SymPy Equality, format it as an equation
            expr = sp.sympify(replace_greek_letters(expr))
            debug_print(f"Formatted expression: {expr}")
            equation_latex = f"{sp.latex(expr.lhs)} = {sp.latex(expr.rhs)}"
        
        else:
            debug_print("Expression is a SymPy expression but not a Matrix.")
            # If it's another SymPy expression, format it as an equation
            expr = replace_greek_letters(expr)
            debug_print(f"Formatted expression: {expr}")
            equation_latex = f"{formatted_var_name} = {sp.latex(expr)}"
            debug_print(f"Equation LaTeX: {equation_latex}")
  
    elif isinstance(expr, sp.Matrix):
        debug_print("Expression is a SymPy Matrix with units.")
        # If it's a SymPy matrix with units, format each element
        matrix_latex = replace_greek_letters(sp.latex(expr.applyfunc(lambda x: x)))
        equation_latex = f"{formatted_var_name} = {matrix_latex}"

    elif isinstance(expr, u.Quantity):
        debug_print("Expression is a pint Quantity.")

        if isinstance(expr.magnitude, np.ndarray):
            debug_print("Magnitude is a NumPy array.")
            debug_print(f"Sympified expression: {expr}")
            equation_latex = f"{formatted_var_name} = {sp.latex(Matrix(expr.magnitude))} \\, {sp.latex(expr.units)}"

        else:
            debug_print("Magnitude is not a NumPy array.")
            equation_latex = f"{formatted_var_name} = {sp.latex(expr.magnitude)} \\, {sp.latex(expr.units)}"
    
    else:
        debug_print("Expression is a regular variable.")

        if isinstance(expr, (int, float)):
            value_latex = sp.latex(expr)
        
        else:
            value_latex = str(expr)

        equation_latex = f"{formatted_var_name} = {value_latex}"

    debug_print(f"Generated LaTeX: {equation_latex}")
    render_content(equation_latex, comment=comment, content_type='latex', equation_size=equation_size, comment_size=comment_size, line_height=line_height, comment_width=comment_width)

def latex_to_mathml(latex_source):
    """Convert LaTeX to MathML for script-free rendering.

    Native MathML displays in any Chromium surface (browsers, VS Code
    webviews, marimo) without JavaScript, and the report template's MathJax
    build (tex-mml-chtml) typesets it for the PDF. The original LaTeX is
    kept in a data-latex attribute for debugging and tooling.

    Returns None if conversion fails (caller falls back to raw delimiters).
    """
    try:
        from latex2mathml.converter import convert
        mathml = convert(latex_source, display='block')
    except Exception as e:
        debug_print(f"latex2mathml conversion failed for {latex_source!r}: {e}")
        return None
    # MathML defaults single-letter identifiers to italic; TeX renders
    # capital Greek upright - match TeX so \Sigma stays an upright sigma.
    # latex2mathml emits capital Greek as entities &#x00391;-&#x003A9;.
    mathml = re.sub(r'<mi>(&#x0039[1-9A-F];|&#x003A[0-9];|[Α-Ω])</mi>',
                    r'<mi mathvariant="normal">\1</mi>', mathml)
    # Left-align within the flex layout instead of MathML's default centring
    return mathml.replace(
        '<math ',
        f'<math style="text-align:left;margin:0" '
        f'data-latex="{html_module.escape(latex_source, quote=True)}" ',
        1)


def render_content(content, comment='', content_type='latex', equation_size='small',
                  comment_size='small', line_height='1.2', comment_width='50%',
                  eq_id=None):
    """Render LaTeX equations or HTML content with optional comments.

    LaTeX content is emitted as MathML, which renders without JavaScript
    everywhere (marimo, VS Code notebook outputs, Jupyter, the exported
    report). If conversion fails the raw \\[..\\] form is emitted and the
    report's MathJax still typesets it.

    eq_id makes the equation referenceable: the block gets the anchor
    'eq-<eq_id>' and an equation-number placeholder that the exporter fills
    in document order ('@eq:<eq_id>' elsewhere becomes 'Equation (N)').
    """
    if content_type == 'latex':
        content_html = latex_to_mathml(content) or rf"\[ {content} \]"
    else:
        content_html = content
    anchor = f' id="eq-{eq_id}"' if eq_id else ''
    number = (f'<span class="eq-number" data-eq-id="{eq_id}"></span>'
              if eq_id else '')
    html_code = f"""
    <div class="math"{anchor}>
        <div class="math-equation">
         {content_html}
        </div>
        {number}
        <div class="math-comment">
         {comment}
        </div>
    </div>
    """
    display(HTML(html_code))

def create_results_table(*solutions, case_names=None, custom_classes="results-table",
                         table_id=None, caption=''):
    """Create an HTML table from multiple solution dictionaries.

    table_id makes the table referenceable: the block gets the anchor
    'tbl-<table_id>' and a caption 'Table N: <caption>' whose number the
    exporter fills in document order ('@tbl:<table_id>' elsewhere becomes
    'Table N').
    """

    if case_names is None:
        case_names = [f"Case {i+1}" for i in range(len(solutions))]

    data = []
    for sol, case in zip(solutions, case_names):
        row = {'Load Case': case}
        for key, value in sol.items():
            value = round(float(value), 2)
            value = Q_(value, u.kN)
            row[str(key)] = f"{value:.2f~P}"
        data.append(row)

    df = pd.DataFrame(data)
    styled_table = df.style.hide(axis='index')
    html_table = styled_table.to_html(table_id="results_table")
    html_table = html_table.replace(r"<table", f'<table class={custom_classes}')

    if table_id:
        caption_text = f": {caption}" if caption else ""
        html_table = (
            f'<div class="table-block" id="tbl-{table_id}">'
            f'<div class="table-caption">Table '
            f'<span class="tbl-number" data-tbl-id="{table_id}"></span>'
            f'{caption_text}</div>'
            f'{html_table}</div>'
        )

    return HTML(html_table)