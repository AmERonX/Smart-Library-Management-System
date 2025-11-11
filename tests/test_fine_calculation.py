"""
Test script to verify fine calculation trigger works correctly.
Creates a borrow record with a past due_date, then returns it to trigger fine calculation.
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timedelta
from dotenv import load_dotenv
from database import SessionLocal, engine
from models import User, Book, BorrowRecord, Fine
from sqlalchemy import text

load_dotenv()

def test_fine_calculation():
    """Test fine calculation by creating an overdue borrow and returning it."""
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("Testing Fine Calculation Trigger")
        print("=" * 60)
        
        # Step 1: Get or create a test user
        print("\n1. Getting test user...")
        user = db.query(User).filter(User.role == 'student').first()
        if not user:
            print("   ERROR: No student user found. Please create a user first.")
            return
        print(f"   ✓ Using user: {user.username} (ID: {user.user_id})")
        
        # Step 2: Get a book with available copies
        print("\n2. Getting a book with available copies...")
        book = db.query(Book).filter(Book.available_copies > 0).first()
        if not book:
            print("   ERROR: No books with available copies found.")
            return
        print(f"   ✓ Using book: {book.title} (ID: {book.book_id}, Available: {book.available_copies})")
        
        # Step 3: Create a borrow record with past due_date (3 days ago)
        print("\n3. Creating borrow record with overdue due_date...")
        now = datetime.utcnow()
        borrow_date = now - timedelta(days=5)  # Borrowed 5 days ago
        due_date = now - timedelta(days=3)     # Due 3 days ago (overdue!)
        
        # Check if book has available copies
        if book.available_copies <= 0:
            print("   ERROR: Book has no available copies. Please check another book.")
            return
        
        # Create borrow record directly in DB (bypassing API validation)
        borrow = BorrowRecord(
            user_id=user.user_id,
            book_id=book.book_id,
            borrow_date=borrow_date,
            due_date=due_date,
            return_date=None  # Not returned yet
        )
        db.add(borrow)
        
        # Decrease available copies
        book.available_copies -= 1
        db.commit()
        db.refresh(borrow)
        
        print(f"   ✓ Created borrow record (ID: {borrow.borrow_id})")
        print(f"     Borrow date: {borrow_date}")
        print(f"     Due date: {due_date} (OVERDUE by {(now - due_date).days} days)")
        
        # Step 4: Check that no fine exists yet
        print("\n4. Checking for existing fines...")
        existing_fine = db.query(Fine).filter(Fine.borrow_id == borrow.borrow_id).first()
        if existing_fine:
            print(f"   ⚠ WARNING: Fine already exists for this borrow (ID: {existing_fine.fine_id})")
            print(f"     Amount: ${existing_fine.amount}")
        else:
            print("   ✓ No fine exists yet (expected)")
        
        # Step 5: Return the book (this should trigger the fine)
        print("\n5. Returning the book (should trigger fine calculation)...")
        return_date = now
        borrow.return_date = return_date
        book.available_copies += 1
        db.commit()
        db.refresh(borrow)
        
        print(f"   ✓ Book returned at: {return_date}")
        
        # Step 6: Check if fine was created
        print("\n6. Checking if fine was created...")
        fine = db.query(Fine).filter(Fine.borrow_id == borrow.borrow_id).first()
        
        if fine:
            days_overdue = (return_date.date() - due_date.date()).days
            expected_amount = max(1, days_overdue) * 1.00
            
            print(f"   ✓ Fine created successfully!")
            print(f"     Fine ID: {fine.fine_id}")
            print(f"     Amount: ${fine.amount}")
            print(f"     Status: {fine.status}")
            print(f"     Issue date: {fine.issue_date}")
            print(f"\n   Calculation check:")
            print(f"     Days overdue: {days_overdue} days")
            print(f"     Expected amount: ${expected_amount}")
            print(f"     Actual amount: ${fine.amount}")
            
            if float(fine.amount) == expected_amount:
                print(f"     ✓ Amount matches expected value!")
            else:
                print(f"     ⚠ WARNING: Amount doesn't match expected value!")
        else:
            print("   ✗ ERROR: No fine was created! Trigger may not be working.")
            print("     Check:")
            print("     1. Is the trigger installed? (Run migration 008)")
            print("     2. Check database logs for trigger errors")
        
        # Step 7: Test duplicate prevention
        print("\n7. Testing duplicate fine prevention...")
        # Try to update return_date again (should not create duplicate)
        borrow.return_date = return_date + timedelta(seconds=1)
        db.commit()
        
        fine_count = db.query(Fine).filter(Fine.borrow_id == borrow.borrow_id).count()
        if fine_count == 1:
            print(f"   ✓ Duplicate prevention works! (Only {fine_count} fine exists)")
        else:
            print(f"   ⚠ WARNING: {fine_count} fines found (should be 1)")
        
        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)
        
    except Exception as e:
        db.rollback()
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_fine_calculation()