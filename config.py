"""
Configuration settings for Smart Cataloguing Pipeline
Centralized configuration for easy customization and environment-specific settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables early
load_dotenv()

# ============================================================================
# API CONFIGURATION
# ============================================================================

# External API URLs
OPENLIBRARY_API_URL = os.getenv(
    "OPENLIBRARY_API_URL",
    "https://openlibrary.org/api/books"
)

GOOGLEBOOKS_API_URL = os.getenv(
    "GOOGLEBOOKS_API_URL",
    "https://www.googleapis.com/books/v1/volumes"
)

# Google Books API Key (optional, increases rate limits)
GOOGLEBOOKS_API_KEY: Optional[str] = os.getenv("GOOGLEBOOKS_API_KEY", None)

# ============================================================================
# PERFORMANCE SETTINGS
# ============================================================================

# Request timeout in seconds
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "5"))

# Maximum retries for failed API calls
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))

# ============================================================================
# VALIDATION SETTINGS
# ============================================================================

# ISBN validation pattern (allows X/x as ISBN-10 check digit)
ISBN_PATTERN = r'^(\d{9}[\dXx]|\d{13})$'

# Minimum number of core fields required from Open Library
MIN_CORE_FIELDS = 3

# Core fields to check for completeness
CORE_FIELDS = ['title', 'publishers', 'publish_date']

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

# Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Log format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================

# Server host
HOST = os.getenv("HOST", "0.0.0.0")

# Server port
PORT = int(os.getenv("PORT", "8000"))

# Enable auto-reload (development only)
RELOAD = os.getenv("RELOAD", "False").lower() == "true"

# ============================================================================
# FEATURE FLAGS
# ============================================================================

# Enable/disable Open Library as primary source
ENABLE_OPENLIBRARY = os.getenv("ENABLE_OPENLIBRARY", "True").lower() == "true"

# Enable/disable Google Books as fallback
ENABLE_GOOGLEBOOKS = os.getenv("ENABLE_GOOGLEBOOKS", "True").lower() == "true"

# Enable detailed API response logging
ENABLE_API_LOGGING = os.getenv("ENABLE_API_LOGGING", "True").lower() == "true"

# ============================================================================
# AI ENHANCEMENT CONFIGURATION
# ============================================================================

# Feature flag to enable AI enhancement pipeline
ENABLE_AI_ENHANCEMENT = os.getenv("ENABLE_AI_ENHANCEMENT", "True").lower() == "true"

# Keys for Gemini and LangSearch
GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY", None)
LANGSEARCH_KEY: Optional[str] = os.getenv("LANGSEARCH_KEY", None)

# File system paths for artifacts
ENHANCED_BOOKS_DIR = os.getenv("ENHANCED_BOOKS_DIR", os.path.join("data", "enhanced_books"))
FAISS_INDEX_DIR = os.getenv("FAISS_INDEX_DIR", os.path.join("data", "faiss_index"))
FAISS_INDEX_PATH = os.path.join(FAISS_INDEX_DIR, "library_index.faiss")
FAISS_ID_MAP_PATH = os.path.join(FAISS_INDEX_DIR, "id_map.json")

# Dual FAISS indexes and lock files (new)
FAISS_IDENTITY_INDEX_PATH = os.path.join(FAISS_INDEX_DIR, "faiss_identity.index")
FAISS_TOPICAL_INDEX_PATH = os.path.join(FAISS_INDEX_DIR, "faiss_topical.index")
FAISS_IDENTITY_LOCK_PATH = os.path.join(FAISS_INDEX_DIR, "faiss_identity.lock")
FAISS_TOPICAL_LOCK_PATH = os.path.join(FAISS_INDEX_DIR, "faiss_topical.lock")

# Strict validation toggle (fail startup if AI keys missing)
STRICT_AI_VALIDATION = os.getenv("STRICT_AI_VALIDATION", "False").lower() == "true"

# ============================================================================
# FUTURE CONFIGURATION (Step 2+)
# ============================================================================

# Redis configuration (for future async implementation)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Celery configuration (for future async implementation)
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

# Note: DATABASE_URL is defined in database.py (not here to avoid duplication)
# See database.py for database configuration

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_googlebooks_url() -> str:
    """Get Google Books API URL with optional API key."""
    if GOOGLEBOOKS_API_KEY:
        return f"{GOOGLEBOOKS_API_URL}?key={GOOGLEBOOKS_API_KEY}"
    return GOOGLEBOOKS_API_URL


def is_production() -> bool:
    """Check if running in production environment."""
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def get_config_summary() -> dict:
    """Get a summary of current configuration (for debugging)."""
    return {
        "apis": {
            "open_library": {
                "enabled": ENABLE_OPENLIBRARY,
                "url": OPENLIBRARY_API_URL
            },
            "google_books": {
                "enabled": ENABLE_GOOGLEBOOKS,
                "url": GOOGLEBOOKS_API_URL,
                "api_key_configured": bool(GOOGLEBOOKS_API_KEY)
            }
        },
        "performance": {
            "request_timeout": REQUEST_TIMEOUT,
            "max_retries": MAX_RETRIES
        },
        "server": {
            "host": HOST,
            "port": PORT,
            "reload": RELOAD
        },
        "environment": os.getenv("ENVIRONMENT", "development"),
        "logging": {
            "level": LOG_LEVEL,
            "api_logging": ENABLE_API_LOGGING
        },
        "ai_enhancement": {
            "enabled": ENABLE_AI_ENHANCEMENT,
            "google_api_key_configured": bool(GOOGLE_API_KEY),
            "langsearch_key_configured": bool(LANGSEARCH_KEY),
            "paths": {
                "enhanced_books_dir": ENHANCED_BOOKS_DIR,
                "faiss_index_dir": FAISS_INDEX_DIR
            }
        }
    }


# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Validate configuration settings."""
    errors = []
    
    if not ENABLE_OPENLIBRARY and not ENABLE_GOOGLEBOOKS:
        errors.append("At least one API source must be enabled")
    
    if REQUEST_TIMEOUT < 1:
        errors.append("REQUEST_TIMEOUT must be at least 1 second")
    
    if MAX_RETRIES < 0:
        errors.append("MAX_RETRIES cannot be negative")
    
    # AI enhancement validation (soft by default)
    if ENABLE_AI_ENHANCEMENT and STRICT_AI_VALIDATION:
        if not GOOGLE_API_KEY:
            errors.append("GOOGLE_API_KEY is required when ENABLE_AI_ENHANCEMENT and STRICT_AI_VALIDATION are true")
        if not LANGSEARCH_KEY:
            errors.append("LANGSEARCH_KEY is required when ENABLE_AI_ENHANCEMENT and STRICT_AI_VALIDATION are true")

    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")


# Validate configuration on import
validate_config()
