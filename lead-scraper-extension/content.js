(function () {
    chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
        if (!message || message.type !== 'SCRAPE_PAGE') {
            return false;
        }

        try {
            if (!window.__MAI_SHARED_SCRAPER__ || typeof window.__MAI_SHARED_SCRAPER__.extractPayload !== 'function') {
                throw new Error('Shared scraper engine is not available.');
            }

            const payload = window.__MAI_SHARED_SCRAPER__.extractPayload(document);
            const hasContent = Boolean(
                (payload.tables || []).length ||
                (payload.links || []).length ||
                (payload.headings || []).length ||
                (payload.contacts || []).length
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
