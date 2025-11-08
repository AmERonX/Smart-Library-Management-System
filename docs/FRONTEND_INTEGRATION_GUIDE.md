# Frontend Integration Guide - Librarian Admin UI

**Document Version:** 1.0  
**Last Updated:** 2025-10-10  
**Status:** Ready for Implementation

---

## 📋 **Implementation Checklist**

Track your progress as you implement features for frontend integration:

### **🔴 Critical Requirements (Must Implement Before Frontend)**
- [PENDING] **CORS Configuration** - Enable browser-based API calls (5 min)
- [PENDING] **Pagination** - Add pagination to `/catalogue/pending` endpoint (30 min)
- [PENDING] **Authentication** - Implement API Key or JWT authentication (2-4 hrs)
- [PENDING] **Error Standardization** - Consistent error response format (1 hr)

### **🟡 High Priority Enhancements **
- [PENDING] **Search & Filter** - Add search/filter to pending books (1-2 hrs)
- [PENDING] **Book Management** - CRUD for main catalogue (view, edit, delete books)
- [PENDING] **Dashboard Stats** - Create statistics endpoint for overview (1 hr)

### **🟢 Medium Priority Enhancements **
- [PENDING] **Bulk Operations** - Approve/reject multiple books at once (1 hr)
- [PENDING] **Update/Delete Pending** - Edit pending entries before confirmation (1 hr)
- [PENDING] **Book Management** - CRUD endpoints for main catalogue (3-4 hrs)
- [PENDING] **File Upload** - Upload cover images (1 hr)

### **🔵 Low Priority Enhancements **
- [PENDING] **Export Functionality** - Export to CSV/JSON (1 hr)
- [PENDING] **WebSocket Notifications** - Real-time updates (2-3 hrs)

### **📝 Documentation & Testing**
- [PENDING] Update API documentation with new endpoints
- [PENDING] Write unit tests for new features
- [PENDING] Create Postman/Insomnia collection
- [PENDING] Update README with new features

### **🚀 Deployment Preparation**
- [PENDING] Configure production environment variables
- [PENDING] Set up HTTPS/SSL certificates
- [PENDING] Enable API rate limiting
- [PENDING] Configure database backups
- [PENDING] Set up monitoring and loggingg

---

## 📋 **Executive Summary**

The SLMS backend is **production-ready** with a complete librarian confirmation workflow. However, several enhancements are needed for optimal frontend integration. This document outlines critical requirements and recommended improvements.

---

## ✅ **Current State - What's Ready**

### **1. Complete RESTful API**
- ✅ Well-structured endpoints with clear request/response schemas
- ✅ Comprehensive validation via Pydantic models
- ✅ Detailed error responses with proper HTTP status codes (400, 404, 500)
- ✅ Interactive API documentation at `/docs` (Swagger UI)
- ✅ Alternative docs at `/redoc` (ReDoc)

### **2. Librarian Workflow Endpoints**
All core endpoints are implemented and tested:

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/catalogue/add` | POST | Add book with auto-metadata extraction | ✅ Ready |
| `/catalogue/pending` | GET | List all pending books for review | ✅ Ready |
| `/catalogue/confirm/{pending_id}` | POST | Approve/reject with optional edits | ✅ Ready |
| `/catalogue/insert/{pending_id}` | POST | Insert approved book into main catalogue | ✅ Ready |
| `/catalogue/audit/{pending_id}` | GET | View complete audit trail | ✅ Ready |
| `/health` | GET | Health check for monitoring | ✅ Ready |
| `/` | GET | Service information | ✅ Ready |

### **3. Data Structure & Quality**
- ✅ Rich metadata in responses (title, authors, publisher, ISBN, etc.)
- ✅ Status tracking (pending → awaiting_confirmation → approved → completed → failed)
- ✅ Complete audit logging for accountability
- ✅ Transaction safety with rollback on errors
- ✅ Idempotent operations (safe to retry)

### **4. Database Schema**
- ✅ PostgreSQL with proper schema (`lms_core`)
- ✅ Normalized tables (books, authors, publishers, book_authors)
- ✅ Pending catalogue table with JSON metadata storage
- ✅ Audit trail table with timestamps
- ✅ ISBN-10 and ISBN-13 support

---

## 🚨 **Critical Requirements - Must Implement**

### **1. CORS Configuration** ⭐ **HIGHEST PRIORITY**
**Problem:** Browser-based frontends cannot communicate with the API due to CORS restrictions.

**Solution:**
```python
# Add to main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React/Vite dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production Configuration:**
```python
# Use environment variable for production
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)
```

