"""
Catalogue routes for Librarian Confirmation & Audit Logging.
Implements the complete workflow with full audit trail.
"""

import logging
from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from database import get_db, Base
from models import PendingCatalogue, CatalogueAudit
from schemas import (
    CatalogueAddRequest,
    MetadataFetchRequest,
    CatalogueAddResponse,
    PendingCatalogueResponse,
    PendingEditRequest,
    ConfirmationRequest,
    ConfirmationResponse,
    AuditLogsResponse,
    AuditLogResponse
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/catalogue",
    tags=["Catalogue Management"],
    responses={
        404: {"description": "Not found"},
        400: {"description": "Bad request"},
        500: {"description": "Internal server error"}
    }
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_audit_log(
    db: Session,
    pending_id: int,
    action: str,
    source: str,
    details: str = None
) -> CatalogueAudit:
    """
    Create an audit log entry for traceability.
    
    Args:
        db: Database session
        pending_id: ID of pending catalogue entry
        action: Action type (e.g., 'input_received', 'approved')
        source: Source of action (e.g., 'frontend', 'librarian')
        details: Optional additional details
        
    Returns:
        Created audit log entry
    """
    audit_entry = CatalogueAudit(
        pending_id=pending_id,
        action=action,
        source=source,
        details=details
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    
    logger.info(f"Audit log created: pending_id={pending_id}, action={action}, source={source}")
    return audit_entry


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.post("/fetch-metadata")
async def fetch_metadata_only(
    request: MetadataFetchRequest,
    db: Session = Depends(get_db)
):
    """
    Fetch metadata from external APIs without creating a pending entry.
    Used for preview before submission.
    
    This endpoint:
    1. Validates input (ISBN format if provided)
    2. Fetches metadata from Open Library and Google Books APIs
    3. Returns metadata preview without creating any database entries
    
    Args:
        request: Book input data (isbn, title, authors)
        db: Database session (injected, not used but required for dependency)
        
    Returns:
        Dictionary with success flag and metadata_preview
        
    Raises:
        HTTPException 400: If validation fails
        HTTPException 500: If metadata fetching fails
    """
    try:
        logger.info(f"Fetching metadata (preview only): isbn={request.isbn}, title={request.title}")
        
        # Import metadata fetching functions from main.py
        from main import (
            fetch_openlibrary_metadata,
            fetch_googlebooks_metadata,
            merge_metadata,
            BookInput
        )
        
        # Create BookInput for metadata fetching
        # Title is already cleaned by the schema validator
        book_input = BookInput(
            isbn=request.isbn,
            title=request.title,
            authors=request.authors,
            total_copies=1  # Not used for metadata fetching
        )
        
        # Try Open Library first (only if ISBN provided)
        primary_metadata = None
        if request.isbn:
            primary_metadata = fetch_openlibrary_metadata(request.isbn)
        
        # Try Google Books as fallback
        fallback_metadata = None
        if request.isbn:
            fallback_metadata = fetch_googlebooks_metadata(isbn=request.isbn)
        elif request.title:
            fallback_metadata = fetch_googlebooks_metadata(
                title=request.title,
                authors=request.authors
            )
        
        # Merge metadata from both sources
        merged_metadata = merge_metadata(primary_metadata, fallback_metadata, book_input)
        
        if merged_metadata:
            metadata_preview = {
                "title": merged_metadata.get('title'),
                "authors": merged_metadata.get('authors'),
                "publisher": merged_metadata.get('publisher'),
                "publication_year": merged_metadata.get('publication_year'),
                "isbn_10": merged_metadata.get('isbn_10'),
                "isbn_13": merged_metadata.get('isbn_13'),
                "source": merged_metadata.get('source')
            }
            
            return {
                "success": True,
                "metadata_preview": metadata_preview
            }
        else:
            return {
                "success": False,
                "metadata_preview": None,
                "message": "No metadata found from external APIs"
            }
            
    except Exception as e:
        logger.error(f"Error fetching metadata: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metadata: {str(e)}"
        )


@router.post("/add", response_model=CatalogueAddResponse, status_code=status.HTTP_201_CREATED)
async def add_book_to_pending_catalogue(
    request: CatalogueAddRequest,
    db: Session = Depends(get_db)
):
    """
    Add a book to the pending catalogue with automatic metadata extraction.
    
    This unified endpoint:
    1. Validates input (ISBN format, required fields)
    2. Creates a pending catalogue entry with status='pending'
    3. Fetches metadata from Open Library and Google Books APIs
    4. Updates pending entry with raw_metadata and status='awaiting_confirmation'
    5. Logs audit trail for all actions
    
    If metadata extraction fails, the entry is still created with status='failed'
    so librarian can manually enter metadata.
    
    Args:
        request: Book input data (isbn, title, authors, total_copies)
        db: Database session (injected)
        
    Returns:
        Success response with pending_id, status, and metadata preview
        
    Raises:
        HTTPException 400: If validation fails
        HTTPException 500: If database operation fails
    """
    try:
        logger.info(f"Adding book to pending catalogue: title={request.title}, isbn={request.isbn}")
        
        # Ensure required tables exist for the current DB bind (useful in test DBs)
        try:
            insp = inspect(db.bind)
            if not insp.has_table("pending_catalogue"):
                Base.metadata.create_all(bind=db.bind)
        except Exception:
            pass

        # Step 1: Create pending catalogue entry with status='pending'
        # Clean up placeholder title if present
        title = request.title if request.title != "Fetching title..." else ""
        
        pending_entry = PendingCatalogue(
            isbn=request.isbn,
            title=title,
            authors=request.authors,
            total_copies=request.total_copies,
            raw_metadata=None,
            output_json=None,
            status='pending'
        )
        
        db.add(pending_entry)
        db.commit()
        db.refresh(pending_entry)
        
        logger.info(f"Created pending catalogue entry: id={pending_entry.id}")
        
        # Step 2: Create audit log for input received
        create_audit_log(
            db=db,
            pending_id=pending_entry.id,
            action='input_received',
            source='frontend',
            details=f"Book added: {title or request.isbn or 'Unknown'}"
        )
        
        # Step 3: Fetch metadata from external APIs
        metadata_preview = None
        try:
            # Import metadata fetching functions from main.py
            from main import (
                fetch_openlibrary_metadata,
                fetch_googlebooks_metadata,
                merge_metadata,
                BookInput
            )
            
            logger.info(f"Fetching metadata for pending_id={pending_entry.id}")
            
            # Create BookInput for metadata fetching
            # Use cleaned title (not placeholder)
            book_input = BookInput(
                isbn=request.isbn,
                title=title if title else None,
                authors=request.authors,
                total_copies=request.total_copies
            )
            
            # Try Open Library first
            primary_metadata = None
            if request.isbn:
                primary_metadata = fetch_openlibrary_metadata(request.isbn)
            
            # Try Google Books as fallback
            fallback_metadata = None
            if request.isbn:
                fallback_metadata = fetch_googlebooks_metadata(isbn=request.isbn)
            elif request.title:
                fallback_metadata = fetch_googlebooks_metadata(
                    title=request.title,
                    authors=request.authors
                )
            
            # Merge metadata from both sources
            merged_metadata = merge_metadata(primary_metadata, fallback_metadata, book_input)
            
            if merged_metadata:
                # Step 4: Update pending entry with fetched metadata
                pending_entry.raw_metadata = merged_metadata
                pending_entry.status = 'awaiting_confirmation'
                db.commit()
                db.refresh(pending_entry)
                
                logger.info(f"Metadata extracted successfully for pending_id={pending_entry.id}")
                
                # Create audit log for successful extraction
                create_audit_log(
                    db=db,
                    pending_id=pending_entry.id,
                    action='metadata_extracted',
                    source='metadata_pipeline',
                    details=f"Source: {merged_metadata.get('source')}"
                )
                
                # Create metadata preview for response
                metadata_preview = {
                    "title": merged_metadata.get('title'),
                    "authors": merged_metadata.get('authors'),
                    "publisher": merged_metadata.get('publisher'),
                    "publication_year": merged_metadata.get('publication_year'),
                    "isbn_10": merged_metadata.get('isbn_10'),
                    "isbn_13": merged_metadata.get('isbn_13'),
                    "source": merged_metadata.get('source')
                }
            else:
                # Metadata extraction failed
                pending_entry.status = 'failed'
                db.commit()
                db.refresh(pending_entry)
                
                logger.warning(f"Metadata extraction failed for pending_id={pending_entry.id}")
                
                # Create audit log for failed extraction
                create_audit_log(
                    db=db,
                    pending_id=pending_entry.id,
                    action='metadata_extraction_failed',
                    source='metadata_pipeline',
                    details="No metadata found from external APIs"
                )
        
        except Exception as e:
            # Metadata extraction error - log but don't fail the request
            logger.error(f"Error during metadata extraction: {str(e)}")
            pending_entry.status = 'failed'
            db.commit()
            db.refresh(pending_entry)
            
            create_audit_log(
                db=db,
                pending_id=pending_entry.id,
                action='metadata_extraction_failed',
                source='metadata_pipeline',
                details=f"Error: {str(e)}"
            )
        
        # Step 5: Return response
        return CatalogueAddResponse(
            message="Book added to pending catalogue successfully" if pending_entry.status == 'awaiting_confirmation' 
                    else "Book added but metadata extraction failed. Please enter manually.",
            pending_id=pending_entry.id,
            status=pending_entry.status,
            metadata_preview=metadata_preview
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding book to pending catalogue: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add book to pending catalogue: {str(e)}"
        )


@router.get("/pending/{pending_id}", response_model=PendingCatalogueResponse)
async def get_pending_by_id(pending_id: int, db: Session = Depends(get_db)):
    try:
        pending_entry = db.query(PendingCatalogue).filter(PendingCatalogue.id == pending_id).first()
        if not pending_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pending catalogue entry with id {pending_id} not found"
            )
        return pending_entry
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pending entry {pending_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending entry: {str(e)}"
        )


@router.patch("/pending/{pending_id}", response_model=PendingCatalogueResponse)
async def update_pending_entry(
    pending_id: int,
    request: PendingEditRequest,
    db: Session = Depends(get_db)
):
    try:
        pending_entry = db.query(PendingCatalogue).filter(PendingCatalogue.id == pending_id).first()
        if not pending_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pending catalogue entry with id {pending_id} not found"
            )
        if pending_entry.status in ["approved", "completed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit entry with status '{pending_entry.status}'"
            )

        changed = []

        if request.raw_metadata is not None:
            base = dict(pending_entry.raw_metadata or {})
            base.update(request.raw_metadata)
            pending_entry.raw_metadata = base
            changed.append("raw_metadata")

        if request.title is not None:
            pending_entry.title = request.title
            if pending_entry.raw_metadata is None:
                pending_entry.raw_metadata = {}
            pending_entry.raw_metadata["title"] = request.title
            changed.append("title")

        if request.authors is not None:
            pending_entry.authors = request.authors
            if pending_entry.raw_metadata is None:
                pending_entry.raw_metadata = {}
            pending_entry.raw_metadata["authors"] = request.authors
            changed.append("authors")

        if request.isbn is not None:
            pending_entry.isbn = request.isbn
            if pending_entry.raw_metadata is None:
                pending_entry.raw_metadata = {}
            pending_entry.raw_metadata["isbn"] = request.isbn
            changed.append("isbn")

        if request.isbn_10 is not None:
            pending_entry.isbn_10 = request.isbn_10
            if pending_entry.raw_metadata is None:
                pending_entry.raw_metadata = {}
            pending_entry.raw_metadata["isbn_10"] = request.isbn_10
            changed.append("isbn_10")

        if request.isbn_13 is not None:
            pending_entry.isbn_13 = request.isbn_13
            if pending_entry.raw_metadata is None:
                pending_entry.raw_metadata = {}
            pending_entry.raw_metadata["isbn_13"] = request.isbn_13
            changed.append("isbn_13")

        if request.total_copies is not None:
            pending_entry.total_copies = int(request.total_copies)
            if pending_entry.raw_metadata is None:
                pending_entry.raw_metadata = {}
            pending_entry.raw_metadata["total_copies"] = int(request.total_copies)
            changed.append("total_copies")

        # Validate total_copies before commit
        if pending_entry.total_copies is None or int(pending_entry.total_copies) < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="total_copies must be >= 1. Please PATCH with a valid total_copies value."
            )

        db.commit()
        db.refresh(pending_entry)

        try:
            create_audit_log(
                db=db,
                pending_id=pending_id,
                action="pending_edited",
                source="librarian",
                details=("fields: " + ", ".join(changed)) if changed else "no changes"
            )
        except Exception:
            pass

        return pending_entry
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating pending entry {pending_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update pending entry: {str(e)}"
        )
