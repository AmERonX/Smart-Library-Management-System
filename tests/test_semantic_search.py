import os
import pytest
from fastapi.testclient import TestClient

import sys
import os as _os
sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..')))

from main import app

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    pytest.skip("GOOGLE_API_KEY not set; skipping semantic search tests", allow_module_level=True)

client = TestClient(app)


def test_semantic_search_empty_index_returns_200():
    resp = client.post(
        "/search/semantic",
        json={
            "query": "clean code software engineering",
            "mode": "hybrid",
            "top_k": 5,
            "normalize": True,
            "expand": False,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["query_raw"] == "clean code software engineering"
    assert body["mode"] == "hybrid"
    assert isinstance(body.get("results"), list)
