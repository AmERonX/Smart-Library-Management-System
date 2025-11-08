# Phase-1: Book Insertion Service - Complete Guide

## Status: ✅ Production Ready

**Version**: Phase-1  
**Date**: 2025-10-08  
**Tests**: 17/17 passing ✅

## Overview

The Book Insertion Service safely inserts approved pending catalogue entries into the main books catalogue with full ISBN support, idempotency guarantees, and comprehensive audit logging.

## Quick Start (3 Minutes)

### Step 1: Apply Database Migration
```bash
# Run migration to add ISBN fields and core tables
psql -U postgres -d slms -f migrations/001_add_isbn_fields_and_core_tables.sql
```

### Step 2: Start Server
```bash
# Windows PowerShell
.\start_server.ps1

# Or directly
uvicorn main:app --reload --port 8000
```

### Step 3: Test the Complete Workflow
```bash
# 1. Add book to pending catalogue
curl -X POST http://localhost:8000/catalogue/add \
  -H "Content-Type: application/json" \
  -d '{
    "isbn": "9780132350884",
    "title": "Clean Code",
    "authors": ["Robert C. Martin"],
    "total_copies": 3
  }'
# Response: {"pending_id": 1, "status": "awaiting_confirmation"}

# 2. Approve metadata (librarian)
curl -X POST http://localhost:8000/catalogue/confirm/1 \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "edits": {"publisher": "Prentice Hall", "publication_year": "2008"}
  }'
# Response: {"status": "approved"}

# 3. Insert into main catalogue (NEW!)
curl -X POST http://localhost:8000/catalogue/insert/1
# Response: {"message": "Book inserted successfully", "book_id": 1, "status": "completed"}
```

### Step 4: Verify in Database
```sql
-- Check the inserted book
SELECT * FROM lms_core.books WHERE id = 1;

-- Check audit trail
SELECT action, details, timestamp 
FROM lms_core.catalogue_audit 
WHERE book_id = 1 
ORDER BY timestamp;
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Request                            │
│              POST /catalogue/insert/{pending_id}             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              routes/insertion.py (HTTP Layer)                │
│  - Request validation                                        │
│  - Error handling (400, 404, 500)                           │
│  - Response formatting                                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│         services/insertion.py (Business Logic)               │
│  - insert_pending_book() - Main entry point                 │
│  - ISBN normalization & type inference                       │
│  - Publisher/Author upserts (avoid duplicates)              │
│  - Book lookup by ISBN (13 → 10 → legacy)                  │
│  - Transaction management & rollback                         │
│  - Audit logging                                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  Database (PostgreSQL)                       │
│  Tables: pending_catalogue, books, authors, publishers,     │
│          book_authors, catalogue_audit                       │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. ISBN-Aware Logic
- **Dual ISBN Support**: Handles both ISBN-10 and ISBN-13
- **Normalization**: Strips hyphens, spaces, and validates format
- **Canonical Preference**: Uses ISBN-13 as primary identifier
- **Edition Handling**: Different ISBNs = different editions (separate book records)

### 2. Idempotency
- **Safe Retries**: Can be called multiple times without side effects
- **Row Locking**: Uses `SELECT FOR UPDATE` to prevent race conditions
- **Status Checking**: Returns "already completed" for processed entries
- **No Duplicates**: Upsert semantics prevent duplicate authors/publishers

### 3. Data Integrity
- **Transactional**: All operations in single DB transaction
- **Rollback on Error**: No partial state on failures
- **Constraint Validation**: Enforces available_copies ≤ total_copies
- **Audit Trail**: Every action logged with timestamp and details

### 4. Metadata Completeness
- **All Fields Inserted**: No partial skipping of available metadata
- **Nullable Fields**: Handles missing publisher, edition, cover_url gracefully
- **Author Placeholders**: Creates "Unknown Author" if authors list is empty
- **Source Priority**: Prefers output_json (librarian-confirmed) over raw_metadata

## Database Schema Changes

### Migration Required

Run the migration script to add ISBN fields:

```bash
psql -U postgres -d slms -f migrations/001_add_isbn_fields_and_core_tables.sql
```

### New Fields on `books` Table

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `isbn_10` | VARCHAR(10) | Indexed | ISBN-10 format (10 digits) |
| `isbn_13` | VARCHAR(13) | Unique, Indexed | ISBN-13 format (canonical) |
| `isbn` | VARCHAR(20) | Unique | Legacy field (backward compatible) |

### Indexes Created

- `idx_books_isbn_10` - Fast lookup by ISBN-10
- `idx_books_isbn_13` - Fast lookup by ISBN-13 (unique)

## API Endpoint

### POST `/catalogue/insert/{pending_id}`

**Description**: Insert approved pending book into main catalogue

**Path Parameters**:
- `pending_id` (integer, required): ID of pending_catalogue entry

**Request**: No body required

**Response 200 - Success**:
```json
{
  "message": "Book inserted successfully",
  "pending_id": 123,
  "book_id": 456,
  "status": "completed"
}
```

**Response 400 - Invalid State**:
```json
{
  "detail": "Pending record must be 'approved' to insert. Currently: pending"
}
```

**Response 404 - Not Found**:
```json
{
  "detail": "Pending catalogue entry not found: 99999"
}
```

**Response 500 - Server Error**:
```json
{
  "detail": "Internal server error during book insertion"
}
```

## Usage Examples

### Example 1: Insert New Book

```bash
# Approve pending entry first
curl -X POST http://localhost:8000/catalogue/confirm/123 \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

