# Smart Library Management System (SLMS)

**Version:** 2.0 | **Status:** ✅ Production Ready | **Last Updated:** 2025-10-11

A complete FastAPI-based library management system with automatic metadata extraction, librarian confirmation workflow, and intelligent book cataloguing.

## 🎯 Features

### Core Features
- ✅ **Unified Workflow**: Single endpoint handles book addition + metadata extraction
- ✅ **Dual API Integration**: Open Library (primary) + Google Books (fallback)
- ✅ **Intelligent Fallback**: Automatically switches APIs if one fails
- ✅ **ISBN Support**: Full support for ISBN-10 and ISBN-13 formats
- ✅ **Database-First**: All operations persisted with complete audit trail
- ✅ **Idempotent Operations**: Safe to retry any step
- ✅ **Fast Response**: Optimized for <5 second response times

### Librarian Confirmation Workflow
- ✅ **Automatic Metadata Extraction**: Fetches from external APIs automatically
- ✅ **Pending Catalogue Management**: Store unconfirmed metadata separately
- ✅ **Librarian Review & Approval**: Review, edit, approve, or reject metadata
- ✅ **Complete Audit Trail**: Full traceability of all actions with timestamps
- ✅ **Transaction Safety**: Atomic operations with rollback on errors
- ✅ **Graceful Failure Handling**: Manual entry if APIs fail

### Book Insertion Service (Phase-1)
- ✅ **ISBN-Aware Insertion**: Handles both ISBN-10 and ISBN-13
- ✅ **Duplicate Detection**: Adds copies to existing books
- ✅ **Publisher/Author Upserts**: Prevents duplicate entities
- ✅ **Edition Management**: Different ISBNs = different editions
- ✅ **17/17 Tests Passing**: Comprehensive test coverage

## Quick Start

**🚀 New User?** Follow [SETUP_GUIDE.md](SETUP_GUIDE.md) for complete step-by-step instructions.

**Quick Setup:**

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac
# Edit .env with your database credentials

# 3. Initialize database
psql -U postgres -c "CREATE DATABASE slms;"
psql -U postgres -d slms -f db/Schema/db_files.sql

# 4. Verify setup
python verify_setup.py

# 5. Start server
.\start_server.ps1  # Windows
uvicorn main:app --reload  # Linux/Mac
```

**Prerequisites:** Python 3.10+, PostgreSQL 12+

**Access the API:**
- Main: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

---

## 🔄 **Complete Workflow**

The system follows a **4-step librarian-centric workflow**:

```
1. ADD BOOK → 2. REVIEW → 3. CONFIRM → 4. INSERT
```

### **Step 1: Add Book (Automatic Metadata Extraction)**
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

**Response:**
```json
{
  "message": "Book added to pending catalogue successfully",
  "pending_id": 1,
  "status": "awaiting_confirmation",
  "metadata_preview": {
    "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
    "authors": ["Robert C. Martin"],
    "publisher": "Prentice Hall",
    "publication_year": "2008",
    "isbn_10": "0132350882",
    "isbn_13": "9780132350884",
    "source": "google_books"
  }
}
```

### **Step 2: Review Pending Books (Librarian)**
```bash
curl -X GET "http://localhost:8000/catalogue/pending"
```

### **Step 3: Confirm/Reject Metadata (Librarian)**
```bash
curl -X POST "http://localhost:8000/catalogue/confirm/1" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "edits": {
      "publisher": "Prentice Hall",
      "publication_year": "2008"
    },
    "reason": "Verified and corrected"
  }'
