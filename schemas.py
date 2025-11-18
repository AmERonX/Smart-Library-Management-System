"""
Pydantic models for request/response validation in Librarian Confirmation API.
Ensures data integrity and provides automatic API documentation.
"""

import re
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, AliasChoices, EmailStr


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class MetadataFetchRequest(BaseModel):
    """
    Request schema for fetching metadata only (no pending entry created).
    Used by POST /catalogue/fetch-metadata endpoint.
    Title is optional when ISBN is provided.
    """
    isbn: Optional[str] = Field(
        None,
        description="ISBN-10 or ISBN-13 (10 or 13 digits)"
    )
    title: Optional[str] = Field(
        None,
        description="Book title (optional if ISBN provided)"
    )
    authors: Optional[List[str]] = Field(
        default=None,
        description="List of author names"
    )
    total_copies: int = Field(
        default=1,
        ge=1, #ge -> greater than or equal to
        description="Number of copies (not used for metadata fetching)",
        validation_alias=AliasChoices("total_copies", "book_copies"),
    )
    
    @field_validator('isbn')
    @classmethod
    def validate_isbn(cls, v):
        """Validate ISBN format: must be 10 or 13 digits if provided (allows X as ISBN-10 check digit)."""
        if v is not None:
            cleaned = v.replace('-', '').replace(' ', '').upper()
            if not re.match(r'^(\d{9}[\dX]|\d{13})$', cleaned):
                raise ValueError('ISBN must be exactly 10 or 13 digits (ISBN-10 may end with X)')
            return cleaned
        return v
    
    @model_validator(mode='after')
    def validate_isbn_or_title(self):
        """Ensure at least ISBN or title is provided."""
        if not self.isbn and not self.title:
            raise ValueError('Either ISBN or title must be provided')
        # Clean up placeholder title
        if self.title == "Fetching title...":
            self.title = None
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "isbn": "9780132350884",
                "title": None,
                "authors": None,
                "total_copies": 1
            }
        }
    )


class CatalogueAddRequest(BaseModel):
    """
    Request schema for adding a book to pending catalogue.
    Used by POST /catalogue/add endpoint.
    """
    isbn: Optional[str] = Field(
        None,
        description="ISBN-10 or ISBN-13 (10 or 13 digits)"
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Book title (required)"
    )
    authors: Optional[List[str]] = Field(
        default=None,
        description="List of author names"
    )
    total_copies: int = Field(
        default=1,
        ge=1,
        description="Number of copies to add (must be >= 1)",
        validation_alias=AliasChoices("total_copies", "book_copies"),
    )
    
    @field_validator('isbn')
    @classmethod
    def validate_isbn(cls, v):
        """Validate ISBN format: must be 10 or 13 digits if provided (allows X as ISBN-10 check digit)."""
        if v is not None:
            cleaned = v.replace('-', '').replace(' ', '').upper()
            if not re.match(r'^(\d{9}[\dX]|\d{13})$', cleaned):
                raise ValueError('ISBN must be exactly 10 or 13 digits (ISBN-10 may end with X)')
            return cleaned
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "isbn": "9780132350884",
                "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
                "authors": ["Robert C. Martin"],
                "total_copies": 3
            }
        }
    )


# ============================================================================
# SEARCH SCHEMAS
# ============================================================================

class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    mode: Literal["identity", "topical", "hybrid"] = Field("hybrid")
    top_k: int = Field(
        default=10, 
        ge=1, 
        le=50,
        description="Number of results to return (must be between 1 and 50)"
        )
    normalize: bool = Field(
        True,
        description="Normalize results"
        )
    expand: bool = Field(
        False,
        description="Expand results"
        )


class SemanticSearchHit(BaseModel):
    book_id: int
    score: float
    vector_type: str
    title: str
    authors: Optional[List[str]] = None
    publisher: Optional[str] = None
    publication_year: Optional[str] = None


class SemanticSearchResponse(BaseModel):
    query_raw: str
    query_processed: str
    mode: str
    results: List[SemanticSearchHit]


