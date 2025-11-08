"""
Minimal E2E test for AI enhancement pipeline (LangSearch + Gemini only).
Skips if GOOGLE_API_KEY or LANGSEARCH_KEY are not configured.
Updated to verify FAISS-only storage with DB mapping rows (no legacy id_map.json).
"""

import os
import time
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
import os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

from database import Base, get_db
from models import BookFaissMap
from main import app

# ----------------------------------------------------------------------------
# Skip if API keys missing
# ----------------------------------------------------------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LANGSEARCH_KEY = os.getenv("LANGSEARCH_KEY")

if not GOOGLE_API_KEY or not LANGSEARCH_KEY:
    pytest.skip("GOOGLE_API_KEY and/or LANGSEARCH_KEY not set; skipping E2E AI pipeline test", allow_module_level=True)

# ----------------------------------------------------------------------------
# Test database (SQLite) override
# ----------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_ai_pipeline.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Override dependency
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ----------------------------------------------------------------------------
# E2E: approve -> insert -> background enhancement -> artifacts
# ----------------------------------------------------------------------------

def test_ai_pipeline_artifacts_created():
    # 1) Add a book
    add_resp = client.post(
        "/catalogue/add",
        json={
            "isbn": "9780132350884",
            "title": "Clean Code",
            "authors": ["Robert C. Martin"],
            "total_copies": 1
        }
    )
    assert add_resp.status_code == 201
    pending_id = add_resp.json()["pending_id"]

    # 2) Approve the book (no pipeline yet)
    conf_resp = client.post(
        f"/catalogue/confirm/{pending_id}",
        json={"approved": True, "reason": "E2E test"}
    )
    assert conf_resp.status_code == 200

    # 3) Insert into main catalogue (triggers background enhancement)
    ins_resp = client.post(f"/catalogue/insert/{pending_id}")
    assert ins_resp.status_code == 200
    book_id = ins_resp.json().get("book_id")
    assert book_id is not None

    # 4) Wait for background task to finish
    time.sleep(8)

    # 5) Assert artifacts (dual FAISS indexes, DB mappings)
    enhanced_path = os.path.join("data", "enhanced_books", f"{book_id}.json")
    faiss_identity = os.path.join("data", "faiss_index", "faiss_identity.index")
    faiss_topical = os.path.join("data", "faiss_index", "faiss_topical.index")

    assert os.path.exists(enhanced_path), f"Missing enhanced JSON: {enhanced_path}"
    assert os.path.exists(faiss_identity), f"Missing FAISS identity index: {faiss_identity}"
    assert os.path.exists(faiss_topical), f"Missing FAISS topical index: {faiss_topical}"

    with open(enhanced_path, "r", encoding="utf-8") as f:
        enhanced = json.load(f)
    assert enhanced.get("title")
    # Check mapping rows exist
    db = TestingSessionLocal()
    try:
        rows = db.query(BookFaissMap).filter(BookFaissMap.book_id == int(book_id)).all()
        kinds = {r.vector_type for r in rows}
        assert "identity" in kinds and "topical" in kinds
    finally:
        db.close()
