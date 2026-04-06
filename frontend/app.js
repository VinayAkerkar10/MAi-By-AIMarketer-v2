// Global data storage
let appData = {
    currentUserRole: null,
    currentOrganizationId: null,
    businessProfile: null,
    generatedStrategy: null,
    currentStrategyId: null,
    reviewCampaignId: null,
    adminApiKeys: [],
    adminUsers: [],
    adminLicenses: [],
    adminOrganizations: [],
    scrapedLeads: [],
    enrichedData: [],
    campaigns: [],
    templates: [
        {
            id: 1,
            name: "SaaS Lead Nurturing",
            category: "Email",
            industry: "SaaS",
            content: "Hi [Name],\n\nWe noticed you downloaded our guide on scaling SaaS operations. As a follow-up, I wanted to share how [Your Company] has helped similar companies like yours increase their operational efficiency by 40%.\n\nWould you be interested in a 15-minute call to discuss your current challenges?\n\nBest regards,\n[Your Name]\n\nCreated by Mrityunjay Pandey, AIMarketer Pvt. Ltd."
        },
        {
            id: 2,
            name: "LinkedIn Connection Request",
            category: "LinkedIn",
            industry: "Technology",
            content: "Hi [Name],\n\nI see we're both in the tech industry and I'm impressed by [Company]'s recent growth. I'd love to connect and share insights about digital marketing strategies that have worked well for similar companies.\n\nBest,\n[Your Name]\n\nCreated by Mrityunjay Pandey, AIMarketer Pvt. Ltd."
        },
        {
            id: 3,
            name: "WhatsApp Follow-up",
            category: "WhatsApp",
            industry: "General",
            content: "Hi [Name],\n\nThanks for your interest in our solution! I wanted to follow up on our conversation and see if you had any questions about how we can help [Company] achieve its marketing goals.\n\nLet me know if you'd like to schedule a quick demo.\n\nBest regards,\n[Your Name]\n\nCreated by Mrityunjay Pandey, AIMarketer Pvt. Ltd."
        },
        {
            id: 4,
            name: "Healthcare Outreach",
            category: "Email",
            industry: "Healthcare",
            content: "Dear [Name],\n\nI hope this email finds you well. I wanted to reach out regarding how [Your Company] has been helping healthcare organizations improve their patient engagement through targeted digital marketing.\n\nWould you be available for a brief call this week?\n\nWarm regards,\n[Your Name]\n\nCreated by Mrityunjay Pandey, AIMarketer Pvt. Ltd."
        },
        {
            id: 5,
            name: "Finance Industry Introduction",
            category: "LinkedIn",
            industry: "Finance",
            content: "Hello [Name],\n\nI noticed your expertise in financial services and thought you might be interested in our recent case study showing how we helped a fintech company increase their qualified leads by 150%.\n\nWould love to connect!\n\n[Your Name]\n\nCreated by Mrityunjay Pandey, AIMarketer Pvt. Ltd."
        }
    ],
};

const BASE_API_URL = API_CONFIG.BASE_URL;
const TOKEN_STORAGE_KEY = "access_token";
const LOGIN_PAGE_PATH = "login.html";
let analyticsRequestVersion = 0;
let analyticsMode = "campaign_summary";
let selectedStrategyId = "";
let strategyOptions = [];
let strategyVersionMetrics = [];
let performanceChartMode = "campaign_summary";
let strategyHistoryOptions = [];
let strategyHistoryRequestVersion = 0;
let campaignStrategyOptions = [];
let campaignStrategyVersionOptions = [];
let strategyVersionRequestToken = 0;
let continentMasterOptions = [];
let businessCategoryMasterOptions = [];
let isCreateCampaignInFlight = false;
let currentEditingCampaignId = null;
let currentEditingCampaignBudget = null;
let leadLocationState = {
    text: "",
    lat: null,
    lng: null,
    place_id: null,
};
let browserExtensionPayloadState = null;
let adminApiKeysLoaded = false;
let adminUsersLoaded = false;
let adminLicensesLoaded = false;
let adminOrganizationsLoaded = false;
let currentAdminSection = 'users';
let adminModalSubmitHandler = null;
let enrichmentPreviewState = {
    columns: [],
    preview: [],
    mapping: {}
};
let autosuggestRegistry = {};

const CONTINENT_COUNTRY_MAP = {
    "Asia": ["India", "Indonesia", "Malaysia", "Singapore", "Thailand", "Vietnam", "Philippines", "Japan", "South Korea", "China"],
    "Africa": ["South Africa", "Nigeria", "Kenya", "Egypt", "Morocco", "Ghana", "Ethiopia"],
    "Europe": ["United Kingdom", "Germany", "France", "Italy", "Spain", "Netherlands", "Sweden"],
    "MENA": ["UAE", "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman", "Jordan"],
    "North America": ["United States", "Canada", "Mexico"],
    "South America": ["Brazil", "Argentina", "Chile", "Colombia", "Peru"],
};

const DEFAULT_BUSINESS_CATEGORIES = [
    "Technology",
    "Healthcare",
    "Finance",
    "Manufacturing",
    "Professional Services",
    "Retail",
    "Education",
    "Software Development",
    "Data Analytics",
    "Cloud Services",
    "Cybersecurity",
    "Artificial Intelligence",
    "Consulting",
    "Marketing Agency",
];

const COMPANY_SIZE_OPTIONS = ["Large", "Medium", "Small"];

function debounce(fn, wait = 300) {
    let timeoutId = null;
    return function debounced(...args) {
        if (timeoutId) {
            window.clearTimeout(timeoutId);
        }
        timeoutId = window.setTimeout(() => {
            fn.apply(this, args);
        }, wait);
    };
}

function sortStringsAsc(values) {
    return [...new Set((Array.isArray(values) ? values : [])
        .map((value) => String(value || '').trim())
        .filter(Boolean))]
        .sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
}

