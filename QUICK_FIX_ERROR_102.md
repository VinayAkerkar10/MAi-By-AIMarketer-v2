# 🔧 Fix Error Code -102

**Error Code: -102** means the web server isn't running or the connection was refused.

## ✅ Quick Fix (Choose One):

### Method 1: Use the Batch File (Easiest)

1. **Double-click** `START_UI_SERVER.bat` in the project root
2. Wait for: `Serving HTTP on 0.0.0.0 port 8080`
3. Open browser: `http://localhost:8080/standalone.html`

### Method 2: Manual Start

1. **Open PowerShell** in the project root
2. **Run:**
   ```powershell
   cd frontend
   python -m http.server 8080
   ```
3. **Keep that window open** (don't close it!)
4. Open browser: `http://localhost:8080/standalone.html`

### Method 3: Open File Directly (No Server)

1. Navigate to `frontend` folder
2. Right-click `standalone.html`
3. Select "Open with" → Your browser
4. ⚠️ Some features may not work without a server

---

## 🔍 Troubleshooting

### If Python is not found:
```powershell
# Check if Python is installed
python --version

# If not installed, download from python.org
```

### If Port 8080 is already in use:
```powershell
# Use a different port
python -m http.server 8081

# Then open: http://localhost:8081/standalone.html
```

### If you see "Connection Refused":
- Make sure the server window is still open
- Check Windows Firewall isn't blocking it
- Try a different port (8081, 8082, etc.)

---

## ✅ Verify Server is Running

After starting the server, you should see:
```
Serving HTTP on 0.0.0.0 port 8080 (http://0.0.0.0:8080/)
```

**If you see this, the server is running!** ✅

---

## 📋 What to Do Next

1. ✅ Start the server (use Method 1 or 2 above)
2. ✅ Keep the server window open
3. ✅ Open browser: `http://localhost:8080/standalone.html`
4. ✅ You should see the MAi UI!

---

**Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.**