**Impact:** Without this, frontend cannot make API calls.  
**Effort:** 5 minutes  
**Priority:** 🔴 **CRITICAL**

---

### **2. Pagination for `/catalogue/pending`** ⭐
**Problem:** Returns all pending books in a single response. Will cause performance issues with 100+ pending books.

**Solution:**
```python
@router.get("/pending", response_model=PaginatedPendingResponse)
async def get_pending_books(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """Get paginated list of pending books."""
    query = db.query(PendingCatalogue)
    
    # Apply filters
    if status:
        query = query.filter(PendingCatalogue.status == status)
    else:
        query = query.filter(PendingCatalogue.status.in_(['awaiting_confirmation', 'failed']))
    
    # Count total
    total = query.count()
    
    # Paginate
    offset = (page - 1) * page_size
    items = query.order_by(PendingCatalogue.created_at.desc()).offset(offset).limit(page_size).all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
```

**Impact:** Prevents UI slowdown with large datasets.  
**Effort:** 30 minutes  
**Priority:** 🔴 **CRITICAL**

---

### **3. Authentication & Authorization** ⭐
**Problem:** No librarian login system. Anyone can approve/reject books.

**Solution Options:**

**Option A: Simple API Key (Quick Start)**
```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key != os.getenv("LIBRARIAN_API_KEY"):
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

# Apply to endpoints
@router.post("/confirm/{pending_id}", dependencies=[Depends(verify_api_key)])
async def confirm_book_metadata(...):
    ...
```

**Option B: JWT-Based Authentication (Recommended)**
```python
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

# Implement:
# - POST /auth/login - Returns JWT token
# - POST /auth/register - Create librarian account
# - GET /auth/me - Get current user info
# - Middleware to verify JWT on protected routes
```

**Impact:** Secures the system from unauthorized access.  
**Effort:** 2-4 hours (API Key) or 1-2 days (JWT)  
**Priority:** 🔴 **CRITICAL** (for production)

---

### **4. Error Handling Standardization**
**Problem:** Error responses are inconsistent across endpoints.

**Solution:**
```python
# Add to schemas.py
class ErrorDetail(BaseModel):
    code: str
    message: str
    field: Optional[str] = None

class StandardErrorResponse(BaseModel):
    error: ErrorDetail
    timestamp: datetime
    path: str

# Add global exception handler in main.py
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc)
            },
            "timestamp": datetime.utcnow().isoformat(),
            "path": request.url.path
        }
    )
```

**Impact:** Easier frontend error handling.  
**Effort:** 1 hour  
**Priority:** 🟡 **HIGH**

---

## 🔧 **Recommended Enhancements - Should Implement**

### **5. Search & Filter Capabilities**
**Need:** Librarians need to search pending books by title, author, ISBN, or status.

**Implementation:**
```python
@router.get("/pending/search")
async def search_pending_books(
    q: Optional[str] = Query(None, description="Search query (title, author, ISBN)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    date_from: Optional[datetime] = Query(None, description="Filter by creation date"),
    date_to: Optional[datetime] = Query(None, description="Filter by creation date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search and filter pending books."""
    query = db.query(PendingCatalogue)
    
    # Full-text search
    if q:
        search_filter = or_(
            PendingCatalogue.title.ilike(f"%{q}%"),
            PendingCatalogue.isbn.ilike(f"%{q}%"),
            PendingCatalogue.authors.cast(String).ilike(f"%{q}%")
        )
        query = query.filter(search_filter)
    
    # Status filter
    if status:
        query = query.filter(PendingCatalogue.status == status)
    
    # Date range filter
    if date_from:
        query = query.filter(PendingCatalogue.created_at >= date_from)
    if date_to:
        query = query.filter(PendingCatalogue.created_at <= date_to)
    
    # Paginate and return
    total = query.count()
    items = query.order_by(PendingCatalogue.created_at.desc()).offset((page-1)*page_size).limit(page_size).all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }
```

**Impact:** Improves librarian productivity.  
**Effort:** 1-2 hours  
**Priority:** 🟡 **HIGH**

---

### **6. Dashboard & Statistics Endpoint**
**Need:** Librarians need an overview of pending work and system status.

**Implementation:**
```python
@router.get("/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics for librarian UI."""
    
    # Count by status
    pending_count = db.query(PendingCatalogue).filter(
        PendingCatalogue.status == 'pending'
    ).count()
    
    awaiting_count = db.query(PendingCatalogue).filter(
        PendingCatalogue.status == 'awaiting_confirmation'
    ).count()
    
    approved_count = db.query(PendingCatalogue).filter(
        PendingCatalogue.status == 'approved'
    ).count()
    
    failed_count = db.query(PendingCatalogue).filter(
        PendingCatalogue.status == 'failed'
    ).count()
    
    completed_today = db.query(PendingCatalogue).filter(
        PendingCatalogue.status == 'completed',
        PendingCatalogue.updated_at >= datetime.utcnow().date()
    ).count()
    
    # Total books in catalogue
    total_books = db.query(Book).count()
    total_copies = db.query(func.sum(Book.total_copies)).scalar() or 0
    
    # Recent activity (last 10 audit logs)
    recent_activity = db.query(CatalogueAudit).order_by(
        CatalogueAudit.timestamp.desc()
    ).limit(10).all()
    
    return {
        "pending_review": awaiting_count + failed_count,
        "pending_insertion": approved_count,
        "processing": pending_count,
        "completed_today": completed_today,
        "total_books": total_books,
        "total_copies": total_copies,
        "status_breakdown": {
            "pending": pending_count,
            "awaiting_confirmation": awaiting_count,
            "approved": approved_count,
            "failed": failed_count
        },
        "recent_activity": recent_activity
    }
```

**Impact:** Provides at-a-glance overview for librarians.  
**Effort:** 1 hour  
**Priority:** 🟡 **HIGH**

---

### **7. Bulk Operations**
**Need:** Approve/reject multiple books at once.

**Implementation:**
```python
class BulkConfirmationRequest(BaseModel):
    pending_ids: List[int] = Field(..., description="List of pending IDs to process")
    approved: bool = Field(..., description="True to approve all, False to reject all")
    reason: Optional[str] = Field(None, description="Reason for bulk action")

@router.post("/confirm/bulk")
async def bulk_confirm_books(
    request: BulkConfirmationRequest,
    db: Session = Depends(get_db)
):
    """Bulk approve or reject multiple pending books."""
    results = []
    
    for pending_id in request.pending_ids:
        try:
            # Reuse existing confirmation logic
            result = await confirm_book_metadata(
                pending_id=pending_id,
                request=ConfirmationRequest(
                    approved=request.approved,
                    reason=request.reason
                ),
                db=db
            )
            results.append({"pending_id": pending_id, "success": True, "result": result})
        except Exception as e:
            results.append({"pending_id": pending_id, "success": False, "error": str(e)})
    
    return {
        "total": len(request.pending_ids),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }
```

**Impact:** Saves time when processing many books.  
**Effort:** 1 hour  
**Priority:** 🟢 **MEDIUM**

---

### **8. Update/Delete Pending Entries**
**Need:** Edit pending book details before confirmation.

**Implementation:**
```python
@router.put("/pending/{pending_id}")
async def update_pending_book(
    pending_id: int,
    updates: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Update pending catalogue entry before confirmation."""
    pending = db.query(PendingCatalogue).filter(
        PendingCatalogue.id == pending_id
    ).first()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Pending entry not found")
    
    if pending.status not in ['pending', 'awaiting_confirmation', 'failed']:
        raise HTTPException(status_code=400, detail="Cannot edit approved/completed entries")
    
    # Update allowed fields
    allowed_fields = ['title', 'authors', 'isbn', 'total_copies', 'raw_metadata']
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(pending, field, value)
    
    db.commit()
    db.refresh(pending)
    
    # Log audit
    create_audit_log(db, pending_id, 'updated', 'librarian', f"Updated fields: {list(updates.keys())}")
    
    return pending

@router.delete("/pending/{pending_id}")
async def delete_pending_book(
    pending_id: int,
    reason: str = Query(..., description="Reason for deletion"),
    db: Session = Depends(get_db)
):
    """Delete pending catalogue entry."""
    pending = db.query(PendingCatalogue).filter(
        PendingCatalogue.id == pending_id
    ).first()
    
    if not pending:
        raise HTTPException(status_code=404, detail="Pending entry not found")
    
    if pending.status == 'completed':
        raise HTTPException(status_code=400, detail="Cannot delete completed entries")
    
    # Log before deletion
    create_audit_log(db, pending_id, 'deleted', 'librarian', reason)
    
    db.delete(pending)
    db.commit()
    
    return {"message": "Pending entry deleted successfully", "pending_id": pending_id}
```

**Impact:** Allows corrections without re-adding books.  
**Effort:** 1 hour  
**Priority:** 🟢 **MEDIUM**

---

### **9. Book Management Endpoints (Main Catalogue)**
**Need:** View, edit, and manage books in the main catalogue.

**Implementation:**
```python
# GET /books - List all books with pagination
# GET /books/{book_id} - Get book details
# PUT /books/{book_id} - Update book metadata
# DELETE /books/{book_id} - Delete book (soft delete recommended)
# GET /books/search - Search books by title, author, ISBN
# POST /books/{book_id}/copies - Add/remove copies
```

**Impact:** Complete catalogue management.  
**Effort:** 3-4 hours  
**Priority:** 🟢 **MEDIUM**

---

### **10. File Upload for Cover Images**
**Need:** Allow librarians to upload custom cover images.

**Implementation:**
```python
from fastapi import UploadFile, File
import shutil
from pathlib import Path

UPLOAD_DIR = Path("uploads/covers")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/pending/{pending_id}/cover")
async def upload_cover_image(
    pending_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload cover image for pending book."""
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Save file
    file_path = UPLOAD_DIR / f"{pending_id}_{file.filename}"
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update pending entry
    pending = db.query(PendingCatalogue).filter(
        PendingCatalogue.id == pending_id
    ).first()
    
    if pending and pending.raw_metadata:
        pending.raw_metadata['cover_url'] = f"/uploads/covers/{file_path.name}"
        db.commit()
    
    return {"message": "Cover uploaded successfully", "url": f"/uploads/covers/{file_path.name}"}

# Add static file serving in main.py
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

**Impact:** Better visual presentation.  
**Effort:** 1 hour  
**Priority:** 🟢 **MEDIUM**

---

### **11. Export Functionality**
**Need:** Export pending books or catalogue data to CSV/Excel.

**Implementation:**
```python
from fastapi.responses import StreamingResponse
import csv
from io import StringIO

