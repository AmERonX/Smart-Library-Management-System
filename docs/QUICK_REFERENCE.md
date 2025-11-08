# SLMS Quick Reference

Quick commands and tips for daily use. For complete setup, see [SETUP_GUIDE.md](../SETUP_GUIDE.md).

---

## 📋 **Common Commands**

### **Add Book**
```bash
curl -X POST "http://localhost:8000/catalogue/add" \
  -H "Content-Type: application/json" \
  -d '{"isbn": "9780132350884", "title": "Clean Code", "total_copies": 3}'
```

### **List Pending Books**
```bash
curl http://localhost:8000/catalogue/pending
```

### **Approve Book**
```bash
curl -X POST "http://localhost:8000/catalogue/confirm/1" \
  -H "Content-Type: application/json" \
  -d '{"approved": true, "reason": "Verified"}'
```

### **Insert to Catalogue**
```bash
curl -X POST "http://localhost:8000/catalogue/insert/1"
```

### **View Audit Trail**
```bash
curl http://localhost:8000/catalogue/audit/1
```

---

## 🗄️ **Database Queries**

### **View Pending Books**
```sql
SELECT id, isbn, title, status, created_at
FROM lms_core.pending_catalogue
WHERE status = 'awaiting_confirmation'
ORDER BY created_at;
```

### **View Books in Catalogue**
```sql
SELECT book_id, isbn_13, title, total_copies, available_copies
FROM lms_core.books
ORDER BY created_at DESC
LIMIT 10;
```

### **Check Audit Logs**
```sql
SELECT book_id, action, source, timestamp
FROM lms_core.catalogue_audit
ORDER BY timestamp DESC
LIMIT 20;
```

### **Find Book by ISBN**
```sql
SELECT * FROM lms_core.books
WHERE isbn_13 = '9780132350884'
   OR isbn_10 = '0132350882';
```

---

## 📊 **Status Values**

| Status | Meaning | Next Action |
|--------|---------|-------------|
| `pending` | Just created | Wait for metadata extraction |
| `awaiting_confirmation` | Metadata ready | Librarian review |
| `approved` | Librarian approved | Insert to catalogue |
| `rejected` | Librarian rejected | Archive or delete |
| `failed` | Metadata failed | Manual entry |
| `completed` | In catalogue | Done |

---

## 🔧 **Troubleshooting**

### **Metadata Extraction Fails**
```bash
# Check API health
curl http://localhost:8000/health

# Expected: Both APIs "reachable"
```

### **Database Connection Error**
```bash
# Check .env file
cat .env

# Should have:
# DATABASE_URL=postgresql://postgres:password@localhost:5432/slms
```

### **Migration Not Applied**
```bash
# Apply migration
psql -U postgres -d slms -f migrations/002_add_isbn_fields_to_pending_catalogue.sql

# Verify
psql -U postgres -d slms -c "\d lms_core.pending_catalogue"
```

---

## 🧪 **Testing**

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_insertion.py -v

# With coverage
pytest tests/ --cov=services --cov-report=html
```

---

## 🌐 **API Endpoints**

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Service info |
| GET | `/health` | Health check |
| POST | `/catalogue/add` | Add book |
| GET | `/catalogue/pending` | List pending |
| POST | `/catalogue/confirm/{id}` | Approve/reject |
| POST | `/catalogue/insert/{id}` | Insert book |
| GET | `/catalogue/audit/{id}` | Audit logs |

---

## 💡 **Tips**

1. **Always check audit logs** when debugging issues
2. **Use `/health` endpoint** to verify API connectivity
3. **Pending entries can be retried** - operations are idempotent
4. **ISBN-13 is canonical** - prefer it over ISBN-10
5. **Status transitions are one-way** - can't go back

---

## 📚 **More Documentation**

- [WORKFLOW.md](WORKFLOW.md) - Complete workflow diagrams
- [API_ENDPOINTS.md](API_ENDPOINTS.md) - Full API reference
- [SETUP_GUIDE.md](../SETUP_GUIDE.md) - Installation guide
