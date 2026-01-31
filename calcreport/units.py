import pint
from pint.delegates.formatter._compound_unit_helpers import sort_by_dimensionality

# Initialize pint
u = pint.UnitRegistry()
u.formatter.default_format = '~P'

#Sort units by dimensionality eg so instead of mN we get Nm
u.formatter.default_sort_func = sort_by_dimensionality
Q_ = u.Quantity

# Silence NEP 18 warning
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    Q_([])