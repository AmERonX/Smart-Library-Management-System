"""
User routes for borrowing, reservations, fines, and user account management.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from database import get_db
from models import User, Book, BorrowRecord, Reservation, Fine, BookMetadata
from schemas import (
    BorrowRequest, BorrowResponse, BorrowRecordResponse, BorrowListResponse,
    ReturnRequest, ReturnResponse, RenewRequest, RenewResponse,
    ReservationRequest, ReservationResponse, ReservationListResponse,
    FineResponse, FineListResponse, PayFineRequest, PayFineResponse,
    UserResponse, UserSummaryResponse
)
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

# Borrowing period (default 14 days)
BORROW_PERIOD_DAYS = 14
RENEW_PERIOD_DAYS = 14


# ============================================================================
# USER ACCOUNT
# ============================================================================

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return UserResponse(
        user_id=current_user.user_id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at
    )


@router.get("/me/summary", response_model=UserSummaryResponse)
async def get_user_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user dashboard summary"""
    try:
        # Count active borrows
        active_borrows = db.query(BorrowRecord).filter(
            BorrowRecord.user_id == current_user.user_id,
            BorrowRecord.return_date.is_(None)
        ).count()
        
        # Count overdue books
        now = datetime.utcnow()
        overdue_books = db.query(BorrowRecord).filter(
            BorrowRecord.user_id == current_user.user_id,
            BorrowRecord.return_date.is_(None),
            BorrowRecord.due_date < now
        ).count()
        
        # Count active reservations
        active_reservations = db.query(Reservation).filter(
            Reservation.user_id == current_user.user_id,
            Reservation.status == 'active'
        ).count()
        
        # Count pending fines and total amount
        pending_fines_query = db.query(
            func.count(Fine.fine_id),
            func.coalesce(func.sum(Fine.amount), Decimal('0'))
        ).filter(
            Fine.user_id == current_user.user_id,
            Fine.status == 'pending'
        ).first()
        
        pending_fines = pending_fines_query[0] or 0
        total_fine_amount = pending_fines_query[1] or Decimal('0')
        
        return UserSummaryResponse(
            user_id=current_user.user_id,
            username=current_user.username,
            active_borrows=active_borrows,
            active_reservations=active_reservations,
            pending_fines=pending_fines,
            total_fine_amount=total_fine_amount,
            overdue_books=overdue_books
        )
        
    except Exception as e:
        logger.error(f"Error getting user summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user summary"
        )


# ============================================================================
# BORROWING
# ============================================================================

