# Running UI Without Database
## Standalone Frontend Mode

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**

---

## Quick Start

### Option 1: Open Directly in Browser

1. **Navigate to frontend folder:**
   ```powershell
   cd frontend
   ```

2. **Open `standalone.html` in your browser:**
   - Double-click `standalone.html`
   - Or right-click → "Open with" → Your browser
   - Or drag and drop the file into your browser

3. **That's it!** The UI will load with:
   - ✅ No database required
   - ✅ All data stored in browser (localStorage)
   - ✅ Full UI functionality
   - ✅ Sample data included

### Option 2: Use Python Simple HTTP Server

```powershell
# Navigate to frontend folder
cd frontend

# Start simple HTTP server (Python 3)
python -m http.server 8080

# Or if you have Python 2
python -m SimpleHTTPServer 8080
```

Then open: **http://localhost:8080/standalone.html**

### Option 3: Use Live Server (VS Code)

If you have VS Code with Live Server extension:
1. Right-click on `standalone.html`
2. Select "Open with Live Server"

---

## What Works Without Database

✅ **Business Profile** - Save and view business information  
✅ **AI Strategy Generator** - Generate strategies (uses mock AI)  
✅ **Lead Scraper** - Simulate lead scraping with sample data  
✅ **Data Enrichment** - Upload and enrich customer data  
✅ **Campaign Manager** - Create and manage campaigns  
✅ **Analytics Dashboard** - View metrics and charts  
✅ **Template Library** - Browse and use templates  

---

## Data Storage

All data is stored in **browser localStorage**:
- Business profiles
- Generated strategies
- Scraped leads
- Campaigns
- Enriched data

**Data persists** between browser sessions on the same computer.

---

## Features Available

### 1. Business Profile
- Fill out business information
- Save profile (stored locally)
- View profile summary

### 2. AI Strategy Generator
- Generate marketing strategy
- View recommended channels
- See budget allocation
- View campaign timeline
- See content strategy

### 3. Lead Scraper
- Search for leads by location
- View scraped results
- Export to CSV

### 4. Data Enrichment
- Upload CSV/Excel files
- Map columns
- Simulate enrichment
- View before/after comparison

### 5. Campaign Manager
- Create multi-channel campaigns
- View active campaigns
- Track campaign metrics

### 6. Analytics
- View key metrics
- See performance charts
- Download reports

### 7. Template Library
- Browse templates
- Filter by category/industry
- Preview and use templates

---

## Limitations (Standalone Mode)

⚠️ **No Backend Integration:**
- Strategy generation uses mock data (not real AI)
- Lead scraping shows sample data
- Data enrichment is simulated
- Campaigns don't actually send

⚠️ **No Authentication:**
- No login required
- No user management
- No organization management

⚠️ **No Real AI:**
- Strategy recommendations are based on industry templates
- Not using Ollama or OpenAI

---

## Connecting to Backend (Later)

When you're ready to connect to the backend:

1. **Update API endpoints in `app.js`:**
   ```javascript
   const API_BASE_URL = 'http://localhost:8000';
   ```

2. **Replace mock functions with real API calls:**
   ```javascript
   async function generateAIStrategy() {
       const response = await fetch(`${API_BASE_URL}/api/strategy/generate`, {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ business_profile: appData.businessProfile })
       });
       const strategy = await response.json();
       // Display strategy
   }
   ```

---

## File Structure

```
frontend/
├── index.html          # Original frontend (requires backend)
├── standalone.html     # Standalone version (no backend needed)
├── app.js              # Application logic
└── style.css           # Styling
```

---

## Quick Test

1. Open `frontend/standalone.html` in browser
2. Fill out Business Profile form
3. Click "Save Business Profile"
4. Go to "AI Strategy Generator" tab
5. Click "Generate AI Strategy"
6. View the generated strategy!

---

## Troubleshooting

### UI Not Loading
- Make sure you're opening `standalone.html` (not `index.html`)
- Check browser console for errors (F12)

### Data Not Persisting
- Check if localStorage is enabled in browser
- Try clearing browser cache and reloading

### Charts Not Showing
- Make sure Chart.js CDN is loading
- Check browser console for JavaScript errors

---

## Next Steps

1. ✅ **Explore the UI** - Test all features
2. ✅ **Fill out forms** - See how data flows
3. ✅ **Generate strategies** - View mock AI responses
4. ⏳ **Connect to backend** - When database is ready

---

**Status:** ✅ **READY** - UI works completely standalone!

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**
