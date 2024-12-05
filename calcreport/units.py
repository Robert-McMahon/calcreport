import pint

# Initialize pint
u = pint.UnitRegistry()
u.formatter.default_format = '~P'
Q_ = u.Quantity

# Silence NEP 18 warning
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    Q_([])