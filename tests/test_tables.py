from pathlib import Path

import pandas as pd
import pytest


def test_create_table_preserves_mixed_unit_dataframe_values():
    from calcreport import create_table

    df = pd.DataFrame({
        'Pressure': ['500 kPa'],
        'Flow': ['9.60 L/min'],
        'Re': [172],
    })
    html = create_table(df, table_id='network',
                        caption='Network results').data

    assert 'id="tbl-network"' in html
    assert 'data-tbl-id="network"' in html
    assert ': Network results' in html
    assert '500 kPa' in html
    assert '9.60 L/min' in html
    assert 'kN' not in html


def test_create_table_accepts_raw_html():
    from calcreport import create_table

    raw = '<table class="custom"><tr><td>value</td></tr></table>'
    html = create_table(raw, table_id='raw').data

    assert raw in html
    assert 'id="tbl-raw"' in html


def test_create_table_accepts_as_raw_html_renderer():
    from calcreport import create_table

    class Renderer:
        def as_raw_html(self, inline_css):
            assert inline_css is False
            return '<table><tr><td>rendered</td></tr></table>'

    html = create_table(Renderer(), table_id='rendered').data
    assert 'rendered' in html
    assert 'id="tbl-rendered"' in html


def test_create_table_rejects_unsupported_input():
    from calcreport import create_table

    with pytest.raises(TypeError, match='pandas DataFrame'):
        create_table(object())


def test_pagedjs_detached_parent_regression_guard_is_bundled():
    import calcreport

    template = (Path(calcreport.__file__).parent / 'export' / 'templates' /
                'js' / 'paged.polyfill.js').read_text()
    recursive_call = (
        'this.lastChildCheck(parentElement.lastElementChild, rootElement);'
    )
    guard = 'if (!parentElement.parentNode)'

    assert recursive_call in template
    assert guard in template
    assert template.index(recursive_call) < template.index(guard)
