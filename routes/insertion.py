"""
Book Insertion Routes - Phase 1
FastAPI endpoints for inserting approved books into the main catalogue.

This module provides HTTP endpoints that wrap the core insertion service logic.
It handles request validation, error responses, and transaction management.

Endpoints:
- POST /catalogue/insert/{pending_id}: Insert approved pending book into catalogue
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database import get_db
from schemas import InsertionResponse, ErrorResponse
from services.insertion import insert_pending_book
from services.embeddings import enhance_and_store

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/catalogue",
    tags=["Book Insertion"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request - invalid state or missing data"},
        404: {"model": ErrorResponse, "description": "Pending entry not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)


@router.post(
    "/insert/{pending_id}",
    response_model=InsertionResponse,
    status_code=status.HTTP_200_OK,
    summary="Insert approved book into catalogue",
    description="""
    Insert an approved pending_catalogue entry into the main books catalogue.
    
    **Workflow:**
    1. Validates that pending entry exists and has status='approved'
    2. Extracts metadata from output_json (librarian-confirmed data)
    3. Upserts publisher and authors to avoid duplicates
    4. Checks if book exists by ISBN (ISBN-13 preferred, then ISBN-10)
    5. If book exists: adds copies to existing book
    6. If book is new: creates new book record with all metadata
    7. Logs comprehensive audit trail
    8. Marks pending entry as 'completed'
    
    **Idempotency:**
    - Safe to call multiple times for the same pending_id
    - If already completed, returns success without re-processing
    - Uses database locks (SELECT FOR UPDATE) to prevent race conditions
    
    **ISBN Handling:**
    - Supports both ISBN-10 and ISBN-13
    - Normalizes ISBNs (removes hyphens/spaces)
    - Uses ISBN-13 as canonical identifier
    - Different ISBNs = different editions (separate book records)
    
    **Error Cases:**
    - 400: Pending entry not in 'approved' state
    - 400: Required metadata missing (e.g., no title)
    - 404: Pending entry not found
    - 500: Database errors or unexpected failures
    
    **Example Responses:**
    
    *New book inserted:*
    ```json
    {
        "message": "Book inserted successfully",
        "pending_id": 123,
        "book_id": 456,
        "status": "completed"
    }
    ```
    
    *Existing book updated:*
    ```json
    {
        "message": "Existing book updated with additional copies",
        "pending_id": 123,
        "book_id": 789,
        "status": "completed"
    }
    ```
    
    *Already completed (idempotent):*
    ```json
    {
        "message": "Pending record already completed",
        "pending_id": 123,
        "book_id": 789,
        "status": "completed"
    }
    ```
    """,
    responses={
        200: {
            "description": "Book inserted or updated successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "new_book": {
                            "summary": "New book inserted",
                            "value": {
                                "message": "Book inserted successfully",
                                "pending_id": 123,
                                "book_id": 456,
                                "status": "completed"
                            }
                        },
                        "existing_book": {
                            "summary": "Copies added to existing book",
                            "value": {
                                "message": "Existing book updated with additional copies",
                                "pending_id": 123,
                                "book_id": 789,
                                "status": "completed"
                            }
                        },
                        "already_completed": {
                            "summary": "Already completed (idempotent)",
                            "value": {
                                "message": "Pending record already completed",
                                "pending_id": 123,
                                "book_id": 789,
                                "status": "completed"
                            }
                        }
                    }
                }
            }
        }
    }
)
async def insert_approved_book(
    pending_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Insert an approved pending book into the main catalogue.
    
    This endpoint is a thin wrapper around the core insertion service.
    It handles HTTP concerns (validation, error responses) while delegating
    business logic to services/insertion.py for testability.
    
    Args:
        pending_id: ID of pending_catalogue entry to insert
        db: Database session (injected by FastAPI)
        
    Returns:
        InsertionResponse with result details
        
    Raises:
        HTTPException: On validation errors, not found, or database errors
    """
    logger.info(f"Received insertion request for pending_id: {pending_id}")
    
    try:
        # Call core insertion service
        result = insert_pending_book(db, pending_id)
        # Auto-trigger enhancement only when a brand-new book was inserted
        if result.get('action') == 'inserted' and result.get('book_id'):
            book_id = int(result['book_id'])
            logger.info(f"Scheduling enhancement for book_id={book_id}")
            # Pass current engine so background task uses the same DB (important in tests)
            background_tasks.add_task(enhance_and_store, book_id, db.bind)
        
        # Return success response
        return InsertionResponse(
            message=result['message'],
            pending_id=result['pending_id'],
            book_id=result.get('book_id'),
            status=result['status']
        )
    
    except ValueError as e:
        # Validation errors (bad state, missing data)
        error_msg = str(e)
        logger.warning(f"Validation error for pending_id {pending_id}: {error_msg}")
        
        # Determine appropriate status code
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
    
    except SQLAlchemyError as e:
        # Database errors
        error_msg = f"Database error during insertion: {str(e)}"
        logger.error(f"Database error for pending_id {pending_id}: {str(e)}", exc_info=True)
        # Include actual error in response for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    
    except Exception as e:
        # Unexpected errors
        error_msg = f"Unexpected error during insertion: {str(e)}"
        logger.error(f"Unexpected error for pending_id {pending_id}: {str(e)}", exc_info=True)
        # Include actual error in response for debugging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )
