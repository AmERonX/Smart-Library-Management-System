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

### **3. Confirm/Reject Book Metadata**

**Endpoint:** `POST /catalogue/confirm/{pending_id}`

**Description:** Librarian approves or rejects book metadata after review.

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pending_id` | integer | Yes | ID of pending catalogue entry |

**Request Body (Approve):**
```json
{
  "approved": true,
  "edits": {
    "publisher": "Prentice Hall PTR",
    "publication_year": "2008",
    "edition": "1st Edition"
  },
  "reason": "Verified metadata with library records"
}
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
| `edits` | object | No | Dictionary of field corrections (only if approved) |
| `reason` | string | No* | Reason for approval/rejection |

*Required if `approved=false`

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
    "edition": "1st Edition",
    "total_copies": 3,
    "source": "librarian_confirmed"
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

### **4. Insert Approved Book into Catalogue**

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
| `/catalogue/confirm/{id}` | POST | Approve/reject metadata | No |
| `/catalogue/insert/{id}` | POST | Insert into catalogue | No |
| `/catalogue/audit/{id}` | GET | Get audit logs | No |

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

# Step 3: Approve metadata
curl -X POST "http://localhost:8000/catalogue/confirm/$PENDING_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "approved": true,
    "edits": {
      "publisher": "Prentice Hall",
      "publication_year": "2008"
    },
    "reason": "Verified"
  }'

# Step 4: Insert into catalogue
curl -X POST "http://localhost:8000/catalogue/insert/$PENDING_ID"

# Step 5: View audit trail
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
- **Insertion Service**: [INSERTION_SERVICE_README.md](INSERTION_SERVICE_README.md)
- **Librarian Confirmation**: [LIBRARIAN_CONFIRMATION_README.md](LIBRARIAN_CONFIRMATION_README.md)
- **Testing Guide**: [TESTING_GUIDE.md](TESTING_GUIDE.md)

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
