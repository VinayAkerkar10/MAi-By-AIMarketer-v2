(function () {
    const EMAIL_REGEX = /[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi;
    const PHONE_REGEX = /(?:\+?\d[\d\s().-]{6,}\d)/g;

    function getVisibleText(root = document.body) {
        if (!root) return '';
        return String(root.innerText || root.textContent || '').trim();
    }

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

    function extractHeadings() {
        return uniqueBy(
            Array.from(document.querySelectorAll('h1, h2, h3'))
                .map((node) => normalizeText(node.textContent))
                .filter(Boolean),
            (value) => value.toLowerCase()
        );
    }

    function extractLinks() {
        const links = Array.from(document.querySelectorAll('a[href]')).map((anchor) => ({
            text: normalizeText(anchor.textContent),
            href: anchor.href || anchor.getAttribute('href') || ''
        })).filter((item) => item.href);

        return uniqueBy(links, (item) => `${item.href}|${item.text}`.toLowerCase());
    }

    function extractTables() {
        return Array.from(document.querySelectorAll('table')).map((table, tableIndex) => {
            const rows = Array.from(table.querySelectorAll('tr'));
            const parsedRows = rows
                .map((row) => Array.from(row.querySelectorAll('th, td')).map((cell) => normalizeText(cell.textContent)))
                .filter((cells) => cells.some(Boolean));

            if (!parsedRows.length) {
                return null;
            }

            const headerCandidate = parsedRows[0];
            const hasHeader = rows[0] && rows[0].querySelector('th');
            const headers = hasHeader
                ? headerCandidate.map((value, idx) => value || `column_${idx + 1}`)
                : null;

            const dataRows = (hasHeader ? parsedRows.slice(1) : parsedRows).map((cells) => {
                if (headers) {
                    const rowObj = {};
                    headers.forEach((header, idx) => {
                        rowObj[header] = cells[idx] || '';
                    });
                    return rowObj;
                }

                const rowObj = {};
                cells.forEach((value, idx) => {
                    rowObj[`column_${idx + 1}`] = value;
                });
                return rowObj;
            }).filter((rowObj) => Object.values(rowObj).some(Boolean));

            return {
                index: tableIndex,
                headers: headers || [],
                rows: dataRows
            };
        }).filter(Boolean);
    }

    function extractContacts() {
        const pageText = getVisibleText();
        const emails = Array.from(new Set((pageText.match(EMAIL_REGEX) || []).map((value) => value.toLowerCase())));
        const phones = Array.from(new Set((pageText.match(PHONE_REGEX) || []).map((value) => normalizeText(value))));

        const maxLength = Math.max(emails.length, phones.length);
        const contacts = [];

        for (let idx = 0; idx < maxLength; idx += 1) {
            contacts.push({
                email: emails[idx] || null,
                phone: phones[idx] || null
            });
        }

        if (!contacts.length) {
            return [];
        }

        return uniqueBy(contacts, (item) => `${item.email || ''}|${item.phone || ''}`.toLowerCase());
    }

    function buildPayload() {
        return {
            website_url: window.location.href,
            page_title: document.title || '',
            tables: extractTables(),
            links: extractLinks(),
            headings: extractHeadings(),
            contacts: extractContacts()
        };
    }

    chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
        if (!message || message.type !== 'SCRAPE_PAGE') {
            return false;
        }

        try {
            const payload = buildPayload();
            const hasContent = Boolean(
                payload.tables.length ||
                payload.links.length ||
                payload.headings.length ||
                payload.contacts.length
            );

            sendResponse({
                success: hasContent,
                payload,
                message: hasContent ? 'Page scraped successfully.' : 'No lead data found on this page.'
            });
        } catch (error) {
            sendResponse({
                success: false,
                payload: null,
                message: error instanceof Error ? error.message : 'Failed to scrape page.'
            });
        }

        return true;
    });
})();
