class RepeatTableHeadersHandler extends Paged.Handler {
    constructor(chunker, polisher, caller) {
        super(chunker, polisher, caller)
        this.splitTablesRefs = []
        this.tableWidths = new Map() // Store the calculated column widths for each table
        this.processedTables = new Set() // Track tables that have been processed
        console.log("RepeatTableHeadersHandler constructor called")
    }

    // Process tables before Paged.js adds refs
    beforeParsed(content) {
        console.log('Processing all tables before pagination');
        const tables = content.querySelectorAll('table');
        
        tables.forEach((table, index) => {
            // Generate a temporary ID if none exists
            const tempId = `table-${index}`;
            console.log(`Initial processing of table ${tempId}`);
            
            // Store original styling
            const originalStyles = window.getComputedStyle(table);
            console.log('Original styles:', originalStyles);
            const originalWidth = originalStyles.width;
            console.log('Original width:', originalWidth);
            const originalTableLayout = originalStyles.tableLayout;
            console.log('Original table layout:', originalTableLayout);
            
            // Temporarily set table to full width for measurement
            table.style.width = '100%';
            table.style.tableLayout = 'auto';
            
            const widths = this.calculateWidths(table);
            if (widths) {
                // Store widths with temporary ID
                this.tableWidths.set(tempId, widths);
                // Apply colgroup immediately
                this.applyWidths(table, widths, tempId);
            }
            
            // Restore original styling
            table.style.width = originalWidth;
            table.style.tableLayout = originalTableLayout;
            
            // Store temp ID for later matching
            table.dataset.tempId = tempId;
        });
    }

    initializeTable(table) {
        if (!table.dataset.ref) return null;
        console.log(`Initializing table ${table.dataset.ref}`);
        
        // First, ensure we're working with the original table in its natural state
        table.style.width = '100%';
        
        // Get column widths from the first row only
        const headerRow = table.querySelector('tr');
        if (!headerRow) return null;

        const cells = headerRow.querySelectorAll('th, td');
        const columnCount = cells.length;
        const contentWidths = new Array(columnCount).fill(0);

        // Measure content width of header cells
        cells.forEach((cell, index) => {
            // Create clone for measurement
            const clone = cell.cloneNode(true);
            clone.style.cssText = `
                position: absolute;
                visibility: hidden;
                white-space: nowrap;
                padding: 0;
                border: 0;
                width: auto;
                min-width: 0;
                max-width: none;
            `;
            document.body.appendChild(clone);
            contentWidths[index] = clone.getBoundingClientRect().width;
            document.body.removeChild(clone);
        });

        // Calculate percentages based on content widths
        const totalWidth = contentWidths.reduce((sum, width) => sum + width, 0);
        const percentageWidths = contentWidths.map(width => 
            `${Math.max(5, (width / totalWidth * 100)).toFixed(2)}%`
        );

        console.log(`Captured widths for table ${table.dataset.ref}:`, percentageWidths);
        return percentageWidths;
    }    
    
    calculateWidths(table) {
        // Get column widths from the first row only
        const headerRow = table.querySelector('tr');
        if (!headerRow) return null;

        const cells = headerRow.querySelectorAll('th, td');
        const columnCount = cells.length;
        const contentWidths = new Array(columnCount).fill(0);

        // Measure content width of header cells
        cells.forEach((cell, index) => {
            const clone = cell.cloneNode(true);
            clone.style.cssText = `
                position: absolute;
                table-layout: auto;
                visibility: hidden;
                white-space: nowrap;
                padding: 0;
                border: 0;
            `;
            document.body.appendChild(clone);
            contentWidths[index] = clone.getBoundingClientRect().width;
            console.log(`Width of cell ${index}:`, contentWidths[index]);
            document.body.removeChild(clone);
        });

        // Calculate percentages based on content widths
        const totalWidth = contentWidths.reduce((sum, width) => sum + width, 0);
        console.log(`Total width:`, totalWidth);
        const percentageWidths = contentWidths.map(width => 
            `${Math.max(5, (width / totalWidth * 100)).toFixed(2)}%`
        );

        console.log(`Calculated widths:`, percentageWidths);
        return percentageWidths;
    }

