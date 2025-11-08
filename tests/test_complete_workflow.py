"""
End-to-End Workflow Test Script
Tests the complete book cataloguing workflow from addition to insertion.

Usage:
    python test_complete_workflow.py

Requirements:
    - Server running on http://localhost:8000
    - Database initialized with migrations applied
"""

import requests
import json
import time
import pytest
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

# ANSI color codes for pretty output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_step(step_num: int, description: str):
    """Print a step header."""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}STEP {step_num}: {description}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")


def print_success(message: str):
    """Print success message."""
    print(f"{GREEN}✓ {message}{RESET}")


def print_error(message: str):
    """Print error message."""
    print(f"{RED}✗ {message}{RESET}")


def print_info(message: str):
    """Print info message."""
    print(f"{YELLOW}ℹ {message}{RESET}")


def print_json(data: Dict[Any, Any], title: str = "Response"):
    """Pretty print JSON data."""
    print(f"\n{title}:")
    print(json.dumps(data, indent=2))


def check_health() -> bool:
    """Check if server is running and APIs are reachable."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        health_data = response.json()
        
        if response.status_code == 200:
            print_success("Server is running")
            print_info(f"Open Library: {health_data['apis']['open_library']}")
            print_info(f"Google Books: {health_data['apis']['google_books']}")
            return True
        else:
            print_error("Server health check failed")
            return False
    except requests.exceptions.RequestException as e:
        print_error(f"Cannot connect to server: {e}")
        print_info("Make sure the server is running: python main.py")
        return False


@pytest.fixture(scope="module")
def pending_id():
    """Fixture that creates a book and returns its pending_id."""
    print_step(1, "Add Book to Pending Catalogue")
    
    book_data = {
        "isbn": "9780132350884",
        "title": "Clean Code",
        "authors": ["Robert C. Martin"],
        "total_copies": 3
    }
    
    print_info("Sending request...")
    print_json(book_data, "Request Body")
    
    response = requests.post(
        f"{BASE_URL}/catalogue/add",
        json=book_data,
        timeout=10
    )
    
    assert response.status_code == 201, f"Failed to add book: {response.status_code}"
    result = response.json()
    print_success(f"Book added successfully!")
    print_json(result)
    
    pending_id = result['pending_id']
    status = result['status']
    
    if status == 'awaiting_confirmation':
        print_success(f"Metadata extracted successfully")
        print_info(f"Pending ID: {pending_id}")
        print_info(f"Status: {status}")
        
        if result.get('metadata_preview'):
            preview = result['metadata_preview']
            print_info(f"Title: {preview.get('title')}")
            print_info(f"Publisher: {preview.get('publisher')}")
            print_info(f"Year: {preview.get('publication_year')}")
            print_info(f"Source: {preview.get('source')}")
    elif status == 'failed':
        print_error("Metadata extraction failed")
        print_info("Book can still be processed with manual metadata entry")
    
    return pending_id


def test_add_book(pending_id: int):
    """Test Step 1: Add book with metadata extraction."""
    # The fixture already created the book, just verify we have a valid ID
    assert pending_id is not None, "Failed to create pending book"
    assert isinstance(pending_id, int), "Pending ID should be an integer"
    print_success(f"Book created with pending_id: {pending_id}")


def test_get_pending(pending_id: int):
    """Test Step 2: Get pending books."""
    print_step(2, "Get Pending Books (Librarian View)")
    
    response = requests.get(f"{BASE_URL}/catalogue/pending", timeout=5)
    assert response.status_code == 200, f"Failed to get pending books: {response.status_code}"
    
    pending_books = response.json()
    print_success(f"Found {len(pending_books)} pending book(s)")
    
    # Find our book
    our_book = next((b for b in pending_books if b['id'] == pending_id), None)
    assert our_book is not None, f"Could not find book with ID {pending_id}"
    
    print_success(f"Found our book (ID: {pending_id})")
    print_info(f"Title: {our_book['title']}")
    print_info(f"Status: {our_book['status']}")
    print_info(f"Created: {our_book['created_at']}")
    
    if our_book.get('raw_metadata'):
        print_success("Raw metadata is populated")
    else:
        print_error("Raw metadata is empty")


def test_confirm_book(pending_id: int):
    """Test Step 3: Confirm/approve book metadata."""
    print_step(3, "Confirm Book Metadata (Librarian Action)")
    
    # Apply desired changes via PATCH before confirm
    patch_body = {
        "raw_metadata": {
            "publisher": "Prentice Hall",
            "publication_year": "2008"
        }
    }
    patch_resp = requests.patch(
        f"{BASE_URL}/catalogue/pending/{pending_id}",
        json=patch_body,
        timeout=5
    )
    assert patch_resp.status_code == 200, f"Failed to patch pending: {patch_resp.status_code}"

    confirmation_data = {
        "approved": True,
        "reason": "Verified and corrected metadata"
    }
    
    print_info("Approving book with edits...")
    print_json(confirmation_data, "Confirmation Request")
    
    response = requests.post(
        f"{BASE_URL}/catalogue/confirm/{pending_id}",
        json=confirmation_data,
        timeout=5
    )
    
    assert response.status_code == 200, f"Failed to confirm book: {response.status_code}"
    result = response.json()
    print_success("Book approved successfully!")
    print_json(result)
    
    assert result['status'] == 'approved', f"Unexpected status: {result['status']}"
    print_success("Status updated to 'approved'")
    
    if result.get('output_json'):
        print_success("output_json created with finalized metadata")
        output = result['output_json']
        print_info(f"Final Title: {output.get('title')}")
        print_info(f"Final Publisher: {output.get('publisher')}")
        print_info(f"Final Year: {output.get('publication_year')}")


def test_insert_book(pending_id: int):
    """Test Step 4: Insert book into main catalogue."""
    print_step(4, "Insert Book into Main Catalogue")
    
    print_info("Inserting approved book...")
    
    response = requests.post(
        f"{BASE_URL}/catalogue/insert/{pending_id}",
        timeout=10
    )
    
    assert response.status_code == 200, f"Failed to insert book: {response.status_code}"
    result = response.json()
    print_success("Book inserted successfully!")
    print_json(result)
    
    book_id = result.get('book_id')
    status = result['status']
    action = result.get('message')
    
    assert book_id is not None, "Book ID not returned"
    print_success(f"Action: {action}")
    print_info(f"Book ID: {book_id}")
    print_info(f"Pending ID: {pending_id}")
    print_info(f"Status: {status}")
    
    if status == 'completed':
        print_success("Workflow completed successfully!")


def test_audit_logs(pending_id: int):
    """Test Step 5: View audit logs."""
    print_step(5, "View Audit Trail")
    
    response = requests.get(
        f"{BASE_URL}/catalogue/audit/{pending_id}",
        timeout=5
    )
    
    assert response.status_code == 200, f"Failed to get audit logs: {response.status_code}"
    result = response.json()
    audit_logs = result['audit_logs']
    
    print_success(f"Found {result['total_entries']} audit log entries")
    print_json(result)
    
    print("\nAudit Trail Summary:")
    for log in audit_logs:
        timestamp = log['timestamp'].split('T')[1].split('.')[0]
        print(f"  {timestamp} | {log['action']:30s} | {log['source']:20s}")
    
    # Verify expected actions
    actions = [log['action'] for log in audit_logs]
    
    # Required actions (must be present)
    required_actions = [
        'input_received',
        'metadata_extracted',
        'approved',
        'pending_completed'
    ]
    
    # One of these must be present (inserted OR copies_added)
    insertion_actions = ['inserted', 'copies_added']
    
    # Check required actions
    missing_required = [a for a in required_actions if a not in actions]
    has_insertion = any(a in actions for a in insertion_actions)
    
    assert not missing_required, f"Missing required audit actions: {missing_required}"
    assert has_insertion, f"Missing insertion action (expected 'inserted' or 'copies_added')"
    
    print_success("All expected audit actions present")
    if 'inserted' in actions:
        print_info("Action: New book inserted")
    elif 'copies_added' in actions:
        print_info("Action: Copies added to existing book")


def main():
    """Run complete end-to-end workflow test."""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}SLMS End-to-End Workflow Test{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    
    # Check server health
    if not check_health():
        print_error("\nTest aborted: Server not available")
        return
    
    time.sleep(1)
    
    # Step 1: Add book
    pending_id = test_add_book()
    if not pending_id:
        print_error("\nTest failed at Step 1: Add Book")
        return
    
    time.sleep(1)
    
    # Step 2: Get pending books
    if not test_get_pending(pending_id):
        print_error("\nTest failed at Step 2: Get Pending Books")
        return
    
    time.sleep(1)
    
    # Step 3: Confirm book
    if not test_confirm_book(pending_id):
        print_error("\nTest failed at Step 3: Confirm Book")
        return
    
    time.sleep(1)
    
    # Step 4: Insert book
    book_id = test_insert_book(pending_id)
    if not book_id:
        print_error("\nTest failed at Step 4: Insert Book")
        return
    
    time.sleep(1)
    
    # Step 5: View audit logs
    if not test_audit_logs(pending_id):
        print_error("\nTest failed at Step 5: Audit Logs")
        return
    
    # Final summary
    print(f"\n{GREEN}{'='*70}{RESET}")
    print(f"{GREEN}✓ ALL TESTS PASSED!{RESET}")
    print(f"{GREEN}{'='*70}{RESET}")
    print(f"\n{GREEN}Complete workflow executed successfully:{RESET}")
    print(f"  • Pending ID: {pending_id}")
    print(f"  • Book ID: {book_id}")
    print(f"  • Status: completed")
    print(f"\n{YELLOW}Next Steps:{RESET}")
    print(f"  • View in Swagger UI: http://localhost:8000/docs")
    print(f"  • Check database: SELECT * FROM lms_core.books WHERE book_id = {book_id};")
    print(f"  • View audit logs: GET /catalogue/audit/{pending_id}")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Test interrupted by user{RESET}")
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        import traceback
        traceback.print_exc()
