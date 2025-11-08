"""
Pydantic models for request/response validation in Librarian Confirmation API.
Ensures data integrity and provides automatic API documentation.
"""

import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


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
        description="ISBN-10 or ISBN-13 (10 or 13 digits)",
        example="9780132350884"
    )
    title: str = Field(
        ...,
        min_length=1,
        description="Book title (required)",
        example="Clean Code"
    )
    authors: Optional[List[str]] = Field(
        default=None,
        description="List of author names",
        example=["Robert C. Martin"]
    )
    total_copies: int = Field(
        default=1,
        ge=1,  # greater than or equal to 1 (required minimum number of copies)
        description="Number of copies to add (must be >= 1)",
        example=3
    )
    
    @field_validator('isbn')
    @classmethod
    def validate_isbn(cls, v):
        """Validate ISBN format: must be 10 or 13 digits if provided (allows X as ISBN-10 check digit)."""
        if v is not None:
            # Remove hyphens and spaces for validation
            cleaned = v.replace('-', '').replace(' ', '').upper()
            if not re.match(r'^(\d{9}[\dX]|\d{13})$', cleaned):
                raise ValueError('ISBN must be exactly 10 or 13 digits (ISBN-10 may end with X)')
            return cleaned
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "isbn": "9780132350884",
                "title": "Clean Code: A Handbook of Agile Software Craftsmanship",
                "authors": ["Robert C. Martin"],
                "total_copies": 3
            }
        }


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
    edits: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Dictionary of field edits to apply (only if approved=True)",
        example={"publisher": "MIT Press", "publication_year": "2016"}
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for approval/rejection (required if rejected)",
        example="Metadata verified and corrected"
    )
    
    @model_validator(mode='after')
    def validate_reason_if_rejected(self):
        """Ensure reason is provided when rejecting."""
        if self.approved is False and not self.reason:
            raise ValueError('Reason is required when rejecting metadata')
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "approved": True,
                "edits": {
                    "publisher": "Prentice Hall",
                    "publication_year": "2008"
                },
                "reason": "Verified metadata with library records"
            }
        }


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
    
    class Config:
        from_attributes = True  # Pydantic v2 (was orm_mode in v1)


class CatalogueAddResponse(BaseModel):
    """
    Response schema for successful book addition to pending catalogue.
    """
    message: str = Field(..., description="Success message")
    pending_id: int = Field(..., description="ID of created pending catalogue entry")
    status: str = Field(..., description="Current status")
    metadata_preview: Optional[Dict[str, Any]] = Field(None, description="Preview of extracted metadata")
    
    class Config:
        json_schema_extra = {
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


class ConfirmationResponse(BaseModel):
    """
    Response schema for confirmation action.
    """
    message: str = Field(..., description="Result message")
    pending_id: int = Field(..., description="ID of pending catalogue entry")
    status: str = Field(..., description="Updated status")
    output_json: Optional[Dict[str, Any]] = Field(None, description="Finalized metadata (if approved)")
    
    class Config:
        json_schema_extra = {
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
    
    class Config:
        from_attributes = True


class AuditLogsResponse(BaseModel):
    """
    Response schema for list of audit logs.
    """
    message: str = Field(..., description="Response message")
    pending_id: int = Field(..., description="Pending catalogue ID")
    total_entries: int = Field(..., description="Total number of audit entries")
    audit_logs: List[AuditLogResponse] = Field(..., description="List of audit log entries")
    
    class Config:
        json_schema_extra = {
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


class ErrorResponse(BaseModel):
    """
    Standard error response schema.
    """
    detail: str = Field(..., description="Error message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Pending catalogue entry not found"
            }
        }


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
    
    class Config:
        json_schema_extra = {
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