function normalizeAutosuggestOptions(options) {
    const normalized = (Array.isArray(options) ? options : [])
        .map((option) => {
            if (option && typeof option === 'object') {
                const value = String(option.value ?? '').trim();
                const label = String(option.label ?? option.value ?? '').trim();
                return value || label ? { value: value || label, label: label || value } : null;
            }

            const text = String(option || '').trim();
            return text ? { value: text, label: text } : null;
        })
        .filter(Boolean);

    const deduped = [];
    const seen = new Set();
    normalized.forEach((option) => {
        const key = `${option.value}::${option.label}`.toLowerCase();
        if (seen.has(key)) return;
        seen.add(key);
        deduped.push({
            value: option.value,
            label: option.label,
            searchText: option.label.toLowerCase(),
            valueText: option.value.toLowerCase(),
        });
    });

    return deduped.sort((a, b) => a.label.localeCompare(b.label, undefined, { sensitivity: 'base' }));
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function escapeRegExp(value) {
    return String(value ?? '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlightMatch(text, query) {
    const sourceText = String(text ?? '');
    const searchQuery = String(query ?? '').trim();
    if (!searchQuery) {
        return escapeHtml(sourceText);
    }

    const pattern = new RegExp(`(${escapeRegExp(searchQuery)})`, 'ig');
    return escapeHtml(sourceText).replace(pattern, '<mark class="autosuggest__match">$1</mark>');
}

function findAutosuggestOption(options, value) {
    const normalizedValue = String(value || '').trim().toLowerCase();
    if (!normalizedValue) return null;
    return (Array.isArray(options) ? options : []).find((option) => (
        option.searchText === normalizedValue || option.valueText === normalizedValue
    )) || null;
}

function getCountryOptionsForContinent(continentName) {
    const safeContinent = String(continentName || '').trim();
    return sortStringsAsc(CONTINENT_COUNTRY_MAP[safeContinent] || []);
}

function getAutosuggestLiveRegion() {
    let region = document.getElementById('autosuggestStatus');
    if (region) return region;

    region = document.createElement('div');
    region.id = 'autosuggestStatus';
    region.className = 'sr-only';
    region.setAttribute('aria-live', 'polite');
    region.setAttribute('aria-atomic', 'true');
    document.body.appendChild(region);
    return region;
}

function announceAutosuggestMessage(message) {
    const region = getAutosuggestLiveRegion();
    region.textContent = String(message || '');
}

function setAutosuggestExpanded(instance, expanded) {
    if (!instance?.input) return;
    instance.input.setAttribute('aria-expanded', expanded ? 'true' : 'false');
}

function updateAutosuggestAriaActiveDescendant(instance) {
    if (!instance?.input) return;

    const activeOption = instance.visibleOptions?.[instance.activeIndex];
    if (activeOption?.domId) {
        instance.input.setAttribute('aria-activedescendant', activeOption.domId);
        return;
    }

    instance.input.removeAttribute('aria-activedescendant');
}

function setAutosuggestLoading(target, isLoading) {
    const instance = typeof target === 'string' ? autosuggestRegistry[target] : target;
    if (!instance?.spinner) return;

    if (instance.loadingTimer) {
        window.clearTimeout(instance.loadingTimer);
        instance.loadingTimer = null;
    }

    if (isLoading) {
        instance.loadingTimer = window.setTimeout(() => {
            instance.spinner.classList.remove('hidden');
            if (instance.wrapper) {
                instance.wrapper.classList.add('autosuggest--loading');
            }
            instance.input?.setAttribute('aria-busy', 'true');
            instance.loadingTimer = null;
        }, 150);
        return;
    }

    instance.spinner.classList.add('hidden');
    if (instance.wrapper) {
        instance.wrapper.classList.remove('autosuggest--loading');
    }
    instance.input?.setAttribute('aria-busy', 'false');
}

function hideAutosuggestMenu(instance) {
    if (!instance?.panel) return;
    instance.panel.innerHTML = '';
    instance.panel.classList.add('hidden');
    instance.activeIndex = -1;
    instance.visibleOptions = [];
    setAutosuggestExpanded(instance, false);
    updateAutosuggestAriaActiveDescendant(instance);
}

function renderAutosuggestMenu(instance, query = '') {
    if (!instance?.panel) return;

    const normalizedQuery = String(query || '').trim().toLowerCase();
    const options = Array.isArray(instance.options) ? instance.options : [];
    const visibleOptions = normalizedQuery
        ? options.filter((option) => option.searchText.includes(normalizedQuery) || option.valueText.includes(normalizedQuery))
        : options.slice(0, instance.defaultVisibleCount || 8);

    instance.visibleOptions = visibleOptions.map((option, index) => ({
        ...option,
        domId: `${instance.panel.id}-option-${index}`
    }));
    instance.activeIndex = visibleOptions.length ? 0 : -1;

    if (!instance.visibleOptions.length) {
        instance.panel.innerHTML = '<div class="autosuggest__empty" role="status">No results found</div>';
        instance.panel.classList.remove('hidden');
        setAutosuggestExpanded(instance, true);
        updateAutosuggestAriaActiveDescendant(instance);
        announceAutosuggestMessage(`No results found for ${query || 'this field'}.`);
        return;
    }

    instance.panel.innerHTML = instance.visibleOptions
        .map((option, index) => `
            <button
                type="button"
                class="autosuggest__option${index === instance.activeIndex ? ' autosuggest__option--active' : ''}"
                data-autosuggest-value="${escapeHtml(option.value)}"
                id="${option.domId}"
                role="option"
                aria-selected="${index === instance.activeIndex ? 'true' : 'false'}"
            >${highlightMatch(option.label, query)}</button>
        `)
        .join('');
    instance.panel.classList.remove('hidden');
    setAutosuggestExpanded(instance, true);
    updateAutosuggestAriaActiveDescendant(instance);
    announceAutosuggestMessage(`${instance.visibleOptions.length} suggestion${instance.visibleOptions.length === 1 ? '' : 's'} available.`);
}

function updateAutosuggestActiveOption(instance) {
    if (!instance?.panel) return;
    const items = instance.panel.querySelectorAll('.autosuggest__option');
    items.forEach((item, index) => {
        const isActive = index === instance.activeIndex;
        item.classList.toggle('autosuggest__option--active', isActive);
        item.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    updateAutosuggestAriaActiveDescendant(instance);
}

function selectAutosuggestOption(instance, option) {
    if (!instance?.input || !option) return;
    instance.input.value = option.label;
    if (instance.select) {
        instance.select.value = option.value;
        instance.select.dispatchEvent(new Event('change', { bubbles: true }));
    }
    if (typeof instance.onSelect === 'function') {
        instance.onSelect(option.value, option);
    }
    announceAutosuggestMessage(`${option.label} selected.`);
    hideAutosuggestMenu(instance);
}

function setAutosuggestValue(inputId, value) {
    const instance = autosuggestRegistry[inputId];
    if (!instance?.input) return;
    const exactMatch = findAutosuggestOption(instance.options, value);
    instance.input.value = exactMatch ? exactMatch.label : String(value || '').trim();
    if (instance.select && exactMatch) {
        instance.select.value = exactMatch.value;
    }
}

function setAutosuggestOptions(inputId, options) {
    const instance = autosuggestRegistry[inputId];
    if (!instance) return;

    instance.options = normalizeAutosuggestOptions(options);
    const currentValue = String(instance.input?.value || '').trim();
    const exactMatch = findAutosuggestOption(instance.options, currentValue);
    if (currentValue && exactMatch) {
        instance.input.value = exactMatch.label;
        if (instance.select) {
            instance.select.value = exactMatch.value;
        }
    }
    if (!currentValue) {
        hideAutosuggestMenu(instance);
    }
}

function syncEnhancedSelectUI(selectOrId) {
    const select = typeof selectOrId === 'string'
        ? document.getElementById(selectOrId)
        : selectOrId;
    if (!(select instanceof HTMLSelectElement)) return;

    const instance = autosuggestRegistry[select.id];
    if (!instance?.input) return;

    const options = Array.from(select.options).map((option) => ({
        value: option.value,
        label: option.textContent || option.label || option.value
    }));
    const suggestionOptions = options.filter((option) => String(option.value || '').trim() !== '');
    instance.options = normalizeAutosuggestOptions(suggestionOptions);
    instance.input.disabled = Boolean(select.disabled);
    instance.input.required = Boolean(instance.originalRequired);
    instance.panel.classList.toggle('hidden', true);

    const emptyOption = options.find((option) => String(option.value || '').trim() === '');
    if (emptyOption?.label) {
        instance.input.placeholder = emptyOption.label;
    }

    const selectedOption = options.find((option) => String(option.value) === String(select.value));
    instance.input.value = selectedOption && String(selectedOption.value || '').trim() !== ''
        ? selectedOption.label
        : '';
    hideAutosuggestMenu(instance);
}

function initAutosuggestField(config) {
    const input = document.getElementById(config.inputId);
    const panel = document.getElementById(config.panelId);
    if (!input || !panel) return;

    const wrapper = input.closest('.autosuggest');
    let spinner = wrapper?.querySelector('.autosuggest__spinner');
    if (!spinner && wrapper) {
        spinner = document.createElement('span');
        spinner.className = 'autosuggest__spinner hidden';
        spinner.setAttribute('aria-hidden', 'true');
        wrapper.appendChild(spinner);
    }

    const instance = {
        input,
        panel,
        wrapper,
        spinner,
        options: [],
        visibleOptions: [],
        activeIndex: -1,
        defaultVisibleCount: config.defaultVisibleCount || 8,
        onSelect: config.onSelect,
        onInputChange: config.onInputChange,
    };
    autosuggestRegistry[config.inputId] = instance;

    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-controls', panel.id);
    input.setAttribute('aria-busy', 'false');
    panel.setAttribute('role', 'listbox');

    const debouncedRender = debounce(() => {
        renderAutosuggestMenu(instance, input.value);
    }, 300);

    if (!input.dataset.autosuggestBound) {
        input.addEventListener('input', () => {
            const exactMatch = findAutosuggestOption(instance.options, input.value);
            if (instance.select) {
                instance.select.value = exactMatch ? exactMatch.value : '';
            }
            if (typeof instance.onInputChange === 'function') {
                instance.onInputChange(input.value);
            }
            debouncedRender();
        });
        input.addEventListener('focus', () => {
            renderAutosuggestMenu(instance, input.value);
        });
        input.addEventListener('keydown', (event) => {
            if (panel.classList.contains('hidden') && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
                renderAutosuggestMenu(instance, input.value);
            }

            if (event.key === 'ArrowDown') {
                if (!instance.visibleOptions.length) return;
                event.preventDefault();
                instance.activeIndex = (instance.activeIndex + 1) % instance.visibleOptions.length;
                updateAutosuggestActiveOption(instance);
                return;
            }

            if (event.key === 'ArrowUp') {
                if (!instance.visibleOptions.length) return;
                event.preventDefault();
                instance.activeIndex = (instance.activeIndex - 1 + instance.visibleOptions.length) % instance.visibleOptions.length;
                updateAutosuggestActiveOption(instance);
                return;
            }

            if (event.key === 'Enter') {
                const activeOption = instance.visibleOptions[instance.activeIndex];
                if (activeOption) {
                    event.preventDefault();
                    selectAutosuggestOption(instance, activeOption);
                }
                return;
            }

            if (event.key === 'Escape') {
                hideAutosuggestMenu(instance);
            }
        });
        input.addEventListener('blur', () => {
            window.setTimeout(() => {
                if (instance.select) {
                    const exactMatch = findAutosuggestOption(instance.options, input.value);
                    if (exactMatch) {
                        instance.input.value = exactMatch.label;
                        instance.select.value = exactMatch.value;
                    }
                }
                hideAutosuggestMenu(instance);
            }, 150);
        });
        input.dataset.autosuggestBound = '1';
    }

    if (!panel.dataset.autosuggestBound) {
        panel.addEventListener('mousedown', (event) => {
            const button = event.target.closest('[data-autosuggest-value]');
            if (!button) return;
            event.preventDefault();
            const option = findAutosuggestOption(instance.options, button.dataset.autosuggestValue);
            if (option) {
                selectAutosuggestOption(instance, option);
            }
        });
        panel.dataset.autosuggestBound = '1';
    }
}

function enhanceSelectToAutosuggest(selectId, config = {}) {
    const select = document.getElementById(selectId);
    if (!(select instanceof HTMLSelectElement) || select.dataset.autosuggestEnhanced) {
        return;
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'autosuggest autosuggest--enhanced';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'form-control autosuggest__input';
    input.id = `${selectId}Autosuggest`;
    input.autocomplete = 'off';
    input.disabled = select.disabled;
    input.required = select.required;

    const panel = document.createElement('div');
    panel.id = `${selectId}Suggestions`;
    panel.className = 'autosuggest__menu hidden';
    panel.setAttribute('aria-label', config.ariaLabel || `${selectId} suggestions`);

    select.insertAdjacentElement('afterend', wrapper);
    wrapper.appendChild(input);
    wrapper.appendChild(panel);

    select.classList.add('autosuggest__native');
    select.setAttribute('aria-hidden', 'true');
    select.tabIndex = -1;
    select.required = false;
    select.dataset.autosuggestEnhanced = '1';

    const label = document.querySelector(`label[for="${selectId}"]`);
    if (label) {
        label.setAttribute('for', input.id);
    }

    initAutosuggestField({
        inputId: input.id,
        panelId: panel.id,
        defaultVisibleCount: config.defaultVisibleCount,
        onSelect: (_value, option) => {
            if (typeof config.onSelect === 'function') {
                config.onSelect(option?.value ?? _value, option);
            }
        }
    });

    const instance = autosuggestRegistry[input.id];
    if (instance) {
        instance.select = select;
        instance.originalRequired = input.required;
        autosuggestRegistry[selectId] = instance;
    }

    syncEnhancedSelectUI(select);

    const observer = new MutationObserver(() => {
        syncEnhancedSelectUI(select);
    });
    observer.observe(select, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ['disabled']
    });

    if (!select.dataset.autosuggestSyncBound) {
        select.addEventListener('change', () => {
            syncEnhancedSelectUI(select);
        });
        select.dataset.autosuggestSyncBound = '1';
    }
}

function validateAutosuggestField(inputId, label, { required = false, options = [] } = {}) {
    const input = document.getElementById(inputId);
    if (!input) return true;

    const value = String(input.value || '').trim();
    if (!value) {
        if (required) {
            showErrorMessage(`${label} is required.`);
            input.focus();
            return false;
        }
        return true;
    }

    const exactMatch = findAutosuggestOption(normalizeAutosuggestOptions(options), value);
    if (!exactMatch) {
        showErrorMessage(`Please choose a valid ${label.toLowerCase()} from the suggestions.`);
        input.focus();
        return false;
    }

    input.value = exactMatch.value;
    return true;
}

function validateBusinessProfileAutosuggestFields() {
    const continentValue = String(document.getElementById('continent')?.value || '').trim();
    const validations = [
        validateAutosuggestField('industry', 'Industry', {
            required: true,
            options: businessCategoryMasterOptions.length ? businessCategoryMasterOptions : DEFAULT_BUSINESS_CATEGORIES
        }),
        validateAutosuggestField('companySize', 'Company Size', {
            required: true,
            options: COMPANY_SIZE_OPTIONS
        }),
        validateAutosuggestField('continent', 'Continent', {
            required: true,
            options: continentMasterOptions.length ? continentMasterOptions.map((row) => row.name) : ["Africa", "Asia", "Europe", "MENA", "North America", "South America"]
        }),
        validateAutosuggestField('country', 'Country', {
            required: false,
            options: getCountryOptionsForContinent(continentValue)
        })
    ];

    return validations.every(Boolean);
}

function validateLeadScraperAutosuggestFields() {
    const businessTypeInput = document.getElementById('businessType');
    if (!businessTypeInput || !String(businessTypeInput.value || '').trim()) {
        return true;
    }

    return validateAutosuggestField('businessType', 'Business Type/Category', {
        required: false,
        options: businessCategoryMasterOptions.length ? businessCategoryMasterOptions : DEFAULT_BUSINESS_CATEGORIES
    });
}

function setupAutosuggestControls() {
    initAutosuggestField({ inputId: 'industry', panelId: 'industrySuggestions' });
    initAutosuggestField({ inputId: 'companySize', panelId: 'companySizeSuggestions' });
    initAutosuggestField({
        inputId: 'continent',
        panelId: 'continentSuggestions',
        onInputChange: (value) => {
            const continentOptions = continentMasterOptions.length
                ? continentMasterOptions.map((row) => row.name)
                : ["Africa", "Asia", "Europe", "MENA", "North America", "South America"];
            const exactMatch = findAutosuggestOption(normalizeAutosuggestOptions(continentOptions), value);
            populateCountryDropdown(exactMatch ? exactMatch.value : '', '');
        },
        onSelect: (value) => {
            populateCountryDropdown(value, '');
        }
    });
    initAutosuggestField({ inputId: 'country', panelId: 'countrySuggestions' });
    initAutosuggestField({ inputId: 'businessType', panelId: 'businessTypeSuggestions' });

    enhanceSelectToAutosuggest('strategyHistorySelect', { ariaLabel: 'Strategy history suggestions' });
    enhanceSelectToAutosuggest('strategyVersionSelect', { ariaLabel: 'Strategy version suggestions' });
    enhanceSelectToAutosuggest('campaignObjective', { ariaLabel: 'Campaign objective suggestions' });
    enhanceSelectToAutosuggest('campaignStrategy', { ariaLabel: 'Campaign strategy suggestions' });
    enhanceSelectToAutosuggest('campaignStrategyVersion', { ariaLabel: 'Campaign strategy version suggestions' });
    enhanceSelectToAutosuggest('audienceSource', { ariaLabel: 'Audience source suggestions' });
    enhanceSelectToAutosuggest('analyticsModeSelect', { ariaLabel: 'Analytics view mode suggestions' });
    enhanceSelectToAutosuggest('strategySelect', { ariaLabel: 'Analytics strategy suggestions' });
    enhanceSelectToAutosuggest('templateCategory', { ariaLabel: 'Template category suggestions' });
    enhanceSelectToAutosuggest('templateIndustry', { ariaLabel: 'Template industry suggestions' });
    enhanceSelectToAutosuggest('adminProviderName', { ariaLabel: 'Provider suggestions' });
    enhanceSelectToAutosuggest('adminApiKeyStatus', { ariaLabel: 'API key status suggestions' });

    setAutosuggestOptions('companySize', COMPANY_SIZE_OPTIONS);
}

function redirectToLogin() {
    const currentPath = window.location.pathname || "";
    if (!currentPath.endsWith(`/${LOGIN_PAGE_PATH}`) && !currentPath.endsWith(LOGIN_PAGE_PATH)) {
        window.location.href = LOGIN_PAGE_PATH;
    }
}

function getStoredToken() {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
}

function updateLogoutButtonVisibility() {
    const logoutBtn = document.getElementById('logoutBtn');
    if (!logoutBtn) return;
    logoutBtn.classList.toggle('hidden', !getStoredToken());
}

async function handleLogout() {
    try {
        await apiRequest('/api/auth/logout', 'POST', {});
    } catch (error) {
        console.warn('Logout API failed, continuing with local cleanup:', error);
    } finally {
        localStorage.removeItem('access_token');
        localStorage.removeItem('organization_name');
        localStorage.removeItem('user_id');
        window.location.href = LOGIN_PAGE_PATH;
    }
}


const DEFAULT_ANALYTICS_VIEW_MODEL = {
    totalLeads: 0,
    activeCampaigns: 0,
    conversionRate: 0,
    roi: 0,
    monthlyMetrics: [
        { month: 'Jan', leads: 0, conversions: 0 },
        { month: 'Feb', leads: 0, conversions: 0 },
        { month: 'Mar', leads: 0, conversions: 0 },
        { month: 'Apr', leads: 0, conversions: 0 },
        { month: 'May', leads: 0, conversions: 0 }
    ],
    funnelData: [0, 0, 0, 0]
};

function mapBackendAnalyticsToUIFormat(reportResponse) {
    const reportData = reportResponse?.data || {};
    const totals = reportData?.totals || {};
    const rates = reportData?.rates || {};

    const sent = Number(totals?.sent) || 0;
    const opened = Number(totals?.opened) || 0;
    const clicked = Number(totals?.clicked) || 0;
    const converted = Number(totals?.converted) || 0;

    // Keep existing chart structure with 5 points; backend currently returns aggregate totals only.
    const monthlyMetrics = [
        { month: 'Jan', leads: 0, conversions: 0 },
        { month: 'Feb', leads: 0, conversions: 0 },
        { month: 'Mar', leads: 0, conversions: 0 },
        { month: 'Apr', leads: 0, conversions: 0 },
        { month: 'May', leads: sent, conversions: converted }
    ];

    return {
        totalLeads: sent,
        activeCampaigns: Number(reportData?.total_campaigns) || 0,
        conversionRate: Number(rates?.conversion_rate) || 0,
        roi: Number(rates?.roi) || 0,
        monthlyMetrics,
        funnelData: [sent, opened, clicked, converted]
    };
}

async function loadAnalytics() {
    try {
        const response = await apiRequest('/api/analytics/report?report_type=campaign_summary');
        return mapBackendAnalyticsToUIFormat(response);
    } catch (error) {
        console.error('Analytics loading error:', error);
        return { ...DEFAULT_ANALYTICS_VIEW_MODEL };
    }
}

function mapStrategyAnalyticsToUIFormat(strategyResponse) {
    const overall = strategyResponse?.overall || {};
    const byVersion = Array.isArray(strategyResponse?.by_version) ? strategyResponse.by_version : [];
    strategyVersionMetrics = byVersion.map((row) => ({
        strategy_version_no: Number(row?.strategy_version_no) || 0,
        campaign_count: Number(row?.campaign_count) || 0,
        avg_roi: Number(row?.avg_roi) || 0
    }));

    const sent = Number(overall.total_sent) || 0;
    const opened = Number(overall.total_opened) || 0;
    const clicked = Number(overall.total_clicked) || 0;
    const converted = Number(overall.total_converted) || 0;

    const monthlyMetrics = byVersion.length
        ? byVersion.map((row) => ({
            month: `Version ${Number(row.strategy_version_no) || 0}`,
            leads: Number(row.avg_roi) || 0,
            conversions: Number(row.total_converted) || 0
        }))
        : [{ month: 'Version 1', leads: 0, conversions: 0 }];

    return {
        totalLeads: sent,
        activeCampaigns: Number(overall.campaign_count) || 0,
        conversionRate: Number(overall.avg_conversion_rate) || 0,
        roi: Number(overall.avg_roi) || 0,
        monthlyMetrics,
        funnelData: [sent, opened, clicked, converted]
    };
}

async function loadStrategyOptions() {
    setAutosuggestLoading('strategySelect', true);
    try {
        const response = await apiRequest('/api/strategy/history');
        const rows = Array.isArray(response?.strategies) ? response.strategies : [];
        strategyOptions = rows.map((item) => ({
            id: item.strategy_id,
            label: item.business_name || item.strategy_id
        })).filter((item) => !!item.id);

        const strategySelect = document.getElementById('strategySelect');
        const strategyModeOption = document.querySelector('#analyticsModeSelect option[value="strategy_performance"]');
        if (strategyModeOption) {
            strategyModeOption.disabled = strategyOptions.length === 0;
        }

        if (strategySelect) {
            strategySelect.innerHTML = strategyOptions.length
                ? strategyOptions.map((item) => `<option value="${item.id}">${item.label}</option>`).join('')
                : '<option value="">No strategies available</option>';
            strategySelect.disabled = strategyOptions.length === 0;
            syncEnhancedSelectUI(strategySelect);
        }

        if (strategyOptions.length > 0) {
            if (!selectedStrategyId || !strategyOptions.some((opt) => opt.id === selectedStrategyId)) {
                selectedStrategyId = strategyOptions[0].id;
            }
            if (strategySelect) strategySelect.value = selectedStrategyId;
            syncEnhancedSelectUI('strategySelect');
        } else {
            selectedStrategyId = "";
            if (analyticsMode === "strategy_performance") {
                analyticsMode = "campaign_summary";
                const modeSelect = document.getElementById('analyticsModeSelect');
                if (modeSelect) modeSelect.value = analyticsMode;
                syncEnhancedSelectUI('analyticsModeSelect');
            }
        }
    } catch (error) {
        console.error('Strategy options loading error:', error);
        strategyOptions = [];
    } finally {
        setAutosuggestLoading('strategySelect', false);
    }
}

async function loadStrategyAnalytics(strategyId) {
    if (!strategyId) {
        return null;
    }
    try {
        return await apiRequest(`/api/analytics/strategy/${encodeURIComponent(strategyId)}`);
    } catch (error) {
        console.error('Strategy analytics loading error:', error);
        return null;
    }
}

function syncAnalyticsControls() {
    const modeSelect = document.getElementById('analyticsModeSelect');
    const strategyWrapper = document.getElementById('strategySelectWrapper');
    const strategySelect = document.getElementById('strategySelect');
    const strategyBadge = document.getElementById('strategyModeBadge');

    if (modeSelect) {
        modeSelect.value = analyticsMode;
        syncEnhancedSelectUI(modeSelect);
    }
    if (strategyWrapper) {
        strategyWrapper.style.display = analyticsMode === 'strategy_performance' ? '' : 'none';
    }
    if (strategySelect && selectedStrategyId) {
        strategySelect.value = selectedStrategyId;
        syncEnhancedSelectUI(strategySelect);
    }
    if (strategyBadge) {
        strategyBadge.classList.toggle('hidden', analyticsMode !== 'strategy_performance');
    }
}

function setupAnalyticsControls() {
    const modeSelect = document.getElementById('analyticsModeSelect');
    const strategySelect = document.getElementById('strategySelect');

    if (modeSelect && !modeSelect.dataset.bound) {
        modeSelect.addEventListener('change', async function () {
            analyticsMode = this.value;
            if (analyticsMode === 'strategy_performance' && strategyOptions.length === 0) {
                await loadStrategyOptions();
            }
            syncAnalyticsControls();
            loadAndRenderAnalytics();
        });
        modeSelect.dataset.bound = '1';
    }

    if (strategySelect && !strategySelect.dataset.bound) {
        strategySelect.addEventListener('change', function () {
            selectedStrategyId = this.value || "";
            loadAndRenderAnalytics();
        });
        strategySelect.dataset.bound = '1';
    }
}

async function loadAndRenderAnalytics() {
    analyticsRequestVersion += 1;
    const localVersion = analyticsRequestVersion;

    setupAnalyticsControls();
    syncAnalyticsControls();

    let analyticsData = { ...DEFAULT_ANALYTICS_VIEW_MODEL };
    if (analyticsMode === 'strategy_performance') {
        if (strategyOptions.length === 0) {
            await loadStrategyOptions();
            if (localVersion !== analyticsRequestVersion) {
                return;
            }
            syncAnalyticsControls();
        }

        if (selectedStrategyId) {
            const strategyResponse = await loadStrategyAnalytics(selectedStrategyId);
            if (localVersion !== analyticsRequestVersion) {
                return;
            }
            analyticsData = strategyResponse
                ? mapStrategyAnalyticsToUIFormat(strategyResponse)
                : { ...DEFAULT_ANALYTICS_VIEW_MODEL };
            if (!strategyResponse) {
                strategyVersionMetrics = [];
            }
        } else {
            analyticsData = await loadAnalytics();
            strategyVersionMetrics = [];
        }
    } else {
        analyticsData = await loadAnalytics();
        strategyVersionMetrics = [];
    }

    if (localVersion !== analyticsRequestVersion) {
        return;
    }

    updateAnalyticsDashboard(analyticsData);
    renderBestStrategyVersionHint();
}

function renderBestStrategyVersionHint() {
    const hintEl = document.getElementById('bestStrategyVersionHint');
    if (!hintEl) return;

    if (analyticsMode !== 'strategy_performance' || strategyVersionMetrics.length === 0) {
        hintEl.classList.add('hidden');
        hintEl.textContent = '';
        return;
    }

    const sorted = [...strategyVersionMetrics].sort((a, b) => b.avg_roi - a.avg_roi);
    const best = sorted[0];
    const baseline = sorted[sorted.length - 1];
    const delta = best.avg_roi - baseline.avg_roi;

    hintEl.textContent = `Best Performing Version: V${best.strategy_version_no} (${delta >= 0 ? '+' : ''}${delta.toFixed(2)}% vs V${baseline.strategy_version_no})`;
    hintEl.classList.remove('hidden');
}

async function loginOrganization(credentials = null) {
    redirectToLogin();
    return null;
}

async function apiRequest(path, method = "GET", body = null) {
    const token = getStoredToken();
    if (!token) {
        redirectToLogin();
        throw new Error('Authentication required');
    }

    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
    };

    const options = {
        method,
        headers
    };

    if (body !== null) {
        options.body = JSON.stringify(body);
    }

    let response;
    try {
        response = await fetch(`${BASE_API_URL}${path}`, options);
    } catch (networkError) {
        throw new Error('Network error. Please check backend connectivity.');
    }

    if (response.status === 204) {
        return { success: true };
    }

    let data = {};
    try {
        data = await response.json();
    } catch (parseError) {
        data = {};
    }

    if (!response.ok) {
        if (response.status === 401) {
            localStorage.removeItem(TOKEN_STORAGE_KEY);
            redirectToLogin();
        }
        const message = data?.detail || data?.message || `Request failed with status ${response.status}`;
        throw new Error(message);
    }

    return data;
}


async function apiRequestWithOptions(path, options = {}) {
    const token = getStoredToken();
    if (!token) {
        redirectToLogin();
        throw new Error('Authentication required');
    }

    const method = options.method || 'GET';
    const isFormData = !!options.isFormData;
    const headers = {
        'Authorization': `Bearer ${token}`,
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(options.headers || {})
    };

    const requestOptions = {
        method,
        headers,
        body: options.body || null
    };

    let response;
    try {
        response = await fetch(`${BASE_API_URL}${path}`, requestOptions);
    } catch (networkError) {
        throw new Error('Network error. Please check backend connectivity.');
    }

    let data = {};
    try {
        data = await response.json();
    } catch (parseError) {
        data = {};
    }

    if (!response.ok) {
        if (response.status === 401) {
            localStorage.removeItem(TOKEN_STORAGE_KEY);
            redirectToLogin();
        }
        const message = data?.detail || data?.message || `Request failed with status ${response.status}`;
        throw new Error(message);
    }

    return data;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function normalizeApiLead(lead) {
    const safeLead = (lead && typeof lead === 'object') ? lead : {};

    return {
        ...safeLead,
        businessName: safeLead.businessName || safeLead.business_name || safeLead.name || 'N/A',
        address: safeLead.address || safeLead.location || safeLead.formatted_address || 'N/A',
        email: safeLead.email || 'N/A',
        phone: safeLead.phone || 'N/A',
        website: safeLead.website || safeLead.url || safeLead.html_url || 'N/A',
        rating: safeLead.rating ?? '-',
        category: safeLead.category || safeLead.business_type || 'N/A'
    };
}

function formatStrategyKey(key) {
    return key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
}

function normalizeStrategyForDisplay(apiStrategy) {
    const timeline = apiStrategy.campaign_timeline && typeof apiStrategy.campaign_timeline === 'object'
        ? Object.values(apiStrategy.campaign_timeline)
            .filter(phase => phase && typeof phase === 'object')
            .map(phase => `${phase.name || 'Phase'} (${phase.duration || 'TBD'})`)
            .join(' | ')
        : 'Timeline unavailable';

    const budgetAllocation = Object.fromEntries(
        Object.entries(apiStrategy.budget_allocation || {}).map(([key, value]) => [formatStrategyKey(key), `${Number(value) || 0}%`])
    );

    const keyMessages = Array.isArray(apiStrategy.target_segments) && apiStrategy.target_segments.length > 0
        ? apiStrategy.target_segments
        : [apiStrategy.insights || 'No strategic insights returned'];

    return {
        channels: Array.isArray(apiStrategy.recommended_channels) ? apiStrategy.recommended_channels : [],
        budgetAllocation,
        timeline,
        keyMessages,
        contentStrategy: Array.isArray(apiStrategy.content_strategy) ? apiStrategy.content_strategy : [],
        targetBudget: appData.businessProfile?.budget || 0,
        targetAudience: appData.businessProfile?.targetAudience || '',
        companySize: appData.businessProfile?.companySize || ''
    };
}

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Initializing MAi App');

    if (!getStoredToken()) {
        redirectToLogin();
        return;
    }
    
    // Small delay to ensure all elements are rendered
    setTimeout(async () => {
        initializeApp();
        await loadCurrentUserContext();
        applyAdminVisibility();
        setupNavigation();
        setupAutosuggestControls();
        setupEventListeners();
        await loadContinentMasterData();
        await loadBusinessCategoryMasterData();
        loadDataFromStorage();
        initializeSampleData();
        
        // Show initial module
        showModule('business-profile');
        
        console.log('App initialization complete');
    }, 100);
});

function initializeApp() {
    console.log('Initializing application...');
    
    // Initialize sample campaigns if none exist
    if (appData.campaigns.length === 0) {
        appData.campaigns = [
            {
                id: 1,
                name: "Q1 Lead Generation Campaign",
                objective: "Lead Generation",
                channels: ["Email", "LinkedIn"],
                status: 'Active',
                created: new Date().toLocaleDateString(),
                metrics: {
                    sent: 1250,
                    opened: 625,
                    clicked: 87,
                    converted: 12
                }
            },
            {
                id: 2,
                name: "Brand Awareness Initiative",
                objective: "Brand Awareness",
                channels: ["LinkedIn", "WhatsApp"],
                status: 'Active',
                created: new Date().toLocaleDateString(),
                metrics: {
                    sent: 890,
                    opened: 534,
                    clicked: 76,
                    converted: 8
                }
            }
        ];
    }
    
    console.log('App data initialized:', appData);
}

async function loadContinentMasterData() {
    setAutosuggestLoading('continent', true);
    try {
        const response = await apiRequest('/api/strategy/master/continents');
        const rows = Array.isArray(response?.continents) ? response.continents : [];
        continentMasterOptions = sortStringsAsc(rows
            .map((row) => ({
                id: row?.id,
                name: String(row?.name || '').trim()
            }))
            .filter((row) => row.name.length > 0)
            .map((row) => row.name))
            .map((name, index) => ({ id: index + 1, name }));
    } catch (error) {
        console.error('Continent master loading error:', error);
        continentMasterOptions = [];
    } finally {
        setAutosuggestLoading('continent', false);
    }
    populateContinentDropdown();
}

async function loadBusinessCategoryMasterData() {
    setAutosuggestLoading('industry', true);
    setAutosuggestLoading('businessType', true);
    try {
        const response = await apiRequest('/api/strategy/master/business-categories');
        const rows = Array.isArray(response?.business_categories) ? response.business_categories : [];
        businessCategoryMasterOptions = sortStringsAsc(rows
            .map((row) => String(row?.category_name || '').trim())
            .filter((name) => name.length > 0));
    } catch (error) {
        console.error('Business category master loading error:', error);
        businessCategoryMasterOptions = [];
    } finally {
        setAutosuggestLoading('industry', false);
        setAutosuggestLoading('businessType', false);
    }
    populateBusinessCategoryDropdowns();
}

function populateBusinessCategoryDropdowns() {
    const options = businessCategoryMasterOptions.length
        ? businessCategoryMasterOptions
        : DEFAULT_BUSINESS_CATEGORIES;
    populateSingleCategoryDropdown('industry', 'Select Industry', options);
    populateSingleCategoryDropdown('businessType', 'Select Category', options);
}

function populateSingleCategoryDropdown(selectId, placeholder, options) {
    const input = document.getElementById(selectId);
    if (!input) return;

    input.placeholder = placeholder;
    setAutosuggestOptions(selectId, options);

    const previousValue = String(input.value || '').trim();
    const exactMatch = findAutosuggestOption(normalizeAutosuggestOptions(options), previousValue);
    if (exactMatch) {
        input.value = exactMatch.value;
    }
}

function populateContinentDropdown() {
    const continentInput = document.getElementById('continent');
    if (!continentInput) return;

    const options = continentMasterOptions.length
        ? continentMasterOptions.map((row) => row.name)
        : sortStringsAsc(["Asia", "Africa", "Europe", "MENA", "North America", "South America"]);

    continentInput.placeholder = 'Select Continent';
    setAutosuggestOptions('continent', options);
}

function populateCountryDropdown(continentName, selectedCountry = '') {
    const countryInput = document.getElementById('country');
    if (!countryInput) return;

    const countries = getCountryOptionsForContinent(continentName);
    countryInput.placeholder = 'Select Country (Optional)';
    setAutosuggestOptions('country', countries);

    if (selectedCountry) {
        const exactMatch = findAutosuggestOption(normalizeAutosuggestOptions(countries), selectedCountry);
        countryInput.value = exactMatch ? exactMatch.value : '';
        return;
    }

    const currentValue = String(countryInput.value || '').trim();
    if (currentValue && !findAutosuggestOption(normalizeAutosuggestOptions(countries), currentValue)) {
        countryInput.value = '';
    }
}

function updateProfileCTAState() {
    const ctaBtn = document.getElementById('generateStrategyFromProfile');
    if (!ctaBtn) return;
    ctaBtn.classList.toggle('hidden', !appData.businessProfile);
}

async function loadCurrentUserContext() {
    try {
        const response = await apiRequest('/api/auth/me');
        const role = String(response?.user?.role || '').trim().toLowerCase();
        const organizationId = String(response?.user?.organization_id || '').trim();
        appData.currentUserRole = role || null;
        appData.currentOrganizationId = organizationId || null;
    } catch (error) {
        console.error('Failed to load current user context:', error);
        appData.currentUserRole = null;
        appData.currentOrganizationId = null;
    }
}

function isSuperAdminUser() {
    return appData.currentUserRole === 'super_admin';
}

function isOrgAdminUser() {
    return appData.currentUserRole === 'admin';
}

function isAdminUser() {
    return isSuperAdminUser() || isOrgAdminUser();
}

function applyAdminVisibility() {
    const adminTab = document.getElementById('adminApiKeysTab');
    const adminModule = document.getElementById('admin-api-keys');
    const orgTabBtn = document.getElementById('adminOrganizationsTabBtn');
    const canAccessAdmin = isAdminUser();

    if (adminTab) {
        adminTab.classList.toggle('hidden', !canAccessAdmin);
    }
    if (adminModule && !canAccessAdmin) {
        adminModule.classList.add('hidden');
    }
    if (orgTabBtn) {
        orgTabBtn.classList.toggle('hidden', !isSuperAdminUser());
    }
}

async function handleGenerateStrategyFromProfile() {
    if (!appData.businessProfile) {
        showErrorMessage('Please complete your Business Profile first.');
        return;
    }

    const strategyTab = document.querySelector('.nav__tab[data-module="strategy-generator"]');
    showModule('strategy-generator');
    if (strategyTab) {
        setActiveTab(strategyTab);
    }
    await generateAIStrategy();
}

function setupNavigation() {
    console.log('Setting up navigation...');
    
    const navTabs = document.querySelectorAll('.nav__tab');
    console.log('Found navigation tabs:', navTabs.length);
    
    navTabs.forEach((tab, index) => {
        const moduleId = tab.getAttribute('data-module');
        console.log(`Tab ${index}: ${moduleId}`);
        
        // Remove any existing listeners
        tab.removeEventListener('click', handleTabClick);
        
        // Add click listener
        tab.addEventListener('click', handleTabClick);
    });
}

function handleTabClick(event) {
    event.preventDefault();
    event.stopPropagation();
    
    const moduleId = this.getAttribute('data-module');
    console.log('Navigation tab clicked:', moduleId);
    
    if (moduleId) {
        showModule(moduleId);
        setActiveTab(this);
    }
}

function showModule(moduleId) {
    console.log('Showing module:', moduleId);

    if (moduleId === 'admin-api-keys' && !isAdminUser()) {
        showErrorMessage('Admin access required.');
        return;
    }
    
    // Hide all modules
    const allModules = document.querySelectorAll('.module');
    allModules.forEach(module => {
        module.classList.add('hidden');
    });
    
    // Show target module
    const targetModule = document.getElementById(moduleId);
    if (targetModule) {
        targetModule.classList.remove('hidden');
        console.log('Successfully showed module:', moduleId);
        
        // Handle special initialization for specific modules
        handleModuleSpecialInit(moduleId);
    } else {
        console.error('Module not found:', moduleId);
    }
}

function handleModuleSpecialInit(moduleId) {
    switch(moduleId) {
        case 'strategy-generator':
            updateStrategyGeneratorState();
            loadStrategyHistoryOptions();
            break;
        case 'analytics':
            setTimeout(() => { loadAndRenderAnalytics(); }, 200);
            break;
        case 'campaign-manager':
            displayActiveCampaigns();
            loadCampaignStrategyOptions();
            break;
        case 'templates':
            populateTemplateLibrary();
            break;
        case 'admin-api-keys':
            setupAdminDashboardListeners();
            showAdminSection(currentAdminSection);
            break;
    }
}

function setActiveTab(activeTab) {
    // Remove active class from all tabs
    document.querySelectorAll('.nav__tab').forEach(tab => {
        tab.classList.remove('nav__tab--active');
    });
    
    // Add active class to clicked tab
    if (activeTab) {
        activeTab.classList.add('nav__tab--active');
    }
}

function initializeSampleData() {
    // Populate templates on load
    setTimeout(() => {
        populateTemplateLibrary();
    }, 300);
}

function setupEventListeners() {
    console.log('Setting up event listeners...');

    // Business Profile Form
    const businessProfileForm = document.getElementById('businessProfileForm');
    if (businessProfileForm) {
        businessProfileForm.addEventListener('submit', handleBusinessProfileSubmit);
        if (!businessProfileForm.dataset.previewBound) {
            businessProfileForm.addEventListener('input', updateBusinessProfilePreview);
            businessProfileForm.addEventListener('change', updateBusinessProfilePreview);
            businessProfileForm.dataset.previewBound = '1';
        }
        console.log('Business profile form listener added');
    }

    const continentSelect = document.getElementById('continent');
    if (continentSelect && !continentSelect.dataset.bound) {
        continentSelect.addEventListener('change', function () {
            populateCountryDropdown(this.value, '');
        });
        continentSelect.dataset.bound = '1';
    }

    const generateFromProfileBtn = document.getElementById('generateStrategyFromProfile');
    if (generateFromProfileBtn && !generateFromProfileBtn.dataset.bound) {
        generateFromProfileBtn.addEventListener('click', handleGenerateStrategyFromProfile);
        generateFromProfileBtn.dataset.bound = '1';
    }

    // AI Strategy Generator
    const generateStrategyBtn = document.getElementById('generateStrategy');
    if (generateStrategyBtn) {
        generateStrategyBtn.addEventListener('click', generateAIStrategy);
    }

    const strategyHistorySelect = document.getElementById('strategyHistorySelect');
    if (strategyHistorySelect && !strategyHistorySelect.dataset.bound) {
        strategyHistorySelect.addEventListener('change', handleStrategyHistoryChange);
        strategyHistorySelect.dataset.bound = '1';
    }

    const strategyVersionSelect = document.getElementById('strategyVersionSelect');
    if (strategyVersionSelect && !strategyVersionSelect.dataset.bound) {
        strategyVersionSelect.addEventListener('change', handleStrategyVersionChange);
        strategyVersionSelect.dataset.bound = '1';
    }

    const createCampaignFromStrategyBtn = document.getElementById('createCampaignFromStrategyBtn');
    if (createCampaignFromStrategyBtn && !createCampaignFromStrategyBtn.dataset.bound) {
        createCampaignFromStrategyBtn.addEventListener('click', createCampaignFromStrategy);
        createCampaignFromStrategyBtn.dataset.bound = '1';
    }

    const generateLeadsFromStrategyBtn = document.getElementById('generateLeadsFromStrategyBtn');
    if (generateLeadsFromStrategyBtn && !generateLeadsFromStrategyBtn.dataset.bound) {
        generateLeadsFromStrategyBtn.addEventListener('click', generateLeadsFromStrategy);
        generateLeadsFromStrategyBtn.dataset.bound = '1';
    }

    const launchStrategyCampaignBtn = document.getElementById('launchStrategyCampaignBtn');
    if (launchStrategyCampaignBtn && !launchStrategyCampaignBtn.dataset.bound) {
        launchStrategyCampaignBtn.addEventListener('click', launchStrategyReviewCampaign);
        launchStrategyCampaignBtn.dataset.bound = '1';
    }

    // Lead Scraper Form
    const leadScraperForm = document.getElementById('leadScraperForm');
    if (leadScraperForm) {
        leadScraperForm.addEventListener('submit', handleLeadScraping);
    }
    setupLeadLocationControls();

    setupSourceSelectionControls();

    // Range slider for radius
    const radiusSlider = document.getElementById('radius');
    if (radiusSlider) {
        radiusSlider.addEventListener('input', function() {
            const rangeValue = document.querySelector('.range-value');
            if (rangeValue) {
                rangeValue.textContent = `${this.value} miles`;
            }
        });
    }

    // Customer Data Enrichment
    const customerDataFile = document.getElementById('customerDataFile');
    if (customerDataFile) {
        customerDataFile.addEventListener('change', handleFileUpload);
    }

    const fileUploadArea = document.getElementById('fileUploadArea');
    if (fileUploadArea) {
        setupDragAndDrop(fileUploadArea);
    }

    const startEnrichmentBtn = document.getElementById('startEnrichment');
    if (startEnrichmentBtn) {
        startEnrichmentBtn.addEventListener('click', startDataEnrichment);
    }

    // Campaign Manager
    setupCampaignManagerListeners();

    // Template filters
    const templateCategory = document.getElementById('templateCategory');
    const templateIndustry = document.getElementById('templateIndustry');
    if (templateCategory) templateCategory.addEventListener('change', filterTemplates);
    if (templateIndustry) templateIndustry.addEventListener('change', filterTemplates);

    // Export functionality
    const exportDataBtn = document.getElementById('exportData');
    if (exportDataBtn) {
        exportDataBtn.addEventListener('click', exportApplicationData);
    }

    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    updateLogoutButtonVisibility();
    updateProfileCTAState();
    setupAdminApiKeysListeners();
    setupAdminDashboardListeners();

    // Modal close functionality
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal__overlay')) {
            closeModal();
            closeAdminCrudModal();
        }
    });
}

