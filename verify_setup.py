#!/usr/bin/env python3
"""
Setup Verification Script for SLMS
Run this script to verify your installation is correct.
"""

import sys
import subprocess
import os
from pathlib import Path


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_check(name, status, message=""):
    """Print a check result."""
    symbol = "✓" if status else "✗"
    color = "\033[92m" if status else "\033[91m"  # Green or Red
    reset = "\033[0m"
    
    print(f"{color}{symbol}{reset} {name}", end="")
    if message:
        print(f" - {message}")
    else:
        print()


def check_python_version():
    """Check if Python version is 3.10+."""
    version = sys.version_info
    is_valid = version.major == 3 and version.minor >= 10
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    print_check(
        "Python Version",
        is_valid,
        f"Found {version_str} {'(OK)' if is_valid else '(Need 3.10+)'}"
    )
    return is_valid


def check_ai_keys():
    """Check AI-related environment keys (optional)."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        google_key = os.getenv('GOOGLE_API_KEY')
        ls_key = os.getenv('LANGSEARCH_KEY')
        configured = bool(google_key) and bool(ls_key)
        if configured:
            print_check("AI Keys", True, "GOOGLE_API_KEY and LANGSEARCH_KEY configured")
        else:
            # Optional but recommended for AI pipeline and semantic search
            missing = []
            if not google_key:
                missing.append('GOOGLE_API_KEY')
            if not ls_key:
                missing.append('LANGSEARCH_KEY')
            print_check("AI Keys", False, f"Optional: missing {', '.join(missing)}")
        return True
    except Exception as e:
        print_check("AI Keys", False, f"Error: {str(e)}")
        return False


def check_env_values():
    """Validate critical env values (formats and sanity)."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        db_url = os.getenv('DATABASE_URL', '')
        host = os.getenv('HOST', '0.0.0.0')
        port = os.getenv('PORT', '8000')
        ok = True
        if not db_url.startswith('postgresql://'):
            ok = False
            print_check("DATABASE_URL format", False, "Expected to start with postgresql://")
        else:
            print_check("DATABASE_URL format", True, "postgresql://…")
        try:
            p = int(port)
            print_check("Server PORT", 0 < p < 65536, str(p))
            ok = ok and (0 < p < 65536)
        except Exception:
            ok = False
            print_check("Server PORT", False, f"Invalid integer: {port}")
        # Optional flags sanity (do not fail build)
        for flag in [
            "ENABLE_OPENLIBRARY",
            "ENABLE_GOOGLEBOOKS",
            "ENABLE_AI_ENHANCEMENT",
            "ENABLE_METADATA_ENHANCEMENT",
            "ENABLE_EMBEDDINGS",
            "ENABLE_SEMANTIC_SEARCH",
        ]:
            val = os.getenv(flag, '').lower()
            if val in ('true', 'false', ''):
                print_check(flag, True, val or "(unset)")
            else:
                print_check(flag, False, f"Expected true/false, got '{val}'")
        return ok
    except Exception as e:
        print_check("Env values", False, f"Error: {e}")
        return False


def check_faiss_indexes_readable():
    """If FAISS indexes exist, ensure they are readable by faiss."""
    try:
        from dotenv import load_dotenv
        import faiss  # type: ignore
        load_dotenv()
        idx_dir = os.getenv('FAISS_INDEX_DIR', 'data/faiss_index')
        identity = Path(idx_dir) / 'faiss_identity.index'
        topical = Path(idx_dir) / 'faiss_topical.index'
        ok = True
        for name, path in [("FAISS identity", identity), ("FAISS topical", topical)]:
            if path.exists():
                try:
                    _ = faiss.read_index(str(path))
                    print_check(name, True, f"Readable: {path}")
                except Exception as e:
                    ok = False
                    print_check(name, False, f"Unreadable: {path} ({e})")
            else:
                print_check(name, True, f"Not present (ok)")
        return ok
    except ImportError as e:
        print_check("FAISS availability", False, f"faiss not installed: {e}")
        return False
    except Exception as e:
        print_check("FAISS check", False, f"Error: {e}")
        return False


def check_vectorizer_embed_dim():
    """Check EMBED_DIM is defined and sane (from centralized config)."""
    try:
        from config import EMBED_DIM as dim
        ok = isinstance(dim, int) and dim > 0
        print_check("Embedding dimension", ok, f"EMBED_DIM={dim}")
        return ok
    except Exception as e:
        print_check("Embedding dimension", False, f"Error: {e}")
        return False


