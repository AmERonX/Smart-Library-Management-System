"""
Book Insertion Service - Phase 1
Core business logic for inserting approved books into the main catalogue.

This module provides transaction-safe, idempotent insertion of books from pending_catalogue
into the main books table with full ISBN support (ISBN-10 and ISBN-13), author/publisher
upserts, and comprehensive audit logging.

Key Features:
- ISBN-aware: Supports both ISBN-10 and ISBN-13 with intelligent normalization
- Idempotent: Safe to retry; prevents duplicate books and double-adding copies
- Transactional: All operations in a single DB transaction with rollback on failure
- Auditable: Full audit trail for every action (inserted, copies_added, failures)
- Upsert semantics: Authors and publishers are upserted to avoid duplicates

Design Philosophy:
- Pure Python functions (no HTTP handling) for testability
- Explicit error handling with detailed logging
- Conservative approach: prefer data integrity over convenience
"""

import logging
import json
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models import (
    PendingCatalogue,
    CatalogueAudit,
    Book,
    Author,
    Publisher,
    BookAuthor
)

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS - ISBN Normalization
# ============================================================================

def normalize_isbn(isbn: Optional[str]) -> Optional[str]:
    """
    Normalize ISBN by removing hyphens, spaces, and converting to uppercase.
    
    Args:
        isbn: Raw ISBN string (may contain hyphens, spaces)
        
    Returns:
        Normalized ISBN string (digits only) or None if input is None/empty
        
    Example:
        >>> normalize_isbn("978-0-13-235088-4")
        "9780132350884"
        >>> normalize_isbn("0-13-235088-2")
        "0132350882"
    """
    if not isbn:
        return None
    
    # Remove hyphens, spaces, and convert to uppercase (for ISBN with 'X' check digit)
    normalized = isbn.replace('-', '').replace(' ', '').strip().upper()
    
    # Validate: should be 10 or 13 characters (digits or 'X' for ISBN-10)
    if not re.match(r'^(\d{9}[\dX]|\d{13})$', normalized):
        logger.warning(f"Invalid ISBN format after normalization: {isbn} -> {normalized}")
        return None
    
    return normalized


def infer_isbn_type(isbn: str) -> Optional[str]:
    """
    Infer ISBN type (isbn_10 or isbn_13) based on length.
    
    Args:
        isbn: Normalized ISBN string
        
    Returns:
        'isbn_10', 'isbn_13', or None if invalid
    """
    if not isbn:
        return None
    
    length = len(isbn)
    if length == 10:
        return 'isbn_10'
    elif length == 13:
        return 'isbn_13'
    else:
        return None


# ============================================================================
# HELPER FUNCTIONS - Database Upserts
# ============================================================================

def get_or_create_publisher(db: Session, publisher_name: Optional[str]) -> Optional[int]:
    """
    Get existing publisher or create new one (upsert semantics).
    Uses PostgreSQL INSERT ... ON CONFLICT DO NOTHING for concurrency safety.
    
    Args:
        db: Database session
        publisher_name: Publisher name (will be trimmed)
        
    Returns:
        Publisher ID or None if publisher_name is empty
        
    Note:
        This function does NOT commit; caller must commit the transaction.
    """
    if not publisher_name or not publisher_name.strip():
        logger.debug("Publisher name is empty, skipping publisher creation")
        return None
    
    publisher_name = publisher_name.strip()
    
    # Try to find existing publisher
    existing = db.query(Publisher).filter(Publisher.name == publisher_name).first()
    if existing:
        logger.debug(f"Found existing publisher: {publisher_name} (ID: {existing.publisher_id})")
        return existing.publisher_id
    
    # Create new publisher using upsert (PostgreSQL specific)
    try:
        stmt = pg_insert(Publisher).values(name=publisher_name)
        stmt = stmt.on_conflict_do_nothing(index_elements=['name'])
        db.execute(stmt)
        db.flush()  # Flush to get the ID
        
        # Retrieve the publisher (either just inserted or inserted by concurrent transaction)
        publisher = db.query(Publisher).filter(Publisher.name == publisher_name).first()
        logger.info(f"Created/retrieved publisher: {publisher_name} (ID: {publisher.publisher_id})")
        return publisher.publisher_id
    
    except SQLAlchemyError as e:
        logger.error(f"Error upserting publisher '{publisher_name}': {str(e)}")
        raise