    // Called when Paged.js starts processing a table
    processTable(table) {
        if (!this.tableWidths.has(table.dataset.ref)) {
            console.log(`Initial processing of table ${table.dataset.ref}`)
            const widths = this.calculateOptimalColumnWidths(table)
            console.log(`Calculated widths:`, widths)
            this.tableWidths.set(table.dataset.ref, widths)
            this.applyCalculatedWidths(table, widths)
        }
    } 
    
    calculateOptimalColumnWidths(table) {
        const columnCount = this.getColumnCount(table)
        console.log(`Calculating optimal column widths for ${columnCount} columns`)
        
        // Initialize arrays to track maximum content width for each column
        const columnWidths = new Array(columnCount).fill(0)

        // Process all rows (including header and body)
        const rows = table.querySelectorAll('tr')
        rows.forEach(row => {
            const cells = row.querySelectorAll('th, td')
            cells.forEach((cell, index) => {
                if (index < columnCount) {
                    //Get the computed width of the cell's content
                    const computedStyle = window.getComputedStyle(cell)
                    const contentWidth = cell.offsetWidth - parseFloat(computedStyle.paddingLeft) - parseFloat(computedStyle.paddingRight)
                    console.log(`Content width for cell ${index}:`, contentWidth)
                    
                    // Update maximum width for this column
                    columnWidths[index] = Math.max(columnWidths[index], contentWidth)
                    console.log(`Max width for column ${index}:`, columnWidths[index])
                }
            })
        })

        // Add some padding to each column width
        const padding = 0 // Adjust this value as needed
        return columnWidths.map(width => width + padding + 'px')
    }

    getColumnCount(table) {
        const headerRow = table.querySelector('tr')
        if (!headerRow) return 0
        
        let count = 0
        const cells = headerRow.querySelectorAll('th, td')
        cells.forEach(cell => {
            count += cell.colSpan || 1
        })
        return count
    }

    applyCalculatedWidths(table, widths) {
        // Create or update colgroup
        let colgroup = table.querySelector('colgroup')
        if (!colgroup) {
            colgroup = document.createElement('colgroup')
            table.insertBefore(colgroup, table.firstChild)
        } else {
            colgroup.innerHTML = '' // Clear existing cols
        }

        // Create cols with calculated widths
        widths.forEach(width => {
            const col = document.createElement('col')
            col.style.width = width
            colgroup.appendChild(col)
        })
    }

    afterPageLayout(pageElement, page, breakToken, chunker) {
        this.chunker = chunker;
        this.splitTablesRefs = [];

        if (breakToken) {
            const node = breakToken.node;
            const tables = this.findAllAncestors(node, "table");
            if (node.tagName === "TABLE") tables.push(node);

            if (tables.length > 0) {
                tables.forEach(table => {
                    // Try to match table with stored widths using tempId
                    const tempId = table.dataset.tempId;
                    const ref = table.dataset.ref;
                    
                    if (ref && tempId && this.tableWidths.has(tempId)) {
                        // Transfer widths from tempId to ref
                        const widths = this.tableWidths.get(tempId);
                        this.tableWidths.set(ref, widths);
                        // Apply widths using the ref
                        this.applyWidths(table, widths, ref);
                    }
                });

                this.splitTablesRefs = tables.map(t => t.dataset.ref);

                let thead = node.tagName === "THEAD" ? node : this.findFirstAncestor(node, "thead");
                if (thead) {
                    let lastTheadNode = thead.hasChildNodes() ? thead.lastChild : thead;
                    breakToken.node = this.nodeAfter(lastTheadNode, chunker.source);
                }

                this.hideEmptyTables(pageElement, node);
            }
        }
    } 
 
    applyWidths(table, widths, identifier) {
        console.log(`Applying widths to table ${identifier}:`, widths);
        
        // Remove any existing colgroup
        const existingColgroup = table.querySelector('colgroup');
        if (existingColgroup) {
            existingColgroup.remove();
        }

        // Create fresh colgroup
        const colgroup = document.createElement('colgroup');
        widths.forEach(width => {
            const col = document.createElement('col');
            col.style.width = width;
            colgroup.appendChild(col);
        });

        // Insert colgroup at the start of table
        table.insertBefore(colgroup, table.firstChild);
        
        // Ensure table styling
        if (!table.classList.contains('markdown-cell')) {
            table.classList.add('markdown-cell');
        }
    }  