// Business Profile Functions
function handleBusinessProfileSubmit(e) {
    e.preventDefault();
    console.log('Business profile form submitted');

    if (!validateBusinessProfileAutosuggestFields()) {
        return;
    }
    
    const businessName = document.getElementById('businessName').value;
    const industry = document.getElementById('industry').value;
    const companySize = document.getElementById('companySize').value;
    const revenue = parseInt(document.getElementById('revenue').value) || 0;
    const continent = document.getElementById('continent').value;
    const country = document.getElementById('country').value;
    const region = document.getElementById('region').value.trim();
    const budget = parseInt(document.getElementById('budget').value) || 0;
    const targetAudience = document.getElementById('targetAudience').value;
    const websiteLink = document.getElementById('websiteLink').value.trim();
    
    const marketingGoals = Array.from(document.querySelectorAll('#business-profile input[type="checkbox"]:checked')).map(cb => cb.value);
    
    const profile = {
        businessName,
        industry,
        companySize,
        revenue,
        continent,
        country,
        region,
        marketingGoals,
        budget,
        targetAudience,
        websiteLink
    };
    
    console.log('Profile data:', profile);
    
    appData.businessProfile = profile;
    saveDataToStorage();
    displayProfileSummary(profile);
    updateProfileCTAState();
    showSuccessMessage('Business profile saved successfully! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
}

function getBusinessProfileFormData() {
    const businessName = String(document.getElementById('businessName')?.value || '').trim();
    const industry = String(document.getElementById('industry')?.value || '').trim();
    const companySize = String(document.getElementById('companySize')?.value || '').trim();
    const revenueValue = String(document.getElementById('revenue')?.value || '').trim();
    const continent = String(document.getElementById('continent')?.value || '').trim();
    const country = String(document.getElementById('country')?.value || '').trim();
    const region = String(document.getElementById('region')?.value || '').trim();
    const budgetValue = String(document.getElementById('budget')?.value || '').trim();
    const targetAudience = String(document.getElementById('targetAudience')?.value || '').trim();
    const websiteLink = String(document.getElementById('websiteLink')?.value || '').trim();
    const marketingGoals = Array.from(document.querySelectorAll('#business-profile input[type="checkbox"]:checked'))
        .map((cb) => String(cb.value || '').trim())
        .filter(Boolean);

    return {
        businessName,
        industry,
        companySize,
        revenue: revenueValue ? parseInt(revenueValue, 10) || 0 : null,
        continent,
        country,
        region,
        marketingGoals,
        budget: budgetValue ? parseInt(budgetValue, 10) || 0 : null,
        targetAudience,
        websiteLink
    };
}

function hasBusinessProfileContent(profile) {
    if (!profile || typeof profile !== 'object') return false;
    return Boolean(
        String(profile.businessName || '').trim() ||
        String(profile.industry || '').trim() ||
        String(profile.companySize || '').trim() ||
        String(profile.continent || '').trim() ||
        String(profile.country || '').trim() ||
        String(profile.region || '').trim() ||
        String(profile.targetAudience || '').trim() ||
        String(profile.websiteLink || '').trim() ||
        Number(profile.revenue) > 0 ||
        Number(profile.budget) > 0 ||
        (Array.isArray(profile.marketingGoals) && profile.marketingGoals.length > 0)
    );
}

function calculateProfileStrength(profile) {
    const safeProfile = profile && typeof profile === 'object' ? profile : {};
    const checks = [
        Boolean(String(safeProfile.businessName || '').trim()),
        Boolean(String(safeProfile.industry || '').trim()),
        Boolean(String(safeProfile.companySize || '').trim()),
        Number(safeProfile.revenue) > 0,
        Boolean(
            String(safeProfile.continent || '').trim() ||
            String(safeProfile.country || '').trim() ||
            String(safeProfile.region || '').trim()
        ),
        Array.isArray(safeProfile.marketingGoals) && safeProfile.marketingGoals.length > 0,
        Number(safeProfile.budget) > 0,
        Boolean(String(safeProfile.targetAudience || '').trim()),
        Boolean(String(safeProfile.websiteLink || '').trim())
    ];

    const completed = checks.filter(Boolean).length;
    return Math.round((completed / checks.length) * 100);
}

function isProfileComplete(profile) {
    const safeProfile = profile && typeof profile === 'object' ? profile : {};
    return Boolean(
        String(safeProfile.businessName || '').trim() &&
        String(safeProfile.industry || '').trim() &&
        String(safeProfile.companySize || '').trim() &&
        Number(safeProfile.revenue) > 0 &&
        Array.isArray(safeProfile.marketingGoals) &&
        safeProfile.marketingGoals.length > 0 &&
        Number(safeProfile.budget) > 0 &&
        String(safeProfile.targetAudience || '').trim() &&
        String(safeProfile.websiteLink || '').trim()
    );
}

function generateAIInsights(profile) {
    const safeProfile = profile && typeof profile === 'object' ? profile : {};
    const insights = [];
    const suggestions = [];
    const industry = String(safeProfile.industry || '').trim().toLowerCase();
    const companySize = String(safeProfile.companySize || '').trim().toLowerCase();
    const goals = Array.isArray(safeProfile.marketingGoals) ? safeProfile.marketingGoals : [];

    if (industry === 'retail') {
        insights.push('Retail companies typically allocate 8-12% of revenue to marketing.');
    }
    if (industry === 'technology' || industry === 'software development' || industry === 'artificial intelligence') {
        insights.push('Technology businesses tend to perform well with content-led lead generation and LinkedIn campaigns.');
    }
    if (industry === 'healthcare') {
        insights.push('Healthcare marketing usually benefits from trust-driven messaging and educational content.');
    }
    if (industry === 'finance') {
        insights.push('Finance campaigns usually convert better when compliance, credibility, and case-led messaging are emphasized.');
    }

    if (companySize === 'small') {
        insights.push('Small companies often benefit from focusing on lead generation and brand awareness before scaling channels.');
    }
    if (companySize === 'medium') {
        insights.push('Mid-sized companies usually see stronger ROI from segmented campaigns across email and paid social.');
    }
    if (companySize === 'large') {
        insights.push('Larger organizations often benefit from multi-channel orchestration with tighter audience segmentation.');
    }

    if (goals.includes('Lead Generation')) {
        insights.push('Lead generation goals usually benefit from combining email nurture with LinkedIn outreach.');
    }
    if (goals.includes('Brand Awareness')) {
        insights.push('Brand awareness goals usually improve with consistent social posting and content amplification.');
    }

    if (!String(safeProfile.websiteLink || '').trim()) {
        suggestions.push('Add a website to improve targeting, enrichment quality, and strategy accuracy.');
    }
    if (!goals.length) {
        suggestions.push('Define at least one marketing goal so strategy generation can prioritize the right channels.');
    }
    if (!String(safeProfile.targetAudience || '').trim()) {
        suggestions.push('Describe the target audience to improve messaging and campaign recommendations.');
    }
    if (!String(safeProfile.continent || '').trim() && !String(safeProfile.country || '').trim() && !String(safeProfile.region || '').trim()) {
        suggestions.push('Add geographic information so the strategy can adapt to the right market context.');
    }
    if (Number(safeProfile.budget) <= 0) {
        suggestions.push('Set a marketing budget so recommendations can align with realistic campaign scope.');
    }

    return { insights, suggestions };
}

function getIndustryBenchmarks(profile) {
    const industry = String(profile?.industry || '').trim().toLowerCase();
    const benchmarks = {
        retail: {
            channels: ['Social Media Ads', 'Influencer Marketing', 'Email Campaigns'],
            conversionRate: '2-4%',
            budgetNote: 'Retail brands often reinvest heavily into seasonal promotions.'
        },
        technology: {
            channels: ['LinkedIn', 'Content Marketing', 'Email Nurturing'],
            conversionRate: '3-7%',
            budgetNote: 'Technology companies usually prioritize demand generation and thought leadership.'
        },
        'software development': {
            channels: ['LinkedIn', 'Case Study Content', 'Email Nurturing'],
            conversionRate: '3-6%',
            budgetNote: 'Software companies often grow pipeline with educational assets and outbound sequencing.'
        },
        healthcare: {
            channels: ['Email', 'Search Ads', 'Educational Content'],
            conversionRate: '2-5%',
            budgetNote: 'Healthcare marketing performs better with trust-led and compliance-aware messaging.'
        },
        finance: {
            channels: ['Email Campaigns', 'LinkedIn Outreach', 'Webinars'],
            conversionRate: '2-5%',
            budgetNote: 'Financial services messaging usually performs best when credibility and proof points are clear.'
        }
    };

    return benchmarks[industry] || {
        channels: ['Email Campaigns', 'LinkedIn Outreach', 'Content Marketing'],
        conversionRate: '2-5%',
        budgetNote: 'Benchmarks vary by segment. Complete more profile details for sharper guidance.'
    };
}

function formatProfileSummaryValue(value, placeholder, formatter = null) {
    const rawValue = Array.isArray(value) ? value.filter(Boolean) : value;
    const hasValue = Array.isArray(rawValue)
        ? rawValue.length > 0
        : !(rawValue === null || rawValue === undefined || String(rawValue).trim() === '');

    if (!hasValue) {
        return `<span class="profile-summary__placeholder">${placeholder}</span>`;
    }

    if (typeof formatter === 'function') {
        return formatter(rawValue);
    }

    return String(rawValue);
}

function renderInsightsDashboard(profile, options = {}) {
    const summaryContent = document.getElementById('profileSummaryContent');
    if (!summaryContent) return;
    const safeProfile = profile && typeof profile === 'object' ? profile : {};
    const showEmptyState = options.showEmptyState !== false && !hasBusinessProfileContent(safeProfile);
    const completed = isProfileComplete(safeProfile);
    const strength = completed ? 100 : calculateProfileStrength(safeProfile);
    const { insights, suggestions } = generateAIInsights(safeProfile);
    const benchmarks = getIndustryBenchmarks(safeProfile);
    const strengthLabel = completed
        ? 'Profile complete. The dashboard is now showing the finalized snapshot.'
        : strength >= 80
            ? 'Strong profile. Strategy generation should be highly contextual.'
            : strength >= 50
                ? 'Good progress. A few more details will improve strategy quality.'
                : 'Early draft. Add more business context to unlock better recommendations.';

    const revenueMarkup = formatProfileSummaryValue(
        safeProfile.revenue,
        'Annual revenue not added yet',
        (value) => `$${Number(value).toLocaleString()}`
    );
    const budgetMarkup = formatProfileSummaryValue(
        safeProfile.budget,
        'Marketing budget not added yet',
        (value) => `$${Number(value).toLocaleString()}`
    );
    const goalsMarkup = formatProfileSummaryValue(
        safeProfile.marketingGoals,
        'Select one or more goals',
        (value) => value.join(', ')
    );

    summaryContent.innerHTML = `
        <div class="insights-dashboard__grid">
            <section class="insight-card insight-card--strength dashboard-section">
                <div class="insight-card__title">Profile Strength</div>
                <div class="strength-meter">
                    <div class="strength-meter__meta">
                        <div class="strength-meter__value">${strength}%</div>
                        <div class="strength-meter__label">${strengthLabel}</div>
                    </div>
                    <div class="strength-meter__bar" aria-label="Profile strength meter">
                        <div class="strength-meter__fill" style="width: ${strength}%"></div>
                    </div>
                </div>
            </section>

            <section class="insight-card dashboard-section ${completed ? 'hidden' : ''}">
                <div class="insight-card__title">AI Insights</div>
                ${insights.length ? insights.map((item) => `<div class="insight-chip">${item}</div>`).join('') : `<p class="insight-card__text">Select an industry, company size, and goals to unlock tailored guidance.</p>`}
            </section>

            <section class="insight-card dashboard-section ${completed ? 'hidden' : ''}">
                <div class="insight-card__title">Industry Benchmarks</div>
                <div class="benchmark-row"><strong>Typical Channels:</strong> ${benchmarks.channels.join(', ')}</div>
                <div class="benchmark-row"><strong>Average Conversion Rate:</strong> ${benchmarks.conversionRate}</div>
                <div class="benchmark-row"><strong>Budget Insight:</strong> ${benchmarks.budgetNote}</div>
            </section>

            <section class="insight-card dashboard-section ${completed ? 'hidden' : ''}">
                <div class="insight-card__title">Smart Suggestions</div>
                ${suggestions.length ? suggestions.map((item) => `<div class="suggestion-item">${item}</div>`).join('') : `<p class="insight-card__text">No major gaps detected. The profile is ready for strategy generation.</p>`}
            </section>

            <section class="insight-card insight-card--snapshot dashboard-section ${completed ? 'insight-card--snapshot-complete' : ''} ${!completed ? 'hidden' : ''} ${showEmptyState ? 'insight-card--snapshot-empty' : ''}">
                <div class="insight-card__title">Current Profile Snapshot</div>
                ${showEmptyState ? `
                    <div class="profile-summary__empty-state">
                        <h4>Live Preview</h4>
                        <p>Start filling out the business profile. This dashboard updates in real time and keeps your saved summary after submission.</p>
                    </div>
                ` : ''}
                <div class="profile-summary">
                    <div class="summary-item">
                        <strong>Business Name:</strong>
                        <span>${formatProfileSummaryValue(safeProfile.businessName, 'Your company name')}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Industry:</strong>
                        <span>${formatProfileSummaryValue(safeProfile.industry, 'Select an industry')}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Company Size:</strong>
                        <span>${formatProfileSummaryValue(safeProfile.companySize, 'Choose company size')}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Annual Revenue:</strong>
                        <span>${revenueMarkup}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Continent:</strong>
                        <span>${formatProfileSummaryValue(safeProfile.continent, 'Select a continent')}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Country:</strong>
                        <span>${formatProfileSummaryValue(safeProfile.country, 'Optional country')}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Region:</strong>
                        <span>${formatProfileSummaryValue(safeProfile.region, 'Optional region')}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Marketing Goals:</strong>
                        <span>${goalsMarkup}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Budget:</strong>
                        <span>${budgetMarkup}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Target Audience:</strong>
                        <span>${formatProfileSummaryValue(safeProfile.targetAudience, 'Describe your ideal customer')}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Website:</strong>
                        <span>${formatProfileSummaryValue(safeProfile.websiteLink, 'Add your website URL')}</span>
                    </div>
                </div>
            </section>
        </div>
    `;
}

function renderBusinessProfileSummary(profile, options = {}) {
    renderInsightsDashboard(profile, options);
}

function updateBusinessProfilePreview() {
    const draftProfile = getBusinessProfileFormData();
    renderBusinessProfileSummary(draftProfile, { showEmptyState: true });
}

function setupAdminApiKeysListeners() {
    const addBtn = document.getElementById('adminApiKeyAddBtn');
    if (addBtn && !addBtn.dataset.bound) {
        addBtn.addEventListener('click', () => {
            openAdminApiKeyForm();
        });
        addBtn.dataset.bound = '1';
    }

    const cancelBtn = document.getElementById('adminApiKeyCancelBtn');
    if (cancelBtn && !cancelBtn.dataset.bound) {
        cancelBtn.addEventListener('click', () => {
            closeAdminApiKeyForm();
        });
        cancelBtn.dataset.bound = '1';
    }

    const form = document.getElementById('adminApiKeyForm');
    if (form && !form.dataset.bound) {
        form.addEventListener('submit', handleAdminApiKeySubmit);
        form.dataset.bound = '1';
    }
}

function setAdminApiKeysLoading(isLoading) {
    const loader = document.getElementById('adminApiKeysLoader');
    if (loader) {
        loader.classList.toggle('hidden', !isLoading);
    }
}

function setAdminApiKeysFeedback(message, type = 'info') {
    const feedback = document.getElementById('adminApiKeysFeedback');
    if (!feedback) return;
    if (!message) {
        feedback.classList.add('hidden');
        feedback.textContent = '';
        feedback.className = 'hidden';
        return;
    }
    feedback.className = `alert alert--${type}`;
    feedback.textContent = message;
}

function openAdminApiKeyForm(row = null) {
    if (!isAdminUser()) return;

    const form = document.getElementById('adminApiKeyForm');
    const idInput = document.getElementById('adminApiKeyId');
    const providerInput = document.getElementById('adminProviderName');
    const statusInput = document.getElementById('adminApiKeyStatus');
    const apiKeyInput = document.getElementById('adminApiKeyValue');
    const saveBtn = document.getElementById('adminApiKeySaveBtn');
    if (!form || !idInput || !providerInput || !statusInput || !apiKeyInput || !saveBtn) return;

    if (row) {
        idInput.value = row.id || '';
        providerInput.value = String(row.provider_name || 'github');
        statusInput.value = String(row.status || 'active');
        apiKeyInput.value = '';
        apiKeyInput.placeholder = 'Leave blank to keep existing key';
        saveBtn.textContent = 'Update API Key';
    } else {
        idInput.value = '';
        providerInput.value = 'github';
        statusInput.value = 'active';
        apiKeyInput.value = '';
        apiKeyInput.placeholder = 'Enter provider API key';
        saveBtn.textContent = 'Save API Key';
    }

    syncEnhancedSelectUI(providerInput);
    syncEnhancedSelectUI(statusInput);

    form.classList.remove('hidden');
}

function closeAdminApiKeyForm() {
    const form = document.getElementById('adminApiKeyForm');
    const providerInput = document.getElementById('adminProviderName');
    const statusInput = document.getElementById('adminApiKeyStatus');
    if (form) {
        form.classList.add('hidden');
        form.reset();
    }
    syncEnhancedSelectUI(providerInput);
    syncEnhancedSelectUI(statusInput);
}

function renderAdminApiKeysTable() {
    const tbody = document.getElementById('adminApiKeysTableBody');
    if (!tbody) return;

    const rows = Array.isArray(appData.adminApiKeys) ? appData.adminApiKeys : [];
    if (rows.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6">No API keys configured.</td>
            </tr>
        `;
        return;
    }

    const escapeHtml = (value) => String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    tbody.innerHTML = rows.map((row) => `
        <tr>
            <td>${escapeHtml(row.provider_name || '')}</td>
            <td>${escapeHtml(row.api_key_masked || '')}</td>
            <td><span class="status ${String(row.status || '').toLowerCase() === 'active' ? 'status--success' : 'status--warning'}">${escapeHtml(row.status || '')}</span></td>
            <td>${escapeHtml(row.created_by || '')}</td>
            <td>${escapeHtml(row.updated_at ? new Date(row.updated_at).toLocaleString() : '')}</td>
            <td style="display:flex; gap:6px; flex-wrap: wrap;">
                <button class="btn btn--sm btn--secondary admin-api-edit-btn" data-id="${escapeHtml(row.id || '')}">Edit</button>
                <button class="btn btn--sm btn--outline admin-api-disable-btn" data-id="${escapeHtml(row.id || '')}">Disable</button>
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('.admin-api-edit-btn').forEach((button) => {
        button.addEventListener('click', () => {
            const row = rows.find((item) => String(item.id) === String(button.dataset.id));
            if (!row) return;
            openAdminApiKeyForm(row);
        });
    });

    tbody.querySelectorAll('.admin-api-disable-btn').forEach((button) => {
        button.addEventListener('click', async () => {
            const keyId = String(button.dataset.id || '');
            if (!keyId) return;
            const confirmed = window.confirm('Disable this API key?');
            if (!confirmed) return;
            await disableAdminApiKey(keyId);
        });
    });
}

async function loadAdminApiKeys(force = false) {
    if (!isAdminUser()) return;
    if (adminApiKeysLoaded && !force) {
        renderAdminApiKeysTable();
        return;
    }

    setAdminApiKeysLoading(true);
    setAdminApiKeysFeedback('', 'info');
    try {
        const response = await apiRequest('/api/admin/api-keys', 'GET');
        appData.adminApiKeys = Array.isArray(response?.api_keys) ? response.api_keys : [];
        adminApiKeysLoaded = true;
        renderAdminApiKeysTable();
    } catch (error) {
        console.error('Failed to load admin API keys:', error);
        setAdminApiKeysFeedback(error.message || 'Failed to load API keys.', 'error');
    } finally {
        setAdminApiKeysLoading(false);
    }
}

async function handleAdminApiKeySubmit(event) {
    event.preventDefault();
    if (!isAdminUser()) return;

    const idInput = document.getElementById('adminApiKeyId');
    const providerInput = document.getElementById('adminProviderName');
    const statusInput = document.getElementById('adminApiKeyStatus');
    const apiKeyInput = document.getElementById('adminApiKeyValue');

    const keyId = String(idInput?.value || '').trim();
    const providerName = String(providerInput?.value || '').trim();
    const status = String(statusInput?.value || 'active').trim();
    const apiKey = String(apiKeyInput?.value || '');

    if (!providerName) {
        setAdminApiKeysFeedback('Provider is required.', 'error');
        return;
    }

    if (!keyId && !apiKey.trim()) {
        setAdminApiKeysFeedback('API key is required.', 'error');
        return;
    }

    const payload = {
        provider_name: providerName,
        api_key: apiKey,
        status,
    };

    try {
        if (keyId) {
            await apiRequest(`/api/admin/api-keys/${encodeURIComponent(keyId)}`, 'PUT', payload);
            setAdminApiKeysFeedback('API key updated successfully.', 'success');
            showSuccessMessage('API key updated successfully.');
        } else {
            await apiRequest('/api/admin/api-keys', 'POST', payload);
            setAdminApiKeysFeedback('API key created successfully.', 'success');
            showSuccessMessage('API key created successfully.');
        }
        closeAdminApiKeyForm();
        await loadAdminApiKeys(true);
    } catch (error) {
        console.error('Failed to save admin API key:', error);
        setAdminApiKeysFeedback(error.message || 'Failed to save API key.', 'error');
        showErrorMessage(error.message || 'Failed to save API key.');
    }
}

async function disableAdminApiKey(keyId) {
    try {
        const response = await apiRequest(`/api/admin/api-keys/${encodeURIComponent(keyId)}`, 'DELETE');
        console.log("Disable API response:", response);

        if (response && response.success) {
            const message = response.message || 'API key disabled successfully';
            setAdminApiKeysFeedback(message, 'success');
            showSuccessMessage(message);
            await loadAdminApiKeys(true);
        } else {
            setAdminApiKeysFeedback('Failed to disable API key', 'error');
            showErrorMessage('Failed to disable API key');
        }
    } catch (error) {
        console.error('Failed to disable API key:', error);
        setAdminApiKeysFeedback(error.message || 'Failed to disable API key.', 'error');
        showErrorMessage(error.message || 'Failed to disable API key.');
    }
}

function setAdminSectionLoading(sectionKey, isLoading) {
    const loaderMap = {
        users: 'adminUsersLoader',
        licenses: 'adminLicensesLoader',
        organizations: 'adminOrganizationsLoader',
    };
    const loader = document.getElementById(loaderMap[sectionKey] || '');
    if (loader) {
        loader.classList.toggle('hidden', !isLoading);
    }
}

function setAdminSectionFeedback(sectionKey, message, type = 'info') {
    const feedbackMap = {
        users: 'adminUsersFeedback',
        licenses: 'adminLicensesFeedback',
        organizations: 'adminOrganizationsFeedback',
    };
    const feedback = document.getElementById(feedbackMap[sectionKey] || '');
    if (!feedback) return;
    if (!message) {
        feedback.className = 'hidden';
        feedback.textContent = '';
        return;
    }
    feedback.className = `alert alert--${type}`;
    feedback.textContent = message;
}

function getRoleOptionsHtml(includeSuperAdmin = false, selectedRole = 'user') {
    const roles = includeSuperAdmin ? ['super_admin', 'admin', 'user'] : ['admin', 'user'];
    return roles.map((role) => `
        <option value="${role}" ${String(selectedRole || '').toLowerCase() === role ? 'selected' : ''}>${role}</option>
    `).join('');
}

function getCurrentAdminScopedOrganizationId() {
    return appData.currentOrganizationId || '';
}

function getOrganizationOptionsHtml(selectedOrganizationId = '') {
    const rows = Array.isArray(appData.adminOrganizations) ? appData.adminOrganizations : [];
    return rows.map((org) => `
        <option value="${org.id}" ${String(selectedOrganizationId || '') === String(org.id || '') ? 'selected' : ''}>
            ${String(org.name || org.id || '')}
        </option>
    `).join('');
}

async function ensureAdminOrganizationsLoaded() {
    if (!isSuperAdminUser()) return;
    if (!adminOrganizationsLoaded) {
        await loadAdminOrganizations(true);
    }
}

function showAdminSection(sectionKey = 'users') {
    currentAdminSection = sectionKey;
    const sectionMap = {
        users: 'adminSectionUsers',
        licenses: 'adminSectionLicenses',
        'api-keys': 'adminSectionApiKeys',
        organizations: 'adminSectionOrganizations',
    };

    Object.entries(sectionMap).forEach(([key, sectionId]) => {
        const section = document.getElementById(sectionId);
        const tab = document.querySelector(`[data-admin-section="${key}"]`);
        const shouldShow = key === sectionKey && (key !== 'organizations' || isSuperAdminUser());
        if (section) section.classList.toggle('hidden', !shouldShow);
        if (tab) tab.classList.toggle('active', shouldShow);
    });

    if (sectionKey === 'users') {
        loadAdminUsers();
    } else if (sectionKey === 'licenses') {
        loadAdminLicenses();
    } else if (sectionKey === 'api-keys') {
        loadAdminApiKeys();
    } else if (sectionKey === 'organizations' && isSuperAdminUser()) {
        loadAdminOrganizations();
    }
}

function openAdminCrudModal({ title, bodyHtml, submitLabel = 'Save', onSubmit, hideSubmit = false }) {
    const modal = document.getElementById('adminCrudModal');
    const titleEl = document.getElementById('adminCrudModalTitle');
    const bodyEl = document.getElementById('adminCrudModalBody');
    const submitBtn = document.getElementById('adminCrudModalSubmitBtn');
    if (!modal || !titleEl || !bodyEl || !submitBtn) return;

    titleEl.textContent = title;
    bodyEl.innerHTML = bodyHtml;
    submitBtn.textContent = submitLabel;
    submitBtn.classList.toggle('hidden', hideSubmit);
    adminModalSubmitHandler = typeof onSubmit === 'function' ? onSubmit : null;
    modal.classList.remove('hidden');
}

function closeAdminCrudModal() {
    const modal = document.getElementById('adminCrudModal');
    const bodyEl = document.getElementById('adminCrudModalBody');
    if (bodyEl) bodyEl.innerHTML = '';
    if (modal) modal.classList.add('hidden');
    adminModalSubmitHandler = null;
}

async function handleAdminCrudModalSubmit() {
    if (typeof adminModalSubmitHandler === 'function') {
        await adminModalSubmitHandler();
    }
}

function setupAdminDashboardListeners() {
    document.querySelectorAll('[data-admin-section]').forEach((button) => {
        if (button.dataset.bound) return;
        button.addEventListener('click', () => {
            const nextSection = String(button.dataset.adminSection || 'users');
            if (nextSection === 'organizations' && !isSuperAdminUser()) return;
            showAdminSection(nextSection);
        });
        button.dataset.bound = '1';
    });

    const bindings = [
        ['adminUserAddBtn', openCreateUserModal],
        ['adminLicenseAddBtn', openCreateLicenseModal],
        ['adminOrganizationAddBtn', openCreateOrganizationModal],
        ['adminCrudModalCloseBtn', closeAdminCrudModal],
        ['adminCrudModalCancelBtn', closeAdminCrudModal],
        ['adminCrudModalSubmitBtn', handleAdminCrudModalSubmit],
    ];

    bindings.forEach(([id, handler]) => {
        const element = document.getElementById(id);
        if (element && !element.dataset.bound) {
            element.addEventListener('click', handler);
            element.dataset.bound = '1';
        }
    });
}

async function loadAdminUsers(force = false) {
    if (!isAdminUser()) return;
    if (adminUsersLoaded && !force) {
        renderAdminUsersTable();
        return;
    }

    setAdminSectionLoading('users', true);
    setAdminSectionFeedback('users', '', 'info');
    try {
        const path = isSuperAdminUser()
            ? '/api/admin/users'
            : `/api/admin/users?organization_id=${encodeURIComponent(getCurrentAdminScopedOrganizationId())}`;
        const response = await apiRequest(path, 'GET');
        appData.adminUsers = Array.isArray(response?.users) ? response.users : [];
        adminUsersLoaded = true;
        renderAdminUsersTable();
    } catch (error) {
        console.error('Failed to load admin users:', error);
        setAdminSectionFeedback('users', error.message || 'Failed to load users.', 'error');
    } finally {
        setAdminSectionLoading('users', false);
    }
}

function renderAdminUsersTable() {
    const tbody = document.getElementById('adminUsersTableBody');
    if (!tbody) return;
    const rows = Array.isArray(appData.adminUsers) ? appData.adminUsers : [];
    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="5">No users found.</td></tr>';
        return;
    }

    const escapeHtml = (value) => String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    tbody.innerHTML = rows.map((row) => `
        <tr>
            <td>${escapeHtml(row.user_id || '')}</td>
            <td>${escapeHtml(row.email || '')}</td>
            <td>${escapeHtml(row.role || '')}</td>
            <td><span class="status ${row.is_active ? 'status--success' : 'status--warning'}">${row.is_active ? 'active' : 'inactive'}</span></td>
            <td style="display:flex; gap:6px; flex-wrap:wrap;">
                <button class="btn btn--sm btn--secondary admin-user-edit-btn" data-id="${escapeHtml(row.id || '')}">Edit</button>
                <button class="btn btn--sm btn--outline admin-user-role-btn" data-id="${escapeHtml(row.id || '')}">Role</button>
                <button class="btn btn--sm btn--outline admin-user-password-btn" data-id="${escapeHtml(row.id || '')}">Reset Password</button>
                <button class="btn btn--sm btn--outline admin-user-delete-btn" data-id="${escapeHtml(row.id || '')}">Delete</button>
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('.admin-user-edit-btn').forEach((button) => {
        button.addEventListener('click', () => openEditUserModal(button.dataset.id));
    });
    tbody.querySelectorAll('.admin-user-role-btn').forEach((button) => {
        button.addEventListener('click', () => openChangeUserRoleModal(button.dataset.id));
    });
    tbody.querySelectorAll('.admin-user-password-btn').forEach((button) => {
        button.addEventListener('click', () => openResetPasswordModal(button.dataset.id));
    });
    tbody.querySelectorAll('.admin-user-delete-btn').forEach((button) => {
        button.addEventListener('click', async () => {
            if (!window.confirm('Deactivate this user?')) return;
            await deleteAdminUser(button.dataset.id);
        });
    });
}

async function openCreateUserModal() {
    await ensureAdminOrganizationsLoaded();
    const includeSuperAdmin = isSuperAdminUser();
    const orgField = isSuperAdminUser() ? `
        <div class="form-group">
            <label class="form-label" for="adminUserOrganizationId">Organization</label>
            <select class="form-control" id="adminUserOrganizationId" required>
                ${getOrganizationOptionsHtml()}
            </select>
        </div>
    ` : '';

    openAdminCrudModal({
        title: 'Create User',
        submitLabel: 'Create User',
        bodyHtml: `
            <div class="grid grid--two-col">
                ${orgField}
                <div class="form-group">
                    <label class="form-label" for="adminUserUserId">User ID</label>
                    <input type="text" class="form-control" id="adminUserUserId" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="adminUserEmail">Email</label>
                    <input type="email" class="form-control" id="adminUserEmail">
                </div>
                <div class="form-group">
                    <label class="form-label" for="adminUserRole">Role</label>
                    <select class="form-control" id="adminUserRole" required>
                        ${getRoleOptionsHtml(includeSuperAdmin, 'user')}
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label" for="adminUserPassword">Password</label>
                    <input type="password" class="form-control" id="adminUserPassword" required>
                </div>
            </div>
        `,
        onSubmit: async () => {
            const payload = {
                organization_id: isSuperAdminUser()
                    ? String(document.getElementById('adminUserOrganizationId')?.value || '').trim()
                    : getCurrentAdminScopedOrganizationId(),
                user_id: String(document.getElementById('adminUserUserId')?.value || '').trim(),
                email: String(document.getElementById('adminUserEmail')?.value || '').trim() || null,
                role: String(document.getElementById('adminUserRole')?.value || 'user').trim(),
                password: String(document.getElementById('adminUserPassword')?.value || '')
            };
            await apiRequest('/api/admin/users', 'POST', payload);
            closeAdminCrudModal();
            setAdminSectionFeedback('users', 'User created successfully.', 'success');
            await loadAdminUsers(true);
        }
    });
}

function openEditUserModal(userId) {
    const row = (appData.adminUsers || []).find((item) => String(item.id) === String(userId));
    if (!row) return;

    openAdminCrudModal({
        title: `Edit User: ${row.user_id}`,
        submitLabel: 'Save Changes',
        bodyHtml: `
            <div class="grid grid--two-col">
                <div class="form-group">
                    <label class="form-label" for="adminEditUserUserId">User ID</label>
                    <input type="text" class="form-control" id="adminEditUserUserId" value="${String(row.user_id || '').replace(/"/g, '&quot;')}" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="adminEditUserEmail">Email</label>
                    <input type="email" class="form-control" id="adminEditUserEmail" value="${String(row.email || '').replace(/"/g, '&quot;')}">
                </div>
                <div class="form-group">
                    <label class="form-label" for="adminEditUserStatus">Status</label>
                    <select class="form-control" id="adminEditUserStatus">
                        <option value="true" ${row.is_active ? 'selected' : ''}>active</option>
                        <option value="false" ${!row.is_active ? 'selected' : ''}>inactive</option>
                    </select>
                </div>
            </div>
        `,
        onSubmit: async () => {
            const payload = {
                user_id: String(document.getElementById('adminEditUserUserId')?.value || '').trim(),
                email: String(document.getElementById('adminEditUserEmail')?.value || '').trim() || null,
                is_active: String(document.getElementById('adminEditUserStatus')?.value || 'true') === 'true'
            };
            await apiRequest(`/api/admin/users/${encodeURIComponent(userId)}`, 'PUT', payload);
            closeAdminCrudModal();
            setAdminSectionFeedback('users', 'User updated successfully.', 'success');
            await loadAdminUsers(true);
        }
    });
}

function openChangeUserRoleModal(userId) {
    const row = (appData.adminUsers || []).find((item) => String(item.id) === String(userId));
    if (!row) return;

    openAdminCrudModal({
        title: `Change Role: ${row.user_id}`,
        submitLabel: 'Update Role',
        bodyHtml: `
            <div class="form-group">
                <label class="form-label" for="adminChangeUserRole">Role</label>
                <select class="form-control" id="adminChangeUserRole">
                    ${getRoleOptionsHtml(isSuperAdminUser(), row.role || 'user')}
                </select>
            </div>
        `,
        onSubmit: async () => {
            await apiRequest(`/api/admin/users/${encodeURIComponent(userId)}/role`, 'PATCH', {
                role: String(document.getElementById('adminChangeUserRole')?.value || 'user').trim()
            });
            closeAdminCrudModal();
            setAdminSectionFeedback('users', 'User role updated successfully.', 'success');
            await loadAdminUsers(true);
        }
    });
}

function openResetPasswordModal(userId) {
    const row = (appData.adminUsers || []).find((item) => String(item.id) === String(userId));
    if (!row) return;

    openAdminCrudModal({
        title: `Reset Password: ${row.user_id}`,
        submitLabel: 'Reset Password',
        bodyHtml: `
            <div class="form-group">
                <label class="form-label" for="adminResetUserPassword">New Password</label>
                <input type="password" class="form-control" id="adminResetUserPassword" required>
            </div>
        `,
        onSubmit: async () => {
            await apiRequest(`/api/admin/users/${encodeURIComponent(userId)}/reset-password`, 'PATCH', {
                password: String(document.getElementById('adminResetUserPassword')?.value || '')
            });
            closeAdminCrudModal();
            setAdminSectionFeedback('users', 'Password reset successfully.', 'success');
        }
    });
}

async function deleteAdminUser(userId) {
    try {
        await apiRequest(`/api/admin/users/${encodeURIComponent(userId)}`, 'DELETE');
        setAdminSectionFeedback('users', 'User deactivated successfully.', 'success');
        await loadAdminUsers(true);
    } catch (error) {
        console.error('Failed to deactivate user:', error);
        setAdminSectionFeedback('users', error.message || 'Failed to deactivate user.', 'error');
    }
}

async function loadAdminLicenses(force = false) {
    if (!isAdminUser()) return;
    if (adminLicensesLoaded && !force) {
        renderAdminLicensesTable();
        return;
    }

    setAdminSectionLoading('licenses', true);
    setAdminSectionFeedback('licenses', '', 'info');
    try {
        const path = isSuperAdminUser()
            ? '/api/admin/licenses'
            : `/api/admin/licenses?organization_id=${encodeURIComponent(getCurrentAdminScopedOrganizationId())}`;
        const response = await apiRequest(path, 'GET');
        appData.adminLicenses = Array.isArray(response?.licenses) ? response.licenses : [];
        adminLicensesLoaded = true;
        renderAdminLicensesTable();
    } catch (error) {
        console.error('Failed to load admin licenses:', error);
        setAdminSectionFeedback('licenses', error.message || 'Failed to load licenses.', 'error');
    } finally {
        setAdminSectionLoading('licenses', false);
    }
}

function renderAdminLicensesTable() {
    const tbody = document.getElementById('adminLicensesTableBody');
    if (!tbody) return;
    const rows = Array.isArray(appData.adminLicenses) ? appData.adminLicenses : [];
    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="6">No licenses found.</td></tr>';
        return;
    }

    const escapeHtml = (value) => String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    tbody.innerHTML = rows.map((row) => `
        <tr>
            <td>${escapeHtml(row.organization_id || '')}</td>
            <td>${escapeHtml(row.type || '')}</td>
            <td>${escapeHtml(row.status || '')}</td>
            <td>${escapeHtml(row.period || '')}</td>
            <td>${escapeHtml(row.max_users || '')}</td>
            <td style="display:flex; gap:6px; flex-wrap:wrap;">
                <button class="btn btn--sm btn--secondary admin-license-edit-btn" data-id="${escapeHtml(row.id || '')}">Edit</button>
                <button class="btn btn--sm btn--outline admin-license-status-btn" data-id="${escapeHtml(row.id || '')}">Status</button>
                <button class="btn btn--sm btn--outline admin-license-delete-btn" data-id="${escapeHtml(row.id || '')}">Delete</button>
            </td>
        </tr>
    `).join('');

    tbody.querySelectorAll('.admin-license-edit-btn').forEach((button) => {
        button.addEventListener('click', () => openEditLicenseModal(button.dataset.id));
    });
    tbody.querySelectorAll('.admin-license-status-btn').forEach((button) => {
        button.addEventListener('click', () => openUpdateLicenseStatusModal(button.dataset.id));
    });
    tbody.querySelectorAll('.admin-license-delete-btn').forEach((button) => {
        button.addEventListener('click', async () => {
            if (!window.confirm('Delete this license?')) return;
            await deleteAdminLicense(button.dataset.id);
        });
    });
}

async function openCreateLicenseModal() {
    await ensureAdminOrganizationsLoaded();
    const orgField = isSuperAdminUser() ? `
        <div class="form-group">
            <label class="form-label" for="adminLicenseOrganizationId">Organization</label>
            <select class="form-control" id="adminLicenseOrganizationId" required>
                ${getOrganizationOptionsHtml()}
            </select>
        </div>
    ` : '';

    openAdminCrudModal({
        title: 'Create License',
        submitLabel: 'Create License',
        bodyHtml: `
            <div class="grid grid--two-col">
                ${orgField}
                <div class="form-group">
                    <label class="form-label" for="adminLicenseType">License Type</label>
                    <select class="form-control" id="adminLicenseType">
                        <option value="strategy_only">strategy_only</option>
                        <option value="strategy_leads">strategy_leads</option>
                        <option value="full_suite">full_suite</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label" for="adminLicensePeriod">Period</label>
                    <select class="form-control" id="adminLicensePeriod">
                        <option value="monthly">monthly</option>
                        <option value="yearly">yearly</option>
                        <option value="one_time">one_time</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label" for="adminLicenseMaxUsers">Max Users</label>
                    <input type="number" class="form-control" id="adminLicenseMaxUsers" min="1" value="1">
                </div>
            </div>
        `,
        onSubmit: async () => {
            const payload = {
                organization_id: isSuperAdminUser()
                    ? String(document.getElementById('adminLicenseOrganizationId')?.value || '').trim()
                    : getCurrentAdminScopedOrganizationId(),
                license_type: String(document.getElementById('adminLicenseType')?.value || 'strategy_only').trim(),
                period: String(document.getElementById('adminLicensePeriod')?.value || 'monthly').trim(),
                max_users: Number(document.getElementById('adminLicenseMaxUsers')?.value || 1) || 1
            };
            await apiRequest('/api/admin/licenses', 'POST', payload);
            closeAdminCrudModal();
            setAdminSectionFeedback('licenses', 'License created successfully.', 'success');
            await loadAdminLicenses(true);
        }
    });
}

function openEditLicenseModal(licenseId) {
    const row = (appData.adminLicenses || []).find((item) => String(item.id) === String(licenseId));
    if (!row) return;

    openAdminCrudModal({
        title: `Edit License: ${row.id}`,
        submitLabel: 'Save Changes',
        bodyHtml: `
            <div class="grid grid--two-col">
                <div class="form-group">
                    <label class="form-label" for="adminEditLicenseType">License Type</label>
                    <select class="form-control" id="adminEditLicenseType">
                        <option value="strategy_only" ${row.type === 'strategy_only' ? 'selected' : ''}>strategy_only</option>
                        <option value="strategy_leads" ${row.type === 'strategy_leads' ? 'selected' : ''}>strategy_leads</option>
                        <option value="full_suite" ${row.type === 'full_suite' ? 'selected' : ''}>full_suite</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label" for="adminEditLicensePeriod">Period</label>
                    <select class="form-control" id="adminEditLicensePeriod">
                        <option value="monthly" ${row.period === 'monthly' ? 'selected' : ''}>monthly</option>
                        <option value="yearly" ${row.period === 'yearly' ? 'selected' : ''}>yearly</option>
                        <option value="one_time" ${row.period === 'one_time' ? 'selected' : ''}>one_time</option>
                    </select>
                </div>
                <div class="form-group">
                    <label class="form-label" for="adminEditLicenseMaxUsers">Max Users</label>
                    <input type="number" class="form-control" id="adminEditLicenseMaxUsers" min="1" value="${Number(row.max_users || 1)}">
                </div>
            </div>
        `,
        onSubmit: async () => {
            await apiRequest(`/api/admin/licenses/${encodeURIComponent(licenseId)}`, 'PUT', {
                license_type: String(document.getElementById('adminEditLicenseType')?.value || row.type).trim(),
                period: String(document.getElementById('adminEditLicensePeriod')?.value || row.period).trim(),
                max_users: Number(document.getElementById('adminEditLicenseMaxUsers')?.value || row.max_users || 1) || 1
            });
            closeAdminCrudModal();
            setAdminSectionFeedback('licenses', 'License updated successfully.', 'success');
            await loadAdminLicenses(true);
        }
    });
}

function openUpdateLicenseStatusModal(licenseId) {
    const row = (appData.adminLicenses || []).find((item) => String(item.id) === String(licenseId));
    if (!row) return;

    openAdminCrudModal({
        title: 'Update License Status',
        submitLabel: 'Update Status',
        bodyHtml: `
            <div class="form-group">
                <label class="form-label" for="adminLicenseStatusValue">Status</label>
                <select class="form-control" id="adminLicenseStatusValue">
                    <option value="active" ${row.status === 'active' ? 'selected' : ''}>active</option>
                    <option value="suspended" ${row.status === 'suspended' ? 'selected' : ''}>suspended</option>
                    <option value="cancelled" ${row.status === 'cancelled' ? 'selected' : ''}>cancelled</option>
                </select>
            </div>
        `,
        onSubmit: async () => {
            await apiRequest(`/api/admin/licenses/${encodeURIComponent(licenseId)}/status`, 'PATCH', {
                status: String(document.getElementById('adminLicenseStatusValue')?.value || row.status).trim()
            });
            closeAdminCrudModal();
            setAdminSectionFeedback('licenses', 'License status updated successfully.', 'success');
            await loadAdminLicenses(true);
        }
    });
}

async function deleteAdminLicense(licenseId) {
    try {
        await apiRequest(`/api/admin/licenses/${encodeURIComponent(licenseId)}`, 'DELETE');
        setAdminSectionFeedback('licenses', 'License deleted successfully.', 'success');
        await loadAdminLicenses(true);
    } catch (error) {
        console.error('Failed to delete license:', error);
        setAdminSectionFeedback('licenses', error.message || 'Failed to delete license.', 'error');
    }
}

async function loadAdminOrganizations(force = false) {
    if (!isSuperAdminUser()) return;
    if (adminOrganizationsLoaded && !force) {
        renderAdminOrganizationsTable();
        return;
    }

    setAdminSectionLoading('organizations', true);
    setAdminSectionFeedback('organizations', '', 'info');
    try {
        const response = await apiRequest('/api/admin/organizations', 'GET');
        appData.adminOrganizations = Array.isArray(response?.organizations) ? response.organizations : [];
        adminOrganizationsLoaded = true;
        renderAdminOrganizationsTable();
    } catch (error) {
        console.error('Failed to load organizations:', error);
        setAdminSectionFeedback('organizations', error.message || 'Failed to load organizations.', 'error');
    } finally {
        setAdminSectionLoading('organizations', false);
    }
}

function renderAdminOrganizationsTable() {
    const tbody = document.getElementById('adminOrganizationsTableBody');
    if (!tbody) return;
    const rows = Array.isArray(appData.adminOrganizations) ? appData.adminOrganizations : [];
    if (!rows.length) {
        tbody.innerHTML = '<tr><td colspan="5">No organizations found.</td></tr>';
        return;
    }

    const escapeHtml = (value) => String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    tbody.innerHTML = rows.map((row) => `
        <tr>
            <td>${escapeHtml(row.name || '')}</td>
            <td>${escapeHtml(row.domain || '')}</td>
            <td>${escapeHtml(row.status || '')}</td>
            <td>${escapeHtml(row.created_at ? new Date(row.created_at).toLocaleString() : '')}</td>
            <td><button class="btn btn--sm btn--secondary admin-org-view-btn" data-id="${escapeHtml(row.id || '')}">View</button></td>
        </tr>
    `).join('');

    tbody.querySelectorAll('.admin-org-view-btn').forEach((button) => {
        button.addEventListener('click', () => openOrganizationDetailsModal(button.dataset.id));
    });
}

function openCreateOrganizationModal() {
    if (!isSuperAdminUser()) return;
    openAdminCrudModal({
        title: 'Create Organization',
        submitLabel: 'Create Organization',
        bodyHtml: `
            <div class="grid grid--two-col">
                <div class="form-group">
                    <label class="form-label" for="adminOrganizationName">Organization Name</label>
                    <input type="text" class="form-control" id="adminOrganizationName" required>
                </div>
                <div class="form-group">
                    <label class="form-label" for="adminOrganizationDomain">Domain</label>
                    <input type="text" class="form-control" id="adminOrganizationDomain">
                </div>
            </div>
        `,
        onSubmit: async () => {
            await apiRequest('/api/admin/organizations', 'POST', {
                name: String(document.getElementById('adminOrganizationName')?.value || '').trim(),
                domain: String(document.getElementById('adminOrganizationDomain')?.value || '').trim() || null
            });
            closeAdminCrudModal();
            setAdminSectionFeedback('organizations', 'Organization created successfully.', 'success');
            await loadAdminOrganizations(true);
        }
    });
}

async function openOrganizationDetailsModal(orgId) {
    if (!isSuperAdminUser()) return;
    try {
        const response = await apiRequest(`/api/admin/organizations/${encodeURIComponent(orgId)}`, 'GET');
        const org = response?.organization || {};
        const licenses = Array.isArray(response?.licenses) ? response.licenses : [];
        openAdminCrudModal({
            title: `Organization: ${org.name || orgId}`,
            hideSubmit: true,
            bodyHtml: `
                <div class="admin-org-detail">
                    <p><strong>ID:</strong> ${String(org.id || '')}</p>
                    <p><strong>Name:</strong> ${String(org.name || '')}</p>
                    <p><strong>Domain:</strong> ${String(org.domain || '')}</p>
                    <p><strong>Status:</strong> ${String(org.status || '')}</p>
                    <p><strong>Users:</strong> ${Number(response?.users_count || 0)}</p>
                    <p><strong>Licenses:</strong> ${licenses.length}</p>
                </div>
            `
        });
    } catch (error) {
        console.error('Failed to load organization details:', error);
        setAdminSectionFeedback('organizations', error.message || 'Failed to load organization details.', 'error');
    }
}

function setupLeadLocationControls() {
    const locationInput = document.getElementById('location');
    const useCurrentLocationBtn = document.getElementById('useCurrentLocationBtn');
    const suggestionsContainer = document.getElementById('locationSuggestions');

    if (locationInput && !locationInput.dataset.bound) {
        locationInput.addEventListener('input', function () {
            const nextText = String(this.value || '').trim();
            leadLocationState = {
                text: nextText,
                lat: null,
                lng: null,
                place_id: null,
            };
            renderLocationSuggestions([]);
        });
        locationInput.dataset.bound = '1';
    }

    if (useCurrentLocationBtn && !useCurrentLocationBtn.dataset.bound) {
        useCurrentLocationBtn.addEventListener('click', handleUseCurrentLocation);
        useCurrentLocationBtn.dataset.bound = '1';
    }

    if (suggestionsContainer) {
        renderLocationSuggestions([]);
    }
}

function renderLocationSuggestions(suggestions = []) {
    const container = document.getElementById('locationSuggestions');
    if (!container) return;

    const safeSuggestions = Array.isArray(suggestions) ? suggestions : [];
    if (safeSuggestions.length === 0) {
        container.innerHTML = '';
        container.classList.add('hidden');
        return;
    }

    container.innerHTML = safeSuggestions
        .map((item) => `<div class="suggestion-item" style="padding: 6px 0;">${item}</div>`)
        .join('');
    container.classList.remove('hidden');
}

function handleUseCurrentLocation() {
    if (!navigator.geolocation) {
        showErrorMessage('Geolocation is not supported by this browser.');
        return;
    }

    const btn = document.getElementById('useCurrentLocationBtn');
    const locationInput = document.getElementById('location');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Detecting...';
    }

    const finalizeButton = () => {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Use Current Location';
        }
    };

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const lat = Number(position?.coords?.latitude);
            const lng = Number(position?.coords?.longitude);
            if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
                showErrorMessage('Unable to read your current location coordinates.');
                finalizeButton();
                return;
            }

            const text = `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
            leadLocationState = {
                text,
                lat,
                lng,
                place_id: null,
            };
            if (locationInput) {
                locationInput.value = text;
            }
            renderLocationSuggestions([]);
            showSuccessMessage('Current location detected.');
            finalizeButton();
        },
        (error) => {
            const message = error?.message || 'Unable to detect current location.';
            showErrorMessage(message);
            finalizeButton();
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 60000,
        }
    );
}

