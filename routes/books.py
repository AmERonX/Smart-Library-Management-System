import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import asc, desc, func

from database import get_db
from models import Book, Author, Publisher, BookAuthor, BookMetadata
from schemas import (
    BooksListResponse,
    BookListItem,
    BookDetailResponse,
    PublisherRef,
    AuthorRef,
    ErrorResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/books",
    tags=["Books"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


@router.get("", response_model=BooksListResponse)
def list_books(
    page: int = 1,
    page_size: int = 20,
    q: Optional[str] = None,
    author: Optional[str] = None,
    publisher: Optional[str] = None,
    year: Optional[str] = None,
    year_from: Optional[str] = None,
    year_to: Optional[str] = None,
    sort: str = "created_desc",
    db: Session = Depends(get_db),
):
    try:
        if page < 1 or page_size < 1 or page_size > 100:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid pagination params")

        query = db.query(Book)

        if q:
            qv = f"%{(q or '').lower()}%"
            query = query.filter(func.lower(Book.title).like(qv))

        if author:
            av = f"%{(author or '').lower()}%"
            query = query.filter(
                Book.authors.any(
                    BookAuthor.author.has(func.lower(Author.full_name).like(av))
                )
            )

        if publisher:
            pv = f"%{(publisher or '').lower()}%"
            query = query.filter(Book.publisher.has(func.lower(Publisher.name).like(pv)))

        if year:
            query = query.filter(Book.publication_year == year)
        else:
            if year_from:
                query = query.filter(Book.publication_year >= str(year_from))
            if year_to:
                query = query.filter(Book.publication_year <= str(year_to))

        # Sorting
        if sort == "title_asc":
            query = query.order_by(asc(Book.title))
        elif sort == "year_asc":
            query = query.order_by(asc(Book.publication_year))
        elif sort == "year_desc":
            query = query.order_by(desc(Book.publication_year))
        else:  # created_desc
            query = query.order_by(desc(Book.created_at))

        total = query.count()
        items: List[Book] = query.offset((page - 1) * page_size).limit(page_size).all()

        # Build mapping for authors per book
        result_items: List[BookListItem] = []
        for b in items:
            authors_list = [ba.author.full_name for ba in (b.authors or [])]
            result_items.append(
                BookListItem(
                    book_id=int(b.book_id),
                    title=b.title,
                    authors=authors_list or None,
                    publisher=b.publisher.name if b.publisher else None,
                    publication_year=str(b.publication_year) if b.publication_year is not None else None,
                    available_copies=int(b.available_copies),
                    cover_url=b.cover_url,
                )
            )

        return BooksListResponse(total=int(total), page=page, page_size=page_size, items=result_items)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing books: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error while listing books")


@router.get("/{book_id}", response_model=BookDetailResponse)
def get_book_detail(book_id: int, db: Session = Depends(get_db)):
    try:
        book: Optional[Book] = db.query(Book).filter(Book.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Book with id {book_id} not found")

        publisher_ref = None
        if book.publisher:
            publisher_ref = PublisherRef(publisher_id=int(book.publisher.publisher_id), name=book.publisher.name)

        authors_refs: List[AuthorRef] = []
        for ba in (book.authors or []):
            if ba.author:
                authors_refs.append(AuthorRef(author_id=int(ba.author.author_id), full_name=ba.author.full_name))

        # Get book metadata (description, keywords, etc.)
        book_metadata = db.query(BookMetadata).filter(BookMetadata.book_id == book_id).first()
        
        # Merge enhanced_metadata with book_metadata description if available
        # Use dict() to ensure we have a mutable dict (JSONB may return different types)
        enhanced_metadata = dict(book.enhanced_metadata) if book.enhanced_metadata else {}
        if book_metadata:
            # Add description to enhanced_metadata if not already present
            if book_metadata.description and ('description' not in enhanced_metadata or not enhanced_metadata.get('description')):
                enhanced_metadata['description'] = book_metadata.description
            # Add keywords if available
            if book_metadata.keywords and ('keywords' not in enhanced_metadata or not enhanced_metadata.get('keywords')):
                enhanced_metadata['keywords'] = book_metadata.keywords

        return BookDetailResponse(
            book_id=int(book.book_id),
            title=book.title,
            isbn=book.isbn,
            isbn_10=book.isbn_10,
            isbn_13=book.isbn_13,
            publication_year=str(book.publication_year) if book.publication_year is not None else None,
            edition=book.edition,
            cover_url=book.cover_url,
            total_copies=int(book.total_copies),
            available_copies=int(book.available_copies),
            publisher=publisher_ref,
            authors=authors_refs,
            enhanced_metadata=enhanced_metadata if enhanced_metadata else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching book detail for id {book_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error while fetching book detail")
