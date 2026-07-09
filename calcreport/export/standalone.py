"""Inline external assets so an exported report is a single portable HTML file.

Local stylesheets become <style> blocks, local scripts become inline
<script> blocks, and local images become base64 data URIs. Remote (http/https)
references such as the MathJax CDN script are left untouched, so viewing a
standalone report still needs internet access for math rendering.
"""

import base64
import mimetypes
from importlib import resources
from pathlib import Path

from bs4 import BeautifulSoup


def _is_remote(ref: str) -> bool:
    # Site-absolute paths (/foo/bar.js) are skipped too: they depend on a
    # server root, so there is no reliable filesystem location to inline from.
    return ref.startswith(('http://', 'https://', '//', 'data:', '/'))


def _resolve_asset(ref: str, search_dirs) -> bytes | None:
    """Find a relative asset reference, searching each directory in order,
    then the assets bundled with the package."""
    for directory in search_dirs:
        candidate = Path(directory) / ref
        if candidate.is_file():
            return candidate.read_bytes()

    packaged = resources.files('calcreport.export').joinpath(ref)
    if packaged.is_file():
        return packaged.read_bytes()
    return None


def _to_data_uri(data: bytes, ref: str) -> str:
    mime, _ = mimetypes.guess_type(ref)
    mime = mime or 'application/octet-stream'
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def inline_assets(soup: BeautifulSoup, search_dirs) -> None:
    """Inline every local stylesheet, script, and image in the document.

    Modifies the soup in place. Unresolvable references are left as-is with
    a warning so the output degrades no worse than the non-standalone export.

    Args:
        soup: Parsed HTML document.
        search_dirs: Directories to try (in order) when resolving relative
            asset paths; the packaged template assets are the final fallback.
    """
    for link in soup.find_all('link', rel='stylesheet'):
        href = link.get('href', '')
        if not href or _is_remote(href):
            continue
        css = _resolve_asset(href, search_dirs)
        if css is None:
            print(f"Warning: could not resolve stylesheet '{href}', leaving external reference")
            continue
        style = soup.new_tag('style')
        style.string = css.decode('utf-8')
        link.replace_with(style)

    for script in soup.find_all('script', src=True):
        src = script['src']
        if _is_remote(src):
            continue
        js = _resolve_asset(src, search_dirs)
        if js is None:
            print(f"Warning: could not resolve script '{src}', leaving external reference")
            continue
        del script['src']
        # A literal </script> inside the JS would terminate the inline block
        # early; escape it (valid inside JS string literals, where it occurs).
        script.string = js.decode('utf-8').replace('</script', '<\\/script')

    for img in soup.find_all('img', src=True):
        src = img['src']
        if _is_remote(src):
            continue
        data = _resolve_asset(src, search_dirs)
        if data is None:
            print(f"Warning: could not resolve image '{src}', leaving external reference")
            continue
        img['src'] = _to_data_uri(data, src)