function getStructuredLocationPayload() {
    const locationInput = document.getElementById('location');
    const text = String(locationInput?.value || leadLocationState.text || '').trim();

    if (text !== String(leadLocationState.text || '').trim()) {
        return {
            text,
            lat: null,
            lng: null,
            place_id: null,
        };
    }

    return {
        text,
        lat: leadLocationState.lat,
        lng: leadLocationState.lng,
        place_id: leadLocationState.place_id,
    };
}

function setBrowserExtensionPayload(payload) {
    browserExtensionPayloadState = (payload && typeof payload === 'object') ? payload : null;
    const statusEl = document.getElementById('extensionPayloadStatus');
    if (!statusEl) return;

    if (browserExtensionPayloadState) {
        const keys = Object.keys(browserExtensionPayloadState);
        statusEl.textContent = `Browser extension payload attached${keys.length ? ` (${keys.join(', ')})` : ''}.`;
        statusEl.classList.remove('hidden');
        renderExtensionPreview(browserExtensionPayloadState);
    } else {
        statusEl.textContent = '';
        statusEl.classList.add('hidden');
        renderExtensionPreview(null);
    }
}

function extractPreviewData(payload) {
    const safePayload = (payload && typeof payload === 'object') ? payload : {};
    const unique = (items) => Array.from(new Set(items.filter(Boolean)));
    const toDomain = (href) => {
        try {
            const normalized = String(href || '').trim();
            if (!normalized) return null;
            const url = new URL(normalized.startsWith('http') ? normalized : `https://${normalized}`);
            return url.hostname.replace(/^www\./i, '');
        } catch (_error) {
            return null;
        }
    };

    const websites = unique(
        (Array.isArray(safePayload.links) ? safePayload.links : [])
            .map((link) => (link && typeof link === 'object') ? toDomain(link.href) : null)
    ).slice(0, 5);

    const emails = unique(
        (Array.isArray(safePayload.contacts) ? safePayload.contacts : [])
            .map((contact) => (contact && typeof contact === 'object') ? String(contact.email || '').trim() : '')
    ).slice(0, 5);

    const phones = unique(
        (Array.isArray(safePayload.contacts) ? safePayload.contacts : [])
            .map((contact) => (contact && typeof contact === 'object') ? String(contact.phone || '').trim() : '')
    ).slice(0, 5);

    const names = unique(
        (Array.isArray(safePayload.headings) ? safePayload.headings : [])
            .map((heading) => String(heading || '').trim())
            .filter((heading) => heading.length >= 3)
    ).slice(0, 5);

    return { websites, emails, phones, names };
}