    hideEmptyTables(pageElement, breakTokenNode) {
        this.splitTablesRefs.forEach(ref => {
            let table = pageElement.querySelector("[data-ref='" + ref + "']")
            if (table) {
                let sourceBody = table.querySelector("tbody > tr")
                if (!sourceBody || this.refEquals(sourceBody.firstElementChild, breakTokenNode)) {
                    table.style.visibility = "hidden"
                    table.style.position = "absolute"
                    let lineSpacer = table.nextSibling
                    if (lineSpacer) {
                        lineSpacer.style.visibility = "hidden"
                        lineSpacer.style.position = "absolute"
                    }
                }
            }
        })
    }

    refEquals(a, b) {
        return a && a.dataset && b && b.dataset && a.dataset.ref === b.dataset.ref
    }

    findFirstAncestor(element, selector) {
        while (element.parentNode && element.parentNode.nodeType === 1) {
            if (element.parentNode.matches(selector)) return element.parentNode
            element = element.parentNode
        }
        return null
    }

    findAllAncestors(element, selector) {
        const ancestors = []
        while (element.parentNode && element.parentNode.nodeType === 1) {
            if (element.parentNode.matches(selector)) ancestors.unshift(element.parentNode)
            element = element.parentNode
        }
        return ancestors
    }

    layout(rendered, layout) {
        this.splitTablesRefs.forEach(ref => {
            const renderedTable = rendered.querySelector(`[data-ref='${ref}']`);
            if (renderedTable) {
                if (!renderedTable.getAttribute("repeated-headers")) {
                    const sourceTable = this.chunker.source.querySelector(`[data-ref='${ref}']`);
                    
                    // Apply widths first
                    const storedWidths = this.tableWidths.get(ref);
                    if (storedWidths) {
                        this.applyWidths(renderedTable, storedWidths, ref);
                    }
                    
                    // Then repeat headers
                    this.repeatTHead(sourceTable, renderedTable);
                    renderedTable.setAttribute("repeated-headers", true);
                }
            }
        });
    }

    
    repeatColgroup(sourceTable, renderedTable) {
        let colgroup = sourceTable.querySelectorAll("colgroup")
        let firstChild = renderedTable.firstChild
        colgroup.forEach((colgroup) => {
            let clonedColgroup = colgroup.cloneNode(true)
            renderedTable.insertBefore(clonedColgroup, firstChild)
        })
    }

    repeatTHead(sourceTable, renderedTable) {
        let thead = sourceTable.querySelector("thead")
        if (thead) {
            let clonedThead = thead.cloneNode(true)
            renderedTable.insertBefore(clonedThead, renderedTable.firstChild)
        }
    }

    nodeAfter(node, limiter) {
        if (limiter && node === limiter) return
        let significantNode = this.nextSignificantNode(node)
        if (significantNode) return significantNode
        if (node.parentNode) {
            while ((node = node.parentNode)) {
                if (limiter && node === limiter) return
                significantNode = this.nextSignificantNode(node)
                if (significantNode) return significantNode
            }
        }
    }

    nextSignificantNode(sib) {
        while ((sib = sib.nextSibling)) { if (!this.isIgnorable(sib)) return sib }
        return null
    }

    isIgnorable(node) {
        return (
            (node.nodeType === 8)
            || ((node.nodeType === 3) && this.isAllWhitespace(node))
        )
    }

    isAllWhitespace(node) {
        return !(/[^\t\n\r ]/.test(node.textContent))
    }
   
    isIgnorable(node) {
        return (
            (node.nodeType === 8)
            || ((node.nodeType === 3) && this.isAllWhitespace(node))
        )
    }

    isAllWhitespace(node) {
        return !(/[^\t\n\r ]/.test(node.textContent))
    }

    // Add a new method to clean any interfering styles
    cleanTableStyles(table) {
        // Remove any existing styles that might interfere
        const elementsToClean = table.querySelectorAll('col, th, td');
        elementsToClean.forEach(el => {
            // Keep only essential styles
            const computedStyle = window.getComputedStyle(el);
            el.style.cssText = `
                padding: ${computedStyle.padding};
                border: ${computedStyle.border};
                box-sizing: border-box !important;
            `;
        });
    }

}
console.log(' About to register RepeatTableHeadersHandler')

Paged.registerHandlers(RepeatTableHeadersHandler)
console.log(' RepeatTableHeadersHandler registered')