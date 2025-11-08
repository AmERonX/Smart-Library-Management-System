# Librarian Confirmation & Audit Logging Feature

## Overview

This module extends the Smart Library Management System (SLMS) with a complete librarian confirmation workflow and audit logging system. It ensures that every book's metadata is validated by a librarian before being added to the main catalogue, with full traceability for accountability.

## Features

✅ **Pending Catalogue Management** - Store incoming book metadata awaiting confirmation  
✅ **Librarian Confirmation API** - Review, edit, approve, or reject metadata  
✅ **Audit Logging** - Complete traceability of all actions with timestamps  
✅ **Input Validation** - Pydantic models ensure data integrity  
✅ **Transaction Safety** - Atomic operations with rollback on errors  
✅ **RESTful API** - Clean FastAPI endpoints with automatic documentation  

## Architecture

### Database Tables

#### `pending_catalogue`
Stores books awaiting librarian confirmation.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Unique ID |
| `isbn` | VARCHAR(20) | ISBN-10 or ISBN-13 |
| `title` | TEXT | Book title (required) |
| `authors` | TEXT[] | Array of author names |
| `total_copies` | INT | Number of copies to add |
| `raw_metadata` | JSONB | Fetched metadata from APIs |
| `output_json` | JSONB | Finalized metadata post-confirmation |
| `status` | VARCHAR(20) | Pipeline stage (see below) |
| `created_at` | TIMESTAMP | Creation timestamp (UTC) |
| `updated_at` | TIMESTAMP | Last update timestamp (UTC) |

**Status Values:**
- `pending` - Initial entry, metadata extraction not started
- `awaiting_confirmation` - Metadata extracted, waiting for librarian
- `approved` - Librarian approved, ready for final processing
- `failed` - Rejected by librarian or extraction failed
- `completed` - Successfully inserted into main catalogue

#### `catalogue_audit`
Audit trail for all catalogue-related actions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | SERIAL PRIMARY KEY | Unique ID |
| `book_id` | INT | References `pending_catalogue(id)` |
| `action` | VARCHAR(50) | Action type (e.g., 'approved', 'rejected') |
| `source` | VARCHAR(50) | Source of action (e.g., 'librarian', 'frontend') |
| `details` | TEXT | Optional message or JSON note |
| `timestamp` | TIMESTAMP | Action timestamp (UTC) |

**Common Actions:**
- `input_received` - Initial book entry created
- `metadata_extracted` - External API metadata fetched
- `approved` - Librarian approved the metadata
- `rejected` - Librarian rejected the metadata
- `completed` - Book successfully added to main catalogue
- `error` - Error occurred during processing

## API Endpoints

### 1. Add Book to Pending Catalogue

**POST** `/catalogue/add`

Add a book to the pending catalogue for librarian confirmation.

**Request Body:**
```json
{
  "isbn": "9780132350884",
  "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
  "authors": ["Robert C. Martin"],
  "total_copies": 3
}
```

**Response (201 Created):**
```json
{
  "message": "Book added to pending catalogue successfully",
  "pending_id": 1,
  "status": "awaiting_confirmation"
}
```

**Validation Rules:**
- `isbn`: Optional, must be 10 or 13 digits (hyphens/spaces removed)
- `title`: Required, minimum 1 character
- `authors`: Optional array of strings
- `total_copies`: Required, must be ≥ 1

---

### 2. Get Pending Books

**GET** `/catalogue/pending`