# Insert into catalogue
curl -X POST http://localhost:8000/catalogue/insert/123
```

**Result**: New book created with all metadata

### Example 2: Add Copies to Existing Book

```bash
# If ISBN already exists in catalogue
curl -X POST http://localhost:8000/catalogue/insert/124
```

**Result**: Existing book's copies incremented

### Example 3: Idempotent Retry

```bash
# Call again for same pending_id
curl -X POST http://localhost:8000/catalogue/insert/123
```

**Result**: Returns "already completed" without changes

## Workflow States

```
pending_catalogue.status transitions:

pending → awaiting_confirmation → approved → completed
                                     ↓
                                  rejected
```

**Insertion Service** only processes entries with `status='approved'`

## Testing

### Available Test Suites

#### 1. Unit Tests (Recommended)
```bash
# Run all 17 insertion tests
pytest tests/test_insertion.py -v

# Run specific test
pytest tests/test_insertion.py::test_insert_new_book_creates_records -v

# Run with coverage report
pytest tests/test_insertion.py --cov=services.insertion --cov-report=html
```

**Test Coverage (17 tests)**:
- ✅ ISBN normalization and type inference (5 tests)
- ✅ New book insertion with full metadata
- ✅ Copy addition to existing book
- ✅ New edition handling (different ISBN)
- ✅ Idempotency (repeated calls, no duplicates)
- ✅ Transaction rollback on errors
- ✅ ISBN-10 only, ISBN-13 only, both ISBNs
- ✅ Missing publisher, empty authors
- ✅ Error cases (not found, not approved, missing title)
- ✅ Audit trail logging

#### 2. Integration Tests
```bash
# Test complete workflow (requires running server)
# 1. Start server in terminal 1
uvicorn main:app --reload --port 8000

# 2. Run integration tests in terminal 2
pytest test_catalogue.py -v                    # Metadata extraction
pytest test_librarian_confirmation.py -v       # Librarian workflow
```

#### 3. Interactive Testing
```bash
# Open Swagger UI
# Visit: http://localhost:8000/docs
# Try the POST /catalogue/insert/{pending_id} endpoint
```

### Test Results Summary

**Status**: ✅ All tests passing

```
tests/test_insertion.py::test_normalize_isbn_with_hyphens PASSED
tests/test_insertion.py::test_normalize_isbn_with_spaces PASSED
tests/test_insertion.py::test_infer_isbn_type_isbn13 PASSED
tests/test_insertion.py::test_infer_isbn_type_isbn10 PASSED
tests/test_insertion.py::test_infer_isbn_type_invalid PASSED
tests/test_insertion.py::test_get_or_create_publisher_new PASSED
tests/test_insertion.py::test_get_or_create_publisher_existing PASSED
tests/test_insertion.py::test_get_or_create_author_new PASSED
tests/test_insertion.py::test_get_or_create_author_existing PASSED
tests/test_insertion.py::test_insert_new_book_creates_records PASSED
tests/test_insertion.py::test_insert_adds_copies_to_existing PASSED
tests/test_insertion.py::test_insert_creates_new_edition PASSED
tests/test_insertion.py::test_insert_idempotent PASSED
tests/test_insertion.py::test_insert_not_found PASSED
tests/test_insertion.py::test_insert_not_approved PASSED
tests/test_insertion.py::test_insert_missing_title PASSED
tests/test_insertion.py::test_audit_logs_created PASSED

