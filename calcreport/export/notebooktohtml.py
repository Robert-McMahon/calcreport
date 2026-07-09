import json
import re
from pathlib import Path
from importlib import resources
import argparse
import cmarkgfm
from cmarkgfm.cmark import Options as cmarkgfmOptions
from bs4 import BeautifulSoup
import ast

'''
to start a local server to serve the content on port 8000, run the following command in the terminal:
python -m http.server 8000
'''

options = (cmarkgfmOptions.CMARK_OPT_UNSAFE)

DEBUG_MODE = False
debug_log = []

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        debug_log.append(' '.join(str(a) for a in args))
        print(*args, **kwargs)

# Metadata keys recognised in cover page / appendix markdown source lines
# (marimo notebooks have no per-cell metadata, so `key: value` lines in the
# cell body are the marimo equivalent of Jupyter cell metadata).
INLINE_METADATA_KEYS = {'title', 'client', 'project', 'docid', 'revision',
                        'filename', 'date', 'author'}


def extract_inline_metadata(source: str):
    """Pull `key: value` metadata lines out of markdown source.

    Returns (metadata dict, source with those lines removed). Only lines
    whose key is in INLINE_METADATA_KEYS are treated as metadata.
    """
    metadata, kept = {}, []
    for line in source.split('\n'):
        m = re.match(r'^([A-Za-z_]+):\s*(.+?)\s*$', line)
        if m and m.group(1).lower() in INLINE_METADATA_KEYS:
            metadata[m.group(1).lower()] = m.group(2)
        else:
            kept.append(line)
    return metadata, '\n'.join(kept)