def get_or_create_author(db: Session, author_name: str) -> int:
    """
    Get existing author or create new one (upsert semantics).
    Uses PostgreSQL INSERT ... ON CONFLICT DO NOTHING for concurrency safety.
    
    Args:
        db: Database session
        author_name: Author full name (will be trimmed)
        
    Returns:
        Author ID
        
    Note:
        This function does NOT commit; caller must commit the transaction.
        If author_name is empty, creates a placeholder "Unknown Author <timestamp>".
    """
    # Handle empty author names with placeholder
    if not author_name or not author_name.strip():
        timestamp = datetime.now(timezone.utc).isoformat()
        author_name = f"Unknown Author {timestamp}"
        logger.warning(f"Empty author name provided, using placeholder: {author_name}")
    else:
        author_name = author_name.strip()
    
    # Try to find existing author
    existing = db.query(Author).filter(Author.full_name == author_name).first()
    if existing:
        logger.debug(f"Found existing author: {author_name} (ID: {existing.author_id})")
        return existing.author_id
    
    # Create new author using upsert (PostgreSQL specific)
    try:
        stmt = pg_insert(Author).values(full_name=author_name, bio=None)
        stmt = stmt.on_conflict_do_nothing(index_elements=['full_name'])
        db.execute(stmt)
        db.flush()  # Flush to get the ID
        
        # Retrieve the author (either just inserted or inserted by concurrent transaction)
        author = db.query(Author).filter(Author.full_name == author_name).first()
        logger.info(f"Created/retrieved author: {author_name} (ID: {author.author_id})")
        return author.author_id
    
    except SQLAlchemyError as e:
        logger.error(f"Error upserting author '{author_name}': {str(e)}")
        raise


# ============================================================================
# HELPER FUNCTIONS - Book Lookup
# ============================================================================

def find_book_by_isbn(db: Session, isbn_10: Optional[str], isbn_13: Optional[str]) -> Optional[Book]:
    """
    Find existing book by ISBN-13 (preferred) or ISBN-10.
    
    Search order:
    1. isbn_13 (canonical identifier)
    2. isbn_10
    3. Legacy isbn field (for backward compatibility)
    
    Args:
        db: Database session
        isbn_10: Normalized ISBN-10 (10 digits)
        isbn_13: Normalized ISBN-13 (13 digits)
        
    Returns:
        Book object if found, None otherwise
    """
    # Priority 1: Search by ISBN-13 (canonical)
    if isbn_13:
        book = db.query(Book).filter(Book.isbn_13 == isbn_13).first()
        if book:
            logger.debug(f"Found book by ISBN-13: {isbn_13} (book_id: {book.book_id})")
            return book
    
    # Priority 2: Search by ISBN-10
    if isbn_10:
        book = db.query(Book).filter(Book.isbn_10 == isbn_10).first()
        if book:
            logger.debug(f"Found book by ISBN-10: {isbn_10} (book_id: {book.book_id})")
            return book
    
    # Priority 3: Search legacy isbn field (backward compatibility)
    if isbn_13:
        book = db.query(Book).filter(Book.isbn == isbn_13).first()
        if book:
            logger.debug(f"Found book by legacy isbn field (ISBN-13): {isbn_13} (book_id: {book.book_id})")
            return book
    
    if isbn_10:
        book = db.query(Book).filter(Book.isbn == isbn_10).first()
        if book:
            logger.debug(f"Found book by legacy isbn field (ISBN-10): {isbn_10} (book_id: {book.book_id})")
            return book
    
    logger.debug(f"No existing book found for ISBN-10: {isbn_10}, ISBN-13: {isbn_13}")
    return None


def find_book_by_title_authors(db: Session, title: str, author_ids: List[int]) -> Optional[Book]:
    """
    Find existing book by exact title and author match.
    
    This is a fallback for books without ISBNs. Use with caution as it may
    produce false positives for common titles.
    
    TODO: Implement fuzzy matching or normalization for better accuracy.
    
    Args:
        db: Database session
        title: Book title (exact match, case-sensitive)
        author_ids: List of author IDs to match
        
    Returns:
        Book object if found, None otherwise
    """
    if not title or not author_ids:
        return None
    
    # Find books with exact title
    books = db.query(Book).filter(Book.title == title).all()
    
    # Check if any book has the same set of authors
    for book in books:
        book_author_ids = {ba.author_id for ba in book.authors}
        if book_author_ids == set(author_ids):
            logger.debug(f"Found book by title+authors: {title} (book_id: {book.book_id})")
            return book
    
    logger.debug(f"No existing book found for title: {title} with given authors")
    return None


