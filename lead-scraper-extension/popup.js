const SCRAPED_PAYLOAD_KEY = 'lead_scraper_extension_payload';
const APP_URL_PATTERNS = ['127.0.0.1', 'localhost', 'aimarketer', 'onrender.com'];
const DEFAULT_APP_URL = 'http://127.0.0.1:5500/frontend/index.html';

async function getActiveTab() {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    return tabs[0] || null;
}

function looksLikeAppUrl(url) {
    const safeUrl = String(url || '').toLowerCase();
    return APP_URL_PATTERNS.some((pattern) => safeUrl.includes(pattern));
}

function setStatus(message, isError = false) {
    const statusEl = document.getElementById('status');
    if (!statusEl) return;
    statusEl.textContent = message;
    statusEl.style.borderColor = isError ? '#fca5a5' : '#d9e2ec';
    statusEl.style.background = isError ? '#fef2f2' : '#fff';
}

function setMeta(payload) {
    const metaEl = document.getElementById('meta');
    if (!metaEl) return;

    if (!payload) {
        metaEl.textContent = '';
        return;
    }

    const tables = Array.isArray(payload.tables) ? payload.tables.length : 0;
    const links = Array.isArray(payload.links) ? payload.links.length : 0;
    const headings = Array.isArray(payload.headings) ? payload.headings.length : 0;
    const contacts = Array.isArray(payload.contacts) ? payload.contacts.length : 0;
    metaEl.textContent = `Tables: ${tables} | Links: ${links} | Headings: ${headings} | Contacts: ${contacts}`;
}

async function savePayload(payload) {
    await chrome.storage.local.set({ [SCRAPED_PAYLOAD_KEY]: payload });
}

async function loadPayload() {
    const stored = await chrome.storage.local.get(SCRAPED_PAYLOAD_KEY);
    return stored[SCRAPED_PAYLOAD_KEY] || null;
}

function updateSendButtonState(payload) {
    const sendBtn = document.getElementById('sendBtn');
    if (!sendBtn) return;
    sendBtn.disabled = !payload;
}

async function scrapeCurrentPage() {
    const tab = await getActiveTab();
    if (!tab || !tab.id) {
        throw new Error('No active tab available.');
    }

    await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        files: ['content.js']
    });
    console.log('[Extension] Forced content script injection');

    const response = await chrome.tabs.sendMessage(tab.id, { type: 'SCRAPE_PAGE' });
    if (!response) {
        throw new Error('No response from content script.');
    }

    if (!response.success || !response.payload) {
        throw new Error(response.message || 'No data found on this page.');
    }

    return response.payload;
}

async function getAppTargetTab() {
    const activeTab = await getActiveTab();
    if (activeTab && activeTab.id && looksLikeAppUrl(activeTab.url)) {
        return activeTab;
    }

    const tabs = await chrome.tabs.query({});
    const existingAppTab = tabs.find((tab) => tab.id && looksLikeAppUrl(tab.url));
    if (existingAppTab) {
        await chrome.tabs.update(existingAppTab.id, { active: true });
        if (typeof existingAppTab.windowId === 'number') {
            await chrome.windows.update(existingAppTab.windowId, { focused: true });
        }
        return existingAppTab;
    }

    const createdTab = await chrome.tabs.create({ url: DEFAULT_APP_URL, active: true });
    if (!createdTab || !createdTab.id) {
        throw new Error('Unable to open the MAi app page.');
    }

    return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
            chrome.tabs.onUpdated.removeListener(listener);
            reject(new Error('Timed out while opening the MAi app page.'));
        }, 15000);

        const listener = (tabId, changeInfo, updatedTab) => {
            if (tabId !== createdTab.id) return;
            if (changeInfo.status !== 'complete') return;
            clearTimeout(timeout);
            chrome.tabs.onUpdated.removeListener(listener);
            resolve(updatedTab);
        };

        chrome.tabs.onUpdated.addListener(listener);
    });
}

async function sendPayloadToApp(payload) {
    const tab = await getAppTargetTab();
    if (!tab || !tab.id) {
        throw new Error('No MAi app tab available.');
    }

    console.log('[Extension] Auto sending payload', { tabId: tab.id, url: tab.url });

    const results = await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        world: 'MAIN',
        func: async (extensionPayload) => {
            const waitForFunction = (fnName, timeout = 5000) => {
                return new Promise((resolve) => {
                    const start = Date.now();

                    const check = () => {
                        if (typeof window[fnName] === 'function') {
                            return resolve(true);
                        }
                        if (Date.now() - start > timeout) {
                            return resolve(false);
                        }
                        requestAnimationFrame(check);
                    };

                    check();
                });
            };

            console.log('[Extension] Injected script started');

            const isAvailable = await waitForFunction('setLeadExtensionPayload');

            if (!isAvailable) {
                console.error('[Extension] Function not available after waiting');
                return {
                    success: false,
                    message: 'window.setLeadExtensionPayload is not available on this page'
                };
            }

            console.log('[Extension] Function found, sending payload');
            window.setLeadExtensionPayload(extensionPayload);

            return {
                success: true,
                message: 'Payload sent to app successfully'
            };
        },
        args: [payload]
    });

    const result = results && results[0] ? results[0].result : null;
    if (!result || !result.success) {
        throw new Error((result && result.message) || 'Failed to send payload to app.');
    }
}

async function handleScrape() {
    try {
        setStatus('Scraping current page...');
        const payload = await scrapeCurrentPage();
        await savePayload(payload);
        setMeta(payload);
        updateSendButtonState(payload);
        setStatus('Page scraped successfully. Sending payload to app...');
        console.log('[Extension] Auto sending payload');
        await sendPayloadToApp(payload);
        setStatus('Page scraped successfully and sent to the app.');
    } catch (error) {
        updateSendButtonState(null);
        setMeta(null);
        setStatus(error instanceof Error ? error.message : 'Failed to scrape page.', true);
    }
}

async function handleSend() {
    try {
        const payload = await loadPayload();
        if (!payload) {
            throw new Error('No scraped payload available. Scrape the page first.');
        }

        setStatus('Sending payload to app...');
        await sendPayloadToApp(payload);
        setMeta(payload);
        setStatus('Payload sent to the app. Open the Lead Scraper UI to continue.');
    } catch (error) {
        setStatus(error instanceof Error ? error.message : 'Failed to send payload.', true);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const scrapeBtn = document.getElementById('scrapeBtn');
    const sendBtn = document.getElementById('sendBtn');

    if (scrapeBtn) {
        scrapeBtn.addEventListener('click', handleScrape);
    }

    if (sendBtn) {
        sendBtn.addEventListener('click', handleSend);
    }

    const payload = await loadPayload();
    updateSendButtonState(payload);
    setMeta(payload);

    if (payload) {
        setStatus('Stored payload found. Auto-send is enabled, but you can still resend manually.');
    }
});