Retrieve all books awaiting librarian confirmation.

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "isbn": "9780132350884",
    "title": "Clean Code",
    "authors": ["Robert C. Martin"],
    "total_copies": 3,
    "raw_metadata": {
      "publisher": "Prentice Hall",
      "publication_year": "2008",
      "description": "A handbook of agile software craftsmanship"
    },
    "output_json": null,
    "status": "awaiting_confirmation",
    "created_at": "2025-10-08T06:08:21Z",
    "updated_at": null
  }
]
```

---

### 3. Confirm Book Metadata

**POST** `/catalogue/confirm/{pending_id}`

Approve or reject book metadata after librarian review.

**Request Body (Approval):**
```json
{
  "approved": true,
  "edits": {
    "publisher": "Prentice Hall PTR",
    "publication_year": "2008",
    "edition": "1st"
  },
  "reason": "Metadata verified with library records"
}
```

**Request Body (Rejection):**
```json
{
  "approved": false,
  "reason": "Incorrect metadata - wrong edition"
}
```

**Response (200 OK - Approved):**
```json
{
  "message": "Metadata approved successfully",
  "pending_id": 1,
  "status": "approved",
  "output_json": {
    "isbn": "9780132350884",
    "title": "Clean Code",
    "authors": ["Robert C. Martin"],
    "publisher": "Prentice Hall PTR",
    "publication_year": "2008",
    "edition": "1st",
    "description": "A handbook of agile software craftsmanship",
    "total_copies": 3,
    "keywords": null,
    "embeddings": null,
    "source": "librarian_confirmation"
  }
}
```

**Response (200 OK - Rejected):**
```json
{
  "message": "Metadata rejected",
  "pending_id": 1,
  "status": "failed",
  "output_json": null
}
```

**Validation Rules:**
- `approved`: Required boolean
- `edits`: Optional dictionary of field updates (only applied if approved)
- `reason`: Required if `approved=false`

---

### 4. Get Audit Logs

**GET** `/catalogue/audit/{pending_id}`

Retrieve all audit log entries for a specific pending book.

**Response (200 OK):**
```json
{
  "message": "Audit logs retrieved successfully",
  "pending_id": 1,
  "total_entries": 2,
  "audit_logs": [
    {
      "id": 1,
      "book_id": 1,
      "action": "input_received",
      "source": "frontend",
      "details": "Book added: Clean Code",
      "timestamp": "2025-10-08T06:08:21Z"
    },
    {
      "id": 2,
      "book_id": 1,
      "action": "approved",
      "source": "librarian",
      "details": "Metadata verified with library records",
      "timestamp": "2025-10-08T06:15:42Z"
    }
  ]
}
```

---

## Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    LIBRARIAN CONFIRMATION WORKFLOW           │
└─────────────────────────────────────────────────────────────┘

1. Frontend/User Input
   │
   ├─► POST /catalogue/add
   │   └─► Creates pending_catalogue entry (status: 'awaiting_confirmation')
   │       └─► Audit log: 'input_received'
   │
2. Metadata Extraction (existing pipeline)
   │
   ├─► Fetch from Open Library / Google Books
   │   └─► Updates raw_metadata field
   │       └─► Audit log: 'metadata_extracted'
   │
3. Librarian Review
   │
   ├─► GET /catalogue/pending
   │   └─► Librarian reviews metadata
   │
4. Confirmation Decision
   │
   ├─► POST /catalogue/confirm/{pending_id}
   │   │
   │   ├─► If approved=true:
   │   │   ├─► Merge edits into raw_metadata
   │   │   ├─► Create output_json
   │   │   ├─► Set status='approved'
   │   │   └─► Audit log: 'approved'
   │   │
   │   └─► If approved=false:
   │       ├─► Set status='failed'
   │       └─► Audit log: 'rejected'
   │
5. Final Processing (future step)
   │
   └─► Insert into main books/authors/publishers tables
       └─► Set status='completed'
           └─► Audit log: 'completed'
```

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Database

Set the `DATABASE_URL` environment variable:

```bash
# Windows PowerShell
$env:DATABASE_URL="postgresql://user:password@localhost:5432/slms"

# Linux/Mac
export DATABASE_URL="postgresql://user:password@localhost:5432/slms"
```

Or create a `.env` file:
```
DATABASE_URL=postgresql://user:password@localhost:5432/slms
```

### 3. Initialize Database

Run the SQL schema:

```bash
psql -U postgres -d slms -f Schema/db_files.sql
```

Or let the application auto-create tables on startup (SQLAlchemy will handle this).

### 4. Run the Application

```bash
python main.py
```

Or with uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing

### Run Unit Tests

```bash
pytest test_librarian_confirmation.py -v
```

### Test Coverage

The test suite includes:
- ✅ Valid input validation
- ✅ Invalid ISBN rejection
- ✅ Missing required fields
- ✅ Pending book retrieval
- ✅ Approval workflow with edits
- ✅ Rejection workflow with reason
- ✅ Audit log creation and retrieval
- ✅ ISBN normalization (hyphens removed)
- ✅ Error handling (404, 400, 422, 500)

