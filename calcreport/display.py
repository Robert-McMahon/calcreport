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
        var_name = [name for name, val in frame.f_locals.items() if val is args[0]][0]
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

def render_content(content, comment='', content_type='latex', equation_size='small', 
                  comment_size='small', line_height='1.2', comment_width='50%'):
    """Render LaTeX equations or HTML content with optional comments."""
    content_html = rf"\[ {content} \]" if content_type == 'latex' else content
    html_code = f"""
    <script type="text/javascript" async src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-MML-AM_CHTML"></script>
    <script type="text/javascript">
         MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
    </script>
    <div class="math">
        <div class="math-equation">
         {content_html}
        </div>
        <div class="math-comment">
         {comment}
        </div>
    </div>
    """
    display(HTML(html_code))

def create_results_table(*solutions, case_names=None, custom_classes="results-table"):
    """Create an HTML table from multiple solution dictionaries."""

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
    
    return HTML(html_table)