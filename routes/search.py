"""
Semantic Search Routes
Provides POST /search/semantic to retrieve semantically similar books.
"""

import logging
from typing import List, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database import get_db
from schemas import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchHit,
    ErrorResponse,
)
from services.query_processing import prepare_query
from services.vectorizer import embed_text
from services.ai.faiss_sync import search as faiss_search
from models import BookFaissMap, Book
from config import ENABLE_SEMANTIC_SEARCH

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/search",
    tags=["Semantic Search"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        503: {"model": ErrorResponse, "description": "Embedding service unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)


def _fetch_results(
    db: Session,
    vector_type: str,
    query_vec,
    top_k: int,
) -> List[Dict]:
    hits: List[Tuple[int, float]] = faiss_search(vector_type, query_vec, k=top_k)
    if not hits:
        return []

    try:
        faiss_ids = [fid for fid, _ in hits]
        mappings: List[BookFaissMap] = (
            db.query(BookFaissMap)
            .filter(BookFaissMap.id.in_(faiss_ids), BookFaissMap.vector_type == vector_type)
            .all()
        )
        if not mappings:
            return []

        by_fid: Dict[int, BookFaissMap] = {m.id: m for m in mappings}
        book_ids = list({m.book_id for m in mappings})

        books: List[Book] = db.query(Book).filter(Book.book_id.in_(book_ids)).all()
        by_book: Dict[int, Book] = {b.book_id: b for b in books}

        results: List[Dict] = []
        for fid, score in hits:
            m = by_fid.get(int(fid))
            if not m:
                continue
            book = by_book.get(int(m.book_id))
            if not book:
                continue
            authors = [ba.author.full_name for ba in (book.authors or [])]
            results.append(
                {
                    "book_id": int(book.book_id),
                    "score": float(score),
                    "vector_type": vector_type,
                    "title": book.title,
                    "authors": authors or None,
                    "publisher": book.publisher.name if book.publisher else None,
                    "publication_year": str(book.publication_year) if book.publication_year is not None else None,
                }
            )
        return results
    except SQLAlchemyError:
        # If mapping tables are missing or DB not initialized, return no results instead of 500
        return []


@router.post(
    "/semantic",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic vector search over the catalogue",
)
def semantic_search(req: SemanticSearchRequest, db: Session = Depends(get_db)):
    try:
        if not ENABLE_SEMANTIC_SEARCH:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Semantic search disabled by configuration (ENABLE_SEMANTIC_SEARCH=false)",
            )
        q_raw = req.query
        q_proc = prepare_query(
            q_raw,
            normalize=req.normalize,
            expand=req.expand,
        )

        try:
            vec = embed_text(q_proc)
        except RuntimeError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e),
            )

        if req.mode == "identity":
            merged = _fetch_results(db, "identity", vec, req.top_k)
        elif req.mode == "topical":
            merged = _fetch_results(db, "topical", vec, req.top_k)
        else:
            ident = _fetch_results(db, "identity", vec, req.top_k)
            topic = _fetch_results(db, "topical", vec, req.top_k)
            best: Dict[int, Dict] = {}
            for r in ident + topic:
                bid = int(r["book_id"])
                if bid not in best or r["score"] > best[bid]["score"]:
                    best[bid] = r
            merged = sorted(best.values(), key=lambda x: x["score"], reverse=True)[: req.top_k]

        return {
            "query_raw": q_raw,
            "query_processed": q_proc,
            "mode": req.mode,
            "results": [SemanticSearchHit(**r) for r in merged],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Semantic search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during semantic search",
        )