@router.post("/borrows", response_model=BorrowResponse)
async def borrow_book(
    request: BorrowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Borrow a book (uses stored function for concurrency safety)"""
    try:
        # Check if book exists
        book = db.query(Book).filter(Book.book_id == request.book_id).first()
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )
        
        # Calculate due date
        if request.due_date:
            due_date = request.due_date
        else:
            due_date = datetime.utcnow() + timedelta(days=BORROW_PERIOD_DAYS)
        
        # Use stored function for borrowing (handles concurrency and reservations)
        try:
            result = db.execute(
                text("SELECT borrow_book(:user_id, :book_id, :due_date)"),
                {"user_id": current_user.user_id, "book_id": request.book_id, "due_date": due_date}
            ).scalar()
            
            db.commit()
            
            if result:  # True = book borrowed successfully
                # Get the borrow record
                borrow = db.query(BorrowRecord).filter(
                    BorrowRecord.user_id == current_user.user_id,
                    BorrowRecord.book_id == request.book_id,
                    BorrowRecord.return_date.is_(None)
                ).order_by(BorrowRecord.borrow_date.desc()).first()
                
                return BorrowResponse(
                    success=True,
                    borrow_id=borrow.borrow_id if borrow else None,
                    reserved=False,
                    message="Book borrowed successfully"
                )
            else:  # False = book reserved instead
                return BorrowResponse(
                    success=False,
                    reserved=True,
                    message="Book not available. Reservation created."
                )
                
        except Exception as e:
            db.rollback()
            logger.error(f"Error in borrow_book function: {str(e)}")
            # Fallback: Manual borrowing logic
            if book.available_copies > 0:
                # Create borrow record
                borrow = BorrowRecord(
                    user_id=current_user.user_id,
                    book_id=request.book_id,
                    due_date=due_date
                )
                db.add(borrow)
                
                # Update book available copies
                book.available_copies -= 1
                db.commit()
                db.refresh(borrow)
                
                return BorrowResponse(
                    success=True,
                    borrow_id=borrow.borrow_id,
                    reserved=False,
                    message="Book borrowed successfully"
                )
            else:
                # Create reservation
                reservation = Reservation(
                    user_id=current_user.user_id,
                    book_id=request.book_id,
                    status='active'
                )
                db.add(reservation)
                db.commit()
                db.refresh(reservation)
                
                return BorrowResponse(
                    success=False,
                    reserved=True,
                    message="Book not available. Reservation created."
                )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error borrowing book: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to borrow book"
        )


@router.get("/borrows/active", response_model=BorrowListResponse)
async def get_active_borrows(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active borrows for current user"""
    try:
        now = datetime.utcnow()
        borrows = db.query(BorrowRecord).filter(
            BorrowRecord.user_id == current_user.user_id,
            BorrowRecord.return_date.is_(None)
        ).all()
        
        items = []
        for borrow in borrows:
            book = db.query(Book).filter(Book.book_id == borrow.book_id).first()
            items.append(BorrowRecordResponse(
                borrow_id=borrow.borrow_id,
                book_id=borrow.book_id,
                book_title=book.title if book else "Unknown",
                borrow_date=borrow.borrow_date,
                due_date=borrow.due_date,
                return_date=borrow.return_date,
                is_overdue=borrow.due_date < now
            ))
        
        return BorrowListResponse(total=len(items), items=items)
        
    except Exception as e:
        logger.error(f"Error getting active borrows: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active borrows"
        )


@router.get("/borrows/history", response_model=BorrowListResponse)
async def get_borrow_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get borrowing history for current user"""
    try:
        borrows = db.query(BorrowRecord).filter(
            BorrowRecord.user_id == current_user.user_id
        ).order_by(BorrowRecord.borrow_date.desc()).all()
        
        items = []
        for borrow in borrows:
            book = db.query(Book).filter(Book.book_id == borrow.book_id).first()
            items.append(BorrowRecordResponse(
                borrow_id=borrow.borrow_id,
                book_id=borrow.book_id,
                book_title=book.title if book else "Unknown",
                borrow_date=borrow.borrow_date,
                due_date=borrow.due_date,
                return_date=borrow.return_date,
                is_overdue=False  # Historical records don't show as overdue
            ))
        
        return BorrowListResponse(total=len(items), items=items)
        
    except Exception as e:
        logger.error(f"Error getting borrow history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get borrow history"
        )


@router.post("/borrows/{borrow_id}/return", response_model=ReturnResponse)
async def return_book(
    borrow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return a borrowed book"""
    try:
        # Get borrow record
        borrow = db.query(BorrowRecord).filter(
            BorrowRecord.borrow_id == borrow_id,
            BorrowRecord.user_id == current_user.user_id
        ).first()
        
        if not borrow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Borrow record not found"
            )
        
        if borrow.return_date is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book already returned"
            )
        
        # Update borrow record
        borrow.return_date = datetime.utcnow()
        
        # Update book available copies
        book = db.query(Book).filter(Book.book_id == borrow.book_id).first()
        if book:
            book.available_copies += 1
        
        # Check if fine was created (trigger should create it automatically)
        fine = db.query(Fine).filter(Fine.borrow_id == borrow_id).first()
        fine_created = fine is not None
        fine_amount = fine.amount if fine else None
        
        db.commit()
        
        return ReturnResponse(
            success=True,
            fine_created=fine_created,
            fine_amount=fine_amount,
            message="Book returned successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error returning book: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to return book"
        )


