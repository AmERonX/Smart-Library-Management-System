# Smart Library Management System - Complete Workflow

**Version:** 2.0  
**Last Updated:** 2025-10-09  
**Status:** ✅ Production Ready

---

## 📋 **Table of Contents**

1. [Overview](#overview)
2. [Complete Workflow Diagram](#complete-workflow-diagram)
3. [Step-by-Step Flow](#step-by-step-flow)
4. [Database State Transitions](#database-state-transitions)
5. [Error Handling](#error-handling)
6. [Audit Trail](#audit-trail)

---

## 🎯 **Overview**

The SLMS workflow is designed around a **librarian-centric** approach where:
- Books are added with automatic metadata extraction
- Librarians review and confirm/edit metadata
- Approved books are inserted into the main catalogue
- Complete audit trail tracks every action

**Key Principles:**
- ✅ Database-first (all operations persisted)
- ✅ Idempotent (safe retries)
- ✅ Transactional (atomic operations)
- ✅ Auditable (complete traceability)

---

## 🔄 **Complete Workflow Diagram**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 1: ADD BOOK TO CATALOGUE                     │
│                   POST /catalogue/add                                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  1. Validate Input                     │
        │  ├─ ISBN format (10 or 13 digits)      │
        │  ├─ Title (required)                   │
        │  └─ total_copies >= 1                  │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  2. Create Pending Entry (DB)          │
        │  INSERT INTO pending_catalogue         │
        │  ├─ isbn, title, authors               │
        │  ├─ total_copies                       │
        │  ├─ status = 'pending'                 │
        │  ├─ raw_metadata = NULL                │
        │  └─ output_json = NULL                 │
        │  COMMIT & Get pending_id               │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  3. Create Audit Log                   │
        │  INSERT INTO catalogue_audit           │
        │  ├─ id = pending_id               │
        │  ├─ action = 'input_received'          │
        │  ├─ source = 'frontend'                │
        │  └─ timestamp = NOW()                  │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  4. Fetch Metadata (External APIs)     │
        │  ├─ Try Open Library (primary)         │
        │  ├─ Try Google Books (fallback)        │
        │  └─ Merge results                      │
        └────────┬───────────────────────────────┘
                 │
                 ├─── Success ──────────┐
                 │                      │
                 │                      ▼
                 │         ┌────────────────────────────┐
                 │         │  5. Update Pending Entry   │
                 │         │  UPDATE pending_catalogue  │
                 │         │  SET raw_metadata = {...}  │
                 │         │      status = 'awaiting_   │
                 │         │               confirmation' │
                 │         │  WHERE id = pending_id     │
                 │         └────────┬───────────────────┘
                 │                  │
                 │                  ▼
                 │         ┌────────────────────────────┐
                 │         │  6. Create Audit Log       │
                 │         │  action = 'metadata_       │
                 │         │           extracted'       │
                 │         └────────┬───────────────────┘
                 │                  │
                 │                  ▼
                 │         ┌────────────────────────────┐
                 │         │  7. Return Success         │
                 │         │  {                         │
                 │         │    "pending_id": xyz,      │
                 │         │    "status": "awaiting_    │
                 │         │              confirmation",│
                 │         │    "metadata_preview": {   │
                 │         │      "title": "...",       │
                 │         │      "authors": [...],     │
                 │         │      "publisher": "..."    │
                 │         │    }                       │
                 │         │  }                         │
                 │         └────────────────────────────┘
                 │
                 └─── Failed ───────────┐
                                        │
                                        ▼
                         ┌────────────────────────────┐
                         │  5. Update Pending Entry   │
                         │  UPDATE pending_catalogue  │
                         │  SET status = 'failed'     │
                         │  WHERE id = pending_id     │
                         └────────┬───────────────────┘
                                  │
                                  ▼
                         ┌────────────────────────────┐
                         │  6. Create Audit Log       │
                         │  action = 'metadata_       │
                         │           extraction_      │
                         │           failed'          │
                         └────────┬───────────────────┘
                                  │
                                  ▼
                         ┌────────────────────────────┐
                         │  7. Return Partial Success │
                         │  {                         │
                         │    "pending_id": xyz,      │
                         │    "status": "failed",     │
                         │    "message": "Metadata    │
                         │               extraction   │
                         │               failed."     │
                         │  }                         │
                         └────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│              STEP 2: LIBRARIAN VIEWS PENDING BOOKS                   │
│              GET /catalogue/pending                                  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  1. Query Database                     │
        │  SELECT * FROM pending_catalogue       │
        │  WHERE status IN ('awaiting_           │
        │                    confirmation',      │
        │           'Metadata_extraction_failed')│
        │  ORDER BY created_at ASC               │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  2. Return List                        │
        │  [                                     │
        │    {                                   │
        │      "id": xyz,                        │
        │      "isbn": "9780132350884",          │
        │      "title": "Clean Code",            │
        │      "authors": ["Robert C. Martin"],  │
        │      "raw_metadata": {                 │
        │        "publisher": "Prentice Hall",   │
        │        "publication_year": "2008",     │
        │        ...                             │
        │      },                                │
        │      "status": "awaiting_confirmation",│
        │      "created_at": "2025-10-09T14:00"  │
        │    }                                   │
        │  ]                                     │
        └────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│         STEP 3: LIBRARIAN CONFIRMS/REJECTS METADATA                  │
│         POST /catalogue/confirm/{pending_id}                         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  1. Fetch Pending Entry (with lock)    │
        │  SELECT * FROM pending_catalogue       │
        │  WHERE id = pending_id(xyz)                 │
        │  FOR UPDATE                            │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  2. Validate Status                    │
        │  Must be: 'awaiting_confirmation' or   │
        │           'failed'                     │
        └────────┬───────────────────────────────┘
                 │
                 ├─── APPROVED ─────────┐
                 │                      │
                 │                      ▼
                 │         ┌────────────────────────────┐
                 │         │  3. Apply Librarian Edits  │
                 │         │  merged = raw_metadata +   │
                 │         │           edits            │
                 │         └────────┬───────────────────┘
                 │                  │
                 │                  ▼
                 │         ┌────────────────────────────┐
                 │         │  4. Create output_json     │
                 │         │  (finalized metadata)      │
                 │         └────────┬───────────────────┘
                 │                  │
                 │                  ▼
                 │         ┌────────────────────────────┐
                 │         │  5. Update Database        │
                 │         │  UPDATE pending_catalogue  │
                 │         │  SET status = 'approved'   │
                 │         │      output_json = {...}   │
                 │         │  WHERE id = pending_id     │
                 │         └────────┬───────────────────┘
                 │                  │
                 │                  ▼
                 │         ┌────────────────────────────┐
                 │         │  6. Create Audit Log       │
                 │         │  action = 'approved'       │
                 │         │  source = 'librarian'      │
                 │         └────────┬───────────────────┘
                 │                  │
                 │                  ▼
                 │         ┌────────────────────────────┐
                 │         │  7. Return Success         │
                 │         │  {                         │
                 │         │    "status": "approved",   │
                 │         │    "output_json": {...}    │
                 │         │  }                         │
                 │         └────────────────────────────┘
                 │
                 └─── REJECTED ─────────┐
                                        │
                                        ▼
                         ┌────────────────────────────┐
                         │  3. Update Database        │
                         │  UPDATE pending_catalogue  │
                         │  SET status = 'rejected'   │
                         │  WHERE id = pending_id     │
                         └────────┬───────────────────┘
                                  │
                                  ▼
                         ┌────────────────────────────┐
                         │  4. Create Audit Log       │
                         │  action = 'rejected'       │
                         │  source = 'librarian'      │
                         │  details = reason          │
                         └────────┬───────────────────┘
                                  │
                                  ▼
                         ┌────────────────────────────┐
                         │  5. Return Response        │
                         │  {                         │
                         │    "status": "rejected"    │
                         │  }                         │
                         └────────────────────────────┘


┌─────────────────────────────────────────────────────────────────────┐
│           STEP 4: INSERT INTO MAIN CATALOGUE                         │
│           POST /catalogue/insert/{pending_id}                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌────────────────────────────────────────┐
        │  1. Fetch & Lock Pending Entry         │
        │  SELECT * FROM pending_catalogue       │
        │  WHERE id = pending_id                 │
        │  FOR UPDATE                            │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  2. Validate Status                    │
        │  Must be: 'approved'                   │
        │  (Idempotent: if 'completed', return)  │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  3. Extract & Normalize Metadata       │
        │  Source: output_json                   │
        │  ├─ Normalize ISBNs                    │
        │  ├─ Extract title (required)           │
        │  └─ Extract authors, publisher         │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  4. Upsert Publisher                   │
        │  INSERT INTO publishers                │
        │  ON CONFLICT (name) DO NOTHING         │
        │  RETURNING publisher_id                │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  5. Upsert Authors                     │
        │  FOR EACH author:                      │
        │    INSERT INTO authors                 │
        │    ON CONFLICT (full_name) DO NOTHING  │
        │  Collect author_ids                    │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  6. Check if Book Exists               │
        │  SELECT * FROM books                   │
        │  WHERE isbn_13 = '...'                 │
        │     OR isbn_10 = '...'                 │
        └────────┬───────────────────────────────┘
                 │
                 ├─── EXISTS ────────────┐
                 │                       │
                 │                       ▼
                 │         ┌─────────────────────────────┐
                 │         │  7A. Add Copies             │
                 │         │  UPDATE books               │
                 │         │  SET total_copies += N      │
                 │         │      available_copies += N  │
                 │         │  WHERE book_id = X          │
                 │         └─────────┬───────────────────┘
                 │                   │
                 │                   ▼
                 │         ┌─────────────────────────────┐
                 │         │  8A. Create Audit Log       │
                 │         │  action = 'copies_added'    │
                 │         └─────────┬───────────────────┘
                 │                   │
                 │                   └──────┐
                 │                          │
                 └─── NEW BOOK ─────────┐   │
                                        │   │
                                        ▼   │
                         ┌──────────────────────────────┐
                         │  7B. Insert New Book         │
                         │  INSERT INTO books           │
                         │  (isbn, isbn_10, isbn_13,    │
                         │   title, publisher_id, ...)  │
                         │  RETURNING book_id           │
                         └──────────┬───────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────────────┐
                         │  8B. Link Authors            │
                         │  FOR EACH author_id:         │
                         │    INSERT INTO book_authors  │
                         │    (book_id, author_id)      │
                         └──────────┬───────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────────────┐
                         │  9B. Create Audit Log        │
                         │  action = 'inserted'         │
                         └──────────┬───────────────────┘
                                    │
                                    └──────┐
                                           │
                                           ▼
        ┌────────────────────────────────────────────────┐
        │  9. Mark Pending as Completed                  │
        │  UPDATE pending_catalogue                      │
        │  SET status = 'completed'                      │
        │  WHERE id = pending_id                         │
        └────────┬───────────────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  10. Create Final Audit Log            │
        │  action = 'pending_completed'          │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  11. COMMIT Transaction                │
        └────────┬───────────────────────────────┘
                 │
                 ▼
        ┌────────────────────────────────────────┐
        │  12. Return Success                    │
        │  {                                     │
        │    "message": "Book inserted",         │
        │    "pending_id": xyz,                  │
        │    "book_id": abc,                     │
        │    "status": "completed"               │
        │  }                                     │
        └────────────────────────────────────────┘
```

---

## 📊 **Database State Transitions**

### **pending_catalogue.status Lifecycle**

```
┌─────────┐
│ pending │  ← Initial state after POST /catalogue/add
└────┬────┘
     │
     ├─── Metadata extraction succeeds ───┐
     │                                    │
     ▼                                    │
┌──────────────────────┐                 │
│ awaiting_confirmation│ ◄───────────────┘
└────┬─────────────────┘
     │
     ├─── Librarian approves ───┐
     │                           │
     ▼                           │
┌──────────┐                    │
│ approved │ ◄──────────────────┘
└────┬─────┘
     │
     ├─── Insertion succeeds ───┐
     │                           │
     ▼                           │
┌───────────┐                   │
│ completed │ ◄─────────────────┘
└───────────┘

Alternative paths:

┌─────────┐
│ pending │
└────┬────┘
     │
     ├─── Metadata extraction fails ───┐
     │                                  │
     ▼                                  │
┌────────┐                             │
│ failed │ ◄───────────────────────────┘
└────┬───┘
     │
     └─── Librarian can manually enter data
          and approve → 'approved'

┌──────────────────────┐
│ awaiting_confirmation│
└────┬─────────────────┘
     │
     ├─── Librarian rejects ───┐
     │                          │
     ▼                          │
┌──────────┐                   │
│ rejected │ ◄─────────────────┘
└──────────┘
```

### **Valid Status Transitions**

| From | To | Trigger | Action |
|------|-----|---------|--------|
| `pending` | `awaiting_confirmation` | Metadata extracted | Auto |
| `pending` | `failed` | Metadata extraction failed | Auto |
| `awaiting_confirmation` | `approved` | Librarian approves | Manual |
| `awaiting_confirmation` | `rejected` | Librarian rejects | Manual |
| `failed` | `approved` | Librarian manually enters data | Manual |
| `approved` | `completed` | Book inserted successfully | Auto |

---

## ⚠️ **Error Handling**

### **Metadata Extraction Failures**

**Scenario:** External APIs (Open Library, Google Books) fail or return no results

**Behavior:**
1. Pending entry is still created with `status='failed'`
2. Audit log records `action='metadata_extraction_failed'`
3. Response indicates failure but provides `pending_id`
4. Librarian can manually enter metadata and approve

**Example Response:**
```json
{
  "message": "Book added but metadata extraction failed. Please enter manually.",
  "pending_id": 123,
  "status": "failed",
  "metadata_preview": null
}
```

### **Validation Errors**

**Scenario:** Invalid input (bad ISBN format, missing required fields)

**Behavior:**
1. Request rejected with HTTP 400
2. No database entry created
3. Clear error message returned

**Example Response:**
```json
{
  "detail": "ISBN must be exactly 10 or 13 digits"
}
```

### **Database Errors**

**Scenario:** Database connection failure, constraint violation

**Behavior:**
1. Transaction rolled back
2. HTTP 500 returned
3. Error logged for debugging
4. No partial state left in database

### **Insertion Failures**

**Scenario:** Book insertion fails (missing required data, constraint violation)

**Behavior:**
1. Transaction rolled back
2. Pending entry remains in `approved` state
3. Audit log records `action='insert_failed'` with error details
4. Can be retried (idempotent)

---

## 📝 **Audit Trail**

Every action in the workflow is logged to `catalogue_audit` table for complete traceability.

### **Audit Actions**

| Action | Source | When | Details |
|--------|--------|------|---------|
| `input_received` | `frontend` | Book added | Initial request data |
| `metadata_extracted` | `metadata_pipeline` | APIs succeed | Source API used |
| `metadata_extraction_failed` | `metadata_pipeline` | APIs fail | Error message |
| `approved` | `librarian` | Librarian approves | Edits applied |
| `rejected` | `librarian` | Librarian rejects | Rejection reason |
| `inserted` | `insertion_service` | New book created | book_id, ISBN, title |
| `copies_added` | `insertion_service` | Existing book updated | book_id, copies added |
| `pending_completed` | `insertion_service` | Process complete | Final book_id |
| `insert_failed` | `insertion_service` | Insertion error | Error details |

### **Querying Audit Logs**

```sql
-- Get complete history for a pending entry
SELECT action, source, details, timestamp
FROM lms_core.catalogue_audit
WHERE book_id = 123
ORDER BY timestamp ASC;

-- Count books processed today
SELECT COUNT(DISTINCT book_id)
FROM lms_core.catalogue_audit
WHERE action = 'pending_completed'
  AND timestamp >= CURRENT_DATE;

-- Find failed insertions
SELECT book_id, details, timestamp
FROM lms_core.catalogue_audit
WHERE action = 'insert_failed'
ORDER BY timestamp DESC
LIMIT 10;
```

---

## 🎯 **Summary**

**Workflow Characteristics:**
- ✅ **4-Step Process**: Add → Review → Confirm → Insert
- ✅ **Automatic Metadata**: Fetched from Open Library + Google Books
- ✅ **Human Oversight**: Librarian reviews and edits before final insertion
- ✅ **Fault Tolerant**: Handles API failures gracefully
- ✅ **Fully Audited**: Every action logged with timestamp
- ✅ **Idempotent**: Safe to retry any step
- ✅ **Transactional**: No partial state on errors

**Next Steps:**
- See [API_ENDPOINTS.md](API_ENDPOINTS.md) for detailed API documentation, frontend integration guidance, and all workflow endpoint details

---

**For Questions or Issues:**
- Check audit logs: `GET /catalogue/audit/{pending_id}`
- Review application logs
- Run tests: `pytest tests/ -v`
