import re
from typing import Dict

from config import ENABLE_SEMANTIC_QUERY_NORMALIZE
from services.ai.query_rewriter import enhance_query

_whitespace_re = re.compile(r"\s+")
_punct_re = re.compile(r"[\"'\u2018\u2019\u201C\u201D\u2014]")

_SYNONYMS: Dict[str, str] = {
    "ai": "artificial intelligence",
    "ml": "machine learning",
    "db": "database",
    "dbms": "database management system",
    "nlp": "natural language processing",
}


def normalize_query(q: str) -> str:
    q = (q or "").strip().lower()
    q = _punct_re.sub(" ", q)
    q = _whitespace_re.sub(" ", q)
    return q


def expand_query(q: str) -> str:
    tokens = q.split()
    expanded = []
    for t in tokens:
        expanded.append(t)
        if t in _SYNONYMS:
            expanded.append(_SYNONYMS[t])
    return " ".join(expanded) if expanded else q


def prepare_query(
    raw_query: str,
    *,
    normalize: bool = True,
    expand: bool = False,
) -> str:
    """
    Enrich the raw query via LLM (if enabled). Falls back to legacy
    normalize/expand handling when enrichment is unavailable.
    """
    if not raw_query:
        return ""

    enriched = enhance_query(raw_query)
    if enriched:
        return enriched

    processed = raw_query
    if normalize and ENABLE_SEMANTIC_QUERY_NORMALIZE:
        processed = normalize_query(processed)

    if expand:
        processed = expand_query(processed)

    return processed
