# SLMS Frontend Testing Guide

## 🎯 What We've Built So Far

✅ **Completed:**
- Core JavaScript files (config, api, utils)
- CSS stylesheets (main, components)
- Dashboard page (index.html + dashboard.js)
- CORS support added to backend

## 📋 Testing the Dashboard

### **Step 1: Ensure Backend is Running**

Open a terminal in your backend directory and start the server:

```bash
cd D:\SLMS_checkpoint2

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start server
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

**Verify backend is working:**
Open browser and go to: http://localhost:8000/health

You should see a JSON response:
```json
{
  "service": "operational",
  "apis": {
    "open_library": "reachable",
    "google_books": "reachable"
  }
}
```

### **Step 2: Open the Frontend**

**Option A: Direct File Access (Simplest)**
1. Navigate to `D:\SLMS_checkpoint2\slms-frontend\`
2. Double-click `index.html`
3. It will open in your default browser

**Option B: Using Python HTTP Server (Recommended)**
1. Open a new terminal in the frontend directory:
   ```bash
   cd D:\SLMS_checkpoint2\slms-frontend
   python -m http.server 3000
   ```
2. Open browser: http://localhost:3000

**Option C: Using VS Code Live Server**
1. Install "Live Server" extension in VS Code
2. Right-click `index.html` → "Open with Live Server"

### **Step 3: What You Should See**

**Dashboard Page (`index.html`):**

1. **Navigation Bar** at the top:
   - SLMS logo
   - Menu: Dashboard (active), Add Book, Pending, Catalogue

2. **Statistics Cards** showing:
   - 📚 Total Books (fetched from backend)
   - ⏳ Pending Approval (count of pending entries)
   - ✓ Added Today (books added today)
   - 👥 Available Copies (total available)

3. **Recent Pending Entries** table:
   - If you have pending entries, they'll show here
   - If empty, you'll see "No Pending Entries" message

4. **Quick Actions** buttons:
   - Add New Book (goes to add-book.html)
   - Review Pending (goes to pending.html)
   - Browse Catalogue (goes to catalogue.html)

### **Step 4: Check Browser Console**

Open browser DevTools (F12) and check the Console tab:

**Expected logs:**
```
Initializing dashboard...
Backend health: {service: "operational", apis: {...}}
Dashboard stats loaded: {totalBooks: X, pendingCount: Y, ...}
Recent pending loaded: Z entries
Auto-refresh enabled (every 30s)
```

**If you see errors:**
- "Unable to connect to backend" → Backend not running or CORS not enabled
- "Network error" → Check backend URL in js/config.js
- Other errors → Check browser console for details

### **Step 5: Test Auto-Refresh**

The dashboard auto-refreshes every 30 seconds. To test:

1. Add a book via backend (use API docs or curl)
2. Wait 30 seconds or refresh the page manually
3. Stats should update automatically

### **Step 6: Test Navigation**

Click the navigation links:
- "Add Book" → Goes to add-book.html (not yet created, will show 404)
- "Pending" → Goes to pending.html (not yet created, will show 404)
- "Catalogue" → Goes to catalogue.html (not yet created, will show 404)

**Note:** These pages will be created next!

### **Step 7: Test Responsiveness**

Resize your browser window:
- Stats cards should stack on mobile
- Navigation should remain readable
- All content should be responsive

## 🐛 Troubleshooting

### **Problem: Dashboard shows "-" for all stats**

**Possible causes:**
1. Backend not running
2. CORS not enabled
3. Database empty

**Solution:**
- Verify backend is running: http://localhost:8000/health
- Check browser console for errors
- Add some test books via backend API

### **Problem: "Unable to connect to backend" error**

**Solution:**
1. Check backend is running on port 8000
2. Verify CORS middleware was added to main.py
3. Check js/config.js has correct API_BASE_URL:
   ```javascript
   API_BASE_URL: 'http://localhost:8000',
   ```

### **Problem: No pending entries showing**

**Expected behavior if database is fresh:**
- You'll see "No Pending Entries" message
- Add a book to test

**To add test data via backend:**
```bash
curl -X POST "http://localhost:8000/catalogue/add" \
  -H "Content-Type: application/json" \
  -d '{
    "isbn": "9780132350884",
    "title": "Clean Code",
    "authors": ["Robert C. Martin"],
    "total_copies": 3
  }'
```

### **Problem: Page loads but looks unstyled**

**Possible causes:**
1. CSS files not loading (check paths)
2. Browser cache

**Solution:**
1. Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
2. Check browser console for 404 errors on CSS files
3. Verify CSS files exist in `css/` folder

### **Problem: JavaScript errors in console**

**Common errors:**
- "api is not defined" → Ensure config.js and api.js load before dashboard.js
- "CONFIG is not defined" → config.js not loaded
- "Syntax error" → Check JavaScript files for typos

**Solution:**
Check the order of script tags in index.html:
```html
<script src="js/config.js"></script>     <!-- Load first -->
<script src="js/utils.js"></script>      <!-- Load second -->
<script src="js/api.js"></script>        <!-- Load third -->
<script src="js/pages/dashboard.js"></script>  <!-- Load last -->
```

## ✅ Success Checklist

Before moving to next pages, verify:

- [ ] Backend running on http://localhost:8000
- [ ] Frontend loads without errors
- [ ] Navigation bar displays correctly
- [ ] Stats cards show numbers (not "-")
- [ ] Recent pending entries table appears (empty or with data)
- [ ] Quick action buttons are clickable
- [ ] Browser console shows no errors
- [ ] Page auto-refreshes every 30 seconds

## 📝 Test Data

If you want to add test data to see the dashboard in action:

```bash
# Add a few books
curl -X POST "http://localhost:8000/catalogue/add" \
  -H "Content-Type: application/json" \
  -d '{"isbn": "9780132350884", "title": "Clean Code", "authors": ["Robert C. Martin"], "total_copies": 3}'

curl -X POST "http://localhost:8000/catalogue/add" \
  -H "Content-Type: application/json" \
  -d '{"isbn": "9780201633610", "title": "Design Patterns", "authors": ["Erich Gamma"], "total_copies": 2}'

curl -X POST "http://localhost:8000/catalogue/add" \
  -H "Content-Type: application/json" \
  -d '{"isbn": "9780134757599", "title": "Refactoring", "authors": ["Martin Fowler"], "total_copies": 1}'
```

Then refresh the dashboard to see the stats update!

## 🚀 Next Steps

Once the dashboard is working correctly, we'll continue building:
1. Add Book page (add-book.html)
2. Pending Catalogue page (pending.html)
3. Books Catalogue page (catalogue.html)
4. Book Detail page (book-detail.html)

---

## 📞 Need Help?

If you encounter issues not covered here:
1. Check browser console for specific error messages
2. Verify all files are in the correct locations
3. Ensure backend CORS middleware was added correctly
4. Try clearing browser cache