def check_prompt_template():
    """Check if the externalized Gemini prompt template path is present (informational)."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        default_path = os.path.join('prompts', 'gemini_metadata_prompt.txt')
        path = os.getenv('GEMINI_PROMPT_PATH', default_path)
        exists = Path(path).exists()
        msg = f"{path} (found)" if exists else f"{path} (not found, will use inline fallback)"
        print_check("Gemini Prompt Template", True, msg)
        return True
    except Exception as e:
        print_check("Gemini Prompt Template", False, f"Error: {e}")
        return False


def check_app_routes():
    """Inspect FastAPI app routes to ensure key endpoints are present."""
    try:
        from main import app
        paths = {getattr(r, 'path', '') for r in getattr(app, 'routes', [])}
        expected = {
            '/', '/health',
            '/catalogue/add', '/catalogue/pending', '/catalogue/confirm/{pending_id}', '/catalogue/insert/{pending_id}', '/catalogue/audit/{pending_id}',
            '/search/semantic', '/books', '/books/{book_id}'
        }
        missing = sorted([p for p in expected if p not in paths])
        ok = len(missing) == 0
        print_check("FastAPI routes", ok, "All present" if ok else ("Missing: " + ", ".join(missing)))
        return ok
    except Exception as e:
        print_check("FastAPI routes", False, f"Error: {e}")
        return False

def check_artifact_dirs():
    """Check FAISS and enhanced metadata directories."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        enhanced_dir = os.getenv('ENHANCED_BOOKS_DIR', 'data/enhanced_books')
        faiss_dir = os.getenv('FAISS_INDEX_DIR', 'data/faiss_index')
        ok = True
        # Ensure enhanced dir exists and is writable
        epath = Path(enhanced_dir)
        if not epath.exists():
            try:
                epath.mkdir(parents=True, exist_ok=True)
                print_check("Enhanced books dir", True, f"Created: {enhanced_dir}")
            except Exception as e:
                ok = False
                print_check("Enhanced books dir", False, f"Cannot create: {enhanced_dir} ({e})")
        else:
            writable = os.access(epath, os.W_OK)
            print_check("Enhanced books dir", writable, enhanced_dir + (" (read-only)" if not writable else ""))
            ok = ok and writable
        # Ensure FAISS dir exists and is writable
        fpath = Path(faiss_dir)
        if not fpath.exists():
            try:
                fpath.mkdir(parents=True, exist_ok=True)
                print_check("FAISS index dir", True, f"Created: {faiss_dir}")
            except Exception as e:
                ok = False
                print_check("FAISS index dir", False, f"Cannot create: {faiss_dir} ({e})")
        else:
            writable = os.access(fpath, os.W_OK)
            print_check("FAISS index dir", writable, faiss_dir + (" (read-only)" if not writable else ""))
            ok = ok and writable
        return ok
    except Exception as e:
        print_check("Artifact directories", False, f"Error: {str(e)}")
        return False


def check_virtual_env():
    """Check if running in a virtual environment."""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    print_check("Virtual Environment", in_venv, "Active" if in_venv else "Not activated")
    return in_venv


def check_dependencies():
    """Check if required packages are installed."""
    # Map package names to their import names
    required_packages = {
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'sqlalchemy': 'sqlalchemy',
        'psycopg2': 'psycopg2',
        'pydantic': 'pydantic',
        'requests': 'requests',
        'httpx': 'httpx',
        'python-dotenv': 'dotenv',
        # AI & Vector search
        'google-generativeai': 'google.generativeai',
        'faiss-cpu': 'faiss',
        'beautifulsoup4': 'bs4',
        'portalocker': 'portalocker',
        'numpy': 'numpy',
    }
    
    missing = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)
    
    is_valid = len(missing) == 0
    message = "All installed" if is_valid else f"Missing: {', '.join(missing)}"
    print_check("Required Packages", is_valid, message)
    return is_valid


def check_env_file():
    """Check if .env file exists."""
    env_path = Path('.env')
    exists = env_path.exists()
    print_check(".env File", exists, "Found" if exists else "Not found (copy from .env.example)")
    return exists


