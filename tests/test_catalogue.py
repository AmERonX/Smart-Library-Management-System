"""
Test script for Smart Cataloguing Pipeline
Tests validation, API fetching, and metadata merging without starting the server.
"""

import sys
import os


sys.path.insert(0,os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))


from main import (
    BookInput,
    fetch_openlibrary_metadata,
    fetch_googlebooks_metadata,
    merge_metadata,
    extract_year,
    extract_description
)

def test_validation():
    """Test input validation."""
    print("\n=== Testing Input Validation ===")
    
    # Test 1: Valid ISBN (13 digits)
    try:
        book = BookInput(isbn="9780132350884", total_copies=2)
        print("✓ Valid 13-digit ISBN accepted")
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Test 2: Valid ISBN (10 digits)
    try:
        book = BookInput(isbn="0132350882", total_copies=1)
        print("✓ Valid 10-digit ISBN accepted")
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Test 3: Invalid ISBN
    try:
        book = BookInput(isbn="123", total_copies=1)
        print("✗ Invalid ISBN should have been rejected")
    except ValueError as e:
        print(f"✓ Invalid ISBN correctly rejected: {e}")
    
    # Test 4: Title without ISBN
    try:
        book = BookInput(title="Clean Code", authors=["Robert C. Martin"], total_copies=1)
        print("✓ Title without ISBN accepted")
    except Exception as e:
        print(f"✗ Failed: {e}")
    
    # Test 5: Neither ISBN nor title
    try:
        book = BookInput(total_copies=1)
        print("✗ Should require ISBN or title")
    except ValueError as e:
        print(f"✓ Missing ISBN and title correctly rejected")
    
    # Test 6: Invalid total_copies
    try:
        book = BookInput(isbn="9780132350884", total_copies=0)
        print("✗ Should reject total_copies < 1")
    except Exception as e:
        print(f"✓ Invalid total_copies correctly rejected")


def test_helper_functions():
    """Test helper functions."""
    print("\n=== Testing Helper Functions ===")
    
    # Test extract_year
    assert extract_year("2008-08-01") == "2008", "Failed to extract year from date"
    assert extract_year("August 2008") == "2008", "Failed to extract year from text"
    assert extract_year("") is None, "Should return None for empty string"
    print("✓ extract_year() working correctly")
    
    # Test extract_description
    assert extract_description("  Multiple   spaces  ") == "Multiple spaces", "Failed to clean description"
    assert extract_description("") is None, "Should return None for empty string"
    assert extract_description(None) is None, "Should return None for None input"
    print("✓ extract_description() working correctly")


def test_api_fetching():
    """Test API fetching functions."""
    print("\n=== Testing API Fetching ===")
    
    # Test Open Library
    print("\nTesting Open Library API...")
    isbn = "9780132350884"  # Clean Code
    metadata = fetch_openlibrary_metadata(isbn)
    if metadata:
        print(f"✓ Open Library returned data for ISBN {isbn}")
        print(f"  Title: {metadata.get('title')}")
        print(f"  Authors: {metadata.get('authors')}")
        print(f"  Source: {metadata.get('source')}")
    else:
        print(f"⚠ Open Library returned no data for ISBN {isbn}")
    
    # Test Google Books
    print("\nTesting Google Books API...")
    metadata = fetch_googlebooks_metadata(isbn=isbn)
    if metadata:
        print(f"✓ Google Books returned data for ISBN {isbn}")
        print(f"  Title: {metadata.get('title')}")
        print(f"  Authors: {metadata.get('authors')}")
        print(f"  Publisher: {metadata.get('publisher')}")
        print(f"  Year: {metadata.get('publication_year')}")
        print(f"  Source: {metadata.get('source')}")
    else:
        print(f"✗ Google Books returned no data for ISBN {isbn}")
    
    # Test Google Books with title search
    print("\nTesting Google Books API with title search...")
    metadata = fetch_googlebooks_metadata(title="Clean Code", authors=["Robert C. Martin"])
    if metadata:
        print(f"✓ Google Books returned data for title search")
        print(f"  Title: {metadata.get('title')}")
        print(f"  Authors: {metadata.get('authors')}")
    else:
        print(f"✗ Google Books returned no data for title search")


def test_metadata_merging():
    """Test metadata merging logic with enhanced fields."""
    print("\n=== Testing Metadata Merging ===")
    
    # Create mock metadata with new fields
    primary = {
        'isbn_10': '0132350882',
        'isbn_13': '9780132350884',
        'title': 'Clean Code',
        'authors': ['Robert C. Martin'],
        'publisher': 'Prentice Hall',
        'publication_year': '2008',
        'edition': None,
        'language': 'en',
        'description': 'A handbook of agile software craftsmanship.',
        'table_of_contents': ['Chapter 1: Clean Code', 'Chapter 2: Meaningful Names'],
        'subjects': ['Software Engineering', 'Programming'],
        'categories': ['Programming'],
        'cover_url': 'http://example.com/cover1.jpg',
        'source': 'open_library'
    }
    
    fallback = {
        'isbn_10': '0132350882',
        'isbn_13': '9780132350884',
        'title': 'Clean Code',
        'authors': ['Robert C. Martin'],
        'publisher': 'Prentice Hall',
        'publication_year': '2008',
        'edition': '1st',
        'language': 'en',
        'description': 'A handbook of agile software craftsmanship.',
        'categories': ['Computers', 'Software Engineering'],
        'page_count': 464,
        'preview_link': 'http://books.google.com/preview',
        'cover_url': 'http://example.com/cover2.jpg',
        'source': 'google_books'
    }
    
    book_input = BookInput(isbn="9780132350884", total_copies=2)
    
    # Test merging with both sources
    merged = merge_metadata(primary, fallback, book_input)
    assert merged is not None, "Merge should not return None"
    assert merged['title'] == 'Clean Code', "Title should be preserved"
    assert merged['edition'] == '1st', "Edition should be filled from fallback"
    assert merged['total_copies'] == 2, "Total copies should be from input"
    assert merged['keywords'] is None, "Keywords should be None"
    assert merged['embeddings'] is None, "Embeddings should be None"
    assert merged['embedding_text'] is not None, "Embedding text should be generated"
    assert 'Clean Code' in merged['embedding_text'], "Embedding text should contain title"
    assert merged['page_count'] == 464, "Page count should be from Google Books"
    assert merged['table_of_contents'] is not None, "Table of contents should be from Open Library"
    print("✓ Metadata merging with both sources works correctly")
    print(f"  Embedding text length: {len(merged['embedding_text'])} chars")
    
    # Test with only fallback
    merged = merge_metadata(None, fallback, book_input)
    assert merged is not None, "Should use fallback when primary is None"
    assert merged['source_priority'] == 'google_books', "Source priority should be from fallback"
    print("✓ Metadata merging with only fallback works correctly")
    
    # Test with both None
    merged = merge_metadata(None, None, book_input)
    assert merged is None, "Should return None when both sources fail"
    print("✓ Metadata merging correctly handles both sources failing")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Smart Cataloguing Pipeline - Test Suite")
    print("=" * 60)
    
    try:
        test_validation()
        test_helper_functions()
        test_api_fetching()
        test_metadata_merging()
        
        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
