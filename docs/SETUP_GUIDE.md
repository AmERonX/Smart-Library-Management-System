# SLMS Setup Guide for New Users

This guide will help you set up the Smart Library Management System from scratch on a new machine.

## Prerequisites

Before starting, ensure you have:

1. **Python 3.10 or higher**
   - Check: `python --version`
   - Download: https://www.python.org/downloads/

2. **PostgreSQL 15 or higher**
   - Check: `psql --version`
   - Download: https://www.postgresql.org/download/

3. **Git** (optional, for cloning)
   - Check: `git --version`


## Step-by-Step Setup

### 1. Extract/Clone the Project

```bash
# If you received a ZIP file
unzip SLMS_checkpoint2.zip
cd SLMS_checkpoint2

# OR if cloning from Git
git clone <repository-url>
cd SLMS_checkpoint2
```

### 2. Create Virtual Environment

**Windows (PowerShell):**
```powershell
Remove-Item -Recurse -Force venv(remove existing venv, if exists, to start fresh)
python -m venv venv(create new venv) 
#py -<version> -m venv venv(to install a specific version) e.g # py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1(activate venv)
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Troubleshooting:**
- If you get "execution policy" error on Windows:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### 3. Install Dependencies

```bash
python.exe -m pip install --upgrade pip 
pip install -r requirements.txt
```

**Expected output:** Should install ~20 packages including FastAPI, SQLAlchemy, psycopg2, etc.

AI enhancement and vector search packages included:
- `google-generativeai` (embeddings and metadata extraction)
- `faiss-cpu` (vector index)
- `portalocker` (file-level locks for FAISS writes)
- `beautifulsoup4` (HTML text extraction)

**Common Issues:**
- **psycopg2 fails on Windows**: Install `psycopg2-binary` instead
  ```bash
  pip install psycopg2-binary
  ```

### 4. Setup PostgreSQL Database

#### 4.1 Create Database

**Windows (PowerShell):**
```powershell
# Login to PostgreSQL (will prompt for password)
psql -U postgres

# Inside psql prompt:
CREATE DATABASE slms;
\q
```

**Linux/Mac:**
```bash
sudo -u postgres psql
CREATE DATABASE slms;
\q
```

#### 4.2 Run Database Schema

```bash
# Navigate to project root, then:
psql -U postgres -d slms -f db/Schema/db_files.sql
```

**Verify tables created:**
```bash
psql -U postgres -d slms -c "\dt lms_core.*"
```

You should see tables like:
- `lms_core.books`
- `lms_core.pending_catalogue`
- `lms_core.catalogue_audit`
- etc.

### 5. Configure Environment Variables

#### 5.1 Create `.env` file

Copy the example file:
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

#### 5.2 Edit `.env` file

Open `.env` in any text editor and set your database credentials:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/slms

# AI enhancement keys (optional but required for AI pipeline and semantic search)
GOOGLE_API_KEY=your_google_api_key_here
LANGSEARCH_KEY=your_langsearch_key_here

# Artifact directories (defaults shown). Use absolute paths if needed.
ENHANCED_BOOKS_DIR=data/enhanced_books
FAISS_INDEX_DIR=data/faiss_index
```

**IMPORTANT:** If your password contains special characters, URL-encode them:
- `@` → `%40`
- `:` → `%3A`
- `/` → `%2F`
- `#` → `%23`

**Example:**
- Password: `myPass@123`
- Encoded: `myPass%40123`
- Full URL: `postgresql://postgres:myPass%40123@localhost:5432/slms`

### 6. Start the Server

**Windows (Recommended):**
```powershell
.\start_server.ps1
```
#### In case of powershell execution policy issue run following command, to temporarily bypass it:
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\start_server.ps1
```


**Manual Start (All Platforms):**
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Expected Output:**
```
============================================================
  SLMS - Smart Library Management System
============================================================

✓ Found .env file
✓ Virtual environment activated

Starting server...
  URL: http://127.0.0.1:8000
  Docs: http://127.0.0.1:8000/docs
  ReDoc: http://127.0.0.1:8000/redoc

INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 7. Verify Installation

Open your browser and visit:
- **API Docs:** http://127.0.0.1:8000/docs
- **Health Check:** http://127.0.0.1:8000/health

Or use curl:
```bash
curl http://127.0.0.1:8000/health
```

