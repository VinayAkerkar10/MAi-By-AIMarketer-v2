// Global data storage
let appData = {
    currentUserRole: null,
    businessProfile: null,
    generatedStrategy: null,
    currentStrategyId: null,
    adminApiKeys: [],
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
let leadLocationState = {
    text: "",
    lat: null,
    lng: null,
    place_id: null,
};
let adminApiKeysLoaded = false;

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
        }

        if (strategyOptions.length > 0) {
            if (!selectedStrategyId || !strategyOptions.some((opt) => opt.id === selectedStrategyId)) {
                selectedStrategyId = strategyOptions[0].id;
            }
            if (strategySelect) strategySelect.value = selectedStrategyId;
        } else {
            selectedStrategyId = "";
            if (analyticsMode === "strategy_performance") {
                analyticsMode = "campaign_summary";
                const modeSelect = document.getElementById('analyticsModeSelect');
                if (modeSelect) modeSelect.value = analyticsMode;
            }
        }
    } catch (error) {
        console.error('Strategy options loading error:', error);
        strategyOptions = [];
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
    }
    if (strategyWrapper) {
        strategyWrapper.style.display = analyticsMode === 'strategy_performance' ? '' : 'none';
    }
    if (strategySelect && selectedStrategyId) {
        strategySelect.value = selectedStrategyId;
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
    try {
        const response = await apiRequest('/api/strategy/master/continents');
        const rows = Array.isArray(response?.continents) ? response.continents : [];
        continentMasterOptions = rows
            .map((row) => ({
                id: row?.id,
                name: String(row?.name || '').trim()
            }))
            .filter((row) => row.name.length > 0);
    } catch (error) {
        console.error('Continent master loading error:', error);
        continentMasterOptions = [];
    }
    populateContinentDropdown();
}

async function loadBusinessCategoryMasterData() {
    try {
        const response = await apiRequest('/api/strategy/master/business-categories');
        const rows = Array.isArray(response?.business_categories) ? response.business_categories : [];
        businessCategoryMasterOptions = rows
            .map((row) => String(row?.category_name || '').trim())
            .filter((name) => name.length > 0);
    } catch (error) {
        console.error('Business category master loading error:', error);
        businessCategoryMasterOptions = [];
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
    const select = document.getElementById(selectId);
    if (!select) return;

    const previousValue = String(select.value || '').trim();
    select.innerHTML = `<option value="">${placeholder}</option>`;

    options.forEach((name) => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        select.appendChild(option);
    });

    if (previousValue && options.includes(previousValue)) {
        select.value = previousValue;
    }
}

function populateContinentDropdown() {
    const continentSelect = document.getElementById('continent');
    if (!continentSelect) return;

    const previousValue = continentSelect.value || '';
    continentSelect.innerHTML = '<option value="">Select Continent</option>';

    const options = continentMasterOptions.length
        ? continentMasterOptions.map((row) => row.name)
        : ["Asia", "Africa", "Europe", "MENA", "North America", "South America"];

    options.forEach((name) => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        continentSelect.appendChild(option);
    });

    if (previousValue && options.includes(previousValue)) {
        continentSelect.value = previousValue;
    }
}

function populateCountryDropdown(continentName, selectedCountry = '') {
    const countrySelect = document.getElementById('country');
    if (!countrySelect) return;

    const safeContinent = String(continentName || '').trim();
    const countries = CONTINENT_COUNTRY_MAP[safeContinent] || [];
    countrySelect.innerHTML = '<option value="">Select Country (Optional)</option>';

    countries.forEach((country) => {
        const option = document.createElement('option');
        option.value = country;
        option.textContent = country;
        countrySelect.appendChild(option);
    });

    if (selectedCountry && countries.includes(selectedCountry)) {
        countrySelect.value = selectedCountry;
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
        appData.currentUserRole = role || null;
    } catch (error) {
        console.error('Failed to load current user context:', error);
        appData.currentUserRole = null;
    }
}

function isAdminUser() {
    return appData.currentUserRole === 'admin';
}