class ConfirmationRequest(BaseModel):
    """
    Request schema for librarian confirmation of book metadata.
    Used by POST /catalogue/confirm/{pending_id} endpoint.
    """
    approved: bool = Field(
        ...,
        description="True to approve, False to reject"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for approval/rejection (required if rejected)"
    )
    
    @model_validator(mode='after')
    def validate_reason_if_rejected(self):
        """Ensure reason is provided when rejecting."""
        if self.approved is False and not self.reason:
            raise ValueError('Reason is required when rejecting metadata')
        return self
    
    model_config = ConfigDict(
        extra='ignore',
        json_schema_extra={
            "example": {
                "approved": True,
                "reason": "Verified metadata with library records"
            }
        }
    )


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class PendingCatalogueResponse(BaseModel):
    """
    Response schema for pending catalogue entry.
    Used by GET /catalogue/pending and POST /catalogue/add endpoints.
    """
    id: int = Field(..., description="Unique pending catalogue ID")
    isbn: Optional[str] = Field(None, description="ISBN")
    title: str = Field(..., description="Book title")
    authors: Optional[List[str]] = Field(None, description="List of authors")
    total_copies: int = Field(..., description="Number of copies")
    raw_metadata: Optional[Dict[str, Any]] = Field(None, description="Fetched metadata")
    output_json: Optional[Dict[str, Any]] = Field(None, description="Finalized metadata")
    status: str = Field(..., description="Current status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    model_config = ConfigDict(from_attributes=True)  # Pydantic v2


class CatalogueAddResponse(BaseModel):
    """
    Response schema for successful book addition to pending catalogue.
    """
    message: str = Field(..., description="Success message")
    pending_id: int = Field(..., description="ID of created pending catalogue entry")
    status: str = Field(..., description="Current status")
    metadata_preview: Optional[Dict[str, Any]] = Field(None, description="Preview of extracted metadata")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Book added to pending catalogue successfully",
                "pending_id": 1,
                "status": "awaiting_confirmation",
                "metadata_preview": {
                    "title": "Clean Code",
                    "authors": ["Robert C. Martin"],
                    "publisher": "Prentice Hall",
                    "publication_year": "2008",
                    "isbn_10": "0132350882",
                    "isbn_13": "9780132350884",
                    "source": "google_books"
                }
            }
        }
    )


class ConfirmationResponse(BaseModel):
    """
    Response schema for confirmation action.
    """
    message: str = Field(..., description="Result message")
    pending_id: int = Field(..., description="ID of pending catalogue entry")
    status: str = Field(..., description="Updated status")
    output_json: Optional[Dict[str, Any]] = Field(None, description="Finalized metadata (if approved)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Metadata approved successfully",
                "pending_id": 1,
                "status": "approved",
                "output_json": {
                    "isbn": "9780132350884",
                    "title": "Clean Code",
                    "authors": ["Robert C. Martin"],
                    "publisher": "Prentice Hall",
                    "publication_year": "2008",
                    "total_copies": 3
                }
            }
        }
    )


class AuditLogResponse(BaseModel):
    """
    Response schema for single audit log entry.
    """
    id: int = Field(..., description="Audit log ID")
    pending_id: int = Field(..., description="Referenced pending catalogue ID")
    action: str = Field(..., description="Action type")
    source: str = Field(..., description="Source of action")
    details: Optional[str] = Field(None, description="Additional details")
    timestamp: datetime = Field(..., description="Action timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class AuditLogsResponse(BaseModel):
    """
    Response schema for list of audit logs.
    """
    message: str = Field(..., description="Response message")
    pending_id: int = Field(..., description="Pending catalogue ID")
    total_entries: int = Field(..., description="Total number of audit entries")
    audit_logs: List[AuditLogResponse] = Field(..., description="List of audit log entries")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Audit logs retrieved successfully",
                "pending_id": 1,
                "total_entries": 3,
                "audit_logs": [
                    {
                        "id": 1,
                        "pending_id": 1,
                        "action": "input_received",
                        "source": "frontend",
                        "details": None,
                        "timestamp": "2025-10-08T06:08:21Z"
                    }
                ]
            }
        }
    )


class ErrorResponse(BaseModel):
    """
    Standard error response schema.
    """
    detail: str = Field(..., description="Error message")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "detail": "Pending catalogue entry not found"
            }
        }
    )


# ============================================================================
# INSERTION SERVICE SCHEMAS (Phase-1)
# ============================================================================

class InsertionResponse(BaseModel):
    """
    Response schema for book insertion endpoint.
    Used by POST /catalogue/insert/{pending_id}.
    """
    message: str = Field(..., description="Result message")
    pending_id: int = Field(..., description="ID of pending catalogue entry")
    book_id: Optional[int] = Field(None, description="ID of created/updated book")
    status: str = Field(..., description="Status of pending entry after insertion")
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "message": "Book inserted successfully",
                    "pending_id": 123,
                    "book_id": 456,
                    "status": "completed"
                },
                {
                    "message": "Existing book updated with additional copies",
                    "pending_id": 123,
                    "book_id": 789,
                    "status": "completed"
                },
                {
                    "message": "Pending record already completed",
                    "pending_id": 123,
                    "book_id": 789,
                    "status": "completed"
                }
            ]
        }
    )

