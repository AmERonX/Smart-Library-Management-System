import re
from typing import Dict

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