@router.get("/pending", response_model=List[PendingCatalogueResponse])
async def get_pending_books(db: Session = Depends(get_db)):
    """
    Retrieve all books awaiting librarian confirmation.
    
    Returns all entries with status='awaiting_confirmation' or 'failed', ordered by
    creation date (oldest first) for FIFO processing. Failed entries allow librarians
    to manually enter metadata when API extraction fails. Rejected and completed entries
    are excluded from this list.
    
    Args:
        db: Database session (injected)
        
    Returns:
        List of pending catalogue entries
        
    Raises:
        HTTPException 500: If database query fails
    """
    try:
        logger.info("Fetching all pending catalogue entries")
        
        pending_books = db.query(PendingCatalogue).filter(
            PendingCatalogue.status.in_(['awaiting_confirmation', 'failed'])
        ).order_by(PendingCatalogue.created_at.asc()).all()
        
        logger.info(f"Found {len(pending_books)} pending catalogue entries")
        
        return pending_books
        
    except Exception as e:
        logger.error(f"Error fetching pending books: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending books: {str(e)}"
        )


@router.post("/confirm/{pending_id}", response_model=ConfirmationResponse)
async def confirm_book_metadata(
    pending_id: int,
    request: ConfirmationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Confirm or reject book metadata after librarian review.
    
    This endpoint handles the librarian's decision on book metadata:
    
    **If approved=True:**
    1. Merges any edits into raw_metadata
    2. Creates output_json with finalized metadata
    3. Sets status='approved'
    4. Logs audit entry with action='approved'
    
    **If approved=False:**
    1. Sets status='failed'
    2. Logs audit entry with action='rejected' and reason
    
    All operations are atomic (transaction-based).
    
    Args:
        pending_id: ID of pending catalogue entry
        request: Confirmation data (approved, edits, reason)
        db: Database session (injected)
        
    Returns:
        Confirmation result with updated status and output_json
        
    Raises:
        HTTPException 404: If pending entry not found
        HTTPException 400: If entry is not in awaiting_confirmation status
        HTTPException 500: If database operation fails
    """
    try:
        logger.info(f"Processing confirmation for pending_id={pending_id}, approved={request.approved}")
        
        # Fetch pending catalogue entry
        pending_entry = db.query(PendingCatalogue).filter(
            PendingCatalogue.id == pending_id
        ).first()
        
        if not pending_entry:
            logger.warning(f"Pending catalogue entry not found: id={pending_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pending catalogue entry with id {pending_id} not found"
            )
        
        # Validate status (allow both awaiting_confirmation and failed)
        if pending_entry.status not in ['awaiting_confirmation', 'failed']:
            logger.warning(f"Invalid status for confirmation: id={pending_id}, status={pending_entry.status}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm entry with status '{pending_entry.status}'. Expected 'awaiting_confirmation' or 'failed'."
            )
        
        # Handle approval
        if request.approved:
            logger.info(f"Approving metadata for pending_id={pending_id}")
            
            # Start with raw_metadata or empty dict
            base_metadata = dict(pending_entry.raw_metadata or {})
            
            # Create output_json with complete metadata
            output_json = {
                # Prefer API-fetched (and possibly edited) metadata; fallback to original input only if missing
                "isbn": base_metadata.get("isbn") or pending_entry.isbn,
                "isbn_10": base_metadata.get("isbn_10"),
                "isbn_13": base_metadata.get("isbn_13"),
                "title": base_metadata.get("title") or pending_entry.title,
                "authors": base_metadata.get("authors") or (pending_entry.authors or []),
                "publisher": base_metadata.get("publisher"),
                "publication_year": base_metadata.get("publication_year"),
                "edition": base_metadata.get("edition"),
                "description": base_metadata.get("description"),
                "cover_url": base_metadata.get("cover_url"),
                "categories": base_metadata.get("categories"),
                "total_copies": pending_entry.total_copies,
                "keywords": base_metadata.get("keywords"),
                "embeddings": base_metadata.get("embeddings"),
                "source": "librarian_confirmation"
            }
            
            # Update pending entry
            pending_entry.raw_metadata = base_metadata
            pending_entry.output_json = output_json
            pending_entry.status = 'approved'
            
            # Create audit log
            create_audit_log(
                db=db,
                pending_id=pending_id,
                action='approved',
                source='librarian',
                details=request.reason or "Metadata approved"
            )
            
            db.commit()
            db.refresh(pending_entry)

            # Enhancement now triggers automatically after insertion; no background task here

            logger.info(f"Successfully approved metadata for pending_id={pending_id}")
            
            return ConfirmationResponse(
                message="Metadata approved successfully",
                pending_id=pending_id,
                status=pending_entry.status,
                output_json=output_json
            )
        
        # Handle rejection
        else:
            logger.info(f"Rejecting metadata for pending_id={pending_id}")
            
            # Update status to rejected
            pending_entry.status = 'rejected'
            
            # Create audit log with rejection reason
            create_audit_log(
                db=db,
                pending_id=pending_id,
                action='rejected',
                source='librarian',
                details=request.reason or "Metadata rejected"
            )
            
            db.commit()
            db.refresh(pending_entry)
            
            logger.info(f"Successfully rejected metadata for pending_id={pending_id}")
            
            return ConfirmationResponse(
                message="Metadata rejected",
                pending_id=pending_id,
                status=pending_entry.status,
                output_json=None
            )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error confirming metadata for pending_id={pending_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm metadata: {str(e)}"
        )


@router.get("/audit/{pending_id}", response_model=AuditLogsResponse)
async def get_audit_logs(pending_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all audit log entries for a specific pending catalogue entry.
    
    Returns audit logs ordered by timestamp (oldest first) to show the
    complete history of actions taken on the book entry.
    
    Args:
        pending_id: ID of pending catalogue entry
        db: Database session (injected)
        
    Returns:
        List of audit log entries with metadata
        
    Raises:
        HTTPException 404: If pending entry not found
        HTTPException 500: If database query fails
    """
    try:
        logger.info(f"Fetching audit logs for pending_id={pending_id}")
        
        # Verify pending entry exists
        pending_entry = db.query(PendingCatalogue).filter(
            PendingCatalogue.id == pending_id
        ).first()
        
        if not pending_entry:
            logger.warning(f"Pending catalogue entry not found: id={pending_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pending catalogue entry with id {pending_id} not found"
            )
        
        # Fetch audit logs
        audit_logs = db.query(CatalogueAudit).filter(
            CatalogueAudit.pending_id == pending_id
        ).order_by(CatalogueAudit.timestamp.asc()).all()
        
        logger.info(f"Found {len(audit_logs)} audit log entries for pending_id={pending_id}")
        
        return AuditLogsResponse(
            message="Audit logs retrieved successfully",
            pending_id=pending_id,
            total_entries=len(audit_logs),
            audit_logs=audit_logs
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error fetching audit logs for pending_id={pending_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch audit logs: {str(e)}"
        )
