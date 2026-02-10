// Global data storage
let appData = {
    businessProfile: null,
    generatedStrategy: null,
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
    analytics: {
        totalLeads: 1247,
        activeCampaigns: 8,
        conversionRate: 3.2,
        roi: 285,
        monthlyMetrics: [
            { month: "Jan", leads: 120, conversions: 4 },
            { month: "Feb", leads: 145, conversions: 6 },
            { month: "Mar", leads: 167, conversions: 8 },
            { month: "Apr", leads: 198, conversions: 12 },
            { month: "May", leads: 223, conversions: 15 }
        ]
    }
};

// Sample leads data
const sampleLeads = [
    { businessName: "Innovate Software Inc", address: "123 Tech St, San Francisco, CA", phone: "+1-415-555-0123", website: "www.innovatesw.com", rating: 4.5, category: "Software Development" },
    { businessName: "DataFlow Systems", address: "456 Analytics Ave, Austin, TX", phone: "+1-512-555-0456", website: "www.dataflow.com", rating: 4.2, category: "Data Analytics" },
    { businessName: "CloudNext Technologies", address: "789 Cloud Dr, Seattle, WA", phone: "+1-206-555-0789", website: "www.cloudnext.com", rating: 4.7, category: "Cloud Services" },
    { businessName: "SecureIT Solutions", address: "321 Security Blvd, Denver, CO", phone: "+1-303-555-0321", website: "www.secureit.com", rating: 4.3, category: "Cybersecurity" },
    { businessName: "AI Ventures Corp", address: "654 Innovation Way, Boston, MA", phone: "+1-617-555-0654", website: "www.aiventures.com", rating: 4.6, category: "Artificial Intelligence" },
    { businessName: "TechStart Hub", address: "987 Startup Blvd, Austin, TX", phone: "+1-512-555-0987", website: "www.techstarthub.com", rating: 4.4, category: "Technology Consulting" },
    { businessName: "Digital Solutions Pro", address: "147 Digital Ave, San Jose, CA", phone: "+1-408-555-0147", website: "www.digitalsolutionspro.com", rating: 4.1, category: "Digital Marketing" },
    { businessName: "InnovateTech Labs", address: "258 Innovation Dr, Portland, OR", phone: "+1-503-555-0258", website: "www.innovatetech.com", rating: 4.8, category: "Research & Development" }
];

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded - Initializing MAi App');
    
    // Small delay to ensure all elements are rendered
    setTimeout(() => {
        initializeApp();
        setupNavigation();
        loadDataFromStorage();
        setupEventListeners();
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
            break;
        case 'analytics':
            setTimeout(updateAnalyticsDashboard, 200);
            break;
        case 'campaign-manager':
            displayActiveCampaigns();
            break;
        case 'templates':
            populateTemplateLibrary();
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
        updateAnalyticsDashboard();
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

    // AI Strategy Generator
    const generateStrategyBtn = document.getElementById('generateStrategy');
    if (generateStrategyBtn) {
        generateStrategyBtn.addEventListener('click', generateAIStrategy);
    }

    // Lead Scraper Form
    const leadScraperForm = document.getElementById('leadScraperForm');
    if (leadScraperForm) {
        leadScraperForm.addEventListener('submit', handleLeadScraping);
    }

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
    const geography = document.getElementById('geography').value;
    const budget = parseInt(document.getElementById('budget').value) || 0;
    const targetAudience = document.getElementById('targetAudience').value;
    
    const marketingGoals = Array.from(document.querySelectorAll('#business-profile input[type="checkbox"]:checked')).map(cb => cb.value);
    
    const profile = {
        businessName,
        industry,
        companySize,
        revenue,
        geography,
        marketingGoals,
        budget,
        targetAudience
    };
    
    console.log('Profile data:', profile);
    
    appData.businessProfile = profile;
    saveDataToStorage();
    displayProfileSummary(profile);
    showSuccessMessage('Business profile saved successfully! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
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
                <strong>Markets:</strong> ${profile.geography}
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

function generateAIStrategy() {
    console.log('Generating AI strategy...');
    
    const loadingDiv = document.getElementById('strategyLoading');
    const inputDiv = document.getElementById('strategyInput');
    const resultsDiv = document.getElementById('strategyResults');
    
    if (!loadingDiv || !inputDiv || !resultsDiv) return;
    
    // Show loading state
    inputDiv.classList.add('hidden');
    loadingDiv.classList.remove('hidden');
    resultsDiv.classList.add('hidden');
    
    // Simulate AI processing
    setTimeout(() => {
        const strategy = generateStrategyRecommendations();
        appData.generatedStrategy = strategy;
        saveDataToStorage();
        
        displayStrategyResults(strategy);
        
        loadingDiv.classList.add('hidden');
        resultsDiv.classList.remove('hidden');
        
        showSuccessMessage('AI strategy generated successfully! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
    }, 3000);
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
    // Display channels
    const channelGrid = document.getElementById('channelRecommendations');
    if (channelGrid) {
        channelGrid.innerHTML = strategy.channels.map(channel => `
            <div class="channel-card">
                <h4>${channel}</h4>
                <p>Recommended for your industry</p>
            </div>
        `).join('');
    }
    
    // Display budget allocation
    const budgetDiv = document.getElementById('budgetAllocation');
    if (budgetDiv) {
        budgetDiv.innerHTML = Object.entries(strategy.budgetAllocation).map(([channel, percentage]) => `
            <div class="budget-item">
                <strong>${channel}:</strong> ${percentage} ($${Math.round((parseFloat(percentage) / 100) * strategy.targetBudget).toLocaleString()})
            </div>
        `).join('');
    }
    
    // Display timeline
    const timelineDiv = document.getElementById('campaignTimeline');
    if (timelineDiv) {
        timelineDiv.innerHTML = `<div class="timeline-item">${strategy.timeline}</div>`;
    }
    
    // Display key messaging
    const messagingDiv = document.getElementById('keyMessaging');
    if (messagingDiv) {
        messagingDiv.innerHTML = strategy.keyMessages.map(message => `
            <div class="message-item">${message}</div>
        `).join('');
    }
    
    // Display content strategy
    const contentDiv = document.getElementById('contentStrategy');
    if (contentDiv) {
        contentDiv.innerHTML = strategy.contentStrategy.map(content => `
            <div class="content-item">${content}</div>
        `).join('');
    }
    
    // Setup export button
    const exportBtn = document.getElementById('exportStrategy');
    if (exportBtn) {
        exportBtn.onclick = () => {
            showSuccessMessage('Strategy export initiated! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
        };
    }
}

// Lead Scraper Functions
function handleLeadScraping(e) {
    e.preventDefault();
    console.log('Lead scraping form submitted');
    
    const location = document.getElementById('location').value;
    const businessType = document.getElementById('businessType').value;
    const radius = document.getElementById('radius').value;
    const additionalFilters = document.getElementById('additionalFilters').value;
    
    const searchParams = {
        location,
        businessType,
        radius,
        additionalFilters
    };
    
    startLeadScraping(searchParams);
}

function startLeadScraping(params) {
    const progressDiv = document.getElementById('scrapingProgress');
    const resultsDiv = document.getElementById('leadsResults');
    const noResultsDiv = document.getElementById('noLeadsMessage');
    const exportBtn = document.getElementById('exportLeads');
    
    if (!progressDiv || !resultsDiv) return;
    
    // Show progress
    progressDiv.classList.remove('hidden');
    resultsDiv.classList.add('hidden');
    if (noResultsDiv) noResultsDiv.classList.add('hidden');
    
    // Simulate scraping progress
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 100) progress = 100;
        
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        
        if (progressFill) progressFill.style.width = `${progress}%`;
        if (progressText) progressText.textContent = `${Math.round(progress)}%`;
        
        if (progress >= 100) {
            clearInterval(progressInterval);
            
            setTimeout(() => {
                // Filter sample leads based on business type
                const filteredLeads = sampleLeads.filter(lead => 
                    !params.businessType || lead.category.toLowerCase().includes(params.businessType.toLowerCase())
                );
                
                appData.scrapedLeads = filteredLeads;
                saveDataToStorage();
                
                displayScrapedLeads(filteredLeads);
                progressDiv.classList.add('hidden');
                resultsDiv.classList.remove('hidden');
                if (exportBtn) exportBtn.disabled = false;
                
                showSuccessMessage(`Found ${filteredLeads.length} leads! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.`);
            }, 500);
        }
    }, 200);
}

function displayScrapedLeads(leads) {
    const tbody = document.getElementById('leadsTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = leads.map(lead => `
        <tr>
            <td><strong>${lead.businessName}</strong></td>
            <td>${lead.address}</td>
            <td>${lead.phone}</td>
            <td><a href="http://${lead.website}" target="_blank">${lead.website}</a></td>
            <td>⭐ ${lead.rating}</td>
            <td><span class="status status--info">${lead.category}</span></td>
        </tr>
    `).join('');
    
    // Setup export functionality
    const exportBtn = document.getElementById('exportLeads');
    if (exportBtn) {
        exportBtn.onclick = () => {
            exportLeadsToCSV(leads);
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

function startDataEnrichment() {
    // Show step 3
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');
    
    if (step2) step2.classList.add('hidden');
    if (step3) step3.classList.remove('hidden');
    
    // Simulate enrichment progress
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress > 100) progress = 100;
        
        const progressBar = document.getElementById('enrichmentProgress');
        const progressText = document.getElementById('enrichmentProgressText');
        
        if (progressBar) progressBar.style.width = `${progress}%`;
        if (progressText) progressText.textContent = `${Math.round(progress)}%`;
        
        if (progress >= 100) {
            clearInterval(progressInterval);
            
            setTimeout(() => {
                showEnrichmentResults();
            }, 500);
        }
    }, 300);
}

function showEnrichmentResults() {
    // Show step 4
    const step3 = document.getElementById('step3');
    const step4 = document.getElementById('step4');
    
    if (step3) step3.classList.add('hidden');
    if (step4) step4.classList.remove('hidden');
    
    // Sample data for before/after comparison
    const beforeData = [
        { company: 'TechCorp', email: '', phone: '', website: '' },
        { company: 'DataSoft', email: '', phone: '', website: '' },
        { company: 'CloudTech', email: '', phone: '', website: '' }
    ];
    
    const afterData = [
        { company: 'TechCorp', email: 'info@techcorp.com', phone: '+1-555-0123', website: 'www.techcorp.com' },
        { company: 'DataSoft', email: 'contact@datasoft.com', phone: '+1-555-0456', website: 'www.datasoft.com' },
        { company: 'CloudTech', email: 'hello@cloudtech.com', phone: '+1-555-0789', website: 'www.cloudtech.com' }
    ];
    
    displayComparisonTables(beforeData, afterData);
    
    // Setup download button
    const downloadBtn = document.getElementById('downloadEnrichedData');
    if (downloadBtn) {
        downloadBtn.onclick = () => {
            showSuccessMessage('Enriched data download started! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
        };
    }
    
    showSuccessMessage('Data enrichment completed successfully! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
}

function displayComparisonTables(beforeData, afterData) {
    // Before table
    const beforeHead = document.getElementById('beforeTableHead');
    const beforeBody = document.getElementById('beforeTableBody');
    
    if (beforeHead && beforeBody) {
        beforeHead.innerHTML = '<tr><th>Company</th><th>Email</th><th>Phone</th><th>Website</th></tr>';
        beforeBody.innerHTML = beforeData.map(row => `
            <tr>
                <td>${row.company}</td>
                <td>${row.email || '-'}</td>
                <td>${row.phone || '-'}</td>
                <td>${row.website || '-'}</td>
            </tr>
        `).join('');
    }
    
    // After table
    const afterHead = document.getElementById('afterTableHead');
    const afterBody = document.getElementById('afterTableBody');
    
    if (afterHead && afterBody) {
        afterHead.innerHTML = '<tr><th>Company</th><th>Email</th><th>Phone</th><th>Website</th></tr>';
        afterBody.innerHTML = afterData.map(row => `
            <tr>
                <td>${row.company}</td>
                <td><strong>${row.email}</strong></td>
                <td><strong>${row.phone}</strong></td>
                <td><strong>${row.website}</strong></td>
            </tr>
        `).join('');
    }
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
    
    // Load active campaigns
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

function createCampaign() {
    const campaignName = document.getElementById('campaignName');
    const campaignObjective = document.getElementById('campaignObjective');
    
    if (!campaignName || !campaignObjective) return;
    
    const selectedChannels = Array.from(document.querySelectorAll('.wizard-step[data-step="2"] input[type="checkbox"]:checked'))
        .map(cb => cb.value);
    
    if (!campaignName.value || !campaignObjective.value || selectedChannels.length === 0) {
        showErrorMessage('Please fill in all required fields.');
        return;
    }
    
    const campaign = {
        id: Date.now(),
        name: campaignName.value,
        objective: campaignObjective.value,
        channels: selectedChannels,
        status: 'Active',
        created: new Date().toLocaleDateString(),
        metrics: {
            sent: Math.floor(Math.random() * 1000) + 100,
            opened: Math.floor(Math.random() * 500) + 50,
            clicked: Math.floor(Math.random() * 100) + 10,
            converted: Math.floor(Math.random() * 20) + 2
        }
    };
    
    appData.campaigns.push(campaign);
    saveDataToStorage();
    
    // Reset wizard to step 1
    nextWizardStep(1);
    const form = document.getElementById('campaignDetailsForm');
    if (form) form.reset();
    
    // Switch to active campaigns tab
    showCampaignTab('active');
    setActiveCampaignTab(document.querySelector('[data-tab="active"]'));
    displayActiveCampaigns();
    
    showSuccessMessage(`Campaign "${campaign.name}" created successfully! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.`);
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
    
    campaignsGrid.innerHTML = appData.campaigns.map(campaign => `
        <div class="campaign-card">
            <div class="campaign-card__header">
                <h3 class="campaign-card__title">${campaign.name}</h3>
                <div class="campaign-card__status">
                    <span class="status status--success">${campaign.status}</span>
                </div>
            </div>
            <div class="campaign-card__body">
                <div class="campaign-card__metrics">
                    <div class="campaign-metric">
                        <div class="campaign-metric__value">${campaign.metrics.sent}</div>
                        <div class="campaign-metric__label">Sent</div>
                    </div>
                    <div class="campaign-metric">
                        <div class="campaign-metric__value">${campaign.metrics.opened}</div>
                        <div class="campaign-metric__label">Opened</div>
                    </div>
                    <div class="campaign-metric">
                        <div class="campaign-metric__value">${campaign.metrics.clicked}</div>
                        <div class="campaign-metric__label">Clicked</div>
                    </div>
                    <div class="campaign-metric">
                        <div class="campaign-metric__value">${campaign.metrics.converted}</div>
                        <div class="campaign-metric__label">Converted</div>
                    </div>
                </div>
                <div class="campaign-card__actions">
                    <button class="btn btn--sm btn--secondary" onclick="editCampaign(${campaign.id})">Edit</button>
                    <button class="btn btn--sm btn--outline" onclick="pauseCampaign(${campaign.id})">Pause</button>
                </div>
            </div>
        </div>
    `).join('');
}

function editCampaign(campaignId) {
    showSuccessMessage('Campaign editing feature coming soon! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.');
}

function pauseCampaign(campaignId) {
    const campaign = appData.campaigns.find(c => c.id === campaignId);
    if (campaign) {
        campaign.status = campaign.status === 'Active' ? 'Paused' : 'Active';
        saveDataToStorage();
        displayActiveCampaigns();
        showSuccessMessage(`Campaign ${campaign.status.toLowerCase()}! Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.`);
    }
}

// Analytics Functions
function updateAnalyticsDashboard() {
    // Update metric cards
    const totalLeadsEl = document.getElementById('totalLeadsMetric');
    const activeCampaignsEl = document.getElementById('activeCampaignsMetric');
    const conversionRateEl = document.getElementById('conversionRateMetric');
    const roiEl = document.getElementById('roiMetric');
    
    if (totalLeadsEl) totalLeadsEl.textContent = appData.analytics.totalLeads.toLocaleString();
    if (activeCampaignsEl) activeCampaignsEl.textContent = appData.analytics.activeCampaigns;
    if (conversionRateEl) conversionRateEl.textContent = `${appData.analytics.conversionRate}%`;
    if (roiEl) roiEl.textContent = `${appData.analytics.roi}%`;
    
    // Create charts with delay
    setTimeout(() => {
        createPerformanceChart();
        createFunnelChart();
    }, 100);
}

function createPerformanceChart() {
    const ctx = document.getElementById('performanceChart');
    if (!ctx || ctx.chart) return;
    
    try {
        ctx.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: appData.analytics.monthlyMetrics.map(m => m.month),
                datasets: [{
                    label: 'Leads Generated',
                    data: appData.analytics.monthlyMetrics.map(m => m.leads),
                    borderColor: '#1FB8CD',
                    backgroundColor: 'rgba(31, 184, 205, 0.1)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Conversions',
                    data: appData.analytics.monthlyMetrics.map(m => m.conversions),
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
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error creating performance chart:', error);
    }
}

function createFunnelChart() {
    const ctx = document.getElementById('funnelChart');
    if (!ctx || ctx.chart) return;
    
    try {
        ctx.chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Leads', 'Qualified', 'Opportunities', 'Closed'],
                datasets: [{
                    data: [1247, 623, 187, 45],
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
                appData.businessProfile = parsedData.businessProfile;
                displayProfileSummary(parsedData.businessProfile);
            }
            
            if (parsedData.generatedStrategy) {
                appData.generatedStrategy = parsedData.generatedStrategy;
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
}

function exportApplicationData() {
    const exportData = {
        businessProfile: appData.businessProfile,
        generatedStrategy: appData.generatedStrategy,
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

// Utility Functions
function showSuccessMessage(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert--info success-animation';
    alertDiv.innerHTML = `<p>${message}</p>`;
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 4000);
}

function showErrorMessage(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert--error';
    alertDiv.innerHTML = `<p>${message}</p>`;
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
        background-color: rgba(192, 21, 47, 0.1);
        border-color: rgba(192, 21, 47, 0.2);
        color: var(--color-error);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        alertDiv.remove();
    }, 4000);
}

// Global functions for inline onclick handlers
window.nextWizardStep = nextWizardStep;
window.editCampaign = editCampaign;
window.pauseCampaign = pauseCampaign;
window.showTemplateModal = showTemplateModal;
window.closeModal = closeModal;