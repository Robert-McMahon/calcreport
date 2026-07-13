import re
from .constants import greek_letters, greek_unicode, greek_spelled

# Spelled names longest-first so 'vartheta' wins over 'theta' and 'theta'
# over 'eta' when matching prefixes.
_greek_spelled_by_length = sorted(greek_spelled, key=len, reverse=True)

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

def sanitize_units_latex(tex):
    """Make sympy's rendering of pint units safe for latex2mathml.

    sympy renders a pint Unit as \\mathtt{\\text{...}} with % escaped to
    \\%. latex2mathml cannot render a percent inside \\text{} (a raw % is
    parsed as a comment, \\% is emitted as a literal backslash-percent), so
    hoist a pure-percent unit out into math mode where \\% converts to %.
    """
    return tex.replace(r'\mathtt{\text{\%}}', r'\%')


def replace_greek_letters(text):
    """Replace whole words that match Greek letters with LaTeX equivalents."""
    pattern = r'(' + '|'.join(re.escape(key) for key in greek_letters.keys()) + r')'
    return re.sub(pattern, lambda m: greek_letters[m.group(1)], str(text))

def latexify_symbol_segment(segment):
    """Convert one underscore-delimited piece of a variable name to LaTeX.

    Unicode Greek characters are replaced wherever they occur (they are
    unambiguous). Spelled-out Greek names are replaced only when the whole
    segment matches ('sigma' -> \\sigma) or as a prefix followed by an
    uppercase letter or digit ('SigmaF' -> \\Sigma F), so ordinary words
    like 'pitch' are never mangled by 'pi' or 'chi' hiding inside them.
    """
    for char, macro in greek_unicode.items():
        if char in segment:
            segment = segment.replace(char, macro)
    if segment in greek_spelled:
        return greek_spelled[segment]
    for name in _greek_spelled_by_length:
        if segment.startswith(name):
            rest = segment[len(name):]
            if rest and (rest[0].isupper() or rest[0].isdigit()):
                return greek_spelled[name] + rest
    return segment


def format_var_name(name):
    """Format variable names with proper LaTeX subscripts and Greek letters."""
    if '_' in name:
        base, subscript = name.split('_', 1)
        base = latexify_symbol_segment(base)
        subscript = '_'.join(latexify_symbol_segment(p) for p in subscript.split('_'))
        subscript = escape_latex(subscript)
        return f"{base}_{{\\text{{{subscript}}}}}"
    else:
        return escape_latex(latexify_symbol_segment(name))