def check_database_url():
    """Check if DATABASE_URL is set in .env."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        db_url = os.getenv('DATABASE_URL')
        is_valid = db_url is not None and db_url != ""
        
        if is_valid:
            # Mask password in output
            masked_url = db_url
            if '@' in db_url:
                parts = db_url.split('@')
                if ':' in parts[0]:
                    user_pass = parts[0].split(':')
                    masked_url = f"{user_pass[0]}:****@{parts[1]}"
            
            print_check("DATABASE_URL", True, f"Set ({masked_url})")
        else:
            print_check("DATABASE_URL", False, "Not set in .env")
        
        return is_valid
    except Exception as e:
        print_check("DATABASE_URL", False, f"Error: {str(e)}")
        return False


def check_postgresql():
    """Check if PostgreSQL is accessible."""
    try:
        result = subprocess.run(
            ['psql', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_installed = result.returncode == 0
        version = result.stdout.strip() if is_installed else "Not found"
        print_check("PostgreSQL", is_installed, version)
        return is_installed
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print_check("PostgreSQL", False, "Not found in PATH")
        return False


def check_database_connection():
    """Check if database connection works."""
    try:
        from dotenv import load_dotenv
        from sqlalchemy import create_engine, text
        
        load_dotenv()
        db_url = os.getenv('DATABASE_URL')
        
        if not db_url:
            print_check("Database Connection", False, "DATABASE_URL not set")
            return False
        
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        print_check("Database Connection", True, "Connected successfully")
        return True
    except Exception as e:
        print_check("Database Connection", False, f"Error: {str(e)}")
        return False


def check_database_tables():
    """Check if required tables exist."""
    try:
        from dotenv import load_dotenv
        from sqlalchemy import create_engine, text, inspect
        
        load_dotenv()
        db_url = os.getenv('DATABASE_URL')
        
        if not db_url:
            print_check("Database Tables", False, "Cannot check (no DATABASE_URL)")
            return False
        
        engine = create_engine(db_url)
        inspector = inspect(engine)
        
        required_tables = [
            'books',
            'pending_catalogue',
            'catalogue_audit',
            'publishers',
            'authors'
        ]
        
        existing_tables = inspector.get_table_names(schema='lms_core')
        missing_tables = [t for t in required_tables if t not in existing_tables]
        
        is_valid = len(missing_tables) == 0
        message = f"Found {len(existing_tables)} tables" if is_valid else f"Missing: {', '.join(missing_tables)}"
        print_check("Database Tables", is_valid, message)
        return is_valid
    except Exception as e:
        print_check("Database Tables", False, f"Error: {str(e)}")
        return False


def check_project_structure():
    """Check if required files and directories exist."""
    required_paths = [
        'main.py',
        'config.py',
        'database.py',
        'models.py',
        'schemas.py',
        'requirements.txt',
        'routes/',
        'routes/search.py',
        'routes/catalogue.py',
        'routes/insertion.py',
        'services/',
        'services/ai/',
        'tests/',
        'db/Schema/db_files.sql'
    ]
    
    missing = []
    for path in required_paths:
        if not Path(path).exists():
            missing.append(path)
    
    is_valid = len(missing) == 0
    message = "All files present" if is_valid else f"Missing: {', '.join(missing)}"
    print_check("Project Structure", is_valid, message)
    return is_valid


def main():
    """Run all verification checks."""
    print_header("SLMS Setup Verification")
    print("\nThis script will verify your SLMS installation.\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_env),
        ("Project Structure", check_project_structure),
        ("Required Packages", check_dependencies),
        (".env Configuration", check_env_file),
        ("DATABASE_URL", check_database_url),
        ("AI Keys", check_ai_keys),
        ("Env Values", check_env_values),
        ("PostgreSQL", check_postgresql),
        ("Database Connection", check_database_connection),
        ("Database Tables", check_database_tables),
        ("Artifacts", check_artifact_dirs),
        ("Prompt Template", check_prompt_template),
        ("EMBED_DIM", check_vectorizer_embed_dim),
        ("FAISS Indexes", check_faiss_indexes_readable),
        ("App Routes", check_app_routes),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_check(name, False, f"Unexpected error: {str(e)}")
            results[name] = False
    
    # Summary
    print_header("Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total} checks")
    
    if passed == total:
        print("\n✓ Your setup is complete! You can start the server with:")
        print("  Windows: .\\start_server.ps1")
        print("  Linux/Mac: uvicorn main:app --reload")
    else:
        print("\n✗ Some checks failed. Please review the errors above.")
        print("  Refer to SETUP_GUIDE.md for detailed setup instructions.")
        
        # Provide specific guidance
        if not results.get("Virtual Environment"):
            print("\n  → Activate virtual environment:")
            print("     Windows: .\\venv\\Scripts\\Activate.ps1")
            print("     Linux/Mac: source venv/bin/activate")
        
        if not results.get("Required Packages"):
            print("\n  → Install dependencies:")
            print("     pip install -r requirements.txt")
        
        if not results.get(".env Configuration"):
            print("\n  → Create .env file:")
            print("     copy .env.example .env  (Windows)")
            print("     cp .env.example .env    (Linux/Mac)")
        
        if not results.get("Database Tables"):
            print("\n  → Initialize database:")
            print("     psql -U postgres -d slms -f db/Schema/db_files.sql")
    
    print("\n" + "=" * 60 + "\n")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
