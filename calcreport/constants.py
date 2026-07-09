# Unicode Greek characters -> LaTeX. Unambiguous: these can be used directly
# in Python identifiers (e.g. σ_max = ...) and are replaced wherever they
# appear in a name. Trailing spaces keep concatenation safe ('\sigma F').
greek_unicode = {
    'α': '\\alpha ', 'β': '\\beta ', 'γ': '\\gamma ', 'δ': '\\delta ',
    'ε': '\\varepsilon ', 'ϵ': '\\epsilon ', 'ζ': '\\zeta ', 'η': '\\eta ',
    'θ': '\\theta ', 'ϑ': '\\vartheta ', 'ι': '\\iota ', 'κ': '\\kappa ',
    'λ': '\\lambda ', 'μ': '\\mu ', 'ν': '\\nu ', 'ξ': '\\xi ',
    'π': '\\pi ', 'ϖ': '\\varpi ', 'ρ': '\\rho ', 'ϱ': '\\varrho ',
    'σ': '\\sigma ', 'ς': '\\varsigma ', 'τ': '\\tau ', 'υ': '\\upsilon ',
    'φ': '\\varphi ', 'ϕ': '\\phi ', 'χ': '\\chi ', 'ψ': '\\psi ',
    'ω': '\\omega ',
    'Γ': '\\Gamma ', 'Δ': '\\Delta ', 'Θ': '\\Theta ', 'Λ': '\\Lambda ',
    'Ξ': '\\Xi ', 'Π': '\\Pi ', 'Σ': '\\Sigma ', 'Υ': '\\Upsilon ',
    'Φ': '\\Phi ', 'Ψ': '\\Psi ', 'Ω': '\\Omega ',
    # Capital Greek letters that share their glyph with a Latin letter
    # (no LaTeX macro exists for these).
    'Α': 'A', 'Β': 'B', 'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Ι': 'I',
    'Κ': 'K', 'Μ': 'M', 'Ν': 'N', 'Ο': 'O', 'Ρ': 'P', 'Τ': 'T', 'Χ': 'X',
}

# Spelled-out Greek names -> LaTeX, matched only against whole name segments
# or as a segment prefix followed by an uppercase letter/digit (so 'SigmaF'
# -> 'ΣF' but 'pitch' is never mangled by 'pi' or 'chi'). Includes 'pi' and
# 'lambda' properly ('_pi'/'lamb' in the legacy dict below were workarounds
# for substring matching and the lambda keyword).
greek_spelled = {
    'alpha': '\\alpha ', 'beta': '\\beta ', 'gamma': '\\gamma ',
    'delta': '\\delta ', 'epsilon': '\\epsilon ', 'varepsilon': '\\varepsilon ',
    'zeta': '\\zeta ', 'eta': '\\eta ', 'theta': '\\theta ',
    'vartheta': '\\vartheta ', 'iota': '\\iota ', 'kappa': '\\kappa ',
    'lambda': '\\lambda ', 'lamb': '\\lambda ', 'mu': '\\mu ', 'nu': '\\nu ',
    'xi': '\\xi ', 'omicron': '\\omicron ', 'pi': '\\pi ', 'varpi': '\\varpi ',
    'rho': '\\rho ', 'varrho': '\\varrho ', 'sigma': '\\sigma ',
    'varsigma': '\\varsigma ', 'tau': '\\tau ', 'upsilon': '\\upsilon ',
    'phi': '\\phi ', 'varphi': '\\varphi ', 'chi': '\\chi ', 'psi': '\\psi ',
    'omega': '\\omega ',
    'Gamma': '\\Gamma ', 'Delta': '\\Delta ', 'Theta': '\\Theta ',
    'Lambda': '\\Lambda ', 'Lamb': '\\Lambda ', 'Xi': '\\Xi ', 'Pi': '\\Pi ',
    'Sigma': '\\Sigma ', 'Upsilon': '\\Upsilon ', 'Phi': '\\Phi ',
    'Psi': '\\Psi ', 'Omega': '\\Omega ',
    'Alpha': 'A', 'Beta': 'B', 'Epsilon': 'E', 'Zeta': 'Z', 'Eta': 'H',
    'Iota': 'I', 'Kappa': 'K', 'Mu': 'M', 'Nu': 'N', 'Omicron': 'O',
    'Rho': 'P', 'Tau': 'T', 'Chi': 'X',
}

# Legacy substring-replacement dict, kept for replace_greek_letters()
# backwards compatibility. Prefer greek_unicode/greek_spelled above.
greek_letters= {
    "alpha": "\\alpha ",
    "beta": "\\beta ",
    "gamma": "\\gamma ",
    "delta": "\\delta ",
    "epsilon": "\\epsilon ",
    "varepsilon": "\\varepsilon ",
    "zeta": "\\zeta ",
    "theta": "\\theta ",
    "vartheta": "\\vartheta ",
    "iota": "\\iota ",
    "kappa": "\\kappa ",
    "mu": "\\mu ",
    "nu": "\\nu ",
    "xi": "\\xi ",
    "omicron": "\\omicron ",
    "_pi": "\\pi ",
    "varpi": "\\varpi ",
    "rho": "\\rho ",
    "varrho": "\\varrho ",
    "sigma": "\\sigma ",
    "varsigma": "\\varsigma ",
    "tau": "\\tau ",
    "upsilon": "\\upsilon ",
    "phi": "\\phi ",
    "varphi": "\\varphi ",
    "chi": "\\chi ",
    "omega": "\\omega ",
    "eta": "\\eta ",
    "psi": "\\psi ",
    "lamb": "\\lambda ",
    "Alpha": "\\Alpha ",
    "Beta": "\\Beta ",
    "Gamma": "\\Gamma ",
    "Delta": "\\Delta ",
    "Epsilon": "\\Epsilon ",
    "Zeta": "\\Zeta ",
    "Theta": "\\Theta ",
    "Iota": "\\Iota ",
    "Kappa": "\\Kappa ",
    "Mu": "\\Mu ",
    "Nu": "\\Nu ",
    "Xi": "\\Xi ",
    "Omicron": "\\Omicron ",
    "Pi": "\\Pi ",
    "Rho": "\\Rho ",
    "Sigma": "\\Sigma ",
    "Tau": "\\Tau ",
    "Upsilon": "\\Upsilon ",
    "Phi": "\\Phi ",
    "Chi": "\\Chi ",
    "Omega": "\\Omega ",
    "Eta": "\\Eta ",
    "Psi": "\\Psi ",
    "Lamb": "\\Lambda ",
}