def unwrap_marimo_container(html_content: str) -> str:
    """Remove the flex-layout div marimo wraps around cell outputs.

    `marimo export ipynb` consolidates a cell's displayed outputs inside
    <div style='display: flex;...flex-direction: column;...'>. The flex
    styling interferes with paged.js fragmentation, so unwrap it and keep
    the children.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    top = [el for el in soup.contents if getattr(el, 'name', None)]
    if (len(top) == 1 and top[0].name == 'div' and not top[0].get('class')
            and 'display: flex' in (top[0].get('style') or '')
            and 'flex-direction: column' in (top[0].get('style') or '')):
        return ''.join(str(child) for child in top[0].contents)
    return html_content


class NotebookCell:
    def __init__(self, cell_type, source, output, metadata=None, level=None, section_number=None, header_id=None):
        self.cell_type = cell_type  # markdown, code
        self.source = source
        self.output = output
        self.metadata = metadata or {}
        self.level = level  # For headers: 1 for h1, 2 for h2, 3 etc, or None for non-headers
        self.section_number = section_number
        self.header_id = header_id
        self.category = None  # cover_page, executive_summary, body, appendix

class DocumentStructure:
    def __init__(self):
        self.cover_page = None
        self.header_footer = None
        self.executive_summary = None
        self.body_cells = []
        self.appendices = []
        self.headers = []
        self.max_header_level = 6

    def get_section_number(self, current_numbers):
        """Generate section number from current numbering state."""
        return '.'.join(str(n) for n in current_numbers if n > 0)

class NotebookToHTML:
    def __init__(self, template_path=None):
        self.debug_mode = DEBUG_MODE
        self.structure = DocumentStructure()
        self.template = self._load_template(template_path)
        self.figure_refs = {}   # figure id -> number
        self.eq_refs = {}       # equation id -> number
        self.tbl_refs = {}      # table id -> number
        self.sec_refs = {}      # section id -> {'number': '1.2', 'anchor': 's1s2'}

    def _load_template(self, template_path=None):
        """Load the report template.

        Resolution order: explicit path argument, then a project-local
        ./templates/report_template.html (allows per-project overrides),
        then the template bundled with the package.
        """
        if template_path is not None:
            print(f"Loading template file: {template_path}")
            return Path(template_path).read_text(encoding='utf-8')

        local_template = Path('./templates/report_template.html')
        if local_template.exists():
            print(f"Loading project template: {local_template}")
            return local_template.read_text(encoding='utf-8')

        packaged = resources.files('calcreport.export').joinpath('templates/report_template.html')
        print("Loading bundled template (no ./templates/report_template.html found)")
        return packaged.read_text(encoding='utf-8')
    
    def _apply_inline_metadata(self, nb_cell):
        """Merge `key: value` lines from the cell source into its metadata.

        Jupyter cell metadata wins over inline source metadata, so existing
        notebooks are unaffected; marimo notebooks (which have no per-cell
        metadata) supply title/client/docid/etc. as lines in the cell body.
        """
        inline_meta, stripped_source = extract_inline_metadata(nb_cell.source)
        if inline_meta:
            nb_cell.metadata = {**inline_meta, **nb_cell.metadata}
            nb_cell.source = stripped_source

    def extract_structure(self, cells):
        """
        Extract and categorize document structure from notebook cells.
        Handles arbitrary header levels and special sections.
        """
        # Initialize section numbering array (index 0 unused for easier level mapping)
        current_numbers = [0] * (self.structure.max_header_level + 1)
        current_category = "body"

        print("\nExtracting document structure...")
        
        for cell in cells:
            nb_cell = NotebookCell(
                cell_type = cell['cell_type'],
                source = ''.join(cell['source']),
                metadata = cell.get('metadata', {}),
                output = cell.get('outputs', {})
            )
            if cell['cell_type'] == 'markdown':
                lines = nb_cell.source.split('\n')
                for line in lines:
                    # Process special sections first
                    if line.startswith('# Cover Page'):
                        nb_cell.category = "cover_page"
                        self._apply_inline_metadata(nb_cell)
                        self.structure.cover_page = nb_cell

                    elif line.startswith('# Executive Summary'):
                        nb_cell.category = "executive_summary"
                        self.structure.executive_summary = nb_cell
                        break
                        
                    elif line.startswith('# Appendix'):
                        nb_cell.category = "appendix"
                        self._apply_inline_metadata(nb_cell)
                        self.structure.appendices.append(nb_cell)
                        break
                    
                    # Process regular headers
                    header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
                    if header_match:
                        level = len(header_match.group(1))
                        text = header_match.group(2).strip()

                        # Skip if this is a special section we already handled
                        if any(x in text for x in ['Cover Page', 'Executive Summary', 'Appendix']):
                            continue

                        # A '{#sec:id}' suffix makes the section referenceable
                        # via '@sec:id'; strip it from the displayed text.
                        sec_tag = re.search(r'\s*\{#sec:([A-Za-z0-9_-]+)\}\s*$', text)
                        sec_ref_id = None
                        if sec_tag:
                            sec_ref_id = sec_tag.group(1)
                            text = text[:sec_tag.start()].strip()
                            nb_cell.source = nb_cell.source.replace(
                                line, f"{header_match.group(1)} {text}")

                        # Update section numbers
                        current_numbers[level] += 1
                        # Reset all deeper levels
                        for i in range(level + 1, len(current_numbers)):
                            current_numbers[i] = 0
                            
                        # Generate section number (eg 1.2.3)
                        section_numbers = current_numbers[1:level + 1]
                        section_number = ".".join(str(n) for n in section_numbers)

                        # Generate section ID (eg s1s2s3)
                        section_id = 's' + 's'.join(str(n) for n in section_numbers)
                        # Update cell properties
                        nb_cell.level = level
                        nb_cell.section_number = section_number
                        nb_cell.header_id = section_id
                        
                        # Add to headers list
                        header_info={
                            'level': level,
                            'text': text,
                            'id': section_id,
                            'section_number': section_number,
                            'category': current_category
                        }
                        self.structure.headers.append(header_info)
                        if sec_ref_id:
                            self.sec_refs[sec_ref_id] = {
                                'number': section_number,
                                'anchor': section_id,
                            }
                        break
                                    
            # Add to appropriate content collection
            if nb_cell.category not in ["cover_page", "executive_summary", "appendix"]:
                self.structure.body_cells.append(nb_cell)
        
        for header in self.structure.headers:
            self.debug_print(f"Level {header['level']}: ({header['text']}) (ID: {header['id']})")

    def generate_header_footer(self):
        """
        Generate header and footer HTML content using metadata.
        
        Args:
            metadata: Dictionary containing document metadata
        '''
        """
        metadata = self.structure.cover_page.metadata
        meta_html = ['<div class="running-header">']
        meta_html.append('<div class="header-content">')
        meta_html.append('<div class="header-left">Robert McMahon BEng(Mech), Consultant Engineer')
        meta_html.append('</div>')
        meta_html.append('<div class="header-center">{}</div>'.format(metadata.get('title', '')))
        meta_html.append('<div class="header-right">')
        meta_html.append('<div class="client">Client: {}</div>'.format(metadata.get('client', '')))
        meta_html.append('<div class="project">Project: {}</div>'.format(metadata.get('project', '')))
        meta_html.append('</div>')
        meta_html.append('</div>')
        meta_html.append('</div>')
        meta_html.append('<div class="running-footer">')
        meta_html.append('<div class="footer-content">')
        meta_html.append('<div class="footer-left">')
        meta_html.append('<div class="docid">Document ID: {}</div>'.format(metadata.get('docid', '')))
        meta_html.append('<div class="revision">Revision: {}</div>'.format(metadata.get('revision', '')))
        meta_html.append('</div>')
        meta_html.append('<div class="footer-right">')
        meta_html.append('<div class="page-count">Page <span class="page-number"></span> of <span class="page-total"></span></div>')
        meta_html.append('</div>')
        meta_html.append('</div>')
        meta_html.append('</div>')

        return '\n'.join(meta_html) 

    def collect_figure_references(self, cells) -> dict:
        """
        Collect figure references and assign numbers to them.
        Should be called before processing cells to ensure all figure numbers are assigned.
        
        Args:
            cells: List of notebook cells to process
            
        Returns:
            Dictionary mapping figure IDs to their assigned numbers
        """
        figure_refs = {}
        figure_counter = 0
        
        for cell in cells:
            if cell['cell_type'] == 'code':
                source = ''.join(cell['source']) 
                image_pattern = r"Image\(['\"]([^'\"]+)['\"](?:\s*,\s*metadata\s*=\s*(\{[^}]+\}))?"
                image_match = re.search(image_pattern, source)
                
                if image_match and image_match.groups()[1]:
                    metadata_str = image_match.group(2)
                    try:
                        metadata = ast.literal_eval(metadata_str)
                        if 'ID' in metadata:
                            figure_counter += 1
                            figure_refs[metadata['ID']] = figure_counter
                    except (ValueError, SyntaxError) as e:
                        self.debug_print(f"Error parsing figure metadata: {e}")
        return figure_refs

    def collect_output_references(self, cells):
        """Assign document-order numbers to referenceable equations and tables.

        equation(id=...) and create_results_table(table_id=...) leave
        data-eq-id / data-tbl-id placeholders in their output HTML; numbering
        happens here rather than at execution time because marimo executes
        cells in dependency order, not document order.
        """
        for cell in cells:
            if cell['cell_type'] != 'code':
                continue
            for output in cell.get('outputs', []):
                html = ''.join(output.get('data', {}).get('text/html', ''))
                for eq_id in re.findall(r'data-eq-id="([^"]+)"', html):
                    if eq_id not in self.eq_refs:
                        self.eq_refs[eq_id] = len(self.eq_refs) + 1
                for tbl_id in re.findall(r'data-tbl-id="([^"]+)"', html):
                    if tbl_id not in self.tbl_refs:
                        self.tbl_refs[tbl_id] = len(self.tbl_refs) + 1

    def resolve_cross_references(self, text: str) -> str:
        """Replace @fig/@eq/@tbl/@sec references with numbered links."""
        def replace(match):
            kind, ref_id = match.groups()
            if kind == 'fig' and ref_id in self.figure_refs:
                return (f'<a href="#fig-{ref_id}" class="figure-ref">'
                        f'Figure {self.figure_refs[ref_id]}</a>')
            if kind == 'eq' and ref_id in self.eq_refs:
                return (f'<a href="#eq-{ref_id}" class="equation-ref">'
                        f'Equation ({self.eq_refs[ref_id]})</a>')
            if kind == 'tbl' and ref_id in self.tbl_refs:
                return (f'<a href="#tbl-{ref_id}" class="table-ref">'
                        f'Table {self.tbl_refs[ref_id]}</a>')
            if kind == 'sec' and ref_id in self.sec_refs:
                sec = self.sec_refs[ref_id]
                return (f'<a href="#{sec["anchor"]}" class="section-ref">'
                        f'Section {sec["number"]}</a>')
            print(f"Warning: unresolved cross-reference '@{kind}:{ref_id}'")
            return match.group(0)

        return re.sub(r'@(fig|eq|tbl|sec):([A-Za-z0-9_-]+)', replace, text)

    def inject_reference_numbers(self, html_content: str) -> str:
        """Fill the empty number placeholders left by equation()/tables."""
        html_content = re.sub(
            r'(<span class="eq-number" data-eq-id="([^"]+)">)(</span>)',
            lambda m: f'{m.group(1)}({self.eq_refs.get(m.group(2), "?")}){m.group(3)}',
            html_content)
        html_content = re.sub(
            r'(<span class="tbl-number" data-tbl-id="([^"]+)">)(</span>)',
            lambda m: f'{m.group(1)}{self.tbl_refs.get(m.group(2), "?")}{m.group(3)}',
            html_content)
        return html_content

    def generate_toc_html(self):
            """Generate HTML for table of contents with support for multiple header levels."""
            toc_html = ['<nav class="toc"><ol class="toc-list">']
            current_level = 0
            
            # Add executive summary if exists
            if self.structure.executive_summary:
                toc_html.append(
                    '<li class="front-matter"><a href="#executive-summary">'
                    '<span class="title">Executive Summary'
                    '<span class="leaders"></span></span>'
                    '<span class="pagenumber"></span></a></li>'
                )
            
            # Add numbered sections
            for header in self.structure.headers:
                if header['category'] != 'appendix':
                    level = header['level']
                    section_prefix = f"{header['section_number']}. "
                    
                    # Adjust nested lists based on level difference
                    while current_level < level - 1:
                        toc_html.append('<ol>')
                        current_level += 1
                    while current_level > level - 1:
                        toc_html.append('</ol></li>')
                        current_level -= 1
                    
                    toc_html.append(
                        f'<li><a href="#{header["id"]}">'
                        f'<span class="title">{section_prefix}{header["text"]}'
                        f'<span class="leaders"></span></span>'
                        f'<span class="pagenumber"></span></a>'
                    )
                    
                    # Don't close li yet if this level might have children
                    if not any(h['level'] > level for h in self.structure.headers):
                        toc_html.append('</li>')
            
            # Close any remaining open lists
            while current_level > 0:
                toc_html.append('</ol></li>')
                current_level -= 1
            
            # Add appendices
            if self.structure.appendices:
                for i, appendix in enumerate(self.structure.appendices):
                    letter = chr(65 + i)
                    toc_html.append(
                        f'<li class="appendix-entry"><a href="#appendix-{letter.lower()}">'
                        f'<span class="title">Appendix {letter} - {appendix.metadata.get("title", "")}'
                        f'<span class="leaders"></span></span>'
                        f'<span class="pagenumber"></span></a></li>'
                    )
            
            toc_html.append('</ol></nav>')
            return '\n'.join(toc_html)

    def generate_cover_page(self):
            """Generate cover page HTML using metadata from cover page cell."""
            if not self.structure.cover_page:
                return ""
            source_content = self.structure.cover_page.source
            # Convert markdown to HTML
            html = cmarkgfm.github_flavored_markdown_to_html(source_content, options)

            # Process the HTML with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            revision_table = soup.find('table')
            
            metadata = self.structure.cover_page.metadata
            return f'''
            <div class="cover-page">
                <div class="cover-content">
                    <h1>{metadata.get('client', 'Client')}</h1>
                    <h1>{metadata.get('project', 'Project')}</h1>
                    <h1>{metadata.get('title', 'Document Title')}</h1>
                    <div class="cover-info">
                        <p>Document ID: {metadata.get('docid', '')}</p>
                        </div>
                </div>
                <div class="revision-table">  
                    {revision_table}
                </div>
            </div>
            '''

    def generate_executive_summary(self):
        """Generate executive summary page HTML."""
        if not self.structure.executive_summary:
            return ""
            
        content = cmarkgfm.github_flavored_markdown_to_html(self.structure.executive_summary.source, options)
        return f'''
        <div class="executive-summary" id="executive-summary">
            {content}
        </div>
        '''

    def generate_appendix_pages(self):
        """
        Generate cover pages for appendices.
        Gets appendix information from the document structure.
        """
        if not self.structure.appendices:
            return []

        def get_appendix_content(appendix, letter):
            """Helper function to process appendix content and metadata"""
            metadata = appendix.metadata
            # Build additional metadata sections
            metadata_sections = []
            if 'title' in metadata:
               metadata_sections.append(
                   f'<div class="appendix-subtitle">{metadata["title"]}</div>'
                ) 
            if 'filename' in metadata:
                metadata_sections.append(
                    f'<div class="appendix-filename">File: {metadata["filename"]}</div>'
                )
            if 'date' in metadata:
                metadata_sections.append(
                    f'<div class="appendix-date">Date: {metadata["date"]}</div>'
                )
            if 'revision' in metadata:
                metadata_sections.append(
                    f'<div class="appendix-revision">Revision: {metadata["revision"]}</div>'
                )
            
            # Combine metadata sections if they exist
            metadata_html = '\n'.join(metadata_sections) if metadata_sections else ''
            
            return f'''
            <div class="appendix-cover">
                <div class="appendix-content" id="appendix-{letter.lower()}">
                    <div class="appendix-title">Appendix {letter}</div>
                    {metadata_html}
                </div>
            </div>
            '''
        
        return [
            get_appendix_content(appendix, chr(65 + i))
            for i, appendix in enumerate(self.structure.appendices)
        ]

    def process_markdown_cell(self, cell: NotebookCell, figure_refs: dict = None) -> str:
        """
        Process a markdown cell, handling section numbers, figure references, and header IDs.
        
        Args:
            cell: NotebookCell instance containing the markdown content
            figure_refs: Dictionary mapping figure IDs to their numbers
        
        Returns:
            Processed HTML content
        """
        if figure_refs is None:
            figure_refs = {}
        # Get the source content
        source_content = cell.source

        # Replace @fig/@eq/@tbl/@sec references with links
        source_content = self.resolve_cross_references(source_content)

        # Replace legacy [id] figure references with links. The (?!\() guard
        # keeps markdown links whose text happens to be a figure id intact.
        source_content = re.sub(
            r'\[([^\]]+)\](?!\()',
            lambda m: f'<a href="#fig-{m.group(1)}" data-ref="fig-{m.group(1)}" class="figure-ref">Figure {figure_refs.get(m.group(1), "?")}</a>'
            if m.group(1) in figure_refs else m.group(0),
            source_content
        )
        
        # Update headers with section numbers if this is a header cell
        if cell.level is not None and cell.section_number:
            source_content = self.update_markdown_with_section_numbers(cell, source_content)
        
        # Convert markdown to HTML
        html = cmarkgfm.github_flavored_markdown_to_html(source_content, options)
        # Process the HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        current_section = []
        
        # Add IDs to headers and ensure proper section numbering
        for tag_level in range(1, 7):
            headers = soup.find_all(f'h{tag_level}')
            if headers:
                for header in headers:
                    original_text = header.text.strip()
                    # Extract section number and text
                    section_match = re.match(r'^(\d+(\.\d+)*)\.\s*(.+)$', original_text)
                    if section_match:
                        section_nums = [int(n) for n in section_match.group(1).split('.')]
                        header_text = section_match.group(3).strip()
                        
                        # Update current section context
                        if tag_level == 1:
                            current_section = section_nums
                        elif len(section_nums) == tag_level:
                            current_section = section_nums
                    
                    
                    # Debug current structure headers
                    for h in self.structure.headers:
                        # Extract section numbers from header ID
                        h_section_nums = [int(n) for n in h['id'].lstrip('s').split('s')]
                        
                        # Check if text, level, and section hierarchy match
                        if (h['text'] == header_text and 
                            h['level'] == tag_level and 
                            h_section_nums[:tag_level-1] == section_nums[:tag_level-1]):
                            header['id'] = h['id']
                            header['class'] = header.get('class', [])
                            if isinstance(header['class'], str):
                                header['class'] = header['class'].split()
                            if 'section-number' not in header['class']:
                                header['class'].append('section-number')                        
                            break
                    else:
                        self.debug_print("No match found for this header")
        
        # Add appropriate classes based on cell category
        classes = ['markdown-cell']
        if cell.category:
            classes.append(f"{cell.category}-content")
        
        # Wrap the processed content in a div with appropriate classes
        return f'<div class="{" ".join(classes)}">{str(soup)}</div>'

    def update_markdown_with_section_numbers(self, cell: NotebookCell, source: str = None) -> str:
        """
        Update markdown headers with section numbers.
        This is now a helper method for process_markdown_cell.

        Args:
            cell: NotebookCell instance to update
            source: Markdown to update (defaults to cell.source); passing the
                already figure-ref-substituted text keeps those substitutions.

        Returns:
            Updated markdown content
        """
        if source is None:
            source = cell.source
        if not cell.level or not cell.section_number:
            return source

        lines = source.split('\n')
        updated_lines = []

        for line in lines:
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                hashes = header_match.group(1)
                text = header_match.group(2).strip()
                # Find matching header in our structure
                for header in self.structure.headers:
                    if (header['text'] == text and 
                        header['level'] == len(hashes) and 
                        header['id'] == cell.header_id):
                        line = f"{hashes} {header['section_number']}. {text}"
                        break
            updated_lines.append(line)
    
        return '\n'.join(updated_lines)

    def process_code_cell(self, cell: NotebookCell, figure_refs: dict = None) -> str:
        """
        Process a code cell, handling output and figure references.
        
        Args:
            cell: NotebookCell instance containing the code content
            figure_refs: Dictionary mapping figure IDs to their numbers
        
        Returns:
            Processed HTML content or empty string if no content to display
        """
        if figure_refs is None:
            figure_refs = {}
        # Check if this is an image cell
        image_pattern = r"Image\(['\"]([^'\"]+)['\"](?:\s*,\s*metadata\s*=\s*(\{[^}]+\}))?"
        image_match = re.search(image_pattern, cell.source)

        if image_match:
            image_url = image_match.group(1)
            metadata_str = image_match.group(2) if image_match.groups()[1] is not None else "{}"
            
            try:
                metadata = ast.literal_eval(metadata_str)
                fig_id = metadata.get('ID', '')
                caption = metadata.get('caption', '')
                fig_num = figure_refs.get(fig_id, '?')
                
                # Create figure HTML with explicit number
                return f'''
                    <figure class="figure" id="fig-{fig_id}" data-label="fig-{fig_id}">
                        <img src="{image_url}" alt="{caption}" />
                        <figcaption>Figure {fig_num}: {caption}</figcaption>
                    </figure>
                '''
            except (ValueError, SyntaxError) as e:
                return f'<figure class="figure"><img src="{image_url}" alt="figure" /></figure>'

        # Process cell outputs
        if len(cell.output) > 0:
            outputs = []

            for output in cell.output:
                # Stream outputs (print statements) and errors have no 'data' key
                data = output.get('data', {})
                if 'text/html' in data:
                    html_content = ''.join(data['text/html'])

                    # Remove marimo's flex wrapper, then MathJax scripts
                    html_content = unwrap_marimo_container(html_content)
                    html_content = self.clean_mathjax_content(html_content)

                    # Strip the notebook-preview math sizing so the report
                    # stylesheet controls equation typography
                    html_content = html_content.replace(
                        'font-size:1.2em;line-height:normal;', '')

                    # Fill equation/table numbers and resolve @refs (so
                    # comments can say 'per @eq:weight' or 'see @fig:mesh')
                    html_content = self.inject_reference_numbers(html_content)
                    html_content = self.resolve_cross_references(html_content)

                    # Add to outputs if content remains after cleaning
                    if html_content.strip():
                        outputs.append(html_content)

                elif 'image/png' in data:
                    # Generated images (e.g. matplotlib charts) are embedded
                    # in the notebook as base64 - inline them as data URIs
                    png_b64 = ''.join(data['image/png']).strip()
                    outputs.append(
                        f'<img class="cell-image" alt="chart" '
                        f'src="data:image/png;base64,{png_b64}" />'
                    )

            if outputs:
                return self.wrap_code_output('\n'.join(outputs))

        return
    
    def clean_mathjax_content(self, html_content: str) -> str:
        """
        Clean MathJax-related scripts and unnecessary content from HTML.
        
        Args:
            html_content: Raw HTML content containing MathJax elements
        
        Returns:
            Cleaned HTML content
        """
        # Remove MathJax script tags
        html_content = re.sub(
            r'<script[^>]*MathJax[^>]*>.*?</script>\s*',
            '',
            html_content
        )
        
        # Remove MathJax function calls
        html_content = re.sub(
            r'<script type="text/javascript">\s*MathJax\.Hub\.Queue\([^\)]+\);\s*</script>',
            '',
            html_content
        )
        
        return html_content

    def wrap_code_output(self, content: str) -> str:
        """
        Wrap code output in appropriate HTML structure.
        
        Args:
            content: Processed HTML content to wrap
        
        Returns:
            Wrapped HTML content
        """
        # Add appropriate classes based on content type
        if 'math-equation' in content:
            wrapper_class = 'math-group'
        else:
            wrapper_class = 'code-output'
        
        return f'''
            <div class="{wrapper_class}">
                {content}
            </div>
        '''

    def debug_print(self, *args, **kwargs):
        """
        Print debug information if debug mode is enabled.
        """
        if hasattr(self, 'debug_mode') and self.debug_mode:
            print(*args, **kwargs)
            debug_log.append(' '.join(str(a) for a in args))

    def convert_notebook(self, notebook_path: str) -> str:
        """Convert Jupyter notebook to HTML."""
        # Read the notebook file
        print(f"Reading notebook file: {notebook_path}")
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        # First pass: collect all figure IDs and assign numbers
        figure_refs = self.collect_figure_references(notebook['cells'])
        self.figure_refs = figure_refs

        # Assign document-order numbers to equations and tables
        self.collect_output_references(notebook['cells'])

        # Extract document structure (also registers {#sec:id} references)
        self.extract_structure(notebook['cells'])

        # Generate document components
        cover_page = self.generate_cover_page()
        header_footer = self.generate_header_footer()
        executive_summary = self.generate_executive_summary()
        toc = self.generate_toc_html()
        

        # Process body content
        content = []
        cell_counter = 1
        for cell in self.structure.body_cells:
            if cell.cell_type == 'markdown':
                processed_content = self.process_markdown_cell(cell, figure_refs)
                content.append(processed_content)
                cell_counter += 1
            elif cell.cell_type == 'code':
                processed_content = self.process_code_cell(cell, figure_refs)
                if processed_content:
                    content.append(processed_content)
                    cell_counter += 1

        # Process appendix content
        appendix_pages = self.generate_appendix_pages()

        # Combine all components
        final_content = '\n'.join(filter(None, [
            header_footer,
            cover_page,
            executive_summary,
            toc,
            '\n'.join(content),
            '\n'.join(appendix_pages) if appendix_pages else ''
        ]))
        self.debug_print(f"Final content: {final_content}")
        return self._create_html_document(final_content)

    def _create_html_document(self, content: str) -> str:
        """Create the HTML document using the template."""
        return self.template.format(content=content)

def convert_notebook_to_html(notebook_path: str, output_path: str, template_path: str = None,
                             standalone: bool = False):
    """
    Convert a Jupyter notebook to a formatted HTML document.

    Args:
        notebook_path: Path to the input .ipynb file.
        output_path: Path where the HTML file should be saved.
        template_path: Optional path to a report template HTML file.
        standalone: Inline local CSS/JS and base64-encode images so the
            output is a single portable file (MathJax still loads from CDN).
    """
    converter = NotebookToHTML(template_path=template_path)

    html_content = converter.convert_notebook(notebook_path)
    soup = BeautifulSoup(html_content, 'html.parser')

    if standalone:
        from .standalone import inline_assets
        search_dirs = [Path(output_path).resolve().parent,
                       Path.cwd(),
                       Path(notebook_path).resolve().parent]
        if template_path:
            # Template hrefs like templates/styles.css are relative to the
            # directory the templates/ folder sits in.
            search_dirs.append(Path(template_path).resolve().parent.parent)
        inline_assets(soup, search_dirs)

    html_content = soup.prettify()

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    if standalone:
        print(f"Standalone HTML document saved to: {output_path}")
    else:
        print(f"HTML document saved to: {output_path} \n start a http server with: python -m http.server 8000, then browse to http://localhost:8000/ to view the document")

# Main function to handle command-line arguments
def main():
    global DEBUG_MODE
    parser = argparse.ArgumentParser(description="Convert a Jupyter notebook to a formatted HTML document.")
    parser.add_argument("notebook_path", help="Path to the input .ipynb file.")
    parser.add_argument("output_path", help="Path where the HTML file should be saved.")
    parser.add_argument("--template", help="Path to a report template HTML file (default: ./templates/report_template.html if present, else the bundled template).")
    parser.add_argument("--debug", action="store_true", help="Print debug output and write it to debug.log.")
    parser.add_argument("--standalone", action="store_true",
                        help="Produce a single self-contained HTML file: inline the template "
                             "CSS/JS and embed images as base64 data URIs. The result can be "
                             "opened directly (file://) or emailed; MathJax still loads from CDN.")
    parser.add_argument("--pdf", nargs="?", const="AUTO", default=None, metavar="PDF_PATH",
                        help="Also render the report to PDF via headless Chromium. "
                             "Optionally give the PDF path (default: output path with .pdf extension). "
                             "The HTML must be written next to its templates/ and images/ folders.")

    args = parser.parse_args()

    if args.debug:
        DEBUG_MODE = True

    convert_notebook_to_html(args.notebook_path, args.output_path, template_path=args.template,
                             standalone=args.standalone)

    if args.pdf:
        from .htmltopdf import html_to_pdf
        pdf_path = str(Path(args.output_path).with_suffix('.pdf')) if args.pdf == "AUTO" else args.pdf
        html_to_pdf(args.output_path, pdf_path)

    if args.debug:
        with open("debug.log", "w") as f:
            for item in debug_log:
                f.write(f"{item}\n")

if __name__ == "__main__":
    main()