```

### **Step 4: Insert into Main Catalogue**
```bash
curl -X POST "http://localhost:8000/catalogue/insert/1"
```

**Response:**
```json
{
  "message": "Book inserted successfully",
  "pending_id": 1,
  "book_id": 456,
  "status": "completed"
}
```

**📚 For detailed workflow diagrams, see [docs/WORKFLOW.md](docs/WORKFLOW.md)**

---

**Try it out:**
- Interactive docs: http://localhost:8000/docs
- Run tests: `pytest tests/ -v`

For detailed API documentation, see [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md).



## 📚 **Documentation Index**

**Not sure where to start?** See **[DOCUMENTATION_MAP.md](DOCUMENTATION_MAP.md)** for a guided navigation.

| Document | Purpose | Audience |
|----------|---------|----------|
| **[SETUP_GUIDE.md](SETUP_GUIDE.md)** ⭐ | Complete step-by-step installation guide | New users, deployment |
| **[PACKAGING_CHECKLIST.md](PACKAGING_CHECKLIST.md)** | Pre-deployment checklist | Developers sharing code |
| **[verify_setup.py](verify_setup.py)** | Automated setup verification | All users |
| **[docs/WORKFLOW.md](docs/WORKFLOW.md)** ⭐ | Complete workflow with diagrams | Developers, architects |
| **[docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md)** ⭐ | Full API reference | Frontend developers |
| **[docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** | Quick commands and tips | Daily development |
| **[docs/INSERTION_SERVICE_README.md](docs/INSERTION_SERVICE_README.md)** | Book insertion service details | Backend developers |
| **[docs/LIBRARIAN_CONFIRMATION_README.md](docs/LIBRARIAN_CONFIRMATION_README.md)** | Librarian workflow details | Backend developers |
| **[docs/FRONTEND_INTEGRATION_GUIDE.md](docs/FRONTEND_INTEGRATION_GUIDE.md)** | Frontend integration guide | Frontend developers |
| **[personal_notes.md](personal_notes.md)** | Development progress tracker | Internal use only |

**⭐ = Start here for new users**




## Example ISBNs to Try

- **Clean Code**: 9780132350884
- **The Pragmatic Programmer**: 9780135957059
- **Design Patterns**: 9780201633610
- **Refactoring**: 9780134757599
- **Code Complete**: 9780735619678

## Performance

- **Target**: <3 second response time
- **Typical**: 1-2 seconds for successful fetch
- **Timeout**: 5 seconds per API call
- **Database**: PostgreSQL with connection pooling

## Project Structure

```
SLMS1/
├── main.py                          # FastAPI application entry point
├── config.py                        # Configuration settings
├── database.py                      # Database session management
├── models.py                        # SQLAlchemy ORM models
├── schemas.py                       # Pydantic request/response schemas
├── requirements.txt                 # Python dependencies
├── start_server.ps1                 # Windows startup script
├── .env.example                     # Environment variables template
│
├── routes/                          # API endpoints
│   ├── __init__.py
│   ├── catalogue.py                 # Librarian confirmation workflow
│   └── insertion.py                 # Book insertion service
│
├── services/                        # Business logic layer
│   ├── __init__.py
│   └── insertion.py                 # Book insertion business logic
│
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── test_catalogue.py            # Metadata extraction tests
│   ├── test_librarian_confirmation.py  # Librarian workflow tests
│   ├── test_insertion.py            # Insertion service tests (17 tests)
│   └── test_complete_workflow.py    # End-to-end workflow tests
│
├── db/                              # Database files
│   ├── Schema/
│   │   └── db_files.sql             # PostgreSQL base schema
│   └── migrations/
│       ├── 001_add_isbn_fields_and_core_tables.sql
│       ├── 002_add_isbn_fields_to_pending_catalogue.sql
│       └── 003_rename_catalogue_audit_book_id_to_pending_id.sql
│
└── docs/                            # Documentation
    ├── API_ENDPOINTS.md             # Complete API reference
    ├── WORKFLOW.md                  # Detailed workflow diagrams
    ├── QUICK_REFERENCE.md           # Quick commands and tips
    ├── INSERTION_SERVICE_README.md  # Insertion service documentation
    └── LIBRARIAN_CONFIRMATION_README.md  # Librarian workflow docs
```

## License

Part of the Smart Library Management System (SLMS) project.
