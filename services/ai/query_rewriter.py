import logging
from functools import lru_cache
from typing import Optional

import google.generativeai as genai

from config import (
    ENABLE_QUERY_REWRITER,
    GOOGLE_API_KEY,
    QUERY_REWRITER_MODEL,
    QUERY_REWRITER_PROMPT_PATH,
)

logger = logging.getLogger(__name__)

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)


@lru_cache(maxsize=1)
def _load_prompt() -> Optional[str]:
    try:
        with open(QUERY_REWRITER_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error(
            "Query rewriter prompt file not found at %s", QUERY_REWRITER_PROMPT_PATH
        )
    except OSError as exc:
        logger.error(
            "Unable to read query rewriter prompt at %s: %s",
            QUERY_REWRITER_PROMPT_PATH,
            exc,
        )
    return None


@lru_cache(maxsize=None)
def _get_model(model_name: str):
    return genai.GenerativeModel(model_name)


def _extract_text(response) -> str:
    if response is None:
        return ""

    # google-generativeai may expose `.text` or `.candidates`
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    candidates = getattr(response, "candidates", None)
    if candidates:
        for candidate in candidates:
            parts = getattr(candidate, "content", None)
            if parts and getattr(parts, "parts", None):
                for part in parts.parts:
                    value = getattr(part, "text", None)
                    if isinstance(value, str) and value.strip():
                        return value
            value = getattr(candidate, "text", None)
            if isinstance(value, str) and value.strip():
                return value

    return ""


def enhance_query(raw_query: str) -> Optional[str]:
    """
    Use a configured LLM to enrich the raw user query with structured context.
    Returns None on failure so callers can gracefully fall back.
    """
    if not ENABLE_QUERY_REWRITER:
        return None
    if not GOOGLE_API_KEY:
        logger.warning("GOOGLE_API_KEY not set; skipping query enrichment.")
        return None

    template = _load_prompt()
    if not template:
        return None

    prompt = template.replace("{query}", (raw_query or "").strip())
    model_name = QUERY_REWRITER_MODEL or "gemini-2.5-flash-lite"

    try:
        model = _get_model(model_name)
        response = model.generate_content(prompt)
        enhanced_text = _extract_text(response).strip()
        if not enhanced_text:
            logger.warning("Query rewriter produced empty response.")
            return None
        return enhanced_text
    except Exception as exc:  # noqa: BLE001
        logger.error("Query rewriter failed: %s", exc, exc_info=True)
        return None