### Manual Testing with cURL

**Add a book:**
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

**Get pending books:**
```bash
curl -X GET "http://localhost:8000/catalogue/pending"
```

**Approve metadata:**
```bash
curl -X POST "http://localhost:8000/catalogue/confirm/1" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "edits": {"publisher": "Prentice Hall"},
    "reason": "Verified"
  }'
```

**Get audit logs:**
```bash
curl -X GET "http://localhost:8000/catalogue/audit/1"
```

## File Structure

```
SLMS1/
├── main.py                          # FastAPI app with metadata extraction
├── database.py                      # Database configuration & session management
├── models.py                        # SQLAlchemy ORM models
├── schemas.py                       # Pydantic request/response models
├── config.py                        # Configuration settings
├── routes/
│   ├── __init__.py
│   └── catalogue.py                 # Catalogue confirmation endpoints
├── test_librarian_confirmation.py   # Unit tests
├── requirements.txt                 # Python dependencies
└── Schema/
    └── db_files.sql                 # PostgreSQL schema
```

## Error Handling

All endpoints return standardized error responses:

**400 Bad Request:**
```json
{
  "detail": "Cannot confirm entry with status 'approved'. Expected 'awaiting_confirmation'."
}
```

**404 Not Found:**
```json
{
  "detail": "Pending catalogue entry with id 999 not found"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "isbn"],
      "msg": "ISBN must be exactly 10 or 13 digits",
      "type": "value_error"
    }
  ]
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to add book to pending catalogue: <error message>"
}
```

## Design Decisions

### 1. **Separate Pending Catalogue Table**
- Keeps unconfirmed data isolated from production catalogue
- Allows flexible metadata editing without affecting live data
- Enables easy cleanup of rejected entries

### 2. **JSONB for Metadata Storage**
- Flexible schema for varying metadata from different sources
- Efficient querying with PostgreSQL JSONB operators
- Easy to merge edits without complex column updates

### 3. **Comprehensive Audit Logging**
- Every action is logged with timestamp and source
- Provides accountability for librarian decisions
- Enables debugging and workflow analysis
- Supports compliance and data governance

### 4. **Transaction-Based Confirmation**
- Confirmation and audit logging happen atomically
- Rollback on errors ensures data consistency
- Prevents partial updates

### 5. **Status-Based Workflow**
- Clear state machine: pending → awaiting_confirmation → approved/failed → completed
- Easy to query books at each stage
- Supports future automation and reporting

### 6. **UTC Timestamps**
- All timestamps stored in UTC for consistency
- Avoids timezone confusion in distributed systems
- Easy conversion to local time in frontend

## Future Enhancements

- [ ] Bulk approval/rejection of multiple books
- [ ] Librarian assignment and workload tracking
- [ ] Email notifications for pending reviews
- [ ] Metadata comparison view (API vs. librarian edits)
- [ ] Integration with main catalogue insertion
- [ ] Automated metadata quality scoring
- [ ] Export audit logs to CSV/PDF
- [ ] Role-based access control (RBAC)
- [ ] Webhook support for external integrations

## Troubleshooting

### Database Connection Issues

**Error:** `Failed to initialize database`

**Solution:**
1. Verify PostgreSQL is running
2. Check `DATABASE_URL` environment variable
3. Ensure database exists: `createdb slms`
4. Verify credentials and permissions

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'sqlalchemy'`

**Solution:**
```bash
pip install -r requirements.txt
```

### Test Failures

**Error:** Tests fail with database errors

**Solution:**
- Tests use SQLite in-memory database
- Ensure `pytest` and `httpx` are installed
- Check that `test.db` is not locked by another process

## Contributing

When extending this feature:

1. **Add audit logs** for all significant actions
2. **Use transactions** for multi-step operations
3. **Validate input** with Pydantic models
4. **Handle errors** gracefully with appropriate HTTP status codes
5. **Write tests** for new functionality
6. **Document** API changes in this README

## License

Part of the Smart Library Management System (SLMS) project.

---

**Version:** 2.0.0  
**Last Updated:** 2025-10-08  
**Maintainer:** SLMS Development Team