# ============================================================================
# HELPER FUNCTIONS - Book Creation
# ============================================================================

def create_book_and_links(
    db: Session,
    metadata: Dict[str, Any],
    publisher_id: Optional[int],
    author_ids: List[int],
    total_copies: int
) -> Book:
    """
    Create a new book record and link it to authors.
    
    Args:
        db: Database session
        metadata: Dictionary containing book metadata (title, isbn_10, isbn_13, etc.)
        publisher_id: Publisher ID (nullable)
        author_ids: List of author IDs to link
        total_copies: Number of copies to initialize
        
    Returns:
        Created Book object
        
    Note:
        This function does NOT commit; caller must commit the transaction.
    """
    # Extract metadata fields
    isbn_10 = metadata.get('isbn_10')
    isbn_13 = metadata.get('isbn_13')
    
    # Determine canonical ISBN for legacy field (prefer isbn_13)
    canonical_isbn = isbn_13 if isbn_13 else isbn_10
    
    # Create book record
    book = Book(
        isbn=canonical_isbn,  # Legacy field (backward compatibility)
        isbn_10=isbn_10,
        isbn_13=isbn_13,
        title=metadata['title'],
        publisher_id=publisher_id,
        publication_year=metadata.get('publication_year'),
        edition=metadata.get('edition'),
        cover_url=metadata.get('cover_url'),
        total_copies=total_copies,
        available_copies=total_copies
    )
    
    db.add(book)
    db.flush()  # Flush to get book_id
    
    logger.info(f"Created new book: {book.title} (book_id: {book.book_id}, ISBN-13: {isbn_13}, ISBN-10: {isbn_10})")
    
    # Create book-author links
    for author_id in author_ids:
        book_author = BookAuthor(book_id=book.book_id, author_id=author_id)
        db.add(book_author)
        logger.debug(f"Linked book {book.book_id} to author {author_id}")
    
    db.flush()
    return book


def add_copies(db: Session, book: Book, copies_to_add: int) -> None:
    """
    Add copies to an existing book.
    
    Args:
        db: Database session
        book: Book object to update
        copies_to_add: Number of copies to add
        
    Note:
        This function does NOT commit; caller must commit the transaction.
    """
    book.total_copies += copies_to_add
    book.available_copies += copies_to_add
    
    logger.info(f"Added {copies_to_add} copies to book {book.book_id}. "
                f"New totals: {book.total_copies} total, {book.available_copies} available")


# ============================================================================
# HELPER FUNCTIONS - Audit Logging
# ============================================================================

def log_audit(
    db: Session,
    pending_id: int,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    book_id: Optional[int] = None
) -> None:
    """
    Create an audit log entry for the insertion service.
    
    Args:
        db: Database session
        pending_id: ID of pending_catalogue entry
        action: Action type (e.g., 'inserted', 'copies_added', 'insert_failed')
        details: Optional dictionary with additional context (will be JSON-serialized)
        book_id: Optional actual book_id from books table (stored in details)
        
    Note:
        This function does NOT commit; caller must commit the transaction.
        For failure logging, use a separate transaction to ensure audit is persisted.
    """
    # Serialize details to JSON string
    details_str = None
    if details:
        try:
            details_str = json.dumps(details, default=str)
        except (TypeError, ValueError) as e:
            logger.warning(f"Failed to serialize audit details: {e}")
            details_str = str(details)
    
    audit_entry = CatalogueAudit(
        pending_id=pending_id,
        action=action,
        source='insertion_service',
        details=details_str
    )
    
    db.add(audit_entry)
    logger.debug(f"Audit log created: pending_id={pending_id}, action={action}, book_id={book_id}")


# ============================================================================
# MAIN INSERTION FUNCTION
# ============================================================================

