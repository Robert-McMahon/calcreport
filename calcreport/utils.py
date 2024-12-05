import re
from .constants import greek_letters

def escape_latex(text):
    """Escape LaTeX special characters in text, except underscores."""
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def replace_greek_letters(text):
    """Replace whole words that match Greek letters with LaTeX equivalents."""
    pattern = r'(' + '|'.join(re.escape(key) for key in greek_letters.keys()) + r')'
    return re.sub(pattern, lambda m: greek_letters[m.group(1)], str(text))

def format_var_name(name):
    """Format variable names with proper LaTeX subscripts and Greek letters."""
    if '_' in name:
        base, subscript = name.split('_', 1)
        base = replace_greek_letters(base)
        subscript = replace_greek_letters(subscript)
        subscript = escape_latex(subscript)
        return f"{base}_{{\\text{{{subscript}}}}}"
    else:
        name = replace_greek_letters(name)
        return escape_latex(name)