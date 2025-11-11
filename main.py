"""
Smart Cataloguing Pipeline - Step 1: Synchronous MVP
FastAPI service for fetching book metadata from Open Library and Google Books APIs, with
LLM workflow enhancement planned for future.
"""

import logging
import re
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel, Field, field_validator, model_validator
import requests
from requests.exceptions import RequestException, Timeout

# Import configuration
from config import (
    OPENLIBRARY_API_URL,
    GOOGLEBOOKS_API_URL,
    REQUEST_TIMEOUT,
    ISBN_PATTERN,
    LOG_LEVEL,
    LOG_FORMAT,
    ENABLE_OPENLIBRARY,
    ENABLE_GOOGLEBOOKS,
    get_googlebooks_url
)

# Import database and routes for librarian confirmation feature
from database import init_db
from routes import catalogue, insertion
from routes import search
from routes import books
from routes import auth, users

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan: initialize DB tables on startup."""
    logger.info("Initializing database tables...")
    try:
        init_db()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        # Don't fail startup - allow app to run even if DB is not available
    yield

# Initialize FastAPI app
app = FastAPI(
    title="Smart Library Management System (SLMS)",
    description="Book metadata fetching service with librarian confirmation workflow",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (restrict in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(catalogue.router)
app.include_router(insertion.router)  # Phase-1: Book Insertion Service
app.include_router(search.router)  # Semantic Search
app.include_router(books.router)  # Books list & detail
app.include_router(auth.router)  # Authentication (register, login)
app.include_router(users.router)  # User endpoints (borrowing, reservations, fines)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class BookInput(BaseModel):
    """
    Input model for book cataloguing request.
    Validates ISBN format and ensures required fields are present.
    """
    isbn: Optional[str] = Field(None, description="10 or 13 digit ISBN")
    title: Optional[str] = Field(None, description="Book title")
    authors: Optional[List[str]] = Field(default=None, description="List of author names")
    total_copies: int = Field(default=1, ge=1, description="Number of copies to add")

    @field_validator('isbn')
    @classmethod
    def validate_isbn(cls, v):
        """Validate ISBN format: must be 10 or 13 digits (allows X as ISBN-10 check digit)."""
        if v is not None:
            # Normalize: remove hyphens/spaces and uppercase for X check digit
            cleaned = v.replace('-', '').replace(' ', '').upper()
            if not re.match(ISBN_PATTERN, cleaned):
                raise ValueError('ISBN must be exactly 10 or 13 digits (ISBN-10 may end with X)')
            return cleaned
        return v

    @model_validator(mode='after')
    def validate_title_or_isbn(self):
        """Ensure either ISBN or title is provided."""
        if self.title is None and self.isbn is None:
            raise ValueError('Either ISBN or title must be provided')
        return self


class BookMetadata(BaseModel):
    """
    Output model for book metadata response.
    Contains all fields fetched from external APIs.
    """
    isbn: Optional[str]
    isbn_10: Optional[str] = None
    isbn_13: Optional[str] = None
    title: str
    authors: List[str]
    publisher: Optional[str]
    publication_year: Optional[str]
    edition: Optional[str]
    language: Optional[str] = None
    description: Optional[str]
    table_of_contents: Optional[List[str]] = None
    subjects: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    page_count: Optional[int] = None
    cover_url: Optional[str]
    preview_link: Optional[str] = None
    total_copies: int
    keywords: Optional[List[str]] = None
    embeddings: Optional[str] = None
    embedding_text: Optional[str] = None
    source: str
    source_priority: Optional[str] = None


# ============================================================================
# API FETCHING FUNCTIONS
# ============================================================================

def fetch_openlibrary_metadata(isbn: str) -> Optional[dict]:
    """
    Fetch book metadata from Open Library API with enhanced work details.
    Fetches both edition and work-level metadata for richer content.
    
    Args:
        isbn: Book ISBN (10 or 13 digits)
        
    Returns:
        Dictionary containing book metadata or None if fetch fails
    """
    try:
        logger.info(f"Fetching metadata from Open Library for ISBN: {isbn}")
        
        params = {
            'bibkeys': f'ISBN:{isbn}',
            'format': 'json',
            'jscmd': 'data'
        }
        
        response = requests.get(
            OPENLIBRARY_API_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        book_key = f'ISBN:{isbn}'
        
        if book_key not in data or not data[book_key]:
            logger.warning(f"No data found in Open Library for ISBN: {isbn}")
            return None
        
        book_data = data[book_key]
        
        # Check if we have at least 3 core fields
        core_fields = ['title', 'publishers', 'publish_date']
        present_fields = sum(1 for field in core_fields if field in book_data)
        
        if present_fields < 3:
            logger.warning(f"Open Library data incomplete for ISBN: {isbn} (only {present_fields}/3 core fields)")
            return None
        
        # Fetch work details for richer metadata (table of contents, subjects, etc.)
        work_data = {}
        table_of_contents = None
        subjects = None
        description = None
        
        if 'works' in book_data and book_data['works']:
            work_key = book_data['works'][0].get('key')
            if work_key:
                try:
                    work_url = f"https://openlibrary.org{work_key}.json"
                    work_response = requests.get(work_url, timeout=REQUEST_TIMEOUT)
                    work_response.raise_for_status()
                    work_data = work_response.json()
                    
                    # Extract description from work
                    desc = work_data.get('description')
                    if isinstance(desc, dict):
                        description = desc.get('value')
                    elif isinstance(desc, str):
                        description = desc
                    
                    # Extract table of contents
                    toc = work_data.get('table_of_contents')
                    if isinstance(toc, list):
                        table_of_contents = [item.get('title') for item in toc if isinstance(item, dict) and 'title' in item]
                    
                    # Extract subjects
                    subjects = work_data.get('subjects')
                    
                    logger.debug(f"Fetched work details for ISBN: {isbn}")
                except Exception as e:
                    logger.warning(f"Could not fetch work details: {str(e)}")
        
        # Fallback description from edition data
        if not description:
            description = extract_description(book_data.get('notes') or book_data.get('subtitle'))
        
        # Extract ISBNs
        isbn_10 = book_data.get('identifiers', {}).get('isbn_10', [None])[0] if 'identifiers' in book_data else None
        isbn_13 = book_data.get('identifiers', {}).get('isbn_13', [None])[0] if 'identifiers' in book_data else None
        
        # Extract and normalize metadata
        metadata = {
            'isbn_10': isbn_10,
            'isbn_13': isbn_13,
            'title': book_data.get('title', ''),
            'authors': [author['name'] for author in book_data.get('authors', [])],
            'publisher': book_data.get('publishers', [{}])[0].get('name') if book_data.get('publishers') else None,
            'publication_year': extract_year(book_data.get('publish_date', '')),
            'edition': book_data.get('edition_name'),
            'language': 'en',  # Open Library data API typically returns English editions
            'description': description,
            'table_of_contents': table_of_contents,
            'subjects': subjects,
            'categories': [subject['name'] for subject in book_data.get('subjects', [])],
            'cover_url': book_data.get('cover', {}).get('large') or book_data.get('cover', {}).get('medium'),
            'source': 'open_library'
        }
        
        logger.info(f"Successfully fetched metadata from Open Library for ISBN: {isbn}")
        return metadata
        
    except Timeout:
        logger.error(f"Timeout while fetching from Open Library for ISBN: {isbn}")
        return None
    except RequestException as e:
        logger.error(f"Request error while fetching from Open Library: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while fetching from Open Library: {str(e)}")
        return None


def fetch_googlebooks_metadata(isbn: Optional[str] = None, title: Optional[str] = None, 
                               authors: Optional[List[str]] = None) -> Optional[dict]:
    """
    Fetch book metadata from Google Books API with language filtering.
    Prefers English editions, then selects the most recent among filtered results.
    
    Args:
        isbn: Book ISBN (10 or 13 digits)
        title: Book title (used if ISBN not available)
        authors: List of author names (used with title)
        
    Returns:
        Dictionary containing book metadata or None if fetch fails
    """
    try:
        # Build query string
        if isbn:
            query = f'isbn:{isbn}'
            logger.info(f"Fetching metadata from Google Books for ISBN: {isbn}")
        elif title:
            query = f'intitle:{title}'
            if authors and len(authors) > 0:
                query += f'+inauthor:{authors[0]}'
            logger.info(f"Fetching metadata from Google Books for title: {title}")
        else:
            logger.warning("No ISBN or title provided for Google Books search")
            return None
        
        params = {'q': query}
        
        response = requests.get(
            GOOGLEBOOKS_API_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        
        data = response.json()
        
        if 'items' not in data or len(data['items']) == 0:
            logger.warning(f"No results found in Google Books for query: {query}")
            return None
        
        items = data['items']
        
        # Filter for English editions first
        english_items = [
            item for item in items 
            if item.get('volumeInfo', {}).get('language', '').startswith('en')
        ]
        
        if english_items:
            items = english_items
            logger.debug(f"Filtered to {len(english_items)} English editions")
        else:
            logger.debug("No English editions found, using all results")
        
        # Sort by publication year (most recent first)
        def extract_year_from_item(item):
            date = item.get('volumeInfo', {}).get('publishedDate', '')
            if date and len(date) >= 4 and date[:4].isdigit():
                return int(date[:4])
            return 0
        
        items_sorted = sorted(items, key=extract_year_from_item, reverse=True)
        latest_item = items_sorted[0]
        book_data = latest_item.get('volumeInfo', {})
        
        logger.debug(f"Selected edition from year: {book_data.get('publishedDate', 'unknown')}")
        
        # Extract ISBNs
        identifiers = book_data.get('industryIdentifiers', [])
        isbn_10, isbn_13 = None, None
        for ident in identifiers:
            if ident.get('type') == 'ISBN_10':
                isbn_10 = ident.get('identifier')
            elif ident.get('type') == 'ISBN_13':
                isbn_13 = ident.get('identifier')
        
        # Extract and normalize metadata
        metadata = {
            'isbn_10': isbn_10,
            'isbn_13': isbn_13,
            'title': book_data.get('title', ''),
            'authors': book_data.get('authors', []),
            'publisher': book_data.get('publisher'),
            'publication_year': extract_year(book_data.get('publishedDate', '')),
            'edition': book_data.get('contentVersion'),
            'language': book_data.get('language'),
            'description': book_data.get('description'),
            'categories': book_data.get('categories', []),
            'page_count': book_data.get('pageCount'),
            'cover_url': book_data.get('imageLinks', {}).get('thumbnail'),
            'preview_link': book_data.get('previewLink'),
            'source': 'google_books'
        }
        
        logger.info(f"Successfully fetched metadata from Google Books")
        return metadata
        
    except Timeout:
        logger.error(f"Timeout while fetching from Google Books")
        return None
    except RequestException as e:
        logger.error(f"Request error while fetching from Google Books: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while fetching from Google Books: {str(e)}")
        return None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_year(date_string: str) -> Optional[str]:
    """
    Extract 4-digit year from a date string.
    
    Args:
        date_string: Date string in various formats
        
    Returns:
        4-digit year string or None
    """
    if not date_string:
        return None
    
    # Try to find 4 consecutive digits
    match = re.search(r'\d{4}', date_string)
    return match.group(0) if match else None


def extract_description(text: Optional[str]) -> Optional[str]:
    """
    Extract and clean description text.
    
    Args:
        text: Raw description text
        
    Returns:
        Cleaned description or None
    """
    if not text:
        return None
    
    # Basic cleaning - remove excessive whitespace
    cleaned = ' '.join(text.split())
    return cleaned if cleaned else None


def safe_join_list(lst: Optional[List], separator: str = ", ") -> str:
    """
    Safely join a list of strings with a separator.
    
    Args:
        lst: List of strings to join
        separator: Separator to use between items
        
    Returns:
        Joined string or empty string if list is None/empty
    """
    if not lst:
        return ""
    return separator.join([str(x) for x in lst if isinstance(x, str) and x.strip()])


def safe_join_lines(lst: Optional[List]) -> str:
    """
    Safely join a list of strings with newlines.
    
    Args:
        lst: List of strings to join
        
    Returns:
        Joined string or empty string if list is None/empty
    """
    if not lst:
        return ""
    return "\n".join([str(x) for x in lst if isinstance(x, str) and x.strip()])


def merge_metadata(primary: Optional[dict], fallback: Optional[dict], 
                   input_data: BookInput) -> Optional[dict]:
    """
    Merge metadata from primary and fallback sources with intelligent field prioritization.
    Creates embedding_text for AI processing by combining rich text fields.
    
    Args:
        primary: Metadata from primary source (Open Library)
        fallback: Metadata from fallback source (Google Books)
        input_data: Original input data from user
        
    Returns:
        Merged metadata dictionary or None if both sources failed
    """
    if primary is None and fallback is None:
        logger.error("Both API sources failed to return metadata")
        return None
    
    # Determine which source to use as base (prefer most recent edition)
    chosen = None
    if primary and fallback:
        # Compare publication years to pick the most recent
        primary_year = primary.get('publication_year', '')
        fallback_year = fallback.get('publication_year', '')
        try:
            if int(primary_year or 0) >= int(fallback_year or 0):
                chosen = primary
                logger.info("Using Open Library as primary source (newer or equal edition)")
            else:
                chosen = fallback
                logger.info("Using Google Books as primary source (newer edition)")
        except (ValueError, TypeError):
            chosen = primary
            logger.info("Using Open Library as primary source (year comparison failed)")
    else:
        chosen = primary or fallback
        source_name = "Open Library" if primary else "Google Books"
        logger.info(f"Using {source_name} as only available source")
    
    # Start with chosen source
    base_metadata = chosen.copy()
    
    # Merge missing fields from the other source
    other = fallback if chosen == primary else primary
    if other:
        for key, value in other.items():
            if key not in ['source', 'source_priority']:
                # Fill in if missing or empty
                if not base_metadata.get(key) or base_metadata.get(key) == []:
                    base_metadata[key] = value
                    logger.debug(f"Filled missing field '{key}' from alternate source")
    
    # Build comprehensive merged metadata
    # Use fetched data as authoritative source (user input only used for search)
    merged = {
        'isbn': input_data.isbn or base_metadata.get('isbn_13') or base_metadata.get('isbn_10'),
        'isbn_10': (primary or {}).get('isbn_10') or (fallback or {}).get('isbn_10'),
        'isbn_13': (primary or {}).get('isbn_13') or (fallback or {}).get('isbn_13'),
        'title': base_metadata.get('title'),  # Always use fetched title
        'authors': base_metadata.get('authors', []),  # Always use fetched authors
        'publisher': base_metadata.get('publisher'),
        'publication_year': base_metadata.get('publication_year'),
        'edition': base_metadata.get('edition'),
        'language': base_metadata.get('language'),
        'description': (primary or {}).get('description') or (fallback or {}).get('description'),
        'table_of_contents': (primary or {}).get('table_of_contents'),
        'subjects': (primary or {}).get('subjects'),
        'categories': (fallback or {}).get('categories') or (primary or {}).get('categories'),
        'page_count': (fallback or {}).get('page_count'),
        'cover_url': (fallback or {}).get('cover_url') or (primary or {}).get('cover_url'),
        'preview_link': (fallback or {}).get('preview_link'),
        'total_copies': input_data.total_copies,
        'keywords': None,
        'embeddings': None,
        'source': base_metadata.get('source'),
        'source_priority': chosen.get('source')
    }
    
    # Create embedding_text by combining rich text fields for AI processing
    rich_text_fields = [
        merged.get('title', ''),
        safe_join_list(merged.get('authors')),
        merged.get('description', ''),
        safe_join_lines(merged.get('table_of_contents')),
        safe_join_list(merged.get('subjects')),
        safe_join_list(merged.get('categories')),
    ]
    
    # Filter out empty strings and join with newlines
    embedding_text = "\n".join(filter(None, rich_text_fields))
    merged['embedding_text'] = embedding_text if embedding_text else None
    
    logger.info(f"Merged metadata complete. Embedding text length: {len(embedding_text) if embedding_text else 0} chars")
    
    return merged


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Smart Library Management System (SLMS)",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "Metadata Extraction (Open Library, Google Books)",
            "Librarian Confirmation Workflow",
            "Audit Logging"
        ]
    }


# NOTE: The /catalogue/add endpoint has been moved to routes/catalogue.py
# It now creates a pending_catalogue entry AND fetches metadata in a single unified operation.
# This eliminates the previous duplicate endpoint issue.


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    Tests connectivity to external APIs.
    """
    health_status = {
        "service": "operational",
        "apis": {}
    }
    
    # Test Open Library
    try:
        response = requests.get(OPENLIBRARY_API_URL, timeout=2)
        health_status["apis"]["open_library"] = "reachable" if response.status_code < 500 else "degraded"
    except:
        health_status["apis"]["open_library"] = "unreachable"
    
    # Test Google Books
    try:
        response = requests.get(GOOGLEBOOKS_API_URL, timeout=2)
        health_status["apis"]["google_books"] = "reachable" if response.status_code < 500 else "degraded"
    except:
        health_status["apis"]["google_books"] = "unreachable"
    
    return health_status


if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT, RELOAD
    uvicorn.run(app, host=HOST, port=PORT, reload=RELOAD)
