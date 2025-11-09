import os
import json
import logging
from typing import Dict, Any, Optional

import numpy as np
import google.generativeai as genai
from sqlalchemy.orm import Session

from config import GOOGLE_API_KEY, ENHANCED_BOOKS_DIR, ENABLE_EMBEDDINGS
from database import SessionLocal
from models import Book, BookFaissMap
from services.ai import faiss_sync
from services.ai import metadata_enhancer
from services.vectorizer import embed_text as embed_text_shared

logger = logging.getLogger(__name__)

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


def _embed_text(text: str) -> Optional[np.ndarray]:
    try:
        return embed_text_shared(text)
    except RuntimeError:
        # Likely disabled or not configured
        return None


def _identity_text(enhanced: Dict[str, Any]) -> str:
    title = enhanced.get("title") or ""
    authors = ", ".join(enhanced.get("authors") or [])
    publisher = enhanced.get("publisher") or ""
    parts = [title]
    if authors:
        parts.append(f"by {authors}")
    if publisher:
        parts.append(f"published by {publisher}")
    return " ".join([p for p in parts if p]).strip()


def _topical_text(enhanced: Dict[str, Any]) -> str:
    topical_terms = (enhanced.get("keywords") or []) + (enhanced.get("broad_categories") or []) + (enhanced.get("sub_disciplines") or [])
    topical_terms = [t for t in topical_terms if isinstance(t, str) and t.strip()]
    if topical_terms:
        return ", ".join(topical_terms)
    return f"{enhanced.get('title') or ''} {enhanced.get('description') or ''}"


def _get_or_create_map(db: Session, book_id: int, vector_type: str) -> int:
    row = db.query(BookFaissMap).filter_by(book_id=book_id, vector_type=vector_type).first()
    if row:
        return int(row.id)
    # Do not assign to faiss_id here; in Postgres it's a GENERATED ALWAYS column.
    # Just insert (book_id, vector_type) and use the row's primary key as the FAISS ID.
    row = BookFaissMap(book_id=book_id, vector_type=vector_type)
    db.add(row)
    db.flush()  # assign id
    db.commit()
    db.refresh(row)
    return int(row.id)


def store_enhanced_embeddings(
    db: Session,
    book_id: int,
    enhanced: Dict[str, Any],
    identity_vec: Optional[np.ndarray],
    topical_vec: Optional[np.ndarray],
) -> Dict[str, Any]:
    book = db.query(Book).filter(Book.book_id == book_id).first()
    if not book:
        raise ValueError(f"Book not found: {book_id}")

    book.enhanced_metadata = enhanced
    db.commit()

    identity_id = None
    topical_id = None
    if ENABLE_EMBEDDINGS and identity_vec is not None and topical_vec is not None:
        identity_id = _get_or_create_map(db, book_id, "identity")
        topical_id = _get_or_create_map(db, book_id, "topical")
        faiss_sync.append("identity", identity_id, identity_vec)
        faiss_sync.append("topical", topical_id, topical_vec)

    # Optional export to filesystem
    try:
        os.makedirs(ENHANCED_BOOKS_DIR, exist_ok=True)
        out_path = os.path.join(ENHANCED_BOOKS_DIR, f"{book_id}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(enhanced, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Could not write enhanced JSON export for book_id={book_id}: {e}")

    return {
        "book_id": book_id,
        "identity_faiss_id": int(identity_id) if identity_id is not None else None,
        "topical_faiss_id": int(topical_id) if topical_id is not None else None,
    }


def enhance_and_store(book_id: int, engine=None) -> Dict[str, Any]:
    db = SessionLocal() if engine is None else Session(bind=engine)
    try:
        book = db.query(Book).filter(Book.book_id == book_id).first()
        if not book:
            raise ValueError(f"Book not found: {book_id}")

        base = {
            "title": book.title,
            "authors": [ba.author.full_name for ba in (book.authors or [])],
            "publisher": book.publisher.name if book.publisher else None,
            "year": book.publication_year,
            "edition": book.edition,
            "isbn_10": book.isbn_10,
            "isbn_13": book.isbn_13,
        }
        enhanced = metadata_enhancer.enhance(base)

        identity_vec = None
        topical_vec = None
        if ENABLE_EMBEDDINGS:
            identity_text = _identity_text(enhanced)
            topical_text = _topical_text(enhanced)
            identity_vec = _embed_text(identity_text)
            topical_vec = _embed_text(topical_text)

        return store_enhanced_embeddings(db, book_id, enhanced, identity_vec, topical_vec)
    except Exception as e:
        logger.error(f"Enhance-and-store failed for book_id={book_id}: {e}")
        return {"success": False, "error": str(e)}
    finally:
        try:
            db.close()
        except Exception:
            pass