function renderExtensionPreview(payload) {
    const preview = document.getElementById('extensionPreview');
    const details = document.getElementById('extensionDetails');
    const toggleBtn = document.getElementById('togglePreviewDetails');
    const escapePreviewHtml = (value) => String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    if (!preview || !details || !toggleBtn) return;

    if (!payload || typeof payload !== 'object') {
        preview.innerHTML = '';
        details.innerHTML = '';
        details.style.display = 'none';
        details.classList.add('hidden');
        toggleBtn.classList.add('hidden');
        preview.classList.add('hidden');
        return;
    }

    const previewData = extractPreviewData(payload);
    const renderList = (items, emptyText) => {
        if (!items.length) {
            return `<li style="color:#9ca3af;">${escapePreviewHtml(emptyText)}</li>`;
        }
        return items.map((item) => `<li>${escapePreviewHtml(item)}</li>`).join('');
    };

    preview.innerHTML = `
        <div style="padding:14px; background:linear-gradient(180deg, #0f172a 0%, #111827 100%); color:#f5f7fa; border-radius:12px;">
            <strong style="display:block; margin-bottom:10px;">Scraped Data Preview</strong>
            <div style="display:grid; gap:10px;">
                <div>
                    <div style="font-size:12px; text-transform:uppercase; color:#93c5fd; margin-bottom:4px;">Top Websites</div>
                    <ul style="margin:0; padding-left:18px;">${renderList(previewData.websites, 'No website domains detected')}</ul>
                </div>
                <div>
                    <div style="font-size:12px; text-transform:uppercase; color:#86efac; margin-bottom:4px;">Contacts</div>
                    <ul style="margin:0; padding-left:18px;">${renderList([...previewData.emails, ...previewData.phones].slice(0, 5), 'No contacts detected')}</ul>
                </div>
                <div>
                    <div style="font-size:12px; text-transform:uppercase; color:#fcd34d; margin-bottom:4px;">Business Names</div>
                    <ul style="margin:0; padding-left:18px;">${renderList(previewData.names, 'No business names inferred')}</ul>
                </div>
            </div>
        </div>
    `;
    preview.classList.remove('hidden');

    details.innerHTML = `
        <h4>Details</h4>
        <div><strong>Top Websites:</strong> ${previewData.websites.length ? previewData.websites.map(escapePreviewHtml).join(', ') : 'None'}</div>
        <div><strong>Emails:</strong> ${previewData.emails.length ? previewData.emails.map(escapePreviewHtml).join(', ') : 'None'}</div>
        <div><strong>Phones:</strong> ${previewData.phones.length ? previewData.phones.map(escapePreviewHtml).join(', ') : 'None'}</div>
        <div><strong>Business Names:</strong> ${previewData.names.length ? previewData.names.map(escapePreviewHtml).join(', ') : 'None'}</div>
    `;
    details.style.display = 'none';
    details.classList.add('hidden');

    toggleBtn.textContent = 'View Details';
    toggleBtn.classList.remove('hidden');
}

window.setLeadExtensionPayload = function(payload) {
    // Accept structured payloads from the browser extension without interrupting the UI flow.
    if (!payload || typeof payload !== 'object') {
        console.warn('Ignoring invalid browser extension payload:', payload);
        return false;
    }

    console.log('Received browser extension payload:', payload);
    window.leadExtensionPayload = payload;
    setBrowserExtensionPayload(payload);

    if (window.appData && typeof window.appData === 'object') {
        window.appData.extensionPayload = payload;
    }

    const websiteUrlInput = document.getElementById('websiteUrl');
    const websiteUrl = String(payload.website_url || '').trim();
    if (websiteUrlInput && websiteUrl) {
        websiteUrlInput.value = websiteUrl;
    }

    if (typeof showSuccessMessage === 'function') {
        showSuccessMessage('Browser extension data attached.');
    } else {
        console.info('Browser extension data attached.');
    }

    return true;
};

window.clearLeadExtensionPayload = function() {
    setBrowserExtensionPayload(null);
};

if (window.__MAI_EXTENSION_PAYLOAD__) {
    setBrowserExtensionPayload(window.__MAI_EXTENSION_PAYLOAD__);
}

const togglePreviewDetailsBtn = document.getElementById('togglePreviewDetails');
if (togglePreviewDetailsBtn && !togglePreviewDetailsBtn.dataset.bound) {
    togglePreviewDetailsBtn.onclick = () => {
        const el = document.getElementById('extensionDetails');
        if (!el) return;
        const isHidden = el.style.display === 'none' || el.classList.contains('hidden');
        el.style.display = isHidden ? 'block' : 'none';
        el.classList.toggle('hidden', !isHidden);
        togglePreviewDetailsBtn.textContent = isHidden ? 'Hide Details' : 'View Details';
    };
    togglePreviewDetailsBtn.dataset.bound = '1';
}

function displayProfileSummary(profile) {
    renderBusinessProfileSummary(profile, { showEmptyState: true });
}

// AI Strategy Generator Functions
function updateStrategyGeneratorState() {
    const profileAlert = document.getElementById('profileAlert');
    const generateBtn = document.getElementById('generateStrategy');
    
    if (!profileAlert || !generateBtn) return;
    
    if (appData.businessProfile) {
        profileAlert.innerHTML = `
            <p><strong>Business Profile Detected:</strong> ${appData.businessProfile.businessName} in ${appData.businessProfile.industry}</p>
            <p>Ready to generate AI-powered marketing strategy recommendations.</p>
        `;
        profileAlert.className = 'alert alert--info';
        generateBtn.disabled = false;
        generateBtn.textContent = 'Generate AI Strategy';
    } else {
        profileAlert.innerHTML = '<p>Please complete your Business Profile first to generate personalized strategies.</p>';
        profileAlert.className = 'alert alert--info';
        generateBtn.disabled = true;
    }
}

function resetStrategyVersionDropdown(message = 'Select version') {
    const versionSelect = document.getElementById('strategyVersionSelect');
    if (!versionSelect) return;
    versionSelect.innerHTML = `<option value="">${message}</option>`;
    versionSelect.disabled = true;
    syncEnhancedSelectUI(versionSelect);
}

async function loadStrategyHistoryOptions() {
    const historySelect = document.getElementById('strategyHistorySelect');
    if (!historySelect) return;

    const requestVersion = ++strategyHistoryRequestVersion;
    historySelect.disabled = true;
    historySelect.innerHTML = '<option value="">Loading strategies...</option>';
    syncEnhancedSelectUI(historySelect);
    resetStrategyVersionDropdown();
    setAutosuggestLoading('strategyHistorySelect', true);

    try {
        const response = await apiRequest('/api/strategy/history');
        if (requestVersion !== strategyHistoryRequestVersion) return;

        const strategies = Array.isArray(response?.strategies) ? response.strategies : [];
        strategyHistoryOptions = strategies;

        if (!strategies.length) {
            historySelect.innerHTML = '<option value="">No saved strategies</option>';
            historySelect.disabled = true;
            appData.currentStrategyId = null;
            syncEnhancedSelectUI(historySelect);
            return;
        }

        historySelect.innerHTML = '<option value="">Select strategy</option>';
        strategies.forEach((item) => {
            const strategyId = item?.strategy_id;
            if (!strategyId) return;
            const name = item?.business_name || strategyId;
            const latestVersion = Number(item?.latest_version_no) || 0;
            const option = document.createElement('option');
            option.value = strategyId;
            option.textContent = latestVersion > 0 ? `${name} (Latest V${latestVersion})` : name;
            historySelect.appendChild(option);
        });
        historySelect.disabled = false;
        syncEnhancedSelectUI(historySelect);

        const optionValues = Array.from(historySelect.options)
            .map((opt) => String(opt.value || '').trim())
            .filter((val) => !!val);

        if (optionValues.length > 0) {
            const preferredId = String(appData.currentStrategyId || '').trim();
            const nextId = optionValues.includes(preferredId) ? preferredId : optionValues[0];
            historySelect.value = nextId;
            appData.currentStrategyId = nextId;
            saveDataToStorage();
            syncEnhancedSelectUI(historySelect);
        } else {
            appData.currentStrategyId = null;
        }
    } catch (error) {
        if (requestVersion !== strategyHistoryRequestVersion) return;
        console.error('Strategy history loading error:', error);
        historySelect.innerHTML = '<option value="">Failed to load strategies</option>';
        historySelect.disabled = true;
        syncEnhancedSelectUI(historySelect);
        resetStrategyVersionDropdown('Select version');
    } finally {
        setAutosuggestLoading('strategyHistorySelect', false);
    }
}

async function handleStrategyHistoryChange(event) {
    const strategyId = event?.target?.value || '';
    const versionSelect = document.getElementById('strategyVersionSelect');
    if (!versionSelect) return;
    appData.currentStrategyId = strategyId || null;
    saveDataToStorage();

    resetStrategyVersionDropdown('Loading versions...');
    setAutosuggestLoading('strategyVersionSelect', true);
    if (!strategyId) {
        resetStrategyVersionDropdown();
        setAutosuggestLoading('strategyVersionSelect', false);
        return;
    }

    const requestVersion = ++strategyHistoryRequestVersion;

    try {
        const response = await apiRequest(`/api/strategy/${encodeURIComponent(strategyId)}/versions`);
        if (requestVersion !== strategyHistoryRequestVersion) return;

        const versions = Array.isArray(response?.versions) ? response.versions : [];
        if (!versions.length) {
            resetStrategyVersionDropdown('No versions available');
            return;
        }

        versionSelect.innerHTML = '<option value="">Select version</option>';
        versions.forEach((version) => {
            const versionNo = Number(version?.version_no);
            if (!Number.isFinite(versionNo)) return;
            const option = document.createElement('option');
            option.value = String(versionNo);
            option.textContent = `Version ${versionNo}`;
            versionSelect.appendChild(option);
        });
        versionSelect.disabled = false;
        syncEnhancedSelectUI(versionSelect);
    } catch (error) {
        if (requestVersion !== strategyHistoryRequestVersion) return;
        console.error('Strategy versions loading error:', error);
        resetStrategyVersionDropdown('Failed to load versions');
    } finally {
        setAutosuggestLoading('strategyVersionSelect', false);
    }
}

async function handleStrategyVersionChange(event) {
    const historySelect = document.getElementById('strategyHistorySelect');
    const strategyId = historySelect?.value || '';
    const versionNo = event?.target?.value || '';
    if (!strategyId || !versionNo) return;

    const loadingDiv = document.getElementById('strategyLoading');
    const resultsDiv = document.getElementById('strategyResults');
    if (loadingDiv) loadingDiv.classList.remove('hidden');

    try {
        const response = await apiRequest(`/api/strategy/${encodeURIComponent(strategyId)}/versions/${encodeURIComponent(versionNo)}`);
        const strategyOutput = response?.strategy_output;
        if (!strategyOutput || typeof strategyOutput !== 'object') {
            throw new Error('Strategy version data is not available.');
        }

        appData.generatedStrategy = strategyOutput;
        saveDataToStorage();
        displayStrategyResults(strategyOutput);
        if (resultsDiv) resultsDiv.classList.remove('hidden');
        showSuccessMessage(`Loaded strategy version ${versionNo}.`);
    } catch (error) {
        console.error('Strategy version detail loading error:', error);
        showErrorMessage(error.message || 'Failed to load strategy version.');
    } finally {
        if (loadingDiv) loadingDiv.classList.add('hidden');
    }
}

async function generateAIStrategy() {
    console.log('Generating AI strategy...');
    
    const loadingDiv = document.getElementById('strategyLoading');
    const inputDiv = document.getElementById('strategyInput');
    const resultsDiv = document.getElementById('strategyResults');
    
    if (!loadingDiv || !inputDiv || !resultsDiv) return;
    if (!appData.businessProfile) {
        showErrorMessage('Please complete your Business Profile first.');
        return;
    }

    inputDiv.classList.add('hidden');
    loadingDiv.classList.remove('hidden');
    resultsDiv.classList.add('hidden');

    try {
        const profile = appData.businessProfile;
        const payload = {
            business_profile: {
                business_name: profile.businessName,
                industry: profile.industry,
                company_size: profile.companySize,
                revenue: profile.revenue || null,
                continent: profile.continent,
                country: profile.country || null,
                region: profile.region || null,
                marketing_goals: Array.isArray(profile.marketingGoals) ? profile.marketingGoals : [],
                budget_range: profile.budget ? `$${Number(profile.budget).toLocaleString()}` : null,
                target_audience: profile.targetAudience || null,
                website_link: profile.websiteLink || null
            }
        };

        const response = await apiRequest('/api/strategy/generate', 'POST', payload);
        const strategy = response?.strategy || {};

        appData.generatedStrategy = strategy;
        saveDataToStorage();
        displayStrategyResults(strategy);

        loadingDiv.classList.add('hidden');
        resultsDiv.classList.remove('hidden');
        await loadStrategyHistoryOptions();
        showSuccessMessage('AI strategy generated successfully!');
    } catch (error) {
        console.error('Strategy generation error:', error);
        loadingDiv.classList.add('hidden');
        inputDiv.classList.remove('hidden');
        showErrorMessage(error.message || 'Failed to generate strategy.');
    }
}

function generateStrategyRecommendations() {
    const profile = appData.businessProfile;
    
    const strategies = {
        Technology: {
            channels: ['LinkedIn', 'Email Marketing', 'WhatsApp Business', 'Content Marketing'],
            budgetAllocation: { 'LinkedIn': '35%', 'Email': '30%', 'WhatsApp': '20%', 'Content': '15%' },
            timeline: '4-month campaign with weekly optimization',
            keyMessages: ['Technical expertise', 'Innovation leadership', 'Scalable solutions', 'ROI-focused results'],
            contentStrategy: ['Technical whitepapers', 'Case studies', 'Product demos', 'Webinar series', 'Developer tutorials']
        },
        Healthcare: {
            channels: ['Email Marketing', 'LinkedIn', 'Professional Networks'],
            budgetAllocation: { 'Email': '40%', 'LinkedIn': '35%', 'Professional Networks': '25%' },
            timeline: '6-month campaign with compliance focus',
            keyMessages: ['Patient safety', 'Regulatory compliance', 'Clinical outcomes', 'Cost efficiency'],
            contentStrategy: ['Clinical studies', 'Compliance guides', 'Patient testimonials', 'Educational content']
        },
        Finance: {
            channels: ['LinkedIn', 'Email Marketing', 'Financial Publications'],
            budgetAllocation: { 'LinkedIn': '45%', 'Email': '30%', 'Publications': '25%' },
            timeline: '3-month intensive campaign',
            keyMessages: ['Financial security', 'Risk management', 'Regulatory expertise', 'ROI optimization'],
            contentStrategy: ['Market analysis', 'Risk assessments', 'Regulatory updates', 'Financial forecasts']
        }
    };
    
    const industryStrategy = strategies[profile.industry] || strategies.Technology;
    
    return {
        ...industryStrategy,
        targetBudget: profile.budget,
        targetAudience: profile.targetAudience,
        companySize: profile.companySize
    };
}

function displayStrategyResults(strategy) {
    const safeArray = (v) => Array.isArray(v) ? v : [];
    const safeObject = (v) => (v && typeof v === 'object' && !Array.isArray(v)) ? v : {};
    const renderList = (arr, className, emptyMsg) =>
        arr.length ? arr.map(item => `<div class="${className}">${item}</div>`).join('') : `<div class="${className}">${emptyMsg}</div>`;

    // 1) Recommended channels
    const channelGrid = document.getElementById('channelRecommendations');
    if (channelGrid) {
        const channels = safeArray(strategy.recommended_channels);
        channelGrid.innerHTML = channels.length
            ? channels.map(channel => `
                <div class="channel-card">
                    <h4>${channel}</h4>
                    <p>Recommended for your business profile</p>
                </div>
            `).join('')
            : `<div class="channel-card"><h4>No channels available</h4><p>Strategy response did not include channel recommendations.</p></div>`;
    }

    // 2) Budget allocation + 3) Budget analysis
    const budgetDiv = document.getElementById('budgetAllocation');
    if (budgetDiv) {
        const allocation = safeObject(strategy.budget_allocation);
        const allocationHtml = Object.entries(allocation).length
            ? Object.entries(allocation).map(([key, value]) => `
                <div class="budget-item">
                    <strong>${formatStrategyKey(key)}:</strong> ${value ?? 0}%
                </div>
            `).join('')
            : `<div class="budget-item">Budget allocation not available.</div>`;

        const analysis = safeObject(strategy.budget_analysis);
        const competitor = safeObject(analysis.competitor_benchmark);
        const recommendations = safeArray(analysis.budget_recommendations);

        const analysisHtml = Object.keys(analysis).length
            ? `
                <div class="budget-item"><strong>Recommended Budget Range:</strong> ${analysis.recommended_budget_range || 'N/A'}</div>
                <div class="budget-item"><strong>Budget Assessment:</strong> ${analysis.budget_assessment || 'N/A'}</div>
                <div class="budget-item"><strong>Budget Recommendations:</strong> ${recommendations.length ? recommendations.join(', ') : 'N/A'}</div>
                <div class="budget-item"><strong>Competitor Benchmark:</strong> ${
                    Object.keys(competitor).length
                        ? Object.entries(competitor).map(([k, v]) => `${formatStrategyKey(k)}: ${v}`).join(' | ')
                        : 'N/A'
                }</div>
            `
            : `<div class="budget-item">Budget analysis not available.</div>`;

        budgetDiv.innerHTML = allocationHtml + analysisHtml;
    }

    // 4) Campaign timeline (dynamic phases only)
    const timelineDiv = document.getElementById('campaignTimeline');
    if (timelineDiv) {
        const timeline = safeObject(strategy.campaign_timeline);
        const phases = Object.entries(timeline);

        timelineDiv.innerHTML = phases.length
            ? phases.map(([phaseKey, phaseValue]) => {
                const phase = safeObject(phaseValue);
                const activities = safeArray(phase.key_activities);
                return `
                    <div class="timeline-item">
                        <strong>${phase.name || formatStrategyKey(phaseKey)}</strong>
                        <div>Duration: ${phase.duration || 'N/A'}</div>
                        <div>${phase.description || 'No description provided.'}</div>
                        <div>Activities: ${activities.length ? activities.join(', ') : 'N/A'}</div>
                    </div>
                `;
            }).join('')
            : `<div class="timeline-item">Campaign timeline not available.</div>`;
    }

    // 5) Target segments + insights + provider info
    const messagingDiv = document.getElementById('keyMessaging');
    if (messagingDiv) {
        const segments = safeArray(strategy.target_segments);
        const providerInfo = safeObject(strategy.provider_info);

        messagingDiv.innerHTML = `
            ${renderList(segments, 'message-item', 'Target segments not available.')}
            <div class="message-item"><strong>Insights:</strong> ${strategy.insights || 'No insights provided.'}</div>
            <div class="message-item"><strong>Provider:</strong> ${providerInfo.provider || 'unknown'}</div>
            <div class="message-item"><strong>Model:</strong> ${providerInfo.model || 'unknown'}</div>
        `;
    }

    // 6) Content strategy + KPIs
    const contentDiv = document.getElementById('contentStrategy');
    if (contentDiv) {
        const contentStrategy = safeArray(strategy.content_strategy);
        const kpis = safeArray(strategy.kpis);

        contentDiv.innerHTML = `
            ${renderList(contentStrategy, 'content-item', 'Content strategy not available.')}
            ${kpis.length ? `<div class="content-item"><strong>KPIs:</strong> ${kpis.join(', ')}</div>` : `<div class="content-item">KPIs not available.</div>`}
        `;
    }

    // Export button unchanged
    const exportBtn = document.getElementById('exportStrategy');
    if (exportBtn) {
        exportBtn.onclick = () => {
            showSuccessMessage('Strategy export initiated! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
        };
    }
}

function getCurrentStrategyId() {
    const persistentId = appData?.currentStrategyId;
    if (typeof persistentId === 'string' && persistentId.trim()) {
        return persistentId.trim();
    }
    const fallbackId = appData?.generatedStrategy?.strategy_id;
    return typeof fallbackId === 'string' && fallbackId.trim() ? fallbackId.trim() : '';
}

function setStrategyExecutionStatus(message, isError = false) {
    const statusEl = document.getElementById('strategyExecutionStatus');
    if (!statusEl) return;
    statusEl.innerHTML = `<span class="${isError ? 'status status--error' : 'status status--success'}">${message}</span>`;
}

function updateStrategyLaunchButtonState() {
    const launchBtn = document.getElementById('launchStrategyCampaignBtn');
    if (!launchBtn) return;
    const hasCampaign = typeof appData.reviewCampaignId === 'string' && appData.reviewCampaignId.trim();
    launchBtn.disabled = !hasCampaign;
}

async function createCampaignFromStrategy() {
    const strategyId = getCurrentStrategyId();
    if (!strategyId) {
        showErrorMessage('Please generate or load a strategy first.');
        setStrategyExecutionStatus('Strategy ID not found. Generate or load a strategy first.', true);
        return;
    }

    try {
        const response = await apiRequest('/api/campaigns/from-strategy', 'POST', {
            strategy_id: strategyId
        });
        await loadCampaigns();
        const campaignId = response?.campaign_id || 'unknown';
        appData.reviewCampaignId = (response?.campaign_id && String(response.campaign_id).trim()) ? String(response.campaign_id).trim() : null;
        saveDataToStorage();
        updateStrategyLaunchButtonState();
        showCampaignTab('active');
        setActiveCampaignTab(document.querySelector('[data-tab="active"]'));
        setStrategyExecutionStatus(`Campaign created from strategy (ID: ${campaignId}).`);
        showSuccessMessage('Campaign created. Review and launch when ready.');
    } catch (error) {
        appData.reviewCampaignId = null;
        updateStrategyLaunchButtonState();
        setStrategyExecutionStatus(error.message || 'Failed to create campaign from strategy.', true);
        showErrorMessage(error.message || 'Failed to create campaign from strategy.');
    }
}

async function launchStrategyReviewCampaign() {
    const campaignId = String(appData.reviewCampaignId || '').trim();
    if (!campaignId) {
        setStrategyExecutionStatus('No review campaign available to launch yet.', true);
        return;
    }
    try {
        const response = await apiRequest(`/api/campaigns/${encodeURIComponent(campaignId)}/launch`, 'POST', {});
        await loadCampaigns();
        setStrategyExecutionStatus(`Campaign launched (ID: ${campaignId}).`);
        showSuccessMessage(response?.message || 'Campaign launched successfully.');
    } catch (error) {
        setStrategyExecutionStatus(error.message || 'Failed to launch campaign.', true);
        showErrorMessage(error.message || 'Failed to launch campaign.');
    }
}

async function generateLeadsFromStrategy() {
    const strategyId = getCurrentStrategyId();
    if (!strategyId) {
        showErrorMessage('Please generate or load a strategy first.');
        setStrategyExecutionStatus('Strategy ID not found. Generate or load a strategy first.', true);
        return;
    }

    try {
        const response = await apiRequest('/api/leads/from-strategy', 'POST', {
            strategy_id: strategyId
        });
        const jobId = response?.job_id || response?.task_id || 'unknown';
        setStrategyExecutionStatus(`Lead generation started (Job ID: ${jobId}).`);
        showSuccessMessage(response?.message || 'Lead generation started from strategy.');
    } catch (error) {
        setStrategyExecutionStatus(error.message || 'Failed to start lead generation from strategy.', true);
        showErrorMessage(error.message || 'Failed to start lead generation from strategy.');
    }
}

// Lead Scraper Functions
function getNormalizedSelectedSources() {
    const selectedValues = Array.from(
        document.querySelectorAll('#sourceSelection input[type="checkbox"]:checked')
    ).map(cb => cb.value);

    if (selectedValues.includes('all')) {
        return ['github', 'google_maps', 'linkedin', 'volza'];
    }

    return Array.from(new Set(selectedValues.filter(value => value !== 'all')));
}

function setupSourceSelectionControls() {
    const sourceContainer = document.getElementById('sourceSelection');
    if (!sourceContainer) return;

    const allCheckbox = sourceContainer.querySelector('input[type="checkbox"][value="all"]');
    const individualCheckboxes = Array.from(
        sourceContainer.querySelectorAll('input[type="checkbox"]:not([value="all"])')
    );

    if (!allCheckbox || individualCheckboxes.length === 0) return;

    allCheckbox.addEventListener('change', function() {
        if (this.checked) {
            individualCheckboxes.forEach(cb => {
                cb.checked = true;
            });
        }
    });

    individualCheckboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            if (!cb.checked) {
                allCheckbox.checked = false;
                return;
            }

            if (individualCheckboxes.every(input => input.checked)) {
                allCheckbox.checked = true;
            }
        });
    });
}

