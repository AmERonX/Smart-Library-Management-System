# Smart Library Management System - API Endpoints

**Version:** 2.0  
**Last Updated:** 2025-10-09  
**Base URL:** `http://localhost:8000`

---

## 📋 **Table of Contents**

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Catalogue Management](#catalogue-management)
4. [Book Insertion](#book-insertion)
5. [Audit & Monitoring](#audit--monitoring)
6. [Health & Status](#health--status)
7. [Error Responses](#error-responses)

---

## 🎯 **Overview**

The SLMS API provides RESTful endpoints for managing library book cataloguing with librarian confirmation workflow.

**Key Features:**
- ✅ Automatic metadata extraction from Open Library & Google Books
- ✅ Librarian review and approval workflow
- ✅ Complete audit trail
- ✅ ISBN-aware book management (ISBN-10 & ISBN-13)
- ✅ Idempotent operations

**API Documentation:**
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🔐 **Authentication**

**Current Status:** No authentication required (development mode)

**Future:** Will implement JWT-based authentication for production:
- Librarian role: Full access
- Staff role: Add books only
- Admin role: All operations + user management

---

## 📚 **Catalogue Management**

### **1. Add Book to Pending Catalogue**

**Endpoint:** `POST /catalogue/add`

**Description:** Add a book with automatic metadata extraction from external APIs.

**Request Body:**
```json
{
  "isbn": "9780132350884",
  "title": "Clean Code",
  "authors": ["Robert C. Martin"],
  "total_copies": 3
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `isbn` | string | No* | ISBN-10 or ISBN-13 (10 or 13 digits) |
| `title` | string | Yes | Book title |
| `authors` | array[string] | No | List of author names |
| `total_copies` | integer | No | Number of copies (default: 1, min: 1) |

*Either `isbn` or `title` must be provided.

**Success Response (201 Created):**
```json
{
  "message": "Book added to pending catalogue successfully",
  "pending_id": 123,
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

**Partial Success Response (201 Created - Metadata Failed):**
```json
{
  "message": "Book added but metadata extraction failed. Please enter manually.",
  "pending_id": 124,
  "status": "failed",
  "metadata_preview": null
}
```

**Error Responses:**
- `400 Bad Request`: Invalid ISBN format or missing required fields
- `500 Internal Server Error`: Database error

**Example cURL:**
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

**Workflow:**
1. Creates pending catalogue entry
2. Fetches metadata from Open Library
3. Falls back to Google Books if needed
4. Updates entry with metadata
5. Returns preview for librarian review

---

### **2. Get Pending Books**

**Endpoint:** `GET /catalogue/pending`

**Description:** Retrieve all books awaiting librarian confirmation.

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skip` | integer | No | 0 | Number of records to skip (pagination) |
| `limit` | integer | No | 50 | Maximum records to return |

**Success Response (200 OK):**
```json
[
  {
    "id": 123,
    "isbn": "9780132350884",
    "title": "Clean Code",
    "authors": ["Robert C. Martin"],
    "total_copies": 3,
    "raw_metadata": {
      "isbn_10": "0132350882",
      "isbn_13": "9780132350884",
      "publisher": "Prentice Hall",
      "publication_year": "2008",
      "description": "A handbook of agile software craftsmanship...",
      "source": "google_books"
    },
    "output_json": null,
    "status": "awaiting_confirmation",
    "created_at": "2025-10-09T14:30:00Z",
    "updated_at": null
  }
]
```

**Error Responses:**
- `500 Internal Server Error`: Database query failed

**Example cURL:**
```bash
curl -X GET "http://localhost:8000/catalogue/pending?skip=0&limit=20"
```

**Use Case:** Librarian dashboard showing books needing review

---

### **3. Get Single Pending Book**

**Endpoint:** `GET /catalogue/pending/{pending_id}`

**Description:** Fetch a single pending entry by ID.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pending_id` | integer | Yes | ID of pending catalogue entry |

**Success Response (200 OK):** Same shape as items in `GET /catalogue/pending`.

**Error Responses:**
- `404 Not Found`: Pending entry not found

---

### **4. Edit Pending Book (Pre-Approval)**

**Endpoint:** `PATCH /catalogue/pending/{pending_id}`

**Description:** Save librarian edits before approval. Updates the pending record's `raw_metadata` and mirrors select fields (title, authors, isbn*, total_copies).

**Request Body (examples):**
```json
{ "raw_metadata": { "publisher": "Prentice Hall PTR", "edition": "1st" } }
```
```json
{ "book_copies": 2 }
```

Notes:
- Accepts either `total_copies` or `book_copies` (alias). Minimum is 1.
- Allowed when status is `awaiting_confirmation` or `failed`.

**Success Response (200 OK):** Updated pending entry.

**Error Responses:**
- `400 Bad Request`: Invalid status or `total_copies < 1`
- `404 Not Found`: Pending entry not found

---

### **5. Confirm/Reject Book Metadata**

**Endpoint:** `POST /catalogue/confirm/{pending_id}`

**Description:** Librarian approves or rejects book metadata after review.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pending_id` | integer | Yes | ID of pending catalogue entry |

**Request Body (Approve):**
```json
{ "approved": true, "reason": "Verified metadata with library records" }
```

**Request Body (Reject):**
```json
{
  "approved": false,
  "reason": "Incorrect book - wrong ISBN"
}
```

**Request Schema:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `approved` | boolean | Yes | True to approve, false to reject |
| `reason` | string | No* | Reason for approval/rejection |

*Required if `approved=false`.

Edits are no longer accepted at confirmation time. Use `PATCH /catalogue/pending/{id}` to make changes before confirming.

**Success Response - Approved (200 OK):**
```json
{
  "message": "Metadata approved successfully",
  "pending_id": 123,
  "status": "approved",
  "output_json": {
    "isbn": "9780132350884",
    "isbn_10": "0132350882",
    "isbn_13": "9780132350884",
    "title": "Clean Code",
    "authors": ["Robert C. Martin"],
    "publisher": "Prentice Hall PTR",
    "publication_year": "2008",
    "edition": "1st",
    "total_copies": 3,
    "source": "librarian_confirmation"
  }
}
```

**Success Response - Rejected (200 OK):**
```json
{
  "message": "Metadata rejected",
  "pending_id": 123,
  "status": "rejected",
  "output_json": null
}
```

**Error Responses:**
- `400 Bad Request`: Invalid status (not awaiting_confirmation)
- `404 Not Found`: Pending entry not found
- `500 Internal Server Error`: Database error

**Example cURL:**
```bash
# Approve with edits
curl -X POST "http://localhost:8000/catalogue/confirm/123" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "edits": {
      "publisher": "Prentice Hall PTR",
      "publication_year": "2008"
    },
    "reason": "Verified and corrected"
  }'

# Reject
curl -X POST "http://localhost:8000/catalogue/confirm/123" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": false,
    "reason": "Incorrect ISBN"
  }'
```

---

## 📦 **Book Insertion**

### **6. Insert Approved Book into Catalogue**

**Endpoint:** `POST /catalogue/insert/{pending_id}`

**Description:** Insert approved pending book into main catalogue. Idempotent operation.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pending_id` | integer | Yes | ID of approved pending catalogue entry |

**Request Body:** None

**Success Response - New Book (200 OK):**
```json
{
  "message": "Book inserted successfully",
  "pending_id": 123,
  "book_id": 456,
  "status": "completed"
}
```

**Success Response - Existing Book (200 OK):**
```json
{
  "message": "Existing book updated with additional copies",
  "pending_id": 123,
  "book_id": 789,
  "status": "completed"
}
```

**Success Response - Already Completed (200 OK):**
```json
{
  "message": "Pending record already completed",
  "pending_id": 123,
  "book_id": 456,
  "status": "completed"
}
```

**Error Responses:**
- `400 Bad Request`: Pending entry not in 'approved' state
- `404 Not Found`: Pending entry not found
- `500 Internal Server Error`: Database error

**Example cURL:**
```bash
curl -X POST "http://localhost:8000/catalogue/insert/123"
```

**Workflow:**
1. Validates pending entry is approved
2. Extracts metadata from output_json
3. Upserts publisher and authors
4. Checks if book exists by ISBN
5. Creates new book OR adds copies to existing
6. Marks pending entry as completed
7. Logs complete audit trail

**Idempotency:** Safe to call multiple times - returns success if already completed.

---

## 📚 **Books Catalogue**

### **7. List Books**

**Endpoint:** `GET /books`

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number |
| `page_size` | integer | No | 20 | Items per page (max 100) |
| `q` | string | No | — | Title substring (case-insensitive) |
| `author` | string | No | — | Author substring (case-insensitive) |
| `publisher` | string | No | — | Publisher substring (case-insensitive) |
| `year` | string | No | — | Exact publication year |
| `year_from` | string | No | — | Start year (inclusive) |
| `year_to` | string | No | — | End year (inclusive) |
| `sort` | string | No | created_desc | One of: created_desc, title_asc, year_asc, year_desc |

**Success Response (200 OK):**
```json
{
  "total": 1,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "book_id": 456,
      "title": "Clean Code",
      "authors": ["Robert C. Martin"],
      "publisher": "Prentice Hall",
      "publication_year": "2008",
      "available_copies": 5,
      "cover_url": "https://..."
    }
  ]
}
```

---

### **8. Get Book Detail**

**Endpoint:** `GET /books/{book_id}`

**Success Response (200 OK):**
```json
{
  "book_id": 456,
  "title": "Clean Code",
  "isbn": null,
  "isbn_10": "0132350882",
  "isbn_13": "9780132350884",
  "publication_year": "2008",
  "edition": null,
  "cover_url": "https://...",
  "total_copies": 5,
  "available_copies": 5,
  "publisher": { "publisher_id": 7, "name": "Prentice Hall" },
  "authors": [{ "author_id": 3, "full_name": "Robert C. Martin" }],
  "enhanced_metadata": { }
}
```

---

## 📊 **Audit & Monitoring**

### **5. Get Audit Logs**

**Endpoint:** `GET /catalogue/audit/{pending_id}`

**Description:** Retrieve complete audit trail for a pending catalogue entry.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pending_id` | integer | Yes | ID of pending catalogue entry |

**Success Response (200 OK):**
```json
{
  "message": "Audit logs retrieved successfully",
  "pending_id": 123,
  "total_entries": 5,
  "audit_logs": [
    {
      "id": 1,
      "book_id": 123,
      "action": "input_received",
      "source": "frontend",
      "details": "Book added: Clean Code",
      "timestamp": "2025-10-09T14:30:00Z"
    },
    {
      "id": 2,
      "book_id": 123,
      "action": "metadata_extracted",
      "source": "metadata_pipeline",
      "details": "Source: google_books",
      "timestamp": "2025-10-09T14:30:05Z"
    },
    {
      "id": 3,
      "book_id": 123,
      "action": "approved",
      "source": "librarian",
      "details": "Verified and corrected",
      "timestamp": "2025-10-09T14:35:00Z"
    },
    {
      "id": 4,
      "book_id": 123,
      "action": "inserted",
      "source": "insertion_service",
      "details": "{\"book_id\": 456, \"title\": \"Clean Code\"}",
      "timestamp": "2025-10-09T14:36:00Z"
    },
    {
      "id": 5,
      "book_id": 123,
      "action": "pending_completed",
      "source": "insertion_service",
      "details": "{\"book_id\": 456}",
      "timestamp": "2025-10-09T14:36:01Z"
    }
  ]
}
```

**Error Responses:**
- `404 Not Found`: Pending entry not found
- `500 Internal Server Error`: Database query failed

**Example cURL:**
```bash
curl -X GET "http://localhost:8000/catalogue/audit/123"
```

**Audit Actions:**
- `input_received`: Initial book addition
- `metadata_extracted`: Successful API fetch
- `metadata_extraction_failed`: API fetch failed
- `approved`: Librarian approved
- `rejected`: Librarian rejected
- `inserted`: New book created
- `copies_added`: Copies added to existing book
- `pending_completed`: Process completed
- `insert_failed`: Insertion error

---

## 🏥 **Health & Status**

### **6. Root Endpoint**

**Endpoint:** `GET /`

**Description:** Basic service information.

**Success Response (200 OK):**
```json
{
  "service": "Smart Library Management System (SLMS)",
  "version": "2.0.0",
  "status": "operational",
  "features": [
    "Metadata Extraction (Open Library, Google Books)",
    "Librarian Confirmation Workflow",
    "Audit Logging"
  ]
}
```

**Example cURL:**
```bash
curl -X GET "http://localhost:8000/"
```

---

### **7. Health Check**

**Endpoint:** `GET /health`

**Description:** Check service and external API connectivity.

**Success Response (200 OK):**
```json
{
  "service": "operational",
  "apis": {
    "open_library": "reachable",
    "google_books": "reachable"
  }
}
```

**Degraded Response (200 OK):**
```json
{
  "service": "operational",
  "apis": {
    "open_library": "unreachable",
    "google_books": "reachable"
  }
}
```

**Example cURL:**
```bash
curl -X GET "http://localhost:8000/health"
```

**Use Case:** Monitoring and alerting systems

---

## ⚠️ **Error Responses**

### **Standard Error Format**

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### **HTTP Status Codes**

| Code | Meaning | When |
|------|---------|------|
| `200` | OK | Successful request |
| `201` | Created | Resource created successfully |
| `400` | Bad Request | Invalid input or validation error |
| `404` | Not Found | Resource not found |
| `500` | Internal Server Error | Server-side error |

### **Common Error Examples**

**400 Bad Request - Invalid ISBN:**
```json
{
  "detail": "ISBN must be exactly 10 or 13 digits"
}
```

**400 Bad Request - Invalid Status:**
```json
{
  "detail": "Pending record must be 'approved' to insert. Currently: pending"
}
```

**404 Not Found:**
```json
{
  "detail": "Pending catalogue entry not found: 999"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Internal server error during book insertion"
}
```

---

## 📝 **Complete API Summary**

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/` | GET | Service info | No |
| `/health` | GET | Health check | No |
| `/catalogue/add` | POST | Add book with metadata | No |
| `/catalogue/pending` | GET | List pending books | No |
| `/catalogue/pending/{id}` | GET | Get single pending entry | No |
| `/catalogue/pending/{id}` | PATCH | Save edits before approval | No |
| `/catalogue/confirm/{id}` | POST | Approve/reject metadata (finalize from saved edits) | No |
| `/catalogue/insert/{id}` | POST | Insert into catalogue | No |
| `/catalogue/audit/{id}` | GET | Get audit logs | No |
| `/books` | GET | List books with filters | No |
| `/books/{book_id}` | GET | Book detail | No |

---

## 🧭 User-Facing Endpoints (Student)

This section documents endpoints used by students/end-users to search, borrow, reserve, return, and view account data. Items marked as Planned indicate endpoints inferred from the database schema that are not yet implemented in the codebase.

### 🔍 9. Semantic Search (Existing)

- Endpoint: `POST /search/semantic`
- Description: Vector-based semantic search over the catalogue with optional normalization and query expansion.
- Request Body example:
  ```json
  {
    "query": "machine learning for beginners",
    "normalize": true,
    "expand": false,
    "mode": "best_of", 
    "top_k": 10
  }
  ```
- Success Response (200 OK):
  ```json
  {
    "query_raw": "machine learning for beginners",
    "query_processed": "machine learning for beginners",
    "mode": "best_of",
    "results": [
      { "book_id": 123, "title": "...", "authors": ["..."], "publisher": "...", "publication_year": "2021", "score": 0.87, "vector_type": "topical" }
    ]
  }
  ```

### 🔎 10. Classic Search (Planned)

- Endpoint: `POST /books/search`
- Description: Keyword/fielded search (title, author, publisher, years) with pagination and sort; complements semantic search.
- Request Body example:
  ```json
  {
    "q": "data structures",
    "author": "Cormen",
    "publisher": "MIT",
    "year": null,
    "year_from": "2000",
    "year_to": "2025",
    "page": 1,
    "page_size": 20,
    "sort": "created_desc"
  }
  ```
- Response: Same shape as `GET /books` list.

### 📚 11. Catalogue Helpers (Planned)

- `GET /books/{book_id}/availability`
  - Description: Returns `available_copies` and derived `status` for a book.
  - Response example:
    ```json
    { "book_id": 456, "available_copies": 2, "status": "available" }
    ```
- `GET /books/{book_id}/metadata`
  - Description: Returns extended metadata from `book_metadata` (description, toc, keywords).
  - Response example:
    ```json
    { "book_id": 456, "description": "...", "toc": "...", "keywords": ["...", "..."] }
    ```
- `GET /categories`
  - Description: List categories for browsing and filtering.
- `GET /authors`
  - Description: List authors (with optional filtering and pagination).

### 📖 12. Borrowing (Planned)

- `POST /borrows`
  - Description: Borrow a book. Uses concurrency-safe stored function `borrow_book(user_id, book_id, due_date)`; if no copies, auto-creates a reservation.
  - Request body:
    ```json
    { "book_id": 456, "due_date": "2025-11-30T23:59:59Z" }
    ```
  - Response examples:
    ```json
    { "success": true, "borrow_id": 789, "reserved": false }
    ```
    ```json
    { "success": false, "reserved": true }
    ```
- `GET /borrows/active`
  - Description: List current borrows for the authenticated user (`return_date IS NULL`).
- `GET /borrows/history`
  - Description: Full borrowing history for the user.
- `POST /borrows/{borrow_id}/renew`
  - Description: Extend due date if eligible (policy-controlled).
  - Request body:
    ```json
    { "new_due_date": "2025-12-15T23:59:59Z" }
    ```

### 🔄 13. Returns (Planned)

- `POST /borrows/{borrow_id}/return`
  - Description: Return a borrowed book; sets `return_date=NOW()` and increments `books.available_copies`. May create a fine via trigger if overdue.
  - Response example:
    ```json
    { "success": true, "fine_created": false }
    ```

### 📌 14. Reservations (Planned)

- `POST /reservations`
  - Description: Create reservation for a book when unavailable. Enforced uniqueness per user/book by partial unique index.
  - Request body:
    ```json
    { "book_id": 456 }
    ```
- `GET /reservations/active`
  - Description: List active reservations for the user.
- `DELETE /reservations/{reservation_id}`
  - Description: Cancel reservation (sets status to `cancelled`).
- `POST /reservations/{reservation_id}/fulfill`
  - Description: Mark as fulfilled when copy becomes available (typically coordinated with a borrow operation).

### 💳 15. Fines (Planned)

- `GET /fines`
  - Description: List fines for the user with status and amounts.
- `POST /fines/{fine_id}/pay`
  - Description: Mark fine as paid; sets `status='paid'` and `paid_date=NOW()`.

### 👤 16. User Account (Planned)

- `GET /me`
  - Description: Basic profile for the authenticated user.
- `GET /me/summary`
  - Description: Dashboard: counts of active borrows, active reservations, pending fines.

Notes:
- Planned endpoints are derived from tables: `borrow_records`, `reservations`, `fines`, `book_metadata`, `categories`, and `authors` in the schema (lms_core).
- Book status consistency is handled by DB triggers; APIs should update `available_copies` and let triggers manage `books.status`.
- Reservation uniqueness: conflicts should return `409 Conflict` using the partial unique index on `(user_id, book_id)` where `status='active'`.

---

## 🚀 **Usage Examples**

### **Complete Workflow Example**

```bash
# Step 1: Add book
RESPONSE=$(curl -s -X POST "http://localhost:8000/catalogue/add" \
  -H "Content-Type: application/json" \
  -d '{
    "isbn": "9780132350884",
    "title": "Clean Code",
    "authors": ["Robert C. Martin"],
    "total_copies": 3
  }')

PENDING_ID=$(echo $RESPONSE | jq -r '.pending_id')
echo "Created pending entry: $PENDING_ID"

# Step 2: Get pending books (librarian view)
curl -X GET "http://localhost:8000/catalogue/pending"

# Step 3: Save librarian edits before approval (optional)
curl -X PATCH "http://localhost:8000/catalogue/pending/$PENDING_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_metadata": { "publisher": "Prentice Hall", "publication_year": "2008" },
    "book_copies": 2
  }'

# Step 4: Approve metadata (finalize from saved metadata)
curl -X POST "http://localhost:8000/catalogue/confirm/$PENDING_ID" \
  -H "Content-Type: application/json" \
  -d '{ "approved": true, "reason": "Verified" }'

# Step 5: Insert into catalogue
curl -X POST "http://localhost:8000/catalogue/insert/$PENDING_ID"

# Step 6: View audit trail
curl -X GET "http://localhost:8000/catalogue/audit/$PENDING_ID"
```

### **Python Example**

```python
import requests

BASE_URL = "http://localhost:8000"

# Add book
response = requests.post(
    f"{BASE_URL}/catalogue/add",
    json={
        "isbn": "9780132350884",
        "title": "Clean Code",
        "authors": ["Robert C. Martin"],
        "total_copies": 3
    }
)
pending_id = response.json()["pending_id"]
print(f"Pending ID: {pending_id}")

# Approve
response = requests.post(
    f"{BASE_URL}/catalogue/confirm/{pending_id}",
    json={
        "approved": True,
        "edits": {"publisher": "Prentice Hall"},
        "reason": "Verified"
    }
)
print(f"Status: {response.json()['status']}")

# Insert
response = requests.post(f"{BASE_URL}/catalogue/insert/{pending_id}")
book_id = response.json()["book_id"]
print(f"Book ID: {book_id}")
```

---

## 🔧 **Configuration**

### **Environment Variables**

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/slms
LOG_LEVEL=INFO
REQUEST_TIMEOUT=5
ENABLE_OPENLIBRARY=true
ENABLE_GOOGLEBOOKS=true
```

## 🧩 **Frontend Integration Overview**

For browser-based UIs:

- Enable CORS in `main.py` (FastAPI `CORSMiddleware`).
- Paginate large lists (e.g., pending catalogue) to avoid heavy payloads.
- Standardize error responses (`schemas.ErrorResponse`).
- Consider auth (API key or JWT) before production.

Client generation: use `openapi.json` with openapi-typescript-codegen to create a typed client.

### **API Rate Limits**

**External APIs:**
- Open Library: No strict limits (be respectful)
- Google Books: 1000 requests/day (unauthenticated)

**SLMS API:**
- No rate limits currently (development mode)
- Production: Will implement per-user rate limiting

---

## 📚 **Additional Resources**

- **Workflow Documentation**: [WORKFLOW.md](WORKFLOW.md)
- **Setup Guide**: [SETUP_GUIDE.md](SETUP_GUIDE.md)

---

## 🆘 **Support**

**For Issues:**
1. Check audit logs: `GET /catalogue/audit/{pending_id}`
2. Review application logs
3. Verify database state
4. Run tests: `pytest tests/ -v`

**Common Issues:**
- **Metadata extraction fails**: Check external API connectivity with `/health`
- **Insertion fails**: Verify pending entry is in 'approved' status
- **Duplicate ISBN**: Book already exists, will add copies instead

---

**Last Updated:** 2025-10-09  
**API Version:** 2.0  
**Maintained by:** SLMS Development Team