function applyAdminVisibility() {
    const adminTab = document.getElementById('adminApiKeysTab');
    const adminModule = document.getElementById('admin-api-keys');
    const canAccessAdmin = isAdminUser();

    if (adminTab) {
        adminTab.classList.toggle('hidden', !canAccessAdmin);
    }
    if (adminModule && !canAccessAdmin) {
        adminModule.classList.add('hidden');
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
            loadAdminApiKeys();
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

    // Modal close functionality
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal__overlay')) {
            closeModal();
        }
    });
}

// Business Profile Functions
function handleBusinessProfileSubmit(e) {
    e.preventDefault();
    console.log('Business profile form submitted');
    
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

    form.classList.remove('hidden');
}

function closeAdminApiKeyForm() {
    const form = document.getElementById('adminApiKeyForm');
    if (form) {
        form.classList.add('hidden');
        form.reset();
    }
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

function displayProfileSummary(profile) {
    const summaryCard = document.getElementById('profileSummary');
    const summaryContent = document.getElementById('profileSummaryContent');
    
    if (!summaryCard || !summaryContent) return;
    
    const summaryHTML = `
        <div class="profile-summary">
            <div class="summary-item" style="margin-bottom: 12px;">
                <strong>Business Name:</strong> ${profile.businessName}
            </div>
            <div class="summary-item" style="margin-bottom: 12px;">
                <strong>Industry:</strong> ${profile.industry}
            </div>
            <div class="summary-item" style="margin-bottom: 12px;">
                <strong>Company Size:</strong> ${profile.companySize}
            </div>
            <div class="summary-item" style="margin-bottom: 12px;">
                <strong>Annual Revenue:</strong> $${profile.revenue.toLocaleString()}
            </div>
            <div class="summary-item" style="margin-bottom: 12px;">
                <strong>Continent:</strong> ${profile.continent || 'N/A'}
            </div>
            <div class="summary-item" style="margin-bottom: 12px;">
                <strong>Country:</strong> ${profile.country || 'N/A'}
            </div>
            <div class="summary-item" style="margin-bottom: 12px;">
                <strong>Region:</strong> ${profile.region || 'N/A'}
            </div>
            <div class="summary-item" style="margin-bottom: 12px;">
                <strong>Marketing Goals:</strong> ${profile.marketingGoals.join(', ')}
            </div>
            <div class="summary-item" style="margin-bottom: 12px;">
                <strong>Budget:</strong> $${profile.budget.toLocaleString()}
            </div>
            <div class="summary-item" style="margin-bottom: 12px;">
                <strong>Target Audience:</strong> ${profile.targetAudience}
            </div>
            <div class="summary-item" style="margin-bottom: 12px;">
                <strong>Website:</strong> ${profile.websiteLink || ''}
            </div>
        </div>
    `;
    
    summaryContent.innerHTML = summaryHTML;
    summaryCard.style.display = 'block';
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
}

async function loadStrategyHistoryOptions() {
    const historySelect = document.getElementById('strategyHistorySelect');
    if (!historySelect) return;

    const requestVersion = ++strategyHistoryRequestVersion;
    historySelect.disabled = true;
    historySelect.innerHTML = '<option value="">Loading strategies...</option>';
    resetStrategyVersionDropdown();

    try {
        const response = await apiRequest('/api/strategy/history');
        if (requestVersion !== strategyHistoryRequestVersion) return;

        const strategies = Array.isArray(response?.strategies) ? response.strategies : [];
        strategyHistoryOptions = strategies;

        if (!strategies.length) {
            historySelect.innerHTML = '<option value="">No saved strategies</option>';
            historySelect.disabled = true;
            appData.currentStrategyId = null;
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

        const optionValues = Array.from(historySelect.options)
            .map((opt) => String(opt.value || '').trim())
            .filter((val) => !!val);

        if (optionValues.length > 0) {
            const preferredId = String(appData.currentStrategyId || '').trim();
            const nextId = optionValues.includes(preferredId) ? preferredId : optionValues[0];
            historySelect.value = nextId;
            appData.currentStrategyId = nextId;
            saveDataToStorage();
        } else {
            appData.currentStrategyId = null;
        }
    } catch (error) {
        if (requestVersion !== strategyHistoryRequestVersion) return;
        console.error('Strategy history loading error:', error);
        historySelect.innerHTML = '<option value="">Failed to load strategies</option>';
        historySelect.disabled = true;
        resetStrategyVersionDropdown('Select version');
    }
}

async function handleStrategyHistoryChange(event) {
    const strategyId = event?.target?.value || '';
    const versionSelect = document.getElementById('strategyVersionSelect');
    if (!versionSelect) return;
    appData.currentStrategyId = strategyId || null;
    saveDataToStorage();

    resetStrategyVersionDropdown('Loading versions...');
    if (!strategyId) {
        resetStrategyVersionDropdown();
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
    } catch (error) {
        if (requestVersion !== strategyHistoryRequestVersion) return;
        console.error('Strategy versions loading error:', error);
        resetStrategyVersionDropdown('Failed to load versions');
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
        setStrategyExecutionStatus(`Campaign created from strategy (ID: ${campaignId}).`);
        showSuccessMessage(response?.message || 'Campaign created from strategy.');
    } catch (error) {
        setStrategyExecutionStatus(error.message || 'Failed to create campaign from strategy.', true);
        showErrorMessage(error.message || 'Failed to create campaign from strategy.');
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
            return `<div class="status status--success" style="margin-bottom: 8px;">${label}: ${leadCount} leads</div>`;
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
    
    const location = getStructuredLocationPayload();
    const businessType = document.getElementById('businessType').value;
    const radius = document.getElementById('radius').value;
    const additionalFilters = document.getElementById('additionalFilters').value;
    const sources = getNormalizedSelectedSources();

    if (!String(location?.text || '').trim()) {
        showErrorMessage('Location is required.');
        return;
    }

    if (sources.length === 0) {
        showErrorMessage('Please select at least one source.');
        return;
    }
    
    const searchParams = {
        location,
        businessType,
        radius,
        additionalFilters,
        sources
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
            business_type: params.businessType,
            radius: Number(params.radius) || 10,
            max_results: 25,
            sources: Array.isArray(params.sources) ? params.sources : ['github']
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
    if (!tbody) return;

    const safeLeads = Array.isArray(leads) ? leads : [];

    const escapeHtml = (value) => String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');

    const titleize = (key) => String(key || '')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());

    const formatValue = (value) => {
        if (value === null || value === undefined || value === '') return 'N/A';
        if (Array.isArray(value)) {
            if (value.length === 0) return 'N/A';
            return value.map(item => formatValue(item)).join('<br>');
        }
        if (typeof value === 'object') {
            const entries = Object.entries(value);
            if (entries.length === 0) return 'N/A';
            return entries
                .map(([k, v]) => `<div><strong>${escapeHtml(titleize(k))}:</strong> ${formatValue(v)}</div>`)
                .join('');
        }
        return escapeHtml(value);
    };

    const getFirstAvailable = (lead, keys, fallback = 'N/A') => {
        for (const key of keys) {
            const val = lead?.[key];
            if (val !== undefined && val !== null && val !== '') return val;
        }
        return fallback;
    };

    const renderWebsite = (value) => {
        if (value === null || value === undefined || value === '') return 'N/A';
        const website = Array.isArray(value) ? value[0] : value;
        if (!website || typeof website !== 'string') return escapeHtml(formatValue(value));
        const href = website.startsWith('http') ? website : `http://${website}`;
        return `<a href="${escapeHtml(href)}" target="_blank">${escapeHtml(website)}</a>`;
    };

    const renderLeadDetails = (lead) => {
        const metadata = (lead && typeof lead.metadata === 'object' && lead.metadata) ? lead.metadata : {};
        const topRepos = Array.isArray(metadata.top_repos) ? metadata.top_repos : [];
        const bio = metadata.bio || 'N/A';
        const followers = metadata.followers ?? 'N/A';
        const publicRepos = metadata.public_repos ?? 'N/A';

        return `
            <div><strong>Followers:</strong> ${escapeHtml(followers)}</div>
            <div><strong>Public Repos:</strong> ${escapeHtml(publicRepos)}</div>
            <div><strong>Top Repos:</strong> ${topRepos.length ? topRepos.map(repo => escapeHtml(repo)).join(', ') : 'N/A'}</div>
            <div><strong>Bio:</strong> ${escapeHtml(bio)}</div>
        `;
    };

    tbody.innerHTML = safeLeads.map((leadRaw, index) => {
        const lead = (leadRaw && typeof leadRaw === 'object') ? leadRaw : {};

        const businessName = getFirstAvailable(lead, ['business_name', 'businessName', 'name', 'login']);
        const address = getFirstAvailable(lead, ['address', 'location', 'formatted_address']);
        const phone = formatValue(getFirstAvailable(lead, ['phone', 'phones', 'contact_numbers']));
        const websiteValue = getFirstAvailable(lead, ['website', 'websites', 'url', 'html_url']);
        const rating = getFirstAvailable(lead, ['rating', 'score', 'stars'], 'N/A');
        const category = getFirstAvailable(lead, ['category', 'business_type', 'type'], 'N/A');
        const source = String(getFirstAvailable(lead, ['source'], 'unknown')).toLowerCase();
        const sourceLabel = titleize(source);
        const sourceClass = source.replace(/[^a-z0-9_-]/g, '');
        const detailsId = `leadDetails_${index}`;

        return `
            <tr>
                <td>
                    <strong>${escapeHtml(businessName)}</strong>
                    <span class="source-badge source-badge--${escapeHtml(sourceClass)}">${escapeHtml(sourceLabel)}</span>
                    <div style="margin-top:6px;">
                        <button type="button" class="btn btn--outline btn--sm lead-details-toggle" data-target="${detailsId}">View Details</button>
                    </div>
                    <div id="${detailsId}" class="lead-details hidden" style="margin-top:6px; font-size:12px;">
                        ${renderLeadDetails(lead)}
                    </div>
                </td>
                <td>${formatValue(address)}</td>
                <td>${phone}</td>
                <td>${renderWebsite(websiteValue)}</td>
                <td>${rating === 'N/A' ? 'N/A' : escapeHtml(rating)}</td>
                <td><span class="status status--info">${escapeHtml(category)}</span></td>
            </tr>
        `;
    }).join('');

    tbody.querySelectorAll('.lead-details-toggle').forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const detailsEl = targetId ? document.getElementById(targetId) : null;
            if (!detailsEl) return;

            detailsEl.classList.toggle('hidden');
            this.textContent = detailsEl.classList.contains('hidden') ? 'View Details' : 'Hide Details';
        });
    });

    const exportBtn = document.getElementById('exportLeads');
    if (exportBtn) {
        exportBtn.onclick = () => {
            exportLeadsToCSV(safeLeads);
        };
    }
}