function renderSourceResultsSummary(results = {}, summary = null) {
    const container = document.getElementById('sourceResultsSummary');
    if (!container) return;

    const safeResults = (results && typeof results === 'object') ? results : {};
    const entries = Object.entries(safeResults);
    const safeSummary = (summary && typeof summary === 'object') ? summary : null;

    if (entries.length === 0 && !safeSummary) {
        container.innerHTML = '';
        return;
    }

    const sourceRows = entries.map(([source, sourceResult]) => {
        const isSuccess = sourceResult?.status === 'success';
        const label = source.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

        if (isSuccess) {
            const leadCount = Array.isArray(sourceResult?.leads) ? sourceResult.leads.length : 0;
            const suffix = source === 'browser_extension' ? 'clean leads' : 'leads';
            return `<div class="status status--success" style="margin-bottom: 8px;">${label}: ${leadCount} ${suffix}</div>`;
        }

        const message = sourceResult?.message || 'Source failed.';
        const cleanMessage = message.includes('API key')
            ? 'API key not configured.'
            : message;

        return `<div class="status status--error" style="margin-bottom: 8px;">${label}: ${cleanMessage}</div>`;
    }).join('');

    const summaryHtml = safeSummary
        ? `<div class="summary-box"><span>Total: ${Number(safeSummary.total_sources_requested) || 0}</span><span class="success-count">Successful: ${Number(safeSummary.successful_sources) || 0}</span><span class="failed-count">Failed: ${Number(safeSummary.failed_sources) || 0}</span></div>`
        : '';

    container.innerHTML = summaryHtml + sourceRows;
}

function handleLeadScraping(e) {
    e.preventDefault();
    console.log('Lead scraping form submitted');

    if (!validateLeadScraperAutosuggestFields()) {
        return;
    }
    
    const location = getStructuredLocationPayload();
    const websiteUrl = String(document.getElementById('websiteUrl')?.value || '').trim();
    const businessType = document.getElementById('businessType').value;
    const radius = document.getElementById('radius').value;
    const additionalFilters = document.getElementById('additionalFilters').value;
    const sources = getNormalizedSelectedSources();
    const extensionPayload = browserExtensionPayloadState;
    const hasBrowserContext = Boolean(websiteUrl || extensionPayload);

    if (!hasBrowserContext && !String(location?.text || '').trim()) {
        showErrorMessage('Location is required.');
        return;
    }

    if (!hasBrowserContext && !String(businessType || '').trim()) {
        showErrorMessage('Business type is required.');
        return;
    }

    if (!hasBrowserContext && sources.length === 0) {
        showErrorMessage('Please select at least one source.');
        return;
    }
    
    const searchParams = {
        location,
        websiteUrl,
        businessType,
        radius,
        additionalFilters,
        sources,
        extensionPayload
    };
    
    startLeadScraping(searchParams);
}

async function startLeadScraping(params) {
    const progressDiv = document.getElementById('scrapingProgress');
    const resultsDiv = document.getElementById('leadsResults');
    const noResultsDiv = document.getElementById('noLeadsMessage');
    const exportBtn = document.getElementById('exportLeads');
    
    if (!progressDiv || !resultsDiv) return;

    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    if (progressFill) progressFill.style.width = '15%';
    if (progressText) progressText.textContent = '15%';

    progressDiv.classList.remove('hidden');
    resultsDiv.classList.add('hidden');
    if (noResultsDiv) noResultsDiv.classList.add('hidden');
    renderSourceResultsSummary();

    try {
        const scrapeRequest = {
            location: params.location,
            business_type: params.businessType || 'Website Leads',
            radius: Number(params.radius) || 10,
            max_results: 25,
            sources: Array.isArray(params.sources) ? params.sources : ['github'],
            website_url: params.websiteUrl || null,
            extension_payload: params.extensionPayload || null
        };

        const startResponse = await apiRequest('/api/leads/scrape', 'POST', scrapeRequest);
        const taskId = startResponse.task_id;

        if (progressFill) progressFill.style.width = '40%';
        if (progressText) progressText.textContent = '40%';

        const POLL_INTERVAL_MS = 1000;
        const MAX_POLL_ATTEMPTS = 180; // 3 minutes

        let taskData = null;
        for (let attempt = 0; attempt < MAX_POLL_ATTEMPTS; attempt++) {
            await sleep(POLL_INTERVAL_MS);
            const statusResponse = await apiRequest(`/api/leads/${taskId}`);
            taskData = statusResponse.data;

            const pct = Math.min(95, 40 + Math.floor(((attempt + 1) / MAX_POLL_ATTEMPTS) * 55));
            if (progressFill) progressFill.style.width = `${pct}%`;
            if (progressText) progressText.textContent = `${pct}%`;

            if (taskData?.status === 'completed') {
                break;
            }
            if (taskData?.status === 'failed') {
                break;
            }
            // status === "processing" => continue polling
        }

        renderSourceResultsSummary(taskData?.results || {}, taskData?.summary || null);

        if (!taskData || (taskData.status !== 'completed' && taskData.status !== 'failed')) {
            throw new Error(taskData?.error || 'Lead scraping did not complete in time.');
        }

        if (taskData.status === 'failed') {
            throw new Error(taskData?.error || 'Lead scraping failed.');
        }

        const normalizedLeads = Array.isArray(taskData.leads)
            ? taskData.leads.map(normalizeApiLead)
            : [];

        appData.scrapedLeads = normalizedLeads;
        saveDataToStorage();

        if (progressFill) progressFill.style.width = '100%';
        if (progressText) progressText.textContent = '100%';

        displayScrapedLeads(normalizedLeads);
        progressDiv.classList.add('hidden');
        resultsDiv.classList.remove('hidden');
        if (exportBtn) exportBtn.disabled = false;

        showSuccessMessage(`Found ${normalizedLeads.length} leads!`);
    } catch (error) {
        console.error('Lead scraping error:', error);
        progressDiv.classList.add('hidden');
        if (noResultsDiv) noResultsDiv.classList.remove('hidden');
        showErrorMessage(error.message || 'Lead scraping failed.');
    }
}

function displayScrapedLeads(leads) {
    const tbody = document.getElementById('leadsTableBody');
    const resultsMeta = document.getElementById('leadsResultsMeta');
    if (!tbody) return;

    const safeLeads = Array.isArray(leads) ? leads : [];
    const displayedLeads = safeLeads.slice(0, 10);
    const total = safeLeads.length;
    const shown = displayedLeads.length;

    const escapeHtml = (value) => String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    const titleize = (key) => String(key || '')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());

    const NOT_AVAILABLE = 'Not Available';

    const getNormalizedValue = (lead, key) => {
        const value = lead?.[key];
        if (value === null || value === undefined || value === '') return NOT_AVAILABLE;
        return String(value);
    };

    const renderCellValue = (value) => {
        const normalized = String(value || NOT_AVAILABLE);
        if (normalized === NOT_AVAILABLE) {
            return `<span class="table-cell--muted">${escapeHtml(NOT_AVAILABLE)}</span>`;
        }
        return escapeHtml(normalized);
    };

    const renderLinkCell = (value) => {
        const normalized = String(value || NOT_AVAILABLE);
        if (normalized === NOT_AVAILABLE) {
            return `<span class="table-cell--muted">${escapeHtml(NOT_AVAILABLE)}</span>`;
        }

        const href = normalized.startsWith('http') ? normalized : `https://${normalized}`;
        return `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(normalized)}</a>`;
    };

    if (resultsMeta) {
        if (total > 0) {
            resultsMeta.textContent = `Showing ${shown} of ${total} results. Download full data using "Export CSV".`;
        } else {
            resultsMeta.textContent = 'Showing 0 of 0 results.';
        }
    }

    if (total === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="11" class="table-cell--muted">No leads found</td>
            </tr>
        `;
    } else {
        tbody.innerHTML = displayedLeads.map((leadRaw) => {
        const lead = (leadRaw && typeof leadRaw === 'object') ? leadRaw : {};

        const name = getNormalizedValue(lead, 'name');
        const company = getNormalizedValue(lead, 'company');
        const email = getNormalizedValue(lead, 'email');
        const phone = getNormalizedValue(lead, 'phone');
        const website = getNormalizedValue(lead, 'website');
        const linkedin = getNormalizedValue(lead, 'linkedin');
        const github = getNormalizedValue(lead, 'github');
        const location = getNormalizedValue(lead, 'location');
        const designation = getNormalizedValue(lead, 'designation');
        const industry = getNormalizedValue(lead, 'industry');
        const source = getNormalizedValue(lead, 'source').toLowerCase();
        const sourceLabel = titleize(source);
        const sourceClass = source.replace(/[^a-z0-9_-]/g, '');

        return `
            <tr>
                <td>${renderCellValue(name)}</td>
                <td>${renderCellValue(company)}</td>
                <td>${renderCellValue(email)}</td>
                <td>${renderCellValue(phone)}</td>
                <td>${renderLinkCell(website)}</td>
                <td>${renderLinkCell(linkedin)}</td>
                <td>${renderLinkCell(github)}</td>
                <td>${renderCellValue(location)}</td>
                <td>${renderCellValue(designation)}</td>
                <td>${renderCellValue(industry)}</td>
                <td><span class="source-badge source-badge--${escapeHtml(sourceClass)}">${escapeHtml(sourceLabel)}</span></td>
            </tr>
        `;
        }).join('');
    }

    const exportBtn = document.getElementById('exportLeads');
    if (exportBtn) {
        exportBtn.onclick = () => {
            exportLeadsToCSV(safeLeads);
        };
    }
}

function exportLeadsToCSV(leads) {
    const headers = ['Name', 'Company', 'Email', 'Phone', 'Location', 'Website', 'Source', 'Industry'];
    const csvContent = [
        headers.join(','),
        ...leads.map(lead => [
            `"${String(lead.name || '').replace(/"/g, '""')}"`,
            `"${String(lead.company || '').replace(/"/g, '""')}"`,
            `"${String(lead.email || '').replace(/"/g, '""')}"`,
            `"${String(lead.phone || '').replace(/"/g, '""')}"`,
            `"${String(lead.location || '').replace(/"/g, '""')}"`,
            `"${String(lead.website || '').replace(/"/g, '""')}"`,
            `"${String(lead.source || '').replace(/"/g, '""')}"`,
            `"${String(lead.industry || '').replace(/"/g, '""')}"`
        ].join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'scraped_leads.csv';
    a.click();
    window.URL.revokeObjectURL(url);
    
    showSuccessMessage('Leads exported successfully! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
}

// Customer Data Enrichment Functions
function setupDragAndDrop(area) {
    area.addEventListener('dragover', (e) => {
        e.preventDefault();
        area.classList.add('dragover');
    });
    
    area.addEventListener('dragleave', () => {
        area.classList.remove('dragover');
    });
    
    area.addEventListener('drop', (e) => {
        e.preventDefault();
        area.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload({ target: { files } });
        }
    });
}

async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Show step 2
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    
    if (step1) step1.classList.add('hidden');
    if (step2) step2.classList.remove('hidden');

    try {
        const formData = new FormData();
        formData.append('file', file);

        const response = await apiRequestWithOptions('/api/enrichment/preview-csv', {
            method: 'POST',
            body: formData,
            isFormData: true
        });

        const columns = Array.isArray(response?.columns) ? response.columns : [];
        const previewRows = Array.isArray(response?.preview) ? response.preview : [];

        enrichmentPreviewState.columns = columns;
        enrichmentPreviewState.preview = previewRows;
        enrichmentPreviewState.mapping = {};

        displayColumnMapping(columns);
    } catch (error) {
        console.error('CSV preview error:', error);
        showErrorMessage(error.message || 'Failed to preview CSV. Using fallback mapping.');
        enrichmentPreviewState.columns = ['Company Name', 'Email', 'Phone', 'Industry'];
        enrichmentPreviewState.preview = [];
        enrichmentPreviewState.mapping = {};
        displayColumnMapping(enrichmentPreviewState.columns);
    }
}

function displayColumnMapping(columns) {
    const mappingDiv = document.getElementById('columnMapping');
    if (!mappingDiv) return;

    const targets = ['business_name', 'email', 'phone', 'industry', 'website', 'none'];
    const targetLabels = {
        business_name: 'Company Name',
        email: 'Email',
        phone: 'Phone',
        industry: 'Industry',
        website: 'Website',
        none: 'None',
    };
    const suggestTarget = (columnName) => {
        const key = String(columnName || '').trim().toLowerCase();
        if (!key) return 'none';
        if (key.includes('email')) return 'email';
        if (key.includes('phone') || key.includes('mobile') || key.includes('tel')) return 'phone';
        if (key.includes('industry') || key.includes('category') || key.includes('sector')) return 'industry';
        if (key.includes('website') || key.includes('url') || key.includes('site')) return 'website';
        if (key.includes('company') || key.includes('business') || key === 'name' || key.includes('organization')) return 'business_name';
        return 'none';
    };

    const previewRows = Array.isArray(enrichmentPreviewState.preview)
        ? enrichmentPreviewState.preview.slice(0, 2)
        : [];
    const escapeHtml = (value) => String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    const previewText = (columnName) => {
        if (!previewRows.length) return '-';
        const values = previewRows
            .map((row) => row?.[columnName])
            .map((value) => String(value ?? '').trim())
            .filter((value) => value.length > 0);
        return values.length ? values.join(' | ') : '-';
    };

    mappingDiv.innerHTML = `
        <div class="column-mapping">
            <h4>Map CSV columns to system fields:</h4>
            <div class="table-responsive">
                <table class="table">
                    <thead>
                        <tr>
                            <th>File Label</th>
                            <th>Field Mapping</th>
                            <th>Preview Data</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${columns.map((col) => `
                            <tr>
                                <td>${escapeHtml(col)}</td>
                                <td style="min-width: 180px;">
                                    <select class="form-control enrichment-column-mapping" data-source-column="${escapeHtml(col)}">
                                        ${targets.map((target) => `
                                            <option value="${target}" ${suggestTarget(col) === target ? 'selected' : ''}>${targetLabels[target] || target}</option>
                                        `).join('')}
                                    </select>
                                </td>
                                <td>${escapeHtml(previewText(col))}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    const mappingSelects = mappingDiv.querySelectorAll('.enrichment-column-mapping');
    mappingSelects.forEach((select) => {
        const sourceColumn = String(select.getAttribute('data-source-column') || '');
        if (!sourceColumn) return;
        if (!select.id) {
            select.id = `enrichmentMapping_${sourceColumn.replace(/[^a-z0-9_-]/gi, '_')}`;
        }
        enrichmentPreviewState.mapping[sourceColumn] = String(select.value || 'none');
        select.addEventListener('change', function () {
            enrichmentPreviewState.mapping[sourceColumn] = String(this.value || 'none');
        });
        enhanceSelectToAutosuggest(select.id, {
            ariaLabel: `${sourceColumn} mapping suggestions`
        });
    });
}

function collectColumnMappingSelections() {
    const mapping = {};
    const selects = document.querySelectorAll('.enrichment-column-mapping');
    selects.forEach((select) => {
        const sourceColumn = String(select.getAttribute('data-source-column') || '').trim();
        const target = String(select.value || '').trim();
        if (sourceColumn && target && target.toLowerCase() !== 'none') {
            mapping[sourceColumn] = target;
        }
    });
    return mapping;
}

async function pollEnrichmentTask(taskId, onProcessing) {
    const POLL_INTERVAL_MS = 2000;
    const MAX_ATTEMPTS = 180;

    for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
        await sleep(POLL_INTERVAL_MS);

        const response = await apiRequest(`/api/enrichment/status/${taskId}`);
        const task = response?.status || response?.data || response || {};
        const status = task?.status;

        if (status === 'processing') {
            if (typeof onProcessing === 'function') {
                onProcessing(attempt, MAX_ATTEMPTS);
            }
            continue;
        }

        if (status === 'completed' || status === 'failed') {
            return task;
        }
    }

    throw new Error('Data enrichment did not complete in time.');
}

async function startDataEnrichment() {
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');
    const fileInput = document.getElementById('customerDataFile');
    const progressBar = document.getElementById('enrichmentProgress');
    const progressText = document.getElementById('enrichmentProgressText');

    const file = fileInput?.files?.[0];
    if (!file) {
        showErrorMessage('Please upload a file before starting enrichment.');
        return;
    }

    if (step2) step2.classList.add('hidden');
    if (step3) step3.classList.remove('hidden');

    if (progressBar) progressBar.style.width = '10%';
    if (progressText) progressText.textContent = '10%';

    try {
        const selectedMapping = collectColumnMappingSelections();
        const formData = new FormData();
        formData.append('file', file);
        formData.append('column_mapping', JSON.stringify(selectedMapping));

        const uploadResponse = await apiRequestWithOptions('/api/enrichment/upload', {
            method: 'POST',
            body: formData,
            isFormData: true
        });

        const taskId = uploadResponse?.task_id;
        if (!taskId) {
            throw new Error('Enrichment task ID not returned.');
        }

        if (progressBar) progressBar.style.width = '20%';
        if (progressText) progressText.textContent = '20%';

        const finalTask = await pollEnrichmentTask(taskId, (attempt, maxAttempts) => {
            const pct = Math.min(95, 20 + Math.floor(((attempt + 1) / maxAttempts) * 75));
            if (progressBar) progressBar.style.width = `${pct}%`;
            if (progressText) progressText.textContent = `${pct}%`;
        });

        if (finalTask.status === 'failed') {
            throw new Error(finalTask.error || 'Data enrichment failed.');
        }

        if (progressBar) progressBar.style.width = '100%';
        if (progressText) progressText.textContent = '100%';

        showEnrichmentResults(finalTask);
    } catch (error) {
        console.error('Enrichment error:', error);
        showErrorMessage(error.message || 'Data enrichment failed.');
    }
}

function showEnrichmentResults(response) {
    // Show step 4
    const step3 = document.getElementById('step3');
    const step4 = document.getElementById('step4');

    if (step3) step3.classList.add('hidden');
    if (step4) step4.classList.remove('hidden');

    const beforeData = response?.original_records || response?.original_data || [];
    const afterData = response?.enriched_records || response?.enriched_data || [];

    displayComparisonTables(beforeData, afterData);

    // Setup real CSV download button
    const downloadBtn = document.getElementById('downloadEnrichedData');
    if (downloadBtn) {
        downloadBtn.onclick = () => {
            downloadAsCSV(afterData, 'enriched_data.csv');
            showSuccessMessage('Enriched data download started! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
        };
    }

    showSuccessMessage('Data enrichment completed successfully! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
}

function downloadAsCSV(data, filename) {
    const rows = Array.isArray(data) ? data : [];

    const toCell = (value) => {
        if (value === null || value === undefined) return '';
        if (Array.isArray(value) || typeof value === 'object') {
            try {
                return JSON.stringify(value);
            } catch {
                return String(value);
            }
        }
        return String(value);
    };

    const escapeCSV = (value) => {
        const str = toCell(value);
        const escaped = str.replace(/"/g, '""');
        return `"${escaped}"`;
    };

    const headers = Array.from(
        new Set(
            rows.flatMap(row => (row && typeof row === 'object') ? Object.keys(row) : [])
        )
    );

    const csvLines = [];
    if (headers.length > 0) {
        csvLines.push(headers.map(escapeCSV).join(','));
        for (const row of rows) {
            const record = (row && typeof row === 'object') ? row : {};
            csvLines.push(headers.map(key => escapeCSV(record[key])).join(','));
        }
    } else {
        csvLines.push('"No data"');
    }

    const csvContent = csvLines.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename || 'data.csv';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    window.URL.revokeObjectURL(url);
}

function displayComparisonTables(beforeData, afterData) {
    const safeBefore = Array.isArray(beforeData) ? beforeData : [];
    const safeAfter = Array.isArray(afterData) ? afterData : [];

    const toTitle = (key) => String(key || '')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());

    const escapeHtml = (value) => String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    const formatValue = (value) => {
        if (value === null || value === undefined || value === '') return '-';

        if (Array.isArray(value)) {
            if (!value.length) return '-';
            return value.map(item => formatValue(item)).join('<br>');
        }

        if (typeof value === 'object') {
            const entries = Object.entries(value);
            if (!entries.length) return '-';
            return entries
                .map(([k, v]) => `<div><strong>${escapeHtml(toTitle(k))}:</strong> ${formatValue(v)}</div>`)
                .join('');
        }

        return escapeHtml(value);
    };

    const collectColumns = (rows) => {
        const cols = [];
        const seen = new Set();
        rows.forEach(row => {
            if (!row || typeof row !== 'object') return;
            Object.keys(row).forEach(k => {
                if (!seen.has(k)) {
                    seen.add(k);
                    cols.push(k);
                }
            });
        });
        return cols;
    };

    const renderTable = (headEl, bodyEl, rows, emphasize = false) => {
        if (!headEl || !bodyEl) return;

        const columns = collectColumns(rows);
        if (!columns.length) {
            headEl.innerHTML = '<tr><th>Data</th></tr>';
            bodyEl.innerHTML = '<tr><td>-</td></tr>';
            return;
        }

        headEl.innerHTML = `<tr>${columns.map(col => `<th>${escapeHtml(toTitle(col))}</th>`).join('')}</tr>`;

        bodyEl.innerHTML = rows.length
            ? rows.map(row => {
                const cells = columns.map(col => {
                    const rendered = formatValue(row?.[col]);
                    return emphasize ? `<td><strong>${rendered}</strong></td>` : `<td>${rendered}</td>`;
                }).join('');
                return `<tr>${cells}</tr>`;
            }).join('')
            : `<tr><td colspan="${columns.length}">-</td></tr>`;
    };

    // Before table
    const beforeHead = document.getElementById('beforeTableHead');
    const beforeBody = document.getElementById('beforeTableBody');
    renderTable(beforeHead, beforeBody, safeBefore, false);

    // After table
    const afterHead = document.getElementById('afterTableHead');
    const afterBody = document.getElementById('afterTableBody');
    renderTable(afterHead, afterBody, safeAfter, true);
}

// Campaign Manager Functions
function setupCampaignManagerListeners() {
    // Campaign tabs
    document.querySelectorAll('.campaign-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const tabType = this.dataset.tab;
            showCampaignTab(tabType);
            setActiveCampaignTab(this);
        });
    });
    
    // Create campaign button
    const createCampaignBtn = document.getElementById('createCampaignBtn');
    if (createCampaignBtn) {
        createCampaignBtn.addEventListener('click', createCampaign);
    }

    const campaignStrategy = document.getElementById('campaignStrategy');
    if (campaignStrategy && !campaignStrategy.dataset.bound) {
        campaignStrategy.addEventListener('change', handleCampaignStrategyChange);
        campaignStrategy.dataset.bound = '1';
    }
    
    // Load active campaigns
    loadCampaigns();
    loadCampaignStrategyOptions();
}

