from setuptools import setup, find_packages

setup(
    name="calcreport",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'sympy',
        'pint',
        'pandas',
        'numpy',
        'IPython'
    ],
    package_data={
        'calcreport': [
            'export/templates/*',
            'export/templates/js/*',
        ]
    },
    include_package_data=True,
    author="Rob McMahon",
    description="A library for generating engineering calculation reports in Jupyter notebooks",
)