def insert_pending_book(db: Session, pending_id: int) -> Dict[str, Any]:
    """
    Main insertion function: Insert approved pending book into main catalogue.
    
    This function is the entry point for the insertion service. It performs the
    complete workflow:
    1. Lock and validate pending_catalogue entry (must be 'approved')
    2. Extract and normalize metadata from output_json
    3. Upsert publisher and authors
    4. Check if book exists by ISBN
    5. If exists: add copies; if new: create book record
    6. Log audit trail
    7. Mark pending_catalogue as 'completed'
    
    The entire operation is transactional and idempotent.
    
    Args:
        db: Database session (transaction will be committed by caller)
        pending_id: ID of pending_catalogue entry to process
        
    Returns:
        Dictionary with result:
        {
            'success': bool,
            'message': str,
            'pending_id': int,
            'book_id': int (if applicable),
            'status': str,
            'action': str ('inserted' or 'copies_added' or 'already_completed')
        }
        
    Raises:
        ValueError: If pending entry not found or not in 'approved' state
        SQLAlchemyError: On database errors (will be caught and logged as audit)
    """
    logger.info(f"Starting insertion for pending_id: {pending_id}")
    
    try:
        # ====================================================================
        # STEP 1: Lock and validate pending_catalogue entry
        # ====================================================================
        
        # Use SELECT FOR UPDATE to lock the row and prevent race conditions
        pending = db.query(PendingCatalogue).filter(
            PendingCatalogue.id == pending_id
        ).with_for_update().first()
        
        if not pending:
            raise ValueError(f"Pending catalogue entry not found: {pending_id}")
        
        # Check idempotency: if already completed, return success
        if pending.status == 'completed':
            logger.info(f"Pending {pending_id} already completed, returning existing result")
            
            # Try to find the book_id from audit logs
            audit = db.query(CatalogueAudit).filter(
                CatalogueAudit.pending_id == pending_id,
                CatalogueAudit.action.in_(['inserted', 'copies_added'])
            ).order_by(CatalogueAudit.timestamp.desc()).first()
            
            book_id = None
            if audit and audit.details:
                try:
                    details = json.loads(audit.details)
                    book_id = details.get('book_id')
                except:
                    pass
            
            return {
                'success': True,
                'message': 'Pending record already completed',
                'pending_id': pending_id,
                'book_id': book_id,
                'status': 'completed',
                'action': 'already_completed'
            }
        
        # Validate status
        if pending.status != 'approved':
            raise ValueError(
                f"Pending record must be 'approved' to insert. Currently: {pending.status}"
            )
        
        # ====================================================================
        # STEP 2: Extract and normalize metadata
        # ====================================================================
        
        # Prefer output_json (librarian-confirmed), fallback to raw_metadata
        metadata_source = pending.output_json if pending.output_json else pending.raw_metadata
        
        if not metadata_source:
            raise ValueError(f"No metadata available for pending_id {pending_id}")
        
        # Extract required fields
        title = metadata_source.get('title')
        if not title:
            raise ValueError(f"Title is required but missing for pending_id {pending_id}")
        
        # Extract and normalize ISBNs
        raw_isbn = metadata_source.get('isbn')
        raw_isbn_10 = metadata_source.get('isbn_10')
        raw_isbn_13 = metadata_source.get('isbn_13')
        
        # Normalize ISBNs
        isbn_10 = normalize_isbn(raw_isbn_10) if raw_isbn_10 else None
        isbn_13 = normalize_isbn(raw_isbn_13) if raw_isbn_13 else None
        
        # If only generic 'isbn' field present, infer type by length
        if not isbn_10 and not isbn_13 and raw_isbn:
            normalized = normalize_isbn(raw_isbn)
            if normalized:
                isbn_type = infer_isbn_type(normalized)
                if isbn_type == 'isbn_10':
                    isbn_10 = normalized
                elif isbn_type == 'isbn_13':
                    isbn_13 = normalized
        
        logger.debug(f"Normalized ISBNs - ISBN-10: {isbn_10}, ISBN-13: {isbn_13}")
        
        # Extract other metadata
        publisher_name = metadata_source.get('publisher')
        publication_year = metadata_source.get('publication_year')
        edition = metadata_source.get('edition')
        cover_url = metadata_source.get('cover_url')
        
        # Extract authors (handle both list and JSON formats)
        authors_raw = metadata_source.get('authors', [])
        if isinstance(authors_raw, str):
            try:
                authors_raw = json.loads(authors_raw)
            except:
                authors_raw = [authors_raw]
        
        if not authors_raw:
            authors_raw = ['Unknown Author']
        
        # Get total_copies from pending_catalogue (source of truth)
        total_copies = pending.total_copies
        
        # ====================================================================
        # STEP 3: Upsert publisher and authors
        # ====================================================================
        
        publisher_id = get_or_create_publisher(db, publisher_name)
        
        author_ids = []
        for author_name in authors_raw:
            author_id = get_or_create_author(db, author_name)
            author_ids.append(author_id)
        
        logger.info(f"Upserted publisher (ID: {publisher_id}) and {len(author_ids)} authors")
        
        # ====================================================================
        # STEP 4: Check if book exists by ISBN
        # ====================================================================
        
        existing_book = find_book_by_isbn(db, isbn_10, isbn_13)
        
        if existing_book:
            # ================================================================
            # CASE A: Book exists - add copies
            # ================================================================
            
            logger.info(f"Book already exists (book_id: {existing_book.book_id}), adding {total_copies} copies")
            
            add_copies(db, existing_book, total_copies)
            
            # Log audit
            log_audit(
                db,
                pending_id=pending_id,
                action='copies_added',
                details={
                    'pending_id': pending_id,
                    'book_id': existing_book.book_id,
                    'added_copies': total_copies,
                    'new_total': existing_book.total_copies,
                    'new_available': existing_book.available_copies,
                    'isbn_10': isbn_10,
                    'isbn_13': isbn_13
                },
                book_id=existing_book.book_id
            )
            
            # Mark pending as completed
            pending.status = 'completed'
            log_audit(db, pending_id=pending_id, action='pending_completed', book_id=existing_book.book_id)
            
            db.commit()
            
            logger.info(f"Successfully added copies for pending_id {pending_id}")
            
            return {
                'success': True,
                'message': 'Existing book updated with additional copies',
                'pending_id': pending_id,
                'book_id': existing_book.book_id,
                'status': 'completed',
                'action': 'copies_added'
            }
        
        else:
            # ================================================================
            # CASE B: New book - insert
            # ================================================================
            
            logger.info(f"Creating new book for pending_id {pending_id}")
            
            # Prepare metadata dictionary
            book_metadata = {
                'title': title,
                'isbn_10': isbn_10,
                'isbn_13': isbn_13,
                'publication_year': publication_year,
                'edition': edition,
                'cover_url': cover_url
            }
            
            # Create book and links
            new_book = create_book_and_links(
                db,
                metadata=book_metadata,
                publisher_id=publisher_id,
                author_ids=author_ids,
                total_copies=total_copies
            )
            
            # Log audit
            log_audit(
                db,
                pending_id=pending_id,
                action='inserted',
                details={
                    'pending_id': pending_id,
                    'book_id': new_book.book_id,
                    'title': title,
                    'isbn_10': isbn_10,
                    'isbn_13': isbn_13,
                    'publisher_id': publisher_id,
                    'author_ids': author_ids,
                    'total_copies': total_copies
                },
                book_id=new_book.book_id
            )
            
            # Mark pending as completed
            pending.status = 'completed'
            log_audit(db, pending_id=pending_id, action='pending_completed', book_id=new_book.book_id)
            
            db.commit()
            
            logger.info(f"Successfully inserted new book (book_id: {new_book.book_id}) for pending_id {pending_id}")
            
            return {
                'success': True,
                'message': 'Book inserted successfully',
                'pending_id': pending_id,
                'book_id': new_book.book_id,
                'status': 'completed',
                'action': 'inserted'
            }
    
    except ValueError as e:
        # Validation errors (bad state, missing data)
        logger.error(f"Validation error for pending_id {pending_id}: {str(e)}")
        
        # Log failure in audit (separate transaction to ensure it's persisted)
        try:
            log_audit(
                db,
                pending_id=pending_id,
                action='insert_failed',
                details={'error': str(e), 'error_type': 'ValueError'}
            )
            db.commit()
        except:
            pass  # Don't fail if audit logging fails
        
        raise
    
    except SQLAlchemyError as e:
        # Database errors
        logger.error(f"Database error for pending_id {pending_id}: {str(e)}")
        db.rollback()
        
        # Log failure in audit (separate transaction)
        try:
            log_audit(
                db,
                pending_id=pending_id,
                action='insert_failed',
                details={'error': str(e), 'error_type': 'SQLAlchemyError'}
            )
            db.commit()
        except:
            pass  # Don't fail if audit logging fails
        
        raise
    
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error for pending_id {pending_id}: {str(e)}")
        db.rollback()
        
        # Log failure in audit (separate transaction)
        try:
            log_audit(
                db,
                pending_id=pending_id,
                action='insert_failed',
                details={'error': str(e), 'error_type': type(e).__name__}
            )
            db.commit()
        except:
            pass  # Don't fail if audit logging fails
        
        raise
