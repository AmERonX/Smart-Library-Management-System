# Smart Library Management System (SLMS)

**Version:** 2.0 | **Status:** Production Ready | **Last Updated:** 2026-04-30

A complete FastAPI-based library management system with automatic metadata extraction, librarian confirmation workflow, and intelligent book cataloguing.

## Installation

```bash
# Clone
git clone https://github.com/AmERonX/Smart-Library-Management-System.git
cd Smart-Library-Management-System

# Create and activate venv (Windows)
python -m venv .venv && .\.venv\Scripts\activate
# or (Linux/Mac)
python3 -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

For full setup and troubleshooting, see [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md).

## Features

### Core Features
- **Unified Workflow**: Single endpoint handles book addition + metadata extraction
- **Dual API Integration**: Open Library (primary) + Google Books (fallback)
- **Intelligent Fallback**: Automatically switches APIs if one fails
- **ISBN Support**: Full support for ISBN-10 and ISBN-13 formats
- **Database-First**: All operations persisted with complete audit trail
- **Idempotent Operations**: Safe to retry any step
- **Fast Response**: Optimized for <5 second response times

### Librarian Confirmation Workflow
- **Automatic Metadata Extraction**: Fetches from external APIs automatically
- **Pending Catalogue Management**: Store unconfirmed metadata separately
- **Librarian Review & Approval**: Review, edit, approve, or reject metadata
- **Complete Audit Trail**: Full traceability of all actions with timestamps
- **Transaction Safety**: Atomic operations with rollback on errors
- **Graceful Failure Handling**: Manual entry if APIs fail

### Book Insertion Service
- **ISBN-Aware Insertion**: Handles both ISBN-10 and ISBN-13
- **Duplicate Detection**: Adds copies to existing books
- **Publisher/Author Upserts**: Prevents duplicate entities
- **Edition Management**: Different ISBNs = different editions

### Semantic Search & AI Features
- **Intelligent Search**: Find books by meaning, not just exact keyword matches using the `/search/semantic` API.
- **AI Metadata Enhancement**: Enriches book metadata automatically via Gemini and LangSearch.
- **Vector Embeddings**: Auto-generates text embeddings using FAISS for catalogue matching.

### User Management & Operations
- **Authentication**: Secure user registration and login.
- **Borrowing System**: Complete tracking of book checkouts and returns.
- **Book Reservations**: Users can reserve books that are currently unavailable.
- **Fines Tracking**: Automated fine calculation for late returns.

## Quick Start

**🚀 New User?** Follow [SETUP_GUIDE.md](docs/SETUP_GUIDE.md) for complete step-by-step instructions.

**Prerequisites:** Python 3.10+, PostgreSQL 12+

### Quick Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac
# Edit .env with your database credentials and (optionally) AI keys
# DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/slms
# GOOGLE_API_KEY=your_google_api_key_here
# LANGSEARCH_KEY=your_langsearch_key_here

# 3. Initialize database
psql -U postgres -c "CREATE DATABASE slms;"
psql -U postgres -d slms -f db/Schema/db_files.sql

# 4. Verify setup
python verify_setup.py
```

### Starting the Servers

**Option 1: Use PowerShell Scripts (Windows - Recommended)**
```powershell
# Terminal 1 - Backend:
.\start_server.ps1

# Terminal 2 - Frontend:
.\start_frontend.ps1
```

**Option 2: Manual Start**
```bash
# Terminal 1 - Backend:
.\venv\Scripts\Activate.ps1  # Windows
python main.py

# Terminal 2 - Frontend:
cd slms-frontend
python -m http.server 3000 --bind 127.0.0.1
```

**Access Points:**
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Frontend**: http://localhost:3000
- **Admin Dashboard**: http://localhost:3000/index.html
- **User Portal**: http://localhost:3000/login.html

### Quick Test

```bash
# Test backend health
curl http://localhost:8000/health

# Test user registration (from browser)
# Go to http://localhost:3000/login.html → Register tab
```

**Troubleshooting:**
- **Port already in use**: `netstat -ano | findstr :8000` then `taskkill /PID <PID> /F`
- **Database connection error**: Check `.env` file and ensure PostgreSQL is running
- **CORS error**: Backend CORS is configured to allow all origins

---

## ⚙️ AI Configuration Quick Start

Configure AI features via environment variables (in `.env` or your shell). If the three flags below are unset, each defaults to `ENABLE_AI_ENHANCEMENT` (default: true).

