"""
Unit tests for Book Insertion Service (Phase-1)
Tests cover all acceptance criteria: new book insertion, copy addition,
edition handling, idempotency, and failure scenarios.

Test Database:
- Uses in-memory SQLite for fast, isolated tests
- Each test gets a fresh database session
- No external dependencies or API calls

Test Coverage:
1. test_insert_new_book_creates_records - Full insertion workflow
2. test_insert_existing_isbn_adds_copies - Copy addition to existing book
3. test_insert_new_edition_inserts_new_book - Different ISBN = new edition
4. test_idempotent_on_repeated_call - Idempotency guarantee
5. test_failure_rolls_back_and_audited - Error handling and rollback
6. test_insert_with_isbn_10_only - ISBN-10 support
7. test_insert_with_isbn_13_only - ISBN-13 support
8. test_insert_with_both_isbns - Dual ISBN support
9. test_insert_without_publisher - Nullable publisher
10. test_insert_with_empty_authors - Unknown author placeholder
11. test_pending_not_found - 404 error handling
12. test_pending_not_approved - 400 error handling
13. test_missing_title - Validation error handling
"""

import pytest
import json
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

import sys
import os


sys.path.insert(0,os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))

from database import Base
from models import (
    PendingCatalogue,
    CatalogueAudit,
    Book,
    Author,
    Publisher,
    BookAuthor
)
from services.insertion import (
    insert_pending_book,
    normalize_isbn,
    infer_isbn_type,
    get_or_create_publisher,
    get_or_create_author,
    find_book_by_isbn,
    create_book_and_links,
    add_copies
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_db():
    """
    Create an in-memory SQLite database for each test.
    Ensures test isolation and fast execution.
    """
    # Create in-memory SQLite engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Yield session for test
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_pending_approved(test_db: Session):
    """
    Create a sample approved pending_catalogue entry with full metadata.
    """
    pending = PendingCatalogue(
        isbn="9780132350884",
        title="Clean Code: A Handbook of Agile Software Craftsmanship",
        authors=["Robert C. Martin"],
        total_copies=3,
        raw_metadata={
            "isbn": "9780132350884",
            "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
            "authors": ["Robert C. Martin"],
            "publisher": "Prentice Hall",
            "publication_year": "2008",
            "edition": "1st"
        },
        output_json={
            "isbn_13": "9780132350884",
            "isbn_10": "0132350882",
            "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
            "authors": ["Robert C. Martin"],
            "publisher": "Prentice Hall",
            "publication_year": "2008",
            "edition": "1st",
            "cover_url": "https://example.com/cover.jpg"
        },
        status="approved"
    )
    test_db.add(pending)
    test_db.commit()
    test_db.refresh(pending)
    return pending


@pytest.fixture
def sample_pending_no_isbn(test_db: Session):
    """
    Create a pending entry without ISBN (title and authors only).
    """
    pending = PendingCatalogue(
        isbn=None,
        title="The Pragmatic Programmer",
        authors=["Andrew Hunt", "David Thomas"],
        total_copies=2,
        output_json={
            "title": "The Pragmatic Programmer",
            "authors": ["Andrew Hunt", "David Thomas"],
            "publisher": "Addison-Wesley",
            "publication_year": "1999"
        },
        status="approved"
    )
    test_db.add(pending)
    test_db.commit()
    test_db.refresh(pending)
    return pending


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

def test_normalize_isbn():
    """Test ISBN normalization removes hyphens and spaces."""
    assert normalize_isbn("978-0-13-235088-4") == "9780132350884"
    assert normalize_isbn("0-13-235088-2") == "0132350882"
    assert normalize_isbn("978 0 13 235088 4") == "9780132350884"
    assert normalize_isbn("  9780132350884  ") == "9780132350884"
    assert normalize_isbn("") is None
    assert normalize_isbn(None) is None
    assert normalize_isbn("123456789X") == "123456789X"  # ISBN-10 with X


def test_infer_isbn_type():
    """Test ISBN type inference based on length."""
    assert infer_isbn_type("9780132350884") == "isbn_13"
    assert infer_isbn_type("0132350882") == "isbn_10"
    assert infer_isbn_type("123456789X") == "isbn_10"
    assert infer_isbn_type("12345") is None
    assert infer_isbn_type("") is None


def test_get_or_create_publisher(test_db: Session):
    """Test publisher upsert logic."""
    # Create new publisher
    pub_id_1 = get_or_create_publisher(test_db, "Prentice Hall")
    test_db.commit()
    assert pub_id_1 is not None
    
    # Get existing publisher (should return same ID)
    pub_id_2 = get_or_create_publisher(test_db, "Prentice Hall")
    test_db.commit()
    assert pub_id_1 == pub_id_2
    
    # Empty publisher name returns None
    pub_id_3 = get_or_create_publisher(test_db, "")
    assert pub_id_3 is None
    
    pub_id_4 = get_or_create_publisher(test_db, None)
    assert pub_id_4 is None


def test_get_or_create_author(test_db: Session):
    """Test author upsert logic."""
    # Create new author
    author_id_1 = get_or_create_author(test_db, "Robert C. Martin")
    test_db.commit()
    assert author_id_1 is not None
    
    # Get existing author (should return same ID)
    author_id_2 = get_or_create_author(test_db, "Robert C. Martin")
    test_db.commit()
    assert author_id_1 == author_id_2
    
    # Empty author name creates placeholder
    author_id_3 = get_or_create_author(test_db, "")
    test_db.commit()
    assert author_id_3 is not None
    
    # Verify placeholder was created
    author = test_db.query(Author).filter(Author.author_id == author_id_3).first()
    assert "Unknown Author" in author.full_name


# ============================================================================
# ACCEPTANCE TESTS
# ============================================================================

def test_insert_new_book_creates_records(test_db: Session, sample_pending_approved):
    """
    Test 1: Insert new book creates all required records.
    
    Acceptance Criteria:
    - Publisher row exists
    - Author rows exist
    - Book row exists with isbn_13, isbn_10, and all metadata
    - Book has correct number of copies
    - book_authors links exist
    - catalogue_audit contains 'inserted' and 'pending_completed' actions
    """
    pending = sample_pending_approved
    
    # Execute insertion
    result = insert_pending_book(test_db, pending.id)
    
    # Verify result
    assert result['success'] is True
    assert result['action'] == 'inserted'
    assert result['pending_id'] == pending.id
    assert result['book_id'] is not None
    assert result['status'] == 'completed'
    
    # Verify pending status updated
    test_db.refresh(pending)
    assert pending.status == 'completed'
    
    # Verify publisher created
    publisher = test_db.query(Publisher).filter(Publisher.name == "Prentice Hall").first()
    assert publisher is not None
    
    # Verify author created
    author = test_db.query(Author).filter(Author.full_name == "Robert C. Martin").first()
    assert author is not None
    
    # Verify book created with all fields
    book = test_db.query(Book).filter(Book.book_id == result['book_id']).first()
    assert book is not None
    assert book.title == "Clean Code: A Handbook of Agile Software Craftsmanship"
    assert book.isbn_13 == "9780132350884"
    assert book.isbn_10 == "0132350882"
    assert book.isbn == "9780132350884"  # Canonical (isbn_13)
    assert book.publisher_id == publisher.publisher_id
    assert book.publication_year == "2008"
    assert book.edition == "1st"
    assert book.cover_url == "https://example.com/cover.jpg"
    assert book.total_copies == 3
    assert book.available_copies == 3
    
    # Verify book-author link
    book_author = test_db.query(BookAuthor).filter(
        BookAuthor.book_id == book.book_id,
        BookAuthor.author_id == author.author_id
    ).first()
    assert book_author is not None
    
    # Verify audit logs
    audit_inserted = test_db.query(CatalogueAudit).filter(
        CatalogueAudit.pending_id == pending.id,
        CatalogueAudit.action == 'inserted'
    ).first()
    assert audit_inserted is not None
    assert audit_inserted.source == 'insertion_service'
    
    audit_completed = test_db.query(CatalogueAudit).filter(
        CatalogueAudit.pending_id == pending.id,
        CatalogueAudit.action == 'pending_completed'
    ).first()
    assert audit_completed is not None


def test_insert_existing_isbn_adds_copies(test_db: Session, sample_pending_approved):
    """
    Test 2: Inserting existing ISBN adds copies instead of creating duplicate.
    
    Acceptance Criteria:
    - Book's total_copies increased by pending.total_copies
    - Book's available_copies increased by pending.total_copies
    - No new book record created
    - catalogue_audit contains 'copies_added' and 'pending_completed'
    """
    pending = sample_pending_approved
    
    # Pre-create the book
    publisher = Publisher(name="Prentice Hall")
    test_db.add(publisher)
    test_db.commit()
    
    author = Author(full_name="Robert C. Martin")
    test_db.add(author)
    test_db.commit()
    
    existing_book = Book(
        isbn="9780132350884",
        isbn_13="9780132350884",
        isbn_10="0132350882",
        title="Clean Code: A Handbook of Agile Software Craftsmanship",
        publisher_id=publisher.publisher_id,
        total_copies=5,
        available_copies=5
    )
    test_db.add(existing_book)
    test_db.commit()
    test_db.refresh(existing_book)
    
    book_author = BookAuthor(book_id=existing_book.book_id, author_id=author.author_id)
    test_db.add(book_author)
    test_db.commit()
    
    initial_total = existing_book.total_copies
    initial_available = existing_book.available_copies
    
    # Execute insertion
    result = insert_pending_book(test_db, pending.id)
    
    # Verify result
    assert result['success'] is True
    assert result['action'] == 'copies_added'
    assert result['book_id'] == existing_book.book_id
    
    # Verify copies added
    test_db.refresh(existing_book)
    assert existing_book.total_copies == initial_total + pending.total_copies
    assert existing_book.available_copies == initial_available + pending.total_copies
    
    # Verify no duplicate book created
    book_count = test_db.query(Book).filter(Book.isbn_13 == "9780132350884").count()
    assert book_count == 1
    
    # Verify audit log
    audit_copies = test_db.query(CatalogueAudit).filter(
        CatalogueAudit.pending_id == pending.id,
        CatalogueAudit.action == 'copies_added'
    ).first()
    assert audit_copies is not None
    
    # Parse details
    details = json.loads(audit_copies.details)
    assert details['added_copies'] == pending.total_copies
    assert details['book_id'] == existing_book.book_id


def test_insert_new_edition_inserts_new_book(test_db: Session):
    """
    Test 3: Different ISBN (even with same title/authors) creates new book.
    
    Acceptance Criteria:
    - New book record created (different book_id)
    - Both books exist with different ISBNs
    - Same title and authors but different editions
    """
    # Create first edition
    pending_1 = PendingCatalogue(
        isbn="9780132350884",
        title="Clean Code",
        authors=["Robert C. Martin"],
        total_copies=2,
        output_json={
            "isbn_13": "9780132350884",
            "title": "Clean Code",
            "authors": ["Robert C. Martin"],
            "edition": "1st"
        },
        status="approved"
    )
    test_db.add(pending_1)
    test_db.commit()
    
    result_1 = insert_pending_book(test_db, pending_1.id)
    book_id_1 = result_1['book_id']
    
    # Create second edition with different ISBN
    pending_2 = PendingCatalogue(
        isbn="9780135781685",
        title="Clean Code",
        authors=["Robert C. Martin"],
        total_copies=3,
        output_json={
            "isbn_13": "9780135781685",
            "title": "Clean Code",
            "authors": ["Robert C. Martin"],
            "edition": "2nd"
        },
        status="approved"
    )
    test_db.add(pending_2)
    test_db.commit()
    
    result_2 = insert_pending_book(test_db, pending_2.id)
    book_id_2 = result_2['book_id']
    
    # Verify different books created
    assert book_id_1 != book_id_2
    
    # Verify both books exist
    book_1 = test_db.query(Book).filter(Book.book_id == book_id_1).first()
    book_2 = test_db.query(Book).filter(Book.book_id == book_id_2).first()
    
    assert book_1.isbn_13 == "9780132350884"
    assert book_2.isbn_13 == "9780135781685"
    assert book_1.edition == "1st"
    assert book_2.edition == "2nd"
    
    # Verify total book count
    book_count = test_db.query(Book).count()
    assert book_count == 2


def test_idempotent_on_repeated_call(test_db: Session, sample_pending_approved):
    """
    Test 4: Calling insert twice for same pending_id is idempotent.
    
    Acceptance Criteria:
    - First call: inserts book successfully
    - Second call: returns "already completed" without duplicating
    - No duplicate books or double-added copies
    - Both calls return success
    """
    pending = sample_pending_approved
    
    # First call
    result_1 = insert_pending_book(test_db, pending.id)
    assert result_1['success'] is True
    assert result_1['action'] == 'inserted'
    book_id_1 = result_1['book_id']
    
    # Get initial copy counts
    book = test_db.query(Book).filter(Book.book_id == book_id_1).first()
    initial_total = book.total_copies
    initial_available = book.available_copies
    
    # Second call (idempotent)
    result_2 = insert_pending_book(test_db, pending.id)
    assert result_2['success'] is True
    assert result_2['action'] == 'already_completed'
    assert result_2['message'] == 'Pending record already completed'
    assert result_2['book_id'] == book_id_1
    
    # Verify no duplicate books
    book_count = test_db.query(Book).count()
    assert book_count == 1
    
    # Verify copies not doubled
    test_db.refresh(book)
    assert book.total_copies == initial_total
    assert book.available_copies == initial_available


def test_failure_rolls_back_and_audited(test_db: Session):
    """
    Test 5: Database errors trigger rollback and failure audit.
    
    Acceptance Criteria:
    - On constraint violation or error, transaction rolls back
    - No partial state inserted (no orphaned records)
    - catalogue_audit contains 'insert_failed' entry
    """
    # Create pending with missing required field (title)
    pending = PendingCatalogue(
        isbn="9780132350884",
        title="Test Book",
        authors=["Test Author"],
        total_copies=1,
        output_json={
            "isbn_13": "9780132350884",
            # Missing 'title' - will cause ValueError
            "authors": ["Test Author"]
        },
        status="approved"
    )
    test_db.add(pending)
    test_db.commit()
    
    # Attempt insertion (should fail)
    with pytest.raises(ValueError) as exc_info:
        insert_pending_book(test_db, pending.id)
    
    assert "Title is required" in str(exc_info.value)
    
    # Verify no book created
    book_count = test_db.query(Book).count()
    assert book_count == 0
    
    # Verify failure audited
    audit_failed = test_db.query(CatalogueAudit).filter(
        CatalogueAudit.pending_id == pending.id,
        CatalogueAudit.action == 'insert_failed'
    ).first()
    assert audit_failed is not None
    assert 'Title is required' in audit_failed.details


def test_insert_with_isbn_10_only(test_db: Session):
    """Test insertion with only ISBN-10 (no ISBN-13)."""
    pending = PendingCatalogue(
        isbn="0132350882",
        title="Test Book ISBN-10",
        authors=["Test Author"],
        total_copies=1,
        output_json={
            "isbn_10": "0132350882",
            "title": "Test Book ISBN-10",
            "authors": ["Test Author"]
        },
        status="approved"
    )
    test_db.add(pending)
    test_db.commit()
    
    result = insert_pending_book(test_db, pending.id)
    
    assert result['success'] is True
    book = test_db.query(Book).filter(Book.book_id == result['book_id']).first()
    assert book.isbn_10 == "0132350882"
    assert book.isbn_13 is None
    assert book.isbn == "0132350882"  # Canonical fallback to isbn_10


def test_insert_with_isbn_13_only(test_db: Session):
    """Test insertion with only ISBN-13 (no ISBN-10)."""
    pending = PendingCatalogue(
        isbn="9780132350884",
        title="Test Book ISBN-13",
        authors=["Test Author"],
        total_copies=1,
        output_json={
            "isbn_13": "9780132350884",
            "title": "Test Book ISBN-13",
            "authors": ["Test Author"]
        },
        status="approved"
    )
    test_db.add(pending)
    test_db.commit()
    
    result = insert_pending_book(test_db, pending.id)
    
    assert result['success'] is True
    book = test_db.query(Book).filter(Book.book_id == result['book_id']).first()
    assert book.isbn_13 == "9780132350884"
    assert book.isbn_10 is None
    assert book.isbn == "9780132350884"  # Canonical (isbn_13 preferred)


def test_insert_with_both_isbns(test_db: Session, sample_pending_approved):
    """Test insertion with both ISBN-10 and ISBN-13."""
    pending = sample_pending_approved
    
    result = insert_pending_book(test_db, pending.id)
    
    assert result['success'] is True
    book = test_db.query(Book).filter(Book.book_id == result['book_id']).first()
    assert book.isbn_13 == "9780132350884"
    assert book.isbn_10 == "0132350882"
    assert book.isbn == "9780132350884"  # Canonical (isbn_13 preferred)


def test_insert_without_publisher(test_db: Session):
    """Test insertion without publisher (nullable field)."""
    pending = PendingCatalogue(
        isbn="9780132350884",
        title="Test Book No Publisher",
        authors=["Test Author"],
        total_copies=1,
        output_json={
            "isbn_13": "9780132350884",
            "title": "Test Book No Publisher",
            "authors": ["Test Author"]
            # No publisher field
        },
        status="approved"
    )
    test_db.add(pending)
    test_db.commit()
    
    result = insert_pending_book(test_db, pending.id)
    
    assert result['success'] is True
    book = test_db.query(Book).filter(Book.book_id == result['book_id']).first()
    assert book.publisher_id is None


def test_insert_with_empty_authors(test_db: Session):
    """Test insertion with empty authors list creates placeholder."""
    pending = PendingCatalogue(
        isbn="9780132350884",
        title="Test Book No Authors",
        authors=[],
        total_copies=1,
        output_json={
            "isbn_13": "9780132350884",
            "title": "Test Book No Authors",
            "authors": []
        },
        status="approved"
    )
    test_db.add(pending)
    test_db.commit()
    
    result = insert_pending_book(test_db, pending.id)
    
    assert result['success'] is True
    
    # Verify Unknown Author was created
    unknown_author = test_db.query(Author).filter(
        Author.full_name == "Unknown Author"
    ).first()
    assert unknown_author is not None


def test_pending_not_found(test_db: Session):
    """Test error when pending_id doesn't exist."""
    with pytest.raises(ValueError) as exc_info:
        insert_pending_book(test_db, 99999)
    
    assert "not found" in str(exc_info.value).lower()


def test_pending_not_approved(test_db: Session):
    """Test error when pending entry is not in 'approved' state."""
    pending = PendingCatalogue(
        isbn="9780132350884",
        title="Test Book",
        authors=["Test Author"],
        total_copies=1,
        output_json={"title": "Test Book", "authors": ["Test Author"]},
        status="pending"  # Not approved
    )
    test_db.add(pending)
    test_db.commit()
    
    with pytest.raises(ValueError) as exc_info:
        insert_pending_book(test_db, pending.id)
    
    assert "must be 'approved'" in str(exc_info.value)
    assert "pending" in str(exc_info.value)


def test_missing_title(test_db: Session):
    """Test error when required title field is missing."""
    pending = PendingCatalogue(
        isbn="9780132350884",
        title="Placeholder",
        authors=["Test Author"],
        total_copies=1,
        output_json={
            "isbn_13": "9780132350884",
            "authors": ["Test Author"]
            # Missing title
        },
        status="approved"
    )
    test_db.add(pending)
    test_db.commit()
    
    with pytest.raises(ValueError) as exc_info:
        insert_pending_book(test_db, pending.id)
    
    assert "Title is required" in str(exc_info.value)


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