@router.post("/borrows/{borrow_id}/renew", response_model=RenewResponse)
async def renew_book(
    borrow_id: int,
    request: RenewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Renew a borrowed book"""
    try:
        # Get borrow record
        borrow = db.query(BorrowRecord).filter(
            BorrowRecord.borrow_id == borrow_id,
            BorrowRecord.user_id == current_user.user_id
        ).first()
        
        if not borrow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Borrow record not found"
            )
        
        if borrow.return_date is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot renew returned book"
            )
        
        # Calculate new due date
        if request.new_due_date:
            new_due_date = request.new_due_date
        else:
            new_due_date = datetime.utcnow() + timedelta(days=RENEW_PERIOD_DAYS)
        
        # Update due date
        borrow.due_date = new_due_date
        db.commit()
        db.refresh(borrow)
        
        return RenewResponse(
            success=True,
            borrow_id=borrow.borrow_id,
            new_due_date=borrow.due_date,
            message="Book renewed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error renewing book: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to renew book"
        )


# ============================================================================
# RESERVATIONS
# ============================================================================

@router.post("/reservations", response_model=ReservationResponse)
async def create_reservation(
    request: ReservationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a reservation for a book"""
    try:
        # Check if book exists
        book = db.query(Book).filter(Book.book_id == request.book_id).first()
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Book not found"
            )
        
        # Check if user already has an active reservation for this book
        existing = db.query(Reservation).filter(
            Reservation.user_id == current_user.user_id,
            Reservation.book_id == request.book_id,
            Reservation.status == 'active'
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active reservation for this book"
            )
        
        # Create reservation
        reservation = Reservation(
            user_id=current_user.user_id,
            book_id=request.book_id,
            status='active'
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        
        return ReservationResponse(
            reservation_id=reservation.reservation_id,
            book_id=reservation.book_id,
            book_title=book.title,
            reservation_date=reservation.reservation_date,
            expiry_date=reservation.expiry_date,
            status=reservation.status
        )
        
    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active reservation for this book"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create reservation"
        )


@router.get("/reservations/active", response_model=ReservationListResponse)
async def get_active_reservations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active reservations for current user"""
    try:
        reservations = db.query(Reservation).filter(
            Reservation.user_id == current_user.user_id,
            Reservation.status == 'active'
        ).all()
        
        items = []
        for reservation in reservations:
            book = db.query(Book).filter(Book.book_id == reservation.book_id).first()
            items.append(ReservationResponse(
                reservation_id=reservation.reservation_id,
                book_id=reservation.book_id,
                book_title=book.title if book else "Unknown",
                reservation_date=reservation.reservation_date,
                expiry_date=reservation.expiry_date,
                status=reservation.status
            ))
        
        return ReservationListResponse(total=len(items), items=items)
        
    except Exception as e:
        logger.error(f"Error getting active reservations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get active reservations"
        )


@router.delete("/reservations/{reservation_id}")
async def cancel_reservation(
    reservation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a reservation"""
    try:
        reservation = db.query(Reservation).filter(
            Reservation.reservation_id == reservation_id,
            Reservation.user_id == current_user.user_id
        ).first()
        
        if not reservation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found"
            )
        
        if reservation.status != 'active':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel non-active reservation"
            )
        
        reservation.status = 'cancelled'
        db.commit()
        
        return {"success": True, "message": "Reservation cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error cancelling reservation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel reservation"
        )


# ============================================================================
# FINES
# ============================================================================

@router.get("/fines", response_model=FineListResponse)
async def get_fines(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get fines for current user"""
    try:
        fines = db.query(Fine).filter(
            Fine.user_id == current_user.user_id
        ).order_by(Fine.issue_date.desc()).all()
        
        items = []
        total_amount = Decimal('0')
        for fine in fines:
            borrow = db.query(BorrowRecord).filter(BorrowRecord.borrow_id == fine.borrow_id).first()
            book = db.query(Book).filter(Book.book_id == borrow.book_id).first() if borrow else None
            
            items.append(FineResponse(
                fine_id=fine.fine_id,
                borrow_id=fine.borrow_id,
                book_title=book.title if book else "Unknown",
                amount=fine.amount,
                issue_date=fine.issue_date,
                paid_date=fine.paid_date,
                status=fine.status
            ))
            
            if fine.status == 'pending':
                total_amount += fine.amount
        
        return FineListResponse(
            total=len(items),
            total_amount=total_amount,
            items=items
        )
        
    except Exception as e:
        logger.error(f"Error getting fines: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get fines"
        )


@router.post("/fines/{fine_id}/pay", response_model=PayFineResponse)
async def pay_fine(
    fine_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a fine as paid"""
    try:
        fine = db.query(Fine).filter(
            Fine.fine_id == fine_id,
            Fine.user_id == current_user.user_id
        ).first()
        
        if not fine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fine not found"
            )
        
        if fine.status == 'paid':
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fine already paid"
            )
        
        fine.status = 'paid'
        fine.paid_date = datetime.utcnow()
        db.commit()
        
        return PayFineResponse(
            success=True,
            fine_id=fine.fine_id,
            message="Fine paid successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error paying fine: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pay fine"
        )