@router.get("/pending/export")
async def export_pending_books(
    format: str = Query("csv", regex="^(csv|json)$"),
    db: Session = Depends(get_db)
):
    """Export pending books to CSV or JSON."""
    
    pending_books = db.query(PendingCatalogue).filter(
        PendingCatalogue.status.in_(['awaiting_confirmation', 'failed'])
    ).all()
    
    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Title', 'Authors', 'ISBN', 'Status', 'Created At'])
        
        for book in pending_books:
            writer.writerow([
                book.id,
                book.title,
                ', '.join(book.authors or []),
                book.isbn,
                book.status,
                book.created_at.isoformat()
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=pending_books.csv"}
        )
    
    # JSON format
    return [
        {
            "id": book.id,
            "title": book.title,
            "authors": book.authors,
            "isbn": book.isbn,
            "status": book.status,
            "created_at": book.created_at.isoformat()
        }
        for book in pending_books
    ]
```

**Impact:** Useful for reporting and backups.  
**Effort:** 1 hour  
**Priority:** 🟢 **LOW**

---

### **12. WebSocket Support for Real-Time Updates**
**Need:** Notify librarians when new books are added or status changes.

**Implementation:**
```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import List

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# In catalogue.py, after creating pending entry:
await manager.broadcast({
    "type": "new_pending_book",
    "pending_id": pending_entry.id,
    "title": pending_entry.title
})
```

**Impact:** Improves UX with real-time notifications.  
**Effort:** 2-3 hours  
**Priority:** 🟢 **LOW**

---

## 📊 **Priority Matrix**

| Feature | Priority | Effort | Impact | When to Implement |
|---------|----------|--------|--------|-------------------|
| CORS Configuration | 🔴 CRITICAL | 5 min | High | Before frontend development |
| Pagination | 🔴 CRITICAL | 30 min | High | Before frontend development |
| Authentication | 🔴 CRITICAL | 2-4 hrs | High | Before production deployment |
| Error Standardization | 🟡 HIGH | 1 hr | Medium | Week 1 |
| Search & Filter | 🟡 HIGH | 1-2 hrs | High | Week 1 |
| Dashboard Stats | 🟡 HIGH | 1 hr | High | Week 1 |
| Bulk Operations | 🟢 MEDIUM | 1 hr | Medium | Week 2 |
| Update/Delete Pending | 🟢 MEDIUM | 1 hr | Medium | Week 2 |
| Book Management | 🟢 MEDIUM | 3-4 hrs | High | Week 2-3 |
| File Upload | 🟢 MEDIUM | 1 hr | Low | Week 3 |
| Export Functionality | 🟢 LOW | 1 hr | Low | Week 4 |
| WebSocket Notifications | 🟢 LOW | 2-3 hrs | Low | Week 4+ |

---

## 🎨 **Frontend Technology Recommendations**

### **Recommended Stack:**
1. **React** + **TypeScript** + **Vite** (Modern, fast development)
2. **TanStack Query** (React Query) - API state management
3. **React Router** - Navigation
4. **Tailwind CSS** + **shadcn/ui** - UI components
5. **Zod** - Runtime validation (matches Pydantic)
6. **Axios** or **Fetch API** - HTTP client

### **Alternative Stack:**
1. **Vue 3** + **TypeScript** + **Vite**
2. **Pinia** - State management
3. **Vue Router** - Navigation
4. **Vuetify** or **PrimeVue** - UI components

### **Quick Admin Panel:**
1. **React Admin** - Pre-built admin framework
2. **Refine** - Headless admin framework
3. **AdminJS** - Node.js admin panel (requires adapter)

---

## 🔌 **API Client Generation**

Generate TypeScript client from OpenAPI spec:

```bash
# Install openapi-typescript-codegen
npm install --save-dev openapi-typescript-codegen

# Generate client
npx openapi-typescript-codegen --input http://localhost:8000/openapi.json --output ./src/api --client axios
```

This creates type-safe API client functions automatically.

---

## 📝 **Sample Frontend Integration Code**

### **React + TypeScript Example:**

```typescript
// src/api/catalogue.ts
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export interface PendingBook {
  id: number;
  title: string;
  authors: string[] | null;
  isbn: string | null;
  status: string;
  raw_metadata: any;
  created_at: string;
}

export const catalogueApi = {
  // Get pending books
  getPendingBooks: async (page = 1, pageSize = 20) => {
    const response = await axios.get<PendingBook[]>(
      `${API_BASE_URL}/catalogue/pending`,
      { params: { page, page_size: pageSize } }
    );
    return response.data;
  },

  // Confirm book
  confirmBook: async (pendingId: number, approved: boolean, edits?: any, reason?: string) => {
    const response = await axios.post(
      `${API_BASE_URL}/catalogue/confirm/${pendingId}`,
      { approved, edits, reason }
    );
    return response.data;
  },

  // Add book
  addBook: async (data: { isbn?: string; title: string; authors?: string[]; total_copies?: number }) => {
    const response = await axios.post(
      `${API_BASE_URL}/catalogue/add`,
      data
    );
    return response.data;
  },
};

// src/components/PendingBooksList.tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { catalogueApi } from '../api/catalogue';

export function PendingBooksList() {
  const queryClient = useQueryClient();
  
  const { data: books, isLoading } = useQuery({
    queryKey: ['pendingBooks'],
    queryFn: () => catalogueApi.getPendingBooks(),
  });

  const confirmMutation = useMutation({
    mutationFn: ({ id, approved }: { id: number; approved: boolean }) =>
      catalogueApi.confirmBook(id, approved),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pendingBooks'] });
    },
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <h2>Pending Books</h2>
      {books?.map((book) => (
        <div key={book.id}>
          <h3>{book.title}</h3>
          <p>Authors: {book.authors?.join(', ')}</p>
          <p>Status: {book.status}</p>
          <button onClick={() => confirmMutation.mutate({ id: book.id, approved: true })}>
            Approve
          </button>
          <button onClick={() => confirmMutation.mutate({ id: book.id, approved: false })}>
            Reject
          </button>
        </div>
      ))}
    </div>
  );
}
```

---

## 🧪 **Testing Recommendations**

### **Backend Testing:**
```bash
# Test all endpoints
pytest tests/ -v

# Test with coverage
pytest tests/ --cov=. --cov-report=html
```

### **Frontend Testing:**
```bash
# Unit tests (Vitest)
npm run test

# E2E tests (Playwright)
npm run test:e2e
```

---

## 📦 **Deployment Considerations**

### **Backend:**
- Use **Gunicorn** or **Uvicorn** with multiple workers
- Set up **HTTPS** with Let's Encrypt
- Configure **environment variables** for production
- Set up **database backups**
- Enable **API rate limiting**

### **Frontend:**
- Build optimized production bundle
- Deploy to **Vercel**, **Netlify**, or **AWS S3 + CloudFront**
- Configure **environment variables** for API URL
- Enable **CDN** for static assets

---

## 🔒 **Security Checklist**

- [ ] CORS configured with specific origins (not `*`)
- [ ] Authentication implemented (JWT or API Key)
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (using SQLAlchemy ORM)
- [ ] Rate limiting enabled
- [ ] HTTPS enforced in production
- [ ] Sensitive data not logged
- [ ] File upload size limits
- [ ] API key rotation policy
- [ ] Regular dependency updates

---

## 📞 **Next Steps**

1. **Immediate (Before Frontend Development):**
   - [ ] Add CORS middleware
   - [ ] Implement pagination
   - [ ] Add authentication (at least API key)

2. **Week 1 (Parallel with Frontend Setup):**
   - [ ] Add search & filter
   - [ ] Create dashboard stats endpoint
   - [ ] Standardize error responses

3. **Week 2 (During Frontend Development):**
   - [ ] Implement bulk operations
   - [ ] Add update/delete endpoints
   - [ ] Create book management endpoints

4. **Week 3+ (Enhancement Phase):**
   - [ ] File upload support
   - [ ] Export functionality
   - [ ] WebSocket notifications

---

## 📚 **Additional Resources**

- **FastAPI CORS Documentation:** https://fastapi.tiangolo.com/tutorial/cors/
- **FastAPI Security:** https://fastapi.tiangolo.com/tutorial/security/
- **React Query Documentation:** https://tanstack.com/query/latest
- **shadcn/ui Components:** https://ui.shadcn.com/

---

## 🤝 **Support & Contribution**

For questions or contributions, please refer to the main project documentation.

**Document Maintained By:** SLMS Development Team  
**Last Review Date:** 2025-10-10
