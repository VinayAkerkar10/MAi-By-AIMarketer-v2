(function () {
    const EMAIL_REGEX = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi;
    const PHONE_REGEX = /(?:\+?\d[\d\s().-]{6,}\d)/g;
    const INVALID_LINK_PREFIXES = ['javascript:', '#'];

    function normalizeText(value) {
        return String(value || '').replace(/\s+/g, ' ').trim();
    }

    function uniqueBy(items, getKey) {
        const seen = new Set();
        return items.filter((item) => {
            const key = getKey(item);
            if (!key || seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }

    function isVisible(node) {
        if (!node || !(node instanceof Element)) return false;
        const style = window.getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
    }

    function getVisibleText(root = document.body) {
        if (!root) return '';
        return normalizeText(root.innerText || root.textContent || '');
    }

    function absoluteUrl(value) {
        const text = normalizeText(value);
        if (!text) return '';
        const lowered = text.toLowerCase();
        if (INVALID_LINK_PREFIXES.some((prefix) => lowered.startsWith(prefix))) return '';
        try {
            return new URL(text, window.location.href).href;
        } catch (_error) {
            return '';
        }
    }

    function extractHeadings(root = document) {
        const headingNodes = Array.from(root.querySelectorAll('h1, h2, h3, h4, h5, h6, [role="heading"]'))
            .filter((node) => isVisible(node));
        return uniqueBy(
            headingNodes
                .map((node) => normalizeText(node.textContent))
                .filter((text) => text && text.length >= 3),
            (value) => value.toLowerCase()
        ).slice(0, 50);
    }

    function extractLinks(root = document) {
        const links = Array.from(root.querySelectorAll('a[href]'))
            .filter((anchor) => isVisible(anchor))
            .map((anchor) => ({
                text: normalizeText(anchor.textContent || anchor.getAttribute('aria-label')),
                href: absoluteUrl(anchor.getAttribute('href') || anchor.href || '')
            }))
            .filter((item) => item.href);

        return uniqueBy(links, (item) => `${item.href}|${item.text}`.toLowerCase()).slice(0, 500);
    }

    function extractContacts(root = document) {
        const pageText = getVisibleText(root.body || root);
        const emails = Array.from(new Set((pageText.match(EMAIL_REGEX) || []).map((value) => value.toLowerCase())));
        const phones = Array.from(new Set((pageText.match(PHONE_REGEX) || []).map((value) => normalizeText(value))));

        Array.from(root.querySelectorAll('a[href^="mailto:"], a[href^="tel:"]')).forEach((anchor) => {
            const href = String(anchor.getAttribute('href') || '');
            if (href.startsWith('mailto:')) {
                const email = normalizeText(href.replace(/^mailto:/i, ''));
                if (email) emails.push(email.toLowerCase());
            }
            if (href.startsWith('tel:')) {
                const phone = normalizeText(href.replace(/^tel:/i, ''));
                if (phone) phones.push(phone);
            }
        });

        const contacts = [];
        const maxLength = Math.max(emails.length, phones.length);
        for (let idx = 0; idx < maxLength; idx += 1) {
            contacts.push({
                email: emails[idx] || null,
                phone: phones[idx] || null
            });
        }

        return uniqueBy(
            contacts.filter((item) => item.email || item.phone),
            (item) => `${item.email || ''}|${item.phone || ''}`.toLowerCase()
        ).slice(0, 100);
    }

    function buildRows(cellMatrix, headers, kind, tableIndex) {
        const rows = cellMatrix.map((cells) => {
            const row = {};
            cells.forEach((value, idx) => {
                row[headers[idx] || `column_${idx + 1}`] = value;
            });
            return row;
        }).filter((row) => Object.values(row).some(Boolean));

        if (!rows.length) return null;
        return {
            index: tableIndex,
            kind,
            headers,
            rows
        };
    }

    function extractHtmlTables(root = document) {
        return Array.from(root.querySelectorAll('table'))
            .filter((table) => isVisible(table))
            .map((table, tableIndex) => {
                const rows = Array.from(table.querySelectorAll('tr'));
                const parsedRows = rows
                    .map((row) => Array.from(row.querySelectorAll('th, td'))
                        .map((cell) => normalizeText(cell.textContent)))
                    .filter((cells) => cells.some(Boolean));

                if (!parsedRows.length) return null;

                const hasHeader = rows[0] && rows[0].querySelector('th');
                const headers = (hasHeader ? parsedRows[0] : parsedRows[0].map((value, idx) => value || `column_${idx + 1}`))
                    .map((value, idx) => value || `column_${idx + 1}`);
                const dataRows = hasHeader ? parsedRows.slice(1) : parsedRows;
                return buildRows(dataRows, headers, 'html_table', tableIndex);
            })
            .filter(Boolean);
    }

    function extractAriaTables(root = document) {
        const selectors = '[role="table"], [role="grid"], [role="treegrid"]';
        return Array.from(root.querySelectorAll(selectors))
            .filter((table) => isVisible(table))
            .map((table, tableIndex) => {
                const rowNodes = Array.from(table.querySelectorAll('[role="row"]')).filter((row) => isVisible(row));
                if (!rowNodes.length) return null;

                const matrix = rowNodes.map((row) =>
                    Array.from(row.querySelectorAll('[role="columnheader"], [role="gridcell"], [role="cell"]'))
                        .map((cell) => normalizeText(cell.textContent))
                        .filter(Boolean)
                ).filter((cells) => cells.length >= 2);

                if (!matrix.length) return null;
                const headers = matrix[0].map((value, idx) => value || `column_${idx + 1}`);
                const hasHeader = rowNodes[0].querySelector('[role="columnheader"]');
                const dataRows = hasHeader ? matrix.slice(1) : matrix;
                return buildRows(dataRows, headers, 'aria_table', tableIndex);
            })
            .filter(Boolean);
    }

    function extractDivGrids(root = document) {
        const candidates = Array.from(root.querySelectorAll('section, div, main'))
            .filter((node) => isVisible(node))
            .filter((node) => node.children.length >= 2 && node.children.length <= 50);

        const tables = [];

        candidates.forEach((container, tableIndex) => {
            const children = Array.from(container.children).filter((child) => isVisible(child));
            if (children.length < 2) return;

            const sampleTag = children[0].tagName;
            if (!children.every((child) => child.tagName === sampleTag)) return;

            const matrix = children.map((child) => {
                const directValues = Array.from(child.children)
                    .filter((grandChild) => isVisible(grandChild))
                    .map((grandChild) => normalizeText(grandChild.textContent))
                    .filter(Boolean)
                    .slice(0, 12);
                return directValues;
            }).filter((cells) => cells.length >= 2);

            if (matrix.length < 2) return;

            const columnCount = Math.max(...matrix.map((cells) => cells.length));
            if (columnCount < 2) return;

            const headers = Array.from({ length: columnCount }, (_value, idx) => `column_${idx + 1}`);
            const built = buildRows(matrix, headers, 'div_grid', tableIndex);
            if (built) {
                tables.push(built);
            }
        });

        return tables.slice(0, 25);
    }

    function extractPayload(root = document) {
        return {
            website_url: window.location.href,
            page_title: document.title || '',
            headings: extractHeadings(root),
            links: extractLinks(root),
            contacts: extractContacts(document),
            tables: [
                ...extractHtmlTables(root),
                ...extractAriaTables(root),
                ...extractDivGrids(root)
            ]
        };
    }

    window.__MAI_SHARED_SCRAPER__ = {
        extractHeadings,
        extractLinks,
        extractContacts,
        extractHtmlTables,
        extractAriaTables,
        extractDivGrids,
        extractPayload
    };
})();
