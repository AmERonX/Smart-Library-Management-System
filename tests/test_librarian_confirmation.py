"""
Unit tests for Librarian Confirmation & Audit Logging feature.
Tests the complete workflow from book addition to confirmation with audit trail.
"""

import pytest
import logging
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

import sys
import os
sys.path.insert(0,os.path.abspath(os.path.join(os.path.dirname(__file__),'..')))

from database import Base, get_db
from models import PendingCatalogue, CatalogueAudit
from main import app


# Configure logging to avoid Windows handle errors

# ============================================================================
# TEST DATABASE SETUP
# ============================================================================

# Use in-memory SQLite for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ============================================================================
# TEST CASES
# ============================================================================

def test_add_book_valid_input():
    """
    Test adding a book with valid input.
    Should create pending entry and audit log.
    """
    # Arrange
    book_data = {
        "isbn": "9780132350884",
        "title": "Clean Code",
        "authors": ["Robert C. Martin"],
        "total_copies": 3
    }
    
    # Act
    response = client.post("/catalogue/add", json=book_data)
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Book added to pending catalogue successfully"
    assert data["status"] == "awaiting_confirmation"
    assert "pending_id" in data
    
    # Verify database entry
    db = TestingSessionLocal()
    pending_entry = db.query(PendingCatalogue).filter_by(id=data["pending_id"]).first()
    assert pending_entry is not None
    assert pending_entry.isbn == "9780132350884"
    assert pending_entry.title == "Clean Code"
    assert pending_entry.status == "awaiting_confirmation"
    
    # Verify audit log
    audit_log = db.query(CatalogueAudit).filter_by(pending_id=data["pending_id"]).first()
    assert audit_log is not None
    assert audit_log.action == "input_received"
    assert audit_log.source == "frontend"
    db.close()


def test_add_book_invalid_isbn():
    """
    Test adding a book with invalid ISBN.
    Should return 422 validation error.
    """
    # Arrange
    book_data = {
        "isbn": "123",  # Invalid ISBN
        "title": "Test Book",
        "total_copies": 1
    }
    
    # Act
    response = client.post("/catalogue/add", json=book_data)
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_add_book_missing_title():
    """
    Test adding a book without title.
    Should return 422 validation error.
    """
    # Arrange
    book_data = {
        "isbn": "9780132350884",
        "total_copies": 1
        # Missing title
    }
    
    # Act
    response = client.post("/catalogue/add", json=book_data)
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_add_book_invalid_total_copies():
    """
    Test adding a book with invalid total_copies (< 1).
    Should return 422 validation error.
    """
    # Arrange
    book_data = {
        "isbn": "9780132350884",
        "title": "Test Book",
        "total_copies": 0  # Invalid
    }
    
    # Act
    response = client.post("/catalogue/add", json=book_data)
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_get_pending_books():
    """
    Test retrieving all pending books.
    Should return list of books with status='awaiting_confirmation'.
    """
    # Arrange - Add two books
    book1 = {
        "isbn": "9780132350884",
        "title": "Clean Code",
        "authors": ["Robert C. Martin"],
        "total_copies": 2
    }
    book2 = {
        "isbn": "9780134685991",
        "title": "Effective Java",
        "authors": ["Joshua Bloch"],
        "total_copies": 1
    }
    
    client.post("/catalogue/add", json=book1)
    client.post("/catalogue/add", json=book2)
    
    # Act
    response = client.get("/catalogue/pending")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Clean Code"
    assert data[1]["title"] == "Effective Java"


def test_confirm_approved_updates_status():
    """
    Test approving metadata.
    Should create output_json and update status to 'approved'.
    """
    # Arrange - Add a book
    book_data = {
        "isbn": "9780132350884",
        "title": "Clean Code",
        "authors": ["Robert C. Martin"],
        "total_copies": 3
    }
    add_response = client.post("/catalogue/add", json=book_data)
    pending_id = add_response.json()["pending_id"]
    
    # Simulate metadata extraction by updating raw_metadata
    db = TestingSessionLocal()
    pending_entry = db.query(PendingCatalogue).filter_by(id=pending_id).first()
    pending_entry.raw_metadata = {
        "publisher": "Prentice Hall",
        "publication_year": "2008",
        "description": "A handbook of agile software craftsmanship"
    }
    db.commit()
    db.close()
    
    # Apply librarian edits via PATCH before confirming
    patch_body = {
        "raw_metadata": {
            "publisher": "Prentice Hall PTR",
            "edition": "1st"
        }
    }
    patch_resp = client.patch(f"/catalogue/pending/{pending_id}", json=patch_body)
    assert patch_resp.status_code == 200

    # Act - Approve (finalize from saved metadata)
    confirmation_data = {
        "approved": True,
        "reason": "Metadata verified"
    }
    response = client.post(f"/catalogue/confirm/{pending_id}", json=confirmation_data)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Metadata approved successfully"
    assert data["status"] == "approved"
    assert data["output_json"] is not None
    assert data["output_json"]["publisher"] == "Prentice Hall PTR"
    assert data["output_json"]["edition"] == "1st"
    assert data["output_json"]["source"] == "librarian_confirmation"
    
    # Verify database
    db = TestingSessionLocal()
    pending_entry = db.query(PendingCatalogue).filter_by(id=pending_id).first()
    assert pending_entry.status == "approved"
    assert pending_entry.output_json is not None
    
    # Verify audit log
    audit_logs = db.query(CatalogueAudit).filter_by(
        pending_id=pending_id,
        action="approved"
    ).all()
    assert len(audit_logs) == 1
    assert audit_logs[0].source == "librarian"
    db.close()