function exportLeadsToCSV(leads) {
    const headers = ['Business Name', 'Address', 'Phone', 'Website', 'Rating', 'Category'];
    const csvContent = [
        headers.join(','),
        ...leads.map(lead => [
            `"${lead.businessName}"`,
            `"${lead.address}"`,
            `"${lead.phone}"`,
            `"${lead.website}"`,
            lead.rating,
            `"${lead.category}"`
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

function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Show step 2
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    
    if (step1) step1.classList.add('hidden');
    if (step2) step2.classList.remove('hidden');
    
    // Simulate file parsing and show column mapping
    setTimeout(() => {
        displayColumnMapping(['Company Name', 'Email', 'Phone', 'Industry']);
    }, 500);
}

function displayColumnMapping(columns) {
    const mappingDiv = document.getElementById('columnMapping');
    if (!mappingDiv) return;
    
    mappingDiv.innerHTML = `
        <div class="column-mapping">
            <h4>Map your data columns:</h4>
            ${columns.map(col => `
                <div class="mapping-row" style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 4px;">${col}:</label>
                    <select class="form-control">
                        <option value="${col.toLowerCase().replace(' ', '_')}">${col}</option>
                        <option value="name">Name</option>
                        <option value="email">Email</option>
                        <option value="phone">Phone</option>
                        <option value="company">Company</option>
                        <option value="skip">Skip this column</option>
                    </select>
                </div>
            `).join('')}
        </div>
    `;
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
        const formData = new FormData();
        formData.append('file', file);

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
}

async function loadCampaignStrategyOptions() {
    const strategySelect = document.getElementById('campaignStrategy');
    if (!strategySelect) return;

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
    } catch (error) {
        console.error('Campaign strategy options loading error:', error);
        campaignStrategyOptions = [];
        strategySelect.innerHTML = '<option value="">None</option>';
    } finally {
        resetCampaignStrategyVersionDropdown();
    }
}

async function handleCampaignStrategyChange(event) {
    const strategyId = event?.target?.value || '';
    const versionSelect = document.getElementById('campaignStrategyVersion');

    resetCampaignStrategyVersionDropdown();
    if (!strategyId) return;

    if (versionSelect) {
        versionSelect.disabled = true;
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
    }
}

async function loadCampaigns() {
    try {
        const response = await apiRequest('/api/campaigns');
        appData.campaigns = Array.isArray(response?.campaigns) ? response.campaigns : [];
        saveDataToStorage();
    } catch (error) {
        console.error('Campaign loading error:', error);
        appData.campaigns = [];
    }

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
        contentDiv.innerHTML = selectedChannels.map(channel => `
            <div class="content-form">
                <h5>${channel} Content</h5>
                <div class="form-group">
                    <label class="form-label">Subject/Title</label>
                    <input type="text" class="form-control" id="${channel}-subject" placeholder="Enter ${channel} subject">
                </div>
                <div class="form-group">
                    <label class="form-label">Message Content</label>
                    <textarea class="form-control" id="${channel}-content" rows="4" placeholder="Enter ${channel} message content"></textarea>
                </div>
            </div>
        `).join('');
    }
}

async function createCampaign() {
    const campaignName = document.getElementById('campaignName');
    const campaignObjective = document.getElementById('campaignObjective');
    const audienceSource = document.getElementById('audienceSource');
    const strategySelect = document.getElementById('campaignStrategy');
    const strategyVersionSelect = document.getElementById('campaignStrategyVersion');
    const strategyWarning = document.getElementById('campaignStrategyWarning');
    
    if (!campaignName || !campaignObjective) return;
    
    const selectedChannels = Array.from(
        document.querySelectorAll('.wizard-step[data-step="2"] input[type="checkbox"]:checked')
    ).map(cb => cb.value);
    
    if (!campaignName.value || !campaignObjective.value || selectedChannels.length === 0) {
        showErrorMessage('Please fill in all required fields.');
        return;
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

        const channelContent = selectedChannels.map(channel => {
            const contentEl = document.getElementById(`${channel}-content`);
            const subjectEl = document.getElementById(`${channel}-subject`);
            return {
                channel,
                subject: subjectEl?.value || '',
                content: contentEl?.value || ''
            };
        });

        const payload = {
            campaign_name: campaignName.value,
            channels: selectedChannels,
            target_audience: campaignObjective.value,
            audience_source: audienceSource?.value || 'scraped_leads',
            content: JSON.stringify(channelContent),
            schedule_date: null,
            budget: null
        };
        if (strategyId) {
            payload.strategy_id = strategyId;
        }
        if (strategyVersion && strategyId) {
            payload.strategy_version_no = parseInt(strategyVersion, 10);
        }

        console.log('[campaign_debug] createCampaign payload:', payload);
        await apiRequest('/api/campaigns/create', 'POST', payload);

        const createdCampaignName = campaignName.value;

        nextWizardStep(1);
        const form = document.getElementById('campaignDetailsForm');
        if (form) form.reset();
        if (strategySelect) strategySelect.value = '';
        resetCampaignStrategyVersionDropdown();

        showCampaignTab('active');
        setActiveCampaignTab(document.querySelector('[data-tab="active"]'));
        await loadCampaigns();

        showSuccessMessage(`Campaign "${createdCampaignName}" created successfully!`);
    } catch (error) {
        console.error('Campaign creation error:', error);
        showErrorMessage(error.message || 'Failed to create campaign.');
    }
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
                return Array.isArray(parsed) ? parsed : [parsed];
            } catch {
                return [{ content: rawContent }];
            }
        }
        if (typeof rawContent === 'object') return [rawContent];
        return [];
    };
    
    campaignsGrid.innerHTML = appData.campaigns.map(campaign => {
        const campaignId = campaign.id || campaign.campaign_id || Date.now();
        const channels = Array.isArray(campaign.channels) ? campaign.channels : [];
        const contentItems = parseContent(campaign.content);
        const scheduleDate = campaign.schedule_date ? formatValue(campaign.schedule_date) : 'Not scheduled';
        const budget = campaign.budget !== null && campaign.budget !== undefined ? formatValue(campaign.budget) : 'Not set';
        const metrics = campaign.metrics || { sent: 0, opened: 0, clicked: 0, converted: 0 };

        const extraFields = Object.entries(campaign)
            .filter(([k]) => ![
                'id', 'campaign_id', 'name', 'campaign_name', 'objective', 'target_audience',
                'channels', 'status', 'created', 'metrics', 'content', 'schedule_date', 'budget'
            ].includes(k))
            .map(([k, v]) => `<div><strong>${k}:</strong> ${formatValue(v)}</div>`)
            .join('');

        return `
        <div class="campaign-card">
            <div class="campaign-card__header">
                <h3 class="campaign-card__title">${campaign.name || campaign.campaign_name || 'Untitled Campaign'}</h3>
                <div class="campaign-card__status">
                    <span class="status status--success">${campaign.status || 'Unknown'}</span>
                </div>
            </div>
            <div class="campaign-card__body">
                <div style="margin-bottom:12px;">
                    <div><strong>Objective:</strong> ${campaign.objective || campaign.target_audience || 'N/A'}</div>
                    <div><strong>Channels:</strong> ${channels.length ? channels.map(ch => `<span class="status status--info">${ch}</span>`).join(' ') : 'N/A'}</div>
                    <div><strong>Schedule Date:</strong> ${scheduleDate}</div>
                    <div><strong>Budget:</strong> ${budget}</div>
                </div>

                ${contentItems.length ? `
                    <div style="margin-bottom:12px;">
                        <strong>Content:</strong>
                        ${contentItems.map(item => `
                            <div style="margin-top:6px;">
                                ${item.channel ? `<div><strong>Channel:</strong> ${formatValue(item.channel)}</div>` : ''}
                                ${item.subject ? `<div><strong>Subject:</strong> ${formatValue(item.subject)}</div>` : ''}
                                ${item.content ? `<div><strong>Message:</strong> ${formatValue(item.content)}</div>` : ''}
                                ${!item.channel && !item.subject && !item.content ? `<div>${formatValue(item)}</div>` : ''}
                            </div>
                        `).join('')}
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
                    <button class="btn btn--sm btn--secondary edit-btn" data-id="${escapeAttr(String(campaignId))}">Edit</button>
                    <button class="btn btn--sm btn--outline pause-btn" data-id="${escapeAttr(String(campaignId))}">Pause</button>
                </div>
            </div>
        </div>
        `;
    }).join('');

    campaignsGrid.querySelectorAll('.edit-btn').forEach(button => {
        button.addEventListener('click', () => {
            editCampaign(button.dataset.id);
        });
    });

    campaignsGrid.querySelectorAll('.pause-btn').forEach(button => {
        button.addEventListener('click', () => {
            pauseCampaign(button.dataset.id);
        });
    });
}

async function editCampaign(campaignId) {
    const campaign = appData.campaigns.find(c => String(c.campaign_id || c.id) === String(campaignId));
    const currentName = campaign?.campaign_name || campaign?.name || '';
    const nextName = prompt('Edit campaign name', currentName);

    if (nextName === null) {
        return;
    }

    const updatedName = nextName.trim();
    if (!updatedName) {
        showErrorMessage('Campaign name cannot be empty.');
        return;
    }

    try {
        await apiRequest(`/api/campaigns/${encodeURIComponent(campaignId)}`, 'PUT', {
            campaign_name: updatedName
        });

        await loadCampaigns();
        showSuccessMessage('Campaign updated successfully! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
    } catch (error) {
        console.error('Campaign update error:', error);
        showErrorMessage(error.message || 'Failed to update campaign.');
    }
}

async function pauseCampaign(campaignId) {
    try {
        const response = await apiRequest(`/api/campaigns/${encodeURIComponent(campaignId)}/pause`, 'POST', {});
        await loadCampaigns();

        const newStatus = response?.campaign?.status || 'updated';
        showSuccessMessage(`Campaign ${String(newStatus).toLowerCase()}! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.`);
    } catch (error) {
        console.error('Campaign pause error:', error);
        showErrorMessage(error.message || 'Failed to update campaign status.');
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
    updateProfileCTAState();
}

function exportApplicationData() {
    const exportData = {
        businessProfile: appData.businessProfile,
        generatedStrategy: appData.generatedStrategy,
        currentStrategyId: appData.currentStrategyId,
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
window.showTemplateModal = showTemplateModal;
window.closeModal = closeModal;
