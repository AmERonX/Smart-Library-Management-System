"""
SQLAlchemy ORM models for Librarian Confirmation & Audit Logging.
Defines database tables for pending catalogue entries and audit trail.
Extended with core library models: Publishers, Authors, Books, BookAuthors.
"""

from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, JSON, CheckConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class PendingCatalogue(Base):
    """
    Model for books awaiting librarian confirmation.
    Stores incoming book metadata before final approval and insertion into main catalogue.
    
    Workflow stages (status field):
    - 'pending': Initial entry, metadata extraction not yet started
    - 'awaiting_confirmation': Metadata extracted, waiting for librarian review
    - 'approved': Librarian approved, ready for final processing
    - 'failed': Rejected by librarian or extraction failed
    - 'completed': Successfully inserted into main catalogue
    """
    __tablename__ = "pending_catalogue"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Book identifiers and basic info
    isbn = Column(String(20), nullable=True, index=True, comment="ISBN-10 or ISBN-13 (legacy field)")
    isbn_10 = Column(String(10), nullable=True, index=True, comment="ISBN-10 format (10 digits)")
    isbn_13 = Column(String(13), nullable=True, index=True, comment="ISBN-13 format (13 digits, canonical)")
    title = Column(Text, nullable=False, comment="Book title")
    authors = Column(JSON, nullable=True, comment="Array of author names (stored as JSON for SQLite compatibility)")
    total_copies = Column(Integer, nullable=False, default=1, comment="Number of copies to add")
    
    # Metadata storage
    raw_metadata = Column(
        JSON,
        nullable=True,
        comment="Fetched metadata from external APIs (JSON format)"
    )
    output_json = Column(
        JSON,
        nullable=True,
        comment="Finalized metadata after librarian confirmation (JSON format)"
    )
    
    # Status tracking
    status = Column(
        String(30),
        nullable=False,
        default='pending',
        index=True,
        comment="Pipeline stage: pending/awaiting_confirmation/approved/failed/completed"
    )
    
    # Timestamps (UTC)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Entry creation timestamp (UTC)"
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        onupdate=func.now(),
        comment="Last update timestamp (UTC)"
    )
    
    def __repr__(self):
        return f"<PendingCatalogue(id={self.id}, isbn={self.isbn}, title={self.title}, status={self.status})>"


class CatalogueAudit(Base):
    """
    Model for audit logging of all catalogue-related actions.
    Provides full traceability for accountability and debugging.
    
    Common action types:
    - 'input_received': Initial book entry created
    - 'metadata_extracted': External API metadata fetched
    - 'approved': Librarian approved the metadata
    - 'rejected': Librarian rejected the metadata
    - 'completed': Book successfully added to main catalogue
    - 'error': Error occurred during processing
    """
    __tablename__ = "catalogue_audit"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Reference to pending catalogue entry
    pending_id = Column(
        Integer,
        ForeignKey('pending_catalogue.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        comment="References pending_catalogue.id"
    )
    
    # Action details
    action = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Action type (e.g., 'input_received', 'approved', 'rejected')"
    )
    source = Column(
        String(50),
        nullable=False,
        comment="Source of action (e.g., 'frontend', 'librarian', 'metadata_pipeline')"
    )
    details = Column(
        Text,
        nullable=True,
        comment="Optional message or JSON note with additional context"
    )
    
    # Timestamp (UTC)
    timestamp = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Action timestamp (UTC)"
    )
    
    def __repr__(self):
        return f"<CatalogueAudit(id={self.id}, pending_id={self.pending_id}, action={self.action}, timestamp={self.timestamp})>"


# ============================================================================
# CORE LIBRARY MODELS (for Book Insertion Service)
# ============================================================================

class Publisher(Base):
    """
    Model for book publishers.
    Stores unique publisher names with upsert semantics to avoid duplicates.
    """
    __tablename__ = "publishers"
    
    publisher_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(Text, nullable=False, unique=True, comment="Publisher name (unique)")
    
    # Relationships
    books = relationship("Book", back_populates="publisher")
    
    def __repr__(self):
        return f"<Publisher(id={self.publisher_id}, name={self.name})>"


class Author(Base):
    """
    Model for book authors.
    Stores unique author names with upsert semantics to avoid duplicates.
    """
    __tablename__ = "authors"
    
    author_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name = Column(Text, nullable=False, unique=True, comment="Author full name (unique)")
    bio = Column(Text, nullable=True, comment="Author biography (optional)")
    
    # Relationships
    books = relationship("BookAuthor", back_populates="author")
    
    def __repr__(self):
        return f"<Author(id={self.author_id}, name={self.full_name})>"


class Book(Base):
    """
    Model for books in the main catalogue.
    Supports both ISBN-10 and ISBN-13 with isbn_13 as canonical identifier.
    
    Key fields:
    - isbn: Legacy field (kept for backward compatibility)
    - isbn_10: ISBN-10 format (10 digits)
    - isbn_13: ISBN-13 format (13 digits, preferred canonical)
    - Different ISBNs = different editions (separate book rows)
    """
    __tablename__ = "books"
    
    book_id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # ISBN fields (support multiple formats)
    isbn = Column(String(20), nullable=True, unique=True, comment="Legacy ISBN field (backward compatibility)")
    isbn_10 = Column(String(10), nullable=True, index=True, comment="ISBN-10 format")
    isbn_13 = Column(String(13), nullable=True, unique=True, index=True, comment="ISBN-13 format (canonical)")
    
    # Core metadata
    title = Column(Text, nullable=False, comment="Book title")
    publisher_id = Column(Integer, ForeignKey('publishers.publisher_id'), nullable=True, comment="Foreign key to publishers")
    publication_year = Column(String(10), nullable=True, comment="Publication year (string for flexibility)")
    edition = Column(String(50), nullable=True, comment="Edition information")
    cover_url = Column(Text, nullable=True, comment="URL to book cover image")
    
    # Copy management
    total_copies = Column(Integer, nullable=False, default=1, comment="Total number of copies")
    available_copies = Column(Integer, nullable=False, default=1, comment="Number of available copies")
    
    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=True, onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint('available_copies <= total_copies', name='check_available_lte_total'),
        CheckConstraint('available_copies >= 0', name='check_available_gte_zero'),
    )
    
    # Relationships
    publisher = relationship("Publisher", back_populates="books")
    authors = relationship("BookAuthor", back_populates="book")
    
    def __repr__(self):
        return f"<Book(id={self.book_id}, title={self.title}, isbn_13={self.isbn_13}, isbn_10={self.isbn_10})>"


class BookAuthor(Base):
    """
    Many-to-many association table linking books and authors.
    A book can have multiple authors, and an author can write multiple books.
    """
    __tablename__ = "book_authors"
    
    book_id = Column(Integer, ForeignKey('books.book_id', ondelete='CASCADE'), primary_key=True)
    author_id = Column(Integer, ForeignKey('authors.author_id', ondelete='CASCADE'), primary_key=True)
    
    # Relationships
    book = relationship("Book", back_populates="authors")
    author = relationship("Author", back_populates="books")
    
    def __repr__(self):
        return f"<BookAuthor(book_id={self.book_id}, author_id={self.author_id})>"
