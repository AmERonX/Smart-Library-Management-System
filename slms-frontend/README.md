# SLMS Frontend

Web-based frontend for Smart Library Management System using vanilla HTML, CSS, and JavaScript.

## Quick Start

1. **Start Backend** (see main [README.md](../README.md))
2. **Serve Frontend:**
   ```bash
   python -m http.server 3000
   # Or use: .\start_frontend.ps1 (Windows)
   ```
3. **Access:** http://localhost:3000

## Pages

- **Admin Dashboard** (`index.html`) - Stats, recent entries, quick actions
- **Add Book** (`add-book.html`) - ISBN lookup, metadata fetch
- **Pending** (`pending.html`) - Review/approve workflow
- **Catalogue** (`catalogue.html`) - Browse, search, filter books
- **Book Detail** (`book-detail.html`) - Complete book information
- **User Portal** (`login.html`) - Secure user authentication and registration
- **User Dashboard** (`user-dashboard.html`) - User statistics, borrowed books, and active reservations
- **User Book Browse** (`user-browse.html`) - Browse the catalogue with filtering and semantic search capabilities
- **User Book Detail** (`user-book-detail.html`) - View specific book details and place reservations
- **My Borrows** (`user-borrows.html`) - View currently borrowed books and borrowing history
- **My Reservations** (`user-reservations.html`) - Manage active and historical book reservations
- **My Fines** (`user-fines.html`) - View and manage outstanding fines

## Configuration

Update API endpoint in `js/config.js`:
```javascript
const CONFIG = {
  API_BASE_URL: 'http://localhost:8000',  // Change for production
};
```

## Project Structure

```
slms-frontend/
├── *.html              # Page files
├── css/
│   ├── main.css        # Global styles
│   └── components.css  # UI components
└── js/
    ├── config.js       # Configuration
    ├── api.js          # API client
    ├── utils.js        # Utilities
    └── pages/          # Page-specific logic
```

For detailed testing instructions, see [TESTING_GUIDE.md](TESTING_GUIDE.md).