function resetCampaignStrategyVersionDropdown() {
    campaignStrategyVersionOptions = [];
    const versionSelect = document.getElementById('campaignStrategyVersion');
    const warningEl = document.getElementById('campaignStrategyWarning');
    if (versionSelect) {
        versionSelect.innerHTML = '<option value="">Select version</option>';
        versionSelect.value = '';
        versionSelect.disabled = true;
        syncEnhancedSelectUI(versionSelect);
    }
    if (warningEl) {
        warningEl.classList.add('hidden');
    }
}

function populateCampaignStrategyVersionDropdown(versions) {
    const versionSelect = document.getElementById('campaignStrategyVersion');
    if (!versionSelect) return;

    const safeVersions = Array.isArray(versions) ? versions : [];
    campaignStrategyVersionOptions = safeVersions;

    versionSelect.innerHTML = '<option value="">Select version</option>';
    safeVersions.forEach((row) => {
        const versionNo = Number(row?.version_no);
        if (!Number.isFinite(versionNo)) return;
        const option = document.createElement('option');
        option.value = String(versionNo);
        option.textContent = `Version ${versionNo}`;
        versionSelect.appendChild(option);
    });
    versionSelect.disabled = safeVersions.length === 0;
    syncEnhancedSelectUI(versionSelect);
}

async function loadCampaignStrategyOptions() {
    const strategySelect = document.getElementById('campaignStrategy');
    if (!strategySelect) return;

    setAutosuggestLoading('campaignStrategy', true);
    try {
        const response = await apiRequest('/api/strategy/history');
        const strategies = Array.isArray(response?.strategies) ? response.strategies : [];
        campaignStrategyOptions = strategies
            .map((item) => ({
                id: item?.strategy_id,
                label: item?.business_name || item?.strategy_id || 'Unknown Strategy'
            }))
            .filter((item) => !!item.id);

        strategySelect.innerHTML = '<option value="">None</option>';
        campaignStrategyOptions.forEach((item) => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = item.label;
            strategySelect.appendChild(option);
        });
        syncEnhancedSelectUI(strategySelect);
    } catch (error) {
        console.error('Campaign strategy options loading error:', error);
        campaignStrategyOptions = [];
        strategySelect.innerHTML = '<option value="">None</option>';
        syncEnhancedSelectUI(strategySelect);
    } finally {
        setAutosuggestLoading('campaignStrategy', false);
        resetCampaignStrategyVersionDropdown();
    }
}

async function handleCampaignStrategyChange(event) {
    const strategyId = event?.target?.value || '';
    const versionSelect = document.getElementById('campaignStrategyVersion');

    resetCampaignStrategyVersionDropdown();
    setAutosuggestLoading('campaignStrategyVersion', true);
    if (!strategyId) {
        setAutosuggestLoading('campaignStrategyVersion', false);
        return;
    }

    if (versionSelect) {
        versionSelect.disabled = true;
        syncEnhancedSelectUI(versionSelect);
    }

    const requestToken = ++strategyVersionRequestToken;
    try {
        const response = await apiRequest(`/api/strategy/${encodeURIComponent(strategyId)}/versions`);
        if (requestToken !== strategyVersionRequestToken) return;
        const versions = Array.isArray(response?.versions) ? response.versions : [];
        populateCampaignStrategyVersionDropdown(versions);
    } catch (error) {
        if (requestToken !== strategyVersionRequestToken) return;
        console.error('Campaign strategy versions loading error:', error);
        resetCampaignStrategyVersionDropdown();
    } finally {
        setAutosuggestLoading('campaignStrategyVersion', false);
    }
}

async function loadCampaigns() {
    try {
        const response = await apiRequest('/api/campaigns');
        appData.campaigns = Array.isArray(response?.campaigns) ? response.campaigns : [];
        if (appData.reviewCampaignId) {
            const exists = appData.campaigns.some(
                (c) => String(c?.campaign_id || c?.id || '') === String(appData.reviewCampaignId)
            );
            if (!exists) {
                appData.reviewCampaignId = null;
            }
        }
        saveDataToStorage();
    } catch (error) {
        console.error('Campaign loading error:', error);
        appData.campaigns = [];
    }
    updateStrategyLaunchButtonState();
    displayActiveCampaigns();
}

function showCampaignTab(tabType) {
    document.querySelectorAll('.campaign-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    if (tabType === 'create') {
        const createTab = document.getElementById('createCampaign');
        if (createTab) createTab.classList.remove('hidden');
    } else if (tabType === 'active') {
        const activeTab = document.getElementById('activeCampaigns');
        if (activeTab) activeTab.classList.remove('hidden');
    }
}

function setActiveCampaignTab(activeTab) {
    document.querySelectorAll('.campaign-tab').forEach(tab => {
        tab.classList.remove('campaign-tab--active');
    });
    if (activeTab) {
        activeTab.classList.add('campaign-tab--active');
    }
}

function nextWizardStep(step) {
    // Hide all steps
    document.querySelectorAll('.wizard-step').forEach(s => {
        s.classList.add('hidden');
        s.classList.remove('wizard-step--active');
    });
    
    // Show target step
    const targetStep = document.querySelector(`[data-step="${step}"]`);
    if (targetStep) {
        targetStep.classList.remove('hidden');
        targetStep.classList.add('wizard-step--active');
    }
    
    // Special handling for content creation step
    if (step === 4) {
        generateContentForms();
    }
}

function generateContentForms() {
    const selectedChannels = Array.from(document.querySelectorAll('.wizard-step[data-step="2"] input[type="checkbox"]:checked'))
        .map(cb => cb.value);
    
    const contentDiv = document.getElementById('contentCreation');
    if (contentDiv) {
        contentDiv.innerHTML = selectedChannels.map(channel => {
            const normalized = String(channel || '').trim().toLowerCase();

            if (normalized === 'email') {
                return `
                    <div class="content-form">
                        <h5>Email Content</h5>
                        <div class="form-group">
                            <label class="form-label">Subject</label>
                            <input type="text" class="form-control" id="${channel}-subject" placeholder="Enter email subject">
                        </div>
                        <div class="form-group">
                            <label class="form-label">Body</label>
                            <textarea class="form-control" id="${channel}-content" rows="5" placeholder="Enter email body"></textarea>
                        </div>
                    </div>
                `;
            }

            if (normalized === 'linkedin' || normalized === 'facebook') {
                return `
                    <div class="content-form">
                        <h5>${channel} Content</h5>
                        <div class="form-group">
                            <label class="form-label">Post Content</label>
                            <textarea class="form-control" id="${channel}-content" rows="4" placeholder="Enter ${channel} post content"></textarea>
                        </div>
                    </div>
                `;
            }

            if (normalized === 'twitter') {
                return `
                    <div class="content-form">
                        <h5>Twitter Content</h5>
                        <div class="form-group">
                            <label class="form-label">Tweet Content</label>
                            <textarea class="form-control" id="${channel}-content" rows="3" maxlength="280" placeholder="Enter tweet content (max 280 chars)"></textarea>
                            <small style="color: var(--color-text-secondary);">Max 280 characters.</small>
                        </div>
                    </div>
                `;
            }

            if (normalized === 'whatsapp') {
                return `
                    <div class="content-form">
                        <h5>WhatsApp Content</h5>
                        <div class="form-group">
                            <label class="form-label">Message</label>
                            <textarea class="form-control" id="${channel}-content" rows="4" placeholder="Enter WhatsApp message"></textarea>
                        </div>
                    </div>
                `;
            }

            return `
                <div class="content-form">
                    <h5>${channel} Content</h5>
                    <div class="form-group">
                        <label class="form-label">Message</label>
                        <textarea class="form-control" id="${channel}-content" rows="4" placeholder="Enter ${channel} message"></textarea>
                    </div>
                </div>
            `;
        }).join('');
    }
}

function validateSelectedChannelContent(selectedChannels) {
    const normalizedChannels = Array.isArray(selectedChannels)
        ? selectedChannels.map((c) => String(c || "").trim().toLowerCase()).filter(Boolean)
        : [];

    for (const channel of normalizedChannels) {
        if (channel === "email") {
            const subjectEl = document.getElementById("Email-subject");
            const bodyEl = document.getElementById("Email-content");
            const subject = String(subjectEl?.value || "").trim();
            const body = String(bodyEl?.value || "").trim();
            if (!subject || !body) {
                return "Email channel requires both Subject and Body.";
            }
            continue;
        }

        if (channel === "linkedin") {
            const post = String(document.getElementById("LinkedIn-content")?.value || "").trim();
            if (!post) return "LinkedIn channel requires Post Content.";
            continue;
        }

        if (channel === "facebook") {
            const post = String(document.getElementById("Facebook-content")?.value || "").trim();
            if (!post) return "Facebook channel requires Post Content.";
            continue;
        }

        if (channel === "twitter") {
            const tweet = String(document.getElementById("Twitter-content")?.value || "").trim();
            if (!tweet) return "Twitter channel requires Tweet Content.";
            if (tweet.length > 280) return "Twitter content must be 280 characters or fewer.";
            continue;
        }

        if (channel === "whatsapp") {
            const message = String(document.getElementById("WhatsApp-content")?.value || "").trim();
            if (!message) return "WhatsApp channel requires Message content.";
            continue;
        }

        // Fallback for unknown/custom channels (backward compatible)
        const fallbackContentEl = document.getElementById(`${channel}-content`);
        const fallbackContent = String(fallbackContentEl?.value || "").trim();
        if (!fallbackContent) {
            const label = channel.charAt(0).toUpperCase() + channel.slice(1);
            return `${label} channel requires Message content.`;
        }
    }

    return null;
}