def test_confirm_rejected_records_reason():
    """
    Test rejecting metadata.
    Should mark status='failed' and record rejection reason in audit.
    """
    # Arrange - Add a book
    book_data = {
        "isbn": "9780132350884",
        "title": "Clean Code",
        "authors": ["Robert C. Martin"],
        "total_copies": 3
    }
    add_response = client.post("/catalogue/add", json=book_data)
    pending_id = add_response.json()["pending_id"]
    
    # Act - Reject
    confirmation_data = {
        "approved": False,
        "reason": "Incorrect metadata - wrong edition"
    }
    response = client.post(f"/catalogue/confirm/{pending_id}", json=confirmation_data)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Metadata rejected"
    assert data["status"] == "failed"
    assert data["output_json"] is None
    
    # Verify database
    db = TestingSessionLocal()
    pending_entry = db.query(PendingCatalogue).filter_by(id=pending_id).first()
    assert pending_entry.status == "failed"
    
    # Verify audit log
    audit_logs = db.query(CatalogueAudit).filter_by(
        pending_id=pending_id,
        action="rejected"
    ).all()
    assert len(audit_logs) == 1
    assert audit_logs[0].source == "librarian"
    assert "wrong edition" in audit_logs[0].details
    db.close()


def test_confirm_rejected_without_reason():
    """
    Test rejecting metadata without providing reason.
    Should return 422 validation error.
    """
    # Arrange - Add a book
    book_data = {
        "isbn": "9780132350884",
        "title": "Clean Code",
        "total_copies": 1
    }
    add_response = client.post("/catalogue/add", json=book_data)
    pending_id = add_response.json()["pending_id"]
    
    # Act - Reject without reason
    confirmation_data = {
        "approved": False
        # Missing reason
    }
    response = client.post(f"/catalogue/confirm/{pending_id}", json=confirmation_data)
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_confirm_nonexistent_pending_id():
    """
    Test confirming a non-existent pending entry.
    Should return 404 error.
    """
    # Arrange
    confirmation_data = {
        "approved": True,
        "reason": "Test"
    }
    
    # Act
    response = client.post("/catalogue/confirm/99999", json=confirmation_data)
    
    # Assert
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_audit_retrieval():
    """
    Test retrieving audit logs for a pending book.
    Should return ordered actions.
    """
    # Arrange - Add and confirm a book
    book_data = {
        "isbn": "9780132350884",
        "title": "Clean Code",
        "authors": ["Robert C. Martin"],
        "total_copies": 2
    }
    add_response = client.post("/catalogue/add", json=book_data)
    pending_id = add_response.json()["pending_id"]
    
    # Approve the book
    confirmation_data = {
        "approved": True,
        "reason": "Verified"
    }
    client.post(f"/catalogue/confirm/{pending_id}", json=confirmation_data)
    
    # Act - Get audit logs
    response = client.get(f"/catalogue/audit/{pending_id}")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Audit logs retrieved successfully"
    assert data["pending_id"] == pending_id
    assert data["total_entries"] == 3  # input_received + metadata_extracted + approved
    
    audit_logs = data["audit_logs"]
    assert audit_logs[0]["action"] == "input_received"
    assert audit_logs[1]["action"] == "metadata_extracted"
    assert audit_logs[2]["action"] == "approved"
    
    # Verify chronological order
    timestamp1 = datetime.fromisoformat(audit_logs[0]["timestamp"].replace('Z', '+00:00'))
    timestamp2 = datetime.fromisoformat(audit_logs[1]["timestamp"].replace('Z', '+00:00'))
    timestamp3 = datetime.fromisoformat(audit_logs[2]["timestamp"].replace('Z', '+00:00'))
    assert timestamp1 <= timestamp2 <= timestamp3


def test_audit_retrieval_nonexistent_pending_id():
    """
    Test retrieving audit logs for non-existent pending entry.
    Should return 404 error.
    """
    # Act
    response = client.get("/catalogue/audit/99999")
    
    # Assert
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_isbn_normalization():
    """
    Test that ISBN with hyphens is normalized correctly.
    """
    # Arrange
    book_data = {
        "isbn": "978-0-13-235088-4",  # ISBN with hyphens
        "title": "Clean Code",
        "total_copies": 1
    }
    
    # Act
    response = client.post("/catalogue/add", json=book_data)
    
    # Assert
    assert response.status_code == 201
    pending_id = response.json()["pending_id"]
    
    # Verify normalized ISBN in database
    db = TestingSessionLocal()
    pending_entry = db.query(PendingCatalogue).filter_by(id=pending_id).first()
    assert pending_entry.isbn == "9780132350884"  # Hyphens removed
    db.close()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