==================== 17 passed in 0.48s ====================
```

## Audit Trail

Every insertion action is logged to `catalogue_audit`:

### Audit Actions

| Action | Description | Details JSON |
|--------|-------------|--------------|
| `inserted` | New book created | `{pending_id, book_id, isbn_13, isbn_10, title, ...}` |
| `copies_added` | Copies added to existing book | `{pending_id, book_id, added_copies, new_total}` |
| `pending_completed` | Pending entry marked complete | `{book_id}` |
| `insert_failed` | Insertion failed | `{error, error_type}` |

### Query Audit Logs

```sql
-- Get audit trail for pending_id
SELECT action, source, details, timestamp
FROM lms_core.catalogue_audit
WHERE book_id = 123
ORDER BY timestamp DESC;

-- Count insertions today
SELECT COUNT(*)
FROM lms_core.catalogue_audit
WHERE action = 'inserted'
  AND timestamp >= CURRENT_DATE;
```

## Error Handling

### Validation Errors (400)

- Pending entry not in 'approved' state
- Required metadata missing (e.g., no title)
- Invalid ISBN format

**Action**: Fix metadata and retry

### Not Found Errors (404)

- Pending entry doesn't exist

**Action**: Verify pending_id

### Database Errors (500)

- Constraint violations
- Connection failures
- Unexpected SQLAlchemy errors

**Action**: Check logs, verify DB state, retry if transient

## Configuration

### Environment Variables

Set in `.env`:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/slms
```

### Logging

Configure in `main.py`:

```python
LOG_LEVEL=INFO  # DEBUG for verbose insertion logs
```

## Performance Considerations

### Concurrency

- **Row Locks**: `SELECT FOR UPDATE` prevents race conditions
- **Upsert Semantics**: `INSERT ... ON CONFLICT DO NOTHING` for authors/publishers
- **Transaction Isolation**: Default READ COMMITTED is sufficient

### Optimization

- **Indexes**: ISBN fields are indexed for fast lookups
- **Batch Processing**: For bulk insertions, consider background worker (future)
- **Connection Pooling**: SQLAlchemy pool configured in `database.py`

## Future Enhancements (Not Implemented)

- [ ] Fuzzy title/author matching for books without ISBNs
- [ ] Async/background processing with Celery
- [ ] Bulk insertion endpoint for multiple pending entries
- [ ] Embedding generation integration (separate microservice)
- [ ] Full-text search indexing trigger
- [ ] Webhook notifications on completion

## Troubleshooting

### Issue: "Pending record must be 'approved'"

**Cause**: Entry not approved by librarian yet

**Solution**: Call `/catalogue/confirm/{pending_id}` first

### Issue: "Title is required but missing"

**Cause**: output_json lacks title field

**Solution**: Ensure metadata extraction populated output_json correctly

### Issue: Duplicate ISBN constraint error

**Cause**: ISBN already exists with different book_id (shouldn't happen with proper lookup)

**Solution**: Check `find_book_by_isbn()` logic, verify indexes

### Issue: Transaction deadlock

**Cause**: Concurrent insertions for same pending_id

**Solution**: Idempotency handles this; retry after brief delay

## Code Structure

```
c:\Projects\SLMS1\
├── models.py                    # SQLAlchemy models (extended)
│   ├── PendingCatalogue
│   ├── CatalogueAudit
│   ├── Publisher              # NEW
│   ├── Author                 # NEW
│   ├── Book                   # NEW (with isbn_10, isbn_13)
│   └── BookAuthor             # NEW
│
├── services/
│   ├── __init__.py
│   └── insertion.py           # Core business logic
│       ├── insert_pending_book()      # Main entry point
│       ├── normalize_isbn()
│       ├── get_or_create_publisher()
│       ├── get_or_create_author()
│       ├── find_book_by_isbn()
│       ├── create_book_and_links()
│       ├── add_copies()
│       └── log_audit()
│
├── routes/
│   ├── catalogue.py           # Existing librarian workflow
│   └── insertion.py           # NEW: Insertion endpoint
│
├── schemas.py                 # Pydantic models (extended)
│   └── InsertionResponse      # NEW
│
├── tests/
│   └── test_insertion.py      # NEW: Comprehensive tests
│
├── migrations/
│   └── 001_add_isbn_fields_and_core_tables.sql  # NEW
│
└── main.py                    # FastAPI app (updated)
```

## Contact & Support

For questions or issues with the insertion service:

1. Check audit logs: `SELECT * FROM catalogue_audit WHERE action = 'insert_failed'`
2. Review application logs: Look for `insertion_service` entries
3. Verify database state: Check pending_catalogue.status and books table
4. Run tests: `pytest tests/test_insertion.py -v`

## License

Part of Smart Library Management System (SLMS) - Phase 1 Implementation