async function createCampaign() {
    const campaignName = document.getElementById('campaignName');
    const campaignObjective = document.getElementById('campaignObjective');
    const audienceSource = document.getElementById('audienceSource');
    const strategySelect = document.getElementById('campaignStrategy');
    const strategyVersionSelect = document.getElementById('campaignStrategyVersion');
    const strategyWarning = document.getElementById('campaignStrategyWarning');
    const createCampaignBtn = document.getElementById('createCampaignBtn');
    const launchDate = document.getElementById('launchDate');
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');
    
    if (!campaignName || !campaignObjective) return;
    if (isCreateCampaignInFlight) return;
    
    const selectedChannels = Array.from(
        document.querySelectorAll('.wizard-step[data-step="2"] input[type="checkbox"]:checked')
    ).map(cb => cb.value);
    
    if (!campaignName.value || !campaignObjective.value || selectedChannels.length === 0) {
        showErrorMessage('Please fill in all required fields.');
        return;
    }

    isCreateCampaignInFlight = true;
    if (createCampaignBtn) {
        createCampaignBtn.disabled = true;
        createCampaignBtn.textContent = currentEditingCampaignId ? 'Saving...' : 'Creating...';
    }

    try {
        const strategyId = strategySelect?.value || '';
        const strategyVersion = strategyVersionSelect?.value || '';

        if (strategyWarning) {
            strategyWarning.classList.add('hidden');
        }
        if (strategyVersion && !strategyId) {
            if (strategyWarning) {
                strategyWarning.classList.remove('hidden');
            } else {
                showErrorMessage('Please select a strategy before choosing a version.');
            }
            return;
        }

        const validationError = validateSelectedChannelContent(selectedChannels);
        if (validationError) {
            showErrorMessage(validationError);
            return;
        }

        const contentSchema = {};
        selectedChannels.forEach((channel) => {
            const channelKey = String(channel || '').trim().toLowerCase();
            const contentEl = document.getElementById(`${channel}-content`);
            const subjectEl = document.getElementById(`${channel}-subject`);
            const textValue = String(contentEl?.value || '').trim();
            const subjectValue = String(subjectEl?.value || '').trim();

            if (channelKey === 'email') {
                contentSchema.email = {
                    subject: subjectValue,
                    body: textValue,
                };
                return;
            }
            if (channelKey === 'linkedin') {
                contentSchema.linkedin = { post: textValue };
                return;
            }
            if (channelKey === 'facebook') {
                contentSchema.facebook = { post: textValue };
                return;
            }
            if (channelKey === 'twitter') {
                contentSchema.twitter = { tweet: textValue };
                return;
            }
            if (channelKey === 'whatsapp') {
                contentSchema.whatsapp = { message: textValue };
                return;
            }
            contentSchema[channelKey] = { message: textValue };
        });

        const payload = {
            campaign_name: campaignName.value,
            channels: selectedChannels,
            target_audience: campaignObjective.value,
            audience_source: audienceSource?.value || 'scraped_leads',
            content: JSON.stringify(contentSchema),
            schedule_date: launchDate?.value ? new Date(launchDate.value).toISOString() : null,
            start_date: startDate?.value ? new Date(startDate.value).toISOString() : null,
            end_date: endDate?.value ? new Date(endDate.value).toISOString() : null,
            budget: null
        };
        if (strategyId) {
            payload.strategy_id = strategyId;
        }
        if (strategyVersion && strategyId) {
            payload.strategy_version_no = parseInt(strategyVersion, 10);
        }

        const isEditing = !!currentEditingCampaignId;
        if (isEditing) {
            const updatePayload = {
                campaign_name: payload.campaign_name,
                channels: payload.channels,
                target_audience: payload.target_audience,
                content: payload.content,
                schedule_date: payload.schedule_date,
                start_date: payload.start_date,
                end_date: payload.end_date,
                budget: currentEditingCampaignBudget,
                strategy_id: payload.strategy_id || null,
                strategy_version_no: payload.strategy_version_no || null
            };
            console.log('[campaign_debug] updateCampaign payload:', updatePayload);
            await apiRequest(`/api/campaigns/${encodeURIComponent(currentEditingCampaignId)}`, 'PUT', updatePayload);
        } else {
            const idempotencyKey = `campaign-create-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
            console.log('[campaign_debug] createCampaign payload:', payload);
            await apiRequestWithOptions('/api/campaigns/create', {
                method: 'POST',
                headers: {
                    'Idempotency-Key': idempotencyKey
                },
                body: JSON.stringify(payload)
            });
        }

        const createdCampaignName = campaignName.value;

        nextWizardStep(1);
        const form = document.getElementById('campaignDetailsForm');
        if (form) form.reset();
        if (launchDate) launchDate.value = '';
        if (startDate) startDate.value = '';
        if (endDate) endDate.value = '';
        if (strategySelect) strategySelect.value = '';
        resetCampaignStrategyVersionDropdown();
        resetCampaignEditMode();

        showCampaignTab('active');
        setActiveCampaignTab(document.querySelector('[data-tab="active"]'));
        await loadCampaigns();

        showSuccessMessage(isEditing
            ? `Campaign "${createdCampaignName}" updated successfully!`
            : `Campaign "${createdCampaignName}" created successfully!`);
    } catch (error) {
        console.error('Campaign creation error:', error);
        showErrorMessage(error.message || 'Failed to create campaign.');
    } finally {
        isCreateCampaignInFlight = false;
        if (createCampaignBtn) {
            createCampaignBtn.disabled = false;
            createCampaignBtn.textContent = currentEditingCampaignId ? 'Save Campaign' : 'Create Campaign';
        }
    }
}

function resetCampaignEditMode() {
    currentEditingCampaignId = null;
    currentEditingCampaignBudget = null;
    const createCampaignBtn = document.getElementById('createCampaignBtn');
    if (createCampaignBtn) {
        createCampaignBtn.textContent = 'Create Campaign';
    }
}

function toDateTimeLocalValue(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    const tzOffsetMs = date.getTimezoneOffset() * 60000;
    return new Date(date.getTime() - tzOffsetMs).toISOString().slice(0, 16);
}

function parseCampaignContentForEditor(rawContent) {
    const normalized = {
        email: { subject: '', body: '' },
        linkedin: { post: '' },
        facebook: { post: '' },
        whatsapp: { message: '' },
        twitter: { tweet: '' },
    };

    const applyLegacyEntry = (entry = {}) => {
        const channel = String(entry.channel || '').trim().toLowerCase();
        if (!channel) return;
        const subject = String(entry.subject || '').trim();
        const content = String(entry.content || entry.body || entry.message || '').trim();
        if (channel === 'email') {
            normalized.email.subject = subject;
            normalized.email.body = content;
            return;
        }
        if (channel === 'linkedin' || channel === 'facebook' || channel === 'twitter') {
            if (channel === 'twitter') {
                normalized.twitter.tweet = content;
            } else {
                normalized[channel].post = content;
            }
            return;
        }
        if (channel === 'whatsapp') {
            normalized.whatsapp.message = content;
        }
    };

    let parsed = rawContent;
    if (typeof rawContent === 'string') {
        const text = rawContent.trim();
        if (!text) return normalized;
        try {
            parsed = JSON.parse(text);
        } catch {
            normalized.email.body = text;
            return normalized;
        }
    }

    if (Array.isArray(parsed)) {
        parsed.forEach((entry) => {
            if (entry && typeof entry === 'object') {
                applyLegacyEntry(entry);
            }
        });
        return normalized;
    }

    if (parsed && typeof parsed === 'object') {
        const email = parsed.email;
        if (email && typeof email === 'object') {
            normalized.email.subject = String(email.subject || '').trim();
            normalized.email.body = String(email.body || email.content || '').trim();
        }
        const linkedin = parsed.linkedin;
        if (linkedin && typeof linkedin === 'object') {
            normalized.linkedin.post = String(linkedin.post || linkedin.content || '').trim();
        }
        const facebook = parsed.facebook;
        if (facebook && typeof facebook === 'object') {
            normalized.facebook.post = String(facebook.post || facebook.content || '').trim();
        }
        const whatsapp = parsed.whatsapp;
        if (whatsapp && typeof whatsapp === 'object') {
            normalized.whatsapp.message = String(whatsapp.message || whatsapp.content || '').trim();
        }
        const twitter = parsed.twitter;
        if (twitter && typeof twitter === 'object') {
            normalized.twitter.tweet = String(twitter.tweet || twitter.post || twitter.content || '').trim();
        }

        const legacyEntries = parsed.legacy_channels;
        if (Array.isArray(legacyEntries)) {
            legacyEntries.forEach((entry) => {
                if (entry && typeof entry === 'object') {
                    applyLegacyEntry(entry);
                }
            });
        }
    }

    return normalized;
}

function setSelectValueAllowCustom(selectEl, value, fallbackLabel = 'Custom') {
    if (!selectEl) return;
    const normalized = String(value || '').trim();
    if (!normalized) {
        selectEl.value = '';
        syncEnhancedSelectUI(selectEl);
        return;
    }
    const existing = Array.from(selectEl.options).find((opt) => String(opt.value) === normalized);
    if (!existing) {
        const option = document.createElement('option');
        option.value = normalized;
        option.textContent = fallbackLabel ? `${fallbackLabel}: ${normalized}` : normalized;
        selectEl.appendChild(option);
    }
    selectEl.value = normalized;
    syncEnhancedSelectUI(selectEl);
}

async function startCampaignEditFlow(campaignId) {
    const response = await apiRequest(`/api/campaigns/${encodeURIComponent(campaignId)}`);
    const campaign = response?.campaign;
    if (!campaign || typeof campaign !== 'object') {
        throw new Error('Campaign details could not be loaded.');
    }

    currentEditingCampaignId = String(campaign.campaign_id || campaign.id || campaignId);
    currentEditingCampaignBudget = (campaign.budget !== null && campaign.budget !== undefined)
        ? Number(campaign.budget)
        : null;

    const createCampaignBtn = document.getElementById('createCampaignBtn');
    if (createCampaignBtn) {
        createCampaignBtn.textContent = 'Save Campaign';
    }

    showCampaignTab('create');
    setActiveCampaignTab(document.querySelector('[data-tab="create"]'));
    nextWizardStep(1);

    const campaignName = document.getElementById('campaignName');
    const campaignObjective = document.getElementById('campaignObjective');
    const audienceSource = document.getElementById('audienceSource');
    const strategySelect = document.getElementById('campaignStrategy');
    const strategyVersionSelect = document.getElementById('campaignStrategyVersion');
    const launchDate = document.getElementById('launchDate');
    const startDate = document.getElementById('startDate');
    const endDate = document.getElementById('endDate');

    if (campaignName) campaignName.value = campaign.campaign_name || campaign.name || '';
    if (campaignObjective) {
        const objective = campaign.objective || campaign.target_audience || '';
        setSelectValueAllowCustom(campaignObjective, objective, 'Audience');
    }
    if (audienceSource) {
        audienceSource.value = campaign.audience_source || 'scraped_leads';
    }

    if (strategySelect) {
        setSelectValueAllowCustom(strategySelect, campaign.strategy_id || '', 'Strategy');
    }

    if (strategySelect && campaign.strategy_id) {
        await handleCampaignStrategyChange({ target: { value: strategySelect.value } });
        if (strategyVersionSelect && campaign.strategy_version_no !== null && campaign.strategy_version_no !== undefined) {
            setSelectValueAllowCustom(strategyVersionSelect, String(campaign.strategy_version_no), 'Version');
        }
    } else {
        resetCampaignStrategyVersionDropdown();
    }

    if (launchDate) launchDate.value = toDateTimeLocalValue(campaign.schedule_date);
    if (startDate) startDate.value = toDateTimeLocalValue(campaign.start_date);
    if (endDate) endDate.value = toDateTimeLocalValue(campaign.end_date);

    const selectedChannels = Array.isArray(campaign.channels) ? campaign.channels : [];
    const selectedChannelSet = new Set(selectedChannels.map((channel) => String(channel || '').trim().toLowerCase()));
    document.querySelectorAll('.wizard-step[data-step="2"] input[type="checkbox"]').forEach((checkbox) => {
        checkbox.checked = selectedChannelSet.has(String(checkbox.value || '').trim().toLowerCase());
    });

    generateContentForms();
    const contentMap = parseCampaignContentForEditor(campaign.content);
    const checkedChannels = Array.from(
        document.querySelectorAll('.wizard-step[data-step="2"] input[type="checkbox"]:checked')
    ).map((cb) => cb.value);
    checkedChannels.forEach((channel) => {
        const key = String(channel || '').trim().toLowerCase();
        const subjectEl = document.getElementById(`${channel}-subject`);
        const contentEl = document.getElementById(`${channel}-content`);
        if (!contentEl) return;

        if (key === 'email') {
            if (subjectEl) subjectEl.value = contentMap.email.subject || '';
            contentEl.value = contentMap.email.body || '';
            return;
        }
        if (key === 'linkedin') {
            contentEl.value = contentMap.linkedin.post || '';
            return;
        }
        if (key === 'facebook') {
            contentEl.value = contentMap.facebook.post || '';
            return;
        }
        if (key === 'whatsapp') {
            contentEl.value = contentMap.whatsapp.message || '';
            return;
        }
        if (key === 'twitter') {
            contentEl.value = contentMap.twitter.tweet || '';
        }
    });
}

function displayActiveCampaigns() {
    const campaignsGrid = document.getElementById('campaignsGrid');
    if (!campaignsGrid) return;
    
    if (appData.campaigns.length === 0) {
        campaignsGrid.innerHTML = `
            <div class="text-center">
                <p>No active campaigns. Create your first campaign to get started!</p>
            </div>
        `;
        return;
    }

    const formatValue = (value) => {
        if (value === null || value === undefined || value === '') return 'N/A';
        if (Array.isArray(value)) return value.join(', ') || 'N/A';
        if (typeof value === 'object') return JSON.stringify(value);
        return String(value);
    };

    const escapeAttr = (value) => String(value)
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    const parseContent = (rawContent) => {
        if (!rawContent) return [];
        if (Array.isArray(rawContent)) return rawContent;
        if (typeof rawContent === 'string') {
            try {
                const parsed = JSON.parse(rawContent);
                if (Array.isArray(parsed)) return parsed;
                if (parsed && typeof parsed === 'object') {
                    return Object.entries(parsed).map(([channel, payload]) => ({ channel, payload }));
                }
                return [{ content: rawContent }];
            } catch {
                return [{ content: rawContent }];
            }
        }
        if (typeof rawContent === 'object') {
            return Object.entries(rawContent).map(([channel, payload]) => ({ channel, payload }));
        }
        return [];
    };

    const renderCampaignContent = (rawContent) => {
        const safeText = (value) => {
            if (value === null || value === undefined) return '';
            return String(value).trim();
        };

        let parsed = rawContent;
        if (typeof rawContent === 'string') {
            const trimmed = rawContent.trim();
            if (!trimmed) return '';
            try {
                parsed = JSON.parse(trimmed);
            } catch {
                return `
                    <div class="campaign-content-block">
                        <div class="campaign-content-line"><strong>Message:</strong> ${formatValue(trimmed)}</div>
                    </div>
                `;
            }
        }

        if (Array.isArray(parsed)) {
            return parsed.map((item) => {
                if (!item || typeof item !== 'object') {
                    return `
                        <div class="campaign-content-block">
                            <div class="campaign-content-line"><strong>Message:</strong> ${formatValue(item)}</div>
                        </div>
                    `;
                }
                return `
                    <div class="campaign-content-block">
                        ${item.channel ? `<div class="campaign-content-line"><strong>Channel:</strong> ${formatValue(item.channel)}</div>` : ''}
                        ${item.subject ? `<div class="campaign-content-line"><strong>Subject:</strong> ${formatValue(item.subject)}</div>` : ''}
                        ${item.content ? `<div class="campaign-content-line"><strong>Message:</strong> ${formatValue(item.content)}</div>` : ''}
                    </div>
                `;
            }).join('');
        }

        if (parsed && typeof parsed === 'object') {
            const sections = [];
            const email = parsed.email && typeof parsed.email === 'object' ? parsed.email : null;
            const linkedin = parsed.linkedin && typeof parsed.linkedin === 'object' ? parsed.linkedin : null;
            const facebook = parsed.facebook && typeof parsed.facebook === 'object' ? parsed.facebook : null;
            const twitter = parsed.twitter && typeof parsed.twitter === 'object' ? parsed.twitter : null;
            const whatsapp = parsed.whatsapp && typeof parsed.whatsapp === 'object' ? parsed.whatsapp : null;

            if (email && (safeText(email.subject) || safeText(email.body) || safeText(email.content))) {
                sections.push(`<div class="campaign-content-block"><div class="campaign-content-title">Email</div>${safeText(email.subject) ? `<div class="campaign-content-line"><strong>Subject:</strong> ${formatValue(email.subject)}</div>` : ''}${safeText(email.body || email.content) ? `<div class="campaign-content-line"><strong>Body:</strong> ${formatValue(email.body || email.content)}</div>` : ''}</div>`);
            }
            if (linkedin && safeText(linkedin.post || linkedin.content || linkedin.message)) {
                sections.push(`<div class="campaign-content-block"><div class="campaign-content-title">LinkedIn</div><div class="campaign-content-line"><strong>Post:</strong> ${formatValue(linkedin.post || linkedin.content || linkedin.message)}</div></div>`);
            }
            if (facebook && safeText(facebook.post || facebook.content || facebook.message)) {
                sections.push(`<div class="campaign-content-block"><div class="campaign-content-title">Facebook</div><div class="campaign-content-line"><strong>Post:</strong> ${formatValue(facebook.post || facebook.content || facebook.message)}</div></div>`);
            }
            if (twitter && safeText(twitter.tweet || twitter.post || twitter.content || twitter.message)) {
                sections.push(`<div class="campaign-content-block"><div class="campaign-content-title">Twitter</div><div class="campaign-content-line"><strong>Tweet:</strong> ${formatValue(twitter.tweet || twitter.post || twitter.content || twitter.message)}</div></div>`);
            }
            if (whatsapp && safeText(whatsapp.message || whatsapp.content || whatsapp.post)) {
                sections.push(`<div class="campaign-content-block"><div class="campaign-content-title">WhatsApp</div><div class="campaign-content-line"><strong>Message:</strong> ${formatValue(whatsapp.message || whatsapp.content || whatsapp.post)}</div></div>`);
            }

            if (sections.length > 0) return sections.join('');

            return `
                <div class="campaign-content-block">
                    <div class="campaign-content-line"><strong>Message:</strong> ${formatValue(parsed)}</div>
                </div>
            `;
        }

        return '';
    };

    const getStatusMeta = (statusValue) => {
        const normalized = String(statusValue || 'unknown').toLowerCase();
        const map = {
            draft: 'status--draft',
            scheduled: 'status--scheduled',
            active: 'status--active',
            paused: 'status--paused',
            stopped: 'status--stopped',
            failed: 'status--error',
            completed: 'status--success',
        };
        return {
            normalized,
            className: map[normalized] || 'status--info',
            label: normalized ? normalized.charAt(0).toUpperCase() + normalized.slice(1) : 'Unknown',
        };
    };

    const buildActionButtons = (campaignId, status) => {
        const buttons = [
            `<button class="btn btn--sm btn--secondary action-btn" data-action="edit" data-id="${escapeAttr(String(campaignId))}">Edit</button>`
        ];
        if (status === 'draft') {
            buttons.push(`<button class="btn btn--sm btn--outline action-btn" data-action="schedule" data-id="${escapeAttr(String(campaignId))}">Schedule</button>`);
        }
        if (status === 'draft' || status === 'scheduled') {
            buttons.push(`<button class="btn btn--sm btn--primary action-btn" data-action="launch" data-id="${escapeAttr(String(campaignId))}">Launch</button>`);
        }
        if (status === 'active' || status === 'scheduled') {
            buttons.push(`<button class="btn btn--sm btn--outline action-btn" data-action="pause" data-id="${escapeAttr(String(campaignId))}">Pause</button>`);
        }
        if (status === 'paused' || status === 'stopped') {
            buttons.push(`<button class="btn btn--sm btn--outline action-btn" data-action="resume" data-id="${escapeAttr(String(campaignId))}">Resume</button>`);
        }
        if (['draft', 'scheduled', 'active', 'paused'].includes(status)) {
            buttons.push(`<button class="btn btn--sm btn--outline action-btn" data-action="stop" data-id="${escapeAttr(String(campaignId))}">Stop</button>`);
        }
        buttons.push(`<button class="btn btn--sm btn--outline action-btn" data-action="delete" data-id="${escapeAttr(String(campaignId))}">Delete</button>`);
        return buttons.join('');
    };
    
    campaignsGrid.innerHTML = appData.campaigns.map(campaign => {
        const campaignId = campaign.id || campaign.campaign_id || Date.now();
        const channels = Array.isArray(campaign.channels) ? campaign.channels : [];
        const statusMeta = getStatusMeta(campaign.status);
        const scheduleDate = campaign.schedule_date ? formatValue(campaign.schedule_date) : 'Not scheduled';
        const startDate = campaign.start_date ? formatValue(campaign.start_date) : 'Not set';
        const endDate = campaign.end_date ? formatValue(campaign.end_date) : 'Not set';
        const budget = campaign.budget !== null && campaign.budget !== undefined ? formatValue(campaign.budget) : 'Not set';
        const metrics = campaign.metrics || { sent: 0, opened: 0, clicked: 0, converted: 0 };

        const extraFields = Object.entries(campaign)
            .filter(([k]) => ![
                'id', 'campaign_id', 'name', 'campaign_name', 'objective', 'target_audience',
                'channels', 'status', 'created', 'metrics', 'content', 'schedule_date', 'start_date', 'end_date', 'budget'
            ].includes(k))
            .map(([k, v]) => `<div><strong>${k}:</strong> ${formatValue(v)}</div>`)
            .join('');

        return `
        <div class="campaign-card">
            <div class="campaign-card__header">
                <h3 class="campaign-card__title">${campaign.name || campaign.campaign_name || 'Untitled Campaign'}</h3>
                <div class="campaign-card__status">
                    <span class="status ${statusMeta.className}">${statusMeta.label}</span>
                </div>
            </div>
            <div class="campaign-card__body">
                <div style="margin-bottom:12px;">
                    <div><strong>Objective:</strong> ${campaign.objective || campaign.target_audience || 'N/A'}</div>
                    <div><strong>Channels:</strong> ${channels.length ? channels.map(ch => `<span class="status status--info">${ch}</span>`).join(' ') : 'N/A'}</div>
                    <div><strong>Schedule Date:</strong> ${scheduleDate}</div>
                    <div><strong>Start Date:</strong> ${startDate}</div>
                    <div><strong>End Date:</strong> ${endDate}</div>
                    <div><strong>Budget:</strong> ${budget}</div>
                </div>

                ${campaign.content ? `
                    <div style="margin-bottom:12px;">
                        <strong>Content:</strong>
                        <div class="campaign-content-grid">
                            ${renderCampaignContent(campaign.content)}
                        </div>
                    </div>
                ` : ''}

                ${extraFields ? `<div style="margin-bottom:12px;">${extraFields}</div>` : ''}

                <div class="campaign-card__metrics">
                    <div class="campaign-metric">
                        <div class="campaign-metric__value">${metrics.sent ?? 0}</div>
                        <div class="campaign-metric__label">Sent</div>
                    </div>
                    <div class="campaign-metric">
                        <div class="campaign-metric__value">${metrics.opened ?? 0}</div>
                        <div class="campaign-metric__label">Opened</div>
                    </div>
                    <div class="campaign-metric">
                        <div class="campaign-metric__value">${metrics.clicked ?? 0}</div>
                        <div class="campaign-metric__label">Clicked</div>
                    </div>
                    <div class="campaign-metric">
                        <div class="campaign-metric__value">${metrics.converted ?? 0}</div>
                        <div class="campaign-metric__label">Converted</div>
                    </div>
                </div>
                <div class="campaign-card__actions">
                    ${buildActionButtons(campaignId, statusMeta.normalized)}
                </div>
            </div>
        </div>
        `;
    }).join('');

    campaignsGrid.querySelectorAll('.action-btn').forEach(button => {
        button.addEventListener('click', async () => {
            const action = button.dataset.action;
            const campaignId = button.dataset.id;
            if (!campaignId || !action) return;

            if (action === 'edit') return editCampaign(campaignId);
            if (action === 'pause') return pauseCampaign(campaignId);
            if (action === 'resume') return resumeCampaign(campaignId);
            if (action === 'stop') return stopCampaign(campaignId);
            if (action === 'launch') return launchCampaign(campaignId);
            if (action === 'schedule') return scheduleCampaign(campaignId);
            if (action === 'delete') return deleteCampaign(campaignId);
        });
    });
}

async function editCampaign(campaignId) {
    try {
        await startCampaignEditFlow(campaignId);
        showSuccessMessage('Campaign loaded. Review and save your changes.');
    } catch (error) {
        console.error('Campaign update error:', error);
        showErrorMessage(error.message || 'Failed to load campaign for editing.');
    }
}

async function pauseCampaign(campaignId) {
    try {
        let response;
        try {
            response = await apiRequest(`/api/campaigns/${encodeURIComponent(campaignId)}/pause`, 'PATCH', {});
        } catch (error) {
            const msg = String(error?.message || '').toLowerCase();
            if (msg.includes('404') || msg.includes('405')) {
                response = await apiRequest(`/api/campaigns/${encodeURIComponent(campaignId)}/pause`, 'POST', {});
            } else {
                throw error;
            }
        }
        await loadCampaigns();

        const newStatus = response?.campaign?.status || 'updated';
        showSuccessMessage(`Campaign ${String(newStatus).toLowerCase()}! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.`);
    } catch (error) {
        console.error('Campaign pause error:', error);
        showErrorMessage(error.message || 'Failed to update campaign status.');
    }
}

async function resumeCampaign(campaignId) {
    try {
        const response = await apiRequest(`/api/campaigns/${encodeURIComponent(campaignId)}/resume`, 'PATCH', {});
        await loadCampaigns();
        showSuccessMessage(response?.message || 'Campaign resumed successfully.');
    } catch (error) {
        console.error('Campaign resume error:', error);
        showErrorMessage(error.message || 'Failed to resume campaign.');
    }
}

async function stopCampaign(campaignId) {
    try {
        const response = await apiRequest(`/api/campaigns/${encodeURIComponent(campaignId)}/stop`, 'PATCH', {});
        await loadCampaigns();
        showSuccessMessage(response?.message || 'Campaign stopped successfully.');
    } catch (error) {
        console.error('Campaign stop error:', error);
        showErrorMessage(error.message || 'Failed to stop campaign.');
    }
}

async function launchCampaign(campaignId) {
    try {
        const response = await apiRequest(`/api/campaigns/${encodeURIComponent(campaignId)}/launch`, 'POST', {});
        await loadCampaigns();
        showSuccessMessage(response?.message || 'Campaign launched successfully.');
    } catch (error) {
        console.error('Campaign launch error:', error);
        showErrorMessage(error.message || 'Failed to launch campaign.');
    }
}

async function scheduleCampaign(campaignId) {
    try {
        const response = await apiRequest(`/api/campaigns/${encodeURIComponent(campaignId)}/schedule`, 'POST', {});
        await loadCampaigns();
        showSuccessMessage(response?.message || 'Campaign scheduled successfully.');
    } catch (error) {
        console.error('Campaign schedule error:', error);
        showErrorMessage(error.message || 'Failed to schedule campaign.');
    }
}

async function deleteCampaign(campaignId) {
    const confirmed = window.confirm('Are you sure you want to delete this campaign?');
    if (!confirmed) return;
    try {
        const response = await apiRequest(`/api/campaigns/${encodeURIComponent(campaignId)}`, 'DELETE');
        if (String(appData.reviewCampaignId || '') === String(campaignId)) {
            appData.reviewCampaignId = null;
            updateStrategyLaunchButtonState();
            saveDataToStorage();
        }
        await loadCampaigns();
        showSuccessMessage(response?.message || 'Campaign deleted successfully.');
    } catch (error) {
        console.error('Campaign delete error:', error);
        showErrorMessage(error.message || 'Failed to delete campaign.');
    }
}

// Analytics Functions
function updateAnalyticsDashboard(analyticsData) {
    const viewModel = analyticsData || { ...DEFAULT_ANALYTICS_VIEW_MODEL };

    // Update metric cards
    const totalLeadsEl = document.getElementById('totalLeadsMetric');
    const activeCampaignsEl = document.getElementById('activeCampaignsMetric');
    const conversionRateEl = document.getElementById('conversionRateMetric');
    const roiEl = document.getElementById('roiMetric');

    if (totalLeadsEl) totalLeadsEl.textContent = Number(viewModel.totalLeads || 0).toLocaleString();
    if (activeCampaignsEl) activeCampaignsEl.textContent = Number(viewModel.activeCampaigns || 0);
    if (conversionRateEl) conversionRateEl.textContent = `${Number(viewModel.conversionRate || 0)}%`;
    if (roiEl) roiEl.textContent = `${Number(viewModel.roi || 0).toFixed(2)}%`;

    // Create charts with delay
    setTimeout(() => {
        createPerformanceChart(viewModel);
        createFunnelChart(viewModel);
    }, 100);
}

function createPerformanceChart(analyticsData) {
    const ctx = document.getElementById('performanceChart');
    if (!ctx) return;

    const viewModel = analyticsData || { ...DEFAULT_ANALYTICS_VIEW_MODEL };
    const labels = Array.isArray(viewModel.monthlyMetrics) ? viewModel.monthlyMetrics.map(m => m.month) : [];
    const primaryData = Array.isArray(viewModel.monthlyMetrics) ? viewModel.monthlyMetrics.map(m => m.leads) : [];
    const secondaryData = Array.isArray(viewModel.monthlyMetrics) ? viewModel.monthlyMetrics.map(m => m.conversions) : [];
    const isStrategyMode = analyticsMode === 'strategy_performance';
    const desiredType = isStrategyMode ? 'bar' : 'line';

    try {
        if (ctx.chart && performanceChartMode !== analyticsMode) {
            ctx.chart.destroy();
            ctx.chart = null;
        }

        if (ctx.chart) {
            ctx.chart.data.labels = labels;
            ctx.chart.data.datasets[0].data = primaryData;
            if (!isStrategyMode && ctx.chart.data.datasets[1]) {
                ctx.chart.data.datasets[1].data = secondaryData;
            }
            ctx.chart.update();
            return;
        }

        ctx.chart = new Chart(ctx, {
            type: desiredType,
            data: {
                labels,
                datasets: isStrategyMode
                    ? [{
                        label: 'Average ROI (%)',
                        data: primaryData,
                        borderColor: '#1FB8CD',
                        backgroundColor: 'rgba(31, 184, 205, 0.35)',
                        borderWidth: 1,
                    }]
                    : [{
                        label: 'Leads Generated',
                        data: primaryData,
                        borderColor: '#1FB8CD',
                        backgroundColor: 'rgba(31, 184, 205, 0.1)',
                        tension: 0.4,
                        fill: true
                    }, {
                        label: 'Conversions',
                        data: secondaryData,
                        borderColor: '#FFC185',
                        backgroundColor: 'rgba(255, 193, 133, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: isStrategyMode ? {
                        callbacks: {
                            label: function(context) {
                                const idx = context.dataIndex;
                                const info = strategyVersionMetrics[idx] || {};
                                const roi = Number(info.avg_roi || 0).toFixed(2);
                                const campaigns = Number(info.campaign_count || 0);
                                return [`Avg ROI: ${roi}%`, `Campaigns: ${campaigns}`];
                            }
                        }
                    } : undefined
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        performanceChartMode = analyticsMode;
    } catch (error) {
        console.error('Error creating performance chart:', error);
    }
}

function createFunnelChart(analyticsData) {
    const ctx = document.getElementById('funnelChart');
    if (!ctx) return;

    const viewModel = analyticsData || { ...DEFAULT_ANALYTICS_VIEW_MODEL };
    const funnelData = Array.isArray(viewModel.funnelData) ? viewModel.funnelData : [0, 0, 0, 0];

    try {
        if (ctx.chart) {
            ctx.chart.data.datasets[0].data = funnelData;
            ctx.chart.update();
            return;
        }

        ctx.chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Leads', 'Qualified', 'Opportunities', 'Closed'],
                datasets: [{
                    data: funnelData,
                    backgroundColor: ['#1FB8CD', '#FFC185', '#B4413C', '#5D878F'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error creating funnel chart:', error);
    }
}

// Template Library Functions
function populateTemplateLibrary() {
    filterTemplates();
}

function filterTemplates() {
    const categoryFilter = document.getElementById('templateCategory');
    const industryFilter = document.getElementById('templateIndustry');
    
    let filteredTemplates = appData.templates;
    
    if (categoryFilter && categoryFilter.value) {
        filteredTemplates = filteredTemplates.filter(t => t.category === categoryFilter.value);
    }
    
    if (industryFilter && industryFilter.value) {
        filteredTemplates = filteredTemplates.filter(t => t.industry === industryFilter.value);
    }
    
    displayTemplates(filteredTemplates);
}

function displayTemplates(templates) {
    const templatesGrid = document.getElementById('templatesGrid');
    if (!templatesGrid) return;
    
    if (templates.length === 0) {
        templatesGrid.innerHTML = '<div class="text-center"><p>No templates found matching your criteria.</p></div>';
        return;
    }
    
    templatesGrid.innerHTML = templates.map(template => `
        <div class="template-card" onclick="showTemplateModal(${template.id})">
            <div class="template-card__header">
                <h3 class="template-card__title">${template.name}</h3>
                <div class="template-card__meta">
                    <span class="status status--info">${template.category}</span>
                    <span class="status status--success">${template.industry}</span>
                </div>
            </div>
            <div class="template-card__body">
                <div class="template-card__preview">
                    ${template.content.substring(0, 150)}...
                </div>
            </div>
        </div>
    `).join('');
}

function showTemplateModal(templateId) {
    const template = appData.templates.find(t => t.id === templateId);
    if (!template) return;
    
    const modalTitle = document.getElementById('modalTemplateTitle');
    const modalContent = document.getElementById('modalTemplateContent');
    const useBtn = document.getElementById('useTemplateBtn');
    const modal = document.getElementById('templateModal');
    
    if (modalTitle) modalTitle.textContent = template.name;
    if (modalContent) {
        modalContent.innerHTML = `
            <div class="template-preview">
                <div class="template-meta mb-16">
                    <span class="status status--info">${template.category}</span>
                    <span class="status status--success">${template.industry}</span>
                </div>
                <div class="template-content">
                    <pre style="white-space: pre-wrap; font-family: inherit;">${template.content}</pre>
                </div>
            </div>
        `;
    }
    
    if (useBtn) {
        useBtn.onclick = () => {
            useTemplate(template);
        };
    }
    
    if (modal) modal.classList.remove('hidden');
}

function useTemplate(template) {
    // Copy template content to clipboard
    navigator.clipboard.writeText(template.content).then(() => {
        closeModal();
        showSuccessMessage(`Template "${template.name}" copied to clipboard! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.`);
    }).catch(() => {
        showSuccessMessage(`Template "${template.name}" ready to use! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.`);
        closeModal();
    });
}

function closeModal() {
    const modal = document.getElementById('templateModal');
    if (modal) modal.classList.add('hidden');
}

// Data Persistence Functions
function saveDataToStorage() {
    try {
        const dataToSave = {
            businessProfile: appData.businessProfile,
            generatedStrategy: appData.generatedStrategy,
            currentStrategyId: appData.currentStrategyId,
            reviewCampaignId: appData.reviewCampaignId,
            scrapedLeads: appData.scrapedLeads,
            enrichedData: appData.enrichedData,
            campaigns: appData.campaigns,
            lastSaved: new Date().toISOString()
        };
        localStorage.setItem('maiAppData', JSON.stringify(dataToSave));
    } catch (error) {
        console.warn('Could not save data to localStorage:', error);
    }
}

function loadDataFromStorage() {
    try {
        const savedData = localStorage.getItem('maiAppData');
        if (savedData) {
            const parsedData = JSON.parse(savedData);
            
            if (parsedData.businessProfile) {
                const savedProfile = parsedData.businessProfile;
                appData.businessProfile = {
                    ...savedProfile,
                    continent: savedProfile.continent || '',
                    country: savedProfile.country || '',
                    region: savedProfile.region || '',
                    websiteLink: savedProfile.websiteLink || ''
                };
                const continentSelect = document.getElementById('continent');
                if (continentSelect && appData.businessProfile.continent) {
                    continentSelect.value = appData.businessProfile.continent;
                }
                const industrySelect = document.getElementById('industry');
                if (industrySelect && appData.businessProfile.industry) {
                    industrySelect.value = appData.businessProfile.industry;
                }
                const businessTypeSelect = document.getElementById('businessType');
                if (businessTypeSelect && appData.businessProfile.industry) {
                    businessTypeSelect.value = appData.businessProfile.industry;
                }
                populateCountryDropdown(appData.businessProfile.continent, appData.businessProfile.country);
                const regionInput = document.getElementById('region');
                if (regionInput) {
                    regionInput.value = appData.businessProfile.region || '';
                }
                displayProfileSummary(appData.businessProfile);
            }
            
            if (parsedData.generatedStrategy) {
                appData.generatedStrategy = parsedData.generatedStrategy;
            }

            if (typeof parsedData.currentStrategyId === 'string' && parsedData.currentStrategyId.trim()) {
                appData.currentStrategyId = parsedData.currentStrategyId.trim();
            }

            if (typeof parsedData.reviewCampaignId === 'string' && parsedData.reviewCampaignId.trim()) {
                appData.reviewCampaignId = parsedData.reviewCampaignId.trim();
            }
            
            if (parsedData.scrapedLeads) {
                appData.scrapedLeads = parsedData.scrapedLeads;
            }
            
            if (parsedData.campaigns) {
                appData.campaigns = parsedData.campaigns;
            }
        }
    } catch (error) {
        console.warn('Could not load data from localStorage:', error);
    }
    if (appData.businessProfile) {
        renderBusinessProfileSummary(appData.businessProfile, { showEmptyState: true });
    } else {
        updateBusinessProfilePreview();
    }
    updateStrategyLaunchButtonState();
    updateProfileCTAState();
}

function exportApplicationData() {
    const exportData = {
        businessProfile: appData.businessProfile,
        generatedStrategy: appData.generatedStrategy,
        currentStrategyId: appData.currentStrategyId,
        reviewCampaignId: appData.reviewCampaignId,
        scrapedLeads: appData.scrapedLeads,
        campaigns: appData.campaigns,
        exportDate: new Date().toISOString(),
        attribution: "Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd."
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mai_app_data.json';
    a.click();
    window.URL.revokeObjectURL(url);
    
    showSuccessMessage('Application data exported successfully! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
}

// Utility Functions are provided by toast.js

// Global functions for inline onclick handlers
window.nextWizardStep = nextWizardStep;
window.editCampaign = editCampaign;
window.pauseCampaign = pauseCampaign;
window.resumeCampaign = resumeCampaign;
window.stopCampaign = stopCampaign;
window.launchCampaign = launchCampaign;
window.scheduleCampaign = scheduleCampaign;
window.deleteCampaign = deleteCampaign;
window.showTemplateModal = showTemplateModal;
window.closeModal = closeModal;
