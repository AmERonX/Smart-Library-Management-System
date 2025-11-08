import os
import json
import time
from typing import Dict, Any, List, Optional

import requests
from bs4 import BeautifulSoup
import google.generativeai as genai

from config import GOOGLE_API_KEY, LANGSEARCH_KEY

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


def _langsearch_search(query: str, count: int = 3, timeout: int = 10) -> List[Dict[str, Any]]:
    if not LANGSEARCH_KEY:
        return []
    url = "https://api.langsearch.com/v1/web-search"
    headers = {"Authorization": f"Bearer {LANGSEARCH_KEY}", "Content-Type": "application/json"}
    body = {"query": query, "freshness": "noLimit", "summary": True, "count": count}
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        resp.raise_for_status()
        j = resp.json()
        return j.get("data", {}).get("webPages", {}).get("value", [])
    except Exception:
        return []


def _langsearch_rerank(query: str, docs: List[str], top_n: Optional[int] = None, timeout: int = 15) -> List[int]:
    if not LANGSEARCH_KEY or not docs:
        return []
    url = "https://api.langsearch.com/v1/rerank"
    headers = {"Authorization": f"Bearer {LANGSEARCH_KEY}", "Content-Type": "application/json"}
    body: Dict[str, Any] = {"model": "langsearch-reranker-v1", "query": query, "documents": docs}
    if top_n is not None:
        body["top_n"] = top_n
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=timeout)
        resp.raise_for_status()
        j = resp.json()
        results = j.get("results") or j.get("data", {}).get("results", [])
        sorted_by_score = sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)
        return [int(r.get("index")) for r in sorted_by_score if "index" in r]
    except Exception:
        return []


def _fetch_page(url: str, timeout: int = 8) -> Optional[str]:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, timeout=timeout, headers=headers)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def _clean_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for s in soup(["script", "style", "noscript", "iframe", "svg"]):
        s.decompose()
    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return "\n".join(lines)[:8000]


def _extract_with_gemini(page_text: str) -> Optional[Dict[str, Any]]:
    if not GOOGLE_API_KEY:
        return None
    prompt = f"""
You are an expert bibliographic cataloguer and subject indexer for academic and technical books.
Your task is to analyze the following page text and produce structured JSON metadata that captures both
bibliographic details and intellectual content. You must distinguish between *descriptive* metadata and
*subject-level* conceptual information.

Return a single JSON object with these exact keys:
"title", "authors" (array of all author names), "publisher", "year", "edition",
"description" (a factual 120–200 word summary of the book's purpose, topics, and coverage — NOT marketing text),
"keywords" (8–12 concept-level terms, describing the *core technical or thematic ideas* discussed in the book.
Exclude any words related to format, publisher, author names, or edition information. Prefer nouns like
'data modeling', 'query optimization', 'sql', 'distributed systems', 'database design'),
"broad_categories" (3–5 general academic or topical areas),
"sub_disciplines" (3–6 fine-grained domains under those categories, e.g., 'Relational Databases', 'Concurrency Control'),
"isbn_10", "isbn_13", and "evidence" (list of up to 3 short text snippets that support your extracted data).

If any field is missing, use null or [].
Return strictly valid JSON — no Markdown, no commentary, no code fences.

Example:
{
  {
  "title": "Example Book",
  "authors": ["Alice Smith", "Bob Dylan"],
  "publisher": "Academic Press",
  "year": "2021",
  "edition": "2nd Edition",
  "description": "This book provides a structured introduction to algorithmic design and analysis...",
  "keywords": ["algorithm analysis", "computational complexity", "graph algorithms", "dynamic programming"],
  "broad_categories": ["Computer Science", "Mathematics"],
  "sub_disciplines": ["Algorithms", "Combinatorial Optimization", "Computational Theory"],
  "isbn_10": "1234567890",
  "isbn_13": "9781234567890",
  "evidence": ["Title: Example Book", "By Smith and Dylan", "Published 2021 by Academic Press"]
  },
  {
  "title": "Artificial Intelligence: A Modern Approach",
  "authors": ["Stuart Russell", "Peter Norvig"],
  "publisher": "Pearson",
  "year": "2021",
  "description": "Standard reference for AI theory and practice, from search and reasoning to deep learning...",
  "keywords": ["artificial intelligence", "Intelligent Agents","machine learning", "reasoning", "planning", "neural networks"],
  "broad_categories": ["Computer Science", "Mathematics", "Engineering"],
  "sub_disciplines": [ "Machine Learning", "Deep Learning", "Natural language processing", "Reinforcemett Learning", " "],
  "isbn_10": "null",
  "isbn_13": "null",
  "evidence": ["Title: Artificial Intelligence: A Modern Approach", "By Russell and Norvig", "Published 2021 by Pearson"]
  }
}

Now extract this same structure from the following book page text:
{page_text[:8000]}
"""
    try:
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip().replace("```json", "").replace("```", "")
        return json.loads(text)
    except Exception:
        return None


