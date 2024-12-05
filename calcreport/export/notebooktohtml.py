import json
import re
from pathlib import Path
import cmarkgfm
from cmarkgfm.cmark import Options as cmarkgfmOptions
from bs4 import BeautifulSoup
import ast

'''
to start a local server to serve the content on port 8000, run the following command in the terminal:
python -m http.server 8000
'''

options = (cmarkgfmOptions.CMARK_OPT_UNSAFE)

DEBUG_MODE = True
if DEBUG_MODE:
    debug_log = []

def debug_print(*args, **kwargs):
    if DEBUG_MODE:
        debug_log.append(*args, *kwargs)
        print(*args, **kwargs)

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
    def __init__(self):
        self.debug_mode = DEBUG_MODE
        self.structure = DocumentStructure()
        
        # Load template once during initialization
        with open('./templates/report_template.html', 'r') as f:
            self.template = f.read()
    
    def extract_structure(self, cells):
        """
        Extract and categorize document structure from notebook cells.
        Handles arbitrary header levels and special sections.
        """
        # Initialize section numbering array (index 0 unused for easier level mapping)
        current_numbers = [0] * (self.structure.max_header_level + 1)
        current_category = "body"

        self.debug_print("\nStarting structure extraction:")
        
        for cell in cells:
            nb_cell = NotebookCell(
                cell_type = cell['cell_type'],
                source = ''.join(cell['source']),
                metadata = cell.get('metadata', {}),
                output = cell.get('outputs', {})
            )
            #self.debug_print(f"Cell Metadata: {nb_cell.metadata}")
            if cell['cell_type'] == 'markdown':
                lines = nb_cell.source.split('\n')
                for line in lines:
                    # Process special sections first
                    if line.startswith('# Cover Page'):
                        nb_cell.category = "cover_page"
                        self.structure.cover_page = nb_cell
                        
                    elif line.startswith('# Executive Summary'):
                        nb_cell.category = "executive_summary"
                        self.structure.executive_summary = nb_cell
                        break
                        
                    elif line.startswith('# Appendix'):
                        nb_cell.category = "appendix"
                        self.structure.appendices.append(nb_cell)
                        #self.debug_print(f"Appendix metadata: {nb_cell.metadata}")
                        break
                    
                    # Process regular headers
                    header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
                    if header_match:
                        level = len(header_match.group(1))
                        text = header_match.group(2).strip()

                        self.debug_print(f"\nProcessing header - Level: {level}")
                        self.debug_print(f"Header text: {text}")
                        
                        # Skip if this is a special section we already handled
                        if any(x in text for x in ['Cover Page', 'Executive Summary', 'Appendix']):
                            continue
                        
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
                        self.debug_print(f"Generated section number: {section_number}")
                        self.debug_print(f"Generated ID: {section_id}")
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
                        self.debug_print(f"Added header to structure: {header_info}")
                        break
                                    
            # Add to appropriate content collection
            if nb_cell.category not in ["cover_page", "executive_summary", "appendix"]:
                self.structure.body_cells.append(nb_cell)
        
        self.debug_print("\nFinal header structure:")
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
        #self.debug_print(f'Metadata type: {type(metadata)}')
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
        #self.debug_print(f"meta_html: {meta_html}")

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
                        f'<span class="title">Appendix {letter}'
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
            #self.debug_print(f"Cover page HTML: {soup.prettify()}")
            revision_table = soup.find('table')
            
            #self.debug_print(f"Revision Table: {revision_table}")

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
            #self.debug_print(f"Appendix metadata: {metadata}")
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
            <div class="appendix-cover no-page-numbers">
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
        #self.debug_print(f"Processing markdown cell: {cell.source}")
        # Get the source content
        source_content = cell.source
        
        # Replace figure references with links
        source_content = re.sub(
            r'\[([^\]]+)\]',
            lambda m: f'<a href="#fig-{m.group(1)}" data-ref="fig-{m.group(1)}" class="figure-ref">Figure {figure_refs.get(m.group(1), "?")}</a>' 
            if m.group(1) in figure_refs else m.group(0),
            source_content
        )
        
        # Update headers with section numbers if this is a header cell
        if cell.level is not None and cell.section_number:

            source_content = self.update_markdown_with_section_numbers(cell)
        
        # Convert markdown to HTML
        html = cmarkgfm.github_flavored_markdown_to_html(source_content, options)
        self.debug_print(f"Processed markdown HTML: {html}")
        # Process the HTML with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        current_section = []
        
        # Add IDs to headers and ensure proper section numbering
        for tag_level in range(1, 7):
            headers = soup.find_all(f'h{tag_level}')
            if headers:
                self.debug_print(f"\nProcessing h{tag_level} headers:")
                for header in headers:
                    original_text = header.text.strip()
                    # Extract section number and text
                    section_match = re.match(r'^(\d+(\.\d+)*)\.\s*(.+)$', original_text)
                    if section_match:
                        section_nums = [int(n) for n in section_match.group(1).split('.')]
                        header_text = section_match.group(3).strip()
                        
                        self.debug_print(f"Original header text: '{original_text}'")
                        self.debug_print(f"Section numbers: {section_nums}")
                        self.debug_print(f"Cleaned header text: '{header_text}'")
                        
                        # Update current section context
                        if tag_level == 1:
                            current_section = section_nums
                        elif len(section_nums) == tag_level:
                            current_section = section_nums
                    
                    
                    # Debug current structure headers
                    self.debug_print("Looking for match in structure headers:")
                    for h in self.structure.headers:
                        self.debug_print(f"Comparing with structure header - Level: {h['level']}, Text: '{h['text']}', ID: {h['id']}")
                        
                        # Extract section numbers from header ID
                        h_section_nums = [int(n) for n in h['id'].lstrip('s').split('s')]
                        
                        # Check if text, level, and section hierarchy match
                        if (h['text'] == header_text and 
                            h['level'] == tag_level and 
                            h_section_nums[:tag_level-1] == section_nums[:tag_level-1]):
                            
                            self.debug_print(f"Found matching header in structure with correct hierarchy!")
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

    def update_markdown_with_section_numbers(self, cell: NotebookCell) -> str:
        """
        Update markdown headers with section numbers.
        This is now a helper method for process_markdown_cell.
        
        Args:
            cell: NotebookCell instance to update
        
        Returns:
            Updated markdown content
        """
        if not cell.level or not cell.section_number:
            return cell.source
            
        lines = cell.source.split('\n')
        updated_lines = []
        #self.debug_print(f"Updating markdown with section numbers for cell {cell.header_id}...")

        for line in lines:
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                #self.debug_print(f"Line: {line} is a header)")
                hashes = header_match.group(1)
                text = header_match.group(2).strip()
                # Find matching header in our structure
                for header in self.structure.headers:
                    if (header['text'] == text and 
                        header['level'] == len(hashes) and 
                        header['id'] == cell.header_id):
                        line = f"{hashes} {header['section_number']}. {text}"
                        #self.debug_print(f"Updated line: {line}")
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
        #self.debug_print(f"Processing code cell...")
        # Check if this is an image cell
        image_pattern = r"Image\(['\"]([^'\"]+)['\"](?:\s*,\s*metadata\s*=\s*(\{[^}]+\}))?"
        image_match = re.search(image_pattern, cell.source)

        if image_match:
            #self.debug_print("Its an image cell...")
            image_url = image_match.group(1)
            metadata_str = image_match.group(2) if image_match.groups()[1] is not None else "{}"
            
            try:
                metadata = ast.literal_eval(metadata_str)
                fig_id = metadata.get('ID', '')
                caption = metadata.get('caption', '')
                fig_num = figure_refs.get(fig_id, '?')
                
                # Create figure HTML with explicit number
                #self.debug_print(f"Creating figure with ID {fig_id} and number {fig_num}")
                return f'''
                    <figure class="figure" id="fig-{fig_id}" data-label="fig-{fig_id}">
                        <img src="{image_url}" alt="{caption}" />
                        <figcaption>Figure {fig_num}: {caption}</figcaption>
                    </figure>
                '''
            except (ValueError, SyntaxError) as e:
                self.debug_print(f"Error parsing image metadata: {e}")
                return f'<figure class="figure"><img src="{image_url}" alt="figure" /></figure>'

        # Process cell outputs
        if len(cell.output) > 0:
            #self.debug_print("Cell has outputs...")
            #self.debug_print(f"Cell output is: {cell.output}")
            #self.debug_print(f"Cell output type is: {type(cell.output)}")
            outputs = []
                        
            for output in cell.output:
                
                if 'text/html' in output['data']:
                    self.debug_print("Processing maths cell...")
                    html_content = ''.join(output['data']['text/html'])
                    
                    # Clean up MathJax-related content
                    html_content = self.clean_mathjax_content(html_content)
                    
                    # Add to outputs if content remains after cleaning
                    if html_content.strip():
                        outputs.append(html_content)
            
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
            debug_log.append(*args, *kwargs)

    def convert_notebook(self, notebook_path: str) -> str:
        """Convert Jupyter notebook to HTML."""
        # Read the notebook file
        self.debug_print(f"Reading notebook file: {notebook_path}")
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        # First pass: collect all figure IDs and assign numbers
        figure_refs = self.collect_figure_references(notebook['cells']) 

        # Extract document structure
        debug_print("Extracting document structure...")
        self.extract_structure(notebook['cells'])

        # Generate document components
        cover_page = self.generate_cover_page()
        header_footer = self.generate_header_footer()
        #self.debug_print(f"Header and footer: {header_footer}")
        executive_summary = self.generate_executive_summary()
        toc = self.generate_toc_html()
        

        # Process body content
        content = []
        cell_counter = 1
        for cell in self.structure.body_cells:
            #self.debug_print(f"Processing cell {cell_counter}...")
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

        #self.debug_print(f"Final content: {final_content}")
        return self._create_html_document(final_content)

    def _create_html_document(self, content: str) -> str:
        """Create the HTML document using the template."""
        return self.template.format(content=content)

def convert_notebook_to_html(notebook_path: str, output_path: str):
    """
    Convert a Jupyter notebook to a formatted HTML document.
    
    Args:
        notebook_path: Path to the input .ipynb file.
        output_path: Path where the HTML file should be saved.
    """
    converter = NotebookToHTML()
    
    html_content = converter.convert_notebook(notebook_path)
    html_content = BeautifulSoup(html_content, 'html.parser').prettify()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

# Example usage:
#if __name__ == "__main__":
convert_notebook_to_html(
    "/home/rmc/script/Projects/30031-GMS-ENGINESKID/30031-001.ipynb",
    "/home/rmc/script/Projects/30031-GMS-ENGINESKID/output_report.html",
    )

if DEBUG_MODE:
    with open("debug.log", "w") as f:
        for item in debug_log:
            f.write(f"{item}\n")