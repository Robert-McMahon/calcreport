import threading
import time
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# Console message logged by templates/js/mathjax-config.js when the
# MathJax -> paged.js -> MathJax render pipeline has fully finished.
RENDER_COMPLETE_MESSAGE = 'Final MathJax typeset complete'


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def _serve_directory(directory: Path):
    """Serve a directory on an ephemeral localhost port in a daemon thread."""
    server = HTTPServer(('127.0.0.1', 0), partial(_QuietHandler, directory=str(directory)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def html_to_pdf(html_path: str, pdf_path: str, timeout: int = 120):
    """
    Render an exported report HTML file to PDF using headless Chromium.

    Serves the HTML file's directory over a temporary localhost HTTP server
    (paged.js loads stylesheets via XHR, which browsers block on file://),
    waits for paged.js pagination and MathJax typesetting to complete, then
    prints to PDF. Relative assets (templates/, images/) are resolved against
    the HTML file's directory, so the HTML must be written next to those
    folders - same requirement as viewing it in a browser.

    Args:
        html_path: Path to the exported HTML report.
        pdf_path: Path where the PDF should be saved.
        timeout: Maximum seconds to wait for rendering to complete.
    """
    try:
        from playwright.sync_api import sync_playwright, Error as PlaywrightError
    except ImportError:
        raise RuntimeError(
            "PDF export requires playwright. Install it with: uv add playwright"
        )

    html_path = Path(html_path).resolve()
    pdf_path = Path(pdf_path)

    server = _serve_directory(html_path.parent)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}/{html_path.name}"

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except PlaywrightError as e:
            raise RuntimeError(
                "Could not launch Chromium. Install it with: playwright install chromium"
            ) from e

        try:
            page = browser.new_page()

            render_complete = []
            page.on('console', lambda msg: render_complete.append(True)
                    if RENDER_COMPLETE_MESSAGE in msg.text else None)

            print(f"Rendering {html_path.name} in headless Chromium...")
            page.goto(url)

            # Wait for paged.js to produce at least one page
            page.wait_for_selector('.pagedjs_page', timeout=timeout * 1000)

            # Wait for the render-complete console message from the default
            # template; fall back to page-count stability for custom templates
            # that don't log it.
            deadline = time.time() + timeout
            prev_count = -1
            stable_polls = 0
            while time.time() < deadline and not render_complete and stable_polls < 4:
                count = page.locator('.pagedjs_page').count()
                stable_polls = stable_polls + 1 if count == prev_count else 0
                prev_count = count
                page.wait_for_timeout(500)

            # Ensure webfonts (MathJax fonts in particular) are loaded
            page.evaluate('document.fonts.ready')

            page_count = page.locator('.pagedjs_page').count()
            print(f"Layout complete: {page_count} pages. Writing PDF...")

            page.pdf(
                path=str(pdf_path),
                prefer_css_page_size=True,
                print_background=True,
                display_header_footer=False,
            )
        finally:
            browser.close()

    server.shutdown()
    print(f"PDF document saved to: {pdf_path}")