- **Flags**
  - `ENABLE_METADATA_ENHANCEMENT` — enable Gemini-based metadata extraction
  - `ENABLE_EMBEDDINGS` — enable text embeddings generation and FAISS writes
  - `ENABLE_SEMANTIC_SEARCH` — enable `/search/semantic` API
  - Legacy default: `ENABLE_AI_ENHANCEMENT`

- **Prompt template**
  - `GEMINI_PROMPT_PATH` — path to metadata prompt file (default: `prompts/gemini_metadata_prompt.txt`)

- **Models and dimensions**
  - `GEMINI_GENERATION_MODEL` (e.g., `gemini-2.5-flash-lite`)
  - `EMBEDDING_MODEL_NAME` (e.g., `models/text-embedding-004`)
  - `EMBED_DIM` (must match embedding model output size)

Example:
```env
ENABLE_METADATA_ENHANCEMENT=true
ENABLE_EMBEDDINGS=true
ENABLE_SEMANTIC_SEARCH=true
GEMINI_PROMPT_PATH=prompts/gemini_metadata_prompt.txt
GEMINI_GENERATION_MODEL=gemini-2.5-flash-lite
EMBEDDING_MODEL_NAME=models/text-embedding-004
EMBED_DIM=768
```

Verify configuration quickly: `python verify_setup.py`.

Note: Changing `EMBED_DIM` or `EMBEDDING_MODEL_NAME` requires rebuilding FAISS indexes in `data/faiss_index/`.

---

## 🔄 Complete Workflow

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

### **Semantic Search**
```bash
curl -X POST "http://localhost:8000/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "clean code software engineering",
    "mode": "hybrid",
    "top_k": 5,
    "normalize": true,
    "expand": false
  }'
```

**📚 For detailed workflow diagrams, see [docs/WORKFLOW.md](docs/WORKFLOW.md)**

---

**Try it out:**
- Interactive docs: http://localhost:8000/docs
- Run tests: `pytest tests/ -v`

For detailed API documentation, see [docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md). See [CHANGELOG.md](docs/CHANGELOG.md) for recent changes.



## 📚 Documentation Index

**Not sure where to start?**

| Document | Purpose | Audience |
|----------|---------|----------|
| **[SETUP_GUIDE.md](docs/SETUP_GUIDE.md)** ⭐ | Complete step-by-step installation guide | New users, deployment |
| **[verify_setup.py](verify_setup.py)** | Automated setup verification | All users |
| **[docs/WORKFLOW.md](docs/WORKFLOW.md)** ⭐ | Complete workflow with diagrams | Developers, architects |
| **[docs/API_ENDPOINTS.md](docs/API_ENDPOINTS.md)** ⭐ | Full API reference | Frontend developers |
| **[CHANGELOG.md](docs/CHANGELOG.md)** | Consolidated log of changes | All |

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
SLMS_checkpoint2/
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
│   ├── insertion.py                 # Book insertion service
│   ├── search.py                    # Semantic search API
│   ├── books.py                     # Books list & detail
│   ├── auth.py                      # Authentication endpoints
│   └── users.py                     # User operations (borrowing, reservations, fines)
│
├── services/                        # Business logic layer
│   ├── __init__.py
│   ├── insertion.py                 # Book insertion business logic
│   ├── embeddings.py                # Enhance metadata + store FAISS vectors
│   ├── vectorizer.py                # Shared embedding entrypoint (EMBED_DIM)
│   └── ai/
│       ├── __init__.py
│       ├── faiss_sync.py            # FAISS index IO with file locks
│       └── metadata_enhancer.py     # LangSearch + Gemini metadata enrichment
│
├── data/
│   ├── enhanced_books/              # Enhanced JSON artifacts
│   └── faiss_index/                 # FAISS index files (.index, .lock)
│
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── test_catalogue.py
│   ├── test_librarian_confirmation.py
│   ├── test_insertion.py
│   ├── test_complete_workflow.py
│   └── test_ai_pipeline_e2e.py
│
├── db/
│   ├── Schema/
│   │   └── db_files.sql
│   └── migrations/
│       ├── 001_add_isbn_fields_and_core_tables.sql
│       ├── 002_add_isbn_fields_to_pending_catalogue.sql
│       └── 003_rename_catalogue_audit_book_id_to_pending_id.sql
│
└── docs/
    ├── API_ENDPOINTS.md
    └── WORKFLOW.md
```

## License

Part of the Smart Library Management System (SLMS) project.