Expected response:
```json
{
  "service": "operational",
  "database": "connected",
  "apis": {
    "open_library": "reachable",
    "google_books": "reachable"
  }
}
```

## Common Issues & Solutions

### Issue 1: "psycopg2" installation fails

**Solution:**
```bash
pip uninstall psycopg2
pip install psycopg2-binary
```

### Issue 2: "could not translate host name" database error

**Cause:** Special characters in password not URL-encoded

**Solution:** Encode special characters in `.env` file (see Step 5.2)

### Issue 3: "relation does not exist" database error

**Cause:** Database schema not initialized

**Solution:** Run the schema file again:
```bash
psql -U postgres -d slms -f db/Schema/db_files.sql
```

### Issue 4: "Port 8000 already in use"

**Solution:**
```bash
# Find and kill the process using port 8000
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac:
lsof -ti:8000 | xargs kill -9
```

### Issue 5: Virtual environment activation fails (Windows)

**Solution:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue 6: PostgreSQL not installed

**Windows:** Download from https://www.postgresql.org/download/windows/
**Mac:** `brew install postgresql`
**Linux:** `sudo apt-get install postgresql postgresql-contrib`

## Testing Your Setup

### Quick Test

```bash
# Test health endpoint
curl http://127.0.0.1:8000/health

# Test adding a book
curl -X POST "http://127.0.0.1:8000/catalogue/add" \
  -H "Content-Type: application/json" \
  -d '{
    "isbn": "9780132350884",
    "title": "Clean Code",
    "total_copies": 1
  }'
```

### Run Test Suite

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_complete_workflow.py -v
```

## Quick Reference

### Common API Commands

Add Book
```bash
curl -X POST "http://localhost:8000/catalogue/add" \
  -H "Content-Type: application/json" \
  -d '{"isbn":"9780132350884","title":"Clean Code","total_copies":3}'
```

List Pending
```bash
curl http://localhost:8000/catalogue/pending
```

Approve
```bash
curl -X POST "http://localhost:8000/catalogue/confirm/1" \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "reason": "Verified"}'
```

Insert
```bash
curl -X POST "http://localhost:8000/catalogue/insert/1"
```

Audit Trail
```bash
curl http://localhost:8000/catalogue/audit/1
```

### Testing Shortcuts
```bash
pytest tests/ -v
pytest tests/test_insertion.py -v
pytest tests/ --cov=services --cov-report=html
```

Notes:
- The AI E2E test `tests/test_ai_pipeline_e2e.py` requires `GOOGLE_API_KEY` and `LANGSEARCH_KEY`. It will skip when keys are absent.
- In VS Code, ensure the Test Explorer uses the same interpreter and env as your terminal:
  - Select Interpreter: `venv/Scripts/python.exe`
  - Settings (optional):
    - `python.testing.cwd = ${workspaceFolder}`
    - `python.envFile = ${workspaceFolder}/.env`

## Next Steps

Once setup is complete:

1. Read the [README.md](../README.md) for feature overview
2. Check [WORKFLOW.md](WORKFLOW.md) for complete workflow
3. Visit http://127.0.0.1:8000/docs for interactive API documentation
4. Try the example ISBNs in README.md

## Need Help?

If you encounter issues not covered here:
1. Check the logs in the terminal
2. Verify PostgreSQL is running: `pg_isready`
3. Verify Python version: `python --version` (must be 3.10+)
4. Check if all dependencies installed: `pip list`

## Checklist

Use this checklist to verify your setup:

- [ ] Python 3.10+ installed
- [ ] PostgreSQL 12+ installed and running
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Database `slms` created
- [ ] Database schema initialized
- [ ] `.env` file created with correct DATABASE_URL
- [ ] Server starts without errors
- [ ] Health check returns "operational"
- [ ] Can access http://127.0.0.1:8000/docs

---

## 📚 **Next Steps**

After successful setup, explore:
- **[WORKFLOW.md](WORKFLOW.md)** - Understand the complete workflow
- **[API_ENDPOINTS.md](API_ENDPOINTS.md)** - Learn the API
- **Quick Reference**: See the [Quick Reference](#quick-reference) section above


---

**Setup Time:** ~15-20 minutes for first-time setup  
**Last Updated:** 2025-10-11