def enhance(book_record: Dict[str, Any]) -> Dict[str, Any]:
    title = book_record.get("title") or ""
    authors = ", ".join(book_record.get("authors") or [])
    isbn = book_record.get("isbn") or book_record.get("isbn_13") or book_record.get("isbn_10") or ""
    query = f"{title} by {authors}" + (f" (ISBN {isbn})" if isbn else "")

    results = _langsearch_search(query, count=10)
    urls: List[Optional[str]] = []
    docs: List[str] = []
    for r in results:
        u = r.get("url") or r.get("id")
        urls.append(u)
        doc = " ".join([x for x in [r.get("name"), r.get("snippet"), r.get("summary")] if x])
        docs.append(doc)

    extracted: Optional[Dict[str, Any]] = None
    tried: set[int] = set()

    ranked_indices: List[int] = _langsearch_rerank(query, docs, top_n=min(5, len(docs))) if docs else []
    if ranked_indices:
        for idx in ranked_indices:
            if 0 <= idx < len(urls) and urls[idx]:
                tried.add(idx)
                html = _fetch_page(urls[idx])
                if not html:
                    continue
                text = _clean_visible_text(html)
                if not text:
                    continue
                extracted = _extract_with_gemini(text)
                if extracted:
                    break

    if not extracted:
        for i, u in enumerate(urls):
            if i in tried or not u:
                continue
            html = _fetch_page(u)
            if not html:
                continue
            text = _clean_visible_text(html)
            if not text:
                continue
            extracted = _extract_with_gemini(text)
            if extracted:
                break

    enhanced: Dict[str, Any] = {
        "title": extracted.get("title") if extracted else title,
        "authors": extracted.get("authors") if (extracted and isinstance(extracted.get("authors"), list)) else (book_record.get("authors") or []),
        "publisher": extracted.get("publisher") if extracted else (book_record.get("publisher")),
        "publication_year": extracted.get("year") if extracted else (book_record.get("year")),
        "edition": extracted.get("edition") if extracted else (book_record.get("edition")),
        "description": extracted.get("description") if extracted else None,
        "keywords": extracted.get("keywords") if extracted else [],
        "broad_categories": extracted.get("broad_categories") if extracted else [],
        "sub_disciplines": extracted.get("sub_disciplines") if extracted else [],
        "isbn_10": extracted.get("isbn_10") if extracted else book_record.get("isbn_10"),
        "isbn_13": extracted.get("isbn_13") if extracted else book_record.get("isbn_13"),
        "evidence": extracted.get("evidence") if extracted else [],
        "source": "langsearch_gemini"
    }

    if not enhanced.get("title"):
        enhanced["title"] = title
    if not enhanced.get("authors"):
        enhanced["authors"] = book_record.get("authors") or []

    return enhanced
