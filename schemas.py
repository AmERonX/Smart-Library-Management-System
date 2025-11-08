"""
Pydantic models for request/response validation in Librarian Confirmation API.
Ensures data integrity and provides automatic API documentation.
"""

import re
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict, AliasChoices


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class CatalogueAddRequest(BaseModel):
    """
    Request schema for adding a book to pending catalogue.
    Used by POST /catalogue/add endpoint. 
    TODO: Update with actual endpoint, Input provided by librarian
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
    top_k: int = Field(10, ge=1, le=50)
    normalize: bool = Field(True)
    expand: bool = Field(False)


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
    TODO: Update with actual endpoint, Input provided by librarian
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
    TODO: Update with actual endpoint, Output provided by librarian
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