class BookListItem(BaseModel):
    book_id: int
    title: str
    authors: Optional[List[str]] = None
    publisher: Optional[str] = None
    publication_year: Optional[str] = None
    available_copies: int
    cover_url: Optional[str] = None


class BooksListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[BookListItem]


class PublisherRef(BaseModel):
    publisher_id: int
    name: str


class AuthorRef(BaseModel):
    author_id: int
    full_name: str


class BookDetailResponse(BaseModel):
    book_id: int
    title: str
    isbn: Optional[str] = None
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    publication_year: Optional[str] = None
    edition: Optional[str] = None
    cover_url: Optional[str] = None
    total_copies: int
    available_copies: int
    publisher: Optional[PublisherRef] = None
    authors: List[AuthorRef]
    enhanced_metadata: Optional[Dict[str, Any]] = None


class PendingEditRequest(BaseModel):
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    isbn: Optional[str] = None
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    total_copies: Optional[int] = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("total_copies", "book_copies"),
    )
    raw_metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# USER & AUTHENTICATION SCHEMAS
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr = Field(...)
    password: str = Field(..., min_length=6)
    role: Optional[str] = Field(default="student", pattern="^(student|admin|librarian)$")


class UserLoginRequest(BaseModel):
    """User login request"""
    username: str = Field(...)
    password: str = Field(...)


class UserResponse(BaseModel):
    """User profile response"""
    user_id: int
    username: str
    email: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Authentication token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============================================================================
# BORROWING SCHEMAS
# ============================================================================

class BorrowRequest(BaseModel):
    """Request to borrow a book"""
    book_id: int = Field(..., description="ID of book to borrow")
    due_date: Optional[datetime] = Field(None, description="Due date (defaults to 14 days from now)")


class BorrowResponse(BaseModel):
    """Borrow operation response"""
    success: bool
    borrow_id: Optional[int] = None
    reserved: bool = Field(default=False, description="True if book was reserved instead of borrowed")
    message: str


class BorrowRecordResponse(BaseModel):
    """Borrow record details"""
    borrow_id: int
    book_id: int
    book_title: str
    borrow_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    is_overdue: bool = False

    model_config = ConfigDict(from_attributes=True)


class BorrowListResponse(BaseModel):
    """List of borrow records"""
    total: int
    items: List[BorrowRecordResponse]


class ReturnRequest(BaseModel):
    """Request to return a book"""
    borrow_id: int = Field(..., description="ID of borrow record")


class ReturnResponse(BaseModel):
    """Return operation response"""
    success: bool
    fine_created: bool = Field(default=False, description="True if a fine was created for overdue return")
    fine_amount: Optional[Decimal] = None
    message: str


class RenewRequest(BaseModel):
    """Request to renew a book"""
    borrow_id: int = Field(..., description="ID of borrow record")
    new_due_date: Optional[datetime] = Field(None, description="New due date (defaults to 14 days from now)")


class RenewResponse(BaseModel):
    """Renew operation response"""
    success: bool
    borrow_id: int
    new_due_date: datetime
    message: str


# ============================================================================
# RESERVATION SCHEMAS
# ============================================================================

class ReservationRequest(BaseModel):
    """Request to create a reservation"""
    book_id: int = Field(..., description="ID of book to reserve")


class ReservationResponse(BaseModel):
    """Reservation details"""
    reservation_id: int
    book_id: int
    book_title: str
    reservation_date: datetime
    expiry_date: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class ReservationListResponse(BaseModel):
    """List of reservations"""
    total: int
    items: List[ReservationResponse]


# ============================================================================
# FINE SCHEMAS
# ============================================================================

class FineResponse(BaseModel):
    """Fine details"""
    fine_id: int
    borrow_id: int
    book_title: str
    amount: Decimal
    issue_date: datetime
    paid_date: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class FineListResponse(BaseModel):
    """List of fines"""
    total: int
    total_amount: Decimal
    items: List[FineResponse]


class PayFineRequest(BaseModel):
    """Request to pay a fine"""
    fine_id: int = Field(..., description="ID of fine to pay")


class PayFineResponse(BaseModel):
    """Pay fine operation response"""
    success: bool
    fine_id: int
    message: str


# ============================================================================
# USER DASHBOARD SCHEMAS
# ============================================================================

class UserSummaryResponse(BaseModel):
    """User dashboard summary"""
    user_id: int
    username: str
    active_borrows: int
    active_reservations: int
    pending_fines: int
    total_fine_amount: Decimal
    overdue_books: int
